# session 解散地图（详设）

## 问题与约束

`StrategySession`（`kernel/cw_strategy_session.py`）30+ 字段三类混装；本篇钉死每样东西的去向与读者迁移契约。约束：①**正常识别路径行为零变化**——每字段迁移后读到的值与迁前逐字节相同；识别失准路径的行为变化 = 用户裁定接受项（总纲 §1.3），仅限 §A 删除族；②每字段唯一归属（gs 槽 / 实例属性 / Match / 删除），禁双宿主过渡期残留双源；③kernel 不 import 策略实现包的依赖矩阵保持；④字段名以全仓 grep 普查对账表为准（本篇名称为设计面锚，落地普查逐条归类）。

## §2 输入承载契约（自足重述；前置迭代同名语义的继承版）

### 2.1 十二 payload 槽表（决策输入容器化）

家族归属 = fields.md §2.2 画面附加域显式例外（「当前画面的 payload，非当前画面 = None」）：在屏由唯一写者观察覆盖、离屏置 None、进决策时 None = 观察层失约抛错。来源渠道 = observation。

| # | 槽位 | 类型 | 唯一写者 | 消费入口 | 动作 |
|---|---|---|---|---|---|
| 1 | `gs.prep_obs` | `PrepObservation \| None`（非 Field 容器字段） | CwScreenPrep 观察链（写点白名单原样平移） | decide_prep_screen；`cw_equip_wear_plan`；`_act_execute_default` OpenShop 腿死读点（换源不删参） | 自 session 迁入 |
| 2 | `gs.shop` | `ShopPayload \| None` | 既有观察段 | decide_shop_action | 不动 |
| 3 | `gs.encounter` | `EncounterPayload`（options 升级 `list[EncounterOption]`） | CwScreenEncounter | decide_encounter | 域版本 bump |
| 4 | `gs.supply` | `SupplyPayload`（options 升级 `list[SupplyOption]`） | CwScreenSupplyNode | decide_supply | 域版本 bump |
| 5 | `gs.invest_strategy_opts` | `list[str]`（OCR 原文名） | CwScreenInvestStrategy | decide_invest_strategy | 新增 |
| 6 | `gs.invest_env_opts` | `list[str]`（OCR 原文名） | CwScreenInvestEnv | decide_invest_env | 新增 |
| 7 | `gs.megastar_opts` | `list[MegastarOption] \| None` | CwScreenMegastar | decide_megastar | 新增 |
| 8 | `gs.partner_opts` | `list[PartnerOption] \| None` | CwScreenPartner | decide_partner | 新增 |
| 9 | `gs.planner_opts` | `list[PlannerOption] \| None` | CwScreenPlanner | decide_planner | 新增 |
| 10 | `gs.star_tome_opts` | `list[str] \| None` | CwScreenBookcard | decide_star_tome | 新增 |
| 11 | `gs.wish_trial_opts` | `list[str] \| None` | CwScreenWishTrial | decide_wish_trial | 新增 |
| 12 | `gs.box_card_names` | `list[str] \| None` | CwScreenBoxPick | decide_box_card | 新增 |

配套：8 新域键 + 2 变域 bump + `node_screen_refresh` 域 +1（新顶层字段）；选项类宿主不变（`cw_events.py`），payload 槽注解字符串化 + `TYPE_CHECKING`（#3/#4/#7/#8/#9 选项类同住 cw_events，循环导入禁；先例 = session `prep_obs_frame` 字符串注解）；序列化经 `dataclasses.asdict` 鸭子形；`prep_obs` 非 Field 不占域键。

### 2.2 属屏映射与路由清点（自足重述）

- **路由屏取值规则**：识别命中且在映射内 = 该屏名，只清属屏 ≠ 它的槽；映射外建档屏 / 非身份臂语境（阶段二备战双锚、阶段三特殊规则臂）/ 未识别 = 清全部十槽（这些语境无任何 decide 消费，清点只影响审计面）。
- 属屏映射单一源 = `_PAYLOAD_DOMAINS` 扩展为 `槽 → (属屏, route_clearable)` 二元组。十行清点全集（分发键 = `_dispatch_identity_screen` 建档屏名，锚 `cw_loop.py` 分发臂）：`gs.encounter`→货币战争-遭遇节点；`gs.supply`→货币战争-补给；`gs.invest_strategy_opts`→货币战争-投资策略；`gs.invest_env_opts`→货币战争-投资环境；`gs.megastar_opts`→货币战争-盛会之星；`gs.partner_opts`→货币战争-列车同行；`gs.planner_opts`→货币战争-骇入策划；`gs.star_tome_opts`→货币战争-星徽秘典弹窗；`gs.wish_trial_opts`→货币战争-祈愿试炼；`gs.box_card_names`→货币战争-备战-武装箱选择（**分流注**：`货币战争-武装箱弹窗` 派发 CwScreenArmoryBox，无 decide 调用不产槽）。
- 豁免：`prep_obs` 不入映射；`shop` 入映射 `route_clearable=False`（清点口全集三处 = CloseShop 逻辑腿 + prep 相位观察商店锚 miss 分支 + 机械关店口 `CwOpCloseShop._clear_shop_payload → leave_screen`，点击已发/幂等已关两出口同清（commit 554e3dea6 落地）；shop 清点单一源语义 = 关店出口统一经 CwOpCloseShop 清场，路由挂点不辖 shop）。
- **「已 None 跳过」实现落点 = 路由挂点侧**（挂点读槽值判 None 跳过，不占 write_seq 不落 journal），`leave_screen` 本体不动；清点写入口经 `leave_screen(槽, sig=…)`，sig family/mode 引用既有 CloseShop 腿清点行同一常量源、`actor='cw_loop_route_clear'`。
- 两路径语义：`stop_at_prep` 早退发生在挂点之前（早退轮不清点，清点顺延至 loop 下一次路由周期）；未知兜底在分发后循环尾（不绕行，未识别轮清全部十槽）。

### 2.3 瞬态槽三分语义 + 刷新通道

**离屏 = None**；**在屏失读帧 = 不写不读**（handler 走自身失败安全分支）；**在屏读得 = 覆盖**。判别信号定死 = **「写槽以该分支将调用 decide 为前提」**。结构防线 = **「每次决策恰以当次观察产物为单源」**。`prep_obs` 不适用（豁免域）。

三条刷新建议通道动作化（用户裁定）：`RefreshNodeOptions()`（encounter）/`RefreshSupply()`（supply）/`RefreshInvestCards(slots: tuple[int, ...])`（invest 逐卡槽位，三闸点击链留 handler）。**各通道刷新闸输入源（零参后的判定依据）**：encounter = per-visit 位（见下）；supply = `gs.supply_refresh_used`（与现调用方派生式逐字节相同）；invest = 现 PickEvent.refresh_slots 产生条件原样（kernel `decide_event` 返回值携带，入口包装时转动作）。

`encounter_refreshed_in_visit: Field[bool]`（顶层字段，渠道 `logic_action`；journal 归属 = write_logic 常规规则进快照流水，不适用「刷新计数组」豁免类）完整契约：
- **语义单位 = 每次决策调用会话（handle 调用）**，非 op 实例：现状首调缺省 False、刷新发射后重决策 True、重入重走首调复位 False；
- **写 False** = 各决策路径（handle/lifecycle）每次进入的首调前置段；**写 True** = 刷新发射分支内、重决策发起前同步直写；两点均**同步直写、失败即异常上抛**（fail-loud）；无 match 语境经 `cw_match` None 守卫跳过（缺席跳过，megastar_clicked 同型）；
- **读侧**：`decide_encounter` 读本字段（**读点声明**——零参后 refresh 旗标的唯一输入源；禁误接累计计数 `gs.encounter_refresh_used`，那会在第 2+ 遭遇节点首调产生建议分叉）；未写态读 None 缺省 False（生产不可达；第三方/测试直调口径，megastar_clicked 同型先例）；
- 窗语义：True 残留 = 刷新发射至同 handle 重决策之间；跨 handle 无读面；不在路由清点辖域；
- handler 侧「本局已用」累计计数闸与日志分支原样保留（读 `gs.encounter_refresh_used`，现状不动）。

### 2.4 刷新重决策链分屏形态（禁统一改形）

- **encounter = 同访问内二次「读得=覆盖」**：刷新后重决策前以重读产物覆盖写槽再 decide；
- **supply/invest = 发射后交回重入型**：刷新发射即 return（supply 经 round_retry 重入），重入访问走常规「OCR → 写槽 → decide」起点链天然单源——禁照 encounter 形态改 supply 为同访问重决策（行为变化）。

## §A 识别层防御缓存 → 删除（用户裁定 2026-09-16）

| session 字段 | 现消费面 | 删除后的表现 |
|---|---|---|
| `last_hp` / `last_hp_t` | `cw_hp_policy` gated_hp/decision_hp 新鲜度门；**`cw_screen_battle_wait:458` killed 判定兜底（删后改读 gs.hp——行为变化登记 §1.3）** | 门简化为 gs.hp 直读（gs.hp 有结算覆盖写端 + carried 语义兜底一层） |
| `last_hp_real` / `last_hp_real_node` | 备战血量真值对账 | 读什么用什么 |
| `hp_suspect` | hp 下行拒信复现通道 | 通道关闭 |
| `last_level_obs` | 等级单调守卫（OCR 误读防线） | 误读直接进判据直至下次读对 |
| `star_pending_regression` | star 回退防抖（合成动画窗） | 窗内误读直接进板面账。**连带面申报**：①star_regression 停机钩子/留证链原以防抖窗态为触发条件——钩子改绑 star 回退事件本身（防抖删、留证保持，失败可见）；②依赖防抖窗态的银狼升费豁免随窗消亡（行为变化登记）；③ADR-0420 帧态门删除申报 |
| `upcoming_types` | buy_cards journal 行（`'?'` 软兜底，唯一消费） | 删 + journal 行该列降级申报（'?' 常态化） |

删除 = 字段 + 全部消费逻辑（`cw_hp_policy` 新鲜度门、单调守卫、防抖窗）+ 写端，**非迁移**；普查词表 = 七符号全仓（两仓 + 正本树），承载桶 = 随本阶段删 / 不辖申报。
失准处置路径 = 识别优化批（修识别本身），不回滚锚（用户裁定）。

## §A′ 节点探针族 → gs 非 Field 簿记组 `node_books`（迁移重锚，**不删**）

**定性**：`plane_node_table`/`plane_node_table_plane`/`plane_lengths_seen`/`nodeseq_probe_anchor` 不是防御缓存——是 `schedule_of`/`nodes_of_plane` 的**现役唯一真值源**（位面日程/视界/hp 门时基），链观察批已定性「各司其职」并把退役划「另批承接消费点重接」；本批 = 该承接批。用户「删缓存」裁定不覆盖真值源（删 = 位面日程/视界/时基全链瘫痪）。

| 字段 | 落位 | 读者（重锚全集） |
|---|---|---|
| `plane_node_table` / `plane_node_table_plane` / `plane_lengths_seen` / `nodeseq_probe_anchor` → `node_books` 同名四槽 | `cw_game_state.py` 非 Field 组（宿主先例 = `exec_books`） | `cw_plane_table.schedule_of`/`nodes_of_plane`（真值源读口）；`cw_economy`/`cw_intention`/`cw_discipline_rules`/`cw_line_switch`（日程/视界消费）；`cw_hp_policy`（门时基残余消费——门主体已删，残余读点一并重锚）；`cw_screen_battle_wait` 结算锚（`node_t_of` 同式契约）；mandate_v1 全判据（shop/proof/encounter/levelup/budget/horizon） |
| `last_node_type` / `node_type_current` → **字段删除、消费面重锚 `node_kind_of(gs)` 直读** | gs 已有推导读口（`cw_game_state.py::node_kind_of`，链观察产物） | 现状双源并存：一半消费点已直读 gs 推导（entry/buy_cards/mandate/shop/cw_reward_node/sim），另一半「session 识别值优先 + gs 兜底」（`cw_discipline_rules:200`/`flow.py:169`）；重锚 = 后一半换 gs 推导直读，删左移推断装配（`cw_screen_prep.py` 写点族）；`entry.py:787`/`battle_wait:424` 遥测读点同换 |

迁移契约 = 值等价换宿主（写者原样、读者改解析宿主），非删除；普查词表 = 四符号 + `last_node_type`/`node_type_current`（重锚六符号）全仓，承载桶 = 重锚 / 不辖申报。`upcoming_types` 归 §A 删除（唯一消费 = buy_cards journal 行软兜底，降级申报）；`node_type_current` 现状双源并存——一半消费点已直读 `node_kind_of(gs)`，重锚 = 另一半（识别值优先源）换 gs 推导直读。

## §B gs 正本已存在 → session 重复账退役（读写点换源，无新槽）

session 实名 → gs 正本（**两套名不同，普查词表用 session 实名**）：

| session 字段（实名） | gs 正本 | 消费面备注 |
|---|---|---|
| `active_strategies` | `gs.active_strategies`（§3.4.4） | 机械换源 |
| `active_env` | `gs.active_env` | 机械换源 |
| `briefing_affixes` | `gs.enemy_affixes` | **非机械**：空门触发采集、跳过门、保位写、None 元素语义逐点保留 |
| `briefing_bosses` | `gs.plane_bosses` | 同上 |
| `enemy_difficulty` | `gs.enemy_difficulty`（§3.1） | 机械换源 |
| `selected_difficulty` | `gs.selected_difficulty` | 机械换源 |
| `last_streak` | `gs.streak`（§3.2.12） | **主消费 = `cw_observation` 观察喂入 + obs_conflict 仲裁**（:2310-2325 一带）；economy 侧为次级读 |
| `chosen_megastar` / `chosen_partner` | `gs.chosen_*`（handler 已 write_logic） | 机械换源 |
| `last_owned_equips` | **特例——值不等价**：exec_state 选卡到账 +1/穿戴 −1 写腿在 gs.equips 刻意无对应（在册豁免）。处置 = **删**；武装箱打分输入改读 `gs.equips` 现值（保守缺省）——**消费点 = `flow.py::decide_box_card`**（非 cw_equip_wear_plan，其输入 = prep_obs）——行为变化登记（总纲 §1.3）；完整库存账 = 库存域建模批 |
| **载体中继机制**（relay 六调用，输入 100% 为本表待删 session 字段） | relay 随字段退役改直连 gs 正本（fields.md §2.1 正本行随批改写） | — |

迁移契约：读者逐个换源；写端仅写 session 份则改写 gs 份后 session 份删除（普查对账表兜底）。

## §C 框架设施

| session 字段 | 去向 |
|---|---|
| `rng` | 策略实例 `self.rng`（构造即种子化，`None → 0` 语义保持） |
| `performance` | `CurrencyWarMatch.performance`（battle_wait 结算点写点换宿主；**kernel 唯一读者 = `cw_reconcile._battle_facts_between` 同步换源**；`reconcile_hp` 对账腿随 hp 锚删除简化——gs.hp 单源后双源对账无对象，对账腿删 = 行为变化登记 §1.3） |
| `strategy_state` | 策略实例 `self.state`（§3 读者迁移） |
| `pending_round_outcomes` | **删**（只写不读零消费死面，`cw_screen_battle_wait` 写入端随批停止） |
| `prep_obs_frame` | `gs.prep_obs`（非 Field；写读者全集换宿主） |
| `prep_frame_class` / `shop_frame_class` | gs 非 Field 两槽 `frame_class_prep`/`frame_class_shop`（直存直取；**不与 chain `mark_frame_obs` 单槽合并**——单槽已有 chain 在产写端且 view 语义异源，双消费者互偷；机制合并归统一观察架构批）；方向刷新触发读口换源，帧类写点守卫锁随批翻新 |
| **create_session 副作用** `reset_layout_unknown_state()` | **函数本体保留不退役**——复位对象是 `obs/cw_back_layout.py` 模块级全局 `_unknown_streak`（跨局残留防线），与 gs 容器无关（cw_vocab:961 在册）。处置 = create_session 退役后**调用点迁引导漏斗每局建立时**；测试隔离复位入口保留；`obs/cw_back_layout.py` 入 3.5 文件面 |

## §D StrategySession 类本体

全字段归位后拆类；`strategy_state_of`/`ensure_strategy_state_attached`/`install_strategy_state_factory`/`strategy_state_lazy` 访问口族随拆退役；`bind_exec_state`/`exec_state_of` 已随前置迭代消亡。

## §3 StrategyState 外部读者迁移（总纲 §2.5 展开）

普查词表 = `strategy_state_of` / `state_of` / `strategy_state`（含注释形态；**子串污染申报**：`state_of` 为 `strategy_state_of`/`game_state_of` 子串，普查按全符号匹配归类），两仓逐仓 + 正本树（排除 `sources/`/`changes/`/`proofs/`）。承载桶六类：

1. **kernel 判据函数参数注入（已有形参位）**：session getattr fallback 删除，调用方（ops 层）从 `ctx.cw_match.strategy.state` 取值注入既有形参位；
2. **执行层显式读**：`ctx.cw_match.strategy.state.<字段>` 直读——预登记重载面：cw_loop（cw4_counters 预算闸族）、cw_screen_deploy（target_comp/fuel_filler_stall_buys/cw4_m1p_*）、cw_screen_buy_cards（cw4_visit_bought_names）、**operations/cw_op/（cw_buy_card_action、cw_op_sell_off_target、cw_op_tools 三处 state 读者）**；
3. **kernel 新增 state 形参**：体内自取非 fallback 的（`cw_deploy_logic` 等约 5 处）签名新增 state 形参申报（非判据变更）；
4. **遥测快照换源**：局终快照链单点改 `match.strategy.state`；
5. **impl 内部**：`state_of(session)` → `self.state`；
6. **正本批辖**。

零未承载项产出对账表；写端缺席态语义（None-safe 跳过）逐点保留（megastar_clicked 先例）。

## §4 game_state_of 访问口退役（总纲 §2.6 展开）

普查词表 = `game_state_of`（src 树 + sr-od-test 独立仓全量直查为准，计数随普查表申报）。承载桶四类（统一口径）：**桶 1 调用方已有 gs 形参/局部引用直用；桶 2 改经持有点（策略实例 `self.gs`；ops 层 `ctx.cw_match.gs`）；桶 3 kernel 补 gs 形参**（无 gs 形参的 kernel 函数签名收窄申报——非判据变更）；**桶 4 正本批辖**。

**journal 装配重锚**：journal 装配唯一锚 = `game_state_of` 建立路径——随旁口退役悬空；装配点迁至引导漏斗 gs 构造点（3.5 阶段承载），`game_state/journal.md` 正本随批更新。

## 关键取舍

- **obs_books 方案已撤销**（用户裁定：防御缓存删除，非迁移）——§A 为删除表；探针族因真值源定性单独重锚（§A′），不属于该裁定范围。
- **帧触发两槽入 gs 非 Field 而非并 `mark_frame_obs`**：单槽已有 chain 在产写端且 view 语义异源，双消费者互偷；机制合并归统一观察架构批。
- **pending_round_outcomes 删而非迁**：零读者死面（消费半早删，观察半候评估——本批即评估点）。
- **Match 增 gs 字段**：gs 正身在 Match（strategy 持只读引用），ops 取容器 = 「取当局事实」语义，所有权一致。
