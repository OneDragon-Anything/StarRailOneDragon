# ADR-0638: T-64+T-183 合并批——已判死代码删除执行(C2 谷底回滚/C5 掉血三臂/flow 结算策略半 + T-183 三死函数退役)

- 状态:已实施(工作树;入库走编排者 committer,落地审候编排者另派)
- 关联:ADR-0583(on_round_end 拆两半——本批删除其策略半,观察半存活)、04_survival_budget §7 #7/#8(退役裁决正本,2026-09-04 用户裁定/编排者亲验定谳;本批 = 两裁决的「迁移后批次」执行欠账清偿)、ADR-0147/0148(roll 可负担门/穷金重建门限——设计消费方已消亡,随批退役)、方案正本 `.debug/temp/currency_war/T-64-交付报告.md`(v2,含方案对抗审 P1+低 4 项补全;T-183 语义判定与 18 符号守卫集申报)

## 1. 背景与归层

**归层**:决策层死码清除(纯删除,零行为变更申报)——非识别/执行/遥测层。

T-64(已判死代码删除批)与 T-183(comp 节奏锚)合并设计:方案批对三件死链逐符号复核后判死,本批执行删除。删除面 = 方案 §3.1 申报的 9 文件(cw_comps.py 零编辑,T-183 数据面保留)+ 测试仓 4 锁处置 + 退役负向新锁。T-183 面只做「删除 + level_plan 数据保留」——原任务语「接线复活三死函数」经方案批证伪改判为退役,comp 节奏锚在 mandate_v1 契约域新立命题件候方案审后另批立项。

## 2. Considered Options

- **✓ 删除执行(本批)**:三件均已裁退役且零行为死链经方案批逐符号复核维持(登记臂前置 `v3_evolution` 零写端臂恒假/三臂零决策消费端 write-only/三死函数调用面随旧栈消亡),删除是裁决欠账的清偿,不删 = 僵尸代码常驻 + 复活风险面。
- **✗「接线复活三死函数」(T-183 原任务语)否决**:①判据语境是旧栈(双轨读法/旧 get_node_goal 形态/已消亡的 committed_from 透传链);②mandate_v1 判据域以 contracts 契约登记为唯一接线纪律,复活 = 绕开契约面;③其 P1 金地板/急救援引的旧阈值域未过「未证即退役」门,复活即引入未证行为。
- **✗ 保留 pending_round_outcomes 消费语义否决**:策略半删除后槽只写不读,保留理由 = 观察半写入面(ADR-0583 存活半)+ 测试锚;消费方缺席候遥测面清理批再评估,不在本批扩面。

## 3. 已实施架构(删除面)

- **主仓 9 文件**(方案 §3.1 逐条):
  - `strategies/impl/flow.py`:imports(BloodAlarmTracker/rollback_weakest/RoundOutcome/NODES_PER_PLANE)、常量 `VALLEY_ROLLBACK_LOSS`、三方法(`_drain_pending_round_outcomes`/`_process_settlement_strategy_half`/`_alarm_node_type_fallback`)、两 drain 调用点、模块 docstring 段改写(墓碑注)。
  - `strategies/impl/mandate_v1/mandate_state.py`:4 字段(`v3_evolution`/`v3_alarm`/`v3_pending_rollback`/`v3_prev_hp`)+ 节注释单入口化;意向面字段(`v3_intention` 族)保留。
  - `kernel/cw_discipline_rules.py`:`BloodAlarmTracker` 类 + 伴生孤儿导入(deque/dataclass/field)。
  - `kernel/cw_evolution.py`:`rollback_weakest`/`_swap_action`/`_sell_action` + docstring 提及句同步 + 孤儿导入 `iter_deployed_slots`;EvolutionState 本体与演进引擎族不动(R5 W6 在册,另批裁决)。
  - `kernel/cw_state.py`:`NODE_TOKEN_TO_WORD` 词表;节注释精确到②半段删除,①半段(布局未知态复位槽式转发 `reset_layout_unknown_state`,flow.create_session 活消费)保留。
  - `kernel/cw_telemetry_exit.py`:`DEFECT_KIND_BLOOD_ALARM_NODE_FALLBACK` 常量。
  - `kernel/cw_economy.py`:T-183 三死函数(`_want_level_up`/`_resolve_level_goal`/`roll_affordable`)+ 伴生 `_xp_gold_floor` + 孤儿常量 `P2_REBUILD_GOLD_FLOOR` + 两导入(`LevelGoal`/`effective_hp_threshold`)与 TYPE_CHECKING `Comp`;`effective_refresh_prob` docstring 消费端描述同步。
  - `kernel/cw_strategy_session.py`:`pending_round_outcomes` docstring 改写(待加工队列 → 结算观察累积面,槽本体保留)。
  - `operations/cw_screen/cw_screen_battle_wait.py`:入槽注释消费端描述删除,观察半写入语义保留。
- **测试仓**:2 锁删(`test_valley_rollback_weakest_then_pause`/`test_valley_rollback_no_retained_sells_weakest`,被锁函数退役)、1 锁改判恰 0(`test_valley_rollback_slot_zero_consumer_guard`:基线声明1/写1/读1 → `v3_pending_rollback` 全 src 零存在,docstring 记语义演进)、1 锁保持(`test_valley_rollback_slot_guard_blindspot`,合成样本自检)、`_THRESHOLD_CONSUMERS` 合法减员(cw_economy 止损门行随 `_xp_gold_floor` 退役,锁文自载减员路径)。
- **退役负向新锁**:`test_cw_t64_retired_symbols_guard.py`——17 符号(18 集减 `v3_pending_rollback`,后者由改判后的 slot 守卫专辖,两锁合计恰覆盖 18 符号集,不重复断言)AST 标识符全零扫描(声明/读/写;注释/docstring 墓碑提及不入 AST 天然豁免)。

## 4. 边界申报

- **零行为变更申报**:删除链全部符号 src 零活消费端(方案 §2 逐符号双向核对);行为中性由「HEAD worktree vs 本批树 `cw_replay --diff` 输出逐行一致」实证(同档案零新增分歧;档案对 HEAD 的既有分歧系档案录制后已入库行为批所致,非本批面)。
- **SwapDeploy 动作链转零生产者**(申报不扩面):`_swap_action` 删除后 `SwapDeploy` 类体与其执行链、cw_bench_equips 分支、sim ledger 检查成零生产者/测试直调面,与演进引擎族同型,候动作面清理批或 R5 W6 一并裁决。
- **cw_evolution 演进引擎本体**(evolution_step 族)src 零调用仅测试直调:R5 迁移规划 W6 有在册角色,不随本批删除;`EvolutionState.paused` 写端已消亡,恢复分支为防御性保留(docstring 已注明恒 False 不构成活路径)。
- **_xp_gold_floor 挂账清偿**:[39]「HP 分支待删」载体即本函数,删除即清偿;ADR-0519「组 5 合法件」的合法性评价随消费面消亡失对象,本 ADR 记档。
- **cw_state 注释段精度**:节注释辖两个入口,删除精确到②半段(词表);①半段布局未知态复位是活入口(flow.create_session 消费 + obs cw_back_layout 注册),保留并改单入口口径。

## 5. 验证

- **守卫移除变异红证**:干净文件(cw_investments.py,非本批面)注入函数体形态探针(引用 `VALLEY_ROLLBACK_LOSS` + 读 `.v3_pending_rollback`)⇒ 新锁 `test_t64_retired_symbols_absent_in_src` 红(命中并报 `cw_investments.py:行号`)+ slot 守卫红;git 还原后双绿。负向锁有牙证明在案。
- **点名域全量**:`uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"` = **3290 passed / 2 skipped**(167s)。
- **ruff**:9 个主仓改动文件零违规;测试仓 3 文件的 13 条(UP009/I001/E402)经 HEAD 版本对照为存量债(同数),本批零新增。
- **import 冒烟**:flow/mandate_v1_strategy/sim.engine_p1/cw_economy/cw_discipline_rules/cw_evolution/cw_state/cw_telemetry_exit/cw_screen_battle_wait 九模块导入全绿(引擎路径断裂排查)。
- **grep 零残留**:18 符号全仓(src+测试仓)grep 仅剩墓碑注释/docstring 词形,AST 标识符面零存在(负向锁守)。

## 6. 文档三同步

本 ADR + INDEX 行;04_survival_budget §7 #7/#8 欠账行销案(改「已执行」);flow/README.md 实现面与 §5 违宪标记销案;flow/prep_visit.md §5 谷底回滚标记销案;flow/screen_op.md §2-2 roll_affordable 死码注记销案;proofs/p39 头注(roll_affordable/_xp_gold_floor 陈述过期,正文不改)。
