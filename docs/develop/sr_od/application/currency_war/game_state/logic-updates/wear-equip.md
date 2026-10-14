# 穿装备(WearEquip)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。

## 1. 动作是什么

把 owned 装备库存网格内的一件拖到目标角色的已穿槽位。动作类型(`kernel/cw_vocab.py` 清单中的类)= `CwActionWearEquipParam`(已登记动作类型类,注册行 = 备战域 op;坐标参数化机械动作:字段 `item_name` / `char_name`('' = front-only 回退步)/ `row` ∈ front/back / `slot` = 画面物理槽位 1 基)。op 载体 = `operations/cw_op/cw_wear_equip_action.py::CwActionWearEquipOp`(非终结;体迁自执行器,`prep_actions.py::PrepActionExecutor._wear_equip` 薄委托)。**动作发出形态(穿戴原子通路)** = 决策核逐帧发出 WearEquip 序,发出顺序即执行顺序;计划构造 kernel 单一源 = `kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`(决策侧逐帧现算,构造点唯一;`EquipWearStep` 为动作构造源,branch = m7 角色级分配 / front_only 身份读失败回退)。

## 2. 逻辑态域集

容器(GameState,游戏状态对象,下同)`equips` 域**有写**:owned −1(已登记才减),上报函数单点。tracked 写账随动作同步(op 自上报 `report_action_wear_equip_param` 内聚):

| 账 | 负责写入的代码 | 内容 |
|---|---|---|
| equips 域 | op 自上报 `kernel/cw_action_report/wear_equip.py::report_action_wear_equip_param`(op 零 game state 直写)| owned 库存 −1 件(`gs.equips` write_logic,evidence `owned[<件>] -1(穿戴)`;owned 无此件 = 只跳该侧)+ 目标角色 equips +1(物理 (row, slot) 内联换算)|

落地真值(穿没穿)= 观察写入边对账(下一入口装备区读数覆盖)。**零窗口申报**:WearEquip = 截断点(独占动作发出帧),发出即本次访问结束 → 下一入口完整观察装备区实读覆盖,同一访问内无后续帧消费。(原「视觉域黑板帧摘件分支」随 `gs.prep_obs` 黑板停用删除——黑板帧已停用。)

## 3. 确定面转移规则(逐条)

1. **机械执行**:目标拖点 = `PrepActionExecutor._equip_slot_drag_point(row, slot)`(前排 = 「前排-N」rect 中心 x、y1+21(D-36 校准);后排 = 布局选档 `obs/cw_back_layout.py::select_back_layout` 同式派生;缺失 = None 禁兜底坐标)→ 源件 = owned 网格按名定位 `_owned_grid_locate(item_name)`(名字定位是唯一稳锚,网格 reflow 使快照坐标失真)→ 固定等待 `PREP_DRAG_SETTLE_WAIT_S`(等备战面板/上件 reflow 动画收尾,非判效)→ mouse_move + drag_to + park_cursor;
2. **tracked 双侧**(上报函数 `report_action_wear_equip_param`):owned 侧 = `gs.equips` 现读-摘件-回写;目标角色 equips 追加(槽位表下标 = 排内槽号内联换算,槽位空 = 跳过);角色装备上限 = `kernel/cw_comps.py::EQUIP_CAPACITY`(计划面容量扣减消费);
3. **零比对出生**:动作 op 内零 CV-diff 验穿——穿没穿归观察写入边对账;原 avatar-slot CV-diff 验穿面已删除(机械执行零判效纪律——发出后不读屏验证是否生效),考古归 git;
4. **穿着即合成**(已登记建模裁定):两件可合成组件穿到同一角色 = 自动合成;**不记合成预期值**([fields.md](../fields.md) §4.1 豁免)——该豁免是建模裁定,不是知识缺口;后果走观察覆盖 + 缺陷记录表。

## 4. 随机面

无确定性随机(穿着合成产物 = 注册表配方确定,但按豁免不记预期值)。

## 5. 拒绝语义

- 装备槽位坐标缺失 / owned 网格未定位到目标件 = 未发出(`emitted=False`,「计划失效」通道,下帧重派重算);
- row/slot 越界 = validate 拒(发出前输入契约拒绝);
- 上报函数 owned 无此件 = 只跳 owned 侧(机械动作仍发出,tracked 侧照记);
- 拖拽静默不生效 = 零判效(发出后不读屏验证是否生效),下一入口完整观察实读对账把差异暴露出来(账实失配 → 失配告警停机 → 按真 bug 修,重试 = 决策循环按新观察自然重派;同 [deploy-move.md](deploy-move.md) §5)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionWearEquipParam`;`kernel/cw_action_report/wear_equip.py::report_action_wear_equip_param`(tracked 写入分支)/ 内联换算;`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan` / `EquipWearStep`(四路输入容器读口);`kernel/cw_comps.py::EQUIP_CAPACITY`;`prep_actions.py::PrepActionExecutor._wear_equip` / `_owned_grid_locate` / `_equip_slot_drag_point` / `PREP_DRAG_SETTLE_WAIT_S`;`operations/cw_op/cw_wear_equip_action.py::CwActionWearEquipOp`;`obs/cw_back_layout.py::select_back_layout`。

## 7. 语义验证

WearEquip = 容器写语义动作(非零写族成员):容器 `equips` 域 owned −1(已登记才减)+ 目标角色 equips +1,两处写入内聚于上报函数 `report_action_wear_equip_param` 单点(行为锁 = `test_cw_unified_action_2a` 动作类型覆盖锁容器写集断言);落地真值(穿没穿)归观察边界 reconcile。

## 8. 判例注记(动作发出阶段)

备战期(穿戴 = 备战期发出的动作,动作发出点 = mandate M7 装备计划;商店期无穿戴动作)。

## 9. 依据

[../action-logic-state.md](../action-logic-state.md)(视觉域动作容器零写契约);`kernel/cw_action_report/wear_equip.py::report_action_wear_equip_param` docstring(发出即记账形态与 session 跳过申报);`kernel/cw_equip_wear_plan.py` 模块头(计划构造迁居/构造点唯一);[fields.md](../fields.md) §4.1(穿着即合成豁免)/ §4.2 RunEquip 行(基础行为面);`research/equipment_mechanics.md` §1(穿着即合成/装备上限 3 件)。
