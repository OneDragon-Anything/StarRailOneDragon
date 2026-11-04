# 工具原子七类(CwActionToolUseOp)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。**一篇覆盖七注册行**:七类共用一个 op 类(族文件先例,`cw_tool_use_action.py` 单类七行),机械执行部分同构,逐类差异在写入方申报与判据准入——以代码结构自然边界为准,本篇内逐类小节。

## 1. 动作是什么

拖拽使用装备注册表 category='工具' 的消耗品:owned 装备网格内工具 icon → 目标(装备件/角色槽位)机械拖曳。注册表七行(每动作类型一行)同指 `operations/cw_op/cw_tool_use_action.py::CwActionToolUseOp`(非终结;体迁自执行器,原 `prep_actions.py::PrepActionExecutor._use_tool` 薄委托已随死代码清偿移除,执行 = op 直执行 + 自上报):

| 动作类型(`kernel/cw_vocab.py` 清单中的类) | 注册名 | 字段形 |
|---|---|---|
| `FurnaceUse` | 冶金炉 | 双模式:`target_kind` ∈ equip/char + `item_name`(equip 分支)/ `row`+`slot`(char 分支)|
| `PrivilegeCardUse` | 特权赋予卡 | 双模式(同上)|
| `WrenchUse` | 拆装扳手 | `row` + `slot`(画面物理槽位 1 基)|
| `PrecisionWrenchUse` | 精密拆装扳手 | `row` + `slot` |
| `StaffProjectorUse` | 员工投影仪 | `row` + `slot` |
| `PerfectProjectorUse` | 完美投影仪 | `row` + `slot` |
| `LuckyTokenUse` | 好运令牌 | `row` + `slot` |

工具名解析表 = `CwActionToolUseOp._TOOL_NAME_BY_CLASS`(注册名 = icon 定位的稳定依据,与装备注册表同名)。七类均已登记(动作类型 union 与 `CW_ACTION_TYPES` 白名单皆在,注册表七行同指 `CwActionToolUseOp`)。

## 2. 逻辑态域集

状态容器(GameState)(GameState,游戏状态对象,下同)`equips` 域**有写**:消耗移除与效果写入同域**合并单笔**(确定面 `write_logic`/随机面 `write_logic_rand`,禁拆两笔);获得走 `gain_character` 获得链(投影仪复制);变异面不走链(冶金炉变异产物随机归观察);零写分支统一保留证据 `tool_*`。写入方权威版本 = `kernel/cw_action_report/tool_use.py` 七具名上报函数(`_REPORT_BY_CLASS` 按 param 类型解析,一族一文件先例),逐类语义与采样口径以函数 docstring 为权威版本。效果写入桥引用:`EQUIP_WRITE_SIDES` 登记面与效果桥四函数(`transform_equip_to_privilege`/`spawn_equip_bench_unit`/`grant_equip_item`/`settle_wrench_duplicate_gold`,均在用)——申报各工具效果分支的写入流向与组合收尾(逐件恰一个代码写入方,登记值共四形 bridge:/contribution:/op:/observation):

| 工具(分支)| 效果写入方(``EQUIP_WRITE_SIDES`` 申报;效果桥/收尾引用)|
|---|---|
| 冶金炉·equip | 负写入(不写)形态 `observation`(变异产物随机归观察)|
| 冶金炉·char | 变异产物随机归观察 |
| 特权赋予卡·equip(在用执行分支)| 库存替换桥 `cw_effect_inventory.transform_equip_to_privilege`(`bridge:` 形;映射单一源 = `privilege_counterpart`)|
| 特权赋予卡·char | 已穿装备原位变换桥 `transform_worn_equip_to_privilege` 已登记(「哪件被选」随机归观察;在用执行分支只消费库存替换)|
| 拆装扳手 | `op:` 形(执行域既有装备转移链)|
| 精密拆装扳手 | `contribution:equip_wrench_duplicate_gold`(重复获得 +1 金,零直写,组合写收尾 = 获得回执窗)|
| 员工投影仪 | 上报函数 `cw_action_report/tool_use.py::report_action_staff_projector_use_param`(费用门 ≤3 前置查,门值 3 = 调用位 `cost_gate=3`;原 `cw_affix_effects._TOOL_SPAWN_COST_GATE`/`cw_effect_inventory.STAFF_PROJECTOR_COST_GATE` 门表常量已随死代码清偿移除)→ 获得链 `cw_gain_chain.gain_character`(1★ 复制进席)|
| 完美投影仪 | 同员工投影仪,无费用门(`cost_gate=0`) |
| 好运令牌 | 入区桥 `cw_effect_inventory.grant_equip_item`(选定后确定面;判据面在用 fail-closed——读不到数据/条件不满足时默认走保守分支不动作,永不进准入)|

## 3. 确定面转移规则(逐条)

1. **机械执行**(七类同构):源件 = 工具 icon 按注册名定位(`PrepActionExecutor._owned_grid_locate`,名字唯一稳定依据)→ 目标 = equip 模式 owned 网格目标件 / char 模式角色槽位中心(`row`/`slot` 直取)→ mouse_move + drag_to → park_cursor;拖后固定等待(异步落地等待,非判效)——不做「是否已消耗」的交叉核对,消耗真值 = 下一帧装备区读数;
2. **截断类**:首件消费后网格 reflow → 工具原子动作的发出帧独占,后续网格目标动作下帧重评;
3. **上报写入方** = `kernel/cw_action_report/tool_use.py` 七具名上报函数(`_REPORT_BY_CLASS` 按 param 类型解析,op 机械执行后直调自己的上报函数):状态容器 `equips` 合并单笔写(消耗移除与效果写入同笔,禁拆两笔);获得分支(投影仪复制)走 `gain_character` 获得链,变异面(冶金炉)不走链随机归观察;效果写入桥/组合收尾引用 = §2 表(节点边界窗 `settle_node_boundary_gold` / 获得回执窗 `settle_wrench_duplicate_gold`,机理见 [op-effects.md](op-effects.md) §4);入席分支缺 `target_cost` = 调用错(缺费用会假过门,禁缺省放行),非进阶类别传入特权化/入区分支 = 调用错显式报错;
4. **基础行为与效果同笔字段写操作**:消耗品 −1、目标件消失、穿戴域迁移等 op 基础行为与效果写入**合并单笔**状态容器 `equips` 写(黑板帧面直写分支已随 `gs.prep_obs` 黑板停用删除——黑板帧已停用);消耗真值 = 下一入口完整观察装备区读数覆盖(截断点独占动作发出帧零窗口);
5. **判据准入** = `kernel/cw_equip_env.py::evaluate_tool_actions` → `admitted_tool_actions`(G1 准入,动作发出点禁第二套时机判断):冶金炉/特权赋予卡 = 判据准入放行(原子类发出);扳手/精密扳手/员工投影仪/完美投影仪/好运令牌 = 判据面 fail-closed(读不到数据/条件不满足时默认走保守分支不动作),动作发出点禁无判据发出(投影仪/令牌的 kernel 写入桥已备,接入调用 = 桥调用)。

## 4. 随机面

冶金炉变异产物 / 特权赋予卡拖角色分支「哪件被选」/ 好运令牌选件 = 随机面归观察(负写入申报,`EQUIP_WRITE_SIDES` observation 行);装备获得固定入栏序(`research/equipment_mechanics.md` §5)= 观察剪枝知识,不进逻辑态。

## 5. 拒绝语义

- owned 网格未定位到工具(已消耗/reflow)/ 未定位到目标件 = 未发出(`emitted=False`,下帧重派);
- `target_kind` 非法 / equip 分支缺目标件名 / row 或 slot 越界 = validate 拒(发出前输入契约拒绝);
- 投影仪拒落(超费用门/席满/目标未识别)= 视觉域帧面零写——席满不是部分成功,是无落位;桥面 `spawn_equip_bench_unit` 零写分支同形(cost_gate/席满/bench 未观察 → False 拒落);
- 特权赋予卡库存替换:库存未观察/无此件 → 桥返 None 零写;非进阶成品 = 调用错零写留观察。

## 6. kernel 符号锚

`kernel/cw_vocab.py` 七个动作类型类(`CwAction<Tool>UseParam`);`kernel/cw_action_report/tool_use.py`(七具名上报函数 + `_REPORT_BY_CLASS`,写入方权威版本;员工投影仪费用门值 3 = `report_action_staff_projector_use_param` 调用位);`kernel/cw_affix_effects.py::EQUIP_WRITE_SIDES` / `EQUIP_REWRITE_DECLARATIONS`(原 `_TOOL_SPAWN_COST_GATE`/`cw_effect_inventory.STAFF_PROJECTOR_COST_GATE` 门表常量已随死代码清偿移除);`kernel/cw_effect_inventory.py::privilege_counterpart` / `transform_equip_to_privilege` / `transform_worn_equip_to_privilege` / `spawn_equip_bench_unit` / `grant_equip_item` / `settle_wrench_duplicate_gold`;`kernel/cw_equip_env.py::evaluate_tool_actions` / `admitted_tool_actions`;`prep_actions.py::_owned_grid_locate`(机械原语);`operations/cw_op/cw_tool_use_action.py::CwActionToolUseOp`(`_TOOL_NAME_BY_CLASS`)。

## 7. 语义验证

写入方归属完备性 = 双层防漂移测试:`EQUIP_WRITE_SIDES` 键集恰等于 `EQUIP_REWRITE_DECLARATIONS`(逐件恰一个代码写入方,登记值四形封闭 + 目标函数可解析校验,import 时即显式报错),扫描命中集 vs 申报键集对齐归测试(`test_cw_affix_spec_registry`);桥/组合写的等价性 = 窗口独占契约(完全预测,失配等价推算 bug 走缺陷记录表,不静默不改道)。落地真值(消耗没消耗/变换没变换)= 下一帧装备区读数观察覆盖。

## 8. 先例注记(动作发出阶段)

备战期(档 1 判据准入放行原子类发出;档 2 判据面 fail-closed 永不进准入)。商店期无本族。

## 9. 依据

`kernel/cw_affix_effects.py` `_validate_equip_write_sides`(防漂移测试)与 `EQUIP_WRITE_SIDES`(效果写入桥申报);`kernel/cw_action_report/tool_use.py` 模块头(上报写入方权威版本:合并单笔/获得走链/变异面不走链/零写保留证据);`kernel/cw_effect_inventory.py` 写入桥段(窗口独占性分形判据);`operations/cw_tool_use_action.py` 模块头(一类覆盖七行);[fields.md](../fields.md) §4.2 RunTools 行/ §5.3(效果族归属四选一);[op-effects.md](op-effects.md) §4(写入桥机理);`research/equipment_mechanics.md` §5(工具 7 件全量)。
