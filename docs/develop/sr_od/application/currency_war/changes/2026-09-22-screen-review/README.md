# 2026-09-22-screen-review(货币战争全画面规范符合性审查·只设计不落码)

> 任务账本 = `.debug/progress/2026-09-22-cw-screen-review/dag.jsonl`(36 个画面审查任务 T-1..T-36 + 汇总 T-37)。
> 审查产出 = 账本目录 `reports/`(每屏一份规范符合性审查报告);有问题屏的修法设计稿 = 本目录逐屏一文件;设计稿经无前提对抗循环(攻击收敛或触 4 轮上限)后**停在「待用户裁决」**——用户逐屏认同后才立落地批,未认同不派任何落码。

## 文档
- 设计稿:`<snake>.md`(仅审查有问题的屏才产生;`§0 状态` 字段标注 草案/对抗收敛待裁决/对抗未收敛待裁决)

## 进度
- 审查:0/36 完成(明细 = `dag.py --file .debug/progress/2026-09-22-cw-screen-review/dag.jsonl list`)
- 设计对抗:未开始
- 落地:未开始(等待用户逐屏认同)

## 边界(本次审查立什么、不立什么)
- 审查范围 = 每屏六面:**画面 op / 动作 op / 观察上报 / 动作上报 / game state 计算 / 文档**,对照正本:`screens/op-layer.md`、`screens/README.md`、`flow/action_ops.md`、`flow/action_exec.md`、`flow/README.md` §1(决策控制分层铁律)、`game_state/fields.md`、`game_state/logic-updates/`。
- 在册欠账(策划/装备两相上报、SwapDeploy 未接线、商店锁未建模等)不重复立项,只核对现状与在册描述一致;不一致才算新发现。
- 对抗循环上限 4 轮:不收敛即标注「对抗未收敛-待用户裁决」,不无限烧。
- 只设计不落码:所有修法(含文档修正)都停在设计稿;设计稿被用户认同前不改任何代码与正本文档。

## 逐屏状态
| 任务 | 屏 | 审查 | 设计稿 |
|---|---|---|---|
| T-1 | CwScreenPrep 备战 | 有问题(高0中9低8+死文件疑点2)·报告=reports/T-1-r1.md(合并) | **对抗触顶待裁决**(prep.md;r1 13条→r2 6条→r3 5条→r4触顶残留3条转T-37) |
| T-2 | CwScreenBuyCards 商店开画面 | 有问题(高2中3低2)·报告=账本reports/T-2-r1.md | **对抗触顶待裁决**(buy_cards.md;r1 9条→r2 6条→r3 1低→r4触顶残留1低转T-37) |
| T-3 | CwScreenBattleWait 战斗等待·结算 | 有问题(高0中3低3)·报告=账本reports/T-3-r1.md | **对抗触顶待裁决**(battle_wait.md;r1 4条→r2 3条→r3 3条→r4触顶残留3低转T-37) |
| T-4 | CwScreenEncounter 遭遇 | 有问题(高1中3低1)·报告=账本reports/T-4-r1.md | **对抗触顶待裁决**(encounter.md;r1 2条→r2 3条→r3 2低→r4触顶残留3低转T-37) |
| T-5 | CwScreenSupplyNode 补给 | 有问题(高0中3低4)·报告=账本reports/T-5-r1.md | **对抗收敛待裁决**(supply_node.md;r1未收敛7条→r2未收敛4条→r3收敛) |
| T-6 | CwScreenInvestStrategy 投资策略 | 有问题(高0中4低1)·报告=账本reports/T-6-r1.md | **对抗收敛待裁决**(invest_strategy.md;r1未收敛4条→r2收敛) |
| T-7 | CwScreenInvestEnv 投资环境 | 有问题(高0中3低3)·报告=账本reports/T-7-r1.md | **对抗收敛待裁决**(invest_env.md;r1 6条→r2 3条→r3 1低→r4收敛) |
| T-8 | CwScreenMegastar 盛会之星 | 有问题(高1中2低2)·报告=账本reports/T-8-r1.md | **对抗触顶待裁决**(megastar.md;r1→r2收敛;新规范扩项后 r3=高0中4低7、r4终轮=高0中1低7(未收敛触顶),两轮 19 条已全部随稿清偿,含转换门匹配域收窄设计腿,待裁决) |
| T-9 | CwScreenEquipPick 选择装备 | 有问题(高1中1低3)·报告=账本reports/T-9-r1.md | **对抗收敛待裁决**(equip_pick.md;r1 7条→r2 1低→r3收敛)+新规范增补待裁决 |
| T-10 | CwScreenYinLang 骇入策划/银狼升星 | 有问题(高0中2低3)·报告=账本reports/T-10-r1.md | **对抗收敛待裁决**(planner.md;r1 7条→r2 3条→r3 1低→r4收敛)+新规范增补待裁决 |
| T-11 | CwScreenPartner 选择伙伴 | 有问题(高1中2低3)·报告=账本reports/T-11-r1.md | **对抗收敛待裁决**(partner.md;r1 7条→r2 2条→r3 1低→r4收敛)+新规范增补待裁决 |
| T-12 | CwScreenFortune 命运卜者 | 有问题(高1中1低2)·报告=账本reports/T-12-r1.md | **对抗收敛待裁决**(fortune.md;r1 5条→r2收敛)+新规范增补待裁决 |
| T-13 | CwScreenWishTrial 祈愿试炼 | 有问题(高1低2)·报告=账本reports/T-13-r1.md | **对抗收敛待裁决**(wish_trial.md;r1 4条→r2 1低→r3收敛)+新规范增补待裁决 |
| T-14 | CwScreenBookcard 星徽秘典书册卡 | 有问题(高1中2低3)·报告=账本reports/T-14-r1.md | **对抗触顶待裁决**(bookcard.md;r1 3条→r2 3条→r3 1低→r4触顶残留1低转T-37)+新规范增补待裁决 |
| T-15 | CwScreenExpertInvite 专家邀请函 | 有问题(高1低1)·报告=账本reports/T-15-r1.md | **对抗收敛待裁决**(expert_invite.md;r1收敛附4条文字级备注)+新规范增补待裁决 |
| T-16 | CwScreenBoxPick 武装箱选卡 | 有问题(高0中1低5)·报告=账本reports/T-16-r1.md | **对抗收敛待裁决**(box_pick.md;r1 6低→r2 6低→r3 3低→r4收敛)+新规范增补待裁决 |
| T-17 | CwOpOpenShop 商店框·开店 | 有问题(高0中1低2)·报告=账本reports/T-17-r1.md | **对抗收敛待裁决**(op_open_shop.md;r1 5条→r2 3条→r3收敛) |
| T-18 | CwOpCloseShop 商店框·关店 | 有问题(高0中3低3)·报告=账本reports/T-18-r1.md | **对抗触顶待裁决**(op_close_shop.md;r4终轮=收敛0条实质,3条低残留随定稿/归T-37) |
| T-19 | CwScreenArmoryBox 简易武装箱 | 有问题(高0中1低2)·报告=账本reports/T-19-r1.md | **对抗收敛待裁决**(armory_box.md;r1收敛附2条文字级备注) |
| T-20 | CwScreenBriefing 简报 | 有问题(高0中1低5)·报告=账本reports/T-20-r1.md | **对抗触顶待裁决**(briefing.md;r1 4条→r2 1条→r3 1条→r4触顶残留1低转T-37)+新规范增补待裁决 |
| T-21 | CwScreenBossBriefing BOSS简报 | 有问题(高0中2低2)·报告=账本reports/T-21-r1.md | **对抗收敛待裁决**(boss_briefing.md;r1 3条低→r2收敛) |
| T-22 | CwScreenPlaneTransition 位面过渡 | 有问题(高0中1低2)·报告=账本reports/T-22-r1.md | **对抗收敛待裁决**(plane_transition.md;r1 3条低→r2收敛) |
| T-23 | CwScreenWaitOneOne 等待1-1 | 有问题(高0中0低1)·报告=账本reports/T-23-r1.md | **对抗收敛待裁决**(wait_one_one.md;r1收敛) |
| T-24 | CwScreenDeployNotFull 未达上限弹窗 | 有问题(高0中0低4)·报告=账本reports/T-24-r1.md | **对抗收敛待裁决**(deploy_not_full.md;r1收敛附4条文字级备注) |
| T-25 | CwScreenPlaneIntel 位面情报 | 有问题(高0中0低5)·报告=账本reports/T-25-r1.md | **对抗收敛待裁决**(plane_intel.md;r1 4条→r2 1低→r3定点收敛)+新规范增补待裁决 |
| T-26 | CwScreenNextButton 下一步按钮 | 有问题(高0中0低2)·报告=账本reports/T-26-r1.md | **对抗收敛待裁决**(next_button.md;r1 7条→r2收敛附2低) |
| T-27 | CwScreenPlaneDetail 位面详情 | 有问题(高0中0低3)·报告=账本reports/T-27-r1.md | **对抗收敛待裁决**(plane_detail.md;r1 2条中→r2收敛) |
| T-28 | CwScreenConsumableOverlay 消耗品浮层 | 有问题(高0中0低1)·报告=账本reports/T-28-r1.md | **对抗收敛待裁决**(consumable_overlay.md;r1收敛附3低) |
| T-29 | CwScreenEmblemDetailPopup 徽章详情弹窗 | **合规**(0发现)·报告=账本reports/T-29-r1.md | 无需修法,直接收口 |
| T-30 | CwScreenItemDetailPopup 物品详情弹窗 | 有问题(高0中0低2)·报告=账本reports/T-30-r1.md | **对抗收敛待裁决**(item_detail.md;r1收敛附1低) |
| T-31 | CwScreenInterruptDialog 中断对话 | 有问题(高0中0低1)·报告=账本reports/T-31-r1.md | **对抗收敛待裁决**(interrupt_dialog.md;r1 5条→r2 1词→r3定点收敛) |
| T-32 | CwScreenRefreshOddsPopup 刷新概率表 | 有问题(高0中0低1)·报告=账本reports/T-32-r1.md | **对抗收敛待裁决**(refresh_odds_popup.md;r1 4低→r2收敛附2低) |
| T-33 | CwScreenRoleDetailOverlay 角色详情浮层 | 有问题(高0中1低1)·报告=账本reports/T-33-r1.md | **对抗收敛待裁决**(role_detail_overlay.md;r1收敛附4低) |
| T-34 | CwScreenShopCardDetail 商店牌详情 | 有问题(高0中1低2)·报告=账本reports/T-34-r1.md | **对抗收敛待裁决**(shop_card_detail.md;r1收敛附4低) |
| T-35 | CwScreenPrepLockedReturn 锁定返回 | 有问题(高0中0低1)·报告=账本reports/T-35-r1.md | **对抗收敛待裁决**(prep_locked_return.md;r1 2低→r2 2低→r3定点收敛) |
| T-36 | CwScreenAhaEquipPick 顿悟装备选卡 | **合规**(0发现)·报告=账本reports/T-36-r1.md | 无需修法,直接收口 |
| T-37 | 汇总(晨报+本 README 收口) | 待新规范重审收尾后启动 | - |
