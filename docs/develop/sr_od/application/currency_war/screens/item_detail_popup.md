# 道具详情弹窗(item_detail_popup · 货币战争-道具详情弹窗)

> 代码 = `operations/cw_screen/cw_screen_item_detail_popup.py::CwScreenItemDetailPopup`。职责:获得道具(聘用书类)后自动弹出的介绍 modal(外循环「道具详情弹窗」分支)的一次访问——点 × 关闭、结束本次访问主循环。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环「道具详情弹窗」分支:OCR「聘用书」(lcs 0.8)∧ **祈愿排他**(`货币战争-祈愿试炼.标识-祈愿试炼` 不命中)。排他双写于外循环分支与本 op `entry_ok`(两处同参):祈愿试炼选项名含「聘用书」,无排他即截胡祈愿分支死循环——排他是本分支判据承重件,非装饰。建档 = `currency_war_item_detail.yml`,**有档案但无 id_mark**(仅「按钮-关闭」定位区)→ 入口维持 OCR 回退;档案补 id_mark 后可切 area 识别标志(切换属实施时的内部对齐事项)。

## 2. 画面形态声明

**空决策形态**(纯推进:不问策略器,只做固定的观察与推进动作)。两 node 直继承 `SrOperation`(观察 node + 决策动作 node 两个运行节点,合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(`entry_ok` OCR「聘用书」∧ 祈愿排他复判,与分发判定同源同参;miss = round_fail 返回主循环重新判定)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部落地复查(落地复查 = 动作发出后下一轮检查上一动作是否已生效——画面标志消失;下同。推进已发 → 门不命中 = 已离开本画面 → success 结束本次访问)→ 点 × 单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 在用值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

轻观察:观察 node = `entry_ok` OCR+排他复判 → obs = `CwScreenItemDetailPopupObs`(`on_screen`/`screen`,位于 `kernel/cw_screen_report/item_detail_popup.py`;无 report 接口)。零 GameState 写端。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「返回主循环」= 本访问结束、控制权返回主循环 `cw_loop.py::CwLoop.loop` 重新识别画面并重判):

| 动作 op(动作类型清单参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——单步推进由画面 op 内置动作完成(`progress_once`:点「货币战争-道具详情弹窗.按钮-关闭」× 关闭) | 画面 op 内置动作(内置动作 = 画面 op 内部代码直接执行的固定动作,不经动作注册表派发;`progress_once`:area 读 center → `mouse_move`+`click`) | 无 report 接口(推进型规范形态,op-layer.md §3) | **是(推进即终结)**:点击后 `round_wait` 重入;落地复查 OCR∧排他不命中 = 已离开 → `round_success` 结束本次访问(见 §5);推进未落地 = `round_fail` 结束本次访问 |

`progress_once` = 读 `货币战争-道具详情弹窗.按钮-关闭` center(`kernel/cw_obs_core.py::area_center`)→ `mouse_move`+`click`(防吞点击)。坐标缺失 = False → 决策动作 node `round_fail`。

## 5. 终结与交回

推进已发 → `round_wait` 重入;落地复查 = OCR∧排他复判,不命中 = 已离开 → `success` 结束本次访问(无防御上限)。落点:祈愿帧让路祈愿试炼分支,其余 = 获得道具语境的底层屏(备战/补给等)重判。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件;道具入包由下一帧观察侧重新核实。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理(祈愿屏形态被排他条款排除,不接管)。

## 8. 守卫与防线

`node_max_retry_times=2` 在用值仅框架异常路径消费;无停机钩子/失配告警面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与测试面

- journal op 名 = 「道具详情弹窗」;frame_tag = `overlay_item_detail`(dispatch 包装,on_result 日志闭包)。测试:`sr-od-test/test/sr_od/application/currency_war/test_screen_progression_inline.py`(推进型骨架内联形态测试,item_detail_popup 已登记);建档 = `currency_war_item_detail.yml`。

## 开放设计注

- 档案 id_mark 缺位(OCR 回退的根因);排他双写收敛为单一源的改法待后续实施——两处同参目前靠纪律维持,漂移无锁。
