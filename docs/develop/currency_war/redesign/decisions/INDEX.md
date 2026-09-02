# CW redesign 决策记录索引(dd-NNN)

| 编号 | 标题 | Status | 日期 |
|------|------|--------|------|
| [dd-001](dd-001-ab-baseline-gate.md) | DD-001:旧决策包删除时序——A/B 过线前不得物理删除(批 1 拆 1a/1b 两段) | accepted | |
| [dd-002](dd-002-rotation-doubling-semantics.md) | DD-002:轮岗突变语义勘误——选择后每备战阶段 100% 生效;20% 是观测频率不是机制概率 | accepted | |
| [dd-003](dd-003-cross-plane-node-count-defect.md) | DD-003:跨位面剩余节点数实现缺陷登记——`total_remaining_nodes` 对全部位面写死 9,L 换轨前必修 | accepted | |
| [dd-004](dd-004-encounter-refresh-execution-wiring.md) | DD-004:遭遇分支刷新执行链接线——决策建议字段长期无消费端,接线并登记触发源缺位 | accepted | |
| [dd-005](dd-005-buy-landing-real-empty-slot-semantics.md) | DD-005:买牌期望态落点判据对齐「真实空槽优先」——快照过期不再误停线 | accepted | |
| [dd-006](dd-006-settle-read-chain-boss-win-form.md) | DD-006:结算读点链 boss 胜局形态修复——失败页分支抢走页1 + 填充率页2 假值 + killed 兜底误判 | accepted | |
| [dd-007](dd-007-plane-fallback-endpoint-discipline.md) | DD-007:P2 回退先验端点纪律对称化——未揭晓位面回退统一取结构上端(9) | superseded(见文末 SUPERSEDED 节) | |
| [dd-008](dd-008-cost-tier-star-goal-heuristic-retired.md) | DD-008:费用档星目标启发式废弃——星目标决策权回归成型档显式要求 | accepted | |
| [dd-009](dd-009-legacy-mechanism-eviction.md) | DD-009:旧方案零引用机制整批清退——约 20 族默认关开关+影子比对残留删除 | accepted | 2026-09-02 |
| [dd-010](dd-010-equip-grid-two-state-fill-order-purify.md) | DD-010:装备区识别重构——两态位移+填充序剪枝+画面守卫外移(识别器纯化) | accepted | 2026-09-02 |
| [dd-011](dd-011-op-anim-wait-gate-retirement.md) | DD-011:操作完成自等动画规范——稳定门(gate)进入退役 | accepted | 2026-09-02 |
