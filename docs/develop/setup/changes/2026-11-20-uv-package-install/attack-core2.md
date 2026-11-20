# 核二·规范遵循攻击报告

审查对象：design.md / landing.md / README.md（2026-11-20-uv-package-install）
对照规范：docs/develop/harness/iteration-design.md（下称「规范」）、项目 AGENTS.md §10「文档规范」（下称「AGENTS §10」）
核查方式：逐项对照 + 文档引用锚实证（pyproject.toml / debug.bat / start_mcp_server.ps1 / sr_od_daemon.py / deploy 两件 / CI 三件 / skill 四件 / quickstart / ai_coding / common-package-sync.md / AGENTS.local.md 逐一行号复核，全部实际读取）。

## 发现清单

### [应修] C2-1 design §0 状态「草案」与 README 进度「迭代设计:对抗审中」失同步

- 规范出处：iteration-design.md §6（「带开放问题的定稿」不存在——未决状态由总纲 §0 表达；生命周期 草案→对抗审中→定稿，定稿才可派落地批）+ §5-4（修订后全量同步复查，禁只改触碰段）
- 位置：design.md §0「状态：草案」 vs README.md 进度节「迭代设计:对抗审中」
- 证据：规范 §2.1 定义状态序列 `草案 → 对抗审中 → 定稿`，两处状态位应一致表达同一事实。当前 README 已推进到「对抗审中」（设计对抗进行中、attack 报告在途、落地 0/2 未派工），design §0 仍停在「草案」。§0 状态位是「定稿才可派落地批」门槛的判断源，两处不一致使流程位置判定失真——后续若有人只读总纲会误判迭代尚未进入对抗审。
- 建议：design §0 状态改为「对抗审中」，与 README 对齐；此后每次流程位置变化（定稿/收尾）按 §5-4 全量同步两处。

### [应修] C2-2 实体改动在「正本更新清单」与 3.2 阶段之间归类不一致：ps1 注入删除进末阶段，debug.bat 归 3.2

- 规范出处：iteration-design.md §3.1（固定末阶段 = 正本更新；阶段 = 一个可独立验收的 worker 批）+ §3.2（正本更新清单每行格式「正本文档：节 ← 本迭代哪个阶段导致」，由固定末阶段消费，清单清零 = 收尾完成）
- 位置：landing.md 3.2 节（范围/文件面仅 debug.bat）+ 「正本更新清单」行「tools/mcp/start_mcp_server.ps1：注释与注入清理 ← 3.1」
- 证据：design §2.2-③ 中 start_mcp_server.ps1 行为「注释 + 注入（删除）」——注入删除是脚本实体行为改动（实测 start_mcp_server.ps1:112 `$env:PYTHONPATH = "src"`），与 debug.bat 的 setx/PYTHONPATH 族删除（同为实体行为改动）完全同族。落地却分置两处：debug.bat 归 3.2「打包链冒烟与启动脚本清理」，ps1 的清理（含实体改动）归末阶段「正本更新」。两处矛盾：① 3.2 阶段名为「启动脚本清理」却只清 debug.bat 不清同为启动脚本的 ps1，名实不符；② 正本更新清单按规范应载「正本文档」的更新义务，混入脚本行为改动后，「清单清零 = 收尾完成」的语义失真（清单项不再是文档更新而是代码改动）。另：清单不含 debug.bat（③ 有行、3.2 有处理，逻辑自洽但与 ps1 的归类标准互相矛盾——同为实体改动，一个进清单一个不进，归类规则无说明）。
- 建议：统一归类——把 start_mcp_server.ps1 的注入删除挪进 3.2（与 debug.bat 同批清理启动脚本，阶段名随之名实相符），末阶段清单只留其注释口径行；或在 landing 首节写明归类规则（实体改动归落地阶段、清单只收口径与注释）并按规则把 ps1 行拆开。注意挪动后 3.2 完成判据须补 ps1 验证点，且 3.2 与 3.1 的 MCP 裸起冒烟互不影响（3.1 用 `-m` 直起不经 ps1）。

### [应修] C2-3 口径同步计数不完整：currency-war references 申报「4 处」，实测 6 处提及，按清单字面执行漏改 2 处

- 规范出处：iteration-design.md §3.2（清单 = 固定末阶段唯一消费源，清零 = 收尾完成——清单不完整则收尾判定失真）+ §5-4（全量同步复查：判据同步、文件面真实路径逐一核）
- 位置：design.md §2.2-③「skills/sr-od-dev-currency-war/references/{sim-testing,telemetry-reading,match-review}.md | 4 处命令前缀与『必须带』说法」+ landing.md 正本更新清单对应三行
- 证据：实测 grep（2026-11-20）：三文件含 PYTHONPATH 共 6 处——match-review.md:4（「`(运行需 PYTHONPATH=src)`」说明）、sim-testing.md:65（「运行需 `PYTHONPATH=src`,项目根跑」说明）、sim-testing.md:68（命令前缀）、telemetry-reading.md:8（命令前缀）、:11（「必须带前缀」说法）、:15（复盘渲染命令前缀）。design 申报口径「命令前缀 + 必须带说法」只覆盖 4 处（68/8/11/15），漏 match-review.md:4 与 sim-testing.md:65 两处说明性提及；landing 清单行「sim-testing.md：replay 命令前缀」的字面语义同样不覆盖 65 行说明文字。包安装化后这两处文字即成错误口径，末阶段按清单字面执行会漏改，而「清单清零」判据不会报警。
- 建议：design ③ 该行处数改 6 并写明口径（3 处命令前缀 + 2 处说明性提及 + 1 处「必须带」说法，逐处给行号）；landing 清单三行的处描述同步细化（「sim-testing.md：replay 命令前缀与运行说明（65/68 行）」等），保证 worker 按行可勾。

### [应修] C2-4 APPPATH 推导式样未在 design 写实，landing 侧仅「`%~dp0src\...`」带省略号——单文档方案的深度缺口

- 规范出处：iteration-design.md §2.1（单文档方案此处即完整设计，深度要求与详设相同）+ §2.2（方案深度标准 = 实现者无需再设计）+ §5-2（「看情况/待定/酌情」= 未定稿；实现者遇到的每个语义选择都要能在设计里找到答案）
- 位置：design.md §2.2-③ debug.bat 行「APPPATH 校验逻辑改按源码路径推导」+ landing.md 3.2 完成判据「原校验意图（路径存在性检查）按 `%~dp0src\...` 直接推导保留」
- 证据：debug.bat 现状（实测 58-59 行等四处）`set "PYTHONPATH=%~dp0src"` + `set "APPPATH=%PYTHONPATH%\%MAINPATH%"`。改造需回答的语义选择：APPPATH 保留为变量改指 `%~dp0src\%MAINPATH%`，还是删除变量改字面路径？三处校验/打印（62-63、119-120、228-236）是否同步改？design 作为单文档完整设计只给方向（「按源码路径推导」），具体式样落在 landing 且尾巴是省略号（`...`）。按规范 §2.3 判据「实现某个阶段只读总纲 + 该阶段指向的详设即可动手」——本迭代无详设，实现者只读总纲时无法确定上述选择，属轻度「需再设计」。
- 建议：design §2.2-③ debug.bat 行补一句定死式样（如「APPPATH 改 `%~dp0src\%MAINPATH%`，四组设置与三处校验同步替换，MAINPATH 逻辑不动」），landing 3.2 判据把 `...` 落实为同一式样。

### [存疑] C2-5 git 追踪文档以不入库的 AGENTS.local.md 节号作依据与验收判据，「ZZZ 仓」缩写无定义——仓库外读者不可解析

- 规范出处：AGENTS §10「git 追踪的文档只记录项目级使用内容，禁止个人本机内容」+「写文档用直白表述，禁自造黑话或项目内部缩写……首次出现的项目术语给定义 + 例子」
- 位置：design.md §1（「AGENTS.local.md §2.3 记载的实测事故」「不落地 ZZZ 仓的同类改动——只按 AGENTS.local §2.2 写同步件」）+ landing.md 末阶段（「按 AGENTS.local §2.2 模板」「若撞占用按 AGENTS.local §2.3 处置」「产出 ZZZ 同步件」）
- 证据：AGENTS.local.md 不入 git（本机文件，实测存在 §2.2「SR→ZZZ 同步」/§2.3「项目 MCP server 运维」），design/landing 是 git 追踪的迭代文档——以本机文件节号为设计依据与末阶段完成判据（「同步件与反馈件存在且按模板成形」），其他环境读者无法解析依据内容；「ZZZ 仓」（绝区零一条龙仓）首现无定义。缓解事实：本迭代目标由用户裁定、落地与验收均在本机单 agent 流程内执行，引用对本机 worker 可达；且 design §1 已对「明确不解决」给出 ZZZ 边界语义。
- 建议：在引用处各补一句内容摘要使其自包含（如「AGENTS.local §2.2 = SR→ZZZ 同步件模板（列出改动文件与移植要点）」「§2.3 = 端口占用处置」），「ZZZ 仓」首现处补「（绝区零一条龙仓，本机姊妹项目）」。

### [低级] C2-6 README 引用的 attack.md 当前不存在

- 规范出处：iteration-design.md §4（README 只串文档记进度——所串文档链接应可达）
- 位置：README.md「设计对抗:进行中 · 报告=[attack.md](attack.md)」
- 证据：实测迭代目录（2026-11-20）仅 README.md / design.md / landing.md / 本报告，无 attack.md。属对抗审在途的时序性悬空（核一报告未落盘），定稿门槛「攻击收敛」判定依赖该报告存在。
- 建议：核一报告落盘后链接自然闭合；若核一以其他文件名产出，同步改 README 链接。

### [低级] C2-7 design §0 保留「无详设」声明行，与附录 A 模板「无详设删本行」不符

- 规范出处：iteration-design.md 附录 A（总纲模板：文档清单行「（无详设删本行）」）
- 位置：design.md §0「文档清单：无详设（单文档方案，§2 即完整设计）」
- 证据：模板规定无详设时删除文档清单行；design 保留并作单文档方案自声明。保留比删除信息量更大（明示 §2 承载完整设计、深度按详设标准），属可辩护偏差，非硬规则（§5 四条不含此项）。
- 建议：维持现状可接受；若求模板严格一致则删行，由 §2 开头「（单文档完整设计）」承担声明。

### [低级] C2-8 design §2.1 代码块未区分新增行与现状行，改动面需读者自行 diff

- 规范出处：iteration-design.md §5-2（实现者无需再设计——改动面应无歧义）
- 位置：design.md §2.1 toml 代码块
- 证据：实测 pyproject.toml 现状：`[tool.uv]` 段已存在（package=false、cache-dir、environments、default-groups，48-51 行），无 [build-system]。代码块把 [tool.uv] 全段照贴，注释仅标「新增」于 [build-system]、标「原 false」于 package 行——cache-dir/environments/default-groups 三行系现状照贴未标注，实现者需对照现状文件自行分辨「两处改动」的文字说明与整段代码块的对应关系。
- 建议：代码块内加一行注释（如「# 以下 [tool.uv] 仅 package 行翻转，其余三行系现状」），改动面一目了然。

### [低级] C2-9 「src-layout 自动发现需 setuptools>=61」选型依据无出处

- 规范出处：iteration-design.md §5-1（依据就地标注——关键主张旁写明依据）
- 位置：design.md §2.1 第一定列点
- 证据：「构建后端选 setuptools（src-layout 自动发现需 setuptools>=61，取 >=64 留余量）」——版本门槛主张（>=61）无文档指针；同文档其余关键主张均有标注（如「uv 0.10.4 文档行为，阶段 1 实测复核」「实测确认」），此处独缺。
- 建议：补 setuptools 文档指针（自动发现机制引入版本），或标注「阶段 1 构建实跑即验证」。

### [低级] C2-10 quickstart 改动处申报「~5 处」为约数，实测 6 行

- 规范出处：iteration-design.md §5-4（文件面真实路径全量反查）
- 位置：design.md §2.2-③「docs/develop/setup/quickstart.md | IDE/命令行/环境设置段（~5 处）」
- 证据：实测 grep：quickstart.md 含 PYTHONPATH 6 行（48/49/59/60/91/102），均为需改口径（IDE 设置、命令行、GUI 启动、MCP 启动、pyright 说明），无反义句。约数偏小，worker 按数勾验有漏改风险（同文档 character-data skill「2 处」、ai_coding「1 处」均为实数且准确）。
- 建议：「~5 处」改「6 处」（或逐行号列出）。

### [低级] C2-11 末阶段改 sr_od_daemon.py 后未按「改任何 Python 代码须重启 MCP server」声明处置

- 规范出处：项目 AGENTS.md §6（改了任何 Python 代码都要重启项目 MCP server 才生效）+ iteration-design.md §3.1（影响面申报三层完整）
- 位置：landing.md 影响面申报「共享资源面」（重启事项仅关联阶段 1 的临时端口冒烟）
- 证据：末阶段文件面含 tools/mcp/daemon/sr_od_daemon.py（注释口径改动，属 Python 代码改动），共享资源面的重启说明只覆盖阶段 1（「不动常驻 24001 实例则无需重启它」），未对末阶段改 daemon 后常驻 server 是否重启作显式裁定。注释改动无行为差异，条件化处理有合理基础，但规范字面未覆盖——留白易被按 §6 字面追加无谓重启，或被质疑漏报。
- 建议：landing 共享资源面补一句显式裁定（「末阶段 daemon 仅注释改动，无行为差异，不重启常驻 server」）。

### [低级] C2-12 3.2 文件面未申报 PyInstaller 冒烟构建的产物目录

- 规范出处：iteration-design.md 附录 C（文件面 = 本阶段会动的文件/目录）
- 位置：landing.md 3.2「文件面：debug.bat」
- 证据：3.2 范围含「单独构建 OneDragon-RuntimeLauncher.spec」，构建必然产生输出目录（deploy 下构建产物），文件面仅列 debug.bat。产物目录在 .gitignore 内不入库，按「允许动的入库文件」口径可辩。
- 建议：文件面补一行「+ PyInstaller 构建产物目录（gitignore 内，不入库）」即完备。

## 逐项核查结论表

| # | 核查项 | 结论 |
|---|---|---|
| 1 | 文档构成：三件齐 / 详设声明与实际一致 / 单文档深度达标 | 三件齐（过）；无 details/ 目录与「无详设」声明一致（过）；单文档深度总体达详设级，唯 APPATH 推导式样缺口 → **C2-4**；声明行保留与模板偏差 → C2-7；代码块改动面歧义 → C2-8 |
| 2 | design 结构：§0 / §1 / §2 要素齐 /「明确不解决」边界 | §0/§1/§2 要素全齐（过）；「明确不解决」四条（打包方式/分包/历史过程件/ZZZ）边界划清（过）；§0 状态位失同步 → **C2-1** |
| 3 | landing 阶段小节七件（含末阶段）/ 常规检查首节自包含 | 3.1 / 3.2 / 末阶段七件逐件全齐（过）；「完成前常规检查」首节自包含定义、不引用规范不存在章节号、三阶段判据均引用不复述（过）；末阶段判据 = 清单清零 + quickstart 附加点（§2.3-3/4）齐（过）；共享资源面留白 → C2-11；3.2 文件面缺构建产物 → C2-12 |
| 4 | 正本更新清单格式与 design §2.2-③ 逐行对照 | 14 行对 ③ 13 行：currency-war 一行拆三行无遗漏、AGENTS.local/pyproject 注释等全对应（映射完整）；差异 = debug.bat 不在清单（自洽但与 ps1 归类标准矛盾）→ **C2-2**；③ 计数漏 2 处说明性提及 → **C2-3**；quickstart 约数 → C2-10 |
| 5 | 写作硬规则四条 | 依据就地标注：总体密集到位（文件:行号、实测标注、文档行为+复核安排），个别缺出处 → C2-9；实现者无需再设计：全文无「看情况/待定/酌情」，唯 APPATH 式样缺口 → **C2-4**；无过程叙事：design/landing 无「本轮/修订后/已改/上轮」类措辞（过）；README 只串文档记进度、design/landing 正文无进度无状态（过），链接悬空 → C2-6 |
| 6 | AGENTS §10 相关 | as-built 无状态：过——pyproject 片段属改动内容本身非运行阈值（合理）；「uv 0.10.4」版本快照已配「阶段 1 实测复核」防失效（合理）；正文无进度/变更史/状态位（§0 状态为规范合法字段）。changes/ 引用铁律：过——design/landing 居 changes/ 内，引用方向均为正本/skill/外部（合法方向），无 changes/ 外长期物被违规引用。术语定义：可编辑安装/build-system 首现均带定义或用途注释、src-layout 系项目 AGENTS 已用术语（过）；AGENTS.local 节号与「ZZZ 仓」不可解析 → **C2-5** |

统计：阻断 0 / 应修 4 / 存疑 1 / 低级 7，共 12 条。
