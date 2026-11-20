# 核三·治本核验攻击报告

> 审查对象：design.md / landing.md（2026-11-20-uv-package-install）。
> 审查员只读核实现状 + 查官方文档佐证技术行为主张；未改动任何仓库源码。
> 外部佐证：uv 官方文档（docs.astral.sh/uv，concepts/projects/config、concepts/projects/commands、reference/cli#uv-run）、setuptools 官方文档（package discovery）；本机 uv 0.10.4 与 design 引用版本一致。

## 发现清单

### [阻断] A1 用户端运行链（uv sync / uv run 的全部调用点）被 package=true 直接波及，design 影响面缺失整个用户端象限

- 位置：design.md §2.2（分层缺失「用户端运行链」层）、§1「明确不解决」清单
- 证据：
  - `src/one_dragon/envs/python_service.py` 四处 uv 调用全部作用于**用户安装目录**：`:136` 安装流程 `uv sync --find-links <Environment.zip 解压目录> --default-index <镜像源>`；`:161-162` 环境自检 `uv sync --frozen --inexact --check`；`:190` 按需同步（同步后恢复原 uv.lock 字节）；`:225` `uv sync --check`。
  - `src/one_dragon/devtools/python_launcher.py:157` 用户端主程序启动链 `uv run --frozen -m <app>`。
  - uv 官方文档（reference/cli#uv-run）：uv run 默认创建并同步环境，`--frozen` 只跳过 lockfile 更新、**不跳过环境同步**；`--check` 会把「项目未按 lock 安装」判为不同步。即 package=true 后：用户端每次 install/自检/run 都会要求本项目 editable 就绪 → 需要**构建**（build isolation 拉 setuptools）。
  - 离线自足被打破：Environment.zip = build-release.yml:131 `uv export --no-hashes --no-dev` + `pip wheel` 产物，setuptools 是构建后端、不在运行依赖导出面 → wheels 目录无 setuptools → 用户端构建本项目必须联网到镜像源。现状（package=false）用户端 sync 只装第三方 wheels，Full-Environment 包离线自足。
  - 存量用户升级路径：老用户 venv 无 editable → 升级后 `uv sync --check` 立即判不同步 → 触发 `uv_sync_runtime_dependencies` 在用户机器上构建 → 新增失败面（离线/杀软/构建环境）。
- 建议：design 增设「用户端运行链」影响层，二选一写明并列入 landing 阶段：
  1. （推荐）用户侧调用点显式规避——python_service.py 四处 uv sync 与 python_launcher.py 的 run_args 加 `--no-install-project`（uv 官方支持该 flag），用户端发布形态维持现有 `PYTHONPATH=src` 注入机制（python_launcher.py:113 已存在且必须保留）；
  2. 或把「用户端构建可成功」纳入 3.1/3.2 验证（本地模拟 install 流程实测），并同步更新发布文档的离线承诺口径。

### [阻断] A2 CI `uv export` 默认把项目自身 emit 进 requirements.txt，Environment.zip 将含指向 CI 路径的 editable 包——「CI 无行为变化」断言不成立

- 位置：design.md §2.1 末条（「两处 CI 均用 uv sync（非 --frozen）……CI 无行为变化」）；build-release.yml:131-132
- 证据：uv 官方文档（concepts/projects/commands）原文："By default, the current project is included in the exported requirements file with all of its dependencies."。现状 package=false 时项目不进 lock、export 不含项目，CI 正常；翻转后 `uv export --no-hashes --no-dev` 输出项目 editable 条目（`-e file://...` 形式，参见 uv issue #6995、#20238 的同类报告）→ 同一步骤的 `pip wheel -r requirements.txt` 会在 CI 上构建该 editable 条目并把产物 wheel 放进 deploy/dist/wheels → 随 StarRail-OneDragon-Environment.zip 分发给用户——editable 指针指向 GitHub runner 的临时绝对路径，用户侧安装即得悬空指针包。
- 建议：build-release.yml 的 uv export 加 `--no-emit-project`；build-release.yml 纳入 landing.md 影响面申报（当前 landing 代码文档面只列了 locale-po.yml 一个 workflow）。

### [应修] F1 locale-po.yml 不经 uv（setup-python + pip install polib），删 PYTHONPATH 前缀会直接弄坏该 CI

- 位置：design.md §2.2-③ 表（`.github/workflows/locale-po.yml:36`「PYTHONPATH 前缀」）；landing.md 正本更新清单同项
- 证据：`.github/workflows/locale-po.yml:23-36` 全文核实：`actions/setup-python@v4` + `pip install polib==1.2.0`，无 uv、无 venv、无任何可编辑安装。该 workflow 里 `PYTHONPATH=$(pwd)/src` 是模块解析的**必要手段**而非过时口径——删掉后 `python src/one_dragon/devtools/compile_po.py` 立即 `ModuleNotFoundError`，mo 编译提交链断。
- 建议：design 显式二选一：① 保留该行并加注释（无 uv 工作流的必要手段，不属本迭代清理面）；② 将该 workflow 改造为 uv sync 形态（属实质改动，须列入 landing 文件面与完成判据）。现方案按「口径同步」直接删除不可行。

### [应修] F2 冒烟矩阵与 CI 实际构建的 spec 集合不对齐；editable 引入改变全部三个 spec 的模块解析路径

- 位置：design.md §2.2-②-5、§2.3-5；landing.md §3.2
- 证据：
  - build-release.yml:115-121：CI 实际构建的是 `OneDragon-Installer.spec` 与 `OneDragon-Launcher.spec`（此二 spec **无** sys.path.insert、无 runtime hook；入口 `sr_installer_app.py` / `sr_launcher.py` 顶层硬导入 `one_dragon_qt` / `one_dragon`）。design 与 landing 只冒烟 `OneDragon-RuntimeLauncher.spec`（唯一自带 sys.path.insert 的 spec）。
  - 本地实测：干净 shell（去 PYTHONPATH）下 `.venv/Scripts/python -c "import one_dragon"` → `ModuleNotFoundError`（package=false 现状，即 CI 等价环境的 venv 解析能力）；而本地既有构建产物 `deploy/build/OneDragon-Launcher/Analysis-00.toc` 显示 66 个 one_dragon 模块全部从 `D:\...\StarRailOneDragon\src` 解析（本地 shell 带 PYTHONPATH）。venv 获得可编辑安装后，这两个 spec 构建时的 modulegraph 解析来源随之改变，bundle 内容（模块集、体积）可能变化。
- 建议：3.2 冒烟补 Installer/Launcher 两个 spec 的构建（或至少 pyinstaller dry-run Analysis 对比模块清单），验证 bundle 与现状等价；无法等价时在 design 写明差异与接受理由。

### [应修] F3 兜底清单不完整：mcp_service_interface.py 注入漏入口径同步层，用户端机制与 docstring 口径未显式声明

- 位置：design.md §1 五类兜底清单、§2.2-③ 表
- 证据（grep 全仓核实）：
  - `src/sr_od/gui/interface/devtools/mcp_service_interface.py:106-112`：GUI「MCP 服务」界面拉起 server 子进程时显式注入绝对路径 PYTHONPATH，注释原文「src-layout + package=false」——与清单第 5 类（daemon 注入）同族同场景，但既不在 §1 清单也不在 ③ 处置表（包安装化后该注释口径同样变错）。
  - `src/one_dragon/devtools/python_launcher.py:113,140-143`：用户端运行链设置 PYTHONPATH 并以其做路径校验——属「发布形态无安装」的另一根，应在「明确不解决」中显式声明而非缺席（且与 A1 处置联动）。
  - `src/sr_od/application/currency_war/telemetry/cw_match_recorder.py:17`：docstring 用法带「PYTHONPATH=src」口径，与已列入 ③ 的 skill references 同类，漏列。
- 建议：三处补入清单并分层处置（mcp_service_interface 入 ③；python_launcher 入「明确不解决 + 用户端层」；cw_match_recorder docstring 随 ③ 一行）。

### [存疑] Q1 CI 现状构建 Launcher/Installer 时 one_dragon 的解析机制未确证

- 位置：design.md §2.3-5（仅认 PyInstaller 并存为唯一重验证点）
- 证据：按可查证据推演（CI 无 PYTHONPATH 环境变量、spec 无 insert、venv 无项目包），modulegraph 应解析不到 one_dragon；但 release 产物在用，说明存在本审查未能定位的机制（PyInstaller 某版本行为或 runner 环境因素）。未找到权威依据闭环。
- 建议：实现前在 CI（或洁净机复现 CI 步骤）跑一次现状构建观察解析日志；A2/F2 处置后本项随闭。

### [存疑] Q2 uv build isolation 是否消费 `--find-links`（离线 wheels 能否喂构建依赖）未见文档明文

- 位置：与 A1 相关（用户端 install 流程）
- 证据：python_service.py 安装链带 `--find-links <wheels 目录>`；setuptools 属 build isolation 依赖，通常走 index 解析，`--find-links` 是否同时用于构建依赖未查到官方说明。
- 建议：A1 若走 `--no-install-project` 路线则本项自然消解；若走「验证用户端可构建」路线，此项必须实测后写进 design 边界。

### [低级] L1 design §2.4「当前版本会假定 setuptools 并告警」与现行官方文档不符

- 位置：design.md §2.4 第 2 条
- 证据：uv 官方文档（concepts/projects/config#build-and-package-options）：有 `[project]` 无 `[build-system]` 时项目视为 virtual、**不构建不安装**（"If a build system is not defined, uv will not attempt to build or install the project itself, just its dependencies."）；「无 build-system 时用 setuptools legacy backend」仅在 `package = true` 且未定义 build-system 的组合下成立，且文档未提及告警。结论方向（选显式声明）不受影响。
- 建议：措辞改为「uv 以 build-system 存在性判定项目是否安装；显式声明消除判定歧义」。

### [低级] L2 存量 setx PYTHONPATH 残留无清理动作

- 位置：design.md §2.3（风险清单）、landing.md §3.2
- 证据：debug.bat:55 的 `setx` 已长期污染用户级环境变量；landing 只删脚本行，已污染机器的用户级 PYTHONPATH 仍在——sys.path 中 PYTHONPATH 位于 site-packages 之前，会持续遮蔽可编辑安装；本机 SR/ZZZ 双仓并存场景下若指向另一仓 src 则跨仓串包。
- 建议：quickstart 重写段补一句「曾用 debug.bat 配置过的机器请删除用户级 PYTHONPATH 变量」（或 debug.bat 菜单加一次性 unset 项，归 3.2）。

## 根源两问独立结论

**归层成立，无需更深归层。** 「src-layout 或单仓四包结构迫使 package=false」的更深根不成立：setuptools 官方文档明确 src-layout 自动发现扫描整个 `src/`、支持多顶级包（拒多包的是 flat-layout），四包 `__init__.py` 已逐一核实存在，「零额外包清单配置」主张有官方依据。「跨项目共享 one_dragon 与包安装冲突」的担心也不成立：common-package-sync.md 的同步是 src/ 文件级复制（rm -rf + cp -r），可编辑安装是指向 src/ 的查找指针、不复制文件——同步后改动即时生效、无需重装；各仓 venv 指向各自 src/，指针不参与版本化，不存在同源复制漂移。反倒是包安装化 + 清除用户级 PYTHONPATH（含 L2 残留清理）对双仓卫生是净改善。design 未点破但真实存在的一层是：资源定位（config/、assets/ 按项目根、`__file__` 推根）决定项目只能以源码树形态运行、永不能真安装——这是「为何止步于可编辑」的边界而非根因，design §2.3-4 已识别为边界。「约定层」归层成立。

**主措施是修根，保留兜底可接受，但治本完备性有两个实质缺口。** package=true + 可编辑安装直击约定层根因、消灭「忘设环境变量」失败形态，是架构级处理而非同族补丁（跨件半问成立）。保留兜底的遮蔽风险经测量有限：凡经 uv 的链（CI、MCP 脚本、daemon），uv run/sync 失败会前置报错、不会被 pytest pythonpath 掩盖；遮蔽只发生在「裸 python 直跑 pytest/LSP」——恰是兜底的目标场景。建议补一个轻量环境探针（test-check.yml 加一步 `uv run python -c "import sr_od, ..."`）让「包没装上」在 CI 主链可见。但 package=true 是 pyproject 属性、广播到**所有** uv sync/uv run 调用点：用户端运行链（A1）与 CI export（A2）两个象限设计未覆盖——不处置即被动接受用户端构建依赖联网与发布包污染，治本完备性不成立；把这两象限纳入处置（`--no-install-project` / `--no-emit-project`）或显式验证接受后，方可称完整治本。
