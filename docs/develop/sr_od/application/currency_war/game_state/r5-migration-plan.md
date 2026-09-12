# R5 迁移规划 v2——单源直迁:旧 12 流代码删除 + GameState 本体退役
> **持久家声明**(2026-09-11 晋升入库):本文自临时档 `.debug/temp/currency_war/R5-迁移规划.md`(v2.1)内容原样迁入;temp 原件降为工作副本,后续修订以本文件为准(单源直迁八波排期,重构 retirement.md 影子框架的裁决口径)。

> **v2 重写声明**:用户裁定(2026-09-10,经编排者转达)**不用影子开关/影子期——直接迁移并删除旧代码**,
> 覆盖 retirement.md 既有影子框架。本文件按单源直迁口径整体重写,替换 v1(影子口径版,已废弃)。
>
> **修订行(v2.1 增量修正令,编排者转达用户裁定:影子开关销案)**:
> 1. 全篇验收判据统一锚定「**测试锁族+落地审+实机窗口直接暴露**」,影子期等待语义零残留——
>    全文扫描在案:余下「影子」字样仅存于裁定转述/R1 已交付代码事实/§8 销案清单/风险立场
>    表述(「无影子缓冲」=已接受风险,非等待语义);原 v1 的「候影子语料」类门(W4B 对拍/
>    W5 进入门/P7 进入门)在 v2 重构时已全部改锚三元组,本轮复核零条勘误。
> 2. **主账本时代序**:W3 判读/哨兵/运行时切换(含删旧读面)完成后,journal 即为唯一被读
>    账本;旧流仅余无读者的写面存活至 W7 物理删除。W4 审计并行位保持。
> 3. §6/§7 于 v2 已随波次重构改写(P4/P5/P7 门现锚三元组与先接后删/先迁后删波序),本轮
>    复核无影子残留。
> 4. 波数对账申报:v1「七波骨架」在直迁重构(前一修正令:透传域建模进关键路径、写面/本体
>    删除分波)下已演化为**八波**;本版维持八波。若编排者按「七波维持」要求并回,候选合并位
>    =W4 并入 W3 尾(审计+流删同包)或 W8 双段拆分——候指认,未指认前按八波派发。
>
> 输入正本不变:`docs/develop/sr_od/application/currency_war/game_state/retirement.md`(13 流处置表/11 消费面清单——
> 其逐流处置与消费面清册继续有效;影子期/M1-M5 排期/前置六条按本裁定重构)+
> `docs/develop/sr_od/application/currency_war/decisions/0630-unified-state-journal.md`(含修订节;其决策 6「影子双写」
> 被本裁定推翻,需随实施批补裁定 ADR)+ 派生规则单一源判定方案 R5。
> 本批只读盘点+写规划,零代码/零配置改动。清点树 = 2026-09-11 工作树;口径 = 全仓 `*.py` 正则出现次数。

**直迁五原则**(用户裁定,规划全篇据此):
1. 旧 12 流 = **删除代码**(不是停写观察);
2. GameState 本体(旧策略侧快照容器)= 消费面迁完**即删**;
3. journal **无条件常开**——无 state_journal flag、无装配段武装点(该武装 hunk 不应用,销案);
4. retirement.md 影子期/M1-M5 排期/前置六条(黑窗/归档观察窗等)按直迁重构;
5. 验证职责 = **测试锁族 + 落地审 + 实机窗口直接暴露**(替代影子并行对账);风险立场已由用户接受:
   直接暴露优于双源并行。

**术语速查**:旧 12 流 = 现役流程侧遥测 12 条独立 JSONL 流(decisions/outcomes/exogenous/
spend_ledger/shop_snapshots/cw4_counters/defect_ledger/op_journal/exec_events/invest_cards/
obs_conflicts/runs;补遗第 13 条 board_state_archive)。统一 state(GameState)= 新容器,文档名
GameState、代码类名 **BoardState**(`kernel/cw_board_state.py:1096`)。旧 GameState = 策略侧 35 字段
局面快照类(`kernel/cw_state.py:167`)。**删除面** = 一波中物理删除的代码(类/函数/分支/配置键)。
**先接后删 / 先迁后删** = 删除波顺序纪律:替代载体先落地并验证,再删被替代代码。

---

## 1. 消费面盘点(数字沿用 v1 清点,迁移方式按直迁改写)

### 1.1 现状基线

已落库(reviews/ 下各有落地审 accept):R1 记录机制(写入口+渠道签名+版本 id+journal 自足快照流水+
**影子装配(缺省关)+D1 写入纪律锁**——前半保留、加粗部分按裁定转删除对象)/R1.1 守卫族扩员/
R2 receipts 回执域+动作写点+D2/R1.2 派生规则②③腿+类型派生/R3.1+R3.2 判读面迁移(journal_query
新读面+CLI `--source journal`+装配器 v12+宽容消费契约单一源)/R4 决策行 state_ref=`{run_id}#{v}`
版本钉(现行行面钉字段=state_ref 单字段,原过渡钉面标记 pin_scope 已退役删除——候裁 10
终裁 C 案,历史档案判读知识见 schema 正本 §8-2)/投影载体 `cw_bs_view.py`(BoardState 主值+
未建模域帧透传→GameState 形状,41 处调用点)。

直迁口径下的缺口清单(=各波删除/新建对象的底册):
1. **match_final 局终域未实现**(src 零命中)——runs 收编、哨兵断流探测、终局防重、Δ池再生触发
   四件事的共同前置载体;
2. **obs_event 登记面未接线**(API 在位 R1;生产调用仅 1 处 `cw_board_state.py:1834`;
   obs_conflicts 收编映射未做)——删除 obs_conflicts 写面的硬前置;
3. **legacy 合成签名未退役**(kernel 7 处合成点 `cw_board_state.py:1435-1579`);
4. **applied-gate 族未迁**(读 action_log 末条 `result=='applied'`:`cw_evolution.py:1430-1507`、
   sim 引擎 2 处、cw_bench_equips 申报面)——删除 GameState 前必须迁;
5. **cw4 逐 key 审计清单未产出**;
6. **哨兵 3 脚本尾读旧流**(cw_sentinel/cw_runs_gap/cw_early_stop,真源 `skills/sr-od-currency-war-dev/scripts/`);
7. **透传域未建模**(`cw_bs_view.py` 模块头申报清单:hp 门后值/bench/deployed/deploy_cap/
   plane_bosses/enemy_affixes/active_env/equips/shop/refresh_probs/board_next_tier)——
   直迁下建模批**进关键路径**(影子口径下可候批,直迁下 GameState 删除的唯一堵点);
8. **ExpectedState/ExpectedEntry 与 BoardState expect/confirm 双容器并行**(`cw_expected_state.py`);
9. **双 ShopCard 并存**(`cw_state.py:110` 旧容器版 vs `cw_board_state.py:459` 统一容器版)——类型去重挂建模波;
10. **cw_state.py 是共享词汇库非纯 GameState 本体**(~40 个导出符号全仓引用:BenchChar/动作类
    LevelUp·SellDeployed·SwapDeploy·CompTransaction/常量 BENCH_CAPACITY·DEPLOYED_CAPACITY·
    XP_*/MatchOutcome/snapshot_copy/deployed_place/sell_refund 等,127 处 import)——
    **删除 = 切割非整文件删**,残余类型居所挂候裁 9。

### 1.2 GameState 消费点分桶(src 合计 **456 处/67 文件**;测试仓另 498 处)

| 桶 | 处数 | 文件数 | 代表文件(处数) | 直迁方式(波) |
|---|---|---|---|---|
| 决策 | **344** | 41 | cw_intention 44 / cw_evolution 31 / cw_economy 27 / cw_comps 19 / mandate_v1\mandate 18 / flow 17 / cw_state(本体)17 | **读口直连统一容器**:决策函数签名与字段读改切统一容器(W6);投影 `cw_bs_view.py` 退役删除;`GameState` 类型引用全量消失 |
| 执行 | 57 | 13 | obs\cw_observation 12(read_game_state 填充端)/ cw_op_buy_cards 9 / cw_screen_prep 8 | **喂入链改造**:read_game_state 保留为观察函数,产出直接经统一写入口 observe;3 个 `session.last_state` 写点(`cw_screen_prep.py:563/787`、`cw_op_buy_cards.py:781`)删除(W6) |
| 判读 | 21 | 6 | telemetry\recorder 9 / schema 6 | **旧流序列化面删除**(W7);决策行 state_ref 落钉保留(不涉旧类型) |
| sim | 27 | 6 | engine_p1 10 / cw_replay 6 / runner 5 / engine_p2 4 | **内部模型切统一容器**:引擎真值直写统一容器,decide 同签名消费(W6);`synthesize_from_game_state` 桥反转为直写喂入口;旧格式回放重建(`cw_replay.py:56`)随删 |
| 装配 | 7 | 1 | cw_game_ports 7(端口协议注解) | 注解跟随切统一容器(W6) |
| GUI | 0 | 0 | —(gui 与 one_dragon_qt 全量零命中) | 不适用 |
| 测试仓 | 498 | — | | 锁随各波重构(锁红≠改动错:被钉语义被用户裁定取代的,先重推锁语义再改,禁机械跟绿) |

**与旧口径 521 对账**:未附统计口径与树时点,按现树不可复现(现口径 src 456 处/452 行);
本规划以现值为准,排期依据是桶间分布与缺口清单,非总数。

### 1.3 旧 12 流引用分布(删除波影响面)

src **461 处/62 文件**:判读 225(query 53/match_archive 49/recorder 27/defects 16/schema 19/cli 14…)、
执行 83(cw_loop 31/cw_screen_prep 12/cw_op_deploy 12…)、决策 75(mandate_v1\entry 21/mandate 10…)、
sim 69(engine_p1 20/ledger_hooks 17…)、装配 3、数据/序列化旁支 6。**写点**集中在 recorder.py+
cw_loop.py+零散 ops(=W7 删除面);**读点**在判读 CLI/装配器/sim 账本/哨兵/运行时内部
(=W3/W4 切换+删除面)。obs_conflicts 写面为唯一汇点形态(`kernel/cw_observe.py:161 obs_conflict()`,
截图节流+告警门+defect 旁路都在汇点内;field 键封闭枚举已有 = `telemetry/defects.py:52`)。

---

## 2. 迁移波次(八波,依赖序;每波=范围+删除面+进入门+删除后验证)

验证三元组(每波同构,下表只列差异项):**①测试锁族**(新增/重构锁,交付清单点名)
**②落地审**(独立干净上下文 reviewer,逐 hunk+亲跑)**③实机窗口**(直接暴露:哨兵武装前置,
≥1 完整局,判读按 telemetry-reading 流程;具体局数候编排者,建议删除波 ≥2 局)。

| 波 | 范围(新建/改造) | 删除面 | 进入门 | 删除后验证(差异项) |
|---|---|---|---|---|
| **W1 journal 常开化+观察接线收尾** | ①journal 无条件装配(match/app 初始化单点),config `state_journal` 开关删除、`currency_war_app.py:96-101` 条件武装销案、`currency_war_config.py:110/139-140` 持久键删除;②obs_event 登记面收编:obs_conflict() 汇点转 note_obs_event(行结构/截图节流/告警门原样;键封闭清单以 defects.py:52 枚举为底补全调用点);③显式签名铺满+kernel 7 处 legacy 合成点退役;④kind_inherited 分支保留锁;⑤battle_done 新行(节点推进写入行带语义,替 `cw_screen_battle_wait.py:365-368` 旧写的「接」半);⑥影子闸分支逐点核(装配常真后删或折叠) | `state_journal` 配置键+装配条件武装 hunk+影子闸条件分支+legacy 合成签名路径;开关两态逐位锁重构为常开锁(锁语义重推申报) | 无(首波) | 常开锁(任意局无条件产 journal);**首局即三口径实测**(单行写 p50/p99、备战链增量、单局体积——无影子缓冲,超预期=写放大拖慢对局,flush 阈值常量可调);D1/D2 锁绿;legacy 行=0 锁;obs_event 封闭集锁;旧读端零行为锁;ADR 义务=影子双写推翻裁定入档 |
| **W2 局终域+runs/board_state_archive 收编** | match_final 局终域落码(一段终态一行,恢复局跨段多行);runs 字段收编(局终收口一行;gold 轨迹从流水派生;comps/pivot 派生列前置=决策行已备);断流兜底改启动扫描补写行(note=recovered 显影);board_state_archive 逐能力归宿(bs_prov 注记已有/bs_pending 挂起摘要/局终速查→match_final);候裁 1-4 定谳落地 | 无(本波纯新建+替换准备;被替代码随 W7 删) | W1 | 一段一行/恢复局多行走查锁;补写行 note=recovered 显影锁;判定方案走查集不受影响;实机窗口:局终域行核对 |
| **W3 判读/哨兵/运行时切新账+删旧读面** | 哨兵 3 脚本尾读改 journal(runs 断流探测→局终域行断流探测);运行时内部旧流读面全量清点切换(cw_loop 心跳已版本 id 核验/summary 兜底/Δ池再生触发/终局防重挂局终域行;含 cw_screen_prep 的 spend 对账读面等,以批首 grep 清点为准);寿命契约装配端(run 段整体滚动清理+archived_out 显影+保留窗) | CLI `--source` 参数+query.py 旧视图族+cli 旧路由+match_archive `_SLICE_FILES` 旧流键+哨兵旧流读面;离线考古工具面(tools/cw proofs、replay_to_md、cw_node_validate、cw_divergence_stats)随删或保留只读考古=候裁 6 | W2 | 旧读面零引用 grep 锁;旧档案 v11/v12 装配回归锁(缺流键容忍,宽容契约既有);哨兵演练锁(合成账本);实机窗口:哨兵武装值守 1 局+CLI 走查 |
| **W4 cw4 审计+键收编+流删** | ①逐 key 审计(键级三分:游戏效果键→效果域/策略行为键→决策行/无消费键删;判定面四查=实机判读/sim 红则判据/轮差分/预注册披露);②键收编落码(效果键→效果域 inventory 写点、策略键→决策行字段、无消费键删分键代码);③流删:cw_loop `_record_cw4_counters_snapshot` 写点+match_archive `COUNTERS_FILE`+cli cw4 视图 | cw4_counters.jsonl 全链(写点/装配键/视图)+无消费键分键代码 | 审计部分无门可先行(与 W1-W3 并行);键收编落码候效果域设计件(候裁 8) | 键全集封闭性锁(写点全集对齐,禁凭概念断格);效果域写点经 inventory 方法域(D1 锚);落地审;实机窗口:判读面计数可见性抽查 |
| **W5 透传域建模收编** | `cw_bs_view.py` 透传清单逐域建模入统一容器:bench/deployed(席位模型)、deploy_cap、shop(牌面 payload)、plane_bosses、enemy_affixes、active_env、equips、refresh_probs、board_next_tier(派生);**hp 专项**:容器存门前真值,新鲜度/门控施门迁消费侧(session 政策语义保留,记录/消费分离不变);类型去重(双 ShopCard 归一;BenchChar 居所定谳) | 旧透传分支(投影内的 frame 透传段随投影整体退役挂 W6;本波删除面=各域的旧「不入容器」豁免申报与双类型) | W1(写入面稳定);候裁 5(ExpectedState 归一方案)先行 | 逐域行为锁(值源切换逐位等价:回放语料对拍);hp 门重构专项对拍(血线决策语义,门后值=门前真值+消费侧施门的等价证明);D1 锁扩面(新域写点全走写入口);落地审;实机窗口:1 局备战/商店/结算帧字段核对 |
| **W6 决策面切统一容器(消费迁移完成波)** | 生产决策面签名与字段读切换(kernel 20 文件+strategies/impl mandate_v1+decision_assembly+cw_game_ports,建议包内三段串行:kernel→strategies→sim);sim 引擎内部模型切统一容器(engine_p1/engine_p2 真值直写,`synthesize_from_game_state` 反转为直写喂入口,旧格式回放重建 `cw_replay.py:56` 切新账);applied-gate 族改观察侧 reconcile(发射行 receipts+后续快照对比;`cw_reconcile.py` 守卫+留证骨架复用);Δ池语料源切 journal(再生管线转 journal 行;既有 META 内嵌池沿用);last_state 链改统一容器喂入(read_game_state 产出直 observe);投影 `cw_bs_view.py` 退役;ExpectedState 归一落地 | `GameState` 类型在决策/执行/sim/装配桶的全部引用(456 处的主体)、投影模块、last_state 三写点、action_log applied 消费路径、旧格式 sim 回放重建 | W5(建模绿)+W4(键新载体绿);候裁 5 定谳 | **零引用锁(src+测试仓 GameState=0)**;决策行为锁族全绿(mandate_v1/intention/economy 既有锁);sim 全量锁+零漂移锚(test_cw_sim_fidelity 指纹);applied-gate reconcile 双报对拍窗;回放语料逐位等价;落地审;实机窗口:≥2 完整局判读(决策语义直接暴露) |
| **W7 旧 12 流写面删除** | 处置表定案流写点全部下线(recorder 旧流方法+cw_loop/ops 散布写点+battle_done 旧写+board_state_archive 写点+sim/ledger_hooks runs 兜底旧码);归档只读声明(数据文件不删不写,裸读考古);**retirement.md 影子框架重构文档批**(排期/前置六条按本规划改版)+ADR 同步 | 旧 12 流+补遗共 13 条流的**全部写面代码**(recorder 写方法、写点调用、recovered 兜底、battle_done 旧写、cw4 剩余写点);防双计无对象(单源后自然消失,勿实现) | W3+W4+W6 验收绿;候裁 2(invest_cards)定谳——**删除前定谳硬门**(效果原文回流断供不可逆) | 旧流文件名全仓零写点 grep 锁(先例 ADR-0571/D1 手法);全量测试绿;落地审;实机窗口:≥2 完整局(单源直迁后的第一手验证,判读全走新账) |
| **W8 GameState 本体删除+正名** | ①`cw_state.py` **切割删除**:GameState 数据类+tracking/mutation 方法+last_state 链残留删除;共享词汇类型(BenchChar/动作类/常量/MatchOutcome 等)按候裁 9 定居所;②正名 BoardState→GameState(类名;模块文件名候裁 7);D1 锁 `_BOARD_STATE_MODULE` 常量+文档锚更新;pin_scope 零写入 grep 核对(候裁 10 终裁 C 案=字段整体退役删除,T-99 已执行,W8 仅存此核对) | GameState 数据类本体、cw_state.py 中其专属方法、(若裁正名)`cw_board_state.py` 旧类名/模块名 | W7 验收绿+全仓 GameState 零引用(W6 锁持续绿) | 零引用锁持续绿;全量测试绿;grep 锁全绿(D1/停写/读面);CLI/装配回归;落地审;实机窗口:1 完整局(正名后回归) |

### 删除时点论证(原「停写时点」)

旧流写面删除钉 **W7**,本体删除+正名钉 **W8**。波序=先接后删/先迁后删的展开:
①obs_event 接线(W1)先于 obs_conflicts 写面删除(W7)——留证义务不蒸发;
②判读/哨兵/运行时读面(W3)、cw4 载体(W4)、决策消费面(W6)先切,写面(W7)后删——
删除瞬间无在仓读者断供;③applied-gate(W6)先迁,本体(W8)后删——决策成败消费面不断粮;
④透传域建模(W5)先于决策切换(W6)——消费者有字段可读;⑤recorder 旧流序列化消费旧类型,
故写面删除(W7)先于本体删除(W8)。

### 波间并行度

**主账本时代序(修正令②)**:W3 完成后 journal 即为唯一被读账本(旧读面已随 W3 删除),
旧流仅余无读者的写面存活至 W7 物理删除——此后一切判读/哨兵值守直接暴露于新账,无过渡双读态。
W4 审计并行位保持。并行约束:W4 的审计段与 W1-W3 并行先行;W2/W3 串行(载体依赖);W5 可与
W3/W4 并行(不同文件域:W5 在 kernel 容器与 obs 喂入面,W3 在 telemetry/skills);W6 大波建议
包内三段串行派发;W7/W8 串行收尾。同一时刻最多两波在飞(文件域互斥约束,先例=retirement.md
「M2/M3 可并行,不同文件域」)。

---

## 3. GameState 改名时机

**结论:正名(BoardState→GameState)与本体删除同收尾波(W8),本体删除段在前、正名段在后。**

与 v1 的差异:v1 需「腾名 GameStateView」中间态(投影形状存活);直迁口径下本体即删,
**类名随删除直接释放**,无腾名波。论证三条:
1. **删除释放名字**:GameState 类删除(W8 前段)后名字空闲,正名(W8 后段)无冲突——
   v1 的腾名→停写→正名三段收敛为删除→正名两段,同波双段同文件域(cw_state.py 切割+
   cw_board_state.py 改名),审查面连续。
2. **正名仍在最后**:W1-W7 的任务书/验收判据/测试锁/落地审锚全部引用 BoardState 符号,
   提前改名=对账锚失效税;且正名是机械大 diff(src 153 处/32 文件+测试仓 187 处+文档锚),
   与删除段的审查混装会污染逐 hunk 归属。同波内保持「先删后名」两段各自可验。
3. **与 ADR-0630 改名计划锚兼容**:「迁移完之后将 BoardState 改名成 GameState」(后果节逐字锚)——
   「迁移完」=W7 验收绿(消费迁移+旧流删除完成),W8 即执行。

---

## 4. 退役前置六条重构(retirement.md §6 在直迁口径下的形态)

| # | 原条 | 直迁口径下形态 | 落点 |
|---|---|---|---|
| 1 | 黑窗消解三条件 | **消解**(无双写窗即无黑窗概念)。其保护意图(决策源/sim/判读三面不悬空)转为**波序门**:W7 删写面前 W3-W5 读面已切且新载体在产;W8 删本体前 W6 消费面已切 | 波表进入门列 |
| 2 | obs_event 登记面收编完成 | **保留,升级为硬门**:obs_conflicts 写面删除前收编必须已接(W1),否则拒读留证蒸发 | W1 交付,W7 门 |
| 3 | 宽容契约到装配端 | **已闭环**(R3.2 accept:read_journal_stats 单一源+三层计数);常开化后即刻全量生效,不再候语料 | 无新义务 |
| 4 | 决策数据源不抽空 | **保留**:GameState 本体删除前 applied-gate 族必须已迁观察侧 reconcile | W6 交付,W8 门 |
| 5 | 寿命契约耦合 | **保留**(辖 journal/state_ref 存续):滚动清理以 run 段为整体单元、archived_out 显影、保留窗=跨期语料窗;清理策略随 W1 常开后真实数据积累定,无观察窗计时 | W3 装配端 |
| 6 | 归档只读+观察窗 | **观察窗流程消解**;归档数据只读保留为事实约束(旧档案不删不写,可裸读考古);实机窗口(验证性质)替代观察窗(过渡性质) | W7 声明 |

---

## 5. 风险清单(逐项挂波)

| # | 风险 | 机制 | 缓解 | 挂波 |
|---|---|---|---|---|
| 1 | **无影子缓冲,迁移错误直接暴露实机**(用户已接受立场,规划如实承接) | 直迁期间无双源对账网,错误直达实机 | 三元组验证每波不减(锁族+落地审+实机窗口);每波删除面 revert 即恢复(删除是代码操作,可逆);波间不并行超约束 | 全波 |
| 2 | journal 常开化首局即全量生效 | 体积预估 15-45MB/局、写放大直接上进实机路径;无影子期缓冲 | W1 实测门(三口径,超预期即调 flush 阈值常量);常开锁+D1 锁;异常=停局排查(实机卡住=现场修复纪律) | W1 |
| 3 | 透传域建模缺口→决策断粮 | W6 类型切换后,漏建模字段以缺省值/异常暴露,决策静默漂移最危险 | W5 逐域申报清单+回放语料逐位对拍;W6 决策行为锁族全绿门;实机 ≥2 局判读 | W5/W6 |
| 4 | hp 门语义重构漂移 | 门后消费值→门前真值+消费侧施门,施门语义错=血线决策漂移 | W5 hp 专项对拍(等价证明:门参数同源)+posture_release 假帧守卫既有锁 | W5 |
| 5 | applied-gate 语义差 | 发射行+快照对比 与 action_log 末条 在「发射后未落地」窗判定不同源 | reconcile 双报对拍窗(两口径并行一期,diff 申报后才切) | W6 |
| 6 | cw4 键审计遗漏→指标静默消失 | 三分漏键=判读/sim 判据面缺列 | 键全集封闭性锁;四查判定面走查;无消费键删除逐键申报 | W4 |
| 7 | Δ池语料源切换失真 | sim fidelity 语料再生从 decisions.jsonl 转 journal,行语义差异入池 | 既有 META 内嵌池沿用;指纹/digest 锚(test_cw_sim_fidelity);再生后抽样对拍 | W6 |
| 8 | 判读考古断供 | 旧格式读面删除后,存量语料专用工具失效 | 候裁 6(随删 vs 保留只读考古);原始 JSONL 永远可裸读 | W3 |
| 9 | 已删代码复活 | 后续开发重新引入旧流写点/GameState 构造 | 每删除波交付零引用 grep 锁(旧流文件名/GameState 符号),锁进全量集 | W6/W7/W8 |
| 10 | invest_cards 效果原文不可逆断供 | 流删后候选卡效果原文无回流(注册表 ground truth 回流用途不变,但逐局原文语料断) | 候裁 2 定谳为 W7 硬门;倾向=strategy_offer 域建模(随 W5 payload 建模同批) | W5/W7 |
| 11 | 知识双源漂移 | 影子框架推翻后,ADR-0630 决策 6/retirement.md 旧文与事实相抵 | ADR 义务:影子推翻裁定随 W1 入档;retirement.md 重构随 W7;改版前旧文以本规划为裁决口径 | W1/W7 |

---

## 6. 工作包切分(8 包,与波一一对应,按序派发)

| 包 | =波 | 文件面 | 验证 | 预计规模 |
|---|---|---|---|---|
| **P1 常开化+观察接线批** | W1 | currency_war_config.py、currency_war_app.py、kernel/cw_state_journal.py(无条件装配)、kernel/cw_observe.py(汇点转 obs_event)、kernel/cw_board_state.py(合成点退役)、cw_screen_battle_wait.py、telemetry/defects.py;测试锁重构(开关两态锁→常开锁/完备率/封闭集) | §2 W1 列 | **M**(1-2 天;含 ADR 义务) |
| **P2 局终域+收编定谳批** | W2 | kernel/cw_board_state.py(match_final 域)、operations/cw_loop.py(局终收口/启动扫描补写)、telemetry/recorder.py(recovered 源)、sim/ledger_hooks.py(替换准备);候裁 1-4 随裁随落 | §2 W2 列 | **L**(设计+落码;可拆设计半批+实施半批) |
| **P3 判读/哨兵/运行时切换批** | W3 | skills/sr-od-currency-war-dev/scripts/ 三件、operations/cw_loop.py(触发面)、telemetry/query.py+cli.py+match_archive.py(删旧读面)、寿命契约面;**跨 skill scripts 与 src 双文件域,派单声明**;候裁 6 随裁 | §2 W3 列 | **M** |
| **P4 cw4 审计+键收编+流删批** | W4 | 审计(只读产出)→strategies/kernel 分键写点→operations/cw_loop.py+telemetry/match_archive.py+cli.py(流删);候裁 8 前置 | §2 W4 列 | **M**(审计段可提前独立派) |
| **P5 透传域建模批** | W5 | kernel/cw_board_state.py(新域)、obs/ 喂入面(cw_observation/cw_identity_obs)、kernel/cw_effect_inventory.py(效果键落域)、双 ShopCard 去重;候裁 2/5 随裁 | §2 W5 列 | **L**(建模密集;hp 专项单列验收) |
| **P6 决策面切换批(最大波)** | W6 | kernel 决策簇→strategies/impl(mandate_v1 全簇)→sim(engine_p1/engine_p2/cw_replay/runner)三段串行;decision_assembly/cw_game_ports;kernel/cw_bs_view.py 删除;kernel/cw_evolution.py(applied-gate);Δ池再生管线;last_state 链(cw_screen_prep/cw_op_buy_cards);ExpectedState 归一;测试仓锁大面重构 | §2 W6 列;零引用锁为本包核心交付 | **XL**(建议包内三段各设检查点交付;1-2 worker 串行或分派) |
| **P7 旧流写面删除批** | W7 | telemetry/recorder.py(旧流方法)、operations/cw_loop.py 与 ops 散布写点、cw_screen_battle_wait.py(旧 battle_done)、sim/ledger_hooks.py(旧兜底)、cw_loop archive_snapshot(board_state_archive);retirement.md 重构文档批+ADR;停写零引用锁 | §2 W7 列 | **M**(删除面广但机械;进入门=三元组合门) |
| **P8 本体删除+正名批** | W8 | kernel/cw_state.py(切割)、kernel/cw_board_state.py→正名(候裁 7)、全仓 import 面+测试仓、D1 锁常量、game_state 目录命名注;候裁 9/10 | §2 W8 列 | **M**(机械为主;两段各自可验) |

---

## 7. 候编排者裁决清单

1. **outcomes 归宿两案**:结算真值正本扩 Settlement vs 流水行 extra 槽(P2 前置;伤害三分量不入 state 两案一致)。
2. **invest_cards 效果原文回流**:strategy_offer 域建模(倾向,随 P5)vs 接受断供——**P7 删流硬门**。
3. **cw_anchor 四 carrier_kind 归宿**(P2)。
4. **defect_ledger 案 A/案 B + op_journal 同批裁决**:保留专用流在直迁口径下仍合法(保留=不删,
   不入 P7 删除面);裁保留则 refs 迁 journal 键+寿命联动挂 P3——(P2 定谳)。
5. **ExpectedState 归一方案**:执行面写点迁 BoardState expect/confirm vs 申报保留执行域机制
   (P5/P6 前置)。
6. **离线考古工具面**(tools/cw proofs、replay_to_md、cw_node_validate、cw_divergence_stats):
   随删(裸 JSONL 可考古)vs 保留只读考古(禁 import 运行时写面)——(P3)。
7. **模块文件名随正名改**(cw_board_state.py→cw_game_state.py):建议改,代价=D1 锁常量+32 导入面
   +文档路径,纯机械——(P8)。
8. **效果域内容语义设计件**:cw4 效果键入域归宿依赖,README §5 记「候讨论成文」——
   P4 前必须成文或显式降级「键值原样入效果域」。
9. **cw_state.py 残余词汇类型居所**(P8 切割前置):留原文件(文件更名,如 cw_vocab.py)vs 迁居
   kernel 既有模块;含双 ShopCard 归一后唯一居所(与 P5 衔接)。
10. **pin_scope='board_state' 标记值**随正名是否改写(数据值兼容 vs 断代)——(P8,低)。
    **已收口**:候裁 10 终裁 C 案=字段整体退役删除,T-99 已执行,本条不再有对象;
    执行规格与判读知识归宿见定谳记录
    `docs/develop/sr_od/application/currency_war/changes/2026-09-11-unified-state/定谳记录-候裁7910.md`。

## 8. 销案清单(本裁定明废,实施批禁再引用)

- `state_journal` 配置开关 + currency_war_app 装配段条件武装 hunk(P1 删除);
- 影子期/影子对拍验收门(对拍语义改为回放语料对拍+实机窗口);
- 观察窗(≥2 周)流程;M1-M5 排期框架(重构为八波);防双计装配器切片消解(单源后无对象);
- v1 规划的腾名 GameStateView 中间态(本体直接删除,名随删除释放)。

## 9. 边界与不在本批

链观察 B-1..B-4(独立切分,chain_diff 登记挂 P1/P2);效果域实施中「效果语义设计件」正文
(候裁 8 的成文属设计批,键落域落码属 P4/P5);旧档案数据文件(只读事实,无清理批——
寿命契约滚动清理策略候 P3 后按数据积累定)。
