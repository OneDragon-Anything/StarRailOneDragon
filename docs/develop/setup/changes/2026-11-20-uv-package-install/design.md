# uv 包安装化（消灭 PYTHONPATH 依赖）迭代设计（总纲）

## 0. 元信息

- 迭代目标：用户裁定（2026-11-20 会话）——去掉 `pyproject.toml` 的 `[tool.uv] package = false`，让项目由 uv 以包形式管理安装，消灭「每次运行前设置 `PYTHONPATH=src`」的隐性失败与散落各处的兜底。
- 状态：定稿（四轮对抗收敛：三轮 6 条发现全部闭合、四轮零新增阻断/应修；用户端丙案经用户 2026-11-20 裁定）
- 文档清单：无详设（单文档方案，§2 即完整设计）

## 1. 问题与动机

- 现状症状：`pyproject.toml` 设 `[tool.uv] package = false`（pyproject.toml:48），uv 不把本项目装进 `.venv`，`import sr_od` 等顶级包全靠外部手段把 `src` 加入模块搜索路径。由此同一根因散出七类兜底：
  1. 环境变量：开发者每会话设 `PYTHONPATH=src`（AGENTS.md §1.2）；`debug.bat:55` 甚至用 `setx` 永久污染用户级环境变量；
  2. pytest 配置：`[tool.pytest.ini_options] pythonpath = ["src"]`（pyproject.toml:136）；
  3. pyright 配置：`[tool.pyright] extraPaths = ["src"]`（pyproject.toml:105）；
  4. 打包链自插：`deploy/hook_path_inject.py:17`、`deploy/OneDragon-RuntimeLauncher.spec:18` 手动 `sys.path.insert`；
  5. 开发侧 MCP 启动链注入：`tools/mcp/start_mcp_server.ps1:113`、`tools/mcp/daemon/sr_od_daemon.py:192`、`src/sr_od/gui/interface/devtools/mcp_service_interface.py:112`（GUI「MCP 服务」界面拉起 server 同族注入）；
  6. 用户端发布链注入：`src/one_dragon/devtools/python_launcher.py:113` 运行时设 `PYTHONPATH=<安装目录>/src`（用户机器以源码树形态运行，此注入是发布形态的必要机制而非补丁，本迭代**保留不动**，见「明确不解决」）；
  7. skills 脚本 sys.path 自插族：`skills/*/scripts/` 下约 14 处脚本自行 `sys.path.insert` 定位 src（不经 uv 直跑脚本的兜底，幂等无害，保留）。
  忘设环境变量的失败形态 = `-m` 启动秒退 `ModuleNotFoundError`（AGENTS.local.md §2.3「项目 MCP server 运维」节记载的实测事故），对协作者与 AI 会话是持续摩擦。
- 根因归层（约定层）：项目的构建形态约定为「不安装、纯源码目录」，迫使每个消费场景各自解决导入路径。七类兜底是同一根的症状（跨件半问成立：同族第 2 件起即应升架构级处理，本迭代即该架构级处理）。
- 解决到哪：**开发与 CI 环境**由 uv 把本项目以**可编辑安装**（editable install：在 `.venv` 登记一个指向 `src/` 的查找指针，import 时直接读源码树文件而非复制副本，源码改动即时生效）方式纳入环境管理。此后任何 `uv run` 下的 import 不再需要环境变量；uv 在 pyproject 变化后自动保持安装最新（uv 0.10.4 文档行为，阶段 3.1 实测复核）。
- 明确不解决：
  - **用户端发布链代码零改动**：终端用户机器（Launcher 分发安装）维持 `PYTHONPATH` 注入机制（python_launcher.py:113），python_service / python_launcher 不做任何修改；用户机由环境包补 setuptools 供给安装本项目（§2.2-④-2 丙案），隐式可离线能力保留；
  - 不改 PyInstaller 打包方式本身（spec 继续自插 `SRC_DIR` 作兜底，仅验证与可编辑安装并存不冲突）；
  - 不拆分 `one_dragon` / `one_dragon_qt` / `onnxocr` / `sr_od` 为独立分发包（单 project 多顶级包形态维持）；
  - 不追改 `docs/**/changes/` 历史过程件中的旧口径（迭代区铁律）；
  - 不落地 ZZZ 仓（绝区零一条龙仓，本机姊妹项目 ZenlessZoneZero-OneDragon）的同类改动——只按 AGENTS.local.md §2.2（SR→ZZZ 同步件模板：背景/同步点/修法/完成判据四节）写同步件，由 ZZZ 侧自行处理。

## 2. 方案（单文档完整设计）

### 2.1 核心改动

`pyproject.toml` 两处：

```toml
# 新增（当前 pyproject 无 [build-system]；uv 靠它确定构建方式）
[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"

[tool.uv]
# 以下 [tool.uv] 段仅 package 行由 false 翻转为 true，其余三行系现状保留
package = true
cache-dir = "./.install/uv_cache"
environments = ["sys_platform == 'win32'"]
default-groups = []
```

- 构建后端选 **setuptools**：`src/` 下四个顶级包 `one_dragon` / `one_dragon_qt` / `onnxocr` / `sr_od` 均含 `__init__.py`（实测确认），setuptools 对 src-layout 多顶级包自动发现零额外包清单配置（依据：setuptools 官方 package discovery 文档，src-layout 扫描整个 `src/`；版本要求 `>=64` 为保守覆盖，阶段 3.1 构建实跑即验证）。
- 改后执行 `uv lock`（锁文件新增本项目条目——实测 uv.lock **不含** setuptools 构建依赖条目，构建后端仅安装时经构建隔离解析）+ `uv sync --group dev`（与 CI 口径一致，.github/workflows/test-check.yml:35、build-release.yml:98）。
- CI 兼容性：sync 类步骤（test-check.yml、build-release.yml:98）行为不变；但 build-release.yml 的 `uv export` 步骤（:131）与用户端调用点受波及，处置见 §2.2-④——**「CI 无行为变化」仅在 sync 面**成立。

### 2.2 影响面分层与处置

**① 零改动层（既有兜底保留，冗余无害）**

| 项 | 依据 | 保留理由 |
|---|---|---|
| pytest `pythonpath=["src"]` | pyproject.toml:136 | 兜「不经 uv 直用 python 跑 pytest」场景；测试 CI 依赖它而非环境变量（.github/workflows/test-check.yml:83） |
| pyright `extraPaths=["src"]` | pyproject.toml:105 | 兜不经 uv 的 LSP 场景；注释措辞随正本更新 |
| locale-po.yml 的 `PYTHONPATH=$(pwd)/src` 前缀 | .github/workflows/locale-po.yml:36 | **功能依赖非过期口径**：该 workflow 是 ubuntu + `pip install polib`（:29），无 uv、无项目安装，前缀是 `one_dragon` 导入唯一来源——与 pytest pythonpath 同判，保留不删 |
| deploy 的 `sys.path.insert` | deploy/hook_path_inject.py:17、OneDragon-RuntimeLauncher.spec:18 | 打包分析从源码树取模块，与可编辑安装互不依赖 |
| daemon 的 spawn 注入 | tools/mcp/daemon/sr_od_daemon.py:192 | 幂等兜底；注释口径更新 |
| GUI 侧 server 拉起注入 | src/sr_od/gui/interface/devtools/mcp_service_interface.py:112 | 同 daemon 族幂等兜底；docstring 口径更新 |
| 用户端发布链注入 | src/one_dragon/devtools/python_launcher.py:113 | 发布形态必要机制（用户机以源码树形态运行）；④-2 丙案下零改动保留，注入与可编辑安装指向同一 src/，语义一致 |
| skills 脚本 sys.path 自插族 | skills/*/scripts/ 约 14 处 | 不经 uv 直跑脚本的兜底，幂等无害 |
| 资源定位（config/、assets/ 按项目根） | — | 可编辑安装不改变 `__file__`（仍指向源码树真实路径），定位行为零变化 |

**② 需冒烟验证层（预期无行为差异，验证后才签字）**

1. `uv run python -c "import sr_od, one_dragon, one_dragon_qt, onnxocr"`（去污后 shell，见 landing 3.1 判据的去污前置）；
2. GUI 裸跑：`uv run python src/sr_od/gui/sr_full_app.py` 起 0 错误（口径同 docs/develop/one_dragon/common-package-sync.md 的「GUI 起来」）；
3. MCP server 裸 `-m` 启动至 `.log/mcp_server.log` 尾部「Uvicorn running」（判活标志 = AGENTS.md §6），用临时端口避撞常驻 24001；
4. pytest 全量 `-m "not slow"` 通过；
5. PyInstaller 构建 **`OneDragon-Installer.spec` + `OneDragon-Launcher.spec`** 各一次（CI 实构同款，build-release.yml:120-121；此二 spec **无** sys.path.insert 兜底，是可编辑安装改变 modulegraph 解析来源的真实验面——现状 CI 靠何种机制解析到 `one_dragon` 未确证，可编辑安装后机制明确为 venv 查找指针，属风险收敛为改善）。`OneDragon-RuntimeLauncher.spec` 自带兜底，随批构建不单独要求。

**③ 口径同步层（改后既有文案变错，必改清单）**

豁免边界：带「需/必须 PYTHONPATH」断言的用法文案入列必改；`docs/**/changes/` 历史过程件与 `docs/**/proofs/` 历史复算记录豁免；改后仍合法保留 `PYTHONPATH` 字样的**警示/历史注释类**内容豁免（quickstart 的存量清理提示句、pyproject 保留注释等——grep 收口时不算残留）。

| 文件 | 处 |
|---|---|
| AGENTS.md §1.2 | PYTHONPATH 前置说明 |
| AGENTS.local.md §2.3（本机，不入 git） | 启动命令注入说明 |
| docs/develop/setup/quickstart.md | 6 处（:48/49/59/60/91/102：IDE、命令行、GUI 启动、MCP 启动、pyright 说明） |
| docs/develop/setup/ai_coding.md | 1 处（:27） |
| docs/develop/sr_od/backend/entry.md | 1 处（:27 注入要求说明） |
| docs/develop/one_dragon/common-package-sync.md:41 | 启动验证命令前缀 |
| .github/dev.md:7 | 运行命令说明 |
| skills/sr-od-dev-character-data/SKILL.md | 2 处（:19/:33） |
| skills/sr-od-dev-character-data/scripts/generate_ascension_const.py | 1 处（:6 用法 docstring） |
| skills/sr-od-dev-currency-war/references/sim-testing.md | 2 处（:65 说明 /:68 命令） |
| skills/sr-od-dev-currency-war/references/telemetry-reading.md | 3 处（:8/:15 命令 /:11「必须带」说法） |
| skills/sr-od-dev-currency-war/references/match-review.md | 1 处（:4 说明） |
| skills/sr-od-dev-currency-war/scripts/：repair_invest_attribution.py:44、win_model_m1.py:10、win_model_build_table.py:9、replay_to_md.py:11/:37、calibration/calib_vuh_v1.py:23 | 各自的用法/重跑说明 |
| skills/sr-od-dev-currency-war/scripts/proofs/：4 文件 5 处脚本头「重跑:PYTHONPATH=src」注释 | 现行重跑指引（非历史存档），入列必改 |
| src/sr_od/application/currency_war/telemetry/cw_match_recorder.py:17 | docstring 用法「项目根,PYTHONPATH=src」 |
| tools/mcp/daemon/sr_od_daemon.py:188-205 | 注释口径（注入保留） |
| src/sr_od/gui/interface/devtools/mcp_service_interface.py:106 | docstring 口径（注入保留） |
| pyproject.toml pyright/pytest 段注释 | 「package=false」措辞 |
| tools/mcp/start_mcp_server.ps1:110-113 | 注释 + 注入清理（**实体改动，实施归 3.2**；删而 daemon/GUI 注入保留的理由：ps1 注入仅服务启动进程自身的会话环境，可编辑安装后 `uv run` 链路自足故删；daemon/GUI 注入作用于拉起的子进程、属跨进程幂等兜底故留） |
| debug.bat（实体改动，实施归 3.2） | 三块分别处置——**CONFIG_PYTHON_ENV 块**：删 `setx "PYTHONPATH"` 与 `set "PYTHONPATH"` 行，APPATH 改 `set "APPPATH=%~dp0src\%MAINPATH%"`（本块有 MAINPATH 赋值），`if not exist "%PYTHONPATH%"` 校验行删除、APPATH 校验行保留且 WARN 文案「PYTHONPATH 设置错误」改「APPATH 设置错误」；**REINSTALL_PY_LIBS 块**：删 `set "PYTHONPATH"`、`set "APPPATH"` 两行与对应两行校验（本块无 MAINPATH 赋值且不消费二者，仅用 PYTHON/UV）；**DEBUG 块**：删 `set "PYTHONPATH"`、`echo [PASS] PYTHONPATH` 行、`if not exist "%PYTHONPATH%"` 校验，APPATH 改 `set "APPPATH=%~dp0src\%MAINPATH%"`（本块有 MAINPATH 赋值 :205），APPATH 校验的 WARN 文案「PYTHONPATH 设置错误」改「APPATH 设置错误」；`setx "PYTHON"`（:54）**保留**——非导入机制（Python 解释器不读 `PYTHON` 变量），超出本迭代范围 |

**④ 调用点适配层（`package = true` 的广播面，行为改动）**

`package = true` 是项目级属性，广播到仓库内全部 `uv sync` / `uv run` 调用点。开发侧受益，以下处置：

1. **CI 离线环境包**：build-release.yml:131 `uv export --no-hashes --no-dev --format requirements-txt` 加 `--no-emit-project`——uv export 默认把当前项目以 editable 条目写进输出（uv 官方 commands 文档明文），照旧会导致后续 `pip wheel` 在 runner 上构建项目、把指向 runner 临时路径的悬空指针包打进 StarRail-OneDragon-Environment.zip 分发给用户；加 flag 后环境包不含项目自身，内容语义与现状一致（另追加 setuptools 一行，见下）。
2. **用户端运行链（丙案，已裁定）**：`package = true` 后用户机的 uv 调用点（`src/one_dragon/envs/python_service.py` 四处 sync：:136 安装 `--find-links`、:161-162 自检 `--frozen --inexact --check`、:190 按需同步、:225 `--check`；`src/one_dragon/devtools/python_launcher.py:147` `uv run --frozen`）默认会安装本项目。行为基线（编排者隔离实验实测，uv 0.10.4、临时目录 src-layout 最小项目、空 uv 缓存）：
   - 可编辑安装需要 setuptools（构建隔离解析）：联网（走镜像源）**成功装上**；空缓存 + 离线（UV_OFFLINE=1）**无 setuptools 供给时失败 exit 1**；`--find-links` 目录有 setuptools wheel 时**离线也成功构建安装**（构建隔离认 `--find-links`）；uv.lock 本身**不含** setuptools 条目（锁面不变）；
   - `uv run` **无** `--no-install-project` 选项（`uv sync` 有）；`uv sync --no-install-project` 在项目已装态会**卸载**项目——排除路线在开发机 GUI（与用户机同代码，venv_install_card.py:17/:37）不可行，已否决。
   **丙案（用户裁定）**：`src/one_dragon/envs/python_service.py`、`src/one_dragon/devtools/python_launcher.py` **零改动**；用户机离线安装能力由环境包补 setuptools 保留——build-release.yml 的 wheels 打包步骤在 `uv export --no-emit-project` 输出后向 requirements.txt 追加一行 `setuptools>=64`（满足 build-system.requires 版本约束），`pip wheel` 将其打进 StarRail-OneDragon-Environment.zip；用户机安装时 `--find-links <wheels>` 供给构建隔离（上表实测），断网也能装上项目。装机代价 = 环境包多一个 setuptools wheel（~800KB 级）。存量用户升级边界：新 lock 含项目条目、自检触发一次按需同步——联网用户走镜像自动恢复；**断网存量用户**该按需同步调用点（python_service.py:190）不传 `--find-links`、取不到本地 wheels，构建隔离无 setuptools 供给会失败并退出启动器（python_launcher.py:305-308），需一次联网或重跑安装器——与主站文档「完整包不能完全替代后续更新」口径一致；初次离线安装不受影响（:136 安装路径带 `--find-links`）。若未来要求断网升级可启动，方向是给 :190 补 `--find-links` 与 wheels 目录保障（公共框架一行级改动），本迭代不做（与「零改动」裁定前提冲突）。
3. **CI 环境探针（新增）**：test-check.yml 依赖安装步骤后加一步 `uv run python -c "import sr_od, one_dragon, one_dragon_qt, onnxocr"`——让「包没装上」类环境故障在 CI 主链显性报错，防 ① 层兜底遮蔽（pytest pythonpath 使测试在该场景照样绿）。

### 2.3 风险与边界

1. **uv.lock 变化**：新增本项目 `[[package]]` 段。与 pyproject 同批提交；分支合流期可能一次性冲突，解决方式 = 任一侧重跑 `uv lock`。用户端锁面行为随 ④-2 裁定方案处置。
2. **首次安装需联网（仅开发机与 CI）**：可编辑安装的构建隔离需拉 setuptools 进 uv 缓存（`.install/uv_cache`，项目内缓存）；开发机与 CI 有网，一次性成本。用户端初次安装由环境包补 setuptools 供给（④-2 丙案），不依赖外网；断网存量升级例外见 §2.2-④-2 升级边界。
3. **项目目录移动/改名后可编辑安装指针失效**：症状 = import 报错；处置 = 重跑 `uv sync`。现 PYTHONPATH 方案换机同样要重设，失败模式未变差，但报错更隐蔽——quickstart 补一句处置说明。
4. **存量用户级 PYTHONPATH 残留遮蔽**：历史执行过 `debug.bat` setx 或按旧 quickstart 用 `setx PYTHONPATH` 的机器，用户级 PYTHONPATH 持续排在 site-packages 之前遮蔽可编辑安装，双仓（SR/ZZZ）机器可能跨仓串包——quickstart 重写段补「曾配置过的机器请删除用户级 PYTHONPATH 变量」。
5. **未来 `uv build` 非可编辑安装的隐性边界**：真安装会把包复制进 site-packages，`__file__` 不再指向源码树，按 `__file__` 推项目根的资源定位会断——本迭代只走 `uv sync`（可编辑），此边界写进 quickstart 警示句，不设防。
6. **发布 CI 的 export/wheel 链**：④-1 处置后的真实产物需随下一次 release 构建观察（workflow 若支持手动触发则阶段 3.3 实跑一次验证 requirements.txt 不含 `-e` 条目）。
7. **用户端 uv 版本行为一致性**：④-2 实验基于本机 uv 0.10.4；随项目分发的 `.install/uv` 若为旧版本，其 editable 安装与「构建隔离认 `--find-links`」行为需同口径实测（阶段 3.3 判据含分发版 uv 实测）。

### 2.4 关键取舍

- **setuptools vs hatchling**：hatchling 需手写 `packages = ["src/one_dragon", ...]` 四项清单（新包落地要记得维护）；setuptools src-layout 自动发现零配置、团队熟悉度同栈（dev 组 pyinstaller 生态即 setuptools 系）。选 setuptools。
- **显式 `package = true` + 显式 `[build-system]` vs 删行赌默认**：uv 以 build-system 存在性判定项目是否安装（官方 projects/config 文档：无 build-system 则项目视为 virtual，不构建不安装项目本身，只装依赖）；显式声明消除判定歧义与版本行为差异。选双显式。
- **用户端：丙（环境包补 setuptools）vs 甲（条件化排除）vs 乙（接受联网）**：丙兼得零公共框架侵入与初次离线安装能力保留（构建隔离认 `--find-links`，实测离线安装成功；断网存量升级仍需联网一次，见 §2.2-④-2 升级边界），总改动量最小（CI 一行）；甲为一台机器判据塞双态逻辑进公共框架；乙无谓放弃离线安装能力。**用户裁定（2026-11-20）：丙**。
- **症状修法（已否决）**：把 `PYTHONPATH=src` 写进 `.env`——被部分工具启动环境校验拒绝（AGENTS.md §1.2 记载），且不解决七类兜底同根问题。
- **已否决**：`uv run --no-install-project`（选项不存在）；无条件全局 `--no-install-project`（开发机 GUI 卸载 editable + 自检卡红，venv_install_card.py 同代码双态运行）；setuptools 写进 `[project]` dependencies（运行时不需要它，污染运行依赖面——正确落点是环境包内容面即 export 产物追加）。
- **兜底全清 vs 保留**：全清（删 pytest pythonpath / pyright extraPaths / daemon 注入等）改动面大三倍且引入「必须走 uv」的强约束；保留兜底零风险且各兜底另有独立价值（① 层理由），配 ④-3 探针补 CI 可见性。选保留 + 探针。
