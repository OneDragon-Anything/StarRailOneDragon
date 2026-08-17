# ADR-0177: 机制常数核对器完整落地(redesign 23 号处置)——首份审计报告 + 实测升级

## Status

Accepted(2026-08-17,策略优化会话;23 号 J2 判据兑现)

## Context

ADR 场景:15 个影子模块共同消费的「游戏物理常数」地基此前零治理(cw_mechanism.py v0 已收编
首批 14 个常数,但核对器只有 SHOP_REFRESH_COST 一个且 docstring 承诺的其余三个未实现)。
23 号 §1 实锤:SHOP_REFRESH_COST=2 纯猜从未校准;XP_CLICK_COST 曾因取值过贵致 DP 全路径值 0
坍塌(ADR-0155 V1.0 事故)。

## Decision Drivers

- 23 号 J2 判据(预注册可证伪):「XP 系 verified、refresh/level 金费首次有测量或暴露观测缺口」
- 判定语义诚实:混杂未控的观测不得毒化注册表(不写假 refuted)

## Considered Options

1. **补齐四审计 + confounded 语义(选)**:执行侧归因(refresh 已有)+ xp/base/interest 三审计,
   观测窗混杂(boss+2/连胜未观收入、快照口径差)时判 confounded 而非 refuted;
2. 只跑既有单审计 → J2 判据不完整;
3. 强行 verdict 二值 → 混杂假阳性毒化注册表(拒绝)。

## Decision

选 1,三件:

- **cw_mechanism_audit.py 补齐三审计**:`audit_xp_per_buy`(同节点行对 Δxp/买数;主峰 0=快照
  已含买牌 XP 的口径差、次峰=真值 → confounded)、`audit_base_income`(跨节点零花费零连胜窗,
  est=Δgold−interest;整体上偏=未观收入混入 → confounded)、`audit_interest_threshold`
  (gb≥50 封顶段命中;正偏差主导 → confounded)。verdict 词表:consistent|refuted|confounded|underpowered。
- **首份审计报告(6824 行 decisions.jsonl 实跑)**:
  - SHOP_REFRESH_COST:est=2,n=1098,**consistent**(主峰 2×974;次峰 0×95=免费刷策略、1×29=减费,均可解释);
  - XP_PER_BUY:confounded(主峰 0×523=口径,次峰 4×22=真值观测,与注册值 4 相符);
  - BASE_INCOME / INTEREST_THRESHOLD:confounded(连胜/boss 未观收入混入 streak=None 观测窗;
    **暴露观测缺口**:streak 接线后收窗可判)。
  - J2 预注册预测兑现:refresh 首次有测量(且实测确认)、XP 系次峰佐证、base/interest 显式缺口。
- **注册表升级**:SHOP_REFRESH_COST unverified→verified(provenance=telemetry 实测众数,n=1098)。

## Consequences

- 23 号处置完成(注册表 v0 + 核对器 + 首份报告),redesign 提案文件删档;
- 观测缺口清单(streak=None 行对、xp 前值未记)成为采集接线靶单(喂 40 号预测台账/39 号探针);
- 下批可测(需 outcome 流/gold 逐动作轨迹):SELL_REFUND、SHOP_ODDS_TABLE、HP_LOSS_PRIOR;
- 测试:+7(audit 判定语义)+ 注册表断言更新(总 13 过)。
