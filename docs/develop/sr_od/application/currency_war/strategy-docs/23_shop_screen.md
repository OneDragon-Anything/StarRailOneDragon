# 23 商店开画面策略面(shop screen)

> 画面 = 货币战争-备战-开商店(建档 `assets/game_data/screen_info/currency_war_battle_prep_shop_open.yml`);**能力面** = [../screens/README.md](../screens/README.md) §5.4。本篇 = 该画面的**策略面**:策略思路概述 + 会执行的动作清单(按用户裁定 2026-09-14 策略收缩后的目标形态)+ 形式判据指针 + 在案判例。
> 判据本体的唯一现行家 = [11_shop_decisions.md](11_shop_decisions.md)(六序/买面/卖出/刷新/升级),**引用不重复**;数值单一源在代码(常量名形态)。流程编排 = `../screens/shop.md`;决策本体 = `strategies/impl/mandate_v1/shop.py::decide_shop_action`(全函数:f(期望态)→恰一个动作),单动作循环 = `operations/cw_screen/cw_screen_buy_cards.py::run_buy_waves`。

## 1. 策略思路/算法概述

- **候选买入评估**:对店面每张牌先判类再过金约束门——件级买入判定序(六序)与 M2 义务通道语义 = 11 §1(序 1/序 2 = 骨架义务 M2,不走息律门;序 3-5 = EV 买面,判据 = `criteria/buy.py::ev_buy_candidates`/`ev_buy_veto`);合成完成买入 M2b 与核心卡支配支(C1)= 11 §1/§2 在案通道;拒因分类单一源 = `shop.py::shop_unbought_reasons`。
- **刷新门**:路径总账形式二(判据本体 = `criteria/refresh.py::r1_commitment_account`,账项装配 = `shop.py::_r1_ledger_terms`;P40 `../proofs/p40-refresh-ev.md` + 验证档 `../proofs/validations/P40_VALIDATION.md`,息损递推 = P47 `../proofs/p47-interest-account.md`);期内续刷受 R2 息线熔断(`criteria/refresh.py::r2_budget`/`r2_card_reserve`,P54);刷前过存在性门 P92(`criteria/refresh.py::all_channel_buy_exists`,`../proofs/math_proofs.md` P92 行);危机帧不变式 P36-a(`criteria/refresh.py::crisis_refresh_invariant`)先于存在性门。刷新 = **段终结**(刷后交外循环重观察重建期望态)。
- **收工判定**:「无动作可做」= 主动提案 `CloseShop`(恒可用终结,全函数契约);牌面含未识别槽(失读窗)→ 花钱动作全禁、仅关店收工(能力矩阵篇 §3.5/§4);visit 级刷新硬墙(`operations/cw_screen/cw_screen_buy_cards.py::MAX_REFRESH`)超墙后终结集降级仅关店。
- **满席腾位(收缩后目标形态)**:商店期**不卖备战**——席满而需腾位时 = 提案 `CloseShop` 离店 → 外循环交备战 → 备战期 M4 腾席卖出([22_prep_screen.md](22_prep_screen.md))→ 重开商店(`OpenShop`)继续买。牌面持久依据:节点内关店/重开不刷新商店,跨节点才自动刷新全店(`docs/game/currency_war/research/economy.md` §2.1)——腾位往返不损失已刷牌面。

## 2. 会执行的动作清单(收缩后目标形态)

| 动作 | 词表/op 载体 | 触发判据(指针) |
|---|---|---|
| 买牌 | `BuyCard` → `operations/cw_op/cw_buy_card_action.py::CwActionBuyCardOp` | 六序判类 + M2 义务 + M2b/C1 支配支 + EV 买面(§1 候选买入评估行) |
| 刷新 | `RefreshShop` → `cw_refresh_shop_action.py::CwActionRefreshShopOp`(**段终结**) | 刷新门路径总账 + R2 熔断 + P92 存在性门 + P36-a(§1 刷新门行) |
| 关商店 | `CloseShop` → `cw_close_shop_action.py::CwActionCloseShopOp`(**访问终结**) | 收工判定(§1);席满腾位链第一步 |

## 3. 能力 vs 策略(在案判例)

- **判例(用户裁定 2026-09-14)**:卖备战(`CwActionSellBenchOp`,词表摊平后单一注册行指备战 op)与买经验(`CwActionLevelUpOp` 同上)是商店开画面**可用**动作(能力矩阵篇 §3.5 两行在役),但默认策略**不在商店期做**——两者收缩至备战期决策([22_prep_screen.md](22_prep_screen.md))。
- 原则定义与记载纪律 = 能力矩阵篇 §1:能力面按「画面机制全集」记(op/词表/转移函数全保留),策略面按本篇动作清单记;收缩只改决策提案集,不删执行面。
- 商店期另不做:上阵/卖上阵(本就非商店画面动作面)。
