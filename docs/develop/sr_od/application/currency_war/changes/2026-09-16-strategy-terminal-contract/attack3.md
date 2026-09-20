# attack3 —— 策略器终态契约 迭代设计 对抗审查报告（r3，独立干净上下文）

> 审查对象 = 本目录 design.md / details/session-dissolution.md / landing.md / README.md（当前工作树版本）。
> 判据源全部直调复核：iteration-design.md（四硬规则/§7 三核/阶段七件/README 构成）、00_framework.md、01_math_framework.md、
> fields.md（§2.1/§2.2/§3.2/§3.4/§3.7.1/§8.8/§9.4）、flow/README.md §2、flow/session.md、flow/outer_loop.md、
> game_state/journal.md §6、flow/action_exec.md、AGENTS.md §8-§11、strategy-work §6（对抗纪律）、
> 在飞迭代四目录 README、被取代的 strategy-input-unification 全套（含 13 轮 attack）。
> 代码真值 = `src/sr_od/application/currency_war/` 逐文件直读 + 两仓（src / sr-od-test）全量普查
> （Select-String 逐文件计数，规避 rg 从仓库根因 .gitignore 跳过 sr-od-test 的坑）。数值/口径/引文均为直调值。
> 前两轮报告（attack.md 21 条 / attack2.md 21 条）已读；本篇不重复其已消解项，但**对「已消解」声明与正文实态做了逐条回访**——
> 回访发现多处消解未落正文，作为发现如实列入。

## 发现总数：23（blocker 2 / major 13 / minor 8）

---

## blocker

### B1 landing 各阶段「范围承诺 ⊃ 文件面授权」多处失配——按停手令 worker 无法开工，四处置信实证（同类问题 attack1 已报、声明消解后仍未修全）

- **位置**：landing.md 3.1/3.2/3.4 范围行 vs 各自「文件面」行；对码锚见下。
- **发现内容**：逐阶段试读「范围里每个动作在文件面内有承载」，四处不匹配：
  - ① **3.1**：范围写「Match 加 `gs`/`performance` 字段并引导漏斗填充（additive）」，但 `CurrencyWarMatch` 定义在
    `strategies/impl/cw_strategy.py:190`，3.1 文件面只列 `kernel/cw_game_state.py`、`kernel/cw_vocab.py`、
    `operations/cw_loop.py`、`strategies/impl/cw_strategy_manager.py`——**不列 cw_strategy.py**（attack1 首轮已报，
    当前正文未改）。改数据类与改构造点必须同批，分置两阶段 = 半态。
  - ② **3.2**：范围①「`last_owned_equips` 删」的**写腿**不在文件面——直调写点全集：
    `kernel/cw_exec_state.py:83-86`（选卡到账 +1）、`kernel/cw_exec_state.py:140-146`（穿戴 −1）、
    `operations/cw_op/cw_op_equip_all.py:93-96/:480`（穿戴覆写）、`operations/cw_screen/cw_screen_prep.py:737`
    （主写端，在面）；**读腿** `obs/cw_observation.py:2647-2649`（载体中继兜底读点，cw_observation 只在 3.3/3.5 文件面）。
    范围②「hp 新鲜度门删」的策略侧**薄委托本体** `strategies/impl/cw_strategy.py:255`（`gated_hp`，其 docstring 自报
    消费点含 mandate_v1 adapter decision_state ×1 + encounter λ 键读点 ×1）不在 3.2 文件面（mandate_v1 子树只在 3.5）。
    另：节点三字段消费者 `operations/cw_screen/cw_screen_buy_cards.py:1027-1028` 也不在 3.2 文件面（见 M8）。
  - ③ **3.4**：文件面 =「`operations/`、`strategies/impl/` 调用点」，但 `game_state_of(` 全仓 152 处调用中在**两个目录之外**的
    非 KERNEL 调用方无任何阶段承载：包根 `prep_actions.py`（422/501/508/598/753/772/777/792/805，3.5 只列其
    HoldFrame 分支语境）、`obs/cw_back_layout.py:569`、`obs/cw_identity_obs.py:588/613/1608`、
    `currency_war_app.py:213`。3.6 以「`game_state_of` 符号两仓普查归零」收口，这四个文件的调用点按文件面合法改不到。
    （attack1 ④ 已报同类；当前仅 prep_actions 在 3.5 面挂名，其余三处仍悬空。）
  - ④ **3.2/3.3 的「unified-obs 3.4 落码收」前置只解了 3.2/3.3**：3.4 文件面 `operations/` 与 unified-obs 3.4 文件面
    （`cw_screen_prep.py`/`cw_screen_buy_cards.py`/`cw_shop_action_ops.py`）实际相交（`cw_shop_action_ops.py:225` 有
    `game_state_of` 调用点），见 M12。
- **修正方向**：逐阶段把「范围动作 → 承载文件」对齐：①Match 字段项移入 3.5 或把 cw_strategy.py 加进 3.1 文件面；
  ②3.2 文件面补 `kernel/cw_exec_state.py`、`operations/cw_op/cw_op_equip_all.py`、`obs/cw_observation.py`（中继读点）、
  `strategies/impl/cw_strategy.py`（gated_hp 处置）+ mandate_v1 两消费点（或显式声明 decision_hp 保 (gs, session)
  签名过渡到 3.5）；③3.4 文件面补包根 prep_actions.py、obs/ 两文件、currency_war_app.py（或明确并轨 3.5 面并改写 3.4 范围）。

### B2 landing 3.7 验收锚与 design §2.8 直接矛盾：「`cw_decision_trace` 决策迹锚对照」所引模块现役零接线，验收判据不可执行

- **位置**：landing.md 3.7 范围③④（「HoldFrame 帧入迹」「`cw_decision_trace` 决策迹锚对照」）vs design.md §2.8 终验（「锚 =
  journal 动作行……`cw_decision_trace` 模块零接线不引用」「HoldFrame 帧以 round 日志文本可见（不入册）」）。
- **发现内容**：直调复核：`install_decision_trace`/`record_decision_frame`/`reset_decision_trace_anchor`
  全仓（src + sr-od-test）**零生产调用点**（仅 cw_decision_trace.py 自身定义与注释、economy_cycle/mandate_state 注释提及）——
  attack2 M4 已判此锚无对照物且**声明消解**；design §2.8 已改为 journal 动作行锚，但 **landing 3.7 未同步**，
  仍保留旧锚与「HoldFrame 帧入迹与 §2.8 申报一致」的旧口径（§2.8 现口径 = HoldFrame 只以 round 日志可见）。
  阶段验收凭据引用一个不存在的对照物 = 该阶段验收判据不可执行，触碰定稿门槛（阶段可验收性）。
  同时它实证 README「r2 21 条已消解」的消解落实不完整（另见 M1）。
- **修正方向**：landing 3.7 ③改「HoldFrame 帧以 round 日志文本核对」；④改「journal 动作行锚对照（与改前同难度局）」，
  删除 `cw_decision_trace` 引用；同步检查 design §2.8 与 3.7 的可观测性申报措辞逐字一致。

---

## major

### M1 design.md §2.1「`mandate_v1/shop.py` 本体已 gs-first 零改动」与 landing 3.5「shop.py 改形（现役 ~68 处 session 消费）」同迭代内直接冲突；attack2 M2 判失实并声明消解后正文未改

- **位置**：design.md §2.1 实现位分布行 vs landing.md 3.5 范围行。
- **发现内容**：对码：`flow.py::decide_shop_action` 以 `shop.decide_shop_action(gs, session, config, registry=…)`（flow.py:713）
  调用 mandate 本体；shop.py 内 `session` token 76 处、`state_of(` 19 处、`game_state_of(` 1 处（直调计数）。session 解散后
  该签名与状态通道**必须改形**——landing 3.5 与码面一致，design §2.1 括注「零改动」是被取代迭代（旧设计旧契约下成立的表述）
  的残留。两文冲突且 README 宣称该条已消解，属「消解未落正文 + 设计↔落地失同步」（iteration-design 硬规则 4 卡点）。
- **修正方向**：design §2.1 括注改为「判据语义零触碰（签名/状态通道改形随 landing 3.5，普查对账表兜底）」。

### M2 路由清点的两条核心语义在「自足重述」中丢失：命中映射屏的清点规则与非身份臂语境的全清规则

- **位置**：design.md §2.3、details/session-dissolution.md §2.2；被取代目录 design.md §2.3（承载被丢弃的原文）。
- **发现内容**：旧设计（strategy-input-unification/design.md §2.3）钉死两条：①「识别命中且在映射内 = 该屏名，
  **只清属屏 ≠ 它的槽**」；②「映射外建档屏 / 非身份臂语境（**阶段二备战双锚、阶段三特殊规则臂**）/ 未识别 = 清全部十槽」。
  新 design §2.3 + details §2.2 只重述了挂点位置、十行映射、shop route_clearable=False、已 None 跳过、早退/未识别两路径——
  ①②两条消失。①是挂点的主规则（没有它，外循环每轮都会清掉命中屏自己的槽，supply 重入型 handler 的跨轮次槽保活语义被破坏）；
  ②覆盖阶段二/阶段三臂的清点行为（现行代码 `cw_loop.py::loop` 阶段一命中即 return，阶段二双锚/阶段三臂是独立分支，
  识别产出的取值规则必须逐分支定义）。实现者按现文开工必须自行再设计规则 = 违「实现者无需再设计」；同时实证
  「继承并就地重述」声明（README/design §0）对该段不真实。
- **修正方向**：details §2.2 补回①②两条（逐分支语境枚举：阶段一命中映射屏 / 阶段一命中映射外建档屏 / 阶段二双锚 /
  阶段三特殊规则 / 未识别兜底 / stop_at_prep 早退），并标注与旧设计的继承关系。

### M3 路由清点写端 actor `'cw_loop_route_clear'` 未预登记进 `REGISTERED_ACTORS`——首次清点写入即在册校验炸错

- **位置**：design.md §2.3、details §2.2（`actor='cw_loop_route_clear'`）；landing.md 3.1（actor 预登记行）；
  代码锚 `kernel/cw_game_state.py:284-335`（REGISTERED_ACTORS 现值）、`:361-371`（`_validate_sig` 在册硬校验）、
  `:3149-3160`（leave_screen 走 obs 族 + 在册校验）。
- **发现内容**：直调现值：REGISTERED_ACTORS 含 `CwLoop` 但 **无** `cw_loop_route_clear`。清点写入口经
  `leave_screen(槽, sig=…)`，sig.actor 必须在册，缺登记 = 第一次「在屏→离屏」转换即 ValueError 响亮炸错（live 首轮必现）。
  landing 3.1 只预登记了 `CwScreenYinLang`/`CwScreenBoxPick`。
- **修正方向**：landing 3.1 actor 预登记行补 `'cw_loop_route_clear'`（或改用已在册的 `CwLoop` 并同步设计文）。

### M4 输出词表入册形态未定义：8 个不走注册表的新动作类型与 `CW_ACTION_TYPES` 白名单 / 注册完备锁 / `PICK_ACTION_TYPES` 的关系无承载

- **位置**：design.md §2.2（「CW_ACTION_TYPES 白名单与注册完备锁随批纳入（新类型全量入册，例外申报）」）、landing 3.1 判据；
  代码锚 `kernel/cw_vocab.py:828-837`（CW_ACTION_TYPES 现值 22 类，**不含** PickEvent）、
  `kernel/cw_events.py:895-900`（`PICK_ACTION_TYPES` + `EventPick` 联合）、
  `operations/cw_op/cw_action_registry.py:7-13`（注册完备锁 = 遍历 `CW_ACTION_TYPES` **+ `cw_events.PICK_ACTION_TYPES`**
  逐类断言注册表可命中）、`:149-153`（五条 pick 注册行）。
- **发现内容**：新词表 13 类中仅 5 个（PickEncounter/PickSupply/PickMegastar/PickPartner/PickPlanner）有注册行承接；
  `PickInvest`/`PickStarTome`/`PickWishTrial`/`PickBoxCard`/`RefreshNodeOptions`/`RefreshSupply`/`RefreshInvestCards`/
  `HoldFrame` 共 8 类是 handler 自管消费（无动作 op）。「全量入册」若指入 `CW_ACTION_TYPES`，注册完备锁逐类断言注册命中
  即红——需要一个**指名道姓的豁免/锁改形规格**（哪些类豁免、锁的遍历源怎么改），「例外申报」四字不是规格。
  且 `PickEvent` 退役后 `cw_events.PICK_ACTION_TYPES`/`EventPick` 的退役或换名零申报（锁的第二个遍历源、
  `action_op_for` 的 `Action | EventPick` 形参联合都要跟着变）。attack1 m10/attack2 m10 均触此面，
  现文仍未给出可执行形态。
- **修正方向**：details 补一节「新词表 × 白名单 × 完备锁」：8 个 handler 自管类是否入 `CW_ACTION_TYPES`（建议：入册 +
  锁加显式豁免名单常量，锁测试逐名断言）；`PICK_ACTION_TYPES`/`EventPick` 随 Pick 族改名的处置行；`HoldFrame` 不入
  validate/`_act_execute`/注册表的实现约束（分支判等先于 validate 的顺序申报）。

### M5 `performance` 的换宿主面漏掉唯一 kernel 读者；reconcile_hp 对账层的整体改形（保旧不写/下行背书/上行留证/帧龄门）无落位说明

- **位置**：details/session-dissolution.md §C（「`performance` → `CurrencyWarMatch.performance`（battle_wait 结算点写点换宿主）」）、
  §A（`last_hp_real`/`last_hp_real_node`/`hp_suspect` 行）；代码锚 `kernel/cw_reconcile.py:401-441`
  （`_battle_facts_between` 读 `session.performance.history`）、`:449-490`（`_reject_down` 读写 `hp_suspect`/
  `last_hp_real`/`last_hp_real_node`）、`:492-616`（`reconcile_hp` 主链：读不到沿用 `last_hp_real` 保旧不写、
  上行 ≥HP_REAL_JUMP_CONFLICT 留证、帧龄门、下行仲裁调 `_battle_facts_between`）。
- **发现内容**：§C 的 performance 行只申报了 battle_wait 写点换宿主，但该字段的**唯一读取方在 kernel**
  （`cw_reconcile._battle_facts_between`）。两条出路二选一，现文都没选：①下行背书随 §A 一并删（hp_suspect 通道关闭 +
  「读什么用什么」）→ `_battle_facts_between` 连同 `performance.history` 的 kernel 读取一起消亡，
  但该留证链（obs_conflict 证据面）与「reconcile_hp 变成什么、备战帧 hp 由谁按什么渠道写 gs.hp」没有落位说明，
  且「读什么用什么」不是实现者可执行的规格；②背书保留 → kernel 拿不到 `Match.performance`（kernel 禁依上层），
  必须参数注入——§2.5/§C 均无此桶。另 fields.md §3.2.13 的 hp 写入闸语义（hp_readable/hp_trusted 收编口径）
  与本改形的关系（备战帧 hp observe 写端是否变化）未核。
- **修正方向**：details §A/§C 补「reconcile_hp 对账层处置」小节：逐机制（保旧不写/下行背书/上行留证/帧龄门/拒信通道）
  给出删或留的裁定 + 保留时的宿主与注入方式；§C performance 行补读点归零或换宿主申报。

### M6 star 防抖删除的连带行为面未申报：停机钩子/留证链断供、银狼升费豁免消亡、ADR-0420 帧态门删除

- **位置**：details §A（`star_pending_regression` 行「窗内误读直接进板面账」）、design §1.3/§2.8（失准变化申报清单）；
  代码锚 `kernel/cw_reconcile.py:204-297`（防抖+锚定保旧+帧态门+确认采新分支，`exec_books.star_regression` 计数
  在确认分支 `:282-284` 累积）、`:627`（`_star_stop_hook`）、`:231`（银狼升费豁免「防每2局误停一次」）。
- **发现内容**：删除 `star_pending_regression` 不只删「防抖窗」一个效果：①确认采新分支消亡 →
  `exec_books.star_regression` 永不累积 → star 回退**停机钩子与留证链永久断供**（停机钩子静默失效是本项目
  od-dev-stop-hooks 纪律的高敏面）；②银狼升费豁免（防误停）随之失去存在语境；③ADR-0420 合成特效帧态门
  一并消失。§1.3 的接受项清单只写了「star 防抖」，§A 行的「窗内误读直接进板面账」只覆盖写入语义——
  三条连带变化均不在申报面。
- **修正方向**：§A star 行与 design §1.3 申报清单补三条连带（钩子/留证断供、豁免消亡、帧态门删除），
  并注明「识别优化批修识别时钩子链是否重建」的归属。

### M7 `last_streak` 消费面误报：主消费是观察喂入 + obs_conflict 仲裁，不是「economy C 杠杆读」

- **位置**：details §B（`last_streak` 行备注「economy C 杠杆读，换源现读」）；
  代码锚 `obs/cw_observation.py:2310-2325`（streak 观察值源 = `_sess.last_streak`，带方向真值；
  `_prep_streak` 与 `last_streak` 幅度不符即 obs_conflict 仲裁）、`:2633-2651`（relay 块同源）；
  `cw_screen_battle_wait.py:132-137`（写端）；`cw_economy.py:579`（C 杠杆读，注释级）。
- **发现内容**：直调全文，`session.last_streak` 的现役消费主链 = read_game_state 的 streak 喂入源 +
  无方向幅度失配仲裁；economy C 杠杆实际经 gs.streak（观察喂入后）。§B 把它标成「机械换源」并只写一个
  遥测性消费——真正的非机械面（喂入源切换 + 仲裁读点改 gs.streak 后「结算写端先于喂入」的时序等价性）
  没有被标注为需逐点保留项，普查对账时会按机械桶漏掉仲裁面。
- **修正方向**：§B last_streak 行备注改为「非机械：结算写端改直写 gs.streak 后，观察喂入与幅度仲裁读点换源，
  方向真值先于喂入的时序逐点保留」。

### M8 节点类型三字段（`last_node_type`/`node_type_current`/`upcoming_types`）删除无普查词表、无逐读者归位地图，design §2.4 家族表无行

- **位置**：details §A′ 末句（仅一句「归 §A 删除——chain-observation 为节点类型单一源」）、§A 普查词表（七符号）、
  landing 3.2 判据（「删除线七符号 + 重锚线四符号」）、design §2.4 家族表；
  消费者直调全集：`cw_screen_prep.py:486/511/638/2531-2545`（写端+左移推断链）、
  `cw_screen_battle_wait.py:424`、`cw_screen_buy_cards.py:1027-1028`、`cw_discipline_rules.py:200`、
  `flow.py:169`、`strategies/impl/mandate_v1/entry.py:787`、测试仓 6 处（test_cw_leak_ladder/test_cw_p2_blood_band）。
- **发现内容**：三字段是 §A/§A′ 之外的**第三组删除字段**（十锚删除集 = 七符号 + 三字段 + §B 的 last_owned_equips），
  但：普查词表（七符号/四符号）都不含它们 → 删除无对账兜底；无逐读者「删除后的表现」表（§A 七字段每字段有，
  三字段没有）；discipline_rules/flow 有 `node_kind_of(gs)` 兜底（等价性可证），battle_wait/buy_cards/entry 的
  消费没有等价性说明；buy_cards 不在 3.2 文件面（见 B1-②）。
- **修正方向**：§A′ 末句扩成三字段小表（消费者全集 + 删除后读法 + 等价性依据）；普查词表补三符号；
  design §2.4 家族表补行；landing 3.2 文件面补 buy_cards。

### M9 载体中继（session_carrier）/五镜像封闭集机制的宿主面未处置；fields.md §2.1 不在正本更新清单

- **位置**：details §B（无 relay 相关行）、§C；landing「正本更新清单」fields.md 行（只列 §2.2/§3.4/§3.7.1/§8.1-8.5/§9.4）、
  末阶段普查词表；代码锚 `obs/cw_observation.py:2620-2651`（relay 块六次调用，输入**全部**是待删 session 字段：
  active_strategies/active_env/plane_bosses←briefing_bosses/enemy_affixes←briefing_affixes/equips←last_owned_equips/
  selected_difficulty）、`kernel/cw_game_state.py:3188`（`GameState.relay`）、fields.md §2.1（载体中继约定 + 五镜像封闭集）。
- **发现内容**：relay 机制的输入侧 100% 是 session 字段——session 解散后机制结构性死亡，但：① relay 块的处置
  （整删 or 各字段改直写）未在 §B 逐字段申报；②「接线滞后窗值冻结申报」（equips 中继兜底，fields.md §3.2.15 在册）
  随之消失未申报；③五镜像封闭集（锁锚 = test_cw_game_state_batch4）的规格本体在 fields.md §2.1，
  正本更新清单的 fields.md 行**不含 §2.1**；④末阶段普查词表不含 relay/session_carrier/五镜像——
  正本残留只能靠运气。
- **修正方向**：details §B 补「relay 块整删 + 五镜像喂入点改各画面直写」申报；正本清单 fields.md 行补 §2.1；
  末阶段普查词表补 relay/session_carrier。

### M10 §2.5 五桶缺「kernel 无 state 形参位需新增形参」桶；「kernel 函数现状多已有 target_comp/ist 形参位」与码面不符

- **位置**：design.md §2.5、details §3 桶 1；码面反例：`kernel/cw_deploy_logic.py:1539-1554`
  （`tgt_comp`/`ist` 体内自取，无形参位）、`kernel/cw_economy.py:1235`、`kernel/cw_intention.py:2361/:2662`、
  `kernel/cw_line_switch.py:283-285`、`kernel/cw_recipe.py:119-124`。
- **发现内容**：桶 1 的迁移动作 =「调用方从 `match.strategy.state` 取值注入**既有形参位**」，并断言
  「session getattr 仅为 fallback」。直调反例：上述 kernel 消费点无既有形参位、getattr 是主读路径——
  迁移必须**新增形参**（改变 kernel 签名面），而桶 3（补 gs 形参）只辖 game_state_of，不辖 state 注入。
  这些点落入五桶中的任何一个都名不符实，普查对账表会产出无处归类的承载项。
- **修正方向**：§2.5/§3 桶 1 拆成 1a（既有形参位注入）/1b（kernel 补 state 形参 + 签名收窄申报，对齐桶 3 形态）。

### M11 `create_session` 的副作用无归位：`reset_layout_unknown_state()`（跨局布局未知态残留防线）随唯一冷建口退役后宿主未指定

- **位置**：design.md §2.1/§2.7（构造/引导漏斗迁移）、landing 3.5；代码锚 `flow.py:225-231`
  （create_session 内调用 `reset_layout_unknown_state`，docstring 自述「新局起点……防跨局残留让开局提前吃冻结」）、
  `kernel/cw_vocab.py:955-963`（槽式转发）、`obs/cw_back_layout.py:148-169`（真实现注册）。
- **发现内容**：该调用有真实行为（缺失 = 上一局布局未知态计数带入新局，开局 CV 高发不可判期提前吃冻结——
  落地审 C4 实证语义）。终态契约把冷建收敛为 `cls(gs, config)`，design/landing 都没有指定该复位调用迁到
  引导漏斗还是策略构造器；同理 `v3_phase='FORM'` live 初值（现 create_session 落位，现役零读者，风险低）
  也没指定去向。行为零变化承诺依赖一个未被安排的调用。
- **修正方向**：design §2.7 引导漏斗行补「`reset_layout_unknown_state()` 随漏斗保留（或移入构造器，二选一钉死）；
  `v3_phase` 初值随 StrategyState 构造缺省（零读者申报）」。

### M12 landing 3.4 依赖行缺 unified-obs 3.4 前置，违反本 landing 首节自定的相交挂载规则

- **位置**：landing.md 3.1 依赖行（「3.2–3.5 各自挂与其文件面相交的 unified-obs 3.4 项，见各阶段依赖行」）vs
  3.4 依赖行（只挂「3.1」）；文件面对照：3.4 面 = `operations/`（⊃ `cw_screen_prep.py`/`cw_screen_buy_cards.py`/
  `cw_op/cw_shop_action_ops.py`），unified-obs 3.4 面（其 landing.md 3.4）= `run_state.py`/`cw_screen_prep.py`/
  `cw_screen_buy_cards.py`/`cw_shop_action_ops.py`/`telemetry/query.py`/`match_archive.py`——三者相交，
  且 `cw_shop_action_ops.py:225` 有 `game_state_of` 调用点。
- **发现内容**：按现依赖行，3.4 可在 unified-obs 3.4 落码前派工，与同文件在飞批冲突——正是 design §2.10/landing
  首节声明要防的形态。3.5 经 3.2/3.3 传递等待，唯独 3.4 有洞。
- **修正方向**：3.4 依赖行补「unified-obs 3.4 落码收（相交面 = cw_screen_prep/cw_screen_buy_cards/cw_shop_action_ops）」。

### M13 末阶段普查词表与预登记清单兜不住 §B/§A 字段面在正本树的残留：01_math_framework.md 的 `aggregate_economy(session.active_strategies)` 解析口锚为例证

- **位置**：landing「末阶段：正本更新」范围②词表（decide_ 前缀/StrategySession/game_state_of/strategy_state_of/
  state_of/refresh_used/encounter_refreshed_in_visit/prep_obs_frame/PickBoxCard/计数词）+ 正本更新清单；
  对照：`strategy-docs/01_math_framework.md` §5「resolved 投资状态」行在册锚 =
  「`aggregate_economy(session.active_strategies).interest_cap_override`（kernel `cw_economy.cap_resolved_of_session`…）」——
  正本引用 session 实名字段，末阶段词表**不含九字段/七符号/四符号/relay 面**，预登记清单也不含 01_math_framework.md。
  中段普查（3.2/3.3 的「全仓」）是否覆盖正本树：§A 写了「两仓 + 正本树」，§B/3.3 未声明范围——
  正本树命中即便被 3.3 检出并标「正本批辖」，末阶段自己的普查也查不到它，清零判据形同虚设。
- **修正方向**：末阶段词表并入 §A 七符号 + §A′ 四符号 + 节点三字段 + §B 九字段 + relay/session_carrier；
  3.3 判据显式声明普查范围含正本树；正本清单补 01_math_framework.md §5 行。

---

## minor

### m1 计数词三处失准（值对标签错）

- 「选择族其余 **9 个**非 CwAction 选择入口」（design §1.1/§2.2）：直调 ABC + flow 实现，非 CwAction 返回的
  pick 入口 = **8**（EncounterPick/SupplyPick/MegastarPick/PartnerPick/PlannerPick 五类 + star_tome/wish_trial/
  box_card 裸 int×3）；9 是动作**子类型**数（含 PickInvest），不是入口数。「9 个非 CwAction 选择入口 + invest 对齐」
  按子类型口径应写「8 入口 + invest 换型 = 9 子类型」。
- 「10 pick handler——其中 **8 个** handle/lifecycle 双路径」（design §2.7/landing 3.5）：直调 `run_lifecycle` 分流，
  双路径实为 **9**（supply_node:145 亦有分流；仅 box_pick 单路径）。
- 「`game_state_of(session)` 旁路 **~250 处**」（design §1.1）：直调调用出现次数 src 152 + sr-od-test 139 = **291**。

### m2 design §0「状态：草案」与 README「对抗审中」不同步

迭代已进行至 r3 攻击，按 iteration-design §2.1 状态阶梯应为「对抗审中」。两处取一。

### m3 design §2.4 家族表漏 `enemy_difficulty` 行

details §B 有（`enemy_difficulty` → `gs.enemy_difficulty`，机械换源），design 家族级概要表「五镜像 + chosen_* +
last_streak + last_owned_equips」未含它（enemy_difficulty 不属五镜像封闭集）。同表也未见节点三字段（见 M8）。

### m4 cw_hp_policy 不在 §A′ 读者全集

`cw_hp_policy._node_t_of`/`decision_hp`（cw_hp_policy.py:93-119）经 `node_t_of(session,…)` 消费探针族——
§A′ 读者枚举未列（其消费随 §A 门删除而消亡，属现状陈述不完备而非缺口，建议加一行删除线注记防普查归类歧义）。

### m5 landing 3.5 文件面「operations/cw_reconcile.py」为幽灵路径

实文件 = `kernel/cw_reconcile.py`（glob 直调核实；operations/ 下无此文件）。按字面派工，kernel/cw_reconcile.py
的 ~10 处 `strategy_state_of` 与 reconcile 链 session 消费改形无文件面承载。修正为 kernel/cw_reconcile.py。

### m6 landing 正本清单「两篇『空 board stub』失真句」与实际文档文本不符

`docs/game/currency_war/currency_war_invest_env.md:33`/`currency_war_invest_strategy.md:34` 实文 =
「overlay 时 board 不可读」（陈述事实，非失真）；失真句「state.board 由调用方传空 stub」在 `flow.py:448` docstring
（直调核实仍在），归末阶段「代码 docstring 复核清零」兜底行。清单行描述应改指 flow.py docstring 或删该行。

### m7 README 进度行携带「用户四裁定」内容句，构成设计内容的第二抄本面

「r1 21 条已消解——含用户四裁定落地：刷新建议动作化/PickOption per-screen 子类型/HoldFrame 保留/识别防御缓存删除」——
裁定细节已在 design §0/§2.9（README 自己也声明「此处不设第二抄本」）。README 进度只留「已消解」计数即可。

### m8 「连续 None 的 stall 兜底归外循环防线」失实声明有两处同源副本未纳入修正面

design §2.2 只点名「ABC docstring……随批修正」；同句注释在 `cw_screen_prep.py:1551` 与 `:1718`（两决策循环各一），
landing 3.5 的修正范围同样只写 ABC docstring。随批一并清或并入「注释历史锚复核清零」行点名。

---

## 三核覆盖说明

### 核三（治本）：零发现 + 实际攻击过的面

- §1.2 归层「约定层」成立：构造/输入/输出三维度均是历史演化出的形状约定（对码：ABC 无参构造 + create_session/
  create_state 双口 + 入口 4-5 参，flow/README §2.2 契约形状即现状快照），无表示/语义层病灶被误判；
- §2 治本成立：终态契约四条把「生命周期/输入形状/输出形状」一次性立约，非在旧载体上打补丁；
  StrategySession 解散 + gs 正本换源与 session.md as-designed 的职责分离裁定（策略器状态归实现包）同向收敛；
- 跨件半问核过：本迭代承接 strategy-input-unification（同根问题的第 2 件被合并而非第 3 件补丁），
  统一观察架构批、库存域建模批以「明确不解决」显式划界，无逐件修形态；
- 宪法面：无新增 hp/战力决策消费（防御缓存删除是减面）；λ/数学判据层零触碰（kernel 纯函数零触碰成立，
  已对 flow.py→cw_events 调用形状核验）；「禁静默熵种子翻转」与 00_framework 数据通道纪律不冲突。

### 核一（无前提）实际攻击过的面（除上述发现外零发现的面）

- 终态四条 × 详设覆盖矩阵（§1 每症状 → §2 每机制 → details 逐节有落位）；
- 十二槽表逐槽对码（写者/消费入口/类型/域版本；选项类宿主 cw_events 循环导入禁约束与 #3/#4/#7/#8/#9 对码成立）；
- `_PAYLOAD_DOMAINS` 二元组扩展与 leave_screen 在册校验（:3156）自洽性；shop 两处既有清点对码成立
  （cw_game_state.py:2031 + cw_observation.py:2594）；
- `encounter_refreshed_in_visit` 完整契约对码（write_logic 常规归档、journal.md §6 豁免类辨析、
  megastar_clicked 同型先例、读侧 None 缺省）；supply/invest 重入型 vs encounter 同访问型的分屏形态与码面一致；
- 构造注入生命周期等价：引导漏斗每局 instantiate（cw_strategy_manager.py:73-79）、discard_stale_match_container
  保留、rng None→0 语义与现漏斗覆写式逐位等价、恢复局冷启动语义（新 gs + 新实例 = 现状全量重建）；
- buy_cards 防御裸构造改道的动机核实（cw_screen_buy_cards.py:798-814 现状裸构造确实绕过 journal 装配漏斗）；
- 回放/sim 面：「现行 sim 零策略构造」对码成立（sim 树仅 cw_replay 触策略）；`--run/--rounds` 面改形点 =
  cw_replay.py:88-112，旁证辖域申报与实态一致；
- 输出动作化语义等价：PickEvent∈CwAction、五 Pick 类非 CwAction、EncounterPick.refresh/SupplyPick.refresh/
  PickEvent.refresh_slots 三通道与三刷新动作一一对应、reason 保留、registry 五行换键名结构零改动、
  enhance_char_id 零消费者（可随型退役）、expert_invite 不走 decide（OpenBookcard docstring 在册）；
- 五镜像/chosen_*/enemy_difficulty 换源值等价性抽查（handler 双写点确认时序：cw_screen_invest_strategy.py:529-540
  确认成功后同点双写）；briefing 双字段非机械消费面（空门/跳过门/保位写/None 元素）与码面逐点对上
  （cw_entry_plane_intel.py:93-159、cw_screen_briefing.py:142-176、cw_screen_prep.py:1880-1941）；
- §A′ 值等价换宿主可行性（schedule_of/nodes_of_plane/node_t_of/r_* 全部 duck-typed getattr，同名四槽换宿主
  逐字节可行；sim 侧无探针字段触点，零改动申报成立）；探针读者全集普查（14 文件，声明面覆盖 13 + cw_hp_policy，见 m4）；
- §2.7 调用方迁移表的调用点计数对码（prep×2 = cw_screen_prep:1541/1708；buy_cards 循环 = :1089；
  pick handler 10 文件及其 decide 调用点全集）；REGISTERED_ACTORS 预登记两名的缺席面核实为真；
- 阶段可验收性试读（3.1 纯增量可绿、3.2 删除/重锚双线的对照单测可构造、3.6 清尾判据可达）——除 B1/B2 所列失配外成立；
- 落地依赖对码：execstate-dissolution 6/6 + 正本清零、turnstate-retirement 3/3 + 清零（README 直调），
  「均已收尾非前置」属实；unified-obs 3.4 文件面交集核对（除 M12 外成立）；
- 被取代迭代「继承并就地重述」抽查：十二槽表/三分语义/两路径语义/prep_obs 豁免/encounter_refreshed_in_visit
  契约均真实继承；路由清点语境规则一段继承失真（M2）。

### 核二（规范遵循）实际攻击过的面（除上述发现外零发现的面）

- iteration-design 四硬规则逐条（依据就地标注抽查 12 处关键主张；无过程叙事正文扫描——design/details/landing
  正文未见「第 N 轮/已改」类措辞，过程叙事集中在 README 进度行与 attack 报告属合法位）；全量同步复查 = 本报告
  M1/B2/m2 等即其卡点产出；
- 阶段小节七件齐（3.1-3.7 + 末阶段逐字段核对，七件俱全，含「通用工程门（引用，不复述）」形态）；
- 正本更新清单逐行锚真实性（清单 20 行逐行对正本树，除 m6 外锚均真实可解析；`flow/projection_contract.md`、
  `screens/op-layer.md`、`strategy-docs/13_pick_family.md` 等 12 处文件在树核实）；
- design↔details↔landing↔README 口径对账（契约成员计数 12/13、pick 族 9→10、Match 终形、journal 归属、
  §2.10 依赖表 vs landing 依赖行——除所列发现外一致）；
- AGENTS.md §8 注释规范（索引/槽位字段定义注释要求已在 landing 3.1 判据内申报）、§9 双层文档流
  （changes/ 引用寿命：正文对 chain-observation 批的承接引用属迭代内合法）、§10 测试规范（L1/L3 分层、
  普查对账表机制）、§11 提交卫生（通用工程门含逐文件点名与 show --stat 复核）。

---

## 附：关键直调计数备查（复核入口）

| 项 | 设计文口径 | 直调值 | 位置 |
|---|---|---|---|
| `game_state_of(` 调用 | ~250 处 | src 152 + sr-od-test 139 = 291 | Select-String 全量 |
| `strategy_state_of`+`state_of` 耦合 | ~100+ 处 | strategy_state_of 138 + impl state_of 数十处 | 同上 |
| shop.py session 消费 | ~68 处 | session token 76 / state_of 19 / game_state_of 1 | mandate_v1/shop.py |
| 非 CwAction 选择入口 | 9 | 8（入口）/9（子类型） | cw_strategy.py ABC + flow.py |
| handle/lifecycle 双路径 pick handler | 8 | 9 | run_lifecycle 分流逐文件 |
| 删除族字段 | 七符号（§A 词表） | 10 = 7 + 节点三字段（+§B last_owned_equips） | cw_strategy_session.py 类体 |
| session dataclass 字段 | 30+ | 31 | 同上 |
| REGISTERED_ACTORS | 补 2 名 | 现值无 CwScreenPlanner/CwScreenBoxPick/cw_loop_route_clear | cw_game_state.py:284 |
| `cw_decision_trace` 生产调用 | 零接线（design §2.8）/ 验收锚（landing 3.7） | 零调用点 | 全仓 grep |
| Match 定义位置 | 3.1 范围有、文件面无 | cw_strategy.py:190 | 直读 |
