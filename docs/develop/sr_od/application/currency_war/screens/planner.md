# 骇入策划二选一(planner · 货币战争-骇入策划)

> 代码 = `operations/cw_screen/cw_screen_planner.py::CwScreenPlanner`(两 node 直继承 `SrOperation`)。职责:银狼「我来当策划」策划事件 overlay 一次访问——OCR 两卡文字 → `decide_planner` 选卡 → 点卡下半部选中(press_time 加固)→ 确认机械交回。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/cw_hacker_planner.yml`。

## 1. 分发判定

- 外循环分支 0a2:id_mark 锚「货币战争-骇入策划.标识-我来当策划」;dispatch 带 on_fail_retry。分发 = 阶段一身份行,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 触发 = 银狼首次升 2 星(及 5 费升 2 星),非随机事件;机制 = [../../../../game/gameplay/currency_war.md](../../../../../game/gameplay/currency_war.md)「银狼我来当策划事件」节。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1);**分发即门**(无 op 内入口守卫):观察 node = 左右两卡 OCR 桶一次读 → `report_screen_planner_obs` 落容器 `planner_opts` 槽(恒两卡,空桶照写;match/gs 缺席的局外兜底路径跳过)→ obs 挂实例属性;决策动作 node = 顶部重入出口门(确认已发 → OCR「我来当策划」不在 = overlay 已关 → success 交回)→ 零参决策 `match.strategy.decide_planner()`(候选自容器槽;唯一入口 = 策略对象,handler 禁 kernel 直调;委托 `kernel/cw_events.py::decide_planner` 升费卡打分含银狼线/在场判定,target_comp 决定银狼线加成,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E16。「何时升费非最优」由策略模块表达,handler 不写死优先级)→ 点卡+确认链 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=5` 现役值仅框架异常路径消费)。无 chosen_* 写端。

## 3. 观察面

观察 node = 左右两卡 OCR 桶一次读(入口帧一次读,决策轮复用实例载体;恒两元素 0=左卡/1=右卡)。卡面读取 = 全图 OCR,文本带 y 300-420(卡描述带),按 x 二分归左右卡(x<960 左 / ≥960 右)join 为 `PlannerOption(idx, text)`。观察 payload = `CwScreenPlannerObs`(`on_screen`/`options`/`screen`,住 `kernel/cw_screen_report/planner.py`);report = `report_screen_planner_obs` 候选写容器 `planner_opts` 槽(恒写,空桶照写)。

## 4. 动作面

决策动作 node 选卡+确认链(点卡+确认机械半经动作工厂 `cw_overlay_pick_action.py::PlannerPickOp`;决策半留守):

```
重入出口门(决策动作 node 顶部):_confirm_pending 置位 → OCR「我来当策划」全词(lcs 0.5)不在
  = overlay 已关(上轮确认已落地)→ success 交回;在 = 重走
  (裁决词 = 全词「我来当策划」:短词「策划」在艺术字漏读时可能假通过)
options = 观察轮 obs 载体 → decide_planner()(零参;候选读容器 planner_opts 槽)
target = _card_point(idx):卡 area(「骇入选项-左卡/右卡」)rect 相对几何推导
  = 中心 x + 71% 高度(卡下半部选中),详情钮避让 clamp(底缘上移 11% 比例);
  area 缺失回退旧实证 rect 常量
→ mouse_move + click(press_time 0.15 常量,输入管线半死态短按下不采样的加固)
  → 1.2s 等选中动画
→ 置 _confirm_pending → 确认:「按钮-骇入确认」center(建档 rect 中心,兜底常量)
  → emit_overlay_confirm(裁决词「我来当策划」,press_time 同加固;机械交回零判效)
```

交互陷阱:点卡上半部 = 弹「属性详情」非选中(选中点击几何治理,见 §7);布局漂移下绝对 y 常数会落卡外 → 选中失败 → 确认无效,防线 = 相对几何(只更 yml rect,本方法零改)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入出口门「我来当策划」不在 | **画面终结** | round_success 交回外循环重分发 |
| 出口门在(确认未落地) | 节点循环重入 | 重走选卡+确认(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

本屏无 chosen_hack 写端、无到账登记(选择后果走下一帧观察覆盖;GameState 字段位 `chosen_hack` 先申报无写端,fields.md §3.4.5)。候选观察:`report_screen_planner_obs` 候选写容器 `planner_opts` 槽(恒写,空桶照写)。字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」。

## 7. 子态与 overlay

「属性详情」面板 = 点卡上半部误触发的伴随形态,**未建模独立处理**(点卡 = 机械单发;面板若真弹出,后果归下一帧重入:外循环按当前画面重分派——详情 overlay 族分支或本 op 重走链;族注 = [README.md](README.md) §5.5)。

## 8. 守卫与防线

- 选中点 = area rect 相对几何(SELECT_Y_RATIO / DETAIL_MARGIN_RATIO 两比例,rect 单一源 = 建档;布局再漂移只更 yml)。
- press_time 加固(点卡与确认同参数;短按下不被采样的输入管线形态)。
- 详情面板检测分支已拆除(症状侧补丁退役;根治理 = 选中点几何)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「策划事件」;op 内日志 tag = `[cw-planner]`(决策 reason/左右卡)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(节点循环族两 node 形态锁:观察上报容器/入口门 miss fail/容器零参决策 + round_wait)。代码注引的 planner 策略接线锁/基建锁(test_cw_planner_strategy_wiring / test_cw_infra_locks)已不在册(开放设计注)。
- game 侧知识:事件机制 = [../../../../game/gameplay/currency_war.md](../../../../../game/gameplay/currency_war.md) 银狼策划事件节;建档与字段面 = `assets/game_data/screen_info/cw_hacker_planner.yml` + [../game_state/fields.md](../game_state/fields.md) §3.4.5。

## 开放设计注

- 本屏无 chosen_hack 写端:GameState 字段位已申报(fields.md §3.4.5)而画面档与 op 已在役,写端接线待批(申报不自定案)。
- 选中点击高度比例(71%)为单次交互实证的经验值,半区归属的充分统计待补。
