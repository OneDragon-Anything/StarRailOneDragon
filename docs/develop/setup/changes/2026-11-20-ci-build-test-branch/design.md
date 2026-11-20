# CI 集成测试分支（Build Test Branch）迭代设计（总纲）

## 0. 元信息

- 迭代目标：用户裁定（2026-11-20 会话「A+B+C」）中的 C 项——移植 ZZZ 仓的集成测试分支机制（定时把带标签的 open PR squash 合入 `test` 分支并自动跑测试）。A 项（PR 构建通道）与 B 项（构建去重门控）经探索发现已由协作者 ShadowLemoon 的 open PR #612 完整实现，改走处置分析另案（`.debug/temp/PR612处置分析.md`，不入 git），不在本迭代范围。
- 状态：定稿（三轮收敛：一轮 13 条 + 二轮 8 条裁定全闭合，三轮零新增阻断/应修、低级 5 条随定稿顺手修）
- 文档清单：无详设（单文档方案，§2 即完整设计）

## 1. 问题与动机

- 现状症状：
  1. PR 各自过 test-check（pull_request 触发、单分支对 main 验证），**PR 之间的冲突与交互问题没有任何防线**——两个 PR 单独都绿、合在一起才炸的形态只能在合入后暴露；
  2. 本仓实际开发不走 PR：活开发线 `feat/mcp-backend-sync2` 直推（GitHub 仓库 push 记录至 2026-11-19），而 test-check 只挂 pull_request 与 push main 两个触发——**活线改动的 CI 覆盖为零**（2026-11-20 GitHub API 实查：全仓最近 12 次运行全部是每日关 issue 的定时任务，无一次测试/构建）；
  3. 仓库的 main 分支停摆于 2026-07-29（tip = PR #611 的 squash 合并产物，单 parent 提交「ci: 修复仓库名」），其上无 test-check.yml；活线与 main 已分叉四个月。
- 根因归层（流程层）：验证流程只有「单个 PR 对基线」一维，缺「多个待合改动相互叠加」的集成验证环节。同框架姊妹仓 ZZZ（ZenlessZoneZero-OneDragon）已有同型机制：`Build Test Branch` workflow + `tools/ci/build_test_branch.py`，每日 schedule 实跑中（2026-11-20 GitHub API 实查其近 6 次运行全 success，含手动触发一次；schedule 实跑有 3.7-5.6 小时平台延迟，实查同批数据）。
- 解决到哪：每日自动从基线分支重建 `test` 集成分支——带 `test-branch` 标签的 open PR 按 PR 号升序 squash 合入，与基线或先前 PR 冲突者打 `test-conflict` 标签跳过并生成冲突报告（文件/行号/相关 PR）；test 分支重建成功后自动联动 test-check 在 test 分支头上跑全量测试，测试失败落为带 `test-branch-red` 标签的 issue（自管理开/关，见 §2.2-2）。test 分支的 SR 侧消费方式即这条验证闭环（ZZZ 的 test 分支消费方是 CNB 镜像分发——CNB 渠道本仓 main 上也有 active 的 sync-cnb.yml，但其镜像源是停摆 main、活线没有该链路；治理后若 CNB 链路保留，test 分支可随镜像链自然分发，本设计不展开）。
- 定位声明（预备性占位，带战术权衡放行）：落地时点对上述三症状的改善为零——触发休眠（§2.3-1）+ 当前零个 PR 带 `test-branch` 标签 + 治理未决。激活后的治疗路径逐症状：症状 1 ← PR 群对齐基线后的每日集成验证（§2.3-2）；症状 2 ← 本迭代 3.2 的 push 触发扩展（立即生效部分，不受默认分支限制）；症状 3 ← 归前置治理件（本迭代明确不解决）。占位放行的理由：机制代码与 ZZZ 同源已验证、落地面小，先行入库使治理了结当日即可激活，避免治理后重新排期。
- 明确不解决：
  - **main 停摆治理**（活线与 main 合流、或切换默认分支）——本迭代的前置条件而非任务（§2.3-1），排期与负责人归用户与协作者协调（本机待办与处置分析件已登记）；
  - A+B（PR 构建通道、构建去重门控）——PR #612 已含完整实现，处置另案；
  - CNB 同步、RuntimeLauncher 分发、代码签名（#612 捆绑的产品级大件）；
  - 测试仓（sr-od-test）的集成分支同步——test 分支跑测试用的是测试仓基线分支的测试，open PR 各自新增的测试文件不在其中（§2.3-3 边界）；
  - ZZZ 侧任何改动（方向相反：本迭代是 SR 学习 ZZZ）。

## 2. 方案（单文档完整设计）

### 2.1 组件与来源

| 组件 | 动作 | 来源与验证状态 |
|---|---|---|
| `tools/ci/build_test_branch.py` | 新增，照搬 ZZZ 同名脚本（610 行）＋基线参数化适配（§2.2-1） | ZZZ 实跑验证件（每日 schedule success，§1 证据）；机制：从基线重建 test 分支、逐 PR `git merge --squash`、冲突检测（index 未合并文件 + `git merge-tree` 判对基线冲突）、squash 提交署名保留原作者、`gh` 打标签、Step Summary 报告、`git push --force origin test` |
| `.github/workflows/build-test-branch.yml` | 新增，照搬 ZZZ 同名 workflow＋env `BASE_BRANCH` | ZZZ 实跑验证件；schedule `0 20 * * *`（UTC，北京 04:00；平台实跑延迟 3.7-5.6 小时，集成分支不追准点）＋workflow_dispatch（`prs` 手动列表输入）；concurrency（`group: ${{ github.workflow }}`、cancel-in-progress: false）；permissions contents/pull-requests/issues write；`if: github.repository_owner == 'OneDragon-Anything'`；ubuntu-latest 跑 `python3 tools/ci/build_test_branch.py` |
| `.github/workflows/test-check.yml` | 修改：push 触发扩展 + workflow_run 触发 + 主仓 checkout 显式 ref + 测试仓 checkout 三事件覆盖 + 失败 issue 通知 | **全新接线，无 ZZZ 先例**（ZZZ 的 test 分支消费方是 CNB 分发、其 pytest 自 2026-08 起禁用）——静态判据 + 唤醒后首跑验收承担（§2.3-1） |

### 2.2 SR 特有适配（与 ZZZ 的差异点）

1. **基线参数化（BASE_BRANCH），全量清单**：ZZZ 的基线硬编码 `origin/main`（其 main 是活线）；SR 的 main 停摆、活线为 `feat/mcp-backend-sync2`——照搬会把四个月前的代码建成集成分支，完全错误。参数化范围（ZZZ 源件行号为 2026-11-20 版本）：
   - git 命令实参 **5 处**：`rebuild_test_branch` 内 fetch（L486）、`checkout -B test`（L487）、`merge-tree` 冲突判定（L530）；`get_related_prs` 的 `git log origin/main..HEAD`（L255，冲突报告定位相关 PR）；`get_commit_authors` 的 `git log --reverse origin/main..{pr_ref}`（L311，squash 署名作者清单——漏改则 PR 自活线分叉时 Co-authored-by 列入活线四个月全部提交者，署名污染）；
   - 用户可见文案与 docstring 中的 main 字样（冲突报告标题、Step Summary 基线行、build-test-branch.yml 头注释的 origin/main 表述等）随基线变量改；
   - 收口口径：脚本内 git 实参与文案不再含硬编码 main 基线——`grep -n "origin/main"` 零命中（拦 `origin/main` 连写形态），`grep -n '"main"'` 命中仅 1 处且为 `os.environ.get("BASE_BRANCH", "main")` 默认值行（拦 `"origin", "main"` 分离实参形态与文案裸字符串）。
   两个 workflow（build-test-branch.yml 与 test-check.yml）**各自**声明同名 env `BASE_BRANCH: feat/mcp-backend-sync2`——GitHub 的 env 不跨 workflow 共享；活线换代改两处 env 行（同步义务，漏改侧静默按 main 口径运行无告警，§2.3-6）。
2. **测试闭环（workflow_run 联动 + 失败 issue）**：build_test_branch.py 用 GITHUB_TOKEN 推 test 分支，而 GITHUB_TOKEN 的推送**不会触发 on.push 类 workflow**（GitHub 防递归规则；ZZZ sync-cnb.yml 头部注释同证此行为，其为此用 workflow_run 补齐）。闭环两件：
   - test-check 挂 `on.workflow_run: workflows: ["Build Test Branch"], types: [completed]`，job 级 `if` 新增 workflow_run 成功过滤（失败重建不跑测试）；
   - **失败去向**：test-check 现有失败出口仅日志 notice（定时触发的失败无天然关联人）。升级为 issue 自管理指示灯——失败步骤以 `if: failure() &&`（workflow_run 触发条件）**限定集成分支事件**（指示灯只反映集成分支；push/pull_request 失败维持 notice 日志层——其有关联人：推送者与 PR 作者），用 gh 创建或评论带 `test-branch-red` 标签的 issue（附运行链接与分支头 sha）；成功收尾步骤以 `if: success() &&`（workflow_run 触发条件）**显式**声明（不依赖 if 的隐式 success() 规则），仅 workflow_run 触发时关闭该标签全部 open issue。标签由步骤首跑自建（`gh label create --force` 幂等）。
3. **test-check 三事件接线**：
   - 触发：`push: branches: [main, feat/mcp-backend-sync2]`（活线直推即时获得 CI——push 触发不受默认分支限制）＋ workflow_run（§2.2-2）；test-check 补 concurrency：`group: test-check-${{ github.event.workflow_run.head_sha || github.ref }}`、cancel-in-progress: true——分组键取触发头 sha（workflow_run）或事件 ref（其余），防活线高频推送堆积；不用裸 `github.ref` 的原因：workflow_run 事件的 `github.ref` = 默认分支 ref，会与 push main 同组互挤（cancel-in-progress 互杀）；
   - 主仓 checkout 显式 `ref: ${{ github.event.workflow_run.head_sha || github.ref }}`——workflow_run 事件的 `github.sha` 是**默认分支头**而非触发运行头（GitHub 官方 events 文档原文 "Last commit on default branch"），不写 ref 会检出停摆 main 跑测试；非 workflow_run 事件 head_sha 为空、回退 github.ref（pull_request = 合并 ref、push = 推送分支），行为不变；
   - 测试仓 checkout：pull_request → `github.head_ref`（现状不变）；push → `main`（现状不变）；workflow_run → `env.BASE_BRANCH`，取不到 fallback `main`（沿用 continue-on-error + 后续 fallback 步骤模式）。

### 2.3 风险与边界

1. **默认分支前置（硬阻断，落地≠生效）**：schedule、workflow_dispatch、workflow_run 三类触发都要求 workflow 文件位于默认分支（GitHub 平台行为），默认分支是停摆的 main——本迭代文件落活线后**这些触发全部休眠**，直到 main 治理了结（合流或切默认分支）。落地验收分两层：静态可验部分（本迭代判据）与 CI 实跑部分（前置满足后首跑核对）。唤醒验收两步走：首跑只验「机制跑通」（分支重建 + 联动触发 + issue 通知路径可达），**基线修红单独走**——test-check 自身 3.5 个月零运行、最后一跑失败（2026-08-07），唤醒后首跑大概率红，修红完成前本机制不当作防线使用（ZZZ 曾以「告警从不成功就是噪音」为由禁用其 pytest，前车之鉴）。pull_request 类触发不受默认分支限制（用合并结果的文件），但本迭代**新增的触发**（schedule / dispatch / workflow_run / push 扩展）不依赖 pull_request 事件——test-check 现有 pull_request 触发保留不动，build-test-branch.yml 不挂 PR 触发。
2. **PR 基线对齐前置**：实测 10 个 open PR 的 base 全是停摆 main，与集成分支基线（活线）错位——squash 三方合并基底落在 7 月分叉点，活线四个月改动全部参与合并，错位 PR 会被冲突墙淹没。机制对此容错（冲突跳过 + `test-conflict` 标签 + 报告），但错位面大时近乎全跳、报告全是噪音。**防线实际作用始于 PR 群对齐后**（治理了结 + 存量 PR rebase 到新基线）。
3. **测试覆盖边界**：test 分支上跑的是测试仓 BASE_BRANCH 分支（现配活线同名分支）的测试——open PR 各自新增的测试不在其中（测试仓分支同步无自动化，ZZZ 亦无此机制）。集成验证的保证面 = 代码层冲突检出 + 基线测试套件对集成代码的回归。激活后零标签 PR 期 test 分支 = 基线快照，每日全量即活线每日回归——这是机制激活初期对本仓的实际价值面，也是 runner 费用的主要去向。
4. **runner 费用**：每日 ubuntu 轻量建分支（秒级）＋test-check 全量一次（windows runner，约 10-20 分钟）；3.2 的 push 触发扩展使活线每次直推各触发一次全量（concurrency 取消同分支旧跑，堆积有上限）。
5. **权限与工具链**（按 workflow 分列）：
   - build-test-branch.yml：contents / pull-requests / issues 三写权限（建分支/建标签/维护 PR 标签，照搬 ZZZ）；
   - test-check.yml：现状 permissions 仅 `contents: read`——需**新增 `issues: write`**（失败 issue 的 gh 创建/评论/关闭与 `test-branch-red` 标签自建都要；缺它 gh issue create 直接 403，红灯通知静默失效）；gh 认证由步骤 env `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` 提供；
   - ubuntu 与 windows runner 均预装 gh CLI 与 python3（ZZZ 同配置实跑佐证）；标签 `test-branch`/`test-conflict` 由脚本 ensure_labels 首跑自建，`test-branch-red` 由失败通知步骤首跑自建，无需手工预置。
6. **BASE_BRANCH 双处同步**：两个 workflow 各自的 env 是两份拷贝，活线换代需同步改两行；漏改一侧按 main 口径静默运行（测试仓 checkout 落 fallback main、集成分支基线错）无平台告警——正本 repositories.md 记录该同步义务（见 landing「正本更新清单」）。

### 2.4 关键取舍

- **照搬 vs 重写**：脚本与建分支 workflow 照搬 ZZZ 实跑验证的实现（每日 schedule success，§1 证据），SR 侧只动基线参数化；**闭环接线（workflow_run 联动 + 失败 issue）是全新代码**，无 ZZZ 先例——不自称「照搬已验证」，靠静态判据与唤醒后首跑验收。
- **失败通知走 issue 而非日志/外部 webhook**：日志 notice 无天然关联人（定时触发无触发者）；外部 webhook（IM 群）无现成基础设施。issue 自管理开/关 = 零外部依赖、可见性好、绿转红自动熄灯。
- **不写单元测试**：脚本行为契约 = ZZZ 源实现（同源照搬）＋SR 首跑验收；可单测的纯函数面窄（手动 PR 列表解析、冲突标记行号解析），按测试规范「只测核心」不值当。若首跑暴露 SR 适配缺陷，修复时按「真实故障锁测试」原则补。
- **弃「活线切 PR 流」**：pull_request 触发不受默认分支限制、立即生效、零代码——但把直推习惯改成 PR 流是团队流程迁移（治理层选项，归用户裁定），非本迭代件；本迭代用 push 触发扩展（§2.2-3）拿到同等的活线 CI 覆盖。
- **弃「人工叠加验证」**：open PR 流量极低（10 个存量、零标签），人工本地叠加当前可行——但不可持续且依赖个人纪律，机制化才可靠；每日 schedule 的意义正在于不依赖人记得。
- **弃「test→活线常开 PR」过渡形态**（main 停摆期唯一能跑的 pull_request 触发路径）：常开 PR 污染 PR 列表、与 #612 的 `build` 标签机制交互、治理了结后失去存在价值——休眠等前置，不做过渡形态。
- **时区与准点**：schedule `0 20 * * *` UTC（北京 04:00）沿用 ZZZ；平台实跑延迟 3.7-5.6 小时（ZZZ 实测同批），集成分支不追准点，接受。
