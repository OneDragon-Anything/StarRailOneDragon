# 骇入策划选择(PickPlanner)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一(机械确认链纪律正本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.4)。

## 1. 动作是什么

银狼骇入策划 overlay 点卡选中并确认。词表 = `kernel/cw_vocab.py::CwActionPickPlannerParam`(`PickOption` 子类:字段 `idx` = 候选下标 0 起、`reason` = 归因记录字段)。op 载体 = `operations/cw_op/cw_overlay_pick_action.py::CwActionPickPlannerOp`(体迁自 `cw_screen_planner.py::CwScreenPlanner._handle_overlay` 点卡确认尾段,替身缝 = 方法级桩保留;域 env = `OverlayPickExecEnv`)。

## 2. 逻辑态域集

**容器 GameState 零写**——事件线选择非逻辑态通道([../action-logic-state.md](../action-logic-state.md) §6):

- **选择落地观察写端:现役无在册写端**——策划选择的落地域 = `kernel/cw_game_state.py::chosen_hack`(值 = 策划名),字段在册但**暂无画面建档与写入端**(`CwScreenPlanner` 不在 `REGISTERED_ACTORS`;选择落地不落账,归观察侧补档批);
- **确认到账 grant**:无(本类确认无登记面);
- 选中点几何(避开卡内「详情」按钮区)归决策半 `_card_point` 单一源现算,经 `env.target` 传入。

## 3. 确定面转移规则(逐条)

1. **点卡选中**:mouse_move + click `env.target`(press_time = `op.CLICK_PRESS_TIME`;选中点避开卡内「详情」按钮区——点卡身上部,点错触详情面板的实证几何治理)→ 固定等待 1.2s(选中动画);
2. `op._confirm_pending = True`;
3. **确认机械交回** = `emit_overlay_confirm`(确认点 = `area_center`(op.ctx, '按钮-骇入确认', `CwScreenPlanner.CARD_AREA_SCREEN`)or `CwScreenPlanner.CONFIRM`;裁决词 = 全词「我来当策划」——短词「策划」在艺术字漏读时可能假通过);轮次结果经 `env.round_result` 旁路回传;
4. 详情面板防御已拆:面板若真弹出(点错所致)= 选中点几何治理域,后果归下一帧重入自愈——本屏分发即门,外循环按当前画面重分派(详情 overlay 族分支/本 op 重走链)。

## 4. 随机面

策划候选内容 = 随机面归观察;选择后果不记预期值。

## 5. 拒绝语义

零验证确认链:确认未落地不重试不判效——下一轮重入入口观察裁决(详情面板弹出同走重入);确认点 area 缺失走兜底常量(本屏在册例外派生模式)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionPickPlannerParam` / `PickOption`;`operations/cw_op/cw_overlay_pick_action.py::CwActionPickPlannerOp` / `OverlayPickExecEnv`;`operations/cw_screen/_overlay_confirm.py::emit_overlay_confirm`;`kernel/cw_obs_core.py::area_center`;`kernel/cw_game_state.py::chosen_hack`(在册无写端);`operations/cw_screen/cw_screen_planner.py::CwScreenPlanner`(替身缝/选中点几何单一源)。

## 7. 语义验证

容器零写语义 = 「事件线选择非逻辑态通道」契约;选择落地无容器写端(§2 申报)= 真值暂由画面分发重入观察承载。无 M1 投影直锁对象。

## 8. 判例注记(发射期)

骇入策划 overlay 画面期;发射位 = 画面 op act 段经注册表工厂分派。

## 9. 依据

`operations/cw_op/cw_overlay_pick_action.py::CwActionPickPlannerOp` docstring(点卡几何/裁决词全词/面板防御拆除裁定);[flow/action_ops.md](../../flow/action_ops.md) §4.4(pick 族行);[fields.md](../fields.md) §3.4(事件选择域组;chosen_hack 暂无画面建档注)。
