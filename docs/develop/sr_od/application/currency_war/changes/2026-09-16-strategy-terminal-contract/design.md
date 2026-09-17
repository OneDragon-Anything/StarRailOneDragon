# 策略器终态契约 迭代设计（总纲）

## 0. 元信息

- 迭代目标（用户裁定 2026-09-16，会话裁定）：**一步到位直达终态**，取代「批 1 输入统一 → 批 2 构造注入」的分批方案；**输出侧一并统一**（选择族 → 动作 op）。
- 终态契约四条：
  1. **构造注入**：策略器每局冷建 `cls(gs, config)`——实例持有容器只读引用、按参注入配置、私有状态（StrategyState）与 rng；
  2. **决策入口零参**：12 个 `decide_<画面>()` 无形参，语义 = 「读自己（gs + 私有态）→ 发一个动作」；
  3. **StrategySession 解散**：逐字段按「谁产生/谁消费」归位（删除/正本换源/实例属性/Match），载体类退役；
  4. **输出统一单动作词表**：12 个入口返回类型统一 `-> CwAction`，无第二族、无 None。
- 状态：对抗审中
- 文档清单：[details/session-dissolution.md](details/session-dissolution.md)——输入承载契约重述（十二槽表/三分语义/per-visit 位/刷新链分屏形态）+ session 逐字段归位地图 + StrategyState 读者迁移 + game_state_of 退役。
- 承接出处：取代 `changes/2026-09-16-strategy-input-unification/`（其设计语义由本设计继承并就地重述，该目录不再落地）。

## 1. 问题与动机

### 1.1 现状症状（符号锚）

- **契约是中间态而非终态**：构造无参 + `create_session`/`create_state` 冷建双口 + 决策入口带参（备战/商店吃旁路、pick 族收 4–5 参）+ 跨步状态走独立载体 `StrategySession`（30+ 字段三类混装）。
- **session 三类性质混装**：识别层防御缓存（hp 四锚、hp_suspect、last_level_obs、star_pending_regression）与节点探针族（plane_node_table 等——**定性见 §2.4：真值源重锚，非缓存**）、节点类型双源（last_node_type/node_type_current）共存于识别侧；策略器状态（StrategyState）与框架设施（rng/performance）同宿。其中五镜像字段（session 实名 active_strategies/active_env/briefing_affixes/briefing_bosses/enemy_difficulty/selected_difficulty）与 chosen_*、streak 等在 gs 已有正本（fields.md §2.1/§3.2/§3.4），session 份是重复账。
- **StrategyState 隐性耦合 ~100+ 处**：`strategy_state_of(session)` 的 getattr 防御读散布 kernel、执行层（cw_loop/cw_screen_deploy/cw_screen_buy_cards）、遥测（局终快照链）——「框架只搬运引用不读内部」的设计声明名存实亡，执行层消费策略产出（选了什么阵容）这一真实依赖靠 getattr 遮着。
- **输出两态并存（精确口径）**：invest 的 `PickEvent` **已属 CwAction 族**（既有事实）；真正缺口 = 选择族其余 **8 个非 CwAction 选择入口**——`EncounterPick/SupplyPick/MegastarPick/PartnerPick/PlannerPick` 五类 + `decide_star_tome/decide_wish_trial/decide_box_card` 裸 `int`×3——返回「选了第几个」的选择结果而非动作 op，点哪里的翻译散在画面 op。
- **game_state_of(session) 旁路 291 处**（src 树实测，两仓普查为准）：容器须经 session 旁表解析，旁路是 session 存在的全部理由之一。

### 1.2 根因归层

**约定层**。契约从未按终态立约：生命周期（构造/冷建/状态宿主）、输入形状、输出形状三个维度各自历史演化。非语义层问题：每帧决策所需事实与产出无争议。

### 1.3 解决到哪 / 明确不解决

**解决**：终态契约四条（§0）一次落地；伴随 = gs 旁路退役、StrategyState 读者显式化、识别层防御缓存删除（§2.4-A，用户裁定）、路由清点/载荷容器化等输入面基建。

**明确不解决**：
- kernel 判据语义与纯函数签名（`decide_event` 族收 typed options 的形态不变，判据零触碰；签名补 gs 形参非判据变更）；
- 统一观察架构批的 decide() 输入视图口径与本批「实例持容器只读引用」的衔接（当前不冲突；该批落地时裁决视图化形态）；
- owned 正本迁 GameState 的库存域建模批（在册申报；本批 `last_owned_equips` 处置见 §2.4-B，武装箱打分降级为 gs.equips 现值 = 行为变化登记）；
- **识别失准路径的行为变化 = 用户裁定接受项**（§2.4-A 防御缓存删除：hp 新鲜度门、等级单调守卫、star 防抖、battle_wait killed 判定兜底改 gs.hp、`upcoming_types` journal 行降级、reconcile_hp 对账腿删除随锚退役；实机跑出识别失准 → 走识别优化批修识别本身，不回滚锚）；
- prep 屏编排域 sim 不可达现状（flow/README §2.3/§2.4 归因域限定不变）。

## 2. 方案

### 2.1 终态契约（构造注入 + 零参）

```python
strategy = MandateV1Strategy(gs, config)   # 每局冷建；gs = 当局容器单例；config 按参注入
action = strategy.decide_shop_action()     # 零参；读自己 → 发一个动作
```

- **构造**：`__init__(self, gs: GameState, config)`——`self.gs`（容器只读引用）、`self.config`、`self.state = StrategyState()`（实例属性）、`self.rng = random.Random(config.strategy_seed if config.strategy_seed is not None else 0)`（**None → 0 固定种子语义保持现状，禁静默翻转为熵种子**）。构造即唯一冷建口，`create_session`/`create_state` 退役。
- **实例不跨局**：局容器弃置 = 实例连带回收（现状引导漏斗即每局 instantiate）；异常路径残留容器弃置守卫（`discard_stale_match_container`）保留。
- **Match 容器终形**：`CurrencyWarMatch = {gs, strategy, performance}`——gs 为正身（策略持只读引用），performance 观测反馈归框架侧。
- **零参入口 12**：`decide_prep_screen()` / `decide_shop_action()` / `decide_invest_strategy()` / `decide_invest_env()` / `decide_supply()` / `decide_encounter()` / `decide_megastar()` / `decide_partner()` / `decide_planner()` / `decide_star_tome()` / `decide_wish_trial()` / `decide_box_card()`。契约成员 = 12 抽象 + 0 工厂。
- **实现位分布**：`decide_prep_screen` = `bridge.py` 覆写体（唯一实现）；`decide_shop_action` = `flow.py` 缺省实现（`mandate_v1/shop.py` 函数签名已 gs-first，但**函数体内 state_of/game_state_of 消费数十处随批改形**）；`decide_encounter` = `flow.py` 缺省体 + `bridge.py` 覆写体（生产在用）；其余 pick = `flow.py` 缺省实现。
- **兼容裁定**：干净断不留兼容壳（用户裁定 2026-09-16；依据 = 注册面封闭集 {mandate_v1}，flow/README §2.4）。第三方存量策略在新契约下不兼容 = 显式破坏申报。

### 2.2 输出统一（单一 `CwAction`，无例外）

- **基型事实**：商店四动作（BuyCard/LevelUp/RefreshShop/CloseShop）**已属 CwAction 族**（既有事实，非本批改动）；备战词表同理。真正缺口 = 选择族。
- **选择族动作化（8 个非 CwAction 选择入口 + invest 对齐）**：`PickOption(idx: int, reason: str = '')` 基类（CwAction 子类）+ per-screen 子类型——`PickEncounter` / `PickSupply` / `PickInvest`（invest 双入口共用，`PickEvent` 退役）/ `PickMegastar` / `PickPartner` / `PickPlanner` / `PickStarTome` / `PickWishTrial` / `PickBoxCard`。子类即执行注册表的分发键：**五条注册行换键名，注册表结构零改动**（用户裁定，方案 B）；invest 双入口/star_tome/wish_trial/box_card 现不走注册表（handler 自管确认链/直点），返回子类型后消费方式不变。**双词表处置**：`PICK_ACTION_TYPES`（cw_events）与 `CW_ACTION_TYPES` 随批收敛为 `CW_ACTION_TYPES` 单表（九 Pick 子类 + 三刷新动作 + HoldFrame 全量入册）。
- **刷新建议动作化（用户裁定）**：三条通道各自动作型——`RefreshNodeOptions()`（encounter 刷新建议，替代 `EncounterPick.refresh=True`）、`RefreshSupply()`（替代 `SupplyPick.refresh=True`）、`RefreshInvestCards(slots: tuple[int, ...], reason: str = '')`（替代 `PickEvent.refresh_slots` 逐卡槽位，画面三闸点击链留在 handler）。均为 CwAction 子类；`CW_ACTION_TYPES` 白名单与注册完备锁随批纳入（新类型全量入册，例外申报）。
- **备战 None 显式化**：`decide_prep_screen()` 空发射帧返回 `HoldFrame()`（CwAction 子类，语义 = 本帧无动作交回外循环重观察），None 退役。现状 None → `round_success(wait=1.0)` 直接交回，无连续 None 计数器（ABC docstring「stall 兜底归外循环防线」为失实声明，随批修正）；终态 = 决策环分支判等对象从 `result is None` 换 `isinstance(result, HoldFrame)`，`round_success(wait=1.0)` 路径逐字相同，round 日志文本随批更新，系统级 `stall_watch`/`NODE-DWELL` 哨兵对其透明。HoldFrame 不进 validate、不进 `_act_execute`、不查动作注册表、不写续段 token/动作记录（等待帧非动作）。`decide_shop_action()` 恒不 None 现状不变（CloseShop 终结）。
- **kernel 纯函数零触碰**：`decide_event` 族返回 Pick 族的现状不动，策略入口负责 Pick → CwAction 包装（数据组装职责归入口）。reason 字段随动作保留（判读面 parity）。
- **等价性主张**：输出载体变化但决策不变——四格/同帧对照逐格断言「同槽产物 → 同 idx/同刷新槽位/同动作语义」。

### 2.3 路由清点与离屏机制

- 挂点 = 外循环「识别产出后、`_dispatch_identity_screen` 调用前」单点，按属屏映射清 payload 槽。**路由屏取值规则**：命中且在映射内 = 该屏名，只清属屏 ≠ 它的槽；映射外建档屏 / 非身份臂语境 / 未识别 = 清全部十槽。映射单一源 = 扩展 `_PAYLOAD_DOMAINS` 为 `槽 → (属屏, route_clearable)` 二元组；`shop` 保留映射内 `route_clearable=False`（既有两处显式清点为唯一清点源）；`prep_obs` 不入映射（豁免）。
- 已 None 跳过（不占 write_seq 不落 journal）；清点写入口经 `leave_screen(槽, sig=…)`，sig family/mode 引用既有 CloseShop 腿清点行同一常量源、`actor='cw_loop_route_clear'`。
- 两路径语义：`stop_at_prep` 早退发生在挂点之前（早退轮不清点，早退屏非属屏无 decide 消费，清点顺延至 loop 下一次路由周期）；未知兜底在分发后循环尾（不绕行，未识别轮清全部十槽）。

### 2.4 StrategySession 解散地图

逐字段归位表与读者迁移契约见 [details/session-dissolution.md](details/session-dissolution.md)。家族级概要：

| session 字段族 | 去向 |
|---|---|
| **识别层防御缓存（hp 四锚、hp_suspect、last_level_obs、star_pending_regression、upcoming_types）** | **删**（用户裁定 2026-09-16：正常识别路径零变化，失准路径走识别优化批；`cw_hp_policy` 新鲜度门随之简化为 gs.hp 直读；star 防抖连带面与 `upcoming_types` journal 行降级申报见 details §A） |
| **节点探针族（plane_node_table、plane_node_table_plane、plane_lengths_seen、nodeseq_probe_anchor）** | **迁移重锚，不删**——schedule_of/nodes_of_plane 现役唯一真值源，下游 = cw_economy/cw_intention/cw_discipline_rules/cw_line_switch/cw_screen_battle_wait 结算锚/mandate_v1 全判据（shop/proof/encounter/levelup/budget/horizon 时基）；归 gs 非 Field 簿记组 `node_books`（读者全量重锚，chain-observation 批「另批承接消费点重接」的承接批 = 本批） |
| **节点类型双源（last_node_type、node_type_current）** | **重锚 `node_kind_of(gs)` 直读，不删**——现状双源并存：一半消费点已直读 gs 推导，另一半「识别值优先 + gs 兜底」换 gs 直读，删左移推断装配（details §A′） |
| 五镜像（session 实名含 briefing_affixes/briefing_bosses/enemy_difficulty 等，逐字段见 details §B）+ chosen_* + last_streak + last_owned_equips | gs 正本换源（详见 details §B；`last_owned_equips` 特例：删，武装箱打分（`flow.py::decide_box_card`）改 gs.equips 现值——行为变化登记 §1.3；载体中继 relay 随字段退役改直连） |
| `pending_round_outcomes` | **删**（只写不读零消费死面，写入端随批停止） |
| `prep_obs_frame` | `gs.prep_obs`（非 Field 容器字段） |
| `prep_frame_class` / `shop_frame_class` | gs 非 Field 两槽 `frame_class_prep`/`frame_class_shop`（直存直取；**不与 chain `mark_frame_obs` 单槽合并**——双消费者分析裁定不合槽，机制合并归统一观察架构批） |
| `rng` | 策略实例（构造即种子化，§2.1） |
| `performance` | Match 容器 |
| `strategy_state` | 策略实例属性 `self.state` |
| `StrategySession` 类本体 | 全字段归位后退役 |

### 2.5 StrategyState 外部读者显式化

- **执行层/流程层读者**（cw_loop 预算闸、cw_screen_deploy 选人、cw_screen_buy_cards 记账等）：改读 `ctx.cw_match.strategy.state` 具名字段——隐性 getattr 变显式声明依赖。
- **kernel 判据函数读者**：参数注入——kernel 函数现状多已有 target_comp/ist 形参位，session getattr 仅为 fallback；调用方（ops 层）从 `match.strategy.state` 取值注入，kernel 保持纯函数。
- **遥测局终快照**：读 `match.strategy.state` 快照链单点换源。
- 「黑盒引用/框架不读内部」设计声明正式退役（flow/README §2.5 随正本批改写）。
- 迁移用**全仓 grep 普查对账表**机制（词表 = `strategy_state_of`/`state_of`/`strategy_state`，含注释形态；两仓逐仓；排除 `changes/`/`sources/`/`proofs/`），承载桶六类（参数注入已有位 / 执行层显式读 / **kernel 新增 state 形参** / 遥测换源 / impl 内部 / 正本批辖——详见 details §3）。

### 2.6 game_state_of(session) 访问口退役

- 容器引用持有点 = 策略实例 `self.gs` + Match；`game_state_of(session)` 旁口随 session 退役。
- 迁移同普查对账机制（`game_state_of` 一词，291 处两仓合计）：桶 = 调用方已有 gs 形参直用 / 改经 `match.gs` / kernel 纯函数已收 gs 不动 / 正本批辖。
- **journal 装配重锚**：journal 装配唯一锚 = `game_state_of` 建立路径，随旁口退役悬空——装配点迁至新建立路径（引导漏斗 gs 构造点，3.5 阶段），`game_state/journal.md` 正本随批更新。

### 2.7 调用方迁移契约

| 调用面 | 改动 |
|---|---|
| 引导漏斗（`cw_strategy_manager.py` 容器建立函数） | `cls(gs, config)` 构造；journal 装配重锚（§2.6）；`create_session` 调用链退役 |
| 12 入口调用点（prep×2、buy_cards 循环、10 pick handler——其中 9 个 handle/lifecycle 双路径、box_pick 单路径） | 写槽 → `strategy.decide_X()` 零参；返回 CwAction 按类型分发（五个 Pick 子类型经既有注册表换键名；invest/wish_trial/bookcard/box_pick 的 handler 自管消费链读 `.idx`——`_card_point` 翻译留在 handler，坐标不出策略层）；**buy_cards 防御路径裸 Match 构造退役**——改经引导漏斗统一建立容器（新 Match 形含 gs，裸构造无容器来源），`run_operation` 直跑场景同漏斗 |
| kernel/执行层/遥测 StrategyState 读者 | §2.5 迁移 |
| game_state_of 旁口 | §2.6 退役 |
| sim / 回放 | **现行 sim 零策略构造**（引擎自有 stream rng），sim 侧零改动核对申报；回放现行 `--run/--rounds` 面构造随批（`create_session` 退役） |
| 测试仓 | 契约形状锁（12 零参 + 构造形态 + 输出词表）、单帧锁构造（`cls(gs, cfg)` → 调方法）、handler 锁、普查对账表 |

### 2.8 验证

- **行为变化申报（scoped 零行为）**：①正常识别路径 = 每帧同输入值、同选择 idx、同动作语义（零变化）；②识别失准路径 = 防御缓存删除后的表现变化（**用户裁定接受项**，§1.3 登记）；③装备账完整度降级（`last_owned_equips` 删）= 行为变化登记。载体变化（动作词表/构造形态）为可判读形态差。
- **主凭据**：①decide 层四格对照（encounter 首调/累计闸命中/刷新重决策/重入重走首调；invest 拆分同帧对照；其余入口同槽产物 → 同动作）；②handler 级行为锁（逐 handler 剧本 + 写槽-决策单源 + encounter 四格）；③StrategyState 迁移对账表 + game_state_of 退役对账表 + 锚删除普查表零未承载项；④L1 + L3。
- **旁证**：回放（现行 `--run` 面）改前/改后逐轮 plan 串文本 diff——辖域 = shop 驱动器路径，对 pick 链/session 解散结构性零覆盖（显式申报）。
- **终验**：实机一局 smoke（**锚 = journal 动作行**——journal 状态流水为现行唯一在产决策记录载体；`cw_decision_trace` 模块零接线不引用；与改前同难度局对照）；候实机窗口，不阻代码收口、阻迭代收尾。
- **可观测性申报**：journal 行量/write_seq 位移/快照新域行/动作词表形态变化/`ChannelSig.group_id` 位移；路由清点每槽每「在屏→离屏」转换至多一行 + 交回重入型识别瞬态轮多对行（形态预期）；HoldFrame 帧以 round 日志文本可见（不写容器、决策迹模块未接线不入册）。

### 2.9 关键取舍

- **一步到位 vs 分批**：用户裁定一步到位。放弃的安全网价值以「全阶段四格对照 + 普查对账表零未承载」补偿。
- **输出统一并入**：用户裁定。`PickOption` 采用 per-screen 子类型（用户裁定方案 B）：子类即执行注册表分发键，注册结构零改动，批 4 收编面维持排期；单类型 + 注册表改造为备选（词表纯度 vs 新对抗面）。
- **`self.state` 公开属性 vs 只读门面**：公开属性——执行层消费策略产出是真实依赖，显式声明优于访问器仪式；写仍归策略器独占。
- **HoldFrame 保留**（用户裁定）：类型纯度 + 决策迹等待帧可见；成本 = 分支判等对象替换（无计数器改造成本，更正后事实）。
- **识别防御缓存删除**（用户裁定）：防线是「没建的识别优化的替身」——失准暴露后修识别本身，符合失败可见哲学。
- **kernel 纯函数零触碰**：判据层输入来源由调用方组装的纪律不变。
- **rng None → 0 固定种子保持**：禁静默熵种子翻转。

### 2.10 落地依赖与冲突面

- unified-obs-reconcile 3.4 落码收（`cw_screen_prep.py`/`cw_screen_buy_cards.py` 相交；传递链与其 3.3 候窗实机验证期——开工前协商解耦或排候窗后，本设计不预设结果）；其 3.4 交面清单以其 landing 3.4 文件面为准全列。
- execstate-dissolution / turnstate-retirement 均已收尾非前置。
- 本批正本更新批须 unified-obs 正本更新批先收（flow/README、fields.md 文档面顺序）。

## 3. 契约扩员附记（普查迁移批 2；零参入口 12 → 15）

> 本节为迭代内附记，寿命 = 本迭代；正本（flow/README §2.2）随正本更新批收敛。

- **扩员动因** = 策略侧内容回流普查对抗裁决 F-overlay-01/02/03（三条均 CONFIRMED，裁决过程档 = `.debug/temp/audit-sweep/adjudication-1.md` §2，寿命随迭代）：命运卜者强化三选一 / 专家邀请函选卡 / 选择装备三选一三屏的选卡判据原住画面 handler（选择打分 / 第二实现 / 意向消费错位三类全中），修正落点 = 判据迁 kernel 新纯函数 + handler 改「写槽 → 零参 decide」，契约面需为三屏补零参入口。走 flow/README §2.2「新事件面优先归并进既有 pick 接口或走契约改版」两路预授权中的**契约改版路**（三屏各有独立 payload 槽与判据域，归并进既有九口会错位）。
- **扩员内容**：新增三个零参入口 `decide_fortune()`（候选 = `gs.fortune_opts` OCR 卡文）/ `decide_expert_invite()`（候选 = `gs.expert_invite` 弹窗载体 = 卡羁绊解析 + 板面计数；idx = -1 表现金为王，PickOption idx 值域扩展申报）/ `decide_equip_pick()`（候选 = `gs.equip_pick_opts` OCR 卡名带）；抽象 12 → 15。词表新增 per-screen 子类型 `PickFortune` / `PickExpertInvite` / `PickEquip`，入 `CW_ACTION_TYPES` + `PICK_ACTION_TYPES`；三屏确认链/直点均 handler 自管消费，与 StarTome/WishTrial/BoxCard 同豁免类（注册完备锁豁免集随迁）。
- **判据落点**：fortune 关键词权重表 → `cw_events.decide_fortune`；expert 三级语义（在场计数 → 同线 → 现金为王）→ `cw_events.choose_expert_index` 整函数平移；equip key_fit+100 / 泛用关键词+1.0 → `cw_equip_value.decide_equip_overlay_pick`（收 `locked_comp` 参数，意向读迁策略入口自 `self.state` 注入——§2.5 参数注入桶）。equip 与 `pick_equipment` 序数分档语义不可合一（子串命中制 vs 精确名制、泛用关键词腿 vs 名键先验），新立函数不并轨，合一属轻微行为变化另裁。
- **口径** = ABC 返回注解沿用子类型联合先例（§2.2 输出统一）；验收结论 B 条已定调**行为保持优先**：三件判据原样迁移（当前行为逐位复刻），禁顺带改策略语义。已知分叉单列挂账：expert_invite 实码（在场浓度版）与 E9 在案规格（目标线优先版，13_pick_family.md §2）分叉 = 独立行为变更挂账（迁移保持实码行为，规格切换另批裁定）。payload 三新槽入 `_PAYLOAD_DOMAINS` 路由清点 + `DEFAULT_GS_SCHEMA`。
