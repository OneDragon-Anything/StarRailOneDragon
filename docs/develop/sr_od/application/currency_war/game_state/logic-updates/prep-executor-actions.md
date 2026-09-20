# 备战执行器机制(备战域动作族总述)

> 归属:[logic-updates/](README.md) 索引下**执行器机制总述**——只写执行器机制/编排与族共通面;逐动作逻辑态全在专篇(索引见 §4 边界),总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 执行器与发射形态

备战域原子动作经统一执行器 `prep_actions.py::PrepActionExecutor` 机械执行(持 ctx + 宿主 op 复用截图/拖拽原语):**发出即职责完成,零验证零判效**(最严读法:点击/拖拽后不读屏判「是否生效」,落地判定完全归观察侧 reconcile)。词表单一源 = `kernel/cw_vocab.py`(`CwAction` 基类 + 全动作类 + 白名单 `CW_ACTION_TYPES`;执行器 `validate` 两层 = 白名单 + 静态参数)。

**坐标系二分(实现现况)**:席位域动作(SellBench/SellDeployed/DeployMove)携**容器槽位表下标 0 基**(bench 0-8 / deployed 0-9,观察面读口 `bench_view_slots_of`/`deployed_rows_of` 同基直取零换算;DeployMove 落位另携载荷 `(to_row, to_slot)` 直指,执行边零现读);**画面物理槽位 1 基**仅存于坐标参数化机械动作(WearEquip/工具七类/OpenBox/OpenTome/OpenBookcard)的 `row`/`slot` 字段。执行坐标边换算单点 = `kernel/cw_exec_state.py::deployed_row_slot`(下标→物理排槽)/ `deployed_idx_of`(物理→下标)。

**发射形态(R2 原子通路)**:决策核逐帧发原子动作(部署 = DeployMove 序/穿戴 = WearEquip 序/卖出 = SellBench/SellDeployed),备战环逐帧执行决策输出的恰一个动作(None = 本帧无动作,交回外循环重观察);组合壳(RunDeploy/RunEquip/RunTools)已退役。发射位计划构造单一源 = `strategies/impl/mandate_v1/deploy_plan.py::deploy_plan_moves`(部署;选人 `select_deployments_reasoned` + 排路由 `deploy_row_pref` + 槽位 `deploy_slot_plans`)、`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`(穿戴)。

**执行器三件套(每动作同构)**:①机械执行(`_dispatch_action` 经注册表 `action_op_class_for` 分派,`emitted` = 发出事实,False 只用于执行前输入契约拒绝);②tracked 主账同步(`_track_remove_bench`/`_track_remove_deployed`/`_track_move_deployed`,置 None 不移位,摘除腿照常执行只显影不拒写);③效果随 op 自上报(动作 op 内直调自己的上报函数,`kernel/cw_action_report/` 函数族 = 效果内聚单点)+ 执行点金差显影(`_executed_gold_delta`:卖 = +`sell_refund`、CollectOre = None、其余 0/未发出 None——**仅进回执 extra 留证,不经它直推容器金账**;容器金账唯一写点 = 上报函数 `report_action_sell_bench_param`/`report_action_sell_deployed_param`,执行缝直推腿已退役防双记)+ 回执域(`note_action_receipt`)与 journal 行。

## 2. 卖出族共通执行面(SellBench / SellDeployed)

逐动作逻辑态全文见 [sell-bench.md](sell-bench.md) / [sell-deployed.md](sell-deployed.md);本节只留执行器侧共通面:执行器拖槽中心 → 出售区(`sell_point` 单一源,area 缺失 RuntimeError 禁兜底坐标);卖出动画 1s 等待(`research/screen_flow_timing.md` #21 口径);tracked 摘除 = 按下标置 None(信息位/下标脱节不再按 slot 重构);执行点金差(`_executed_gold_delta`)按 `sell_refund` 进回执 extra 留证——容器金账唯一写点 = 上报函数(`report_action_sell_bench_param`/`report_action_sell_deployed_param`),执行缝无金腿(SellDeployed 的 owned 恢复腿内聚于上报函数,见 sell-deployed.md §2)。

## 3. 词表完备性注:SwapDeploy(上阵↔备战对调;非注册行)

词表 + 容器逻辑态直写 + sim 消费在役,**生产执行器未接线**(备战域部署换位经部署机拖拽承载);**不经注册表分发**,不在 [README.md](README.md) 注册行映射内。逻辑态规则(规则在册,供接线/sim 消费):deployed 下标 `d_idx` 与 bench 下标 `b_idx` **原槽对调**(置空不移位坐标系);上场者继承下场者的排(含开拓者形态归一,归一核 = `cw_exec_state.trailblazer_row_identity` 与 deploy/swap 上报同源),`Unit.slot` 信息位重写;board 派生随写(front/back rows 行写挂钩 `_resync_board_delta`,本腿禁手写);拒绝 = 同名同星已在场其余位(`duplicate_on_board`)/ expect 双侧失配(陈旧提案)/槽空越界。装备随人走(对象迁移)。kernel 锚 = `kernel/cw_action_report/swap_deploy.py::report_action_swap_deploy_param`、`kernel/cw_vocab.py::mutate_bench_deployed` SwapDeploy 分支(W43 裁决 1/2 代际校验 + 同名唯一性)。

## 4. 边界(逐动作逻辑态专篇索引)

备战域注册行逐动作专篇:[sell-bench.md](sell-bench.md) / [sell-deployed.md](sell-deployed.md) / [level-up.md](level-up.md) / [deploy-move.md](deploy-move.md) / [wear-equip.md](wear-equip.md) / [collect-ore.md](collect-ore.md) / [open-box.md](open-box.md) / [open-tome.md](open-tome.md) / [open-bookcard.md](open-bookcard.md) / [tools.md](tools.md);转场与事件线:[start-battle.md](start-battle.md) / [open-shop.md](open-shop.md) / pick 族五篇(pick-*.md)。全集映射(26 注册行)见 [README.md](README.md)。

## 5. 依据

[../action-logic-state.md](../action-logic-state.md) §3/§3A/§1.4(执行态跟踪账落点);`prep_actions.py` 模块头(执行器坐标系与「发出即职责完成」契约);`kernel/cw_action_report/` 包 `__init__` docstring(上报函数族规约与双域腿统一申报);`kernel/cw_exec_state.py` ADR-0316/ADR-0392 槽位语义注;[fields.md](../fields.md) §4.2(基础行为面);`research/merge_mechanics.md` §3(同名唯一恒成立);`research/equipment_mechanics.md` §1(穿着即合成/装备上限 3 件)。
