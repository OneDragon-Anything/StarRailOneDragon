# 核一·无前提攻击报告

审查对象：design.md / landing.md / README.md（2026-11-20-uv-package-install）。全部行号与现状断言逐项用 Read/Grep 核实；技术主张以 uv 0.10.4 / setuptools 官方文档查证（本机 uv 0.10.4，与设计引用版本一致）。

已核实为正确的引用（不再列入发现，结论部分计账）：pyproject.toml:48/105/136、debug.bat:55、deploy/hook_path_inject.py:17、OneDragon-RuntimeLauncher.spec:18、start_mcp_server.ps1:110-113、sr_od_daemon.py:188-205、test-check.yml:35/83、build-release.yml:98、locale-po.yml:36、common-package-sync.md:41、.github/dev.md:7、ai_coding.md 1 处（:27）、character-data SKILL.md 2 处（:19/:33）、quickstart 环境段（§4 整段，6 处提及 ≈ 「~5 处」）、AGENTS.local.md §2.2 模板与 §2.3 事故记载均存在；src/ 四顶级包均含 `__init__.py`；landing 三阶段的设计依据节号全部真实存在、文件面与 design §2.2-③ 对得上；build_full.bat:9 存在 landing 所述 spec 调用形态。

## 发现清单

### [阻断] locale-po CI 的 PYTHONPATH 前缀是功能依赖，按 landing 指令删除会直接弄坏该 CI
- 位置：design.md §2.2-③（locale-po.yml 行）/ landing.md 正本更新清单
- 证据：`.github/workflows/locale-po.yml` 运行于 ubuntu-latest，依赖安装仅 `pip install polib==1.2.0`（:29），无 uv、无 venv 同步、无项目安装；编译步骤 `PYTHONPATH=$(pwd)/src python src/one_dragon/devtools/compile_po.py`（:36）中前缀是 `one_dragon` 导入的唯一来源。landing 明确指示「PYTHONPATH 前缀删除」——照做后该 CI 在下一次 `*.po` 变更推送时 ModuleNotFoundError。design 把它归入「改后既有文案变错」的口径层是归类错误：该前缀不是过期口径，而是 design §2.2-① 自己为 pytest pythonpath 辩护的同类「不经 uv 直用 python」场景的功能兜底——① 的保留逻辑与 ③/landing 的删除指令自相矛盾。
- 建议：把 locale-po.yml 移出 ③（保留前缀），或改判据为「该 workflow 迁移到 uv sync + uv run 后删前缀」——二选一须在 design 定稿前裁定，不能按现文执行。

### [应修] build-release 的 `uv export` + `pip wheel` 离线环境包链路行为改变，design「CI 无行为变化」主张不成立
- 位置：design.md §2.1（「锁文件随 pyproject 同批提交后 CI 无行为变化」）
- 证据：`.github/workflows/build-release.yml:131-132`：`uv export --no-hashes --no-dev --format requirements-txt > deploy/dist/requirements.txt` 后 `pip wheel --wheel-dir=deploy/dist/wheels -r ...`。uv 官方 CLI 文档：`uv export` 默认包含当前项目自身（以 `-e .` 形式），排除需显式 `--no-emit-project`。当前 package=false 时项目不可安装、导出不含项目；翻转后 requirements.txt 将新增 `-e .` 行——pip wheel 会对项目自身构建 wheel（或直接失败），StarRail-OneDragon-Environment.zip（终端用户离线依赖包，:135）内容与构建行为改变。该步骤完全未进 design 影响面（build-release.yml 仅以 :98 的 uv sync 口径被引用）。
- 建议：design 增补处置：`uv export` 加 `--no-emit-project`（保持环境包语义不变），或分析项目 wheel 入包后的离线安装行为并写入 §2.3；同时撤回或收窄「CI 无行为变化」的表述。

### [应修] 发布/终端用户启动链整体未入影响面：Launcher 运行时 PYTHONPATH 注入 + 用户机 uv sync 将新增「构建本项目」环节
- 位置：design.md §1（五类兜底枚举）/ §2.2（分层处置）/ §2.3-2（联网成本仅按「本机与 CI」分析）
- 证据：发布的 OneDragon-Launcher.exe 入口 `src/sr_od/gui/sr_launcher.py:13,16` 调 `one_dragon.devtools.python_launcher.run_python`，链路为：`configure_environment`（python_launcher.py:112-123 运行时注入 PYTHONPATH、未设即 `sys.exit(1)`；:140-144 用 PYTHONPATH 派生 APPPATH）→ `sync_dependencies`（src/one_dragon/envs/python_service.py:171-206，用户机执行 `uv sync --inexact --default-index <镜像>`）→ `execute_python_script`（python_launcher.py:147 `uv run --frozen`）。uv 官方 sync 文档：项目定义 build-system 后 `uv sync` 会以可编辑方式安装项目——即翻转后**终端用户每次环境同步新增构建本项目的环节**（构建隔离需拉 setuptools）；Full-Environment 离线包用户（build-release.yml:317 打包、安装后离线装 wheels）能否完成该构建未分析。这是第六类兜底 + 行为变更，design §1/§2.2/§2.3 均未提及。
- 建议：design 定稿前对该链表态：a) 影响面分层补 python_launcher.py 行（归 ① 保留 + ③ 口径，或说明处置）；b) §2.3-2 补「终端用户首次 sync 需联网拉 setuptools（镜像可用性）/离线包路径」的分析与验证项（或明确划出边界并说明理由）。

### [应修] §2.2 ①/③ 漏列 src 内 GUI 侧 MCP 注入：注释「package=false」改后变错
- 位置：design.md §2.2-① 表 / §2.2-③ 表
- 证据：`src/sr_od/gui/interface/devtools/mcp_service_interface.py:105-113`：`_server_spawn_env` 注入 `env['PYTHONPATH'] = str(root / 'src')`，docstring 明写「src-layout + package=false，显式注入绝对路径 PYTHONPATH」。daemon 的同类注入被列入 ①（保留）+ ③（注释口径更新），此 GUI 侧文件在两表中均缺席——按 ③ 自身判据（「改后既有文案变错，必改清单」）应入列。
- 建议：③ 表补 mcp_service_interface.py 行（注释口径更新，注入按 ① 逻辑保留）。

### [应修] ③ 清单按自身判据漏列多处「需 PYTHONPATH=src」类文案（skill scripts 与 src docstring 与正本 doc）
- 位置：design.md §2.2-③ 表
- 证据（均已 grep 逐条核实）：`docs/develop/sr_od/backend/entry.md:27`（「`PYTHONPATH=<项目>/src` 注入要求…src-layout 的解析要求」——正本文档，非 changes/）；`src/sr_od/application/currency_war/telemetry/cw_match_recorder.py:17`（docstring「用法(项目根,PYTHONPATH=src)」）；`skills/sr-od-dev-character-data/scripts/generate_ascension_const.py:6`（「用法:PYTHONPATH=src 下…」——同 skill 的 SKILL.md 两处已列入而脚本漏列）；`skills/sr-od-dev-currency-war/scripts/` 多文件（repair_invest_attribution.py:44、win_model_m1.py:10、win_model_build_table.py:9、replay_to_md.py:11/:37、calibration/calib_vuh_v1.py:23、proofs/ 若干「重跑:PYTHONPATH=src」）。这些与已列入的 references/*.md「必须带前缀」说法同类同判；proofs/ 历史声明（「某日跑通」的记录）可另立边界豁免，但 design 未划这条边界。
- 建议：③ 清单补列或明示豁免边界（建议：带「需/必须」断言的用法文案入列，历史重跑记录豁免）；正本更新清单同步。

### [应修] 「干净 shell」冒烟判据不可自证：未给去污手段，存在已知的用户级污染途径，冒烟可空转通过
- 位置：design.md §2.2-②-1/2/3 / landing.md 3.1 完成判据
- 证据：判据写「干净 shell（无 PYTHONPATH 环境变量）」但两文均未给达成方式；而本迭代自身记录了用户级污染途径——debug.bat:55 `setx PYTHONPATH` 与 quickstart.md:49 曾向用户推荐 `setx PYTHONPATH "src"`。在执行过 setx 的机器上，新开 Git Bash/PowerShell 天然带绝对路径 PYTHONPATH 指向本仓 src——即使可编辑安装缺失/损坏，import 冒烟照样通过（假阴性），判据失去鉴别力。（审查机当前环境 PYTHONPATH 为空，本机可执行，但判据文本不自保护。）
- 建议：判据补一步显式去污：PowerShell `Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue`，Git Bash `unset PYTHONPATH`，并要求先 `echo $env:PYTHONPATH` 确认为空再跑冒烟。

### [存疑] design §2.4 对「无 build-system 时 uv 行为」的表述与当前 uv 文档不符
- 位置：design.md §2.4（「uv 对『有 [project] 无 [build-system]』的行为随版本演化（当前版本会假定 setuptools 并告警）」）
- 证据：uv 官方 projects/config 文档：`[project]` 存在而无 `[build-system]` 时 uv「不会尝试构建或安装项目本身，只装依赖」，未提及告警；「假定 setuptools legacy 后端」的规则适用于依赖包及显式 `package = true` 场景。sync 文档同样明示「项目未定义 build system 则不会被安装」。设计选择的落点（显式 build-system + package=true）方向正确且不受影响，但支撑表述按文档应修正。另：「src-layout 自动发现需 setuptools>=61」的版本号未能在 setuptools 官方 discovery 文档核实到出处（不影响结论：要求 >=64 已保守覆盖）。
- 建议：修正该句为文档口径（或给出具体版本的行为出处）；版本号断言补出处或删。

### [低级] debug.bat 行族范围不精确，且同块 setx "PYTHON"（54 行）去留未表态
- 位置：design.md §2.2-③ debug.bat 行
- 证据：实测行号——「212-217」漏 218（`echo [PASS] APPPATH`）；「228-236」漏 237-239（APPPATH 检查块闭合段）；所引范围内混入非 PYTHONPATH 行（58 `set PYTHON`、61 PYTHON 检查、113/121 同），worker 需自行分辨「PYTHONPATH 设置族」不含这些行；同块 debug.bat:54 `setx "PYTHON"` 同为用户级永久污染，设计对其沉默——与「用户级环境变量永久污染，包安装化后无存在理由」的动机表述不一致（不删也可，但应表态）。
- 建议：范围修正为按块描述（CONFIG_PYTHON_ENV / REINSTALL_PY_LIBS / DEBUG 三块中的 PYTHONPATH 相关行），并对 setx PYTHON 一句表态。

### [低级] cw references 处数不符：design 称 4 处，实核 6 处
- 位置：design.md §2.2-③（skills/sr-od-dev-currency-war/references 行）
- 证据：sim-testing.md:65、:68；telemetry-reading.md:8、:11、:15；match-review.md:4——共 6 处（3 命令前缀 + 3 「必须带/需」说法）。文件名列举无遗漏，仅计数错。
- 建议：改为 6 处或删去计数；worker 执行时以 grep 为准。

### [低级] README 指针失准：报告文件名不存在、阶段状态明细指向落空
- 位置：README.md
- 证据：「设计对抗:进行中 · 报告=attack.md」——attack.md 不存在（分核报告为 attack-core1.md 等命名）；「落地:阶段 0/2 done（明细见 landing.md）」——landing.md 无任何阶段状态记录可看。
- 建议：报告指针改实际文件名；阶段状态要么 landing 补状态行、要么 README 去掉「明细见」指针。

## 结论

方向与核心机制成立（引用核实绝大多数准确，setuptools src-layout 多包自动发现与 uv 可编辑安装/自动同步行为均有官方文档背书，landing 与 design 一致性良好），但影响面在两个方向有实质漏报——非 uv 消费者（locale-po CI，其删除指令会直接弄坏 CI，判阻断）与发布/终端用户链（build-release 的 uv export 离线包、Launcher 运行链的 uv sync/uv run --frozen）——另有按设计自身判据漏列的口径清单与不自证的干净 shell 判据；修完阻断与应修项后方可开工。
