# plaza-carry-retirement 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集；行为批另加全量）；
- 术语清理（各阶段承载）：本阶段文件面内代码注释与文档的存量黑话按统一术语表 `docs/develop/sr_od/application/currency_war/terminology.md` 清理——替换表内的词按表列白话改写；保留词首次出现带定义；不改动代码真名与游戏内容词；不做本阶段文件面之外的回溯清理；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」「文档规范·术语使用」节。

## 3.1 数据批：core 序换位 + 火花裁定 + 契约入注

**范围**：巡海击破 core 序换位（波提欧进首位）、双王圣杯 core 序换位（Saber 进首位）、火花星间旅人裁定落地（火花进 core 首位、need_star 补火花条目〔精值按 plaza 火花簇 `carry_star3_rate` 就地注释核对定档〕、分歧沿革就地注释归 final_comps 交叉核对记录）；`core_chars` 字段注释与 `members` 读口 docstring 写入「首位=定义件」契约。**不含**：任何读口/字段/表删改（本批完成后 `carry_anchor` 仍读 plaza_carry——本批行为变化 = core 序微差与火花线 members 扩员，见 design §2.2 前四行）。
**设计依据**：design.md §2.1 第 1 条、§2.2 表（巡海/双王/火花三行）、§2.3。
**文件面**：`src/sr_od/application/currency_war/kernel/cw_comps.py`（数据条目与字段注释）；`sr-od-test/` 对应镜像（火花线 members 相关断言扩员）。
**依赖**：无。
**优先级建议**：10。
**完成判据**：
- 全库 21 线 `core_chars[0]` 与 design §2.2 申报后的锚值一致（复核判定式：`comp.core_chars[0]` == 该线现行 `carry_anchor` 值，全库逐线通过）；
- 火花线 need_star 含火花条目且精值依据（star3 率口径）就地注释；
- 完成前常规检查（本文首节）。
**验收凭据形式**：判定式全库复核记录（逐线 core[0] 清单）+ 测试名。

## 3.2 代码批：字段/表退役 + 派生改造 + 断言改造

**范围**：`Comp.plaza_carry` 字段、`CARRY_ANCHOR_FALLBACK`、`_LINE_ANCHOR_DIVERGENCE`、`rating_anchor` 符号级删除；`carry_anchor` 改派生 `core_chars[0]`；新增 `named_units` 模块级派生函数（终局单锚/过渡全员/裸键组三态，过渡判据 = `TRANSITION_COMBO_PARTS` 键集）并替换 `form_progress`（点名折条）与 `deploy_search` L1 named 层（:278-282 附近）的就地表达式；`intention_core` 简化为 core[0]（plaza_carry 分支删除）；line_select 评分锚消费点直读 `carry_anchor`；`_validate_anchor_invariants` 按设计 §2.1 第 7 条改造（断言①等价改写/②换判据/③删/④不动）；cw_loop.py :1778 附近 plaza_carry 注释引用清理；cw_comps 模块头「plaza_carry 字段是两层交叉核对基准」句改写（交叉核对职责移交往对账报告）。**不含**：run 分配器（3.3）、对账工具（3.4）。
**设计依据**：design.md §2.1 第 2/3/4/5/7 条、§2.5。
**文件面**：`kernel/cw_comps.py`、`kernel/cw_intention.py`、`strategies/impl/mandate_v1/line_select.py`、`strategies/impl/mandate_v1/deploy_search.py`、`operations/cw_loop.py`；`sr-od-test/` 镜像（test_faction_derivation_locks 锚派生口径断言整段改写、test_line_select rating_anchor 断言改读、test_select_deployment 构造参数删、test_cw_comps/test_economy 值断言核对）。
**依赖**：3.1（数据就位后派生值才与申报锚值一致）。
**优先级建议**：9。
**完成判据**：
- 符号级 grep 清零：`plaza_carry` / `CARRY_ANCHOR_FALLBACK` / `_LINE_ANCHOR_DIVERGENCE` / `rating_anchor` 在 src 生产代码零残留（测试镜像同步清零）；
- 恒等断言：design §2.4 判定式落地批内测试覆盖（15 线逐位恒等 + 过渡条目 named_units == core 全员 + 火花线按申报值）；
- 行为对照 design §2.2 表（火花线申报四项：members 扩员/评分锚移位/意向核心换键/fp·部署·装备第一顺位值不变）；
- 完成前常规检查 + 全量测试。
**验收凭据形式**：grep 零残留记录 + 测试名清单 + 火花线行为对照记录。

## 3.3 run 分配器批：统计簇键源换表

**范围**：新增 `LINE_STAT_CLUSTER: dict[str, str]`（线名 → 统计簇名，21 条，值 = 各线 3.1 完成后的 `carry_anchor` 值快照；docstring 声明「adherence 统计分组键，非行为判据」）；`cw_run_allocator.arm_key_of` 由 `carry_anchor(comp)` 改查表（调用侧 `arm_id not in arms` 防线语义不变）。
**设计依据**：design.md §2.1 第 6 条。
**文件面**：`kernel/cw_run_allocator.py`（表就近放置于该模块）；`sr-od-test/` 镜像。
**依赖**：3.1（快照时点）；与 3.2 无文件冲突，排后保守串行。
**优先级建议**：7。
**完成判据**：
- `arm_key_of` 返回值与改造前逐线恒等（21 线对照断言）；
- 完成前常规检查。
**验收凭据形式**：逐线键值对照记录 + 测试名。

## 3.4 对账工具批：版本重跑差异报告

**范围**：`tools/cw/gen_plaza_comps.py` 生成末尾追加对账报告——逐线比对「聚类 carry（PLAZA_CARRY_CLUSTERS）vs COMP_LIBRARY 各线 core_chars[0]」，输出不同值线清单（stdout 报告，不阻断生成）。
**设计依据**：design.md §2.1 第 8 条、§2.3 第一行。
**文件面**：`tools/cw/gen_plaza_comps.py`；`sr-od-test/` 无（工具脚本，测试不覆盖）。
**依赖**：无（可与 3.1 并行）。
**优先级建议**：6。
**完成判据**：
- 重跑工具输出含对账节；火花线按 §2.2 裁定后应不出现在差异清单（花火 vs 火花分歧已收口）；
- 完成前常规检查（ruff 一项）。
**验收凭据形式**：工具输出样例。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新权威版本文档。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列权威版本文档。
**依赖**：3.1–3.4 全部。
**优先级建议**：0。
**完成判据**：清单清零；权威版本与实现一致；黑话终扫（design 方案与 landing/README 自身按术语表扫描清零；`proofs/` 已标注退役指针篇目豁免）。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `strategy-docs/12_line_and_intention.md`（CARRY 档口径：`plaza_carry ∪ core_chars 合流` → core 序顶端派生；评分锚/意向核心措辞）← 3.2
- `strategy-docs/10_prep_decisions.md`（字段存留表：plaza_carry 行 → 派生读数；CARRY_ANCHOR_FALLBACK 行删）← 3.2
- `strategy-docs/24_deploy_segment.md`（L1 named 层：点名件表达式换源措辞——named_units 单一源）← 3.2
- `skills/sr-od-dev-currency-war/references/comp-definition.md`（schema 分层语义「身份/成员」节：core 首位=定义件契约；实现层最小面「优先级」行 = 功能链序数化投影的顶端读数）← 3.1/3.2
- `skills/sr-od-dev-currency-war/references/version-update.md`（版本重跑清单：聚类 carry vs core[0] 对账步骤）← 3.4
- `docs/game/currency_war/data/plaza_meta.md`（人读版头部：交叉核对用途注记 → 对账报告指针；数据值不变）← 3.4
- `data/cw_plaza_comps.py` 模块头 docstring（「plaza_carry 字段是两层交叉核对基准」句 → 对账报告口径）← 3.2（生成器模板同步，3.4 批核对再生成）
