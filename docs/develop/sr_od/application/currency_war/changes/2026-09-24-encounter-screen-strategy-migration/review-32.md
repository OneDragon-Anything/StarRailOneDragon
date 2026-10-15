# 3.2 阶段验收报告

- 验收对象：项目仓 commit `8922f97d2`（15 文件，+179/−958，含 `encounter.py` 整删）；测试仓 commit `0e340efa`（2 文件）。
- 验收方式：独立干净上下文，零残留 grep 与删除面/接线/防线/依赖方向全部直调复跑，不采信 worker 输出；生产链逐跳读代码。
- 验收日期：2026-09-24

## 结论：**通过**（需返工发现 0 条；信息级观察 2 条，均判定合理、无需返工）

## 发现清单

1. **[信息级] 超申报面 1/2：`encounter_pick.py` 模块 docstring 接线状态句收口——判定合理**
   - 位置：`strategies/impl/mandate_v1/encounter_pick.py:14-16`。
   - 事实：3.1 落码时该句为前瞻占位（「现役核仍 = kernel/cw_encounter_selection.decide_encounter……本文件经迁移批 3.2 原子切换后接管」）；3.2 接线后 kernel 判据面已物理删除，该句若不更新即成失实注释（声称 kernel 现役，实际 kernel 已无 decide_encounter）。本批改为「生产接线 = flow.decide_encounter 直调本文件 decide」，直调核实与代码现态一致（flow.py:595-616 直调 encounter_pick.decide）。
   - 证据：该文件不在 landing §3.2 申报文件面内（worker 自报超面）；改动仅注释 3 行（diff stat = 6 ±）。
   - 修正方向：无需返工。属必要注释收口，指针为持久迭代索引（迭代目录名），符合注释规范（变更史不入注释、持久索引合法）。

2. **[信息级] 超申报面 2/2：`flow.py` pick 族段头「投资两屏/遭遇」——判定合理**
   - 位置：`strategies/impl/flow.py:405-406`。
   - 事实：段头注释原述「判据单源 = 策略层 mandate_v1(投资两屏) / kernel cw_events/cw_comps(其余画面)」，本批遭遇判据迁策略层后该句失真；改写为「策略层 mandate_v1(投资两屏/遭遇)」。
   - 证据：flow.py 本就在 landing §3.2 申报文件面内，此 2 行为文件面内的额外注释修订（worker 自报）。
   - 修正方向：无需返工。注释性修订，保持段头与同 commit 代码一致，防注释漂移。

## 验收核对表

### 判据 1：零残留两段 grep 独立复跑 ✓

- ① 两 kernel 文件内 16 符号 grep（无词边界，强于判据）：`cw_encounter_selection.py` 与 `cw_survey19_hooks.py` 对 `EncounterPick|decide_encounter|encounter_tier_score|F_MIN|G_BASE|DELTA_T|g_ratio|_d_enc_snapshot|_Diagnostics|_kappa_state|reward_tier|_lowest_idx|_FILL_EDGE_THRESHOLD|REWARD_TIER_LAST|_option_mechanics|_reward_value` 均零命中 ✓。
- ① `cw_events.py` 现态直读：`EVENT_PICK_TYPES = (MegastarPick, PartnerPick, PlannerPick)`（:443）、`EventPick = MegastarPick | PartnerPick | PlannerPick`（:448）——无 EncounterPick 位 ✓。
- ② 全仓词边界 grep（src + sr-od-test 的 .py）：`\bEncounterPick\b|\bF_MIN\b|\bG_BASE\b|\bDELTA_T\b|\bencounter_tier_score\b|\bREWARD_TIER_LAST\b|\b_option_mechanics\b|\b_reward_value\b` 双侧零命中 ✓（大小写敏感；`f_min` 小写记号未误报——判据集本身全大写/带下划线前缀，不涉及）。
- 附加：`dark-install` 全仓零命中（标定缺失型暗装段退役 ✓，新 fail 段 = `dark-fallback:*`）；被删 EV 核 `mandate_v1/encounter` 无残留 importer（src grep 零命中）。

### 判据 2：删除面完整性（对照 design §2.7 清单）✓

- **保留面逐项未动**（直读现态 + diff 零触碰）：
  - `SettlementRing`/`EncounterLog.tier_cleared`/`record_settlement_row`/`claim_encounter_reward`/`last_normal_battles`/`last_row`/`game_start_reset` 均在 `cw_encounter_selection.py` 现态（仅 docstring 增消费者指针与孤儿申报，行为零改动）；`game_start_reset` 全仓零调用与 design §2.1 孤儿申报一致（grep 仅定义点）。
  - `EncounterOption` 留 kernel（cw_events.py:44），六方消费面未动。
  - `D_ENC_VARIANT` 槽留 kernel（唯一标定槽，`_CALIBRATABLE = ('D_ENC_VARIANT',)`）；kernel `apply_calibration`/`reset_calibration` 重建为仅收该键（未知键抛错照旧）。
  - `cw_screen_battle_wait.py` 装填分支零改动（不在 commit 文件面；现态 :303-323 直读 `D_ENC_VARIANT` 双态装填照旧，None 期遭遇行恒 None）。
  - `cw_difficulty_account` 只收口注释未删码 ✓：diff 仅 `from_strategies` docstring（孤儿态登记）；`GROWTH_PER_STREAK` sim 活消费直调实证（`sim/cw_sim_enemy.py:33-34` import、:128 消费）——「禁整模块删」申报成立。
  - `cw_survey19_hooks` 剩 `wear_discipline_alert` ✓（模块头改述「P1 狼狩穿戴纪律(单件模块)」）。
- **EV 核退役** ✓：`encounter.py` 整删（401 行，deleted file mode）；`provisional.py` 双槽 `ENCOUNTER_DSTAT_MAP`/`ENCOUNTER_G_GOLD` 删除 + 头部指针句改指策略层注入口。

### 判据 3：新接线正确性 ✓

- `flow.decide_encounter`（flow.py:595-616）：`_require_slot_options` 守卫原样（离屏 None 抛错保留）→ 入口内务 `_consume_prep_direction_frame()` 保留 → `encounter_pick.decide(options, self.gs)` → 两型动作包装（`EncounterRefreshSuggestion`→`CwActionRefreshNodeOptionsParam`、`EncounterPickDecision`→`CwActionPickEncounterParam`）；`refresh_used` 预计算删除（次数闸内嵌 decide，直读 encounter_pick.py:200-212 `_empty_reachable_frame`：left≥1 才建议刷、None/0 落最低档，fail-closed）✓。
- `cw_events` import 保留合法 ✓：flow.py:657（decide_planner）、:794（decide_fortune）、:808（choose_expert_index）三处直调现役。
- `bridge.decide_encounter` 覆写已删 ✓：全仓 `def decide_encounter` 仅 cw_strategy.py:178（抽象）+ flow.py:595（基类实现）两点；bridge 现 import 面（GameState/CwAction/CwActionObsParam/CwFlowStrategy/entry/state_of）ruff 实证无未用（六文件 ruff 全过）。
- **生产链逐跳推演无断点** ✓：`cw_screen_encounter.act` 调 `match.strategy.decide_encounter()` → config `strategy_id` 值域收缩 = {'mandate_v1'}（currency_war_config.py:72-81）→ `MandateV1Live(MandateV1Strategy)` 零覆写注册壳（mandate_v1_strategy.py:17-22）→ `MandateV1Strategy(CwFlowStrategy)` 无 decide_encounter 覆写（bridge.py 现态确认）→ 基类 flow.decide_encounter → `encounter_pick.decide`（签名 `(options, gs)` 匹配；纯值出口；判据序与 design §2.2–§2.5 逐位相符：立场门→窗口→κ_S 三态→cap 过滤在前→t≤4 直判/t≥5 经验层→空集阀→difficulty 最高主序→tiebreak 小优→输入序先；reason 因词封闭枚举 `refresh-valve:{window-insufficient|kappa-不足|empty-reachable}` 与 `dark-fallback:*` 照 §2.2 契约）。
- `EVENT_PICK_TYPES` 运行时构造合法（删类同批摘位，无 NameError 面）；注册完备测试（test_cw_unified_action_4.py）全绿。

### 判据 4：防线实现 ✓

- `cw_screen_encounter.py` 重调分支：重调仍返 `CwActionRefreshNodeOptionsParam` ∧ 刷新锚读缺 → `round_fail('刷新锚点读缺,交回重读')`（diff :863-870）；分支进入条件分析直调核实——left 读缺/0 帧 decide 闸内嵌不返建议、不进本分支，活面 = left≥1 ∧ 锚读缺，与 design §2.5 一致。
- `cw_loop.py` 语义直调核 ✓：`OP_FAIL_REDISPATCH_LIMIT = 5`（:529）；分发网 ok=True（含零点击 round_success）→ 连续 fail 窗清零（:829-836），fail → 计数、达 5 → 显式 round_fail 交上层（:852-868）——旧「零点击终结交回」确对「锚持续读缺 ∧ 建议刷恒成立」无防护，改 fail 后有界收敛，design 定谳论证与代码一致。
- 行为测试改写 ✓：`test_encounter_refresh_gate_mismatch_round_fail_redispatch` 断言 `not rs.is_success and '刷新锚点读缺'` + `clicks == []` + `dispatches == []`（零点击零派发保留）；docstring 同步改写并引持久迭代指针。
- 其余 op 路径零行为变化 ✓：`cw_screen_encounter` diff 除该分支外仅注释；`cw_pick_encounter_action`/`cw_action_report/pick_encounter.py`/`cw_battle_wait` 均不在 commit 面零改动。

### 判据 5：依赖方向 ✓

- kernel 无指向 strategies 的 import ✓：kernel 目录 `^\s*(from|import)\s+.*strategies` 零命中（全部为注释/docstring 中的依赖矩阵声明文字）。
- 策略层无 obs import ✓：strategies 目录对 `currency_war.obs` 零命中；`encounter_pick.reward_tier` 钻石检测集消费 `kernel/cw_obs_core.DIAMOND_EQUIP_NAMES`（kernel 手维护件，方向合法）。

### 判据 6：注释收口（design §2.7 清单逐项抽查）✓

全部经 diff 逐条确认：cw_vocab 两处（CwActionPickEncounterParam/CwActionRefreshNodeOptionsParam「替代 EncounterPick」改指策略层载体）✓；cw_node_obs 三处（模块 docstring「喂 cw_events.decide_*」句、难度轴 comment「decide_encounter 按难度选」句、read_encounter_options docstring「comp 成型度选」句）✓；EncounterOption 六档句（「1=易/2=中/3=难」→ 六档事实 + 漏读「一」→1）✓；cw_economy 败补消费点清单（6 → 5，encounter.py 引用随删件摘除）✓；cw_difficulty_account 孤儿登记 ✓；cw_survey19_hooks 模块头 ✓；cw_strategy 接口注 ✓；supply.py 钻石单一源句改指 kernel/cw_obs_core ✓；flow docstring「kernel 按原评分直接选卡」句改写 ✓；cw_events 模块 docstring 遭遇句收口 ✓；provisional 头部指针句 ✓。

### 判据 7：测试面 ✓

- 两仓 diff 对照 ✓：测试仓仅 2 文件——重调测试改写（docstring+断言+测试名）与替身改词表动作（import 摘除 + 两处实例构造改 `CwActionPickEncounterParam(idx=1)`）；`claim_encounter_reward` 分支测试（`test_claim_encounter_reward_branches`）零改动；两测试文件对 `cw_encounter_selection` 的 import 仅保留面符号（claim_encounter_reward/record_settlement_row），与 design §2.7 测试面申报一致。
- 自跑验证 ✓：三受影响文件 57 passed；CW 全量 L1（`-m "not slow"`）**1156 passed**；六改动文件 ruff check 全过。

### 判据 8：超申报面两处评估 ✓（合理，见发现清单 1/2）

两处均注释性、均必要（一处防失实注释、一处防段头漂移），无行为面，持久索引合规，非边界侵入。

### 边界侵入检查 ✓

`git show --stat` 两 commit 与 landing §3.2 申报文件面逐一对账：项目仓 15 文件 = 申报 14 文件 + `encounter_pick.py`（发现 1，注释性）；测试仓 2 文件 = 申报面；无集合外文件混入；sim 文件零触碰（「不改 sim」边界守住）。

### 附：设计 vs 实现微差登记（不构成发现）

- design §2.1 列 `selection_state_of`「随本体迁」——实现未在策略层重建该 helper，`encounter_pick.decide` 直读 `gs.settlement_ring`/`gs.encounter_log`（encounter_pick.py:237-238）。迁出目的（kernel 侧零消费、判据取数随本体）已达成，全仓零残留；两属性读取无封装价值，属实现自由度，不返工。
- `last_normal_battles`/`tier_cleared`/`game_start_reset` 三处 docstring 增注消费者指针/孤儿申报——「保留面原样」指行为零改动，注释增注属 design §2.1/§2.7 明文义务（game_start_reset 失实 docstring 随批收口），合规。
