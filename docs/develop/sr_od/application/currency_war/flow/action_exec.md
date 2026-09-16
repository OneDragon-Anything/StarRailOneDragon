# 动作执行(action_exec)

> 反向规格化来源 = `kernel/cw_vocab.py`(统一动作词表)+ `operations/cw_op/`(动作 op 群与注册表)+ `prep_actions.py`(PrepActionExecutor 执行器)+ `operations/cw_screen/cw_screen_deploy.py`(部署机)。职责:动作怎么落地、怎么上报、失败怎么治理。路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作词表与注册表

- **词表单一源** = `kernel/cw_vocab.py::CW_ACTION_TYPES`(统一动作白名单;新增动作必须同步登记,漏登记 = 执行面拒「未知动作类型」,动作从未真正执行)。
- **注册表单一源** = `operations/cw_op/cw_action_registry.py`(词表类 → 动作 op 类一张表;`action_op_for`/`action_op_class_for` 全动作唯一注册点;行序 isinstance 首中即返,is-a 链父类行兜底规则见模块头)。词表外类型 = AssertionError 响亮暴露(非法返回 = 策略器 bug,禁静默跳过)。
- **备战域动作全集**:`ClickSpheres(max_k)`/`OpenBox(slot)`/`OpenTome(slot)`/`SellBench(slot, reason)`/`SellDeployed(row, slot)`/`DeployMove(from_slot, to_row, to_slot)`/`LevelUp`/`OpenShop(read_only)`/`StartBattle`。(组合壳 RunDeploy/RunEquip/RunTools 已随统一词表退役,批2b R2:部署 = DeployMove 原子序发射位逐帧现算,穿戴 = WearEquip 原子,工具 = 工具原子类经 ToolUseOp;`CwScreenDeploy` 唯一生产直调 = 外循环 0j 恢复链)。
- `SellBench.reason` = 线账闭合孤儿证明载体(**记录非指令**,执行层不读;'' = 未标缺省);发射侧值域闭集 = `cw_prep_actions.SELL_BENCH_REASONS` 唯一承重值 `line_switch_collapse`;reason 不入幂等键。
- 动作实例键 `action_key(action)` = 类型+行为参数(SellBench(3) 与 SellBench(5) 各自计数;归因字段经字段 metadata 不入键)——屏蔽/失败计数的幂等粒度。

## 2. 执行契约

**动作 op = 机械执行,无成败回执**(用户裁定:动作 op 只管机械执行,禁做验证;动作未生效归动作层修可靠性,落地判定归观察侧 reconcile 对账):

| 执行面 | 契约形态 |
|---|---|
| 动作 op(`cw_op/cw_<action>_action.py`,`ActionOp.execute` 单方法) | 机械执行(点击/拖拽)+ 向 game state 上报动作事实(逻辑态由 game state 经 `apply_*` 族独占写入);**无返回**——发出即职责完成,零判效 |
| 落地登记注册表(`cw_screen_op_base.py` §6.4) | 动作发射点统一触发(单一发射口,发射即触发);逐件申报面 = `EMIT_TRIGGERED_DECLARED`(遭遇/策略刷新计数、经验账本两通道);「未落地不计数」防线由观察侧 reconcile 承接 |
| 画面 op 级状态(`CwScreenDeploy` 等) | 具名成功/失败状态(STATUS_NOOP/STATUS_DEPLOYED/STATUS_OVERLAY_PREEMPTED 等,判读侧分键)——这是画面 op 的轮次结果语义,不是动作回执 |
| 商店编排(`_open_shop_phase`) | `(progressed, detail)`:读数性开店 progressed = 开店成功 |

配套**发射门**(发射方与执行方同源谓词,防空计划发射):部署候选单一源 = kernel `select_deployments`(`cw_deploy_logic`;发射×执行单一源)。发射门与执行侧经同一帧属性 `recipe_floor_lock_exempt` 同帧同值——锁定线语境豁免:豁免武装帧且本帧无有效仙舟供给时门让位;发射侧拒因/开火分键 = `deploy_emit_*`,执行侧计划拒因/门命中分桶 = `deploy_exec_*`。

## 3. 备战单动作消费

逐动作循环细则 = [../screens/prep.md](../screens/prep.md) §4(决策恰取一个动作,None = 本帧无动作交回重观察 → F3 validate → 期望态记账 → 执行 → acct 暂存 → 终结判定读注册表 → 逻辑态直写)。本篇只补执行面要点:

- 期望态记账(acct 族)在下一入口 heavy 帧消费对账(`_v2_post_frame_accounting`:拖动期望/买牌期望/经验/羁绊/商店池/合成预览/装备期望),失配 = 纠偏/缺陷台账,零决策不重执行。
- **无 fail-stop/恢复原语**:原「执行失败 → try_recovery 关弹层 → 交回」分支已随验证段废除批删除;overlay 残留的治理 = 外循环 0 系 overlay 分支(下一轮重识别自愈)。

## 4. 商店动作执行(一 op 一文件 `cw_op/cw_<action>_action.py`;注册表 `cw_action_registry.py`;守卫 `cw_shop_action_ops.py`)

- **BuyCardOp**(`cw_buy_card_action.py`):点击定位 = 期望态 payload 定长槽阵列(数组下标+1 = 物理槽;身份同一性优先,退化按 (name, star);坐标 = screen_info「商店牌-N」现取,area 缺失显式失败)→ 买前裁片**纯留证**(零判效)→ 点击 → 动画窗 → **发出即记账**(total_buy / spend_executed / bought_names)→ tracking 同步(mutate 与逻辑态直写同分支单一源:满栏合成买 tracked 侧同样合成腾槽)→ 满栏自动多买补差(k = `merge_buy_k` 单一源)。**execute 无返回**(发出即职责完成,零判效)。期望态推进 = 容器规则通道(`apply_shop_action_logic` 简单腿 + `apply_shop_merge_leg` 合成升星腿,基点 = 买前快照三件组)。
- **LevelUpOp**(`cw_level_up_action.py`):点购买经验单击 → 动画等待(光标遮挡由段顶 park 防)→ 记账(clicks 序列 = 动作内部步骤,决策循环逐帧重组——外部买面在 clicks 之间不可插花)。
- **RefreshShopOp**(`cw_refresh_shop_action.py`,段终结):硬墙(`../screens/shop.md` §5,visit 级);刷前现读两口径 → 刷前刷新钮真值读(三态+免费剩余次数,best-effort)→ 点击 → 两帧指纹一致门等牌行稳定(非 blind sleep)→ **发出即记账**(刷价 = 基价常量;total_refresh/did_refresh)。牌名集对比仅作遥测留证(refresh_board_changed;原安灯 free_refresh_proc 豁免消费已随安灯退役);「刷新是否生效」判定归观察侧 reconcile,执行侧零重试。
- **SellBenchOp**(`cw_sell_bench_action.py`,商店域能力面;注册行已更替备战域):拖拽卖出(统一拖拽原语机械单发,零判效零重试)→ 发出即记账 → tracking 同步(置 None 不紧缩)+ `register_round_sold`(同轮不回买)。
- **CloseShopOp**(`cw_close_shop_action.py`,访问终结恒可用):动作 op 内 no-op,关店点击由编排壳 `cw_op_close_shop.py::CwOpCloseShop` 承担。

## 5. 部署执行(CwScreenDeploy,`cw_screen_deploy.py`)

- **前置**:registry decision 全集锚(`cw_overlay_registry.derive_decision()`)任一命中 → `round_fail(STATUS_EVENT_OVERLAY+命中画面名)`(执行环境失配速报交回重判)。
- **输入装配**:槽位坐标全部从 screen_info 读(备战栏 9/前排 4/后排按 cap 差公式选档 `select_back_layout` 单一入口);cap = paddle 直读域防抖(权威;失读才单调链 max 兜底)。
- **选人/围栏/排序单一源** = kernel `cw_deploy_logic.select_deployments`(发射×执行单一源)。围栏集 = RECIPE ∪ ENGINE;r387 cap 富余放行散牌填空。
- **拖拽循环运行时守卫**:每槽动态 cap 复查、同名在场禁双(`deploy_legal` 不变量)、列车配方底线仲裁(判定单一源 = kernel `recipe_floor_holds`;含锁定线语境豁免)、fresh 复查源槽占用、前排保证、系统单位剔除。P24 残余补部署的列车件过滤经同一判定(`filter_fill_plan_by_floor`)。
- **遮蔽哨(发射前拦截)**:每槽迭代体一切像素读之前置 registry decision presence 探测哨,命中 = `STATUS_OVERLAY_PREEMPTED` 截断本轮(剩余单位留 bench,交 0 系 overlay 分支自愈)。**部署落地零像素判效**:拖拽机械发出即计入,落地事实归备战环入口观察对账。
- **换排纠正**:场内错排者拖回正排;禁清空前排守卫 + 前排保证后置——出口不变量「上阵≥1 ⇒ 前排≥1」在函数出口成立,收尾出口断言现读复验(`STATUS_FRONT_INVARIANT_FAIL` 兜底)。
- **off-target 卖出腾位**(deploy-swap):守卫 `offtarget_sell_allowed`(引擎/配方体系件默认恒不卖;例外 = 换阵卖出义务臂 + 转型臂 + 演进降级换血臂,逐件拒因分键零静默;判定单一源 = `swap_sell_exclusion_reason`)。
- **收尾**:SIFT 真值纠 tracking(观测回路)+ 装备快照回写 tracked_deployed.equips。
- **拖后整队等待 2.0s**【注·口述口径 screen_flow_timing.md #10】:羁绊徽章动画窗。

## 6. 重试语义汇总

| 层 | 重试/恢复 | 上限与去向 |
|---|---|---|
| 动作实例 | 机械单发,动作级零重试零判效;落地事实归下一入口观察对账 | 无动作级去向;外循环防线接管未转移 |
| 失败记忆 | deploy_fail_counts(同角色拖拽被游戏拒 ≥1 → 跳过) | 备战后对账刷新自然重置 |
| 外循环 | node_max_retry_times=400(备战节点) | round_fail 交兜底链;无进展归 G3 守卫(guards.md §1) |
