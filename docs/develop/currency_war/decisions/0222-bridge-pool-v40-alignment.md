# ADR-0222 过渡桥池 V4.0 口径对齐(狼狩/贝洛伯格入池;引擎阵营单一源)

## Status

accepted(2026-08-22;r353)

## Context

局38-42 四局同型失败(r3-r6 掉血过快、深度散):过渡骨架全按 V3.7「仙舟+DOT」建模。V4.0+ 攻略口径(sources/V4.0-4.4_公共_难度攻略):A830+ 不提升羁绊基础伤害 → 怪血翻倍 DOT 不涨,3仙舟+2DOT 过渡不稳;能打伤害的前期羁绊五家 = 仙舟/狼狩/DOT/列车/贝洛伯格(transitions.md §1)。「狼狩」根本不在引擎阵营表——知识在 docs 里,代码没接。

## Decision Drivers

- 版本口径漂移:桥池/引擎阵营是 V3.7 时代手选,未经 V4.0 对齐
- 三处引擎阵营定义(手抄两份+派生一份)是双源隐患

## Considered Options

1. 只加狼狩进手抄表:治标,贝洛伯格仍缺,双源仍在
2. **桥池扩容 + 派生单一源**(选):新增 dot_belog(DOT2+贝洛伯格2)/hunt3(狼狩3+DOT2,飞霄 fixed)两桥;line_strategy 手抄副本删除,改 import cw_line_defs.ENGINE_FACTIONS(桥池 engine_bonds 键并集派生)
3. 全部重跑调研重建桥池:工作量大且 V4.4 数据未变,过度

## Decision

选 2。语义变化:狼狩/贝洛伯格件从「散件」升为引擎件(散店有引擎件→买优先于刷)。锁:test_cw_r271_line_defs(五阵营派生)+ test_cw_sim_finds(散店语义更新)。局43 实证:双飞霄 r1 即买,r1-r8 三连正增长、遭遇仅 -10、HP 88 峰值=四局最佳。
