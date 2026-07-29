# AGENTS.md

本文件是项目级 AI 编码协作入口，只保留会直接影响实现落点与提交流程的约束。
详细规范与背景资料不要堆在这里，按需继续阅读：
- AI 编码 harness 工程方法论：[docs/develop/harness/README.md](docs/develop/harness/README.md)
- 上下文分层判据：[docs/develop/harness/context_layering.md](docs/develop/harness/context_layering.md)
- 入口文件维护规范：[docs/develop/harness/entry_files.md](docs/develop/harness/entry_files.md)
- AI 工具接入指引：[docs/develop/setup/ai_coding.md](docs/develop/setup/ai_coding.md)

## 项目概述

- 项目：星穹铁道一条龙（StarRail-OneDragon），面向 Windows 的崩坏星穹铁道自动化工具。
- 语言与环境：Python 3.11、uv、PySide6。
- 代码布局：`src-layout`，源码在 `src/`，运行时配置在 `config/`，资源在 `assets/`，开发文档在 `docs/develop/`。
- 运行基准：1080p；配置以 YAML 为主。
- 测试仓库独立维护：`sr-od-test/` 需要单独放在仓库根目录（已被 gitignore）。

## 常用命令

```shell
uv sync --group dev
uv run python src/sr_od/gui/sr_full_app.py
uv run pytest sr-od-test/
uv run ruff check src/你修改的文件.py
uv run ruff check --fix src/你修改的文件.py
```

- 因 `pyproject.toml` 设 `[tool.uv] package = false`，运行前需确保 `PYTHONPATH=src`：PowerShell 执行 `$env:PYTHONPATH="src"`，或在项目根 `.env` 写入 `PYTHONPATH=src` 后改用 `uv run --env-file .env python src/sr_od/gui/sr_full_app.py`。
- 也可以沿用 `debug.bat`（交互式调试入口，已设置好环境）。
- 只对自己修改的文件运行 `ruff check`。
- 不要对整个 `src/` 目录运行 ruff，现有仓库尚未全面适配。
- 优先使用 Windows PowerShell 可直接执行的命令。

## 架构落点

### 1. 核心分层

- `src/one_dragon/`：通用基础框架、配置、环境、工具、YOLO 能力。
- `src/one_dragon_qt/`：通用 Qt GUI 框架与公共组件。
- `src/onnxocr/`：OCR 引擎。
- `src/sr_od/`：星穹铁道业务代码，包括 application、operation、context、gui 等。

`one_dragon` / `one_dragon_qt` / `onnxocr` 是游戏无关的公共框架包（OneDragon 系列跨项目共享），星铁业务只在 `sr_od/`；公共框架的同步维护见 [common-package-sync.md](docs/develop/one_dragon/common-package-sync.md)。

### 2. 功能开发优先路径

- **涉及游戏流程的改动先理解再动手**：新功能 / debug / 修 bug 碰到自动化与游戏交互、游戏机制时，先读相关代码 + `screen_info` 弄清「bot 当前走到哪个画面、按什么玩法逻辑走」，知识缺失或过期按 `sr-od-dev-screen-onboarding` 等 skill 补档，别凭猜改（凭猜 → 只覆盖一种情况、漏另一种 → 回归）。纯代码改动（重构 / 性能 / UI / 基建）不适用。
- 新功能优先评估是否应做成 `SrApplication`，放在 `src/sr_od/application/`，并通过 `ApplicationFactory` 接入（参考现有 `world_patrol`、`sim_universe`、`trailblaze_power` 等 `XxxAppFactory`）。
- 不要直接把新流程硬塞进主线逻辑；先复用现有 Application、Operation、配置体系与界面组件。
- 新的设置界面优先沿用现有 setting card、`YamlConfigAdapter`、`AdapterInitMixin` 等模式。

### 3. 关键运行机制

- `SrContext`（继承 `OneDragonContext`）管理懒加载服务与配置；实例级配置变更要走 `reload_instance_config()`。
- 操作链基于 `Operation` 编排；业务流程由 `SrApplication` 与各 `XxxAppFactory` 组装。
- ONNX session 的异步调用必须通过 `one_dragon.utils.gpu_executor.submit`，不要并发直调多个 session。

## 开发硬约束

- 所有函数签名、类成员变量都要有类型注解；使用 `list[str]`、`X | Y`。
- 注释与 docstring 用中文，保持现有项目风格。
- 禁止相对导入；仅类型注解使用 `TYPE_CHECKING` 导入。
- `__init__.py` 默认不要暴露模块，除非已有明确模式或收到明确要求。
- 构造函数显式声明参数，不要用 `**kwargs`。
- 路径操作使用 `pathlib`，字符串格式化使用 f-string。
- GUI 优先复用 `pyside6-fluent-widgets` 与现有项目组件，保持 Fluent Design。
- 配置改动优先落到 YAML 与对应 `YamlConfig` 子类，不要随意散落硬编码配置。
- 1080p 坐标属于项目既有前提，可以按现有模式硬编码，不要额外做分辨率适配设计。
- 模型文件（`.onnx` 等）走运行时资源下载，`.gitignore` 已忽略 `models/`，勿 `git add` 模型文件。

## 文档与测试要求

- 写文档 / skill / 注释 / 入口文件用直白表述，避免自造黑话或项目内部缩写（行业通用术语可用），首次出现的项目术语给定义 + 例子。
- 修改代码后，同步更新对应的 `docs/develop/` 文档与 `sr-od-test/` 测试。
- 提交前至少验证自己改动直接影响的部分（`ruff check` + 相关测试）；若无法本地完成，要明确说明缺失前提。
- 复杂功能、架构调整或新自动化流程，先补设计/说明文档，再继续实现。

## 提交流程与协作边界

- 默认不要主动执行 `git commit`、`git push`、`git reset`、删分支等版本控制操作，除非用户明确要求。
- 如果用户明确要求切换分支，先 `stash` 当前改动，再切换。
- Review 关注逻辑错误、运行时崩溃、死循环、资源泄漏；不要为风格问题大改现有代码。
- 提交 PR 后，review comment 需要逐条回复或修正。

## 自维护指南

修改 **AI 入口文件** `AGENTS.md`（团队共享 / 跨工具单一源，提交）时，必须先按 [entry_files.md](docs/develop/harness/entry_files.md) 的规范来：纯指令不掺杂元信息、只放 always-on 该留的（「删了会出错吗」逐条自检）、单一信息源（`AGENTS.md` 是源，工具入口 `@import` 引入）、共享文档改动先经用户确认。`.claude/CLAUDE.md` 是**个人本地**（`.claude/` 整个不入库，见 entry_files.md），个人随意改。

## 深入阅读

只在当前任务确实需要时继续看这些文档：
- AI 编码 harness 工程：`docs/develop/harness/`
- 打包说明：`.github/dev.md`
- 业务模块架构：`docs/develop/one_dragon/`（按需补充）
