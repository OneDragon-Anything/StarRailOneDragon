# 祈愿试炼(wish_trial · 货币战争-祈愿试炼)

> 代码 = `operations/cw_screen/cw_screen_wish_trial.py::CwScreenWishTrial`(两 node 直继承 `SrOperation`)。职责:祈愿试炼 overlay(节点级 quest 选择,叠备战、挡出战)一次访问——OCR 各卡 objective → `decide_wish_trial` 选卡 → 点卡选中 + 确认;确认落地由重入裁决承载并补写 chosen_wish。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_wish_trial.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役):id_mark 锚「货币战争-祈愿试炼.标识-祈愿试炼」。(单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 道具详情弹窗分支(0e3)以「非祈愿屏」排他让路(共用「聘用书」类文案时祈愿锚优先),排他判定留外循环。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(「标识-祈愿试炼」,miss = round_fail 交回外循环重判)→ objective 一次读 → `report_screen_wish_trial_obs` 落容器 `wish_trial_opts` / `wish_trial_opts_xy`(空桶照写,同门双写,op-layer.md §1.1 :35)→ obs 挂实例属性。决策动作 node = 顶部重入裁决(确认 pending = 上轮已发确认的 `(objectives, pick_idx)` 快照;标识不在 = overlay 已关 → 此刻才写 `chosen_wish` + success;标识在 = 未落地 → 清标志重走)→ 零参决策 `match.strategy.decide_wish_trial()`(候选自容器槽;打分:金币类/阵营词命中/刷新购买操作向 + 效果偏置基分,权重常量单一源 = `strategies/impl/pick_bias.py::PICK_BIAS`,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E5)。决策出口无屏内兜底:无 match 局外不设早退支(用户裁决 2026-09-22 全族删门);返回 None/词表外 = 具名 round_fail 零盲发交回外循环(op-layer.md §1.1 出口③),pick idx 越界 = 守卫断言 AssertionError(op-layer.md §1.3,禁钳位),策略异常自然传播;守卫均在派发前、零点击,fail 出口非循环出口、非防御上限;选卡派发 = 策略产实例直发,流程侧零值域改写。选卡坐标 = 容器 `wish_trial_opts_xy`(选项坐标伴随域,与候选名域 `wish_trial_opts` 同序等长):观察上报与名字域同门一并入容器(op-layer.md §1.1 :35,坐标单一真相源 = 观察上报),动作 op 按 idx 自容器取点,缺席/越界 = 守卫断言;确认钮等静态控件锚 = screen_info area 现取不变。选卡确认链经 `CwActionPickWishTrialOp` 派发(机械链+自上报在动作 op 内,pick-op-unify 批)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=8` 现役值仅框架异常路径消费)。

## 3. 观察面

观察 node = 入口门(「标识-祈愿试炼」)+ objective 一次读(每访问恰一次,决策轮复用实例载体);objective 读取 `_read_objectives`:OCR 文本带 y 250-400,按 x 近邻分流到卡槽(槽 x 常量数组,容差 160),同桶 join 为各卡 objective 文本(候选卡数随节点变,槽常量覆盖 3 卡位);槽位坐标观察期一次解析(x = 槽 x 常量数组桶锚、y = 卡身 y 常量 340)。观察 payload = `CwScreenWishTrialObs`(`on_screen`/`options`/`option_points`/`screen`,住 `kernel/cw_screen_report/wish_trial.py`);report = `report_screen_wish_trial_obs` 候选与槽位坐标一并写 `wish_trial_opts` / `wish_trial_opts_xy`(同门同写,op-layer.md §1.1 :35;空桶照写;match/gs 缺席的局外兜底路径跳过)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickWishTrialOp`(`CwActionPickWishTrialParam`) | 注册表工厂 `action_op_for` 直发策略产 `CwActionPickWishTrialParam` 实例(`OverlayPickExecEnv` 仅携 op;坐标由动作 op 自容器取[op-layer §1.1 :35];两守卫派发前,流程侧零值域改写) | 自上报 `report_action_pick_wish_trial_param`(零写族,容器零写) | 否(非终结):发出后 `round_wait` 循环推进;落地由重入裁决判——「货币战争-祈愿试炼.标识-祈愿试炼」不在 = 补写 `chosen_wish` + success 交回外循环(见 §5) |
| (无 match,局外,非动作) | — | — | 不设早退支(op-layer §1.1;用户裁决 2026-09-22 全族删门):单跑缺上下文沿正常链路自然失败,局内不达此态 |
| (决策无有效输出/pick idx 越界,非动作) | — | — | 守卫 fail:词表外/None = round_fail(含原值)、idx 越界 = AssertionError;零点击零派发,交回外循环 |

决策动作 node 选卡+确认链(整体经动作工厂 `cw_pick_wish_trial_action.py::CwActionPickWishTrialOp` 派发,pick-op-unify 批;机械链+自上报零写在动作 op 内,派发 param 携真实选中 idx):

```
objs = 观察轮 obs 载体(无 match 局外不设早退支,用户裁决 2026-09-22 全族删门)
pick = decide_wish_trial()(零参;候选读容器 wish_trial_opts 槽)
  (返回 None/词表外 = round_fail 含原值;idx 越界 = AssertionError;策略异常自然传播)
坐标 = 容器 wish_trial_opts_xy[pick.idx](动作 op 内取;缺席 = 守卫断言,op-layer §1.1 :35)→ 置确认 pending → 直发 pick 派发
  (动作 op 内:按容器坐标 mouse_move + click[点卡身选中:金色边框 + 确认选择亮]
   → 1.0s → 点「按钮-确认选择」[round_by_find_and_click_area,success_wait 1.5;
   本屏独有检测,不与 partner/megastar 的同名钮撞——祈愿锚在前已分流]
   → 自上报 report_action_pick_wish_trial_param)
  (机械交回零判效;落地判定归决策动作 node 顶部重入裁决,
   chosen_wish 写端随之在裁决点,防未落地轮留幻影登记)
```

交互陷阱:ESC 不关本 overlay(禁键盘纪律下无替代键路径,唯一出口 = 选卡+确认);卡位不建 screen_info area(:35 辖域边界既判 = 选项坐标入坐标域);选卡坐标 = 观察上报容器 `wish_trial_opts_xy`(op-layer.md §1.1 :35)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入裁决标识不在(overlay 关) | **画面终结** | 补写 `chosen_wish` + round_success 交回外循环重分发(回备战) |
| 重入裁决标识在(确认未落地) | 节点循环重入 | 重走重选(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |
| 无 match(局外) | 不设早退支(op-layer §1.1;用户裁决 2026-09-22 全族删门) | 未支持用法:单跑缺上下文沿正常链路自然失败,局内不达此态 |
| 决策无有效输出(返回 None/词表外)/pick idx 越界 | 守卫 fail(op FAIL) | round_fail / 框架异常路径(留证截图 + node_max_retry_times=8 预算耗尽)交回外循环;连续 fail 由外环重派网兜底(flow/README §4) |
| 入口锚 miss | op FAIL | 交回外循环重分发 |

「确认离开 = 画面终结」= [README.md](README.md) §6;守卫两行与「入口锚 miss」行同落点类,补行保表完备。

## 6. 状态上报面

- 候选观察:`report_screen_wish_trial_obs` 候选与槽位坐标一并写 `wish_trial_opts` / `wish_trial_opts_xy`(同门同写,op-layer.md §1.1 :35;空桶照写)。
- `chosen_wish` write_logic(重入裁决点写;值 = 选中卡 objective 原文名;objective 未读到/选中槽文本空不写,None 保持「无记录」)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」;quest 生命周期域 = fields.md §3.4.6(圣杯任务;本 op 只辖选卡,任务条件/完成态零供给)。

## 7. 子态与 overlay

本屏无子态。试炼 overlay 的内容随节点变(候选卡数/objective 不同),对 op 透明(逐帧现读)。

## 8. 守卫与防线

- 决策出口守卫:无 match 局外不设早退支(op-layer.md §1.1;用户裁决 2026-09-22 全族删门)——原「盲发首卡」退役申报;返回 None/词表外 = 具名 round_fail 零盲发——原「策略异常 fallback 首卡」退役申报。
- 值域守卫:pick idx 越界 = 守卫断言 AssertionError——原「越界保持 idx=0 静默钳位」退役申报。
- chosen 记录面:objective 未读到/选中槽文本空不写(None 保持「无记录」)——语义保持,策略异常降级轮已随守卫退役。
- 确认落地判定归重入裁决(同轮验关已拆,验证废除);未落地轮重走 = `round_wait` 循环推进(无防御上限)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「祈愿试炼」;op 内日志 tag = `[cw-wish]`(决策描述/点击点)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(节点循环族两 node 形态锁:观察上报容器/坐标域同门双写/入口门 miss fail/wish 落地裁决时点写/决策出口守卫——局外无早退支自然失败、词表外/None round_fail、idx 越界断言、直发零重建)、test_cw_unified_action_4.py(确认链机械行为锁:点击点 = 容器 `wish_trial_opts_xy[param.idx]`,缺席/越界 = 守卫断言)、test_cw_screen_report_ports.py(report 写面契约:双域写 + 等长守卫)、test_cw_game_state_consume.py(chosen_wish 接线锁)。
- game 侧知识:画面与机制(节点级 quest、奖励形态) = [../../../../game/screens/currency_war_wish_trial.md](../../../../../game/screens/currency_war_wish_trial.md);决策规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E5。
