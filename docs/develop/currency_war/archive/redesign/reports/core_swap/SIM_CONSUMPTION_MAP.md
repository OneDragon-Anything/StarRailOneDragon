# CW sim 侧决策接口消费面测绘(策略器换核 + 备战接口升序列的设计输入)

> 产出范围:sim 引擎对 `CwStrategy` 决策接口的消费面测绘。所有行号亲读自当前工作区代码(2026-09-03)。结论强度 = 最弱一环,逐条标注。
> 文件面声明:本文件是本次任务唯一写入;其余全部只读。

---

## ① 问题逐答

### Q1 sim 引擎实际调用哪些 decide_* 接口?decide_prep_screen 在 sim 里有没有被调用?

**论断:sim 引擎每个决策段只调两个策略钩子——`update_target` 与 `decide_shop_screen`;`decide_prep_screen` 在整个 sim/ 目录下零调用,sim 完全不驱动备战决策环(PrepAction 词表在 sim 侧零消费)。**

证据链:

- `sim/engine_p1.py:926`:`strat.update_target(st, sess, config)`;`engine_p1.py:937`:`acts = strat.decide_shop_screen(sess, config)` —— 决策循环体内仅此两处策略调用(整文件 2128 行亲读,无其他 `strat.decide_*` 调用点;补给决策 `engine_p1.py:1704-1710` 调的是纯函数 `cw_events.decide_supply`,不经 CwStrategy 接口)。
- 全仓 grep `decide_prep_screen|decide_shop_screen`:sim/ 下命中仅 3 处,全部是 `decide_shop_screen`:`engine_p1.py:937`、`sim/cw_replay.py:240`、`sim/checks/decision_v2.py:177`。`decide_prep_screen` 的调用面全部在生产/装配侧(`operations/cw_screen/cw_screen_prep.py:1193,1351`、`decision_assembly.py` 经 `prep_brain._select`→`strategy.decide_prep_screen` 见 `decision/decision_v2/prep_brain.py:205-211`)。
- 引擎注释自证(`engine_p1.py:927-935`):「sim 决策段 = 商店决策核……旧 decide_prep 薄委托仅作迁移期兼容,离线主路径不再依赖」。

**sim 怎么驱动备战阶段(等价物拆解)**:sim 的「备战期」= 轮内决策段循环(买/卖/升级/刷新/事务)+ 轮末固定管线,**不走 PrepAction 环**:

1. 收入/事件金/投资注入(L720-791)→
2. `update_target` + `decide_shop_screen` 决策段循环 `for _seg in range(8)`(L921),执行 BuyCard/RefreshShop/LevelUp/SellBench/SellDeployed/SwapDeploy/CompTransaction(L990-1312,词表 = `cw_state.Action` 族)→
3. 轮末升级 while 循环(L1315-1318)→
4. **部署 = 引擎直调围栏纯函数** `cw_deploy_logic.select_deployments`(L1399,L1321-1328 注释:「deployed 代理 = deploy_bench 真实围栏逻辑……与 CwOpDeploy op 同一源」)或显式动作轮的残余补部署 `_residual_fill_deploy`(L362-479)→
5. 装备发放/合成/分配(L1640-1814)→ 结算。

即:生产侧备战环里由 `decide_prep_screen` 承担的收球/开箱/开典籍/腾席/单步拖拽决策,在 sim 里**没有等价物也不被建模**(球/箱/典籍在 sim 无实体,见 Q4);部署在 sim 是引擎内置围栏而非策略输出。sim 消费的「策略面」仅 = 商店波决策 + 战略意向(update_target 写 session.target_comp/v3_*)。

结论强度:强(直接代码证据 + 引擎注释自证,无推断环)。

### Q2 商店序列在 sim 里怎么被执行(re-decide / 段数上限 / 截断)?

**论断:序列消费 = 逐动作遍历 + 两个「截断重规划」触发点(RefreshShop、消费店槽的 CompTransaction)+ 四道终止门;段数上限 = 每轮 8 段。**

机制细节(全部 `engine_p1.py`):

- **段循环**:`for _seg in range(8)`(L921)——每轮至多 8 个决策段,注释(L904-909):「每个 RefreshShop 动作后**独立重决策一段**……r273 修:sim 逐动作消费,遇 RefreshShop 执行后立即 re-decide(捕捉『刷到就买』),段数上限防死循环」。
- **段内执行**:拿到 `acts`(list[Action])后 `for a in acts`(L990)逐动作 isinstance 分派执行。
- **截断点 1 = RefreshShop**:执行刷新(扣金/免费额度/产经验,L991-1025)、`_waves.append` 新牌面波后 `break`(L1027「刷后立即 re-decide(见新店)」)——**同段剩余动作全部作废**,外层 `_seg` 进入下一段重新 `decide_shop_screen`。
- **截断点 2 = CompTransaction fill 消费店槽**:`if _applied and _shop_fill_cards: break`(L1306-1312,注释:「事务 fill 已消费店槽——同批后续 BuyCard 是对陈旧 state.shop 的提案,作废并立即重决策(同 RefreshShop 的 break-redecide 语义)」)。
- **终止门**:`acts` 为空 → break(L986-987,空序列 = 决策完成,对应关店);`use_refresh=False` 时滤掉 RefreshShop(L983-985);整段无进展(`progressed=False`)→ break(L1313-1314);8 段用尽。
- **账本披露**:`_segs_used`(L988,段计数)落 `sim.segments`(L1956);刷新次数入 `res.refreshes`/`p2_refreshes`(L992-994)。

**对序列接口升级的直接含义**:现役核一段内返回的序列,遇 RefreshShop/事务 fill 后**尾部静默作废**——这是 sim 与生产共同的语义(生产 = `cw_screen_prep.py:1595` 注释「decide_shop_screen → 执行至首个 RefreshShop → 重判,MAX_REFRESH 硬墙」)。新核发射 list[PrepAction] 序列时,**序列内 RefreshShop 之后的动作是否保留/重排,必须在接口契约里显式定义**;sim 侧现状 = 截断丢弃 + 重新整段决策。

结论强度:强(逐行证据)。

### Q3 换核 A/B:sim 侧需要什么接线才能公平对拍?

**论断:sim 侧已具备换核 A/B 的全部基础设施——`simulate_p1(strategy=...)` 注入参数 + 同 seed 配对双臂先例;序列接口消费者挂在唯一调用点 `engine_p1.py:937`;单动作核包长度 1 序列的适配器在 sim 侧零成本(消费者是泛型 list 遍历);行为等价性判据 = 同 seed+同池指纹+同注册表视图下账本逐位相等(零漂移门,引擎 docstring 自证此门先例)。**

证据与推理链:

- **注入点**:`simulate_p1(..., strategy=None, session=None, config=None, ...)`(`engine_p1.py:483-492`);默认构造 `DecisionV2Strategy(registry=sim_decision_registry())`(L559-565)。注意注入桩策略无 `registry` 属性时观测键回退 sim 视图(L566-569)——新核**建议带 registry 属性**,否则 `_round_p1_downgrade` 等观测键走回退路径(行为不受影响,但观测口径混)。
- **A/B 配对先例**:`runner.simulate_p2_ab`(`runner.py:531-604`)同池同 seed 双臂、两臂 strategy 均以 `sim_decision_registry()` 派生注册表构造(L556-561),`logging.disable` 静音(L554);`simulate_p1_ab`(`runner.py:498-527`)为 use_refresh 双臂样板 + 分辨率底 `check_ab_resolution_floor`。换核 A/B 应复制此形态:同 seed_base、同 pool、同 planes、同 invest/p2_combat/synthesis_chain/equip_wear_effect 参数。
- **序列消费者挂哪**:`engine_p1.py:937` 是 sim 内 `decide_shop_screen` 唯一调用点;`cw_replay.py:240` 与 `checks/decision_v2.py:177` 是另外两个离线消费点(见 Q5)。
- **单动作核 → 长度 1 序列适配器零成本**:sim 消费端只做 `for a in acts` + isinstance 分派(L990 起),不感知序列长度/来源;适配器(`decide_shop_screen` 返回 `[action]` 或把旧单动作循环拍平)在 sim 里零额外执行成本、零 RNG 消耗差异——**前提是适配器本身不消耗额外随机数且决策时点不变**(同一段一次调用)。
- **行为等价性判据**:引擎 docstring 明确零漂移门先例——「planes=1 九轮(默认,**逐位不变**——回归门=旧代码同 seed 同池 diff={})」(`engine_p1.py:499-500`);公平对拍判据建议见 ③节。
- **坑位提示**:①RNG 流——`StrategySession` 的 rng 由 seed 派生(`engine_p1.py:607-608`),决策核若消费 rng 会改变配对性,新核/适配器须 rng-neutral 或双臂同耗;②`sim_decision_registry()` 的 `level_max=LEVEL_CAP(9)`(L341-358)是 sim 环境语义,两臂必须同注册表视图;③`sess.expected_state = {}` 离线口径(L626)与 `sess.shop_state_frame = st` 帧写(L936)是 sim 侧黑板契约接线,新核若改读别的帧须同步(见 Q4)。

结论强度:强(机制逐条有行号;「适配器零成本」以不耗 rng/不改调用时点为前提,是构造性论证非实测,标中强——首跑须用零漂移门实测验证)。

### Q4 sim 的输入构造:GameState/session 怎么喂给策略?新核额外输入从哪来?

**论断:sim 有三条喂入路径——①引擎合成(主路径,从头构造 GameState + seed 派生 session);②cw_replay 回放器(decisions.jsonl 快照重建 GameState);③checks 探针(手搓 GameState 直接调接口)。新核若只需要 GameState 域数据(金/板/bench/shop/等级/hp/streak)则零新增输入面;若需要 PrepObservation 域实体(球/箱/典籍/物理槽位),sim 无实体,必须走合成器 `synthesize_snapshot` 或显式声明边界。**

证据:

- **引擎合成(主路径)**:`GameState()` 全新构造,`plane/level/gold/hp = 1,3,5,80`(L588-589),开局 bench 采样 4 张(L592-603);`sess = StrategySession(rng=random.Random(f'sim-p1-{seed}'))`(L607-608);观测态补齐(`hp_trusted=True` L616、`st.streak` L619-620、`sess.expected_state = {}` L626、`sess.v2_state` L609、`sess.node_type_current` L719、P2 进场的 `plane_node_table`/`plane_lengths_seen` L696-710、结算后 `sess.last_streak`/`st.streak` L1619-1620)。**黑板帧接线 = `sess.shop_state_frame = st`(L936)**,写者白名单注释自证 sim 引擎是合法写者(`kernel/cw_strategy_session.py:315-316`「写者白名单 = buy_cards.run_buy_waves 波顶融合段 / 兼容期旧接口 sim 引擎(独立批)。读者 = decide_shop_screen」;对称地 `prep_obs_frame` 写者白名单 = `cw_screen_prep._observe`/破警告派生帧/旧接口薄委托,**不含 sim**——`cw_strategy_session.py:300-309`)。
- **回放器 `cw_replay.py`**:`_rebuild_state`(L52-88)从 `replay/decisions.jsonl` 的 state dict 重建 GameState(bench/deployed 经 `bench_from_compact`/`deployed_from_compact` 转槽位表),`_restore_session`(L149-162)恢复 session 派生态;`sess.shop_state_frame = st` 后 `strat.decide_shop_screen(sess, _Cfg())`(L239-240)。角色 = 对历史局快照秒级重放决策、`--diff` 与当时实跑对比(L1-31 docstring)。
- **checks 探针**:`sim/checks/decision_v2.py:160-177` 手搓中局 GameState + 裸 `StrategySession`,写帧后直接调 `decide_shop_screen`,锁遥测契约(候选分键格式/轮次戳等);`checks/decision_v2.py:40-66` 锁候选生成覆盖。
- **合成器**:`runner.synthesize_snapshot(st)`(`runner.py:886-959`)GameState→Snapshot(阶段2契约),sim 真值契约注释(L895-902):「spheres/boxes/tomes 恒空元组、event_overlay=None、box_overlay_open=False(sim 无交互面实体,决策域在 shop 开态)」——**这是新核额外输入的硬边界**:PrepObservation 的实体域(spheres/boxes/tomes/free_bench_slots 语义/物理槽位)在 sim 无真值源。
- skill 边界佐证:`sim-testing.md:11-12`「代理近似:`st.deployed` 代理名单……」与「未建模:装备效果、星级……」——球/箱实体未列因其根本不进 sim。

结论强度:强。

### Q5 sim 侧为序列接口需要新增/修改的面(文件级清单)+ 不需要动的面

**需要动(若新核仍经 `decide_shop_screen` 商店路径换核)**:

| 文件 | 位置 | 动什么 | 理由 |
|---|---|---|---|
| `sim/engine_p1.py` | L937 | 无需改动接口本身;仅当新核序列内含「截断语义变化」(RefreshShop 后保留尾部动作)时,需在 L1027 break 处按新契约调整 | sim 内 `decide_shop_screen` 唯一消费点;序列 list 遍历天然兼容 |
| `sim/runner.py` | 新增/扩展 `simulate_p2_ab` 形态的换核 A/B harness(样板 L531-604;或 `simulate_p1_ab` L498-527) | 双臂 = 现役核(经长度1适配器)vs 新核,同 seed_base/pool/planes/注册表 | 现有 AB 函数都是参数双臂(use_refresh/flag),没有「策略对象双臂」的通用入口(simulate_p2_ab 是私有先例) |
| `sim/cw_replay.py` | L239-240 | 若接口签名/帧契约变化,回放须同步(帧写 + 调用形态) | 第二消费点;换核后回放应能跑新核做历史局分歧判读 |
| `sim/checks/decision_v2.py` | L174-177 | 探针若锁新接口契约(序列形状/长度上限/截断不变式),在此加锁 | 第三消费点;决策契约的常态防线 |

**若要把备战序列接口(list[PrepAction])本身拉进 sim 消费**(即 sim 也要跑 prep 决策段):额外需要——

| 文件 | 动什么 | 理由 |
|---|---|---|
| `sim/engine_p1.py` 决策循环 | 新增 prep 段调用点(写 `prep_obs_frame` 等价物 → 调 `decide_prep_screen` → 执行 PrepAction 序列,需自建 PrepAction 执行语义:ClickSpheres/OpenBox/DeployMove 等在 sim 的效果模型) | 现状 sim 零消费;球/箱/典籍无实体(L895-902 契约 + sim-testing 边界),**这是行为建模扩张而非纯接线**,成本与失真风险高,建议换核 A/B 不走此路(商店路径已覆盖买/卖/升级/刷新/事务全经济决策面) |
| `kernel/cw_strategy_session.py` L300-309 | 若 sim 成为 prep 帧写者,写者白名单注释与字段契约同步 | 文档单一源纪律 |

**不需要动**:

- `sim/engine_p1.py` 动作执行层(L990-1312):BuyCard/LevelUp/RefreshShop/Sell/事务分派对序列来源无感;`LevelUpShop is-a LevelUp` 出口映射已在决策核内(`decision_v2/strategy.py:318-333`)。
- 部署围栏(L1321-1442)、`_residual_fill_deploy`:引擎内置,不经策略接口。
- `sim/pool.py`(Δ 池/池指纹)、`sim/engine_p2.py`(仅 TYPE_CHECKING 引用,共享循环体)、`sim/cw_sim_invest.py`、`sim/ledger_hooks.py`、`sim/checks/{pool,corpus,segments,ledger,calib,runtime}.py`(账本消费,不触决策接口)。
- `decision/cw_strategy.py` ABC 之外的生产装配(`decision_assembly.py`/`cw_screen_prep.py`):换核+升序列的接口本体改动在决策域,sim 对拍不需要动它们。

---

## ② sim 侧序列接线需求清单(文件级汇总)

按「商店路径换核 A/B」最小集:

1. `sim/runner.py` — 换核 A/B harness(双 strategy 臂,样板 `simulate_p2_ab`);复用 `check_ab_resolution_floor` 报噪声带。
2. `sim/engine_p1.py:937` — 消费点保持;若序列截断契约变更(RefreshShop 后保留尾部)才动 L1027。
3. `sim/cw_replay.py:239-240` — 新核回放支持(接口/帧契约同步)。
4. `sim/checks/decision_v2.py:174-177` — 新接口契约锁(序列形状/截断不变式/遥测契约延续)。
5. (可选,不推荐首期)`engine_p1.py` prep 段仿真 + PrepAction 执行语义 + `cw_strategy_session.py` 白名单注释——仅当要求 sim 直接消费 `decide_prep_screen` 序列时;球/箱实体缺失是硬边界。

## ③ 公平对拍判据建议

1. **环境恒等**:同 seed_base/同 n、同 pool 且核对 `pool_fingerprint`(含 `+eqg` 位,`engine_p1.py:641`)、同 `planes`、同 `use_refresh=True`、同 invest/p2_combat/synthesis_chain/equip_wear_effect 缺省、双臂 registry 均自 `sim_decision_registry()` 派生(`engine_p1.py:341-358`)。
2. **零漂移门(先于 A/B)**:现役核 vs 「现役核包长度1序列适配器」,同 seed 同池,**SimResult.ledger 逐位相等**(先例:`engine_p1.py:499-500` planes=1 回归门 diff={})。此门红 = 适配器引入了额外 rng 消耗/调用时点漂移,先修适配器再谈 A/B。
3. **统计 A/B 门**:新核 vs 适配器臂,配对差值过 `check_ab_resolution_floor`(`runner.py:526` 先例);主判据沿用既有 sim A/B 门基线口径(B1 avg_final_hp n500 / B2 p2_hp0 n300,基线 `.debug/temp/currency_war/sim_baseline_20260902_v3/`),|Δ| < 底 = 噪声带内不得叙述方向性结论(`runner.py:500-506` 纪律)。
4. **序列语义披露**:新核批次的账本 `sim.segments`(L1956)与刷新/截断相关计数(refreshes、explicit_action_rejects、phantom_rebuys)对旧基线对照——截断契约变化会先在这些计数显影,先解释计数漂移再解释 hp。
5. **rng 中立性**:新核/适配器不得消费局内 rng 流(`engine_p1.py:604-608` 会话流派生注释是契约);若必须消费,双臂同耗并声明。

---

### 附:关键证据行号速查

| 论断 | 证据 |
|---|---|
| sim 唯一决策调用点 | engine_p1.py:926(update_target)、937(decide_shop_screen) |
| decide_prep_screen 在 sim 零调用 | grep 全仓:sim/ 下仅 shop 接口 3 处(engine_p1:937 / cw_replay:240 / checks/decision_v2:177) |
| 段循环 8 段上限 | engine_p1.py:921 |
| RefreshShop 截断重规划 | engine_p1.py:991-1027(break@1027) |
| 事务 fill 截断 | engine_p1.py:1306-1312 |
| 部署走围栏不经策略 | engine_p1.py:1321-1328、1399 |
| 零漂移门先例 | engine_p1.py:499-500 |
| sim 帧写者白名单 | cw_strategy_session.py:300-317 |
| 回放器 | cw_replay.py:52-88、239-240 |
| 合成器 + 实体缺失边界 | runner.py:886-959(895-902) |
| AB 配对样板 | runner.py:498-527、531-604 |
| sim 边界(skill 主线) | .dsh/skills/sr-od-currency-war-dev/references/sim-testing.md:7-15 |
