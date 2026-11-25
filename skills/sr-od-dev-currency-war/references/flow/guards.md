# 守卫与停机(guards)

> 来源 = `operations/cw_loop.py` + `operations/cw_screen/cw_screen_prep.py` + `operations/cw_screen/cw_screen_shop.py` + `obs/cw_identity_obs.py` + `kernel/cw_mismatch_policy.py` 的守卫/停机/降级段。路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。

> 分工判据(od-dev-stop-hooks):**采集哨兵不停机**(bot 可能只是慢;停滞判读 = 事件哨兵 `skills/sr-od-dev-currency-war/scripts/cw_sentinel.py`,只保留证据不停机);**停机钩子保画面**(`stop_running(reason=..., save_screenshot=True)` 一行——框架自动截图 + `[stop]` 日志行即现场事实)。

## 1. 外循环连续失败重派上限(通用规则)

| 限额 | 计数语义 |
|---|---|
| `OP_FAIL_REDISPATCH_LIMIT`(值见代码) | 连续计数:任一分发 op 成功即清零(不同计数键的成功也算);同一计数键(`chain_key` 或 journal 名)连续 fail 达到上限 → 保留证据截图 + 显式出口交上层处置,取代无限空转。刻意之处 = 消除「静默」而非「重试」,ERROR 日志行让人和停滞哨兵都能看到 |

计数/判定统一在 `_dispatch_screen_op`。位面过渡的误分发根修在识别层:BOSS简报 id_mark 换装徽记模板(OCR 误读免疫),阶段一位面过渡身份分支挂 boss 判别排他。

**出口语义(停机转交接,双出口契约)**:耗尽出口按构造参数 `cleanup_delegate` 分流(产生点 = `_dispatch_screen_op` 防线段,契约单一源 = 该包装 docstring)——

- **默认(app 主路径,False)**:耗尽 → `round_success`,status 以 `STATUS_HANDOFF_PREFIX`(「异常退出交接:」)开头、后缀 = 触发计数键。语义 = 异常退出是预期内处置:节点出错过多触发弃局,loop 把「该退出但还没退」的状态交接给 app 退出收尾节点,由其调 `CwEntryExit` 清场退局回大厅(交接语义见 loop.md §6 与 entry-exit.md §4)。
- **委托清理模式(route⑤ 构造点,True)**:耗尽维持 `round_fail`(现状文案)——委托实例失败计数从零重算,出口若翻成交接 success 会让 exit 误判清理完成、残局遗留且账面成功(静默失败);由 exit 节点重试承接,其预算耗尽 → exit fail → app 失败收尾,残局可见非静默。

两出口都不吃 `node_max_retry` 预算——「不停机」指框架不自动重派,处置决策交上层:默认出口以带前缀 success 收敛 loop op(app 按前缀转交接);fail 出口作为顶层 op 结果时直接收敛运行 FAILED,作为委托清理实例结果时由 exit 节点重试承接(见上条)。

**链形 dispatch 分支契约**:链形分支(一个分支体内连续派发多个画面 op,现役唯一 = 投资环境链:环境 op → 等待 1-1)必须传同一 `chain_key` 归组计数(`_dispatch_screen_op` 可选参数,缺省 None = 计数键仍 journal 名);链首调用方按**双条件**判定防线已触发并提前返回(`result == FAIL` ∨ status 带交接前缀;两种出口都只从防线段产生,契约见包装 docstring;透传保两种模式「链尾不空跑」)。链形透传分支(3c,大厅收尾)为单发透传例外、不经连续失败重派上限(既有申报不变)。未按契约接线 = 绕过防线(链内交替 fail 异键归一失效的历史形态)。链形分支的限额按「连续 fail 分发次数」计,每轮失败消耗 2 次计数(链首 + 链尾各一次;语义申报见包装 docstring)。

备战交互链迁 `CwScreenPrep` 特殊流程段后的失败链形态(迭代 2026-11-18-prep-special-flow):锁定直出战未执行 = 画面 op 段3b retry 保锁(框架预算每访问 1 首跑+3 重试=4 次)→ 访问 fail 进入本重派上限计数,备战 op 键连续 fail 限 5 次重派发 → 至多约 20 次出战尝试,有界且 ≪ 旧形态 loop 节点原地重试预算 400 次。横幅守卫与兜底清(`_fallback_clear_pending`)留主循环识别命中后、派发前,与本重派上限的交界无变化。

## 2. 未知画面兜底(常驻兜底机制)

- 触发 = loop 尾所有分支不命中(兜一切未知态;移除条件 = 该类未知态全部建档实际不可达,长期保留)。
- 处置:每轮固定间隔重试(`UNKNOWN_RETRY_WAIT_S`,值见代码),连续 `UNKNOWN_FAIL_THRESHOLD`(值见代码)轮耗尽 → round_fail 交框架失败,日志 `[cw!]` 行即信号。
- 前置退出 = 战斗等待画面 op 自己的节点级预算(`UNKNOWN_BAIL_N`,值见代码;轮数达限 → op 截图保留证据 + round_fail 退出,由未知画面兜底接手)。
- **处理流程**:analyze_screen 离线判已建档命中 → 未命中按元素语义建档 + cw_loop 阶段一身份分发接入调用(新增处理器分支 + `CW_DISPATCH_SCREENS` 登记,三处缺一不可)→ 重跑;战斗特效帧(OCR 乱码)**先确认非新画面**(analyze_screen 为准)才可调大阈值或加等待。画面被任何分支接走 → 计数自然复位。

## 3. 商店未识别卡停机

位置 = 商店画面 op 观察 node 入口观察段(入口 = 单次读零防抖——读不到时交决策前置检查显式失败,禁重读等待)。判据 = 读链终判仍含 unknown 槽 → `stop_running(save_screenshot=True)` + round_fail——观察落地即停,决策/购买不见残缺牌面。**不能降级带着错误数据继续跑**(未识别卡按非 target 跳过 = 决策在残缺牌面上做 + 错过新内容建档窗口)。决策侧 unknown 窗收窄(花钱禁发出动作、仅 CloseShop)保留为第二道防线。
**处理流程**:对 `[stop]` 截图跑 analyze_screen + 离线 SIFT 交叉核对确认真未知 → 新卡建档(screen_info/立绘库)→ 重启 server 重跑。

## 4. 召唤物/物品未识别停机(`obs/cw_identity_obs.py`)

触发 = 备战栏槽位占用但 SIFT 未识别(金币说明 overlay 开着则跳过本帧判定——overlay 盖住备战栏右端会制造假「占用未识别」)。处置 = `stop_running(save_screenshot=True)`。**不能降级**——未建档物品被当空槽/普通占用乱操作比停机贵。

**离线规则(只对实时帧停机)**:「实时帧」= 从游戏窗口现截的画面;「离线帧」= 调用方用 `analyze_screen(screenshot=图路径)` 传入的历史图,backend 入口在读图分支内把它标成非实时(帧来源信号 = `sr_od/context/frame_source.py::frame_is_live()`)。钩子函数体第一句看这个标记:离线帧 → 只打一行 `[cw-hook][summon] 离线帧:占用未识别判定跳过` 日志后返回,不调 `stop_running`、不做面板守卫 OCR、不留证截图。理由:停机是在保护「正在跑的那一局」,读一张旧图没有局可停;旧图的留证会混进当前局的截图目录。判读离线读图结果时,看到占用未识别**不会**触发本钩子,要确认是否真有未建档物品须对实时画面读。其余只打日志不停机的留证汇点(存图 `kernel/cw_observe.py::cw_shot` / `cw_shot_unique`、入账 `obs_conflict`)口径见 `strategy/15_observation_multisource_arbitration.md` §1。
**处理流程**:点该槽位看内容 → 物品变体 → 补进 `find_armory_boxes`/`find_tomes` 模板或新增物品类目 → 真召唤物 → `character_avatar/<名>/raw.png` 建模板 → roster 核条目。

## 5. 观察对账失配告警(kernel;`cw_mismatch_policy.py` 槽 + `currency_war_app.py` 闭包)

触发 = `GameState.observe()` 观察覆盖 logic 值失配(逻辑态被实读证伪 = bug:此前观察态错 / 逻辑推算代码错)。失配先分三类处置:①白名单内机制性差异(`EXEMPT_REGISTRY` 登记并带原因)→ 直接采纳;②sim 局的证据 → 抑制告警;③其余 = 真失配 → 停机,不设开关。停机后按两原因排查:①此前观察态错——查 `state/journal.jsonl` 该字段前序写入行;②逻辑推算代码错——按 actor/动作组/写入方 evidence 定位修推算。机制性结构差异走豁免申报(`EXEMPT_REGISTRY`,带 reason)。

## 6. 降级链汇总(fail-closed 行为)

| 场景 | 降级行为 | 为什么 fail-closed |
|---|---|---|
| gold 失读(shop 关态) | 备战入口全量观察(heavy)重试 | 宁可重观察,不造值 |
| 卖出执行守卫 | 守卫断言唯一 = `guard_proposal_vs_expected`(提案动作的对象在期望态中存在且未被消费,非法 = 策略器 bug 显式报出;零读屏) | 不卖错件(卖出不可逆) |
| 部署 cap 失读 | 单调链最大值兜底;全部来源都读不到 → 不设「备战席已满」检查(拖动被游戏拒绝就是真值) | 低读阻塞上阵(贵)> 高读白拖一次(便宜) |
| 团队规模超限(「X/Y」红色 X > Y:主角光环持有者占 2 点规模,板满后再选即超限) | 出战前规模超限守卫(`prep_actions.guard_team_size_over_cap_for_battle`,席满守卫之后):现读「X/Y」经双帧确认(`cw_observation.read_paddle_pair_confirmed`)占用 > 上限 → **不发点击**,带受阻码 `未执行:团队规模超限(规模占用>上限)` + 受阻回执行交回外循环重观察;X/cap 任一不可读 → 放行(不可判 ≠ 超限);sim 零触及 | 超限态出战被游戏静默拒绝(无横幅无弹窗、按钮仍亮),点了 = 逻辑态「已出战」假前进 + 外循环白等战斗窗;守卫只拦不解脱——撤谁/卖谁/升上限归策略侧,解限动作落地前停在备战(连续失败走重派上限→弃局)。识别侧配套:状态容器 `team_size_used`(观察值 X)/ `chosen_aura`(选中光环)+ 派生读口 `team_size_used_of`(占用之和),策略帧空位按占用之和算 |
| 空部署计划 | 部署计划单一源空计划不产动作 | 空部署计划被判定为「成功」是假成功形态——空计划不产动作才正确 |
| 增量态构造 fail-closed | 金失读/tracked 空 → 回退全量 read_game_state | 空 tracked 真空/丢跟踪不可区分,不造值 |
| 期望态对账不一致 | 写入缺陷记录行保留证据,**不纠漂不重执行** | 对账是观测不是决策;纠漂需先归因 |
| 免费刷新次数失配 | 观察 id_mark 确认覆盖逻辑态失配 → 观察对账失配告警 | 次数 = 画面可观察的剩余次数,以实际观察为准纠正 |
