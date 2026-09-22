# 骇入策划选择(PickPlanner)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一(机械确认链纪律正本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.5)。**即时单相上报**(用户裁定 2026-09-21 = [flow/action_ops.md](../../flow/action_ops.md) §1 增补 2:动作 op 确认点击后一口写完整效果逻辑态;发射/落地两相与证据闩已全域退役)。

## 1. 动作是什么

银狼「我来当策划」二选一(画面 货币战争-银狼升星)点卡选中并确认。词表 = `kernel/cw_vocab.py::CwActionPickPlannerParam`(`PickOption` 子类:字段 `idx` = 候选下标 0 起、`reason` = 归因记录字段)。op 载体 = `operations/cw_op/cw_pick_planner_action.py::CwActionPickPlannerOp`(体迁自 `cw_screen_yinlang.py::CwScreenYinLang._handle_overlay` 点卡确认尾段,替身缝 = 方法级桩保留;域 env = `OverlayPickExecEnv`)。

## 2. 逻辑态域集

**单相**(上报宿主 = `kernel/cw_action_report/pick_planner.py::report_action_pick_planner_param`,与 pick_invest 同构;`CwActionPickPlannerOp` 确认点击后调用,`leg_type`/`norm_item` 经 `OverlayPickExecEnv` 随派发透传):

- **条件腿 rider 先行**(上报内、腿型分派之前):欢愉契约在册时采样授予一枚条件腿单位(获得链 `gain_character`,evidence = `joy_conditional:<单位名>`;授予失败不阻塞腿型分派,调用点级 best-effort);
- 腿型分派容器写域按腿:
  - **装备腿**:`equips` 入栏(`write_logic`)+ 获得后果链(`cw_effect_inventory.apply_equip_acquire_consequence`,命中后果表则送角色 → bench + 合成级联);未解析件名 → `equips` 值不变翻来源 + 留证行(禁猜);
  - **升费腿**:`bench`/`front_row`/`back_row` 变换窗三态(恰一枚 2★银狼LV.999 → 变 1★ + `lv999_cost_tier` 档行(现档+1,牌库改变的容器表达;档行时序 = 变换落行后、级联前)/ 多枚 → 值不变翻来源留证 / 零枚未观察 → fail-closed 留证响停)+ `merge_cascade_write` 级联;
  - **unknown**:零记账 + 留证行(含弱化词且装备锚未命中的卡文落此——弱化兜底档已按原文二分法退役,静默零记账变响亮申报);
- **未路由腿型** = 终态兜底零写(reason = `unrouted_leg_zero_write`);
- **选中点几何**(避开卡内「详情」按钮区)归决策半 `_card_point` 单一源现算,经 `env.target` 传入。

## 3. 确定面转移规则(逐条)

1. **点卡选中**:mouse_move + click `env.target`(press_time = `op.CLICK_PRESS_TIME`;选中点避开卡内「详情」按钮区——点卡身上部,点错触详情面板的实证几何治理)→ 固定等待 1.2s(选中动画);
2. **确认机械交回** = `emit_overlay_confirm`(确认点 = `area_center`(op.ctx, '按钮-骇入确认', `CwScreenYinLang.CARD_AREA_SCREEN`)or `CwScreenYinLang.CONFIRM`;裁决词 = 全词「我来当策划」——短词「策划」在艺术字漏读时可能假通过);轮次结果经 `env.round_result` 旁路回传;
3. **确认点击后即时自上报**完整结果(单相一口写,见 §2);
4. 详情面板防御已拆:面板若真弹出(点错所致)= 选中点几何治理域,后果归下一帧外循环自愈——本屏分发即门,外循环按当前画面重分派(详情 overlay 族分支)。

## 4. 随机面

策划候选内容 = 随机面归观察;选择后果不记预期值。升费腿为确定面(档 +1 与变换窗输入均容器现算)。

## 5. 拒绝语义

零验证确认链:确认未落地不重试不判效——确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派(派发即终结,本访问零重入裁决;详情面板弹出同走外循环重分发);确认点 area 缺失走兜底常量(本屏在册例外派生模式)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionPickPlannerParam` / `PickOption`;`operations/cw_op/cw_pick_planner_action.py::CwActionPickPlannerOp` / `cw_overlay_pick_env.py::OverlayPickExecEnv`;`operations/cw_screen/_overlay_confirm.py::emit_overlay_confirm`;`kernel/cw_obs_core.py::area_center`;`kernel/cw_action_report/pick_planner.py::report_action_pick_planner_param`(即时单相:条件腿 rider 先行 + 腿型分派一口写);`kernel/cw_economy.py::effective_cost`(现档读口);`kernel/cw_game_state.py::lv999_cost_tier`(档字段,写端 = 本腿 + deploy_move 上阵变费腿)。

## 7. 语义验证

单相语义 = 确认点击后一口写腿型分派效果(§2):装备腿/升费腿逐步落行,unknown 零记账留证。M1 投影直锁对象无(选择族形态锁 = test_cw_yinlang_phase32 三态/单相即时上报/档行断言族)。

## 8. 判例注记(发射期)

骇入策划 overlay 画面期;发射位 = 画面 op act 段经注册表工厂分派,派发即终结交回。

## 9. 依据

`operations/cw_op/cw_pick_planner_action.py::CwActionPickPlannerOp` docstring(点卡几何/裁决词全词/面板防御拆除/即时单相上报);`kernel/cw_action_report/pick_planner.py` 模块头(单相写序:条件腿 rider 先行/equip/upgrade 三态/unknown 留证/unrouted 兜底);[flow/action_ops.md](../../flow/action_ops.md) §4.5(pick 族行);[fields.md](../fields.md) §3.4(事件选择域组;lv999_cost_tier 字段节)。
