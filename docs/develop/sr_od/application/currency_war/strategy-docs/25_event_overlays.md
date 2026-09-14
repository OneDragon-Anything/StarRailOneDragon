# 25 事件面画面策略(event overlays)

> 画面族 = 节点 overlay 单选画面:货币战争-投资环境 / 货币战争-投资策略 / 货币战争-补给 / 货币战争-遭遇节点 / 货币战争-盛会之星 / 选择伙伴 / 选择装备(cw_equip_pick)/ 命运卜者强化(cw_fortune_picker)/ 骇入策划(cw_hacker_planner)/ 祈愿试炼 / 星徽秘典四选一 / 专家邀请函 / 武装箱弹窗;**能力面** = [../flow/screens-actions-capability.md](../flow/screens-actions-capability.md) §3.2/§3.6。本篇 = 该画面族的**策略面**。
> 判据本体引用不重复:九接口决策规格 = [13_pick_family.md](13_pick_family.md);事件面目录 E1-E18 = [08_events.md](08_events.md);数值单一源在代码。事件画面由外循环分支 handler 分派(overlay 不占备战/商店期动作面)。

## 1. 策略思路/算法概述

- **选卡决策**:每画面 N 选 1,决策 = pick 族接口(契约面 = `strategies/impl/cw_strategy.py::CwStrategy` 分画面入口,决策本体 = `kernel/cw_events.py::decide_event` 系);逐接口规格与选项价值序 = 13 号篇,本篇不复制。
- **刷新建议**:是否建议重掷 = `PickEvent.refresh` 布尔(零阈值结构存在性判据,P81 `../proofs/p81-invest-refresh-dominance.md`;环境屏不启用 = ADR 在案口径);策略屏逐卡刷新 = `PickEvent.refresh_slots` 槽序(逐槽计数现读 >0 才点)。刷新只是建议——是否真刷由画面 op 按现读次数裁决(失败安全)。
- **画面间差异要点**(判据细节均归 13 号篇):投资环境 = 开场必经、整局增益、难度加成随品质(`docs/game/currency_war/research/economy.md` §9);投资策略 = 局内三选一可刷新、逐槽刷新;补给 = 唯一无结算屏节点(合成 outcome 行);遭遇 = 难度卡选择 + 分支刷新。

## 2. 会执行的动作清单(按画面)

| 画面 | 动作 | 判据指针 |
|---|---|---|
| 投资环境 | 三选一 + 整组刷新重掷 | 13 号篇 decide_invest;P81 |
| 投资策略 | 三选一 + 逐槽刷新 | 13 号篇;`PickEvent.refresh_slots` |
| 补给/遭遇/盛会之星/伙伴/装备/命运卜者/策划/祈愿/星徽典籍/专家邀请函 | 选卡(N 选 1;部分带刷新钮) | 13 号篇对应接口 + 08 号篇事件目录 |
| 武装箱弹窗 | 四选一点卡(经备战执行器 `PickBoxCard` 闭环) | 13 号篇 box 卡判据(`decide_box_card`) |

事件面不做的:战斗类支出决策(事件选择不触发备战/商店判据链);overlay 在场时备战/商店动作一律让位(交外环 handler,能力矩阵篇 §4)。

## 3. 能力 vs 策略

事件面动作集(选卡/刷新/返回)与能力面同集(能力矩阵篇 §3.2/§3.6);策略收缩不涉及本画面族。
