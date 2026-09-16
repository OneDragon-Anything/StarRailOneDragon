# 效果账本自推进迁移迭代设计（总纲）

## 0. 元信息
- 迭代目标：用户裁定（2026-09-15）「不能在 loop 做编排」——效果账本节点推进从 `operations/cw_loop.py` 备战分支迁入 game state kernel 派生管线，承接 `game_state/node-derivation.md`（R5 判定方案）与 `game_state/effect-domain.md`（§节点推进族）记载的目标态。
- 状态：草案
- 文档清单：无详设（单文档方案，本篇即完整设计）

## 1. 问题与动机
- 现状症状：效果账本节点推进 = cw_loop 备战分支入口约 70 行编排（推进账本/到期留证/刷新余额发放/节点边界金结算/容量重锚），全仓唯一生产调用点；挂点错位——分支入口读到的是**上一轮观察**写入的节点现值，非本帧派生序；弹窗腿/0q/0p 的节点进入（R5 §3.3 判定为节点边界）不触发账本推进，仅备战帧分支入口触发。
- 根因归层：流程层。账本推进是「节点进入派生事件」的后效；R5 派生管线落地后事件源在 kernel 内部（`observe_screen_context` 四腿写 `node_ord`），后效却仍由外层循环显式驱动——编排住错层。依据：`game_state/node-derivation.md` §①（四规则组、派生管线、与 advance_node 同坐标系）；`game_state/effect-domain.md` §节点推进触发的效果推进段（「目标态在 _swap 派生管线内」）。
- 解决到哪：效果推进段整体入 `observe_screen_context` 派生管线（尾段，同临界区）；经济参数经注册式提供方注入；cw_loop tick 块删除。
- 明确不解决：节点序来源升级（四腿**已实现**于 `observe_screen_context`，本迭代不动腿本体）；节点边界金结算口径（败局保守闸/宝钻透传 0 语义保持现值）；哨兵「备战环空转」检测面（独立小批）；§3 其余编排的迁移（达标臂/恢复链等，独立迭代）。

## 2. 方案
- 系统级变化：
  1. **kernel 新增效果推进段**：`observe_screen_context` 管线尾段（类型派生之后、方法返回前，同临界区）。段逻辑：
     a. `effective = effective_node_ord(self)`；`advanced, expired = self.effects.advance_node(effective)`——账本内置去重（同节点不重复推进）为闸门，管线段无条件调用。依据：`cw_effect_inventory.py` §240-254（同节点去重与「登记当节点不推进」守卫在 inventory 内）。
     b. `expired` 逐条 `log.warning('[cw!][effect] 效果到期移除:…')`（留证语义与现值一致）。
     c. `advanced` 为真 → `grant_effect_node_refresh_balance(self, frame=…)`。
     d. `advanced` ∧ 经济提供方在场 ∧ `self.settlement.value` 非 None 且 `killed is True` ∧ `self.streak.value` 非 None ∧ `self.node.value`（kind 可知）→ 以提供方聚合参数调 `settle_node_boundary_gold`。任一不满足 = 跳过金结算，**其余段照常**（保守闸语义与现值一致，依据 = cw_loop 现块「败局/结算不可知时整拍跳过」+ `settle_node_boundary_gold` 金未读自跳契约，`cw_effect_inventory.py:1107-1110`）。
     e. `project_effect_capacity(self)`（每 pass 重锚，不限 advanced）。
     f. 整段 `try/except Exception → log.warning` 不上抛（best-effort，同 journal sink「不毒化写入链」纪律，`cw_game_state.py:2748`）。
  2. **经济提供方注册口**：`register_boundary_economy_provider(fn)`，模块级汇点，照 `_STATE_JOURNAL_SINK` 注册模式（`cw_game_state.py:816-831`）。`fn() -> tuple[float, int, int | None] | None`（win_reward_mult, interest_flat_per_node, interest_cap_override）；未注册或返回 None = 金结算跳过。生产注册 = ctx 级一次性注册，provider 闭包动态读 `ctx.cw_match.session.active_strategies` 做 `aggregate_economy`（局外/无 match 返回 None，无生命周期装卸）。sim/测试直注。
  3. **cw_loop tick 块删除**：备战分支效果段约 70 行全删；随块失用的 import 同删（`board_state_of` 若仅剩后文达标臂使用，以该处自有 import 为准）。
- 行为变化申报（对齐设计语义的偏差收敛）：
  - 推进时点：从「备战分支入口（读上一轮观察现值）」改为「观察派生时（本帧四腿派生序）」——即设计 §8.4「备战帧观察后调用」的本意；
  - 覆盖面：弹窗腿/0q/0p 的节点进入**也开始触发**账本推进（对齐节点边界正式定义「节点推进 = 进入该节点的备战画面」，R5 §3.3 定义基准）；现状仅备战帧触发属覆盖缺口非语义。
- 接口契约（本迭代两个新增面，唯一必须定死的深度内容）：
  - 管线段序：上下文对 → 顶栏观察层 → 节点域四腿 → 类型派生 → **效果推进段（新增，末尾）**；
  - 提供方：见 2.条 2；聚合口径单一源 = `cw_investments.aggregate_economy`（禁第二份）。
- 关键取舍：
  - 备选「提升为 kernel 单函数、由调用方显式调」：放弃——调用方仍须记得调用，编排只是换层；与派生管线「随事件自治」方向相逆（R5 §①「纯 _swap 内管线无 hook 框架」的自治语义）。
  - 备选「维持 loop 现状、归效果域批」：放弃——用户裁定编排不住 loop；效果域批落地时本块删除与本迭代重复。
  - 备选「以 state/journal.jsonl 写静默做哨兵面替代心跳」：独立小批（哨兵侧），不入本迭代。
