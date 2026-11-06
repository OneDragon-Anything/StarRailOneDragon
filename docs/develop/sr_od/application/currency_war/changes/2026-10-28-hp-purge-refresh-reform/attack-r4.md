# 第 4 轮无前提对抗审查（hp-purge-refresh-reform）

- 审查人立场：干净上下文攻击者，只带对象清单与判据源，无预设焦点；未读 attack-r1/r2/r3。
- 审查对象：design.md、details/hp-purge.md、details/refresh-chain.md、details/shop-buy-reform.md、landing.md（details/hp-purge-appendix.md 未生成，不属对象）。
- 方法：五篇全量通读；判据源逐项直调（iteration-design.md、strategy-docs 被引行、math_proofs/proofs 行、现役代码逐锚、清查件/追查件/复盘件抽核、工作清单裁定节、sr-od-test 测试面、merge_mechanics/economy 研究篇、2026-10-18 与 2026-10-28 两处边界件）；代码基线以本仓现值直读为准。
- 结论：**发现 14 条**（高 2 / 中 6 / 低 6）。核心集中在 hp-purge §6 验收词表与删除面双向不匹配、目标可买合成腿真值源窄化、残留扫描口径与裁定申报不一致三处。

## 发现清单

### 高

**H-1 验收词表与删除面双向失真（过度捕获 + 漏捕获）**
- 位置：`details/hp-purge.md:49`（§6 词表）
- 过度捕获三类：
  1. `p1_blood_floor` 入清零词表，但裁定 R-7（design.md §3）明确 p1/p2_blood_floor **保留为纯观测**——定义在 `statefn/predicates.py:125/:156`，现役观测消费在 `strategies/impl/mandate_v1/entry.py:583-584`（terminal_targetless_idle 纯计数，清查件 C-11 同判）。statefn/predicates.py 在 3.1 文件面，按词表扫描该符号永不归零（完成判据不可满足）或逼删保留面。
  2. 裸前缀 `handoff_` 误覆盖保留面：`cw_intention.py:1167` `'p2_handoff_'`（LOCK_PATH 键族，hp-purge.md §3 自declared 保留）、telemetry handoff 承接快照（`telemetry/schema.py:447`，清查件 C-7 保留）、`data/cw_battle_tables.py:144` handoff 深度分桶采样数据、`mandate_state.py:127-128` v3_handoff/v3_handoff_plane 观测载体（清查件 B-15 只删 :174 hp 维投影一项）。前四者均在 3.1 文件面或其扫描半径内。
  3. `refresh_ev_budget` 入清零词表，但清查件 A-9 处置 = **删应急归零支（:1275-1276）非删函数**——B-16 标量投影支（cw_economy.py:953-1000，设计明言「随 A-9 收窄」保留）与 `test_economy.py:77/:647` 合法 0 帧契约测试组均消费该函数本体。整函数删除违反执行单一源并连带破坏 B-16 保留路径与既有测试。
- 漏捕获（清查件明列删除、词表缺失）：`p1/p2_levelup_stop_hp`（B-1）、`decision_hp`（B-6 删半）、`DIFFICULTY_HP_TABLE`（B-8/B-17）、`HP_QUALITY_ALARM/HP_DISTRESS_FRAC`（B-10）、`form_floor/p1_exit_blood_target`（B-2 零消费孤儿）、`p1_levelup_stop_rung`、k 线性族 `k_linear/k_hp_calibration_grid/blood_margin_low_hp/boss_tax_p75_by_plane`（B-5/明细 B-6）。这些符号被删后的残留不受「符号级残留清零 = 完成必要条件」约束。
- 修正方向：词表按「本篇实际删除符号全集」重造（A 组符号 + B 组逐条被删符号），剔除 `p1_blood_floor`、裸 `handoff_`、`refresh_ev_budget`（保留面符号改用「diff 核对无 hp 读取」口径，同 p2_supply_horizon 行先例），并补「保留-改口径符号」清单（decision_hp 若删本体、blood_xp_mode 改名面等）。

**H-2 目标可买合成腿真值源窄化，与腿语义、裁定 #7 字面、merge 机制主例三方不符**
- 位置：`details/refresh-chain.md:17`（合成腿定义）、`:26`（指定消费 `_merge_pair_names`）；`design.md:33`（总纲同式）
- 设计指定合成腿真值源 = `shop.py:234 _merge_pair_names`，该谓词口径 = **全局面（bench∪deployed）同名副本恰 2 张 ∧ 全 1★**（:256-264）。三类失配：
  1. 「场上 2★ 成员 + 备战 1★×2」帧：merge_mechanics.md §2 主例与连锁例（:17-18）明载买第三张 1★ 触发合成、净释放席位——裁定 #7「已持 2 张买第 3 张直接合成」字面成立，谓词却因副本计数含场上 2★（恰 2 张不成立）返回 False。该帧正是 ρ 改口径与 W5「未达标成员副本照买」语义批量制造出的常见形态（2★ 追 3★ 攒 1★ 对）。
  2. 「备战 2×2★ + 商店 2★ 直出」帧：merge_mechanics.md §2.5 连升例与 §2.6（2星直出已实测确认）下同属裁定字面「已持 2 张买第 3 张直接合成」，设计未覆盖（现行机器只在 m2_stockpile 有 spot2 直出支，shop.py:1282-1288，不在指定真值源内）。
  3. `_merge_pair_names` docstring 自身（shop.py:240-247）已申报该谓词 = 机器口径非机制全集、「作门将从对齐机器翻成误杀真通道」——设计在已读该警示的情况下仍指定其为目标可买真值源且未申报残余。
- 后果：「追星误拦缺陷顺带消除」（refresh-chain.md:27）申报过强——席满帧的可合成判别仍沿旧机器窄口径误拦；「已知余量」（:28）仅申报了「席满+零燃料+不可合成」态，未含「席满+可合成但谓词判不出」态。
- 修正方向：合成腿真值源改为按 merge_mechanics.md §1/§2 机制口径直算（同名 1★ 副本计数 ≥2 即第三张可触发合成，含连锁面；2★ 对 + 2★ 直出卡第二腿如实声明覆盖或申报为余量），或在详设显式申报窄口径残余及其与裁定字面的偏差交用户确认；同步修 refresh-chain §1 已知余量段与单帧测试 ③ 的场景定义。

### 中

**M-1 残留扫描口径与总纲申报的裁定 #3 验收口径不一致，跨文件面孤儿无人认领**
- 位置：`design.md:9`（「全仓残留扫描清零为验收门槛」）vs `landing.md:9`（扫描范围 = 本阶段文件面；末阶段只扫 docs/）
- 无任何阶段执行 src+tests+docs 全仓扫描；跨面死引用实证存在：effective_hp_threshold/HP_SAFE_THRESHOLD 连根删（清查件 B-8/B-17）后的注释面 `obs/cw_observation.py:956/:968/:971`、`kernel/cw_entry_policy.py:15`、`operations/cw_loop.py:770`、`operations/cw_entry/cw_entry_start.py:359`、`strategies/impl/cw_strategy_manager.py:62`、`src/sr_od/context/sr_context.py:212`、`currency_war_config.py:38` 均不在 3.1 文件面（hp-purge.md:18 连带面只列 cw_comps/cw_performance/cw_hp_policy 注释）也不在任何阶段的扫描范围。
- 修正方向：两处口径取齐——要么 landing 各阶段加「词表全 src/sr-od-test 扫描（豁免清单申报）」替代文件面限定，要么总纲把「全仓」改述为分面扫描+末阶段全仓辅助盘点的合成口径，并把上述 7 处注释面收编进 3.1 连带面清单。

**M-2 B-4「伤害锚保留」消费者申报失实，vd_p1/vd_p2 删除后成零消费孤儿**
- 位置：`details/hp-purge.md:34`（R-3 删除面补全未申报）、`:49`（词表无 vd 锚）；清查件 §2.2 B-4
- 清查件 B-4 称 vd_p2_loss/vd_p1_loss_* 「还喂 cw_first_passage 掉血分布/cw_plane_table/λ 概率侧」故保留；grep 实证 `kernel/cw_first_passage.py` 零 vd_p* 消费。A 组停升级线族与 p2_supply_horizon 血项（R-3 改「剩余节点数」）删除后，`cw_registry.py:357`（vd_p2_loss）与 vd_p1_loss_intercept/vd_p1_loss_slope_rung 全仓零消费，`04_survival_budget.md` §6-1「L_c 口径差核对」项同死。按执行单一源照单保留 = 留零消费孤儿 + 死核对项，违裁定 #3「禁留废弃」。
- 修正方向：hp-purge R-3 删除面补全增列 vd 锚处置（删除或降级为 sim 校准面单一源并重锚 04 §2/§6-1），词表补符号；同步 04_survival_budget 正本更新清单行（landing.md:105 已列 §6-1 申报，需补 vd 字段本体归属）。

**M-3 负结果记忆的会话字段载体文件面错位**
- 位置：`design.md:48`（「shop_session.py 会话字段扩展」）、`landing.md:57`（3.3 文件面「shop_session.py（标记字段）」）
- `criteria/shop_session.py` 是判据/协议函数模块，其模块头（:4）自述「存储 = session_scope/StrategyState」——现行商店会话状态字段单一源 = `mandate_state.py` StrategyState（shop_plugin_budget:407、shop_visit_restricted:417 先例）。mandate_state.py 在 3.1 文件面（限「计数器与孤儿字段行」），总纲 §2.1 未给 3.3 加字段的 carve-out：按 landing 执行无处落字段，按代码实况执行则越 3.1 文件面契约。
- 修正方向：总纲 §2.1 与 landing 3.3 文件面改为 mandate_state.py（新增字段行级 carve-out），或如实改述字段落点为 StrategyState 并声明与 3.1 的行级分工。

**M-4 B-19「blood_xp_mode 随 R-1 联动核」落点文件不在 hp-purge 文件面**
- 位置：`details/hp-purge.md:26`（B-19 列为「改」类条目）；`design.md:49`（cw_investments.py 划归 3.2）
- blood_xp_mode 定义在 `kernel/cw_investments.py:1216`，消费位 `criteria/levelup.py:386/:389`（门⑥，R-1 改名面）。hp-purge 的 B 组触碰面文件清单不含 cw_investments.py；若「改」涉及该符号（命名收拢/语义申报）即越 3.2 文件面，若不涉及则「改」的语义在 hp-purge 内无内容、不可执行。R-1 词表亦只收 `blood_xp_gate`（改名面），`blood_xp_mode` 的处置结果无验收载体。
- 修正方向：hp-purge §3 R-1 补一行 B-19 处置结论（如「blood_xp_mode 保留为币种判别、消费位语义复核、零 cw_investments 改动」，依据 R-1 币种通式定性），或给 cw_investments.py 相关行加 3.1 carve-out。

**M-5 裁定 #7「场上非线内件」腿的落地转述与腾位机制事实不符，总纲与详设口径不一致**
- 位置：`details/refresh-chain.md:23`（「场上非线内件腾位发生在访问间隙（关店 → 备战腾位 → 重进后席位已空，目标可买自然转真）」）vs `design.md:33`（判据含「∨ 场上非线内件」）
- 机制事实：备战 M4 腾位卖的是**备战席燃料**（bench-only，mandate.py:392 fuel_sell_candidates 签名即 bench 域）；场上非线内件的卖出属部署置换面，且买牌落点为备战栏（merge_mechanics.md §1）——卖场上件不释放备战席，「关店 → 腾位 → 重进转真」链条在「席满 + 零备战燃料 + 场上有非线内件」帧不成立。裁定字面把场上件列为燃料源（工作清单 W3 替换条件与已知余量均含它），设计实际以 bench-only 实现，其桥接论证失实，等效于静默裁掉裁定的一腿。
- 修正方向：refresh-chain §1 如实改写——「场上非线内件」腿在店内条件不可达（买牌落备战栏 + 店内禁卖场上件为能力面裁定），或申报为「需用户对该腿的机制解释再确认」的开放项；总纲 §2.0 同步口径，不得保留与详设相反的条件列举。

**M-6 过程叙事残留 + 修订后未全量同步（写作硬规则 3/4 违例，iteration-design.md §5）**
- 位置与条目：
  1. `landing.md:41`「（无解锁支——**G2 撤稿**，见 refresh-chain §2 末条）」——G2 为对抗审轮次局部编号，全迭代文档无定义，读者不可解析；
  2. `details/hp-purge.md:62`「（曾作为第一版推荐）：被『整条退役』取代后又回定为终选」——修订史叙事；
  3. `details/hp-purge.md:7`「待决约束：R-1/R-3……用户裁决前本篇对应小节不动工」与 `:35`「两项已于 2026-10-28 用户裁决通过……本篇可开工」同篇并存——裁决已定，:7 未同步（硬规则 4 违例实证）；
  4. `design.md:36`「原 W2 解锁支撤稿」措辞同族。
- 修正方向：删 G2 引用（改为「解锁支不设，理由见 refresh-chain §2 关键取舍」）；hp-purge.md:62 改写为纯现选理由；:7 待决约束条目删除或改为已决申报；design.md:36 改「升级推迟期资金序（W2 让位支不设）」。

### 低

**L-1 两详设边界段的行段估算与行段契约矛盾**
- 位置：`details/refresh-chain.md:5`（「shop.py ……会话/凑金段（≈L1600-2080）」）、`details/shop-buy-reform.md:5`（「买面段……≈L200-1600」）
- 总纲 §2.1 契约边界 = 250 | 1961/1962；两详设的 ≈ 段互有重叠错位（1600-1961 双算、200-250 漏归）。虽有「行段契约见 landing」兜底，实现者先读详设即被误导。
- 修正方向：两处 ≈ 段改为与契约一致的 1962/250 分界（或删估算只留契约指针）。

**L-2 总纲行为接口「三布尔合取」计数残留**
- 位置：`design.md:52`
- 括号列举与 refresh-chain §5 伪码均只有两布尔（refresh_warranted(含目标可买) ∧ r2_budget），「三」为旧稿口径残留。
- 修正方向：改「两布尔合取（目标可买并入判据）」。

**L-3 hp-purge §3「仅此两行归本篇 + 3.3 回归锁」落点无处安放**
- 位置：`details/hp-purge.md:34`
- shop.py:373/:996 的回归锁测试面（test_no_target_three_arms / test_decision_payload / test_line_select）全部在 3.1 执行；3.3 文件面（landing.md:57）不含该两行也不含这些测试。「3.3 回归锁」对 3.3 是无主指令。
- 修正方向：改为「3.1 回归锁」（与 landing.md:29 一致）或指向 3.4 行为对照。

**L-4 执行单一源的 B 组编号双表错位未定基准**
- 位置：`details/hp-purge.md:26`（引用 B-6 decision_hp）、`:57`（快照义务）
- 清查件 §1 聚合表与 §2.2 明细表的 B 组编号错位（聚合 B-4~B-7 = 明细 B-5~B-7；聚合表不给「伤害锚」编号），hp-purge 引用的 B-6 按聚合表对、按明细表错行。快照整件抄录后错位随入执行单一源。
- 修正方向：hp-purge §7 快照义务加一句「以 §2.2 明细表编号为准，§1 聚合表编号仅索引」或要求快照时统一重编号。

**L-5 ρ 重定义后 qualified_member_costs 契约描述残留未列入同步面**
- 位置：`details/refresh-chain.md:37`（连带同步面只列 contracts.py:279-282 与 criteria/__init__.py:71-73）
- `criteria/contracts.py:288-291`（qualified_member_costs 契约行）自述「R2 预留卡价同源消费」，ρ 改停留目标价后该描述残留；3.2 文件面（landing.md:43）未列 :288-291。
- 修正方向：3.2 连带面补 contracts.py:288-291 描述同步。

**L-6 裁定载体不在快照清单；W5 前置裁决被设计径行裁决**
- 位置：`details/hp-purge.md:57`（快照清单=三份证据文件+词表）；`details/shop-buy-reform.md:15`（达标成员停买口径）；`design.md` §3（决策点表无此项）
- 裁定 #1-#7 原文与 W 编号定义寄存 `.debug/temp/2026-10-28_CW修复工作清单.md`（gitignore），不在快照义务内——.debug 清理后设计的合法性来源断链。且工作清单 W5 明标「前置裁决：need_star 达标后同名副本语义……待裁决后设计」，详设径行定为「显式停买（star_goal_met）」，总纲 §3 未载该裁决——设计越过清单声明的裁决流。另 landing.md:110 把 flow/session.md 的清查件行号标为 D-27/D-28/D-29（session.md 实为 D-26），对账标签小错。
- 修正方向：快照义务补裁定载体（或总纲 §0 就地全文照录裁定原文）；W5 口径列入 §3 决策点表标「随对抗审定稿请用户确认」；landing 对账标签改正。

## 已攻击面清单（实际做过的核验）

1. 五篇对象全量通读 + design↔details↔landing 交叉对读（行段契约、carve-out、文件面、依赖链、七件齐、模板符合性）。
2. 规范源 iteration-design.md 全文（四硬规则/七件/引用寿命/三核细则）逐条对照。
3. 代码锚直调：shop.py（2080 行总量、1-260/261-390/735-859/860-1009/1265-1294/1540-1629/1951-2080 逐段）、refresh.py 全文 378 行、contracts.py 80-368、criteria/__init__.py 全文、levelup.py 160-514、cw_discipline_rules.py 75-262、cw_economy.py 790-889/1065-1104/1230-1305、cw_intention.py 1060-1209/1420-1609、cw_comps.py（37/125/538/2852-3127）、cw_performance.py（100-129/238-269）、cw_registry.py（175-179/357/603-719/700/858/936-938）、cw_vocab.py:65/:69、mandate.py（1-30/380-439/950-1004/1065-1094）、mandate_state.py、statefn/odds.py:55-84、statefn/predicates.py:125-185、economy_cycle.py 全文 313 行、telemetry/schema.py:480-509、entry.py:480/:545-614、decision_payload.py:101、cw_investments.py:455-494/:1216、criteria/shop_session.py 头部、cw_observation.py:940-984、cw_entry_policy.py 全文、cw_first_passage.py（vd 消费 grep）。
4. 全仓符号级 grep：p2_supply_horizon/arm_a_*/no_target_arms/hoard_target_set/k_empty_window_fallback、blood_xp_*、blood_budget_*、p1/p2_blood_floor、hp_floor_triggered、k_alert、handoff 族、HP_SAFE_THRESHOLD/effective_hp_threshold/PerformanceTracker/maybe_pivot/pivot_overlap、vd_p1/vd_p2、emergency_hp/is_emergency/refresh_ev_budget、neardeath_direction、levelup_crisis_defer/level_spend_blocked、_up_clicks/_up_cost/GATE_GOLD_SHORT。
5. 策略正本被引行直调：11_shop_decisions.md:55-58/:59/:84/:100/:106/:110/:186、01_math_framework.md:194（钩子行）、23_shop_screen.md:10/:13、10_prep_decisions.md:196-199、04_survival_budget.md §2/§6-1、12_line_and_intention.md §1.4、14_p1_consume_arms.md N5/Z1 相关行、00_framework §3/§4、math_proofs.md P21(:45)/P36(:60) 行、proofs/p37-late-xp-conversion-cost.md:183-190、p86/p21/p37/p71/p72/p85/p28/p24/p36 单篇与 validations 存在性、merge_mechanics.md 全文（§1/§2/§2.5/§2.6）。
6. 证据文件抽核：hp 清查件全量读（A/B/C/D/DG/E 组结构与条数、§3 裁决项、A-9 交叉复核口径）、追查件（§1.2/§1.4/§4/§5 缺陷编号/§7 三节）、复盘件（A2 装备穿戴条目）、工作清单（裁定 1-7 照录、执行纪律节、W1-W11 各项与状态）。
7. 测试面锚：test_seat_recoverable_narrow.py、test_decision_payload.py:1-30/:130-194、test_line_select.py:340-379、test_sim_levelup_cycle.py:20-89、test_no_target_three_arms.py、test_levelup_prob_axis.py:311/:421/:508、test_economy.py（refresh_ev_budget/reserve_cap 断言组）、test_cw_interest_floor.py 不存在性核实（代码注释旧名漂移，设计未引，不立案）。
8. 边界件：changes/2026-10-28-supply-decision-wiring/ 存在性；changes/2026-10-18-levelup-band-gate/design.md:156（攒金收敛态声明域）与 W8-1 勘误口径。
9. 治本核：总纲 §1 归层（语义层 hp 输入化 + 约定层残件堆积）与证据吻合；金线闸/资金序/免费分支纳入判据的饿死环论证按门⑦ gold_short 凑金收敛链复核成立；「明确不解决」四项边界依据（W6/W7/A2/supply-wiring 独立迭代）逐项成立。
