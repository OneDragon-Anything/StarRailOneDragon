# 0336 - 旧策略栈删除:line_strategy + 配套模块

- **Status**: accepted(2026-08-25;ADR-0310 步 5 锁迁移清偿;删除门槛 W66 条件性通过 + W67 no_same 归零后执行;AD8 对抗后维持,附四条件见 Consequences 末)
- **Context**:ADR-0310 载体批后 decision_v2 为唯一策略载体,旧 `LineStrategy`(line_v2)停用不删作 A/B 对照臂与回退开关。删除门槛(sim A/B 验收通过即删,leader 裁定,不等实机)经 W66 合流总验**条件性通过**:
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
  - 负:config 切回 `line_v2` 的回退路径消失(ADR-0310 C5 窗口关闭)——回滚 SOP(三层,W79b review 补):主仓 `git revert ff430f79` + **测试仓 `git revert a2ad66c`(必须同步——不同步则 45 个 v1 锁测试缺失且 smoke 豁免表已删 dead_system 条目而 revert 后该检查器带 204/400 病根恢复,smoke 必红)** + 主仓子模块指针 `git revert 90df85e7`;ledger_consistency(账本 bug,单独修非 d2 批)/coldstart_direction(v2 高频真实缺陷,d2 批带修+补 v2 等价变异自检——原 v1 门单帧锁/变异自检锁随删,W79b 指出防线空缺)。
  - 兼容:遥测 schema 的 v2_* 字段与判栈保留(历史数据可判);session v1 遗留字段保留(反序列化兼容)。
- **AD8 对抗(2026-08-25)四条件与张力补记**:裁决=有条件稳固。①**承诺漂移如实记录**:本 ADR Context 承诺「v1 停用不删作 A/B 对照」,执行为全删+default 降格臂——v2 vs v1 永久不可重跑,后续证据口径以 W66 存档为唯一基线;②**统计叙述修正**:W66「hp 不劣」实为 CI[-0.89,+3.93] 内不显著(点估计 v1 优 1.52,功效~30%)——此后 sim 对照报告禁用「不劣」措辞,必写 CI+点估计+功效;no_same 归零验证域=seeds 0-99(100-399 约 71 违规未复验)→ 补验批挂策略池;③**时机张力**:删除依据 100% 为 sim(不可外推实机),v2 实机完整验证局为 0——W72 验证局即刻优先,书面接受无 v1 对照的归因降级;④**coldstart 防线**:v2 独有缺陷(79/400)的门锁+变异自检锁随删空缺,限期并入 d2 批补 v2 等价防线;d2 批前重估回滚窗口(测试载体已改,窗口窄)。
