# 货币战争策略设计 · 唯一现行入口（strategy-docs）

> 本目录是货币战争（CW）**策略设计的唯一现行家**：每个画面结合哪些数学证明、怎么产出决策的设计语义都在这里，与代码现状保持一致。
> 读者 = 无会话历史的工程师/智能体。术语首次出现时给定义。
> **职责分界（用户裁定）**：本目录只管"每个画面结合哪些数学证明、怎么产出决策"；**流程控制（画面路由/访问相位/动作发射/守卫）单独立文档 = `../flow/`**。

## 1. 这套文档回答什么问题

「两个工程师独立实现，会得到同一个策略」——这是全链合格线。为此本链做到：

- 每个机制规格无歧义（判据、触发、辖域、边界逐条写明）；
- 每个进决策门的数字带**三形态标注**：【注】游戏定义值（注册表直读）/【推】已证推导（引命题号）/【拟】观测估计（必须带置信区间 + fail-closed 退路 + 标定义务 owner 与期限）；无标注数字不得进决策门；
- 每条论断可回溯（命题号 → `proofs/math_proofs.md` 索引 → 单篇证明；命题集与各命题状态一律以该索引为准——编号有空洞、个别命题有退役/撤回状态，勿按编号连续性推断；或「文件:节」出处）。

## 2. 阅读顺序（总纲先读 → 分篇按决策点）

### 总纲（依赖序）

| 篇 | 文件 | 一句话 |
|---|---|---|
| 00 | [00_framework.md](00_framework.md) | 哲学与约束：发展优先默认、危险信号只升不降、hp/战力辖域硬闸门、约束单一源 |
| 01 | [01_math_framework.md](01_math_framework.md) | 数学框架（NMF 塌缩）：公理栈五条、七面判据、数字三形态章程、两条总纲级不变量 |
| 02 | [02_mandate_layer.md](02_mandate_layer.md) | 骨架行为层：三层权限模型、骨架义务 M1-M7、输入缺失按可逆性定向 fail |
| 04 | [04_survival_budget.md](04_survival_budget.md) | 生存预算统一件：血预算数学 h>d·L_c 为唯一模型（12 号件塌缩 + 01 §4.7 重述） |

### 分篇（按决策点）

| 篇 | 文件 | 一句话 |
|---|---|---|
| 10 | [10_prep_decisions.md](10_prep_decisions.md) | 备战画面决策：部署/装备/腾席判据 + 共同地基（机制速查/形式刻画/注册表形态） |
| 11 | [11_shop_decisions.md](11_shop_decisions.md) | 商店画面决策：买入六序、买面（P55 阶段 2 已撤史实/P56 现行）、引擎池、卖出、刷新、升级、经济引擎、机制突变 |
| 12 | [12_line_and_intention.md](12_line_and_intention.md) | 换线与意向：生命周期状态机、证据门与通用目标态定义、换线机器四触发 |
| 13 | [13_pick_family.md](13_pick_family.md) | pick 族薄判据：九接口决策规格 + 事件面目录 E1-E18 |
| 14 | [14_p1_consume_arms.md](14_p1_consume_arms.md) | P1 经济循环消费臂：闲置金转战力的三发射通道（买/升/刷）设计与硬前置裁决 |
| 15 | [15_observation_multisource_arbitration.md](15_observation_multisource_arbitration.md) | 观察层读数多源一致性与仲裁：双源冲突的采信规则、留证与布局档错位 |
| 16 | [16_evaluation_tables_reassessment.md](16_evaluation_tables_reassessment.md) | 评估表体系重估：选卡/选项分数常量族的保留/改形/退役裁定与重 derive 挂账 |
| 17 | [17_stall_form_spend_authority.md](17_stall_form_spend_authority.md) | 落后即消费族：无可追件∧富金∧落后形态（Φ_stall）的支出授权面 |
| 08 | [08_events.md](08_events.md) | 事件面规格骨架：E1-E18 逐项收录语义、数学判据逐项标「待 derive」（落差登记） |
| 07 | [07_meta_run.md](07_meta_run.md) | 跨局 meta 域：显式声明出辖（当前无可设计对象，登记为未来立项） |
| 18 | [18_equip_wear_semantics.md](18_equip_wear_semantics.md) | 装备穿戴策略语义：RunEquip 穿戴定谳、opening/非 key_equips 释放判据、词缀条件分配优先级 |
| 19 | [19_reinforce_channel_and_survival_discount.md](19_reinforce_channel_and_survival_discount.md) | 补强通道与生存折现重估 |
| 20 | [20_large_balance_must_spend.md](20_large_balance_must_spend.md) | 大额结余必花域与旱期金出口分层 |
| 21 | [21_opening_window_and_tool_consume.md](21_opening_window_and_tool_consume.md) | 装备策略残余：opening 期释放门收窄 + 工具件消费语义（承 18 号稿） |
| 22 | [22_prep_screen.md](22_prep_screen.md) | 备战画面策略面：收缩后动作清单(含商店期移入的卖备战/买经验)+ 判据指针(判据本体 = 10/02/04/18) |
| 23 | [23_shop_screen.md](23_shop_screen.md) | 商店开画面策略面：买/刷/关收缩动作面 + 满席腾位链 + 能力/策略判例(判据本体 = 11) |
| 24 | [24_deploy_segment.md](24_deploy_segment.md) | 部署执行段策略面：选人围栏/换血卖出/残余补部署(判据本体 = 10 §1/02 §7) |
| 25 | [25_event_overlays.md](25_event_overlays.md) | 事件面画面(投资环境/投资策略/单选族)策略：选卡 + 刷新建议(判据本体 = 13/08) |
| 26 | [26_battle_settlement.md](26_battle_settlement.md) | 战斗与结算期策略面：出战标准/结算读数供数/无战斗期独立决策申报(判据本体 = 04) |
| 27 | [27_transit_screens.md](27_transit_screens.md) | 过场与推进型画面(简报/BOSS简报/位面过渡/回大厅)：无策略决策面申报 |

（原 03/05/06/09 已按决策点重排删除：03/05/06 拆入 10-13；09 架构篇整体迁 `../flow/README.md` §2——策略↔流程契约。）

阅读时点：总纲 00/01/02/04 先读；分篇 10-17 + 08 是决策面主干，按所属决策点读；07 是出辖登记篇，随需查阅；18-27 是画面/专项面，判据本体在 10-17 各篇，画面篇头部有指针——做该画面的活时随任务查阅，无需通读。

## 3. 与既有资产的关系（谁管什么，禁双源）

| 资产 | 角色 | 与本链的关系 |
|---|---|---|
| 本目录 `strategy-docs/` | **策略决策设计**（as-designed 现行权威） | 决策判据设计语义唯一现行家 |
| `../flow/`（flow/ 七篇） | **流程控制设计** | 画面识别路由/访问相位/动作发射契约/守卫的唯一现行家；策略↔流程契约（四身份分离、契约成员 13、单动作循环；序列语义为历史注）在其 README §2 |
| `docs/develop/sr_od/application/currency_war/proofs/`（math_proofs.md 索引 + P 系列单篇） | **定价权威** | 一切"多少算够"的数学证明。本链只消费命题结论与状态，不重推、不改写；命题以索引状态列为准 |
| `docs/game/currency_war/research/` | **游戏真值** | 与实现无关的游戏机制事实。游戏版本变了它变，本链引用不复制数值 |
| 代码注册表（`cw_chars`/`cw_shop_odds`/`cw_state` 等） | **机制数值单一源** | 文档只写常量名与语义，值一律在代码 |
| `src/sr_od/.../currency_war/` 代码 | **实现** | 本链是设计，代码是实现；行为变更走三同步 = as-built 正文语义更新 + 代码注释 + 测试（见 sr-od-currency-war-dev skill「文档同步」）；决策 why 进设计文档动机段与代码注释（ADR 档案已退役，仅经用户命令创建） |
| `archive/design/`、`archive/redesign/`、`strategy/` 旧树 | **素材·已删除（4e32b2e4 吸收后删除）·git 历史可溯** | 塌缩素材来源仅存于 git 历史，不再承载现行语义；其中的 R 标链/勘误史不搬入本链 |
| `.debug/progress/` 当前迭代 | 进度与决策 why 挂账 | 进度不进共享文档;决策 why 收敛于设计文档动机段与代码注释(ADR 档案已退役) |

## 4. 宪法：用户四条裁定（每篇都要过）

写任何一篇、采纳任何机制时逐条自检（详述与判读见 [00_framework.md](00_framework.md) §1）：

1. **禁战力建模**：决策依据 = 游戏定义值或核心已定义规则；经验拟合/采样分布不得作决策依据。例外只有硬闸门授权的两件（λ_death 表、P15 掉血公式），且例外扩大须用户逐项确认。
2. **位面只作参数**：位面只允许作（节点数表/伤害锚表/档位表）的查表键进通用模型；任何机制谓词的辖域条件中不得出现位面字面量。按位面枚举机制辖域 = 设计缺陷。
3. **发展优先默认，危险只升不降**：默认姿态 = 发展优先；危险信号（血线硬地板、λ 顾问）只允许把反应提前，禁止推迟；压制发展的机制不得出现。
4. **数学先行**：每个机制规格可证明或显式登记待证假设；数字带三形态；无标注数字不进决策门。

## 5. 本链文档纪律

- 正文 as-designed 无状态：不写进度、变更史、会话快照；修订走「版本号 + 变更记录」节，不在正文内嵌勘误标。
- 直白表述：禁自造黑话；项目术语首次出现给定义 + 例子。
- 历史件出处注：正文引用的 NMF（= NEW_MATH_FRAMEWORK.md）/lambda-risk-philosophy/REVIEW/AUTHORITY/strategy 旧树均为**已删除**的塌缩素材，语义已吸收进本目录；其编号与裁定号考古走 git 历史，现行语义一律以本目录正文与代码为准。
- 引用规范：命题号 P(N) 经 `proofs/math_proofs.md` 索引跳转单篇；文档引用写「文件名:节」。
- 阈值/权重不写死值，只写常量名；值的单一源在代码注册表或标定批。
