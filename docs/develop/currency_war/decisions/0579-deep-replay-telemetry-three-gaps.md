# ADR-0579: 深度复盘遥测三缺口(candidate_scores 供数恢复 / op_journal 逐动作行 / 非决策 op journal)

日期:2026-09-07;状态:已接受
关联:ADR-0571(披露面豁免与 grep 守卫范式)/ADR-0577(hp 事件模型 v9,禁入决策输入先例)/T-113(账本);方案与双审 = `.debug/temp/currency_war/t112_deep_telemetry/{方案.md,方案审.md,方案审-v2.md}`

## 1. 背景与问题

用户需求:「至少看到每一次画面 op 调用的观察数据和决策动作,理由可以没有」。三缺口实证(run7 42 决策行 + 075840 73 行直读):

1. **candidate_scores 全库恒空**(孤儿缓存):字段声明在(mandate_state)、读端活(buy_cards :695-697 轮次守卫 + :859 落盘)、写链每帧都走,但生产者随 v1/v2 架构删除(690e9dba/b94e9cfb)后无人写。决策依据字段本身健康(target_comp/eval_breakdown 非空 70/73+40/42,空帧=补给节点结构性)。
2. **商店段内逐动作期望态断供**:ADR-0517 §8.5 申报挂账——decisions 行保持段尾累计形态,段内投影只进 log,「这轮五次点击各自的盘面变化」不可见。
3. **非决策 op(战斗等待/入口链/位面切换)零结构化行**:obs_conflicts 只记不一致(负空间 journal),正常轮询只有日志文本。

## 2. 决策

### 2.1 缺口①供数恢复(写点唯一源)

`flow.py::update_target` 段级重入守卫体内(update_intention 之后)**每轮恰一次**写候选线评分表:`_telemetry_last_candidate_scores = {线名: round(line_completion_feasibility(state, c, session, registry, visible), 4)}`(候选集 = `_v2_comps()` − `ist.evicted` − `weak_planes` 命中)+ 轮次戳。评分器 = P2 判据核心单一源,零新自由参数;P1 帧上 G 的视界语义按函数现状如实落盘(判读按位面分层)。

**C1 字段改名(方案审必改项,采纳推荐②)**:`last_candidate_scores` → `_telemetry_last_candidate_scores`(`_round` 同)。`_telemetry_` 前缀自带披露面隔离——守卫从「白名单豁免读端」升格为「全仓命中点计数锁」(合法命中 = mandate_state 声明×2 + flow 写点×1 + buy_cards 读点×1,第 4 文件即红),白名单语义不塌。改名成本 = 声明×2 + 读点×1 共 3 处;decisions.jsonl 落盘键 `candidate_scores` 是 schema 字段名不受影响。

**轮内时序语义(C2,必报)**:段级重入守卫使候选表 = 轮入口(首个 update_target 调用点)快照,**非店开时刻值**——商店行判读时按「选线时点的 G 值」理解,勿当店开实况。

### 2.2 缺口②③新流 op_journal.jsonl

独立薄流(体积红线:**永不并入 decisions 行**;decisions v1 零 schema 变更):

- **kind='action'**:唯一写点 = `apply_action_outcome` 回执位(cw_op_buy_cards);CloseShop 终结不入行(ADR-0518 契约);被拒动作零行(拒因面 = spend_gate 拒因 + spend_ledger 既有辖域)。字段:ts/run_id/plane/round_num/seq(段内动作序)/frame_seq(段序关联键,C6)/action(serialize_action)/exec_ok/gold/bench_used/expected_delta。
- **expected_delta = 全量展平叶级 diff**(C3 写死,零漏报口径):前后帧各 `serialize_state` → 全量展平(嵌套 dict 递归点号路径;列表叶 = 整列表替换计一条)→ 键集对称差 + 同键值比较;>12 条截断置 `_trunc`(读端按「此帧 delta 不完整」分型)。投影之外的真实变化必然出现在 delta(「投影没算到但真变了」= 投影残差,深度复盘核心抓取面)。
- **kind='op'**:非决策 op enter/exit 成对行(位面过渡/战斗等待已接线;op 名 = op_name 单一源;obs 有界键摘要;轮询 tick 不落行)。孤儿 enter 行(中断丢 exit)= 进程中断证据,装配端 `_annotate_orphan_op_rows` 标注 `outcome='orphan'` 容缺非缺陷。
- **体积纪律**:action 行 ≤400B / op 行 ≤250B(超限截断 `_trunc`);每局 500 行软上限超限停写;`_SLICE_FILES` 追加(v9 内加法,免重装配);禁入决策输入(grep 守卫:`expected_delta`/`frame_seq` 键族出 telemetry/op_journal + match_archive 即红)。

### 2.3 语义张力声明(C7)

`candidate_scores` 在 v1/v2 时代就是选线器的**决策输入**(被删的生产者即选线器评分链);今日恢复供数 + 声明禁决策消费 = **语义反转**。守卫只强制当下合规;未来选择器如需合法消费(如 P74/P75 落码后把可行性分用于选线)**必须先撤守卫再改语义**,防后人把「守卫拦红」误判为遥测缺陷。

## 3. 后果

- 正面:深度复盘三大缺口闭合;cw_divergence_stats(close_call 判读)恢复供数;sim/生产两侧 decisions.jsonl 同亮。
- 代价:decisions.jsonl 商店行每帧 +~10 键(全史 +2-4MB);op_journal 新流 ~25-40KB/局(500 行硬顶 = 200KB/局保险丝);逐候选可行性每轮毫秒级计算(实施批实测数字候首局补录)。
- 中性:P1 帧候选表如实落 G 的视界语义;备战步进帧/补给帧结构性空与本字段无关(判读口径)。
- 风险与防线:遥测禁入决策输入(grep 守卫族)/行帽与软上限/独立流(应急阀门 = _SLICE_FILES 一行可裁)。

## 4. 验证

新锁(test_cw_op_journal.py):逐击一行/未执行零行/delta 全量性(投影外变化必现)/守卫移除红检/命中点计数锁/孤儿行容缺/run_id 门控/软上限停写。双局重装配读数 + 首局体积实测数字随落地审补录。
