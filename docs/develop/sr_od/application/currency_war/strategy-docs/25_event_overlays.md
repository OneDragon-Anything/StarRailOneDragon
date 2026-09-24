# 25 事件面画面策略(event overlays)

> 画面族 = 节点 overlay 单选画面:货币战争-补给 / 货币战争-遭遇节点 / 货币战争-盛会之星 / 选择伙伴 / 命运卜者强化(cw_fortune_picker)/ 银狼升星(cw_yinlang_star_up)/ 祈愿试炼 / 星徽秘典四选一 / 专家邀请函 / 武装箱弹窗(原选择装备 cw_equip_pick 随该屏误判退役删除,2026-09-22);**能力面** = [../screens/README.md](../screens/README.md) §5.2/§5.5。本篇 = 该画面族的**策略面**。
> **投资环境画面已拆独立正本篇 = [28_invest_env_screen.md](28_invest_env_screen.md)**(宪法六一画面一文档,2026-09-23 迁移迭代;策略面/判据/动作全部在彼处,本篇不再辖)。
> **投资策略画面已拆独立正本篇 = [29_invest_strategy_screen.md](29_invest_strategy_screen.md)**(宪法六一画面一文档;策略面/判据/动作全部在彼处,本篇不再辖)。
> 判据本体引用不重复:九接口决策规格 = [13_pick_family.md](13_pick_family.md);事件面目录 E1-E18 = [08_events.md](08_events.md);数值单一源在代码。事件画面由外循环分支 handler 分派(overlay 不占备战/商店期动作面)。

## 1. 策略思路/算法概述

- **选卡决策**:每画面 N 选 1,决策 = pick 族接口(契约面 = `strategies/impl/cw_strategy.py::CwStrategy` 分画面入口);决策本体分画面单一源 = 各画面策略层决策器(投资策略 = `strategies/impl/mandate_v1/invest_strategy.py`,正本 29 号稿;投资环境 = `strategies/impl/mandate_v1/invest_env.py`,正本 28 号稿;其余画面 = `kernel/cw_events.py` 判据);逐接口规格与选项价值序 = 13 号篇,本篇不复制。
- **刷新建议**:是否建议重掷由各决策本体给纯值/旗标,动作包装归 flow;投资策略屏逐卡刷新 = 策略层刷新判据的槽序动作集(29 号稿 §4;P81 `../proofs/p81-invest-refresh-dominance.md`;逐槽计数现读 >0 才点);环境屏整组刷新判据 = 28 号稿 §4(单全局钮,slots 作真值哨兵)。刷新只是建议——是否真刷由画面 op 按现读次数裁决(失败安全)。
- **画面间差异要点**(判据细节均归 13 号篇;投资策略 = 29 号稿,投资环境 = 28 号稿):补给 = 唯一无结算屏节点(合成 outcome 行);遭遇 = 难度卡选择 + 分支刷新。

## 2. 会执行的动作清单(按画面)

| 画面 | 动作 | 判据指针 |
|---|---|---|
| 补给/遭遇/盛会之星/伙伴/装备/命运卜者/策划/祈愿/星徽典籍/专家邀请函 | 选卡(N 选 1;部分带刷新钮) | 13 号篇对应接口 + 08 号篇事件目录 |
| 武装箱弹窗 | 四选一点卡(经备战执行器 `PickBoxCard` 闭环) | 13 号篇 box 卡判据(`decide_box_card`) |
| 投资环境(已拆出) | 三选一 + 整组刷新重掷 | [28_invest_env_screen.md](28_invest_env_screen.md) |

事件面不做的:战斗类支出决策(事件选择不触发备战/商店判据链);overlay 在场时备战/商店动作一律让位(交外环 handler,能力矩阵篇 §4)。

## 3. 能力 vs 策略

事件面动作集(选卡/刷新/返回)与能力面同集(能力矩阵篇 §3.2/§3.6);策略收缩不涉及本画面族。
