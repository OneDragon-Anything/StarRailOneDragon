# ADR-0148: P2+ 穷金重建门限(rush_level 降档 interest_first)

## Status

Accepted(2026-08-15;live 验证待 M23+,M22 起跑早于本提交未含)

## Context

- 评审 f3ab 推荐组合第二项(d1):M20 P1 r8-9 已烧空,进 P2 仅 13-18 金却被 node plan 套 spend_mode=level → rush_level(息权×0.5 + 跳卖息)→ **破产螺旋**;用户基准「P2 稳定 ≥50 吃息」。
- M21 无门对照:P2 刷新烧金 64(> M20 的 34)——穷金下越刷越穷的又一实证。

## Decision Drivers

1. 自愈式(当前金判定)优于进场粘滞:金回升 ≥ floor 自动回 rush_level,无需跨轮状态。
2. 与 ADR-0147(roll 门,35)同族语义:两门都是「P2 稳定 ≥50」基准的邻域数学表达;重建门限略低(30)——升 8 需 ~40 金级投入,30 以下 rush 无意义,息引擎(50 封顶)可渐进重建。

## Considered Options

- A. 当前金判定降档 ✅ / B. 进场金粘滞(需 session 状态,复杂且易过期)/ C. 只调 node_plan 表(P2 改 saving——伤健康金局,过度反应)。

## Decision

1. `cw_economy.P2_REBUILD_GOLD_FLOOR = 30`。
2. `_economy_mode_for`:spend=level 且 plane≥2 且 gold < floor → 返回 interest_first(息引擎重建);否则原样 rush_level。

## 验证

- 单测:P2 gold 50→rush_level / 18→interest_first / 0→interest_first(原默认态即穷金);403 passed。
- live(M23+):P2 穷进场局息引擎重建可见(金曲线回升 ≥30 后回 rush)。
