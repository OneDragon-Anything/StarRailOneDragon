# 未达上限确认弹窗(deploy_not_full · 货币战争-未达上限警告)

> 代码 = `operations/cw_screen/cw_screen_deploy_not_full.py::CwScreenDeployNotFull`(两 node 直继承 `SrOperation`)。职责:「可出战角色人数未达上限」确认弹窗的一次访问——勾「本局不再提示」+ 确认,解除未达上限警告对出战的阻塞。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 阶段一身份分发(分支号制已停用):id_mark = `货币战争-未达上限警告.标识-未达上限警告`(**位置区分**判据:投资策略屏描述「能量上限」与「未达上限」共享子序列「上限」,全屏 LCS 会误匹配吞投资策略分支——area 位置不同即不命中)。单一源 = [skills/sr-od-dev-currency-war/references/flow/loop.md](skills/sr-od-dev-currency-war/references/flow/loop.md) §2;建档 = `currency_war_deploy_not_full.yml`。

## 2. 画面形态声明

**空决策形态**(确认即推进,零策略问询)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 标识门(「标识-未达上限警告」,miss = round_fail 返回主循环)+ obs{on_screen} + 占位 report 调用 → obs 挂实例属性;决策动作 node = 顶部落地复查(确认已发 → id_mark 不在 = 弹窗已关 → success 结束本次访问;id_mark 在 = 未落地重做)→ `_confirm_and_dismiss` 确认体 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=10` 在用值仅框架异常路径消费)。

## 3. 观察面

轻观察:payload = `CwScreenDeployNotFullObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/deploy_not_full.py`);标识门在观察 node(miss → `round_fail` 返回主循环)。report = `report_screen_deploy_not_full_obs` 占位调用(本屏在用零字段写操作点,接口为统一形态占位;match/gs 缺席跳过)。零 GameState 写端。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「返回主循环」= 本访问结束、控制权返回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(动作类型清单参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——确认链由内置动作完成(`_confirm_and_dismiss`:勾「本局不再提示」+ 确认) | 画面 op 内置动作(`_confirm_and_dismiss`:勾 `货币战争-未达上限警告.勾选-本局不再提示`(`_overlay_confirm.py::safe_click`)+ 确认(`_overlay_confirm.py::emit_overlay_confirm`)+ 置位 `_confirm_pending`) | 观察侧 `report_screen_deploy_not_full_obs`(占位调用挂观察 node,本屏零字段写操作点;动作本体无自上报) | 否(非终结):确认后 `round_wait` 循环推进;落地由落地复查判——id_mark 不在 = 弹窗已关 → `round_success` 返回主循环(见 §5) |

`_confirm_and_dismiss`:勾 `货币战争-未达上限警告.勾选-本局不再提示`(`_overlay_confirm.py::safe_click` 带防吞点击 + 0.3s)→ 确认(`_overlay_confirm.py::emit_overlay_confirm`,mouse_move 缓解 + success_wait=3.0)→ 置位 `_confirm_pending`(落地判定归下一轮落地复查)。坐标 = screen_info 现取优先,**缺失才用兜底常量**(`CHECKBOX_NO_PROMPT(912,589)` / `BTN_CONFIRM(1159,653)`)——与「禁兜底坐标」一般红线不同的 as-built 例外,在此申报。

## 5. 终结与交回

落地复查:确认已发 ∧ id_mark miss = 已关 → `round_success(wait=3.0)` 结束本次访问;id_mark 仍在 = 确认未落地 → 重做(`round_wait` 循环推进,无防御上限)。落点 = 底层屏(备战 / 出战链语境)重判。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件;「本局不再提示」为游戏局级抑制位,不入任何账。

## 7. 子态与 overlay

- 本 op 自身即 overlay 处理件;命中即自处理,底层屏返回主循环重新判定。
- **出战链弹窗主路径**:出战动作 op 为单击原子形态(点击后世界交回主循环重识别),出战单击后渲染的本弹窗由主循环阶段一身份分发接住派发本 op 处理——本 op 已登记 `CW_DISPATCH_SCREENS`(`kernel/cw_dispatch_tables.py` 单源),身份分发先于备战分支命中,是本弹窗的唯一处理路径(出战动作 op 内已无内联收尾)。

## 8. 守卫与防线

`node_max_retry_times=10` 在用值仅框架异常路径消费;「点了≠成了」防线 = 落地复查;无停机钩子/失配告警面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与测试面

- journal op 名 = 「未达上限确认」;frame_tag = `overlay_deploy_not_full`;dispatch wait=3(与确认收尾 success_wait 同口径);日志 tag `[cw-deploywarn]`。测试:弹窗主路径(出战点击 → 本弹窗帧 → 阶段一身份分发接住本 op → 交回)= `sr-od-test/test/sr_od/application/currency_war/operations/cw_op/test_cw_start_battle_action.py::test_popup_main_path_deploy_not_full`;建档 = `currency_war_deploy_not_full.yml`。
