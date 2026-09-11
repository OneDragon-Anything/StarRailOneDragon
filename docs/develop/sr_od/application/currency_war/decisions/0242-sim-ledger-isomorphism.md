# ADR-0242 sim 判读同构基建(账本/checks/快照池/CLI/seed 重放)

## Status

accepted(2026-08-24;用户定调「更多用模拟测试提前发现问题」;方法论 ADR-0012 后的实作)

## Context

实机暴露的策略行为病(局49 r1 清金、金滞留、伪档)在 sim 批次里每天发生,但 sim 只评终态分布、判读视图查不了 sim——「找不合理指纹」只能等实机(数十分钟/局)。两轮对抗审查(10+10 发现,含 blocker:Δ池 gitignored 静默回退让同 seed hp_ge_60 可翻转、快照 str 桶键全 miss 静默失效)定稿 ⓪-⑤ 设计。

## Considered Options

1. 只加异常断言不动 sim 本体:断言无逐轮数据可吃(过程不可观测是三根源之首)。
2. **判读同构:两流账本+checks+快照池+CLI(选)**:sim 局产出与生产遥测同构的 jsonl(decisions/outcomes/shop_snapshots 三流),判读 CLI `--sim-batch` 同一套视图查 sim 批次;实机学费回灌成 checks 断言。
3. 视图改走共同投影层(二轮#4 备选):改动面大;三流同 schema 由构造成立,零视图分叉更便宜。

## Decision

选 2,分四件落地(主仓 9364e193/ba7ce6f3/bb5f576a/2cd05b61,测试仓配对四提交):

- **⓪ Δ池快照化**:resolve_pool 三态(auto/snapshot/fallback/Path)+指纹=hash(池内容+桶宽+采样器版本);缺源 raise 不静默;主仓提交快照 `cw_delta_pool_data.py`(生成器 `tools/cw/gen_delta_pool_snapshot.py`,写目标白名单+源目录断言≠sim_runs);auto 口径与快照同(无标签 retrofix 行不入池)。
- **① 两流账本**:SimResult.ledger 每轮一行(轮内段聚合);收入分解/花销逐笔 reason(classify_buy 单一源,r368 门同源消费)/depth(收口 _deployable_depth)/core_count+target 同行/牌面波;write_batch_ledger 三流落盘 sim_runs/(目录守卫禁写生产 replay;滚动保留 20 批;每局 run_id 带 seed)。
- **② checks**:cw_sim_checks 纯函数(不 import cw_sim);batch 默认内嵌(checks_violations 挂结果);局49 指纹断言只对构造账本(sim 内冷启动门不可达)。
- **④⑤ CLI**:`cw_telemetry --sim-batch` 同视图查 sim;`cw_sim replay --seed N --pool snapshot [--expect-fingerprint]` 单局逐轮重放;economy 视图补卖牌回金(SellBench.income)。

## Consequences

- 判读手法(滞留/供给对照/异常标记)秒级扫百局 sim;checks 报 games 索引→seed 重放定位。
- 生产 actions 序列化自动携带 BuyCard.reason(dataclass 字段)——生产侧判读未来可直接用同标签。
- CI smoke 锁(测试仓)锁链路不锁分布:checks 全绿+指纹命中提交快照+同 seed 确定性。
- SimResult 消费方增量兼容(新字段默认值);test_cw_sim 裸调用显式 pool='fallback'(回退显式化)。
- ③(Δ池扩核心键)维持暂缓:账本先攒 core_count(带 target 上下文),v2 线id→comp 映射补齐后按线分桶重跑先验。
