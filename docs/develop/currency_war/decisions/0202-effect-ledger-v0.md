# ADR-0202: 既持效果台账 v0 落地(redesign 53 号处置:现金日程+机制突变+免费额度)

## Status

Accepted(2026-08-17,策略优化会话;DP 注入改造/boss 位精确标注/守恒对账验证层为消费批次)

## Context

53 号诊断(用户发起增补轮):持有效果的确定性现金流被摊平成等效息——时机信息在表示层
被扔掉(gold 43 时下节点 +7 跨息档 vs gold 20 时分期是预支流动性,摊平给同一答案);
DP effect-blind(买断制照样攒息、连胜 ×3 照 ×1、商业间谍成本曲线不动);效果表零验证通道。
现成活伤:_want_level_up 简算 `_click_cost=4+level` 与 xp_click_cost 三处口径不一致。

## Decision Drivers

- 效果=合同:持有效果的每一局都在验证它
- 三算例(商业间谍/长期主义/买断制)是现状算不出、台账后 DP 直接涌现的方向——离线可验

## Considered Options

1. **三层台账+注入式消费接口先行(选)**:EffectLedger(calendar/mutations/budgets)+
   四象限分类路由 + node_income_with/interest_with/level_cost_with 注入接缝;
2. 直接改 DP 主循环——D1 网格约束(金步长 1)与去双计迁移随批次;
3. 不做——效果建模的三处结构性盲区继续。

## Decision

选 1:`cw_effect_ledger.py` v0——

- **三算例全过(测试)**:①商业间谍单击 4→3 → 30 击成本 120→90(−25%);
  ②长期主义 next_nodes 日程:gold 43+12 ≥50 跨息档(无日程 48 不跨)——**时点价值
  涌现**,摊平分结构上给不出;余期外为 0;③买断制 cap 0 → interest 恒 0(死资金
  矛盾的解),利息上调 cap 10 对拍;
- 伟大征服 ×3 乘子进收入(现状 DP 照 ×1);特战资金 boss 位日程(粗锚 8/17/26)。

## Consequences

- 33 号层 3(义务 DP 重解)的突变基底就位;roll_affordable/_refresh_cap 读余量的
  点消费改造挂批次;守恒对账(验证层)挂 telemetry 批次;
- **v1 扩展(同日晚,全量效果扫描)**:①overlay 已有字段的路由补全
  (surprise_every[共存取密]/gold_per_three_5cost/xp_per_refresh/xp_per_node/
  free_refresh_burst);②**环境侧首破**(ADR-0144 挂账缺口):ENV_ECONOMY_EFFECTS
  按官方效果原文落三条可数值化环境(增发货币[位面首节点日程]/长线利好[30 刷后价 1,
  与 38 号跨线投资联动]/蓝海占位),build_env_ledger 入口;未覆盖环境=空台账=现状。
  环境侧 83 条中其余经济类(二手市场 20 刷返金/经济过热奖励节点替换等)按「机制可
  数值化优先」逐批进(战力/规则类走原通道不进台账);
- **v2 根治(同日「治本推进」)**:③**DP 主循环注入**(53 号盲区 2 根治):solve(ledger)
  参数化——收入/息/成本全走台账突变视图,None=现状零漂移(抽查 5000 姿态 diff=0);
  ④**D1 金步长 5→1**(53 号网格约束原文执行):状态空间 620k→3M,求解 ~60s,日程小额度
  不再被量化蒸发;涌现验证保持(survived/band 0.74/level 8);⑤**roll_affordable 点消费**
  读免费额度(加油站类策略下期望刷价摊销;无 active_strategies=旧行为);
  ⑥集成涌现测试(slow 标记):商业间谍 V 差 >5% 状态面+姿态差 >100;买断制 V 差 >30%;
- **v3 解缓存(同日,「67 秒」质询)**:solve_cached + ledger_fingerprint ——
  ①**重算触发面**:指纹只含改 DP 世界的字段(calendar+mutations),overlay 73 条中
  仅 ~11 条(息 cap/单击价/连胜乘子/节点收入类)会变指纹,52 条纯时点金(instant_gold)
  命中即免重算——典型一局需重算 0-1 次;②**三层缓存**:进程内 memo(0s)→ 盘 pickle
  (~6s,232MB,按「指纹+源 mtime」键,改源自动失效)→ 冷解(~67s);
  ③生产路径 _solved() 换 solve_cached——MCP server 重启后首个查询从 67s 降 ~6s,
  同持卡指纹跨进程全局只解一次。
- 53 号处置完成(v0-v3),提案文件删档;测试 +11(effect_ledger 7+集成 2+缓存 2)。
