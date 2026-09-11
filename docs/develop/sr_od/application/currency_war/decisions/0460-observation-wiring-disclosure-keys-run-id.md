# ADR-0460: 观测接线批——披露键进 decisions 遥测 / obs_conflicts 补 run_id / 简报行归属

- 状态: accepted
- 日期: 2026-08-30
- 关联: W576 预注册判定移交清单②③④(数据面缺口声明 2/3/4);W586 复盘 B4(简报词缀清单错位的下游受害例);ADR-0451(血预算停手,披露键的语义出处)

## 背景与问题

三处观测面缺口导致判读盲区(W576 三局判定实证):

1. **血预算披露键未落遥测**:`v3_blood_budget_rejects` / `v3_blood_budget_refresh_rejects` 在 session 有写点(arbiter/remediation 拒付面)但 decisions.jsonl 全文检索零命中——「带内拒付计数 >0」这类预期无从判定(组1.2/组9.1)。`p1_directed_downgrade_active` 是纯谓词(无 session 写点、无遥测落盘),末窗降格触发面不可观测(组1.6)。`xp_expect_ledger` 在 StrategySession 上是动态 setattr 属性(W552),asdict/遥测不可见。
2. **obs_conflicts.jsonl 无 run_id**:归局只能按 ts 时间窗手工过滤。
3. **exogenous 简报行 run_id 归属滞后**:简报屏在 `CurrencyWarRunLoop.__init__`(start_run)之前读——此刻 `_CURRENT_RUN_ID` 为空(进程首局,行被静默丢弃)或指向上局(行带旧 run_id,ts 却落在下一局窗口;局20/局21 实证)。下游受害例:W586 B4 中两份局22 词缀清单不一致,简报存证行的归属错位正是取错源的候选根源。

## 决策

零决策行为变更,三件全为观测面接线:

1. **披露键接出点 = recorder 统一自取**(非 shop.py extra 通道——该文件归属他批,且 `record_outcome` 板深快照已有 `_CTX_MATCH_REF` 模块槽自取先例):`TelemetryRecorder.record_decision` 落盘前自 session 取两个拒付计数、平铺 `xp_expect_ledger`(dict);`p1_downgrade_active` 按 state + `DEFAULT_REGISTRY` 现算(生产 `DecisionV2Strategy()` 缺省即 DEFAULT_REGISTRY;sim A/B 注入臂行不带此语义保证,判读按 strategy_id 分栈)。`xp_expect_ledger` 同时升为 StrategySession 正式字段(动态属性→声明字段,pending_buy_expect 同判例);prep_director 读写端 getattr 兜底天然兼容,不改。
2. **obs_conflicts 补 run_id = 唯一汇点内部自取**:所有调用点收敛于 `cw_observe.obs_conflict()`,在该处取 `current_run_id()` 补键——旧结论「写入点 10+ 处逐处加参数是高风险机械改动」不成立,调用方零改动。历史行无此键,读取端按「有键才过滤」容忍,不回填。
3. **简报行归属 = 写入时点带正确归属(局间缓冲)**,而非读取侧按 ts 窗口重归属——侵入面小一个量级(只动 cw_telemetry 模块内,判读工具与历史数据零改动):live run 存在时简报行照写;run 关闭(summary 落盘)后或进程首局前,kind='briefing' 行暂存模块槽(上限 16 行),`start_run` 建新 run_id 后以新 id 补写,ts 保留采集时点。其余 kind 维持原 no-op 门(局外事件族不归属下一局,防行为面外溢)。代价:进程在补写前终止则缓冲丢弃——相比原状(行被丢/带错 id)只改善不劣化。

## Considered Options(简报归属)

- **A. 读取侧按 ts 窗口归属**:判读工具与下游脚本都要改,历史窗口口径各自维护,漂移风险高。弃。
- **B. 简报读取前预生成 run_id**:需要动 start_run 时序与「继续进度」恢复路径,跨文件高风险。弃。
- **C. 局间缓冲 + start_run 补写(采纳)**:单文件、零调用方改动、归属语义在写入点即正确。

## 后果

- decisions 行新增四个可选末尾字段:`sess_blood_budget_rejects` / `sess_blood_budget_refresh_rejects` / `p1_downgrade_active` / `xp_expect_ledger`(None=缺省,旧 schema 不破坏)。
- obs_conflicts 新行带 `run_id`;`query_obs_conflicts` 视图 `--run` 给定时按该键过滤(历史行不命中,空参全量)。
- exogenous 简报行归属正确;进程首局的简报行(此前恒丢)开始可见。
- 行为锁:`sr-od-test/test/sr_od/app/currency_war/test_cw_w603_telemetry_wiring.py`。
