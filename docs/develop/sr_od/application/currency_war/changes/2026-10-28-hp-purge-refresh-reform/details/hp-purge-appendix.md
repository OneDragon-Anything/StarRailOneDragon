# hp 判据族删除 · 执行单一源快照（hp-purge-appendix）

> 本文件由 3.1 落地批按 details/hp-purge.md §7 快照义务抄录生成，是 3.1 执行单一源。四份证据与裁定文件原文寄存 .debug（gitignore 区，寿命独立于迭代），本快照保留原貌（含清查件内部编号错位，不重排）；.debug 原件此后仅作溯源参考。残留扫描词表一并快照如下（取自 details/hp-purge.md §6）。
>
> 快照来源（2026-10-28，3.1 开工前抄录）：
> 1. hp 逻辑清查件 = `.debug/temp/2026-10-28_hp逻辑清查.md`
> 2. P2 金滞留支出链追查件 = `.debug/temp/2026-10-28_P2金滞留支出链追查.md`
> 3. 单局复盘件 = `.debug/currency_war/deep_review/g_20261028_011013.md`
> 4. CW 修复工作清单（裁定载体）= `.debug/temp/2026-10-28_CW修复工作清单.md`

### 6. 残留扫描验收（裁定 #3）

- **扫描时点与范围分层**：3.1 阶段收尾对**符号级词表做全仓扫描**（词表逐符号唯一、无误捕风险，全仓安全）＋ 本篇文件面结构核对；`docs/` 残留扫描归**末阶段**（正本章删除发生在末阶段，此前扫必然不清零）。
- **词表（符号级，可清零口径——被删符号清单，逐符号对照 hp 清查件 B 组/A 组裁定）**：`p2_crisis|blood_budget|blood_xp_gate|levelup_blood_gate_defer|crisis_stop_hp|levelup_crisis_defer|level_spend_blocked|all_in_xp_domain_hit|is_emergency|emergency_hp|p1_levelup_stop_hp|p2_levelup_stop_hp|DIFFICULTY_HP_TABLE|HP_QUALITY_ALARM|form_floor|p1_exit_blood_target|k_linear|k_hp_calibration_grid|blood_margin_low_hp|k_alert|effective_hp_threshold|HP_SAFE_THRESHOLD|HP_BAND_MID`。
  - **不过扫符号（R-1 保留面 + 避免过度捕获）**：`decision_hp`（R-1 保留 = 经验批支付门读口，行为零变化）；`blood_xp_full_clicks`（全量击数算术保留）；`blood_xp_mode`（B-19「改」类条目，随 R-1 币种通式联动核，非删）；`refresh_ev_budget`（清查件 A-9 处置 = 删归零支**非删函数**，符号保留、diff 核对归零支消失）；`p1_blood_floor|p2_blood_floor`（R-7 保留裁定，观测谓词）；`p2_handoff_*`（handoff 快照/数据面保留键，仅 `handoff_boss_e_damage` 等清查件 B-4 明列投影参数删除——精确列名不扫裸前缀）。
  - `levelup_blood_gate_defer` 处置声明（R-1 连带）：门⑥改名「经验批支付门」后旧拒因键清零，新拒因键 = `xp_batch_payment_defer`（币种通式语义）。
  - `p2_supply_horizon|line_completion_feasibility|no_target_arms|hoard_target_set|k_empty_window_fallback` = **保留-改口径符号**（不在清零词表，验收 = diff 核对无 hp 读取）。
- **宽词族（hp/血/危机/crisis）不作符号级清零判据**——C 组观测面合法保留 + game 侧 R-8 挂账，宽词扫描仅作末阶段辅助盘点，命中行逐条归类（保留依据/漏删申报），豁免清单随残留申报一并出具。
- 多行形态模式或 AST 扫描（防跨行绕过，进度账本验收协议条款）。**符号级残留清零 + 漏删申报零条 = 本篇完成必要条件。**

---

# 快照一：hp 逻辑清查（源 = .debug/temp/2026-10-28_hp逻辑清查.md）

# 货币战争（Currency War）「hp 用作策略逻辑」全量清查

- **清查日期**：2026-10-28
- **代码基线**：`a42f1e2cd6e462472d5a768e130c006cdf4ac6ee`（2026-10-28 01:01:20 +0800，货币战争:随机角色授予采样域牌库时点过滤 + 登记仙舟概念股(1008)）
- **用户裁定原文（2026-10-28，本次清查依据）**：「我们现在最新的策略核心是，只要我们策略是正确的，hp 自然是没问题可以通关的，所以策略侧不应该考虑 hp」。含义：**hp 是对局结果，不是策略决策的输入**——策略器做买牌/升级/刷新/阵容/投资决策时，判据里不该出现 hp；「hp 低于某线就做/不做什么」的策略逻辑 = 过期设计。
- **清查方法**：对 currency_war 域全部源码（strategies/kernel/sim/obs/operations/telemetry）与双侧文档（develop/game）做宽词全量扫描（词族见 §5），逐命中读上下文，判据 = 该处 hp 是否参与「做什么决策」的分支/门/授权，不是出现 hp 就算。
- **与缺陷 A1 的关系**：A1（危机带拦截下无支出出口，实证局 g_20261028_011013，seed=20260118，死亡@P2r5）的病灶组件在本文 A 类清单内——危机带拦截（A-1/A-3）、血预算停升级（A-2）；A-9（应急带刷新归零）经交叉复核对 mandate_v1 刷新发射零行为差（消费端 = 遥测披露面，见 §2.1 A-9 与 §3 R-2），**不是 A1 病灶组件、非修复前置**。修 A1 时按本清单一次性清理，勿二次排查。

**术语（首现定义）**：危机带 = P2 位面「血量 ≤ 约两次败局伤害(≈41)」的停付区间；血预算 = 当前血量按「每战期望掉血」折算的剩余可承受败局轮数；血闸 = 血本位局「血余额 ≥ 整级血成本才买经验」的支付能力检查；血本位局 = 持有「奋斗协议」等把购经验币种从金币改成血量的投资卡的局；ALL IN 窗 = 位面末最后一战「花光」豁免窗；挂空 = 函数/参数仍在代码但生产调用面为空（只被测试经桥调用或零调用）；孤儿 = 常量/字段/登记项已无任何消费方。

---

## 1. 聚合删改清单（修「危机带」问题时要动的全部条目索引）

> 按 A→B→D→E 组排；每行 = 编号 + 锚 + 一句话处置。明细与依赖关系见 §2–§4。

### A 组（策略决策逻辑读 hp——核心删改区）
| 编号 | 锚 | 处置 |
|---|---|---|
| A-1 | kernel/cw_discipline_rules.py:212-232（p2_crisis_stop_hp） | 删（危机带血线 ≈41 推导） |
| A-2 | kernel/cw_discipline_rules.py:235-260（p2_crisis_band 谓词） | 删（危机带谓词本体） |
| A-3 | kernel/cw_discipline_rules.py:154-209（blood_budget_levelup_blocked 血预算停升级门） | 删 |
| A-4 | strategies/impl/mandate_v1/criteria/levelup.py:484-514（level_spend_blocked 两支） | 删（判据组合口） |
| A-5 | strategies/impl/mandate_v1/criteria/levelup.py:370-377（升级资格门④ + levelup_crisis_defer 计数） | 改（删门④；发射门序 7 门变 6 门） |
| A-6 | kernel/cw_discipline_rules.py:82-128（all_in_xp_domain_hit，hp≤停升级线血侧半支，**已挂空**） | 删（零产线消费位） |
| A-7 | kernel/cw_comps.py:2862-3086（maybe_pivot 信号3 保命转型，**待办层挂空**） | 删或降级为纯观测（待裁决 R-5） |
| A-8 | kernel/cw_performance.py:244-268（is_run_dead 死局检测三门，**待办层挂空**） | 删或降级为纯观测（待裁决 R-5） |
| A-9 | kernel/cw_economy.py:1074-1088 + :1275（is_emergency 应急帧刷新预算归 0） | 删 = 仅改遥测义务账/v2 投影语义，mandate_v1 零行为差；非 A1 修复前置（交叉复核定案，见 §2.1 A-9 与 §3 R-2） |
| A-10 | strategies/impl/mandate_v1/criteria/levelup.py:385-392（升级资格门⑥血闸）+ kernel/cw_economy.py:792-882（blood_xp_gate 族） | **待裁决 R-1**（[40]② 已裁定支付能力检查） |
| A-11 | kernel/cw_intention.py:1067-1094（p2_supply_horizon 血预算视界）+ :1099-1150（line_completion_feasibility G 门）+ :1427-1530（arm_a_*/no_target_arms/hoard_target_set）+ shop.py:373 消费 | **待裁决 R-3**（P86 已证命题的判据重锚问题） |

### B 组（hp 判据支撑件——随主判据删则孤儿化）
| 编号 | 锚 | 处置 |
|---|---|---|
| B-1 | kernel/cw_discipline_rules.py:131-151（p1/p2_levelup_stop_hp 停升级线推导） | 删（随 A-3） |
| B-2 | kernel/cw_registry.py:164-209（血预算停手族参数块） | 删/收；其中 p1_exit_blood_target=60(:192)、blood_budget_refresh_stop_enabled(:204)、form_floor(:271) **零消费孤儿**可直接删 |
| B-3 | kernel/cw_registry.py:858 + :934-942（约束名 'blood_budget_stop' 与 slot 覆盖表行） | 删（arbiter 代码已删，登记残留） |
| B-4 | kernel/cw_registry.py:603-651（handoff 承接门 hp 维投影参数：handoff_boss_e_damage 等） | 删（消费代码 handoff_gate_gap 已删，孤儿） |
| B-5 | kernel/cw_registry.py:695-719（k_alert/k_linear/k_hp_calibration_grid/blood_margin_low_hp/boss_tax_p75_by_plane） | 删（零消费孤儿） |
| B-6 | kernel/cw_hp_policy.py 全文件（decision_hp/hp_decision_trusted_of 读口政策层） | 改：decision_hp 随 A 组孤儿化可删；hp_decision_trusted_of 保留（观测面仍消费） |
| B-7 | kernel/cw_discipline_rules.py:44-56（hp_decision_trusted 薄委托） | 随 B-6 处置 |
| B-8 | kernel/cw_economy.py:135-141（HP_SAFE_THRESHOLD/DIFFICULTY_HP_TABLE 保血阈值表）+ :213-252（effective_hp_threshold） | 删（消费链只剩挂空的 maybe_pivot） |
| B-9 | kernel/cw_first_passage.py 全模块（first_passage_win/hp_floor/plane_hp_ratio/p_win_lambda/risk_posture 首达生存模型） | 待裁决 R-6 附带（现役唯一消费 = effective_hp_threshold → 挂空链；模型本体是「18 号」标定工件） |
| B-10 | kernel/cw_economy.py:676-680（HP_QUALITY_ALARM/HP_DISTRESS_FRAC） | 删（零消费孤儿；HP_QUALITY_ALARM 仅注释自引） |
| B-11 | strategies/impl/mandate_v1/statefn/predicates.py:125-185（p1_blood_floor/p2_blood_floor 濒死带谓词） | 改（现役消费 = 纯观测分键；随 A 组删后是否保留观测读口待裁决 R-7） |
| B-12 | strategies/impl/mandate_v1/statefn/lambda_death.py:34-39/:121-146（hp_band 血带维 + make_key 键构造） | 保留或随观测面裁（λ 表本体 = P51 标定工件，裁定二已裁概率侧合法） |
| B-13 | strategies/impl/mandate_v1/criteria/refresh.py:160-165（crisis_refresh_invariant 纯数交叉核对函数）+ mandate.py:1078-1079（executor 序位声明） | 改（无行为消费；修 A1 若立「危机特批刷新支」才需要它，否则删） |
| B-14 | strategies/impl/mandate_v1/mandate_state.py:123-124（v3_blood_budget_rejects/refresh_rejects 计数器） | 删；:124 refresh_rejects 现已零写端孤儿 |
| B-15 | strategies/impl/mandate_v1/mandate_state.py:174（v3_handoff_hp_proj 孤儿字段） | 删 |
| B-16 | kernel/cw_economy.py:953-1000（get_node_goal 标量投影 hp 形参支）+ kernel/cw_game_state.py:4707-4746（scalar_projection_state hp 入参） | 改（投影支 = 迁移漏点诊断路径，生产恒走容器支；hp 形参可去） |
| B-17 | kernel/cw_vocab.py:64-69（DIFFICULTY_HP_TABLE/HP_SAFE_THRESHOLD/effective_hp_threshold re-export） | 删（随 B-8） |
| B-18 | strategies/impl/mandate_v1/audit/provisional.py:64（P_HIT_Q_CONV「P36-b/c 危机预算阶梯」拟槽） | 删或随 P36-b/c 一起退役（登记项） |

### D 组（文档面）
见 §2.4（develop 侧 ~20 篇）与 §2.5（game 侧 6 处），每篇给节锚与一句话语义。

### E 组（测试面）
见 §2.6（7 个测试文件、~12 个断言锚），锁 A/B 组行为的测试随主判据删改同步重写。

---

## 2. 分类明细

### 2.1 A 类·策略决策逻辑读 hp（核心删改区）

判据 = hp 直接参与「做什么决策」的分支/门/授权。

| # | 锚 | 引述/语义 | 删改建议 | 依赖关系 |
|---|---|---|---|---|
| A-1 | `kernel/cw_discipline_rules.py:212-232` | `p2_crisis_stop_hp(registry)` = 「P2 危机带血线 = ceil(2 × vd_p2_loss)≈41 血」——血预算「双失缓冲」算术 | 删 | 消费位 = p2_crisis_band(A-2)与 level_spend_blocked(A-4)；删它孤儿化 A-2 |
| A-2 | `kernel/cw_discipline_rules.py:235-260` | `p2_crisis_band(gs,session,registry)` = 「plane≥2 ∧ 门后 hp 真值 ∧ hp ≤ 危机带线」谓词；docstring 自述三个行为面共域（refresh 停付 P2 分支/arbiter 危机买入闸/M3 危机让位）——前两个消费面代码已删，现役唯一活消费 = A-4 | 删 | 删它孤儿化 A-4 的危机支；docstring 引用的 `blood_budget_refresh_blocked`/`_crisis_buy_gate_open` 均已不存在（过期注释，一并清） |
| A-3 | `kernel/cw_discipline_rules.py:154-209` | `blood_budget_levelup_blocked` = 「P21 已证：hp ≤ 停升级线内升级收益到账 ≥1 战之后 EV 严格负 → 拒绝购买经验」；hp 不可信帧 fail-closed 拒付 | 删 | 消费位 = A-4 第一支；拒付计数写 mandate_state.v3_blood_budget_rejects(B-14)；ALL IN 豁免(:190-191)随删——豁免语义「末战花光是时机不是血线判断」不受影响（豁免对象消失） |
| A-4 | `strategies/impl/mandate_v1/criteria/levelup.py:484-514` | `level_spend_blocked` = P21 血预算线（blood_budget_levelup_blocked）∨ P2 危机带（p2_crisis_band）两支，ALL IN 豁免共享 | 删（含 :423-449 的 `_plane_last_battle`/`terminal_all_in` 若再无消费则一并核） | 上游 = A-3/A-2；下游 = A-5 门④ |
| A-5 | `strategies/impl/mandate_v1/criteria/levelup.py:370-377` | 升级资格门④：「P21 危机带全域判定（无域内让位）……危机带帧无论金位一律拦」，命中计 `levelup_crisis_defer` | 改：删门④，资格门 7 道变 6 道；`levelup_crisis_defer` 计数键与契约登记（criteria/contracts.py:243-246、criteria/__init__.py:54-55）随删 | 门序声明在 upgrade_gate_verdict docstring(:300-306)；11_shop_decisions.md §2 与 02_mandate_layer.md M3 行同步改（D 组） |
| A-6 | `kernel/cw_discipline_rules.py:82-128` | `all_in_xp_domain_hit` = 位面末战 ∧ hp 真值可信 ∧ 门后 hp ≤ 停升级线的血侧半支谓词；docstring 自述「本谓词现无产线消费位，保留 = 停升级线血侧读口」 | 删 | 零产线调用（全仓仅定义）；随 A-3/A-1 的线一起删除，防误接线复活 |
| A-7 | `kernel/cw_comps.py:2862-3086` | `maybe_pivot` 信号3 保命转型：`hp < 0.75×effective_hp_threshold(gs)` → 切最快成型 easy 阵容，hp 危险时信号1/2 独占（:2921/:2934-2936 直读 gs.hp，:2929-2933 注释自申报「待办层（生产调用面空，测试仓经桥调用）」） | 待裁决 R-5（挂空死码：立即删 vs 保留待办姿态） | 依赖 B-8 effective_hp_threshold；消费 tracker.is_losing_streak（C-8） |
| A-8 | `kernel/cw_performance.py:244-268` | `is_run_dead` 死局检测三门：`gs.hp.value < DEAD_HP(20)` ∧ trend 高 ∧ 下回合锁不住血节点；:258-262 注释自申报「待办层（生产调用面空）」 | 待裁决 R-5 | 依赖 C-8 trend；DEAD_HP/TREND_THRESHOLD/LOCK_NODES 常量(:246-248)随删 |
| A-9 | `kernel/cw_economy.py:1074-1088` + `:1275` | `is_emergency` = 「应急触发（绝对 HP 档）hp ≤ registry.emergency_hp(25)」；`refresh_ev_budget` :1275 应急帧返回 0 刷新预算。**链路末环消费面修正（交叉复核，证据链 = .debug/temp/2026-10-28_P2金滞留支出链追查.md §7）**：归零链前两环真实（hp≤25 → :1275 归零），但末环消费端归因有误——`obligation`/`channel_capacity`（economy_cycle.py:201-207/:187）在 mandate_v1 的**唯一现役消费者 = `disclose_budget`**（economy_cycle.py:295，写 `v3_release_budget` 遥测披露字段；docstring :243-255 明文「不入决策输入，披露面字段禁决策消费」，schema.py:486-504 同口径）；`get_node_goal` 标量分支（budget.py:106 调用走部分传参先验 fallback）mandate_v1 现役不进；旧执行层预算门 `authorize_release_refresh` 已停用零调用。**行为直证**：实证局 g_20261028_011013 r4 帧 hp=1 付费刷新真实发射（dseq103，journal v764→v769 金 139→137 含回执）——归零链若在发射位生效该回执不可能存在 | **已落定（原待裁决 R-2 撤销）**：删 = 仅改遥测义务账/v2 投影语义，**mandate_v1 刷新发射零行为差**；非 A1 修复前置。「hp=1 却仍刷新」不是闸失效，是闸不在这条链上。若裁决目标含 v2 栈或披露账读数语义则属另一改面（见 R-2） | 下游 = 披露字段 v3_release_budget（mandate_state.py:195，遥测透传 sess_release_budget）；P28 命题是其数学基座（见 §2.4 proofs） |
| A-10 | `strategies/impl/mandate_v1/criteria/levelup.py:385-392`（门⑥）+ `kernel/cw_economy.py:792-882` | 门⑥血闸：`blood_xp_gate_for` 不过 → `levelup_blood_gate_defer`；`blood_xp_gate` = 「血余额 ≥ 下一级血成本(⌈need/4⌉×6) 才买经验」（血本位局的支付能力检查，:824-827 自辩「非质量信号、支付能力检查」） | **待裁决 R-1**（[40]② 用户 2026-08-31 逐项确认过 vs 本裁定字面覆盖） | blood_xp_mode 解析在 kernel/cw_investments.py:1216-1245；消费位另 = entry.py:844-846（血本位凑金步跳过）+ prep_actions.record_hp_pay_event |
| A-11 | `kernel/cw_intention.py:1067-1094` | `p2_supply_horizon` = 「P2 有效供给视界 H = min(位面剩余节点, ⌈hp / vd_p2_loss⌉)」——血预算轮数进 G 门 | **待裁决 R-3** | 下游 = line_completion_feasibility(:1099-1150，G = ∏(1−(1−q)^H)) → arm_a_live_direction(:1446-1452)/arm_a_corner_names(:1483-1485)/no_target_arms(:1508)/hoard_target_set(:1530) → shop.py:373（乙分支枢纽资格集）——P2 阵容方向锁定与囤货判据整链读 hp；P86 证明批已证甲分支「原门逐字」，删 hp 视界须命题重锚 |

**A 类补充说明**：
- 流层（operations/、obs/）核查结论：**无**「flow 层把 hp 喂给策略决策」的现役路径——观察层只把 hp 写容器（obs/cw_observation.py:2737-2756 observe/write_prior/carry 三态写端），策略消费全部经 A 组判据点名；cw_screen_prep.py:769-770/cw_screen_shop.py 的注释均确认 hp 消费统一走 decision_hp 读口（政策层，B-6）。operations/cw_prep_level_up_action.py:10 注释提及血闸逐帧重闸已随整批化停用（as-built 现状 = 发出点一次授权）。
- `strategies/impl/mandate_v1/entry.py:574-586` 形态⑥观测分键 `terminal_targetless_idle`（金滞留入败局暴露）触发条件含 `p1_blood_floor ∨ p2_blood_floor`——**纯观测零行为**，归 C-11，但注意它是 hp 参与观测分键触发的唯一位；修 A1 重设计金滞留出口时它可能升级为消费点。
- `strategies/impl/cw_strategy.py:445-446`：旧 `gated_hp`（结算 HP 新鲜度门）已删除，现役消费点 = decision_hp——确认无残留门。

### 2.2 B 类·hp 判据的支撑件

为 hp 线存在的推导/查表/注册表。每条标「随主判据删则孤儿化」的依赖注记。

| # | 锚 | 引述/语义 | 删改建议 | 依赖注记 |
|---|---|---|---|---|
| B-1 | `kernel/cw_discipline_rules.py:131-151` | `p2_levelup_stop_hp`（=ceil(d×vd_p2_loss)≈21 血）/`p1_levelup_stop_hp`（≈11 血）停升级线阈值推导 | 删（随 A-3/A-4） | 消费位 = A-3/A-6；伤害锚来源 = registry vd_p1/vd_p2（B-4） |
| B-2 | `kernel/cw_registry.py:164-209` + `:271` | 血预算停手族注册表参数：emergency_hp=25(:168)/blood_budget_stop_enabled(:175)/blood_budget_stop_d(:179)/p1_levelup_stop_rung(:184)/p1_exit_blood_target=60(:192)/blood_budget_refresh_stop_enabled(:204)/form_floor(:271) | 改：emergency_hp/stop_enabled/stop_d/rung 随 A 组删；:192/:204/:271 **已零消费孤儿，可直接删** | :192 p1_exit_blood_target（P1 末窗出口血目标线）消费代码已删（仅 cw_discipline_rules.py:228 注释自引）；:204 blood_budget_refresh_stop_enabled 的闸函数 blood_budget_refresh_blocked 已删 |
| B-3 | `kernel/cw_registry.py:858` + `:934-942` | arbiter 执行约束名序含 `'blood_budget_stop'`(:858) 与 slot 覆盖表 `('slot','boss'):('blood_budget_stop','boss_levelup_ban')` 等三行 | 删 | **arbiter/filters 代码已随 decision_v2 栈删除**（全仓无 arbiter 实现），登记残留；同表 :928-930 gold_floor 行同族孤儿（非 hp 但同批可核） |
| B-4 | `kernel/cw_registry.py:308-352` | 伤害锚：vd_p1_loss_intercept/vd_p1_loss_slope_rung（P1 条件败局伤害拟合）/vd_p2_loss=20.05（P2 条件败局伤害，P12 收益侧口径） | **保留大部分**——伤害锚是游戏机制标定（掉血先验），还喂 cw_first_passage 掉血分布/cw_plane_table/λ 概率侧；仅「作停升级线分母」的用途随 A 组消失 | 删 A 组后不孤儿化（用途收敛为概率侧）；口径差待办（04_survival_budget §6-1 L_c 口径核对）是否随裁撤销待裁决 R-8 附带 |
| B-5 | `kernel/cw_registry.py:603-651` | handoff 承接门 hp 维 boss 投影参数：handoff_ev_gap_bonus/handoff_boss_e_damage 表/handoff_boss_e_damage_default/handoff_boss_reward_bonus | 删 | 消费代码 `handoff_gate_gap` 已删（全仓仅注释引用），孤儿常量 |
| B-6 | `kernel/cw_registry.py:695-719` | k(hp) 血量边际价值族：k_alert=3.0/k_linear=1.0/k_hp_calibration_grid/blood_margin_low_hp=40/boss_tax_p75_by_plane | 删 | 零消费（FLIP 末窗投影分支已删，仅注释互引） |
| B-7 | `kernel/cw_hp_policy.py:35-64`（全文件）+ `cw_discipline_rules.py:44-56` | 决策 hp 政策层读口：decision_hp（gs.hp 直读统一口）+ hp_decision_trusted_of/hp_decision_trusted（可信位 = source∈{observation,carried}） | 改：决策读口 decision_hp 随 A 组删则孤儿化（可删）；**可信位保留**——观测面（obs/reconcile/sim obs_gen）与遥测仍消费 | 消费同门申报纪律（模块头 :15-22）随决策面消失而失效；obs/cw_observation.py:2401-2404、kernel/cw_reconcile.py、sim/cw_sim_obs_gen.py:188、strategies/impl/cw_strategy.py:446 引用 |
| B-8 | `kernel/cw_economy.py:135-141` + `:213-252` | 保血阈值表 HP_SAFE_THRESHOLD=40/DIFFICULTY_HP_TABLE(A1-A8: 40-55) + effective_hp_threshold（职级表 × plane_hp_ratio 位面乘子派生） | 删 | 唯一消费 = maybe_pivot（A-7 挂空）；plane_hp_ratio 依赖 B-9 |
| B-9 | `kernel/cw_first_passage.py` 全模块（:85-192） | 首达生存模型：first_passage_win（掉血分布卷积 P(Σloss<hp)）/hp_floor（保血阈值反解）/plane_hp_ratio/p_win_lambda/risk_posture（盈余/临界/必死边缘三区律） | 待裁决 R-6 附带：整链现役消费 = effective_hp_threshold→maybe_pivot（挂空）；模型本体是「18 号首达生存模型」标定工件，risk_posture 三区律注释自称「非手写 hp 阈值」 | 若 A-7 删，则全模块孤儿化（除测试） |
| B-10 | `kernel/cw_economy.py:676-680` | HP_QUALITY_ALARM=40（运营质量报警线，自注「诊断用，非 spending 触发器」）/HP_DISTRESS_FRAC=0.5（攒利息门 hp 急救分位，注释提到「急救通道 _phase_weights」——该通道代码已不存在） | 删 | 零消费孤儿（仅 04_survival_budget.md:66 文档引用）；:670-674 用户定调注释「血低是报警非触发/死亡螺旋」是宝贵判读史，删常量时注释去向归 git |
| B-11 | `strategies/impl/mandate_v1/statefn/predicates.py:125-185` | `p1_blood_floor`/`p2_blood_floor` 濒死带谓词（hp≤HP_BAND_NEAR_DEATH=15 ∧ 位面域 ∧ 可信）；docstring 自述「决策面消费（血线硬地板解锁包三件）已随血线地板删除链停用，现行消费面 = 纯观测」 | 改（待裁决 R-7）：保留为观测读口 or 随观测分键一起裁 | 现役消费 = entry.py:583-584（C-11 观测分键）；阈值常量单一源 = lambda_death.HP_BAND_NEAR_DEATH（B-12） |
| B-12 | `strategies/impl/mandate_v1/statefn/lambda_death.py:34-39` + `:108-146` | 血带结构锚 HP_BAND_NEAR_DEATH=15/HP_BAND_MID=40 + hp_band 血带映射 + make_key 四维键构造（λ 表键维：难度带×血带×位面×节点） | 保留（λ 表本体 = P51 标定工件，启动必载；裁定二/R27-3 已裁「hp 入概率路由键合法——概率侧非价值侧」） | 现役决策消费 = 无（原 λ 顾问/exposure/floor_eff 消费族已删，模块头 :12-18 申报）；消费位 = predicates 观测件（B-11） |
| B-13 | `strategies/impl/mandate_v1/criteria/refresh.py:160-165` + `mandate.py:1078-1079` | crisis_refresh_invariant(gold, hp_critical)「P36-a 危机不变式」——executor 结构位声明 + 纯数交叉核对函数（本函数不驱动行为） | 改：现役刷新门（r1_commitment_account/r2_budget）无危机特批支，本函数零行为消费；修 A1 若按 14_p1_consume_arms §5.2(b)3 立「危机特批刷新支」才需要 | 契约登记 criteria/contracts.py:273-275 + criteria/__init__.py:76-77 + 23_shop_screen.md:10 |
| B-14 | `strategies/impl/mandate_v1/mandate_state.py:123-124` | v3_blood_budget_rejects（A-3 拒付计数载体）/v3_blood_budget_refresh_rejects（**零写端孤儿**） | 删（随 A-3）；:124 可直接删 | 遥测透传链 = telemetry/schema.py:460-465（D 组）+ cw_decision_trace.py:129-130 |
| B-15 | `strategies/impl/mandate_v1/mandate_state.py:174` | v3_handoff_hp_proj 孤儿字段（handoff hp 投影，无写端无读端） | 删 | flow/session.md:119 仍列为迁出字段（文档同步 D 组） |
| B-16 | `kernel/cw_economy.py:953-1000`（get_node_goal hp/gold/level 形参支）+ `kernel/cw_game_state.py:4707-4746`（scalar_projection_state hp 入参构造投影容器） | 标量投影支：全参传 hp 时构造最小容器走 refresh_ev_budget（内含 is_emergency hp 闸）——注释自申报「迁移漏点排查」诊断路径 | 改：随 A-9 裁定处置；若 is_emergency 删则投影支自然无 hp 语义 | 生产恒走容器支（:972-976 部分传参走先验 fallback 并记 [cw-seam] debug） |
| B-17 | `kernel/cw_vocab.py:64-69` | DIFFICULTY_HP_TABLE/HP_SAFE_THRESHOLD/effective_hp_threshold re-export | 删（随 B-8） | 词表 re-export 孤儿 |
| B-18 | `strategies/impl/mandate_v1/audit/provisional.py:64` | 拟槽登记 P_HIT_Q_CONV「#12 p_hit/q_conv(P36-b/c 危机预算阶梯)」 | 删或随 P36-b/c 退役批一并（登记项，非行为） | audit 登记面 |
| B-19 | `kernel/cw_investments.py:111-190` + `:1216-1245` | EconomyEffect hp 字段族（xp_buy_hp_cost/hp_gold_swap/gold_per_20hp_lost 等——**卡效果登记，非读 hp**）+ is_blood_economy/blood_xp_mode（血本位判别与模式解析） | 保留（效果登记面）；blood_xp_mode 的去留随 R-1 裁定联动 | 消费 = 门⑥(A-10)/invest_strategy 血本位三态（策略立场，非血线判据，不在清查删改区） |

### 2.3 C 类·观测/遥测面（建议保留，单独列）

hp 作为事后读数。hp 是结果不是输入，事后看结果不违反裁定；「反向驱动决策」风险逐条标注。

| # | 锚 | 语义 | 备注 |
|---|---|---|---|
| C-1 | `obs/cw_observation.py:230-261` | read_hp_opt 备战屏血量读取（原生/放大双通道仲裁采放大值，防美术字丢十位误判濒死） | 保留（观测读取面）；仲裁设计正本 = 15_observation_multisource_arbitration.md |
| C-2 | `obs/cw_observation.py:2227-2249`（PHASE_FIELD_SPEC hp 段调度）+ `:2383-2404`（reconcile 接线与可信位）+ `:2737-2756`（observe/write_prior/carry 三态写端） | hp 观察漏斗：shop 关态才 OCR、读不到走对账、真值/prior/携带三态写容器 | 保留；hp_readable/hp_trusted 位消费 hp_decision_trusted_of（B-7 保留半） |
| C-3 | `obs/cw_settlement_obs.py:124-131`（parse_settlement_hp）+ `:683-761`（read_round_outcome：hp_after/hp_confidence/掉血 tooltip 三分量） | 结算屏 hp 真值读取 + P15 掉血公式数据源 | 保留（00_framework §3 授权件之一「P15 掉血公式」） |
| C-4 | `kernel/cw_screen_report/shop.py:33-41` | 店帧观察回灌镜像（hp = 对账层决策值 + hp_readable/hp_trusted 位） | 保留 |
| C-5 | `kernel/cw_game_state.py:1809-1857`（apply_settlement_cover）+ `:2511`（hp Field 写入闸声明）+ `:2273`（开局种子 OPENING_HP_BASE） | hp 结算覆盖写端（唯一真值入口）+ 容器字段 | 保留（状态面，非决策面） |
| C-6 | `kernel/cw_game_state.py:2954`（hp_floor_triggered 事件位，自注「纯观察登记，无判据载体」）+ `sim/cw_sim_battle.py:87-122`（apply_hp_outcome：败局扣血 + 首次 0hp 保底剩 1）+ `sim/cw_sim_opening.py:63-143`（开局 HP 查表）+ `sim/cw_sim_obs_gen.py:173-188`（hp/hp_trusted=True 喂观察面） | sim 世界模型的 hp 机制（0hp 保底 = 游戏全局机制，非策略判据） | 保留；hp_floor_triggered 语义正本 = game_state/fields.md §3.5.3 |
| C-7 | telemetry 全家：`schema.py:379-380`（决策帧 hp/hp_readable 字段）、`:594-596`（outcomes hp_after/hp_confidence）、`:682`（final_hp）、`:688`（death_window）、`:735-740`（hp_pay 血购回执载荷）、`match_archive.py` hp 真值链 v9（:128-145/:616-658/:877-926）、`query.py:40-52`（_outcome_hp_trusted 可信门）、`journal_query.py:303-305`（view_hp）、`cw_match_recorder.py:92-107`、`state.py:200-228` | 全部为事后读数与复盘指标（hp 链/掉血条目/终局 hp/血购回执） | 保留；⚠️ 两处标注：①schema.py:488-489 义务来源枚举含 `'crisis'`（危机金出口分支）——**代码内已无写端**（全仓无 'crisis' 落值），枚举过期，修 A1 时若危机出口重立则复活、否则清枚举；②schema.py:119-120「真濒死帧上 F7 越过 D_ε 门的动作发射分键」——该分键按 hp 状态给决策发射计数，属「读数反过来给决策下结论」的判读面，判读时按裁定口径处理 |
| C-8 | `kernel/cw_performance.py:106-193` | PerformanceTracker 掉血 trend/recent_hp_loss_trend/is_losing_streak/perf_for_comp（观测反馈层：「掉血 trend → maybe_pivot 信号」） | 保留本体（观测层）；**标注反向驱动**：现役唯一消费 = maybe_pivot（A-7 挂空）——若 A-7 删则本组降为纯记录（performance.record 由结算链喂入，cw_screen_battle_wait.py:128）；若 A-7 保留待办姿态则维持标注 |
| C-9 | `kernel/cw_env_grants.py:802-842` + `:889-923`（完胜判定：相邻两结算帧 hp_after 持平）+ `kernel/cw_encounter_selection.py:99-105/:145-146/:243`（hp_after 透传基准） | 完胜/环境锁判定 = 「本节点未损血」——判定**已发生事件**的结果读数判据（同 killed 语义位） | 保留；判定对象是过去一场战斗，不是未来决策输入（env_grants.py:806-810 偏差面申报同读） |
| C-10 | `kernel/cw_battle_calib.py:389-396`（hp_events 计数）+ `sim/power_model/corpus_extract.py:321-327`（is_censored_hp 删失判定：hp_after∈{0,1}） | sim/标定的 hp 校准边界（掉血分布标定、删失口径） | 保留（sim 校准面） |
| C-11 | `strategies/impl/mandate_v1/entry.py:574-586` | 形态⑥观测分键 terminal_targetless_idle（target 空窗 ∧ 濒死带 ∧ 域外 ∧ 持金 ∧ 零消费——金滞留入败局形态暴露，纯观测零行为） | 保留但标注：触发谓词含血带谓词（B-11），是 hp 参与观测分键触发的唯一位；修 A1 重设计支出出口时注意勿静默升级为决策消费 |
| C-12 | `kernel/cw_reconcile.py:447-497` | reconcile_hp hp 对账统一入口（真值直传/开局先验/None 诚实未知；旧三层沿用锚已停用） | 保留（观测对账层）；开局分支消费 cw_opening_hp（待裁决 R-4） |
| C-13 | `kernel/cw_decision_trace.py:143-155` | 停用面字段清单：'hp'/'hp_readable' 注释「统一 state 可算，不入新文件行」 | 保留（决策迹文件已按裁定不含 hp 直存，钉行现值可查） |

### 2.4 D 类·文档面（develop 侧）

> 每条 = 篇名 + 节锚 + 一句话语义；「正本区」= strategy-docs/、proofs/、flow/、game_state/、sim/ 各正本；「changes/ 迭代件」会不定期删减，只做盘点索引。修裁定时改这些章。

**strategy-docs/（正本区）**：

| # | 篇·节 | 一句话语义 |
|---|---|---|
| D-1 | `00_framework.md` §3（:34-44）+ §4 | hp/战力使用边界硬闸门：仅两件被授权消费 hp（λ 表血带维、P15 掉血公式），其余须用户逐项确认；§4 危机响应架构裁决（血线硬地板 ≤15 登记待办、发展为主）——**裁定的上位正典，修裁定时本节须重写授权面** |
| D-2 | `04_survival_budget.md` 全篇（§2 血预算算术 :16-57 / §3 段末窗保血语义 60 线 :60-76 / §4 段内血危机止损 :78-82 / §6 口径核对 :92-96 / §7 hp 进决策授权对账表 :98-114 / §8 验收 :120-128） | 血预算唯一权威模型 + **hp 消费对账表单一源**（表 #3 血线硬地板/#4 血预算止损族=「候选缺口待确认」/#5 [40]② 血闸/#6 gated_hp（已删，过期行）/#7 谷底回滚（已删，过期行）/#8 掉血三档（已删，过期行））——**修裁定的主战场：表 #4 即本次要删的 A-2/A-3 族，§7 表整体须重造** |
| D-3 | `10_prep_decisions.md` §4（:193-199）+ :179 + :221 | 决策面只有经济与阵容、HP 只进遥测/复盘 + 合法 hp 消费五件清单（λ 表/P15/血线硬地板/P21 域/[40]②）+ 血预算指针收敛行——五件清单随裁定收敛 |
| D-4 | `01_math_framework.md` 公理3（:27「血不入任何账与自变量」）+ §8（:34-35）+ §3.3 升级行（:71 拦截层处置：保留 P21 血预算线）+ :88（P36-a 支配性例外）+ :119（危机火力行）+ :140（λ_death 行）+ :191（P72 收尾支：P72(2)=P21 在产）+ :199 | 纯金流公理 + 拦截层收窄后的 P21 保留声明——:71/:191 的「保留 P21」表述随 A 组删须改 |
| D-5 | `02_mandate_layer.md` M3 行（:43「P21 危机带全域拦 + 血本位血闸」）+ :51/:58（「HP 不在硬约束里」+ hp 仅作路由键边界）+ :78（升级支出拦截现行态：保留 P21）+ :96/:99（命题 A 验收：位面 1 结束 hp≤40 的局 ≤18/40、进 P2 时 hp>40 ≥22/40 等 hp 指标） | M3 门语义 + hp 边界声明 + **sim/实机验收判据引用 hp 指标（标注：判据引用 hp 指标下结论，修 A1 时验收线须换尺）** |
| D-6 | `11_shop_decisions.md` §2（:55 资格门全链含 P21 危机带全域判定与血闸/:58 血本位局/:59 拦截层处置表「保留 P21 血预算线」）+ :81-84（写入代码位 + 血本位安全带 [40]②）+ :103（「血线维度不适用于本判据」）+ :106/:110（P36-a 危机不变式先于存在性门）+ :178（空板止损守卫「与血线禁令同构」）+ :186（升级触发统一批新基线：85/85 被 P21 危机带拦的批读数 + 「sim hp 校准失真，hp 类只作报警线」注） | 升级判据权威篇——:55/:59 随 A 组删改；:84 血闸随 R-1；:186 的批读数佐证了危机带全域封死形态（与 A1 病灶同源） |
| D-7 | `14_p1_consume_arms.md` §5.2(a)（:130-157 p1_crisis_band 判据权威定义 Z1 降格登记待办 +(b)2/(b)3 消费位暂不实现）+ §5.4（:180-185 深血线死握三例 + F1 血线→支出反馈边）+ :205（守卫先于特批刷新）+ §7 写入代码位表（:222-224）+ §8（:270 锚重锚/:279-281 勘误登记）+ §9.7（:396 hp 登记待办）+ §10（:434-440 帧序与血线停付）+ §11 评审记录（:472-531）+ :554 | P1 消费通道篇：p1_crisis_band 全套（Z1 未写入代码）+ **F1「血线→支出反馈边结构性缺位」诊断**（与 A1 同病灶族的历史登记）——修 A1 时本篇 §5 为必读前案 |
| D-8 | `17_stall_form_spend_authority.md` §1 定位声明（:5-7「触发谓词零 hp 消费；救援面维持登记待办不复活」）+ §2.3（:90-91 分支③(b)2/(b)3 危机帧行）+ :126/:151-157/:162-163 | 停滞成型支出授权篇的 hp 红线声明与 (b)2/(b)3 挂空行——随 Z1 族的最终处置联动 |
| D-9 | `19_reinforce_channel_and_survival_discount.md` :4（判据出处含 hp 红线）+ :23（hp 红线三条）+ :32（危机帧禁接行）+ :43/:68-76/:84/:94-96/:112-117 | 补强通道篇的 hp 禁令与 λ 概率侧边界声明 |
| D-10 | `20_large_balance_must_spend.md` 卷首 v2.3 变更注（:3「停止付血线域内让位随出口三层删除消亡」）+ :101/:143（停止付血线让位裁决引用/出范围声明） | 富余段必花篇——血线让位已消亡的收尾声明，as-built 一致 |
| D-11 | `21_opening_window_and_tool_consume.md` :101/:143/:162 | 开局窗篇：停止付血线与装备域不相交声明 + sim 禁用 hp/胜率/出口金作工具件验证判据 |
| D-12 | `22_prep_screen.md` :5（判据指针）+ :32（第 4 步升级检查「血预算线/资金线门类拒发同落零动作」） | 备战屏篇 M3 调用时机——血预算线拒发语义随 A-4 删改 |
| D-13 | `23_shop_screen.md` :10（刷新放行链「危机帧不变式 P36-a 先于存在性门」） | 商店屏篇刷新序——P36-a 结构位随 B-13 裁定联动 |
| D-14 | `26_battle_settlement.md` :5（hp 消费唯一登记处指针）+ :11-12（连败/血线响应全部折算进备战/商店判据 + 血预算停止追等级线指针）+ :22 | 结算篇的血线响应收敛声明 |
| D-15 | `15_observation_multisource_arbitration.md` :16（行2 hp 四通道仲裁）+ :43/:59/:64/:74/:136/:143/:152/:180-183 | 观测仲裁篇（hp 双通道标定/对账层/trusted 位）——**观测面正本，保留**；:183 streak 双源与保血方向关联注随裁标注 |
| D-16 | `strategy-docs/README.md` :51（29 篇行）+ :79（「危险信号（血线硬地板、λ 顾问）只允许把反应提前」） | 分篇入口与姿态总纲行——:79 随裁定重写 |
| D-17 | `08_events.md`/`13_pick_family.md`/`16_evaluation_tables_reassessment.md`/`29_invest_strategy_screen.md` 血本位三态/血本位族评分排除行（08:31/:44-48、13:20/:39、16:82） | 血本位（卡效果币种切换）的策略立场三态——**与「读 hp」不同族**（判据 = 卡效果字段非当前血量），保留；仅在 R-1 撤血闸时联动核对其发射面 |

**proofs/（正本区）**：

| # | 篇 | 一句话语义 |
|---|---|---|
| D-18 | `math_proofs.md` 索引行 P21(:45)/P36(:60)/P51(:72)/P52(:74)/P66(:87)/P72(:93)/P85(:105)/P86(:106) | P21 濒死升级 EV 负（血预算停升级的数学基座）/P36 危机火力阶梯/P51 λ 血带维/P72 升级预算闸（(2)=P21 在产）/P85 血闸让位序/P86 血预算 H 主导 P2 空候选 |
| D-19 | `proofs/p21-p2-deathbed-levelup-ev.md` 全篇 | P21 判据（存活到账 h>d·L_c ∧ 受益覆盖）= A-3 血预算停升级门的数学正本——判据删除后本篇降级为历史命题（结论「血量驱动的保血升级无经济性依据」仍成立，但「因此拦」的授权面随裁定消失） |
| D-20 | `proofs/p28-emergency-band-hoard-ev.md` + `validations/P28_VALIDATION.md`（:10/:67 引 spend_gate D2 血线臂——**spend_gate 代码已删，过期引用**） | 应急带（hp≤25）非转化支出期权折扣 = A-9 is_emergency 闸的数学基座 |
| D-21 | `proofs/p36-crisis-firepower-floor.md`（P36-a 不变式 + P36-b/c 预算阶梯缺件）+ `validations/P36A_VALIDATION.md` :78 | 危机带火力地板/刷新不变式 = B-13 的命题面 |
| D-22 | `proofs/p71-levelup-channel-budget-gate.md`（:78 血预算停付在 hp=46 帧不触发→闸缺失定位/:100 seg_p2_blood_budget_levelup 检查项）+ `proofs/p72-full-band-budget-gate.md`（:4/:11 病灶帧 HP=45>危机带线 41 三闸不触发 + §2.5 血面合取行 :116-122/:141/:152 帧 E 危机带内停付）+ `proofs/p85-preemptive-levelup-hard-node.md`（:15 术语血闸/:119 血面让位序不旁路/:180 拒因行/:203 死亡带误触发） | 升级预算闸三篇——血面合取支随 A 组删改 |
| D-23 | `proofs/p86-no-target-period-fund-allocation.md`（:62/:66/:185/:202 血预算 H = ⌈hp/伤害⌉ 主导 P2 空候选）+ `p86-proof-batch.md`（:102/:300） | P86 甲分支 G 门逐字继承血预算视界 = A-11 的命题正本（R-3 裁定的重锚对象） |
| D-24 | `proofs/p09-hp1-dead-anchor.md`（0hp 保底 1hp 机制锚）/`p17-ab-hp-measure-legality.md`（出口 hp 作 A/B 度量的合法性边界）/`p15`+`p15v2`+`p12v2`（条件败局伤害标定，λ 概率侧输入）/`p51-waiting-cost-lemma.md`（纯金流公理+λ 血带维）/`p24`（:61-63 不解除血预算停手门——随 A 组删过期）/`p29`（:36 删 hp≥40 代理门——已合规历史）/`p35`（:132 P21 适用范围对照）/`p37`（三段 hp 轴分界叙述）/`p46`（:43 无血线分支）+ `validations/P46_VALIDATION.md`（濒死带 O=0 与 P51 联动缺口）/`出口生存余量设计批-命题与因果链.md`（:43/:49/:62 R5 危机带帧行为失稳门覆盖缺口） | 机制锚与概率侧命题保留；含「血预算停手门」引用的行（p24）随删过期；出口生存余量批的 R5 行 = A1 同族缺口的历史登记 |
| D-25 | `proofs/validations/P36A_VALIDATION.md`/`P37_VALIDATION.md`/`P51_V3_REBUILD.md` 等验证档中的血带/危机引用 | 验证档随其母命题处置 |

**flow/、game_state/、sim/（正本区）**：

| # | 篇·节 | 一句话语义 |
|---|---|---|
| D-26 | `flow/session.md` :41-43（last_hp/last_hp_real/hp_suspect 表行）+ :76 + :119 + :147 + :249/:263 | §2.1 清册表 hp 三行**已过期**（字段随终态契约 §A 从 StrategySession 删除，cw_strategy_session.py:111-115 注释正本）；:147「掉血三个分支哑火」段引用的 BloodAlarmTracker 已删（flow/README.md:106 已声明）——清册时点账 vs as-built 的漂移，修批顺带收敛 |
| D-27 | `flow/README.md` :106-124 | 结算链删除声明 + 决策 hp 读口统一（decision_hp/可信位）——as-built 现行，随 B-7 裁定联动 |
| D-28 | `flow/action_ops.md` :105 | LevelUp op「零授权零计数（击数推导/血闸全上移发出点）」——as-built，随 R-1 联动 |
| D-29 | `game_state/fields.md` §3.5.3（:1180-1185 hp_floor_triggered）+ hp 写入闸（§3.2.13，:2511 代码锚）+ :2328 + `game_state/README.md` :127 + `game_state/冻结残余清单.md` :18/:32/:42（λ̂_U 濒死带量级旧表坐标勘误） | 容器字段面正本，保留；冻结残余清单的 λ̂_U 注属观测度量面 |
| D-30 | `sim/sim-design.md` §8.2（:240-241 扣血采样/0hp 保底）+ :50/:64/:112/:118/:265 + `sim/sim-wiring.md` :28/:38 + `sim/sim-power-model.md` :97/:147-149/:219 | sim 世界模型 hp 机制与「功率模型永不入 HP 特征」铁律——保留；:219 check_formation_hp_coupling_sentinel 为 sim 校准锚 |

**changes/ 迭代件（盘点索引，正本禁引其内容；会不定期删减）**：
- `changes/2026-10-18-levelup-band-gate/`（design/attack/landing）——升级带闸（= A-4/A-5 门④ 的落地迭代），修 A1 时该迭代件的语义由正本 11_shop_decisions.md 承接。
- `changes/2026-10-12-prep-shop-workflow-redesign/`（design/landing/details/line_and_upgrade.md/details/prep_pipeline.md）——血线地板解锁包删除链与 P21 保留的迭代记录（sell.py:115-118 与 predicates.py:129-131 注释引用的「line_and_upgrade §2.3」即此件）。
- `changes/2026-10-17-levelup-shop-transition/`（design/attack）——升级商店转场迭代，门④消费位相关。
- 其余命中（2026-09-06-c1-direct-core-entry、2026-09-15-sim-redesign、2026-09-21-gs-opening-seed）为少量 hp 字样（开局种子/词缀腿），非血线判据语义。

### 2.5 D 类·文档面（game 侧）

> 分两列：**机制事实（保留）** vs **基于血量的打法判据/启发式（过期候选）**。

**机制事实（保留，勿误伤）**：

| # | 锚 | 语义 |
|---|---|---|
| DG-1 | `data/gameplay.md` :13 + :93 | 生命值规则原文：未在行动值内取胜扣血、首次归零保底 1HP、开局值随职级/难度/词缀变 |
| DG-2 | `research/combat.md` §3（:24-31 血量→星 70→+3星/40→+2星）+ :38-50（掉血结构：败局一次性扣血非慢流血/遭遇惩罚制）+ :74-76（难度→怪物血量 ×1.052） | 战斗机制事实 |
| DG-3 | `research/economy.md` §10.2（:142-147：HP 跨位面继承/开局 HP 初值实证 A8+108=82/「开局不利」−20/掉血结构/失败扣血公式） | 对局机制事实（cw_opening_hp 的知识源，保留） |
| DG-4 | `research/invest_effects.md` :27（鲜血神殿/5F 令咒任务机制「血<88 不能接」为任务后果事实）/:49-50（血金互兑卡）/:76（奋斗协议购经验花血） | 卡效果机制（B-19 的知识源，保留） |
| DG-5 | `data/competitors.md`（永久创伤/燃血克星等词缀机制）+ `data/bosses.md`（共享血量等 boss 机制） | 词缀/boss 机制事实 |
| DG-6 | `research/final_comps/final_wandi_burn.md` 等（燃血=记录-返还引擎、低血高经济运营描述） | 阵容机制知识（描述「游戏里燃血怎么运作」，非 bot 策略判据，保留） |

**打法启发式（过期候选——按裁定「基于血量的打法判据」清理；注意这些是「人怎么玩」的知识档，清理方式=删或标注过期，由修批执行）**：

| # | 锚 | 语义 |
|---|---|---|
| DG-7 | `research/economy.md` §5（:55「位面1 遭遇前战力不足→舍弃利息刷新凑羁绊保血」/:56「血危险锁血急救→花光提质量」/:60 信号「HP 低于阈值」）+ §6（:62-77 保血 vs 保经济决策树：血健康/血<40 止损刷新/A8 保血保连胜>保经济卖血）+ §7（:79-87 阶段共识表「血健康继续吃息/血危险果断花光提质量」+ :87 联动行） | **血危险→花光/血线止损类判据 = 过期候选**（正是裁定点名否定的形态；economy.md 被 10_prep_decisions 等多处引为阶段共识源，清时需扫引用面） |
| DG-8 | `research/plaza_methodology.md` M8（:70「血量换经济边界：血量低就不需要卡利息了，留20块就OK」）+ M9（:73-78「保血是硬约束，连胜是资产」+ :76 A8 高难保血/保连胜>保经济卖血 + :78 装备保血）+ :30（纯过渡定位「只为保血」）+ :84（「成型后掉血→补装备/星级，不换阵容」掉血归因三分法） | 人打法方法论的血量判据——过期候选（M9 整节为血量中心主义；:84 掉血归因属诊断方法论，可剥离保留） |
| DG-9 | `research/transitions.md` :17（纯经济类策略=「NPC」(血换经济，1位面boss门口启动)）+ :53（过渡桥「保底稳血」定位） | 过渡体系知识中的血量措辞——随 DG-7/8 同批标注 |
| DG-10 | `research/README.md` :21（过渡桥定义「保底稳血、攒经济」）+ :68（索引行「经济机制：…保血边界/阶段共识」）+ §策略相关文档节（:82-87） | 索引与定义行的血量措辞——随 DG-7 联动 |
| DG-11 | `research/combo_methodology.md` :284-293（DOT≥2 轮 vs 无 DOT 轮掉血对比核算） | 研究证据面（掉血观测对比，非判据），保留但属「hp 读数下结论」形态——标注即可 |

### 2.6 E 类·测试面

锁 A/B 组行为的测试（修改判据时同步重写；路径前缀 `sr-od-test/test/sr_od/application/currency_war/`）：

| # | 锚 | 锁的行为 | 随判据删改的处置 |
|---|---|---|---|
| E-1 | `strategies/impl/mandate_v1/test_levelup_prob_axis.py:310-317`（test_p21_crisis_band_retained：hp=10 帧断言 level_spend_blocked 为 True「停付照常」）+ :420-443（test_crisis_band_blocks_spend_and_interest_key_domain：危机带管辖 + 键域断言）+ :499-515（test_crisis_band_blocks_even_with_gold_above_line：富金帧仍拦 + levelup_crisis_defer 计数） | **锁危机带停付行为的行为锁**——A-4/A-5 删改的直接测试对象 | 重写：改为断言「危机帧不再拦升级」（负向守卫）或随门删除一并删除 |
| E-2 | `strategies/impl/mandate_v1/test_levelup_prob_axis.py:374-418`（p2_blood_floor/p1_blood_floor 真值表：信任门/位面域/边界含 hp≤15） | 锁濒死带谓词真值表（B-11） | 随 R-7 裁定：保留则留测试；删则删测试 |
| E-3 | `strategies/impl/mandate_v1/test_shop_session_loop.py:658-679`（test_gate_p21_crisis_frame_defers：门④命中计 levelup_crisis_defer；test_gate_blood_gate_frame_defers_and_control：门⑥血闸 defer 计数） | 锁升级资格门④/⑥拒因计数 | 门④测试随 A-5 删；门⑥测试随 R-1 |
| E-4 | `kernel/test_economy.py:321-382`（blood_xp_gate 拒付代表：hp 无真值/可信位 False fail-closed 三态 + blood_xp_gate_for 注入形态） | 锁血闸 fail-closed（B-19/A-10） | 随 R-1 |
| E-5 | `kernel/test_economy.py:876-890`（effective_hp_threshold 职级/位面表值断言） | 锁保血阈值派生（B-8） | 随 B-8 删则删 |
| E-6 | `kernel/test_cw_opening_hp.py` 全文件（词缀域写尾 HP 先验跟随回调：先验不过可信位 fail-closed/真值恢复） | 锁开局血量先验写尾（待裁决 R-4 载体） | 随 R-4 |
| E-7 | `kernel/test_settle.py:551-580`（decision_hp 直读测试 + hp_decision_trusted_of） | 锁政策层读口语义（B-7） | decision_hp 半随 A 组删；可信位半保留 |
| E-8 | `sim/test_sim_opening.py:98-106`（opening_hp_or_raise 实证档 82/62 + 非实证档报错索样本） | 锁 sim 开局 HP 查表边界（C-6/R-4） | 随 R-4（倾向保留——sim 世界模型面） |
| E-9 | `sim/test_sim_rules.py:135-141` + `sim/test_sim_smoke_batch.py:10/:271` + `sim/cw_sim_backend/test_p3_win_terminal.py:188` + `kernel/test_node_advance.py:1236/:1262`（0hp 保底事件位翻真/终局死亡形态） | 锁 sim 0hp 保底机制（游戏机制，非策略判据） | **保留不动** |
| E-10 | `kernel/test_match_archive.py:393/:452`（hp_pay 事件行 mode='blood_buy' 载荷） | 锁血购回执遥测链（C-7） | 随 R-1（若血闸撤，hp_pay 写点 prep_actions.record_hp_pay_event 联动核） |

---

## 3. 待裁决项（两难写清）

| # | 事项 | 两难 |
|---|---|---|
| R-1 | **血本位支付能力闸**（A-10：blood_xp_gate 族 + 升级门⑥ + entry.py:844-846 血本位凑金步） | 一边：[40]② 用户 2026-08-31 曾逐项确认「血余额≥整级血成本才买经验」是**支付能力检查、账户读数非质量信号**（04_survival_budget §7 表 #5「已裁定」）；血本位局里血就是购经验的币种，「买不买得起」与「金不够买不起」同构，不属「hp 低就不做」。另一边：2026-10-28 裁定字面「策略侧不应该考虑 hp」可覆盖它——血余额正是 hp。撤闸后果 = 血本位局零血仍发购买经验（执行层报错/空转）。需用户明确 [40]② 是否被新裁定废除。 |
| R-2 | **应急带刷新闸**（A-9：is_emergency hp≤25 → refresh_ev_budget 归 0） | **已落定（交叉复核，撤销原「修 A1 必须先裁」前置）**：该归零链对 mandate_v1 刷新发射**零行为差**——链路末环唯一现役消费者 = `disclose_budget`（economy_cycle.py:295）写 `v3_release_budget` 遥测披露字段（「禁决策消费」有 docstring 与 schema 双口径防线），`get_node_goal` 标量分支 mandate_v1 现役不进、旧执行层预算门 `authorize_release_refresh` 已停用零调用；实证局 g_20261028_011013 r4 帧 hp=1 付费刷新真实发射（journal 金 139→137 含回执）为行为直证。证据链 = .debug/temp/2026-10-28_P2金滞留支出链追查.md §7。剩余口径：删 is_emergency 归零支 = 仅改遥测义务账（v3_release_budget 读数语义）与 v2 投影语义；若未来裁决目标含 v2 栈复活或披露账读数口径（如 sess_release_budget 判读基线），属另一改面另立项，与 A1 修复互不前置。P28 命题（应急带非转化支出期权折扣）随本条降级为无现役消费面的历史命题。 |
| R-3 | **P2 血预算视界**（A-11：p2_supply_horizon ⌈hp/vd_p2_loss⌉ → line_completion_feasibility G 门 → 阵容方向锁定/囤货链） | 一边：hp 明确是判据输入（血预算轮数决定「等不等得到缺件」），按裁定应删。另一边：P86 证明批已证无目标期三分支判据（甲分支 G 门「原门逐字」继承此视界），删 hp 视界后 H 退化为纯剩余节点数——G 门分辨力变化会改变 P2 线锁定/空窗判据行为，涉及命题重锚与 A/B，不是删一行。且 P86 文档（proofs/p86:62）记载「血预算 H 主导 P2 空候选是常态带」——它正是当前 P2 空窗病灶的数学描述。需用户裁：删（+命题重锚排期）或暂留（标注待重锚）。 |
| R-4 | **开局血量先验**（cw_opening_hp 模块 + reconcile 开局分支 + sim opening） | 一边：它是**对局状态初始化事实**（开局血量本来就不是 100，133 局普查实证），不预判任何决策，机制上等价于「读一次开局面板」；策略判据删除后它只喂容器与遥测。另一边：它的存在让 hp 从开局就有非 None 值，是 A 组判据的取值来源；且「先验不过可信位」的语义（fail-closed）与决策可信位耦合（B-7）。倾向保留（世界事实面），但归属（观测层 or 独立保留）请用户确认。 |
| R-5 | **挂空死码的处置时点**（A-7 maybe_pivot 保命转型 / A-8 is_run_dead 死局检测 / A-6 all_in_xp_domain_hit） | 一边：三者生产调用面为空（注释自申报「待办层，测试仓经桥调用」），按「过期设计删除」应直接删。另一边：注释同时申报「重挂生产消费必经政策层读口」——存在「将来重挂」的意图残留；删码会连带删测试桥（测试经桥调用它们）。修 A1 批次是否顺手清挂空码（而非只修活码），请用户定范围。 |
| R-6 | **首达生存模型**（B-9 cw_first_passage 全模块）与 **λ 表血带维**（B-12 hp_band） | 一边：首达模型现役唯一消费 = 挂空的 maybe_pivot，删则全模块孤儿；λ 表血带维现无决策消费（仅观测分键）。另一边：两者都是**概率侧工件**（λ 表=死亡概率查表，裁定二/R27-3 已裁「hp 入概率路由键合法——概率侧非价值侧」；首达模型=掉血分布卷积的标定产物），且 19/04 号篇多处声明「若未来需要掉血趋势信号，按硬闸门走 λ_death 概率侧新立项」——留着是未来合法通道的地基。删或留请用户裁（倾向：保留为概率侧标定工件，但解除与决策面的全部接线）。 |
| R-7 | **濒死带观测谓词**（B-11 p1/p2_blood_floor）与其消费位（C-11 entry.py 形态⑥观测分键、flow.py 锁生成可行性观察件） | 一边：谓词本体读 hp 判「当前帧是否濒死带」，形态上是「hp 参与分支」。另一边：其唯一消费是**纯观测分键**（金滞留入败局形态暴露、boss 濒死死区分键），零行为——按「事后看结果不违反裁定」可留。风险：修 A1 重设计支出出口时该分键可能升级为消费点（届时即成 A 类）。留（标注）或删请用户裁。 |
| R-8 | **game 侧打法启发式的清理深度**（DG-7/8/9/10：economy.md §5-§7、plaza_methodology.md M8-M9、transitions.md、research/README.md 索引行） | 一边：裁定说「基于血量的打法判据/启发式 = 过期候选」。另一边：这些文档的定位是「人怎么玩」的知识档（攻略提炼/社区共识），描述的是人类玩家的打法而非 bot 策略判据；bot 现役代码并不消费 economy.md §6（消费历史见 cw_economy.py:666-674 注释——已按「报警非触发」定调弃用）。全部删 vs 加「历史打法，bot 不采用」标注，请用户裁。 |
| R-9 | **hp 字面参与的机制判定读数**（C-9 完胜判定 hp 差分 / C-10 删失判定 / telemetry 濒死分键 C-7②） | 严格字面下「分支判据读 hp」包括这些——但它们判定的是**已发生事件**（这场是否完胜/该样本是否删失/该帧发射计数），不是未来决策输入，机制上等价于 killed/progress 真值。按「hp 是结果不是输入，事后看结果不违反裁定」应保留。列出仅为完整性确认，若有异议请指出。 |

---

## 4. 完整性自检

**扫描词清单**（代码与文档同词族）：
`hp`、`血`、`危机`、`crisis`、`blood`、`掉血`、`伤害锚`、`loss`（经 vd_p1_loss/vd_p2_loss/streak_floor_loss_damage/hp_max_loss 族命中）、`濒死`、`急救`、`存活`、`死亡`/`death`、`floor`（hp_floor/recipe_floor/interest_floor/form_floor/war_floor/rebirth_floor/gold_floor/boss_floor——非 hp 的 floor 逐个排除：recipe_floor=配方底线门、interest_floor/gold_floor/war_floor/rebirth_floor=金地板、form_floor=孤儿参数、boss_floor=保底金门 θ_G、directed_refresh_high_cost_floor=刷价门槛，均非血判据）、`保底`。

**扫过的目录**：
- 代码：`src/sr_od/application/currency_war/` 全树（strategies/ 含 criteria/statefn/audit、kernel/ 含 action_report/screen_report、sim/ 含 power_model、obs/ 含 recognizers、operations/ 全树、telemetry/、data/、knowledge/、tools/、根级 10 个 py）——排除 `__pycache__`/`.install`。
- 测试：`sr-od-test/test/sr_od/application/currency_war/` 全树（两轮词扫描 + 专项符号扫描）。
- 文档 develop：`docs/develop/sr_od/application/currency_war/` 下 strategy-docs/（28 篇）、proofs/（单篇 + math_proofs + validations）、flow/、game_state/、sim/、screens/、changes/（List 扫描定位命中文件后按需读）。
- 文档 game：`docs/game/currency_war/` 全树（README/data/research/final_comps）。

**命中为零或近零的词（如实记录）**：
- `急救`：代码零命中（唯一引用 = cw_economy.py:677 注释提到的「急救通道 _phase_weights」——该通道代码已不存在，注释过期）；game 侧命中 = economy.md §5:56（打法启发式，已列 DG-7）。
- `存活`：代码仅出现在注释/命题语义里（cw_discipline_rules.py:227「不是存活保证」、cw_first_passage 生存概率叙述），无存活判据代码。
- `伤害锚`：字面零命中；实际载体 = vd_p1_loss_*/vd_p2_loss/streak_floor_loss_damage/handoff_boss_e_damage（B-4/B-5 已收）。

**已知保留意见（可能没查透的地方）**：
1. `docs/develop/sr_od/application/currency_war/changes/` 只做了**文件级**定位与抽样（12 个命中文件列名，未逐篇通读）——changes/ 是迭代过程区、正本禁引其内容，本次按「盘点索引」处理；若某迭代件含未回写正本的血判据语义，需修批时以正本+代码为准。
2. `screens/`（38 篇画面 doc）未逐篇扫——画面 doc 属识别面，hp 相关仅结算屏/备战屏读数位（已在 C-2/C-3 覆盖），风险低。
3. `knowledge/`、`data/`、`tools/` 三目录词扫描命中极少（仅 data/affix_effects_data.py 词缀原文「紧急止血」等游戏文本、tools 为采集/调参脚本），未逐文件精读——若 tools/cw_weight_search 里有 hp 权重搜索逻辑属离线工具面，不在策略决策面。
4. `strategies/impl/mandate_v1/` 部分 2000+ 行大文件（mandate.py 1921 行/shop.py 2000+ 行/sell_gate.py）按词扫描命中定位精读，未逐行通读——shop.py/sell_gate.py 现役判据链经扫描确认零 hp 读取（仅「血统/血本位」词样命中，为义务血统与卡效果语义，非血线判据）；若存在未命中词形式的 hp 派生量（如经中间变量改名传递），本轮未覆盖。
5. `sr-od-test/` 仓库为独立 git 仓，本次按工作区当前内容扫描，未核其 git 历史。


---

# 快照二：P2 金滞留支出链追查（源 = .debug/temp/2026-10-28_P2金滞留支出链追查.md）

# P2「金滞留不花」决策链定向追查(sim 局 g_20261028_011013)

> 调查日期 2026-10-28;只读调查,不改代码。判读纪律按 sr-od-currency-war-dev/telemetry-reading(行锚=v 号/报告 L 号/dseq/file:line)。
> 用户问题照录:「金从 108 滞留到 142 直至死亡——这个问题不应该跟 hp 挂钩,而是调查:为什么正常的策略路线也不花钱,连刷新也没有吗?」即不接受「hp 低→危机带→什么都不做」的解释框架,追查**买牌(M2 照买照囤/合成完成/线内成员)与刷新(停留刷新/搜索刷新)**两条与 hp 无关的正常支出通道在位面 2 为什么几乎没开火。

## 0. 数据面与金账基准(journal 锚)

金账链(统一账 `state/journal.jsonl` `gold` 写行):进 P2 v611=111 → r1 店后 v643=108 → r2 收入 v661=120 → r2 店后 v712=122 → r3(补给)收入 v730=132 → r4 收入 v744=142 → r4 店内消费至 v848=131 → **死亡 v866=142(match_final 金=142)**。
P2 收入合计 43(12+10+10+11),卖出回收 19,买牌+付费刷新支出 **31**(买 29+刷新 2);净 +31 而终值 142=死亡时点。
等级链(常见误读排除):`level` 写行 v437=5 → **v725=6(xp 0/40)**:6 级是 r2→r3 之间**自然经验**到 20/20 自动升的,0 金支出;全对局**零买经验动作**(cw4 `levelup_trigger_natural=0`,资金线 defer=0)。

全对局买因分布(回执 28 笔 + 决策 log 124 条逐条核对):m2_line_member×2(P1)、m2_merge_completion×1(P1)、scene_plugin_buy 发出 5/回执 4(报告已登记 ±1 观察项)、dead_gold_press_buy×3(全 P1)、**m6_stockpile×17 发出(P1×5 + P2×12)**;付费刷新 1 次(P2r4,2 金)。P2 段 14 笔买入=29 金,其中**线内件 0 笔**。

## 1. 逐帧支出决策表(P2,帧=decide_shop_action 单动作帧)

### 1.1 P2r1(节点 2-1,金 111,等级 5,hp 38,连胜 3)

| dseq | 动作 | 金 | 店况关键件 | 判定链要点 |
|---|---|---|---|---|
| 77 | 开店(shop_gold_read) | 111 | 概率条 1→45%/2→33%/3→20%/4→2%,**无 5 费档**(报告 L2456;= REFRESH_PROB[5],cw_shop_odds.py:52) | 店 5 槽=赛飞儿/缇宝/艾丝妲/黑塔/万敌,**线内件 0** |
| 78 | 卖停云(+1) | 112 | — | shop_swap 腾席 |
| 79 | 买缇宝 2金(m6_stockpile) | 110 | 非线内 2 费 | M6 富余臂(gold>g*=50)命中 |
| 80-83 | 卖爻光(+1)/买赛飞儿 1(合成 2★)/买艾丝妲 1/买黑塔 1 | →108 | 全非线内 | M6 链;bench 9/9 满 |
| 84 | 收店 | 108 | 残牌万敌 1金 | M6 席满置换拒(m6_bench_full)→ **步骤6 刷新判据评估:等级 5<花火 2 费带下界 6 → 拒 `stay_gate_upgrade_first`**(counter=2 之一)→ 收工 |
| 85 | 出战 | 108 | — | hp 38≤41(P2 危机带,cw_discipline_rules.py:212-232) |

**r1 小结**:升级意图=stay_gate 触发(升级到带内 6 级)→ 被危机 defer 拦(资金门其实可过:111-16≥50);刷新判据被「升级优先」分支拒 → **升级/刷新双关**。买面只有 M6(缺件未进店,M2 无候选静默跳过——`missing` 循环对不在店的成员零计数,shop.py:1254-1257)。

### 1.2 P2r2(节点 2-2,金 108→收入 120,等级 5,xp 18/20,hp 38)

| dseq | 动作 | 金 | 店况关键件 | 判定链要点 |
|---|---|---|---|---|
| 86-88 | 投资策略屏:免费刷 2 次+选溜佩佩(cash=9) | — | — | 策略卡通道,不花金 |
| 89 | 开店 | 120 | **三月七 1★(1费,槽1)**、砂金2、银枝2、遐蝶4、飞霄1;概率条同 L5(L2778) | 全场 P2 唯一线内件进店帧 |
| 90 | 卖黑塔(+1) | 121 | — | shop_swap |
| 91 | 买砂金 2(m6) | 119 | 砂金=黄泉线旧件 | M6 |
| 92 | 卖绯英(+2) | 121 | — | shop_swap |
| 93 | 买银枝 2(m6) | 119 | 非线内 | M6 |
| 94 | 卖缇宝(+2) | 121 | — | shop_swap |
| 95 | 买飞霄 1(m6) | 120 | 非线内 | M6 |
| 96 | 卖风堇(+2) | 122 | — | shop_swap |
| 97 | 收店 | 122 | 残牌三月七 1金、遐蝶 4金 | **三月七未买的机制**:①M2 义务面 `missing` 按名集(shop.py:930),三月七已持有 2★ → 不在 missing → 序 1 不评;②M2b 需 bench 同名 1★ 对(无);③m2_stockpile 门 `_cnt(m,1)==1 ∧ _cnt(m,2)==0` 被持有 2★ 关闭(shop.py:1277-1279);④M6 排除线内成员(counter `m6_line_member_excluded=2` 之一)→ **该 1★ 副本四臂全部够不着,结构性不可买**。然后刷新判据:同 dseq84 拒 `stay_gate_upgrade_first`(counter=2 之二)→ 收店 |
| 98 | 出战 | 122 | — | r2 战败 38→1(sim 随机,hp_floor 保底事件,非解锁信号——报告 L2969/写点 cw_game_state.py:2954) |

**r2 小结**:唯一一次缺件进店(三月七),因「义务面名单星级盲 + 囤腿 2★ 关闭」没有可走的买臂;刷新继续被等级带门拒。

### 1.3 P2r3(节点 2-3 补给,金 122→132):无商店;自然经验 20/20 → **等级 6**(v725,0 金)。

### 1.4 P2r4(节点 2-4,金 142→131,等级 6∈花火带[6,7],hp 1)

| dseq | 动作 | 金 | 店况关键件 | 判定链要点 |
|---|---|---|---|---|
| 99 | 开店 | 142 | 概率条 1→30%/2→40%/3→25%/4→5%,仍无 5 费(L3118);板=千冶·刃2/星期日3/卡芙卡2/丹恒·饮月2/乱破1,**线内件 0** | 停留目标=花火(未完成星级目标中费用档最低,levelup.py:206-213);等级 6∈[6,7] → 刷新判据本帧起**放行** |
| 100 | 买千冶·刃 2(scene_plugin) | 140 | 场景插件位 | 序 2 额度 1→0 |
| 101 | 卖银枝(+2) | 142 | — | 置换腾席 |
| 102 | 买星期日 3(m6) | 139 | 非线内 | M6 |
| **103** | **付费刷新 2金(star_target)** | **137** | 刷后=白厄3/刻律德菈3/万敌1/海瑟音4/白厄3,**线内件 0** | 全对局唯一刷新:r2 预算(gold−(g*+ρ2)=139−52≥2)✓,P92 通道②(花火 2费 prob(6,2)=40%,gold≥2)✓,seat_recoverable ✓(忘归人/飞霄/艾丝妲尚可卖)。发射位=六序末(shop.py:1962-2061) |
| 104-109 | 卖飞霄(+1)/买刻律德菈 3(scene_plugin)/卖艾丝妲(+1)/买白厄 3(m6)/卖忘归人(+3)/买白厄 3(m6) | →133 | 全非线内;燃料(忘归人/飞霄/艾丝妲)售罄 | 每帧被买/卖占用,刷新无评估位(单动作契约,shop.py:772-794) |
| 110 | 收店 | 136 | 残牌万敌1/海瑟音4 | bench 9/9 ∧ 本轮新买件受换出守卫(dead_pair_exit_guard_kept_young=6)→ 燃料售空 → seat_ok=False → **P92 拦刷门全通道空 → 拒 `p92_no_buy_refresh_blocked`**(3 帧之一)+`must_spend_r1_no_buy_blocked` → 收工置标记 |
| 111-112 | 部署千冶·刃→back3;开店 | 136 | — | 备战解拦复核(bench_full 机会+席空出)清标记重开(session_scope.py:398-428) |
| 113 | 买万敌 1(m6) | 132 | — | bench 回 9/9 |
| 114 | 收店 | 132 | 残牌海瑟音 4金 | 同 dseq110:P92 拦刷(3 帧之二);记 bench_full 机会 |
| 115-117 | 卖黄泉(+3)/部署星期日→back4(列车×3 唯一羁绊升档)/巨星选花火 | 135 | — | — |
| 118-119 | 开店(读数)→收店 | 135 | 牌面读取空 | 读数会话零处理不置标记(close_read_noop=1) |
| 120 | 开店(解拦:海瑟音 bench_full 机会+席空) | 135 | 残牌海瑟音 4金 | — |
| 121 | 买海瑟音 4(m6,全局最贵买笔) | 131 | 非线内 | M6 |
| 122 | 收店 | 131 | 店空 | 同 dseq110:P92 拦刷(3 帧之三)→ 收工 |

### 1.5 P2r5(节点 2-5 遭遇,金 131→死亡时 142):备战帧无开店直出遭遇(dseq123-124);局终收入 +11 → 金 142 死亡(abnormal)。

**店况供给总账(P2 掷新牌板仅 4 块:r1 板、r2 板、r4 板、r4 刷新板,共 20 槽)**:瓦尔特 **0 次**、姬子·启行 **0 次**、花火 **0 次**、三月七 1 次(r2 槽1)。其余 17 槽全为非线内件。

## 2. 三条假设的归因结论

**主导 = 假设③(店况概率×等级结构)+ 假设①(升级闸含 hp 入参,经「升级优先」前置间接锁死刷新),两段各辖一半;假设②(判据缺陷)在 r4 席位坍缩段实锤为次因。**

- **「为什么不买」→ ③ 主导,占 P2 全部商店帧**:线内缺件三件在 5/6 级的供给面结构性枯竭——瓦尔特 **5 费**(cw_chars.py:190),REFRESH_PROB 5/6 级 5 费档**不存在**(7 级起 1%,cw_shop_odds.py:47-58)→ 出现率**恒 0**,不是低;姬子·启行 3 费(单板命中约 7-9%)、花火 2 费(约 11-13%)在仅有的 4 块板上全空属正常概率(全空概率 50-60% 量级);唯一进店的三月七被买臂结构够不着(见缺陷候选 5)。**而提升出现率的唯一通道(升级 6→7+)被假设①拦死**——③ 与 ① 在此耦合。
- **「为什么不刷」→ r1/r2 是 ①,经「升级优先」前置起作用;刷新判据链本身无 hp 入参**:refresh_warranted 等级<带下界 → 拒 `stay_gate_upgrade_first`(refresh.py:101-105,counter=2:dseq84/97);它要求的升级被 P21 危机全域拦(`levelup_crisis_defer=17`,资金门 0 拦)→ 升级/刷新互锁双关。r4 等级 6∈带后判据放行,但**席位坍缩使 P92 拦刷门把追星刷新一并拦掉**(`p92_no_buy_refresh_blocked=3`:dseq110/114/122)——M6 在 r4 灌满 bench 且燃料售空(本轮新买件受 young 守卫),席位维 seat_ok=False → 全通道空 → 拒刷(见缺陷候选 2)。20 槽里只掷出 1 次付费刷新的直接原因=发射位次最低(六序末)+ 每轮仅 1 块免费板 + P92 席位拦刷。
- **「不花钱」的准确形态**:支出通道不是全关——M6(触发域=gold>g*=50,无位面门,shop.py:1543-1616)在 P2 开火 12 次 24 金+scene_plugin 2 次 5 金;**关掉的是「线内转化型支出」**(M2 缺件买+追星刷新)。M6 买的非线内 1★ 终局 9/9 压 bench(报告 L3311),金完成了「花」但零战力转化——FM-1 死型机理(目标态缺口=∅ ∧ 期收入>0 → 金位单调不降)在本局表现为「缺口件买不到/刷不出,富余金走 M6 囤积」。
- **dead_gold_press_buy 触发域**(问题清单 2):`gold < g*(=50) ∧ 奖励帧`(shop.py:1419,`reward_node_suppressed`),本局 3 次全在 P1 奖励节点(金 9-29<50);**P2 触发域为空集**:金全程 ≥108>50 且 P2 节点序(battle/battle/supply/battle/encounter)无奖励帧——双重出辖,与 hp 无关。

## 3. 资金面核对(问题清单 4)

- g* = saturation_line = 10×cap_resolved(cw_economy.py:339-341);P2 等级 5/6 段 cap=5 → g*=50。金 108-142 全程 > g* → **富余段(must-spend zone)全程命中**(`must_spend_l2_trigger=9`)。
- 对「买」:富余段放行 M6/档 1/垫件;义务面 M2 走息律门豁免([41] 序 1/2 不走息律门)——资金面**从未拦买**(本局无一条买拒因是资金类;`m6_s_reserve_reject` 键零出现)。
- 对「刷」:r2 预算门=g*+ρ(合格集最低费=花火 2)+待付升级批(本局升级门 verdict=miss,不追加)→ 预算 52,金 132-142 恒过——资金面也**从未拦刷**。
- 设计声明核对:**对不上本局形态**。`changes/2026-10-18-levelup-band-gate/design.md:156` 申报的「攒息期升级-刷新双滞(金上涨+吃息)= 预期健康态」其模型域=「现金 30-60<线+批、等凑金发射」——本局金 108-142**远超线+批**(r1 时 111−16=95≥50,资金门可发射),实际拒因键是 `levelup_crisis_defer`(17/17)而非 `levelup_fund_line_defer`(0/0)。该声明依赖的释放条件「金攒够 → 凑金可达 → 发射」在危机闸路径上**不存在**(危机判定金位无关,cw_discipline_rules.py:212-232「危机带帧无论金位一律拦」)——声明覆盖的滞留形态与本局滞留形态是两个键、两套释放条件。

## 4. 系统性核验(问题清单 6;只引已登记读数)

- `strategy-docs/11_shop_decisions.md:186`(升级触发统一批 sim 预注册读数,n=20,sim 死亡 15 局):**「FM-1 对照读数:死时金 ≥ 50 = 15/15」**——本局死时金 142 同形态;同批「stay_gate 触发 85 帧(9/20 局)全部被 P21 危机带全域拦(85/85,触发/危机拦逐局相等);升级发射帧=0」——与本局 17/17、发射 0 **同键同构**;「死亡局终金 51-146(中位 105)」本局 142 在区间内偏高端。
- 本局 cw4_counters 与该批读数逐键同构:等级腿零命中(终局 lv 4-6 批侧;本局 lv6)、四联完整死型 0/15(本局同不为完整四联)。
- 结论:**「升级 stay_gate 触发→危机全域拦→零发射→金滞留至死」是 sim 批的系统性形态**(同批 9/20 局),本局非孤例;批侧该读数已明注「禁外推实机发射频率」(sim hp 校准失真,hp 类只作报警线)。

## 5. 缺陷候选清单(策略侧;单局=候选,跨局/sim 复测才定案)

1. **[高] 升级-刷新双滞无解锁支**:等级<停留带下界时刷新判据拒(升级优先,refresh.py:101-105)、升级判据触发但被危机全域拦(levelup.py:371-377;cw_discipline_rules.py:212-232),两通道互锁且无任何让位/降级支(如「升级被 defer N 帧后带内降档刷新」)。本局 17 帧 trigger=17 defer;批基线 85/85(11_shop_decisions.md:186)。锚:criteria/refresh.py:101-105、criteria/levelup.py:269-277+371-377、counters `levelup_trigger_stay_gate=17`/`levelup_crisis_defer=17`。
2. **[高] P92 拦刷门通道集缺「追星刷新」腿**:席位坍缩帧(bench 9/9 ∧ seat_recoverable 判空)全通道空 → 拒刷;但掷新牌本身不占席,追星刷新在席满帧恰恰是合法支出。锚:criteria/refresh.py:282-378(all_channel_buy_exists 无 stay-target 腿)、shop.py:2044-2065、counters `p92_no_buy_refresh_blocked=3`(r4 收店帧系)。
3. **[中] M6 囤货与追星刷新无席面协调**:富余段 M6 无席位预留/降权,把 bench 灌满后反手触发缺陷 2 锁死刷新,并挤压后续 m2_stockpile 需席。锚:shop.py:1543-1616、报告 L3130-3307(r4 六笔非线内买入)、counters `m6_bench_full=8`。
4. **[中] 义务面名单星级盲**:missing 按名集(shop.py:930),已持有 2★ 的线内成员同名 1★ 副本进不了任何买臂(m2_stockpile 门 `_cnt(m,2)!=0` 关闭,shop.py:1277-1279)→ 2★→3★ 追星通道结构性断裂(本局三月七 need 2★ 已满足未生效;need 3★ 成员即爆)。锚:shop.py:930+1277-1279、报告 L2784(三月七 1金 未买)。
5. **[低] 目标不可达性无决策出口**:5 费缺件(瓦尔特)在当前等级路径出现率恒 0 时仅被静默过滤(refresh_prob=0),无「该目标本局不可达 → 换线/降档/升等重排」的显式决策。锚:criteria/refresh.py:206-233(qualified_member_costs)、cw_shop_odds.py:47-58、cw_chars.py:190、决策 payload k_members 全程含瓦尔特(mandate jsonl 77-124)。
6. **[低] 刷新发射曝光率低**:刷新=会话循环第 7 位(单动作契约),每轮免费板仅 1 块,帧被买/卖占满即无评估位——追星窗口的实际掷店密度=每轮 1 板+付费刷,与本局仅 4 板 20 槽直接相关。锚:shop.py:772-794(契约+位次)、1962-2061(发射段)、报告商店章(4 块板)。

## 6. 数据边界声明

- 拒因计数键不带 dseq,「dseq84/97=stay_gate 帧、dseq110/114/122=p92 帧」为**计数守恒推断**(counter 总数与可达到步骤 6 的帧集恰好相等,逐帧动作集已核对),非逐帧日志直证。
- dseq119/118 的读数会话、解拦复核时序按代码语义重构(session_scope.py:398-428、shop.py:810-828),回执行不携带关店 reason。
- sim 战斗结算随机(P(win)=0.5),r2 战败 38→1 不进归因;板面概率为按 REFRESH_PROB+超几何池模型的估算(cw_shop_odds.py:125-148)。
- hp 层面的全仓清查由另一子 agent 负责,本文不重复;本文 hp 只出现在「危机闸键语义」这一处事实引用。

## 7. A-9 交叉复核(2026-10-28 二轮裁定;回应 hp 逻辑清查件 A-9 与本文 §1.4 的表面矛盾)

**A-9 声称**:`is_emergency`(hp≤25,cw_economy.py:1074-1088)→ `refresh_ev_budget` 归 0(:1275)→ economy_cycle.py:187 吃掉义务支出 C_t 刷新分量 → 本局 r4(hp=1)刷新预算应为 0,与本文「r4 判据放行+预算 52+P92 过」矛盾。

**裁定:本文 §1.4 正确;A-9 的链路前两环真实、末环(消费归因)错误。归零量不闸 mandate_v1 的任何实际动作。**

### 7.1 代码链路核验(①)

- `refresh_ev_budget` 全仓**调用点仅 2 处**(grep 语法级核实,其余命中均为 docstring/注释):
  1. `economy_cycle.py:187`(`channel_capacity` 刷新分量)→ 唯一下游 `obligation()`(:207)→ 唯一消费者 `disclose_budget`(:295)写 `v3_release_budget`——**遥测披露面**,函数 docstring 明文「不入决策输入……披露面字段禁决策消费」(economy_cycle.py:243-255,守卫测试 = test_economy 预算遥测披露节),读端 = recorder `sess_release_budget` 透传(schema.py:486-504:「sess_release_budget 记账面(预算许可),不作兑现证据」);
  2. `cw_economy.py:995`(`get_node_goal` **标量投影分支**):mandate_v1 现役调用 `statefn/budget.py:106` 是 `get_node_goal(plane, round)` **不带标量参数** → 走 :1000 先验 fallback 分支,**该分支不调 refresh_ev_budget**(budget.py:88 明注「零 hp 依赖零 seam 日志」),且喂的是 `next_level_xp_cost` 升级金投影、非刷新决策。
- **旧执行层预算门已停用**:`authorize_release_refresh`/`_accrue_release_frame_spend` 仅存于 docstring 停用史引用(schema.py:500-501「旧 authorize_release_refresh/_accrue_release_frame_spend 机制停用史与口径裁决」;economy_cycle.py:24/233),零现役调用。
- **mandate_v1 商店刷新发射链不含任何 hp/EV 预算面输入**:免费刷 → `refresh_warranted`(查表,refresh.py:74-108)→ `r2_budget(gold−(g*+ρ+升级预留)≥刷价,shop.py:1987-1995)` → P92 拦刷门(refresh.py:282-378);`r1_start` docstring 明注「原路径总账比较式判据面已由查表判据取代……**禁按旧 EV 正性语义复活接线**」(refresh.py:140-152)。刷新判据族唯一 hp 邻接件 `crisis_refresh_invariant` 在发射链零消费(mandate.py:1078-1079「结构位在 executor——此处为序位声明」),且其式(hp_critical ∧ gold≤0,refresh.py:160-165)在本局金 100+ 恒 False。

### 7.2 本局数据证据(②)

- **行为直证**:hp=1 的 r4 帧,付费刷新真实执行——dseq103,journal gold 写行 v764=139 → v769=137,聚合 receipts 含 `CwActionRefreshShopParam`(dseq103)。若 A-9 链在发射位生效,该回执不可能存在。
- **计数面**:cw4_counters 72 键中**无任何** refresh-EV/义务预算类键(无 refresh_ev_*、无 release_budget_*);`sess_release_budget` 属 session 侧 recorder 透传字段,不在 journal 字段集(39 字段逐一枚举核过)——归零链在遥测面有形、在决策计数面无痕。
- r4 实际刷新放行算术(g*=50+ρ=2,金 139−52≥2)与该会话唯一刷新侧拒因计数(`p92_no_buy_refresh_blocked=3`)见本文 §1.4 与 §5-2。

### 7.3 对 R-2 裁决的口径修正(供 hp 清查件参考)

A-9 指认的「应急带刷新闸」在 mandate_v1 现役链上**不闸任何动作**:它塑造的只是 ① 遥测义务账(C_t/`sess_release_budget` 的刷新分量,hp≤25 帧记 0)与 ② 一个现役调用走不到的 v2 姿态投影分支。因此 R-2「应急带刷新闸删不删」应先改对象口径:动 `refresh_ev_budget` 的 is_emergency 归零 = 改遥测义务账与 v2 投影语义,对 mandate_v1 商店刷新发射**零行为差**;若裁决目标本就含 v2 栈或披露账读数,则属另一改面。本局「hp=1 却仍刷新」不是闸失效,而是闸根本不在这条链上——与本文 §2 主结论(刷新拒因 = stay_gate 前置死锁 + P92 席位坍缩,均无 hp 入参)自洽。


---

# 快照三：单局复盘 g_20261028_011013（源 = .debug/currency_war/deep_review/g_20261028_011013.md）

# 货币战争复盘 g_20261028_011013

## 局头

- 对局: g_20261028_011013
- 运行段: run_20261028_011013
- 策略版本 commit: a42f1e2cd
- 注册表指纹: e391af59e6fe
- 时间窗: 2026-10-28T01:10:13 ~ 2026-10-28T01:10:23
- 终局: abnormal 位面 P2-R5 hp — 金 142 时长 10s
- 数据完整性: 无
- 策略遥测: mandate_v1 (124 条)(未归属 3 条)

## 开局

### 开局 画面-BOSS简报

#### 0 观察

- 位面首领(plane_bosses) ["巨鹿生物制药","智识实验室","深穹智械科技"]
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]
- 选择难度(selected_difficulty) A8

### 开局 画面-投资环境

#### 0 观察

- 金(gold) 3

#### 策略评价
- **决策正确性**:合格——选「列车同行概念股」为五项相加 argmax(策略遥测 dseq1:total=144=cash0+dir100+gift44;判据=strategy-docs/28_invest_env_screen.md §1/§2,dir100=S 档列车线,gift44=随机列车角色赠卡档分均值)。宏观判尺=M1「run 的入口是资源」(docs/game/currency_war/research/plaza_methodology.md §M1)。
- **是否符合发展主线**:✓——该环境=列车线策略型硬锁定信号(kernel/cw_comps.py:661 lock_rules),本局自首帧 direction.locked=true(comp=列车同行)即由此承接;列车=十类终局线最大类(final_comps/README.md 类别索引 274 篇)。
- **备选与改进**:圣杯邀请/昼之半神概念股按同机器总分更低;env_refresh_left=1 未用(报告 L67)——按 28 §4「帧最好<全表均值才刷」不刷合理。缺口:本章策略依据块缺席(dseq1 未装配),见复盘者附加·完整性申报 1。


### 开局 画面-备战

#### 0 观察

- 金(gold) 3
- 血(hp) 82
- 等级(level) 3
- 经验(xp) 0/4
- 连胜(streak) 0
- 后台格数(back_layout) 6
- 装备库存(equips) 轮滑鞋
- 穿戴(occupied_equips) {}
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) (空)
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 空 | 空 | 空 | 空 | — | — |
| 后排 | 空 | 空 | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 飞霄1★ | 砂金1★ | 吉尔伽美什1★ | 姬子·启行1★ | 空 | 空 | 空 | 空 |

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 投资环境候选(invest_env_opts) | 命运圣杯邀请、列车同行概念股、昼之半神概念股 → 命运圣杯邀请、列车同行概念股、昼之半神概念股 | (前值=累计快照) |
| 环境刷新余量(env_refresh_left) | 1 → 1 | (前值=累计快照) |
| 投资环境(active_env) | 列车同行概念股 → 列车同行概念股 | (前值=累计快照) |
| 节点序列(node_seq_by_plane) | P1: 奖励→奖励→战斗→战斗→补给→战斗→遭遇→奖励→BOSS;P2: 战斗→战斗→补给→战斗→遭遇→奖励→BOSS;P3: 战斗→战斗→补给→战斗→遭遇→奖励→BOSS → P1: 奖励→奖励→战斗→战斗→补给→战斗→遭遇→奖励→BOSS;P2: 战斗→战斗→补给→战斗→遭遇→奖励→BOSS;P3: 战斗→战斗→补给→战斗→遭遇→奖励→BOSS | (前值=累计快照) |
| 备战席(bench) | 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★(空×4) → 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★(空×4) | (前值=累计快照) |
| 装备库存(equips) | 轮滑鞋 → 轮滑鞋 | (前值=累计快照) |

#### 策略评价
- **决策正确性**:本章=入口观察+章内变化显影,无策略动作面;开局手牌 5 张为局配置发放,无决策可评。
- **是否符合发展主线**:✓ active_env=列车同行概念股 已生效;方向 locked=true(k_members=姬子·启行/三月七/花火/瓦尔特;12_line_and_intention.md §1.3 硬规则·策略型先到先锁)。
- **备选与改进**:无。


## 节点 1-1 奖励

### 节点 1-1 奖励 画面-备战

#### 0 观察

- 金(gold) 3
- 血(hp) 82
- 等级(level) 3
- 经验(xp) 0/4
- 连胜(streak) 0
- 后台格数(back_layout) 6
- 羁绊计数(board) {}
- 装备库存(equips) 轮滑鞋
- 穿戴(occupied_equips) {}
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) (空)
- 投资环境(active_env) 列车同行概念股
- 节点序位(node_pos) [1,1]

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 空 | 空 | 空 | 空 | — | — |
| 后排 | 空 | 空 | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 飞霄1★ | 砂金1★ | 吉尔伽美什1★ | 姬子·启行1★ | 空 | 空 | 空 | 空 |

#### 1 采晶矿 采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:2(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:2

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿奖励(ore_rewards) | 10,10=装备 和平手枪;20,10=金+2;30,10=角色 ?;40,10=装备 量产型装甲;50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 → 10,10=装备 和平手枪;20,10=金+2;30,10=角色 ?;40,10=装备 量产型装甲;50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 | (前值=累计快照) |
| 晶矿(spheres) | 8 座(金×1,蓝×1,灰×1) → 7 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 10,10=装备 和平手枪;20,10=金+2;30,10=角色 ?;40,10=装备 量产型装甲;50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 → 20,10=金+2;30,10=角色 ?;40,10=装备 量产型装甲;50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 |  |
| 装备库存(equips) | 轮滑鞋 → 轮滑鞋、和平手枪 |  |
| 晶矿(spheres) | 7 座(蓝×1,灰×1) → 6 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 20,10=金+2;30,10=角色 ?;40,10=装备 量产型装甲;50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 → 30,10=角色 ?;40,10=装备 量产型装甲;50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 |  |
| 金(gold) | 7 → 9 |  |
| 晶矿(spheres) | 6 座(蓝×1,灰×1) → 5 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 30,10=角色 ?;40,10=装备 量产型装甲;50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 → 40,10=装备 量产型装甲;50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 |  |
| 备战席(bench) | 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★(空×4) → 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★、翡翠1★(空×3) |  |

#### 2 采晶矿 采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:3(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:3

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿(spheres) | 5 座(蓝×1,灰×1) → 4 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 40,10=装备 量产型装甲;50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 → 50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 |  |
| 装备库存(equips) | 轮滑鞋、和平手枪 → 轮滑鞋、和平手枪、量产型装甲 |  |
| 晶矿(spheres) | 4 座(蓝×1,灰×1) → 3 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 50,10=装备 轮滑鞋;60,10=金+3;70,10=装备 以太钻头;80,10=金+5 → 60,10=金+3;70,10=装备 以太钻头;80,10=金+5 |  |
| 装备库存(equips) | 轮滑鞋、和平手枪、量产型装甲 → 轮滑鞋、和平手枪、量产型装甲、轮滑鞋 |  |
| 晶矿(spheres) | 3 座(蓝×1,灰×1) → 2 座(灰×1) |  |
| 晶矿奖励(ore_rewards) | 60,10=金+3;70,10=装备 以太钻头;80,10=金+5 → 70,10=装备 以太钻头;80,10=金+5 |  |
| 金(gold) | 9 → 12 |  |

#### 3 采晶矿 采晶矿 2 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:4(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=采晶矿 2 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:4

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿(spheres) | 2 座(灰×1) → 1 座(灰×1) |  |
| 晶矿奖励(ore_rewards) | 70,10=装备 以太钻头;80,10=金+5 → 80,10=金+5 |  |
| 装备库存(equips) | 轮滑鞋、和平手枪、量产型装甲、轮滑鞋 → 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头 |  |
| 晶矿(spheres) | 1 座(灰×1) → 0 座 |  |
| 晶矿奖励(ore_rewards) | 80,10=金+5 → (空) |  |
| 金(gold) | 12 → 17 |  |

#### 4 开店
- 策略依据: mandate_v1:5(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:5

#### 策略评价
- **决策正确性**:合格——8 座晶矿全采(金 7→17+装备 4 件+翡翠,零成本资产入口);采毕开店进店,备战工序序合规。
- **是否符合发展主线**:✓ 无偏离。
- **备选与改进**:无(payload window 全 open:false=开局窗口信号未点亮,常态)。


### 节点 1-1 奖励 画面-商店

#### 0 观察

- 金(gold) 17
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 3
- 概率(refresh_probs) 1→100%

**商店牌面(shop)**

| 槽 | 牌名 | 阵营 | 费用 | 星级 |
|---|---|---|---|---|
| 1 | 爻光 | 仙舟 | 1 | 1★ |
| 2 | 乱破 | 巡海游侠 | 1 | 1★ |
| 3 | 飞霄 | 狼狩 | 1 | 1★ |
| 4 | 三月七 | 列车同行 | 1 | 1★ |
| 5 | 赛飞儿 | 夜之半神 | 1 | 1★ |

#### 1 买牌 三月七(1金)
- 策略依据: mandate_v1:6(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m2_line_member)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: 三月七(列车同行,1金,槽4) · char_id=三月七 · reason=m2_line_member
  - dtag: mandate_v1:6

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 1]: 三月七 → phase[1, 1]: 三月七 | (前值=累计快照) |
| 金(gold) | 17 → 16 |  |
| 商店牌面(shop) | 爻光1金、乱破1金、飞霄1金、三月七1金、赛飞儿1金 → 爻光1金、乱破1金、飞霄1金、赛飞儿1金(空×1) |  |
| 备战席(bench) | 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★、翡翠1★(空×3) → 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★、翡翠1★、三月七1★(空×2) |  |

#### 2 买牌 乱破(1金)
- 策略依据: mandate_v1:7(entry=decide_shop_action, op=CwActionBuyCardParam, reason=scene_plugin_buy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: 乱破(巡海游侠,1金,槽2) · char_id=乱破 · reason=scene_plugin_buy
  - dtag: mandate_v1:7

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 1]: 三月七 → phase[1, 1]: 三月七、乱破 |  |
| 金(gold) | 16 → 15 |  |
| 商店牌面(shop) | 爻光1金、乱破1金、飞霄1金、赛飞儿1金(空×1) → 爻光1金、飞霄1金、赛飞儿1金(空×2) |  |
| 备战席(bench) | 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★、翡翠1★、三月七1★(空×2) → 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★、翡翠1★、三月七1★、乱破1★(空×1) |  |

#### 3 买牌 爻光(1金)
- 策略依据: mandate_v1:8(entry=decide_shop_action, op=CwActionBuyCardParam, reason=dead_gold_press_buy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: 爻光(仙舟,1金,槽1) · char_id=爻光 · reason=dead_gold_press_buy
  - dtag: mandate_v1:8

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 1]: 三月七、乱破 → phase[1, 1]: 三月七、乱破、爻光 |  |
| 金(gold) | 15 → 14 |  |
| 商店牌面(shop) | 爻光1金、飞霄1金、赛飞儿1金(空×2) → 飞霄1金、赛飞儿1金(空×3) |  |
| 备战席(bench) | 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★、翡翠1★、三月七1★、乱破1★(空×1) → 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★、翡翠1★、三月七1★、乱破1★、爻光1★ |  |

#### 4 收店
- 策略依据: mandate_v1:9(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:9

#### 策略评价
- **决策正确性**:合格——三月七=m2_line_member(M2 义务免利息门,02_mandate_layer.md:42/11_shop_decisions.md:23);乱破=scene_plugin_buy;爻光/赛飞儿=dead_gold_press_buy(②(b) 死金压牌库:奖励帧∧gold<g*=50,买入地板 cost≤死金 7/4,strategies/impl/mandate_v1/shop.py:1419-1446;判据出处=11_shop_decisions.md:43)。全部 1★ 全额退=活期资产([11] 零利息损失口径,11_shop_decisions.md:21)。
- **是否符合发展主线**:✓ 三月七=k_members 首副本;爻光=仙舟3 体系成员(保护集)经死金臂 prio1 保护腿承接(shop.py:1433-1439),行为=囤货同向。
- **备选与改进**:爻光买因标签按 12_line_and_intention.md §4 应记 protection_hoard——标签差异非行为差异,不改判。


### 节点 1-1 奖励 画面-备战

#### 0 观察

- 金(gold) 14
- 血(hp) 82
- 等级(level) 3
- 经验(xp) 0/4
- 连胜(streak) 0
- 后台格数(back_layout) 6
- 羁绊计数(board) {}
- 装备库存(equips) 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) (空)
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 空 | 空 | 空 | 空 | — | — |
| 后排 | 空 | 空 | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 飞霄1★ | 砂金1★ | 吉尔伽美什1★ | 姬子·启行1★ | 翡翠1★ | 三月七1★ | 乱破1★ | 爻光1★ |

#### 1 换位 部署槽5→front1 ✓(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:10(entry=decide_prep_screen, op=CwActionDeployMoveParam, route_tag=m5_opening_board)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=部署槽5→front1 ✓(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:10

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、姬子·启行1★、翡翠1★、三月七1★、乱破1★、爻光1★ → 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、翡翠1★、三月七1★、乱破1★、爻光1★(空×1) |  |
| 上阵(deployed) | 前排 姬子·启行1★;后排 (空) → 前排 姬子·启行1★;后排 (空) | (前值=累计快照) |
| 羁绊计数(board) | (空) → 列车同行×1、领航员×1 |  |

#### 2 开店
- 策略依据: mandate_v1:11(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=step4_shop_session)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:11

#### 策略评价
- **决策正确性**:合格——姬子·启行 front1(M5 开局板面,02_mandate_layer.md:45);领航员羁绊随行显影。
- **是否符合发展主线**:✓ 列车配方开局上架(P1 锁定局采购集=开局配方∪锁定线名单并集,12 §1.2)。
- **备选与改进**:无。


### 节点 1-1 奖励 画面-商店

#### 0 观察

- 金(gold) 14
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 3

#### 1 买牌 赛飞儿(1金)
- 策略依据: mandate_v1:12(entry=decide_shop_action, op=CwActionBuyCardParam, reason=dead_gold_press_buy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: 赛飞儿(夜之半神,1金,槽5) · char_id=赛飞儿 · reason=dead_gold_press_buy
  - dtag: mandate_v1:12

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 1]: 三月七、乱破、爻光 → phase[1, 1]: 三月七、乱破、爻光、赛飞儿 |  |
| 金(gold) | 14 → 13 |  |
| 商店牌面(shop) | 飞霄1金、赛飞儿1金(空×3) → 飞霄1金(空×4) |  |
| 备战席(bench) | 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、翡翠1★、三月七1★、乱破1★、爻光1★(空×1) → 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、三月七1★、乱破1★、爻光1★ |  |

#### 2 收店
- 策略依据: mandate_v1:13(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:13

#### 策略评价
- **决策正确性**:合格——赛飞儿 1 金 dead_gold_press(金 14→13,死金 4≥1,奖励帧门内)。
- **是否符合发展主线**:中性——非线件压牌库/活期资产,11_shop_decisions.md:112 P90 前窗买入语义合规。
- **备选与改进**:无。


### 节点 1-1 奖励 画面-备战

#### 0 观察

- 金(gold) 13
- 血(hp) 82
- 等级(level) 3
- 经验(xp) 0/4
- 连胜(streak) 0
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×1、领航员×1
- 装备库存(equips) 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) (空)
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 空 | 空 | 空 | — | — |
| 后排 | 空 | 空 | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 飞霄1★ | 砂金1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 三月七1★ | 乱破1★ | 爻光1★ |

#### 1 换位 部署槽7→back1 ✓(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:14(entry=decide_prep_screen, op=CwActionDeployMoveParam, route_tag=m1_deploy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=部署槽7→back1 ✓(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:14

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、三月七1★、乱破1★、爻光1★ → 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、乱破1★、爻光1★(空×1) |  |
| 上阵(deployed) | 前排 姬子·启行1★;后排 (空) → 前排 姬子·启行1★;后排 三月七1★ |  |
| 羁绊计数(board) | 列车同行×1、领航员×1 → 列车同行×2、领航员×1、护盾×1 |  |

#### 2 换位 部署槽3→front2 ✓(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:15(entry=decide_prep_screen, op=CwActionDeployMoveParam, route_tag=m1_deploy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=部署槽3→front2 ✓(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:15

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 乱破1★、飞霄1★、砂金1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、乱破1★、爻光1★(空×1) → 乱破1★、飞霄1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、乱破1★、爻光1★(空×2) |  |
| 上阵(deployed) | 前排 姬子·启行1★;后排 三月七1★ → 前排 姬子·启行1★、砂金1★;后排 三月七1★ |  |
| 羁绊计数(board) | 列车同行×2、领航员×1、护盾×1 → 列车同行×2、领航员×1、护盾×2、公司×1、追击×1 |  |

#### 3 出战 出战已点击(无弹窗)
- 策略依据: mandate_v1:16(entry=decide_prep_screen, op=CwActionStartBattleParam, route_tag=battle)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=出战已点击(无弹窗) · 画面=货币战争-备战
  - dtag: mandate_v1:16

#### 策略评价
- **决策正确性**:合格——三月七 back1、砂金 front2 部署(M1);board=列车×2+护盾×2,列车2 体系(四体系之一,transition_combos.md §定义)开局内点亮;cap3 满配出战。
- **是否符合发展主线**:✓ 过渡主线起点达成。
- **备选与改进**:乱破×2/爻光 留 bench 合理(1★ 活期+保护集期权,12 §1.2 囤货纪律)。


### 节点 1-1 奖励 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★
- 后排(back_slots) 三月七1★
- 敌方难度(enemy_difficulty) 108
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 结算(settlement) | — → — | (前值=累计快照) |

### 节点 1-1 奖励 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [1,1] → [1,2] |  |

## 节点 1-2 奖励

### 节点 1-2 奖励 画面-备战

#### 0 观察

- 金(gold) 13
- 血(hp) 82
- 等级(level) 3
- 经验(xp) 2/4
- 连胜(streak) 0
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1
- 装备库存(equips) 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) (空)
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七1★ | 空 | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 飞霄1★ | 空 | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 空 | 乱破1★ | 爻光1★ |

#### 1 采晶矿 采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:17(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:17

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿奖励(ore_rewards) | (空) → 10,10=金+1;20,10=装备 幸运星;30,10=装备 以太钻头;40,10=金+4;50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 |  |
| 晶矿(spheres) | 8 座(金×1,蓝×1,灰×1) → 7 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 10,10=金+1;20,10=装备 幸运星;30,10=装备 以太钻头;40,10=金+4;50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 → 20,10=装备 幸运星;30,10=装备 以太钻头;40,10=金+4;50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 |  |
| 金(gold) | 19 → 20 |  |
| 晶矿(spheres) | 7 座(蓝×1,灰×1) → 6 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 20,10=装备 幸运星;30,10=装备 以太钻头;40,10=金+4;50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 → 30,10=装备 以太钻头;40,10=金+4;50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 |  |
| 装备库存(equips) | 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头 → 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星 |  |
| 晶矿(spheres) | 6 座(蓝×1,灰×1) → 5 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 30,10=装备 以太钻头;40,10=金+4;50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 → 40,10=金+4;50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 |  |
| 装备库存(equips) | 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星 → 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星、以太钻头 |  |

#### 2 采晶矿 采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:18(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:18

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿(spheres) | 5 座(蓝×1,灰×1) → 4 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 40,10=金+4;50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 → 50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 |  |
| 金(gold) | 20 → 24 |  |
| 晶矿(spheres) | 4 座(蓝×1,灰×1) → 3 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 50,10=角色 ?;60,10=装备 和平手枪;70,10=金+2;80,10=金+3 → 60,10=装备 和平手枪;70,10=金+2;80,10=金+3 |  |
| 备战席(bench) | 乱破1★、飞霄1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、乱破1★、爻光1★(空×2) → 乱破1★、飞霄1★、三月七1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、乱破1★、爻光1★(空×1) |  |
| 晶矿(spheres) | 3 座(蓝×1,灰×1) → 2 座(灰×1) |  |
| 晶矿奖励(ore_rewards) | 60,10=装备 和平手枪;70,10=金+2;80,10=金+3 → 70,10=金+2;80,10=金+3 |  |
| 装备库存(equips) | 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星、以太钻头 → 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星、以太钻头、和平手枪 |  |

#### 3 采晶矿 采晶矿 2 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:19(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=采晶矿 2 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:19

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿(spheres) | 2 座(灰×1) → 1 座(灰×1) |  |
| 晶矿奖励(ore_rewards) | 70,10=金+2;80,10=金+3 → 80,10=金+3 |  |
| 金(gold) | 24 → 26 |  |
| 晶矿(spheres) | 1 座(灰×1) → 0 座 |  |
| 晶矿奖励(ore_rewards) | 80,10=金+3 → (空) |  |
| 金(gold) | 26 → 29 |  |

#### 4 开店
- 策略依据: mandate_v1:20(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:20

#### 策略评价
- **决策正确性**:合格——8 矿全采(金+幸运星/以太钻头/和平手枪)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-2 奖励 画面-商店

#### 0 观察

- 金(gold) 29
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 3
- 概率(refresh_probs) 1→100%

**商店牌面(shop)**

| 槽 | 牌名 | 阵营 | 费用 | 星级 |
|---|---|---|---|---|
| 1 | 飞霄 | 狼狩 | 1 | 1★ |
| 2 | 椒丘 | 狼狩 | 1 | 1★ |
| 3 | 远坂凛 | 命运圣杯 | 1 | 1★ |
| 4 | 翡翠 | 公司 | 1 | 1★ |
| 5 | 大丽花 | 盛会之星 | 1 | 1★ |

#### 1 买牌 椒丘(1金)
- 策略依据: mandate_v1:21(entry=decide_shop_action, op=CwActionBuyCardParam, reason=dead_gold_press_buy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: 椒丘(狼狩,1金,槽2) · char_id=椒丘 · reason=dead_gold_press_buy
  - dtag: mandate_v1:21

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 1]: 三月七、乱破、爻光、赛飞儿 → phase[1, 2]: 椒丘 |  |
| 金(gold) | 29 → 28 |  |
| 商店牌面(shop) | 飞霄1金、椒丘1金、远坂凛1金、翡翠1金、大丽花1金 → 飞霄1金、远坂凛1金、翡翠1金、大丽花1金(空×1) |  |
| 备战席(bench) | 乱破1★、飞霄1★、三月七1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、乱破1★、爻光1★(空×1) → 乱破1★、飞霄1★、三月七1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ |  |

#### 2 收店
- 策略依据: mandate_v1:22(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:22

#### 策略评价
- **决策正确性**:合格——椒丘 1 金 dead_gold_press(奖励帧,死金 9≥1);prio1 保护集腿(椒丘=DOT2 体系成员,shop.py:1433-1439)。
- **是否符合发展主线**:✓ 保护集囤货(DOT2=过渡四体系之一)。
- **备选与改进**:无。


### 节点 1-2 奖励 画面-备战

#### 0 观察

- 金(gold) 28
- 血(hp) 82
- 等级(level) 3
- 经验(xp) 2/4
- 连胜(streak) 0
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1
- 装备库存(equips) 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星、以太钻头、和平手枪
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) (空)
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七1★ | 空 | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 飞霄1★ | 三月七1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 乱破1★ | 爻光1★ |

#### 1 出战 出战已点击(无弹窗)
- 策略依据: mandate_v1:23(entry=decide_prep_screen, op=CwActionStartBattleParam, route_tag=battle)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=出战已点击(无弹窗) · 画面=货币战争-备战
  - dtag: mandate_v1:23

#### 策略评价
- **决策正确性**:合格——板面 3/3(cap3)满配,无新增动作面直接出战。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-2 奖励 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★
- 后排(back_slots) 三月七1★
- 敌方难度(enemy_difficulty) 108
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 1-2 奖励 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [1,2] → [1,3] |  |

## 节点 1-3 战斗

### 节点 1-3 战斗 画面-备战

#### 0 观察

- 金(gold) 28
- 血(hp) 82
- 等级(level) 4
- 经验(xp) 0/6
- 连胜(streak) 0
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1
- 装备库存(equips) 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星、以太钻头、和平手枪
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) (空)
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七1★ | 空 | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 飞霄1★ | 三月七1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 乱破1★ | 爻光1★ |

#### 策略评价
- **决策正确性**:合法空集——金 28 攒利息段,等级 4(节点经验自然升至 4);本章随后进投资策略屏(节点型流程序),无义务动作缺席。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-3 战斗 画面-投资策略

#### 0 观察

- 策略刷新余量(strategy_refresh_left) {}

#### 策略依据

- mandate_v1:24(entry=decide_invest_strategy, op=CwActionPickInvestStrategyParam, reason=pick total=150 cash=0 dir=100 gift=50 stance=0 steer=0)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…

#### 策略评价
- **决策正确性**:合格——盛会之星星徽套组 total=150(cash0+dir100+gift50,遥测 dseq24)为三候选最高;黄金期货=期权族不计分(29_invest_strategy_screen.md §2.1 不计分通道,fail-closed 0),榜样的力量·银 无机械分。判定尺=29 §1 五项相加+§3 落地序(阵容冲突护栏基准=锁定线 factions;盛会之星∈列车 flex_factions,kernel/cw_comps.py:617,交集非空不排除)。
- **是否符合发展主线**:✓ 方向分来自 S 档列车线;盛会星徽=线内 flex 增益件。
- **备选与改进**:立场表全零(29 §2.4,用户裁定 2026-09-23)下无更强备选;帧内含帧级顶级卡(盛会套组=对齐保护)→帧级门拒刷(29 §4)合规。


### 节点 1-3 战斗 画面-备战

#### 0 观察

- 金(gold) 36
- 血(hp) 82
- 等级(level) 4
- 经验(xp) 0/6
- 连胜(streak) 0
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1
- 装备库存(equips) 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星、以太钻头、和平手枪
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七1★ | 空 | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 飞霄1★ | 三月七1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 乱破1★ | 爻光1★ |

#### 1 开店
- 策略依据: mandate_v1:25(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:25

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 投资策略候选(invest_strategy_opts) | 榜样的力量·银、盛会之星星徽套组、黄金期货 → 榜样的力量·银、盛会之星星徽套组、黄金期货 | (前值=累计快照) |
| 策略刷新余量(strategy_refresh_left) | {"榜样的力量·银":1,"盛会之星星徽套组":1,"黄金期货":1} → {"榜样的力量·银":1,"盛会之星星徽套组":1,"黄金期货":1} | (前值=累计快照) |
| 持卡(active_strategies) | 盛会之星星徽套组 → 盛会之星星徽套组 | (前值=累计快照) |

#### 策略评价
- **决策正确性**:合格(开店进店;金 36)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-3 战斗 画面-商店

#### 0 观察

- 金(gold) 36
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 4
- 概率(refresh_probs) 1→65%、2→25%、3→10%

**商店牌面(shop)**

| 槽 | 牌名 | 阵营 | 费用 | 星级 |
|---|---|---|---|---|
| 1 | 翡翠 | 公司 | 1 | 1★ |
| 2 | 万敌 | 夜之半神 | 1 | 1★ |
| 3 | 花火 | 盛会之星 | 2 | 1★ |
| 4 | 三月七 | 列车同行 | 1 | 1★ |
| 5 | 阿格莱雅 | 昼之半神 | 1 | 1★ |

#### 1 卖备战
- 策略依据: mandate_v1:26(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=1 income=1 expect=飞霄
  - dtag: mandate_v1:26

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 乱破1★、飞霄1★、三月七1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ → 乱破1★、三月七1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★(空×1) |  |
| 金(gold) | 36 → 37 |  |

#### 2 买牌 花火(2金)
- 策略依据: mandate_v1:27(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m2_line_member)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: 花火(盛会之星,2金,槽3) · char_id=花火 · reason=m2_line_member
  - dtag: mandate_v1:27

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 2]: 椒丘 → phase[1, 3]: 花火 |  |
| 金(gold) | 37 → 35 |  |
| 商店牌面(shop) | 翡翠1金、万敌1金、花火2金、三月七1金、阿格莱雅1金 → 翡翠1金、万敌1金、三月七1金、阿格莱雅1金(空×1) |  |
| 备战席(bench) | 乱破1★、三月七1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★(空×1) → 乱破1★、花火1★、三月七1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ |  |

#### 3 买牌 三月七(1金)
- 策略依据: mandate_v1:28(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m2_merge_completion)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: 三月七(列车同行,1金,槽4) · char_id=三月七 · reason=m2_merge_completion
  - dtag: mandate_v1:28

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 3]: 花火 → phase[1, 3]: 花火、三月七 |  |
| 金(gold) | 35 → 34 |  |
| 商店牌面(shop) | 翡翠1金、万敌1金、三月七1金、阿格莱雅1金(空×1) → 翡翠1金、万敌1金、阿格莱雅1金(空×2) |  |
| 备战席(bench) | 乱破1★、花火1★、三月七1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ → 乱破1★、花火1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★(空×1) |  |
| 上阵(deployed) | 前排 姬子·启行1★、砂金1★;后排 三月七1★ → 前排 姬子·启行1★、砂金1★;后排 三月七2★ |  |

#### 4 买牌 翡翠(1金)
- 策略依据: mandate_v1:29(entry=decide_shop_action, op=CwActionBuyCardParam, reason=scene_plugin_buy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: 翡翠(公司,1金,槽1) · char_id=翡翠 · reason=scene_plugin_buy
  - dtag: mandate_v1:29

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 3]: 花火、三月七 → phase[1, 3]: 花火、三月七、翡翠 |  |
| 金(gold) | 34 → 33 |  |
| 商店牌面(shop) | 翡翠1金、万敌1金、阿格莱雅1金(空×2) → 万敌1金、阿格莱雅1金(空×3) |  |
| 备战席(bench) | 乱破1★、花火1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★(空×1) → 乱破1★、花火1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ |  |

#### 5 收店
- 策略依据: mandate_v1:30(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:30

#### 策略评价
- **决策正确性**:合格——店内置换卖飞霄(+1)腾席;花火 2 金=m2_line_member(k_members 首副本,M2 免利息门,11_shop_decisions.md:23);三月七 1 金=m2_merge_completion(2/3 完成段,11 §2「2★ 决策现行覆盖」件①;合成 2★ 落场上位 L873);翡翠=scene_plugin(公司×1→×2)。金约束全程合规(11:21)。
- **是否符合发展主线**:✓ 三月七 2★=need_star(三月七)=2★ 达标(cw_comps.py:669),全局唯一线内升星。
- **备选与改进**:无——同帧三买均为义务/插件位,无更优备选。


### 节点 1-3 战斗 画面-备战

#### 0 观察

- 金(gold) 33
- 血(hp) 82
- 等级(level) 4
- 经验(xp) 0/6
- 连胜(streak) 0
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1
- 装备库存(equips) 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星、以太钻头、和平手枪
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 空 | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 花火1★ | 翡翠1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 乱破1★ | 爻光1★ |

#### 1 换位 部署槽2→back2 ✓(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:31(entry=decide_prep_screen, op=CwActionDeployMoveParam, route_tag=m1_deploy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=部署槽2→back2 ✓(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:31

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 乱破1★、花火1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ → 乱破1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★(空×1) |  |
| 上阵(deployed) | 前排 姬子·启行1★、砂金1★;后排 三月七2★ → 前排 姬子·启行1★、砂金1★;后排 三月七2★、花火1★ |  |
| 羁绊计数(board) | 列车同行×2、领航员×1、护盾×2、公司×1、追击×1 → 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1 |  |

#### 2 穿装备 穿戴 以太钻头 → 砂金(front-2) 已发(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:32(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=穿戴 以太钻头 → 砂金(front-2) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:32

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、以太钻头、幸运星、以太钻头、和平手枪 → 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、幸运星、以太钻头、和平手枪 |  |

#### 3 穿装备 穿戴 以太钻头 → 砂金(front-2) 已发(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:33(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=穿戴 以太钻头 → 砂金(front-2) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:33

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、幸运星、以太钻头、和平手枪 → 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、幸运星、和平手枪 |  |

#### 4 穿装备 穿戴 轮滑鞋 → 姬子·启行(front-1) 已发(发出即记账,落地归观察对账…
- 策略依据: mandate_v1:34(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=穿戴 轮滑鞋 → 姬子·启行(front-1) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:34

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 轮滑鞋、和平手枪、量产型装甲、轮滑鞋、幸运星、和平手枪 → 和平手枪、量产型装甲、轮滑鞋、幸运星、和平手枪 |  |

#### 5 穿装备 穿戴 轮滑鞋 → 姬子·启行(front-1) 已发(发出即记账,落地归观察对账…
- 策略依据: mandate_v1:35(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=穿戴 轮滑鞋 → 姬子·启行(front-1) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:35

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 和平手枪、量产型装甲、轮滑鞋、幸运星、和平手枪 → 和平手枪、量产型装甲、幸运星、和平手枪 |  |

#### 6 穿装备 穿戴 和平手枪 → 三月七(back-1) 已发(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:36(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=穿戴 和平手枪 → 三月七(back-1) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:36

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 和平手枪、量产型装甲、幸运星、和平手枪 → 量产型装甲、幸运星、和平手枪 |  |

#### 7 穿装备 穿戴 量产型装甲 → 三月七(back-1) 已发(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:37(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=穿戴 量产型装甲 → 三月七(back-1) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:37

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 量产型装甲、幸运星、和平手枪 → 幸运星、和平手枪 |  |

#### 8 穿装备 穿戴 幸运星 → 三月七(back-1) 已发(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:38(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=穿戴 幸运星 → 三月七(back-1) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:38

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 幸运星、和平手枪 → 和平手枪 |  |

#### 9 穿装备 穿戴 和平手枪 → 花火(back-2) 已发(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:39(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=穿戴 和平手枪 → 花火(back-2) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:39

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 和平手枪 → (空) |  |

#### 10 出战 出战已点击(无弹窗)
- 策略依据: mandate_v1:40(entry=decide_prep_screen, op=CwActionStartBattleParam, route_tag=battle)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=出战已点击(无弹窗) · 画面=货币战争-备战
  - dtag: mandate_v1:40
- 同值写入 ×8 略(前=后,零信息)

#### 策略评价
- **决策正确性**:部署花火 back2=线成员(M1)✓;穿戴 8 件链含一处**配对控制缺口**(缺陷候选 A2,详见复盘者附加):和平手枪→三月七(L1016)后量产型装甲→三月七(L1030)——两件简易同角色=穿着即合成(equipment_mechanics.md §1;§1.1 两两全配方),量产型装甲为自适应外骨骼组件(cw_comps.py:631 equip_assign)被烧入非目标合成对,违 10_prep_decisions.md §2 组件保留律[29]与 §2.1 门B。钻头×2→砂金(击破线件上非线单位)、轮滑鞋×2→姬子(反重力皮靴,C6 全队骨架件)合规。
- **是否符合发展主线**:✓ 部署/出战序合规;装备分配大向=线内 key 件方向。
- **备选与改进**:量产型装甲应留装备栏囤外骨骼对(本局仅 1 件,囤至第二件到货);穿戴序应先消耗非向量件、最后穿向量件。


### 节点 1-3 战斗 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★
- 后排(back_slots) 三月七2★、花火1★
- 敌方难度(enemy_difficulty) 114
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 1-3 战斗 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [1,3] → [1,4] |  |

## 节点 1-4 战斗

### 节点 1-4 战斗 画面-备战

#### 0 观察

- 金(gold) 33
- 血(hp) 82
- 等级(level) 4
- 经验(xp) 2/6
- 连胜(streak) 1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 空 | 翡翠1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 乱破1★ | 爻光1★ |

#### 1 开店
- 策略依据: mandate_v1:41(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:41

#### 策略评价
- **决策正确性**:合格(开店;金 33 攒利息段)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-4 战斗 画面-商店

#### 0 观察

- 金(gold) 42
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 4
- 概率(refresh_probs) 1→65%、2→25%、3→10%

**商店牌面(shop)**

| 槽 | 牌名 | 阵营 | 费用 | 星级 |
|---|---|---|---|---|
| 1 | 大丽花 | 盛会之星 | 1 | 1★ |
| 2 | 卡芙卡 | 星核猎手 | 2 | 1★ |
| 3 | 风堇 | 昼之半神 | 2 | 1★ |
| 4 | 乱破 | 巡海游侠 | 1 | 1★ |
| 5 | 赛飞儿 | 夜之半神 | 1 | 1★ |

#### 1 收店
- 策略依据: mandate_v1:42(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:42

#### 策略评价
- **决策正确性**:合格——金 42<g* 攒利息段;战斗帧死金臂不辖(shop.py:1419 奖励帧门);店内 1 金档均非义务/保护候选(乱破×2 已持、赛飞儿已持、大丽花=非保护盛会件)。docs/game/currency_war/research/economy.md §7 前中期共识=滚雪球到 50 金。
- **是否符合发展主线**:✓ 攒息正确姿态。
- **备选与改进**:大丽花 press 期权本帧不可达系判据域限定(非奖励帧),非缺陷。


### 节点 1-4 战斗 画面-备战

#### 0 观察

- 金(gold) 42
- 血(hp) 82
- 等级(level) 4
- 经验(xp) 2/6
- 连胜(streak) 1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 空 | 翡翠1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 乱破1★ | 爻光1★ |

#### 1 开店
- 策略依据: mandate_v1:43(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=step4_shop_session)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:43

#### 策略评价
- **决策正确性**:合格(店空重开即收)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-4 战斗 画面-商店

#### 0 观察

- 金(gold) 42
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 4

#### 1 收店
- 策略依据: mandate_v1:44(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:44

#### 策略评价
- **决策正确性**:合格(0 买收店;败态登记 pending_loss P1-R4=sim 随机战败,不归因策略——sim-testing.md:15)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-4 战斗 画面-备战

#### 0 观察

- 金(gold) 42
- 血(hp) 82
- 等级(level) 4
- 经验(xp) 2/6
- 连胜(streak) 1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股
- 败态登记(pending_loss) P1-R4 (battle)

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 空 | 翡翠1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 乱破1★ | 爻光1★ |

#### 1 出战 出战已点击(无弹窗)
- 策略依据: mandate_v1:45(entry=decide_prep_screen, op=CwActionStartBattleParam, route_tag=battle)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: detail=出战已点击(无弹窗) · 画面=货币战争-备战
  - dtag: mandate_v1:45

#### 策略评价
- **决策正确性**:合格(4/4 cap 满配出战)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-4 战斗 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★
- 后排(back_slots) 三月七2★、花火1★
- 敌方难度(enemy_difficulty) 114
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 1-4 战斗 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [1,4] → [1,5] |  |

## 节点 1-5 补给

### 节点 1-5 补给 画面-备战

#### 0 观察

- 金(gold) 42
- 血(hp) 38
- 等级(level) 4
- 经验(xp) 4/6
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 空 | 翡翠1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 乱破1★ | 爻光1★ |

#### 策略评价
- **决策正确性**:0 动作章——补给节点备战未开店,但金 42<g* 无 M6 义务,合规;无义务动作缺席。
- **是否符合发展主线**:✓。
- **备选与改进**:补给选卡缺席归下一章评(候选 A3)。


### 节点 1-5 补给 画面-补给

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 补给(supply) | 0: 以太钻头;1: 量产型装甲;2: 以太钻头(带钻标) → 0: 以太钻头;1: 量产型装甲;2: 以太钻头(带钻标) | (前值=累计快照) |
| 补给刷新余量(supply_refresh_left) | 1 → 1 | (前值=累计快照) |
| 节点序位(node_pos) | [1,5] → [1,6] |  |

#### 策略评价
- **决策正确性**:**应选未选**(候选 A3,sim 流程层):手牌 idx2=以太钻头(带钻标)——按 30_supply_screen.md §2 裁定①「带钻压过一切」应立即选;策略器未被调用(结构性机制见复盘者附加 A3【编排者更正】)。
- **是否符合发展主线**:缺席(带钻=人口位/星徽材料资产,30 §2 第 1 级依据)。
- **备选与改进**:【编排者更正 2026-10-28】兜底点卡**已发生**:journal v390/v391(CwActionPickSupplyOp 内容全未知翻来源写)+ v392(node_pos [1,5]→[1,6])= 盲点 CARD_BODY 兜底链走通、节点被消费;「无 PickSupply 回执」非动作缺席证据——该 op 全链路不调 note_action_receipt(回执写点仅备战/商店四处,实机同形态),渲染器动作节仅由回执行驱动。真实缺口 = 策略器结构性不可达(见 A3 更正);sim 流程层缺口,不立策略病灶。


## 节点 1-6 战斗

### 节点 1-6 战斗 画面-补给

#### 0 观察

- 补给刷新余量(supply_refresh_left) 1

#### 策略评价
- **决策正确性**:余量读数章无决策面;supply_refresh_left=1 随节点过期未用——选卡链缺席的连带面(同上章)。
- **是否符合发展主线**:—。
- **备选与改进**:同候选 A3 处置。


### 节点 1-6 战斗 画面-备战

#### 0 观察

- 金(gold) 61
- 血(hp) 38
- 等级(level) 4
- 经验(xp) 4/6
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 乱破1★ | 空 | 翡翠1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 乱破1★ | 爻光1★ |

#### 1 开店
- 策略依据: mandate_v1:46(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:46

#### 策略评价
- **决策正确性**:合格(开店,金 61>g*=50 进入富余段)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-6 战斗 画面-商店

#### 0 观察

- 金(gold) 61
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 4
- 概率(refresh_probs) 1→65%、2→25%、3→10%

**商店牌面(shop)**

| 槽 | 牌名 | 阵营 | 费用 | 星级 |
|---|---|---|---|---|
| 1 | 千冶·刃 | 星核猎手 | 2 | 1★ |
| 2 | 赛飞儿 | 夜之半神 | 1 | 1★ |
| 3 | 黑塔 | 银河学者 | 1 | 1★ |
| 4 | 真理医生 | 银河学者 | 3 | 1★ |
| 5 | 翡翠 | 公司 | 1 | 1★ |

#### 1 买牌 千冶·刃(2金)
- 策略依据: mandate_v1:47(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"ope…
- 动作: 画面=货币战争-备战-开商店
  - action: 千冶·刃(星核猎手,2金,槽1) · char_id=千冶·刃 · reason=m6_stockpile
  - dtag: mandate_v1:47

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 3]: 花火、三月七、翡翠 → phase[1, 6]: 千冶·刃 |  |
| 金(gold) | 61 → 59 |  |
| 商店牌面(shop) | 千冶·刃2金、赛飞儿1金、黑塔1金、真理医生3金、翡翠1金 → 赛飞儿1金、黑塔1金、真理医生3金、翡翠1金(空×1) |  |
| 备战席(bench) | 乱破1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★(空×1) → 乱破1★、千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ |  |

#### 2 卖备战
- 策略依据: mandate_v1:48(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"吉尔伽美什":{"open…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=0 income=1 expect=乱破
  - dtag: mandate_v1:48

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 乱破1★、千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ → 千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★(空×1) |  |
| 金(gold) | 59 → 60 |  |

#### 3 买牌 真理医生(3金)
- 策略依据: mandate_v1:49(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"吉尔伽美什":{"open…
- 动作: 画面=货币战争-备战-开商店
  - action: 真理医生(银河学者,3金,槽4) · char_id=真理医生 · reason=m6_stockpile
  - dtag: mandate_v1:49

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 6]: 千冶·刃 → phase[1, 6]: 千冶·刃、真理医生 |  |
| 金(gold) | 60 → 57 |  |
| 商店牌面(shop) | 赛飞儿1金、黑塔1金、真理医生3金、翡翠1金(空×1) → 赛飞儿1金、黑塔1金、翡翠1金(空×2) |  |
| 备战席(bench) | 千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★(空×1) → 真理医生1★、千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ |  |

#### 4 卖备战
- 策略依据: mandate_v1:50(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"乱破":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"吉尔伽美什":{"open…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=7 income=1 expect=乱破
  - dtag: mandate_v1:50

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 真理医生1★、千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、乱破1★、爻光1★ → 真理医生1★、千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、爻光1★(空×1) |  |
| 金(gold) | 57 → 58 |  |

#### 5 买牌 赛飞儿(1金)
- 策略依据: mandate_v1:51(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"o…
- 动作: 画面=货币战争-备战-开商店
  - action: 赛飞儿(夜之半神,1金,槽2) · char_id=赛飞儿 · reason=m6_stockpile
  - dtag: mandate_v1:51

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 6]: 千冶·刃、真理医生 → phase[1, 6]: 千冶·刃、真理医生、赛飞儿 |  |
| 金(gold) | 58 → 57 |  |
| 商店牌面(shop) | 赛飞儿1金、黑塔1金、翡翠1金(空×2) → 黑塔1金、翡翠1金(空×3) |  |
| 备战席(bench) | 真理医生1★、千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、爻光1★(空×1) → 真理医生1★、千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★ |  |

#### 6 收店
- 策略依据: mandate_v1:52(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"o…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:52

#### 策略评价
- **决策正确性**:合格——千冶·刃 2 金/真理医生 3 金/赛飞儿 1 金均 m6_stockpile(M6 富余处置义务,02_mandate_layer.md:46;P46 支出否决不适用=金>50 利息已饱和段);席满帧 shop_swap 卖乱破×2(置换账,11_shop_decisions.md §4.0)。
- **是否符合发展主线**:✓ 千冶·刃=多线通用之王(plaza_methodology M3:Early→Final 0.96/28 路线),买因质量高;真理医生=银河学者填充(transition_combos.md §学者路线副产品语义)。
- **备选与改进**:[41] 收窄(富金优先囤 S)不辖——升级授权零、无 S 预留(根链=缺陷候选 A1),本帧无违例。


### 节点 1-6 战斗 画面-备战

#### 0 观察

- 金(gold) 57
- 血(hp) 38
- 等级(level) 4
- 经验(xp) 4/6
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 真理医生1★ | 千冶·刃1★ | 翡翠1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 赛飞儿1★ | 爻光1★ |

#### 1 出战 出战已点击(无弹窗)
- 策略依据: mandate_v1:53(entry=decide_prep_screen, op=CwActionStartBattleParam, route_tag=battle)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"o…
- 动作: detail=出战已点击(无弹窗) · 画面=货币战争-备战
  - dtag: mandate_v1:53

#### 策略评价
- **决策正确性**:合格(board 4/4 cap4 满配出战)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-6 战斗 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★
- 后排(back_slots) 三月七2★、花火1★
- 敌方难度(enemy_difficulty) 114
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 1-6 战斗 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [1,6] → [1,7] |  |

## 节点 1-7 遭遇

### 节点 1-7 遭遇 画面-备战

#### 0 观察

- 金(gold) 57
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 0/20
- 连胜(streak) 1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 真理医生1★ | 千冶·刃1★ | 翡翠1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 赛飞儿1★ | 爻光1★ |

#### 策略评价
- **决策正确性**:0 动作章=申报点:金 57>g* 富余段未开店(M6 未获评估位;遭遇节点备战无开店帧,形态见完整性申报 2)。等级 5(自然经验)。
- **是否符合发展主线**:✓ 无实证偏离(M6 消费位=店内会话,未开店则未触发;非义务动作被跳过的实证不存在)。
- **备选与改进**:申报交编排者核节点型工序;若属策略器返回出战,则富余段压牌库在遭遇前帧缺位(候补观察项)。


### 节点 1-7 遭遇 画面-遭遇

#### 0 观察

(无)

#### 策略依据

- mandate_v1:54(entry=decide_encounter, op=CwActionPickEncounterParam, reason=e3-simple\|pick:t2\|kappa=边缘)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"o…

#### 策略评价
- **决策正确性**:合格——pick:t2|kappa=边缘(窗口=1-4 败+1-6 胜→恰一胜=边缘,31_encounter_screen.md §2.2;边缘态 cap 过滤后最高可及=t2,§2.3/§2.4 主序)。判定尺=31 篇判据+04_survival_budget.md §7 #9 授权的结算观测输入。
- **是否符合发展主线**:中性——遭遇=高危节点(combat.md §3),t2=进度达标制下保底口径。
- **备选与改进**:combat.md §3 载明「未成型期选高难刮最低进度」为攻略认可收益——现行立场值直选结构(EDGE_CAP)已在册待实机重拍(31 §1 裁定 3),非本局新增缺陷。


### 节点 1-7 遭遇 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★
- 后排(back_slots) 三月七2★、花火1★
- 敌方难度(enemy_difficulty) 114
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 1-7 遭遇 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 遭遇(encounter) | 0: ?;1: ?;2: ?;3: ? → 0: ?;1: ?;2: ?;3: ? | (前值=累计快照) |
| 已选(encounter) | [2,"金+20(占位,encounter_tier_params_pending_u22)"] → [2,"金+20(占位,encounter_tier_params_pending_u22)"] | (前值=累计快照) |
| 节点序位(node_pos) | [1,7] → [1,8] |  |

## 节点 1-8 奖励

### 节点 1-8 奖励 画面-遭遇

#### 0 观察

(无)

#### 策略评价
- 过渡显影帧(0 观察),无决策动作面,三槽不适用。


### 节点 1-8 奖励 画面-备战

#### 0 观察

- 金(gold) 80
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 2/20
- 连胜(streak) 2
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 8 座(金×1,蓝×1,灰×1)
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 真理医生1★ | 千冶·刃1★ | 翡翠1★ | 吉尔伽美什1★ | 赛飞儿1★ | 翡翠1★ | 椒丘1★ | 赛飞儿1★ | 爻光1★ |

#### 1 卖备战 卖备战槽4 ✓
- 策略依据: mandate_v1:55(entry=decide_prep_screen, op=CwActionSellBenchParam, reason=ore_make_room, route_tag=ore_make_room_sell)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"吉尔伽美什":{"open":false,"sig":null},"姬子·启行":{"o…
- 动作: detail=卖备战槽4 ✓ · 画面=货币战争-备战
  - dtag: mandate_v1:55

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿奖励(ore_rewards) | (空) → 10,10=金+2;20,10=角色 ?;30,10=装备 折叠小刀;40,10=角色 ?;50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 |  |
| 备战席(bench) | 真理医生1★、千冶·刃1★、翡翠1★、吉尔伽美什1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★ → 真理医生1★、千冶·刃1★、翡翠1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★(空×1) |  |
| 金(gold) | 80 → 82 |  |

#### 2 采晶矿 采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:56(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"椒…
- 动作: detail=采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:56

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿(spheres) | 8 座(金×1,蓝×1,灰×1) → 7 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 10,10=金+2;20,10=角色 ?;30,10=装备 折叠小刀;40,10=角色 ?;50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 → 20,10=角色 ?;30,10=装备 折叠小刀;40,10=角色 ?;50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 |  |
| 金(gold) | 82 → 84 |  |
| 晶矿(spheres) | 7 座(蓝×1,灰×1) → 6 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 20,10=角色 ?;30,10=装备 折叠小刀;40,10=角色 ?;50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 → 30,10=装备 折叠小刀;40,10=角色 ?;50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 |  |
| 备战席(bench) | 真理医生1★、千冶·刃1★、翡翠1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★(空×1) → 真理医生1★、千冶·刃1★、翡翠1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★ |  |

#### 3 卖备战 卖备战槽1 ✓
- 策略依据: mandate_v1:57(entry=decide_prep_screen, op=CwActionSellBenchParam, reason=ore_make_room, route_tag=ore_make_room_sell)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"椒…
- 动作: detail=卖备战槽1 ✓ · 画面=货币战争-备战
  - dtag: mandate_v1:57

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 真理医生1★、千冶·刃1★、翡翠1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★ → 千冶·刃1★、翡翠1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★(空×1) |  |
| 金(gold) | 84 → 87 |  |

#### 4 采晶矿 采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:58(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"椒…
- 动作: detail=采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:58

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿(spheres) | 6 座(蓝×1,灰×1) → 5 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 30,10=装备 折叠小刀;40,10=角色 ?;50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 → 40,10=角色 ?;50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 |  |
| 装备库存(equips) | (空) → 折叠小刀 |  |
| 晶矿(spheres) | 5 座(蓝×1,灰×1) → 4 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 40,10=角色 ?;50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 → 50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 |  |
| 备战席(bench) | 千冶·刃1★、翡翠1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★(空×1) → 忘归人1★、千冶·刃1★、翡翠1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★ |  |

#### 5 开店
- 策略依据: mandate_v1:59(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:59

#### 策略评价
- **决策正确性**:合格——卖吉尔伽美什/真理医生=ore_make_room 晶矿腾位(垫件谓词过滤,11_shop_decisions.md §4.0 场景表;均为非线 1★ 垫件);8 矿全采。
- **是否符合发展主线**:✓ 腾位对象资格合规(非保护集非义务面)。
- **备选与改进**:无。


### 节点 1-8 奖励 画面-商店

#### 0 观察

- 金(gold) 87
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 5
- 概率(refresh_probs) 1→45%、2→33%、3→20%、4→2%

**商店牌面(shop)**

| 槽 | 牌名 | 阵营 | 费用 | 星级 |
|---|---|---|---|---|
| 1 | 真理医生 | 银河学者 | 3 | 1★ |
| 2 | 风堇 | 昼之半神 | 2 | 1★ |
| 3 | 黑塔 | 银河学者 | 1 | 1★ |
| 4 | 黄泉 | 巡海游侠 | 3 | 1★ |
| 5 | 绯英 | 星间旅人 | 2 | 1★ |

#### 1 卖备战
- 策略依据: mandate_v1:60(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=2 income=1 expect=翡翠
  - dtag: mandate_v1:60

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、翡翠1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★ → 忘归人1★、千冶·刃1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★(空×1) |  |
| 金(gold) | 87 → 88 |  |

#### 2 买牌 黄泉(3金)
- 策略依据: mandate_v1:61(entry=decide_shop_action, op=CwActionBuyCardParam, reason=scene_plugin_buy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 黄泉(巡海游侠,3金,槽4) · char_id=黄泉 · reason=scene_plugin_buy
  - dtag: mandate_v1:61

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 6]: 千冶·刃、真理医生、赛飞儿 → phase[1, 8]: 黄泉 |  |
| 金(gold) | 88 → 85 |  |
| 商店牌面(shop) | 真理医生3金、风堇2金、黑塔1金、黄泉3金、绯英2金 → 真理医生3金、风堇2金、黑塔1金、绯英2金(空×1) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★(空×1) → 忘归人1★、千冶·刃1★、黄泉1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★ |  |

#### 3 卖备战
- 策略依据: mandate_v1:62(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=5 income=1 expect=翡翠
  - dtag: mandate_v1:62

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、黄泉1★、停云1★、赛飞儿1★、翡翠1★、椒丘1★、赛飞儿1★、爻光1★ → 忘归人1★、千冶·刃1★、黄泉1★、停云1★、赛飞儿1★、椒丘1★、赛飞儿1★、爻光1★(空×1) |  |
| 金(gold) | 85 → 86 |  |

#### 4 买牌 风堇(2金)
- 策略依据: mandate_v1:63(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 风堇(昼之半神,2金,槽2) · char_id=风堇 · reason=m6_stockpile
  - dtag: mandate_v1:63

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 8]: 黄泉 → phase[1, 8]: 黄泉、风堇 |  |
| 金(gold) | 86 → 84 |  |
| 商店牌面(shop) | 真理医生3金、风堇2金、黑塔1金、绯英2金(空×1) → 真理医生3金、黑塔1金、绯英2金(空×2) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、黄泉1★、停云1★、赛飞儿1★、椒丘1★、赛飞儿1★、爻光1★(空×1) → 忘归人1★、千冶·刃1★、黄泉1★、停云1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★ |  |

#### 5 收店
- 策略依据: mandate_v1:64(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:64

#### 策略评价
- **决策正确性**:合格——卖翡翠×2(shop_swap 腾席)+黄泉 3 金=scene_plugin(减益×1 边际)+风堇 2 金=m6_stockpile(金 86-84>50 富余段)。
- **是否符合发展主线**:中性偏正——黄泉=黄泉减益线核心(多线期权);减益2=列车 B 流注册 sub_tiers 方向(cw_comps.py:630)。
- **备选与改进**:无。


### 节点 1-8 奖励 画面-备战

#### 0 观察

- 金(gold) 84
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 2/20
- 连胜(streak) 2
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1
- 装备库存(equips) 折叠小刀
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 4 座(蓝×1,灰×1)
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 黄泉1★ | 停云1★ | 赛飞儿1★ | 风堇1★ | 椒丘1★ | 赛飞儿1★ | 爻光1★ |

#### 1 换位 部署槽3→front3 ✓(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:65(entry=decide_prep_screen, op=CwActionDeployMoveParam, route_tag=m1_deploy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: detail=部署槽3→front3 ✓(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:65

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、黄泉1★、停云1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★ → 忘归人1★、千冶·刃1★、停云1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★(空×1) |  |
| 上阵(deployed) | 前排 姬子·启行1★、砂金1★;后排 三月七2★、花火1★ → 前排 姬子·启行1★、砂金1★、黄泉1★;后排 三月七2★、花火1★ |  |
| 羁绊计数(board) | 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1 → 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1 |  |

#### 2 采晶矿 采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:66(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: detail=采晶矿 3 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:66

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿(spheres) | 4 座(蓝×1,灰×1) → 3 座(蓝×1,灰×1) |  |
| 晶矿奖励(ore_rewards) | 50,10=装备 幸运星;60,10=金+1;70,10=金+4;80,10=装备 和平手枪 → 60,10=金+1;70,10=金+4;80,10=装备 和平手枪 |  |
| 装备库存(equips) | 折叠小刀 → 折叠小刀、幸运星 |  |
| 晶矿(spheres) | 3 座(蓝×1,灰×1) → 2 座(灰×1) |  |
| 晶矿奖励(ore_rewards) | 60,10=金+1;70,10=金+4;80,10=装备 和平手枪 → 70,10=金+4;80,10=装备 和平手枪 |  |
| 金(gold) | 84 → 85 |  |
| 晶矿(spheres) | 2 座(灰×1) → 1 座(灰×1) |  |
| 晶矿奖励(ore_rewards) | 70,10=金+4;80,10=装备 和平手枪 → 80,10=装备 和平手枪 |  |
| 金(gold) | 85 → 89 |  |

#### 3 采晶矿 采晶矿 1 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补)
- 策略依据: mandate_v1:67(entry=decide_prep_screen, op=CwActionCollectOreParam, route_tag=prep_spheres)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: detail=采晶矿 1 个(载荷机械点;动画等待 2s,晶矿未消由下一帧观察回补) · 画面=货币战争-备战
  - dtag: mandate_v1:67

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 晶矿(spheres) | 1 座(灰×1) → 0 座 |  |
| 晶矿奖励(ore_rewards) | 80,10=装备 和平手枪 → (空) |  |
| 装备库存(equips) | 折叠小刀、幸运星 → 折叠小刀、幸运星、和平手枪 |  |

#### 4 开店
- 策略依据: mandate_v1:68(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:68

#### 策略评价
- **决策正确性**:合格——黄泉 front3 部署(场况插件,会话额度 5−4=1>0,11_shop_decisions.md:15 序 2);采矿 4+1;开店。
- **是否符合发展主线**:✓ 减益×1 上板为 B 流方向件。
- **备选与改进**:无。


### 节点 1-8 奖励 画面-商店

#### 0 观察

- 金(gold) 89
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 5

#### 1 收店
- 策略依据: mandate_v1:69(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:69

#### 策略评价
- **决策正确性**:合格(店余 2 张非候选,收店)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-8 奖励 画面-备战

#### 0 观察

- 金(gold) 89
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 2/20
- 连胜(streak) 2
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) 折叠小刀、幸运星、和平手枪
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 空 | 停云1★ | 赛飞儿1★ | 风堇1★ | 椒丘1★ | 赛飞儿1★ | 爻光1★ |

#### 1 开店
- 策略依据: mandate_v1:70(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=step4_shop_session)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:70

#### 策略评价
- **决策正确性**:合格(开店,金 89 富余段)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 1-8 奖励 画面-商店

#### 0 观察

- 金(gold) 89
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 5

#### 1 买牌 绯英(2金)
- 策略依据: mandate_v1:71(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 绯英(星间旅人,2金,槽5) · char_id=绯英 · reason=m6_stockpile
  - dtag: mandate_v1:71

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 8]: 黄泉、风堇 → phase[1, 8]: 黄泉、风堇、绯英 |  |
| 金(gold) | 89 → 87 |  |
| 商店牌面(shop) | 真理医生3金、黑塔1金、绯英2金(空×2) → 真理医生3金、黑塔1金(空×3) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、停云1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★(空×1) → 忘归人1★、千冶·刃1★、绯英1★、停云1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★ |  |

#### 2 收店
- 策略依据: mandate_v1:72(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:72

#### 策略评价
- **决策正确性**:合格——绯英 2 金=m6_stockpile(富余段压牌库)。
- **是否符合发展主线**:中性——星间旅人线核心 1★=多线保险期权(plaza M3 多线通用语义)。
- **备选与改进**:无。


### 节点 1-8 奖励 画面-备战

#### 0 观察

- 金(gold) 87
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 2/20
- 连胜(streak) 2
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) 折叠小刀、幸运星、和平手枪
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 绯英1★ | 停云1★ | 赛飞儿1★ | 风堇1★ | 椒丘1★ | 赛飞儿1★ | 爻光1★ |

#### 1 穿装备 穿戴 折叠小刀 → 姬子·启行(front-1) 已发(发出即记账,落地归观察对…
- 策略依据: mandate_v1:73(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: detail=穿戴 折叠小刀 → 姬子·启行(front-1) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:73

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 折叠小刀、幸运星、和平手枪 → 幸运星、和平手枪 |  |

#### 2 穿装备 穿戴 幸运星 → 三月七(back-1) 已发(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:74(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: detail=穿戴 幸运星 → 三月七(back-1) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:74

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 幸运星、和平手枪 → 和平手枪 |  |

#### 3 穿装备 穿戴 和平手枪 → 花火(back-2) 已发(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:75(entry=decide_prep_screen, op=CwActionWearEquipParam, route_tag=m7_equip_transfer)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: detail=穿戴 和平手枪 → 花火(back-2) 已发(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:75

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 装备库存(equips) | 和平手枪 → (空) |  |

#### 4 出战 出战已点击(无弹窗)
- 策略依据: mandate_v1:76(entry=decide_prep_screen, op=CwActionStartBattleParam, route_tag=battle)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: detail=出战已点击(无弹窗) · 画面=货币战争-备战
  - dtag: mandate_v1:76
- 同值写入 ×3 略(前=后,零信息)

#### 策略评价
- **决策正确性**:合格——折叠小刀→姬子·启行(高周波电锯组件,=列车 equip_assign 姬子项 cw_comps.py:631;economy.md §8 概念股送件对照);幸运星→三月七、和平手枪→花火=单件过渡穿着,未新增非目标合成对。
- **是否符合发展主线**:✓ M7 装备转移常态(02_mandate_layer.md:47)。
- **备选与改进**:无。


### 节点 1-8 奖励 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★、黄泉1★
- 后排(back_slots) 三月七2★、花火1★
- 敌方难度(enemy_difficulty) 114
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 1-8 奖励 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [1,8] → [1,9] |  |

## 节点 1-9 BOSS

### 节点 1-9 BOSS 画面-备战

#### 0 观察

- 金(gold) 87
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 4/20
- 连胜(streak) 2
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 绯英1★ | 停云1★ | 赛飞儿1★ | 风堇1★ | 椒丘1★ | 赛飞儿1★ | 爻光1★ |

#### 策略评价
- **决策正确性**:0 动作出战——P1 辖域禁升级(11_shop_decisions.md §2 阶段保护,2026-10-18 用户裁定)∧板满∧无装备余量,判据内合法。**申报面**:金 87 富余段未开店,M6 未获评估位(见完整性申报 2-②);M5「1-9 boss 前升 6/7」(plaza_methodology M5 关键窗)被 P1 升级辖域禁令覆盖——判据如此,非违例,登记观察。
- **是否符合发展主线**:✓ 过渡形态满 cap 出战 boss。
- **备选与改进**:若放开 boss 帧开店可 m6 press 补强——现行判据无此位,不改判。


### 节点 1-9 BOSS 画面-BOSS简报

#### 0 观察

- 位面首领(plane_bosses) ["巨鹿生物制药","智识实验室","深穹智械科技"]
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]
- 选择难度(selected_difficulty) A8

### 节点 1-9 BOSS 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★、黄泉1★
- 后排(back_slots) 三月七2★、花火1★
- 敌方难度(enemy_difficulty) 114
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 1-9 BOSS 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [1,9] → [2,1] |  |

## 节点 2-1 战斗

### 节点 2-1 战斗 画面-BOSS简报

#### 0 观察

- 位面首领(plane_bosses) ["巨鹿生物制药","智识实验室","深穹智械科技"]
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]
- 选择难度(selected_difficulty) A8

### 节点 2-1 战斗 画面-位面转场

#### 0 观察

- 节点序列(node_seq_by_plane) {"1":["reward","reward","battle","battle","supply","battle","encounter","reward"…
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 2-1 战斗 画面-备战

#### 0 观察

- 金(gold) 111
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 16/20
- 连胜(streak) 3
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 绯英1★ | 停云1★ | 赛飞儿1★ | 风堇1★ | 椒丘1★ | 赛飞儿1★ | 爻光1★ |

#### 1 开店
- 策略依据: mandate_v1:77(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:77

#### 策略评价
- **决策正确性**:合格(开店,金 111;连胜 3)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 2-1 战斗 画面-商店

#### 0 观察

- 金(gold) 111
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 5
- 概率(refresh_probs) 1→45%、2→33%、3→20%、4→2%

**商店牌面(shop)**

| 槽 | 牌名 | 阵营 | 费用 | 星级 |
|---|---|---|---|---|
| 1 | 赛飞儿 | 夜之半神 | 1 | 1★ |
| 2 | 缇宝 | 昼之半神 | 2 | 1★ |
| 3 | 艾丝妲 | 银河学者 | 1 | 1★ |
| 4 | 黑塔 | 银河学者 | 1 | 1★ |
| 5 | 万敌 | 夜之半神 | 1 | 1★ |

#### 1 卖备战
- 策略依据: mandate_v1:78(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=3 income=1 expect=停云
  - dtag: mandate_v1:78

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、绯英1★、停云1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★ → 忘归人1★、千冶·刃1★、绯英1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★(空×1) |  |
| 金(gold) | 111 → 112 |  |

#### 2 买牌 缇宝(2金)
- 策略依据: mandate_v1:79(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 缇宝(昼之半神,2金,槽2) · char_id=缇宝 · reason=m6_stockpile
  - dtag: mandate_v1:79

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[1, 8]: 黄泉、风堇、绯英 → phase[2, 1]: 缇宝 |  |
| 金(gold) | 112 → 110 |  |
| 商店牌面(shop) | 赛飞儿1金、缇宝2金、艾丝妲1金、黑塔1金、万敌1金 → 赛飞儿1金、艾丝妲1金、黑塔1金、万敌1金(空×1) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、绯英1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★(空×1) → 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★ |  |

#### 3 卖备战
- 策略依据: mandate_v1:80(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=8 income=1 expect=爻光
  - dtag: mandate_v1:80

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★、爻光1★ → 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★(空×1) |  |
| 金(gold) | 110 → 111 |  |

#### 4 买牌 赛飞儿(1金)
- 策略依据: mandate_v1:81(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 赛飞儿(夜之半神,1金,槽1) · char_id=赛飞儿 · reason=m6_stockpile
  - dtag: mandate_v1:81

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 1]: 缇宝 → phase[2, 1]: 缇宝、赛飞儿 |  |
| 金(gold) | 111 → 110 |  |
| 商店牌面(shop) | 赛飞儿1金、艾丝妲1金、黑塔1金、万敌1金(空×1) → 艾丝妲1金、黑塔1金、万敌1金(空×2) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿1★、风堇1★、椒丘1★、赛飞儿1★(空×1) → 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★(空×2) |  |

#### 5 买牌 艾丝妲(1金)
- 策略依据: mandate_v1:82(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 艾丝妲(银河学者,1金,槽3) · char_id=艾丝妲 · reason=m6_stockpile
  - dtag: mandate_v1:82

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 1]: 缇宝、赛飞儿 → phase[2, 1]: 缇宝、赛飞儿、艾丝妲 |  |
| 金(gold) | 110 → 109 |  |
| 商店牌面(shop) | 艾丝妲1金、黑塔1金、万敌1金(空×2) → 黑塔1金、万敌1金(空×3) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★(空×2) → 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★(空×1) |  |

#### 6 买牌 黑塔(1金)
- 策略依据: mandate_v1:83(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 黑塔(银河学者,1金,槽4) · char_id=黑塔 · reason=m6_stockpile
  - dtag: mandate_v1:83

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 1]: 缇宝、赛飞儿、艾丝妲 → phase[2, 1]: 缇宝、赛飞儿、艾丝妲、黑塔 |  |
| 金(gold) | 109 → 108 |  |
| 商店牌面(shop) | 黑塔1金、万敌1金(空×3) → 万敌1金(空×4) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★(空×1) → 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、黑塔1★ |  |

#### 7 收店
- 策略依据: mandate_v1:84(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:84

#### 策略评价
- **决策正确性**:合格——m6_stockpile 链(富余段):缇宝 2 金/赛飞儿 1 金(第二副本合成 2★,L2422)/艾丝妲/黑塔;shop_swap 卖停云/爻光腾席。
- **是否符合发展主线**:中性——P2 转型期买入全为非线内件(线缺件=瓦尔特/姬子 2★3★/花火 2★,未进店);M6 本义=活期资产,合规。
- **备选与改进**:缺陷候选 A1 根链在此显形:升级授权零→无 S 整批预留→富金全走 press;判据内无违例。


### 节点 2-1 战斗 画面-备战

#### 0 观察

- 金(gold) 108
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 16/20
- 连胜(streak) 3
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 绯英1★ | 缇宝1★ | 赛飞儿2★ | 风堇1★ | 椒丘1★ | 艾丝妲1★ | 黑塔1★ |

#### 1 出战 出战已点击(无弹窗)
- 策略依据: mandate_v1:85(entry=decide_prep_screen, op=CwActionStartBattleParam, route_tag=battle)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: detail=出战已点击(无弹窗) · 画面=货币战争-备战
  - dtag: mandate_v1:85

#### 策略评价
- **决策正确性**:合格(出战)。
- **是否符合发展主线**:⚠ hp 38≤p2_crisis_stop_hp=41(cw_discipline_rules.py:212-232)——自此全部 P2 备战帧入危机带,M3 升级全拦(缺陷候选 A1 前提面;hp 掉落本身=sim 随机结算不归因,sim-testing.md:15)。
- **备选与改进**:无(危机带内判据如此)。


### 节点 2-1 战斗 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★、黄泉1★
- 后排(back_slots) 三月七2★、花火1★
- 敌方难度(enemy_difficulty) 114
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 2-1 战斗 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [2,1] → [2,2] |  |

## 节点 2-2 战斗

### 节点 2-2 战斗 画面-备战

#### 0 观察

- 金(gold) 108
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 18/20
- 连胜(streak) 4
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 绯英1★ | 缇宝1★ | 赛飞儿2★ | 风堇1★ | 椒丘1★ | 艾丝妲1★ | 黑塔1★ |

#### 策略评价
- **决策正确性**:合格(0 动作;经验 18/20)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 2-2 战斗 画面-投资策略

#### 0 观察

- 策略刷新余量(strategy_refresh_left) {"榜样的力量·银":1,"盛会之星星徽套组":1,"黄金期货":1}

#### 策略依据

- mandate_v1:86(entry=decide_invest_strategy, op=CwActionRefreshInvestCardsParam, reason=refresh: 帧级门过,可刷槽 3/3)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 同值写入 ×1 略(前=后,零信息)

#### 策略评价
- **决策正确性**:合格——帧级门过(候选恰 3/全精确分类/无帧级顶级卡/锁定帧 max_N≠1,29 §4)建议刷新;执行换牌后经 decide_pick 选溜佩佩(total=9 cash=9,遥测 dseq88,归属缺口见完整性申报 1)。
- **是否符合发展主线**:中性——经济小卡,危机带前帧。
- **备选与改进**:无(刷新后候选域即此)。


### 节点 2-2 战斗 画面-备战

#### 0 观察

- 金(gold) 120
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 18/20
- 连胜(streak) 4
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 绯英1★ | 缇宝1★ | 赛飞儿2★ | 风堇1★ | 椒丘1★ | 艾丝妲1★ | 黑塔1★ |

#### 1 开店
- 策略依据: mandate_v1:89(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:89

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 投资策略候选(invest_strategy_opts) | (起点) → 无伤通关、全武行、二费援军 |  |
| 策略刷新余量(strategy_refresh_left) | {"榜样的力量·银":1,"盛会之星星徽套组":1,"黄金期货":1} → {"榜样的力量·银":1,"盛会之星星徽套组":1,"黄金期货":1,"无伤通关":1,"全武行":1,"二费援军":1… |  |
| 投资策略候选(invest_strategy_opts) | 无伤通关、全武行、二费援军 → 溜佩佩、成本控制、回收计划 |  |
| 持卡(active_strategies) | 盛会之星星徽套组 → 盛会之星星徽套组、溜佩佩 |  |

#### 策略评价
- **决策正确性**:合格(开店,金 120;持卡「盛会之星星徽套组、溜佩佩」显影)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 2-2 战斗 画面-商店

#### 0 观察

- 金(gold) 120
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 5
- 概率(refresh_probs) 1→45%、2→33%、3→20%、4→2%

**商店牌面(shop)**

| 槽 | 牌名 | 阵营 | 费用 | 星级 |
|---|---|---|---|---|
| 1 | 三月七 | 列车同行 | 1 | 1★ |
| 2 | 砂金 | 公司 | 2 | 1★ |
| 3 | 银枝 | 星间旅人 | 2 | 1★ |
| 4 | 遐蝶 | 夜之半神 | 4 | 1★ |
| 5 | 飞霄 | 狼狩 | 1 | 1★ |

#### 1 卖备战
- 策略依据: mandate_v1:90(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=8 income=1 expect=黑塔
  - dtag: mandate_v1:90

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、黑塔1★ → 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★(空×1) |  |
| 金(gold) | 120 → 121 |  |

#### 2 买牌 砂金(2金)
- 策略依据: mandate_v1:91(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 砂金(公司,2金,槽2) · char_id=砂金 · reason=m6_stockpile
  - dtag: mandate_v1:91

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 1]: 缇宝、赛飞儿、艾丝妲、黑塔 → phase[2, 2]: 砂金 |  |
| 金(gold) | 121 → 119 |  |
| 商店牌面(shop) | 三月七1金、砂金2金、银枝2金、遐蝶4金、飞霄1金 → 三月七1金、银枝2金、遐蝶4金、飞霄1金(空×1) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★(空×1) → 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★ |  |

#### 3 卖备战
- 策略依据: mandate_v1:92(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=2 income=2 expect=绯英
  - dtag: mandate_v1:92

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、绯英1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★ → 忘归人1★、千冶·刃1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★(空×1) |  |
| 金(gold) | 119 → 121 |  |

#### 4 买牌 银枝(2金)
- 策略依据: mandate_v1:93(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 银枝(星间旅人,2金,槽3) · char_id=银枝 · reason=m6_stockpile
  - dtag: mandate_v1:93

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 2]: 砂金 → phase[2, 2]: 砂金、银枝 |  |
| 金(gold) | 121 → 119 |  |
| 商店牌面(shop) | 三月七1金、银枝2金、遐蝶4金、飞霄1金(空×1) → 三月七1金、遐蝶4金、飞霄1金(空×2) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★(空×1) → 忘归人1★、千冶·刃1★、银枝1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★ |  |

#### 5 卖备战
- 策略依据: mandate_v1:94(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=3 income=2 expect=缇宝
  - dtag: mandate_v1:94

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、银枝1★、缇宝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★ → 忘归人1★、千冶·刃1★、银枝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★(空×1) |  |
| 金(gold) | 119 → 121 |  |

#### 6 买牌 飞霄(1金)
- 策略依据: mandate_v1:95(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 飞霄(狼狩,1金,槽5) · char_id=飞霄 · reason=m6_stockpile
  - dtag: mandate_v1:95

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 2]: 砂金、银枝 → phase[2, 2]: 砂金、银枝、飞霄 |  |
| 金(gold) | 121 → 120 |  |
| 商店牌面(shop) | 三月七1金、遐蝶4金、飞霄1金(空×2) → 三月七1金、遐蝶4金(空×3) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、银枝1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★(空×1) → 忘归人1★、千冶·刃1★、银枝1★、飞霄1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★ |  |

#### 7 卖备战
- 策略依据: mandate_v1:96(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=5 income=2 expect=风堇
  - dtag: mandate_v1:96

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、银枝1★、飞霄1★、赛飞儿2★、风堇1★、椒丘1★、艾丝妲1★、砂金1★ → 忘归人1★、千冶·刃1★、银枝1★、飞霄1★、赛飞儿2★、椒丘1★、艾丝妲1★、砂金1★(空×1) |  |
| 金(gold) | 120 → 122 |  |

#### 8 收店
- 策略依据: mandate_v1:97(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:97

#### 策略评价
- **决策正确性**:合格——m6_stockpile 链(砂金/银枝/飞霄)+shop_swap 卖黑塔/绯英/缇宝/风堇;金 120-122 富余段。
- **是否符合发展主线**:中性(同节点 2-1 章:M6 本义合规,转型件未进店)。
- **备选与改进**:无。


### 节点 2-2 战斗 画面-备战

#### 0 观察

- 金(gold) 122
- 血(hp) 38
- 等级(level) 5
- 经验(xp) 18/20
- 连胜(streak) 4
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股
- hp_floor_triggered 是
- 败态登记(pending_loss) P2-R2 (battle)

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 银枝1★ | 飞霄1★ | 赛飞儿2★ | 空 | 椒丘1★ | 艾丝妲1★ | 砂金1★ |

#### 1 出战 出战已点击(无弹窗)
- 策略依据: mandate_v1:98(entry=decide_prep_screen, op=CwActionStartBattleParam, route_tag=battle)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: detail=出战已点击(无弹窗) · 画面=货币战争-备战
  - dtag: mandate_v1:98

#### 策略评价
- **决策正确性**:合格(出战)。
- **是否符合发展主线**:⚠ **hp_floor_triggered=是**(L2811)=sim 战斗保底事件位(cw_game_state.py:2954 写点注释「纯观察登记,无判据载体」;cw_sim_battle.py:20「保底剩 1」机制)——P2r2 战败 38→1 触发游戏侧保底,**非策略解锁信号**,不构成支出授权变化;hp=1 起全程危机带(M3 全拦,候选 A1)。
- **备选与改进**:危机带帧「转化优先」通道未实现(04_survival_budget.md §7 #3)——本帧起 4 个备战帧金位 122→142 滞留(见 A1)。


### 节点 2-2 战斗 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★、黄泉1★
- 后排(back_slots) 三月七2★、花火1★
- 敌方难度(enemy_difficulty) 114
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 2-2 战斗 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [2,2] → [2,3] |  |

## 节点 2-3 补给

### 节点 2-3 补给 画面-备战

#### 0 观察

- 金(gold) 122
- 血(hp) 1
- 等级(level) 6
- 经验(xp) 0/40
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 银枝1★ | 飞霄1★ | 赛飞儿2★ | 空 | 椒丘1★ | 艾丝妲1★ | 砂金1★ |

#### 策略评价
- **决策正确性**:0 动作章=申报点(金 122/hp1;同节点 1-7 章申报面,见完整性申报 2-②)。
- **是否符合发展主线**:⚠ 危机带帧富金滞留(候选 A1)。
- **备选与改进**:同 A1。


### 节点 2-3 补给 画面-补给

#### 0 观察

- 补给刷新余量(supply_refresh_left) 1

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 补给(supply) | (起点) → 0: 以太钻头;1: 折叠小刀;2: 以太钻头(带钻标) |  |
| 节点序位(node_pos) | [2,3] → [2,4] |  |

#### 策略评价
- **决策正确性**:**应选未选**(同候选 A3):手牌含 以太钻头(带钻标)未选,策略器未被调用;兜底盲点卡已发生(见 A3【编排者更正】),「无 PickSupply 回执」= 渲染口径非缺席证据。
- **是否符合发展主线**:缺席。
- **备选与改进**:同候选 A3 处置。


## 节点 2-4 战斗

### 节点 2-4 战斗 画面-补给

#### 0 观察

- 补给刷新余量(supply_refresh_left) 1

#### 策略评价
- 余量读数章,无决策面。


### 节点 2-4 战斗 画面-备战

#### 0 观察

- 金(gold) 142
- 血(hp) 1
- 等级(level) 6
- 经验(xp) 0/40
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 忘归人1★ | 千冶·刃1★ | 银枝1★ | 飞霄1★ | 赛飞儿2★ | 空 | 椒丘1★ | 艾丝妲1★ | 砂金1★ |

#### 1 开店
- 策略依据: mandate_v1:99(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:99

#### 策略评价
- **决策正确性**:合格(开店,金 142=危机带富余峰值)。
- **是否符合发展主线**:⚠ 同候选 A1 前提面。
- **备选与改进**:无。


### 节点 2-4 战斗 画面-商店

#### 0 观察

- 金(gold) 142
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 6
- 概率(refresh_probs) 1→30%、2→40%、3→25%、4→5%

**商店牌面(shop)**

| 槽 | 牌名 | 阵营 | 费用 | 星级 |
|---|---|---|---|---|
| 1 | 千冶·刃 | 星核猎手 | 2 | 1★ |
| 2 | 星期日 | 盛会之星 | 3 | 1★ |
| 3 | 卡芙卡 | 星核猎手 | 2 | 1★ |
| 4 | 丹恒·饮月 | 仙舟 | 2 | 1★ |
| 5 | 乱破 | 巡海游侠 | 1 | 1★ |

#### 1 买牌 千冶·刃(2金)
- 策略依据: mandate_v1:100(entry=decide_shop_action, op=CwActionBuyCardParam, reason=scene_plugin_buy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 千冶·刃(星核猎手,2金,槽1) · char_id=千冶·刃 · reason=scene_plugin_buy
  - dtag: mandate_v1:100

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 2]: 砂金、银枝、飞霄 → phase[2, 4]: 千冶·刃 |  |
| 金(gold) | 142 → 140 |  |
| 商店牌面(shop) | 千冶·刃2金、星期日3金、卡芙卡2金、丹恒·饮月2金、乱破1金 → 星期日3金、卡芙卡2金、丹恒·饮月2金、乱破1金(空×1) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、银枝1★、飞霄1★、赛飞儿2★、椒丘1★、艾丝妲1★、砂金1★(空×1) → 忘归人1★、千冶·刃1★、银枝1★、飞霄1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★ |  |

#### 2 卖备战
- 策略依据: mandate_v1:101(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=2 income=2 expect=银枝
  - dtag: mandate_v1:101

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、银枝1★、飞霄1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★ → 忘归人1★、千冶·刃1★、飞霄1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★(空×1) |  |
| 金(gold) | 140 → 142 |  |

#### 3 买牌 星期日(3金)
- 策略依据: mandate_v1:102(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 星期日(盛会之星,3金,槽2) · char_id=星期日 · reason=m6_stockpile
  - dtag: mandate_v1:102

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 4]: 千冶·刃 → phase[2, 4]: 千冶·刃、星期日 |  |
| 金(gold) | 142 → 139 |  |
| 商店牌面(shop) | 星期日3金、卡芙卡2金、丹恒·饮月2金、乱破1金(空×1) → 卡芙卡2金、丹恒·饮月2金、乱破1金(空×2) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、飞霄1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★(空×1) → 忘归人1★、千冶·刃1★、星期日1★、飞霄1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★ |  |

#### 4 CwActionRefreshShopParam
- 策略依据: mandate_v1:103(entry=decide_shop_action, op=CwActionRefreshShopParam, reason=star_target)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=star_target · cost=2
  - dtag: mandate_v1:103

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 商店牌面(shop) | 卡芙卡2金、丹恒·饮月2金、乱破1金(空×2) → 白厄3金、刻律德菈3金、万敌1金、海瑟音4金、白厄3金 |  |
| 金(gold) | 139 → 137 |  |

#### 5 卖备战
- 策略依据: mandate_v1:104(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=3 income=1 expect=飞霄
  - dtag: mandate_v1:104

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、星期日1★、飞霄1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★ → 忘归人1★、千冶·刃1★、星期日1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★(空×1) |  |
| 金(gold) | 137 → 138 |  |

#### 6 买牌 刻律德菈(3金)
- 策略依据: mandate_v1:105(entry=decide_shop_action, op=CwActionBuyCardParam, reason=scene_plugin_buy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"open":false,"sig":["synergy",4]},"忘…
- 动作: 画面=货币战争-备战-开商店
  - action: 刻律德菈(夜之半神,3金,槽2) · char_id=刻律德菈 · reason=scene_plugin_buy
  - dtag: mandate_v1:105

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 4]: 千冶·刃、星期日 → phase[2, 4]: 千冶·刃、星期日、刻律德菈 |  |
| 金(gold) | 138 → 135 |  |
| 商店牌面(shop) | 白厄3金、刻律德菈3金、万敌1金、海瑟音4金、白厄3金 → 白厄3金、万敌1金、海瑟音4金、白厄3金(空×1) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、星期日1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★(空×1) → 忘归人1★、千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★ |  |

#### 7 卖备战
- 策略依据: mandate_v1:106(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"op…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=7 income=1 expect=艾丝妲
  - dtag: mandate_v1:106

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、艾丝妲1★、砂金1★ → 忘归人1★、千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、砂金1★(空×1) |  |
| 金(gold) | 135 → 136 |  |

#### 8 买牌 白厄(3金)
- 策略依据: mandate_v1:107(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"op…
- 动作: 画面=货币战争-备战-开商店
  - action: 白厄(散,3金,槽1) · char_id=白厄 · reason=m6_stockpile
  - dtag: mandate_v1:107

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 4]: 千冶·刃、星期日、刻律德菈 → phase[2, 4]: 千冶·刃、星期日、刻律德菈、白厄 |  |
| 金(gold) | 136 → 133 |  |
| 商店牌面(shop) | 白厄3金、万敌1金、海瑟音4金、白厄3金(空×1) → 万敌1金、海瑟音4金、白厄3金(空×2) |  |
| 备战席(bench) | 忘归人1★、千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、砂金1★(空×1) → 忘归人1★、千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★ |  |

#### 9 卖备战
- 策略依据: mandate_v1:108(entry=decide_shop_action, op=CwActionSellBenchParam, reason=shop_swap)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"op…
- 动作: 画面=货币战争-备战-开商店
  - action: reason=shop_swap · bench_idx=0 income=3 expect=忘归人
  - dtag: mandate_v1:108

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 忘归人1★、千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★ → 千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★(空×1) |  |
| 金(gold) | 133 → 136 |  |

#### 10 买牌 白厄(3金)
- 策略依据: mandate_v1:109(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"op…
- 动作: 画面=货币战争-备战-开商店
  - action: 白厄(散,3金,槽5) · char_id=白厄 · reason=m6_stockpile
  - dtag: mandate_v1:109

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 金(gold) | 136 → 133 |  |
| 商店牌面(shop) | 万敌1金、海瑟音4金、白厄3金(空×2) → 万敌1金、海瑟音4金(空×3) |  |
| 备战席(bench) | 千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★(空×1) → 白厄1★、千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★ |  |

#### 11 收店
- 策略依据: mandate_v1:110(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"op…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:110

#### 策略评价
- **决策正确性**:合规但暴露危机段出口单一(候选 A1 行为面):千冶·刃 2 金=scene_plugin(→同章部署 back3 ✓ 战力转化)、星期日 3 金=m6_stockpile(→部署 back4 ✓);刻律德菈/白厄×2/万敌=m6_stockpile 囤 bench;付费刷新 1 次=star_target(停留目标花火 2 费带[6,7]∧等级 6∈带→停留刷新,11_shop_decisions.md §3 分派 2 合规;refresh_probs 2→40% 峰值互证 L2975)。
- **是否符合发展主线**:部分✓——两次部署为 P2 唯一战力转化;另 5 张 1★ 终局未消费(终态 bench 9/9 非线件)。
- **备选与改进**:hp=1 帧按 04 §7 #3 解锁包语义应「转化优先」——解锁包未实现,现行唯一出口=M6 press;本帧=候选 A1 实证样本。


### 节点 2-4 战斗 画面-备战

#### 0 观察

- 金(gold) 133
- 血(hp) 1
- 等级(level) 6
- 经验(xp) 0/40
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 空 | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 白厄1★ | 千冶·刃1★ | 星期日1★ | 刻律德菈1★ | 赛飞儿2★ | 千冶·刃1★ | 椒丘1★ | 白厄1★ | 砂金1★ |

#### 1 换位 部署槽2→back3 ✓(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:111(entry=decide_prep_screen, op=CwActionDeployMoveParam, route_tag=m1_deploy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"op…
- 动作: detail=部署槽2→back3 ✓(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:111

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 白厄1★、千冶·刃1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★ → 白厄1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★(空×1) |  |
| 上阵(deployed) | 前排 姬子·启行1★、砂金1★、黄泉1★;后排 三月七2★、花火1★ → 前排 姬子·启行1★、砂金1★、黄泉1★;后排 三月七2★、花火1★、千冶·刃1★ |  |
| 羁绊计数(board) | 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×1 → 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×2、星核猎手×1、燃血×1 |  |

#### 2 开店
- 策略依据: mandate_v1:112(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=step4_shop_session)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"op…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:112

#### 策略评价
- **决策正确性**:合格(千冶·刃 back3 部署=场景插件位;星核猎手×1+燃血×1 上板;开店)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 2-4 战斗 画面-商店

#### 0 观察

- 金(gold) 133
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 6

#### 1 买牌 万敌(1金)
- 策略依据: mandate_v1:113(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open":false,"sig":null},"姬子·启行":{"op…
- 动作: 画面=货币战争-备战-开商店
  - action: 万敌(夜之半神,1金,槽3) · char_id=万敌 · reason=m6_stockpile
  - dtag: mandate_v1:113

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 4]: 千冶·刃、星期日、刻律德菈、白厄 → phase[2, 4]: 千冶·刃、星期日、刻律德菈、白厄、万敌 |  |
| 金(gold) | 133 → 132 |  |
| 商店牌面(shop) | 万敌1金、海瑟音4金(空×3) → 海瑟音4金(空×4) |  |
| 备战席(bench) | 白厄1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★(空×1) → 白厄1★、万敌1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★ |  |

#### 2 收店
- 策略依据: mandate_v1:114(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:114

#### 策略评价
- **决策正确性**:合格(万敌 1 金 m6_stockpile;收店)。
- **是否符合发展主线**:中性。
- **备选与改进**:无。


### 节点 2-4 战斗 画面-备战

#### 0 观察

- 金(gold) 132
- 血(hp) 1
- 等级(level) 6
- 经验(xp) 0/40
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×2、星核猎手×1、燃血×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 黄泉1★ | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 千冶·刃1★ | 空 | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 白厄1★ | 万敌1★ | 星期日1★ | 刻律德菈1★ | 赛飞儿2★ | 千冶·刃1★ | 椒丘1★ | 白厄1★ | 砂金1★ |

#### 1 CwActionSellDeployedParam 卖front排3 ✓
- 策略依据: mandate_v1:115(entry=decide_prep_screen, op=CwActionSellDeployedParam, route_tag=m1_swap_redeploy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…
- 动作: detail=卖front排3 ✓ · 画面=货币战争-备战
  - dtag: mandate_v1:115

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 上阵(deployed) | 前排 姬子·启行1★、砂金1★、黄泉1★;后排 三月七2★、花火1★、千冶·刃1★ → 前排 姬子·启行1★、砂金1★;后排 三月七2★、花火1★、千冶·刃1★ |  |
| 羁绊计数(board) | 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、巡海游侠×1、减益×2、星核猎手×1、燃血×1 → 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、减益×1、星核猎手×1、燃血×1 |  |
| 金(gold) | 132 → 135 |  |

#### 2 换位 部署槽3→back4 ✓(发出即记账,落地归观察对账)
- 策略依据: mandate_v1:116(entry=decide_prep_screen, op=CwActionDeployMoveParam, route_tag=m1_deploy)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…
- 动作: detail=部署槽3→back4 ✓(发出即记账,落地归观察对账) · 画面=货币战争-备战
  - dtag: mandate_v1:116

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 备战席(bench) | 白厄1★、万敌1★、星期日1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★ → 白厄1★、万敌1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★(空×1) |  |
| 上阵(deployed) | 前排 姬子·启行1★、砂金1★;后排 三月七2★、花火1★、千冶·刃1★ → 前排 姬子·启行1★、砂金1★;后排 三月七2★、花火1★、千冶·刃1★、星期日1★ |  |
| 羁绊计数(board) | 列车同行×2、领航员×1、护盾×2、公司×1、追击×1、盛会之星×1、战技点×1、量子同频×1、减益×1、星核猎手×1、燃血×1 → 列车同行×3、领航员×1、护盾×2、公司×1、追击×1、盛会之星×2、战技点×1、量子同频×1、减益×1、星核猎手×1、燃血×1、能量×1 |  |

#### 策略评价
- **决策正确性**:合格且质量高——卖黄泉 front3(m1_swap_redeploy,M4 姊妹出口/转型域双门,24_deploy_segment.md §1.1)+星期日 back4 部署(盛会×2、列车×3、能量×1):羁绊档两处升档(列车×2→×3),6/6 cap 满配。
- **是否符合发展主线**:✓ 列车×3 向 form_tiers=4 推进——全局唯一一次羁绊档位升级行为。
- **备选与改进**:黄泉 3 金回收=让位序合规(非线 1★)。


### 节点 2-4 战斗 画面-巨星

#### 0 观察

(无)

#### 策略依据

- mandate_v1:117(entry=decide_megastar, op=CwActionPickMegastarParam, reason=select_megastar 命中 花火)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…

#### 策略评价
- **决策正确性**:合格——select_megastar 命中花火(遥测 dseq117);花火=k_members+need_star 2★ 未达(现役追星对象),与线一致。
- **是否符合发展主线**:✓ 备选星期日=线 flex 插件,花火优先合规。
- **备选与改进**:无。


### 节点 2-4 战斗 画面-备战

#### 0 观察

- 金(gold) 135
- 血(hp) 1
- 等级(level) 6
- 经验(xp) 0/40
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×3、领航员×1、护盾×2、公司×1、追击×1、盛会之星×2、战技点×1、量子同频×1、减益×1、星核猎手×1、燃血×1、能量×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 千冶·刃1★ | 星期日1★ | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 白厄1★ | 万敌1★ | 空 | 刻律德菈1★ | 赛飞儿2★ | 千冶·刃1★ | 椒丘1★ | 白厄1★ | 砂金1★ |

#### 1 开店
- 策略依据: mandate_v1:118(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=shop_gold_read)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:118

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 巨星候选(megastar_opts) | {'idx': 0, 'char_id': '花火', 'xy': [10, 10]}、{'idx': 1, 'char_id': '星期日', 'xy': [20, 10]} → {'idx': 0, 'char_id': '花火', 'xy': [10, 10]}、{'idx': 1, 'char_id': '星期日', 'xy': [20, 10]} | (前值=累计快照) |
| 已选(megastar) | 花火 → 花火 | (前值=累计快照) |

#### 策略评价
- **决策正确性**:合格(开店;巨星选项/已选显影)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 2-4 战斗 画面-商店

#### 0 观察

- 金(gold) 135
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 6

#### 1 收店
- 策略依据: mandate_v1:119(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:119

#### 策略评价
- **决策正确性**:合格(店空收店)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 2-4 战斗 画面-备战

#### 0 观察

- 金(gold) 135
- 血(hp) 1
- 等级(level) 6
- 经验(xp) 0/40
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×3、领航员×1、护盾×2、公司×1、追击×1、盛会之星×2、战技点×1、量子同频×1、减益×1、星核猎手×1、燃血×1、能量×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 千冶·刃1★ | 星期日1★ | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 白厄1★ | 万敌1★ | 空 | 刻律德菈1★ | 赛飞儿2★ | 千冶·刃1★ | 椒丘1★ | 白厄1★ | 砂金1★ |

#### 1 开店
- 策略依据: mandate_v1:120(entry=decide_prep_screen, op=CwActionOpenShopParam, route_tag=step4_shop_session)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…
- 动作: 画面=货币战争-备战
  - dtag: mandate_v1:120

#### 策略评价
- **决策正确性**:合格(开店)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 2-4 战斗 画面-商店

#### 0 观察

- 金(gold) 135
- 商店刷新价(shop_refresh_cost) 2
- 等级(level) 6

#### 1 买牌 海瑟音(4金)
- 策略依据: mandate_v1:121(entry=decide_shop_action, op=CwActionBuyCardParam, reason=m6_stockpile)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…
- 动作: 画面=货币战争-备战-开商店
  - action: 海瑟音(昼之半神,4金,槽4) · char_id=海瑟音 · reason=m6_stockpile
  - dtag: mandate_v1:121

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 本轮新买(round_fresh_buys) | phase[2, 4]: 千冶·刃、星期日、刻律德菈、白厄、万敌 → phase[2, 4]: 千冶·刃、星期日、刻律德菈、白厄、万敌、海瑟音 |  |
| 金(gold) | 135 → 131 |  |
| 商店牌面(shop) | 海瑟音4金(空×4) → (无内容)(空×5) |  |
| 备战席(bench) | 白厄1★、万敌1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★(空×1) → 白厄1★、万敌1★、海瑟音1★、刻律德菈1★、赛飞儿2★、千冶·刃1★、椒丘1★、白厄1★、砂金1★ |  |

#### 2 收店
- 策略依据: mandate_v1:122(entry=decide_shop_action, op=CwActionCloseShopParam)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…
- 动作: 画面=货币战争-备战-开商店
  - dtag: mandate_v1:122

#### 策略评价
- **决策正确性**:合规但同候选 A1 行为面——海瑟音 4 金=m6_stockpile 入 bench(全局最贵买笔;危机带帧金 135→131,无转化授权通道)。
- **是否符合发展主线**:中性(昼之半神线核心 1★ 期权)。
- **备选与改进**:同候选 A1。


### 节点 2-4 战斗 画面-备战

#### 0 观察

- 金(gold) 131
- 血(hp) 1
- 等级(level) 6
- 经验(xp) 0/40
- 连胜(streak) -1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×3、领航员×1、护盾×2、公司×1、追击×1、盛会之星×2、战技点×1、量子同频×1、减益×1、星核猎手×1、燃血×1、能量×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 千冶·刃1★ | 星期日1★ | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 白厄1★ | 万敌1★ | 海瑟音1★ | 刻律德菈1★ | 赛飞儿2★ | 千冶·刃1★ | 椒丘1★ | 白厄1★ | 砂金1★ |

#### 1 出战 出战已点击(无弹窗)
- 策略依据: mandate_v1:123(entry=decide_prep_screen, op=CwActionStartBattleParam, route_tag=battle)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…
- 动作: detail=出战已点击(无弹窗) · 画面=货币战争-备战
  - dtag: mandate_v1:123

#### 策略评价
- **决策正确性**:合格(6/6 cap 满配出战)。
- **是否符合发展主线**:✓。
- **备选与改进**:无。


### 节点 2-4 战斗 画面-战斗

#### 0 观察

- 前排(front_slots) 姬子·启行1★、砂金1★
- 后排(back_slots) 三月七2★、花火1★、千冶·刃1★、星期日1★
- 敌方难度(enemy_difficulty) 114
- 敌方词缀(enemy_affixes) ["灼热轰炸","低费审美","正当防卫"]

### 节点 2-4 战斗 画面-对局收口

#### 0 观察

(无)

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 节点序位(node_pos) | [2,4] → [2,5] |  |

## 节点 2-5 遭遇

### 节点 2-5 遭遇 画面-备战

#### 0 观察

- 金(gold) 131
- 血(hp) 1
- 等级(level) 6
- 经验(xp) 2/40
- 连胜(streak) 1
- 后台格数(back_layout) 6
- 羁绊计数(board) 列车同行×3、领航员×1、护盾×2、公司×1、追击×1、盛会之星×2、战技点×1、量子同频×1、减益×1、星核猎手×1、燃血×1、能量×1
- 装备库存(equips) (空)
- 穿戴(occupied_equips) {}
- 晶矿(spheres) 0 座
- 溢出警告(overflow_warning) 否
- 持卡(active_strategies) 盛会之星星徽套组、溜佩佩
- 投资环境(active_env) 列车同行概念股

**上阵(deployed)**

| 排 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 前排 | 姬子·启行1★ | 砂金1★ | 空 | 空 | — | — |
| 后排 | 三月七2★ | 花火1★ | 千冶·刃1★ | 星期日1★ | 空 | 空 |

**备战席(bench)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| 白厄1★ | 万敌1★ | 海瑟音1★ | 刻律德菈1★ | 赛飞儿2★ | 千冶·刃1★ | 椒丘1★ | 白厄1★ | 砂金1★ |

#### 策略评价
- **决策正确性**:0 动作章=申报点:金 131/hp1 危机帧无开店无动作直出遭遇(同节点 1-7/1-9 申报面,见完整性申报 2-②;危机带支出通道缺位=候选 A1)。
- **是否符合发展主线**:⚠ 危机带富金滞留至死局前最后一帧。
- **备选与改进**:同候选 A1。


### 节点 2-5 遭遇 画面-遭遇

#### 0 观察

(无)

#### 策略依据

- mandate_v1:124(entry=decide_encounter, op=CwActionPickEncounterParam, reason=e3-simple\|pick:t2\|kappa=边缘)
  - payload:
    - direction: {"locked":true,"comp":"列车同行","candidates":[]}
    - k_members: ["姬子·启行","三月七","花火","瓦尔特"]
    - k_fallback: {"hit":false,"band":""}
    - window: {"万敌":{"open":false,"sig":null},"三月七":{"open":false,"sig":["synergy",4]},"刻律德菈":{"open":false,"sig":null},"千冶·刃":{"open"…

#### 章内变化

| 字段 | 前 → 后 | 说明 |
|---|---|---|
| 终局(match_final) | abnormal hp — 金 142 → abnormal hp — 金 142 | (效果钩子) (前值=累计快照) |
| 遭遇(encounter) | (起点) → 0: ?;1: ?;2: ?;3: ? |  |

#### 策略评价
- **决策正确性**:合格——pick:t2|kappa=边缘(窗口=2-1 胜+2-2 败→边缘,31 §2.2);本节点战败即局终(death),结算=sim 随机面不归因策略(sim-testing.md:15)。
- **是否符合发展主线**:终局 abnormal(位面 2 未出)。
- **备选与改进**:hp=1 下档位选择不影响 sim 结算面,无改进语义。


## 复盘者附加

## 产出一 · 算法缺陷候选清单(按严重度;单局=候选,跨局/sim 复测才定案)

### A1(高)危机带(hp≤41)全域拦截下策略无任何支出/转化出口,富金滞留至死局
- **证据链(当帧数据)**:cw4_counters `levelup_trigger_stay_gate=17` 全部被 `levelup_crisis_defer=17` 拦截、`levelup_reward_node_defer=27`、`levelup_fund_line_defer=0`、`levelup_trigger_natural=0`(对局档案 `endgame.match_final.final.cw4_counters`,局 g_20261028_011013)——P2 全部备战帧 hp≤38≤p2_crisis_stop_hp=41(cw_discipline_rules.py:212-232),M3 升级被 P21 全域拦;金轨迹 108→122→142→131 滞留(报告 节点 2-1/2-2/2-4/2-5 备战章 0 观察,L2297/L2544/L2928/L3173/L3576);板面战力 P2 期仅 2-4 增 2 个 1★(L3213/L3328),终态 bench 9/9 非线件;`hp_floor_triggered=是`(L2811)经写点核实=sim 战斗保底事件位「纯观察登记,无判据载体」(cw_game_state.py:2954),非策略解锁信号。
- **判定尺出处**:economy.md §6/§7(:62-87,A8「血危险锁血急救→花光提质量」社区多源共识=玩法文档面)+ 04_survival_budget.md §7 #3(血线硬地板解锁包三件=转化优先/凑息禁令/M3 解锁至饱和线下——用户 2026-09-01 已条件确认,未实现)+ §7 #4(停刷新数值/支出降格/终止分支确认前不写入代码)+ §7 #7 缺口披露(「其余血位无即时反应机制,设计明示接受,无替代码」)。
- **sim 边界切割**:hp 掉 38/1=sim 随机战斗不归因(sim-testing.md:15);缺陷面=危机带 11 个备战帧的支出决策面全部缺位(策略器侧无出口可走),与战斗结算面无关。
- **修复任务指向**:04 §7 #3/#4 危机带确认批(已登记确认通道;本局为该缺口实证样本,新候选标记=「危局带确认批实证样本 g_20261028_011013」)。

### A2(低-中)穿戴序未做「两件简易不共角色」配对控制,key 组件被烧入非目标合成对
- **证据链(当帧数据)**:报告 节点 1-3 备战 ####6/####7(L1009/L1023):和平手枪→三月七、量产型装甲→三月七 同角色连穿——穿着即合成(equipment_mechanics.md §1 两件简易同角色自动合成;§1.1 8 基础件两两 28/28 全配方);量产型装甲=自适应外骨骼组件(列车 equip_assign 三月七=自适应外骨骼,cw_comps.py:631),合成产物必非 key 需求向量;该章 8 件全穿、装备库存清零(L1113 节点 1-4 equips=(空)),零组件保留。
- **判定尺出处**:10_prep_decisions.md §2(组件保留律[29]:意向锁定即留材料;合成规划=key_equips 反推需求向量)+ §2.1 门B(被操作装备在不在目标需求向量里)。
- **边界**:sim 不建模装备效果(10 §2.1.9),损失面为机制账(P1→P2 装备转移价值);新候选标记,候单帧测试/实机复测定案。

### A3(申报级)补给屏带钻选项未选(1-5/2-3 两节点)——策略决策链未接线,sim 流程层缺口【编排者更正 2026-10-28】
- **证据链(当帧数据)**:journal.jsonl v384/v388(1-5 supply options 含「以太钻头(带钻标)」)→ **v390/v391(CwActionPickSupplyOp:bench/equips 内容全未知翻来源写)+ v392(node_pos [1,5]→[1,6])= 兜底盲点卡(CARD_BODY 固定点,idx=0 零内容载荷)已发生、节点被消费**;带钻选项(idx2)未获评估即被丢弃,内容 fail-closed 禁猜不入账(pick_supply.py:92-105 内容全未知分支)。报告「无 PickSupply 回执」非动作缺席证据:CwActionPickSupplyOp 全链路不调 note_action_receipt(回执写点 = 备战/开商店/关商店/商店买牌四处,补给选卡 op 不在其列,实机同形态),渲染器动作节仅由回执行驱动。
- **未接线机制(代码锚)**:决策门槛挂 op 实例载体 `_sup_opts`(每列选项+点击点),唯一写点 = 实机 OCR 读链 `_observe_live`(cw_screen_supply_node.py:247);sim 观察腿在 :210 经 `sim_or_live_observation` 改道后端生成器产物(只落容器、不回填实例载体),:304 门槛 `opts` 非空不成立 → decide_supply 结构性不可达 → 恒走兜底 = 30_supply_screen.md §6 申报形态,本局与之吻合。
- **判定尺出处**:30_supply_screen.md §2 裁定①(带钻压过一切)+ §6 sim 盲区申报;sim 流程层缺口,非策略器决策,不立策略病灶。
- **修复任务指向**:30 §6 两前置(sim 决策链接线生效+占位分布换真实池,已登记交接项)。

## 产出二 · 回灌判据读数(局 id=g_20261028_011013)

- **①buys**:BuyCard 回执 28 笔(锚=报告各商店章买牌节:L205/223/241、L340、L603、L838/856/875、L1436/1470/1504、L1836/1870/2072、L2372/2406/2424/2442、L2679/2713/2747、L2987/3021/3071/3105/3139、L3237、L3474);花金分布=1金×13/2金×8/3金×6/4金×1,总 51 金;另付费刷新 1 次 2 金(L3047)。买因分布=m2_line_member×2、m2_merge_completion×1、scene_plugin_buy×4、dead_gold_press_buy×3、m6_stockpile×18(对照 cw4_counters:dead_gold_press_buy_hit=3 吻合;scene_plugin_buy_hit=5 与回执 4 差 1,±1 观察项见完整性申报 4)。
- **②2★/3★ 到手与到位轮次**:3★=0;2★×2——三月七 2★@P1r3(锚=节点 1-3 商店 ####3 m2_merge_completion,gold 35→34,L857-873;到位=同帧部署入 1-3 出战板);赛飞儿 2★@P2r1(锚=节点 2-1 商店 ####4,gold 111→110,L2406-2422;到位轮次=无,终局留 bench)。线内核心星级推进:姬子·启行(need 3★)/花火(need 2★)全程 1★,瓦尔特(need 1★)全程未到手(cw_comps.py:666-670)。
- **③hp 均值与区间(单局只记值)**:82(开局~P1r3)→38(P1r4 战败,单轮 −44)→38(P1r5~P2r1)→1(P2r2 战败,单轮 −37,触发游戏 hp 保底)→1(P2r3~P2r4)→0(P2r5,death);区间 [0,82]。锚=各备战章 0 观察 hp 行+败态登记(L1260/L2812)。⚠ sim hp 未校准,只作记录不作 A/B 判据(sim-testing.md:16)。
- **④刷新带**:商店付费刷新 1 次@P2r4(reason=star_target,cost=2,锚=L3039-3053);P1 付费刷新 0 次(cw4_counters shop_refresh_p1_no_refresh=9,P1 各商店章零刷新动作节);投资策略屏刷新建议 2 帧@2-2(dseq86/87)执行 1 次换牌;补给刷新余量 1×2 节点未用(L1356/L2901);环境刷新余量 1 未用(L67)。

## 产出三 · 位面三问总答

1. **位面 1 过渡阵容顺利凑出?是**——列车2(姬子·启行+三月七2★)1-1 内点亮,护盾2/减益/黄泉/砂金/花火 填充,P1r4 大掉血(−44)为 sim 随机结算不归因策略,P1r5~r9 连胜至 boss(hp 38 进 P2)。
2. **位面 2 转型成功?否**——锁定线「列车同行」成型方向零推进:列车同行 board 计数全程 ×2(2-4 才 ×3,L3329),瓦尔特全程未到手,姬子/花火停 1★;危机带(hp≤41)全域拦 M3×17 帧,富金 108→142 滞留,转型预算失配(位面 1 末板面结构决定位面 2 成本,11_shop_decisions.md §5)。
3. **位面 3 最终阵容顺利凑出?未达**——死于 P2r5(终局 abnormal),未进入位面 3。

## 产出四 · 完整性申报

1. **策略遥测未归属 3 条处置**(dseq 1/87/88,经报告 dtag 全集与遥测 124 条差集核定):
   - dseq1(decide_invest_env,选列车同行概念股,total=144):决策已落地(active_env 生效,journal v56),缺口=开局投资环境章无回执关联(装配面);判读已并入该章策略评价,不影响结论。
   - dseq87(2-2 投资策略第二次刷新建议,同帧同因):29 §4 同帧去重 memo 协议的「再调恢复首调建议」形态,非缺陷;渲染装配缺席。
   - dseq88(2-2 选溜佩佩,total=9 cash=9):决策已落地(持卡 L2639 显影),回执关联缺口;判读已并入 2-2 投资策略章策略评价。
2. **应有动作整章缺席**:①1-5/2-3 补给屏策略选卡(带钻在场)未发生——sim 补给决策链未接线(30 §6 已申报盲区;【编排者更正】兜底盲点卡已发生,journal v390-v392,缺口 = 策略器结构性不可达,交编排者核 sim 流程层);②遭遇(1-7/2-5)/BOSS(1-9)节点备战章无开店动作(战斗/奖励节点均有),金 57/87/131 富余段 M6 未获评估位——形态待核(流程层节点型工序 or 策略器返回出战),申报不判病灶;③开局投资环境章策略依据块缺席(同 dseq1 装配缺口)。
3. **渲染器缺口注记处置**:局头「数据完整性: 无」,报告无未归节/未归行清单、章尾无缺口注记——渲染器面零缺口;本节第 2 条为复盘者自查补充申报。
4. **键语义核对声明(红线义务)**:hp_floor_triggered 判读经写点核实(cw_game_state.py:2954「纯观察登记,无判据载体」)=sim 战斗保底事件位,非血线地板解锁信号;dead_gold_press_buy 触发域经 shop.py:1419 核实(奖励帧∧gold<g*);upgrade_trigger P1 辖域禁升级经 criteria/levelup.py:269 核实——三键均按写点语义判读,无误读立案。scene_plugin_buy_hit=5 与回执 4 的 ±1 差异未立案(计数点在 emit,回执渲染面可能有同帧合并,候跨局对照)。


---

# 快照四：CW 修复工作清单（裁定载体；源 = .debug/temp/2026-10-28_CW修复工作清单.md）

# CW 修复工作清单（2026-10-28 起草）

> **迭代设计已立项**：`docs/develop/sr_od/application/currency_war/changes/2026-10-28-hp-purge-refresh-reform/`（design.md + 三详设 + landing.md，状态 = 草案）。本清单此后为裁定与挂账台账，执行以迭代文档为准；已进迭代的项（W1-W5、W8、W10、W11）在迭代内追踪，未进迭代的挂账项（W6/W7/W9）留本清单。

> 本轮调查收口后的总工作清单。修「危机带/金滞留」问题时按此执行，完成后逐项勾销。
> 实证局：g_20261028_011013（sim，seed=20260118，死亡@P2r5，金 142 滞留至死）
> 调查产物三件：hp 逻辑清查 = `.debug/temp/2026-10-28_hp逻辑清查.md`；支出链追查 = `.debug/temp/2026-10-28_P2金滞留支出链追查.md`；单局复盘 = `.debug/currency_war/deep_review/g_20261028_011013.md`

## 用户裁定（工作依据，照录）

1. **2026-10-28（hp 出策略）**：「只要我们策略是正确的，hp 自然是没问题可以通关的，所以策略侧不应该考虑 hp」——hp 是对局结果不是决策输入，策略判据里的 hp 全部删除。
2. **2026-10-28（商店搜牌模型追认）**：锁定终局阵容后，缺件角色存在「当前等级 = 其刷新概率峰值级」时停留刷新、买够再升级——即现行「最优概率带三分派」设计，方向正确，破在执行层。
3. **2026-10-28（删除纪律）**：「这次我们改了之后，相关的历史代码、注释、文档的相关的内容，都要删除掉，不要留废弃的内容影响以后判断」——删除是唯一处置形态。
4. **2026-10-28（危机不变式删除裁定）**：「要删除危机不变式以及对应的数学证明 P36-a」——判据函数与命题本体、单篇证明全删。
5. **2026-10-28（刷新预算整级预留腿删除）**：「策略先判断是否停留当前等级刷新；判断了停留，就没有给升级预留的必要」——刷新预算里「升级凑金时叠加整级批」的腿删除。技术上亦为死代码：升级只留概率带单判据（2026-10-18 裁定）后，「升级凑金待付」与「刷新放行」两状态互斥，该腿不可达。续刷熔断闸本身保留（利息线纪律在刷新面的执行者，用户确认）。
6. **2026-10-28（刷新金线闸算式更新）**：「当前金 ≥ 最大利息所需金币 + 刷新价格 + 刷新目标角色的价格」。「刷新目标角色的价格」= 当前停留目标（费用档最低的未完成星级目标）的注册表卡价——替换现役「合格集最低费卡价」口径（旧口径按「无 2★」过滤会把已 2★ 追 3★ 的当前目标排除在外，漏留她的卡钱）。
7. **2026-10-28（存在性门删除裁定）**：「P92 删除」——整道门删，刷新判据并入「目标卡刷出后买得到」一行条件；命题行/编号引用/计数键全链清零。

### 补充裁决（2026-10-28 设计对抗期，迭代 `2026-10-28-hp-purge-refresh-reform` 内登记）

- **R-1（血本位支付门归类）**：用户裁决通过——归类为「经验批支付门」币种通式（金本位 = 金余额 ≥ 批 + 守资金线；血本位 = 血余额 ≥ 批），行为零变化，删「血闸」hp 家族命名与危机带串联语义。
- **R-3（血预算视界）**：用户裁决通过——删血项、机制保留（终选口径）：`p2_supply_horizon` 的 H 改为剩余节点数（「整条退役」经对抗实核不可行：`k_empty_window_fallback` 机器有三处生产消费位 + P1 空窗防环职责，与 hp 无关）。行为变化 = 可行性与回退带不再随血低收紧。
- 其余待决项处置（R-4/R-6/R-7/R-8/R-9/W5 前置）：登记于迭代 design.md §3，随 3.1 落地批按清查件建议处置并申报。

---

## 执行纪律：连根删，禁留废弃（2026-10-28 用户裁定，全部工作项通用验收门槛）

- **代码**：函数/谓词/常量/计数键/遥测枚举连根删——禁 deprecated 标记、禁兼容壳、禁「结构位保留」「历史读口」类残件；hp 清查件里标注「挂空」「孤儿」的一律在删除范围内。
- **注释**：引用被删符号/键/命题/判据的注释同步清；「判据历史键名保留」类注记（如 `lv9_stop`）逐个复核，随删。
- **文档**：正本相关章节**整段删除**（不留「已废弃/已停用」叙述段——设计正文 as-built 只写系统现状）；proofs 失效命题行（P21/P36 族等）随重锚批删除或改写；game 侧打法启发式清理深度随 R-8 裁决。
- **测试**：E 组锁语义测试随删/重写，禁留 skip/xfail 尸体。
- **验收判据**：修复批收尾做全仓残留扫描（关键词族：危机带/血预算/血闸/危机不变式/血本位/blood/crisis/hp_critical/levelup_crisis_defer/p2_crisis/hp_floor 等，以 hp 清查件 §5 词表为准）+ 受影响测试全量通过——**残留申报清零才算完成**。

---

## W1【P0·主项】hp 逻辑全删

- **清单单一源** = hp 逻辑清查件 A/B/D/E 组（A 组 11 条、B 组支撑件 19 条、D 组文档 41 条、E 组测试 10 条），本条不重复罗列，修时照清单执行。
- 核心删除：危机带族（`cw_discipline_rules.py:212-260`）、血预算停升级门（`:154-209`）、升级资格门④（`criteria/levelup.py:370-377`，`levelup_crisis_defer` 计数）、`level_spend_blocked`（`:484-514`）、挂空死码（`all_in_xp_domain_hit` / `maybe_pivot` 信号3 / `is_run_dead`）。
- **危机不变式 + P36-a 删除（2026-10-28 单独裁定，范围扩至证明侧）**：
  - 代码：判据函数 `criteria/refresh.py:160` `crisis_refresh_invariant`、序位声明（`mandate.py:1078-1079`）、contracts 注册（`criteria/contracts.py:273` 与 `criteria/__init__.py:76`）、旧执行层落地残件（`crisis_invariant_lane` / `crisis_overflow`，其消费门 `authorize_release_refresh` 已停用）、相关测试锁；
  - 证明：`math_proofs.md` P36 行删除 + 单篇 `proofs/p36-crisis-firepower-floor.md` 整文件删除；P36-a′（`crisis_overflow` 储备线降档）/ P36-b / P36-c 为同一命题族且全部以 hp 为索引（危机深度 d=25−hp），按 W1 hp 口径一并处置；
  - 引用清理：`23_shop_screen.md:10`（刷新门链行）、`14_p1_consume_arms.md`（N5 及 §5.2 相关行）、`10_prep_decisions.md:199`（历史注记）、`proofs/p37-late-xp-conversion-cost.md:188`（同族引用行）、`01_math_framework.md` P36 索引行；
  - 验收：grep `crisis_refresh_invariant|crisis_invariant_lane|crisis_overflow|P36|危机不变式|危机火力` 全仓零残留。
- **状态**：边界待两项裁决闭合（见文末裁决队列 R-1/R-3）。

## W2【P0】升级-刷新互锁补解锁支（结构缺陷 #1，高）

- 形态：刷新判据「带下界 > 当前级 → 先升级」与升级门可同时闭死（本局 lv5 双关 17 帧；批读数 stay_gate 触发 85/85 全拦零发射）。W1 删 hp 闸后主源消失，但升级仍可能因**资金线凑金穷尽**推迟（`levelup_fund_line_defer`），此态下刷新门依旧拒刷 → 同形死锁仍在。
- **要求**：升级处于「推迟/凑金在途」态时，停留刷判据须有让位支（就近刷或显式降级），禁双门同时零动作。
- 锚：`refresh.py:101-105` / `levelup.py:371-377` / `11_shop_decisions.md:186` 批基线。
- **状态**：待设计。

## W3【P1】删除存在性门（P92），刷新判据并入「目标可买」条件（2026-10-28 裁定 #7）

- **裁定**：P92 整门删除。原门 = 六通道枚举（线内件/插件/压牌库/凑星/核心卡/腾位，逐条查「刷得出×买得起×有席位」全死才拦）——抽象过重，且误拦追星的根源即「以通道全集为中心」的错视角。
- **替换**：刷新判据并入一行目标中心条件——**允许刷 ⟺ 目标卡刷出后买得到（有空位 ∨ 已持 2 张买第 3 张直接合成 ∨ 可卖一件腾出位〔备战席燃料 ∨ 场上非线内件〕）**。原「补追星腿」缺陷（#2）由此顺带消除，不再单独立项。
- 删除范围：通道枚举代码（`refresh.py:282-378` `all_channel_buy_exists` + 装配 `shop.py:1996-2049`）、`math_proofs.md` P92 挂起命题行、`01_math_framework.md` all_channel_exists 待证钩子行、全部「P92」编号引用（`23_shop_screen.md`、`11_shop_decisions.md` §3.1 等）、计数键 `p92_no_buy_refresh_blocked` 及其消费端、相关测试。
- 已知余量（用户接受）：极端死态（席满 + 零燃料 + 场上无非线内件 + 不可合成）下会白刷到金线才停——压牌库抢席位修复（W4）落地后该态几乎不可构造。
- **状态**：待设计。

## W4【P1】M6 压牌库与刷新的席位协调（缺陷 #3，中）

- 形态：M6（富余金压牌库囤货）在追星窗口灌满备战席（本局 9/9，`m6_bench_full=8`）+ 燃料售空，反锁刷新。
- **要求**：停留刷窗口内 M6 让位（预留弹药位/限额），或席满时自动降级囤货。
- 锚：`shop.py:1543-1616`。
- **状态**：待设计。

## W5【P2】义务面名单星级盲（缺陷 #4，中）

- 形态：2★ 已达标成员的同名 1★ 副本四条买臂全不接收，2★→3★ 追星通道断裂（本局全场唯一线内件三月七 1★ 在店无人买）。
- 锚：`shop.py:930` + `:1277-1279`。
- **前置裁决**：need_star 达标后同名副本语义（继续追星 or 视为完成停买）。
- **状态**：待裁决后设计。

## W6【P2】缺件不可达无显式出口（缺陷 #5，低）

- 形态：目标件在当前级刷新概率恒 0（5 费在 lv5/6 概率表无档），M2 静默零候选，无换线/降档显式评估。
- 锚：`refresh.py:206-233` / `data/cw_shop_odds.py` 概率表。
- **状态**：待设计。

## W7【P3】刷新发射曝光率（缺陷 #6，低）

- 形态：刷新在单动作序末位 + 每轮仅 1 免费板，峰值级窗口内实际掷板次数过少（本局 20 槽）。
- 锚：`shop.py:772-794`。
- **状态**：待设计。

## W8【P1】文档/遥测对账（随批执行）

1. `changes/2026-10-18-levelup-band-gate/design.md:156`「攒息期升级-刷新双滞 = 预期健康态」声明域（现金 30-60 凑金滞）与本局形态（金 108-142 危机闸滞、无释放条件）不符 → 正本 `11_shop_decisions.md` 相关行核对修正（changes/ 只作勘误线索）。
2. `flow/session.md` §2.1 表 hp 三行对应字段已删（过期行）。
3. `telemetry/schema.py:488` 义务来源枚举 `'crisis'` 无代码写端。
4. `23_shop_screen.md:10`「危机帧不变式 P36-a 先于存在性门」与实况不符（发射链零消费，见 hp 清查件 A-9 交叉复核）。

## W9【P2】复盘报告其他登记候选（非本轮主线，挂账不丢）

- **A2 装备穿戴序配对**（低-中）：同角色连穿两件简易件烧掉 key 组件（本局自适应外骨骼），缺「两件简易不共角色」配对控制。锚 = 复盘报告 L1009/L1030；判定尺 = `10_prep_decisions.md` §2。候单帧测试/实机复测定案。
- **A3 sim 补给决策链未接线**（申报级，流程层非策略）：补给屏带钻选项无选卡回执且兜底点卡未发生（journal v384→v392），与 `30_supply_screen.md` §6 申报形态不符 → 核 sim 流程层。
- **遭遇/BOSS 节点备战章无开店动作**（金 57/87/131 富余段 M6 未获评估位）：流程层节点型工序待核，申报不判病灶。

## W10【P2】刷新判据 R 族死代码清理（2026-10-28 追查发现，非 hp 项）

- **R1 路径总账**（原「刷前算清刷+买+利息总账」门）：2026-10-12 用户裁定被三段式查表判据取代，函数本体已删，残留三处尸体 → 删：注册行 `criteria/__init__.py:65`、注释 `refresh.py:301`、文档 `23_shop_screen.md:10`（该行还把 R1 写成现役放行条件，明确漂移）。
- **r1_start / r0_stop 死函数**：零调用面（r1_start 自注「保留=四函数位完备集，禁复活」）→ 按删除纪律连壳删，同步清 contracts 注册（`criteria/contracts.py:252/255`）与 `criteria/__init__.py:60/62`。
- **保留现役**：`r2_budget`（金−预留≥刷价，shop.py:1994 消费）——唯一活门，不动（2026-10-28 用户确认保留；利息线纪律 = 买面金门/刷新预留/升级资金门三面各一道，本闸管刷新面）。
- **卡价预留 ρ 口径更新（2026-10-28 裁定 #6）**：`criteria/refresh.py::r2_card_reserve`（单一源，shop.py `_r2_card_reserve` 为别名重导出）从「合格集最低费卡价」（`qualified_member_costs` 过滤「该级可刷出 ∧ 无 2★」取 min）改为「**当前停留目标角色的注册表卡价**」（`stay_target_of` 的 cost）。行为差：已 2★ 追 3★ 的目标（如姬子·启行 2★→3★）旧口径被「无 2★」过滤排除、漏留其卡价，新口径正确预留 3 金。连带：①P54 证明行 ρ 语义更新（「合格集最低费卡价」→「停留目标卡价」；docstring 同步）；②`qualified_member_costs` 在 R2 位的消费消失（P91 费用带等其他消费位不动，核查后如无他消费随删）；③测试 `test_cw_interest_floor` 私有名直引面随改；④停留目标为空的帧刷新判据本就拒绝，ρ 无需兜底值。
- **整级经验预留腿删除（2026-10-28 裁定，死代码）**：`shop.py:1988-1989`（升级凑金待付窗时把整级批加进刷新预留）+ 相应注释块句子（:1981-1986 内该支描述）。死因：升级概率带单判据后升级触发态与刷新放行态互斥，该腿不可达。⚠ 别误删 `_up_clicks/_up_cost` 本体——升级意图出口的发射计算仍消费它们（那里可达）。连带复核 `11_shop_decisions.md` §2「升级意图出口」行与 `refresh.py` docstring 中「整级预留保护」句的清理。
- **证明侧随核**：P40/P47/P54 命题行按剩余消费面处置（P40 的 EV 面已随 R1 死，R0-2 判定尺消费位 = 已删的 r1_commitment_account，须重锚或删行）。
- 验收：grep `r1_commitment_account|r0_stop|r1_start` 全仓零残留（r2_budget 保留）。

## W11【P1】刷新负结果记忆 / 重进价值评估（2026-10-28 用户提出）

- 形态：策略没有「离开商店后是否值得再进来」的记录——本局实证：r4 刷 1 次后，3 个收店帧重复提刷被 P92 拦（dseq110/114/122）+ 1 帧会话空转（dseq119），每帧都是「重进→提刷→被同一门拦→关店」白转周期。
- **要求**：同节点内记「刚被判无可买/零收获」——无新事实（金/席/店况未变）时不再提刷、直接关店；可选增强 = 停留刷加「本节点预算包络」（次数上限或零收获计数降级）。
- **边界注意**：期望式评估工具已在仓（`cw_shop_odds.expected_refreshes` / `reencounter_window_frames` 再遇窗）但被 2026-10-12 用户裁定停用（「期望价值难算不直观，星级目标直接驱动」）——若采用期望形态需用户翻案；非期望形态（计数/记忆）不冲突。
- 锚：`shop.py:1963-2075`（刷新发射链）/ `shop_session.py:109`（访问计数）/ `23_shop_screen.md:10`（无墙声明）。
- **加强证据（免费腿旁路）**：免费刷新按裁定「白给的刷新照用」**绕过全部判据门**（`shop.py:1963-1971`，不走查表/R2/P92）——持「高效决策」（9999 次免费刷，`cw_investments.py:473`）时 = 无条件刷到次数耗尽，每次刷新一个完整重进周期，是失控循环的现实形态而非理论担忧。
- **状态**：待设计（形态选择交用户裁决）。

---

## 裁决队列（W1 动工前须闭合）

| # | 事项 | 两难 | 出处 |
|---|---|---|---|
| R-1 | 血本位支付闸（`blood_xp_gate` 族 + 升级门⑥） | 旧裁定 [40]②「血余额≥整级血成本才买经验 = 支付能力检查」vs 新裁定字面（血本位局买经验的币种就是血量，算不算 hp 入参？） | hp 清查件 §3 R-1 |
| R-3 | P2 血预算视界（`cw_intention.py:1067-1150`，⌈hp/期望掉血⌉ → 锁线可行性 G 门） | 删 = P86 命题重锚 + 锁线行为变化；留 = hp 仍在策略输入 | hp 清查件 §3 R-3 |
| R-4~R-9 | 低权重（开局血量先验 / 挂空死码清理范围 / λ 表血带维 / 濒死观测谓词 / game 侧启发式深度 / 事件 hp 读数） | 逐项两难详述见 hp 清查件 §3 | 同上 |

（R-2 应急带刷新闸已落定：遥测面零行为差，随 W1 轻删，非前置。）

## 执行顺序建议

R-1/R-3 裁决 → W1（hp 全删，含文档/测试同步）→ W8 文档对账 → W3/W4（商店链执行层主刀）→ W2 解锁支兜底 → W5/W6/W7 → W9。
