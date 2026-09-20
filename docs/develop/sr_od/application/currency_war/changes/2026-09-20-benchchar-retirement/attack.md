# 对抗审查报告：benchchar-retirement 迭代设计

> 审查角色 = 对抗审查员。方法 = 对 design.md §4 inventory 用 grep 逐符号复核（BenchChar / CwSimFrame / bench_place / _merge_bench / 三个换形函数 / is_item_slot / tracked_books），重点攻击三个可能被低估的面（CwSimFrame 消费深度、策略层 tracked 快照形态、观察链产出形态），并对阶段切分、四不变量测试锁、派生信息、sim 行为面逐条取证。
> 判级标准：blocker = 不修就没法开工 / 必产错误行为；major = 设计缺口但实施中可纠正；minor = 文字 / 完备性。
> 行号锚基于 2026-09-20 分支 feat/mcp-backend-sync2 工作区现状，实施推进后行号会漂移，符号名为准。

## 判级总览

**结论：需先修订（blocker 1，major 5，minor 4）。** 设计的动机诊断、终态形状、观察/记录层先行容器化的前提判断全部成立；但 T-1+T-2 的闭合集在文本里不可执行（tracked_books——容器内 BenchChar 大本营——不归属任何阶段，sim 两处 bench_place 直调方排在 T-4 却在 T-1+T-2 签名翻转时即断），且设计第 4 行明确要求读者「照阶段执行，勿重设计」，闭合集欠账不能指望实施者自行重设计补齐。

---

## Blocker

### B1. T-1+T-2 闭合集与阶段结构自相矛盾：tracked_books / mutate_bench_deployed 链无阶段归属，sim 直调方跨阶段断裂

**证据链（bench_place / _merge_bench 的全部直调方，grep 全量）：**

| 直调方 | 调用点 | 设计归属 |
|---|---|---|
| `cw_action_report/buy_card.py` | 111（bench_place）、114（_merge_bench） | T-1+T-2 ✅（已列） |
| `cw_action_report/collect_ore.py` | 205、236 | T-1+T-2 ✅（已列） |
| `kernel/cw_merge_simulate.py` | 132、191、506 + 定义 226 | T-1+T-2 ✅（kernel 算法，隐含） |
| `kernel/cw_exec_state.py` bench_from_compact | 305 | T-1+T-2 ✅（隐含） |
| **`kernel/cw_vocab.py` mutate_bench_deployed** | **1238（bench_place）、1241（_merge_bench）** | **❌ 无阶段提及** |
| **`sim/cw_sim_nodes.py` place_bench_unit_placeholder** | **284（bench_place）** | **❌ 设计排在 T-4** |
| **`sim/cw_sim_opening.py` apply_opening** | **126（bench_place）** | **❌ 设计排在 T-4** |

**为什么这是 blocker 而非 major：**

1. **mutate_bench_deployed 是活代码，不是残留。** 它的活消费方有两条：(a) 实机买入执行链 `operations/cw_op/cw_buy_card_action.py:173`——`mutate_bench_deployed(_books.bench, _books.deployed, action, shop=_payload_cards)`，操作对象是 `GameState.tracked_books`（2026-09-09 双响事故的修复写入点，见该处注释）；(b) `kernel/cw_action_report/buy_card.py:162` 升星腿经 `mutate_bench_deployed_local`（cw_game_state.py:1859-1865 惰性转发）调它。T-1+T-2 的文本清单（「9 个上报函数工作副本直用 BenchView」）覆盖了 (b) 所在文件却没提 (a)——实机 operations 层文件不在 T-1..T-6 任何阶段的文字描述里。

2. **tracked_books 是容器内 BenchChar 大本营，形状迁移无阶段归属。** `GameState.tracked_books.bench/deployed` 声明为 `list[BenchChar | None]`（cw_game_state.py:2352-2361，非 Field 簿记，合法写端 = reconcile_tracking + 动作随动同步）。BenchChar 退役 ⇒ tracked_books 必须换形状，这是**容器 schema 变更**，design.md 全文没有出现「tracked_books」这个词。它的读写端横跨：`cw_reconcile.py:313,345`（reconcile_tracking 整表写回）、`prep_actions.py:493,593,735-800`（卖出后备势同步/溢出腿/部署装备回写）、`cw_screen_prep.py:783`（_reconcile_tracking 形参 `list[BenchChar]`）、`cw_screen_buy_cards.py:788-790`、`cw_op/cw_op_equip_all.py:102`、`cw_op/cw_deploy_move_action.py:75`、`cw_action_report/sell_bench.py:84-90`（溢出吸收构造 BenchChar 写 tracked）、`cw_action_report/wear_equip.py:49`（上报函数读 tracked）。T-1+T-2 文本声称覆盖「kernel 算法 + 上报函数」，实际闭合集按无兼容层裁定至少要拉进 obs / operations 共 10+ 文件。

3. **无兼容层裁定下没有第三条路。** bench_place 签名翻转后，旧形状 tracked 表无法调用它；让 mutate_bench_deployed 用 `bench_view_of_slots` 临时换形续命 = (i) 与「不设双路径」的用户裁决冲突（隐性兼容层）；(ii) tracked 路径的占位件三分类照旧被压成布尔再降级——**本迭代要修的信息销毁根因在 tracked 路径原样存活**，与 §1 动机直接矛盾。同理，sim 两处直调方（cw_sim_nodes.py:284 / cw_sim_opening.py:126）若留到 T-4 修，T-1+T-2 落地瞬间即断，「逐阶段测试全绿」在 T-2→T-4 之间不成立。

**修订要求：**
- 在 design.md 明文重写 T-1+T-2 闭合集：tracked_books 形状迁移 + mutate_bench_deployed 重写 + 上列全部读写端 + sim 两处 bench_place 直调方的最小容器化修补，逐一入单。
- 明文裁定：阶段边界处禁用换形函数做续命转换（换形函数仅存续于「尚待迁移的只读消费方」——即 bench_slots_of 读口族——不做任何写路径中间形）。
- 若实施已按现文本开工（design.md 第 4 行「状态 = 实施中」），先停 T-1+T-2 提交，按本闭合集重新圈定提交面。

---

## Major

### M1. 不变量 1「装备继承载体」腿无测试锁

merge 时素材装备并入升星载体的逻辑（merge_simulate.py:163-183：`inherited` 累加 → `carrier.equips` 拼接 → 链式到不动点）是 T-1+T-2 重写对象，但全测试仓**没有任何断言 merge 后装备继承的测试**：grep `inherited|继承|merge.*equips` 零命中装备继承断言。`test_cw_merge_step_callback.py` 只锁 on_step 回调每合成级触发一次；`test_cw_transfer_golden.py` 锁的是卖/换位族的退款、装备回收、排继承（文件头声明），不是 merge 继承；`test_cw_overflow_gate.test_overflow_absorb_syncs_tracked` 锁溢出吸收。装备继承环节现有防线 = merge_simulate 内部的自检 raise（:194-197 场上同名同星 ≤1），不含 equips。**要求：T-1+T-2 开工前补一条容器形状下的继承锁（2 个带装备素材 + 1 载体 → 升星后 carrier.equips = 原有 ∪ 两素材件），或写入阶段验收判据。**

### M2. 不变量 2「部署恒 held」腿无测试锁

`test_cw_sell_item_slot_predicate.py:25-27` 明文申报：`is_item_slot` 属性读的唯一合法居所是卖出谓词（有行为锁），**部署侧 cw_deploy_logic 同名读「防线归 review 与代码规范」——无锁**。占位恒 held 的实现 = `cw_deploy_logic.py:538-549`（is_item_slot 候选剔除出全部桶、恒 held、拒因 'item_slot'）与 :291（死供给判定②）。T-3 把这两处改 `kind ∈ ('tome','bookcard','supply_box')` 时没有回归网。**要求：T-3 前补 select_deployments_reasoned 对占位件恒 held + 拒因入闭集的锁。**

### M3. 开拓者形态归一在容器写路径的归属未设计，且现状写路径本身不对称

`_apply_row_to_char`（cw_exec_state.py:401-417，签名 BenchChar）负责换排时改写 char_id（记忆↔欢愉）并同步 faction——这是 cw_chars.py:47-53 登记过的历史事故（欢愉计数虚高/记忆漏算）的修复单一源。现状：(a) tracked 侧 mutate 有归一（cw_vocab.py:1260,1294）；(b) swap 上报有归一（swap_deploy.py:78）；(c) **deploy_move 上报没有**（deploy_move.py:63-69 只改 position_pref，不调 trailblazer_form、不刷 faction）——行为靠下一帧观察自愈（cw_identity_obs.py:450-451 按排归一）。design.md §2 退役符号清单与 §5 各阶段**均未提 `_apply_row_to_char` 的去留**；BenchChar 退役后其签名即断。若 T-1+T-2 重写 swap 上报时把 :78 的归一弄丢、或 T-3 部署装配把消费点防御归一（cw_board_by_row.py:43-44、cw_bond_equips.py:131-132）误解为可删，board 计数即重现历史事故。测试网仅有纯函数路由锁（test_cw_sim_equips.test_trailblazer_form_routing），**容器行写归一无锁**。**要求：design.md 补一条——Unit 版形态归一挂在哪（建议：行写端/上报函数内，与 board 派生同挂点），并明确 deploy_move 上报是否顺带补齐对称性（属行为变化，需单独申报）。**

### M4. 「CwSimFrame T-4 一次删干净」的真实体量在测试种子层，且 M1 锁骑在被重写的通道上

生产侧消费深度复核结论（对 §6 风险 3 的正面回答）：**比 178 处引用（src 91 + 测试仓 87）暗示的浅得多**——
- 三个 CwSimFrame 签名的 kernel 函数是**死代码**：`cw_economy.economy_score`（:923）、`cw_discipline_rules.star_weighted_copies`（:29）、`cw_bench_equips.state_equips_multiset`（:134）全仓（src+测试）零调用点；`cw_first_passage` 的帧入参包装同理（板强/胜率真入口是标量参，cw_first_passage.py:119,208）。
- 序列化/重放契约**已先行切断**：telemetry `serialize_state` 委托容器 `full_state_snapshot`（schema.py:236-252），旧档案按 dict 宽容读；`sim/cw_replay.py` 走 `restore_state_snapshot` 容器恢复（:31-118），CwSimFrame 重建面已退役（:9-12 自证）。删帧不破任何落盘/回放契约。
- 剩余真实体量 = **测试种子层**：18 个测试文件 87 处直构 CwSimFrame，统一经 `_cw_helpers.py` 的 `cw4_state/cw4_feed/cw4_box` → `synthesize_from_game_state` 装箱（_cw_helpers.py:188-304）。T-4 删帧必须同批重写整个种子层为直构 GameState。
- **方法学风险**：M1 投影锁（test_cw_shop_projection_logic.py:61「CwSimFrame 桩帧 → 容器（sim 合成口；测试/生产同一条喂入通道）」）自身骑在被删的种子通道上。「零行为变化」的核心证据与被改物同体——重写种子时若语义漂移（如空牌面补写、节点 kind='' 补写、D 类域补写的差异，见 _cw_helpers.py:268-271 两处刻意分叉），锁会在改动种子的同一提交里变绿/变红而不可判读。**要求：T-4 增补两条设计条文——①种子层重写为独立提交单元且锁断言逐字节保形；②设计 §6 预算测试迁移体量（18 文件 + 共享 helper）。**

### M5. 「零行为变化」申报不成立：sim 中间形往返现有两处保真缺陷，直构化必然改变其行为

- `place_bench_unit_placeholder`（cw_sim_nodes.py:278-288）：view → BenchChar 表 → bench_place → bench_view_of_slots 的往返把**占位件槽压成 empty**（:279-283 只搬 kind=='unit' 槽，非 unit 槽留 None → 写回变 empty），且**不搬既有 Unit.equips**（:282-283 构造无 equips 字段）——sim 奖励角色落席帧会把已穿戴装备从容器席位视图抹掉。T-4 直构 BenchView 后这两点必然变成「保留」，是行为变化（修复方向正确）。
- `_find_and_mutate_unit` bench 腿（cw_sim_equips.py:117-131）：已重建好容器槽表（new_slots），却再经 `_slots_to_chars`（:153-163，占位件同样压 None）→ `bench_view_of_slots` 绕一圈写回——同样的占位件保真缺陷，直构化即修复。
**要求：§5/§3 的「零行为变化」改为「零策略行为变化 + sim 记录保真两处偏差显式修复」，偏差列入阶段验收（先补占位件在席 + 装备在席的 sim 锁再改，防「修复」变「回归」）。**

---

## Minor

### m1. §2 退役符号清单不完备
未列：`deployed_place` / `bench_from_compact` / `deployed_from_compact` / `pad_bench` / `pad_deployed` / `bench_occupied_slot_nos`（cw_exec_state.py:248-398，签名全部吃 BenchChar 表，tracked 迁移时一并定型或退役）；`_apply_row_to_char`（见 M3）；`unit_rows_to_deployed` / `deployed_slots_to_rows`（cw_game_state.py:1530,1574——容器↔帧形转换对，上报族与 sim 合成口在用，帧退役后前者的存在意义需裁决）。

### m2. position_pref 派生指针有误导风险
§2「经注册表按 char_id 派生」若被实施者读成 `get_role_position`（cw_factions.py:116——全局 character_const 按命途的近似，docstring 自证「货币战争实际站位以实机为准，命途只是近似」，且入参域是全局角色 id 非 CW 花名册名）会派生错。CW 正确单一源 = `get_char(name).position_pref()`（cw_chars.py:40-44，含 flex→back 归一）。建议 design.md 点名 CW 注册表函数。

### m3. 死代码删除的连带注释/契约面
`cw_registry.py:75` 注释宣称 star_weighted_copies 为「唯一加权实现」（实际零调用）；`kernel/cw_vocab.py:14-33`「推演内核正式类型 = CwSimFrame」的终态消费面声明、`docs/develop/.../game_state/fields.md §9` 帧↔容器映射契约正本，均随帧退役需同批处理，否则留下指向已删类型的正本文档。

### m4. inventory 量级复核（对 §4 的数字对账）
BenchChar：src 244 行 + 测试仓 183 行；CwSimFrame：src 91 行 + 测试仓 87 行（18 文件）；bench_place/_merge_bench/换形函数族 src 152 行。§4「96 文件/~880 引用」量级成立；其中相当比例是注释与死函数，实改面小于申报——对排期是利好，不构成缺口。

---

## 四不变量测试锁指认（§3 逐条）

| 不变量 | 锁 | 判定 |
|---|---|---|
| 1. 合并语义（≥3 升星/素材清空/装备继承/连锁不动点） | 连锁回调：`test_cw_merge_step_callback.test_on_step_fires_once_per_merge_level`；升星直写判定：`test_cw_game_state_consume.test_detect_merge_upgrade_signature`、`test_merge_projection_direct_write_and_observe_wins`；买牌合成投影：`test_cw_shop_projection_logic.test_merge_buy_single_report_two_forms`、`test_full_bench_merge_buy_k`；满栏吸收：`test_cw_overflow_gate.test_sellbench_overflow_logic_state_absorbs_card`、`test_overflow_absorb_syncs_tracked`；晶矿支载体链：`test_cw_collect_ore_rand.test_char_branch_bench_carrier_chain` | **装备继承载体腿无锁（M1）**，其余有 |
| 2. 占位件三防线 | 卖恒拒：`test_cw_sell_item_predicate` 全文件（凑息/筹资两通道行为锁）；恒占 1 席：`test_cw_unified_action_2c.test_bench_slot_bookcard_kind_roundtrip_as_item_placeholder`（9−2=7 占席派生）、`test_cw_seat_recoverable_narrow.test_placeholder_full_bench_refresh_blocked`；kind 保留（本迭代修复对象）：`test_cw_collect_ore_rand.test_char_reward_preserves_item_slot_kinds`、`test_cw_unified_action_2c.test_entry_box_tome_arms_read_benchview_kind` | **部署恒 held 腿无锁（M2）**，其余有 |
| 3. 随机态采样链 | `test_cw_collect_ore_rand` 全套（test_gold_branch_write_sequence 写序/test_char_branch_merge_dual_domain 双域组/test_sampler_support_set_and_reproducibility 重现性/test_multi_point_full_bench_skip/test_none_domains_skip_and_level_unread/test_bench_unobserved_rejects_whole_batch/test_sim_dispatch_intercepts_and_counts_uses 流键）；基座：`test_cw_game_state.test_write_logic_rand_and_observe_random_outcome`、`test_any_logic_rand_truth_table` | 有，充分 |
| 4. 席满即止/逐点推演/None 域跳写 | 席满即止：`test_cw_shop_projection_logic.test_buy_rejected_when_full_and_no_merge`、`test_cw_collect_ore_rand.test_multi_point_full_bench_skip`、`test_cw_ore_bench_free`、`test_cw_seat_recoverable_narrow.test_placeholder_full_bench_refresh_blocked`；None 域跳写：`test_cw_shop_projection_logic.test_none_gold_domain_skip`、bench 写门（test_cw_game_state.py:545 区）、`test_cw_collect_ore_rand.test_bench_unobserved_rejects_whole_batch` | 「逐点推演」无独立命名锁，靠 merge 链 on_step + 投影直锁族间接覆盖，判部分 |

## 三大攻面复核结论（审查要求 1）

- **(a) CwSimFrame**：能否 T-4 一次删干净 = 能，但前提是把测试种子层（18 文件 + `_cw_helpers` 三件套 + M1 锁保形）纳入同一提交单元（M4）。背后**没有**序列化/重放契约——schema.py 已容器委托、cw_replay 已容器恢复、旧档案 dict 宽容读；剩下的深消费全是死函数与注释。
- **(b) 策略层 tracked 快照**：mandate_v1 判定输入 = `bench_slots_of(gs)` 读口产物（BenchChar 槽位表，entry.py:575-621、mandate.py:311,2265-2266、shop.py:483,882-1050）；另有一个真正的容器内 BenchChar 宿主 = `tracked_books`（策略禁读，写端 = reconcile/动作随动）——后者是 B1 的核心。shop.py:1967,2190,2361 的候选 BenchChar 构造（faction 注册表派生 + position_pref='back'）在容器形状下平移为候选 Unit，无实质风险。别名面 = tracked 表就地变异（pad/place/merge 原地）+ 快照靠 snapshot_copy 断别名（buy_card.py:158-161）；容器化后 frozen Unit + 构造点新帧纪律承接，§6 风险 2 的评估成立。
- **(c) 观察链**：纯 CV 层产 `list[BenchChar]`（cw_identity_obs.identify_slots:341-472，faction/position_pref 构造期已注册表派生；battle_prep_recognizer.py:114-116 三字段同形，其 extras_doc 字符串 :137 还向消费方声明了 BenchChar dict 形状——T-5 需同步改声明）；映射层 `bench_view_from_obs`（item_kind_by_slot 细分占位 kind）与 `deployed_rows_from_obs` 在写门转容器形状。T-5 直产 = 识别器直接产 BenchSlot/Unit 行，方向成立；占位件槽号集（read_supply_boxes/read_tomes/find_bookcards）从「事后拼 item_kind_by_slot」改为「识别期定 kind」即可，无隐藏契约。

## 通过面（设计成立的部分，简列）

1. 动机诊断正确：三处实锁暴露确为换形口信息销毁（buy_card.py:140,166 与 swap_deploy.py:80 经 `bench_view_of_slots` 写回降级 supply_box；collect_ore.py:62 注释自证「恒降级」）。
2. 容器终态形状已被观察/记录层先行验证：BenchView/BenchSlot/Unit frozen（cw_game_state.py:562-600）、kind 五分类在 obs 写端已建档（bench_view_from_obs + item_kind_by_slot，cw_game_state.py:1425-1457）。
3. sim 引擎本体已容器直写（cw_sim_base.py SimEngineV2 签名体系；cw_sim_actions.apply_player_action 委托上报函数族），T-4 实际剩余面 = nodes/opening/equips/pool 四处中间形，比「sim 推进全改」的表述小。
4. 容器读口族已建齐（back_capacity_of/deployed_count_of/front_count_of/back_count_of/max_units_of，cw_game_state.py:3991-4040），T-3 策略迁移有现成落点；deploy_logic 的羁绊派生本就走注册表（`get_char(ch).factions`，cw_deploy_logic.py:200,297-301,516-519 等），faction 字段的依赖面比 §6 担心的小。
5. 阶段顺序 T-3（策略）→ T-4（sim）→ T-5（观察）合理：策略判定已容器直读（黑板批 3.5 已清），sim 与观察互不依赖，T-5 最后做不影响前序——前提是 B1 的闭合集先修订。
