# 后果声明（world decl）详设

## 问题与约束

- 辖域：`WorldDecl` 声明 schema、18 转移动作的声明对照、动作 op 喂入、画面 op 派发点判断、`SimBackend.advance` 推进分派、转移事件半部退役。总纲划给本篇的接口契约 = design.md §2.2 七条。
- 硬约束：实机路径零行为变化（端口未装 = no-op；派发点判断结果与现行 `terminal` 判断逐动作一致）；kernel 上报函数保持纯函数（零机制——无装饰器无 sink）；`sr_od/operations` 共享层零改动。
- 依据标注约定：本篇画面档名字面值权威 = `assets/game_data/screen_info/` 各档 + `sim/cw_sim_backend.py` 档名常量；动作→交回目标权威 = `docs/develop/sr_od/application/currency_war/screens/<篇>.md` §5 终结/交回表（下表逐行标核实状态）。

## 方案

### 1. 声明 schema（kernel 新增，住 `cw_event_hooks.py` 同域新家）

```python
@dataclass(frozen=True)
class WorldDecl:
    """动作后果声明(上报函数构造;消费面见 §4)。"""
    next_screen: str    # 动作后确定的下一画面 screen_info 档名;'' = 无画面(局终等未建模终态)
    trigger: str     # 推进分派类别(§3 分派表);'' = 无
```

> 命名注记：`trigger` 是声明数据里的分类标签，随 `LogicOutcome.world_decl` 显式传递；它与本迭代退役的事件机制（`TransitionEvent`/sink/订阅）无关，退役后该词不再有任何机制含义。

**单值依据**：游戏推进确定性——推导权威源 = **kernel 节点日程真值表**（本迭代自 `sim/cw_sim_plane_schedule.py` 迁入 kernel 新模块 `cw_node_schedule.py`：纯数据零依赖，迁移无技术障碍，attack.md 复审 R1 修法 (a)）+ `effective_node_ord`（`report_node_advance` 推进落账写 `node_ord`）。**禁读容器 `gs.node` 作推导口**——它是观察镜像，不随推进变（写端 = 观察漏斗/类型派生/sim backend，均在构造点之后；`chain_node_type` 构造时刻诚实缺位），R1 复审定案。backend `_on_node_advance` 迁表后同源 import。

- 载体：`LogicOutcome` 新增 `world_decl: WorldDecl | None = None`（dataclass 默认字段，全量构造点零改动兼容）。
- 构造义务：上报函数 `applied=True` 出口必构造；`applied=False`（拒绝/未发出）= `None`——对齐现行「applied=False 零广播」（`cw_event_hooks.transition_event_on_applied` 装饰器语义，本迭代后该语义由构造纪律承载）。
- **签名改形申报（D1）**：18 个上报落点中 17 个现役返回 `LogicOutcome`，唯 `report_node_advance` 返回 `bool`（推进落账位）。本迭代将其返回形态改为 `LogicOutcome`（`applied` = 推进落账位，`world_decl` = node_advance 声明），两个 bool 消费点（`cw_op_settle_confirm.py` 的 `_advanced` 日志、`cw_pick_supply_action.py` 的确认分支）随 3.2 改造为 LogicOutcome 消费。
- 语义类（`trigger`）收敛集：**backend `advance` 分派表为单一源**（下 §3），现役 9 类。**准入判据一句话：上报函数/获得链已写的（腾席/离屏/动作直接后果）不进 trigger；只有 backend 专属的活才进**（sim 经济结算/队列出队/候选采样/排除集簿记——实机里「游戏自己算」的部分）。**值零新词，沿用现役动作名**（`node_advance`/`battle_resolve` 为归并过程名）；`''` = 纯画面转移（backend 只按 `next_screen` 推进，零专属过程）。禁自造动宾变形（`box_pick` 之类与画面名/动作名错位的词一律不进本集）：

```
node_advance / battle_resolve / open_box / pick_box_card / pick_megastar /
pick_planner / pick_supply / pick_invest_env / pick_invest_strategy
```

纯转移动作（`trigger=''`）：open_bookcard（腾席写端在其上报）、pick_partner/pick_fortune/pick_wish_trial/pick_star_tome/pick_expert_invite（零写占位，真值归观察）、close_shop（离屏写端在其上报）——backend 仅按 `next_screen` 推进画面。

### 2. 18 转移动作 → 声明对照表

广播点现状依据 = `cw_event_hooks.TRANSITION_EVENT_KINDS`（18 成员）与装饰器 grep 实证（2026-09-24）；「上报落点」= 声明构造处。

| # | 现行 kind | 上报落点（文件::函数） | trigger | next_screen | 核实状态 |
|---|---|---|---|---|---|
| 1 | settle_confirm | `kernel/cw_game_state.py::report_node_advance` | `node_advance` | 节点键推导单值（规则见下表） | 已核（推导规则） |
| 2 | supply_confirm | 同上（同函数按确认来源参数分 kind） | `node_advance` | 同上 | 已核（推导规则） |
| 3 | start_battle | `cw_action_report/start_battle.py` | `battle_resolve` | `'货币战争-结算'` | 已核（screens/prep.md §5 出战终结 + sim `_resolve_battle` 呈现 SCREEN_SETTLE） |
| 4 | pick_encounter | `cw_action_report/pick_encounter.py` | `battle_resolve` | `'货币战争-结算'` | 已核（encounter.md §5「派发即终结」+ sim `pick_encounter → _resolve_battle`） |
| 5 | open_box | `cw_action_report/zero_writes.py` | `open_box` | `'货币战争-备战-武装箱选择'` | 已核（box_pick.md §1 + sim `_on_open_box`） |
| 6 | open_bookcard | `cw_action_report/open_bookcard.py` | `''` | `'货币战争-备战-专家邀请函'` | 已核（腾席写端 = 本上报「开卡即腾席」；backend 活仅呈现，画面档全表唯一可推 → 纯转移） |
| 7 | pick_invest_env | `cw_action_report/pick_invest_env.py` | `pick_invest_env` | `'货币战争-备战'` | 已核（sim `_on_invest_picked`；opening 判别见 §3 推导）。⚠️ 该值隐性耦合现役 offer 日程（日程节点均 battle/reward → 备战；日程扩面时须随节点 kind 推导化） |
| 8 | pick_invest_strategy | `cw_action_report/pick_invest_strategy.py` | `pick_invest_strategy` | `'货币战争-备战'` | 已核（同上；同耦合注） |
| 9 | pick_box_card | `cw_action_report/zero_writes.py` | `pick_box_card` | `'货币战争-备战'` | 已核（box_pick.md §5 选卡即终结交回备战） |
| 10 | pick_megastar | `cw_action_report/zero_writes.py` | `pick_megastar` | `'货币战争-备战'` | 已核（megastar 弹在备战上，选完交回；sim `_on_overlay_picked`） |
| 11 | pick_planner | `cw_action_report/pick_planner.py` | `pick_planner` | `'货币战争-备战'` | 已核（同上同型） |
| 12 | pick_supply | `cw_action_report/pick_supply.py` | `pick_supply` | `'货币战争-补给'` | 已核定（attack.md §二：supply.md §5 交回落点无名值，选卡后画面本瞬间不变，sim `_on_supply_picked` 零画面写停留 SCREEN_SUPPLY；该值在 A2 双声明模型下自洽——随后到的 node_advance 声明才切走） |
| 13 | pick_partner | `cw_action_report/zero_writes.py` | `''` | `'货币战争-备战'` | 已核定（attack.md §二：partner.md §5 → 底层屏；registry decision 条目叠备战） |
| 14 | pick_fortune | `cw_action_report/zero_writes.py` | `''` | `'货币战争-备战'` | 已核定（attack.md §二：fortune.md §5 → 底层屏；registry 外屏，宿主画面域底层屏） |
| 15 | pick_wish_trial | `cw_action_report/zero_writes.py` | `''` | `'货币战争-备战'` | 已核定（attack.md §二：wish_trial.md §5 明示「回备战」） |
| 16 | pick_star_tome | `cw_action_report/zero_writes.py` | `''` | `'货币战争-备战'` | 已核定（attack.md §二：bookcard.md §5 → 底层屏；星徽秘典弹窗叠备战） |
| 17 | pick_expert_invite | `cw_action_report/zero_writes.py` | `''` | `'货币战争-备战'` | 已核定（attack.md §二：expert_invite.md §3 明示「弹窗关回备战」） |
| 18 | close_shop | `cw_action_report/close_shop.py` | `''` | `'货币战争-备战'` | 已核（shop.md §5 关店回备战；离屏写端 = 本上报） |

**`node_advance` 的 next_screen 推导规则**（声明构造点 = `report_node_advance` 推进落账**后**；`node_ord` 已是新节点序——序数字段随推进写，与观察镜像 `gs.node` 无关，见 §1 单值依据/R1 复审定案）：

```
eff = effective_node_ord(gs)            # 推进落账后的新节点序
总长 = sum(len(node_sequence_of(p)) for p in (1, 2))   # kernel 节点日程真值表（R1 迁入）
eff > 总长 → next_screen = ''            # 局终（P3 未建模；交回照常，外循环走结束链）
plane, round_num = 反解(eff)      # 仿 backend `_ordinal_to_node`（cw_sim_backend.py:1111-1120）按迁入表变长累加，实现落 kernel 迁移件 cw_node_schedule.py
kind = node_sequence_of(plane)[round_num - 1]   # 迁入 kernel 的真值表取 kind（backend 同型做法）
plane > 1 ∧ round_num == 1 → '货币战争-位面过渡'           # 位面切换优先
kind:
    supply    → '货币战争-补给'
    encounter → '货币战争-遭遇节点'
    boss      → BOSS简报档
    battle/reward → '货币战争-备战'                          # 与 _screen_for_node 同映射
```

迁入随注（F2）：总长与反解一律用迁入表的变长累加/公式（与 backend 同型），禁用固定位面长度常量（固定 9 仅在 P1=9 时与变长重合，非通用前提）。

迁移件（R1 修法 (a)）：`cw_sim_plane_schedule.py` 真值表迁 kernel 新模块 `cw_node_schedule.py`（`node_sequence_of` 等原样平移），旧模块**退役**（薄委托 = 零消费死壳不留），sim 消费点改 import kernel——消费点实测 = backend/测试（生成器零消费，F3 已核）；关联指针修正 = `kernel/cw_battle_calib.py:15` 模块注释现指 sim 路径，随 3.2 改指 kernel 新模块。

### 3. `SimBackend.advance(decl)` 推进分派

- 入口：`cw_sim_ports.declare_world(decl)` → 端口未装 no-op；装了 → `backend.advance(decl)`。`decl is None`（非转移动作）端口层直返。
- 分派表（现行 `on_transition_event` 各 case 内部逻辑**平移不变**，判别子从 kind 换成 `trigger`）：

| trigger | 平移目标（现行 case） | 内部逻辑 |
|---|---|---|
| `node_advance` | `settle_confirm/supply_confirm → _on_node_advance` | 节点经验入账 + 轮首收入（现役含胜利奖励发放，时序披露见下） + 商店全刷 + overlay 队列检查（按节点） + offer 检查 + 呈现节点屏（幂等守卫不变） |
| `battle_resolve` | `start_battle/pick_encounter → _resolve_battle` | coarse 结算：hp 扣减 + 连胜计数转移 + 败补挂账 + 结算页呈现 |
| `open_box` | `open_box → _on_open_box` | 箱面呈现 + **候选采样写容器** |
| `pick_box_card` | `pick_box_card → _on_box_picked` | 装备获得链入栏（`gain_equipment`：equips 追加 + 送单位表回调，装备无升星判断；选卡上报为零写占位，入栏归 backend）+ 模态交回 |
| `pick_megastar` | `pick_megastar → _on_overlay_picked('megastar')` | **overlay 队列出队** + 交回 |
| `pick_planner` | `pick_planner → _on_overlay_picked('planner')` | 同上 |
| `pick_supply` | `pick_supply → _on_supply_picked` | **宝钻写**（读容器 chosen_supply 写 diamond_count） |
| `pick_invest_env` / `pick_invest_strategy` | `pick_invest_env/strategy → _on_invest_picked` | **排除集累计**（offer 采样去重，backend 私有簿记）+ 模态交回；**opening 判别推导 = `gs.node.value is None`**（现行 `_after_modal_pick` 第二腿即此判；env 恒开局、strategy 恒非开局，推导可靠，声明无需携带） |
| `''`（纯转移） | `open_bookcard → _present_modal(SCREEN_EXPERT)`；`pick_partner/fortune/wish_trial/star_tome/expert_invite/close_shop → _dismiss_modal` | 零专属过程——按 `next_screen` 推进画面（呈现 overlay / 幂等交回；`_dismiss_modal` 节点窗让路恢复位语义保留） |

**奖励发放时序披露**（实机口径 vs sim 现役 coarse 口径；差异归 sim 校准批，不影响声明结构）：实机 = 战斗结算时发节点基础奖励与连胜奖励（结算页呈现）；sim 现役 = 结算时转移连胜**计数**，胜利金币奖励随**下一节点窗轮首收入**发放（`apply_round_start_income` 的 `win_reward_mult` 胜利奖励乘数，M04 流键坐标系平移自旧引擎）。

- **对账面**（`next_screen` 的 sim 消费）：`advance` 完成后，对 `next_screen` 非空串的声明断言**状态机底层稳态画面 == `decl.next_screen`**（稳态 = 让路恢复位消费完、队列弹完后的 `_present_node_screen`/`_dismiss_modal`/`_present_modal` 落点屏）。**建模内合法失配豁免集**（这些场景最上层呈现屏 ≠ 底层稳态，非漂移）：① overlay 队列命中（`_window_resume='offer'` + `_present_pending_overlay` 呈现巨星/planner 等）；② offer 日程命中（呈现投资策略屏）；③ 节点窗让路期间选卡族经 `_dismiss_modal` 恢复到 offer 屏/节点屏——豁免集内断言延后至稳态（overlay 选完/让路消费完后对账）。**局终断言载体**（`next_screen=''`）：`backend.done` 为真 ∧ 呈现 ∈ {'货币战争-大厅'}（`_game_over` 现役呈现，cw_sim_backend.py:1425-1432）——非字面等值空串。断言不等且不在豁免集 = 缺陷留证（`disclosures` 或 defect sink）不停机——声明与状态机漂移的早期警报。
- **集外处置**（S4）：`trigger` 值不在分派表键集 = `ValueError` 响亮——与现行 `emit_transition_event` 集外 kind 同等防线（构造点漂移 = 接线 bug，禁静默）；分派表键集 = `advance` 模块常量单一源。

### 4. 动作 op 喂入与消费面

- **喂入**（动作 op 内，自上报后一行）：

```python
cw_sim_ports.declare_world(gs_outcome.world_decl)
```

落点 = 18 转移动作对应的动作 op（`operations/cw_op/` 下：`cw_start_battle_action` / `cw_pick_encounter_action` / `cw_op_settle_confirm` / `cw_open_box_action` / `cw_open_bookcard_action` / `cw_close_shop_action` / `cw_pick_box_card_action` / `cw_pick_supply_action` / `cw_pick_invest_action`（投资两屏同指一 op，registry 两 param 行；env/strategy 声明随各 param 的上报出口各构造各喂）/ `cw_pick_megastar_action` / `cw_pick_planner_action` / `cw_pick_partner_action` / `cw_pick_fortune_action` / `cw_pick_wish_trial_action` / `cw_pick_star_tome_action` / `cw_pick_expert_invite_action`）。喂入点核对（A2）：**settle_confirm → `cw_op_settle_confirm`；supply_confirm → `cw_pick_supply_action`**（现役补给选卡 op 内选卡后即发确认上报，cw_pick_supply_action.py:84——结算 op 不发 supply_confirm）。

**多支上报并喂契约（A2）**：一次补给动作 op 执行产生两支上报、两份声明（pick_supply 宝钻腿声明 + node_advance 推进声明），契约 = **每支上报出口各自紧跟一行喂入**（喂入行跟着上报走，不做合并）；round 结果 `data` 携带**最后一份**（node_advance，终结转移），先前声明仅经端口喂入、不再随 data 重复。

非转移动作本迭代**不加喂入行**（其 `world_decl` 恒 `None`，无信息可喂）；overlay 批扩面时按同契约加。

- **交回判断：派发点本迭代零改动**。交回语义由 `terminal` 单独承载（现状判断不变），声明不参与判断。依据两条（持久锚，D5）：① refresh 族 `terminal=True` 但无画面转移——`operations/cw_op/cw_refresh_shop_action.py` 关店/刷新族现役 terminal 登记 + `screens/README.md` §6 终结总表「访问终结但画面档不变」行；② 局终罕见态——P2 末确认 `terminal=True` 必须交回（外循环走结束链）但无下一画面（声明空串），「`terminal ∧ 声明非空`」式会在此卡死留守。声明对实机 = **数据面**：随 round 结果 `data` 字段携带（`OperationRoundResult.data: Any` 现役载荷位），journal 记「预期画面」供与实读画面 diff 对账（画面漂移早期警报料；禁作判效断言，A3 拆除纪律）。
- **overlay 批扩展位**：非终结动作（部署/买牌）触发弹窗需交回时，判断式扩展为 `terminal ∨ (data 声明 next_screen 为 overlay 档)`——data 通道本迭代就位，判断切换归 overlay 批。

### 5. 单动作单轨迁移

- 每个动作的落地 = ①上报函数构造声明（摘其装饰器/emit 点）②动作 op 喂入行 + round 结果 `data` 携带 ③`advance` 加对应 case（同时 `on_transition_event` 摘对应 case）。派发点零改动（交回判断 = terminal）。任一时刻同一动作只有一条驱动路径。
- `install_backend` 的 `set_transition_event_sink` 订阅保留至 3.4（仍有未迁动作时事件半部在役）；全部迁完由 3.4 整体删除。

### 6. 退役清单（3.4）

| 退役符号 | 位置 |
|---|---|
| `TRANSITION_EVENT_KINDS` / `TransitionEvent` / `set_transition_event_sink` / `emit_transition_event` / `transition_event_on_applied` | `kernel/cw_event_hooks.py`（文件保留——事实事件半部 `FACT_EVENT_KINDS`/`emit_fact_event`/`FactEvent` 原样不动；模块头注转移描述删） |
| 装饰器应用 16 处（8 具名文件各 1 + zero_writes 8）+ `report_node_advance` 内 emit 调用 1 处 | 各上报文件（3.2/3.3 已逐动作摘，本批验证归零） |
| `SimBackend.on_transition_event` / `install_backend` 转移 sink 订阅 | `sim/cw_sim_backend.py` |
| 测试对转移事件的断言 | `sr-od-test`（落地批 grep `transition_event` 盘点，断言平移为声明对照测试或退役） |

### 7. 测试与验收面

- **声明对照测试**（新）：表驱动——每个转移动作构造桩 gs 触发上报，断言返回 `world_decl` 的 `trigger`/`next_screen` 与 §2 对照表逐位一致（`node_advance` 的 `next_screen` 对桩 gs 节点序按推导规则断言）；`applied=False` 路径断言 `world_decl is None`。
- **e2e 回归**：`run_sim_full_match` 多种子（沿用现役验收种子集）跑通 P1→P2——声明驱动与现行事件驱动的世界终态对拍（`container_snapshot` 逐位一致是等价性的最强判据）。
- **实机零变化**：现役 op 流程测试（fixture_controller 剧本）期望不改全过；派发点判断对 18 动作逐动作断言「交回结果与改前一致」。
- **退役归零**：多形态探针（`transition_event` / `TRANSITION_EVENT` / 装饰器名）grep 归零，含跨行形态（清理批验收协议：单行 grep 被跨行绕过 = 假绿）。

## 关键取舍

- **声明双维互补，而非单维「下一画面」**：曾考虑只返回画面集（实机判断 + sim 挑选），放弃——sim 的节点窗/战斗结算是**过程**不是画面，画面集承载不了触发时机；反之 `trigger` 在实机无消费面。两维各司其职，消费强度互补（design.md §2.1）。
- **`trigger` 9 类 + 空，而非进一步收敛到 2 类过程**：曾考虑选卡族全部归纯转移由 backend 自容器推导细分，放弃——`pick_invest_env/strategy` 的排除集累计、`pick_box_card` 的装备入栏、`pick_supply` 的宝钻写是动作特异性后果（写端 = backend 私有簿记，上报零写），推导 = backend 第二份「动作→后果」账，恰是本迭代要消灭的形态。9 类的单一源 = `advance` 分派表，新增动作若落新类才扩表。**准入判据 = 写端归属**：上报/获得链已写的（腾席/离屏/直接后果）不进 trigger（open_bookcard/close_shop/五零档选卡因此降为 `''` 纯转移）；仅 backend 专属簿记与 sim 经济结算进。
- **`trigger` 值零新词（沿用现役动作名）**：曾考虑动宾归一命名（如 `box_open`/`box_pick`），放弃——与现役动作名（`open_box`/`pick_box_card`）错位、与画面名（box_pick = `CwScreenBoxPick` 武装箱选择画面）撞车，读者对不上号；归并类的 `node_advance`/`battle_resolve`/`dismiss` 是真同型归并所需的过程语义名，非新词。
- **喂入点在动作 op 内而非画面 op 派发点**：动作 op 自上报契约（op-layer.md §1.2「机械执行后 op 内直调自己的上报函数」）的自然延伸——`LogicOutcome` 在手即喂，画面 op 只读不转递；派发点分散于各画面 op，转递会加一跳传话。
- **`terminal` 保留而非吸收**：refresh 族证明「访问终结」与「画面转移」正交（持久锚 = `operations/cw_op/cw_refresh_shop_action.py` 现役 terminal 登记 + `screens/README.md` §6 终结总表），声明只承载转移；吸收 = 丢刷新族的交回语义。
- **单动作单轨，而非双轨灰度**：双驱动期间节点窗幂等守卫虽可兜住重复推进，但两套信号并存 = 行为等价性不可判定；单动作切 = 每步可用 e2e 种子逐位对拍验证。
