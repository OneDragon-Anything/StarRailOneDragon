# 逻辑态更新(logic-updates)

> 定位:**每个注册表动作 op 一篇**专篇,说明该动作的逻辑态应如何计算——域集、转移规则、确定面/随机面、拒绝语义、kernel 符号锚。总述两篇只承载机制:执行器机制 = [prep-executor-actions.md](prep-executor-actions.md),效果账机制 = [op-effects.md](op-effects.md);总则与原则在 [../action-logic-state.md](../action-logic-state.md)(本目录的纪律母篇)。

## 总则(必读)

1. **写口归属(硬规则)**:动作 op 只负责执行画面动作 + 机械执行后**直调自己的上报函数**(动作语义单一源 = `kernel/cw_action_report/` 上报函数族,每动作一文件一函数 `report_action_<snake>_param`,零写动作族集中在 `zero_writes.py`);**逻辑态的更新写入由上报函数族独占**(函数内 `gs.write_logic`,kernel → 容器单向依赖),dict 确认族到账 = `kernel/cw_exec_state.py::apply_confirm_effect`。op 层/策略层禁自带逻辑态记账函数或并行登记路径,禁新增按类型聚合的转移函数(分派只允许出现在引擎入口)。
2. **两态制(+逻辑随机态扩展)**:容器(`GameState`)每字段只有两种值来源——观察态(`observe()` 写)与逻辑态(动作后推算,`write_logic()` 写);同帧冲突观察赢。效果本身随机的推算口径走**逻辑随机态**(`write_logic_rand()` 写,来源 `logic_rand`;观察覆盖差异预期内,策略器消费前必须重观察),见 [../action-logic-state.md](../action-logic-state.md) §1.2 与 [../fields.md](../fields.md) §2.1/§2.5。tracked 账字段在观察态/逻辑态基础上另有**「未观察」态值**(无观察锚定,值不可消费;与「已观察下的空」类型可分)。对账 = 观察态 vs 逻辑态比对,**唯一发生点 = 画面 op 上报观察数据进 game state 的观察边界,由 game state 执行**(../../screens/op-layer.md §1.3)。
3. **确定面/随机面**:逻辑态只写确定面;随机面两档落法——无可写口径归下一帧观察(域级跳写),有确定面/期望口径按逻辑随机态直写(`write_logic_rand`),见 [../action-logic-state.md](../action-logic-state.md) §1.2。
4. **拒绝语义**:游戏拒买/拒上/期望失配 → 上报函数返回 `LogicOutcome(applied=False, reason)`,零容器写。
5. **判例**:商店期默认策略动作面 = 买牌/刷新/关店;卖备战与买经验收缩至备战期(判例见 [screens/README](../../screens/README.md) §5 与 strategy-docs/23_shop_screen.md)。**席满/腾位形态(2026-09-15 用户裁定修正)**:不是「关店→备战卖→重开」一条自动链——关店时**交还外循环**,由备战 op 在自己的决策周期自行判断与卖出;商店期为何关店、备战要做什么、何时重开,由**策略实现自行记录状态**(框架侧提供跨段状态载体与路由保证:节点内关店/重开牌面持久;策略侧多画面联动的重设计另批)。

## 逐动作专篇索引(注册表行 ↔ 专篇)

**计数口径(以代码现值为准)**:行数/类数/专篇缺档数一律以**落码时点 `operations/cw_op/cw_action_registry.py` 现值**清点为准,本节不固化计数;落码时注册表已演进 = 以当时代码现值重清。当前快照括注 = 35 行 / 27 op 类 / 专篇在档 27 行(20 个专篇文件,工具 7 行共 [tools.md](tools.md) 一篇、LevelUpShop 显式行并入 [level-up.md](level-up.md))/ 缺档 8 行(7 个 pick 行 + Obs 行:语义现役记载 = [flow/action_ops.md](../../flow/action_ops.md) §4.5/§4.4 行 + 上报函数 docstring,补篇外溢不批)。基准 = `cw_action_registry.py` 与 [flow/action_ops.md](../../flow/action_ops.md) §4;写域登记面 = `SHOP_PROJECTION_DOMAINS`(商店族)与各上报函数 docstring(备战族;原 `PREP_PROJECTION_DOMAINS` 登记面随聚合写口退役)。映射粒度 = 注册行 → 专篇**文件**(一行一文件,零内节落点);工具原子 7 行同指一个 op 类(`CwActionToolUseOp`,族文件先例)= 一篇 [tools.md](tools.md) 内逐类小节。

### 商店族(3 行)

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| BuyCard | `CwActionBuyCardOp` | [buy-card.md](buy-card.md) | `report_action_buy_card_param`(快照与合成升星腿内聚单点) |
| RefreshShop | `CwActionRefreshShopOp` | [refresh-shop.md](refresh-shop.md) | `report_action_refresh_shop_param`(刷新三计数经效果账本 `record_refresh` 单口触发) |
| CloseShop | `CwActionCloseShopOp` | [close-shop.md](close-shop.md) | `report_action_close_shop_param`(`leave_screen`) |

### 备战族(10 行 + 工具原子 7 行)

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| SellBench | `CwActionSellBenchOp` | [sell-bench.md](sell-bench.md) | `report_action_sell_bench_param`(双域统一单点) |
| LevelUp(LevelUpShop 同字段双类型,显式独立行同 op) | `CwActionLevelUpOp` | [level-up.md](level-up.md) | `report_action_level_up_param`(LevelUpShop 经 `report_action_level_up_shop_param` 一行委托) |
| DeployMove | `CwActionDeployMoveOp` | [deploy-move.md](deploy-move.md) | `report_action_deploy_move_param` + board 派生挂钩 |
| SellDeployed | `CwActionSellDeployedOp` | [sell-deployed.md](sell-deployed.md) | `report_action_sell_deployed_param`(双域统一单点) |
| WearEquip | `CwActionWearEquipOp` | [wear-equip.md](wear-equip.md) | `report_action_wear_equip_param`(容器 equips 写 owned−1 + tracked 账内聚) |
| CollectOre | `CwActionCollectOreOp` | [collect-ore.md](collect-ore.md) | `report_action_collect_ore_param`(容器精确摘晶矿 + 晶矿金窗登记内聚单点) |
| OpenBox | `CwActionOpenBoxOp` | [open-box.md](open-box.md) | 零写族 `zero_writes`(终结动作,交回外循环下一入口覆盖) |
| OpenTome | `CwActionOpenTomeOp` | [open-tome.md](open-tome.md) | `report_action_open_tome_param` 腾席(bench kind tome → empty) |
| OpenBookcard | `CwActionOpenBookcardOp` | [open-bookcard.md](open-bookcard.md) | `report_action_open_bookcard_param` 腾席(bench kind bookcard → empty;终结动作,发射位 = 策略器卡片臂) |
| FurnaceUse | `CwActionToolUseOp` | [tools.md](tools.md) | 容器直写(正本 = `tool_use.py` 七函数) |
| PrivilegeCardUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| WrenchUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| PrecisionWrenchUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| StaffProjectorUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| PerfectProjectorUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |
| LuckyTokenUse | `CwActionToolUseOp` | [tools.md](tools.md) | 同上 |

### 转场族(2 行)

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| StartBattle | `CwActionStartBattleOp` | [start-battle.md](start-battle.md) | `report_action_start_battle_param`(容器零写,结算屏观察覆盖接管;免战跳过递减内聚) |
| OpenShop | `CwActionOpenShopOp` | [open-shop.md](open-shop.md) | 零写族 `zero_writes`(terminal 承载行,流程层 `_open_shop_phase` 消费) |

### 观察族(1 行)

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| Obs | `CwActionObsOp` | ——(专篇缺档) | 零写占位 `report_action_obs_param`(容器更新通道 = 观察漏斗本体;契约正本 = [flow/action_ops.md](../../flow/action_ops.md) §4.4) |

### 事件线 pick 族(12 行,按现役两档分型)

分型依据 = `cw_action_registry.py` pick 族注册行现值 + `kernel/cw_action_report/` 各上报模块头 + `cw_overlay_pick_action.py` op docstring;分型成员判值以落码时点代码现值为准(迁移批落地前后盘面不同,禁沿用快照档成员)。现役**无分步两相行**(`flow/action_ops.md` §4.5 现文已申报「全族即时上报……两相与证据闩形态已全域清偿」)。

**即时单相(5 行)**:

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| PickEncounter | `CwActionPickEncounterOp` | [pick-encounter.md](pick-encounter.md) | `report_action_pick_encounter_param`(具名模块 `kernel/cw_action_report/pick_encounter.py`,发射即写 chosen_encounter;兑现后清单次消费) |
| PickSupply | `CwActionPickSupplyOp` | [pick-supply.md](pick-supply.md) | `report_action_pick_supply_param`(即时单相一口写:owned 规范名 + 单位腿 `grant_bench_unit_cascade` + 装备后果腿 `apply_equip_acquire_consequence`;内容未知/名未解析 = 翻来源留证;选择落地 = `chosen_supply` 画面 op 确认即写) |
| PickInvestStrategy | `CwActionPickInvestOp` | ——(专篇缺档;补篇决策 = 新增 pick-invest.md 专篇,接缝归口 = T-37 汇总登记) | `report_action_pick_invest_strategy_param`(发射即写,整支走获得链 `gain_invest_strategy`) |
| PickInvestEnv | `CwActionPickInvestOp` | ——(同上,两行同指一 op) | `report_action_pick_invest_env_param`(发射即写,整支走获得链 `gain_invest_env`) |
| PickPlanner | `CwActionPickPlannerOp` | [pick-planner.md](pick-planner.md) | `report_action_pick_planner_param`(即时单相:条件腿 rider 先行 → equip/upgrade 腿一口写,具名模块 `pick_planner.py`,模块头申报即时单相) |

**零写族(7 行)**:

| 注册行 | op 类 | 专篇 | 上报函数(动作语义单一源) |
|---|---|---|---|
| PickMegastar | `CwActionPickMegastarOp` | [pick-megastar.md](pick-megastar.md) | 零写族 `zero_writes`(选择落地 = chosen_megastar 画面 op 写端) |
| PickPartner | `CwActionPickPartnerOp` | [pick-partner.md](pick-partner.md) | 零写族 `zero_writes`(选择落地 = chosen_partner 画面 op 写端) |
| PickFortune | `CwActionPickFortuneOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |
| PickWishTrial | `CwActionPickWishTrialOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |
| PickStarTome | `CwActionPickStarTomeOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |
| PickBoxCard | `CwActionPickBoxCardOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |
| PickExpertInvite | `CwActionPickExpertInviteOp` | ——(专篇缺档) | 零写族 `zero_writes`(选择落地归观察) |

(原 PickEquip 行已随选择装备屏误判退役整体删除——词表/注册行/上报函数全套删除,墓碑 = `flow/action_ops.md` §4.5 末行,不入本表。)

### 词表在册、不经注册表分发(层级区别:非注册行)

以下词表类在 `CW_ACTION_TYPES` 白名单但**无注册行**,与组合壳/画面 op 同属「动作域之外」层级(全集口径见 [flow/action_ops.md](../../flow/action_ops.md) §4.5/§4.6):

- **3 个刷新动作**(RefreshNodeOptions/RefreshSupply/RefreshInvestCards)走各画面既有点击链;(HoldFrame 曾在册 = 等待帧非动作,2026-09-20 用户裁定随重观察动作收编删除——`CwActionObsParam` scope='outer_loop' 同为分支拦截型,但其词表类有注册行(in_place 路径派发用),不属本节无行豁免面);
- **商店域旧 op 文件**(`cw_sell_bench_action` / `cw_level_up_action`):**已随动作 op 重组退役删除**(词表摊平后单一注册行指备战 op,`cw_action_registry.py` 模块头「同名动作双域行更替申报」注销登记),逻辑态语义由上报函数保留、并入 [sell-bench.md](sell-bench.md) / [level-up.md](level-up.md) 双域记载。

**非词表类注(SwapDeploy)**:`CwActionSwapDeployParam` = union 在册 / `CW_ACTION_TYPES` 白名单外 / 无注册行 / 上报与 sim 消费在役,宿主 = [prep-executor-actions.md](prep-executor-actions.md) §3。
