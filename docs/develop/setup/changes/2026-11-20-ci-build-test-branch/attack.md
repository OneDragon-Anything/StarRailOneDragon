# 设计对抗汇总

## 三核报告

- 核一·无前提：[attack-core1.md](attack-core1.md) —— 阻断 1 / 应修 4 / 存疑 0 / 低级 5
- 核二·规范遵循：[attack-core2.md](attack-core2.md) —— 阻断 2 / 应修 0 / 存疑 1 / 低级 3
- 核三·治本核验：[attack-core3.md](attack-core3.md) —— 阻断 1 / 应修 4 / 存疑 2 / 低级 1

核一 B1 的平台事实主张（workflow_run 事件下 GITHUB_SHA = 默认分支头）经编排者对照 GitHub 官方 events 文档独立核实，原文 "Last commit on default branch"——成立。

## 合并裁定与处置（去重后，级别取三核最高）

| # | 级别 | 发现（合并来源） | 裁定 | 落点 |
|---|---|---|---|---|
| 1 | 阻断 | workflow_run 事件下 `github.sha` = 默认分支头（官方文档证实），design §2.2-3「checkout 默认行为已正确」推断反了——闭环触发时 test-check 检出停摆 main（2026-07-29）跑测试，结果与集成分支无关且无告警，并被判据「主仓 checkout 无 ref 改动」锁死（核一 B1） | 主仓 checkout 加显式 `ref: ${{ github.event.workflow_run.head_sha \|\| github.ref }}`——非 workflow_run 事件 head_sha 为空、回退 github.ref（pull_request = 合并 ref、push = 推送分支），三事件行为均不变；判据同步改 | design §2.2-3 / landing 3.2 |
| 2 | 阻断 | 基线参数化清单不全：ZZZ 脚本 `origin/main` 作 git 实参 **5 处**（fetch L486 / checkout -B L487 / merge-tree L530 / get_related_prs L255 / get_commit_authors L311），另有用户可见文案与 docstring 中的 main 字样；design「三处」计数错误且自身「两处/三项」矛盾；`get_commit_authors`（L311）漏改 = PR 自活线分叉时 Co-authored-by 列入活线四个月全部提交者（署名污染，休眠期无首跑、潜伏到治理后才发作）（核二 B1 / 核一 S1） | §2.2-1 全量列清单（5 实参处 + 文案/docstring）；landing 3.1 收口判据改 grep 口径（`origin/main` 与裸 main 文案清零，唯 BASE_BRANCH 默认值字面量合法），不再枚举「除 N 处外」 | design §2.2-1 / landing 3.1 |
| 3 | 阻断 | `env.BASE_BRANCH` 在 test-check.yml 无定义来源（GitHub env 不跨 workflow），照写求值为空 → 静默 fallback main，恰好验不出；「活线换代只改一行」不成立（要改两个文件）（核二 B2 / 核一 S3） | 两个 workflow 各配同名 env `BASE_BRANCH: feat/mcp-backend-sync2`；design 声明两处同步义务与静默错配风险；「只改一行」表述改「改两处 env 行」 | design §2.2-1/3 / landing 3.1/3.2 |
| 4 | 阻断 | 测试闭环缺最后一环：test 分支测试红了无去向——test-check 失败出口仅日志 notice，定时触发的失败无天然关联人；SR test-check 自身 3.5 个月零运行、最后一跑（2026-08-07）失败，唤醒后首跑大概率红且无人消化；ZZZ 从未在 test 分支跑过测试（其 pytest 2026-08 起禁用，理由原文「一个告警从来都不成功就是噪音」），workflow_run 联动是无先例推断（核三 B1） | 失败通知落地成 issue：test-check 失败步骤升级——失败时 gh 创建或评论带 `test-branch-red` 标签的 issue（附运行链接）；workflow_run 触发成功时关闭该标签全部 open issue（自愈指示灯）。唤醒验收改两步：首跑「机制跑通」与「基线修红」分离，修红完成前不当作防线 | design §2.2-2 / landing 3.2 / repositories.md（正本） |
| 5 | 应修 | PR 基线错位：实测 10 个 open PR 的 base 全是停摆 main，与集成分支基线（活线）错位——squash 三方合并基底落在 7 月分叉点，活线四个月改动全部参与合并，冲突墙淹没真冲突；机制对此容错（跳过+标签+报告）但错位面大时近乎全跳（核一 S4） | 写入第二层前置：治理了结后存量 PR 需 rebase 到新基线；错位期行为如实（冲突跳过+报告噪音，防线实际作用始于 PR 群对齐后） | design §2.3（前置 2） |
| 6 | 应修 | 症状 2（活线 CI 零覆盖）有立即生效的免费解未采纳：test-check 加 `push: branches: [main, 活线]`（push 触发不受默认分支限制）（核一 S2） | 采纳：3.2 范围加入 push 触发扩展 + test-check 补 concurrency（`group: test-check-${{ github.ref }}`、cancel-in-progress: true，防活线高频推送堆积）；§2.4 补取舍（每日推送各触发一次全量，费用换覆盖） | design §2.2/2.4 / landing 3.2 |
| 7 | 应修 | 「本仓无 CNB 渠道」与事实相悖——main 上有 active 的 sync-cnb.yml（镜像源是停摆 main），同会话处置分析件自己记录了它（核三 F1） | 改为：CNB 镜像渠道存在于 main、活线没有；test 分支的 SR 侧消费 = 测试闭环（治理后若 CNB 链路保留，test 分支可随镜像链自然分发——一句联动说明，不展开） | design §1 |
| 8 | 应修 | 「照搬已实跑验证」话术掩盖闭环接线是全新未跑代码（核三 F4） | 表述两分：脚本 + 建分支 workflow = ZZZ 实跑验证（每日 success 证据）；闭环接线（workflow_run 联动 + 失败 issue）= 全新无先例，静态判据 + 唤醒后首跑验收承担 | design §2.1 / §2.4 |
| 9 | 应修 | 机制使用知识（标签语义 / 休眠前置 / 唤醒验收）无正本归宿，跨人跨机不可见（gitignored TODO 是唯一载体）（核二 Q1 / 核三 F3） | 新建 `docs/develop/setup/repositories.md`（ZZZ 同名先例形态）：分支模型（main / 活线 / test）+ CI workflow 清单 + test 分支机制（标签语义、BASE_BRANCH、休眠前置与唤醒验收清单、test-branch-red issue 标签）；正本更新清单补行；README 进度行同步「生效验证:待前置」 | landing 正本清单 / README |
| 10 | 应修 | §2.4 备选取舍面缺「活线切 PR 流」（pull_request 触发不受限、立即生效、零代码）与「人工叠加验证」（open PR 流量极低，人工可行）（核三 F2） | 补两条取舍：切 PR 流 = 治理层选项非本迭代件（流程迁移归用户裁定）；人工叠加 = 低流量可行但不可持续，机制化才可靠 | design §2.4 |
| 11 | 存疑 | 归层定性：C 落地时点对 §1 三症状改善为零（触发休眠 + 当前零标签 PR + 治理未决）——「预备性占位」；激活后治疗路径未点明（零标签 PR 期 test 分支 = 基线快照，每日全量 = 活线每日回归，双面硬币未写）（核三 Q1） | §1 明写「预备性占位（带战术权衡放行）」定位与激活后逐症状治疗路径；每日基线回归作为特性写入 §2.3-4 | design §1 / §2.3-4 |
| 12 | 存疑 | 前置件（main 治理）无排期、无负责人，决策支持件不入库，C 生效时点悬空（核三 Q2） | 如实登记：前置件归用户与协作者协调（本机待办与处置分析件已记，gitignore 属性接受）；design 边界声明维持 | design §1（一句） |
| 13 | 低级 | main tip 实为单 parent 的 squash 产物非「合并提交」；schedule 实跑延迟 3.7-5.6 小时（ZZZ 实测）未提；README 阶段计数与 attack 索引缺失；判据对照锚点不含 concurrency；「追加」措辞应为「新增」；无 PR 时每日全量照跑未写明；ZZZ repositories.md 引用未冠仓前缀且转述多了原文没有的「供测试者使用」（核一 L 族 / 核二 L 族 / 核三 L1） | 全部照建议落 | 各处 |

## 收敛状态

第一轮：阻断 4 族 / 应修 6 / 存疑 2 / 低级 9（去重）——未收敛，处置已全部落入修订，进入二轮闭合复核。

---

## 第二轮

报告：[attack-round2.md](attack-round2.md)（闭合复核：12/13 闭合 + 新增 应修 2 / 低级 6）。四个指定检查点（checkout 表达式三事件求值 / gh windows 可行性 / 3.2·3.3 同文件串行 / grep 判据自洽）全过。

二轮处置（已落入修订）：

| # | 级别 | 发现 | 裁定 | 落点 |
|---|---|---|---|---|
| 14 | 应修 | landing 3.3 判据缺 permissions（issues: write）与 GH_TOKEN 认证对照项——test-check 现状仅 contents: read，漏改时 gh issue create 403、红灯通知静默失效且验收照过；design §2.3-5 权限声明笼统混三 workflow（N1） | §2.3-5 按 workflow 分列（build-test-branch 三写照搬；test-check 新增 issues: write + 步骤 env GH_TOKEN）；3.3 判据补两项对照 | design §2.3-5 / landing 3.3 |
| 15 | 应修 | §2.3-3 尾句「激活前的实际价值面」与 §2.3-1 休眠结论自相矛盾（每日全量只在激活后发生）（N2，即一轮 #11 半落残余） | 改「激活后零标签 PR 期」 | design §2.3-3 |
| 16 | 低级 | 成功收尾依赖隐式 success() 规则未点明（N3） | `if: success() &&` 显式声明 | design §2.2-2 / landing 3.3 |
| 17 | 低级 | grep origin/main 拦不住 `"origin", "main"` 分离实参形态（N4） | 收口判据改双形态（连写零命中 + `"main"` 命中仅默认值行 1 处） | design §2.2-1 / landing 3.1 |
| 18 | 低级 | 判据 env 两项表述笼统（INCLUDE/CONFLICT 照搬与 BASE_BRANCH 新增混列）（N5） | 判据逐项标注照搬/新增 | landing 3.1 |
| 19 | 低级 | ZZZ workflow 头注释 origin/main 措辞无处置（N6） | 纳入文案清单与判据（头注释随基线改） | design §2.2-1 / landing 3.1 |
| 20 | 低级 | §2.3-1「两个 workflow 均不挂 PR 触发」与 test-check 保留 pull_request 现状矛盾（N7） | 改「新增触发不依赖 pull_request；test-check 现有 PR 触发保留不动」 | design §2.3-1 |
| 21 | 低级 | concurrency 裸 `github.ref` 分组使每日联动与 push main 同组互挤（workflow_run 的 github.ref = 默认分支 ref）（N8） | 分组键改 `test-check-${{ github.event.workflow_run.head_sha \|\| github.ref }}` 并写明理由 | design §2.2-3 / landing 3.2 |

二轮结论：**未收敛**（应修 2）——修订已落，进入三轮闭合确认。

---

## 第三轮（闭合确认）

报告：[attack-round3.md](attack-round3.md)。二轮处置 #14-#20 闭合（含两条应修），#21 半落（landing 3.2 范围段旧表达式漏同步——判据已改对、错误实现必被逐字对照验收拦下，定低级）；一轮 #11 随 #15 真闭合；新增 **阻断 0 / 应修 0 / 低级 5**。

三轮处置（随定稿顺手修，均低级）：

| # | 级别 | 发现 | 裁定 | 落点 |
|---|---|---|---|---|
| 22 | 低级 | landing 3.2 范围①残留旧 concurrency 表达式（R1） | 同步为 head_sha 分组键 | landing 3.2 |
| 23 | 低级 | design §0 状态行滞后（R2） | 定稿 | design §0 |
| 24 | 低级 | README 分核列表混入闭合报告、缺 round3 链接（R3） | 分核与轮次报告分组列出 | README |
| 25 | 低级 | 失败指示灯开/关事件面不对称（开=任意事件失败，关=仅 workflow_run 成功）（R4） | 对称化：开也限定 workflow_run（指示灯只反映集成分支；push/PR 失败有关联人，维持日志层） | design §2.2-2 / landing 3.3 |
| 26 | 低级 | §2.3-6「§正本清单」指法不标准（R5） | 改「landing『正本更新清单』」 | design §2.3-6 |

**三轮零新增阻断与应修级发现 → 达到收敛判据，设计定稿。**
