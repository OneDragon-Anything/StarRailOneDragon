# ADR-0252 开局轮装备 hold:gen 散件攒到战斗轮再穿(r388)

## Status

accepted(2026-08-22;r388;commit 5c6a2251;用户 live 质问驱动)

## Context

用户 live 质问「1-2 就乱装备」,实证:r1-r2 三月七独占流星飞翼+轮滑鞋两件。根因有两层(commit message 记载):

1. r70 过渡期持有条件 `0.0 < form < COMMIT_FRAC` 在开局 form **恰为 0** 时为 False(严格大于)——hold 分支被绕过,gen 散件照穿给唯一在场者;
2. r1-r2 是奖励节点,穿着零战斗变现;阵容未起步时分配语义退化成「谁在场谁独占」。

## Considered Options

1. **把 r70 条件改为 `0.0 <= form`**:只修边界符号——但 r1-r2 奖励轮零战斗变现的问题仍在,穿与不穿无差别,语义没对齐轮次性质。否(动机推断:commit 选择了按轮次而非 form 边界处理;依据=修法落点是 `_opening_round` 而非 form 比较)
2. **开局轮(P1 r≤2)强制 `_transition_hold = target_comp 存在`**(选):key_equips 命中件照穿(命中即阵容意图明确),gen 散件攒到 r3 战斗轮再穿。与 r70「P1 白板也该穿」不冲突:白板 8 战指的是 r3+ 战斗期,不含奖励轮。

## Decision

选 2。`_opening_round = plane==1 且 round_num<=2` 时覆盖 `_transition_hold = _tgt_comp is not None`;r3+ form=0 走 r70 原逻辑不变。

## Consequences

- 开局奖励轮 gen 散件不再乱穿;key_equips 命中件仍即时穿(阵容意图明确的件不延误);
- r70 语义边界澄清:其「白板也该穿」限定 r3+ 战斗期;
- 锁测试 2 条(开局 hold / r3+ form=0 沿 r70);equip 相关 88 绿;全量 1036 passed;
- 反向形态(hold 过矫白板挨打)由 ADR-0254 的 check_equip_worn_in_battle 常态拦截。
