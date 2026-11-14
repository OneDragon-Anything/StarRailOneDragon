# 2026-11-13-trait-v47-rebuild

## 文档
- 设计总纲:[design.md](design.md)
- 详设:[details/trait-data-layer.md](details/trait-data-layer.md)（数据层结构与生成器）
- 详设:[details/consumer-migration.md](details/consumer-migration.md)（消费点迁移）
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:两轮对抗收口（第一轮 25 点已修订；第二轮复攻 7 点【阻断 1/应修 4/备忘 2】已修订——查表契约补高费档覆盖、members 可组队员口径+召唤特例登记、零消费接口删除、黑话与计数修正 · 报告=[attack.md](attack.md) §4-§5）
- 设计对抗:两轮收敛，已定稿（查表契约按用户裁定 2026-11-14 收敛为派生形态——消费方从注册表 source 字段派生映射，无需角色批交付符号）
- 落地:阶段 2/8 done(3.2 翻译与对拍闭环 gen_traits.py:查表契约派生形态落地——运行期派生映射+覆盖守卫 63⊇63;翻译零 fail-closed(同名多档合并/is_hide 过滤);成员对拍 29 键零 diff,例外清单首版空待人裁;cw_traits_data.py 全文渲染 dry-run 预览+import 烟测通过;凭据=.debug/temp/currency_war/gen_traits_report_v4.7.txt 与 cw_traits_data.py 预览;gen_factions.py 删除因并行在飞改动顺延;明细见 landing.md)
- 正本更新:未开始
