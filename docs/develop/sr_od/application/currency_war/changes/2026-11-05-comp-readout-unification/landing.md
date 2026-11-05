# comp-readout-unification 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集；行为批另加全量）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- **基线复核（多 agent 并行期）**：各阶段开工前 `git log --oneline -5` 对照 design.md 卷首基线声明；基线漂移（Comp/读口相关文件被并行迭代改动）则先修订设计再动工。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 批 A：members 读口与 14 处替换

**范围**：`Comp.members` property + 14 处消费点替换 + `predicates.line_members` 薄委托（模块级与函数 docstring 双处悬空引用修正）+ 删 `refresh._comp_members`（含 `_candidate_members` 回退分支死代码申报）+ 死防御清理 + test_sell_window_launch 鸭型桩改造。**不含**：kernel DI 管道退役（独立后续迭代）、双列数据清理（批 D）。
**设计依据**：details/members-readout.md 全文
**文件面**：`kernel/cw_comps.py`；`strategies/impl/mandate_v1/statefn/predicates.py`、`session_scope.py`、`criteria/refresh.py`、`criteria/priority.py`、`criteria/sell_candidates.py`、`line_select.py`、`deploy_search.py`、`shop.py`；`kernel/cw_intention.py`、`kernel/cw_investments.py`、`kernel/cw_launch_admission.py`；`sr-od-test/` 对应镜像（含 test_sell_window_launch.py 桩改造；其余期望值侧手搓并集刻意保留）。
**依赖**：无
**优先级建议**：10
**完成判据**：
- 行为对照 details/members-readout.md §2（14 处逐位等价替换；**主判据 = 14 处逐一核对完成**）；辅助 grep：单行式 `core_chars.*shared_chars|shared_chars.*core_chars` + 两行式 `\.core_chars\)[\s\S]{0,120}\.shared_chars` 在 src/ 生产代码归零（合法内联 2 处除外：derive_member_priority / _char_gift_tier）；
- `faction_migration_snapshots` 恒等快照全量通过；不新增构造断言测试（裁定见详设 §3）；
- predicates 模块级与函数 docstring 悬空引用清零；鸭型桩改造后 test_sell_window_launch 全绿；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名清单 + 双形态 grep 归零记录 + 14 处逐一核对清单。

## 3.2 批 B：carry 单名锚统一

**范围**：LINE_ANCHOR 21 行表 → `_LINE_ANCHOR_DIVERGENCE` 分歧登记（1 行）+ `rating_anchor` 读法函数 + `_validate_line_anchor` 改校验登记表 + `cw_line_scales.py` 常量 docstring 指针同步 + equip_allocation（两处）/ cw_equip_env 装备优先序统一走 `carry_anchor` + 分配器键换算单一源（cw_run_allocator 读口 + cw_loop `_allocator_update` 改调）+ `cross_line_skeleton` carries 集合统一 + `intention_core` docstring 分工声明（实现体不动）。
**设计依据**：details/carry-anchor.md 全文
**文件面**：`strategies/impl/mandate_v1/line_select.py`；`kernel/cw_comps.py`（equip_allocation 内两处）；`kernel/cw_equip_env.py`；`kernel/cw_plugins.py`；`kernel/cw_line_scales.py`；`kernel/cw_run_allocator.py`；`operations/cw_loop.py`；`kernel/cw_intention.py`（仅 docstring）；`sr-od-test/` 镜像。
**依赖**：与批 A 同动 `line_select.py` —— 串行执行（无逻辑依赖）
**优先级建议**：9
**完成判据**：
- 行为对照 details/carry-anchor.md §2：评分锚 21 套 anchor 值迁移前后逐一对照（含火花线登记取花火）；3 条空值线装备优先人行为变化按 §2 申报接受（攻略明文知识落地）；
- `cross_line_skeleton` 输出对照（fallback 三人不在 W16 任何键集的零漂移论证落地核对）；
- 分配器块零漂移验证：allocator 初始化日志 arms 键列表与详设 §3 实测式对照（键 = n_posts≥15 聚类 carry 名）+ update 行为不变抽查；
- 完成前常规检查。
**验收凭据形式**：21 套 anchor 对照表 + 分配器键核对记录 + 测试名 + grep（LINE_ANCHOR 符号归零、登记表校验生效）。

## 3.3 批 C：装备到人补全与 key_equips 投影化

**范围**：四段顺序提交。第 0 步：补建恒等测试（`key_equips == derive_key_equips` 全库断言，先证明防线有效）；数据批：8 套 equip_assign 补全（教义为准重写，出处优先序与线索见详设 §1，单件级宁缺毋滥；每套补后恒等重锁）；退役批：`key_equips` 字段删除改 property + 手编数据行全删 + `derive_key_equips` fallback 分支删除 + 三处「恒等测试」docstring 引用修正（cw_comps ×2、proofs/p42）；测试收尾：恒等测试转终态建库校验（全库 equip_assign 非空且键 ⊆ core∪shared）。
**设计依据**：details/equip-projection.md 全文
**文件面**：`kernel/cw_comps.py`；`docs/develop/sr_od/application/currency_war/proofs/p42-equipment-machine-ev.md`（引用修正一处）；`sr-od-test/` 镜像。
**依赖**：无（与批 B/D 在 cw_comps.py 交叠——串行更稳）
**优先级建议**：7
**完成判据**：
- 第 0 步测试先绿后动数据；数据批 8 套逐套人工过目记录（出处注释齐全，恒等随套保持绿）；
- 退役批：`comp.key_equips` 消费端读法零改动验证（grep 消费点无改动）；建库校验生效；三方向行为变化（增/减/重写，详设 §3）按申报接受，实机首局观察记录承接；
- 完成前常规检查 + 全量测试。
**验收凭据形式**：过目记录 + grep 记录 + 实机首局观察指针。

## 3.4 批 D：双列回声清理与语义诚实化

**范围**：~18 套 shared 列与 core 重复的回声删除（带交叉核对注）+ `shared_chars` 字段注释改写活语义 + core∩shared=∅ 建库校验。
**设计依据**：details/roster-hygiene.md 全文
**文件面**：`kernel/cw_comps.py`（数据行 + 字段注释 + 校验）；`sr-od-test/` 镜像。
**依赖**：批 A（members 锚）
**优先级建议**：6
**完成判据**：
- 21 套 `comp.members` 输出清理前后全量恒等对照（批 A 锚的落地核对）；
- `derive_member_priority` / 送卡档位 / `_line_hoard` 输出恒等（消费面抽查）；
- core∩shared 建库校验生效（双列数据重现 import 即炸）；
- 完成前常规检查。
**验收凭据形式**：members 恒等对照表 + 消费面抽查记录。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `strategy-docs/12_line_and_intention.md` §2（K 读口口径：line_members 薄委托后读口位置、成员集单一源 = Comp.members）← 批 A
- `strategy-docs/10_prep_decisions.md` 字段存留表（**补 key_equips 行**——现表该字段整个缺席，标「派生 property」；shared_chars 条目附「第二档终局成员」语义）← 批 C/D
- `strategy-telemetry.md` `k_members` 行读口列（读口仍为 predicates.line_members，零改动则显式申报不变）← 批 A
- `skills/sr-od-dev-currency-war/references/comp-definition.md`（schema 分层语义表成员行 + **读口层立法三条与读口清单**——本迭代的架构产出落点）← 全部批
- `strategy-docs/README.md` 模块地图（cw_comps 条目补读口层说明）← 末阶段
- `proofs/p42-equipment-machine-ev.md` 引用修正（随批 C 退役批，见 3.3）← 批 C
- DI 退役、p41 K 口径、equip_taboos 接线、transition 退役：均在 design「明确不解决」另案声明，不入本清单
