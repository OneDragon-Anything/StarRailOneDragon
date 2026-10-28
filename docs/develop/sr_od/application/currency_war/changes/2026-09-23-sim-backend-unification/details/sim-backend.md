# SimBackend（详设）

## 问题与约束

- 辖域：sim 世界本体——状态结构、画面状态机、overlay 触发层、世界规则件、随机体系、与旧引擎的替换关系。
- 总纲划给本篇的接口契约：`sim/cw_sim_ports.py` 端口形状、事件钩子契约、写通道三条各一、容器字段判据（`design.md` §2）。
- 硬约束：一实例一局；确定性 = 全部采样由 seed 派生；kernel 单一源不复制——规则件语义缺口 = 补 kernel（生产双端受益），禁 sim 第二份实现。

## 方案

### 1. 结构与字段收敛

`SimBackend` 为 dataclass，组合持有 `gs: GameState` + 私有运行时字段。总纲字段判据逐项落位：

**收敛进容器（消灭双账）**：

| 旧 `_Eng` 字段 | 去向 | 写语义 |
|---|---|---|
| `plane` / `round_num` | `gs.node`（NodeKey） | 进节点/推进时写，与实机画面 op 锚定（`kernel observe_node_anchor`）同构 |
| `options` / `supply_opts` / `encounter_opts` / `box_cands` / `ores` | 容器各 `*_opts` 槽 | 经生成器 + `report_screen_*` 通道送达（与实机观察上报同一条写通道），后端不私持副本 |
| `streak_unsigned` | 由容器带符号连胜派生 `max(signed, 0)` | 派生读，不设第二账 |

**新增容器 Field（实机可观察/影响玩法，双端受益）**：

- `pending_loss`：败态挂账（`LostNodeRef`）；写端 = 战斗结算失败分支；消费 = 轮首收入败补支（U04 口径，`sim/cw_sim_income.py` 模块头申报）。
- `shop_locked`：整店锁；v1 恒 `False` 语义保留（旧裁定②：动作词表无锁通道，首版恒解锁 + 披露），字段先行。
- `diamond_count`：宝钻计数（UI 可见）。

**留 SimBackend 私有（实机不可观察的簿记/机器）**：

- `seed` / `cfg`（RunConfig）；画面状态机；`excluded_invest` / `excluded_env`（offer 全程去重采样簿记，U07③）；`overlay_queue`；`planner_fired`（一次性标志）；`furnace_uses` / `ore_uses`（随机流键坐标簿记，非游戏事实）；`disclosures`（未建模申报面）；局结果面（`hp_trail` 等，消费方 = 运行器断言）。

### 2. 画面状态机

- 状态 = `(screen_name, 载荷)`；`screen_name` ∈ screen_info 对局屏档名（权威 = 各画面建档，`cw_screen_state.CW_IN_MATCH_PREFIX` 域）。
- **转移源两类**：
  1. **上报事件钩子**（总纲事件钩子契约）：终结动作族（start_battle → 战斗等待；settle_confirm / supply_confirm 经 `report_node_advance` → 节点推进）；pick 族确认 → 画面交回（交回目标权威源 = `screens/` 各篇 §5 终结/交回表）；开箱动作落地 → 箱面。转移事件重入幂等（同一终结动作重复上报不二次推进）。
  2. **节点推进序列**（平移旧引擎 M 序列，`cw_sim_engine.py` 引擎头注）：写 `gs.node` → 轮首收入（kernel `round_start_income` 三分支：常规/补给·奖励/败补 U04）→ 位面开局环境金 → 商店自动全刷（整店锁跳过）→ overlay 队列检查 → offer 日程检查（U07 固定轮次 + 联席决策；overlay 让路选定后复走本检查，让路不吞 offer 槽）→ 按节点类型呈现对应屏（prep / supply / encounter / boss；reward 节点 = 备战档晶矿子态，键形裁决 = `details/flow-seam.md` §3）。
- 节点经验在节点推进时入账（`apply_node_xp` 平移，NODE_XP_BY_TYPE 表原样）；连胜转移（`streak_income_after` / `streak_signed_after` 平移）在战斗结算后。
- **初始序列**（reset）：词缀/boss 名单采样并写容器（`gs.plane_bosses` 等）→ 简报屏（词缀 + boss 载荷）→（`env_present` = 真）投资环境屏 → wait_one_one → P1r1 对应屏。进入/退出条件权威源 = `screens/` 各篇；P3 进场即局终（现役 `p3_unobserved` 口径）。
- until 语义：点击分支返回 `round_wait` 后，下一轮 until 问询 = 状态机可见性——上报已同步转移画面，故下一轮即为转移后真值（与实机「观察赢」同形，语义不降级）。

### 3. overlay 事实触发层

- **机制**：世界事件 → 触发评估器（每 overlay 一个，消费世界事实）→ `OverlayQueue` 入队 → 状态机模态呈现（压住底层画面，选完交回）。评估器接口 = `fn(event, backend) -> overlay_kind | None`，按 kind 注册表；`sim/cw_sim_overlay.py::OverlayQueue` 结构平移。
- **一期目录**（用户裁定 2026-09-23）：
  - 开箱：动作触发——开箱动作落地 → 箱面 + 候选生成；
  - 巨星（盛会之星）：事实触发——消费事实事件（板面组成变化类：deploy / 买牌合成 / sell / wear 落地后广播，总纲事件钩子契约）评估盛会之星羁绊计数，跨阈值 → 入队；阈值与判据语义源 = `data/cw_factions.py` + `docs/game/currency_war/` 玩法文档巨星节；
  - planner（银狼首次升 2 星）：事实事件（升星类）消费；判据 = `cw_sim_special.py::planner_overlay_due` 平移，一次性标志 = `planner_fired`。
- **其余族**（partner / expert / fate / aha / hack）：触发条件实机零档 → 占位披露（`OVERLAY_PARAM_PENDING` 族，现役口径），评估器缺位 = 不入队；**这是数据缺口不是架构豁免**，补档后逐个落评估器（二期目录）。

### 4. 世界规则件（自旧引擎平移；语义零改）

| 旧模块 | 归宿 |
|---|---|
| `cw_sim_income.py` | 平移 backend（轮首收入/连胜转移）；`income_modifiers_of` 消费 kernel `aggregate_economy` 不变 |
| `cw_sim_actions.py` | `apply_player_action` 退役（动作分支改由 op → 上报函数族承担，与实机完全同构：实机 op 怎么组装 `executed`，sim 路径同一段 op 代码同法组装）；`xp_apply_amount` / `apply_node_xp` 平移 backend |
| `cw_sim_shop.py` | kernel `sample_shop_deal` 不动；`deal_shop`（自动全刷的世界写）平移 backend；`effective_deal_probs` / rotation 平移；`refresh_cost_for` 随 sim 私有动作分支退役 |
| `cw_sim_offer.py` | offer 采样（`sample_strategy_offer` / `sample_env_offer`）平移 backend；`apply_env_pick` / `apply_strategy_pick` / `inject_choices` 退役（替换 = pick 动作走 op → `report_action_pick_invest_*` → `gain_invest_*` 获得链）；`QUALITY_REWRITE_ENV_NAMES` 迁 kernel 常量位（游戏事实，效果建模批消费） |
| `cw_sim_nodes.py` | 选项生成（箱候选/补给/遭遇参数/晶矿奖励）平移 backend；`apply_*_pick` 分支退役（pick 动作走 op → `report_action_pick_supply` / `pick_encounter` / `collect_ore` → 获得链） |
| `cw_sim_battle.py` / `cw_sim_enemy.py` / `cw_sim_opening.py` / `cw_sim_special.py` / `cw_sim_streams.py` / `cw_sim_run_config.py` / `cw_sim_base.py` / `cw_sim_plane_schedule.py` | 平移保留（coarse 战斗结算 / boss 名单 / 开局种子 / 特殊角色规则 / 流键 / 配置 / 证据签名 / 节点日程）；`RunConfig.enemy_affixes` 降级为 override（定向测试用），常规词缀由 reset 采样（流键 `reset/affixes`） |
| `cw_sim_equips.py` | 动作分支退役：kernel `cw_action_report/tool_use.py` 七上报已覆盖炉/精密扳手/扳手（tool-gain-report 迭代在库），装备/工具动作走 op → 上报函数族与实机同构；纯披露键（`UNMODELED_GRANTS`）迁 backend |
| `cw_sim_engine.py` / `cw_sim_phase.py` | **退役删除**（`CwSimEngine` / `_Eng` / `RunResult` / `StepResult` / `simulate_run` / `CwSimPhase`）；位面开局环境金分支（`_apply_env_plane_gold`）平移进节点推进序列（读 kernel `INVESTMENT_ENVS`）；局结果面归宿 = backend 结果面 |
| `sim/cw_replay.py` | 不动（journal 重放，不依赖引擎） |

## 关键取舍

- **组合 vs GameState 子类**：子类制造第二容器形状，决策输入形状随运行模式漂移，边界侵蚀无类型系统兜底；且 Field 通道（observe/evidence/缺陷台账/schema）与裸属性两套状态纪律混于一体。组合后 kernel 与流程只见纯 `GameState`（用户裁定 2026-09-23 定名 SimBackend）。
- **转移事件挂 kernel 钩子槽 vs op 内 port 通知**：后者给数十个 op 加 sim 分支，违反「op 体零改动」；kernel 槽缺省关先例成熟（`set_defect_sink`），因果方向正确（上报 = 世界变化 → 转移）。
- **相位载荷写容器而非后端私持**：消除双账；pick 族决策入口本就容器零参读，sim 世界与实机世界对决策呈现同一形状。
- **动作分支经上报函数族而非 sim 私有转移函数**：现役契约「期望态两执行面同源」（`flow/projection_contract.md` §3.6）的自然延伸；sim 私有动作语义即第二真相源，缺口补 kernel。
