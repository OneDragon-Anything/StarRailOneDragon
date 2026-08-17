# ADR-0178: 预测台账层 v0 落地(redesign 40 号处置)——前向预测登记+记分+保真度分区

## Status

Accepted(2026-08-17,策略优化会话;40 号核心件,消费端门为增量)

## Context

40 号诊断:系统每回合产出前向预测(DP 期望轨迹/池信念面命中率/成本曲线/伤害预算)但从未落盘
从未对答案——全系统唯一未开采的免费校准数据(forecast scoring)。物理原语位置单源(sim_env
同源 import cw_horizon)但「单源≠被测量」:函数形式错(缺耦合项/形状错)23 号定向常数审计
原理性测不出。六个重推理端(24 搜索/28 证明/14 反事实/33 定价/34 D 臂/38 会话)全站在
前向模型上,暴露面无人计量。

## Decision Drivers

- 最便宜的模型校准通道:预测-实现差只隔一行 join
- 防混杂毒化(ADR-0177 confounded 语义同款纪律)

## Considered Options

1. **纯函数四件套先行(选)**:Ledger 登记/reconcile 记分/FidelityMap 分区/residual_regression
   提名,消费端门(24 防钻营/34 分区)增量接;
2. 一步到位含 telemetry 第四路 predictions.jsonl 接线——依赖各引擎接缝改造,先立地基;
3. 只做全局 sim-vs-实测对照(34 号既有)——一把只会全关的闸,无分区粒度。

## Decision

选 1:`cw_pred_ledger.py` v0——

- ``Prediction``(点/区间,零新计算纪律)+ ``reconcile``(误差=actual−point、区间命中判定,
  实现值缺失如实跳过);
- ``FidelityMap``:分区(机制族×位面×等级档三段)聚合 mae/bias/命中率 + ``dark_regions``
  (n=0 暗区=39 号探针靶单);
- ``residual_regression``:残差×协变量 OLS(|t|≥2 显著才提名,欠功效/方差退化返回空——
  不误报;se≈0 完美拟合 t=inf 处理);
- J0 自洽锚切片(测试):幅度错→分区 bias 检出;缺耦合项(残差×连胜线性)→回归提名;
  白噪→零误报。

## Consequences

- 40 号处置完成(v0 地基),提案文件删档;
- 预测供给接线(DP 轨迹/16 面命中/17 成本导出)与 predictions.jsonl 第四路落盘挂 telemetry
  批次;消费端门(24 防钻营优先)增量;
- 与 23 号闭环:残差提名 → registry audit backlog(provenance=observational-residual);
- 测试 +7。
