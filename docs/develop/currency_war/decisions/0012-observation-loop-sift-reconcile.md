# 0012. 观测回路:deploy 后 SIFT 真实身份纠 tracking 漂移

- **Status**: accepted
- **Date**: 2026-08-09
- **原编号**: D-12

## Context
观测回路的断点根因:deploy op 是视觉拖拽(D-7/D-8/D-10),不调 `mutate_bench_deployed` → `session.tracked_bench_chars`/`tracked_deployed` 滞留(已上场的还在 bench、已卖的还在 deployed)→ 下轮 buy 用**漂移 tracking** 做集中度判断 → 错。`read_game_state` 的 deployed 也是 tracked+rebuild(假身份)。D-1/D-6/D-9 此前"集中有效"结论全基于漂移 tracking,不可信。

## Decision Drivers
- buy/部署决策依赖 `session.tracked_*`;tracking 漂 → 决策错
- deploy 是视觉拖拽、绕过 mutate,正是回路断点
- shop-open 时 SIFT 读 deployed 受 overlay 遮蔽 + 循环内多次调贵

## Considered Options
1. 在 `read_game_state` 加 SIFT(shop overlay 遮前排 + 循环内贵,否)
2. 详情面板 OCR 读 deployed 身份(慢,逐个点开,否)
3. deploy 后(shop 关、bench/deployed 全可见)SIFT 纠 tracking(选中)

## Decision
`deploy_bench` 加 `_reconcile_tracking`:deploy 完成后用 SIFT `read_bench_chars` + `read_deployed_chars` 读真实身份,重置 `tracked_bench_chars`/`tracked_deployed`(保留旧 tracking 的 star,按 char_id 匹配)。闭合观测回路 → 解锁核心锁②(端到端观测回路通)。

## Consequences
- 正向:下轮 buy/deploy 用准 tracking;D-1/D-6/D-9 的集中度结论可在此后重验。
- 负向:每轮 deploy 后多一次 SIFT(9 槽,可接受);star multiset 需防重复 char_id 碰撞。
- 边界:SIFT star 恒 1,身份准为主;shop-open 时不做(deploy 后 shop 关才做)。

## Links
- `· docs/develop/currency_war/strategy/04_state_reconciliation.md`(状态对账)
- 关联 D-NN:D-7/D-8/D-10(deploy 视觉拖拽)、D-1/D-6/D-9(漂移期结论作废,待重验)
