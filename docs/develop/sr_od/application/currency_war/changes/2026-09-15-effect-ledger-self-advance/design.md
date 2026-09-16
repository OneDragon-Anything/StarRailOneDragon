# 效果账本自推进迁移迭代设计（总纲）

## 0. 元信息
- 迭代目标：用户裁定（2026-09-15）「不能在 loop 做编排」——效果账本节点推进从 `operations/cw_loop.py` 备战分支迁入 game state kernel 派生管线，承接 `game_state/node-derivation.md` §3.3 规则六（迁移三面：①驱动时点 ②键源切派生层 ③计数器退役；本迭代做①②，③挂效果域批 M3，见 §1 不解决）。
- 状态：草案（对抗审一轮打回，本稿为修正稿）
- 文档清单：无详设（单文档方案，本篇即完整设计）；对抗报告 = [attack.md](attack.md)

## 1. 问题与动机
- 现状症状：效果账本节点推进 = cw_loop 备战分支入口编排（`cw_loop.py:1885-1969`，85 行含注释），全仓唯一生产调用点；挂点错位——分支入口读到的是**上一轮观察**写入的节点镜像；弹窗腿/0q/0p 的节点进入（R5 §3.3 判定为节点边界）不触发账本推进。
- 根因归层：流程层。账本推进是「节点进入派生事件」的后效；四腿派生已实现于 kernel（`observe_screen_context`，生产喂入 = `cw_observation.py:2682` 漏斗 + loop 开局链分支写点），后效却仍由外层循环显式驱动——编排住错层。依据：`node-derivation.md` §①（四规则组、派生管线、与 advance_node 同坐标系）、§3.3 规则六（`node-derivation.md:302-313`，迁移三面原文）。
- 解决到哪：效果推进段整体入 `observe_screen_context` 派生管线（尾段，同临界区）；**结算参数源全部切派生层**（规则六第②面）；经济参数经注册式提供方注入；cw_loop tick 块删除（与管线接线**同一提交原子切换**，防双驱动窗口）。
- 明确不解决：
  - **计数器退役（迁移三面③）**：账本内部 `_last_tick_node` 去重计数器保留，仅存去重职能；「派生 hist 守卫单调 vs tick 键计数器」双权威窗分叉风险挂效果域批 M3 差异清单（在册），本迭代不收口。
  - 节点序来源升级：四腿已实现，本迭代不动腿本体。
  - 节点边界金结算口径（败局保守闸/宝钻透传 0 语义）保持现值。
  - 哨兵「备战环空转」检测面（独立小批）；§3 其余编排的迁移（达标臂/恢复链等，独立迭代）。
  - 旧设计件悬空指针（「GameState-数据结构设计.md §5.1/§8.4」类引用）的全局清理（本迭代仅保证新增文本不新增悬空引用）。

## 2. 方案
- 系统级变化：
  1. **kernel 新增效果推进段**：`observe_screen_context` 管线尾段（类型派生之后、方法返回前，同临界区）。段逻辑：
     a. **推进闸（双条件）**：`effective = effective_node_ord(self)`；`effective is None` → 整段跳过（**「未观察不当真进节点」守卫随迁**，语义 = 现码 `cw_loop.py:1895-1899` 禁令：禁把未观察当真进节点无条件推进虚耗余期/虚累余额）。非 None → `advanced, expired = self.effects.advance_node(effective)`（账本内置去重继续兜底同序幂等）。
     b. `expired` 逐条 `log.warning('[cw!][effect] 效果到期移除:…')`（留证语义与现值一致）。
     c. `advanced` 为真 → `grant_effect_node_refresh_balance(self, frame=f'p{(effective - 1) // 9 + 1}-r{(effective - 1) % 9 + 1}')`（frame = 派生序反解，与现值同形）。
     d. **节点边界金结算（推进与结算分离，双水位）**：
       - 结算水位：新工程字段 `boundary_settled_ord`（非 Field，同 `node_hist_ord` 形态）。
       - **触发条件（三 conjunction，完整）**：`effective` 非 None ∧ `effective > (boundary_settled_ord or 0)` ∧ **本帧为该节点的入口可结算帧**。入口可结算帧 = 备战帧 ∨ 补给选择画面——依据 = 节点边界定义基准（`node-derivation.md` §3.3：节点推进 = 进入该节点的备战画面；**补给特例 = 补给选择画面即节点入口，补给节点无备战画面**）。0q/0p/弹窗族其余推进帧 = 过渡标记，**不触发结算**（当帧节点镜像未刷新，取错窗参数——攻击 F1 实证），递延至该节点入口帧：普通战斗/遭遇/策略节点 = 备战帧；补给节点 = 补给选择画面（段序在类型派生之后，当帧已直定 kind=supply，可知）。
       - 参数源（**序与位置禁读节点镜像；kind 为唯一镜像读取**，与现码同源）：
         - `plane, round_num = _node_key_for_ord(effective)` 反解（同模块私有读口，`cw_game_state.py:3183-3189`）；
         - `node_type = self.node.value.kind`（镜像现值，含漏斗继承合成；**不设 kind 闸**：`round_start_income` 对未知/空 kind 落 else→combat 落袋是现值语义，`cw_economy.py:528-531`，加闸 = 收入语义变化）；
         - `streak = int(max(0, self.streak.value))`（符号归一保留现值）；
         - 倍率/息修饰 = 经济提供方（见 2）；`diamond_gold = 0`、`lost_node = None`（现值）。
       - **守卫与水位落点（失败路径规格）**：
         - 前置守卫：`self.node.value is None ∨ self.streak.value is None ∨ self.settlement.value is None` → 金结算**静默跳过**（不告警，与现码同窗同语义——现码同条件静默跳过），其余段照常；
         - `settle` 后水位落点对齐 `NodeBoundarySettlement` 载体（`cw_effect_inventory.py:1067-1077`）：`written=True` → 落水位；`written=False ∧ total<=0`（无欠账）→ 落水位；`written=False ∧ 金未读`（gold None）→ **水位不动**（下个入口帧重试，防永久漏结）。
       - 结算成功 → `log.info('[cw][effect] 节点边界金结算 logic 写入(branch=… total=…)')`。
     e. `project_effect_capacity(self)`（每 pass 重锚，不限 advanced）。
     f. 整段 `try/except Exception → log.warning('[cw][effect] 效果推进段失败(不阻塞): …')` 不上抛（best-effort，同 journal sink「不毒化写入链」纪律；**显式选择 warning 级**——效果段失败非纯记录层事件，留巡检可见痕）。
  2. **经济提供方注册口**：`register_boundary_economy_provider(fn)`，模块级单槽汇点，照 `_STATE_JOURNAL_SINK` 注册模式（`cw_game_state.py:816-831`）。`fn() -> tuple[float, int, int | None] | None`（win_reward_mult, interest_flat_per_node, interest_cap_override，聚合口径单一源 = `cw_investments.aggregate_economy`）；未注册或返回 None = 金结算跳过（推进/发放/重锚照常）。**生产注册点唯一 = ctx 级一次性注册**（应用装配完成后；provider 闭包动态读 `ctx.cw_match`——恢复局 `cw_match` 在场即正常供参，无静默窗口；局外返回 None）。**禁止挂开局链初始化**（恢复接管局不走开局链，挂那里 = 恢复局整局金结算静默缺失）。sim/测试直注。
  3. **cw_loop tick 块删除**：备战分支效果段全删（含金结算成功 `log.info('[cw-loop] 节点边界金结算…')` 与段失败 warning——日志形状变化见行为变化申报）；随块失用的 import 同删（`board_state_of` 以达标臂自有 import 为准，`cw_loop.py:1992`）。
- 行为变化申报：
  - 推进时点：从「备战分支入口（上一轮镜像现值）」改为「观察派生时（本帧四腿派生序，`effective_node_ord`）」；
  - 覆盖面：弹窗腿/0q/0p 的节点进入**也开始触发账本推进**（对齐节点边界正式定义，R5 §3.3 定义基准）；现状仅备战帧触发属覆盖缺口；
  - **金结算时点与参数源**：结算从「分支入口」改为「节点入口帧（备战帧；补给特例 = 补给选择画面）的管线尾段」，参数源从「节点镜像键」改为「派生序反解 + 镜像 kind」——正常流与现值等价，弹窗腿先推进形态由递延水位防错窗（攻击 F1/F7 修正）；
  - **日志形状**：金结算成功行 `[cw-loop] 节点边界金结算 logic 写入(…)` → `[cw][effect] 节点边界金结算 logic 写入(…)`；段失败行 `[cw-loop] 效果账本 tick 失败(不阻塞)` → `[cw][effect] 效果推进段失败(不阻塞)`（旧标签随 tick 块消失；`[cw][effect]` 不在哨兵 LOOP 白名单前缀内，无哨兵语义影响）；
  - **补给节点入口收入**：从「永续观察覆盖兜底（现码不在补给入口做 logic 结算）」变为「入口帧管线 logic 结算」（对齐节点边界定义特例——补给选择画面即节点入口；supply 分支首次进 logic 面）；
  - 「未观察不当真进节点」守卫**随迁保留**（非废除）。
- 接口契约（本迭代两个新增面，唯一必须定死的深度内容）：
  - 管线段序：上下文对 → 顶栏观察层 → 节点域四腿 → 类型派生 → **效果推进段（新增，末尾）**；
  - 提供方：见 2 条 2；聚合口径单一源 = `cw_investments.aggregate_economy`（禁第二份）。
- 关键取舍：
  - 备选「提升为 kernel 单函数、由调用方显式调」：放弃——调用方仍须记得调用，编排只是换层；与派生管线「随事件自治」方向相逆（R5 §①「纯 _swap 内管线无 hook 框架」的自治语义）。
  - 备选「维持 loop 现状、归效果域批」：放弃——用户裁定编排不住 loop；效果域批落地时本块删除与本迭代重复。
  - 备选「金结算挂在账本 advanced 位、与推进同点」：放弃——弹窗腿/0q 腿推进帧上节点镜像未刷新，当帧结算取错窗参数（攻击 F1 实证场景）；递延到备战帧 = 节点入口定义本尊、镜像新鲜，且以结算水位保每节点恰一次。
  - 备选「以 state/journal.jsonl 写静默做哨兵面替代心跳」：独立小批（哨兵侧），不入本迭代。
