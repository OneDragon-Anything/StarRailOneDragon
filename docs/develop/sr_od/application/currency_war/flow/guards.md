# 守卫总册（guards）

> 反向规格化来源 = `operations/cw_loop.py` + `operations/cw_screen/cw_screen_prep.py` + `operations/cw_screen/cw_screen_buy_cards.py` + `obs/cw_identity_obs.py` + `kernel/cw_mismatch_policy.py` 的守卫/停机/降级段。职责：识别域与执行面的停机/留证防线。对局状态推进的监测不在框架——停滞判读 = 事件哨兵 `skills/sr-od-currency-war-dev/scripts/cw_sentinel.py`(v5.2:STALL 同特征零推进/LOOP 签名循环/NODE-DWELL 相位滞留/SILENCE 沉默,只留证不停机)。路径根 = `src/sr_od/application/currency_war/`。
> 分工判据（od-dev-stop-hooks，2026-09-16 框架化）：**采集哨兵不停机**（bot 可能只是慢）；**停机钩子保画面**（`stop_running(reason=..., save_screenshot=True)` 一行——框架自动截图 + `[stop]` 日志行即现场事实，flag 文件已全量退役，处理流程知识归本篇）。

## 1. 外环连续 fail 重派网（通用网）

| 限额 | 值 | 语义 |
|---|---|---|
| `OP_FAIL_REDISPATCH_LIMIT=5` | 连续计（任一分发 op ok 清零；异键 ok 同闭窗） | 同一分发 op 连续 fail 达本值 → 留证截图 + round_fail 显式停交上层，取代「fail → round_wait 零预算重派」的无界空转（T-266；实锤 = 选择伙伴 15 连败靠 NODE-DWELL 900s 哨兵兜住才停，2026-09-15 事故）。round_fail 在 node_max_retry 400 下**不停机**——刻意：消除「静默」而非「重试」，ERROR 行进日志 = 哨兵 STALL 通道与人都能看到，停机决策留给观察者 |

> 原 §1 的两条专用 streak 守卫（0q 位面过渡误分发 =3、prep 连续失败 =5）已退役并入本网：阈值同值平手无行为差，计数/判定统一在 `_dispatch_screen_op`（hook 早退位次之后，hook 仍可短路）。链形透传分支（3c）不经本网（各有自身预算）。
> 补注:分支守卫钩子（0n visit_ok/_fail 计数、A1 bail 清除、B5 窗口关+闩清）自 dispatch 包装落地起经 `_dispatch_screen_op` 的 **on_result 调用点邻接闭包**执行，仅执行落点随包装迁移，钩子明细。
> 位面过渡的误分发根修在识别层（2026-09-16）：BOSS简报锚换装徽记模板（OCR 误读免疫），阶段一位面过渡身份臂挂 boss 判别排他（接管派发 boss op）；原 0q 兜底随「未建档实证的故障形态不作兜底理由」裁定同批退役（见 outer_loop §2.3 退役记录）。

## 2. 未知画面兜底（常驻安全网；`cw_loop.py::CwLoop._handle_unknown_fallback`）

- 触发 = loop 尾所有分支不命中（兜一切未知态，非点名某态的临时捕获；移除条件 = 该类未知态全部建档实际不可达，长期保留）。
- 处置（2026-09-16 框架化）：每轮 1s 重试（`UNKNOWN_RETRY_WAIT_S=1`，恒定无退避），连续 `UNKNOWN_FAIL_THRESHOLD=15` 轮耗尽 → round_fail 交框架失败（运行 FAILED 收口）——不再 stop_running/flag/截图，日志 `[cw!]` 行 + 失败结果即信号。
- 前置 bail = 战斗等待 op 自己的节点级预算（`cw_screen_battle_wait`，`UNKNOWN_BAIL_N=10` 轮未知 → op 截图留证 + round_fail bail 交回本兜底；不停机，兜底链裁决权留外循环）。
- 处理流程：analyze_screen 离线判已建档命中 → 未命中按元素语义建档 + cw_loop 0x 分支加 handler → 重跑；战斗特效帧（OCR 乱码）**先确认非新画面**（analyze_screen 为准）才可调大阈值或加等待。画面被任何分支接走 → 计数自然复位。

## 3. 商店未识别卡停机

位置 = 商店画面 op **入口观察处**（`cw_screen_buy_cards.run_buy_waves`，回执落地即判）。判据 = 读链终判（`read_shop_cards` 内部易误判重观察之后）仍含 unknown 槽 → `stop_running(save_screenshot=True)` 框架截图留证（`[stop]` 日志行）+ round_fail——观察落地即停，决策/购买不见残缺牌面（2026-09-16 迁移+框架化：防抖探针/flag 随「识别不到就是 bug」裁定退役，旧收工段钩子在买波之后 = 太晚）。**不能降级带病跑**（未识别卡按非 target 跳过 = 决策在残缺牌面上做 + 错过新内容建档窗口；用户 2026-08-24 裁决接受阻断代价）。决策侧 unknown 窗收窄（花钱禁发射、仅 CloseShop，`mandate_v1/shop.py`）保留为纵深第二线。
处理流程：对 `[stop]` 截图跑 analyze_screen + 离线 SIFT 对拍（真实 rect 商店牌-1..5）确认真未知 → 新卡建档（screen_info/立绘库）→ 重启 server 重跑。

## 4. 召唤物/物品未识别停机（`obs/cw_identity_obs.py`）

触发 = 备战栏槽位占用但 SIFT 未识别（非角色非已知箱/典籍；金币说明 overlay 开着则跳过本帧判定——overlay 盖住备战栏右端会制造假「占用未识别」，局 69 实证）。处置 = `stop_running(save_screenshot=True)` 框架留证（2026-09-16 框架化：flag 退役）。**不能降级**——未建档物品被当空槽/普通占用乱操作比停机贵（用户 2026-08-20 纠偏）。
处理流程：点该槽位看内容（物品直接开启/弹面板，角色出详情）→ 物品变体 → 补进 `find_supply_boxes`/`find_tomes` 模板或新增物品类目（r100j 教训：卡包变体 TM 0.54 漏检，物品占槽是常态）→ 真召唤物 → `portrait_plaza/<名>/raw.png` 建模板 → roster 核条目。偏常驻兜底，识别覆盖该类物品前保留。

## 5. 特殊投资策略停机（临时捕获；`cw_screen_prep.py`）

触发 = 效果清单含候逐条确定的名单效果（`_SPEC_INVEST_WATCH_NAMES`，挂点 = visit_open_shop 入口）→ 直接停机（`stop_running(save_screenshot=True)`），**人工采集**——不再代码落截图/转储/flag（2026-09-16 裁定）。停机后画面原样保持（店开着）：人工看画面 / MCP 截图补帧，对照效果注册表逐条确定该组合下商店改写/计数/经验行为，结论回填效果规格 verdict/notes。同组合进程内只停一次（重启清零 = 允许重停）。采够后删整段（常量+方法+挂点两行），不留开关。

## 6. 观察对账安灯（kernel；`cw_mismatch_policy.py` 槽 + `currency_war_app.py` 闭包）

触发 = `GameState.observe()` 观察覆盖 logic 值失配（逻辑态被实读证伪 = bug：此前观察态错 / 逻辑推算代码错），经三分流（豁免注册表 / sim 证据抑制 / 真失配）后仍真失配 → 停机（闭包 = stop_running 一行，截图归框架）。处置 = 两原因排查：①此前观察态错——查 `state/journal.jsonl` 该字段前序写入行；②逻辑推算代码错——按 actor/动作组/写端 evidence 定位修推算。机制性结构差异走豁免申报（`EXEMPT_REGISTRY`，带 reason），不留开关。

## 7. 降级链汇总（fail-closed 行为）

| 场景 | 降级行为 | 为什么 fail-closed |
|---|---|---|
| gold 失读（shop 关态） | 备战入口 heavy 观察重试（旧腾席链 b「read_only 店取真值/链 c stale 试算」已随单动作循环迁移批死码清理删除） | 宁可重观察,不造值 |
| 卖前对拍不符 | **守卫断言两级分型**（2026-09-05 双账 HIT 实证定谳）——`guard_expected_vs_tracked`:①多集等价(成员同、槽位序异)⇒ WARNING「槽位布局漂移」+按 tracked 真值就地重播种逻辑态 bench,**不炸环**;②真多集分歧 ⇒ AssertionError 炸出(双属归因不变)。`guard_proposal_vs_expected`(提案 vs 期望态)仍恒炸;满栏买入豁免面已收窄(满栏合成买双账同构,豁免仅剩非合成满栏买像素差漏检的 fail-open 残余窗) | 不卖错件(卖出不可逆)。两守卫零读屏(tracked 纯内存),详见 `../screens/op-layer.md` §1.3/`action_exec.md` §4 |
| 全保护死锁（旧链 c） | （随腾席链死码删除退役;M4 腾席现由 mandate_v1 骨架义务承载） | — |
| 部署 cap 失读 | 单调链 max 兜底；全源失读 → 不设板满门（拖到游戏拒即真值） | 低读阻塞上阵（贵）> 高读白拖一次（便宜） |
| 空部署计划 | （旧 flow.py 发射门已随死码删除;部署候选单一源 = `cw_deploy_logic.select_deployments`,空候选不提案） | 空计划 ✓ = 假成功形态(候选单一源空不提案为唯一防线;停顿监测归哨兵) |
| 增量态构造 fail-closed | 金失读/tracked 空 → 回退全量 read_game_state | 空 tracked 真空/丢跟踪不可区分，不造值 |
| 期望态对账不一致 | 落缺陷台账留证，**不纠漂不重执行** | 对账是观测不是决策；纠漂需先归因 |
| 免费刷新 proc | flag 留证**不停机** | 免费不是失败（通道保留作对账防线） |

## 退役记录

- **执行失败安灯**（2026-09-16，`75e107dc9`）：「计划花费>0 且金差≈0」判定语义随动作 op 机械执行化失效，并入 §6 统一对账。
- **L0 观察缺陷安灯**（2026-09-16）：「确认缺陷即停实机」的停机决策不该住在缺陷/遥测层——判级与台账保留（L1/L2），停机不再由缺陷层发起。
- **星级回退停机钩子**（2026-09-16）：星回退处置归 §6 观察对账（observe-vs-logic），不再单设钩子与采样登记（`exec_books.star_regression` 随删）。
- **flag 文件全量退役**（2026-09-16）：`unknown_state`/`shop_unk`/`summon_stop_hook`/`l0_andon_hook`/`cw_reconcile_andon`/`spec_invest_shop_hook`/`battle_wait_bail` 等 flag 不再产出——停机现场事实 = `[stop]` 日志行（reason + 截图路径）+ `.debug/images/` 框架截图；处理流程知识归本篇各节。孤儿历史文件（含写端早亡的 `stall_watch`/`prep_no_progress`）已清。例外 = `cw_free_refresh_proc.flag`（免费刷新对账留证，不停机非停机钩子，§7）。
