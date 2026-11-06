# hp-purge-refresh-reform 第 5 轮对抗审查报告（无前提 · 三核并重）

- 审查日期：2026-10-28
- 审查者：干净上下文攻击者（仅持对象清单 + 判据源清单，未读 r1-r4 报告）
- 审查对象：design.md、details/hp-purge.md、details/refresh-chain.md、details/shop-buy-reform.md、landing.md（hp-purge-appendix.md 未生成，不在对象内）
- 代码基线：HEAD = cf34d0afa（设计引用锚全部按现值直调核验；清查件基线 a42f1e2 与现值的符号/行号漂移已逐锚对账，主体无漂移，个别行号偏差见 B2/B8）
- 判据源：iteration-design.md 全篇、裁定载体「用户裁定」节 1-7 条（直读）、hp 清查件 / 追查件 / 复盘件（直读抽核）、strategy-docs 九篇被引行（直调）、math_proofs P21/P36/P40/P54/P86/P92 行（直调）、现役代码约 60 个 file:line 锚（逐锚直调）、测试面 8 个锚（直调）、sim-testing/strategy-work 被引节（直调）、两处外部 changes 声明（直调）

## 结论

**总纲方向与三核立场成立（治本核通过、无高严重度阻断），但「凭这份直接开工」会在 3.1/3.2/3.3 各撞到至少一处需要回炉修订的契约/口径缺口**——6 项中严重度（文件面契约切函数、W5 未锁窗口口径不闭合、删除面跨文件残留无人认领、R-4~R-9 合法性链与执行规则缺口、总纲契约面与 landing 失同步、prereg 载体指针幻影），8 项低严重度（表述矛盾/接口未钉死/引用寿命/过程叙事残留）。修订面均为局部精度修正，不动方案主体。

严重度分布：**高 0 / 中 6 / 低 8，共 14 条**。

---

## 发现清单

### A1【中】shop.py 行段三分边界切在函数体内，carve-out 不覆盖实际改动面

- 位置：design.md:46；refresh-chain.md:5/:21/:30；shop-buy-reform.md:5；shop.py:234-264、:267-315
- 发现：
  1. 三分界线 `:249` 横穿 `_merge_pair_names`（def shop.py:234，函数体至 :264）。refresh-chain.md:21 要求「合成腿谓词按机制全集定义（shop.py:234 段重写，refresh-chain 文件面）」——重写必然触碰 :250-264，该段落在 shop-buy-reform 独占段（design.md:46「shop.py:250-1961 → shop-buy-reform」），而 carve-out 清单（design.md:46 只列 :373/:996/:327/:267）未含该函数。refresh-chain.md:5 自述头部段「≈L1-249，含 ρ 别名与合成腿谓词」与总纲行级互斥契约（「各详设不得触碰对方文件面」）直接冲突。
  2. `p92_seat_recoverable` 的 carve-out 只写「shop.py:267（p92_seat_recoverable 定义）」单行（design.md:46），refresh-chain.md:30 的处置是「符号删除（唯一消费位随装配段）」——删除需动 :267-315 整函数（49 行，均在 buy 段），单行授权不覆盖。
- 后果：3.2 实现第 1 天按契约字面执行即违反文件面互斥；不做字面执行则撞停手令回炉。
- 修正方向：三分边界改按语义段（如头部段 = shop.py:1-315 归 refresh-chain，buy 段起点改 :316），或 carve-out 显式扩为「:234-264（_merge_pair_names 整函数）与 :267-315（p92_seat_recoverable 整函数）」，design.md §2.1 与 landing 3.2/3.3 文件面同步。

### A2【中】W5 星级口径与未锁窗口缺件源不闭合

- 位置：shop-buy-reform.md:17-18；levelup.py:193-194（unfinished_star_targets 未锁期恒返回空集）；shop.py:930
- 发现：shop-buy-reform.md:17「缺件集/买臂推导改消费 unfinished_star_targets（修 shop.py:930 名集星级盲）；`_dg_gap`/`missing` 推导域同步换口径」——unfinished_star_targets 在未锁窗口恒为空（levelup.py:193-194 `if not view.locked: return []`），字面执行会把未锁窗口的义务面缺件集清空，未锁窗口 M2 首副本买进（现役行为，追查件 §1.1「M2 缺件未进店静默跳过」所在机制）随之死亡。而 :18 行为变化申报只覆盖锁定场景（三月七 2★ 达标停买 / 姬子 2★ 追 3★ 全配置可达），未申报也未声明未锁窗口的缺件源保留方式（missing（名集）与星级缺口双源合并？还是扩展 unfinished_star_targets 适用域？）。
- 修正方向：钉死推导——未锁窗口沿用名集 missing（首副本语义），锁定后叠加 unfinished_star_targets 星级缺口维；或声明 unfinished_star_targets 扩展适用域。补一条「未锁窗口 M2 首副本照买」回归测试进 3.3 完成判据。

### A3【中】删除面跨文件残留级联无人认领（裁定 #3「注释同步清/孤儿删」违反面）

- 位置：hp-purge.md:26/:34/:49；landing.md:9（扫描范围 = 本阶段文件面）；design.md:49（3.1 文件面）
- 发现（全部经现值直调核实）：
  1. **B-8/B-17 家族**：`effective_hp_threshold`/`HP_SAFE_THRESHOLD`/`DIFFICULTY_HP_TABLE` 删除后，文件面外的注释/登记残留至少 9 处：kernel/cw_entry_policy.py:15、obs/cw_observation.py:956/:968-971/:2739、operations/cw_entry/cw_entry_start.py:359、operations/cw_loop.py:770、operations/cw_screen/cw_screen_prep.py:770/:1174、strategies/impl/cw_strategy.py:445-446、currency_war_config.py:37-38。这些文件均不在 3.1 文件面（kernel 枚举未含 cw_entry_policy.py；obs/operations/config/strategies 层完全未列）。
  2. **B-6 家族**：`decision_hp` 删除（词表含此符号）后，上述 obs/operations/cw_strategy 注释残留同批悬空（功能调用面确已清零：唯一生产调用 = cw_comps.py:2921（maybe_pivot，随 A-7 删），cw_economy.py:1086-1087（is_emergency，随 A-9 删）——孤儿化判定本身成立）。
  3. **B-14 家族**：mandate_state.py:123-124 删除后，telemetry/schema.py:460-465（`sess_blood_budget_rejects`/`sess_blood_budget_refresh_rejects` 字段——注释自述「透传源 = strategy_state_of(session).v3_blood_budget_rejects」，透传源即被删字段）与 kernel/cw_decision_trace.py:129-130（披露族封闭清单成员，自注「封闭清单禁散落第二登记」）成孤儿；schema.py 在 3.1 文件面只分到 :488-489，cw_decision_trace.py 不在任何阶段文件面。
  4. **同族**：telemetry/schema.py:513-515 `posture_unfulfilled` 注释内 `action=allocator/crisis_release/downgrade` 的 `crisis_release` 值 = 危机金出口停用机制残留，不在 3.1（:488-489）/3.2（:500）任一行段。
  5. **词表缺口**：hp-purge.md:49 清零词表缺 `effective_hp_threshold` 与 `HP_SAFE_THRESHOLD` 两符号（B-8/B-17 的删除对象本身不在验收词表）；且阶段扫描范围 =「本篇文件面」（landing.md:9）→ 上述全部命中在阶段验收漏网，末阶段宽词盘点才暴露为计划外「漏删申报」。
- 修正方向：二选一并全量同步——①3.1 文件面补列上述行（cw_entry_policy.py:15、cw_observation.py 4 处、operations 4 处、cw_strategy.py:445-446、currency_war_config.py:37-38、schema.py:460-465、cw_decision_trace.py:129-130、schema.py:513-515）；②扫描范围改为「词表对 src/ + sr-od-test/ 全量扫描，命中即清零（豁免申报）」；词表补 `effective_hp_threshold|HP_SAFE_THRESHOLD`。

### A4【中】R-4~R-9 处置的合法性链与 hp-purge 执行规则缺口

- 位置：design.md:10/:63/:69-71；hp-purge.md:26；裁定载体「用户裁定」节（仅 1-7 条）
- 发现：
  1. design.md:63 标题声明「已裁决：**两项**均按推荐方案通过」= R-1/R-3；但 §3 表同时给出 R-4/R-7、R-5、R-6/R-8/R-9 的处置。裁定载体 7 条裁定不含 R-4~R-9（载体裁决队列将其列为「W1 动工前须闭合」事项，无裁决记录）。R-5 可从裁定 #3 推导但该行未标依据；R-4/R-7、R-6/R-8/R-9 行完全无依据标注（写作硬规则 1）；R-4/R-7 行为「均保留」的合法性（按裁定 #1「hp 是结果」推导观测面合法）未写出。
  2. design.md:70「经对抗审确认」= 过程叙事（写作硬规则 3，见 B7）。
  3. R-6「cw_first_passage 保留」（design.md:71）与 hp-purge.md:26 执行规则三态冲突：A-7/B-8 删除后该模块功能消费面清零（现值直调：唯一功能 import = cw_economy.py:227 在 effective_hp_threshold 体内；cw_line_switch/plane_table/registry/run_allocator 命中均为注释关系描述）→ 按规则①属「零消费孤儿 → 直接删」。保留的依据（概率侧标定工件、早期「hp 入概率路由键合法」裁定）在设计正文零标注；且该保留与 hp-purge 关键取舍对 A-7/A-8 的弃案理由（「保留待后续启用 = 垃圾代码」hp-purge.md:64）表面同构、未作区分声明。实现者按 §2 三态走会误删 203 行模块，按 §3 走则保留——两条路径分叉未闭合。
  4. design.md:71「λ 表血带维随 hp 删除面孤儿化申报」与 R-7 保留裁定自相矛盾：R-7 保留 p1/p2_blood_floor 谓词（predicates.py:125-185，hp-purge 文件面内不动）→ lambda_death.py 的血带锚仍被 predicates/entry.py:583-586 观测分键消费，非孤儿。该格按清查件 R-6 原文照抄（「现无决策消费」）但未按 R-7 处置结果更新口径。
- 修正方向：§3 每行补合法性来源（裁定编号 / 清查件 R 节推导链）；hp-purge §2 为 B-9/B-12 增设第④态「概率侧标定工件保留（依据 = 概率路由键合法裁定，非行为逻辑，与 A-7 未证行为代码区分）」；R-6 格改述为「cw_first_passage 保留（概率侧工件）；λ 血带维保留（观测分键消费仍在，非孤儿）」。

### A5【中】总纲 §2.1 跨详设契约面与 landing/详设失同步（修订后全量同步复查未闭合）

- 位置：design.md:49；landing.md:29/:43；refresh-chain.md:30；hp-purge.md:26
- 发现：
  1. design.md:49 的 3.2 contracts.py 行清单漏 `:283`（all_channel_buy_exists 契约行）与 `:288-291`（qualified_member_costs 契约行）——refresh-chain.md:30 与 landing.md:43 均已列出。总纲自定位 = 跨详设接口契约是「唯一必须在总纲定死的深度内容」，行级互斥以总纲为准时会漏授权两处必动行。
  2. **cw_investments.py 三方归属冲突**：design.md:49 把 :1216 `blood_xp_mode` 行列为 3.1 carve-out（「R-1 币种通式联动，改类条目」）；landing.md:29（3.1 文件面）完全没有 cw_investments.py，landing.md:43（3.2 文件面）才以「cw_investments.py（如免费分支需效果侧配合）」整文件出现；hp-purge.md:26 的 B 组「连带面触碰文件收编清单」也漏 cw_investments.py（B-19 的锚文件恰是它）。R-1 的 :1216 联动核按 landing 3.1 文件面开工即越权/无授权。且「改类条目」未写明改动内容：现值直调 :1216-1233 为函数（非类条目），R-1 行为零变化，实际义务 = docstring :1220「[40]② 血闸与遥测写点经本助手同源消费」措辞随 R-1 改名清理——设计应写明到这个粒度。
- 修正方向：总纲补 :283/:288-291；cw_investments.py:1216 统一归 3.1（landing 3.1 文件面补行）并写明改动 = docstring 血闸措辞随 R-1 清理；hp-purge §2 收编清单补该文件。

### A6【中】prereg 硬门四指标载体指针幻影

- 位置：design.md:61；landing.md:18
- 发现：「sim 四指标（位面 1 出口金/过渡凑齐率/终局金/终局阵容完成率，**sim-testing §一**）」——sim-testing.md 现值无「§一」节，也无四指标清单（首节 = 「先知道边界」；全篇节 = 先知道边界/种子段分配纪律/批驱动器 monkeypatch 规约/单局复盘素材采集）。四指标实际载体 = `strategy-docs/11_shop_decisions.md:186` 基线行（四个指标名逐一对得上，design 同一行也引了它）。prereg 完整性硬门的验收线载体指针失效，落地批 3.4 按指针取数会落空。
- 修正方向：指针改为 `11_shop_decisions.md:186`（或 skill 内真实小节），design.md:61 与 landing.md:18 两处同步。

### B1【低】「已知余量」白刷表述与自身终态语义矛盾

- 位置：refresh-chain.md:31；对照 refresh-chain.md:16-19/:26 与 landing.md:49
- 发现：「极端死态（席满+零燃料+不可合成）白刷到金线」——在终选条件集下该态目标可买 = False → 付费刷（合取拒）与免费刷（目标可买检查拒）均不发射，「白刷」不可能发生；3.2 单帧测试④锁的恰是「拒（关店）」。该句系从裁定 #7 载体原文照抄（载体语境的腾位腿含「场上非线内件」），席位腿收窄（refresh-chain.md:24/:26）后未重推余量形态。真实余量形态 = 「金滞留至关店-腾位-重进链」（:26 已写）。
- 修正方向：改述余量 = 「极端死态下刷新持续被拒（target_unbuyable），金经关店腾位链释放；压牌库让位（shop-buy-reform §2）落地后该态几乎不可构造」。

### B2【低】shop.py:996「视界消费」定性失实；:373 docstring「直传」既有漂移未点名

- 位置：hp-purge.md:34；design.md:46；shop.py:373/:476/:996
- 发现：现值直调——shop.py:996 调 `shop_unbought_reasons` 传 `hub_names=frozenset()`（常量空集），不消费 H（全仓唯一调用点即此处）；「shop.py:373/:996 消费行随新 H 输出值语义重算」与「3.1 回归测试锁两消费位等值」对 :996 为空义务。同时 :373 docstring 自述「入参 = kernel.no_target_arms().hub_names 直传」与调用实况（传空集）本就不符——设计按「视界消费」两行处理，未识别这是文档-代码既有漂移。
- 修正方向：carve-out 收窄为 :373 注释行；:373 语义修正（「直传」改为如实申报「现调用点传空集，hub_option 键现役不触发」）；删去 :996 的等值测试义务。

### B3【低】W4 窗口否决项的求值时点未钉死

- 位置：shop-buy-reform.md:22-23；shop.py:1543（M6 位）vs :1974-1977（刷新判据位）
- 发现：M6 在六序（步 5）触发，刷新判据在步 6 求值；六序买/卖改变 bench 与持有 → `refresh_warranted` 帧内不同时点求值可不同真。「消费 refresh_warranted 现值，同帧同参——禁第二推导」未指明取帧首现值还是 M6 位现值（两者对窗口判定可给出不同答案，进而影响 M6 让位的帧集）。
- 修正方向：钉死 = M6 位现值现算（同参 = 该时点 bench/deployed 现读），或帧首一次性求值传递；任选其一并写入 shop-buy-reform §2。

### B4【低】目标可买席位腿的装配参数流未钉死

- 位置：refresh-chain.md:29/:64；shop.py:300-314（现行同参装配：sell_exclusions + dead_pair_exit_release + counters/dedup_names）
- 发现：「fuel_sell_candidates（现役单一源，本篇复用同参装配，禁第二实现）」+ §5 伪码保持 `refresh_warranted(gs, session)` 两参签名。同参装配所需的 counters、merge_guard 帧级 dedup（shop.py:963 `_mm_dedup`，帧级共享载体）、cap_hold、defer_names（_t3_protect）在两参签名内无来源——refresh_warranted 体内自取（经 state_of(session).cw4_counters 等）与调用侧装配后传参（扩签名）两条路均可，设计未择一；dedup 共享语义（merge_material_guard 事件「每帧每素材至多 1」跨消费位合并）取决于所选路径。
- 修正方向：择一写明（建议 = 判据扩参，装配仍在调用侧，保持 dedup/counters 帧级共享现状）。

### B5【低】ρ 取值口径双读：注册表基价 vs stay_target_of 实费档

- 位置：refresh-chain.md:40；裁定 #6（「注册表卡价」）；levelup.py:181-183/:202/:210-213；refresh.py:101
- 发现：「改为 stay_target_of(state) 的 CHARACTERS cost」两读——按字面取 `CHARACTERS[name].cost` 基价，或取 stay_target_of 返回元组的 t[2]（= `effective_cost` 变费后实档，银狼系变费帧两者分叉）。判据带归属用 t[2]（refresh.py:101 `prob_band_of_cost(target[2])`）；若 ρ 取基价，变费帧 ρ 与判据目标带不同源，违反设计自身的「ρ 与判据共用同一目标、禁第二推导」。
- 修正方向：钉死 ρ = stay_target_of 返回元组的实费档（t[2]），并注明与裁定 #6「注册表卡价」的口径关系（注册表 cost 的 resolved 实付档）。

### B6【低】资金序收敛论证的权威锚落在另一迭代 changes/ 件上（引用寿命）

- 位置：design.md:36；refresh-chain.md:42；AGENTS.md「双层文档流」铁律；iteration-design.md §1 引用寿命分层
- 发现：「资金线推迟态 = 攒金收敛态（金上涨吃息，2026-10-18 声明域 changes/2026-10-18-levelup-band-gate/design.md:156）」——该锚是 load-bearing（支撑「必收敛、非死锁」核心声明），而 changes/ 会不定期删减、跨迭代引用寿命不受保障；追查件 §3 与 W8.1 自身裁定「changes/ 只作勘误线索」。收敛论证应锚正本或机制本身。
- 修正方向：论证改为自足（每轮节点收入 > 0 ∧ 利息线内金单调上涨 → 凑金可达域收敛到发射；依据 = 11_shop_decisions §2.1 资金线门行 + 01_math_framework 金流公理），changes 件降为勘误线索注。

### B7【低】写作硬规则违反：过程叙事残留（iteration-design §5-3）

- 位置：hp-purge.md:63；design.md:70
- 发现：hp-purge.md:63「曾两度反复（第一版推荐 → 「整条退役」→ 回定本口径）」= 上稿修订史（卡点：「本轮/修订后/已改」类措辞即打回）；design.md:70「（shop-buy-reform §1，**经对抗审确认**）」= 审查过程指称。过程住对抗报告，不进设计正文。
- 修正方向：删修订史句，保留技术理由（k_empty_window_fallback 三处生产消费位 + P1 空窗防环职责）；W5 行删「经对抗审确认」。

### B8【低】R-3 删除面含 phantom 改码义务：contracts.py:88-106/:166-171「p2plus 支随新 H」

- 位置：hp-purge.md:34；design.md:49；landing.md:29；contracts.py:79-106/:134-171
- 发现：该两处（_s_reserve_line_formed / _k_projection_domain_full）现值直调不读 H——p2plus 合法性判据消费的是三分支评估产出的 k_fallback_* 字段与 K_FALLBACK_SOURCE_THREE_ARM 常量，H 语义变更发生在上游 cw_intention（p2_supply_horizon→line_completion_feasibility），contracts 守卫代码零改动需求。设计把该两处列入 R-3「删除/改口径面」+ 3.1 文件面，落地批会撞「无可改之物」的停手令边界；且「p2plus 支随新 H」字面可误读为删除指令（同段虽有「K_FALLBACK_SOURCE_THREE_ARM 常量保留」互证）。
- 修正方向：改述为「contracts.py:88-106/:166-171 无码改；仅末阶段随 P86 重锚核对其 docstring 的 P86 引用表述」。

---

## 已核验为正的面（零发现，逐项直调）

1. **代码锚主体真值**：shop.py 全文件 2080 行属实；三分段语义边界（:1962 刷新段起、:2079 收工）属实；free_refresh :1963-1971、GATE_GOLD_SHORT :1988-1989、r2_budget :1994、P92 装配 :1996-2054、must_spend_r1_budget_fail :2067（保留侧）逐行属实；p92_seat_recoverable :267、_r2_card_reserve :221、_merge_pair_names :234（docstring 误杀警示 :240-247 属实）、refresh_ev_budget 注释 :327、missing 名集 :930、m2_stockpile 门 :1277-1279、M6 :1543-1616、单动作契约/位次 :770-795 全部属实。
2. **refresh.py/levelup.py/mandate.py 锚**：r0_stop :22、r1_start :140、crisis_refresh_invariant :160、r2_card_reserve :236、all_channel_buy_exists :282-378、r1_commitment_account 注释 :301、r1_start「禁复活」自注属实；levelup 门④ :370-377、门⑥ :385-392、level_spend_blocked :484-514、门序 docstring :300-306、unfinished_star_targets :174、stay_target_of :206、追查件锚 :269-277 属实；mandate fuel_sell_candidates :392（bench-only 属实）、crisis :4/:1078-1079、level_spend_blocked 残留 :963/:996 属实。
3. **kernel 锚**：cw_discipline_rules :82-128/:131-151/:154-209/:212-260 属实；cw_intention p2_supply_horizon :1067-1094、G 门 :1099-1150、arm_a_*/no_target_arms/hoard_target_set :1427-1530、k_empty_window_fallback :1576、LOCK_PATH_OBS_KEY_PREFIXES :1163-1171、neardeath_direction_obs_ 仅注册行 :1166（src 全仓零发射属实）、候选-锁定制停用史 :1180-1181 属实；cw_economy is_emergency :1074-1088、refresh_ev_budget :1237-1287（归零支 :1275-1276）、blood_xp_gate 族 :792-882、B 组各行属实；cw_comps maybe_pivot :2862-3102、PIVOT :2852-2859、import :37、注释 :125 属实；cw_performance is_run_dead :244-269、cw_hp_policy :20、cw_game_state hp_floor_triggered :2954、cw_vocab :64-69、cw_registry B-2/B-3/B-5/B-6 各行属实；economy_cycle :12/:14/:29-30/:177/:187（3.1）与 :24/:233（3.2）属实；odds.py:67、cw_investments 高效决策 :473 属实；entry.py:480 部署围栏、decision_payload.py:101、shop_session.py:109 属实。
4. **contracts/__init__ 行级分工**：contracts :243-246（level_spend_blocked 契约）、:88-106/:100-106/:166-171（p2plus 守卫）、:138-142（P1 空窗防环）、:252/:255/:261-267/:273/:279-282/:283 属实；__init__ :54-55/:60/:62/:65/:71-73/:76 属实。
5. **词表互斥性**：`decision_hp` 清零不误伤保留的 `hp_decision_trusted(_of)`（无子串碰撞）；不过扫清单（refresh_ev_budget/p1_blood_floor/p2_blood_floor/p2_handoff_）与 R-7/保留裁定、A-9「删归零支非删函数」口径一致；`p2_crisis`/`blood_budget` 现值命中全部落在删除面或文件面内。
6. **行为接口契约与代码实况吻合**：升级触发态与刷新放行态互斥（裁定 #5 死代码推导）经三分派代码核实成立（gold_short 仅在升级触发帧产生，该帧刷新 ①支必拒）；「未锁分支 stay_target 恒空 → ρ=0、锁定支 ρ 恒有值（目标空帧判据先拒）」与 levelup.py:193-194/refresh.py:98-100 完全一致；裁定 #7 席位腿收窄（卖场上件不释放备战席位）与 merge_mechanics §1 落点规则（先备战）一致；资金序「①支维持拒绝」与现行 refresh.py:102-105 结构一致（删除面 = 不加支，无行为面风险）。
7. **测试面锚**：test_seat_recoverable_narrow.py（存在，实锁 p92_seat_recoverable）、sim/test_sim_levelup_cycle.py:44（_REFRESH_REJECT_KEYS 含 p92 键，路径在 sim/ 子目录）、test_decision_payload.py:10/:158/:169、test_line_select.py:358-360、test_no_target_three_arms.py（五类锁 P86 三分支/回退带）、E 组锚（test_levelup_prob_axis :310-317、test_shop_session_loop :658-679、kernel/test_economy :876-890）全部真实存在且语义如设计所述；LOCK_PATH 键族测试侧零覆盖（设计声明属实——cw_intention.py:1160 注释声称的守卫测试不存在，属既有代码注释漂移，设计判断正确）。
8. **证据/裁定文件转述**：hp 清查件 A/B/C/D/E 组结构、A-9 交叉复核（追查件 §7 零行为差 + hp=1 刷新回执直证）、追查件 §1.2 r2 帧/§1.4/缺陷 #2/#3、11_shop_decisions.md:186 批读数（15/15、85/85、中位 105）、:58 [40]② 定性、:110 P92 段、23_shop_screen.md:10 三合一漂移行、01_math_framework.md:194 钩子行、10_prep_decisions.md:199、p37:188、math_proofs P21/P36/P40/P54/P86/P92 行、p36 单篇存在、2026-10-18 design.md:156 声明域、merge_mechanics（docs/game/currency_war/research/ 下，§2 连锁合成属实）、cw_shop_odds REFRESH_PROB :47-58、supply-decision-wiring 迭代目录存在——设计对裁定与证据的转述与原件一致，未发现二手失真。
9. **landing 七件与依赖序**：3.1-3.4 + 末阶段七件齐；依赖链 3.1→3.2→3.3→3.4→末阶段无环、判据可验收；正本更新清单声明「单一源 = 清查件快照、下表为归并索引」——D 组条目覆盖机制成立（清查件 B 组编号 §1/§2.2 错位已被 hp-purge §7 预申报）。
10. **skill 引用**：strategy-work §1（未证即停用/零调参 :16/:23/:39）、§3（无开关 :34/:38）、§4（锚点事前 :53）、§6（prereg :48-49/:81）与 sim-testing「先知道边界」末条（A/B 挂起 :17）、「单局复盘素材采集」节（cw_sim_match_drive :32-38）均真实存在；cw_sim_match_drive 符号在 src 可解析。

**如实申报（非发现）**：追查件 W10 引用的 `test_cw_interest_floor.py` 在测试仓不存在（`r2_card_reserve` 测试引用全仓为零）——设计未继承该死锚（shop.py:227 docstring 的同款死引用落在 ρ 重写段内随改消失），不构成设计的错误；shop.py:1981 注释「ρ〔合格集最低费卡价〕」旧口径描述在整级预留支删除的重写范围内自然消除。
