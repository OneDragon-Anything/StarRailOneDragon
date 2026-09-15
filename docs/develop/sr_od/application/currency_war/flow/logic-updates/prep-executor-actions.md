# 备战执行器动作族(部署/卖/移位/穿装)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。本篇四动作 = `DeployMove`(部署 = 备战席 → 上阵移位)/`SellBench`(卖备战)/`SellDeployed`(卖上阵)/`WearEquip`(穿装备);卖与部署的独立细节另见 [sell-bench.md](sell-bench.md) / [sell-deployed.md](sell-deployed.md),本篇给族共通面与执行器坐标系。

## 1. 动作族与执行器

备战域原子动作经统一执行器 `prep_actions.py::PrepActionExecutor` 机械执行(持 ctx + 宿主 op 复用截图/拖拽原语):**发出即职责完成,零验证零判效**(T-223:点击/拖拽后不读屏判「是否生效」,落地判定完全归观察侧 reconcile)。词表单一源 = `kernel/cw_vocab.py`(`CwAction` 基类 + 全动作类 + 白名单 `CW_ACTION_TYPES`;执行器 `validate` 两层 = 白名单 + 静态参数)。

**文档-实现偏差(词表白名单载体)**:action-logic-state.md §3 头原文「备战域动作词表 = kernel/cw_prep_actions.py::PREP_ACTION_TYPES 白名单」;实况 = 统一词表归一(unified-action-factory 批2b)后 `PREP_ACTION_TYPES` 退役,单一源 = `kernel/cw_vocab.py::CW_ACTION_TYPES`(漏登记 = 执行面拒「未知动作类型」,动作从未真正执行)。本篇按实现写入。

**文档-实现偏差(双族坐标系)**:action-logic-state.md §2.4 头与 [../screens-actions-capability.md](../screens-actions-capability.md) §2 原文「族 A(cw_vocab)= 槽位下标,族 B(cw_prep_actions)= 物理槽位 1-9,换算 = 族 B = 族 A + 1」;实况 = 族 B 动作类已随统一词表退役,现役坐标系二分:**席位域动作**(SellBench/SellDeployed/DeployMove)携**容器槽位表下标 0 基**(bench 0-8 / deployed 0-9,读口 `bench_slots_of`/`deployed_slots_of` 同基直取零换算);**画面物理槽位 1 基**仅存于坐标参数化机械动作(WearEquip/工具七类/OpenBox/OpenTome/OpenBookcard)的 `row`/`slot` 字段。执行坐标边换算单点 = `kernel/cw_exec_state.py::deployed_row_slot`(下标→物理排槽)/ `deployed_idx_of`(物理→下标)。本篇按实现写入。

**发射形态(R2 原子通路)**:决策核逐帧发原子动作(部署 = DeployMove 序/穿戴 = WearEquip 序/卖出 = SellBench/SellDeployed),备战环逐帧取决策输出首项执行;组合壳(RunDeploy/RunEquip/RunTools)已退役。发射位计划构造单一源 = `kernel/cw_deploy_logic.py::select_deployments`+`assign_deploy_slots`(部署)、`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`(穿戴)。

**执行器三件套(每动作同构)**:①机械执行(`_execute_dispatch` 分派,`emitted` = 发出事实,False 只用于执行前输入契约拒绝);②tracked 主账同步(`_track_remove_bench`/`_track_remove_deployed`/`_track_move_deployed`,置 None 不移位,摘除腿照常执行只显影不拒写);③逻辑效果推进(`apply_op_effect` 两执行面同源挂点)+ 执行点金差(`_executed_gold_delta`:卖 = +`sell_refund` → `_advance_gold`;LevelUp = 0 金腿已切直写;其余 0/None)+ 回执域(`note_action_receipt`)与 journal 行。

## 2. DeployMove(部署:备战席 → 上阵移位)

**域集**(`apply_prep_action_logic` DeployMove 腿 + `_project_prep_obs` 黑板帧半):bench / front_row / back_row(容器)+ board(增量)/ 观察帧 bench_chars/deployed_chars/front_occupied/back_occupied/free_bench_slots。**装备随人走**(对象整体迁移)。

**确定面**:①源槽摘除(置 None 不移位);②目标单位落 `to_row` 排**首空槽**(`deployed_place` 单一源:首选排满 fallback 另一排;排/槽号信息位重写,开拓者按目标排形态归一 `_apply_row_to_char`);③board 羁绊计数**增量** +1——按上场单位羁绊标签全集(`cw_bond_equips.py::unit_bond_tags`,星徽/卡带贡献在内;无标签回退阵营),逐标签 +1(ADR-0312 增量全集,防全量重算抹掉 OCR 真值);④上阵计数派生递增(= deploy_vacancy −1,heavy 帧重读校准);⑤执行器拖点 = 源槽 area 中心 → 落位排现读首空位(`empty_deploy_slots` 与发射位选排规则同构),拖后 2s 徽章动画等待 + 触发型 overlay 快查(盛会之星锚)。

**随机面**:无(徽章动画 ~2s/overlay 延迟弹出 = 画面时序,`research/screen_flow_timing.md` #10/#24,非逻辑态)。

**拒绝语义**:同名同星已在场 = 游戏拒(恒成立约束「场上同名同星 ≤1」,`research/merge_mechanics.md` §3;kernel 守卫 `duplicate_on_board`)→ 零容器写;`to_row` 非法/源槽空/两排全满 = 静默零写守卫(陈旧提案,等观察覆盖);执行器两排全满 = 未发出(False,观察重派);目标槽拖拽未落地 = 零变化,归下一帧观察。

**kernel 锚**:`kernel/cw_game_state.py::apply_prep_action_logic`(DeployMove 腿);`kernel/cw_vocab.py::simulate`(DeployMove 分支)/`mutate_bench_deployed`;`kernel/cw_exec_state.py::deployed_place`/`deployed_row_slot`/`_apply_row_to_char`;`kernel/cw_bond_equips.py::unit_bond_tags`/`_recount_board`;`kernel/cw_deploy_logic.py::empty_deploy_slots`;`prep_actions.py::PrepActionExecutor._deploy_move`/`_track_move_deployed`;`operations/cw_screen/cw_screen_prep.py::_project_prep_obs`(DeployMove 分支)。

**sim 等价**:`simulate` DeployMove 分支逐腿平移(同名守卫/摘槽/落槽/board 增量同式)。细粒度申报:无标签回退分支 sim 排除 `'?'` 阵营(`_f != '?'`),容器写口按非空 faction 直计(含 `'?'`)——双实现微差,以容器写口为最终事实;合法帧 faction 缺省 `'?'` 时增量差一档,由 heavy 重读校准兜底。

**判例注记**:备战期(22/24 号篇);部署属逻辑态已建模面(批 2a 落码),执行后不再强制保守回退交回(R9 全覆盖后由帧内逻辑态推进承接;overlay 检出仍环中止交外环 handler)。

## 3. SellBench / SellDeployed(卖)

逐动作全文见 [sell-bench.md](sell-bench.md) / [sell-deployed.md](sell-deployed.md);族共通面:执行器拖槽中心 → 出售区(`sell_point` 单一源,area 缺失 RuntimeError 禁兜底坐标);卖出动画 1s 等待(`screen_flow_timing.md` #21 口径);tracked 摘除 = 按下标置 None(信息位/下标脱节不再按 slot 重构,T-261 实证治本);执行点金差 = dispatch 前 tracked 快照的 `sell_refund`(身份不可辨 = None 诚实缺失)→ `_advance_gold` 直推容器金账;`apply_op_effect` 分支:SellBench = 金腿,SellDeployed = 金腿 + owned 恢复腿(不对称申报,见 sell-deployed.md §2)。备战域容器写口域集 = gold/bench(SellBench)与 front_row/back_row/board/gold(SellDeployed);equips 域留观察覆盖(域集封闭申报)。

**判例注记**:备战期(判例 = screens-actions-capability §5:卖备战/卖上阵收缩至备战期;商店域 op 能力面在役不删)。

## 4. WearEquip(穿装备)

**域集**:容器 `equips` 域**不写**(域集封闭申报,留观察覆盖);视觉域 = `PrepObservation.owned_equips` 摘件(`_project_prep_obs` WearEquip 分支);tracked 面 = `apply_op_effect` WearEquip 分支(owned −1 + tracked 目标角色 equips +1)。

**确定面**:①装备归属转移:owned 库存 −1 件、目标角色已穿域 +1(角色装备上限 = `EQUIP_CAPACITY`);②物理→下标换算单一函数 = `deployed_idx_of`(执行坐标边);③拖点 = 目标 avatar 槽位(`_equip_slot_drag_point`:前排 rect 中心 y+21 校准,后排经布局选档 `select_back_layout` 同式派生;缺失 None 禁兜底坐标);源件 = owned 网格按名定位(名字定位是唯一稳锚,网格 reflow 使坐标失真);④计划构造 kernel 单一源 = `kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`(决策侧逐帧现算);⑤拖前稳帧确认(`_wait_stable_frame`,输入条件化等待非判效)。

**零比对出生(裁决 3)**:动作 op 内零 CV-diff 验穿——穿没穿归观察写入边对账(装备期望态对账族下一入口暴露);原 avatar-slot CV-diff 验穿面随原子化删除。**穿着即合成**(在册建模裁定):两件可合成组件穿到同一角色 = 自动合成;**不记合成预期值**(fields.md §4.1 豁免),后果走观察覆盖 + 缺陷台账——该豁免是建模裁定,不是知识缺口。

**随机面**:无确定性随机(穿着合成产物 = 注册表配方确定,但按豁免不记预期值)。

**拒绝语义**:装备槽位坐标缺失 / owned 网格未定位到目标件 = 未发出(False,「计划失效」通道,下帧重派重算);row/slot 越界 = validate 拒;`apply_op_effect` 分支 owned 无此件 = 只跳 tracked 侧(机械动作仍发出)。

**kernel 锚**:`kernel/cw_vocab.py::WearEquip`;`kernel/cw_exec_state.py::apply_op_effect`(WearEquip 分支)/`deployed_idx_of`;`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`;`prep_actions.py::PrepActionExecutor._wear_equip`/`_owned_grid_locate`/`_equip_slot_drag_point`;`operations/cw_screen/cw_screen_prep.py::_project_prep_obs`(WearEquip 分支)。

**sim 等价**:WearEquip 不在 `cw_vocab.py::Action` 联合内,`simulate` 无该分支(零局内资源推进语义,同「视觉域动作容器零写」契约);tracked/观察帧两账随动作同步,等价性归观察边界 reconcile。

**判例注记**:备战期(穿戴 = 备战期发射面,发射位 = mandate M7 装备计划;商店期无穿戴动作)。

## 5. 词表完备性注:SwapDeploy(上阵↔备战对调)

词表 + 容器逻辑态直写 + sim 消费在役,**生产执行器未接线**(备战域部署换位经部署机拖拽承载)。逻辑态规则(规则在册,供接线/sim 消费):deployed 槽 `d_idx` 与 bench 槽 `b_idx` **原槽对调**(置空不移位坐标系);上场者继承下场者的排(含开拓者形态归一),槽号信息位重写;board 重算(`_recount_board`);拒绝 = 同名同星已在场其余位(`duplicate_on_board`)/ expect 双侧失配(陈旧提案)/槽空越界。装备随人走(对象迁移)。kernel 锚 = `kernel/cw_game_state.py::apply_shop_action_logic`(SwapDeploy 腿)、`kernel/cw_vocab.py::simulate`/`mutate_bench_deployed` SwapDeploy 分支(W43 裁决 1/2 代际校验 + 同名唯一性)。

## 6. 边界(不在本篇的动作)

LevelUp(备战单击形态)→ [level-up.md](level-up.md);OpenBox/OpenTome/OpenBookcard(视觉域腾席动作)→ [open-bookcard.md](open-bookcard.md);ClickSpheres/工具原子七类(视觉域 + 效果账)→ [op-effects.md](op-effects.md);OpenShop/StartBattle(转场类,逻辑态 = 空)→ [start-battle.md](start-battle.md)。

## 7. 依据

[../action-logic-state.md](../action-logic-state.md) §3/§3A/§1.4(执行态跟踪账落点);`prep_actions.py` 模块头(执行器坐标系与「发出即职责完成」契约);`kernel/cw_game_state.py::apply_prep_action_logic` docstring 与 `PREP_PROJECTION_DOMAINS` 登记面;`kernel/cw_exec_state.py` ADR-0316/ADR-0392 槽位语义注;[../game_state/fields.md](../../game_state/fields.md) §4.2 RunDeploy/RunEquip 行(基础行为面);`research/merge_mechanics.md` §3(同名唯一恒成立);`research/equipment_mechanics.md` §1(穿着即合成/装备上限 3 件)。
