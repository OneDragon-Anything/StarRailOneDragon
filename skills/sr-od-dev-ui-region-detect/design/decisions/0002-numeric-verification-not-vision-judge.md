# 0002. 验证用数值对拍 ground truth,不用 vision 当裁判

- **Status**: accepted
- **Date**: 2026-08-04

## Context

检测出坐标后要验证「对不对」。试过让 vision 当裁判:画 GT(绿)+ 检测(红/橙)overlay 让
vision 数对齐 → vision 报「7/9、槽 3/9 错位、前后排对齐」。但**数值对拍显示 bench 全 9 个
≤5px(槽3=1px、槽9=3px)、前排误差 71px(多峰)** —— vision 的计数 / 对齐判断与数值**完全
反了**。

根因:vision 不懂游戏、会基于文字瞎猜;数 overlay 对齐也会数错(状态推理 / 计数 / 对齐判断
不可信,只客观描述可信)。

## Decision Drivers

- **可信**:坐标对错是几何问题,数值差是 ground truth;vision 计数 / 对齐是猜测,不是 ground
  truth。
- **版本鲁棒**:数值对拍不依赖游戏语义,跨版本稳定。
- **可复现**:数值差能写进测试 / 报告,vision 判断不能。

## Considered Options

1. **vision 当裁判**(看 overlay 数对齐):实测与数值完全反(见 Context),不可信。
2. **数值对拍 ground truth(选中)**:`detected_center` vs `gt_center` 数值差;形状检测给矩形用
   IoU>0.8,投影峰值法给点用中心距 < 10px。
3. **人工肉眼复核全部**:准但不可规模化;作为数值对拍的**补充**(落盘标注图肉眼复核数量与
   位置 + 多样本核实稳定性),不替代数值。

## Decision

选 2(+3 补充):坐标对错只看数值差;vision 只用于「描述客观特征」和「给 ground truth」,
**不当裁判**。判据写进 `../../SKILL.md`「验证」段。

## Consequences

- **正向**:验证客观可复现;不受 vision 计数 / 对齐幻觉影响;可写进自动化校验。
- **负向**:需要先有 ground truth(手圈 / `click_game` 实锤 / screen_info 已有 `pc_rect`)——
  ground truth 来源要人工或建档成果。
- **follow-up**:ground truth 标注流程归 `od-dev-screen-onboarding`(建档),本 skill 只
  消费 GT 做对拍。

## Links

- `../../SKILL.md`「验证」段 + vision 段(「状态推理 / 计数 / 对齐判断不可信」)。
- 同源 vision 不可信问题:[ADR-0004](0004-vision-color-unreliable.md)(颜色维度)。
