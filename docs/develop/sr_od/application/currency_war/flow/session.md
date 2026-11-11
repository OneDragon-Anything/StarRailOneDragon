# Session 职责分离(session 三类状态分离,as-designed)
> 术语:本篇所用货币战争域术语的统一定义见 [../terminology.md](../terminology.md)。

> **状态声明**:本篇是 **设计件 (as-designed)**,非现状描述。目标态与现状在正文内显式区分 (双态标注先例 = `sim/sim-design.md`);现状描述从 `kernel/cw_strategy_session.py` 反推(路径根 = `src/sr_od/application/currency_war/`,下称 session 文件)与各消费点 (grep 直调行号见清册)。迁移方案按用户 2026-09-06 裁定为 **一次性原子切换**(流水-20260906.jsonl 18:47 行)——原任务书的「分期迁移+双轨并存」框架被该裁定取代,§6 如实记录被取代的框架以保留推理链。
> **与 GameState 的分工边界**:本篇管 **StrategySession**(局身份 + 观察数据 + `strategy_state` 策略状态黑盒 + 框架设施);局内已知事实快照状态容器(GameState) = **GameState**(`kernel/cw_game_state.py`,单例宿主 = session 旁表 `game_state_of`——session 对象即局身份,两者共存非替代)。GameState 设计权威版本 = `game_state/README.md`(总纲)+ `fields.md`(字段级规格)。
> **来源裁定**(用户 2026-09-06):session 的本义 = 只承载「从游戏画面观察到的数据」 (框架采集与更新的职责);策略需要的中间状态、临时变量、推导状态 (目标意向/纪律计数/回退集/计划/防重入标志/推导缓存)都是 **策略器的内容**——策略器一局内存活、自己持有;执行层状态 (拖拽失败计数/发出连败/事件防重入)归画面 op/执行层。本设计件把「策略实例无状态、状态全放 session」的历史妥协纠正回职责本位。
> **读者** = 无会话历史的工程师/智能体。术语首次出现给定义。
> **修订记录**:r1 对抗回炉 (审查 2b362e40,发现清单 = `session_design_attack/发现清单.md`(原始件已灭失,2026-09-12 清理))——A1 补动态属性清册段 (§2.6,24 项)并消解遥测承诺矛盾;A2 五字段停用改判迁出 (v2_state/locked_line/bridge_id→§2.3,v2_round_*→§2.4),停用降为 4 项全部带前置动作;A3 sim 前提修正 (§3.4/§5.6,撤回「零改动」);B1 megastar 落点定案局状态容器;B2 六处漏消费点补入 §5;B3 恢复局两行评级升「中」+6.2-4 判读义务;B4 create_state 非 abstract 兼容条款;建议 C1/C2/C3 全部采纳,已就地标注。

## 0. 术语(首现定义)

- **观察数据**:框架从游戏画面采集/推导的对局事实(血量/金币/牌面/板凳/等级/连胜/节点类型/词缀/池状态/已持投资策略等)。判据 = **谁产生**:框架读屏与识别层守卫产生;策略器只读。
- **策略器状态**:策略推导产生、供后续决策消费的中间状态(意向状态机/定型信号累积/回退集/纪律计数/遥测分键状态容器)。生命周期 = 一局(局首建、局终灭)。
- **执行层状态**:动作执行与画面 op 运行产生的状态(拖拽失败计数/发出连败/防重入标志/对账期望账)。产生者 = op/执行侧代码,不是读屏采集。
- **策略器(StrategyActor)** = 策略实现包(`strategies/impl/mandate_v1/`)的决策本体(bridge/entry/mandate/shop 等),经契约接口被流程侧调用(flow/README.md §2;后契约形状 = 每局全新创建口 2 + 分画面决策入口 15 = 17)。
- **StrategySession(session)** = 现行一局跨步状态载体 dataclass(`kernel/cw_strategy_session.py`)。
- **恢复局(接管形态)** = server/进程重启后 `cw_match` 不在,外循环识别到对局中途画面并重建 match 继续跑的形态(outer_loop.md §1 新局兜底、§3 恢复局检测)。
- **黑盒状态对象** = 框架只搬运引用、不识内部结构的策略器状态载体(§3.1 裁决 2)。

## 1. 现状与问题(session 三类混装)

现状 session 一个 dataclass 混装三类字段(§2 清册):观察数据、策略器状态、执行层状态,另有已停用残字段。历史成因 = 「策略实例无状态」约定(flow/README.md §2.5:策略实例不持可变每局状态,跨步状态走 session)——该约定把策略器的中间状态外置到框架载体,产生三类后果:

1. **职责不可判读**:读 session 字段无法判断「这是画面事实还是策略推导」——`v3_intention`(策略意向状态机)与 `last_hp`(结算屏真值)同住一个类。
2. **契约污染**:kernel 判据层(cw_intention/cw_evolution/cw_discipline_rules)以 `session.v3_*` 类型注解消费策略器状态——判据层对「框架载体上的策略内部结构」产生字段级耦合,session 文件头自述的 kernel 驻留理由(避 kernel→decision 断环边)反被字段本身破坏。
3. **生命周期契约缺失**:`memory` dict 之前,策略临时变量逐个升 dataclass 字段才能存活;升字段 = 框架载体代管策略私有状态,停用字段堆积(v2_state/v2_prev_hp 等 §2 清册「停用」段)即该机制的账单。

**目标态一句话**:session 只剩观察数据(+框架设施 rng/performance);策略器状态 = 实现包自定义的状态对象,由框架按局创建引用、所有权归策略器;执行层状态 = 执行侧载体(画面 op 实例/流程侧状态容器),不进 session。

## 2. 三类字段清册(逐字段)

**归类判据(四问,按序)**:① 谁产生(框架读屏/识别守卫 vs 策略推导 vs op 执行)?② 谁消费(策略决策/执行重试/遥测)?③ 生命周期(帧/节点/环/局)?④ 有无除 session 外的自然宿主(画面 op 实例、执行侧随动载体(已停用)、流程侧计数器)?

统计(**清册全集对账:dataclass 字段 79 + 动态属性 25(`cw4_counters` + §2.6 的 24 个)= 104 项**)。dataclass 侧:**观察 28 项(留)+ 框架设施 2 项(留)+ 策略器 28 项(迁出,含动态属性 `cw4_counters`)+ 执行层 16 项(迁出)+ 停用 5 项(全部带前置动作)**;动态属性侧另有 **24 项(迁出,§2.6)**。策略器迁出合计 **52 项**(28+24)。清册全集来源声明:dataclass 字段枚举自 `cw_strategy_session.py` 全文;动态属性枚举自两源并集——`flow.py on_match_start` 清零段(`flow.py:120-180`,20 个)+ 消费侧惰性建 4 个(`v3_registry`/`v3_dir_refresh_used`/`v3_alloc_frame`/`v3_reserve_cap`)。两源并集即迁移账本全集,逐项有落点(动态属性段已并入清册)。

> **as-built 字段账对账**(实施批落位实际数,计划外发现字段的逐波清单单一源 = 「落位裁量」节):实际迁移 **MandateState 72 具名 + scratch dict** = 本篇清册计划内 52 + 实施时发现的计划外 20(第一波 9 + 第二波 11);**ExecState 22 具名** = 本篇清册 16 + 计划外 6。执行层状态类目此后整体停用(git 历史可溯):ExecState 载体与访问口已拆除,22 具名字段各自归位(删/策略器状态/GameState 状态容器),见 §2.4 as-built 停用注。两波计划外字段均为实施批按 §6.1「计划外字段一律视为范围遗漏」收录的实装 grep 发现项(产生者/消费者与清册同族),按本篇自己的对账规则回写入账,防止下批按清册找字段归属系统性误导。

### 2.1 观察数据——留 session(表列 26 项,GameState 归一批后现态)

| 字段 | 产生者 | 消费者 | 生命周期 | 备注 |
|---|---|---|---|---|
| ~~`last_hp` / `last_hp_t` / `last_hp_real` / `last_hp_real_node` / `hp_suspect`~~ | —— | —— | —— | **已停用删除**(终态契约 §A 防御缓存删除,`cw_strategy_session.py` 注释权威版本):结算 hp 识别标志/对账识别标志/hp 下行拒信通道整组删除——「上一真值」语义由结算覆盖写端 + carried 语义承载(`../game_state/fields.md` §2.1),hp 读数消费 = 状态容器单读(`decision_hp`,观测与支付币读数面) |
| `last_node_type` / `node_type_current` / `upcoming_types` | 节点行读取(read_node_sequence) | on_round_end 遥测、策略器(旧日志标签 director)判节点 | 帧/节点 | 节点识别标志同族模式 |
| `nodeseq_probe_anchor` | 节点行读取(框架侧) | 节点行读取防重 | 节点 | 左移推断轮次用 |
| `last_streak` | 结算屏「连胜×N」 | economy C 杠杆 | 节点 | 方向语义在符号 |
| `last_level_obs` | read_level + 单调守卫 | 等级读数消误 | 局 | 识别层守卫状态 |
| `active_strategies` | 选卡 handler 采集 | read_game_state 拷入 state | 局 | 已持投资策略 |
| `last_owned_equips` | 备战入口观察装配点全量重写(主写端,P4 接入调用)+ 穿戴 pass 执行位步内覆写 | state.equips 遥测、载体中继兜底 | 帧 | ;决策输入(门①/工具评估/计划产出位)已切状态容器 `equips` 域(黑板帧停用前搬迁),勿回接本镜像 |
| `chosen_megastar` / `chosen_partner` | 选择 handler | 遥测回写 state | 局 | 复盘维度 |
| `star_pending_regression` | 识别防抖(合成动画窗确认) | star 真值采信 | 节点内 | 框架识别守卫 |
| `briefing_affixes` / `briefing_bosses` / `selected_difficulty` / `enemy_difficulty` / `active_env` | 简报/入口屏/情报屏采集 | mechanics_fit/boss_fit | 局 | boss 名单中的 None 占位元素保留原槽位、不做过滤（槽位序号即语义） |
| ~~`prep_obs_frame`~~ | —— | —— | —— | **已停用删除**(黑板帧停用):备战黑板帧宿主与 `gs.prep_obs` 槽一并删除,策略器唯读状态容器契约归位——备战决策读 = 状态容器单例 `game_state_of(session)` 全量直读;`PrepObservation` 瘦身为备战环 op 局部控制信号载体(shop_open/substate/event_overlay),不进 session |
| ~~`pending_round_outcomes`~~ | —— | —— | —— | **已停用删除**:消费侧 drain 停用后观察半累积槽整删——结算真值归宿 = gs 结算覆盖写端(`apply_settlement_cover`)+ `performance.history` |

> 帧代次（帧的版本标记）标注双槽现役宿主 = GameState 非 Field 双槽 `gs.frame_class_prep`/`gs.frame_class_shop`(帧语义注记,非游戏事实;写点 = 备战/商店域观察装配点与决策环直写,读者 = 决策入口终局意向重估节拍,读后即清):`gs.frame_class_shop` 标注对象 = **最近一次商店域状态容器观察写点**(入口观察段喂入/续段重观察)——商店黑板槽 `shop_state_frame` 已随两态制收尾停用删除,状态容器 = 商店决策读单源;`gs.frame_class_prep` 标注对象 = 最近一次备战域状态容器观察写点(黑板帧宿主已停用,标注语义保留)。

> **GameState 归一批后的现态修正**(本篇清册 = 迁移时点账,上两行已移出表外):`last_state` 备战快照已随 last_state 链停用批删除,现役宿主 = GameState 状态容器(观察喂入 = `read_game_state` 漏斗);`effect_inventory` 现已归一 `GameState.effects`(载体归一防第二账本),session 兼容读口 property 已撤,消费点直读 `game_state_of(session).effects`。本表现态列 26 项(帧代次标注双槽不在其列,现役宿主 = `gs.frame_class_prep`/`gs.frame_class_shop`,注如上)——全字段集以 `cw_strategy_session.py` 类体为准(统计行与 §4 结构图为清册时点数)。

### 2.2 框架设施——留 session(2 项)

| 字段 | 说明 |
|---|---|
| `rng` | 种子契约基准(公平/replay);default 固定种子 0,消费方显式注入。非三类任一,属框架基础设施 |
| `performance` | 观测反馈跟踪器(双侧 OCR),框架采集域 |

### 2.3 策略器状态——迁出至策略器状态对象(28 项,含动态属性 `cw4_counters`;as-built 实际落点 72 具名 = 52 清册 + 计划外两波 20,清单见 「落位裁量」节)

| 字段 | 产生者 | 消费者 | 生命周期 | 迁出落点(目标态归属) |
|---|---|---|---|---|
| `target_comp` / `target_drought` / ~~`pending_deploys`~~ / `transition_framework` | update_target 策略推导 | 部署/买入/卖出决策 | 局/轮 | MandateState.意向面 ~~`pending_deploys` 〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕~~ |
| `commit_signals` / `stash_comp` / `commit_flip_pending` / `focus_factions` | 定型信号推导 | update_target 线选择 | 局 | MandateState.定型面 |
| `last_candidate_scores` / `last_candidate_scores_round` | 选线轮评分推导 | 遥测、shop 侧陈旧判定 | 轮 | MandateState.推导缓存 |
| `v3_intention` | cw_intention 状态机(策略判据层) | kernel/mandate/sim 广域只读 | 局 | MandateState(核心意向状态机) |
| `v3_evolution` / `v3_core_names` / ~~`v3_mode`~~ / `v3_alarm` / `v3_pending_rollback` / `v3_prev_hp` / `v3_last_intention_event` / `v3_intention_key` | 意向/演进/纪律推导 | mandate_v1 决策、on_match_start 清零 | 局/轮 | MandateState ~~`v3_mode` 〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕~~ |
| ~~`v3_blood_budget_rejects` / `v3_blood_budget_refresh_rejects`~~ | 血预算拒付披露(策略) | 遥测 | 局 | MandateState **〔已随 hp 判据族删除删除——MandateState 侧计数器与遥测透传字段同批删除〕** |
| ~~`v3_handoff` / `v3_handoff_plane`~~ | 位面 2 承接快照(策略计算) | decide_prep | 位面 | MandateState **〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕** |
| ~~`v3_posture_unfulfilled`~~ | 仲裁帧级重算(策略) | 对账门遥测 | 帧 | MandateState **〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕** |
| `cw4_counters`(动态属性,非 dataclass 字段) | 策略行为观测分键(mandate_v1/encounter/shop/entry 多点写) | decisions 行、cw4_counters.jsonl 局终快照、sim 轮差分账本、A/B 披露 | 局 | MandateState;**遥测消费线必须随迁保持可读**(§5.4) |
| ~~`v2_state` / `locked_line`~~ / `bridge_id` | 决策层相位元组/终局阵容锁定/桥线(活读端 = 商店执行回执 decisions 行,**原读端宿主 `cw_screen_buy_cards.py` 已随商店访问重构停用**;**原活写端** = 旧引擎 engine_p1.py:672/701,已随引擎停用消解,见 §5.6 as-built 注) | decisions 行遥测 | 局 | MandateState.相位面(sim 初始相位改经状态构造,§5.6)~~`v2_state`/`locked_line` 〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕~~ |
| `memory`(dict) | 策略 scratch | 策略临时变量 | 局 | **随切换直接消解**(§6.3,用户裁定) |

### 2.4 执行层状态——迁出至执行侧载体(16 项;as-built 实际落点 22 具名 = 16 清册 + 计划外第二波 6:`last_prep_action_sig`/`_supply_detour_done`/`cw_prep_pending_accts`/`cw_takeover_collect_done`/`cw_takeover_tries`(此两名已停用删除——现行接管补采无 gs 字段,真值经位面详情屏写门落状态容器)/`cw4_swap_arm_on`,见 「落位裁量」节)

> **as-built 停用注(执行层落点列消解)**:执行侧载体(`ExecState`,本表「迁出落点」列的目标态宿主)已随执行层状态类目整体停用(git 历史可溯)——GameState 成为一统的局内事实状态容器后,执行层不再设独立状态载体。本表各字段终局:失败记忆(`deploy_fail_counts`/`equip_drag_fail_counts`)、死面(`_supply_detour_done`)、期望账(`pending_buy_expect`/`xp_expect_ledger`/`cw_prep_pending_accts`/`expected_state` 族)、僵尸轮账(`v2_round_key`/`v2_round_sold`)删除;防重入半边按语义归位(megastar 旗标 → 策略器状态 `StrategyState.megastar_clicked`,刷新计数 → GameState `node_screen_refresh` 域状态容器计数);席位真值 → 主域字段(bench/deployed);暂存/接管恢复/簿记/节点台账 → GameState 状态容器(选择域/match_facts 域/plane_node_sequences)。现行字段规格单一源 = `../game_state/fields.md` §3.4 与 `../game_state/README.md` §3.3。

| 字段 | 产生者 | 消费者 | 生命周期 | 迁出落点(目标态归属) |
|---|---|---|---|---|
| `deploy_fail_counts` | 部署拖拽执行失败 | DeployMove 跳过重试 | 局 | 执行侧(PrepActionExecutor/DeployMove 动作 op 载体) |
| `megastar_candidate_clicked` | 巨星 handler 点击执行 | handler 防重入 | handler 访问内 | **`ctx.cw_match` 级局状态容器(定案,不留实施批裁量)**——字段定义理由(session 文件:123-124)恰是「防 new CwScreenMegastar instance 重置 instance flag → 重选卡死」,落 op 实例 = 每次新建实例清零 = 原始事故按定义复发(对抗审查 B1 改判;初版落点作废) |
| `star_regression_count` | star 回退停机钩子计数 | 停机钩子判定 | 节点×2 | **已删除**(停机钩子随 2026-09-16 框架化批停用,星回退处置归观察对账;状态容器登记 `exec_books.star_regression` 同批删除) |
| (席位随动字段已停用;席位真值 = 主域 bench/deployed,对账唯一发生点 = 观察边界) | — | — | — | — |
| `v2_round_key` / `v2_round_sold` | 同轮买卖互斥事实账本——判死删除:轮键全仓零写端使登记恒早退 no-op(唯一调用桩 = cw_sell_bench_action 卖出落地段),`v2_round_sold` 恒空集,买侧互斥消费面不存在,机制从未在环 | 无 | 轮(轮键自校验) | **已删除**(死面僵尸,随执行层状态类目停用;现行同轮已卖互斥单一事实源 = mandate_v1 自有载体 `cw4_round_sold_names`) |
| `pending_buy_expect` / `xp_expect_ledger` | 期望账构建(执行对账) | heavy 定型帧对账 | 单元/局 | 执行侧对账载体 |
| `expected_state` | 原聚合口 `apply_op_effect`(动作 op 重组批④后瘦身改名 `apply_confirm_effect`,只留 dict 确认族)到账登记 | reconcile_expected 覆盖点(期望账机制已随本表停用) | visit 内 | 执行侧期望对账状态容器 |

### 2.5 停用字段——删除(5 项,全部带前置动作)

> 修订补正:初版 5 个字段标「已核无人读写」与现状不符,已逐个改判迁出(§2.3/§2.4);停用判据改为一律**列前置动作**,不使用「已核无人读写」类置信标签。

| 字段 | 停用依据 | 前置动作(切换批内完成) |
|---|---|---|
| `dual_track_phase` | 读点归零(文件注释+);**但回放恢复路径有活写端** `sim/cw_replay.py:152`(回放恢复时写回) | 删 `cw_replay.py:152` 写行(该行恢复的是已无消费的老栈字段,恢复语义消失 = 停用语义的一部分,显式声明非静默) |
| `v2_ever_full_interest` | 仅冻结 default 栈读写,唯一写点 = `flow.py:152` 局首复位 | 写点随 `on_match_start` 重写(§5.2)自然消失,核归零后删 |
| `v2_prev_hp` | v1 遗留,后无读无写 | 无前置,直接删 |
| `v2_round_bought` | 同轮已买集:唯一写端 = `flow.py:139` 局首清零(cw_round_ledger 只登记卖侧,买侧集无登记写端);互斥消费语义现状由轮键重置段空转 | 写点随 `on_match_start` 重写消失;核无仲裁读端后删——若切换批核对发现仲裁守卫活读此集,则改判随 cw_round_ledger 宿主迁出(与 `v2_round_sold` 同状态容器),禁带疑删除 |
| `v2_seed_bought` | 唯一写端 = `flow.py:151` 局首清零 → 该 dict 现状**恒空**,种子年龄豁免(cw_discipline_rules.py:161)已结构性失效 | kernel 死码收尾:删 `cw_discipline_rules.py:161` 读段(恒空输入的豁免分支)+ `flow.py:151` 写行——豁免失效是现状既成事实,切换批把它显式收尾而非延续假账 |

### 2.6 动态属性——迁出至策略器状态对象(24 项)

> 补入说明:这些属性无 dataclass 字段定义,靠动态 setattr 挂 session(初版清册只收了 `cw4_counters` 一个,缺 1/4)。枚举源 = `flow.py:126-180` on_match_start 清零段(20 个)+ 消费侧惰性建 4 个。**全部归类策略器状态**(产生者 = 策略推导/决策层簿记,消费者 = 决策与遥测,生命周期 = 局/轮),全部迁 MandateState:

| 组 | 属性(逐个) | 产生者/消费面备注 |
|---|---|---|
| 相位与镜像(每轮重算) | `v3_phase` / `v3_form_ok` / `v3_b_t` / ~~`v3_dp_posture`~~ / `v3_mirror_key` | write_shop_mirrors 每轮写;`v3_form_ok` 原有 sim 直写点(engine_p1.py:1098,已随引擎停用消解,§5.6)~~`v3_dp_posture` 〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕~~ |
| ~~`v3_formed_stop`~~ | 成型停手 | **行为面消费** = cw_screen_prep 决策豁免联动 + decisions 行入行(非纯遥测;宿主画面 op 已随商店访问重构停用)——**〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕** |
| ~~`v2_remedy_used` / `v2_steady_lv_used` / `v3_steady_lv_abandoned` / `v3_remedy_abandoned`~~ | 补偿/稳态簿记 |  跨局清零计数——**〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕** |
| ~~`v2_round_refreshes` / `v2_round_p1_early` / `v2_round_p2_core` / `v2_round_press_exempt` / `v2_round_press_copy`~~ | 轮笔数披露 | 遥测判读面(journal/局档案)——**〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除;`v2_round_refreshes` 模块 docstring 残留引用同批清理〕** |
| 富余金强制释放与跨位面承接 | ~~`v3_release` / `v3_release_round`~~ / `v3_release_spent` / ~~`v3_handoff_gap`~~ / `v3_handoff_hp_proj` | 富余金强制释放指令及其跨位面承接记录——「把利息线以上的富余金币强制花掉」姿态的状态与执行进度(语义见 proofs/p17、p18);`v3_release_spent`/`v3_reserve_cap` 是遥测透传源(telemetry/schema.py:424/433、recorder.py:241/250);`v3_handoff_hp_proj` **〔已随 hp 判据族删除删除——孤儿字段(无写端无读端)同批删除〕**~~`v3_release`/`v3_release_round`/`v3_handoff_gap` 〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕~~ |
| 消费侧惰性建 | `v3_registry`(A/B 注册表注入通道,cw_economy 消费)/ ~~`v3_dir_refresh_used`~~(刷新消耗计数)/ ~~`v3_alloc_frame`~~(DP 姿态轮帧缓存;原引擎消费点已随停用消解)/ `v3_reserve_cap`(储备线披露;原引擎消费点已随停用消解) | 惰性建模式迁 MandateState 具名字段(缺省值即现惰性初值)~~`v3_dir_refresh_used`/`v3_alloc_frame` 〔已删除——死槽字段(读写消费面为零)随死代码全量清偿移除〕~~ |

**遥测承诺精确化(消解「session 只剩 30 项」与「遥测 schema 零改」的表面矛盾)**:§6.1 迁移清单**扩大到全部 104 项**(含本节 24 个动态属性);遥测承诺收窄为——**decisions/schema/jsonl 的序列化 schema 与格式零改,但全部数据源读点改为经访问函数抽自 MandateState**。session 字段数与遥测 schema 本就无蕴含关系(动态属性从来不进 asdict,遥测可见性从来全靠显式读点),初版「schema 零改」表述未点明该依赖链,此处显式化(对抗审查 C1 采纳)。

## 3. 策略器一局存活契约(三个显式问题)

### 3.1 裁决 1:载体形态 = 黑盒状态对象挂 session,所有权归策略器

**裁决**:session 增加单一黑盒字段 `strategy_state: object = None`;策略器状态类型由**实现包自定义**(如 `mandate_v1/mandate_state.py` 的 `MandateState` dataclass,并入 §2.3 全部 28 项 + §2.6 全部 24 项,合计 52 项;as-built 72 具名 + scratch,见 §2 统计行注);框架(策略管理器 `create_session`)在每局创建时调用实现包的工厂钩子建实例、写入 `session.strategy_state`,此后**框架只搬运引用,不读不写其内部**——所有权归策略器,生命周期管理(每局新建、局终随 session 销毁)归框架。

- **被否选项 A:策略管理器每局复用同一策略实例**(策略器变有状态单例)——否决理由:①策略实例现在是跨局长命对象,「每局新建 session」的清零保证失效,漏清零字段成为跨局污染源(现状 `on_match_start` 逐字段清零已多次出漏,`flow.py:120-180` 的清零清单本身就是该形态的补丁史);②sim 与 live 共享同一实例定义时,实例级可变状态让并发跑批/回放交叉核对不可复现;③换核热替换面(A/B 切 strategy_id)要求实例可随时丢弃——实例带状态则丢弃即丢局中状态,语义断裂。
- **被否选项 B:框架代管 dict(= memory 现状延伸)**——否决理由:①schema 不可见(asdict/telemetry 看不见),判读面盲区;②无类型与守卫,键名冲突靠纪律约束(memory 注释五条款全是纪律不是机制);③所有权名义归策略、宿主仍在框架载体——与目标态的定义矛盾,只是换个字段名继续混装。
- **被否选项 C:状态作为独立参数贯穿全部契约接口签名**——否决理由:契约接口 + bridge/entry/mandate/shop 全链签名改一遍,改动面最大,且签名携带的输入本就经 session 黑板(prep_obs_frame 同款),单独走参数属双通道。

**契约条款**:
1. `MandateState` 类型定义、字段、更新语义全部在实现包;kernel 判据层(cw_intention/cw_evolution 等)对策略状态的消费改经**访问函数**(取 `session.strategy_state` 后类型收窄),kernel 不再持有 `session.v3_*` 字段注解。
2. 框架侧唯一义务:`create_session` 时置初值、局终随 session 销毁、不复用上局引用(as-built 语义更新:生命周期并入后新建与 live 初值统一在 create_session 唯一的每局新建入口,原 `on_match_start` 逐字段清零/强制新建钩子已删——状态对象每局新建即天然清零,「不复用上局引用」by construction 成立)。
3. 意向状态机的跨轮驱动重入守卫(现状 `v3_intention_key` 段级重入)语义原样搬入 MandateState,**不变**。
4. **遥测可见性依赖链显式化**(对抗审查 C1 采纳):黑盒字段不进 asdict/repr/遍历通道(全仓核过无 asdict(session)/deepcopy(session) 消费点,该面成立),动态属性现状的「asdict 完整」亦名存实亡——**迁移后遥测可比性完全依赖 §5.4 的访问函数抽读链,该链是唯一观测通道,任何新遥测字段必须从访问函数出发,禁直读 session 猜字段**。

### 3.2 裁决 2:恢复局语义 = 策略器状态保守冷启动

**裁决**:恢复局(server 重启后接管残局)下,session 观察数据由入口观察全量重建(现状 `discard_stale_match_container` + 新局兜底已有 by-construction 语义,flow/README §2.3),策略器状态**不可重建、不尝试重建**——以空 MandateState 冷启动,凭当帧观察数据重新驱动意向状态机(重新锁定终局阵容/重评演进)。丢失状态的语义逐类显式声明:

| 丢失的状态类 | 冷启动语义 | 风险评级 |
|---|---|---|
| 意向状态机(`v3_intention`) | 从未锁定态重驱动,凭现读 board/bench/持有重锁——可能锁到与重启前不同的线 | **中**:换线成本存在但决策仍自洽(意向状态机的输入是观察数据,不是历史意向);恢复局已有遥测标记可判读 |
| 纯限制器计数(defer 门/handoff 采样戳/稳态放弃计数) | 归零 = 「未发生过」语义 | 低:保守限制器,归零只放宽限制一轮,下个入口重估 |
| 同轮已卖集(原 §2.4 执行侧轮账本 `v2_round_sold`) | 实施盘点改判:该守卫实为恒空集僵尸(轮键零写端 → 登记恒 no-op),从未在环,已随执行层状态类目停用删除;现行同轮买卖互斥由 mandate_v1 自有载体 `cw4_round_sold_names` 承载,恢复局冷启动同样丢失——「同轮已卖禁买回」守卫失效窗口与先卖后买回的缩幅循环风险语义不变,宿主换为策略器状态 | **中**(宿主换为 mandate_v1 载体,失效方向与自愈特性不变) |
| 回退集/已买集(`memory` 类) | 空 = 豁免暂时失效 | 低:与现状重启丢 session 同语义 |
| `cw4_counters` 遥测分键 | 局终快照只含恢复后增量 | 低:遥测断点,恢复局标记在场可判读;非行为面 |

**被否选项:策略器状态序列化进对局存档、恢复时反序列化**——否决理由:①序列化面 = 策略内部结构,框架存档装配(match_archive)将被迫理解 MandateState schema,黑盒契约破坏;②策略改版后旧存档反序列化的版本兼容是无底洞;③恢复局是低频路径,冷启动损失有限且上表逐类可观测——为一类低频路径引入持久化 schema 契约不成立。**显式战术权衡**:意向重锁可能换线,若实机判读显示恢复局换线致损显著,升级路径 = 只把「已锁定线 id」一个标量随 runs summary 落盘供恢复参考(框架可见、策略可读),不做全量序列化——此为后备,不进本设计承诺。

### 3.3 裁决 3:热替换面 = 局边界丢弃冷启

**裁决**:换策略实现(切 strategy_id)只允许发生在**局边界**(现状 config 切换即局粒度,flow/README §2.4 换核机制不变);替换时旧状态对象整体丢弃、新实现的状态对象由其工厂每局全新创建——因为状态类型是各实现包私有,跨实现的状态迁移**不定义**(不做映射搬移)。局中不允许热替换(无此需求,现状亦无通道)。

- **被否选项:新旧实现状态兼容层/迁移函数**——否决理由:状态是策略私有推导,A 实现的状态对 B 实现无语义;兼容层会把两个实现的内部结构耦合进一个迁移模块,正是本次要消灭的耦合形态。

### 3.4 与 sim 侧策略实例生命周期的对齐

**现状(as-built)**:本节设计时点的对齐对象——旧自驱动引擎的三处裸构造(`sim/engine_p1.py`/`sim/engine_p2.py`)、策略字段直写(`v2_state` 初始相位/`v3_form_ok` 镜像写)与「`create_session` 的 sim 侧消费仅回放工具」前提——已随旧引擎整体停用失去对象(考古走 git)。**对齐裁决由驱动反转 by-construction 承接**(权威版本 = [../sim/sim-design.md](../sim/sim-design.md) §1):sim 与实机同一条流程链(外层循环 + 画面 op + 动作 op + 策略器,装后端即 sim 跑一局),三条裁决的现役形态:

1. **构造**:`create_session` 唯一的每局新建入口 live/sim 同链,无 sim 专有构建口;策略器状态生命周期同源 by construction。
2. **写点**:状态迁 MandateState 后无引擎直写面——初始相位经状态构造,镜像写经 live/sim 共享镜像函数,禁裸 setattr。
3. **读点**:全部消费经访问函数(与 live 同一口),读取口径逐字节一致。

回放工具(`sim/cw_replay.py`)保留直构 session + 状态同源接入调用的工具面(非引擎路径)。

## 4. 目标态结构(双态)

```
【现状(as-is)】                          【目标态(to-be)】
StrategySession(104 项混装:              StrategySession(30 项:观察 28 + 设施 2
  dataclass 79 + 动态属性 25)              + strategy_state 黑盒引用)
  ├─ 观察数据                              │   └─ MandateState(实现包私有,52 项:
  ├─ 策略器状态(dataclass 28+动态 24)     │        dataclass 28 + 动态 24)
  ├─ 执行层状态(16 项)                    │
  └─ 停用残字段(5 项)                    执行侧载体(16 项:局状态容器/op 实例/流程状态容器)
                                          停用残字段:物理删除(5 项,带前置)
```

> as-built 实际数(计划外两波并入后):MandateState 72 具名 + scratch;ExecState 22 具名——逐波清单与对账见 §2 统计行 as-built 注。上图「执行侧载体」目标态已消解:执行层状态类目停用(git 历史可溯)后,现行结构 = StrategySession(观察数据)+ StrategyState(策略器状态)+ GameState 状态容器(局内事实独占承载,含 Field 域与非 Field 簿记),见 flow/README §2.5 与 `../game_state/README.md`。session 侧现态另经 **GameState 归一批**修正(§2.1 注):`last_state`/`effect_inventory` 不再落 session(现役宿主 = GameState 状态容器 / `GameState.effects`),`pending_round_outcomes` 后批新增——session 现态字段集以 `cw_strategy_session.py` 类体为准。

## 5. 影响面逐项声明

### 5.1 策略管理器、注册壳与 create_session 直调点

- `cw_strategy_manager.py`:`create_session` 增「调用实现包状态工厂」一步(ABC 工厂接口 `create_state(config) -> object`,非 abstract)。
- **第三方插件兼容条款**(对抗审查 B4 采纳):CwStrategy 是 plugins/currency_war_strategies 的参赛入口契约,新增 **abstract** 钩子会让所有存量第三方策略实例化后调 create_session 即 TypeError。裁决:`create_state` 定义为 **ABC 非 abstract 钩子,基类缺省实现返回 None**——存量第三方策略零破坏(None 态 = 策略器可沿用惰性建模式,与现状 cw_intention.py:1695-1702 惰性建同构);mandate_v1 覆写返回 MandateState。不做插件契约版本化(非 abstract 缺省已消除破坏面,版本化属过度设计)。
  **B4 承诺收缩申报(as-built,「落位裁量」节同文)**:「零破坏」收缩为「缺省 None **不会让策略构造与 create_session 报错**」;**不承诺**框架行为面读点(ops 主链决策输入等)容忍 `strategy_state=None`——第三方策略未覆写 create_state 且无工厂注册时状态恒 None,进入行为面读点 = AttributeError 显式报错(mis-assembly 信号,优于静默产 None 假数据)。判据/披露面(kernel 判据、遥测披露键)维持防御 getattr 形态(异型状态对象字段缺席退缺省)。两形态划分与 None 契约单一源 = `strategy_state_of` docstring。附带工厂契约:`create_state(config)` 的 config **可忽略、可为 None**(工厂实现禁读 config 取值;原「sim 注入桩面」消费例已随旧引擎停用消解)。
- **create_session 直调点两处纳入改造面**(对抗审查 B2-6 补):`sim/cw_replay.py:195` 与 `operations/cw_screen/cw_screen_buy_cards.py:497` 绕过 StrategyManager 直调 `strat.create_session(config)`——两处的状态工厂语义随 §5.1 钩子自动生效(直调的就是 ABC 方法),核对项 = 直调后 session.strategy_state 非 None。
- 注册壳 `mandate_v1_strategy.py`:零判据纪律不变;仅透传工厂。

### 5.2 中间 ABC(`strategies/impl/flow.py`)

- 生命周期新建(`on_match_start` 清零段 `flow.py:120-180`,对抗审查 C3 引用校准)对 MandateState 字段的逐项清零**整体消失**——状态对象每局新建即天然清零(as-built:该钩子随生命周期并入物理删除,新建与 live 初值归 create_session 唯一的每局新建入口)。
- 方向刷新/`decide_*` 内对 `session.v3_*`/`session.commit_*` 的读写改经 `session.strategy_state`(访问函数收窄类型);ABC 不定义 MandateState 内部结构(它是实现私有)。

### 5.3 bridge 透传与 kernel 判据层

- `mandate_v1/bridge.py` 及 entry/mandate/shop/assembly 的 `session.v3_intention` getattr 族:改访问函数后调用点机械替换,签名不变。
- kernel(cw_intention/cw_evolution/cw_economy/cw_deploy_logic/cw_discipline_rules/battle_calib)对 `session.v3_*` 的消费:改访问函数;**kernel 对 session 的字段注解依赖随之消失**——session 文件头「驻 kernel 理由」弱化为「观察数据载体被 kernel 判据消费」,不再需要防 kernel→decision 断环边。

### 5.4 序列化与遥测(decisions 行 / cw4_counters.jsonl / shop_snapshots / match_archive)

- decisions 行的 `v3_intention`/`sess_commit_scores` 字段(cw_screen_buy_cards.py:623-666、cw_serialize.serialize_intention):**schema 零改**,数据源从 session 字段改为经访问函数抽自 MandateState——遥测跨版本可比性保住。
- `cw4_counters` 局终快照链(cw_loop:384/879/1356 → match_archive.record_cw4_counters_* → cw4_counters.jsonl → ab_core_swap 披露抽取):读点全改经访问函数;**sim 轮差分账本(engine_p1.py:1038-2358)同步换读点**。这是切换批最容易漏的断流点(动态属性 grep 不易枚举全),实施批须以「session 上除观察/设施外的 getattr 兜底全部清零」为完成判据。(as-built:上述 jsonl 流与 ab_core_swap 披露面已随流载体停用批收敛为局终聚合 `MatchFinal.cw4_counters`,原引擎轮差分账本随旧引擎停用消解。)
- **shop_snapshots 流**(对抗审查 B2-1 补):`telemetry/recorder.py:820` 读 `session.v3_intention`(best-effort suppress,漏改 = 静默缺失)——换访问函数,并**纳入 6.2-2 对照面**(shop_snapshots 的 rho_obs 与 decisions 同 seed 对照)。
- **动态属性透传源**(与动态属性枚举联动):`v3_reserve_cap`/`v3_release_spent`(telemetry/schema.py:424/433、recorder.py:241/250 `_w611_int` 读 session 动态属性)——换读自 MandateState,schema 字段零改。
- match_archive 的 decision_detail(v3_intention 帧,match_archive.py:416):同上换源。

### 5.5 执行层消费点

- `deploy_fail_counts`/`equip_drag_fail_counts`:迁到执行器/动作 op 载体(PrepActionExecutor、DeployMove 动作 op、prep_actions 发出器),生命周期语义逐字段保持(局级/跨环)——载体落点实施批裁,候选 = `PrepActionExecutor`/动作 op 实例字段;**禁**为它们新开 session 字段。
- `pending_buy_expect`/`xp_expect_ledger`/`expected_state`:执行侧对账载体,对账语义 = 观察边界(screens/op-layer.md §2.3(ii));席位随动字段已停用。**kernel 读写签名重构**(对抗审查 B2-5 补):`kernel/cw_reconcile.py:78`、`kernel/cw_expected_state.py:333` 对这组字段有读写签名——迁出后 kernel→执行侧载体的访问路径**必须定义**(候选 = 执行侧载体访问口注入 kernel,或对账入口收拢签名),禁让 kernel 直接 getattr session 猜新宿主——那是与 §1-2 同型的耦合换壳复活。
- `v2_round_key`/`v2_round_bought`/`v2_round_sold`(§2.4 新增):原迁移指令(随 `cw_round_ledger` 宿主迁移,`register_round_sold` 轮键自校验语义不变,live 调用方与仲裁消费点同步换宿主)已作废——实施盘点证明轮键守卫恒早退使 `register_round_sold` 恒为 no-op(调用方实为 cw_sell_bench_action 卖出落地段,非 cw_shop_action_ops),`v2_round_key`/`v2_round_sold` 判死面随执行层状态类目停用删除,`v2_round_bought` 按 §2.5 前置动作删除;现行同轮已卖互斥单一事实源 = mandate_v1 自有载体 `cw4_round_sold_names`。
- 执行层读策略状态的既有点换访问函数(对抗审查 B2-2/3 补):`cw_op_deploy.py:1014`(读 v3_intention 取 locked_fac)、`cw_shop_action_ops.py:362`(读 cw4_counters)、`:395`(读 v3_intention)——执行层读策略状态的合法通道 = 访问函数,逐点改。
- `star_regression_count` 随停机钩子停用删除,不迁移;`megastar_candidate_clicked` 按 §2.4 定案落 `ctx.cw_match` 级局状态容器。(defer_count/bail_reason_counts 已随 DeferSpheres/BailToOuter 动作类型停用整体删除,不迁移。)

### 5.6 sim 侧(as-built:旧引擎停用后零专有改造面)

见 §3.4:设计时点的五类 sim 改造点已随自驱动引擎整体停用失去对象——驱动反转后 sim 与实机同一条流程链,原「改状态通道」的改造面由架构收敛消解:

| 原改造点 | 现役形态 |
|---|---|
| 裸构造 ×3(旧 engine_p1/engine_p2 识别标志) | 消亡——`create_session` 唯一的每局新建入口 live/sim 同链(§3.4) |
| 策略字段直写 ×3(`v2_state`/`v3_form_ok`) | 消亡——状态迁 MandateState 后无引擎直写面;初始相位经状态构造,镜像写经共享镜像函数 |
| 广域只读点(`v3_intention`/`cw4_counters`/`v3_dir_refresh_used`/`v3_alloc_frame`/`v3_reserve_cap`) | 消亡——读写同口 = 访问函数,live/sim 同一读链 |
| cw4_counters 轮差分 | 消亡——原引擎轮差分账本随停用拆除;计数同源累计,消费 = 局终聚合 `MatchFinal.cw4_counters`(§5.4 as-built 注) |
| create_session 直调 | 仅回放工具(`sim/cw_replay.py`)保留工具面直构 |

sim 决策逻辑与判据本体零改动——as-built 后 sim 亦无专有状态通道,决策语义与状态通道均与实机同构。

## 6. 迁移方案:一次性原子切换(用户 2026-09-06 裁定)

> 原任务书按「契约先行→分期迁移→双轨并存→旧字段停用」框架命题;用户裁定**「这么小的事一次迁完」**,以下按裁定改写。被取代的分期/双轨框架不再展开,其有效残余(每期可独立验证的思想)吸收进切换批的验证清单。

### 6.1 切换批范围(单 commit)

契约(`strategy_state` 黑盒字段 + `create_state` 非 abstract 钩子)+ **§2.3 全部 28 项 + §2.6 全部 24 项迁 MandateState**(合计 52 项策略器状态)+ §2.4 全部 16 项迁执行侧载体 + §2.5 全部 5 项停用(含各前置动作:kernel 死码清理/cw_replay 写点删/v2_round_bought 带疑禁删条款)+ 改判字段(v2_state/locked_line/bridge_id/v2_round_key/v2_round_sold)的活读写点换源(实施盘点修正:v2_round_key/v2_round_sold 无活读写点——轮键零写端使登记恒 no-op,两字段已判死面删除,换源指令作废;该类目全部字段后随执行层状态类目停用再行归位,见 §2.4 as-built 停用注)+ §5 全部消费点换读(含 5.4 遥测透传源/5.5 补点/5.6 sim 五类改造点)+ `memory` 消解(§6.3)。**不做分期、不设双轨期**:切换 commit 前 session 旧形态、commit 后目标态,无中间并存态——双写/双读纪律问题在单 commit 边界上构造性不存在。切换批范围以 §2 清册全集(104 项)为账本,**计划外字段一律视为范围遗漏**(禁「清册外即不管」)。

### 6.2 验证清单(切换批完成判据,取代逐期实机验证)

1. 快速集测试全量通过(`uv run pytest sr-od-test/ -m "not slow"`)+ 直接受影响面慢桶一次全量。
2. 决策帧截图保留证据对照:同 seed sim 跑切换前后各 N 局,decisions 行/`cw4_counters`/**shop_snapshots**/`v3_intention` 序列化输出逐帧对照并**截图保留证据**(逐字节一致;不一致 = 读点漏改或语义漂移,逐处归因;保留证据物归对局档案,供对抗审查与用户二次确认调阅)。
3. grep 完成判据(对抗审查 C2 采纳,范围扩到全集):对**清册全集 104 项逐一**做 session 形态访问归零 grep——含 §2.3/§2.6 迁出字段(`session.v3_*`/`session.v2_*`/`session.commit_*`/`session.cw4_counters`/`session.memory` 及 `getattr(session|sess, '<键>')` 动态属性形态)、§2.4 执行层字段(`deploy_fail_counts` 等)、§2.5 停用字段名(直接属性访问形态,防 cw_screen_buy_cards.py:658-660 类 AttributeError)——任何一项在 session 形态上有残留访问即不收尾。
4. 实机局 ≥1 局跑通 + 恢复局形态一次手工验证(重启 server 接管残局,核对 §3.2 冷启动语义与恢复局遥测标记),**并加两项行为面判读**(对抗审查 B3 采纳):①~~恢复轮血预算披露~~(该判读对象已随 hp 判据族删除删除——判读义务随对象消解);②恢复轮同轮买卖序列判读(同轮已卖互斥宿主 = mandate_v1 `cw4_round_sold_names`,恢复局冷启动同样丢失,判读义务不因原执行侧守卫 `v2_round_sold` 的停用而撤销——该守卫经实施盘点判恒空集僵尸,从未在环;守卫缺位窗口内无卖后买回缩幅循环)。

### 6.3 `memory` 的消解(不设过渡)

`memory` dict(2026-09-06 刚落地)在切换批直接消解:其既有键并入 `MandateState` 具名字段(高频/需守卫的)或 MandateState 内的 scratch dict(一次性键,纪律条款原样平移——键名模块前缀/局级生命周期/不入 decisions)。**不保留 session.memory 作为过渡通道**——保留即等于保留「框架载体代管策略私有状态」的反模式本体。

## 7. 风险与回滚

### 7.1 回滚方式

单 commit 原子切换 ⇒ 回滚 = `git revert` 该单 commit,工作树回到现状形态,无残留半态(原子切换在此点优于分期:分期回滚需逐期对账字段双态)。测试仓同步 revert 同批测试改动。

### 7.2 最大行为风险点(按序)

1. **恢复局语义变化**(§3.2):现状恢复局丢 session 与切换后丢 MandateState 行为面等价(都是保守冷启动),但意向重锁路径从「session 空 v3_intention 惰性建」变为「工厂显式新建」——语义应逐字节一致,风险在读点漏改导致恢复局行为分叉。**恢复轮已评级「中」的行为面**(同轮已卖守卫缺位)有专项判读义务(6.2-4),非仅「跑通」(同轮已卖互斥宿主现为 mandate_v1 `cw4_round_sold_names`;原执行侧 `v2_round_sold` 守卫经实施盘点判恒空集僵尸,从未在环,已随执行层状态类目停用删除;原「掉血三个分支哑火」行为面随 BloodAlarmTracker 删除消解)。
2. **遥测断流**:`cw4_counters`/`v3_intention`/`v3_reserve_cap`/`v3_release_spent` 等序列化读点散布 sim/telemetry/operations 三域(§5.4),漏一处 = 该域数据静默缺失(不会报错)。缓解 = grep 完成判据(6.2-3)+ 决策帧与 shop_snapshots 逐字节对照(6.2-2)。
3. **执行层迁出改变了防重入/失败计数的宿主生命周期**:落点若选错(如挂 op 实例而 op 每访问重建),计数提前清零,防线失效——§2.4 每字段标注了原生命周期,实施批逐字段核对落点生命周期 ≥ 原生命周期(`megastar_candidate_clicked` 已按 B1 定案局状态容器,不留裁量空间)。
4. **停用字段的静默/报错双形态**:直接属性访问的残余读点(cw_screen_buy_cards.py:658-660 类)删除即首商店帧 AttributeError;`cw_replay.py:152` 对 `dual_track_phase` 的 setattr 删字段后**不报错但静默丢恢复语义**——两类都在 §2.5 前置动作 + 6.2-3 全字段 grep 判据适用范围内,无「已核」标签兜底。
5. **sim 改造面失真**(设计期显式化):三构造点/三写点/五类只读点任一漏改 = sim 起跑即崩(构造)或状态通道口径分叉(读写),后者会被 6.2-2 同 seed 对照抓;构造类崩溃首局即暴露,风险在排查成本非隐蔽性。(as-built:切换批已落地,旧引擎停用后 sim 与实机同链路、无专有改造面,该风险面消解。)
6. **kernel 判据层换访问函数引入 import 方向问题**:访问函数落点须不造 kernel→impl 断环边(候选 = kernel 内薄读口 `strategy_state_of(session)` + TYPE_CHECKING 收窄,实施批裁);kernel 对执行层字段的读写签名重构(§5.5 cw_reconcile/cw_expected_state)同此判。
