# DD-022 · decisions.jsonl 期望态标记(expected_paths 字段)

- 状态:accepted
- 日期:2026-09-03
- 关联:W971 `EXPECTED_STATE.md`(FINAL v3.1)/ DD-019(期望态 infra 落地)/ DD-014(黑板决策接口);02-state §4.3

## 背景与问题

期望态 infra(DD-019)落地后,`decisions.jsonl` 决策行不记录「决策时点哪些
数据是期望态推进值」——复盘归因断链:决策错无法分型「基于错误的期望推进」
还是「实读错」。

## 决策

1. **字段**:`DecisionTrace.expected_paths: list[dict] | None = None`——决策
   时点 session.expected_state 未确认条目摘要 `[{path, value, produced_by,
   at_round, kind}]`;kind 供判读按五分类预分型(语义见
   cw_expected_state.reconcile_expected)。
2. **接出点 = recorder 统一 session 自取**(w603 汇点先例,单一接出覆盖全部
   决策面:备战步进行/买牌行/补给合成行/sim 行),不在逐调用点传参——防
   「漏一面=该面动作全部漏登记」的 F8 同型风险。
3. **读端三态**:旧行无键 = 迁移前数据(不修复);新行 `[]` = 无挂起期望;
   新行非空 = 决策基于含期望推进值的画面。可选末尾追加字段,旧 schema 不破坏。
4. **value 非标量**(BuyExpect 载体等)str 化防序列化炸;标量(合成链 star
   推进值)保真——期望态快照摘要单一源 = recorder.snapshot_expected_paths,
   sim ledger 行同构共用。
5. **判读视图**:query_rounds 行尾 `exp=N(produced_by:path)` 可选展示(非空
   才显示),旧数据/无挂起不显示,不破坏既有判读。
6. **match_archive 聚合(expected_diff_stats)= 二期**,本批不做(挂账)。

## Considered Options

- 快照点:**decide 入口随载荷传** 会侵入决策核且漏 sim 面;**recorder 汇点
  session 自取(选定)** = 零决策侵入、全决策面一次覆盖。取值时点与生产
  record 调用时点一致(decide 之后、动作执行前)。
- value 序列化:深拷贝 JSON 化会拉大行体(BuyExpect 全槽快照);**str 化
  摘要(选定)** 保行体紧凑,精确对账仍走 expected_reconcile.jsonl 专项通道。

## 后果

- 复盘归因可直接读 decisions 行分型期望态污染面;sim 行恒 [](sim 引擎未接
  期望态推进,与生产同构缺省)。
- 已知边界:条目 value 为载体对象时判读只见 str 摘要——逐字段对账归
  expected_reconcile.jsonl(职责分立,不双写)。
