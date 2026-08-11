# 0100. deploy mouseDown 角色头像 avatar(推翻 D-118b drag 假设;5.1.9)

- **Status**: accepted
- **Date**: 2026-08-12
- **原编号**: D-100

## Context
D-118b(commit efe4da40)假设「deploy = long-press drag(hold 0.5 拾取)」但**未 live 验**(commit message 明记「live 验待:长按 drag 能否真正 deploy」)。2026-08-12 live 验 5.1.6 发现 deploy drag **placed=0**(长期未发现 —— D-145~D-154 一堆 deploy fix 都基于这个未验假设;文档 L83「drag hold 0.5 拾取」是 D-118b 未验假设非实测)。

诊断过程(全排 mouse_move / hold_time 0.5+1.0 / mouseDown 中心+上部 都无效):
- **click bench 开详情面板**(D-118b 验 + 本轮再验)→ click 非 pickup。
- drag mouseDown 立绘(中心 y912 / 上部 y882)→ 不拾取(hold 无效)。
- **equip drag 成功**(mouseDown 装备 icon 准)vs **deploy drag 失败**(mouseDown 立绘非 avatar)。
- **米游社官方玩法说明**:deploy = 拖拽角色**头像 avatar**(角色卡左上小圆,非立绘/名字)。

## Decision Drivers
- D-118b 未 live 验(commit 明记)→ drag 假设从未证,placed=0 长期未发现
- click 开详情(非 pickup);mouseDown 立绘不拾取(排 hold_time/mouse_move)
- 米游社官方:拖角色头像 avatar
- equip drag 成功(mouseDown icon 准)vs deploy drag 失败(mouseDown 立绘非 avatar)

## Considered Options
1. **D-118b drag**(hold 0.5,mouseDown 立绘)—— placed=0(未验假设,失败)
2. **mouseDown avatar**(角色卡左上小圆)+ drag(选中)
3. **click-deploy**(D-118)—— click 开详情(D-118b 验非 pickup)

## Decision
deploy drag mouseDown 改**角色头像 avatar**(角色卡左上,bench center 偏 `-40,-50`)+ `hold_time=1.0`(drag_mouse docstring 货币战争角色长按)+ `mouse_move`(bug#1 mitigation 对齐 equip_all 2f521915)。`slot_occupied` 验源槽空仍用 center(src)。

## Consequences
- **正向:avatar mouseDown drag placed=3/5**(2026-08-12 live 验 level1 cap 未满,bench→后排/前排 ✓ CV 验源空)。deploy 从 placed=0 → 3/5(根因解);5.1.6 选排随之生效(pref=back→后排,front→前排)。
- **负向**:bench槽2/5 失败(bug#1 间歇 / avatar 偏移,60% 成功率需提高 —— 下轮精化 avatar 偏移 or CV 定位 avatar 替代固定偏移)。
- **推翻 D-118b drag 假设**:hold_time 非根因(D-118b 假设),avatar mouseDown 才是。文档 L83 需更正(drag hold 0.5 拾取 → 改 avatar mouseDown)。

## Links
- 推翻 D-118b(commit efe4da40)drag 假设(无 ADR)。
- 补 [0099](0099-deploy-position-pref.md) 选排(avatar drag 让选排生效)。
- 米游社官方:deploy 拖角色头像。
