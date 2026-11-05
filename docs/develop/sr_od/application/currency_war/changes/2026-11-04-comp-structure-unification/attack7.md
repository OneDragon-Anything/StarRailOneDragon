# 对抗审查报告·第七轮（核一·无前提 + 实现者走查）

> 攻击对象：README.md / design.md / details/{faction-priority, counter-tables, transition-library, press-stockpile}.md / landing.md（七份，本目录）。前六轮报告（attack.md～attack6.md）未读、未 grep、未引用；本报告全部证据为本轮自行对码取得（对码基准 = 工作区当前源码与测试仓）。核验方法：事实主张逐条对源码/测试取行级证据（属性读与关键字参数构造两种形态均查）、删除符号全库消费对照、「不动文件」波及核查、三层同主张同步复查、实现者逐阶段桌面演练。

## 攻击点清单

### G1 test_f9 是混合断言测试，按「测试函数粒度删」会误伤另一迭代的行为锁
- **位置**：details/press-stockpile.md §3（测试删除——「`test_front_window_predicates.py` 中仅收窄域相关测试函数随源删（该文件含非收窄域谓词测试 ×4，保留不动——按测试函数粒度删，不整文件删）」）。
- **攻击**：该文件实际含 6 个测试函数：4 个前窗谓词函数（非收窄域，保留面——已核，数量申报准确）+ 2 个收窄域类方法。其中 `test_f9_unlocked_frame_untouched`（test_front_window_predicates.py:229-245）是**混合断言**：除收窄旗断言（`swap_transition_narrow_frame(...) is False`，:237）外，还捆绑「万金油件（花火）不再经序 1 义务面自动买入」（:235-242，断言无 `m2_` 买因发射）与「hub_option_buy 零显影」（:244-245）——这两条是统一让位优先级迭代 3.4「万金油退出义务买入面（申报②）」的验收断言，与 P88 收窄无逻辑关联（其 docstring 自述覆盖对象含「统一让位优先级迭代 3.4——原乙臂〔枢纽件经序 1 成员面照常发射〕随万金油项删除废止」）。按设计给的「测试函数粒度删」指令整删该函数 = 连带删除该行为锁，测试覆盖静默回退；不删则收窄域断言面残留已退役符号。设计未回答混合测试函数的处置（整删 / 拆函数保留万金油断言面）——实现者必须自行决定，违反「实现者无需再设计」定稿门槛（iteration-design §5 硬规则 2）。
- **证据**：sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_front_window_predicates.py:229-245（断言混合形态）；同文件 :185「锁线转型域收窄(原 press_narrow_transition 并入)」分区注。
- **严重度**：中（须修订——补一句混合函数的拆分/保留口径；不阻断结构设计本身）。

### G2 冷启动臂退出判据 `_p1_system_support` 的处置无答案（死循环防线承接的缺口）
- **位置**：details/transition-library.md §3（冷启动与回退——「冷启动买入分支（shop.py `_COLD_BOND_KEYS`）与保护集（protection.py 体系键）的键域**改读过渡库见即买并集**」）。
- **攻击**：现行冷启动臂（shop.py:1616-1652）触发条件是**四联**：未锁定 ∧ 实候选空 ∧ 过渡候选空 ∧ 三羁绊支持度现算全 0——第四联读 `cw_intention._p1_system_support(gs)`（shop.py:1628-1629，退出判据「任一三羁绊 > 0 即停，希儿系点亮不算——防希儿开局帧误判退出/触发」，分支注释 :1620-1621 自述）。详设只申报了**键域**改造（`_COLD_BOND_KEYS` 换源）；退出判据这一联的处置全文无答案。`_p1_system_support`（cw_intention.py:461）不在退役符号集中清单（清单只列了 `_p1_pair_support`），也不在保留边界声明；其全库消费面 = cw_intention 内部三处（:503/:615/:983，均在随配方机器删除的函数族内）+ protection.py:75（在 `refresh_transition_locked_systems` 内，随 §4 合并裁定改造消失）+ shop.py:1628（**无任何设计覆盖**）。新机器的计分是「成员持有分」（§2），与体系支持度不同源：改后该函数若删则退出判据断供、若留则判据与「见即买→持有→计分>0→候选形成」（§3 死循环闭环叙述）的等价性未论证——尤其现行注释里「希儿系点亮不算」这类防误判语义在新计分下的对应物未设计。实现者必须自行决定函数去留与退出判据换轴方式。
- **证据**：shop.py:1626-1629（四联触发条件与 `_p1_system_support` 读取）；cw_intention.py:461（定义）；protection.py:75；transition-library.md §3（仅键域改造申报）。
- **严重度**：中（须修订——在 §3 补一句退出判据处置即可；属单点申报缺口，非结构缺陷）。

### G3 README 进度节三处陈旧（含已被推翻裁定的旧语义残留）
- **位置**：README.md「进度」节（:11-15）。
- **攻击**：三处不同步：① **旧行残留**——「设计对抗:四轮完成 · 报告=[attack.md]…[attack4.md]」（:14）是被五轮行（:13）取代后未删除的旧进度行，同节并存两条「设计对抗:」进度，违反 iteration-design §4「进度只写在 README（一处）」与硬规则 4「修订后全量同步复查」；② **轮次脱节**——attack6.md 已存在于本目录（第七轮攻击者旁观到的文件事实），而进度停在「五轮完成、待第六轮」（:12-13），进度记录与已发生轮次不符；③ **旧语义残留**——:12 括注「（含 E1 拆表重构：克制数据拆两张独立表、**过渡层仅不可玩级排除**）」中后半句是第五轮时点的旧设计状态；后续裁定已改为统一减分制（design.md 契约 A「用户 2026-11-04 裁定纯减分制无排除特殊逻辑」、transition-library.md §2「纯减分、无排除特殊逻辑」）——design/详设已同步、README 残留被推翻表述，正是「被后续裁定推翻的旧表述残留」类型（三层同主张同步失守）。
- **证据**：README.md:12-15；attack6.md 的存在（目录清单）；design.md 契约 A；transition-library.md §2。
- **严重度**：低（表述级——README 是索引文档，不影响实现者开工；但定稿前应清）。

### G4 详设⑤ 路径写错：deploy_search.py 不在 criteria/ 子目录
- **位置**：details/transition-library.md §5 裁定注⑤——「`criteria/deploy_search.py:985` 部署圈人过渡支」。
- **攻击**：deploy_search.py 实际位于 `strategies/impl/mandate_v1/deploy_search.py`（mandate_v1 直下），`criteria/` 子目录下没有该文件；行号 :985 本身准确（`plane1 = not session_scope.plane2_started_of(gs)`，且 :987 读 `p1_pair`，确为部署圈人过渡支）。同迭代 landing.md 3.2 对 sell_gate.py 特意标注「（注：在 mandate_v1/ 下、非 criteria/ 子目录）」，说明文档对这类路径错位有明确警觉，而本条未做同款校对。落地批按该路径寻文件会先扑空一层。
- **证据**：源码路径 `src/sr_od/application/currency_war/strategies/impl/mandate_v1/deploy_search.py:985`；`criteria/` 目录实际清单（buy/contracts/levelup/priority/refresh/sell/sell_candidates/shop_session/stockpile——无 deploy_search）。
- **严重度**：低（表述级；行号与归类正确，路径多一层）。

### G5 「早前……废除/取代」类修订过程叙事措辞残留两处
- **位置**：details/transition-library.md §2（「早前『不可玩级排除表』设计废除：……」）；details/counter-tables.md §1（「**拆表声明（取代早前『同一张表分批生长』设计）**」）。
- **攻击**：iteration-design §5 硬规则 3「无过程叙事：不写谁审的、第几轮攻击、**上稿改了什么**；过程住对抗报告」。「早前 X 设计废除/取代」是对本迭代内上稿修订的时序锚定（读者需要知道修订史才能理解该括注），同等内容可写成无时序的取舍形态（「备选：排除表——放弃：量子熄火为暂时性削弱非不可玩级……」，归入详设「关键取舍」节即完全合法——transition-library 关键取舍节已有四条同型记录，本条却留在方案节内带时序措辞）。不误导实现，但属硬规则违例形态。
- **证据**：transition-library.md:55；counter-tables.md:24。
- **严重度**：低（表述级）。

### G6 退役符号的注释清理面未穷尽：cw_transition.py 漏列
- **位置**：landing.md 3.3 文件面（「`kernel/cw_plugins.py` 与 `kernel/cw_bridge_pool.py`（存量注释中对退役符号的悬空引用随批清理）」）；details/transition-library.md 退役符号集中清单。
- **攻击**：cw_transition.py:45/:58 docstring 写「定型权威 = `cw_intention.committed_authority`:plane≥2 / 意向状态机 locked / **p1_pair 非空**」——`p1_pair` 是 3.3 白名单退役符号（`IntentionState.p1_pair` 字段删除），且该句描述的序②语义随「committed_authority 序② 替代」（transition-library §4）过时。该文件不在 3.3 文件面（文件面点名做注释清理的仅 cw_plugins/cw_bridge_pool 两处）。同时 3.3 判据「退役符号白名单 grep 清零——判据按符号级，不按字符串盲 grep」在 `p1_pair` 上与保留符号 `sess_p1_pair` 同字符串，注释行命中时的归类（残留待清 / 豁免）需实现者自判。补一行文件面或判据口径即闭合。
- **证据**：kernel/cw_transition.py:45、:58；landing.md 3.3 文件面；transition-library.md §6/退役清单。
- **严重度**：低（表述级——注释悬空无行为影响，判据符号级执行的边界情况）。

## 实现者走查记录

按 landing.md 阶段序桌面演练「凭这份文档开工」，文件面逐个路径解析 + 语义选择查答案 + 判据可独立执行性：

### 3.1 羁绊优先级结构落地 —— 可开工
- **文件面全部可解析**：cw_comps/cw_recipe/cw_line_switch/cw_intention/pick_common/p65_check/cw_plugins + 「其余消费面」清单 13 文件（cw_invest_channels/cw_launch_admission/deploy_search/flow/cw_events/cw_exec_state/cw_investments/invest_env/invest_strategy/sim/power_model/features.py）逐一存在；tools/cw/proofs/p65_check.py（仓库根 tools/）存在。
- **设计依据自足**：§4 映射表 12 行给齐全部读点的现状读法/新读法/行为判定；对码抽验全中——`all_factions = factions ∪ flex`（cw_comps.py:174-176，S3 主张属实）；`_faction_hit_bonus` 三层规则无副档分支（cw_invest_channels.py:159-173，副档落空）、INVEST_SOFT=30（cw_line_scales.py:63，变化①数值「+30/0」有据）；cw_line_switch 防御式读两处（:102/:158，恒空→线距离恒 0 的推断成立）；配方伪阵容构造点确为 `Comp(form_tiers=…)` 关键字形态（cw_recipe.py:46/54/61、cw_intention.py:808）；`__post_init__` 已存在（cw_comps.py:157，「扩展」表述准确）；or_reqs ⊆ 档 0 校验下键集恒等成立（现行希儿 or_reqs 两键均在其 form_tiers 内，SEELE_OR_REQS cw_comps.py:370）；`pair_target_comp` 构造带 `dict(sorted(...))`（:808），迁移保序恒等推演成立；首键读法全库唯一（`next(iter(c.form_tiers)` 仅 cw_intention.py:544；全库 `factions[0]` 读法均为 Character/SystemCard 侧、无 Comp.factions 首元素读——S1「唯一生产消费」与龙丹/桑博两处键序敏感主张成立，COMP_LIBRARY 确 21 套）；p65_check 确读 `c.form_tiers`/`c.sub_tiers`/`ist.p1_pair_frozen_obs`（:90/:100/:154/:210）。
- **判据可独立执行**：65 板面算术（21×3+2）正确；快照构造规则（零羁绊/半成型⌈目标/2⌉/成型/混合）与 fixture 落点、生成脚本落点齐备；「关键字参数形态」grep 判据与 `form_tiers=` 实际形态吻合。

### 3.2 克制表直写 —— 可开工
- 文件面全部存在；`currency_war_config.py` 残留注释实际跨 :36-37 两行（MECHANIC_COUNTERS/AFFIX_MECHANIC_MAP 在 :36），详写 :37 一处——判据按符号 grep 不受行号偏差影响，不计攻击点。
- 数据核验全中：MECHANIC_COUNTERS 恰 12 行、AFFIX_MECHANIC_MAP 恰 27 键、LINE_FACTION_TO_MECH 恰 3 对（持续伤害→DoT 改名、减益/燃血恒等，pick_common.py:43-47）、活链路恰 2 条（净化→[DoT,减益]、掉血削上限→[燃血]，其余 10 行值域与三特征交空逐一核对）、死条目「紧急止血→爆发机会」存在（cw_comps.py:293，「等」字覆盖高费审美/形单影只/皮糙肉厚等同型死条目）、`merged_mechanic_tables` 消费点唯一（pick_common.py:69）、COUNTER_PICK_PENALTY=-750 宿主 cw_line_scales.py:70、调用点四行号全准（invest_env.py:337/347、invest_strategy.py:281/338）、新表 2 条的名单与 21 线档 0 键交核验恒等（DOT队/专家桑博DOT 含持续伤害、千冶减益/黄泉减益含减益、万敌单C 含燃血）、RUST_AFFIX_NAME 宿主 cw_comps.py:319 不在删除面与详设一致。残留行号（affix_effects_data.py:11、cw_briefing_obs.py:54/90/357、cw_affinity_table.py:97）逐一对码吻合。

### 3.3 过渡阵容库与配方决策层退役 —— 除 G2 外可开工
- 文件面全部可解析（statefn/predicates 解析为 statefn 目录下 predicates.py；economy_cycle 存在且有 TRANSITION_TRAITS 消费——键域改造的泛述覆盖）；「不动的文件」清单 7 项全部存在（tools/cw/ 路径按仓库根解析）。
- 数值对码全中：体系卡判据档 FACTIONS tiers[0]（仙舟3/持续伤害2/列车同行2/量子同频2/贝洛伯格2，cw_factions.py:53-91 + cw_system_cards.py:48-50）；配方完全体档列车 4（cw_recipe.py:54）；条目表四人费值全对（爻光1/藿藿1/丹恒·饮月2 = _CORE_TRIO cw_line_facts.py:30；姬子·启行3/三月七1/希儿3 = cw_chars.py:128-154）；费段解锁真值全对（REFRESH_PROB：lv1-3 纯 1 费、lv4 起 1-3 费、lv5 起 4 费、lv7 起 5 费，cw_shop_odds.py:47-58）；or_reqs/required_deployed 与现行 SEELE_OR_REQS/SEELE_CARRY_CHAR 逐字一致（cw_comps.py:370-371/:528）；star_goal 铁三角 2★/希儿 3★（cw_system_cards.py:107/:134）；「档 0 空而 required_deployed 非空合法」由 form_progress 现行实现支撑（cw_comps.py:1137-1172，required 逐名折条独立于羁绊账）；TRANSIT_AFFIX_PENALTY 九行行号依据逐一对码吻合（cw_affinity_table.py:99/109/112/114/116/118/178/518/545/550），「救世主」为合法羁绊名（FACTIONS 注册表 in独立 类，白厄专属，cw_factions.py:104）、「量子熄火前 4 次攻击 1 点伤害后解除」与 affix_effects_data.py:25 原文一致；committed_authority 序①②（:1198-1233）；transition_locked_systems 三端（写端 protection.py:54、消费端 bridge.py:244-284、位面清空 flow.py:233）；direction_comp_of 十处消费点申报准确（flow×5 :558/577/595/617/648 + entry×3 :514/1166/1194 + shop:863 + decision_payload:62——其余 grep 命中均为注释/docstring）；sess_p1_pair:466/sess_framework:406 准；槽语义下游六点行号全准（:1260/:1304-1364（:1353 直读 p1_pair+_pair_members）/:1426/:1187/:1616 及 sell_gate.py:70/:779）；退役符号 12 函数 + 5 字段 + mandate_state 字段 + cw_system_cards 六符号全部真实存在；`update_p1_recipe`/`clear_p1_recipe`/`pair_target_comp`/`decision_target` 全库消费对照无详设外遗漏（decision_target 全库零外部消费，整模块删除断链为零；flow/mandate_state/session_scope/priority/sell_candidates 的注释提及均落在 3.3 文件面内）；七处换轴归类点行号全准（除 G4 的 ⑤ 路径前缀）且全库 `plane2_started` 其余消费（line_select 终局锁定触发、levelup 升星辖域、refresh 刷新节奏、session_scope 维护点）均可按「无关用途保留」二分原则归类——详设自声明「落地批以同一 grep 复核补全」的可执行闭环成立。
- **拍板点**：仅 G2（cold_start 退出判据）。

### 3.4 富余买入并入压牌库与 P88 退役 —— 除 G1 外可开工
- 文件面全部存在；shop.py:1893 注释原文逐字属实（「压牌库判据的席位维由序列/末位让路承载」，:1893-1894 跨行）；M6 结构与「tier_w 空插兜底带」落点吻合（:1906-1908 现行 m6_overflow_strand 分支）；义务装配行号群全准（k_members :863-864、buy/obligation_members :884-904，契约 D 申报与代码一致）；dominance_buy 序 6 全貌（契约键 ('mandate','dominance_buy') contracts.py:236、eligible mandate.py:557、调用段 :958-979、dead_stock 防线在循环内 :2137、_narrow_frame 消费点 shop.py:982 与计数 :2157、sell_gate.py:131 映射键）；`swap_transition_narrow_frame` 全库消费（mandate:975/shop:982/cw_deploy_logic 注释 :192/:200）均在申报删除/文件面内；PRESS_NARROWED_ARMS 独苗属实（mandate.py:676-680，hub_option_buy 并入移除注释在案）；dead_stock docstring s77091 叙事 :644-649 准；p88_check.py:34/:87 准；test_dead_stock_pair.py:187-195 直调断言区准；test_sell_window_launch.py 闭集对账与 S_spec 断言（:164/:168/:180-183）存在，键集期望更新判据可执行。
- **拍板点**：仅 G1（test_f9 混合断言）。

### 末阶段 正本更新 —— 可开工
- 正本更新清单 12 条目标全部存在（strategy-docs 六篇 + README、sim-power-model 相关、proofs/、skills/sr-od-dev-currency-war/references/comp-definition.md（仓内 skills/ 与挂载 .agents/skills/ 双路径均在）、docs/game/currency_war/）。
- 黑话终扫判据可执行：术语表 §1 替换表词在七份文档中零命中（逐词扫描）；「正本」8 处均为模板固定节名（landing 有自觉豁免注）；「sub_tiers 对拍锚」为代码源字符串原文引用，合法。

## 收敛判定建议

本轮对七份文档做了全量对码核验（事实主张抽样约 70 项逐条对源码取证）与实现者逐阶段走查：**无高危发现**。design/详设/landing 三层的事实主张密度与准确率显著高于常规设计稿——抽查的全部符号、行号、数值、表数据、路径、测试断言区除下述清单外均对码吻合，删除符号的全库消费对照未发现详设外断链，「不动文件」波及与接口契约（A/B/C/D）钉死度均通过核验。

**不满足「本轮收敛、可定稿」——须先修复两个中级项**：

1. **G1（中）**：补 test_f9_unlocked_frame_untouched 的处置口径（拆分保留万金油断言面，或声明整删及覆盖替代）——press-stockpile §3 一句话修订；
2. **G2（中）**：补冷启动臂退出判据（`_p1_system_support`，shop.py:1628-1629）的换轴申报（函数去留 + 新退出条件与「希儿开局帧防误判」语义的等价物）——transition-library §3 一句话修订。

两个低级项建议随上述修订顺手清理（G3 README 进度节重写为单行现态、G4 ⑤ 路径去 criteria/ 前缀、G5 两处「早前……」改写为无时序取舍、G6 文件面补 cw_transition.py 一行）；均不构成定稿阻断。G1/G2 修订完成后，从本轮核验面看已无已知阻断项，可进入定稿。
