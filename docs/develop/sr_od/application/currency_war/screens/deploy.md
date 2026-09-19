# 部署机(deploy · 备战画面执行段;SCREEN_NAME = 货币战争-备战)

> 代码 = `operations/cw_screen/cw_screen_deploy.py::CwScreenDeploy`(直继承 `SrOperation` 单体,单 node「部署备战栏角色」;**出辖申报**:不属画面分发主体,两 node 化与 obs 化未立项——评估另立批,裁延迟,[op-layer.md](op-layer.md) §3 出辖)。**非独立建档画面**:部署机在备战画面上以拖拽执行,槽位坐标全部来自备战建档(`assets/game_data/screen_info/currency_war_battle_prep.yml`:备战栏-1..9 / 前排-1..4 / 后排-N / 区域-出售区)。执行细则单一源 = [../flow/action_exec.md](../flow/action_exec.md) §5(前置断言/输入装配/围栏/拖拽循环守卫/换排/off-target/收尾逐条在彼),本篇只写画面侧编排与调用契约,禁复制成第二源。路径根 = `src/sr_od/application/currency_war/`。

## 1. 调用契约(分发判定)

- 无外循环分发分支;两个调用面:
  - **唯一直调** = cw_loop 0j「前台无角色提示」恢复链(`cw_loop.py::_frontless_recovery_step` → `CwScreenDeploy(ctx).execute()`;`prep_actions.py` 模块头明文:「CwScreenDeploy 画面 op 仍由 cw_loop 0j 前台无角色恢复链直调,非词表成员」)。
  - **备战期部署的生产载体 = DeployMove 原子序**(部署机不在常规备战环路径):发射核 `cw_loop.py::launch_prepared_battle` / `cw_loop.py::_battle_chain_deploy_moves` 按 kernel 计划现算逐 move 发,执行 = `prep_actions.py::PrepActionExecutor` + 注册行 `cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp`;组合壳 RunDeploy 已退役(`kernel/cw_vocab.py` 词表无该类)。
- 入口执行断言:`cw_screen_deploy.py::CwScreenDeploy.deploy` 首闸 = `kernel/cw_overlay_registry.py::derive_decision` 全集锚任一命中 → `round_fail(STATUS_EVENT_OVERLAY+命中画面名)`(执行环境失配速报交回重判;口径 = registry 内,registry 外 overlay 为已知漏检残余,口径申报见 action_exec.md §5 前置节)。

## 2. 画面形态声明

**执行型机械段式 op**(非决策循环形态、非空决策推进形态):计划语义零内嵌——选人/围栏/排序单一源 = `kernel/cw_deploy_logic.py::select_deployments_reasoned`(发射×执行单一源),op 只做输入装配(SIFT/CV 现读)+ 拖拽执行 + 运行时守卫;非动作词表成员,无决策入口、零策略器问询。

## 3. 观察面

输入装配全现读(action_exec.md §5 的画面侧数据源):占用 = `obs/currency_war_cv.py::slot_occupied`(CV 像素);身份 = `obs/cw_identity_obs.py::read_bench_chars` / `read_deployed_chars`(SIFT,plaza 立绘模板 `cw_screen_deploy.py::CwScreenDeploy._get_templates` 缓存 ctx);cap = `obs/cw_observation.py::read_deploy_cap_debounced`(paddle 域防抖权威,失读才单调链 max 兜底);deployed 计数双源仲裁 = `cw_observation.py::arbitrate_deployed_count`(取低值 fail-closed,分歧/失读留证 = `cw_screen_deploy.py::_note_deployed_count_divergence`);后排布局选档 = `obs/cw_back_layout.py::select_back_layout`(cap 差公式单一入口,未知态写类冻结 → 后排部署跳过)。装配源 = 容器单例(`kernel/cw_game_state.py::game_state_of`;node 未观察 = None = 计划弃权保守侧)。

**部署落地零像素判效**:拖拽机械发出即计入 placed,落地事实归备战环入口观察对账;收尾观测回路 = SIFT 真值纠 tracking(`cw_screen_deploy.py::CwScreenDeploy._reconcile_tracking`)+ 装备快照回写 `tracked_deployed[].equips`(`_snapshot_equips_into_tracking`,执行簿记非策略读口)。

## 4. 动作面

- 拖拽统一原语 = `operations/dev/drag_cw_char.py::DragCwChar.drag_char`(中心拖 + hold0;机械单发零判效);卖出落点单一源 = `prep_actions.py::sell_point`(`货币战争-备战.区域-出售区` center)。
- 主拖拽循环运行时守卫(计划已定,守卫只拦机械不安全面,细则 = action_exec.md §5):每槽动态 cap 复查(仲裁值+placed)、同名在场禁双、配方底线仲裁(`cw_screen_deploy.py::r288_hold_now`,判定单一源 = `kernel/cw_deploy_logic.py::recipe_floor_holds`,含锁定线豁免)、**遮蔽哨**(迭代体一切像素读之前探测 decision overlay presence,命中 = `STATUS_OVERLAY_PREEMPTED` 截断,剩余留 bench 交 0 系 overlay 分支)、fresh 源槽复查、前排保证(队列重排优先,强转兜底)、系统单位剔除(`cw_screen_deploy.py::exclude_system_units`)。P24 残余补部署 = `cw_screen_deploy.py::residual_fill_plan` + `filter_fill_plan_by_floor`(底线同辖 fill 段)。
- 换排纠正 = `cw_screen_deploy.py::CwScreenDeploy._fix_misplaced_rows`:错排者拖回注册表正排;**禁清空前排守卫**(计数调用内动态维护,防双移动各自看到计数放行而合击清空)+ 后置前排保证——出口不变量「上阵≥1 ⇒ 前排≥1」在函数出口成立。
- off-target 卖出腾位 = `cw_screen_deploy.py::CwScreenDeploy._sell_offtarget_deployed`:逐件单一判定 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`(排除族∪资格族,拒因分键零静默;swap_ctx 不可得退型 = 标量 fenced + 排除链静默,在册遗留缺口);卖数 ≤ 1:1 替换上限(= bench target 数);换阵卖出义务臂态 = `swap_ctx.fenced_on`(off-line 引擎/配方件让位可卖,新线 core∪shared 继续保护)。
- 交互时序:每拖后 1.2s 特效等待、拖完整队 2.0s(羁绊徽章动画窗,`docs/game/currency_war/research/screen_flow_timing.md` #10)。

## 5. 终结与交回

- 具名状态集(发射契约:成功/no-op/失败判读侧可分):成功 = `STATUS_DEPLOYED` / `STATUS_NOOP`(计划空合法稳态)/ `STATUS_NO_BENCH` / `STATUS_ROWFIX_RECOVERED`(板满失配窄豁免:仲裁真满板 ∧ 前排全空 ∧ 后排有人 → 场内换排修复成功);失败 = `STATUS_LANDED_NONE`(计划非空 placed=0)/ `STATUS_BOARD_FULL_MISMATCH` / `STATUS_PHANTOM_FULL_BOARD` / `STATUS_FRONT_INVARIANT_FAIL` / `STATUS_OVERLAY_PREEMPTED` / `STATUS_EVENT_OVERLAY`。
- 出口不变量「上阵≥1 ⇒ 前排≥1」在成功出口现读复验(`cw_screen_deploy.py::CwScreenDeploy._front_ok_now`;NO_BENCH 早退点同样复验;前排槽未建模 = 识别退化态断言不辖)。
- 交回落点(0j 恢复链消费):成功 → 出战链直接再出战(`PrepActionExecutor` + StartBattle;失败信号 = 出战链 `POST_LAUNCH_BLOCKERS` 弹窗守卫,非像素判效);fail → `round_retry` 回 0j 分支计重试,超限 `FRONTLESS_REDEPLOY_LIMIT=2` round_fail 交兜底链(预算持于外循环,[../flow/guards.md](../flow/guards.md) §3)。

## 6. 状态上报面

- 零逻辑态直写:部署/卖出逻辑态未建模面,容器真值归下一帧观察对账;本 op 不消费上报函数族(与备战域 DeployMove/SellDeployed 动作的 `report_action_deploy_move_param`/`report_action_sell_deployed_param` 直写语义分属两条链)。
- 执行侧分键族(best-effort,`strategy_state.cw4_counters`):`deploy_exec_held_*`(计划拒因)/ `deploy_exec_r288_skip_ctx_open|closed`(底线门命中分桶)/ `deploy_swap_sell_excluded_*` / `deploy_swap_sell_rejected_*`(卖出逐件拒因)/ `sell_offtarget_arm_*|regular`(驱动归因);与发射侧 `deploy_emit_*` 同粒度对读。

## 7. 子态与 overlay

- 遮蔽防线两道:入口 `derive_decision` 全集断言(拦已成型 overlay)+ 拖拽循环/P24 遮蔽哨(拦窄时序窗弹出;presence 近似 = 锚在场即判遮蔽,方向保守)。overlay 残留治理 = 外循环 0 系分支重识别自愈,本 op 无 fail-stop/恢复原语(action_exec.md §3)。
- 关联弹窗:0d 未达上限警告(部署文档族,出战确认语境,文档 = [deploy_not_full.md](deploy_not_full.md))。

## 8. 守卫与防线

- 失败记忆归分发层:op 侧不自持熔断计数;同签名零推进的停顿监测归哨兵(框架不裁策略卡死)。
- cap 误差不对称取舍(降级链 = guards.md §4):低读阻塞上阵(贵)> 高读白拖一次(便宜)——paddle 权威直用、失读 max 兜底、全源失读不设板满门(拖到游戏拒即真值)。

## 9. 遥测与锁面

- 无独立 dispatch journal 行(0j 直调;包装链形补 op =「前台无角色恢复」行,[../flow/outer_loop.md](../flow/outer_loop.md) §2.2 0j 行);日志前缀 `[cw-deploy]` / `[cw!]` 警示面;部署识别基准帧留证 = `operations/decision_frame_hooks.py::save_decision_frame`(deploy)。
- 测试锁(锁面根 = `sr-od-test/test/sr_od/application/currency_war/`):占槽物品写入端存在性锁(test_cw_deploy_pseudo_slot)、unified-action 原子通路锁(test_cw_unified_action_2a 等)等部署面行为锁。
- game 侧:备战建档 = `currency_war_battle_prep.yml`;拖后整队等待口径 = `docs/game/currency_war/research/screen_flow_timing.md` #10。

## 开放设计注

- 调用面口径对齐(已修):[README.md](README.md) §4/§5.3 与 [prep.md](prep.md) 的「组合路径 = RunDeploy」旧表述已按代码现状修正(组合壳退役;唯一直调 = 0j;备战期部署 = DeployMove 原子序)。
- m1p 载荷接缝错位:`cw4_m1p_plan_pending` 写端(mandate m1p 发射位)与读端(`deploy` 入口读后即清,消费 = R1-a 直投/R1-b 重 derive)在组合壳退役后分离——常规备战环 DeployMove 原子执行不消费载荷,读端仅 0j 直调可达;m1p 直投在现调用面的可达性与「零读者」表述口径候裁。
- 换排纠正与 comp `char_positions` 覆盖的口径双源(注册表 pref vs 覆盖)以错排残留面存在(守卫不改判定),收口候后续批。
