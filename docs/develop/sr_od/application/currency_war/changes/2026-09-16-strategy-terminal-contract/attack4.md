# attack4 —— 策略器终态契约 迭代设计 对抗审查报告（r4，独立干净上下文）

> 审查对象：`design.md` / `details/session-dissolution.md` / `landing.md` / `README.md`（2026-09-16 当前工作树版本）。
> 判据源全部直调复核：iteration-design.md、00/01 宪法两篇、fields.md（§2.1/§2.2/§3.4/§3.7.1/§8.8/§9.4）、flow/README §2 全节、flow/session.md、flow/outer_loop.md、flow/action_exec.md、game_state/journal.md、guards.md 头注、被取代的 strategy-input-unification 全文、unified-obs-reconcile landing、代码真值（cw_strategy/cw_strategy_session/cw_game_state/cw_hp_policy/cw_reconcile/cw_vocab/cw_events/cw_back_layout/cw_plane_table/cw_strategy_manager/flow/bridge/shop/cw_loop/cw_screen_prep/cw_screen_buy_cards/cw_screen_battle_wait/cw_observation/cw_action_registry 等）。
> 全仓普查（出现次数，Select-String -AllMatches 实测）：`game_state_of` src=287/test=175；`strategy_state_of` src=131/test=6；`state_of` src=584（含子串）；`create_session` src=25/test=0；`prep_obs_frame` src=23/test=2；`last_hp` src=59；`upcoming_types` src=4；`relay(` 生产 6 处（cw_observation.py:2633-2651，值源逐行核对全部为 session 字段）。`kernel/cw_strategy.py` 路径不存在（glob 直证）。

## 发现总数：21（blocker 3 / major 10 / minor 8）

---

## blocker

### B1 landing 3.2「范围承诺 ⊃ 文件面授权」失配复发：探针族重锚的 mandate_v1 消费文件无文件面承载

- **文件:节**：landing.md §3.2（范围行 vs 文件面行）
- **发现**：范围行承诺「读者**全量**重锚（cw_plane_table/cw_economy/cw_intention/cw_discipline_rules/cw_line_switch/cw_screen_battle_wait/**mandate_v1 判据**——值等价换宿主）」，完成判据要求「重锚线值等价（schedule_of/nodes_of_plane 逐字节对照）」。但文件面对 mandate_v1 只授权「`entry.py`（遥测读点）+ `strategies/impl/mandate_v1/`（**两 hp 消费点随门简化**）」。直调代码，探针族在 mandate_v1 的消费文件至少还有：`statefn/horizon.py`（:20 import schedule_of，:71 导出面）、`criteria/levelup.py`（:184 nodes_of_plane 真值链）、`shop.py`（:2340/:2512 `horizon.r_remaining(session,…)` 时基链）——均不在「两 hp 消费点」授权语义内。签名从 session 改 gs 后这些调用点必须同批改，按停手令 worker 无法在不越文件面的前提下完成范围承诺。attack1/attack3 B1 已报同类问题并声明消解，本次为**消解后复发的新实例**。
- **修正方向**：3.2 文件面 mandate_v1 括注改为「探针消费点全量（horizon/levelup/shop/entry 等，以普查对账表实测清单为准）+ 两 hp 消费点」，或把 mandate_v1 探针调用点改形移入 3.5 并在 3.2 范围行显式缩窄。

### B2 StrategyState 迁移六桶中「桶 2 执行层显式读」无任何阶段承载；cw_op 的 state 读者被 3.5 文件面用途括注排除，与完成判据「普查归零」自相矛盾

- **文件:节**：landing.md §3.5（范围行/文件面行 vs 完成判据行）；details §3
- **发现**：details §3 定义承载桶六类；landing 3.5 范围只写「读者迁移收尾（**kernel 注入桶 + 遥测快照桶 + impl 桶 self.state**）」——桶 2（执行层显式读）不在任何阶段的范围行；3.1–3.4 亦无。且 3.5 文件面对 `operations/cw_op/` 的授权括注 = 「注册表换键名 + CW_ACTION_TYPES + 完备锁」，而 cw_op 下实存 StrategyState 读者：`cw_buy_card_action.py:114`（v3_intention）、`cw_op_sell_off_target.py:58-62`（target_comp ×3）、`cw_op_tools.py:329`（target_comp）——被用途括注排除在外。同阶段完成判据却要求「`strategy_state_of`/`state_of` 符号普查归零（对账表）」：按授权面干活的 worker 必然留下 cw_op 三处未承载，验收判据不可满足。details §3 桶 2 的「预登记重载面」（cw_loop/cw_screen_deploy/cw_screen_buy_cards）也未覆盖上述 cw_op 消费点与 `cw_screen_equip_pick.py:57`、`cw_screen_battle_wait.py:419`。
- **修正方向**：3.5 范围行补桶 2（执行层显式读）；文件面 cw_op 括注扩为「注册表换键名 + CW_ACTION_TYPES + 完备锁 + state 读者迁移（普查清单实测驱动）」；details §3 桶 2 预登记面补 cw_op 三文件与 equip_pick/battle_wait。

### B3 `reset_layout_unknown_state()` 退役段三重失实：机制论证与代码事实相反、函数本体不在文件面、测试隔离消费面未申报

- **文件:节**：details §C 表「create_session 副作用」行；landing §3.5 范围行 + 文件面行
- **发现**：设计稿论证「每局新容器 by construction 满足（新局新 gs = 未知态天然重置）」。直调代码证伪：该函数复位的是 `obs/cw_back_layout.py:150` 的 **`_unknown_streak` 模块级进程全局**，与 gs 容器无任何宿主关系——「新局新 gs」不重置它。真实自愈机制 = docstring 明文「生产=任一已知帧自动清零」（cw_back_layout.py:154）；残留风险窗 = 上局尾帧未知 ∧ 新局首帧仍未知 → 提前累积达 `UNKNOWN_FREEZE_FRAMES=3` 触发写类冻结，`kernel/cw_vocab.py:958-961` docstring 明文该调用存在的理由即「**防跨局残留让开局提前吃冻结**」。三重问题：①「by construction 满足」论证错误，防线削弱未如实申报（行为变化申报面缺失）；②函数本体在 `obs/cw_back_layout.py:153`，不在 landing 3.5 文件面（文件面仅含 obs/cw_observation.py）——「函数退役」按字面不可执行；③`cw_back_layout.py:148-149` 注明「测试纪律=被测生产路径含模块级全局时 setup 必须一并复位」——测试隔离消费面随函数退役失去唯一复位入口，无替代方案申报。
- **修正方向**：三选一并如实申报——(a) 保留函数与 flow 调用（移出退役清单，仅随 create_session 改挂新构造路径）；(b) 删调用保留函数作测试复位口，申报跨局残留窗行为变化（依赖「任一已知帧自动清零」自愈）；(c) 真删函数则同步申报测试复位替代机制。文件面补 `obs/cw_back_layout.py`。

---

## major

### M1 §A 删除族「现消费面」遗漏行为面消费点：`cw_screen_battle_wait` killed 兜底（hp 对比）读 `session.last_hp`——正常识别路径行为变化未申报，处置无答案

- **文件:节**：details §A 表 `last_hp`/`last_hp_t` 行「现消费面」列；design §1.3/§2.8
- **发现**：§A 表声称 last_hp/last_hp_t 的消费面 = cw_hp_policy 门一族。直调代码：`cw_screen_battle_wait.py:456-466` killed 判定兜底 `_prev_hp = getattr(_session, 'last_hp', None)` + `_st.last_outcome_t` 邻接门（gap==1）→ `killed = hp_after >= prev_hp`——这是胜负判定的活逻辑，非识别防线。字段删除后该分支：随字段删 = killed 判定少一路兜底（**正常识别路径行为变化**，不在 §1.3 申报清单——申报清单只含识别失准四项与装备账降级）；换源 = 现成候选 `_st.last_outcome_hp`（:497-498，同置信门同值）设计未写。普查词表会抓到该读点，但「承载桶 = 随本阶段删/不辖申报」二分对它无答案。
- **修正方向**：§A 表补该消费点行，处置钉死为「换源 `(last_outcome_hp, last_outcome_t)`（SettlementState，非 session 宿主，生命周期同段）」并在 3.2 完成判据加 killed 兜底对照单测。

### M2 「行为变化登记 §1.3」指针悬空：reconcile_hp 对账腿删除、银狼豁免消亡等在 §1.3/§2.8 申报清单中无对应项

- **文件:节**：details §C performance 行 vs design §1.3/§2.8
- **发现**：details §C 写「reconcile_hp 对账腿删 = **行为变化登记 §1.3**」。直调 §1.3 与 §2.8：申报清单实有三项 = ①正常识别路径零变化；②识别失准路径（hp 门/等级守卫/star 防抖/节点探针左移）；③装备账完整度降级——**无 reconcile_hp 对账腿删除项**。银狼升费豁免消亡、upcoming_types journal 降级用「见 details §A」扩散指针，主清单同样无行。行为变化申报的单一收口面（§2.8）失去完备性，终验「与改前同难度局对照」的分歧归因清单不完整。
- **修正方向**：§2.8 行为变化申报增列：④hp 双源对账腿删除（reconcile_hp 简化）；⑤star 回退确认链形态变化（防抖确认 → 回退即采新，含银狼豁免消亡与 ADR-0420 帧态门删除）；⑥upcoming_types journal 列 '?' 常态化；⑦B3 所涉布局未知态跨局残留窗（若裁退役）。

### M3 `RefreshNodeOptions`/`RefreshSupply` 执行路径无定义：不在完备锁豁免集、亦无注册行与 op 定义——实现者面临无答案选择

- **文件:节**：landing §3.5（注册完备锁规格）；design §2.2；landing §3.1/§3.5 文件面
- **发现**：完备锁规格断言「白名单成员要么有注册行、要么在 handler 自管豁免集（PickInvest/PickStarTome/PickWishTrial/PickBoxCard/**RefreshInvestCards**）」。RefreshInvestCards 因「三闸点击链留在 handler」入豁免集；`RefreshNodeOptions()`/`RefreshSupply()` 同为 handler 消费的刷新建议（design §2.2 只对 RefreshInvestCards 标注「点击链留在 handler」），既不在豁免集（=> 必须有注册行），全文档又无对应动作 op 的定义、无 `cw_op/` 新增文件授权（3.5 文件面 cw_op 括注仅「注册表换键名」）。落地时锁断言必然失败或实现者自行拍板二选一——「实现者无需再设计」违反（attack3 M4 声明消解后的残留缺口）。
- **修正方向**：二选一定死——(a) 豁免集补入 RefreshNodeOptions/RefreshSupply（与 RefreshInvestCards 同型：handler 自管点击链）；(b) 定义两个新动作 op 并扩 3.5 文件面。按现状行为等价原则推荐 (a)。

### M4 `PICK_ACTION_TYPES`（cw_events.py:895）双词表结构处置未申报

- **文件:节**：design §2.2；landing §3.1/§3.5
- **发现**：现状注册完备锁遍历「`cw_vocab.CW_ACTION_TYPES` + `cw_events.PICK_ACTION_TYPES`」双词表（cw_action_registry.py:9-11 模块头明文）。终态 Pick 族全数变为 CwAction 子类入 CW_ACTION_TYPES 后：旧 Pick 载体（EncounterPick 等）退役，PICK_ACTION_TYPES 是退役、清空保留、还是改造为新 Pick 子类索引——四份文档零提及。落地改 CW_ACTION_TYPES 时完备锁的双表遍历行为未定义（旧表含已退役类型即锁炸或锁空转）。
- **修正方向**：landing 3.5 范围补「PICK_ACTION_TYPES 退役/并入声明 + 完备锁单表化」，消费点（cw_action_registry 完备锁、其余 grep 实测）随批处理。

### M5 landing 3.1/3.2 文件面「`kernel/cw_strategy.py`」为幽灵路径——Match 加字段与 gated_hp 处置两处改形无文件面承载

- **文件:节**：landing §3.1 文件面行、§3.2 文件面行
- **发现**：glob 直证 `kernel/` 下无 `cw_strategy.py`（仅 `cw_strategy_session.py`）。`CurrencyWarMatch`（3.1 要加 `gs`/`performance` 字段）实际宿主 = `strategies/impl/cw_strategy.py:191`；`gated_hp`（3.2 括注「gated_hp 本体简化」）实际宿主 = 同文件 :255，且它只是薄委托，**门本体**在 `kernel/cw_hp_policy.py`。按字面派工：3.1 的 Match 字段、3.2 的 hp 锚删除连带（gated_hp 薄委托读 `session.last_hp/last_hp_t`，锚删后必须同批退役/改形）均无文件面授权。attack3 m5 报过同型错误（cw_reconcile 幽灵路径）并已修，本处为漏网同型。另 3.2 括注「gated_hp 本体简化」与代码事实（本体在 cw_hp_policy、cw_strategy 侧是委托壳）不符，易误导改错层。
- **修正方向**：3.1/3.2 文件面改 `strategies/impl/cw_strategy.py`；3.2 范围表述改「cw_hp_policy 门本体简化 + cw_strategy.gated_hp 薄委托随锚退役（消费点 6 处按 docstring 申报面改直读/换口）」。

### M6 design↔landing/篇内计数失同步三处残留（两处 attack3 已指认、声明消解后未改全）

- **文件:节**：design §2.7 / design §1.1+§2.6 / details §A vs landing §3.2+末阶段
- **发现**：①design §2.7「10 pick handler——其中 **8 个** handle/lifecycle 双路径」：直调 10 个 handler 类方法集，双路径实为 **9**（lifecycle_observe+lifecycle_decision_cycle 见于 encounter/supply_node/invest 双篇/megastar/partner/planner/bookcard/wish_trial；仅 box_pick 单路径）——attack3 m1 已指认，landing 3.5 已改「9 个」，design 未改，两文档现并存 8/9。②`game_state_of` 计数：§1.1「**291 处（src 树实测）**」值对标签错——291 是 attack3 的两仓「调用形态」合计（src 152+test 139），非 src 树数；本文普查词形态 src=287/test=175；§2.6 又写「**~250 处**」——同一词在两节三个数并存（attack3 m1 消解只动了 §1.1 的标注来源）。③删除族符号计数：details §A「普查词表 = **七符号**全仓」vs landing 3.2「删除线**八符号**」vs landing 末阶段「删除线七符号 + upcoming_types」——八符号（last_hp/last_hp_t/last_hp_real/last_hp_real_node/hp_suspect/last_level_obs/star_pending_regression/upcoming_types）是表格实列数，§A 的「七符号」与之矛盾（按末阶段口径七=不含 upcoming_types，则 §A 普查词表漏列本表成员）。
- **修正方向**：①design §2.7 改 9；②两节统一为一个口径并标明计数形态（建议：词形态、两仓、以落地普查表为准）；③§A 改「八符号」与 landing 对齐。

### M7 supply 刷新闸输入通道的「继承并就地重述」缺失：零参后 `decide_supply` 的 refresh 旗标承载全文档无着落

- **文件:节**：details §2.3 vs 被取代迭代 design.md §2.1-4；design §2.1/§2.2
- **发现**：被取代迭代 §2.1-4 明确 supply 等价方案：「入口读顶层容器字段 `gs.supply_refresh_used`（域键 node_screen_refresh 仅是分组名），派生式与现调用方逐字节相同」；本迭代 details §2.3 只重述了 `encounter_refreshed_in_visit` 完整契约（含「禁误接累计计数」告诫——仅 encounter 侧），supply 通道未重述。实现者读「`decide_supply()` 零参」后无法回答：刷新闸输入从哪读、是否与 encounter 同禁累计计数（实际语义相反：supply 现状调用方传的**就是**容器累计派生旗标，cw_screen_supply_node.py:209，入口读同一字段才等价）。game 侧文档（currency_war_supply.md:39「无刷新按钮,传 refresh_used=True」）与 cw_events.py:741 的 refresh 建议分支使该输入并非死参，不写即分叉。
- **修正方向**：details §2.3 补 supply 段：「`decide_supply` 入口直读 `gs.supply_refresh_used`（与现调用方派生式逐字节相同；encounter 的 per-visit 禁令不适用 supply）」。

### M8 「`decide_shop_action` 函数本体已 gs-first 零改动」口径仍失准：函数体内实存大量 session 消费，必改形却可按字面漏改

- **文件:节**：design §2.1「实现位分布」；landing §3.5 范围行
- **发现**：直调 `mandate_v1/shop.py:742` 起的 `decide_shop_action` 函数体：:770-772/:786/:806（`state_of(session).cw4_counters` 等）、:860/:884/:906-939（sell_gate/consume_on_merge）、:957-978/:1056-1295/:1383-1387 等——函数**体内** session/state 消费数十处，session 退役后必须随批改形。「本体已 gs-first 零改动」只有「签名第一参已是 gs」这半句为真；attack3 M1 判定 design↔landing 冲突后，landing 补了「模块内其余 ~68 处」括注，但「本体零改动」的字面读法仍把本体内消费点排除在改形面外——实现者按字面执行即漏改，且普查词表（strategy_state_of/state_of）能抓到但处置归属（本体 or 其余）无答案。
- **修正方向**：两处统一改为「`decide_shop_action` 签名已是 gs-first（输入通道无需改形）；其**体内与模块内全部 session 消费随批改形**（普查对账表兜底）」。

### M9 design §2.4 五镜像括注纳入 `enemy_difficulty` 与 fields.md §2.1 封闭集定义冲突（attack3 m3 的消解引入新失准）

- **文件:节**：design §2.4 表「五镜像」行
- **发现**：现文「五镜像（session 实名含 briefing_affixes/briefing_bosses/**enemy_difficulty** 等，逐字段见 details §B）」。正本 fields.md §2.1 五镜像封闭集 = `active_strategies/active_env/plane_bosses/enemy_affixes/selected_difficulty`（锁锚 test_cw_game_state_batch4，新增第六镜像须同步扩集与锁）。enemy_difficulty 不在封闭集；briefing_affixes/briefing_bosses 是 enemy_affixes/plane_bosses 的 session 实名（映射关系非同名字段）。括注把 enemy_difficulty 写进「五镜像（…）」内使「五镜像」一词与正本封闭集定义冲突——attack3 m3 要求的是「家族表补 enemy_difficulty 行」，不是把它塞进五镜像括注。
- **修正方向**：改为「五镜像（session 实名 ↔ gs 正本映射见 details §B）+ enemy_difficulty + chosen_* + last_streak + last_owned_equips」分行列举，保持「五镜像」与 fields.md §2.1 封闭集一一对应。

### M10 unified-obs-reconcile 3.4 相交面清单不全：3.5 的 telemetry/ 面与其相交零申报、依赖行不挂

- **文件:节**：design §2.10；landing §3.5（依赖行/文件面行）
- **发现**：design §2.10 只列「unified-obs 3.4 落码收（cw_screen_prep.py/cw_screen_buy_cards.py 相交）」。直调 unified-obs landing 3.4 文件面：还含 `telemetry/query.py`（分类器双函数删除）、`telemetry/match_archive.py`（注释指针）、`operations/cw_op/cw_shop_action_ops.py`（注释）。本迭代 3.5 文件面含 `telemetry/`（局终快照换源）——与其 query.py/match_archive.py 相交；3.5 依赖行只挂「3.1–3.4」不挂 unified-obs 3.4，telemetry 相交在任何依赖行/冲突面申报中均无（cw_shop_action_ops 被 landing 3.4 依赖行的「operations/ 面与其 3.4 相交」兜住，telemetry 无对应兜底）。
- **修正方向**：§2.10 相交清单补 telemetry 两文件；landing 3.5 依赖行补「unified-obs 3.4 落码收（telemetry/ 面相交）」。

---

## minor

### m1 过程叙事违规三处（iteration-design §5 硬规则 3，「本轮/修订后/已改」类措辞即打回）

- **文件:节**：design §0 状态行；design §2.9 第 4 条；details §A′ 首句
- **发现**：①design §0「状态：对抗审中（**r1–r3**）」——轮次过程信息渗入正文（进度已住 README）；②design §2.9「成本 = 分支判等对象替换（无计数器改造成本，**更正后事实**）」——修订痕迹措辞；③details §A′「**定性更正**：…」——同族。三者均属「过程住对抗报告」纪律的违例形态。
- **修正方向**：状态行改「对抗审中」；删「更正后事实」「定性更正」字样，直接陈述当前定性（探针族定性内容保留，去掉更正语式）。

### m2 design §2.2「选择族动作化（9 个非 CwAction 选择入口 + invest 对齐）」计数歧义残留（attack3 m1 半修）

- **文件:节**：design §2.2 小节题
- **发现**：§1.1 已按 attack3 m1 改为「8 个非 CwAction 选择入口」，§2.2 题仍写「9 个…+ invest 对齐」——按 attack3 修正口径应为「8 入口 + invest 换型 = 9 动作子类型」，现措辞仍可读作「9 个入口」。
- **修正方向**：改「选择族动作化（8 个非 CwAction 选择入口 + invest 换型，共 9 个动作子类型）」。

### m3 README 进度行仍携带用户四裁定内容句 + 「待 r4」预登记引用（attack3 m7 指认后未改）

- **文件:节**：README.md 进度节
- **发现**：「（r1 21 条/r2 21 条已消解；**用户裁定四条——刷新建议动作化/PickOption per-screen 子类型/HoldFrame 保留/识别防御缓存删除——已落 design §0/§2.2/§2.4**）」——README 自己声明「此处不设第二抄本」却又复述裁定内容，且轮次计数与裁定细节均为过程信息；「[attack4.md]（待 r4）」在报告落盘前为死链引用。
- **修正方向**：进度行收敛为「对抗审中 · 报告=attack.md/attack2.md/attack3.md/attack4.md」。

### m4 design §1.1 将节点探针族归入「识别层防御缓存」与 details §A′ 定性篇内矛盾

- **文件:节**：design §1.1 第 2 条 vs details §A′
- **发现**：§1.1「观察锚/识别守卫（hp 四锚、hp_suspect、**节点探针族**、last_level_obs、star_pending_regression）**是识别层防御缓存**」；§A′ 开篇即「**不是防御缓存**——是现役唯一真值源」。总纲症状叙述与详设定性直接冲突（详设以「定性更正」语式掩盖了总纲未同步的事实）。
- **修正方向**：§1.1 括注摘除「节点探针族」，改为「识别层防御缓存（hp 四锚、hp_suspect、last_level_obs、star_pending_regression、upcoming_types）与节点探针族（真值源，另见 §2.4 重锚行）」。

### m5 landing 3.4/3.5 设计依据使用非正式节名「details §game_state_of / §StrategyState」

- **文件:节**：landing §3.4/§3.5 设计依据行
- **发现**：details 实际节名 = 「§3 StrategyState 外部读者迁移」「§4 game_state_of 访问口退役」；「§game_state_of/§StrategyState」可唯一解析但不精确，违反「引用锚存在性与可解析性」的严格口径。
- **修正方向**：改「details §3/§4」。

### m6 `last_node_type` 归入「重锚六符号（不删）」类目，但其无 gs 宿主、实际处置 = 字段删除——与 §A′「迁移契约 = 值等价换宿主，非删除」矛盾

- **文件:节**：details §A′ 表第 2 行及迁移契约句
- **发现**：重锚后读点直读 `node_kind_of(gs)`，`last_node_type`/`node_type_current` 两个 session 字段本体随 session 退役**删除**（无 node_books 落位行）；「重锚六符号普查、承载桶 = 重锚」的归类把两个删除字段混入「不删」类目，普查对账表的桶判定会歧义（cw_screen_prep 写点族 :511/:638/:2536/:2543 是删除而非重锚）。
- **修正方向**：§A′ 表该行拆注：「读点重锚 node_kind_of(gs) 直读；session 字段本体随载体退役删除（写点族 = 左移推断装配删除面）」。

### m7 「`cw_decision_trace` 模块零接线不引用」措辞不精确，且该符号不在任何普查词表

- **文件:节**：design §2.8 终验行；landing §3.7
- **发现**：直调 grep：`install_decision_trace`/`record_decision_frame` 生产零调用（「零接线」✓），但 `mandate_state.py:154/:169`、`economy_cycle.py:249-250` 注释仍引用「cw_decision_trace 披露族」，`cw_game_state.py:927` 提及其为消费方——「不引用」不成立（注释形态在册）。landing 3.7 以「零接线不引用」为 smoke 锚前提，末阶段普查词表却无 `cw_decision_trace` 一词，注释残留无清零兜底。
- **修正方向**：措辞改「零接线（生产零调用）；注释残留引用随 3.5 注释锚复核清零」，末阶段普查词表补 `cw_decision_trace`。

### m8 普查对账表的计数口径未定义：「归零」判据的匹配形态（词出现 vs 调用形态）无规则

- **文件:节**：design §2.5/§2.6；details §3/§4；landing 首节
- **发现**：词表只给词与范围，未钉死匹配形态。实测两种口径差异巨大（`game_state_of`：调用形态 src=152 vs 词形态 src=287）；「符号普查归零」在两种口径下是不同的完成判据。attack3 与本报告计数不一致的根源即此。
- **修正方向**：landing 首节普查定义补一句：「匹配形态 = 词出现（含注释/docstring/字符串），逐桶归类时标注实码调用与纯叙述锚；归零判据 = 实码调用归零 + 叙述锚改指/清零」。

---

## 三核覆盖说明

### 核三（治本）：零发现 + 实际攻击过的面

- §1 归层（约定层）成立性：契约三维度（生命周期/输入形状/输出形状）从未按终态立约、session 三类混装的「策略实例无状态」历史妥协定性（flow/session.md §1）与代码现状吻合——归层成立，无发现。
- §2 治本性：构造注入消灭「无参构造+旁路冷建」、零参消灭「载荷旁路」、载体解散消灭「重复账」、输出单动作词表消灭「第二返回族」——四条均指向约定层根因，非症状补丁；「明确不解决」清单对 kernel 判据语义、库存域建模、识别优化的边界划出有依据。无发现。
- 同族问题第二次出现检查：session 载体治理链（execstate-dissolution → turnstate-retirement → 本批）是同一根因的分步收口而非逐件打补丁，末批以「类本体退役」收尾，符合「升级架构级收口」形态。无发现。
- 实际攻击过的面：四条终态契约各自与 00/01 宪法的相容性（构造注入不触 hp 硬闸门辖域——λ 血带消费经 decision_hp 的通道在 §A 删门后改 gs.hp 直读，仍属 00 §3 已授权的 λ 表输入面，无新增闸门外溢）；「一步到位」取舍的风险补偿结构（§2.9）；兼容裁定与注册面封闭集依据（flow/README §2.4 直对 ✓）；Match 终形 `{gs, strategy, performance}` 的所有权语义（details 关键取舍末条）。

### 核一（无前提）实际攻击过的面（除上述发现外零发现的面）

- 跨文档引用锚存在性：design↔details↔landing↔README 全部相对链接与节引用逐一解析（除 m5 节名不精确外全部可解析；正本更新清单 16 个正本路径全部实存，含 `docs/game/screens/currency_war_supply.md` 与 `货币战争-补给.md` 的「decide_supply 传 refresh_used=True」句 :39 直对 ✓）。
- 阶段可验收性逐阶段试读：3.1（纯增量，零行为——新动作类型/域键/挂点均可单测验收；B3 的函数退役除外）、3.2（除 B1/M5 外可验收）、3.3（briefing 非机械消费面四点直对代码：cw_screen_prep 写点保位、空门语义在 cw_observation relay 段注 2621-2625 在册）、3.4（桶口径清晰，行为零变化=值同一实例成立）、3.5（除 B2/M3/M8 外）、3.6/3.7（可验收）。
- 「实现者无需再设计」试读：十二槽表逐槽、三分语义、per-visit 位契约（写 False/写 True/fail-loud/None 缺省/窗语义五要素与被取代版逐字一致）、刷新链分屏形态（encounter 同访问二次覆盖 vs supply/invest 交回重入）、属屏映射十行与 `_dispatch_identity_screen` 分发臂（cw_loop.py:1326-1604）逐行对上、分流注（武装箱弹窗无 decide）属实、路由取值规则与早退/未知兜底两路径语义与 cw_loop.py:1715 stop_at_prep 位置（分发之前）吻合、HoldFrame 分支落点与 cw_screen_prep.py:1545-1552 的 F3→None→validate→execute 现役序列吻合（HoldFrame 于 F3 前拦截，不进 validate/注册表/续段 token ✓）、`encounter_refreshed_in_visit` 与 execstate 落地现状的分工（handler 侧累计闸保留 = cw_screen_encounter.py:320/:451 读 `gs.encounter_refresh_used` 现状原样 ✓）。
- 机制等价性主张逐点验：rng `None→0` 与 establish_new_match 覆盖逻辑（cw_strategy_manager.py:77-78）逐位等价 ✓；「实例不跨局/局容器弃置连带回收」与 establish_new_match 幂等门+discard_stale_match_container 保留语义一致 ✓；journal 装配「唯一锚 = game_state_of 建立路径」断言与生产唯一 provider 注入点（cw_strategy_manager.py:91）吻合，重锚至引导漏斗 gs 构造点机制等价 ✓；「gs.hp 有结算覆盖写端」断言与 apply_settlement_cover（cw_screen_battle_wait.py:526-541，同 HP_CONFIDENCE_THRESHOLD 门）直对成立 ✓；五条注册行换键名与 cw_action_registry.py:149-153 逐行对上 ✓；actor 预登记三缺（CwScreenPlanner/CwScreenBoxPick/cw_loop_route_clear）与 REGISTERED_ACTORS 现状（cw_game_state.py:284-335）核对属实 ✓；relay 六调用「输入 100% 为 §B 待删字段」与 cw_observation.py:2410-2449+2633-2651 值源逐行核对成立 ✓；`upcoming_types` 唯一消费=buy_cards journal 软兜底（:1028）属实 ✓；§A′ 四个行锚（cw_discipline_rules:200/flow.py:169/entry.py:787/battle_wait:424）逐一直对成立 ✓；sim 零策略构造与回放 `--run` 面 create_session（sim/cw_replay.py:108）申报属实 ✓；buy_cards 防御路径裸构造（:799-814）实存、改经漏斗的等价性（职级吸收/装配触发）核对无行为分叉 ✓。
- 继承声明抽查：十二槽表/三分语义/属屏映射/encounter per-visit 契约四项与被取代迭代逐段比对语义一致（supply 段缺失见 M7）；被取代版「cw_decision_trace 为现行决策记录载体」的过期断言在本稿已更正为「journal 唯一在产、零接线」——与本报告 grep 直证一致（更正正确，措辞瑕疵见 m7）。

### 核二（规范遵循）实际攻击过的面（除上述发现外零发现的面）

- 四文档构成合规（总纲 §0-§2/详设三部分/landing 阶段小节七件齐含固定末阶段/README 两节）；标题层级、阶段排序、依赖闭链（3.1←无、3.2-3.4←3.1、3.5←3.1-3.4、3.6←3.5、3.7←3.6、末阶段←全部+unified-obs 正本批）自洽。
- 依据就地标注：设计稿关键主张多数带符号锚/正本节号/用户裁定指针，抽查锚（fields.md §2.2 例外、§3.4.4、journal.md §6 豁免类、flow/README §2.4 封闭集、chain-observation 承接）全部实存可解析；被攻处即上列各条（计数词、消费面枚举、文件面）。
- 阶段「通用工程门（本文首节定义）」引用形态合规（单一定义+引用不复述）；正本更新清单行格式（正本：节 ← 阶段）合规；README 不放判据基本合规（m3 残留除外）。
- 全量同步复查（硬规则 4）：本轮实际执行——四份文档间同一主张的口径对账结果即 M6/M9/m3 等条目；引用符号/路径存在性复查结果即 M5/m5/m7。
