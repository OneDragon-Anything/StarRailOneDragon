# 商店刷新概率表弹窗(refresh_odds_popup · 货币战争-商店刷新概率表)

> 代码 = `operations/cw_screen/cw_screen_refresh_odds_popup.py::CwScreenRefreshOddsPopup`。职责:采晶矿误触开的刷新概率表弹窗(遮挡底层屏关键按钮)的一次访问——点 × 关闭交回。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 阶段一身份分发(号制已退役,不引 0x):锚 = `货币战争-商店刷新概率表.标识-刷新概率表`(id_mark;单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。不关闭会遮挡底层屏关键按钮(如出战),推进是流程义务。建档 = `currency_war_shop_refresh_odds.yml`。

## 2. 画面形态声明

**空决策形态**(纯推进)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口锚门(「货币战争-商店刷新概率表.标识-刷新概率表」,与分发判定同源同参;miss = round_fail 交回外循环重判)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部重入裁决(推进已发 → 锚不在 = 已离开本画面 → success 交回)→ 点 × 单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 现役值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

轻观察:观察 node = `entry_ok` area 锚原语 → obs = `CwScreenRefreshOddsPopupObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/refresh_odds_popup.py`;无 report 接口)。零 GameState 写端——概率条数值直读进 `refresh_probs` 属**商店域观察面**([shop.md](shop.md) §3),非本 op 职责。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——单步推进留守 op 内(`progress_once`:点「货币战争-商店刷新概率表.按钮-关闭概率表」× 关闭) | 画面 op 留守臂(`progress_once`:area 读 center → `mouse_move`+`click`) | 无 report 接口(推进型规范形态,op-layer.md §3) | **是(推进即终结)**:点击后 `round_wait` 重入;重入裁决锚 miss = 已离开 → `round_success` 交回(见 §5);推进未落地 = `round_fail` 交回 |

`progress_once` = 读 `货币战争-商店刷新概率表.按钮-关闭概率表` center(`kernel/cw_obs_core.py::area_center`;× 已 area 化,坐标单一真相源)→ `mouse_move`+`click`(mouse_move 必带:恢复原语同坐标点击曾落空,bug#1 缓解保留)。坐标缺失 = False → 决策动作 node `round_fail`(建档缺失时分发锚预检先行报缺,此处为兜底防线)。

## 5. 终结与交回

推进已发 → `round_wait` 重入;重入 = 锚 miss = 已离开 → `success` 交回(关闭确认由重入裁决承接;无防御上限)。落点:店开 → 0n 商店访问;备战 → 备战环。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理,底层屏交回重判。

## 8. 守卫与防线

`node_max_retry_times=2` 现役值仅框架异常路径消费;无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「商店刷新概率表」;frame_tag = `overlay_refresh_odds`(dispatch 包装,on_result 日志闭包)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_progression_inline.py`(推进型骨架内联形态锁,refresh_odds_popup 在册);建档 = `currency_war_shop_refresh_odds.yml`,概率条读取机制见 [shop.md](shop.md) §3。
