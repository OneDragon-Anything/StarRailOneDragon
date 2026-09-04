# 0285 sim 判读口径两小修 + A/B 分辨率底(批㉑ F1/F3/F5 + 批㉒ F4 合卷)

- 状态: accepted
- 日期: 2026-08-24
- 来源: sim 压测批㉑(F1 carry 门 checker 口径差/F3 endgold 漂移
  归因/F5 检查语义改变)+ 批㉒ F4(A/B 分辨率底)。

## 背景

批㉑ 裁决三件:

1. **checker 口径差(非死锁)**:carry_gate_bench_deadlock 的金足
   判据是 `wave_gold ≥ cost`,不含调用方地板——seed30/39 的恒 2
   违规全部是「金足但破息档地板」的合法 miss(gold=12/10,
   floor=10,r5 boss_breaker 档 → gold−cost=9/7<floor 早退),
   与 checker docstring 残留声明逐字吻合;该检查的归 0 预期在
   旧口径下**结构性不可达**;
2. **endgold 漂移源 = r419 超容买守卫(ADR-0283),非策略变化**:
   守卫拦截 97 次终局窗买入 → 金滞留 → 末金 51.9→58.1(+6.14,
   r416 仅 +0.08 在噪声带内);sim_endgold_calib 的分子从此混入
   「守卫拦截的合法滞留」,原义(买通道死锁/策略滞留)判读力被
   稀释——若再涨需先扣守卫口径再判读,否则把 sim 真实化误读为
   策略劣化;
3. **A/B 分辨率底(批㉒ F4)**:单流 RNG 配对只削 32% 方差(耦合
   比 0.675),n=300 底 ±1.93hp——|Δavg|<底的差值在噪声带内
   不得叙述为方向性结论(批㉑ 判 r416 +0.08 为噪声与此一致)。

## 决策

1. **件2(checker floor 对齐)**:carry_gate 金足判据改
   `wave_gold − cost ≥ _carry_floor_est(轮次, wave_gold)`——
   检查模块不 import 策略(依赖方向纪律),地板三档
   (50/30/10)与 line_strategy 同步维护(值漂移由 floor 边界
   双向锁暴露);保守取梯级最大(r≥5 恒 boss_breaker 10;
   r<5 economy/war 并存取最大)——宁可漏报不误报,对齐后残留
   违规即真死锁/门漏边。锁:floor 边界两态(r5 cost2:gold=12
   恰达 floor 报 / gold=11 破地板不报)+ 梯级锁;
2. **件3(endgold 双口径)**:账本新增
   `sim.bench_full_skipped_gold`(守卫拦截买折算金,`cw_sim`
   BuyCard 守卫分支累计);`check_sim_endgold_calib` 并行输出
   总口径 ratio 与**净滞留口径 net_ratio =(末金均值 −
   guard_skipped_gold 均值)/实机 24.3**——判读侧可区分「策略
   滞留」vs「守卫拦截」;违规按净口径(总口径披露供跨批对照);
3. **件4(ab_resolution_floor)**:`check_ab_resolution_floor(
   hps_a, hps_b)` 纯函数——配对差 mean/sd + 95% 底
   `1.96·sd_pair/√n`(按批现算,勿写死 1.93)+ `noise_band`
   标注;`cw_sim.simulate_p1_ab(n)` A/B 报告入口内嵌该披露
   (同 seed 配对双臂 + headline)。

## 回归验证

- 件2:新语义 n=300 批 carry_gate violations **2→0**(seed30/39
  口径差消除);合成账本 floor 边界两态双向锁绿;
- 件3:本批(ADR-0284 后)n=300:总口径 53.68(2.21)/ 净口径
  52.95(2.18)——守卫残金 0.73/局,两口径判读可分;纯策略滞留
  (零拦截)形态违规语义不变(r413 原双向锁仍绿);
- 件4:合成配对 ±5 对称抖动 → noise_band=True;恒定差 10 →
  False;simulate_p1_ab 报告形状锁绿。

## Considered Options

- 件2 备选「账本披露 gate 实调 floor」:拒绝——需策略侧写账本
  (跨模块新通道,值随象限/连胜态变);保守梯级估计零新通道,
  残留即真死锁信号,方向性不损;
- 件3 备选「并行第二检查器」:拒绝——双检查器同语义分叉风险;
  单检查器双口径输出,消费侧按 net_ratio 判读;
- 件4 备选「判读纪律只进 verification.md 不落代码」:拒绝——
  纪律无锁会漂;函数化 + simulate_p1_ab 接线让每个 A/B 报告
  自带底,n<2 声明数据边界不判。

## 影响

- `cw_sim.py`:BuyCard 守卫分支 `bench_full_skipped_gold` 累计
  入账本;`simulate_p1_ab` 新入口;批报告
  `bench_full_skipped_gold`;
- `cw_sim_checks.py`:`_carry_floor_est` + carry_gate 金足判据
  对齐;`check_sim_endgold_calib` 双口径;
  `check_ab_resolution_floor`;
- 测试:`test_cw_r420_shop_slot_semantics.py`(floor 两态/梯级/
  双口径/分辨率底/simulate_p1_ab 形状);
- 判读纪律:任何 sim A/B 结论 |Δavg_hp| < 95% 底(n=300 ≈
  ±1.93hp)标「噪声带内」,不得叙述方向(批㉒ F4 杠杆原文)。
