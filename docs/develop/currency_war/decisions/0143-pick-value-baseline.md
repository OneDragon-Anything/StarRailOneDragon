# ADR-0143: 选卡价值基准分(pick_value)——评估表进注册表 + decide_event 消费

## Status

Accepted(2026-08-15)

## Context

- ADR-0142 建立了 315 条全量评估表(strategy_eval_full.tsv),但只落地了经济子集的类目归位;选卡打分仍是「白名单 > comp 匹配 > 裸品质先验(棱彩50/金30/银10)+economy+20」——同品质内无先后(鲜血阶梯 75 分与数值碾压 35 分同起点),评估表的价值分没进决策。
- 环境侧 83 条评估进行中(env_eval_full.tsv,子代理),产出后走同一模式接入。

## Decision Drivers

1. 评估分已含品质+经济价值信息 → 消费时防双计(economy+20 只在回落路径加)。
2. OCR 形变名(•↔·)不能丢分 → pick_value_of 精确名优先 + LCS 兜底(同 _option_rarity 口径 0.6)。
3. comp 匹配仍最高优先(45×N+20 压倒一切)——成型加速 > 静态基准分。

## Considered Options

- A. pick_value 进注册表字段 + decide_event 替换裸品质先验 ✅:单一源(注册表),评估表为派生数据源标注;测试语义同步更新。
- B. 白名单扩到 11 条 ≥60 候选:只解决头部,300 条长尾仍裸先验;且白名单(config)与注册表双源漂移。
- C. 等环境侧评估一起接:策略侧数据已齐,环境侧走同模式无额外设计,不必串行。

## Decision

1. `InvestmentStrategy.pick_value: int = 0`;文件尾 PICK_VALUE 表(315 条,TSV 派生)replace 合并;codex 6 新条目未评估(0 = 回落品质先验,与旧行为一致)。
2. `pick_value_of(name)`:精确名 → LCS(0.6)→ None。SURVIVAL_PICKS(10 条恢复/免战/降难度)低血 +15 钩子。
3. decide_event:comp 命中 > 评估分(替裸品质先验;economy+20 仅回落路径) > LCS 裸评估分 > 未注册 0;品质难度惩罚(ADR-0141)与 HP 分档叠加不变。
4. 行为变化(测试实证):「免费午餐(银,50)」胜「乱成一锅粥+(彩,45-12=33)」——分数为纲替品质为纲;高评估彩(鲜血阶梯 75)仍压过惩罚,惩罚语义(调相对序非禁选)不变。

## 后续

- 环境侧 env_eval_full.tsv 产出后:InvestmentEnv 加 pick_value + env 选卡消费(局中环境出现时 comp 已定,可加 comp 匹配修正)。
- 战力类 yes-new-field(104 条)进战力通道(evaluate 的战力评估),非本 ADR。
