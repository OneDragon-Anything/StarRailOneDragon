# Session 职责分离(session 三类状态分离,as-designed)

> **状态声明**:本篇是**设计件(as-designed)**,非现状描述。目标态与现状在正文内显式区分(双态标注先例 = `sim/sim-design.md`);现状描述反向规格化自 `kernel/cw_strategy_session.py`(330 行,路径根 = `src/sr_od/application/currency_war/`,下称 session 文件)与各消费点(grep 直调行号见清册)。迁移方案按用户 2026-09-06 裁定为**一次性原子切换**(流水-20260906.jsonl 18:47 行)——原任务书的「分期迁移+双轨并存」框架被该裁定取代,§6 如实记录被取代的框架以保留推理链。
> **来源裁定**(用户 2026-09-06):session 的本义 = 只承载「从游戏画面观察到的数据」(框架采集与更新的职责);策略需要的中间状态、临时变量、推导状态(目标意向/纪律计数/回退集/计划/防重入标志/推导缓存)都是**策略器的内容**——策略器一局内存活、自己持有;执行层状态(拖拽失败计数/发射连败/事件防重入)归画面 op/执行层。本设计件把「策略实例无状态、状态全放 session」的历史妥协纠正回职责本位。
> **读者** = 无会话历史的工程师/智能体。术语首次出现给定义。
> **修订记录**:r1 对抗回炉(审查 2b362e40,发现清单 = `session_design_attack/发现清单.md`(原始件已灭失,2026-09-12 清理))——A1 补动态属性清册段(§2.6,24 项)并消解遥测承诺矛盾;A2 五字段退役改判迁出(v2_state/locked_line/bridge_id→§2.3,v2_round_*→§2.4),退役降为 4 项全部带前置动作;A3 sim 前提修正(§3.4/§5.6,撤回「零改动」);B1 megastar 落点定案局容器;B2 六处漏消费点补入 §5;B3 恢复局两行评级升「中」+6.2-4 判读义务;B4 create_state 非 abstract 兼容条款;建议 C1/C2/C3 全部采纳,已就地标注。

## 0. 术语(首现定义)

- **观察数据**:框架从游戏画面采集/推导的对局事实(血量/金币/牌面/板凳/等级/连胜/节点类型/词缀/池状态/已持投资策略等)。判据 = **谁产生**:框架读屏与识别层守卫产生;策略器只读。
- **策略器状态**:策略推导产生、供后续决策消费的中间状态(意向状态机/定型信号累积/回退集/纪律计数/遥测分键容器)。生命周期 = 一局(局首建、局终灭)。
- **执行层状态**:动作执行与画面 op 运行产生的状态(拖拽失败计数/发射连败/防重入标志/对账期望账)。产生者 = op/执行侧代码,不是读屏采集。
- **策略器(StrategyActor)** = 策略实现包(`strategies/impl/mandate_v1/`)的决策本体(bridge/entry/mandate/shop 等),经契约接口被流程侧调用(flow/README.md §2;后契约形状 = 每局冷建 2 + 分画面决策入口 11)。
- **StrategySession(session)** = 现行一局跨步状态载体 dataclass(`kernel/cw_strategy_session.py`)。
- **恢复局(接管形态)** = server/进程重启后 `cw_match` 不在,外循环识别到对局中途画面并重建 match 继续跑的形态(outer_loop.md §1 新局兜底、§3 恢复局检测)。
- **黑盒状态对象** = 框架只搬运引用、不识内部结构的策略器状态载体(§3.1 裁决 2)。

## 1. 现状与问题(session 三类混装)

现状 session 一个 dataclass 混装三类字段(§2 清册):观察数据、策略器状态、执行层状态,另有已退役残字段。历史成因 = 「策略实例无状态」约定(flow/README.md §2.5:策略实例不持可变每局状态,跨步状态走 session)——该约定把策略器的中间状态外置到框架载体,产生三类后果:

1. **职责不可判读**:读 session 字段无法判断「这是画面事实还是策略推导」——`v3_intention`(策略意向状态机)与 `last_hp`(结算屏真值)同住一个类。
2. **契约污染**:kernel 判据层(cw_intention/cw_evolution/cw_discipline_rules)以 `session.v3_*` 类型注解消费策略器状态——判据层对「框架载体上的策略内部结构」产生字段级耦合,session 文件头自述的 kernel 驻留理由(避 kernel→decision 断环边)反被字段本身破坏。
3. **生命周期契约缺失**:`memory` dict 之前,策略临时变量逐个升 dataclass 字段才能存活;升字段 = 框架载体收编策略私有状态,退役字段堆积(v2_state/v2_prev_hp 等 §2 清册「退役」段)即该机制的账单。

**目标态一句话**:session 只剩观察数据(+框架设施 rng/performance);策略器状态 = 实现包自定义的状态对象,由框架按局创建引用、所有权归策略器;执行层状态 = 执行侧载体(画面 op 实例/流程侧容器),不进 session。

## 2. 三类字段清册(逐字段)

**归类判据(四问,按序)**:① 谁产生(框架读屏/识别守卫 vs 策略推导 vs op 执行)?② 谁消费(策略决策/执行重试/遥测)?③ 生命周期(帧/节点/环/局)?④ 有无除 session 外的自然宿主(画面 op 实例、执行侧 tracked 账、流程侧计数器)?

统计(**清册全集对账:dataclass 字段 79 + 动态属性 25(`cw4_counters` + §2.6 的 24 个)= 104 项**)。dataclass 侧:**观察 28 项(留)+ 框架设施 2 项(留)+ 策略器 28 项(迁出,含动态属性 `cw4_counters`)+ 执行层 16 项(迁出)+ 退役 5 项(全部带前置动作)**;动态属性侧另有 **24 项(迁出,§2.6)**。策略器迁出合计 **52 项**(28+24)。清册全集来源声明:dataclass 字段枚举自 `cw_strategy_session.py` 全文;动态属性枚举自两源并集——`flow.py on_match_start` 清零段(`flow.py:120-180`,20 个)+ 消费侧惰性建 4 个(`v3_registry`/`v3_dir_refresh_used`/`v3_alloc_frame`/`v3_reserve_cap`)。两源并集即迁移账本全集,逐项有落点(初版清册漏动态属性段,对抗审查 A1 修订补入)。

> **as-built 字段账对账**(实施批落位实际数,账外收编逐波清单单一源 = 「落位裁量」节):实际落点 **MandateState 72 具名 + scratch dict** = 本篇清册 52 + 账外第一波 9 + 账外第二波 11;**ExecState 22 具名** = 本篇清册 16 + 账外第二波 6。两波账外字段均为实施批按 §6.1「账外字段一律视为范围遗漏」收编的实装 grep 发现项(产生者/消费者与清册同族),按本篇自己的对账规则回写入账,防止下批按清册找字段归属系统性误导。

### 2.1 观察数据——留 session(27 项)

| 字段 | 产生者 | 消费者 | 生命周期 | 备注 |
|---|---|---|---|---|
| `last_state` | 框架 read_game_state | overlay handler 读 comp 近似 | 帧覆写 | 备战快照 |
| `last_hp` / `last_hp_t` | 结算屏采集 | gated_hp 新鲜度门→prep hp | 节点 | 结算真值链 |
| `last_hp_real` / `last_hp_real_node` | 备战屏真值帧 reconcile | hp_trusted 帧龄门 | 帧/节点 |  对账锚 |
| `hp_suspect` | 识别层拒信守卫 | 守卫自身复现确认 | 节点内 | 识别质量通道,非策略输入 |
| `last_node_type` / `node_type_current` / `upcoming_types` | 节点行探针(read_node_sequence) | on_round_end 遥测、director 判节点 | 帧/节点 | 仿 last_hp 模式 |
| `plane_node_table` / `plane_node_table_plane` / `plane_lengths_seen` | 位面首帧探针 | cw_plane_table.schedule_of、离线统计 | 位面/局 | |
| `nodeseq_probe_anchor` | 框架探针 | 探针防重 | 节点 | 左移推断轮锚 |
| `last_streak` | 结算屏「连胜×N」 | economy C 杠杆 | 节点 | 方向语义在符号 |
| `last_level_obs` | read_level + 单调守卫 | 等级读数消误 | 局 | 识别层守卫状态 |
| `active_strategies` | 选卡 handler 采集 | read_game_state 拷入 state | 局 | 已持投资策略 |
| `effect_inventory` | 挂点采集(现仅升级挂点) | 决策路径待接线 | 局 | ActiveEffectInventory 纯数据 |
| `last_owned_equips` | 备战入口观察装配点全量重写(主写端,P4 接线 T-171)+ 穿戴 pass 执行位步内覆写 | state.equips 遥测、载体中继兜底 | 帧 | ;决策输入(门①/工具评估/计划产出位)已切黑板帧 owned_equips,勿回接本镜像 |
| `chosen_megastar` / `chosen_partner` | 选择 handler | 遥测回写 state | 局 | 复盘维度 |
| `star_pending_regression` | 识别防抖(合成动画窗确认) | star 真值采信 | 节点内 | 框架识别守卫 |
| `briefing_affixes` / `briefing_bosses` / `selected_difficulty` / `enemy_difficulty` / `active_env` | 简报/入口屏/情报屏采集 | mechanics_fit/boss_fit/保血阈值 | 局 |  保位勿滤 |
| `prep_obs_frame` | 入口观察段(唯一读屏点) | decide_prep_screen | 帧覆写 | 备战黑板帧 = 纯视觉/占用观察载体(PrepObservation;帧保留域封闭清单见其 dataclass 定义,局内事实不在帧上);备战决策读 = session 容器单例 `board_state_of`(容器域)+ 帧视觉域并读;黑板写读契约与 None 帧失约保留(W971) |

> 帧代次标注槽 `prep_frame_class`/`shop_frame_class` 留 session(帧语义注记,非游戏事实):`shop_frame_class` 标注对象 = **最近一次商店域容器观察写点**(入口观察段喂入/续段重观察)——商店黑板槽 `shop_state_frame` 已随两态制收口退役删除,容器 = 商店决策读单源;`prep_frame_class` 标注对象 = 同名黑板帧最近一次写入。本表按槽退役后现态列 27 项(统计行与 §4 结构图为清册时点数,含该槽)。

### 2.2 框架设施——留 session(2 项)

| 字段 | 说明 |
|---|---|
| `rng` | 种子契约锚(公平/replay);default 固定种子 0,消费方显式注入。非三类任一,属框架基础设施 |
| `performance` | 观测反馈跟踪器(双侧 OCR),框架采集域 |

### 2.3 策略器状态——迁出至策略器状态对象(28 项,含动态属性 `cw4_counters`;as-built 实际落点 72 具名 = 52 清册 + 账外两波 20,清单见 「落位裁量」节)

| 字段 | 产生者 | 消费者 | 生命周期 | 迁出落点(目标态归属) |
|---|---|---|---|---|
| `target_comp` / `target_drought` / `pending_deploys` / `transition_framework` | update_target 策略推导 | 部署/买入/卖出决策 | 局/轮 | MandateState.意向面 |
| `commit_signals` / `stash_comp` / `commit_flip_pending` / `focus_factions` | 定型信号推导 | update_target 线选择 | 局 | MandateState.定型面 |
| `last_candidate_scores` / `last_candidate_scores_round` | 选线轮评分推导 | 遥测、shop 侧陈旧判定 | 轮 | MandateState.推导缓存 |
| `v3_intention` | cw_intention 状态机(策略判据层) | kernel/mandate/sim 广域只读 | 局 | MandateState(核心意向状态机) |
| `v3_evolution` / `v3_core_names` / `v3_mode` / `v3_alarm` / `v3_pending_rollback` / `v3_prev_hp` / `v3_last_intention_event` / `v3_intention_key` | 意向/演进/纪律推导 | mandate_v1 决策、on_match_start 清零 | 局/轮 | MandateState |
| `v3_blood_budget_rejects` / `v3_blood_budget_refresh_rejects` | 血预算拒付披露(策略) | 遥测 | 局 | MandateState |
| `v3_handoff` / `v3_handoff_plane` | P2 承接快照(策略计算) | decide_prep | 位面 | MandateState |
| `v3_posture_unfulfilled` | 仲裁帧级重算(策略) | 对账门遥测 | 帧 | MandateState |
| `cw4_counters`(动态属性,非 dataclass 字段) | 策略行为观测分键(mandate_v1/encounter/shop/entry 多点写) | decisions 行、cw4_counters.jsonl 局终快照、sim 轮差分账本、A/B 披露 | 局 | MandateState;**遥测消费线必须随迁保持可读**(§5.4) |
| `v2_state` / `locked_line` / `bridge_id` | 决策层相位元组/锁线/桥线(初版误判退役;对抗审查 A2 改判——**活读端** = cw_op_buy_cards.py:658-662 直接属性访问入 decisions 行,**活写端** = sim/engine_p1.py:672/701,见 §5.6) | decisions 行遥测 | 局 | MandateState.相位面(sim 初始相位改经状态构造,§5.6) |
| `memory`(dict) | 策略 scratch | 策略临时变量 | 局 | **随切换直接消解**(§6.3,用户裁定) |

### 2.4 执行层状态——迁出至执行侧载体(16 项;as-built 实际落点 22 具名 = 16 清册 + 账外第二波 6:`last_prep_action_sig`/`_supply_detour_done`/`cw_prep_pending_accts`/`cw_takeover_collect_done`/`cw_takeover_tries`/`cw4_swap_arm_on`,见 「落位裁量」节)

| 字段 | 产生者 | 消费者 | 生命周期 | 迁出落点(目标态归属) |
|---|---|---|---|---|
| `deploy_fail_counts` | 部署拖拽执行失败 | DeployMove 跳过重试 | 局 | 执行侧(CwOpDeploy/PrepActionExecutor 载体) |
| `equip_drag_fail_counts` | 装备拖拽执行失败 | CwOpEquipAll 拉黑 | 局 | 同上 |
| `launch_dead_streak` | 出战发射连败 | 停机钩子 cw_launch_dead | 跨环 | 执行侧发射器载体 |
| `megastar_candidate_clicked` | 巨星 handler 点击执行 | handler 防重入 | handler 访问内 | **`ctx.cw_match` 级局容器(定案,不留实施批裁量)**——字段定义理由(session 文件:123-124)恰是「防 new CwScreenMegastar instance 重置 instance flag → 重选卡死」,落 op 实例 = 每次新建实例清零 = 原始事故按定义复发(对抗审查 B1 改判;初版落点作废) |
| `_supply_refresh_used` / `_encounter_refresh_used` | 补给/遭遇刷新点击执行 | handler 防重入(screen_op.md §8.4 裁 carried/执行侧) | 节点 | 画面 op 实例/节点级执行载体 |
| `defer_count` | DeferSpheres 控制流计数(框架流程侧) | 门=2 防空转环;battle_wait 复位 | 环 | 流程侧载体(flow/README §2.2「defer 计数归框架」本就非策略) |
| `star_regression_count` | star 回退停机钩子计数 | 停机钩子判定 | 节点×2 | 执行侧停机钩子载体 |
| `bail_reason_counts` | BailToOuter 流程事件 | ping-pong 诊断 | 局 | 流程侧载体 |
| `tracked_bench_chars` / `tracked_deployed` | 执行侧跟踪账(随动更新) | 双账断言(screen_op.md §2.3(ii)) | visit 内 | 执行侧 tracked 账(现状归 session 属历史宿主错位) |
| `v2_round_key` / `v2_round_sold` | 同轮买卖互斥事实账本(初版误判退役;对抗审查 A2 改判——**活写端** = `kernel/cw_round_ledger.py:30-34` 带轮键自校验登记,**live 调用方** = cw_shop_action_ops.py:487 卖出落地路径) | cw_round_ledger 仲裁守卫 + 执行侧幂等加固 | 轮(轮键自校验) | **执行侧轮账本**(随 cw_round_ledger 宿主迁出;kernel 对执行账的访问口见 §5.5) |
| `pending_buy_expect` / `xp_expect_ledger` | 期望账构建(执行对账) | heavy 定型帧对账 | 单元/局 | 执行侧对账载体 |
| `expected_state` | apply_op_effect 到账登记 | reconcile_expected 覆盖点 | visit 内 | 执行侧期望对账容器 |

### 2.5 退役字段——删除(5 项,全部带前置动作)

> 对抗审查 A2 修订:初版 5 个字段标「已核无人读写」与现状不符,已逐个改判迁出(§2.3/§2.4);退役判据改为一律**列前置动作**,不使用「已核无人读写」类置信标签。

| 字段 | 退役依据 | 前置动作(切换批内完成) |
|---|---|---|
| `dual_track_phase` | 读点归零(文件注释+);**但回放恢复路径有活写端** `sim/cw_replay.py:152`(回放恢复时写回) | 删 `cw_replay.py:152` 写行(该行恢复的是已无消费的老栈字段,恢复语义消失 = 退役语义的一部分,显式声明非静默) |
| `v2_ever_full_interest` | 仅冻结 default 栈读写,唯一写点 = `flow.py:152` 局首复位 | 写点随 `on_match_start` 重写(§5.2)自然消失,核归零后删 |
| `v2_prev_hp` | v1 遗留,后无读无写 | 无前置,直接删 |
| `v2_round_bought` | 同轮已买集:唯一写端 = `flow.py:139` 局首清零(cw_round_ledger 只登记卖侧,买侧集无登记写端);互斥消费语义现状由轮键重置段空转 | 写点随 `on_match_start` 重写消失;核无仲裁读端后删——若切换批核对发现仲裁守卫活读此集,则改判随 cw_round_ledger 宿主迁出(与 `v2_round_sold` 同容器),禁带疑删除 |
| `v2_seed_bought` | 唯一写端 = `flow.py:151` 局首清零 → 该 dict 现状**恒空**,种子年龄豁免(cw_discipline_rules.py:161)已结构性失效 | kernel 死码收口:删 `cw_discipline_rules.py:161` 读段(恒空输入的豁免分支)+ `flow.py:151` 写行——豁免失效是现状既成事实,切换批把它显式收口而非延续假账 |

### 2.6 动态属性——迁出至策略器状态对象(24 项)

> 对抗审查 A1 修订补入:这些属性无 dataclass 字段定义,靠动态 setattr 挂 session(初版清册只收了 `cw4_counters` 一个,缺 1/4)。枚举源 = `flow.py:126-180` on_match_start 清零段(20 个)+ 消费侧惰性建 4 个。**全部归类策略器状态**(产生者 = 策略推导/决策层簿记,消费者 = 决策与遥测,生命周期 = 局/轮),全部迁 MandateState:

| 组 | 属性(逐个) | 产生者/消费面备注 |
|---|---|---|
| 相位与镜像(每轮重算) | `v3_phase` / `v3_form_ok` / `v3_b_t` / `v3_dp_posture` / `v3_mirror_key` | write_shop_mirrors 每轮写;`v3_form_ok` 有 sim 直写点(engine_p1.py:1098,§5.6) |
| 成型停手 | `v3_formed_stop` | ;**行为面消费** = cw_screen_prep.py:2173 决策豁免联动 + cw_op_buy_cards.py:639 入 decisions 行(非纯遥测) |
| 补偿/稳态簿记 | `v2_remedy_used` / `v2_steady_lv_used` / `v3_steady_lv_abandoned` / `v3_remedy_abandoned` |  跨局清零计数 |
| 轮笔数披露 | `v2_round_refreshes` / `v2_round_p1_early` / `v2_round_p2_core` / `v2_round_press_exempt` / `v2_round_press_copy` | decisions/遥测判读面 |
| 泄息指令与承接门 | `v3_release` / `v3_release_round` / `v3_release_spent` / `v3_handoff_gap` / `v3_handoff_hp_proj` | W332b/w227;`v3_release_spent`/`v3_reserve_cap` 是遥测透传源(telemetry/schema.py:424/433、recorder.py:241/250) |
| 消费侧惰性建 | `v3_registry`(A/B 注册表注入通道,cw_economy.py:662 消费)/ `v3_dir_refresh_used`(刷新消耗计数,cw_registry.py:836)/ `v3_alloc_frame`(DP 姿态轮帧缓存,engine_p1.py:961/1267)/ `v3_reserve_cap`(储备线披露,engine_p1.py:1300) | 惰性建模式迁 MandateState 具名字段(缺省值即现惰性初值) |

**遥测承诺精确化(消解「session 只剩 30 项」与「遥测 schema 零改」的表面矛盾)**:§6.1 迁移清单**扩大到全部 104 项**(含本节 24 个动态属性);遥测承诺收窄为——**decisions/schema/jsonl 的序列化 schema 与格式零改,但全部数据源读点改为经访问函数抽自 MandateState**。session 字段数与遥测 schema 本就无蕴含关系(动态属性从来不进 asdict,遥测可见性从来全靠显式读点),初版「schema 零改」表述未点明该依赖链,此处显式化(对抗审查 C1 采纳)。

## 3. 策略器一局存活契约(三个显式问题)

### 3.1 裁决 1:载体形态 = 黑盒状态对象挂 session,所有权归策略器

**裁决**:session 增加单一黑盒字段 `strategy_state: object = None`;策略器状态类型由**实现包自定义**(如 `mandate_v1/mandate_state.py` 的 `MandateState` dataclass,收编 §2.3 全部 28 项 + §2.6 全部 24 项,合计 52 项;as-built 72 具名 + scratch,见 §2 统计行注);框架(策略管理器 `create_session`)在每局创建时调用实现包的工厂钩子建实例、写入 `session.strategy_state`,此后**框架只搬运引用,不读不写其内部**——所有权归策略器,生命周期管理(每局新建、局终随 session 销毁)归框架。

- **被否选项 A:策略管理器每局复用同一策略实例**(策略器变有状态单例)——否决理由:①策略实例现在是跨局长命对象,「每局新建 session」的清零保证失效,漏清零字段成为跨局污染源(现状 `on_match_start` 逐字段清零已多次出漏,`flow.py:120-180` 的清零清单本身就是该形态的补丁史);②sim 与 live 共享同一实例定义时,实例级可变状态让并发跑批/回放对拍不可复现;③换核热替换面(A/B 切 strategy_id)要求实例可随时丢弃——实例带状态则丢弃即丢局中状态,语义断裂。
- **被否选项 B:框架代管 dict(= memory 现状延伸)**——否决理由:①schema 不可见(asdict/telemetry 看不见),判读面盲区;②无类型与守卫,键名冲突靠纪律约束(memory 注释五条款全是纪律不是机制);③所有权名义归策略、宿主仍在框架载体——与目标态的定义矛盾,只是换个字段名继续混装。
- **被否选项 C:状态作为独立参数贯穿全部契约接口签名**——否决理由:契约接口 + bridge/entry/mandate/shop 全链签名改一遍,爆炸面最大,且签名携带的输入本就经 session 黑板(prep_obs_frame 同款),单独走参数属双通道。

**契约条款**:
1. `MandateState` 类型定义、字段、更新语义全部在实现包;kernel 判据层(cw_intention/cw_evolution 等)对策略状态的消费改经**访问函数**(取 `session.strategy_state` 后类型收窄),kernel 不再持有 `session.v3_*` 字段注解。
2. 框架侧唯一义务:`create_session` 时置初值、局终随 session 销毁、不复用上局引用(as-built 语义更新:生命周期收编后冷建与 live 初值统一在 create_session 唯一冷建口,原 `on_match_start` 逐字段清零/强制冷建钩子已删——状态对象每局新建即天然清零,「不复用上局引用」by construction 成立)。
3. 意向状态机的跨轮驱动重入守卫(现状 `v3_intention_key` 段级重入)语义原样搬入 MandateState,**不变**。
4. **遥测可见性依赖链显式化**(对抗审查 C1 采纳):黑盒字段不进 asdict/repr/遍历通道(全仓核过无 asdict(session)/deepcopy(session) 消费点,该面成立),动态属性现状的「asdict 完整」亦名存实亡——**迁移后遥测可比性完全依赖 §5.4 的访问函数抽读链,该链是唯一观测通道,任何新遥测字段必须从访问函数出发,禁直读 session 猜字段**。

### 3.2 裁决 2:恢复局语义 = 策略器状态保守冷启动

**裁决**:恢复局(server 重启后接管残局)下,session 观察数据由入口观察全量重建(现状 `discard_stale_match_container` + 新局兜底已有 by-construction 语义,flow/README §2.3),策略器状态**不可重建、不尝试重建**——以空 MandateState 冷启动,凭当帧观察数据重新驱动意向状态机(重锁线/重评演进)。丢失状态的语义逐类显式声明:

| 丢失的状态类 | 冷启动语义 | 风险评级 |
|---|---|---|
| 意向状态机(`v3_intention`) | 从未锁定态重驱动,凭现读 board/bench/持有重锁——可能锁到与重启前不同的线 | **中**:换线成本存在但决策仍自洽(意向状态机的输入是观察数据,不是历史意向);恢复局已有遥测标记可判读 |
| 掉血三臂记忆(`v3_alarm`/BloodAlarmTracker) | 归零 = 恢复轮内掉血三臂**哑火**——低血量时不停手/不升级/不进危机臂 | **中**(对抗审查 B3 改判,初版误标「低」):它是**触发器不是限制器**,归零的失效方向是「少保血」而非「保守」;恢复局恰是观察数据刚重建、最需要血线武器的时刻。缓解见 6.2-4 判读义务 |
| 纯限制器计数(拒付计数/defer 门/handoff 采样戳/稳态放弃计数) | 归零 = 「未发生过」语义 | 低:保守限制器,归零只放宽限制一轮,下个入口重估 |
| 同轮已卖集(`v2_round_sold`,§2.4 执行侧轮账本) | 空集 = 「同轮已卖禁买回」的**防永动机守卫**失效,恢复轮内先卖后买回的缩幅循环检查缺位 | **中**(对抗审查 B3 改判,初版沿现状注释写「只失去互斥」低估):不是单纯互斥丢失,是资金缩幅循环的在环防线缺失;恢复轮窗口有限(单轮轮键),下一轮键重置后自愈 |
| 回退集/已买集(`memory` 类) | 空 = 豁免暂时失效 | 低:与现状重启丢 session 同语义 |
| `cw4_counters` 遥测分键 | 局终快照只含恢复后增量 | 低:遥测断点,恢复局标记在场可判读;非行为面 |

**被否选项:策略器状态序列化进对局存档、恢复时反序列化**——否决理由:①序列化面 = 策略内部结构,框架存档装配(match_archive)将被迫理解 MandateState schema,黑盒契约破坏;②策略改版后旧存档反序列化的版本兼容是无底洞;③恢复局是低频路径,冷启动损失有限且上表逐类可观测——为一类低频路径引入持久化 schema 契约不成立。**显式战术权衡**:意向重锁可能换线,若实机判读显示恢复局换线致损显著,升级路径 = 只把「已锁定线 id」一个标量随 runs summary 落盘供恢复参考(框架可见、策略可读),不做全量序列化——此为后备,不进本设计承诺。

### 3.3 裁决 3:热替换面 = 局边界丢弃冷启

**裁决**:换策略实现(切 strategy_id)只允许发生在**局边界**(现状 config 切换即局粒度,flow/README §2.4 换核机制不变);替换时旧状态对象整体丢弃、新实现的状态对象由其工厂冷建——因为状态类型是各实现包私有,跨实现的状态迁移**不定义**(不做映射搬移)。局中不允许热替换(无此需求,现状亦无通道)。

- **被否选项:新旧实现状态兼容层/迁移函数**——否决理由:状态是策略私有推导,A 实现的状态对 B 实现无语义;兼容层会把两个实现的内部结构耦合进一个迁移模块,正是本次要消灭的耦合形态。

### 3.4 与 sim 侧策略实例生命周期的对齐

**现状(对抗审查 A3 修正,初版前提与现状相反)**:sim 引擎**不经** `create_session`——三处裸构造:`sim/engine_p1.py:670`、`:699`(`sess = session or StrategySession(rng=random.Random(...))`,session 参数为注入通道)、`sim/engine_p2.py:132-133`(注释明言禁裸构造的 OS 熵默认入 sim);且 sim **现状就直写策略字段**:`engine_p1.py:672`/`:701`(`sess.v2_state = ('economy', ...)`,给决策层喂初始相位)、`:1098`(`sess.v3_form_ok = True`,镜像投影);create_session 的 sim 侧唯一消费方 = `sim/cw_replay.py:195`(回放工具,非引擎主路径)。sim 另对 `v3_intention`/`cw4_counters`/`v3_dir_refresh_used`/`v3_alloc_frame`/`v3_reserve_cap` 广域只读(engine_p1.py:930/1158/1264-1300/2103/2248/2422 等)。

对齐裁决(**sim 侧有实质改造,「零改动」断言撤回**):
1. **构造**:三处裸构造改经统一 sim 侧构建口(候选 = 引擎入参接被测策略的 create_session/state 工厂,或 sim 内薄 helper 调工厂),保证 sim/live 状态生命周期同源;`session` 注入参数通道保留(回放/进场态复用 session 时,`strategy_state` 为 None 的处理 = 由该口惰性走工厂补建,禁留 None 进决策)。
2. **写点**:`v2_state` 初始相位(672/701)改经 MandateState **构造参数/初始化入口**(初始相位是策略状态的合法初始化输入,不再事后 setattr);`v3_form_ok` 写点(1098)属镜像投影面——sim 与 live 共享同一镜像函数(write_shop_mirrors 等价),写经状态对象,禁裸 setattr。
3. **读点**:全部 getattr 消费改经访问函数(与 live 同一口),读取口径逐字节一致。

## 4. 目标态结构(双态)

```
【现状(as-is)】                          【目标态(to-be)】
StrategySession(104 项混装:              StrategySession(30 项:观察 28 + 设施 2
  dataclass 79 + 动态属性 25)              + strategy_state 黑盒引用)
  ├─ 观察数据                              │   └─ MandateState(实现包私有,52 项:
  ├─ 策略器状态(dataclass 28+动态 24)     │        dataclass 28 + 动态 24)
  ├─ 执行层状态(16 项)                    │
  └─ 退役残字段(5 项)                    执行侧载体(16 项:局容器/op 实例/流程容器)
                                          退役残字段:物理删除(5 项,带前置)
```

> as-built 实际数(账外两波收编后):MandateState 72 具名 + scratch;ExecState 22 具名——逐波清单与对账见 §2 统计行 as-built 注。

## 5. 影响面逐项声明

### 5.1 策略管理器、注册壳与 create_session 直调点

- `cw_strategy_manager.py`:`create_session` 增「调用实现包状态工厂」一步(ABC 工厂接口 `create_state(config) -> object`,非 abstract)。
- **第三方插件兼容条款**(对抗审查 B4 采纳):CwStrategy 是 plugins/currency_war_strategies 的参赛入口契约,新增 **abstract** 钩子会让所有存量第三方策略实例化后调 create_session 即 TypeError。裁决:`create_state` 定义为 **ABC 非 abstract 钩子,基类缺省实现返回 None**——存量第三方策略零破坏(None 态 = 策略器可沿用惰性建模式,与现状 cw_intention.py:1695-1702 惰性建同构);mandate_v1 覆写返回 MandateState。不做插件契约版本化(非 abstract 缺省已消除破坏面,版本化属过度设计)。
  **B4 承诺收缩申报(as-built,「落位裁量」节同文)**:「零破坏」收缩为「缺省 None **不炸策略构造与 create_session**」;**不承诺**框架行为面读点(ops 主链决策输入等)容忍 `strategy_state=None`——第三方策略未覆写 create_state 且无工厂注册时状态恒 None,进入行为面读点 = AttributeError 显式炸错(mis-assembly 信号,优于静默产 None 假数据)。判据/披露面(kernel 判据、遥测披露键)维持防御 getattr 形态(异型状态对象字段缺席退缺省)。两形态划分与 None 契约单一源 = `strategy_state_of` docstring。附带工厂契约:`create_state(config)` 的 config **可忽略、可为 None**(sim 注入桩面传 None,工厂实现禁读 config 取值)。
- **create_session 直调点两处纳入改造面**(对抗审查 B2-6 补):`sim/cw_replay.py:195` 与 `operations/cw_op/cw_op_buy_cards.py:497` 绕过 StrategyManager 直调 `strat.create_session(config)`——两处的状态工厂语义随 §5.1 钩子自动生效(直调的就是 ABC 方法),核对项 = 直调后 session.strategy_state 非 None。
- 注册壳 `mandate_v1_strategy.py`:零判据纪律不变;仅透传工厂。

### 5.2 中间 ABC(`strategies/impl/flow.py`)

- 生命周期冷建(`on_match_start` 清零段 `flow.py:120-180`,对抗审查 C3 引用校准)对 MandateState 字段的逐项清零**整体消失**——状态对象每局新建即天然清零(as-built:该钩子随生命周期收编物理删除,冷建与 live 初值归 create_session 唯一冷建口)。
- 方向刷新/`decide_*` 内对 `session.v3_*`/`session.commit_*` 的读写改经 `session.strategy_state`(访问函数收窄类型);ABC 不定义 MandateState 内部结构(它是实现私有)。

### 5.3 bridge 透传与 kernel 判据层

- `mandate_v1/bridge.py` 及 entry/mandate/shop/assembly 的 `session.v3_intention` getattr 族:改访问函数后调用点机械替换,签名不变。
- kernel(cw_intention/cw_evolution/cw_economy/cw_deploy_logic/cw_discipline_rules/battle_calib)对 `session.v3_*` 的消费:改访问函数;**kernel 对 session 的字段注解依赖随之消失**——session 文件头「驻 kernel 理由」弱化为「观察数据载体被 kernel 判据消费」,不再需要防 kernel→decision 断环边。

### 5.4 序列化与遥测(decisions 行 / cw4_counters.jsonl / shop_snapshots / match_archive)

- decisions 行的 `v3_intention`/`sess_commit_scores` 字段(cw_op_buy_cards.py:623-666、cw_serialize.serialize_intention):**schema 零改**,数据源从 session 字段改为经访问函数抽自 MandateState——遥测跨版本可比性保住。
- `cw4_counters` 局终快照链(cw_loop:384/879/1356 → match_archive.record_cw4_counters_* → cw4_counters.jsonl → ab_core_swap 披露抽取):读点全改经访问函数;**sim 轮差分账本(engine_p1.py:1038-2358)同步换读点**。这是切换批最容易漏的断流点(动态属性 grep 不易枚举全),实施批须以「session 上除观察/设施外的 getattr 兜底全部清零」为完成判据。
- **shop_snapshots 流**(对抗审查 B2-1 补):`telemetry/recorder.py:820` 读 `session.v3_intention`(best-effort suppress,漏改 = 静默缺失)——换访问函数,并**纳入 6.2-2 对照面**(shop_snapshots 的 rho_obs 与 decisions 同 seed 对照)。
- **动态属性透传源**(对抗审查 A1 联动):`v3_reserve_cap`/`v3_release_spent`(telemetry/schema.py:424/433、recorder.py:241/250 `_w611_int` 读 session 动态属性)——换读自 MandateState,schema 字段零改。
- match_archive 的 decision_detail(v3_intention 帧,match_archive.py:416):同上换源。

### 5.5 执行层消费点

- `deploy_fail_counts`/`equip_drag_fail_counts`/`launch_dead_streak`:迁到执行器/动作 op 载体(CwOpDeploy、CwOpEquipAll、prep_actions 发射器),生命周期语义逐字段保持(局级/跨环)——载体落点实施批裁,候选 = `ctx.cw_match` 级执行态容器或 op 实例字段;**禁**为它们新开 session 字段。
- `tracked_bench_chars`/`pending_buy_expect`/`xp_expect_ledger`/`expected_state`:迁执行侧对账载体,双账断言语义不变(screen_op.md §2.3(ii))。**kernel 读写签名重构**(对抗审查 B2-5 补):`kernel/cw_reconcile.py:78`、`kernel/cw_expected_state.py:333` 对这组字段有读写签名——迁出后 kernel→执行侧载体的访问路径**必须定义**(候选 = 执行侧载体访问口注入 kernel,或对账入口收拢签名),禁让 kernel 直接 getattr session 猜新宿主——那是与 §1-2 同型的耦合换壳复活。
- `v2_round_key`/`v2_round_bought`/`v2_round_sold`(§2.4 新增):随 `cw_round_ledger` 宿主迁移——轮账本宿主从 session 改为执行侧容器,`register_round_sold` 的轮键自校验语义不变,live 调用方(cw_shop_action_ops.py:487)与仲裁消费点同步换宿主。
- 执行层读策略状态的既有点换访问函数(对抗审查 B2-2/3 补):`cw_op_deploy.py:1014`(读 v3_intention 取 locked_fac)、`cw_shop_action_ops.py:362`(读 cw4_counters)、`:395`(读 v3_intention)——执行层读策略状态的合法通道 = 访问函数,逐点改。
- `_supply_refresh_used`/`_encounter_refresh_used`/`defer_count`/`bail_reason_counts`/`star_regression_count`:按 §2.4 落点迁,防重入语义逐字段保持;`megastar_candidate_clicked` 按 §2.4 定案落 `ctx.cw_match` 级局容器。

### 5.6 sim 引擎

见 §3.4:**「零改动」断言撤回**——sim 侧实质改造点(对抗审查 A3 补齐,全部在切换批范围内):

| 改造点 | 现状锚点 | 改法 |
|---|---|---|
| 裸构造 ×3 | engine_p1.py:670、:699;engine_p2.py:132-133 | 统一 sim 侧构建口走被测策略工厂;session 注入通道保留,None 时惰性走工厂补建 strategy_state |
| 策略字段直写 ×3 | engine_p1.py:672/701(`v2_state` 初始相位)、:1098(`v3_form_ok` 镜像投影) | 前者改 MandateState 构造参数;后者改 sim/live 共享镜像函数写状态对象,禁裸 setattr |
| 广域只读点 | engine_p1.py:930/1158/1264-1300/2103/2248/2422(`v3_intention`/`cw4_counters`/`v3_dir_refresh_used`/`v3_alloc_frame`/`v3_reserve_cap`) | 全部换访问函数(与 live 同口) |
| cw4_counters 轮差分 | engine_p1.py:1038-1108/2192-2198/2355-2360 | 读点同上换;差分口径不变 |
| create_session 直调 | cw_replay.py:195(回放工具) | 随 §5.1 钩子自动生效,核对 strategy_state 非 None |

sim 决策逻辑与判据本体零改动(改的是状态通道,不改决策语义)。

## 6. 迁移方案:一次性原子切换(用户 2026-09-06 裁定)

> 原任务书按「契约先行→分期迁移→双轨并存→旧字段退役」框架命题;用户裁定**「这么小的事一次迁完」**,以下按裁定改写。被取代的分期/双轨框架不再展开,其有效残余(每期可独立验证的思想)吸收进切换批的验证清单。

### 6.1 切换批范围(单 commit)

契约(`strategy_state` 黑盒字段 + `create_state` 非 abstract 钩子)+ **§2.3 全部 28 项 + §2.6 全部 24 项迁 MandateState**(合计 52 项策略器状态)+ §2.4 全部 16 项迁执行侧载体 + §2.5 全部 5 项退役(含各前置动作:kernel 死码收口/cw_replay 写点删/v2_round_bought 带疑禁删条款)+ A2 改判字段(v2_state/locked_line/bridge_id/v2_round_key/v2_round_sold)的活读写点换源 + §5 全部消费点换读(含 5.4 遥测透传源/5.5 补点/5.6 sim 五类改造点)+ `memory` 消解(§6.3)。**不做分期、不设双轨期**:切换 commit 前 session 旧形态、commit 后目标态,无中间并存态——双写/双读纪律问题在单 commit 边界上构造性不存在。切换批范围以 §2 清册全集(104 项)为账本,**账外字段一律视为范围遗漏**(禁「清册外即不管」)。

### 6.2 验证清单(切换批完成判据,取代逐期实机验证)

1. 快速集测试全量通过(`uv run pytest sr-od-test/ -m "not slow"`)+ 直接受影响面慢桶一次全量。
2. 决策帧截图留证对照:同 seed sim 跑切换前后各 N 局,decisions 行/`cw4_counters`/**shop_snapshots**/`v3_intention` 序列化输出逐帧对照并**截图留证**(逐字节一致;不一致 = 读点漏改或语义漂移,逐处归因;留证物归对局档案,供对抗审查与用户二次确认调阅)。
3. grep 完成判据(对抗审查 C2 采纳,范围扩到全集):对**清册全集 104 项逐一**做 session 形态访问归零 grep——含 §2.3/§2.6 迁出字段(`session.v3_*`/`session.v2_*`/`session.commit_*`/`session.cw4_counters`/`session.memory` 及 `getattr(session|sess, '<键>')` 动态属性形态)、§2.4 执行层字段(`deploy_fail_counts` 等)、§2.5 退役字段名(直接属性访问形态,防 cw_op_buy_cards.py:658-660 类 AttributeError)——任何一项在 session 形态上有残留访问即不收口。
4. 实机局 ≥1 局跑通 + 恢复局形态一次手工验证(重启 server 接管残局,核对 §3.2 冷启动语义与恢复局遥测标记),**并加两项行为面判读**(对抗审查 B3 采纳):①恢复轮血预算披露(掉血三臂哑火面——拒付计数/停手动作判读,确认「少保血」风险窗口实际影响);②恢复轮同轮买卖序列判读(防永动机守卫缺位窗口内无卖后买回缩幅循环)。

### 6.3 `memory` 的消解(不设过渡)

`memory` dict(2026-09-06 刚落地)在切换批直接消解:其既有键并入 `MandateState` 具名字段(高频/需守卫的)或 MandateState 内的 scratch dict(一次性键,纪律条款原样平移——键名模块前缀/局级生命周期/不入 decisions)。**不保留 session.memory 作为过渡通道**——保留即等于保留「框架载体收编策略私有状态」的反模式本体。

## 7. 风险与回滚

### 7.1 回滚方式

单 commit 原子切换 ⇒ 回滚 = `git revert` 该单 commit,工作树回到现状形态,无残留半态(原子切换在此点优于分期:分期回滚需逐期对账字段双态)。测试仓同步 revert 同批测试改动。

### 7.2 最大行为风险点(按序)

1. **恢复局语义变化**(§3.2):现状恢复局丢 session 与切换后丢 MandateState 行为面等价(都是保守冷启动),但意向重锁路径从「session 空 v3_intention 惰性建」变为「工厂显式冷建」——语义应逐字节一致,风险在读点漏改导致恢复局行为分叉。**恢复轮两个已评级「中」的行为面**(掉血三臂哑火/同轮已卖守卫缺位)有专项判读义务(6.2-4),非仅「跑通」。
2. **遥测断流**:`cw4_counters`/`v3_intention`/`v3_reserve_cap`/`v3_release_spent` 等序列化读点散布 sim/telemetry/operations 三域(§5.4),漏一处 = 该域数据静默缺失(非炸错)。缓解 = grep 完成判据(6.2-3)+ 决策帧与 shop_snapshots 逐字节对照(6.2-2)。
3. **执行层迁出改变了防重入/失败计数的宿主生命周期**:落点若选错(如挂 op 实例而 op 每访问重建),计数提前清零,防线失效——§2.4 每字段标注了原生命周期,实施批逐字段核对落点生命周期 ≥ 原生命周期(`megastar_candidate_clicked` 已按 B1 定案局容器,不留裁量空间)。
4. **退役字段的静默/炸错双形态**(对抗审查 A2 升级):直接属性访问的残余读点(cw_op_buy_cards.py:658-660 类)删除即首商店帧 AttributeError;`cw_replay.py:152` 对 `dual_track_phase` 的 setattr 删字段后**不炸但静默丢恢复语义**——两类都在 §2.5 前置动作 + 6.2-3 全字段 grep 判据辖内,无「已核」标签兜底。
5. **sim 改造面失真**(对抗审查 A3 撤回「零改动」后显式化):三构造点/三写点/五类只读点任一漏改 = sim 起跑即崩(构造)或状态通道口径分叉(读写),后者会被 6.2-2 同 seed 对照抓;构造类崩溃首局即暴露,风险在排查成本非隐蔽性。
6. **kernel 判据层换访问函数引入 import 方向问题**:访问函数落点须不造 kernel→impl 断环边(候选 = kernel 内薄读口 `strategy_state_of(session)` + TYPE_CHECKING 收窄,实施批裁);kernel 对执行层字段的读写签名重构(§5.5 cw_reconcile/cw_expected_state)同此判。
