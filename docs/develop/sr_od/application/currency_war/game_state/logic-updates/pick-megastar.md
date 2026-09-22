# 盛会之星选择(PickMegastar)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一(机械确认链纪律正本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.4)。

## 1. 动作是什么

盛会之星 overlay 点「确认选择」确认已选强化角色。词表 = `kernel/cw_vocab.py::CwActionPickMegastarParam`(`PickOption` 子类:字段 `idx` = 候选下标 0 起、`reason` = 归因记录字段)。op 载体 = `operations/cw_op/cw_pick_megastar_action.py::CwActionPickMegastarOp`(体迁自 `cw_screen_megastar.py::CwScreenMegastar._do_action` 确认半,替身缝 = 方法级桩保留;域 env = `OverlayPickExecEnv`)。

## 2. 逻辑态域集

**容器 GameState 零写**——事件线选择非逻辑态通道([../action-logic-state.md](../action-logic-state.md) §6):

- **候选选中半留守画面 op**:候选选中点击与 `chosen_megastar` 写端在原体内交错(点击 → 写端 → 动画等待),写端属单次逻辑写入豁免面——确认机械半先收拢进本 op,候选半随写端留在画面 op;`chosen_megastar`(容器 Field,值 = 强化角色名)写端 = `CwScreenMegastar` 候选选中时点的观察写;
- **确认到账 grant**:无——原「到账登记」ConfirmMegastar 块已随两态制废除(`chosen_megastar` 写端无挂账登记环节);`ConfirmMegastar` 在 `register_confirm_arrival` 零写(`_overlay_confirm.py` 分道申报);
- 候选选中建议不经本动作确认链外的第二载体;本 op = 确认钮单发。

## 3. 确定面转移规则(逐条)

1. 确认 = 建档「货币战争-盛会之星.按钮-确认选择」查找点击(`round_by_find_and_click_area`,全族统一;area 缺失 = 显式失败交框架轮次,禁兜底坐标)→ 固定等待 0.9s;
2. 纯机械单发(原 step2 安全网已拆——「请选择强化角色」文本 = 确认钮旁伴随文案,禁据它判步);
3. 轮次结果经 `env.round_result` 旁路回传;确认未落地 overlay 残留 = 下一帧重入裁决自愈:节点循环读「仍在巨星 overlay?」(标识锚仍命中)→ 重走本链(候选已选 → 机械单发确认再推进)。

## 4. 随机面

强化候选内容 = 随机面归观察;选择后果不记预期值。

## 5. 拒绝语义

零验证确认链:确认未落地不重试不判效——下一轮重入入口观察裁决(§3 第 3 条自愈环)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionPickMegastarParam` / `PickOption`;`operations/cw_op/cw_pick_megastar_action.py::CwActionPickMegastarOp` / `cw_overlay_pick_env.py::OverlayPickExecEnv`;`kernel/cw_obs_core.py::area_center`;`kernel/cw_game_state.py::chosen_megastar`;`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival`(ConfirmMegastar 零写分道);`operations/cw_screen/cw_screen_megastar.py::CwScreenMegastar`(候选半/写端/替身缝)。

## 7. 语义验证

容器零写语义 = 「事件线选择非逻辑态通道」契约;`chosen_megastar` 真值 = 候选选中写端 + 下一帧重入观察。无 M1 投影直锁对象。

## 8. 判例注记(发射期)

盛会之星 overlay 画面期;发射位 = 画面 op act 段经注册表工厂分派。

## 9. 依据

`operations/cw_op/cw_pick_megastar_action.py::CwActionPickMegastarOp` docstring(候选半留守裁定/单发语义);`operations/cw_screen/_overlay_confirm.py` 分道申报;[flow/action_ops.md](../../flow/action_ops.md) §4.4(pick 族行);[fields.md](../fields.md) §3.4.5(盛会之星域)。
