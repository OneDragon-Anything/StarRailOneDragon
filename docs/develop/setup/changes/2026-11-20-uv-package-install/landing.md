# uv 包安装化（消灭 PYTHONPATH 依赖）落地

## 影响面申报（线级一份，设计定稿时冻结）

### 代码文档面

- pyproject.toml（build-system 新增 + package 翻转 + 注释措辞）
- uv.lock（机器重生成）
- debug.bat（三块分别清理，式样见 design §2.2-③）
- tools/mcp/start_mcp_server.ps1（注释与注入清理）
- .github/workflows/build-release.yml（uv export 加 `--no-emit-project` + requirements.txt 追加 `setuptools>=64` 一行）
- .github/workflows/test-check.yml（新增 import 探针步骤）
- AGENTS.md（§1.2）
- AGENTS.local.md（§2.3，本机文件不入 git）
- docs/develop/setup/quickstart.md
- docs/develop/setup/ai_coding.md
- docs/develop/sr_od/backend/entry.md
- docs/develop/one_dragon/common-package-sync.md
- .github/dev.md
- skills/sr-od-dev-character-data/SKILL.md
- skills/sr-od-dev-character-data/scripts/generate_ascension_const.py
- skills/sr-od-dev-currency-war/references/sim-testing.md
- skills/sr-od-dev-currency-war/references/telemetry-reading.md
- skills/sr-od-dev-currency-war/references/match-review.md
- skills/sr-od-dev-currency-war/scripts/（repair_invest_attribution.py、win_model_m1.py、win_model_build_table.py、replay_to_md.py、calibration/calib_vuh_v1.py 的用法/重跑说明）
- skills/sr-od-dev-currency-war/scripts/proofs/（4 文件 5 处脚本头重跑指引注释）
- src/sr_od/application/currency_war/telemetry/cw_match_recorder.py:17（docstring）
- src/sr_od/gui/interface/devtools/mcp_service_interface.py:106（docstring）
- tools/mcp/daemon/sr_od_daemon.py（注释口径）

### 共享资产面

- uv.lock：协作者共享锁文件，本迭代必然改动（design §2.1），同批提交

### 共享资源面

- 实机：无（GUI/MCP/打包冒烟均不需游戏在线）
- 重启 MCP server：阶段 3.1 判据含 server 裸起验证（临时端口冒烟，不动常驻 24001 实例则无需重启它；若撞占用按 AGENTS.local.md §2.3「项目 MCP server 运维」节处置）；阶段 3.2 改 start_mcp_server.ps1 后用该脚本重启一次冒烟（脚本链改动常规验证）；末阶段 daemon.py / mcp_service_interface.py 仅注释与 docstring 改动、无行为差异，不重启常驻 server

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动的 `.py` 文件全部通过；
- 本阶段直接受影响测试全量一次通过（阶段 3.1 为 pytest 全量 `-m "not slow"`，其余阶段为受影响文件相关子集）；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 核心构建改动与运行冒烟

**范围**：pyproject.toml 加 `[build-system]`（setuptools>=64）+ `package = true`；`uv lock` + `uv sync --group dev`；四项运行冒烟（import / GUI / MCP 裸起 / pytest 全量）。边界——不动任何 `.py` 代码、不动 debug.bat 与 ps1、不动 CI 与用户端调用点（归 3.2/3.3/末阶段）。
**设计依据**：design.md §2.1、§2.2-②
**文件面**：pyproject.toml、uv.lock
**依赖**：无
**优先级建议**：10
**完成判据**：
- 去污前置：冒烟前 `Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue`（PowerShell）或 `unset PYTHONPATH`（Git Bash），并 `echo` 确认为空（防 debug.bat setx / 旧 quickstart 的用户级残留造成假阴性）；
- 去污后 shell 中 `uv run python -c "import sr_od, one_dragon, one_dragon_qt, onnxocr"` 成功（design §2.2-②-1）；
- 去污后 shell 中 `uv run python src/sr_od/gui/sr_full_app.py` GUI 进程启动且日志无 traceback（design §2.2-②-2）；
- 去污后 shell 中 `uv run python -m sr_od.backend.entry.server --port 24999 --mode dev` 启动，日志尾部出现「Uvicorn running」（design §2.2-②-3；用后即停，确认常驻 24001 server 未受影响）；
- `uv run pytest sr-od-test/ -m "not slow"` 退出码 0（design §2.2-②-4）；
- uv.lock 含本项目自身条目、不含 setuptools 条目（design §2.1 实测口径）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：命令 + 退出码 / 日志尾部行

## 3.2 打包链冒烟与启动脚本清理

**范围**：构建 `OneDragon-Installer.spec` 与 `OneDragon-Launcher.spec` 各一次（CI 实构同款，命令形态按 build-release.yml:115-121 的 Activate + `pyinstaller <spec>`）；debug.bat 三块清理（式样按 design §2.2-③ debug.bat 行逐块处置）；start_mcp_server.ps1 注入与注释清理。边界——不改 spec 本体、不跑 build_full.bat 全量、不动 RuntimeLauncher.spec。
**设计依据**：design.md §2.2-②-5、§2.2-③ debug.bat 与 ps1 行
**文件面**：debug.bat、tools/mcp/start_mcp_server.ps1、deploy 下 PyInstaller 构建产物目录（gitignore 内，不入库）
**依赖**：3.1
**优先级建议**：8
**完成判据**：
- Installer 与 Launcher 两个 spec 构建成功且产出 exe（design §2.2-②-5；构建于去污后 shell，验证可编辑安装下的 modulegraph 解析）；
- debug.bat 逐块对照 design §2.2-③：CONFIG 块无 PYTHONPATH set/setx/校验行、APPATH 为 `%~dp0src\%MAINPATH%` 式样、APPATH 校验保留且 WARN 文案为「APPATH 设置错误」；REINSTALL 块无 PYTHONPATH/APPATH 行与校验（保留 PYTHON/UV）；DEBUG 块无 PYTHONPATH set/echo/校验行、APPATH 为推导式样、WARN 文案为「APPATH 设置错误」；`setx "PYTHON"` 保留；
- start_mcp_server.ps1：无 `PYTHONPATH` 注入行，注释不再表述「package=false 依赖」；改后用该脚本重启 MCP server 冒烟可起；
- 完成前常规检查（本文首节；本阶段无 .py 改动则 ruff 项不适用）。
**验收凭据形式**：构建日志 / 脚本 diff 对照 / server 日志尾部行

## 3.3 CI 环境包与探针适配

**范围**：build-release.yml 的 wheels 打包步骤——`uv export` 加 `--no-emit-project`，并在输出重定向后向 deploy/dist/requirements.txt 追加一行 `setuptools>=64`；test-check.yml 加 import 探针步骤；用分发的 `.install/uv` 版本复验 design §2.2-④-2 行为基线（离线 + find-links 供给 setuptools 装 editable 成功）。边界——用户端代码（python_service / python_launcher）**零改动**（design §2.2-④-2 丙案），不迁移 locale-po.yml（其前缀是功能依赖，design §2.2-①）。
**设计依据**：design.md §2.2-④-1/2/3、§2.3-6/7
**文件面**：.github/workflows/build-release.yml、.github/workflows/test-check.yml
**依赖**：3.1
**优先级建议**：9
**完成判据**：
- `grep -n "uv export"` 确认 build-release.yml:131 命令含 `--no-emit-project`，且紧随其后存在向 requirements.txt 追加 `setuptools>=64` 的步骤（追加须满足 pyproject build-system.requires 版本约束）；
- workflow 若支持手动触发（workflow_dispatch），触发一次并核对 requirements.txt 产物无 `-e` 条目且含 setuptools 行、wheels 产物含 setuptools wheel；不支持则将「下次 release 观察该项」记入 `.debug/temp/TODO.md`（AGENTS.local.md §2.1 本地待办）；
- test-check.yml 探针步骤存在且形如 `uv run python -c "import sr_od, one_dragon, one_dragon_qt, onnxocr"`；
- 分发版 uv 复验：uv 二进制取 `.install/uv/uv.exe`（本机无该目录时先跑 `env.bat` 或 GUI 环境安装生成），复现环境三要素 = 临时目录建 src-layout 最小项目（式样按 design §2.1）+ `UV_CACHE_DIR` 指空临时目录 + wheels 目录放 setuptools wheel（`pip download setuptools --dest <wheels>`），设 `UV_OFFLINE=1` 后 `uv sync --frozen --find-links <wheels>` 复现「装上根项目」成功——与 design §2.2-④-2 行为基线同口径；禁动本仓 venv 状态后不恢复；
- 完成前常规检查（本文首节；本阶段无 src .py 改动，ruff 项不适用）。
**验收凭据形式**：grep 对照 / 命令退出码 / CI 运行记录

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本文档与注释口径；产出 ZZZ 同步件（`.debug/temp/zzz/2026-11-20-uv-package-install.md`，按 AGENTS.local.md §2.2「SR→ZZZ 同步」模板：背景/ZZZ 同步点/修法/完成判据四节）与 skill 反馈件（`.debug/temp/skill_feedback.md` 追加，框架级经验）。边界——不追改 `docs/**/changes/` 历史过程件。
**设计依据**：design.md §2.2-③、§2.3-3/4/5；AGENTS.local.md §1/§2.2
**文件面**：正本更新清单所列全部文件 + `.debug/temp/zzz/` 新同步件 + `.debug/temp/skill_feedback.md`
**依赖**：3.1、3.2、3.3
**优先级建议**：0
**完成判据**：正本更新清单清零；③ 层清单文件内 `grep -n PYTHONPATH` 残留为 0 或仅剩合法保留项（三类：locale-po.yml 功能前缀、① 层保留注入点的必要引用、quickstart 存量清理提示句与 pyproject 历史注释类警示内容）；quickstart 含目录移动后重跑 `uv sync` 的处置说明、存量用户级 PYTHONPATH 清理提示、`uv build` 非可编辑边界警示（design §2.3-3/4/5）；同步件与反馈件存在且按模板成形
**验收凭据形式**：文档对照 review / grep 收口记录

## 正本更新清单

归类规则：实体行为改动归落地阶段（3.2/3.3），本清单只收纯文档与注释口径项。

- docs/develop/setup/quickstart.md：环境设置段重写（含目录移动处置 + 存量 PYTHONPATH 清理 + uv build 边界警示） ← 3.1
- docs/develop/setup/ai_coding.md：MCP 启动命令（:27） ← 3.1
- docs/develop/sr_od/backend/entry.md：注入要求说明（:27） ← 3.1
- AGENTS.md §1.2：常用命令 PYTHONPATH 说明 ← 3.1（改 AI 入口文件按 od-dev-writing-agent-instructions skill 处理）
- docs/develop/one_dragon/common-package-sync.md：启动验证命令（:41） ← 3.1
- .github/dev.md：运行命令（:7） ← 3.1
- skills/sr-od-dev-character-data/SKILL.md：运行方式说明（:19/:33） ← 3.1
- skills/sr-od-dev-character-data/scripts/generate_ascension_const.py：用法 docstring（:6） ← 3.1
- skills/sr-od-dev-currency-war/references/sim-testing.md：运行说明与命令（:65/:68） ← 3.1
- skills/sr-od-dev-currency-war/references/telemetry-reading.md：CLI 命令与「必须带前缀」说法（:8/:11/:15） ← 3.1
- skills/sr-od-dev-currency-war/references/match-review.md：渲染器运行说明（:4） ← 3.1
- skills/sr-od-dev-currency-war/scripts/：repair_invest_attribution.py:44、win_model_m1.py:10、win_model_build_table.py:9、replay_to_md.py:11/:37、calibration/calib_vuh_v1.py:23 用法/重跑说明 ← 3.1
- skills/sr-od-dev-currency-war/scripts/proofs/：4 文件 5 处脚本头重跑指引注释 ← 3.1
- src/sr_od/application/currency_war/telemetry/cw_match_recorder.py：docstring 用法（:17） ← 3.1
- src/sr_od/gui/interface/devtools/mcp_service_interface.py：docstring 口径（:106） ← 3.1
- tools/mcp/daemon/sr_od_daemon.py：注释口径（:188-205，注入保留） ← 3.1
- pyproject.toml pyright/pytest 段注释措辞 ← 3.1
- AGENTS.local.md §2.3（本机不入 git）：启动命令注入说明 ← 3.1
