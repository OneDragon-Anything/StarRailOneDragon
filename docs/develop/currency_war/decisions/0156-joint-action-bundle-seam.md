# ADR-0156 战术层选择机制换形:回合内联合行动束(影子接缝落地)

## Status

Accepted(2026-08-16;切流待 P2 分歧挖掘实机 replay + P3 校准 A/B)

## Context

历史头号杀手(board 散 → P2 秒死)与 commit/pivot/prefilter/drought-bail 一族粘性补丁的共因:贪心按「单动作边际」估值,看不见**同回合动作间交互** —— 第 5/6 张同 trait 的断点跳变、同商店 2 张同名(要么都买凑星要么都不买)、连锁买卖净金。M38 target 振荡(r6-r7 转 4 次)是该族的最新症状。用户 2026-08-16 定调:振荡保险不再加门,按重设计提案 06 号(redesign/06_joint_action_bundle.md)治本。

## Decision Drivers

1. 每条粘性补丁都引入手调阈值(commit 阈值/prefilter 例外/bail 轮数),在贪心框架内这些参数没有正确答案(12 号修三次未收官的 open questions)。
2. 加性松弛上界恰好 = 现贪心 eval → 束优≥贪心按构造成立、超时降级=回退现状、关交互项=与贪心全同(天然对拍锚点)。
3. optimizer's curse 风险(交互项标错被主动放大):v0 只对 target/skeleton 阵营计分 + margin 门槛 + 分歧日志。

## Considered Options

- **继续调粘性门**(commit 阈值/pivot 冷却等):拒绝 —— 病历已证不收敛,M38 振荡是最新例。
- **A5 多步搜索**(跨回合纵深):拒绝 v0 —— 需多步搜索基建,阶段 5+;且治的是「看不到未来」非「看不到交互」。
- **联合行动束**(06 号,采纳):回合内横向联合,现在就可精确求解(2^5 子集枚举),离线可测。
- 直接删粘性门族:待切流验证后逐步退役(v0 影子期全保留,零行为变化)。

## Decision

1. 新增 `cw_bundle.py`(纯函数):束 = 买牌子集(联合可负担);V(B) = Σ 单动作 delta(加性部分=现贪心 eval 同口径,含集中度项)+ 交互项(断点跳变 BREAK_W × 跨档数 / 同名第 2 张 PAIR_W / 第 3 张 MERGE_W 当场 3合1)。
2. 三条性质落测试锁定(`test_cw_bundle.py` 6 条):关交互项 = 最优单买(贪心锚点);无可买 → None;同名对/断点跨档交互可见;确定性;影子开关默认关。
3. **接缝(影子)**:`cw_plan.plan()` 买牌候选循环前,`BUNDLE_SEAM_ACTIVE=False`(默认,贪心现状栈零改);True → bundle_select 优先,异常/None 回退贪心 + [cw][bundle] 分歧日志(切流前的质量观察通道)。
4. off-target 入束仅当参与交互项(联合价值可见才放行)—— 粘性门退役的雏形,完整退役待切流 A/B。

## Consequences

- 切流前置:P2 分歧挖掘(实机 replay 断点临界位面集,统计束-贪心分歧率与类型)、P3 校准环境 A/B(冻结估值只换选择机制);均需实机窗口。
- 交互项权重(BREAK_W/PAIR_W/MERGE_W)是 plaza 锚定先验,校准点;防 optimizer's curse 的约束(target/skeleton only + BUNDLE_MARGIN)在切流 A/B 中检验。
- 提案原文处理删档(redesign/06_joint_action_planner.md → 06_joint_action_bundle.md);本 ADR 为决策单一源。
