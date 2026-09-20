# 逻辑随机态采样落地·点晶矿（logic-rand-sampling）迭代设计

> 迭代目标 = 把逻辑随机态（`FieldSource='logic_rand'`）从内核基座推进到**首个动作落地（点晶矿）**，确立**采样语义 + 污染传递**两条纪律，作为后续随机动作（冶金炉/特权卡/好运令牌/投资卡随机授予）逐批迁移的范式。状态 = 对抗审中（修订轮）。文档清单 = 本文档（单文档方案，无详设）+ [landing.md](landing.md)。
> 读者 = 无会话历史的工程师/智能体，照本 spec 机械执行，勿重新设计。路径根 = `src/sr_od/application/currency_war/`；测试仓 = `sr-od-test/`（独立 git 仓，单独提交）。
> 基座已落地（主仓 commit `d24585b7d` / 测试仓 `7c6e1d4f`，2026-09-20）：`kernel/cw_game_state.py` 的 `FieldSource` 增 `logic_rand`、`write_logic_rand()` 写口、`observe()` 随机旁路（差异只落 `logic_rand_outcome` 台账行，无告警无安灯）、`logic_rand_fields()` 查询口。
> 用户裁定（2026-09-20，会话）：见 §0；游戏机制口述（点晶矿掉落规则）同源，证据分级 = 临时建模口径（§0 裁决 2）。

## 0. 已定裁决（禁重开）

1. **随机态语义 = 采样语义**：动作上报函数**真掷一次随机**，把采样结果当作真实发生的奖励走完整确定性链写入容器。抽中类型的域写**采样值**；未抽中类型的域**值不变、仅翻来源**（实机上采样是猜测，真奖励可能是另外两种，观察前 bot 不知道哪些域真变了）——三个类型影响域的**并集**全部标 `logic_rand`。
2. **点晶矿掉落规则 = 临时建模口径 v0**（用户 2026-09-20 临时拍定，**非核实游戏事实，后续按实机采集数据优化**）：点开晶矿 = **金币 / 装备 / 角色** 三选一。金币 1–5 随机；装备在**简易装备池**随机（装备注册表 category=`简易` 全集，`data/cw_equipment_data.py`）；角色在**当前概率表**上随机（随等级费用概率表 = `data/cw_shop_odds.py::REFRESH_PROB`，sim 发牌同源基线 `sim/cw_sim_shop.py::effective_deal_probs`；费用档内抽名 = `data/cw_chars.py::chars_by_cost` 均匀）。**校准回路**：规则参数集中于采样器常量面（§2.3），后续采集优化只改常量与披露键、不动结构；校准数据源 = 随机态观察收口天然产出的 `logic_rand_outcome` 行（采样值 vs 实读真值逐局积累）+ 必要时的专项采集钩子（后续批）。
   **在册冲突调和**：在册记载不完全一致——`docs/game/currency_war/research/screen_flow_timing.md` #16（实机观察记录）记三形态「奖励角色→备战 / 金币→商店 / 装备→右侧装备栏」，与本口径一致；`fields.md` §4.2 另记「角色/箱落席占 1 槽」（箱形态）、`research/final_comps/final_wandi_burn.md` 记「金币/角色/装备/稀有物」（月光精华层效果语境的晶矿）。**v0 有意取三选一**：箱/稀有物形态不进采样器，采样错形态时观察收口出 `logic_rand_outcome` 行兜底（安全的不准确，采集校准自愈）；v0 不表达箱形态的代价由发射位席满让路门 + 观察回补既有裁定承担（`screen_flow_timing.md` #16：「席满时部分晶矿可能没点开，由后续 heavy 观察自然回补（晶矿仍在→下轮再派）」）。
3. **满栏时点击晶矿无效、无法开启**（用户裁定）：上报前置门 = 备战席无空位 → `applied=False` 零写（与游戏侧行为同源；策略发射位的席满让路门为第一道防线，`fields.md` §4.2 CollectOre 前置谓词，本门是上报层同口径双保险）。
4. **直接在容器上逐步写**（废弃「scratch 攒批、一次性写回」）：上报函数内的每个语义步立即落容器，**每步 = 一次写入 = 一行状态流水**（备战多一个角色存一次；触发 3合1 存一次；再触发再存一次）。遥测无新增机制——现有流水按写落行，设计后果只是把动作分解成逐步写。
5. **参数只落写入口，纯计算函数不加**：`_merge_bench` 等纯变换保持纯函数；`_merge_bench` 加**可选步回调**（每完成一级合并调用一次，调用侧经回调落容器），缺省 `None` = 现行为（买牌路径零改动）；board 派生挂钩（`_write_logic_frame → _resync_board_delta`）在行域写为随机态时**继承随机态**。
6. **跨动作污染 = 上报入口判定**：上报函数入口检查「本次要读的输入域中是否有 `logic_rand`」→ 有则本动作全部产出标随机。**本批只接点晶矿**（其写入面按 §2.4 规则直接落，入口判定口本批建成供后续动作逐批接入——逐动作迁移是后续批，见 §3 边界）。
7. **RNG 注入**：上报函数加可选 `rng` 参数；实机不传 = 未播种 `random.Random`（采样是猜测，标随机态）；sim 传引擎流键派生 rng（流键 = `M1x/ore/{uses}`，`uses` = 引擎局内点矿动作单调序、1 基、引擎侧计数——流键硬约束「模块号 + 局内坐标」与 `M10/炉/{uses}` 先例同型，`sim/cw_sim_streams.py` 模块头；固定键会使同局多次点矿采样序列逐位相同）。
8. **sim 复用边界**：**动作内随机**全部住上报函数——sim 经 `sim/cw_sim_actions.py::apply_player_action` 委托同一函数，采样即世界真值，sim 零自算；**非动作环境事件**（节点间自动发牌 `M05/deal`、位面 boss `M20`、战斗结算）不是动作、无上报函数，留守 sim 侧自己的采样。
9. **board 跟随行域表达污染**：board（羁绊计数，派生量）不做独立标记写（派生量禁手写纪律不破）——行域实际变化时派生行自动继承随机态；行域仅标「值不变」时 board 不动，board 的可信度由消费侧查行域（`any_logic_rand(('front_row','back_row'))`）判定。

### 0.1 建模假设档（披露面，实机待核）

**整套掉落规则（§0 裁决 2）为临时口径 v0——用户拍定、未实测，与下表假设同批待采集校准**；校准 = 集中改采样器常量面，不改结构。

| 假设 | 内容 | 披露键 |
|---|---|---|
| 三选一等概率 | 金/装备/角色各 1/3（权重未实测） | `ore_type_uniform` |
| 金 1–5 均匀 | 区间用户拍定，分布形态未实测，按均匀 | `ore_gold_uniform_1_5` |
| 角色星级 = 1 | 晶矿掉落角色按 1★ 采样（直出高星无记载，同 sim 发牌 U12 口径） | `ore_char_star1` |
| 不受轮岗翻倍档影响 | 晶矿掉落概率表用基线 `REFRESH_PROB[level]`，不挂轮岗重掷（无依据不加规则） | `ore_no_rotation_tier` |

披露键在册落点 = `kernel/cw_ore_reward.py` 模块级披露表常量 `ORE_ASSUMPTION_KEYS`（实现时建，键名与上表一一对应），随局披露面汇总消费。

## 1. 问题与动机

- **现状症状**：随机奖励动作对「逻辑态与真值的分叉」无表达——点晶矿掉落金额/内容无写端（盲区申报，`prep_actions.py::PrepActionExecutor._executed_gold_delta` ClickSpheres 支）；投资卡随机授予无写端无吸收（`kernel/cw_projection_audit.py` 在册缺口，2026-09-19 拆除的随机对账申报面待重设计）；策略面无法区分「字段的观察值是当前真值」和「该值已可能被随机奖励改动」。
- **根因归层**：语义层。两态制（observation/logic，ADR-0651）只有「亲见的真值」与「确定可推算的预期」两类；**效果本身随机**的推算无落点，随机面被整体推给观察收口（`action-logic-state.md` §1.2 旧两档口径），跳写留下的旧观察值在策略面与真值不可区分。
- **解决到哪**：随机态在点晶矿全链落地（采样 → 污染传递 → 观察收口闭环），确立可复制的逐动作迁移范式；采样器与合成链即 sim 可复用的共享语义源。
- **明确不解决**：其他动作的随机态迁移（冶金炉/特权卡穿域腿/好运令牌采样迁入上报函数、投资卡随机授予写端、G7/G8 持卡修饰）——逐批后续迭代；策略消费门（备战环见 `logic_rand_fields()` 非空即发 `CwActionObs` 环内重观察）——策略器批；sim 批量验证与分布校准——sim 侧后续批。

## 2. 方案（单文档完整设计）

### 2.1 随机态语义（采样 + 污染 + 收口）

- **值语义**：`logic_rand` 字段的值 = 一个**可能世界**的快照（采样结果或未变标记值），不是真值承诺。策略器消费前必须重观察；消费门 = `logic_rand_fields()`（基座查询口，被观察覆盖后字段自然移出）。
- **污染传递（动作内）**：采样触发的确定性链上每次写入都标随机态——例：角色奖励落备战席（随机）→ 3合1 判定触发升星（随机）→ 行域变化 board 派生重算（继承随机）。
- **污染传递（跨动作）**：同一 visit 内、观察收口前，后续动作的入口判定读到随机态输入域 → 其全部产出标随机态（例：采样世界上的卖牌，退款落在采样的 gold 上，gold 仍随机）。
- **观察收口**（基座，零改动）：下一帧观察覆盖——真值与随机态值一致的域等值采新**零行零噪声**；不一致的域出 `logic_rand_outcome` 台账行（预期内，不进失配三分流、不响安灯）。实机 = 猜测被观察校准；sim = 无观察，采样即世界真值（`_MISMATCH_SUPPRESS_PREFIXES` 抑制面本就挡 sim 证据行，双保险）。

### 2.2 内核增量

| # | 改动 | 位置 | 契约 |
|---|---|---|---|
| 1 | `_merge_bench` 步回调 | `kernel/cw_merge_simulate.py` | 签名加 `on_step: Callable[[], None] | None = None`：**每完成一级合并**（升星/置 None/装备继承落地后）调用一次；`None` = 现行为。**调用侧写入契约**：回调触发时调用侧对**每个受该级影响的域各落一行**（整表值；一级合并可同时变更 bench 与行域——载体在场上时 bench 侧置 None 与行域升星同级发生，两域各一行、evidence 同带 `proj_ore_merge#N`）；merge 本体不感知容器 |
| 2 | board 派生继承随机态 | `kernel/cw_game_state.py::_write_logic_frame` | 行域写（front_row/back_row）的 source 为 `logic_rand` 时，`_resync_board_delta` 触发的 board 派生写**同标** `logic_rand`（现在硬走 logic）；evidence 仍 `proj_board_resync`。board 非 Field 行域，无递归派生 |
| 3 | 污染判定读口 | `kernel/cw_game_state.py::GameState` | `any_logic_rand(field_names: list[str]) -> bool`：任一名字段的现来源为 `logic_rand` 即 True。消费面 = 各动作上报入口（后续批逐个接入；本批建成+测试） |
| 4 | `write_logic_rand` docstring 采样语义修订 | `kernel/cw_game_state.py` | 「随机口径（确定面或期望）」改为三形态：**采样值 / 未变标记 / 确定外壳**；值不承诺真值；模块 docstring「逻辑随机态」段同改 |

### 2.3 晶矿奖励采样器

新模块 `kernel/cw_ore_reward.py`（纯函数离线可测，sim/live 共用）：

```python
def roll_ore_reward(rng: random.Random, level: int) -> OreReward
# OreReward = kind('gold'|'equip'|'char') + 载荷(gold int / equip str / char_id str)
```

- 类型：三选一等概率（假设档 `ore_type_uniform`，§0.1）；
- gold：`rng.randint(1, 5)`；
- equip：简易池均匀（category=`简易` 全集，`data/cw_equipment_data.py`）；
- char：费用档 ~ `REFRESH_PROB[level]` → 档内 `chars_by_cost(cost)` 均匀抽名；星级恒 1（假设档 `ore_char_star1`）。

多点批 = 每点独立调用一次 `roll_ore_reward`（同一 rng 实例顺序推进，批内序列不重置；跨批经流键 `{uses}` 坐标隔离，§2.5）。

**规则参数集中常量面（校准回路落点，裁决 2）**：类型权重、金区间、星级口径、概率表档选择全部落本模块模块级常量（各带披露键注释，与 §0.1 表一一对应）；掉落规则按采集数据优化时只改常量与披露键，采样结构、写入链、上报接口不动。校准数据源 = `logic_rand_outcome` 行（每行自带采样预期 vs 实读真值，逐局积累可统计），专项采集钩子如有需要另立后续批。

### 2.4 点晶矿上报改造（`kernel/cw_action_report/collect_ore.py`）

签名加 `rng: random.Random | None = None`（None = 模块级未播种 Random，实机；sim 传 `stream_rng(seed, 'M1x/ore/{uses}')`，§2.5）。

**多点载荷语义**：载荷为批式坐标列表（一动作可点开多颗，`select_ore_clicks` + `SPHERE_CLICK_BATCH_MAX_K`）→ **逐点顺序推演**：载荷序遍历，每点独立守卫、独立 roll、独立逐步写（同一动作组 `group_id`，全部 evidence 带点序 `#ore<k>`，k = 载荷序 1 基）。**席满即后续无效**：某点触发席满（含前点角色奖励耗掉空位后的累计判）→ 该晶矿留在 spheres（不摘除、不采样），其后的点同规则逐点继续判（前面点可能不掉席，后续点仍可开）。与在册裁定同源：`screen_flow_timing.md` #16「席满时部分晶矿可能没点开，由后续 heavy 观察自然回补（晶矿仍在→下轮再派）」。

**守卫（逐点前置，全拒 = 该点零写）**：spheres 未观察（现行为，整批拒）/ 载荷无交集（现行为，整批拒）/ **bench 未观察**（新，`'bench_unobserved'` 整批拒——席满守卫与角色落点均不可判）/ **该点时 bench 无空位**（新，该点跳过：晶矿留在 spheres 字段现值中（不摘除）、不采样——裁决 3）/ **level 缺读**（新，整批拒 `'level_unread'`——角色采样需当前等级，宁缺勿造）。spheres 摘除按点推进：开成的点即时摘除（逻辑态），没开的点留在 spheres 字段现值中（不摘除）。

**动作级出参词表**：全部点开成 = `applied=True`（reason 缺省）；混合批（≥1 开成 + ≥1 席满跳过）= `applied=True, reason='ore_partial_open_skipped'`；全部席满跳过（无一点开成）= `applied=False, reason='bench_full_no_open'`；整批拒词 = spheres 未观察 / 无交集 / `'bench_unobserved'` / `'level_unread'`（见守卫）。

**单点写序**（每步一行，同组 `group_id`；rand = `write_logic_rand`，logic = `write_logic`）：

| 步 | 域 | 来源 | 值 | evidence |
|---|---|---|---|---|
| 1 | spheres | logic | 该点坐标摘除（逻辑态，确定面） | `proj_collect_ore_drop#ore<k>` |
| 2 | 未抽中类型的域（gold/equips/bench/front_row/back_row 中不属于抽中类型的，且**现值非 None**） | rand | **值不变**（标记） | `proj_ore_mark_<field>#ore<k>` |
| 3a | 抽中金：gold | rand | 现值 + N（N ∈ 1..5） | `proj_ore_reward_gold#ore<k>` |
| 3b | 抽中装备：equips | rand | 现值 + [采样件] | `proj_ore_reward_equip#ore<k>` |
| 3c | 抽中角色：bench | rand | 工作列表落位后整表（`bench_place`，深拷贝元素防别名） | `proj_ore_reward_char#ore<k>` |
| 3c+ | 触发合成时：bench / front_row / back_row | rand | **每级合并后，每个受该级影响的域各落一行**（整表值；一级可同时变更 bench 与行域——两域各一行、同步号），evidence `proj_ore_merge#<级>#ore<k>`；board 派生行随每次行写自动逐级产生，**属预期流水**（逐步写设计的固有形态） | 同左 |
| 4 | 角色分支中合成未触及的行域 | rand | 值不变（标记，真值可能因角色奖励而变） | `proj_ore_mark_front_row#ore<k>` / `…_back_row#ore<k>` |

**None 域边界**：目标域值 `None`（未观察）→ **跳写不标记**（随机态标记对「本就未知」的域无信息增益；`logic_rand_fields` 语义不受影响）。抽中类型的域值为 None → 跳采样写、等观察覆盖（诚实缺失），其余域照常。board 无观察基座时派生跳过（现行为，`_resync_board_delta` 既有门）。

深拷贝纪律：工作列表元素一律 `snapshot_copy` 深拷（买牌路径浅拷贝共享对象的别名坑不继承，`buy_card.py` ⚠ 注在案）。

### 2.5 sim 接线

**炉先例形态（旁路直调，`cw_sim_engine.py::_apply_furnace` L407-426 同型）**——`apply_player_action` 主分派表**不动**（CollectOre 无现成分支、也不新增），引擎在炉所在的前置分派处新增 CollectOre 拦截：

```python
# cw_sim_engine.py 前置分派（与 CwActionFurnaceUseParam 分派同处）
if isinstance(action, CwActionCollectOreParam):
    return self._apply_collect_ore(eng, action)

def _apply_collect_ore(self, eng: _Eng, action: CwActionCollectOreParam) -> LogicOutcome:
    uses = eng.ore_uses + 1                      # 局内点矿动作单调序，1 基
    out = report_action_collect_ore_param(
        eng.gs, action, sig=logic_sig(group_id=f'act:sim@M1x/ore/{uses}'),
        rng=stream_rng(eng.seed, f'M1x/ore/{uses}'))
    if out.applied:
        eng.ore_uses = uses                      # 拒分支不耗序（与炉一致）
    return out
```

- `logic_sig` = `sim/cw_sim_base.py`（logic_action 族规范署名，actor = `SIM_ENGINE_ACTOR`='SimEngineV2'）；

- `eng.ore_uses` = 引擎局内点矿动作计数（`_Eng` 新字段，构造 0 起，`furnace_uses` 同型）；
- 采样即世界真值：sim 侧点晶矿零自算，掉落内容 = 上报函数采样结果直接落容器；
- 流键 `M1x/ore/{uses}` 满足流键硬约束「模块号 + 局内坐标」（`cw_sim_streams.py` 模块头），同局多次点矿序列自然推进。

### 2.6 关键取舍

- **采样 vs 纯标记 vs 期望值**：纯标记（值不变）sim 无法复用、连锁算不了；期望口径需分布校准（无）。采样两副面孔——实机=猜测（标随机等校准），sim=世界真值（免自算）——且与「逐动作上报函数 = 动作语义单一源」架构对齐。
- **直接容器逐步写 vs scratch 攒批**：作用链会越长越长、牵扯字段越来越多，攒批写回的 scratch 面失控；逐步写让流水粒度对齐游戏事件（一格一存）。代价 = 中断留半态：属推算代码 bug 场景，流水可见停在哪一步、下帧观察收口，可接受。
- **污染粒度 = 动作级入口判定 + 显式采样链**：不做逐字段数据流分析（复杂度不值，观察收口兜底）。
- **board 不显式标记**：派生量禁手写（`_resync_board_delta` 单一源纪律）；污染经行域表达 + 消费侧查行域（裁决 9）。
- **守卫先于采样**：level 缺读 / 席满在掷骰前整体拒，避免「摘了晶矿却采不出奖励」的半动作。

## 3. 边界

- 其他动作（买牌/卖/上阵/工具族/事件选择族）**零改动**——污染入口判定逐动作接入是后续批；买牌路径经 `on_step=None` 零行为变化。
- 策略器零改动（`CwActionObs` 消费门归策略批）；外循环、画面 op 零改动。
- 晶矿视觉识别（`OreSight` 读链）零改动。
- 实机验证候下批局前统一重启 MCP server（改了 Python 代码）。
