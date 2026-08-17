# ADR-0205: 投资效果全量调研落地(纠错 + v2 字段 + 台账/难度路由)

## Status

Accepted(2026-08-17,策略优化会话;接法:effects_from_strategies 已备,生产 session 接线
与 47 号切流批次)

## Context

strategy/18 全量调研(335 策略 + 83 环境)发现:注册表两张在用卡效果错算(伟大征服漏
「难度+连胜」与 +12XP;远见漏「棱彩流+难度豁免」);另有 17 条 API 文本明数值的效果
零建模。API 裁定(用户):desc 没说的数值不建模、不实机查。

## Decision Drivers

- 在用卡错算直接污染在跑的局(选卡分系统性偏)
- DP(v6 0.3s)已能按台账定制解——数值进注册表即可被消费

## Considered Options

1. **注册表扩字段 + 台账路由(选)**:EconomyEffect v2 加 13 个语义字段(带配对
   触发条件);effects_from_strategies/conditional_effects_at/gold_at_level_effect
   三个路由;DifficultyAccount.from_strategies 难度建账;
2. 直接在消费端散读注册表——字段语义散落,双源;
3. 只修纠错不动新增——调研白做。

## Decision

选 1:

- **纠错**:伟大征服(win_reward_mult=3 + difficulty_per_streak=1 + xp_instant=12)、
  远见(instant_gold=15 + future_quality_upgrade='prism' +
  difficulty_inflation_exempt=True)——API 原文为证;
- **新建 12 条**(73→85):成长基金/成长的快乐/超发货币/固定理财(+)/经验到账/
  孪生素数/狸财经狸/不等价交换/星际和平保险/简单模式/难度修改器/退化(难度并入旧条);
- 台账路由三口:静态路由(cap/单击/乘子/日程/息/刷价);等级条件突变(成长的快乐
  8 级起);等级触发日程(成长基金 40@lv9);
- 难度账本 from_strategies:静态 Δ 进 augments,per_streak 走动态项
  (简单模式+难度修改器+streak3 → total=100−7+3 实测);
- 放弃(API 裁定):品质通胀/odds 概率族/礼盒内容/投影仪分布。

## Consequences

- 持卡组合定制解的数值链路全通(注册表→路由→台账→solve(ledger));
- 行为条件流(存款回报等)与期权类(期货系)留 33 号框架;生产 session 接线挂
  47 号切流批次(基线解仍为生产现状,零漂移);
- 测试 +5(纠错断言/路由/难度账本);strategy/18 §8 路线 1-3 完成。
