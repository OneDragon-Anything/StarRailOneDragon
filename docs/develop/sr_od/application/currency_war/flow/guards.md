# 守卫总册（guards）

> 反向规格化来源 = `operations/cw_loop.py` + `operations/cw_screen/cw_screen_prep.py` + `operations/cw_screen/cw_screen_buy_cards.py` 的守卫/停机/降级段。职责：识别域与执行面的停机/留证防线。对局状态推进的监测不在框架——停滞判读 = 事件哨兵 `skills/sr-od-currency-war-dev/scripts/cw_sentinel.py`(v5.2:STALL 同特征零推进/LOOP 签名循环/NODE-DWELL 相位滞留/SILENCE 沉默,只留证不停机;注:框架 stall_watch.flag 写端已随守卫删除,哨兵该关键词静默保留)。路径根 = `src/sr_od/application/currency_war/`。
> 分工判据（od-dev-stop-hooks）：**采集哨兵不停机**（bot 可能只是慢）；**停机钩子保画面**（stop_running + flag + 截图，处理完删 flag 重启）。本篇全部为流程防线，与策略判据无关。

## 1. 外环连续 fail 重派网（通用网）

| 限额 | 值 | 语义 |
|---|---|---|
| `OP_FAIL_REDISPATCH_LIMIT=5` | 连续计（任一分发 op ok 清零；异键 ok 同闭窗） | 同一分发 op 连续 fail 达本值 → 留证截图 + round_fail 显式停交上层，取代「fail → round_wait 零预算重派」的无界空转（T-266；实锤 = 选择伙伴 15 连败靠 NODE-DWELL 900s 哨兵兜住才停，2026-09-15 事故）。round_fail 在 node_max_retry 400 下**不停机**——刻意：消除「静默」而非「重试」，ERROR 行进日志 = 哨兵 STALL 通道与人都能看到，停机决策留给观察者 |

> 原 §1 的两条专用 streak 守卫（0q 位面过渡误分发 =3、prep 连续失败 =5）已退役并入本网：阈值同值平手无行为差，计数/判定统一在 `_dispatch_screen_op`（hook 早退位次之后，hook 仍可短路）。链形透传分支（3c）不经本网（各有自身预算）。
> 补注:分支守卫钩子（0n visit_ok/_fail 计数、A1 bail 清除、B5 窗口关+闩清）自 dispatch 包装落地起经 `_dispatch_screen_op` 的 **on_result 调用点邻接闭包**执行，仅执行落点随包装迁移，钩子明细。
> 位面过渡的误分发根修在识别层（2026-09-16）：BOSS简报锚换装徽记模板（OCR 误读免疫），阶段一位面过渡身份臂挂 boss 判别排他（接管派发 boss op）；原 0q 兜底随「未建档实证的故障形态不作兜底理由」裁定同批退役（见 outer_loop §2.3 退役记录）。

## 2. 未知画面兜底（常驻安全网；`cw_loop.py::CwLoop._handle_unknown_fallback`）

- 触发 = loop 尾所有分支不命中（兜一切未知态，非点名某态的临时捕获；移除条件 = 该类未知态全部建档实际不可达，长期保留）。
- `UNKNOWN_STOP_THRESHOLD=15` 轮 ≈ 2min（旧 30s 放宽，换取停机钩子触发前充分自愈窗口）；重试退避 = 2s 起步每连续一次翻倍，封顶 `UNKNOWN_RETRY_BACKOFF_CAP_S=10`（画面被任何分支接走 → streak 归 1 退避自动复位）。
- 触发动作：截图 + `unknown_state.flag`（处理流程：analyze_screen 离线判已建档命中 → 未命中按元素语义建档 + 0x 分支加 handler → 删 flag + 重启 server）→ `stop_running`。

## 3. 商店未识别卡停机

防抖重读 2 帧（判据化自愈：牌行两帧指纹一致门 + ≥1.0s 观察窗）后仍有未识别槽 → 停机保画面（shop_unk.flag）待建档。**不能降级带病跑**（未识别卡按非 target 跳过 = 决策在残缺牌面上做 + 错过新内容建档窗口；用户 2026-08-24 裁决接受阻断代价）。

## 4. 降级链汇总（fail-closed 行为）

| 场景 | 降级行为 | 为什么 fail-closed |
|---|---|---|
| gold 失读（shop 关态） | 备战入口 heavy 观察重试（旧腾席链 b「read_only 店取真值/链 c stale 试算」已随单动作循环迁移批死码清理删除） | 宁可重观察,不造值 |
| 卖前对拍不符 | **守卫断言两级分型**（2026-09-05 双账 HIT 实证定谳）——`guard_expected_vs_tracked`:①多集等价(成员同、槽位序异)⇒ WARNING「槽位布局漂移」+按 tracked 真值就地重播种逻辑态 bench,**不炸环**;②真多集分歧 ⇒ AssertionError 炸出(双属归因不变)。`guard_proposal_vs_expected`(提案 vs 期望态)仍恒炸;满栏买入豁免面已收窄(满栏合成买双账同构,豁免仅剩非合成满栏买像素差漏检的 fail-open 残余窗) | 不卖错件(卖出不可逆)。两守卫零读屏(tracked 纯内存),详见 `../screens/op-layer.md` §1.3/`action_exec.md` §4 |
| 全保护死锁（旧链 c） | （随腾席链死码删除退役;M4 腾席现由 mandate_v1 骨架义务承载） | — |
| 部署 cap 失读 | 单调链 max 兜底；全源失读 → 不设板满门（拖到游戏拒即真值） | 低读阻塞上阵（贵）> 高读白拖一次（便宜） |
| 空部署计划 | （旧 flow.py 发射门已随死码删除;部署候选单一源 = `cw_deploy_logic.select_deployments`,空候选不提案） | 空计划 ✓ = 假成功形态(候选单一源空不提案为唯一防线;停顿监测归哨兵) |
| 增量态构造 fail-closed | 金失读/tracked 空 → 回退全量 read_game_state | 空 tracked 真空/丢跟踪不可区分，不造值 |
| 期望态对账不一致 | 落缺陷台账留证（L1→复现升 L0 安灯），**不纠漂不重执行** | 对账是观测不是决策；纠漂需先归因 |
| 免费刷新 proc | flag 留证**不停机** | 免费不是失败（通道保留作对账防线） |
