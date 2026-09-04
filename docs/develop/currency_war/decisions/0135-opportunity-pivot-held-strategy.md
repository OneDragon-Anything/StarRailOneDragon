# 0135 机会型 pivot(held_strategy_fit)+ 空板无证据不罚

## Status

accepted(2026-08-15;用户:「拿到很适配的策略/环境主动转阵容,提高胜率」—— 讨论确认方向后落地)

## Context

绑定扫描(ADR-0134)实证:84 条策略阵容特定(星徽套组=阵营+核心+装备三件套,全阵营各一张)。但 pivot 机制只有保命型(连败 maybe_pivot);选完策略后没有任何通路让「套组在手」影响 comp 选择 —— 机会型转型(人玩核心技能)缺失。调试中发现**空板无证据惩罚**伪影:_board_alignment 对空板全罚 ×0.3(罚的前提是 deployed-lock 错配证据,空板没有),而 factions 空的 comp(反甲白厄,故意设计:白厄无阵营)永远躲过 → 早期选择被抬轿 + 机会 pivot 被压死。

## Considered Options

- 信号通路:选策略时反向改 target(一次性)vs **评分维度**(held_strategy_fit 进 comp_score,持续起作用,后续每张新策略都自然重评)→ 后者。
- 强度:仅加性 W_HELD(被 acq/难度乘子稀释,套组双命中只把追击飞霄从 top4 外抬到 #2)vs 加性 + **成型加速乘子**(双命中 ×1.4,压过 strength 先验差)+ **套组授予角色计入持有副本**(acq 解锁:送卡=已持有,不按全牌池低估)→ 三件套。
- 空板罚:保留(统一罚不改变正常 comp 间排序)vs 修(罚需要正证据;且现状只打到 factions 非空的 comp = 数据伪影)→ 修。

## Decision

1. held_strategy_fit(comp, active_strategies):绑定(ADR-0134 strategy_bindings)∩ comp,按**绑定命中数**计(套组双命中=1.0 满分;单命中 0.75;无命中 0.5 中性;无策略 None 动态剔除)。
2. comp_score 加 W_HELD=0.15 维;select_comp 加成型加速乘子(1.0+0.4×(fit−0.5)×2,双命中 ×1.4)+ 套组授予角色并入 acq 持有副本(仅本 comp 核心生效)。
3. _board_alignment:空板(board 无任何单位)返 1.0 —— 惩罚需「板上有单位但不匹配」的正证据。

验证:held_strategy_fit 三态 + 端到端(空板持追击套组 → select_comp 机会转向追击飞霄,压过反甲白厄)+ 空板伪影修复;CW 全套 391 passed(刷新上限测试随 comp 停留语义更新:基线 lv6 非 roll ≤2 / lv7 停留 roll ≤4)。

## 后续(实战沉淀,非本 ADR)

- 乘子 0.4 / W_HELD 0.15 阶段 6 实玩校准;env 侧机会(契约送成套角色)同构接线待议。
