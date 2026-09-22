# 位面详情 overlay(plane_detail · 货币战争-位面详情)

> 代码 = `operations/cw_screen/cw_screen_plane_detail.py::CwScreenPlaneDetail`(两 node 直继承 `SrOperation`)。职责:一切来源(情报采集 op 失败退出残留 / 开局自动弹出等)的位面详情 overlay → 点 X 关闭交回。

## 1. 分发判定

- 阶段一身份分发(号制已退役):标题锚「货币战争-位面详情.标识-位面详情标题」;分发 = 阶段一身份行(单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。关不掉 → 包装 `on_fail_retry` 映射 round_retry(消费同一 retry 池)。
- 本屏同档的专用识别 op = `CwScreenPlaneIntel`([plane_intel.md](plane_intel.md);本屏 6 node 管线,打开/关闭转场归编排单一源 `CwEntryPlaneIntel`,详见该篇):识别运行中不经本分支;本分支只兜无采集语境的残留。

## 2. 画面形态声明

**空决策形态**(推进型弹窗)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口锚门(「货币战争-位面详情.标识-位面详情标题」,与分发判定同源同参;miss = round_fail 交回外循环重判)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部重入裁决(推进已发 → 锚不在 = 已离开本画面 → success 交回)→ 点 X 单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 现役值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

观察 node = 标题 id_mark(「标识-位面详情标题」,与分发判定同源同参)→ obs = `CwScreenPlaneDetailObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/plane_detail.py`;无 report 接口);零写端。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——单步推进留守 op 内(点 X 关闭:「货币战争-位面详情.按钮-关闭位面详情」) | 画面 op 留守臂(`act.progress_once`,success_wait=1.5) | 无 report 接口(推进型规范形态,[op-layer.md](op-layer.md) §3) | 是(推进后重入锚不在 = 已离开本画面 → round_success 交回;点 X 未落地 = round_fail 交回重判) |

单动作 = 点「货币战争-位面详情.按钮-关闭位面详情」(`success_wait=1.5`:点 X 后等过渡动画再交回裁决)。

## 5. 终结与交回

推进已发 → `round_wait`(机械交回);重入锚不在 = 已离开本画面 → success 交回外循环;点 X 未落地(按钮 miss)= round_fail 交回重判;首发锚 miss = 误分发 fail 交回重判(循环无防御上限)。

## 6. 状态上报面

零写端。

## 7. 子态与 overlay

本屏本身即 overlay 形态,无子态。

## 8. 守卫与防线

`node_max_retry_times=2` 现役值仅框架异常路径消费;无停机钩子——关闭不了由外循环重派/兜底链裁决。

## 9. 遥测与锁面

journal op 名 = 「位面详情」;测试锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_screen_progression_inline.py`(推进型骨架内联形态锁,plane_detail 在册);画面档 = `assets/game_data/screen_info/currency_war_plane_detail.yml`。
