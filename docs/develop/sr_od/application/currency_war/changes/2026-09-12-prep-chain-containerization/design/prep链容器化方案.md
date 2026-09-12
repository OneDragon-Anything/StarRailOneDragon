# 备战观察链容器化方案（prep 链容器化·详设）

> **迭代定位**:本迭代(`2026-09-12-prep-chain-containerization`)承接 unified-state
> 迭代设计件《商店黑板容器化方案》§1.4 裁定外溢的 prep 链容器化面,独立成迭代。
> **文档定位**：本设计件 = 《商店黑板容器化方案》§1.4「明确不解决」裁定的外溢承接
> （依据 = 该件 §1.4 第一条「备战黑板槽 `prep_obs_frame` 其处置随波 4 adapter 决策缝
> 改造走,本方案不辖」+ sim/实机同源性判读报告 `.debug/temp/sim_adapter_同源性判读.md`
> 证据表 #12 与未完成面清单第 4 条「prep 链本体签名容器化 = 备战观察链容器化
> (类 W5 透传域建模),建议下批立项」）。辖域 = 备战观察链的 GameState 签名切容器
> BoardState 透传域建模:范围锚 = `strategies/impl/mandate_v1/entry.py` 五处签名、
> `kernel/cw_strategy_session.py:202`、`operations/cw_screen/cw_screen_prep.py`
> game_state_view 最后 1 处活调用消点、`shop_state_frame` 槽字段处置、
> `session.last_state` 写点处置。字段级语义正本 = `game_state/fields.md`;字段映射
> 契约正本 = 调研草案 `w6-切换波次调研草案.md` §4 字段对照表(本设计不复制,逐处
> 方案只写映射结论与读口符号)。数值只写常量名。
> **判读时点申报**:本设计代码现态判读基线 = 2026-09-12 工作树(波 4 段②在飞未落库
> 态,判读报告同基线)。任务书锚 `cw_screen_prep.py:737` 在现树为同段
> `session.last_state` 写点行;game_state_view 活调用现树行号 = :714(判读报告 #4
> 同)。本文一律「符号 + 现树行号」双锚,行号漂移以符号为准;波 4 段②落库后落地批
> 批首按符号 grep 复核一次(判读报告「复核义务」同款)。
> **状态**:定稿(对抗收敛,landing.md 已立,候编排者立落地批)。

## 0. 术语

- **备战黑板槽**: `StrategySession.prep_obs_frame`(PrepObservation 型,在码锚 =
  `kernel/cw_strategy_session.py:198`)。生命周期 = 画面态(每次备战观察覆写);写者
  白名单 = `cw_screen_prep` 入口观察/投影步/finalize 买后暂存(在码注释申报)。
- **obs.state 槽**: `PrepObservation.state`(`GameState | None`,在码锚 =
  `kernel/cw_prep_actions.py` PrepObservation 字段)——备战黑板帧上的决策视图槽。
- **决策视图**: `game_state_view(bs, st)` 产物(`kernel/cw_bs_view.py:80`)——
  「容器主值(含 carried 沿用)+ 未建模/执行域帧透传」合成的 GameState 消费视图。
  全仓生产活调用现剩 1 处 = `cw_screen_prep.py:714` 备战观察口(判读报告 #4)。
- **prep 投影**: `_project_prep_obs`(cw_screen_prep.py:847)——逐动作零读屏的期望态
  纯计算推进,黑板帧载体;动作后首读对账归下一入口 heavy(ADR-0517 决策 7/8/10)。
- **透传域建模(类 W5 手法)**: r5-migration-plan §2 W5 波「透传域建模收编」的手法
  ——投影/视图层未建模、原经帧透传的域,逐域建模入容器或裁定消费面归宿,使消费
  签名可整体切容器。本文沿用该手法处置备战链透传面,不新立第二清单(域归宿以
  调研草案 §4 字段对照表与 fields.md 正本为准)。
- **读口族**: 波 1/波 3 落地的容器公共读口单一源(`cw_board_state.py:2794-2905`:
  `plane_of`/`round_num_of`/`node_kind_of`/`gold_of`/`level_of`/`deployed_slots_of`/
  `bench_slots_of`/`max_units_of`/`back_capacity_of`/`deployed_count_of` 等,旧
  GameState 缺省值镜像语义在各口 docstring 申报)。
- **decision_hp**: 波 2 交付的 kernel hp 政策读口(门前真值+消费侧施门单一源;依据 =
  设计件《hp施门下沉kernel政策层设计.md》§2.3,《商店黑板容器化方案》§2.2-2 锚)。

## 1. 问题与约束

### 1.1 现状(prep 链 GameState 残留面全表)

**载体关系**:观察漏斗 heavy 每帧产出原读帧 `st`(read_game_state 产物)→ 容器观察
写端已在同帧就位(read_game_state 内部 `_feed_board_state` + 备战席/上场席观察写端,
cw_screen_prep.py:646-710)→ `obs.state = game_state_view(_bs_obs, st)` 合成决策视图
(:714)→ 备战黑板帧带视图进决策 → `entry.emit` 取 `state = obs.state`(:414)分喂五处
签名与其下游 prep 域全簇;原帧 `st` 另写 `session.last_state`(:737,执行侧装配源,
ADR-0530)。即:**同帧三载体并存**——容器单例(记录正本,已就位)、决策视图
(第二状态面,消费中转)、last_state 帧(执行侧装配)。

**五处签名**(全部位于 entry.py,形参 `state: GameState | None`,实参 =
`obs.state` 视图):

| # | 锚(现树) | 函数 | state 域读 | state 下游漏斗 |
|---|---|---|---|---|
| ① | entry.py:151 | `_sphere_progress_sig(state, obs)` | round_num(getattr 缺省 1) | 无(纯函数) |
| ② | entry.py:335 | `_lambda_quantile_armed(state, hp, p_value)` | node_type/enemy_difficulty/plane | 无(纯函数) |
| ③ | entry.py:364 | `_upgrader_evaluate(session, state, gold, hp)` | 经②委托;`gold` 形参现体零消费(函数体 :366-392 实证) | ② |
| ④ | entry.py:830 | `_reconcile_posture_authorization(session, state, emitted, k_members, registry)` | plane/round_num/gold/level/hp/active_strategies/deployed/bench/max_units() | `crit_levelup.level_spend_blocked(state,…)`(:905)、`levelup.levelup_budget_gate(state,…)`(:988) |
| ⑤ | entry.py:1034 | `_criteria_pass(frame, session, state, k_members, …)` | gold/round_num/deployed | `crit_sell.line_switch_sell(…, state,…)`(:1068)、`crit_sell.funding_support_sell(…, state=state,…)`(:1105)、`locked_buy_cap_hold(state)`(:1101/:1118) |

**emit 体既有桥装/视图消费点**(段内一并申报,不在五处锚内):
`k_empty_window_fallback(board_state_bridge(state), …)`(:551,kernel 已切容器签名,
桥装箱)、`board_state_bridge(state)` ×2(④ 体内 :882/:927,kernel 血闸/奖励闸已切
容器签名,桥装箱)、`board_state_of(session)` ×2(④ 体内 :969/:970,成本计算读容器)、
`state = obs.state`(:414)供 run_mandate/wanted_closure_emit/fuel_sell_candidates/
record_round_sold/should_switch/evaluate_evidence_gate/p1_blood_floor/p2_blood_floor
等下游 prep 域全簇(签名仍 GameState;判读报告 #12「prep 链本体签名保留」申报面)。

**obs.state 槽写点全表**:读屏路径视图合成(:714)、无 session 兜底(:716)、端口路径
直存(:494-495)、light 缓存沿用(:833)、投影步帧替换(`_project_prep_obs` 内
dataclasses.replace)、finalize 买后暂存(:2885 `state=_post`)。**读点全表**:emit(:414)、
对账族(`_shop_pool_inputs` :262/`_merge_preview_inputs` :275/对账消费 :1116/:1202/
:1253/:1305-1311)、观察终饰 dual/gated_hp 拷回(:1554-1566 与 lifecycle_reconcile
:1784-1796)、缺陷行 plane/round(:2585-2586)、装配缝(`decision_assembly.py:110`
snapshot_from_obs 锚优先级 + `adapter.py` snapshot_to_obs 装配/decision_state 骨架)。

**session.last_state 面**:三写点 = cw_screen_prep.py:514(端口路径)/:737(读屏路径)/
cw_op_buy_cards.py:916(商店融合段)。读者 = 节点 overlay 近似(session 槽注释申报)、
`_spend_unit_open`(:2150,plane/round 记账)、`_probe_node_type`(:2665,plane_now)、
spec-invest 停机钩子(:2434,留证显示)、cw_deploy_logic/sell_gate 轮号解析
(last_state 优先半;商店域读者,《商店黑板容器化方案》§1.1 读者表)。**备战决策链
对 last_state 零直读**(决策输入 = obs.state 视图,非 last_state)。

**shop_state_frame 残面**(M2,判读报告 #14/未完成面波 4 剩余 2):读者已 0(波 4 段②
切完),残留 = 写点 2 处(cw_op_buy_cards.py:632 投影写/:922 融合写)+ 槽字段
(cw_strategy_session.py:202)+ 遥测读 1 处(cw_op_buy_cards.py:1088)+ M2 grep=0 锁
未立——判读报告裁定「移缴下批」。

### 1.2 症状与根因归层

- **症状**:①prep 决策输入走第二状态面(决策视图),容器观察写端同帧已就位但决策
  读不直连——与《商店黑板容器化方案》§1.1 波 1 过渡桥张力同族(该件 §1.2 根因
  判定「黑板模式先于统一 state 容器存在」在备战域同构成立);②game_state_view 全仓
  最后 1 处活调用挂在备战观察口,投影模块 `cw_bs_view.py` 的波 5 物理删除被此点
  绊住(调研草案 §2「投影退役前提 = 16 处取帧点全改道」,判读报告 #4 已消 15);
  ③hp 双门混装:视图 hp 按门前真值供给(W5 hp 专项),观察终饰又对视图帧二次施门
  (:1565/:1795 gated_hp)——视图帧既当记录面又当消费面,门语义分界模糊
  (fields.md §2.2「识别质量是写入闸门,不是字段」的帧形态残留)。
- **根因归层(表示层,流程层并发)**:obs.state 槽混装「记录语义(容器已建模域)」
  与「观察语义(视觉/占用域)」,视图合成层是为让旧 GameState 签名继续工作而立的
  转换层;签名切容器后转换层失去存在理由。修法 = 决策读收口容器单例(流程层)、
  视图层消亡、黑板帧退役到纯视觉/占用观察载体(表示层)。
- **归层依据**:《商店黑板容器化方案》§1.2 同构判定 + §1.4 外溢裁定(本批辖域来源);
  两态制裁决 = ADR-0651 / fields.md §2.5。

### 1.3 约束

1. **在飞批文件面**:波 4(T-97)段②在飞文件含 cw_op_buy_cards.py/mandate_v1
   criteria/*/mandate.py/adapter.py 等,本设计落地批在其落库前禁触(任务书文件面
   约束);段 1(需改 criteria/)与段 3(需改 cw_op_buy_cards/cw_strategy_session)
   均以波 4 落库为依赖(§2.8)。
2. **last_state 三写点归波 5**:喂入反转(read_game_state 产出直 observe)是波 5
   整体改造,三写点删除随批(调研草案 §3 波 5 行/《商店黑板容器化方案》§1.4);
   本批零触碰写点,先接后删(读者改道后才删,本批不新增读者,§2.5)。
3. **记录渠道封闭集**:容器写入只走 observe/carry/write_prior/write_logic/relay
   (fields.md §2.4);prep 投影直写 = `write_logic` 渠道,sig 必填(ADR-0634 渠道
   签名纪律)。
4. **观察赢**:投影直写值受后续观察覆盖,失配 = 投影模型 bug 走缺陷台账
   (fields.md §2.3,ADR-0651 错误哲学);失读沿用 = 容器写端 carry(沿用+来源帧
   标注),禁缺省值造值。
5. **载体迁移非策略改动**:行为面目标 = 零变化;行为差逐项显式申报(§2 各处
   「行为差申报」行),禁静默语义修正。
6. **sim 零覆盖前提**:prep 线 sim 全程零覆盖,sim 唯一决策入口 = decide_shop_screen
   (判读报告 #12;`sim/ab_core_swap.py:27` 在码申报同结论)——sim 锁族不在本批
   验证面,本批对 sim 三件文件面零触碰(§2.6)。
7. **黑板帧失约契约不变**:决策入口对 `prep_obs_frame is None` 抛错(黑板契约,
   bridge.py:117-121 在码)保持;容器域引导窗不新增「在屏前置」类守卫(备战域无
   单一 payload 域,无商店链 `bs.shop.value is None` 的等价物——差异申报,§2.3)。

### 1.4 明确不解决

- 商店域黑板面(波 4 已辖:读者切换/投影直写接线,本设计只承接其 §2.4 步 4 移缴的
  M2 物理删除残面,§2.5);
- `session.last_state` 三写点删除与喂入反转、cw_replay 旧格式回放重建删(波 5);
- `cw_expected_state.py` 残件删除(波 5;prep 面引用 5 文件均在波 5 删除面,本批
  不动,§2.6);
- `board_state_bridge` 桥本体退役(波 5;本批只消 prep 域调用点,§2.6);
- 旧 GameState 数据类本体与 `cw_state.py` 切割(W8/账本 T-7)。

## 2. 方案

### 2.1 目标结构

1. **备战决策输入 = 容器单例**:`bs = board_state_of(session)` 调用方显式一次置顶,
   五处签名与 prep 域全簇签名以 `bs: BoardState` 为载体(与波 1 kernel 簇、波 4
   商店链 `decide_shop_action(bs,…)` 同形态;同帧同视图纪律 =《商店黑板容器化方案》
   §2.2-1,禁函数内二次取容器)。
2. **黑板帧退役到纯视觉/占用观察载体**:`PrepObservation.state` 槽删除;帧保留域
   封闭清单 = spheres/boxes/tomes/shop_open/box_overlay_open/event_overlay/
   bench_chars/deployed_chars/free_bench_slots/deploy_vacancy/deploy_divergent/
   deploy_stale/front_occupied/back_occupied/front_size/back_size/substate/
   state_gold_trusted(最后一项保留依据:cw_loop 指纹 gold 分量消费,在码锚
   cw_loop.py:161/172「单一写点」申报;其余为画面瞬态实体与占用读数,非局内事实,
   字段准入四问不过容器门——fields.md §8.8,同《商店黑板容器化方案》§3 标注槽
   取舍同构)。
3. **视图合成层消亡**:game_state_view 生产活调用清零(唯一活调用 = 备战观察口,
   本设计消点);`cw_bs_view.py` 文件本体删除仍归波 5(先接后删:消费面清零是
   删除前提,文件删除是波 5 交付)。
4. **prep 投影切容器双轨形态**:容器域投影 = 新 kernel 写口 `apply_prep_action_logic`
   (§2.4-3);黑板帧投影保留视觉域半(state 复制腿删除)。
5. **帧代次标注槽保留**(`prep_frame_class`/`shop_frame_class`,ADR-0583 §3.4):
   标注坐标系重锚 =「最近一次备战域容器观察/喂入写点」;`view` 值语义从「派生视图
   帧」重述为「派生喂入(增量重播)」,写者白名单清单随标注契约锁重推(§4-P8)。

### 2.2 五处签名逐处方案(问题①)

统一前置:emit 内 `bs = board_state_of(session)` 一次置顶(:414 附近);五处调用点
传 bs。域读映射正本 = 调研草案 §4 字段对照表,读口符号 = §0 读口族。

**① `_sphere_progress_sig`**:(state, obs) → `(bs: BoardState, obs)`;
`round_num` 经 `round_num_of(bs)`。行为差申报:旧「state is None → 轮次按 1」分支
消亡——round_num_of 未观察帧缺省 1 镜像同值,语义等价(波 1 读口等价契约,commit
33f84ca1e 读口申报段)。

**② `_lambda_quantile_armed`**:(state, hp, p_value) → `(bs, hp, p_value)`;
`node_type` → `node_kind_of(bs) or ''`、`enemy_difficulty` → `bs.enemy_difficulty.value`
(None=未读透传,λ 键 None 域语义不变)、`plane` → `plane_of(bs)`。行为差申报:旧
「state is None → 不评估」前置分支退役——该分支生产不可达(heavy 观察恒产出视图帧,
light 兼容形态现生产无调用方,cw_screen_prep.py:537 在码申报);state 非 None 而域
缺读的引导窗路径与新读口缺省镜像逐位一致,λ 键无 CI → 不评估的既有兜底不变。
hp 形参保留(调用方供给,非本函数域读)。

**③ `_upgrader_evaluate`**:(session, state, gold, hp) → `(session, bs, hp)`;
死参 `gold` 删除(现体零消费,§1.1 表③实证;调用点 entry.py:661-663 同步收缩)。
委托②形态不变;血线硬地板判断(hp ≤ `HP_BAND_NEAR_DEATH`)零改。

**④ `_reconcile_posture_authorization`**:(session, state, emitted, k_members,
registry) → `(session, bs, emitted, k_members, registry)`。逐域:
`get_node_goal` 入参 = `plane_of(bs)`/`round_num_of(bs)`/`gold_of(bs)`/`level_of(bs)`/
hp 经 `decision_hp`(门前真值+消费侧施门单一源;禁直读 `bs.hp.value` 引入施门旁路
——波 2 政策读口契约,《商店黑板容器化方案》§2.2-2 同锚)、strategies =
`bs.active_strategies.value`;`state.max_units()` → `max_units_of(bs)`;席位迭代
(:958-961 arm1 输入/:991-992 预算闸输入)→ `deployed_slots_of(bs)`/`bench_slots_of(bs)`
(换算单一源,§0 读口族);体内 `board_state_bridge(state)` ×2(:882/:927)→ 直传
bs(消桥;视图→桥→容器往返恒等,行为差零);体内 `board_state_of(session)` ×2
(:969/:970)→ 复用形参 bs。下游漏斗判据两件随段 1 切容器:
`level_spend_blocked(bs, session, _reg)`、`levelup_budget_gate(bs, session,
gold_of(bs), cap_resolved_of_session(session), k_members, bench_slots_of(bs),
deployed_slots_of(bs), clicks, cost)`(两函数签名切 bs,内部字段读按字段对照表;
auth_id/日志串的 plane/round 取读口值,格式不变)。

**⑤ `_criteria_pass`**:(frame, session, state, k_members, …) → `(frame, session,
bs, k_members, …)`。逐域:`state.gold` → `gold_of(bs)`(契约闸 ContractCtx 金参/
筹资比较/fallback 比较)、`state.round_num` → `round_num_of(bs)`(T3 保护集/排除集
轮参)、`state.deployed` → `deployed_slots_of(bs)`(fallback 上阵输入)。下游漏斗
三件:`line_switch_sell(…, bs,…)`、`funding_support_sell(gold_of(bs), …, state=bs,…)`
(两函数签名切 bs,段 1);`locked_buy_cap_hold(bs)`——kernel 已双形态
(`cw_intention.py:2570` 注解 `BoardState | GameState | None`),调用点零改即兼容。

**emit 体伴随改道(段 1 内)**:`k_empty_window_fallback(board_state_bridge(state),…)`
(:551)→ `k_empty_window_fallback(bs,…)`(消桥;kernel 已容器签名,波 3 贯通申报
在码);五处之外的 emit 体 state 消费(run_mandate/wanted_closure_emit 等)维持
`state = obs.state` 视图——寿命 = 段 2,先接后删纪律下视图供数不断供。

### 2.3 观察口消点方案(问题②)

消点 = 删除 `obs.state = game_state_view(_bs_obs, st)`(:714)。**前置条件**:
obs.state 的全部决策消费面已切容器(段 1 五处 + 段 2 prep 域全簇),对账/装配缝
消费面已改道(段 2,§2.4-4)——先接后删,视图供数在切换完成前不拆。

- **「容器主值+失读沿用」语义去向**:视图死亡后,沿用语义完全由容器写端在源上承接
  ——read_game_state 内部 `_feed_board_state` 的真读 observe/失读 carry(cw_observation
  .py:2447-2449/:2526/:2532)/hp reconcile 沿用 + 备战席/上场席空集守卫 carry
  (cw_screen_prep.py:656-710,P2-1 空集失读守卫/P3-10 特效窗观察顺延门,在码);
  视图独有的「引导窗透传帧值」半随签名切容器消亡,由读口缺省镜像承接(波 1 等价
  契约)。依据 = 调研草案 §2(投影退役前提)与 §4 对照表「有值即真读」保真位收敛行。
- **消点动作清单**(段 2 执行)::711-714 视图合成删(含 cw_bs_view import);
  :716 无 session 兜底支删;:833 light 缓存 state 沿用删(`_cached_state` 槽随缓存
  收缩为视觉域四件而删除;其三处留证读点同步改道——drag/buy/equip 期望态对账
  缺陷行 plane/round(:961/:1015/:1441,record_defect 记账面非决策面)改读口
  `plane_of`/`round_num_of`,读口缺省镜像 1 取代现 `getattr(…,0)` 兜底 0,留证行
  数值口径变化申报);:494-495 端口路径 obs.state 装配删——`bundle.state` 随之
  失去 prep 链消费归宿,端口路径边界申报见 §2.6;`PrepObservation.state` 字段删除
  (cw_prep_actions.py);snapshot_from_obs 的 `st = obs.state` 锚优先级
  (decision_assembly.py:110)改纯容器锚(回退链 = 读口族,现为「帧值优先+容器兜底」,
  改后 = 容器单源——行为差申报:帧值与容器值常态帧逐位同源(视图即容器主值),
  引导窗差异 = 读口缺省镜像,同 §2.2 ②申报)。
- **失约契约**:黑板帧级 `prep_obs_frame is None` 抛错不变(§1.3-7);容器级引导窗
  不新增守卫。备战域与商店链差异申报:商店链有单一在屏 payload 域(离屏 None 抛错),
  备战域观察是多域并集(bench/node/gold…),无等价单锚——维持现状(域级 None 语义
  由各读口镜像与判据内部 fail-closed 承接)。

### 2.4 下游 prep 域全簇与投影/暂存面(段 2 主体)

1. **emit 体下游全簇切换**:state 形参 → bs,函数集 = `run_mandate`/
   `wanted_closure_emit`/`fuel_sell_candidates`/`record_round_sold`(mandate.py)、
   `should_switch`/`evaluate_evidence_gate`(proof.py)、`p1_blood_floor`/
   `p2_blood_floor`(statefn/predicates.py)。字段读按字段对照表+读口族
   (run_mandate 的 max_units/deployed/board、proof 的 shop 预备域空表等;predicates
   现存双形态读支 :61-63 在码,容器支保留、GameState 帧兼容支随本段删除——先例 =
   波 3 `_PlaneShim` 同波消亡申报)。`MandateFrame` 构造(:692-699):gold/level/
   deploy_cap/round_num 改读口;bench/deployed 维持视觉表(obs.bench_chars/
   deployed_chars,帧域);node_type 维持 session.node_type_current。emit 体非传参
   state 直读三点随本段清零(P6 锁兜底面):`_round_num` 计算(:415-416,喂球路径
   :495/wanted 实参 :525/tools 相位 :621)→ `round_num_of(bs)`;`wanted_closure_emit`
   的 `state.max_units()` 实参(:525)→ `max_units_of(bs)`;tools 发射位
   `_tools_phase` 的 plane 读(:621)→ `plane_of(bs)`。
2. **对账族/观察终饰/缺陷行改道**:`_shop_pool_inputs`/`_merge_preview_inputs`
   (:262/:275,读 st.shop 旧容器版 ShopCard)→ 读 `bs.shop.value.cards` 容器版
   ShopCard(双类型归一波 4 已立;换算单一源 = `shop_cards_to_legacy`,cw_board_state
   .py:861);对账消费点(:1116/:1202/:1253/:1305-1311)同向;dual 拷回
   (:1554-1566/:1784-1796)删除——`dual_track_phase` 不入容器(调研草案 §4/§6),
   消费改派生读 committed_from 的形态已在波 3 立,帧上二次拷回是残件;gated_hp
   帧上二次施门删除——视图死亡后无门后值载体,hp 消费统一经 decision_hp(§1.2
   症状③收口);缺陷行 plane/round(:2585-2586)→ 读口。
3. **prep 投影容器化**:新 kernel 写口 `apply_prep_action_logic(bs, action, *,
   produced_by: str, sig: ChannelSig) -> None`,落位 `kernel/cw_board_state.py`
   (与 `apply_shop_action_logic` 同区先例)。**域集封闭 = gold(SellBench 回金,
   公式单一源 = `cw_state.sell_refund`)+ bench(SellBench 摘槽,BenchView 重建
   write_logic;重播种先例 =《商店黑板容器化方案》§2.3 布局代次行)**;未建模域
   零写(OpenBox/OpenTome/ClickSpheres 投影只动视觉域,黑板帧投影保留其腿);
   域级 None 跳写/回执登记面形态对齐商店方案 §4-M5(登记面 = 新锁 §4-P5);
   sig 纪律 = `family='logic_action'`,actor = `CwScreenPrep`(REGISTERED_ACTORS
   在册扩表申报,cw_board_state.py:239),group_id 对齐 `act:<op类名>@<seq>` 先例。
   `_project_prep_obs` 的 state 复制腿(dataclasses.replace 的 gold 调整)删除,
   改调本口;投影帧代次 = none 语义不变(:1702/:1934 在码)。
4. **finalize 买后暂存容器喂入**(:2846-2887):`build_post_buy_incremental_state`
   的 GameState 增量构造改容器写——gold 关店真读 → `write_logic(bs.gold)`;bench
   tracked 重播 → `write_logic(bs.bench, bench_view_of_slots(tracked))`(构造单一源
   既有);fail-closed 双维回退(gold 失读/tracked 空 → 全量 read_game_state 观察
   喂入口)语义不变;hp 三件组面跟随波 4 步 4 形参收缩结论(《商店黑板容器化方案》
   §2.4,不另立语义);暂存动作 = 容器写 + `prep_obs_frame` 帧代次标 `view`
   (:2885 的 `state=_post` 帧替换随 state 槽退役消亡,标注写点保留——重锚见 §2.1-5)。
5. **adapter 缝收敛**:`snapshot_to_obs` 保留视觉域映射,state 装配(:69)随槽退役
   删;`decision_state` GameState 骨架输出退役(唯一消费 = assembly.py:251,随段 2
   改容器读)——判读报告 #2「输出仍是 GameState 骨架」申报面由此收口。

### 2.5 session.last_state 与 shop_state_frame 槽字段处置(问题④③)

**last_state(④)**:三写点(:514/:737/cw_op_buy_cards.py:916)**本批零触碰,归
波 5**(约束 §1.3-2)。边界划分:

| 面 | 本批(段 1/2/3) | 波 5 |
|---|---|---|
| 三写点 | 零触碰 | 随喂入反转删除 |
| 备战决策链依赖 | 段 1/2 后 = 0(决策读容器;grep 锁 §4-P7) | —— |
| 读者面(_spend_unit_open/_probe_node_type/spec-invest 显示/overlay 近似) | 不动(记账与显示读数,非决策输入) | 随写点删除同批改容器读或随面消亡 |
| cw_deploy_logic/sell_gate 轮号解析 last_state 优先半 | 不动(商店域读者,波 4 面) | 喂入反转同批切容器读 |

依据:写点删除的前提 = 喂入反转使 last_state 冗余(调研草案 §6 残留表「last_state
槽本体:波 5 喂入改造退役」);提前删 = 读者悬空,违先接后删。

**shop_state_frame(③):处置 = 删(本批段 3 承接 M2 移缴面)**。依据:槽的读者
波 4 段②已切容器(判读报告 #14「生产读者已 0」),写点 2 处均为波 4 双轨的旧半
(:632 投影旧轨——波 4 步 1「黑板帧投影 `_proj` 同步保留」的过渡轨;:922 融合写旧轨
——步 4 对象),过渡使命已由 `apply_shop_action_logic` 直写与观察漏斗承接;留槽 =
「三处可写」双轨残存,违两态制单源。段 3 动作:两写点删(:632/:922)、遥测读
:1088 改容器读、槽字段删(cw_strategy_session.py:202 与 :199-202 注释面)、M2
零引用锁落地(src+测试仓 `shop_state_frame` grep=0;`prep_obs_frame` 不辖——其
退役由 §2.4 obs.state 槽锁 §4-P4 辖)。标注槽 `shop_frame_class` 保留,坐标系重锚
申报 =「最近一次商店域容器观察写点」(《商店黑板容器化方案》§2.1-3 同款,落地批
同步注释面)。

### 2.6 与波 5 面的边界声明(问题⑤)

| 波 5 面 | 边界 | 依据 |
|---|---|---|
| engine_p1 / engine_p2 | **零交集**:sim 对 prep 线零覆盖,sim 唯一决策入口 = decide_shop_screen;本设计文件面不含 sim 两件 | 判读报告 #12;ab_core_swap.py:27 在码申报 |
| cw_replay | **零交集**:旧格式回放重建删是波 5 面;回放不触备战链(sim 零覆盖同上) | 判读报告 #8/#12 |
| cw_bs_view | **交集协调**:本批消最后 1 处活调用(:714,§2.3)= 波 5 物理删除文件的前提达成;**文件删除归波 5**,本批不删;波 5 前提清单(16 处取帧点全改道)由本批闭合计数闭合 | 调研草案 §2/§3 波 5 行;判读报告 #4 |
| cw_expected_state | **零交集**:残件 5 文件引用(prep_actions.py 等)在波 5 删除面,本批不动 | 调研草案 §3 波 5 行/§6 |
| last_state 三写点+喂入反转 | **归波 5**(§2.5 边界表) | 调研草案 §3 波 5 行/§6 |
| board_state_bridge 桥本体退役 | 本批消 prep 域调用点(:551/:882/:927,§2.2);桥本体与 sim 侧存量调用点归波 5(桥 docstring 退役条款) | cw_board_state.py:2908-2918 |
| synthesize 反转 | 归波 5(内部模型直写);本批 finalize 喂入(§2.4-4)是生产侧观察喂入,非引擎反转面 | 判读报告 波 5 清单 |
| cw_game_ports 端口路径(假环境) | 本批只删 prep 链的 obs.state 装配消费(:494-495);`ObservationBundle.state`(GameState 载体)随之失去 prep 消费归宿——**容器喂入归观察源实现方契约**(LiveCwObserver/FakeCwObserver 在 `observe_prep` 产物落地时经容器喂入口写,与读屏路径 read_game_state 同语义;协议本体与 cw_game_ports.py 本批零触碰,装配桶注解未切归波 4 剩余项,判读报告 #13);假环境 prep 测试的容器喂入改造并入段 2 测试面(测试仓文件面,批首 grep 补全义务同 §4 尾);生产 `observation_source()` 恒 None = 本边界零生产行为面 | cw_game_ports.py:47-56/:98;_observe_from_ports 端口分支(cw_screen_prep.py:481-528) |

### 2.7 数据流(目标态)

| 时点 | 动作 | 容器写 | 容器读 |
|---|---|---|---|
| 入口 heavy | 观察漏斗(observe_full + read_game_state/_feed_board_state + 备战席/上场席写端) | observe/carry(既有,零新增) | —— |
| 黑板帧 | 视觉/占用域装配(state 槽不存在) | —— | —— |
| 逐动作·决策 | 三遍编排读容器 + 帧视觉域 | —— | bs 全域(读口族)+ frame 视觉域 |
| 逐动作·投影 | `apply_prep_action_logic`(封闭两域)+ 帧视觉域推进 | write_logic | —— |
| 观察终饰 | dual 派生读/hp 消费侧施门(decision_hp) | —— | 容器+派生 |
| 买后重估 | 容器增量喂入 + 帧代次 `view` 标注 | write_logic(gold/bench) | —— |
| sim | 不适用(prep 零覆盖) | —— | —— |
| 端口路径(假环境) | 观察源实现方容器喂入(observe_prep 产物落地,§2.6 边界行) | 实现方契约喂入口 | bs 全域(读口族) |
| last_state | 执行侧装配源(波 5 前,原帧直写不变) | —— | —— |

对齐申报:容器写端零新增渠道(投影/喂入均 write_logic 既有渠道);新增写口一件
(`apply_prep_action_logic`);其余写点全部为既有在产面。

### 2.8 迁移路径与分批建议(问题⑦)

三段串并行,先接后删;每段 = 一个可独立派工验收的落地批(账本阶段唯一源 =
对抗收敛后的 landing.md,本文只给范围/文件面/依赖):

**段 1·决策判据签名切容器(规模 M)**。范围 = §2.2 全部(五处+漏斗判据四件
+locked_buy_cap_hold 零改兼容+emit 置顶与 :551 消桥)。文件面 = entry.py、
criteria/sell.py、criteria/levelup.py(+测试仓对应锁)。依赖 = **波 4 落库**
(criteria 两件为波 4 在飞文件)。完成判据 = prep 决策行为锁族绿 + §4-P1/P2。

**段 2·备战黑板槽退役(规模 L)**。范围 = §2.3 + §2.4 全部(观察口消点+state 槽
删除+prep 域全簇+投影写口+finalize 喂入+adapter 缝收敛)。文件面 = cw_screen_prep.py、
cw_prep_actions.py、mandate.py、proof.py、statefn/predicates.py、adapter.py、
assembly.py、decision_assembly.py、kernel/cw_board_state.py(+测试仓对应锁)。
依赖 = 段 1 + **波 4 落库**(段 2 文件面 adapter.py/decision_assembly.py/mandate.py/
proof.py 与波 4 段②在飞清单重叠,文件互斥约束同 §1.3-1)。完成判据 = §4-P3/P4/P5/P7/P8。

**段 3·商店黑板槽退役收尾(规模 S)**。范围 = §2.5 shop_state_frame 全部(M2 移缴
面承接)。文件面 = cw_op_buy_cards.py、cw_strategy_session.py(+测试仓 M2 锁)。
依赖 = **波 4 落库**;与段 1/段 2 无相互依赖,可并行派(文件域互斥满足:
r5-migration-plan「同一时刻最多两波在飞」约束下,段 1 与段 3 不同文件域可并行)。

段 3 完成即本设计全部落地;固定末阶段 = 正本更新(fields.md §8 符号指针
apply_prep_action_logic 登记行、session 正本槽注、《商店黑板容器化方案》M2 行收敛、
迁移规划波次表 prep 面行),清单由 landing.md 承载。

## 3. 关键取舍

- **决策读容器单例(选) vs prep 槽换载体(弃)**:换载体(槽保留、obs.state 换
  BoardState 快照或派生读口)改动最小,但保留第二状态面——视图/槽双载体永续、
  cw_bs_view 退役被绊、同帧三载体照旧,是症状搬迁非治本(与《商店黑板容器化方案》
  §3 第一条同构论证)。
- **视图合成层随签名切换消亡(选) vs 保留视图供下游(弃)**:下游全簇切换后视图
  零消费;保留 = 第二转换层永续 + hp 双门混装残留(§1.2 症状③)。代价 = 段 2
  一次吃下 prep 域全簇(规模 L),但该簇切换是消点的必要前置,拆开反而制造
  「视图只剩单一读者」的中间态两批付审查面。
- **obs.state 槽删除(选) vs 退化为执行侧透传槽(弃)**:last_state 已是执行侧
  装配/透传槽,双槽同义 = 重复状态面;对账/显示类读者(§1.1 读点表)读数域全部
  有容器读口,无不可替代读者。
- **hp 消费经 decision_hp(选) vs 直读 bs.hp.value(弃)**:波 2 政策读口是施门
  单一源,直读 = 施门旁路,血线决策漂移(调研草案 §5 风险 1 同族)。
- **last_state 写点不提前删(选) vs 随段 2 顺删(弃)**:写点删除前提 = 喂入反转
  (波 5 整体改造);提前删读者悬空,违先接后删(§2.5 边界表)。
- **分三段(选) vs 单批(弃)**:波 4 在飞文件面强制分波依赖;三段各自可独立验收,
  段 1/段 3 可并行缩短关键路径(§2.8)。

## 4. 锁面(落地卡 criteria 输入,问题⑥)

| # | 锁 | 断格内容 |
|---|---|---|
| P1 | 五处签名行为等价锁 | prep 决策行为锁族既有断格重申:球门成效签名(①)/λ 分位触发(②③,含 None 域不评估与缺省镜像)/姿态对账逐门定位(④)/EV 面发射组织(⑤);载体切容器后同输入同输出(对象测试面直喂 bs 构造) |
| P2 | 漏斗判据等价锁 | level_spend_blocked/levelup_budget_gate/line_switch_sell/funding_support_sell 切 bs 后判定矩阵逐格等价;locked_buy_cap_hold 双形态值等价断言 |
| P3 | game_state_view 零活调用锁 | 段 2 后全仓(src+测试仓)`game_state_view(` 活调用 grep=0(定义与 strategy_input_state 包装残留由波 5 删文件时一并消;注释提及不辖) |
| P4 | obs.state 槽零引用锁 | 段 2 后全仓(src+测试仓)`PrepObservation` 的 state 槽属性访问与字段定义 grep=0;`state_gold_trusted` 消费(cw_loop 指纹)零波及断言 |
| P5 | prep 投影等价锁+登记面 | `apply_prep_action_logic` vs 旧投影 state 腿:SellBench 同输入逐域等价(gold 回金公式/摘槽);域集封闭断言(集外动作零写)+ None 跳写清单与登记面申报(形态对齐《商店黑板容器化方案》§4-M5) |
| P6 | prep 域容器单源锁 | 段 2 后 prep 决策链(run_mandate/proof/criteria 族)`GameState` 形参与帧字段读 grep=0(predicates 容器支外的帧兼容支删除断言);对账族读容器 payload 断言 |
| P7 | last_state 决策依赖清零锁 | 段 1 起持续绿:prep 决策链文件集(entry.py)对 `last_state` 直读 grep=0(写点与执行侧读者不辖,§2.5 边界表) |
| P8 | 帧代次标注契约形状锁重推 | 既有 L6 形状锁按写点清单变更重推:prep 写点增 `apply_prep_action_logic` 投影 none 写/finalize view 写保留;shop 写点随段 3 收敛;标注槽保留断言(ADR-0583 §3.4) |
| M2 | shop_state_frame 零引用锁 | 段 3 后全仓(src+测试仓)`shop_state_frame` grep=0(《商店黑板容器化方案》§4-M2 移缴承接) |

验证三元组:测试锁族(上表)+ 落地审(独立干净上下文 reviewer 逐 hunk)+ 实机窗口
——备战链 ≥1 完整局直接暴露(备战决策/投影推进/买后重估/last_state 链行为判读;
局数候编排者,建议段 2 交付后 ≥1 局、全部段落地后随波 5 实机窗口合并判读)。
测试仓基线参考:sr-od-test 对应域 = test_cw_mandate_decide / test_cw_p2_blood_band /
test_cw_mandate_lifecycle(原 test_cw_prep_flag_machine,git mv 改名) /
test_cw_board_state_consume / test_cw_obs_arch_prep_writeflow
(last_state 写点锁,段内零变化断言)/ test_cw_migration_budget_authority(迁移哨兵);
批首按消费函数名 grep 补全(调研草案 §1 方法论申报同款义务)。
