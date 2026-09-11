# ADR-0118:BuyShopCards 补给 overlay bail 改用 screen_info area(治备战「返回补给阶段」假阳 → 死循环)

- **Status**:Accepted(2026-08-13)
- **关联**:ADR 无前置(补给画面建档 2026-08-13 提供 `标识-补给阶段` area);events.md「BuyShopCards 假阳 bail bug」

## Context

`run_operation CurrencyWarRunLoop max_rounds=1` 实跑撞 **死循环**(2026-08-13):游戏停在**补给节点的备战屏**(右上「返回补给阶段」按钮,补给非遮挡子态),Loop 派 `BattlePrepCycle` → `BuyShopCards` → 后者 `round_by_ocr('补给阶段', lcs 0.8)` **把「返回补给阶段」按钮文本的子串「补给阶段」误判成补给 overlay** → `round_fail('备战被事件 overlay(补给阶段)叠')` → Loop 重派 BattlePrepCycle → 循环(~6s/轮,无限)。

根因:该 bail 用**全屏 OCR**(文本「补给阶段」),而备战「返回补给阶段」按钮文本含该子串 → 假阳。`BuyShopCards` 的 plan()(含 streak 破息等)根本没被触发到(在 bail 之前退出)。

## Decision Drivers

- 补给画面 2026-08-13 建档后,`货币战争-补给` 有 id_mark area `标识-补给阶段`(pc_rect [893,120,1027,230],位置 = 补给标题,**≠** 备战返回按钮 [1716,51])→ 可用**位置判**替全屏 OCR,根治假阳。
- 与 `battle_loop` 0e 供给 dispatch(L261,同 area)一致 —— 检测口径统一。

## Considered Options

### A. 「补给阶段」从全屏 OCR 列表移到 screen_info area 判(采用)
`BuyShopCards` overlay bail:`('补给阶段', ...)` 从 `round_by_ocr` 列表移到 `round_by_find_area` 元组(同 投资策略/投资环境)。
- 位置判:`标识-补给阶段` area 只在真补给标题(overlay/独立屏)命中;备战「返回补给阶段」按钮位置不同 → 不命中 → BuyShopCards 正常 prep(死循环解)。
- 与 Loop 0e 检测同源(area 一致),口径统一。

### B. 删「补给阶段」bail 整条(否决:丢兜底)
BuyShopCards 入口 guard(L97,需 `备战标识-购买经验`)+ Loop 0e dispatch 已覆盖真补给屏 → 该 bail 冗余。但留 area 版(A)作**防御兜底**(Loop dispatch 被绕过时 BuyShopCards 自身仍能 bail),更稳;删(B)虽也 work 但少一层兜底。

### C. 收紧 LCS 阈值(否决:治标)
`lcs 0.8 → 1.0` 杀「返回补给阶段」子串匹配 —— 但全屏 OCR 全等仍可能误匹(「补给阶段」在别处全等出现),且不解决「文本判 vs 位置判」根因。area(A)位置约束根治。

## Decision

**A**。`shop.py` overlay bail 块:`('货币战争-补给', '标识-补给阶段', '补给阶段')` 加入 `round_by_find_area` 元组;`round_by_ocr` 列表移除 `'补给阶段'`(余 `遭遇其一/选择伙伴/确认选择` 仍 TODO T#103 待建 area)。

## 验证

`run_operation CurrencyWarRunLoop max_rounds=1`(2026-08-13,补给节点备战)实跑:死循环**解除** —— BuyShopCards 正常执行(`plan 买0张 升0次 刷0次 gold=31`,无 `overlay(补给阶段)` bail)→ DeployBench → EquipAll → 出战。
(注:本轮 出战 click 间歇落空[bug#1],与本修复无关,另记。)

## 关联

- 补给画面建档(2026-08-13):`标识-补给阶段` id_mark + `按钮-返回补给阶段`(备战)area 化铺路。
- `battle_loop` 0e 供给 dispatch(L261,同 area)。
- events.md「BuyShopCards 假阳 bail bug」(本 ADR 解)。
