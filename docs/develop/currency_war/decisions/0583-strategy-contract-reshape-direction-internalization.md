# ADR-0583: 策略契约重塑——CwStrategy 去策略专属语义(方向节拍内化 + 生命周期收编)

日期:2026-09-08;状态:已接受
关联:ADR-0517(画面 op 规范,裁定 1 来源)/ADR-0563(策略器状态工厂与 B4 收缩,create_state 保留依据)/ADR-0579(候选评分遥测供数,键守卫段内平移)/`docs/develop/currency_war/flow/README.md`(四身份分离/黑板单一写端,§2 同步重写);方案 = `.debug/temp/currency_war/t119_strategy_contract/方案.md`(v2,零阻断)+ 方案审 v2(0 阻断 + 3 低随批)

## 1. 背景与问题

`CwStrategy` ABC 的接口面是历史增量堆积的结果:「17 接口」口径(4 生命周期 + 1 战略层 + 3 序列决策 + 9 pick)中混入了大量**某具体策略实现(mandate_v1 前身)的内部构造**:

1. **`update_target` = 方向重估的流程侧直调口**:生产三处 ops(cw_screen_prep:1414/:2271、cw_op_buy_cards:605)+ sim 一处(engine_p1:1238)在**自己选定的时机**调用它——流程侧持有「方向节拍知识」(何时重估/以什么为输入),违反 ADR-0517 目标模型(op 的策略接触面 = 入口观察 + 策略器单动作循环)。伴生病灶:方向驱动的 hp 输入 = 备战入口**血条现读**(`cw_screen_prep:1405` drive_intention 先于 `:1411` gated_hp 覆写执行),与商店线(buy 前已吃结算门)形成同节点双 hp 基准——r68 同门病灶族(「先调方用假 hp 判 pivot、后调方真 hp 反向 pivot」)。
2. **生命周期四钩子与冷建重叠**:`MandateState` 每局冷建三条路径(create_session 工厂接线 / on_match_start 无条件重建 / CurrencyWarMatch.__post_init__ 兜底附着),live 路径**每局建两次**(建一次被 on_match_start 丢弃重建);on_match_end = P1 no-op 死钩子;on_round_end 混装观察数据(结算真值)与策略器内部加工(掉血 tracker/谷底回滚)。
3. **分画面决策入口不全在 ABC**:pick 族 9 个中 4 个(decide_planner/star_tome/wish_trial/box_card)只在 flow 层,生产商店入口 decide_shop_action 也在 ABC 外——「ABC = 各画面 op 需要调用的决策入口」的契约形状名不副实;decide_prep_action deprecated 薄委托与 decide_shop_screen 序列兼容驱动器滞留 abstract 面。

裁定来源(用户在案):①ADR-0517 画面 op 规范(目标模型);②基类去策略专属语义——`update_target`/意向 target 机器是 mandate_v1 基线的设计自陈(「透传声明」),换一个策略实现未必有 target 概念,**基类契约 = 各画面 op 需要调用的决策入口(分画面)**;哪个画面在什么时机重估什么方向/状态,全部是具体策略实现的私事。

## 2. 决策

### 2.1 新契约形状(抽象 12 + 非 abstract 工厂 1 = 保留总成员 13;独特方法面 20)

```
CwStrategy(ABC)
├─ 冷建(2):create_session [abstract,唯一冷建口] / create_state [非 abstract 工厂,ADR-0563 B4]
├─ 备战画面(1):decide_prep_screen [abstract]
├─ 商店画面(1):decide_shop_action [abstract,本批升格]
└─ 事件画面 pick 族(9):decide_invest/supply/encounter/megastar/partner/
   planner/star_tome/wish_trial/box_card [abstract,本批补齐 4 个]
```

删除/降格:`update_target`(删)、`on_match_start`/`on_match_end`(删)、`on_round_end`(删,职责拆两半)、`decide_prep_action`(删,deprecated 兑现)、`decide_shop_screen`(降格为 flow 层非 abstract 缺省驱动器 + bridge 覆写,sim/回放/序列锁消费形态不变)。注册面封闭集 = {mandate_v1},第三方实存 = 0,破坏面 = 零(ADR-0563 B4 适用性复核:create_state 缺省 None 条款不变)。

独特方法面 = 20(ABC 14 + flow 独有 6;契约相关 19 = 20 − write_shop_mirrors 内部方法)。旧「17 钩子/21」口径系重复计数与口径外成员混入,以代码实存面为准。

### 2.2 方向节拍内化(`_refresh_direction`,策略器私有非契约)

- 删除全部流程侧直调点(ops 三处 + sim 一处 + drive_intention 一处);方向重估收进 `CwFlowStrategy._refresh_direction`(逐字平移原 update_target 两段:键守卫贵段 = `update_intention` + 候选评分遥测,每 game-round 恰一次;便宜段 = 派生视图刷新)。幂等键 `v3_intention_key` 持有者 = MandateState(实现包私有),流程侧/sim/框架零接触;kernel `drive_intention` 本体不动、生产调用点清零、键守卫保留作纵深防御。
- **触发信号 = 黑板帧刷新代次标注**(不扩 GameState/PrepObservation 本体):`session.prep_frame_class`/`shop_frame_class` ∈ {'full','view','none'},缺省 'none'。触发面 = 备战入口 + 商店入口 + pick 族 9 入口(11 调用 op、12 调用行;方案审 Z1 裁决:finalize 买后 `_post` 暂存为黑板帧标 'view',pick 入口消费——把原 `:2271` 同一次写的调用形态改为帧消费形态,键面/基底/幂等键行为逐位同源)。写者 = 流程观察段具名写点(cw_screen_prep 入口 heavy='full'/破墙='view'/投影='none'/read_only 分支='none'/finalize 暂存='view';cw_op_buy_cards 商店首段='full'/续段='none';sim 每段='full');读者 = 策略器入口刷新,**读后即复位 'none'**。
- D6 边界口径(实施裁决,如实申报):「驱动器不写帧类槽」辖**新鲜度宣告写点**——策略器/驱动器实现包内零 `'full'/'view'` 标注写点(守卫锁 = 契约形状锁正则);消费侧「读后即复位 'none'」是读协议半部,非新鲜度宣告,落在 flow.py 读口内。空间守卫锁钉死两槽的出现文件白名单(载体定义/三流程观察写点文件/策略器读口)。

### 2.3 生命周期收编

- **create_session = 唯一冷建口**:工厂接线(既有)+ live 初值 `v3_phase='FORM'`(原 on_match_start 唯一非零缺省迁此;工厂产物保持 '' — sim 直构 session 读数保真)。on_match_start/on_match_end 删除,调用点(cw_loop:1226/:2351)删除。
- **on_round_end 拆两半**(数据归属判据:结算真值归观察、策略器加工归策略):观察半 = `performance.record`/`last_streak`/`last_hp`(过 `HP_CONFIDENCE_THRESHOLD` 门,门随迁)/`last_hp_t`——battle_wait 结算点**即时直写**(写点与原调用同点同时序,`performance.history` 无缺行窗口;streak 即时写是备战帧对账锚的硬前提);策略半 = 掉血三臂喂入/node_type 回落/谷底回滚登记/`v3_prev_hp`——`session.pending_round_outcomes` 待加工槽(观察层追加)+ 策略器下一决策入口惰性 drain(flow 层 `_drain_pending_round_outcomes`,处理即清)。零行为差依据:四字段族(v3_alarm/v3_pending_rollback/v3_prev_hp 及其加工)src 内零行为读端;`VALLEY_ROLLBACK_LOSS` 已裁定退役,本批只搬运不删除。

### 2.4 驱动输入 hp 门统一(行为收敛,编排者裁决采纳方案审修法②)

v1 曾断言「方向层全域不读 hp」——系 grep 假阴性(`getattr(state, 'hp', 0)` 字符串属性形态绕过 `\.hp` 模式;亲证 3 处:cw_intention.py:910-911/1080/1358,消费链 `p2_supply_horizon` → `line_completion_feasibility` 视界 → 全部 plane==2 判据全程活跃)。**现状时序差确凿**:生产路径 drive_intention 先于 gated_hp 覆写执行 → 状态机驱动吃 pre-gated(血条现读)hp;内化后驱动发生在决策入口,吃 post-gated(结算门)hp。

**裁决 = 统一到 gated 门,作为显式申报的行为收敛**(本批唯一非零行为差):与 gated_hp docstring 的 r68 教训同向(「消费方必须同门」)——商店线 buy 前已吃 gated 门,方向驱动并入同门,消除同节点双 hp 基准病灶族。行为差窗口 = 备战血条现读 ≠ 结算 hp 的轮(OCR 误读轮)∩ P2 hp 判据阈值边缘翻转,域限 plane==2,概率性。同键守卫段内的候选评分遥测列(`_telemetry_last_candidate_scores`)随同一 hp 输入同步移门(方案审 L-a 采纳)——误读轮的分值差属申报面判读差异,非漂移。

**该域对 sim 对照结构性免疫**(sim 零 gated_hp 引用、hp 恒真值,engine_p1:692 直接赋值,pre/post 两态输入同值)→ sim 零漂移只承载结构等价;收敛由本申报 + L7 门锁 + 当期迭代判读注记承载。

## 3. Considered Options(驱动输入 hp 门,最值钱栏)

| # | 方案 | 裁决 | 理由 |
|---|---|---|---|
| ① | 保留 update_target,只改调用形态(ops 内聚到一处) | **否** | 违裁定 2(ABC 策略专属语义必须出基类);流程侧仍持节拍知识 |
| ② | 方向刷新留在 flow 层,以函数注入供 ops 调用 | **否** | 流程侧仍决定「何时刷新」= 节拍知识未出流程侧 |
| ③ | 结算半纯 lazy-drain(观察字段一并惰性化) | **否** | 观察对账锚时序被破坏:`session.last_streak` 是备战帧 streak 权威/对账源(cw_observation:2199-2213),惰性化则下一入口观察读到旧值 → obs_conflict 误报(硬证据在案) |
| ④ | 驱动输入 hp 保 pre-gated(入口前暂存现读) | **否** | 为保「零行为差」引入时序连锁复杂度,且与 r68 教训的「消费方同门」方向相悖——现读 hp 在误读轮是假值 |
| ⑤ | **方向驱动输入统一到 gated 门(采纳)** | **采纳** | 治 r68 同门病灶;行为收敛显式申报 + L7 门锁承载;与「零调参/数学先行」无冲突(不引入任何新数值) |

## 4. 等价性判定与 sim 可观测性声明

本批判据 = **结构等价 + 一处显式申报的行为收敛(§2.4)**。结构等价 = 决策行为(动作序列/选线结果)结构域逐位等价。**实际证据集(落地审 M1 裁定口径②改写)**:①行为锁 L1-L7 全绿(方向节拍/窗口帧/商店段/冷建唯一/结算拆两半/契约形状/驱动输入门);②既有行为锁全集绿(快速层 3070 / 全量 3593+1 家底红);③改后同 seed 双跑自洽(PYTHONHASHSEED=0,digest 逐位一致——证明确定性未被重构破坏,**不构成与改前的等价证据**);④代码级逐调用点等价论证(§2.2/§2.3/§3.3-sim 各节);⑤**改前/改后 sim 批对拍与 `cw_replay --diff` 本批未执行**(实施批禁 git 无改前基线,如实申报)——补做义务已折入 **T-120 批 1 保真度基线对拍**(进度账本在记)。分域申报:

- **sim 可见域**:契约/调用结构层(sim 决策链 = decide_shop_screen 驱动器 + 内化刷新)——sim 零漂移可作等价证据。实施注:sim 采购面三观察块后移到 decide_shop_screen 之后(旧序 = 战略层直调先于观察块;内化后刷新发生在驱动器首帧消费,后移保持「读数 = 本段入口态刷新后视图」语境逐位不变)。
- **sim 结构性不可见三域**:①驱动输入 hp 门(§2.4,sim 免疫);②破墙窗口(live-only 模态,等价性由锁 + 代码级论证承载——破墙 view 帧以自身 .state 刷视图,replace 保真 = 买后物理真值,视图值等价);③结算惰性化(sim 自写 last_streak,不走 battle_wait 观察半)。

判读面显式差异(非行为,ADR-0579 同族):甲 phase 列 '' → 'FORM' 翻转两路径(cw_replay 回放 + cw_op_buy_cards 防御路径,诊断列);乙 意向事件日志行触发时点收拢到决策入口刷新(买后日志行后移一拍,内容不变;**扩**:cw_op_buy_cards 段顶 state 日志行的 target/fp 列与 decisions 行同段首帧值变为上一刷新点值——刷新时点内化的同族判读差);丁 破墙窗口方向视图观察基底 = 入口 OCR 读(原 tracked 重播账;物理同源)。方案审三低随批落实:L-a 候选评分遥测移门申报(§2.4);L-b finalize 暂存帧 `prep_obs_frame` 缺席守卫(0n 直入商店路径显式跳过,该窄窗 pick 退回 'none' 类)+ 暂存帧仅 state/帧类两字段有消费合法性(现帧其余 OCR 列相对 _post 已陈旧,禁扩读);L-c overlay 反弹子路径并入丁(经备战入口 overlay 防线反弹的 pick 消费入口 heavy full 帧,基底 = 入口 OCR)。

## 5. 边界申报(明确不在本批)

1. 换线标定激活(θ/U_X/V_ms 注入/W 触发)= 另行批次;本批保证内化后「标定到位即可在策略器内激活」。
2. `VALLEY_ROLLBACK_LOSS` 退役:本批原样搬运进惰性 drain(含零读端死写),删码归既定退役批。
3. sim 游戏孪生化(破墙/模态建模):本批只做调用面收敛。
4. `decide_prep_screen` 的 list 返回形态保持(单动作循环取首项);备战决策收单动作签名属后续契约迭代。
5. **实施批新发现窗口(编排者已裁决归收敛族,申报终文本见 §5.5)**:finalize 暂存帧的消费者 = 决策入口(pick/备战),但 loop 层**达标臂**(readiness_launch_decision,cw_loop:1700)与「前台无角色」恢复链(CwOpDeploy)在「买后 → 下一决策入口前」的窗口读 `target_comp` 不经任何决策入口——旧形态 :2271 立即重估喂它们,新形态读到上一刷新点视图。可达性收窄:P2+ 锁定帧 target 与 state 无关(无差),窗口域 = P1 未锁帧 ∧ 买翻 p1_early_pair ∧ 达标臂同迭代评估,且旧形态该窗口的判定输入本就是「新 target × 旧 last_state(段顶快照)」混合新鲜度,差异方向不单调;sim 不可达(sim 每段消费 full 帧)。处置 = 并入 §2.4 收敛族申报(编排者裁决);达标臂判定改经策略入口已立为架构跟进任务(与 T-121 op 化同族),后续批次处置,不属本批。

### 5.5 行为收敛申报(§2.4 + §5-5 合并终文本,编入当期迭代判读注记)

本批行为收敛族共两条,均为有意收敛、非漂移:

1. **方向驱动输入 hp 门统一**(§2.4,L7 门锁承载):意向状态机每轮驱动输入 = 备战血条现读(pre-gated)→ 决策入口帧 state(post-gated,结算新鲜度门放行值);同键守卫段内候选评分遥测列(`_telemetry_last_candidate_scores`)随同一 hp 输入同步移门。域 = 血条现读 ≠ 结算 hp 的轮(OCR 误读轮;r68/r69 实证该类轮真实发生)∩ P2 hp 判据阈值边缘翻转(`p2_supply_horizon` → `line_completion_feasibility` 视界 → P2 移交强锁候选门槛/信号缓锁门/撤销出口③),限 plane==2,概率性。方向 = 消除同节点双 hp 基准(r68 同门病灶族)。sim 对本域结构性免疫(hp 恒真值,pre/post 同值)。
2. **finalize 暂存帧 × 达标臂/恢复链窗口**(§5-5):买后方向视图从「finalize 时点立即重估」变为「下一决策入口消费暂存帧刷新」——loop 层达标臂与前台无角色恢复链在该窗口读 `target_comp` 为上一刷新点值。域 = P1 未锁帧 ∧ 本次买入翻转 p1_early_pair ∧ 达标臂/恢复链在同迭代(下一决策入口之前)评估;方向 = 非单调的混合新鲜度差(旧判定输入 = 新 target × 旧 last_state 段顶快照,本就非同源新鲜),非系统性回退;sim 不可见(sim 每段消费 full 帧)。判读注记:该窗口内达标臂评估行若与买前面貌不符,归本收敛申报,不立漂移案。

## 6. 实施面与验证

- src:ABC 重塑(cw_strategy)、flow 内化/收编/驱动器缺省、bridge 覆写收缩、session 三新字段(prep_frame_class/shop_frame_class/pending_round_outcomes,带定义注释)、cw_screen_prep 四迁移点 + 帧类写点、cw_op_buy_cards 段帧标注、engine_p1 观察块后移 + 段帧标注、cw_loop 调用点删除、cw_screen_battle_wait 观察半直写(`_write_settlement_observation` 单一写点);src `update_target` 48 处 grep 全量逐处过(4 调用 + 2 定义链 + 42 注释/docstring;engine_p1:1225/1240/1801「买后已刷新」行为契约锚改写为新锚)。
- 测试:18 处桩迁移(逐锁重推语义);新锁 L1 方向节拍/L2 窗口帧(含买后 pick 窗口)/L3 商店段/L4 冷建唯一口/L5 结算惰性消费(幂等 + 死亡局末战 history 行)/L6 契约形状(abstract 12 + 墓碑 + 键面与帧槽空间守卫 + D6 正则)/L7 驱动输入门(钉住 gated 新行为)。
- 验证(实际执行集):ruff 全绿;CW 快速层全量(3070/0);全量套件(3593 passed,既有红家底 = test_id_mark 恰 1);行为锁 L1-L7 全绿;sim 同 seed 双跑自洽。**改前/改后 sim 对拍补做义务折入 T-120 批 1 保真度基线对拍(账本在记)**;实机流程检查随当期实机局进行。
