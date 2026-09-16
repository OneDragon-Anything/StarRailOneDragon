# 出战执行器合一审计（landing 3.1 交付物）

> 审计对象 = 三条出战执行路径的现存实码（符号锚：`operations/cw_loop.py::readiness_battle_launch` /
> `::launch_prepared_battle` / `::locked_resume_sync_and_battle` / `::CwLoop.DISPATCH_AREA_ANCHORS` /
> `prep_actions.py::PrepActionExecutor._start_battle` / `operations/cw_op/cw_start_battle_action.py::StartBattleOp`）。
> 结论供统一执行器规格与 3.3 接线消费。

## 1. 三路径现状盘点

| 路径 | 入口 | 包装语义（路径独有） | 底层 |
|---|---|---|---|
| 达标臂 | cw_loop 达标臂分支 → `readiness_battle_launch`（:346，唯一调用点 :1976） | ①屏态复验：fresh 截图 + 双锚（stale → `readiness_stale_screen` 分键 + `(False, detail)` 放弃，**不耗 C1 失败计数**；复验异常 → 保守放行 + defect 留证）②G1 准入预估（`readiness_admission_report`，显影不拦截，`deploy_swap_no_victim` 分键）③**浮层安全检查在分支体内**（锚表扫描排除备战自身锚 + 遭遇 OCR「遭遇其」→ 命中置 `_arm_armed=False` + `readiness_overlay_hold` 分键）④失败记账：成功复位 `readiness_launch_fail`、失败 `+1` | `launch_prepared_battle(sync_once=False)` → `PrepActionExecutor.execute(StartBattle())` |
| 恢复局面 | `locked_resume_sync_and_battle`（:172） | 闩辖：`_cw_locked_sync_done` 置位后同步步跳过；**无复验/浮层检查/独立分键** | `launch_prepared_battle(sync_once=True)`（同执行器） |
| 策略终点 | mandate 动作链 StartBattle 词表动作 → `_start_battle`（prep_actions:855，薄委托） | 无包装（纯动作分派；部署由策略链内 DeployMove 动作承担） | `_dispatch_action(StartBattle())` → `StartBattleOp`（**与左两路径同一执行器**） |

## 2. 关键事实

1. **点击链已统一**：StartBattleOp 模块头明文「备战环 / 达标臂发射核 / 恢复局锁定直出战三路径经同一注册表分派到达本 op，禁各写一套点击段」；旧发射家族（转移轮询/备战标识消失验证/拦截弹窗守卫/重发长按下/失焦守卫/launch_dead 连败停机）随出战域重设计（T-286）整删，op 零判效、交回后画面由外循环重判。
2. **C1 单一底层发射函数已存在**：`launch_prepared_battle`（部署原子序 + StartBattle 执行核），达标臂/恢复局面两调用面共用——C1 的「禁各写一套发射位」已兑现。
3. **「合一」的真实残余** = 包装语义三段（屏态复验/浮层安全检查/G1 预估）只在达标臂面存在；恢复局面面与策略终点路径均无。design §2.2「两调用面同保浮层检查」= 对恢复局面面的防误触补齐（行为改进，已申报）。
4. **现存测试锁 = 空**：test 树 grep `readiness_battle_launch|launch_prepared_battle|达标臂|locked_resume|StartBattle` 零命中——landing 3.1「既有出战行为锁全绿」判据为空集，本阶段随统一执行器交付首批直测。
5. **正本漂移实证**：start-battle.md §1 所述「未落地原样重发长按下/连败停机留证」与实码不符（T-286 后 op 零重发零判效）——正本清单已有修正条目。

## 3. 统一执行器规格（`launch_battle_unified`）

- 签名：`launch_battle_unified(op, ctx, *, face: str) -> tuple[bool, str]`；`face ∈ {'armed', 'resume'}`。
- 内部序（design §2.2）：**屏态复验**（双锚 fresh；stale → `(False, 'readiness_stale_screen')` 分键；异常 → 保守放行 + defect）→ **浮层安全检查**（锚表扫描 + 遭遇 OCR 兜底，命中 → `(False, 'readiness_overlay_hold:<hit>')` 分键——两 face 同保，恢复局面面防误触补齐）→ **face 分轨**（armed：G1 预估显影 + 部署原子序每帧现算不过闩；resume：闩辖部署原子序一次）→ **StartBattle 执行** → 返回 `(last_launch_ok, last_detail)`。
- 失败语义分轨：本函数只返回事实；`readiness_launch_fail` 分键与成功复位归调用方（达标臂分支，3.3 随 op 迁移）。
- 等价声明：`face='armed'` ≡ 现 `readiness_battle_launch` + 达标臂浮层闸 合体；`face='resume'` ≡ 现 `launch_prepared_battle(sync_once=True)` + 复验/浮层补齐。

## 4. 宿主与依赖路由

- 依赖清单：`CwLoop.DISPATCH_AREA_ANCHORS`（锚表类常量）、`_battle_chain_deploy_moves`（部署计划 kernel 单一源装配）、`readiness_admission_report`、`strategy_state_of` 分键、`launch_prepared_battle`——**全部住在 cw_loop.py**。
- 结论：3.1 宿主 = **cw_loop.py**（依赖原地，零拷贝零环）；3.3 接线时若 op 面调用需跨模块，锚表常量外移评估。landing 3.1 落点「prep_actions.py」按本审计修正为 cw_loop.py（prep_actions 宪章张力随之消解）。

## 5. 遥测逐键宿主映射表

| 键 | 现宿主 | 目标宿主（3.3 后） |
|---|---|---|
| `readiness_stale_screen` | readiness_battle_launch（复验段） | 统一执行器（复验段） |
| `readiness_overlay_hold` | 达标臂分支浮层闸 | 统一执行器（浮层段） |
| `readiness_launch_fail` + 成功复位 | 达标臂分支调用方 | 调用方（3.3 随迁，op 消费面） |
| `deploy_swap_no_victim` | readiness_battle_launch（G1） | 统一执行器（armed 面） |
| `LAUNCH_QUALITY_EVAL_ERROR_KEY` / `LAUNCH_QUALITY_DEFER_FRAMES_KEY` | 达标臂分支（armed 判定消费） | 策略前置发射位（3.2 随判定消费迁策略） |
| `KEY_PRECHECK_SKIP` | `_prep_anchors_hit` 预检 | **退役申报**（预检随达标臂拆除） |
| `KEY_ABANDONED_LAUNCH` | 达标臂分支弃射路径 | 统一执行器复验段或策略前置位（按 3.3 形态钉） |
| `launch_arbitrage_*` 其余（受限访问段） | `_launch_frame_arbitration` | 仲裁意图化：意图执行 = op 受限访问机器 |

## 6. 遗留与风险

- start-battle.md §1 漂移 → 正本清单修正条目已列（3.4 执行）。
- 策略终点路径（`_start_battle` 薄委托）本迭代零改动（mandate_v1 边界）；3.3 后其发射语义 = 策略前置位产 StartBattle 意图经统一执行器（design 方案 3），落地时 `_start_battle` 退役评估归 3.3。
