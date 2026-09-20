# 动作执行(action_exec)

> 反向规格化来源 = `kernel/cw_vocab.py`(统一动作词表)+ `operations/cw_op/`(动作 op 群与注册表)+ `prep_actions.py`(PrepActionExecutor 执行器)。职责:动作怎么落地、怎么上报、失败怎么治理。路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作词表与注册表

- **词表单一源** = `kernel/cw_vocab.py::CW_ACTION_TYPES`(统一动作白名单;新增动作必须同步登记,漏登记 = 执行面拒「未知动作类型」,动作从未真正执行)。
- **注册表单一源** = `operations/cw_op/cw_action_registry.py`(词表类 → 动作 op 类一张表;`action_op_for`/`action_op_class_for` 全动作唯一注册点;行序 isinstance 首中即返,is-a 链父类行兜底规则见模块头)。词表外类型 = AssertionError 响亮暴露(非法返回 = 策略器 bug,禁静默跳过)。
- **备战域动作全集**:`CollectOre(max_k)`/`OpenBox(slot)`/`OpenTome(slot)`/`SellBench(slot, reason)`/`SellDeployed(row, slot)`/`DeployMove(from_slot, to_row, to_slot)`/`LevelUp`/`OpenShop(read_only)`/`StartBattle`/`Obs(scope)`(重观察动作,in_place = 环内重观察零点击零拖拽——宿主画面 op heavy 观察链重跑上报;outer_loop = 交回外循环重观察,分支拦截型;现役接线域 = 备战决策环)。(组合壳 RunDeploy/RunEquip/RunTools 已随统一词表退役,批2b R2:部署 = DeployMove 原子序发射位逐帧现算,穿戴 = WearEquip 原子,工具 = 工具原子类经 `CwActionToolUseOp`;部署机画面 op `CwScreenDeploy` 已退役删除——部署无画面 op 载体)。
- `SellBench.reason` = 线账闭合孤儿证明载体(**记录非指令**,执行层不读;'' = 未标缺省);发射侧值域闭集 = `cw_prep_actions.SELL_BENCH_REASONS` 唯一承重值 `line_switch_collapse`;reason 不入幂等键。
- 动作实例键 `action_key(action)` = 类型+行为参数(SellBench(3) 与 SellBench(5) 各自计数;归因字段经字段 metadata 不入键)——屏蔽/失败计数的幂等粒度。

## 2. 执行契约

**动作 op = `CwActionXxxOp`(框架 `SrOperation` 子类,构造 = `(ctx, param, env)`;op 内机械执行后直调自己的上报函数)**(规范正文单一源 = [action_ops.md](action_ops.md) §1;本节保留执行面契约表):

| 执行面 | 契约形态 |
|---|---|
| 动作 op(`cw_op/cw_<action>_action.py`,单节点 op;注册表 `action_op_class_for` 类级解析 + `(ctx, param, env)` 组装,节点函数直调) | 机械执行(点击/拖拽)→ **op 内直调自己的上报函数**(上报 = `kernel/cw_action_report/report_action_<snake>_param`,每动作一个具名接口;容器逻辑态写入单点);round 结果成功态 = 发出事实(失败 = 定位落空等未发出通道,`round_fail` 零重试交回) |
| 上报函数族(`kernel/cw_action_report/`) | 每动作恰一个具名函数 = 该动作的容器写语义单点(命名机械可推导,完备锁 = test_cw_action_report_contract);分派只允许 op 直调与引擎入口(sim/回放)的委托分支串;终结跳写(refresh/close 生产不写)与零写族策略声明在包 `__init__` |
| 画面 op 级状态(各画面 op 的具名轮次状态,判读侧分键) | 具名成功/失败状态——这是画面 op 的轮次结果语义,不是动作回执(部署机历史 STATUS 族已随其退役消失) |
| 商店编排(`_open_shop_phase`) | `(progressed, detail)`:读数性开店 progressed = 开店成功 |

**事件线 pick 族(`cw_op/cw_overlay_pick_action.py`,12 op)**(pick-op-unify 批起全族同契约):每屏选择动作 = 一个 `CwActionPickXxxOp`,op 内 = 选中点击 → 确认点击(或点卡即选)→ 自上报(`report_action_pick_*_param`,全族零写)——动作 op 重组批 §1.1 登记的「零上报例外」已撤销。机械参数(定位点/确认钮/裁决词)由画面 op 决策半现算经 `OverlayPickExecEnv` 传入(op 类体内零决策);确认后容器写(`chosen_*`/`active_*`/效果登记/置闩/`register_confirm_arrival` Confirm* 到账)留守画面 op 原写点原时点。刷新三动作(RefreshNodeOptions/RefreshSupply/RefreshInvestCards)不经注册表(分屏形态各异,留守画面 op 刷新链,注册完备锁豁免)。

配套**发射门**(发射方与执行方同源谓词,防空计划发射):部署候选单一源 = kernel `select_deployments`(`cw_deploy_logic`;发射×执行单一源)。发射门与执行侧经同一帧属性 `recipe_floor_lock_exempt` 同帧同值——锁定线语境豁免:豁免武装帧且本帧无有效仙舟供给时门让位;发射侧拒因/开火分键 = `deploy_emit_*`,执行侧计划拒因/门命中分桶 = `deploy_exec_*`。

## 3. 备战单动作消费

逐动作循环细则 = [../screens/prep.md](../screens/prep.md) §4(决策恰取一个动作,None = 本帧无动作交回重观察 → F3 validate → 期望态记账 → 执行 → acct 暂存 → 终结判定读注册表 → 逻辑态直写)。本篇只补执行面要点:

- **重观察通道(CwActionObs,scope 选口径)**:策略发射 `CwActionObsParam` = 请求新鲜观察,值域闭集 = `cw_vocab.OBS_SCOPES`。
  **scope='in_place'**(缺省)= 环内重观察:执行体 = 宿主画面 op `reobserve_in_visit`(现役唯一宿主 = `CwScreenPrep`)heavy 观察链重跑,漏斗直写容器 = 观察边界对账(「重新观察上报」),帧代次标 full(方向重估触发,同入口帧;贵段消费侧键守卫每 game-round 恰一次限频)后决策环**原地续跑**(不交回外循环,访问/段序号不重启);重观察见事件 overlay = `CwObsOverlayBail` 控制流异常交回外循环重分发(画面路由归外循环,环内不消化;捕获先例 = StopBrakeShortCircuit)。
  **scope='outer_loop'** = 交回外循环重新观察:决策环在 F3 之前**分支拦截**(不进执行器/动作注册表/续段 token/动作记录),round_success(wait=1.0) 交回,行为与原 HoldFrame 空发射帧逐字一致(用户裁定 2026-09-20 HoldFrame 收编删除;自旋防护 = 交回后归外循环 stall 防线)。
  **读屏点规范的在册例外**:「循环内零读屏」自本通道起收窄——决策环内仅策略显式发射 Obs(in_place) 才触发读屏,其余路径仍零读屏。in_place 发射域无重观察能力(env.op 未接线)= AssertionError 响亮暴露(策略器 bug)。

- 期望态记账(acct 族)在下一入口 heavy 帧消费对账(`_v2_post_frame_accounting`:拖动期望/买牌期望/经验/羁绊/商店池/合成预览/装备期望),失配 = 纠偏/缺陷台账,零决策不重执行。
- **无 fail-stop/恢复原语**:原「执行失败 → try_recovery 关弹层 → 交回」分支已随验证段废除批删除;overlay 残留的治理 = 外循环 0 系 overlay 分支(下一轮重识别自愈)。

## 4. 商店动作执行(一 op 一文件 `cw_op/cw_<action>_action.py`;注册表 `cw_action_registry.py`;守卫 `cw_shop_action_ops.py`)

- **CwActionBuyCardOp**(`cw_buy_card_action.py`):点击定位 = 期望态 payload 定长槽阵列(数组下标+1 = 物理槽;身份同一性优先,退化按 (name, star);坐标 = screen_info「商店牌-N」现取,area 缺失显式失败)→ 买前裁片**纯留证**(零判效)→ 点击 → 动画窗 → **发出即记账**(total_buy / spend_executed / bought_names)→ tracking 同步(mutate 与上报同分支单一源:满栏合成买 tracked 侧同样合成腾槽)→ 满栏自动多买补差(k = `merge_buy_k` 单一源,上报 executed 回执携带)。期望态推进 = op 自上报 `report_action_buy_card_param`(gold −单价×k + 落位 + payload −k + 合成连锁/升星腿,买前快照三件组内聚函数内)。
- **CwActionLevelUpOp**(`cw_prep_level_up_action.py`;`CwActionLevelUpShopParam` 同字段双类型共用):点购买经验单击 → 动画等待(光标遮挡由段顶 park 防)→ 记账;上报 = `report_action_level_up_param`(击数自算 1,满级拒付 `level_cap`)。clicks 序列 = 动作内部步骤,决策循环逐帧重组——外部买面在 clicks 之间不可插花。
- **CwActionRefreshShopOp**(`cw_refresh_shop_action.py`,段终结):硬墙(`../screens/shop.md` §5,visit 级);刷前现读两口径 → 刷前刷新钮真值读(三态+免费剩余次数,best-effort)→ 点击 → 固定等待 1s 等动画收敛(`REFRESH_CLICK_SETTLE_WAIT_S`)→ **发出即记账**(刷价 = 基价常量;total_refresh/did_refresh)。**终结跳写(收窄申报,2026-09-18 迁入裁决)**:金与 payload 不写(观察覆盖),刷新三计数由本 op 自上报统一触发(`report_action_refresh_shop_param` → 效果账本 `record_refresh` 单口;free = 刷前按钮态真值优先,sink 吸收路径接收侧补触发);牌名集对比仅作遥测留证(refresh_board_changed);「刷新是否生效」判定归观察侧 reconcile,执行侧零重试。
- **CwActionSellBenchOp**(`cw_prep_sell_bench_action.py`,备战域 = 唯一活执行路径):拖拽卖出(统一拖拽原语机械单发,零判效零重试)→ 发出即记账 → tracking 同步(置 None 不紧缩);上报 = `report_action_sell_bench_param`(退款/装备回收/溢出腿单点)。
- **CwActionCloseShopOp**(`cw_close_shop_action.py`,访问终结恒可用):动作 op 内 no-op,关店点击由编排壳 `cw_op_close_shop.py::CwOpCloseShop` 承担;终结跳写(结构离屏写 = 编排壳观察写端)。

## 5. 部署执行(DeployMove 原子动作;部署机画面 op 已退役)

- **现役路径**:部署 = 备战决策环动作——mandate 发射位逐帧现算 `CwActionDeployMoveParam` 原子序 → `cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp` 机械拖拽(`DragCwChar.drag_char` 中心拖 + hold0)→ 自上报 `kernel/cw_action_report/deploy_move.py::report_action_deploy_move_param`(bench→deployed 槽位平移 + board 维护)→ 决策循环以逻辑态续算;落地事实归备战环入口观察对账。
- **选人/围栏/排序/底线门单一源** = kernel `cw_deploy_logic.py`(`select_deployments_reasoned`/`recipe_floor_holds`/`select_swap_plan`/`residual_fill_plan`;发射侧 mandate 与执行侧 op 共用同一判定)。
- **部署机画面 op 时代的执行细则**(遮蔽哨/换排纠正/off-target 卖出腾位/dual-source 仲裁/收尾 SIFT 纠账)已随 `cw_screen_deploy.py` 退役删除——其中判定语义单一源收编 `cw_deploy_logic.py`(函数级对应见其模块头),路径速查 = [../screens/deploy.md](../screens/deploy.md)。

## 6. 重试语义汇总

| 层 | 重试/恢复 | 上限与去向 |
|---|---|---|
| 动作实例 | 机械单发,动作级零重试零判效;落地事实归下一入口观察对账 | 无动作级去向;外循环防线接管未转移 |
| 失败记忆 | deploy_fail_counts(同角色拖拽被游戏拒 ≥1 → 跳过) | 备战后对账刷新自然重置 |
| 外循环 | node_max_retry_times=400(备战节点) | round_fail 交兜底链;无进展归 G3 守卫(guards.md §1) |
