# 盛会之星选巨星(megastar · 货币战争-盛会之星)

> 代码 = `operations/cw_screen/cw_screen_megastar.py::CwScreenMegastar`(两 node 直继承 `SrOperation`)。职责:盛会之星 overlay 一次访问——候选立绘 OCR → `decide_megastar` 选巨星 → 点候选 + 确认;**节点完成模型 = 标识门复检**(overlay 消失才完成)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_megastar.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役,不引 0x):id_mark 锚「货币战争-盛会之星.标识-盛会之星」(独有标题;全屏「确认选择」判据已退役——多屏共享该词)。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 触发 = 盛会羁绊激活时弹出(非固定节点),**一局可多次** → dispatch 为 OCR 反应式,何时弹都接得住;选中标记不得跨节点保持。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。**节点循环**形态,两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 节点完成门(`_in_node`:「标识-盛会之星」还在;miss = 复位 `StrategyState.megastar_clicked` + 节点完成 round_success 交回外循环)→ 候选懒读(仅未选中时读,见 §3)→ `report_screen_megastar_obs` 落容器 `megastar_opts` 槽 → obs 挂实例属性。决策动作 node = 顶部节点完成复检(每轮新帧)→ 零参决策 `match.strategy.decide_megastar()`(候选自容器槽;缺省实现委托 `kernel/cw_comps.py::select_megastar`,未命中/OCR 空 → idx=0,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E7)→ 「选中 → 确认」链经 `CwActionPickMegastarOp` 派发(选中半迁入动作 op,`env.need_select` 驱动,pick-op-unify 批;`chosen_megastar` 写端与选中旗标留守决策面,派发前写)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=8` 现役值仅框架异常路径消费)。chosen_megastar 留守选择点,不进 report。

## 3. 观察面

观察 node = 节点完成门(含选中标记复位副作用,须在门内)+ 候选懒读(仅「本访问将选择」即未选中时读;确认访问不重读候选;`obs/cw_node_obs.py::read_megastar_options`:候选标题「盛会之星一X先生/女士!」正则解析角色名,先生/女士与全/半角叹号容错,按 center-x 左→右排序)。观察 payload = `CwScreenMegastarObs`(`in_node`/`options`/`screen`,住 `kernel/cw_screen_report/megastar.py`);report = `report_screen_megastar_obs` 候选写容器 `megastar_opts` 槽(空候选不写,闸在 report 内;match/gs 缺席的局外兜底路径跳过)。决策零参读容器槽。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickMegastarOp`(`CwActionPickMegastarParam`) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:候选定位点 + `need_select` 选中半开关;选中点击与确认点击均在动作 op 内,确认钮 op 类体内自读「货币战争-盛会之星.按钮-确认选择」) | 自上报 `report_action_pick_megastar_param`(零写族单相:机械链发出后即全相,发射相意图遥测,容器零写等观察覆盖) | 否(非终结):发出后 `round_wait` 循环推进;落地由决策动作 node 顶部门复检判——「标识-盛会之星」不在 = 节点完成 `round_success` 交回外循环(见 §5) |

决策动作 node 单动作体 `_do_action`(零参:候选自观察轮 obs 载体):决策与写端留守 + 「选中 → 确认」链派发(`CwActionPickMegastarOp`;机械链在动作 op 内,pick-op-unify 批):

1. **决策 + 写端留守**(仅当 `StrategyState.megastar_clicked` 为 False,经 kernel `strategy_state_of` 通道读写,状态缺席不冷建):`decide_megastar()` 零参决策(候选读容器 `megastar_opts` 槽)选 idx → 置位选中标记(局级,跨 re-dispatch 持久)→ `chosen_megastar` 写(容器 `game_state_of(match.session).write_logic`,派发前写——原「候选选中时点」平移至「点选前」,窗口内无读者;session 份退役,gs 单一源)→ 组 env(候选位 = 「候选-左」/「候选-右」area center,兜底常量 (822,333)/(1061,333) + `need_select=True`)→ 派发。
2. **机械链(动作 op 内)**:`need_select` → 点候选(mouse_move + click)→ 0.6s → 点确认(`「按钮-确认选择」area center`,兜底 (1490,560))→ mouse_move + click → 0.9s → 自上报 `report_action_pick_megastar_param`(零写)。确认 = 纯机械单发(验证废除;「请选择强化角色」文本 = 确认钮旁伴随文案非第二画面步骤,未建模独立处理);确认未落地 overlay 残留 = 下一轮门复检自愈(门仍在 → 候选已选 → 机械单发确认再推进)。确认轮(已选中)只发确认(`need_select=False`,idx 复用决策轮缓存)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| observe 门 miss(overlay 消失) | **节点完成** | round_success(wait = `CW_OVERLAY_SETTLE_S`=1.0 固定时长)交回外循环重分发 |
| 确认未落地 | 节点循环重入 | 重走 `_do_action`(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- 候选观察:`report_screen_megastar_obs` 候选写容器 `megastar_opts` 槽(空候选不写)。
- `chosen_megastar` write_logic(点选前(派发前)写;session 份退役,gs 单一源;单次逻辑写入豁免——选择落地无定型帧,后果走观察覆盖;ADR-0651 两态制下无挂账登记环节)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」;效果账 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §8。

## 7. 子态与 overlay

本屏无子态。「请选择强化角色」area(与「按钮-确认选择」rect 重叠)系伴随文案,不做步骤判定。

## 8. 守卫与防线

- 选中标记宿主 = **策略器状态 `StrategyState.megastar_clicked`**(mandate_v1 私有;执行层读写经 kernel `strategy_state_of`,None-safe 不冷建,状态缺席跳过):op 实例级标记会在 re-dispatch 时重置 → 重候选 toggle 反选 → 确认无候选卡死;observe 门 miss 时主动复位(一局多次触发,标记不得跨节点保持)。
- 一局多次触发 → 节点循环逐次独立(无跨节点状态残留)。
- 确认纯机械单发(残留自愈归重入裁决);无本屏专属停机钩子([../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 =「巨星强化」;op 内日志 tag = `[cw-megastar]`(candidates/pick/reason)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens.py`(遭遇 + 盛会之星两 node 形态锁:门完成/懒读跳过/重派不重触发选中[派发 `env.need_select` 断言]/门 miss 复位/缺席态不冷建)、test_cw_unified_action_4.py(巨星 op 机械链行为锁)、test_cw_runnode_retire.py(旧节点基类退役等价)。
- game 侧知识:机制(巨星 = 阵营羁绊选 1 角色给全队 buff) = [../../../../game/screens/currency_war_megastar.md](../../../../../game/screens/currency_war_megastar.md);决策规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1。
