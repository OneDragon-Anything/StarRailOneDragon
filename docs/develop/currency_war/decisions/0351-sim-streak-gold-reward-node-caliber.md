# 0351 sim 连胜金口径修正(奖励/补给轮不计数不发金)

- 日期:2026-08-26
- 状态:accepted(直接落地)
- 关联:combat.md §4(口径裁决)、P6(口径声明段)、批⑱ streak_combat_only_income 检查器

## 背景

奖励/补给节点的连胜语义已实机裁决(2026-08-26,双局实证):

- **run13 r2 奖励结算屏 = 基础 5 + 连胜×0**:r1/r2 两奖励节点全过后连胜计数仍为 0 → 奖励节点**不计连胜数**;
- **run15 r3 战斗胜利结算屏 = 基础 5 + 利息 3 + 连胜金 1 = 9 金整**:r1/r2 奖励轮后 counter0 的战斗轮照发 `STREAK_GOLD_TABLE[0]=1`(表值与实机互证)→ 战斗轮发金语义不变,**奖励轮无 streak 分量**。

裁决前的 sim 折中口径:奖励/补给轮的收入照发 `streak_gold(streak)`(发金侧错,+1 金/奖励轮量级);且 sim 内部 streak 计数在结算段按 `delta>0` 无差别累积——奖励/补给轮 Δ 恒 +2 也会推进计数(计数侧同样偏离裁决;`_combat_streak_by_round` 重放口径才是对的,两者常年不等、检查器只并列披露)。

## 决策

1. **收入段**(cw_sim 备战期收入分解):奖励/补给轮 `income.streak = 0`;战斗/遭遇/boss 轮维持 `streak_gold(streak)`(单一源 cw_economy)。
2. **结算段**(cw_sim 轮末 streak 更新):仅战斗类节点(battle/encounter/boss)`delta>0` 计连胜、否则归零;奖励/补给轮**不动 streak**。`session.last_streak` 写入语义不变(生产 = 结算「连胜×N」写 session,奖励轮结算屏恒 ×0/不变,与生产一致)。
3. **检查器收紧**(cw_sim_checks.check_streak_combat_only_income):从「双口径并列披露(violations 恒 0)」改为断言——**奖励/补给轮 `income.streak != 0` 即违规**;combat-only 重算和并列保留为披露面(delta>0 = 计数侧回归的哨兵)。

## Considered Options

- 只修发金、不动计数(任务书初版设想「计数侧对」)——否决:实测 seed 0 账本 r3 收入 streak=2 来自 r1/r2 奖励轮胜,计数侧实际在动;只清发金会让「奖励轮后的首个战斗轮」仍按虚高 counter 发金,run15 r3(counter0→1 金)直接证伪。
- 顺带改 `STREAK_GOLD_TABLE[0]=0`——否决:run15 实证 counter0 战斗轮发 1 金,表值 49/49 样本(ADR-0262)与实机互证,不动。
- sim 全局改读 `_combat_streak_by_round` 重放——否决:重放是账本后验近似(delta≥0 与 sim delta>0 在 Δ=0 战斗轮有残差),sim 内部计数就地修才是单一源。

## 后果

- sim 金轨迹整体下移:奖励/补给轮 −streak 金,且奖励轮后的战斗轮按真实(更低)counter 发金;策略决策受金位变化间接影响(利息档边界帧可能翻转),属口径修正的预期效应。
- 批⑱检查器使命完成(「等待裁决」的披露面 → 裁决后断言),去门变异(奖励轮发金回潮)必须涌现 violations。
- 实机对局(run15 在飞)不改运行时行为——本批只辖 sim 收入模型与检查器,生产发金读游戏真值结算,无生产代码变更。
