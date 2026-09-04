# R196_FIX_REPORT——CW R196 对抗审查修复批(七症+两观察处置)

> 任务书=编排者 R196 修复批裁决(规格权威=IMPL_DESIGN §2/§2.7/§4.2.1+契约 v2
> §3.2/§3.3+telemetry 键登记规格);攻击报告=IMPL_ADV_R196.md(单一事实源)。
> 登记节=design_telemetry.md 文末「R196 修复批」节(键行+裁量+观察注记)。
> 文件面(源码,全部本批改动):cw4/{entry,proof,mandate,bridge}.py、
> criteria/sell.py、decision_v2/series_adapter.py、strategies/mandate_v1_strategy.py;
> shop.py 零触碰(见裁量③);文档=design_telemetry.md(键节 8 新键行+索引+R196 节);
> 测试=sr-od-test 两件(test_cw4_mandate_v1.py 更新 17 类锁+新增 20 项行为测试)。
> 冻结族/冻结残余 11 项/契约 v1 v2 正文/步4b 七项工程裁量:零触碰(见冻结对账)。

## 逐症修注(三元组:改点锚 → 检验式 → 规格对齐)

### 症1 换线结构性空转(最重)

- **改点**:
  1. `proof.best_alt_comp(state, session, registry)` 新函数——alt 候选供给;
  2. `proof.should_switch`:`alt_comp is None` 路径改为自派生(best_alt_comp),
     派生空才 `('no_alt')`;no_target / e_cur_undefined / no_alt / relock_window
     四路 return 全部 `_count` 分键计数;
  3. `entry.emit`:k_switched 实值化——`session.cw4_prev_line_name` 帧间线名快照,
     本帧生效 K 名不同 ⇒ k_switched=True + old_line_members 自 `get_comp(prev_name)`
     取回喂 `_criteria_pass`(line_switch_sell 只在 K 已更新的备战期评,§2.7)。
- **检验式**:①测试 `test_should_switch_event_with_alt_supply`(monkeypatch
  e_rounds 使 alt 显著更优 ⇒ event 真 + alt_comp 非空);②`test_no_alt_and_no_target_split_keys`
  /`test_e_cur_undefined_counted`(分键计数);③`test_entry_k_switched_real_value`
  (entry 两帧,帧2 K 翻转 ⇒ line_switch_sell 收到 k_switched=True+旧线成员);
  ④`grep alt_comp src/.../cw4` 命中含 entry/proof 供给侧。
- **规格对齐**:IMPL_DESIGN §2.7 接线义务「proof pass 内每备战期调用一次,产出换线
  事件;不换线也记遥测」;D-P4 回锁窗(L224-227)由死码转可达(行为测试锁,
  见下);归因分键纪律(R24-2 族)。
- **裁量申报**:候选集来源规格未给——COMP_LIBRARY(§1 proof 行)−当前线−
  drought 排除;证据门 P38 序数形态=「e_rounds 有限 ∧ shop_supply>0(基线
  best_alt_line 同口径)」,p_complete 数值门候标定批;None 期整体 fail-closed
  ⇒ 本裁量零行为面。见 telemetry R196 节裁量①。

### 症2 EV 冲突丢弃

- **改点**:`entry._criteria_pass`(增 `skeleton_out` 参数)与 emit 臂①支撑通道:
  骨架已发射 SellBench 槽位集 + EV pass 内已采纳槽位 = 先到先得冲突域,冲突
  提案丢弃 + `ev_conflict_dropped` 计数(禁重发)。
- **检验式**:`test_same_slot_dropped_not_resent`(骨架卖槽2 + EV 两路(line_switch/
  funding)均提案槽2 ⇒ out 空 + 计数2)/`test_distinct_slot_kept`(异槽保留零计数)。
- **规格对齐**:entry L275-276 docstring 宣称(先到先得丢弃+遥测)落地;键行
  补登(telemetry 键节;键系代码已宣称键的对账,非新装置)。

### 症3 影子遥测错位

- **改点**:`entry._lambda_quantile_armed(state, hp, p)`——相对分位求值体
  (PL 键 → 可消费格 λ_U 在 `lambda_u_order` 降序全序中的分位序 ≤ p);
  `_upgrader_evaluate` 改收 state,三口径分列:p=None ⇒ 不求值(两键构造性
  恒 0);p 注入形态 ⇒ 影子键 `advisor_lambda_shadow_armed`;p 标定形态 ⇒ 真键
  `advisor_lambda_armed`(信号位 lambda_armed,行为面接线候标定批);血线
  thr=None 期 ⇒ 结构锚 hp15(`lambda_death.HP_BAND_NEAR_DEATH` 单一源)影子
  照测 `advisor_bloodline_shadow_armed`(行为无关);thr 非空行为面不翻案。
- **检验式**:`test_lambda_none_period_no_keys` / `test_lambda_injected_form_counts_shadow_only`
  (表首危格触发+健康格不触发)/ `test_lambda_calibrated_counts_true_key` /
  `test_bloodline_none_period_shadow`(hp10<15 影子真、neardeath/f7 假;hp30 不触发)。
- **规格对齐**:design_telemetry L67 升档器激活率门观察级段(R29-1/R36-2/R41-5①
  三口径分列);键集零扩张(冻结族纪律:对齐既有键,零新装置)。
- **裁量申报**:三口径的「注入形态=影子/标定形态=真键」映射为 R41-5 三口径
  (影子/注入/真键)的实现落点;λ 分位序取同值首址(饱和并列组按最危端,保守)。

### 症4 bench_full_buy_abandon 双失联

- **改点**:mandate M2 bench 满放弃路径在环耗竭分支补 `_count('bench_full_
  buy_abandon')`(事件帧计数,与 m2_retry_exhausted 的环终止计数分键)。
- **检验式**:`test_bench_full_buy_abandon_counted`(bench 满∧全 3★ 无燃料 ⇒
  两键各 ≥1)。
- **规格对齐**:mandate docstring 宣称 + R102-N1 三通道分键判读的实现侧补臂;
  键行补登(语义=M2 义务因 bench 满未成交的事件帧)。

### 症5 截断器对齐契约 v2 §3.2

- **改点**(entry):
  1. ClickSpheres → `_CONDITIONAL`;`truncate_frame_stable` 末批判:同序列其后
     还有 ClickSpheres ⇒ 非末批可续;序列内最后一个 ⇒ 其后截断(判型内语义,
     不计失败键);
  2. conditional 五类复检:`SellBench`/`DeployMove` 槽位引用对生成期观察投影集
     (`bench_slots`,bridge 自 obs.bench_chars 现读供给)+ 前序同序列卖出/拖出
     累积投影;推不出 ⇒ 截断 + `emitter_conditional_truncated` 计数;组合类
     (SellDeployed/RunDeploy/RunEquip)按计划静态推出可续(ADR-0316);语境
     缺省 None ⇒ 条件成立续发(生产路径 bridge 总供给,显式注释);
  3. BailToOuter → `_TERMINAL`(退役·终点,契约 §3.2 行;发射行为等价)。
- **检验式**:`test_click_spheres_normal_continue_and_last_batch_truncates` /
  `test_sellbench_name_slot_recheck`(空槽截断+计数)/ `test_sellbench_in_sequence_
  projection`(同序列二次引用已卖槽截断)/ `test_deploymove_from_slot_recheck` /
  `test_composite_conditional_continue` / `test_bail_to_outer_terminal` /
  `test_no_context_conditional_continues`;17 类覆盖测试期望值同步更新
  (ClickSpheres='conditional'、BailToOuter='terminal'——锁语义随契约行重推,
  锁红≠改动错)。
- **规格对齐**:契约 v2 §3.2 逐类表 L93(ClickSpheres 条件)/L84/L101/L102
  (复检+静态推出,推不出即截断)/L92(BailToOuter 退役·终点)。实现期增补
  条目未回契约改版(判型值系对既有条款的对齐,非新判)。

### 症6 常数单源

- **改点**:
  1. mandate:本地 `BENCH_CAPACITY: int = 9` 删除,改 `from kernel.cw_state
     import BENCH_CAPACITY`(单一源);
  2. `cheapest_member_cost`:字面量 3 → K 成员在 CHARACTERS 的最低 cost
     (全未注册名 ⇒ 保守估 3,bench_char_cost 注册表先例);
  3. criteria/sell L94:字面量 3 → `sell_refund(1, bench_char_cost(b))` 派生;
  4. `mandate._s_reserve(frame, session)`:`b_target(0,0,0)` 退化形 → `s_line`
     组装实装(B=0[xp 未观测,分量级 None 期申报]+saturation(cap_resolved)
     +0[窗口预留槽未标定]+2×2[刷费基价] ⇒ 默认局 54;辖 dominance 路径
     check_s_reserve)。
- **检验式**:`test_bench_capacity_single_source`(值等+源文件无重定义)/
  `test_cheapest_member_cost_registry_derived` / `test_s_reserve_s_line_assembly`
  (=saturation+4)/ `test_funding_refund_registry_derived`(注册名按 sell_refund
  派生;未注册探针名保守估 3 与旧值同构)。
- **规格对齐**:§3.2 硬约束③「整买目标预留金不被非 S 组成动作吃掉(辖
  dominance_buy+M6+EV 买入面)」——B 分量 xp 未观测/MandateFrame 未载 ⇒ 非
  静默 0(docstring 分量级申报);非「规格确为 0 预留」。
- **裁量申报(边界)**:shop.py L223 同族 `s_reserve=b_target(0,0,0)` 本批
  **未动**——步4b 商店线 criteria 接线属候标定裁量面(任务书「步4b 七项
  工程裁量不翻案」);同族收口归商店线标定批。见 telemetry R196 节裁量③。

### 症7 类型注解

- **改点**:entry(`emit` registry/返回、`_criteria_pass` 全参+返回)、bridge
  (`decide_prep_action` obs/返回)、mandate(`_state_view` 返回)、series_adapter
  (`decide_prep_screen`/`decide_prep_action` config/obs/返回,TYPE_CHECKING 导入)、
  strategies 桥(`_assemble_turn` 全注解)。OBS-2:series_adapter L4 docstring
  ``D``ecisionV2Strategy`` 笔误修正。
- **检验式**:ruff 改动文件全过;辖域=R196 清单六文件,非全仓断言。

## 观察处置

- **OBS-1(OpenShop 单帧闭环张力)**:评估后属实——契约 v2 §3.2 OpenShop=截断点
  与 IMPL_DESIGN §3.1「M5→…→M7 单帧闭环」的表述错位成立(含开店意图帧其后
  发射位构造性丢弃)。按任务书处置:**禁改契约**;已在 design_telemetry R196 节
  登记 OBS-1 观察注记(候选收口=IMPL_DESIGN 打「开店帧分帧重评」辖域标或契约
  改版,归编排者裁决;未裁前照现状保守截断运行)。**呈报编排者**。
- **OBS-2**:docstring 笔误已修(症7 条内)。

## 冻结对账

- 冻结六装置族(D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面
  验证装置):零触碰、零新增装置——症3=对齐既有登记键(键集零扩张);本批
  新键 8 个全部系「代码/文档已宣称的键的对账补登或发射面可观测性键」
  (ev_conflict_dropped/bench_full_buy_abandon=宣称键;switchline 四键组=
  §2.7「不换线也记遥测」归因分键;emitter_conditional_truncated=§3.2 复检
  fail 方向的可观测披露,与 §3.3「禁不可观测静默截断」同精神)。
- 冻结残余 11 项:零触碰。契约 v1/v2 正文:零改动。步4b 七项工程裁量:零翻案
  (shop.py s_reserve 边界申报,非翻案——本批未动其行为)。

## 复验记录(全实测)

1. **步3+4/4b 既有测试全绿**:test_cw4_mandate_v1 61 + test_cw4_shop_line 34
   (含 17 类判型锁按契约行重推后的期望值更新)。
2. **双门复跑**:`baseline_self_pairing_gate n=20` 零污染(mismatches==[])+
   `arm_diff_probe n=6` 相异(baseline/new_core rows>0)——3 项 slow 测试全绿
   (24.6s)。
3. **新增行为测试 20 项全绿**(TestR196Wiring/TestR196EvConflictDrop/
   TestR196TruncationBehavior/TestR196ShadowKeys/TestR196Constants)。
4. **CW L1 全量**:2366 passed, 2 skipped, 822 deselected, 1 xpassed(2:15)。
5. **ruff**:改动文件(src 8 件+测试 2 件)全过。

## 行为变更申报(判读面注意)

- S 预留实装使 dominance 路径 check_s_reserve 门槛默认局 0→54(dominance
  资格仍=金>g*;54 以下 dominance 发射被③拦截,落 dominance_bench_wait 计数)
  ——硬约束③语义恢复,非缺陷;M6/EV 商店面未动(裁量③)。
- cheapest_member_cost 由恒 3 → K 成员注册表最低 cost(多数线仍=3;含 1 费
  成员的线更低)——金需求侧更精确。
- ClickSpheres 非末批可续:仅影响含多批 ClickSpheres 的序列(生产为单动作
  帧,零漂移);BailToOuter 判型标签变更,发射行为等价。
