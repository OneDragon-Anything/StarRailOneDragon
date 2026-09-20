# BenchChar 退役·计算层收编容器形状（benchchar-retirement）迭代设计

> 迭代目标 = **退役 BenchChar 角色形条目**，全库备战席/上阵位计算统一容器形状：bench = `BenchView`/`BenchSlot`（五分类 kind），deployed = `Unit` 行（front_row/back_row）。三个换形函数（`bench_slots_of`/`bench_slots_to_legacy`/`bench_view_of_slots`）随往返消失。**无兼容层**：不设双路径、不设过渡字段、**禁换形函数续命**（任何消费面不许靠换形过渡，直接改形状——对抗审 B1 裁定）。
> 状态 = 设计修订轮（首轮对抗审 blocker×1/major×5/minor×4 已收编，待复审确认后开工 T-1）。读者 = 无会话历史的工程师/智能体，照阶段执行，勿重设计。路径根 = `src/sr_od/application/currency_war/`；测试仓 = `sr-od-test/`。

## 1. 动机（根因）

双形状并存使 `bench_slots_to_legacy`（BenchView→BenchChar）成为**信息销毁点**：占位件 kind 三分类（tome/bookcard/supply_box）被压成布尔 `is_item_slot`，写回被迫降级 supply_box——collect_ore/buy_card/swap_deploy 三处实锁暴露（OpenTome 找不到典籍）。修信息丢失的正确层 = 消灭换形本身，而非在换形口补救。容器形状是唯一能表达占位件五分类的形状（BenchChar 天然装不下），终态必然单形状；本迭代完成容器化迁移的计算层收编（观察/记录层已在此前批次完成）。

## 2. 终态判定

- **bench 计算形状** = `BenchView`/`BenchSlot`（kind ∈ unit/tome/bookcard/supply_box/empty）。占位件判定 = `kind ∈ ('tome','bookcard','supply_box')`（布尔 `is_item_slot` 退役）。
- **deployed 计算形状** = `front_row`/`back_row` 的 `list[Unit]`（容器现值直接算；10 槽表语义保留在需要处按行下标派生）。
- **faction/position_pref 不入形状**：部署装配需要时经注册表按 char_id 派生（单一源 = `get_char(char_id).position_pref()`，勿用全局 get_role_position——对抗审 R3；现 `bench_slots_to_legacy` 同款派生搬进消费点）。
- **退役符号**：`BenchChar`、`snapshot_copy`、`bench_place`（容器版重写）、`bench_slots_of`、`bench_slots_to_legacy`、`bench_view_of_slots`、`_merge_bench` 旧签名、`deployed_place`/`_apply_row_to_char`/`unit_rows_to_deployed`（随形状退役或容器化重写，对抗审 R3）、`CwSimFrame`（序列化/重放契约已先行切断：`serialize_state` 委托 `full_state_snapshot`、`cw_replay` 走 `restore_state_snapshot`；剩余深消费 `economy_score`/`star_weighted_copies`/`state_equips_multiset` 全仓零调用 = 死函数随删）。
- **tracked_books 迁移（对抗审 B1 核心）**：`GameState.tracked_books`（cw_game_state.py，`list[BenchChar|None]`，容器内 BenchChar 大本营）改存 **BenchView 同构槽位快照**（冻结直存，§2 快照纪律）；读写端横跨 cw_reconcile/prep_actions/cw_screen_prep/cw_screen_buy_cards/cw_op_equip_all/cw_deploy_move_action/sell_bench/wear_equip 等 10+ 文件，全数入 T-1 闭合集。deployed 侧快照形状同批声明（对抗审 R2）：ADR-0392 保洞语义与 deployed_idx 坐标恒稳（行下标基不变），禁借迁移改索引语义。
- **`mutate_bench_deployed`（cw_vocab）链**：实机消费 = `operations/cw_op/cw_buy_card_action.py`（tracked 同步，2026-09-09 双响事故修复写入点）+ `buy_card.py` 升星腿——随计算层同批改容器形状，**禁用换形续命**。
- **快照/别名纪律**：冻结形状（BenchView/BenchSlot/Unit frozen）直存快照；equips 可变 list 的别名面在构造点保证「每帧新构造」，tracked 快照持有冻结壳即可。

## 3. 不变量（语义逐位不变，禁顺带改行为）

1. 合并语义：同名同星 ≥3 全场域（bench+deployed）→ 升星 +1、素材清空、装备继承载体、连锁到不动点（`_merge_bench` 现契约）。
2. 占位件三防线：恒占 1 席（席满守卫计入）、卖恒拒、部署恒 held。
3. 随机态采样链（logic-rand-sampling）写序/evidence/组语义不变——只换工作形状。
4. 席满即止、逐点推演、None 域跳写等既有锁全绿。
5. **开拓者形态归一**（对抗审 M3）：容器行写（front_row/back_row）经 `_apply_row_to_char` 同源的归一口——swap 上报有归一、deploy_move 上报缺归一为**既有不对称缺陷**，随迁移统一归一点并申报修复（弄丢即重现 cw_chars.py 登记的欢愉/记忆计数事故）。

**T-0 前置锁（对抗审 M1/M2，翻签名前先锁现状语义）**：
- 装备继承载体锁（全测试仓现无 merge 装备继承断言——`merge_simulate.py` 装备继承段是重写对象，先锁后改）；
- 部署恒 held 锁（`test_cw_sell_item_slot_predicate.py` 明文申报防线归 review，`cw_deploy_logic.py` 部署伪槽段 T-3 改 kind 口无回归网——先补）；
- sim 保真修复对照凭据（两处偏差修复前后 sim 记录对照，T-1+T-2 提交说明附，对抗审 R5）。

## 4. 面清单（inventory 2026-09-20，96 文件/~880 引用）

大头：`kernel/cw_game_state.py`(72)、`kernel/cw_merge_simulate.py`(42)、`kernel/cw_exec_state.py`(37)、`kernel/cw_vocab.py`(30, CwSimFrame)、`kernel/cw_deploy_logic.py`(29)、`obs/cw_identity_obs.py`(29)、策略层 mandate_v1(mandate/shop/predicates/sell_gate/criteria/proof/bridge ~90)、`kernel/cw_action_report/*`(~45)、`sim/*`(~45)、`kernel/cw_economy.py`/`cw_bench_equips.py`/`cw_intention.py` 等；测试仓 ~50 文件。

## 5. 阶段（账本 T-0..T-6，逐阶段测试全绿；T-0 先锁后改）

- **T-0 前置锁**：装备继承载体锁 + 部署恒 held 锁 + 开拓者归一现状锁（先锁现状行为，翻签名后作为不变量哨兵）。
- **T-1+T-2（同一提交单元，闭合集 = 全部直调方，禁换形续命）**：`bench_place`/`_merge_bench`/`mutate_bench_deployed` 改吃 `BenchView` + 行 Unit；9 个上报函数 + `tracked_books` 全部读写端（10+ 文件，§2 清单）+ `operations/cw_op/cw_buy_card_action.py` tracked 同步 + **sim 两处 `bench_place` 直调**（`cw_sim_nodes.py`/`cw_sim_opening.py`，提前入单——留到 T-4 会打破逐阶段全绿）同批改；collect_ore 删 `_bench_view_keep_items` 本地补丁（换形口随往返退役自然消失）。
- **T-3 部署/卖/策略判定层**：`cw_deploy_logic`、`sell_gate`、mandate_v1 判定读容器形状；position_pref 注册表派生落消费点；开拓者归一统一（§3.5 申报）。
- **T-4 sim 帧退役**：`CwSimFrame` 删除 + 测试种子层改造（`_cw_helpers.cw4_feed`/`cw4_box` → `synthesize_from_game_state` 装箱，87 处/18 文件；**M1 投影锁骑在被删种子通道上，锁语义逐字节保形**）+ 死函数删（`economy_score`/`star_weighted_copies`/`state_equips_multiset`）。**申报修正（对抗审 M5）**：非「零行为变化」——sim 中间形往返现存两处保真偏差随直构化修复（`cw_sim_nodes.py` 丢占位件槽+丢 Unit.equips；`cw_sim_equips.py` 丢占位件槽），正确申报 = **零策略行为变化 + 两处 sim 记录保真偏差显式修复**；修复落点裁定（对抗审 R1）= place_bench_unit_placeholder 容器原生重写的自然写法即含保真修复，落在 T-1+T-2（申报随之移位），实施提交说明写明，禁刻意复刻丢弃行为。
- **T-5 观察链直产**：`cw_identity_obs`（SIFT 产 list[BenchChar] 段）/`battle_prep_recognizer`（extras_doc 字符串声明的 BenchChar dict 形状同步改）/observe spec 门直产 BenchView（`bench_view_from_obs`/`item_kind_by_slot` 随中间形消失）。
- **T-6 收尾退役**：删 BenchChar/snapshot_copy/换形函数/CwSimFrame 与全部引用；全量 grep 归零；L3；正本更新（fields.md §3.2.5/§4.2/§9 帧↔容器映射契约、action-logic-state.md、projection_contract.md、recognizer extras_doc、cw_registry.py 占位注释同步——对抗审 R2）。

## 6. 风险

- faction/position_pref 派生点遗漏 → 部署装配行为漂移（锁：transfer_golden + 部署族测试 + T-0 锁）。
- 开拓者形态归一遗漏 → 欢愉/记忆羁绊计数事故重现（cw_chars.py 在案；§3.5 统一归一点 + 锁）。
- tracked 快照别名（equips list 共享）→ 仅测试网偶发假差（构造点新帧纪律不变）。
- 测试种子层改造（87 处/18 文件）面广 → M1 投影锁语义逐字节保形为先决。
- 体量：逐文件点名 add；每阶段独立 commit。
