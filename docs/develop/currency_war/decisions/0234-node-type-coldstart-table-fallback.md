# ADR-0234 结算 node_type 首节点冷启动兜底(开局槽序表)

## Status

accepted(2026-08-22;r362;用户点破「1-1/1-2 是奖励,记录全普通战斗」;遥测审计进行中的第一修复)

## Context

局47 outcomes.jsonl 的 r1-r4 node_type 全记「普通战斗」,而 nodeseq 首帧(12:01)明示 slot0/1=reward——用户看遥测即发现。根因:**首节点的类型在它自己的备战期从没被读到**——r1 备战期 nodeseq 首帧常 skip(非 clean 帧),upcoming_types 空 → 左移推断无值 → node_type_current=None → battle_loop 回退 `'普通战斗'`(None 语义被默认值伪装成真值,r265 链条的开局盲区)。

## Considered Options

1. 备战期重试 nodeseq 到成功:治本但备战有倒计时,重试预算与 gate 语义纠缠。
2. **结算时查 plane_node_table 兜底**(选):r306 已存的开局帧完整槽序——slot i ≈ 该位面第 i+1 节点(reward/reward/battle/battle/supply… 实证稳定,变异位仅 slot5/6,前 4 槽查表恒准);current 无值时按轮次查表。
3. 结算屏 OCR 推断:r260 已弃(二手推断误中'基础奖励'实锤)。

## Decision

选 2。`_node_type_from_table(session, plane, round)` 静态方法:表空/越界 → None(不伪装);锁测试 3 条(r1/r2=reward、r5 supply/r9 boss、越界/表空 None)。已知边界:slot5/6 变异位查表可能错(策略改节点),但 current 直读/左移在非首节点基本覆盖——本兜底只补首节点冷启动。

## Consequences

- 优先级链:boss OCR > current(左移优先) > **槽序表兜底** > 普通战斗——首节点 reward 记录从此正确。
- 遥测全面审计(子代理 80b8a6c5)进行中,同类问题(默认值污染/首帧缺口)按审计结论批量处理。
