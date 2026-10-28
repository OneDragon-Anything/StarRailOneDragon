# 开秘密典籍(OpenTome)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

点击占备战席 1 槽的秘密典籍道具开启:典籍离席腾槽 + 星徽四选一弹窗弹出;选卡不在本执行链,点完开启返回主循环(返回主循环)。**非终结**动作(与 OpenBox 的终结化不同,弹窗交给外循环的画面分支处理)。op 载体 = `operations/cw_op/cw_open_tome_action.py::CwActionOpenTomeOp`(体迁自执行器,原薄委托 `prep_actions.py::PrepActionExecutor._open_tome` 已随死代码清偿移除,执行 = op 直执行 + 自上报);动作类型(`kernel/cw_vocab.py` 清单中的类)= `CwActionOpenTomeParam`(`slot: int | None`,None = 首件;与 OpenBox/OpenBookcard 同签名)。发出条件 = 备战策略产出 OpenTome。

## 2. 逻辑态域集

**容器腾位写入**(上报函数 = `kernel/cw_action_report/open_tome.py::report_action_open_tome_param`,op 自上报):bench 槽位 kind `tome` → `empty`(开典籍即腾位,占席事实进容器(GameState,游戏状态对象,下同))。守卫 = bench 未观察 / 槽不存在 / 槽类型不符 → 陈旧提案零写;`slot=None` = 首个 `kind='tome'` 槽(与动作发出形态对齐)。腾位窗口 = OpenTome 非终结,同一次访问的后续帧晶矿谓词消费 `bench_free_slots`(派生自容器 bench),直写消除「开典籍后席空数少计一帧」的保守偏置。

**其它域零写**:选卡后果(星徽四选一)随机面归观察;典籍不消失,消耗在选卡确认(申报 = 上报函数 docstring)。

**触发物识别**(备战观察链):典籍占席事实经 bench 槽位 `kind='tome'` 进容器(观察读链 `read_bench_view` 识别期定 kind,同帧 `read_tomes` 槽号集构造;决策分支 = mandate_v1 entry 开典籍分支读容器 bench 首个 tome 槽)。

## 3. 确定面转移规则(逐条)

1. `read_tomes` 识别在席典籍(识别域 = screen_info 单一源,禁兜底坐标);
2. 点目标槽**一次**(单击即开启,游戏侧单次点击弹星徽四选一;用户确认 2026-09-25)→ 固定动画等待(`_OVERLAY_ANIM_WAIT_S`)→ 返回主循环(非终结,同画面继续本轮);
3. 星徽四选一 overlay 弹出由外循环阶段一身份行「货币战争-星徽秘典弹窗」分发星徽秘典画面 op(`operations/cw_screen/cw_screen_bookcard.py`):`chosen_tome` 选择写入位置(选择落地即写 logic)+ 确认到账登记 = `_overlay_confirm.register_confirm_arrival` → `kernel/cw_exec_state.py::apply_confirm_effect` dict `ConfirmTome` 分支 owned +1;
4. 本动作自身零金零装备零经验面。

## 4. 随机面 / 观察面

四选一卡面内容 = 随机面归观察;选卡后果默认不记预期值(事件线选择非逻辑态通道,[../action-logic-state.md](../action-logic-state.md) §6),有显式到账登记的照登记(ConfirmTome owned +1,见 §3 第 3 条)。

## 5. 拒绝语义

无典籍 / 槽不匹配 = 未发出(round 结果失败态,观察-执行竞态),返回主循环重新观察重派;`action.slot` 对位无匹配 = 未发出(detail 载实读槽位表);过渡帧不开(`is_prep_like_frame` 不命中)= 不发,交完整观察;validate 参数非法(slot 越界)= 发出前输入契约拒绝。容器腾位写入守卫(槽不存在/类型不符)= 静默零写等观察覆盖。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionOpenTomeParam`;`operations/cw_op/cw_open_tome_action.py::CwActionOpenTomeOp`;`kernel/cw_action_report/open_tome.py::report_action_open_tome_param`(腾位函数)/ `obs/cw_identity_obs.py::read_bench_view`(kind 识别期细分读链);`kernel/cw_exec_state.py::apply_confirm_effect`(dict ConfirmTome 分支);`operations/cw_screen/cw_screen_bookcard.py`(`chosen_tome` 写入位置 / ConfirmTome 登记);`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival`。

## 7. 语义验证

腾位写入语义单一源 = `report_action_open_tome_param`(bench kind 'tome' → 'empty',陈旧提案零写;行为测试 = `test_cw_unified_action_2a` 动作类型覆盖测试)。触发物识别 = 容器 bench 槽 kind 细分(读链识别期定 kind,决策分支读容器分派;行为测试 = mandate_v1 决策面 bench kind 分派用例)。选卡后果归观察(ConfirmTome 登记)。

## 8. 判例注记(动作发出阶段)

备战期(占席道具只在备战画面可见可点);腾位类动作之一(占席道具三件 = 补给箱/秘密典籍/书册卡)。

## 9. 依据

[flow/action_ops.md](../../flow/action_ops.md) §4.2 OpenTome 行(单击开启/非终结);`kernel/cw_action_report/open_tome.py::report_action_open_tome_param` docstring(腾位守卫与零写面);`operations/cw_screen/cw_screen_bookcard.py` 模块头(`chosen_tome` 写入位置与 ConfirmTome 推进);[fields.md](../fields.md) §3.2.5(占席道具)/§4.2 事件选择行。
