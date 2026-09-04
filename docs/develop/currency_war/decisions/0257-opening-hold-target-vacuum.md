# ADR-0257: 开局装备 hold 的 target 真空修正(对抗审查 R3;r388 补丁)

- **Status**: accepted
- **Date**: 2026-08-23

## Context

r388(ADR-0252)开局轮装备 hold 的实现为
`_transition_hold = _tgt_comp is not None`(equip_all L321),而 skill 实机运维节
明载「重启后首局 target 重选是已知断档」——重启后首局 r≤2 恰是 target 真空
高发窗口,此时 r388 覆盖与 r70 form 门**两条 hold 全不生效**,r388 所修的
「开局乱穿」原样残留;且配套检查 check_equip_worn_in_battle(ADR-0254)明示
r1-r2 不报,残留形态正落 sim 免检窗——双侧失明。豁免补偿对抗审查
(2026-08-23,报告 adversarial-compensation-r387-r388)判 DESIGN_RISK 并建议
优先修(重启窗口是高频路径)。附带发现:旧判依赖局部 import 的短路求值
(COMMIT_FRAC 只在 target 分支导入),脆弱。

## Considered Options

1. **开局轮 hold 无条件化**(抽 `_transition_hold_active` 纯函数)——
   key_equips 白名单本就来自 target(target 真空=白名单空=全 hold),
   语义自洽;纯函数可单帧锁。
2. 维持旧判 + 给 target 真空补假 target 兜底——引入假 target 污染下游
   分配语义,且「兜底值」是 skill 防坑清单点名的反模式。
3. 只改检查项让 sim 可测——sim 结构性测不了(check 的 r1-r2 免检窗与
   hold 窗口同源,同源前提相关),治标不治本。

## Decision

选 1:抽 `_transition_hold_active(tgt_comp, form, dual, opening_round)` 纯函数
(equip_all 模块级),开局轮 `return True` 无条件;r70 form 门分支局部导入
COMMIT_FRAC(治短路脆弱点)。锁测试 test_cw_r388_opening_hold.py 八断言
(含 R3 核心场景:开局 + target 真空 → hold)。

## Consequences

- 重启后首局 r≤2 不再乱穿,ADR-0252「开局不再乱穿」承诺补全;
- 实机判读锚点(对抗审查 R4 同框):重启加载后的首局,遥测 equipped
  在 r≤2 应为空或仅 key_equips 命中件——跑局批次核;
- R5(双轨期框架命脉件被当 gen hold)不在本 ADR 范围——白名单扩展
  (framework carry 入白名单)挂 sim 账本批,破格语义单独评审;
- r388 的 hold 语义现在与 r70 解耦清晰:开局门无条件、form 门要 target,
  后续版本若改开局节点序(r1/r2 不再固定奖励),两门都要复跑(对抗
  审查 R4 前提相关风险,记入版本 checklist)。
