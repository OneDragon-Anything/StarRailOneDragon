# ADR-0588: run_id 铸造边界对齐进局时刻(开局遥测行归属治本)

- 状态: Accepted(2026-09-07;方案经无前提对抗审零阻断后落地)
- 关联: ADR-0460(简报行归属缓冲,本 ADR 对其选项 B 翻案)、ADR-0273(runs 收口兜底回填,重算规则的人工审形态依据)、ADR-0335(收口钩子)

## 背景

run_id 曾在 `CwLoop.__init__` 才铸造,而入口链的遥测行早于铸造产生:简报行(ADR-0460 已用局间缓冲治过)之外,**投资环境/投资策略选卡行**(`record_invest_cards`,recorder 同一写端漏斗)走「run_id 空则丢、否则盖 `_CURRENT_RUN_ID`」门——开局 env/strategy 行被盖上**上一局** run 戳(冷启动首局则零行)。后果:45 个历史档案 `opening.chosen_env` 恒空或错收他局选择,「行 ts vs run 时间线」离线审计(行 ts 晚于所盖 run 收口)连报。

归层:遥测层·写端归因。采集面(OCR/落流)与最终选中可见性(`state.active_env`)完好,不动。

## 决策

**铸造单点前移 + 幂等认领**,三处落点:

1. `telemetry/state.py` 新增 `ensure_run_started(match, difficulty)` 与模块 token `_RUN_MATCH`(铸造时点的 match 容器引用,`is` 比较规避对象复活 id 复用)。门控三分支任一成立 → 经 `start_run` 铸新 run(函数体零改动)并在返回后自赋 token;否则认领现有 open run 原样返回:
   - `_CURRENT_RUN_ID` 空:进程首局/重启后首铸造(治冷启动零行);
   - `_RUN_CLOSED`:上局已收口,正常开新局;
   - `_RUN_MATCH is not match`:悬空 open run 防护(入口铸造后入口链 FAIL 的 run 不收口;新局确凿信号处容器弃置重建,新容器 ≠ 铸造时容器 → 强制重铸)。
2. `cw_entry_start.py` 三分支在写任何开局遥测行前调 ensure:简报锚(`_establish_match_once` 之后、`CwScreenBriefing.execute` 之前——新局路径第一个遥测生产分支)、投资环境分支、投资策略分支(后两者是「选卡前必有 open run」的硬保证,幂等)。
3. `cw_loop.py` `__init__` 从无条件 `start_run` 改调 ensure(同容器 open run 认领 = 一段一 id;接管局/run_operation/恢复路径上 run 已收口 → 按 gate 重铸,等价旧「每执行新 run_id」语义)。

**历史治理**:`tools/cw/repair_invest_attribution.py` 按「首个收口时刻 ≥ 行 ts 的 run」对 invest_cards.jsonl(env 与 strategy 两 kind 同罪面)重归属,再对受影响档案 `assemble_game` 重建。默认 dry-run;`--apply` 才落盘(备份 + journal + 原子重写,只换 run_id 字段逐字节保真);对「recovered 收口(回填 ts=名义窗尾)或无收口」run 名下的行单列「疑似串门-人工审」不自动改。幂等可重跑(重归属后 owner==stamped 全库成立)。

**装配端 ts 窗口兜底:不做**。服务对象消失(写端已对 + 历史真值可重算);兜底只堵 `opening.chosen_env` 一个读口(切片全列表/`--run` 查询/ADR-0132 效果回流对拍都修不动);双归属规则 = 永久判读歧义。**P2 摘除代价申报(落地审)**:方案附带的「装配端归属证据失真 log-warning 检测器」(只报警不改数据)本批未带——装配端此后**无写端归因回潮的常驻报警**,回潮检知依赖重算脚本 dry-run 的可重跑性(V2 签名 + 人工审清单即检出手法);判读侧发现 chosen_env 异常时,先重跑本脚本核对再下结论。

## Considered Options

- **A. 逐 kind 复制 ADR-0460 式缓冲**(仿简报缓冲给 invest_cards 加暂存+补写):按 kind 逐个缴税(简报已缴一次,invest 再缴,下一个入口遥测种类再缴),且治不了「行 ts 恒早于所盖 run 铸造时刻」的语义倒挂——离线审计永久误报;缓冲自身带「进程死在补写前 → 丢弃」丢失窗。弃。
- **B. 装配端按 ts 窗口重归属**:见决策节「不做」三论据。弃。
- **C. 铸造前移 + 幂等认领门(采纳)**:归属正确性在写点一次性成立,冷启动零行与错戳同治。
- **对 ADR-0460 选项 B 的翻案记录(如实表述)**:0460 曾否决「简报读取前预生成 run_id」,原文风险两条 = 「需要动 start_run **时序**」+「『继续进度』恢复路径跨文件高风险」。本案**确实动了 0460 否过的 start_run 调用时序**(调用点从 loop `__init__` 前移到入口链——这正是当年选项 B 的字面定义),以幂等门控 + gate 三分支对恢复路径的显式覆盖**拆除其风险后果**(重复铸造面/悬空 run 污染/恢复路径误伤),不是「未动时序」。翻案实质依据:第二个、第三个 kind(env/strategy)重复踩同一坑,「逐 kind 缓冲成本可控」的前提已被证伪。

## 后果

- 开局 env/strategy/简报行生而归本局;档案 `opening.chosen_env/chosen_strategies` 从恒空/串门变正确;冷启动首局不再零行。
- run_id 内嵌时间戳提前约 10-60s → game_id(首段 run 派生)随之变化——纯派生标识,无外部稳定引用,历史档案不受影响。
- 判读面口径变化:开局行 ts 合法地早于档案 `start_ts`(start_ts 不聚合 invest/exogenous 流);既有「窗外=串门」审计启发式须改判据为「行 ts > 所盖 run 收口」(重算脚本 V2 同款)。
- 每次入局铸造一次/认领零次;runs.jsonl 每 loop 执行仍恰一行收口 summary;缺陷闩/L0 换局重置时刻随铸造点前移(仍每局一换)。
- 残余缺口(显式接受):入口链 FAIL 的悬空 run 行留原始流不入档;真假局(开局即败零观察)run 悬空不入档——两世界(旧:串门污染他档;新:悬空留原始流可人工查)均无档案污染。
- 行为锁:`sr-od-test/test/sr_od/app/currency_war/test_cw_run_boundary.py`(L1-L6)、`test_cw_invest_repair.py`(重算脚本对账)。
