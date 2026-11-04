# 26 战斗与结算期策略面(battle & settlement)

> 画面 = 货币战争-战斗 / 货币战争-结算 / 货币战争-结算-战报;**能力面** = [../screens/README.md](../screens/README.md) §5.6。本篇 = 该阶段的**策略面**:出战标准 + 结算读数供数 + 「战斗期无独立决策」的边界申报。
> **单一源** = 该信息的唯一权威出处;**帧** = 一次截取游戏画面并做一次决策的时点;**出战就绪段** = 从决定出战到该次战斗相关流程收尾的整段状态;**数字来源标注(四种)**:【注】游戏定义值 /【推】已证推导 /【拟】观测估计 /【拍】用户立场登记值。
> 数值单一源在代码;hp 使用边界（合法消费面闭集）单一源 = [00_framework.md](00_framework.md) §3，观测面登记 = [04_survival_budget.md](04_survival_budget.md) §1。流程编排 = `../flow/outer_loop.md` §3/§4。

## 1. 策略思路/算法概述

- **出战标准**(战斗期入口,判据落在备战期末):发出决策 = mandate_v1 决策链最先检查的发出点(判定核心 = `kernel/cw_launch_admission.py::readiness_launch_decision` 配方完备门槛 + 板面质量维;质量推迟帧不发出动作、以遥测细分键可见);富余段(金超出利息线的状态)→ 追加商店访问意图(`CwActionOpenShopParam` 普通开店形态)。**出战后只额外进一次商店,且这次访问只允许花出战奖励相关支出**(标志位 `bridge.launch_restricted_session_active`,出战就绪 ∧ 金已达利息线时置位,经 kernel 谓词 `cw_launch_arbitrage.launch_arbitration_gate` 检查;拒绝时改发 `CloseShop` 结束本次访问;该限制每个出战就绪段最多触发一次);发出执行 = 统一执行器 `operations/cw_loop.py::launch_battle_unified`(屏态复验→浮层安全检查→部署原子序→出战点击链)。
- **战斗**:自动进行(auto-battler,`docs/game/currency_war/data/gameplay.md`),bot 无决策动作——等待 + 结算探针(`operations/cw_screen/cw_screen_battle_wait.py` 三段式)。
- **结算读数供数**:结算屏三项(收入明细/连胜/利息)数值单一源 = `kernel/cw_economy.py` 注册表(机制与凭据 = `docs/game/currency_war/research/economy.md` §10/§11,本篇不复制);hp 真值链 = 结算屏 hp 读取 → 对账层 → 状态容器(GameState)三态写端（观测漏斗权威版本 = [15_observation_multisource_arbitration.md](15_observation_multisource_arbitration.md)，结算覆盖写端 = `cw_screen_battle_wait` §3.5.1);掉血结构 = P15（数据源 = 结算屏 hp 分量，观测面）。
- **连败/掉血响应**:非独立战斗期决策——结算读数只进观测与复盘（hp 是对局结果，00 §3），备战/商店判据不读 hp。败局收入补发口径 = economy.md §11(玩家裁定),供数不进策略判据权威定义。

## 2. 会执行的动作清单

| 动作 | 载体 | 策略判据 |
|---|---|---|
| 无策略动作(等待 + 结算点「继续挑战」) | `CwScreenBattleWait`(流程推进) | 无——本画面不产生策略动作;读数经观察通道进状态容器供备战/商店决策消费 |

## 3. 能力 vs 策略

战斗/结算画面能力面仅「等待/点继续」(能力矩阵篇 §3.7),策略面为空是**申报的形态**而非缺口:一切战斗相关取舍(买面/刷新/升级节奏)的前置决策都在备战期与商店期完成([22_prep_screen.md](22_prep_screen.md)/[23_shop_screen.md](23_shop_screen.md))。
