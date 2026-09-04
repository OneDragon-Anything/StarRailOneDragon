# 09 架构统一篇（契约 / 插件 / 管理器 / 注册壳）

> 塌缩来源：`archive/design/CONTRACT_SERIES_DECISION.md`（序列决策契约 v2，已冻结）+ `archive/design/CONTRACT_V2_PROPOSAL.md` + 换核迁移序批件（redesign/reports/core_swap/）。本篇把散落三处的架构语义收为统一篇：**契约、管理器、实现、注册壳四身份分离，单一核 mandate_v1**（REVIEW §2.1 归属混乱的修复位）。
> 前置阅读：[02_mandate_layer.md](02_mandate_layer.md)（骨架层）、[03_strategy_layer.md](03_strategy_layer.md)（策略语义——本篇只管「语义怎么被发射/装配」，不管判据内容）。

## 1. 四身份分离（谁是契约、谁是管理器、谁是实现、谁是注册壳）

| 身份 | 载体 | 职责 | 禁止 |
|---|---|---|---|
| **契约** | `strategies/impl/cw_strategy.py` 的 `CwStrategy` ABC（接口定义）+ 序列决策契约正文（§2） | 定义策略器与流程侧（画面 op）之间的全部接口：17 个钩子（§3）+ 序列语义（§2） | ABC 自身不含内置逻辑（纯接口，全 abstract） |
| **管理器** | `strategies/impl/cw_strategy_manager.py`（StrategyManager） | 按 config.strategy_id 实例化/选择策略；值域 = {decision_v2, mandate_v1}（构造期校验 + save 持久化）；ev_arm 开发字段 {skeleton_only, full} | 不承载判据；不知道策略内部结构 |
| **实现** | `strategies/impl/mandate_v1/`（新核 cw4 包：entry/proof/bridge/shop/criteria/statefn 分层）+ `strategies/impl/decision_v2/`（冻结基线，A/B 臂③） | 决策本体：证明层/骨架层/EV 层/状态函数按 00-08 的分层语义落码 | 禁自实现生命周期机制（幂等键/连败恢复/屏蔽/stall 门——归流程侧框架）；禁绕过契约自造接口 |
| **注册壳** | `strategies/mandate_v1_strategy.py`（MandateV1Live，照抄 DecisionV2Live 模式，__module__ 守卫壳子类） | 把实现包注册进策略扫描器（STRATEGY_ID 元数据 + 装配链覆写 `_assemble_turn` 注入） | 壳内零判据逻辑——只做注册与装配接线 |

**单一核**：现行策略核 = **mandate_v1**（cw4 分层包）。decision_v2 为声明的 A/B 基线臂，**A/B 过线 = 整体删除旧决策包的触发门**（用户裁定 2026-08-31；时序裁决 dd-001）——旧包是冻结共存基线，不是残留。换核机制 = config 切 strategy_id（最小面），不改流程侧分发。

## 2. 序列决策契约（画面 op ↔ 策略器）v2 摘要

（冻结正文 = CONTRACT_SERIES_DECISION.md；本节收条款骨架，冲突时以冻结件为准。）

- **动作发射类接口**两条：备战线 `decide_prep_screen(session, config) -> list[PrepAction]`；商店线 `decide_shop_screen(session, config) -> list[Action]`。执行序 = 列表序；生产接口 = 裸 list（Decision/AtomOp 层不进生产接口，仅存 sim/离线驱动）。
- **观察帧黑板**：画面 op 侧把本帧观察写入 session 黑板（prep_obs_frame / shop_state_frame；画面 op 是唯一写者），然后调用一个决策接口；策略器读黑板、禁自取屏；**观察帧缺失即抛错**（禁静默按空观察决策）。
- **序列语义**：**帧稳定域**（核心条款）——序列内第 i+1 个动作不得依赖第 i 个动作执行后的新观察；发射时逐动作判「执行后画面状态能否静态推出」，推不出即截断（该动作可作最后一个发出）。**fail-stop**：任一动作未落地 → 余下丢弃 → 流程侧 heavy 重观察重调接口。**逐动作验证保留**（期望态对账/执行验证照跑，不依赖重决策）。
- **截断规则**：商店线域与备战线域（PrepAction 17 具体类逐类判）分域枚举——BuyCard/LevelUp 可续；拖拽族条件续（bench 索引结构恒稳 + 名-槽一致性复检）；RefreshShop/CompTransaction/合成触发/开箱/开典籍/overlay 类 = 截断点；**未识别动作 fail-closed**：词表外/无分类动作处截断 + 计数披露（禁不可观测静默截断），缺口须回契约改版补条目，禁只改代码。两域表 + fail-closed 条款 = 已枚举动作类的完备判；词表演进由 fail-closed 兜底。
- **空批与控制流**：空序列合法（商店线 = 决策完成触发关店；备战线处理归流程侧框架）；策略器**禁用空批表达控制流**——控制流走词表内特殊动作（DeferSpheres 族，defer 计数归框架）。
- **职责分界**：观察帧写端/执行/验证/截断响应/生命周期（幂等键 action_key、连败→恢复→屏蔽、stall 门、强制出战）全部归流程侧；策略器只做「帧稳定域内出计划序列 + 判截断」。
- **版本纪律**：契约冻结后任何条款改动动版本号，禁静默改义；契约是接口冻结件不是策略开关——行为输入未就绪的过渡臂走策略开关生命周期门。
- **sim 消费面注记**：sim 仅消费 update_target + decide_shop_screen——**sim A/B 的证明面 = 商店波经济决策**；prep 屏编排域在 sim 无实体真值源，其正确性防线 = 契约锁 + 适配器零漂移门 + 实机，不在 sim A/B 辖内。

## 3. CwStrategy 17 接口（钩子全景）

ABC 全 abstract、无状态策略（实例不持有可变每局状态，跨步状态走 StrategySession——框架每局新建、局终销毁；构造无参，配置按参传入）。钩子四组：

**生命周期 4**：

| 钩子 | 语义 |
|---|---|
| `create_session(config)` | 每局开始调一次，返回空白 StrategySession（rng 由 run loop 覆写） |
| `on_match_start(state, session, config)` | 每局开始（首次截图后），初始化跨步状态 |
| `on_round_end(state, session, config, obs)` | 每场战斗后（观测驱动），performance 记录 |
| `on_match_end(session, config, outcome)` | 每局结束收尾 |

**战略 1**：`update_target(state, session, config)`——选/转型 target_comp；框架在每个备战回合 decide_shop_screen 之前调一次；实现写 session.target_comp（首轮选、其后按信号 pivot、无强信号保持）。证据门/换线机器（03 §4.2/§4.3）的接线载体。

**序列决策 3**：`decide_prep_screen`（备战黑板序列契约，见 §2）；`decide_shop_screen`（商店序列契约，空序列 = 决策完成触发关店；词表 = BuyCard/LevelUpShop/RefreshShop/SellBench/SellDeployed/CompTransaction/拖拽族）；`decide_prep_action`（deprecated 兼容期薄委托：旧单动作签名 → 写黑板 → 委托序列核解包首元素；调用方迁移完随 P5 删除）。

**pick 族 9**（选项决策，动作编排归画面 op，不在序列契约辖内）：

| 钩子 | 事件面 |
|---|---|
| `decide_invest(kind, options, ...)` | E1/E2（投资环境/策略三选一） |
| `decide_supply(options, ...)` | E4（补给，OCR 未就绪默认委托） |
| `decide_encounter(options, ...)` | E3（遭遇难度，已接线 cw_events） |
| `decide_megastar(options, ...)` | E7（巨星，OCR 未就绪） |
| `decide_partner(options, ...)` | E6（伙伴/领航员，OCR 未就绪） |
| `decide_planner(options, ...)` | 策略规划类选项（cw_events） |
| `decide_star_tome(options, ...)` | 星徽典籍四选一 |
| `decide_wish_trial(options, ...)` | 圣杯试炼二选一（E5） |
| `decide_box_card(names, ...)` | 武装箱选卡（PickBoxCard） |

共 4+1+3+9 = 17。pick 族返回 PickEvent 系载体（选项决策，不进截断表）；新事件面优先评估归并进既有 pick 钩子或走契约改版，禁旁路自造接口（遭遇分支刷新的 pick.refresh 旗标泄漏 = 已登记的后续收编候选）。

## 4. 装配与依赖矩阵

- **依赖方向**：实现包 → 知识层/数学层/执行层单向；分包依赖矩阵禁 decision→obs 直依（obs 读口经 app 桶装配点 install_obs_ports 注入）；决策本体 = 纯函数（bridge.decide_from_turn），装配链由注册桥壳覆写注入（app 桶）——依赖矩阵合规分拆的既定模式。
- **装配点**：obs→Snapshot 装配半部在 app 桶（decision_assembly）；黑板单一写端纪律保持；`_RESET_PHASE_ROUND_CACHE` 注入槽（缺省关）+ `discard_stale_match_container`（异常路径残留容器弃置，ADR-0419——session 全量重建 by construction）。
- **gated_hp**（结算 HP 新鲜度门，r68/r69 单源 helper）：结算真值仅在可信窗口内覆盖现读——观测质量门，非决策输入（04 §7 表 #6）。

## 5. 三臂 A/B 与换核时序

- **三臂结构**（判前锁 v6 口径）：单被测体两因子 strategy_id∈{decision_v2, mandate_v1} × ev_arm∈{skeleton_only, full}；三臂 = ①mandate_v1/skeleton_only ②mandate_v1/full ③decision_v2 基线。预指定主对照 = ②−①（EV 增量，命题 B）；次对照 ①−③（命题 A 非劣参照，仅描述性）。
- **归因域限定**：sim 引擎唯一决策入口 = decide_shop_screen ⇒ 归因域 = shop 决策面（prep 面 sim 不可达），结论不得外推为全决策面处理效应。
- **判读硬前置**（判前锁 v6 检查单）：任一行未落地 ⇒ 正式 A/B 被 raise 拦死（排程层防零刷新事故复发）；强制披露清单（fail-closed 关闭面的拒因计数——U_X/T_SEARCH_A 豁免 ⇒ EV 买/压库/凑息卖/换线塌缩五面两臂恒等关闭，headline 必须随附该降级分量）。
- **遥测分栈**：DecisionTrace 按 (strategy_id, ev_arm) 二元组分栈；mandate 标记维度区分骨架/EV 动作（命题 A/B 分离判读的载体）。

## 6. 修订纪律

本篇收现行架构语义；契约条款变更走 CONTRACT_SERIES_DECISION 版本号（v1→v2 先例）；策略包结构变更（cw4 内部分层）走实现 ADR + 本篇修订；判据语义变更归 00-08 各篇 + ADR（三同步纪律：ADR + as-built 正文 + 代码注释引 ADR-NN）。
