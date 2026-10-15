# 遭遇迁移设计 对抗审查报告（第五轮）

> 攻击对象 = 本目录 design.md / landing.md / README.md 三件。全部码点/数值/引文按「直调复核禁转述」执行，证据以 文件:行 标注。判据源直调：00/01 号稿（宪法与数字三形态章程 §6）、04 号稿 §7 裁定表第 9 行、op-layer.md §1.4、p64 单篇、math_proofs.md 索引（P15/P26/P64/P85 行）、P9_VALIDATION.md、cw_node_schedule.py、economy.md §10.2、combat.md §3、货币战争-敌人信息浮层.md、iteration-design.md、strategy-work.md、AGENTS.md，以及任务书所列全部现役代码文件与测试仓 grep 面。此前轮次报告未采信（隔离声明：全部发现由本轮独立直调得出）。

## 发现清单

### R5-F1 [严重度:高] landing 注释收口写「改指 data 单一源」，与 design §2.4/§2.7「迁 kernel/cw_obs_core 后改指」直接矛盾，且 data 宿主被 design 明令禁止
- 位置：landing.md §3.2（范围段）；design.md §2.4、§2.7
- 发现：landing.md:15 写「钻石名单单一源表述两处（`cw_events.py` SupplyOption docstring / `supply.py` 头部，**改指 data 单一源**）」。但 design.md:110 明文「钻石检测集单一源迁 **`kernel/cw_obs_core.py`**……⚠️ 不可迁 `data/cw_equipment_data.py`：生成文件由 `tools/cw/gen_equip_registry.py` 整文件覆写」，design.md:141 同款句「（钻石检测集单一源迁 kernel/cw_obs_core 后改指，§2.4）」。直调证实禁令基础成立：`tools/cw/gen_equip_registry.py:355` = `out_path.write_text(module)`（整文件覆写），`cw_equipment_data.py:3` = 「勿手改」。landing 自己的文件面（landing.md:17）也写「`kernel/cw_obs_core.py`（接收钻石检测集单一源，design §2.4）」——同一小节内文件面与注释收口项自相矛盾。按 landing 字面执行会把两处长期存活的 docstring 指到 design 禁止承载该常量的生成文件上。
- 修正方向：landing §3.2 两处「改指 data 单一源」→「改指 `kernel/cw_obs_core` 单一源（design §2.4）」，与 design §2.7 指针收口清单逐字对齐。

### R5-F2 [严重度:中] 阶段 3.1 新核的钻石检测集来源无解：文件面既不含 obs 也不含 cw_obs_core，3.2 文件面又漏 `encounter_pick.py` 本身
- 位置：landing.md §3.1/§3.2 文件面；design.md §2.1/§2.4
- 发现：`reward_tier` 消费 `DIAMOND_EQUIP_NAMES`（现核 `cw_encounter_selection.py:263-268` 为函数体内 import），现役唯一定义 = `obs/cw_node_obs.py:216`，kernel 侧无模块级再出口（`cw_obs_core.py` 全文无此常量）。landing 3.1 范围新建 `encounter_pick.py`（含 `reward_tier` 与四档常量，landing.md:4）但文件面（landing.md:6）只有新文件 + 测试两个路径——实现者只有两条路：(a) strategies→obs 直 import，违反 design §2.1「策略层不 import obs」不变量与 landing 3.2 完成判据「策略层无 obs import」（landing.md:21）的终态口径，该暂态未获任何申报；(b) 复制三件名，违反单一源。且 3.2 把定义迁 `kernel/cw_obs_core` 时 `encounter_pick.py` 的 import 行必须同步改源，但 `encounter_pick.py` 不在 3.2 文件面（landing.md:17）——严格按文件面施工会在 3.2 完成判据处撞死（触发停手令）。
- 修正方向：二选一并落纸——①把「`DIAMOND_EQUIP_NAMES` 定义迁 `kernel/cw_obs_core.py` + `obs/cw_node_obs.py` 改 import kernel」移入 3.1（新核消费前置；obs 侧仅 import 源一行切换，不触现役接线，与 3.1「零行为变化」边界相容）；②保留 3.1 暂态 obs import 的显式申报 + 把 `strategies/impl/mandate_v1/encounter_pick.py` 补进 3.2 文件面。

### R5-F3 [严重度:中] 3.2 零残留 grep 集按字面不可执行：`EncounterPick` 是新载体名前缀、「旧址」括注对 `encounter_tier_score` 失实、集合不完整
- 位置：landing.md §3.2 完成判据第 1 条（landing.md:21）
- 发现：①新载体名 `EncounterPickDecision`（design.md:69-71、landing.md:4）以 `EncounterPick` 为子串，全仓 grep `EncounterPick` 在落批后恒非零（新文件与测试处处命中），「零残留」按字面永不可绿——须 `\b` 词边界或逐文件点名；landing 自己也意识到保留分支的纠缠（「EV 核保留分支下 `EncounterPick` 项 = 改形后零引用为准」）但没解决子串碰撞。②括注「（**kernel `cw_encounter_selection.py` 旧址**）」对 `encounter_tier_score` 失实：其实址 = `kernel/cw_survey19_hooks.py:17`（design §2.7 自己也是这么写的）。③集合只列 6 符号，漏了同一删除/迁出面的 `PROGRESS_BAR_DIRECTION`/`BAR_SEMANTICS`/`_FILL_EDGE_THRESHOLD`/`_kappa_state`/`reward_tier`/`g_ratio`/`_lowest_idx`/`_d_enc_snapshot`/`_Diagnostics`（design §2.3/§2.7），这些的 kernel 旧址零残留同样是验收对象。
- 修正方向：grep 集改写为「词边界模式 + 每符号标注旧址文件」的表；补齐 §2.3/§2.7 全部物理删除与迁出符号。

### R5-F4 [严重度:低] §2.2 节点日程摘要以 P2 口径冒充 kernel 全表，与 §2.12 锚点 6 表面冲突
- 位置：design.md §2.2（窗口定义维持段，design.md:93）
- 发现：§2.2 写「kernel 真值表（`cw_node_schedule`……）= 单遭遇（**supply@r3 + encounter@r5**）」。直调 `cw_node_schedule.py:28-36`：P1 = reward/reward/battle/battle/supply(**r5**)/battle/encounter(**r7**)/reward/boss，P2 = battle/battle/supply(r3)/battle/encounter(r5)/reward/boss——「supply@r3+encounter@r5」仅 P2 成立；§2.12 锚点 6（design.md:187）自己写「P1 首遭遇帧 = r7」。同文档两处按字面对不上（上下文虽在谈 P2 分歧，但主句主语是「kernel 真值表」）。等价性结论本身经直调推演成立：P1 遭遇帧前最近两战斗类行 = r3/r4；P2 遭遇帧（全局序 14）前最近两战斗类行 = 全局 11/13，均晚于 P1 遭遇行（全局 7），两候选窗口同取两行——维持候选 A 的论证不因此动摇。
- 修正方向：§2.2 改为按位面陈述「每位面恰一次遭遇（P1 encounter@r7/supply@r5；P2 encounter@r5/supply@r3）」，消除与 §2.12 锚点 6 的表面冲突。

### R5-F5 [严重度:低] §1 症状 1「裁定 9 已授权的结算观测基建闲置」与 §2.1 保留面的在产事实相抵
- 位置：design.md §1 症状 1 末句（design.md:18）
- 发现：「裁定 9 已授权的结算观测基建闲置」不成立：结算观测持久化在产（写端 `record_settlement_row` = `cw_screen_battle_wait.py:330`）、兑现回调在产（`claim_encounter_reward` = `cw_op_settle_confirm.py:104`）——§2.1 自己把 `claim_encounter_reward` 登记为「结算确认链挂点」。真实闲置面 = 判据侧消费：`last_normal_battles`/`_kappa_state` 唯一消费 = 被迁的 `decide_encounter`（`cw_encounter_selection.py:389-390`，全仓 grep 证实无其他生产消费）。
- 修正方向：改述为「裁定 9 授权的判据消费面（κ_S 窗口/经验层）闲置；持久化写端与兑现回调在产」。

### R5-F6 [严重度:低] §2.7 删除清单漏随删函数的专属 import 收口（cw_events 6 枚 + bridge 2 枚）
- 位置：design.md §2.7；landing.md §3.2
- 发现：删除 `decide_encounter`/`_option_mechanics`/`_reward_value` 后，`cw_events.py` 的 `form_progress`（:117，唯一消费）/`deployed_count_of`（:119）/`max_units_of`（:119）/`plane_of`（:137/:145/:146，全部在被删函数体内）/`merged_mechanic_tables`（:82）/`mechanics_fit`（:84）变为未用 import（ruff F401）；删除 `bridge.decide_encounter` 覆写后，`bridge.py:39-44` 的 `CwActionPickEncounterParam`/`CwActionRefreshNodeOptionsParam` 顶层 import 在 bridge 内无其余消费（bridge 全文核）。删除清单与 landing 3.2 均未列这批机械收口——实现者只删函数体会留死 import，靠 ruff 兜底属于「实现者替设计补设计」。
- 修正方向：§2.7/landing 3.2 补一句「被删函数的专属 import 同批收口（以 ruff F401 清零为准）」，点名上述 8 枚。

### R5-F7 [严重度:低] §2.5 无界重进循环：防线挂账无期限，且未论证「廉价防线不随本批做」的取舍
- 位置：design.md §2.5（design.md:118）；landing.md §3.2 末段「已定谳申报」
- 发现：设计对机制的诊断经直调证实无误——`cw_loop.py:829-836` ok 即清零连续 fail 计数窗、:852-868 仅 fail 计数达 `OP_FAIL_REDISPATCH_LIMIT=5` 才 `round_fail`；零点击 `round_success` 每轮 ok=True，外循环确无防护。刷新阀激活后该路径由死转活（design §2.12 行为变化申报 2，卡死一条龙级风险自评）。但处置①的挂账（流程层批）**无期限/无强制触发条件**——strategy-work §3 对悬置面的通则是「必须带裁决期限（超过一个对局周期未决=违规）」，本挂账未引该通则也未自定期限；且 3.2 文件面本就含 `cw_screen_encounter.py`（注释收口），「`round_fail` 计数防线（数行级）为何不随批做、只做注释」的取舍未写一句理由，只写「择一归 flow 域」——连防线方案的选择都被推迟。
- 修正方向：二选一——①防线随批落（op 侧把「重调仍 Suggestion ∧ 锚读缺」转具名 `round_fail` 计入重派上限，方向保守、与「op 层零行为改动」边界的冲突需在设计里显式豁免并说明）；②保留挂账但补期限/触发条件（如「随下一流程批强制携行；实机哨兵触发即提前」），并写明本批不做的权衡一句。

### R5-F8 [严重度:低] README「待用户过目/裁定点」节复述 design 内容，构成第二抄本漂移面
- 位置：README.md §待用户过目/裁定点 2（README.md:15-17）
- 发现：白名单 {其一,其二}/偏好序/「过目未过 → 回落最低档并回设计层」三句均为 design §2.2/§2.10 的内容复述（design.md:63、:166）。迭代规范对 README 的限定是「只做两件事——串文档、记进度；不放判据、不放松散笔记」（iteration-design.md §4），模板仅文档/进度两节；design §2.2 修订时此处构成第 4 条硬规则（全量同步复查）的额外同步义务面。supply 批 README 亦有扩展节先例（该批 README.md:13「后续顺手项」），故降为低。
- 修正方向：压缩为纯指针（「裁定点清单与后果单一源 = design.md §2.2/§2.10，定稿呈报时逐项给出」），或保留但在 design §2.2 修订义务里点名此处同步。

## 零发现面申报（实际攻击过的面，未列 = 未攻）

**判据源直调（全部相符，零发现）**
1. 宪法五/六：`00_framework.md` §1 第 5/6 条（用户裁定 2026-09-23）与 design 引用逐字相符；判据线「换一套策略实现会不会要不同的值/序」原文在册（00:17），§2.1 迁移判据线引用如实。
2. 宪法一/二/三：P3 分支 `plane_of(gs)==3` 枚举辖域违例存量属实（`cw_events.py:137`）；「危险只升不降」方向核查（遭遇败局入窗使 κ_S 降档 = 反应提前）与 00 §4 相符。
3. 01 §6 数字三形态章程：【拍】字面辖域引文逐字命中（「登记即立场、分差即偏好强度」的加法立场值，01:168）；【拍】禁域条款（01:167）；公理 5/无标注数字禁令（01:28、170）；合法性要件 2 = 初值经裁决窗过目（01:166）——design 的章程缺口申报（离散结构立场值不在字面辖域）与「定稿呈报 = 过目载体」设计如实、未越权。
4. 授权链：04 号稿 §7 表第 9 行直调——授权辖域（敌方通道 killed/进度填充率 + GameState 持久化）、「判据正本 = `kernel/cw_encounter_selection.py`」指针、用户 2026-09-12 逐项确认，与 design §0/§1 症状 5/§2.9 改写方案全部相符。op-layer.md §1.4 刷新剩余语义（None = 未观察；节点屏闸 None = 拒刷；禁访问内重读/重调的刷新链纪律）相符。
5. P64 单篇：辖域原文「静态 `dict[敌方难度读数→stat]` 形态，条件表形态不在辖域」（p64:5）与 design「引申申报，非 P64 原文结论」的分层申报诚实相符；自由项清单 B/q/s/m（p64:19-21）与 §2.3 引用一致；L 表一~四录/五~六未录（p64:22）支撑经验档层依据；点亮前置链① = 浮层读数通道（p64:30）与「明确不解决」划分相符。
6. math_proofs 索引：P15v2 boss 26.79 / 普战 10.45（索引 :27）、P26 待证明（Δp_prep 条件表 + L_node 分位口径未采，索引 :38）、P85 A/B 分键（遭遇备战帧）与不消费选档输出（索引 :94）——§2.2/§2.12 引用逐项相符。
7. P9_VALIDATION.md:10 确登记 cw_survey19_hooks「P1/P9/P8」旧编号与 math_proofs 索引无关——§2.7 删除不受影响声明属实；wear_discipline_alert 零生产消费属实（全仓 grep 仅定义）。

**现役代码直调（全部相符，零发现）**
8. 三核并存与恒暗装：六标定槽全 None（`cw_encounter_selection.py:47-64`）→ `F_MIN is None` 即 `_dark`（:375-376）= 最低档 + 零刷新；生产壳覆写链（`bridge.py:252-285` 覆写、基类 `flow.py:594-609` 挂 `cw_events.decide_encounter`）与 §1 症状 1 完全一致；「13 号稿双轨描述漂移」属实（`13_pick_family.md:21`，且该行连现役暗装核都未提）。
9. 迁移面对照：`_CALIBRATABLE`（:72-73）、`_FILL_EDGE_THRESHOLD=0.5`（:285）、cap=2/6（:418）、cap 过滤在前 + t≤4 比值腿/t≥5 经验层顺序（:421-434）、`tier_cleared`（:195-198）、`reward_tier` 四档序与 `'/'.join(rewards)` 输入及 `(档, idx)` 并列序（:247-278、:442-444）、`_lowest_idx` 空表返 0（:459-463）、因词三枚举与 `e3-simple|` 归因串（:371/:396/:406/:438/:446）——§2.2-§2.4「照原核逐位同构」声明全部逐位核实。
10. 消费面声明全列核实：`EncounterPick` 全部消费方（src 28 处 grep = cw_events 本体 + cw_encounter_selection + cw_vocab :715/:906 + bridge + encounter.py）；`EVENT_PICK_TYPES`/`EventPick` 位（`cw_events.py:538-543`）；`EncounterOption` 五方（obs 写端/cw_screen_report/encounter.py:16、容器、sim :528、测试仓 5 文件）；`apply_calibration`/`reset_calibration` 全仓零外部引用；`encounter_tier_score` 唯一消费 = `cw_events._score`（:129/:145）；`flow.py:656/793/807` 现役消费行号逐一命中；`test_cw_unified_action_4.py:28/:259/:278` 行号命中；`test_cw_obs_arch_event_screens.py:417-420` 保留面 import + 重调零点击行为锁（:390-404）；EV 核 src+测试仓双零消费、模块 docstring 自称的「EV 核纯函数锁」经 grep 确不存在（design 勘误属实）；`cw_economy.py:414` 败补六消费点句、`cw_difficulty_account.py:56-59` 消费批句、`provisional.py:22-23` 注入指针句、`supply.py:12` 单一源句——design 指针收口清单逐条实址命中。
11. 文件级契约：`gen_equip_registry.py:355` 整文件覆写 + `cw_equipment_data.py:3` 勿手改（design 避开 data 宿主的理由成立；「三钻无标志字段可派生」经 :53/:64-65 核实——财富宝钻 official='宝钻' 而红钻/蓝钻无任何标志字段，集合级不可派生属实）；`kernel/cw_obs_core.py` 手维护、非生成，可作宿主；`EQUIPMENT_ROSTER`（:233）在册。
12. op 层与动作链：`cw_screen_encounter.py` 重调路径/三出口/空候选零点击/idx 越界断言（:150-252）与 §2.5/§2.6/§2.8 申报一致；`CwActionPickEncounterOp` 静态入参词表动作、`report_action_pick_encounter_param(gs, param: Any)` 鸭子取 idx（`cw_pick_encounter_action.py:54`、`cw_action_report/pick_encounter.py:47-58`）——「动作链零改动」成立。
13. 外循环防护语义：`cw_loop.py:829-868` 如 F7 所引——design「零点击 round_success 不计数且清零窗」的直调结论正确（该发现只攻挂账治理，不攻机制诊断）。
14. 窗口/日程两源：`cw_node_schedule.py`（P1 42 局零反例、P2 7 局对照，:6-12；P1/P2 序列 :28-36）与 economy.md §10.2 P2 行双遭遇 r3/r5 + 「待多局复核」注（:133）——「两源冲突未定谳」申报属实；P1/P2 两源 boss 均位面末节点核实；P1 r7 帧窗口 = r4/r6 两普战（锚点 6）核实。
15. sim 盲区申报：sim 全目录零 `record_settlement_row` 调用；`ENCOUNTER_TIER_COUNT=4`（`cw_sim_backend.py:488`）；占位奖励文本 `'金+20(占位,…)'`（:537-538）不含「金币」字面 → 新 tiebreak 下全落末档；sim `refresh_left=None`（:1379）→ 闸拒——§2.12 sim 形态推演逐位成立。
16. 浮层/combat 判据源：浮层入口②（遭遇选中卡 → 查看详情）已建档、难度分随卡变 OCR 全可读（`货币战争-敌人信息浮层.md:9/:31-33/:45`）；combat.md §3「遭遇奖励 = 伤害进度达标制非清场制」（:38）——killed=True 蕴含进度达标的方向论证前提属实。

**规范遵循（除 F1/F2/F3/F8 外零发现）**
17. iteration-design.md：design 四节齐（§0 元信息含状态「对抗审中」/§1 四件齐/§2 单文档方案深度申报）、依据就地标注密度高（每关键主张带直调指针，抽核无虚标）；landing 三阶段七件齐、固定末阶段 + 正本更新清单齐、清单与 §2.9 文档面一致（31 新建未占用、30 = supply、25/13/08/04 行实址核对）；README 索引 + 进度结构合模板。
18. strategy-work.md：零调参通则——「本批零新数值」经核成立（白名单/偏好序走【拍】缺口申报路径；cap=6 = 档位值域游戏事实；0.5 = 惰性阈值未定谳不激活；κ_S/经验层/刷新阀结构门无自由数字）；「符合策略核心即可落码」确认链引用（2026-09-05 裁定）与 skill §2.4 原文相符；L2 点名/SKILL.md 测试分层引用有效；§6 对抗循环对象三档覆盖本批。
19. AGENTS.md：迭代内工件引用 changes/ 先例合法（寿命 = 迭代）；正本更新清单未引入对 changes/ 的长期引用；「暗装」等术语在文内定义（§1）后使用。

**部分攻击面如实申报（攻了、证据不完整或范围受限）**
- 「验收线保全申报」（design §2.12：无在册验收线以遭遇选档为直接判据面）——math_proofs 索引 P15/P26/P64/P85 与测试仓行为锁面已核支持该申报；当期迭代 criteria 目录（.debug/progress 现役迭代）未穷尽，该半边未证。
- `cw_game_state.py`（3859 行）只核遭遇相关字段/消费点（settlement_ring/encounter_log/encounter_refresh_left/chosen_encounter/enemy_difficulty/encounter payload），未逐行。
- `sim/cw_sim_backend.py`（1612 行）只核遭遇/刷新/结算写端相关面；mandate_v1 其余文件（entry/shop/proof/criteria 等）非本批对象未攻；28/29 号稿正本未攻；25 号稿只核头注/§1/§2。
- `game_start_reset` 全仓零调用方（仅定义，`cw_encounter_selection.py:206`）——属存量基建形态非本批引入，§2.1 将其列入保留面语义可自洽（生命周期 = 局由 GameState 字段 default_factory 保证），未立发现；落地批若做全仓复扫可顺手申报孤儿态。
