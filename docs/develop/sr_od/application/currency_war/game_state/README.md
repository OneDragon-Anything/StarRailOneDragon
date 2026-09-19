# GameState 设计总纲

> 本文档所属 = game_state 设计目录(本目录总纲)。
> **命名对应注**:本文档所称 **GameState**(统一 state),即代码类名
> (`src/sr_od/application/currency_war/kernel/cw_game_state.py`;
> 旧名 BoardState/旧模块名 cw_board_state.py,两者指同一容器)。
> 路径缩写约定:本文反引号短路径 `research/X.md`/`data/X.md` 等 = `docs/game/currency_war/` 下对应文件(非 src 树);game 侧文档同理指向本仓 docs/。


## 1. 本目录是什么

统一 state(GameState)的设计文档正式目录,总-分结构:本文件=总纲,分篇各管一面;
另有动作逻辑态总则与逐动作更新规格子目录(§4)。字段级完整规格(字段清单、决策 op 写入面、
效果族归属、生命周期与治理面)的正本 = [fields.md](fields.md)(沿用原详设节号体系,
代码注释所引节号以该篇为解析归宿);本目录自足,不依赖任何迭代过程件。

上位裁定与 why(ADR 档案体系已按用户令整体退役,裁定 why 的归宿 = 本目录正本动机段 + git 历史)。
**现行有效上位裁定三条**:①守卫族终版(节点域守卫族口径,见 [node-domain.md](node-domain.md) §4);
②单字段双值结构(§2 设计理念);③字段层次终极版(观察层=原始读数/逻辑层=计算值,§2 第 1-2 条)。
承载这三条的记录机制 = [journal.md](journal.md)(三渠道写入口 observe/carry/write_prior + 自足快照变更账)。

## 2. 设计理念(六条)

1. **观察如实上报**。观察层=画面原始读数,零计算——observe() 只落原文,禁写派生值。
   例:备战帧顶栏 OCR 读到「备战阶段 1-3」,原文整串进观察层字段 `top_bar_raw`;
   把原文解析成序键 3 是计算,归逻辑层。
2. **state 内派生逻辑态**。逻辑层=从观察数据**计算**的一切(节点序键/节点类型/效果
   计数/统计)。派生规则是 state 内部逻辑,在同一写入事务内完成——**无独立事件流**,
   一切派生产出都是 state 写入,不存在「hook 触发后再写」的第二条路径。
3. **单字段双值结构**。一个事实 = 一个逻辑层值字段 + 一个原始读数字段,不设两个
   专名字段再在读时合并。例:节点序 = `top_bar_raw`(观察层)+ `node_ord`(逻辑层)。
   单事实单值字段(金/hp 等)不拆,来源与质量维由渠道签名承载(见 journal.md §3)。
4. **唯一写入口,禁旁路**。一切写入必经统一写入口(Field 系 API)或 inventory 方法域
   (效果域);绕 API 直改字段=违反,机器面=grep 子串守卫锁(先例
   = 旧 12 流写面删除批「旧流文件名全仓零写点」grep 锁手法)。
5. **单版本事务**。一次逻辑写入 = 一个版本 = 一笔自足快照行:写入口收到写入后,同一
   事务内先落原始变更,再按固定次序跑关注点派生(节点判定→类型→效果推进),所有连带
   字段更新共享同一版本 id;原子性=派生出错整笔回滚留证,无中间态。
6. **行行自足账本**。任一账本行 = 改了什么 + 渠道签名 + 版本 id + 写入后完整 state
   快照;查询=按行直接读,零重放、零前溯、零锚、零对账。崩溃丢失窗=该时点无行,
   诚实缺失。

## 3. 核心规范摘要

### 3.1 写入口两分法:observe() / write_logic()

写入 API 按数据层两分(符号=kernel/cw_game_state.py):

| 写口 | 层 | 用途 |
|---|---|---|
| `observe()` | 观察层 | 亲眼看到的原始读数,覆盖旧值;value=None 拒绝(缺读不写禁猜) |
| `write_logic()` | 逻辑层 | 按游戏规则推算的逻辑值**直接写字段**(两态制 标准通道,策略器立即可读;非免检——值之后仍受观察覆盖辖) |

配套口:`carry()`(失读沿用,evidence 带 carried:来源帧)/`write_prior()`
(先验写入,如开局 hp 先验)/`leave_screen()`(画面附加域离屏置 None)/`relay()`
(接管中继)/`note_obs_event()`(零状态变更的观察事件留证行)。完整 API 契约见
journal.md §6,符号单一源 = kernel/cw_game_state.py(字段级规格 =
[fields.md](fields.md) §8)。(原 `expect()`/`confirm()`/`discard_expected()`
两步机制已随统一 state 直迁废除。)

### 3.2 权威序

- **观察赢**:观察写入覆盖 logic 来源值;失配记 `observe_vs_logic_mismatch` 缺陷行
  (留证显影,不静默)。失配 = 推算代码 bug,修推算代码。失配比对前的**前置吸收
  面**(形状受控的机制性差异,命中即台账行采新、不进安灯):gold 节点边界金补结
  闩(boundary_gold_backfilled)/ front_row、back_row 行槽位纯重排
  (deploy_slot_reorder,同单位多重集仅排列差异 = 游戏侧行内重排无逻辑
  写端,采新入纠漂面)/ board 派生漂移观察覆盖采新(board_derived_adopt,辖
  `proj_board_resync` 写端)。**已知缺口**:bench/equips 投资卡随机授予、
  晶矿随机金现无吸收规则(随机对账申报面 2026-09-19 用户裁定整体拆除待重设计),
  命中照真失配停。
- **board 派生量**(禁独立写):上阵羁绊计数 = front_row/back_row 单位集合的派生量,
  逻辑写端经 `write_logic` 行域挂钩 `_resync_board_delta` 单一源自动重算(观察基座 +
  行变更增量);独立手写 board = 越格(非派生写端的 board 失配照真失配停)。派生量
  以观察为真值源:派生漂移(环境卡星徽幽灵计数/未知身份零贡献/徽标 OCR 坏读)
  经观察覆盖采新收敛,落 `board_derived_adopt` 台账行不进安灯——「上阵单位集合」
  这一真不变量由行域自身失配面独立把守。观察侧仍按双源仲裁覆盖(观察赢辖)。
- **节点生效序**:权威序字段的读口 = 生效序读口,语义=逻辑层现值与 run 内高水位
  取大(公式体单一源见 [node-domain.md](node-domain.md) §3);消费面恒取逻辑层。
- **节点类型三源仲裁**:结算屏权威> 节点序列台账现读 > 帧标签 OCR
  ([fields.md](fields.md) §3.2.1;仲裁细则单一源 = node-domain.md)。

**容器字段投影完备性审计**:全部 Field 字段对「游戏侧变更是否可造成 observe 失配」
的三分类注册面 = `kernel/cw_projection_audit.py`(`PROJECTION_AUDIT`;「无写端无规则」
缺口恒空,完备性锁在测试仓 test_cw_board_derived_and_reorder.py);字段级语义正本
仍 = [fields.md](fields.md)。

### 3.3 域清单

统一 state 按域组织(域=字段分组,读不分域;写入域准入白名单=迁移批裁定硬
约束,逐格以实码写点全集为准;域键=gs_schema 键,字段全集逐字段规格 =
[fields.md](fields.md)):

| 域(gs_schema 键) | 字段全集 | 主写渠道 |
|---|---|---|
| 节点域(node) | node(NodeKey)/ node_path | ①观察+③派生(见 node-domain.md) |
| 派生域(derivation) | top_bar_raw(观察层)/ node_ord(逻辑层)/ prev_screen / current_screen / node_hist_ord(哨兵) | ①观察+③派生(见 node-domain.md §2-§3) |
| 单位域(units) | front_row / back_row / bench(BenchView)/ back_layout / deploy_cap | ①观察+②动作+③效果桥 |
| 经济域(economy) | gold / hp / level / xp / streak / level_up_cost / shop_refresh_cost | ①观察+②动作 |
| 商店刷新计数域(refresh_counters) | 三计数已迁出容器住效果账本(2026-09-18,写端=刷新上报函数);prev_node_spent 保留容器(economy 面) | ②动作+③效果桥 |
| 节点屏刷新计数域(node_screen_refresh) | encounter_refresh_used / supply_refresh_used / env_refresh_used / strategy_refresh_used(逐卡) | ②动作(遭遇/策略经 on_outcome 发射钩子写、补给为 live 刷新发射单点,三写端在产;环境零写端在册) |
| 持久账本域(inventory) | equips / consumables(免战牌载体归一入效果账本,不在本域) | ①观察+②动作 |
| 晶矿域(spheres) | spheres | ①观察 |
| 交互状态域(substate) | prep_substate(分类子态四档)/ event_overlay | ①观察+③接管协议 |
| 画面 payload 域(shop/encounter/supply) | shop / encounter / supply(非当前画面=None) | ①观察 |
| 选择结果域(event_choices) | chosen_encounter / chosen_supply / chosen_megastar / chosen_partner / chosen_wish / chosen_fortune / chosen_hack / chosen_expert / chosen_tome / chosen_equip | ②选择 handler 单次逻辑写 |
| 结算域(settlement) | settlement(hp/streak/gold/level 结算真值)/ hp_floor_triggered(纯观察登记) | ①观察 |
| 局级事实域(match_facts) | selected_difficulty / game_mode / enemy_difficulty / plane_bosses / enemy_affixes / active_env / active_strategies / board / resumed_match / takeover_collect_done / takeover_tries | ①观察+②动作+③中继+③接管协议(后三字段,渠道 logic_hook;域版本 2) |
| 轮内账域(round_ledger) | round_fresh_buys(值形状 `{'phase': tuple|None, 'names': list[str]}`) | ②动作(record_fresh_buy 单口写,sim/live 同口) |
| 效果账本域(effects) | effects(ActiveEffectInventory 实例清单;非 Field 载体) | inventory 方法域(随快照行自带) |
| 动作回执域(receipts) | receipts(滚动窗,容量常量 RECEIPTS_WINDOW_CAP) | ②动作 |
| 局终域(match_final) | match_final(一段终态一行;恢复局跨段多行) | ③局终收口 |
| 工程结构(非 Field) | schema_version / gs_schema / frame_obs / write_seq / hb_prev_seq / hb_stall_count / created_monotonic;非域簿记组与台账单列——`exec_books`(ExecBooks 执行侧过程簿记组:外部授予待吸收闩族,直读 `game_state_of(session).exec_books`)/ `tracked_books`(TrackedBooks 主账槽位簿记)/ `plane_node_sequences`(位面节点序列台账,PlaneNodeLedger 载体;访问口 = cw_exec_state 三访问函数) | 构造/迁移写;簿记组/台账 = 直读属性(非 Field 无渠道面) |

渠道族封闭集 = obs(画面 op 观察)/ logic_action(动作 op 逻辑计算)/ logic_hook
(state 内部派生逻辑计算);carried/prior/synthesized 是 obs 族内子模,非第四源。

## 4. 文档地图

| 分篇 | 管什么 |
|---|---|
| [fields.md](fields.md) | 字段级完整规格(原详设节号体系 §1-§8 + §9 推演内核帧映射对账):逐字段语义/写端/边界、决策 op 写入面、效果族写入归属、生命周期与治理面;代码注释所引节号的解析归宿 |
| [journal.md](journal.md) | 记录机制:账本文件、三渠道封闭集与渠道签名、版本 id 与单版本事务、自足快照行、落盘与查询 |
| [effect-domain.md](effect-domain.md) | 效果域:在场效果账本的内容语义(计数器模型/实例清单/分类词表/生命周期/逐效果规格) |
| [node-domain.md](node-domain.md) | 节点域:字段双层、生效序读口与 hist 哨兵、守卫族、派生规则单一源引用 |
| [node-derivation.md](node-derivation.md) | 节点推进判定方案(派生规则单一源持久家):四规则组本体/画面流转全景图/场景走查/实现位与载荷锚 |
| [strategy-env-impacts.md](strategy-env-impacts.md) | 投资策略/环境逐效果在 state 里的影响(已确认条目+候逐条确定占位清单) |
| [chain-observation.md](chain-observation.md) | 链观察对接:基线链/现行链双源、diff 证据、与遥测账本的挂接 |
| [retirement.md](retirement.md) | 旧 12 流退役逐流处置与消费方迁移清单 |
| [action-logic-state.md](action-logic-state.md) | 动作逻辑态总则:两态制纪律、写口归属硬规则(动作 op 只上报动作,逻辑态更新由 game state 独占)、确定面/随机面、拒绝语义 |
| [logic-updates/](logic-updates/README.md) | 逐动作逻辑态更新规格(每动作 op 一篇:域集/转移规则/随机面/拒绝语义/kernel 符号锚) |

## 5. 边界与姊妹文档

- **推演内核帧分界**:sim 推演内核帧(CwSimFrame,符号 =
  `kernel/cw_vocab.py`)与本容器是平行表示,不是镜像——帧 = sim 侧
  局面帧类型(转移/检查/离线重建面载体),容器 = 实机真值记录模型;
  生产写入 = sim 引擎直写本容器(渠道签名写入口,渠道族封闭集见 §3),
  帧的「环境真值工作态」身份随引擎切容器收敛为推演/离线面;表示分界、
  写入契约与逐字段映射对账 = [fields.md](fields.md) §9。
- **字段级规格**=[fields.md](fields.md)(本目录分篇,正本)——字段清单/决策 op
  写入面/效果族归属/生命周期/治理面;与其冲突时以代码现状为准,正文随代码同步修订。
- **派生规则单一源**=场景一判定方案([node-derivation.md](node-derivation.md))——本目录引用不复写。
- **旧流退役处置**=[retirement.md](retirement.md)(本目录分篇;退役排期过程件归 git 历史)。
- **链观察**=[chain-observation.md](chain-observation.md)(本目录分篇,链观察对接面正本);链观察设计原始件已随过程区清理退役,考古走 git 历史。
- **效果域内容语义**(计数器模型/生命周期/逐效果规格)=
  [effect-domain.md](effect-domain.md);本目录只记捕获面
  (效果变化随快照行自带)与逐效果 state 影响登记。
- **策略侧遥测(决策行文件)**= 两文件模型的另一文件,schema 正本 =
  [决策行文件schema设计.md](决策行文件schema设计.md)(本目录分篇);state 引用
  只经版本钉 state_ref=`(run_id, v)`,且决策输入禁读状态流水。
- 玩法语义(各效果游戏机制原文/节点流转时序)挂靠
  [docs/game/currency_war/](../../../../../game/currency_war/)(game 子树)。
