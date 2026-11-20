# 设计对抗汇总

## 三核报告

- 核一·无前提：[attack-core1.md](attack-core1.md) —— 阻断 1 / 应修 5 / 存疑 1 / 低级 3
- 核二·规范遵循：[attack-core2.md](attack-core2.md) —— 阻断 0 / 应修 4 / 存疑 1 / 低级 7
- 核三·治本核验：[attack-core3.md](attack-core3.md) —— 阻断 2 / 应修 3 / 存疑 2 / 低级 2

三核关键证据（CI export 默认含项目、用户端 uv sync 调用点、locale-po 无 uv、CI 实构 Installer/Launcher 二 spec、mcp_service_interface 注入）经编排者对仓库逐处抽查复核，全部属实。

## 合并裁定与处置（去重后，级别取三核最高）

| # | 级别 | 发现（合并来源） | 裁定 | 落点 |
|---|---|---|---|---|
| 1 | 阻断 | locale-po.yml 是 ubuntu + `pip install polib`（无 uv），`PYTHONPATH=$(pwd)/src` 是导入功能依赖非过期口径，删除即断 mo 编译 CI（核一阻断 / 核三 F1） | **保留前缀不删**；移出 ③ 清单、并入 ① 兜底层并注明理由（不经 uv 的直跑场景，与 pytest pythonpath 同判） | design §2.2-① / landing 清单删行 |
| 2 | 阻断 | CI `uv export` 默认把项目自身以 editable 条目写进 requirements.txt（uv 官方文档明文），`pip wheel` 会在 runner 上构建项目并把悬空指针包打进 Environment.zip；「CI 无行为变化」主张不成立（核三 A2 / 核一应修1） | **`uv export` 加 `--no-emit-project`**，保持环境包语义不变；build-release.yml 入影响面；撤回「无行为变化」表述 | design §2.2-新④ / landing 新阶段 3.3 |
| 3 | 阻断 | `package = true` 广播到用户端全部 uv 调用点（python_service.py 四处 sync、python_launcher.py `uv run --frozen`）——用户机被迫构建本项目（离线 Environment.zip 无 setuptools、存量用户 `--check` 立判不同步）（核三 A1 / 核一应修2） | **用户侧调用点加 `--no-install-project`**（uv 官方支持），用户端发布形态维持现状 PYTHONPATH 注入；「明确不解决」补「用户端不做包安装化」边界 | design §1/§2.2-①④ / landing 新阶段 3.3 |
| 4 | 应修 | 冒烟 spec 不对齐：CI 实构 Installer/Launcher（均无 sys.path.insert），设计只冒烟 RuntimeLauncher（唯一自插兜底的）（核三 F2） | 3.2 冒烟改 **Installer + Launcher 二 spec**（CI 同款）；顺带闭核三 Q1（CI 现状解析机制未确证——editable 后机制明确，风险变改善） | design §2.2-②5 / landing 3.2 |
| 5 | 应修 | mcp_service_interface.py:103-113 GUI 侧 server 拉起注入 + docstring「package=false」漏列（核一3 / 核三 F3） | ① 层补（注入保留）+ ③ 层补（docstring 口径） | design §1 第5类并句 / §2.2①③ / landing 末阶段 |
| 6 | 应修 | ③ 清单按自身判据漏列：entry.md:27、cw_match_recorder.py:17、generate_ascension_const.py:6、cw skill scripts 5 文件；proofs/ 历史记录未划豁免边界（核一4 / 核三 F3） | 全部补列；豁免边界定为「带『需/必须 PYTHONPATH』断言的用法文案入列，proofs/ 历史重跑记录豁免」 | design §2.2-③ / landing 清单 |
| 7 | 应修 | 「干净 shell」判据不自证：setx 污染机上冒烟假阴性通过（核一5） | 判据补显式去污（`unset PYTHONPATH` / `Remove-Item Env:PYTHONPATH`）+ 前置 `echo` 确认为空 | landing 3.1 判据 |
| 8 | 应修 | design §0「草案」与 README「对抗审中」失同步（核二 C2-1） | §0 状态改「对抗审中」，此后按硬规则 4 两处同步 | design §0 |
| 9 | 应修 | ps1 注入删除（实体改动）归末阶段、debug.bat 归 3.2，归类矛盾且 3.2 名实不符（核二 C2-2） | 归类规则定死：**实体行为改动归落地阶段，末阶段清单只收纯文档/注释口径项**；ps1 整体（注释+注入）挪 3.2 | landing 3.2 / 清单 |
| 10 | 应修 | cw references 计数 4 实为 6、quickstart「~5」实为 6（核二 C2-3/C2-10 / 核一低级2） | 处数改实测值并逐处给行号；阶段判据加「清单文件内 grep PYTHONPATH 清零（豁免边界除外）」收口 | design §2.2-③ / landing 判据 |
| 11 | 应修 | APPPATH 推导式样 design 未写实、landing 带省略号——实现者需再设计（核二 C2-4） | design 定死式样：`set "APPPATH=%~dp0src\%MAINPATH%"`，三块同步替换，PYTHONPATH 行与其校验行删除，APPATH 校验保留 | design §2.2-③ / landing 3.2 |
| 12 | 存疑 | 「无 build-system 时 uv 假定 setuptools 并告警」与 uv 官方文档不符（实际：不构建不装项目本身）；「setuptools>=61」无出处（核一存疑 / 核三 L1 / 核二 C2-9） | 表述改文档口径；版本断言删除，依据改「setuptools 官方 package discovery 文档 + 阶段构建实跑验证」 | design §2.4 / §2.1 |
| 13 | 存疑 | AGENTS.local 节号与「ZZZ 仓」对仓库外读者不可解析（核二 C2-5） | 引用处补一句内容摘要；ZZZ 首现补「（绝区零一条龙仓，本机姊妹项目）」 | design §1 / landing 末阶段 |
| 14 | 低级 | 存量 setx PYTHONPATH 用户级残留遮蔽可编辑安装、双仓串包风险（核三 L2） | quickstart 重写段补「曾用 debug.bat 配置的机器删除用户级 PYTHONPATH 变量」 | design §2.3 / landing 末阶段判据 |
| 15 | 低级 | setx "PYTHON"（debug.bat:54）去留未表态（核一低级1） | 表态：**保留**——非导入机制（Python.exe 不读 PYTHON 变量），超出本迭代范围 | design §2.2-③ |
| 16 | 低级 | debug.bat 行族范围不精确（漏 218/237-239，混入 PYTHON 行）（核一低级1） | 改按块描述（CONFIG_PYTHON_ENV / REINSTALL_PY_LIBS / DEBUG 三块）+ 式样定死后行号自然收敛 | design §2.2-③ |
| 17 | 低级 | 代码块现状行未标注（C2-8）、README attack.md 悬空（C2-6，本文件闭合）、模板声明行保留（C2-7 维持）、daemon 改后重启未裁定（C2-11）、3.2 构建产物目录未申报（C2-12） | 全部照建议落 | design §2.1 / landing |
| 18 | 采纳 | CI 加环境探针让「包没装上」在主链可见，防兜底遮蔽（核三治本建议） | test-check.yml 加一步 `uv run python -c "import sr_od, one_dragon, one_dragon_qt, onnxocr"` | landing 3.3 |

未采纳/维持：核三 Q2（--find-links 是否喂构建隔离）随裁定 3 的处置路线自然消解（后经二轮修订升裁，见下）。

## 收敛状态

第一轮：阻断 3 / 应修 8（去重，表内 #4–#11）——未收敛，处置已全部落入修订，进入二轮。

---

## 第二轮

报告：[attack-round2-closure.md](attack-round2-closure.md)（闭合复核：18/18 闭合 + 新发现 应修 2 / 低级 4）、[attack-round2-nopremise.md](attack-round2-nopremise.md)（无前提新攻：阻断 2 / 应修 5 / 存疑 2 / 低级 5，含临时目录一手实测）。

**编排者对二轮关键实测主张的独立复核**（隔离 uv 缓存的临时目录 src-layout 最小项目，uv 0.10.4）：

| 实验 | 结果 | 对二轮主张的裁决 |
|---|---|---|
| `uv run --help` 含 `--no-install-project`？ | **无**（uv sync 有） | 阻断-1 **证实**——run_args 加该 flag 不可行 |
| 空缓存 + 离线 + `uv sync --frozen` 装根项目 | **exit 1 失败**（setuptools unsatisfiable） | 「UV_OFFLINE=1 也能装」**证伪**（该实验未隔离缓存）；核一轮 A1「离线包破坏」判断**复活** |
| 联网 `uv lock` | lock 只含根项目、**无 setuptools 条目** | 「lock 无 setuptools」证实 |
| 空缓存 + 在线 + `--frozen` sync | 成功装 editable | 联网用户/开发机无碍 |
| 已装态 + `UV_NO_INSTALL_PROJECT=1` + `uv run` | 正常运行、**不卸载** | env 变量形态对 run 有效且无乒乓 |
| 无项目 venv + `sync --no-install-project --check --frozen` | **exit 0** | 排除项不参与 check 判定，用户机自检形态可行 |

二轮处置（已落入修订）：

| # | 级别 | 发现 | 裁定 | 落点 |
|---|---|---|---|---|
| 19 | 阻断 | `uv run` 无 `--no-install-project`（无前提阻断-1） | 撤销 run_args 加 flag；用户端排除改用 `UV_NO_INSTALL_PROJECT=1` 环境变量（实验证实对 run/sync 双有效且不卸载） | design §2.2-④-2 |
| 20 | 阻断 | `sync --no-install-project` 卸载已装项目 + 开发机 GUI 安装卡同代码双态运行（无前提阻断-2） | 用户端处置升级为**两态方案**（甲：安装目录 `.git` 判据 + env 条件注入 / 乙：接受联网装、离线承诺改口径），**升用户裁定**（§2.4 取舍）——「无条件排除」路径正式否决 | design §2.2-④-2、§2.4 |
| 21 | 应修 | ④-2 原动机表述（被迫构建/拉 setuptools/离线挂）与实测部分不符（二轮应修1） | 动机按编排者实验矩阵重写：联网可装、真离线（空缓存）失败、lock 无 setuptools | design §2.2-④-2 行为基线 |
| 22 | 应修 | debug.bat 第三块无 MAINPATH 赋值，「三块同式样」前提不成立（二轮应修2 + 闭合 B） | 逐块差异化处置：REINSTALL 块直接删 PYTHONPATH/APPATH 行（不消费二者）；CONFIG/DEBUG 块改推导式样；DEBUG 块 echo/WARN 文案同步 | design §2.2-③ / landing 3.2 |
| 23 | 应修 | proofs/ 定性错误——系现行重跑指引非历史存档（二轮应修3 + 闭合 D） | proofs/ 4 文件 5 处入列必改；豁免边界改写 | design §2.2-③ / landing |
| 24 | 应修 | 末阶段 grep 收口判据自噬（quickstart 警示句/pyproject 注释必含 PYTHONPATH 字样）（闭合 A） | 豁免补第三类「警示/历史注释类合法残留」 | landing 末阶段判据 |
| 25 | 应修 | skills 脚本 sys.path 自插族 ~14 处未申报（二轮应修5） | §1 补第七类兜底 + ① 层保留 | design §1/§2.2-① |
| 26 | 应修 | 3.3 原 `--check` 组合实测步骤会在开发机卸载项目（二轮应修4） | 判据重写：两态复验改在临时目录模拟 + 禁动本仓 venv 后不恢复 | landing 3.3 |
| 27 | 低级 | ps1 在 design 四层无归层（闭合 C）、行号偏差（闭合 E：docstring :106、spec :120-121）、attack.md 一轮计数 | 全部照建议落 | design ③ 表 / attack.md 本文 |
| 28 | 存疑 | 二轮存疑 2 条（attack-round2-nopremise.md） | 随 19/20 处置消解或落入 §2.3-7（分发版 uv 行为一致性 3.3 实测） | design §2.3-7 / landing 3.3 |

二轮结论：**未收敛**（阻断 2）——修订已落；用户端方案选型（甲/乙）为产品级裁定点，升用户裁定后定稿（「带开放问题的定稿不存在」）。

---

## 裁定轮（用户参与）

用户追问「为什么 setuptools 不能也在环境包里」→ 编排者补实验：

| 实验 | 结果 |
|---|---|
| E7（find-links 供给 setuptools） | wheels 目录放 setuptools wheel 后，空缓存 + 离线 + `--frozen` + `--find-links` → **exit 0 构建并装上根项目**——构建隔离认 `--find-links`（一轮核三 Q2 存疑就此闭环） |

伴随查证：主站文档（OneDragon-Home，ZZZ 侧 quickstart.md:52，同框架同发布链）明示「完整包可减少下载、不能完全替代网络」——「纯离线安装」非官方承诺，仅隐式能力；安装命令恒带 `--default-index` 镜像（python_service.py:128-134）佐证。

**用户裁定（2026-11-20）：丙案——环境包补 setuptools**（CI 在 export 产物追加 `setuptools>=64` 一行，用户端/开发端/公共框架零改动，隐式离线能力完整保留）。甲（条件化排除）乙（接受联网）均弃——甲为不存在的承诺付公共框架侵入，乙无谓放弃能力。已落入 design §2.2-④-2 / §2.4 与 landing 3.3。

---

## 第三轮

报告：[attack-round3.md](attack-round3.md)（丙案闭合 + 全量同步：阻断 0 / 应修 2 / 存疑 1 / 低级 3，另记二轮低级遗留 3 项）。二轮处置 #19-28 十条全闭合、三处清单对齐、硬规则全净；两条应修均为 design 文本局部问题。

| # | 级别 | 发现 | 裁定 | 落点 |
|---|---|---|---|---|
| 29 | 应修 | §2.2-① 用户端注入行残留「排除安装」措辞与丙案矛盾（R3-1） | 照建议改写（注入与可编辑安装同指 src/，语义一致） | design §2.2-① |
| 30 | 应修 | 丙案段「断网存量用户自动恢复」与代码矛盾：按需同步（python_service.py:190）不传 `--find-links`，断网升级用户首次启动会失败退出（R3-2） | **文本修正**（忠实执行「零改动」裁定）：升级边界如实写入——初次离线安装保留、断网存量升级需联网一次（与主站口径一致）；给 :190 补 `--find-links` 记为未来方向不实施 | design §2.2-④-2 / §2.4 / §2.3-2 |
| 31 | 存疑 | 分发版 uv 复验步骤欠自包含（R3-3） | 判据补齐：uv 二进制取得方式 + 复现环境三要素 | landing 3.3 |
| 32 | 低级 | CONFIG 块 WARN 文案与校验判据、末阶段节号 /6→/5、ps1 删留理由缺位（R3-4/5/6）、二轮低级遗留（-e 形式表述、README 阶段计数） | 全部照建议落 | design ③/landing/README |

---

## 第四轮（闭合确认）

报告：[attack-round4.md](attack-round4.md)。三轮 6 条 + 二轮遗留 3 项全部闭合；全量同步复查干净；新发现仅 1 低级（design §0 轮次子状态滞后一句话，随定稿消解）。

**四轮零新增阻断与应修级发现 → 达到收敛判据（连续一轮无新增），设计定稿。**
