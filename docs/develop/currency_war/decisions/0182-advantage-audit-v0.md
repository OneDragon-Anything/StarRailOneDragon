# ADR-0182: 决策级优势审计 v0 落地(redesign 42 号处置:T2 一步差+覆盖记账)

## Status

Accepted(2026-08-17,策略优化会话;T1 自然变异/13 号 J1 双通道对拍为 v1 消费端批次)

## Context

42 号诊断:切流证据 = run 级 A/B(~50 局/比较),每局几十个决策点只用了 1 bit 胜负;
「影子说的更好,结果上到底好不好」从未被计算。确定性贪心下 IS(重要性采样)失效,
需要换估计器(T2 把模型暴露压到一步)。

## Decision Drivers

- 影子切流队列(15 模块)需要决策粒度证据,run 级 A/B 吞吐不够
- J0 注入恢复为主张生死判据(不过线降级 diff+覆盖登记层)

## Considered Options

1. **T2 值函数一步差 + 覆盖记账(选)**:A = V(影子备选后继) − V(实际后继),V=18 号
   P(win) 生存换算;live=None 语义=「该做没做」的自然对照;
2. 直接做 T1 自然变异回归——需状态指纹分桶×多臂语料,v0 数据面未备;
3. 局级 rollout(14 号领地)——模型暴露大,拒绝。

## Decision

选 1:`cw_advantage_audit.py` v0——

- ``advantage_one_step``:simulate 一步(不动作=原状态)→ P(win) 差;simulate 异常显式
  不可计分(非静默 0);金差暂不进 V(生存单目标,v1 消费 35 号价格);
- ``audit_decision_class``:决策类×位面×等级档聚合,verdict=positive/negative/noise/
  uncovered(欠功效如实),noise_floor 参数化;
- ``CoverageLedger``:不可测原因显式路由(no_shadow→39 探针/sim_untrusted→40 dark/
  no_variation→29 实验需求单)——证据缺口地图;
- **J0 注入恢复过**(测试):「该升级不升」类劣化(xp 门槛-1 真实机制)→ positive 恢复
  (mean>地板且 CI 下界过);clean(同动作)→ noise 零误报;覆盖路由三向验证。

## Consequences

- 42 号处置完成(v0),提案文件删档;
- T1(自然变异条件化)与 13 号 38 例金零进展的双通道对拍(J1)挂消费端批次——需影子栈
  离线重放管线(13 号回溯审计同法);
- 与 40 号上下游:T2 计分门消费保真度分区(v0 位面档近似);
- 测试 +6。
