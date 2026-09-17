# 策略器终态契约 迭代设计 对抗审查报告（首轮）

> 审查对象 = 本目录 design.md / details/session-dissolution.md / landing.md / README.md。
> 判据源全部直调复核：iteration-design.md（形式门）、strategy-docs/00/01、game_state/fields.md、
> flow/README.md / session.md / outer_loop.md / game_state/journal.md / action_exec.md、
> 被取代迭代 2026-09-16-strategy-input-unification 全套、在飞三迭代 README、
> 代码真值逐文件直读（cw_strategy.py / cw_strategy_session.py / cw_vocab.py / cw_events.py /
> flow.py / cw_strategy_manager.py / cw_action_registry.py / cw_overlay_pick_action.py /
> cw_hp_policy.py / cw_plane_table.py / cw_game_state.py / cw_exec_state.py / cw_events.py /
> cw_loop.py / cw_screen_prep.py / cw_screen_buy_cards.py / cw_screen_invest_strategy.py /
> cw_screen_encounter.py / cw_screen_supply_node.py / obs/cw_observation.py / sim/cw_replay.py / sim/*）。
> 符号锚普查两仓逐仓：`game_state_of`（src 287 处 + sr-od-test 173 处）、
> `strategy_state_of|state_of`（合并命中 src 442 处）、`PickBoxCard`、`refresh_used`、
> `plane_lengths_seen`、`prep_frame_class`、`enhance_char_id` 等逐词跑。
> 严重度：blocker = 定稿门槛问题；major = 须修；minor = 建议。

## 发现总数：21（blocker 3 / major 8 / minor 10）

---

## Blocker

### [B1] blocker | design.md §2.1「输入承载」；details/session-dissolution.md（全文）；landing.md 3.1
**发现内容**：设计声称输入面语义「逐条继承前置迭代 §2.2 并**重述于 details/session-dissolution.md §2**」，但 details/session-dissolution.md **不存在 §2 节**（全文只有「问题与约束 / 逐字段归位表 A-D / StrategyState 外部读者迁移 / game_state_of 退役 / 关键取舍」），且**十二 payload 槽表、瞬态槽三分语义（在屏失读不写不读、判别信号定死）、在屏前置抛错契约、刷新重决策腿分屏形态（encounter 同访问二次覆盖 vs supply/invest 交回重入）、`encounter_refreshed_in_visit` 的完整写读契约（复位随 handle 进入而非实例构造、读侧 None 缺省 False、无 match 语境跳过写、不入路由清点辖域）在四份文档中全部没有重述**。landing 3.1 的「契约 g」引称同样无解（契约 g 定义在被取代迭代 §2.2-g）。这些语义的实际唯一宿主 = `changes/2026-09-16-strategy-input-unification/design.md` §2——该目录已申报「不再落地」，且 changes/ 按铁律「会不定期、无理由删减」。落地判据（3.1「十二槽…注释带归属与坐标系申报」、3.5「payload 写槽接线」「encounter_refreshed_in_visit 四格对照」）的规格单一源因此缺失。
**修正方向**：把前置迭代 §2.2（槽位表全 12 行：槽名/类型/唯一写者/读者/现状→动作）、§2.2-c（瞬态三分 + 刷新重决策分屏形态）、§2.1-4（per-visit 位完整契约）实质重述进 details（新增「输入承载契约」节），design §2.1 改指该节；或在 details 卷首以「随本迭代收编的既有语义附件」形态整篇并入。删除「重述于 details §2」的不实指针。

### [B2] blocker | design.md §2.2「pick 族动作化」；代码锚 `kernel/cw_events.py::PickEvent.refresh_slots`（cw_events.py:515-586）、`operations/cw_screen/cw_screen_invest_strategy.py::_decide_and_act`（:425-477）
**发现内容**：输出统一宣称「九个选择入口统一返回 PickOption(idx, reason)」「行为零变化——同槽产物 → 同 idx/同动作语义」，但**投资策略逐卡刷新建议（`PickEvent.refresh_slots`，ADR-0600/math_proofs P81 在产行为）在单一动作词表中没有任何载体**：`PickOption` 只有 idx/reason 两字段，`RefreshNodeOptions()` 无参。现状该建议驱动真实点击链（handler 逐槽三闸：屏上余量现读闸/容器逐卡计数闸/F2 唯一 L1 槽守卫，逐槽点「刷新次数N」钮后终结交回重入重决策）——这是每局多次发生的生产行为，不是遥测面。载体缺失的两种落地都是行为变化：建议静默丢失（不再逐卡刷新 = 决策序列变化）或 RefreshNodeOptions 兼职承载（与「encounter 刷新建议动作化」定义冲突且无参可传槽位）。同理 **`SupplyPick.refresh=True`（「无钻,刷新找钻」，cw_screen_supply_node 在产链）在 design §2.2 只字未提**（只命名了 encounter）。
**修正方向**：三选一并写入 §2.2：①`PickOption` 增 `refresh_slots: tuple[int, ...] = ()`（invest 专用字段，坐标系注释照 [索引定义] 模板）；②`RefreshNodeOptions` 带槽位参数并定义 invest/supply/encounter 三屏的语义映射；③显式申报「invest/supply 刷新建议通道本批保留 Pick 载体、输出统一辖域收窄为其余入口」——但③与「单一 CwAction 基型」的终态四条冲突，须用户裁定。同时 §2.8 的行为零变化申报相应收窄。

### [B3] blocker | design.md §2.2/§2.7；代码锚 `operations/cw_op/cw_action_registry.py`（:149-153 五条 pick 注册行）、`operations/cw_op/cw_overlay_pick_action.py`（EncounterPickOp/SupplyPickOp/MegastarPickOp/PartnerPickOp/PlannerPickOp + OverlayPickExecEnv）、`kernel/cw_events.py::PICK_ACTION_TYPES`（:912）、各 handler act 段（cw_screen_encounter.py:393 `action_op_for(EncounterPick(idx=idx))` 等）
**发现内容**：pick 输出的点击链执行**按类型键控**：五个 XxxPick 类型 → 注册表五行 → 五个 op 类（确认链机械体，机械参数由 handler 经 OverlayPickExecEnv 显式传入）。改成单一 `PickOption` 类型后 `action_op_class_for(PickOption)` 只能解析到一行，**九个画面的确认链分发在类型键控注册表上结构不可表达**。design §2.7「pick 族 handler 把 PickOption.idx 映射到既有 _card_point 点击链——翻译逻辑留在 handler」实际含义 = 撤销统一动作工厂批 4 的收编（overlay act 段退出注册表工厂），但这一结构性退役（注册五行更替/删除、cw_overlay_pick_action.py 五个 op 类与 OverlayPickExecEnv 的归宿、EventPick 基类与 PICK_ACTION_TYPES 的处置、注册完备锁 test_cw_unified_action_4 的遍历面变化）**全文未申报**；landing 3.5 文件面**不含 `operations/cw_op/`**，实现者合法改不到这些文件。design §2.2「执行注册表按具体类分发，注册面不动」对 shop 成立、对 pick 不成立，未作区分。
**修正方向**：§2.2 增「pick 输出的执行分发面」小节，逐项定死：注册表五行更替形态（按调用面 handler 分发则申报批 4 收编面的退役与替代分发形态）、PICK_ACTION_TYPES/EventPick 处置、注册完备锁的遍历词表更新；landing 3.5 文件面补 `operations/cw_op/cw_action_registry.py`、`operations/cw_op/cw_overlay_pick_action.py`。

---

## Major

### [M1] major | landing.md 3.1/3.3/3.4/3.5「文件面」；代码锚 `strategies/impl/cw_strategy.py:190`（CurrencyWarMatch 定义）、`kernel/cw_plane_table.py`、`kernel/cw_exec_state.py`、`operations/cw_op/cw_op_equip_all.py`、`prep_actions.py`（包根）、`obs/cw_back_layout.py`、`obs/cw_identity_obs.py`、`kernel/cw_reconcile.py`、`telemetry/cw_match_recorder.py`、`strategies/impl/mandate_v1/{__init__,entry,economy_cycle,mandate_state,sell_gate,encounter,pick_bias}.py`
**发现内容**：范围承诺的动作在对应阶段文件面无承载（大原子完整性缺口，逐项实证）：①3.1 要求「Match 容器加 gs/performance 字段」，但 `CurrencyWarMatch` dataclass **定义在 cw_strategy.py:190**，3.1 文件面只列 `cw_strategy_manager.py`（构造点）不列 cw_strategy.py（定义点）——3.1 合法改不到 dataclass；②3.3 范围含 `last_owned_equips` 换源，其读写点在 `kernel/cw_exec_state.py`（:83-86/:141-147 逻辑写腿）与 `operations/cw_op/cw_op_equip_all.py`（:93-96/:480），3.3 文件面两者皆无；③§A 四槽读者含 `kernel/cw_plane_table.py`（schedule_of/node_t_of/nodes_of_plane 全收 session 形参，cw_plane_table.py:70-130），3.2/3.5 文件面均未列；④3.4「ops/impl 调用点」按目录枚举漏掉包根 `prep_actions.py`（game_state_of(match.session) 10+ 处）、`obs/cw_back_layout.py`、`obs/cw_identity_obs.py`、`telemetry/cw_match_recorder.py`、`currency_war_app.py`；⑤3.5 impl 桶括号枚举「cw_strategy/flow/bridge/shop/cw_strategy_session 残余」漏 `mandate_v1/__init__.py`（:47 `install_strategy_state_factory(StrategyState)` 模块级副作用随工厂退役必须删）、`mandate_state.py`（state_of 本体）、`entry.py`/`economy_cycle.py`/`sell_gate.py`（state_of 调用面）。普查对账表能检出这些点，但按停手令 worker 只能打回设计——等于每个都要返工一轮设计修订。
**修正方向**：各阶段文件面按普查词表实跑结果重列（或改为「普查对账表驱动，文件面 = 命中文件全集」的显式口径）；3.1 文件面补 `strategies/impl/cw_strategy.py`。

### [M2] major | landing.md 3.2「完成判据」普查词表；details/session-dissolution.md §A
**发现内容**：3.2 宣称对「details §A 表全族」做普查对账，但词表只有**十符号**，§A 实为 **14 字段**——漏 `last_hp_real_node`、`last_node_type`、`plane_node_table`、`plane_node_table_plane` 四个。这四个恰是防御 getattr 读法重灾区（`cw_plane_table.py:122`、`cw_screen_battle_wait.py:661`、`strategies/impl/mandate_v1/statefn/predicates.py:417-444`、`cw_screen_prep.py:2551` 全是 `getattr(sess, '<名>', None)` 形态）——漏迁移**不炸而静默降级**（如 plane_node_table 缺失 → 位面轮数退 (9,9,9) 先验、log 告警一行），十词普查清零会产出假阴性收口。
**修正方向**：3.2 词表补全 14 名（或改为「details §A 表逐字段名」引称），并把「防御 getattr 形态命中必须逐条归类、禁以炸错代普查」写进完成判据。

### [M3] major | design.md §2.4/§2.9、details §C「帧触发切 gs 机制」；代码锚 `kernel/cw_game_state.py:2908/3341-3350`（gs.frame_obs 单槽 + mark/consume_frame_obs）、`obs/cw_observation.py:2697`（在产写端）、`cw_game_state.py:3975/4274`（合成口 mark('full')）
**发现内容**：「方向刷新触发单源合一」把 session 双槽（prep_frame_class/shop_frame_class）切到 gs **单槽** frame_obs，但该槽已是 chain-observation 批的**在产机制**：cw_observation.py:2697 每备战帧按 spec 命中标 `'view'/'full'`。两个系统同值不同义（chain-obs 的 view = spec 限读；方向刷新的 view = 派生帧只刷视图），且消费即清（consume_frame_obs 复位 'none'）——合并后**双消费者互偷标记**：方向刷新消费一次即清掉 chain-observation 待消费的标注（或反之）；session 双槽并单槽后的交错写序（prep 逻辑态直写步每迭代写 'none'，若与 shop visit 的 pending 'full' 交错是否互抹）全文未分析。另 sim 侧帧类写点（session.md §2.1 在册「sim engine 每决策段」）在现行重写后的 sim 树中是否存在未核，设计未申报。
**修正方向**：§C 补三件事：①两系统 view/full 语义映射表（或声明 chain-obs 槽与方向刷新槽各自独立、只共享 FrameObsLevel 类型——那「单源合一」表述须改）；②消费互斥协议（谁先消费、消费后对方读到什么缺省）；③双槽→单槽交错写序分析或声明保留双槽各挂 gs。正本 `game_state/chain-observation.md` 补入正本更新清单（当前缺席）。

### [M4] major | details/session-dissolution.md §B「last_owned_equips → gs 装备库存」；代码锚 `kernel/cw_exec_state.py:83-86/:141-147`、`operations/cw_op/cw_overlay_pick_action.py:117-120`（ConfirmSupply 到账写边）、`flow.py:663`（decide_box_card owned_spare 读者）、fields.md §3.2.15（gs.equips 写端清单）
**发现内容**：session.last_owned_equips 与 gs.equips **不是逐字节同源账**：session 份有「选卡/确认到账 +1 件」（cw_exec_state 逻辑推进腿，经 ConfirmSupply/事件确认链触发）与「穿戴 −1」执行位腿；gs.equips 的写端清单（fields.md §3.2.15）**刻意没有这两条腿**（「补给/事件获得的装备不记预期值,经观察覆盖收口」是在册豁免申报）。直接把读者（decide_box_card 的 owned_spare 近兑现对数、cw_observation:2667 relay 兜底）换源 gs.equips，在「到账 → 下一次装备区观察」窗口内读值不同 → 违反 details 约束①「每字段迁移后读到的值与迁前逐字节相同」，且会改武装箱选卡打分输入（行为面）。设计只写「session 份先退役」未申报写腿差。
**修正方向**：二选一：①迁移时把 exec_state 两条腿移植为 gs.equips 的 write_logic 写端并同步 fields.md §3.2.15 写端清单与 §4.1 豁免申报（部分腿退出豁免 = 行为申报）；②申报「last_owned_equips 读者本批挂账随 owned 库存域批换源，session 槽降级为该批前唯一宿主保留」——则 details §B 该行删除。禁止现状方案直接换源。

### [M5] major | design.md §2.1/§2.9「rng 随构造种子化」「sim 构造时传含 seed 的 config」；代码锚 `cw_strategy_manager.py:77-78`（现状唯一覆写点）、`sim/`（cw_sim_engine.py:397 stream_rng；全树无策略构造、无 session.rng 读者）
**发现内容**：两处 as-built 断言失真：①种子语义翻转未申报——现状 `strategy_seed=None` 时**不覆写**，session.rng 保持缺省 `Random(0)`（确定性）；新构造 `random.Random(config.strategy_seed)` 在 None 时 = OS 熵种子（真随机）。当前 src 树 `session.rng` 零读者（行为面差为零），但种子契约锚（cw_strategy_session.py:192-196「None 禁 OS 熵」注释）的语义被静默反转，一旦出现消费方即按新语义走；②「sim 从局 seed 派生的现状口径不变（sim 构造时传含 seed 的 config）」指向**已不存在的树**：现行 sim 引擎（cw_sim_* 重构后）不构造策略器、rng 为引擎自有流（`stream_rng(eng.seed, …)`），唯一策略构造点 = `sim/cw_replay.py:88/108`（`MandateV1Strategy()` + `create_session(_Cfg())`）。§2.7「sim 引擎…构造 (gs, config) 每局」同此失真——照文实现会去找不存在的 sim 构造点。
**修正方向**：①§2.1 补 None 分支语义裁定（`None → Random(0)` 保旧 or 显式申报改熵种子）；②§2.7/§2.9 的 sim 行改写为 as-built：改动面 = cw_replay 一处构造 + decide_shop_screen 驱动器签名随批，sim 引擎零接触；cw_strategy_session.py:192-196 的旧锚注释随批清除（入普查词表「run loop 覆写」叙述形态）。

### [M6] major | design.md §2.6/landing.md 3.5/3.6；代码锚 `cw_strategy_manager.py:89-91`（game_state_of 建立路径注入 run_id_provider）、`kernel/cw_state_journal.py:404-486`（install_state_telemetry/ensure_journal_assembly）、正本 `game_state/journal.md` §7（生产注入漏斗 = establish_new_match 容器建立点 + game_state_of 局容器建立路径）
**发现内容**：journal 遥测装配的**唯一触发锚 = `game_state_of(session)` 局容器建立路径**（GameState 构造器刻意零装配逻辑——正本在册裁定）。本批退役 game_state_of 旁口、gs 改为 Match 字段由漏斗直建后，该锚随符号消亡：**新局 gs 的 run 归属注入与 ensure_journal_assembly 触发没有任何阶段承接**（3.5 范围只写「引导漏斗 (gs, config) 构造 + Match 终形」），漏接的故障形态 = journal 行静默不落（「诚实缺失」面），要到 3.7 核对单才可能暴露。正本侧 `game_state/journal.md`（§6 写入口 API 面/§7 装配锚）也**不在正本更新清单**。
**修正方向**：3.5 范围显式增「漏斗内 gs 建立点接管装配触发（run_id_provider 注入 + ensure_journal_assembly，语义 = 现 game_state_of 建立路径等价平移）」；正本更新清单补 `game_state/journal.md` §7（装配锚改指新建立点）行。

### [M7] major | design.md §2.2/§2.9「HoldFrame/外循环 stall 门」；代码锚 `operations/cw_screen/cw_screen_prep.py:1553-1556`（None → round_success 交回）、cw_loop.py 全文（无连续 None 计数对象）
**发现内容**：两处断言与代码不符 + 执行语义缺失：①「外循环 stall 门改计连续 HoldFrame（计数逻辑等价平移）」「代价 = 外循环一处计数对象改名」——**全仓不存在「连续 None」计数对象**：现行 None 路径 = prep 处理器 `round_success('本帧无动作,交回外循环重观察')` 直接交回，运行级停滞防线是哨兵 stall_watch/NODE-DWELL（watch 总体进展，非计 None 帧）。「等价平移」「改名」是对不存在的机制作断言；②HoldFrame 作为动作进入 prep 循环后的路径未定义：`action → _executor.validate → _act_execute → action_op_class_for`（词表外 = AssertionError 响亮暴露，cw_screen_prep.py:1591-1597 在册）——HoldFrame 需要 CW_ACTION_TYPES 登记、terminal op 注册行、action_key/journal receipts/`_visit_acts`/`cw4_frame_action_record`（:1582-1585 状态写入会把动作名记进遥测）的逐面处置，设计只写了返回类型与 stall 门，实现者必须自行设计拦截点（注册表前短路？op 行 terminal=True？）与遥测足迹。
**修正方向**：§2.2 重写 HoldFrame 段：拦截点定死（建议 = prep 循环在 validate 前识别 HoldFrame → 沿用现 round_success 交回路径，零注册零执行）、申报「无既有计数器，连续 HoldFrame 计数 = 新增防线（若立项）或明确不设」、遥测足迹逐项申报（cw4_frame_action_record 是否记 HoldFrame、_visit_acts 是否计入、VISIT_ACTION_CAP 是否消耗）。

### [M8] major | landing.md「正本更新清单」`flow/journal.md` 行
**发现内容**：正本更新清单与 3.1 设计依据引 `flow/journal.md` §6——**该文件不存在**：journal 正本实际在 `game_state/journal.md`（flow/ 七篇中无 journal.md）。末阶段按清单派工即命中不存在路径；且 §6（写入口 API 面：leave_screen/ChannelSig/刷新计数组豁免类）确实是路由清点行 sig 形态与 `encounter_refreshed_in_visit` 归属申报的正确归宿，属路径笔误而非行应删除。
**修正方向**：路径改 `game_state/journal.md` §6；借 M6 一并补 §7 装配锚行。

---

## Minor

### [m1] minor | design.md §2.4 家族表
「五镜像 + chosen_* + owned_equips + **节点序列台账** → gs 正本已存在」——session 没有节点序列台账字段组（gs.plane_node_sequences 属 execstate 已迁，前置迭代产物；session 的 plane_node_table 是位面探针表，归 details §A）。家族表（总纲）与 details 分解不同步，幻影行会误导读者以为 session 还有台账要迁。修正：删该词或改注「（前置迭代已迁，无 session 份）」。

### [m2] minor | design.md §1.1/§2.4
以 **gs 字段名指称 session 字段**：「五镜像字段（…plane_bosses/enemy_affixes…）…session 份是重复账」——session 上的实际字段名是 `briefing_bosses`/`briefing_affixes`（cw_strategy_session.py:182/190），gs 侧才叫 plane_bosses/enemy_affixes。「值对标签错」类：值结论（重复账）对，标签错。修正：§1.1 改用 session 真名或标注「session 名 briefing_* ↔ gs 名 *」。

### [m3] minor | design.md §2.2 vs §2.1
「**九个**选择入口统一返回」与 §2.1 十二零参入口中 pick 族实为 **10**（invest 拆分后：invest_strategy/invest_env/supply/encounter/megastar/partner/planner/star_tome/wish_trial/box_card）篇内不同步（landing 自己申报了「九接口/十入口口径对齐」却没改 design 正文）。另「商店词表（BuyCard/LevelUp/RefreshShop/CloseShop）**并入为 CwAction 子类**」表述成结构变更——四类**本就是** CwAction 子类（cw_vocab.py:374-576），`Action` 只是类型别名（:648），现状差异仅在返回标注与 None 语义；§1.1「三族并存」的商店族描述随之失真。修正：计数改 10；「并入」改「返回标注 Action 别名退役、签名归一 CwAction」。

### [m4] minor | design.md §0 承接出处 / README.md 承接出处
「该迭代 **13 轮对抗**的语义裁定」= 过程叙事入设计正文（iteration-design 硬规则 3：「第几轮攻击」类措辞打回；且该计数随 changes/ 清理死亡）。修正：改「该迭代对抗收敛的语义裁定」。

### [m5] minor | landing.md 3.2/3.3 设计依据
「design.md §2.4-**A** / §2.4-**B/C**」锚不可解析：design.md §2.4 是无字母小节的家族表，A/B/C/D 只存在于 details。修正：改为「design.md §2.4；details §A/§B/C」。

### [m6] minor | design.md §2.5 普查词表
`state_of`、`strategy_state` 两词是 `game_state_of`/`strategy_state_of` 的**子串**——两仓普查时三词互相污染（game_state_of 的 460 处命中会涌入 state_of 桶），分桶前必须显式声明排除规则，否则对账表噪声淹没真实命中（kernel 内 `card_state_of`/`selection_state_of` 等同形词也会误中）。修正：词表改写成正则边界形态（`\bstate_of\b` 等）并在对账表机制句中声明。

### [m7] minor | README.md「承接出处」节
复制 design §0 的裁定内容与「终态契约四条」（第二抄本）：iteration-design §4 限定 README「只做两件事——串文档、记进度；不放判据、不放松散笔记」，规则 1 禁集中抄本（必漂移）。修正：README 承接出处收缩为一行指针（「详见 design.md §0」）。

### [m8] minor | landing.md 首节「通用工程门」
把 L1 定义为 CW 目录级（`pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`），却标注「源 = 项目 AGENTS.md『测试规范』」——AGENTS 的 L1 是 `sr-od-test/` 全量。引用与内容不符（借用同名标签改口径应自证，不应挂源）。修正：改口径名（如「L1-CW」）或扩回全仓。

### [m9] minor | design.md §2.10
unified-obs-reconcile 3.4 冲突面只列「cw_screen_prep.py/cw_screen_buy_cards.py 相交」——其落地文件面实际还含 `kernel/cw_game_state.py`、`obs/cw_observation.py`、`operations/cw_loop.py`（本批 3.1/3.2/3.3/3.5 同面）。3.1 已挂「3.4 落码收」依赖所以主排期安全，但 §2.10 同时提供了「开工前协商解耦」选项——按不完整的交面清单去协商会谈漏三份文件。修正：§2.10 交面清单补全。

### [m10] minor | design.md §2.5 桶 2 / 核三·关键取舍
「执行层/流程层读者改读 `ctx.cw_match.strategy.state` 具名字段」把跨层读从隐性 getattr 变显式直读——诚实化成立，但耦合本体保留；「把执行层真实消费面字段（target_comp 消费位/cw4_visit_bought_names/cw4_m1p_* 登记位）升为 Match/gs 契约面字段」这一备选未进关键取舍。修正：关键取舍补一行备选与放弃理由（如「字段语义归策略私有、升契约面 = 契约面膨胀」），否则治本论证缺一块。

---

## 三核覆盖与行为零变化专攻结论

- **核一（无前提）**：B1/B2/B3 + M1-M8 全部落在此核（终态四条中「输出统一」维度两处无落位、「构造注入」维度漏斗/装配锚不自洽；跨文档引用锚两类断裂；3.5 大原子内部完整性文件面缺口）。
- **核二（规范遵循）**：m3/m4/m5/m7/m8 + B1 的引用锚面（iteration-design 四硬规则之 2/3/4 违例各有着落；阶段七件、README 构成、状态标注均合规）。
- **核三（治本）**：§1.2 归层「约定层」成立（契约三维度历史演化无终态约定，代码实证支持）；§2 方向治本成立（解散混装载体的中间层、状态归所有者、输出单基型 = 契约终态化，非症状补丁）；保留缺口见 m10。
- **行为零变化申报专攻**：五条攻击线结论——①session 字段迁移值等价：last_streak/chosen_*/五镜像成立（gs 正本经观察漏斗由 session 镜像喂入，换源后值同源），**last_owned_equips 不成立（M4）**；②构造注入生命周期等价：实例不跨局/异常弃置/恢复局冷启动三条成立，**rng None 种子语义不成立（M5）**、journal 装配生命周期悬空（M6）；③输出动作化语义等价：encounter 刷新通道可平移、shop CloseShop 终结不变，**invest refresh_slots 与 supply refresh 无承载（B2）、HoldFrame 执行语义未定义（M7）、pick 注册表分发断裂（B3）**；④StrategyState 读值等价：判据面防御 getattr / 行为面显式解引的两形态划分与 ADR-0563 一致，等价成立（kernel 参数注入桶的「多已有形参位」陈述经 cw_economy:1235-1237、cw_deploy_logic:1541-1601、cw_intention:2378/2680 抽核属实）；⑤每阶段独立可绿：3.2/3.3/3.4 在 session 存活前提下可独立验收，**3.5 的可绿性依赖 B1/B2/B3/M1 先修**（否则普查对账表必然非零未承载、停手令连环触发）。
