# 对抗审查报告·第二轮（核一·无前提）

> 攻击独立展开：全部证据为本轮直接 grep/读码取得（不采信任何既有报告结论）。
> 被审对象：README.md / design.md / details/faction-priority.md / details/counter-tables.md /
> details/transition-library.md / details/press-stockpile.md / landing.md。
> 核验基准：`src/sr_od/application/currency_war/` 现行代码 + `sr-od-test/` + 正本文档。

## 攻击点清单

### B1 p65_check.py 被 3.1 与 3.3 双重删除面炸掉，却被详设点名保留——「保留边界」声明对该文件失实
- 位置：details/transition-library.md §问题与约束「保留边界」；landing.md 3.3「不动的文件」与 3.1 文件面；details/faction-priority.md §4 表
- 攻击：`tools/cw/proofs/p65_check.py` 是 tools 侧证明校验工具，它同时消费两个被本迭代删除的东西——① 读 `c.form_tiers` / `c.sub_tiers`（3.1 删字段后直接 AttributeError）；② 消费 `ist.p1_pair_frozen_obs`（IntentionState 字段，transition-library 退役清单明列删除）。而 transition-library「保留边界（先声明，防误伤）」把 `p65_check.py` 点名为数据层保留物，保留理由写的是「它们消费的是『四体系引擎计数』这个结算/判据语言」——该理由对这个文件失实：它消费的 form_tiers∪sub_tiers 是 3.1 要删的字段，p1_pair_frozen_obs 是 3.3 要删的退役字段，均非「四体系引擎计数」。landing 3.3「不动的文件（数据层消费链）：…tools/cw/**」与 3.1 文件面/§4 表（自称「全部读点」）都不含它。结果：3.1 落地当天 p65 证明校验工具链断裂，3.3 再补删 p1_pair_frozen_obs 桩二次断裂；「保留边界防误伤」的核心声明没有经过全库消费面核实。
- 证据：`grep form_tiers` → `tools/cw/proofs/p65_check.py:100,154,163,262`（`set(c.form_tiers or {}) | set(c.sub_tiers or {})`，非 getattr 防御，字段删除即炸）；`grep p1_pair_frozen_obs` → `p65_check.py:83,90,204,210`（:210 `self.p1_pair_frozen_obs = pair` 最小意向桩）；transition-library.md:8（保留边界点名 p65_check.py）；landing.md:43（tools/cw/** 不动）；faction-priority.md §4 表与 landing 3.1 文件面均无 p65_check.py。
- 严重度：高

### B2 契约 D 声称「k_members 在 3.3 改为两层合成名单」——transition-library 全文无此设计，3.4 的名单源在两份详设间漂移
- 位置：design.md 契约 D；details/press-stockpile.md「风险兜底·契约 D 修正」；details/transition-library.md §5
- 攻击：契约 D（总纲四契约之一）宣称「M6 兜底带的『线内成员』名单源在 3.3 改为两层合成名单——落地顺序锁定 3.3 → 3.4」。但 3.3 详设（transition-library）全文没有出现 k_members，也没有任何「两层合成名单」的改造条目——它对方向链的实际设计是 §5 第四侧「部署搜索直接读过渡层状态（过渡锁定条目 > 候选首位条目 > 终局锁定线/候选首位，四层优先现读，无状态物化）」，即 direction_comp_of 的单方向名单。现行代码里 `k_members = predicates.line_members(direction_comp_of(session))`（shop.py:863-864）是单方向名单；真正的「两层合成」变量是 `buy_members`/`obligation_members`（shop.py:884-904，锁定线 ∪ 过渡候选并集），是另一个变量。press-stockpile 的「k_members + 两层合成」把两个变量拼成了一个不存在的读口：3.4 实现者无法确定兜底带「与线内成员零重叠」读哪个名单（k_members 单方向 11-4 层优先？还是 buy_members 两层并集？），两个读法的候选集不同、买入行为不同。「耦合点已申报，非独立批次」的可验收性依赖两边对名单源的共同理解——契约 D 没有钉死，各自演化接口就会对不上（iteration-design §2 跨详设契约的定义性失效）。
- 证据：press-stockpile.md:46（「M6 兜底带读的『线内成员』（k_members）在 3.3 被改为两层合成名单」）；transition-library.md §5 全文（无 k_members/两层合成字样；第四侧 = 四层优先单方向）；shop.py:863-864（k_members = line_members(k)，单方向）；shop.py:884-904（buy_members = 锁定线/实候选 ∪ 过渡候选，两层合成但是另一变量）；M6 的 stockpile 契约消费 `k_members=k_members`（shop.py:1912）。
- 严重度：高

### B3 P88 退役漏 tools/cw/proofs/p88_check.py——它 import 3.4 要删的谓词并断言要删的映射键，且与「tools/cw/** 不动」声明正面冲突
- 位置：details/press-stockpile.md §3 删除清单；landing.md 3.3「不动的文件」/ 3.4 文件面与判据
- 攻击：`tools/cw/proofs/p88_check.py` 是 P88 的辖域校验工具：它 `from … import swap_bond_gate_domain_of`（3.4 删除清单明列）、定义 `S_SPEC = frozenset({'dominance_buy', 'hub_option_buy'})`、断言 `LAUNCH_CAUSE_BY_ARM['dominance_buy'] == 'press'`（:87，sell_gate.py:131 的映射键也是 3.4 删除项）。3.4 落地后该工具 import 即 ImportError，断言也永假。它不在 3.4 文件面、不在 press-stockpile §3 测试删除清单（只列 test_sell_window_launch.py / test_front_window_predicates.py）；同时 landing 3.3 明文「不动的文件：…tools/cw/**」。3.4 完成判据「P88 符号零残留（swap_transition_narrow_frame/swap_bond_gate_domain_of/PRESS_NARROWED_ARMS）」若按全库 grep 执行，p88_check.py 就是残留本身——判据、文件面、保留声明三者互斥。
- 证据：p88_check.py:34（import swap_bond_gate_domain_of）、:50（S_SPEC 含 'dominance_buy'）、:87（断言 LAUNCH_CAUSE_BY_ARM['dominance_buy']=='press'）；press-stockpile.md §3（删除清单无 p88_check.py）；landing.md:43（tools/cw/** 不动）与 :63（P88 符号零残留）。
- 严重度：高

### B4 proofs/p88.md 的处置两文档矛盾：landing 说「原地保留」、详设说「移入归档」
- 位置：landing.md 3.4 文件面；details/press-stockpile.md §3
- 攻击：同一文件两种处置。landing 3.4 文件面：`docs/develop/sr_od/application/currency_war/proofs/p88.md`（文首标注退役指针，**原地保留可溯**）；press-stockpile §3：`proofs/p88.md` **移入归档**（标题标注…；git 历史保全文）。落地 worker 面对互斥指令需自行拍板；「修订后全量同步复查」硬规则（design↔landing 判据同步）在修订中被漏跑。
- 证据：landing.md:58 vs press-stockpile.md:31，两文并读即见。
- 严重度：中

### B5 3.2 完成判据「三件套符号全库零残留（grep 核对）」与文件面互相矛盾：全库 grep 在文件面之外有大量活引用（含 src 内注释与 game 侧文档）
- 位置：landing.md 3.2 完成判据与文件面；details/counter-tables.md §3
- 攻击：判据要求全库 grep 零残留，但按文件面（cw_comps.py / pick_common.py / invest_env.py / invest_strategy.py + 测试镜像）干完活后，以下引用全部残留：src 内注释——`currency_war_config.py:36`（「单一源在 cw_comps.MECHANIC_COUNTERS(经 AFFIX_MECHANIC_MAP 归一)」）、`data/affix_effects_data.py:11`、`obs/cw_briefing_obs.py:54,90,357`、`kernel/cw_affinity_table.py:97`；文档——`docs/game/currency_war/data/competitors.md:15,37,131`、`docs/game/screens/currency_war_briefing.md:33,35`、`docs/game/currency_war/README.md:20`、`strategy-docs/10/13/16/28/29 号稿`。这些文件均不在 3.2 文件面（worker「允许动的文件」之外），判据按字面不可达成；判据也未界定 grep 范围（src only？含 docs？含注释？）——按任一合理界定都过不了或界定本身无文。
- 证据：本轮 grep `LINE_FACTION_TO_MECH|MECHANIC_COUNTERS|AFFIX_MECHANIC_MAP|merged_mechanic_tables|punished_mechs_of` 全库 70 命中，src 消费代码仅 pick_common/invest_env/invest_strategy（详设已覆盖 ✓「消费点唯一」主张成立），其余为上述注释/文档指针；landing.md:30 文件面 vs :35 判据。
- 严重度：中

### B6 正本更新清单不完备，且 10 号稿现存正文明文与 3.2 删除正面冲突
- 位置：landing.md「正本更新清单」；strategy-docs 现行文本
- 攻击：五处漏项——(a) `10_prep_decisions.md:209` 字段存留表明文「MECHANIC_COUNTERS/BOSS 表 | **留**」，3.2 要删 MECHANIC_COUNTERS，清单对该文件只写「form_tiers/sub_tiers 行 → faction_reqs」，删完正本自相矛盾；(b) `13_pick_family.md:72` 点名 `punished_mechs_of`/`LINE_FACTION_TO_MECH`、`29_invest_strategy_screen.md:59`「主派→受克属性映射」、`16_evaluation_tables_reassessment.md:73`「MECHANIC_COUNTERS 机制注册表唯一权威源」——符号删除后全部失指，均不在清单；(c) `sim/sim-power-model.md:65`「词缀：经 AFFIX_MECHANIC_MAP 映射的机制 tag 聚合——映射口径钉死…抽取器在产物头部落映射版本指纹」——表删除后该映射口径声明失去数据源，不在清单；(d) docs/game 侧 competitors.md / currency_war_briefing.md / currency_war/README.md 的 MECHANIC_COUNTERS/AFFIX_MECHANIC_MAP 指针（见 B5）不在清单（清单只有 final_comps/README.md 且预计零改动）；(e) proofs 正本 `p65-promote-candidate-set-reachability.md:36,42`、`p59:44`、`p87`、`p38:19` 以 form_tiers/sub_tiers 为命题符号——3.1 后符号消亡，清单无 proofs 行。
- 证据：各文件行号均本轮 grep 直读；landing.md:105-113 清单逐行核对无上述条目。
- 严重度：中

### B7 transition-library §5 priority 侧 rank 装配式自相矛盾：member_rank_of 的返回值不是「条目注册序」，且多条目同名成员的合并规则未声明
- 位置：details/transition-library.md §5 priority 侧
- 攻击：装配式写「rank 装配 = {n: (1, p) for n, p in member_rank_of(过渡条目).items()}（层值恒 1 = 过渡层，位次 = 条目注册序；现行『候选位次』废止）」。但 `member_rank_of`（cw_comps.py:249-257）= `derive_member_priority` 现算，返回 core 0 / 其余 1 两档序数——p ∈ {0,1}，不是条目注册序（0..3）；按字面装配，四个条目的成员位次几乎全为 0（过渡条目最小字段形态下 shared_chars 多为空）。括号里的「位次 = 条目注册序」与装配式的数据源对不上，两种实现行为不同。另外现行 `_transition_member_ranks`（priority.py:205-223）有「跨多候选对成员 setdefault 取最小位次」的合并规则，新设计的装配式只写了单条目形态——三个过渡候选条目都含某成员时位次取哪条，无文。实现者无法凭此开工。
- 证据：cw_comps.py:243-257（derive_member_priority：`rank = dict.fromkeys(comp.core_chars, 0)` + shared setdefault 1）；priority.py:205-223（现行槽位次 + setdefault 跨对取最小）；transition-library.md:91 原文。
- 严重度：中

### B8 囤货行未覆盖「P2+ 未终局锁定」帧：现行该帧恒空集（保利息缺省），「未锁帧 = 两层候选并集」若按字面适用即未申报的行为大变
- 位置：details/transition-library.md §5 囤货行与局面表；cw_intention.py 现行 hoard_target_set / k_empty_window_fallback
- 攻击：现行 `hoard_target_set` 三形态 = locked（_line_hoard）/ P1（p1_pair/p1_transition 分带）/ **p2plus 恒空集**（「丙分支保利息缺省（空集，不囤）」，cw_intention.py:1151-1153）；P2 入口有终局兜底锁定，但兜底锁帧之前存在未锁短窗。§5 局面表只有三行（双未锁/过渡锁定/终局锁定），「双未锁 = 两层候选并集」未限定 P1——实现者按字面在 P2+ 未锁帧返回并集 = 从「不囤保利息」变「囤」，属未申报行为变化；若维持现行空集则设计无文，同样是自行拍板。连带：`k_empty_window_fallback` 的 p2plus 带（现行 :1194-1195 恒空集）在退役清单只点名 p1_gap/p1_lock_band 两带改造，p2plus 带存废无文。
- 证据：cw_intention.py:1143-1153（P1 分支 + p2plus 空集）、:1184-1195（k_empty_window_fallback 三带）；transition-library.md §5 表（无 P2+ 未锁行）与退役清单（「p1_gap/p1_lock_band 两带」）。
- 严重度：中

### B9 landing 文件面多处路径失真，不满足「文件面真实路径」定稿卡点
- 位置：landing.md 3.3 / 3.4 文件面
- 攻击：四处路径在仓库中不存在或错层——① 3.3「`kernel/mandate_state.py`（字段删除）」：实际 `strategies/impl/mandate_v1/mandate_state.py`，kernel/ 下无此文件；② 3.3「不动的文件：`kernel/cw_engine_facts.py`」：实际 `knowledge/cw_engine_facts.py`（保留声明指错目录，且它正是 B1 的主角）；③ 3.4「`criteria/sell_gate.py`」：实际 `strategies/impl/mandate_v1/sell_gate.py`（不在 criteria/ 子目录）；④ 3.3 括号清单「predicates」实际位于 `mandate_v1/statefn/predicates.py`（偏差一级）。iteration-design 硬规则 4 的卡点要求定稿前逐一核引用路径存在性——未通过。
- 证据：本轮 Test-Path 全量扫描（kernel/mandate_state.py MISSING、kernel/cw_engine_facts.py MISSING、criteria/sell_gate.py MISSING）+ Get-ChildItem 定位（mandate_state 在 mandate_v1/、cw_engine_facts 在 knowledge/、sell_gate 在 mandate_v1/、predicates 在 mandate_v1/statefn/）。
- 严重度：中

### B10 3.1→3.2 之间受克判定的中间态无设计，且恒等性无测试承载：§4 表只写 3.2 终态，§7 快照面不含受克，3.2 判据「活链路 2 条恒等」无测试载体
- 位置：details/faction-priority.md §4 表受克行、§7 快照面；details/counter-tables.md §2/§3；landing.md 3.2 判据
- 攻击：三段合成的缺口——(a) 3.1 删除 form_tiers 字段后，`punished_mechs_of`（pick_common.py:55 读 `set(comp.form_tiers)`）必须改读口才能活到 3.2；faction-priority §4 表受克行的新读法列写的是 3.2 终态（「core_faction_reqs ∩ 直写表（契约 A，counter-tables 详设落地）」），3.1 中间态改成什么（经旧改名层读 core_faction_reqs 键？）两份详设都没写（§2 规则 3 只给 cw_intention.py:544 首键的过渡期例外，未给受克链路）；(b) §7 快照构造六项（成型度/L1/L2/囤货采购集/线距离/投资通道）不含选卡受克减分——受克链路在 3.1 的恒等无断言；(c) counter-tables §3 只写「对应测试随源删除」，没有为活链路 2 条（净化身心/永久创伤）建立新断言，而 landing 3.2 完成判据第一条就是「活链路 2 条行为逐位恒等」、验收凭据「测试名」——测试名无源。行为恒等主张（本迭代最核心的「删的全是死数据」论断）没有任何可执行载体。
- 证据：pick_common.py:55-59（现行读 form_tiers/or 键）；faction-priority.md:75（受克行新读法 = 终态）、:96-98（快照面六项无受克）；counter-tables.md:52（只删测试）；landing.md:34（「活链路 2 条…逐位恒等」）。
- 严重度：中

### B11 过程叙事残留：修订稿正文引用上轮攻击点编号与修订过程，违反写作硬规则 3
- 位置：details/faction-priority.md §7；details/transition-library.md 关键取舍；details/press-stockpile.md 风险兜底
- 攻击：三处——① faction-priority §7「线距离（cw_line_switch，**A2 教训**：原快照面漏此项）」：A2 是上一轮对抗报告的攻击点编号，会话局部标识符（iteration-design §5-3 卡点「本轮/修订后/已改」类措辞即打回；项目 AGENTS §8 注释规范同禁 W 轮次号/rN 类编号），脱离报告的读者无法知道 A2 指什么——应改写为纯语义理由（防御式读静默归零的机理已足以自证）；② transition-library 关键取舍「放弃『退役整个 cw_system_cards 模块』（**本详设初稿口径，对抗审查修正**）」——明写上稿形态与修订过程，正卡点原文；③ press-stockpile「**契约 D 修正**（批次耦合申报）」的「修正」同型。过程住对抗报告与账本、进度只住 README——三处均违。
- 证据：faction-priority.md:97、transition-library.md:107、press-stockpile.md:46 原文。
- 严重度：中

### B12 dominance_buy 删除清单漏 mandate.py 调用点与计数键族：清单只列函数本体与 shop.py 分支，调用段（:958-979）不在任何清单
- 位置：details/press-stockpile.md §1/§3；mandate.py 现行代码
- 攻击：现行 dominance_buy 的发射链有第三段——mandate.py:958-979：`dominance_buy_eligible(...)` 调用（:962）+ `swap_transition_narrow_frame` 消费（:975）+ `_count('press_narrowed_transition_domain_prep_seen')` 计数（:976）+ `_emit_open_shop('dominance_buy')`（:979）。press-stockpile §1 只列「shop.py 序 6 分支（含 _narrow_frame 消费点与 press_narrowed_transition_domain 计数）」与「mandate.dominance_buy_eligible（本体…）」——调用段不在清单；§3「dominance_* 计数键族逐键核对」也没有给出键清单（press_narrowed_transition_domain_prep_seen、press_narrowed_transition_domain（shop.py:2155-2157）等键的存废未逐键裁定）。对照 transition-library「退役对象（决策层，逐符号）」的粒度标准，本篇删除清单粒度不齐，worker 照单删函数不删调用点 = 炸。
- 证据：mandate.py:958-979（调用段）、:676-680（PRESS_NARROWED_ARMS 独苗 ✓ 该主张属实）；shop.py:2155-2157（press_narrowed_transition_domain 计数）；press-stockpile.md:18-20 清单原文。
- 严重度：中

### B13 3.5a/3.5b 完成判据无量化阈值：「恶化」「基线方差内」均无定义，验收不可独立执行
- 位置：landing.md 3.5a / 3.5b
- 攻击：3.5a 判据「无席位周转恶化；恶化即回滚 3.3」——「恶化」无阈值（周转率降多少算恶化？多少局样本？）；3.5b「D 帧买入手数变化与让位频率对照（基线方差内 = 通过）」——「方差」指什么的方差（跨局方差？单指标方差？）、几倍 σ 内算通过，均无定义；两轮对照的模拟批次规模（多少局）也未写。判据依赖 reviewer 主观裁量，不可独立验证，违反「阶段可验收性」（iteration-design §3.1 判据可验证）。行为批的回滚口径（git revert）系于此判据——判据不可执行 = 回滚决策无据。
- 证据：landing.md:77（3.5a 判据原文）、:89（3.5b「基线方差内 = 通过」）。
- 严重度：中

### B14 design §0 状态字段停留在「草案」，与 README 进度（首轮收敛、待复审）不同步
- 位置：design.md §0；README.md 进度节
- 攻击：生命周期为草案 → 对抗审中 → 定稿，当前真实状态是二次对抗审中（README 自述「对抗修订稿…待复审确认攻击收敛后定稿」），design §0 状态仍写「草案」——状态由总纲 §0 表达的机制未随修订同步。硬规则 4 全量同步复查的轻症。
- 证据：design.md:6（「状态：草案」）；README.md:12-13。
- 严重度：低

### B15 表述级不精确一组（各有一句可改的实据）
- 位置：design.md 契约 B；details/counter-tables.md §1；details/transition-library.md §1 条目表
- 攻击：① 契约 B「过渡条目…羁绊要求只填 faction_reqs（**多数**条目仅档 0）」——条目表 4/4 全部仅档 0，「多数」弱化了事实；② counter-tables §1 新表 `AFFIX_COUNTERS_FACTIONS` 未声明宿主文件（从 landing 3.2「pick_common.py（新表+判定）」反推，详设自身不可解析）；③ 希儿条目 need_star 注「（star_goal 迁移）」——SystemCard.star_goal 属数据层全量保留（不动），过渡条目 need_star 与它同值并存，实为复制非迁移，「迁移」措辞掩盖了同值双源形态。
- 证据：transition-library.md:52-57（四条目 faction_reqs 档 0 列全空 or_reqs 之外的档）；counter-tables.md:14-22（无宿主声明）；cw_system_cards.py:96,107,116,125,134（star_goal 数据层在）。
- 严重度：低

### B16 faction-priority §2 规则 1「档 0 空 → 成型度恒 0（与现行 form_tiers={} 语义一致）」在 required_deployed 非空形态下与现行不一致
- 位置：details/faction-priority.md §2 规则 1
- 攻击：现行 form_progress 的早退条件是三字段合取（form_tiers 空 ∧ or_reqs 空 ∧ required_deployed 空，cw_comps.py:1137-1140）——form_tiers={} 但 required_deployed 非空时，required 逐名 0/1 分支仍计均值；新规则「档 0 空 → 恒 0」会把 required 分支一并归 0。现库 21 线与 4 条过渡条目均无此形态（反甲白厄 form_tiers={} 且 required 空），迁移恒等不受影响，但「与现行语义一致」的等价主张对该形态不成立，属语义规则边界声明不完备（新校验 or_reqs ⊆ 档 0 已覆盖 or_reqs 维，required_deployed 维无对应约束）。
- 证据：cw_comps.py:1137-1140,1160-1162（早退三合取 + required 分支）；faction-priority.md:32（规则 1 原文）。
- 严重度：低

### B17 过渡候选机器的重开级方向过滤消失未列入行为变化申报；周边符号存废未裁定一组
- 位置：details/transition-library.md §2/§5/§6；cw_intention.py 现行代码
- 攻击：三项——(a) 现行候选空间有词缀/boss 重开级排除（`_pair_restart_dead`：全线重开级的体系对不入 p1_pair_space，cw_intention.py:550-570,598），新候选机器 = 纯成员持有计分，无重开级过滤；§2 只写了「受克面由 counter-tables 直写表覆盖」（选卡减分维），重开级方向排除的消失不在 §6 四条申报内（§6 第 1 条「开局采购方向」只笼统覆盖方向变化）；(b) `seele_system_formed`/`_SEELE_SYSTEM_KEY` 在 deploy_search:362 与 TRANSITION_TRAITS 并列消费（希儿系单卡二元判据），退役清单只列 TRANSITION_TRAITS 单键组分支，希儿改用 or_reqs/required_deployed 后该消费的处置无文（本体属数据层保留？部署消费删？）；(c) `cw_line_facts.framework_members`/`FRAMEWORK_FACTIONS` 的活消费 = cw_recipe（整删）+ flow.py:614-657（随 :610/:651 读点删除），3.3 后成孤儿死代码，退役清单未裁定其存废；`schema.py:406 sess_framework`（transition_framework 的遥测镜像字段，cw_decision_trace.py:123 引用）同样无处置声明。
- 证据：cw_intention.py:550-599（_pair_restart_dead + alive 过滤）；deploy_search.py:362；grep framework_members/FRAMEWORK_FACTIONS 全部命中（cw_recipe/flow/cw_line_facts/cw_transition 注释）；schema.py:406 + cw_decision_trace.py:123。
- 严重度：低

## 收敛判定建议

**不收敛（打回修订）。** 本轮独立核验下，文档的可信面与失守面同样清晰：

**可信面（核验属实，不再重复攻击）**：21 套 COMP_LIBRARY 计数、克制三件套行数（26 键/12 行/3 对）与「活链路仅 2 条」求交分析、`_faction_hit_bonus` 三层无副档分支、`all_factions` 不含副档、tuple 形态零使用、`cw_intention.py:544` 首键读法、`getattr` 防御式读静默归零机理、sub_tiers 消费 5 处、`FACTIONS.tiers[0]` 数值（仙舟 3/DOT 2/列车 2/量 2/贝 2）、SEELE_OR_REQS 逐字一致、`_CORE_TRIO`/star_goal 数值、committed_authority 行号与序②、hoard/k_empty_window 行号与死锁环 docstring、shop.py:1893 注释原文、s77091 docstring、PRESS_NARROWED_ARMS 独苗、p88/合约/sell_gate 行号、受克调用点四行号、G1b/_engines_count/P24 保留链——主张与代码逐一对得上，第一手核验功夫扎实。

**失守面**：三个高危全部集中在「保留边界/跨详设契约没有经过同样的全库核实」——B1（p65_check 双炸 + 保留理由失实）、B2（契约 D 的名单源在两份详设间漂移）、B3（p88_check 被 3.4 炸 + 与 3.3 保留声明冲突）同根：**删除面与保留面各自做过、但互不对账**。修订建议按同族根治：对每个退役符号与每个「不动」声明做一次交叉全库 grep（含 tools/、docs/game、strategy-docs、proofs、注释），把结果逐文件归行进 §4 表/退役清单/正本清单；契约 D 补 k_members 的精确读口（变量名 + 合并式）；p88.md 处置二选一；受克链路补 3.1 中间态与恒等断言载体；3.5 判据补量化阈值与批次规模；清掉 A2/初稿口径类过程叙事；修正四处文件路径。修订后建议第三轮复审只核上述各点的落文，不再全面重攻。

高中低分布：高 3（B1/B2/B3）、中 10（B4–B13）、低 4（B14–B17），共 17 点。
