# equip-taboos-retirement 进度

> 迭代目录 = `docs/develop/sr_od/application/currency_war/changes/2026-11-05-equip-taboos-retirement/`。
> 判据单一源 = design.md + landing.md；本文件只记状态与指针。

## 阶段

- [x] 阶段 1 设计：design.md 定稿（2026-11-05；用户裁定来源 = 字段冗余排查会话）
- [x] 阶段 2 对抗审查：轮 0 预演自审 3 点 + 轮 1 外部 subagent 报告 7 点（阻断 1/应修 3/可选 3）合并处置——attack.md
- [x] 阶段 3 落地：字段+唯一消费点+3 行数据删除；grep 清零（src + sr-od-test + tools/cw/proofs，墓碑注记豁免）；万敌囤货装备集退役前后恒等（4 件关键装备抽查通过）；ruff 通过；L1 全绿 3743 passed（与基线逐位一致——零行为实证，含 test_faction_migration_identity 的万敌囤货集逐位断言）
- [x] 阶段 4 正本更新：P42 文首横幅 + :124/:256/:334 行内注记 + VALIDATION 注记、10 号稿两处、01/08/13 三篇 E11/结论行、comp-definition skill 两处
- [x] 返工批（轮 1 报告送达后）：p42_check.py 三处消费修复 + 验收口径扩 tools + 外溢面现行通道登记 + §2.2 证据补强

## 遗留登记

- 10 号稿 §5 存留表存在 `family`/`substitute_plan` 存量失真（两字段早已不在 Comp——历史退役后存留表未同步；轮 0 发现，非本批引入）。归正本维护批处理，本批未顺手扩面。
- p42_check.py :236 存量红（断言 20 套 vs 现 21 套——姬子 A/B 拆分时未同步，math_proofs.md 已登记待修）。非本批引入（退役前即红），归 P42 自检脚本维护批。
