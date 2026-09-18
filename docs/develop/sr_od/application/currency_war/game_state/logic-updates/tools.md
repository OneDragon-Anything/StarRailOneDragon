# 工具原子七类(ToolUseOp)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。**一篇辖七注册行**:七类共用一个 op 类(族文件先例,`cw_tool_use_action.py` 单类七行),机械半同构,逐类差异在写端申报与判据准入——以代码结构自然边界为准,本篇内逐类小节。

## 1. 动作是什么

拖拽使用装备注册表 category='工具' 的消耗品:owned 装备网格内工具 icon → 目标(装备件/角色槽位)机械拖曳。注册表七行(每词表类一行)同指 `operations/cw_op/cw_tool_use_action.py::ToolUseOp`(非终结;体迁自执行器,`prep_actions.py::PrepActionExecutor._use_tool` 薄委托):

| 词表类(`kernel/cw_vocab.py`) | 注册名 | 字段形 |
|---|---|---|
| `FurnaceUse` | 冶金炉 | 双模式:`target_kind` ∈ equip/char + `item_name`(equip 腿)/ `row`+`slot`(char 腿)|
| `PrivilegeCardUse` | 特权赋予卡 | 双模式(同上)|
| `WrenchUse` | 拆装扳手 | `row` + `slot`(画面物理槽位 1 基)|
| `PrecisionWrenchUse` | 精密拆装扳手 | `row` + `slot` |
| `StaffProjectorUse` | 员工投影仪 | `row` + `slot` |
| `PerfectProjectorUse` | 完美投影仪 | `row` + `slot` |
| `LuckyTokenUse` | 好运令牌 | `row` + `slot` |

工具名解析表 = `ToolUseOp._TOOL_NAME_BY_CLASS`(注册名 = icon 定位锚,与装备注册表同名)。七类均在 `cw_vocab.py::Action` 联合外(零容器动作转移语义)。

## 2. 逻辑态域集

容器 GameState `equips` 域零直写契约(域集封闭申报)——本族逻辑态 = **视觉域帧面 + 执行写端**两账,写端归属申报单一源 = `kernel/cw_affix_effects.py::EQUIP_WRITE_SIDES`(逐件恰一个落码写端,值词表四形 bridge:/contribution:/op:/observation):

| 工具(腿)| 视觉域帧面(`_project_tool_obs` 直写)| 执行写端(`apply_tool_execution_write` 分派)|
|---|---|---|
| 冶金炉·equip | 工具 −1 + 目标件消失 | 负写端 `observation`(变异产物随机归观察)|
| 冶金炉·char | 工具 −1 + 目标角色穿戴域 → 库存域全量迁移(名迁移)| 变异产物随机归观察 |
| 特权赋予卡·equip(现役执行臂)| 工具 −1 + 目标件名确定变换(帧面镜像)| 库存腿桥 `cw_effect_inventory.transform_equip_to_privilege`(`bridge:` 形;映射单一源 = `privilege_counterpart`)|
| 特权赋予卡·char | 只写工具 −1 | 穿域腿桥 `transform_worn_equip_to_privilege` 在册(「哪件被选」随机归观察;现役执行臂只消费库存腿)|
| 拆装扳手 | 目标角色穿戴域全量回库存 + 工具 −1 | `op:` 形(执行域既有装备转移链锚)|
| 精密拆装扳手 | 同扳手,**不消耗**(工具库存面不递减)| `contribution:equip_wrench_duplicate_gold`(重复获得 +1 金,零直写,组合写收口 = 获得回执窗)|
| 员工投影仪 | 1★ 复制入备战席 + 工具 −1(超门/席满/目标未识别 = 拒落零写)| 入席腿桥 `cw_effect_inventory.spawn_equip_bench_unit`(费用门表 `cw_affix_effects._TOOL_SPAWN_COST_GATE`,数值单一源 = `cw_effect_inventory.STAFF_PROJECTOR_COST_GATE`)|
| 完美投影仪 | 同员工投影仪,无费用门 | 同上(gate 0)|
| 好运令牌 | 只写工具 −1 | 入区腿桥 `cw_effect_inventory.grant_equip_item`(选定后确定面;判据面现役 fail-closed,永不进准入)|

## 3. 确定面转移规则(逐条)

1. **机械执行**(七类同构):源件 = 工具 icon 按注册名定位(`PrepActionExecutor._owned_grid_locate`,名字唯一稳锚)→ 目标 = equip 模式 owned 网格目标件 / char 模式角色槽位中心(`row`/`slot` 直取)→ mouse_move + drag_to → park_cursor;拖后固定等待(异步落地等待,非判效)——零消耗确认对拍,消费真值 = 下一帧装备区读数;
2. **截断类**:首件消费后网格 reflow → 工具原子发射帧独占,后续网格目标动作下帧重评;
3. **执行写端分派** = `kernel/cw_affix_effects.py::apply_tool_execution_write`(工具族七件拖拽/使用回执统一入口):bridge 形逐腿执行(入席/入区/库存特权化/穿域特权化),op 形与负写端(observation)零写留证,contribution 形零写并指回组合收口(节点边界窗 `settle_node_boundary_gold` / 获得回执窗 `settle_wrench_duplicate_gold`,机理见 [op-effects.md](op-effects.md) §4);入参契约:入席腿缺 `target_cost` = 调用错(缺费用会假过门,禁缺省放行),非进阶类别传入特权化/入区腿 = 调用错显式炸;
4. **基础行为不在执行写端口**:消耗品 −1、目标件消失、穿戴域迁移等 op 基础行为 = 视觉域帧面直写(`cw_screen_prep.py::_project_tool_obs` 按 `EQUIP_WRITE_SIDES` 申报逐类落),执行写端口只管**效果**写端(两面对照分工,防双写);
5. **判据准入** = `kernel/cw_equip_env.py::evaluate_tool_actions` → `admitted_tool_actions`(G1 准入,发射位禁第二套时机判断):冶金炉/特权赋予卡 = 判据准入放行(原子类发射);扳手/精密扳手/员工投影仪/完美投影仪/好运令牌 = 判据面 fail-closed,发射位禁无判据发射(投影仪/令牌的 kernel 写端桥已备,接线 = 桥调用)。

## 4. 随机面

冶金炉变异产物 / 特权赋予卡拖角色腿「哪件被选」/ 好运令牌选件 = 随机面归观察(负写端申报,`EQUIP_WRITE_SIDES` observation 行);装备获得固定入栏序(`research/equipment_mechanics.md` §5)= 观察剪枝知识,不进逻辑态。

## 5. 拒绝语义

- owned 网格未定位到工具(已消耗/reflow)/ 未定位到目标件 = 未发出(`emitted=False`,下帧重派);
- `target_kind` 非法 / equip 腿缺目标件名 / row 或 slot 越界 = validate 拒(发出前输入契约拒绝);
- 投影仪拒落(超费用门/席满/目标未识别)= 视觉域帧面零写——席满不是部分成功,是无落位;桥面 `spawn_equip_bench_unit` 零写分支同形(cost_gate/席满/bench 未观察 → False 拒落);
- 特权赋予卡库存腿:库存未观察/无此件 → 桥返 None 零写;非进阶成品 = 调用错零写留观察。

## 6. kernel 符号锚

`kernel/cw_vocab.py` 七词表类;`kernel/cw_affix_effects.py::EQUIP_WRITE_SIDES` / `apply_tool_execution_write` / `_TOOL_SPAWN_COST_GATE` / `EQUIP_REWRITE_DECLARATIONS`;`kernel/cw_effect_inventory.py::privilege_counterpart` / `transform_equip_to_privilege` / `transform_worn_equip_to_privilege` / `spawn_equip_bench_unit` / `grant_equip_item` / `STAFF_PROJECTOR_COST_GATE` / `settle_wrench_duplicate_gold`;`kernel/cw_equip_env.py::evaluate_tool_actions` / `admitted_tool_actions`;`prep_actions.py::PrepActionExecutor._use_tool` / `_owned_grid_locate`;`operations/cw_op/cw_tool_use_action.py::ToolUseOp`(`_TOOL_NAME_BY_CLASS`);`operations/cw_screen/cw_screen_prep.py::_project_tool_obs`。

## 7. 语义验证

写端归属完备性 = 双层防漂移锁:`EQUIP_WRITE_SIDES` 键集恰等于 `EQUIP_REWRITE_DECLARATIONS`(逐件恰一个落码写端,值词表封闭 + 目标函数可解析校验,import 即炸),扫描命中集 vs 申报键集对齐归测试锁(`test_cw_affix_spec_registry`);桥/组合写的等价性 = 窗口独占契约(完全预测,失配等价推算 bug 走缺陷台账,不静默不改道)。落地真值(消耗没消耗/变换没变换)= 下一帧装备区读数观察覆盖。

## 8. 判例注记(发射期)

备战期(档 1 判据准入放行原子类发射;档 2 判据面 fail-closed 永不进准入)。商店期无本族。

## 9. 依据

`kernel/cw_affix_effects.py::apply_tool_execution_write` docstring(四形分派与入参契约)与 `_validate_equip_write_sides`(防漂移锁);`cw_screen_prep.py::_project_tool_obs` docstring(逐类帧面申报);`kernel/cw_effect_inventory.py` 写端桥段(窗口独占性分形判据);`operations/cw_tool_use_action.py` 模块头(一类辖七行);[fields.md](../fields.md) §4.2 RunTools 行/ §5.3(效果族归属四选一);[op-effects.md](op-effects.md) §4(写端桥机理);`research/equipment_mechanics.md` §5(工具 7 件全量)。
