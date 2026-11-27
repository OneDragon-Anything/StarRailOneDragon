# 前台无角色提示弹窗(toast_no_front · 货币战争-提示-前台无角色)

> 代码 = `operations/cw_screen/cw_screen_no_front_hint.py::CwScreenNoFrontHint`(两 node:观察 → 决策动作)。职责:「前台区域无角色」提示弹窗的一次访问——点确认关闭,解除出战阻塞。**零恢复动作语义**:确认即结束本次访问交回主循环,不重部署不补发出——「前台无角色」根因处置归部署面决策(下一备战帧自然提案),弹窗分支不自愈;弹窗残留 = 主循环下一帧重判再入本 op,天然幂等。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 阶段一身份分发:id_mark = `货币战争-提示-前台无角色.标识-无角色提示`。单一源 = [skills/sr-od-dev-currency-war/references/flow/loop.md](skills/sr-od-dev-currency-war/references/flow/loop.md) §2;建档 = `currency_war_toast_no_front.yml`。
- **弹窗帧可达性**:出战动作 op 为单击原子形态(点击后世界交回主循环重识别),本弹窗在出战单击后渲染,由主循环阶段一身份分发接住派发本 op——本屏已登记 `CW_DISPATCH_SCREENS`(`kernel/cw_dispatch_tables.py` 单源),身份分发先于备战分支命中,是本弹窗的唯一处理路径。

## 2. 画面形态声明

**空决策形态**(确认即解除阻塞,零策略问询)。两 node(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 标识门(「标识-无角色提示」,miss = round_fail 返回主循环;门在 op 执行时重验,防分发与执行之间画面已切换的盲点确认)+ obs{on_screen} + 占位 report 调用 → obs 挂实例属性;决策动作 node = 顶部落地复查(确认已发 → id_mark 不在 = 弹窗已关 → success 结束本次访问;id_mark 在 = 未落地重做)→ `_confirm_and_dismiss` 确认体 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=10` 在用值仅框架异常路径消费)。

## 3. 观察面

轻观察:payload = `CwScreenNoFrontObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/no_front.py`);标识门在观察 node(miss → `round_fail` 返回主循环)。report = `report_screen_no_front_obs` 占位调用(本屏在用零字段写操作点,接口为统一形态占位;match/gs 缺席跳过)。零 GameState 写端。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「返回主循环」= 本访问结束、控制权返回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(动作类型清单参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——确认链由内置动作完成(`_confirm_and_dismiss`:点「按钮-确认」) | 画面 op 内置动作(`_confirm_and_dismiss`:点 `货币战争-提示-前台无角色.按钮-确认` + 置位 `_confirm_pending`) | 观察侧 `report_screen_no_front_obs`(占位调用挂观察 node,本屏零字段写操作点;动作本体无自上报) | 否(非终结):确认后 `round_wait` 循环推进;落地由落地复查判——id_mark 不在 = 弹窗已关 → `round_success` 返回主循环(见 §5) |

`_confirm_and_dismiss`:点 `货币战争-提示-前台无角色.按钮-确认`(`round_by_find_and_click_area`,pre_delay=0.3 / success_wait=1 / retry_wait=1)→ 置位 `_confirm_pending`(落地判定归下一轮落地复查)。坐标 = screen_info 现取,点击落空 = 原语失败透传 round_retry(计节点预算;无兜底常量)。

## 5. 终结与交回

落地复查:确认已发 ∧ id_mark miss = 已关 → `round_success(wait=1.5)` 结束本次访问;id_mark 仍在 = 确认未落地 → 重做(`round_wait` 循环推进,无防御上限)。落点 = 底层屏(备战 / 出战链语境)重判——零恢复动作,重部署归部署面决策(下一备战帧自然提案)。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件。

## 7. 子态与 overlay

- 本 op 自身即 overlay 处理件;命中即自处理,底层屏返回主循环重新判定。
- 与「未达上限警告」弹窗同族(出战单击后渲染的两类真弹窗,均经阶段一身份分发处理;姊妹篇 = [deploy_not_full.md](deploy_not_full.md))。

## 8. 守卫与防线

`node_max_retry_times=10` 在用值仅框架异常路径消费;「点了≠成了」防线 = 落地复查;无停机钩子/失配告警面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与测试面

- journal op 名 = 「货币战争-前台无角色确认」;dispatch 包装统一落 `[cw-op]` 主日志行;建档 = `currency_war_toast_no_front.yml`。
- **sim 分支不适用**:后端画面状态机不建模本屏,弹窗帧恒不派发到本 op(机制 = sim 身份答口返回状态机当前屏,本弹窗屏不在其中)。
- 测试:三门路径(门 miss fail / 门 hit 确认 / 落地复查)= `sr-od-test/test/sr_od/application/currency_war/operations/cw_screen/test_cw_screen_no_front_hint.py`;弹窗主路径剧本(出战点击 → 本弹窗帧 → 阶段一身份分发接住)= `sr-od-test/test/sr_od/application/currency_war/operations/cw_op/test_cw_start_battle_action.py::test_popup_main_path_no_front_hint`。
