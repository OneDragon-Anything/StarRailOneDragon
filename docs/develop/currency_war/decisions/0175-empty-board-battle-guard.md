# ADR-0175: 空板出战守卫(强度表首个消费)

## Status

Accepted(2026-08-17,r23)

## Context

15 号敌情强度表(r22 落地)实测发现 P1 内部强度极不均匀:p1-1 掉 25.5(p90 29)/p1-7 掉 24.1/
p1-9 boss 21.7,而 p1-2/p1-8 奖励节点 0——先验平滑曲线与实测锯齿差异显著。54 局 decisions 实证
p1-1 出战分布含 **(lv4, dep=0)×5 空板出战**:空板打高强度节点直接掉 1/4 血,是低血进 P2 的
最上游根源。

## Decision Drivers

- 空板出战无任何正当场景(bench 有人=部署失败,应重试而非出战)
- 强度表→策略消费的闭环需要首个落地件

## Considered Options

1. 只在 p1-1 等高强度节点开守卫——节点强度是统计量,单点开关过拟合;
2. **全节点空板守卫(选)**:板上 0 人且 bench 有人 → 回 RunDeploy 重试;
3. 校验放 Director 执行层——策略层拦截更早,避免无效 StartBattle 消耗步数。

## Decision

选 2。重试上限 2 次(prep_phase_retry,防部署持续失败时 phase 死循环;超限放行交 Director
stall 兜底);环入口 retry 清零(与 defer 同宿主模式);板上有人不拦截。

## Consequences

- 5/54 局的空板出战消除;正常局零影响(有人即放行)。
- 依赖 obs.deployed_chars/bench_chars 的 tracking 质量(环入口 heavy 读);tracking 断链时
  最坏行为=多重试 2 次,无死循环风险。
