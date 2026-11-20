# 四轮复核报告（闭合确认 · 2026-11-20）

复核对象：三轮处置（attack.md #29-32）后的 design.md / landing.md / README.md。
复核方式：三轮 6 条发现 + 二轮低级遗留 3 项逐条对正文找落实处；处置句涉及的事实全部对仓库实读（python_service.py:100-210、python_launcher.py:280-330、env_config.py:1-30、debug.bat 三块、build-release.yml:125-140、OneDragon-Home src/zzz/zh/quickstart.md:52）；design/landing/README 硬规则与残留措辞 grep；三处清单逐文件比对。

## 1. 结论摘要

- 三轮处置 #29-32 全部闭合，无一处「裁定面打了折扣」；二轮低级遗留 3 项中 2 项已闭合、1 项（docs/proofs 字面缝隙）维持合法遗留。
- 处置改句未引入新矛盾；关键引文「完整包不能完全替代后续更新」对主站原文核实为缩略引用、语义一致。
- 全量同步复查：三处清单逐文件对齐、README 链接全可达、硬规则零命中、事实锚（行号/路径/文件存在性）全部吻合。
- 新发现：**阻断 0 / 应修 0 / 存疑 0 / 低级 1**（design §0 轮次状态滞后一句话）。按收敛判据（连续一轮无新增阻断级与应修级）**达到收敛，可定稿**。

## 2. 三轮处置逐条闭合表

| # | 裁定要点 | 落实处核对 | 仓库实证 | 判定 |
|---|---|---|---|---|
| 29 | §2.2-① 用户端注入行清除「排除安装」措辞 | design.md:65 现为「发布形态必要机制（用户机以源码树形态运行）；④-2 丙案下零改动保留，注入与可编辑安装指向同一 src/，语义一致」；grep「排除安装」design/landing/README 零命中 | — | 闭合（措辞与三轮建议略异——「指向同一 src/」替代「优先级仍高于」——两者均正确且信息等价：同指 src/ 时优先级高低无行为差异，未引入新矛盾） |
| 30 | 升级边界如实写入，三处口径一致 | §2.2-④-2（design.md:112）：联网走镜像自动恢复；断网存量用户按需同步调用点（:190）不传 `--find-links`、构建隔离无 setuptools 供给失败并退出启动器（:305-308）、需一次联网或重跑安装器；初次离线安装不受影响（:136 带 `--find-links`）；「给 :190 补 `--find-links` 记为未来方向不实施」句在。§2.4（design.md:129）：「初次离线安装能力保留……断网存量升级仍需联网一次，见 §2.2-④-2 升级边界」。§2.3-2（design.md:118）：「用户端初次安装……不依赖外网；断网存量升级例外见 §2.2-④-2 升级边界」——三处均为「初次离线安装保留 / 断网存量升级需一次联网」同口径 | python_service.py:187-196 按需同步命令仅 `--inexact --default-index`、确无 `--find-links`（:190 为 `sync` 参数行，行号吻合）；python_launcher.py:305-308 确为失败路径 `sys.exit(1)`；python_service.py:136-138 安装路径确带 `--find-links`。主站引文核实：OneDragon-Home `src/zzz/zh/quickstart.md:52` 原文「完整包可以减少首次安装时的环境或模型下载，但不能完全替代后续的代码和资源更新」——design 引文「完整包不能完全替代后续更新」为缩略引用，语义一致 | 闭合 |
| 31 | landing 3.3 分发版 uv 复验自包含 | landing.md:89：uv 二进制取 `.install/uv/uv.exe`（本机无该目录时先跑 env.bat 或 GUI 环境安装生成）+ 复现环境三要素（临时目录 src-layout 最小项目按 design §2.1 式样、`UV_CACHE_DIR` 指空临时目录、wheels 目录放 setuptools wheel 且附 `pip download setuptools --dest` 取得命令）+ 执行命令（`UV_OFFLINE=1` + `uv sync --frozen --find-links <wheels>`） | env.bat 仓库根实存；env_config.py:10-11 默认路径 `DEFAULT_UV_DIR_PATH = .install/uv`、`DEFAULT_UV_PATH = .install/uv/uv.exe` 与判据字面一致 | 闭合 |
| 32a | R3-4① design CONFIG 块 WARN 文案 | design.md:102 CONFIG 块：「APPATH 校验行保留且 WARN 文案『PYTHONPATH 设置错误』改『APPATH 设置错误』」 | debug.bat CONFIG 块实况：PYTHONPATH 校验行与 APPATH 校验行（WARN「PYTHONPATH 设置错误」）均在，处置句与实况逐行可执行对应 | 闭合 |
| 32b | R3-4② landing CONFIG 判据补「校验行」 | landing.md:73：「CONFIG 块无 PYTHONPATH set/setx/校验行……APPATH 校验保留且 WARN 文案为『APPATH 设置错误』」——与 REINSTALL（「行与校验」）、DEBUG（「set/echo/校验行」）两块判据口径齐平 | 同上 | 闭合 |
| 32c | R3-5 末阶段节号 /6→/5 | landing.md:96：「设计依据：design.md §2.2-③、§2.3-3/4/5」——§2.3-5（uv build 边界警示）与末阶段判据自引「design §2.3-3/4/5」一致，头部与判据不再错位 | — | 闭合 |
| 32d | R3-6 ps1 删留理由 | design.md:101 括注：「ps1 注入仅服务启动进程自身的会话环境，可编辑安装后 `uv run` 链路自足故删；daemon/GUI 注入作用于拉起的子进程、属跨进程幂等兜底故留」——同族三件两留一删的理由对称补齐 | — | 闭合 |
| 32e | 二轮低级-3（-e 形式表述） | design.md:108 现表述「以 editable 条目写进输出」「指向 runner 临时路径的悬空指针包」，不再断言 `-e` 具体形式；landing.md:87「产物无 `-e` 条目」系对产物的核对项（无论 `-e .` 还是 `-e file://...` 形态均覆盖），非对 uv 行为形式的断言 | — | 闭合 |
| 32f | 二轮低级-5（README 阶段计数） | README.md:12 重写为「落地:未开始（阶段划分见 landing.md）」——「阶段 0」与计数不齐问题随重写消失 | — | 闭合 |
| 32g | 二轮低级-4（docs/**/proofs/ 字面不落豁免三类） | 维持未改：design §2.2-③ 豁免句明文「`docs/**/proofs/` 历史复算记录豁免」，landing 末阶段 grep 作用域限「③ 层清单文件内」（docs 侧 proofs 不在 ③ 清单、不会被扫到），无操作面影响 | — | 合法遗留（不阻断定稿，随收口可不动） |

## 3. 全量同步复查记录

1. **三处清单对齐**：design §2.2-③ 表 20 行（18 口径项 + ps1/debug.bat 两实体项）↔ landing 代码文档面 23 项（18 口径项 + pyproject.toml/uv.lock/build-release.yml/test-check.yml/debug.bat/ps1 六实体项）↔ landing 正本更新清单 18 行——口径项逐文件一一对应无多无漏；landing 多出的实体项各有 design 依据（pyproject/uv.lock ← §2.1，build-release.yml ← ④-1，test-check.yml ← ④-3）。python_service.py / python_launcher.py 不在任何清单，仅以「零改动」边界语句与行为基线引用形式出现（合法）。
2. **状态一致**：design §0 与 README 大状态一致（均为对抗审中/闭合确认）；轮次子状态失同步见 R4-1。
3. **README 链接**：design/landing/attack/attack-core1/2/3/attack-round2-closure/attack-round2-nopremise/attack-round3 八链接文件全部存在（目录实列 10 文件）。
4. **硬规则快查**：design/landing/README grep「本轮|修订后|修订前|待定|看情况|TBD|暂定」零命中；「排除安装/UV_NO_INSTALL_PROJECT/两态方案」零命中（丙案口径贯通无残留）。
5. **事实锚抽查**：build-release.yml:131 `uv export --no-hashes --no-dev --format requirements-txt`（现无 `--no-emit-project`，与「迭代目标态、3.3 实施后判据核对」自洽）、:132 pip wheel、:135 Compress-Archive；debug.bat 三块（CONFIG 块有 MAINPATH、DEBUG 块 :205 有 MAINPATH、REINSTALL 块无 MAINPATH）与 design 逐块处置前提全部吻合。

## 4. 新发现

### [低级] R4-1. design §0 轮次状态滞后于 README

- 位置：design.md:6「状态：对抗审中（……三轮复核中）」。
- 证据：attack.md 三轮处置表已完整、README.md:10-11 已标「三轮发现已处置，四轮闭合确认中」——design §0 的轮次子状态未随三轮处置收尾更新。大状态「对抗审中」无误，README 为轮次进度单一源，影响轻微。
- 建议：定稿时随 §0 状态改「已定稿」一并消解；若四轮后又改文，先同步为当前轮次。

## 5. 收敛判定

本轮新增：**阻断 0 / 应修 0 / 存疑 0 / 低级 1（R4-1）**。

三轮 6 条发现全部闭合、二轮低级遗留清账（2 闭 1 合法遗留）、处置未引入新问题、全量同步复查干净。按收敛判据（连续一轮无新增阻断级与应修级发现），本轮零新增阻断与应修——**达到收敛，design.md / landing.md / README.md 可定稿**。R4-1 为一句话级状态同步，随定稿动作顺手处理即可，不构成定稿前置。
