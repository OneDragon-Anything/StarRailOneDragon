# 0081. 静态游戏数据 auto-write 守卫:garbage 拒 + existing 不覆盖

- **Status**: accepted
- **Date**: 2026-08-11
- **原编号**: D-81

## Context
review 抓到 `affix_effects_data.py` 工作区损坏(形单影只值 `85%160%/30%`)。根因:简报 tooltip 未弹时 `read_affix_effect` 读下行(下一词缀行 /「下一步」按钮)当效果 → garbage;`write_affix_effects` 无条件 `current.update()` 覆盖 existing → garbage 累积。词缀效果是**静态游戏数据**(不随对局变,每场只选不同词缀,效果本身固定)。

## Decision Drivers
- OCR 本质不可靠(tooltip 弹出依赖 click 落地 + 动画)
- 静态数据无条件覆盖只会把对的换错的
- 需兼顾自动采新词缀 + 防 OCR 污染

## Considered Options
1. 改 OCR 层检测 tooltip 未弹(复杂 + 难 live 验;即使 OCR 层完美,写入守卫仍必要作防御纵深)
2. 删 auto-write 改纯人工(失去自动采新词缀能力)
3. 写入守卫:garbage 拒 + existing divergent 不覆盖 + new key 正常加(选中)

## Decision
`write_affix_effects` 双守卫:
- **garbage 守卫**:`_is_garbage_affix` 拒「下一步」在 key/value + 空效果(真效果绝不只含/含按钮文字)→ 不写。
- **existing 不覆盖**:已有词缀遇 divergent OCR → **不覆盖**(静态数据,现有值更可信),仅 `[cw!][briefing]` log + tooltip 截图已存待人工 review。新 key(过守卫)正常新增。

## Consequences
- 正向:auto-write 不再把 garbage / divergent 写进 ground truth;正常采集未被破坏(D-82 live 验 4 词缀全匹配 → no-op)。
- 负向:divergent OCR 不更新(existing 更可信),真值更正需人工 review 截图。
- 边界:适用于"静态游戏数据"自动采集(词缀/装备效果等);动态状态不适用。

## Links
- `· docs/develop/currency_war/strategy/`(briefing/affix)
- 关联 D-NN:D-82(live 验证健康)、D-17(研究证据基同类:数据权威源)
