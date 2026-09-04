# ADR-0262: streak_gold 连胜金换实测真值表(表化 + 边界锁)

- **Status**: accepted
- **Date**: 2026-08-24

## Context

连胜金(每节点收入 = 基础 + 连胜 + 利息)此前在 `cw_economy.streak_gold` 以
if/elif 四档近似实现(r305 真值接入)。视觉 worker 已从奖励弹窗 49/49
真实样本确立真值表(证据:`docs/game/currency_war/research/economy.md`
§10.1 + `.debug/temp/currency_war/cw_dev/cw_reward_判读.md`):弹窗底部为
**固定规则表,与对局状态无关**——连胜 0-1→1 金 / 2-4→2 / 5→3 / 6+→4。

数值语义 r305/r307(commit de447f0b)已与真值一致(sim 收入模型与
line_strategy 决策 EV 共用该单一源);本决策把**形式**收敛为显式
`STREAK_GOLD_TABLE` 常量(数据即代码,档位一目了然),并补齐边界锁。

## Considered Options

1. **真值表常量 + 表尾截断(采纳)**——`STREAK_GOLD_TABLE: tuple[int, ...]
   = (1, 1, 2, 2, 2, 3, 4)`,索引=连胜数,`min(streak, len-1)` 越界取末
   值(末位即 6+ 档);`max(0, ...)` 保持负值输入与旧实现同返首档。
2. 公式继续(if/elif)——数值等价,但档位边界藏在比较链里,读表需推理;
   后续若游戏调档,改表比改三段 if 更不易错。
3. 查表 + 外推(如 streak>6 线性递增)——无证据支撑外推语义,弹窗明示
   6+ 封顶;引入未观测行为,拒绝。

## Decision

`cw_economy.streak_gold` 改查 `STREAK_GOLD_TABLE`(常量 docstring 注明
实测来源与样本量);消费点行为**零变化**(cw_sim 收入层、line_strategy
决策 EV、既有锁均沿用同一函数)。锁测试补 6+ 边界(streak=9)与
「常量逐点一致」守卫(`test_cw_r305_reward_data.py`)。

## Consequences

- 消费点(cw_sim `income.streak` / line_strategy `_tier_now`)数值不变,
  sim 分布与遥测对账不受影响。
- 后续弹窗规则变更(版本更新)时只改常量一处,边界锁会精确指出哪档变了。
- 残余近似:`BASE_INCOME=5`(基础奖励随节点变,见同测试文件 TODO)不在
  本决策范围。
