# 第三轮对抗审（扩围增量；核一·无前提 + 核二·规范遵循 + 核三·治本）

- 攻击者：对抗审查员（iteration-design.md §7 三核并重）
- 对象：design.md **§2.4 遭遇扩围** + 被 §2.4 改写的 §3 验收锚 3；landing.md **3.3（扩围版四块）** + 正本更新清单遭遇相关条目。原三块（补给选卡即时上报/补给刷新闸观察化/遭遇刷新链终结化）已经 attack.md/attack2.md 两轮审且 3.1/3.2 落地——前轮结论不锚定，但扩围与已落地前三块或正本规范冲突同样攻击。attack.md/attack2.md = 历史工件。
- 方法：无依据标注的主张必攻；试读（假自己是实现者逐块问「凭这份能开工吗」）；全量同步复查（设计引用的每个符号/字段/文件读码核存在性与语义——`cw_screen_encounter.py`、`cw_op_settle_confirm.py`、`cw_overlay_pick_action.py`、`zero_writes.py`、`cw_encounter_selection.py`、`cw_game_state.py`、`cw_screen_battle_wait.py`、`cw_screen_report/encounter.py`、op-layer.md、fields.md、encounter.md、combat.md §3 均已直读）；对照正本逐项核（规范出处随条给）。
- 日期：2026-09-21（第三攻击轮，扩围增量）

---

## ① 总判

**需修订（阻塞 5 + 建议 4）**。

扩围四块的方向（稳定期删除、派发即终结、chosen 迁动作侧、结算奖励兑现回调）均有用户裁定背书、与已落地的刷新终结化/补给 3.1 形态自洽，骨架成立。阻塞集中在三类：①**design 稿内部自相矛盾**——§2.1 遭遇段仍保留「重入裁决与 chosen_encounter 写端不动，不在本迭代辖内」的原条款，§2.4 又整体撤销之，§2.2 消费点迁移总表对扩围符号零扩行；②**失败安全申报不实**——稳定期删除后「候选读缺 = 少拿一次机会非卡死面」与现状代码行为（options 空时以 idx=0 **盲选左卡并派发确认**）不符；③**奖励兑现回调的数据载体与防线不完整**——新字段 `encounter_reward_claimed` 的写通道/审计行/遥测接线/生命周期全未定义，「推进前读 node_kind_of」的机制论证与代码事实不符（`report_node_advance` 推进 `node_ord`，不写 `gs.node` 镜像），镜像陈旧 + chosen 残留 + 结算覆盖 best-effort 失败三条非删失误兑现路径无防线。

## ② 逐条发现

### X1 [阻塞] | design.md §2.1（遭遇段末句）/ §2.2 表 vs §2.4 | design 稿内部自相矛盾：§2.1 仍声明「选卡分支的重入裁决与 chosen_encounter 写端不动（不在本迭代辖内）」，§2.4 整体撤销该条款，§2.2 迁移总表对扩围符号零扩行

- **问题**：§2.1 遭遇段末句原文「选卡分支的重入裁决与 `chosen_encounter` 写端**不动**（动作事实边界现行合法形态，`op-layer.md` §2.2，**不在本迭代辖内**）」——§2.4 第二、三块做的恰是删重入裁决 + 迁 chosen 写端。landing 3.3 顶部注只撤销了 landing 侧旧条款（「原『不含：遭遇选卡分支的重入裁决与 chosen_encounter 写端』条款随之撤销」），design 正文未同步。同时 §2.2「消费点迁移总表」仍是原三块的表，扩围涉及的全部符号零行：`_confirm_pending`（读写点删）、`_record_chosen`（写端删+迁移）、`chosen_encounter`（写端画面 op→动作 report）、`gs.encounter` payload（新消费点 = report 值组装）、`encounter_reward_claimed`（新字段 + 审计行）、`screen_flow_timing.md #23`（口径注改写）。试读者拿到的是同一文档内两个互斥口径，无法判定哪个生效。
- **权威源证据**：design.md §2.1 末句 vs §2.4 第二/三块（同文档互斥）；landing.md 3.3 顶部注（只撤 landing 条款）；§2.2 表逐行核（无上述任一符号）。现役符号存在性：`cw_screen_encounter.py::_confirm_pending`(:105,:182-192,:250)、`::_record_chosen`(:112-138)。
- **建议修法**：§2.1 遭遇段末句改写为「扩围后 = §2.4 辖内（见 §2.4）」；§2.2 表补扩围符号各行（符号/现消费点/迁移三列，与原表同构），`encounter_reward_claimed` 行需含 `cw_projection_audit` 审计行与遥测接线去向（详见 X3）。

### X2 [阻塞] | design.md §2.4 第一块（入口稳定期删除） | 失败安全申报不实：候选读缺的现状行为 = 盲选左卡并派发确认，不是「少拿一次机会非卡死面」；2s 稳定期恰是该读缺风险的现役缓解

- **问题**：§2.4 称读帧时点后移风险「由既有失败安全承接：候选读缺 = 空表不写容器、剩余读缺 = None = 闸拒绝，两方向均为『少拿一次机会』非卡死面」。读码：候选空时 `report_screen_encounter_obs` 确实整函数早退不写容器（`cw_screen_report/encounter.py:61-62`），但决策动作 node 随后**并不停**——`options = obs.options if obs is not None else []`，match/options 条件不满足则 `idx=0, reason='default(no-options/match)'` 直落确认链，派发 `CwActionPickEncounterParam(idx=0)` **点左卡 + 点选择确认**（`cw_screen_encounter.py:193-260`）。这是不可逆的游戏态动作（消耗本节点选择），不是「少拿一次机会」。2s 稳定期正是对该读缺风险的现役缓解（observe node 注释自证：「入口帧可能在稳定期内，立即读难度卡有读缺风险」，:145-151）；删除它是用户裁定、成立，但设计必须如实申报删除后的暴露面并给空候选分支定义新行为，而不是把盲选包装成失败安全。
- **权威源证据**：`operations/cw_screen/cw_screen_encounter.py:158-171`（sleep 2.0 + 重截）、:193-196（options 空落 default）、:245-260（盲选派发确认链）；`kernel/cw_screen_report/encounter.py:61-62`（空候选早退——「不写容器」申报属实，但只覆盖容器半，不覆盖动作半）。
- **建议修法**：§2.4 第一块补空候选分支的新行为定义——二选一并写入验收锚 3：①（推荐，同屏已有先例）options 空 = 零点击 `round_success` 终结交回外循环重进重读（与刷新闸数据不一致分支同构，`cw_screen_encounter.py:213-220`）；②如实申报「候选读缺 = 维持现状盲选左卡（idx=0）」为已知接受行为。当前措辞（「不写容器…非卡死面」）两样都不是，实现者无从落码。

### X3 [阻塞] | design.md §2.4 第四块 / landing 3.3 第四块 | `encounter_reward_claimed` 的数据载体未定义完整：写通道/sig、审计行、journal/遥测接线、生命周期全部空缺，声明的消费面没有读取路径

- **问题**：设计只定义了字段形状（`tuple[int, str] | None` 顶层字段）与触发判据，以下实现者必答项全部未定义：①**写通道**——`write_logic`？sig 的 family/actor 是什么（回调挂 `CwOpSettleConfirm` 但语义值来自遭遇域；现役 `_record_chosen` 用 `ChannelSig(family='logic_action', actor='CwScreenEncounter', mode='compute')`，新写端 actor 归谁）？②**审计行**——`cw_projection_audit.py` 对本迭代其它新字段（`*_refresh_left`）均安排了行改/新增（§2.2 表在册），`encounter_reward_claimed` 无行；③**遥测/journal 接线**——声明消费面 = 「策略器收益对账/单局复盘」，但复盘协议（match-review）与遥测判读消费的是 journal/telemetry 行或容器投影，无接线声明 = 声明的消费者读不到；④**生命周期**——单槽跨遭遇覆盖（第二遭遇覆写第一）还是逐节点？`chosen_encounter` 兑现后是否清（见 X4b）？sim 侧是否有写端（supply left 有 sim 写端先例，本字段无申报）。「深度 = 实现者无需再设计」（§0）在该块不成立。
- **权威源证据**：design.md §2.4 第四块全文（仅机制依据+判据+「不直写」取舍）；landing.md 3.3 第四块、文件面（含 `cw_projection_audit.py` 但只为 refresh 行）、完成判据（行为锁三型，无审计/遥测判据）；对照先例 = §2.2 表 `encounter_refresh_left` 行的审计行安排（本迭代自己的标准）。
- **建议修法**：§2.4 第四块补一段「载体与接线」：写通道（write_logic + sig/actor 定值）、`cw_projection_audit` 新增行、journal/遥测落点（至少 journal 事件行或 schema 注记）、生命周期（建议 = 单槽逐遭遇覆盖 + 兑现后清 `chosen_encounter`，见 X4）、sim 侧零写端申报（若成立）；landing 3.3 完成判据补对应 grep/行为锁。

### X4 [阻塞] | design.md §2.4 第四块（回调判据与时序论证） | 「推进上报前调回调」的机制论证与代码不符 + 三条非删失误兑现路径无防线，宣称的 fail-closed 不成立

- **问题**：四点：
  - **(a) 机制论证错误**：设计称「`report_node_advance` 会推进 node 指针，`node_kind_of` 须读推进前值判『当前是遭遇』」。读码：`report_node_advance` → `advance_node_effective` 只写 `gs.node_ord`（序号，`cw_game_state.py:3063-3073`）；`node_kind_of` 读的是 `gs.node`（NodeKey 镜像，:3474-3477），镜像由备战帧 `observe_screen_context`/类型直定写，**不随推进上报变化**。即回调放在推进前还是后对 `node_kind_of` 读值无差别——设计的时序论证建立在不存在的作用机制上（结论碰巧无害，但说明设计未核该符号语义，且正文本应论证的镜像滞后语义反被漏掉）。
  - **(b) 镜像陈旧 + chosen 残留 → 非遭遇局误兑现**：`gs.node` 镜像滞后至下一备战帧观察；`_record_round_outcome` 自己就要走「boss 锚 > `node_kind_of` > 节点表 > 缺省」四腿兜底（`cw_screen_battle_wait.py:444-449`），证明单一 `node_kind_of` 读值在结算时点并不可靠。若某普通战斗节点备战观察缺失（镜像残留 `'遭遇'`）且 `chosen_encounter` 残留上一遭遇值、该局 `progress_delta>0` → 回调在非遭遇结算上误写兑现记录。设计防线只覆盖「双 None = 删失」与「无 chosen → 不兑现」，chosen 的**残留**（非 None 的旧值）无任何防线（无兑现后清空、无节点序对账）。
  - **(c) 结算覆盖 best-effort 失败 → 消费陈旧值**：宿主 `_record_round_outcome` 的 `apply_settlement_cover` 调用整体包在「观测回路失败不阻塞对局」try/except 内（`cw_screen_battle_wait.py:533-587`），失败时 `gs.settlement` 残留**上一节点/上一场**真值；回调在 `CwOpSettleConfirm` 内消费 `settlement.progress_delta` 时无从区分「本局值」与「陈旧值」——陈旧 `progress_delta>0` + 镜像仍 `'遭遇'`（同一场驻留重试轮）→ 误兑现。设计未申报该窗。
  - **(d) 驻留循环多次触发**：`CwOpSettleConfirm` 是 `node_max_retry_times=400` 的驻留 op，死点击自愈链下同一结算屏回调每轮触发；幂等性（同值重写？首触发闩？）未申报。
- **权威源证据**：`kernel/cw_game_state.py:3063-3114`（advance 只写 node_ord）、:3474-3477（node_kind_of 读镜像）、:3616-3619（镜像写端 = 观察侧）；`operations/cw_screen/cw_screen_battle_wait.py:444-449`（四腿兜底 = 单读不可靠的自证）、:533-587（best-effort try/except）、:743-779（②段读点先于确认 op 派发——**本局结算数据就绪时序本身成立**，此点设计核过、无异议）；`operations/cw_op/cw_op_settle_confirm.py:79-99`（驻留多轮点击即多轮回调）。
- **建议修法**：①重写时序论证为真实机制（镜像滞后语义：回调读值 = 最近备战帧观察的节点类型；并说明「推进前调」仍保留的理由 = 语义清晰/防御下一备战帧早到，而非虚假的指针推进论）；②补**节点序对账防线**：回调记录兑现时的 `effective_node_ord(gs)` 入值或入行，消费端可核「兑现行节点序 == chosen 所在遭遇节点序」；最低成本修法 = **兑现后清 `chosen_encounter`（单次消费语义）**，一并消解 (b) 残留面；③申报 (c) 陈旧窗残余或以「settlement 行 note `battle_done:遭遇` 同帧校验」收口（note 已带节点类型，`cw_screen_battle_wait.py:585`）；④申报 (d) 幂等语义（推荐 = 同值幂等重写，零闩）。

### X5 [阻塞] | landing.md 正本更新清单（fields.md 条目） | 正本更新清单漏改 fields.md §3.4 头部 chosen 硬规则条款与 §4「事件选择」节——chosen_encounter 迁动作侧后两处正本即刻失真

- **问题**：清单对 fields.md 只安排「§3.4.1/§3.4.2 重写（……+ chosen_encounter 写端迁动作侧注记）」。但 chosen 写端硬规则的正文住在两处清单未覆盖的位置：①**§3.4 节点事件屏头部通用条款**（fields.md:718-721）：「选择结果 chosen_\*（动作事实边界：**留守画面 op 重入裁决点单次逻辑写入**——『确认已发→下一帧锚不在=落地』后才写……）」——遭遇迁动作侧发射即写后该通用条款对遭遇失真；②**§4「事件选择（10 屏）」**（fields.md:1051-1060）：「chosen_\* 写端已接七屏（……**遭遇**/补给……）」+「默认不记预期值」语境——遭遇条目需改判注记。同理 op-layer 清单条目已覆盖 §1.4/§2.2 遭遇例外改判（清单 :69，已核），但 fields.md 两处遗漏 = 迭代收尾义务（「正本与实现一致」）漏项，末阶段判据「清单清零」也检不出。
- **权威源证据**：fields.md:718-721、:1051-1060；landing.md 正本更新清单 :72（仅 §3.4.1/§3.4.2 + 兑现记录字段节 + 迁动作侧「注记」——注记落点未含上述两节）。
- **建议修法**：清单 fields.md 条目补：§3.4 头部条款加遭遇例外改判注（先例写法 = 同段投资域收窄条款的表述形态）、§4「事件选择」遭遇行改写（发射即写、值组装 = payload 槽、盲选/越界不写）；顺带核 encounter.md §6（清单已安排全文重写，无漏）。

### X6 [建议] | design.md §2.4 第三块 / landing 3.3 文件面 | `report_action_pick_encounter_param` 升格容器写后的模块归宿未定义：zero_writes 留守与「零写族」模块语义冲突，具名新模块又不在文件面

- **问题**：函数现住 `kernel/cw_action_report/zero_writes.py`（模块定位 = 「零写动作族上报集中件」，docstring 自证）。升格为容器写后二选一：留 zero_writes（与模块语义/`_report_zero_write` 族策略冲突，且先例 pick_supply/pick_equip 升格时均迁具名模块，`zero_writes.py:77-84` 注释在册）；迁具名新模块 `cw_action_report/encounter.py`（landing 3.3 文件面无此文件，文件面只列 `zero_writes.py`）。任一选择都该由设计点名，否则实现者自行猜。
- **权威源证据**：`kernel/cw_action_report/zero_writes.py:1-12`（族策略）、:71-73（现函数）、:77-84（升格先例 = 迁具名模块）；landing.md 3.3 文件面。
- **建议修法**：§2.4 第三块/landing 3.3 点名归宿（建议 = 迁 `cw_action_report/encounter.py`，照 pick_supply 先例），文件面补该文件。

### X7 [建议] | design.md §2.4 第四块（判据） | 「progress_delta>0 主判 ∨ killed 辅判」的判据独立增量未申报：killed 在结算链多为 progress 符号的派生值，hp 对比兜底腿在遭遇局语义未证

- **问题**：读码：`_record_round_outcome` 内 `killed is None ∧ progress_delta is not None → killed = progress_delta > 0`（`cw_screen_battle_wait.py:468-471`）——主判成立的场合辅判几乎恒同值，辅判的真实独立增量只剩「killed 由文本/hp 对比读到显式值」的场合；而 hp 对比兜底（:484-493，`killed = hp_after >= prev_hp`）在遭遇局（伤害进度达标制、不清场、我方可能零掉血）的胜负能否由 hp 单调判定**无任何在册证据**（combat.md §3 只定谳进度达标制）。辅判可能引入主判不会误的误（hp 兜底误 True 而 progress_delta ≤ 0 时判据为 ∨ 仍兑现）。机制依据本身核过成立（combat.md:38-48「打够最低进度=拿奖励，不需要清空敌人」→ progress_delta>0 作达标信号方向正确，败局负值/删失 None 的口径与 §3 一致）。
- **权威源证据**：`cw_screen_battle_wait.py:468-471`（派生）、:484-493（hp 兜底）；`docs/game/currency_war/research/combat.md:38-48`。
- **建议修法**：§2.4 申报判据重叠度与 hp 兜底腿的遭遇局未证状态；或收窄为单判 `progress_delta > 0`（killed 仅作删失期备胎并要求与 progress 同号才采纳）。

### X8 [建议] | design.md §2.4 第三块 | chosen 发射即写后的暂态假值窗口未申报：确认未生效（点击链失败）时容器已持未落地的 chosen，且奖励回调在该窗内无防线消费

- **问题**：迁动作侧后 chosen 写时点 = 确认点击发射（「点完确认立即写」），语义从「落地记录」变「发射意图记录」。确认未生效 → 外循环重派 → 观察/重决策/重写 chosen——多数场景自愈；但窗口期内 chosen 已持值，若后续结算回调因 X4(b/c) 的陈旧条件触发，消费的是未落地意图。设计对 supply 同形态申报了「确认未生效 = 代码 bug + 外循环重派」的处置，但未申报 chosen 假值窗与回调消费的关系（修法 X4② 的兑现后清 chosen 可一并收窄本窗）。
- **权威源证据**：design.md §2.4 第二块（确认未生效处置申报）vs 第三块（chosen 写时点，无假值窗申报）；`op-layer.md` §1.1 投资两屏同形态条款（作先例时也未申报此窗——本条 = 全族共性欠账，不阻本迭代）。
- **建议修法**：§2.4 第三块补一句：「chosen = 发射即写的意图记录，确认未生效窗内为暂态假值，由外循环重派覆盖自愈；奖励兑现回调的消费防线见第四块（X4 修法）」。

### X9 [建议] | design.md §2.4 第一块 / landing 3.3 第二块 | `screen_flow_timing.md #23` 口径注改写承诺未落到任何完成判据或清单条目

- **问题**：§2.4 与 landing 3.3 第二块均承诺「`research/screen_flow_timing.md` #23 口径注同步改写（用户裁定 supersession）」，但 3.3 完成判据（行为锁 + grep + 通用工程门）与正本更新清单均无该文件条目——承诺无验收挂钩，落地批漏改无检出面。（research doc 非正本、不进「正本更新清单」是结构原因，但承诺既已写下就应有判据承载。）
- **权威源证据**：design.md §2.4 第一块、landing.md 3.3 第二块 vs 3.3 完成判据 :48-52、正本更新清单 :64-73（两处均无该文件）。
- **建议修法**：3.3 完成判据补一条「`screen_flow_timing.md` #23 注已带 supersession 标记（用户裁定 2026-09-21）」的文档判据。

## ③ 试读与复查结论（摘要）

- **试读**：凭现稿能否开工——四块中刷新终结化（已落地部分）与派发即终结可开工；入口稳定期删除（X2 空候选行为未定义）、chosen 迁移（X6 归宿）、奖励兑现回调（X3 载体/X4 防线）三处实现者须自行设计，与 §0「深度 = 实现者无需再设计」不符。
- **全量同步复查**：§2.4 引用符号逐个读码核过——`node_kind_of`/`Settlement.killed`/`progress_delta`/`chosen_encounter`/`encounter_refresh_left`/`apply_settlement_cover`/`emit_overlay_confirm(env.op)` 均存在且语义如设计所用，**除 X4(a) 的推进机制误述外无幻觉符号**；「结算三项已入 RoundOutcome 与容器结算域」属实（`apply_settlement_cover` :1347-1398）；「本局结算数据先于确认 op 就绪」属实（宿主 ②段读点 :756 先于确认派发 :773）；`env.op` 宿主引用在同步 execute 形态下无失效面（任务提示方向核过，不成立，无发现）。
- **核二**：op-layer §1.4（刷新=终结/剩余闸）、§1.2（动作 op 禁验证/点击即上报）、§2.2（动作事实边界）逐项对过——扩围自身对 §2.2 的例外改判已安排正本修订（用户裁定显式迁移，程序合法），遗漏面见 X5；combat.md §3 机制依据引用属实（见 X7）。
- **核三（治本）**：派发即终结 + chosen 迁动作侧 = 消「两相上报」同族根，与 3.1/投资先例同构，治本成立；奖励兑现回调把「获取奖励」的用户意图转为语义账面 + 数值走真值源（settle_truth/观察），防双源取舍已如实申报（设计 §2.4 末句），方向治本——但 X3/X4 显示该新机制的载体与防线还停在「机制草图」深度，须补足后再落码。

---

# 第三轮对抗审 · 复攻（第二轮次）

- 攻击者：对抗审查员（对「attack3 处置修订后」的 design §2.4 / landing 3.3 扩围面做无前提复攻）
- 对象：design.md §2.4（含 attack3 X2/X3/X4/X6/X7/X8 处置后形态）+ §2.2 表扩围行 + §3 验收锚 3；landing.md 3.3 扩围四块 + 正本更新清单扩围条目；账本 T-7（doing）。
- 日期：2026-09-21（复攻轮）。编号 R-*，不与前轮 X-* 混用。
- 方法：全部机制主张重新对码核证（`cw_op_settle_confirm.py`、`cw_screen_battle_wait.py`、`cw_screen_encounter.py`、`cw_game_state.py`（Field/Settlement/EncounterPayload/apply_settlement_cover/advance_node_effective/node_kind_of）、`cw_encounter_selection.py`（SettlementRing/EncounterLog/record_settlement_row）、`cw_overlay_pick_action.py`、`cw_action_report/zero_writes.py`、`cw_screen_report/encounter.py`、`cw_vocab.py`、`fields.md`、`op-layer.md`、`screen_flow_timing.md` #23、combat.md §3、dag.jsonl T-7）。

## ① 总判（复攻）

**需修订（阻塞 2 + 建议 4）**。

四块机制骨架经复攻全部成立（含前轮处置：空候选分支新行为、模块归宿、单判 progress_delta、清 chosen 幂等、时序论证重写——逐项对码核过，见 ④）。两处阻塞：①**奖励兑现判据第二腿按规格不可实现**——「容器结算行 note == 'battle_done:遭遇'」的 note 不住在容器域（Field 只有 value/source/evidence，Settlement 结构无 note；note 仅随 `_swap` 落 journal 行），「回调 = 纯容器读」与该判据腿互斥，实现者必须自行换载体；②**「9 条全采纳」申报不实**——X9 的文档判据未落任何完成判据（design §2.2 表还声称「文档判据 = landing 3.3」，landing 该节并无此判据），X5 的 fields.md 两处正本失真点未进清单，而 design 元信息与账本 T-7 note 均宣称全采纳。

## ② 逐条发现（复攻）

### R1 [阻塞] | design §2.4 第四块判据 / landing 3.3 第四块 | 双证第二腿「容器结算行 note」不在容器域：note 仅落 journal 行，「纯容器读」约束下该判据不可按规格实现

- **问题**：判据要求 `node_kind_of(gs)=='遭遇'` ∧ 容器结算行 `note=='battle_done:遭遇'`，且回调声明「纯容器读零读屏」。读码：`Field` 仅 `{value, source, evidence}`（`cw_game_state.py:386-412`）；`Settlement` 数据类无 note/node_type 字段（:607-621，只有 hp_after/streak_after/killed/progress_delta/gold/level/xp）；`apply_settlement_cover` 的 note 形参只透传给 `gs.observe(..., note=note)` → `_swap` → **journal 行**（:2320-2347，写 journal 后不存 Field）。即容器里不存在可读的「结算行 note」——按规格落码要么读 journal（违反纯容器读自约束），要么实现者自行改载体（违反 §0「实现者无需再设计」）。
- **权威源证据**：`cw_game_state.py:386-412 / :607-621 / :1394-1398 / :2320-2347`；design §2.4 判据段与「回调 = 纯容器读零读屏」句（同块互斥）；landing 3.3 第四块同款表述。
- **建议修法**（三选一，设计点名）：①判据腿换 **`gs.settlement_ring` 尾行 `node_type=='遭遇'`**（`_RingRow` 有 node_type/killed；环写端 `record_settlement_row` 在 `_record_round_outcome` 环写位 `cw_screen_battle_wait.py:512-514`，先于确认 op 派发 :773-774，且该写点在结算覆盖的 best-effort try 块之外——顺带把 §2.4 申报的「结算覆盖失败陈旧窗」残余收掉大半，残余申报可缩窄）；②`Settlement` 数据类增 `node_type` 字段（改动面大，域版本联动，不推荐）；③note 回读 journal（违反自约束，不推荐）。推荐①，同步改写 design §2.4 判据/landing 3.3/验收锚 3 措辞。
- **严重级**：阻塞。

### R2 [阻塞] | design §0 元信息 / §2.2 表 #23 行 / landing 3.3 完成判据与正本更新清单 | 「9 条全采纳」申报不实：X9 判据未落任何验收面、X5 的 fields.md 两处失真点未进清单

- **问题**：三点。①X9 要求 #23 口径注改写有验收挂钩：design §2.2 表行声称「文档判据 = landing 3.3」，但 landing 3.3 完成判据（:48-52）与正本更新清单（:64-73）均无 `screen_flow_timing.md` 条目——指针指向不存在的判据，比前轮「无挂钩」更糟（现在是假挂钩）。②X5 指出的两处正本失真点仍未点名进清单：fields.md §3.4 头部通用条款（:718-724「chosen_* 留守画面 op 重入裁决点单次逻辑写入」——扩围后对遭遇失真）与 §4「事件选择」（:1051-1060「chosen_* 写端已接七屏（…遭遇…）」）；清单 fields.md 条目只写「§3.4.1/§3.4.2 重写 + 迁动作侧注记」，未含上述两节，末阶段「清单清零」检不出该失真。③design §0「9 条全采纳」与账本 T-7 note「阻塞5+建议4 全采纳」（dag.jsonl :21）与实况不符——收口申报失真会传导为「正本更新批照单执行即漏」。
- **权威源证据**：landing.md 3.3 完成判据与正本清单（无 #23/无 fields 两节）；design §2.2 表 #23 行；fields.md:718-724、:1051-1060（现文仍持留守口径）；dag.jsonl T-7 note。
- **建议修法**：landing 3.3 完成判据补「`screen_flow_timing.md` #23 注已带 supersession 标记（用户裁定 2026-09-21）」；正本清单 fields.md 条目补 §3.4 头部例外改判注 + §4 遭遇行改写；如不采纳则把 design/账本的「全采纳」改为如实的部分采纳申报。
- **严重级**：阻塞（收口申报失真 + 正本漏项）。

### R3 [建议] | design §2.4 第三块 | 「兑现后清 chosen_encounter」的写通道未定义：清除写的 sig/actor 与审计行为空白

- **问题**：`chosen_encounter` 现写端 = `_record_chosen` 用 `write_logic + ChannelSig(family='logic_action', actor='CwScreenEncounter')`；清空是同字段的第二次写端，actor 归宿（回调宿主 `CwOpSettleConfirm`？遭遇域 `claim_encounter_reward`？）、`cw_projection_audit.py` 现有 `chosen_encounter` 审计行（:279）对清除写是否放行/如何投影，设计未写。X3 修法给 `encounter_reward_claimed` 定了 sig，清除写漏配对。
- **权威源证据**：`cw_screen_encounter.py:131-136`（现写端 sig）；`cw_projection_audit.py:279`；design §2.4 只定义新字段 sig。
- **建议修法**：§2.4 第三块补一句：清除写 = `write_logic(None)` 同族 sig（actor 与回调写端一致），审计行申报投影语义（None = 已消费/未写）。
- **严重级**：建议。

### R4 [建议] | design §2.4 第四块 | 双证判据的假阴性面未申报：note/ring 的 node_type 来自 battle_wait 四腿兜底，镜像缺失的遭遇局会 fail-closed 漏兑现

- **问题**：结算行 node_type 的产源 = `boss 锚 > node_kind_of > 节点表 > 缺省'普通战斗'` 四腿（`cw_screen_battle_wait.py:444-449`）；遭遇局若备战观察缺失（镜像 None）且节点表 miss → note/ring 行落 `'普通战斗'` → 不兑现。方向 fail-closed（漏记非误记）、低频，但「双证」两腿同源（node_kind_of 与 note 主腿同产源），双证的独立增量主要只剩 boss 锚误盖与节点表纠偏两窄窗——设计的双证收益申报偏满。
- **权威源证据**：`cw_screen_battle_wait.py:444-449`；design §2.4 判据段。
- **建议修法**：§2.4 补一句假阴性申报（镜像缺失遭遇局漏兑现，方向安全，归观察可靠性治理）；若采 R1①（ring 尾行），申报同理。
- **严重级**：建议。

### R5 [建议] | design §2.4 第四块载体段 | 「现役消费面 = 容器读端（策略器收益对账）」申报不实：新字段零现役读端，「策略器收益对账」消费无任何批次/任务承接

- **问题**：`encounter_reward_claimed` 是新字段，「容器读端（策略器收益对账）」现役不存在；遥测接线候批申报了，但策略器/复盘侧的读端没有任何后续批次登记——落地后字段写后无人读，直至无期限候批。X3 修法要求的「声明的消费者读得到」只满足了审计投影半。
- **权威源证据**：design §2.4 载体段；landing/账本无对应后续任务。
- **建议修法**：载体段改为如实申报「现役消费面 = 审计投影唯一；策略器收益对账读端挂账（外溢候选登记）」，照 §1.3「明确不解决」节同款写法。
- **严重级**：建议。

### R6 [建议] | design §2.2 表扩围行 vs 代码现状 | 表内符号与版本号对已落码状态漂移：`_try_refresh`/三退役计数符号在 src 已不存在、「域版本 2→3」vs 现码已 = 4

- **问题**：遭遇刷新终结化（3.3 第一块）与剩余闸已在码（`cw_screen_encounter.py` 现役即终结形态 + `encounter_refresh_left` 字段 `cw_game_state.py:2053`），`_try_refresh`/`encounter_refresh_used`/`encounter_refreshed_in_visit`/`supply_refresh_used` 在 src 已零命中（仅 `cw_screen_supply_node.py:341` 注释残留「与遭遇屏 _try_refresh 同类」一句，非遭遇域、判据豁免但照抄易困惑）。§2.2 `supply_refresh_left` 行「`node_screen_refresh` 域版本 2→3」与现码版本注释 = 4（`cw_game_state.py:172`）矛盾——3.2 落地批照抄「2→3」会写错版本。扩围符号与这些行同表，试读时以表为据会误判待办面。
- **权威源证据**：全仓 grep（上述符号）；`cw_game_state.py:172`（版本 4 注释已含 encounter_refresh_left 迭代记）；design §2.2 表。
- **建议修法**：§2.2 表对已落码行加「已落码」标记或改过去时；域版本行改「bump 至 max(现值,现值+1)」式表述（或核对后写 4→5）。
- **严重级**：建议（已定稿面边缘，不重攻其设计本身，仅记同步债）。

## ③ 试读结论（复攻）

凭 T-7 卡（criteria 指向 landing 3.3 完成判据 + 三符号 grep + 通用工程门）+ design §2.4 + landing 3.3：第一/二/三块（稳定期删除+空候选分支、派发即终结、chosen 迁动作侧即时写）**可开工**——挂点、值组装（`gs.encounter` payload 槽，唯一覆盖写端 = 入口观察 report，与确认点击同步相邻无覆写窗）、越界 fail-closed（`_record_chosen` 守卫口径平移）、模块归宿（照 pick_supply 迁具名模块先例，`zero_writes.py:77-84` 注记在册）、上游调用位（`CwActionPickEncounterOp.run` :181-186 自上报位已在）齐备。第四块（奖励兑现回调）**不可直接开工**：R1 判据第二腿载体必须先由设计定夺；R3 清除写通道顺带补。T-7 criteria 本身无 R1/R2 缺陷（criteria 指回 landing 判据，修 landing 即自动跟上）。

## ④ 零发现面声明（复攻核过、无新发现）

- **机制依据**：combat.md §3「遭遇奖励 = 伤害进度达标制、结算屏三项采集点」引用属实（:38-48）；`progress_delta>0` 单判方向与 §3 一致（败局负值/None 删失口径对齐）；killed 不入判据的处置（X7）与 `cw_screen_battle_wait.py:468-493` 派生/hp 兜底腿实况相符。
- **#23 口径**：`screen_flow_timing.md` #23 原文存在且含「入口 2s 稳定 + 刷新 2s」双口径；用户裁定 supersession 程序成立（先例 = combat.md §3 遭遇高危条）——缺的只是验收挂钩（R2）。
- **回调挂点与时序**：`CwOpSettleConfirm.confirm` 点击成功分支 → `_report_node_advance` 前插回调可行（长按兜底路径同段覆盖）；宿主 ②段 `_record_round_outcome`（:756，含环写 :512-514 与结算覆盖 :570-585）先于确认 op 派发（:773-774），结算数据就绪成立；`report_node_advance`→`advance_node_effective` 只写 `node_ord`/`node_hist_ord`（:3042-3073），不触 `gs.node` 镜像——design 时序论证（X4(a) 处置后形态）与代码一致；驻留多轮幂等经「兑现后清 chosen」收口成立（第二轮 chosen=None 天然 no-op）。
- **空候选分支**：与现码「刷新闸数据不一致零点击终结」分支同构（`cw_screen_encounter.py:213-220` 先例在码）；现行盲选路径（:193-196, :245-260）确认存在，X2 处置如实。
- **规范遵循**：§1.1 出口①「派发即终结」、§1.2 增补 2「点完即写」、§2.2 动作事实边界遭遇例外改判（用户裁定显式迁移，op-layer §1.4/§2.2 清单条目在）程序自洽；「数值不直写」防双源成立（gold 真值 = `settle_truth` :1389 先例、随机4费 = bench heavy 观察，兑现记录仅语义账面）。
- **并行批现状如实记录**：action_ops.md / op-layer.md 有另一批未提交 hunk（增补 3 面），与本扩围面无文本冲突；design.md/landing.md 本轮修订亦未提交、attack3.md 未跟踪——以上均为工作区实况，非攻击发现。
