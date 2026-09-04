# 0276 sim 3合1 merge 接入 + session 结算补写(批⑩最大杠杆;批⑩ F3/F4/F5、批⑤ F4)

- 状态: accepted
- 日期: 2026-08-24
- 来源: sim 压测批⑩(F3/F4/F5 + 检查项 4 条)/ 批⑤ F4;worker 任务「sim 侧修复批五件」件1/件3/件5(批⑩部分)

## 背景

批⑩ 裁决:生产 `simulate(BuyCard)` 每次买入后调 `_merge_bench`
(全场域 bench+deployed,同名同星 ≥3 → star+1、删 2 张),sim 买入
不合并——同名副本在 bench 堆积占席 → `bench_is_full` 门死 → 买通道
死 → 滞留金 2.2× 虚高 → engines2/avg_hp/席位/卖出类结论全部含堵塞
失真分量(F3 副本滞留卖出误报、F4 复合死锁 1/300、F5 末轮 bench
10.69>9 物理上限)。这是 ADR-0271 登记的第一顺位缺口、批⑩最大杠杆。

批⑤ F4(同批修复):`_boss_breaker_actions` 的 r308 保连胜门读
`session.last_streak` / `session.node_type_current`——simulate_p1
两者都不写(连胜只存本地变量算收入、节点类型只进账本)→ 决策侧
连胜响应在 sim 恒盲(300 局「地板降 5」0 次触发)。

## 决策

1. **merge 接入 sim 执行层**:BuyCard 分支 append 后调
   `_merge_bench(st.bench, st.deployed)`(与生产 simulate 同一函数,
   单一源);合并次数按单位消减推算(每次合并净减 2 单位)入账本
   `sim.merges`(单位守恒/席位判读输入);
2. **卖出回金接生产 `sell_refund` 单一源**(star 感知:1星=cost、
   2星=3×cost−1…)——merge 落地后 bench 可有 star≥2,旧恒按 1星
   cost 退会低估合成件价值;
3. **session 结算补写**:决策前写 `session.node_type_current`
   (=本局采样节点,词表 battle/encounter/boss/…);结算后写
   `session.last_streak`(连胜计数)——生产语义对齐
   (prep_director / default_strategy.on_settlement);
4. **批⑩ F3 裁决落地**:`check_no_same_round_buy_sell` 豁免边扩到
   engine_seed 收集语境(同轮同名买入 ≥2 = 3合1 素材收集,其同名
   卖出=合成冗余让位,与 copy 豁免同族);单张买入即卖(振荡)仍
   0 容忍;裁决探针 `check_engine_seed_sell_exemption` 双向锁;
5. **批⑩ 检查项 4 条**:
   - `bench_full_deadlock_probe`(进 _BATCH_CHECKS):连续 ≥3 轮
     零买入+bench≥9+金>20+**deployed<cap**(上通道同堵)——判据表
     原文三维在末段普遍成立(n=60 预跑 41/60 误报:板满+攒金是合法
     终局),deployed<cap 才是 F4(seed174)的特异性维度;
   - `sim_endgold_calib`(批级披露):sim 末金/实机 24.3 比值,
     >1.5 报——**P1-only 已知缺口**:末段滞留金在 sim 无处可花
     (P2 入口继承价值不可判),比值 ~2.1× 恒报是披露而非回归;
   - `anchor_registry_n300`(登记制):基线锚一律 n=300 口径 +
     池指纹登记于 `ANCHOR_REGISTRY_N300`,n=60 只作快速哨兵;
   - engine_seed 豁免(见 4)。

## 回归验证(n=300 配对,seed 0-299,pool='snapshot' e19afdfa)

| 指标 | 旧(批⑩ n=300 锚) | 新(本批+ADR-0277) | 判读 |
|---|---|---|---|
| engines2_by_r6 | 0.083 | **0.277** | merge 恢复成型读数(3合1 素材不再占席堵买) |
| avg_final_hp | 26.03 | 28.81 | win 校准抬升(ADR-0277 贡献) |
| hp_ge_60 | 0.017 | 0.04 | boss 恒败钉死解除 |
| battle_losses_le_2 | 0.027 | 0.033 | — |
| recipe5_by_r6 | (n=60: 0.450) | 0.62 | 供给通道恢复 |
| avg_refreshes | 1.61 | 1.11 | 买通道活,早刷需求降 |
| 末轮 bench 均值 | 10.69 | 9.64 | 副本堆积消化;仍 ≥9=98%(候选件合法持位,非死锁:deadlock probe 0/300) |
| 卖出/局 | 0.89 | 1.45 | 卖出通道恢复(star 感知回金) |
| 合并/局 | — | 4.32 | merge 生效直接度量 |
| 滞留金比(sim/实机) | 2.2× | 2.17× | **未收敛**(P1-only 已知缺口,见上) |

方向解读:数字大变是修正的意义——旧栈 engines2 0.083 的一半以上
是「副本占席→买不进→成型不可达」的堵塞失真;merge 一接,engines2/
recipe5/卖出/滞留金分布的 sim 读数恢复判读力(批⑩ F5 的「卖出类
结论降级不可判」解除)。滞留金比值未收敛本身也是有信息量的读数:
残差已定位到 P1 末段花金通道(非席位问题)。

## Considered Options

- **A. 只修 bench 计数不接 merge(ADR-0271 Option C 的延续)**:
  拒绝——副本堆积的根因还在,席位门读真数据也恒堵;
- **B. merge 接入 + star 感知卖出 + session 补写(选定)**:与生产
  `simulate`/`mutate_bench_deployed` 逐条同源,执行层错位从此
  sim 可发现;
- **C. 顺带重定锚 n=60**:拒绝——批⑩ F1 已证 n=60 噪声带 ±0.071
  不可判,锚一律 n=300(登记制检查落地)。

## 影响

- `cw_sim.py`:BuyCard 分支 merge+计数;SellBench 分支 sell_refund;
  结算 boss 胜分支前的 session 两写;账本 sim.merges;批级检查接线;
- `cw_sim_checks.py`:engine_seed 豁免边+裁决探针;deadlock probe
  (进批量集);endgold calib / anchor registry(批级);
- `docs/develop/currency_war/sim-wiring.md`:bench 行移「已接」
  (merge 补齐),node_type/streak 行已接(session 口径);
- 测试:`test_cw_r413_sim_merge_win_wiring.py`(17 锁)+
  `test_cw_r410_bench_pop_semantics.py` 守恒式更新(−2×merges);
- 基线锚:n=300 新锚登记于 `ANCHOR_REGISTRY_N300`(见上表)。
