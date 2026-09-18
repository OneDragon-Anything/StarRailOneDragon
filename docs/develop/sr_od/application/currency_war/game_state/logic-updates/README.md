# 逻辑态更新(logic-updates)

> 定位:**每个动作 op 一篇**,说明该动作的逻辑态应如何计算——域集、转移规则、确定面/随机面、拒绝语义、kernel 符号锚。总-分结构的「分」;总则与原则在 [../action-logic-state.md](../action-logic-state.md)(本目录的纪律母篇)。

## 总则(必读)

1. **写口归属(硬规则)**:动作 op 只负责执行画面动作 + 向 game state 上报动作事实;**逻辑态的更新写入由 game state 独占**——商店域 `kernel/cw_game_state.py::apply_shop_action_logic`(+合成升星腿 `apply_shop_merge_leg`),备战域 `apply_prep_action_logic`,效果账 `kernel/cw_exec_state.py::apply_op_effect`。op 层/策略层禁自带逻辑态记账函数或并行登记路径。
2. **两态制**:容器(`GameState`)每字段只有两种值来源——观察态(`observe()` 写)与逻辑态(动作后推算,`write_logic()` 写);同帧冲突观察赢。tracked 账字段在观察态/逻辑态基础上另有**「未观察」态值**(无观察锚定,值不可消费;与「已观察下的空」类型可分)。对账 = 观察态 vs 逻辑态比对,**唯一发生点 = 画面 op 上报观察数据进 game state 的观察边界,由 game state 执行**(../../screens/op-layer.md §1.3)。
3. **确定面/随机面**:逻辑态只写确定面;随机面(刷新新牌面/变异/掉落)归下一帧观察。
4. **拒绝语义**:游戏拒买/拒上/期望失配 → 转移函数返回 `LogicOutcome(applied=False, reason)`,零容器写。
5. **判例**:商店期默认策略动作面 = 买牌/刷新/关店;卖备战与买经验收缩至备战期(判例见 [screens/README](../../screens/README.md) §5 与 strategy-docs/23_shop_screen.md)。**席满/腾位形态(2026-09-15 用户裁定修正)**:不是「关店→备战卖→重开」一条自动链——关店时**交还外循环**,由备战 op 在自己的决策周期自行判断与卖出;商店期为何关店、备战要做什么、何时重开,由**策略实现自行记录状态**(框架侧提供跨段状态载体与路由保证:节点内关店/重开牌面持久;策略侧多画面联动的重设计另批)。

## 逐动作文档索引(全集映射)

基准 = `operations/cw_op/cw_action_registry.py`(26 注册行 / 20 op 类)与 [flow/action_ops.md](../../flow/action_ops.md) §4;域集封闭申报面 = `SHOP_PROJECTION_DOMAINS` / `PREP_PROJECTION_DOMAINS`。

### 商店族(3 行)

| 动作 op | 文档 | 转移函数腿 |
|---|---|---|
| 买牌(BuyCard) | [buy-card.md](buy-card.md) | `apply_shop_action_logic` BuyCard 腿 + `apply_shop_merge_leg` 合成升星腿 |
| 刷新(RefreshShop) | [refresh-shop.md](refresh-shop.md) | `apply_shop_action_logic` RefreshShop 腿 + `record_refresh_execution` 计数组 |
| 关店(CloseShop) | [close-shop.md](close-shop.md) | `apply_shop_action_logic` CloseShop 腿(`leave_screen`) |

### 备战族(9 行 + 工具原子 7 行)

| 动作 op | 文档 | 转移函数腿 |
|---|---|---|
| 卖备战(SellBench) | [sell-bench.md](sell-bench.md) | `apply_shop_action_logic` SellBench 腿(商店域)/`apply_prep_action_logic`(备战域) |
| 买经验(LevelUp;LevelUpShop is-a 兜底同行) | [level-up.md](level-up.md) | `apply_shop_action_logic` LevelUpShop 腿 + `apply_prep_action_logic` LevelUp 分支 |
| 部署(DeployMove) | [prep-executor-actions.md](prep-executor-actions.md) §2 | `apply_prep_action_logic` DeployMove 腿 + board 派生挂钩 |
| 卖上阵(SellDeployed) | [sell-deployed.md](sell-deployed.md) | `apply_shop_action_logic` SellDeployed 腿(v2 动作族;生产策略面归备战域) |
| 穿装备(WearEquip) | [prep-executor-actions.md](prep-executor-actions.md) §4 | `apply_op_effect` WearEquip 分支(容器 equips 零写,视觉域 + tracked) |
| 点球(ClickSpheres) | [click-spheres.md](click-spheres.md) | `apply_op_effect` ClickSpheres 分支(球金窗登记;容器零写) |
| 开补给箱(OpenBox) | [open-box.md](open-box.md) | 容器零写(终结动作,交回外循环) |
| 开秘密典籍(OpenTome) | [open-tome.md](open-tome.md) | 容器零写(视觉域 tomes 摘件) |
| 书册(OpenBookcard) | [open-bookcard.md](open-bookcard.md) | 容器零写(视觉域腾席 +1) |
| 工具原子七类(FurnaceUse/PrivilegeCardUse/WrenchUse/PrecisionWrenchUse/StaffProjectorUse/PerfectProjectorUse/LuckyTokenUse,同指 ToolUseOp) | [op-effects.md](op-effects.md) §5 | 视觉域帧面(`_project_tool_obs` 按 `EQUIP_WRITE_SIDES`)+ `apply_tool_execution_write` |

### 转场族(2 行)

| 动作 op | 文档 | 转移函数腿 |
|---|---|---|
| 开战(StartBattle) | [start-battle.md](start-battle.md) | 容器零写(结算屏观察覆盖接管;免战跳过递减挂 `apply_op_effect`) |
| 开店(OpenShop) | [start-battle.md](start-battle.md) §10 | 容器零写(terminal 承载行,流程层 `_open_shop_phase` 消费) |

### 事件线 pick 族(5 行)

| 动作 op | 文档 | 转移函数腿 |
|---|---|---|
| PickEncounter / PickSupply / PickMegastar / PickPartner / PickPlanner(EncounterPickOp/SupplyPickOp/MegastarPickOp/PartnerPickOp/PlannerPickOp) | [op-effects.md](op-effects.md) §7 | 容器零写(确认到账 grant 挂 `apply_op_effect` dict 分支;选择落地 = chosen_* 观察写端) |

### 词表在册、不经注册表分发(指针)

SwapDeploy(容器腿在 `apply_shop_action_logic`,生产执行器未接线)见 [prep-executor-actions.md](prep-executor-actions.md) §5;7 个 pick 子类(PickInvest/PickStarTome/PickWishTrial/PickBoxCard/PickFortune/PickExpertInvite/PickEquip)由各画面 handler 自管消费链、RefreshNodeOptions/RefreshSupply/RefreshInvestCards 走各画面既有点击链、HoldFrame = 等待帧非动作——全集口径见 [flow/action_ops.md](../../flow/action_ops.md) §4.5。
