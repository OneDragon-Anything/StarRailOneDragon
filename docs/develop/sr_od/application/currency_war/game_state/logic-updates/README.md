# 逻辑态更新(logic-updates)
> 术语:本篇所用货币战争域术语的统一定义见 [../../terminology.md](../../terminology.md)。

> 定位:**每个注册表动作 op 一篇**专篇,说明该动作的**逻辑态**应如何计算——逻辑态 = 动作发生后按游戏规则推算出来的游戏状态(例:买一张牌后金币 −40、备战席 +1;若下一帧实际观察与推算不符,以实际观察为准)。每篇覆盖:涉及的数据域、转移规则、确定面/随机面、拒绝语义、kernel 符号名引用(实现所在的代码符号)。总述两篇只承载机制:执行器机制 = [prep-executor-actions.md](prep-executor-actions.md),效果账机制 = [op-effects.md](op-effects.md);总则与原则在 [../action-logic-state.md](../action-logic-state.md)(本目录的纪律母篇)。

## 总则(必读)

1. **写入入口归属(硬规则)**:动作 op 只负责执行画面动作 + 机械执行后**直调自己的上报函数**(动作语义单一源 = `kernel/cw_action_report/` 上报函数族,每动作一文件一函数 `report_action_<snake>_param`;不对游戏状态做任何写入的动作集中在 `zero_writes.py`)。**逻辑态的更新写入由上报函数族独占**(函数内 `gs.write_logic`,kernel → 状态容器(GameState)(GameState,游戏状态对象,下同)单向依赖);dict 确认族的到账 = `kernel/cw_exec_state.py::apply_confirm_effect`。op 层/策略层禁自带逻辑态记账函数或并行登记路径,禁新增按类型聚合的转移函数(现无任何聚合分派点;上报函数调用方 = 动作 op 直调与商店序列驱动器直调)。
2. **两态制(+逻辑随机态扩展)**:状态容器每字段只有两种值来源——观察态(`observe()` 写,来自画面识别)与逻辑态(动作后推算,`write_logic()` 写);同一帧两者冲突时**以实际观察为准**(本目录「帧」= 一帧截图,即某一时刻的画面快照)。效果本身随机的推算口径走**逻辑随机态**(`write_logic_rand()` 写,来源 `logic_rand`;随机效果按采样结果推算直写,无法采样的留给观察;观察覆盖差异属预期,策略器消费前必须重新观察),见 [../action-logic-state.md](../action-logic-state.md) §1.2 与 [../fields.md](../fields.md) §2.1/§2.5。席位主域的「未观察」态由锚定标志 `tracked_account_observed` 承载(未经观察确认,值不可消费;与「已观察下的空」类型可分)。**对账**(观察读数与推算值的比对,不一致以实际观察为准)唯一发生点 = 画面 op 上报观察数据进 game state 的观察边界,由 game state 执行(../../screens/op-layer.md §1.3)。
3. **确定面/随机面**:逻辑态只写确定面(结果可准确计算的部分);随机面两档落法——推算不出可靠值的域**跳写**(留空不写、等下一帧观察覆盖),有确定口径/期望口径的按逻辑随机态直写(`write_logic_rand`),见 [../action-logic-state.md](../action-logic-state.md) §1.2。
4. **拒绝语义**:游戏拒买/拒上/期望失配 → 上报函数返回 `LogicOutcome(applied=False, reason)`,零字段写操作(不改动游戏状态)。
5. **先例**:商店期默认策略动作面 = 买牌/刷新/关店;卖备战与买经验收缩至备战期(先例见 [screens/README](../../screens/README.md) §5 与 strategy-docs/23_shop_screen.md)。**席满/腾位形态(2026-09-15 用户裁定修正)**:不是「关店→备战卖→重开」一条自动链——关店时**返回主循环(重新识别画面)**,由备战 op 在自己的决策周期自行判断与卖出;商店期为何关店、备战要做什么、何时重开,由**策略实现自行记录状态**(框架侧提供跨段状态载体与路由保证:节点内关店/重开牌面持久;策略侧多画面联动的重设计归后续迭代)。

## 逐动作专篇索引(注册表行 ↔ 专篇)

**计数口径(以代码现值为准)**:行数/类数/尚无专篇的行数,一律以**读文档时点 `operations/cw_op/cw_action_registry.py` 代码现值**清点为准,本节不固化计数;注册表已演进 = 以当时代码现值重新清点。当前快照括注 = 34 行 / 27 op 类 / 已有专篇 27 行(20 个专篇文件,工具 7 行共 [tools.md](tools.md) 一篇;买经验单类型单行)/ 尚无专篇 8 行(7 个 pick 行 + Obs 行:语义的在用记载 = [flow/action_ops.md](../../flow/action_ops.md) §4.5/§4.4 行 + 上报函数 docstring;超出本表登记面的补篇不批)。基准 = `cw_action_registry.py` 与 [flow/action_ops.md](../../flow/action_ops.md) §4;写域登记面 = 各上报函数族域覆盖(商店族全集见 [../action-logic-state.md](../action-logic-state.md) §2 头注,原 `SHOP_PROJECTION_DOMAINS` 登记常量已随死代码清偿移除)与各上报函数 docstring(备战族;原 `PREP_PROJECTION_DOMAINS` 登记面已随聚合写入入口停用)。映射粒度 = 注册行 → 专篇**文件**(一行对应一个专篇文件,不落小节);工具原子 7 行是先例例外,七行同指一个 op 类(`CwActionToolUseOp`),共一篇 [tools.md](tools.md)、内分逐类小节。

### 商店族(3 行)

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| BuyCard | `CwActionBuyCardOp` | [buy-card.md](buy-card.md) | `report_action_buy_card_param`(同步写入快照数据与合成升星,集中在这一个函数) |
| RefreshShop | `CwActionRefreshShopOp` | [refresh-shop.md](refresh-shop.md) | `report_action_refresh_shop_param`(刷新三个计数经效果账本 `record_refresh` 单一入口触发) |
| CloseShop | `CwActionCloseShopOp` | [close-shop.md](close-shop.md) | `report_action_close_shop_param`(`leave_screen`) |

### 备战族(10 行 + 工具原子 7 行)

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| SellBench | `CwActionSellBenchOp` | [sell-bench.md](sell-bench.md) | `report_action_sell_bench_param`(商店/备战两个域的历史两份写入统一为一份代码) |
| LevelUp | `CwActionLevelUpOp` | [level-up.md](level-up.md) | `report_action_level_up_param` |
| DeployMove | `CwActionDeployMoveOp` | [deploy-move.md](deploy-move.md) | `report_action_deploy_move_param` + board 派生挂钩 |
| SellDeployed | `CwActionSellDeployedOp` | [sell-deployed.md](sell-deployed.md) | `report_action_sell_deployed_param`(商店/备战两个域的历史两份写入统一为一份代码) |
| WearEquip | `CwActionWearEquipOp` | [wear-equip.md](wear-equip.md) | `report_action_wear_equip_param`(库存 equips 写 owned−1 + 目标角色 equips +1,集中在同一函数) |
| CollectOre | `CwActionCollectOreOp` | [collect-ore.md](collect-ore.md) | `report_action_collect_ore_param`(从游戏状态精确移除晶矿 + 晶矿金窗口登记,集中在同一函数) |
| OpenBox | `CwActionOpenBoxOp` | [open-box.md](open-box.md) | 零写族 `zero_writes`(终结动作——发出即结束本次访问、返回主循环,数据由下一入口的观察覆盖) |
| OpenTome | `CwActionOpenTomeOp` | [open-tome.md](open-tome.md) | `report_action_open_tome_param` 腾位(释放备战席槽位:bench kind tome → empty) |
| OpenBookcard | `CwActionOpenBookcardOp` | [open-bookcard.md](open-bookcard.md) | `report_action_open_bookcard_param` 腾位(释放备战席槽位:bench kind bookcard → empty;终结动作,动作发出点 = 策略器卡片分支) |
| FurnaceUse | `CwActionToolUseOp` | [tools.md](tools.md) | 状态容器直写(权威版本 = `tool_use.py` 七函数) |
| PrivilegeCardUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| WrenchUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| PrecisionWrenchUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| StaffProjectorUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| PerfectProjectorUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| LuckyTokenUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |

### 转场族(2 行)

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| StartBattle | `CwActionStartBattleOp` | [start-battle.md](start-battle.md) | `report_action_start_battle_param`(状态容器零写,结算屏观察覆盖接管;免战牌跳过次数递减集中在同一函数) |
| OpenShop | `CwActionOpenShopOp` | [open-shop.md](open-shop.md) | 零写族 `zero_writes`(承载 `terminal=True` 终结标志的注册行,流程层 `_open_shop_phase` 消费) |

### 观察族(1 行)

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| Obs | `CwActionObsOp` | ——(尚无专篇) | 零写占位 `report_action_obs_param`(状态容器更新通道 = 观察数据的聚合入口本体;契约权威版本 = [flow/action_ops.md](../../flow/action_ops.md) §4.4) |

### 事件线 pick 族(12 行,按在用两档分型)

分型依据 = `cw_action_registry.py` pick 族注册行现值 + `kernel/cw_action_report/` 各上报模块头 + `cw_overlay_pick_env.py` 族契约模块头与各 `cw_pick_<snake>_action.py` op docstring;分型成员以读文档时点代码现值为准(动作 op 重组落地前后盘面不同,禁沿用快照档成员)。在用形态**已无分步两相行**(全族即时上报;`flow/action_ops.md` §4.5 现文已申报「两相与证据标志形态已全域修复」)。

**即时单相(5 行)**:

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| PickEncounter | `CwActionPickEncounterOp` | [pick-encounter.md](pick-encounter.md) | `report_action_pick_encounter_param`(具名模块 `kernel/cw_action_report/pick_encounter.py`,发出动作时立即写入 chosen_encounter;兑现后清单只消费一次) |
| PickSupply | `CwActionPickSupplyOp` | [pick-supply.md](pick-supply.md) | `report_action_pick_supply_param`(即时单相一口写:owned 追加 0..n 件规范名装备(选中列首件 + 附加件按画面 y 序)+ 角色入席分支 `grant_bench_unit_cascade` + 装备后果链逐件 `apply_equip_acquire_consequence`;整列读不到装备名 = 装备域留空不写、不算缺陷,内容未知/名字未解析 = 值保持不变、来源标记翻转并保留证据;选择落地 = `chosen_supply` 由画面 op 确认时写入 (角色, 装备名列表) 2 元组) |
| PickInvestStrategy | `CwActionPickInvestOp` | [pick-invest.md](pick-invest.md)（专篇已补） | `report_action_pick_invest_strategy_param`(发出动作时立即写入,整支走获得链 `gain_invest_strategy`) |
| PickInvestEnv | `CwActionPickInvestOp` | 同上（两行同指一 op,专篇同为 pick-invest.md） | `report_action_pick_invest_env_param`(发出动作时立即写入,整支走获得链 `gain_invest_env`) |
| PickPlanner | `CwActionPickPlannerOp` | [pick-planner.md](pick-planner.md) | `report_action_pick_planner_param`(即时单相:先授予条件单位(rider,欢愉契约),随后装备/升费效果一口写,具名模块 `pick_planner.py`,模块头申报即时单相) |

**零写族(7 行)**:

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| PickMegastar | `CwActionPickMegastarOp` | [pick-megastar.md](pick-megastar.md) | 零写族 `zero_writes`(选择落地 = chosen_megastar 由画面 op 负责写入) |
| PickPartner | `CwActionPickPartnerOp` | [pick-partner.md](pick-partner.md) | 零写族 `zero_writes`(选择落地 = chosen_partner 由画面 op 负责写入) |
| PickFortune | `CwActionPickFortuneOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |
| PickWishTrial | `CwActionPickWishTrialOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |
| PickStarTome | `CwActionPickStarTomeOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |
| PickBoxCard | `CwActionPickBoxCardOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |
| PickExpertInvite | `CwActionPickExpertInviteOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |

(原 PickEquip 行因选择装备屏的误判已整体停用删除——动作类型清单/注册行/上报函数全套删除,已证伪标记 = `flow/action_ops.md` §4.5 末行,不入本表。)

### 动作类型清单已登记、不经注册表分发(层级区别:非注册行)

以下动作类型在 `CW_ACTION_TYPES` 白名单但**无注册行**,与组合壳/画面 op 同属「动作域之外」层级(全集口径见 [flow/action_ops.md](../../flow/action_ops.md) §4.5/§4.6):

- **3 个刷新动作**(RefreshNodeOptions/RefreshSupply/RefreshInvestCards)走各画面既有点击链;(HoldFrame 曾已登记 = 等待帧非动作,2026-09-20 用户裁定随重观察动作的并入而删除——`CwActionObsParam` scope='outer_loop' 同为分支拦截型,但其动作类型有注册行(in_place 路径派发用),不属本节「无注册行」的豁免范围);
- **商店域旧 op 文件**(`cw_sell_bench_action` / `cw_level_up_action`):**已随动作 op 重组停用删除**(动作类型清单摊平后单一注册行指备战 op,`cw_action_registry.py` 模块头「同名动作双域行更替申报」注销登记),逻辑态语义由上报函数保留、并入 [sell-bench.md](sell-bench.md) / [level-up.md](level-up.md) 双域记载。

**非动作清单类注(SwapDeploy)**:`CwActionSwapDeployParam` = union 已登记 / `CW_ACTION_TYPES` 白名单外 / 无注册行 / 上报与 sim 消费在用,宿主 = [prep-executor-actions.md](prep-executor-actions.md) §3。
