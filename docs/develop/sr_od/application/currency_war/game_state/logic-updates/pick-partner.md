# 列车伙伴选择(PickPartner)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号名引用路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一(机械确认链纪律权威版本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.4)。

## 1. 动作是什么

列车同行伙伴 overlay「点选候选 → 确认」脉冲链。动作类型(`kernel/cw_vocab.py` 清单中的类)= `CwActionPickPartnerParam`(`PickOption` 子类:字段 `idx` = 候选下标 0 起、`reason` = 归因记录字段)。op 载体 = `operations/cw_op/cw_pick_partner_action.py::CwActionPickPartnerOp`(体迁自 `cw_screen_partner.py::CwScreenPartner._handle_overlay` 脉冲尾段,替身缝 = 方法级桩保留;域 env = `OverlayPickExecEnv`)。

## 2. 逻辑态域集

**状态容器(GameState)(GameState,游戏状态对象,下同)零写**——事件线选择非逻辑态通道([../action-logic-state.md](../action-logic-state.md) §6):

- **选择落地观察写入**:`chosen_partner`(状态容器 Field,值 = 候选阵营名)= 画面 op `CwScreenPartner` 的观察写入边;
- **确认到账 grant**:无——`ConfirmPartner` 在 `register_confirm_arrival` 零写(handler 既有写入位置承担,`_overlay_confirm.py` 分道申报);
- **状态宿主在画面 op**:选中态标记(`op._pick_point`)与脉冲计数(`op._confirm_pulses`/`op._confirm_pending`)宿主 = 画面 op,本 op 经 `env.op` 消费——计数生命周期 = 节点级,画面 op 单一归属不变。

## 3. 确定面转移规则(逐条)

1. **点选候选**:`env.unselected` 为真(未选中提示在场实证)或首轮(`op._confirm_pulses == 0`)→ mouse_move + click `op._pick_point`(y 取建档「候选-卡区」带的中心;单选语义无反选面)→ 固定等待 0.7s;
2. **确认**:确认点 = `op._find_text_center`(screenshot, '确认选择');缺失 → `round_retry(wait=1)` 结束本次访问(轮次结果经 `env.round_result` 旁路);命中 → mouse_move + click → 固定等待 1.0s → `op._confirm_pulses += 1`、`op._confirm_pending = True` → `round_retry(wait=1)`;
3. 本屏 = 单屏单选、无第二画面步:点选 → 确认 → 落地复查即完;retry 轮重复确认零副作用(置灰态被游戏拒绝,无确认穿透风险)。

## 4. 随机面

伙伴候选内容(阵营)= 随机面归观察;选择后果不记预期值。

## 5. 拒绝语义

零验证确认链(确认后不读屏验证是否生效):「确认选择」文本缺失 → round_retry 返回轮次结果(非判效,落地复查);确认未落地(overlay 残留)不重试不判效——下一轮重入入口观察裁决。

## 6. kernel 符号名引用

`kernel/cw_vocab.py::CwActionPickPartnerParam` / `PickOption`;`operations/cw_op/cw_pick_partner_action.py::CwActionPickPartnerOp` / `cw_overlay_pick_env.py::OverlayPickExecEnv`;`kernel/cw_game_state.py::chosen_partner`;`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival`(ConfirmPartner 零写分道);`operations/cw_screen/cw_screen_partner.py::CwScreenPartner`(状态宿主/写入方/替身缝)。

## 7. 语义验证

状态容器零写语义 = 「事件线选择非逻辑态通道」契约;`chosen_partner` 真值 = 画面 op 的观察写入 + 下一帧重入观察。无 M1 投影测试对象。

## 8. 先例注记(动作发出阶段)

伙伴选择 overlay 画面期;动作发出点 = 画面 op act 段经注册表工厂分派。

## 9. 依据

`operations/cw_op/cw_pick_partner_action.py::CwActionPickPartnerOp` docstring(脉冲链/状态宿主归属/单屏单选澄清);`operations/cw_screen/_overlay_confirm.py` 分道申报;[flow/action_ops.md](../../flow/action_ops.md) §4.4(pick 族行);[fields.md](../fields.md) §3.4(事件选择域组)。
