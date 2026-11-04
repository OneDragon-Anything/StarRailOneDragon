# GameState 设计总纲

> 本文档所属 = game_state 设计目录(本目录总纲)。
> **命名对应注**:本文档所称 **GameState**(统一 state),即代码类名
> (`src/sr_od/application/currency_war/kernel/cw_game_state.py`;
> 旧名 BoardState/旧模块名 cw_board_state.py,两者指同一状态容器(GameState))。
> 路径缩写约定:本文反引号短路径 `research/X.md`/`data/X.md` 等 = `docs/game/currency_war/` 下对应文件(非 src 树);game 侧文档同理指向本仓 docs/。


## 1. 本目录是什么

统一 state(GameState)的设计文档正式目录,总-分结构:本文件=总纲,分篇各管一面;
另有动作逻辑态总则与逐动作更新规格子目录(§4)。字段级完整规格(字段清单、决策 op 写入面、
效果族归属、生命周期与治理面)的权威版本 = [fields.md](fields.md)(沿用原详设节号体系,
代码注释所引节号以该篇为解析归宿);本目录自足,不依赖任何迭代过程件。

上位裁定与 why(ADR 档案体系已按用户令整体停用,裁定 why 的归宿 = 本目录权威版本动机段 + git 历史)。
**现行有效的三条上位裁定**:
①**节点前进由动作上报触发,画面读数只用来核对**——点下「继续挑战」「确认」这类终结动作就立即上报推进;
  画面读出的节点号只做对账核对(对账 = 推算状态与下一帧实读逐项比对,对不上即 bug),不再当推进的触发器
  (规则本体唯一权威出处 = [node-derivation.md](node-derivation.md) §3.3;旧的「从画面推断推进」口径连同守卫已停用)。
②**一个事实存两个字段**——一个逻辑层值字段 + 一个原始读数字段,不设两个专名字段再在读时合并(§2 设计理念第 3 条)。
③**字段分层的最终版**——一个事实按四层落位:原始读数(观察层)/按规则推算的值(逻辑层)/读时现算的派生读取入口
  (不存储)/单调历史水位,以节点域四件套为样板(§2 第 1-2 条;[node-domain.md](node-domain.md) §2);
  节点域另有一条「直写改判」:节点序位允许观察侧用画面识别标志确认后直接写入(不走通用观察通道),
  这是对旧裁决「禁止观察直写序位键」的改判,见 [node-derivation.md](node-derivation.md) §3.2-7。
承载这三条的记录机制 = [journal.md](journal.md)(三个渠道写入口 observe/carry/write_prior + 自足快照变更账)。

## 2. 设计理念(六条)

1. **观察如实上报**。观察层=画面原始读数,零计算——observe() 只落原文,禁写派生值。
   例:备战帧顶栏 OCR 读到「备战阶段 1-3」,原文整串进观察层字段 `top_bar_raw`;
   把原文解析成序键 3 是计算,归逻辑层。
2. **state 内派生逻辑态**。逻辑层=从观察数据**计算**的一切(节点序键/节点类型/效果
   计数/统计)。派生规则是 state 内部逻辑,在同一写入事务内完成——**无独立事件流**,
   一切派生产出都是 state 写入,不存在「hook 触发后再写」的第二条路径。
3. **单字段双值结构**。一个事实 = 一个逻辑层值字段 + 一个原始读数字段,不设两个
   专名字段再在读时合并。例:节点序位 = `top_bar_raw`(观察层)+ `node_pos`(逻辑层)。
   单事实单值字段(金/hp 等)不拆,来源与质量维由渠道签名承载(见 journal.md §3)。
4. **唯一写入口,禁旁路**。一切写入必经统一写入口(Field 系 API)或 inventory 方法域
   (效果域);绕 API 直改字段=违反,机器面=grep 子串守卫测试(先例
   = 旧 12 流写面删除批「旧流文件名全仓零写入位置」grep 守卫手法)。
5. **单版本事务**。一次逻辑写入 = 一个版本 = 一笔自足快照行:写入口收到写入后,同一
   事务内先落原始变更,再按固定次序跑关注点派生(节点判定→类型→效果推进),所有连带
   字段更新共享同一版本 id;原子性=派生出错整笔回滚保留证据,无中间态。
6. **行行自足账本**。任一账本行 = 改了什么 + 渠道签名 + 版本 id + 写入后完整 state
   快照;查询=按行直接读,零重放、零前溯、零锚定点、零对账。崩溃丢失窗=该时点无行,
   诚实缺失。

## 3. 核心规范摘要

### 3.1 写入口:observe() / write_logic() / write_logic_rand()

写入 API 按数据层两分 + 随机扩展(符号=kernel/cw_game_state.py):

| 写入入口 | 层 | 用途 |
|---|---|---|
| `observe()` | 观察层 | 亲眼看到的原始读数,覆盖旧值;value=None 拒绝(缺读不写禁猜) |
| `write_logic()` | 逻辑层 | 按游戏规则推算的逻辑值**直接写字段**(两态制 标准通道,策略器立即可读;非免检——值之后仍会被观察覆盖) |
| `write_logic_rand()` | 逻辑层·随机扩展 | 随机效果动作的采样推算直写(详见 [fields.md](fields.md) §2.5) |

配套口:`carry()`(失读沿用,evidence 带 carried:来源帧;**logic_rand 来源不沿用**
——随机态种子/采样值非「上次好值」,fields.md §2.2)/`write_prior()`
(先验写入,如开局 hp 先验)/`leave_screen()`(画面附加域离屏置 None)/`relay()`
(接管中继)/`note_obs_event()`(零状态变更的观察事件保留证据行)。完整 API 契约见
journal.md §6,符号单一源 = kernel/cw_game_state.py(字段级规格 =
[fields.md](fields.md) §8)。(原 `expect()`/`confirm()`/`discard_expected()`
两步机制已随统一 state 直迁废除。)
**开局预填初值与锚定标志位**:每局全新创建时按开局真值预填一批字段(rand 随机态)+ `prep_anchored` 标志位 +
通道选择入口 `anchor_aware_write`——rand 通道「消费前必须重观察」纪律的显式例外(种子值/未确认期
链写供直接消费,确认后恢复纪律),权威版本 = [fields.md](fields.md) §2.6。

### 3.2 权威序

- **以实际观察为准**:观察写入覆盖 logic 来源值;失配记 `observe_vs_logic_mismatch` 缺陷记录行
  (保留证据、暴露出来,不静默)。失配 = 推算代码 bug,修推算代码。失配比对前的**已知机制性差异白名单**
  ——以下三种已知差异不算推算错误,读到新值就直接采纳并记一行日志(不触发告警停机;失配告警首现注:
  发现失配即报警并停机):
  ① 节点边界把差额金币补回(gold 节点边界金补齐,`boundary_gold_backfilled`);
  ② 上阵行内单位只换位置、成员不变(front_row/back_row 行槽位纯重排,`deploy_slot_reorder`
  ——同单位多重集仅排列差异 = 游戏侧行内重排、无逻辑写入方,直接采纳新读数并做纠偏处理);
  ③ board 羁绊计数与观察不一致(board 派生漂移,观察覆盖直接采纳新读数,`board_derived_adopt`,
  适用于 `proj_board_resync` 写入方)。**逻辑随机态旁路**:logic_rand 来源值的观察
  覆盖差异 = 随机效果落地预期内,落 `logic_rand_outcome` 记录行直接采纳新读数
  (无告警无停机),不经失配的三种标准处理分支——三分支 = ①白名单差异直接采纳
  ②logic_rand 预期内差异记录采纳 ③真失配记缺陷并停机。**已知缺口**:bench/equips 投资卡随机授予、
  晶矿随机金现无吸收规则(随机对账申报面 2026-09-19 用户裁定整体拆除待重设计;
  重设计机制位置 = 逻辑随机态 write_logic_rand,写入方接入调用归后续批),
  命中照真失配停。
- **board 派生量**(禁独立写):上阵羁绊计数 = front_row/back_row 单位集合的派生量,
  逻辑写入方经 `write_logic` 行域挂钩 `_resync_board_delta` 单一源自动重算(观察基座 +
  行变更增量);独立手写 board = 违反约束的写入(非派生写入方的 board 失配照真失配停)。派生量
  以观察为真值源:派生漂移(环境卡星徽幽灵计数/未知身份零贡献/徽标 OCR 坏读)
  经观察覆盖直接采纳新读数收敛,落 `board_derived_adopt` 记录行不触发失配告警——「上阵单位集合」
  这一真不变量由行域自身失配面独立把守。观察侧仍按双源仲裁覆盖(以实际观察为准)。
- **节点生效序**:权威序位字段的读取入口 = 生效序读取入口,语义=`node_pos` 现值与 run 内
  高水位按元组字典序取大(公式体与消费纪律 = [node-domain.md](node-domain.md) §3);两态来源
  语义(id_mark 确认态/推进态)单一源 = [node-derivation.md](node-derivation.md) §3.2-7。
- **节点类型三源仲裁**:结算屏权威> 节点序列记录表现读 > 帧标签 OCR
  ([fields.md](fields.md) §3.2.1;类型派生权威链与冲突保留证据单一源 =
  [node-derivation.md](node-derivation.md) §3.3-5,指针 = [node-domain.md](node-domain.md) §7)。

**状态容器字段投影完备性审计**:每个字段都在 `kernel/cw_projection_audit.py` 登记了
「游戏改动会不会导致观察对不上」的分类(`PROJECTION_AUDIT`;「无写入方无规则」
缺口恒空,齐全性由测试仓 test_board_derived_and_reorder.py 保证);字段级语义权威版本
仍 = [fields.md](fields.md)。

### 3.3 域清单

统一 state 按域组织(域=字段分组,读不分域;写入域准入白名单=迁移批裁定硬
约束,逐格以实码写入位置全集为准;域键=gs_schema 键,字段全集逐字段规格 =
[fields.md](fields.md)):

| 域(gs_schema 键) | 字段全集 | 主写渠道 |
|---|---|---|
| 节点域(node) | node(NodeKey)/ node_path | ①观察+③派生(见 node-domain.md) |
| 派生域(derivation) | top_bar_raw(观察层)/ node_pos(逻辑层,`(位面, 轮)` 序位)/ prev_screen / current_screen / node_hist_pos(哨兵) | ①观察+③派生(见 node-domain.md §2-§3) |
| 单位域(units) | front_row / back_row / bench(BenchView)/ back_layout / deploy_cap | ①观察+②动作+③效果桥 |
| 经济域(economy) | gold / hp / level / xp / streak / level_up_cost / shop_refresh_cost | ①观察+②动作 |
| 商店刷新计数域(refresh_counters) | 免费刷新剩余次数 = 状态容器字段 free_refresh_left(Field,剩余语义,三写入方同格);付费/全量两计数放在效果账本(写入方=刷新上报函数);prev_node_spent 保留状态容器(economy 面) | ①观察+②动作+③效果桥 |
| 节点屏刷新计数域(node_screen_refresh) | env_refresh_left / strategy_refresh_left(逐卡,键 = 注册表规范卡名)/ encounter_refresh_left / supply_refresh_left(四字段均剩余语义:屏显「剩余次数」观察真值;旧 `*_refresh_used` 已用计数字段已停用,考古走 git) | ①观察(各屏观察 report 数据进入点摄入,读缺跳写、None = 未观察 = 拒绝;encounter 写入方 = `report_screen_encounter_obs`)+ sim 写入方(仅 supply_refresh_left;遭遇/投资两屏无 sim 刷新执行面;逐字段规格 = fields.md §3.4.1–§3.4.4) |
| 持久账本域(inventory) | equips / consumables(免战牌载体归一入效果账本,不在本域) | ①观察+②动作 |
| 晶矿域(spheres) | spheres | ①观察 |
| 交互状态域(substate) | prep_substate(分类子态四档)/ event_overlay | ①观察+③接管协议 |
| 画面 payload 域(shop/encounter/supply) | shop / encounter / supply(非当前画面=None) | ①观察 |
| 选择结果域(event_choices) | chosen_encounter / chosen_supply / chosen_megastar / chosen_partner / chosen_wish / chosen_fortune / chosen_hack / chosen_expert / chosen_tome / chosen_equip | ②选择 handler 单次逻辑写 |
| 结算域(settlement) | settlement(hp/streak/gold/level 结算真值)/ hp_floor_triggered(纯观察登记) | ①观察 |
| 局级事实域(match_facts) | selected_difficulty / game_mode / enemy_difficulty / plane_bosses / enemy_affixes / active_env / active_strategies / board(resumed_match 已停用,域版本 5) | ①观察+②动作+③中继 |
| 轮内账域(round_ledger) | round_fresh_buys(值形状 `{'phase': tuple|None, 'names': list[str]}`) | ②动作(record_fresh_buy 唯一入口写,sim/live 同口) |
| 效果账本域(effects) | effects(ActiveEffectInventory 实例清单;非 Field 载体) | inventory 方法域(随快照行自带) |
| 动作回执域(receipts) | receipts(滚动窗,容量常量 RECEIPTS_WINDOW_CAP) | ②动作 |
| 局终域(match_final) | match_final(一段终态一行;恢复局跨段多行) | ③局终收尾 |
| 工程结构(非 Field) | schema_version / gs_schema / frame_obs / write_seq / hb_prev_seq / hb_stall_count / created_monotonic / prep_anchored(锚定标志位,fields.md §2.6);非域记录表单列——`plane_node_sequences`(位面节点序列记录表,PlaneNodeLedger 载体;读取入口 = cw_exec_state 三访问函数) | 构造/迁移写;簿记组/记录表 = 直读属性(非 Field 无渠道面) |

渠道族封闭集 = obs(画面 op 观察)/ logic_action(动作 op 逻辑计算)/ logic_hook
(state 内部派生逻辑计算);carried/prior/synthesized 是 obs 族内子模,非第四源。

## 4. 文档地图

| 分篇 | 管什么 |
|---|---|
| [fields.md](fields.md) | 字段级完整规格(原详设节号体系 §1-§8 + §9 与 sim 的表示分界):逐字段语义/写入方/边界、决策 op 写入面、效果族写入归属、生命周期与治理面;代码注释所引节号的解析归宿 |
| [journal.md](journal.md) | 记录机制:账本文件、三渠道封闭集与渠道签名、版本 id 与单版本事务、自足快照行、落盘与查询 |
| [effect-domain.md](effect-domain.md) | 效果域:在场效果账本的内容语义(计数器模型/实例清单/分类清单/生命周期/逐效果规格) |
| [node-domain.md](node-domain.md) | 节点域索引篇:生效序读取入口与消费纪律、记录面分工、类型派生与链查询指针;规则本体单一源引用(不在两处重复写) |
| [node-derivation.md](node-derivation.md) | 节点推进判定方案(派生规则单一源持久家):终结动作上报+观察 id_mark 确认规则本体/画面流转全景图/场景走查/停用申报 |
| [strategy-env-impacts.md](strategy-env-impacts.md) | 投资策略/环境逐效果在 state 里的影响(已确认条目+待逐条确定占位清单) |
| [chain-observation.md](chain-observation.md) | 链观察对接:基线链/现行链双源、diff 证据、与遥测记录表的接入 |
| [retirement.md](retirement.md) | 旧 12 流停用逐流处置与消费方迁移清单 |
| [action-logic-state.md](action-logic-state.md) | 动作逻辑态总则:两态制纪律(+逻辑随机态扩展)、写入入口归属硬规则(动作 op 只上报动作,逻辑态更新由 game state 独占)、确定面/随机面、拒绝语义 |
| [logic-updates/](logic-updates/README.md) | 逐动作逻辑态更新规格(每动作 op 一篇:域集/转移规则/随机面/拒绝语义/kernel 符号名引用) |

## 5. 边界与姊妹文档

- **sim 表示分界**:sim 与 live 同一状态容器类型、同一份单例(`game_state_of(session)`)
  ——后端状态副本里的值写 obs 渠道,动作效果经动作 op 上报函数族走 logic_action 渠道
  (渠道签名写入口,渠道族封闭集见 §3);不存在「状态容器 ↔
  中间帧」映射层(原推演内核帧及其合成口已随帧通道停用,考古归 git 历史)。
  表示分界与对接对照表 = [fields.md](fields.md) §9 与 [../sim/sim-wiring.md](../sim/sim-wiring.md)。
- **字段级规格**=[fields.md](fields.md)(本目录分篇,权威版本)——字段清单/决策 op
  写入面/效果族归属/生命周期/治理面;与其冲突时以代码现状为准,正文随代码同步修订。
- **派生规则单一源**=场景一判定方案([node-derivation.md](node-derivation.md))——本目录引用不复写。
- **旧流停用处置**=[retirement.md](retirement.md)(本目录分篇;停用排期过程件归 git 历史)。
- **链观察**=[chain-observation.md](chain-observation.md)(本目录分篇,链观察对接面权威版本);链观察设计原始件已随过程区清理停用,考古走 git 历史。
- **效果域内容语义**(计数器模型/生命周期/逐效果规格)=
  [effect-domain.md](effect-domain.md);本目录只记捕获面
  (效果变化随快照行自带)与逐效果 state 影响登记。
- **策略侧遥测(决策行文件)**= 两文件模型的另一文件,schema 权威版本 =
  [决策行文件schema设计.md](决策行文件schema设计.md)(本目录分篇);state 引用
  只经版本钉 state_ref=`(run_id, v)`,且决策输入禁读状态流水。
- 玩法语义(各效果游戏机制原文/节点流转时序)挂靠
  [docs/game/currency_war/](../../../../../game/currency_war/)(game 子树)。

## 6. 术语表

本目录术语已并入统一术语表 [../terminology.md](../terminology.md)（唯一速查入口：替换词 / 保留词定义 / 游戏内容词保护清单）；本节不再维护第二张表。
