# 遭遇选择(PickEncounter)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一(同族共通面见各篇 §2 开头,机械确认链纪律正本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.4)。

## 1. 动作是什么

遭遇节点弹窗点选一张遭遇卡并确认。词表 = `kernel/cw_vocab.py::PickEncounter`(`PickOption` 子类:字段 `idx` = 画面候选卡位下标 0 起(左→右)、`reason` = 归因记录字段)。op 载体 = `operations/cw_op/cw_overlay_pick_action.py::EncounterPickOp`(体迁自 `cw_screen_encounter.py::CwScreenEncounter._confirm_default`,替身缝 = 原方法薄委托保留;域 env = `OverlayPickExecEnv`)。

## 2. 逻辑态域集

**容器 GameState 零写**——事件线选择非逻辑态通道([../action-logic-state.md](../action-logic-state.md) §6)。机械参数由画面 op 决策半现算经 `OverlayPickExecEnv` 传入,op 类体内零决策零读决策输入;轮次结果经 `env.round_result` 旁路回传(基类 execute 返回契约恒 True)。本动作的写边:

- **选择落地观察写端**:`chosen_encounter`(容器 Field,值形 (难度档, 奖励文本))= 画面 op `CwScreenEncounter` 的观察写入边(`REGISTERED_ACTORS` 在册);
- **确认到账 grant**:无(本类确认无登记面;`ConfirmStrategy`/`ConfirmMegastar`/`ConfirmPartner` 在 `register_confirm_arrival` 零写,分道申报见 `operations/cw_screen/_overlay_confirm.py`);
- 刷新建议不经本动作:遭遇刷新链 = 同访问重决策,发射 `RefreshNodeOptions` 前须以重读产物覆盖写槽再决策(刷新链分屏形态申报,`cw_vocab.py::RefreshNodeOptions`)。

## 3. 确定面转移规则(逐条)

1. 点卡选中:卡位中心 = `kernel/cw_obs_core.py::area_center`('遭遇卡-其一'/'遭遇卡-其二',缺失兜底 `CwScreenEncounter.CARD_LEFT`/`CARD_RIGHT` 历史实测常量);`idx == 0` 点左卡否则右卡(`safe_click`);
2. 固定等待 0.8s;
3. 确认机械交回 = `_overlay_confirm.emit_overlay_confirm`(确认点 = area_center('按钮-选择') or `SELECT_BTN`;裁决词 = 标题全词「遭遇节点」,4 字 vs 备战「遭遇」标签 2 字 LCS 不误匹配);轮次结果(末步 `round_*` 产物)经 `env.round_result` 旁路回传。

## 4. 随机面

遭遇卡面内容(难度档/奖励)= 随机面归观察;选择后果不记预期值。

## 5. 拒绝语义

零验证确认链:确认未落地(overlay 残留)不重试不判效——下一轮重入入口观察裁决(节点循环重走本链,「插空白点击取消选中」类风险的防线 = 重入裁决 + 预算耗尽 bail);screen_info 坐标缺失走兜底常量(本屏在册例外,其余坐标缺失 = 禁兜底)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::PickEncounter` / `PickOption`;`operations/cw_op/cw_overlay_pick_action.py::EncounterPickOp` / `OverlayPickExecEnv`;`operations/cw_screen/_overlay_confirm.py::safe_click` / `emit_overlay_confirm`;`kernel/cw_obs_core.py::area_center`;`kernel/cw_game_state.py::chosen_encounter` / `REGISTERED_ACTORS`(CwScreenEncounter 行);`operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter`(替身缝/写点)。

## 7. 语义验证

容器零写语义 = 「事件线选择非逻辑态通道」契约;选择落地真值 = chosen_encounter 观察写端 + 下一帧重入观察。无 M1 投影直锁对象(不经 `apply_shop_action_logic`/`apply_prep_action_logic` 写口)。

## 8. 判例注记(发射期)

遭遇节点画面期;发射位 = 各 overlay 画面 op act 段经注册表工厂分派(`cw_action_registry.py` 事件线 pick 族行)。

## 9. 依据

`operations/cw_op/cw_overlay_pick_action.py` 模块头(体迁纪律/域 env 契约)与 `EncounterPickOp` docstring;[flow/action_ops.md](../../flow/action_ops.md) §4.4(pick 族行);[fields.md](../fields.md) §3.4(事件选择域组)。
