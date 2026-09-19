# 武装箱四选一选卡(box_pick · 货币战争-备战-武装箱选择)

> 代码 = `operations/cw_screen/cw_screen_box_pick.py::CwScreenBoxPick`(两 node 直继承 `SrOperation`)。职责:备战环 `OpenBox` 终结化开箱后弹出的武装箱四选一选卡画面——OCR 卡名 → `decide_box_card` 选卡 → 点卡选中即确认(单步,无独立确认钮);**选卡即终结交回**(选卡落地由下一帧观察覆盖)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_battle_prep_supply_box.yml`。

## 1. 分发判定

- 外循环分支 0f2:id_mark 锚「货币战争-备战-武装箱选择.标识-请选择」。入口链 = 备战访问内 `OpenBox` 点开启(**终结化**——开箱即交回外循环)→ 外循环按本画面分发本 op。分发 = 阶段一身份行(选卡画面盖备战,历史无身份行时误派备战 op ping-pong);单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 与 0f(货币战争-武装箱弹窗,道具获得说明弹窗,`CwScreenArmoryBox` 只关弹窗)是兄弟画面不同职责:0f = 展示弹窗关闭,0f2 = 选卡画面。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3;选卡即终结,单步无确认)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 两道闸(入口锚复验,分发即门 op 内机械复验防误派;OCR 卡名空 = 未发出通道)→ 任一 miss = round_fail 交回外循环重派(重观察语境禁猜,禁盲点首卡;report 不调,容器不进盲值)→ `report_screen_box_pick_obs` 落容器 `box_card_names` 槽 → obs + OCR 坐标挂实例属性。决策动作 node = 选卡决策 → 选卡链经 `CwActionPickBoxCardOp` 派发(点卡选中即确认 + 动画等待迁入动作 op,pick-op-unify 批)→ round_success 交回(选卡落地由下一帧观察覆盖;op 内零重试轮,重试预算归外循环重分发;`node_max_retry_times=5` 现役值仅框架异常路径消费)。零参决策 `match.strategy.decide_box_card()`(候选自容器槽;局内 fail-closed:异常留证完整栈后显式上抛 / 返回越界索引同上抛——两者都禁无声回落内联打分,策略 bug 禁永久遮蔽;局外防御 = kernel 机器空键纯通用排序;薄壳语义:locked_comp 两态锚 + 三本库存账 → 共享机器 `kernel/cw_equip_value.py::pick_equipment` 序数分档,key 直击 > 近兑现 > 材料 > 通用,base = 通用输出先验;规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E18)。

## 3. 观察面

单次观察(观察 node):入口锚复验(分发即门,op 内机械复验防误派;「标识-请选择」miss = 非本画面 → fail 交回外循环重分发)→ 卡名读取 `_read_card_names`:「区域-卡名行」建档 rect 约束 OCR,2-8 字过滤,按 x 升序 → [(卡名, 卡 x 中心)]。观察 payload = `CwScreenBoxPickObs`(`on_screen`/`card_names`/`screen`,住 `kernel/cw_screen_report/box_pick.py`);report = `report_screen_box_pick_obs` 候选写容器 `box_card_names` 槽(两道闸过才写;match/gs 缺席的局外兜底路径跳过)。x 坐标留守本 op 不进容器(点击定位输入)。

## 4. 动作面

```
names = 观察轮 obs 载体
  → 空 = round_fail(OCR 未读卡名(变体字型/动画帧)= 未发出通道交回外循环
    重派,重观察语境禁猜;禁「盲点首卡」兜底——选错不可逆;闸在观察 node)
idx = _decide_card_index(决策动作 node):
  局内 = decide_box_card()(零参;候选读容器 box_card_names 槽;
    fail-closed:异常留证完整栈后显式上抛 / 返回越界索引
    同上抛——两者都禁无声回落内联打分,策略 bug 禁永久遮蔽)
  局外 = kernel pick_equipment(机器空键)
card_point = (选中卡 x 中心, 卡身 y 常量 290)(点卡名带下方一点,避「查看详情」按钮)
→ 派发 CwActionPickBoxCardOp(动作 op 内:target mouse_move + click
  [bug#1 缓解]→ 点卡选中即确认[单步]→ 固定动画等待
  [_OVERLAY_ANIM_WAIT_S = prep_actions overlay 动画等待常量]
  → 自上报 report_action_pick_box_card_param;派发 param 携真实选中 idx)
→ round_success(选卡即终结,交回外循环)
```

选卡+确认+自上报经动作工厂(`CwActionPickBoxCardOp`)派发;武装箱选卡不属备战动作词表(与备战 `OpenBox` 开箱动作分属两域)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 点卡成功 | **选卡即终结** | round_success 交回外循环(选卡落地由下一帧观察覆盖;与 `OpenBox` 终结化交回等待同源) |
| 入口锚 miss / OCR 未读卡名 | op FAIL | 交回外循环按当前画面重分发(重派重观察) |
| 决策契约违约 | 异常上抛 | fail-closed(留证后上抛,禁回落) |

「确认离开 = 画面终结」= [README.md](README.md) §6(本屏确认 = 点卡本身);`node_max_retry_times=5` 现役值仅框架异常路径消费。

## 6. 状态上报面

本屏无 chosen_\* 写端、无到账登记(装备到账归下一帧 owned 观察覆盖)。候选观察:`report_screen_box_pick_obs` 候选写容器 `box_card_names` 槽(两道闸过才写)。字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5(「装备三选一」与武装箱选择面同屏性待采证注)/ §4「事件选择」;效果账 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §2(显式不建模清单:OpenBox 箱体消耗在选卡确认)。

## 7. 子态与 overlay

本屏无子态。同一武装箱域的两画面分工:0f 说明弹窗(关闭动作,非本 op)/ 0f2 选卡画面(本 op);建档中「装备卡-1..4」area 为画面元素档,现役点击坐标 = OCR x + 卡身 y 常量(区域-卡名行 rect 为读数单一源)。

## 8. 守卫与防线

- 决策 fail-closed 契约:策略异常/越界索引 = 留证后上抛,禁无声回落内联打分(策略 bug 禁遮蔽;行为锁在册)。
- OCR 未读卡名 = 未发出通道 fail 交回重派(选错不可逆,禁盲点兜底)。
- 点击 y 避让「查看详情」按钮带(几何防线)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「武装箱选择」(0f2 分发);op 内日志 tag = `[cw][boxpick]`(选中卡名/交回)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_progression_inline.py`(box_pick 观察 report 接线/两道闸 skip report/点卡决策锁)、test_cw_unified_action_2a.py::test_pick_box_decision_fail_closed(fail-closed 决策契约行为锁 + 画面常量)。
- game 侧知识:画面与机制 = [../../../../game/screens/currency_war_battle_prep_supply_box.md](../../../../../game/screens/currency_war_battle_prep_supply_box.md);决策规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E18。

## 开放设计注

- 0f2 分发锚(「货币战争-备战-武装箱选择.标识-请选择」)未登记外循环分发锚预检表 `cw_loop.py::DISPATCH_AREA_ANCHORS`(iter1 可解析性预检覆盖缺该行,申报不自定案)。
