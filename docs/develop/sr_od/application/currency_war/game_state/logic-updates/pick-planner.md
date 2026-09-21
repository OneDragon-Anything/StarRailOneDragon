# 骇入策划选择(PickPlanner)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一(机械确认链纪律正本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.4)。**两相上报**(银狼升星记账批 2026-09-20 推广批落地:发射相意图遥测 / 落地相证据闩分步,设计 = `changes/2026-09-20-yinlang-starup-accounting/design.md` §2.2)。

## 1. 动作是什么

银狼「我来当策划」二选一(画面 货币战争-银狼升星)点卡选中并确认。词表 = `kernel/cw_vocab.py::CwActionPickPlannerParam`(`PickOption` 子类:字段 `idx` = 候选下标 0 起、`reason` = 归因记录字段)。op 载体 = `operations/cw_op/cw_overlay_pick_action.py::CwActionPickPlannerOp`(体迁自 `cw_screen_yinlang.py::CwScreenYinLang._handle_overlay` 点卡确认尾段,替身缝 = 方法级桩保留;域 env = `OverlayPickExecEnv`)。

## 2. 逻辑态域集

**两相**(上报宿主 = `kernel/cw_action_report/pick_planner.py::report_action_pick_planner_param`,与 pick_invest 同构):

- **发射相**(evidence 缺省,CwActionPickPlannerOp 机械链发出后):意图遥测日志行,**容器零写**——确认未落地重走不重复;
- **落地相**(evidence = `EVIDENCE_OVERLAY_CLOSED`,消费面 = `CwScreenYinLang` 重入裁决出口「入口词『我来当策划』不在 = overlay 已关」):腿型分派应用一次,容器写域按腿:
  - **装备腿**:`equips` 入栏(`write_logic`)+ 获得后果链(`cw_effect_inventory.apply_equip_acquire_consequence`,命中后果表则送角色 → bench + 合成级联);未解析件名 → `equips` 值不变翻来源 + 留证行(禁猜);
  - **升费腿**:`bench`/`front_row`/`back_row` 变换窗三态(恰一枚 2★银狼LV.999 → 变 1★ + `lv999_cost_tier` 档行(现档+1,牌库改变的容器表达;档行时序 = 变换落行后、级联前)/ 多枚 → 值不变翻来源留证 / 零枚未观察 → fail-closed 留证响停)+ `merge_cascade_write` 级联;
  - **unknown**:零记账 + 留证行;**weaken**:零记账;
- **选中点几何**(避开卡内「详情」按钮区)归决策半 `_card_point` 单一源现算,经 `env.target` 传入。

## 3. 确定面转移规则(逐条)

1. **点卡选中**:mouse_move + click `env.target`(press_time = `op.CLICK_PRESS_TIME`;选中点避开卡内「详情」按钮区——点卡身上部,点错触详情面板的实证几何治理)→ 固定等待 1.2s(选中动画);
2. `op._confirm_pending = True`;
3. **确认机械交回** = `emit_overlay_confirm`(确认点 = `area_center`(op.ctx, '按钮-骇入确认', `CwScreenYinLang.CARD_AREA_SCREEN`)or `CwScreenYinLang.CONFIRM`;裁决词 = 全词「我来当策划」——短词「策划」在艺术字漏读时可能假通过);轮次结果经 `env.round_result` 旁路回传;
4. 详情面板防御已拆:面板若真弹出(点错所致)= 选中点几何治理域,后果归下一帧重入自愈——本屏分发即门,外循环按当前画面重分派(详情 overlay 族分支/本 op 重走链)。

## 4. 随机面

策划候选内容 = 随机面归观察;选择后果不记预期值。升费腿为确定面(档 +1 与变换窗输入均容器现算)。

## 5. 拒绝语义

零验证确认链:确认未落地不重试不判效——下一轮重入入口观察裁决(详情面板弹出同走重入);确认点 area 缺失走兜底常量(本屏在册例外派生模式)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionPickPlannerParam` / `PickOption`;`operations/cw_op/cw_overlay_pick_action.py::CwActionPickPlannerOp` / `OverlayPickExecEnv`;`operations/cw_screen/_overlay_confirm.py::emit_overlay_confirm`;`kernel/cw_obs_core.py::area_center`;`kernel/cw_action_report/pick_planner.py::report_action_pick_planner_param`(两相:发射相意图遥测 / 落地相腿型分派;`EVIDENCE_OVERLAY_CLOSED` 单一定义在 pick_invest);`kernel/cw_economy.py::effective_cost`(现档读口);`kernel/cw_game_state.py::lv999_cost_tier`(档字段,写端 = 本腿 + deploy_move 上阵变费腿)。

## 7. 语义验证

两相语义 = pick 族证据闩形态(action_ops §2.3);落地相容器写按腿分派(§2):装备腿/升费腿逐步落行,unknown/weaken 零记账。M1 投影直锁对象无(选择族形态锁 = test_cw_yinlang_phase32 三态/证据闩/档行断言族)。

## 8. 判例注记(发射期)

骇入策划 overlay 画面期;发射位 = 画面 op act 段经注册表工厂分派。

## 9. 依据

`operations/cw_op/cw_overlay_pick_action.py::CwActionPickPlannerOp` docstring(点卡几何/裁决词全词/面板防御拆除裁定);[flow/action_ops.md](../../flow/action_ops.md) §4.4(pick 族行);[fields.md](../fields.md) §3.4(事件选择域组;lv999_cost_tier 字段节);设计正本 = `changes/2026-09-20-yinlang-starup-accounting/design.md` §2.1/§2.2。
