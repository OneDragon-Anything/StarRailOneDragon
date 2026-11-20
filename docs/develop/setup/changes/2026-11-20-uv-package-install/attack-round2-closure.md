# 二轮复核报告（闭合核验 + 全量同步复查）

复核对象：修订后 design.md / landing.md / README.md（2026-11-20-uv-package-install）。
复核方式：attack.md 18 条裁定逐条对修订后正文找落实处；关键行号与现状断言全部对仓库 Read/Grep 实证（build-release.yml、python_service.py、python_launcher.py、locale-po.yml、debug.bat、ps1、daemon、mcp_service_interface.py、pyproject.toml、test-check.yml、③ 清单全部 17 个文件的 grep 命中行、iteration-design.md §5-4）；另做全仓 PYTHONPATH 反查验证清单与豁免边界的完备性。

## 1. 结论摘要

- 18 条裁定：**18/18 闭合**（其中 #4/#5 附行号小偏差、#11/#16 附未覆盖残留行——均另行列入第 3 节发现，不构成裁定本身未闭合）。
- 全量同步复查：三处清单逐文件对齐无多无漏；判据↔设计依据节号对应真实；README 与 design §0 一致、五个链接全部可达；归类规则执行一致（ps1/debug.bat→3.2，python_service 等→3.3，纯口径项→末阶段清单，pyproject 实体归 3.1、注释措辞归清单）。
- 修订引入的新问题：**应修 2 / 低级 4**（详见第 3 节）。按收敛判据（连续一轮无新增阻断级与应修级）本轮未收敛。

## 2. 18 条裁定逐条闭合表

| # | 裁定要点 | 落实处核对 | 仓库实证 | 判定 |
|---|---|---|---|---|
| 1 | locale-po 保留前缀、移出 ③ 入 ①、landing 删行 | design §2.2-① 表 locale-po 行（功能依赖非过期口径，:29/:36）✓；③ 表无 locale-po 行 ✓；landing 正本清单无该行 ✓；landing 3.3 边界「不迁移 locale-po.yml」✓ | locale-po.yml:29 `pip install polib==1.2.0`、:36 前缀、ubuntu-latest 属实 | 闭合 |
| 2 | `uv export` 加 `--no-emit-project`、build-release 入影响面、撤回「无行为变化」 | design §2.2-④-1 完整（editable 条目机理 + flag）✓；§2.1 改「『CI 无行为变化』仅在 sync 面成立」✓；landing 代码文档面 + 3.3 范围/判据 ✓ | build-release.yml:131 `uv export --no-hashes --no-dev --format requirements-txt`、:132 `pip wheel` 属实；:98 sync 属实 | 闭合 |
| 3 | 用户侧调用点加 `--no-install-project`、用户端维持注入、「明确不解决」补边界 | design §2.2-④-2（四处 sync + run_args 逐行号）✓；§1 第 6 类 + 明确不解决第一条 ✓；① 表用户端注入行 ✓；landing 3.3 范围/判据（含 `--check` 组合实测）✓ | python_service.py 四处 = :136 `'sync'`（--find-links 紧邻 :137）、:161-162 `'sync'/'--frozen'`、:190 `'sync'`、:225 `['uv','sync','--check']`；python_launcher.py:147 `run_args = ['run', '--frozen', ...]`、:113 注入——全部与仓库一致（:136/:161-162 为命令块起点，元素行号有 1-2 行容差，定位无歧义） | 闭合 |
| 4 | 冒烟改 Installer+Launcher 二 spec、闭核三 Q1 | design §2.2-②-5 改为二 spec 构建 +「现状 CI 解析机制未确证→editable 后机制明确，风险收敛为改善」（Q1 收口表述）✓；landing 3.2 范围+判据（二 spec 构建成功产出 exe）✓ | build-release.yml 实构确为 Installer/Launcher（pyinstaller 命令在 :120-121）；design 引「:118-119」为 Activate+cd 行，见第 3 节 E | 闭合（附行号小偏差） |
| 5 | mcp_service_interface 补 ①（注入保留）+ ③（docstring 口径） | design §1 第 5 类（:112）、① 表 GUI 行（:112）、③ 表 docstring 行；landing 代码文档面 + 正本清单均有 ✓ | 注入 :112、docstring 首行 :106——③/清单写 :104 偏 2 行，见第 3 节 E | 闭合（附行号小偏差） |
| 6 | ③ 补列 5 项 + proofs 豁免边界 | design ③ 豁免边界句 + 表补 entry.md:27、cw_match_recorder.py:17、generate_ascension_const.py:6、cw scripts 五文件行 ✓；landing 清单同步 ✓ | 全部行号 grep 实证一致（见第 3 节 D 的豁免边界完备性备注） | 闭合 |
| 7 | 干净 shell 判据补显式去污 | landing 3.1 判据首条「去污前置」（Remove-Item/unset + echo 确认空 + 污染来源）✓；design §2.2-②-1 回指 ✓；3.1 判据 2-5 全部「去污后 shell 中」✓ | — | 闭合 |
| 8 | §0 状态同步 | design §0「对抗审中」= README「迭代设计:对抗审中」✓ | — | 闭合 |
| 9 | 归类规则定死、ps1 挪 3.2 | landing 正本清单首「归类规则」句 ✓；3.2 范围/文件面/判据含 ps1（无注入行 + 注释不再表述 package=false + 重启冒烟）✓；清单无 ps1/debug.bat 行 ✓；3.2 阶段名名实相符 ✓ | ps1:110 注释（package=false 表述）、:113 注入属实；见第 3 节 C（design 侧 ps1 处置描述缺失） | 闭合（附 C 项） |
| 10 | 计数改实测 + grep 收口判据 | design ③ quickstart「6 处（:48/49/59/60/91/102）」、cw references 拆三行共 6 处（:65/:68、:8/:11/:15、:4）✓；landing 末阶段判据 grep 收口 ✓ | quickstart 恰 6 行、cw references 恰 6 处，行号逐一相符；grep 收口判据自身缺陷见第 3 节 A | 闭合 |
| 11 | APPPATH 式样定死 | design ③ debug.bat 行：式样 `set "APPPATH=%~dp0src\%MAINPATH%"`、三块替换、MAINPATH 不动、PYTHONPATH 行与校验行删除、APPATH 校验保留 ✓；landing 3.2 判据同式样 ✓（design/landing 式样串一致） | debug.bat 三块 APPPATH set 行确为 3 处（:59/:115/:213）、`if not exist "%PYTHONPATH%"` 三处可 grep 收口；:217 echo 行残留见第 3 节 B | 闭合（附 B 项） |
| 12 | §2.4 表述改文档口径、删版本断言 | design §2.4 改「uv 以 build-system 存在性判定项目是否安装（官方 projects/config 文档：无 build-system 则 virtual，不构建不安装）」✓；§2.1 删「>=61」断言，改「>=64 保守覆盖 + 官方 discovery 文档 + 阶段 3.1 构建实跑即验证」✓ | — | 闭合 |
| 13 | AGENTS.local 节号补摘要、ZZZ 首现补定义 | design §1「AGENTS.local.md §2.3『项目 MCP server 运维』节」+「不落地 ZZZ 仓（绝区零一条龙仓，本机姊妹项目 ZenlessZoneZero-OneDragon）…按 AGENTS.local §2.2（SR→ZZZ 同步件模板：背景/同步点/修法/完成判据四节）」✓；landing 共享资源面与末阶段均带节名/模板摘要 ✓ | — | 闭合 |
| 14 | quickstart 补存量清理提示 | design §2.3-4 ✓；landing 正本清单 quickstart 行「+ 存量 PYTHONPATH 清理」✓；末阶段判据「存量用户级 PYTHONPATH 清理提示」✓（与 grep 判据的冲突见第 3 节 A，属判据缺陷非裁定未落） | — | 闭合 |
| 15 | `setx "PYTHON"` 表态保留 | design ③ debug.bat 行「`setx "PYTHON"`（:54）保留——非导入机制」✓；landing 3.2 判据「`setx "PYTHON"` 保留」✓ | debug.bat:54 `setx "PYTHON" ...` 属实 | 闭合 |
| 16 | debug.bat 改按块描述 | design ③「三块（CONFIG_PYTHON_ENV / REINSTALL_PY_LIBS / DEBUG）」✓ | 三标签实测 :44/:106/:205，块名一致；块内 PYTHON 行/PYTHON 校验行天然排除在「PYTHONPATH 设置族」外，自洽（:217 残留见 B） | 闭合（附 B 项） |
| 17 | 五小项照建议落 | C2-8：§2.1 代码块加「以下 [tool.uv] 段仅 package 行翻转，其余三行系现状保留」✓；C2-6：attack.md 已存在、README 链接可达 ✓；C2-7：声明行维持 ✓；C2-11：landing 共享资源面「末阶段 daemon.py / mcp_service_interface.py 仅注释与 docstring 改动、无行为差异，不重启常驻 server」✓；C2-12：3.2 文件面补「deploy 下 PyInstaller 构建产物目录（gitignore 内，不入库）」✓ | pyproject.toml [tool.uv] 现状四行与代码块注释相符 | 闭合 |
| 18 | test-check.yml 加 import 探针 | design §2.2-④-3（含防兜底遮蔽理由）✓；landing 代码文档面 + 3.3 判据（探针步骤存在且形如指定命令）✓ | test-check.yml:35 sync、:83 pytest 属实（探针插点前提成立） | 闭合 |

## 3. 复核发现（新问题，非 18 条范围即修订自身引入）

### [应修] A. 末阶段 grep 收口判据与裁定 14、保留注释内在冲突——豁免列举不完备，判据按字面不可执行

- 位置：landing.md 末阶段完成判据（「③ 层全部清单文件内 `grep -n PYTHONPATH` 残留为 0 或仅剩豁免项（proofs/ 历史记录、locale-po.yml 功能前缀、保留兜底注入点的必要引用）」）
- 证据：两类**必须保留**的 PYTHONPATH 字样不在三类豁免内——
  1. quickstart 重写段按裁定 14 必须写入「曾配置过的机器请删除用户级 PYTHONPATH 变量」（design §2.3-4、landing 正本清单 quickstart 行均要求）——该句必含 PYTHONPATH 字样，grep 必命中；
  2. pyproject.toml:134 pytest 段注释「(取代 CI 的 PYTHONPATH=src env 和测试文件里手动的 sys.path.insert)」是历史叙述，包安装化后仍成立，③ 清单对 pyproject 行的字面口径只改「package=false」措辞——该行同样命中且非豁免。
  按判据字面执行 = 判据永红，或 worker 被迫删掉裁定 14 要求的警示句/无害历史注释；按 §5-2「实现者无需再设计」，worker 撞到时须停手提请修订。
- 建议：豁免列举补第四类「重写后新增的清理提示句与保留的历史叙述句」，或判据改为「grep 命中逐条归类：需改口径为 0，命中项全部属豁免类」。

### [应修] B. debug.bat 三块内两处 PYTHONPATH 引用行未表态——裁定 11 式样未覆盖的语义空洞

- 位置：design.md §2.2-③ debug.bat 行 / landing.md 3.2 完成判据
- 证据（debug.bat 实测）：
  1. DEBUG 块 :217 `echo [PASS] PYTHONPATH：%PYTHONPATH%`——设计删除面只含 `setx/set "PYTHONPATH"` 行与 `if not exist "%PYTHONPATH%"` 校验行，:217 不在其列；执行后 %PYTHONPATH% 未定义，该行打印字面 `%PYTHONPATH%`，成为用户可见的误导输出（DEBUG 菜单每次启动打印）。设计对「:217 删还是改」无答案。
  2. 三块保留的 APPPATH 校验行（:63/:120/:236）WARN 文案均为「PYTHONPATH 设置错误」——保留行内文案含旧口径，改不改无表态（:236 在 DEBUG 块括号式校验块内）。
- 建议：design 补一句「`echo [PASS] PYTHONPATH` 行删除；APPATH 校验行 WARN 文案顺带改为 APPPATH 措辞」，landing 3.2 判据同步（判据可加「无 `%PYTHONPATH%` 变量引用」收口）。

### [低级] C. ps1 的处置描述在 design 正文丢失（修订引入的 design↔landing 失同步）

- 位置：design.md §2.2（四层均无 ps1 行）
- 证据：修订前 design ③ 有 ps1 行（核二 C2-2 引证），修订按裁定 9 挪 landing 3.2 后，design 正文对 ps1 只剩 §1 第 5 类的症状枚举——为什么 ps1 删注入而同族 daemon（:192）/GUI（:112）注入保留，设计层无归层无理由；③ 表 debug.bat 有行而 ps1 无行，同族实体清理两件处置在 design 侧不对称。landing 3.2 判据自足可执行（无注入行 + 注释不再表述 package=false），单凭 landing 能开工，故定低级。
- 建议：design §2.2 补一行说明 ps1 处置与「删而 daemon 留」的理由（如：ps1 注入仅服务启动进程，可编辑安装后 uv run 链路自足，删除；daemon/GUI 注入为幂等兜底保留）。

### [低级] D. 豁免边界字面不覆盖 docs 下 proofs/，且 design 与 landing 宽窄不一

- 位置：design.md §2.2-③ 豁免边界句 vs landing.md 末阶段判据
- 证据：design 豁免字面 = `skills/sr-od-dev-currency-war/scripts/proofs/` + `docs/**/changes/`；landing 判据写泛化的「proofs/ 历史记录」。全仓 grep 实测 `docs/develop/sr_od/application/currency_war/proofs/` 下 4 文件 5 处命中（p77:78、p72:178、validations/p42_granularity_check.md:5、validations/P5_REMEASURE.md:4）——均为历史重跑记录（「2026-09-07 亲跑」类），按豁免边界精神应豁免，但按 design 字面两不沾（非 skills 路径、非 changes/）。末阶段判据作用域限于「③ 层清单文件内」，实际收口不受影响，故定低级。
- 建议：design 豁免边界改为「各处 proofs/ 历史重跑记录（skills scripts 下与 docs 玩法目录下均是）」，与 landing 泛化口径对齐。

### [低级] E. 行号偏差两处（另两处容差记录）

- 1. mcp_service_interface.py docstring 实际在 **:106**（:104 为空行、def 在 :105）；design §2.2-③ 表与 landing 正本更新清单均写 :104。同文件 design §1 第 5 类与 ① 表的 :112（注入行）正确。
- 2. design §2.2-②-5「CI 实构同款，build-release.yml:118-119」——pyinstaller 实构命令在 **:120-121**（:118 为 Activate、:119 为 cd deploy）；landing 3.2 的「:115-121」覆盖 step 全程、正确。引用行号应指命令本体。
- 容差记录（不判偏差）：python_service.py「:136 安装 --find-links」（--find-links 元素在 :137）、「:161-162 自检 --frozen --inexact --check」（--inexact/--check 在 :163/:164）——均为命令块首行定位，起点准确无歧义。
- 建议：顺手校正前两处。

### [低级] F. attack.md 收敛状态行统计口径自相矛盾

- 位置：attack.md「收敛状态」节「第一轮：阻断 3 / 应修 12（去重）」
- 证据：裁定表内应修级实为 8 条（#4-#11）；12 为三核未去重合计（核一 5 + 核二 4 + 核三 3）。标了「（去重）」却用未去重数。不影响裁定内容，影响后续按条数对账。
- 建议：改「应修 8（去重前 12）」。

## 4. 全量同步复查记录（iteration-design.md §5-4）

1. **三处清单逐文件对齐**：design §2.2-③ 表 18 行（含 debug.bat）↔ landing 影响面申报代码文档面 24 项 ↔ landing 正本更新清单 17 行——24 = 3.1 面（pyproject、uv.lock）2 + 3.2 面（debug.bat、ps1）2 + 3.3 面（build-release.yml、test-check.yml、python_service.py、python_launcher.py）4 + 末阶段清单 17 − 共享 uv.lock 不重复计 = 对齐无多无漏；正本清单缺 debug.bat/ps1 由归类规则句显式解释，口径一致。
2. **判据↔设计依据节号**：landing 3.1 依据 §2.1/§2.2-②、3.2 依据 §2.2-②-5/③、3.3 依据 §2.2-④、末阶段依据 §2.2-③/§2.3-3/4/6——节号全部真实存在，判据内容与设计逐项对应（②-1~4 ↔ 3.1 判据 2-5、②-5 ↔ 3.2、④-1/2/3 ↔ 3.3 判据 1/3/2、§2.3-3/4/5 ↔ 末阶段 quickstart 三附加点）。
3. **README**：与 design §0 状态一致（对抗审中）；design/landing/attack/attack-core1/2/3 五链接全部可达；「阶段 0/3」与 landing 三编号阶段 + 末阶段结构相符；阶段状态记 README、landing 不记状态，分工正确。
4. **归类规则执行一致性**：ps1/debug.bat（实体）→ 3.2；python_service/python_launcher/build-release/test-check（实体）→ 3.3；pyproject 实体改动 → 3.1、其注释措辞 → 末阶段清单（同文件两阶段动，按项归类符合规则）；locale-po.yml → ① 保留、landing 无行；正本更新清单全部为纯文档/注释口径项。一致。
5. **引用锚存在性抽核**：design §1/§2.2 引用的全部 文件:行号 逐一对仓库核实——pyproject:48/105/136、debug.bat:54/55、hook_path_inject.py:17、RuntimeLauncher.spec:18、ps1:113、daemon:192（③ 行 188-205）、mcp_service_interface:112、python_launcher:113/147、test-check:35/83、build-release:98/131、locale-po:29/36、common-package-sync:41、.github/dev.md:7、ai_coding:27、quickstart 六行、character-data :19/:33、entry.md:27、cw 五脚本与三 references 全部行号——除第 3 节 E 所列两处偏差外全部相符。

## 5. 收敛建议

本轮新增应修 2（A/B）+ 低级 4（C/D/E/F），按收敛判据（连续一轮无新增阻断级与应修级）**未收敛**。A/B 修复成本均为一两句话（判据豁免补类 + debug.bat 两行处置表态），建议编排者直接修订后再走一轮闭合确认。
