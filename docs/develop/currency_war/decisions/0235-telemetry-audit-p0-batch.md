# ADR-0235 遥测审计 P0 批修复(node_type 词汇统一/槽序表写入/同轮左移锚定/abandoned 兜底)

## Status

accepted(2026-08-22;r363;子代理全面审计 80b8a6c5 发现清单 P0 组)

## Context

用户看局47 遥测发现 node_type 全错(1-1/1-2 奖励记成普通战斗),发起全面审计。P0 级发现:①词汇表三源混写(全量 829 行 8 种值:中文兜底/英文 token/OCR 中文并存,下游 EXPECTED_DROP/sim Δ池/视图按错误桶聚合);②**r362 修复是死码**——plane_node_table 全仓无写入者;③同轮多次 probe 左移推断超前一位(开店/关店/重开时 current 写成下一节点);④中止局无 runs summary(近 6 局实锤,'abandoned' schema 定义了但无写入方,跨局统计分母偏)。

## Decision

1. **词汇统一**:`_normalize_node_type` 静态映射(英文 token/OCR 中文/旧兜底 → EXPECTED_DROP 键域中文),battle_loop 出口单点归一;未知透传不吞。
2. **槽序表写入端**:prep_director._probe_node_type 首帧(current+upcoming+past 按 idx)存 plane_node_table——r362 兜底的消费端从此有数据。
3. **同轮左移锚定**:nodeseq_probe_anchor=(plane,round);同轮重复 probe 不重做左移(防超前);current 直读降为首帧兜底(current 无值时)。
4. **abandoned 兜底**:loop 顶检测 is_context_stop + 未写 summary → 补记 result='abandoned'(gold 轨迹 recorder 内存带);正常终局置 _summary_written 跳过。

## Considered Options

- P1 组(gold_trajectory 多采样/去重取首帧/refresh 快照假金/level 非单调/board≠板深)与 P2 组:本批不修——按审计优先序 1/2/6 先行,P1 组下一批(判读视图地基,修法需视图侧配合改动)。

## Consequences

- 下局起 outcomes.node_type 全中文标准词;runs.jsonl 覆盖中止局;**历史数据的混合词汇在读侧兼容**(sim live_delta_pool 已有英文映射,视图按需补)。
- 审计白名单(hp_after/plane/round/actions 等可信字段)进 skill telemetry-reading。
