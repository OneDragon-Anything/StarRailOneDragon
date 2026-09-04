# ADR-0142: 投资策略效果全量评估落地 —— 9 条经济效果错装类目归位 + 评估表建立

## Status

Accepted(2026-08-15)

## Context

- 用户指令(缺口2):315 条投资策略**先全量评估**(可量化的进策略,全面了解后治本改好),再动选卡逻辑。
- 子代理全量评估产出 `.debug/temp/currency_war/strategy_eval_full.tsv`(315 条:value_class 七分类 / quantizable 三档 / pick_priority 0-100 / quant_fields / notes),程序化解析注册表 + 逐条读 effect 原文。
- 评估发现 **9 条已装 EconomyEffect 的数值装错类目**:重复性效果(每次升级/每场结算/接下来N节点/进boss节点/按损血)被压成一次性 `instant_gold` → 经济分算错(一次性在选卡时点一次性体现,重复性应持续折算)。

## Decision Drivers

1. 数据正确性优先:注册表是策略层的单一真相源,装错类目比不装危害大(错误信号地基)。
2. 保守低估原则:战斗结算类条件金按保守值折算(如 每场最多4金 → 每节点1金)。
3. 反向激励隔离:损血换钱类(保险)建档但**不进经济分**(选卡评分不应鼓励损血)。

## Considered Options

- **A. 只修 9 条类目,新字段最小集** ✅(采纳):新增 5 字段(gold_per_boss_node / gold_next_nodes_amount+count / gold_per_level_up / gold_per_20hp_lost)+ 返利用现有 gold_per_three_5cost + 两条保守折 gold_per_node。消费侧在 _economic_value 按 20 节点摊销折算(利息同通道)。
- B. 等图鉴逐条核对后一起修:拖延,9 条的效果原文已实锤(doc 系带 content_id),无需等。
- C. 一步到位建全部 104 条 yes-new-field 字段:范围过大;战力类(power_pct/dmg_reduct 等)应先进战力评估通道而非经济,分批(ADR-0143+ 处理选卡价值分 pick_value)。

## Decision

1. EconomyEffect 新增 5 字段(语义见 docstring);aggregate_economy 聚合(amount/加法,count/max)。
2. 9 条归位:特战资金/+→gold_per_boss_node(11/7);长期主义/+→gold_next_nodes(7/9×3);节节高升→gold_per_level_up(1,2星角色单位奖励留 effect 文本);返利→gold_per_three_5cost(3,返利+ 对照组本就正确);保险→gold_per_20hp_lost(5,不进分);按劳分配/剩余价值→gold_per_node(1,每场结算金保守折算)。
3. _economic_value 消费:分期金摊 20 节点、boss 金 /9、升级金 ×5 次摊 20;gold_per_20hp_lost 故意不消费(注释写明)。
4. strategy_eval_full.tsv 为后续选卡价值分(ADR-0143)的评估基线:11 条 pick_priority≥60 白名单候选 + 42 条条件白名单(待 comp 匹配升档)。

## 后续(ADR-0143 范围,不在本 ADR)

- pick_value 进注册表 + decide_event 消费(基准 + comp 匹配 + HP 分档 + 时点修正)。
- 104 条 yes-new-field 高频字段(gold_per_boss_node 已建;power_pct_per_node / dmg_reduct_pct / lucky_rate_pct 等待战力通道)。
