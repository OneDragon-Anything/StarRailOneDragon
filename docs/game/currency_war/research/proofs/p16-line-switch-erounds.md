# P16:换线判据 E_rounds 的超几何口径、滞回稳定性与截断误差界

> 状态:**已证**(口径命题 + 稳定性命题 + 误差界命题;落地=cw_line_switch.py,registry.line_switch_*)
> 数据源(单一源代码,数值不抄):`cw_shop_odds`(`SHOP_SLOTS=5` L28、`POOL_COPIES_PER_CARD={1:27,2:27,3:9,4:9,5:9}` L33、`DISTINCT_CARDS_PER_COST` L37、`REFRESH_PROB` 表 L44-52,即 P5 实值表)、`cw_chars.CHARACTERS`(标签集)、`cw_state`(`BENCH_CAPACITY`/`bench_occupied`)、decision_v2 registry(`line_switch_theta=1.0`/`line_switch_debias_delta=0.15`/`line_switch_min_dwell=2` L791-796、`interest_floor=50` L812)
> 实现:`src/sr_od/application/currency_war/kernel/cw_line_switch.py`(`p_bar_faction`/`line_distance`/`e_rounds`/`should_switch_e`)
> 设计:W328 未成型姿态设计稿 §③(设计裁决承载:ADR-0426;实现:`posture_release.py`/`cw_line_switch.py`)
> 提出:W345 审查问⑥/C5-②(E_rounds 判据未命题化);证明=本批(W349)

## 命题

设当前线 cur、候选线 alt,各线缺口 `distance(c) = need(c) − held(c) − shelf(c)`(需求 − 持有 − 货架可见可买),估计式

    E_rounds(c) = distance(c) / per_round(c)
    per_round(c) = (1 + rolls(c)) × p̄(c, lv),   rolls(c) = min(affordable, bench_free)

其中 p̄ 为单次刷新至少出 1 张该标签件的超几何概率;切换判据为

    E(alt)×(1+δ) + θ < E(cur)×(1+δ),   且驻留 ≥ D_min。

三条:

1. **口径命题**:p̄ 的超几何口径(牌池 27/9 副本、5 格店、费用档二项混合)与 P5 主定理所用的刷新概率模型**同构**,是同一机制真值表的正确读法;
2. **稳定性命题**:θ>0 的滞回 + D_min≥1 驻留下,换线决策序列**不存在抖动**(不存在使决策在相邻帧间往复翻转的无穷交替序列),且振荡频率有硬上界 1/(2·D_min) 次/轮;
3. **误差界命题**:几何近似下 E_rounds 的加性误差有界:E[完成轮数] 与 d/λ 之差不超过单轮最大命中数 c_max=5(SHOP_SLOTS)量级的常数;截断(rolls 取当帧快照)造成的误差是**双线共模**的,在比较判据中相消。

## 证明

### ① 超几何 p̄ 口径与 P5 模型的同构性

机制真值(注册表单一源):牌池按费用档隔离,1/2 费每张 27 副、3/4/5 费每张 9 副(`POOL_COPIES_PER_CARD`,cw_shop_odds.py L33);每次刷新独立抽 5 格(`SHOP_SLOTS=5`,L28);各费用档出现格数 m 服从 Binomial(5, p_cost),p_cost 来自 `REFRESH_PROB` 等级×费用表(L44-52)——**该表即 P5 刷新-升级主定理所引用的同一张实值表**(P5 单篇「数据源」行)。

给定该费用档 m 格,格内卡牌从该档池不放回均匀抽取,p̄_cost 的全概率展开:

    P(≥1 目标 | cost) = Σ_m B(m; 5, p_cost) × [1 − C(T−A, m)/C(T, m)]

其中 T=v·a(该档池总张数)、A=目标种数×a(目标张数)。这正是超几何「m 抽全空」补事件的精确式——与 `ev_proto.p_at_least_one` 及 cw_shop_odds 内部模型同一构型(实现 p_bar_faction,L83-90,逐项对拍)。费用档互斥(每格恰属一档),故各档概率**可加**:p̄ = Σ_cost P(≥1|cost)。多标签并集按标签独立取 1−∏(1−p̄_f) 是**承认的高估方向**(联合分布高估,DESIGN §附5 诚实列表);注意该偏差方向对 cur 与 alt 双线同施,不影响②的比较结构。已见牌扣除口径:`distance` 的 held/shelf 两项把「已在板面/货架的目标件」从需求中扣除——即已见牌不重复计入 p̄ 期望,等价于按可见库存修正牌池,与 cw_shop_odds 的池模型(池减已购)同口径。证毕。

### ② 滞回 + 驻留下不存在抖动序列

设任一帧的决策为二元函数 S(e_cur, e_alt, dwell) ∈ {stay, switch}。**θ-滞回的单向性**:switch 条件要求

    E(alt)·k + θ < E(cur)·k,  k=1+δ>0。

切换发生后,原 alt 成为新 cur。若下一帧要切回(原 cur 成新 alt),需要

    E(cur)·k + θ < E(alt)·k。

两式相加得 2θ < 0,与 θ=1.0>0(registry L791)矛盾——**同一对 E 值下双向切换条件不相容**,θ-抖动在代数上被排除(δ 同乘两侧不改变此性质)。滞回的经典构造(shifted threshold)由此获得无抖动保证。

**时间维**:即使 E 值逐帧漂移使上述静态矛盾失效(两条线的 E 随局面演化),D_min=2 驻留(`line_switch_min_dwell`,registry L796;`should_switch_e` L173-174)给出时间硬约束:每两次切换之间至少隔 D_min 帧 → 振荡频率 ≤ 1/(2·D_min) 次/轮 = 0.25 次/轮。合取:**不存在帧级抖动序列;有界漂移下的往复频率有硬上界**。退化情形双 inf → 维持原线(实现 `both_inf`/`alt_inf` 分支,L163-164),无穷大不参与比较,无边界奇异。证毕。

### ③ E_rounds 截断的误差界

**几何近似的加性界**。设每轮对该线命中 X 轮 iid、E[X]=λ=(1+rolls)·p̄、X≤c_max=5(每轮至多 5 格全中)。完成 d 张缺口的轮数 T_d 满足更新理论的基本更新不等式(对 iid 非负整值 X):

    d/λ ≤ E[T_d] ≤ d/λ + E[X²]/(E[X]·min(1,P(X≥1))) ≤ d/λ + c_max/p̄,

即估计式 d/λ 的**加性误差 ≤ 5/p̄ 轮**(p̄∈[0.1,0.5] 常态带 → 上界 10-50 轮的松包;实际因每轮多命中的几何衰减,误差远小于此包——demo 帧 lv6、distance=2 的 E≈4.54/6.02 轮,DESIGN §③,量级与 5/p̄ 包一致)。关键点:误差是 d 与 λ 的**缓变函数**,不随 d/λ 放大,方向偏保守(低估 λ 侧因 rolls 取下界)。

**截断的共模相消**。rolls=min(affordable, bench_free) 取**当帧金位与货架快照**(实现 e_rounds L135-138):未来金的回充(息+奖励,P13 收入下界 6/轮)使真实 rolls ≥ 当帧值 → 单线 E_rounds 系统性**高估**(保守侧)。但比较判据两侧同乘 (1+δ) 且共享 θ,凡对双线取值相同或近似的误差项(δ 修偏、几何近似常数项、金位快照在相邻帧的漂移)在差式 `E(alt)−E(cur)` 中**相消**;残差只来自双线 per_round 的差异部分(不同费用档的 p̄ 差、不同 distance),其量级由①的表值精确性辖住。δ=0.15 的修偏(p̄ 满池乐观 10-20%,DESIGN §③修订1)进一步把系统偏差从判据中移除,θ=1.0 只承载去偏后残噪声——与②的滞回预算同源。证毕。

## 检验点

1. `p_bar_faction` 对拍:任取 (tag, level),与 `ev_proto.p_at_least_one` 逐位一致;lv6「持续伤害」p̄=0.3502/刷(DESIGN §⑤ 套算值)为锁定锚;
2. 稳定性锁:构造 (e_cur, e_alt) 对称对断言双向 switch 条件互斥(θ>0);D_min 锁:dwell<D_min 时无论差多大不切;
3. 单调性锁:E_rounds 对 distance 单调增、对 p̄/rolls 单调减;distance=0→0.0、p̄=0→inf 的边界分支;
4. sim 参数门(DESIGN §⑥):θ∈{0.5,1,2}×D_min∈{1,2,3}×δ∈{0.10,0.15,0.20} 网格,振荡率与假阴性率双指标(Wilson 95% 上界 ≤15%)——本命题预测:任何网格点振荡率 ≤ 1/(2·D_min) 的局占比上限,违例即命题证伪。

## 关联

- P5(REFRESH_PROB 同表、禁单次边际口径)、P13(金位回充的收入下界,截断保守侧的机制来源)、P11(溢余段刷金成本下界 0,rolls 的 affordable 口径不含息损项的依据);DESIGN §③(w328);registry L791-812(参数单一源)。
