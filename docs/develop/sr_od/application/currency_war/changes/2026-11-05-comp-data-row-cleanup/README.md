# comp-data-row-cleanup 进度

> 迭代目录 = `docs/develop/sr_od/application/currency_war/changes/2026-11-05-comp-data-row-cleanup/`。
> 判据单一源 = design.md；本文件只记状态与指针。

## 阶段

- [x] 阶段 1 设计：design.md 定稿（2026-11-05；含逐消费点零行为验证表——**need_star 部分的验证后被证错，见 A6**）
- [x] 阶段 2 对抗审查：外部 subagent 通道再次失联（finished 后报告未送达），编排者五向自审（attack.md）
- [x] 阶段 3 落地：flex∩bonus 6 处删除 + 互斥建库校验（**保留**）；need_star 59 行清理落地后**撤销**（A6 反转：1★ 行是活数据——`unfinished_star_targets` 未持有 0<1 入未完成目标集「首张即目标」；窄子集测试 `stay_target='藿藿'` 断言拦截；数据/校验/docstring/正本全部回滚，字段补防再犯注记）
- [x] 阶段 4 正本：10 号稿 flex 行补校验说明（need_star 撤销不涉及）；12 号稿 need_star 行补「1★ 行是活数据」防再犯措辞

## 遗留登记

- 全量 L1 基线红（并行批 sim 后端装配冲突）——本迭代验证口径 = 受影响域窄子集全绿；全量待并行批提交后补跑。
- need_star 的「59 行死行」判定撤销后，**不再存在待清的 need_star 数据行**（原判定错误）；flex∩bonus 互斥校验已在位，同族残留防线齐。
