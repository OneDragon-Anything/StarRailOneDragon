# 0105 select_comp acq 收窄 + board penalty 加重(治 acq 主导 spread;P1 弱根因 part1)

Status: accepted
Date: 2026-08-12

## Context
review 🔴 战略层#1:select_comp 评分链 acq 乘子方差(0.15-1.0)压过 `_board_alignment`(0.7-1.2)→ 选 board 不支持但 core 易刷的 comp → spread → 永不成型(P1 弱主因,events R2 实证)。组合修:acq 收窄 + board penalty + board 梯度 + form 加法。本 ADR 修 **acq 收窄 + board penalty(part1)**;board 梯度化 + form_progress 进 comp_score 加法项 = part2(ADR-0106 动态权重)。

## Decision Drivers
- board 已有阵营是**沉没投资**(CW deployed-lock),select_comp 该优先 board 支持的 comp,而非追新方向。
- acq 作乘子上界 1.0 + 方差 0.85 直接决定排序 → 主次颠倒(acq 该是次级 tiebreak,非主导)。

## Considered Options
- **A(选)**:acq `0.15+0.85p` → `0.5+0.5p`(方差 0.85→0.5);board 全不匹配 `×0.7` → `×0.3`(重罚)。
- B:仅 acq 收窄(board ×0.7 仍不够压 acq)。
- C:仅 board 加重(acq 0.15-1.0 仍主导)。
选 A(组合 —— agent 明确「单修一个不够,区分力塌缩 + 乘法主次颠倒 环环相扣」)。

## Decision
- acq 乘子 `0.5 + 0.5 * acquirability_factor`(`p=0`→×0.5 仍降但不碾 board;`p=1`→×1.0)。
- `_board_alignment` 全不匹配 `×0.3`(原 `×0.7`)。
- board 梯度化(按命中比例)+ form_progress 进 comp_score 加法项(`W_BOARD`)= ADR-0106(comp_score 动态权重一并)。

## Consequences
- acq 方差减半 + board 全不匹配重罚 → select_comp 偏 board 支持的 comp → 减 spread(P1 弱根因 part1)。
- 调 `test_board_alignment`(0.7→0.3)。296 测试过。
- part2(board 梯度 + form 加法 + comp_score 动态权重)= ADR-0106。
