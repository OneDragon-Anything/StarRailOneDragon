# 26 战斗与结算期策略面(battle & settlement)

> 画面 = 货币战争-战斗 / 货币战争-战斗结算 / 货币战争-结算 / 货币战争-结算-战报;**能力面** = [../screens/README.md](../screens/README.md) §5.6。本篇 = 该阶段的**策略面**:出战标准 + 结算读数供数 + 「战斗期无独立决策」的边界申报。
> 数值单一源在代码;hp 消费唯一登记处 = [04_survival_budget.md](04_survival_budget.md) §7 授权对账表。流程编排 = `../flow/outer_loop.md` §3/§4。

## 1. 策略思路/算法概述

- **出战标准**(战斗期入口,判据落在备战期末):发射决策 = mandate_v1 前置发射位(2026-09-16 迁移;判定核 = `kernel/cw_launch_admission.py::readiness_launch_decision` 配方完备门槛 + 板面承重质量维;质量推迟帧不发射分键显影);溢出段 → 受限商店访问**意图**(`OpenShop(restricted_spend=True)`,预算闸拒因 = 花后金位跌破息线),执行 = 备战访问 op 内仲裁单元(`operations/cw_loop.py::_launch_frame_arbitration`,第三载体 `[cw-op]` 行口径不变);发射执行 = 统一执行器 `operations/cw_loop.py::launch_battle_unified`(屏态复验→浮层安全检查→部署原子序→出战点击链)。
- **战斗**:自动进行(auto-battler,`docs/game/currency_war/data/gameplay.md`),bot 无决策动作——等待 + 结算探针(`operations/cw_screen/cw_screen_battle_wait.py` 三段式)。
- **结算读数供数**:结算屏三项(收入明细/连胜/利息)数值单一源 = `kernel/cw_economy.py` 注册表(机制与凭据 = `docs/game/currency_war/research/economy.md` §10/§11,本篇不复制);hp 真值链 = 结算读点经新鲜度门(`strategies/impl/cw_strategy.py::gated_hp`)覆盖现读;掉血结构 = P15(消费授权见 04 §7 表 #2)。
- **连败/血线响应**:非独立战斗期决策——全部折算进备战/商店判据(血预算停追级线 = [22_prep_screen.md](22_prep_screen.md) §1;危机刷新不变式 P36-a = [23_shop_screen.md](23_shop_screen.md) §1;升档器血线硬地板 = 00 号篇 §4)。败局收入补发口径 = economy.md §11(玩家裁定),供数不进策略判据本体。

## 2. 会执行的动作清单

| 动作 | 载体 | 策略判据 |
|---|---|---|
| 无策略动作(等待 + 结算点「继续挑战」) | `CwScreenBattleWait`(流程推进) | 无——本画面不产生策略动作;读数经观察通道进容器供备战/商店决策消费 |

## 3. 能力 vs 策略

战斗/结算画面能力面仅「等待/点继续」(能力矩阵篇 §3.7),策略面为空是**申报的形态**而非缺口:一切战斗相关取舍(血预算/刷新危机/升级节奏)的前置决策都在备战期与商店期完成(22/23 号篇)。
