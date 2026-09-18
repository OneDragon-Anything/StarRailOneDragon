# 开补给箱(OpenBox)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

点击占备战席 1 槽的补给箱道具开启:**终结动作**——开箱即引入新事实(武装箱选择画面弹出),执行即本访问结束,交回外循环分发选卡。op 载体 = `operations/cw_op/cw_open_box_action.py::OpenBoxOp`(`terminal=True`,`terminal_wait=1.8s`;体迁薄委托 = `prep_actions.py::PrepActionExecutor._open_box`);词表 = `kernel/cw_vocab.py::OpenBox`(`slot: int | None`,None = 第一箱)。发射条件 = 备战策略产 OpenBox。

## 2. 逻辑态域集

容器 GameState **零写**(合法零写集申报):`kernel/cw_game_state.py::apply_prep_action_logic` 对 OpenBox **合法零写**(登记面两集申报:写口分支集 7 动作 / 合法零写集含 OpenBox)——**R7 终结化**,结束判定先行交回外循环,不经逻辑态写;腾席/到账事实由交回后的下一入口 heavy 观察覆盖(零窗口:终结 = 发出即 visit 结束,无同 visit 后续帧消费)。`kernel/cw_exec_state.py::apply_op_effect` else 分支显式不建模清单点名 OpenBox——箱不消失,消耗在选卡确认。

**触发物识别**(备战观察链):补给箱占席事实经 bench 槽位 `kind='supply_box'` 进容器(观察写端 `bench_view_from_obs` 细分;决策臂 = mandate_v1 entry 开箱臂读容器 bench 首个 supply_box 槽,臂序 box 优先于典籍)。

## 3. 确定面转移规则(逐条)

1. `read_supply_boxes` 识别在席箱(识别域 = screen_info 单一源,禁兜底坐标);
2. 点目标槽「开启」(槽中心 + `BOX_OPEN_DY=41` 偏移)→ 固定动画等待(`terminal_wait=1.8s`,等待归产生动画的操作)→ 机械交回外循环;
3. 后续选卡 = 武装箱选择画面 op(`operations/cw_screen/cw_screen_box_pick.py`)分发:卡名集 logic 写入 `box_card_names` 候选槽(actor = CwScreenBoxPick,同访问覆盖写)→ 策略契约 `decide_box_card` 现算选卡(fail-closed)→ 选卡即终结交回;
4. **到账**:选中装备进 owned 库存无独立逻辑写端,真值归下一帧装备区读数观察覆盖;确认到账登记面 = `operations/cw_screen/_overlay_confirm.py::register_confirm_arrival` → `apply_op_effect` dict `ConfirmBox` 分支(owned +1)——分支在册,现役登记发射位核对 = ConfirmSupply(补给选卡)/ConfirmTome(星徽秘典)/ConfirmExpertCash(专家邀请函),ConfirmBox 暂无在役发射点(武装箱链现走 `box_card_names` 写槽 + 观察覆盖,登记面为确认通道预留)。

## 4. 随机面 / 观察面

箱内卡面内容 = 随机面归观察;选卡后果不记预期值(事件线选择非逻辑态通道,[../action-logic-state.md](../action-logic-state.md) §6);腾席/到账真值均由下一入口 heavy 帧实读覆盖。

## 5. 拒绝语义

无箱 / 指定槽无箱 = 未发出(`emitted=False`,观察-执行竞态),交回重观察重派;`action.slot` 对位无匹配 = 未发出(detail 载实读槽位表);validate 参数非法(slot 越界)= 发出前输入契约拒绝。容器零写语义下无 `applied=False` 拒绝形态。

## 6. kernel 符号锚

`kernel/cw_vocab.py::OpenBox`;`operations/cw_op/cw_open_box_action.py::OpenBoxOp`(`terminal`/`terminal_wait` 类属性,消费点经注册表 `action_op_class_for` 读);`kernel/cw_game_state.py::apply_prep_action_logic`(合法零写集申报)/ `bench_view_from_obs`(kind 细分观察写端);`kernel/cw_exec_state.py::apply_op_effect`(else 分支显式不建模 + dict ConfirmBox 分支);`operations/cw_screen/cw_screen_box_pick.py`(`box_card_names` 写点 / `decide_box_card`);终结判定总表 = [screens/README](../../screens/README.md) §4。

## 7. 语义验证

OpenBox = **合法零写集成员**(登记面申报,行为锁 = `test_cw_unified_action_2a` 词表覆盖锁零写集断言:write_seq 不变);终结化语义由注册表 `terminal=True` 承载(执行即交回外循环,下一入口 heavy 覆盖腾席/到账真值)。触发物识别 = 容器 bench 槽 kind 细分(mandate_v1 决策面 bench kind 分派用例)。

## 8. 判例注记(发射期)

备战期(占席道具只在备战画面可见可点);开箱是腾席类动作之一(占席道具三件 = 补给箱/秘密典籍/书册卡,腾席义务先于部署/上阵发射)。

## 9. 依据

[flow/action_ops.md](../../flow/action_ops.md) §4.2 OpenBox 行(终结化/识别/点击链);`kernel/cw_game_state.py::apply_prep_action_logic` docstring(两集申报);`operations/cw_screen/cw_screen_box_pick.py` docstring(`box_card_names` 写槽与选卡即终结);[fields.md](../fields.md) §3.2.5(占席道具)/§4.2 事件选择行。
