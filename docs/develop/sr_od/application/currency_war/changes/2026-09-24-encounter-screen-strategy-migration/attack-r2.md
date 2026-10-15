# 遭遇迁移设计 对抗审查报告（第二轮）

> 审查对象：`design.md`（194 行）+ `landing.md`（43 行）+ `README.md`（14 行）。审查方式：无前提三核；判据源全部直调（现役代码逐符号 read/grep，裁定/证明/节点表/画面知识逐篇 read，测试仓全量 grep 定谳）。发现共 12 条（高 2 / 中 5 / 低 5），文末附零发现面申报。首轮 16 条的修复落点经抽验均已在稿（F3/F4/F5/F8/F10/F11/F12/F13/F14/F15/F16 对应处逐一直调确认），本报告不重复已收敛项。

## 发现清单

### R2-F1 [严重度:高] 判据迁移计划引入 strategies→obs 直接依赖，与在册 decision 桶依赖矩阵正面冲突
- 位置：design §2.1（依赖方向段「注册表（DIAMOND_EQUIP_NAMES 转经 obs 层、EQUIPMENT_ROSTER data 注册表——策略层消费 obs/data 层合法）」）、§2.4（「消费源：DIAMOND_EQUIP_NAMES（obs/cw_node_obs）与 EQUIPMENT_ROSTER（data/cw_equipment_data）」）
- 发现：直调 `strategies/impl/cw_strategy.py:254`——「**分包依赖矩阵禁 decision→obs 直依**，生产装配点 = app/decision_assembly ``install_obs_ports()``」；`strategies/impl/mandate_v1/bridge.py:7-8` 模块 docstring——「依赖矩阵：**decision 只可依 data/kernel**」。`encounter_pick.py` 将驻 `strategies/impl/mandate_v1/`（decision 桶，与 supply/invest_env 同桶），按 §2.4 计划顶层消费 `obs/cw_node_obs.DIAMOND_EQUIP_NAMES`（:216）= 决策文件直依 obs 层，恰是被禁边。旁证：全 strategies/ 目录 grep `from sr_od.application.currency_war.obs` **零命中**——现存决策件无一依 obs，先例是观察层把游戏事实预制进载荷契约（`SupplyOption.has_diamond`，cw_events.py:170），决策只消费 kernel 契约。设计「策略层消费 obs/data 层合法」是无依据标注的断言（迭代规范写作硬规则 1），且与两条在册锁文冲突；landing 3.2 完成判据只查「kernel 无指向 strategies」，拦不住这条反向新增。治本视角：本条只把 kernel→obs 搬成 decision→obs，注册表错置 obs 层的根没动。
- 修正方向：把 `DIAMOND_EQUIP_NAMES`（三个游戏定义物品名，宪法五①游戏真值）迁 `data/cw_equipment_data.py`（与 `EQUIPMENT_ROSTER` 同址，kernel/obs/策略层依 data 全合法；kernel 侧 `cw_events.py:18-20` 依 data 先例在册），obs 保留消费；或照 `has_diamond` 先例把钻石归属并进 `EncounterOption` 载荷契约。§2.1/§2.4 表述与 landing 3.1 文件面（新增 data 文件）同步改。

### R2-F2 [严重度:高] 「测试仓 EV 核纯函数锁」不存在，多处事实申报与删除面指向幻影工件
- 位置：design §1 症状 1（「唯一消费 = 测试仓 EV 核纯函数锁」）、§2.7（删除面第三条「+ 测试仓 EV 核纯函数锁」）、§2.10 裁定点 1（保留代价「+ 测试锁长期随仓」、推荐④「纯函数锁的维护税」）；landing 3.2（「退役删除 = 删 encounter.py + provisional 双槽 + EV 锁」）
- 发现：全 workspace grep `decide_encounter_ev` 仅 1 命中 = 定义处本体（encounter.py:278）；`reward_subtype_value`/`ENCOUNTER_G_GOLD`/`ENCOUNTER_DSTAT_MAP` 在 src + sr-od-test 全量 grep，消费全部封闭在 encounter.py/provisional.py 自身与文档；`sr-od-test/test/sr_od/application/currency_war/` 目录 136 个测试文件无任何 *encounter* 命名文件、无 mandate_v1.encounter import。即 EV 核在 src 与测试仓**双双零消费**，「唯一消费 = 测试仓 EV 核纯函数锁」为不实申报；§2.7 删除面与 landing 3.2 的「删 EV 锁」指向不存在的文件（实现者按图索骥会空手），§2.10 呈给用户裁定的保留代价/退役理由各含一笔幻影账。注：该错误使退役推荐**更强**（零消费 anywhere），但不改变「消费面全列（直调核实）」申报失实的性质，且裁定点 1 是本批唯一阻塞裁定，事实基座必须干净。
- 修正方向：§1/§2.7/§2.10/landing 3.2 全部改述为「EV 核 src 与测试仓均零消费（全仓 grep 定谳）」，删除「EV 锁」删除面条目；§2.10 推荐理由④改为「provisional 双槽维护税 + 零消费死代码」。

### R2-F3 [严重度:中] sim 占位奖励文本「全落金币档」错报，实落末档（值对标签错）
- 位置：design §2.12（「占位奖励文本全落金币档，tiebreak 维度 sim 恒并列」）
- 发现：直调 `sim/cw_sim_backend.py:535-539`——占位奖励文本 = `f'金+{ENCOUNTER_REWARD_GOLD_PLACEHOLDER}(占位,{ENCOUNTER_PARAMS_PENDING_U22})'`，即 `'金+20(占位,encounter_tier_params_pending_u22)'`，**不含「金币」子串**。按 §2.4 自列的 `reward_tier` 映射语义（cw_encounter_selection.py:256-278 直调：钻石名命中→钻档；`EQUIPMENT_ROSTER` 精确命中→装备档；含「金币」字面→金币档；否则末档），四条占位文本全落**末档（unmapped）**，非金币档。「tiebreak 恒并列」「行为差异只在主序与刷新阀」两个结论不受影响（四档同文本同档位），但申报的映射档位与直调语义不符——正是攻击纪律点名的「值对标签错」错误类。
- 修正方向：§2.12 该句改「占位奖励文本全落末档（不含『金币』字面、非注册表成员）」；或若想让 sim 落金币档，改占位文本含「金币」并申报理由。

### R2-F4 [严重度:中] 「P1/P2 序列，42 局零反例」口径失真，且自引节点表内含未对账的 P2 双遭遇行
- 位置：design §2.2（窗口定义段「现役节点日程真值表下（kernel/cw_node_schedule.py P1/P2 序列，42 局零反例）每位面至多一次遭遇」）、§2.10（同口径复述）；同段引 `economy.md §10.2` 佐证 boss 位
- 发现：直调 `kernel/cw_node_schedule.py:6-12`——「42 局零反例」为 **P1 专项**（源 `plane_schedule_observed.md` 裁定记录节同口径），P2 证据 = 「有投资策略环境的局序列与默认一致（**7 局对照**）」；`plane_schedule_observed.md:25/80` 明示 P2 完整结算样本默认环境仅 **1 局** + 环境局 5 局，并自报「不能排除其他条件下存在变体」。同时 design 同段引用的 `economy.md §10.2` P2 行（:133）为 `battle|battle|encounter|reward|encounter|reward|?|boss@r7`（「1 帧；待多局复核」）——**同位面双遭遇**候选证据就在设计自引的表里，未与「每位面至多一次遭遇」对账；§2.2 变体触发器把「同位面第二遭遇」当纯假设未来事件（多遭遇环境/P3 采齐），对在库候选证据只字未提。影响有界（普战窗口为保守侧，等价性不成立时失败方向仍安全），但候选 B 的「两口径逐位等价」论证在 P2 的证据强度被夸大，且违反依据就地标注纪律。
- 修正方向：§2.2/§2.10 括注改「P1 42 局零反例；P2 = 7 局对照（完整结算样本少，plane_schedule_observed 自报变体不能排除）」；对 economy.md §10.2 P2 双遭遇行补一句对账（ Kernel 真值表以结算屏源为准、该行 1 帧待复核 = 变体触发器的在库候证，触发条件达成前窗口维持普战口径）。

### R2-F5 [严重度:中] design §0 状态字段过期（「草案（对抗审查前）」），与 README/实际流程矛盾——全量同步复查卡点命中
- 位置：design §0（「状态：草案（对抗审查前）」）；对照 README 进度（「迭代设计:对抗审中（修订已按首轮发现落稿）」「设计对抗:进行中」）
- 发现：iteration-design §6「状态由总纲 §0 表达」，§5.4 卡点 = 修订后 design↔landing↔README 全量反查。首轮审查已完成、16 条已处置、本报告即第二轮——§0 状态仍是审查前值，与 README 进度和 `attack.md` 头部（「审查对象：design.md（187 行，状态『草案(对抗审查前)』」）共同证明该字段在首修轮被遗漏。生命周期权威字段失真 = 同步复查未全量的直接实证。
- 修正方向：§0 状态改「对抗审中」。

### R2-F6 [严重度:中] README 进度行含过程叙事（「已处置/首轮/首修轮」类措辞），踩写作硬规则 3 的打回线
- 位置：README 进度节（「修订已按首轮发现落稿」「首轮 16 条：高 2 / 中 8 / 低 6，已全部处置；F2/F9 部分与窗口候选在首修轮已先期处理」）
- 发现：iteration-design §5.3「无过程叙事：不写谁审的、第几轮攻击、上稿改了什么……卡点：形式检查——『本轮/修订后/已改』类措辞即打回」；§4 模板的设计对抗行只允许 `<未开始/进行中/收敛> · 报告=[attack.md](attack.md)`。轮次计数、处置状态、F2/F9 编号级叙事全部属于对抗报告与账本，README 只留状态。另「窗口候选在首修轮已先期处理」是把 §2.10 的实质决策记录在了过程叙事里（与 R2-F11 连带）。
- 修正方向：README 两行收敛为模板形态（状态 + 报告链接）；轮次统计与处置明细已在 attack.md，不损失信息。

### R2-F7 [严重度:中] 注释指针收口清单漏三处，其中一处使 landing「全仓 grep 无 EncounterPick 残留」完成判据按字面不可满足
- 位置：design §2.7（「注释指针收口（已知点全列…）」）；landing 3.2 完成判据/文件面
- 发现：①`mandate_v1/audit/provisional.py:22-23`——「# 新遭遇选档判据的标定注入 = kernel/cw_encounter_selection.apply_calibration（与本模块槽位物理隔离…）」：迁移后注入位 = 策略层（§2.3 自述），该指针两分支下均陈旧；裁定保留分支该文件根本不在 landing 3.2 文件面（仅退役分支以「按裁定」入面）。②`mandate_v1/encounter.py:67` docstring——「拒因串经 ``EncounterPick.reason`` 透传至既有 record_event_choice」：保留分支的改形义务只覆盖「import 与六处签名/构造消费」（六处计数经直调核实正确：:264/:268/:280/:306/:308/:387），docstring 提及不在列 → landing 3.2 完成判据「全仓 grep 无 EncounterPick 残留」按字面必红。③`flow.py:598` docstring——「已刷尽/未观察 → refresh_used=True，**kernel 按原评分直接选卡**」：§2.6 重写该入口但收口清单未列此句（句中「kernel 评分」指被删的旧核）。「已知点全列」申报与实际不符，实现者要么漏改要么自行拍板。
- 修正方向：§2.7 收口清单补列三处（provisional.py:22 指针、encounter.py:67 docstring〔随裁定分支〕、flow.py:598 句）；landing 3.2 文件面在保留分支补 provisional.py。

### R2-F8 [严重度:低] landing 正本更新清单对 04 号稿的改动范围越出 design §2.9（两处各自演化）
- 位置：landing 正本更新清单 04 号稿行（「裁定 9 行『判据正本』指针改策略层；**授权辖域表述补『判据结构确认载体 = 对抗审查』分层**」）；对照 design §2.9 04 号稿条（仅指针替换）
- 发现：landing 给 04 号稿（宪法 §5 约束单一源表点名的授权对账表）安排了 design 未载明的第二处内容修改——向裁定行补分层表述。iteration-design §3.1「设计改 → 小节改 → 账本跟着改，禁止两处各自演化」；正本（授权表）的内容修改决策应先落 design §2.9。改动方向本身与 §2.2 分层申报一致，属落地文档单方面扩权而非内容错误。
- 修正方向：二选一对齐——design §2.9 的 04 号稿条补该增量；或 landing 删去增量、只留指针替换。

### R2-F9 [严重度:低] §2.2 决策序「刷新阀（§2.6）」内指针错位，刷新阀正节为 §2.5
- 位置：design §2.2 决策序第 3 步（「`不足` → 可及集空 → 刷新阀（§2.6）」）
- 发现：刷新阀的定义节 = §2.5（「建议刷 = 且仅 = 可及集空 ∧ gs.encounter_refresh_left ≥ 1…」）；§2.6 是输出契约与接线，不含阀判据。§2.2 其余指针（窗口变体、收敛申报）指向正确，仅此一处错段。
- 修正方向：改「（§2.5）」。

### R2-F10 [严重度:低] 验收锚 6「r7 奖励行不入窗」节点标签错（P1 r7 = 遭遇，r8 才是奖励）
- 位置：design §2.12 验收锚点 6（「P1 首遭遇帧窗口 = r4/r6 两场普战，r7 奖励行不入窗」）
- 发现：直调 `cw_node_schedule.py:28-31` P1 序列 = reward/r1、reward/r2、battle/r3、battle/r4、supply/r5、battle/r6、**encounter/r7**、reward/r8、boss/r9。锚点前半（r4/r6 两场普战）经序列逐位核算成立；「r7 奖励行」与自引真值表矛盾（r7 是遭遇节点自身——本意应为「遭遇帧自身的遭遇行尚不存在/不入窗」）。验收锚要被逐字执行，标签错会卡住核对。
- 修正方向：改「r4/r6 两场普战入窗；r7 遭遇行（本帧）与奖励行均不入窗」。

### R2-F11 [严重度:低] 「已裁定维持候选 A」无裁定指针（权威词与出处双缺）
- 位置：design §2.10（「窗口候选（已裁定维持候选 A：普战窗口）」）
- 发现：本项目「裁定」= 用户/编排者权威动作，在册裁定一律带主体+日期（宪法两条均标「用户裁定 2026-09-23」；04 号稿裁定表带逐项确认日期）。该处「已裁定」无任何指针；从 README 过程叙事反推，它实为首轮对抗审查的修订处置。处置对抗发现 ≠ 裁定，权威词溢出 + 依据未就地标注（写作硬规则 1）。取舍实质（等价性论证 + 变体触发器登记）已在节内完整在场，故低。
- 修正方向：改「维持候选 A（首轮对抗审查修订处置；等价性论证见上）」，或补真实裁定指针。

### R2-F12 [严重度:低] 正本更新清单引用不存在的画面文档路径 `docs/game/screens/货币战争-遭遇节点.md`
- 位置：design §2.9 末条、landing 正本更新清单末行
- 发现：glob + 目录直调 `docs/game/screens/`——无任何 `*遭遇*` 中文命名文档；遭遇屏画面文档实址 = `currency_war_encounter.md`（英文 id 命名，与 screen_info `currency_war_encounter.yml` 同 id 系；「货币战争-遭遇节点」是 screen_id/归档帧目录名，非文档文件名）。设计把 screen 名当成了文档路径——正是全量同步复查「文件面真实路径」检查项的靶形。同条目另两路径（`screens/encounter.md`、`docs/game/screens/currency_war_encounter.md`）实存且确含待改句（encounter.md:12 决策委托句直调在册），更新面不丢失，故低。
- 修正方向：删除该死路径条目（currency_war_encounter.md 已覆盖）；或改注「画面文档实址 = currency_war_encounter.md，screen 名与文档名不同系」。

## 零发现面申报（实际攻击过的面清单）

以下各面经直调核查**无发现**：

1. **生产暗装核直调**：六标定槽字面全 None（cw_encounter_selection.py:47-64）、暗装门序先于 κ_S（:375-385）、暗装 = 最低档+零刷新+`e3-simple|dark-install:` 归因（:367-373）——§1 症状 1/2 逐句与码相符。
2. **三核并存现状**：kernel 旧核（cw_events.py:99-155，词缀轴消费 `affixes`、P3 字面量分支 :137 在册）；EV 核（encounter.py，EV 式 :8、双槽 fail 向申报 :56-59）；bridge 覆写接线（bridge.py:252-285）——三核定位与「生产从未生效」申报成立。
3. **EV 核 EncounterPick 依赖计数**：import :81 + 签名/构造六处（:264/:268/:280/:306/:308/:387）——设计「六处」计数正确（grep 漏 :280 注解行，read 补齐后核实）。
4. **§2.1/§2.3/§2.7 符号归属唯一性**（首轮 F5 修复面）：`_kappa_state`/`_FILL_EDGE_THRESHOLD`/`PROGRESS_BAR_DIRECTION`/`BAR_SEMANTICS`/`apply_calibration`/`reset_calibration`/`reward_tier`+四档常量/`_lowest_idx` 三处口径一致（连体迁策略层）；`g_ratio`/`_d_enc_snapshot`/`_Diagnostics`/四退役槽三处口径一致（物理删除）。
5. **消费面 grep 定谳**：`last_normal_battles` 生产消费唯一 = 判据本体（:390）；`record_settlement_row` 单一写端 = cw_screen_battle_wait.py:305/330（W239 汇合点 docstring 在册）；`encounter_tier_score` 唯一生产消费 = 旧核 `_score`（cw_events.py:128-146）；`marginal_value` 唯一消费链 = encounter_tier_score（cw_survey19_hooks.py:14/24）；`DifficultyAccount` 全仓零生产消费；`apply_calibration`/`reset_calibration` 零代码外部引用（注释指针问题见 R2-F7）；EVENT_PICK_TYPES/EventPick 零 src 消费方（摘位申报的 NameError 风险 :538-543 属实）；EncounterOption 测试仓恰五文件引用（game_state_consume/obs_arch_event_screens/route_clear/screen_report_ports/world_decl）——「五方引用」属实。
6. **op/动作链零耦合**：`CwActionPickEncounterOp` 静态入参 = 词表动作、`idx = action.idx` 鸭子消费（cw_pick_encounter_action.py:54/67）；`report_action_pick_encounter_param(gs, param: Any, sig)` 鸭子取 idx（pick_encounter.py:47/58）；重调链现状（cw_screen_encounter.py:180-195）与 §2.5「重调同输入同输出→零点击终结」论证相符；闸内嵌后 op 层零行为改动结论成立。
7. **测试面申报**：test_cw_unified_action_4.py :28 import、:259/:278 构造——行号属实；test_cw_obs_arch_event_screens.py :417-419 仅 import 保留面符号（零改动正确）、:380-404 重调零点击行为锁在册（docstring 收口义务已列）；test_cw_sim_backend 经 SimpleNamespace 鸭子喂入不受影响。
8. **sim 面**：`encounter_options()` :528、遭遇观察 `refresh_left=None` :1378、结算环零写端（sim/ 全目录 grep 零命中）、`ENCOUNTER_TIER_COUNT=4` :488——sim 盲区申报（「逐位一致」）除 R2-F3 档位标签外成立。
9. **GameState 容器面**：settlement_ring :2132 / encounter_log :2135 / encounter_refresh_left :2161 / encounter :2298 / chosen_encounter :2339 / enemy_difficulty :2126 全在册，§2.1 保留面与读口清单完备。
10. **判据源逐字核对**：00_framework §1 第 5/6 条（含「用户裁定 2026-09-23」与判据线原文）；04 号稿 §7 表第 9 行原文——「判据正本 = kernel/cw_encounter_selection.py」为登记从句（「持久化形态生效即登记…；判据正本 = …」），设计「载体登记≠结构授权」读法与原文相容；「例外扩大程序完成」「用户 2026-09-12 逐项确认」逐字在行；op-layer.md §1.4 剩余语义（None = 未观察、节点屏闸 None = 拒刷）相符；p64 状态节辖域原文（「辖域 = 静态 dict[敌方难度读数→stat] 形态，条件表形态不在辖域」）——DELTA_T「引申申报，非 P64 原文结论」的表述如实；自由项 B/q/s/m 在 p64 证明节 :24 在册。
11. **proofs 索引**：P15v2 boss 26.79/普战 10.45（math_proofs.md :27）；P26 待证明双挂账（Δp_prep 条件表 + L_node 分位口径，:38）与 §1/§2.9 引用逐字相符；P85 A/B 分键「不消费选档输出」的零影响申报与索引行判据面（N×G×R）不冲突。
12. **规范源**：strategy-work §2.4「2026-09-05 用户裁定：玩家过目门删除，符合策略核心即可落码」逐字相符（§2.2 合法性载体引用）；§1 零调参——本批零新数值申报成立（0.5/cap 2/6/t≤4/tier 4/窗口 2 全为在码现值直调核对，激活非新增）；§6 prereg 完整性——§2.12 验收线保全申报（盘点入口三件 + sim 盲区 + 判读锚事前写定）合门。
13. **先例批承接**：env 批 design §1 :18「遭遇等其余画面…后续批」、补给批 design §1 :26 同口径——§0 承接指针实指；补给批已落地证据链（25 号稿头注 :6、30_supply_screen.md 存在、README §2 含 30 行、导航句「18-30」:56、cw_survey19_hooks 无 supply_reroll_decision）全部直调成立。
14. **文档面现状**：13 号稿 :21「双轨」过期描述属实；08 号稿 E3 行结构（现有语义格/待 derive/P26 锚）与 §2.9 改法对位；25 号稿画面族现存 8 屏（:3 逐名清点）与拆分头注先例（28/29/30 行式）；31 号稿编号未被占用。
15. **画面知识**：敌人信息浮层入口②（选中卡→查看详情→X 关回）与「OCR 全可读」（货币战争-敌人信息浮层.md :9/:31-33）——§1 不解决面与 §2.11 点亮路径描述相符；combat.md §3「遭遇奖励 = 伤害进度达标制，非清场制」（:38-39 在 §3 节内）；economy.md §10.2 P1/P2 boss 均位面末节点（:132-133）——「boss 后无遭遇决策点」成立。
16. **治本核验**：§1 归层（分层语义 = 宪法五存量 + 表示层暗装门粒度）经代码逐符号证实成立；§2 主干（判据本体迁策略层 + 三核收敛 + 门收窄）修根非症状；逐画面迁移 = 宪法六既定节奏（第四批），跨件半问不触发。例外 = R2-F1（obs 注册表错置的根只搬半截）。
