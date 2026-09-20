# 逻辑随机态采样落地·点晶矿（logic-rand-sampling）迭代设计

> 迭代 = 把逻辑随机态（`FieldSource='logic_rand'`）从内核基座推进到**首个动作落地（点晶矿）**，确立**采样语义 + 污染传递**两条纪律，作为后续随机动作（冶金炉/特权卡/好运令牌/投资卡随机授予）逐批迁移的范式。读者 = 无会话历史的工程师/智能体，照本 spec 机械执行，勿重新设计。路径根 = `src/sr_od/application/currency_war/`；测试仓 = `sr-od-test/`（独立 git 仓，单独提交）。
> 基座已落地（主仓 commit `d24585b7d` / 测试仓 `7c6e1d4f`，2026-09-20）：`kernel/cw_game_state.py` 的 `FieldSource` 增 `logic_rand`、`write_logic_rand()` 写口、`observe()` 随机旁路（差异只落 `logic_rand_outcome` 台账行，无告警无安灯）、`logic_rand_fields()` 查询口。
> 用户裁定（2026-09-20，会话）：见 §0；游戏机制口述（点晶矿掉落规则）同源，证据分级 = 口述。

## 0. 已定裁决（禁重开）

1. **随机态语义 = 采样语义**：动作上报函数**真掷一次随机**，把采样结果当作真实发生的奖励走完整确定性链写入容器。抽中类型的域写**采样值**；未抽中类型的域**值不变、仅翻来源**（实机上采样是猜测，真奖励可能是另外两种，观察前 bot 不知道哪些域真变了）——三个类型影响域的**并集**全部标 `logic_rand`。
2. **点晶矿掉落规则**（用户口述 2026-09-20）：点开晶矿 = **金币 / 装备 / 角色** 三选一。金币 1–5 随机；装备在**简易装备池**随机（装备注册表 category=`简易` 全集，`data/cw_equipment_data.py`）；角色在**当前概率表**上随机（随等级费用概率表 = `data/cw_shop_odds.py::REFRESH_PROB`，sim 发牌同源基线 `sim/cw_sim_shop.py::effective_deal_probs`；费用档内抽名 = `data/cw_chars.py::chars_by_cost` 均匀）。
3. **满栏时点击晶矿无效、无法开启**（用户裁定）：上报前置门 = 备战席无空位 → `applied=False` 零写（与游戏侧行为同源；策略发射位的席满让路门为第一道防线，`fields.md` §4.2 CollectOre 前置谓词，本门是上报层同口径双保险）。
4. **直接在容器上逐步写**（废弃「scratch 攒批、一次性写回」）：上报函数内的每个语义步立即落容器，**每步 = 一次写入 = 一行状态流水**（备战多一个角色存一次；触发 3合1 存一次；再触发再存一次）。遥测无新增机制——现有流水按写落行，设计后果只是把动作分解成逐步写。
5. **参数只落写入口，纯计算函数不加**：`_merge_bench` 等纯变换保持纯函数；`_merge_bench` 加**可选步回调**（每完成一级合并调用一次，调用侧经回调落容器），缺省 `None` = 现行为（买牌路径零改动）；board 派生挂钩（`_write_logic_frame → _resync_board_delta`）在行域写为随机态时**继承随机态**。
6. **跨动作污染 = 上报入口判定**：上报函数入口检查「本次要读的输入域中是否有 `logic_rand`」→ 有则本动作全部产出标随机。**本批只接点晶矿**（其写入面按 §2.4 规则直接落，入口判定口本批建成供后续动作逐批接入——逐动作迁移是后续批，见 §3 边界）。
7. **RNG 注入**：上报函数加可选 `rng` 参数；实机不传 = 未播种 `random.Random`（采样是猜测，标随机态）；sim 传引擎流键派生 rng（流键 = `M1x/ore`，惯例单一源 = `sim/cw_sim_streams.py::stream_rng`）。
8. **sim 复用边界**：**动作内随机**全部住上报函数——sim 经 `sim/cw_sim_actions.py::apply_player_action` 委托同一函数，采样即世界真值，sim 零自算；**非动作环境事件**（节点间自动发牌 `M05/deal`、位面 boss `M20`、战斗结算）不是动作、无上报函数，留守 sim 侧自己的采样。
9. **board 跟随行域表达污染**：board（羁绊计数，派生量）不做独立标记写（派生量禁手写纪律不破）——行域实际变化时派生行自动继承随机态；行域仅标「值不变」时 board 不动，board 的可信度由消费侧查行域（`any_logic_rand(('front_row','back_row'))`）判定。

### 0.1 建模假设档（披露面，实机待核）

| 假设 | 内容 | 披露键 |
|---|---|---|
| 三选一等概率 | 金/装备/角色各 1/3（权重未实测） | `ore_type_uniform` |
| 金 1–5 均匀 | 区间用户口述，分布形态未实测，按均匀 | `ore_gold_uniform_1_5` |
| 角色星级 = 1 | 晶矿掉落角色按 1★ 采样（直出高星无记载，同 sim 发牌 U12 口径） | `ore_char_star1` |
| 不受轮岗翻倍档影响 | 晶矿掉落概率表用基线 `REFRESH_PROB[level]`，不挂轮岗重掷（无依据不加规则） | `ore_no_rotation_tier` |

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
| 1 | `_merge_bench` 步回调 | `kernel/cw_merge_simulate.py` | 签名加 `on_step: Callable[[], None] | None = None`：**每完成一级合并**（升星/置 None/装备继承落地后）调用一次；`None` = 现行为。调用侧经回调把工作列表当前状态落容器（闭包自持写入通道与步骤计数，merge 本体不感知容器） |
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

### 2.4 点晶矿上报改造（`kernel/cw_action_report/collect_ore.py`）

签名加 `rng: random.Random | None = None`（None = 模块级未播种 Random，实机；sim 传 `stream_rng(seed, 'M1x/ore')`）。

**守卫前置（全拒 = 零写，先于任何写）**：spheres 未观察（现行为）/ 载荷无交集（现行为）/ **bench 无空位**（新，`applied=False 'bench_full_no_open'`，裁决 3）/ **level 缺读**（新，`applied=False 'level_unread'`——角色采样需当前等级，宁缺勿造）。

**写序**（每步一行，同组 `group_id`；rand = `write_logic_rand`，logic = `write_logic`）：

| 步 | 域 | 来源 | 值 | evidence |
|---|---|---|---|---|
| 1 | spheres | logic | 载荷坐标精确摘除（现行为不变） | `proj_collect_ore_drop` |
| 2 | 未抽中类型的域（gold/equips/bench/front_row/back_row 中不属于抽中类型的） | rand | **值不变**（标记） | `proj_ore_mark_<field>` |
| 3a | 抽中金：gold | rand | 现值 + N（N ∈ 1..5） | `proj_ore_reward_gold` |
| 3b | 抽中装备：equips | rand | 现值 + [采样件] | `proj_ore_reward_equip` |
| 3c | 抽中角色：bench | rand | 工作列表落位后整表（`bench_place`，深拷贝元素防别名） | `proj_ore_reward_char` |
| 3c+ | 触发合成时：bench/front_row/back_row | rand | **每级合并落一行**（`_merge_bench(on_step=…)`，步骤计数进 evidence `proj_ore_merge#N`）；board 派生行自动继承 rand | 同左 |
| 4 | 合成未触及的行域（角色分支行域无变化时） | rand | 值不变（标记，真值可能因角色奖励而变） | `proj_ore_mark_front_row`/`…_back_row` |

深拷贝纪律：工作列表元素一律 `snapshot_copy` 深拷（买牌路径浅拷贝共享对象的别名坑不继承，`buy_card.py` ⚠ 注在案）。

### 2.5 sim 接线

`sim/cw_sim_actions.py::apply_player_action` 的 CollectOre 委托分支传 `stream_rng(eng.seed, 'M1x/ore')`（形参随引擎现有 rng 传递惯例对接）。sim 侧此后点晶矿零自算：上报函数采样即世界真值。

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
