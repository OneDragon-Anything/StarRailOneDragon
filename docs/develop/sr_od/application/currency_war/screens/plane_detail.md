# 位面详情 overlay(plane_detail · 货币战争-位面详情)

> 代码 = `operations/cw_screen/cw_screen_plane_detail.py::CwScreenPlaneDetail`(推进型骨架基类 = `_progression_base.py::CwProgressionScreenOp`)。职责:一切来源(情报采集 op 失败退出残留 / 开局自动弹出等)的位面详情 overlay → 点 X 关闭交回。

## 1. 分发判定

- 外循环分支 0a4:标题锚「货币战争-位面详情.标识-位面详情标题」;分发 = 阶段一身份行(单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。关不掉 → 包装 `on_fail_retry` 映射 round_retry(消费同一 retry 池)。
- 本屏同档的**专用采集 op** = `CwScreenPlaneIntel`([plane_intel.md](plane_intel.md)):采集运行中自带详情识别与关闭,不经本分支;本分支只兜无采集语境的残留。

## 2. 画面形态声明

**空决策形态**(推进弹窗族)。骨架 = 入口观察 → 单次推进 → 重入观察裁决 → 交回;节点预算 = 1 次推进 + 1 次重入(`node_max_retry_times=2`),其余重试归外循环(基类合同 = [op-layer.md](op-layer.md) §1.5 空决策形态/验证废除)。

## 3. 观察面

入口/重入锚 = 同一标题 id_mark(与分发判定同源同参);零写端。

## 4. 动作面

单动作 = 点「货币战争-位面详情.按钮-关闭位面详情」(`success_wait=1.5`:点 X 后等过渡动画再交回裁决)。

## 5. 终结与交回

推进已发 → round_retry(机械交回);重入锚不在 = 已离开本画面 → success 交回外循环;首发锚 miss = 误分发 fail 交回重判;节点预算耗尽 → FAIL 交回。

## 6. 状态上报面

零写端。

## 7. 子态与 overlay

本屏本身即 overlay 形态,无子态。

## 8. 守卫与防线

节点预算 2(有界终止单);无停机钩子——关闭不了由外循环重派/兜底链裁决。

## 9. 遥测与锁面

journal op 名 = 「位面详情」;无专属测试锁在册(锁面目录 = `sr-od-test/test/sr_od/application/currency_war/`);画面档 = `assets/game_data/screen_info/currency_war_plane_detail.yml`。
