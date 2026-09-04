# 0120. deploy 中心拖+hold0 推翻 avatar 假设(DragCwChar 统一拖拽;5.1.9 重诊)

- **Status**: accepted(2026-08-13)
- **原编号**: D-120
- **↺ 推翻**:0100(原文件已删,见 INDEX)(avatar mouseDown + hold 1.0)
- **关联**:[0099](0099-deploy-position-pref.md) 选排 / [0019](0019-max-units-dynamic-back-row.md) 动态后排 / DragCwChar(``drag_char`` 原语)

## Context

0100(原文件已删,见 INDEX) 把 deploy 拖拽机制定为「mouseDown 角色卡左上 **avatar 小圆** + ``hold_time=1.0`` 长按」,live 验 placed=3/5,2/5 失败归「bug#1 间歇 / avatar 偏移」。2026-08-13 重诊:**avatar 结论全错**:

- 「左上小圆 = avatar」**错** —— 那是**星标**(star icon),非头像。角色卡整张可拖(立绘 / 名字 / 中心任一点 mouseDown 都拾取)。
- 「mouseDown 立绘开详情 → 立绘不拾取」**错** —— 详情面板是 **click(mouseUp 松开)** 触发,非 mouseDown。drag = **按下 + 移动**(按下即移 = 拾取;按下不动松开 = click 开详情)。
- 0100 的 placed=3/5「成功」+ 2/5 失败,实为 avatar 偏移(``-40,-50``)落点偶偏 + ``hold_time=1.0`` 长按被判长按/click → ~50% 开详情失败;偶中(偏移落点仍在卡上 + 没被判 click)= 那部分「成功」。**avatar 偏移 + 长按正是失败根因,非解法**。

实测(2026-08-13):中心 drag(563,911→887,398,hold_time=0)→ 飞霄 bench→bench **上阵 ✓**。中心拖 + 按下即移(hold0)即拾取。

## Decision Drivers

- avatar=星标误识 → 0100 建立在错的地标上;左上小圆非头像。
- 详情=click(mouseUp)非 mouseDown → drag 失败诊断错;drag 失败的真因是长按被判 click,不是「mouseDown 错位置」。
- 中心拖+hold0 实测成功(飞霄 ✓);旧 avatar 偏移+hold1s ~50% 失败。
- 全仓角色拖拽机制散落(deploy / sell / DragCwChar 各自 drag_to + 不同 hold/偏移),需单一源。

## Considered Options

1. **[0100] avatar 左上 mouseDown + hold_time=1.0**(推翻)—— avatar=星标误识 + 长按被判 click 开详情 → ~50% 失败;placed=3/5 是偏移落点偶中的噪声。
2. **中心拖 + hold_time=0 + 验源槽变**(采用)—— 卡中心 mouseDown + 按下即移即拾取;retry 防 bug#1 间歇;``_src_changed`` 像素 diff 验源槽变(deploy 空 / swap 换人 / sell 都生效)。实测 ✓。
3. avatar 左上 CV 定位(替固定偏移)—— 0100「下轮精化」设想;**前提错**(avatar=星标),无需。

## Decision

**2**。角色拖拽统一为 **中心拖 + hold_time=0**,抽成 ``DragCwChar.drag_char(op, src, dst, max_retry=3)`` 静态原语(``operations/dev/drag_cw_char.py``):

``mouse_move`` 源(bug#1 settle)→ ``drag_to(start=src, end=dst, duration=1.0, hold_time=0.0)`` → ``mouse_move`` 释放区(防 drag 锁残留)→ ``_src_changed`` 验源槽像素变;retry 3 次防 bug#1 间歇。

- **deploy(``DeployBench._deploy_deterministic``)+ sell(``_sell_offtarget_deployed``)+ DragCwChar op 全走 ``drag_char``** —— 全仓角色拖拽机制单一源(不再各处 drag_to + avatar 偏移)。
- 删 deploy_bench 4 个死方法(``_deploy_by_identity``/``_deploy_all_slots``/``_deploy_strategic``/``_deploy_naive``,均未调用 + 嵌旧 avatar drag)。
- 验证从 ``slot_occupied(源空)`` 改 ``_src_changed(源槽变)`` —— 后者更通用(deploy 空 + swap 换人都判变;deploy_bench 原占用检测仍用 ``slot_occupied``)。
- **后排槽位数动态**([0019]):``DragCwChar._slot_center`` 后排优先用调用方传的 ``back_centers``(财富宝钻 +1 致 >6 时),否则 screen_info 后排-N;``DeployBench._row_centers`` 读**全部** ``后排-N`` area(不硬编码 6,screen_info 补 后排-7+ 后自动跟上)。

## Consequences

- **正向**:deploy/sell 拖拽成功率从 ~50%(avatar 长按被判 click)→ 中心拖稳定拾取(retry 兜底 bug#1);机制单一源,改一处传导全仓。
- **负向 / 待验**:(a) deployed→bench 直接拖仍不生效(CW 机制需 bench→deployed swap,非 op 机制问题,见 DragCwChar docstring);(b) 后排 >6(财富宝钻)的**实际槽位坐标**未 live 验(等财富宝钻局)—— ``back_centers`` 参数 + ``_row_centers`` 读全已就位,调用方传检测到的实际槽即可;(c) sell 拖拽加验源槽变(``drag_char``),不再盲计数 —— 首跑看日志确认卖出数与 gold 增加对得上。
- **推翻 [0100]**:avatar mouseDown + hold1.0 作废;0100「placed=3/5 成功」是 avatar 偏移落点偶中的噪声非机制有效。

## Links
- 推翻 0100(原文件已删,见 INDEX)(avatar mouseDown + hold 1.0)。
- [0099](0099-deploy-position-pref.md) 选排(中心拖让选排稳定生效)。
- [0019](0019-max-units-dynamic-back-row.md) 动态后排(``back_centers`` / ``_row_centers`` 不硬编码 6)。
- DragCwChar ``drag_char``(``operations/dev/drag_cw_char.py``)= 全仓角色拖拽单一源。
