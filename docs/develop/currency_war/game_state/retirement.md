# retirement.md —— 旧遥测流退役档案(处置判据与清单结构)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(含 GameState/BoardState
> 命名对应注)。
> **写作纪律**:本文只写退役的**处置判据与清单结构**(as-built 无状态)——执行进度记
> 进度账本,本文不随批更新状态;退役排期与波次的单一源 =
> [r5-migration-plan.md](r5-migration-plan.md)(单源直迁八波),本文不复写排期;
> 变更史归 ADR(ADR-0634 / ADR-0641),本文文末只留版本历史表。

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
| board_state_archive(补遗) | 倾向退役 | 逐能力归宿:bs_prov→快照来源注记、bs_pending→行内挂起摘要、局终速查→match_final 行;行行全量后独立局终归档流冗余;退役与 12 流同批,停写前继续在产 |
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

## 5. 退役排期(单一源 = R5 直迁八波)

退役排期与波次的**单一源 = [r5-migration-plan.md](r5-migration-plan.md) §2**
(单源直迁八波 W1-W8,依赖序与波间并行度同表);本文不复写排期。
原影子口径的 M1-M5 排期框架已随直迁裁定作废(ADR-0634 推翻影子双写;
删除波 1 已按直迁口径执行 9 流写入端删除,ADR-0641)。旧编号引用对照:

| 旧框架(M1-M5,影子口径,已作废) | 直迁八波去向 |
|---|---|
| M1 写入口批 | 写入口/渠道签名/流水落盘 = R1 系列已交付;journal 常开化 = W1(ADR-0634);obs_event 登记面收编义务折入 W1 |
| M2 观察接线批 | 观察接线收尾 = W1;「两镜像窗口前提检查」随影子框架消解 |
| M3 派生规则验收批 | 派生规则②③腿+类型派生已交付(R1.2/R2);派生验收职责由每波验证三元组承接(测试锁族+落地审+实机窗口) |
| M4 消费方切换批 | 判读/哨兵/运行时切换 = W3;cw4 审计+键收编 = W4;决策面/sim 切换 = W6 |
| M5 旧流停写批 | 写面删除 = 删除波批次(删除波 1 已执行 9 流写入端,余量随 W7)+GameState 本体删除 = W8;归档只读保留,「观察窗」流程消解 |

链观察实施批(B-1..B-4)独立切分,见 [chain-observation.md](chain-observation.md)。

## 6. 退役前置条件(直迁形态)

影子口径的「M5 进入门六条」按直迁裁定重构,细则单一源 =
[r5-migration-plan.md](r5-migration-plan.md) §4 逐条重构表,本文只留当前形态:

1. 黑窗消解三条件:**消解**——无双写窗即无黑窗概念;其保护意图(决策源/sim/判读
   三面不悬空)转为波序门(W7 删写面前 W3-W5 读面已切,W8 删本体前 W6 消费面已切)。
2. obs_event 登记面收编:**已交付**(W1,ADR-0634 决策 5)——obs_conflicts 写面
   删除前收编在位,拒读留证义务不蒸发。
3. 宽容契约到装配端:**已闭环**(R3.2:read_journal_stats 单一源+三层计数),
   常开化后即刻全量生效。
4. 决策数据源不抽空:**保留**——GameState 本体删除(W8)前 applied-gate 族
   (读 action_log 末条 applied 标记做门的消费面)必须已迁观察侧 reconcile
   (W6 交付,W8 门)。
5. 寿命契约耦合:**保留**——滚动清理以 run 段为整体单元(两文件同批淘汰,禁单件
   淘汰);已淘汰单元的钉=永久 unverified,档案 index 行申报 archived_out 显影;
   保留窗下限=跨期语料窗(实现居所 = `cw_state_journal` 退役 manifest)。
6. 归档只读+观察窗:观察窗(过渡性质)消解,实机窗口(验证性质)替代;归档数据
   只读保留为事实约束(旧档案不删不写,可裸读考古)。

## 7. 消费方迁移清单(11 消费面)

状态三分 = **已迁/候/不适用**;本清单只定结构与计划批次,状态推进记进度账本。
批次列的 M 编号为影子框架旧排期,与直迁八波的对应见 §5 对照表(现行排期以
R5 规划为准)。

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

## 版本历史

| 日期 | 变更 | 凭据 |
|---|---|---|
| 2026-09-11(前) | 初版:13 流处置表(§2)+cw4 逐 key 审计(§3)+两文件模型(§4)+影子期/M1-M5 排期框架与前置六条(影子口径)+11 消费面清单(§7);两轮批面修正(文档审 F14/F15 释义补注、v3.8 对账同步 M2/M3 行滞后同步) | 进度账本 game_state 目录批;审结论 = 进度目录 `reviews/game_state目录批-文档审.md`(本地不入 git) |
| 2026-09-11 | 直迁重构:影子期/M1-M5 排期框架与前置六条影子口径作废——§5 排期改指 R5 八波正本(附旧编号对照注)、§6 前置条件改直迁形态、逐批落点对照叙述链收敛为本表;§2 board_state_archive 行「影子期继续在产」改「停写前继续在产」 | ADR-0634(直迁裁定)/ ADR-0641(删除波 1 落档+本重构兑现);排期正本 = r5-migration-plan.md |
