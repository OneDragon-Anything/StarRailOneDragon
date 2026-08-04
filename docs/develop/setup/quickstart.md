# 快速开始（Quickstart）

> 面向第一次接触本项目的人（或 AI agent）：从零把项目在本机跑起来。
> 也可把本文档链接发给 AI agent，说「按 quickstart 帮我初始化项目」。
>
> 分三阶段，每阶段做完都会问「是否继续」——只想先把 GUI 跑起来，做完 **①** 即可。

## 前提

- **Windows**：项目仅支持 `win32`（见 `pyproject.toml` 的 `environments`）。
- **终端**：PowerShell（下文命令均为 PowerShell 语法）。
- **Git**：已安装。

## ① 跑起来（核心）

### 1. clone 主仓

```powershell
git clone https://github.com/OneDragon-Anything/StarRailOneDragon.git
cd StarRailOneDragon
```

### 2. 安装 uv

本项目用 [uv](https://github.com/astral-sh/uv) 管理依赖与 Python 版本。

```powershell
winget install --id=astral-sh.uv -e
# 或：irm https://astral.sh/uv/install.ps1 | iex
```

装完**重开终端**，`uv --version` 能输出版本即成功。

### 3. 初始化 Python 环境 + 装依赖

```powershell
uv sync --group dev
```

- uv 会按 `requires-python = ">=3.11.9,<=3.11.12"` **自动准备 Python 3.11.x**，无需手动装 Python。
- `--group dev` 必须带：本项目 `default-groups = []`，不带只会装运行依赖、漏掉 dev 组（`ruff` / `pytest` / `mcp` / `uvicorn` 等）。
- 成功判据：生成 `.venv/`、命令无报错退出。

### 4. 让 `src/` 进入模块搜索路径（src-layout 前提）

项目是 `src-layout` + `package = false`，源码在 `src/` 下，但**不会自动进 `sys.path`**。二选一（一次设置，跑 app / 测试 / 构建都生效）：

- **IDE（推荐）**：把 `src/` 设为 `Sources Root`（PyCharm），或 VS Code 里设 `PYTHONPATH=src`。
- **命令行**：每个新 PowerShell 会话先 `$env:PYTHONPATH = "src"`（会话级）；或 `setx PYTHONPATH "src"`（永久，需重开终端）。

> 也可沿用 `debug.bat`（交互式调试入口，已设置好环境）。
> 这是 **src-layout 的结构前提**，不是测试相关的 `.env`（那摊见 ②）。本阶段不需要任何 `.env` 文件。

### 5. 跑起来验证

```powershell
# 已在 IDE 设 Sources Root：
uv run python src/sr_od/gui/sr_full_app.py
# 纯命令行（本会话临时设 PYTHONPATH）：
$env:PYTHONPATH = "src"; uv run python src/sr_od/gui/sr_full_app.py
```

**主窗口（星穹铁道一条龙 GUI）弹出 = ① 完成。** app 本身不读任何环境变量。

> ① 完成即可开发、可跑 GUI。下面两阶段按需继续。

## ② 跑测试（可选）

测试代码在独立仓 `sr-od-test`，clone 到**本项目根目录**下（已被 gitignore）：

```powershell
git clone https://github.com/OneDragon-Anything/sr-od-test.git sr-od-test
```

IDE 里把 `sr-od-test/` 设为 `Test Sources Root`；运行：

```powershell
uv run pytest sr-od-test/
```

> 测试可能依赖游戏截图样本 / 运行时资源，缺失时部分用例会跳过或报错，属正常。

## ③ 配 AI 工具（可选）

### MCP（项目自有，已实现）

项目把游戏感知 / 操作（窗口状态 / 截图 / OCR / 进游戏）经 MCP 暴露给 agent，辅助开发与调试。两步（需 ① 的 `uv sync --group dev` 已装好 `mcp`）：

```powershell
# 1) 起后端 server（:24001；项目根目录，另起一个常驻终端）
$env:PYTHONPATH = "src"; uv run python -m sr_od.backend.entry.server --port 24001
# 2) 注册到 Claude Code（再另开终端）
claude mcp add --transport http sr_od http://127.0.0.1:24001/mcp
```

- **工具清单见 [sr_od/backend/mcp.md](../sr_od/backend/mcp.md)**（不在此列举，避免随实现演进过时）。
- **远程 SSH**（在别的机器 SSH 到游戏本机操作）场景下，游戏在 Session 1、SSH 在 Session 0，需用常驻 daemon 跨会话拉起 server —— 详见 [AI 编码助手接入 §MCP](ai_coding.md#mcp) 与 [sr_od/backend/](../sr_od/backend/)。

### LSP（代码导航，pyright）

项目用 uv 方式 pyright 做 LSP（定义 / 引用 / 符号），`pyproject.toml` 已配 `[tool.pyright] extraPaths=["src"]`（同 `PYTHONPATH=src` 的根因）。Claude Code 的 pyright 插件安装见 [AI 编码助手接入](ai_coding.md)。

### Skills

项目开发类 skill（`sr-od-dev-*`，如 pr-finishing / deciding-a-fix / gameplay-automation 等），Claude Code 经 `.claude/skills/` junction 自动加载；写作规范 `od-dev-writing-skills` 在公共仓 `OneDragon-Skills`（见 §Skills）。**团队采用 [superpowers](https://github.com/anthropics/superpowers) 作为开发流程方法论**（brainstorming → 计划 → TDD → review → 合并），本项目 dev skill 是叠加其上的项目特定补充，建议一并安装（`/plugin install superpowers`）。详见 [AI 编码助手接入 §Skills](ai_coding.md#skills)。

### Plugin

后续补充。

## 下一步

- 架构与开发规范：[AGENTS.md](../../../AGENTS.md)
- AI 工具接入全貌：[ai_coding.md](ai_coding.md)
- AI 编码 harness 方法论：[../harness/README.md](../harness/README.md)
