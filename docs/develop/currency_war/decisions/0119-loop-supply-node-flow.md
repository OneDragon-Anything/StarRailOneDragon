# ADR-0119:Loop 补给节点流程 —— 点「返回补给阶段」进补给屏(替 supply 停机 hook)

> ✅ 注(2026-08-15):「live 验待下个补给节点」已闭环 —— 补给 2026-08-15 完整重建档(独立屏实锤 + 5 列交互 live 验证 + RunSupplyNode 模型核对 + fixture 4 态),battle_loop 停机 tuple 已移出补给、0e 分支接管。

- **Status**:Accepted(2026-08-13)
- **关联**:ADR-0118(BuyShopCards 补给 bail)/ 补给画面建档(2026-08-13)/ events.md「出战 click 落空」

## Context

`CurrencyWarRunLoop` 在**补给节点的备战屏**(右上「返回补给阶段」按钮)走 `BattlePrepCycle → 出战`,但**出战 click 不推进**(manual+op 都无转场、无 dialog)。2026-08-13 live 查明根因:**补给节点无"出战打怪"** —— 补给节点的推进方式 = **选补给(确认)即完成节点进下回合**(实测 1-5 补给 → 选卡 → 确认 → 1-6,角色+装备入 bench)。

旧 Loop 没有"补给节点备战 → 进补给屏"这一步:0e 分支只检测**补给屏本身**(标识-补给阶段)→ RunSupplyNode,但 bot 停在**补给节点备战**(非补给屏),不会自动进补给屏 → 备战分支 → BattlePrepCycle → 出战(无效)→ 卡。

## Decision Drivers

- live 确认补给节点流程(选补给→进下回合,非出战);bot 必须主动进补给屏(点「返回补给阶段」)。
- 补给屏 RunSupplyNode 已建(select+确认+验证 overlay 消失);缺的只是"备战→补给屏"的导航。

## Considered Options

### A. 备战分支检测「返回补给阶段」→ 点它进补给屏,下轮 0e 分支接 RunSupplyNode(采用)
补给节点备战(返回补给阶段 area 命中)→ `round_by_find_and_click_area` 点按钮 → 下轮 Loop 0e 检测补给屏 → RunSupplyNode 选+确认 → 进下回合。
- 复用已有 RunSupplyNode(不重写选/确认逻辑);只补"导航进补给屏"一步。
- round_wait 自愈:click 落空(bug#1)→ 下轮重检测补给节点备战 → 重点,到落地为止。

### B. 备战分支直接调 RunSupplyNode(否决:不在补给屏)
备战分支直接 RunSupplyNode → 但 RunSupplyNode._in_node 检测补给屏(标识-补给阶段),备战屏不命中 → 立即 round_success(误判完成)→ 不选补给。须先导航到补给屏(A)。

### C. 保留 supply 停机 hook(否决:bot 跑不通)
上轮(2026-08-13)加的 supply 停机 hook 抓补给节点给 AI 建档 —— 但建档核心已完成(流程+id_mark+area+doc),hook 会**阻塞 bot 过补给节点**(每遇即停)。改 flow(A)让 bot 真跑通;次要素交互验证(角色详情/数字)降级 passive。

## Decision

**A**。`battle_loop.loop()` 备战分支( BattlePrepCycle 前):检测 `按钮-返回补给阶段` → 点它 → round_wait;下轮 0e 分支 RunSupplyNode 接手选+确认推进。

## 验证

代码就位(commit 5aceb1e4)+ server restart 生效。**live 验待下个补给节点**(bot 当前在战斗节点备战,需跑到补给节点触发:返回补给阶段按钮态 → 点 → 补给屏 → RunSupplyNode → 进下回合)。

## 关联

- ADR-0118(BuyShopCards bail,让 BuyShopCards 在补给节点备战不误 bail)。
- 补给画面建档(2026-08-13):流程 live 确认 + 按钮-返回补给阶段 area。
- RunSupplyNode(选+确认+验证)/ Loop 0e 分支(补给屏 dispatch)。
