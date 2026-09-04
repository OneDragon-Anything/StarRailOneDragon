# 换核重切批0 · 设计输入(IMPL_DESIGN 批0/批1 ↔ 现树逐项对账)

> 产出:2026-09-03。任务=把 IMPL_DESIGN.md 原始实现计划与当前代码树逐项对账,产出「换核重切批0」的设计输入。
> 文档面声明:本文件是本次任务**唯一**写入;`.debug/temp/currency_war/redesign/` 下设计件全程只读未动;IMPL_ADV_* 未读。
> 对账范围:IMPL_DESIGN.md 全文(587 行,通读)、`src/sr_od/application/currency_war/` 下 decision/(全部 24 文件面)、decision_assembly.py、kernel/(点名核)、strategies/、operations/(点名核)。

---

## ① 文档计划提取(组件清单 + 行号)

### 1.0 先裁决一个口径问题:「批0/批1」与「resolver 19 条」「意图发射器」在文档中的字面出处

**结论:IMPL_DESIGN.md 全文没有「批0」「批1」的批次命名,也没有名为「resolver」或「意图发射器」的组件。**

证据(均亲跑 grep):
- `批0|批 0` → 零命中;`resolver|Resolver|RESOLVED` → 零命中;`意图发射|意图|intent|Emitter` → 零命中;`19 条|19条|十九条` → 零命中。
- 文档的实现计划本体是 **§6.4 迁移序(L515-522,依赖序 5 步)** + **§1 模块结构(L83-116,cw4 包树)**。任务书的「批0≈包骨架+resolver 19条+statefn+audit;批1≈判据族+意图发射器」是对 §6.4 步 1(statefn 先行)与步 3(criteria 七面)的转述。

「resolver 19 条 resolved 输入」的最接近锚(按证据强度排序):
1. **`docs/develop/currency_war/redesign/02_knowledge_registries.md` §4.1 resolve_\* 契约**(L221-231):10 个签名(resolve_pool/prob_table/shop_slots/refresh_cost/xp/levelup_currency/income/interest/sell_refund/board_predicates),辖 R01-R16 的 resolved 输入。
2. **cw3 实现件 `cw3/knowledge/resolver.py`**(已物理删除,归档于 `.debug/progress/2026-08-31-currency-war-redesign/支撑/cw3_code_archive_20260901/cw3/knowledge/resolver.py`):公开 resolve_\* 函数 16 个 + 谓词助手 4 个(held_copies/pool_left_card/same_cost_taken/hp_afford_batch)= 20 个公开入口(CODE_AUDIT_CYCLE1 L86 记「10 契约+超集 5」)。
3. 树内唯一「19 条」字面 = `kernel/cw_investments.py:6`(米游社百科 19 条投资版本缺口)——与 resolver 无关。

**「19」这个计数在文档与树中均无法复现**(候选:10 契约、15 契约+超集、16/20 个实现入口,都对不上 19)。判:**流程锚-待重切 + 用户口径待确认**,不立案为缺陷(2026-09-03 辖域调整裁定)。本报告按「resolver=resolved 输入解析层(resolve_\* 契约族)」的语义继续对账——这是唯一有载体的读法。

「意图发射器」最接近锚:文档 L533(R7-1「ev_buy_candidates 候选发射器补位」)与 L400(§4.2.1 发射面行:「两函数构成发射面(候选生成+否决门一体)」)。即任务书说的「意图发射器」≈ 候选/动作发射面。

### 1.1 批0 组件清单(按文档原文;行号=IMPL_DESIGN.md 现行行号)

| # | 组件 | 职责(文档原文摘要) | 文档落点 | 行号 |
|---|---|---|---|---|
| A1 | cw4 包骨架 | 新策略包,依赖单向:入口→判据/义务→状态函数→注册表 | `decision/cw4/` | L83-88 |
| A2 | entry.py | decide_prep 三遍编排(证明→骨架→EV);输出=排序 actions 列表,每条带 `mandate: bool` | cw4/entry.py | L89、L122 |
| A3 | statefn/ 8 模块 | NMF §2 的 22 项状态量单一源:lambda_death(PL 键 λ 表+floor_eff)、interest(L 递推)、income(Ī)、horizon(R_全局,Φ 私有)、s_line(S)、odds(q/P_shop)、vopt(V_opt/V_slot/V_comp/档匹配谓词)、predicates(板满/arm1_existence 等) | cw4/statefn/ | L102-110、L133 |
| A4 | audit/ 3 模块 | derived(【推】推导量注册表)/provisional(【拟】None fail-closed 开关)/proof_consts(证明声明常数白名单) | cw4/audit/ | L111-114 |
| A5 | bridge.py | CwStrategy 子类,STRATEGY_ID='mandate_v1',config 值域扩 | cw4/bridge.py | L115、L374-381 |
| A6 | 前置半步 0 | 「挂后台效果」资格谓词载体(cw_chars 单位级字段/comp resolved 查询谓词,读装备态) | cw_chars / 谓词 | L517(R32-中⑤) |
| A7 | (resolver 口径)resolved 输入 | 投资变体参数替换进各面(01 §4.10 resolved 纪律);R01-R16 契约 | (cw3 已删;02 §4.1) | L263、L285 |
| A8 | op 层锁存写路径 | HandleInvestStrategy 共享 op → session 字段 cap_sup_latched/候选名(载体=StrategySession,GameState 禁承载) | operations + kernel/cw_strategy_session.py | L85(R74-2/R75/R76-1) |
| A9 | 前置缺陷修复 | aggregate_economy 枚举 ⊇ EconomyEffect 全字段 + sim 利息 flat 分量 | cw_investments.py / sim engine | L304(§2.12) |

### 1.2 批1 组件清单

| # | 组件 | 职责 | 行号 |
|---|---|---|---|
| B1 | criteria/ 七面 | buy/sell/levelup/refresh/stockpile/equipment 判据族(P38-P50 映射,§2.1-2.6) | L94-101、L137 起 |
| B2 | 发射面 | ev_buy_candidates+ev_buy_veto(候选生成+否决门一体)、stockpile_buy、line_switch_sell 等 EV 追加发射 | L400、L533 |
| B3 | mandate/executor | M1-M7 义务序+四硬约束检查点+M2→M4 重试环 | L92、L306-368、L343-358 |
| B4 | proof/line_selector | 证据门+should_switch+stop_buy+signal_arm 三函数位 | L91、L123、L417-418 |
| B5 | 三臂 A/B 接线 | ev_arm 遥测字段、ledger_hooks/ab_judge 判栈二元组、判前锁 v6 | L380、L520、L427-455 |

(后续批:§6.4 步 5 测试位、标定批/锚批等——均系批1 之后的事件间约束,本报告不展开。)

---

## ② 逐项对账表(组件 → 在树状态 → 证据 → 判断)

### 批0 项

| 项 | 状态 | 证据(file:line) | 判断与推理链 |
|---|---|---|---|
| A1 cw4 包骨架 | **不存在** | `decision/` 全树 glob:仅 `decision_v2/`(24 文件)+ cw_strategy*.py;grep `cw4\|mandate_v1` 全 currency_war 零命中 | 「包骨架已在树」的假设**被推翻**——在树的是**宿主管线**(见 A2 行),不是策略包。批0 仍需建 cw4 包(或裁定的等价落位) |
| A2 entry.py | **不存在;职责有对应载体但语义漂移(重大)** | 换核缝实证:`decision_assembly.py:175-202`(DecideAdapter.decide → prep_brain.assemble → prep_brain.decide)+ `prep_brain.py:201-211`(`_select` 仍复用现役 `strategy.decide_prep_screen`,docstring 自述「批 1 = 现役决策核复用;批 2 折叠为私有函数族」)+ `strategy.py:775-807`(现役旧核=规则序**步级单动作**,返回单个 PrepAction) | **最重分歧**:文档 entry=每备战期输出**排序 actions 列表**(L122);现役黑板管线=**步级单动作**(Decision.ops=(op,) 单元素,prep_brain.py:244-245)。换核必须先裁发射形态(见 ④-1) |
| A3 statefn/ | **不存在(8 模块全缺);零散既有件见右** | grep `statefn\|lambda_death\|s_line\|vopt` 零命中。既有单件:①`kernel/cw_plane_table.py:70` schedule_of + `:50` PLANE_FALLBACK_PRIORS=(9,9,9)——正是文档 §6.1(L490-494)要求的唯一真值源与 R46-1 保守上端口径,**已在树且语义一致**;②`decision_v2/economy_cycle.py`(储备制 R*/义务/通道容量,ADR-0445)+ `kernel/cw_economy.py`(reserve_cap/schedule_upgrade/refresh_ev_budget);③`kernel/cw_investments.py:586` aggregate_economy(resolved 输入后裔) | 22 项状态量层整体缺;但 §6.1「写死 9 修复」的**修复目标恰是现状**(schedule_of 已是单一源)→ 该处死项免做。economy_cycle 是现役预算模型,与新 statefn 是并存替换关系 |
| A4 audit/ | **不存在** | grep `provisional\|proof_consts` 全 currency_war 仅 cw_evolution.py:970 一处无关注释 | 且**语义反向**:文档规定 θ/D_min/δ 归【拟】None fail-closed(L239 R23-5);现役 θ/D_min 已是注册表**实值**(`kernel/cw_line_switch.py:168-174` 消费 reg.line_switch_theta/line_switch_min_dwell,registry 注入)。见 ④-2 |
| A5 bridge.py | **机制已在树,壳需新建** | `strategies/decision_v2_strategy.py:26-38`(DecisionV2Live 注册桥;__module__ 守卫机制在 L13-17 说明);`decision/cw_strategy_manager.py` 存在 | 注册桥模式现成可抄(免做的=机制);新建的=mandate_v1 壳+config 值域扩(小件) |
| A6 挂后台效果谓词载体 | **不存在** | grep `后台效果` 全 currency_war 零命中;cw_chars 无该字段 | 批0 前置半步 0 仍要新建(文档 L517 明示三消费位依赖) |
| A7 resolver(resolved 输入) | **原实现已删档;职责由 kernel 承担** | cw3 resolver.py 归档(见 ①-1.0);现役:`cw_investments.py:61`(EconomyEffect)/`:149`(STRATEGY_ECONOMY 全量注册)/`:576,586`(economy_effect_of/aggregate_economy);`cw_registry.py`(DecisionV2Registry 实值注入);消费链 `cw_economy.py`(interest_cap 等) | resolver **不是批0 待建组件**——resolved 输入(投资变体→机制参数)在树有单一源(cw_investments+registry);新核若需要 R01-R16 契约面,消费 kernel 即可。缺陷面见 A9 |
| A8 锁存写路径(HandleInvestStrategy+cap_sup_latched) | **不存在(载体在,写端与字段缺)** | `operations/cw_screen/cw_screen_invest_strategy.py:40`(现役 op=CwScreenInvestStrategy,无锁存写端;grep `HandleInvestStrategy` 零命中);grep `cap_sup` 全 currency_war 零命中;载体在:`kernel/cw_strategy_session.py:29`(StrategySession)、`:127`(active_strategies,即文档引的写入先例)、现役锁存例=v2_ever_full_interest(strategy.py:804) | StrategySession 载体**免做**(文档 R76-1 裁的落点正是现役文件);写端 op 与 cap_sup_latched 字段**新建**。注意:是否仍要锁存族取决于换核范围(若批0 不含 r2 三层门可缓) |
| A9 前置缺陷(aggregate 枚举/sim flat) | **未修** | `cw_investments.py:595-622` 亲读:重建枚举仍缺 interest_flat_per_node/gold_at_node 族/gold_at_level 族/xp_click_discount_from_level 族(文档 §2.12 L304 所指 R83-1 缺陷现场原样);sim 侧 flat 缺陷(R92-4)本次未独立复核(标注) | 文档把它定为「落码批前置缺陷」→ 换核批0 若消费息日程/破息门,此前置**必须随批0** |

### 特别核对项(任务书第 3 点)

**「resolver 19 条」**:文档无此组件(见 ①-1.0);树中对应职责=cw_investments/registry(证据如上)。「19」计数不可复现——**待用户口径确认**,不立案。

**statefn**:文档规定=NMF §2 22 项状态量的单一实现层(L102-110、L133 状态函数层纪律)。树中**无对应物**(仅 schedule_of/economy_cycle 等零散单件,见 A3 行)。

**audit**:文档规定=零调参代码形态三件(L111-114)。树中**无对应物**;且现役「注册表实值直用」与「【拟】None fail-closed」纪律相反(见 A4/④-2)。

**TurnState/DirectionView/BudgetView 算不算其中一部分?——判:不算 statefn,不算 resolver;算换核的接线缝(改造件)。** 判断依据:
1. turn_state.py:1-17 自述:「投影字段=前版方向/预算契约字段照搬」——它是**流程侧方向/预算投影**,不是数学状态量层。DirectionView=intent/locked/hoard/committed/bench_view(意向状态机只读快照,cw_intention 权威);BudgetView=interest_floor/reserve_cap/obligation/schedule/ev_auth(economy_cycle 现役件投影)。
2. 与 22 项状态量的交集≈仅 interest_floor(turn_state.py:71 `registry.interest_cap × 10`)——它与文档 arm2 结构守息门 g\*=10×cap_resolved(L172 R26-H1 行)**同式**,这是唯一语义对上位;L/λ/Ī/S/odds/V_opt 全无。
3. DirectionView 与 resolver 无关:resolver 的输入是注册表突变→机制参数(R01-R16),DirectionView 是意向/囤货/板面视图。
4. 但 prep_brain.assemble(prep_brain.py:180-198)是**每备战节点入口的幂等装配点、单一写端**——这正是新核消费 statefn 输出的天然接线面:换核时把 22 项状态量挂进 TurnState(或平行视图)即可复用全部装配纪律(幂等/快照拷贝/遥测)。故列「改造」而非「无关」。

### 批1 项(对账结论,证据从简——均 grep+点名读)

| 项 | 状态 | 证据 | 判断 |
|---|---|---|---|
| B1 criteria 七面 | 不存在 | grep `dominance_buy\|fuel_sell\|stockpile` 零命中;现役=candidates/filters/scoring/arbiter 四层(strategy.py:19-21) | 全新建;与现役四层是**并存替换**(新 strategy_id 注册,文档 §4.1 L374-381) |
| B2 发射面(候选发射器) | 不存在 | grep `ev_buy_candidates` 零命中;近义=candidates.generate_candidates(语义不同:无 mandate 标记/否决门结构) | 全新建;发射形态依赖 ④-1 裁决 |
| B3 mandate/executor | 不存在 | 现役步级规则序(strategy.py:778-784:球/箱/主流程 买→部署→装备→出战);grep `mandate_v1` 零命中 | 全新建(批1) |
| B4 proof/line_selector | **部分在树(语义漂移)** | `kernel/cw_line_switch.py:154-175` should_switch_e:判据式与文档 L239 逐字同构(E(alt)(1+δ)+θ<E(cur)(1+δ) ∧ dwell≥D_min);`:143-151` switch_allowed=辖域门;信号锁线≈cw_intention(意向分层状态机,strategy.py:9);**缺**:stop_buy 停手线(grep `stop_flag` 零命中)、证据门 P38、C_stay/χ/D_ε 全族 | 数学比较器可在树复用;停手线/证据门/滞回成本项新建;θ/D_min 归宿分歧见 ④-2 |
| B5 三臂接线 | 不存在 | grep `ev_arm` 零命中;ledger_hooks 判栈现按 strategy_id 单维 | 新建(小件,随批1/判读批) |

---

## ③ 重切建议(换核口径)

**换核的准确解剖**(证据链:decision_assembly.py:193-198 → prep_brain.py:201-211 → strategy.py:775):生产管线已在树且冻结可用;「重构实体」=替换 `prep_brain._select` 对 `strategy.decide_prep_screen`(现役旧核)的委托。新核可以两种形态落:(a) 新 CwStrategy 子类(mandate_v1)实现 decide_prep_screen 接口,config 切 strategy_id 即换核——最小面;(b) 直接改 _select 分发——侵入面大,不推荐。文档 §4.1 本就裁「新 strategy_id 双被测体」,(a) 与文档一致。

### 免做(已在树,批0 不动)
1. **宿主管线全套**:DecideAdapter/黑板契约/装配点管线/执行回放(decision_assembly.py、prep_brain.py、contracts.py、adapter.py)——「批0 骨架免做」假设中**成立的一半**。
2. **schedule_of 真值源 + PLANE_FALLBACK_PRIORS(9,9,9)**(cw_plane_table.py:50,70)——文档 §6.1 处死项的修复目标已是现状;horizon.py 新建时直接消费,**禁再建长度常量**(文档 L490 明令)。
3. **StrategySession 载体机制**(cw_strategy_session.py)——锁存/跨轮状态的既裁落点。
4. **注册桥机制**(strategies/ 目录+__module__ 守卫)——mandate_v1 壳照抄 DecisionV2Live 模式。
5. **should_switch 数学比较器**(cw_line_switch.should_switch_e)——判据式同构,可作为非窗口帧对拍锚(参数归宿另裁)。
6. **resolved 输入单一源**(cw_investments/registry)——resolver 职责的现役承载,新核直接消费。

### 改造(在树但语义偏,批0 要动)
1. **prep_brain._select / 策略注册面**:换核点本体+config strategy_id 值域扩(cw_strategy_manager 校验文案同步)。
2. **prep_brain.assemble / TurnState**:扩为 statefn 输入缝(22 项状态量装配),保持幂等/单一写端纪律——防投影散落成第二 statefn。
3. **cw_line_switch 参数归宿**:θ/D_min 从 registry 实值改 provisional(采纳文档)或**反向裁定文档跟树**(现役已有 sim/实机数据支撑的实值)——这是必须显式裁决的分歈权,不能默认哪边。
4. **发射形态契约(最重)**:步级单动作 vs 备战期 actions 列表(④-1)——决定 entry/executor/criteria 全部形状,批0 第一裁决位。
5. **DecideAdapter/决策环**:若裁 actions 列表形态,Decision.ops 多元素化+执行侧逐 op 回放绑定(现绑定表单键 decision_assembly.py:200-201)。

### 新建(缺,批0 清单)
1. cw4 包本体:statefn 8 模块 + audit 3 模块(+批1 的 proof/mandate/criteria/entry——见下)。
2. 「挂后台效果」资格谓词载体(cw_chars 单位级字段,前置半步 0,文档 L517)。
3. 前置缺陷修复:aggregate_economy 枚举补全(含 interest_flat_per_node)+ sim 利息 flat 分量(文档 §2.12;**注意**:此修会改变现役 decision_v2 臂的经济行为,须按 A/B 纪律评估是否随批0 还是独立批)。
4. HandleInvestStrategy 锁存写端 + session.cap_sup_latched 字段(若批0/批1 范围含 r2 三层门/升帽可达性判据;否则缓)。
5. ev_arm 遥测字段+判栈二元组(可挂批1,但 schema 先定以免返工)。

### 批1 影响
- 批1(criteria 七面+发射面)的函数签名全部**依赖批0 的发射形态裁决**(④-1):actions 列表形态下 criteria 返回追加动作流;步级形态下需把「每备战期多动作」折叠进步级环(与现役 defer/腾席链共存)——后者复杂度显著更高,建议在批0 设计时就把「整备期动作批」作为新核的输出契约。
- 意图发射器(ev_buy_candidates 发射面)与现役 candidates 层并存(新 strategy_id 域内),无迁移负担;L-B5(a) 哨兵(mandate=false 计数)依赖 ev_arm/mandate 遥测先落。
- 三臂判读前置(判读器迁移+v6)按文档 §5.1 R19 绑定仍归批1 之后、首批 sim 判读之前。

---

## ④ 文档与树的重大语义分歧

1. **发射粒度(最重)**:文档全篇以「每备战期 → 排序 actions 列表(mandate: bool)」为决策输出契约(L122、§3.1 执行序 L310-329);现役黑板管线=「每步单动作、环入口全量重判」(strategy.py:778「每步全量重判,先命中先出」;prep_brain.py:244 Decision.ops 单元素)。两者决策语义不等价(重试环/单帧闭环 M2→M4 等规格在步级形态下需重述)。换核设计第一问。
2. **参数纪律相反**:文档 θ/D_min/δ/u/H 系=【拟】None fail-closed、标定值只能经 provisional.py 注入(L239、L530);现役=registry 实值直用(cw_line_switch.py:168-174、cw_registry)。若换核采纳文档纪律,现役 CW 经济行为(换线频率等)会变——需按「锁的存在性纪律」重推,禁机械跟任一边。
3. **证明层承载者不同**:文档 proof/line_selector(证据门 P38+should_switch+stop_buy+signal_arm)在现役由 kernel/cw_intention 意向状态机+phase/form 判据承担(strategy.py:7-17 换源清单)——职责对应、机制不同;stop_buy 停手线在现役**无对应物**(线成型语义由 locked/committed 承载,M2 是否停买过渡件未见显式谓词)。
4. **流程锚-待重切清单**(不立案为缺陷,2026-09-03 辖域裁定):
   - 文档指向 battle_loop 时代代码锚:§2.12 指向 cw_investments.py「L586-631」——**仍准**(亲读对上);CODE_AUDIT 系指 cw3/resolver.py 行号——宿主已删档;
   - 文档 §4.1 R2-7「cw3 已物理删除」与树一致(归档在 .debug/progress);
   - 「resolver 19 条」「意图发射器」词汇无文档出处(①-1.0),后续文档引用建议改用 02 §4.1 契约名/「候选发射面」;
   - 文档 §1 包树落位 `decision/cw4/`——现 decision/ 已被 cw_strategy/manager+decision_v2 占位,新包落位无冲突但命名(是否仍叫 cw4)待裁。
5. **微弱但申报**:文档 L122 称 entry 输入=「GameState 快照」;现役黑板输入=session.prep_obs_frame(观察帧,decide_prep_screen 契约,strategy.py:786-790)——快照/观察帧两层在 decision_assembly.py:95-148 已有映射,换核时输入面取 TurnState.snap 或 prep_obs_frame 需钉死单一源。

---

## 附:本次核验方法(可复算)

- 文档:IMPL_DESIGN.md 通读(L1-587;含全部 §0-§7),grep 亲跑:`批0|resolver|意图|19 条|statefn|provisional|proof_consts|cap_sup|mandate_v1|cw4|stop_flag|ev_arm|后台效果` 等。
- 树:glob decision/ 全量(24 文件)、kernel/(44 文件面)、strategies/;点名读 decision_assembly.py 全文、prep_brain.py 全文、turn_state.py 全文、strategies/decision_v2_strategy.py 全文、strategy.py 头+775-820、cw_line_switch.py 120-179、cw_investments.py 586-640、cw_strategy_session.py 点读、operations/ 投资策略 op 点读;cw3 归档 resolver.py 函数面 grep。
- 未复核项(如实申报):sim engine_p1 利息行 flat 缺陷(R92-4)未亲读 sim 代码;NMF/01/02 三件设计文档只读了 02 §4.1 契约段;docs/develop/currency_war 其余 as-built 未逐篇对账。
