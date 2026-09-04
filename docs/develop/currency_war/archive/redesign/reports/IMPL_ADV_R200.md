# IMPL_ADV_R200 · 货币战争重构对抗审查(无锚轮·代码面+量具面)

> 攻击者=全新视角(无历史锚)。开工令已执行:先读 `sr-od-currency-war-dev` skill 入口+references(strategy-work/sim-testing),通读 `IMPL_DESIGN.md` 总纲(判据索引表/§1 模块结构/§6.4-R 换核切面)后动工。无前提纪律遵守:本任务书给的审查对象清单之外,未读任何 IMPL_ADV_*.md 既有报告与登记节(R199 报告仅在本报告成文前按「报告族格式」要求读了排版骨架,其结论未作为任何发现的输入;成文后复核发现 R199-症1 所指 `r1_commitment_account` 契约缺行在现树 contracts.py L200-204 已在位=该症已收口,本报告零重复立案)。只读审查:零代码改动、零 git。

## ① 攻击计划

1. **代码面**:cw4 全包(entry/mandate/proof/shop/bridge/criteria×7/statefn×8/audit×3)逐文件通读;数值锚点一律直调注册表来源复核(cw_shop_odds/cw_economy/cw_state/cw_plane_table),建模对象对照 skill/设计文档的玩法语义——「公式对」与「对得上游戏」分两道门。
2. **量具面**:ab_core_swap.py 门组(自配对门/arm_diff_probe/活性守卫/v6 检查单)+ sim/checks/(runner 聚合、decision_v2 契约等价门、ledger 买卖互斥检查)——攻「量具测的是不是它声称测的东西」。
3. 指定外围:mandate_v1_strategy.py(注册桥)、series_adapter.py(长度 1 适配器)。

## ② 新症逐条(论断+证据+推理链;代码锚点=文件:行;结论强度取最弱一环)

### 症1(高)· `p_complete` 尾概率 off-by-one:求和闭区间含 `x=m`,算出的是 P(≥m+1) 不是 P(≥m)

- **代码锚点**:`decision/cw4/statefn/vopt.py` L140-142:
  `tail = 1.0 - sum(_comb(refreshes, x) * q**x * (1-q)**(refreshes-x) for x in range(min(m, refreshes) + 1))`
- **复现/推导**:docstring 与注释自declared「P(命中 ≥ m) = 1 − Σ_{x<m} …」,但 `range(min(m, refreshes)+1)` 是 `x ∈ [0, m]` **闭区间**——求和含 `x=m` 项,`tail = P(x ≥ m+1)`。数值例(m=1, q=0.5, refreshes=1):真值 P(≥1)=0.5;代码 Σ_{x=0..1}=1.0 ⇒ tail=0.0。**单探测针即可证伪**。
- **消费面与影响**:`proof.evidence_gate`(proof.py L173,P38 证据门序数形态,`pc > 0.0` 过门)与 `delta_p_hat`(vopt.py L152-160,P38 概率因子)。边界系统性左移一档:任何「恰好差 1 张、预算内单发可中」的线在门上被误判零完成率。方向=保守(不过门),但这是**数学错**,不是声明的保守端取值——P38 闭式带规格(NMF §2「ΔP̂」行)与此实现两读不可同真。
- **活性申报(强度最弱环)**:evidence_gate/delta_p_hat 现树无生产调用点(should_switch 走 e_rounds 序数半边,proof.py L186-193 自declared)——本症当前为**潜伏面**,标定批/证据门接线日即转为行为面。测试仓无该尾值的数值锁(test_cw4_statefn.py 仅模块映射行 L315-316),不会被旧锁拦住修复。
- **定性**:治本——`range(m)`(m≤refreshes 时);泛化步:同文件其余边界已亲核(`p_bar_exact` 超几何 none-项、`_streak_v_table` 转移、registry `_refresh_dist` 均无同病)。

### 症2(中高)· `slot_q` 分母与注册表超几何口径背离:漏扣已持有 j 张的离池量——「公式内部自洽」但与注册表权威模型(【注】米游社 V4.4 采集)不等价

- **代码锚点**:`decision/cw4/statefn/odds.py` L34-37:`denom = v*a - taken_c; return p * (a - j) / denom`。
- **注册表直调复核**:`data/cw_shop_odds.py` `_refresh_dist` L125-127:剩余同费总牌 `total = (a−j) + (v−1)a − c = v·a − j − c`,注释明写「拥有的 j 张已离开牌库」。cw4 的 `slot_q` 分母 `v·a − taken_c` **未扣 j**——分子扣了(a−j)、分母没扣,持牌越多偏差越大(cost1 满池 v·a=540,j→27 时 q 相对偏差 ~5%)。
- **方向分析(不对称,非全保守)**:q 低估 ⇒ ①`p_shop` 低估 ⇒ `a7_lower_bound = c/P_shop` 高估(金可行性截断格的退路值上偏=保守);②但 `p_miss = (1−q)^H` **高估** ⇒ `v_opt = u·p_miss·(c/P_shop)` 双分量同向放大 ⇒ **V_opt 系统性高估 = 期权/压库面 fail-open**。「保守端」 blanket 声明不成立。
- **强度最弱环**:v_opt/a7/slot_q 现树无生产消费位(line_switch_sell 的 vopt 全式未接线,见症5③)——本症为「对得上游戏」门上的**模型背离在册**,接线日转行为面。
- **定性**:治本——分母改 `v*a - j - taken_c`(与 registry `_refresh_dist` 同式,NMF §2 q 行公式随之勘误);泛化步:`p_shop` 的 `(1−q)^SHOP_SLOTS` 槽间独立假设 vs registry 同店内无放回超几何——二阶小量,但同属「包装层悄悄换模型」族,修症2 时一并声明或对拍。

### 症3(中)· 「挂后台效果」保护在三条卖面通道中两条未实现、一条语境恒 False:声明的资格过滤整体不可达

- **代码锚点**:
  - `criteria/sell.py` `sell_for_interest` L64-73:docstring L59-61 声明「对象 = 1★ ∧ **无后台效果** ∧ 零重叠(资格谓词 = predicates.bench_effect_qualified)」,函数体只查 `star==1` + `zero_overlap`,**零调用** bench_effect_qualified;
  - `criteria/sell.py` `funding_support_sell` L87-103:docstring L84-85「凑息档序**同资格**」,同样零调用——**两臂同开的现役通道**(entry.py L442/L533、shop.py L750 消费);
  - `mandate.py` `fuel_sell_candidates` L178-179:`BenchEffectContext(rust_affix_present=False, equipped=False, herta_star_supply=False)` **硬编码全 False**——例外①(黑塔·星级供强语境)与例外②(库藏生锈词缀局)构造性不可触发,predicates.py L98-124 精心实现的例外枚举在全部调用点失效。
- **推理链**:predicates.bench_effect_qualified 的三消费位声明(fuel_sell 豁免/凑息档序资格/危局阀桶不动子集,predicates.py L114-115)中前两个在代码里不存在或空转;后果=funding_support(支付支撑)可把挂后台效果件(如小黑塔星级供强件、生锈局已穿装备件)当燃料卖掉筹资。M4 通道至少留了谓词调用形状(空语境),另两条连形状都没有——「同类还有吗」的答案就是:卖面三通道只有 1/3 接了谓词、0/3 接了真语境。
- **定性**:治本——三通道统一经共享装配函数(语境从 state 现读:rust_affix_present/equipped/herta_star_supply 均有可观测来源),禁各通道自拼;泛化步:grep 全 cw4「docstring 声明了过滤、函数体没做」的声明-实现缺口(本审查另捕获 stockpile 的 V_slot 净门同型,见症5④)。

### 症4(中)· 量具面:零刷新事故的「正式 A/B 前置守卫组」不拦零刷新事故形态——事故前置态双守卫全绿

- **代码锚点**:`sim/ab_core_swap.py` `FAMILY_PROVISIONAL_DEPS` L228-233(refresh 族豁免条件=V_GAP 处 None 期)+ `action_family_liveness_gate` L285-290(豁免自动生效,零发射不红)+ `_v6_row_specs` L386-434(16 行判据无一涉及 V_GAP/标定注入态)。
- **推理链**:该守卫组自declared 对策(L208-212:「正式 A/B 在 EV 面全未标定态开跑…B1/B2 被当作处理效应误读。本守卫组把『正式 A/B 前的硬前置』代码化,防同类漏检」)。但复演事故配置(V_GAP=None 开正式 A/B):活性守卫——refresh 族进 exempt 清单,门绿;`require_v6_green_for_formal_ab`——16 行全过,门绿。**防护纯程序性**(依赖操作者记得 `apply_core_swap_calibration`),代码化的「硬前置」不含它要防的那件事的最小充分条件(ev_arm=full 的正式 A/B ⇒ EV 面至少一个槽位非 None,或豁免清单必须随 A/B 判读产物一并落档并强制消费)。
- **定性**:治本——v6 清单加一行 `text/mark` 型判据「formal AB ⟹ V_GAP 注入态(或 exempt 清单为空的显式豁免批文)」;或 arm_diff_probe 返回值携 `exempt` 状态、ab_judge 拒绝判读含 refresh 豁免的 formal 批。补丁形态=在 apply 处加日志(不拦,不采)。泛化步:同族槽位 U_X/T_SEARCH_A 的「注入悬崖」(症5)同受此门失守波及。

### 症5(中)· 【拟】注入的「开闸即全开」语义悬崖族:注入本应解锁标定比较,实际解锁无门放行(量具面+行为面双重失真)

四例同根,合并立案:

1. `criteria/buy.py` L50-52:`T_SEARCH_A` 非 None ⇒ `t_search = frozenset({1, 2, 3})` **硬编码**——EV 买面对全部 1-3 费非线 1★ 全额可退件放行,候选生成里没有任何 EV 比较(唯一后续门 ev_buy_veto 只查星级与金)。
2. `shop.py` `_t_search_active` L325-334:同款占位,M6 压库/dominance 消费——注入后买全部 1-3 费 1★。
3. `criteria/sell.py` `line_switch_sell` L42-51:U_X/V_MS 注入 ⇒ 旧线非新线 bench 件**全卖**,docstring 自认「比较式本体…标定批开闸后接 vopt 全式」——但 `apply_core_swap_calibration`(ab_core_swap.py L76-97)**已经注入 V_MS**;当前靠 U_X 仍 None 挡住,一旦 U_X 注入即从「全堵」跳「全卖」,中间的 V_opt/V_power 比较式不存在。
4. `criteria/stockpile.py` L31-32:`if bench_free == 1: pass`——声明的「free=1 过 V_slot 净门」是**空语句**,注释自称「V_slot🔴=0 保守代入放行」:对一道**放行门**代入 0 门槛是放行偏,「保守端」措辞方向反号(1★ 全额可退使占用近可逆,可辩护,但注释的定性是错的)。

- **推理链**:零调参纪律(strategy-work §1)要求每个数有出处;这四处把「未标定」折叠成「注入即取无界宽松缺省」,使任何注入态 A/B 测得的都不是设计语义(量具失真),也使 fail-closed 的安全声明在注入路径上静默失效(行为失真)。症4 的守卫失守让这族悬崖可以直接进正式判读。
- **定性**:治本分两层——①窗口/门槛数值必须从 CalibValue 派生(哪怕先用 ci_lo),禁注入态硬编码 {1,2,3};②「净门/全式未落位」的发射位在注入态应保持缺省保守(如 line_switch_sell 未接全式前对注入态返回保守子集而非全集),或最少在 ab_core_swap.apply 处 disclose「注入解锁面=无门放行形态」。泛化步:grep `注入形态占位` 全 cw4。

### 症6(低)· 刷新费字面量双源复发+幻影符号引用

- **代码锚点**:`mandate.py` L400 `s_line(0, _cap_of(session), [], 2)` 与 docstring L392-393 引「REFRESH_COST_BASE 建模常量」;`shop.py` L175/690/693 `int(state.shop_refresh_cost or 2)`。单一源=`cw_state.REFRESH_COST_BASE=2`(grep 亲验,obs 层消费点均 import 符号)。R196 症6 自家「字面量改单一源」纪律(cheapest_member_cost 同批修过)在这三处漏网。治本:import 符号名。

### 症7(低中)· 量具面覆盖域:sim A/B 只经 `decide_shop_screen`,新核 prep 线整体零覆盖,门组结论的辖域大于测量域

- **代码锚点**:`sim/engine_p1.py` L946-947(sim 唯一决策入口=`sess.shop_state_frame` + `strat.decide_shop_screen`);grep 全 sim 无 `decide_prep_screen`/`prep_obs_frame` 消费(checks/decision_v2.py 的契约等价门是手搓帧探针,非 sim 引擎)。
- **推理链**:`new_core_self_pairing_gate`(ab_core_swap.py L126-150)的「新核零漂移/确定性」结论、活性守卫的 sell 族覆盖,全部只测 shop 波路径;entry.emit 三遍编排、prep 截断器 `truncate_frame_stable`、`_merge_ev_before_frame_end`、升档器求值位、proof 线级状态机在 sim 全零覆盖。而 ab_core_swap.py L23-24 预注册声明「臂间 ledger diff 的归因域…diff 全部归于 **prep/shop 决策面**」——prep 在 sim 不可达,该归因域声明与测量域不符(diff 只可能源于 shop 面)。SIM_CONSUMPTION_MAP Q1 申报「证明面=商店波」属实,但门组 docstring 的确定性/归因结论未随辖域收窄。
- **定性**:治本=门组与预注册声明补测量域限定句,或给 sim 引擎补 prep 段驱动(工作量另议);泛化步:liveness 门 'sell' 族的「活过」证据同样只覆盖 shop 侧发射位(M4 shop 版/funding/sell_for_interest),prep 侧 `m4_fuel_sell_for_m2` 发射位无 sim 证据。

### 观察(不立案,邻界申报)

- **OBS-1** `bridge.py` L161-162:`bench_slots` 派生用真值过滤 `if b is not None and getattr(b, 'slot', None)`——物理槽位 1-9 基(cw_prep_actions.py L12)下 slot 0 不存在,现行为正确;但 falsy 过滤是潜伏陷阱(应 `is not None`),若槽位基变 0 即静默漏槽→复检误截断。
- **OBS-2** `entry.py` L334 `ClickSpheres(max_k=min(3, len(obs.spheres)))` 魔数 3 未见注册表/契约锚(零调参纪律问一句:3 从哪来)。
- **OBS-3** `predicates.arm1_existence` docstring(L31-34)「deploy_cap=None 兜底固定槽表常数 10(保守端)」与契约层 `_arm1_cap_level_driven`(None=违例弃权)并存——兜底分支经 run_mandate/shop 的 ensure_contract 前置已不可达,双语义死代码,建议注释收口。
- **OBS-4** `audit/derived.py` L75-82 登记 `difficulty_interim`(公式形态:108+品质+遭遇+特殊,subtag 语料拟合),但 `lambda_death.difficulty_band`(L111-121)无任何公式——难度缺读直接域外。IMPL_DESIGN §1「真值优先+**公式 interim 兜底**+持续对账」的兜底半边未落码(~10% 帧丢 λ,方向保守)。登记表声称的入口与实现体语义不对齐,属登记漂移信号。
- **OBS-5** `shop.py` 发射序:r1 付费刷新(RefreshShop 截断点,L692-694)之后的 sell_for_interest/funding 发射会被截断器丢弃(L715-769 的卖面追加在 out 尾部)——计数披露在(`emitter_post_truncation_dropped`),方向安全(刷后重决策),但注入态下 funding 支撑与刷新互斥的交互未在任何门/锁中显式化。

## ③ 流程锚-豁免(核验过未立案的正面面)

- **shop M2 无 stop_flag 门与 prep 侧等价**:missing 非空 ⇒ stop_buy 定义性 False(线不成型),两读自洽(shop.py L438-482 vs mandate.py L267)。
- **同轮买卖互斥检查兼容**:check_no_same_round_buy_sell(ledger.py L252-301)只报「买先于卖同名」;cw4 shop 波 M4 先卖后买、卖面只用 pre-wave bench 快照(新买件不入卖集)——0 冲突。
- **商店合成触发截断**(shop.py L315-321):held 计数含 deployed(保守域)、逐 BuyCard 递增——逻辑正确。
- **R199-症1 收口复验**:contracts.py L200-204 已含 `('refresh','r1_commitment_account')`,注册完备性恢复(本审查独立复核,非采信 R199)。
- **series_adapter MRO 处理正确**:别名覆写绕过 list 化派发(series_adapter.py L51-59),checks/decision_v2.py check_prep_series_contract 四判据+语料覆盖门结构完好。
- **λ 表启动必载守卫**(lambda_death.py L69-103):损坏态空 dict+一次性报警、可消费格 CI 完整性校验、48 格计数——与 R2-4 规格一致。
- 运行时只读:全程零 pytest/零写入工作区(报告本身除外)、零 git。

## ④ 冻结对账

- 本轮对象=代码面+量具面,冻结残余清单/冻结六装置未直接触碰;新提及计数键均为**已登记键**的消费面核查(emitter_post_truncation_dropped/ev_conflict_dropped/criteria_contract_violation 族),零新键提案。

## ⑤ 清洁门申报

- 文件面:本报告单件,零其它写入、零 git。
- 禁凑数:7 症+5 观察,每症给代码锚点/复现或推导/方向分析/治本-泛化;症1 含可执行数值证伪例;不立案项均给独立定性。
- 强度声明:症1 证据强(数值证伪)但消费面潜伏;症2/症5③ 同为潜伏面(接线前不改行为);症3/症4/症7 为现役行为面/量具面。各症结论强度已按最弱一环标注。
