# ADR-0208: HORIZON_SEAM 切流执行(DP 姿态替换静态节点表)

## Status

Accepted(2026-08-18 r16 执行;回滚 = HORIZON_SEAM_ACTIVE 改 False 一行)

## Context

六连败(A8)同模式:P1 boss 稳定损 20-36 血 → P2 残血开局即崩。r11-r15 五轮诊断
证据链:①160+ 局 decisions 对拍,「表 hold→DP level」在 P1-r7/r9 高金段系统性
分歧——静态表节奏结构性慢一档;②live plan 对拍器实证 live r8 全刷牌不升 vs 复现
LevelUp×10;③r8 经济投入已尽力(gold 58 全花),强度差距根子在 P1 全程等级/星级
积累;④DP 姿态语义逐段核验(极早期 lv3→4 便宜早升合理;P2 gold 51 先搜牌 60+ 冲 8,
与玩家共识「攒 50 吃满息升 8」兼容);⑤V1 涌现验证(ADR-0155:等级带 92.6% ±1 级,
满息脉冲涌现)+V6 性能(0.3s 冷解/解级 memo 0ms)早已达标。

## Decision Drivers

- 治本:六局证据全部指向表的节奏缺陷,继续用表 = 已知次优
- 回滚成本一行;DP 异常自动回表(_horizon_node_goal None 兜底)
- 目标明确授权「自主推进不需询问直到稳定通关」

## Considered Options

1. **切流(选)**:HORIZON_SEAM_ACTIVE=True(r14 已备好调用方传参,开关即生效);
2. 继续表+灰度影子:影子数据已充分(160 局),再等无新信息;
3. 手调表节奏:局部补丁,治标;DP 是表的严格升级(涌现+状态感知)。

## Decision

选 1。切流面:spend_mode(cw_plan 卖息挡/cw_evaluate 经济模式)+target_level
(升级 gate)。DP 输出词表 interest/adaptive/level 与消费端判据兼容(r14 核过)。
效果感知解(持卡定制)仍走基线解(53 号切流另批)。

## Consequences

- 预期:P1 等级提前 1-2 节点到位 → boss 战强度差缩小 → P2 起步血量改善;
- 观测:下一局起 dp_posture 影子 vs 生产姿态 diff 应归零(同源);
  exec_events/decisions 持续采;
- 若 P2 存活无改善 → 回滚一行 + 败因转向阵容质量侧(comp 强度/星级);
- ADR-0155 的影子语义升级为生产语义。
