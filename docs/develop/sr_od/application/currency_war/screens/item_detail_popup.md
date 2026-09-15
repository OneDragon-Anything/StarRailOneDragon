# 道具详情弹窗(item_detail_popup · 货币战争-道具详情弹窗)

> 代码 = `operations/cw_screen/cw_screen_item_detail_popup.py::CwScreenItemDetailPopup`。职责:获得道具(聘用书类)后自动弹出的介绍 modal(0e3)的一次访问——点 × 关闭交回。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 0e3:OCR「聘用书」(lcs 0.8)∧ **祈愿排他**(`货币战争-祈愿试炼.标识-祈愿试炼` 不命中)。排他双写于外循环分支与本 op `entry_ok`(两处同参):祈愿试炼选项名含「聘用书」,无排他即截胡 0h 分支死循环——排他是本分支判据承重件,非装饰。建档 = `currency_war_item_detail.yml`,**有档案但无 id_mark**(仅「按钮-关闭」定位区)→ 入口维持 OCR 回退;档案补 id_mark 后可切 area 锚(切换属实施批内部对齐,ADR-0584 §2.2)。

## 2. 画面形态声明

**空决策形态**(纯推进)。推进型变体(`_progression_base.py::CwProgressionScreenOp` 子类):入口观察 → 单次推进 → 重入观察裁决交回;节点预算 = 2(合同 = [../flow/screen_op.md](../flow/screen_op.md))。

## 3. 观察面

轻观察:入口/重入观察 = `entry_ok` OCR+排他复判(payload = None)。零 GameState 写端。

## 4. 动作面

`progress_once` = 读 `货币战争-道具详情弹窗.按钮-关闭` center(`kernel/cw_obs_core.py::area_center`)→ `mouse_move`+`click`(bug#1 缓解)。坐标缺失 = False → 基类 `round_fail`。

## 5. 终结与交回

推进已发 → `round_retry` 重入;重入 = OCR∧排他复判,不命中 = 已离开 → `success` 交回;预算耗尽 FAIL 交回。落点:祈愿帧让路 0h,其余 = 获得道具语境的底层屏(备战/补给等)重判。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件;道具入包由下一帧观察侧重锚。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理(祈愿屏形态被排他条款排除,不接管)。

## 8. 守卫与防线

节点预算 = 2(基类合同);无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「道具详情弹窗」;frame_tag = `overlay_item_detail`(dispatch 包装,on_result 日志闭包)。测试锁:无点名行为锁(骨架锁随基类,锁面根 = `sr-od-test/test/sr_od/application/currency_war/`);建档 = `currency_war_item_detail.yml`。

## 开放设计注

- 档案 id_mark 缺位(OCR 回退根因);排他双写的单一源化候批——两处同参目前靠纪律维持,漂移无锁。
