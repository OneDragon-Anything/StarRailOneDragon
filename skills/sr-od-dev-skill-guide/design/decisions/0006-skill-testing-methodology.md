# 0006. skill 测试方法论(偏离 superpowers 强制 RED,采纳 utility test 作方法论型主方法)

- **Status**: accepted
- **Date**: 2026-08-04

## Context
SKILL.md「两类 skill」说 **GREEN 验证不可省**,但一直没给具体方法。superpowers 的 `testing-skills-with-subagents` 给的是 **pressure-scenario 法**(专注 discipline / compliance,one-shot A/B/C + 多重压力 + 抓 rationalization)—— 但它自己明说"别测 reference / 无规则可违 / agent 无动机绕过的 skill"。
本项目**多数 skill 是方法论覆盖型 / how-to / reference**(gameplay-automation / screen-onboarding / ui-region-detect / deciding-a-fix / debug-automation),要测的是"**能不能照方法论把活干好**",不是"守不守纪律"。pressure test 不对症。
用户做法:**干净工作空间 + 可交互子 agent + 扮用户只答所问 + 观察 gap + 修 skill + 循环** —— 正是方法论型的 GREEN 方法(可用性测试 / dogfooding 思路)。

## Decision Drivers
- **GREEN 要有具体可操作方法**(否则"GREEN 不可省"是空话)。
- **对症**:方法论型(测实用性 / 完整性)vs 纠正型(测纪律)用不同测法。
- **不盲从 superpowers 强制 RED**(外部效度不足,见 ADR-0004 / writing-craft §3.1)。

## Considered Options
1. **全盘采 superpowers pressure test**:不对症方法论型 + 强制 RED(违背两类 skill)。
2. **分两类**(选中):方法论型 = utility test(用户法)、纠正型 = pressure test;RED 按型可省。
3. **不规定测试法**:GREEN 空洞,等于没验证。

## Decision
选 2:
- `references/skill-testing.md` 记两制度;**方法论型主方法 = utility test**(干净工作空间 + 可交互子 agent + 扮用户只答所问 + 观察 gap + RCA 过滤 + 修 + 循环);**纠正型 = pressure test**(superpowers 思路)。
- RED 按两类 skill(方法论型可省,纠正型做 baseline)。
- SKILL.md「两类 skill」的 GREEN 链到 skill-testing。

## Consequences
- **正向**:GREEN 有实操方法;对症(方法论型用 utility、纠正型用 pressure);保留 RED 弱化立场(不被 superpowers Iron Law 绑架)。
- **负向**:utility test 耗时(需扮用户多轮),一次实测成本不低。
- **follow-up**:① 用本方法**实测 skill-dev-guide 自身**(找个不规范 skill 让子 agent 按本 guide 修,验证 guide 完整性)—— 即写完本 ADR 立刻做;② 其他 skill 逐个补 GREEN。

## Links
- SKILL.md「两类 skill」(GREEN 链到本方法)。
- [`../../references/skill-testing.md`](../../references/skill-testing.md)(两制度 + utility test 详解 + checklist)。
- `writing-craft.md` §3.1(观察到的 gap 经 RCA 过滤再进 skill)。
- 同源 superpowers 偏离:[ADR-0005](0005-drop-superpowers-dependency.md)。
