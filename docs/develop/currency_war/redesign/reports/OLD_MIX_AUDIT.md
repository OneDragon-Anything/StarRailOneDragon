# 货币战争重构 · 新旧方案混杂清查报告(OLD_MIX_AUDIT)

> 清查日期:2026-09(只读审计,未改任何生产/文档文件)
> 判别尺(用户裁定):**新承载** = IMPL_DESIGN / NEW_MATH_FRAMEWORK / DESIGN_MANDATE_LAYER / math_proofs(P 编号,2026-09-01 后重推)/ redesign decisions(dd-NNN)任一引用其语义;**旧残留** = 只被旧机制时代产物引用(无任何新方案文档引用其语义);**边界件** = 重构期显式「承接/重述」的旧结论,须确认承接声明在场。
> 实际盘点口径:`cw_registry.py` 的布尔开关不是约 20 个,是 **约 50 个**(含伞开关+子旗标);本报告按开关族分组清查,并对全部数值字段做了旧命题溯源抽查。

---

## 0. 总体结论(一句话版)

**新方案四件套本身基本干净**:旧机制概念(form=1.0 配方 / locked_line / target_comp / spend_receipt / 转型臂 / 旧臂 / W948 字段族 / P13)在 IMPL_DESIGN、NEW_MATH_FRAMEWORK、DESIGN_MANDATE_LAYER、IMPL_FIX_LEMMAS 四文档中**零活引**(精确 grep 逐词核过,见 §2)。真正的混杂集中在三处:①**旧层 decision_v2 注册表在消费 math_proofs 已判废的数值**(P3 阶梯/P15 作废回归/P8 作废口径);②**一批「挂账未跑」的默认关开关族**悬在旧层(新方案不引用、旧层自身的生命周期义务也未履行);③**承诺随迁移批 3 删除的影子比对接线未删干净**。追加裁定补查的**「过时旧描述」类**(§7):先例费用档星目标已废留档;同型尸体一处(中期护航三套,自标待删);活着的攻略启发式行为规则四条(桥线池优先序/final 件条件上场窗/插件禁用矩阵/桑博环境强偏好),均无证明无新承接,需逐条裁决。

---

## 1. cw_registry.py 开关与字段分类

先立框架:**cw_registry 整体属于旧层**——IMPL_DESIGN §2.7(R23-5 节)原话「旧层 cw_registry 存值系策略设计参数非机制真值」。IMPL_DESIGN §4.1/§4.2 显式裁定「decision_v2 冻结共存(基线对照完整性优先),新包 cw4 以 strategy_id `mandate_v1` 注册」——即整个旧层是**声明过的 A/B 基线臂③**,不是残留。因此下表的「新承载/边界/残留」按**字段级语义是否被新文档点名**判。

### 1.1 新承载(语义被新方案文档直接引用)

| 字段/族 | 证据 |
|---|---|
| `interest_cap`(经 `interest_floor()` 派生) | IMPL_DESIGN §2.3/§6.2/§6.3:新 levelup 的 arm2 结构守息门 `g*=10×cap_resolved`;dd-007 端点纪律同源 |
| `line_switch_theta` / `line_switch_debias_delta` / `line_switch_min_dwell` 的**语义**(滞回参数 θ/δ/D_min) | IMPL_DESIGN §2.7(R23-5/R24-2):P16 结构被新方案 line_selector 承接;**但注意:新方案明确不消费 registry 存值**——θ/D_min/δ 归 `audit/provisional.py`【拟】槽位,标定前 None ⇒ should_switch fail-closed 不评估。P16_VALIDATION 门⑤的 θ=1.0/δ=0.15/D_min=2 只作「sim 注入形态」 |

除这两族外,**新方案四件套没有引用 registry 任何其他开关/常量的语义**(IMPL_DESIGN §6.3 处死名单反而是反向操作:写死 9/HP 分支/连胜息常量/线锚计数闸门族/危局双阈值/V̄ 闸门/i_bar/u-H 注入链全部处死,替代判据全部有新证明出处)。

### 1.2 边界件(承接/重述声明在场,不算残留)

| 项 | 承接声明位置 | 说明 |
|---|---|---|
| decision_v2 全栈(含 registry 绝大多数默认开开关:blood_budget_stop / formed_stop / vd_p2 / vd_p1_pair / engine_affinity / buy_lock / evolve_* / sell_*_guard / p1_early_gate / press_channel / levelup_multihit / p2_core_firstpiece / crisis_release / merge_completion_exempt / copy_swap_target_exempt / handoff 族 / remedy 族 / S5 卖序族 / 词缀消费面三开关 等) | IMPL_DESIGN §4.1「新 strategy_id 双被测体重建……decision_v2 冻结共存」+ §7 要点 1 | A/B 三臂的 legacy 基线臂;承接声明在场。**它们退出历史舞台的路径 = A/B 收口后整栈退役,不是逐个清理** |
| θ/D_min/δ 的 registry 存值(1.0/0.15/2) | IMPL_DESIGN §2.7 R23-5:「旧层 cw_registry 存值系策略设计参数非机制真值……不得入 proof_consts,入【拟】」 | 显式重述+归宿裁定,在场 |
| cw_plane_table 的 `PLANE_FALLBACK_PRIORS` / `DEFAULT_PLANE_LENGTHS` | dd-003 / dd-007 / R25-1 / R46-1 / R49-6 链 | 新方案唯一真值源 schedule_of 的回退先验;端点纪律已按 R46-1/R49-6 收口(消费语义 (9,9,9)) |
| DESIGN_MANDATE_LAYER 中的 cw3 八台叙述(L149 等) | DML L147「【R-SYNC 2026-09:落地载体已改】……从『原地改 cw3 八台』改为新建」 | 历史归因引用,带 supersede 标 |
| IMPL_DESIGN §5.1 判前锁 v5→v6 变更 | §5.1 R9 次要/R19 验证缺口:「PREREG_cw3_vs_legacy_AB.md v5 为 cw3-vs-legacy 双臂产物,cw3 已物理删除(R2-7)」+ v6 挂账单一源清单 13 行(每行带出处批次+落地判据) | 承接声明在场。**但注意:v6 尚未落进 PREREG 文件本体**(该文件 grep 不到 v6/三臂/mandate_v1 字样),判读器 ab_judge 词表迁移同样挂账未执行——§5.1 自己定了「任一未落地 ⇒ sim 数据不得进判读门」的硬前置,属**已声明未执行的边界**,非遗留 |

### 1.3 旧残留(无任何新方案文档引用其语义;且在旧层自身处于判负/悬置态)

以下开关族**新方案零引用**,且各自在旧层的生命周期档案里是「默认关 + 判据挂账未跑」或「判负保留」态。用户裁定「旧方案彻底出局」后,它们的合法存在理由只剩「decision_v2 基线臂还活着」这一层;若 A/B 收口后 decision_v2 退役,它们将整批变为死代码。**处置建议分两档:随基线退役整批删除(首选);或在退役前按各自预注册判据跑完定谳(仅当用户还要采信旧层的验证结论时才值得)。**

| 开关族 | 现值 | 旧层档案状态 | 处置建议 |
|---|---|---|---|
| `spend_gate_enabled` / `spend_gate_interest_enabled` / `spend_gate_bench_enabled` | 全 False | ADR-0499:三轮 A/B 传导格三度双败,「维持关保留(禁第四态删码)」;恢复前置=实机锚量化判据(未定) | 关死现状=已关;**建议随基线退役删除**(新方案 arm2 守息门+D3 bench 语义已覆盖) |
| `realization_chain_enabled` + 6 子旗标 + 7 占位参数(兑现链 v2,W802) | 全 False / 占位 | PREREG_兑现链A_B v3 判据挂账,「A/B 数据齐即跑,不过则删码留 ADR,禁悬置默认关」——挂账未执行 | **悬置默认关,违自身纪律**;随基线退役删除,或补跑判据 |
| `p1_tier_push_enabled` + 3 子旗标 + 8 参数(W803) | 全 False / 占位 | ADR-0494,PREREG_tier_push_AB v2 判据挂账未跑 | 同上 |
| `recipe_fence_enabled` / `form_break_sell_blocked_enabled` / `below_floor_spend_gate_enabled`(形态达标三方向,ADR-0432/0433/0434) | 全 False | 「验证排期挂账(退役批 ADR-0466/0467/0469 补 deadline):不过 → 删码留 ADR」——排期未到/未跑 | 同上 |
| `c1_directed_spend_enabled`(ADR-0443) | False | 验证排期挂账同上 | 同上 |
| `line_switch_survival_gate_enabled` / `rounds_two_state_enabled`(C4) | 双 False | W638/W643 判据挂账;注释自带「不过 → 删码留 ADR,禁无限挂起」 | 同上;注意这两族的 p2 损血表/p_win 表本身被 math_proofs P12/P15v2 方向级引用,删开关不等于删表 |
| `crisis_fallback_enabled` / `crisis_fallback_max_cost`(W956) | False / 2 | 「策略开关生命周期第 1 态:默认关=A/B 注入态;预注册判据 = PREREG.md,判正后翻默认开」——判据未跑 | 悬置默认关;随基线退役删除 |
| `w875_energy_leak_enabled` / `w875_sync_action_enabled` | 双 False | 开臂判据挂账(环境恢复后补验) | 同上 |
| `w878_mono_attribute_enabled` / `w878_formed_bond_enabled` / `w878_slow_burn_enabled` / `w878_synth_equip_dep_enabled` | 四 False | 单帧锁+样本判据挂账(「当前无模拟/实机输入,悬置默认关」) | 同上 |
| `junk_first_sacrifice_enabled` / `equip_env_fill3_enabled` | 双 False | 双钥匙开臂判据挂账(实机 ≥2 局零漏采) | 同上(机制真值部分保留在 data 层,不随开关删) |
| `longterm_refresh_discount_enabled` + 阈值/折价 | False | 开臂判据①(局内刷新计数接线)未做,「缺省 0 → 折后价永不生效」=死参数 | 同上 |
| `megastar_enhance_enabled` | False | 三前置挂账(画面建档/机制确认/执行面接线),「执行面未接」 | 同上 |
| **`director_v2_shadow_compare` + decision_assembly.shadow_compare_step + prep_director 的接线** | False(但代码路径活着) | registry 注释:「采集完成即回 False;**旧环随迁移批 3(ADR-0465) 退役时生产分支一并删**」。迁移批 3(w633)已落地、旧策略 line_strategy/default_strategy .py 已删,**但影子比对的生产分支没有按承诺删除**(decision_assembly.py:76-78/197、prep_director.py:1388-1390 仍接线) | **真残留(承诺删除未执行)**:建议核实 ADR-0465 删除清单后删掉该旗标+影子比对分支 |
| `boss_tax_p75`(标量) | 34.0 | 注册表注释自认「无运行时消费者——保留原因=sim 标定接口锚+退役挂账 sim 标定批裁定」 | 自我登记的准僵尸;随基线退役或 sim 标定批裁定 |

### 1.4 ⚠️ 数值字段里的旧命题口径残留(本审计最重要的发现)

新方案判废的数学口径,仍在旧层注册表里**以「已证」语气被生产消费**:

| registry 字段 | 引用口径 | math_proofs 现状(2026-09-01 后) | 判定 |
|---|---|---|---|
| `rung_value = {1:1.4, 2:3.0}` | 注释:「P3 已证边际(e0→e1 +1.4 / e1→e2 +1.6 金/轮)」 | **P3 数值面=证明不成立,1.4/1.6 明确标(作废)** | 旧口径活引。math_proofs P3 行自带豁免注:「其生产闸门残留在旧层,随新设计替换消亡」——即被登记过的旧层残留,但**引用语气(「已证」)未同步降级**,误导后续读者 |
| `h3_win_rate = {0.139, 0.416, 0.778}` | 注释引 P3「H3 阶梯矩阵胜率」 | P3:「阶梯 13.9/41.6/77.8%(作废)」 | 同上 |
| `hp_to_gold = 0.5` | 注释引「P3:4.4HP≈2.2金」 | P10 行:「hp_to_gold/h3_win_rate 溯废 P3」 | 同上 |
| `vd_p1_loss_intercept=11.32 / vd_p1_loss_slope_rung=-0.37` 及其下游(`emergency_hp=25` 的推导带、`p1_levelup_stop_rung` 的 L_c≈10.58、`streak_floor_loss_damage` 的 boss 26.71 锚) | 注释引 w324 粗模型拟合(ADR-0424/0425) | **P15 行把同一组数标作废:「battle 条件伤害=11.32−0.37·rung(作废);P15v2 数值见重证件(battle 10.35,rung 梯度只立方向不立系数)」** | 生产在消费一个被证明层判废的回归系数;emergency_hp=25 的「持久依据」注释还显式引 math_proofs P15 + 该拟合——**引用链与 math_proofs 现状态直接冲突** |
| `piggy_refresh_round_cap=1` 的注释口径「s≤0.277R / P8 上限 s≤2金」 | 注释引 P8 | P8:「Δp=0.277 作废禁引;数值闸门(s≤2金)全部撤回」;重推门式改为 c<Δq·R(待实采) | 注释里的数值依据已废(现行值 1 次/节点是保守惯例,但书面依据失效) |
| `realization_delta_p_tier=0.75` 的推导注释 | 「P3 羁绊期望表 e0→e1/e1→e2 ≈1.4-1.6 金/轮」 | 同 P3 作废 | 同上 |

**处置建议(需用户裁决)**:decision_v2 作为 A/B 基线臂继续跑,数值冻结可以接受(基线本就该冻结);但**注册表注释的「已证」语气必须降级为「P3/P15 作废前的旧口径,基线冻结值」**,否则每个后续读者都会再踩一次「引用已废证明」的坑。若用户认为基线臂也不该用废数,则 rung_value/h3_win_rate/hp_to_gold/vd_p1_loss_* 需按 P15v2 重标定——那是行为变更,须走 ADR。

---

## 2. 新方案四件套的旧概念 grep(范围 2)

逐词精确 grep(`form=1` / `locked_line` / `target_comp` / `spend_receipt` / `转型臂` / `旧臂` / `W948` / `intention_stagnation` / `PLANE_LENGTHS_TRUTH` / `cw3`):

| 文档 | 结果 |
|---|---|
| IMPL_DESIGN.md | **全部零命中**(含 `cw3` 零命中;§5.1 只以「cw3 已物理删除(R2-7)」的 supersede 语气提及,经 v6 清单行 1 承接) |
| NEW_MATH_FRAMEWORK.md | 全部零命中;「配方」仅出现在 [20] 过渡配方(游戏知识)与 P42 组件语境,合法 |
| DESIGN_MANDATE_LAYER.md | 旧概念零命中;`cw3` 多处=三轮 A/B 失败形态的**历史归因**,且 L147 有【R-SYNC】supersede 标声明「落地载体已改为新建」——边界件,承接声明在场 |
| IMPL_FIX_LEMMAS.md | 全部零命中 |

辅助核:`PLANE_LENGTHS_TRUTH` 在生产代码也零命中(§6.1 处死项确实没落回代码);`target_comp` 在生产代码是活状态字段(prep_actions/prep_director/cw_synthesis),非孤儿。

## 3. IMPL_FIX_LEMMAS / 判前锁 v6 验收清单逐行 provenance(范围 3)

v6 挂账单一源清单实体在 **IMPL_DESIGN §5.1**(13 行,IMPL_FIX_LEMMAS 各批对照表多处回指「v6 行 N」)。逐行核:

- **行 1-13 全部有「出处批次 + 落地判据」两列**,出处=R9 次要 / R19 / R40-1 / R38-低9 / R42-1 / R44-6 / R43-6 / R45-2 / R48-3 / R48-2 / R54-3 / R59-1 / R63-3 / R64-4 / R65-4——**全部是新方案对抗修复批的证明锚,无一行是旧口径沿用**;
- 行内嵌的修订链(R48-2 标、R50-1 标、R51-1 标、R56-2 标、R59-1 标、R63/64/65 联动标等)均为「打标不删史」的新方案内部 supersede,纪律合规;
- 唯一沾旧的地方:**锁源文件本体** `PREREG_cw3_vs_legacy_AB.md` 仍是 v5 双臂 cw3 口径,v6 变更只挂在设计件里没落进锁文件;`tools/cw/ab_judge.py` 词表迁移同样挂账。这不是「引了旧内容」而是「新变更未落地」,§5.1 行 2 已把它定为判读前硬前置——**列为待执行项,非残留**。

## 4. research/ 已推翻/禁引命题的活引检查(范围 4)

math_proofs.md 中标已推翻/禁引/作废的命题:P2(禁授权)、P3(数值面废)、P4(方向证伪)、P8(数值面废,结构面降级维持)、P9(数值禁引,候选线维持)、P10(数值降级)、P13(已推翻)、P15(原回归废,P15v2 成立)、P27(禁引)。对四件套逐一 grep:

| 命题 | 新文档引用情况 | 判定 |
|---|---|---|
| P13(用户点名) | **零引用** | 干净 |
| P27 | 零引用 | 干净 |
| P2 | NMF §1.1/§4:以「P25 v2 形态待证明占位,默认关」重述——引用的是重推形态不是废结论 | 边界件,承接方式合规 |
| P8 | NMF §3.3 表:入「五个待证钩子只占位不授权」(P26/P25/P29/P8/P12),结构形态消费、数值门已撤 | 边界件,合规 |
| P9 | NMF §公理区:「首次 0hp 保底 1hp,再次归零结束(P9 候选线语义)」——恰是 P9 获准维持的候选线语义,未引禁引的期望账数值 | 边界件,合规 |
| P15 | 新文档引用走 P15v2 冻结语料(tools/cw/proofs/p15)口径 | 合规;**但旧层 registry 引 11.32/−0.37 旧回归,见 §1.4** |
| P3/P10 废数值 | 四件套零引用;只在旧层 registry(§1.4) | 新方案干净 |

research/ 其余篇:economy.md 的「已…」命中实为过期攻略存档补记说明,非推翻命题;未发现新文档对 research 已废结论的活引。

## 5. 生产代码旧机制残留(范围 5)

- **W948 转型臂:无复发**。字段族只在 cw_registry.py 的墓碑注释里(L1674-1678,ADR-0509 留档),全仓 src/test 零活引用;
- **已删机制墓碑注释清单核过一遍**:p1_iface 五开关(ADR-0487)、c1_asset 五字段(ADR-0444)、rb_signal 七字段(ADR-0507)、件价值八字段(ADR-0496/0497)、spend_receipt_gate(ADR-0504)、early_pace/filler_star/goldrich/refresh_starve/catchup/phase_form_score/formed_stop_min_level 等——**全部只存在于墓碑注释,无活代码路径**;
- **cw3 机器层代码:.py 已全删**(cw_phase_machine / cw_loss_budget / cw_deadlock_prover / cw_decision_bus / cw_horizon / cw_release_layer / cw_signal_lock / cw_line_tribunal / cw_market_clearing / cw_power_table 等),src 内 `import cw3`/`cw3` 零命中;strategies 下仅剩 decision_v2_strategy.py(line_strategy/default_strategy 已删,且有 test_cw_early_kernel 的防复发锁看守「decision_v2 不得 import line_strategy」);
- **唯一真残留:`director_v2_shadow_compare` 族**——registry 注释承诺「旧环随迁移批 3(ADR-0465) 退役时生产分支一并删」,迁移批 3 已落地,但 decision_assembly.py(shadow_compare_enabled/shadow_compare_step)与 prep_director.py(L1388-1390)的接线仍在(详见 §1.3);
- **卫生问题(非功能残留)**:`src/sr_od/application/currency_war/__pycache__/` 下有约 110 个无源 .pyc(cw3 时代已删模块 + 分包迁移前旧位置的模块),`sr-od-test/test/.../__pycache__/` 下有 test_cw3_*.pyc、test_cw_w948_transform_arm.pyc 等孤儿测试编译缓存。Python3 不会从 __pycache__ 无源导入,功能无害,但会污染 grep/审计——建议清一次。

## 6. sr-od-test 锁旧语义测试(范围 6)

- 逐词 grep(含 W948/transform_arm/cw3/line_strategy/default_strategy/全部已删字段名):**无任何 .py 测试在锁定已删/判负机制**;
- 命中处全是两类合法形态:①**墓碑注释**(test_cw_adr0293_calibration 等,记录字段已删);②**防复发锁**(test_cw_infra_locks 的 dead_arm_cleanup_locks 段:_DELETED_FIELDS 断言已删字段不得复活;test_cw_intention_switch/adr0297 同款)——这是反向守卫,是资产不是残留;
- test_cw_star_form.py 一处「truth_star.json 已随 cw3 删除迁移,不再可复算,改锚 sim 实测」=如实降级声明,合规。

---

## 7. 过时旧描述废弃候选(追加裁定 2026-09:旧方案时代经验/攻略启发式行为规则,无数学证明、无新方案承接,仍活现行代码)

> 判别口径(用户裁定):**行为启发式规则**(直接决定 bot 做什么)才算;经验**数据标定**(λ_death 分层表、remeet_window_rounds 锚点、through_rate 标定接口等,有兜底清单+声明)= 活校准,**不算**;comp 库里的阵容构成/站位/机制事实(随游戏版本变,docs/game 三级证据)= 游戏知识,**不算**;用户口述裁定(如 rebirth_floor=20 的 [18])= 有裁定背书,列边界不列候选。先例 = M6 费用档星目标(default_star_goal)。

### 7.1 先例本体现状核对

| 项 | 现状 |
|---|---|
| 费用档默认星目标(≤3费冲3星/≥4费2星) | **已废并留档**:cw_comps.py L79 注释「费用档默认星目标规则已废弃,M6」;cw_plaza_comps.py L8/L22 同步声明「star3_by_cost 仅校准对拍用,不作星目标决策输入」。现行 star_goals 只认成型档显式要求(逐 comp 显式条目,属游戏知识)。全仓无按费用档推星目标的活代码。剩尾工=注释/对拍词汇收尾,归已派的删除批 |

### 7.2 已退役但尸体还在(同类先例,可并入删除批)

| 规则本体 | 出处 | 现行消费点 | 废弃影响面 |
|---|---|---|---|
| 中期护航三套 `EscortComp`(cw_comps.py L453 起整段) | 难度攻略 22-34(6 级正式构筑、低造价、P2 稳定连胜)+ ADR-0140 | **消费点已清零**(注释自证:全仓 grep 仅本文件自引用 + test_cw_affix_megastar 的 serves 词汇对照 + test_cw_decisions 的 escort_for 单测);自标「禁止新增消费点,后续清理批可整段删除」 | 只影响两个测试的词汇对照/单测,须同步删测试段;无生产行为面 |
| 成长型不护航 `GROWTH_MECHANICS = {"燃血","欢愉叠层"}`(cw_comps.py L485) | 攻略(「需叠被动从头到场,护航打断节奏」) | 待核——若仅护航链(EscortComp 退役链)消费则已死;grep 显示 cw_plugins/candidates 命中需甄别是否同一段 | 若死:随 EscortComp 同批删;若活:单列候选 |

### 7.3 活着的攻略启发式行为规则(候选,需逐条裁决)

| # | 规则本体 | 出处 | 现行消费点 | 废弃影响面 |
|---|---|---|---|---|
| 1 | **桥线池优先序**(cw_bridge_pool.py:P1 桥按 81 篇攻略验证强度排序、P2 桥=列车4+护盾3「40 篇验证的平滑桥」) | 攻略频次统计(V4.0 攻略过渡框架),无证明无新承接 | **活**:cw_intention / cw_line_defs(过渡线选择倾向) | 过渡期锁线优先序会变(改由评分/完成度排序承接);sim 过渡局行为需回归验证 |
| 2 | **final 件条件上场窗口**(cw_deploy_seat.py L83/L199:「手上有 4击破 才让白厄上场」的判据形式化;final 件买而囤 bench、窗口触发才上场) | 663 帖攻略精读 #243/#245/#249 | **活**:deploy 席位决策(final 件上场时机) | 白厄等 final 件上场时机改由通用部署排序决定;需 sim 验证不劣化 |
| 3 | **插件禁用矩阵 `PLUGIN_DISABLE_MATRIX`**(cw_plugins.py:如「不要杰帕德(分受击概率)」) | 攻略单帖(#48 等) | **活**:买候选生成(candidates 侧) | 个别插件件恢复可买;影响面小但逐条核对帖号证据强度 |
| 4 | **特邀专家桑博环境强偏好**(cw_comps.py L510:「攻略明言开局必须刷专家邀请环境」33k use 帖) | 攻略帖频次 | **活**:投资/环境选择偏好(cw_investments 消费) | 环境选择改由统一 EV/invest 判据;桑博 DOT 局开局行为会变 |

### 7.4 边界件(有裁定/承接/游戏知识属性,不列候选)

- `rebirth_floor=20`:口述 [18] 用户裁定(应急保留重生基数),新方案 §6.3 也点名其为「ADR-0463/0503 crisis 系出口=legacy 兜底」——有承接声明;
- `char_positions` 站位(ADR-0139)、`weak_planes` 位面乏力过滤、comp 构成/评级/星级显式要求:游戏机制事实与阵容知识(game 侧,随版本变),非策略启发式;
- 买经验硬门 `want_level_up`(cw_deploy_seat L269,ADR-0129):`_xp_gold_floor` 已进新方案处死名单(§6.2),有承接;
- decision_v2 内部经验常数族(forming_bias / crisis_buy_bias / off_target_sell_bias / form_floor=20[注释自认「Q1 四档 sim 对照待校准」未校验] / bond_fallback_max_cost / carry_gate_max_round / formed_stop_min_round / phase_fallback_min_round 等):无数学证明,但整栈属 §1.2 冻结基线边界,随基线退役消亡——**其中 form_floor 是唯一注释自认未校准的,点名提示**;
- 排除项(活校准,用户口径明确不算):remeet_window_rounds(2-4 费=锚点间拟合,标定接口)、through_rate(推断近似,sim 校准域)、λ_death 分层表、boss_tax 分位锚组、streak_floor 拟合表(其口径作废问题见 §1.4,那是「引废证明」不是「无证明启发式」)。

---

## 8. 处置建议汇总(按优先级)

1. **(需用户裁决)registry 数值注释降级**:rung_value / h3_win_rate / hp_to_gold / vd_p1_loss_* / emergency_hp 推导链 / piggy 注释——把「P3 已证 / P15」语气改为「P3/P15 作废前旧口径,decision_v2 基线冻结值(math_proofs P3/P15 行登记在案的旧层残留)」。是否按 P15v2 重标定基线臂数值 = 行为变更,须用户裁定 + ADR。
2. **(删除)`director_v2_shadow_compare` + decision_assembly/prep_director 影子比对接线**:ADR-0465 迁移批 3 承诺的删除未执行,旧环已不在,比对无生产者。
3. **(整批删除,随 decision_v2 退役)**:§1.3 列出的全部「默认关+挂账未跑」开关族(spend_gate 三旗 / realization_chain 七旗 / p1_tier_push 四旗 / 形态达标三方向 / c1_directed_spend / C4 双开关 / crisis_fallback / w875×2 / w878×4 / junk_first / equip_env_fill3 / longterm_refresh / megastar_enhance / boss_tax_p75 标量)。若用户想在退役前采信其中任何一族的旧层验证结论,须先跑各自预注册判据——否则它们只是「禁悬置默认关」纪律下的悬置债。
4. **(待执行,非遗留)**:判前锁 v6 落进 PREREG 文件本体 + ab_judge 词表迁移(IMPL_DESIGN §5.1 行 1-2 已定为判读前硬前置)。
5. **(卫生)**:清理 src 与 sr-od-test 的无源 .pyc 孤儿缓存。
6. **(过时旧描述,需用户逐条裁决)**:§7.3 四条活着的攻略启发式行为规则(桥线池优先序 / final 件条件上场窗 / 插件禁用矩阵 / 桑博环境强偏好)——废弃即行为变更,建议各配一条 sim 回归再裁;§7.2 中期护航三套 + GROWTH_MECHANICS 可并入先例删除批;form_floor=20 是 decision_v2 内唯一注释自认未校准的经验值,随基线退役前可点名复核。
