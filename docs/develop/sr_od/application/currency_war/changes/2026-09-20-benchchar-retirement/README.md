# BenchChar 退役迭代

## 文档
- 设计总纲:[design.md](design.md)（单文档方案）
- 落地:[landing.md](landing.md)（阶段拆分与验收，账本唯一源）
- 进度账本 = `.debug/progress/2026-09-20-benchchar-retirement/dag.jsonl`（P0..P8）

## 进度
- 迭代设计:定稿
- 设计对抗:三轮收敛——首轮 [attack.md](attack.md)（blocker 1/major 5/minor 4，已收编）；第二轮 [attack2.md](attack2.md)（blocker 2/major 5/minor 2，已收编；并裁落位决策权归策略层）；第三轮 [attack3.md](attack3.md)（收敛确认：前两轮 19 条闭合核对通过；新发现 blocker 1/major 2/minor 4 = N1-N7，已收编）
- 落地:9/9 done（P0-P8 全部验收关账；L1 829 passed / L3 全仓 1316 passed；明细 = .debug/progress/2026-09-20-benchchar-retirement/reports|reviews/）
- 正本更新:清零（P8 完成——landing 正本更新清单 + 累计遗留（旧 kernel 单一源指针/to_slot 契约/帧退役口径/死旋钮字段）全部闭环，正本区残响 grep 归零）
