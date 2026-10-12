# 货币战争 sim 游戏后端设计（sim/ · 体系总纲）

> 性质：**设计正本（as-built）**——写 sim 现在就是这么设计的：结构、语义、接口契约、数据流、边界；与代码现状同步维护，架构变化才改本文。数值一律不落本文（单一源在代码常量/注册表，正文只写常量名）。
> 结构分工（本目录三篇）：本文 = 体系总纲；[sim-wiring.md](sim-wiring.md) = 容器 GameState ↔ sim 后端逐域接线底账（域粒度，接线变更改对应行）；[sim-power-model.md](sim-power-model.md) = 战斗结算机制化（战力模型）需求定义件（未实施，落地时按其重建结算层）。
> 读者 = 无会话历史的工程师/智能体。术语首次出现给定义。代码定位一律用符号锚 `文件::符号名`，路径根 = `src/sr_od/application/currency_war/`。
> 前身申报：sim 曾是「自驱动引擎」（reset/step 步进协议、策略注入式喂帧、引擎私有工作帧）；该形态已整体退役，考古走 git 历史。本文只写现值。

## 0. 术语

| 术语 | 定义 |
|---|---|
| **live** | 实机运行的 bot（operations 逐动作执行 + 遥测落盘） |
| **sim** | 单局模拟器形态的**游戏后端**：给定局级输入，按游戏规则推演一局的容器状态演化；对流程的动作与画面请求产出应答 |
| **驱动反转** | 架构裁决：真流程（外层循环 + 画面 op + 动作 op + 策略器）当驱动者，sim 退居「游戏后端」——后端不自驱动、不内嵌循环、不自当策略消费者 |
| **SimBackend** | 世界后端本体（`sim/cw_sim_backend.py::SimBackend`）：组合持有容器 + 后端私有运行时，一实例一局 |
| **容器** | `kernel/cw_game_state.py` 的 `GameState`：局内已知事实的唯一状态类型，live 与 sim 同一类型、同一份；写入走带渠道签名的写入口（渠道族封闭集 obs/logic_action/logic_hook），frozen 帧替换 |
| **上报函数族** | `kernel/cw_action_report/report_action_<snake>_param`（动作）与 `kernel/cw_screen_report/report_screen_<snake>_obs`（观察）两族具名函数：字段转移/观察落地的唯一写入口，拒绝语义在函数内 |
| **画面状态机** | SimBackend 内的呈现机：状态 = （screen_info 档名，子态载荷），答「当前在哪屏、什么可见、点击把世界带到哪」 |
| **流键** | 随机子流的键 = 模块号 + 局内坐标（如 `M05/deal/p1/r3` 发牌）；全部随机量按流键派生独立子流（§7） |
| **金路径** | sim 对局会呈现的 screen_info 档名集合（观察生成器注册表键全集，§6.4）；非金路径屏不出注册表 |
| **披露面** | 后端申报「未建模/占位口径」的键值表（`disclosures`），随局结果 unmodeled 输出；判读者据此挡外推 |
| **sim-only 差异** | sim 存在而 live 无对应物（或行为不同）的语义面，判读时须显式声明不可外推（§8.2） |

## 1. 职责与架构

### 1.1 sim 的职责

sim 是**游戏本体的单局模拟器**（「游戏后端」），不是策略评估器：按游戏规则转移状态、按机制概率产生随机量，对动作产出状态回应。策略效果的批量评估、A/B 对照、统计工具都**不在 sim 本体内**——它们是 sim 之上的外层，现不存在（§8.3 边界）。

驱动反转是本架构的根本裁决：真流程当驱动者。同一套流程代码（外层循环、画面 op、动作 op）与同一套策略器，装上后端就在 sim 世界跑，卸了就在实机跑——两形态的分叉面收敛在端口模块与操作基类覆写（§6.5）。

### 1.2 一实例一局与局级输入

`SimBackend` 一实例服务一局；构造即 reset。局级输入 = `seed: int` + `sim/cw_sim_run_config.py::RunConfig`（开局参数正典字段清单唯一汇总面：职级/难度档/环境在场等），由装配方给定——后端内不猜开局条件分布。对局类型非「标准博弈」 = 构造期显式拒绝，不猜差异。

### 1.3 与 live 的同一性

- **同一容器**：局状态 = 容器 `GameState` 单例（`kernel/cw_game_state.game_state_of(session)`），live 与 sim 同一类型、同一渠道架构。后端的世界真值写 obs 渠道，动作效果经动作 op 走 logic_action 渠道；sim 侧证据前缀 = `sim:` 族（`sim/cw_sim_base.py::sim_evidence`）。
- **同一规则核**：后端不复制任何游戏规则——数据注册表（`data/` 各表）、经济与规则核（`kernel/cw_economy.py`、`cw_shop_deal.py`、`cw_gain_chain.py` 等）、决策核（strategies/ 全族）live 与 sim 共用。规则件语义缺口 = 补 kernel（生产双端受益），禁 sim 第二份实现。
- **同一写通道**：见 §6.1 写通道三条各一。

## 2. 世界后端结构

### 2.1 组成

`SimBackend`（`sim/cw_sim_backend.py::SimBackend`）为 dataclass，**组合**持有 `gs: GameState`（禁子类——子类制造第二容器形状，Field 通道与裸属性两套状态纪律混于一体，决策输入形状随运行模式漂移）。三块内容：

1. **画面状态机**（私有态）：当前屏档名 + 子态、模态交回目标、节点窗口让路恢复位（§3）。
2. **采样簿记**（实机不可观察）：offer 全程去重集（`excluded_invest`/`excluded_env`）、overlay 队列（`sim/cw_sim_overlay.py::OverlayQueue`）、触发水位标志（`planner_fired`/`megastar_fired_tier`/`planner_seen_star`）、随机流键坐标簿记、待授予候选下标。
3. **局结果面**：`hp_trail`、`disclosures`（披露面）、`done`、幂等守卫键；`result()` 出 `sim/cw_sim_backend.py::SimRunResult`（纯结果无评判，消费方 = 运行器断言）。

### 2.2 世界规则件

世界规则的承载位置（语义单一源全在 kernel/data，sim 侧只有编排与采样注入）：

| 规则件 | 承载 |
|---|---|
| 轮首收入（常规/补给·奖励/败补 U04 三分支） | kernel `cw_economy.round_start_income`；后端包装 = `cw_sim_backend.apply_round_start_income` |
| 连胜转移 | `cw_sim_backend.streak_signed_after`（容器带符号连胜单账） |
| 节点经验 | `cw_sim_backend.apply_node_xp` + `NODE_XP_BY_TYPE` 表（依据 docs/game/currency_war/research/xp-rules.md） |
| 商店发牌 | kernel `cw_shop_deal.sample_shop_deal`（单一源）；后端 `deal_shop` 只做节点切换自动全刷的世界写 |
| 概率档与轮岗 | `cw_sim_backend.effective_deal_probs` + kernel `cw_battle_calib.roll_rotation_per_stage` |
| offer 采样 | `cw_sim_backend.sample_strategy_offer` / `sample_env_offer`（U07 固定轮次 + 联席决策，键形 = `offer_slots`） |
| 战斗结算 | `sim/cw_sim_battle.py::settle_battle`（随机输出面，§8.2）+ `apply_hp_outcome`（0hp 保底/局终判定） |
| 敌人侧 | `sim/cw_sim_enemy.py`（难度基线/boss 名单 resolve） |
| 开局种子 | `sim/cw_sim_opening.py::apply_opening` |
| 节点选项生成 | `cw_sim_backend` 节点事件件（`encounter_options`/`supply_options`/`box_options`/`reward_ore_points`） |
| 词缀采样 | `SimBackend._sample_affixes`（流键 `reset/affixes`；`RunConfig.enemy_affixes` 降级为定向测试 override） |
| 特殊角色判据 | `sim/cw_sim_special.py`（planner 升星判据 `planner_overlay_due` 等） |

### 2.3 动作腿零私有语义

后端**没有私有动作转移语义**。玩家动作的世界效果由流程侧动作 op 组装并直调上报函数族承担（与实机完全同构：实机 op 怎么组装 `executed`，sim 路径同一段 op 代码同法组装）。动作采样腿（炉/骇客改件/晶矿/刷新等带随机的上报函数）经 `kernel/cw_action_report` 包的 `set_action_rng_provider` 拿流键 rng，注入点 = 装配函数 `sim/cw_sim_backend.py::install_backend`（键形 `action/<tool>/<序号>`，序号 = 本装配内调用序）；实机缺省 None = 未播种口径零变化。

### 2.4 确定性

后端自有采样全部由 seed 派生（`sim/cw_sim_streams.py::stream_rng` 流键，键形沿用模块号坐标系）。同 seed 同 RunConfig 的两次 reset→局终运行，容器逐位一致（确定性锁 = 测试仓首局验收测试）。

## 3. 画面状态机

### 3.1 状态与档名

状态 = （screen_info 档名，子态载荷）。档名权威 = `assets/game_data/screen_info` 各建档；代码层档名常量 = `cw_sim_backend` 的 `SCREEN_*` 常量群（备战/开商店/简报/投资环境/投资策略/补给/遭遇节点/BOSS简报/位面过渡/武装箱/专家邀请函/盛会之星/银狼升星/结算/大厅）。**子态不设独立档名**：晶矿子态（`PREP_SUB_ORE`）与开局补给等待变体（`PREP_SUB_WAIT_ONE_ONE`）= 备战档载荷，由该档名生成器内部分派观察产物（§6.4）。

### 3.2 转移源两类

1. **动作后果声明**（kernel `cw_world_decl.WorldDecl`，契约正本 = §6.3）：转移动作 op 经端口 `cw_sim_ports.declare_world` 喂入 `SimBackend.advance`，按 `decl.trigger` 分派世界过程/画面呈现、完成后按 `decl.next_screen` 等值对账。18 转移动作全量声明驱动：settle_confirm/supply_confirm（经 kernel `report_node_advance`）→ 节点推进；start_battle/pick_encounter → 战斗结算 → 结算页；开箱动作落地 → 武装箱画面 + 候选生成；pick 族 → 模态交回/选卡世界过程；纯转移类（开书册卡/关店/零写选卡族）→ 按 `next_screen` 推进画面。同一终结动作重复上报不二次推进 = kernel 观察态门（重复上报零推进）+ 后端逐 handler 幂等守卫。
2. **点击源**（不经声明通道的推进型点击，经端口 `click_answer` 感知）：简报下一步、BOSS 简报点空白、位面过渡点空白、补给刷新、开店。这些点击的转移语义权威源 = `docs/develop/sr_od/application/currency_war/screens/` 各篇终结/交回表。

### 3.3 节点窗口序列

节点推进（终结动作触发）后的窗口序列（`SimBackend._begin_node_window`，权威序 = 旧引擎实测收尾检查序 overlay → offer → 下一节点）：

```
写 gs.node（NodeKey）+ 节点序观察锚定（kernel observe_node_anchor）
→ 轮首收入（kernel round_start_income 三分支；败补支消费容器 pending_loss；
  扑满帧例外 = 收入递延至结算腿 `_resolve_battle`，基数快照仍轮初口径——
  统一公式「战败时无连胜成分」需胜负，窗口开时未知）
→ 位面开局环境金（kernel cw_investments.INVESTMENT_ENVS 结构化通道）
→ 商店自动全刷（整店锁跳过；kernel sample_shop_deal 采样）
→ overlay 队列检查（非空 → 让路呈现压住节点屏，选定后复走 offer 检查——让路不吞 offer 槽）
→ offer 日程检查（U07 固定轮次 + 联席决策；命中 → 呈现投资策略选卡屏）
→ 按节点类型呈现对应屏（battle/reward → 备战档，reward = 晶矿子态；
  supply → 补给屏；encounter → 遭遇屏；boss → BOSS 简报）
```

窗口前段（收入/环境金/发牌）对同一节点只执行一次（幂等守卫键 = 节点线性序，`SimBackend._window_begun_ord`）——位面过渡点空白等点击源可能重放收口。节点经验在节点推进时入账（被离开节点的类型）；连胜转移在战斗结算后。位面过渡 = 全继承无重置（容器直接续跑 P2 序列，`kernel/cw_node_schedule.py::node_sequence_of` 地面真值表 P1+P2；P3 末节点推进即局终，披露键 `DISCLOSURE_P3_UNOBSERVED`）。

**节点序列权威与场字段分发**：序列真值的单一源 = `cw_node_schedule`（默认地面真值表 + 环境修饰层）。改节点序列的投资环境（「人身意外险」boss 前插补给）经 `resolve_plane_node_seqs` 在环境注册时一次性解出，由获得链尾段写进 GameState 场字段 `node_seq_by_plane`（逻辑态；字段契约与回退语义见 [fields.md](../game_state/fields.md) §3.2.1）。运行时 sim 与 kernel 同源读该字段：局终判定/线性序反解/进窗/线性序正解/窗口收口/offer 门/节点屏呈现各消费点传场字段现值（None = 未注册回退默认表）；`_ordinal_to_node`/`_node_ordinal` 为 kernel 正反解的瘦委托（异常契约统一 `P3UnobservedError`）。任一侧漏读字段 = 修饰局 P1 r9 推进时 `next_screen` 声明与呈现屏确定性漂移（`DECL_SCREEN_DRIFT` 留证）。

### 3.4 初始序列（reset）

词缀采样入 RunConfig → 开局种子（`apply_opening`，obs 真值覆盖种子底座）→ boss 名单采样写容器（`gs.plane_bosses`）→ 整店锁/宝钻计数按现役口径写初值 → hp 轨迹首点 → 呈现简报屏（词缀 + boss 载荷已写容器）。此后：简报下一步 → （环境在场）投资环境选卡 → wait_one_one 等待变体 → P1r1 对应屏。进入/退出条件的权威源 = `docs/develop/sr_od/application/currency_war/screens/` 各篇。

### 3.5 until 与可见性语义

点击腿带 until 时按实机同形返回 `round_wait`（「点了≠成了」），下一轮 until 问询 = 状态机可见性（`visible`）——上报已同步转移画面，故下一轮即为转移后真值（与实机「观察赢」同形，语义不降级）。可见性裁据：模态屏呈现态压住底层屏（模态族内 `_MODAL_SCREENS` 互斥）；sim 不建模的浮层，其「在场锚」area 恒不可见（`_UNPRESENTED_OVERLAY_ANCHORS` 锚门控语义）。

### 3.6 未注册屏响错

状态机呈现未注册屏时 `observe` = `LookupError` 具名响错（防静默失真——sim 不会走到的屏出现观察请求 = 接线 bug 或辖域外屏，响亮暴露而非产空产物）。

## 4. overlay 触发登记层

### 4.1 机制

判据 → 容器登记 → 呈现，三段均与实机同源：

- **判据**：kernel 值回调（`kernel/cw_faction_callbacks.py`，挂 `GameState._write_logic_frame` deployed 写尾）按阵营资格集/星级事件在**逻辑写时**判定，命中即登记——sim 与实机同一份判据代码，观察写零回调（观察通道不触发）。
- **登记**：`kernel/cw_overlay_register.py` 三口（`register_screen_change` / `consume_screen_change` / `clear_screen_changes`）+ 九 kind 封闭词表 + 屏档名映射（`KIND_SCREEN_NAMES`）；登记簿 = `gs.screen_changes.pending`（ScreenChanges sidecar，含逐档簿记 `wish_tiers_fired` / `planner_tiers_fired` / `fortune_battles`，生命周期 = 局）。
- **呈现**：`SimBackend._present_pending_overlay`——数据源 = 容器登记 pending；呈现位三处 = `screen_identity` 问询时点懒呈现（动作上报内登记的条目在宿主交回后的首次身份问询压上模态，等价实机「动作落地即弹」）、`advance` 纯转移尾、节点窗起点（fortune 呈现门判目标底层）。

### 4.2 目录

- **开箱 / 专家邀请函 / 星徽四选一**：动作触发——`open_box` / `open_bookcard` / `open_tome` 上报内直登（kind = `box_card` / `expert_invite` / `star_tome`，成功腿才登）；开箱的候选生成走 `report_screen_box_pick_obs` 同名通道。
- **巨星（盛会之星）**：判据 = deployed 逻辑写尾的资格集上穿（**逐次上穿即弹,无簿记去重**——ScreenChanges 侧栏簿记仅 wish/planner/fortune 三族;阈值语义源 = `data/cw_factions.py` tiers），一局可多次。
- **planner（银狼升星）**：判据 = deployed 逻辑写尾的银狼星级回调（每费用档一次，簿记 = `planner_tiers_fired`）。
- **命运卜者（占卜屋强化）**：判据 = 占卜屋 settle_confirm 腿登记；**呈现门** = 底层备战才收口（下一节点非备战时条目存活等待）。
- **列车同行 / 祈愿试炼 / 阿哈装备**：判据/选卡上报登记；**sim 无呈现面族**（画面 op 无 sim 观察腿，呈现即卡 observe 重试）→ 懒呈现位消费 + 逐 kind 披露（披露键 = `cw_sim_overlay.OVERLAY_PARAM_PENDING:{kind}`）；partner 候选可自资格集算，候 sim 观察腿接线再呈现。这是**数据缺口不是架构豁免**：补观察腿后逐个落呈现，架构面（登记/呈现/交回）零改动。

## 5. 容器字段判据

### 5.1 判据

实机对局中存在且可观察/影响玩法的世界事实 → `GameState` Field（双端受益）；实机不可观察的生成器采样簿记 → SimBackend 私有。**禁第三形态**（GameState 子类）。字段级规格正本 = `game_state/fields.md`。

### 5.2 历史多账收敛（现值单账）

引擎私有工作帧已不存在，三处历史多账的现役承载：

| 事实 | 承载 |
|---|---|
| 位面/轮次 | `gs.node`（NodeKey 单账；进节点/推进时写，与实机画面 op 锚定 `kernel observe_node_anchor` 同口） |
| 选项载荷（投资环境/策略/补给/遭遇/箱/晶矿面板） | 容器各 opts/面板槽，经生成器 + `cw_screen_report` 同名上报函数送达（与实机观察同一条写通道），后端不私持副本 |
| 无符号连胜 | 容器带符号连胜派生读 `max(signed, 0)`，不设第二账 |

### 5.3 判据新增容器 Field

- `pending_loss`：败态挂账（`kernel/cw_economy.py::LostNodeRef`）。写端 = 战斗结算失败腿；消费 = 轮首收入败补支（U04 口径），非 supply/reward 节点消费、败态跨轮保留至下一战斗轮。
- `shop_locked`：整店锁。v1 恒 `False`（动作词表无锁通道，首版恒解锁 + 披露，字段先行占位；实机写端候锁图标观察补档）。
- `diamond_count`：宝钻计数（UI 可见局内货币）。sim 写端 = 补给带钻选项落地腿；实机写端候补档。

## 6. 双端消费契约

### 6.1 写通道三条各一

| 通道 | 承载 | sim 写端 |
|---|---|---|
| 观察（obs 渠道） | 画面观察落地 | 生成器产物经 `kernel/cw_screen_report/report_screen_<snake>_obs` 落容器（与实机观察同一条写通道）；后端世界事实另有直接 obs 写点（`sim_evidence` 证据族，逐域清单见 sim-wiring.md） |
| 动作（logic_action 渠道） | 动作的字段转移 | 流程侧动作 op 组装后直调自己的上报函数（`report_action_<snake>_param`）——sim 与实机同一段 op 代码 |
| 节点推进 | 终结动作上报 | kernel `report_node_advance`（trigger 封闭集 {settle_confirm, supply_confirm}），sim 与实机同源 |

### 6.2 端口模块（接口契约唯一载体）

`sim/cw_sim_ports.py`——模块级装配槽 + 端口函数；缺省 `None` = 纯实机、零行为变化。端口六口（薄协议，签名不随屏数增长）：

- `screen_identity()`：后端画面状态机答当前 screen_info 档名。
- `observe(screen_name)`：生成器直出该屏 `CwScreenXxxObs` 形状产物；消费方必须经同名上报函数落容器。
- `sim_or_live_observation(screen_name, live_read)`：读屏点改道 helper（装了后端 → `observe`，否则原读链）；逐屏显式读屏点一行机械接线，是观察腿唯一的 op 触点。
- `sim_or_live_identity(screen_names, live_read)`：画面身份读点改道 helper（外循环阶段一身份分发；档名 ∈ 调用方清单才返回）。
- `click_answer(...)` / `visible(...)`：sim 点击应答（后端先按点击处理状态机转移，再出实机同形 round 结果，机械镜 = `cw_sim_ports.mirror_click_answer`）与 until/门可见性问询。
- `declare_world(decl)`：动作后果声明喂入——转移动作 op 自上报出口直调；未装配 = no-op（实机零行为变化），装配后 = 后端 `advance(decl)`，`decl is None` 本层直返（契约正本 = §6.3）。

装配纪律：`install_sim_backend` 进程内单装配（重复安装 raise）、`uninstall_sim_backend` 幂等、测试 teardown 必卸（模块槽是进程全局，残留跨测试泄漏）。`mechanical_io_allowed()` = 机械 IO 腿（直连 controller 点击/拖拽）可达性检查口。

### 6.3 动作后果声明（WorldDecl）

「转移动作」= 落地后世界画面/进程前进的动作（全集 18）。动作后果的出口通道 = **动作后果声明**（`kernel/cw_world_decl.py`）：转移动作的「动作落地 → 世界后果」由上报函数自产的数据承载。schema 两维：`next_screen` = 动作后确定的下一画面 screen_info 档名（`''` = 无画面，局终等未建模终态）；`trigger` = 推进分派类别（`''` = 纯画面转移，后端零专属过程）。载体 = `kernel/cw_game_state.py::LogicOutcome.world_decl`（构造义务：上报函数 `applied=True` 出口必构造；`applied=False` = None）。

不引发画面转移的世界变化（板面组成/升星等）不走独立事件通道——由容器值回调（`kernel/cw_faction_callbacks.py`）在 deployed 逻辑写尾内联判定（§4.1 判据段），零模块级钩子槽。

声明契约四条：

1. **trigger 封闭集**：单一源 = `sim/cw_sim_backend.py::ADVANCE_TRIGGER_KINDS`（advance 分派表键集），9 类过程 + 空：`node_advance`（节点推进）/ `battle_resolve`（战斗结算）/ `open_box` / `pick_box_card` / `pick_megastar` / `pick_planner` / `pick_supply` / `pick_invest_env` / `pick_invest_strategy`。准入判据 = 写端归属：上报函数/获得链已写的后果（腾席/离屏/动作直接后果）不进 trigger；只有后端专属的过程（经济结算/队列出队/候选采样/排除集簿记——实机里「游戏自己算」的部分）才进；写端全在上报侧的动作（开书册卡/关店/五类零写选卡）= `''` 纯转移。值零新词，沿用动作名。
2. **`node_advance` 的 `next_screen` 推导**：权威源 = kernel 节点日程真值表（`kernel/cw_node_schedule.py`，P1+P2 地面真值）+ `effective_node_ord`（`kernel/cw_game_state.py`，推进落账后的生效序）。规则序：eff 超真值表总长 → `''`（局终）→ 按表变长累加反解（位面，轮次）→ 位面切换轮优先（`货币战争-位面过渡`）→ 新节点类型映射画面（battle/reward→备战、supply→补给、encounter→遭遇节点、boss→BOSS 简报）。禁读容器 `gs.node` 作推导口——它是观察镜像，不随推进变。
3. **喂入契约**：转移动作 op 在自上报出口紧跟一行 `cw_sim_ports.declare_world(outcome.world_decl)`（一次动作多支上报 = 每支上报出口各自紧跟一行；round 结果 `data` 携带最后一份声明）；非转移动作 `world_decl` 恒 None，无喂入行。端口未装配 = no-op（实机零行为变化）；`decl is None` 端口层直返。
4. **消费与对账**（`SimBackend.advance(decl)`）：按 `decl.trigger` 分派世界过程/画面呈现（18 转移动作全量在表；`''` = 纯画面转移，按 `next_screen` 推进）；完成后按 `decl.next_screen` 等值对账——断言对象 = 状态机**底层稳态画面**（让路恢复位消费完、overlay 弹完后的落点屏）；建模内失配豁免三类（overlay 登记在册 pending / offer 呈现 / 节点窗让路）断言延后至稳态补验；`next_screen=''` 预测局终，断言载体 = `done` 为真 ∧ 呈现大厅屏（局终无下一画面，不走字面等值）。断言不等且不在豁免集 = `disclosures` 缺陷留证不停机（声明与状态机漂移的早期警报）。`trigger` 集外值 = ValueError 响亮（构造点漂移 = 接线 bug，禁静默）。

### 6.4 观察生成器

`sim/cw_sim_obs_gen.py`——注册表：screen_info 档名 → `fn(backend) -> CwScreenXxxObs`。生成器从世界真值（容器 + 状态机运行时）填结构体，零截图零识别；**写通道铁律**：产物必须经 `kernel/cw_screen_report/` 同名上报函数落容器（观察口径/归一化/缺省语义单一源在 report 消费端，生成器只产数据）。金路径 13 档名（备战含晶矿子态与 wait_one_one 变体、商店、battle_wait、补给、投资环境、投资策略、简报、boss 简报、位面过渡、遭遇、开箱、巨星、planner）；非金路径屏不出注册表（§3.6 响错）。`PrepObservation` 控制信号（shop_open/substate/event_overlay）由生成器随观察产出。

### 6.5 流程侧接缝

- `operations/cw_operation_base.py::CwOperation`：CW operations 树唯一父类（框架 `SrOperation` 子类）。sim 装配后改写四条腿：`screenshot()`（哨兵帧，不触 controller，框架每轮自动截图无感运转）、`round_by_find_and_click_area()`（端口 click_answer + until 轮询腿本层 `visible` 收口不重进后端——重进 = 重复触发转移）、`round_by_find_area()`（端口 visible 应答）、`park_cursor()`（静默跳过）。其余 round_by_* / screen_utils 助手一律 `super()` 透传；实机路径全部 `super()` 原样零变化。
- **直连 controller 旁路**（机械 IO 腿）：逐点加 `mechanical_io_allowed()` port 检查（sim → 机械腿静默成功，世界反应由紧随的自上报承接）；漏改路径由运行器 controller 桩兜底。
- **运行器与桩**（测试仓 `sr-od-test/test/harness/sim_backend_runner.py`）：真 screen_loader（生成器查档案点位）+ controller 桩（全接口触碰即 AssertionError，报「sim 模式触碰真实 IO」+ 调用栈）+ `sim_backend_fixture` 装配纪律包装（teardown 必卸）+ `fast_sleep` 等待旁路。sim 分支的等待参数透传丢弃（sim 世界瞬时呈现）。

### 6.6 装配点

`sim/cw_sim_backend.install_backend(backend)`：端口槽装配 + kernel 事实事件 sink 订阅（转移后果不经订阅，走声明喂入 = §6.2 `declare_world`）+ 动作腿 rng 提供槽注入（§2.3）；`uninstall_backend()` 幂等复位三槽。装配点 = sim 运行器（测试仓 harness）；生产实跑入口当前不存在（§8.3）。

## 7. 随机性纪律

- **流键子流**：单局 = 一个 `seed: int`；全部随机量按 `random.Random(f'{seed}#{stream_key}')` 派生子流，键形 = 模块号 + 局内坐标（世界件沿用 `Mxx/...` 坐标系，动作腿 = `action/<tool>/<序号>`）。禁模块间共享 rng 实例；禁策略器读 sim 流（策略自带随机时用独立流键）。
- 动机：单 rng 实例按消耗序耦合时，任何模块加/删一次采样就扰动全流；流键化后各模块随机序独立，模块规格可独立演化。
- **概率源三通道**（随机量的唯一合法来源）：①游戏内可读真值表（如 `data/cw_shop_odds.py` 的 `REFRESH_PROB`）；②已收案的机制口径（依据 docs/game/currency_war/research/ 对应篇）；③已裁定的定案值（裁定记录见对应代码行注释）。禁以 replay/语料统计分布充当机制概率。
- **可复现承诺** = `(seed, RunConfig, 注册表指纹)`。

## 8. 保真度分层与 sim-only 边界

### 8.1 保真度分层（判读外推纪律）

| 层 | 内容 | 判读口径 |
|---|---|---|
| 真代码层 | 注册表/概率表/策略本体/上报函数族 | 可直接信 |
| 机制层 | 按游戏规则建模的转移（收入/经验/发牌/获得链/状态机） | 信机制文档（docs/game/currency_war/research/） |
| 校准层 | 不可复刻面（战斗随机输出面等，随局披露） | 结论带免责，战力相关判读禁出 |
| sim-only 差异面 | §8.2 申报清单 + `disclosures` 披露面 | 禁外推 |

### 8.2 sim-only 与未建模申报（维护义务：新增面在此登记，披露键随局输出）

| 面 | 现役口径 | 判读限制 |
|---|---|---|
| 战斗结算 | 随机输出面：胜负 = 均匀伯努利（`cw_sim_battle.SIM_WIN_PROB`），败局扣血 = 区间均匀采样（`SIM_HP_LOSS_MIN`/`SIM_HP_LOSS_MAX`，锚定实测单次败局总扣血样本域）；扑满关不掉血豁免 | 战力相关判读禁出；机制化重建需求件 = sim-power-model.md |
| 扣血分量 | 基础伤害/进度伤害置 None 占位，随局披露不可分 | 分项判读禁出，候实机结算帧采集 |
| P3 | 节点序列无完整观测：P2 末再推进即局终（披露键 `DISCLOSURE_P3_UNOBSERVED`） | 禁设回退先验，候实机补采 |
| offer 触发 | 罕见离群触发点（观测 ~1-2%，触发源未归因）不建模（披露键 `OFFER_OUTLIER_DISCLOSURE`） | 作披露面 |
| 词缀采样 | 张数/分布占位（注册表键集均匀无放回，披露键 `DISCLOSURE_AFFIX_SAMPLE`） | 词缀构成敏感结论禁出 |
| overlay 余族 | partner/expert/fate/aha/hack 评估器缺位不入队（`OVERLAY_PARAM_PENDING`） | 这些 overlay 的决策域 sim 不可测 |
| 环境经济 | 位面开局金通道已结构化生效，其余通道挂披露（`DISCLOSURE_ENV_CHANNELS`） | 其余经济通道结论禁出 |
| 装备/工具发放 | 发放空表/特权投影仪/炉拖角色模式未建模（`UNMODELED_GRANTS` 族披露键） | 装备获取轨迹 sim 不可判 |
| sim-only 简化档 | 开局补给等待变体、晶矿面板内容占位、开箱候选占位、补给带钻槽位口径等逐键披露 | 逐键披露挡外推 |

### 8.3 不建模边界（架构边界，非缺陷）

- 批量运行 / A/B / 统计工具：不在 sim 本体内，现不存在；恢复载体 = 以后端为世界的批跑件，另批立项。
- 入口链 / 退出链：sim 从对局内起点（简报屏）开始，局终呈现大厅屏即收口；大世界导航不在辖内。
- 战斗与收入校准补齐、噪声注入（对账失能补偿）、性能：不在现役辖域。
- 战斗等待动画窗：实机时间维，sim 结算瞬时完成（呈现结算页承载流程消费链）。

## 9. 记录与回放

- **记录** = 容器统一 state 流水（`kernel/cw_state_journal.py`，live/sim 同构）；sim 不自建第二账本、无批量落盘面。
- **决策回放**（`sim/cw_replay.py`）：对历史局的容器真值帧重放商店决策，秒级看到策略改动影响了哪些决策——策略改动的先导验证通道。回放驱动器逐动作直调上报函数族推进期望态，与生产同一条转移语义。

## 10. 守恒不变量

- **牌池守恒**：剩余牌库 = 固定牌库 − 手上持有副本总数（held 由 bench/deployed 星级派生，Σ 3^(star−1)；合成不销毁，2★ 计 3 张/3★ 计 9 张）。开局手牌是派生池的首个写端，先于任何商店发牌。
- **容器不变式**：金币不出现无规则依据的负值；hp 轨迹与结算记录一致；经验等级符合规则表；局终无未消费败态挂账（`pending_loss` 局终必空）。锁 = 测试仓首局验收测试。
- 维护义务：新增机制不变量在此登记，由对应模块的行为测试锁承载。
