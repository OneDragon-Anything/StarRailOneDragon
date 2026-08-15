# AI 编码助手接入

本仓库使用 Claude Code 协作开发。本文档是**通用方法论**(工具无关);Claude Code 专属接线在 [claude-code/](claude-code/)([入口文件引入](claude-code/entry-file.md)、[commit trailer](claude-code/commit-trailer.md))。

## 团队源 vs 个人入口

只分两层:

- **团队源 `AGENTS.md`**(仓库根,**提交**):跨工具单一来源 —— 项目架构、开发硬约束、提交流程。改它即更新所有已接入工具的行为(前提是内容确实**跨工具通用**)。
- **个人入口**(各工具自己的入口文件,**不入库**):随便弄,唯一要求是**引用到 `AGENTS.md`**。个人偏好 / 工具特有规则写这里,不进 `AGENTS.md`。

具体工具的入口文件位置 / 引入语法不同 —— Claude Code 的推荐接线见 [entry-file.md](claude-code/entry-file.md)。

> 只有「所有工具都该知道」的内容才进 `AGENTS.md`;工具特有的(如 Claude 专属 uv / context7 规则)留在该工具的个人入口。

## AGENTS.md:统一源

根 [AGENTS.md](../../../AGENTS.md) 是跨工具的单一信息源(项目架构、开发硬约束、提交流程)。修改它即等同于更新所有已接入工具的行为 —— 前提是内容确实跨工具通用,否则按两层模型放个人入口。

## MCP

- **推荐**:[context7](https://github.com/upstash/context7) — 查询库文档;建议在 `.claude/settings.json` 启用(见 [entry-file.md](claude-code/entry-file.md))。
- **项目自有游戏操作 MCP**:**已实现**。把游戏感知 / 操作(窗口状态 / 截图 / OCR / 进游戏)经 MCP 暴露给 agent,辅助开发与调试。
  - 启动:`uv run --env-file .env python -m sr_od.backend.entry.server --port 24001`(`.env` 需含 `PYTHONPATH=src`)。
  - 接入 Claude Code:`claude mcp add --transport http sr_od http://127.0.0.1:24001/mcp`。
  - 详见 [backend 文档](../sr_od/backend/README.md)(架构 / MCP / HTTP / 入口 / 远程 SSH daemon)。

## Skills

Skill 是 Claude Code(及 Codex 等少数工具)的可调用能力。要点:**每个工具只读自己目录下的 skill** —— Claude Code 读 `.claude/skills/`,**不读**根目录 `skills/`;且 skill 没有 `@import` 之类的引入逃逸口。

### 依赖 superpowers

[superpowers](https://github.com/anthropics/superpowers)(需求探索 / 计划 / TDD / 调试 / review / 收尾全链路方法论)是 Claude Code 侧插件,装不装随个人;**项目开发流程的权威方法论是公共仓 `od-dev-*` skills**(跨工具,DSH / Claude Code 都经 skill 目录加载),不依赖 superpowers。

### 命名 / 放哪

- **开发类 skill 全在公共仓 `OneDragon-Skills`**(`od-dev-` 前缀,OneDragon 系列通用;12 个:op / app / 玩法开发、画面建档、调试排查、PR 流程、skill 写作等,索引见该仓 `skills/README.md`)。标准安装:`npx skills add OneDragon-Anything/OneDragon-Skills`(agent-skills 开放标准 CLI;公共仓发布于 GitHub 后可用);维护者本地有该仓 clone,用 junction 挂进所用工具的 skill 目录(见个人入口)。Windows junction 免管理员(`mklink /J`)。
- **SR 专属 skill**(星铁独有、跨项目不成立的)放本仓根 `skills/<name>/`(**提交**,`sr-od-` 前缀),同样 junction 进工具 skill 目录(如 Claude Code 的 `.claude/skills/<name>`,**本地**不入库);目前无。

## AI 辅助提交的署名(推荐)

用 AI 编码工具协作时,推荐 commit 消息用 `Co-Authored-By` trailer 标明 AI 参与(透明、可追溯)。两种做法:**靠模型自觉**(在个人入口写指引,跨工具但会忘漏)或 **git `prepare-commit-msg` 钩子自动注入**(更稳,链式 / `git -C` / `--amend` 全覆盖)。Claude Code 的具体实现见 [commit-trailer.md](claude-code/commit-trailer.md)。

## 相关文档

- [AGENTS.md](../../../AGENTS.md) — 统一 AI 编码协作入口
- [claude-code/](claude-code/) — Claude Code 专属接线(entry-file / commit-trailer)
- [快速上手](quickstart.md)
