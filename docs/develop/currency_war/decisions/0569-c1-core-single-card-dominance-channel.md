# ADR-0569: C1 直通核心卡支配性支(并列支配通道,dominance 邻位)——直通终局核心卡信号层入口落码,P25 占位接管

- 状态:已实施
- 关联:设计《直通核心卡信号层入口》(docs/develop/currency_war/design/设计-C1直通核心入口.md,实施唯一口径;spotcheck_v3_C1_C3.md 复核解锁)、ADR-0506(支配性结构通道无条件落地先例,P36-a)、ADR-0556(t5_p1_false 息账零损支配论证先例,T5 止血买)、01_math_framework §3 支配性优先序与 §7 P25 钩子行、`cw_comps.CORE_SINGLE_CARD_REGISTRY`(名单单一源)、`mandate_v1/shop.py` 选择序、`mandate_v1/criteria`(P25 占位接管)

## 1. 背景与问题

直通终局核心卡(希儿/银狼型「单卡依赖型体系核心」)在整个买牌决策链上结构性不可见:锁线态买牌路由的放行集 = 线内成员(M2 义务)/囤货臂/合成臂,其余统一落 `non_line` 终态拒因,无后继评估通道。实机病灶局 g_20260906_182456 p2r2:希儿在售、g=48、4 件共 11 金买得起,shop_rejects 纯判据排除(`non_line`);P35 复盘回放钉死强锁候选集空、希儿量子 G=0.0062——候选机器(promote_candidates,P65 已证希儿量子活载体)看得见希儿系,买牌路由看不见。既有 dominance_buy 资格门(`dominance_buy_eligible` = g>g* ∧ bench_free>0 ∧ stop_flag)在该帧双因恒假(g=48<50 溢余门 + 锁线态 stop_flag=False)——**锁线态下支配买入结构性缺席**,本通道填的正是这个空。

## 2. Considered Options

- **A(否决)并入既有 dominance_buy 通道**:须把零参数资格门三分支化(stop_flag→锁线态/溢余门→不破息/燃料件→名单),稀释 P24 锚、牵动其测试锁语义重推(违「既有通道零改动」),且两支判据域不同构。
- **B(采纳)并列支配通道挂 dominance 邻位(既有通道之后、M3 之前)**:独立判据函数 + 显式辖域分界(既有=停手态∧溢余带∧线外燃料件 vs 本通道=锁线态∧不破息带∧registry 名单核心卡);1★ 全额退与席位判据共享既有单一源(`refund_full_star_ok`/`check_seats`,禁第二实现)。位次合规 = 01:15 支配性结论「零参数、无条件、优先于一切带参 EV 比较(公理 1 的执行形态)」+ :40「支配性优先序(实现时先于数值比较执行)」——支配族发射位必须先于 M3/EV(单动作契约下挂 EV 之后会被带参动作抢占);锁线∧成型重叠带(stop_flag 与锁线态可并存)两通道动作同致:既有通道序位在前先买 + 判据共享,单动作契约下无双发射。
- **C(否决)案B 移交门(核心卡出现→触发换线评估)**:结构冲突([36] 线级选择全局仅一次)、休眠机理(P16 fail-closed 封印=死规格)、粒度错配(见到核心卡的正确第一反应是囤,换线是换线机器第三/第四触发辖域)。
- **数值支(P48③ 统一式)不落码只挂账**(设计 §5 分期落码声明):U_X/RHO_IMPUTE/NBAR_ESTIMATOR/λ_death 生成式未标定 + P48④ 排队消费位未落码,双前置齐才启用;此形态非开关(无「默认关悬置」态)。01 §7 P25 钩子行改指该数值支,旧占位函数 p2_lock_buy 随本批删除(接管,消双源)。

## 3. 已实施架构

- **名单单一源**:`cw_comps.CORE_SINGLE_CARD_REGISTRY`(dict[名→出处指针];知识判据,禁数值权重)。唯一入选规则(谓词式,设计 §3【修订·B3】):入选(c) ⇔ 玩法权威文档中 c 所属线的开线/成型判据以「单一具名卡牌 c 在手」为必要条件 ∧ c 是体系伤害主体。在册 = 希儿、银狼LV.999(欢愉线信号卡注册名;量子同频 4 费「银狼」是另一张卡,不在册)。封闭性辖双出处(四体系表希儿系行 + 直通线信号谱),名单变更随玩法文档版本走;换线机器与入口共用本单一源。
- **资格门**:`mandate.core_single_card_buy_eligible(locked_buy, bench_free)`(dominance_buy_eligible 邻位同构分工:门辖帧级前件,逐卡判据发射位现算)。锁线态判据 = `locked_buy_membership` 非 None(⟺ locked_comp 非空;phase 与 locked_comp 同点同置/同点清,单判惯例同 `locked_line_recipe_floor_conflict` 注)。
  - **修订注(ADR-0625,T-115 恒买腾席批)**:签名收窄为 `core_single_card_buy_eligible(locked_buy)`(`return locked_buy`)——席位维自帧级前件下放商店发射位循环内(席满帧须入循环走腾席购买支,防帧门前件短路使腾席支不可触达);生产消费点唯一 = shop.py C1 锁线腿 elif 门,契约键核验系 `ContractCtx.locked_buy_members` 与签名零耦合。
- **发射位接线**(`shop.decide_shop_action`,dominance_buy 之后、M3 之前):候补 = registry 名单 ∧ ∉ 锁定采购集;逐卡 = `refund_full_star_ok`(1★ 全额退)→ `check_seats`(席位共享单一源)→ `predicates.t5_p1_false`(L 项零损,P47 现算;Ī 取 streak_pre=0 保守近似,收入低估 ⇒ 发射收窄,与 T5 位同款申报)→ `check_affordable` ⇒ 买因 `core_single_card_buy`(囤,不上场;同帧多候补等价免费期权,发射序=店面确定性序)。S 预留硬约束③对象列不含本通道(息纪律由 L 项零损承载,设计判据式无 s_reserve 前件)。
- **契约**:`('mandate', 'core_single_card_buy_eligible')`,前提谓词 `_core_channel_locked_ctx`(可核验派生形态:`ContractCtx.locked_buy_members` 新字段必须系 `locked_buy_membership` 实解析物,非空 frozenset=锁线态;None=未锁帧合法 fail 方向;空集/异型=字面量冒充,违例弃权+计数)。
- **P25 占位接管(全域 4 处)**:①`criteria/buy.py` p2_lock_buy 占位函数删除;②`criteria/contracts.py` 契约键删除(孤儿行同批清);③`criteria/__init__.py` BYPASS_TABLE 行删除(与①同批);④`test_cw4_contracts.py` 注入式 fixture 键改现存契约键 `('sell','sell_for_interest')`(不测死对象);另 01 §7 P25 钩子行改指数值支。
- **对拍测试双向化**:`test_cw4_mandate_v1.TestBypassEnumeration` 补行→函数反向断言(墓碑行豁免,口径同 `test_cw4_contracts._TOMBSTONED_KEYS`)——设计 §6「全表对拍双向强制」由声称落成事实(spotcheck δ1 勘误:落码前实况为函数→行单向)。
- **观测键**:拒因拆键 `core_candidate_rejected`(`shop_unbought_reasons` non_line 分支,registry 卡可辨;sim 检查器归机会错失类)+ §7 三键分账 `core_candidate_seen`(候补支触发)/`core_dominance_buy_hit`(支配性支命中)/`core_numeric_fail_closed`(数值支域帧 fail-closed 显影)。
- **开店闩申报**:备战期开店闩(`cw4_shopped_phase`)辖 run_mandate 的 OpenShop 发射节流;本通道在商店决策访问位下游,闩不辖,零闩读/写,默认不消费。
- **零新开关**:结构支零参数直接落码(strategy-work §3 第 1 档);数值支挂账不落码(待证钩子形态,非开关)。

## 4. 边界申报

- **未锁帧行为零漂移**:`locked_buy_membership` None 帧通道不评估,连 `core_candidate_seen` 都不落——P1 空窗/配方锁/weak/降格帧全部零变化。
- **重叠带语义(δ2 措辞)**:锁线∧成型(stop_flag=True)帧两通道前件可同时为真;行为面无歧义(既有通道先手 + 判据共享 + 单动作契约)。
- **再遇账量级(m3 口径)**:3 费核心卡再遇代价按 P25 v2 修正②贴线带逐点账(非「极高档」);支配性支成立不依赖再遇账量级(净成本≈0 免费期权,Δλ_death 不承重)。
- **名单身份精确性**:欢愉线银狼的注册表卡名 = `银狼LV.999`(升星升费 3/4/5 费档);通道按卡名匹配,量子同频 4 费「银狼」不在册,防同名异卡误配。
- **拒因遥测帧语义**:`core_candidate_rejected` 沿 `shop_unbought_reasons` 既有帧首口径(本帧通道买入的卡在下帧自然消失;帧内「先标拒后买入」与 non_line 既有语义同型)。
- **delta 池/sim 轨迹**:通道在锁线帧改变买面决策 ⇒ sim 轨迹与 Δ池对拍读数可漂移——判读时按三键分账归因;A/B 对照手段不进生产代码。

## 5. 验证

- 红证(临时禁用→锁红):发射位接线临时置 `_core_locked=False` ⇒ 新通道测试 4 红(launch/息破/2★/bench_full 分账);恢复全绿。
- 对拍双向红证:临删 `ev_buy_veto` 函数保行 ⇒ 新反向断言红(删函数不删行=红);临删 BYPASS_TABLE 行保函数 ⇒ 既有正向断言红(删行不删函数=红);恢复全绿。
- 新增 `test_cw_core_single_card_channel.py` 10 用例(通道判据 7 + 拒因拆键 1 + 名单锚定 1 + 闩申报 1)全绿;`test_cw4_contracts.py`/`test_cw4_mandate_v1.py`/`test_cw_shop_rejects.py` 受影响面全绿;`ruff check` 改动文件绿。L1(`-m "not slow and not legacy_baseline"`)结果见交付汇报;全量套件归编排者 commit 门。

## 6. 风险与后果

- **窄域风险(设计 §7 自报)**:若 bench 长期满或买入普遍破息,支配性支退化窄域、通道放行率趋零——防线=三键分账先行,sim 批与实机各读一次分布再定谳;窄域实锤的正确回炉点是重开 V_slot 定价或 P25 重推,不是调宽判据。
- **数值支悬置**:P48③/P48④ 双前置未齐前,C1 对「贵过免费期权域」的核心卡场景(2★ 直出/破息帧)无修复效果——如实在 `core_numeric_fail_closed` 显影,不伪造放行。
- **名单维护**:名单错扩(把非单卡依赖结构卡登入)会放大免费期权囤积面——排除举证随设计 §3 在案,锚定测试钉死在册全集,误扩即红。
