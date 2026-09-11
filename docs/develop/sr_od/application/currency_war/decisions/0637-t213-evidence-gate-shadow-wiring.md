# ADR-0637: T-213 证据门生产接线(影子面)——missing 分解单一源+帧装配器+消费位接线

- **Status**: 已实施(影子面接线,零生产行为变化;对抗审/落地审候编排者另派,入库走 committer)
- **命题**: math_proofs **P76** §4.4 可计算夹界(帧项语义)/§5.5(接线批语义「接线时按夹界形态实现」)/§7 #1-#5(值因子挂账);P38 ②③层(槽试验与合格集命中概率,missing 分解正本)
- **关联**: ADR-0628(夹界落码批,Considered「A/B 移交接线批同批」「本批一并接线=否决(改线选择权威面须方案审级)」两裁决的本批兑现)、`strategy-docs/12_line_and_intention.md` §1(证据门设计层)、R197 症2 影子面裁决(12 号稿 §3)、任务卡 = 进度账本 T-213 行(T-124-r1 §四.1 四要件正本)

## 1. 背景与归层

evidence_gate 自 ADR-0628 落码后全仓零调用点(P76 修正 5):门本体已按夹界形态重写,但「接线批(帧装配+消费位)」未排期前,门对所有 missing≠∅ 帧恒「不可评」= 诚实沉默。T-124 落地审 §四.1 立项接线批四要件:①missing 线距离分解生产者(单一源现不存在,Q2b 已指)②帧装配器(LockSandwichFrame 六项)③A/B 同批(裁决义务)④消费位接线方案审。归层 = 决策层·线选择判据(证明层);本批 = 生产路径接线,**不改任何生产行为**(影子面)。

## 2. 落码形态(四义)

1. **消费位接线 = entry 证明 pass 影子评估**(`entry.py::emit` ② 证明 pass、should_switch 之后一行调用 `proof.evaluate_evidence_gate(state, session)`):输出只进 `cw4_counters` 分键,返回值不被消费做任何行为——R197 症2 影子面同族(在册先例 = should_switch「已接线 + fail-closed 封印休眠」,12 号稿 §3 as-built 词汇:接线 = 生产路径实际调用,封印 = 零行为)。选点理由:证据门语义对象 = 当前生效线 K 的锁线时机;target_comp 权威 = decision_v2 意向状态机(R197 症2),**权威面切换(S1→S3 证据门接管)= 标定落地且门数值可评后的另案裁决批**,本批不越 ADR-0628 Considered 否决线。分键 = `evidence_gate_evaluated` / `evidence_gate_sandwich_suff|band|below_nec|pathological` / `evidence_gate_unavailable`(聚合)+ `evidence_gate_unavailable_<成因>`(成因分桶,聚合与成因不同键防混计,R24-2 纪律);键推导 = reason '(' 前缀(带数值串禁作键);键登记 = proof.py 模块 docstring(现行惯例)。
2. **missing 分解单一源**(`proof.py::line_missing_decomposition` + 内部 `_missing_items`):件模型 = P38——form_tiers 逐档一项(段表登记批前现状口径),m_t = max(0, need−held−shelf) **逐档 clamp**(完成事件 = 各档各自满足,与 `line_distance` 全局 clamp 标量口径有意分歧、不统一,分解口径单一源 = 新抽 `cw_line_switch.tier_progress`,line_distance 恒等重构消费同源);已满足件剔除;货架件「买走即 held」(同 line_distance)并经 extra 通道计入同档池衰减。q_t = `odds.slot_q_tag`(新单一源,P38 ③层含池衰减,分费档明细视图 `slot_q_tag_by_cost` 供主档消费;分子分母同扣 j,slot_q R200 勘误约定同式)。q≤0 项照常入表(p_complete 返 0 → 必要侧拒,静态不可达线诚实出「锁劣」向)。
3. **帧装配器**(`proof.py::assemble_lock_frame`):试验数口径 = **槽试验**(P38 ②层)`SHOP_SLOTS×(R_全局 + 可负担付费刷数)`,R_全局 = `cw_plane_table.r_remaining`,付费刷数走 `saturation_line(cap_resolved_of_session(session))` 可负担窗(e_rounds 同链;静态预算近似,P38 ⑤层金位递推归标定批升级)。六帧项:e_p_next = p_complete(missing, trials−SHOP_SLOTS)(等待一帧只自然刷,S_side 不扣 = 乐观向 → 两侧判据保守);f_plus = (1−P)Σ(P_miss·C_rescue+1)(u=1 消参 §7 #5;p_shop≤0 件只保留 +1 手续费项);b_plus = Σ v_comp_marginal(P49,毛值上界向);c_hold = |H_S|×1(最小卖回协议手续费级上界,乙.1 段 2;1 金 = 甲.2 机制真值)+ C_sat(v_slot 事件门 × P_block 上界式 × v_opt(u=1) 主档被阻断动作估值,§7 #3 V_opt 侧先行的落码形态);**o_plus = None、d_death = None**(值因子挂 V_ms【拟】§7 #1 / Δλ 挂 λ 连续模型【拟】§7 #2,P_i^port 侧线组合评估面亦未落)。
4. **T-124 A/B 移交义务兑现(Q2c)**:确认性对拍(改前/改后同 seeds [9300,9330) × 30 局同池指纹,`PYTHONHASHSEED=0`)——本批行为面预期**逐位恒等**(影子接线+封印期),不一致 = 接线泄漏行为 = 缺陷逐帧定位,不构成效果判读(A/B 无裁决权,strategy-work §3);**sim 可观测性声明**:判据/策略层接线,sim 看得见遥测面(cw4_counters 新键;实测 sim 对 prep 线结构性零覆盖——配对批新键零显影实领,见交付报告可观测性声明)看不见行为差;结构性无帧申报:sandwich_suff/band/below_nec/pathological 在值因子标定前恒 0 计数,禁当「门判负」证据。判读凭据输入 = reviews/T-261-落地审.md(欠功判读范式 + 「不显著≠无效应」边界,效果 A/B 须带检验力/MDE)。

## 3. Considered Options

| 选项 | 裁决 |
|---|---|
| 权威面接线(证据门接管 S1→S3 锁线判定) | 否决(本批):改线选择权威面涉 R197 症2 裁决辖域,且封印期门恒「不可评」,若以「不可评=不锁」消费即向骨架层渗漏为否决(NMF §6/§5.3 禁);须标定落地+门数值可评后另案 |
| 影子面接线(本案) | 采纳:should_switch 同款在册形态;生产路径真实激励(装配/求值逐帧运转,缺陷显影)+ 判读分键数据(标定批对照基线)+ 权威切换批零风险前置 |
| o_plus/d_death 以近似界装配(如 V_slot 全量/λ 点值差) | 否决:值因子 P76 §7 #1/#2 明文挂【拟】,近似 = 自造语义(ADR-0628 Considered 同款否决理由);None 期诚实沉默 |
| missing 分解按 line_distance 全局 clamp 标量拆 q | 否决:完成事件 = 各档各自满足,跨档抵扣无 P38 模型依据(A2 两两不交);逐档 clamp 为正本,与标量口径分歧显式申报 |
| A/B 挪标定后跑 | 否决:裁决义务 Q2c 钉「与接线批同批」;确认性对拍此刻即可钉死「接线零泄漏」 |

## 4. 后果与边界

- **行为面**:零生产行为变化(影子面 + 封印期双自证;A/B 行为面逐位恒等确认在案)。新增遥测键族(§2.1)与 `slot_q_tag*`/`line_missing_decomposition`/`assemble_lock_frame`/`evaluate_evidence_gate` 四个公开函数。
- **敞口更新(取代 ADR-0628 §4 敞口申报的「接线批未排期」 clause)**:门数值可评前置 = ①Δ/ε₂ 注入(标定批)②o_plus/d_death 装配落地(V_ms 侧值因子 + Δλ 协议差模型标定批)。两者齐前门对一切缺口帧恒「不可评」。影子分键在 ① 后仍恒 unavailable(o_plus/d_death 缺),判读禁误读。
- **界方向账本(标定批消费)**:c_hold 上界形态 → nec 侧严格、suff 侧「锁不劣」保证吸收 ≤ 高估量/Δ;e_p_next 乐观 → 两侧保守;trials 静态预算 → P 乐观向。升权威面前须按 P76 §4.4 界语义复核。
- **三同步**:本 ADR + INDEX 行;12 号稿 §1 锚行更新(「未接线」→「已接线(影子面)」);proof.py/entry.py docstring 引本 ADR。
- **测试**:新锁 18(`test_cw_evidence_gate_wiring.py`:分解六件/slot_q_tag 两件/装配四件/影子评估五件/守卫移除一件)+ 守卫移除变异双红实证(摘 entry 调用行 → emit 守卫+源级影子申报锁红;摘成因桶写入行 → 封印分键锁红)。
