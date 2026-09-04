# ADR-0446:配对完成度买牌信号——合并 A/B 实测定谳退回(删码留档)

> **版本界碑(2026-09-04 ADR 存量 review;对象属 decision_v2 栈或旧策略代,现行权威 = strategy-docs/flow/proofs + dd-NNN 系)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb(dd-038)删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

- 日期:2026-08-28
- 状态:**rejected(合并系结构性零活性,退回删除;开关生命周期第 4 态——预注册退出 #1 兑现)**
- 谱系:W469 catalog 先验链定谳删除(ADR-0442)→ W473 成型解剖(⑭冻结买入/⑮买散件/⑯成型后放血病灶)→ W476 设计 + W481 对抗审计修补 → W482 与经济循环总模型(ADR-0445)合并落码 → 合并 A/B 实测 → 本退回
- 设计单一源:`docs/develop/currency_war/prereg/w476_pair_signal/DESIGN.md`;A/B 判据=`docs/develop/currency_war/prereg/w482_merged_ab/PRE_REGISTRATION.md`(判据未改);判定报告=`w482_merged_ab/REPORT.md`

## Context(曾经为什么立项)

P1 成型引导真空:店里出现「能完成已拥有结构」的件时,评分维构造性低显影,非正分门拒之。W469 的 catalog 先验死于「无条件先验 + q=c/k 低精度 + 成型后放血」;本信号改为观测驱动三形态(S1 补齐档位/S2 核心 dup 升星/S3 引擎兜底),bump=engine_jump_gold−int_emb 零新常量,W481 五修复项内建(B-1 cap 余量/B-2 fire 率仅披露/B-3 兑现率门分列/I-1 义务帧辖域/⑩容量并入)。

## Decision(退回裁决)

1. **删码**:pair_signal.py 全模块 + scoring 接线(score_bump 调用/bd['pair_fire']/bd['pair_bump'])+ arbiter 消费计数(ROUND_FIRE_CAP 门/轮计数)+ strategy 轮重置 + 测试锁 B 侧;economy_cycle 的跨档计数改为结构性口径(`_crosses_engine_tier`:买入后四体系达成数 +1)——与 S1/S2「当帧跨档」同一事实集合,A 的容量刀法(A-1/A-2)语义不变。
2. **归因(合并 A/B 实测,n=451×2,池 6400d5d8+eqg1 同 seed 配对)**:fire 全 5734 决策帧 = 0。**不是**预注册预设的候选生成层缺口,而是 **I-1 修复(义务帧辖域 g>R\*)× P1 溢余稀疏的结构性交互**——P1 溢余帧仅 12/4059(0.30%),叠加 form_ok/hp/boss 门后为 0。W476 原设计(非义务帧 fire)与 W471 息线以内零漂移锚在合并系中不相容;择 I-1 后 B 在其设计辖域(P1)内结构性零落点。
3. **连带结果**:成型率 r6 +0.22pp(p=1.0);兑现率门无样本可测。
4. **「配对完成度优先」命题归档待议(非证伪)**:本退回是架构收编的结果(A 义务管「花多少」+ EV 过滤管候选质量),不是「跨档完成件不值得买」的证据(P20 量级账仍成立;A/B 期 P1 溢余帧上无一次 bump 机会被观测)。**重立条件(操作化)**:实机观测到义务帧「花给谁」分布中跨档完成件被 EV 层系统性放行失败(判读面=义务帧花销去向分项),且 I-1 辖域前提(g>R\* 帧稀疏)在实机不成立(实机囤金面六局实证 vs sim 稀疏的 sim-real 错配方向),届时以「评分层配对偏置」形态重立并重新预注册。

## Considered Options

- ①退回删除(选,预注册退出 #1 兑现)②维持死码(零行为零维护价值=债)③扩辖域至 P2 溢余帧(与 W471 §1.4「P2 成型语义换血,由终局线辖」冲突,且属重新设计非本判据范围,归档待议内含)。

## Consequences

- 锁面:test_cw_economy_cycle_pair_signal.py 删除,A 锁以结构性跨档口径重建于 test_cw_economy_cycle.py;零漂移影响=B 退出后 on 行为与 A-only 完全一致(B 从未 fire,退出前后无行为差)。
- 零删码成本兑现:B 全程零行为(fire=0),退回不改变任何对局轨迹。
