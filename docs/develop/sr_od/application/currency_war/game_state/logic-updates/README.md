# 逻辑态更新（logic-updates）

> 定位：**每个动作 op 一篇**,说明该动作的逻辑态应如何计算——域集、转移规则、确定面/随机面、拒绝语义、kernel 符号锚。总-分结构的「分」;总则与原则在 s../action-logic-state.md](../action-logic-state.md)（本目录的纪律母篇）。

## 总则(必读)

1. **写口归属(硬规则)**:动作 op 只负责执行画面动作 + 向 game state 上报动作事实;**逻辑态的更新写入由 game state 独占**——商店域 `kernel/cw_game_state.py::apply_shop_action_logic`(+合成升星腿 `apply_shop_merge_leg`),备战域 `apply_prep_action_logic`,效果账 `kernel/cw_exec_state.py::apply_op_effect`。op 层/策略层禁自带逻辑态记账函数或并行登记路径。
2. **两态制**:容器(`GameState`)每字段只有两种值来源——观察态(`observe()` 写)与逻辑态(动作后推算,`write_logic()` 写);同帧冲突观察赢。tracked 账字段在观察态/逻辑态基础上另有**「未观察」态值**(无观察锚定,值不可消费;与「已观察下的空」类型可分)。对账 = 观察态 vs 逻辑态比对,**唯一发生点 = 画面 op 上报观察数据进 game state 的观察边界,由 game state 执行**(../../screens/op-layer.md §1.3)。
3. **确定面/随机面**:逻辑态只写确定面;随机面(刷新新牌面/变异/掉落)归下一帧观察。
4. **拒绝语义**:游戏拒买/拒上/期望失配 → 转移函数返回 `LogicOutcome(applied=False, reason)`,零容器写。
5. **判例**:商店期默认策略动作面 = 买牌/刷新/关店;卖备战与买经验收缩至备战期(判例见 [screens/README](../../screens/README.md) §5 与 strategy-docs/23_shop_screen.md)。席满/腾位形态 = 关店时交还外循环,由备战 op 自行决策卖出;跨段衔接由策略实现自行记录状态(框架侧提供状态载体与「节点内关店/重开牌面持久」路由保证)。**席满/腾位形态(2026-09-15 用户裁定修正)**:不是「关店→备战卖→重开」一条自动链——关店时**交还外循环**,由备战 op 在自己的决策周期自行判断与卖出;商店期为何关店、备战要做什么、何时重开,由**策略实现自行记录状态**(框架侧提供跨段状态载体与路由保证:节点内关店/重开牌面持久;策略侧多画面联动的重设计另批)。

## 逐动作文档索引

| 动作 op | 文档 | 转移函数腿 |
|---|---|---|
| 买牌(BuyCard) | sbuy-card.md](buy-card.md) | `apply_shop_action_logic` BuyCard 腿 + `apply_shop_merge_leg` 合成升星腿 |
| 卖备战(SellBench) | ssell-bench.md](sell-bench.md) | `apply_shop_action_logic` SellBench 腿(商店域)/`apply_prep_action_logic`(备战域) |
| 卖上阵(SellDeployed) | ssell-deployed.md](sell-deployed.md) | `apply_shop_action_logic` SellDeployed 腿(v2 动作族;生产策略面归备战域) |
| 刷新(RefreshShop) | srefresh-shop.md](refresh-shop.md) | `apply_shop_action_logic` RefreshShop 腿 |
| 关店(CloseShop) | sclose-shop.md](close-shop.md) | `apply_shop_action_logic` CloseShop 腿 |
| 买经验(LevelUp) | slevel-up.md](level-up.md) | `apply_shop_action_logic` LevelUp 腿 |
| 书册(OpenBookcard) | sopen-bookcard.md](open-bookcard.md) | 执行器通用信封(批2c) |
| 开战(StartBattle) | sstart-battle.md](start-battle.md) | 备战终结,交回外循环 |
| 备战执行器动作族(部署/卖/移位/穿装) | sprep-executor-actions.md](prep-executor-actions.md) | `apply_prep_action_logic` + `PrepActionExecutor` 执行侧 |
| 效果账(选卡/工具/特权) | sop-effects.md](op-effects.md) | `apply_op_effect` + `cw_affix_effects` |
