# BenchChar 退役·计算层收编容器形状（benchchar-retirement）迭代设计

## 0. 元信息

- 迭代目标：退役 BenchChar 角色形条目，全库备战席/上阵位计算统一容器形状（bench = `BenchView`/`BenchSlot` 五分类 kind；deployed = `front_row`/`back_row` 的 `Unit` 行）；部署落位决策权同步归位策略层。**无兼容层**：不设双路径、不设过渡字段、换形函数禁续命（任何消费面不许靠换形过渡，直接改形状）。
- 状态：定稿
- 文档清单：[landing.md](landing.md)（阶段拆分与验收；阶段小节 = 账本任务唯一源）

## 1. 问题与动机（根因）

**根因一（表示层）：双形状并存使 `bench_slots_to_legacy`（BenchView→BenchChar）成为信息销毁点。** 占位件 kind 三分类（tome/bookcard/supply_box）被压成布尔 `is_item_slot`，写回被迫降级 supply_box——collect_ore/buy_card/swap_deploy 三处实锁暴露（OpenTome 找不到典籍）。BenchChar 天然装不下占位件五分类，终态必然单形状；消灭换形本身即修根。本迭代完成计算层收编（观察/记录层已在此前批次完成）。

**根因二（层次错位，随同一迁移面归位）：部署落位决策权长在框架层。** 「上场角色去哪一排、落哪个槽」是策略知识（cw_comps.py 已有 comp 站位覆盖概念），现状却由 kernel `assign_deploy_slots` 定排、执行边按「该排首空位」定槽——策略侧对落位无发言权；且备战候选的注册表 position_pref 在此链路恒被丢弃（候选恒按后排路由，前排保证规则的「真 front 候选提前」分支永不触发）。游戏允许任意排布（含空前排、含拖到有人槽=交换），落位全是自由度，全归策略。借同一重写面归位，避免同段代码翻动两次。

明确不解决：策略选人/落位算法本身的优化（只迁归属与形状，不改策略意图）；mandate_v1 之外的策略实现适配（现役仅一套）。

## 2. 方案

### 2.1 终态形状

- **bench 计算形状** = `BenchView`/`BenchSlot`（kind ∈ unit/tome/bookcard/supply_box/empty）。占位件判定 = `kind ∈ ('tome','bookcard','supply_box')`（布尔 `is_item_slot` 退役）。
- **deployed 计算形状** = `front_row`/`back_row` 的 `list[Unit]`（容器现值直接算；10 槽表语义保留在需要处按行下标派生）。
- **faction/position_pref 不入形状**：消费点经注册表按 char_id 派生（单一源 = `get_char(char_id)` 的 `factions`/`position_pref()`，禁全局 get_role_position）。faction 消费面三类，逐类派生口径：
  - 部署装配（发射载荷 faction 字段）：容器槽位现取（现状不变）；
  - 板面阵营计数/体系卡身份（cw_system_cards）：注册表派生，未知名 = `'?'`（与现 `bench_slots_to_legacy` 派生式同式）；
  - 羁绊（cw_bond_equips/board_by_row）：按行归属 + 注册表派生，开拓者形态归一随迁（§3 不变量 5）。
- **(排, 排内槽号) ↔ 槽位表下标换算单一源** = `deployed_row_slot`/`deployed_idx_of`（存活保留，坐标换算与形状无关）。

### 2.2 落位决策权归策略层

裁决：**谁上场、去哪一排、落哪个槽，全部由策略实现决定；框架在落位上零决定**——不定排、不选槽、不荐首空位、不判断占位。

- 框架保留三样：容器状态（行列现值，策略自行遍历判空——容器形状下空槽直接可见，无专用「查空槽」设施）、动作执行（载荷坐标 → 屏幕拖拽）、记录（遥测/对局档案）。
- **拖拽语义 = 游戏规则**：目标槽空 = 放置，有角色 = 交换交互。执行层照单拖拽：不视占位为异常、禁静默换槽（换槽 = 框架又在做落位决定）。执行层唯一失败形态 = 拖拽未生效（画面无响应），走 op 既有失败处理。
- **载荷契约**：`CwActionDeployMoveParam` 增 `to_slot`（排内 1 基画面槽号），与 `to_row` 合成完整落位意图；执行器删除「执行坐标边现读首空位」，按 (to_row, to_slot) 坐标翻译拖点。`CwActionSwapDeployParam`（bench↔deployed 对调）现契约保留。
- **mandate_v1 内聚落位策略**（策略代码）：上场人选、每人的排（comp 站位覆盖 > 注册表 position_pref 派生 > back 兜底）、槽位选择（遍历容器行列现值自定）；原 kernel 规则中的「前排保证」（前排全空时保证前排有角色）作为策略规则随迁 mandate。
- **选人同批迁策略**：`select_deployments`/`select_deployments_reasoned` 属策略决策，随落位归权迁入 mandate_v1，kernel 版退役；出战链不再装配选人输入。
- **出战链**（cw_loop `_battle_chain_deploy_moves`，恢复局同步步/达标臂共用）：改为调用策略层部署计划单一源（mandate_v1 暴露计划函数），不再自带 select+assign 装配。
- **迁移过渡口径**：P1 tracked 翻形至 P2 执行器改造之间，执行链对空槽/落位的读数一律经 §2.1 下标换算单一源（`deployed_row_slot`/`deployed_idx_of`）派生，禁对快照条目 getattr 柔取旧字段（防翻形期静默漂移，落锁入 P1）。
- **sim 语义**：sim 引擎应用部署动作 = 忠实建模游戏拖拽语义（空=放置/占=交换），禁发明私有「占位拒绝」规则。sim 买卡入席 = 游戏自动放置规则（首空槽），非策略落位——`bench_place` 容器原生重写后保留（§2.4）。

**行为变化申报（本迭代全部行为变化，共两项）**：

1. mandate 落位行为变化：备战候选排路由从「恒按后排」变为注册表派生真实生效，槽位由策略显式指定。验证 = sim A/B 对照（落位改前/改后对局指标）+ 新锁（注册表前排角色在前排有空时被排到前排）。
2. sim 记录保真修复两处（非策略行为变化）：`cw_sim_nodes` 丢占位件槽+丢 Unit.equips、`cw_sim_equips` 丢占位件槽——随容器直构自然修复，禁刻意复刻丢弃行为；修复前后 sim 记录对照留凭据。

### 2.3 tracked_books 迁移形状（定稿）

- `TrackedBooks.bench` = `list[BenchSlot | None]`，定长 9（ADR-0316 保洞语义不变：卖出/上阵置 None 不移位）。
- `TrackedBooks.deployed` = `list[Unit | None]`，定长 10（ADR-0392 保洞语义不变）：**表下标 = deployed_idx 动作坐标，恒稳**；排归属由下标派生（0-3 前排 / 4-9 后排）；(排, 排内槽号) ↔ 下标换算经 §2.1 单一源。禁借迁移改索引语义。
- 快照/别名纪律：冻结形状直存快照；equips 可变 list 的别名面在构造点保证「每帧新构造」，tracked 快照持有冻结壳。
- 读写端闭合集（全部入 P1）：cw_reconcile、prep_actions、cw_screen_prep、cw_screen_buy_cards、cw_op_equip_all、cw_deploy_move_action、sell_bench、wear_equip 等 10+ 文件。

### 2.4 退役符号清单（全量裁决）

**删除（随形状退役）**：

- 形条目：`BenchChar`、`snapshot_copy`、`CwSimFrame`
- 换形/槽位表族：`bench_slots_of`、`deployed_slots_of`、`bench_slots_to_legacy`、`bench_view_of_slots`、`unit_rows_to_deployed`、`deployed_slots_to_rows`、`bench_from_compact`、`deployed_from_compact`、`pad_bench`、`pad_deployed`、`bench_clear`、`deployed_clear`、`deployed_place`、`_apply_row_to_char`、`iter_occupied`、`iter_occupied_deployed`、`iter_deployed_slots`、`bench_occupied`、`deployed_occupied`
- 落位权归策略：`assign_deploy_slots`、`empty_deploy_slots`
- 选人迁策略（kernel 版）：`select_deployments`、`select_deployments_reasoned`
- sim 帧通道：`synthesize_from_game_state`、`feed_sim_truth`
- 换形杂项：`_card_to_bench`（ShopCard→BenchChar 换形，含其 position_pref='back' 缺省——与落位旧病灶同源；买卡入席改经 bench_place 直落 BenchSlot）
- 死函数（全仓零调用，含测试仓，2026-09-20 核实）：`economy_score`、`star_weighted_copies`、`state_equips_multiset`、`rebuild_deployed_from_board`

**容器原生重写保留（签名换形状，语义不变）**：

`bench_place`（买卡入席游戏规则：首空槽放置）、`bench_occupied_slot_nos`（容器形输入）、`bench_slots_healthy`（形状无关，原样保留）、`deployed_slot_no`/`deployed_idx_of`/`deployed_row_slot`（坐标换算单一源）、`board_by_row`（容器行输入重写）、`board_unique_key`（容器形重写）、`mutate_bench_deployed`（容器形状重写；实机消费 = operations/cw_op/cw_buy_card_action.py tracked 同步 + buy_card.py 升星腿，随 P1 同批改，禁换形续命）、`mutate_bench_deployed_local`（容器形状重写，随 `mutate_bench_deployed` 同批）。

**字段映射约定（全部消费面统一遵循）**：BenchChar.slot → 容器表下标/行内槽号（§2.1 换算单一源）；BenchChar.faction/position_pref → 注册表派生（§2.1 三类口径）；`is_item_slot=True` → `kind ∈ ('tome','bookcard','supply_box')`；「占用」判定 `is not None` → `kind == 'unit'`（BenchView 下 empty 槽 ≠ 占用）。

### 2.5 测试种子纪律

- **名字表达**：测试想要某阵营/前后排偏好，通过挑选对应注册表角色名获得（前排偏好 = 种注册表前排角色名；未知阵营 = 种注册表外名字）；占位件 = kind 直种。派生是唯一源，生产不可达的状态不锁。
- **无注入口**：种子构造不提供绕过注册表派生的覆盖参数。
- **载体**：`CwSimFrame`/`synthesize_from_game_state`/`feed_sim_truth` 退役后，测试经测试仓 builder 直写容器域（与观察链同写入口），不设帧→容器换形续命。
- 现状面（2026-09-20 实测）：测试仓 CwSimFrame 引用 87 处/18 文件、`BenchChar(` 直造 116 处/32 文件，全部入 P5 重写。

## 3. 不变量（语义逐位不变，禁顺带改行为）

1. 合并语义：同名同星 ≥3 全场域（bench+deployed）→ 升星 +1、素材清空、装备继承载体、连锁到不动点（`_merge_bench` 现契约）。
2. 占位件三防线：恒占 1 席（席满守卫计入）、卖恒拒、部署恒 held。
3. 随机态采样链（logic-rand-sampling）写序/evidence/组语义不变——只换工作形状。
4. 席满即止、逐点推演、None 域跳写等既有锁全绿。
5. 开拓者形态归一：容器行写（front_row/back_row）统一经同源归一口。swap 上报有归一、deploy_move 上报缺归一为既有不对称缺陷，随迁移统一并申报缺陷修复（弄丢即重现 cw_chars.py 登记的欢愉/记忆羁绊计数事故）。

**前置锁（P0 执行；翻签名前先锁现状语义，作为迁移后不变量哨兵）**：

- 装备继承载体锁：全测试仓现无 merge 装备继承断言（2026-09-20 核实），`cw_merge_simulate.py` 装备继承段是重写对象，先锁后改；
- 部署恒 held 锁：`test_cw_sell_item_slot_predicate.py` 明文申报防线归 review；cw_deploy_logic 部署伪槽段改 kind 口无回归网，先补；
- 开拓者归一现状锁：先锁 swap 有归一/deploy_move 缺归一的现状，翻签名后哨兵 §3.5 统一；
- sim 保真对照凭据：§2.2 行为变化申报第 2 项两处偏差的修复前后 sim 记录对照，P1 提交说明附。

## 4. 面清单（inventory 2026-09-20 实测）

词表 = §2.4 删除族 ∪ 重写保留族符号并集（rg：`BenchChar|bench_slots_of|deployed_slots_of|bench_slots_to_legacy|bench_view_of_slots|unit_rows_to_deployed|deployed_slots_to_rows|deployed_place|_apply_row_to_char|bench_from_compact|deployed_from_compact|assign_deploy_slots|empty_deploy_slots|CwSimFrame|snapshot_copy|bench_place|pad_bench|pad_deployed|iter_occupied|iter_deployed_slots|bench_occupied|rebuild_deployed_from_board|_card_to_bench|mutate_bench_deployed_local`）：

- src：704 处 / 60 文件；测试仓：381 处 / 42 文件。
- 大头：kernel/cw_game_state.py、kernel/cw_merge_simulate.py、kernel/cw_exec_state.py、kernel/cw_vocab.py、kernel/cw_deploy_logic.py、obs/cw_identity_obs.py、策略层 mandate_v1（mandate/shop/predicates/sell_gate/criteria/proof/bridge）、kernel/cw_action_report/*、sim/*。
- 外围消费面（易漏，须入阶段点名面）：cw_comps、cw_economy、cw_intention、cw_events、cw_system_cards、cw_board_by_row、cw_bench_equips、cw_equip_wear_plan、cw_effect_inventory、cw_line_switch、cw_launch_admission、cw_performance、cw_battle_calib、economy_cycle、telemetry/schema.py、flow.py、entry.py、shop.py、criteria/sell.py、statefn/predicates.py、operations/cw_loop.py、cw_screen_prep、cw_shop_action_ops、cw_screen_planner、sim/cw_sim_pool。

## 5. 分期

阶段拆分、文件面、依赖与验收判据的唯一源 = [landing.md](landing.md)。顺序：P0 前置锁 → P1 kernel 计算层容器化 → P2 落位载荷与执行面 → P3 策略落位实现与出战链 → P4 策略与 kernel 消费面 → P5 sim 帧退役与测试种子层 → P6 观察链直产 → P7 收尾退役 → P8 正本更新。逐阶段测试全绿；每阶段独立 commit，逐文件点名 add。

## 6. 风险

- 落位行为变化（§2.2 申报第 1 项）波及对局指标 → sim A/B 门先行为主，指标异常回退裁决再议。
- faction 派生点遗漏（§2.1 三类消费面）→ 装配/板面计数/羁绊逐类补锁。
- 开拓者形态归一遗漏 → 欢愉/记忆羁绊计数事故重现（cw_chars.py 在案；§3 不变量 5 归一口 + P0 现状锁 + P3 统一后锁）。
- tracked 快照别名（equips list 共享）→ 仅测试网偶发假差（构造点新帧纪律不变）。
- 测试种子层改造体量大（§2.5 现状面）→ M1 投影锁语义逐字节保形为先决。
- 体量：逐文件点名 add；每阶段独立 commit。
