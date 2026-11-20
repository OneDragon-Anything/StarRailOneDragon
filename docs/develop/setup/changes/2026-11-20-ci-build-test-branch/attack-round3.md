# 三轮闭合确认报告

- 审查对象：本目录修订后的 design.md / landing.md / README.md（2026-11-20 二轮 8 条处置落修订后的稿）。
- 审查依据：attack.md 两轮裁定表（一轮 13 条 + 二轮 8 条）、attack-round2.md、iteration-design.md §5-4；SR 仓 .github/workflows/test-check.yml 现行原文与 git remote 实查（本轮亲自核验）。ZZZ 源件行号等平台事实一轮、二轮已核验且本轮修订未触及，不重复核验。
- 审查方式：二轮 8 条处置逐条对正文找落实处；一轮 #11 复核；三件轻量全量同步复查；新增问题只登记阻断级与应修级（收敛判据只看这两级），低级如实记录。两仓只读。

## 结论摘要

**二轮处置闭合 7/8**。#14-#20 七条全部落实且落点正确；#21 半落（「半落」= 处置的一部分已改、另一部分漏改：分组键在 design 与完成判据两处已改，landing 3.2 范围段仍保留旧表达式，残留登记为低级 R1——完成判据做逐字对照，错误实现必被验收拦下，无静默通过路径）。

**一轮 #11 随 #15 真闭合**：定位声明与逐症状治疗路径在一轮修订已落；二轮半落的唯一原因（价值论证句与休眠结论矛盾）已由 #15 修正，「每日全量即活线每日回归」现限定在「激活后零标签 PR 期」，与 §2.3-1 休眠结论自洽。

**新增：阻断 0 / 应修 0 / 低级 5**。五条低级均为修订同步残留与表述精度，不影响方案骨架（照搬 + 基线参数化 + 三事件接线 + 失败 issue 通知），均有明确的一行至数行修法。

## 逐条核验表（二轮处置 #14-#21）

| # | 级别 | 处置要点 | 落实证据（本轮实查） | 判定 |
|---|---|---|---|---|
| 14 | 应修 | design §2.3-5 按 workflow 分列权限；landing 3.3 判据补 permissions 与 GH_TOKEN 两项对照 | design §2.3-5 已分列：build-test-branch.yml 三写权限（照搬）；test-check.yml「现状仅 contents: read——需新增 issues: write……缺它 gh issue create 直接 403，红灯通知静默失效；gh 认证由步骤 env GH_TOKEN 提供」。「现状仅 contents: read」经现行 test-check.yml 原文实核为真（permissions: contents: read）。landing 3.3 范围含「permissions 新增 issues: write、步骤 env 提供 GH_TOKEN」；完成判据第一条「permissions 含 issues: write（现状仅 contents: read……design §2.3-5）；失败/成功步骤 env 含 GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}」——裁定要求的两项对照齐备，且把成功收尾步骤也纳入 GH_TOKEN 覆盖，比裁定更全 | 闭合 |
| 15 | 应修 | §2.3-3 尾句改「激活后零标签 PR 期」 | design §2.3-3 尾句现为「激活后零标签 PR 期 test 分支 = 基线快照，每日全量即活线每日回归——这是机制激活初期对本仓的实际价值面」——时态限定（激活后）与 §2.3-1「触发休眠、每日全量不发生」不再矛盾；§1 定位声明未引用该特性，无同口径连带问题 | 闭合 |
| 16 | 低级 | 成功收尾 `if: success() &&` 显式声明 | design §2.2-2「成功收尾步骤以 if: success() &&（workflow_run 触发条件）显式声明（不依赖 if 的隐式 success() 规则）」；landing 3.3 范围与完成判据均含同口径（「显式含 success() && workflow_run 触发条件（不依赖隐式规则；对 push/pull_request 事件不执行）」）。上游结论过滤保留在 job if（§2.2-2 第一件、landing 3.2 判据），两层条件分工正确，无重复判定 | 闭合 |
| 17 | 低级 | 收口判据改双形态 grep | design §2.2-1 收口口径：grep "origin/main" 零命中（拦连写）+ grep '"main"' 命中仅 1 处且为 BASE_BRANCH 默认值行（拦分离实参与文案裸字符串）；landing 3.1 判据「基线收口（grep 双形态口径）」同构 | 闭合 |
| 18 | 低级 | 判据逐项标注照搬/新增 | landing 3.1 判据「env INCLUDE_LABEL/CONFLICT_LABEL（照搬）与 BASE_BRANCH（SR 新增）」——两项来源逐项标注，不再依赖 design §2.1 表对应 | 闭合 |
| 19 | 低级 | workflow 头注释纳入文案清单与判据 | design §2.2-1 文案清单含「build-test-branch.yml 头注释的 origin/main 表述」；landing 3.1 判据含「build-test-branch.yml 头注释无裸 main 基线表述（原 ZZZ 注释的 origin/main 措辞随基线改）」 | 闭合 |
| 20 | 低级 | §2.3-1 措辞改「新增触发不依赖 pull_request；现有 PR 触发保留不动」 | design §2.3-1 末段现为「本迭代新增的触发（schedule / dispatch / workflow_run / push 扩展）不依赖 pull_request 事件——test-check 现有 pull_request 触发保留不动，build-test-branch.yml 不挂 PR 触发」。现行 test-check.yml 实有 pull_request 触发，矛盾消除 | 闭合 |
| 21 | 低级 | concurrency 分组键改 head_sha 版并写明理由 | design §2.2-3 分组键已改 `test-check-${{ github.event.workflow_run.head_sha || github.ref }}`，且写明理由（「不用裸 github.ref 的原因：workflow_run 事件的 github.ref = 默认分支 ref，会与 push main 同组互挤」）；landing 3.2 完成判据同表达式并引 design §2.2-3。**但 landing 3.2 范围① 仍写 `group: test-check-${{ github.ref }}`（旧表达式）**——同阶段范围段与判据不同步，见新发现 R1 | **半落** |

分组键语义顺带自检：workflow_run 事件取触发运行的 test 分支头 SHA，push 事件取被推分支 ref——SHA 字符串与 ref 字符串必不相同，每日联动测试与 push main 不再同组，N8 的问题形态消除；活线连续直推仍按同分支 ref 同组互杀旧跑，与 §2.3-4「取消同分支旧跑」表述自洽。

## 一轮 #11 复核

- 定位声明与逐症状治疗路径：design §1「定位声明（预备性占位，带战术权衡放行）」段齐备——落地时点改善为零的三条理由、激活后逐症状路径（症状 1 ← §2.3-2 每日集成验证；症状 2 ← 3.2 push 触发扩展立即生效部分；症状 3 ← 归前置治理件）、放行理由。
- 每日基线回归作为特性：§2.3-3 尾句已落，且经 #15 修正后时态正确（激活后零标签 PR 期才发生）。
- 结论：**真闭合**。

## 全量同步复查

- **清单对齐**：design §2.1 三组件 = landing 影响面前三文件；landing 影响面五文件被四阶段文件面完整覆盖（3.1 = 脚本 + build workflow；3.2、3.3 = test-check.yml；末阶段 = AGENTS.md + repositories.md）；README 阶段计数「3.1/3.2/3.3 + 末阶段」一致。design §2.1 表 test-check 行的改动列举与 landing 3.2+3.3 两阶段范围合计一致。通过（表行未列 concurrency 与 permissions 属判据自足面，非缺项——对应判据直接内联表达式并引 §2.2-3/§2.3-5，与二轮 N5 处置后的口径一致）。
- **节号引用**：landing 各阶段设计依据（§2.1、§2.2-1/2/3、§2.3-1/2/3/4/5、§2.4、正本更新清单节、AGENTS.md §13）与 design 正文互引逐一存在。design §2.3-6「（§正本清单）」指法不标准，登记为 R5。通过（一处指法低级）。
- **现状断言实核（本轮）**：test-check.yml 现行 permissions = contents: read ✓；现行触发 = pull_request + push main ✓（#20 前提成立）；仓 remote 实际 owner = OneDragon-Anything，design §2.1 表 owner 门控值照搬后与本仓 owner 一致，无「照搬值错配导致永不执行」问题 ✓。
- **旧措辞与过程叙事残留**：grep「追加｜只改一行｜供测试者使用｜载明｜合并提交｜上稿｜TBD｜暂定｜酌情」三件零命中。通过。
- **状态行三件同步**：README 已写「三轮闭合确认中」，design §0 仍写「二轮闭合复核中」——滞后一轮，登记为 R2。

## 新发现明细（本轮无阻断级与应修级，以下全部低级）

### R1 [低级] landing 3.2 范围① 的 concurrency 分组键仍是旧表达式（二轮 #21 半落残留）

- 位置：landing.md 3.2 节范围①「+ concurrency（`group: test-check-${{ github.ref }}`、cancel-in-progress: true）」。
- 证据：同一文件的完成判据与 design §2.2-3 均已是 head_sha 版表达式；范围段是二轮修订漏同步的唯一一处。实现者若只按范围段落手，会写出二轮 N8 判定要改掉的裸 github.ref 分组（每日联动测试与 push main 同组互挤、cancel-in-progress 互杀）。
- 定低级的理由：完成判据对 group 表达式做逐字对照并引 design §2.2-3，错误实现必然被验收拦下，无静默通过路径；读者两处对照可自行纠正。
- 建议：范围① 的 group 表达式改为与判据一致（一行改动）。

### R2 [低级] design §0 状态行滞后一轮

- design §0「状态：对抗审中（一轮 13 条裁定已落修订，二轮闭合复核中）」；README 进度行与 attack.md 二轮结论均已登记到三轮闭合确认。进度状态三件不同步。
- 建议：定稿时把 design §0 状态行与 README 一并更新为终态（如「对抗审定稿」）。

### R3 [低级] README「分核:」列表口径混入闭合复核报告

- README 把 attack-round2.md（闭合复核报告，非分核报告）与三份分核报告并列在「分核:」下；attack.md 自身将两者分开列。本轮 attack-round3.md 落定后该列表也需补链接。
- 建议：定稿时把列表改名为「对抗报告」，或按「分核 / 闭合复核」分两组列。

### R4 [低级] 指示灯开/关的事件面不对称未点明（按一轮 #4 裁定口径如实落，非漏落）

- design §2.2-2 / landing 3.3：失败步骤（if: failure()）对任何触发事件都开灯——push、pull_request 触发的测试失败也会开 test-branch-red issue；成功收尾步骤仅 workflow_run 触发时关灯。由此存在窗口期常亮形态：活线直推跑红开灯，后续直推跑绿不熄灯，灯要等下一次 test 分支联动跑绿（每日一次，另有平台调度延迟）才熄。
- 定低级的理由：该行为与一轮 #4 裁定原文一致（裁定对失败开灯未限定事件、对成功关灯明确限定 workflow_run），方向是宁多报不漏报，自愈窗口上限约一个联动周期，非正文漏落，不动方案骨架。
- 建议：正本 repositories.md 描述指示灯语义时写明开/关事件面（开 = 任意触发失败，关 = 仅 test 分支联动成功）与自愈周期。

### R5 [低级] design §2.3-6「（§正本清单）」引用指法不标准

- design §2.3-6 末尾「正本 repositories.md 记录该同步义务（§正本清单）」——「§正本清单」不带文件名、也不是 landing 的实际节名（landing 节名为「正本更新清单」），读者需猜指向。
- 建议：改为「（见 landing.md 正本更新清单节）」。

## 收敛判定

**收敛定稿。**本轮新增阻断级 0、应修级 0，满足「无新增阻断级与应修级发现」的收敛判据。二轮处置 7/8 闭合，唯一半落的 #21 残留（R1）有完成判据逐字对照兜底、无静默失效路径，按低级登记。

定稿时建议顺手完成（均小改动，不要求第四轮复核）：R1 范围段一行同步；R2 状态行更新；R3 README 报告列表归位；R5 引用指法改写；R4 的语义说明随末阶段正本 repositories.md 落。方案骨架（脚本照搬 + 基线参数化 + 三事件接线 + 失败 issue 通知 + 唤醒两步验收）三轮攻击无未闭合伤，可进入落地。
