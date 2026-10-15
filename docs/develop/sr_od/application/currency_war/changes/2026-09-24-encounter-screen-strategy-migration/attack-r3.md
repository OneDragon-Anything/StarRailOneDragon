# 遭遇迁移设计 对抗审查报告（第三轮）

> 攻击对象 = 本目录 design.md / landing.md / README.md 三件。判据源直调：00/01 号稿宪法与章程、04 号稿 §7 裁定表、op-layer.md §1.4、p64 单篇、math_proofs.md 索引（P15/P26/P85）、P9_VALIDATION.md、plane_schedule_observed.md、economy.md §10.2、combat.md §3、iteration-design.md、strategy-work.md、AGENTS.md 注释/文档规范。全部码点/数值/引文按「直调复核禁转述」执行，证据以 文件:行 标注。

## 发现清单

### R3-F1 [严重度:中] 边缘态 cap=2 的合法性载体申报与 01 §6 数字三形态章程正文冲突——被激活的闸门数字无任何在册形态
- 位置：design.md §2.2（判据结构分层申报段、决策序第 4 步「边缘态天花板 cap = 2」及 cap 精确口径申报）
- 发现：design.md:63 申报「判据结构本身（κ_S 三态、边缘态 cap=2、经验档层放行、刷新阀、钻>装备>金币>末档偏好序）= 立场序结构……**非数值闸门，不属【注】/【推】/【拟】任一数值形态**」。直调章程：01_math_framework.md §6 开篇「框架内**每个进决策门的数字**必须标注三形态之一（含本章程扩展形态【拍】）」（:152）；【拍】边界句「凡『数值大小参与方向/闸门判断』的量归【推】/【拟】纪律，【拍】只承载『登记即立场、分差即偏好强度』的加法立场值」（:168）。cap=2 是「t ≤ 2 才可及」的可及性闸门数字（design.md:86），数值大小直接参与闸门判断——按章程正文它**不满足**「非数值闸门」定性，也进不了【拍】；设计明示不属【注】/【推】/【拟】，四形态全部落空。strategy-work.md §1 亦要求每个数字属「规则或推导/显式模型估计」两类或以支配性论证消参——cap=2 三者皆无（「能力缺口最近出现过→无余量」是立场陈述非支配论证）。对照先例：补给批同位置申报的合法性载体是**用户裁定本身**（supply design.md:7「立场序合法性 = 裁定本身，用户裁定 2026-09-24」），本批 cap 序设计自认「用户未逐项明示」（design.md:63），仅余「判据正本沿用，非本批新拍」（design.md:86）一句——但 E-2 期该值处于暗装不可评态，**激活**（本批的行为事件）时未补任何形态/授权锚，等于一个无来源数字首次进入活闸门。
- 修正方向：为 cap=2 补显式合法性链，三选一并写进 §2.2 与 31 号稿裁定登记节：①按【拍】章程补立场登记（声明其闸门性质、请求用户追认，登记表落策略层）；②给出支配性论证消掉该参数；③引 E-2 落码批的在册审查/裁定记录作持久指针并注明「激活不改值」。现稿「非数值闸门，不属任一数值形态」的笼统申报与章程正文直接矛盾，对抗审按「无依据标注的主张默认为攻击目标」必须打回。

### R3-F2 [严重度:中] §2.2「落码形态参照已搁置核」指错模块——四结构不在已搁置 EV 核，与 §1 自身术语矛盾
- 位置：design.md §2.2（「唯一判据变化」段末句）
- 发现：design.md:64「落码形态参照**已搁置核**在册的语义（git 历史可溯）」。直调设计自身词汇：§1 明载「生产现役核 = `kernel/cw_encounter_selection.py::decide_encounter`」（:18）、「历史 EV 核……**已搁置让位**、保留禁删」（:20）。三态表/经验档层/tiebreak/刷新阀四结构的实址全部在现役暗装核：`cw_encounter_selection.py` 的 `_kappa_state`（:297-323）、`EncounterLog.tier_cleared` 经验层（:176-198）、`reward_tier`+四档常量（:244-278）、刷新阀三因（:392-439）；已搁置 EV 核（`mandate_v1/encounter.py`）内**一个都没有**（该文件只有 reward_subtype_value/_branch_lambda/刷新肢等另一套形态，:100-401）。实现者按此句做 git 考古会打开 encounter.py 扑空；且本句是「落码形态参照」的合法性载体句（§2.2 设计原则段），指错对象使该载体声明失锚。
- 修正方向：「已搁置核」改为「现役暗装核（`kernel/cw_encounter_selection.py`，迁移后物理删除，落码前以工作区现态为拷贝源）」。

### R3-F3 [严重度:低] provisional.py 在 landing 3.2 文件面被标为「按裁定」，但其头部指针句收口是无条件义务——保留分支下无阶段认领
- 位置：landing.md §3.2 文件面；design.md §2.3/§2.7
- 发现：landing.md:17 将 `strategies/impl/mandate_v1/audit/provisional.py` 标注「（按裁定）」。直调：`provisional.py:22-23` 头部注「新遭遇选档判据的标定注入 = kernel/cw_encounter_selection.apply_calibration（与本模块槽位物理隔离…）」；design.md:102 规定注入面随迁 `encounter_pick.py` **无条件执行**（不在裁定点 1 辖域），design.md:139 相应规定该指针句「注入面迁策略层后改指」亦无条件。而「按裁定」的分支语义（landing.md:15）在保留分支只覆盖 encounter.py 模块头与 EncounterPick 改形，未含 provisional.py——landing 文件面是 worker 的可动文件边界声明，保留分支下该文件不在面内 → 陈旧指针（指向已迁走的 kernel 注入口）随批存活，且 3.2 完成判据的 grep 集（EncounterPick/encounter_tier_score/四退役槽，landing.md:21）扫不出它。
- 修正方向：provisional.py 的头部指针句收口从「按裁定」中拆出为无条件文件面项；「按裁定」仅修饰双槽删除面。

### R3-F4 [严重度:低] 推荐分支（EV 核退役）下 `cw_economy.py:414` 的消费点清单句失指，「已知点全列」收口清单未含
- 位置：design.md §2.7 注释指针收口；cw_economy.py:414
- 发现：直调 `cw_economy.py:414`（`net_income` docstring）：「②现役 6 个决策消费点（mandate_v1 shop.py ×4 / **encounter.py** / 本模块 loss_exact 前置）全部传 `streak_pre=0, lost_node_type=None`」——「encounter.py」即 EV 核（其 `decide_encounter_ev` 调 `net_income(round_num, 0)`，encounter.py:256）。裁定点 1 推荐退役删除（design.md:160-161），删除后该句计数（6→5）与指称同时失真。design.md:139 收口清单（「已知点全列」）与 landing 3.2 文件面均无 cw_economy.py；完成判据 grep 集亦不含「encounter.py」字样，兜底复扫之外的在册防线缺位。
- 修正方向：收口清单补 `cw_economy.py:414`（退役分支 = 计数与指称同步改写；保留分支 = 不动并注明条件）。

### R3-F5 [严重度:低] landing 3.2 完成判据的「零残留」grep 集不完整：g_ratio/_d_enc_snapshot/_Diagnostics/_CALIBRATABLE 不在列
- 位置：landing.md §3.2 完成判据；design.md §2.3/§2.7
- 发现：landing.md:21 规定验收证据「全仓 grep 无 `EncounterPick`/`encounter_tier_score`/四退役槽残留」。直调 design.md:100 退役面：物理删除的还有 `g_ratio`、`_d_enc_snapshot`、`_Diagnostics` 三个独立符号（及 §2.7:135 重申）；随 apply_calibration 迁移，kernel 侧 `_CALIBRATABLE` 键集（cw_encounter_selection.py:72-73）同样应消失。这四个符号均可 grep 定谳却不进验收 grep 集——删除面完整性少一道可执行的验收证据（现役定义点：cw_encounter_selection.py:289/326/451）。
- 修正方向：grep 集补 `g_ratio`/`_d_enc_snapshot`/`_Diagnostics`/`_CALIBRATABLE`（策略层新文件带同名者除外，按「kernel 侧零残留」口径表述）。

### R3-F6 [严重度:低] §2.6 与 §2.7 对 bridge 的 `EncounterPick` import 形态描述互相矛盾，§2.7 标注错误
- 位置：design.md §2.6 / §2.7；bridge.py:33-35, :53-59
- 发现：§2.6（design.md:123）描述 bridge 消费面为「**顶层 import** + 运行时注解」；§2.7（design.md:136）却写「`decide_encounter` 覆写删除 + **TYPE_CHECKING** `EncounterPick` import 清理」。直调 bridge.py：`EncounterPick` 是 :33-35 的**顶层运行时 import**（非 TYPE_CHECKING；:53-59 的 TYPE_CHECKING 块只有 DecisionV2Registry 与 StrategySession），运行时注解在 :281。同一符号两节两种形态标注，§2.7 与码不符。
- 修正方向：§2.7 改「顶层 import 清理」，与 §2.6 对齐。

### R3-F7 [严重度:低] §0 状态行「对抗审中（第二轮）」含轮次叙事，违 iteration-design 写作硬规则 3
- 位置：design.md §0（:10）；规范 = docs/develop/harness/iteration-design.md §5 规则 3
- 发现：规范正文：「无过程叙事：不写谁审的、**第几轮攻击**、上稿改了什么；过程住对抗报告与账本，**进度只住 README**」，卡点 = 「『本轮/修订后/已改』类措辞即打回」。design.md:10 状态值「对抗审中（**第二轮**）」即为轮次号入正文；轮次与报告链接已合法住于 README.md 进度节（`attack.md`/`attack-r2.md` 链接在册），设计正文只应保留「对抗审中」。
- 修正方向：删「（第二轮）」；状态枚举值照模板（草案/对抗审中/定稿）。

### R3-F8 [严重度:低] §2.1 归因注使用会话局部标识符「W239」，读者不可解码
- 位置：design.md §2.1（:53）；规范 = AGENTS.md §8（引用必须是持久索引，禁 W 轮次号类会话局部标识符）/§9 文档规范（禁自造黑话）
- 发现：design.md:53「`record_settlement_row`——结算行入环单一写端（**W239** 守卫两臂汇合点）」。「W239」无任何文内或持久解码路径，属只在当次会话有意义的编号；其指称事实（守卫两臂汇合点）已有持久载体 = `record_settlement_row` 自身 docstring（cw_encounter_selection.py:218「构造唯一点下游、W239 守卫两臂汇合后调用」——代码注释侧同病，但那是既有注释；本设计新增引用不应复制该形态）。
- 修正方向：改为语义描述或持久索引（例：「守卫两臂汇合点（单一写端契约见 `record_settlement_row` docstring）」）；落批改码时该 docstring 内的 W239 同扫。

### R3-F9 [严重度:低] 钻石名单迁移后两处在册 docstring 的「单一源 = cw_node_obs.DIAMOND_EQUIP_NAMES」表述失准，收口清单与 landing 文件面均未认领
- 位置：design.md §2.4/§2.7；cw_events.py:171、strategies/impl/mandate_v1/supply.py:12
- 发现：design.md:108 规定 `DIAMOND_EQUIP_NAMES` 定义迁 `data/cw_equipment_data`、`obs/cw_node_obs` 改为 import data 单一源。直调两处消费 docstring：`cw_events.py:171`（SupplyOption 字段注，**保留面**随批存活）「检测集单一源 = ``cw_node_obs.DIAMOND_EQUIP_NAMES``」；`supply.py:12`（mandate_v1 模块头，存活）「``cw_node_obs.DIAMOND_EQUIP_NAMES``(红钻/蓝钻/财富宝钻)」。迁移后定义单一源 = data 模块，cw_node_obs 侧降为 re-import——「单一源 = cw_node_obs.*」两句由准确变失准。design.md:139 收口清单与 landing 3.2 文件面均未列 `strategies/impl/mandate_v1/supply.py`（cw_events.py 在面但 :171 句未点名）。
- 修正方向：收口清单补两处「单一源」指称改 data；landing 3.2 文件面补 supply.py（仅注释）。

## 零发现面申报（实际攻击过的面，无发现）

**判据源直调（逐项核符）**：
- 00_framework.md 六条：第五/六条文字与 design §0 指针对应（:14-23）；第三条「危险只升不降」与 §2.2 遭遇败局入窗「反应提前」方向论证相容（§4 λ 顾问「只许提前」同构）；迁移节奏「逐画面推进、批内不夹带」与单画面批形态相符（:23）。
- 04_survival_budget.md §7 第 9 行逐字：授权辖域（敌方通道 killed/进度填充率 + 入 GameState 持久化）、「判据正本 = kernel/cw_encounter_selection.py」失配前提、「持久化形态生效即登记」——§0/§2.2/§2.9 的引用与改写计划全部对得上（04:111）。
- op-layer.md §1.4：剩余语义（None=未观察、节点屏闸 None=拒刷）、刷新=终结动作、禁访问内重读/二次覆盖写——§2.2 闸内嵌与 §2.5 重调收敛申报与之无冲突；重调一次 + 零点击终结在 cw_screen_encounter.py:180-195 实址核符。
- p64 状态节辖域：「已证（结构命题；辖域 = 静态 dict[敌方难度读数→stat] 形态，条件表形态不在辖域）」——§2.3 对 DELTA_T 的「引申申报，非 P64 原文结论」定性诚实成立；点亮前置链①（浮层读数、OCR 全可读、未接入）与 §1 症状 3/§2.11 一致。
- math_proofs.md 索引：P15 行 boss 26.79/普战 10.45（:27）支撑 §2.2 boss 排除论证；P26 行「待证明（Δp_prep 条件表 + L_node 分位口径均未采）」（:38）支撑 §1 明确不解决；P85 行 A/B 分键为遭遇备战帧、不消费选档输出——§2.12 验收线保全申报成立。
- P9_VALIDATION.md:10 确登记 cw_survey19_hooks「P1/P9/P8」旧编号与 math_proofs 无关——§2.7 删除不受影响声明属实；wear_discipline_alert 属 P2 封存件活态后裔与 P2_VALIDATION.md:54/59 一致。
- plane_schedule_observed.md：P1 42 局零反例（:24）、P2 7 局完整对照且样本边界声明（:80）、P2 序列含补给@r3 遭遇@r5（:19）；economy.md §10.2 P2 行双遭遇 r3/r5 且标注「待多局复核」（:133）——**两源分歧、kernel 表下两窗口逐位等价、economy 表下候选 B 收益面待定谳**三项核算全部复算成立，维持候选 A 的取舍论证无懈可击。
- combat.md §3 达标制（:38）→「killed=True 蕴含进度达标、方向安全」成立；`货币战争-敌人信息浮层.md`、`currency_war_encounter.md`、`screens/encounter.md`（kernel 委托句在 :12）、`30_supply_screen.md` 均存在，`31_encounter_screen.md` 编号未占用。

**现役代码直调（设计删改对象逐符号）**：
- cw_encounter_selection.py：六标定槽字面全 None（:47-64）、暗装门序先于 κ_S（:375-385）、暗装=最低档+零刷新+`dark-install` 归因（:367-373）、κ_S 三态/删失归态与 §2.2 决策序逐位同构（:297-323）、cap=2/6（:418）、经验层 t≥5（:431-434）、reward_tier 映射与 `'/'.join(rewards)`、`(档, idx)` 序（:256-278, :442-444）、`_lowest_idx`（:459-463）、保留面（SettlementRing/EncounterLog/_RingRow/SETTLEMENT_RING_DEPTH/selection_state_of/game_start_reset/record_settlement_row/claim_encounter_reward）与 §2.1 清单一致；kernel→obs 反向依赖实锤（:266-268）。
- cw_events.py：旧核四要素（词缀契合/成型度/难度账本压档/P3 `plane_of(gs)==3` 枚举违例）逐条在码（:99-155）；`EncounterOption.affixes` 死输入实锤（obs 写端恒 `affixes=[]`，cw_node_obs.py:39,73）；`EVENT_PICK_TYPES`/`EventPick` 摘位面（:538-543，全 src 零外部消费，删类不摘位 NameError 风险属实）；模块 docstring 现态含补给收口句（:3-5）。
- flow.py：`decide_encounter`（:594-609）、`_require_slot_options` 离屏 None 抛错（:414-422）、`_consume_prep_direction_frame` 兄弟入口同款（:366）、`refresh_used` 预计算（:601-602）、cw_events 现役消费 :656/:793/:807 三行号全对；docstring「kernel 按原评分直接选卡」句在 :598（收口清单已列）。
- bridge.py：覆写（:252-285）直调 `cw_encounter_selection`；模块头依赖矩阵句「decision 只可依 data/kernel」（:8）；不覆写 decide_supply/decide_invest_*（只覆写 prep/encounter/shop_screen）——「回落基类与营业面覆写同构」成立。
- encounter.py EV 核：双槽 None 期恒 fail 向零刷新（:56-59 申报与实现一致）；「六处签名/构造消费」逐点核符（:264/:268/:280/:306/:308/:387）+ docstring 字样（:67）；src+测试仓双零消费 grep 定谳（decide_encounter_ev/encounter_ev_* 全仓仅定义文件命中）；「曾记的 EV 核纯函数锁不存在」属实（测试仓零命中）。
- provisional.py：双槽登记与双槽互锁注（:98-120）、头部指针句（:22-23）——指针问题归 R3-F3。
- cw_survey19_hooks.py：现恰 `encounter_tier_score`+`wear_discipline_alert` 两函数、supply_reroll_decision 已不在（§2.11 申报属实）；encounter_tier_score 唯一消费 = cw_events 旧核 `_score`（:128-146），测试仓零命中。
- cw_difficulty_account.py：`from_strategies`「挂 decide_encounter 消费批」句（:58-59）、marginal_value 唯一消费链 = encounter_tier_score、DifficultyAccount 全仓零生产消费——孤儿申报全部核符。
- op/上报层：`CwActionPickEncounterOp` 静态入参词表动作 + idx 鸭子消费（cw_pick_encounter_action.py:54,67）、`report_action_pick_encounter_param(param: Any)` 鸭子取 idx（pick_encounter.py:47-58）——「动作链零改动」成立；cw_vocab 两处「替代 EncounterPick」实址（:715/:906）；cw_strategy 接口注（:178-180）与依赖矩阵句（:253-254）均存在。
- 依赖方向：strategies/ 全目录零 obs import、kernel 零指向 strategies（仅禁令注释）、obs→data import 已有多点先例（cw_equipment.py:24 等）——§2.1/§2.4 方向声明全部成立。
- sim：`ENCOUNTER_TIER_COUNT=4`（:488）、占位奖励文本「金+20(占位,…)」不含「金币」字面（:535-539）、结算环零写端（grep 零命中）、refresh_left 无 sim 写端——§2.12 盲区申报与「逐位一致」结论成立；`dark-install` 段全仓零消费方，退场无判读面破坏。
- 消费面 grep：`last_normal_battles` 生产消费唯一 = 判据本体（:390）、`last_row` = 兑现回调（:515）；apply_calibration/reset_calibration/_kappa_state/g_ratio/_lowest_idx/_d_enc_snapshot/_FILL_EDGE_THRESHOLD 全部仅定义文件内引用——「全仓零外部引用，随迁零成本」核实为真。

**测试面**：test_cw_unified_action_4.py 类型 import（:27-28）与 `:259`/`:278` 两处实例构造**逐字命中**；注册完备锁遍历 CW_ACTION_TYPES 词表单表、不遍历 EVENT_PICK_TYPES（:115-134）——摘位不破锁；test_cw_obs_arch_event_screens.py 的 cw_encounter_selection import 恰为保留面符号（:417-420）、「重调仍建议刷新→零点击终结交回」锁在册（:387-404）、闸拒绝锁 :349；EncounterOption 测试仓恰五文件引用（game_state_consume/obs_arch_event_screens/route_clear/screen_report_ports/world_decl）——「五方引用」属实；落地后无任何现存测试因删改面红（均为 stub 驱动或保留面符号）。

**文档面与先例**：13 号稿 :21「双轨」过期描述（基线核+EV 核，无 cw_encounter_selection）——「文档漂移实证」定性成立，含「M13 competitors 节点表」指针；08 号稿 E3 行（:18）现有语义/待 derive/P26 锚三格与 §2.9 改写计划逐格对应；25 号稿画面族恰 8 屏（:3）、§1 prose（:13）、§2 表行（:19）三处收口点齐全；strategy-docs/README §2 分篇表含 28/29/30 行、导航句「18-30」（:56）→「18-31」改法成立；补给批/invest-env 批 design §1 的「遭遇等其余画面后续批」承接登记实指；「纯值出口照 supply.decide/invest_env.decide 同构」成立（SupplyDecision/InvestEnvDecision/RefreshSuggestion frozen dataclass 先例，含空帧 no-options 同款）；「次数闸内嵌」先例在 30 号稿 README 行在册。

**三件互查与试读**：landing 三阶段覆盖 design §2.1-§2.9 全部改动面（除 R3-F3/F4/F9 三处认领缺口）；3.1 边界「零行为变化」与设计 3.1→3.2 依赖序自洽；3.3 正本清单六项+画面文档与 §2.9 一一对应、无多无漏；行为变化申报 1-4 ↔ landing 完成判据、§2.12 锚 1-6 ↔ landing 3.1、锚 7 ↔ 落地阶段检查项逐条对上；README 模板合规（报告链接可解析）。实现者试读：3.1 凭 §2.2-§2.5 + 现役码可开工（四结构拷贝源在 3.1 时点仍完整在库）；3.2 消费面/删除面/测试面清单可执行（行号锚 :259/:278/:656/:793/:807 全实址）；3.3 清单可执行。治本核验：§1 归层（分层语义+表示）成立；§2 修根（本体迁策略层=宪法五根、真值归位 data=治本不搬家、三核收敛=单一源）非症状，唯 cap=2 形态债见 R3-F1。
