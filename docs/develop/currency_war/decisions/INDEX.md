# 货币战争 · 决策索引(ADR)

> 原 `docs/game/currency_war/decisions.md`(D-NN append-only,92 条)已转为 ADR(一决策一文件)。
> **废弃条目(bug 修 / 诊断叙事 / 一次性验证 / 被 later D-NN 取代 / 数据进代码 / 过程记录 / 调参实验)未转入** —— git 可查:`git show HEAD:docs/game/currency_war/decisions.md`。
> 文件名 `00NN-<slug>.md`,NN = 原 D-NN 号(保留可追溯,代码/文档里的 D-NN 引用据此映射)。
> D-15/D-16 自主推进期已删(不可信);D-77 源文件缺(引用存在,条目未写)。

| 编号 | 标题 | Status | 日期 | 一句话 |
|------|------|--------|------|--------|
| [0007](0007-deploy-deterministic-cv-verify.md) | deploy 确定性部署(CV 占用→拖空槽→CV 验源空) | accepted | 2026-08-09 | 替 trial-and-error,CV 确定性部署只拖空槽 + 验源槽空 |
| [0012](0012-observation-loop-sift-reconcile.md) | 观测回路:deploy 后 SIFT 纠 tracking 漂移 | accepted | 2026-08-09 | deploy 后 SIFT 真实身份重置 tracking,闭合观测回路(解锁核心锁②) |
| [0014](0014-economy-leveling-remove-board-strong-gate.md) | 经济 leveling:`_saving_for_level` 去 `_board_strong` 门 | accepted | 2026-08-09 | 弱板也攒级(破 chicken-egg),leveling 修对 |
| [0017](0017-research-evidence-base.md) | 货币战争机制研究证据基 | accepted | 2026-08-09 | 多源交叉 + 证据等级,经济/装备/A8 阵容权威地基 |
| [0019](0019-max-units-dynamic-back-row.md) | 团队规模上限 = level + 财富宝钻/诅咒;后排非固定 6 | accepted | 2026-08-09 | cap 动态(宝钻+1/诅咒-1),后排须运行时实测 |
| [0021](0021-phase-skeleton-faction-agnostic.md) | 阶段节奏骨架 = 阵容无关骨架 × 阵容参数 | accepted | 2026-08-09 | 不为每阵容写流程,统一骨架 + level_plan 接缝参数化 |
| [0027](0027-equip-owned-sift-template-detection.md) | 装备 owned icon 检测用 cw_equip SIFT(推翻 VLM 球体误判) | accepted | 2026-08-10 | owned icon 用 SIFT 模板库检测,非亮度/VLM;小 icon 必裁切放大 |
| [0044](0044-equip-verify-avatar-slot-cv-diff.md) | equip_all 验穿用 avatar-slot CV-diff(替 count-verify) | accepted | 2026-08-10 | drag 前后对比 avatar 下方 icon 区,robust 合成/reflow/漏检 |
| [0049](0049-below-avatar-icon-fixed-32px.md) | below-avatar 装备 icon 固定 ~32px(98px 模板 scale 0.33) | accepted | 2026-08-10 | icon 不随装备数变(纠正 mini-template/分辨率墙误判) |
| [0055](0055-shop-cards-sift-vlm-locate.md) | 商店牌识别 OCR→SIFT + 肖像区 VLM 定位 | accepted | 2026-08-10 | 开拓者自定义名破 OCR,改 SIFT;VLM 定位可信别猜坐标 |
| [0081](0081-static-data-auto-write-guard.md) | 静态游戏数据 auto-write 守卫:garbage 拒 + existing 不覆盖 | accepted | 2026-08-11 | 防 OCR 污染写回 ground truth(词缀/装备效果类静态数据) |
| [0091](0091-refresh-prob-live-ocr-authoritative.md) | 商店刷新概率表 REFRESH_PROB 实机 OCR 落地 | accepted | 2026-08-11 | 弹窗表权威(非底部条/placeholder),基础表 + 效果修正待 A4.7 |
| [0092](0092-acquirability-theoretical-not-observed.md) | select_comp 可得性用理论概率非观察 | accepted | 2026-08-11 | 刷新独立→观察无预测力,改 min(refresh_prob) 理论法 |
| [0094](0094-strategy-merge-single-source.md) | 策略三轴重设计与 14 重复 → 合并入 14 + 删 15 | accepted | 2026-08-11 | 单一源(防双源漂移),重设计前先 grep 现有文档 |
| [0095](0095-strategy-design-round1-av-correction.md) | 策略方案定型轮 1(限时 AV / 掉血归因 / commit 渐进 / COMP 扩充) | accepted | 2026-08-11 | review HIGH + 用户玩法修正折进设计;限时=行动值 AV |
| [0096](0096-optionality-vs-commit-reconciliation.md) | optionality/α(t) 与 commit 不矛盾(管不同决策:eval vs pivot) | accepted | 2026-08-11 | optionality 限定通用角色(≥2 comp);α 在 eval、commit 在 pivot,正交 |
| [0097](0097-strategy-impl-wiring-nodeplan-transition-streak.md) | 策略实现接线轮(node_plan / evaluate α-blend 接法 / transition_tempo / streak 杠杆 / A4.3 牌池) | accepted | 2026-08-11 | 14 §2 node_plan 落地 + 0096 α-blend 接 evaluate + round-4 过渡羁绊 + 结算 streak magnitude 进 economy + 0091 表采 D 牌 |
| [0098](0098-comp-viability-star-dimension.md) | comp_viability 加 star 维度(star_achievement;review HIGH-1) | accepted | 2026-08-11 | 核心角色 bot 跟踪 star 归一化进先验(0.40/0.25/0.20/0.15);限时 AV 星级=输出;用 bot 跟踪 star 非 read_star 旁路 |
| [0099](0099-deploy-position-pref.md) | deploy 按角色前后台属性选排(替 0007「前排优先」;5.1.6) | accepted | 2026-08-12 | 角色 position_pref 选排(前→前/后→后),对应排满 fallback;修放错排无效(live 观察 2) |
