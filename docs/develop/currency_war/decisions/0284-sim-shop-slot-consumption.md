# 0284 sim 商店槽消费语义(批㉒最大杠杆;批㉒ F1/F3/F5)

- 状态: accepted
- 日期: 2026-08-24
- 来源: sim 压测批㉒(F1 槽消费缺失/F2 策略-sim 共享盲区/F3 指标
  污染面/F5 池静默地板);压测批㉑报告两小修归 ADR-0285。

## 背景

批㉒ 裁决:sim BuyCard 执行后不从 `st.shop` 移除已买槽(槽仅在
offer/refresh 重赋值),同槽可无限再买——生产语义槽买后消失(全仓
docstring 无一处声明此简化,非已声明取舍)。账本实测(批㉑ HEAD
n=300):**65.13% 买轮含槽再买**(889/1365),超量槽买 3553 次/300
局(≈11.8/局),单槽最高 6 连买;line_strategy r352c 的「同窗同名
买 3」计划被幻影槽无限兜底(merge 轮 82% 零刷新——大量合并靠
再买同一槽而非真实供给)→ **成型类指标(trio3_by_r8/engines2_by_
r6/recipe5_by_r6/formation 耦合的 formed_n)系统性偏乐观**,
refresh 通道价值被掩蔽,sim 永远暴露不了「生产同名二连买点空槽」
类执行 bug(两侧共享同一 artifact 互相掩护)。

## 决策

1. **BuyCard 执行消费槽**:槽匹配(引用同一 → 同名兜底)→
   `st.shop.remove`;无槽且本轮曾上架该名 = 已消费槽再买 →
   **跳过执行**(金/牌池不消费)+ 计数披露;本轮从未上架 =
   店外构造(测试桩)→ legacy 执行 + 披露计数(ADR-0283 桩
   兼容;真策略提案恒来自 st.shop);
2. **RefreshShop 重抽全 5 槽**:查证现行实现已是全 5 槽重抽
   (`draw_shop(level)` 整表重赋值),无改动;锁测试固化「每波
   恒 5 槽」;
3. **池 take 地板如实记**(批㉒ F5):`_Pool.take` 的 `max(0,…)`
   静默地板加 `floor_hits` 计数——27 份/卡下不可达(潜伏),槽
   消费落地后真批次应恒 0,`SimResult.pool_floor_hits` + 批报告
   `pool_floor_hits` 披露(未来降池容量/共享池时 >0 即暴露);
4. **检查项 2 条**(入 `_BATCH_CHECKS`):
   - `shop_slot_consumption`:波内同名买入数 ≤ 该波同名供给槽位
     数(RefreshShop 动作切波;执行层忘消费槽/账本写坏即报);
   - `phantom_rebuy_disclosure`:账本 `sim.phantom_rebuys` 归 0
     锁(批㉒ 设计为披露口径,槽消费落地后升格归 0——修复前
     65.13% 买轮含槽再买 → 修复后 0)。

## 回归验证(n=300 配对,seed 0-299,pool='snapshot' d891233d)

| 指标 | 旧(改前同参重跑) | 新(本批) | 判读 |
|---|---|---|---|
| engines2_by_r6 | 0.277 | **0.237** | **批㉒ F3 波及:成型类指标回落到真实供给口径**(同窗同名 3 份 = 多槽/多窗/刷新的真成本,不再同槽重复点击) |
| recipe5_by_r6 | 0.623 | **0.533** | 同上(幻影供给水分挤出 −0.09) |
| trio3_by_r8 | 0.023 | 0.027 | 真实口径下持平(本就低) |
| avg_refreshes | 1.107 | **3.943** | 真供给逼出刷新需求(旧 1/3 靠幻影槽免刷新;批㉒ F3「refresh 通道价值被掩蔽」解除) |
| avg_final_hp | 28.99 | 29.25 | 噪声带内(±1.93@n300,ADR-0285) |
| hp_ge_60 | 0.067 | 0.047 | 成型回落 + 刷新分流金流的合计效应 |
| battle_losses_le_2 | 0.080 | 0.073 | 同上 |
| formation 耦合 diff | 12.53 | 7.31 | formed_n 92→98,耦合差回落(旧含幻影成型水分) |
| 末金均值(总口径) | 58.08(ratio 2.39) | 53.68(2.21) | 滞留金部分回流真供给购买;净口径 52.95(2.18,ADR-0285) |
| bench_full_skipped_buys | 97 | 72 | 守卫拦截减少 |
| 超容折算金 bench_full_skipped_gold | — | 218(0.73/局) | ADR-0285 净滞留口径输入 |
| phantom_rebuys / pool_floor_hits | —(口径未建) | **0 / 0** | 幻影再买归 0(件1 验收)+ 池守恒绿 |
| carry_gate_bench_deadlock | 2(seed30/39) | **0** | ADR-0285 件2 floor 对齐后真归 0(旧 2 = 口径差非死锁) |

全部检查(含 2 条新检查)0 违规;基线锚按新口径重记于
`ANCHOR_REGISTRY_N300`(engines2 0.237 / recipe5 0.533 /
avg_refreshes 3.943 等,演进链注释指本 ADR)。

## Considered Options

- **A. 按 name 供给计数递减(不删槽)**:拒绝——策略 re-decide
  读 st.shop 逐槽,不删槽 = 幻影槽仍在牌面里,只是计数拦截,
  「生产同名二连买点空槽」类 bug 依旧不可见;
- **B. 无槽提案一律跳过(严格生产语义)**:拒绝——ADR-0283 的
  守卫测试桩(店外构造 x=100)会不可达,超容买守卫回归网失锚;
  折中 = 店外构造 legacy 执行 + 披露计数,真批次由
  phantom_rebuy_disclosure 归 0 锁辖;
- **C. 只加检查不改执行层**:拒绝——检查只能报警不能恢复判读力,
  成型类指标仍旧失真(批㉒ 最大杠杆判词)。

## 影响

- `cw_sim.py`:`_Pool.floor_hits`/take 如实记;SimResult
  `phantom_rebuys`/`pool_floor_hits`;BuyCard 分支槽匹配/消费/
  幻影跳过;账本 `sim.phantom_rebuys`、`sim.bench_full_skipped_
  gold`;批报告 4 个新披露键;
- `cw_sim_checks.py`:`check_shop_slot_consumption`/
  `check_phantom_rebuy_disclosure` 入 `_BATCH_CHECKS`;
  `ANCHOR_REGISTRY_N300` 新锚;
- 测试:`test_cw_r420_shop_slot_semantics.py`(12 锁)+
  `test_cw_r413_sim_merge_win_wiring.py` merge 锁改种子段扫描
  (特定 seed 不再稳定触发 3合1——真实供给约束,意图内);
- **判读消费注意**:引用本批之前的 trio3/engines2/formed_n/
  refresh 通道数值的结论一律带「含幻影槽超买」口径标注(批㉒
  杠杆排序原文);r5plus_refresh_closure 语义不变(刷新仍集中
  早期,r5+ 仍 0)。
