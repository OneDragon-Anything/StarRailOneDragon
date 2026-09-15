# 守卫总册（guards）

> 反向规格化来源 = `operations/cw_loop.py` + `operations/cw_screen/cw_screen_prep.py` + `operations/cw_screen/cw_screen_buy_cards.py` 的守卫/停机/降级段。职责：卡死与失活的检出、留证、停机或降级。路径根 = `src/sr_od/application/currency_war/`。
> 分工判据（od-dev-stop-hooks）：**采集哨兵不停机**（bot 可能只是慢）；**停机钩子保画面**（stop_running + flag + 截图，处理完删 flag 重启）。本篇全部为流程防线，与策略判据无关。

## 1. G3 环级无进展守卫（架构反思三卡死批防线①；`cw_loop.py::prep_no_progress_tick` + `CwLoop.loop` 备战分支 G3 计数段）

- **判据**（修订后口径）：状态指纹恒定窗口累计 `PREP_NO_PROGRESS_ROUNDS=3`【注·框架常量，三起实机卡死 8-34min 在 3 环(≈1min)内停机校准】环即触发停机留证；收益耗尽臂另设放宽判据=「指纹恒定窗口内动作批并集 ⊆ {OpenShop, RunDeploy} ∧ 末批 = RunDeploy ∧ 上一备战环 success」→ 不停机改发射出战（备战等待边际收益恒 0 的支配性论证）。指纹恒定本身即窗口内全部动作的定义性零变换证明（真实买入/卖出/升级必变 gold 或身份串）。
- **动作批签名** = `session.last_prep_action_sig`（备战单轮 op 决策出口写动作类型元组；overlay 交回/策略异常时保持 None;写点 = `cw_screen_prep.py::CwScreenPrep.run` 前置清零 + 决策出口,生命周期孪生环同写）。修订后动作批降级为窗口留证与收益耗尽臂判别输入（窗口动作批并集累积器），不再是计数键。
- **状态指纹** = `cw_loop.py::prep_no_progress_state_fingerprint`（修订节）：(plane, round_num, last_node_type, gold, bench 身份串, deployed 身份串)，为守卫**唯一计数键**（单键化：签名振荡+恒指纹=最纯「忙而无功」，旧双键 (动作批,指纹) 在振荡下每帧归零穿透两出口，实证 run_20260908_210431 15 分钟软卡死）。任一分量变化 = 有推进（战斗等待不进备战分支且回备战时 round 必变；正常多帧部署改变身份或 gold；闩跳过帧动作批不同）。gold 分量仅开态可信帧更新（`prep_obs_frame.state_gold_trusted` 单一写点，关店帧 raw 读数不再归零计数，真买入/升级/刷新必经开店帧）；球/箱/vacancy 刻意不进指纹（识别抖动误计数，由动作签名留证腿覆盖）。
- **计数纯函数** `prep_no_progress_tick`：同指纹累加、指纹变化归零；sig=None 批归零（overlay 垄断/策略异常形态维持哨兵档语义，修订第 3 条）。
- **触发动作**：截图 + `write_no_progress_flag`（签名序列+计数+处理指引）→ 附 `prep_stall_pending_expected` 留证（EXPECTED_STATE prep_obs 覆盖点滞留条目）→ `stop_running(reason='hook:prep_no_progress')`。取代旧备战 stall 留证线（单一计数单一签名，不留两套）。
- flag 处理指引要点：同批动作反复发射而状态不动 = 执行面变换失败（遮罩挡拖拽/点击落空/闩漏网活锁）→ 按截图判画面：未建档 overlay → 建档 + 0x 分支；已建档 → 查该动作执行链。

## 2. 停滞 watchdog（r119；哨兵不停机；`cw_loop.py::CwLoop._stall_watch_tick`）

- 每 `STALL_SNAPSHOT_EVERY=5` iter 采样一次画面指纹（OCR 关键词 frozenset 哈希）；连续 `STALL_N=6` 次相同（≈1-2min 同屏）→ 写 `stall_watch.flag`（关键词+截图+处理指引）+ `[cw!]` 日志一次。**不停机**（bot 可能只是慢，停机代价>等待代价）。
- **战斗窗口宽限**：`BATTLE_WATCH_GRACE_S=600`【注·框架常量，覆盖实测 4-5.5min 战斗】内不计数（出战后合法静止；战斗 HUD 关键词可全程不含豁免词，宽限窗防误报）。开窗 = 备战环出口出战；关窗 = 见结算屏/回备战。
- 豁免判据 = 全帧 OCR 固定短语表（`cw_loop.py::CwLoop.STALL_EXEMPT_PHRASES`：挑战成功/挑战失败/挑战结束/继续挑战/前往结算；裸子串禁回填——弹窗正文撞车致盲形态见常量注）。

## 3. 误分发与恢复链限额

| 限额 | 值 | 语义 |
|---|---|---|
| `FRONTLESS_REDEPLOY_LIMIT=2` | 本 run 累计（复位条件收紧：环 success ∧（本环未发射 StartBattle ∨ 发射验证成功）才复位——StartBattle 验证失败的环在外循环仍记 round_success，该形态部署链不健康不复位；发射结果载体 = `ExecState.last_prep_battle_launch_ok` 三态，消费后清 None 防跨环残留；1-1 冻结局实证旧无条件复位使预算形同虚设） | 前台无角色恢复链（确认→验证重部署→验前排≥1→再出战）超限 round_fail 交兜底链，不再无限 round_wait（1-1 事故 5h 死循环返工） |
| `PLANE_MISDISPATCH_LIMIT=3` | 连续计（接管/过渡成功清零） | 位面过渡误分发型 fail 超限 round_fail（boss 简报帧误分发每 2s 无限循环实证） |
| director fail streak 5 | 连续计 | CwScreenPrep 连续 5 次失败 → round_fail 交未知画面兜底链（消除静默 ping-pong；round_fail 在 node_max_retry 400 下不停机——刻意：消除"静默"，warning 进日志即哨兵，停机决策留给观察者） |

> 补注:分支守卫钩子（0n visit_ok/_fail 计数、0q streak 复位、A1 bail 清除、B5 窗口关+闩清）自 dispatch 包装落地起经 `_dispatch_screen_op` 的 **on_result 调用点邻接闭包**执行——限额值与清零/超限语义不变，仅执行落点随包装迁移，钩子明细。

## 4. 未知画面兜底（常驻安全网；`cw_loop.py::CwLoop._handle_unknown_fallback`）

- 触发 = loop 尾所有分支不命中（兜一切未知态，非点名某态的临时捕获；移除条件 = 该类未知态全部建档实际不可达，长期保留）。
- `UNKNOWN_STOP_THRESHOLD=15` 轮 ≈ 2min（旧 30s 放宽，换取停机钩子触发前充分自愈窗口）；重试退避 = 2s 起步每连续一次翻倍，封顶 `UNKNOWN_RETRY_BACKOFF_CAP_S=10`（画面被任何分支接走 → streak 归 1 退避自动复位）。
- 触发动作：截图 + `unknown_state.flag`（处理流程：analyze_screen 离线判已建档命中 → 未命中按元素语义建档 + 0x 分支加 handler → 删 flag + 重启 server）→ `stop_running`。

## 5. 执行失败安灯（`cw_screen_prep.py` `_spend_unit_close`（判定与记账同点：购买单元收尾）+ `_exec_fail_hook_check`（安灯判定+触发）；分类器在 `run_state.py`）

> 安灯分类器输入面 = 内存直读的一手执行事实:购买单元的 `BuyCardsOutcome` 暂存 + finalize 关店金现读回填的 gold_close。`plan_truncated` 豁免通道语义 = 「刷新硬墙跳过」(单动作下不存在截断丢弃尾)。

- 判定与记账同点：购买单元收尾时跑分类器 `exec_fail_should_stop`——数据源 = 内存直读一手执行事实（单元暂存 `BuyCardsOutcome` 的 visit_actions/gold_open + finalize 关店金现读回填的 gold_close；facts 缺席或金读缺失 → unknown 不停，不猜）。旧数据源三流（decisions.jsonl plan 行 / spend_ledger.jsonl 单元行 / obs_conflicts join 兼容路径）已随删除波 1 停写，只辖存量语料——现行下钻 = journal（`state/journal.jsonl`：receipts 回执窗 + state.values.gold 行行快照）与本钩子 flag 的 plan/gold 三件组（同 `run_state.py` flag 文本口径）。
- "计划≠尝试"分流：plan_truncated（硬墙跳过/截断丢弃）豁免防误停；refresh_attempted/board_changed 进三态判定。
- 触发：每局最多停一次（`_exec_fail_hook_fired`）→ 截图 + `cw_exec_fail_hook.flag`（plan 明细 + gold 开/关）→ `stop_running(reason='hook:exec_fail_mismatch')`。

## 6. 商店未识别卡停机

防抖重读 2 帧（判据化自愈：牌行两帧指纹一致门 + ≥1.0s 观察窗）后仍有未识别槽 → 停机保画面（shop_unk.flag）待建档。**不能降级带病跑**（未识别卡按非 target 跳过 = 决策在残缺牌面上做 + 错过新内容建档窗口；用户 2026-08-24 裁决接受阻断代价）。

## 7. 降级链汇总（fail-closed 行为）

| 场景 | 降级行为 | 为什么 fail-closed |
|---|---|---|
| gold 失读（shop 关态） | 指纹 None 对 None 不构成假推进;备战入口 heavy 观察重试（旧腾席链 b「read_only 店取真值/链 c stale 试算」已随单动作循环迁移批死码清理删除） | 宁可重观察,不造值 |
| 卖前对拍不符 | **守卫断言两级分型**（2026-09-05 双账 HIT 实证定谳）——`guard_expected_vs_tracked`:①多集等价(成员同、槽位序异)⇒ WARNING「槽位布局漂移」+按 tracked 真值就地重播种逻辑态 bench,**不炸环**;②真多集分歧 ⇒ AssertionError 炸出(双属归因不变)。`guard_proposal_vs_expected`(提案 vs 期望态)仍恒炸;满栏买入豁免面已收窄(满栏合成买双账同构,豁免仅剩非合成满栏买像素差漏检的 fail-open 残余窗) | 不卖错件(卖出不可逆)。两守卫零读屏(tracked 纯内存),详见 `screen_op.md` §2.3/`action_exec.md` §4 |
| 全保护死锁（旧链 c） | （随腾席链死码删除退役;M4 腾席现由 mandate_v1 骨架义务承载） | — |
| 部署 cap 失读 | 单调链 max 兜底；全源失读 → 不设板满门（拖到游戏拒即真值） | 低读阻塞上阵（贵）> 高读白拖一次（便宜） |
| 空部署计划 | （旧 flow.py 发射门已随死码删除;部署候选单一源 = `cw_deploy_logic.select_deployments`,空候选不提案） | 空计划 ✓ = 假成功，G3 守卫停机形态 |
| 增量态构造 fail-closed | 金失读/tracked 空 → 回退全量 read_game_state | 空 tracked 真空/丢跟踪不可区分，不造值 |
| 期望态对账不一致 | 落缺陷台账留证（L1→复现升 L0 安灯），**不纠漂不重执行** | 对账是观测不是决策；纠漂需先归因 |
| 免费刷新 proc | flag 留证**不停机** | 免费不是失败（通道保留作对账防线） |
