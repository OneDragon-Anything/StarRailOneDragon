# AUTHORITY.md —— 货币战争设计文档:唯一权威声明(现行语义信谁)

> 本文是 `docs/develop/currency_war/` 的**树根权威裁决文件**。回答三个问题:
> ①现行策略语义的权威载体是哪些文件;②历史文档可信到什么程度;③一个数字要满足什么条件才能进决策门。
> 任何与本文冲突的「自称现行」表述(各文档头部状态声明)一律以本文为准。
> 依据 = 设计评审批裁定书(`.debug/temp/currency_war/design_review/REVIEW.md`,B 档:局部重设计)与执行架构测绘(`.debug/temp/currency_war/execution_architecture_map/MAP.md`)。

---

## 1. 现行语义权威载体(唯一可信集)

**现行语义的唯一权威 = 以下可读设计本意件 + 代码 as-built。**

| 层 | 文件 | 权威辖域 |
|---|---|---|
| 哲学/约束单一源 | `archive/design/lambda-risk-philosophy.md`(λ 哲学) | λ_death 使用纪律、hp/战力辖域硬闸门(§2:仅 λ 表与 P15 掉血公式两处授权消费 hp/战力数据,其余须用户逐项确认)、发展优先默认+危险只升不降姿态(§3) |
| 数学框架总纲 | `archive/design/NEW_MATH_FRAMEWORK.md`(NMF) | 公理栈(§1)、零调参审计与数字三形态(§3,见本文 §3)、用户裁定亲录节(裁定一/二/三+血线地板挂账,NMF:331-349) |
| 骨架层根设计 | `archive/design/DESIGN_MANDATE_LAYER.md`(MANDATE) | 三层权限模型(§3.1)、骨架义务 M1-M7、输入缺失按动作可逆性定向 fail(§3.4) |
| 策略层正文 | `archive/redesign/01_strategy_layer.md`(逐篇地位见 §2) | 买入六序(§4.1)、证据门与换线(§4.2-4.3)、经济引擎(§4.4)、卖出(§4.5)、装备(§4.6)、事件目录 E1-E15(§4.9)、机制突变(§4.10)——其中 §4.7 已被 supersede(见 §2) |
| 专项设计件 | `archive/design/comp-selection.md`、`archive/design/CONTRACT_V2_PROPOSAL.md` 与 `archive/design/CONTRACT_SERIES_DECISION.md`、`strategy/12_blood_budget_semantics.md`(血预算数学)、`strategy/13_buy_face_design.md`(P55/P56/P57 买面命题+预注册判据) | 各自辖域内的现行设计 |
| 数学证明 | `proofs/`(math_proofs.md 索引 + p01-p57 本体 + validations/) | 一切「多少算够」的定价权威;策略命题权威=证明与 sim/实机实证(ADR-0482 口径) |
| 游戏事实 | `docs/game/currency_war/`(research/) | 游戏机制与攻略知识 |
| 代码 as-built | `src/sr_od/application/currency_war/`(结构与契约以代码+`decisions/` ADR 为准) | 实现事实的唯一源;**旧代码不作设计正确性证据,只作「当时实现了什么」的史实引用** |
| 策略 as-built 正文 | `strategy/`(README+01-11 v2 as-built;12/13 现行设计件) | 「系统现在是什么」的正文家;01-11 各篇按 §2.3 逐篇判新旧,其中 v2 as-built 篇在结构统一(迁移批)完成前仍描述活路径的继承域 |

**archive/ 的双重身份声明**:`archive/` 整体是**只读历史档案**(禁新增内容、禁承载新语义),但其中 `archive/design/` 的**可读设计本意件 6 件**(λ哲学/NMF/MANDATE/comp-selection/契约两件)与 `archive/redesign/01_strategy_layer.md` 的现行节,在其辖域内**仍是语义权威**——归档的是「载体树」,不是「语义」。区分判据:读它们是为了拿现行判据=合法;往里写新语义或把「IMPL_DESIGN 说了什么」当论证=违规。

结构事实(MAP.md §1.1):现行实机栈 mandate_v1 是 DecisionV2Strategy 的子类,只覆写备战与商店两个决策域,其余决策域(意向/投资/遭遇/补给/巨星等)经继承活在 v2 代码上;迁移批正在做结构统一。**因此「读哪个设计文档」与「跑哪段代码」是两个问题——设计语义一律以上表为准,不因代码尚在继承过渡而回退读旧设计。**

## 2. 代际裁决表(四代文档各自地位:现行 / 历史 / 归档只读)

### 2.1 第四代·现行:顶层活文档

| 位置 | 地位 |
|---|---|
| `strategy/`(README+01-11 v2 as-built) | **现行 as-built 正文**(v2 as-built 篇在迁移批完成前仍描述活路径的继承域;其中 `01_posture.md` §6-§7 的 HP_LOSS_MU 掉血先验表与 p_win_p2 胜率映射是判据 1(禁战力建模)违例形态,**该两节禁作任何设计消费**,REVIEW §2.4) |
| `strategy/12_blood_budget_semantics.md`、`strategy/13_buy_face_design.md`、`strategy/11_tools_usage_design.md` | **现行设计件**(锚定新核 cw4;12 的 hp 直读停手线带确认通道标注,见 §5) |
| `proofs/`、`prereg/`、`decisions/`、`config.md`、`sim/` | **现行**(各按其职能:证明/预注册/ADR/配置语义/sim 设计) |
| `AUTHORITY.md` | 本文(裁决表唯一家) |

### 2.2 第三代·归档只读但语义仍权威:`archive/design/` 与 `archive/redesign/`

- `archive/design/` 可读本意件 6 件(lambda-risk-philosophy / NEW_MATH_FRAMEWORK / DESIGN_MANDATE_LAYER / comp-selection / CONTRACT_V2_PROPOSAL / CONTRACT_SERIES_DECISION)——**现行权威**(辖域见 §1);design_economy.md/design_latch.md 现行判据细节,正文带 R 系勘误标链,读法=以 design_economy §E4.2 canonical 表为骨架核现行口径,标链只当修复史。
- `archive/design/` 堆叠 4 件(**IMPL_DESIGN.md / IMPL_FIX_LEMMAS.md / design_telemetry.md / IMPL_HISTORY.md**)——**只读历史档案,不再承载现行语义**。它们曾是语义权威实际所在地(~2.5MB、R1-R189 勘误标链),读出「现行语义」需重放 190 轮修复史,已丧失可执行性。合法用法仅两种:①查某条判据的修复史/证据链出处;②按 NMF/λ哲学/MANDATE 给出的指针核对某节的现行口径。**任何批次不得再把新语义写入这四件,也不得把「IMPL_DESIGN 说了什么」当作设计论证**。
- `archive/redesign/01_strategy_layer.md` —— **半现行**:§4.1-4.6、§4.9-4.10 = 现行策略层正文(权威辖域见 §1);**§4.7 已被 supersede**(现行口径=`archive/design/lambda-risk-philosophy.md` §2 硬闸门 + NMF:335 裁定二,文内已加回灌标注);§4.2-4.3 内嵌的 R78-2/R81 位面补条待通用化重写(REVIEW §4.1),读时按「目标态=当前生效档缺口,位面只是参数」理解;§7 的「绿地不共存」工程路线已被 R189 换核重切取代(MAP.md §④)。
- `archive/redesign/` 其余(02/03/IMPL_HISTORY/NAVIGATION/OBS_SUPPLY_INVENTORY/REORG_COVERAGE_MAP/README + reports/ 313 件)——**仅史实**(工程过程件与证据档案,按引用查证用,不承载语义)。

### 2.3 第二代及更早:`strategy/` 内的 v2 as-built 篇

strategy/README+01-11 自称「描述系统现在是什么」——在迁移批(结构统一)完成前,其中描述活路径继承域(意向/投资/遭遇/补给等,MAP.md §②)的篇仍是对现状的准确描述;但**新设计一律不写进这些篇**(新设计件落 strategy/ 新编号或 ADR);迁移批完成、继承域收编 cw4 后,01-11 的 v2 as-built 篇整体转历史。v1(决策 v1 族)与 v0 无独立文档树,史实只见 ADR。

### 2.4 判据总结(一句话版)

现行语义信:§1 表所列文件。历史信到什么程度:修复史与证据链可查、现行口径以指针核对、堆叠件禁当论证。数字什么条件能进决策:过 §3 三形态门。

## 3. 章程:数字的三形态(重 derive 批的宪法)

**任何进入决策门的数字,必须显式标注三形态之一;无标数字不得进决策门,违者=违宪。**(基础=NMF §3 零调参审计:框架内没有裸拟合常数充当闸门,NMF:169-197。)

1. **【注】游戏定义值** —— 游戏注册表里的机制真值(概率表/经验门槛/牌池构成等)。用法:代码直调注册表,单一源在代码;不推导、不拟合、不复制进文档(文档只写常量名)。示例:REFRESH_PROB、XP 门槛表(NMF:173)。
2. **【推】已证推导值** —— 由注册表值经已证命题(闭式/递推/DP)算出的量,无自由参数。用法:必须标注来源命题号(如 P39/P47),数值随注册表重算。示例:L 递推(P47)、E[refreshes](P16)(NMF:175-177)。
3. **【拟】观测估计值** —— 从 sim/实机数据估计的量,必然带不确定性。进决策门须同时满足四件,缺一即不合法:
   - **CI**:带置信区间,禁点值当闸门(NMF:179);
   - **fail-closed 退路**:标定未齐/区间方向翻转时,消费它的判据必须退到安全缺省(拒付/空转/退支配性结构判据),不得用未标定值硬开闸;
   - **标定义务挂账**:写明 owner(哪个批/哪个角色)与期限(对局周期内未决即回炉,REVIEW §4.3-3;13 §2.1 R2-N2 为格式先例);
   - **语境声明**:标定语料的语境(难度/词缀/位面)出域复用属外推,禁(NMF:193 λ 语境声明先例)。

三条硬规则:
- 【拟】形态**允许存在**(挂账登记合法),**不允许无退路地被消费**——「还没标定但先拍个数」在任何形态下都非法;
- 【注】【推】形态也不得绕道:推导链断了就降回【拟】,不得冒充【推】;
- 任何评审/对抗批审数字,第一问=「形态标了吗」,第二问=「【拟】的退路与期限在哪」。

## 4. 冻结与修订纪律(治「冻结文档不冻结」)

- 被标「冻结/已裁定」的节,补条一律走「新设计件 + 本文代际表更新」,不在冻结正文内嵌【提案】【已批准】标注;
- 某节语义被后批覆盖时,**必须当场回灌 supersede 标注**(指针→新权威口径+理由),不得让冻结文本以活跃姿态携带旧律(本次已补两处:01 §4.7、strategy/12 停手线,见 §5);
- hp/战力辖域类争议的唯一裁决口径 = λ 哲学 §2 硬闸门 + NMF:335-337,冲突时不再回读旧禁令文本;
- `archive/` 只读:任何批次不得改写 archive/ 内文件内容(本文 §1 声明的语义权威件如需修订,先在本文登记迁出计划,由编排者裁决后整体迁回活区再改)。

## 5. 已完成的回灌登记

| 位置 | 回灌内容 |
|---|---|
| `archive/redesign/01_strategy_layer.md` §4.7 | supersede 标注:hp 绝对禁令已被 λ 哲学 §2(硬闸门授权面)+ NMF:335(裁定二根因声明)取代;hp 不作入参的根因=无法对战力/胜负建模,例外面须逐项用户确认 |
| `strategy/12_blood_budget_semantics.md` 停手线定义处 | 确认通道标注:hp 直读停手线属裁定二「授权两件之外」的 hp 直接触发形态,与 NMF:337 血线硬地板挂账同通道,待玩家确认(确认前按设计件现状,不落码) |

## 6. 文档树重画:已执行记录(2026-09 重画批)

本节原为方案,现按用户裁定**已执行**,记录如下:

**目录形态(git mv 迁移,保留重命名历史)**:
- `redesign/` → `archive/redesign/`(整树,含 reports/ 313 件);
- `design/` → `archive/design/`(整树,含堆叠三件 IMPL_DESIGN/IMPL_FIX_LEMMAS/design_telemetry);
- `sim-power-model.md`、`sim-wiring.md` → `sim/`(两件是现行 sim 设计件而非历史档案:sim-power-model=ADR-0512 需求定义件、sim-wiring=as-built 接线底账,故新建 `sim/` 归位,不入 archive);
- `config.md` 留顶层(现行配置语义单一源);`strategy/`、`proofs/`、`prereg/`、`decisions/` 不动。

**引用修正**:全仓 `docs/develop/currency_war/redesign|design` 绝对路径引用已改指 `archive/`(docs 内 decisions/proofs/互链 + src 注释 21 文件);根 README 目录节重写;本文件路径随迁更新。归档树内部的历史互链不改(史档原貌保留)。

**后续未执行项**(留给重 derive/迁移批,非本批辖):语义塌缩重刻(堆叠件现行口径塌缩为干净正文,REVIEW §4.1)、strategy/01_posture §6-§7 拟合表 ADR 记档后处置、R78-2 位面补条通用化重写、事件面/引擎池/meta 三个完备性空洞立项。
