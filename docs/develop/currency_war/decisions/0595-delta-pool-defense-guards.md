# ADR-0595: Δ池快照生成器数据防线（fake_/sim_ run 隔离 + 语料塌缩守卫）

日期: 2026-09-08
状态: 已采纳（池锚批事故申报〔台账 T-126 note 2026-09-08〕→ 防线批实施 → 本 ADR 编排者落档）

## 背景（事故）

2026-09-08 实证：telemetry 重构后 Δ池再生源迁移至 `.debug/currency_war/telemetry/live`，该目录仅剩 3 个 run（112 决策行，含假游戏局 run_id=fake_20260908）；旧 16391 行全量语料源目录（`.debug/temp/currency_war/replay/decisions.jsonl`）已消失。假游戏局终触发 ledger_hooks 的 W109 局终再生钩，用微型语料覆盖提交快照（当日 11:54/11:57/12:05 三次实证，指纹 460e6031e2f4ae06 → 59dbc23bb68e0dc5），导致锚定该快照的 9 条测试红。生成器既有「禁 sim 批回灌」守卫不拦 fake_* run 进入 live 源，亦无源语料塌缩防线。

## 决策

生成器（regenerate_snapshot 所在模块）加两道防线：

1. **run 级隔离（机制化双轨）**：`QUARANTINED_RUN_PREFIXES`（fake_=假游戏/调试注入局；sim_=sim 批 run，runner.write_batch_ledger 批目录名实证）+ 保留 8/22 双进程事故两局显式名单；统一判据单一源 `_run_quarantine_reason`（前缀规则优先、名单兜底），命中入 META `quarantined_hits` 披露。**适用范围含 auto 池**：`pool._pool_from_replay` decisions/outcomes 两循环消费同一判据（消费方非第二实现）——`resolve_pool('auto')` 是 simulate_p1 缺省池，假局/sim 批 run 不入缺省校准路径（落地审 F1 裁断，ADR-0582 方案审阻断-1 同型禁再犯；注册表历史 run_id 仅 run_*/fake_ 两形态，前缀判据覆盖完备）。
2. **塌缩守卫**：常量 `SNAPSHOT_COLLAPSE_MIN_RATIO=0.5`（append-only 流合法再生只升不降；50% 把微型语料覆盖 0.8% 与局终增量 ≥99% 分两侧并留清洗余量）；覆写前 `_assert_no_source_collapse` exec 读将被覆写快照文件的 source_rows 作基线（非 import，防长跑进程缓存脱节），源行数低于基线 ×0.5 时 raise `SourceCorpusCollapse`（文案自含两侧行数账），现快照零落盘。告警走局终钩子既有 best-effort warning 通道（ADR-0344 纪律），ledger_hooks 零改动。

## 后果

- 锁：test_cw_delta_pool「pool_data_defense」段 7 锁（判据单一源/混入隔离+披露/假源拒绝零落盘/正常增量放行/塌缩拒绝+快照字节保留/auto 池同判据+披露/auto 池正常源放行），变异亲证双向（隔离判据致盲→恰 4 红（原 3+auto 池同判据锁）；塌缩守卫致盲→静默覆写复发 1 红）。
- 提交快照（460e6031，16391/2246 行账）持续受保护；塌缩守卫生效期间 live 源（144 行）任何再生被拒，局终钩子仅记 warning 不影响对局。
- 塌缩守卫按两流行数「总和」比较：单流截断（如 decisions 砍半，总和约 56%）可过闸，由 META `unlabeled_dropped`/桶贫困披露兜底显影；单流全灭先撞「池为空」拒绝——量级守卫的形状选择，非绕行通道。
- 语料连续性裁决：**快照即真值，不回灌**。live 目录只累积真实局（假/sim 局被隔离），待真实行数跨过塌缩阈值后再生自然恢复；届时锚重推按 ADR-0582 工序另批执行。
- 锚重推禁令：禁止把微型池统计值登记为语料真值（假游戏 n=2 均值≠真值；池锚批红证双向验证确认锁有牙）。

## 索引

- 实施：防线批交付（生成器+test_cw_delta_pool 两文件，零生产行为；批次标识不入持久索引）
- 事故实证：池锚批报告与编排者台账（T-126 note, 2026-09-08；批报告为易失工件,语义单一源在本 ADR 与台账）
- 同族：ADR-0577/0582（池数据防线先例）、ADR-0344（局终钩纪律）
