# 动作执行(action_exec)

> 反向规格化来源 = `kernel/cw_vocab.py`(统一动作词表)+ `operations/cw_op/`(动作 op 群与注册表)+ `prep_actions.py`(PrepActionExecutor 执行器)。职责:动作怎么落地、怎么上报、失败怎么治理。路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作词表与注册表

- **词表单一源** = `kernel/cw_vocab.py::CW_ACTION_TYPES`(统一动作白名单;新增动作必须同步登记,漏登记 = 执行面拒「未知动作类型」,动作从未真正执行)。
- **注册表单一源** = `operations/cw_op/cw_action_registry.py`(词表类 → 动作 op 类一张表;`action_op_for`/`action_op_class_for` 全动作唯一注册点;行序 isinstance 首中即返,is-a 链父类行兜底规则见模块头)。词表外类型 = AssertionError 响亮暴露(非法返回 = 策略器 bug,禁静默跳过)。
- **备战域动作全集**:`CollectOre(max_k)`/`OpenBox(slot)`/`OpenTome(slot)`/`SellBench(slot, reason)`/`SellDeployed(row, slot)`/`DeployMove(bench_idx, to_row, to_slot, faction)`/`LevelUp`/`OpenShop`/`StartBattle`/`Obs(scope)`(重观察动作,in_place = 环内重观察零点击零拖拽——宿主画面 op heavy 观察链重跑上报;outer_loop = 交回外循环重观察,分支拦截型;现役接线域 = 备战决策环)。(组合壳 RunDeploy/RunEquip/RunTools 已随统一词表退役:部署 = DeployMove 原子序发射位逐帧现算,穿戴 = WearEquip 原子,工具 = 工具原子类经 `CwActionToolUseOp`;部署机画面 op `CwScreenDeploy` 已退役删除——部署无画面 op 载体)。
- `SellBench.reason` = 线账闭合孤儿证明载体(**记录非指令**,执行层不读;'' = 未标缺省);发射侧值域闭集 = `cw_prep_actions.SELL_BENCH_REASONS` 唯一承重值 `line_switch_collapse`;reason 不入幂等键。
- 动作实例键 `action_key(action)` = 类型+行为参数(SellBench(3) 与 SellBench(5) 各自计数;归因字段经字段 metadata 不入键)——屏蔽/失败计数的幂等粒度。

## 2. 执行契约

**动作 op = `CwActionXxxOp`(框架 `SrOperation` 子类,构造 = `(ctx, param, env)`;op 内机械执行后直调自己的上报函数)**(规范正文单一源 = [action_ops.md](action_ops.md) §1;本节保留执行面契约表):

| 执行面 | 契约形态 |
|---|---|
| 动作 op(`cw_op/cw_<action>_action.py`,单节点 op;注册表 `action_op_class_for` 类级解析 + `(ctx, param, env)` 组装,节点函数直调) | 机械执行(点击/拖拽)→ **op 内直调自己的上报函数**(上报 = `kernel/cw_action_report/report_action_<snake>_param`,每动作一个具名接口;容器逻辑态写入单点);round 结果成功态 = 发出事实(失败 = 定位落空等未发出通道,`round_fail` 零重试交回) |
| 上报函数族(`kernel/cw_action_report/`) | 每动作恰一个具名函数 = 该动作的容器写语义单点(命名机械可推导,完备锁 = test_cw_action_report_contract);分派只允许 op 直调与引擎入口(sim/回放)的委托分支串;终结跳写(refresh/close 生产不写)与零写族策略声明在包 `__init__` |
| 画面 op 级状态(各画面 op 的具名轮次状态,判读侧分键) | 具名成功/失败状态——这是画面 op 的轮次结果语义,不是动作回执(部署机历史 STATUS 族已随其退役消失) |
| 商店编排(`_open_shop_phase` → `visit_open_shop`) | `(完成事实, detail)`:完成事实 = 商店访问完整收工(开→访问→收店),失败路径店开态交回 |

**事件线 pick 族(`cw_op/cw_pick_xxx_action.py`,11 op 一 op 一文件)**(pick-op-unify 批起全族同契约):每屏选择动作 = 一个 `CwActionPickXxxOp`,op 内 = 选中点击 → 确认点击(或点卡即选)→ 自上报。**上报形态 = 全族即时单相上报**(发射/落地两相与证据闩已全域清偿,迭代 2026-09-21,用户裁定 = action_ops.md §1 增补 2):投资两屏(策略支整支走获得链 `gain_invest_strategy`,环境支走 `gain_invest_env`;词表拆类 = `CwActionPickInvestStrategyParam`/`CwActionPickInvestEnvParam` 两行同指一 op,按 param 类型机械分派上报函数)、补给(`report_action_pick_supply_param` 一口写 + `report_node_advance`)、遭遇(`report_action_pick_encounter_param` 发射即写 `chosen_encounter`)、策划(`report_action_pick_planner_param` 一口写腿型分派效果,条件腿 rider 先行)——各屏点完确认(或点卡即选)立即按成功写完整结果,零证据闩、零重入裁决补写面;确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派。机械参数(辖域申报单一源 = [action_ops.md](action_ops.md) §4.5 段首;确认钮不属机械参数,由动作 op 执行体瞄准处理,增补 3 在册例外):选卡定位 = `env.target`(例外:PickEncounter = op 体内 `area_center`、PickPartner = `env.op._pick_point`);域载荷逐行见段首。op 类体内零决策(决策 = 选中哪个与腿型载荷,瞄准定位查找非决策)。确认后容器写留守画面 op 的部分 = 其余屏的 `chosen_*`/`register_confirm_arrival` Confirm* 到账(**投资两屏零留守**——选择事实与效果全走获得链)。刷新三动作(RefreshNodeOptions/RefreshSupply/RefreshInvestCards)不经注册表(分屏形态各异,留守画面 op 刷新链,注册完备锁豁免)。

配套**发射门**(发射方与执行方同源谓词,防空计划发射):部署选人单一源 = 策略层 `strategies/impl/mandate_v1/deploy_plan.py::select_deployments`(发射×执行单一源;落位计划单一源 = 同模块 `deploy_plan_moves`)。发射门与执行侧经同一帧属性 `recipe_floor_lock_exempt` 同帧同值——锁定线语境豁免:豁免武装帧且本帧无有效仙舟供给时门让位;发射侧拒因/开火分键 = `deploy_emit_*`,执行侧计划拒因/门命中分桶 = `deploy_exec_*`。

## 2.1 终结动作上报节点推进(契约)

节点序前进的唯一动作入口 = kernel `report_node_advance(gs, *, trigger)`(kernel/cw_game_state.py;trigger 封闭集 = `{settle_confirm, supply_confirm}`,集外显式炸错)。两触发点:

- **结算确认**(`cw_op/cw_op_settle_confirm.py::CwOpSettleConfirm`,画面框 op 形态、非动作注册表面):点击「继续挑战」(含长按兜底)→ 遭遇奖励兑现回调(`kernel/cw_encounter_selection.py::claim_encounter_reward`,遭遇扩围批:双证判遭遇 + progress_delta>0 单判,兑现写 `encounter_reward_claimed` 并清 `chosen_encounter` 单次消费;推进上报前调,best-effort)→ **点击即上报** settle_confirm → 交回宿主。结算读点/rounds_done 等结算链留宿主 CwScreenBattleWait;战败分支不进本 op 不推进。
- **补给确认**(`cw_op/cw_pick_supply_action.py::CwActionPickSupplyOp`):点「确认」→ `report_action_pick_supply_param`(即时单相完整结果)+ `report_node_advance(trigger='supply_confirm')` 直接双上报。

**上报时点 = 点击即上报(全动作通用契约)**(通用条款单一源 = [action_ops.md](action_ops.md) §1 增补 2,用户裁定 2026-09-21:选择动作执行按成功处理、点完立即上报写结果、禁事后判断、选择未生效 = 代码 bug 禁防护补丁;本节原 settle/supply 两触发点的「点击即上报」条款已升格为全动作通用,投资两屏 pick 上报随迁移批纳入):动作 op 不做任何确认、不探下一画面锚、不等转移证据——无证据等待 ⇒「上报先于下一节点任何画面渲染」恒成立;节点推进类上报前置**观察态门**(kernel 内):`node_ord` value 在场 ∧ source=observation 双条件才放行,门挡 = obs_event 留证零推进(重复上报/死点击重试报告在结构上零危害);兜底 = 观察锚定(kernel `observe_node_anchor` 补推,锚定写端 = CwScreenPrep 备战顶栏 / CwScreenSupplyNode 补给屏节点条)。推进经生效原语 `advance_node_effective` 落账(candidate 去重守卫 + 效果推进尾段同临界区)。判定语义单一源 = [../game_state/node-derivation.md](../game_state/node-derivation.md) §3.3。

## 3. 备战单动作消费

逐动作循环细则 = [../screens/prep.md](../screens/prep.md) §4(决策恰取一个动作,None = 本帧无动作交回重观察 → F3 validate → 期望态记账 → 执行 → acct 暂存 → 终结判定读注册表 → 逻辑态直写)。本篇只补执行面要点:

- **重观察通道(CwActionObs,scope 选口径)**:策略发射 `CwActionObsParam` = 请求新鲜观察,值域闭集 = `cw_vocab.OBS_SCOPES`。
  **scope='in_place'**(缺省)= 环内重观察:执行体 = 宿主画面 op `reobserve_in_visit`(现役唯一宿主 = `CwScreenPrep`)heavy 观察链重跑,漏斗直写容器 = 观察边界对账(「重新观察上报」),帧代次标 full(方向重估触发,同入口帧;贵段消费侧键守卫每 game-round 恰一次限频)后决策环**原地续跑**(不交回外循环,访问/段序号不重启);重观察见事件 overlay = `CwObsOverlayBail` 控制流异常交回外循环重分发(画面路由归外循环,环内不消化;捕获先例 = StopBrakeShortCircuit)。
  **scope='outer_loop'** = 交回外循环重新观察:决策环在 F3 之前**分支拦截**(不进执行器/动作注册表/续段 token/动作记录),round_success(wait=1.0) 交回,行为与原 HoldFrame 空发射帧逐字一致(用户裁定 2026-09-20 HoldFrame 收编删除;自旋防护 = 交回后归外循环 stall 防线)。
  **读屏点规范的在册例外**:「循环内零读屏」自本通道起收窄——决策环内决策环内在册读屏只有两类——①策略显式发射 Obs(in_place) 触发的重观察(本通道,在册例外①);②终结臂交回前机械留证读(零决策零判效,读数只进缺陷台账;现役 = 投资环境刷新臂刷后帧重读,正本 = [../screens/op-layer.md](../screens/op-layer.md) §1.1 在册例外②),其余路径仍零读屏。in_place 发射域无重观察能力(env.op 未接线)= AssertionError 响亮暴露(策略器 bug)。

- 期望态记账(acct 族)在下一入口 heavy 帧消费对账(`_v2_post_frame_accounting`:拖动期望/买牌期望/经验/羁绊/装备期望),失配 = 纠偏/缺陷台账,零决策不重执行。
- **无 fail-stop/恢复原语**:原「执行失败 → try_recovery 关弹层 → 交回」分支已随验证段废除批删除;overlay 残留的治理 = 外循环 overlay 分发分支(下一轮重识别自愈)。

## 4. 商店动作执行(一 op 一文件 `cw_op/cw_<action>_action.py`;注册表 `cw_action_registry.py`;守卫 `cw_shop_action_ops.py`)

- **CwActionBuyCardOp**(`cw_buy_card_action.py`):点击定位 = 期望态 payload 定长槽阵列(数组下标+1 = 物理槽;身份同一性优先,退化按 (name, star);坐标 = screen_info「商店牌-N」现取,area 缺失/槽号越界显式失败,禁兜底坐标静默点击)→ 点击 → 动画窗 → **发出即记账**(total_buy / spend_executed / bought_names)→ tracking 同步(mutate 与上报同分支单一源:满栏合成买 tracked 侧同样合成腾槽)→ 满栏自动多买补差(k = `merge_buy_k` 单一源,上报 executed 回执携带)。期望态推进 = op 自上报 `report_action_buy_card_param`(gold −单价×k + 落位 + payload −k + 合成连锁/升星腿,买前快照三件组内聚函数内);购买计数回调 `gs.effects.on_buy` = 上报函数内获取计算完时点单点(bump CounterKey.BUY + 购买族效果分派;满栏一击多买按实际张数 k 计 k 次;live/sim 同源,flow 层落地门零计数)。
- **CwActionLevelUpOp**(`cw_prep_level_up_action.py`;`CwActionLevelUpShopParam` 同字段双类型共用):点购买经验单击 → 动画等待(光标遮挡由段顶 park 防)→ 记账;上报 = `report_action_level_up_param`(击数自算 1,满级拒付 `level_cap`)。clicks 序列 = 动作内部步骤,决策循环逐帧重组——外部买面在 clicks 之间不可插花。
- **CwActionRefreshShopOp**(`cw_refresh_shop_action.py`,**访问终结**):体内零读屏零验证(§1 增补 3:动作 op 无论执行前后不做观察识别)→ 点击刷新钮 → 固定等待 1s 等动画收敛(`REFRESH_CLICK_SETTLE_WAIT_S`;等待不是判效)→ **发出即记账**(刷价 = 容器刷价现值 `.value` 读口,失读回基价常量 `REFRESH_COST_BASE`;total_refresh/spend_executed)。自上报 `report_action_refresh_shop_param` 单口三腿:计数触发(`record_refresh` paid/total)+ 免费腿扣减(free 判定 = `gs.free_refresh_left` Field 值 >0;None = 未观察保守按付费,不扣 Field——次数是记账面非决策闸)+ 随机态腿(kernel 发牌采样器 `cw_shop_deal.sample_shop_deal` 与 sim 同源采 5 槽 payload,经 `write_logic_rand` 随机态通道写;observe 覆盖差异落 `logic_rand_outcome` 台账不进失配安灯)。**终结真交回**:执行后本访问结束交回外循环,重进 = 全新入口观察重建牌面;「刷新是否生效」判定归观察侧对账,执行侧零重试。
- **CwActionSellBenchOp**(`cw_prep_sell_bench_action.py`,备战域 = 唯一活执行路径):拖拽卖出(统一拖拽原语机械单发,零判效零重试)→ 发出即记账 → tracking 同步(tracked bench 按下标置 None 不紧缩);上报 = `report_action_sell_bench_param`(置 empty/退款/装备回收/溢出腿单点)。
- **CwActionCloseShopOp**(`cw_close_shop_action.py`,访问终结恒可用):执行位 = 真机械点击「按钮-收起」(miss = 店已关,幂等出口;命中 = 点击 + 固定等待)+ 自上报 `report_action_close_shop_param` 清场(店族 payload leave_screen,两出口同调);零转移验证(收起消失与否归下一帧观察,点击未生效 = 外循环 0n 重分发自然重派重试)。

## 5. 部署执行(DeployMove 原子动作;部署机画面 op 已退役)

- **现役路径**:部署 = 备战决策环动作——mandate 发射位逐帧现算 `CwActionDeployMoveParam` 原子序 → `cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp` 机械拖拽(`DragCwChar.drag_char` 中心拖 + hold0;落位 = 载荷 `(to_row, to_slot)` 直指,执行边零现读)→ 自上报 `kernel/cw_action_report/deploy_move.py::report_action_deploy_move_param`(bench 摘槽 + 载荷落位写 front/back 行 + board 维护)→ 决策循环以逻辑态续算;落地事实归备战环入口观察对账。
- **选人/落位计划单一源** = 策略层 `strategies/impl/mandate_v1/deploy_plan.py`(选人 `select_deployments_reasoned`、排路由 `deploy_row_pref`、槽位 `deploy_slot_plans`、发射/出战链共用 `deploy_plan_moves`);kernel `cw_deploy_logic.py` 保留围栏常量与共用判定谓词(`recipe_floor_holds`/`select_swap_plan`/`residual_fill_plan`)。
- **部署机画面 op 时代的执行细则**(遮蔽哨/换排纠正/off-target 卖出腾位/dual-source 仲裁/收尾 SIFT 纠账)已随 `cw_screen_deploy.py` 退役删除——其中判定语义单一源收编 `cw_deploy_logic.py`(函数级对应见其模块头),路径速查 = [../screens/deploy.md](../screens/deploy.md)。

## 6. 重试语义汇总

| 层 | 重试/恢复 | 上限与去向 |
|---|---|---|
| 动作实例 | 机械单发,动作级零重试零判效;落地事实归下一入口观察对账 | 无动作级去向;外循环防线接管未转移 |
| 失败记忆 | deploy_fail_counts(同角色拖拽被游戏拒 ≥1 → 跳过) | 备战后对账刷新自然重置 |
| 外循环 | node_max_retry_times=400(备战节点) | round_fail 交兜底链;无进展归 G3 守卫(guards.md §1) |
