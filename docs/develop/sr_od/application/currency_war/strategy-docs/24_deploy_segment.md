# 24 部署执行段策略面(deploy segment)

> 定位 = **备战画面内部署执行段**(无独立 screen_info 建档画面):部署 = 备战决策环动作——`CwActionDeployMoveParam` 原子序由策略层发射位逐帧现算,经 `cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp` 机械拖拽在货币战争-备战上执行(部署机画面 op 已退役删除);未达上限确认弹窗(货币战争-未达上限警告)由流程层推进;**能力面** = [../screens/README.md](../screens/README.md) §5.4。本篇 = 该段的**策略面**:思路概述 + 动作清单 + 形式判据指针。
> 判据本体引用不重复:部署与站位判据 = [10_prep_decisions.md](10_prep_decisions.md) §1;换血卖出的骨架侧语义 = [02_mandate_layer.md](02_mandate_layer.md) §7(sell 行,M4 姊妹出口)。数值单一源在代码。

## 1. 策略思路/算法概述

- **选人围栏**:部署候选受围栏辖——引擎/配方体系件围栏 `DEPLOY_FENCE`(单一源 = `kernel/cw_launch_admission.py::DEPLOY_FENCE`,RECIPE ∪ ENGINE)与发射资格(`cw_launch_admission.py::offtarget_sell_allowed`);排路由/槽位选择单一源 = 策略层 `mandate_v1/deploy_plan.py`(排 = `deploy_row_pref` 三级:comp 站位覆盖 > 注册表 position_pref 派生 > back 兜底,前排保证随迁;槽位 = `deploy_slot_plans` 按容器行列现值自定,后排上限 = `back_layout` 现值);后排布局选档单一入口 = `obs/cw_back_layout.py::select_back_layout`。
- **判据必需件首桶序**:选人序以目标 comp 的 `required_deployed` 成员为第一优先桶(现役两实例 = 希儿系 pair 的 `pair_target_comp` 与静态套「希儿量子」;装配单一源 = `mandate_v1/deploy_plan.py::_deploy_plan_inputs`(发射位/出战链共用)与 kernel `assemble_swap_plan_inputs`(换血计划),消费 = `select_deployments` `required_names` 参)。依据 = 判据必要条件的支配论证:该件不在板该体系永远无法成型(希儿系判据的「希儿在板」合取支,`Comp.required_deployed` 字段契约),cap 竞争时空位让给普通成员 = 弱占优劣化;空集缺省 = 序逐位同旧(未接线消费面零漂移)。分轨边界:预检位(shop `can_deploy_single`、`cw_launch_admission.has_deployable`)不穿本参,序无关的单候选可入性语义,边界申报见 `select_deployments` 注(策略层单一源)。
- **换血卖出**:off-target 上阵件挡 target 上场时先卖腾位,victim 资格单一判定 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`(义务集 ∪ 新鲜度排除 ∪ 资格族);部署面换血是 M4 之外的姊妹卖出出口(02 §7)。**转型域方向锁前提**:换血域「方向锁在效」= 终局线锁(``ist.locked_comp``)∨ P1 配方对锁(``ist.p1_pair``,ADR-0357;装配单一源 = `assemble_swap_plan_inputs`)——双轨期板面义务本体 = 过渡配方(cw_recipe 模块不变量;user_playstyle [20]),配方对锁帧不开转型域 = 配方完成件压席帧无合法 victim。域开伴随一处**收紧面(显式申报)**:对锁帧的 off-target 非围栏板件由基座臂任意星级自由卖收窄为资格族逐件判定(档位守恒/1★ 限卖/素材守卫)——2★ 卖出自此只走演进降级换血臂显式通道(P41② 卖出净损被持,经济安全向收紧);演进降级换血臂不受推广影响(pair 帧 membership 空集使其 member 门恒关),店侧 S_spec 收窄直读 `ist.locked_comp` 刻意不随(买侧收窄辖域不变)。**板满换入臂**:必需件或配方完成件滞留 bench ∧ 板满时让位可卖——①必需件臂:required_deployed 成员滞留,假想面板(victim 离场 ∧ 必需件按已换入计)下成型判据仍满(`form_progress >= 1.0`,单一源折法含 OR 组承接规则)的 target 板件让位;②配方完成件臂(双轨对锁期):方向锁在效 ∧ fp<1 ∧ bench 存在「入板即成型」件(``_completion_swap_ins``,✗→✓ 严格优——换入后物化判据改善才准换;桥池 pair required 恒空,完成件压席由本臂承接,判定尺 = user_playstyle [20]/[13]);保护域扩展集(shared ∪ 替班)不因两臂解除(P41② + 替班=不卖契约);卖后上序须真含换入对象(required ∪ 完成件),否则计划拒(`post_sell_req_missing`)——判据必需件/完成件优先于非必需板件([31]③ 上场侧同构的必需件特化)。**发射门轴①对锁期读法**:M1″ 发射门(``_redeploy_emission_allowed``)在 membership 空集帧(锁线采购集未锁帧缺省)压席成员轴退 target 视图(kernel `target_view_char_is`),轴②(入板严格推进成型度)不变——转型域计划不再被发射门恒 defer。
- **补齐语义**:残余补部署 P24(空槽上任意围栏认可件零支出严格优先,`../proofs/p24-residual-fill-dominance.md`);发射门纪律 = 计划空是合法稳态,发射方与执行方同源谓词判空不发射(10 §1)。

## 2. 会执行的动作清单

| 动作 | 词表/op 载体 | 触发判据(指针) |
|---|---|---|
| 选人上阵 | `CwActionDeployMoveParam` 原子序(备战环决策发射,拖拽 = `cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp`;部署机画面 op 已退役) | M1/M5 + 围栏 + 10 §1(计划单一源 = `mandate_v1/deploy_plan.py::deploy_plan_moves`;围栏/底线门谓词 = `kernel/cw_deploy_logic.py`) |
| 换排 | `CwActionDeployMoveParam`(to_row 重拖,策略发) | 同上(放对激活角色赋能;错排事实归备战环入口观察对账) |
| 换血卖出 | `CwActionSellDeployedParam`(`cw_sell_deployed_action.py`;判定单一源 = `swap_sell_exclusion_reason`) | victim 资格 = `swap_sell_exclusion_reason`(义务集∪新鲜度排除∪资格族) |

## 3. 能力 vs 策略

部署执行段动作集与能力面同集(能力矩阵篇 §3.4);策略收缩不涉及本段(收缩只发生在商店期,见 [23_shop_screen.md](23_shop_screen.md) §3)。
