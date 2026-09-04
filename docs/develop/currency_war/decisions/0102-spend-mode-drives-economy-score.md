# 0102 — spend_mode 驱动 economy_score(节点节奏 → 经济评分档位)

- **Status**: accepted
- **Date**: 2026-08-12
- **Related**: 14 §2.2(spend_mode→economy 映射表)/ ADR-0097(node_plan 接线轮,本条补其「剩余 spend_mode→economy_score 权重」)

## Context

`NodeGoal.spend_mode`(节点节奏 gate:saving/interest/level/hold/allin/adaptive;14 §2.0)定义了每节点的经济档位,
但接线不完整:**`_maybe_sell_for_interest` 用了 spend_mode**(allin/level 跳卖息,cw_decisions:732),而 **`evaluate`
→ `economy_score` 用的是静态 `config.economy_mode`(用户偏好常量)**,不随节点 spend_mode 变。

→ 节点节奏(saving 攒息 / level 升人口)没驱动主经济评分。P1 早期(saving,主目标尽快 50 金)与 P2(level,升人口)
的 economy 权重无区分 —— 设计 14 §2.2 明确 spend_mode 是「节点档位 gate(主),config 是偏好(辅)」,但实现只接了一半。

## Decision Drivers

1. **设计 spec 已定**(14 §2.2 映射表 + §节点表):spend_mode → economy_score 权重 + _maybe_sell_for_interest 两消费者。
2. **纯结构接线,非权重调优**:映射 spend_mode→现有 economy_mode(interest_first/rush_level/adaptive 都是 economy_score 已有处理),
   不引入新权重值(权重值留 stage6 实跑校准 = 调优,最后)。
3. **与 _phase_weights 正交无冲突**:economy_mode 调 economy_score **内部**(利息/等级相对权重),
   _phase_weights 调 economy_score **outer 乘子** we(HP/plane 降权)。两者复合,不双计。
   allin(P3)的「economy-low/质量优先」语义由 _phase_weights plane3 `we=0.3` 处理,非 economy_mode(故 allin→adaptive neutral)。

## Considered Options

- **A(选)**:加 `_economy_mode_for(state, config)` 映射(saving/interest→interest_first / level→rush_level / hold/allin/spend→adaptive /
  adaptive→config 偏好辅),evaluate 用它替 `config.economy_mode`。**最小结构接线,复用 economy_score 现有档位处理**。
- **B(否)**:扩 economy_score 加「allin 质量优先」新档位(economy 权重最低)。否:allin economy-low 已由 _phase_weights plane3 we=0.3 覆盖,
  加新档位 = 与 _phase_weights 双计;且无实跑数据支撑新权重值(凭猜违反「值在代码待校准」)。
- **C(否)**:不动(config.economy_mode 静态)。否:设计 14 §2.2 明确 spend_mode 该驱动 economy;节点节奏不区分 economy 违背设计。

## Decision

选 A。`_economy_mode_for`(cw_decisions)+ evaluate L307 用它。映射:

| spend_mode | economy_mode | 理由 |
|---|---|---|
| saving / interest | interest_first | 攒息 snowball(P1 早期主目标尽快 50 金) |
| level | rush_level | 弱化守息 + 强化等级(P2 升人口) |
| hold / allin / spend | adaptive | neutral;economy-low(allin)由 _phase_weights plane3 we=0.3 处理 |
| adaptive | config.economy_mode | 用户偏好辅 |

不改角色级/权重值(stage6 实跑校准);不改 _phase_weights(正交)。BattlePrepCycle 验流程不崩(comp 选择行为变化最小:
saving 节点 economy 权重略升、level 节点略转等级,均在 economy_score 现有档位语义内)。
