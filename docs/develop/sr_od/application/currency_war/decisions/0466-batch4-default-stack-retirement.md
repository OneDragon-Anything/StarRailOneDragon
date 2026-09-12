# ADR-0466: 迁移批 4 commit-1——default 栈退役(default_strategy 本体删除)+ 继承解体 + 执行性钩子平移自持 + strategy_id 值域收敛

> **版本界碑(2026-09-04 ADR 存量 review;统一迁移批史,与 b94e9cfb 互证)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb 删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

## 状态

accepted(2026-09-03;W653 批 4)

## 背景

唯一策略载体裁决(ADR-0309)与重构蓝图 §4.4 定稿判据要求 `default_strategy.py` 与继承塔整体删除;但 `DecisionV2Strategy` 依赖继承复用执行性钩子(球/箱/遭遇/补给/巨星/伙伴/prep 步级族),v1 决策主线(`cw_plan.plan` 四层/`cw_evaluate.evaluate`)仍是买层唯一存活决策核(买层接管未兑现)。方案丙(W642,经 W646 对抗修正采信):继承解体不依赖行为迁移——钩子做「平移自持」(非折叠),行为迁移按失败模式分类后置挂账。

## 决策

1. **继承解体**:`DecisionV2Strategy` 改直接继承 `CwStrategy`;删除 `strategies/default_strategy.py` 全文(1080 行)。
2. **平移清单(W646 修正①,逐字平移零语义改动)**:抽象钩子漏项 `create_session`/`on_match_end`;事件钩子 `decide_invest/supply/encounter/megastar/partner/planner/star_tome/wish_trial/box_card`;prep 步级族 `decide_prep_action/_decide_prep_action_impl/_free_bench_step/_main_flow_step/_pseudo_state/_fresh_state`;私有 helper `_is_boss_round/_cap_shortfall/_levelup_engine_ok/_bench_junk_idx`;`on_round_end` 观测段内联进 dv 同名方法(替换 `super()` 调用)。删除前 20-def 可达性逐一对账 + 实例化冒烟(ABC 抽象残留=实例化 TypeError 风险闭合)。被 dv 覆盖不平移:`on_match_start`/`update_target`/`decide_prep`(v1 体)。
3. **三回退点收口(W631 §1)**:`cw_strategy_manager.instantiate` 未知 id 从「warning+回退 default」改显式 `ValueError`;`cw_replay` `--strategy default` 分支删除,旧语料回放改走冻结快照 worktree(报错信息指路;含非空 `sess_framework` 语料的抽验归编排者冻结面);`shop.py` 无对局态防御分支改构 `DecisionV2Strategy`。
4. **strategy_id 值域前置校验(W639 §4-11)**:`currency_war_config` 默认值 `'default'`→`'decision_v2'`;构造期校验,非法值加载即报错(禁「运行拼错才炸」);`shop.py` 遥测回显缺省同步。存量实例 yml(仅 config/01)已是 decision_v2,注释同步。

## Considered Options

- **方案甲(先折叠腾席链+买层接管再删)**:否决——把两个未竟行为批与删除批捆绑,失败时无法区分「迁移错」与「删除错」;工作量周级。
- **方案乙(双栈并存,只换读口)**:否决——违背 ADR-0309 唯一载体与蓝图 §4.4;每次判据改动双写或漂移。
- **平移时折叠进 prep_brain 守卫分区**:后置挂账(蓝图 §4.2 本意),删除批只做逐字平移,行为等价由「同 seed sim 决策序列逐位一致」锚验证。

## 后果

- 正面:1080 行 v1 本体消失;插件注册面唯一化;回退通道从「静默换栈」变显式报错。
- 代价/边界:旧 default 语料回放必须走冻结快照 worktree;`cw_replay` 主仓不再提供 default 臂;测试面 A 类删 3/B 类重钉 12/C 类改钉 3(测试仓同步 commit)。
- 挂账(W646 修正②/④,删除点 = max(两触发批)):①`cw_plan.plan`/`cw_evaluate.evaluate` v1 主线 + C1-C4/C6 读点 → 买层接管批后删;②`cw_plan` 10 个腾席判据函数(+C5 面)→ 腾席链折叠批后删;③v2 四层管线折叠进 `_select` → 折叠或 ADR 显式取消,二选一。验证锚:删除批同 seed sim 决策序列哈希逐位一致。
- 验证:L1 1845+ 绿(除并行批在飞红);L3 全量 3542 绿(2 失败均非本批归属:W636 在飞 turn_state 锁 + id_mark 顺序相关 flaky 单跑全绿)。
