# 中断挑战弹窗(interrupt_dialog · 货币战争-中断挑战弹窗)

> 代码 = `operations/cw_screen/cw_screen_interrupt_dialog.py::CwScreenInterruptDialog`。职责:ESC 误按/误点左上角弹出的「是否中断挑战」真模态(1g)的一次访问——点右上 X 关闭继续对局。**语义红线:绝不点「放弃并结算」**(不可逆放弃进度),不点「暂时离开」(免中断对局)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 1g:锚 = `货币战争-中断挑战弹窗.标识-中断挑战`(id_mark;序位在备战分支后,序位表 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。真模态:点遮罩无效,关闭只有 X 一条路;建档 = `currency_war_interrupt_dialog.yml`(「按钮-放弃并结算」「按钮-暂时离开」为在册定位区,op 零消费)。

## 2. 画面形态声明

**空决策形态**(纯推进;弹窗带选项面但选择被语义红线钉死为唯一出口——关 X,放弃/离开永不候选)。推进型变体(`_progression_base.py::CwProgressionScreenOp` 子类):入口观察 → 单次推进 → 重入观察裁决交回;节点预算 = 2(合同 = [../flow/screen_op.md](../flow/screen_op.md))。

## 3. 观察面

轻观察:入口/重入观察 = `entry_ok` 基类 area 锚原语。零 GameState 写端——弹窗内「小队生命值」为 HP 真值快照,对账备用、暂不消费。

## 4. 动作面

`progress_once` = `round_by_find_and_click_area(货币战争-中断挑战弹窗.按钮-关闭)`(单尝试合同:按钮不在〔旧帧/已自关〕不再原地新帧重找,False 交基类 fail——新帧重试在 loop 级承载,外循环重派即新帧)。点击成功 → `park_cursor(after_wait=0.1)`(光标离场防污染下一帧)。刻意不用 ESC:X 永远安全,ESC 在面板已关时落备战会再弹本弹窗。

## 5. 终结与交回

推进已发 → `round_retry` 重入;重入 = 锚 miss = 已离开 → `success` 交回;预算耗尽 FAIL 交回(分发行未挂 `on_fail_retry`,fail 走包装缺省映射——区别于 0t/1b 的 retry 池通道)。落点 = 备战(1 分支重判,对局继续)。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件(关闭对局无状态变更)。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理,底层(备战)交回重判。

## 8. 守卫与防线

节点预算 = 2(基类合同);「放弃并结算」不可逆红线由动作面排除(唯一动作 = X)承载,无第二道防线;无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「中断挑战弹窗」;frame_tag = `overlay_interrupt_dialog`(dispatch 包装)。
- 测试锁:无点名行为锁(骨架锁随基类;锁面根 = `sr-od-test/test/sr_od/application/currency_war/`);建档 = `currency_war_interrupt_dialog.yml`。
