# 命运卜者强化三选一(fortune · 货币战争-命运卜者强化)

> 代码 = `operations/cw_screen/cw_screen_fortune.py::CwScreenFortune`(CwScreenOpBase 子类)。职责:命运卜者「强化效果三选一」overlay 一次访问——OCR 三卡文字 → 战力关键词加权选卡 → 点卡下半部选中 + 确认机械交回。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/cw_fortune_picker.yml`。

## 1. 分发判定

- 外循环分支 0a3:**双 id_mark 门**——「货币战争-命运卜者强化.标识-命运卜者」∧「货币战争-命运卜者强化.标识-请选择强化效果」同帧命中;dispatch 带 on_fail_retry(失败消费重试池)。分发 = 阶段一身份行,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。五相位屏:**分发即门**(无 op 内入口守卫;round_retry 重入 → `_handle_overlay` 顶部出口门补位);无 on_outcome 落地登记件;无 chosen_\* 写端。选卡判据 = op 内联战力关键词加权(v1 文本策略,词与权重住本文件 `_handle_overlay`;事件面判据目录 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §2,本屏未接 pick 族九接口)。

## 3. 观察面

observe 段 = 轻观察帧引用(卡面读取归共享动作体现役内聚)。卡面读取 `_read_cards`:全图 OCR,文本带 y 290-410(卡文字带,避详情按钮),按 x 近邻分流到三卡槽(槽 x 常量数组,容差 190),同桶 join。观察 payload = `FortuneObservation`(仅帧引用);本屏不上报 GameState 容器观察。

## 4. 动作面

选卡+确认链 `_handle_overlay`(两路径共享):

```
重入出口门:_confirm_pending 置位 → OCR「命运卜者」(lcs 0.5)不在 = overlay 已关
  (上轮确认已落地)→ success 交回外循环;在 = 重走选卡+确认(计节点预算)
texts = _read_cards → 关键词加权 argmax(全零 = 首卡)
target = (槽 x 常量[best], 卡身 y 常量 480)——点卡下半部选中,避详情按钮带
  → safe_click(bug#1 缓解)→ 1.2s
→ 置 _confirm_pending → 确认:「按钮-确认选择」center(建档 rect 中心,
  兜底常量同按钮)→ emit_overlay_confirm(裁决词「命运卜者」;机械交回零判效)
```

动作词表:画面 op 直驱。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入出口门「命运卜者」不在 | **画面终结** | round_success 交回外循环重分发 |
| 出口门在(确认未落地) | 节点循环重入 | 重走选卡+确认(计 `node_max_retry_times=5` 预算,超 → FAIL bail) |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

本屏无 chosen_fortune 写端、无到账登记(选择后果走下一帧观察覆盖;GameState 字段位 `chosen_fortune` 先申报无写端,fields.md §3.4.5)。字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」。

## 7. 子态与 overlay

本屏无子态。点卡上半部会触发「属性详情」面板(详情按钮带避让由点击 y 常量承担);面板残留归下一帧重入自愈(重分发/详情 overlay 族分支,族注 = [README.md](README.md) §5.5)。

## 8. 守卫与防线

- 双 id_mark 门防与策划系同族画面互派(布局同族:标题+指令+N 卡+确认)。
- 点击 y 避让详情按钮带(同策划事件交互教训的几何防线)。
- OCR 空文本帧 = 全零打分落首卡(有界重试兜底,非盲选禁令屏——与 box_pick 的「OCR 未读 = fail 交回」纪律不同,本屏选错代价低)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「命运卜者」;op 内日志 tag = `[cw-fortune]`(卡文/选卡序号)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens_step3.py`(迁移结构锁)。
- game 侧知识:无独立 game 画面档(建档与字段面 = `assets/game_data/screen_info/cw_fortune_picker.yml` + [../game_state/fields.md](../game_state/fields.md) §3.4.5)。
