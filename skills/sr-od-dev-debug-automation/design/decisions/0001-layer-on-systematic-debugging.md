# 0001. 叠加在 superpowers:systematic-debugging 之上(不重写通用流程)

- **Status**: accepted
- **Date**: 2026-07

## Context
排查运行中自动化 bug 需要**两层**知识:
1. **通用 debugging 流程**(读错误 / 复现 / 找根因 / 验证,Phase 1-4)—— `superpowers:systematic-debugging` 已有成熟方法论。
2. **本项目专属坑**(两个进程日志、识别路径分歧、OCR 隐藏参数、`run_status=3` 歧义)—— 通用流程不管。

本 skill 要决定:把通用流程**重写进自己的 SKILL.md**(自含),还是**引用 `superpowers:systematic-debugging` 作基座、只写项目专属判据**(叠加)?

## Decision Drivers
- **不重复(DRY)**:通用流程已有稳定方法论,重写 = 维护两份、易漂移。
- **内聚 vs 依赖的权衡**:自含最稳(不依赖别的 skill 是否在位),叠加最精简(只写自己独有的)。
- **项目方向**:`docs/develop/harness/README.md` §方向 A 定调「本项目 dev skill 叠加在 superpowers 之上」。

## Considered Options
1. **自含:把 Phase 1-4 重写进 SKILL.md**:最独立,但重复 superpowers 已有的;通用流程更新时要跟两处;SKILL.md 变长、信号被稀释(违反 `sr-od-dev-skill-guide` token 效率)。
2. **叠加:引用 superpowers:systematic-debugging 作基座,SKILL.md 只写项目专属判据**(选中):无重复;用**完整命名空间标识符**引用(`superpowers:systematic-debugging`),符合 skill-guide 硬规范 3「可引用其它 skill,写完整标识符」。
3. **完全不提通用流程**(既不自含也不引用):智能体可能跳过「先复现 / 先读错误」直接钻项目细节,漏通用步骤。

## Decision
选 2:SKILL.md 首行声明「基座:`superpowers:systematic-debugging`,本 skill 只叠加项目专属判据」,用完整命名空间引用。通用 Phase 1-4 不重写、不在本 skill 正文重复。

## Consequences
- **正向**:SKILL.md 只含项目专属判据,精简高信号;通用流程单一源(superpowers),不漂移;完整命名空间引用 → 若 superpowers 改名,全局搜可发现。
- **负向**:**依赖 `superpowers:systematic-debugging` 在位**;若该 skill 被移除 / 不可用,本 skill 失去通用基座(只剩项目专属判据,智能体可能漏通用步骤)。判据:本 skill 的价值在「项目专属」部分,基座丢失时项目专属判据仍有用,故接受此依赖。
- **follow-up**:若团队决定全面去 superpowers 依赖(如 `sr-od-dev-skill-guide` [ADR-0005](../../../sr-od-dev-skill-guide/design/decisions/0005-drop-superpowers-dependency.md) 那样),本 skill 需重评估:要么把 Phase 1-4 吸收进自身,要么改引其它基座。本 skill 与 superpowers:systematic-debugging **无立场冲突**(后者非强制 RED 的 Iron Law 类),故当前不必跟随 skill-guide 的去依赖决策。

## Links
- SKILL.md 首行(基座声明)。
- `sr-od-dev-skill-guide` 硬规范 3(可引用其它 skill,完整标识符)。
- `docs/develop/harness/README.md` §方向 A(项目 dev skill 叠加 superpowers)。
