# hp 判据族删除（详设）

## 问题与约束

- **边界与状态**：R-1/R-3 已于 2026-10-28 用户裁决通过（总纲 §3），本篇可开工。本篇管 hp 判据族删除中**除刷新判据面以外**的全部（`criteria/refresh.py` 的 `crisis_refresh_invariant` 归 refresh-chain 详设，见总纲 §2.1 文件面契约）；接口契约：本篇删除不得改变刷新发射布尔语义；`shop.py` 刷新段不在本篇文件面（唯 carve-out 三行见总纲 §2.1）。

## 方案

### 1. A 组删除（hp 清查件 §2.1 逐条，本篇执行范围）

| 清查件条目 | 锚 | 处置 |
|---|---|---|
| A-1/A-2 危机带族 | `cw_discipline_rules.py:212-260` | 删 `p2_crisis_stop_hp` + `p2_crisis_band`（裁定 #1） |
| A-3 血预算停升级门 | `cw_discipline_rules.py:154-209` | 删 `blood_budget_levelup_blocked` |
| A-4/A-5 M3 升级让位消费位 | `criteria/levelup.py:484-514` + `:370-377` | 删 `level_spend_blocked` 两支 + 资格门④（发射门序 7→6 门，`levelup_crisis_defer` 计数键删）；连带契约登记行随删 = `contracts.py:243-246` + `criteria/__init__.py:54-55`（清查件 A-5 明细自带，勿丢）；`mandate.py:963/:996` 残留引用随清 |
| A-7 挂空死码（maybe_pivot） | `cw_comps.py:2862-3102` | 删；连带面 = `cw_comps.py:37`（effective_hp_threshold import）、`:125` 注释、`:2852-2859`（PIVOT_SURVIVAL_COOLDOWN_ROUNDS 常量与保命豁免注释）、`pivot_overlap` 判据（删后孤儿随删）、`cw_performance.py:107` 与 `cw_hp_policy.py:20` 注释引用 |
| A-6 挂空血侧谓词 | `cw_discipline_rules.py:82-128` | 删 `all_in_xp_domain_hit` |
| A-8 挂空死码 | `cw_performance.py:244-269` | 删（待办层零生产调用，测试经桥调用面随删） |
| A-10 血本位支付门 | `criteria/levelup.py:385-392` + `cw_economy.py:792-882` + `entry.py:844-846`（血闸措辞同步） | **已裁决（R-1）**：归类「经验批支付门」币种通式，行为零变化，删 hp 家族命名与串联语义（总纲 §3） |
| A-11 P2 血预算视界链 | `cw_intention.py:1067-1094`（H 计算）+ `:1099-1150`（G 门）+ `:1427-1530`（arm_a_*/no_target_arms/hoard_target_set 消费）+ `shop.py:373` | **已裁决（R-3，删血项、机制保留）**：H = 剩余节点数，`k_empty_window_fallback` 机器与其消费链保留——细目见 §3 |

### 2. B 组孤儿清理（hp 清查件 §2.2 随主判据删除逐条核）

`p1/p2_levelup_stop_hp` 推导、`cw_registry.py` 血预算参数块/约束名/slot 行/handoff hp 维投影/k_alert 族、`cw_hp_policy.py::decision_hp` 等——**照 hp 清查件 B 组表逐条执行**。执行规则三态：①「零消费孤儿」→ 直接删；②「保留（观测面消费）」→ 不动（如 `hp_decision_trusted_of` 的可信位）；③**「改」类条目**（B-16 get_node_goal 形参支随 A-9 收窄、B-19 blood_xp_mode 随 R-1 联动核）→ 按清查件该行「改」处置执行；**B-6 更正（R-1 裁决后）**：decision_hp 读口**保留**（经验批支付门 fail-closed 读口，行为零变化），其 hp 判据消费面随 A 组删除申报。连带面触碰文件（`cw_game_state.py`、`cw_vocab.py`、`mandate_state.py`、`statefn/predicates.py`、`audit/provisional.py`）已收编进本篇文件面（总纲 §2.1）。**例外（R-6/B-12）**：`cw_first_passage.py` 本体保留（首达生存模型 = sim 校准面工件，非 hp 判据——本批零触碰、不在词表）；λ 表血带维处置面 = `statefn/lambda_death.py`（B-12，已收编进总纲 §2.1 本篇独占与 landing 3.1 文件面）——仅删零消费子集（`make_key` 内部量/`hp_band` 内部量/`HP_BAND_MID`），**`HP_BAND_NEAR_DEATH` 保留**（R-7 保留谓词 `p1/p2_blood_floor` 的阈值单一源，`statefn/predicates.py` + `test_levelup_prob_axis.py:406` 消费）；三态规则①不适用于保留子集。
- **B 组连带悬空注释/孤儿登记面**：B-8/B-17/B-6/B-14 删除后在 `obs/`、`operations/`、`currency_war_config.py`、`cw_entry_policy`（若存在）、`cw_decision_trace`（若存在）、`telemetry/schema.py:460-465` 留悬空注释与孤儿登记 ≥13 处——**点名收编进本篇文件面**（注释清零，逐处直调核验），词表已含对应符号（§6）。

- **A-9 单列**：应急带归零链（`cw_economy.py:1074-1088` is_emergency → `:1237-1287` refresh_ev_budget 归零）是 hp 清查件 **A 组条目 A-9**，归**本篇（3.1）**执行——`cw_economy.py` 在本篇文件面（总纲 §2.1）；追查件 §7 已实锤零行为差（消费端 = 遥测披露面）。连带注释/消费面清点：`economy_cycle.py:187/:29`、`statefn/odds.py:67`、`shop.py:327`（跨文件注释面点名，词表见 §6）。

### 3. R-1/R-3 处置（细节）

- **R-1（推荐方案）**：`upgrade_gate_verdict` 门⑥改名 = 「经验批支付门（币种通式）」：`支付币余额 ≥ 整批成本`（金本位另守资金线——该守线已在门⑦，非本门）。删 `blood_xp_gate` 族命名与「与危机带串联 AND」表述（串联对象已删）。行为零变化；hp 不可信帧 fail-closed 语义保留（读数损坏防护，非 hp 判据）。依据 = `11_shop_decisions.md:58`（[40]② 支付能力检查定性）。
- **R-3（已裁决通过；处置口径按工程实况定为「删血项、机制保留」）**：视界的**血项删除**——`p2_supply_horizon` 的 H 从 `min(剩余节点数, ⌈hp/vd_p2_loss⌉)` 改为 `剩余节点数`（registry `cw_plane_table` P2 值），机制本体（`k_empty_window_fallback` 及其消费链）**保留**。不可整条退役的机器事实：`k_empty_window_fallback`（`cw_intention.py:1576` 起）有三处生产消费位（`shop.py:885` 商店序 1 名单回退、`entry.py:480` 部署围栏、`decision_payload.py:101` payload 派生）且承担 P1 空窗防死锁职责（`contracts.py:138-142`），与 hp 无关；`K_FALLBACK_SOURCE_THREE_ARM` 守卫（`contracts.py:100-106/:166-171`）保留不删（删则 K 空窗帧 EV/M6/dominance 经 fail-closed 静默弃权）。处置细目：①`p2_supply_horizon` 删血项、签名与消费位（`arm_a_*`/`no_target_arms`/`hoard_target_set`/`shop.py:373`）随新 H 语义重算；②契约守卫面（`contracts.py:88-106`）直调核验**不读 H**——无需改码，随行为变化申报即可；③行为变化申报 = 可行性/回退带不再随血低收紧（含 P2 未锁定窗口囤货方向）；④P86 命题重锚（H 定义变更，`math_proofs.md` P86 行）。
- **R-3 删除面补全**：机制保留后，删除/改口径面 = `p2_supply_horizon` 血项与签名（`contracts.py:88-106/:166-171` 守卫面直调核验**不读 H**——无需改码，随行为变化申报）；`shop.py:373/:996` 消费行随新 H 输出值语义（文件面 carve-out 见总纲 §2.1，仅此两行归本篇；两行均无 H 值流，无「两消费位等值锁」义务）；测试面：`test_no_target_three_arms.py` 带断言随新 H 更新（该文件实锁 P86 三分支与回退带，机制保留故文件保留）、`test_decision_payload.py:10/:158/:169`、`test_line_select.py:358-360` 直调断言随 H 更新。观测键族 `LOCK_PATH_OBS_KEY_PREFIXES`（`cw_intention.py:1163-1171`）**保留**（G 门机制保留）；其中 `neardeath_direction_obs_` 前缀在 src 零发射点（仅注册行 :1166，死键）→ 随删申报；LOCK_PATH 键族测试侧零覆盖（无守卫测试文件），不设测试义务、如实申报。行为变化申报补 K 空窗帧：商店序 1 名单/部署围栏/payload 回退带按新 H（不再随血低收紧）。**孤儿申报**：视界血项删除后 `vd_p1_loss_*`/`vd_p2_loss`（`cw_registry.py` 伤害锚数据行）暂成零消费孤儿——处置 = 注册表数据行保留（游戏定义值，数据非判据），消费链已空如实申报，`04_survival_budget.md` §6-1 核对项同步 dead 标注。
- 两项已于 2026-10-28 用户裁决通过（总纲 §3），本篇可开工。

### 4. C 组（观测面）保留边界

hp 清查件 C 组 13 条**全部不动**（画面观察 hp 读数、回灌判据、sim 校准边界——hp 作为事后读数不违反裁定 #1）。唯一交叉点：`hp_floor_triggered`（`cw_game_state.py:2954`，纯观察登记）保留。

### 5. D 组正本章删除 + E 组测试

- D 组 41 条（hp 清查件 §2.4 D-1~D-30 + §2.5 DG-1~DG-11）：正本 strategy-docs 各篇 hp 判据章**整段删**（禁「已废弃」叙述段）；proofs hp 家族命题行（P21 等）删除或重锚；game 侧（DG 组）清理深度随 R-8 裁决（未决前本批只删 develop 侧）。**本篇只登记执行义务，逐章清单 = hp 清查件 §2.4+§2.5，落地批照单执行。**
- E 组 10 条测试锁：**按 hp 清查件 E 组逐条处置**（E-9 标注「保留不动」者不动；其余随删/重写，禁 skip/xfail 尸体）；新增单帧测试固化「升级发射不再有 hp 支」语义（docstring 引本迭代 design.md）。锚漂移注记：清查件 E-7 锚路径 `kernel/test_settle.py` 实为 `operations/cw_op/test_settle.py`（内容吻合）——落地批直调现路径处置，快照保留清查件原貌。

### 6. 残留扫描验收（裁定 #3）

- **扫描时点与范围分层**：3.1 阶段收尾对**符号级词表做全仓扫描**（词表逐符号唯一、无误捕风险，全仓安全）＋ 本篇文件面结构核对；`docs/` 残留扫描归**末阶段**（正本章删除发生在末阶段，此前扫必然不清零）。
- **词表（符号级，可清零口径——被删符号清单，逐符号对照 hp 清查件 B 组/A 组裁定）**：`p2_crisis|blood_budget|blood_xp_gate|levelup_blood_gate_defer|crisis_stop_hp|levelup_crisis_defer|level_spend_blocked|all_in_xp_domain_hit|is_emergency|emergency_hp|p1_levelup_stop_hp|p2_levelup_stop_hp|DIFFICULTY_HP_TABLE|HP_QUALITY_ALARM|form_floor|p1_exit_blood_target|k_linear|k_hp_calibration_grid|blood_margin_low_hp|k_alert|effective_hp_threshold|HP_SAFE_THRESHOLD|HP_BAND_MID`。
  - **不过扫符号（R-1 保留面 + 避免过度捕获）**：`decision_hp`（R-1 保留 = 经验批支付门读口，行为零变化）；`blood_xp_full_clicks`（全量击数算术保留）；`blood_xp_mode`（B-19「改」类条目，随 R-1 币种通式联动核，非删）；`refresh_ev_budget`（清查件 A-9 处置 = 删归零支**非删函数**，符号保留、diff 核对归零支消失）；`p1_blood_floor|p2_blood_floor`（R-7 保留裁定，观测谓词）；`p2_handoff_*`（handoff 快照/数据面保留键，仅 `handoff_boss_e_damage` 等清查件 B-4 明列投影参数删除——精确列名不扫裸前缀）。
  - `levelup_blood_gate_defer` 处置声明（R-1 连带）：门⑥改名「经验批支付门」后旧拒因键清零，新拒因键 = `xp_batch_payment_defer`（币种通式语义）。
  - `p2_supply_horizon|line_completion_feasibility|no_target_arms|hoard_target_set|k_empty_window_fallback` = **保留-改口径符号**（不在清零词表，验收 = diff 核对无 hp 读取）。
- **宽词族（hp/血/危机/crisis）不作符号级清零判据**——C 组观测面合法保留 + game 侧 R-8 挂账，宽词扫描仅作末阶段辅助盘点，命中行逐条归类（保留依据/漏删申报），豁免清单随残留申报一并出具。
- 多行形态模式或 AST 扫描（防跨行绕过，进度账本验收协议条款）。**符号级残留清零 + 漏删申报零条 = 本篇完成必要条件。**

### 7. 执行单一源快照义务

四份证据与裁定文件（hp 清查件、支出链追查件、复盘件、裁定载体工作清单）与本篇 §6 词表均寄存 `.debug`（gitignore 区，寿命独立于迭代）——**3.1 开工前**须全部快照抄录至本目录 `details/hp-purge-appendix.md`，作为落地批执行单一源；快照以清查件原文件为准（清查件内部 B 组编号错位如实保留，不重排）；`.debug` 原件此后仅作溯源参考。

## 关键取舍

- **R-1 备选 = 连支付检查一起删**：放弃。理由：血本位局里血就是经验币种，「余额够不够」是币种算术——金本位局「金不够买经验」从来不被叫 hp 逻辑，血本位同构检查不应因币种是血就被归为 hp 判据；删掉它 = 允许发射游戏必拒绝（或致死）的购买，无策略语义。依据 = [40]②（`11_shop_decisions.md:58`）。
- **R-3 备选 = 仅删 hp 项保留 G 门（终选）**：「整条退役」备选放弃——机器事实（`k_empty_window_fallback` 三生产消费位 + P1 空窗防环职责，与 hp 无关）证明整条退役不可行；删血项 = 满足裁定 #1 的最小治本面。
- **A-7/A-8 挂空死码备选 = 保留待后续启用**：放弃。依据 = 删除纪律（裁定 #3）+ 未证即停用通则（strategy-work §1：注记留码 = 垃圾代码）。
