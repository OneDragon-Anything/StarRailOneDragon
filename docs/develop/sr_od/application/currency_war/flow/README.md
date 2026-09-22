# 货币战争 流程控制设计（flow/ · 唯一现行家）

> 本目录是货币战争（CW）**流程控制的唯一现行设计家**，由流程层代码反向规格化而成。原 `strategy-docs/09_architecture.md`（契约/插件/管理器/注册壳/三臂）已删除，其内容全部收编入本 README §2。
> 职责分界（用户裁定）：**策略文档（`../strategy-docs/`）只管"每个画面结合哪些数学证明、怎么产出决策"；流程控制单独立文档（本目录）**——画面识别与路由、访问相位推进、动作发射契约、守卫与停机。
> 读者 = 无会话历史的工程师/智能体。术语首次出现给定义。代码定位一律用符号锚 `文件::符号名`（loop 内语义段用 `文件::CwLoop.loop(段名)` 形态）——行号随代码增长漂移，不作定位依据；路径根 = `src/sr_od/application/currency_war/`。
> 决策形态 = 画面 op 两 node(观察 node → 决策动作 node,决策动作 = 单动作决策循环→终结 op),规格正本 = [../screens/op-layer.md](../screens/op-layer.md);波批时代旧序列契约的解读钥匙见 §2.2 历史注。
> 术语注(首次出现):逻辑态 = 动作执行后不经观察、按游戏规则推算并直写容器的预期状态;真值以下一帧观察为准(观察赢)。
> 路径缩写约定:本文反引号短路径 `research/X.md`/`data/X.md` 等 = `docs/game/currency_war/` 下对应文件(非 src 树);game 侧文档同理指向本仓 docs/。


## 1. 四层结构总图

```
┌─ 外层循环（cw_loop.py）────────────────────────────────────────┐
│ 画面识别 → 分支路由（身份分发/特殊规则 overlay → 备战 1 → 战斗窗 → 大厅 3c）│
│ 轮次推进（备战环 → 出战 → 战斗等待 → 结算 → 回备战）            │
│ 节点推进 = 终结动作上报（settle/supply_confirm）+ 画面 op 锚定   │
│ 停机/遥测钩子（守卫、runs summary、分配器、对局存档）           │
├─ 画面指挥(35 画面 op,每屏独立类直继承 SrOperation,两 node 形态)──┤
│ 观察 node:门 → 显式读屏(唯一读屏点)→ CwScreenXxxObs →          │
│   report_screen_*_obs 落容器(kernel/cw_screen_report/ 每屏一文件)│
│ 决策动作 node:重入裁决 → 决策(容器零参读;空发射 = Obs outer 口径)│
│   → 动作(零读屏)→ round_wait 循环(无防御上限);终结动作交回  │
│ 备战(CwScreenPrep):heavy 观察+接管补采+审计留守观察 node;       │
│   决策动作 = 单动作 while 循环;商店编排(_open_shop_phase)        │
├─ 策略步进（mandate_v1：bridge.py 决策入口 + entry.py 三遍编排）┤
│ 备战决策 live 链 = bridge.decide_prep_screen：方向代次消费 →      │
│   前置发射位 _launch_front_check(armed 帧短路 return,短路帧不披   │
│   露) → 披露 economy_cycle.disclose_budget(非 armed 帧才到达) →   │
│   decide_prep_frame → entry.emit（①prep实体面→②证明→③升档器→     │
│   ④骨架M1-M7→⑤EV→⑥无动作⇒StartBattle，自有动作词表,     │
│   单动作循环逐帧恰取一个动作(接口返回 CwAction | None,    │
│   None = 本帧无动作);商店决策 = decide_shop_action 单动作   │
│   接口;flow.py 旧备战骨架（相位机/腾席链等 10 方法+session  │
│   字段）已删（考古走 git 历史）;pick 族 13 接口与冷建/结算   │
│   收编仍由 flow.py 中间 ABC 承载│
├─ 动作执行（kernel/cw_vocab.py 词表 + prep_actions.py 执行器│
│ + cw_screen_shop.py 商店画面 op 两 node + cw_action_registry.py 单一注册表  │
│ + kernel/cw_action_report/ 上报函数族（每动作一个具名上报接口）│
│  (cw_<action>_action.py 一 op 一文件,CwActionXxxOp(SrOperation);│
│  守卫 cw_shop_action_ops.py)）──────┤
│ 机械发出（零判效;round 成功态 = 发出事实）→ op 内直调自己的   │
│ 上报函数（容器写单点;写语义逐动作各异）;终结判定 = 注册表 op   │
│ 类 terminal 属性;事件线 pick 族 12 op 全在注册表              │
│（cw_pick_xxx_action.py 一 op 一文件;pick-op-unify 批收编）  │
└────────────────────────────────────────────────────────────────┘
```

分层判据：**外层循环管"现在是哪个画面、交给谁"；画面指挥管"一次访问内观察→决策→执行的编排"；策略步进管"给一帧期望态提什么动作"（骨架 + 委托 mandate_v1 判据,单动作选择序）；动作执行管"一个动作怎么落地（机械发出、零判效;落地判定归观察侧对账,见 [../screens/op-layer.md](../screens/op-layer.md) §1）"**。节点推进喂入 = **动作上报 + 画面 op 锚定**：战斗/补给节点终结动作 op 上报（kernel `report_node_advance`，trigger 封闭集 {settle_confirm, supply_confirm}）+ 画面 op 观察锚定（`CwScreenPrep` 备战顶栏 / `CwScreenSupplyNode` 节点条 → kernel `observe_node_anchor`）；观察漏斗与外循环分支写点不写推进域（判定语义单一源 = [../game_state/node-derivation.md](../game_state/node-derivation.md)）。策略判据（买/卖/升/刷的数学）一律不在本目录，见 `../strategy-docs/11_shop_decisions.md` 等篇。

**用户裁定（2026-09-21,决策控制分层铁律）**：凡用于**控制决策行为**的闸门与判断——政策闸、发射闸、花金/消费限制、动作值域过滤——必须在**策略侧**实现（策略器决策时自限,会话状态存 StrategyState）；**流程侧（外循环 / 画面 op / 动作执行）禁止任何形式的决策闸门与政策判断**。流程侧的合法判断面仅限：画面识别与路由（外循环本职）、防 bug 守卫断言（非控制流）、失败治理与停机（失败出口非决策控制）。决策的值域与节拍永远由策略器在决策时决定——流程侧出现「需要判断该不该放某个动作过」= 分层错误,修法 = 迁策略侧（单一源 = 本条;各篇 op/action 文档引用以指针为准）。

## 2. 策略↔流程契约(吸收原 strategy-docs/09_architecture.md;意向层重塑拆分)

> 原 09 篇已删除,其四身份分离与接口内容收编于本节。判据语义的归属篇同步改指 strategy-docs 新编号。**契约形状**:契约成员 17 = 分画面决策入口 15(抽象)+ 每局冷建口 2——create_session(抽象)+ create_state(非 abstract 工厂);方向重估节拍/生命周期事件等策略内部构造不在契约面。17 = 对外接口面,实现层内部方法数不计入。

### 2.1 四身份分离

| 身份 | 载体 | 职责 | 禁止 |
|---|---|---|---|
| **契约** | `strategies/impl/cw_strategy.py` 的 `CwStrategy` ABC(抽象 12 + 非 abstract 工厂 1;接口面见 §2.2) | 定义各画面 op 调用策略器的全部决策入口与唯一冷建口(§2.2) | ABC 自身零内置逻辑(纯接口,create_state 工厂除外);零策略专属语义(update_target/意向 target 机器/生命周期事件钩子已出契约面)。接口计数:抽象 16 + 非 abstract 工厂 1(接口面见 §2.2) |
| **管理器** | `strategies/impl/cw_strategy_manager.py`(StrategyManager) | 按实例化/选择策略;注册面封闭集 = {mandate_v1}(decision_v2 已随 commit b94e9cfb 删除) | 不承载判据;不知策略内部结构 |
| **实现** | `strategies/impl/mandate_v1/`(单一核)+ `strategies/impl/flow.py`(`CwFlowStrategy` 中间辅助 ABC:唯一冷建口/方向节拍内化刷新/pick 族/商店单动作接口与驱动器缺省,`_abstract=True` 不注册;旧备战骨架已删;结算策略半惰性 drain 三方法已删(退役批)) | 决策本体 | 禁自实现生命周期机制(幂等键/连败恢复/屏蔽/stall 门——归流程侧);禁绕契约自造接口 |
| **注册壳** | `strategies/mandate_v1_strategy.py`(MandateV1Live) | 把实现包注册进策略扫描器 | 壳内零判据逻辑 |

### 2.2 契约接口全景(形状;`cw_strategy.py` + `flow.py`)

**每局冷建 2**(实现 = `flow.py`):

| 接口 | 调用时机(流程侧) | 语义 |
|---|---|---|
| `create_session(config)` [abstract] | 每局开始一次(establish_new_match 进对局前移点/防御路径/回放三处同源) | 返回空白 StrategySession + 策略器状态工厂接线 + live 初值 v3_phase='FORM'——**唯一冷建口**(原 on_match_start 冷建与初值双写点收编) |
| `create_state(config)` [非 abstract 工厂] | 仅由 create_session 接线调用 | 每局冷建策略器状态对象(黑盒契约;缺省 None = 第三方插件兼容条款——新增 abstract 钩子会破坏存量第三方策略,故本口为非 abstract;详 = [session.md](session.md)「第三方插件兼容条款」) |

**分画面决策入口 15**(抽象;方向重估由各入口经黑板帧代次标注内化触发):

| 接口 | 输入 | 返回 | 语义 |
|---|---|---|---|
| decide_prep_screen(session, config) | 容器 game state 直读(game_state_of;迭代 2026-09-18-prep-obs-retirement 阶段 3.5 黑板退役,「观察先于决策」由画面 op 编排保证) | **恰一个动作**(CwAction),None 退役;重观察动作 = CwActionObsParam 两口径——scope='in_place' 环内重观察(宿主重观察上报后原地续决策)/ scope='outer_loop' 交回外循环重观察(承载原 HoldFrame 空发射语义,用户裁定 2026-09-20 HoldFrame 收编删除) | 空发射是合法通道;策略器异常/非法形状由消费端守卫拒绝(cw_screen_prep 决策循环 try/except:异常→本轮 fail 交外循环 retry 链;非 CwAction 返回→具名 fail 留证) |
| `decide_shop_action(session, config)` [本批升格入 ABC] | **终态零参口**:决策输入 = 容器单例 `game_state_of(session)`(self.gs;写者 = 入口观察漏斗/动作自上报/sim 引擎)——形参仅为 ABC 形状保留,决策本体零消费 | **恰一个动作**,「无动作可做」= `CloseShop` 恒可用终结;生产执行侧 = 商店画面 op `CwScreenShop` 决策动作 node 单动作循环逐帧调用,契约核验挂本入口 | 决策本体 = `mandate_v1/shop.py`;容器 shop payload 离屏 = 观察层失约抛错 |
| `decide_invest_env`/`decide_invest_strategy`/`decide_supply`/`decide_encounter`/`decide_megastar`/`decide_partner`/`decide_planner`/`decide_star_tome`/`decide_wish_trial`/`decide_box_card`/`decide_fortune`/`decide_expert_invite`(pick 族 12;原 `decide_equip_pick` 随选择装备屏误判退役删除,2026-09-22) | 容器槽零参读(候选自各 `*_opts` 槽/payload 槽,写端 = 各画面 op 观察上报;离屏 None = 观察层失约抛错) | 恰一个动作:选卡 `CwActionPickXxxParam` ∨ 刷新建议动作(遭遇/补给/投资两屏),互斥单发 | 选项决策;动作编排归画面 op,不进序列契约辖内。决策规格 = `../strategy-docs/13_pick_family.md` |

**非契约成员(实现层,不在 ABC 面)**:

- `decide_shop_screen`(flow 层缺省驱动器 + bridge 覆写)——**序列兼容驱动器**:逐帧调 `decide_shop_action` + 逐动作直调上报函数推进期望态(kernel/cw_action_report 函数族,引擎入口委托分支串;快照三件组与升星腿内聚买牌上报;此后零 `cw_state.simulate` 前瞻消费),终结动作截停、CloseShop 收尾不入序列。sim 引擎/回放/既有序列锁消费;生产执行侧不走(单动作循环)。mandate 覆写保留特有记账(已买件/段序号/续段 token)。
- `_refresh_direction`/`_refresh_direction_views`(flow 层私有)——**方向节拍内化**:键守卫贵段(`update_intention` 状态机 + 候选评分遥测)每 game-round 恰一次 + 便宜派生视图段;触发信号 = GameState 非 Field 双槽帧代次标注(`gs.frame_class_prep`/`gs.frame_class_shop` ∈ full/view/none,写点 = 备战/商店域观察装配点与决策环直写,读者 = 决策入口方向节拍,读后即清;驱动器不写帧类槽)。
- ~~`_drain_pending_round_outcomes`(flow 层私有)~~——**已删(退役批)**:结算策略半惰性加工(掉血三臂/node_type 回落/谷底回滚登记)经方案批复核为零行为死链(登记臂前置零写端/三臂零决策消费端),04_survival_budget §7 #7/#8 裁决落地删除;`session.pending_round_outcomes` 槽保留为观察半累积面。
- `write_shop_mirrors`(遥测镜像写者)。

注(生命周期):旧 `on_match_start/on_match_end` 删除(职责归 create_session 唯一冷建口/局终收口);旧 `on_round_end` 拆两半——观察半(performance.record/last_streak/last_hp 过置信门/last_hp_t)= battle_wait 结算点**即时直写**(`cw_screen_battle_wait._write_settlement_observation` 单一写点),策略半原经 `session.pending_round_outcomes` 待加工槽惰性 drain——**该消费半已随退役批删除,槽保留为只写不读的观察累积面**。旧 `decide_prep_action` 薄委托已删(P5 挂账兑现)。

**序列语义(历史注——波批时代的冻结条款,反向自旧 `cw_strategy.py` 与旧 `cw_screen_prep.py` 序列消费段)**【本节为**历史契约**:整波返回/帧稳定截断/空批终止语义已由终结动作与单动作循环取代([../screens/op-layer.md](../screens/op-layer.md) §1),本节仅作旧序列锁与历史 ADR 的解读钥匙;其中 fail-stop/恢复原语条款已随验证段废除批退役,现行控制流 = 终结动作 + 机械执行零判效】:
- **帧稳定域**(历史):序列内第 i+1 个动作不得依赖第 i 个动作执行后的新观察;发射时逐动作判"执行后画面状态能否静态推出",推不出即截断——截断器已退役,截断点语义由终结动作吸收;流程侧保守口径(每动作落地后 heavy 重观察)已由「入口单次 heavy + 逐动作逻辑态直写」取代。OpenShop/StartBattle 现为终结动作。
- **fail-stop**(已退役):原「任一动作未落地 → 恢复原语(关已知弹层)→ 交回外循环 heavy 重观察重调接口」随验证段废除批删除;现行 = 动作机械发出零判效,落地判定归观察侧对账(../screens/op-layer.md §1)。参数非法拒绝仍为执行前契约检查。
- **对账唯一发生点 = 观察边界**(现行有效,两态制归一):动作 op 自上报(`report_action_<snake>_param`,每动作一个具名接口)直写容器逻辑态,落地判定归观察边界对账(`cw_reconcile` + observe 失配台账兜底);执行侧验证已废(零判效),期望态暂存对账通道已随执行层状态类目退役(git 历史可溯)。
- **控制流类动作已整体退役出词表**(DeferSpheres 族随词汇清理批删除;overlay 让位由环入口直接交回外循环承载);策略器禁用空批表达控制流(商店侧空批通道已由 CloseShop 终结取代)。
- **生命周期机制归流程侧**(现行有效):幂等键 `action_key`、stall 门、强制出战;执行失败记忆机制已随执行层状态类目退役(git 历史可溯)。

共 冷建 2 + 决策入口 15(抽象 16 + 工厂 1 = 17)。新事件面优先归并进既有 pick 接口或走契约改版,禁旁路自造接口。

### 2.3 装配与依赖矩阵（吸收原 09 §4）

- **依赖方向**：实现包 → 知识层/数学层/执行层单向；分包依赖矩阵禁 decision→obs 直依（obs 读口经 app 桶装配点 `install_obs_ports()` 注入）；决策本体 = 纯函数（bridge.decide_prep_frame，决策输入 = obs（黑板）+ session 容器直读）。
- **装配点**：黑板单一写端纪律保持；`_RESET_PHASE_ROUND_CACHE` 注入槽（缺省关）+ `discard_stale_match_container`（异常路径残留容器弃置——session 全量重建 by construction）。
- **gated_hp**（结算 HP 新鲜度门，单一实现的 helper，符号锚见代码）：结算真值仅在可信窗口内覆盖现读——观测质量门，非决策输入（`../strategy-docs/04_survival_budget.md` §7 表 #6）。
- **sim 消费面注记**:sim 消费 decide_shop_screen 驱动器(方向重估经驱动器内单动作入口消费 full 帧触发)——sim A/B 的证明面 = 商店波经济决策;prep 屏编排域在 sim 无实体真值源,其正确性防线 = 契约锁 + 实机,不在 sim A/B 辖内。

### 2.4 换核与 A/B(现状口径)

- **注册面封闭集 = {mandate_v1}**(decision_v2 基线臂已随旧决策包删除终结);换核机制 = config 切 `strategy_id`(最小面),不改流程侧分发。
- 旧三臂 A/B 结构已终结;跨策略 A/B 的判据框架(判前锁/强制披露/遥测分栈)随 sim 重设计批重立(git 可溯)。
- **归因域限定**:sim 引擎唯一决策入口 = 商店决策面(prep 面 sim 不可达),结论不得外推为全决策面处理效应。

### 2.5 无状态策略与 session / 策略器状态

策略实例不持有可变每局状态;状态两类分离(设计单一源 = `flow/session.md` as-designed):**观察数据**走 `StrategySession`(框架每局新建、局终销毁,只承载读屏采集);**策略器状态** = 实现包私有 `StrategyState`,经 `CwStrategy.create_state` 工厂(非 abstract,基类缺省 None)每局冷建、挂 `session.strategy_state` 黑盒引用,框架只搬运引用,策略器侧消费经访问函数(`strategy_state_of`/impl 侧 `state_of`)。**执行层状态类目已退役**(git 历史可溯):局内事实由 GameState 容器独占承载,防重入由决策面读容器计数自行裁决,执行层不再设旁表状态载体。执行层需要读写策略器状态时(如画面 op 读写防重入宿主 `StrategyState.megastar_clicked`),一律经 kernel `strategy_state_of`(None-safe,状态缺席不冷建)——禁 impl 侧 `state_of` 从执行层调用(其 None 冷建覆写副作用属策略器装配语义,执行层不得触发)。异常路径残留容器由 `discard_stale_match_container` 在"确凿新局"信号点丢弃(`cw_strategy.py`)。obs 读口注入槽 `_RESET_PHASE_ROUND_CACHE` 缺省关(`cw_strategy.py`)。

## 3. 各篇导读

| 篇 | 一句话 |
|---|---|
| [outer_loop.md](outer_loop.md) | 外层循环：两阶段身份分发、路由、轮次推进、停机/遥测钩子 |
| [exit_chain.md](exit_chain.md) | 退出链：返回大世界 × 对局退出三层结构、退出路由分发序、A 类名单与停机位同源契约、逐屏归档、穿透/干净判据语义分工 |
| [../screens/op-layer.md](../screens/op-layer.md) | **画面 op 层设计**（行为规范+上报接口+形态分型+obs 工具箱）——两 node 形态(观察+决策动作)、round_wait 循环无防御上限、report 上报接口、对账边界、终结动作集 |
| [../screens/](../screens/README.md) | **画面 op 各篇（一画面一文档）**：备战（prep）/商店（shop）/单选族/弹窗族/推进族——能力矩阵与画面文档模板在其 README |
| [action_exec.md](action_exec.md) | 动作执行：词表与注册表、执行契约（op 自上报 + round 成功态）、落地登记、商店/备战/部署执行要点、重试语义 |
| [projection_contract.md](projection_contract.md) | 备战逻辑态面交互契约：状态面板/观察帧 ↔ 执行臂的字段消费、坐标系、快照 vs 现读时序、注释规范缺口登记 |
| [guards.md](guards.md) | 守卫总册：外环通用网、未知兜底、未识别卡停机、降级链(停滞判读归事件哨兵 cw_sentinel.py,住 skill scripts/) |

## 4. 守卫总览（细则 = guards.md；全量防线含召唤物/对账安灯/特殊投资/降级链）

| 守卫 | 触发 | 动作 | 载体 |
|---|---|---|---|
| 未知画面兜底 | 连续 15 轮全分支不命中（每轮 1s 重试） | round_fail 交框架失败 | `cw_loop.py::CwLoop._handle_unknown_fallback` |
| 商店未识别卡停机 | 入口观察回执含 unknown 槽（读链终判） | stop_running 框架截图留证 + round_fail | `cw_screen_shop.py::CwScreenShop.observe`（`_shop_entry_read` 入口段） |
| 外环连续 fail 重派网 | 同一分发 op 连续 fail 5（ok 清零） | round_fail 显式停交上层 | `cw_loop.py::CwLoop.OP_FAIL_REDISPATCH_LIMIT`（`_dispatch_screen_op`） |

## 5. 入口链（enter/start）与弹窗守卫族

> 反向规格化来源 = `currency_war_app.py` + `operations/cw_entry/`（app/enter/start 三层）。对局内循环见 outer_loop.md，本节管「大世界 → 大厅 → 备战」入口链。守卫族决策依据 = 「守卫引入」→「注册表化+领取目标修正」两次演进（细节归 git 历史）。

### 5.1 链路结构

```
CurrencyWarApp（app 三节点）
  _enter_lobby：弹窗守卫 → 暂停面板恢复预检 → 大厅锚/对局屏判定（已在则跳过）→ CwEntryEnter
  _start_match：恢复预检 → 对局屏判定 → CwEntryStart
  _run_loop：CwLoop（对局内，见 outer_loop.md）
CwEntryEnter.wait_lobby（node_max_retry_times=30；`cw_entry_enter.py::CwEntryEnter.wait_lobby`）：弹窗守卫 → 大厅锚 → 前往参与 → 点空白关弹窗 → 公告轮播 → F 交互进大厅
CwEntryStart.click_start（node_max_retry_times 装饰器缺省 3；`operation_node.py::operation_node`）→ advance_to_prep（node_max_retry_times=60；`cw_entry_start.py::CwEntryStart.advance_to_prep`）：备战锚 → 弹窗守卫 → 大厅残留逃逸 →
  前进按钮分支序（难度确认/模式选择/简报/继续进度/投资环境/投资策略/教程叠层/积分奖励页）→ 兜底 retry
```

### 5.2 弹窗守卫族（注册表 `ENTRY_POPUP_GUARDS` + 统一入口 `try_handle_entry_popups`，`cw_entry_start.py`）

四挂点各一行调用 `try_handle_entry_popups(op, screen)`；识别→动作→具名 retry 的参数住在注册表数据行（`EntryPopupGuardSpec`），元组顺序 = 挂点执行序（supply 在 detail 族前，领取优先；序位机械防线 = 测试仓守卫序位锁，元组重排即红）：

| 注册表项 | 识别（AND 全锚同帧） | 动作 | 返回 |
|---|---|---|---|
| `_TRAIN_SUPPLY_GUARD` | 单锚 `标识-列车补给`@0.75 | 点 `文本-领取提示`（领取语义，无 X 钮；实测确认领取点， rect 以「区域-中央徽章危险区」留档仅供测试负向断言，生产永不点击） | `round_retry('列车补给领取中', wait=3)` |
| `_JADE_DETAIL_GUARD` | 双锚：`标识-星琼标题`@0.5 + `标识-稀有货币`@0.75 | 点 `按钮-关闭X` | `round_retry('星琼详情弹窗关闭中', wait=1.5)` |
| `_STAR_BADGE_GUARD` | 双锚：`标识-流派星徽`@0.9 + `标识-套组标题`@0.9 | 点 `按钮-关闭` | `round_retry('星徽详情弹窗关闭中', wait=1.5)` |

- `try_handle_train_supply_popup` 薄包装仅保留给 CW 之外的真实消费方 `back_to_normal_world_plus`（只管 supply 语义不变）；jade/badge 无 CW 外消费方不设包装。
- **挂点序位**：守卫列位于各节点一切既有分支之前（模态弹窗盖场时背景锚点全部失明，守卫不接则兜底空烧节点预算）；`advance_to_prep` 内先于一切状态分支，且守卫轮不烧 `_advance_steps` 推进预算。
- **返回语义**：守卫一律 `round_retry`（计入 `node_max_retry_times`），禁 `round_wait`（框架对 WAIT 不计 retry 且归零计数 → 无界空转）；守卫×领取交替循环每圈耗 2 次预算，任一节点预算内具名 FAIL。
- **对局屏白名单口径**：`cw_screen_state.LOBBY_STATE_SCREENS` 显式排除入口链可达的非对局屏（大厅/攻略系/列车补给弹窗/星琼详情/星徽详情/积分奖励等）；带 `货币战争-` 前缀的新建档屏默认进对局屏集，入口链可达的弹窗/奖励页漏排除 = 误判「已在对局中」跳过 enter（锁测试钉死）。
