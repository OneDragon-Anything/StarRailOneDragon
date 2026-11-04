# 银狼升星二选一(planner · 货币战争-银狼升星)

> 代码 = `operations/cw_screen/cw_screen_yinlang.py::CwScreenYinLang`(两 node 直继承 `SrOperation`)。职责:银狼「我来当策划」策划事件 overlay 一次访问——OCR 两卡文字 → `decide_planner` 选卡 → 点卡下半部选中(press_time 加固)→ 确认步机械完成即结束本次访问。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/cw_yinlang_star_up.yml`。

## 1. 分发判定

- 阶段一身份分发(旧外循环分支编号已停用):id_mark 识别标志「货币战争-银狼升星.标识-我来当策划」;dispatch 带 on_fail_retry。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 触发 = 银狼**每个费用档**升达 2 星各弹一次(3/4/5 费各一次,非随机事件;判据单一源 = kernel 值回调 `cw_faction_callbacks.py` 银狼星级回调,每费用档簿记 = ScreenChanges.planner_tiers_fired 侧栏)→ 见 [../../../../game/gameplay/currency_war.md](../../../../../game/gameplay/currency_war.md)「银狼我来当策划事件」节。

## 2. 画面形态声明

**单选族例外**(有选择面但零逻辑态账——逻辑态 = 动作执行后不经观察、按游戏规则推算并直写状态容器(GameState)的预期状态,例:买牌后金币 −40、备战席 +1;下一帧观察与推算不符时以实际观察为准,下同;本屏选择不产生逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(观察 node + 决策动作 node 两个运行节点,合同 = [op-layer.md](op-layer.md) §1.1);**分发即门**(无 op 内入口守卫):观察 node = 左右两卡 OCR 桶一次读 → `report_screen_planner_obs` 落状态容器(状态容器 = GameState,游戏状态对象,下同)`planner_opts` 槽(恒两卡,空桶照写;无对局上下文(match/gs 缺席)的兜底路径跳过)→ obs 挂实例属性;决策动作 node = 零参决策 `match.strategy.decide_planner()`(候选自状态容器槽;唯一入口 = 策略对象,handler 禁 kernel 直调;委托 `kernel/cw_events.py::decide_planner` 升费卡打分含银狼线/在场判定,target_comp 决定银狼线加成,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E16;E 系编号 = 事件面编号,目录见该篇。「何时升费非最优」由策略模块表达,handler 不写死优先级)→ 点卡+确认链经 `CwActionPickPlannerOp` 派发(机械链+即时自上报在动作 op 内,选卡动作统一迁移批)→ **点击发出后即 `round_success` 结束本次访问、返回主循环**(即时上报形态:确认点击后动作 op 一口写完整结果,无落地复查、无证据标志;确认未生效由外循环重识别重派;`node_max_retry_times=5` 在用值仅框架异常路径消费)。无 chosen_* 写端。

## 3. 观察面

观察 node = 左右两卡 OCR 桶一次读(入口帧一次读,决策轮复用实例载体;恒两元素 0=左卡/1=右卡)。卡面读取 = 单次全图 OCR,文本归属 = **中心点落入建档两卡 rect**(`骇入选项-左卡/右卡`,坐标单一真相源回 yml;判定语义先例 = `_anchor_hit_full_ocr` 中心点同式;卡位 area 缺失 = observe round_fail 返回主循环重新识别画面,禁兜底 rect;捕获集变化申报 = 旧 y 带 [300,420] → 卡全域 rect,卡内文本全属该卡语义,classify 关键词匹配面不变)join 为 `PlannerOption(idx, text)`。观察 payload = `CwScreenPlannerObs`(`on_screen`/`options`/`screen`,位于 `kernel/cw_screen_report/planner.py`);report = `report_screen_planner_obs` 候选写状态容器 `planner_opts` 槽(恒写,空桶照写)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「返回主循环」= 本访问结束、控制权返回主循环 `cw_loop.py::CwLoop.loop` 重新识别画面并重判):

| 动作 op(动作类型清单参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickPlannerOp`(`CwActionPickPlannerParam`) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:选中点/`branch_type`/`norm_item` 载荷) | 即时单相 `report_action_pick_planner_param`(动作 op 确认点击后一口写,宿主 = `kernel/cw_action_report/pick_planner.py`:条件效果分支 rider 先行 → 装备效果分支入栏+获得后果链 / 升费效果分支变换窗三态+`lv999_cost_tier` 档行 / unknown 保留证据 / unrouted 兜底零写) | 是(发出即终结):点卡+确认链发出并上报后 `round_success` 结束本次访问、返回主循环;确认未生效由外循环重识别重派(见 §5) |

决策动作 node 选卡+确认链(点卡+确认+即时自上报整体经动作工厂 `cw_pick_planner_action.py::CwActionPickPlannerOp`,派发 param 携真实选中 idx;决策半留在画面 op 侧):

```
options = 观察轮 obs 载体 → decide_planner()(零参;候选读状态容器 planner_opts 槽)
target = _card_point(idx):卡 area(「骇入选项-左卡/右卡」)rect 相对几何推导
  = 中心 x + 71% 高度(卡下半部选中),详情钮避让 clamp(底缘上移 11% 比例);
  area 缺失 = act round_fail 零派发零点击返回主循环重新识别画面(禁兜底坐标)
→ 派发 CwActionPickPlannerOp(target 经 env;机械链在动作 op 内):
  mouse_move + click(press_time 0.15 常量,输入管线半死态短按下不采样的加固)
  → 1.2s 等选中动画
→ 确认:「按钮-骇入确认」建档查找点击(round_by_find_and_click_area,全族统一;
  area 缺失 = 显式失败交框架轮次,禁兜底坐标;机械部分完成即结束本次访问零判效——零判效 =
  执行侧不判定动作是否生效,落地事实归下一帧观察,下同)
→ 动作 op 确认点击后即时自上报完整结果(单相一口写)
→ 点击发出后 round_success 结束本次访问、返回主循环
```

交互陷阱:点卡上半部 = 弹「属性详情」非选中(选中点击几何治理,见 §7);布局漂移下绝对 y 常数会落卡外 → 选中失败 → 确认无效,防线 = 相对几何(只更 yml rect,本方法零改)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 选卡确认链发出完成 | **画面终结** | round_success 返回主循环重新分发(点击发出后即结束本次访问;确认未生效 = overlay 残留由外循环重识别重派) |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

本屏无 chosen_hack 写端(该字段位申报不变,fields.md §3.4.5)。**动作侧即时上报**:动作 op 确认点击后经 `report_action_pick_planner_param`(即时单相一口写,宿主 = `kernel/cw_action_report/pick_planner.py`)按效果分支写——条件效果分支 rider 先行;装备效果分支 `equips` 入栏+获得后果链 / 升费效果分支 `bench`/行域变换 + `lv999_cost_tier` 档行(fields.md §3.2.23)/ unknown 零记账+保留证据(弱化词卡文落此)/ unrouted 兜底零写。候选观察:`report_screen_planner_obs` 候选写状态容器 `planner_opts` 槽(恒写,空桶照写)。字段节 = [../game_state/fields.md](../game_state/fields.md) §3.2.23 / §3.4.5 / §4「事件选择」。

## 7. 子态与 overlay

「属性详情」面板 = 点卡上半部误触发的伴随形态,**未建模独立处理**(点卡 = 机械单发;面板若真弹出,后果归下一帧重入:外循环按当前画面重分派——详情 overlay 族分支或本 op 重走链;族注 = [README.md](README.md) §5.5)。

## 8. 守卫与防线

- 选中点 = area rect 相对几何(SELECT_Y_RATIO / DETAIL_MARGIN_RATIO 两比例,rect 单一源 = 建档;布局再漂移只更 yml)。
- press_time 加固(点卡与确认同参数;短按下不被采样的输入管线形态)。
- 详情面板检测分支已拆除(症状侧补丁已停用;根治理 = 选中点几何)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与测试面

- journal op 名 =「策划事件」;op 内日志 tag = `[cw-planner]`(决策 reason/左右卡)。
- 测试:`sr-od-test/test/sr_od/application/currency_war/test_screen_two_node_family.py`(节点循环族两 node 形态测试:观察上报状态容器/入口门 miss fail/状态容器零参决策 + round_wait)。代码注引的 planner 策略接入调用测试/基建测试(test_cw_planner_strategy_wiring / test_cw_infra_locks)已不已登记(开放设计注)。
- game 侧知识:事件机制 = [../../../../game/gameplay/currency_war.md](../../../../../game/gameplay/currency_war.md) 银狼策划事件节;建档与字段面 = `assets/game_data/screen_info/cw_yinlang_star_up.yml` + [../game_state/fields.md](../game_state/fields.md) §3.4.5。

## 开放设计注

- chosen_hack 字段位仍无写端(单相上报写的是效果分支域,非选择存证;fields.md §3.4.5 申报不变)。
- 选中点击高度比例(71%)为单次交互实证的经验值,半区归属的充分统计待补。
- 观察捕获集变化(旧 y 带 → 卡全域 rect)的实机交叉核对待实机窗口。
- 选择坐标观察上报待修问题(用户裁定 2026-09-22,op-layer.md §1.1「选择坐标
  观察上报」条款;全域/族级登记 = action_ops.md §4.5「坐标源待修问题」段,
  字段面 = fields.md §3.4.5a):
  planner_opts 观察载荷在用形态零坐标(observe 组装 PlannerOption(idx, text)),
  选中点几何位于决策半(_card_point 避开详情钮的点位推导)经 env.target 传入
  动作 op——收敛终态 = 坐标与归一化同次观察入状态容器(坐标单一真相源 = 观察
  上报)、策略只出下标、动作 op 按 idx 从状态容器取点执行;收敛归 pick 族
  族级统一改动(无对局上下文时 kernel 直调的兜底分支已删——用户裁决
  2026-09-22 全族删门,非「收敛保留」形态)。
