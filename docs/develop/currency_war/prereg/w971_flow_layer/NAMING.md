# W971 · op 命名规范与迁移映射

> 状态:**已实施(as-built 索引)**——用户定稿 2026-09-03;命名迁移+退役删除批已全量落地(代码层全量 CW 3110 绿,含退役删除与 RunNode 历史抽象退役)。本表保留为旧名↔新名对照索引(旧名列是对照所需的当时事实,不再改动);as-built 正文见 `docs/develop/currency_war/strategy/`。

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

## 4. 退役清单(删除,不迁移)——**用户裁决 2026-09-03:本轮直接执行**(与命名迁移同批交付,commit 分段)

| 旧 | 理由 |
|---|---|
| prep/battle_prep.py(BattlePrepCycle) | 旧备战环,P3b 拆内环后无生产消费 |
| prep/shop.py(BuyShopCards) | 旧壳,P3b 解体(执行链已走三原子) |
| cw_flow/opening_sequence.py(OpeningSequence) | §1 拆解裁决:四步画面 op 由外循环自然流转 |
| cw_flow/overlay_ops.py 薄封装族 | 随 CwScreen* 合并(§2 注) |

## 4.1 入口/整局/外循环级迁移映射(用户裁决 2026-09-03 追加:也统一)

| 新文件 | 新类名 | 旧文件 | 旧类名 |
|---|---|---|---|
| cw_loop.py(operations/ 根) | CwLoop | battle_loop.py | CurrencyWarRunLoop |
| cw_entry_start.py | CwEntryStart | entry/start_currency_war_match.py | StartCurrencyWarMatch |
| cw_entry_exit.py | CwEntryExit | entry/exit_currency_war_match.py | ExitCurrencyWarMatch |
| cw_entry_enter.py | CwEntryEnter | entry/enter_currency_war.py | EnterCurrencyWar |
| cw_screen_plane_intel.py | CwScreenPlaneIntel(与 CollectPlaneIntel 合并,参数化入口;合并风险大则拆 cw_entry_plane_intel.py) | entry/takeover_collect_plane_intel.py | TakeoverCollectPlaneIntel |

注意:CwEntryStart 被 app 层(GUI/ApplicationFactory/一条龙链)消费——grep 波及面含 operations/ 之外,逐处迁移。

## 4.2 不参与命名(保留现名)

prep_director 交回原语等核心语义名若迁移后仍语义完整可保留(如 CwScreenPrep 已覆盖)。

## 5. 实施注意

- 字符串引用面:决策输出 action 类型名、`_run_composite` 字符串 import、测试源码锁(grep 类名/文件名)——逐处核;
- 序锁矩阵(test_cw_dispatch_order_matrix)锚的分支判定行随迁移改锚,锁语义不变;
- 遥测/记录面(op_name 字符串进 runs/decisions 的)核对消费端(遥测判读 CLI/复盘脚本按 op_name 过滤的)——受影响则同步;
- 全量 CW + ruff + 离线完整局(sim 不受影响,但 import 波及需全绿)。

## 6. 画面 op 完成验证模型选型判据(RunNode 退役批追加,用户裁决 2026-09-03:按新架构统一,历史产物清理)

两条路,按画面交互形态选,新浮层 op 落地按此选型并在**类头声明**所选模型:

- **直接实现(依赖外循环重识别兜底)**:单动作/短序列(≤2 步)的浮层——每步
  失败由外循环下一轮重识别自然重派(重识别即兜底),op 不自带验证循环。
  例:列车同行/祈愿/策划/命运等委托薄封装族(逐步内联中)。
- **op 内验证 + 节点预算**(committed-but-verifying):多步序列 / 每步可独立
  失败 / 历史卡死形态的节点——op 内每轮「验证完成(离开本画面锚)→ 做一个
  动作 → round_retry 计 `node_max_retry_times` 预算」,超限框架转 FAIL bail
  交外循环(不无限烧全局预算)。例:`CwScreenSupplyNode`(补给:采集
  detour 多步 + 选卡确认,历史盲单发卡死)、`CwScreenMegastar`(巨星:选候选
  → 确认 → 罕见 step2 安全网,一局多次触发)。

历史产物:RunNode 基类 + `run_nodes/` 包随本判据落档删除(两子类行为等价内联,
预算语义/ADR-0264 关态基线预置原样平移)。
