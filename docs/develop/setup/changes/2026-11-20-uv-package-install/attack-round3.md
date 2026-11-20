# 三轮复核报告（丙案修订闭合性 + 全量同步复查 · 2026-11-20）

复核对象：丙案修订后 design.md / landing.md / README.md（2026-11-20-uv-package-install）。
复核方式：attack.md 一轮 18 条 + 二轮处置 #19-28 + 裁定轮丙案记录逐条对正文找落实处；甲/乙残留措辞全量 grep；关键断言全部对仓库 Read/Grep 实证（build-release.yml:80-160、debug.bat 三块、python_service.py:102-204、python_launcher.py:282-331、env_config.py、test-check 引用、iteration-design.md §5-4/§6）。

## 1. 结论摘要

- 丙案内部一致性：§0/§1/§2.2-④-2/§2.4/landing 3.3 丙案口径贯通（grep 证实无 UV_NO_INSTALL_PROJECT / 挂起 / 待裁定 / 两态方案残留；§2.4 甲乙对比与行为基线中被否决路线的实测记录属合法裁定依据）——但 §2.2-① 表一处行内理由残留排除路线措辞（应修 R3-1），④-2 丙案段一处升级断言与代码矛盾（应修 R3-2）。
- 二轮处置 #19-28：**10 条中 10 条按裁定面闭合**（#27 附注：闭合 C 建议的「理由句」在裁定时收窄未采纳，残留另列 R3-6；#22 裁定文本本身只覆盖 DEBUG 块 WARN，CONFIG 块同性质残留另列 R3-4）。
- 全量同步复查（iteration-design.md §5-4）：三处清单逐文件对齐无多无漏；python_service.py / python_launcher.py 已从全部文件面移除；README 七链接可达、状态与 §0 一致；硬规则快查全净（无过程叙事、无待定措辞）。
- 新发现：**应修 2 / 存疑 1 / 低级 3**；另记二轮低级遗留未处置 3 项。按收敛判据（连续一轮无新增阻断级与应修级）**未收敛**——两条应修均为 design 文本一两句修订，修后可走第四轮闭合确认。

## 2. 丙案内部一致性核验

| 检查点 | 结果 | 证据 |
|---|---|---|
| design §0 状态 | 丙案口径，无待裁定时态 | design.md:6「对抗审中（用户端**丙案已裁定**…三轮复核中）」；grep「挂起/待裁定/升用户裁定」design/landing/README 零命中（§2.4「用户裁定（2026-11-20）：丙」为已决记录，合法） |
| design §1 明确不解决 | 丙案口径 | design.md:23「python_service / python_launcher 不做任何修改；用户机由环境包补 setuptools 供给**安装本项目**（§2.2-④-2 丙案）」——与丙案一致（对比 §2.2-① 残留见 R3-1） |
| design §2.2-④-2 | 标题「（丙案，已裁定）」；行为基线 = 编排者实验矩阵（联网装上/空缓存离线失败 exit 1/find-links 离线成功/lock 无 setuptools），与 attack.md 二轮实验表逐项一致；「排除路线…已否决」为实测事实陈述，合法 | design.md:109-112 ↔ attack.md:48-55 |
| design §2.4 | 丙 vs 甲 vs 乙取舍 + 用户裁定丙，与 attack.md 裁定轮记录（含 E7、主站文档查证）实质一致 | design.md:129 ↔ attack.md:78-86 |
| design §2.3-2 | 「用户端由环境包补 setuptools 供给（④-2 丙案），联网与断网用户均不依赖外网」 | design.md:118 |
| landing 影响面 / 3.3 | 代码文档面无 python_service / python_launcher 行；3.3 边界「用户端代码零改动（design §2.2-④-2 丙案）」 | landing.md:7-29、:80 |
| 残留措辞扫描 | 「UV_NO_INSTALL_PROJECT」design/landing/README 零命中（仅 attack.md 轮次记录，合法）；「条件化排除」仅 §2.4 甲案命名（裁定记录，合法） | grep 输出 |
| ④-2 丙案段断言抽查 | 「追加 setuptools>=64（满足 build-system.requires 版本约束）」「装机代价 ~800KB 级」与 §2.1/裁定轮一致；**存量用户升级断言与代码矛盾 → R3-2** | 见 R3-2 |

## 3. 二轮处置 #19-28 逐条闭合表

| # | 裁定要点 | 落实处核对 | 仓库实证 | 判定 |
|---|---|---|---|---|
| 19 | 撤 run_args 加 flag；用户端排除改环境变量（后随丙案整体撤除） | design §2.2-④-2 无任何 run_args/sync 加 flag 提案；§2.4 已否决栏记「`uv run --no-install-project`（选项不存在）」；UV_NO_INSTALL_PROJECT 三文件零命中——甲案 env 注入路线已随丙案干净撤除 | — | 闭合 |
| 20 | 两态方案升用户裁定 → 裁定轮丙 | §2.4 记丙/甲/乙对比与裁定；④-2「（丙案，已裁定）」；§0 状态同步；无「两态方案」活提案残留 | — | 闭合 |
| 21 | 动机按实验矩阵重写 | §2.2-④-2 行为基线（uv 0.10.4、临时目录 src-layout 最小项目、空 uv 缓存）四断言与 attack.md 实验表逐项一致；§2.3-2 同步改写 | — | 闭合 |
| 22 | debug.bat 逐块差异化处置 | design ③ debug.bat 行三块分别落地（CONFIG：删 setx/set 行+PYTHONPATH 校验、APPATH 推导式样（本块 :49 有 MAINPATH，实况证实）、APPATH 校验保留；REINSTALL：删 PYTHONPATH/APPATH 行与校验、保留 PYTHON/UV；DEBUG：删 set/:217 echo/校验、APPATH 推导（:206 有 MAINPATH，实况证实）、WARN 改「APPATH 设置错误」）；landing 3.2 判据逐块对应 | debug.bat :44-65/:106-128/:205-244 实读逐行对上（:49/:54/:55/:58/:59/:62/:63；:113-121；:206/:212/:213/:217/:228-232/:236） | 闭合（CONFIG 块 WARN 文案同性质残留见 R3-4） |
| 23 | proofs 入列必改 + 豁免边界改写 | design ③ proofs 行「现行重跑指引（非历史存档），入列必改」；豁免边界改三类口径（用法文案必改 / changes\| 历史过程件豁免 / 警示·历史注释类豁免）；landing 清单 proofs 行同步 | — | 闭合（docs 下 proofs 字面缝隙为二轮低级遗留，见 §6） |
| 24 | 豁免补「警示/历史注释类」第三类 | design ③ 豁免句 + landing 末阶段判据三类清单（locale-po 功能前缀 / ① 层注入引用 / quickstart·pyproject 警示内容）——quickstart 提示句与 pyproject 注释命中不再自噬 | — | 闭合 |
| 25 | skills sys.path 自插族第七类 | §1「七类兜底」计数 + 第 7 类行 + ① 层表行（约 14 处，幂等无害保留）三处一致 | design.md:11/:18/:66 | 闭合 |
| 26 | 3.3 原 --check 组合实测撤除，改临时目录复验 + 禁动本仓 venv | landing 3.3 判据「分发版 uv 复验：临时目录（空 uv 缓存 + UV_OFFLINE=1 + --find-links 放 setuptools wheel + --frozen）…禁动本仓 venv 状态后不恢复」；原「本地 --no-install-project sync 后叠跑 --check」步骤已不存在；丙案下用户机本就装项目，无项目 venv 自检形态不复存在，判据与丙案自洽 | — | 闭合（复验自包含性见 R3-3） |
| 27 | ps1 归层 / 行号偏差 / attack 计数 | design ③ 表 ps1 行已回（「注释 + 注入清理（实体改动，实施归 3.2…）」）；docstring 行号已正 :106（design.md:99）；spec 行号已正 :120-121（design.md:75，实况 :120-121 pyinstaller 命令）；attack.md 一轮计数已改「阻断 3 / 应修 8（去重，表内 #4–#11）」 | debug.bat/python 实读；attack.md:38 | 闭合（按裁定面；闭合 C 建议的「删 ps1 而留 daemon/GUI」理由句裁定时收窄未采纳，残留 R3-6） |
| 28 | 二轮存疑 2 条消解或落 §2.3-7 | §2.3-7 分发版 uv 一致性 + landing 3.3 复验步骤落地；存疑-2（「自动保持安装最新」出处）措辞未改，但 3.1 判据实测覆盖（uv.lock 条目 + 去污 import 冒烟），与「消解」裁定相容 | — | 闭合 |

## 4. 全量同步复查记录（iteration-design.md §5-4）

1. **三处清单对齐**：design §2.2-③ 表 20 行（18 纯口径项 + ps1/debug.bat 两实体项）↔ landing 代码文档面 23 项（18 口径项中 pyproject 注释并入 pyproject 行 = 17 行 + pyproject/uv.lock/debug.bat/ps1/build-release.yml/test-check.yml 6 实体项）↔ landing 正本更新清单 18 行——逐文件对齐，无多无漏；python_service.py / python_launcher.py 已从代码文档面、3.3 文件面、正本清单全部移除，仅以「零改动」边界语句与行为基线引用形式出现（合法）。
2. **设计依据节号**：3.1（§2.1、§2.2-②）、3.2（§2.2-②-5、③）、3.3（§2.2-④-1/2/3、§2.3-6/7）全部真实且对应；末阶段头部「§2.3-3/4/6」中 /6 错引（属 3.3 依据），判据自身引 §2.3-3/4/5——见 R3-5。
3. **README**：与 design §0 状态一致（对抗审中/丙案已裁定/三轮复核中）；design/landing/attack/attack-core1/2/3/attack-round2-closure/attack-round2-nopremise 七链接文件全部存在（目录实列 9 文件）。
4. **硬规则快查**：design/landing/README grep「本轮|修订后|修订前|待定|看情况|TBD|暂定」零命中；依据就地标注（④-2 丙案段「上表实测」、§2.4 实测/文档双依据）成立。
5. **引用锚抽核**：build-release.yml:98（sync）/120-121（pyinstaller）/131（export 重定向至 deploy/dist/requirements.txt）/132（pip wheel）/135（Compress-Archive → StarRail-OneDragon-Environment.zip）、python_service.py:136（--find-links :137）/:161-162/:190/:225、python_launcher.py:113/:147、env_config.py DEFAULT_UV_DIR_PATH=.install\uv——全部与正文引用相符。

## 5. 新发现

### [应修] R3-1. design §2.2-① 「用户端发布链注入」行残留排除路线措辞，与丙案矛盾

- 位置：design.md:65（§2.2-① 表）「发布形态必要机制（用户机以源码树形态运行），**配合 §2.2-④-2 排除安装保持现状语义**」。
- 证据：丙案下 §2.2-④-2 无任何「排除安装」——用户机恰恰要**装上**本项目（§1 design.md:23「用户机由环境包补 setuptools 供给**安装本项目**」；attack.md 裁定轮「用户端/开发端/公共框架零改动」指代码零改动，非不安装）。该行理由句是一轮 #3「用户端加 --no-install-project」时期的产物，丙案修订扫了 §1/§2.4 却漏了这行——读者据 ① 层会得出「用户机不安装项目」的错误结论，与同文档 §1 直接冲突。
- 建议：改为「发布形态必要机制（用户机以源码树形态运行）；④-2 丙案下零改动保留，注入优先级仍高于可编辑安装，语义不变」。

### [应修] R3-2. ④-2 丙案段「断网用户由本地 wheels 供给，均自动恢复」与代码矛盾——断网存量用户升级后无法启动

- 位置：design.md:112（§2.2-④-2 丙案段）「存量用户升级：新 lock 含项目条目、自检触发一次按需同步，联网用户走镜像、**断网用户由本地 wheels 供给，均自动恢复**」。
- 证据（代码实读）：
  1. 「自检触发的按需同步」= `python_service.py:171 uv_sync_runtime_dependencies` → `:187-196` 执行 `uv sync --inexact --default-index <镜像>`——**该调用点不传 `--find-links`**（全仓仅 `:136-138` 安装路径传；`_configure_uv_environment`（:102-105）只设 `UV_PYTHON_INSTALL_DIR`/`VIRTUAL_ENV`，grep 证实全 one_dragon 无 `UV_FIND_LINKS` 环境变量）→ 本地 wheels 目录对该路径不可见；
  2. 断网存量用户升级到丙版后：自检（:161-164 `--frozen --inexact --check`）因项目未装判不同步 → :190 按需同步离线无 setuptools 供给（用户机 uv 缓存从未装过 setuptools，E7/行为基线口径）失败 → `python_launcher.py:305-308` **sys.exit(1)**，启动器退出，GUI 不可达（:136 带 --find-links 的恢复路径走不到）；
  3. 该场景今天真实存在：`fetch_latest_code`（python_launcher.py:284-297）断网仅打印 ERROR 不退出，现状（package=false）下断网用户锁面无项目条目、自检通过、可正常离线启动——丙案零改动实施后此切片从「可离线启动」回退为「需一次联网或重跑安装器」。
- 影响：与 §2.4/裁定轮「隐式离线能力完整保留」的卖点表述冲突（实况：**初次离线安装**保留——:136 带 --find-links 且新 Environment.zip 含 setuptools wheel；**存量断网升级**不保留）。此句会原样进 ZZZ 同步件与后续维护判断。
- 建议（二选一）：① 文本修正（默认）——该句改为「联网用户自动恢复；断网存量用户升级后首次启动的按需同步（python_service.py:190 调用点）无 --find-links、取不到本地 wheels，构建隔离无 setuptools 供给会失败并退出启动器（python_launcher.py:305-308），需一次联网或重跑安装器——与主站文档『完整包不能完全替代网络』口径一致；初次离线安装不受影响（:136 带 --find-links）」；② 若「断网升级可启动」是硬需求 → 升用户裁定（给 :190 补 --find-links 属公共框架一行改动，与丙案「零改动」前提冲突，须用户定）。

### [存疑] R3-3. landing 3.3 分发版 uv 复验步骤欠自包含

- 位置：landing.md:89（3.3 完成判据第 4 条）。
- 证据：① 「以 `.install/uv` 下实际分发的 uv 版本」——该目录由用户态环境安装流程生成（env_config.py:9-11 默认路径 `.install\uv\uv.exe`），本机 `.install/` 当前仅有 `uv_cache`、无 `uv/`，判据未写取得方式（跑 env.bat / GUI 环境安装可生成）；② 「空 uv 缓存」「与 design §2.2-④-2 实验同口径」——§2.2-④-2 只给结论矩阵，最小项目构造与空缓存实现（如 `UV_CACHE_DIR` 指临时目录）未落文，worker 需自行重建实验环境。
- 建议：判据补两句——uv 二进制取得方式 + 复现环境三要素（临时 src-layout 最小项目按 §2.1 式样、`UV_CACHE_DIR` 指空临时目录、wheels 目录放 setuptools wheel）。

### [低级] R3-4. CONFIG 块收口两处缝隙（#22 裁定覆盖面残留）

- 位置：design.md:102（§2.2-③ debug.bat 行 CONFIG 块）/ landing.md:73（3.2 判据）。
- 证据：① 保留的 APPATH 校验行（debug.bat:63）WARN 文案同为「PYTHONPATH 设置错误」，DEBUG 块同位置（:236）已改「APPATH 设置错误」，CONFIG 块未随判——清理后该块已无 PYTHONPATH 概念，失败路径提示误导（二轮闭合 B 建议覆盖三处，裁定 #22 只写 DEBUG 块）；② landing 3.2 判据 CONFIG 块只写「无 PYTHONPATH set/setx 行」，漏列「PYTHONPATH 校验行（:62）删除」——REINSTALL（「行与校验」）与 DEBUG（「set/echo/校验行」）两块判据都含校验，CONFIG 独缺；design 已明确 :62 删除（删后若残留，`if not exist "%PYTHONPATH%"` 展开为空串恒真，CONFIG 菜单必 WARN+exit /b 1，功能破坏），判据开头的「逐块对照 design §2.2-③」可兜住，但判据自身口径不齐。
- 建议：design CONFIG 块补「WARN 文案改 APPPATH 措辞」；landing CONFIG 判据补「无 PYTHONPATH 校验行」。

### [低级] R3-5. landing 末阶段设计依据节号错引

- 位置：landing.md:96「design.md §2.2-③、§2.3-3/4/6」。
- 证据：§2.3-6（发布 CI export/wheel 观察）明文「阶段 3.3 实跑」，是 3.3 的依据（3.3 头部已正确引 §2.3-6/7）；末阶段判据自身引「design §2.3-3/4/5」（quickstart 三附加点）。头部 /6 应为 /5。二轮闭合时已存在未被点名，属持续性小错。
- 建议：改「§2.3-3/4/5」。

### [低级] R3-6. ps1「删注入而 daemon/GUI 保留」的归层理由仍缺位

- 位置：design.md §2.2（① 层 daemon/GUI 行各有保留理由，ps1 仅 §1 第 5 类症状枚举 + ③ 行「注释 + 注入清理」，无删除理由）。
- 证据：二轮闭合 C 建议补一句「删而 daemon 留」的理由，裁定 #27 落点收窄为「③ 表归层」未采纳该半句。同族三件两留一删，设计层理由不对称，后续按图索骥者会问。
- 建议：③ 行补括注「ps1 注入仅服务启动进程自身，可编辑安装后 uv run 链路自足故删；daemon/GUI 注入为跨进程幂等兜底故留」。

## 6. 二轮低级遗留现状（未处置项复核，非本轮新增）

attack.md 二轮处置表未收编的 nopremise 低级 3 条现状：

| 项 | 现状 |
|---|---|
| 低级-3（④-1「`-e file://...`」形式 vs 实测 `-e .`） | 未改（design.md:108 原文留存）；结论与处置不受影响，属形式表述差 |
| 低级-4 / 闭合 D 低级半（docs/**/currency_war/proofs/ 历史复算记录字面不落豁免三类） | 未改；末阶段 grep 作用域限 ③ 清单文件内，无操作面影响 |
| 低级-5（README「落地:阶段 0/3 done」与 landing 四阶段结构计数不齐、「阶段 0」无定义） | 未改（README.md:12 原文留存） |

按 iteration-design.md §6「存疑/低级记遗留随收口」属合法遗留，建议定稿前顺手清理（低级-5 尤其，README 是进度单一源）。

## 7. 收敛判定

本轮新增：**阻断 0 / 应修 2（R3-1、R3-2）/ 存疑 1（R3-3）/ 低级 3（R3-4/5/6）**。

按收敛判据（连续一轮无新增阻断级与应修级发现）**未收敛**。两条应修均为 design 文本局部修订（R3-1 一行改写；R3-2 一句断言修正或升裁定），不动方案骨架、不动 landing 阶段结构；R3-2 若走文本修正路线，注意同步核对 §2.4「离线能力保留」表述与 ZZZ 同步件产出时机（末阶段）。修后建议走第四轮轻量闭合确认（重点仅 R3-1/R3-2 落点 + R3-3 判据补写），其余低级项可随收口处理。
