# ADR-0633: T-126 批 5 种子年龄豁免——种子账入装配 A(P78-7 落码)

- 状态:已实施(R1 对抗审 1 阻断+1 中+2 低已全处置,见 §6;工作树,入库走编排者 committer;修复形态候对抗复核)
- 关联:ADR-0585(T-126 卖出仲裁单一源正本;本批 = 其批 5 扩展)、math_proofs **P78-7**(命题,随批入册)、ADR-0289(种子回卖判据表:「真发现(策略 bug,待修)」+「种子 ≥2 轮不回卖 0 容忍」设计原文——本批是该设计的生产落地)、ADR-0593 §4.1 L3(D5 检测器机械窗 ≤2 行,窗口同值源)、ADR-0611(§4 P4「相邻轮种子回卖,独立候批」——本批即其落地;L1 同轮硬面辖同轮形态)、ADR-0625(候裁 5 编排者裁决「采(b)维持待 T-126 种子排除统一落地」+§4 m4_fuel 腾席高频消费位过渡窗加重面申报)、ADR-0580(kernel 身份分层单一源架构,cw_card_identity「新身份类只扩本 helper」)、P76 甲(1★ 全额退/退货表)、P41②(燃料资格「与种子线零重叠」维)、P01(再遇窗)

## 1. 背景与归层

**归层**:决策层——卖出资格「排除装配」语义的身份族扩展;非识别/执行/遥测层。

**立项链**:①设计债正本 = ADR-0289 裁定种子回卖为真发现并给出修复动作(「session 记 seed 购入轮,sell 通道加 ≤2 轮种子年龄豁免」),旧 v2 架构从未落地;旧豁免载体 `v2_seed_bought` 随登记写端消亡退役(`flow/session.md` §2.5;`cw_discipline_rules.seed_age_blocked` 结构性恒 False),设计 0 容忍自此无生产承载。②新证据 = 模拟批 findprob_20260910_005622 D5 种子回卖 2 处(开拓者·记忆 p1r8、开拓者·欢愉 p2r7,相邻轮买→卖);T-126 账本附注 2026-09-10T01:11:24「种子件未被卖出通道排除集保护,归排除面缺口家族,统一修须含种子件排除」。③加重面 = ADR-0625 m4_fuel 腾席高频消费位使过渡窗内种子被卖频率结构性上升;编排者 2026-09-10 裁决种子排除归 T-126 统一落地。④同轮形态已由 ADR-0611 L1 fresh_buys 硬面闭合,本批辖**相邻轮残留形态**。

## 2. Considered Options

- **✓ 装配 A 身份族扩展(种子簿第五构件)**:种子身份与 hub 获取名集同构(获取时点记录,保护面只辖实际获取件),经 `sell_exclusions` 单一入口全通道生效——消费位零改(批 2/3 全量迁移的结构红利);新通道/新臂自动继承。备选「逐通道补种子过滤」否决:每通道再同步一次 = T-126 立项时的症状修法,复发第 5 通道手搓形态。
- **✓ 获取时点登记(动态窄集)**:保护面只辖实际获取的引擎件;备选「静态引擎件全集排除」否决:掏空 1★ 燃料资格(方案审 v3 攻击点①同型实证——引擎阵营件含大量合法燃料,静态全集排除会使凑息/腾席在引擎件域空转)。
- **✓ 窗口有界(≤2 轮)而非 τ=∞**:种子的桥建账在位面过渡终结(P2 换血自由 = 发展优先不变量 01_math_framework §8-2 要求);无限保护会阻断 P2 换血与腾席,属安全域内抑制发展动作 = 全架构回炉级违例。2 轮 = ADR-0289 判据表在册裁定值(【注】,非拟合)。
- **✓ 1★ 辖域**:2★/3★ 获取出辖——其往返非净 0(P76 甲 cost≥2 恒 −1)且无 1★ 燃料通道可达,种子振荡机制(免费往返)不存在;归 P41② 主不等式辖。
- **✓ selfcalc 委托收拢**:种子身份谓词此前只在 sim/checks/selfcalc 有一份实现(ADR-0625 候裁 5「生产决策位无可直调单一源」申报缺口);kernel `cw_card_identity.is_engine_piece` 补齐生产单一源后 selfcalc 改委托,消第二实现(判定核同公式,消费方零改)。
- **备选「只落检测器不修行为」否决**:D5 已在役(检测面),行为面真空才是病灶;检测器是回归资产不是修复本身(ADR-0625 §2-② 同判)。

## 3. 已实施架构

- **kernel 身份单一源**:`cw_card_identity.is_engine_piece(name)`——注册表现算(factions∪flows ∩ ENGINE_FACTIONS),与 `cw_line_defs.classify_buy` 的 engine 分支同判据;ENGINE_FACTIONS import 边申报见函数 docstring(迁移挂账「勿新增消费」明示对象 = RECIPE_* 三符号,不含 ENGINE_FACTIONS)。
- **sell_gate 种子簿**:载体 `MandateState.cw4_seed_acquisitions = {名: (位面, 获取轮)}`(duck 属性,`SEED_ACQUISITIONS_ATTR` 契约);常量 `SEED_WINDOW_ROUNDS = 2`【注·在册裁定】;三件套 = `seed_acquisition_eligible`(获取资格谓词单一源:1★ ∧ 引擎件 ∧ 购买时未持有[bench∪deployed 无同名])/`register_seed_acquisition`(写端单一源,同名覆盖,登记计数键 `seed_acquired` 显影——ADR-0625「过渡窗无显影」申报闭合)/`seed_exclusions`(读端单一源,三重闭合:位面闭合[账位面 ≠ 当前位面销,过渡=桥建账终结;P2 换血自由承载]/窗界闭合[当前轮−获取轮>2 销,P78-3 同型有界]/活性闭合[名不在当前 bench 销=件离场机械判];轮号优先消费形参与 active_window 同槽,位面与 bench 黑板帧现读,帧缺 fail-closed 保持保护面,过度禁卖有界)。
- **装配接线**:`sell_exclusions` 在 L1 硬面后并集 `seed_exclusions` **减换线孤儿 carve(P78-2a 线账闭合族)**——本轮义务买入出基座的塌缩清算卖必须照常发射并带 line_switch_collapse 证明标记(ADR-0591 §4 打标制);**垫保同轮转化不让位**(对抗审发现 2 修订,见 §6-R1-②):种子账活跃(无账闭合事件)时同轮经 M4/funding 转化放行卖出 = P78-1 定义性抵消,种子面不 carve `_t3`。全通道(interest/funding/m4_fuel/line_switch/projection)硬禁,无新增通道对价豁免(funding 兜底池 = A∩静态持有集,种子∉静态集结构性不授;P78-5′ 两腿亦不授:窗口内持有账>0)。
- **发射位注册**:`shop._emit_buy` 合成检出分支后(A4 硬闸后,仅活决策登记;合成补齐分支提前 return = 1★ 即刻离场无种子账),`seed_acquisition_eligible` 通过则 `register_seed_acquisition`;全臂统一(D5 种子身份与买因无关;义务基座成员重叠无害)。
- **零开关**:P78-7 结构命题直接落码无条件生效(strategy-work §3 档 1);零新自由参数(窗口 = 在册裁定值;身份 = 注册表现算)。

## 4. 边界申报

- **同位面 pivot 不设全量线账闭合读点**:P1 内过渡配方互切的旧向种子账随 ≤2 轮窗自然过期(过度禁卖有界可判读,P78-3 同型);位面过渡闭合已覆盖 P2 换血主通道;**换线孤儿语境例外** = 本轮义务买入出基座的塌缩清算由孤儿证明集 carve 承载(见已实施架构;初版无此 carve 曾把 seed18 塌缩标记卖堵死——reason_matrix TestLineSwitchOrphanSeed18 红证→修复→绿,锁定与 ADR-0591 打标制的交互为种子面必守边界)。
- **合并产物同名在席**:种子 1★ 三张合成 2★ 后同名(2★)仍在 bench,活性闭合按名判不销账——账自然存活至窗界(≤2 轮),方向 = 保护合成进度,过度禁卖有界无害。
- **作废买入形态**:sim/replay 序列驱动下已发射买入可被引擎作废(ADR-0585 §6 sim 边界同型),种子账由活性闭合在名不在 bench 的下一读点就地销,自愈有界。
- **D5 检测器非对称**:D5 行序窗跨位面紧邻不漏报(检测器过近似,会 flags 位面过渡帧的合法换血卖)——生产闭合语义取线账族(位面过渡),检测器命中归编排者逐案裁决(在册协议);修复后相邻轮命中应结构性归零,即本批回归验证器。
- **买面零触碰**:engine_seed 候选生成/引擎池渐进买进等买面域不动;本批只动卖面排除。
- **P2 内种子账建模对象辖域注(对抗审发现 3)**:ENGINE_FACTIONS = P1 三引擎(四体系封闭裁定),P2 统一桥不存在(stage_transitions Q3)——P2 内非列车同行的 1★ 引擎件获取所开「桥建账」建模对象不存在,属有界过度保护(≤2 轮窗 + 位面闭合兜底);列车同行件等 P2 真实有值件保护正确。候裁件(不阻本批):P2 是否收窄种子登记辖域,候辖域数据背书后裁。
- **显影键**:ADR-0625 候裁 5 的 victim 种子显影在窗口终结后对象结构性清零;`seed_acquired` 计数 + `seed_exclusions` 读面即种子单一源观测位,per-victim 显影不另开。

## 5. 验证

- **新锁族**:`sr-od-test/test/sr_od/app/currency_war/test_cw_sell_seed_gate.py`——获取资格谓词四腿(星/身份/持有/正格)+登记覆盖语义+三重闭合逐腿(位面/窗界/活性)+全通道经装配 A 生效(interest/funding/m4_fuel/projection 视图)+发射位接线结构锁(inspect.getsource,先例 = 统一state R4 锁①f)+selfcalc 委托等价锁+种子簿与发射登记簿载体分离锁。
- **五案回归锁重certify(凭据②)**:`uv run pytest sr-od-test/test/sr_od/app/currency_war/test_cw_sell_arbitration.py test_cw_sell_window_launch.py test_cw_sell_reason_matrix.py test_cw_sell_seed_gate.py -m "not slow and not legacy_baseline"`(树不可测期点名域口径;终态 112 passed = 五案/窗口/矩阵 92 + 本批种子锁 20)。**交互红证与修复在案**:首跑 reason_matrix TestLineSwitchOrphanSeed18 红(种子面无孤儿 carve 把 ADR-0591 塌缩标记卖堵死;HEAD 四文件探针复跑绿 = 红系本批引入非树态既有),按 P78-2a 线账闭合族补孤儿/垫保双 carve 后转绿。一次性观测如实记档:enum 独立锁曾在一次联跑单发红,同命令复跑与单跑均绿未复现,归时序瞬态(树在飞期既有形态,先例 = 文档落位批 9 红归因),非本批确定性引入。
- **L1 点名域全量**:`uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"` = 3277 passed / 2 failed(121.6s);两红(board_state_consume 合泳对账两步/defect_ledger obs 冲突自治)单跑双绿(我方版本在场),失败仅现于全集顺序态,域属在飞 W2/统一state 面,非本批引入(归因探针在案)。
- **变异自检**:①种子并集行摘除 ⇒ 通道覆盖锁红(实证);②窗界常数 2→3 ⇒ 窗界闭合锁红(实证);③**守卫移除验证(R1-① 生产序锁有牙证明)**:bench 轴退回单读 last_state(初版缺陷形态)⇒ `test_production_order_stale_entry_frame_keeps_fresh_seed` 红(实证,逆替换还原后 23 绿);④通道覆盖锁自含红证(无 A 时种子穿过燃料物理谓词直调实证)。
- **R1 修订后终态(2026-09-11)**:种子锁 23 passed(20→23:+生产序锁/双帧闭合锁/plane 拒收锁,垫保腿按 R1-② 翻转);四文件套 **115 passed**(五案/窗口/矩阵 92 + 种子 23);ruff 5 文件全绿;L1 点名域 3281 passed / 1 failed——红 = `test_bucket_dependency_matrix`,违规边 `sim->knowledge: sim.checks.t190_c:110` 系**他批未跟踪在飞文件**(`?? t190_c.py`,T-190 面)所致,本批四文件零新桶边(sim→kernel 委托边合法),归因在案。
- **文档三同步**:本 ADR + INDEX 行 + ADR-0585 Status 增注(批 5 指针)+ 11_shop_decisions §4.1 as-built 种子语义行 + math_proofs P78 行(P78-7+批 5 状态,随批入册)。

## 6. 修订记录(对抗审 R1;2026-09-11)

审 = 编排者派无前提对抗审(结论 = `.debug/progress/2026-09-06-currency-war-redesign/reviews/T-126-批5-对抗审.md`:阻断 1/中 1/低 2),四条全处置:

- **R1-①(阻断)活性闭合生产销账 hole**:生产 last_state = 商店段入口快照(`cw_op_buy_cards:781`,店内段滞后),初版单读该帧使新鲜种子账在获取 visit 内被逐帧 P56 投影读就地销毁——相邻轮保护生产整面失效,且 sim 只写 shop_state_frame 恰好免疫(sim D5 归零假绿)、锁面搭现读一致视图三重不可见。修法 = **bench 轴双帧并集**(任一帧见名在席即在席,双侧证据皆缺才销;plane/round 轴保持 last_state 优先——段入口粒度对段内不变量恒安全),兼封 prep 语境 shop 投影帧滞留的反方向滞后;**生产序锁**新增(`test_production_order_stale_entry_frame_keeps_fresh_seed`,滞后帧形态钉死)+双帧闭合锁+守卫移除红证(bench 轴退回单读 last_state ⇒ 生产序锁红,实证)。顺带复核:ADR-0611 §3-1 C2「生产逐帧写点」表述实为混合粒度(shop=段入口/prep=帧级)——L1 相位轴(轮/位面,段内不变量)功能不受影响,表述勘误候路由 ADR-0611 面(非本批文件)。
- **R1-②(中)垫保×种子同轮开同轮销**:fuel_filler_stall 候选谓词放行线外引擎件(zero_overlap 只对线成员)→ stall_protect∩种子重叠可达同轮转化卖出(初版 _t3 carve 放行),检测网双盲(D5 窗口 gap≥1+同轮检查器 convert 键豁免)。修法(按审给两候选取数学裁决)= **撤种子面 _t3 carve**:种子账活跃(无账闭合事件)时同轮转化卖出 = P78-1 定义性抵消(对兜底豁免同样构成上界;P78-5′ 对价腿「确定可用且可达成」不成立——桥建账同帧作废、退款净 0 不达成任何账,无损腿亦不成立);换线孤儿 carve 保留(其账已按 P78-2a 线账闭合,清仓非抵消)。**张力申报**:「全臂统一/买因无关」下,垫保臂买入的引擎件同受种子保护、其「垫件牺牲」转化角色对种子成员失效(候选池实际收窄;诚实停摆桶 `*_no_fuel` 承载);候裁件 = 引擎件是否豁免于垫保买臂候选(买面收窄,归买面批,本批不夹带)。
- **R1-③(低)P2 辖域注**:见 §4「P2 内种子账建模对象辖域注」。
- **R1-④(低)plane=None 登记拒收**:fail-closed 一行收口(窗界算术跨位面双向失真防患,与 hold 类缺读拒纪律一致),锁 `test_register_rejects_plane_none`。
- 修复后全量复跑:种子锁 23 passed(20→23:+生产序锁+双帧闭合锁+plane 拒收锁,垫保腿翻转);四文件套与 L1 见 §5 终态更新。
