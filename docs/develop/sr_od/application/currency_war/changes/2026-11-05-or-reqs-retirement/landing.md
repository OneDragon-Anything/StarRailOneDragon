# or-reqs-retirement 落地

（「正本」= 权威版本文档；节名「正本更新」「正本更新清单」沿用迭代设计模板固定名，不按术语表替换。）

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 终局希儿量子条目改档

**范围**：`COMP_LIBRARY`「希儿量子」条目档 0 改 `{量子同频: 4, 贝洛伯格: 4}`、新增档 1 `{战技点: 2, 治疗: 2}`、flex_factions 收敛、删条目 or_reqs；`TRANSIT_AFFIX_PENALTY` 注释措辞更新。**不含**：or_reqs 字段/机器删除（3.3）、过渡条目库（3.2）、其他 20 条终局条目。
**设计依据**：details/seele-final-comp.md 全文。
**文件面**：`src/sr_od/application/currency_war/kernel/cw_comps.py`；`sr-od-test/` 对应镜像（test_cw_comps 希儿条目断言、fp 曲线新期望）。（cw_intention.py 的 TRANSIT_AFFIX_PENALTY 注释与旧过渡条目名绑定，归 3.2 统一改——见 seele-final-comp.md §3。）
**依赖**：无。
**优先级建议**：10。
**完成判据**：
- fp 曲线对照 seele-final-comp.md §2 表逐值一致（希儿+量1=0.417 / 量2=0.500 / 完全体=1.0）；
- commit 线行为：希儿+量1 仍 ≥ 0.4（工具激活面不丢）；
- `COMP_LIBRARY` 内 or_reqs 清零（过渡库旧「希儿引擎」条目仍持，3.2 移除——本阶段不越界动过渡库）；form_progress 对希儿量子按纯 AND 折算、非希儿 20 线 fp 逐位恒等（迁移恒等测试）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名清单 + fp 数值对照记录。

## 3.2 过渡羁绊构造块与组合条目库

**范围**：`TransitionBond` 结构 + 五块数值表 + `_build_transition_combos` 生成器 + 建库校验；`TRANSITION_ENTRY_KIND` 删除、`transition_member_set` 改 combo 展开、`TRANSITION_COMBO_PARTS` 登记、`transition_scores` 纯函数提出；旧 4 条目退役。**不含**：or_reqs 机器删除（3.3）、资格臂（3.4）、锁定机器逻辑改动（零改动验证）。
**设计依据**：details/transition-combos.md 全文。
**文件面**：`src/sr_od/application/currency_war/kernel/cw_comps.py`、`src/sr_od/application/currency_war/kernel/cw_intention.py`；`sr-od-test/` 镜像（生成器单测/锁定语义测试/计分域测试改写）。
**依赖**：无（与 3.1 可并行，同文件时按序提交）。
**优先级建议**：9。
**完成判据**：
- 库恒 10 条、名字/字段合并/校验五条对照 transition-combos.md §2/§4；
- 锁定语义：组合成型才锁（仙舟3+DOT2 两羁绊齐 + 三人在板）；单羁绊凑出（仅仙舟3 成型）任何组合 fp < 1.0 不锁——测试锁行为；
- 冷启动见即买并集 = 五块计分域并集（与旧库并集等值核对）；
- 词缀减分：量子熄火局含量子/贝键 7 条组合各减分、其余 3 条组合上位——排序测试（7 + 3 = 库容 10）；
- 完成前常规检查。
**验收凭据形式**：测试名清单 + 生成条目 10 条人工过目记录。

## 3.3 or_reqs 退役符号清理

**范围**：详设三符号集中清单 9 项逐符号删除（Comp.or_reqs 字段 / form_progress OR 段 / 校验③ / SEELE 常量 / deploy_search 三函数与希儿伪键三分支 / cw_line_facts SEELE_SYSTEM 落地批定位处置 / 测试镜像）。**不含**：kernel 结算侧谓词族（契约 D 保留面，一行不动）。
**设计依据**：details/or-reqs-cleanup.md 全文；总纲契约 A/C。
**文件面**：`src/sr_od/application/currency_war/kernel/cw_comps.py`、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/deploy_search.py`、`src/sr_od/application/currency_war/knowledge/cw_line_facts.py`（按落地批 grep 定位）；`sr-od-test/` 镜像。
**依赖**：3.1 + 3.2。
**优先级建议**：8。
**完成判据**：
- 退役符号 grep 清零（清单符号级；`SEELE_SYSTEM`〔cw_line_facts 公开常量，telemetry RHO_SYSTEM_KEYS 消费〕、`seele_system_formed`、`SEELE_AMP_FACTIONS` 不在清零域——契约 D 保留面；`_SEELE_SYSTEM_KEY`〔deploy_search 私有副本〕在清零域）；
- form_progress 收敛形态对照 or-reqs-cleanup.md「收敛后的形态」；
- 非希儿线行为逐位恒等（迁移恒等测试）+ 部署评分希儿键组改羁绊族键后的圈人对照；
- 完成前常规检查 + 全量测试。
**验收凭据形式**：符号级 grep 记录 + 测试名清单。

## 3.4 过渡侧货架资格虚拟评估臂

**范围**：shop.py 过渡资格臂接入（虚拟计分 top3 组合计分域成员 = 资格名单；触发窗 = 过渡未锁定 ∧ 未终局锁定；金不足/备战满复用 `_acquire_yield` 骨架）。**不含**：终局资格臂改动、候选槽写虚拟结果（即算即用零持久化）。
**设计依据**：details/virtual-eval-arm.md 全文；总纲契约 B。
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`（主体）；`sell_gate.py`（LAUNCH_CAUSE_BY_ARM 买因注册——A4 硬闸必需接入）；`telemetry/schema.py`（键表注释同步，遥测零新增键）；`sr-od-test/` 镜像。
**依赖**：3.2（transition_scores 纯函数）。
**优先级建议**：7。
**完成判据**：
- 资格判定对照 virtual-eval-arm.md §1——独立生效域例：持爻光 + 货架佩拉（佩拉 ∈ 希儿贝2 块计分域 ∧ ∉ 实候选成员并集 ∧ ∉ 终局资格域）→ 过渡资格买入（买因 transition_shelf_qualify_buy）；双资格路由例：持铁三角二人 + 货架丹恒·饮月 → 终局资格臂先消费（买因 shelf_qualify_buy）。（原钦点例「铁三角二人+货架藿藿」经落地批实证不构成本臂独立验证场景——藿藿同在实候选并集与终局资格域内、被前置臂消费；详设 §4-① 例已同步修正）；
- 触发窗两锁定态零行为变化；
- 实机首局观察记录（行为验证沿 comp-structure-unification 口径：不做 A/B 模拟对照，退化发现通道 = 实机对局遥测判读）；
- 完成前常规检查。
**验收凭据形式**：测试名 + 实机首局观察记录指针。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新权威版本文档。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列权威版本文档。
**依赖**：3.1–3.4 全部。
**优先级建议**：0。
**完成判据**：清单清零；权威版本与实现一致；黑话终扫（迭代全部文件面按统一术语表扫描，含本迭代 changes/ 产出文档自身）。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/currency_war/strategy-docs/12_line_and_intention.md`（线与意向：过渡候选域 4→10 组合制、单羁绊不锁语义、虚拟评估臂）← 3.2/3.4
- `docs/develop/sr_od/application/currency_war/strategy-docs/24_deploy_segment.md`（部署分段：L1 键组的 OR 折叠/希儿伪键措辞删除）← 3.3
- `docs/develop/sr_od/application/currency_war/strategy-docs/10_prep_decisions.md`（字段存留表：or_reqs 行删除、希儿量子档位措辞）← 3.1/3.3
- `skills/sr-od-dev-currency-war/references/comp-definition.md`（schema 分层语义：形态端口段改写——OR 分支退役声明、过渡组合制指针）← 3.1/3.2/3.3
- `docs/game/currency_war/research/transition_combos.md`（策略消费指引段：组合候选域从「≤10 对」描述改为已落地组合条目制指针）← 3.2
- `docs/game/currency_war/research/final_comps/final_seele_quantum.md`（无义务——改 COMP_LIBRARY 不触发文档同步，协议见 compo-knowledge；仅当措辞引用 or_reqs 时随批清理）← 3.3
- 代码注释中的 changes/ 详设指针迁移：本迭代在代码/测试注释里留下的 `changes/2026-11-05-or-reqs-retirement/...` 指针，随正本更新一并改指权威版本对应节（changes/ 目录日后删减会使指针悬空）← 3.2/3.3/3.4
