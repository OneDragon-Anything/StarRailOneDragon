# T-5 sim 等价静态核签 + 回归收口报告

- **迭代**：出战域原子化重整（landing 3.5）
- **核签日期**：2026-11-18
- **核对对象**：三批落地后的代码实态（T-2 `27185788b`、T-3 `a556f3c1c`、T-4 `129634c4a` + 返工 `2df4419da`，另有同日并行批与 T-4 范围外清偿 commit `5bb1be1ec`/`4b94bb63e`；核签一律以工作区当前实态为准）
- **设计依据**：design.md §2.5（六行申报表）/ §2.8；landing.md 3.5
- **结论**：**六行全部核签通过，零失配**；回归集 12 条全绿；import 冒烟零错。一处核签方式说明见行5（「sim 恒不可达」机制申报住 design.md 本身，非代码注记；机制经代码验证成立）。

## 1. §2.5 六行逐行静态核签表

### 行1 `CwActionStartBattleOp` 机械执行 —— 通过

申报：`mechanical_io_allowed()` 门在位；弹窗收尾段零残留；删收尾段 = sim 侧少两次恒 False 的 `visible` 查询（`visible` 入口副作用幂等补跑，sim 零行为变化）。

- `mechanical_io_allowed()` 门在位：`operations/cw_op/cw_start_battle_action.py:117` `if cw_sim_ports.mechanical_io_allowed():` 门下 `mouse_move + click`（:118-119），else 分支静默成功注释在位（:120-121）。
- 弹窗收尾段零残留：`grep "_settle_post_click_popup|POST_CLICK_WAIT_S|DeployNotFull|NoFront|deploy_not_full|toast_no_front"` 于该文件零命中（exit 1）。对照旧版（`git show be395fd78:...cw_start_battle_action.py`）：`:76 POST_CLICK_WAIT_S`、`:129 sleep`、`:130 _settle_post_click_popup` 调用、`:150` 定义——均已删净。
- sim 侧影响核实：旧版收尾段两次查询 = `round_by_find_area(scr, '货币战争-未达上限警告', '标识-未达上限警告')` 与 `round_by_find_area(scr, '货币战争-提示-前台无角色', '标识-无角色提示')`。sim 模式下 `round_by_find_area` 经端口应答：`operations/cw_operation_base.py:153-157`（`cw_sim_ports.visible(screen_name, area_name)`）；sim 后端 `visible` 首查 `if screen_name != self._screen: return False`（`sim/cw_sim_backend.py:1925-1926`），而 sim 包全量 grep 两弹窗屏名零命中（见行3）→ 两查询 sim 下恒 False，删除 = 少两次恒 False 查询，申报成立。
- 副作用幂等补跑：`visible` 入口确带两处副作用（`cw_sim_backend.py:1923-1924` `self._maybe_finish_wait()` + `self._sync_shop_record()`）。`_sync_shop_record` 在 `advance` 入口重跑（`:2373`，出战上报 → `declare_world` → `advance` 同流程紧随）；`_maybe_finish_wait` 由下一问询懒完成（`:1885` screen_identity / `:1923` visible / `:2046` click_answer 三处入口），作用域仅 `PREP_SUB_WAIT_ONE_ONE`（`:2127-2131`）——design 申报「本流程不激活」与代码一致（wait_one_one = 开局补给动画等待变体，`:306`/`:2119`，仅补给开局语境进入）。删除零差异成立。

### 行2 上报与声明 —— 通过

申报：上报函数零改动、三出口（battle_resolve / battle_skip / supply_finish）不变；op 自上报调用面参数完整；声明时点提前在 sim 下实质不变（原收尾段 sim 恒走「无弹窗」出口）。

- 三出口在位：`kernel/cw_action_report/start_battle.py:44` `_DECL_TRIGGER = 'battle_resolve'`、`:48` `_SKIP_DECL_TRIGGER = 'battle_skip'`、`:116` `report_node_advance(gs, trigger='supply_finish')`（补给节点分支）。
- 本批零改动：本批全部 commit（`27185788b`/`a556f3c1c`/`129634c4a`/`2df4419da`/`5bb1be1ec`/`4b94bb63e`）对该文件 `git show --stat` 均零命中；最近一次改动 = `73d93945c`（2026-11-11，本迭代之前的注释指针清理）。
- 调用面参数完整：签名 `report_action_start_battle_param(gs, param, sig, session=None, skip_substate=False)`（`start_battle.py:93-95`）；op 调用点 `cw_start_battle_action.py:128-134` 五参全量传齐（`gs`/`action`/`ChannelSig`/`session=`/`skip_substate=skip_substate`）。
- 声明时点：旧版声明在收尾段之后（旧 `:131-141`），收尾段 sim 恒走「无弹窗」出口（行1已证两查询恒 False）→ 新版紧随单击上报，sim 下时序实质不变。

### 行3 弹窗 op（`CwScreenDeployNotFull` / `CwScreenNoFrontHint`）—— 通过

申报：两 op 均有「sim 分支不适用（后端不建模）」docstring 申报；sim 后端 grep 两弹窗屏名零命中 → 恒不派发。

- `CwScreenNoFrontHint` 申报：`operations/cw_screen/cw_screen_no_front_hint.py:16-17`「本屏 sim 分支不适用:后端画面状态机不建模本屏,弹窗帧恒不派发到本 op。」
- `CwScreenDeployNotFull` 申报：`operations/cw_screen/cw_screen_deploy_not_full.py:17-18`「本屏 sim 分支 = 不适用(sim 无对应画面段)。」
- sim 零建模复核：`grep -n "未达上限|前台无角色|no_front|deploy_not_full"` 于 `sim/*.py` 全包零命中（exit 1），覆盖 `cw_sim_backend.py`。恒不派发机制 = 阶段一身份分发答口 `screen_identity` 返回状态机 `_screen`（弹窗屏不在其中）→ 弹窗屏名永不命中分发表（`cw_sim_backend.py:1884-1901`）。

### 行4 发出链 —— 通过

申报：迁入链只动物理位置与 import，端口调用零改动（`sim_or_live_identity` / `round_by_find_area`→`visible`）；`CW_DISPATCH_SCREENS` 单源在位。

- 新旧函数体逐行 diff（旧 = `git show a556f3c1c:operations/cw_loop.py:151-395`，新 = `prep_actions.py:561-776`，覆盖六函数全量）：差异仅四类——① docstring/注释调试叙事转纯语义（design §2.4 申报的清理项）；② 函数内 import 删减（同居后不再需要 `PrepActionExecutor`/`StopBrakeShortCircuit`/`CwActionStartBattleParam` 局部 import）；③ `CwLoop.CW_DISPATCH_SCREENS` → kernel 常量 `CW_DISPATCH_SCREENS`；④ `_prep_anchors_hit` → `prep_anchors_hit`（kernel 公开名）。端口调用零变化。
- 浮层闸门答口：`prep_actions.py:731` `cw_sim_ports.sim_or_live_identity(` 与旧版 `cw_loop.py:328` 同参同序。
- 屏态复验判据：`kernel/cw_obs_core.py:142-148` `prep_anchors_hit` 三处 `op.round_by_find_area`（备战标识-购买经验 / 按钮-出战 / 按钮-跳过，`crop_first=False`）与旧 `cw_loop.py:377-390` `_prep_anchors_hit` 逐字等价——sim 模式经 `cw_operation_base.py:153-157` → `visible` 端口，哨兵帧不进 CV 识别，误真无通路（`cw_operation_base.py:73-74` sim 哨兵帧 + `:151-157` 端口应答）。
- dispatch 单源：定义单点 `kernel/cw_dispatch_tables.py:16`；消费方两处同源——`prep_actions.py:54-56` 直接 import、`cw_loop.py:278-279` 类属性别名指向 `cw_dispatch_tables.CW_DISPATCH_SCREENS`（其余引用点 `cw_loop.py:288/329/337/340` 均经该别名）；全仓 grep 无第二定义点（`cw_loop.py:833`、`cw_screen_plane_detail.py:8` 为 docstring 提及）。

### 行5 resume 面 —— 通过（附核签方式说明）

申报：`locked_resume_sync_and_battle` 迁后语义不变；无需 sim 分支；sim 后端不建模锁定恢复态 → 商店探针恒可开 → 判非锁定 → resume 路径 sim 恒不可达（机制申报）。

- 迁后语义不变：函数体 = 单行委托 `return launch_battle_unified(op, ctx, face='resume')`（`prep_actions.py:593`），与旧版逐字等价（新旧 diff 该区域零差异 hunk）；docstring 亦逐字随迁（diff 首个 hunk 起于 `launch_prepared_battle` docstring，`locked_resume_sync_and_battle` 区段零差异）。
- 无需 sim 分支：函数体与 loop 锁定分支（`cw_loop.py:1389-1400`）零 sim 分支代码。
- 「sim 恒不可达」注记位置说明：**该措辞以机制申报形态住在 design.md §2.5 行5 本身**；代码侧无同名注记，且 `git log -S "不可达"` 全史核对——resume 面历史上从未有过此类代码注记（非迁移丢失）。机制本身经代码验证成立：
  - 探针链 = `cw_loop.py:1370-1375`：点「按钮-商店」（sim 经 `click_answer` 端口，状态机建模开店转移 `cw_sim_backend.py:2175` `_present_modal(SCREEN_SHOP)`）→ 验「货币战争-备战-开商店/按钮-收起」（sim `SCREEN_SHOP = '货币战争-备战-开商店'` `:278`，`visible` 对未建模排除表外的 area 答 True，排除表 `_UNPRESENTED_OVERLAY_ANCHORS` 仅含 `SCREEN_PREP/标识-简易装备` `:1544-1546`）→ `_opened = True` → `probe_resolve` = `'normal'`（`obs/cw_resume_lock.py:27-33`）→ 判非锁定 → `_cw_locked_resume` 在 sim 下恒不置位（`cw_loop.py:1384` 仅探针零响应分支置位）→ resume 路径 sim 恒不可达。

### 行6 armed 面 —— 通过

申报：`cw_screen_prep.py` 调用面 import 指向 `prep_actions`，决策环执行路径不变，零改动。

- import 指向：`operations/cw_screen/cw_screen_prep.py:974-976` 函数内 `from sr_od.application.currency_war.prep_actions import launch_battle_unified`。
- 决策环路径不变：T-4 对该文件 diff 仅 2 行（import 源行 + 注记补「执行器住 prep_actions」），调用 `launch_battle_unified(self, self.ctx, face='armed')`（`:977-978`）零变化；链路 = 决策环 `:850-852` `_act_execute_default(action)` → `:970` `isinstance(action, CwActionStartBattleParam)` 分支 → 统一执行器，路径结构零改动。

## 2. 回归集全量复跑记录

命令（`PYTHONPATH=src`）：

```
uv run pytest sr-od-test/test/sr_od/application/currency_war/test_prep_actions.py \
  sr-od-test/test/sr_od/application/currency_war/operations/cw_op/test_cw_start_battle_action.py \
  sr-od-test/test/sr_od/application/currency_war/operations/cw_screen/test_cw_screen_no_front_hint.py -v
```

结果：**12 passed, 1 warning in 2.85s**（warning = 既有 `locale.getdefaultlocale` DeprecationWarning，与本批无关）。

```
test_prep_actions.py::test_screen_recheck_stale_gives_up PASSED        (屏态复验 stale 放弃)
test_prep_actions.py::test_overlay_gate_holds_launch PASSED            (浮层闸门 hold)
test_prep_actions.py::test_armed_deploys_then_battle_click PASSED      (armed 部署原子序→出战点击)
test_prep_actions.py::test_resume_sync_once_writes_evidence PASSED     (resume 发出即写证据位)
test_cw_start_battle_action.py::test_prep_frame_single_click_report_and_return PASSED
test_cw_start_battle_action.py::test_skip_fallback_clicks_skip_button PASSED
test_cw_start_battle_action.py::test_popup_frame_clicks_battle_only_no_settle PASSED
test_cw_start_battle_action.py::test_popup_main_path_deploy_not_full PASSED
test_cw_start_battle_action.py::test_popup_main_path_no_front_hint PASSED
test_cw_screen_no_front_hint.py::test_gate_miss_fails_back PASSED
test_cw_screen_no_front_hint.py::test_gate_hit_confirms_and_reconfirms PASSED
test_cw_screen_no_front_hint.py::test_confirm_pending_reentry_success PASSED
```

覆盖面对照 design §2.8：发出链四路径（§2.8 第 3 条）✓；出战 op 执行序/弹窗帧不处理/免战 fallback（第 1 条）✓；弹窗主路径剧本并入 `test_cw_start_battle_action.py`（第 4 条）✓；无角色弹窗三门路径（第 2 条）✓。

## 3. import 冒烟记录

命令（`PYTHONPATH=src`）：

```
uv run python -c "import sr_od.application.currency_war.operations.cw_loop, \
  sr_od.application.currency_war.prep_actions, \
  sr_od.application.currency_war.kernel.cw_dispatch_tables, \
  sr_od.application.currency_war.kernel.cw_obs_core, \
  sr_od.application.currency_war.operations.cw_screen.cw_screen_prep, \
  sr_od.application.currency_war.operations.cw_op.cw_start_battle_action"
```

结果：零错（exit 0，无任何 traceback 输出）。

## 4. 动态跑局对照

已裁撤（landing 3.1 用户裁定 2026-11-18：版本适配期 sim 跑不完整属预期态；`compare_sim.py` 已入库备 sim 适配完成后复用）——本阶段不适用。
