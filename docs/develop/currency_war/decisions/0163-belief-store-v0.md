# ADR-0163 信念层 v0(BeliefStore 字段级信念;04 号)

## Status

Accepted(2026-08-16;可靠性表/可观测性矩阵/VoI 不可逆门/归因分案器待后续)

## Context

04 号提案诊断:决策消费「OCR 点估计 + 读不到拍安全默认」——三个实案:M19 hp=100 毒化(读不到落默认,时间线 100↔真值震荡,复盘误判「P1 零损」)、gold 默认 0(白扔回合,扔掉跟踪层明明知道的「上回合 40 金其间只花 2」)、dead-reckoning 漂 18 回合才暴露。三个已落地提案各自打观察噪声补丁(01 ±1 容错/02 hp_conf<0.7 剔除/03 保守先验)= 同一问题的三份局部方案。

## Decision Drivers

1. 观测说谎是有档案的惯性事故(非理论风险),且发现通道全是人工复盘。
2. 前三轮(17/18/13 已落地 + 03/06/16 影子)把决策层换了/加了,输入仍「假装确定」——观测错一位,多层一起错且无层知道自己该不该信输入。
3. 与 obs_conflict(ADR-0154 族)分工清晰:那边管冲突仲裁留证,这边管值的分布表示。

## Considered Options

- **继续点估计+安全默认+个案时序规避**:拒绝 —— M19 类毒化在表示上合法就是 bug 温床。
- **全量信念栈(可靠性表+VoI+归因分案)**:M 级,依赖 telemetry join/probe 落地;按提案灰度路径分阶段。
- **v0 = BeliefStore 表示层**(采纳):消灭「默认值」这个概念本身,三个实案在表示上不可表达。

## Decision

1. 新增 `cw_belief.py`:`FieldBelief`(粗桶直方图 21 桶 + 证据链 [source/value/conf/ts/screen] + 未确证回合计数);
   - `observe`:高斯似然 × 先验(σ ∝ 支撑集宽 × (1−conf));sanity bounds = **支撑集硬截断**;
   - **读不到 ≠ 证据**:OCR 失败不产生证据,先验原样保留 + decay(方差↑)——M19 类毒化不可表达;
   - `track_transition`:过程模型(gold = 上回 − 花费),读不到时唯一推断来源(治「默认 0 白扔回合」);
   - `percentile`/`credible_interval`/`confidence`:悲观分位(hp 低置信消费)/可信区间(不可逆门 required certainty)/众数投影(GameState 兼容层,消费端零改)。
2. 字段独立(规模红线,拒绝联合分布);v0 三字段工厂(gold/hp/level),六字段扩展随消费端接。
3. 测试 6 条(K2 抗毒化回放核心):读不到保先验(hp 不跳 100)/跟踪推断(gold 不落 0)/观测收敛/置信衰减(dead-reckoning 表现为衰减)/分位与区间/支撑集硬截。

## Consequences

- 后续灰度(提案路径):可靠性表(telemetry join 混淆统计,lucky_star 类自动报警)→ 影子模式 K0(action-diff=0)→ 切 gold 单门(替代默认 0)→ 不可逆门(需 probe)。
- 与 obs_conflict 的接线点:obs_conflict 的 verdict 可作为 Evidence(source='仲裁')进信念链。
- 提案原文删档;决策单一源移本 ADR。
