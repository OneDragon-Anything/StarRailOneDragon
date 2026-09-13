# AGENTS.md

本文件是项目级 AI 编码协作入口，只保留会直接影响实现落点与提交流程的约束。
详细规范与背景资料不要堆在这里，按需继续阅读：
- AI 编码 harness 工程方法论：[docs/develop/harness/README.md](docs/develop/harness/README.md)
- 上下文分层判据：[docs/develop/harness/context_layering.md](docs/develop/harness/context_layering.md)
- 入口文件维护规范：[docs/develop/harness/agent_instruction_files.md](docs/develop/harness/agent_instruction_files.md)
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

- 因 `pyproject.toml` 设 `[tool.uv] package = false`，运行前需确保 `PYTHONPATH=src`：PowerShell 执行 `$env:PYTHONPATH="src"`，或 `uv run --env-file .env python src/sr_od/gui/sr_full_app.py`（**`.env` 不放 `PYTHONPATH`**——DSH 启动环境校验会拒绝并阻塞从本目录启动 dsh；主 server 由 daemon/GUI spawn 时已自动注入，手动命令用前一种写法）。
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

- **涉及游戏流程的改动先理解再动手**：新功能 / debug / 修 bug 碰到自动化与游戏交互、游戏机制时，先读相关代码 + `screen_info` 弄清「bot 当前走到哪个画面、按什么玩法逻辑走」，知识缺失或过期按 `od-dev-screen-onboarding` 等 skill 补档，别凭猜改（凭猜 → 只覆盖一种情况、漏另一种 → 回归）。纯代码改动（重构 / 性能 / UI / 基建）不适用。
- 新功能优先评估是否应做成 `SrApplication`，放在 `src/sr_od/application/`，并通过 `ApplicationFactory` 接入（参考现有 `world_patrol`、`sim_universe`、`trailblaze_power` 等 `XxxAppFactory`）。
- 不要直接把新流程硬塞进主线逻辑；先复用现有 Application、Operation、配置体系与界面组件。
- 新的设置界面优先沿用现有 setting card、`YamlConfigAdapter`、`AdapterInitMixin` 等模式。

### 3. 关键运行机制

- `SrContext`（继承 `OneDragonContext`）管理懒加载服务与配置；实例级配置变更要走 `reload_instance_config()`。
- 操作链基于 `Operation` 编排；业务流程由 `SrApplication` 与各 `XxxAppFactory` 组装。
- ONNX session 的异步调用必须通过 `one_dragon.utils.gpu_executor.submit`，不要并发直调多个 session。

## 画面识别

- 代码中画面判定基于画面建档(`assets/game_data/screen_info/<screen_id>.yml`)，`id_mark` area 全命中 = `is_precise` 精准匹配。
- MCP `analyze_screen` 是匹配已建档画面，主要使用 opencv 和 OCR 识别。
- 陌生/未建档画面先走 `od-dev-screen-onboarding`。
- 视觉大模型负责画面理解，辅助新画面建档以及对已建档内容纠错。
- **坐标系统一**:框架提供的截图、画面识别、鼠标点击等，均统一至 1920×1080。唯一例外:离线分析外部传入的非 1080p 图片时,返回坐标是该图的像素空间。
- **坐标单一真相源**:所有识别、点击的坐标区域都要使用 screen_info 保存、获取,避免代码中硬编码。
- **修改 screen_info 一律走 MCP 工具**(`upsert_screen_area` / `delete_screen_area` 等),工具自动合并缓存(`_od_merged.yml`)。
- **模板资产**:框架 `cv2_utils` 全 RGB,存图走 `save_image`(别 `cv2.imencode`,BGR 假设会存反 R/B);裁模板用原始 PNG(别用 webp 有损归档)。

## 开发硬约束

- 所有函数签名、类成员变量都要有类型注解；使用 `list[str]`、`X | Y`。
- 禁止相对导入；仅类型注解使用 `TYPE_CHECKING` 导入。
- `__init__.py` 默认不要暴露模块，除非已有明确模式或收到明确要求。
- 构造函数显式声明参数，不要用 `**kwargs`。
- 路径操作使用 `pathlib`，字符串格式化使用 f-string。
- GUI 优先复用 `pyside6-fluent-widgets` 与现有项目组件，保持 Fluent Design。
- 配置改动优先落到 YAML 与对应 `YamlConfig` 子类，不要随意散落硬编码配置。
- 1080p 坐标属于项目既有前提，可以按现有模式硬编码，不要额外做分辨率适配设计。
- 模型文件（`.onnx` 等）走运行时资源下载，`.gitignore` 已忽略 `models/`，勿 `git add` 模型文件。
- OCR 结果优先使用 `one_dragon.utils.str_utils` 和目标文本做相似匹配,避免 OCR 精度问题;识别结构已知的文本,应用规则修复识别结果,例如 x/y 场景的 `/` 会被误识别成 `1`。

## 注释规范

代码注释、docstring、生成文件内嵌说明同判。

- 注释与 docstring 用中文，保持现有项目风格。
- 注释写「为什么」而非复述代码「怎么做」；写给脱离本对话的读者——他只看代码与注释就要能重建你的推导：结论从哪来（出处/算法/验证）、边界在哪、什么情况下会失效。写完自检：哪句话他只能靠猜？
- **引用必须是持久索引**：注释里禁出现会话局部标识符（W 轮次号 / rN / 批N / `[N]` 之类只在当次会话有意义的编号）；出处要么写成持久索引（ADR-NNNN、文件路径、符号名），要么写成纯语义描述（如「25 局实机 HP 轨迹校准」），二者取一。
- **一条注释一个主题，按「结论→出处→边界」摆放**：语义、校准数据、决策依据不挤进同一句；超出三行的续写说明内容放错位置了。
- **变更史不进注释**：「何时改的 / 从什么改成什么 / 勘误过程」归 git 历史（ADR 已改用户命令制）；注释只留当前值成立的理由 + 指针。自动重生成的文件，其内嵌说明同此收敛——只留当前语义 + 版本历史表，由生成器模板保证，禁止逐批续写叙述链。
- **索引/槽位字段必须带定义注释**：凡 dataclass 或函数参数中带索引、槽位、序号语义的整型字段（`idx`/`slot`/`index` 等），注释必须声明**坐标系**（哪个容器的下标 / 画面物理槽位及基）与**取值时机**（生成期快照 / 执行期现读 / 恒稳）；期望校验类防线字段（`expect`/锚定）另须注明**写入端**。新增此类字段而无定义注释 = 改完再补，不进 commit；与其它模块存在同名动作类时，须在类头声明双方坐标系差异。

## 文档规范

- 写文档用直白表述，禁自造黑话或项目内部缩写（行业通用术语可用），首次出现的项目术语给定义 + 例子。注释规范见上节，同判据。
- **知识归位（任何玩法 app 通用）**：描述游戏的知识 → `docs/game/<玩法>/`（`sources/` = 外部原文存档、`research/` = 提炼结论，只收被应用或被核实的，细则见 [docs/game/README.md](docs/game/README.md)）；描述我们的系统 → 玩法设计文档区（见下方「双层文档流」）；实现进度不进任何文档，归进度追踪。判据：随游戏版本变 → game 子树；随架构变 → 设计文档区；随 commit 变 → 进度追踪。
- **决策记录（ADR）**：仅经**用户命令**创建。日常决策 why 的默认归宿 = 设计文档动机段与代码注释；调参、方法迭代、过程件不立 ADR（现行做法的单一源在代码，考古走 git 历史）。
- **设计正文 as-built 无状态**：只写结构 / 语义 / 接口契约 / 数据流 / 边界 / 动机与约束；数值 / 权重 / 阈值只写常量名（单一源在代码）。进度标记、变更历史（归 git 历史）、状态位、会失效的现状快照禁入正文；正文只在架构变化时修改。
- 修改代码后，同步更新对应的设计文档；复杂功能、架构调整或新自动化流程，先补设计文档再实现。
- **双层文档流（设计文档区的通用模式）**：每个模块的设计文档区都用同构的双层结构——**正本区**放设计文档的正式版本，写的是「系统现在就是这么设计的」，架构改了就更新它、永远与代码现状一致（内部按需自划分），**`changes/` 子目录**放增量迭代设计（每次迭代一个子目录；迭代开始写设计 → 对抗审查 → 修改优化 → 代码实现后更新正本，迭代收尾义务）。玩法应用模块的固定路径 = `docs/develop/sr_od/application/<app_id>/`。目录结构范例：

  ```
  docs/develop/sr_od/application/<app_id>/
  ├── changes/               # 【通用必有】增量迭代设计（唯一过程区）
  │   └── <迭代名>/          #     每次迭代一个子目录；迭代开始在此写设计 → 对抗审查 →
  │                          #     修改优化 → 代码实现后更新正本（迭代收尾义务）
  ├── decisions/             # 【通用必有】ADR（用户命令制）
  └── xxx/                   # 【自由】其余正本按模块需要组织，无规定结构

  docs/develop/sr_od/backend/          # 另一模块：同构双层结构
  ├── changes/               # 【通用必有】
  ├── decisions/             # 【通用必有】
  └── xxx/                   # 【自由】
  ```

  **铁律**：`changes/` 会不定期、无理由删减——**代码与正本文档禁引其内容（长期引用），正本必须自足**；迭代内工件（任务书指针/账本 criteria/验收对照）引用总纲与详设**合法**，寿命 = 迭代。迭代设计的结构、写作硬规则与模板见 [iteration-design.md](docs/develop/harness/iteration-design.md)。
## 测试规范

写/改任何测试前先读 [sr-od-test/README.md](sr-od-test/README.md)「测试纪律」（单一源，9 条硬规则；本节只保留最高频违错的硬约束）：

1. **`test_context` 是 session 级共享**：改其属性一律 `monkeypatch.setattr`；被测生产路径含模块级全局（handler / 闩锁 / 计数器 / 缓存）时，setup 必须一并桩化——测试隔离「整条副作用链」，不是「我调了什么」。
2. **测试零真实副作用**：不写真实 `.debug/`（落盘用 `tmp_path`）；不发真实网络请求（触网链路在入口 mock）。生产模块的对外副作用（停机 / 写 flag / 外部 IO）必须「缺省关 + 启动点显式接通」，禁新写「缺省惰性 import 真实现」的接线。
3. **op 流程测试**：`execute()` 包 harness 的 `fast_sleep()`；运行态前置/复位用 `enter_running_state` / `reset_running_state`，别手写 `_run_state` 裸赋值。
4. **锁契约**：锁结构/回显，不锁分布数值；昂贵计算同次运行内只算一次、多条断言共享；改锁先重推语义——**锁红 ≠ 改动错**，禁为保绿机械跟绿（细则 = README 第 8 条「锁的存在性纪律」）。
5. **同步更新与提交前验证**：修改代码后同步更新 `sr-od-test/` 测试;提交前① 改常量 / 签名 / 数据字段先 grep 消费点与测试锁值（预判波及面）;② `ruff check` + 直接受影响测试;③ 相关测试全量一次通过才提交。
6. **运行口径**：串行为准（`uv run pytest sr-od-test/`），`-n 8` 仅本机可选、不作规范。
7. **慢桶**：单条 ≥2s 的用例入 `sr-od-test/slow_marks.txt`;快速集跑时带 `-m "not slow"` 跳过慢桶,全量跑不过滤。
8. 禁止在测试中扫描代码、注释、文档等，内容规范靠执行纪律保证。

## 提交流程与协作边界

- 默认不要主动执行 `git commit`、`git push`、`git reset`、删分支等版本控制操作，除非用户明确要求。
- **例外（自主推进 worker 批的 commit 授权，用户裁定）**：自主推进流程中的 worker 批按其任务书交付契约 **commit 自己文件面内的改动**——逐文件点名 `git add`（禁 add -A/目录级）、message 含任务 id 与阶段名、只 commit 不 push；写文档与写代码的 worker 同规则。
- 如果用户明确要求切换分支，先 `stash` 当前改动，再切换。
- Review 关注逻辑错误、运行时崩溃、死循环、资源泄漏；不要为风格问题大改现有代码。
- 提交 PR 后，review comment 需要逐条回复或修正。

## 自维护指南

修改 **AI 入口文件**(`AGENTS.md` / 个人本地 `.local`),按 `od-dev-writing-agent-instructions` skill 处理。

## Skills

开发类 skill(`od-dev-*`)全在公共仓 **OneDragon-Skills**(索引见该仓 `skills/README.md`);写 / 改 skill 按该仓 `AGENTS.md` + `od-dev-writing-skills`(4 硬规范 / writing-craft / testing)。

- **挂载**:junction 公共仓 `skills/<name>` → 所用工具读 skill 的目录(本地建、不入库;DSH: `.dsh/skills/`、Claude Code: `.claude/skills/`)。
- **SR 专属 skill**(星铁独有、跨项目不成立的)才进本仓 `skills/<name>/`(`sr-od-` 前缀,提交),同样 junction 挂载。

## 深入阅读

只在当前任务确实需要时继续看这些文档：
- AI 编码 harness 工程：`docs/develop/harness/`
- 打包说明：`.github/dev.md`
- 业务模块架构：`docs/develop/one_dragon/`（按需补充）