# 0336 - 旧策略栈删除:line_strategy + 配套模块

- **Status**: accepted(2026-08-25;ADR-0310 步 5 锁迁移清偿;删除门槛 W66 条件性通过 + W67 no_same 归零后执行)
- **Context**:ADR-0309/0310 载体批后 decision_v2 为唯一策略载体,旧 `LineStrategy`(line_v2)停用不删作 A/B 对照臂与回退开关。删除门槛(sim A/B 验收通过即删,leader 裁定,不等实机)经 W66 合流总验**条件性通过**:
  - hp 不劣:符号 gap(v1−v2)=+1.52(n=400 配对,95% CI 底 ±2.41);
  - 过程不劣/部分更优:trio3 0.19 vs 0.055;v1 独有病根 `dead_system_second_pivot` 0.51/局(204/400)随删除自动消灭=删除净收益;
  - 条件① no_same 归零:W67 修复(ADR-0328);条件② 删除前 v2 全量 checks 复跑:完成;条件③ ledger_consistency d2 已知债:登记不阻塞。
- **Considered Options**:
  1. **保留 line_strategy 仅作 sim 对照臂(不删)**——拒绝:违背删除目标;旧代码 1844 行成死重;双注册 A/B 语义已由「decision_v2 vs default」替代。
  2. **保留线库/状态机等配套模块**——拒绝:消费方(LineStrategy/cw_signal_lock/sim_checks v1 检查器)随删除清空,留即死数据;核心数据(桥池/配方/战力表)已由新栈消费,本批保留。
  3. **全删 + sim 对照臂切换(采纳)**——**采纳**:删 `line_strategy.py`/`cw_phase_machine.py`/`cw_signal_lock.py`/`cw_line_library_v1.py`;sim 默认策略切 DecisionV2Strategy;A/B 对照臂=default 栈(DefaultCwStrategy,simulate_p1 增 config 注入);v1 语义检查器 8 个随删;ADR-0310 兼容垫片(步 5 锁迁移)清偿。
- **Decision**:
  1. **删除面(src,4 文件)**:`strategies/line_strategy.py`(LineStrategy 本体)/`cw_phase_machine.py`(状态机,唯一运行时消费方=LineStrategy)/`cw_signal_lock.py`(信号锁线,唯一消费方=LineStrategy)/`cw_line_library_v1.py`(线库 v1,消费方=LineStrategy+cw_signal_lock+v1 检查器)。理由:全部为 v1 专属输入/运行时,决策_v2 零消费(唯一例外=core_count_for 线库分支已改)。
  2. **sim 默认策略切换**:`simulate_p1` 默认策略 LineStrategy → DecisionV2Strategy(sim 模拟生产唯一载体);`simulate_p1_batch` 无 strategy 参数自动跟随。A/B 对照臂方案:**default 栈(DefaultCwStrategy)**——内置 v1 打法,一直存在、不依赖被删模块;`simulate_p1` 新增 `config` 参数(默认 None,decision_v2 不读;default 臂对照传 SimpleNamespace 桩,含 faction_priority 等)。历史 v1 数字(W66 n=400)存档为删除前基线,不再重跑。
  3. **v1 语义检查器删除(sim_checks 8 个)**:`carry_on_shelf_responded`/`no_future_carry_sold`/`dead_system_second_pivot`/`carry_gate_bench_deadlock`/`bond_fallback_purchase_validity`/`protect_set_bench_share`/`carry_gate_outcome_tracking`/`recipe_refresh_ev_guard`——判据全部绑定 v1 线库(line_of),v2 栈下恒空转(W66 实证全 0);v1 删除后失去对象。`degrade_recover_mutex` 保留(通用 target 切换检查);`p2_precache_gate_closure` 保留(代理口径不依赖线库,注释更新)。`_carry_floor_est`/`_CARRY_FLOOR_*` 死代码随删。
  4. **兼容垫片清偿(ADR-0310 步 5)**:`decision_v2/candidates._legacy_target_names`(旧线库/桥池目标集派生)删,裸 session 退引擎件种子;`discipline` 的 locked_line 方向门回退删;`filters.current_mode` 的 v2_state 兜底删;`strategy._ensure_state` 的 v2_state 初始化删。session 字段 `v2_state`/`locked_line`/`bridge_id`/`v2_prev_hp` **保留**(遥测 schema 兼容 + 历史回放),注释标 v1 遗留;`v2_round_key/bought/sold`/`v2_seed_bought`/`v2_ever_full_interest`/`v2_remedy_used` 为 decision_v2 在用(保留)。
  5. **配套清理**:`cw_replay` `--strategy line` 分支 → decision_v2;`cw_telemetry` 判栈保留 `'line_v2'` 字符串(历史 decisions.jsonl 数据兼容,生产不再产生);`cw_line_defs.core_count_for` 线库分支删(桥池+三人组保留);遥测 `v2_*` 字段(schema 兼容)与 shop.py 写端保留(恒空)。
  6. **测试**:删 45 个锁 v1 行为的测试文件(LineStrategy 单帧锁/r2xx-4xx 系列/状态机/信号锁/主测试);改 10 个(梯度开关/载体测试/策略注册/检查器 repay/core_count/b36 双臂/buy_reason/adr0286/adr0291/0295/0296/0299/0300/r410/r420/w48 等——旧载体形态测试改意向载体,sim 默认策略变化适配);cw_quick.txt 移除已删文件条目。
- **Consequences**:
  - 正:旧策略栈清零(死重/双源/兼容垫片全清);sim 默认=生产唯一载体,对照臂常驻(default)保留 A/B 方法论;v1 病根(dead_system 0.51/局)随删消失。
  - 负:config 切回 `line_v2` 的回退路径消失(ADR-0310 C5 窗口关闭)——回滚=git revert 本删除 commit;ledger_consistency/coldstart_direction 的 v2 已知债继续存续(d2 行为面,豁免表登记)。
  - 兼容:遥测 schema 的 v2_* 字段与判栈保留(历史数据可判);session v1 遗留字段保留(反序列化兼容)。
