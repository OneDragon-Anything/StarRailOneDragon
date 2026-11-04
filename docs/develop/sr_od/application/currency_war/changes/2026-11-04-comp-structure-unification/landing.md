# 阵容结构统一（comp-structure-unification）落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集；行为批另加全量）；
- **术语清理（design 方案 5，各阶段承载）**：本阶段文件面内代码注释与文档的**存量黑话**按统一术语表 `docs/develop/sr_od/application/currency_war/terminology.md` 清理——替换表内的词按表列白话改写（存量与新写同判）；保留词首次出现带定义；不改动代码真名与游戏内容词；不做本阶段文件面之外的回溯清理；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」「文档规范·术语使用」节。

## 3.1 羁绊优先级结构落地

**范围**：`faction_reqs` 结构 + 统一读口 + 建库校验 + 21 套数据迁移 + 全消费面读点替换（含配方伪阵容构造点迁移与线距离防御式读改造）+ 副档两处语义修正 + 迁移恒等测试。**不含**：克制表改造（3.2）、过渡库（3.3）、任何数值知识变更。
**设计依据**：details/faction-priority.md 全文（§4 表含 cw_recipe/cw_line_switch 两行硬阻断项）。
**文件面**：`kernel/cw_comps.py`（结构/读口/校验/数据）；`kernel/cw_recipe.py`（构造式迁移——3.3 才整模块删，本阶段先改构造不删模块）；`kernel/cw_line_switch.py`（防御式读改直读）；`kernel/cw_intention.py`（pair_target_comp 构造 + :544 首键读法）；`strategies/impl/mandate_v1/pick_common.py`（punished_mechs_of 改读档 0 读口，中间态）；`tools/cw/proofs/p65_check.py`（读口机械迁移保活，3.3 冻结）；`kernel/cw_plugins.py`（:17/:115 source 字符串含「sub_tiers 对拍锚」等过时引用，随字段删除随手清理）；其余消费面以 faction-priority.md §4 表为准（cw_invest_channels/cw_launch_admission/deploy_search/flow/cw_events/cw_exec_state/cw_investments/invest_env/invest_strategy/sim/power_model/features.py）；`sr-od-test/` 对应镜像。
**依赖**：无。
**优先级建议**：10。
**完成判据**：
- 行为对照 details/faction-priority.md §4 映射表：除变化①②（副档投资分/轮廓计数，单列断言）外全部逐位恒等；
- `Comp(form_tiers=…)` 构造全库零残留（grep 含关键字参数形态）；cw_line_switch 线距离纳入恒等快照；
- 建库校验五条全部生效（非法数据 import 即炸）；
- 迁移恒等测试全绿（快照构造见 faction-priority.md §7）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名清单 + 迁移对照表（21 套 faction_reqs 全量，人工过目记录）。

## 3.2 克制表直写

**范围**：`AFFIX_COUNTERS_FACTIONS` 直写表 + 判定改档 0 键 + 三张表删除 + 两消费文件调用改写 + 测试同步删。**不含**：词缀效果域、线分词缀面。
**设计依据**：details/counter-tables.md 全文（§2 含调用改写式）。
**文件面**：`kernel/cw_comps.py`（表删除）、`strategies/impl/mandate_v1/pick_common.py`（新表+判定+删 punished_mechs_of）、`strategies/impl/mandate_v1/invest_env.py` 与 `invest_strategy.py`（调用点改写，行号见详设 §2）、`src/sr_od/application/currency_war/currency_war_config.py`（注释 :37 随手清理——currency_war/ 根，非 config/ 子目录）、`data/affix_effects_data.py`（:11 残留）、`obs/cw_briefing_obs.py`（:54/:90/:357 残留）、`kernel/cw_affinity_table.py`（:97 残留）；`sr-od-test/` 镜像。
**依赖**：3.1（档 0 读口）。
**优先级建议**：9。
**完成判据**：
- 活链路 2 条（净化/永久创伤）行为逐位恒等（载体 = 3.1 迁移恒等测试的受克判定断言位）；
- **`src/` + config 生产代码**三张表符号零残留（grep 核对；strategy-docs/docs-game 的文档引用归权威版本更新批，不在本判据域）；
- 完成前常规检查。
**验收凭据形式**：测试名 + grep 零残留记录。

## 3.3 过渡阵容库与配方决策层退役

**范围**：`TRANSITION_LIBRARY` 注册表（4 条，数值按详设口径，过渡条目全量人工过目）+ 候选/锁定机器（cw_intention 落位）+ 冷启动回退承接（k_empty_window_fallback 替代 + 冷启动买入分支/保护集键域改读过渡库）+ committed_authority 序②替代 + **过渡机制关闭判据换轴**（三处按位面关闭的判定统一改为读终局锁定态：recipe_members 判窗/protection 整域关闭/囤货位面分支——生命周期挂钩终局锁定事件，用户裁定）+ 四侧接入（priority/囤货/部署圈人/部署开局面方向）+ 配方决策层退役（详设「退役符号集中清单」逐符号；**数据层保留边界**见详设）。
**设计依据**：details/transition-library.md 全文。
**文件面**：`kernel/cw_comps.py`（注册表）、`kernel/cw_intention.py`（状态机/槽语义/committed_authority/囤货与回退/槽下游四消费点）、`kernel/cw_recipe.py`（整模块删除）、`kernel/cw_system_cards.py`（组合决策层删除，数据层保留）、`kernel/cw_transition.py`（:45/:58 docstring 引 p1_pair 的注释清理）、`strategies/impl/mandate_v1/`（priority/deploy_search/shop/session_scope/sell_candidates/contracts/decision_payload/protection/economy_cycle/statefn/predicates/entry 接入改造与键域改造）、`strategies/impl/mandate_v1/mandate_state.py`（字段删除）、`strategies/impl/flow.py`（物化链写端）、`strategies/impl/cw_strategy.py` 如涉及（bridge 链方向读点，落地批 grep 定位）、`kernel/cw_deploy_logic.py`（TRANSITION_TRAITS 消费与按位面判定换轴连带）、`kernel/cw_registry.py`（P1 锁定帧相关键）、`knowledge/cw_line_facts.py`（注释性引用如有）、`telemetry/schema.py`（sess_p1_pair 写源改、sess_framework 删键）、`tools/cw/proofs/p65_check.py`（文首冻结标注）、`kernel/cw_plugins.py` 与 `kernel/cw_bridge_pool.py`（存量注释中对退役符号的悬空引用随批清理）；`sr-od-test/` 镜像。**不动的文件**（数据层消费链）：`knowledge/cw_engine_facts.py`、`telemetry/cw_win_model.py`、`kernel/cw_battle_calib.py`、`telemetry/match_archive.py`、`tools/cw/ab_judge.py`、`tools/cw/win_model_m1.py`、`tools/cw/proofs/p15/p15v2_fit.py` 及其余 proofs 脚本（按详设裁定表）。
**依赖**：3.1。
**优先级建议**：8。
**完成判据**：
- 行为对照 details/transition-library.md §7 申报六条——**实机首局观察记录**承担行为验证（用户 2026-11-04 裁定：本迭代不做 A/B 模拟对照；行为退化发现通道 = 实机对局遥测判读，不设模拟门）；
- **退役符号白名单 grep 清零**（白名单 = 详设「退役符号集中清单」逐符号；`TRANSITION_TRAITS`/`SYSTEM_CARDS`/`sess_p1_pair` 等保留符号**不在**白名单——判据按符号级，不按字符串盲 grep）；
- **换轴归类复核**（详设 §5 裁定注）：`plane2_started*` 全库消费点逐点归类——过渡机制开关节点全部已换轴为终局锁定态、无关用途保留原判，清单与代码一致；
- 数据层消费链零破坏（`tools/cw/ab_judge.py` 可运行 = engines_count 供给未断）；
- **建库校验③落地**（or_reqs ⊆ 档 0——3.1 悬置项，冲突源 pair_target_comp 已随本阶段退役，faction-priority.md §5）；
- 过渡条目全量数据人工过目记录；
- 完成前常规检查 + 全量测试。
**验收凭据形式**：符号级 grep 记录 + 条目过目记录 + 实机首局观察记录指针。

## 3.4 富余买入并入压牌库与 P88 退役

**范围**：dominance_buy 通道删除（含 sell_gate 映射键与 contracts 契约键）+ M6 一星兜底带 + P88 全套退役。
**设计依据**：details/press-stockpile.md 全文。
**文件面**：`strategies/impl/mandate_v1/shop.py`、`strategies/impl/mandate_v1/mandate.py`（含 :958-979 调用段）、`strategies/impl/mandate_v1/sell_gate.py`（注：在 mandate_v1/ 下、非 criteria/ 子目录）、`strategies/impl/mandate_v1/criteria/contracts.py`、`kernel/cw_deploy_logic.py`、`tools/cw/proofs/p88_check.py`（删除）、`docs/develop/sr_od/application/currency_war/proofs/p88.md`（文首退役标注，原地保留可溯）、`sr-od-test/` 镜像（含 `test_sell_window_launch.py` 键集期望更新、`test_dead_stock_pair.py` 直调断言改写）。
**依赖**：3.1 + **3.3**（M6 名单源耦合，见 design 契约 D）。
**优先级建议**：7。
**完成判据**：
- M6 兜底带行为符合 details/press-stockpile.md §2；特殊帧（终局锁定 ∧ 未成型 ∧ 上场满员）买入手数变化经实机首局观察记录（同 3.3 口径：不做 A/B 模拟对照）；
- P88 符号零残留（`swap_transition_narrow_frame`/`swap_bond_gate_domain_of`/`PRESS_NARROWED_ARMS`）；
- 死库存防线在兜底带生效（测试：断新生对拦截）；
- 完成前常规检查 + 全量测试。
**验收凭据形式**：grep 零残留记录 + 测试名 + 实机首局观察记录指针。

## 末阶段：正本更新

（「正本」= 权威版本文档；节名「正本更新」「正本更新清单」沿用迭代设计模板固定名，不按术语表替换。）

**范围**：按「正本更新清单」逐条更新权威版本文档。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列权威版本文档。
**依赖**：3.1–3.4 全部。
**优先级建议**：0。
**完成判据**：清单清零；权威版本与实现一致；**黑话终扫**（design 方案 5）——迭代全部文件面（含正本更新清单触及文档 + **本迭代 changes/ 产出文档自身**——过程稿不回溯但新写稿守表）按术语表扫描清零（扫描方式 = 术语表 §1 替换表逐词 grep 本迭代文件面清单 + §2 保留词首次定义抽查）；**历史证明文档豁免**——`proofs/` 下已标注退役指针的篇目（p88.md 等）按留档原文不清理（改写破坏「留档可溯」，黑话清理义务对其豁免）。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `strategy-docs/12_line_and_intention.md`（线与意向：候选/成员/知识卡字段口径；姬子 A/B 拆分行的 sub_tiers 措辞；投资通道的目标线口径）← 3.1/3.2/3.3
- `strategy-docs/10_prep_decisions.md`（字段存留表：form_tiers/sub_tiers 行 → faction_reqs；**克制表行**——「MECHANIC_COUNTERS 留」措辞随三张表删除更新）← 3.1/3.2
- `strategy-docs/24_deploy_segment.md`(部署分段：L1/L2 键集口径的 form_tiers/sub_tiers 措辞) ← 3.1
- `strategy-docs/28_invest_env_screen.md`（投资环境屏：护栏指向集的目标线口径）← 3.1/3.2
- `strategy-docs/13/29/16 号稿`（三张表符号与克制机器的活引用措辞——落地时逐篇 grep 定位）← 3.2
- `strategy-docs/32_unified_sell_priority.md`（让位序：recipe_members 语义/配方伪锁帧注）← 3.3
- `strategy-docs/README.md`（模块地图：cw_recipe 条目删除/cw_system_cards 边界声明）← 3.3
- `docs/develop/sr_od/application/currency_war/` 的 sim-power-model 相关权威版本文档（form_tiers→core_faction_reqs 映射口径）← 3.1
- `proofs/` 目录（P65/P88 相关篇随脚本处置同步标注退役指针）← 3.3/3.4
- strategy-docs 中 dominance_buy 与 P88 口径的篇目（落地时 grep `dominance_buy|swap_bond_gate` 在 strategy-docs 的命中篇，逐篇更新）← 3.4
- `skills/sr-od-currency-war-dev/references/comp-definition.md`（本仓 skill：schema 分层语义字段族表）← 3.1/3.3
- `docs/game/currency_war/`（克制三张表引用 4 处措辞——数据值不变原则下仅措辞核对）← 3.2
