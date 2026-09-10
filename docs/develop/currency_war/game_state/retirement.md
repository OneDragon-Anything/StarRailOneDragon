# retirement.md —— 旧流退役与消费方迁移(排期与清单结构)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(含 GameState/BoardState
> 命名对应注)。
> **写作纪律**:本文只写退役**排期与清单结构**,不写执行进度——进度记进度账本,
> 本文不随批更新状态。

## 1. 退役对象与理由

退役对象 = 现役流程侧遥测旧 12 流(`decisions/outcomes/exogenous/spend_ledger/
shop_snapshots/cw4_counters/defect_ledger/op_journal/exec_events/invest_cards/
obs_conflicts/runs`,recorder 写入面/match_archive 切片/全仓落盘调用点三方交叉清点,
另扫出清点补遗第 13 条 `board_state_archive.jsonl`)。

**退役理由(修正口径)**:流散乱(12 流分片、跨流 join 复盘、同一事实多处副本)+
写点不全(开局 1-1/补给→备战等空缺时点)+ 无渠道签名(真读/兜底不可分,靠散字段)
+ 无统一 state(GameState/ExpectedEntry/tracked 族多容器并行)——**非查询/重放问题**
(现役查询本就是读行,统一流水延续读行模型并强化)。

## 2. 逐流处置表

处置词表:**字段收编** = 内容成为统一 state 字段(随快照行自带);**保留专用** =
承载非 state 辖域的独立语义面,作为专用流保留;**退役** = 停写且无收编归宿。
分布:策略源收编 9 / 保留 2 / 逐 key 审计 1(+清点补遗 1,倾向退役);**禁一句话
收编,逐流结论与理由如下**:

| 流 | 处置 | 归宿与理由(一句) |
|---|---|---|
| decisions | 退役(新写) | 「行内全量 GameState」自足形态=流水直系前身;流程侧职责归 journal,决策侧内容归策略侧决策行——一条流装不下两类语义(两文件模型由来) |
| outcomes | 字段收编+流退役 | 结算真值=画面 op 观察,`apply_settlement_cover` 写入后随快照行自带;伤害三分量不入 state(无决策消费),归宿两案候裁(正本扩 Settlement vs 流水行可选 extra 槽) |
| exogenous | 退役(无独立事件流) | kind 逐值收编(节点推进→派生写入行/popup→obs_event/briefing→开局事实域/event_choice→chosen 域/sell_income·hp_pay·level_up→②写入行/resumed→中继行族等);battle_done 旧写点停写与旧流停写同批;cw_anchor 四 carrier_kind 归宿随锚处置候裁 |
| spend_ledger | 拆分:字段收编+部分退役 | 金真值→gold 域;计数→计数域+质量标记;plan_truncated/refresh_skipped→receipts 发射行字段;duration/boundary/progressed=纯工程面退役归日志 |
| shop_snapshots | 字段收编候选+流退役 | 牌面=state 的 shop payload 域,offer/refresh 各为一行观察写入行,独立快照流冗余;rho_obs 不收编→判读侧离线派生 |
| cw4_counters | **逐 key 审计**(见 §3) | 有消费方键迁入(state 效果域/策略侧决策行),无消费方键删;审计清单=迁移前置件 |
| defect_ledger | **保留专用(候裁)** | 案 A=收编 obs_event;案 B(倾向)=保留专用流——severity 判级/复现计数/verdict 词表/安灯联动(安灯=借自产线的停线告警词,此处指缺陷触发的告警通知联动)是「质量索引」不是「证据内容」;裁保留时 refs 改指 journal `(run_id,v)` 键+寿命联动 |
| op_journal | **保留专用(候裁)** | op 耗时画像/孤儿 enter 行=工程诊断面(非 state 辖域);与 defect_ledger 同批同法裁决 |
| exec_events | 字段收编+流退役 | 发射事实→receipts 发射行(**零成败字段**);失败可见性=消费方对比语义(发射行后预期变化未出现=未落地,判定归观察侧 reconcile) |
| invest_cards | 字段收编候选+流退役 | 候选卡面+效果原文→画面 payload 域 `strategy_offer`(离屏即 None);注册表 ground truth 回流用途不变;不进早期迁移批则停写后效果原文回流断供,停写前须定谳 |
| obs_conflicts | 收编(obs_event)+流退役 | 拒读/仲裁拒绝=零写入观察证据,与写入同源同流;行结构/截图节流/告警门语义原样收编 |
| runs | 字段收编+派生列拆分+流退役 | 局终收口一行(局终域 match_final:一**段**一行);gold 轨迹从流水派生;comps/pivot 派生列前置依赖=策略侧决策行;断流兜底回填改为启动扫描补写行(note=recovered 显影) |
| board_state_archive(补遗) | 倾向退役 | 逐能力归宿:bs_prov→快照来源注记、bs_pending→行内挂起摘要、局终速查→match_final 行;行行全量后独立局终归档流冗余;退役与 12 流同批,影子期继续在产 |
| 清点排除记录 | 不入辖 | frames.jsonl/shadow_predictions.jsonl=工具面/离线面(非 bot 运行时落盘),显式排除防方法约束力折损 |

## 3. cw4_counters 逐 key 审计(用户裁定)

键级分流:①游戏效果计数键 → state 效果域(随快照行自带);②策略行为键 → 策略侧
决策行(strategy state);③无消费方键 → 删。消费方判定面=实机判读/sim 检查失败
(red)判据面(即 sim 检查跑红时看哪些判据)/轮差分/预注册披露;逐 key 归宿表=迁移
前置件(产出归迁移批,不在本文预列)。

## 4. 两文件模型(全局落盘目标)

①流程侧 = 统一 state 自足快照流(`state/journal.jsonl`,见 [journal.md](journal.md));
②策略侧 = DecisionTrace 瘦身演进决策行(四要素:state_ref 版本钉+策略自身记忆+决策
函数关键记录+动作 op;瘦身判据=凡统一 state 可算的内容不存;行 schema 归策略侧设计
正文)。其余流逐流评估三类处置,不因「一条流」而一句话收编。

## 5. 退役排期(迁移批次)

| 批 | 内容 | 验收门(一句) |
|---|---|---|
| M1 写入口批 | 写入口+渠道签名+版本分配+流水落盘(行行全量+逐字段来源注记)+obs_event 登记面+receipts/派生域/上下文域/局终域+开关装配;域准入白名单逐格核源;cw4 逐 key 审计清单 | 封闭集/白名单/旁路 grep 锁/行序=版本序/行行自足抽检/耗时体积口径实测;影子局抽检绿 |
| M2 观察接线批 | 画面 op 观察链改走统一入口+第二漏斗+结算覆盖+心跳改版本 id+obs_event 接线+窗①写缓冲+**占号次序统一到补写时**(v3.8-低-6) | 渠道签名完备率;旧 GameState 读端零行为变化;弹窗族可达性走查;收编域覆盖率逐域核对;段界窗①走查;**两镜像窗口前提检查**(v3.8-中-4:第二漏斗喂入面不得触及〈1-1 首备战帧前〉〈两次 0p 采到之间〉两窗) |
| M3 派生规则验收批 | 派生管线已实现面(四腿/幂等锚/类型派生)的验收走查+未覆盖面落地(倒退 obs_event 留证/权威降位重锚+N=2 载体)+效果域写点核源+**效果推进段迁移三面登记**(驱动时点备战 tick→派生推进/键源镜像→派生层/账本 `_last_tick_node` 计数器退役;实施批位候效果域讨论,v3.8-中-1) | 判定方案场景走查逐场景恰一行推进写入;级联两段恰一次推进;恢复局与重入走查 |
| M4 消费方切换批 | 判读 CLI 新视图/档案装配器 v12/哨兵尾读/sim 账本(含 cw4 三面+deployed 槽位映射前置)/复测批指标/策略侧决策行接线(hp/gold/level 投影切换子集前置+pin_scope 窗内标记) | 新旧视图同局对拍 diff 全绿;哨兵演练;sim 对拍绿;标记撤销核验 |
| M5 旧流停写批 | 处置表定案的流写点下线(含 battle_done 停写;防双计由装配器切片侧消解)+归档只读声明+判读文档改版 | 进入条件见 §6;全量测试绿;观察窗开启 |

依赖序:派生代码段实现串行(M2/M3 验收可并行,不同文件域);M4 依赖 M1-M3 全绿;
M5 依赖 M4 验收+§6 三条件。链观察实施批(B-1 采证→B-2 过渡 op→B-3 接线 diff→B-4
消费)独立切分,chain_diff 登记挂 M1/M2,见 [chain-observation.md](chain-observation.md)。

## 6. 退役前置条件(M5 进入门)

1. **黑窗消解三条件**(缺一不开,无黑窗):策略侧决策行 v1 落地接线;sim 三消费面
   切换完成;判读 CLI/档案/哨兵新视图验收绿。
2. **obs_event 登记面收编完成**:旧流停写前必须完成(否则拒读留证断供——obs_conflicts
   等留证义务的归宿未接即停写=数据蒸发)。
3. **宽容契约到装配端**:装配器/判读/哨兵统一实现「坏行跳过+计数申报」消费契约、
   note=recovered 行过滤/标记义务、state 序列化规范化对拍——宽容消费契约在装配端
   就位后才允许旧流停写。
4. **决策数据源不抽空**:action_log 成败消费面(applied-gate 族——读 action_log
   末条 applied 标记做门的消费面)迁移到观察侧驱动(发射行+后续快照对比)完成前,
   相关消费面的旧数据源不得先停写。
5. **寿命契约耦合**:state_ref 解析寿命=run 段记录行存续期;滚动清理以 run 段为整体
   单元(两文件同批淘汰,禁单件淘汰);已淘汰单元的钉=永久 unverified,档案 index
   行申报 archived_out 显影;保留窗下限=跨期分析语料窗。
6. **归档只读+观察窗**:停写后旧流文件归档只读(在飞消费方读旧档案不受影响);
   观察窗(建议 ≥2 周)后滚动清理。

## 7. 消费方迁移清单(11 消费面)

状态三分 = **已迁/候/不适用**;本清单只定结构与计划批次,状态推进记进度账本。

| # | 消费面 | 迁移动作 | 状态 | 批次 |
|---|---|---|---|---|
| 1 | 判读 CLI(`telemetry/cli.py`+`query.py` 视图族) | 新视图族改读两文件(按行读+行间差分,零重放);旧视图读旧档案只读保留至停写批 | 候 | M4 |
| 2 | 对局档案装配(`telemetry/match_archive.py`) | 切片改两文件+候裁保留专用流;派生列改从流水行派生(comps/pivot 标待策略侧);旧档案只读兼容 | 候 | M4 |
| 3 | 回放/修复工具(`tools/cw/replay_to_md.py`、`repair_invest_attribution.py`;自遥测正本 §3.6.2 档案行拆出单列——本文 11 面对正本表 10 行=拆行细化,非矛盾) | 改读新档案面(随装配器 v12) | 候 | M4 |
| 4 | sim 账本三消费面(`sim/checks/ledger.py` 红则判据/`sim/engine_p1.py` 轮差分/`sim/ab_core_swap.py` 预注册披露) | 按逐 key 审计结论切新载体,三面同批;sim runner 经统一写入口落流水(synthesize_from_game_state 同口);deployed→front/back 槽位映射前置 | 候 | M4(停写批前置) |
| 5 | 复测批/AB 判读(`tools/cw/ab_judge.py`、`cw_batch_stats.py`) | sim 账本切新面后指标重接 | 候 | M4 |
| 6 | defect_ledger(若裁保留专用;幸存流+旧流消费方双身份) | refs 目标迁移(指 journal `(run_id,v)` 键)+寿命联动(随 run 段同批淘汰) | 候(随 §2 保留裁) | M4 |
| 7 | 校准/证明脚本(`tools/cw/proofs/*`、`win_model_*`) | 存量语料归档只读不迁移;新语料走新视图;跨期语料窗受寿命契约辖 | 候 | M4 后按需 |
| 8 | 哨兵脚本组(`sr-od-currency-war-dev` skill scripts/:cw_sentinel/cw_runs_gap/cw_early_stop) | 尾读改 journal.jsonl(runs 断流探测→局终域行断流探测);过渡期盯旧流至停写批 | 候 | M4 |
| 9 | 运行时内部(cw_loop 心跳/summary 兜底/Δ池再生触发/终局防重读门) | 心跳改读版本 id;兜底回填与 Δ 池再生的触发改挂局终域行落盘事件;终局防重改挂 match_final 写前查重(运行时控制面豁免类) | 候 | M2/M4 |
| 10 | 策略侧决策行(现役 DecisionTrace) | 瘦身演进落文+接线;消费切换子集落地前 state_ref 带 `pin_scope='board_state'` 标记(钉面≠消费面) | 候 | M4 前落地,M4 接线 |
| 11 | action_log 成败消费面(cw_evolution applied-gate/sim 引擎两处/cw_bench_equips 申报面) | 改观察侧驱动(reconcile 对比口径:发射行+后续快照);零成败 receipts 落地前旧数据源不得抽空 | 候 | M4(与决策行同批) |

「不适用」档预留:清单内消费面经评估确认与新面无交集时标不适用并附一句理由,禁静默
跳过(方法同逐流处置:逐面结论,禁一句话收编)。

---

## 附:2026-09-11 文档审修正批落点对照(本篇)

> F 编号 = 审结论条目号(审结论在进度目录 `reviews/game_state目录批-文档审.md`,
> 本地不入 git);本节为落点备忘,正文 as-built 口径以上文为准。

| 审条目 | 落点 | 修正 |
|---|---|---|
| F14 | §3 判定面 | 「sim 红则判据」展开为「sim 检查失败(red)判据面」;同类括注:「安灯」(§2 defect_ledger 行)、「applied-gate 族」(§6 前置条件 4)首现各加释义 |
| F15 | §7 第 3 行 | 补「自遥测正本 §3.6.2 档案行拆出单列」,11 面对 10 行=拆行细化非矛盾 |

---

## 附:2026-09-11 v3.8 对账同步批落点对照(本篇)

> 对账对象 = 遥测正本 v3.8 增量面(R8 的 13 项);本篇核对结论 = §5 排期表 2 处滞后
> 已同步(M2/M3 行),其余各节无滞后。本节为落点备忘,正文 as-built 口径以上文为准。

| 对账项 | 落点 | 修正 |
|---|---|---|
| v3.8-中-4 + 低-6 | §5 M2 行 | 验收门补两镜像窗口前提检查;内容补占号次序统一到补写时(细则单一源 = 正本 §3.7.2-M2,本文不复写细则) |
| v3.8-中-1 | §5 M3 行 | 内容补效果推进段迁移三面登记(批位候效果域讨论;细则单一源 = 正本 §3.7.2-M3 差异清单) |
| 无滞后申报 | — | §2 逐流处置/§3 逐 key 审计/§6 前置条件/§7 消费面清单与 13 项增量无交集;§5 其余批行(M1/M4/M5)与正本 §3.7.2 现行口径一致 |
