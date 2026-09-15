# 守卫总册（guards）

> 反向规格化来源 = `operations/cw_loop.py` + `operations/cw_screen/cw_screen_prep.py` + `operations/cw_screen/cw_screen_buy_cards.py` 的守卫/停机/降级段。职责：识别域与执行面的停机/留证防线。对局状态推进的监测不在框架——停滞判读 = 外部哨兵 `tools/cw/cw_run_sentinel.py`(判读 [cw-op] 主日志流,只留证不停机)。路径根 = `src/sr_od/application/currency_war/`。
> 分工判据（od-dev-stop-hooks）：**采集哨兵不停机**（bot 可能只是慢）；**停机钩子保画面**（stop_running + flag + 截图，处理完删 flag 重启）。本篇全部为流程防线，与策略判据无关。

## 1. 误分发与恢复链限额

| 限额 | 值 | 语义 |
|---|---|---|
| `FRONTLESS_REDEPLOY_LIMIT=2` | 本 run 累计（复位条件收紧：环 success ∧（本环未发射 StartBattle ∨ 发射验证成功）才复位——StartBattle 验证失败的环在外循环仍记 round_success，该形态部署链不健康不复位；发射结果载体 = `ExecState.last_prep_battle_launch_ok` 三态，消费后清 None 防跨环残留；1-1 冻结局实证旧无条件复位使预算形同虚设） | 前台无角色恢复链（确认→验证重部署→验前排≥1→再出战）超限 round_fail 交兜底链，不再无限 round_wait（1-1 事故 5h 死循环返工） |
| `PLANE_MISDISPATCH_LIMIT=3` | 连续计（接管/过渡成功清零） | 位面过渡误分发型 fail 超限 round_fail（boss 简报帧误分发每 2s 无限循环实证） |
| director fail streak 5 | 连续计 | CwScreenPrep 连续 5 次失败 → round_fail 交未知画面兜底链（消除静默 ping-pong；round_fail 在 node_max_retry 400 下不停机——刻意：消除"静默"，warning 进日志即哨兵，停机决策留给观察者） |

> 补注:分支守卫钩子（0n visit_ok/_fail 计数、0q streak 复位、A1 bail 清除、B5 窗口关+闩清）自 dispatch 包装落地起经 `_dispatch_screen_op` 的 **on_result 调用点邻接闭包**执行——限额值与清零/超限语义不变，仅执行落点随包装迁移，钩子明细。

## 2. 未知画面兜底（常驻安全网；`cw_loop.py::CwLoop._handle_unknown_fallback`）

- 触发 = loop 尾所有分支不命中（兜一切未知态，非点名某态的临时捕获；移除条件 = 该类未知态全部建档实际不可达，长期保留）。
- `UNKNOWN_STOP_THRESHOLD=15` 轮 ≈ 2min（旧 30s 放宽，换取停机钩子触发前充分自愈窗口）；重试退避 = 2s 起步每连续一次翻倍，封顶 `UNKNOWN_RETRY_BACKOFF_CAP_S=10`（画面被任何分支接走 → streak 归 1 退避自动复位）。
- 触发动作：截图 + `unknown_state.flag`（处理流程：analyze_screen 离线判已建档命中 → 未命中按元素语义建档 + 0x 分支加 handler → 删 flag + 重启 server）→ `stop_running`。

## 3. 执行失败安灯（`cw_screen_prep.py` `_spend_unit_close`（判定与记账同点：购买单元收尾）+ `_exec_fail_hook_check`（安灯判定+触发）；分类器在 `run_state.py`）

> 安灯分类器输入面 = 内存直读的一手执行事实:购买单元的 `BuyCardsOutcome` 暂存 + finalize 关店金现读回填的 gold_close。`plan_truncated` 豁免通道语义 = 「刷新硬墙跳过」(单动作下不存在截断丢弃尾)。

- 判定与记账同点：购买单元收尾时跑分类器 `exec_fail_should_stop`——数据源 = 内存直读一手执行事实（单元暂存 `BuyCardsOutcome` 的 visit_actions/gold_open + finalize 关店金现读回填的 gold_close；facts 缺席或金读缺失 → unknown 不停，不猜）。旧数据源三流（decisions.jsonl plan 行 / spend_ledger.jsonl 单元行 / obs_conflicts join 兼容路径）已随删除波 1 停写，只辖存量语料——现行下钻 = journal（`state/journal.jsonl`：receipts 回执窗 + state.values.gold 行行快照）与本钩子 flag 的 plan/gold 三件组（同 `run_state.py` flag 文本口径）。
- "计划≠尝试"分流：plan_truncated（硬墙跳过/截断丢弃）豁免防误停；refresh_attempted/board_changed 进三态判定。
- 触发：每局最多停一次（`_exec_fail_hook_fired`）→ 截图 + `cw_exec_fail_hook.flag`（plan 明细 + gold 开/关）→ `stop_running(reason='hook:exec_fail_mismatch')`。

## 4. 商店未识别卡停机

防抖重读 2 帧（判据化自愈：牌行两帧指纹一致门 + ≥1.0s 观察窗）后仍有未识别槽 → 停机保画面（shop_unk.flag）待建档。**不能降级带病跑**（未识别卡按非 target 跳过 = 决策在残缺牌面上做 + 错过新内容建档窗口；用户 2026-08-24 裁决接受阻断代价）。

## 5. 降级链汇总（fail-closed 行为）

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
