# 0006. 重 app 多子玩法按 app 维度建档

- **Status**: accepted
- **Date**: 2026-08-04(形式化;原始决策 2026-07-18)

## Context
随便观 1 app 调度 7+ 子玩法(游历 / 制造 / 售卖 / 饮茶仙 / 邦巢 / 好物铺 / 德丰大押),每子玩法独立画面 + `入口→子玩法→返回入口` 循环。逐画面零散建档漏 app 维度编排 + 跨画面 op 联动(子 op 委托另一个 op 的跨画面流转,如饮茶仙缺料 → 点制造补料 → 委托 `CraftDispatch` 跳制造坊)。

## Decision Drivers
- **不漏 app 编排**:节点链 / 分支 / 入口循环是 app 维度的,逐画面建档看不到整体。
- **不漏跨画面 op 联动**:子 op 委托另一个 op 的流转单画面建档会漏。
- **职责分离**:screen doc(画面事实)/ develop doc(编排)/ gameplay doc(玩法机制)各管各的。

## Considered Options
1. **逐画面零散建档**:漏 app 编排 + 跨画面 op 联动。
2. **app 维度建档 + 多 doc 分工**(选中):各子玩法画面 + develop doc + gameplay doc 分开。
3. **全塞进 screen doc**:违反「screen doc = 画面事实」(见 [ADR-0007](0007-doc-stable-facts-only.md)),变成代码说明书。

## Decision
选 2。app 有 **≥3 子玩法、各独立画面** → 按 **app 维度**建档(不是逐画面零散):
1. **入口画面 + 各子玩法画面**各自建档(每画面独立 doc,或同 doc 多子态)。
2. **app 编排**(节点链 / 分支 / 入口循环)单独成 **develop doc**(`docs/develop/sr_od/application/<app>.md`),不进 screen doc。
3. **玩法机制**(目标 / 资源 / 循环)进 **gameplay doc** → 此时**触发 `sr-od-dev-gameplay-automation` skill 对游戏玩法进行建档**(不在本 skill 内直接写玩法,避免写成代码说明书)。
4. **跨画面 op 联动**(子 op 委托另一个 op,如缺料 → 跳补料):screen doc 记「跨画面流转入口」,develop doc 记编排。

## Consequences
- **正向**:app 编排 / 跨画面 op 联动不漏;screen / develop / gameplay 职责分离清晰。
- **负向**:重 app 建档是 multi-doc 工程(工作量大);需配合 `sr-od-dev-gameplay-automation`(跨 skill 协作)。
- **边界**:单画面 / 独立 app 走常规 §1-§6 流程,不走本 ADR。

## Links
- SKILL.md「建档规模:单画面 vs 重 app」。
- 相关:[ADR-0007](0007-doc-stable-facts-only.md)(doc 职责)、[ADR-0001](0001-five-step-flow.md)(按规模缩放)。
