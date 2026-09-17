# attack2 —— 策略器终态契约 迭代设计 对抗审查报告（r2，独立干净上下文）

> 审查对象：本目录四份文档（design.md / details/session-dissolution.md / landing.md / README.md）。
> 判据源：`docs/develop/harness/iteration-design.md`（四硬规则+§7 三核）、`strategy-docs/00_framework.md`/`01_math_framework.md`、`game_state/fields.md`、`flow/README.md`/`flow/session.md`/`flow/outer_loop.md`/`game_state/journal.md`/`flow/action_exec.md`、正本树（strategy-docs/screens/architecture/sim/docs/game）、代码真值（`src/sr_od/application/currency_war/` 逐文件直调）、在飞迭代四目录、AGENTS.md §8-§11、`.dsh/skills/sr-od-currency-war-dev/references/strategy-work.md` §6。
> 方法：全部数值/符号/引文直调复核（全仓两仓 grep 普查 + 代码体阅读），禁转述；被取代目录 `strategy-input-unification` 仅用于核「继承并就地重述」声明的真实性，发现均以现行代码为准。未读本迭代 r1 报告（无前提纪律）。

## 发现总览

- 总数 **21**：blocker **2** / major **9** / minor **10**。
- 三核均有发现：核一（无前提/覆盖完整性）B1/B2/M3/M4/M5/M6；核二（规范遵循）M8/m1/m3/m4/m5/m9；核三（治本）B1（治本主张「残影删除」与链观察批的「各司其职」定性冲突）。

---

## blocker

### B1 探针族删除把 cw_plane_table 日程/视界/hp 时基真值链整条悬空，设计零承载

- **位置**：design.md §1.3/§2.4 表（识别层防御缓存行）；details/session-dissolution.md §A（`plane_node_table`/`plane_node_table_plane`/`plane_lengths_seen`/`nodeseq_probe_anchor` 行，「同上=chain 单源对齐删除」「旧机制残影」）；landing.md §3.2。
- **发现**：§A 把四个探针字段定性为「旧机制残影」并整族删除，但代码事实是它们是**现役唯一真值源**，不是残影：
  - `kernel/cw_plane_table.py::schedule_of`（:80 `getattr(session,'plane_lengths_seen')`）与 `::nodes_of_plane`（:122 `getattr(session,'plane_node_table')`）——位面日程/位面轮数的 ADR-0368 单一源；
  - 下游判据面（全部 live）：`cw_discipline_rules.py:204`（boss 停手 `nodes_of_plane`）、`cw_economy.py:1136/1424`（R_剩余/总轮数）、`cw_intention.py:374/902`、`cw_line_switch.py:204`（禁换判据）、`cw_hp_policy.py:101`（**hp 新鲜度门时基 `node_t_of`**）、`cw_screen_battle_wait.py:457`（**结算锚 `last_hp_t` 写点，与读口同式契约禁单侧改式**）、mandate_v1 全家（`encounter.py:257`/`proof.py:494`/`shop.py:1301,1749,2347,2519`/`levelup.py:340`/`budget.py:141`/`statefn/horizon.py`）；
  - 写端 live：`cw_screen_prep.py::store_plane_table`（:207-227，链观察落地批明确「关店探针本体维持现状不动……各司其职」）。
  - `changes/2026-09-16-chain-observation-landing`（已落 HEAD）只把**节点类型**归链单源，并把探针族退役显式划归「另批承接范围 = 消费点重接 + 同族载体盘点」——本批接了盘，却**未接消费点重接**：链（`gs.node_path`）承载类型序，位面**长度派生、未揭晓位面回退 (9,9,9)、[1,9] 脏表夹取、sim 合成口径、`node_t_of` 双端同批改式**均无契约。
  - 连带矛盾：design §1.3「明确不解决：kernel 判据语义与纯函数签名」——`schedule_of(session)/nodes_of_plane(session)/r_remaining(session,…)/node_t_of(session,…)` 的 session 形参随解散必须改形，§1.3 的豁免口径与 §A 删除面互相打架。
  - landing §3.2 文件面（`cw_strategy_session/cw_hp_policy/cw_equip_wear_plan/读写点普查表驱动`）与完成判据（hp 门对照/单调守卫/防抖窗）均无 `cw_plane_table.py` 与日程真值等价对照项；普查词表（十字段）能发现 `cw_plane_table.py:80/122` 的读点，但 §A 承载桶只有「随本阶段删/不辖申报」——schedule_of 不可删、无处归。
- **修正方向**：§A 拆出「探针族退役 = 真值重锚批内工程」：①声明 `schedule_of`/`nodes_of_plane` 换源契约（gs 链长度派生 + 回退/夹取语义逐条保留）；②`node_t_of` 同式契约双端（结算锚写点与决策读口）同批切换的硬约束；③landing 3.2 增文件面 `kernel/cw_plane_table.py` 与「改前/改后 schedule/nodes_of_plane/R_剩余逐节点对照」判据；④§1.3 的 kernel 签名豁免句补「cw_plane_table 族换源改形」申报。

### B2 session 解散地图覆盖缺口：`enemy_difficulty` 全字段无归位；`briefing_affixes`/`briefing_bosses` 字段名错位致普查词表漏接

- **位置**：details/session-dissolution.md §A/§B/§C 全表（约束①「每字段迁移后读到的值与迁前逐字节相同」）；design.md §1.1/§2.4；landing.md §3.3 完成判据「普查对账表（B 表字段名 + 两帧类槽名）」。
- **发现**：`StrategySession` 现役 dataclass 31 字段（`cw_strategy_session.py:119-234`），逐一对表后：
  - **`enemy_difficulty`（:186）在 §A/§B/§C 全部无归位**（五镜像封闭集 = fields.md §2.1 五字段，不含它）。live 读点：`cw_observation.py:2311-2323`（真读失败回退 session 值的读链）、`cw_reconcile.py:545-547`（喂 `opening_hp_prior` 开局 hp 先验）、`cw_opening_hp.py:47-56`。gs 侧有正本（fields.md §3.2.14、sim §9.4 行 32），属 §B 同型重复账，但 B 表没列它。
  - **B 表用 gs 名冒充 session 名**：表列 `enemy_affixes`/`plane_bosses`，session 实际字段名是 `briefing_affixes`/`briefing_bosses`（:182/:190）。details §B 虽有「实际名以普查为准」 hedging，但普查**词表本身 = 「B 表字段名」**（landing 3.3）——按表名 grep，`briefing_affixes`/`briefing_bosses` 零命中，两个字段整体逃逸普查。
  - 两字段消费面非「读 gs 份即可」的机械换源：`cw_entry_plane_intel.py:93-181`（「已有 briefing_bosses 不重复采」跳过门 + 保位写 3 槽/仅空时写）、`cw_screen_prep.py:1884-1945`（briefing_bosses 空门 = 触发位面情报采集 + 保位写）、`cw_observation.py:2463-2466`（session 镜像→gs 五镜像的中继写）。`briefing_bosses` 元素可 None（徽章态保位勿滤）与 gs `plane_bosses` Field 的 None/空语义差异、空门判据迁 gs 后的等价判定，均无逐字段值等价声明——直接违反本篇自设约束①。
- **修正方向**：§B 补三行（`briefing_affixes`→`gs.enemy_affixes`、`briefing_bosses`→`gs.plane_bosses`、`enemy_difficulty`→`gs.enemy_difficulty`），写端/读端逐点换源清单（含上述 7 个文件锚），并显式给出空门/保位/None 元素三态的值等价映射；landing 3.3 词表改「§B 全字段 session 实名 + gs 正本名」双词普查。

---

## major

### M1 武装箱打分消费点锚错：`cw_equip_wear_plan` 无此消费，真点在 `flow.py::decide_box_card`；landing 3.2 范围与文件面自相矛盾

- **位置**：landing.md §3.2（范围「`last_owned_equips` 删 + 武装箱打分输入改 `gs.equips` 现值」；文件面「`kernel/cw_equip_wear_plan.py`（打分输入）」）；details/session-dissolution.md §B 特例行。
- **发现**：直调复核：`cw_equip_wear_plan.py` 全文零 `last_owned_equips`/`pick_equipment` 引用（其输入 = `prep_obs_frame.owned_equips`，:163——那是 3.5 的 prep_obs 迁移面）；武装箱打分的 `last_owned_equips` 消费点 = `strategies/impl/flow.py:663`（`decide_box_card` 内 `spare = getattr(session,'last_owned_equips')` → `pick_equipment(owned_spare=…)`）。该文件**不在 3.2 文件面**（3.5 才含 strategies/impl/）——范围要求本阶段改的代码落在文件面之外。
- **修正方向**：3.2 文件面去掉 `cw_equip_wear_plan.py` 误锚、补 `strategies/impl/flow.py`（或把 `last_owned_equips` 特例整体挪进 3.5 的 decide_box_card 重写）；其余读写点（`cw_exec_state.py:83-147`、`cw_op_equip_all.py:93-96/480`、`cw_screen_prep.py:740`、`obs/cw_observation.py:2666-2671` 载体中继兜底）显式列入普查承载清单。

### M2 design §2.1「mandate_v1/shop.py 本体已 gs-first 零改动」失实

- **位置**：design.md §2.1「实现位分布」。
- **发现**：`mandate_v1/shop.py` 现役 **68 处 session 消费**：`decide_shop_action(gs, session, config, registry)` 签名（:749）、`sell_gate.sell_exclusions(session,…)/obligation_book_of(session)`、全文件 `state_of(session)` 族（cw4_counters/commit_signals/target_comp…）、`game_state_of(session)`。StrategySession 类退役（§D）后这些签名与取口必须全部改形——「零改动」不成立；且与 landing §3.5 自己的文件面（`strategies/impl/(cw_strategy/flow/bridge/shop)`）矛盾。该句会误导波及面/工作量评估与「机制等价性」试读。
- **修正方向**：改为「决策本体判据零改动、载体通道（签名/取口）随批改形」，并把 shop 内 `state_of/game_state_of` 改形点纳入 3.5 普查承载桶。

### M3 防御路径裸 Match 构造在新 Match 终形下无 gs 来源

- **位置**：design.md §2.1（Match 终形 `{gs, strategy, performance}`、构造 `cls(gs, config)`）、§2.7（「buy_cards 循环+防御」调用点行）；landing.md §3.5。
- **发现**：`cw_screen_buy_cards.py:816`：`match = CurrencyWarMatch(_def, _def.create_session(config))`——「无对局态（独立 run_operation 调本 op）」的生产可达防御路径。终态下构造需要先行持有 `gs`，而该路径现状正是「无容器」语境（旧路径靠 `create_session`+`game_state_of` 惰性建容器）；设计未给该路径的容器 bootstrap 契约（构造一次性 gs？复用什么？写槽/观察失约语义如何）。被取代设计 §2.5 曾钉「防御路径语义不变」，重述丢失。
- **修正方向**：§2.7 补防御路径行：gs 的构造/来源、`strategy_state`/prep_obs 缺席时的行为口径、以及 3.5 完成判据加「run_operation 直跑商店 op 冒烟」。

### M4 终验锚前提失实：`cw_decision_trace` 现役零接线，「决策迹锚对照」无对照物

- **位置**：design.md §2.8（终验「`cw_decision_trace` 决策迹锚与改前同难度局对照」；可观测性申报「HoldFrame 帧入决策迹」）；landing.md §3.7。
- **发现**：全仓两仓直调：`install_decision_trace`/`record_decision_frame`/`reset_decision_trace_anchor` **零生产调用点**（`cw_decision_trace.py` 内定义外仅注释引用；economy_cycle/mandate_state 命中均为注释；sr-od-test 零命中）。该模块现役无写入路径——「改前同难度局对照」不存在对照物，「HoldFrame 帧入迹」缺装配点/行 schema 申报。此锚系从被取代目录继承，未对码。
- **修正方向**：三选一并写入设计：①申报决策迹接线批（装配点+record 调用位+HoldFrame 行形态）为 3.5 内子项；②终验锚换现行可执行形态（journal 行/回放 plan 串 diff，与旁证同源但扩大辖域申报）；③显式声明决策迹为后续批，终验只保留 L3+回放+实机 smoke 日志锚。

### M5 路由清点的属屏映射 10 行（含 4 个反直觉建档屏名与 ArmoryBox 分流注）未随「自足重述」迁入

- **位置**：design.md §2.3；details/session-dissolution.md §2.1/§2.3；landing.md §3.1（「属屏映射十行」判据）。
- **发现**：被取代设计 §2.3 钉死的映射行集全部留在被取代目录：`partner=货币战争-列车同行`、`planner=货币战争-骇入策划`、`star_tome=货币战争-星徽秘典弹窗`、`box_card=货币战争-备战-武装箱选择`（并注「`货币战争-武装箱弹窗` 派发 CwScreenArmoryBox，无 decide 调用不产槽」）；以及「映射外建档屏/阶段二备战双锚/阶段三特殊规则臂语境 = 清全部十槽」「『已 None 跳过』实现落点 = 路由挂点侧、`leave_screen` 本体不动（无条件写语义被既有两处清点依赖）」「group_id 沿用 write_seq 形态」。新文档只有「扩展 `_PAYLOAD_DOMAINS` 为二元组」一句——行集与落点若实现者自推（如把 None 检查放 `leave_screen` 本体）即改既有清点语义。被取代目录属 changes/ 可被清理且「不再落地」，不构成可依赖出处。
- **修正方向**：details §2.1 或 design §2.3 补全 10 行映射表（键以 `cw_loop._dispatch_identity_screen` 分发臂为锚）+ None-skip 落点钉死 + 语境清点三定义。

### M6 零参化后 `decide_encounter` 的 `refresh_used` 判据输入源未钉死

- **位置**：details/session-dissolution.md §2.3（per-visit 位只写「写点/窗语义/读侧 None 缺省 False」，未声明读者与用途）；design.md §2.1/§2.2。
- **发现**：现状 `decide_encounter(..., refresh_used)` 的旗标语义 = per-visit（首调 False、同访问刷新后重决策 True；被取代设计 §2.7 明令「禁读累计计数——第 2+ 遭遇节点首调即 True 产生 refresh 旗标/reason/idx 可读分歧」，代码锚 `cw_screen_supply_node.py:210`（supply 用累计计数派生）vs `cw_screen_encounter.py:304/337`（encounter 用调用参数））。终态零参入口必须自己取这个输入——按写点时序推断读者就是 `decide_encounter`、输入就是 `encounter_refreshed_in_visit`，但**设计没有这句**；实现者若误接累计计数 `gs.encounter_refresh_used`，正常路径（第 2+ 遭遇节点，如战争边疆改写出的多遭遇局）建议枝行为分叉，四格对照若只测单节点也照绿。supply（累计派生）与 encounter（per-visit 位）两入口取值源差异同样未写。
- **修正方向**：details §2.3 补一句硬契约：「`decide_encounter` 零参入口的 refresh_used 判据输入 = `encounter_refreshed_in_visit`（写 False 前置段先于首调；写 True 先于重决策）；`decide_supply` 输入 = `gs.supply_refresh_used` 累计计数派生（现状逐字节）」，并把「第 2+ 遭遇节点首调」补进 3.5 四格对照第 5 格。

### M7 landing 3.1 前置挂错：零交集纯增量批被 unified-obs 候窗链整链阻塞

- **位置**：landing.md §3.1（依赖 = unified-obs 3.4 落码收）；design.md §2.10。
- **发现**：3.1 文件面 = `kernel/cw_game_state.py`/`kernel/cw_vocab.py`/`operations/cw_loop.py`/`cw_strategy_manager.py`/测试——与 unified-obs 3.4 文件面（`run_state.py`/`cw_screen_prep.py`/`cw_screen_buy_cards.py`/`cw_shop_action_ops.py`/`telemetry/query.py`/`match_archive.py`，直调其 landing 3.4）**实质零交集**。被取代设计 §2.8 已按文件面拆解裁定「3.1 增量槽位面 | 前置无」，并把 unified-obs 前置只挂其 3.2/3.3；重述时依赖被一刀切挂上 3.1，经 3.1→3.2-3.6 传递链把零冲突批也排进 unified-obs 3.3 实机候窗之后——违反 iteration-design.md §1.1「dep 挂防冲突所需的最小前置，不挂源迭代全卡」。
- **修正方向**：3.1 依赖清空（或仅挂测试仓文件级互斥），unified-obs 3.4 前置改挂 3.2/3.3/3.5 三个实交阶段。

### M8 写作硬规则 3「无过程叙事」违反三处（规范卡点 = 即打回）

- **位置**：design.md :61「**更正后的事实**：现状 None → …」；:125「（无计数器改造成本，更正上事实）」；:128「禁静默熵种子翻转（r1-M5）」。
- **发现**：iteration-design.md §5-3 卡点「『本轮/修订后/已改』类措辞即打回」；「r1-M5」又是会话局部对抗轮次编号（AGENTS §8 禁会话局部标识符同判）。核实本身无误（`cw_strategy_manager.py:77-78` 守卫 None → 缺省 `Random(0)`，设计对值的判断正确——错的是表述形态）。
- **修正方向**：改当前事实直述：「现状 None 即固定种子 0（`establish_new_match` 仅非 None 才覆写），终态构造保持该语义」；取舍行去掉「更正后」状语；发现编号删除或改持久索引。

### M9 核一现状断言「值对标签错」：invest 返回的 `PickEvent` 已是 CwAction 子类；「invest 的 EventPick」符号锚错位

- **位置**：design.md §1.1（「选择族（…+ invest 的 `EventPick` + 裸 `int`×3…）返回『选了第几个』的选择结果而非动作 op」）、§2.2「基型事实」（只认商店四动作+备战词表为既有 CwAction）。
- **发现**：直调：`kernel/cw_vocab.py:580` `class PickEvent(CwAction)`——invest 的返回类型**本就是动作 op 基类成员**；其缺口是「非 per-screen 分发键、未进注册表（`cw_action_registry._REGISTRY` 无行）、不在 `CW_ACTION_TYPES` 白名单」，不是基型。另 `cw_events.py:917` 的 `EventPick` 是 **5 个 pick 类的联合类型别名**，与 invest 无关——与 `PickEvent` 一字之差，设计锚了错误的符号。问题陈述失真会连带误导「输出两态并存」的缺口面与迁移对照口径（invest 现状对照物 = PickEvent 实例形态）。
- **修正方向**：§1.1/§2.2 更正为「invest 返回 CwAction 族 `PickEvent`（option_idx+refresh+refresh_slots 载体），缺口 = 分发键/注册表外/刷新槽内嵌」；符号统一写 `PickEvent`（cw_vocab）。

---

## minor

### m1 design §2.6 与 details §4 的「桶 3」定义不一致（同一编号两义）

design §2.6 桶 3 = 「kernel 纯函数已收 gs 不动」；details §4 桶 3 = 「kernel 补 gs 形参（签名收窄申报）」。landing §3.4「kernel fallback 暂留（桶 3 归 3.5）」随 details 义。方向一致但编号语义漂移，对账表按哪个桶口径登记未定。修正：桶表单一源放 details，design 引用不复制。

### m2 `game_state_of`「~250 处」计数与直调不符

全量直调：src 树 287 处（含注释/docstring），两仓合计 ~462。规模锚应注明口径（树/两仓/是否含注释），否则普查完成态无法对「~250」验收。修正：改为「普查对账表全量兜底，无总数验收」或标注口径。

### m3 landing 阶段标题层级 `### 3.x` 偏离模板

iteration-design.md 附录 C 模板与多数在册 landing（turnstate/execstate/unified-obs/chain-observation）均为 `## 3.x`；本篇与被取代目录同用 `###`。修正：回 `##`。

### m4 引用锚「§2.4-A/§2.4-B/§2.4-D」在设计正文无对应标签

design.md §2.4 是无字母标号的家族表；§1.3「（§2.4-A，用户裁定）」「处置见 §2.4-B」、landing §3.2/§3.6 设计依据同式引用，均只能靠行序猜测解析。修正：家族表补 A/B/…/D 行标，或引用改指 details §A/§B/§D。

### m5 README 超模板承载「承接出处」节，与 design §0 构成第二抄本

README 规范 = 只串文档记进度；承接出处的正位 = 总纲卷首（§1.1 外溢写法），design §0 已完整承载。两处同文随修订必漂移。修正：README 删该节（或压成一行指针）。

### m6 §B 的跨阶段拆分（3.2 承 `last_owned_equips` 特例）两侧未互认

design §2.4 把特例归 §B 行并「详见 details §B」，landing 却把特例放进 3.2（§A 阶段）、3.3 范围未声明「§B 不含特例」。双阶段同文件翻新（flow.py 3.2 换源一次、3.5 重写一次）宜显式声明，防 reviewer 按表重复验收。修正：3.3 范围补「不含 last_owned_equips（3.2 已承）」。

### m7 3.1 additive 的 Match.performance 与 details 约束②「禁双宿主」自缚

3.1「Match 加 gs/performance 并引导漏斗填充（additive）」到 3.5 写点换宿主之间，session.performance 与 Match.performance 并存双宿主（gs 是同一单例引用不算双源，performance 是真双账）。修正：约束②加「终态唯一归属；3.1-3.5 过渡窗的 performance 填充 = 只读镜像或延后至 3.5 同批」二选一显式声明。

### m8 「10 pick handler 双路径」现状锚过宽

box_pick 无五段双路径（单 handle，`cw_screen_box_pick.py` 无 `run_lifecycle`）；megastar/partner 等 lifecycle 路径的 decide 为共享单体。普查可兜底，但作为 3.5 的调用点清点锚会误导计数。修正：改「10 handler（其中 9 个 handle/lifecycle 双路径，box_pick 单路径；调用点全集以 grep 计数为准）」。

### m9 landing 正本清单「`screens/`(… supply 双篇 …)」歧义

screens/ 目录仅 `supply.md` 一篇；「双篇」实际指 docs/game 侧 `货币战争-补给.md` + `currency_war_supply.md`（后者的 refresh_used=True 句在下一清单行已单列 `docs/game/screens/`）。修正：screens/ 行去掉「双篇」或改指 `screens/supply.md + armory_box.md`。

### m10 HoldFrame/RefreshX 与 `CW_ACTION_TYPES` 白名单及注册完备锁的关系未申报

`cw_vocab.py:838` 白名单 + 注册完备锁（遍历 `CW_ACTION_TYPES + PICK_ACTION_TYPES` 断言注册表可解析）。设计只说「HoldFrame 不进 validate、不查注册表」，未说它**入不入白名单**：入 = 锁要求注册行（与「不查注册表」冲突）；不入 = 违「新增动作必须同步登记」白名单纪律需显式例外申报（OpenTome 漏登记教训在册）。三个 Refresh 动作（handler isinstance 消费、不经 `_act_execute`）同题。修正：§2.2 补一句词表登记/豁免申报。

---

## 附：实际攻击过且零发现的面（防漏账）

- 终态契约四条的维度落位完整性（§2.1-§2.2 与 ABC 12 入口一一对应、`decide_invest` 拆二后 10 选择入口/9 子类计数自洽）。
- `None → 0` 固定种子声明（对码 `cw_strategy_manager.py:77-78` 与 session 缺省 `Random(0)`——**值对**，仅 M8 表述形态违规）。
- `discard_stale_match_container` 保留、引导漏斗 = `establish_new_match` 双生产调用方（CwEntryStart 前移点 + CwLoop handle_init 兜底）声明、journal 装配重锚至 gs 构造点与 `journal.md §7`/`cw_strategy_manager.py:89-91` 现状的一致性。
- journal 装配唯一锚 = `game_state_of` 建立路径的现状表述（journal.md §7 逐字吻合）。
- `pending_round_outcomes` 零读者判定（全仓直调：唯一写端 `cw_screen_battle_wait.py:496`，其余为注释）。
- `bind_exec_state`/`exec_state_of` 已消亡（src 零命中）。
- `_PAYLOAD_DOMAINS` 现状（`cw_game_state.py:285` 前，frozenset{shop,encounter,supply}）与「既有两处显式清点」（`cw_game_state.py:2033` CloseShop 腿 + `cw_observation.py:2618` prep 相位 miss；:3965/:4263 为 sim 合成口自足）。
- REGISTERED_ACTORS 缺席面（`cw_game_state.py:285-336`：确无 CwScreenPlanner/CwScreenBoxPick，3.1 预登记正确）。
- 十二槽表写者/读者全集抽查（prep_obs 三读者全：bridge:174/equip_wear_plan:163/cw_screen_prep:1865；chosen_* 双写端 megastar:194+202、partner:290+298）。
- 刷新链三分形态对码（encounter 同访问重决策 / supply `round_retry` 重入 / invest pending+round_retry 重入）与 §2.4 一致。
- HoldFrame 分支等价（`cw_screen_prep.py:1553-1556/1720-1722`：None → `round_success(wait=1.0)` 前于 validate/执行/续段 token，判等对象替换后语义逐字保持）；「无连续 None 计数器」判定（`_stall` 为访问内零进展计数，None 路径先于其触发返回）。
- `decide_event` 纯函数签名现状（已收 gs/locked_comp/demoted_endgame/evicted，:204-206）与「kernel 纯函数零触碰」自洽。
- sim 侧「零策略构造」申报（`sim/` 全目录无 session/strategy 引擎引用；`cw_replay.py:108` create_session 构造已列入随批面）；回放旁证辖域申报（仅 decide_shop_screen 驱动器路径）诚实。
- 在飞迭代状态对账（execstate 6/6 收尾、turnstate 3/3 落 HEAD、unified-obs 3/5 与 §2.10「3.4 落码收」前置、chain-observation 6/6 落 HEAD）。
- 落地七件齐（3.1-3.7+末阶段逐阶段七项全）与普查词表锚真实性（`契约成员 13`/`决策入口 11`/`九接口`/`PickBoxCard`/`refresh_used=True` 两篇/空 board stub 两篇/画面 payload 括注——全部直调命中）。
- 宪法核（00_framework 四条/01_math 公理与七面）：本批为载体/契约形状批，无新判据无新数值，无宪法冲突面。
