# 核二·规范遵循报告

- 审查对象：本迭代 design.md / landing.md / README.md（2026-11-20）
- 审查依据：`docs/develop/harness/iteration-design.md`（下称「迭代文档规范」）、项目 `AGENTS.md`、ZZZ 仓（ZenlessZoneZero-OneDragon）被照搬源件与 `docs/develop/setup/repositories.md` 原文
- 审查方式：逐份读原文＋逐条对照规范；引用锚逐一实存核验（SR 侧与 ZZZ 侧文件均亲自读过）

## 结论摘要

- 阻断 2 / 应修 0 / 存疑 1 / 低级 3
- 总评：文档骨架完全合规（构成、七件、无过程叙事、无黑话、三处同步与锚存在性基本全过），但设计正文的「基线参数化」与「测试仓取分支」两处方案描述存在语义空洞与自相矛盾，按落地判据逐字执行会把缺口锁进实现——两条均为「实现者无需再设计」门槛（迭代文档规范 §5.2）不过，需修订后才能定稿。

## 逐条发现

### [阻断] B1 基线参数化清单不全，且 design 与 landing 计数互相矛盾

- **规范出处**：迭代文档规范 §5.2「实现者无需再设计」（实现者遇到的每个语义选择都能在设计里找到答案）；§5.4「修订后全量同步复查」（design 内部与 design↔landing 口径须一致）。
- **位置**：design.md §2.2-1；landing.md 3.1「范围」与「完成判据」第 2 条。
- **证据**：
  1. design §2.2-1 原文写「脚本取基线的**两处**（`git fetch origin main`、`git checkout -B test origin/main`、`git merge-tree origin/main`）」——「两处」后列了**三项**；landing 3.1 两处均写「**三处**（fetch/checkout/merge-tree）」。同一事实两个计数，且 design 自身计数与所列内容不符。
  2. ZZZ 源件 `ZenlessZoneZero-OneDragon/tools/ci/build_test_branch.py` 中以 `origin/main` 为基线的 git 引用实有 **5 处**：L486（fetch）、L487（checkout -B）、L530（merge-tree）、**L255（get_related_prs：`git log origin/main..HEAD`）**、**L311（get_commit_authors：`origin/main..pr_ref`）**——后两处 design/landing 均未列出。
  3. 另有多处面向用户的输出文本与注释写死 main：L271/273/279/281（冲突报告文案「与 main 冲突」「单独合入 `main`」）、L424（Step Summary「基线:`main`」）、L431（「`test` 与 `main` 一致」）、L545（「无变更(已在 main 中)」）；照搬对象 ZZZ workflow（`.github/workflows/build-test-branch.yml`）头部注释也写死「每次都从 origin/main 重新开始」。
  4. landing 3.1 完成判据原文「除 BASE_BRANCH 参数化三处……外**无语义差异**」——逐字执行即把 L255/L311 留在 `origin/main`。后果：当 open PR 的分支基于活线 `feat/mcp-backend-sync2` 时，L311 的区间会把活线四个月的全部提交作者算进该 PR，`commit_pr` 在多作者时给每人追加一行 Co-authored-by 署名（L363-364）——与 design §2.1 自己声称的「squash 提交署名保留原作者」直接冲突；L255 同理按错误区间扫描（结果靠正则过滤侥幸不失真，但语义漂移）；「基线:`main`」等文案在基线为活线时误导读者。
- **建议**：design §2.2-1 补全参数化口径——5 处 git 基线引用逐处列明改不改（L255/L311 建议一并参数化）；输出文本与 workflow 头注释里的 main 措辞要么随基线名参数化、要么显式裁定保留并写明理由；修正「两处」计数。landing 3.1 范围与判据同步改为与 design 一致的清单。

### [阻断] B2 test-check.yml 里 `env.BASE_BRANCH` 无定义来源，且与「活线换代只改一行」声明矛盾

- **规范出处**：迭代文档规范 §5.2「实现者无需再设计」；§5.4「全量同步复查」（design 两节之间口径互相矛盾）。
- **位置**：design.md §2.2-1 与 §2.2-3；landing.md 3.2「范围」与「完成判据」。
- **证据**：
  1. §2.2-3 要求测试仓取分支表达式用 `${{ env.BASE_BRANCH }}`——该表达式写在 test-check.yml 里，而 BASE_BRANCH 只在 §2.2-1 规定的 **build-test-branch.yml** 的 env 中配置。GitHub Actions 的环境变量（env）不跨 workflow 共享：test-check.yml 不自带一份定义，表达式求值为空 → 取测试仓分支失败 → 按既有 continue-on-error 兜底结构**静默**改用 main 分支的测试。更糟的是 landing 3.2 判据原文就写着「失败 fallback `main`」——错误路径恰好满足判据，实现错了也验不出来。
  2. 若实现者在 test-check.yml 里补一份 `env: BASE_BRANCH: feat/mcp-backend-sync2`（表达式能工作的唯一途径），则与 design §2.2-1「活线换代**只改 workflow 这一行**」矛盾——届时换代要同步改两个 workflow 文件各一处，漏改一处即两仓基线错位。
  3. landing 3.2「范围」只提触发器与取分支表达式扩展，未提 env 定义，文件面信息同样缺失该语义选择。
- **建议**：design 明确 BASE_BRANCH 在 test-check.yml 的来源与同步义务（推荐：test-check.yml 自带同名 env 一份，§2.2-1 的「只改一行」改为「改两个 workflow 文件各一行、须同步」，并写明为什么不用别的传值方式）；landing 3.2 范围与判据补「test-check.yml 含 BASE_BRANCH env 定义」对照点。

### [存疑] Q1 机制使用知识无正本归宿，正本更新清单仅一行

- **规范出处**：AGENTS.md「文档规范」知识归位判据（描述我们的系统 → 设计文档区正本）＋「双层文档流」铁律（changes/ 不定期删减、正本必须自足）；迭代文档规范 §3.2 正本更新清单。
- **位置**：landing.md「正本更新清单」（仅「AGENTS.md §1.1 目录结构 tools/ 行（补 ci）← 3.1」一行）。
- **证据**：本机制引入协作者要用的概念——给 PR 打 `test-branch` 标签即每日自动合入 test 分支跑集成测试、`test-conflict` 标签含义、默认分支治理完成前触发器休眠——这些知识目前只活在 changes/ 三件与被照搬的 workflow 文件头注释里。对照先例：ZZZ 在其 `docs/develop/setup/repositories.md`「CNB 镜像」节正本记载了 test 分支镜像链路；姊妹迭代 `2026-11-20-uv-package-install` 的影响面含 `docs/develop/setup/quickstart.md`、`ai_coding.md`、`.github/dev.md` 等正本同步件。changes/ 清理后，本仓正本（docs/develop/setup/ 下）无任何一处记载该机制。
- **建议**：提请设计者裁定——要么在正本更新清单补一行（在 docs/develop/setup 增设或扩充一篇 CI 说明），要么在设计里显式声明「机制知识由 workflow 文件头注释承载」并把头注释的维护义务写进 3.1 判据。属归宿裁量，不阻断。

### [低级] L1 依据转述超出 ZZZ repositories.md 原文，且引用未冠仓路径前缀

- **规范出处**：迭代文档规范 §5.1「依据就地标注」（依据＝来源文档＋节，转述须忠实、可定位）。
- **位置**：design.md §1「解决到哪」段。
- **证据**：design 写「ZZZ repositories.md 载明其 test 分支靠 sync-cnb 镜像到 CNB **供测试者使用**」。核实 ZZZ `docs/develop/setup/repositories.md`「CNB 镜像」节：镜像链路属实（「sync-cnb.yml 负责把 GitHub 分支和 Tag 镜像到 CNB……Build Test Branch 成功完成也会触发一次（workflow_run）」），但全文无「供测试者使用」表述——总览表里 CNB 镜像的用途原文是「国内代码镜像、Release 附件镜像／发布链路维护」。「供测试者使用」是推断，冠以「载明」即超出源文。另该处引用只写「docs/develop/setup 同类记录」，未像前文「ZZZ 仓 `tools/ci/...`」那样冠仓前缀，按本仓路径解读会落空。
- **建议**：改为源文口径（镜像链路＋用途栏原文），推断部分去掉「载明」或另标为推断；引用补「ZZZ 仓」前缀。

### [低级] L2 阶段小节标题层级与迭代文档规范模板不一致

- **规范出处**：迭代文档规范 §3.1（阶段小节模板为 `### 3.x <阶段名>`）。
- **位置**：landing.md 3.1/3.2 两节标题（用 `## 3.1`）。
- **证据**：模板规定三级标题，本文件与上一迭代（uv-package-install landing）均用二级；模板附录 C 自身「末阶段」也用 `##`，属规范模板自身不统一、且已被两代迭代沿用的本地样式。
- **建议**：不改本迭代（样式统一、无引用歧义）；建议后续修订迭代文档规范模板，把阶段小节层级与末阶段对齐。

### [低级] L3 CI 实跑核对的遗留义务只登记在不入 git 的临时文件

- **规范出处**：迭代文档规范 §6 收敛判据（存疑/低级记遗留随收口）与 §4（进度/遗留归 README 与账本）；AGENTS.md「文档规范」（不入 git 的本机文件不承担项目级长期内容）。
- **位置**：design.md §2.3-1、landing.md 3.1 完成判据第 5 条（两处均指向 `.debug/temp/TODO.md`）。
- **证据**：「默认分支治理完成后首跑核对 CI」这一义务只寄存在 `.debug/temp/TODO.md`（已确认该文件现存在于本机，但 .debug/temp 不入 git、随清理即失），README 进度与账本均无对应登记。
- **建议**：在迭代 README 进度区或进度账本同步登记该遗留（一句「CI 实跑验证：待默认分支前置满足后首跑」即可），临时文件只作展开。

## 核过无发现（检查覆盖清单）

- **文档构成（四节齐）**：README＋design 总纲＋landing 齐；详设按需为无（design §0 已声明单文档方案，§2 即完整设计）——合规。
- **阶段小节七件**：3.1/3.2/末阶段三节，范围/设计依据/文件面/依赖/优先级建议/完成判据/验收凭据形式七件全齐；末阶段=正本更新且判据=清单清零——合规（标题层级见 L2）。
- **写作硬规则**：①依据就地标注总体到位（GitHub API 实查、ZZZ 仓文件、日期均随主张标注；例外见 L1）；②无需再设计——两处不过（B1/B2）；③无过程叙事——grep「本轮/修订后/待定/看情况/TBD/酌情/第 N 轮/上稿/已改」三件全零命中；④全量同步——除 B1/B2 两点外全过（见下）。
- **design↔landing↔README 同步**：影响面四文件（脚本/两 workflow/AGENTS.md）与 design §2.1 三组件＋末阶段一一对应，各阶段文件面覆盖无遗漏；判据引用的节号（§2.1、§2.2-1/2/3、§2.3-1/2/3/5、§2.4、AGENTS.md §13、「正本更新清单」节）全部真实存在；README「迭代设计:对抗审中」与 design §0 状态一致。
- **阶段计数口径**：README「落地:阶段 0/2 done」＋单列「正本更新:未开始」——landing 恰有 3.1/3.2 两个落地阶段＋固定末阶段；上一迭代 README「阶段 3/3 done」＋「正本更新:清零」同口径（y 只计落地阶段，末阶段单列）。自洽，合规。
- **landing 首节对照附录 C**：ruff 限本阶段 `.py` 文件、pytest 与测试仓同步两项标不适用并附理由（design §2.4）、提交纪律四要素齐、来源行在；「检查项来源」引用的 AGENTS.md「测试规范」「提交流程与协作边界」两节真实存在；commit 措辞「含阶段号」（无「任务 id」）与上一迭代先例一致，属合法本地化。无虚构章节号。
- **changes/ 铁律**：三件均未引用其他 changes/ 路径；design 对另案处置只引 PR 号与 `.debug/temp`（非 changes/）——合规。
- **AGENTS.md 文档规范其余**：章节带序号（design §0–§2、landing 3.x 沿模板惯例）；无自造黑话（squash/workflow_run/Step Summary 等为 git 与 GitHub Actions 通用术语，「活线」首次出现即展开为「活开发线 feat/mcp-backend-sync2」）；知识归位——CI 机制非游戏知识不涉 docs/game（正本缺口另记 Q1）。
- **注释规范（ZZZ 源件照搬带入）**：`build_test_branch.py` 全部注释/docstring 为中文；无变更史叙事、无会话局部标识符（轮次号/批次号类）、无「日期＋实机」式标记与案例叙事；docstring 为单行行为契约属函数文档惯例，照搬引入不构成违规。随 B1 修订时建议在参数化各处补一句「为什么」（SR main 停摆、集成分支基线取活线）。
- **提交流程节**：landing 首节已覆盖逐文件点名 git add、禁 `-A`/目录级、commit 含阶段号、`git show --stat` 复核——合规。
- **引用锚实存**：SR 侧 `.github/workflows/test-check.yml` 存在且现状与设计描述相符（取分支表达式 pull_request 用 `github.head_ref` 其余落 main；continue-on-error＋兜底步骤结构；import 探针步骤在；主仓 checkout 无 ref）；`.debug/temp/PR612处置分析.md`、`.debug/temp/TODO.md` 本机实存；`AGENTS.md` 在。ZZZ 侧 `tools/ci/build_test_branch.py`、`.github/workflows/build-test-branch.yml`（内容与 design §2.1 表逐项相符，含 concurrency `group: ${{ github.workflow }}`/`cancel-in-progress: false`、owner 门控、permissions 三项写权限、ubuntu＋python3）、`sync-cnb.yml` 头部注释（与 design §2.2-2 引证相符）、`docs/develop/setup/repositories.md` 均实存。SR 仓 GitHub 远端属 OneDragon-Anything 组织，照搬的 owner 门控对本仓成立。README 引用的 attack.md 尚未落盘——对抗审进行中属预期（本报告即分核产物），不计发现。
