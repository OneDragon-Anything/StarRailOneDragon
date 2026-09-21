# 消耗品详情浮层(consumable_overlay · 无独立画面档)

> 代码 = `operations/cw_screen/cw_screen_consumable_overlay.py::CwScreenConsumableOverlay`。职责:获消耗品奖励后游戏自动弹出的介绍 modal(0f′)的一次访问——点右上 × 关闭交回。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环阶段三特殊规则(无独立画面档):双 OCR 条件「消耗品」∧「拖动到」(lcs 0.9),判定留外循环([../flow/outer_loop.md](../flow/outer_loop.md) §2.2);`entry_ok` 与分发判定**同源同参**。无画面档(op 无画面档名属性;关闭钮借道同族「道具详情弹窗」档,见 §4):「消耗品」= 类型 label、「拖动到」= 拖动使用说明(仅消耗品详情 modal 有,备战底部消耗品栏无),两条件合取不误匹配备战。

## 2. 画面形态声明

**空决策形态**。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(双 OCR 复判,与分发判定同源同参;miss = round_fail 交回外循环重判)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部重入裁决(推进已发 → 双 OCR 不命中 = 已离开本画面 → success 交回)→ 点 × 单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 现役值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

轻观察:观察 node = `entry_ok` 双 OCR 复判 → obs = `CwScreenConsumableOverlayObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/consumable_overlay.py`;无 report 接口)。零 GameState 写端。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——单步推进留守 op 内(`progress_once` 点 × 关闭) | 画面 op 留守臂(`progress_once`:`area_center` 读 `货币战争-道具详情弹窗.按钮-关闭` center + `mouse_move`+`click`) | 无 report 接口(推进型规范形态,op-layer.md §3) | 是(重入裁决:点 × 已发 ∧ 双 OCR 均不命中 = 已离开 → `round_success` 交回;命中 = `round_wait` 再推进) |

`progress_once` = 读 `货币战争-道具详情弹窗.按钮-关闭` center(消耗品 modal 与聘用书 modal 同为道具详情弹窗家族,× 同位,借道同族档案)→ `mouse_move`+`click`(bug#1 缓解,与 `cw_screen_item_detail_popup.py::CwScreenItemDetailPopup` 同式)。坐标缺失 = False → 决策动作 node `round_fail`。刻意不用 ESC:× 永远安全,ESC 在 modal 已自关时落备战会误弹「中断挑战」。

## 5. 终结与交回

推进已发 → `round_wait` 重入;重入 = 双 OCR 复判,双条件不命中 = 已离开 → `success` 交回(无防御上限)。落点 = 底层屏(投资策略/备战等获得消耗品语境)重判。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件;消耗品入包由下一帧观察侧重锚。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理(点 ×),底层屏交回重判。

## 8. 守卫与防线

`node_max_retry_times=2` 现役值仅框架异常路径消费;无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「消耗品浮层」;frame_tag = `overlay_consumable`(dispatch 包装)。测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_progression_inline.py`(推进型骨架内联形态锁,consumable_overlay 在册);关闭坐标借道 `currency_war_item_detail.yml`。

## 开放设计注

- × 坐标在消耗品帧上未实机复点(代码模块头在案申报),复点核实候实机批;装备类详情 modal(无「拖动到」签名)为未覆盖长尾,观察到再补。
