# 0014. 经济 leveling:`_saving_for_level` 去 `_board_strong` 门(弱板也攒级)

- **Status**: accepted
- **Date**: 2026-08-09
- **原编号**: D-14

## Context
bot 卡 lv6 大半局(die p2)。根因:`_saving_for_level` 被 `_board_strong`(form_progress≥0.4)门控 → tier-2 弱板(form_progress<0.4)不攒级 → 花金在买/刷 → 永不升级 → 卡 lv6 cap → 上不了更多单位 → 永 tier-2 → p2 死 = chicken-egg。旧门控意图"板弱该花钱建板",但 buy 受可得性限(DoT 稀疏凑不齐)→ 钱浪费在 refresh/off-target 而非攒级。

## Decision Drivers
- 升级是 tempo 投资(提 cap + shop 高费刷新率),任何板都该追
- 弱板花钱建板受可得性限,钱被浪费而非攒级
- bot 卡 lv6 实测:gold 够不着 level cost

## Considered Options
1. 提 INTEREST_WEIGHT(让攒息值,但不直接促升级)
2. 改 level_plan 更激进(治本但复杂)
3. 去 `_saving_for_level` 的 `_board_strong` 门(选中,最小直击 chicken-egg)

## Decision
`_best_improving_action` 的 `_saving_for_level` 去掉 `_board_strong` 门控。`_saving_for_interest` **仍门控**(息是经济,板强才囤)。弱板也攒级(抑制 off-target 买 + refresh 浪费,留 target 买 + 攒金)→ 够 cost 下轮升级。

## Consequences
- 正向:实测 lv6 时 gold 53(baseline max 43)→ bot 升到 lv7;leveling 修对。
- 负向/边界:p2 仍死 → leveling 必要不充分,还需 comp 质量(tier-3 成型)。
- 边界:仅 leveling 修对(plan 日志直接观测,非 tracking 依赖,证据基础可信);comp 层重做时复审确认不与新 comp 逻辑冲突。

## Links
- `· docs/develop/currency_war/strategy/14_phase_skeleton.md`(经济 tempo / level_plan)
- 关联 D-NN:D-17(研究证据:正确节奏先冲等级 → 维持 50 金吃息)
