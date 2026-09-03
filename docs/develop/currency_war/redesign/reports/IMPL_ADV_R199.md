# IMPL_ADV_R199 · 货币战争重构设计文档对抗审查(无锚轮·修复风暴期文档面首攻)

> 攻击者=全新视角(无历史锚);对象=redesign/ 四文档正文(IMPL_DESIGN / IMPL_HISTORY / CONTRACT_V2_PROPOSAL / CONTRACT_SERIES_DECISION)+ IMPL_FIX_LEMMAS(冻结对账)+ design_telemetry 文末 R196-R198/K 批登记节(修复期新增面)。任务书五重点面全覆盖。开工前已读 `sr-od-currency-war-dev` skill 入口;无锚纪律遵守:计划成形前未读任何 IMPL_ADV_*.md 与 telemetry 文末登记节(先通读正文→成形计划→再执行,登记节仅在执行期对照读)。

## ① 攻击计划

1. **契约完备性声明 vs 现树**(重点面 1):IMPL_DESIGN §4.2.2 三条纪律的「注册完备性静态断言,漏登记=测试红」声明,对现树 criteria 公开函数集直调核验(契约 27/28 条计数、CONTRACTS 键集、静态测试亲跑)。
2. **§4.2.1 权威枚举表 vs 代码 BYPASS_TABLE 对账**(重点面 1 自洽半边):doc 侧「criteria/* 全部函数位二分全称」与代码侧单一源表逐行互查。
3. **R196-R198/K 批登记节谱系与编号完整性**(重点面 2):「R198 标」在 IMPL_DESIGN 两处使用的批次归属;登记节「已落地」声明 vs 现树复验态。
4. **新键的键节/索引登记纪律**(重点面 2+5 交叉):R198/K 批新键 vs R100-N1/R101-N1 确立的三向对账纪律。
5. **v2 附章/提案档与定稿正文同步**(重点面 3):R195 修复后「提案与定稿一致」声明逐段核。
6. **ab_run_20260903 结论引用失真核**(重点面 4):登记节引用的全部数字对 raw json 直调复算。
7. **冻结残余 11 项 + 冻结六装置**(重点面 5):双载体计数、零重复、新键装置面定性。

## ② 新症逐条(三元组:行号+检验式+结果)

### 症1(中高)· CONFLICTS 完备性静态断言现树红:criteria/refresh 公开函数 `r1_commitment_account` 未登记契约,「漏登记=测试红,封死」的声明已被现树自身证伪

- **三元组**:`src/.../cw4/criteria/refresh.py` L37 `def r1_commitment_account(v_gap: float, ...)`(公开函数,`_` 前缀外);`criteria/contracts.py` L130-226 CONTRACTS 的 refresh 域键集={r0_stop, r1_start, r2_budget, crisis_refresh_invariant, hard_node_reinforce_gate}(亲数 5/6,缺 r1_commitment_account);检验式=`uv run pytest sr-od-test/test/sr_od/app/currency_war/test_cw4_contracts.py::TestRegistryCompleteness::test_covers_all_criteria_public_functions`(PYTHONPATH=src)→ **FAILED(亲跑,1 failed 14 passed)**。
- **文档面失真**:①IMPL_DESIGN §4.2.2 纪律 3(L429)「新增判据函数必须同步登记 CONTRACTS(注册完备性静态断言=test_cw4_contracts.py,漏登记=测试红,与 BYPASS_TABLE 同款 R9-1 缺行病封死)」——机制本身如实(确实红了),但封死声明的前提「新增即同步登记」已被打破:该函数在 shop.py L621/L642 现役消费(注释自称「判据本体=criteria/refresh.r1_commitment_account」,形态=P40 R1 启动门总账 `c_eff·E[refreshes] ≤ V_gap`,即零刷新修复批显式登记的「标定批既定欠账」),却不在 CONTRACTS/BYPASS_TABLE/IMPL_DESIGN §4.2.1 三处任何一表=R9-1 缺行病在契约批自家辖域的复发;②K 空窗回退修复批复验记录③(design_telemetry L2924)「cw4 快集 2400 passed+1 预存红(test_cw_w614 旧核零漂移 digest)」——现树该域至少 2 红(本测试+`test_cw4_mandate_v1.py::TestBypassEnumeration::test_criteria_functions_all_enumerated` 同因亦红,亲跑 1 failed 10 passed),最近登记节复验声明与现树矛盾。
- **归属申报(不遮蔽)**:该函数无 git 史(cw4 整目录 untracked),按其语义(R1 启动门总账=标定批欠账)大概率属在飞标定批中间态。但任务书豁免面仅 provisional.py 中间态;refresh.py/shop.py 的公开判据函数落树而三表零登记,契约批「类级封死」声明与「新增判据函数必须同步登记」纪律的违反是现树事实,如实立案(修复=补 CONTRACTS/BYPASS_TABLE/§4.2.1 三处行,或在飞批落位时随批登记)。

### 症2(中)· IMPL_DESIGN §4.2.1 权威枚举表与代码 BYPASS_TABLE/函数集漂移:doc 侧「全部函数位二分全称成立」对现树为假(≥4 行缺位)

- **三元组**:IMPL_DESIGN L421 完备性口径「上表覆盖 criteria/* 与 proof/line_selector 全部函数位,二分全称成立(每行有归属)……新增顶层模块必须同步入表」;检验式=grep `hard_node_reinforce_gate|funding_support_sell|r1_commitment_account|ensure_contract` 于 IMPL_DESIGN.md 全文 → **零命中**(亲跑);而代码侧 `criteria/__init__.py` BYPASS_TABLE(L21-77)含 `('contracts','ensure_contract')`(L74)、`('sell','funding_support_sell')`(L34)、`('refresh','hard_node_reinforce_gate')`(L57)三行,`refresh.py` 另有 `r1_commitment_account` 公开位(两表皆缺)。
- **失真定性**:§4.2.1 自称「臂①旁路集函数级枚举表」的唯一权威(R9-1/R10-3/R11-3/R38-5 四代缺行病封死声明所在),但 R198 批给代码 BYPASS_TABLE 补 `contracts.ensure_contract` 行时(design_telemetry L2910 文件面自证)未同步 doc 表;`funding_support_sell` 在 doc 表中无行(doc 仅有 `sell_for_interest`「支付能力变现」子域行 L406,代码已拆独立函数+第六类别「支付支撑通道」);`hard_node_reinforce_gate`/`r1_commitment_account` 代码在表 doc 不在。「新增顶层模块必须同步入表」的自家纪律被自家批打破=权威表缺行病第五代复发(doc 载体半边)。附带:doc L421 类别合法值清单=发射位/门/谓词/状态函数/发射面(复合)五值,代码 BYPASS_TABLE 实用类别含「判据/闭式」「结构不变式」「支付支撑通道」共八值(代码 docstring L9 已列六值),两载体类别词表不一致。

### 症3(中)· 「R198 标」两批共一号:IMPL_DESIGN 内契约化批与 K 空窗回退补注共用 R198 编号,谱系冲突无消解语句

- **三元组**:IMPL_DESIGN L423 节头「#### 4.2.2 判据契约纪律(**R198 批新增**,2026-09-03 用户批准的组合性改进①…)」与 L431 规格补注「(**R198 标形态**——空窗期方向形态;2026-09-03 第三病灶裁定,SEEDS_EMPTY_LEDGER_DIAG §4)」;检验式=design_telemetry 登记节谱系亲读 → L2908「## R198 判据契约批」与 L2918「## K 空窗回退修复批(2026-09-03 第三病灶)」系**两个独立批次**(文件面互异:R198=contracts.py 新建+接线;K 批=cw_intention.py+shop.py 接线+**「IMPL_DESIGN §4.2.2 规格补注」属 K 批文件面**,L2920 亲读)→ 结果=IMPL_DESIGN 把 K 批产物标为「R198 标」,与登记节谱系冲突。
- **两读不消解**:①补注属 R198 批(则 K 批文件面声明失真);②「R198 标」=借用 R198 键族前缀的标注(K 节 L2922「按 R198 节键族前缀同款展开」只辖键族展开,不辖补注归属)。任务书明示「如实立案或澄清」——本批未见任何澄清语句,编号完整性声明缺位。修法=补注标签改「K 空窗回退修复批标(键族前缀=R198 节)」或登记节补一行两批共号申报。

### 症4(中)· 键名索引未随 R198/K 批新键更新:`criteria_contract_violation` / `shop_k_fallback_p1_gap` 零键节零索引行,「共 40 节」计数失效

- **三元组**:design_telemetry L377-379「## 附:键名索引(本文 ### 键节)」封闭清单止于 `emitter_post_truncation_dropped`(R197 修复批补登,共 40 节);检验式=grep `criteria_contract_violation|shop_k_fallback_p1_gap` 于该索引及全部 `### 键` 节 → **仅命中 R198/K 批登记节正文(L2912/L2922),键节区/索引零命中**(亲跑)。
- **纪律依据**:R100-N1/R101-N1a-c 三向对账纪律(键节/内嵌清单/索引;R101 以三键同型缺登立案为中)与 R196/R197 连续两批的同款补登先例(`switchline_*` 四键节 R196 补登、`emitter_post_truncation_dropped` 键节 L367+索引 R197 补登)确立「新键=键节+索引行」为常态通道;R198 节自称「键登记=design_telemetry 文末 R198 节」(L2912)单载体登记,K 批同款(L2922)——偏离既有纪律且未申报偏离理由。`shop_k_fallback_p1_gap` 的计数对象四条件句(L2922)实质是键节五栏(计数对象/观察级/基线锚/归因/超标)的压缩态,信息在但载体错位;索引「共 40 节」自此计数失真(实际 42 键族)。

### 症5(低中)· 提案档「与定稿正文一致」声明失真:R195 修复只落定稿正文,CONTRACT_V2_PROPOSAL.md 与 CONTRACT_SERIES_DECISION.md 至少三处漂移而头部声明未随撤

- **三元组**:CONTRACT_V2_PROPOSAL.md L3-4「已定稿并入 v2……**内容与定稿正文一致**,后续禁改,以契约为单一源」;检验式=两文件 §3 逐行 diff 亲读 → ①提案 L24 拖拽族行仍含幻影成员「**装备拖拽,商店线侧**」,定稿 L70 已删并带 R195 修注(「原行含『装备拖拽,商店线侧』系幻影成员……已删;IMPL_ADV_R195 症1」);②定稿 L75「词表源对账声明(PickEvent 辖外)」与 L108「完备枚举辖域限定(R195 症1 辖域限定)」提案档零对应;③定稿附章行 5 含「R194 症4 裁定如实申报」指针(L164),提案附章行 5(L68)无 → 结果=「一致」声明为假。
- **定性**:R195 症1/症3 修复落点只在定稿正文(design_telemetry R195 节 L2832-2834 措辞「契约 v2 §3.1 拖拽行删幻影成员」未区分载体),提案档头部「一致+禁改」声明变成双源漂移通道(R95-A4「全量转录为活体漂移通道」同族形态)。修法:头部声明改「内容与定稿正文一致**截至 R195 修复前**;R195 勘误仅落定稿正文,以契约为单一源」或同步提案档(禁改声明下取前者)。

### 观察_OBS-1(不立案,邻界申报缺位)· R198/K 批新键的冻结族邻界定性未申报

R196/R197 冻结对账均有新键定性句(「键集零扩张」/「新键=截断器披露计数,非度量面装置」),R198 节(L2910-2916)与 K 节(L2920-2924)冻结对账只写「冻结族/冻结残余 11 项零触碰」,对 `criteria_contract_violation`(自称「计数>0=接线语境前提漂移信号,判读时须逐键归因」,哨兵味表述)与 `shop_k_fallback_p1_gap` 未做装置面定性。本审查独立定性:两键均为行为面 fail-closed 弃权/回退的披露计数,无阈值门、不进判读门,**不构成冻结六装置(度量面验证装置)扩张**;但邻界定性申报缺位本身是 R197 既定格式的缺口,建议后续批补一句。

## ③ 流程锚-豁免

- `sim/engine_p1.py`(test_cw4_contracts `_decide` 经 `sim_decision_registry`)、`operations/` 全域:流程锚,未立案。
- `kernel/cw_intention.py`(p1_gap_window/hoard_target_set)、`decision/cw4/*`(contracts/shop/entry/criteria):策略器侧锚,照常核验——K 空窗回退接线(shop.py L360-385:plane==1 ∧ ist 在场 ∧ p1_gap_window ∧ 契约放行 → `hoard_target_set(state,_ist).char_targets` sorted 单一源,计数 `shop_k_fallback_p1_gap`)与 §4.2.2 规格补注逐点一致;`p1_gap_window`(cw_intention L496-508)与 `_derive_p1_pair` 不锁分支同源(同一 `_p1_system_support`+`P1_PAIR_LOCK_MIN_SUPPORT=0.5` L445/L527)亲验;P1 空窗 hoard char_targets= `_pair_members(_P1_PAIR_PREF)`(hoard_target_set 源码亲读)=诊断反事实集合逐字同源,「逐位一致」声明结构成立。

## ④ 冻结残余对账 + 冻结族

- **计数**:11 项=LEMMAS 冻结残余清单 9 项(第 7 项 R182 销账标在案 → 有效 8)+ design_telemetry 第 10 项(R98 节「### 冻结残余清单增补:第 10 项」,L506 节头亲读在位)/第 11 项(R115 节 L1078 节头在位)/第 12 项(R162 节 L2266 节头在位)——计数自洽,R186-R198 各节申报链一致。
- **零重复**:三 telemetry 项对象位点互异(L67 激活率门行 cap_sup 核读缺位/L69 激活率门验收级滞后/L75 D_ε 监督面引注止),与 LEMMAS 第 8 项(§5.2 窗口高侧预算,位点 L53)互不重叠;R196-R198/K 批冻结对账「零触碰」与各对象位点现文核对无翻案痕迹。
- **冻结六装置**:新键三枚(criteria_contract_violation/shop_k_fallback_p1_gap/emitter_post_truncation_dropped)按装置面定性(见 OBS-1)均非度量面验证装置扩张;冻结宣言「禁止新增验证装置」字面未破。

## ⑤ 清洁门申报

- 文件面:除本报告外零写入、零 git 操作;全部检验只读(两轮 pytest 亲跑、raw json 直调复算、注册表/现树函数集枚举)。
- 重点面 4(ab_run 引用失真)核验结论:K 批登记节引用数字对 `seeds_empty_ledger_cf_raw.json` 直调复算全符(零动作局 21/100→0;受累局 avg_hp 16.05→33.52;avg_actions_after 41.81;全量均值 31.93→39.24)——**零失真,不立案**;contracts.py 各谓词规格锚对 ZERO_REFRESH_DIAG §3-3/§4.1/§4.2/§6-2 与 IMPL_DESIGN §3.2 L349 拦截对象列逐点核对一致。
- 禁凑数声明:本报告 5 症+1 观察,均亲验现树/现文,无压症;不立案项(OBS-1)已给独立定性供后续批采纳。
