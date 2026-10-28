# 流程接缝（详设）

## 问题与约束

- 辖域：流程代码与 sim 后端的替换面——端口模块、操作基类覆写、观察生成器、运行器与桩、测试迁移。
- 总纲划给本篇的接口契约：`sim/cw_sim_ports.py` 端口形状、事件钩子契约、写通道单一、字段判据（`design.md` §2）。
- 硬约束：实机路径零行为变化（端口缺省关）；流程 op 体零改动（换父 + 基类覆写，不在 op 内写 sim 分支）；公共框架（`one_dragon`）零改动；`sr_od/operations` 共享层零改动（依赖方向：app 树「app 依一切」，禁共享层反向依赖 `application/currency_war`）。

## 方案

### 1. 端口模块 `sim/cw_sim_ports.py`

- 形状如总纲 §2。装配纪律：`install_sim_backend` 重复安装 raise（进程内单装配）；`uninstall_sim_backend` 幂等；测试 teardown 必卸（模块槽是进程全局，残留跨测试泄漏）。
- 模式复刻自 T-120 批 0 的 `cw_game_ports.py`（考古件：仅存 `.debug/temp` 旧工作树副本，未入现役 src）。**类型面按现役重推导**：旧协议引用的 `cw_state.GameState`/`ShopCard`/`Action`、旧 `PrepObservation` 形状、ADR-0462 相位键均为旧容器时代产物，全部退役；现役类型 = `kernel/cw_game_state.GameState` + 各屏 `CwScreenXxxObs` + screen_info 档名。
- 事件钩子槽落位（总纲事件钩子契约）：`kernel` 侧新增模块级槽（缺省 `None`），载**转移事件**与**事实事件**两类；广播点 = 对应上报函数/动作落地点写后；`install_sim_backend` 时由 SimBackend 订阅。实机缺省 `None` = 零开销零行为变化。转移封闭集盘点方法（确定性，非酌情）：以 `cw_action_registry` 注册表全量动作为底集，按 `screens/` 各篇 §5 终结/交回表筛「落地引发画面转移」者；**盘点附录在 3.1 交付**（消费 = 本批广播点接线 + 3.2 backend 订阅）。

### 2. `CwOperation` 基类 `operations/cw_operation_base.py`

- **换父清单**：`operations/` 树直继承 `SrOperation` 的全部类（2026-09-23 grep 实测 67）。**完成判据 = 换父后 grep `^class Cw\w+\(SrOperation\)` 零命中**，不以计数为判据。入口链（`cw_entry/` 4 个）一并换：sim 不跑入口链，换父零成本，避免「哪些换了」成为问题。
- **覆写面**：
  - `screenshot()`：sim → 返回哨兵帧（小空白 `ndarray`），不触 controller。框架每轮自动截图（`one_dragon/base/operation/operation.py::Operation._execute_one_round` → `self.screenshot()` → `last_screenshot`）无感运转。
  - `round_by_find_and_click_area()`：sim → 点击 = `screen_loader` 档案点位直成功（`node_clicked` 置位语义保留）；`until_find_all` = 端口 `visible` 问询，`until_not_find_all` = `visible` 取反（目标区域不可见才算过）；有 until 按实机同形返回 `round_wait`（「点了≠成了」，下一轮 until 问状态机取转移后真值；问询为假 = 继续轮询，sim 点击分支已成功不重发），无 until = `round_success`。实机 → `super()` 原样。
  - `round_by_find_area()`：sim → `visible` 应答。实机 → `super()`。
  - 其余在用助手（`round_by_click_area` / `round_by_ocr_and_click` / `scroll_area` / 拖拽封装等）：以 CW 树内 `round_by_*` / `screen_utils` 调用点 grep 全量清点，逐个归「sim 应答 / `super()` 透传」，清点表入本文件附录（实现期维护）。
- **读屏点改道**（观察分支唯一 op 触点）：每屏显式读屏点一行机械改——`obs = cw_sim_ports.sim_or_live_observation('货币战争-备战', lambda: 原读链())`；helper 住端口模块（装了后端 → `observe`，否则原读链）。接线随 3.3 各屏生成器落地逐屏进行（文件面 = `operations/cw_screen/` 观察 node）。「op 体零改动」精确口径 = 决策/动作/节点推进零改动，观察读屏点一行改除外。
- **直连 controller 旁路**（如 `prep_actions.py::PrepActionExecutor` 拖拽分支）：逐点加端口检查（installed → 机械执行分支静默成功，自上报照走）；运行器 controller 桩兜底。
- **controller 桩**（运行器装配）：`ctx.controller` 全接口触碰即 `AssertionError`（报「sim 模式触碰真实 IO」+调用栈）。双保险：①漏改的帧消费者在哨兵帧上真识别 → 恒未找到 → retry 耗尽 fail；②漏改的直连路径撞桩即炸。

### 3. 观察生成器

- 注册表：screen_info 档名 → `fn(backend) -> CwScreenXxxObs`；生成器从世界真值（容器 + 后端运行时）填结构体，零截图零识别。
- **写通道铁律**：生成器产物必须经 `kernel/cw_screen_report/` 同名上报函数落容器（与实机观察上报同一条写通道）；观察口径（字段映射/归一化/缺省语义）单一源在 report 消费端，生成器只产数据。
- **注册表键 = screen_info 档名（唯一）**；子态不设独立键——同档名子态（晶矿子态 / wait_one_one 变体 / 整店锁）由该档名生成器按状态机子态内部分派出对应观察产物。
- 金路径档名清单（M2，13）：备战（含晶矿子态、wait_one_one 变体）、商店、battle_wait、补给、投资环境、投资策略、简报、boss 简报、位面过渡、遭遇、开箱、巨星、planner；非金路径屏未注册 = sim 不会走到；**状态机呈现未注册屏 = 响错**（防静默失真）。
- `PrepObservation` 控制信号（shop_open / substate / event_overlay）由生成器随观察产出（状态机已知商店开合与 overlay 呈现态）。

### 4. 运行器与 harness（住 `sr-od-test/test/harness/`）

- 装配：真 `screen_loader`（生成器查档案点位）+ controller 桩 + 最小服务面 → `install_sim_backend` → 跑 `CwLoop`（round cap 防失控）→ `uninstall` 复位。
- `fast_sleep` 手法沿用测试仓现有 harness（框架等待旁路）。
- 策略器 = 真实 mandate_v1（MVP 全决策面在真流程上运转）；`install_obs_ports` 装配点照常接通。

### 5. 测试迁移

- `test_cw_sim_engine.py`：规则断言（收入/经验/发牌/结算/装备/offer）平移为 SimBackend 测试；驱动器测试（`_drive` / `simulate_run` 壳 / reset-step 协议）随引擎退役删除。
- `test_cw_collect_ore_rand.py`：晶矿采样断言平移（采样逻辑在 kernel 上报函数内，随动作分支迁移验证）。
- **其余涉退役/平移符号的测试文件一律平移或退役**，清点法 = grep 退役符号集（2026-09-23 清点含：`test_cw_sim_offer.py` / `test_cw_sim_actions.py` / `test_cw_sim_equips.py` / `test_cw_sim_nodes.py` / `test_cw_sim_opening.py` / `test_cw_sim_pool.py` / `test_cw_deploy_to_slot_semantics.py` / `test_cw_tool_use_report.py`）。
- 新增：M3 首局验收测试（判据见总纲 §2 里程碑）。

## 关键取舍

- **覆写放 CW 基类而非 `SrOperation`**：`sr_od/operations` 是共享层，反向 import CW app 树破坏分包方向；`CwOperation` 放 `operations/cw_operation_base.py`（app 树），端口引用合法。
- **哨兵帧 vs 跳过框架自动截图**：跳过需改框架轮协议（`screenshot_before_round` 是逐节点配置，无全局关）；哨兵帧让框架机制零改动运转，且与 controller 桩构成双保险。
- **薄协议 + 注册表 vs 35 方法肥协议**：新增屏 = 注册一个函数；协议签名不随屏数增长（T-120 旧协议 4 方法已随流程形态漂移作废，教训 = 协议形状取最小稳定面）。
- **生成器住 src/sim 而非测试仓**：生成器与生产类型（`CwScreenXxxObs`/`report_screen_*`/GameState 字段）同频演进，同树 import 期校验；测试仓只放「用 sim 的测试」与装配胶水（用户裁定 2026-09-23：MVP 不考虑批跑/A/B/统计，跨仓消费面不存在）。

## 附录 A：`round_by_*` / `screen_utils` / 直连 controller 调用点清点（3.1 实现期实测，grep 全量）

### A.1 `round_by_*` 助手清点（CW 树内调用点）

| 助手 | 调用点数 | 归宿 |
|---|---|---|
| `round_by_find_area` | 96（self 84 / `op.` 8 / `_op.` 4） | **CwOperation 覆写**：sim = 端口 `visible` 应答 |
| `round_by_find_and_click_area` | 46（self 36 / `op.` 10） | **CwOperation 覆写**：sim = 端口 `click_answer` + until 轮询分支本层收口 |
| `round_by_ocr` | 31（self 29 / `op.` 2） | `super()` 透传：哨兵帧真识别恒未找到 → retry 耗尽 fail；sim 金路径到达的屏随 3.3 读屏点改道逐点接 `visible` |
| `round_by_ocr_and_click` | 7 | `super()` 透传（同上） |
| `round_by_op_result` | 8 | `super()` 透传（纯结果转换零 IO，sim 可直接用） |
| `round_by_click_area` | 1（`cw_entry_enter`） | `super()` 透传（入口链 sim 不跑） |
| `round_by_find_area_binary` / `round_by_goto_screen` / `round_by_ocr_and_click_by_priority` / `round_by_ocr_and_click_with_action` / `scroll_area` | 0 | CW 树未用，不覆写 |

调用点分布在 `operations/`（覆写面覆盖）、`currency_war_app.py`（app 根 = 生产实机入口，sim 不经）与 `obs/cw_shop_refresh_obs.py`（非节点上下文，3.3 改道面）。

### A.2 `screen_utils` 直调清点

| 函数 | 调用点 | 归宿 |
|---|---|---|
| `screen_utils.find_area` | 1（`obs/cw_shop_refresh_obs.py`） | 观察域，3.3 读屏点改道面 |
| `screen_utils.get_match_screen_name` | 3（`kernel/cw_obs_core.py` / `operations/cw_screen/cw_screen_prep.py`） | 同上（sim 画面身份归 `screen_identity()`） |

### A.3 直连 `controller` 旁路清点（86 处，分组归宿）

> 口径：一处 = CW 应用树内一行 `ctx.controller.` 直连调用；复核 = 对 `src/sr_od/application/currency_war/**.py`（排除 `__pycache__`）跑 `Select-String -Pattern 'ctx\.controller\.'` 计行数（2026-09-23 实测 = 86）。

| 组 | 文件 | 归宿 |
|---|---|---|
| 拖拽分支（焦点守卫 + `DragCwChar`） | `prep_actions.py::drag_bench_to_sell` / `PrepActionExecutor._drag` | **本批 port 检查**：installed → 机械执行分支静默成功，自上报照走 |
| 动作 op 机械点击/拖拽 | `operations/cw_op/`（buy_card / collect_ore / open_box / open_bookcard / open_tome / level_up / start_battle / pick 族 / refresh_shop / tool_use / wear_equip）+ `_overlay_confirm.py` | 运行器 controller 桩兜底（触碰即炸）；sim 到达面随 3.2/3.4 联调逐点加 port 检查。wear/tool 的 owned/SIFT 读分支在触桩前先因哨兵帧识别失败自然 fail（未发出通道） |
| 画面 op 直连点击 | `operations/cw_screen/`（aha_equip / briefing / settle_confirm / armory_box / encounter / boss_briefing / battle_wait / consumable / item_detail / plane_intel / plane_transition / refresh_odds / supply_node） | 同上 |
| 入口链 | `operations/cw_entry/` | 桩兜底（sim 不跑入口链） |
| 拖拽原语本体 / dev / tools op | `operations/dev/drag_cw_char.py` / `operations/tools/harvest_invest_codex.py` | 桩兜底（生产拖拽统一经 prep_actions 已检查入口） |
| 观察补采截图 | `obs/cw_observation.py`（4 处） | 观察域，3.3 改道面 |
| 遥测录制 / loop 窗口检查 | `telemetry/cw_match_recorder.py` / `operations/cw_loop.py`（game_win） | 实机运维面/桩兜底 |

## 附录 B：转移事件封闭集盘点（3.1 交付；§1 盘点方法执行结果）

方法：底集 = `cw_action_registry` 注册表全量动作 + `report_node_advance` trigger 封闭集；筛 = `docs/develop/sr_od/application/currency_war/screens/` 各篇 §5 终结/交回表「落地引发画面转移」者。成员 = 18，广播点全部接于 kernel 上报函数 applied 出口（`kernel/cw_event_hooks.TRANSITION_EVENT_KINDS` 为代码层单一源；`@transition_event_on_applied` 装饰器 / `report_node_advance` 推进落账后）：

| kind | 广播点（上报函数） | 筛依据 |
|---|---|---|
| `settle_confirm` | `cw_game_state.report_node_advance` | flow/README §1 + screens/prep.md §5 |
| `supply_confirm` | 同上 | 同上 |
| `start_battle` | `cw_action_report/start_battle.py` | prep.md §5「备战访问终结」 |
| `pick_encounter` | `pick_encounter.py` | encounter.md §5「派发即终结」 |
| `pick_supply` | `pick_supply.py` | supply.md §5 |
| `pick_megastar` | `zero_writes.py` | megastar.md §5 |
| `pick_partner` | `zero_writes.py` | partner.md §5 |
| `pick_planner` | `pick_planner.py` | planner.md §5 |
| `pick_invest_env` | `pick_invest_env.py` | invest_env.md §5 |
| `pick_invest_strategy` | `pick_invest_strategy.py` | invest_strategy.md §5 |
| `pick_fortune` | `zero_writes.py` | fortune.md §5 |
| `pick_wish_trial` | `zero_writes.py` | wish_trial.md §5 |
| `pick_star_tome` | `zero_writes.py` | bookcard.md §5 |
| `pick_box_card` | `zero_writes.py` | box_pick.md §5 |
| `pick_expert_invite` | `zero_writes.py` | expert_invite.md §5 |
| `open_box` | `zero_writes.py` | prep.md §5（武装箱选择画面出现） |
| `open_bookcard` | `open_bookcard.py` | README §5.5（专家邀请函弹窗出现） |
| `close_shop` | `close_shop.py` | shop.md §5（商店 overlay 收起回备战） |

**筛落但不入集者（边界登记）**：
- `open_shop`：§5.3「备战环终结」命中筛，但生产路径不经注册表 op（terminal 承载行执行抛），开店点击走流程编排 = **click 源**，3.2 状态机经 `click_answer` 感知，不设 kernel 事件；
- 空决策/推进型画面 op 的点击转移（简报下一步 / BOSS 简报 / 位面过渡 / 位面详情 X / 中断挑战 X / 备战暗色锁定返回等）= click 源，同上不入 kernel 事件集；
- `refresh_shop` / `refresh_node_options` / `refresh_supply` / `refresh_invest_cards`：访问终结但画面档不变（无转移）；
- `buy_card` / `sell_bench` / `sell_deployed` / `deploy_move` / `wear_equip` / `level_up` / `level_up_shop` / `collect_ore` / `open_tome` / 工具原子七类 / `swap_deploy` / `obs`：非终结同屏动作；
- `pick_event`：零写族但生产不可达（策略器不发射）。

**事实事件现役成员**（`FACT_EVENT_KINDS`）：`board_changed`（deploy_move / buy_card / sell_bench / sell_deployed / wear_equip 落地写后）、`star_up`（buy_card 合成升星分支检出时；`detect_merge_upgrade` 布尔语义，单位身份由订阅方读容器）。`swap_deploy` 换位不改板面组成，设计列举外未接线。
