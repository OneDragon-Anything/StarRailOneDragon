# 二轮闭合复核报告

- 审查对象：本目录修订后 design.md / landing.md / README.md（2026-11-20 一轮 13 条裁定落修订后的稿）
- 审查依据：attack.md 合并裁定表（13 条）、三份分核报告、iteration-design.md §5-4「修订后全量同步复查」、ZZZ 仓参照源（tools/ci/build_test_branch.py 与 .github/workflows/ 下 build-test-branch.yml / sync-cnb.yml / test-check.yml 原文）、SR 仓 .github/workflows/test-check.yml 现状、GitHub 官方文档（Events that trigger workflows / Evaluate expressions 两页，本轮亲自核验）
- 审查方式：逐条对照裁定表找落实处；三件全量对齐复查；对修订新引入的四处内容做平台行为核验。两仓只读。

## 结论摘要

**闭合 12/13**（#11 半落）；**新增：阻断 0 / 应修 2 / 存疑 0 / 低级 6**。

一轮 4 条阻断全部闭合且落点正确；半落的 #11 出在裁定落实句自身的措辞与休眠结论矛盾（新发现 N2，应修级）。新应修两条均为判据层面的缺口（N1 失败 issue 步骤的权限与认证无对照项、N2 价值论证句语病），不动方案骨架。四个指定检查点中两个通过（checkout 表达式三事件求值、3.2/3.3 文件面重叠），两个各产出一条发现（N1、N4）。

**收敛判定：未收敛**——按「连续一轮无新增阻断级与应修级」口径，本轮有新增应修 2 条；修订面小（判据补对照项 + 一句措辞），修订后需第三轮闭合复核。

## 逐条闭合表

| # | 裁定要点 | 修订落实处（证据） | 判定 |
|---|---|---|---|
| 1 | 主仓 checkout 显式 ref 三事件行为不变 + 判据同步 | design §2.2-3 第 2 条（表达式 + 平台事实依据 + 三事件回退说明）；landing 3.2 范围③与判据「主仓 checkout 含 ref 表达式」。表达式求值三事件核验见「指定检查点①」，与设计声称一致 | 闭合 |
| 2 | §2.2-1 全量清单（5 实参处 + 文案/docstring）；grep 收口口径 | design §2.2-1 列 5 处实参（L486/487/530/255/311，与 ZZZ 源件本轮逐一复核相符）+ 文案/docstring 项 + 收口口径（grep origin/main 与裸 main 清零、唯一合法残留 = BASE_BRANCH 默认值字面量）；landing 3.1 判据「基线收口（grep 口径）」同构。grep 口径的漏放面见新发现 N4；workflow 头注释漏项见 N6（裁定表未纳该项，不计入半落） | 闭合 |
| 3 | 两 workflow 各配 env BASE_BRANCH；双处同步义务；「只改一行」废除 | design §2.2-1 末段（各自声明 + env 不跨 workflow + 改两处）与 §2.3-6 专条（双处同步 + 静默错配风险 + 正本记录）；landing 3.1 范围、3.2 范围④与判据「env 块含 BASE_BRANCH（与 3.1 同名同值）」。grep 全文「只改一行」零命中 | 闭合 |
| 4 | 失败通知落 issue；成功关灯；唤醒验收两步走 | design §2.2-2（失败步骤 gh 开/评 issue + 成功收尾关 issue + 标签首跑自建）与 §2.3-1 末段（两步验收：机制跑通与基线修红分离 + ZZZ 前车之鉴）；landing 新增阶段 3.3（裁定落点写 landing 3.2，修订将通知独立成 3.3 阶段——结构重组，内容闭合）；repositories.md 入正本清单与末阶段判据；README「生效验证:待前置」。成功收尾步骤的触发条件精度见新发现 N3（低级） | 闭合 |
| 5 | PR 基线错位写入第二层前置；错位期行为如实 | design §2.3-2 专条（10 个 open PR 实测 base 全 main、三方合并基底落 7 月分叉点、冲突墙淹没、近乎全跳、「防线实际作用始于 PR 群对齐后（治理了结 + 存量 PR rebase）」）；§1 定位声明症状 1 治疗路径引 §2.3-2 | 闭合 |
| 6 | push 触发扩展 + concurrency；费用换覆盖取舍 | design §2.2-3 第 1 条（push branches: [main, 活线] + concurrency group/cancel-in-progress）；§2.3-4 费用句（每次直推各触发一次全量 + concurrency 有上限）；§2.4「弃活线切 PR 流」条关联取舍；landing 3.2 范围①与判据（push 两分支 + concurrency cancel-in-progress: true）。concurrency 分组的边缘形态见 N8（低级） | 闭合 |
| 7 | CNB 两层事实 + 一句联动说明 | design §1 解决到哪段（「CNB 渠道本仓 main 上也有 active 的 sync-cnb.yml，但其镜像源是停摆 main、活线没有该链路；治理后若 CNB 链路保留……本设计不展开」）。表述精度小瑕见 N9 之外不另计（见低级 N9 说明——并入本表备注：镜像范围细节不展开属裁定接受面） | 闭合 |
| 8 | 「照搬已验证」话术两分 | design §2.1 表 test-check 行「**全新接线，无 ZZZ 先例**（ZZZ 的 test 分支消费方是 CNB 分发、其 pytest 自 2026-08 起禁用）——静态判据 + 唤醒后首跑验收承担」；§2.4 第一条「闭环接线……是全新代码，不自称『照搬已验证』」；§2.1 表前两行保留「ZZZ 实跑验证件」 | 闭合 |
| 9 | 新建 repositories.md 正本；清单补行；README 进度行 | landing 影响面列 repositories.md、正本更新清单首行（分支模型/CI workflow 清单/机制与唤醒验收 ← 3.1/3.2/3.3）、末阶段文件面与判据（含标签语义、BASE_BRANCH 双处同步义务、休眠前置与唤醒两步验收清单）；README「生效验证:待前置（……唤醒两步验收口径见 design §2.3-1）」 | 闭合 |
| 10 | 补两条备选取舍 | design §2.4「弃『活线切 PR 流』」（治理层选项归用户裁定、非本迭代件、用 push 触发拿同等覆盖）与「弃『人工叠加验证』」（低流量可行但不可持续、机制化才可靠） | 闭合 |
| 11 | 「预备性占位」定位 + 逐症状治疗路径 + 每日基线回归作为特性 | design §1 定位声明段（占位定位、三症状逐条路径、放行理由）落实；「每日基线回归作为特性」写入 §2.3-3 尾句（裁定落点写 §2.3-4，实际落 §2.3-3——位置本身可接受），但该句「这是激活前机制对本仓的实际价值面」与 §2.3-1 休眠结论矛盾（每日全量只在激活后发生）——见新发现 N2（应修） | **半落** |
| 12 | 前置件归属如实登记一句 | design §1 明确不解决第一条：「排期与负责人归用户与协作者协调（本机待办与处置分析件已登记）」——悬空事实显式化，边界维持 | 闭合 |
| 13 | 低级批量七项全部照建议落 | ① main tip 表述：design §1 症状 3 改为「squash 合并产物，单 parent 提交」✓；② schedule 延迟：§1 根因段 / §2.1 表 / §2.4 时区条三处均补 3.7-5.6 小时延迟 ✓；③ README 阶段计数「未开始（阶段 3.1/3.2/3.3 + 末阶段）」与 landing 实际四阶段一致、attack 与三份分核均有索引 ✓；④ concurrency 锚点：design §2.1 表已补 concurrency 项，判据对照自洽（env 三项缺二见 N5）△；⑤ 「新增」措辞：§2.2-2 用「新增」，grep「追加」零命中 ✓；⑥ 无 PR 每日全量：§2.3-3 尾句 + §2.3-4 费用 ✓；⑦ ZZZ repositories.md 引用：改写后不再引用该文件、「供测试者使用」「载明」措辞消失，grep 零命中 ✓ | 闭合（④ 残余见 N5） |

## 全量同步复查（iteration-design.md §5-4 口径）

- **三处清单对齐**：design §2.1 三组件 = landing 影响面前三文件；landing 影响面五文件（脚本 / 两 workflow / repositories.md / AGENTS.md）被阶段文件面完整覆盖（3.1 = 脚本 + build workflow；3.2、3.3 = test-check.yml；末阶段 = AGENTS.md + repositories.md）；README「阶段 3.1/3.2/3.3 + 末阶段」与 landing 阶段结构一致；design §2.1 表 test-check 行的改动列举（push 扩展 / workflow_run / checkout ref / 测试仓三事件 / 失败 issue）与 landing 3.2+3.3 两阶段范围合计一致。通过。
- **判据引用节号实存**：landing 各阶段设计依据（§2.1、§2.2-1/2/3、§2.3-1/2/3/4/5、§2.4、「正本更新清单」节、AGENTS.md §13）与 design 正文内部互引（§2.3-6、§2.2-2、§2.3-2 等）逐一存在。design 引 landing 阶段号（§1「本迭代 3.2」、§2.3-4「3.2 的 push 触发扩展」）为同迭代内互引，合法。通过。
- **README 链接与状态**：design.md / landing.md / attack.md / attack-core1/2/3.md 同目录实存，链接可达；README「迭代设计:对抗审中」与 design §0 状态一致；README「设计对抗:二轮闭合复核中」与 attack.md 收敛状态一致。通过。
- **过程叙事词表**：grep「本轮｜修订后｜待定｜看情况｜TBD｜暂定｜酌情｜上稿｜已改」三件零命中（README/design §0 状态行内的轮次描述属进度状态，进度住 README 为规范允许）。通过。
- **一轮旧措辞残留**：grep「追加｜只改一行｜供测试者使用｜载明｜合并提交」零命中。通过。

## 指定检查点核验

### ① checkout ref 表达式三事件求值 —— 通过，无发现

design §2.2-3 的 `ref: ${{ github.event.workflow_run.head_sha || github.ref }}`：

- **workflow_run 事件**：`github.event.workflow_run.head_sha` 存在且非空（真值），表达式取它——检出 test 分支头。符合设计声称。
- **pull_request / push 事件**：event 上下文无 workflow_run 键，GitHub 表达式语言对不存在属性做宽松解引用返回 null（falsy），`||` 返回第一个真值 → 回退 `github.ref`。官方 Events 文档表：pull_request 的 GITHUB_REF = `refs/pull/N/merge`（与现状 checkout 默认检出 GITHUB_SHA——同 ref 的头提交——等价）、push 的 GITHUB_REF = 被推分支 ref（与默认 GITHUB_SHA 等价）。三事件行为均不变，设计声称成立。
- 本仓自有先例佐证宽松解引用行为：现行 test-check.yml 测试仓 checkout 的 ref 表达式（`github.event.pull_request.head.repo.full_name && format(...) || '...'`）访问 push 事件下不存在的 pull_request 属性并回退，该文件 pull_request 触发的运行实跑过（至 2026-08-07）。

### ② landing 3.3 gh 命令 windows runner 可行性 —— 形态可行；产出应修 N1（权限与认证判据缺口）

- gh CLI 预装于 GitHub 托管的 windows runner（官方 runner 镜像清单列明；design §2.3-5 亦声明）；ZZZ 侧 ubuntu 实跑 gh 打标签为同工具链佐证。
- 判据所列命令形态（gh search issues 查开 → 评论或创建、gh label create --force 幂等自建）在 pwsh 下可执行；`gh label create --force` 幂等语义正确。
- 缺口在权限与认证：见 N1。

### ③ 阶段 3.3 与 3.2 文件面重叠 —— 通过，无发现

两阶段文件面同为 test-check.yml；landing 3.3 依赖声明「3.2（挂在同一触发结构上）」正确——3.3 的成功收尾步骤语义上依赖 3.2 引入的 workflow_run 触发，且依赖使同文件两阶段在派工上串行（3.1 → 3.2 → 3.3 → 末阶段，无环），不构成并行写冲突。拆分本身使「接线」与「通知」两个语义面各自可独立验收，划分合理。

### ④ grep 收口判据与 BASE_BRANCH 默认值自洽性 —— 不误伤；有低级漏放面（N4）

- **不误伤**：`os.environ.get("BASE_BRANCH", "main")` 默认值不含 `origin/main` 字样，grep origin/main 零命中判据不会命中它；裸 main 文案判据已将它显式列为唯一合法残留。自洽。
- **漏放面**：5 处实参中的 L486 是 `git fetch origin main`——`origin` 与 `main` 是两个独立实参，不含 `origin/main` 连写字样；若实现者漏改 L486（其余 4 处已参数化），grep origin/main 零命中照样通过。该漏放由 landing 3.1「脚本与 ZZZ 源件逐段对照（design §2.2-1 清单）」判据兜底（L486 在清单内，逐段对照会暴露）。定级低级，见 N4。

## 新发现明细

### N1 [应修] 失败 issue 步骤的权限与认证无判据对照项，漏改时一轮 #4 的通知目标静默失效

- **位置**：landing 3.3 范围与完成判据（全文无 permissions 与 GH_TOKEN 字样）；design §2.1 表 test-check 行（改动列举同样不含）；design §2.3-5（笼统声明）。
- **证据**：
  1. SR 现行 test-check.yml 的 permissions 仅 `contents: read`。3.3 要用 gh 创建/评论/关闭 issue，需要 `issues: write` 权限，且 gh 命令需要 `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` 环境变量认证（ZZZ build-test-branch.yml 步骤内即如此配置）。
  2. design §2.3-5 写「workflow 显式声明 contents/pull-requests/issues write（建分支/建标签/维护 PR 标签/失败 issue）」——这句把三个 workflow、四类动作的权限混在一句里：build-test-branch 需要 contents/pull-requests/issues 三项，test-check 实际需要的是 issues write（加现状 contents read）。实现者从设计里找不到「test-check 该加哪几项」的直接答案（照抄三项全加与只漏改不加都读得出）。
  3. 后果链：实现者若保持 `contents: read` 不动，失败步骤的 `gh issue create` 因权限不足 403 失败——红灯 issue 开不出来，一轮 #4 修补的「红信号去向」静默失效；而 landing 3.3 判据（只对照 gh 命令形态与标签自建）对此全部通过——错误实现可通过验收。
- **建议**：landing 3.3 范围补「permissions 升级（issues: write）」；判据补两条对照项——「permissions 含 issues: write」「失败步骤 gh 命令所在步骤含 GH_TOKEN 环境变量」。design §2.3-5 按文件区分写明各自所需权限（build-test-branch 三项、test-check 加 issues write）。顺带：`gh search issues` 无命中时退出码非零，判据可加一句「查询命令容错处理（无 open issue 时 exit 1 不视为步骤失败）」。

### N2 [应修] design §2.3-3 「这是激活前机制对本仓的实际价值面」与休眠结论自相矛盾

- **位置**：design §2.3-3 末句：「零标签 PR 期 test 分支 = 基线快照，每日全量即活线每日回归——这是激活前机制对本仓的实际价值面，也是 runner 费用的主要去向。」
- **证据**：design §2.3-1 自身结论——落地后 schedule/workflow_run 触发休眠、每日全量根本不发生；「每日全量即活线每日回归」的现象只能存在于**激活后**（且零标签 PR 期间）。该句是 #11 裁定「每日基线回归作为特性写入」的落实句，按字面读会得出「激活前就有每日回归价值」的错误结论，与 §2.3-1 直接冲突，也误导对「占位放行」价值论证的理解。
- **建议**：改为「激活后零标签 PR 期」——「零标签 PR 期 test 分支 = 基线快照，激活后的每日全量即活线每日回归——这是激活后（且 PR 群打标签前）机制对本仓的实际价值面，也是 runner 费用的主要去向」。§1 定位声明如引用此特性，同口径。

### N3 [低级] 成功收尾步骤的「测试成功才执行」依赖隐式 success() 规则，判据未点明

- **位置**：design §2.2-2「新增成功收尾步骤（仅 workflow_run 触发时）关闭该标签全部 open issue」；landing 3.3 判据「成功收尾步骤 `if` 同时满足 workflow_run 触发与 `conclusion == 'success'` 口径」。
- **证据**：官方表达式文档："A default status check of `success()` is applied unless you include one of these functions"——步骤 if 表达式不含状态函数时隐式附加 success()。因此 `if: github.event_name == 'workflow_run' && github.event.workflow_run.conclusion == 'success'`（照 ZZZ sync-cnb.yml job if 形态）在测试失败（前置步骤失败）时不会执行，指示灯不会「刚开就被关」。行为正确，但依赖实现者知晓隐式规则；且该判据里的 `conclusion == 'success'` 指上游 Build Test Branch 的结论——在 3.2 的 job if 过滤后此处恒为真，属冗余条件，与「本 run 测试成功」不是一回事。
- **建议**：判据改为显式口径「成功收尾步骤 if = `github.event_name == 'workflow_run' && success()`（success() 显式声明，不依赖隐式规则；上游成功已由 job if 保证，不重复判）」。

### N4 [低级] grep origin/main 收口判据不覆盖 L486 的分离实参形态

- **位置**：design §2.2-1 收口口径；landing 3.1 判据「基线收口（grep 口径）」。
- **证据**：见指定检查点④。L486 `git fetch origin main` 中 `origin` 与 `main` 为两个独立实参，漏改时不含 `origin/main` 连写字样，grep 零命中拦不住；由 3.1 逐段对照判据兜底。
- **建议**：收口口径补一条 `grep -n '"main"' tools/ci/build_test_branch.py` 仅允许命中 BASE_BRANCH 默认值一处（字符串字面量层面的 main 清零），或判据注明「L486 分离实参形态由逐段对照覆盖，grep 口径仅作快速收口」。

### N5 [低级] landing 3.1 判据清单中 env INCLUDE_LABEL/CONFLICT_LABEL 在所引对照源（design §2.1 表）无对应

- **位置**：landing 3.1 判据「workflow 对照 design §2.1 表：…… + env INCLUDE_LABEL/CONFLICT_LABEL/BASE_BRANCH + ubuntu 步骤齐全」。
- **证据**：design §2.1 表 build-test-branch 行只写了「env `BASE_BRANCH`」；INCLUDE_LABEL/CONFLICT_LABEL 只存在于 ZZZ 源 workflow（L31-32），design 表内无。判据所列项目超出对照源——与一轮核一 L4（concurrency 锚点缺）同型的锚点不完备残余。
- **建议**：判据改「对照 design §2.1 表 + ZZZ 源 workflow（env 三项、步骤形态见源件）」，或 design §2.1 表把 env 三项写全（照搬件自带 INCLUDE_LABEL/CONFLICT_LABEL、SR 适配增 BASE_BRANCH）。

### N6 [低级] 照搬范围含 ZZZ workflow 头部注释的 main 措辞，无处置声明

- **位置**：landing 3.1 范围（「照搬 + env BASE_BRANCH……」）；design §2.2-1 收口口径（限定「脚本内」）。
- **证据**：ZZZ build-test-branch.yml 头部注释「每次都从 origin/main 重新开始」；3.1 照搬该 workflow 时头注释会原样带入，而 SR 基线是活线——头注释失真。一轮核二 B1 证据明确点名此注释，裁定表 #2 的裁定要点只收了脚本面（实参 + 文案/docstring），该漏项不在裁定口径内，故 #12/闭合表仍判 #2 闭合，此处独立申报。
- **建议**：landing 3.1 范围补一句「workflow 头部注释的 origin/main 措辞随基线改」；design §2.2-1 收口口径同步把 workflow 文件头注释纳入。

### N7 [低级] design §2.3-1「本迭代两个 workflow 均不挂 PR 触发」与 test-check 现状矛盾

- **位置**：design §2.3-1 末句。
- **证据**：test-check.yml 现状挂 pull_request 触发，landing 3.2 明写「不动现有 pull_request 触发行为」——它正是「本迭代的两个 workflow」之一且保留 PR 触发。该句想表达的应是「本迭代不新增 PR 类触发接线（不依赖它绕过休眠）」，字面写成了两个 workflow 都无 PR 触发。读者两处对照可纠正，不阻碍实施。
- **建议**：改为「本迭代不新增 pull_request 类触发（test-check 保留现状 pull_request 触发，build-test-branch 无）」。

### N8 [低级] concurrency 分组使每日联动测试与 push main 触发同组互挤

- **位置**：design §2.2-3 第 1 条（`group: test-check-${{ github.ref }}`、cancel-in-progress: true）。
- **证据**：官方 Events 文档：workflow_run 事件的 GITHUB_REF = 默认分支 ref——每日联动测试的 concurrency group 恒为「test-check + 默认分支 ref」，与 push main 触发的运行同组；cancel-in-progress: true 时，每日集成测试运行中若发生 push main，联动的全量测试被取消（cancelled 状态不触发 if: failure() 步骤，红灯 issue 也不开）——当日集成回归结果静默丢失。当前 main 停摆几乎无 push，触发概率低；治理后 main 恢复活跃时会成为可复现形态。
- **建议**：group 改为 `test-check-${{ github.event.workflow_run.head_branch || github.ref }}`（workflow_run 取上游分支名、其余事件取自身 ref），或维持现状但在 design §2.3 注明该互挤边缘形态与接受理由。

## 收敛判定

**未收敛。** 本轮新增应修级 2 条（N1 判据缺权限/认证对照项、N2 价值论证句与休眠结论矛盾）——不满足「连续一轮无新增阻断级与应修级」口径。两条修订面均小（landing 3.3 补对照项 + design 两句措辞），修订后进入第三轮闭合复核；低级 6 条建议随本轮一并顺手修（N4/N5/N6 收口与锚点、N7/N8 措辞与注明、N3 显式 success()），也可记遗留随收口。方案骨架（照搬 + 基线参数化 + 三事件接线 + 失败 issue 通知）本轮无新攻击点。
