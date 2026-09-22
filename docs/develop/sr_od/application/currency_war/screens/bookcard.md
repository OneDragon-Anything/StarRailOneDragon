# 星徽秘典四选一(bookcard · 货币战争-星徽秘典弹窗)

> 代码 = `operations/cw_screen/cw_screen_bookcard.py::CwScreenBookcard`(两 node 直继承 `SrOperation`)。职责:星徽秘典四选一弹窗一次访问——OCR「XX星徽」卡名 → `decide_star_tome` 选卡 → 点卡即选(弹窗自关,无确认钮);选卡落地由重入裁决承载并补写 chosen_tome + 到账登记。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_star_tome_popup.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役,不引 0x):id_mark 锚「货币战争-星徽秘典弹窗.标识-星徽秘典」(lcs 0.9);命中即接管,不放行备战分支。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(「标识-星徽秘典」,miss = round_fail 交回外循环重判)→ 卡阵营名一次读 → `report_screen_bookcard_obs` 落容器 `star_tome_opts` 槽 → obs + 候选坐标挂实例属性。决策动作 node = 顶部重入裁决(选卡 pending = 上轮已发选卡的星徽名;弹窗不在 = 选卡落地 → 此刻才写 chosen_tome + 到账登记 + success;弹窗在 = 点击未落地 → 重走重选,不留幻影登记)→ 零参决策 `match.strategy.decide_star_tome()`(候选自容器槽;打分:target 阵营命中 / board 已有阵营 / 配方框架阵营命中,权重 = `strategies/impl/pick_bias.py::PICK_BIAS` tome_* 常量,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E17)→ 选卡链经 `CwActionPickStarTomeOp` 派发(点卡即选机械链+自上报在动作 op 内,pick-op-unify 批)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=5` 现役值仅框架异常路径消费)。

## 3. 观察面

观察 node = 入口门(「标识-星徽秘典」)+ 卡阵营名一次读(每访问恰一次,决策轮复用实例载体);卡名读取 `_read_card_factions`:全屏 OCR,取「XX星徽」后缀文本(长度 > 2)→ [(阵营名, x 中心)] 左→右排序。观察 payload = `CwScreenBookcardObs`(`on_screen`/`options`/`screen`,住 `kernel/cw_screen_report/bookcard.py`);report = `report_screen_bookcard_obs` 候选写容器 `star_tome_opts` 槽(空候选不写,闸在 report 内;match/gs 缺席的局外兜底路径跳过)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickStarTomeOp`(`CwActionPickStarTomeParam`) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:定位点,星徽卡 area OCR x 近邻锚) | 自上报 `report_action_pick_star_tome_param`(零写族,容器零写) | 否(非终结):发出后 `round_wait` 循环推进;落地由重入裁决判——「货币战争-星徽秘典弹窗.标识-星徽秘典」不在 = `_settle_picked_tome`(ConfirmTome 到账登记 + `chosen_tome` 写)+ success 交回外循环(见 §5) |

决策动作 node 读卡+选卡+机械交回链(整体经动作工厂 `cw_pick_star_tome_action.py::CwActionPickStarTomeOp` 派发,pick-op-unify 批;机械链+自上报零写在动作 op 内,派发 param 携真实选中 idx):

```
cards = 观察轮实例载体 → idx = decide_star_tome()(零参;候选读容器 star_tome_opts 槽)
  (cards 空 / 无 match = idx 0 fallback)
target = _card_point(idx, faction_x):「星徽卡-1..4」area 中心;
  OCR x 已知时取 x 近邻 area(防 area 序与画面序错位);任一 area 缺失 = round_fail
  (禁裸坐标兜底)→ 置选卡 pending → 派发
  (动作 op 内:target safe_click[bug#1 缓解]→ 1.0s
   → 自上报 report_action_pick_star_tome_param)
  (机械交回零判效;弹窗关没关由下一轮重入裁决)
```

交互陷阱:点卡即选、弹窗自关(无确认步骤);fallback 轮(idx 0 无 OCR 依据)记名 = `(fallback卡1)` 哨兵值,落地裁决时哨兵名不登记(防幻影记录)。与备战词表 `OpenTome`(开秘密典籍道具)分属两域——本屏是弹窗选卡画面,OpenTome 是备战开道具动作。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入裁决弹窗不在(选卡落地) | **画面终结** | `_settle_picked_tome`(到账登记 + chosen_tome 写)→ round_success(wait = `CW_OVERLAY_SETTLE_S`)交回外循环重分发 |
| 重入裁决弹窗在(点击未落地) | 节点循环重入 | 重走重选(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |
| 入口锚 miss / 星徽卡建档缺失 | op FAIL | 交回外循环重分发 |

「确认离开 = 画面终结」= [README.md](README.md) §6(本屏确认 = 点卡本身)。

## 6. 状态上报面

- 候选观察:`report_screen_bookcard_obs` 候选写容器 `star_tome_opts` 槽(空候选不写)。
- `chosen_tome` write_logic(重入裁决点写;值 = 选中卡阵营名)。
- 到账登记 `ConfirmTome`(`kernel/cw_exec_state.py::apply_confirm_effect` dict 分支,owned += 「X星徽」;OCR 卡名已去后缀作阵营名,登记时回拼全名,已是全名则原样)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」;到账登记 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §2(ConfirmTome 行)。

## 7. 子态与 overlay

本屏无子态。建档在册「按钮-关闭」(×)area 为画面元素档,本 op 不消费(选卡即关,无独立关闭路径)。

## 8. 守卫与防线

- 星徽卡 area 缺失 = round_fail(坐标单一真相源,禁裸坐标兜底)。
- x 近邻锚 = 选中卡的 OCR x(决策后取,防把候选首位当选中位)。
- 落地裁决点写(防未落地轮留幻影登记);fallback 哨兵名不登记。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「星徽秘典」;op 内日志 tag = `[cw-flow-bookcard]`(候选/选中/点击点)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(节点循环族两 node 形态锁:观察上报容器/入口门 miss fail/wish·tome 落地裁决时点写)、test_cw_game_state_consume.py(chosen_tome 接线锁)。代码注引的典籍通道锁(test_cw_fake_channels_outerloop)已不在册(开放设计注)。
- game 侧知识:画面与机制(星徽 = 阵营徽记装备) = [../../../../game/screens/currency_war_star_tome_popup.md](../../../../../game/screens/currency_war_star_tome_popup.md)。
