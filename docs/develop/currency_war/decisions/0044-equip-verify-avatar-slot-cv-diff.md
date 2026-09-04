# 0044. equip_all 验穿用 avatar-slot CV-diff(替 count-verify)

- **Status**: accepted
- **Date**: 2026-08-10
- **原编号**: D-44

## Context
count-verify D-41 实测**报 3 实 4 失真**:合成消耗 2 件 → column count 扰;列 reflow + read 漏检也让 count 不可靠。需直接观测 avatar 装备态,非间接推断 column count。

## Decision Drivers
- 合成消耗多件 → column count 不可靠
- 列 reflow + read 漏检 → count 三路失效
- avatar 下方 mini icon 位置固定,直接观测最稳

## Considered Options
1. count-verify(column count 减;合成/reflow/漏检三路失真)
2. SIFT-identify below-icon 名(名错地基不稳,D-37)
3. avatar-slot CV-diff(drag 前后对比目标 avatar 下方 mini icon 区;选中)

## Decision
equip_all 验穿改 **avatar-slot CV-diff**:drag 前 crop 目标 avatar 下方 mini icon 区(`BELOW_ICON_Y=479`),drag 后 crop 同区,`np.abs(pre-post).mean() > BELOW_DIFF_THRESHOLD(8.0)` = 穿[新装/合成都变 icon],不变 = drag 落空。

## Consequences
- 正向:robust 合成消耗 / 列 reflow / read 漏检三路(count-verify 全治);offline fixture 验证连续态 diff 28-41 >> 阈值 8、同态 0.0(D-56)。
- 负向:只验"变了"(穿了),不区分新装 vs 合成(策略层若需区分须 SIFT-identify below-icon)。
- 边界:阈值/区域待 live 跨局面调(单局设定)。

## Links
- `· docs/develop/currency_war/strategy/07_equipment.md`
- 关联 D-NN:D-41(count-verify 失真根因)、D-56(offline 验证 + 抽纯函数)、D-49(below-icon TM 识别)
