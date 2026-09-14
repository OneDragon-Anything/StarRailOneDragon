# AGENTS.md

## 1.项目概述

- 项目：星穹铁道一条龙（StarRail-OneDragon），面向 Windows 的崩坏星穹铁道自动化工具。
- 语言与环境：Python 3.11、uv、PySide6。
- 代码布局：`src-layout`，源码在 `src/`，运行时配置在 `config/`，资源在 `assets/`，开发文档在 `docs/develop/`。
- 运行基准：1080p；配置以 YAML 为主。
- 测试仓库独立维护：`sr-od-test/` 需要单独放在仓库根目录（已被 gitignore）。

### 1.1.目录结构

```
StarRailOneDragon/
├── src/                                # 源码（src-layout）
│   ├── one_dragon/                     # 公共框架（游戏无关）：配置 / 环境 / 工具 / YOLO
│   ├── one_dragon_qt/                  # 公共 Qt GUI 框架与公共组件
│   ├── onnxocr/                        # OCR 引擎
│   └── sr_od/                          # 星穹铁道业务：application / operation / context / gui 等
├── config/                             # 运行时配置（YAML）
├── assets/
│   └── game_data/
│       └── screen_info/                # 画面建档：<screen_id>.yml（识别用 area / 模板 / OCR 配置，机器读）
├── docs/
│   ├── game/                           # 玩法建档：人读 + AI 理解的游戏知识（细则见 docs/game/README.md）
│   │   ├── screens/                    #   画面知识 doc（与 screen_info 对齐）
│   │   ├── gameplay/<玩法>.md          #   玩法总览 doc
│   │   ├── mechanics/                  #   跨玩法机制 doc
│   │   └── <玩法>/{sources,research}/  #   玩法原文存档 / 提炼结论
│   └── develop/
│       ├── harness/                    # AI 编码 harness 工程
│       ├── one_dragon/                 # 公共框架架构
│       └── sr_od/
│           ├── application/<app_id>/   # 玩法应用设计文档区（双层文档流，见「文档规范」）
│           └── backend/                # 设计文档区（同构双层结构）
├── skills/<name>/                      # SR 专属 skill（sr-od- 前缀，提交）
├── deploy/                             # 打包构建脚本（说明见 .github/dev.md）
├── tools/                              # 辅助脚本（cw / mcp / worktree）
└── sr-od-test/                         # 测试仓库（独立 git 仓，不入本仓）
```

`one_dragon` / `one_dragon_qt` / `onnxocr` 是游戏无关的公共框架包（OneDragon 系列跨项目共享），星铁业务只在 `sr_od/`；公共框架的同步维护见 [common-package-sync.md](docs/develop/one_dragon/common-package-sync.md)。

### 1.2.常用命令

```shell
uv sync --group dev
uv run python src/sr_od/gui/sr_full_app.py
uv run pytest sr-od-test/ -m "not slow"   # 测试全量（串行、排除慢桶）
uv run ruff check src/你修改的文件.py
uv run ruff check --fix src/你修改的文件.py
```

- 因 `pyproject.toml` 设 `[tool.uv] package = false`，运行前需确保 `PYTHONPATH=src`：PowerShell 执行 `$env:PYTHONPATH="src"`，或 `uv run --env-file .env python …`（**`.env` 不放 `PYTHONPATH`**，会被部分工具的启动环境校验拒绝；手动命令优先前者）。
- 只对自己修改的文件运行 `ruff check`。
- 不要对整个 `src/` 目录运行 ruff，现有仓库尚未全面适配。
- 优先使用 Windows PowerShell 可直接执行的命令。

### 1.3.关键架构

- `SrContext`（继承 `OneDragonContext`）管理懒加载服务与配置；实例级配置变更要走 `reload_instance_config()`。
- 操作链基于 `Operation` 编排；业务流程由 `SrApplication` 与各 `XxxAppFactory` 组装。

## 2.功能开发优先路径

- **涉及游戏流程的改动先理解再动手**：新功能 / debug / 修 bug 碰到自动化与游戏交互、游戏机制时，先读相关代码 + `screen_info` 弄清「bot 当前走到哪个画面、按什么玩法逻辑走」，知识缺失或过期按 `od-dev-screen-onboarding` 等 skill 补档，别凭猜改（凭猜 → 只覆盖一种情况、漏另一种 → 回归）。纯代码改动（重构 / 性能 / UI / 基建）不适用。
- 新功能优先评估是否应做成 `SrApplication`，放在 `src/sr_od/application/`，并通过 `ApplicationFactory` 接入（参考现有 `world_patrol`、`sim_universe`、`trailblaze_power` 等 `XxxAppFactory`）。
- 不要直接把新流程硬塞进主线逻辑；先复用现有 Application、Operation、配置体系与界面组件。
- 新的设置界面优先沿用现有 setting card、`YamlConfigAdapter`、`AdapterInitMixin` 等模式。

## 3.Operation 最佳实践

- 找元素、点按钮，优先用 `round_by_find_and_click_area`：坐标存在 screen_info（建 area），按「画面名 + 区域名」找，找到才点。不要全屏 OCR 找字，不要在代码里写死坐标。
- 写一个节点先想清楚三件事：**当前画面是什么、这个节点要做什么操作、做完之后画面是留在本屏还是切到别的屏**。
- 画面要切换的操作（点关闭、点确认跳转），把「切换证据」直接写进 `round_by_find_and_click_area` 的 until 参数：
  - `until_find_all=[(目标画面, 区域名)]` —— 目标画面的标志出现才算成功（例：点「开始战斗」→ 等战斗画面标志出现）；
  - `until_not_find_all=[(画面, 区域名)]` —— 刚点的按钮/弹窗消失才算成功（例：点「关闭」→ 等弹窗区域消失）。
  - ⚠️ 不传 until 时点击成功就立刻 `round_success`，等于没验证转移。「点了」≠「成了」：点击可能没生效，下一个节点会在错误画面上继续跑，流程卡死。
- 禁用键盘 ESC 关闭/返回/退出/跳过，一律 screen_info 建档后点画面上的控件；其余按键（移动/交互）也尽量不用，确需用时注释声明原因。理由：前向兼容手机模拟器（无键盘）。
- 完整方法论（round 结果语义、节点粒度、循环结构选型、调试纪律）见 skill `od-dev-write-operation`。

## 4.Application 最佳实践

- 写 app 自底向上：先把用到的各个 op 写完、`run_operation` 单独跑通，再写 app 把它们串起来，最后 `run_standalone_app` 端到端跑。别先搭 app 壳再慢慢填 op——出问题时分不清是 op 错还是串联错。
- app 节点图遵循 hub 模式：第一个节点先回到最通用的画面（主界面，即 hub），流程从主界面出发，最后一个节点回主界面。单独跑还是一条龙连跑，起止状态都确定，app 之间在主界面干净交接。检测游戏窗口/进游戏由框架自动插入，app 里不写。
- 完整步骤（const / run_record / config / factory / app 五件套、GUI、run-record）见 skill `od-dev-write-application`。

## 5.画面识别

- **所有画面都应建档到 screen_info**（`assets/game_data/screen_info/<screen_id>.yml`）：bot 会遇到、需要交互的画面都要建档保存；需要识别、交互、读取的内容都要建成 area——screen_info 是画面识别与交互的唯一事实源。
- **每个画面尽量找到自己独有的 id_mark 组合**：id_mark = 画面独有的稳定元素（文本或模板），组合内全部命中才算精准匹配（`is_precise`）；通常 1-2 个即可，别把所有 area 都标成 id_mark。只有少数没有独有稳定锚的浮层（如点击空白处关闭的弹窗）找不到不冲突的 id_mark，才不设。
- **画面判定优先用框架方法，别手写截图 + OCR 比对**：判断「是不是目标画面」用 `screen_utils.is_target_screen`；识别「当前在哪个画面」用 `screen_utils.get_match_screen_name`（op 内用 `check_and_update_current_screen`，识别并保存结果）。
- 运行失败、流程卡死时，第一步先弄清 bot 当前停在哪个画面（截图识别，可用 MCP 的 `analyze_screen`）；陌生/未建档画面先走 `od-dev-screen-onboarding` 建档，再继续修——别凭猜改。
- 视觉大模型负责画面理解，辅助新画面建档以及对已建档内容纠错。
- **坐标系统一**：框架提供的截图、画面识别、鼠标点击等，均统一至 1920×1080。唯一例外：离线分析外部传入的非 1080p 图片时，返回坐标是该图的像素空间。
- **坐标单一真相源**：所有识别、点击的坐标区域都要使用 screen_info 保存、获取，避免代码中硬编码。
- **不能单独修改 screen_info 的 yml 文件**：运行时加载的是合并缓存（`_od_merged.yml`），手改分 yml 不更新缓存 = 改了也白改。
- **模板资产**：框架 `cv2_utils` 全 RGB，存图走 `save_image`（别 `cv2.imencode`，BGR 假设会存反 R/B）；裁模板用 webp 无损归档。

## 6.MCP

项目的游戏操作能力通过 MCP server 暴露：跑 operation / application / 一条龙、截图与画面识别、screen_info 维护、点击按键等。启动脚本在 `tools/mcp/`，server 由 daemon 管理启停。

- **改了任何 Python 代码，都要重启项目 MCP server 才生效**——server 进程缓存了已加载的模块与 app 实例。「改完跑、行为没变」先想到这条，别先怀疑改动没写对。
- 更新 screen_info 用 MCP 工具（`upsert_screen_area` / `delete_screen_area` 等）：改对应 yml 并顺便更新合并缓存（`_od_merged.yml`）；别手改 yml（原因见「画面识别」）。
- server 同一时间只跑一个运行（单跑道），运行中再发起会被拒绝，重启同样被拒——先查运行状态，必要时 `stop_run` 停掉再重启。

## 7.开发硬约束

- ONNX session 的异步调用必须通过 `one_dragon.utils.gpu_executor.submit`，不要并发直调多个 session。
- 所有函数签名、类成员变量都要有类型注解；使用 `list[str]`、`X | Y`。
- 禁止相对导入；仅类型注解使用 `TYPE_CHECKING` 导入。
- `__init__.py` 默认不要暴露模块，除非已有明确模式或收到明确要求。
- 构造函数显式声明参数，不要用 `**kwargs`。
- 路径操作使用 `pathlib`，字符串格式化使用 f-string。
- 复杂循环与数值运算，优先转换为 numpy 向量化计算，别用 Python 循环逐元素处理（性能差数量级）。
- GUI 优先复用 `pyside6-fluent-widgets` 与现有项目组件，保持 Fluent Design。
- 配置改动优先落到 YAML 与对应 `YamlConfig` 子类，不要随意散落硬编码配置。
- 模块怎么写才方便测试：对外的真实动作（停机 / 写 flag / 截图 / 外部 IO）一律做成可注入回调——默认什么都不做，真实现由运行入口在启动时传入，测试不注入就零副作用；禁「默认没传入就自动用真实现」的写法（测试会沿调用链深处触发真实动作，mock 入口也拦不住）。
- 1080p 坐标属于项目既有前提，可以按现有模式硬编码，不要额外做分辨率适配设计。
- 模型文件（`.onnx` 等）走运行时资源下载，`.gitignore` 已忽略 `models/`，勿 `git add` 模型文件。
- OCR 结果优先使用 `one_dragon.utils.str_utils` 和目标文本做相似匹配,避免 OCR 精度问题;识别结构已知的文本,应用规则修复识别结果,例如 x/y 场景的 `/` 会被误识别成 `1`。

## 8.注释规范

代码注释、docstring、生成文件内嵌说明同判。

- 注释与 docstring 用中文，保持现有项目风格。
- 注释写「为什么」而非复述代码「怎么做」；写给脱离本对话的读者——他只看代码与注释就要能重建你的推导：结论从哪来（出处/算法/验证）、边界在哪、什么情况下会失效。写完自检：哪句话他只能靠猜？
- **引用必须是持久索引**：注释里禁出现会话局部标识符（W 轮次号 / rN / 批N / `[N]` 之类只在当次会话有意义的编号）；出处要么写成持久索引（ADR-NNNN、文件路径、符号名），要么写成纯语义描述（如「25 局实机 HP 轨迹校准」），二者取一。
- **一条注释一个主题，按「结论→出处→边界」摆放**：语义、校准数据、决策依据不挤进同一句；超出三行的续写说明内容放错位置了。
- **变更史不进注释**：「何时改的 / 从什么改成什么 / 勘误过程」归 git 历史；注释只留当前值成立的理由 + 指针。自动重生成的文件，其内嵌说明同此收敛——只留当前语义 + 版本历史表，由生成器模板保证，禁止逐批续写叙述链。
- **索引/槽位字段必须带定义注释**：凡 dataclass 或函数参数中带索引、槽位、序号语义的整型字段（`idx`/`slot`/`index` 等），注释必须声明**坐标系**（哪个容器的下标 / 画面物理槽位及基）与**取值时机**（生成期快照 / 执行期现读 / 恒稳）；期望校验类防线字段（`expect`/锚定）另须注明**写入端**。新增此类字段而无定义注释 = 改完再补，不进 commit；与其它模块存在同名动作类时，须在类头声明双方坐标系差异。

## 9.文档规范

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
  ```

  **铁律**：`changes/` 会不定期、无理由删减——**代码与正本文档禁引其内容（长期引用），正本必须自足**；迭代内工件（任务书指针/账本 criteria/验收对照）引用总纲与详设**合法**，寿命 = 迭代。迭代设计的结构、写作硬规则与模板见 [iteration-design.md](docs/develop/harness/iteration-design.md)。

## 10.测试规范

写/改任何测试前先读 [sr-od-test/README.md](sr-od-test/README.md)「测试纪律」（单一源；本节只保留最高频违错）。

### 10.1.第一原则：测试只覆盖核心内容，极致运行效率

自动化没法靠人肉回归，测试就是质量底线——但**只测核心**。每条测试锁的都是「这段代码应该怎么表现」，来源只有两个：

- **新功能**：锁设计约定——功能按设计文档应该怎么表现（关键路径 + 设计明确处理的边界），测试随功能一起写，就是可执行的设计说明；设计里没约定的行为不要瞎测。
- **存量功能**：锁真实故障——出过的事故、真实可能发生且后果严重的故障形态（卡死一条龙、登录失败、认错画面）。

写不出锁的期望表现的，一律不写：琐碎逻辑、构造完对象逐字段断言、语言自带保证、与其他测试重复的内容。由此：

1. **测试要少**：两条测同一件事 = 冗余，能合并就合并。测试越堆越多，真正的失败越容易被淹没——漏看的红等于没有测试。
2. **慢计算只算一次**：OCR / 识别 / 模拟这类慢计算，同一条测试里只跑一次，结果存下来给所有断言共用，别每个断言各算一遍。
3. **默认不用并行测试**，串行为准。
4. **慢速集**：单条实测 ≥2s 的用例，登记进 `sr-od-test/slow_marks.txt`。

### 10.2.测试基础设施

1. **conftest.py**——pytest 自动加载的公共设施：提供全测试共享的 `test_context`、OCR 结果缓存、日志隔离，以及防污染守卫（共享对象裸赋值自动警告并还原）。
   - `test_context` 是这次测试运行里**所有测试共用的同一个对象**：A 测试改了它的属性，B 测试拿到的就是改过的值——「单跑能过、全量必挂」的假随机失败就来自这。改它的属性必须用 `monkeypatch.setattr`（测试结束自动还原），别裸赋值。
   - 被测生产代码内部还会改模块级全局（注册的 handler、闩锁、计数器、缓存），这些不会自动还原——setup 时要把调用链上会碰到的全局一并桩掉，只桩你直接传的参数不够。
2. **fixture_controller.py**——op / app 流程测试 harness：假游戏控制器、看门狗、运行态前置复位、`fast_sleep`（用法见 10.3）。

### 10.3.Operation / Application 测试规范

1. **流程测试不连真游戏**：用 harness（`sr-od-test/test/harness/fixture_controller.py`）代替——按你写的剧本演：每步给哪张截图当画面、点击落在哪个区域就推进到下一步；op 在上面跑完整流程，所有点击/输入都有记录供断言，轮次太多会自动停（防卡死）。
2. 框架的运行依赖 context 状态，测试必须先把状态设对，进入「运行中」状态用 `enter_running_state`，测试收尾复位用 `reset_running_state`；别直接改 `_run_state` 字段。
3. **跳过框架等待**：跑 op 包一层 `with fast_sleep(): op.execute()`——框架的点击前/轮次间等待是给真机等画面用的，测试里画面是 mock 的、无需等待；不包的话这些等待照真实睡，一条测试大半时间耗在干等上。

### 10.4.高频违错硬约束

1. **测试零真实副作用**：不碰真实环境——项目目录内不写任何文件（落盘只进 pytest 的 `tmp_path`）、不发真实网络请求；断言依据一律来自测试自造的输入或提交进仓的 fixture，不读本机易失产物。
2. **测试红了，先判断再改**：断言的是结果的「应该的样子」（结构、状态文案这类），不断言会随正常调整变动的统计数值。测试红 = 实际行为和预期不一致，先判断是代码错了还是测试过时了：代码错就修代码；确认代码是对的，才更新测试期望。禁止不加判断直接改期望值让测试变绿（细则 = sr-od-test/README.md「写测试」节）。
3. **同步更新与提交前验证**：修改代码后同步更新 `sr-od-test/` 测试；提交前① 改常量 / 签名 / 数据字段先 grep 消费点与测试断言值；② `ruff check` + 直接受影响测试；③ 相关测试全量一次通过才提交；④ 提交后 `git show --stat` 复核入库面 = 申报面（细则 = sr-od-test/README.md「提交」节）。
4. **源码扫描测试一律禁止**：不在测试里读取/扫描源码做断言——退役符号墓碑、依赖方向守卫、包布局守卫等同样禁止，无例外。

## 11.提交流程与协作边界

- **自主 commit 是默认动作**：按阶段提交——每完成一个阶段（一个功能点 / 一处修复 / 一批文档），就 commit 一次，别把多个阶段攒成一大包（意外丢工作区 = 全丢）。
- `git add` 一律逐文件点名，禁 `add -A` 和目录级 add——粗粒度 add 会静默卷入并行批的在飞改动。
- **push 仍需用户明确要求**；`git reset`、删分支等破坏性操作禁止。
- 如果用户明确要求切换分支，先 `stash` 当前改动，再切换。
- Review 关注逻辑错误、运行时崩溃、死循环、资源泄漏；不要为风格问题大改现有代码。
- 提交 PR 后，review comment 需要逐条回复或修正。

## 12.自维护指南

修改 **AI 入口文件**(`AGENTS.md` / 个人本地 `.local`),按 `od-dev-writing-agent-instructions` skill 处理。

## 13.Skills

开发类 skill(`od-dev-*`)全在公共仓 **OneDragon-Skills**(索引见该仓 `skills/README.md`);写 / 改 skill 按该仓 `AGENTS.md` + `od-dev-writing-skills`(4 硬规范 / writing-craft / testing)。

- **挂载**:junction 公共仓 `skills/<name>` → 所用工具读 skill 的目录(本地建、不入库;DSH: `.dsh/skills/`、Claude Code: `.claude/skills/`)。
- **SR 专属 skill**(星铁独有、跨项目不成立的)才进本仓 `skills/<name>/`(`sr-od-` 前缀,提交),同样 junction 挂载。