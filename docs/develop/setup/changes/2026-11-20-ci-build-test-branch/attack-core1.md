# 核一·无前提报告

审查对象：本目录 design.md、landing.md、README.md（2026-11-20 定稿稿）。
审查方法：不预设焦点，把三件当不可信文本；每个关键主张独立找证据——ZZZ 参照源逐行读、SR 仓与 GitHub 接口实测、GitHub 官方文档逐条核对。全部证据于 2026-11-20 采集。

级别定义（下文使用）：

- **阻断**：按现设计落地即产出错误结果或目标不可达，必须先改设计；
- **应修**：设计内容与事实不符或不完备，照做会留下缺陷或误导实现；
- **存疑**：无法单方定论，需用户裁定；
- **低级**：事实性小错、口径含糊，不阻碍实施。

## 结论摘要

**阻断 1 / 应修 4 / 存疑 0 / 低级 5**

最重的一条（B1）：设计对 GitHub Actions 平台行为的一处断言与官方文档相反，照落地判据实现后，测试闭环永远跑在停摆的 main 代码上而不是集成分支上，且错误被验收判据锁定。其余为：基线参数化点计数错误且漏掉的两处里有一处会污染提交署名（S1）、症状二「活线 CI 零覆盖」的覆盖时序未点破且一行配置的立即解未被取舍（S2）、BASE_BRANCH 需在两个文件重复定义的同步义务未声明（S3）、PR 基线分支与集成基线错位这一 SR 特有风险完全未分析（S4）。

## 逐条发现

### [阻断] B1 ·「workflow_run 事件下 github.sha 即 test 分支头」与平台事实相反，主仓 checkout 会落在停摆 main 上

位置：design.md §2.2-3（「主仓 checkout 不动：workflow_run 事件下 `github.sha` 即触发运行的 head_sha（test 分支头），checkout 默认行为已正确」）；landing.md 3.2（范围「不动主仓 checkout」＋完成判据「主仓 checkout 步骤无 ref 改动」）。

证据：

1. GitHub 官方文档「Events that trigger workflows」页 workflow_run 节的表格原文：该事件的 GITHUB_SHA = "Last commit on default branch"、GITHUB_REF = "Default branch"——即默认分支（本仓为停摆 main）的最后提交，不是触发运行的 head_sha。
2. GitHub Community 官方讨论 #48857（Tracing back through workflow runs to the original SHA）：要拿到上游运行对应的提交，必须用 `github.event.workflow_run.head_sha`。
3. GitHub Security Lab 指南（github-actions-preventing-pwn-requests）：workflow_run 触发的运行运行在默认分支上下文，actions/checkout 不传 ref 时检出的是默认分支，要检出触发代码必须显式 `ref: ${{ github.event.workflow_run.head_sha }}`。
4. ZZZ 参照源不覆盖此点：ZZZ 的 test-check.yml 只挂 pull_request 与 push 触发；用 workflow_run 的是 sync-cnb.yml，其做法是整仓裸 clone 后全量推送（git clone --bare），不做 checkout、不依赖 github.sha。「照搬 ZZZ 已验证机制」的说服力到不了这个点——这是 design 在无参照源的地形上自行推断，推断方向反了。

后果推演：本仓默认分支是 2026-07-29 停摆的 main。按 landing 3.2 的判据实现（主仓 checkout 不动），workflow_run 触发的 test-check 将检出停摆点的 main 代码，配上测试仓活线分支的测试——跑的是一个谁也没定义过的组合，测试结果与集成分支毫无关系。更糟的是这个错配可能表现为「正常地绿或红」，没有任何告警指向原因；且 landing 把「主仓 checkout 无 ref 改动」定为完成判据，等于用验收流程把错误锁死。闭环的核心环节（在 test 分支头上跑测试）不会发生。

建议：主仓 checkout 的 ref 改为 `ref: ${{ github.event_name == 'workflow_run' && github.event.workflow_run.head_sha || github.ref }}`——workflow_run 时取触发运行的 head_sha（test 分支头），pull_request 时取 github.ref（即 refs/pull/N/merge，与现状默认行为等价）、push 时取被推分支，三个事件行为均与现状一致（不要用 `|| github.sha` 兜底：pull_request 事件的 github.sha 是测试合并提交，显式传它会改变现状的检出内容）。若不想用嵌套表达式，可拆成两个条件互斥的 checkout 步骤。landing 3.2 的范围与判据必须同步改写：「不动主仓 checkout」与「主仓 checkout 步骤无 ref 改动」两句都要撤销。

### [应修] S1 · 基线参数化「三处」计数错误：ZZZ 脚本里 origin/main 作为 git 命令实参实际出现五处，漏掉的两处中一处会污染提交署名

位置：design.md §2.2-1（「适配：脚本取基线的两处（`git fetch origin main`、`git checkout -B test origin/main`、`git merge-tree origin/main`）参数化」）；landing.md 3.1（判据「除 BASE_BRANCH 参数化三处……外无语义差异」）。

证据：逐行读 ZZZ 仓 tools/ci/build_test_branch.py（全文 610 行，行数与 design 所称一致），`origin/main` 作为 git 命令实参出现 **5 处**：

| 行号 | 所在函数 | 命令 |
|---|---|---|
| L486 | rebuild_test_branch | `git fetch origin main` |
| L487 | rebuild_test_branch | `git checkout -B test origin/main` |
| L530 | rebuild_test_branch（冲突判定） | `git merge-tree --write-tree origin/main pr_ref` |
| L255 | get_related_prs | `git log --format=%B origin/main..HEAD -- <文件>` |
| L311 | get_commit_authors | `git log --reverse --format=%aN <%aE> origin/main..<PR ref>` |

另：design §2.2-1 内部文字自相矛盾——写「取基线的**两处**」却列出三项。

漏改后果分级：

- **L311（get_commit_authors，条件性必现的功能缺陷）**：该函数用「基线到 PR 头」的范围收集 PR 提交作者，供 squash 提交署名与 Co-authored-by 使用。参数化基线为活线后若此处仍写 origin/main，则凡 PR 分支包含活线提交（从活线分叉、或合入过活线）时，范围会把活线四个月的全部提交计入：每个 squash 提交的 Co-authored-by 会列出一长串活线作者、单作者 PR 被误判为多作者而改用发起人的 GitHub noreply 身份——design §2.1 声称的「squash 提交署名保留原作者」失效。实测当前抽查的 3 个 open PR（#612/#618/#604）分叉点都在 main 历史内、暂不触发；但活线是本仓实际开发线，从活线分叉的 PR 是常态形态，且休眠期内（design §2.3-1）没有任何首跑能暴露它，缺陷会潜伏到 main 治理之后才发作。
- **L255（get_related_prs，语义债）**：冲突报告「相关已合入 PR」的检索范围 origin/main..HEAD 在基线≠main 时起点错位（混入基线相对 main 的全部提交）。因基线的普通提交不含 "Squashed from PR" 文案，通常不会误报，但范围语义已经错了，且每个冲突文件都要无谓遍历四个月的提交历史。此函数只在冲突路径走到，影响面小于 L311。
- **文案（6 处用户可见文本 + 1 处 docstring）**：L271/L273/L281（「PR #N 与 main 冲突」「单独合入 main」叙述）、L424（摘要「基线:`main`」）、L431（「test 与 main 一致」）、L545（「无变更(已在 main 中)」）、L485（docstring「从 main 重建」）。基线是活线时这些报告文字全部失真，读者会把「对活线的冲突」读成「对 main 的冲突」——与 S4 的冲突叙述问题联动。

建议：design §2.2-1 把参数化点改为「git 命令中的基线引用共 5 处」并逐一列出（表格如上）；文案处理单列一小节（统一改「基线分支」措辞，或明确声明保留 ZZZ 原文并接受失真）；landing 3.1 判据的对照清单同步更新——现状判据「除三处外无语义差异」会把漏改合法化，实现者逐段对照时会把 L255/L311 当作「ZZZ 原样」放过。

### [应修] S2 · 症状二「活线 CI 零覆盖」的覆盖时序未点破；一行配置的立即可用解未被设计取舍

位置：design.md §1（症状 2 加粗强调「活线改动的 CI 覆盖为零」）、§2.2-2、§2.4、§2.3-1。

证据与推演：

1. 覆盖时序：§2 的解法链是「每日定时重建集成分支 → 完成后联动跑测试」。这条链整体休眠（§2.3-1：三类触发都要求 workflow 文件在默认分支，默认分支是停摆 main）。即落地后症状二依旧为零；main 治理后也只是每日一次的延迟快照验证，不是推送即验证。§1 的「解决到哪」段（「每日自动从基线重建……自动联动 test-check 跑全量测试」）读起来像落地即生效，与 §2.3-1 的休眠结论之间缺一句显式衔接——症状二在休眠期持续存在这一事实没有被点破。
2. 未被取舍的立即解：test-check.yml 增加一个触发 `push: branches: [feat/mcp-backend-sync2]` 即可让活线每次直推都跑测试。push 触发不要求 workflow 文件在默认分支（文件在被推的活线上即生效，与 schedule/workflow_dispatch/workflow_run 不同），落活线立即工作，不依赖 main 治理。§2.4 弃「test→活线常开 PR」过渡形态时只权衡了 PR 列表污染与 #612 的 build 标签交互，完全没有提及这个更轻的直接解。未写明理由的取舍按本次审查口径记为弱点。

建议：二选一并写进设计——要么补 `push` 触发活线（立即缓解症状二；代价是每次推送 10-20 分钟 windows runner，费用与频率需用户点头），要么在 §2.4 明确写下不采用的理由（如 runner 费用、活线推送频繁、休眠期短暂不值得过渡件）。同时在 §1 或 §2.3-1 把症状二的覆盖时序说透：落地后仍为零，治理后为每日快照。

### [应修] S3 · BASE_BRANCH 需在两个 workflow 文件里各自定义，同步义务未声明；测试仓 fallback 到 main 的口径错配无告警

位置：design.md §2.2-1（「workflow env 一处配置」「活线换代只改 workflow 这一行」）、§2.2-3（测试仓 ref 取 `${{ env.BASE_BRANCH }}`）；landing.md 3.2（范围与文件面均未列 env 块新增）。

证据：

1. SR 现状 test-check.yml 没有任何 env 块（实测文件开头只有 name 与 on 块）。landing 3.2 要让测试仓 checkout 取 `env.BASE_BRANCH`，就必须在该文件顶层新增 env 块定义 BASE_BRANCH——build-test-branch.yml 里的同名 env 是另一个文件里的独立定义，两个值没有任何机制保证一致。
2. 「活线换代只改 workflow 这一行」只对 build-test-branch.yml 成立；活线换代实际要同步改两个文件各一行。漏改 test-check.yml 这一处时，测试仓 checkout 取不到新分支，走现有的静默兜底（实测现状结构：一级 checkout `continue-on-error: true`，失败后二级步骤取 ref main，L45-65），跑「测试仓 main 的测试 × 活线代码」的错配组合。
3. design §2.3-3 只写了「保证面 = 基线测试套件对集成代码的回归」，没有讨论兜底触发时测试与代码错位的后果，也没有给任何观察兜底是否发生的手段（兜底是静默的，运行日志里不显眼）。

建议：landing 3.2 范围补「test-check.yml 顶层新增 env 块（BASE_BRANCH）」；design §2.2-1 把「只改这一行」改为「两个 workflow 文件的 BASE_BRANCH 必须同步修改」并声明漂移后果；可选加固：二级兜底步骤打一条 GitHub Actions warning 注解，让兜底发生时在运行摘要里可见。

### [应修] S4 · PR 的 base 分支与集成基线错位：SR 特有适配清单（「三处差异」）漏了这一项，冲突防线在当前仓形态下会被错位冲突淹没

位置：design.md §2.2（只列三处差异）、§2.3（风险清单无此项）。

证据（全部实测，2026-11-20 GitHub 接口）：

1. SR 当前全部 10 个 open PR 的 base 都是 main（停摆分支）：#618/#612/#607/#604/#603/#595/#591/#580/#578/#554。
2. 抽查 3 个 PR 的实际分叉点均在 main 历史内：#612 与 #618 的第一提交的 parent 就是 main 顶端提交（1ffd7e08）；#604 的分叉点（f24784b2）落后 main 顶端 3 个提交。
3. design 的集成基线是活线 feat/mcp-backend-sync2，领先 main 约四个月（§1 症状 3）。

推演：`git merge --squash <PR>` 合入「活线头 + 先前 PR」时，git 找的合并基底是 PR 的分叉点（落在 main 停摆点附近），三方合并的「基底→我方」一侧因此包含活线四个月的全部改动。只要 PR 触碰了活线改过的文件，冲突概率被系统性放大；活线本身不走 PR 直推（§1 症状 2），与 open PR 内容同域（例如 #604 主题「MCP backend 运行态完善」与活线分支名 feat/mcp-backend-sync2 直接同域），「同一件事的两份实现」相撞会成为常态。结果形态：这些 PR 每天被打上 test-conflict 标签跳过——防线每天重新撞一次墙，而 §1 症状 1 真正要防的「PR 之间的冲突」信号被淹没在「PR 对活线错位」的噪声里。ZZZ 没有这个问题：其 PR base = main = 默认分支 = 集成基线，四者一体；SR 移植后这四者裂成两半，design 未做任何分析。

建议：design §2.2 补第四处差异的分析与应对——最低要求是声明预期：「PR base 停留在 main 期间，test-conflict 标签里混入 PR 对活线基线的错位冲突，其数量可能远大于真正的 PR 间冲突」；更好的做法是定一条参与规则（参加集成的 PR 一律以活线为 base），或在冲突报告里区分两种冲突来源（脚本里 main_conflict 判定用的 merge-tree 对基线比对，参数化后判的是「PR 单独对活线」的情况，报告文案 L273/L281「单独合入 main 无冲突」的叙述随之失真——与 S1 的文案项联动修改）。

### [低级] L1 ·「main tip = CNB 同步 PR 的合并提交」与实测不符

位置：design.md §1 症状 3。

证据（实测）：main 顶端提交（1ffd7e08）为单 parent 提交、message「ci: 修复仓库名」、author_date 2026-07-29——不是合并提交（合并提交应有两个 parent）；提交信息里也没有任何「CNB 同步」痕迹。停摆日期与「无 test-check.yml」的事实本身核对无误。

建议：改为「tip 为 2026-07-29 的提交『ci: 修复仓库名』」，或注明归因来源后修正措辞。

### [低级] L2 · 定时触发的时间写法隐含准点，实际平台延迟可达数小时

位置：design.md §2.1（「schedule `0 20 * * *`（UTC，北京 04:00）」）、§2.4 时区条。

证据（实测）：GitHub 定时触发在高负载时段排队延迟。ZZZ Build Test Branch 近 5 次 schedule 运行的实际创建时间为 UTC 01:37～02:44（对应前一日 20:00 UTC 的计划，延迟约 3.7～5.6 小时），即北京时间上午 09:37～10:44 才跑。

建议：补一句「GitHub 定时触发高峰期延迟可达数小时（ZZZ 实跑 3.7～5.6 小时），北京 04:00 是计划时间非实跑时间」。

### [低级] L3 · README 进度口径与 landing 阶段结构不一致；报告索引未收本文件

位置：README.md「落地:阶段 0/2 done」「报告=attack.md」。

证据：landing.md 实际含 3.1、3.2、末阶段三个阶段；「0/2」分母与阶段数不符，「done」位置也易误读（实际含义是 0 个完成）。设计对抗报告已存在 attack.md（另一路），本报告 attack-core1.md 并存后 README 索引未反映。

建议：进度改为「阶段 0/3 done（3.1、3.2、末阶段）」；报告索引补 attack-core1.md。

### [低级] L4 · 判据引用的对照源不含其所列项目；「追加」一词与现状不符

位置：landing.md 3.1（判据「workflow 对照 design §2.1 表：……concurrency……」）；design.md §2.2-2（「job 级 `if` 追加」）。

证据：design §2.1 表实测未列 concurrency 项（只列 schedule、workflow_dispatch、permissions、owner 门控、runner）——判据所列的 concurrency 在其引用的对照源里不存在（判据自身列全了清单，执行无碍，属锚点引用不准）；SR test-check.yml 现状 job 无 if 字段（实测 L10-13），「追加」实为「新增」。

建议：对照锚点改为「ZZZ 源 workflow ＋ 本判据清单」；「追加」改「新增」。

### [低级] L5 ·「无 PR 时也每日跑一次全量测试」的行为未写明

位置：design.md §2.3-4（runner 费用）。

证据（读 ZZZ 脚本 L486-487、L544-546、L560-566 推演）：PR 列表为空时脚本照样从基线重建 test 分支并推送（空列表走完整流程、返回 0 → 运行结论 success）→ workflow_run 照常联动 → 每日一次全量 windows 测试（10-20 分钟）。该行为的两面都没写明：费用面（与有无 PR 无关的每日固定消耗）、价值面（此时 test 分支 = 活线当日头，联动测试恰好构成活线的每日回归，反而部分回应症状二）。

建议：§2.3-4 补一句「无 PR 时集成分支即基线当日头，联动测试构成活线每日回归，费用为每日固定一次全量」。

## 已核实为真的关键主张（正面记录，落地者可免复查）

- §1 的实查数据全部属实：SR 近 12 次运行全为「Auto Close Stale Issues」定时任务（2026-11-08～11-19，接口实测）；ZZZ Build Test Branch 近 6 次全 success（1 次手动触发 + 5 次定时）；PR #612 存在且 open（标题「ci: 同步发布流程」）；test 分支为 2025-11-02 ShadowLemoon 的「Merge branch 'main' into test」；main 停摆于 2026-07-29。
- §2.2-2 的两条平台事实为真：GITHUB_TOKEN 推送不触发 on.push 类 workflow（官方「Triggering a workflow」页原文："if a workflow run pushes code using the repository's `GITHUB_TOKEN`, a new workflow will not run even when the repository contains a workflow configured to run when `push` events occur"）；schedule / workflow_dispatch / workflow_run 三类触发均要求 workflow 文件在默认分支（官方「Events that trigger workflows」页三节各有原句）——§2.3-1 的休眠结论成立，且 landing 3.1「休眠边界如实」判据有据可依。
- §2.3-2 的补充事实：test 分支无保护规则（分支保护接口返回 not protected），强制重建不会被拒。
- §2.3-3「现配活线同名分支」属实：sr-od-test 远端现有 main 与 feat/mcp-backend-sync2 两个分支（接口实测）。
- 判据可执行性抽查：pyyaml==6.0.1 在项目依赖内（pyproject.toml），YAML 解析判据可跑；`.debug/temp/TODO.md` 已存在，3.1 的登记目标可达；ZZZ 脚本确为 610 行；tools/ 目录现状（mcp、wt.ps1，无 ci）与末阶段判据（AGENTS.md 补「ci」）吻合。
- 与在飞状态无冲突：当前分支 feat/mcp-backend-sync2 的未推提交与未提交改动均不含本迭代的 4 个目标文件（git status 实测）。唯一交叠是 test-check.yml 曾被另一迭代（uv 包安装化，阶段 3.3「CI 环境包与探针适配」，在未推提交中）修改——本迭代 3.2 基于当前工作区继续改即可，不构成冲突，但落地 3.2 时应意识到该文件近期有过一次未推的改动。

审查来源清单（平台行为主张的核验出处）：GitHub 官方文档「Events that trigger workflows」（docs.github.com/en/actions/using-workflows/events-that-trigger-workflows，workflow_run 节 GITHUB_SHA/GITHUB_REF 表格）、「Triggering a workflow」（docs.github.com/en/actions/using-workflows/triggering-a-workflow）、GitHub Community 讨论 #48857、GitHub Security Lab「Preventing pwn requests」（securitylab.github.com/research/github-actions-preventing-pwn-requests）、Stack Overflow #79941021；仓库侧证据均来自两仓文件实读与 GitHub 接口实测（详见各条）。
