# 0005. 冲突解决策略(看实际不预设 + 逻辑纠缠先建档 + import 冒烟三连)

- **Status**: accepted
- **Date**: 2026-08-04(形式化日;决策本身随 skill 创建 ~2026-07)

## Context
解 merge 冲突(merge origin/main 时)有两类反模式:① **盲合**游戏流程冲突 → 错配(不知道当前游戏画面/流程长什么样);② **预设「游戏流程冲突必复杂」** → 实际很多是机械可解(注释/import/不同区域 additive)。另外,解完只做 `py_compile` 不够 —— compile 只查语法,抓不到运行时导入/符号缺失(合并后某侧删了符号另一侧还引用)。踩坑:#2300(charge_plan 三 PR 纠缠)正是先 live 建档了 charge_plan 玩法(资源栏+道具处理),才正确融合了 #2300 的兑换以太电池与 main 的每日重置/双倍活动,没靠盲合。

## Decision Drivers
- **不盲合**:游戏流程逻辑纠缠要先搞清当前真实结构。
- **不预设复杂**:很多冲突机械可解,别过度处理。
- **解完真稳**:三连验证抓运行时符号缺失,不只语法。

## Considered Options
1. **一律盲合**:游戏流程冲突会错配。
2. **一律先 live 建档再解**:机械冲突(注释/import)过度处理,浪费时间。
3. **看实际冲突再判 + 逻辑纠缠才建档 + import 冒烟三连**(选中):判据式分流。
4. **解完只 py_compile + ruff**:漏运行时导入/符号缺失。

## Decision
选 3:
- **看实际冲突再判断,别预设复杂**:很多「看似游戏流程」的冲突其实机械可解(注释/import/不同区域 additive)。
- **逻辑纠缠(同文件两侧都改核心)→ 先 live 建档该玩法**(搞清当前真实结构),再据此融合,不盲合。
- **解完三连验证**:`py_compile` + `ruff` + **`import` 冒烟**(实际导入模块)。`import` 比 compile 强,抓运行时导入/符号缺失。

## Consequences
- **正向**:机械冲突快解、逻辑纠缠不盲合;三连验证抓运行时缺失。
- **负向**:判「逻辑纠缠」靠人判;live 建档耗时(但只对真纠缠才做)。
- **follow-up**:无。

## Links
- SKILL.md §6(冲突解决)。
- 相关:[ADR-0001](0001-integration-baseline-discipline.md)(merge main 触发冲突)、[ADR-0004](0004-gameplay-understanding-before-diff.md)(先建玩法理解)。
