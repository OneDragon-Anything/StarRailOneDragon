# AI 入口文件维护规范:AGENTS.md / AGENTS.local.md

> `AGENTS.md`(仓库根,跨工具统一源,**提交的团队共享**)和个人本地入口(**不入库**;DSH: `AGENTS.local.md` 原生加载,Claude Code: `.claude/CLAUDE.md` `@import` 引入)都是 **always-on** 文件。本文档记录这些文件的维护规范;分层判据见 [context_layering.md](context_layering.md),各工具机制见 [ai_tool_rules.md](ai_tool_rules.md)。

**两层定位**:

- `AGENTS.md` —— 团队共享 + 跨工具单一源(提交)。
- 个人本地入口 —— DSH: `AGENTS.local.md`(原生加载,无需引入语法);Claude Code: `.claude/CLAUDE.md`(`@../AGENTS.md` 引入,见 [../setup/claude-code/entry-file.md](../setup/claude-code/entry-file.md))。均不入库,不作共享试验场。

## 1. 纯指令,不掺杂元信息

入口文件**只放给 AI 的 always-on 指令**。不写维护者注释、TODO、试验状态、变更说明——即使 HTML 注释也别用(strip 是隐式行为、格式稍错就漏,且文件该保持纯净)。

元信息去向:

- 维护规范、试验流程 → 本文档。
- 具体改动原因 → commit message。
- 历史决策 → git history / spec。

## 2. 只放 always-on 该留的

逐条「删了会出错吗」自检(见 [context_layering.md](context_layering.md) §1)。特定任务 / 多步流程转 path-rule / skill / 指针;确定性动作转 hook。单文件 < 200 行。

## 3. 单一信息源(两层)

- `AGENTS.md` 是**源**(跨工具通用,**提交**)。
- 个人本地入口(DSH: `AGENTS.local.md` / Claude Code: `.claude/CLAUDE.md`)是**个人本地**(不入库),个人补充;**不复制** AGENTS.md 正文。
- 其他工具入口同理(defer 到 AGENTS.md,不复制)。
- **暂不采用 path-scoped rules**(特定任务规范放单文件,不拆 rules 目录)——原因见 §5。

## 4. 改动流程(两层,无试验晋升)

- **小改**(加 / 改一条约束):直接改 `AGENTS.md`。`AGENTS.md` 是团队共享 + 跨工具源,改动先经用户确认。
- **大改 / 重组 `AGENTS.md`**:风险大,先在**分支 / 临时文件**试验验证(跑 AI 编码会话观察表现),确认后再改 `AGENTS.md`。
  - 不用个人本地入口(`AGENTS.local.md` / `.claude/CLAUDE.md`)作共享试验场——它们个人本地(不入库、不共享),无法承载「试验 → 晋升回 AGENTS.md」的共享流程。
- **共享文档先确认**:`AGENTS.md` 是提交的团队共享文档,改动先经用户确认,不静默重写。
- **个人入口**(DSH: `AGENTS.local.md` / Claude Code: `.claude/CLAUDE.md`):个人随意改(不入库,不影响团队)。

## 5. path-scoped rules:暂不采用

评估过把「特定任务规范」(如 GUI)拆成 **path-scoped rules**(`.claude/rules/*.md` + `paths` frontmatter,Claude 读匹配文件时自动加载,省 always-on context),以及「跨工具单源」(一份源文件 + 各工具 rules 目录 **hardlink** + frontmatter 写多家字段)。

**结论:暂不采用。**

- 当前按-scope 加载的规范**需求不足**(就 GUI 一条、内容少),拆 path-scoped 收益 < 维护成本。
- 跨工具单源(硬链接)成本:git 不保留 hardlink(需脚本重建)+ 各工具 frontmatter 字段不同(Claude `paths` / Cursor·Trae `globs`)+ Qoder 不用文件 frontmatter + Codex/Pi/OpenCode 无 path-scoped——覆盖不全、运维重。
- 补充:rules 文件**不支持 `@import`**(只 CLAUDE.md 支持);rules 唯一引用机制是 hardlink/symlink,跨工具复用受限。

**现状**:特定任务规范(如 GUI)就放**单文件**(AGENTS.md 为源),不拆 path-scoped。这些规范本质是**非 always-on**(只关系部分代码库),理想落 path-scoped rule(②档);本项目不用 path-scoped,故需在 always-on(AGENTS.md)**提及其存在并指向 docs**,让智能体按需得知。提及形式按内容量:极少 → 直接进正文;较多 → 指针(一行 + 链接)。

**重启条件**:将来按-scope 规范变多(测试 / 文档 / MCP 等)且 always-on context 紧张时,再评估。

> 依据:[context_layering.md](context_layering.md) §2/§5(path-scoped 是②档,仅 Claude Code + IDE 派,不跨工具)、[ai_tool_rules.md](ai_tool_rules.md)(frontmatter 跨工具不兼容)。
