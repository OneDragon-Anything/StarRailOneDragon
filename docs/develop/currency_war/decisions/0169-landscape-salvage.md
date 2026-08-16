# ADR-0169 01+10 号成对处置:表示层之争裁决,价值地形 salvage 落地 v0

## Status

Accepted(2026-08-16;MPC 求解器与 comp 退役是破坏性重构,需独立窗口;两提案文件处置删档)

## Context

01(案例检索替代手判库)与 10(删 comp 实体换价值地形+MPC)争同一槽位(战略层表示)。
裁决依据:
- 10 的诊断更根本:离散命名目标催生系统性补偿族(commitment/pivot/绑定表/per-comp 参数表,cw_comps.py 94.5KB 几乎全在供养这一抽象);427 种羁绊组合(784 篇实证)vs ~20 条目库 = 覆盖上限是数学事实;三个表示性盲区(bench 强度 comp[黑塔纪元 ×1.4→×1.5 加码史]/连续变体/条件价值单位)在 comp 表示里写不出来只能 hack。
- 01 的可信度公式(ln(1+use) 归一)已被 17 号证伪(use 近二值头部流量,只有 5/20 聚类非零);01 的篇级案例库价值保留——编译后就是 10 地形的数据供给形态。

## Decision Drivers

1. comp 实体退役是 L 级破坏性重构(波及 select_comp 八因子/target_committed/maybe_pivot 150 行状态机/87 条 STRATEGY_BINDINGS/全部 per-comp 参数表)——需独立窗口+全量对拍,不在本轮强行。
2. 地形资产(断点效用/超加性对/单位值曲线)可独立先行——它是 06 束优化的终态估值接口(10 §2.5 预留)、09 认知地图的估值底座。

## Considered Options

- **01 案例检索路线**:部分采纳(数据形态保留,可信度公式废弃)。
- **10 全案(地形+MPC+comp 退役)**:方向采纳;MPC 与退役另开窗口。
- **v0 地形资产先行**(采纳):断点效用/对收缩/值曲线/bench 项。

## Decision

1. 新增 `cw_landscape.py`:
   - `breakpoint_utility(trait, count)`:断点效用 U——plaza 聚类覆盖度回归(「多少胜局停在 k 档」定效用差;单调由构造保证);
   - `pair_synergy(t1, t2)`:超加性对——共现 lift,n≥8 且 lift>1.05 进表,其余收缩 0(防 optimizer's curse,17 号同款纪律);
   - `unit_value_curve(char, level)`:单位值曲线(过渡牌=曲线交叉的**派生概念**,不再是 transition_chars 字段——1费 Early 高衰减/5费 Late 起);
   - `board_value(board, bench_counts, level)`:板面联合地形值(**bench 项天然支持"强度在备战席"——盲区 1 的解**;打折系数表达未上阵)。
2. 测试 5 条:断点单调/对收缩纪律/值曲线交叉(过渡派生)/盲区 1 解/激活档语义。
3. 消费端:06 束优化终态估值接口预留;与 comp_score 影子对拍后逐层退役 comp 机制(独立窗口)。

## Consequences

- MPC 滚动求解(h=2-3 beam,shop_odds 转移)+ comp 退役 → 待独立重构窗口(需全量 replay 对拍 + 13 号合约回归语料护航)。
- 01/10 提案文件处置删档;裁决关系 INDEX 留档。
