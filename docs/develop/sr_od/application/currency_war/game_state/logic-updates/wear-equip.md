# 穿装备(WearEquip)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。

## 1. 动作是什么

把 owned 装备库存网格内的一件拖到目标角色的已穿槽位。词表 = `kernel/cw_vocab.py::CwActionWearEquipParam`(坐标参数化机械动作:字段 `item_name` / `char_name`('' = front-only 回退步)/ `row` ∈ front/back / `slot` = 画面物理槽位 1 基;**不在 `cw_vocab.py::Action` 联合内**——零容器动作转移语义,同「视觉域动作容器零写」契约)。op 载体 = `operations/cw_op/cw_wear_equip_action.py::CwActionWearEquipOp`(非终结;体迁自执行器,`prep_actions.py::PrepActionExecutor._wear_equip` 薄委托)。发射形态(R2 穿戴原子通路)= 决策核逐帧发 WearEquip 序,发射序即执行序;计划构造 kernel 单一源 = `kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`(决策侧逐帧现算,构造点唯一;`EquipWearStep` 为动作构造源,branch = m7 角色级分配 / front_only 身份读失败回退)。

## 2. 逻辑态域集

容器 GameState `equips` 域**不写**(零写族申报 = `zero_writes.py` 集中承载,留观察覆盖)。tracked 写账随动作同步(op 自上报 `report_action_wear_equip_param` 内聚):

| 账 | 写端 | 内容 |
|---|---|---|
| tracked(执行账)| op 自上报 `kernel/cw_action_report/wear_equip.py::report_action_wear_equip_param`(session 形参在场时执行;op 零 game state 直写)| owned 库存 −1 件(`gs.equips` write_logic,evidence `owned[<件>] -1(穿戴)`;owned 无此件 = 只跳该侧)+ tracked 目标角色 equips +1(物理 (row, slot) → `deployed_idx_of` 换算)|

落地真值(穿没穿)= 观察写入边对账(下一入口装备区读数覆盖)。**零窗口申报**:WearEquip = 截断点(独占发射帧),发出即 visit 结束 → 下一入口 heavy 装备区实读覆盖,无同 visit 后续帧消费——容器 `equips` 零写无暴露窗。(原「视觉域黑板帧摘件腿」随 `gs.prep_obs` 黑板退役删除——迭代 2026-09-18-prep-obs-retirement 阶段 3.5。)

## 3. 确定面转移规则(逐条)

1. **机械执行**:目标拖点 = `PrepActionExecutor._equip_slot_drag_point(row, slot)`(前排 = 「前排-N」rect 中心 x、y1+21(D-36 校准);后排 = 布局选档 `obs/cw_back_layout.py::select_back_layout` 同式派生;缺失 = None 禁兜底坐标)→ 源件 = owned 网格按名定位 `_owned_grid_locate(item_name)`(名字定位是唯一稳锚,网格 reflow 使快照坐标失真)→ `_wait_stable_frame`(输入条件化等待,非判效)→ mouse_move + drag_to + park_cursor;
2. **tracked 双侧**(上报函数 `report_action_wear_equip_param`):owned 侧 = `gs.equips` 现读-摘件-回写;tracked 侧 = dep[idx].equips 追加(目标槽位表下标 = `deployed_idx_of(row, slot)`,槽位空 = 跳过;session 缺席 = tracked 腿跳过);角色装备上限 = `kernel/cw_comps.py::EQUIP_CAPACITY`(计划面容量扣减消费);
3. **零比对出生(裁决 3)**:动作 op 内零 CV-diff 验穿——穿没穿归观察写入边对账;原 avatar-slot CV-diff 验穿面已删除(机械执行零判效纪律),考古归 git;
4. **穿着即合成**(在册建模裁定):两件可合成组件穿到同一角色 = 自动合成;**不记合成预期值**([fields.md](../fields.md) §4.1 豁免)——该豁免是建模裁定,不是知识缺口;后果走观察覆盖 + 缺陷台账。

## 4. 随机面

无确定性随机(穿着合成产物 = 注册表配方确定,但按豁免不记预期值)。

## 5. 拒绝语义

- 装备槽位坐标缺失 / owned 网格未定位到目标件 = 未发出(`emitted=False`,「计划失效」通道,下帧重派重算);
- row/slot 越界 = validate 拒(发出前输入契约拒绝);
- 上报函数 owned 无此件 = 只跳 owned 侧(机械动作仍发出,tracked 侧照记);
- 拖拽静默不生效 = 零判效,下一入口 heavy 实读对账显影(账实失配 → 安灯停 → 按真 bug 修,重试 = 决策循环按新观察自然重派;同 [deploy-move.md](deploy-move.md) §5)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionWearEquipParam`;`kernel/cw_action_report/wear_equip.py::report_action_wear_equip_param`(tracked 腿)/ `deployed_idx_of`;`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan` / `EquipWearStep`(四路输入容器读口,迭代阶段 3.2 换源);`kernel/cw_comps.py::EQUIP_CAPACITY`;`prep_actions.py::PrepActionExecutor._wear_equip` / `_owned_grid_locate` / `_equip_slot_drag_point` / `_wait_stable_frame`;`operations/cw_op/cw_wear_equip_action.py::CwActionWearEquipOp`;`obs/cw_back_layout.py::select_back_layout`。

## 7. 语义验证

WearEquip 不在 `cw_vocab.py::Action` 联合内,零局内资源推进语义,**零写族成员**(登记面申报 = `zero_writes.py`,行为锁 = `test_cw_unified_action_2a` 词表覆盖锁零写集断言:write_seq 不变);tracked 账随动作同步,落地真值归观察边界 reconcile。本动作容器 `equips` 域零写(tracked 腿 = op 自上报单点)。

## 8. 判例注记(发射期)

备战期(穿戴 = 备战期发射面,发射位 = mandate M7 装备计划;商店期无穿戴动作)。

## 9. 依据

[../action-logic-state.md](../action-logic-state.md)(视觉域动作容器零写契约);`kernel/cw_action_report/wear_equip.py::report_action_wear_equip_param` docstring(发出即记账形态与 session 跳过申报);`kernel/cw_equip_wear_plan.py` 模块头(计划构造迁居/构造点唯一);[fields.md](../fields.md) §4.1(穿着即合成豁免)/ §4.2 RunEquip 行(基础行为面);`research/equipment_mechanics.md` §1(穿着即合成/装备上限 3 件)。
