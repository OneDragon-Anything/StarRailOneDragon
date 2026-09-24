# 遭遇迁移设计 对抗审查报告

> 审查对象:`changes/2026-09-24-encounter-screen-strategy-migration/design.md`(187 行,状态「草案(对抗审查前)」)+ 同目录 README.md。
> 审查方式:无前提三核(核一自由攻击 + 核二规范 + 核三治本);判据源全部直调——现役代码逐符号 read/grep,裁定/证明/节点表/画面知识逐篇 read,数值逐个复算。发现共 16 条(高 2 / 中 8 / 低 6),文末附零发现面申报。

## 发现清单

### F1 [严重度:高] 裁定 9 的授权辖域被过度引申为「判据结构经用户授权在案」
- 位置:design §2.2 设计原则段(「其三态表/经验层/tiebreak/阀门结构经用户 2026-09-12 授权在案」)
- 发现:直调 `strategy-docs/04_survival_budget.md` §7 表第 9 行——授权状态「已授权(用户 2026-09-12 逐项确认…)」的消费形态列 = **「结算屏现成读数(含我方掉血分量 B/P)作遭遇决策输入 + 结算观测数据入 GameState 持久化(结算观测环深度 10)」**,依据列 = 「v1 判据辖域 = 敌方通道(killed/进度填充率)…判据正本 = `kernel/cw_encounter_selection.py`」。即裁定 9 逐项确认的对象是**数据输入通道与持久化**,「判据正本 = 本模块」是载体登记;κ_S 三态表、边缘态 cap=2、经验档层放行、刷新阀、以及「钻>装备>金币>末档」偏好序这些**判据结构本身**(激活后进决策门的值/序)不在该行授权文字辖内。设计稿把载体登记读作结构级授权,依据强度与裁定原文不符——这批结构正是「换一套策略实现会不会要不同的值/序」的典型策略立场内容(宪法五判据线),激活后它们的合法性载体悬空。
- 修正方向:二选一并写入 §2.2/§2.9:(a)补结构级用户裁定登记(同补给批「三级优先」的用户裁定指针形态);或(b)照补给批 §2.3 先例申报「确认载体 = 对抗审查」,并把 cap=2、四档偏好序按 01_math_framework §6 作形态申报(立场序结构,非加法【拍】值,zero 数值立场如实落字)。禁保留「经用户 2026-09-12 授权在案」的现有表述。

### F2 [严重度:高] 「动作 op 改吃 EncounterPickDecision」与同节「零行为改动」自相矛盾,且并非补给批先例的同款处理
- 位置:design §2.6 消费面清单「动作 op 入参(operations/cw_op/cw_pick_encounter_action.py——与补给批 SupplyPick→纯值载体的同款处理:动作 op 改吃 EncounterPickDecision,取 idx 字段语义不变)」
- 发现:直调 `cw_pick_encounter_action.py:54-55`——动作 op 构造签名 `param: CwActionPickEncounterParam`,现役吃的是**词表动作**,从来不是 kernel `EncounterPick`;生产派发链 `cw_screen_encounter.py:250` `action_op_for(act, ...)` 传入的也是词表动作。若按设计稿「改吃 EncounterPickDecision」,与同节「词表、op handler(cw_screen_encounter)、观察写槽、终结链**零行为改动**」直接冲突——接口契约两处互斥,实现者无法同时满足。且「同款处理」是对先例的误述:直调补给批 design §2.1,其对 SupplyPick 的处理 = 「flow 鸭子式字段消费 + `cw_vocab`/`cw_pick_supply_action` docstring 提及收口 + 测试仓类型 import 随删」,**没有**「动作 op 改吃纯值载体」一说。(测试仓 `test_cw_unified_action_4.py:259/278` 把 `EncounterPick` 实例 duck-typing 传给动作 op,是测试构造 convenience,不是生产契约。)
- 修正方向:该消费面项改写为「动作 op 零改动(继续吃词表动作 `CwActionPickEncounterParam`,idx 鸭子式消费);`test_cw_unified_action_4.py:259/278` 的 `EncounterPick` 实例构造点改传词表动作实例(与生产派发同型)」——并与补给批先例语义对齐。

### F3 [严重度:中] `EVENT_PICK_TYPES`/`EventPick` 的 `EncounterPick` 位漏列删除面(与补给批先例直接对照)
- 位置:design §2.6(「消费面全列」)/ §2.7(cw_events 删除面)
- 发现:直调 `kernel/cw_events.py:538-540` `EVENT_PICK_TYPES: tuple = (EncounterPick, MegastarPick, PartnerPick, PlannerPick)` 与 `:543` `EventPick = EncounterPick | MegastarPick | PartnerPick | PlannerPick`——两处为**模块级运行时构造**,`EncounterPick` 类定义删除后本模块 import 即 NameError。设计稿两处均未列这两个符号;而同构先例补给批 design §2.6 明确列了「`EVENT_PICK_TYPES` 元组该位(:1003)与 `EventPick` 联合别名该位(:1007)」——同款操作在先例是显式删除面成员,本批漏列,「消费面全列」声明与事实不符。
- 修正方向:§2.7 cw_events 删除面补「`EVENT_PICK_TYPES` 元组 `EncounterPick` 位与 `EventPick` 联合别名 `EncounterPick` 位随删(现址 :538-540/:543,符号锚)」。

### F4 [严重度:中] EV 核「保留」分支与 `EncounterPick` 无条件退役不兼容,保留代价清单漏算载体改形账
- 位置:design §2.6(EncounterPick 退役,无条件)/ §2.7 / §2.10 裁定点 1 保留分支
- 发现:直调 `strategies/impl/mandate_v1/encounter.py:79-82`——EV 核**顶层运行时 import** `EncounterOption, EncounterPick`,且 :264/:268/:280/:306/:308/:387 六处签名注解与实例构造消费之。§2.6/§2.7 对 `EncounterPick` 的退役不以裁定点 1 为条件;若用户裁「保留」,encounter.py 原样保留则 import 直接断。§2.10 保留分支的处置只有「本条跳过、模块头补明示」,未覆盖 EncounterPick 依赖;保留代价清单(「永不激活的判据本体 + 双标定槽 + 测试锁长期随仓」)也未含「EV 核载体须同步改形」这笔账。
- 修正方向:§2.10 裁定点 1 保留分支补一条「`encounter.py` 的 `EncounterPick` 依赖同步改形(私有载体或 TYPE_CHECKING 化+改注解),随裁定结论落地」;或在 §2.6 把 EncounterPick 退役并入裁定点 1 条件。

### F5 [严重度:中] fill 分支与 `_FILL_EDGE_THRESHOLD` 的层次归属在 §2.1/§2.3/§2.7 三处之间不自洽
- 位置:design §2.1 随迁列表 / §2.3 保留两槽段 / §2.7 cw_encounter_selection 删除面
- 发现:§2.1 随迁列表含「κ_S 能力态三态表」;现役 `_kappa_state`(`cw_encounter_selection.py:297-323`)的「恰一胜败局 fill 分支」是三态表函数体的一部分,消费模块级 `_FILL_EDGE_THRESHOLD = 0.5`(:285)与保留槽 `BAR_SEMANTICS`/`PROGRESS_BAR_DIRECTION`(:58-61)。§2.3 说「`_FILL_EDGE_THRESHOLD` 常量与 fill 分支代码保留(定谳后激活)」但未说保留在哪一层;§2.7 删除面不含 `_FILL_EDGE_THRESHOLD`(读作留 kernel)。拼图结果出现两个互斥读法:①fill 分支随 κ_S 迁策略层、阈值留 kernel(策略层判据代码消费 kernel 判据常量——阈值 0.5 是判据值,按宪法五判据线应随策略层);②fill 分支与阈值都留 kernel(kernel 留判据代码,违宪法五)。实现者无从裁决。
- 修正方向:三处统一为一种归属并写明契约——建议「`_kappa_state` 连同 fill 分支与 `_FILL_EDGE_THRESHOLD` 随本体迁 `encounter_pick.py`;kernel 只保留两定谳槽(游戏读数语义),策略层经模块读口消费两槽」,并在 §2.3 注明策略层 fill 分支的槽依赖。

### F6 [严重度:中] 「建议刷 ∧ 刷新锚点读缺」帧的零点击-重进循环面未申报(死分支首次激活引入)
- 位置:design §2.5(闸拒绝帧产出语义)/ §2.12 行为变化申报
- 发现:直调 `cw_screen_encounter.py:180-195`——重调分支现役语义 = 重调仍返 Suggestion → 零点击终结交回(设计稿对纯函数同输出的判断正确,注释收口方向正确);但暗装期 kernel 恒 `refresh=False`,该分支是**不可达死代码**。本批激活刷新阀后,「decide 返 Suggestion(容器 left≥1)∧ 本帧 `_refresh_point is None`(『剩余次数:N』OCR 读缺)」成为活路径:零点击交回 → 外循环重进重建入口 → 重读;若锚点持续读缺且可及集持续空,「重进-观察-建议-零点击」循环无收敛保障,且每轮 `round_success` 不消耗决策 node 的 `node_max_retry_times` 预算。同构先例「空候选零点击交回重读」在暗装期同样不可达——这是本批首次让该失败自愈路径承载真实流量,而 §2.12 行为变化申报 1–5 与验收锚均未覆盖该帧形态。
- 修正方向:§2.12 补一条行为申报(重调-零点击-重进路径由死转活)+ 收敛语义申报(依赖外循环轮次看门狗兜底则点名该兜底;或对「Suggestion ∧ 锚点缺」帧申报有界处置,需用户裁定);验收锚补一条该帧的预期形态。

### F7 [严重度:中] landing.md 缺席,对抗审对象面不完整(与规范生命周期及在飞批先例不符)
- 位置:本迭代 README(「落地:[landing.md](landing.md)(定稿后编写)」)对照 `docs/develop/harness/iteration-design.md`
- 发现:iteration-design §6 生命周期字面——「对抗审中(②设计对抗批:**总纲/详设/landing.md 一并攻**——依据/试读/阶段可验收性/接口契约)」;§1 目录构成 landing.md 为必有件(README 模板无「无则删本行」注)。直调在飞先例:补给批对抗审件(`attack-r12.md`/`review-312.md`)已在攻其 landing 3.1/3.2/3.3 阶段小节——先例是**对抗审时 landing 在场**。本批 landing 缺席,阶段拆分可验收性、§12 工程门引用、账本 criteria 预注册无从本批审查,「阶段与设计一致」这一总纲攻击面(规范核一)落空。
- 修正方向:landing.md 提前到对抗审内完成(照补给批先例),或在 README/§0 申报偏离规范生命周期的理由并留待定稿后补审的流程口。

### F8 [严重度:中] P64 判死结论外延到 `DELTA_T` 未申报辖域差
- 位置:design §1 症状 3(「P64:…任何静态 `dict[旗牌→stat]` 注入都产假真值——`DELTA_T` 净值表的静态注入形态结构性不可达」);§2.3 退役四槽依据
- 发现:直调 `proofs/p64-encounter-dstat-static-map-uncalibratable.md` 状态行——「**辖域 = 静态 `dict[旗牌→stat]` 形态**,条件表形态不在辖域」,命题与证明的判定对象 = EV 核 `ENCOUNTER_DSTAT_MAP`(λ 分带键),全文未提 `cw_encounter_selection.DELTA_T`。`DELTA_T` 的语义是「档位→净值(档位加成+连胜增量+品质/特殊加成增量+持卡 −4 的净值,由 E-3 按选档结果标定)」(现役模块 docstring :51-55)——P64 的自由项论证(B/q/s/m 运行时项)对其**同构适用**,但这是设计稿的引申,不是 P64 的显式结论;「已被证明判死」按现文会被读作 P64 原辖域内结论。
- 修正方向:§1 症状 3 补一句申报:「P64 原辖域 = EV 核 DSTAT_MAP 静态映射;`DELTA_T` 净值表为同构『旗牌→难度量静态映射』形态,判死由同一自由项论证逐项覆盖(引申申报,非 P64 原文结论)」。

### F9 [严重度:中] 「P3 无遭遇」无依据标注
- 位置:design §2.2 窗口定义变更(「boss 行之后不存在遭遇决策点(P2 boss = r7 末节点;P3 无遭遇)」)
- 发现:直调 `docs/game/currency_war/research/economy.md` §10.2 节点表——仅 P1/P2 两行(P1 r7=encounter、boss@r9;P2 r3/r5=encounter、boss@r7),**无 P3 行**;`kernel/cw_plane_table.py:92` 「P3 进表即自适应」= P3 结构无在册静态真值;`competitors.md` :98 也只实锚 P1/P2 boss 轮位。「P3 无遭遇」与「P3 boss 后无决策点」均无出处(迭代规范写作硬规则 1:无依据标注的主张默认为攻击目标)。影响面有限——即便断言不实,boss 行不入窗的失败方向保守(窗口更空→不足态),但标注义务不豁免。
- 修正方向:补出处;无出处则改写为「P3 节点结构未在册,boss 行排除在该位面的行为面按『窗口不足→保守退化』承担」。

### F10 [严重度:中] `test_cw_obs_arch_event_screens.py` 测试面申报错误,且与本节末句自相矛盾
- 位置:design §2.7 测试面第一条
- 发现:直调该测试文件——全文件唯一 `cw_encounter_selection` import 点为 :417-420,import 的是 `claim_encounter_reward, record_settlement_row`,两者均为设计稿 §2.1 自列的 **kernel 保留面**,不随迁移、无需修改;而 §2.7 同段末句自己写「`claim_encounter_reward` 分支锁(kernel 保留面)不动」。前半句「该 import 点随新载体」与后半句互斥且与代码事实不符。另:设计稿测试面未提该文件 :380-404 的「重调仍建议刷新→零点击终结」op 行为锁——激活刷新阀后该锁变为在产路径的行为锁,其 docstring 旧叙述(「按原评分选」)与闸内嵌语义的收口义务同 §2.8 的 op 注释收口同面,未列。
- 修正方向:测试面首条改为「该文件 import 点消费保留面符号,零改动」;补列「重调零点击行为锁的 docstring 旧叙述随批更新(行为断言保留)」。

### F11 [严重度:低] bridge.py 的 `EncounterPick` import 形态标错(顶层运行时 import,非 TYPE_CHECKING)
- 位置:design §2.6 消费面(「bridge.py TYPE_CHECKING import」)、§2.7 同
- 发现:直调 `bridge.py:33-35`——`EncounterPick` 为模块顶层运行时 import(TYPE_CHECKING 块在 :53-59,仅含 `DecisionV2Registry`/`StrategySession`);:281 另有运行时注解 `pick: EncounterPick = ...`。删除面动作本身(清理该 import)没错,但「TYPE_CHECKING import」的定位与现状不符。
- 修正方向:消费面描述改「bridge.py 顶层 import(:33-35)+ :281 运行时注解」。

### F12 [严重度:低] 刷新剩余语义裁定指针死链(`../flow/op-layer.md` 不存在)
- 位置:design §0 裁定指针第三条
- 发现:glob 全 currency_war 文档树,`op-layer.md` 唯一实址 = `screens/op-layer.md`;`flow/` 目录无此文件。§1.4 内容与设计稿引用语义一致(直调 `screens/op-layer.md:64/68`:「刷新闸 = 剩余语义观察真值(全域,用户裁定 2026-09-21)…None = 未观察」)——仅路径段错,应为 `../screens/op-layer.md`。
- 修正方向:改 `../screens/op-layer.md`。

### F13 [严重度:低] refresh-valve 归因串「因」枚举未定死(窗口不足帧的因词缺申报)
- 位置:design §2.2 归因串格式段
- 发现:现役 refresh-valve 三因 = `window-insufficient`/`kappa-不足`/`empty-reachable`(直调 `cw_encounter_selection.py:396/406/438`)。新决策序把「窗口 <2 行」并入「不足态」后,该帧刷新阀 reason 的因词是否保留 `window-insufficient` 未写;设计稿自述保留归因串的动机是「遥测判读连续性」,而判读按词消费,因枚举不封闭 = 判读侧无契约。
- 修正方向:归因串段补「因」封闭枚举,并写明窗口不足帧的取值(保留 `window-insufficient` 或并入 `kappa-不足`,二选一定死)。

### F14 [严重度:低] `cw_difficulty_account` 注释收口锚定位不准(「模块头」实为方法 docstring)
- 位置:design §2.7 注释指针收口(「`kernel/cw_difficulty_account.py` 模块头『挂 decide_encounter 消费批』句」)
- 发现:直调该文件——「遭遇/首领限定建模挂 decide_encounter 消费批」句在 `from_strategies` 方法 docstring(:59),非模块头。孤儿申报本体(marginal_value 唯一消费链 = `encounter_tier_score`、DifficultyAccount 全仓零生产消费)经 grep 核实**成立**。
- 修正方向:锚改「`from_strategies` docstring(:59)」。

### F15 [严重度:低] 批间协调的补给批状态描述过期(已非「对抗审中」)
- 位置:design §2.11(「补给批(30 号稿,对抗审中)」)
- 发现:直调——`strategy-docs/30_supply_screen.md` 正本已存在;`strategy-docs/README.md` §2 已含 30 行、导航句已「18-30」;`25_event_overlays.md` 头注已有「补给画面已拆 30 号稿」;补给批目录已有多轮审查件(attack-r12/review-33/review-312 等);`cw_survey19_hooks.py` 中 `supply_reroll_decision` 已不在(彼批删除面已落地)。「若彼批先落,本批对其剩余面重核」的纪律本身健壮,但状态快照过期会误导批序判断。
- 修正方向:状态行刷新(「彼批删除面/文档面已落地」),§2.11 重核清单相应收敛到仍共享的面。

### F16 [严重度:低] 迭代 README 缺对抗报告链接(模板偏差)
- 位置:本迭代 README「## 进度」节,对照 `docs/develop/harness/iteration-design.md` §4 模板
- 发现:模板进度行格式为「设计对抗:<状态> · 报告=[attack.md](attack.md)」;现 README 为「设计对抗:未开始」,缺报告链接段。对抗审已启动,链接应就位。
- 修正方向:补「 · 报告=[attack.md](attack.md)」。

## 零发现面申报(实际攻击过的面清单)

以下各面经直调核查**无发现**:

1. **数值/口径直调复算(全对)**:P15v2 冻结语料 boss 26.79 / 普战 10.45 → 26.79/10.45=2.5636≈「约 2.56×」✓(`math_proofs.md` P15 行);`ENCOUNTER_TIER_COUNT=4` ✓(`cw_sim_backend.py:491`);P2 节点表 r3/r5=encounter、r5 帧普战窗口=r1/r2、战斗类窗口=r3+r2 的核算 ✓(`economy.md` §10.2 表逐格);`DIAMOND_EQUIP_NAMES`={红钻,蓝钻,财富宝钻} ✓(`cw_node_obs.py:216`);「漏读『一』→1」✓(`cw_node_obs.py:56`);遭遇奖励达标制出处 = combat.md §3 ✓(:38-39 实在 §3 节内);六标定槽字面全 None ✓(`cw_encounter_selection.py:47-64`);cap=2/窗口 2/`_FILL_EDGE_THRESHOLD` 0.5/四档序数/t≤4 分界全部沿用原核 ✓(零新数值申报成立);`reward_tier` 映射语义与「`'/'.join(option.rewards)` 输入、(档,idx) 序」逐位一致 ✓;P26 待证明双挂账(Δp_prep/L_node)与 08 号稿 E3 行、13 号稿 :21「双轨」过期描述 ✓;25 号稿画面族清单 8 屏 ✓;裁定 9 行文本、P64 点亮前置链、敌浮层「OCR 全可读、难度分随卡变」✓;31 号稿编号未占用 ✓;README 导航句现值「18-30」✓。
2. **消费面 grep 定谳(设计稿声明全部核实成立)**:`last_normal_battles` 生产消费唯一 = 判据本体 ✓;`encounter_tier_score` 唯一消费 = 旧核 `_score` ✓;`wear_discipline_alert` 零生产消费 ✓;`DifficultyAccount` 全仓零生产消费、`marginal_value` 唯一消费链 = `encounter_tier_score` ✓;`apply_calibration`/`reset_calibration` 全仓(含测试仓)零外部引用(「退役四键若被测试/工具引用」条件句实态为空集)✓;sim 无结算环写端(grep `settlement_ring|record_settlement_row` 于 sim/ 零命中)✓;`claim_encounter_reward` 消费点 = `cw_op_settle_confirm` ✓;`record_settlement_row` 单一写端 = `cw_screen_battle_wait` ✓;kernel 零指向 strategies ✓。
3. **接线面与守卫**:`flow.py:594-609` 入口(refresh_used 预计算 :601-602、`_consume_prep_direction_frame` :603)与设计稿改写方案逐点对应 ✓;`_require_slot_options`(:414-422)含离屏 None 抛错,bridge 覆写删除后守卫不丢的声明成立 ✓;`cw_screen_encounter` 三出口派发即终结、空候选零点击、sim 机械锚豁免与设计稿 op 层零行为改动的其余面一致 ✓;窗口读口改形与 `last_row`(兑现回调读口)不冲突 ✓。
4. **sim 盲区申报**:sim 遭遇观察 `refresh_left=None`(`cw_sim_backend.py:1393`)、占位非空候选、暗装期与改后 sim 行为「窗口空→闸拒→最低档」逐位一致的声明成立 ✓;可见前置交接(coarse 结算输出接环)落点存在(:1437)✓。
5. **宪法对齐**:宪法二——新判据无位面字面量,旧核 `plane_of(gs)==3` 分支退役 = 存量清除 ✓;宪法三——遭遇败局入窗为保守向的核查成立 ✓;宪法五判据线——迁移/保留面逐项归类合理(EncounterOption 观察契约、结算环裁定 9 基建、`claim_encounter_reward` 记账语义、`enemy_difficulty` 真值读口均非打分)✓;宪法六——`encounter_pick.py` 新文件 + 31 号稿新文档 + 命名避让(不复用 `encounter.py` 空名)✓;迁移节奏逐画面一批 ✓。
6. **治本核验**:§1 归层(分层语义 + 表示)与三核并存现状逐符号证实(生产暗装核 / 基类旧核 / EV 核);§2 修根 = 宪法五兑现 + 暗装门收窄,非症状补丁;逐画面迁移是宪法六既定节奏,非逐件打补丁,跨件半问不触发 ✓。
7. **行为变化申报完整性(除 F6 外)**:①-⑤ 与代码现状可对照,「旧核生产从未生效 + 基类兜底路径变化」双句并陈自洽(非 mandate 策略走基类)✓;`dark-install` 归因段退场已在 §2.2 申报 ✓。
8. **测试面其余项**:`test_cw_unified_action_4.py:28/259/278` 引用属实 ✓;`test_cw_obs_arch_event_screens.py` :400-404 重调行为锁存在 ✓(申报错误见 F10);「新决策本体锁随 landing 落测试仓、`claim_encounter_reward` 分支锁不动」✓。
