# sim 推演内核形态 迭代设计（总纲）

## 0. 元信息

- 迭代目标：T-161——T-145 判据 1 主体（sim 内部模型切换到 GameState 容器本体）受阻的根源设计问题定稿：sim 推演内核以什么正式形态存在。
- 承接出处：T-145 报告 §5-1 停手申报（三点冲突证据+三候选）+ T-145 验收 r1 §七建议 2（范围增补三项）+ 账本 T-161 附注（用户裁定 2026-09-12：范围收窄为「sim 域内部模型正式化方案」）。
- 状态：草案
- 文档清单：无详设（单文档方案，§2 即完整设计）。
- landing.md 不在本批：落地批候对抗审收敛后由编排者另立。
- 已裁边界（本设计不得越）：①策略域前瞻搜索删除已交付（T-163，策略回归纯规则路线）——策略域零 simulate 前瞻消费；本设计不定策略域消费，只定 sim 整局推进的内核载体；②sim 定位 = 环境模拟器跑真实策略测效果（runner 批 / A-B 对照 / 整局驱动）；③方案 B（扩容器记录模型）路线作废——容器按实机真值建模的纯度保持。

## 1. 问题与动机

### 1.1 现状症状

T-145 实施实证：sim 引擎的内部真值模型（旧类 `CwWorkFrame`，现居 `kernel/cw_vocab.py`）无法无损切换到 `GameState` 容器。容器记录模型按设计明文不承载 sim 机制必需的三样表示（依据：T-145 报告 §5-1，三点均经验收 r1 §二逐点亲验属实）：

1. **商店牌购买槽位 x**：sim 买牌按 x 下架（`cw_vocab.py` simulate 买牌分支 `s.shop = [c for c in s.shop if c.x != action.card.x]`）；容器 `ShopCard` 无 x（`shop_card_to_container` 只映射 name/faction/cost/star/cost_source，docstring 明文「x/merge_preview……容器不入存储」，cw_game_state.py:851-864）。
2. **备战件 position_pref**：`BenchView` 往返（`bench_slots_to_legacy`，cw_game_state.py:1179-1213）重建 BenchChar 不带 position_pref（缺省 'back'，cw_exec_state.py:419）——前排偏好件经容器一圈静默变后排，部署排路由键被改写。
3. **动作拒绝回滚**：`simulate` 为 copy-on-write（拒绝返回 `state.copy()` 原帧续用，cw_vocab.py:906-921/:949）；容器为冻结帧替换单例，无帧级复制/回滚原语——`full_state_snapshot`/`restore_state_snapshot` 往返丢字段（§2.5），不可用作回滚。

### 1.2 根因归层

**表示层**。容器记录模型与 sim 机制模型是设计上刻意不同的两套表示：记录模型 = 「当前仍为真的局内已知事实快照」，按实机真值箱占席，不采 sim「无箱实体」的内部口径约定（设计明文：cw_game_state.py 模块头 :31-34、:430 同口径）；机制模型 = 环境真值工作态，须完整承载「试动作-反悔」机制所需的表示（x 槽位/排偏好/帧级回滚）。三点冲突是**表示边界**而非实现缺陷（T-145 验收 r1 §二复核成立）。原判据「sim 切换到容器本体」的隐含假设——两者同物异名、可无损替换——不成立。

### 1.3 解决到哪 / 明确不解决

- **解决到哪**：定稿推演内核的正式形态——正式类型与命名（§2.1）、居所域（§2.2）、与容器记录模型的边界契约含全字段映射对账表（§2.3）、动作账本宿主（§2.4）、快照与回滚原语边界（§2.5）、旧类退役路径（§2.6）、行为零漂移门（§2.7）。
- **明确不解决**：
  - 策略域消费面：策略域 simulate 前瞻消费点已随 T-163 删除清零（策略纯规则，决策零模拟试探；sim 链唯一活调用 = engine_p1），本设计零涉及；
  - 容器记录模型自身演进（state 链各批辖域）；
  - T-120 端口协议（cw_game_ports）批 1+ 的注入形态——本设计只保证其帧型引用在正名后有合法落点（§2.2 理由 3）；
  - 实机 `session.last_state` 链的删除排期——挂既有迁移波（cw_intention.py:2377-2378 申报面），本设计只声明终态与承接指针（§2.6-5）。

## 2. 方案

### 2.1 推演内核的正式类型与命名（问①）

**推演内核 = 一套 kernel 机制面**，由三部分构成（现状代码事实收编，无新增机制）：

| 构件 | 现名 | 依据 |
|---|---|---|
| 局面帧型 | `CwWorkFrame`（cw_vocab.py:104-256，35 字段+方法） | sim 引擎整局推进的状态载体（engine_p1/engine_p2/runner 全程驱动） |
| 单步动作转移（纯函数，copy-on-write） | `simulate(state, action) -> 新帧`（cw_vocab.py:906-1121） | 消费位 = sim 引擎逐步推进 / 假游戏环境动作语义投影 / 规则实现等价性验证（锁 M1；cw_vocab.py:1-28 模块头申报） |
| 实机跟踪转移 | `mutate_bench_deployed`（cw_vocab.py:1124-1240） | 运行时执行点同步 tracked 账；docstring 明文「转移规则与 simulate 一致（单一源，避双源漂移）」 |

外加机制 helper 套件（`_resolve_comp_transaction`/`_apply_comp_transaction`/`_tx_state_view`/`_log_action`/`bench_clear`/`deployed_clear`/`_card_to_bench`/`_*_clear_by_identity`/`_remove_by_identity`），与两转移函数共居。

**正名裁决：`CwWorkFrame` → `CwSimFrame`。**

- 命名语义 = 「sim 模拟环境的局面帧」，与 sim 包家族（cw_sim_invest/cw_sim_piggy）命名同构；`Frame` 后缀延续既有术语系（决策帧/工作帧/黑板帧）。
- 正名语义 = **类本体收编为推演内核正式类型**：字段集、机制行为、缺省值零变化（行为零漂移门见 §2.7）；退役的是名字与含混身份，不是类本体（§2.6）。
- 腾名化石条款作废：cw_vocab.py 模块头「『CwWorkFrame』名让渡给统一容器(kernel/cw_game_state.CwWorkFrame)」为历史规划残留——容器已正名 `GameState` 并兑现（fields.md:13「GameState(正名兑现;原暂名 BoardState)」；r5-migration-plan.md:2-3 正名兑现注），无让渡对象；`CwWorkFrame` 名随本正名退役删除，不授予任何现存类型。模块头随正名批重写为终态声明。
- 双 ShopCard 并存合法化修正：cw_game_state.py:846「旧容器版……随 W8 CwWorkFrame 本体退役波消亡」措辞与本裁决冲突——帧版 ShopCard（带 x/merge_preview）是观测/执行域卡（OCR 产物带点击坐标，黑板帧链自持 x；cw_game_state.py:867-901 shop_cards_to_legacy docstring）兼 sim 机制卡，**随推演内核收编存续**；两类型并存为长期形态，转换只经 W5 两个映射单一源（`shop_card_to_container`/`shop_cards_to_legacy`），该措辞随正名批修正。

### 2.2 居所域（问②）

**裁决：kernel 留守（`kernel/cw_vocab.py`），不迁 sim 域。** 理由四条：

1. **动作语义单一源耦合（决定性）**：`simulate`（环境转移）与 `mutate_bench_deployed`（实机跟踪转移）共居一套转移规则与 helper（`_resolve_comp_transaction` 被 simulate 与 mutate 经 `_tx_state_view` 共用；cw_vocab.py:1128-1134 单一源申报）。这是「环境模拟器跑真实策略」可信度的根基——M1 等价锁验证的正是这套动作语义在模拟环境与实机跟踪两侧同源。移居 sim/ 则 kernel 侧两条生产消费链须反向 import sim，制造 kernel→sim 环或拆双源，两者皆不可接受：①`operations/cw_op/cw_shop_action_ops.py:537`/:618（实机 ops 运行时跟踪 tracked 账，直调 mutate）；②`cw_game_state.apply_shop_merge_leg`（:1657 经 `mutate_bench_deployed_local` :1671-1677 惰性转发消费 mutate——容器升星腿，M1 锁与 simulate 输出等价对拍的容器侧半边；`apply_shop_action_logic` 本体零 mutate 消费，简单腿走自己的逐域 write_logic :1509-1511 起）。
2. **依赖方向既有事实**：sim → kernel 单向（engine_p1.py:65-78 从 cw_vocab import 帧/动作/simulate）；kernel 从不 import sim。移居翻转方向，波及面全仓。
3. **过渡期实机链同型**：帧型当前是实机观察工作载体（`read_game_state` 产帧，`session.last_state = st` 写点 cw_screen_prep.py:535/:756、cw_op_buy_cards.py:935，T-146 装配源迁移在飞）。移居 sim/ 会把在飞迁移面拖进 sim 依赖。
4. **包语义边界**：sim/ 包 = 模拟器（引擎/采样/池/校准/批量/AB/记账/重放）；推演内核是它驱动的机制件，与 kernel 既有机制层（cw_economy/cw_merge_simulate/cw_bond_equips/cw_exec_state 的槽位模型与常量）同层同源——帧的构成类型（BenchChar）与规则常量本就住 kernel。

不拆新模块：正名后 `CwSimFrame` 仍居 cw_vocab.py。候裁9 已定谳本文件为帧定居所（T-7 收口）；拆文件的收益（文件语义单一）不抵第二轮 import 扫描与 shim 生命周期成本——机制面边界由 §2.3 契约承载（文档边界），不依赖文件边界。cw_vocab.py 模块头随正名批改写，声明本文件 = 动作契约词汇 + 推演内核机制面。

### 2.3 与容器记录模型的边界契约（问③）

#### 2.3.1 表示分界原则

- **容器 `GameState`** = 实机真值记录模型：单例、每局新建、观察/逻辑两源直写、frozen Field 帧替换（cw_game_state.py:1-29 模块头）；只记录实机会产生的已知事实。
- **内核帧 `CwSimFrame`** = 环境真值工作态：完美真值（无失读态）、机制完整表示（含 x 槽位/排偏好/动作账）、值语义可变（copy-on-write 试探）。
- 两者是**平行表示，不是镜像**，不存在「谁本体化谁」；原判据的「本体化」提法随本设计作废。

#### 2.3.2 同步机制（单向，双禁令，单一源）

1. **内核帧 → 容器**：唯一通道 = `feed_sim_truth`（= `synthesize_from_game_state` 写入实现，observation 渠道，evidence 恒带 `sim:synthesized`，actor 签名 `synthesize_from_game_state` mode='synthesized'；cw_game_state.py:2758-2934 方向契约亲读）。引擎保持「决策消费点前喂入」节奏（engine_p1 既有接线）。域覆盖增删只改该函数单一源，禁引擎侧散落第二写点。
2. **容器 → 内核帧：禁止**。内核帧的真值来源 = 环境剧本构造（开局采样/重放档案/Δ池/段落进场态），不是容器；回读会把记录模型的缺读态（None/carried）污染机制真值。策略域读容器、引擎喂容器——信息流单向成环：帧 →（feed）→ 容器 →（读口）→ 策略 →（动作）→ 帧。禁令辖的是**把容器值回写进帧字段**；策略侧与引擎决策谓词经容器读口读为合法（§2.3.4 单向环与双 ShopCard 对齐块；engine_p1 容器触点全部为喂后读，:716-723/:1513-1517/:1677-1688/:1814-1834）。现树无容器值回写帧字段的通道（审计口径：engine_p2.build_state 帧源 = P2ReplayEntry 档案构造，engine_p2.py:102-104；cw_replay 在容器上直接决策、零帧重建，模块 docstring :9-12；runner.synthesize_snapshot 方向 = 帧→Snapshot）。
3. **不入同步面（内核独占表示，容器设计不入）**：`ShopCard.x`、`merge_preview`、bench 侧 `position_pref`、`action_log`（§2.4）、帧本体 copy-on-write 语义。
4. **实机观测保真位不入同步面**：`hp_readable`/`hp_trusted`/`gold_readable`/`board_readable`/`level_readable`/`enemy_difficulty_live` 是实机观测域字段；sim 帧恒真读（缺省 True 即 sim 恒真读帧约定，cw_vocab.py:123/:142 字段注）。容器侧质量语义由 Field.source/evidence/渠道签名承载，不与这些位互映射。
5. **无 session 投影面**：`scalar_projection_state`（cw_game_state.py:3208-3271）语义契约原样保留（ADR-0598 结构性豁免不扩修），不属推演内核消费面。

#### 2.3.3 全字段映射对账表（范围增补①）

判定口径：**A 同域无损** / **B 有损·设计边界**（容器刻意不入的表示——机制必需表示留内核，或原值经派生替换/边缘语义归一）/ **C 容器无域·实机观测或策略域字段**（不入同步面）/ **D 容器有域·喂入口现不写**（现状申报，增补归 feed 单一源）/ **E 退役面**。分类计数：A 17 / B 4 / C 8 / D 4 / E 2，合计 35。喂入口覆盖集依据 = synthesize_from_game_state 写入面亲读（cw_game_state.py:2758-2905）。

| # | CwSimFrame 字段 | 容器表示 | 判定 | 备注（依据） |
|---|---|---|---|---|
| 1 | gold | `bs.gold` | A | observe 直写 |
| 2 | round_num | `node.round_num`（NodeKey） | A | |
| 3 | plane | `node.plane`（NodeKey） | A | |
| 4 | node_type | `node.kind` | A | None 帧不写假值：容器无现值时不写 node；已有现值时写 kind_inherited 继承帧（plane/round 取帧值，:2789-2806） |
| 5 | level | `bs.level` | A | |
| 6 | xp_progress | `bs.xp` | A | tuple 直写 |
| 7 | streak | `bs.streak` | A | |
| 8 | hp | `bs.hp` | A | |
| 9 | deploy_cap | `bs.deploy_cap` | A | |
| 10 | back_max | `bs.back_layout` | A | W6 波3 动态真值修正（:3081-3085） |
| 11 | board | `bs.board` | A | |
| 12 | plane_bosses | `bs.plane_bosses` | A | |
| 13 | enemy_affixes | `bs.enemy_affixes` | A | |
| 14 | active_env | `bs.active_env` | A | |
| 15 | equips | `bs.equips` | A | |
| 16 | active_strategies | `bs.active_strategies` | A | |
| 17 | refresh_probs | `bs.shop.refresh_probs`（ShopPayload） | A | 已入 ShopPayload（T-145 验收定性） |
| 18 | deployed | `front_row`+`back_row`（Unit 行） | **B** | 槽位/星级/装备无损，回程 position_pref 按排还原（`unit_rows_to_deployed` :1241）；faction 原值不保（容器刻意不入，注册表派生替换，§3.2.3 同源）；pref≠row 短暂不一致形态被归一（`front_count_of` :3098-3103 口径注，边缘语义损耗申报） |
| 19 | bench | `bs.bench`（BenchView） | **B** | **position_pref 丢**（Unit 无域，重建走缺省 'back'）——机制必需表示留内核的核心实例；faction 同上派生；is_item_slot 经 `kind='supply_box'` **保真**（:2861-2864 写 / :1194-1199 读，勘误见 §2.5） |
| 20 | shop | `bs.shop`（ShopPayload.cards） | **B** | 五记录字段透传无损；**x/merge_preview 容器不入**（设计明文 :851-864）——sim 买牌下架按 x，x 留内核 |
| 21 | action_log | 无容器域 | **B** | 动作账宿主 = 帧自身（§2.4） |
| 22 | front_max | 无域（常量镜像） | C | 恒 4，非观察事实；容器常量 `DEPLOYED_FRONT_CAPACITY` 同值（:3113-3125 max_units_of 同式） |
| 23 | level_readable | 无域（Field.source 近似，不映射） | C | 实机观测保真位；sim 恒 True |
| 24 | gold_readable | 同上 | C | |
| 25 | board_readable | 同上 | C | |
| 26 | hp_readable | 同上 | C | |
| 27 | hp_trusted | 同上 | C | |
| 28 | enemy_difficulty_live | 无域 | C | 实机观测保真位 |
| 29 | board_next_tier | 无容器域 | C | 实机 OCR 域（左面板 X/Y 的 Y），sim 不建模，喂入口不写 |
| 30 | dual_track_phase | 无域 | **E** | ADR-0209 双轨期；W6 消费切换时随 last_state 链退役（字段注 cw_vocab.py:197），不迁容器 |
| 31 | focus_factions | 无域（真家 = StrategyState） | **E** | 同上（cw_vocab.py:198） |
| 32 | enemy_difficulty | `bs.enemy_difficulty` | **D** | 容器有域；喂入口现不写（现状申报）；若 sim 决策消费需该域，域覆盖增补 = 改 synthesize 单一源，不属本形态批 |
| 33 | level_up_cost | `bs.level_up_cost` | **D** | 同上（桥面 `board_state_bridge` :3194 补写，喂入口不写） |
| 34 | shop_refresh_cost | `bs.shop_refresh_cost` | **D** | 同上；sim 帧恒基价常量（cw_vocab.py:131 字段注） |
| 35 | selected_difficulty | `bs.selected_difficulty` | **D** | 同上（桥面 :3200 补写） |

**容器独有域（反向汇总一行）**：node_path/game_mode/refresh_counters(3)/node_screen_refresh(4)/consumables/spheres/substate/event_overlay/event_choices(chosen_×10)/settlement/hp_floor_triggered/prev_screen/current_screen/top_bar_raw/node_ord/receipts/match_final/encounter/supply = 容器记录模型扩面域，sim 帧不建模（环境剧本不产这些事实，设计事实非缺陷）；encounter/supply 两 payload 域在喂入口恒离屏（结构事实，:2896-2901）。

#### 2.3.4 与策略域的关系

**策略域 = 容器读、零模拟试探（T-163 交付后现状）。**

- 策略为纯规则路线（用户裁定 2026-09-12；cw_vocab.py:10-16 模块头同口径申报）：规则直接产出动作，决策零模拟试探。策略域 simulate 前瞻消费点（mandate_v1 shop/sell/flow 等 + cw_shop_action_ops:419 project）已随 T-163 删除清零——现树 `simulate` 唯一活调用 = sim 引擎（engine_p1 `_simulate_state`），全仓 grep 亲验。
- 策略在 sim 局中的真相来源 = 容器读口（引擎于决策消费点前 `feed_sim_truth` 喂入，§2.3.2）；策略产出动作交引擎经 `simulate` 推进——信息流与 §2.3.2 单向环一致，策略域对内核帧零直读零直写。
- 策略↔引擎缝 = 既有双 ShopCard 对齐块（决策核发射容器牌无 x / 引擎真值帧带 x 槽位，按 (name,star) 对齐，engine_p1 显式申报面 + 幻影再买计数），本设计零改动。
- `simulate` 消费面终态 = sim 引擎整局推进 / 假游戏环境动作语义投影 / 规则实现等价性验证（锁 M1），策略域与实机操作链零消费（cw_vocab.py:10-16）。

### 2.4 动作账本宿主（问⑤ / 范围增补②）

**裁决：`action_log` 宿主 = 内核帧自身（正名后 `CwSimFrame.action_log`），不设容器域。**

- C6 冻结 invariant「拒绝记录进账本」的账本就是本字段（契约包 C1；`_log_action` docstring cw_vocab.py:631-633）；拒绝记录随帧存留、随 `copy()` 回滚——账本语义与帧生命周期绑定，天然宿主只有帧。
- 容器 `receipts` 域语义 = **实机 op 执行回执**（发出即簿记，非验证；滚动窗 8；note_action_receipt 唯一写点，cw_game_state.py:943-1008）——记录「实机执行层发出了什么」，与推演内核动作账（机制判定 applied/rejected + reason）是两个语义世界的两本账，**不是「一份账缺宿主」的双账面问题**。方案 B 作废后，容器侧不存在 action_log 宿主缺位：动作账的宿主从来只有帧。
- **禁互写**：sim 侧不写 receipts（模拟动作不得污染实机执行回执）；容器侧不承载 sim 拒绝记录。
- sim 账本的可见性走既有转录面：sim ledger 的 actions 序列化（action_log 三消费面注：策略不读 / 遥测经 sim ledger 间接可见 / sim 代理 = 字段自身，cw_vocab.py:200-205）+ SimResult。若未来判读面需要 sim 拒绝记录进统一 state 流水，另立设计件裁渠道语义，不属本形态。

### 2.5 快照与回滚原语（范围增补③）

**容器快照丢字段清单**（`full_state_snapshot` → `restore_state_snapshot` 往返，:2189-2231/:2937-3007；`_json_safe` = dataclasses.asdict :1300-1310）：

1. bench 侧 `BenchChar.position_pref` 丢——Unit 无域，恢复重建走缺省 'back'，前排偏好件静默变后排。
2. `BenchChar.faction` 原值不保——恢复经注册表派生（`bench_slots_to_legacy` :1204-1209）；'?' OCR 未知态与注册表外形态的原值丢失。
3. shop 卡 `x`/`merge_preview` 不在快照（设计不入存储）。
4. 帧级字段全集（action_log / 保真位族）不在快照（无容器域）。
5. **勘误申报（对 T-145 验收 r1 §二第 3 点）**：`is_item_slot` **不丢**——`BenchSlot.kind='supply_box'` 四点同链保真（synthesize :2861-2864 写 → `_json_safe` asdict 保 kind → restore `_bench_view` :2961-2971 重建 kind → `bench_slots_to_legacy` :1194-1199 还原 is_item_slot=True）。真正丢的是 position_pref（bench 侧）与 faction 原值。

**设计效力两条**：

- 容器快照仅服务离线判读面（T-98 回放 / Δ池 journal 切源），**禁用作内核回滚**。
- 内核回滚唯一原语 = `CwSimFrame.copy()` 深拷贝（现 `CwWorkFrame.copy()` = deepcopy，cw_vocab.py:222-223；simulate 拒绝路径返回 `state.copy()` 原帧续用）。copy-on-write 是推演内核的机制契约，容器侧不补快照/回滚原语（方案 B 作废的必然结论）。

### 2.6 旧类退役路径（问④）

**「退役」语义 = 正名收编，不是物理删除。** 三件事：

1. **名字退役**：全仓改名扫 `CwWorkFrame` → `CwSimFrame`（src + 测试仓；先例 = W8 BoardState→GameState 机械大扫，src 153 处/32 文件+测试仓 187 处，r5-migration-plan.md:150-152）。**不留别名/子类/兼容壳**——名字死亡即死，防双名长尾；扫后全仓 `CwWorkFrame` 零命中入哨兵锁。
2. **职责收敛**：类本体唯一存续职责 = 推演内核（§2.1 套件）。其余历史役逐批由既有迁移收走，本设计不排期只声明终态：实机装配读 → 容器（T-146 在飞）；`last_state` 写点（cw_screen_prep.py:535/:756、cw_op_buy_cards.py:935）与 OCR 填帧链 → 容器观察写通道（挂既有 last_state 链退役波，cw_intention.py:2377-2403 申报面）。**过渡期声明**：退役波落地前，实机链消费点持有 `CwSimFrame` 注解是正式类型对既有消费面的收编延续，不是假名暂住；过渡期上限 = last_state 链退役波（指针 cw_intention.py:2377-2378，无排期锚——该波若拖延，过渡期以月计，故不在设计层作时限断言）。正名批重写模块头时显式声明这一过渡双职责与退役指针，防「按名索骥」误判 sim 泄漏进实机（或反向在 sim 批改实机链行为）、防按「CwSimFrame = sim 专用」立新哨兵误伤在飞实机过渡链。不为过渡期保留旧名。
3. **账债关闭**：r5-migration-plan W8「物理删除」与 T-145 依据③的「删除时点 = W8」字样正式作废（T-145 验收 r1 建议 3 勘误方向的终局化）——机制本体**永不物理删除**，删除债转化为「正名 + 契约 + 职责收敛」，由本设计一次性关闭。

**顺序约束（编排者排期输入）**：正名落地批的前置 = T-146 done（装配源迁移在飞改同一批引用面，防同文件交叉——交叉先例 = T-146/T-163 交叉裁决，账本 note 2026-09-13T01:00:13）。T-163 已交付（策略域 simulate 消费清零落库），其扫面缩小已兑现，不再构成前置。

**文档面修正锚（随正名批）**：cw_vocab.py 模块头重写（腾名化石作废 + 终态消费面声明 + §2.6-2 过渡双职责与退役指针）；cw_game_state.py:846「随 W8 消亡」措辞修正（§2.1）；feed/board_state_bridge/公共读口族 docstring 中的「CwWorkFrame」字样随扫更新；last_state 写点面文件（cw_screen_prep.py、cw_op_buy_cards.py:935）的 docstring 与注解随扫——机械改名扫是全仓 grep 不漏代码面，本锚清单防文档扫圈文件漏点；正本文档（strategy-docs/game_state 区）正名扫归落地批正本更新阶段。

### 2.7 行为零漂移门（落地批验收形态）

- 正名收编批 = 纯机械改名 + 文档面，**sim 行为零漂移**：同 seed 行为投影 digest 逐位一致（投影口径 = test_cw_sim_fidelity 行为投影；锚值以当时有效锚为准——T-145 验收实证锚存在世界依赖，重锚归 T-83 增补门，本设计只锁「改前改后逐位一致」，不锁具体值）。
- sim 圈定测试集参照 T-145 V3 十七文件集；正名批新增 `CwWorkFrame` 全仓零命中哨兵。
- 机制面零改动申报：字段集/缺省值/转移规则/账本语义逐项不变，任何「顺手优化」都属越界（禁夹带）。

### 2.8 关键取舍

| 备选 | 裁决 | 理由 |
|---|---|---|
| 方案 B：x/position_pref/回滚入容器记录模型 | **作废**（用户裁定 2026-09-12） | 改「不采 sim 内部口径」设计明文，破容器按实机真值建模的纯度；三点是表示边界非缺陷（T-145 验收复核） |
| 方案 C：引擎双写（容器先写+帧镜像） | 否决（维持 T-145 §5-1 判断） | ~200 触点改造，机制表示问题原样存在，不解决实质 |
| sim 域移居（帧+simulate 迁 sim/ 包） | 否决 | §2.2 理由 1-3：动作语义单一源被 kernel 侧消费钉死（mutate 链），移居制造 kernel→sim 反向依赖或双源；sim→kernel 既有方向翻转波及全仓 |
| kernel 内拆独立模块（如 kernel/cw_frame.py） | 否决（本期） | §2.2 尾段：候裁9 已定谳 cw_vocab 定居，拆文件第二轮 import 扫描与 shim 生命周期成本 > 文件语义单一收益；契约边界由文档承载 |
| 方案 A 原文「kernel 私有工作台」的「名义切换」质疑 | 正面回答 | 本形态与方案 A 的差异 = 把「私有/名义」换成「正式契约」：机制必需表示以 §2.3 对账表逐字段定界（B/C/D 类不入同步面是**设计明文**而非默认放任）、动作账宿主成文（§2.4）、回滚原语成文（§2.5）、退役语义成文（§2.6）——T-145 验收预期「需在 criteria 明文接受该形态」，本设计即该明文本体。帧形态保留不是妥协：试动作-反悔机制要求可变值语义 + 机制完整表示，与记录模型的 frozen 帧替换在表示层不可调和（§1.2 归层），两套表示平行存在是治本形态，方案 B 才是需要改设计边界的妥协路 |

### 2.9 移交 landing 的待决点清单（落地批立项时由编排者补明为阶段判据）

设计定稿后仍需落地批落笔的实现口径三处，本设计预留裁决方向，landing 立阶段时补明：

1. **哨兵扫描域**：`CwWorkFrame` 零命中哨兵的扫描域 = src + 测试仓；docs 不入哨兵域——正本文档正名扫归落地批末阶段正本更新（§2.6 文档锚），哨兵含 docs 会过早红。
2. **digest 对照取树口径**：§2.7 行为零漂移门的 digest 对照以 fresh worktree（干净 checkout）为准，或显式挂 T-83 增补门为依赖——T-145 验收已实证锚存在「共享树绿/干净树红」世界依赖，共享树验证不等于仓库验证。
3. **正本化措辞改写**：正本更新阶段把本件的压缩表述（腾名/账债关闭/双禁令等依赖 r5-migration-plan 先验知识的词）改写为直白表述并给首现定义，禁原样搬进正本。
