# 对抗审查报告·第六轮（核一·无前提 + 实现者走查）

> 取证方式声明：本报告全部证据来自对 7 份文档逐字直读 + 对 `src/sr_od/application/currency_war/`、`sr-od-test/`、`tools/cw/`、`docs/`（非本迭代目录）的独立对码（直读文件 + 定向 grep）。**披露**：审查中途一次对迭代目录的目录级 grep 侧漏了 attack.md～attack5.md 的匹配行——按本轮任务铁律，这些侧漏内容一律不作为依据；下文每个攻击点的证据均为本人独立复核所得，与侧漏内容无关。侧漏后已停止对迭代目录的一切目录级检索，术语扫描改为对 7 份文档逐文件定向检索。

## 攻击点清单

### F1 点名型条目的型语义与锁定判据冲突：缺引擎/缺引导件的板面可完成锁定
- 位置：details/transition-library.md §1（点名型定义）、§1 条目表（仙舟铁三角/列车骨架行）、§2（锁定评估域）、§1 硬约束末句。
- 攻击：§1 点名型自述适用「引擎不可拆（仙舟铁三角——**引擎缺失的仙舟凑数不构成该过渡**）」与「线定义件引导（列车骨架——**姬子在场才值得朝列车走**）」；但锁定判据 = 「对候选槽内条目求 form_progress ≥ 1.0 即锁」且硬约束明文「羁绊凑人数**不限点名成员**（成型判据读板面羁绊计数，三型同规则）」。计分门控只挡「零点名成员持有」（§2 原文）。组合结果：持 1 名点名件（如仅爻光，score=1 入候选）+ 板面凑满 3 仙舟（爻光+景元+符玄）→ form_progress({仙舟:3})=1.0 → **锁定一个缺 2/3 引擎的「仙舟铁三角」**；持三月七 + 板面任意第二名列车成员 → 锁定**无姬子的「列车骨架」**——两点名型条目表的 or_reqs/required_deployed 列均为「—」，没有任何把型语义接入成型判据的机制（实码 form_progress 只读 faction_reqs/or_reqs/required_deployed，不读 core_chars，cw_comps.py:1111-1177）。锁后不换不可逆，型语义（引擎不可拆/引导件在场）在锁定这一步完全不被执行，沦为只约束候选计分的装饰性表述。实现者要么按 §2 字面实现（违反型语义），要么自行给点名型补 required_deployed/点名在板条件（设计无文）。
- 证据：transition-library.md §1/§2/条目表原文（如上引用）；cw_comps.py:1111-1177（form_progress 实现无 core_chars 参与）；cw_system_cards.py:105（「缺一=空壳」——型语义的判据源本身即要求全员）。
- 严重度：中（须修订：或补点名在板判据，或改写型语义句并申报「部分引擎锁可接受」的行为面）。

### F2 退役符号集中清单自相矛盾：direction_comp_of 同表两行「删除」vs「函数保留」
- 位置：details/transition-library.md「退役符号集中清单」两行 + §5 第四侧；landing.md 3.3 完成判据。
- 攻击：清单行 A「配方开局面读口（session_scope.py:395-412）｜session_scope.py｜**删除**」与行 B「direction_comp_of 消费段｜shop.py｜**改造（函数保留内部换源四层优先，见 §5 第四侧；十处已登记消费点零改动）**」互斥：session_scope.py:395-412 实码就是 direction_comp_of 的定义区（def 在 :400、函数体至 :421，:395-397 是上一个函数 line_members_view 的尾部——该区域不存在另一个可删的独立「读口」）。§5 第四侧又明文「函数保留……不删函数（删即断链）」。landing 3.3 完成判据把这张表声明为「grep 清零」的**唯一依据**并「按符号级」执行：行 A 若折算为符号 direction_comp_of，则白名单要求其清零而行 B/§5 要求其保留——判据不可一致满足；worker 按行 A 删函数则断十处消费点（flow×5/entry×3/shop:863/decision_payload:62，本人逐一清点恰为十处），按 §5 保留则按行 A 验收必红。同表 flow.py 行已带「删除/改造（第四侧替代见 §5）」指针，行 A 无任何指针，属修订残留。
- 证据：transition-library.md 退役清单两行原文；§5 第四侧原文；session_scope.py:385-421 实码（direction_comp_of def :400）；flow.py:558/:577/:595/:617/:648、entry.py:514/:1166/:1194、shop.py:863、decision_payload.py:62 十处消费点；landing.md 3.3 判据「白名单 = 详设『退役符号集中清单』逐符号……唯一依据」。
- 严重度：高（阻断定稿：完成判据的唯一依据自相矛盾，违 iteration-design 硬规则 4）。

### F3 「语义连续／更精确而非更宽」的迁移基线主张与实码不符（净化身心×DOT 方向）
- 位置：details/transition-library.md §2（词缀/boss 排除面）与 §7 申报第 5 条。
- 攻击：三处事实失实。① §2 称「净化身心 → [持续伤害]……廉价 DOT 条目不进候选（承接现行体系卡警觉与 `_pair_restart_dead` 的全线重开排除，**语义连续**）」——实码 `_pair_restart_dead`（cw_intention.py:550-570）对 DOT 体系对要求映射线集（DOT队 ∧ 专家桑博DOT）**全部**重开级；专家桑博DOT 在 AFFINITY_TABLE 无行（表键集 :75-:231 无该线），走 dot 轴泛化只给怕档 −150 且 `affix_restart_hit` 明文「泛化层恒不给重开级……不参与本判定」（cw_affinity_table.py:413）→ all() 不成立 → **现行净化身心局 DOT 体系对照常进候选**；现行唯一警觉是体系卡软权重（dot2 affix_fears=['净化身心']，_WEIGHT_AFFIX_FEAR=−3.0，cw_system_cards.py:119/:59）。新机器的排除是**新增**（更宽），不是「语义连续」。② §7.5 定性「更精确而非更宽：旧首键映射漏挂的线不再漏防」——按①，变化方向实际是双向的（DOT×净化身心变宽；若按 §2 字面二行落表，希儿方向还会变窄，见 F4），该定性两向都不成立。③ §2「黄泉减益线同为净化重开级」——黄泉减益行无净化身心登记，泛化注释明文「已登记线黄泉减益无此记载=记 0」（cw_affinity_table.py:340-341）；「净化重开级」与登记相反（重开级是 RESTART_PENALTY 分档名，黄泉减益在此词缀上是 0 分）。
- 证据：cw_intention.py:550-570；cw_affinity_table.py:174-179（DOT队 行）、:285-307（专家桑博DOT='dot' 轴、无吃怕行）、:407-422（affix_restart_hit）、:340-341（黄泉减益记 0 注）、:108-118（希儿量子 5 条重开级行）；cw_system_cards.py:119。
- 严重度：中（须修订：改写迁移基线表述并如实申报双向变化）。

### F4 TRANSIT_RESTART_FACTIONS 行集未定稿：生成规则非机械、仅 2 行有答案、人工核对判据缺位
- 位置：details/transition-library.md §2（TRANSIT_RESTART_FACTIONS 生成规则）；landing.md 3.3 完成判据。
- 攻击：设计给出「生成规则 = cw_affinity_table 重开级登记（score = RESTART_PENALTY 的线级行）投影为羁绊键、逐行人工核对入库」+「已知活链路」2 行（量子熄火→[量子同频]、净化身心→[持续伤害]）。但该规则**不可机械执行**：重开级行的被克侧是「线」不是羁绊键，投影到哪组键需逐行语义判断——旗舰例自身就未按机械投影（量子熄火×希儿量子若按线键全集投影应为 [量子同频, 贝洛伯格]，设计只给 [量子同频]）。实码重开级行共 7 条词缀行 + 3 条 boss/强敌行（希儿量子×量子熄火/丢失幸运/免死金牌/极速制冷/以人为本 :108-118；万敌单C×永久创伤 :98-100；DOT队×净化身心 :177-179；史瓦罗×反甲白厄 :516-519；红绿灯×反甲白厄/万敌单C :543-551），设计只回答了 2 行，其余 5+ 行（尤其丢失幸运/免死金牌/极速制冷/以人为本——现行机器在这四词缀下**确实排除**希儿系对，因为希儿系对映射线集 = (希儿量子,) 单线全重开）落表与否、映射到哪些键均无答案。若按「已知活链路」二字面落 2 行表 = 希儿引擎在这四词缀局不再排除（保守向**回退**，现行有防护、新机器没有，且未在 §7 申报）；若按全投影落表 = 需对每行给键映射（设计无文）。且 landing 3.3 的人工过目判据只写「过渡条目全量数据人工过目」，不含该表——「逐行人工核对」无验收锚。worker 必须自行设计表数据。
- 证据：cw_affinity_table.py:98-100/:108-118/:177-179/:516-519/:543-551（重开级行全清单）；cw_intention.py:532-547（希儿系对映射线集=单线）+ :550-570（all 判定）→ 四词缀下现行排除成立；transition-library.md §2 原文；landing.md 3.3 判据原文。
- 严重度：高（阻断定稿：安全排除表的数据未定稿，两可落表各有未申报行为差，违「实现者无需再设计」）。

### F5 counter-tables §5 残留清理文件面与 landing 3.2 文件面失同步：判据域 > 允许动文件面
- 位置：details/counter-tables.md §5「判据域限定」；landing.md 3.2 文件面。
- 攻击：详设把 `data/affix_effects_data.py:11`、`obs/cw_briefing_obs.py:54/90/357`、`kernel/cw_affinity_table.py:97` 的注释/字符串残留「**一并列入本阶段文件面清理**」，且判据要求「src/ 生产代码三张表符号零残留（grep 核对）」——四处残留本人逐一复核实存（affix_effects_data.py:11、cw_briefing_obs.py:54/:90/:357、cw_affinity_table.py:97）。但 landing 3.2 文件面仅列 cw_comps/pick_common/invest_env/invest_strategy/currency_war_config + 测试镜像，**不含这三个文件**：worker 按文件面干活则 grep 判据必红，按详设清理则越出 landing 文件面（无申报的自行扩面）。design↔landing 同一主张两层不一致，违硬规则 4。
- 证据：counter-tables.md §5 与 landing.md 3.2 文件面原文对照；上述三文件四行残留实码（本人定向 grep 独立命中）。
- 严重度：中（须修订：landing 3.2 文件面补三文件，或详设改口归入后续批次）。

### F6 迭代文档自身术语违例：「挂点」未替换，且终扫范围不含 changes/ 自身 → 义务无检查位
- 位置：details/transition-library.md:51；design.md 方案 5；landing.md 末阶段终扫。
- 攻击：术语表 §1 替换表「挂点 → 插入位置/调用点」（§0.1「必须替换」），transition-library.md:51「调用**挂点** = 现行 update_p1_recipe 的调用位点原位替换……**挂点**不变」两处未替换。本迭代自设黑话清理义务（design 方案 5），但 landing 末阶段终扫范围 =「迭代全部文件面（含正本更新清单触及文档）」= 代码 + 正本文档，**不含 changes/ 迭代文档自身**——「新写稿守本表」（术语表 §0.4）在本迭代没有任何检查/验收载体，违例将随定稿固化。
- 证据：transition-library.md:51 原文；terminology.md §0.1/§0.4/§1「挂点」行；landing.md 末阶段判据原文。
- 严重度：低（表述级，一处两用；修法 = 改白话 + 终扫补自查位）。

### F7 form_tiers/sub_tiers 注释级悬空引用排在 3.3 而字段删除发生在 3.1
- 位置：cw_plugins.py:17/:115、cw_bridge_pool.py:7；landing.md 3.1/3.3 文件面。
- 攻击：cw_plugins.py:17（注释「……改本表 majority_lines 与对应 Comp.sub_tiers」）、:115（**运行时遥测 source 字符串**「……(sub_tiers 对拍锚)」）、cw_bridge_pool.py:7（注释「form_tiers 机制承载」）在 3.1 删除两字段后即成悬空引用；这三个文件被排进 3.3 文件面（理由是「对退役符号的悬空引用随批清理」——指配方机器符号），3.1 文件面不含它们 → 3.1→3.3 之间存在悬空窗口且阶段归属错位（form_tiers/sub_tiers 是 3.1 删除面，不是 3.3 的配方符号面）。
- 证据：三处实码（本人 grep 命中 cw_plugins.py:17/:115、cw_bridge_pool.py:7）；landing 3.1/3.3 文件面原文。
- 严重度：低（卫生级：注释/字符串悬空不影响运行；修法 = 三处归入 3.1 文件面随手清理）。

### F8 「test_front_window_predicates.py 收窄域行为测试——随源删」删除粒度不明，连带面无处置
- 位置：details/press-stockpile.md §3；mandate.py:670-672 注释；test_front_window_predicates.py / test_leak_ladder.py 实码。
- 攻击：该测试文件并非纯收窄域测试——实含 4 个与 P88 无关的窗口谓词测试（test_table_ready_true_and_front_window_round_window / test_fail_closed_when_table_or_anchor_or_plane_gate_fails / test_dirty_table_frame_silent_false / test_store_plane_table_shape_feeds_predicates，:128/:144/:161/:170）+ 收窄域两类（TestDominanceNarrowFire :213 / TestUnlockedFrameUntouched :229）。「随源删」按文件整删会误删 4 个无关测试，按类删则设计无文；另 test_leak_ladder.py:13-15 文言将该文件标为「候选构造单一源（跨文件消费）」（实无 import、删除不炸运行，但设计的测试处置段应核对这一声明）。删除粒度 = worker 自行拍板。
- 证据：test_front_window_predicates.py 测试清单（如上行号）；test_leak_ladder.py:13-15 原文；mandate.py:671（「收窄域行为测试 = test_front_window_predicates.py」——源码注释同样整文件指认）；press-stockpile.md §3 原文。
- 严重度：低（须在详设写明删除面 = 两收窄测试类、其余测试与构造基建保留）。

### F9 「旧回退带的四体系引擎件全集」与实码不符
- 位置：details/transition-library.md §3（冷启动与回退）。
- 攻击：§3 把新见即买并集描述为「替代旧回退带的**四体系引擎件全集**」——现行 p1_gap/p1_transition 带的成员集 = `_pair_members(_P1_PAIR_PREF)`（cw_intention.py:1147-1148）= 四体系**羁绊全体注册成员**并集（任一角色阵营∪流派命中四体系键即入，含全部 DOT/仙舟/列车/量子·贝成员 + 希儿），不是「引擎件」（引擎件 = 铁三角 + 希儿，cw_system_cards.blank_window_policy 的 engine_chars 口径）。新集（点名集 + 羁绊全体成员）与旧集的实际差远小于该表述暗示，回退行为对照的基线被写错。
- 证据：cw_intention.py:1143-1150（hoard P1 分带现读 _pair_members(_P1_PAIR_PREF)）与 :715-730（_pair_members = 羁绊成员全集展开）；cw_system_cards.py:404-405（engine_chars = 铁三角∪{希儿}）。
- 严重度：低（表述级事实偏差；§3 对新集的构造定义本身自足，不影响实现）。

## 实现者走查记录

（按 landing 阶段序逐阶段桌面演练「凭这份文档开工」；全部路径逐个解析、判据独立执行性核对。）

**3.1（羁绊优先级结构）**：文件面全部可解析——kernel 四件（cw_comps/cw_recipe/cw_line_switch/cw_intention）+ pick_common + proofs（p15/p15v2_fit.py 实存于 tools/cw/proofs/p15/、p65_check.py 实存）+ 消费面 11 文件全部实存（cw_invest_channels/cw_launch_admission/deploy_search/flow/cw_events/cw_exec_state/cw_investments/invest_env/invest_strategy/sim/power_model 目录/features.py）。§4 映射表 12 行逐行对码成立：成型度（cw_comps:1111-1147 只读 faction 键）/L1（deploy_search:213/:227/:302/:306）/L2（:338-341/:359/:656，sub_tiers 全库恰 5 读点与「消费 5 处」一致）/囤货键（cw_intention:1079 form∪sub 手写并集）/投资通道（cw_invest_channels:159-174 三层规则无副档分支，与 S3 一致；flex 降档式 :172-173 = 变化①模板）/轮廓（cw_comps:173-176 form∪flex，与 S3 一致）/受克（pick_common:50-59；or_reqs ⊆ form 键集使「改读档 0」恒等）/首键（:544 `next(iter(c.form_tiers), '')` 全库唯一生产消费；21 线独立复核：仅龙丹（次键列车同行）与专家桑博DOT（次键贝洛伯格）行为受键序影响，其余 19 线与主键所在体系对键集无交——「两处」主张成立）/护栏（:1467 form∪sub 直读）/or 承接（cw_comps:1124-1126）/配方构造（cw_recipe:46/:54/:61 ×3 + cw_intention:808，硬阻断申报属实：字段删除后关键字构造 import 期 TypeError）/线距离（cw_line_switch:102/:158 `getattr(..., 'form_tiers', None) or {}` 防御读静默归空 → 恒 0 判已完成的推演与实码一致）。21 套清点属实（COMP_LIBRARY 恰 21 个 Comp）；sub_tiers 6 处全 int、tuple 零使用属实；建库校验白名单可行（全部 form/sub/or 键 ∈ FACTIONS 注册表键集，本人逐一核对）。65 板面 = 21×3+2 算术成立；迁移规则机械。判据可执行（构造零残留 grep / 校验五条 import 即炸 / 恒等测试）。**卡点：无**（F7 的注释归属为卫生级注记）。

**3.2（克制表直写）**：文件可解析；调用改写式四行号逐一实锚（invest_env.py:337/:347、invest_strategy.py:281/:338，本人定向 grep 独立命中）；27 键/12 行/活链路 2 条/死条目（紧急止血→爆发机会 cw_comps.py:293）全部复核属实；受克行为等价性独立推演成立（改名层 3 对 × punished 键集 ⇔ 直写名单 ∩ 档 0 键；or_reqs ⊆ 档 0 由校验 3 钉死）。RUST_AFFIX_NAME 不在删除面属实（cw_comps.py:319，穿戴语义域）。**卡点 = F5**（判据域三文件不在文件面，判据/文件面冲突）。走查注记：currency_war_config.py 注释引作 :37，MECHANIC_COUNTERS 字样实在 :36（注释块 :35-37）——1 行漂移，不影响可执行性，不单列。

**3.3（过渡库与配方决策层退役）**：文件面含「不动清单」全部实存（cw_engine_facts/cw_win_model/cw_battle_calib/match_archive/ab_judge/win_model_m1/p15 目录/p65_check）；P24_VALIDATION.md:31（rung 单一源 = _engines_count）实锚；ab_judge G1b（:72）实锚。机制面答案基本齐备且对码成立：四条目与 SYSTEM_CARDS 判据一致（仙舟 3/列车 2/DOT 2 = FACTIONS.tiers[0]，希儿判据 = 在板 ∧ 量2∨贝2 与 card_active 逐字一致；engine_required=_CORE_TRIO 同源 cw_line_facts:30；star_goal 2★/3★ 对上 :107/:134）；角色费用六项全对（爻光/藿藿/三月七 1 费、饮月 2 费、姬子·启行/希儿 3 费、黑天鹅 5 费出局，cw_chars.py:128-193）；费段解锁真值逐档对上 REFRESH_PROB（cw_shop_odds.py:47-58）；cw_economy 位面-等级骨架符号实存（:894/:947）；候选机器函数已命名（update_transition_candidates(gs, ist, st)）、挂点原位替换钉死（flow.py:224 现位）；换轴 7 节点逐一对码实锚（priority:151/:327/:332、protection:73、hoard:1143 位面分支、sell_candidates:219、deploy_search:985、shop:847/:865/:883、flow:223-233 含 :233 过渡锁定槽清空）；「现行终局锁定仅位面 2 触发、位面 1 无终局锁定局」与实码一致（line_select:317-332 plane2_started ∧ p2_strategy_pick_done；cw_comps:1026-1029 全部即时锁退役注）；committed_authority 序①②（:1198-1233）、槽下游四消费点（:1260/:1304-1364 含 :1352-1353/:1426 含 :1467/:1187）、need_star 现状（priority.py:164-165 逐字）、k_empty_window_fallback 分带、_COLD_BOND_KEYS（shop:240-241）、保护集体系键（protection:77）、物化写段（flow:245-264）、transition_framework 读点（flow:610/:651）、sess_framework/sess_p1_pair（schema:406/:466）、p65_check 读点（:90/:100/:154/:163/:210/:262）——全部实锚。**卡点 = F2（退役清单自相矛盾）/F4（TRANSIT_RESTART_FACTIONS 行集未定稿）/F3（语义连续表述失实）/F1（点名型锁定语义）**。

**3.4（富余买入归并与 P88 退役）**：文件面全部可解析（shop/mandate/sell_gate/contracts/cw_deploy_logic/p88_check.py/proofs/p88.md 实存）。现状证据逐条对码成立：三通道、M6 席位注释原文（shop.py:1893-1894「压牌库判据的席位维由序列末位让路承载」逐字）、s77091 真凶叙事与根治指针（mandate.py:644-649 docstring 逐字，含「R1 死金×2 + R5 dominance 成对锁席九轮」）、PRESS_NARROWED_ARMS 独苗（mandate.py:676-680 恰 {'dominance_buy'}）、swap_transition_narrow_frame 单函数（:683 起）、调用段 :958-979、契约键（contracts.py:236）、sell_gate 映射键（:131）、p88_check.py:34/:87 逐行、test_dead_stock_pair.py:187-195 直调断言、test_sell_window_launch.py:179-185 收窄集对账、zero_overlap 同规则实存（statefn/predicates.py:47）、M6 tier_w 门槛与排除面（shop:1906/:1898）、dominance_buy_eligible 语义（bench_free>1 金门，测试真值表 :187-196 印证）。契约 D 的名单源耦合申报与 3.3→3.4 顺序锁定自洽。**卡点 = F8**（测试删除粒度，低）。

**末阶段（正本更新）**：清单 12 行逐条可解析——strategy-docs 12/10/24/28/32/README/13/16 实存（29 按落地 grep 定位，可执行）；sim/sim-power-model.md 实存；proofs/p88.md 实存；skills/sr-od-dev-currency-war/references/comp-definition.md 实存（本仓 skills/ 路径正确）；docs/game 侧引用恰 4 处（README.md:20 + data/competitors.md:15/:37/:131，「4 处」计数准确）。判据（清单清零 + 黑话终扫 + 证明留档豁免）可执行；终扫含 §2 保留词首次定义抽查（检查位存在）。**卡点 = F6**（终扫范围不含 changes/ 自身文档，「挂点」违例无检查位，低）。

## 收敛判定建议

**本轮不收敛，不可定稿。** 计数 9 点：高 2（F2、F4）/ 中 3（F1、F3、F5）/ 低 4（F6、F7、F8、F9）。

必须修复项（阻断定稿）：
1. **F2**：修「退役符号集中清单」行 A——session_scope.py:395-412 即 direction_comp_of 定义区，处置改为「改造（内部换源四层优先，见 §5 第四侧）」或删除该行（opening_recipe_comp 字段删除已由 mandate_state 行承载）；同步消除与行 B 的互斥。
2. **F4**：钉死 TRANSIT_RESTART_FACTIONS 全部行与键映射（至少对丢失幸运/免死金牌/极速制冷/以人为本/永久创伤五行给「入表与否 + 键集」答案，并决定是否承接现行希儿系对四词缀排除），landing 3.3 人工过目判据补该表。

须修订项（定稿前一并处理）：F1（点名型锁定判据 vs 型语义二选一并申报）、F3（净化身心×DOT 迁移基线改写为「新增排除」+ 黄泉减益表述纠正 + §7.5 定性改写）、F5（landing 3.2 文件面与判据域对齐）。

低危项可随上述批次顺手清理（F6-F9）。

正面确认（供收敛参考）：五轮消化后的行号级事实主张精度已高——本轮独立对码约 90 处（符号/行号/数值/路径），内容性错误仅 F3/F9/F7/F6 四组表述级 + F5 的层间失同步；两处高危均属「清单/数据未定稿」而非对码错误。修复 F2/F4 并消化 F1/F3/F5 后，具备第七轮收敛确认条件。
