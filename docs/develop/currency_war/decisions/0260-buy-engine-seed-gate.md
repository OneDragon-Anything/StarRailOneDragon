# ADR-0260: 买侧引擎件放行通道(engine_seed;A3 修复1)

- **Status**: accepted
- **Date**: 2026-08-24

## Context

A3 实机弹药 v2.1(局63-67 五局,48 次引擎件上架全轮对拍)量化:
**判据漏 21%**——金够的 cost1-3 引擎核心件被既有 seed/pair 门跳过
(姬子·启行×3/丹恒·饮月×2/藿藿×2/忘归人×2/星期日;r6 金 19-52
仍不买)。机制:凑档/锁线谓词(`_line_wants`/`_pair_wants`)不识
「未持有引擎件」的独立价值——引擎乐高第一块砖(combo_methodology:
引擎实体 > 羁绊档位),与是否凑对/是否线内无关。

## Considered Options

1. **`_want_label` 加 engine_seed 放行分支**(P1 + 过渡体系阵营 +
   未持有 → 放行,floor 语义由调用方保留)——与既有 seed/pair 门
   **并行**不替换;boss_breaker 的 wants OR 链同步挂上(r6-r9 高金期
   判据漏的发生地)。
2. 扩 `_pair_wants` 的 allow 集——pair 门是「同阵营凑对」语义,
   塞引擎语义进去 = 两个判据搅在一起,检查器(pair/off 词表)口径
   也要跟着动。
3. 只修 r6-r9 破息窗——r3-r4 经济窗同样漏(ammo 明细覆盖 r3+),
   窗口修补留死角。

## Decision

选 1:`LineStrategy._engine_seed_wants`(① plane==1;② 卡羁绊
factions∪flows ∩ TRANSITION_TRAITS 键——**import cw_deploy_logic
单一源,不复制**;③ 未持有 `_has_same_name_copy` 为 False;④ 金够/
不破息档由调用方 rem-cost<floor 语义保留)。reason='engine_seed'
(遥测可检索;telemetry `_V2_REASONS` 词表已收)。副本门(r383b)、
copies<3 上限、bench 容量守卫全部不动作(通道只加放行,不加购买)。

## Consequences

- 锁测试 7 条(买/持有关/金不够/地板保留/P2 关/非过渡阵营关);
- 两条旧锁按 r354 先例改语义(锁的是旧通道副作用非真语义):
  r308「忘归人不买」→「不降地板+买后金≥10」;r352 拒买样例
  海瑟音(DOT flow=引擎件)→ 阿格莱雅(真线外);
- deploy_fills_cap 检查加**增长豁免**(买面变宽后「上轮买未部署」
  滞后一拍形态常态化,seed4 r2 4/6→r3 5/7 实证;围栏拦截指纹=
  deployed 停滞不是增长),r391 锁新增 1 条;
- sim A/B(n=60,pool='snapshot',指纹 942d3f79c09e2eb5 一致):
  engines2_by_r6 **0.100→0.150**,recipe5_by_r6 0.417→0.500,
  loss≤2 0.233→0.250,hp≥60 0.067 持平,avg 41.8→40.9(噪声内),
  四检查 0 违规——成型指标方向性改善,HP 结果指标未动(实机判读
  锚点:engine_seed reason 出现次数 + 局末 engines≥2)。
