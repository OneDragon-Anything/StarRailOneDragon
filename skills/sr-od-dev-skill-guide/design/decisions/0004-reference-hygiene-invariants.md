# 0004. 引用卫生硬门 + 硬规范作不变量(编辑也守)

- **Status**: accepted
- **Date**: 2026-08-04

## Context
两个观察到的真实问题:
1. **闭包外依赖**:skill 引用了不在共享产物里的内容 —— gitignored 文件(`.debug/` / `config/` / `.claude/` / `models`)、个人 local 文件、**memory**(个人本地、不跨人共享)。skill 是已提交的共享 artifact,引用闭包外状态 = 在别人机器 / CI / clean checkout 上不存在(类比代码硬编码 `/home/alice/...`)。
2. **过时**:引用「已提交但 skill 文件夹外」的内容,外部改了、skill 引用没跟着变。原规范 3 讲「稳定可引 / 易变抽象」,但**没说 target 必须已提交**,也没给过时检测机制。
3. 此外:规范只在「新建 skill」时被想到,「编辑已有 skill」时容易漏查 → 违规悄悄混进去。

## Decision Drivers
- **共享 artifact 自含**:依赖闭包必须全在产物里(发布工程基本约束)。
- **防过时**:外部引用要么稳定要么可校验,否则必腐。
- **不变量**:规则是 skill 必须恒满足的性质,不只新建时查 —— 编辑(哪怕一行)也要保持。

## Considered Options
1. **轻档**:规范 3 加硬门(target 必须已提交,禁 gitignored / memory)+ 把 4 规则定为不变量(编辑保持,新增引用过门)+ design-docs 记过时应对 4 档谱作指导(选中)。
2. **重档**:轻档 + 建 CI checker 扫 skill 引用,验证 target 存在 + 已提交,失踪 → 红(把过时检测自动化)。
3. **不变**:不解决问题(memory / gitignored 引用继续混入)。

## Decision
选 1(轻档):
- 规范 3 加**硬门**:引用 target 必须**已提交**;gitignored / 个人 local / memory 一律禁(不分独立发布 / 项目内场景)。
- 4 条硬规范定为**不变量(invariant)**:新建全套满足;编辑至少不破坏 + 新增项满足;流程 step 4 自检对新建和编辑都强制,编辑额外查新增引用是否过门。
- `references/design-docs.md` §引用卫生 记**防过时 4 档谱**(依赖稳定契约 / 校验引用 / SSOT+运行时读 / 吸收自含)+ 选档判据,作指导(轻档不强制)。

## Consequences
- **正向**:消除闭包外依赖(禁 memory / gitignored);编辑时自查新引用,防违规混入;过时应对有谱可循(不再只有「抽象化」一档)。
- **负向**:轻档**无自动过时检测**,仍靠人自觉 + PR review;第 2 档(CI checker)、第 3 档(运行时读)未落地。
- **follow-up**:① 重档建 CI checker(第 2 档);② 扫现有 skill 修已存在的 memory / gitignored 引用违规;③ `sr-od-miyoushe` 等「见 design.md」类违规(使用信息误进 design)一并清。

## Links
- SKILL.md 规范 3(硬门)+ 硬规范头部(不变量 callout)+ 流程 step 4。
- `../../references/design-docs.md` §引用卫生(4 档谱)。
- 同源问题:auto-memory `no-memory-refs-in-code-comments`(代码注释禁引 memory;本 ADR 把同约束扩到 skill 正文)。
