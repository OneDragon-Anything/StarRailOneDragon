# 开秘密典籍(OpenTome)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

点击占备战席 1 槽的秘密典籍道具开启:典籍离席腾槽 + 星徽四选一弹窗弹出;选卡不在本执行链,点完开启交回外循环。**非终结**动作(与 OpenBox 的终结化不同,弹窗由外循环画面分支接住)。op 载体 = `operations/cw_op/cw_open_tome_action.py::OpenTomeOp`(体迁薄委托 = `prep_actions.py::PrepActionExecutor._open_tome`);词表 = `kernel/cw_vocab.py::OpenTome`(`slot: int | None`,None = 首件;与 OpenBox/OpenBookcard 同签名)。发射条件 = 备战策略产 OpenTome。

## 2. 逻辑态域集

容器 GameState **零写**(显式申报):`kernel/cw_game_state.py::apply_prep_action_logic` 对集外动作型直接返回;`kernel/cw_exec_state.py::apply_op_effect` else 分支显式不建模清单点名 OpenTome(典籍不消失,消耗在选卡确认)。

**备战观察帧推进**(`kernel/cw_prep_actions.py::PrepObservation`,写口 = `operations/cw_screen/cw_screen_prep.py::_project_prep_obs` OpenTome 分支):`tomes` 载体按 `action.slot` **摘件**(None = 首件,与发射形态对齐)——腾出的席位事实由 tomes 载体与下一帧 heavy 现读承接,本分支不改写 `free_bench_slots`(与 OpenBookcard 分支的差异:典籍有独立载荷列表字段,占席语义走摘件而非腾席计数)。

## 3. 确定面转移规则(逐条)

1. `read_tomes` 识别在席典籍(识别域 = screen_info 单一源,禁兜底坐标);
2. 点目标槽**两次**(第一次选中、第二次开启,间隔 1s)→ 固定动画等待(`_OVERLAY_ANIM_WAIT_S`)→ 交回外循环(非终结,同画面继续本轮);
3. 星徽四选一 overlay 弹出由外循环 0i 分支分发星徽秘典画面 op(`operations/cw_screen/cw_screen_bookcard.py`):`chosen_tome` 选择写点(选择落地即写 logic)+ 确认到账登记 = `_overlay_confirm.register_confirm_arrival` → `kernel/cw_exec_state.py::apply_op_effect` dict `ConfirmTome` 分支 owned +1;
4. 本动作自身零金零装备零经验面。

## 4. 随机面 / 观察面

四选一卡面内容 = 随机面归观察;选卡后果默认不记预期值(事件线选择非逻辑态通道,[../action-logic-state.md](../action-logic-state.md) §6),有显式到账登记的照登记(ConfirmTome owned +1,见 §3 第 3 条)。

## 5. 拒绝语义

无典籍 / 槽不匹配 = 未发出(`emitted=False`,观察-执行竞态),交回重观察重派;`action.slot` 对位无匹配 = 未发出(detail 载实读槽位表);过渡帧不开(`is_prep_like_frame` 不命中)= 不发,交 heavy 观察;validate 参数非法(slot 越界)= 发出前输入契约拒绝。容器零写语义下无 `applied=False` 拒绝形态。

## 6. kernel 符号锚

`kernel/cw_vocab.py::OpenTome`;`operations/cw_op/cw_open_tome_action.py::OpenTomeOp`;`kernel/cw_prep_actions.py::PrepObservation`;`operations/cw_screen/cw_screen_prep.py::_project_prep_obs`(OpenTome 分支 = tomes 摘件);`kernel/cw_exec_state.py::apply_op_effect`(else 显式不建模 + dict ConfirmTome 分支);`operations/cw_screen/cw_screen_bookcard.py`(`chosen_tome` 写点 / ConfirmTome 登记);`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival`。

## 7. 语义验证

OpenTome 不在 `cw_vocab.py::Action` 联合的容器动作辖内——零局内资源推进语义,与「视觉域动作容器零写」契约同义;观察帧摘件行为 = `_project_prep_obs` 分支直断(词表外类型 AssertionError 响亮暴露,R9 纪律)。无 M1 投影直锁对象(本动作不经 `apply_shop_action_logic`/`apply_prep_action_logic` 写口)。

## 8. 判例注记(发射期)

备战期(占席道具只在备战画面可见可点);腾席类动作之一(占席道具三件 = 补给箱/秘密典籍/书册卡)。

## 9. 依据

[flow/action_ops.md](../../flow/action_ops.md) §4.2 OpenTome 行(两次点击/非终结);`operations/cw_screen/cw_screen_prep.py::_project_prep_obs` 段头注(OpenTome 分支语义);`operations/cw_screen/cw_screen_bookcard.py` 模块头(`chosen_tome` 写点与 ConfirmTome 推进);[fields.md](../fields.md) §3.2.5(占席道具)/§4.2 事件选择行。
