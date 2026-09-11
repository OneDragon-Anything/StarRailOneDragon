# ADR-0598: T-160 息帽覆写死链修复——cap_resolved 单一源切 aggregate 聚合 + registry 预算面随批接线 + 幻影卡收口

- 状态:已实施(commit 候编排者统一门)
- 关联:ADR-0131(EconomyEffect 聚合语义:cap 并持取宽 max,0 是有效覆写)、ADR-0516(cap 三源归一,本批为其归一方向的预算面收尾)、ADR-0463(息线恒等式)、ADR-0571(披露面纪律,本批未触)、ADR-0597(S2 谓词对 `interest_cap_override` 的消费与本批决策链消费同输入源)、`kernel/cw_economy.py`(cap_resolved_of_session/reserve_cap)、`kernel/cw_line_switch.py`(e_rounds)、`strategies/impl/mandate_v1/assembly.py`(BudgetView)、`operations/cw_screen/cw_screen_invest_strategy.py`(持卡写点)
- 方案正本:`.debug/temp/currency_war/attacks/prep_strategy_attack_20260908/攻击报告.md` F1 与同目录 `F1方案审.md`(无前提行为攻击 → 方案审「修改方案后放行」,注入面裁决 = 单一源切 aggregate + 测试迁移)

## 1. 背景与病理(归层:决策判据消费层)

备战/商店/发射帧全部息帽阈值经 `cap_resolved_of_session` 供给,而它读
`MandateState.cw4_cap_override`——**全仓零生产写点的死字段**(注册表
`STRATEGY_ECONOMY` 三卡覆写值在册且正确:开源节流 9/利息上调 10/买断制
0;聚合器、sim 收入模型、S2 选卡谓词都消费它,唯独 cw4 决策链结构性
全盲)。后果(实机 10 局持三类卡):买断制局仍守 50 息线——凑息卖把
备战件卖掉去凑一个不存在的息(演示局 g_20260901_202525 金轨迹
44→51→51→47→51→59 贴线囤金,form_ok 全程 False,hp 82→1);利息上调/
开源节流局把 51-100 金带当溢余烧掉。sim 侧「收入按 cap 9/10/0 结算、
决策按 cap 5」系统性错位。

## 2. Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| 补 cw4_cap_override 写点于投资落卡时点 | ✗(方案审) | 注入第三态字段 = 双源并存,死链病复发面;聚合单一源已在册 |
| cap_resolved_of_session 直读 aggregate_economy(session.active_strategies) | ✓ | 注册表派生、零新参数、sim/实机两态同路径;append-only 假设与 economy_score/S2 共享 |
| registry 预算面(reserve_cap floor/BudgetView.interest_floor/换线 affordable)挂账不动 | ✗(编者裁决) | 买断制囤金经刷新授权车道部分存活,③验收无法归因;三处同批接线 |
| None/0 经 `or` 真值折叠 | ✗(最高危陷阱) | 买断制 0 是有效覆写,折叠回 5 且可能全测试绿;判别只认 None |
| e_rounds 从 state 镜像取卡 | ✗ | state 镜像非公共权威(方案审明文);session 参数线程化 |
| 保留 cw4_cap_override 字段为墓碑值 | ✗ | 保留可写字段 = 回流陷阱;删码 + 类体墓碑注 + grep 锁 |

## 3. 已实施架构

1. **核心修复**:`cap_resolved_of_session` = `interest_cap_resolved(
   aggregate_economy(list(session.active_strategies)).interest_cap_override)`,
   空持卡/裸 session/None 回 `DEFAULT_INTEREST_CAP`;docstring 声明
   注入面(实机 handler 确认后 append / sim 注入臂 append+镜像)、
   None/0 判别语义、append-only 回落边界;禁 per-session 缓存(纯函数,
   单帧锁友好)。
2. **预算面三处接线**(session resolved 链,registry 旋钮退役出本缝):
   `reserve_cap` floor(`registry.interest_cap×10` → `saturation_line(
   cap_resolved_of_session(session))`,签名去 registry 参)、assembly
   `_budget` 的 `interest_floor` 分量、`cw_line_switch.e_rounds` 可负担
   窗(新可选 `session` 参,None 形态退注册表派生值保旧桩零漂移;调用
   点 best_alt_line/proof.py×3/cw_intention×1 线程化)。
3. **幻影卡收口**:`cw_screen_invest_strategy` 持卡 append 从点卡确认前
   移到 `confirm_and_verify` 成功后——确认失败轮(round_retry)不留
   幻影卡;幻影买断制 = 息线全关,比幻影 9/10 更烈。
4. **sim 检查器覆写语境观测键**:engine 账本行新增
   `sess_active_strategies`(轮末快照,`sess_active_env` 同构惯例);
   `check_levelup_budget_gate` τ 由行键聚合解析 cap(键缺席 = 历史账本
   /无持卡 → DEFAULT,与旧钉值同值零漂移),兑现 ledger.py 原预留义务。
5. **随批清理**:`cw_plane_table.interest` 零调用第二息实现删除(墓碑
   注在位);`interest_cap_resolved`/`statefn/interest.py` docstring 的
   「MechanismMutation 运行时突变视图」未实现引用修正;
   `MandateState.cw4_cap_override` 字段删除 + 墓碑注 + grep 锁;
   `cw_replay._restore_session` 补 `active_strategies` 回读(持卡局
   重放的修复可见性前提)。

## 4. 边界申报

- **get_node_goal 标量投影缝(结构性,不扩修)**:该接缝以 session=None
  调 `refresh_ev_budget`/`schedule_upgrade` → 息帽 resolved 链恒 base
  cap;接缝无 session 入参(消费面 = entry 兼容调用,量级有界),代码
  体已留申报注。
- **锚 A1 后段未中 + 金出口族未联动(A/B 观测,如实记;落地审 M1)**:
  锚 A1(事前写「r3-r9 均金低于 before」)前段兑现、后段反转——本批
  n=200:r7-r9 均金 after 71.0/109.0/126.6 vs before 51.9/69.4/57.1
  (落地审 n=40 抽验同向:61.8/98.8/111.9 vs 45.8/65.5/56.8);锚按事前
  定义**未中**,按 strategy-work §4「锚点没中=要查」闭环归因:cap=0 使
  升级排程闸(② 前置)恒开 → 金流向升级车道——升级车道吸金合法
  (hp 过程量全段变好是硬证据),但**金出口族其余车道(买牌/刷新)未随
  cap=0 联动**:升级到顶后金重新囤积(息=0 时囤金不亏息、无害但也未
  转化),refreshes/局 23.96→0.0(升级臂在单动作帧序中遮蔽刷新臂;
  刷新授权面未关死——w633 锁与落地审 n=40 抽验双证 `refresh_ev_budget
  (买断制)>0`)。「买断制=攒钱无意义→全花掉」的行为闭环未完成。非本批
  修复缺陷(相对死链基线全面不劣且更好,非回滚理由);**挂账期限化**:
  「刷新/升级车道预算竞速 + 金出口族 cap=0 联动」观察项,归属 = 下一个
  全 planes sim 批或实机持卡局判读(观测批)必核;在账未销前,买断制臂
  A/B 判读禁以「金不囤积」为通过线。
- **H5 流动性下降如实记**:利息上调臂 r5-r9 均金 57.76→99.63(守息
  更深)、refreshes 28.3→24.9、levelup spend 101.3→96.6——流动性下降
  存在,末 hp 38.02→38.56 在噪声带内,本批只裁「联动生效」,不裁净效果。
- **回落语义**:「卖掉后回落」无实现通道(投资策略无移除建模),
  回落实际形态 = 「从未持有」;与 economy_score/S2 共享同一 append-only
  假设,非本批新引入。
- **检查器相邻字面量(未动,出本批文件面)**:`check_levelup_interest_
  engine_gate` 的 `gold0 < 50` 字面量(ADR-0354 判据定义)未随本批
  cap 化,如需覆写语境化另立小批。

## 5. 验证

- **注册表直调**(锚点纪律):三卡覆写值 9/10/0 与并持 max(9+10→10、
  0+9→9)亲跑在案;`STRATEGY_ECONOMY` 为值单一源。
- **单帧锁**(新文件 test_cw_cap_override_link.py,8 支):①三卡联动
  (kernel 链+R* 预算面+换线可负担窗)/②回落三形态/④None-0 区分
  (g*=0、interest=0、两溢余域恒 False)/⑤并持 max/墓碑 grep 锁。
- **L1 快速集**:3179 passed(修复 test_cw_obs_chain 死导入重锚后全绿;
  test_cw_must_spend_zone/sell_reason_matrix/p56_t1/prep_flag_machine/
  r2_interest_floor/w633/launch_arbitrage/op_boundary/cw4_mandate_v1/
  l3_prep/p71_budget_gate/budget_disclosure 12 文件注入通道迁移,w633
  注入一致性锁按「链动/registry 旋钮不动」语义重推改写——买断制可达
  值 0 替 registry 不可达值 4,判别结构保形)。
- **零漂移臂(sim,n=200/臂,同 seed 配对)**:invest=False 两臂 ledger
  逐位一致 200/200。
- **持卡 A/B(n=200/臂,planes=1,池指纹 460e6031e2f4)**:买断制臂
  hp 过程量 r3-r8 全段 +2~3、末 hp 38.68→39.91、hp_ge_60 0.185→0.21;
  「贴 50 息线」形态消失(单局深读:死链臂金位 45-52 贴线帧消失,
  金流向升级车道,levelup 发射从 r3 前移);**锚 A1 未中已记**:r7-r9
  金反转(读数与「金出口族未联动」归因见 §4,挂账期限化在案),非隐瞒
  通过;利息上调臂守息更深(r5-r9 均金 57.76→99.63)。
- **演示局重放(g_20260901_202525,cw_replay --diff + 死链双跑边界
  对照)**:修复引入的漂移 = 死链臂在金 51/47/55/59 帧的凑息卖
  (Sell×7,跨 p1r6-p2r4)在修复臂**全部消失**——「卖备战件凑不存在
  的息」病理在重放链闭死;无持卡局(run_20260908_074522,持三张非息帽
  卡)两臂回放输出逐位一致(分歧 = 档案期旧码既有漂移,与本批无关)。
- `ruff check` 全绿。

## 6. 文件面(逐文件点名,commit 用)

src:kernel/cw_economy.py、kernel/cw_plane_table.py、kernel/cw_line_switch.py、
kernel/cw_intention.py、strategies/impl/mandate_v1/{mandate_state,assembly,
turn_state,economy_cycle,proof,statefn/interest}.py、operations/cw_screen/
{cw_screen_invest_strategy,_overlay_confirm}.py、sim/{checks/ledger,
engine_p1,cw_replay}.py、本 ADR + INDEX 行 + 01 号稿 §5 resolved 行 +
20 号稿判据源行 + sim/sim-wiring.md(共 docs 5 支)。测试仓(14 改 +
1 新):test_cw_{must_spend_zone,sell_reason_matrix,p56_t1,prep_flag_
machine,r2_interest_floor,w633_migration_b3,launch_arbitrage,op_boundary,
cw4_mandate_v1,l3_prep_must_spend_latch,p71_budget_gate,budget_disclosure,
obs_chain,sim_suite}.py + 新增 test_cw_cap_override_link.py。

混入声明(落地审 L1):test_cw_sim_suite.py(:1216-1226 GameState 对账
锁 41→36)与 sim/sim-wiring.md(「结构未建」档撤档)系历史 commit
68d411cc(GameState 死字段五枚删除)的迟到补账,随本批工作树混入——
内容与本批修复方向一致(死字段清理对账),经落地审核实「方向正确」
后纳入本批文件面,commit 时随批点名,防与并行批相撞。
