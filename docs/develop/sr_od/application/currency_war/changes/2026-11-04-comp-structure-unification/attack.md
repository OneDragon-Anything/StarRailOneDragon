# 对抗审查报告（核一·无前提）

> 审查对象：本迭代 7 份文档（README / design / 4 份详设 / landing）。
> 方法：不预设焦点，逐主张对源码核验（grep + 逐文件读）；会话指针类依据单列。
> 可复核的现状主张大多属实（克制表 12 行/活链路 2 条、三件套符号与所在文件、shop.py:1893 注释原文、
> PRESS_NARROWED_ARMS 独苗、INVEST_SOFT=30、_faction_hit_bonus 无副档分支、all_factions 不含副档、
> derive_member_priority 先例、_CORE_TRIO 名单、proofs/p88.md 存在——均已逐一验证通过）；
> 主要问题集中在**消费面清单不完备**与**过渡机器换装期的语义空洞**。

## 攻击点清单

### A1 3.1 删除 `form_tiers` 字段会当场炸掉 `cw_recipe.py` 与 `pair_target_comp`——消费面映射表与文件面双漏
- 位置：faction-priority.md §1（「不留兼容读法」）+ §4 消费面映射表 + landing.md 3.1 文件面
- 攻击：`Comp.form_tiers` 字段删除后，所有 `Comp(form_tiers=...)` 构造点在 import 期即 TypeError。存在两个映射表之外的构造点。
- 证据：`kernel/cw_recipe.py:43-62` 三处 `Comp(name='过渡·仙舟配方', ..., form_tiers={'仙舟': 3})` 等（模块级静态注册表 `_RECIPES`，import 期求值）；`kernel/cw_intention.py:808` `form_tiers=dict(sorted(tiers.items()))`（`pair_target_comp` 内部，3.3 才退役、3.1 时仍活着）。faction-priority.md §4 表无「配方伪阵容构造」行；landing 3.1 文件面点名约 15 个文件里**没有 cw_recipe.py**；transition-library.md 退役清单（逐符号）也**不含 cw_recipe.py / _RECIPES / decision_target / transition_framework**——该模块既不被 3.1 覆盖、也不被 3.3 认领。
- 严重度：高（阻断定稿）

### A2 `cw_line_switch.py` 防御式读 form_tiers——3.1 后静默行为漂移（线距离恒 0），不在任何清单且恒等测试不覆盖
- 位置：faction-priority.md §4 表 + landing.md 3.1 文件面
- 攻击：`getattr(comp, 'form_tiers', None) or {}` 写法在字段删除后**不报错**：返回空档 → `tier_progress` 恒空 → `line_distance` 恒 0 → `e_rounds` 恒 0.0（语义「已完成」）。线距离/保利息线/证据门的输入面静默归零。
- 证据：`kernel/cw_line_switch.py:102`（tier_progress）、`:158`（e_rounds 遍历档位键）；`:127-132`（prog 空 → distance=0）、`:150-152`（dist<=0 → 0.0）。该文件不在 §4 映射表（无「线距离」行）、不在 landing 3.1 文件面；faction-priority.md §7 迁移恒等测试快照面（成型度/部署 L1L2/采购集/投资分）**不含线距离**，此漂移不会被恒等测试抓住。
- 严重度：高（阻断定稿）

### A3 SYSTEM_CARDS / TRANSITION_TRAITS 的真实消费面远超退役清单；「grep 零残留」判据自相矛盾，且物理上切断结算键与 A/B 判据工具链
- 位置：transition-library.md「现状组件清单（退役对象，逐符号）」+ landing.md 3.3 文件面/完成判据
- 攻击：cw_system_cards.py 头注消费方（「decision_v2/candidates 层 1 目标集换源、体系判定、空窗期买门」）之外，全库 grep 实证消费方还有一批不在退役清单、不在 3.3 文件面的文件；尤其 `engines_count` 是**结算 rung 键**与 **A/B 判据门 G1b** 的单一源，其数据源 SYSTEM_CARDS 被整模块退役后结算侧与判据工具断链——而 3.5 模拟对照自己就要用这套判据工具。
- 证据（grep 实证，各带行号）：
  - `telemetry/cw_win_model.py:27,51`（`_SEELE = SYSTEM_CARDS['seele'].engine_required[0]`，胜率模型）；
  - `strategies/impl/mandate_v1/statefn/predicates.py:239-290`（SYSTEM_CARDS × FACTIONS 派生式，注释自称「TRANSITION_TRAITS 的同注册表派生式」）；
  - `knowledge/cw_engine_facts.py:24-45`（TRANSITION_TRAITS **权威副本** + engines_count 机制事实判据；cw_deploy_logic.py:49-51 注释明示「权威副本 = knowledge/cw_engine_facts.TRANSITION_TRAITS…本副本仅为 sim/旧判据消费点保留」）；
  - `strategies/impl/mandate_v1/protection.py:25,77`（保护集体系键）、`economy_cycle.py:77-97`（经济周期判据）、`shop.py:237-241,1629`（冷启动 `_COLD_BOND_KEYS`）、`deploy_search.py:317,362,763,925`、`cw_intention.py:344,361,379,465,485`（支持度机器）、`telemetry/schema.py:18-39`（ρ 实测体系键域）、`kernel/cw_battle_calib.py:101-113`（`_engines_count` 薄委托 = 结算 rung 单一源，见 proofs/validations/P24_VALIDATION.md:31「结算键 = rung，单一源 cw_battle_calib._settle_rung = _engines_count」）；
  - `tools/cw/ab_judge.py:71-72`（G1b 门「过渡配方达标率(engines_count 口径)」——3.5 的「现行 sim 对照口径」）、`tools/cw/win_model_m1.py:49,114`（rung）、`tools/cw/proofs/p15/p15v2_fit.py:34,58`、`tools/cw/proofs/p65_check.py:39,134,275`。
  - 判据自相矛盾：landing 3.3 要求「`p1_pair`…grep 零残留」，但 `sess_p1_pair` 遥测键（telemetry/schema.py:466）与消费它的 `telemetry/match_archive.py:873,1063` 不在文件面——保留则 grep 非零残留判据永红，删除则文件面漏改。
- 严重度：高（阻断定稿）

### A4 `committed_authority` 序②「p1_pair 非空」的替代语义未定义——定型权威判定悬空
- 位置：transition-library.md §3（锁定/交棒）——缺失面
- 攻击：现行 committed（定型/非双轨）判定 = ①`target_comp` 非空 ∨ ②`p1_pair` 非空（cw_intention.py:1198-1233）；序②删除后，新的「过渡锁定（成型即锁）」是否充当 committed 完全未定义。committed 的消费面是攒息门/双轨买门/装备环境/穿戴计划（docstring 1218「committed_from 消费面(攒息/装备环境/穿戴计划)零变化」+ 缺供给帧保守侧 False 的变异测试）——这是激进/保守分界的权威位，实现者必须自行拍板。
- 证据：`kernel/cw_intention.py:1208`（「② ist.p1_pair 非空——P1 配方锁已立」）、`:1233`；`cw_transition.py:57-58`（「定型权威 = cw_intention.committed_authority…p1_pair 非空」）；transition-library.md 全文无 committed_authority/committed_from 字样。
- 严重度：高（阻断定稿）

### A5 过渡配方物化链（opening_recipe_comp / direction_comp_of / v3_core_names / transition_framework）不在退役清单，「部署开局面恒有最强方向」这条第四侧无替代设计
- 位置：transition-library.md 退役清单 + §4 三侧接线
- 攻击：退役清单列了 `pair_target_comp`（物化器本身），但它的**载体与读端**整条链没被认领：`mandate_state.py:399` `opening_recipe_comp` 字段、`flow.py:245-264` 物化写端（注释「部署开局面恒有最强方向、不随 p1_pair 门控变 None」+ `v3_core_names` 派生）、`session_scope.py:395-412` 配方开局面读口、`shop.py:855-894` direction_comp_of 消费、`mandate_state.py:184` `transition_framework` 字段 + `flow.py:610,651` 读点 + `cw_recipe.py` 整个 decision_target「单一入口」+ 遥测 `sess_framework`（telemetry/schema.py:406）。详设三侧接线只有 priority/囤货/部署圈人——部署**开局面**（现行由物化链供方向）是第四侧，去向未定义。
- 证据：见上行号；transition-library.md「现状组件清单」逐条对照无一项覆盖这些符号。
- 严重度：高（阻断定稿）

### A6 正本更新清单引用不存在的文件 `strategy-docs/02_comp.md`
- 位置：landing.md:92（正本更新清单）
- 攻击：清单第 2 条「`strategy-docs/02_comp.md`（阵容与羁绊口径…）← 3.1」，但 strategy-docs/ 目录实际文件是 `02_mandate_layer.md`，全目录 glob 无 `02_comp.md`。「阵容与羁绊口径」正本真身在哪篇未定位，末阶段「清单清零」无法执行。
- 证据：glob `docs/develop/sr_od/application/currency_war/strategy-docs/*.md` 全量 33 个文件中无 02_comp.md，有 02_mandate_layer.md；同清单其余条目（12_line_and_intention.md / 32_unified_sell_priority.md / README.md）均存在。
- 严重度：高（阻断收尾；迭代文档规范硬规则 4「文件面真实路径」违例）

### A7 过渡候选的冷启动语义未定义：`k_empty_window_fallback` 的 P1 分支（p1_gap/p1_lock_band）删除后开局回退目标悬空，旧死锁环防线无承接口
- 位置：transition-library.md 退役清单（「hoard 的 p1_gap/p1_lock_band 两带」）+ §2（「开局全 0」）+ §4 囤货行
- 攻击：新机器「分数 > 0 才进候选」且「开局全 0」→ 开局候选槽空；现行 K 空窗回退单一源（shop.py 与 cw4/entry.py 共用）的 p1_gap 带 = 四体系引擎件全集，其存在理由就是消「K 空→零买入→支持度永不涨」死锁环（函数 docstring 明示）。详设只说「分带删除」，未定义删除后 P1 K 空窗帧买面回退目标集是什么；若落空集则死锁环动机在新机器下同样成立（持有=计分来源，零买入则持有只靠免费送）。行为申报 1「更保守：先有证据再花钱」是一句趋势描述，不是冷启动判据。附：冷启动臂（2026-11-01-dual-layer-candidates 迭代建的「见即买」义务臂，`shop.py:237 _COLD_BOND_KEYS`）与保护集（protection.py）的体系键域改造同样无着墨。
- 证据：`kernel/cw_intention.py:1156-1195`（k_empty_window_fallback 三带 + 死锁环注释）、`:1143-1150`（hoard_target_set P1 分支）；`shop.py:237-241`。
- 严重度：高（阻断定稿）

### A8 design 说「行为批各自落地各自模拟对照」，landing 3.5 把 3.3+3.4 合成单点对照——总纲↔落地矛盾，回滚口径失去归因能力
- 位置：design.md「落地顺序约束」 vs landing.md 3.5
- 攻击：design 明文「行为批（方案 3、4）**各自落地各自模拟对照**（基线 = 上一阶段收尾态）」；landing 3.5 只有一个对照点（基线 = 3.2 收尾、对照 = 3.4 收尾 = 3.3+3.4 全部叠加）。两批行为变化混在一个差分里，指标恶化时无法归因到过渡库还是富余买入——press-stockpile.md 关键取舍的回滚口径（「恶化即恢复 dominance_buy 通道，git revert 本阶段」）前提是恶化可归因到 3.4，该前提被对照设计否决。3.3/3.4 的完成判据都指向 3.5，等于两阶段的验收都悬在一个不可归因的对照上。
- 证据：design.md §2 末段原文；landing.md 3.5「基线 = 3.2 收尾态…对照 = 3.4 收尾态」+ 3.3 判据「模拟对照见 3.5」。
- 严重度：高（阻断定稿；硬规则 4 design↔landing 失同步）

### A9 过渡锁定的评估域未定义；core_chars（计分输入）与 faction_reqs（成型判据）的关系无一句定义
- 位置：transition-library.md §1（条目表）/§2（计分）/§3（锁定）
- 攻击：①锁定评估对**全部 4 条**还是**候选槽内条目**做？板面凑齐羁绊计数但零点名成员的条目（如板面 2 个列车成员皆非姬子·启行/三月七）fp=1 而计分 0——它不在候选（分数>0 才入），锁不锁？两种答案行为不同且都有道理，设计未裁。②条目表 core_chars 与 faction_reqs 两列独立并列，「持有 core 成员计分」与「羁绊计数成型」交叉而无绑定关系，core_chars 填法口径（点名多少、点什么）无规则——「列车骨架」点 2 人而「仙舟铁三角」点 3 人，规则是什么（引擎件？任意成员？）未写。
- 证据：transition-library.md §2「持有过渡条目 core 成员每名 +1…开局全 0」、§3「form_progress(过渡条目, 板面) >= 1.0 即锁（每 game-round 评估）」——评估域无主语；§1 表格两列并立。
- 严重度：中（须修订）

### A10 条目 faction_reqs 数值双源冲突未裁：列车骨架取「卡判据 2」而现行配方机器是「4」，且表内两条目取值口径互相矛盾
- 位置：transition-library.md §1 条目表
- 攻击：现行存在两个过渡知识源且数值不同——体系卡判据（`_TRAIN_TIER = FACTIONS['列车同行'].tiers[0] = 2`，cw_system_cards.py:50）与配方伪阵容（`form_tiers={'列车同行': 4}`，cw_recipe.py:54）。详设表取 2 但未声明对 4 的取舍；同表「希儿引擎」又取终局静态套的 `{量子同频: 4, 贝洛伯格: 2}`（cw_comps.py:522）而非卡/配方口径的 3+2（cw_recipe.py:61）——同表内一条取卡判据、一条取终局档，口径不一致无解释。「落地批数值精校」是兜底话术不是设计（「实现者无需再设计」要求口径钉死，数值可后精校）。
- 证据：cw_system_cards.py:48-50、cw_recipe.py:54,61、cw_comps.py:522 与详设表逐值对照。
- 严重度：中（须修订）

### A11 counter-tables「消费点调用形态不变」误导：`punished_mechs_of` 删除后 invest_env / invest_strategy 两处调用必须改写，参数语义整个换轴
- 位置：counter-tables.md §2 末行 + landing.md 3.2 文件面「消费点（invest 相关调用形态核对）」
- 攻击：现行调用形态是 `punished = punished_mechs_of(anchor)` → `counter_pick_penalty(_opt, punished)`（第二参 = **机制属性集**，值域 {DoT,减益,燃血}）。新签名第二参换为 `core_factions`（**羁绊键集**）。删掉 punished_mechs_of 后两文件的调用必须改写为传 `frozenset(anchor.core_faction_reqs)`——「调用形态不变」若按字面理解（照抄旧调用）= 把机制名当羁绊名求交的静默语义错。设计应写明改写式而非「不变/核对」。
- 证据：`invest_env.py:337,347`、`invest_strategy.py:281,338`（现行调用）；pick_common.py:50-59（旧第二参语义）vs counter-tables.md §2 伪代码新签名。
- 严重度：中（须修订）

### A12 priority 侧 member_rank 映射不可实现：`member_rank_of` 返回 `dict[str, int]`，塞不进 `dict[str, tuple[int, int]]`
- 位置：transition-library.md §4「档内 (层, 位次) 的层值：过渡条目成员 rank 由 member_rank_of(过渡条目) 生成（core=0），不再用候选位次」
- 攻击：现行 `member_rank: dict[str, tuple[int, int]]`（priority.py:167-178：终局成员 (0, 线内序数)、过渡成员 (1, 候选位次)、重叠归终局）。`member_rank_of` 返回单值 0/1（cw_comps.py:249-257）——映射到二元组哪一维？过渡非 core 成员落哪层？与终局 (0, x) 同层后「重叠成员归终局」规则是否保留？均未定义。
- 证据：priority.py:167-178 字段契约 vs cw_comps.py:249-257 返回类型。
- 严重度：中（须修订）

### A13 过渡条目 need_star 字段的消费端未定义：不进表则为死字段，进表则改现行「过渡成员统一缺省 1」规则且未申报
- 位置：transition-library.md §1（need_star 列）+ §4（priority 侧）
- 攻击：条目表填 need_star（「仙舟铁三角三人各 2★（体系卡 star_goal 迁移）」「希儿 3★」），但现行 priority 契约明文「过渡候选成员不入 need_star 表（统一缺省 1）」（priority.py:164-165）。§4 三侧接线未提 need_star_by_member 的口径变化——字段填了没人读（死字段），或要改「统一 1」规则（未申报的行为变化），二选一无答案。
- 证据：transition-library.md §1 表 need_star 列；priority.py:160-166。
- 严重度：中（须修订）

### A14 3.4 文件面漏 sell_gate.py（'dominance_buy' 映射键）与 contracts.py（dominance_buy 契约键所在文件）
- 位置：press-stockpile.md 方案 §1 + landing.md 3.4 文件面
- 攻击：方案 §1 点名删「`dominance_buy` 契约键」，但该键宿主 `criteria/contracts.py:236` 不在 3.4 文件面（文件面 = shop.py/mandate.py/cw_deploy_logic.py/proofs/p88.md/测试镜像）；`sell_gate.py:131` `'dominance_buy': 'press'` 映射键（LAUNCH_CAUSE_BY_ARM 域内）同样不在——删通道后成死键，且闭集对账测试（test_sell_window_launch.py）可能连锁红。「逐键核对」写了但文件面没兜住执行边界。
- 证据：contracts.py:236、sell_gate.py:131 vs landing 3.4 文件面清单。
- 严重度：中（须修订）

### A15 迁移恒等测试的快照载体与构造方式未定义
- 位置：faction-priority.md §7
- 攻击：「迁移前对 21 套全量快照：多板面状态下成型度、部署评分 L1/L2、囤货采购集、投资通道逐卡加分——迁移后逐位比对」——①「多板面状态」具体哪些板面 fixture？②快照存哪（测试仓 fixture / 生成脚本）？③迁移后旧公式已删，期望值如何重放（迁移前生成入库？双写对照？）。worker 拿到的是目标不是做法，快照构造是本测试的核心设计，缺位 = 实现者需再设计。
- 证据：faction-priority.md §7 全文（仅一句「测试面挂 test_faction_derivation_locks.py 同域」定了文件归宿）。
- 严重度：中（须修订）

### A16 候选机器模块选址是「或」字待定——硬规则 2「看情况/待定 = 未定稿」违例
- 位置：transition-library.md §2 标题「候选机器（与终局同构，**新函数 cw_intention 或独立模块**）」
- 攻击：模块选址影响 import 方向、测试镜像路径、依赖边——这是语义选择，设计文档用「或」留给落地批即未定稿。
- 证据：transition-library.md §2 标题原文。
- 严重度：中（须修订）

### A17 3.4 声明「契约 D 独立、仅依赖 3.1」，但 M6 兜底带读的「线内成员」名单源在 3.3 被改——批次耦合未声明
- 位置：design.md 契约 D + landing.md 3.4（「依赖：3.1（无结构依赖，排后避免同文件冲突）」）+ press-stockpile.md §2
- 攻击：M6 兜底带候选 =「与线内成员零重叠的 1★」——k_members/线内名单在现行 = 双层名单（锁定线 ∪ 过渡候选并集，priority.py:148-155），3.3 把它整个改掉。若 3.4 按现行名单实现（3.4 依赖只有 3.1，可不等 3.3），3.3 落地后兜底带行为二次变化且无对照批次覆盖（3.5 对照点只有 3.2→3.4）。两行为批的真实耦合被「独立」声明掩盖。
- 证据：design.md 契约 D「仅依赖统一让位序现行契约…不依赖本迭代任何新结构」；priority.py:148-155（现行双层名单）；landing 3.4 依赖仅 3.1。
- 严重度：中（须修订）

### A18 「p1_gap/p1_lock_band 两带（hoard_target_set P1 分支）」归属描述与代码不符——两带实际住在 k_empty_window_fallback
- 位置：transition-library.md 退役清单「hoard 的 p1_gap/p1_lock_band 两带（`hoard_target_set` P1 分支）」
- 攻击：p1_gap/p1_lock_band 是 `k_empty_window_fallback` 的带 token（cw_intention.py:1169-1193）；`hoard_target_set` 的 P1 分支分带叫 p1_pair/p1_transition（:1143-1150）。括注指错函数，worker 按图索骥改错地方（p1_gap 带内部调 hoard_target_set，两函数相邻但角色不同）。
- 证据：cw_intention.py:1143-1150 vs :1156-1193。
- 严重度：低（表述级）

### A19 faction-priority 语义规则 3「档内无次序（键书写顺序零语义）」与 §4 表「过渡期保留读 core_faction_reqs 首键」自相矛盾，未标注临时例外
- 位置：faction-priority.md §2 规则 3 vs §4 表「面板主羁绊名」行
- 攻击：规则 3 宣称键序零语义是「全行为定义」，同页 §4 又让 cw_intention 首键消费（cw_intention.py:544 `next(iter(c.form_tiers), '')`）在 3.1→3.3 过渡期继续依赖首键（= 依赖迁移保持插入序）。行为面自洽（迁移规则 `{0: form_tiers}` 确实保序），但语义声明打架：读者无法知道「键序零语义」是立即生效还是 3.3 后生效。
- 证据：faction-priority.md §2/§4 对照；cw_intention.py:544。
- 严重度：低（表述级）

### A20 landing 3.1 文件面掺入不可解析路径（sim/features）与无对应消费的点名文件；README「阶段 0/5」口径与 landing 阶段数（5+末阶段）不一致
- 位置：landing.md 3.1 文件面 + README.md:14
- 攻击：①「sim/features」在本仓 src 下无法定位（全库 grep form_tiers/sub_tiers/.factions/.all_factions 无此路径命中；sim 工具实际在 tools/cw/）；文件面路径应可解析。②README「落地:阶段 0/5 done」而 landing 有 3.1-3.5 加固定末阶段共 6 个小节——计数口径未明示。
- 证据：grep 结果（无 sim/features 命中）；landing.md 小节计数。
- 严重度：低（表述级）

### A21 校验 1「与 _line_hoard 现行口径一致」的类比不成立
- 位置：faction-priority.md §5 校验 1「全部羁绊名 ∈ FACTIONS 注册表键（factions ∪ flows 全集口径，与 _line_hoard 现行口径一致）」
- 攻击：`_line_hoard` 的口径是「档位键 ∩ 每角色 (factions ∪ flows) 非空 → 收成员」（cw_intention.py:1088），**不查 FACTIONS 注册表**；「∈ FACTIONS 键」是另一个判定。两集合（FACTIONS 32 键 vs 角色侧阵营/流派并集）若有差集，校验会误判或漏判。「口径一致」表述失准，白名单本身没错。
- 证据：cw_intention.py:1078-1089 vs cw_factions.py 键集。
- 严重度：低（表述级）

### A22 会话指针类依据清单（可复核性盘点）
- 位置：多文件
- 攻击：以下依据标注无法独立复核：①design.md §1 S1「2026-11-04 会话逐线验证：21 线仅 2 线行为受键序影响」——纯会话背书的现状数字，无日志/数据指针；②faction-priority.md「现状约束（2026-11-04 会话逐点核实）」——其中消费面数字（10+/5 处）已由本审查复核属实（实际 form_tiers 消费约 30+ 行、sub_tiers 消费约 8 行，量级方向一致），但标注本身不可复核；③press-stockpile.md「s77091 事故真凶 = 死库存对…已根治」——事故归因叙事无持久指针（防线符号存在已核实：mandate.py:614）；④各篇「用户 2026-11-04 拍板/裁定」×4 处——用户拍板指针属迭代目标追溯合法形态（design §0 同式），不计违规。①③建议补遥测 run id/复盘文档指针或降格为纯语义描述；因「21 线仅 2 线」若错会被迁移恒等测试兜住（键序行为面在 3.1 全量快照内），实际风险受控。
- 证据：各文档原文位置如上；对照 iteration-design.md 硬规则 1「依据 = 来源文档+节 / 直调数据表 / 已证命题」。
- 严重度：低（表述级；不阻断）

## 收敛判定建议

**必须修才能定稿（高 8 条）**：
- A1/A2/A5 同根：3.1/3.3 的消费面清单系统性不全。修法方向：对 `form_tiers|sub_tiers|factions|all_factions|SYSTEM_CARDS|TRANSITION_TRAITS|p1_pair|pair_target_comp|opening_recipe_comp|transition_framework` 做一次全库 grep 并把结果逐文件归行进 faction-priority §4 表、transition-library 退役清单与 landing 文件面（cw_recipe.py / cw_line_switch.py / cw_engine_facts.py / predicates.py / protection.py / economy_cycle.py / cw_win_model.py / cw_battle_calib.py / match_archive.py / tools/cw/* 至少要有「保留 or 退役 or 改造」的逐符号裁定）。
- A3 的「grep 零残留」判据需按符号级白名单重写（区分删除符号与保留键名如 sess_p1_pair），并回答 rung/G1b 判据链在 SYSTEM_CARDS 退役后的口径。
- A4/A7 是真正的设计空洞（committed 权威替代、冷启动回退替代），须在详设补节钉死，不能靠 worker 拍板。
- A6 一行修正即可（定位真实正本篇目），但必须修——末阶段判据依赖它。
- A8 须 design↔landing 二选一对齐：要么 landing 补 3.3 单独对照点，要么 design 改为「合并对照 + 归因手段声明」。

**中危 9 条（A9-A17）**：定稿前应逐条补语义（评估域/数值口径/改写式/类型映射/消费端/文件面/测试构造/选址/耦合申报）；其中 A16（「或」字待定）是一句话可修的硬规则违例，优先处理。

**低危 5 条（A18-A22）**：表述级，可随高/中危修订顺手改；A22 中「21 线仅 2 线」与「s77091 真凶」两处建议补持久指针，其余可带病定稿。

**另记（不计攻击点）**：正本更新清单含「skill sr-od-dev-currency-war/references/comp-definition.md ← 3.1/3.3」，该 skill 不在本仓 `skills/`（glob 零命中），公共仓预期路径 `D:\code\workspace\OneDragon-Skills\skills\sr-od-dev-currency-war` 亦不存在；且个人本地指令禁止直接改公共仓 skill 本体。执行该清单条目前须先定位 skill 真身与修改权限，建议在清单内加注。
