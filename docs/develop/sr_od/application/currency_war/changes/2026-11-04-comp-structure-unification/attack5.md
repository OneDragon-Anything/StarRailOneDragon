# 对抗审查报告·第五轮（核一·无前提 + 实现者走查）

> 审查对象：README / design / details×4 / landing（修订稿，四轮迭代后版本）。
> 方法：无前提攻击——全部攻击点由本轮独立对码取证（src / tools / sr-od-test / strategy-docs / docs-game 直读 + 定向 grep），不以任何前轮报告为依据。
>
> **侧泄漏披露（规范义务）**：本轮一次目录级 grep（`docs/develop/sr_od/application/currency_war` 全树搜 `form_tiers`）的返回中侧漏了本目录 attack.md～attack4.md 的若干匹配行。按「铁律」该等匹配行一律不作为依据；下文 E1–E14 的每一项证据均为泄漏发生**前后**对源码 / 测试仓 / 权威文档的独立直读与独立 grep，可复核、与前轮报告无关。

## 攻击点清单

### E1 契约 A 直写表的键强度唯一形态承载不了「同词缀跨羁绊分级」——两条基线行全部与自家投影规则撞键
- 位置：details/counter-tables.md §1（形态演进声明、两行基线表）；details/transition-library.md §2（`dict[str, tuple[list[str], str]]` 形态 + 「重开级登记的羁绊键投影」生成规则）。
- 攻击：3.2 基线把 `净化身心: ['持续伤害','减益']`、`永久创伤: ['燃血']` 登记为**一般克制级**；3.3 投影规则把亲和表全部 `score = RESTART_PENALTY` 行投影为**不可玩级**。而现行重开级登记恰好覆盖这两个词缀：`'DOT队': {'净化身心': RESTART_PENALTY}`（cw_affinity_table.py:177-179）投影出 `净化身心 → ['持续伤害'] 不可玩级`；`'万敌单C': {'永久创伤': RESTART_PENALTY}`（:96-100）投影出 `永久创伤 → ['夜之半神','燃血'] 不可玩级`。同一词缀键在形态里只有一个强度槽：投影覆盖则 3.2 基线的『减益』条目从选卡减分值域消失（3.2 已验恒等的活链路行为面被改）；基线保留则违反自家投影规则、且『净化身心局 DOT 方向别玩』的现行重开级防线在过渡层丢失（廉价 DOT 条目照常进候选——现行虽因专家桑博DOT 无行不触发整对排除，但 DOT队线分 −100000 + dot2 卡 `affix_fears=['净化身心']` 双重压制是现行实况，新机器无对应物）。详设只申报了量子熄火一处交集（§2「现行登记与四条目档 0 键有交集：量子熄火 × 希儿量子系线」），对两条基线行自身的撞键只字未提，也未给合并/取舍规则——§7 行为申报 5 的「更精确而非更宽」论证因此失据。
- 证据：cw_affinity_table.py:174-180（DOT队 净化身心 RESTART_PENALTY）、:96-100（万敌 永久创伤 RESTART_PENALTY）、:104-118（希儿量子 量子熄火等重开级，即详设唯一申报的交集）、:139（量子熄火×圣杯 FEAR，与详设 ":139" 一致）；cw_system_cards.py:137（dot2 `affix_fears=['量子熄火'/'净化身心']`，:119）；cw_intention.py:550-570（`_pair_restart_dead` 全线重开才排除）；counter-tables.md §1 / transition-library.md §2 原文。
- 严重度：**高**（契约 A 钉死的共用表形态与自家数据生成规则冲突，无解算规则 = 实现者必须发明语义）。

### E2 退役 `_pair_members` + 删 `p1_pair` 字段未申报消费点 `locked_buy_membership`（M2 义务面单一源）——按清单落地即断链
- 位置：details/transition-library.md §6 槽语义下游改造清单 + 退役符号集中清单。
- 攻击：`locked_buy_membership`（cw_intention.py:1304-1364，docstring 自证「锁定帧买入判定统一消费本函数」「刻意维持 p1_pair 直读」）在 :1352-1353 直读 `ist.p1_pair` 并调用 `_pair_members(...)`；sell_gate.py:70 import、:779 运行时调用。§6 下游改造清单只列 locked_buy_scope / locked_faction_scope / k_empty_window_fallback p1_lock_band 支 / cold_start_buy；退役清单也无此行。「`_pair_members` 已在删除清单，其消费点随槽语义改造一并迁移」的兜底句救不了它——该函数不读 `transition_candidates` 槽，读的是字段本身。3.3 照清单删符号：`_pair_members` 没了 → sell_gate 调用链 NameError；只删字段 → `getattr` 缺省使 M2 义务面静默丢失 p1_pair 半边。其义务分支在新机器下读什么（过渡锁定条目成员？候选并集？恒空？）设计无答案，白名单 grep 清零判据也验不出该残留。
- 证据：cw_intention.py:1304/:1349-1364（:1352 `ist.p1_pair`、:1353 `_pair_members`）；sell_gate.py:70/:764/:779；transition-library.md §6 与「退役符号集中清单」原文（零提及 locked_buy_membership）。
- 严重度：**高**（按文档执行直接断运行链，或迫使 worker 停手回设计）。

### E3 退役清单遗漏 `clear_p1_recipe`——正文裁定退役、「唯一依据」清单不含，验收判据不覆盖
- 位置：details/transition-library.md §5 裁定注 vs 「退役符号集中清单（landing 3.3『grep 清零』判据的唯一依据）」。
- 攻击：§5 明文「现行 `clear_p1_recipe` 的位面切换清空职责随配方机器退役」，但集中清单（含 `update_p1_recipe` 等 11 个 cw_intention 符号）没有 `clear_p1_recipe`。该函数定义于 cw_intention.py:1045-1067，调用点 flow.py:229（import :43），注释引用 priority.py:154、mandate_state.py:395/407-408、session_scope.py:82-84/355。换轴节点⑦（flow.py:223-233）覆盖其调用段，但符号级 grep 清零判据不查它——残留或漏删都过验收。
- 证据：cw_intention.py:1045；flow.py:43/:229；priority.py:154；transition-library.md §5/退役清单原文。
- 严重度：中。

### E4 存量字段 `IntentionState.transition_pair` 三处防御读零申报——删除 p1_pair 族后该分支去留无答案
- 位置：details/transition-library.md 全文（零提及）；退役清单 IntentionState 字段行不含它。
- 攻击：`transition_pair: tuple[str, ...] = ()`（cw_intention.py:145，「①锁局过渡对副方向」）被 locked_buy_scope :1294-1295、locked_faction_scope :1458-1463 防御读取，sess_p1_pair 写源注释（schema.py:56/:462「p1_pair 优先次 transition_pair」）也含它。全库无写点（本仓 grep 仅命中定义/读点/注释）——是死字段，但详设对其存废只字未提：§6 两函数的槽语义改造必须决定该分支去留，实现者无答案。
- 证据：grep `transition_pair` 全部命中（cw_intention.py:145/:699/:1294/:1458、schema.py:56/:462、cw_registry.py:318/:440）。
- 严重度：中。

### E5 存量机制 `StrategyState.transition_locked_systems` 与新增 `IntentionState.transition_locked` 同名族并存，存量槽归宿未申报
- 位置：details/transition-library.md §4（新字段）vs 现行 mandate_state/protection/bridge/flow。
- 攻击：现行已有一套「过渡锁定」状态：`transition_locked_systems`（mandate_state.py:434-448，「过渡域已点亮体系的键集」，frozenset），写端 `protection.refresh_transition_locked_systems`（protection.py:54-83，支持度点亮、幂等只增、plane2 关闭），消费 bridge.py:247/:284，清空点 flow.py:233（进位面 2）。详设新设 `IntentionState.transition_locked: str`（条目名、候选内成型即锁）——两者同名族、不同宿主、不同语义（体系键集点亮 vs 条目名锁定）。退役清单 mandate_state 行只列 `opening_recipe_comp`/`transition_framework`/framework 前缀；换轴节点②「含其刷新函数」只覆盖判定面，字段本体与 bridge 两消费点的处置无申报。落地后是双锁定态并存还是存量槽退役，实现者自行拍板。
- 证据：mandate_state.py:434-448；protection.py:54-83（:73 plane2 早退）；bridge.py:244-247/:284；flow.py:229-233；transition-library.md §4/§5/退役清单原文。
- 严重度：中。

### E6 混合型计分的成员重叠未定义——持有一张希儿按字面计 +3
- 位置：details/transition-library.md §2 计分规则（「持有点名成员数 + 持有的档 0 键羁绊成员数（两半等权 +1/名）」）。
- 攻击：希儿注册数据 factions=贝洛伯格、flows=量子同频（cw_chars.py:154），既是希儿引擎条目的点名件、又是其档 0 两键的注册成员——按字面持有一张希儿 = 点名 +1 + 量子同频成员 +1 + 贝洛伯格成员 +1 = +3；同 roster 内一员属两羁绊（桑博 = 贝洛伯格+持续伤害，cw_chars.py:123）是否双计同样未定义。去重规则缺失直接影响候选排序（4 条取前 3）与分数解读，设计无答案。
- 证据：cw_chars.py:154（`_ch("希儿", 3, "front", "输出", "贝洛伯格", "量子同频", ...)`）、:123（桑博）；transition-library.md §2 原文（无去重条款）。
- 严重度：中。

### E7 3.2 判据域大于文件面：三表符号「零残留」将命中至少 5 处未申报的文件面外引用；详设/详设间 config 路径互相打架
- 位置：details/counter-tables.md §5（判据与随手清理申报）；landing.md 3.2 文件面。
- 攻击：判据「**src/ 生产代码三张表符号零残留**（grep 核对）」按字面执行必命中：data/affix_effects_data.py:11（注释）、obs/cw_briefing_obs.py:54/:90（注释）/ **:357（运行时字符串）**、kernel/cw_affinity_table.py:97（注释）——共 5 处，全部不在 3.2 文件面（cw_comps/pick_common/invest_env/invest_strategy/currency_war_config + 测试镜像）。详设只申报了 currency_war_config.py 一处注释随手清理，且把路径写成 `config/currency_war_config.py`（实际在 currency_war/ 根，currency_war_config.py:36——landing 已纠正为根、详设未同步，同主张两层不一致）。判据要么红、要么 worker 自行扩文件面（无申报的自行拍板）。
- 证据：grep `AFFIX_MECHANIC_MAP|MECHANIC_COUNTERS|LINE_FACTION_TO_MECH` 全 src 命中清单（上述行）；counter-tables.md §3/§5 原文；landing.md 3.2 文件面原文。
- 严重度：中。

### E8 design §0 状态字段滞后失同步：「对抗修订稿（三轮）」vs README「对抗审中（五轮）」
- 位置：design.md:6；README.md:12-14。
- 攻击：状态字段是定稿门（iteration-design.md §2.1/§6：草案→对抗审中→定稿），design 仍写「对抗修订稿（三轮）」且非模板状态值，README 已是五轮——两层对同一字段不同步（硬规则 4「修订后全量同步复查」违例）。另 README 设计对抗字段有两行（「五轮进行中」+「四轮完成」），后者被前者完全包含，属修订残留。
- 证据：design.md:6；README.md:12/:13/:14。
- 严重度：中。

### E9 landing 3.3 判据计数失同步：「§7 申报五条」实为六条——第 6 条（换轴行为面）无验收锚
- 位置：landing.md:48 vs details/transition-library.md §7。
- 攻击：§7「行为变化申报」实列 6 条（第 6 条 = 过渡机制关闭判据换轴：位面 2 未终局锁定帧过渡层从整域关闭变照常活跃），landing 3.3 完成判据仍写「申报五条」。换轴是本迭代最大行为变化之一（详设自己标注「用户裁定」），验收清单把它数漏。
- 证据：transition-library.md §7 条目 1-6；landing.md:48。
- 严重度：中。

### E10 `direction_comp_of` 在册消费点计数错误：自称九处、分项与实码均十处
- 位置：details/transition-library.md §5 第四侧。
- 攻击：「flow×5 / entry×3 / shop:863 / decision_payload:62 共九处」——分项合计 5+3+1+1=10；实 grep 调用也是 10 处（flow.py:558/577/595/617/648、entry.py:514/1166/1194、shop.py:863、decision_payload.py:62；session_scope.py:475 是 `__all__` 导出非消费）。函数保留策略不受影响，纯数字主张失实。
- 证据：grep `direction_comp_of` 全 src。
- 严重度：低。

### E11 一般克制级减分常量「落地批定标」——无常量名、无定标方法
- 位置：details/transition-library.md §2（「一般克制级减分进排序（常量落地批定标）」）。
- 攻击：该常量尚不存在（新表配套），名字未定；本迭代已裁定不做 A/B 模拟对照（design 落地顺序约束），「定标」手段只剩人工拍板却未申报拍板主体与参照（终局线分的词缀面？现行 RESTART/FEAR 档？）。数值留代码合法，但「怎么定」是实现者要的答案。
- 证据：transition-library.md §2 原文；design.md「落地顺序约束」节。
- 严重度：低。

### E12 迭代稿自身的术语表违例（方案 5 自身义务）与 §2 定义义务的判据缺口
- 位置：transition-library.md:94/:101；landing.md:76/:79；terminology.md §0/§1/§2；landing.md:79（终扫判据）。
- 攻击：术语表 §0.4「新写稿守本表」——① §1 替换表词「在册」（表列白话 = 已登记）在 transition-library.md 出现两次（:94「其在册消费点」、:101「在册消费点」）；② landing.md 在固定节名之外的白话位用「正本」（:76「清单所列正本文档」、:79「正本与实现一致」；表列白话 = 权威版本——:72 的豁免声明只覆盖节名「正本更新」「正本更新清单」）；③ §2 保留词（判据/口径/真值/单一源/帧/fail-closed 等）7 篇首次出现均未带定义句，而末阶段黑话终扫的扫描方式只写「§1 替换表逐词 grep」——§0.2 的定义义务在自家可执行判据里没有检查位（方案 5 可执行性缺口）。
- 证据：上列行号原文 + terminology.md §0 规则 2/规则 4、§1「在册」「正本」行、§2 表。
- 严重度：低。

### E13 迁移快照脚本无落点、「代表板面」构造规则未定义
- 位置：details/faction-priority.md §7；landing.md 3.1 文件面。
- 攻击：恒等测试是结构批核心验收载体，其快照生成脚本（在旧代码上跑）放哪（tools？测试仓？临时目录？）、「每线 3 个代表板面」的『半成型』按什么规则从线数据构造，均未写。快照自比对使任意选择都「正确」，但覆盖强度随实现者选择漂移；3.1 文件面也没给脚本的合法落位。
- 证据：faction-priority.md §7 原文（两处「脚本生成」）；landing.md 3.1 文件面（无脚本条目）。
- 严重度：低。

### E14 「点名件费段必须位面 1 商店可刷」缺位面 1 等级区间出处
- 位置：details/transition-library.md §1 硬约束。
- 攻击：费段解锁表有出处（cw_shop_odds.REFRESH_PROB，已核实 lv1-3 纯 1 费/lv4 起 2-3 费/lv5 起 4 费/lv7 起 5 费），但「位面 1 可刷」还需位面 1 的等级范围（姬子 3 费 lv4 起可刷、黑天鹅 5 费 lv7 起不可刷，两条结论都依赖「位面 1 覆盖 lv4 且不及 lv7」）——该区间无数据/文档指针，费段校验的边界值实现者无从判定。
- 证据：cw_shop_odds.py:44-58（仅等级×费段表）；transition-library.md §1 原文（区间未标注出处）。
- 严重度：低。

## 实现者走查记录

**3.1（羁绊优先级结构）**：文件面全部可解析——kernel 四件 + pick_common + proofs（`p15/p15v2_fit.py` 为 `tools/cw/proofs/p15/` 子目录形态，实存）+ 消费面文件（cw_invest_channels / cw_launch_admission / deploy_search / flow / cw_events / cw_exec_state / cw_investments / invest_env / invest_strategy / sim/power_model/features.py 全部实存，`test_faction_derivation_locks.py` 同域在册）。§4 映射表 12 行逐行对码成立：成型度（cw_comps:1111-1147）/L1（deploy_search:213,302）/L2（:338-341,656）/囤货键（cw_intention:1079 form∪sub 手写并集）/投资通道（cw_invest_channels:22,:162-178 三层规则无副档分支）/轮廓（cw_comps:174-176 form∪flex）/受克（pick_common:50-59）/首键（:544 `next(iter(c.form_tiers), '')` 唯一生产消费，龙丹 {战技点4,列车4}、桑博 {持续伤害4,贝洛伯格2} 与「错挂」叙事逐字对上 `_p1_pair_lines` docstring :537-539）/护栏（:1467 form∪sub 直读）/or 承接（cw_comps:1124-1126）/配方构造（cw_recipe:46/54/61 ×3 + cw_intention:808）/线距离防御读（cw_line_switch:102/:158 `getattr(...form_tiers...) or {}`）——全部实锚。21 套阵容清点属实（COMP_LIBRARY 21 个 Comp；sub_tiers 六处全 int、tuple 零使用；反甲白厄 form_tiers={} 白纸黑字）。卡点 = E13（脚本落点/板面构造）；走查注记：form_progress 的恒等消费面 cw_equip_wear_plan.py:225-227、cw_screen_shop.py:119-127、mandate.py:726 不在文件面列举——因接口不变无需改动，不构成卡点，仅记录列举不完全。

**3.2（克制表直写）**：文件可解析；调用改写式行号逐一对码无误（invest_env.py:337/:347、invest_strategy.py:281/:338 实锚）；`COUNTER_PICK_PENALTY = -750`（cw_line_scales.py:70）、`merged_mechanic_tables` 消费唯一（pick_common）、27 键/12 行/活链路 2 条/死条目（紧急止血→爆发机会）全部复核属实；受克行为等价性独立推演成立（改名层 3 对 × punished 键集 ⇔ 直写表名单 ∩ core，or_reqs ⊆ 档 0 由校验 3 钉死）。卡点 = E7（判据域>文件面 + config 路径两层不一致）。

**3.3（过渡库与配方层退役）**：文件面含「不动清单」全部实存（cw_engine_facts / cw_win_model / cw_battle_calib / match_archive / ab_judge / win_model_m1 / p15 目录 / p65_check）；机制面答案基本齐备且对码成立——四条目与 SYSTEM_CARDS 判据逐字一致（仙舟3/列车2/DOT2/希儿单卡∨档，engine_required=铁三角与 _CORE_TRIO 同源 cw_line_facts:30，star_goal 2★/3★ 对上 cw_system_cards:107/:134）；费段与档位数值全部核verified（cw_chars/plaza/FACTIONS.tiers/REFRESH_PROB）；换轴 7 节点逐一对码实锚（priority:151,327,332 / protection:73 / hoard:1143 plane_of / sell_candidates:219 / deploy_search:985 / shop:847,865,883 / flow:223-233）；committed_authority 序①②（:1198-1233）、need_star 现状（priority:164-165）、重叠归终局与 setdefault（:170-177,:219-223）、k_empty_window_fallback 死循环注释（:1162-1193）、_COLD_BOND_KEYS 派生（shop:237-241）、保护集体系键（protection:77）、物化写段（flow:245-264）、配方开局面读口（session_scope:395-412）、sess_framework/sess_p1_pair（schema:406/:466，match_archive:1063 纯透传）、p65_check 读点（:90/:100/:154/:163/:210/:262）、P24_VALIDATION:31 rung 定义——全部实锚无误。卡点 = E1（表数据冲突）、E2-E6（消费面与存量机制未申报）、E11/E14。走查注记：`TRANSITION_LIBRARY` 现库不存在（无撞名）✓；cw_plugins/cw_bridge_pool 确有对退役符号的存量注释引用（cw_plugins:17/:115、cw_bridge_pool:7），文件面点名合理。

**3.4（富余买入归并与 P88 退役）**：行号级对码全部命中——shop.py:1893 注释「压牌库判据的席位维由序列末位让路承载」逐字、M6 排除面 obligation_members（:1898/:1931）与义务装配（:884-906）、k_members 单方向名单（:863-864）、dominance 调用段（mandate:958-979）、`dominance_buy_eligible`（:557）、契约键（contracts:236）、映射键（sell_gate:131）、`swap_transition_narrow_frame`（:683）、`dead_stock_pair_buy_reject_reason` docstring s77091 叙事（:644-649）、`PRESS_NARROWED_ARMS` 独苗（:676-680，hub_option_buy 并入注释在）、p88_check:34/:87、test_dead_stock_pair:187-195、p88.md 实存。M6 兜底带语义（zero_overlap 同规则、让位档 10 承载 1★）可开工。无新增卡点。

**末阶段（正本更新）**：清单 12 行逐条可解析——strategy-docs 12/10/24/28/32/README/13/16 实存（29 号稿按「落地时 grep 定位」可执行）；`sim/sim-power-model.md` 实存；proofs/ 目录与 p88.md 实存；`skills/sr-od-dev-currency-war/references/comp-definition.md` 实存；docs/game 侧 4 处引用实锚核verified（README:20 + data/competitors.md:15/37/131）；10 号稿:209「MECHANIC_COUNTERS/BOSS 表 | 留」行实锚存在，清单申报准确。判据（清单清零 + 黑话终扫 + 证明留档豁免）可执行；豁免口径与术语表留档语义自洽。终扫判据的可执行性缺口见 E12③。

## 收敛判定建议

**本轮不收敛，不可定稿。** 必须修复项：

1. **E1（高）**：给 `AFFIX_COUNTERS_FACTIONS` 的冲突解算规则——要么改形态（如值 = 羁绊名×强度的列表，允许同词缀分级），要么改投影规则（显式排除/覆盖已登记键并申报行为取舍），并补「净化身心×DOT队、永久创伤×万敌单C」两处交集的行为申报；
2. **E2（高）**：申报 `locked_buy_membership` 的承接口径（p1_pair 半边在新机器下读什么），并纳入 §6/退役清单或显式裁定其分支退役；
3. 中级项 E3-E9（clear_p1_recipe 入清单、transition_pair/transition_locked_systems 存废裁定、混合型计分去重规则、3.2 判据域与文件面对齐 + config 路径统一、design 状态字段同步、landing 五条→六条）随修订一并清；
4. 低级项 E10-E14 属表述/补出处级，可随上述修订顺手清。

计数：**14 项（高 2 / 中 7 / 低 5）**。修复 E1/E2 后需按流程重送对抗确认收敛。
