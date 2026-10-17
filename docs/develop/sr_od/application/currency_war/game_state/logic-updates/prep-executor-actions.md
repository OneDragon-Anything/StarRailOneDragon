# 备战执行器机制(备战域动作族总述)

> 归属:[logic-updates/](README.md) 索引下**执行器机制总述**——只写执行器机制/编排与族共通面;逐动作逻辑态全在专篇(索引见 §4 边界),总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 执行器与动作发出形态

备战域原子动作经统一执行器 `prep_actions.py::PrepActionExecutor` 机械执行(持 ctx + 宿主 op 复用截图/拖拽原语):**发出即职责完成,零验证零判效**(最严读法:点击/拖拽后不读屏判「是否生效」,落地判定完全归观察侧 reconcile)。动作类型单一源 = `kernel/cw_vocab.py`(全动作类 `CwAction<Xxx>Param` 摊平为独立 dataclass + 运行时白名单 `CW_ACTION_TYPES`;`CwAction` 名 = 全动作 union 别名,注解与 isinstance 兼容面;执行器 `validate` 两层 = 白名单 + 静态参数)。

**坐标系二分(实现现况)**:席位域动作(SellBench/SellDeployed/DeployMove)携**容器(GameState,游戏状态对象,下同)槽位表下标 0 基**(bench 0-8 / deployed 0-9,观察面读口 `bench_view_slots_of`/`deployed_rows_of` 同基直取零换算;DeployMove 落位另携载荷 `(to_row, to_slot)` 直指,执行边零现读);**画面物理槽位 1 基**仅存于坐标参数化机械动作(WearEquip/工具七类/OpenBox/OpenTome/OpenBookcard)的 `row`/`slot` 字段。执行坐标边换算单点 = 排内槽号 ↔ 子表下标内联算术(工作表桥 = `cw_exec_state.deployed_indexed_of_view`/`deployed_view_of_indexed`)。

**动作发出形态(原子通路)**:决策核逐帧发出原子动作(部署 = DeployMove 序/穿戴 = WearEquip 序/卖出 = SellBench/SellDeployed),备战环逐帧执行决策输出的恰一个动作(None = 本帧无动作,返回主循环重新观察);组合壳(RunDeploy/RunEquip/RunTools)已停用。动作发出点的计划构造单一源 = `strategies/impl/mandate_v1/deploy_plan.py::deploy_plan_moves`(部署;选人 `select_deployments_reasoned` + 排路由 `deploy_row_pref` + 槽位 `deploy_slot_plans`)、`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`(穿戴)。

**执行器三件套(每动作同构)**:①机械执行(`_dispatch_action` 经注册表 `action_op_class_for` 分派,`op_success` = round 结果成功态,False 只用于执行前输入契约拒绝);②席位主域直写(上报函数直写 bench/deployed,置 empty 不移位,摘除分支照常执行只把差异暴露出来不拒写);③效果随 op 自上报(动作 op 内直调自己的上报函数,`kernel/cw_action_report/` 函数族 = 效果内聚单点)+ 回执域(`note_action_receipt`,受阻事实 = `reason` 码,见 fields.md 回执契约节)与 journal 行。执行点金差已退役(executor-gold-delta-retire 批)——容器金账唯一写入位置 = 上报函数 `report_action_sell_bench_param`/`report_action_sell_deployed_param`,执行侧直推分支已停用防双记。

## 2. 卖出族共通执行面(SellBench / SellDeployed)

逐动作逻辑态全文见 [sell-bench.md](sell-bench.md) / [sell-deployed.md](sell-deployed.md);本节只留执行器侧共通面:执行器拖槽中心 → 出售区(`sell_point` 单一源,area 缺失 RuntimeError 禁兜底坐标);卖出动画 1s 等待(`research/screen_flow_timing.md` #21 口径);tracked 摘除 = 按下标置 None(信息位/下标脱节不再按 slot 重构);容器金账唯一写入位置 = 上报函数(`report_action_sell_bench_param`/`report_action_sell_deployed_param`),执行侧无金币写入分支(SellDeployed 的 owned 恢复写入内聚于上报函数,见 sell-deployed.md §2);金归属证据链 = journal 写行归因 + 账实对账告警(executor-gold-delta-retire 批,原执行点金差回执键随批退役)。

## 3. 动作类型完备性注:SwapDeploy(上阵↔备战对调;非注册行)

动作类型 + 容器逻辑态直写 + sim 消费在用,**生产执行器未接线**(备战域部署换位 = DeployMove 原子序,部署机画面 op 已停用);**不经注册表分发**,不在 [README.md](README.md) 注册行映射内。逻辑态规则(规则已登记,供接线/sim 消费):deployed 下标 `d_idx` 与 bench 下标 `b_idx` **原槽对调**(置空不移位坐标系);上场者继承下场者的排(含开拓者形态归一,归一核 = `cw_exec_state.trailblazer_row_identity` 与 deploy/swap 上报同源),;board 派生随写(front/back rows 行写挂钩 `_resync_board_delta`,禁止在本分支手写);拒绝 = 同名同星已在场其余位(`duplicate_on_board`)/ expect 双侧失配(陈旧提案)/槽空越界。装备随人走(对象迁移)。kernel 符号锚 = `kernel/cw_action_report/swap_deploy.py::report_action_swap_deploy_param`、上报函数 SwapDeploy 分支(代际校验 + 同名唯一性)。

## 4. 边界(逐动作逻辑态专篇索引)

备战域注册行逐动作专篇:[sell-bench.md](sell-bench.md) / [sell-deployed.md](sell-deployed.md) / [level-up.md](level-up.md) / [deploy-move.md](deploy-move.md) / [wear-equip.md](wear-equip.md) / [collect-ore.md](collect-ore.md) / [open-box.md](open-box.md) / [open-tome.md](open-tome.md) / [open-bookcard.md](open-bookcard.md) / [tools.md](tools.md);转场与事件线:[start-battle.md](start-battle.md) / [open-shop.md](open-shop.md) / pick 族专篇五篇(其余行缺档,见 [README.md](README.md) 索引)。全集映射见 [README.md](README.md)(计数以注册表现值为准)。

## 5. 依据

[../action-logic-state.md](../action-logic-state.md) §3/§3A/§1.5(执行态跟踪账落点);`prep_actions.py` 模块头(执行器坐标系与「发出即职责完成」契约);`kernel/cw_action_report/` 包 `__init__` docstring(上报函数族规约与两个数据域写入统一申报);`kernel/cw_exec_state.py` /槽位语义注;[fields.md](../fields.md) §4.2(基础行为面);`research/merge_mechanics.md` §3(同名唯一恒成立);`research/equipment_mechanics.md` §1(穿着即合成/装备上限 3 件)。
