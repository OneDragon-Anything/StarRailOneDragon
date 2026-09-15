# 商店刷新概率表弹窗(refresh_odds_popup · 货币战争-商店刷新概率表)

> 代码 = `operations/cw_screen/cw_screen_refresh_odds_popup.py::CwScreenRefreshOddsPopup`。职责:点球误触开的刷新概率表弹窗(0e2,遮挡底层屏关键按钮)的一次访问——点 × 关闭交回。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 0e2:锚 = `货币战争-商店刷新概率表.标识-刷新概率表`(id_mark;分发 = 阶段一身份行,[../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。不关闭会遮挡底层屏关键按钮(如出战),推进是流程义务。建档 = `currency_war_shop_refresh_odds.yml`。

## 2. 画面形态声明

**空决策形态**(纯推进)。推进型变体(`_progression_base.py::CwProgressionScreenOp` 子类):入口观察 → 单次推进 → 重入观察裁决交回;节点预算 = 2(合同 = [op-layer.md](op-layer.md) §1.5)。

## 3. 观察面

轻观察:入口/重入观察 = `entry_ok` 基类 area 锚原语。零 GameState 写端——概率条数值直读进 `refresh_probs` 属**商店域观察面**([shop.md](shop.md) §3),非本 op 职责。

## 4. 动作面

`progress_once` = 读 `货币战争-商店刷新概率表.按钮-关闭概率表` center(`kernel/cw_obs_core.py::area_center`;× 已 area 化,坐标单一真相源)→ `mouse_move`+`click`(mouse_move 必带:恢复原语同坐标点击曾落空,bug#1 缓解保留)。坐标缺失 = False → 基类 `round_fail`(建档缺失时分发锚预检先行报缺,此处为兜底防线)。

## 5. 终结与交回

推进已发 → `round_retry` 重入;重入 = 锚 miss = 已离开 → `success` 交回(关闭确认由重入裁决承接);预算耗尽 FAIL 交回。落点:店开 → 0n 商店访问;备战 → 备战环。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理,底层屏交回重判。

## 8. 守卫与防线

节点预算 = 2(基类合同);无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「商店刷新概率表」;frame_tag = `overlay_refresh_odds`(dispatch 包装,on_result 日志闭包)。
- 测试锁:无点名行为锁(骨架锁随基类;锁面根 = `sr-od-test/test/sr_od/application/currency_war/`);建档 = `currency_war_shop_refresh_odds.yml`,概率条读取机制见 [shop.md](shop.md) §3。
