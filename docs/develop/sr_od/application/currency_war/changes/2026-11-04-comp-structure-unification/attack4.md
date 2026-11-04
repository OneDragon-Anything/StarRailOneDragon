# 对抗审查报告·第四轮（核一·无前提）

> 审查对象：本目录 7 份文档（README / design / 四份详设 / landing），对码基准 = 仓库现行代码（src、sr-od-test、tools/cw、docs）。
> 方法：无前提自选攻击面——事实主张逐条对码（符号/行号/数值/路径）、删除面与保留面的全库消费核对、判据换轴类改动的连带完整性、落地页可执行性、术语表合规。
> 侧漏披露：目录级全仓 grep（搜 `LAUNCH_CAUSE_BY_ARM`）时结果意外混入了 attack.md / attack2.md 的匹配行；按铁律未将其内容作为任何依据，本报告全部发现均来自下述独立取证。
> 大量事实主张核验通过不逐条罗列（三张表键数 12/27/3 对、活链路 2 行、费段解锁真值 lv1-3/lv4/lv5/lv7、角色费用七条、FACTIONS 判据档 仙舟3/DOT2/列车2、star_goal 2★/3★、RUST_AFFIX_NAME 消费方、P24_VALIDATION.md:31、ab_judge G1b、shop.py:1893 注释、mandate.py:683/:958-979/:644-649、invest_env:337,347 / invest_strategy:281,338、priority.py:164-165、deploy_search TRANSITION_TRAITS 四处、flow.py:610,651、schema.py:406/:466、cw_plugins:17/:115/:118、cw_bridge_pool:7、p88_check.py:34/:87、test_dead_stock_pair:187-195、docs/game 4 处引用、strategy-docs 各篇与 comp-definition.md 均存在且内容相符）。以下只列发现。

## 攻击点清单

### D1 判据换轴裁定注钉死「三处」，全库实际按位面开闭过渡机制的消费点至少还有四处，且详设内部两套口径互斥
- 位置：details/transition-library.md §5 生命周期裁定注（「现行三处……统一换轴为读终局锁定态：① priority 的 recipe_members 判窗；② protection.py 保护集的整域关闭；③ hoard_target_set 的位面分支」）；§2/§5 部署圈人/囤货各节；§7 申报 6
- 攻击：`grep plane2_started` 全库逐点归类后，「按位面判定过渡机制开关」的消费点远不止三处——
  1. **sell_candidates.py:219**（`if not plane2_started_of(gs):` 过渡候选并集进卖出侧线内身份集）——行内注释明写「与 priority 装配/买面同口径……进位面 2 即退出，锁定不是退出条件，P1 锁定局照收」。这是与①②③完全同族的第四处换轴对象，详设任何章节没有它的改造内容；landing 3.3 文件面虽列了 sell_candidates.py，但只有「接入改造与键域改造」六个字，worker 无法据此知道这一处判窗要不要跟着换轴。
  2. **deploy_search.py:985**（`plane1 = not plane2_started_of(gs)` → :987 p1_pair 进圈人域、:989 未锁且非 P1 走终局候选）——§5 部署圈人节只说「段 1 圈人域 P1 = 过渡候选/锁定条目的羁绊骨架（与终局锁定窗同构）」，「与终局锁定窗同构」未定义，未说明 :985 的位面判定换不换轴；若不换轴，「位面 2 且未终局锁定」的帧圈人域没有过渡贡献，与 §7.6 申报的「照常活跃」不齐；若换轴，这就是裁定注清单外的第四处特判。
  3. **shop.py:883**（`if _p2_started:` 锁定态买面装配：P1 锁定局 = 锁定线 ∪ 过渡候选并集，P2 起 = 锁定线单源）与 **shop.py:865**（k 空窗回退的 P2+ 门）——总纲契约 D 承认「该装配在 3.3 被改」，但改什么没说；这两处位面判定是否换轴为终局锁定态，详设零交代。
  4. **flow.py:223-233**（`if not plane2_started_of(state): update_p1_recipe(...) else: clear_p1_recipe(...)` + 过渡锁定槽同点清空）——§2 只说「调用挂点 = 现行 update_p1_recipe 的调用位点原位替换……挂点不变」，没说这个 if/else 位面守卫的去向：保留守卫则位面 2 未终局锁定帧的过渡候选状态冻结、与 §7.6「照常活跃」矛盾；删守卫则它是换轴第四处而裁定注说「三处是同一次判据换轴，非三条特判」。两头堵。
- 证据：上述五行号实码；§5 保护表首行「双未锁（**任意位面**）| 过渡候选条目成员并集」与 §7.6「位面 2 及以后、终局锁定前的帧……照常活跃（保护/囤货按过渡层状态贡献）」是全域换轴口径，与裁定注「三处」清单口径互斥——同一份详设给出两个适用范围。
- 严重度：高（核心裁定的连带清单不完整 + 内部口径互斥，实现者对至少四处消费点无法凭文档裁决，直接违「实现者无需再设计」定稿门槛）

### D2 「量子熄火对希儿在现行登记是一般怕档非不可玩级」与代码相反，支撑的「交集为空/零行为」结论连锁坍塌
- 位置：details/transition-library.md §2 计分节（「生成规则 = cw_affinity_table 不可玩级登记行的羁绊键投影……如实声明：**当前登记与四条目档 0 键交集为空**（量子熄火对希儿在现行登记是一般怕档非不可玩级；……）——本面为登记更新预留，当前零行为属预期」）
- 攻击：对码 cw_affinity_table.py:104-118——希儿量子线的 `'量子熄火': AffixStance(score=RESTART_PENALTY, note='final_seele_quantum「重开级」;量子同频被禁=核心失效')`。按详设自己在同节定义的映射（「不可玩级……对应现行克制登记里的『重开级』」）与表内常量注释（:19「RESTART_PENALTY(与重开级同档)」），量子熄火对希儿 = **不可玩级**；「一般怕档」（FEAR_PENALTY，−150）的是命运圣杯红A 行的量子熄火（:139）。三重连锁坍塌：① 该句事实主张为假；②「当前登记与四条目档 0 键交集为空」为假——希儿量子线重开级词缀族（量子熄火/丢失幸运/免死金牌/极速制冷/以人为本）按生成规则投影出的羁绊键含「量子同频」，而希儿引擎条目档 0 = {量子同频: 2, 贝洛伯格: 2}，交集非空；③「当前零行为属预期」为假——3.3 落地后开局简报观察到位面 1 词缀「量子熄火」时希儿条目将不进候选，这是真实行为，而 §7 行为变化申报六条中没有这一条。
- 证据：cw_affinity_table.py:108-110（希儿线量子熄火 = RESTART_PENALTY）、:106 注释（「重开级:量子熄火/丢失幸运/免死金牌/极速制冷/以人为本」）、:139（FEAR_PENALTY 的是圣杯行）；transition-library.md §1 条目表希儿引擎档 0 键。
- 严重度：高（事实主张对码失败；行为验收基线错误——按「零行为属预期」做实机首局观察会把正确行为当回归，或反向）

### D3 「配方开局面读口（session_scope.py:395-412）删除」的连带消费面未盘点：direction_comp_of 有九处在册消费点，替代方案只给了部署一个侧
- 位置：details/transition-library.md「退役符号集中清单」行「配方开局面读口（session_scope.py:395-412）| session_scope.py | 删除」；§5 第四侧
- 攻击：:395-412 正是 `direction_comp_of` 函数本体（def :391），即删的是「现行方向阵容读口」。全库消费点：flow.py:558/:577/:595/:617/:648（pick 族）、entry.py:514/:1166/:1194（无方向判定与成员装配）、shop.py:863（序 1 名单解析，K 名单唯一来源）、decision_payload.py:62——共九处，全部在 3.3 改造清单与详设正文之外。§5 第四侧「部署开局面方向……替代 = 部署搜索直接读方向四层优先现读」只交代了部署开局面这一个消费面的替代；商店 K 名单、flow pick 族、entry 装配读什么、经哪个读口，零交代。按清单字面删除 = 九处 import/调用即断；不删 = 与「grep 清零」判据（清单为唯一依据）冲突。
- 证据：session_scope.py:391-412（函数与行号范围重合）；grep `direction_comp_of` 九处消费实码；清单行为「删除」。
- 严重度：高（删除面/保留面清单与其判据「grep 清零」直接冲突，落地即断链）

### D4 transition_candidates 槽语义改存「条目名」后的语义崩坏面未盘点；_pair_members 列入删除但保留面函数仍在消费
- 位置：details/transition-library.md §2（「候选槽语义改存过渡条目名」）、「退役符号集中清单」（`_pair_members` 删除、`k_empty_window_fallback`「函数保留、分带按 §3/§5 改造」）
- 攻击：槽值从体系对元组换成条目名后，以下四个「清单外」消费点语义当场崩坏或无人认领：
  1. **locked_buy_scope**（cw_intention.py:1260-1301）——锁定帧买侧目标约束基准，`transition_candidates` 槽透传后逐对 `_pair_members` 展开；条目名不是体系键，展开语义崩坏；docstring 自称「该契约的单一实现」，消费域 = 商店线买入判定链。退役清单与详设正文均无处置。
  2. **locked_faction_scope**（cw_intention.py:1426-1467）——evolve 提案/部署围栏消费的体系键版：:1451-1457 对槽值逐元素 `keys.add(sys)`（把槽值当体系键 + SEELE_SYSTEM 特判展开），槽值改条目名后语义崩坏。
  3. **k_empty_window_fallback 的 p1_lock_band 带**（:1187-1193）——现行 = 候选首位经 `p1_pair_candidates_of` + `_pair_members` 展开；该函数本身保留，但 §3 只定义了「候选槽为空的帧」的新回退（见即买并集），「K 空窗但候选槽非空」的 p1_lock_band 形态新行为未定义；且它调用的 `p1_pair_candidates_of`（:602）与 `_pair_members`（:715）——后者在删除清单、前者不在清单也不在保留声明，删除即 NameError，保留则成为体系机器残骸。
  4. **shop.py 冷启动臂 cold_start_buy**（:1616-1633）——触发判据含「过渡候选槽空」(:1627) 与 `_p1_system_support` 三羁绊支持度现算 (:1628-1629)；§3「冷启动买入分支（shop.py _COLD_BOND_KEYS）」指的是另一物（:240 常量），同名异物，cold_start_buy 臂与 新过渡层机器的关系（槽语义变化后触发判据怎么办、支持度链留不留）详设零交代。
- 证据：四个消费点实码（行号如上）；退役符号集中清单无以上任何符号（除 _pair_members 被列删除——与保留函数的消费关系自相矛盾）。
- 严重度：高（3.3 核心改造的盲区：清单既漏删（四个消费点）又错删（_pair_members 被保留面消费），grep 清零判据与保留面声明互相打架）

### D5 faction-priority §4「全部读点」映射表漏 locked_faction_scope:1467（form_tiers∪sub_tiers 直读）——3.1 字段删除即 AttributeError
- 位置：details/faction-priority.md §4（表自称「消费面映射表（全部读点）」）；landing 3.1（「其余消费面以 faction-priority.md §4 表为准」）
- 攻击：全库按属性读与关键字构造两种形态 grep `form_tiers|sub_tiers`，逐点对照 §4 表：src 内唯一不在表内的直读点 = cw_intention.py:1467（locked_faction_scope 锁定帧支 `keys |= set(comp.form_tiers) | set(comp.sub_tiers)`）。§1「form_tiers 与 sub_tiers 字段删除（不留兼容读法）」落地后，该行在锁定帧调用即 AttributeError；landing 3.1 让 worker「以 §4 表为准」→ 按表执行必然漏掉；§7 迁移恒等测试的快照面（成型度/部署 L1/L2/囤货采购集/线距离/受克判定/投资通道）不含 locked_faction_scope 输出，测试网也接不住。（tools/cw/proofs/p65_check.py 同样不在表内，但 landing 3.1 文件面单独点名保活迁移，有兜底，不另立点。）
- 证据：grep 全库 `\.form_tiers|\.sub_tiers|form_tiers=|sub_tiers=` 的完整命中清单与 §4 表逐行比对；cw_intention.py:1467 实码。
- 严重度：高（「全部读点」的完备性主张被证伪 = 定稿门槛未过；后果是 3.1 落地即运行时崩溃）

### D6 新过渡锁定态没有字段级设计；现役槽写端 refresh_transition_locked_systems 的判据换轴未设计；bridge.py 调用点不在 3.3 文件面
- 位置：details/transition-library.md §4（「序② 改读过渡锁定态非空（锁定条目名非空）」）、§6；landing 3.3 文件面
- 攻击：① 「锁定条目名非空」——锁定条目名存在哪个字段、宿主是 IntentionState 还是 StrategyState、写端是谁（候选机器顺带写？独立写端？）全部未定义；§6 只说 sess_p1_pair「写源改过渡层状态（锁定条目名/候选槽）」。② 现役过渡锁定槽 = `transition_locked_systems`（mandate_state.py:434-448，体系键集，frozenset），写端 = protection.py:54-83 `refresh_transition_locked_systems`（判据 = `_p1_system_support` 支持度链 ≥ `P1_PAIR_LOCK_MIN_SUPPORT`，幂等只增），调用点 = bridge.py:247/:284。新判据 = form_progress ≥ 1.0、新语义 = 条目名——该函数怎么改、`_p1_system_support`/`P1_PAIR_LOCK_MIN_SUPPORT` 随之的去留、flow.py:233 现行清空行的改造，详设零交代；§5 裁定注②「protection.py 保护集的整域关闭」所指的「保护集」函数在现行 protection.py 已退役（模块头 :3-6 自述），现役只有万金油名单 + 本写端——裁定注引用的对象名与代码现状错位，worker 需自行考古②到底指哪一行。③ bridge.py 不在 landing 3.3 文件面（文件面只列 protection.py 而未列其唯一调用方）。
- 证据：mandate_state.py:434-448、protection.py:54-83、bridge.py:247/:284、flow.py:233 实码；landing 3.3 文件面清单。
- 严重度：中（两套机器交接的关键状态载体无字段设计 = 语义可由 worker 各自推出多个方案，须回设计修订；含文件面遗漏）

### D7 清空出口前移（位面切换 → 终局锁定写入点）产生的「P1 终局锁定局」行为变化未申报
- 位置：details/transition-library.md §4 交棒、§7 行为变化申报（六条）
- 攻击：现行语义（代码在册）：write_line_lock 的连带面刻意**不含**配方链——session_scope.py:352-355「锁定不辖配方链——过渡候选槽/配方物化链/opening_recipe_comp 键不在本函数连带面(P1 锁定局配方链照常每 game-round 重算,退场清空只在进 P2)」；锁定态买面 P1 锁定局 = 锁定线 ∪ 过渡候选成员并集（shop.py:875-888，含 P1 锁定局专述注释）。新设计把清空出口改到终局锁定写入点 → 终局锁定发生在位面 1 时，过渡候选/囤货过渡带/保护过渡贡献当场清空——P1 锁定局的买面、卖免面（sell_line_membership 的过渡支「P1 锁定局照收」）、囤货从现行「照常贡献」变为「立即消失」。§7 六条申报只覆盖「位面 2 及以后、终局锁定前」的帧（申报 6），P1 终局锁定局这一形态的行为差没有申报，也没有显式声明「该形态现行不可达」豁免。
- 证据：session_scope.py:352-355、shop.py:875-888、sell_candidates.py:188-191 注释（「锁定不是退出条件，P1 锁定局照收」）实码；§7 申报清单原文。
- 严重度：中（行为申报面不完整；即便现行 line_select 锁定判据使 P1 锁定局多数局不可达，在册代码与在册注释仍把它当在役语义维护，申报义务不因可达性存疑而免除——或者应在文档里显式裁定该形态不可达）

### D8 landing 文件面两处路径不存在；3.3 文件面遗漏多个含退役符号消费点的文件
- 位置：landing.md 3.4 文件面、counter-tables.md §5 + landing 3.2 文件面、landing 3.3 文件面
- 攻击：① landing 3.4 文件面写 `strategies/impl/mandate_v1/criteria/sell_gate.py`——该路径不存在（criteria/ 目录下无此文件）；真实位置 = `strategies/impl/mandate_v1/sell_gate.py`（:131 `'dominance_buy': 'press'` 内容属实；p88_check.py:16 引用的也是 mandate_v1 直下路径）。文件面是「本阶段允许动的文件」清单，路径假 = worker 无法按清单定位与申报。② counter-tables §5 与 landing 3.2 写 `src/sr_od/application/currency_war/config/currency_war_config.py`——不存在；真实 = `src/sr_od/application/currency_war/currency_war_config.py`（:36-37 确有三张表注释，「随手清理」主张的内容本身属实）。③ 3.3 文件面遗漏：bridge.py（protection 写端调用 ×2，见 D6）、entry.py（direction_comp_of ×3 + k_members 装配，见 D3）、cw_deploy_logic.py（:199 p1_pair 分支②注释悬空 + swap_bond_gate_domain_of 谓词与 3.4 耦合）、cw_registry.py（:318-321 `vd_p1_pair_enabled` 配置项与 :97/:440/:508 p1_pair/v3_core_names 注释族——配方机器退役后配置项语义悬空）、cw_line_facts.py（:50 `_pair_members` 口径注释、`framework_members` 在 cw_recipe 整模块删除后的消费面变化）。
- 证据：glob/read 证伪两路径 + 真实路径内容核对；上述五文件的消费点实码；landing 3.3 文件面清单原文。
- 严重度：中（硬规则 4「文件面真实路径」违背 ×2；文件面遗漏使派工边界失真——修复成本低但必须修）

### D9 设计稿自身术语合规：替换表词未替换（「正本」「闩」）、「锚」第三义未定义即使用
- 位置：design.md 方案 5（「正本更新阶段做全文件面的违例终扫」）、README.md 进度节（「正本更新:未开始」）、design.md S4（「门控-冻结-封印-再闩三态状态机」）、details/transition-library.md §1（「计分锚」×3）、details/counter-tables.md §2（代码注释「锚缺失帧传空集」）
- 攻击：术语表 §1 核心替换表：「正本」→ 权威版本；「闩」→ 一次性标志位。landing.md:71 已为模板固定节名做了豁免声明（「节名……沿用迭代设计模板固定名，不按术语表替换」），design 方案 5 与 README 的「正本」用法无对应声明——本迭代自设了「黑话清理」义务（方案 5），义务载体文档自身带替换表词。「计分锚」「锚缺失帧」的「锚」是第三义（计分基准/锚点线），不在术语表两条锚义（画面识别义/写稿义）之内，未定义即使用（表内「锚(画面识别义)」为必须替换词，第三义游离在表外）。
- 另附观察（非 7 份文档的错，影响方案 5 可执行性）：terminology.md §0 使用规则的编号引用整体偏移一档——规则 1 引「§2 替换表」实为 §1，规则 2 引「§3 保留词」实为 §2，规则 3 引「§4 保留词与 §5 游戏内容词」实为 §3/§4。按编号援引条款清理时会错位。
- 证据：上述文档行原文 + terminology.md §0/§1 对照。
- 严重度：低（表述级；与自设清理义务存在示范性冲突）

## 收敛判定建议

**不收敛，须修订后再审。**

- 五个高严重度点（D1-D5）集中在本稿两个结构性改动上：判据换轴（D1）与配方机器退役/槽语义换轴（D3/D4/D5），外加一处对码失败的事实主张（D2）。它们都不是点状笔误：行号级事实主张的精确率在本稿已非常高（抽查数十处仅 D2 一处内容性错误、D8 两处路径错误），残留缺陷全部落在「清单完备性」——换轴消费面、删除连带面、槽语义下游——正是多轮修订逐点打补丁后最容易系统性漏掉的面。D1 的内部口径互斥（「三处」vs「任意位面」）说明换轴裁定本身还没收口成单一表述。
- 建议修订优先序：D2（一处事实改写 + 补一条行为申报）→ D1（把换轴适用范围收口成一份全量消费点清单）→ D3/D4/D5（按全库 grep 的消费点逐点补处置）→ D6/D7（补锁定态字段设计与 P1 锁定局申报）→ D8/D9（路径与用词）。
- 修订后复查面建议：`plane2_started`、`transition_candidates`、`direction_comp_of`、`_pair_members`、`form_tiers|sub_tiers`（属性读 + 关键字构造两形态）五个 grep 的全量消费点，逐点在文档中能找到「换轴/删除/改造/保留」四态之一的显式处置——本报告的方法可直接复用。
