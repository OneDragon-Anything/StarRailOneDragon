# journal-review-renderer 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/tools -m "not slow"` 及受影响既有子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段名；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 渲染器重写（journal 版）

**范围**：按 details/pipeline.md + details/render-spec.md 重写 `tools/cw/replay_to_md.py`（行加载/节点分组/无 node 行归属/画面切分/动作差分/中间表示/渲染输出/CLI 全量）；新增 fixture 单测。边界：不动 `review_skeleton.py`（3.2）、不动 skill references（3.3）、不动 src。
**设计依据**：details/pipeline.md 全篇；details/render-spec.md §1-§5（策略评价节 = §5.6）；design.md §2 CLI 契约。
**文件面**：`tools/cw/replay_to_md.py`；`sr-od-test/test/tools/test_replay_render.py`（新目录，文件头注明「tools 无 src 镜像先例，按工具名组织」的理由）。
**依赖**：无。
**优先级建议**：0
**完成判据**（两轴分别判定，结构返工不连带迁移轴）：
- **迁移轴**（retirement.md §7 #3 落地）：经 `journal_query.read_journal_stats` 单一读面，对生产 live journal 与 sim 批 journal 各渲染成功一份非空报告（真实数据，人工核验非空且结构完整）；
- **结构轴**：行为对照 pipeline §1-§7 与 render-spec §1-§5 逐节可实现；渲染产物人工对照 render-spec（局头/开局/节点×画面×动作/策略评价节在位，无收尾章/无速览/无计数器）；
- 单测（自造 fixture journal，只写 tmp_path，零真实副作用）覆盖：节点分组与 kind 首行选值、无 node 行三类归属（开局/虚拟组/annex）、画面章切分（组首恒开章、current_screen 变化、弹层 actor 归章、未注册 screen id 兜底）、动作锚 same_value 过滤（no-op receipts 重写不产动作节）、重试链合并、状态差分前值链与章内归属（含章内变化块）、obs 道不入变化表、宽容读坏行计数、动作词参数型别名归一、空动作章与策略评价节；
- 完成前常规检查（本文首节）。
**验收凭据形式**：单测名清单 + 两份真实渲染产物（迁移轴）+ render-spec 对照记录（结构轴）。

## 3.2 review_skeleton.py 删除

**范围**：删除 `tools/cw/review_skeleton.py`；仓内引用清零（grep `review_skeleton` 现存引用 = 自身 + skill sim-testing.md，后者属 3.3 文件面）。边界：不动 match-review.md（3.3）。
**设计依据**：design.md §2 系统级变化 3（sim 局复盘改走 `--journal <sim批>/state/journal.jsonl`）。
**文件面**：`tools/cw/review_skeleton.py`（删除）。
**依赖**：3.1（删除后 sim 复盘入口必须已可用，防工具真空期）。
**优先级建议**：5
**完成判据**：文件已删；仓内 `grep -r review_skeleton`（除 changes/ 本迭代目录与 skill references 3.3 待改行外）零命中；完成前常规检查（首节）。
**验收凭据形式**：grep 输出对照。

## 3.3 skill references 协同更新

**范围**：`skills/sr-od-currency-war-dev/references/` 更新——①match-review.md：产出形态节改为渲染器新结构（局头/开局/节点×画面×动作；无收尾章；文末「复盘者附加」空节；复盘者逐决策面画面章填策略评价），阶段 2 粒度描述改按画面章口径、op 边界重建规则改写为「边界 = 渲染器画面章/动作节产物，复盘者不重建」（旧重建规则依赖死流）；回灌判据读数条款取数锚改 journal 锚（buys = BuyCard 回执 + gold 写入链，渲染器动作节已算出）；「零条候选红线」等复盘者义务保留，落点改指报告文末「复盘者附加」空节（用户裁定 2026-10-16 = A，design §1）；②sim-testing.md：骨架生成器行改为新渲染器 `--journal` 用法；③telemetry-reading.md：旧流引用清查更新（申报理由见 design §2 变化 4）。**skill 目录在本仓**（`.dsh/skills/sr-od-currency-war-dev` junction → `skills/sr-od-currency-war-dev`，已核实）。
**设计依据**：design.md §1 明确不解决（方法论本体不改）+ §2 系统级变化 3/4；attack.md C3/D3。
**文件面**：`skills/sr-od-currency-war-dev/references/match-review.md`、`sim-testing.md`、`telemetry-reading.md`。
**依赖**：3.1（引用的工具行为必须已存在）。
**优先级建议**：5
**完成判据**：三文件更新后与新渲染器行为一致（逐条对照 render-spec 结构描述）；references 内无 review_skeleton 残留引用；完成前常规检查（首节）。
**验收凭据形式**：diff 对照 render-spec 结构逐条核对。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本；含验收期增补三项（reviewer 裁定，2026-10-16）：①`skills/sr-od-currency-war-dev/SKILL.md` 分诊表 match-review 行载体描述更新（一行）；②match-review.md 阶段 2 对本迭代 changes/ 详设的路径引用改锚正本（渲染器注册表常量或 op-layer 义务锚——长寿命文档禁引过程区）；③回灌读数 refresh_probs 锚表述改「journal `shop` 写入行（内嵌 refresh_probs 键）」。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文件。
**依赖**：全部落地阶段。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `src/sr_od/application/currency_war/operations/cw_screen/cw_screen_supply_node.py` 渲染方注释指针（现指 `replay_to_md._supply_entry`，随重写更名）← 3.1
- `tools/cw/replay_to_md.py` 模块 docstring as-built（新数据源/新结构/新 CLI）← 3.1
- `docs/develop/sr_od/application/currency_war/game_state/retirement.md` §7 #3 消费面状态推进（replay_to_md 已迁；repair_invest_attribution 处置结论一并登记）← 3.1
- `docs/develop/sr_od/application/currency_war/screens/op-layer.md`：新增画面 op 须同步渲染器画面注册表的义务锚（判定口径 = actor 带 CwScreen 前缀且未入 ACTOR_REGISTRY；豁免 = 快照章形态 op（CwScreenPrep/CwScreenShop/CwScreenBattleWait）与已知动作类豁免清单 _ACTION_ACTOR_EXEMPT（历史动作命名）；新增画面 op 同步 ACTOR_REGISTRY，新增 CwScreen 前缀动作类同步豁免清单）← 3.1
- `skills/sr-od-currency-war-dev/references/match-review.md` 产出形态节 ← 3.3
- `skills/sr-od-currency-war-dev/references/sim-testing.md` 复盘骨架行 ← 3.3
- `skills/sr-od-currency-war-dev/references/telemetry-reading.md` 旧流引用（若有）← 3.3
- `skills/sr-od-currency-war-dev/SKILL.md` 分诊表 match-review 行载体描述 ← 验收期增补①
