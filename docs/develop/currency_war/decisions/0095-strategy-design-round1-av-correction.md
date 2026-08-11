# 0095. 策略方案定型轮 1:玩法修正(限时 AV / 掉血归因 / commit 渐进 / COMP 扩充)+ review HIGH 折进

- **Status**: accepted
- **Date**: 2026-08-11
- **原编号**: D-95

## Context
策略方案定型(做法一⑤工件 `4_策略设计/`)第一轮。两路输入:**review agent 揪 5 HIGH**(① COMMIT_ROUND=2 vs α(t) R_OPEN=2 早锁矛盾 / ② optionality 数据空 / ③ comp_viability 死函数 maybe_pivot 不调 / ④ spend_mode 0 次出现 economy_score 无 phase 钩子 / ⑤ 8/9 comp 无 level_plan)+ **用户审查给玩法认知修正**(限时 = 行动值 AV 非"非限时" / 掉血归因按成型度三分 / 转型只用于凑不齐 / 前期尽快 50 金少 D / 过渡阵容+通用角色是基础设施 / commit 渐进非死堆 / COMP 流派远不止 9)。

## Decision Drivers
- review HIGH 指向设计内部不一致
- 用户玩法认知修正(限时 / 掉血归因 / commit 语义等)须折进
- 设计先行(配置从设计派生,代码是后续)

## Considered Options
1. 直接改代码(optionality 接线 / economy_score 加 spend_mode 钩子 / comp_viability 接 maybe_pivot)—— 用户要先**定型设计**,代码改动排队
2. 保留"成型后掉血 → 转"—— 用户纠正(阵容收录即强度可信,成型后掉血 = 装备/星级不够 → 补强,非转)

## Decision(折进设计文档)
- **03**:加"掉血归因"框架(成型中 → 继续组建 / 成型后 → 补强不转 / 凑不齐 → 转;COMP_LIBRARY 收录即强度可信,观测判投资方向不推翻阵容)+ 修转型信号 3(成型后掉血不转,仅未成型+濒死才保命转)。
- **14**:P1 前期改"尽快 50 金、少 D 除非过不去、过渡/输出核心稳血存钱" + §4 把 transition_chars/shared_chars/通用过渡角色标为"灵活+存钱+组建支撑"基础设施(当前数据空,待调研补)。
- **12**:commit 语义改"定方向 ≠ 死堆,组建渐进 + 过渡支撑" + 防散放宽(组建期放过过渡/通用辅助,只拒别的成型方向)。
- **currency_war.md**:限时"非限时"误记 → "有限行动值(AV)"(米游社 content/6564)。
- **COMP 扩充调研**(落 `4_策略设计/流派扩充调研.md`):9 新流派 + 通用角色清单(符玄/知更鸟/花火/爻光/缇宝…)。🟢 先入,🟡 待米游社逐角色攻略直读升核。
- 限时下输出低 = 超时扣血 → "输出能力"观测降为 diagnostic(hp_trend 已隐含主信号);扣血公式 + 结算字段🔴待实机核。

## Consequences
- 正向:设计文档自洽 + 玩法认知修正;限时机制(AV)认定纠正双源漂移(`data/gameplay.md:13` 记对了)。
- 负向:代码改动排队(optionality/economy_score/comp_viability/level_plan 待实现,清单记)。
- 边界:本轮只改设计 + 调研;轮 2 review 待跑确认折进后无新 HIGH。

## Links
- `· docs/develop/currency_war/strategy/03_comp_planning.md` / `12_comp_commitment.md` / `14_phase_skeleton.md`
- 关联 D-NN:D-94(14 单源基础)、review round1(5 HIGH)、`4_策略设计/流派扩充调研.md`
