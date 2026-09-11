# ADR-0615: T-181 outcomes 断流定谳勘误 + 零结算段自标识列 v11 + 决策独有段时序插位

- 状态:已实施(commit 候编排者统一门)
- 关联:ADR-0605(v10 departures 加法列先例;本批同为装配端纯读派生列)、ADR-0577(v9「陈旧直到证伪」先验;合成行在场=有结算记录形态,与零行误报形态互斥)、ADR-0612(T-178 批,其落地审 F2 首报本病灶)、账本 T-181
- 实施面:`telemetry/match_archive.py`(SCHEMA_VERSION 10→11:`_settlement_gap` 派生列 + `assign_games` 决策独有段时序插位)、测试仓 `test_cw_telemetry_archive.py`(+3 锁)、`test_cw_departures.py`(字面钉版改单一源)

## 1. 背景

T-178 落地审 F2 报「live 根 outcomes 流 09-08 17:44:49 后断流」(其后 run_20260908_210431 rounds=6 / run_20260909_012536 rounds=1 零 outcome 行),立 T-181 排查批。排查定谳**推翻病灶前提**:遥测结算读链/落盘链无断点,两段全程零战斗、零结算屏帧,零行=正确行为;「rounds=6/1」是 runs 摘要 `rounds_survived` 写自收口时点 `state.round_num`(cw_loop.py 局终收口,备战停滞段带冻结非零值)的合法投影。同批发现分组器对决策独有段的时序错组(v11 bump 触发存量档案重装配时必然显影),随批治本。

## 2. Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| 断流 = 修结算读链/落盘链 | ✗(前提证伪) | 三档案直读(210431:79 决策帧全冻结 p2-r6、零 StartBattle 发射;012536:8 帧全冻结 (1,1)、4 次出战尝试未成战)+ op_journal 断流窗零战斗等待 op 分发 + 同链前后时段正常产结算行(链健康自证)——结算帧从未发生,无链可修 |
| 零结算段处置 = 离线补齐 outcomes 行 | ✗ | 真值源=结算屏帧,从未被捕获;decisions.state.hp 为沿用/冻结值非逐轮真值,合成行=schema 9 已退役的 synthetic 鬼值同款病理(ADR-0577 §3.3);零战斗段正确行数=0 |
| 零结算段处置 = 装配端自标识列(本批) | ✓ | 判读直接可见「零结算是事实而非丢数据」;纯读零运行时侵入,旧档案重装配即补齐(v6/v9/v10 先例) |
| 分组错组 = 续局归组加 ts 相邻性门 | ✗ | 门在归组端,补尾序仍在,孤立续局/多续段形态需逐个补门;插位治本于序,归组规则零改 |
| 分组错组 = 决策独有段按段首 ts 插回时序位(本批) | ✓ | 恢复「后继新局入流不夺前局续段」;归组主判据(首帧)与续局规则零改动,语义面最小 |

## 3. 已实施架构

### 3.1 断流定谳勘误(原 T-181 假设不成立)

- run_20260908_165445(16 结算行,末行 09-08 17:44:49):末次出战成功 17:40:11,17:45 起入 p2-r6 备战停滞,18:11 手停——停滞形态起于本段尾。
- run_20260908_210431(续段,接管 p2-r6 满板 8/8):备战环 17 分钟(买牌 0/无部署可做),**零 StartBattle 发射**,21:21:55 mcp:stop_run 手停;79 决策帧全冻结 (2,6),runs.rounds_survived=6=冻结值。
- run_20260909_012536(新局):备战正常(买 5/卖 1/部署 3),StartBattle 决策动作 ×4 均未成战(零战斗等待 op 分发+前台无角色恢复 ×4),01:28:17 备战环无进展守卫停机;rounds_survived=1=冻结值。
- 停滞形态横跨三个 server build(f763743f 尾段/1c65941a/8d2f34de),现 build f0cba2a7 不复现——行为层根因归策略/执行层另批核(遥测装配面不辖)。

### 3.2 `settlement_gap` 派生列(v11,装配端纯读)

段条目级字段,触发 = 本段决策帧 ≥1 且结算行(outcomes)= 0,值 `{decision_frames, claimed_rounds_survived}`(claimed 取该段 runs 摘要,供与真实结算数对照)。边界:①空段(零决策帧)不标注;②有任一 outcome 行(含 synthetic_supply/recovered/loss_page 来源)即视为有结算记录不标注——合成行可信度争议归判读侧先验(ADR-0577),不在本键重复表达。落在 `segments[]` 与 `endgame.segment_summaries` 双面(同一列表对象)。

### 3.3 `assign_games` 决策独有段时序插位(v11 同批修)

旧法:决策独有段(零结算段,恰是本列目标形态)按 min-ts 排序后**整体补尾**在 seg_order 尾部,续局归组「首帧≠(p1,r1)→并入 games[-1]」无时序门 → 该段被错组到时间上晚于它的最后一局名下。temp 副本亲测实证:现流全量重分组曾给出 `g_20260909_053235 = [053235, run_20260908_210431]`(比段末帧晚 8.5 小时的局名下)、`g_20260908_165445` 静默丢段——v11 bump 的 auto-rebuild 兼容路径会在 commit 后首次判读读档时按当前流 composition 重装配存量档案,锚点配对即被破坏,故随批治本(错组规则系存量,非 v11 引入)。修法:每段段首 ts(跨 decisions/outcomes 两流最小值)单遍成账,决策独有段按 ts 插回时序位。边界申报:①段首 ts 缺失(空串)无法比较,保持补尾退化(旧行为);②同 ts 平手按 run_id 字典序保确定性;③孤立续局(插位后仍居首)自成一体+continuity_note 语义不变;④归组主判据(首帧)与续局规则零改动。

## 4. 验证

- 新锁 3:`test_zero_settlement_segment_self_identified`(两段局构造:零结算段自标识+正常段键缺省+endgame.segment_summaries 双面可见)、`test_settlement_gap_skips_empty_and_settled_segments`(空段/合成行来源边界)、`test_decision_only_segment_groups_to_prior_game_with_later_outcome_game`(后继带 outcome 局在场时决策独有段仍归前局+gap 落锚点局名下)全绿。
- 变异红:注解停用(恒 `{}`)→ 主锁红/边界锁绿;插位停用(比较恒假→补尾退化)→ M1 锁红/两段局锁绿;还原双绿。
- 端到端复演(live 流 temp 副本,零 live 触碰):`g_20260908_165445 = [165445, 210431(gap={79,6})]`、`g_20260909_012536 = [012536(gap={8,1})]`、`g_20260909_053235 = [053235]`,index 行同步。
- 回归:test_cw_telemetry_archive 68 例全绿;受影响面(departures/t100/op_journal)合计 100 例全绿;L1 全量(not slow and not legacy_baseline)3381+ 绿(1 失败=T-168 并行批在途时点态,其锁重推后零红,与本批遥测装配面无因果)。
- ruff:主仓改动文件全绿;test_cw_telemetry_archive 29 错=存量债(新增区间零命中)。

## 5. 边界与残余风险

- `rounds_survived` 写点语义(收口时点 `state.round_num`)未动——写点在 cw_loop.py 局终收口(行为面),零结算段的 claimed 值仍会是冻结值;判读以 `settlement_gap.claimed_rounds_survived` 与真实结算数并读为准,写点语义修正候行为层批。
- 零结算段自标识只回答「有没有结算」,不回答「为什么没有」——停滞根因(备战炼狱/出战未成战)属策略/执行层,见 §3.1 跨层指针。
- 存量档案(现盘 schema 9/10)在 bump 生效后首次 load 重装配:分组结果与装配时点快照可能不同(本批修复使重装配结果=时序真值);若档案曾被按错组落盘,重装配即纠偏。
