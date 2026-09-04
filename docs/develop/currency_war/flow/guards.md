# 守卫总册（guards）

> 反向规格化来源 = `operations/cw_loop.py` + `operations/cw_screen/cw_screen_prep.py` + `operations/cw_op/cw_op_buy_cards.py` 的守卫/停机/降级段。职责：卡死与失活的检出、留证、停机或降级。路径根 = `src/sr_od/application/currency_war/`。
> 分工判据（od-dev-stop-hooks）：**采集哨兵不停机**（bot 可能只是慢）；**停机钩子保画面**（stop_running + flag + 截图，处理完删 flag 重启）。本篇全部为流程防线，与策略判据无关。

## 1. G3 环级无进展守卫（架构反思三卡死批防线①；`cw_loop.py:226-231,1077-1126`）

- **判据**：连续 `PREP_NO_PROGRESS_ROUNDS=3`【注·框架常量，三起实机卡死 8-34min 在 3 环(≈1min)内停机校准】个备战环满足"同签名动作批 ∧ 状态零推进"。
- **动作批签名** = `session.last_prep_action_sig`（备战单轮 op 决策出口写动作类型元组；破墙段同写；overlay 交回/策略异常/破墙派生帧前保持 None，`cw_screen_prep.py:1211-1215,1287-1290`）。空批 = 空元组（连续空批+状态冻结同样计无进展）。
- **状态指纹** = `prep_no_progress_state_fingerprint`（`cw_loop.py:107-131`）：(plane, round_num, last_node_type, gold, bench 身份串, deployed 身份串)。任一分量变化 = 有推进（战斗等待不进备战分支且回备战时 round 必变；正常多帧部署改变身份或 gold；闩跳过帧动作批不同）。球/箱/vacancy 刻意不进指纹（识别抖动误计数，由动作签名腿覆盖）。
- **计数纯函数** `prep_no_progress_tick`：同签名累加、异签名归零；sig=None 不累计（防跨环误延）。
- **触发动作**：截图 + `write_no_progress_flag`（签名序列+计数+处理指引）→ 附 `prep_stall_pending_expected` 留证（EXPECTED_STATE prep_obs 覆盖点滞留条目）→ `stop_running(reason='hook:prep_no_progress')`。取代旧备战 stall 留证线（单一计数单一签名，不留两套）。
- flag 处理指引要点：同批动作反复发射而状态不动 = 执行面变换失败（遮罩挡拖拽/点击落空/闩漏网活锁）→ 按截图判画面：未建档 overlay → 建档 + 0x 分支；已建档 → 查该动作执行链。

## 2. 停滞 watchdog（r119；哨兵不停机；`cw_loop.py:209-215,434-495`）

- 每 `STALL_SNAPSHOT_EVERY=5` iter 采样一次画面指纹（OCR 关键词 frozenset 哈希）；连续 `STALL_N=6` 次相同（≈1-2min 同屏）→ 写 `stall_watch.flag`（关键词+截图+处理指引）+ `[cw!]` 日志一次。**不停机**（bot 可能只是慢，停机代价>等待代价）。
- **战斗窗口宽限**（ADR-0250）：`BATTLE_WATCH_GRACE_S=600`【注·框架常量，覆盖实测 4-5.5min 战斗】内不计数（出战后合法静止；战斗 HUD 关键词可全程不含豁免词，宽限窗防误报）。开窗 = 备战环出口出战；关窗 = 见结算屏/回备战。
- 豁免关键词：战斗/胜利/挑战/结算/准备/倒计时。

## 3. 误分发与恢复链限额

| 限额 | 值 | 语义 |
|---|---|---|
| `FRONTLESS_REDEPLOY_LIMIT=2` | 本 run 累计（出战真转移后复位） | 前台无角色恢复链（确认→验证重部署→验前排≥1→再出战）超限 round_fail 交兜底链，不再无限 round_wait（1-1 事故 5h 死循环返工） |
| `PLANE_MISDISPATCH_LIMIT=3` | 连续计（接管/过渡成功清零） | 位面过渡误分发型 fail 超限 round_fail（boss 简报帧误分发每 2s 无限循环实证） |
| director fail streak 5 | 连续计 | CwScreenPrep 连续 5 次失败 → round_fail 交未知画面兜底链（消除静默 ping-pong；round_fail 在 node_max_retry 400 下不停机——刻意：消除"静默"，warning 进日志即哨兵，停机决策留给观察者） |

## 4. 未知画面兜底（常驻安全网；`cw_loop.py:194-200,1518-1569`）

- 触发 = loop 尾所有分支不命中（兜一切未知态，非点名某态的临时捕获；移除条件 = 该类未知态全部建档实际不可达，长期保留）。
- `UNKNOWN_STOP_THRESHOLD=15` 轮 ≈ 2min（旧 30s 放宽，换取停机钩子触发前充分自愈窗口）；重试退避 = 2s 起步每连续一次翻倍，封顶 `UNKNOWN_RETRY_BACKOFF_CAP_S=10`（画面被任何分支接走 → streak 归 1 退避自动复位）。
- 触发动作：截图 + `unknown_state.flag`（处理流程：analyze_screen 离线判已建档命中 → 未命中按元素语义建档 + 0x 分支加 handler → 删 flag + 重启 server）→ `stop_running`。

## 5. 策略失活早停（ADR-0342/dd-031；`cw_loop.py:360-362,1142-1179`）

- 判据：连续 **2 个完整轮**无任何策略心跳决策行（心跳 = sid 行或载体行，单一源 `query._row_heartbeat`；外环停转 = 整轮零心跳行）→ 停局重启加载策略（"重大修复待加载 = 无条件早停"的运行期镜像：外环死了继续跑 = 零信息量局）。
- dd-031 定谳辖域收敛：sid 行唯一写点在店内决策；mandate 合法跳过开店（三开店站全关）时整轮只有载体行——旧判据"无 sid 行=死"把健康局误杀。结算点 = 备战入口查**上一轮**（本轮决策尚未发生，查本轮恒空会误杀）；telemetry 关闭时本检查让位。

## 6. 执行失败安灯（`cw_screen_prep.py:1604-1640` `_spend_unit_close`（判定与记账同点：购买单元收尾，钩子调用 `:1636-1640`）+ `:1642-1712` `_exec_fail_hook_check`（安灯判定+触发）；分类器在 `run_state.py`）

> 【待 ADR-0517 迁移】本节消费面为波级契约表述（本轮 shop plan 行 / plan_truncated 截断申报）：单动作循环下「计划≠尝试」的截断语义消失，安灯分类器输入与豁免通道的重锚面见 `screen_op.md` §8.5（输入改逐动作事件流；豁免按单动作「跳过≠失败」语义重推）。实现未动，以下 as-built 如实。

- 判定与记账同点：购买单元收尾时跑分类器 `exec_fail_should_stop`——数据源 = decisions.jsonl 本轮 shop plan 行（plan/开店金，shop 开态可信）+ spend_ledger.jsonl 本单元行 gold_close（身份键完整；旧行回退 obs_conflicts join 兼容路径；读失败 None 进分类器 = unknown 不停，不猜）。
- "计划≠尝试"分流（ADR-0456）：plan_truncated（硬墙跳过/截断丢弃）豁免防误停；refresh_attempted/board_changed 进三态判定。
- 触发：每局最多停一次（`_exec_fail_hook_fired`）→ 截图 + `cw_exec_fail_hook.flag`（plan 明细 + gold 开/关）→ `stop_running(reason='hook:exec_fail_mismatch')`。

## 7. 商店未识别卡停机（用户裁决恢复；`cw_op_buy_cards.py:1072-1135`）

防抖重读 2 帧（判据化自愈：牌行两帧指纹一致门 + ≥1.0s 观察窗）后仍有未识别槽 → 停机保画面（shop_unk.flag）待建档。**不能降级带病跑**（未识别卡按非 target 跳过 = 决策在残缺牌面上做 + 错过新内容建档窗口；用户 2026-08-24 裁决接受阻断代价）。

## 8. 降级链汇总（fail-closed 行为）

| 场景 | 降级行为 | 为什么 fail-closed |
|---|---|---|
| gold 失读（shop 关态） | 指纹 None 对 None 不构成假推进；链 b 先开 read_only 店取真值，同环第 2 次仍无 → stale 试算（gate 拒落链 c） | 宁可用保守试算 + 游戏侧 gate 拒绝，不死等（局47 死循环修） |
| 卖前对拍不符 | 整笔跳过（stale_proposal），下轮重 plan | 不卖错件（卖出不可逆）。守卫本体 = 两条内存账对拍（策略侧快照 vs 执行侧 tracked，`cw_op_buy_cards.py:163-173,993-1008`），零读屏；迁移两属拆分见 `screen_op.md` §2.3 |
| 全保护死锁（链 c） | 等待超限 → 强制卖首个非在场件 | 保护是优化不是死锁理由 |
| 部署 cap 失读 | 单调链 max 兜底；全源失读 → 不设板满门（拖到游戏拒即真值） | 低读阻塞上阵（贵）> 高读白拖一次（便宜） |
| 空计划 RunDeploy | 发射门抑制（不发射）+ 执行侧 STATUS_NOOP | 空计划 ✓ = 假成功，G3 守卫停机形态 |
| 增量态构造 fail-closed | 金失读/tracked 空 → 回退全量 read_game_state | 空 tracked 真空/丢跟踪不可区分，不造值 |
| 恢复原语/defer 门 | 反复失败放弃该动作族走主流程，环入口 defer 清零重判 | 无门活锁（M55 OpenTome 365 条重试实证） |
| 期望态对账不一致 | 落缺陷台账留证（L1→复现升 L0 安灯），**不纠漂不重执行** | 对账是观测不是决策；纠漂需先归因 |
| 免费刷新 proc | flag 留证**不停机** | 免费不是失败（通道保留作对账防线） |

## 9. ⚠️ 现状违宪待改标记

本篇辖内全部为流程防线常量（阈值 = 实机事故校准的框架常量，不进策略决策门，无三形态义务）；无位面字面门、无 hp 消费。登记流程债一项：`PREP_NO_PROGRESS_ROUNDS=3` 与旧 stall 留证线的取代关系已在代码注释钉死，守卫语义无违例。
