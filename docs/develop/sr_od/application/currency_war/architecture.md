# 货币战争 · 模块全景图

> 本文回答两个问题:**这个玩法有哪些功能模块**、**每个模块负责什么(不负责什么)**。分层归属以代码树为准(`src/sr_od/application/currency_war/`),表内条目为代表例举(全量以对应目录为准),职责以各模块 docstring 与正本文档为准。阅读顺序:先看全景图建立分层直觉,再按需查逐层职责表。

## 一、分层全景图

```text
                 ┌─────────────────────────────────────────┐
                 │ 入口编排层                                │
                 │  currency_war_app  应用组装·单跑道        │
                 │  cw_entry/*   入局·恢复·位面情报           │
                 │  cw_loop       对局循环:节点流转/看门狗/   │
                 │                重派防线                   │
                 └────────────────────┬────────────────────┘
                                      │ 按节点类型分发画面 op
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 画面 op 层(operations/cw_screen,一画面一 op)                  │
│   两 node 形态(直继承 SrOperation):观察(门+读屏+            │
│   report 落容器)→ 决策动作(重入裁决+决策+动作,round_wait 循环)│
│   备战·商店·战斗等待·伙伴·遭遇·投资·补给·结算·位面转换·弹窗族     │
│                                                              │
│   观察解析工具箱(obs/,观察侧解析设施,一屏一解析器):             │
│     备战屏 read_game_state·节点选项·结算屏·简报屏·商店对账        │
│     角色识别 SIFT·CV 工具·多源仲裁·恢复锁 …(入口链/动作 op/      │
│     kernel/档案有少量复用)                                     │
└────────┬──────────────────────────────────┬─────────────────┘
         │ ①观察态上报(观察边界)              │ ③动作提案落定,
         ▼                                  │   调用动作 op 执行
┌────────────────────────────────┐         │
│ game state 内核层(kernel/)      │         │
│   GameState 容器                │         │
│   (观察态/逻辑态/未观察 三态)     │         │
│   apply_* 单一转移函数族         │         │
│   cw_reconcile 观察边界对账·锚定 │         │
│   领域模型族(经济/阵容/意向/     │         │
│   事件/装备/合成/词表/注册表…)    │         │
│   cw_exec_state 域函数/节点台账   │         │
└──┬─────────────┬───────────────┘         │
   │ ②策略消费口  ▼                          │
   │ (唯一) ┌─────────────────────────────┐ │
   │        │ 策略层(mandate_v1)           │ │
   │        │  mandate/flow 决策核         │ │
   │        │  shop/encounter/entry/      │ │
   │        │  sell_gate/economy_cycle    │ │
   │        │  criteria 判据·statefn 状态函数│ │
   │        │  mandate_state 跨段状态记忆   │ │
   │        └──────────────┬──────────────┘ │
   │                       │ ③动作提案 ──────┘
   │ ④动作上报              ▼
   │ (apply_* 直写)  ┌────────────────────────────────┐
   └────────────────►│ 动作 op 层(operations/cw_op)     │
                     │  动作执行/注册表:买/卖/升/刷/     │
                     │  关店/开卡/装备全穿/定向清场/      │
                     │  商店动作编排                     │
                     └──────┬───────────────────────────┘
                            │ ⑤执行(点击/拖拽)
                            ▼
                     ┌────────────────┐
                     │ 环境             │
                     │ 真机画面 /        │
                     │ sim 模拟画面      │
                     └────────┬────────┘
                              │ 画面变化 → 回到画面 op ①
```

四条主线读图:

1. **观察线**:画面 op 入口观察(经 obs/ 解析工具箱)→ ①观察态上报进 GameState → 观察边界对账(cw_reconcile)。
2. **决策线**:策略层经唯一消费口②读 game state → ③动作提案交回画面 op → 画面 op 调用动作 op 执行。
3. **动作上报线**:动作 op 执行后向 game state 上报动作 → game state 经 apply_* 族独占写逻辑态。
4. **记录线**:GameState 初始化开启遥测 → 随局写 state 流水 → 局终收口装配对局档案(sim 局同构)。

职责铁律(画在图里的规矩):对账只发生在观察边界且由 game state 执行;逻辑态写入由 game state 独占(动作 op 只上报动作);策略消费口唯一 = game state;sim 只模拟环境,不评判策略。

## 二、入口编排层

| 模块 | 负责 | 不负责 |
|---|---|---|
| `currency_war_app.py` | 应用五件套组装、把对局循环接入框架 app 体系、单跑道约束 | 具体对局逻辑 |
| `operations/cw_entry/*` | 入局流程(从大厅进对局)、残局接管与恢复、位面情报采集;是 run 领取的入口链 | 对局内的节点决策 |
| `operations/cw_loop.py` | 对局主循环:按节点类型分发画面 op、看门狗、op 失败重派防线(外环防线)、局终收口钩子 | 任何策略判断;画面内交互(归各画面 op) |
| app 根级:`prep_actions.py` / `decision_assembly.py` / `cw_screen_state.py` | 备战决策环执行器(flow 层「动作执行」主干件,被 cw_screen_prep 消费;停机短路防线在此,执行器抛出交回外循环)/ 实机观察→Snapshot 装配半部 / 轻量画面状态判定(入口链兜底复用) | 具体判据(归策略/画面层) |

## 三、画面 op 层(operations/cw_screen)

**公共件**:

| 模块 | 负责 |
|---|---|
| `operations/decision_frame_hooks.py` / `operations/settle_collect_hooks.py`(两件住 operations/ 直下,非 cw_screen/) | 决策帧/结算屏的留证钩子(证据帧采集) |
| `cw_flow_const.py` / `_overlay_confirm.py` | 流程常量、overlay 确认公共件(画面 op 无共享基类:每画面独立类直继承 `SrOperation`,两 node 形态 = screens/[op-layer.md](screens/op-layer.md) §1) |

**画面 op(一画面一文件,职责 = 该画面的识别、交互、把观察态上报 game state、调用动作 op 执行)**:备战(`cw_screen_prep`,备战环:部署/卖/移位/装备/升级的执行环)、商店(`cw_screen_shop`,两 node:入口观察 + 单动作决策循环)、战斗等待(`cw_screen_battle_wait`)、选择伙伴(`cw_screen_partner`)、遭遇(`cw_screen_encounter`,难度档选择+刷新)、投资策略/环境(`cw_screen_invest_strategy`/`cw_screen_invest_env`)、补给(`cw_screen_supply_node`)、结算族(`cw_screen_briefing`/`boss_briefing`)、位面转换与情报(`cw_screen_plane_transition`/`plane_intel`/`plane_detail`)、装备/道具弹窗族(`aha_equip_pick`/`emblem_detail_popup`/`item_detail_popup`/`role_detail_overlay`/`shop_card_detail`;原 `equip_pick` 随选择装备屏误判退役删除,2026-09-22)、宝箱族(`armory_box`/`box_pick`/`fortune`)、书册(`cw_screen_bookcard`)、巨星(`cw_screen_megastar`)、试牌(`cw_screen_wish_trial`)、专家邀请(`cw_screen_expert_invite`)、中断对话框(`cw_screen_interrupt_dialog`)、其他推进件(`next_button`/`wait_one_one`/`deploy`/`deploy_not_full`/`planner`/`refresh_odds_popup`/`consumable_overlay`/`prep_locked_return`)。

**观察解析工具箱(obs/,观察侧解析设施,一屏一解析器)**:备战屏(`cw_observation` read_game_state 容器直写+轻量回执、`cw_observe_full` 全面识别组装、`cw_identity_obs` SIFT 视觉身份、`cw_faction_obs` 羁绊面板、`cw_back_layout` 后排布局)、节点族(`cw_node_obs` 遭遇/补给/巨星/伙伴选项、`cw_node_reader` 节点行类型)、结算屏(`cw_settlement_obs`)、简报屏(`cw_briefing_obs`,敌人词缀+位面首领)、商店(`cw_shop_obs` 开态对账、`cw_shop_refresh_obs` 刷新钮现场读)、装备/角色(`cw_equipment`、`currency_war_char_id` SIFT 角色识别)、公共件(`currency_war_cv` CV 工具、`cw_arbitration` 多源仲裁、`cw_resume_lock` 恢复局检测、`recognizers/*` 画面识别器注册)。入口链、动作 op、kernel(遭遇选档)、档案记录器有少量复用。

## 四、动作 op 层(operations/cw_op)

动作 op = 策略动作提案的**执行器**:接收画面 op 转交的动作提案,执行画面交互(点击/拖拽),然后**向 game state 上报动作**(逻辑态由 game state 经 apply_* 族独占写入;动作 op 自身不记账)。下表为代表例举,全量执行器清单 = [screens/README.md](screens/README.md) §4。

| 模块 | 负责 |
|---|---|
| `cw_action_registry.py` | 动作注册表单一源(`action_op_for`/`action_op_class_for` 全动作唯一注册点;终结判定读 op 类 `terminal`/`terminal_wait` 属性)。动作 op 无共享基类:各 op 独立直继承框架 `SrOperation`,执行后 op 内自上报 |
| `cw_buy_card_action.py` / `cw_close_shop_action.py` / `cw_prep_sell_bench_action.py` / `cw_prep_level_up_action.py` / `cw_refresh_shop_action.py` | 买牌/关店/卖备战/升级/刷新执行器(卖备战/升级两类 = 商店/备战共用词表单一注册行,注册行指备战 op) |
| `cw_op_open_shop.py` / `cw_wear_equip_action.py` / `cw_tool_use_action.py` + `prep_actions.py` 机械原语 | 开商店/装备穿戴/工具执行器(装备/工具 = 动作原子 `CwActionWearEquipOp`/`CwActionToolUseOp` + `prep_actions.py` 机械原语 `_equip_slot_drag_point`/`_owned_grid_locate`) |
| `cw_shop_action_ops.py` | 商店单动作 op 集 + 守卫断言 `guard_proposal_vs_expected`(提案动作在期望态中须存在且未被消费,非法返回响亮暴露) |

## 五、策略层(strategies/impl/mandate_v1)

策略 = **读 game state、产出动作**,不读屏、不点鼠标。入口 = `flow.py::decide_shop_action` 等包装(mandate 核唯一包装口)。

| 模块 | 负责 |
|---|---|
| `mandate.py`(决策核) | 各画面的决策逻辑:给定 game state,按骨架义务+经济判据产出动作或终结动作 |
| `flow.py` | mandate 核的包装入口:未观察门(关键信息未观察 → 关店回备战)在此 |
| `assembly.py` | 决策视图装配(从 game state 组装决策输入) |
| `shop.py` | 商店期决策面(买/刷/关;跨段状态 substrate 声明所在) |
| `encounter.py` / `entry.py` / `economy_cycle.py` / `sell_gate.py` / `bridge.py` / `turn_state.py` | 遭遇选档、入局决策、经济周期、卖出闸门、桥接、轮内状态 |
| `mandate_state.py` | 跨段状态:策略自己的记忆(为何关店/备战要做什么/何时重开) |
| `criteria/*` | 判据族(买/卖/升/刷/囤货的量化判据) |
| `statefn/*` | 状态函数族(预算/视野/收入/利息/死亡速率/赔率/谓词……数学模型的函数化) |
| `proof.py` / `audit/*` | 数学命题的证明面与审计面 |
| `adapter.py` / `cw_strategy.py` / `cw_strategy_manager.py` / `pick_bias.py` | 策略接口适配与策略管理 |

## 六、game state 内核层(kernel/)

### 容器与记录(职责铁律的承载者)

| 模块 | 负责 |
|---|---|
| `cw_game_state.py` | **GameState 局内容器**:每字段观察态/逻辑态/未观察三态;开局种子底座(冷建 rand 播种)+ 锚定闩 `prep_anchored` + 择道口 `anchor_aware_write`(fields.md §2.6);动作语义单一源 = `kernel/cw_action_report/` 上报函数族(每动作一文件 `report_action_<snake>_param`,op 自上报后由函数族独占写逻辑态;零写族 = `zero_writes.py`);局容器建立时开启遥测装配 |
| `cw_state_journal.py` | state 状态流水落盘(StateJournal:内存缓冲+批量 flush;装配口 `install_state_telemetry`/`ensure_journal_assembly`) |
| `cw_reconcile.py` | 观察边界对账:观察态 vs 逻辑态比对与仲裁、星级锚定、槽号健康不变量、bench 写回 |
| `cw_exec_state.py` | 战斗域领域模型与纯函数宿主(无状态面):`apply_confirm_effect`(dict 确认族到账推进;动作类效果已收编各 op 自上报函数)、槽位语义 helpers(`BenchSlot`/`Unit` 槽位运算/物理坐标↔表下标换算)、位面节点台账三访问函数(台账值载体住 `cw_game_state.py`,本模块转发保持 import 路径) |
| `cw_strategy_session.py` | 策略会话载体(session:策略侧对象的身份与生命周期) |

### 领域模型族(纯逻辑,被策略与容器消费)

| 族 | 模块 | 一句话职责 |
|---|---|---|
| 经济 | `cw_economy`(经济/等级/节奏骨架)、`cw_env_economy`(投资环境估值)、`cw_reward_node`(奖励节点纪律判据)、`cw_difficulty_account`(难度账本) | 金/经验/利息/刷新成本与价值评估的纯函数模型 |
| 阵容与卡 | `cw_comps`(阵容库+评分)、`cw_card_identity`(卡身份分层)、`cw_system_cards`(体系卡)、`cw_line_defs`/`cw_line_switch`/`cw_bridge_pool`/`cw_recipe`/`cw_transition`(线/配方/过渡) | 阵容识别、评分与线管理的判断层数据与纯函数 |
| 意向与事件 | `cw_intention`(终局意向)、`cw_events`(投资 3 选 1/遭遇/补给/巨星决策核)、`cw_encounter_selection`(遭遇选档判定)、`cw_registry`(决策注册表) | 事件类节点的决策判据 |
| 装备 | `cw_bench_equips`/`cw_bond_equips`(装备跟踪/羁绊口径)、`cw_equip_env`(装备环境信号)、`cw_equip_value`(装备价值)、`cw_equip_wear_plan`(穿戴计划)、`cw_affix_effects`(词缀效果注册) | 装备域的跟踪、估值与计划 |
| 战斗 | `cw_battle_calib`(战斗校准)、`cw_deploy_logic`(deploy 围栏/底线门/换血与补位判定;选人与落位计划单一源 = 策略层 `mandate_v1/deploy_plan.py`,sim 与 op 共用)、`cw_launch_admission`/`cw_launch_arbitrage`(发射准入/仲裁)、`cw_hp_policy`(hp 门)、`cw_first_passage`(首达生存概率) | 战斗结果的模拟与发射决策 |
| 观测支撑 | `cw_obs_core`(OCR 公共设施)、`cw_observe`(统一日志/截图)、`cw_anchor`(流程转点观测锚)、`cw_overlay_registry`(overlay 生命周期注册) | 观测基础设施 |
| 合成与推演 | `cw_merge_simulate`(合成引擎)、`cw_vocab`(统一动作词表)、`cw_prep_expect`(备战购买意图载体)、`cw_prep_actions`(备战域 kernel 件) | 期望态推演与备战域公共件 |
| 其他 | `cw_performance`(观测反馈/死局检测)、`cw_run_allocator`(跨局分配)、`cw_decision_trace`(决策行发射)、`cw_discipline_rules`(血预算停手/危机带判据族)、`cw_plane_table`(节点日程标定)、`cw_investments`(投资领域模型)、`cw_effect_inventory`(在场效果清单)、`cw_plugins`(插件注册)、`cw_code_hash_gate`(起局码哈希结构闸)、`cw_telemetry_exit`(遥测上行出口钩子位)、`cw_survey19_hooks`(二轮扫描落地件)、`cw_opening_hp`(开局血量先验) | 各行括注即一句话职责;细节见 kernel/ 各模块 docstring(全量以 kernel/ 目录为准) |


## 七、遥测与档案层(telemetry/)

> 本表为代表例举,全量 = `telemetry/` 目录。

| 模块 | 负责 |
|---|---|
| `state.py` | run 生命周期(铸造/领取/收口;装配已归 GameState 初始化);结算三项遥测行 |
| `match_archive.py` | 对局档案:段归局、game_id 派生、切片装配、水位线 |
| `schema.py` / `query.py` | 遥测 schema 与查询视图族 |

## 八、sim(游戏后端)

sim = 游戏本体的单局模拟器（「游戏后端」）：给定局级输入，按游戏规则推演一局的容器状态演化，对流程的动作与画面请求产出应答。驱动反转 = 根本裁决：真流程（外层循环 + 画面 op + 动作 op + 策略器）当驱动者，装上后端即在同一套流程代码里跑 sim 世界；与 live 共用同一容器（`GameState` 单例）、同一规则核（kernel/data）与同一写通道（上报函数族），动作拒绝语义在上报函数腿内，后端不自判拒绝。策略效果的批量评估/A/B/统计工具不在 sim 本体内（现不存在，sim-design §8.3），决策回放为 sim 之上的独立工具。

世界后端本体 = `cw_sim_backend.py::SimBackend`（dataclass 组合持有容器 + 后端私有运行时，一实例一局：画面状态机/世界规则件编排/事件接线/局结果面，结构正本 = sim-design §2-§4）。按域分模块（除节点日程真值表住 kernel 外，均以 `cw_sim_` 前缀命名）：

| 域 | 模块 | 负责 |
|---|---|---|
| 后端本体 | `cw_sim_backend.py` | SimBackend：画面状态机、世界规则件包装与编排、事件接线、确定性采样、局结果面 |
| 基座 | `cw_sim_base.py` | 容器写入签名/证据标签共用面（`sim:engine:` 前缀），不含游戏规则 |
| 基座 | `cw_sim_streams.py` | 随机流键子流（按模块号+局内坐标派生独立子流，模块间不共享 rng） |
| 基座 | `cw_sim_run_config.py` | 单局运行配置 `RunConfig`（开局参数正典字段清单唯一汇总面） |
| 接缝 | `cw_sim_ports.py` | 端口六口（画面身份/观察/读点改道/点击应答与可见性/声明喂入 `declare_world`；缺省 None = 纯实机零行为变化） |
| 接缝 | `cw_sim_obs_gen.py` | 观察生成器注册表（screen_info 档名 → Obs 产物，经同名上报函数落容器；非金路径屏响错） |
| 游戏系统 | `cw_sim_opening.py` | 对局开局种子（`apply_opening`） |
| 节点日程 | `kernel/cw_node_schedule.py`（kernel 纯数据件） | 位面节点序列真值表（P1/P2 节点日程地面真值表；`node_advance` 声明 `next_screen` 的推导权威源，sim 后端同源 import——契约 = sim-design §6.3） |
| 游戏系统 | `cw_sim_battle.py` | 战斗结算随机输出面（胜负/扣血采样）+ `apply_hp_outcome` 局终判定 |
| 游戏系统 | `cw_sim_enemy.py` | 敌人难度派生与 boss 名单 |
| 游戏系统 | `cw_sim_overlay.py` | overlay 事实触发层队列（`OverlayQueue`/`OVERLAY_KINDS`；评估器 = 后端事件处理方法） |
| 游戏系统 | `cw_sim_special.py` | 特殊角色判据（planner 升星判据 `planner_overlay_due` 等） |
| 回放 | `cw_replay.py` | 决策回放 harness：对历史局容器真值帧重放商店决策，秒级验证策略改动影响 |

sim 设计正本三篇见 `sim/`（体系总纲 sim-design、容器 GameState↔sim 后端接线底账 sim-wiring、战力模型需求定义件 sim-power-model）。

## 九、支撑面

| 位置 | 负责 |
|---|---|
| `knowledge/`、`data/` | 知识数据与静态数据 |
| `tools/cw/`(仓根 tools) | 复盘骨架生成器、哨兵、证明与采样工具(评审/运维面,不在 app 运行路径上) |
| `docs/game/currency_war/` | 游戏机制知识(sources 原文/research 提炼;sim 与判据的机制依据) |
| 本目录各正本 | flow/(外循环路由/动作执行契约/守卫/session/退出链/策略↔流程契约)、screens/(画面 op 一画面一文档)、game_state/(字段规格/逐动作逻辑态更新 logic-updates/)、strategy-docs/(策略决策设计)、sim/(模拟设计)、proofs/(证明) |

