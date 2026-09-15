# 盛会之星选巨星(megastar · 货币战争-盛会之星)

> 代码 = `operations/cw_screen/cw_screen_megastar.py::CwScreenMegastar`(CwScreenOpBase 子类)。职责:盛会之星 overlay 一次访问——候选立绘 OCR → `decide_megastar` 选巨星 → 点候选 + 确认;**节点完成模型 = observe 门复检 + 节点预算**(overlay 消失才完成)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_megastar.yml`。

## 1. 分发判定

- 外循环分支 0b:id_mark 锚「货币战争-盛会之星.标识-盛会之星」(独有标题;全屏「确认选择」判据已退役——多屏共享该词)。分发 = 阶段一身份行,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 触发 = 盛会羁绊激活时弹出(非固定节点),**一局可多次** → dispatch 为 OCR 反应式,何时弹都接得住;选中标记不得跨节点保持。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。**节点循环**形态:每轮 = observe 门(`_in_node`:「标识-盛会之星」还在?→ miss = 复位 `ExecState.megastar_candidate_clicked` + 节点完成)→ 仍在 = 一个动作(`_do_action`)→ round_retry(计 `node_max_retry_times=8` 预算,超 → FAIL bail)。五相位屏:装配点分流;decide+act 内聚于 `_do_action`(两路径共享零转录);无 on_outcome 落地登记件。决策入口 = 契约 `decide_megastar(options, bs, session, config)`(默认实现委托 `kernel/cw_comps.py::select_megastar`,未命中/OCR 空 → idx=0;规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E7)。

## 3. 观察面

observe 段 = 节点完成门(含选中标记复位副作用,须在门内)+ 轻观察帧引用;候选读取归 decide 段(`obs/cw_node_obs.py::read_megastar_options`:候选标题「盛会之星一X先生/女士!」正则解析角色名,先生/女士与全/半角叹号容错,按 center-x 左→右排序)。观察 payload = `MegastarObservation`(仅帧引用);本屏不上报 GameState 容器观察(决策输入 = `board_state_of(match.session)` 视图)。

## 4. 动作面

decide+act 内聚 `_do_action`(两路径共享),两步:

1. **点候选**(仅当 `ExecState.megastar_candidate_clicked` 为 False):`decide_megastar` 选 idx → 点候选位(「候选-左」/「候选-右」area center,兜底常量 (822,333)/(1061,333);名位置 = 卡身选中区)→ mouse_move + click → 置位选中标记(局容器级,跨 re-dispatch 持久)→ `chosen_megastar` 写(session + `board_state_of(session).write_logic`,候选选中时点)→ 0.6s。
2. **点确认**:`「按钮-确认选择」area center`(兜底 (1490,560))→ mouse_move + click → 0.9s。确认 = 纯机械单发(验证废除;「请选择强化角色」文本 = 确认钮旁伴随文案非第二画面步骤,未建模独立处理);确认未落地 overlay 残留 = 下一帧重入自愈(observe 门仍在 → 候选已选 → 机械单发确认再推进,计节点预算)。

动作词表:画面 op 直驱(无 `CW_ACTION_TYPES` 成员)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| observe 门复检 miss(overlay 消失) | **节点完成** | round_success(wait = `CW_OVERLAY_SETTLE_S`=1.0 固定时长)交回外循环重分发 |
| 确认未落地 | 节点循环重入 | 重走 `_do_action`(计预算,超 `node_max_retry_times=8` → FAIL bail) |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- `chosen_megastar` write_logic + session 写(候选选中时点;单次逻辑写入豁免——选择落地无定型帧,后果走观察覆盖;ADR-0651 两态制下无挂账登记环节)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」;效果账 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §8。

## 7. 子态与 overlay

本屏无子态。「请选择强化角色」area(与「按钮-确认选择」rect 重叠)系伴随文案,不做步骤判定。

## 8. 守卫与防线

- 选中标记 = **局容器级**(`ExecState.megastar_candidate_clicked`):op 实例级标记会在 re-dispatch 时重置 → 重候选 toggle 反选 → 确认无候选卡死;observe 门 miss 时主动复位(一局多次触发,标记不得跨节点保持)。
- 一局多次触发 → 节点循环逐次独立(无跨节点状态残留)。
- 确认纯机械单发(残留自愈归重入裁决);无本屏专属停机钩子([../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 =「巨星强化」;op 内日志 tag = `[cw-megastar]`(candidates/pick/reason)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens.py`(迁移结构锁)、test_cw_runnode_retire.py(旧节点基类退役等价)。
- game 侧知识:机制(巨星 = 阵营羁绊选 1 角色给全队 buff) = [../../../../game/screens/currency_war_megastar.md](../../../../../game/screens/currency_war_megastar.md);决策规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1。
