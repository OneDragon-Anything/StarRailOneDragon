# 2026-11-13-trait-v47-rebuild

## 文档
- 设计总纲:[design.md](design.md)
- 详设:[details/trait-data-layer.md](details/trait-data-layer.md)（数据层结构与生成器）
- 详设:[details/consumer-migration.md](details/consumer-migration.md)（消费点迁移）
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:两轮对抗收口（第一轮 25 点已修订；第二轮复攻 7 点【阻断 1/应修 4/备忘 2】已修订——查表契约补高费档覆盖、members 可组队员口径+召唤特例登记、零消费接口删除、黑话与计数修正 · 报告=[attack.md](attack.md) §4-§5）
- 设计对抗:两轮收敛，已定稿（查表契约按用户裁定 2026-11-14 收敛为派生形态——消费方从注册表 source 字段派生映射，无需角色批交付符号）
- 落地:阶段 1/8 done（3.1 聚合器核心 gen_traits.py:29 条中间产物 + 骨架/全覆盖对拍零 diff + wiki 交叉报告；明细见 landing.md）
- 正本更新:未开始
