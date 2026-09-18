# 逻辑态更新(logic-updates)

> 定位:**每个注册表动作 op 一篇**专篇,说明该动作的逻辑态应如何计算——域集、转移规则、确定面/随机面、拒绝语义、kernel 符号锚。总述两篇只承载机制:执行器机制 = [prep-executor-actions.md](prep-executor-actions.md),效果账机制 = [op-effects.md](op-effects.md);总则与原则在 [../action-logic-state.md](../action-logic-state.md)(本目录的纪律母篇)。

## 总则(必读)

1. **写口归属(硬规则)**:动作 op 只负责执行画面动作 + 向 game state 上报动作事实;**逻辑态的更新写入由 game state 独占**——商店域 `kernel/cw_game_state.py::apply_shop_action_logic`(+合成升星腿 `apply_shop_merge_leg`),备战域 `apply_prep_action_logic`,效果账 `kernel/cw_exec_state.py::apply_op_effect`。op 层/策略层禁自带逻辑态记账函数或并行登记路径。
2. **两态制**:容器(`GameState`)每字段只有两种值来源——观察态(`observe()` 写)与逻辑态(动作后推算,`write_logic()` 写);同帧冲突观察赢。tracked 账字段在观察态/逻辑态基础上另有**「未观察」态值**(无观察锚定,值不可消费;与「已观察下的空」类型可分)。对账 = 观察态 vs 逻辑态比对,**唯一发生点 = 画面 op 上报观察数据进 game state 的观察边界,由 game state 执行**(../../screens/op-layer.md §1.3)。
3. **确定面/随机面**:逻辑态只写确定面;随机面(刷新新牌面/变异/掉落)归下一帧观察。
4. **拒绝语义**:游戏拒买/拒上/期望失配 → 转移函数返回 `LogicOutcome(applied=False, reason)`,零容器写。
5. **判例**:商店期默认策略动作面 = 买牌/刷新/关店;卖备战与买经验收缩至备战期(判例见 [screens/README](../../screens/README.md) §5 与 strategy-docs/23_shop_screen.md)。**席满/腾位形态(2026-09-15 用户裁定修正)**:不是「关店→备战卖→重开」一条自动链——关店时**交还外循环**,由备战 op 在自己的决策周期自行判断与卖出;商店期为何关店、备战要做什么、何时重开,由**策略实现自行记录状态**(框架侧提供跨段状态载体与路由保证:节点内关店/重开牌面持久;策略侧多画面联动的重设计另批)。

## 逐动作专篇索引(注册表 26 行 ↔ 专篇 1:1)

基准 = `operations/cw_op/cw_action_registry.py`(26 注册行 / 20 op 类)与 [flow/action_ops.md](../../flow/action_ops.md) §4;域集封闭申报面 = `SHOP_PROJECTION_DOMAINS` / `PREP_PROJECTION_DOMAINS`。映射粒度 = 注册行 → 专篇**文件**(一行一文件,零内节落点);工具原子 7 行同指一个 op 类(`ToolUseOp`,族文件先例)= 一篇 [tools.md](tools.md) 内逐类小节。篇数对账:20 专篇 = 20 op 类。

### 商店族(3 行)

| 注册行 | op 类 | 专篇 | 转移函数腿 |
|---|---|---|---|
| BuyCard | `BuyCardOp` | [buy-card.md](buy-card.md) | `apply_shop_action_logic` BuyCard 腿 + `apply_shop_merge_leg` 合成升星腿 |
| RefreshShop | `RefreshShopOp` | [refresh-shop.md](refresh-shop.md) | `apply_shop_action_logic` RefreshShop 腿 + `record_refresh_execution` 计数组 |
| CloseShop | `CloseShopOp` | [close-shop.md](close-shop.md) | `apply_shop_action_logic` CloseShop 腿(`leave_screen`) |

### 备战族(9 行 + 工具原子 7 行)

| 注册行 | op 类 | 专篇 | 转移函数腿 |
|---|---|---|---|
| SellBench | `PrepSellBenchOp` | [sell-bench.md](sell-bench.md) | `apply_prep_action_logic` SellBench 腿(商店域 `apply_shop_action_logic` SellBench 腿同篇双域) |
| LevelUp(LevelUpShop is-a 兜底同行) | `PrepLevelUpOp` | [level-up.md](level-up.md) | `apply_prep_action_logic` LevelUp 分支 + 商店域 LevelUpShop 腿 |
| DeployMove | `DeployMoveOp` | [deploy-move.md](deploy-move.md) | `apply_prep_action_logic` DeployMove 腿 + board 派生挂钩 |
| SellDeployed | `SellDeployedOp` | [sell-deployed.md](sell-deployed.md) | `apply_prep_action_logic` SellDeployed 腿(商店域腿同篇双域) |
| WearEquip | `WearEquipOp` | [wear-equip.md](wear-equip.md) | `apply_op_effect` WearEquip 分支(合法零写集:容器 equips 零写 + tracked 账) |
| ClickSpheres | `ClickSpheresOp` | [click-spheres.md](click-spheres.md) | `apply_op_effect` ClickSpheres 分支(球金窗登记)+ `apply_prep_action_logic` 容器精确摘球 |
| OpenBox | `OpenBoxOp` | [open-box.md](open-box.md) | 合法零写集(终结动作,交回外循环下一入口覆盖) |
| OpenTome | `OpenTomeOp` | [open-tome.md](open-tome.md) | `apply_prep_action_logic` 腾席分支(bench kind tome → empty) |
| OpenBookcard | `OpenBookcardOp` | [open-bookcard.md](open-bookcard.md) | `apply_prep_action_logic` 腾席分支(bench kind supply_box → empty) |
| FurnaceUse | `ToolUseOp` | [tools.md](tools.md) | 合法零写集(容器零写)+ `apply_tool_execution_write` |
| PrivilegeCardUse | `ToolUseOp` | [tools.md](tools.md) | 同上 |
| WrenchUse | `ToolUseOp` | [tools.md](tools.md) | 同上 |
| PrecisionWrenchUse | `ToolUseOp` | [tools.md](tools.md) | 同上 |
| StaffProjectorUse | `ToolUseOp` | [tools.md](tools.md) | 同上 |
| PerfectProjectorUse | `ToolUseOp` | [tools.md](tools.md) | 同上 |
| LuckyTokenUse | `ToolUseOp` | [tools.md](tools.md) | 同上 |

### 转场族(2 行)

| 注册行 | op 类 | 专篇 | 转移函数腿 |
|---|---|---|---|
| StartBattle | `StartBattleOp` | [start-battle.md](start-battle.md) | 容器零写(结算屏观察覆盖接管;免战跳过递减挂 `apply_op_effect`) |
| OpenShop | `OpenShopOp` | [open-shop.md](open-shop.md) | 容器零写(terminal 承载行,流程层 `_open_shop_phase` 消费) |

### 事件线 pick 族(5 行)

| 注册行 | op 类 | 专篇 | 转移函数腿 |
|---|---|---|---|
| PickEncounter | `EncounterPickOp` | [pick-encounter.md](pick-encounter.md) | 容器零写(选择落地 = chosen_encounter 观察写端) |
| PickSupply | `SupplyPickOp` | [pick-supply.md](pick-supply.md) | 容器零写(唯一到账登记:ConfirmSupply → owned +1;选择落地 = chosen_supply 观察写端) |
| PickMegastar | `MegastarPickOp` | [pick-megastar.md](pick-megastar.md) | 容器零写(选择落地 = chosen_megastar 观察写端) |
| PickPartner | `PartnerPickOp` | [pick-partner.md](pick-partner.md) | 容器零写(选择落地 = chosen_partner 观察写端) |
| PickPlanner | `PlannerPickOp` | [pick-planner.md](pick-planner.md) | 容器零写(落地域 chosen_hack 现役无写入端) |

### 词表在册、不经注册表分发(层级区别:非注册行)

以下词表类在 `CW_ACTION_TYPES` 白名单但**无注册行**,与组合壳/画面 op 同属「动作域之外」层级(全集口径见 [flow/action_ops.md](../../flow/action_ops.md) §4.5/§4.6):

- **SwapDeploy**(容器腿在 `apply_shop_action_logic`,生产执行器未接线)→ [prep-executor-actions.md](prep-executor-actions.md) §3(非注册行注);
- **7 个 handler 自管 pick 子类**(PickInvest/PickStarTome/PickWishTrial/PickBoxCard/PickFortune/PickExpertInvite/PickEquip)由各画面 handler 自管消费链,不经注册表;
- **3 个刷新动作**(RefreshNodeOptions/RefreshSupply/RefreshInvestCards)走各画面既有点击链;**HoldFrame** = 等待帧非动作;
- **商店域旧 op 文件**(`cw_sell_bench_action.SellBenchOp`/`cw_level_up_action.LevelUpOp`):能力面保留、生产不可达(注册行已更替为备战 op,`cw_action_registry.py` 模块头「同名动作双域行更替申报」),逻辑态语义并入 [sell-bench.md](sell-bench.md) / [level-up.md](level-up.md) 双域记载。
