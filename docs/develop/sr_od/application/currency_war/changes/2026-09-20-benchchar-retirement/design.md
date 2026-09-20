# BenchChar 退役·计算层收编容器形状（benchchar-retirement）迭代设计

> 迭代目标 = **退役 BenchChar 角色形条目**，全库备战席/上阵位计算统一容器形状：bench = `BenchView`/`BenchSlot`（五分类 kind），deployed = `Unit` 行（front_row/back_row）。三个换形函数（`bench_slots_of`/`bench_slots_to_legacy`/`bench_view_of_slots`）随往返消失。**无兼容层**：不设双路径、不设过渡字段（用户 2026-09-20 裁决：一次性改完）。
> 状态 = 实施中。读者 = 无会话历史的工程师/智能体，照阶段执行，勿重设计。路径根 = `src/sr_od/application/currency_war/`；测试仓 = `sr-od-test/`。

## 1. 动机（根因）

双形状并存使 `bench_slots_to_legacy`（BenchView→BenchChar）成为**信息销毁点**：占位件 kind 三分类（tome/bookcard/supply_box）被压成布尔 `is_item_slot`，写回被迫降级 supply_box——collect_ore/buy_card/swap_deploy 三处实锁暴露（OpenTome 找不到典籍）。修信息丢失的正确层 = 消灭换形本身，而非在换形口补救。容器形状是唯一能表达占位件五分类的形状（BenchChar 天然装不下），终态必然单形状；本迭代完成容器化迁移的计算层收编（观察/记录层已在此前批次完成）。

## 2. 终态判定

- **bench 计算形状** = `BenchView`/`BenchSlot`（kind ∈ unit/tome/bookcard/supply_box/empty）。占位件判定 = `kind ∈ ('tome','bookcard','supply_box')`（布尔 `is_item_slot` 退役）。
- **deployed 计算形状** = `front_row`/`back_row` 的 `list[Unit]`（容器现值直接算；10 槽表语义保留在需要处按行下标派生）。
- **faction/position_pref 不入形状**：部署装配需要时经注册表按 char_id 派生（现 `bench_slots_to_legacy` 同款派生搬进消费点）。
- **退役符号**：`BenchChar`、`snapshot_copy`、`bench_place`（容器版重写）、`bench_slots_of`、`bench_slots_to_legacy`、`bench_view_of_slots`、`_merge_bench` 旧签名、`CwSimFrame`（sim 观测已 gs 化，帧为残留）。
- **快照/别名纪律**：冻结形状（BenchView/BenchSlot/Unit frozen）直存快照；equips 可变 list 的别名面在构造点保证「每帧新构造」，tracked 快照持有冻结壳即可。

## 3. 不变量（语义逐位不变，禁顺带改行为）

1. 合并语义：同名同星 ≥3 全场域（bench+deployed）→ 升星 +1、素材清空、装备继承载体、连锁到不动点（`_merge_bench` 现契约）。
2. 占位件三防线：恒占 1 席（席满守卫计入）、卖恒拒、部署恒 held。
3. 随机态采样链（logic-rand-sampling）写序/evidence/组语义不变——只换工作形状。
4. 席满即止、逐点推演、None 域跳写等既有锁全绿。

## 4. 面清单（inventory 2026-09-20，96 文件/~880 引用）

大头：`kernel/cw_game_state.py`(72)、`kernel/cw_merge_simulate.py`(42)、`kernel/cw_exec_state.py`(37)、`kernel/cw_vocab.py`(30, CwSimFrame)、`kernel/cw_deploy_logic.py`(29)、`obs/cw_identity_obs.py`(29)、策略层 mandate_v1(mandate/shop/predicates/sell_gate/criteria/proof/bridge ~90)、`kernel/cw_action_report/*`(~45)、`sim/*`(~45)、`kernel/cw_economy.py`/`cw_bench_equips.py`/`cw_intention.py` 等；测试仓 ~50 文件。

## 5. 阶段（账本 T-1..T-6，逐阶段测试全绿）

- **T-1+T-2（同一提交单元，不可分）kernel 算法 + 上报函数容器化**：算法改签名则全部直调方必须同批改，拆开任何一步测试不绿——`bench_place`/`_merge_bench` 改吃 `BenchView` + 行 Unit，9 个上报函数工作副本直用 BenchView（collect_ore 删 `_bench_view_keep_items` 本地补丁，共享口随换形退役自然消失）；`cw_exec_state` 占位件判定改 kind 口。
- **T-3 部署/卖/策略判定层**：`cw_deploy_logic`、`sell_gate`、mandate_v1 判定读容器形状；position_pref 注册表派生落消费点。
- **T-4 sim 帧退役**：sim 推进/装备/节点/商店/开局全改容器形状；`CwSimFrame` 删除；流键/披露面零变化。
- **T-5 观察链直产**：`cw_identity_obs`/recognizer/observe spec 门直产 BenchView（`bench_view_from_obs`/`item_kind_by_slot` 随中间形消失）。
- **T-6 收尾退役**：删 BenchChar/snapshot_copy/换形函数/CwSimFrame 与全部引用；全量 grep 归零；L3。

## 6. 风险

- faction/position_pref 派生点遗漏 → 部署装配行为漂移（锁：transfer_golden + 部署族测试）。
- tracked 快照别名（equips list 共享）→ 仅测试网偶发假差（构造点新帧纪律不变）。
- CwSimFrame 残留消费面比申报多 → T-4 先 grep 清点再动。
- 体量：逐文件点名 add；每阶段独立 commit。
