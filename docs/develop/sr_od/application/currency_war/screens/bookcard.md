# 星徽秘典四选一(bookcard · 货币战争-星徽秘典弹窗)

> 代码 = `operations/cw_screen/cw_screen_bookcard.py::CwScreenBookcard`(CwScreenOpBase 子类)。职责:星徽秘典四选一弹窗一次访问——OCR「XX星徽」卡名 → `decide_star_tome` 选卡 → 点卡即选(弹窗自关,无确认钮);选卡落地由重入裁决承载并补写 chosen_tome + 到账登记。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_star_tome_popup.yml`。

## 1. 分发判定

- 外循环分支 0i:id_mark 锚「货币战争-星徽秘典弹窗.标识-星徽秘典」(lcs 0.9);命中即接管,不放行备战分支。分发 = 阶段一身份行,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。五相位屏:重入裁决先于装配点分流(选卡 pending = 上轮已发选卡的星徽名;弹窗不在 = 选卡落地 → 此刻才写 chosen_tome + 到账登记 + success;弹窗在 = 点击未落地 → 重走计预算,不留幻影登记);门后读卡+选卡+机械交回链纯移入 `_handle_overlay`(两路径共享零转录);无 on_outcome 落地登记件。决策入口 = 契约 `decide_star_tome(factions, gs, session, config)`(返回 options 索引;打分:target 阵营命中 / board 已有阵营 / 配方框架阵营命中,权重 = `strategies/impl/pick_bias.py::PICK_BIAS` tome_* 常量;规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E17)。

## 3. 观察面

observe 段 = 入口门 + 轻观察帧引用;卡名读取归共享动作体 `_read_card_factions`:全屏 OCR,取「XX星徽」后缀文本(长度 > 2)→ [(阵营名, x 中心)] 左→右排序。观察 payload = `BookcardObservation`(仅帧引用);本屏不上报 GameState 容器观察(决策输入 = `game_state_of(match.session)` 视图)。

## 4. 动作面

读卡+选卡+机械交回链 `_handle_overlay`(两路径共享):

```
cards = _read_card_factions → idx = decide_star_tome([阵营名...], GameState 视图)
  (cards 空 / 无 match = idx 0 fallback)
target = _card_point(idx, faction_x):「星徽卡-1..4」area 中心;
  OCR x 已知时取 x 近邻 area(防 area 序与画面序错位);任一 area 缺失 = round_fail
  (禁裸坐标兜底)→ safe_click(bug#1 缓解)→ 1.0s
→ 置选卡 pending → round_retry(机械交回零判效;弹窗关没关由下一轮重入入口门裁决)
```

交互陷阱:点卡即选、弹窗自关(无确认步骤);fallback 轮(idx 0 无 OCR 依据)记名 = `(fallback卡1)` 哨兵值,落地裁决时哨兵名不登记(防幻影记录)。动作词表:画面 op 直驱;与备战词表 `OpenTome`(开秘密典籍道具)分属两域——本屏是弹窗选卡画面,OpenTome 是备战开道具动作。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入裁决弹窗不在(选卡落地) | **画面终结** | `_settle_picked_tome`(到账登记 + chosen_tome 写)→ round_success(wait = `CW_OVERLAY_SETTLE_S`)交回外循环重分发 |
| 重入裁决弹窗在(点击未落地) | 节点循环重入 | 重走重选(计 `node_max_retry_times=5` 预算,超 → FAIL bail) |
| 入口锚 miss / 星徽卡建档缺失 | op FAIL | 交回外循环重分发 |

「确认离开 = 画面终结」= [README.md](README.md) §6(本屏确认 = 点卡本身)。

## 6. 状态上报面

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
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens_step3.py`(迁移结构锁)、test_cw_game_state_consume.py(chosen_tome 接线锁)。代码注引的典籍通道锁(test_cw_fake_channels_outerloop)已不在册(开放设计注)。
- game 侧知识:画面与机制(星徽 = 阵营徽记装备) = [../../../../game/screens/currency_war_star_tome_popup.md](../../../../../game/screens/currency_war_star_tome_popup.md)。
