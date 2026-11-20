# 二轮对抗审报告（无前提攻击 · 2026-11-20）

审查对象：本迭代目录 design.md / landing.md / README.md（当前版）。
审查方法：引用行号逐项 Read/Grep 核验；全仓消费点扫描（PYTHONPATH / sys.path / uv 子命令，排除 .venv、.git、.debug/、docs/**/changes/）；uv 0.10.4 官方文档查证；**临时目录一手实测**（uv 0.10.4 本机版本，src-layout 双顶级包最小项目复现设计场景，测后已清理，未触碰仓库任何文件）。

## 0. 实测环境与矩阵（发现 B1/B2/M1 的证据基座）

临时项目 = pyproject（`[build-system]` setuptools>=64 + `[tool.uv] package = true`）+ `src/pkg_a`、`src/pkg_b` 双顶级包（均有 `__init__.py`），Python 3.11.12，uv 0.10.4。逐条结果：

| # | 实验 | 结果 |
|---|---|---|
| T1 | `uv lock` + `uv sync` | 成功，多顶级包**零包清单配置**自动发现成立；`import pkg_a, pkg_b` 成功 |
| T2 | site-packages 内容 | `__editable__.demo_multi_top-0.1.0.pth`，内容为**纯静态绝对路径**指向 `...\src`（非 import-hook finder） |
| T3 | `uv sync --check --no-install-project`（项目**已装**） | **exit 1**，输出 `Would uninstall 1 package - demo-multi-top`、`The environment is outdated` |
| T4 | `uv sync --no-install-project`（项目**已装**） | **执行卸载**：`Uninstalled 1 package`，.pth 消失，此后 `import pkg_a` 失败 |
| T5 | `uv sync --check --no-install-project`（项目**未装**） | **exit 0**（landing 3.3 实测步骤的目标态成立） |
| T6 | 裸 `uv sync --check`（项目**未装**） | **exit 1**（设计「存量用户不加排除则 --check 立判不同步」的动机主张实证成立） |
| T7 | `uv run --no-install-project ...` | **命令行报错** `unexpected argument '--no-install-project'`（提示相似参数 `--no-reinstall`）；`uv run --help` 全选项面无此 flag（有 `--no-sync`/`--frozen`/`--no-project`/`--no-editable` 等） |
| T8 | `uv run --frozen python -c`（项目未装） | 运行成功且**自动把项目 editable 装上**（.pth 出现）；`UV_OFFLINE=1` 下同样装上且成功——**uv 对根项目的 editable 安装不触发 PEP 517 构建、不拉 setuptools、不需要网络** |
| T9 | `UV_NO_INSTALL_PROJECT=1 uv run python -c`（项目已装） | 成功，已装项目**未被卸载**（环境变量形式对 `uv run` 有效） |
| T10 | `uv export --no-hashes --format requirements-txt` 默认 | 输出含 **`-e .`** 条目（官方文档核实：默认含当前项目，社区案例证实该条目会使 `pip wheel` 在目标机构建项目） |
| T11 | 同上 + `--no-emit-project` | 输出 0 命中 `-e`/项目名——干净，**④-1 处置实证有效** |
| T12 | PyInstaller 6.7.0（项目 dev 组同版本）`--onefile` 打包 `from pkg_a import ...` | 构建 exit 0，bundle 运行输出正常——**modulegraph 沿静态 .pth 成功解析 editable 包**，②-5 的「机制明确为 venv 查找指针」实证支持 |
| T13 | 删 `[build-system]` + 删 `package = true` | lock 条目为 `source = { virtual = "." }`，sync 不装项目——§2.4「无 build-system 视为 virtual」主张成立 |

附：uv.lock（有 build-system 时）仅含项目自身条目（`source = { editable = "." }`），**未出现 setuptools 构建依赖条目**（T8 机制的自然结果）。

## 1. 发现清单

### 阻断

**[阻断-1] `uv run` 不存在 `--no-install-project` 选项，④-2 对 python_launcher 的处置照单实施即瘫痪用户端启动链**
- 位置：design.md §2.2-④-2（design.md:105「`src/one_dragon/devtools/python_launcher.py:147` 的 `run_args = ['run', '--frozen', ...]` 各加 `--no-install-project`」）；landing.md 3.3 完成判据同步收口。
- 证据：实测 T7（uv 0.10.4 = 设计自引版本：`error: unexpected argument '--no-install-project' found`；`uv run --help` 选项面确认仅有 `--no-sync`、`--locked`、`--frozen`、`--no-project`、`--no-editable`、`--exact` 等，无任何 install-project 族 flag）。
- 后果：python_launcher 的 uv run 命令**每次启动直接报错**，用户端全链瘫痪——比不改更糟。
- 建议：python_launcher 改用 `--no-sync`（用户端依赖由 python_launcher.py:303 前置的 `uv_sync_runtime_dependencies` 保证，run 时点无需再同步环境；语义 = 完全不动环境，天然排除项目安装）或环境变量 `UV_NO_INSTALL_PROJECT=1`（实测 T9 对 uv run 有效且不卸已装项目）。同时 landing 3.3 判据的 grep 收口项「python_launcher.py run_args（:147）均含 `--no-install-project`」需随改。

**[阻断-2] `uv sync --no-install-project` 会卸载已装项目、`--check` 组合在项目已装时判失败——④-2 漏判「开发机 GUI 共用同一调用点」象限，实施后开发机 GUI 自检卡永远红、一键装依赖静默摧毁可编辑安装**
- 位置：design.md §2.2-④-2（「用户端运行链」定性，design.md:102-105）；landing.md 3.3。
- 证据：实测 T3/T4（项目已装态：`--check` 组合 exit 1「Would uninstall」；`sync` 真卸载）。调用面核验：`src/one_dragon_qt/view/setting/setting_env_interface.py:324/:339`、`src/one_dragon_qt/widgets/install_card/venv_install_card.py:17`（`install_method=ctx.python_service.uv_sync`）与 `:37`（`is_synced = ctx.python_service.uv_check_sync_status()`）、`python_install_card.py:19`——`python_service.py` 是**公共框架代码，其调用点在开发机 GUI 与用户机 GUI 同样运行**，并非「用户端运行链」专属。
- 后果链（开发机，venv 由 `uv sync --group dev` 装好项目）：
  1. 打开 GUI → 环境自检卡跑 `uv sync --check --no-install-project` → exit 1 → 自检永远报「环境不同步」；
  2. 点「安装依赖」→ `uv sync --no-install-project` → **把开发机 venv 里的项目可编辑安装卸掉**（.pth 消失）→ 此后不经 `uv run` 的裸 `python` import `sr_od` 失败——本迭代的主成果被自家 GUI 一键操作静默摧毁，且与 pytest pythonpath 兜底叠加后故障形态极隐蔽。
- 建议：④-2 必须按调用点实际运行环境细分：用户机态（项目永不安装，加 flag 语义正确，T5 实证）与开发机态（项目已装，加 flag 即破坏，T3/T4 实证）冲突，方案需改为环境无关的一致解——候选：`python_service` 各调用点以环境变量 `UV_NO_INSTALL_PROJECT` 注入（对已装项目不卸载、T9 实证）或引入机器形态判定；至少须在设计里写明两态矩阵与选型，不能维持「行为与现状一致」的现状断言。

### 应修

**[应修-1] ④-2 的动机断言与 uv 根项目 editable 安装的真实机制不符：不触发构建、不拉 setuptools、离线也能装**
- 位置：design.md §2.2-④-2（「否则用户机每次同步/自检/启动都要求本项目可编辑就绪即触发构建（构建隔离拉 setuptools，离线 Environment.zip 用户无 setuptools…）」）；关联 §2.1（「锁文件新增本项目条目与 setuptools 构建依赖条目」）与 §2.3-2（「首次构建需联网：构建隔离环境需拉 setuptools 进 uv 缓存」）。
- 证据：实测 T8（`UV_OFFLINE=1` 下 `uv run --frozen` 把项目 editable 装上且成功；site-packages 无 setuptools）；实测 T13 附注（uv.lock 无 setuptools 条目）。
- 后果：动机叙述错误会误导实现者与后续维护；真实风险是行为面而非构建面——`uv run` 默认自动装项目（T8）与 `uv sync --no-install-project` 要卸项目（T4）在用户端交替执行 = 环境状态乒乓、GUI 自检红绿闪烁（见阻断-2）。§2.3-2 的「联网成本」在 uv sync/run 路径上不存在，仅在 `uv build` 真构建时成立。
- 建议：改写动机与 §2.3-2 措辞；lock 变化描述改为「新增本项目 editable 条目（无 setuptools 构建依赖条目）」。

**[应修-2] debug.bat 第三块（REINSTALL_PY_LIBS）没有 MAINPATH 赋值行，「三块同式样替换、MAINPATH 各块现状赋值不动」的事实前提在第三块不成立**
- 位置：design.md §2.2-③ debug.bat 行；landing.md 3.2 完成判据「APPATH 三处均为 `set "APPPATH=%~dp0src\%MAINPATH%"` 式样」。
- 证据：debug.bat 实读——`set "MAINPATH=..."` 仅存在于 CONFIG_PYTHON_ENV（:49）与 DEBUG（:206）两块；REINSTALL_PY_LIBS（:106-128）无该行（其 APPPATH 行 :115 引用 `%PYTHONPATH%\%MAINPATH%`，依赖菜单循环中的变量残留或恒空）。
- 后果：按式样替换后第三块 APPPATH 展开为 `%~dp0src\`（MAINPATH 为空），`if not exist` 校验仍通过（src 目录存在）——无运行故障（该块 APPPATH 无消费者），但设计断言与现状不符，worker 无从执行「不动」一个不存在的赋值，产出必然偏离设计文本。
- 建议：明确第三块处置——补 `set "MAINPATH=sr_od\gui\sr_full_app.py"` 赋值、或第三块改用不含 MAINPATH 的式样、或说明该块 APPPATH 校验行可一并删除。

**[应修-3] proofs 豁免定性错误：「过程存档非现行用法指引」与 scripts/proofs/ 脚本头注释的实际性质不符**
- 位置：design.md §2.2-③ 豁免边界（「`skills/sr-od-dev-currency-war/scripts/proofs/` 下的历史重跑记录豁免（过程存档非现行用法指引）」）；landing 末阶段判据沿用该豁免。
- 证据：grep 实读——该目录下 p38_check.py:4、p40_refresh_ev_check.py:2、p43_check.py:3、p46-52、p65_check.py:44、p70_check.py:11、p71_check.py:14、p89_check.py:16、p97_refresh_budget_check.py:20、p51_v3_rebuild.py:28 等脚本头注释均为**现行重跑指引**（「入库可重跑: `$env:PYTHONPATH='src'; uv run python ...`」式命令行），非某次重跑的记录。
- 后果：豁免结论本身可维持（改动后命令照跑、前缀冗余无害），但理由错位使末阶段「grep 残留为 0 或仅剩豁免项」的收口口径失据——豁免的是「活用法文案」而非「过程存档」。
- 建议：豁免理由改为成本收益式表述（量多、命令仍有效、无行为故障），或将脚本头注释纳入 ③ 层口径同步。

**[应修-4] landing 3.3 的 `--check` 组合实测步骤会破坏开发机 venv，且无善后**
- 位置：landing.md 3.3 完成判据（「本地以 `--no-install-project` sync 后叠跑 `--check` 验证」）。
- 证据：实测 T4——`uv sync --no-install-project` 在项目已装的 venv 上**卸载项目**。3.3 在 3.1 之后执行（开发机 venv 已装好项目），照单实测 = 卸掉 3.1 刚验证的安装；landing 未写实测后恢复（重跑 `uv sync --group dev`），后续阶段不经 `uv run` 的裸 python import 将莫名失败。
- 建议：判据补善后步骤（实测后 `uv sync --group dev` 恢复并复跑 import 冒烟）；或改在临时 venv 中实测，不碰开发机环境。

**[应修-5] §1「六类兜底」影响面陈述漏了第七类：skills 脚本内 sys.path 自插兜底族**
- 位置：design.md §1（六类清单）、§2.2-①（零改动层表格无此项）。
- 证据：grep 实读——`skills/sr-od-dev-currency-war/scripts/` 下 cw_batch_stats.py:116-117、extract_synthesis.py:18、extract_equip_data.py:24、cw_sim_match_drive.py:61、gen_plaza_invest.py:44、gen_plaza_chars.py:44、gen_plaza_spot_lights.py:43、gen_plaza_comps.py:524、harvest_equip_codex.py:48、gen_traits.py:74、win_model_m1.py:45 及 proofs/ 多处；另有 `skills/sr-od-dev-relic-data/scripts/build_relic_authority_table.py:27`。抽查 cw_batch_stats.py:105-117 注释口径为自包含兜底说明（「自脚本位反推仓库 src…项目根直跑零前置」），改动后并不过期。
- 后果：行为面保留无害（幂等兜底）、注释口径基本不过期，但「影响面分层」是设计核心交付物，存在未申报的一族，后续按图索骥者会撞到设计未认领的面。
- 建议：① 层表格补一行归位（「skill 脚本 sys.path 自插族：幂等兜底，保留，注释口径经抽查不过期」），或在 §1 列为第七类。

### 存疑

**[存疑-1] `uv sync --check --no-install-project`（项目未装）exit 0——官方文档无逐字记载，本审查已代实测通过**
- 位置：design.md §2.2-④-2（「组合语义 = 被排除项不参与同步判定，阶段 3.3 实测复核」）。
- 证据：实测 T5（exit 0）；WebSearch 官方文档与 CLI reference 仅有间接推断（"implied by the docs"），无逐字条文。
- 建议：保留 3.3 实测步骤（本审查实测结果可作旁证但以迭代内实测为准）；注意 T3 反例——「不参与判定」只对**未装态**成立，已装态判该卸（见阻断-2），文档措辞需带状态前提。

**[存疑-2] design §1「uv 在 pyproject 变化后自动保持安装最新（uv 0.10.4 文档行为）」的直接文档出处未核**
- 证据：实测 T8 间接支持（`uv run` 每次自动同步并把缺装的项目装上），但「文档明文」这一定源未在本次查证中找到逐字出处。
- 建议：3.1 冒烟本就覆盖该行为（改 pyproject 后 uv run 直接可用），风险低；如需可把出处改为「实测行为」表述。

### 低级

**[低级-1] design §2.2-②-5 引用「build-release.yml:118-119」指代两个 pyinstaller 构建行——实际在 :120-121**（:118 是 Activate、:119 是 cd deploy）。landing 3.2 的「:115-121」引用正确。

**[低级-2] design ③ 层「mcp_service_interface.py:104」**——docstring 实际起于 :106（`_server_spawn_env`）；:104 为空行。① 层引用 :112（注入行）准确。

**[低级-3] design ④-1 称 export 默认写「`-e file://...`」**——uv 0.10.4 实测输出形态为 `-e .`（T10）。同为 editable 条目、结论与处置不受影响，仅形式表述与实测有差。

**[低级-4] `docs/develop/sr_od/application/currency_war/proofs/` 下约 30 处 PYTHONPATH 复算命令引用**（p38-p97 各证明单的可重跑命令行）既不在 ③ 清单也不在豁免表。末阶段判据限定「③ 层全部清单文件内」故不冲突，但这些是活复算指引，建议豁免表补一句归位，防 worker 末阶段扩大化或困惑。

**[低级-5] README 进度口径「落地:阶段 0/3 done（阶段划分见 landing.md）」**与 landing 的四阶段结构（3.1/3.2/3.3/末阶段）计数不齐，「阶段 0」在 landing 无定义——进度口径歧义。

## 2. 已核验为准确的关键项（正面确认，不构成发现）

- 引用行号全部准确的：pyproject.toml:48/:105/:136、debug.bat:55、hook_path_inject.py:17、RuntimeLauncher.spec:18、start_mcp_server.ps1:113、sr_od_daemon.py:192（:188-205 区间）、python_launcher.py:113/:147、python_service.py 四处 sync（:136/:161/:190/:225，**恰好四处无第五处**）、test-check.yml:35/:83、build-release.yml:98/:115-121/:131、locale-po.yml:29/:36、quickstart.md:48/49/59/60/91/102、ai_coding.md:27、entry.md:27、common-package-sync.md:41、.github/dev.md:7、character-data SKILL.md:19/:33、generate_ascension_const.py:6、sim-testing.md:65/:68、telemetry-reading.md:8/:11/:15、match-review.md:4（单文件复验命中）、currency-war 各脚本行号、cw_match_recorder.py:17。
- Installer/Launcher 两个 spec 确无 sys.path.insert（仅 RuntimeLauncher.spec 与 hook_path_inject.py 有）——②-5 的「真实验面」判断准确。
- locale-po.yml 确为 ubuntu + `pip install polib==1.2.0`、无 uv——① 层「功能依赖保留」判断准确。
- §2.4 两项取舍依据均实证成立：setuptools src-layout 多顶级包零配置自动发现（T1）；无 build-system + 无 package 键则 virtual 不装（T13）。
- workflows 全量清点（auto-close-issue/build-release/locale-po/test-check）——无遗漏 CI 面；文档站不在本仓。
- §2.2-① 「可编辑安装不改变 `__file__`」——静态 .pth 机制（T2）下成立。
- `--no-emit-project` 处置（④-1）实证有效（T10/T11）。
- PyInstaller 6.7.0 对 uv 静态 .pth editable 的解析实证可行（T12）——②-5 风险收敛判断有据。

## 3. 总体结论

方案骨架（package=true + setuptools src-layout 自动发现 + 开发侧受益 + export 排除 + 探针）方向正确，核心机制经一手实测大体成立（T1/T5/T6/T10/T11/T12/T13）。但 **④-2「用户端运行链适配」一节存在两处阻断级硬伤**：`uv run` 根本没有 `--no-install-project` 选项（照单实施 = 用户端启动命令直接报错）；`uv sync --no-install-project` 对已装项目执行卸载且 `--check` 组合在已装态判失败，而 python_service 调用点横跨开发机 GUI——实施后开发机自检卡永红、一键装依赖摧毁可编辑安装。该节需按「调用点运行环境两态矩阵」重写（含 uv run 自动装项目的新机制认知）后方可进入落地。其余为影响面陈述与判据善后的应修项。

分级统计：阻断 2 · 应修 5 · 存疑 2 · 低级 5。
