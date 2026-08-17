# ADR-0176: 0174 位面乘子桥拆除——保血阈值上浮改由 18 号首达模型导出

## Status

Accepted(2026-08-17,策略优化会话;18 号 V2 切片一)

## Context

ADR-0174(桥)为救 M55 P2 死亡,在 `effective_hp_threshold` 手写位面乘子 ×1.25(P2)/×1.5(P3),
其 Considered Options 自认「全量等 18 号 first_passage 是正确但远水」。52 号审计把这类桥定性为
「桥接迁移债:影子器官在库、live 补丁塔在长」。债的实质:手写常乘子——

- 不随板强/剩余日程变化(强板弱板同乘);
- 无校准路径(位面难度实测更新后,乘子不会自己动);
- 与 18 号「手写门变模型定理」的主张直接矛盾(模型在库却未被消费)。

## Decision Drivers

- 18 号提案核心主张:保血阈值应从生存曲线导出,而非手拍常数
- 0174 自身实测锚:P2-1 弱板掉 19/节点 vs P1 ~10;cw_horizon.difficulty_scale P2 1.5-1.95 / P3 1.8-2.2
- 治本授权(用户 2026-08-17:一切以治本为目标,有必要就重构)

## Considered Options

1. **模型导出乘子(选)**:`threshold = base × plane_hp_ratio(tier(level), nodes_left, plane)`,
   ratio = hp_floor(P_win≥0.6 地板,位面 k)/hp_floor(P1);P1 分母恒等 → 对 base 精确零漂移;
2. 直接 `threshold = hp_floor(...)` 全模型化(不乘 base)——P1 行为偏离 M57 验证锚(40),
   无实机 canary 前风险大,且职级 override 语义会被冲掉;留给 V2 切片二(消费端接线批次);
3. 维持 0174 手写乘子——桥继续长债。

## Decision

选 1,三件:

- **`cw_first_passage` v1 位面条件化**:`_loss_dist(tier, plane)` = HP_LOSS_MU(P1 基线)×
  PLANE_LOSS_SCALE{1:1.0, 2:1.6, 3:1.9}(0174 实测 1.9× 与 difficulty_scale 带的收缩中值);
  `first_passage_win/p_win_lambda/risk_posture/p_win_projection` 全链 plane 参数(默认 1 向后兼容)。
- **`hp_floor(tier, nodes, target, plane)` 反解 API + `plane_hp_ratio` 乘子导出**:单次卷积 + CDF
  扫描(v1 实测陷阱:格点步长 2.5 对强板 μ=0.8 过粗,微掉血取整归零 → 地板假性=1、乘子病态
  钳 2.0;细化到 0.5 后强板恢复分辨率);ratio 内部 hp_cap=400(弱板超长程真实血上限内两原
  均无解时避免假性 ratio=1),输出夹 [1.0, 2.0]。
- **`cw_state.effective_hp_threshold` 重构**:P2+ 上浮从手写常乘换成 `plane_hp_ratio`
  (tier 取 `board_tier_of(state.level)`,nodes_left 从 plane×round_num 估)。P1 精确不变。

## Consequences

- **P1 零行为变化**(ratio 分母恒等;既有 difficulty override/fallback 语义全部保留);
  P2/P3 阈值从 40×1.25/×1.5=50/60 变为 ≈40×1.55/×1.85≈62/74(弱板实测锚方向,更早保血)。
- 当前先验(CV 恒定三点分布)下 ratio≈μ 比≈近全域常数——板强/日程分化属实测桶(肥尾)替换
  先验后的涌现属性,结构已就位(校准路径:改 PLANE_LOSS_SCALE/实测桶 → 阈值自动跟随)。
- 18 号 V2 剩余切片(后续):cw_horizon 掉血插件换桶分布转移、D 牌赌局化、hp 残值补丁删除、
  is_run_dead/0141/0143 消费端换源(0174 记的「hp 接线滞后一环」同批)。
- 测试:`test_cw_first_passage.py` +6(位面单调/hp_floor 定义/乘子语义/夹界/扩展 cap)、
  `test_cw_decisions.py` +1(阈值模型乘子接线,含 P1 零漂移断言);CW 全量 573 过。
