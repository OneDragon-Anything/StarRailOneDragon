# 旧账卫生与运维收编（2026-09-11-legacy-hygiene-ops）

## 文档
- 设计总纲:[design.md](design.md)（§3 = 账本依赖边清单 + 账本动作申报）
- 详设:[details/execution-seam-projection.md](details/execution-seam-projection.md)（T-16/T-17 执行缝账务与投影播种；T-17 三层方案已由旧账 T-308 落码批入库 bd27989d4，本迭代辖残余收尾）
- 落盘正本:[details/sources/](details/sources/README.md)（T-280/T-322 交付报告防 .debug/temp 易失的落盘副本）
- 详设:[details/strategy-qualification.md](details/strategy-qualification.md)（T-18/T-20 腾席资格面与代理收窄）
- 详设:[details/sim-baseline.md](details/sim-baseline.md)（T-21/T-22/T-23 sim 基线校准与联动）
- 详设:[details/free-refresh-onboarding.md](details/free-refresh-onboarding.md)（T-13 免费刷新建档接入）
- 详设:[details/docs-hygiene.md](details/docs-hygiene.md)（T-24/T-25 悬空引用清理与文档树迁移）
- 详设:[details/live-verification-and-rulings.md](details/live-verification-and-rulings.md)（T-14/T-26/T-27 实机验证/亲核/候裁）
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:定稿（待复验）
- 设计对抗:完成 · 13 项发现（高 3/中 6/低 4）逐条裁决落盘，记档=[attack.md](attack.md) §四
- 落地:阶段 0/14 done（明细见 landing.md；阶段↔账本任务追认式映射：3.1=T-19 … 3.14=T-27，末阶段=正本更新；依赖边=design.md §3，账本落账动作申报待编排者执行）
- 正本更新:未开始（末阶段卡申报见 design.md §3）
