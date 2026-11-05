# equip-taboos-retirement 进度

> 迭代目录 = `docs/develop/sr_od/application/currency_war/changes/2026-11-05-equip-taboos-retirement/`。
> 判据单一源 = design.md + landing.md；本文件只记状态与指针。

## 阶段

- [x] 阶段 1 设计：design.md 定稿（2026-11-05；用户裁定来源 = 字段冗余排查会话）
- [x] 阶段 2 对抗审查：3 攻击点全数处置（2 修 1 登记；外部 subagent 通道未回传，编排者按任务书六向自完成——attack.md）
- [x] 阶段 3 落地：字段+唯一消费点+3 行数据删除；grep 清零（src 生产代码零命中，cw_comps 墓碑注记豁免）；万敌囤货装备集退役前后恒等（4 件关键装备抽查通过）；ruff 通过；L1 全绿 3743 passed（与基线逐位一致——零行为实证）
- [x] 阶段 4 正本更新：P42 文首横幅 + VALIDATION 注记、10 号稿两处、01/08/13 三篇 E11/结论行、comp-definition skill 两处

## 遗留登记

- 10 号稿 §5 存留表存在 `family`/`substitute_plan` 存量失真（两字段早已不在 Comp——历史退役后存留表未同步；对抗轮 A3 发现，非本批引入）。归正本维护批处理，本批未顺手扩面。
