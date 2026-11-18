# 守卫与停机(guards)

> 来源 = `operations/cw_loop.py` + `operations/cw_screen/cw_screen_prep.py` + `operations/cw_screen/cw_screen_shop.py` + `obs/cw_identity_obs.py` + `kernel/cw_mismatch_policy.py` 的守卫/停机/降级段。路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。

> 分工判据(od-dev-stop-hooks):**采集哨兵不停机**(bot 可能只是慢;停滞判读 = 事件哨兵 `skills/sr-od-dev-currency-war/scripts/cw_sentinel.py`,只保留证据不停机);**停机钩子保画面**(`stop_running(reason=..., save_screenshot=True)` 一行——框架自动截图 + `[stop]` 日志行即现场事实)。

## 1. 外环连续 fail 重派网(通用网)

| 限额 | 计数语义 |
|---|---|
| `OP_FAIL_REDISPATCH_LIMIT`(值见代码) | 连续计(任一分发 op ok 清零;异键 ok 同闭窗);同一分发 op 连续 fail 达限额 → 保留证据截图 + round_fail 显式停交上层,取代无界空转。round_fail 的 FAIL 枚举不吃 node_max_retry 预算,直接收敛运行 FAILED——「不停机」指框架不自动重派、停机决策交上层观察者;刻意处 = 消除「静默」而非「重试」,ERROR 行进日志 = 哨兵 STALL 通道与人都能看到 |

计数/判定统一在 `_dispatch_screen_op`。位面过渡的误分发根修在识别层:BOSS简报 id_mark 换装徽记模板(OCR 误读免疫),阶段一位面过渡身份分支挂 boss 判别排他。

**链形 dispatch 分支契约**:一个分支体内多次 dispatch 的链形分支必须传同一 `chain_key` 归组计数(`_dispatch_screen_op` 可选参数,缺省 None = 计数键仍 journal 名),链首调用方透传防线 FAIL 出口(FAIL 枚举只从防线段产生,出口契约见包装 docstring);现役唯一多 dispatch 链形分支 = 投资环境链(环境 op → 等待 1-1),链形透传分支(3c,大厅收尾)为单发透传例外、不经本网(既有申报不变)。未按契约接线 = 绕过防线(链内交替 fail 异键归一失效的历史形态)。链形下限额计「连续 fail 分发次数」,每粘滞分发轮烧 2 次(链首+链尾;语义申报见包装 docstring)。

备战交互链迁 `CwScreenPrep` 特殊流程段后的失败链形态(迭代 2026-11-18-prep-special-flow):锁定直出战未执行 = 画面 op 段3b retry 保锁(框架预算每访问 1 首跑+3 重试=4 次)→ 访问 fail 走本网,备战 op 键连续 fail 限 5 次重派发 → 至多约 20 次出战尝试,有界且 ≪ 旧形态 loop 节点原地重试预算 400 次。横幅守卫与兜底清(`_fallback_clear_pending`)留主循环识别命中后、派发前,与本网交界无变化。

## 2. 未知画面兜底(常驻安全网)

- 触发 = loop 尾所有分支不命中(兜一切未知态;移除条件 = 该类未知态全部建档实际不可达,长期保留)。
- 处置:每轮固定间隔重试(`UNKNOWN_RETRY_WAIT_S`,值见代码),连续 `UNKNOWN_FAIL_THRESHOLD`(值见代码)轮耗尽 → round_fail 交框架失败,日志 `[cw!]` 行即信号。
- 前置 bail = 战斗等待 op 自己的节点级预算(`UNKNOWN_BAIL_N`,值见代码;轮数达限 → op 截图保留证据 + round_fail bail,由本兜底链接手)。
- **处理流程**:analyze_screen 离线判已建档命中 → 未命中按元素语义建档 + cw_loop 阶段一身份分发接入调用(处理器臂 + `CW_DISPATCH_SCREENS` 登记,三处缺一不可)→ 重跑;战斗特效帧(OCR 乱码)**先确认非新画面**(analyze_screen 为准)才可调大阈值或加等待。画面被任何分支接走 → 计数自然复位。

## 3. 商店未识别卡停机

位置 = 商店画面 op 观察 node 入口观察段(入口 = 单次读零防抖——读缺交决策前置门显式失败,禁重读等待)。判据 = 读链终判仍含 unknown 槽 → `stop_running(save_screenshot=True)` + round_fail——观察落地即停,决策/购买不见残缺牌面。**不能降级带病跑**(未识别卡按非 target 跳过 = 决策在残缺牌面上做 + 错过新内容建档窗口)。决策侧 unknown 窗收窄(花钱禁发出动作、仅 CloseShop)保留为纵深第二线。
**处理流程**:对 `[stop]` 截图跑 analyze_screen + 离线 SIFT 交叉核对确认真未知 → 新卡建档(screen_info/立绘库)→ 重启 server 重跑。

## 4. 召唤物/物品未识别停机(`obs/cw_identity_obs.py`)

触发 = 备战栏槽位占用但 SIFT 未识别(金币说明 overlay 开着则跳过本帧判定——overlay 盖住备战栏右端会制造假「占用未识别」)。处置 = `stop_running(save_screenshot=True)`。**不能降级**——未建档物品被当空槽/普通占用乱操作比停机贵。
**处理流程**:点该槽位看内容 → 物品变体 → 补进 `find_armory_boxes`/`find_tomes` 模板或新增物品类目 → 真召唤物 → `character_avatar/<名>/raw.png` 建模板 → roster 核条目。

## 5. 观察对账失配告警(kernel;`cw_mismatch_policy.py` 槽 + `currency_war_app.py` 闭包)

触发 = `GameState.observe()` 观察覆盖 logic 值失配(逻辑态被实读证伪 = bug:此前观察态错 / 逻辑推算代码错),经三分流(豁免注册表 / sim 证据抑制 / 真失配)后仍真失配 → 停机。处置 = 两原因排查:①此前观察态错——查 `state/journal.jsonl` 该字段前序写入行;②逻辑推算代码错——按 actor/动作组/写端 evidence 定位修推算。机制性结构差异走豁免申报(`EXEMPT_REGISTRY`,带 reason),不留开关。

## 6. 降级链汇总(fail-closed 行为)

| 场景 | 降级行为 | 为什么 fail-closed |
|---|---|---|
| gold 失读(shop 关态) | 备战入口 heavy 观察重试 | 宁可重观察,不造值 |
| 卖出执行守卫 | 守卫断言唯一 = `guard_proposal_vs_expected`(提案动作的对象在期望态中存在且未被消费,非法 = 策略器 bug 显式报出;零读屏) | 不卖错件(卖出不可逆) |
| 部署 cap 失读 | 单调链 max 兜底;全源失读 → 不设板满门(拖到游戏拒即真值) | 低读阻塞上阵(贵)> 高读白拖一次(便宜) |
| 空部署计划 | 部署计划单一源空计划不产动作 | 空计划 ✓ = 假成功形态 |
| 增量态构造 fail-closed | 金失读/tracked 空 → 回退全量 read_game_state | 空 tracked 真空/丢跟踪不可区分,不造值 |
| 期望态对账不一致 | 落缺陷台账保留证据,**不纠漂不重执行** | 对账是观测不是决策;纠漂需先归因 |
| 免费刷新次数失配 | 观察 id_mark 确认覆盖逻辑态失配 → 观察对账失配告警 | 次数 = 画面可观察的剩余次数,以实际观察为准自愈 |
