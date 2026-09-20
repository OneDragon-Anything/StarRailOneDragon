# 对抗审查报告（无前提轮 · attack2）

**总判定：blocker 2 / major 5 / minor 2 —— 方向（消灭换形、单形状容器化）治本成立，但退役清单与阶段闭合集远小于真实迁移面：大批 BenchChar 形状符号与 ~30 文件消费面无阶段归属地堆进 T-6「grep 归零」，T-4 种子层方案自相矛盾（装箱通道本身吃 CwSimFrame）。照此开工，T-4/T-6 必然卡死或被迫在无审查语境下现场设计。**

> 判据源：iteration-design.md §5/§7（直读）、AGENTS.md 文档规范（always-on）、代码真值（grep + 直读 src/sr_od/application/currency_war/ 与 sr-od-test/）。未读 attack.md 及任何前轮报告；未读 landing/README（本轮禁读范围），目录构成经 glob 核实。全部证据为独立取证。

---

## 逐条发现

### [blocker] A1. 退役符号清单与阶段面漏掉整族 BenchChar 形状符号及其 ~30 文件消费面；T-1+T-2「闭合集 = 全部直调方」名不副实，T-6 实为最大的未设计迁移批

**证据**：
- 设计 §2 退役符号列了 `bench_slots_of`/`unit_rows_to_deployed`/`deployed_place`/`_apply_row_to_char` 等，但**未列**同族换形/形状函数：`deployed_slots_of`（cw_game_state.py:3962，经 `unit_rows_to_deployed` 产出 `list[BenchChar|None]` 10 槽表——`unit_rows_to_deployed` 退役后它必须随之退役或重写，设计未裁决）、`deployed_slots_to_rows`（:1574，上报族 buy_card/deploy_move/sell_deployed/swap_deploy/collect_ore 五文件在用的逆换算）、`bench_from_compact`/`deployed_from_compact`（cw_exec_state.py:288/:390，cw_reconcile 写回端在用 ：341-346）、`rebuild_deployed_from_board`/`pad_bench`/`pad_deployed`/`bench_clear`/`deployed_clear`/`iter_occupied`/`bench_occupied`/`bench_occupied_slot_nos`/`board_by_row`/`board_unique_key`（cw_exec_state.py:209-398 全族 BenchChar 签名）。
- 消费面 grep（本轮独立执行）：`bench_slots_of|deployed_slots_of` 在 src 合计 **~130 处引用、30+ 文件**，其中 T-1..T-5 各阶段点名的只有 tracked_books 读写端、上报族、sim 两处、cw_deploy_logic/sell_gate/mandate_v1 判定、obs 链；**以下消费文件不在任何阶段的点名面**：cw_comps、cw_economy、cw_intention、cw_events、cw_system_cards、cw_line_switch、cw_launch_admission、cw_performance、cw_battle_calib、cw_bench_equips、cw_equip_wear_plan、telemetry/schema.py、flow.py、entry.py、shop.py、criteria/sell.py、statefn/predicates.py、economy_cycle.py、cw_loop.py、cw_screen_prep、cw_shop_action_ops、sim/cw_sim_pool。
- 这些消费点大量直接读 BenchChar 字段（`bc.faction`/`bc.star`/`bc.slot`/`bc.char_id`/`is_item_slot`），如 cw_system_cards.py:224 `board_by_row(deployed_slots_of(gs)).count(faction)`、cw_battle_calib.py:71/195、telemetry/schema.py:181。

**杀伤说明**：这些消费点在 T-1..T-5 期间照旧绿（`bench_slots_of` 读 `gs.bench.value`，不读 tracked_books），全部迁移压力落到 T-6「删 BenchChar/换形函数与全部引用；全量 grep 归零」——一个阶段内无任何逐文件设计地重写 30+ 文件的读取形状。每个消费点都要现场回答：`bc.slot` 换成什么（BenchSlot 无 slot 字段，下标即槽位）、faction 怎么来（见 A3/A4）、占位件在 BenchView 下如何过滤（原 `is not None` 现在要 `kind=='unit'`——`empty` 槽与 `ore` 语义差异）。这正是硬规则 2（实现者无需再设计）禁止的形态，且「逐阶段测试全绿」的阶段性承诺对最大迁移批失效——要么 T-6 巨型单提交违反分阶段纪律，要么实现者自行拍板产生实现与设计意图分叉。

**修复方向**：退役清单补全（至少 `deployed_slots_of`/`deployed_slots_to_rows`/compact 族/清空族/计数族逐一裁决去留），并把 30+ 消费文件按域拆进 T-3/T-6 前的独立阶段，逐域写明字段映射约定（slot→下标、faction 派生点、占位件过滤口径）。

### [blocker] A2. T-4 种子层方案自相矛盾：`synthesize_from_game_state` 本身吃 `CwSimFrame`；且测试直产面远大于申报的「cw4_feed/cw4_box 87 处/18 文件」

**证据**：
- cw_game_state.py:3624 `def synthesize_from_game_state(gs: GameState, st: CwSimFrame, *, ...)` —— 设计 §5 T-4 说「`CwSimFrame` 删除 + 测试种子层 `cw4_feed`/`cw4_box` → `synthesize_from_game_state` 装箱」，但被指派的装箱通道签名第二参就是被删类型，删帧后种子输入形状是什么，设计未回答。
- 测试仓独立 grep：`CwSimFrame` **87 处 / 19 个测试文件**（大量直接构造，如 test_cw_budget_disclosure.py:208 `CwSimFrame(gold=0, gold_readable=False, ...)`、test_cw_pair_progressive.py:55、test_cw_p2_blood_band.py:65）；`BenchChar(` 直接构造 **120 处 / ~30 文件**，且 kwargs 含 `faction=`（test_cw_loop_op_fail_redispatch_cap.py:227-229、test_cw_sim_engine.py:190 faction='散'）、`position_pref=`（test_cw_unified_action_2b.py:201、test_cw_exclusive_wear_gate.py:81）、`is_item_slot=True`（test_cw_sell_item_slot_predicate.py:58、test_cw_seat_recoverable_narrow.py:73）、**注册表外角色名**（test_cw_unified_action_2b.py:112/115/151「注册表外散件」）。
- 而 `cw4_feed`/`cw4_box` 词表实测仅 77 行 / 15 文件（含 _cw_helpers 自身）——申报「87 处/18 文件」的数字与 CwSimFrame 引用数（87）吻合、与 cw4 系词表不吻合，口径疑混用。

**杀伤说明**：① T-4 删帧时，`synthesize_from_game_state` 必须同步重写（输入形状未设计 = 卡死或现场设计）；② 直接构造 `CwSimFrame`/`BenchChar` 的 ~35 文件测试全部要改写，其中 faction/position_pref 直种与注册表外名在「faction/position_pref 不入形状、经注册表派生」的终态下**没有表达通道**（`bench_slots_to_legacy` 对未知名派生 faction='?'，cw_game_state.py:1522-1523）——这些测试锁的现状语义（faction 分桶计数、front 位选排）在终态种子层不可复现，要么测试被迫删锁（覆盖率倒退），要么设计被迫开洞（faction 可种）——两者都是本设计未裁决的分支。

**修复方向**：T-4 明确删帧后 `synthesize_from_game_state` 的新输入契约（或另立种子构造器），并显式裁决测试侧 faction/position_pref/注册表外名的表达通道（测试专用注入口或改写锁面）。

### [major] A3. §2「position_pref …现 `bench_slots_to_legacy` 同款派生搬进消费点」主张失真——bench 侧现状是**不派生**（恒缺省 'back'），照「单一源 = get_char(char_id).position_pref()」实施 = 部署选排隐藏行为变化

**证据**：cw_game_state.py:1519-1526 `bench_slots_to_legacy` 构造 BenchChar 时**不写 position_pref**（BenchChar 缺省 'back'，cw_exec_state.py:181）；消费点 cw_deploy_logic.py:2186 `pref = (getattr(bench[bi], 'position_pref', None) or 'back')` 按 bench 候选的 position_pref 选排。即现行生产行为 = bench 候选**恒首选后排**。设计宣称单一源 `get_char(char_id).position_pref()`（cw_chars.py:40）且称这是「同款派生」——两者语义不同：front 位角色（注册表 position_pref='front'）在新派生下选排翻转。

**杀伤说明**：实现者面对自相矛盾的指令（「同款派生」vs 单一源注册表）二选一：搬现状 = 全 'back'（与「单一源 get_char」句冲突，review 必打回）；用注册表 = 部署拖拽选排行为静默改变，违反 §3「语义逐位不变、禁顺带改行为」——§3.5 只申报了开拓者归一的统一，未申报此差异。

**修复方向**：明确裁决 bench 侧选排偏好终态（恒 'back' 照旧 or 注册表派生并作为行为变化显式申报 + 补锁），删除「同款派生」失真表述。

### [major] A4. faction 消费面界定为「部署装配需要时」失真——faction 的非装配消费（board 阵营计数/羁绊）大量在案且无迁移设计

**证据**：cw_system_cards.py:224 `board_by_row(deployed_slots_of(gs)).count(faction)`（阵营 floor 判据）；cw_bond_equips.py:112-132（羁绊按 faction、开拓者归一）；cw_board_by_row.py:11-44（羁绊标签全集，防御性再归一）；测试侧 faction 直种（test_cw_loop_op_fail_redispatch_cap.py:227）。设计 §2 只写「部署装配需要时经注册表按 char_id 派生」。

**杀伤说明**：board 计数/羁绊链的 faction 读取不属于「部署装配」，照设计 grep「部署装配」找不到这些点；若这些消费点改为注册表派生，未知名（SIFT 直读名、注册表外名）从现值（obs 构造期已派生或 '?'）变成另一条派生路径的值——阵营计数行为漂移无锁可拦。

**修复方向**：faction 派生点清单按真实消费面枚举（装配/board 计数/羁绊三类），逐类声明派生式与未知名缺省口径。

### [major] A5. deployed 侧 tracked 快照「同批声明（对抗审 R2）」无落点——目标形状未定稿

**证据**：设计 §2 line 16「deployed 侧快照形状同批声明（对抗审 R2）：ADR-0392 保洞语义与 deployed_idx 坐标恒稳（行下标基不变），禁借迁移改索引语义」——全文再无该形状的声明；而写回端现状是 10 槽表（cw_reconcile.py:345 `deployed_from_compact`、prep_actions.py:800 `deployed_place`），行下标基（front_row 0-3 / back_row 0-5 行内）与 ADR-0392 的 0-9 全表下标**不是同一坐标系**，「行下标基不变」与「deployed_idx 恒稳」并存时如何同时成立（front_row[3] 与 back_row[?] 的 idx 派生式）未写。

**杀伤说明**：T-1 改 `TrackedBooks.deployed` 时实现者必须自行决定快照是「(front,back) 行对」还是「10 槽表」，以及 `deployed_idx`（动作参数坐标系，ADR-0392 0-9）如何在行形状上派生——正是硬规则 2 的「待定 = 未定稿」形态，选错即 deployed_idx 坐标事故（陈旧提案代际校验错位）。

**修复方向**：§2 直接写死 deployed tracked 快照形状 + deployed_idx 在该形状上的派生式。

### [major] A6. 过程叙事遍布正文、状态值非规范枚举、依据指向过程文档（iteration-design §5 规则 3、§2.1 §0）

**证据**：design.md line 3「对抗审 B1 裁定」、line 4「首轮对抗审 blocker×1/major×5/minor×4 已收编，待复审确认后开工」、line 14/15/16/17/26/28/31/39/42/44 共十余处「对抗审 R3/M5/R1/R2/R5/M1/M2/M3」标签。iteration-design §5 规则 3：「不写谁审的、第几轮攻击……『本轮/修订后/已改』类措辞即打回」；§2.1 §0 状态枚举 = 草案/对抗审中/定稿，「设计修订轮（待复审）」不在枚举内。「对抗审 X 裁定」作为设计依据 = 依据指向 attack.md（过程文档，随 changes/ 清理死亡），也违反规则 1「依据 = 来源文档+节/直调数据表/已证命题」。

**杀伤说明**：定稿试读（假实现者）无法追溯「对抗审 R3」指什么——裁定内容必须自足写进正文；报告清理后全部引用死亡。

**修复方向**：所有「对抗审 X」标签改为自足的裁定陈述（结论+依据）；状态改规范枚举。

### [major] A7. 阶段拆分寄居 design.md 且七件不全；landing.md 缺失——阶段无「账本唯一源」

**证据**：目录 glob 仅含 README.md / attack.md / design.md，**无 landing.md**；design.md §5 内嵌 T-0..T-6 阶段（「账本 T-0..T-6」）。iteration-design §1：changes/ 构成必有 landing.md（唯一一份：阶段拆分与验收）；§3.1：阶段小节七件（范围/设计依据/文件面/依赖/优先级/完成判据/验收凭据形式），且「阶段小节 = 账本唯一源」。design 内嵌阶段缺文件面、依赖序、优先级、验收凭据形式，T-1+T-2 的「闭合集」无法被验收对照。

**杀伤说明**：账本立任务无七件套小节可指，criteria 预注册悬空；阶段内容在 design 与（未来的）landing 之间必然双源漂移（iteration-design §5 规则 4 所防事故）。

**修复方向**：按模板落 landing.md（T-0..T-6 七件齐），design §5 只留方案级分期意图。

### [minor] A8. §2 tracked_books 形状描述失真：「`list[BenchChar|None]`」实为 `TrackedBooks` dataclass 双列表

**证据**：cw_game_state.py:2064-2075 `class TrackedBooks`，字段 `bench: list` / `deployed: list`；设计 §2 line 16 写「GameState.tracked_books（cw_game_state.py，`list[BenchChar|None]`）」。

**杀伤说明**：按字面理解会找错宿主/写错迁移面（真实读写端都是 `.bench`/`.deployed` 两列表）。

**修复方向**：改为「TrackedBooks.bench/deployed 两槽位表」。

### [minor] A9. 面清单数字口径不可复核/疑混用

**证据**：§4「96 文件/~880 引用」无口径（哪个词表、src 还是含测试）与依据标注（硬规则 1）；§5 T-4「87 处/18 文件」与 cw4_feed/cw4_box 实测（77 行/15 文件）不符，恰与 CwSimFrame 测试引用数（87 处）吻合。

**修复方向**：注明词表与范围，或修数。

---

## 三核小结

- **核一·无前提**：非零发现（A1/A2/A3/A4/A5/A8/A9）。攻击面：退役符号全集 grep 普查（换形函数族/形状助手族/逆换算）、消费面普查（bench_slots_of/deployed_slots_of/faction/position_pref/tracked_books/CwSimFrame/BenchChar 含测试仓）、逐条事实主张对码（serialize_state 委托 ✓ schema.py:236-252、cw_replay ✓、三死函数零调用 ✓ 含测试仓、sim 两处 bench_place 直调 ✓、`_bench_view_keep_items` ✓、swap 有归一/deploy_move 缺归一 ✓ swap_deploy.py:78 vs deploy_move.py:63-68、T-0 两锁现状主张 ✓——这些主张核过为真，未列发现）。
- **核二·规范遵循**：A5（未定稿/待定）、A6（过程叙事+状态枚举+依据形态，§5 规则 1/3）、A7（landing 缺失+七件不全，§1/§3.1）、A9（依据标注，规则 1）；AGENTS.md 文档规范（直白表述/as-built 无状态）同 A6 判。
- **核三·治本核验**：§1 归层成立——信息销毁点确在表示层（BenchChar 装不下五分类，`bench_slots_to_legacy` 压成布尔，collect_ore.py:62 在案），§2 消灭换形 = 修根而非症状，方向治本。但「完成容器化迁移的计算层收编」这一雄心与阶段闭合集的真实覆盖之间断裂（A1/A2）：治本方案被未闭合的执行设计拖累，按现稿开工的最大风险不是方向错，而是 T-4/T-6 两个巨型无设计批。跨件半问：无同族第 N 件症状补丁迹象。
