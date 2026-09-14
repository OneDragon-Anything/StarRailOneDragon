# 遥测判读方法论(看什么/怎么读/覆盖与缺口)

> 实机局数据判读的细则。读者 = 智能体;适用于:局后判读、跨局对照、异常定位。验收口径(什么算"打得好")的单一源 = 当期进度账本目标行判据;sim 批侧的数据判读见 sim-testing.md。

## 查询工具(遥测 CLI)

```
$env:PYTHONPATH='src'; uv run python -m sr_od.application.currency_war.telemetry.cli query --recent N [--run ID] --view rounds|gold|hp|events|snapshot|final|all
```

- **模块入口必须带 `PYTHONPATH=src` 前缀**(上式已含;裸 `-m` 与 `--env-file .env` 都报 ModuleNotFoundError——`.env` 不放 PYTHONPATH)。仓内无独立 `cw_telemetry` 可执行命令,help 的 prog 名显示为 cw_telemetry 而已。
- **按局档案(跨 run 段免拼段)**:正常局局终自动装配;`--match <game_id>` 直读单局档案(`--recent` 读索引;崩溃局补装配 `assemble --game <game_id>`)。

- rounds=逐轮表(按节点分段);gold=金账行间差分;hp=hp 链;events=观察事件行显影;snapshot=末行快照摘要;final=局终行(match_final)。旧视图族(supply/anomalies/economy 等)已随旧流拆除,深维度按「新复盘需求=新视图」纪律按行差分直读。
- **生产局秒级自检**:旧 `checks` 子命令已随旧流退役——生产自检走哨兵三件(journal 面;武装口径见 [runtime-ops.md](runtime-ops.md)「哨兵脚本组」);sim 批次侧等价物 = simulate_p1_batch 默认内嵌的 checks_violations(sim 检查器保留)。
- 日志跨 run 累积(append+轮转,重启不销毁证据):查旧局按时间窗 grep;需关注行检索 `grep [cw!]`;格式标准单一源在 strategy/05 §6。

## 核心原则(用户定调)

1. **观察的数据都是对决策有用的**——GameState 的每个字段都对应一个决策消费点;遥测要全记,复盘要全面(羁绊/角色/装备/站位/经验/商店/投资策略环境都看),不是只看最显眼的维度。
2. **采集的基本都有用,别被视图边界限制**:decisions.jsonl 的 state 是全量序列化;视图没显示的维度直查 jsonl(join 键 run_id+round_num)。视图覆盖是渐进的,判读面不能跟着视图走。
3. **保真位先行**:hp_readable/gold_readable/board_readable=False 的轮,数值是 miss 兜底不是真值——先滤假数据再下结论。
4. **单局归因是判读大忌**:结论要跨局对照(近 N 局同维并列),单局相关≠因果。

## 观察面全量清单( GameState 32 字段 → 复盘问题)

按判读主题分组;「视图」列 = 现成查询覆盖(无 = 直查 jsonl);「空」= 采集缺口(字段恒空,见文末):

### 阵容质量(三维,缺一即盲判)
| 字段 | 视图 | 复盘问题 |
|---|---|---|
| board | 档案 rounds 行(board 键) | 羁绊档位构成;配方成型进度 |
| board_next_tier | 无 | 距下档几人(差一人没凑上=供给问题) |
| deployed(char_id/star/equips/position_pref) | 档案 rounds 行(deployed 键:名+★+装备+站位) | 核心在场吗(空壳档位);星级演进(核心 2★ 何时到);装备归属(carry 拿 key_equips 了吗/乱穿);**站位**(前排数 vs 设计) |
| bench | 无(仅 outcome bench_count) | bench 囤什么(压缩件/final 囤件/滞留件);席满管理 |
| equips(owned) | 档案 rounds 行(equips 键) | 装备滞留/合成材料囤积 |
| plane_bosses | **空** | boss 克制兑现(counter 线该避没避) |
| enemy_affixes | **空** | 词条 counter 兑现 |

### 经济与节奏
| 字段 | 视图 | 复盘问题 |
|---|---|---|
| gold | rounds/gold | 轨迹/滞留轮/息核对 |
| level | rounds(部分) | 升级节奏 vs 5→7→9 基线;错过窗口 |
| xp_progress | 无 | 经验点了几下/何时升级;半吊子点经验(金尽未升级) |
| level_up_cost / shop_refresh_cost | 无 | 折扣卡生效核对 |
| streak | **空**(state)·outcomes 有 | 连胜-保息抉择是否如设计触发 |
| bench_full_flag | **空** | 席满轮与腾席动作对齐 |

### 供给与选择
| 字段 | 视图 | 复盘问题 |
|---|---|---|
| shop | 档案 rounds 行(shop_snapshots/actions 键) | 全波牌面 vs 购买:该买没买(错过供给)/不该买买(散件固化) |
| refresh_probs | 无(7/39 有数据) | 轮岗概率条(环境效果兑现) |
| shop_locked | **空** | 锁店策略维持 |
| active_env | **空**(仅选卡时) | 环境选择与路线匹配 |
| active_strategies | trace 顶层 | 持卡演进(选了什么/何时;台账回放) |
| megastar_char / partner_char | **空** | 巨星/伙伴选择与 comp 匹配 |

### 局环境与难度
| 字段 | 视图 | 复盘问题 |
|---|---|---|
| node_type | hp | 节点类型×掉血(P1 遭遇凶于 boss?) |
| enemy_difficulty | 无(39/39 有数据) | 难度曲线实测;降难度卡生效 |
| hp/hp_readable | rounds/hp | 轨迹+保真 |
| plane_modifiers | **空** | 位面修正(战个痛快)对掉血调制 |
| selected_difficulty | runs 概览 | 职级对照 |
| front_max/back_max | 无 | 槽位异常(cap 变体检出) |
| focus_factions | 无 | focus 漂移(churn 源) |

### 决策迹(trace 顶层,非 state)
target_comp(换线序列/churn)、candidate_scores、eval_breakdown、actions、sess_*(session 态快照)、v2_mode/locked_line/bridge(策略 v2)、dp_posture(影子姿态)——AB 对拍与「为什么这么决策」的回放源。

## hp 真值链判读(schema 9 起)

> hp 真值链 = 档案里解释「本局 HP 从开局到终值怎么一步步变的」的派生数据:rounds 逐轮 hp/hp_delta、loss_nodes(掉血条目表)、resume_reconciliation(恢复态对账列)、hp_events、hp_pay_defects。schema 9起,链的步进游标(装配时维护的「已解释到的当前 HP 值」,按时间序逐行推进)只由三类行推进:可信结算行(结算屏真读,hp_confidence≥0.9)、hp_pay 事件行(下文)、终局兜底(下文);补给合成行(补给节点无结算屏、由快照合成的 outcomes 行,详见「已知缺口」)一律不入链。判读 HP 问题先分辨落在哪个成员上。

### hp_pay 事件行与 hp_events 列

- **定义**:hp_pay = 血购(用 HP 代替金币买经验;现版本唯一来源 = 投资卡『奋斗协议』xp_buy_hp_cost=6)每击一次落一条的执行回执行,kind='hp_pay',原写在 exogenous.jsonl(外生事件流:决策之外的既成事实记录)——**写端已随旧流收编退役,新局零产出,仅存量档案可见**(装配读侧宽容缺键)。查询:档案 JSON 直读顶层 hp_events 显影列/hp_pay_defects 对账列(判读 CLI 无 exogenous 视图,已随旧视图族拆除)。
- **粒度口径:行数 = 血购击数,总量 = Σhp_delta**。店通道单动作 1 行、备战通道连点循环每击 1 行;数击数、核对血购总量都用本口径。行内字段:hp_delta=−单次代价、currency='hp'、mode=生效卡名、basis='modeled'(按注册表建模的期望值,非实读);**行内不带 state 快照**——支付时点 HP HUD 结构性不可见,行里没有支付时点真值,这是设计而非采集缺失。
- **mode 派生口径**:是否出行与 mode 值都和血购判定同源注册表(active_strategies 中 xp_buy_hp_cost>0 的卡,多卡命中取 active 序首个);卡非 active(金本位升级)→ 零行。零行 = 当局没发生建模内血购,不是采集漏。
- **hp_events 列**:档案顶层加法列 = hp_pay 事件行显影;schema 9 前旧档案恒空(采集面修复只及新局,空 ≠ 没血购)。链上事件步只推进游标、不出掉血条目——「一条掉血条目 = 一次掉血结算」的语义不变,血购不冒充战斗掉血,战斗腿数字因此不含血购。
- **遥测禁入决策输入**:hp_pay 行是纯观测追加写,任何决策/跟踪代码禁读它回写 state.hp / session.last_hp_real / 预算门状态(grep 守卫锁钉死, 隔离申报)。判读同理:档案里有 hp_pay ≠ bot 决策时知道血购掉血——决策侧的血购感知走注册表判定,不经遥测。

### hp_pay_defects 列(建模期望账对账缺陷)

- **产生规则**:装配在每个可信结算行处,把「游标(已计入事件推进)」与结算真值比对,偏差≠0 落一行 `{plane, round, expected_hp(游标), actual_hp(结算真值), gap, modeled_paid(自上次结算起事件 Σhp_delta), ts}`;留证不阻塞装配。
- **读法**:有 hp_pay 的局先看本列(空 = 建模与实跑吻合)。gap≠0 = 血购建模代价与实际扣血有出入;污染半径到下一可信结算为止——游标照取结算值自愈,其后战斗腿不受影响。
- **查询面**:hp_events/hp_pay_defects/resume_reconciliation 都是档案顶层列,`--match` 的 CLI 输出不直接打印,判读直读档案 JSON `telemetry/matches/match_<game_id>.json`(固定根 `.debug/currency_war/telemetry/matches/`,2026-09-07 布局裁定)。

### 段界重锚与 rounds 续段首槽(跨段语义,schema 9 变更)

- **机制**:装配走行跨段(及 rounds 链到达续局段首轮)时,以该段恢复帧(续局段恢复后最早被记录的帧;与 resume_reconciliation 同一帧定义)的 HP 读数重锚(游标重置为恢复读数);恢复帧不可锚(缺帧/hp None/readable=False)→ 不锚、跨段携带照旧(诚实退化)。
- **续段首槽 delta 语义变化(读端可见)**:rounds 里续局段第一轮的 hp_delta 从「跨段净额」变「段内变化」。实例:g_20260907_025608 p2r1 从 −43 变 −19——停机间隙的 −24 不再混进战斗腿。跨局对照跨段槽位时数字会变,属修复语义非回归。
- **重锚差显影落点**:停机间隙变化改显影在 resume_reconciliation 对应续段行的扩展字段:`unexplained_delta`(= 恢复帧读数 − 重锚前游标;负 = 停机间隙真掉血)+ `consumed_by_chain=true`(已被链消费,判读勿重复计入)。**不进 loss_nodes**——重锚差是段界间隙变化,不是战斗掉血条目。
- **判读动作**:续段首轮大额掉血先查 resume_reconciliation:有 unexplained_delta = 已段内化,战斗腿自恢复读数起算;无且恢复帧不可锚 = 仍跨段携带,大额含停机间隙,归因先拆开。

### endgame_final 终局兜底条目与 loss_nodes 读法(schema 9 扩展)

- **终局兜底条目(「终局腿」)**:链走完后 result='loss' 且游标≠0 → 在末轮键追加 `{hp:0, delta:−游标, hp_source:'endgame_final', outcome_source:'runs.final_hp', ts:None}`。真值来源 = runs.final_hp=0 的结构保证(败局终值必 0),补出结算链没解释完的剩余掉血。
- **loss_nodes 条目两类**:掉血结算行(hp_source='settlement')与终局兜底(hp_source='endgame_final'),数败场/算总掉血时两类都算。条目的产出路径读 outcome_source 字段。
- **回落路径条目**:某轮无可信结算行入链(如死亡轮 hp_confidence=0)→ 轮槽 hp 真值单步回落出条目,outcome_source 标来源行(如 'loss_page' = 结算屏回读行)。实例:g_20260907_025608 p2r4 死亡条目 delta=−1 即回落路径产出(outcome_source='loss_page');该局游标已到 0,终局兜底被「游标=0 不重复」守卫跳过——不冒领 ≠ 漏记。
- **零终局兜底形态**:win/abandoned 局恒无;游标 None(全程无可锚行)无 delta 可算,诚实跳过。

### schema 9 起旧口径作废(历史读数对照)

- **「−33 双读数」注作废**:schema 8 时代「同档案重装配 −19→−33」的说法建立在合成行鬼值(与真值不符的陈旧快照值)游标上;合成行退链后 −33 不再产生(182456 v9 重装配该战斗腿 = −19,与原 schema 7 读数一致)。
- **跨段净额读数作废**:续段首轮 −43 形态按上节重锚语义读(−19 + unexplained_delta=−24)。
- **历史文档引用以重装配后为准**:存量档案已 auto-rebuild 原地重装配(schema_version=9);旧文档/旧 ADR 引用的上述读数凡与本节冲突,以重装配后档案直读为准(勘误出处 = 档案重装配记录)。

## 判读流程(局后必做)

0. **先取尺子再看数——两种判读两种尺子,别混**:**单局复盘**(打得对不对)的尺子=玩法恒常标准(配方纪律/经济纪律/响应纪律/已证命题,协议=[match-review.md](match-review.md));**验证当期改动(A/B)**的尺子=当期进度账本目标行判据(没写判据=先补写再判读)+ strategy-work「验证」——**HP 从来不是验收指标,拿 HP 当验收=目标函数错**;
1. **局后判读一律档案直读**:`--recent N` 概览(读档案索引)→ `--match <game_id>` 锁定目标局看视图;`--run` 流查询仅局中实时定位用(早停/哨兵/卡死——游戏还在跑,档案未生成)。**结束值以档案为准:决策日志最后一行的血量不是结束值,那之后还打了仗**;
2. **hp 视图**看轨迹(注定不达标的局按早停纪律反思为什么没早停);档案 hp 真值链(hp_pay 事件行/段界重锚/终局兜底)的 schema 9 判读口径见上节;
3. **阵容三维扫一遍**(羁绊档位×角色构成×装备分配):档案 rounds 行直读 `board`/`deployed`/`bench`/`equips` 键(CLI 无独立 tiers 视图,已随旧视图族拆除);
4. **gold 视图**看滞留/收入核对(金账行间差分);**购买对错**直读档案 rounds 行 `shop_snapshots`(全波牌面)+`actions`(实付动作);
5. **events** 视图观察事件行(obs_event)逐条定位根因（定位不了不进下一局）——旧 anomalies 视图已随旧流拆除；冲突/异常证据面 = journal 行型 2 在账直读（obs_conflicts 历史行 = 冻结档案只读，删除波 1 起）；
6. 视图外维度按需取:优先档案 rounds 的字段面(含决策流程明细——pair/意向/姿态,带策略版本戳);仍不够的「为什么/如果」问题走**回放**(用当期代码对档案状态现算,单帧锁同款机制)——不为此读流;
7. 结论:有异常 → 先确定异常来源,再找出治本的修复方案,然后将方案的实施状态记录到进度账本中合适的位置;同一个问题出现两次 → 必须走到治本方案这步,不许再当单局异常放下;单局结论不留;声明数据边界。
8. **局终的深度复盘不在本流程**——实机监控局终派单走 [match-review.md](match-review.md)「单局复盘协议」(干净子 agent,逐节点玩家对拍);本流程管流程卫生与视图判读,协议管「打得对不对」。

## 已知缺口(判读时心里有数)

- **字段可信度分级(历史全面审计)**——可信白名单:outcomes.hp_after(conf≥0.9)/plane/round_num/progress_delta、decisions.actions/target_comp/candidate_scores、shop_snapshots 的 offer 波牌面(gold 除外)、sess_*/v2_* 快照族、obs_conflicts(冻结档案:该流已随删除波 1 停写,白名单仅辖存量档案判读;新局冲突证据 = journal obs_event 行型 2)。**历史脏区(修复前的旧数据)**:node_type 三源混写(英文 token/中文/旧兜底并存,后统一中文)、中止局无 runs 行、refresh 快照 gold 是算的(非真读)、首轮的 node_type 恒「普通战斗」、level 非单调偶发、board_before 是阵营人次非板深(多标签角色重复计)。判读旧局时这些字段降权。
- **phase 字段是两层语义(误判过实盘病理,W688 定性)**:P1 段 phase 恒 unlocked=设计态——P1 的锁产物记在 p1_pair,别拿 phase 判「P1 与配方脱钩」;终局锁相位只对 plane≥2 段有意义。判读锁相关行为先分清问的是哪一层。
- **补给合成行是快照不是事件(schema 9 起退出 hp 真值链)**:source='synthetic_supply' 的行(补给节点无结算屏,由停机前快照合成的 outcomes 行)hp 结构上无新鲜性保证;病灶实证 = 182456 合成行载 45,而帧序上 19 秒前已结算 31(陈旧一整轮战斗的鬼值)。判读先验 = **陈旧直到证伪**:合成行 hp 一律先当陈旧快照,除非有帧序证据证伪;旧档案合成行 conf 可能仍载 1.0(写端诚实性降权只及新局),conf=1.0 不构成可信证据。退链的中间窗口:补给节点后的首个战斗腿可能吸入「补给时点 → 结算时点」的未建模间隙,判读并读该补给行快照值拆账。
- **补给合成行轮归因 +1(登记不修)**:轮号归因(read_phase_round 走缓存)对补给合成行轮可能偏 +1;装配端退链已消除链上危害,归因偏移留判读侧已知缺口——补给轮跨局对照时 ±1 校对轮号。
- **P2 备战轮台账 miss 18/24 已修(写点③ 2026-09-09 后新局生效)**:病灶根因 = 位面节点台账写入端缺位——写点②(投资环境重读)只在开局触发、写点①(位面详情)仅接管局触发,正常局 P2/P3 序列恒无写入者;非识别失败(接管局 P2 反而命中是判别锚)。修复 = 备战帧 heavy 观察按位合并落表,此后 P2/P3 备战帧 `p26_prep_obs.node_type_next` 应逐帧命中;**判读新局 P2 备战轮仍见 miss = 回归信号,先查写点③是否被跳过(clean 备战帧门/变异窗)**;边界:past 位次(已通过节点)读法结构性 None 不回填,查历史轮仍可能 miss(flow 回落维持原退化路径)。存量档案(修复前局)miss 形态永久留存,跨局对照时按钩子部署边界分段。
- **结算 tooltip「长线作战」回血分量已入遥测(新局 outcomes 行 `heal_longline` 键)**:此前「tooltip 两分量幅度 = hp 链差 + 2」系统偏移(T-57 P26 标定批败面 19/20 实证)机制定谳 = 「长线作战」战斗结算回血 +2(口述 + 连胜轨迹双源;败面也 +2 ⇒ 回血非胜局专属,的「胜利」限定被数据收窄,如实申报)。判读口径:hp 链差(净变化)= 掉血两分量(damage_base+damage_unfinished_progress)+ heal_longline,行内三量齐可直接验证;**禁把 +2 抹进对比公式**(回血量以行内现读为准,非恒定承诺);旧档案无此键,偏移验证仅新局可行。
- **零结算段自标识(v11 起,段条目 `settlement_gap` 键)**:键在场 = 本段零结算(决策帧≥1 且结算行=0:备战停滞/出战未成战后被守卫或人工停机),**非遥测丢失,不可离线补行**(真值源=结算屏帧,从未被捕获;decisions 的 hp 是沿用/冻结值非逐轮真值);随行 `claimed_rounds_survived` 取自收口时点 state.round_num,零结算段可带非零冻结值——「claimed=N 且零 outcome 行」曾是误报「结算断流」的形态(实证 g_20260908_165445 续段 run_20260908_210431),与 gap 并读即防。同批分组修正:决策独有段(零结算段)按段首 ts 归**前局**,后继新局入流不再夺段;旧档案 bump 后首次读档自动重装配纠偏。
- **视图缺口**:上表「无」标记——按「新复盘需求=新视图」纪律渐进补,别写一次性脚本。
- **采集缺口→接线状态(历次迭代已补 5 项)**:active_env/plane_bosses/enemy_affixes(read_game_state 尾部 session→state 统一回写,注入点单一、两策略同源)、megastar_char/partner_char(handler 选择时落 session.chosen_*,同处回写)。**仍缺 reader 的 2 项**:plane_modifiers/shop_locked(观察基建未建,非回写问题,记进度账本推进)。streak 一直是接好的(恒 0 是结算真值,非接线缺)。这些维度的复盘暂用 log/结算屏侧数据兜底。

## 判读纪律

- 异常条目当场定位;跨局存活 = 回归在累积。
- 结论声明数据边界(「基于进店帧,refresh 波牌面不可见」这类)。
- 新复盘需求 = 新视图/查询参数(schema 变更查询同步),不是新 py 文件。
- **别为复盘写一次性脚本**——新复盘需求 = 新视图/查询参数;确需脚本用完即删。
- **阵容质量 = 三维**(羁绊档位 × 角色构成 × 装备分配)——只看羁绊 = 空壳盲判(羁绊够但核心不在场/装备乱用都看不见;数据在 state.deployed[].star/equips 里,别被视图边界限制)。
- 改动效果对照:改策略后下一局 `--recent 5` 并列对比(测试绿≠实跑行为对)。
- **sim 批次同法可查**:sim 批判读走 skills 侧 `cw_batch_stats`(sim 自写账本;判读 CLI `--sim-batch` 入口已随旧流退役,journal 侧 sim 视图待统一账迁移后续批补建),详见 [sim-testing.md](sim-testing.md)——本文档案判读手法按各账本面对应成立,生产判读 CLI 不指向 sim 产物目录。
- 判读定位的策略行为病**必须固化 sim**(检查项/单帧锁),闭环纪律见 [autonomous-loop.md](autonomous-loop.md) 实机监控第 4 步;需要锁死的确定行为固化成单帧锁,见 [strategy-work.md](strategy-work.md)「单帧锁」。

## 数据侧纪律(先查档,再动手)

- **数据源注释 > 采样凑证**:任何「X 是什么/有没有 Y」的疑问,**先查注册表/常量文件的 docstring 与采集溯源注释**(如 `cw_shop_odds.REFRESH_PROB` 的 docstring 写明「游戏内概率表实机 OCR,无位面维度」),答案已在则直接引用——**不要**先跑采样/派 worker/提「待实机核实」。历次批间互证的同类事故:①真值表早已在档仍派 worker 重采白跑;②本可 docstring 一步出答案的疑问,先跑了两局采样凑证吻合;③机制归因未先查 docstring,sim 测试角色自查后自纠。**消费侧对偶**:派单规格里的每个「现状是 Y」断言、压测报告的每个「待核实」建议,同样先过 docstring 这道门。
- **数据治理**(发现旧数据是错的——用户定调:能修复就修复,不能修复就删掉,免得误导未来):
  1. 先定界污染窗口(从采集 bug 引入的第一局起,不是发现日);
  2. 判修复/删除——真值可从别的源重算(如 decisions 逐轮行重算终值/日志回填)→ 修复;真值从未被捕获 → 删除;判不了先隔离标注,别在判读里裸奔;
  3. 派生物必须再生(live 流语料变了 → Δ 池快照重跑生成器、依赖它的 sim 基线作废重记);
  4. 留证≠留语料(事故证据 = 日志/截图/sentinel 保留;删的是分析语料行;删除动作与理由记进度账本);
  5. 防再犯——修复落写端 schema,别靠一次性手工回填(手工回填漏网 = 下一轮伪值)。
  动手前先核语义:`loss+final_hp=100` 可能是放弃局合法值(中断保留当前 HP),不是伪值——把合法数据当脏数据删,比留着脏数据更糟。

## 反例论据(为什么判读纪律这么严)

历届单点断层各自存活 3+ 局才被抓;曾把单帧牌面当全序列、误判健康线而弃线——判读流程与跨局对照纪律每条都有对应的实盘反例(存档于进度账本历史)。
