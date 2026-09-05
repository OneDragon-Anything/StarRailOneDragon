# ADR-0523: 双账守卫两级分型(多集等价降级+槽位漂移重播种)

- 状态:已实施(代码+测试+本 ADR)
- 日期:2026-09-05
- 关联:ADR-0517 §守卫两属(ii)、ADR-0520(播种层双源退役)、第八局双账 HIT 诊断(20260905_noprogress_stop_diag/report.md「双账分离 HIT」节 G1-G5)、三件合并审计 P2/P3

## 背景

第八局 08:06:48 OpenShop 守卫炸「期望态 vs tracked 双账分离」:两签名多集完全相同(符玄×1+阮·梅×2),仅槽位 1↔2 互换。诊断定谳=对账 churn 后实况 bench 洞位重排,投影副本未跟随重播种(投影落@1、游戏填洞落@2)——逐槽有序签名分离但成员集等价,属槽位布局漂移非投影建模分叉;下游风险真实(M4 按槽卖会反复炸名-槽守卫甚至卖错对象),且任意「买牌+bench 有洞」形态可触发。

## 决策

1. `guard_expected_vs_tracked` 两级分型:①多集(Counter)等价 ⇒ WARNING「槽位布局漂移」+ `_reseed_bench_layout` 按 tracked 真值就地重播种投影 bench,不炸环;②真多集分歧 ⇒ 维持 AssertionError(两属归因不变,响亮暴露不软化)。
2. 重播种回写源 = tracked 账(三据:守卫炸点在买组中、bench_slot_map 来不及且不含洞位信息、tracked 纯内存零读屏合 ADR-0517 决策 1/8);降级当帧即重播种,后续 SellBench 名-槽提案对齐实况。
3. 可观测性:降级落 `bench_slot_layout_drift` 分键(L2)、重播种健康门拒绝落 `bench_slot_unhealthy` 分键(槽号唯一∧值域校验,违者拒重播种防坏槽号进不可逆卖出链)。
4. 根因排期声明:投影落洞规则跟随 churn 重排(对账事件接投影链)为独立批,现口径=症状治理+留证,非遗漏。churn 链槽号无重复/越界守卫的根因守卫归观察层仲裁批。

## 验证

ruff 净;test_cw4_shop_line.py 48 passed(含 HIT 载荷原样降级锁/真分歧仍炸锁/churn 后重播种名-槽一致行为锁);CW 快速集 2204 passed / 1 skipped(指纹守卫)。
