# 24 部署执行段策略面(deploy segment)

> 定位 = **备战画面内部署执行段**(无独立 screen_info 建档画面):部署 = 备战决策环动作——`CwActionDeployMoveParam` 原子序由策略层动作发出点逐帧现算,经 `cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp` 机械拖拽在货币战争-备战上执行(部署机画面 op 已停用删除);未达上限确认弹窗(货币战争-未达上限警告)由流程层推进;**能力面** = [../screens/README.md](../screens/README.md) §5.4。本篇 = 该段的**策略面**:思路概述 + 动作清单 + 形式判据指针。
> **单一源** = 该信息的唯一权威出处;**帧** = 一次截取游戏画面并做一次决策的时点;**对账** = 预期记账状态与画面实际读数的比对核验;**两套并行意向** = 过渡配方与终局阵容两套意向并行(代码字段 `ist.p1_pair`);**被换下单位(victim)** = 换血时被卖出腾位的上阵单位;**数字来源标注(四种)**:【注】游戏定义值 /【推】已证推导 /【拟】观测估计 /【拍】用户立场登记值。
> 判据权威定义引用不重复:部署与站位判据 = [10_prep_decisions.md](10_prep_decisions.md) §1;换血卖出的骨架侧语义 = [02_mandate_layer.md](02_mandate_layer.md) §7(sell 行,M4 姊妹出口)。数值单一源在代码。

## 1. 策略思路/算法概述

- **选人围栏**:部署候选受围栏约束——引擎/配方体系件围栏 `DEPLOY_FENCE`(单一源 = `kernel/cw_launch_admission.py::DEPLOY_FENCE`,RECIPE ∪ ENGINE)与上阵资格(`cw_launch_admission.py::offtarget_sell_allowed`);排路由/槽位选择单一源 = 策略层 `mandate_v1/deploy_plan.py`(排 = `deploy_row_pref` 三级:阵容站位覆盖 > 注册表 position_pref 派生 > back 兜底,前排保证随迁;槽位 = `deploy_slot_plans` 按容器行列现值自定,后排上限 = `back_layout` 现值);后排布局选档单一入口 = `obs/cw_back_layout.py::select_back_layout`。
- **判据必需件首桶序**:选人序以目标阵容的 `required_deployed` 成员为第一优先桶(在用两实例 = 希儿系 pair 的 `pair_target_comp` 与静态套「希儿量子」;装配单一源 = `mandate_v1/deploy_plan.py::_deploy_plan_inputs`(动作发出点/出战链共用)与 kernel `assemble_swap_plan_inputs`(换血计划),消费 = `select_deployments` `required_names` 参)。依据 = 判据必要条件的支配论证:该件不在板该体系永远无法成型(希儿系判据的「希儿在板」合取支,`Comp.required_deployed` 字段契约),cap 竞争时空位让给普通成员 = 弱占优劣化;空集缺省 = 序逐位同旧(未接线消费面零漂移)。职责边界:只判断「能不能上一个人」的预检函数(shop 的 `can_deploy_single`、`cw_launch_admission.has_deployable`)不接收这份优先序参数——它们只判单一候选可上阵,与排序无关;边界申报见 `select_deployments` 注(策略层单一源)。
- **换血卖出**:非目标阵容的上阵件挡目标成员上场时先卖腾位,被换下单位(victim)资格单一判定 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`(义务集 ∪ 新鲜度排除 ∪ 资格族);部署面换血是 M4 之外的姊妹卖出出口(`02_mandate_layer.md` §7)。**替补受上阵窗口辖域辖**(与部署一致):窗口未到的终局替补不可上 = 窗口辖域的自然结果,换血通道由过渡替补在产(窗口辖域定义 = [22_prep_screen.md](22_prep_screen.md) §1 第 5 步,数据载体 = 知识卡 `entry_signals`)。**转型域方向锁前提**:换血域「方向锁在效」= 终局阵容已锁定(判定源 = 锁定线槽 `target_comp`,`ist.locked_comp` 为其派生缓存;已定型/非双轨期判定权威 = `cw_intention.committed_authority`——①锁定线槽非空 ②P1 配方锁 `p1_pair` 非空,缺供给帧保守 False;[12_line_and_intention.md](12_line_and_intention.md) §2)∨ 位面 1 过渡配方与终局阵容两套并行意向(``ist.p1_pair``;装配单一源 = `assemble_swap_plan_inputs`)——两套并行意向期间板面义务本体 = 过渡配方(cw_recipe 模块不变量;user_playstyle [20],玩法立场登记条目:两套并行意向期义务按过渡配方),终局阵容锁定生效的帧不开转型域 = 配方完成件压席帧无合法被换下单位。域开伴随一处**收紧面(显式申报)**:终局阵容锁定生效的帧允许换血卖出,但同时收紧——不属于目标阵容、也不在围栏白名单里的上阵角色,不再允许任意星级直接卖,只能逐个按资格规则(保档位、只卖 1★、保合成素材)判定;卖 2★ 只走「演进降级换血」专用通道(P41② 卖出净损被持,经济安全向收紧);「演进降级换血」分支不受本推广影响(位面 1 配对阵容帧的成员名单为空,使其成员门恒关)。**板满换入分支**:必需件或配方完成件滞留 bench ∧ 板满时让位可卖——①必需件分支:`required_deployed` 成员滞留,假想面板(被换下单位离场 ∧ 必需件按已换入计)下成型判据仍满(`form_progress >= 1.0`,单一源折法含 OR 组承接规则)的目标板件让位;②配方完成件分支(两套并行意向且终局阵容锁定生效期):方向锁在效 ∧ fp<1 ∧ bench 存在「入板即成型」件(``_completion_swap_ins``,✗→✓ 严格优——换入后物化判据改善才准换;桥池 pair required 恒空,完成件压席由本分支承接,判定尺 = user_playstyle [20]/[13]);保护域扩展集(shared ∪ 替班)不因两分支解除(P41② + 替班=不卖契约);卖后上序须真含换入对象(required ∪ 完成件),否则计划拒(`post_sell_req_missing`)——判据必需件/完成件优先于非必需板件([31]③ 上场侧同构的必需件特化)。**放行条件在终局阵容锁定生效期的读法**:M1 的重新部署放行条件(``_redeploy_emission_allowed``)在尚未锁定采购名单的帧(终局阵容成员名单未定时缺省为此态)下,压席成员判据退为目标阵容视角(kernel `target_view_char_is`),另一条判据(入板须严格推进成型度)不变——转型域计划不再被放行条件一直推迟。
- **补齐语义**:残余补部署 P24(空槽上任意围栏认可件零支出严格优先,`../proofs/p24-residual-fill-dominance.md`);放行条件纪律 = 计划空是合法稳态,发出方与执行方用同一谓词判空、为空就不发出动作(`10_prep_decisions.md` §1)。

## 2. 会执行的动作清单

| 动作 | 动作类型/op 载体 | 触发判据(指针) |
|---|---|---|
| 选人上阵 | `CwActionDeployMoveParam` 原子序(备战环决策发出,拖拽 = `cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp`;部署机画面 op 已停用) | M1/M5 + 围栏 + `10_prep_decisions.md` §1(计划单一源 = `mandate_v1/deploy_plan.py::deploy_plan_moves`;围栏/底线门谓词 = `kernel/cw_deploy_logic.py`) |
| 换排 | `CwActionDeployMoveParam`(to_row 重拖,策略发出) | 同上(放对激活角色赋能;错排事实归备战环入口观察对账) |
| 换血卖出 | `CwActionSellDeployedParam`(`cw_sell_deployed_action.py`;判定单一源 = `swap_sell_exclusion_reason`) | 被换下单位资格 = `swap_sell_exclusion_reason`(义务集∪新鲜度排除∪资格族) |

## 3. 能力 vs 策略

部署执行段动作集与能力面同集(能力矩阵篇 §3.4);商店期「卖备战/买经验收缩至备战期」的旧判例已废止,不涉及本段动作面(见 [23_shop_screen.md](23_shop_screen.md) §3)。
