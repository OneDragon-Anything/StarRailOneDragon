# 祈愿试炼(wish_trial · 货币战争-祈愿试炼)

> 代码 = `operations/cw_screen/cw_screen_wish_trial.py::CwScreenWishTrial`(两 node 直继承 `SrOperation`)。职责:祈愿试炼 overlay(节点级 quest 选择,叠备战、挡出战)一次访问——OCR 各卡 objective → `decide_wish_trial` 选卡 → 点卡选中 + 确认;确认落地由重入裁决承载并补写 chosen_wish。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_wish_trial.yml`。

## 1. 分发判定

- 外循环分支 0h:id_mark 锚「货币战争-祈愿试炼.标识-祈愿试炼」。分发 = 阶段一身份行(单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 道具详情弹窗分支(0e3)以「非祈愿屏」排他让路(共用「聘用书」类文案时祈愿锚优先),排他判定留外循环。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(「标识-祈愿试炼」,miss = round_fail 交回外循环重判)→ objective 一次读 → `report_screen_wish_trial_obs` 落容器 `wish_trial_opts` 槽(空桶照写)→ obs 挂实例属性。决策动作 node = 顶部重入裁决(确认 pending = 上轮已发确认的 `(objectives, pick_idx)` 快照;标识不在 = overlay 已关 → 此刻才写 `chosen_wish` + success;标识在 = 未落地 → 清标志重走)→ 零参决策 `match.strategy.decide_wish_trial()`(候选自容器槽;打分:金币类/阵营词命中/刷新购买操作向 + 效果偏置基分,权重常量单一源 = `strategies/impl/pick_bias.py::PICK_BIAS`,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E5)→ 选卡确认链经 `CwActionPickWishTrialOp` 派发(机械链+自上报在动作 op 内,pick-op-unify 批)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=8` 现役值仅框架异常路径消费)。

## 3. 观察面

观察 node = 入口门(「标识-祈愿试炼」)+ objective 一次读(每访问恰一次,决策轮复用实例载体);objective 读取 `_read_objectives`:OCR 文本带 y 250-400,按 x 近邻分流到卡槽(槽 x 常量数组,容差 160),同桶 join 为各卡 objective 文本(候选卡数随节点变,槽常量覆盖 3 卡位)。观察 payload = `CwScreenWishTrialObs`(`on_screen`/`options`/`screen`,住 `kernel/cw_screen_report/wish_trial.py`);report = `report_screen_wish_trial_obs` 候选写容器 `wish_trial_opts` 槽(空桶照写;match/gs 缺席的局外兜底路径跳过)。

## 4. 动作面

决策动作 node 选卡+确认链(整体经动作工厂 `cw_overlay_pick_action.py::CwActionPickWishTrialOp` 派发,pick-op-unify 批;机械链+自上报零写在动作 op 内,派发 param 携真实选中 idx):

```
objs = 观察轮 obs 载体 → idx = decide_wish_trial()(零参;候选读容器 wish_trial_opts 槽)
  (策略异常 = 留证告警 fallback 第 1 张;越界 = 不改 target)
target = (槽 x 常量[idx], 卡身 y 常量 340)→ 置确认 pending → 派发
  (动作 op 内:target mouse_move + click[点卡身选中:金色边框 + 确认选择亮]
   → 1.0s → 点「按钮-确认选择」[round_by_find_and_click_area,success_wait 1.5;
   本屏独有检测,不与 partner/megastar 的同名钮撞——祈愿锚在前已分流]
   → 自上报 report_action_pick_wish_trial_param)
  (机械交回零判效;落地判定归决策动作 node 顶部重入裁决,
   chosen_wish 写端随之在裁决点,防未落地轮留幻影登记)
```

交互陷阱:ESC 不关本 overlay(禁键盘纪律下无替代键路径,唯一出口 = 选卡+确认);卡身建档(卡位坐标)挂账实机批,现走槽常量。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入裁决标识不在(overlay 关) | **画面终结** | 补写 `chosen_wish` + round_success 交回外循环重分发(回备战) |
| 重入裁决标识在(确认未落地) | 节点循环重入 | 重走重选(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |
| 入口锚 miss | op FAIL | 交回外循环重分发 |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- 候选观察:`report_screen_wish_trial_obs` 候选写容器 `wish_trial_opts` 槽(空桶照写)。
- `chosen_wish` write_logic(重入裁决点写;值 = 选中卡 objective 原文名;objective 未读到/选中槽文本空 = 盲选 fallback 不写,None 保持「无记录」)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」;quest 生命周期域 = fields.md §3.4.6(圣杯任务;本 op 只辖选卡,任务条件/完成态零供给)。

## 7. 子态与 overlay

本屏无子态。试炼 overlay 的内容随节点变(候选卡数/objective 不同),对 op 透明(逐帧现读)。

## 8. 守卫与防线

- 策略异常留证降级(fallback 首卡,不阻塞);盲选 fallback 轮不写 chosen(防把无依据选择固化成记录值)。
- 确认落地判定归重入裁决(同轮验关已拆,验证废除);未落地轮重走 = `round_wait` 循环推进(无防御上限)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「祈愿试炼」;op 内日志 tag = `[cw-wish]`(决策描述/点击点)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(节点循环族两 node 形态锁:观察上报容器/入口门 miss fail/wish 落地裁决时点写)、test_cw_game_state_consume.py(chosen_wish 接线锁)。
- game 侧知识:画面与机制(节点级 quest、奖励形态) = [../../../../game/screens/currency_war_wish_trial.md](../../../../../game/screens/currency_war_wish_trial.md);决策规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E5。
