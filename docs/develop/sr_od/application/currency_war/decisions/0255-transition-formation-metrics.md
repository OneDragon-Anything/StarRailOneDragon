# ADR-0255 过渡阵容成型指标:引擎乐高/配方档/三人组三层(r394/r394b/r394c)

## Status

accepted(2026-08-23;r394/r394b/r394c;commits 45a1ea2e + d4a277e2;用户点题「为什么没有模拟位面1能否凑到过渡阵容」+「目标不只是三人组,认真看策略阵容文档」驱动)

## Context

缺口:sim 账本 `state.board` 恒空 dict——「r 几凑到配方 X 档/三人组上场」在 sim 判读不可见,只有锁线轮可观测;且首版 trio 指标理解窄了(三人组只是仙舟DOT 组合的核心层,不是过渡阵容的全部判据)。

r394c 修正动因(用户裁决驱动):外部攻略存档(V4.0 的狼狩/贝过渡建议)版本过期致误引,已 git rm;重读 `combo_methodology.md` 最终模型(r148+r149,官方 plaza API 784 篇 Early 定档)修正判据——两两组合 153 篇(仙舟3+DOT2 81 / 仙舟3+列车2 41 / 列车2+DOT2 31)全是大引擎对;贝洛伯格2/减益2/燃血2/战技点2 = 中引擎(拉条/资源型)。

## Considered Options

1. **只加 trio 指标**(首版理解):三人组=仙舟DOT 核心层,单一指标会把「凑到三人组」误当过渡成型全判据——用户点题「目标不只是三人组」。否
2. **engines≥2 即成型**(r394b 首版):只数引擎个数——贝2+减益2(纯中引擎、无大引擎)的板面被误判成型,与 784 篇定档不符。r394c 否决
3. **三层指标 + 引擎含大引擎门**(选):
   - `engines2_by_r6`:过渡成型真判据——`_transition_formed`:引擎数 ≥2 **且含至少一个大引擎**(`_BIG_ENGINES` DOT2/列车2+/仙舟3;`_MID_ENGINES` 贝2/减益2/燃血2/战技点2);
   - `recipe5_by_r6`:配方 5 档(RECIPE_BASE,r356 检查点口径);
   - `trio3_by_r8`:核心三人组(deployed∩_CORE_TRIO≥3,组合核心层)。
   数据源=账本新字段 `board_factions`(deployed 的阵营计数,生产 board 口径,flows 并计)。

## Decision

选 3。首达轮均取 ledger 逐轮扫描的最小轮;boss 局 r9 末未达=未凑成。

## Consequences

- 60 局分布立即暴露问题结构:recipe5=88% vs engines2=43% vs trio3=37%——**凑数层堆配方档,引擎门槛没凑满(空壳档位)**,与 loss≤2=1.7% 互证;成为策略主攻方向的首个量化靶子(进度树 r394 条记载);
- r394c 修正后 60 局 engines2_by_r6 0.433→0.650(中引擎组合正贡献回归真实);锁测试补纯中引擎/单引擎负例(test_transition_formed_requires_big_engine);
- 锁测试 5 条(r394);全量 1055(r394)→1056(r394c)passed;
- hunt3 桥注释的攻略引用随 sources 删除失源,待下次 review 重核(784 篇附录无狼狩独立条目,r394c commit 明示遗留)。
