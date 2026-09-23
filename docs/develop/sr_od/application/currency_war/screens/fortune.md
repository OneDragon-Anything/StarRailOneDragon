# 命运卜者强化三选一(fortune · 货币战争-命运卜者强化)

> 代码 = `operations/cw_screen/cw_screen_fortune.py::CwScreenFortune`(两 node 直继承 `SrOperation`)。职责:命运卜者「强化效果三选一」overlay 一次访问——OCR 三卡文字 → 战力关键词加权选卡 → 点卡下半部选中 + 确认机械交回。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/cw_fortune_picker.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役):**双 id_mark 门**——「货币战争-命运卜者强化.标识-命运卜者」∧「货币战争-命运卜者强化.标识-请选择强化效果」同帧命中;dispatch 带 on_fail_retry(失败消费重试池)。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1);**分发即门**(无 op 内入口守卫):观察 node = 三卡位 OCR 一次读 + 三卡点击坐标 → `report_screen_fortune_obs` 双写容器 `fortune_opts`/`fortune_opts_xy` 槽(空表照写)→ obs 挂实例属性;决策动作 node = 顶部重入出口门(确认已发 → OCR「命运卜者」不在 = overlay 已关 → success 交回)→ 零参决策 `match.strategy.decide_fortune()`(候选自容器槽;判据单一源 = kernel `cw_events.py::decide_fortune` 战力关键词加权,唯一入口 = 策略对象,handler 禁自拟打分;事件面判据目录 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §2)。屏内无兜底:决策返回词表外/None = 具名 round_fail 零盲发交外循环(op-layer.md §1.1 出口③);idx 越界 = 守卫断言 AssertionError、策略异常自然传播(含离屏失约 ValueError,op-layer.md §1.3);两守卫均在派发前零点击,fail 出口非循环出口、非防御上限;选卡派发 = 策略产 `CwActionPickFortuneParam` 直发,流程侧零值域改写;无 match 局外不设早退支(用户裁决 2026-09-22 全族删门);点击坐标 = 动作 op 自容器 `fortune_opts_xy` 读(坐标随报条款)。选卡确认链经 `CwActionPickFortuneOp` 派发(机械链+自上报在动作 op 内,pick-op-unify 批)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=5` 现役值仅框架异常路径消费)。无 chosen_* 写端。

## 3. 观察面

观察 node = 三卡位 OCR 一次读(入口帧一次读,决策轮复用实例载体)。卡面读取 `_read_cards`:全图 OCR,文本带 y 290-410(卡文字带,避详情按钮),按 x 近邻分流到三卡槽(槽 x 常量数组,容差 190),同桶 join。观察 payload = `CwScreenFortuneObs`(`on_screen`/`options`/`option_points`/`screen`,住 `kernel/cw_screen_report/fortune.py`);report = `report_screen_fortune_obs` 候选写容器 `fortune_opts` 槽(无空门直写,空表照写;match/gs 缺席的局外路径跳过 report——report 跳写 = 容器写闸,与决策无关;无 match 局外不设早退支,用户裁决 2026-09-22 全族删门,见 §2)。观察同步上报三卡点击坐标(建档「卡-强化1/2/3」area 主源 + 兜底常量,空读照报;坐标随报条款)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickFortuneOp`(`CwActionPickFortuneParam`) | 注册表工厂 `action_op_for`(派发实例 = 策略产 `CwActionPickFortuneParam`,守卫后直发;局外臂已按 op-layer.md §1.1 :37 退役,match 臂直发 = 唯一构造点;决策半组装 `OverlayPickExecEnv` 仅携 op(env.idx/target 停喂);点选与确认均在动作 op 内,点卡坐标 = 动作 op 按下标自容器 `fortune_opts_xy` 读,确认钮 = op 类体内「按钮-确认选择」建档查找点击) | 自上报 `report_action_pick_fortune_param`(零写族单相:机械链发出后即全相,发射相意图遥测,容器零写等观察覆盖) | 否(非终结):发出后 `round_wait` 循环推进;落地由重入出口门判——OCR「命运卜者」不在 = overlay 已关 = `round_success` 交回外循环(见 §5) |

决策动作 node 选卡+确认链(整体经动作工厂 `cw_pick_fortune_action.py::CwActionPickFortuneOp` 派发,pick-op-unify 批;机械链+自上报零写在动作 op 内,派发 param 携真实选中 idx):

```
重入出口门(决策动作 node 顶部):_confirm_pending 置位 → OCR「命运卜者」(lcs 0.5)不在 =
  overlay 已关(上轮确认已落地)→ success 交回外循环;在 = 重走选卡+确认
局外:无 match 局外不设早退支——单跑缺上下文沿正常链路失败即预期(用户裁决 2026-09-22 全族删门)
texts = 观察轮 obs 载体 → decide_fortune()(零参;候选读容器 fortune_opts 槽)
守卫①:pick 非 `CwActionPickFortuneParam`(None/词表外)→ round_fail(含原值)零盲发
守卫②:pick.idx 越界 [0, 3) → AssertionError(禁钳位)
→ 置 _confirm_pending → 派发(env 仅携 op;env.target/idx 停传)
  (动作 op 内:target = 容器 fortune_opts_xy[pick.idx](坐标随报条款;缺 = 守卫断言)
   → target safe_click(防吞点击) → 1.2s
   → 确认:「按钮-确认选择」area 查找点击(round_by_find_and_click_area,全族统一;零判效)
   → 自上报 report_action_pick_fortune_param)
```

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入出口门「命运卜者」不在 | **画面终结** | round_success 交回外循环重分发 |
| 出口门在(确认未落地) | 节点循环重入 | 重走选卡+确认(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |
| 决策无有效输出/返回词表外/idx 越界/策略异常 | 守卫 fail(op FAIL) | round_fail(含原值)/ 框架异常路径(留证截图 + node_max_retry_times=5 预算耗尽)交回外循环;连续 fail 由外环 fail 重派网兜底(flow/README §4) |
| 局外无 match | 不设早退支(op-layer.md §1.1;用户裁决 2026-09-22 全族删门) | 未支持用法:单跑缺上下文沿正常链路自然失败,局内不达此态 |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

本屏无 chosen_fortune 写端、无到账登记(选择后果走下一帧观察覆盖;GameState 字段位 `chosen_fortune` 先申报无写端,fields.md §3.4.5)。候选观察:`report_screen_fortune_obs` 候选写容器 `fortune_opts` 槽(空表照写)。字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」。

## 7. 子态与 overlay

本屏无子态。点卡上半部会触发「属性详情」面板(详情按钮带避让由点卡坐标承担,坐标单一源 = 建档「卡-强化1/2/3」);面板残留归下一帧重入自愈(重分发/详情 overlay 族分支,族注 = [README.md](README.md) §5.5)。

## 8. 守卫与防线

- 双 id_mark 门防与策划系同族画面互派(布局同族:标题+指令+N 卡+确认)。
- 决策返回契约守卫:decide_fortune 返回 None/词表外 = 具名 round_fail 零盲发、策略异常自然传播(原「越界防御/策略失败 fallback 第1张」退役申报)。
- 值域守卫:pick idx 越界 = 守卫断言 AssertionError(原「静默钳 0」退役申报)。
- 点击 y 避让详情按钮带(同策划事件交互教训的几何防线;坐标随报收敛后避让几何归观察侧建档「卡-强化1/2/3」,动作 op 自容器取点)。
- OCR 空文本帧 = 全零打分落首卡(kernel 判据侧合法缺省 = `cw_events.decide_fortune` 无匹配缺省卡 1,非流程侧兜底;决策出口处置见本节守卫两条)——与 box_pick 的「OCR 未读 = fail 交回」纪律不同,本屏选错代价低。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「命运卜者」;画面 op 日志 tag = `[cw][fortune]`(选卡行:卡文与选卡序号);选卡确认链(`cw_pick_fortune_action.py::CwActionPickFortuneOp`)日志 tag = `cw-pick-fortune`(点卡 `safe_click`;确认 = 「按钮-确认选择」`round_by_find_and_click_area` 建档查找点击,全族统一)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(节点循环族两 node 形态锁:观察上报容器/入口门 miss fail/容器零参决策 + round_wait)。
- game 侧知识:无独立 game 画面档(建档与字段面 = `assets/game_data/screen_info/cw_fortune_picker.yml` + [../game_state/fields.md](../game_state/fields.md) §3.4.5)。
