# retirement.md —— 旧遥测流停用档案(处置判据与清单结构)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(含 GameState/BoardState
> 命名对应注)。术语与图例:保留词与数字来源标注四形态【注】【推】【拟】【拍】见
> [README](README.md) §6 术语表;对账 = 推算状态与下一帧实读逐项比对,对不上即 bug;
> 帧 = 一次拍画面+做决策的时点,帧代次 = 帧的版本标记。
> **写作纪律**:本文只写停用的**处置判据与清单结构**(as-built 无状态)——执行进度记
> 进度账本,本文不随批更新状态;停用排期与波次的原单一源 =
> 排期过程件(单源直迁八波)已删(考古走 git 历史),本文不复写排期;
> 变更史归 ADR,本文文末只留版本历史表。

## 1. 停用对象与理由

停用对象 = 在用流程侧遥测旧 12 流(`decisions/outcomes/exogenous/spend_ledger/
shop_snapshots/cw4_counters/defect_ledger/op_journal/exec_events/invest_cards/
obs_conflicts/runs`,recorder 写入面/match_archive 切片/全仓落盘调用点三方交叉清点,
另扫出清点补遗第 13 条 `board_state_archive.jsonl`)。

**停用理由(修正口径)**:流散乱(12 流分片、跨流 join 复盘、同一事实多处副本)+
写入位置不全(开局 1-1/补给→备战等空缺时点)+ 无渠道签名(真读/兜底不可分,靠散字段)
+ 无统一 state(GameState/ExpectedEntry/tracked 族多容器并行)——**非查询/重放问题**
(在用查询本就是读行,统一流水延续读行模型并强化)。

## 2. 逐流处置表

处置取值:**字段并入** = 内容成为统一 state 字段(随快照行自带);**保留专用** =
承载非 state 适用范围的独立语义面,作为专用流保留;**停用** = 停写且无并入归宿。
分布:策略源并入 9 / 保留 2 / 逐 key 审计 1(+清点补遗 1,倾向停用);**禁一句话
并入,逐流结论与理由如下**:

| 流 | 处置 | 归宿与理由(一句) |
|---|---|---|
| decisions | 停用(新写) | 「行内全量 GameState」自足形态=流水直系前身;流程侧职责归 journal,决策侧内容归策略侧决策行——一条流装不下两类语义(两文件模型由来) |
| outcomes | 字段并入+流停用 | 结算真值=画面 op 观察,`apply_settlement_cover` 写入后随快照行自带;伤害三分量不入 state(无决策消费),归宿两案待裁决(fields.md 扩 Settlement vs 流水行可选 extra 槽) |
| exogenous | 停用(无独立事件流) | kind 逐值并入(节点推进→派生写入行/popup→obs_event/briefing→开局事实域/event_choice→chosen 域/sell_income·hp_pay·level_up→②写入行/resumed→中继行族等);battle_done 旧写入位置停写与旧流停写同批;cw_anchor 四 carrier_kind 归宿随锚处置待裁决 |
| spend_ledger | 拆分:字段并入+部分停用 | 金真值→gold 域;计数→计数域+质量标记;plan_truncated/refresh_skipped→receipts 发射行字段;duration/boundary/progressed=纯工程面停用归日志 |
| shop_snapshots | 字段并入候选+流停用 | 牌面=state 的 shop payload 域,offer/refresh 各为一行观察写入行,独立快照流冗余;rho_obs 不并入→判读侧离线派生 |
| cw4_counters | 流停用(键级审计已定案:效果域 0 键/策略行为键 256 字面+16 闭族 80 实例+9 开放族全保留=策略侧决策行 strategy-state 载体,无消费删 0 键) | 键=策略 state 容器(StrategyState.cw4_counters),sim 红则/轮差分/预注册不经流照旧;局终级全键聚合=局终域行载荷 ``MatchFinal.cw4_counters``;键全集登记单一源=封闭测试(test_cw4_key_closure) |
| defect_ledger | **保留专用(待裁决)** | 案 A=并入 obs_event;案 B(倾向)=保留专用流——severity 判级/复现计数/verdict 取值清单/失配告警联动(失配告警=缺陷触发的报警停机联动)是「质量索引」不是「证据内容」;裁保留时 refs 改指 journal `(run_id,v)` 键+寿命联动 |
| op_journal | **停用(2026-09-15 用户裁定,写入方删除批写入代码)** | op 耗时画像/op 序列归 server 主日志 `[cw-op]` 行(dispatch/仲裁出口行);进程中断证据 = 实机段无 match_final 收尾 + 行流 ts 戛止(中断时点活动签名 = 尾行 sig.actor);动作回执/金差账已在 state 流 receipts/gold 行登记 |
| exec_events | 字段并入+流停用 | 发射事实→receipts 发射行(**零成败字段**);失败可见性=消费方对比语义(发射行后预期变化未出现=未落地,判定归观察侧 reconcile) |
| invest_cards | 字段并入候选+流停用 | 候选卡面+效果原文→画面 payload 域 `strategy_offer`(离屏即 None);注册表 ground truth 回流用途不变;逐局原文语料断供已定案 = 接受断供(写入端已随首批写面删除批停用),定案与恢复路径 = |
| obs_conflicts | 并入(obs_event)+流停用 | 拒读/仲裁拒绝=零写入观察证据,与写入同源同流;行结构/截图节流/告警门语义原样并入 |
| runs | 字段并入+派生列拆分+流停用 | 局终收尾一行(局终域 match_final:一**段**一行);gold 轨迹从流水派生;comps/pivot 派生列前置依赖=策略侧决策行;断流兜底回填改为启动扫描补写行(note=recovered 注记) |
| board_state_archive(补遗) | 倾向停用 | 逐能力归宿:bs_prov→快照来源注记、bs_pending→行内挂起摘要、局终速查→match_final 行;行行全量后独立局终归档流冗余;停用与 12 流同批,停写前继续在用 |
| 清点排除记录 | 不在适用范围 | frames.jsonl/shadow_predictions.jsonl=工具面/离线面(非 bot 运行时落盘),显式排除防方法约束力折损 |

## 3. cw4_counters 逐 key 审计(用户裁定)

键级分流:①游戏效果计数键 → state 效果域(随快照行自带);②策略行为键 → 策略侧
决策行(strategy state);③无消费方键 → 删。消费方判定面=实机判读/sim 检查失败
(red)判据面(即 sim 检查跑红时看哪些判据)/轮差分/预注册披露;逐 key 归宿表=迁移
前置件(产出归迁移批,不在本文预列)。

**已定案代码落地形态(键并入归两文件模型②的策略自身记忆要素,决策行文件落地
前由策略 state 容器承载)**:效果域 0 键(①空转,效果域 inventory 与本容器零交
集);策略行为键 256 字面+16 闭族 80 实例+9 开放域族全保留在策略 state 容器
(②,无消费删 0 键,弱消费键随迁);流载体停用,局终级全键聚合改由局终域行载荷
``MatchFinal.cw4_counters`` 携带。键全集登记单一源 = 封闭测试(测试仓
test_cw4_key_closure:字面全集对齐+参数化族登记+豁免清单三层,扫描方法=审计七
类写模式的 AST 机器化,含 helper 实参常量解析)。

## 4. 两文件模型(全局落盘目标)

①流程侧 = 统一 state 自足快照流(`state/journal.jsonl`,见 [journal.md](journal.md));
②策略侧 = DecisionTrace 瘦身演进决策行(四要素:state_ref 版本钉+策略自身记忆+决策
函数关键记录+动作 op;瘦身判据=凡统一 state 可算的内容不存;行 schema 归策略侧设计
正文)。其余流逐流评估三类处置,不因「一条流」而一句话并入。

## 5. 停用排期(原排期件已删)

停用排期与波次的原单一源(原排期件 §2,单源直迁八波)已随过程件清理删除(考古走 git 历史);本文只记各流当前处置形态,不复写排期。
原影子口径的旧排期框架已随直迁裁定作废(推翻影子双写;首批写面删除已按直迁口径执行 9 流写入方删除)。旧影子框架各批次的实际承载内容(按内容命名,编号已废):写入口与渠道签名/流水落盘与 journal 常开化/obs_event 登记面并入 = 交付于统一 state 直迁系列;派生规则与类型派生 = 已交付(测试族+落地审+实机窗口承担验收);判读/哨兵/运行时消费面切换、cw4 键级审计与键并入、决策面/sim 切换 = 各自成批交付;写面删除与 GameState 本体删除 = 删除批次收尾,归档只读保留。

链观察实施批独立切分,见 [chain-observation.md](chain-observation.md)。
**落地状态(链观察落地批 2026-09-16)**:链写入方/查链接线/diff 证据已交付
(载体 NodeChain/TokenCell + 过渡屏与备战帧写入方 + `chain_diff` 行 +
类型派生四②商店查链);记录表停用(含 `ledger_node_type` 残余消费点
read_game_state 查表优先/装备 O1 门/三票 重接与 session 表冻结面盘点)
仍归本节适用范围,承接范围见统一观察对账与链观察两迭代的不解决清单。

## 6. 停用前置条件(直迁形态)

影子口径的「旧流停写进入门六条」按直迁裁定重构,细则单一源 =
原排期件(已删,git 可溯)的逐条重构表,本文只留当前形态:

1. 黑窗消解三条件:**消解**——无双写窗即无黑窗概念;其保护意图(决策源/sim/判读
   三面不悬空)转为批次顺序门(删写面的批之前读面已切,删 GameState 本体的批之前
   消费面已切)。
2. obs_event 登记面并入:**已交付**——obs_conflicts 写面
   删除前并入在位,拒读保留证据义务不蒸发。
3. 宽容契约到装配端:**已闭环**(read_journal_stats 单一源+三层计数),
   常开化后即刻全量生效。
4. 决策数据源不抽空:**保留**——GameState 本体删除批之前 applied-gate 族
   (读 action_log 末条 applied 标记做门的消费面)必须已迁观察侧 reconcile
   (消费面切换批交付,本体删除批把门)。
5. 寿命契约耦合:**保留**——滚动清理以 run 段为整体单元(两文件同批淘汰,禁单件
   淘汰);已淘汰单元的钉=永久 unverified,档案 index 行申报 archived_out 注记;
   保留窗下限=跨期语料窗(实现居所 = `cw_state_journal` 停用 manifest)。
6. 归档只读+观察窗:观察窗(过渡性质)消解,实机窗口(验证性质)替代;归档数据
   只读保留为事实约束(旧档案不删不写,可裸读考古)。

## 7. 消费方迁移清单(11 消费面)

状态三分 = **已迁/待/不适用**;本清单只定结构与计划批次,状态推进记进度账本。
批次列的旧影子框架编号已作废,对应关系见 §5(按内容命名);现行排期以 git 历史的原排期件为准。

| # | 消费面 | 迁移动作 | 状态 | 批次 |
|---|---|---|---|---|
| 1 | 判读 CLI(`telemetry/cli.py`+`query.py` 视图族) | 新视图族改读两文件(按行读+行间差分,零重放);旧视图读旧档案只读保留至停写批 | 待 | 消费面切换批 |
| 2 | 对局档案装配(`telemetry/match_archive.py`) | 切片改两文件+待裁决的保留专用流;派生列改从流水行派生(comps/pivot 标待策略侧);旧档案只读兼容 | 待 | 消费面切换批 |
| 3 | 回放/修复工具(`tools/cw/replay_to_md.py`、`repair_invest_attribution.py`;自原遥测设计件(已删,git 可溯)的档案行拆出单列——本文 11 面对原表 10 行=拆行细化,非矛盾) | 改读新档案面(随装配器 v12) | 已迁(2026-10-16:replay_to_md 就地重写为 journal 行模型版,经档案切片 `state/journal.jsonl` 单键读新账,commit 84ecddaf4+161cccdc8;repair_invest_attribution 经 match_archive 装配切片读数,已在当前面,无需再迁) | 消费面切换批 |
| 4 | sim 账本三消费面(`sim/checks/ledger.py` 红则判据/`sim/engine_p1.py` 轮差分/`sim/ab_core_swap.py` 预注册披露) | 按逐 key 审计结论切新载体,三面同批;sim runner 经统一写入口落流水(引擎直写容器口径;原合成口已随帧通道停用);deployed→front/back 槽位映射前置 | 待 | 停写批前置 |
| 5 | 复测批/AB 判读(`tools/cw/ab_judge.py`、`cw_batch_stats.py`) | sim 账本切新面后指标重接 | 待 | 消费面切换批 |
| 6 | defect_ledger(若裁保留专用;幸存流+旧流消费方双身份) | refs 目标迁移(指 journal `(run_id,v)` 键)+寿命联动(随 run 段同批淘汰) | 待(随 §2 保留裁) | 消费面切换批 |
| 7 | 校准/证明脚本(`tools/cw/proofs/*`、`win_model_*`) | 存量语料归档只读不迁移;新语料走新视图;跨期语料窗受寿命契约约束 | 待 | 消费面切换批后按需 |
| 8 | 哨兵脚本组(`sr-od-currency-war-dev` skill scripts/:cw_sentinel/cw_runs_gap/cw_early_stop) | 尾读改 journal.jsonl(runs 断流探测→局终域行断流探测);过渡期盯旧流至停写批 | 待 | 消费面切换批 |
| 9 | 运行时内部(cw_loop 心跳/summary 兜底/Δ池再生触发/终局防重读门) | 心跳改读版本 id;兜底回填与 Δ 池再生的触发改挂局终域行落盘事件;终局防重改挂 match_final 写前查重(运行时控制面豁免类) | 待 | 观察接线批/消费面切换批 |
| 10 | 策略侧决策行(在用 DecisionTrace) | 瘦身演进落文+接线;行面钉字段 = state_ref 单字段(过渡钉面标记 pin_scope 已停用删除——行面钉字段终裁 = state_ref 单字段,历史档案判读知识见 [决策行文件schema设计.md](决策行文件schema设计.md) §8-2) | 待 | 接线 = 决策面切换批后另批(决策行文件落地批,验收绿后立卡,已定案) |
| 11 | action_log 成败消费面(cw_evolution applied-gate/sim 引擎两处/cw_bench_equips 申报面) | 改观察侧驱动(reconcile 对比口径:发射行+后续快照);零成败 receipts 落地前旧数据源不得抽空 | 待 | 消费面切换批(与决策行同批) |

「不适用」档预留:清单内消费面经评估确认与新面无交集时标不适用并附一句理由,禁静默
跳过(方法同逐流处置:逐面结论,禁一句话并入)。

---

## 版本历史

| 日期 | 变更 | 凭据 |
|---|---|---|
| 2026-09-11(前) | 初版:13 流处置表(§2)+cw4 逐 key 审计(§3)+两文件模型(§4)+影子期旧排期框架与前置六条(影子口径)+11 消费面清单(§7);两轮批面修正(文档审释义补注、对账口径滞后同步) | 进度账本 game_state 目录批;审结论 = 本地评审档案(不入库) |
| 2026-09-11 | 直迁重构:影子期旧排期框架与前置六条影子口径作废——§5 排期改指直迁原排期件、§6 前置条件改直迁形态、逐批落点对照叙述链收敛为本表;§2 board_state_archive 行「影子期继续在产」改「停写前继续在产(在用)」 | (直迁裁定)/ (首批写面删除批落档+本重构兑现);排期正本 = 原排期件(git 可溯) |
| 2026-09-11 | §2 invest_cards 行「停写前须定案」兑现落档:定案 = 接受断供,恢复路径 = strategy_offer 域建模(挂评估批);同批落 obs 缺陷 refs 指冻结档案的判读指针处置(后果 2/3 两件收尾) | (定案)/ (首批写面删除批——写入方先于定案停用的批序事实如实申报) |
| 2026-09-12 | §7 #10 行修订:迁移动作列「消费切换子集落地前 state_ref 带 pin_scope 标记」随字段停用删除作废——行面钉字段 = state_ref 单字段,历史档案判读知识指 schema 权威版本 §8-2;批次列改「接线 = 决策面切换批后另批」 | 行面钉字段终裁 = state_ref 单字段(定案记录 git 历史可溯);字段停用执行(commit b0775d8b) |
| 2026-09-15 | §2 op_journal 行改判停用(原「保留专用(待裁决)」):op 调用流归宿 = 主日志 `[cw-op]` 行;停滞检测/活跃局判定/监控轮询经核实零依赖该流(停用对哨兵组零迁移零降级);存量档案双键切片(op_journal + state/journal)冻结只读,SCHEMA_VERSION 冻结 12 防重装配摘除 | 用户裁定 2026-09-15;消费盘点与迁移映射 = 进度账本设计件 |
