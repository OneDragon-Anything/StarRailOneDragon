# ADR-0270: _MID_INTEREST_FLOOR 20 金息平台死门删除

- **Status**: accepted
- **Date**: 2026-08-24

## Context

r282 引入 `_MID_INTEREST_FLOOR = 20`(line_strategy):P1 配方成立
(recipe_tier≥5)且 r≤8 且金≥30 时,floor 降到 20(「吃息 2 保投资余量」
的 B 模式平台)。批⑤F1 判死:**消费点(`_economy_actions` 的 floor 分支)
与路由互斥,300 局 0 激活**——金到 30+ 时配方门/路由早已把金导向别处,
分支永不达。P3(math_proofs)证明金≥50 后息成本=0,「平台」语义已弱化:
留金到 50 与降到 20 的期望差被 P3 归零。

## Considered Options

1. **删除(采纳,P3 裁决)** —— 死码删除:常量 + `_economy_actions` 的
   elif 分支 + 随之失去用途的 recipe_tier 局部导入。300 局 0 激活 →
   删除 = 零行为变化;活代码少一条永不触发的路径(读者免于「平台存在」
   的错误心智模型)。
2. **boss_breaker 内生效(拒绝)** —— 把平台语义挪进 boss 破息段
   (`_BOSS_BREAKER_FLOOR` 体系):P3 已证金≥50 后息成本=0,平台在 boss 段
   同样无期望收益;且 boss 段已有自己的地板(10),再叠平台 = 双地板
   语义纠缠。
3. **保留待复活(拒绝)** —— 死码留着 = 双源心智(读者以为平台在起作用);
   真需要时按 ADR 历史重建,git 可考古。

## Decision

- 删除 `line_strategy._MID_INTEREST_FLOOR` 常量与 `_economy_actions` 中
  的 20 平台 elif 分支;floor 链回到三档(≥50 → 50;≥10 → gold%10;
  否则 0)。
- 引用 math_proofs P3(金≥50 后息成本=0)为裁决依据。

## Consequences

- 零行为变化(300 局 0 激活的死门;floor 链在可达路径上逐分支等价)。
- redesign.md 两处 `_MID_INTEREST_FLOOR` 引用同步清理(INTEREST_FLOOR 行
  标注已删)。
- 锁测试 `test_cw_adr0269_prep_two_stage.py::test_mid_interest_floor_removed`:
  src 全仓无 `_MID_INTEREST_FLOOR` 引用残留。
