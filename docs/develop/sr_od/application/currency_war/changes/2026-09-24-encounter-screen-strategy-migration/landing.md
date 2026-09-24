# 遭遇画面策略层迁移与判据激活 落地

## 3.1 策略层新核与单帧锁
**范围**：①钻石检测集单一源迁移（零行为变化的基建搬移）：`DIAMOND_EQUIP_NAMES` 定义自 `obs/cw_node_obs.py` 迁 `kernel/cw_obs_core.py`，消费方 import 源改指（`obs/cw_node_obs` 自身、kernel `cw_encounter_selection.reward_tier` 现役 import 行——仅改 import 源零语义）；②新建 `strategies/impl/mandate_v1/encounter_pick.py`（决策入口 `decide` + 纯值出口 `EncounterPickDecision`/`EncounterRefreshSuggestion` + `_kappa_state` 连体〔含 fill 分支与 `_FILL_EDGE_THRESHOLD`〕+ fill 双定谳槽 + `reward_tier` 与四档常量 + 边缘 cap 立场常量（【拍】登记表落点 = 立场常量区集中，design §2.2；**实现期修订：立场两值已裁定（2026-09-24，过目记录 = design §2.2/§2.10 与迭代 README 回写），直接落过目值**；fail 向分支保留 = 常量置 None 的重拍回退机制，单帧锁覆盖）+ `_lowest_idx` 语义 + `apply_calibration`/`reset_calibration`（策略层注入口，合法键 = fill 双键；立场两值为常量非注入，design §2.3），钻石检测集自 kernel 出口消费）；③测试仓落新决策本体单帧锁（含重拍回退态）。边界：不改 flow/bridge 任何现役接线（本阶段新核未接，选档生产行为零变化）；不动 EV 核。边界：不改 flow/bridge 任何现役接线（本阶段新核未接，选档生产行为零变化）；不动 EV 核。
**设计依据**：design.md §2.1/§2.2/§2.3/§2.4
**文件面**：`kernel/cw_obs_core.py`（接收检测集单一源）；`obs/cw_node_obs.py`（定义迁出改 import）；`kernel/cw_encounter_selection.py`（仅 import 源行）；`strategies/impl/mandate_v1/encounter_pick.py`（新建）；`sr-od-test/test/sr_od/application/currency_war/test_cw_encounter_pick.py`（新建）
**依赖**：design §2.2 同一裁决门（定稿呈报过目）——本阶段落码**含**未过目 fail 向分支（None 期暗装等价，无章程真空窗）；立场两值注入随过目记录在 3.2 接线前完成
**优先级建议**：5
**完成判据**：
- 决策行为对照 design.md §2.2 决策序（单帧锁覆盖 §2.12 锚点 1–6：窗口不足独立态/κ_S 三态×可及集矩阵/边缘 cap/tiebreak/经验档层/闸内嵌两臂/因词封闭枚举含 dark-fallback）
- 全仓 `DIAMOND_EQUIP_NAMES` 单一源 = `kernel/cw_obs_core.py`（grep 定义唯一点）；现役选档行为零变化（reward_tier import 改源前后行为等价）
- §12 通用工程门（引用，不复述）
**验收凭据形式**：测试名（单帧锁全绿 + `ruff check` 改动文件）

## 3.2 接线原子切换与删除面
**范围**：同一 commit 原子切换——`flow.decide_encounter` 改调 `encounter_pick.decide`（`refresh_used` 预计算删除）；`bridge.decide_encounter` 覆写删除（回落基类，被删覆写专属 import 按 ruff F401 实测清收）；kernel 删除面（`cw_events.decide_encounter`/`_option_mechanics`/`_reward_value`/`EncounterPick`/`EVENT_PICK_TYPES` 与 `EventPick` 的 EncounterPick 位及被删函数专属 import〔`form_progress`/`merged_mechanic_tables`/`mechanics_fit`/`deployed_count_of`/`max_units_of`/`plane_of` 等，以 ruff F401 实测为准〕；`cw_encounter_selection` 判据与标定面迁出〔design §2.7 清单；`D_ENC_VARIANT` 与其 kernel 注入口保留〕；`cw_survey19_hooks.encounter_tier_score`）；测试面随迁（`test_cw_unified_action_4.py` 替身改词表动作实例；`test_cw_obs_arch_event_screens.py` 重调行为锁改写〔防线行为，见下〕）；**刷新锚读缺防线随批落**（`cw_screen_encounter` 重调分支：重调仍返 Suggestion ∧ 刷新锚读缺 → `round_fail` 交回计入外循环重派上限——替换现「零点击 round_success 交回」，design §2.5 已定谳外循环对后者无防护；op 层除此外零行为改动）；EV 核处置**已裁定退役删除**（删 `encounter.py` + provisional 双槽 + provisional 头部指针句）；**注释收口**：provisional 头部标定注入指针句改指策略层、flow `decide_encounter` docstring「kernel 按原评分」句、op 层旧判据叙述（`cw_screen_encounter`）、钻石检测集单一源表述两处（`cw_events.py` SupplyOption docstring / `supply.py` 头部，改指 `kernel/cw_obs_core` 单一源）；`cw_economy.py` 败补 docstring 消费点清单改写（encounter.py 引用随删件失指）。边界：不改 sim 文件；不动 `claim_encounter_reward`/`record_settlement_row`/`SettlementRing` 等保留面；`cw_difficulty_account` 只收口注释不删码。
**设计依据**：design.md §2.5/§2.6/§2.7/§2.8/§2.10 裁定点 1
**文件面**：`strategies/impl/flow.py`、`strategies/impl/mandate_v1/bridge.py`、`strategies/impl/mandate_v1/encounter.py`（删）、`strategies/impl/mandate_v1/audit/provisional.py`（删双槽 + 指针句）、`strategies/impl/mandate_v1/supply.py`（仅注释）、`kernel/cw_events.py`、`kernel/cw_encounter_selection.py`（判据迁出 + 段注释收口）、`kernel/cw_survey19_hooks.py`、`kernel/cw_difficulty_account.py`（仅注释）、`kernel/cw_economy.py`（仅注释）、`kernel/cw_vocab.py`（docstring）、`obs/cw_node_obs.py`（docstring 收口）、`operations/cw_screen/cw_screen_encounter.py`（注释 + 防线一处）、`strategies/impl/cw_strategy.py`（注释）、测试仓对应文件
**依赖**：3.1（过目记录已在案：三项裁定 2026-09-24 回写 design §2.2/§2.10 与迭代 README）
**优先级建议**：5
**完成判据**：
- 生产链行为对照 design.md §2.12 行为变化申报（暗装退场/能力驱动/刷新阀/tiebreak/防线一处）；kernel 无指向 strategies 的 import、策略层无 obs import。零残留验证两段：①**迁移符号旧址零残留**（`kernel/cw_encounter_selection.py` 与 `kernel/cw_survey19_hooks.py` 两文件内 grep）：`EncounterPick`/`decide_encounter`/`encounter_tier_score`/`F_MIN`/`G_BASE`/`DELTA_T`/`g_ratio`/`_d_enc_snapshot`/`_Diagnostics`/`_kappa_state`/`reward_tier`/`_lowest_idx`/`_FILL_EDGE_THRESHOLD`/`REWARD_TIER_LAST`/`_option_mechanics`/`_reward_value`（`D_ENC_VARIANT` 保留 kernel——装填语义消费，不在零残留集，design §2.3）；另断言 `cw_events` 的 `EVENT_PICK_TYPES`/`EventPick` 已无 `EncounterPick` 位；②**代码面全仓词边界 grep 零命中**（src + 测试仓 .py，不含 .md 文档）：`EncounterPick`（词边界，不含 `EncounterPickDecision`）/`F_MIN`/`G_BASE`/`DELTA_T`/`encounter_tier_score`/`REWARD_TIER_LAST`/`_option_mechanics`/`_reward_value`（策略层注入口 = fill 双键；`D_ENC_VARIANT` 注入口留 kernel，design §2.3）
- 受影响测试全绿（含保留面 `claim_encounter_reward` 分支锁零改动）；`ruff check` 改动文件；L2 点名集（SKILL.md 测试分层行）
- §12 通用工程门（引用，不复述）
**验收凭据形式**：测试名 + grep 输出（零残留两段）+ L2 全绿
**落地检查项 → 已定谳**（design §2.5）：外循环对「建议刷 ∧ 锚读缺」重进循环无防护（直调 `cw_loop.py`：`OP_FAIL_REDISPATCH_LIMIT` 只计连续 fail，零点击 round_success 交回不计数且清零窗）——处置 = **防线定谳随本阶段落**（`cw_screen_encounter` 重调分支改 `round_fail` 交回计入重派上限；行为变化申报、行为锁改写、完成判据同步），不另挂账；实机锚 ⑦ 为哨兵（防线后不应再见循环形态，出现即回设计层）。**补给孪生面挂账**：`cw_screen_supply_node` 重调分支存在同款「建议刷 ∧ 锚读缺 → 零点击终结」循环面（30 号稿落地后 `supply.decide` 可返 Suggestion 即激活）——同款防线归补给域后续批，登记 31 号稿挂账并交接（design §2.11）。

## 末阶段：3.3 正本更新
**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节 + design.md §2.9
**文件面**：清单所列正本文档
**依赖**：3.1、3.2
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致（31 号稿判据语义 = `encounter_pick.py` 现态；25/13/08/04 号稿无过期遭遇描述）
**验收凭据形式**：文档对照 review

## 正本更新清单
- `strategy-docs/31_encounter_screen.md`（新建）← 3.1/3.2（判据语义 = 落码现态；裁定登记〔含【拍】立场登记过目记录与章程 §6 修订提案〕/数学挂账 = 比值腿复活·E-3 标定含 fill 阈值登记义务·EV 形态挂 P26·档位↑⇒奖励价值↑采样验证·P2 序列两源对账·窗口战斗类变体触发器·补给孪生面防线交接/sim 盲区）← 3.3
- `strategy-docs/25_event_overlays.md`（画面族清单移除遭遇：头注/§1 prose/§2 表行 + 「已拆 31 号稿」头注）← 3.3
- `strategy-docs/13_pick_family.md`（`decide_encounter` 行「双轨」过期描述改单一源指 31 号稿；E3 目录行同改）← 3.3
- `strategy-docs/08_events.md`（E3 行「现有语义」格替换为能力态直通形；「判据状态」维持待 derive；锚不变）← 3.3
- `strategy-docs/04_survival_budget.md`（裁定 9 行「判据正本」指针改策略层；同行补判据结构合法性载体分层）← 3.3
- `strategy-docs/README.md` §2（增 31 行；导航句 18-30 → 18-31）← 3.3
- 画面文档策略指针面（`screens/encounter.md` 的决策委托/刷新闸行为叙述句、`docs/game/screens/currency_war_encounter.md` 的算法描述句，落批全路径核对）← 3.3
