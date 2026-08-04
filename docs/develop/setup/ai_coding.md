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

项目已统一采用 [superpowers](https://github.com/anthropics/superpowers)(需求探索 / 写计划 / TDD / 调试 / review / 分支收尾全链路方法论)。本项目 dev skill(`sr-od-dev-*`)叠加在其之上,非替代 —— 使用者需同时具备 superpowers。Claude Code 安装:插件市场搜 `superpowers`,或 `/plugin install superpowers`。

### 命名 / 放哪

- 统一用 `sr-od-` 项目前缀:开发类 `sr-od-dev-`(指引 AI 在本项目开发 / 配置 / 构建)、使用类 `sr-od-`(指引用本项目做游戏自动化)。`sr-od-` 兼项目命名空间,防和插件 / 个人 skill 撞名。
- **SR 专属 skill** 放本仓根 `skills/<name>/`(**提交**),junction 进 AI 工具读 skill 的目录(如 Claude Code 的 `.claude/skills/<name>`,**本地**不入库)。Windows junction 免管理员(`mklink /J`)。
- **可跨项目通用的开发类 skill**(如 `od-dev-writing-skills` —— skill 写作规范)在 `OneDragon-Skills` 公共仓(`od-` / `od-dev-` 前缀)。**推荐安装该仓获取;具体安装方式后续补**。维护者本地有该仓,用 junction(见个人 `.claude/CLAUDE.md`)。

## AI 辅助提交的署名(推荐)

用 AI 编码工具协作时,推荐 commit 消息用 `Co-Authored-By` trailer 标明 AI 参与(透明、可追溯)。两种做法:**靠模型自觉**(在个人入口写指引,跨工具但会忘漏)或 **git `prepare-commit-msg` 钩子自动注入**(更稳,链式 / `git -C` / `--amend` 全覆盖)。Claude Code 的具体实现见 [commit-trailer.md](claude-code/commit-trailer.md)。

## 相关文档

- [AGENTS.md](../../../AGENTS.md) — 统一 AI 编码协作入口
- [claude-code/](claude-code/) — Claude Code 专属接线(entry-file / commit-trailer)
- [快速上手](quickstart.md)
