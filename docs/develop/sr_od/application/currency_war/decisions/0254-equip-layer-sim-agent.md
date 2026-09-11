# ADR-0254 装备层执行代理:sim 接 decide_supply+equip_allocation(r393)

## Status

accepted(2026-08-23;r393;commit ca2ee6f8;用户定调「怎么最大发挥模拟价值」的分层接线蓝图第 1 项;ADR-0249 预告的下一同类缺口)

## Context

r390/r391 完成 deploy 侧接线后,装备层是同类缺口:sim 不建模 supply 选取与装备分配,r388 类 bug(开局乱穿)在 sim 不可见。两个纯逻辑入口已可 import(与 op 同源,非重写):`decide_supply`(与 run_supply_node 同源)与 `equip_allocation`(与 EquipAll 同源)。

## Considered Options

(选项未逐条记录;依据=commit message 与 ADR-0249 既定模式,推断按 deploy 侧同法:)
1. sim 重写装备选取/分配逻辑:双源必漂移(ADR-0249 否决过同款),否;
2. **sim 接同源纯函数 + 检查项回灌**(选):supply 节点 3 选 1 采样(通用装备池按 `_EQUIP_VALUE` 键 + 无名池即 OCR 漏读形态;带钻概率 15%,实机简报词缀粗估、标为校准点)→ decide_supply 选 → `st.equips`;每轮 equip_allocation 分配给 deployed,穿走的移出 owned;账本 equipped/owned_equips 字段;
3. 画面/OCR 层也接进 sim:明确不做——画面层永远由 fixture 锁管(commit message 明示「画面/OCR 层永远不接」)。

## Decision

选 2。配套检查项 `check_equip_worn_in_battle`(r388 **反向**指纹):战斗轮(r3+)owned 非空但 equipped 空且有人在场**连续 2 轮** → 报 hold 过矫(白板挨打);开局 r1-r2(r388 hold 语义)/deployed 空/已穿不报。连续 2 轮门与 ADR-0253 同理(压代理时序误报)。

## Consequences

- r388 类 bug **双向**(乱穿+不穿)都有 sim 防线:非空验证 基线 0 违规 / 变异(分配恒空)58/60 局涌现;
- 锁测试 4 条;全量 1047 passed;
- 执行层接线收官:三个实机 bug(r373/r387/r388)全部 sim 可发现+常态拦截;带钻 15% 是显式校准点,精度不足时先调它;
- 工具类装备误报由 owned 名单含工具的概率压低,后续可精化(commit message 明示的已知近似)。
