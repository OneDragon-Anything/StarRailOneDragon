# W971 · op 命名规范与迁移映射

> 状态:**FINAL**(用户定稿 2026-09-03);实施批按本表执行,完成后本表转 as-built 索引。

## 1. 命名规则(用户定稿)

- **两类 op,文件名即分类**:
  - **画面 op** = 外循环按画面识别分发的 op → 文件 `cw_screen_<画面>.py`,类 `CwScreen<Pascal>`(类名 = 文件名驼峰,方便互查);
  - **动作 op** = 决策输出动作的执行器(无专属分发画面)→ 文件 `cw_op_<动作>.py`,类 `CwOp<Pascal>`;
- **目录跟随前缀**:`operations/cw_screen/`、`operations/cw_op/`;旧目录 `cw_flow/`、`handlers/`、`prep/` 清空后删除;
- `git mv` 保历史;每处改名 grep 全部引用(import/类名直调/字符串引用/测试源码锁/docs)后迁移;
- 退役 op(BuyShopCards/BattlePrepCycle)不参与命名,随批删除;
- OpeningSequence **拆解退役**(用户裁决:抽象不成立——四步各有画面,外循环按画面分发天然顺序流转,接管局由分发器自然续走;接管补采已挂 PrepDirector 观察段,不依赖壳)。

## 2. 画面 op 迁移映射(21)

| 新文件(cw_screen/) | 新类名 | 旧文件 | 旧类名 |
|---|---|---|---|
| cw_screen_prep.py | CwScreenPrep | prep_director.py | PrepDirector |
| cw_screen_battle_wait.py | CwScreenBattleWait | cw_flow/battle_wait_op.py | BattleWaitOp |
| cw_screen_briefing.py | CwScreenBriefing | cw_flow/briefing_op.py | BriefingOp |
| cw_screen_plane_transition.py | CwScreenPlaneTransition | cw_flow/plane_transition_op.py | PlaneTransitionOp |
| cw_screen_invest_env.py | CwScreenInvestEnv | handlers/handle_invest_env.py | HandleInvestEnv |
| cw_screen_wait_one_one.py | CwScreenWaitOneOne | cw_flow/wait_one_one_op.py | WaitOneOneOp |
| cw_screen_boss_briefing.py | CwScreenBossBriefing | cw_flow/boss_briefing_op.py | BossBriefingOp |
| cw_screen_encounter.py | CwScreenEncounter | handlers/handle_encounter.py | HandleEncounter |
| cw_screen_invest_strategy.py | CwScreenInvestStrategy | handlers/handle_invest_strategy.py | HandleInvestStrategy |
| cw_screen_partner.py | CwScreenPartner | handlers/handle_select_partner.py | HandleSelectPartner |
| cw_screen_planner.py | CwScreenPlanner | handlers/handle_planner_event.py | HandlePlannerEvent |
| cw_screen_fortune.py | CwScreenFortune | handlers/handle_fortune_picker.py | HandleFortunePicker |
| cw_screen_wish_trial.py | CwScreenWishTrial | handlers/handle_wish_trial.py | HandleWishTrial |
| cw_screen_supply.py | CwScreenSupply | handlers/handle_supply_box.py | HandleSupplyBox |
| cw_screen_armory_box.py | CwScreenArmoryBox | handlers/handle_armory_box_dialog.py | HandleArmoryBoxDialog |
| cw_screen_bookcard.py | CwScreenBookcard | cw_flow/overlay_ops.py(BookcardOp) | BookcardOp(星徽秘典) |
| cw_screen_expert_invite.py | CwScreenExpertInvite | handlers/handle_bookcard.py | HandleBookcard(专家邀请函,与秘典区分) |
| cw_screen_equip_pick.py | CwScreenEquipPick | handlers/handle_equip_pick.py | HandleEquipPick |
| cw_screen_deploy_not_full.py | CwScreenDeployNotFull | handlers/handle_deploy_not_full.py | HandleDeployNotFull |
| cw_screen_plane_intel.py | CwScreenPlaneIntel | handlers/collect_plane_intel.py | CollectPlaneIntel |
| (基类) | CwScreenOverlay | cw_flow/overlay_ops.py | CwOverlayOp |

六委托薄封装(Megastar/Partner/ArmoryBox/WishTrial/Planner/Fortune 的 CwOverlayOp 子类)随对应 CwScreen* 合并(委托壳→实现内联,或保留薄封装+实现改名,实施者按最小扰动定,报告说明)。

## 3. 动作 op 迁移映射(7)

| 新文件(cw_op/) | 新类名 | 旧文件 | 旧类名 |
|---|---|---|---|
| cw_op_open_shop.py | CwOpOpenShop | prep/open_shop.py | OpenShopOp |
| cw_op_close_shop.py | CwOpCloseShop | prep/close_shop.py | CloseShopOp |
| cw_op_buy_cards.py | CwOpBuyCards | prep/buy_cards.py | BuyCardsOp(含 BuyCardsOutcome dataclass) |
| cw_op_deploy.py | CwOpDeploy | prep/deploy_bench.py | DeployBench |
| cw_op_equip_all.py | CwOpEquipAll | prep/equip_all.py | EquipAll |
| cw_op_collect_spheres.py | CwOpCollectSpheres | handlers/handle_reward_sphere.py | CollectRewardSpheres |
| cw_op_sell_off_target.py | CwOpSellOffTarget | prep/clean_offtarget.py | CleanDeployedOffTarget |

## 4. 退役清单(删除,不迁移)

| 旧 | 理由 |
|---|---|
| prep/battle_prep.py(BattlePrepCycle) | 旧备战环,P3b 拆内环后无生产消费 |
| prep/shop.py(BuyShopCards) | 旧壳,P3b 解体(执行链已走三原子) |
| cw_flow/opening_sequence.py(OpeningSequence) | §1 拆解裁决:四步画面 op 由外循环自然流转 |
| cw_flow/overlay_ops.py 薄封装族 | 随 CwScreen* 合并(§2 注) |

**不参与命名(保留现名)**:battle_loop.py / CurrencyWarRunLoop(外循环)、entry/(StartCurrencyWarMatch/ExitCurrencyWarMatch/EnterCurrencyWar/TakeoverCollectPlaneIntel 整局与入口级)。

## 5. 实施注意

- 字符串引用面:决策输出 action 类型名、`_run_composite` 字符串 import、测试源码锁(grep 类名/文件名)——逐处核;
- 序锁矩阵(test_cw_dispatch_order_matrix)锚的分支判定行随迁移改锚,锁语义不变;
- 遥测/记录面(op_name 字符串进 runs/decisions 的)核对消费端(遥测判读 CLI/复盘脚本按 op_name 过滤的)——受影响则同步;
- 全量 CW + ruff + 离线完整局(sim 不受影响,但 import 波及需全绿)。
