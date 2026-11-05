# comp-data-row-cleanup 迭代设计（总纲）

## 0. 元信息

- 迭代目标：COMP_LIBRARY 数据行级清理两件——① `flex_factions` 与 `faction_reqs` 档 ≥1 的 6 处同键双登记（迁移残留回声）删除 + 互斥建库校验（**已落地**）；② `need_star` 值 = 1 的 59 行"死行"删除 + 值域建库校验（**落地后撤销**——1★ 行是活数据：`unfinished_star_targets` 对未持有成员 `_held_max_star=0 < 1` 入未完成目标集，承载「首张即目标」停留刷牌语义；原「与缺省 get(name,1) 等价」的恒等论证只覆盖 priority 读法、漏了 levelup 遍历读法的未持有分支，被窄子集测试 `test_locked_frame_need_star_full_transcription` 的 `stay_target='藿藿'` 断言拦截——判例详见 attack.md A6 修正）。用户裁定来源 = 字段冗余排查会话收官轮（2026-11-05）。
- 状态：定稿（含撤销修正）。
- 文档清单：（无详设——单文档方案）。

## 1. 问题与动机

- 症状（两条，均可脚本复核）：
  1. **flex∩bonus 同键 6 处**：列车同行·反震×护盾、列车同行·直伤×减益、黄泉减益×击破、反甲白厄×护盾、万敌单C×战技点、DOT队×减益——`sub_tiers → faction_reqs 档 ≥1` 迁移时读点替换完成、flex 侧同键历史登记未清（与 shared_chars 双列回声同族的迁移残留）。复核判定式：`set(c.flex_factions) & set(c.bonus_faction_reqs)`。
  2. **need_star 值 = 1 死行 59/94（62%）**：消费端 `need_star_by_member.get(name, 1)` 缺省值即 1——值 = 1 的条目与「不登记该名字」行为完全一致；「辅助普适档 1★」的登记纪律批量产出了把隐含缺省显式化的噪声行。复核判定式：`v <= 1 for v in comp.need_star.values()`。
- 根因：①迁移遗留（键域互斥在 faction_reqs 建库校验②「同羁绊禁跨档」已内建，但跨 flex/faction_reqs 两字段的互斥从未校验）；②登记口径无值域下限（1 = 无约束语义未被「不登记」承载）。
- 解决到哪：数据行删除 + 两条建库校验 + 两处 docstring 口径声明。**字段保留**——flex 是「无档位目标的轮廓羁绊」（与 bonus「有档位目标的加分层」语义正交）、need_star 是升级停留门/优先级快照的活知识卡。
- 明确不解决：无外溢面（纯数据行删除，无行为、无知识损失——删掉的行在全部消费点产零）。

## 2. 方案

### 2.1 系统级变化

> ⚠️ 第 2/3（need_star 部分）/4（need_star 部分）条已随 A6 修正**撤销**——1★ 行是活数据；下文保留原稿供判例考古，落地形态以 README/attack.md 为准。

1. **flex 侧重叠键删除（6 行）**：六套的 `flex_factions` 列表各删 1 个与档 ≥1 重叠的键。
2. **need_star 值 = 1 行删除（59 行）**：21 套的 need_star 字典删值 ≤ 1 条目；条目注释中「辅助普适档 1★」措辞随之收窄为「辅助不登记」。
3. **建库校验两条**（`Comp.__post_init__`，import 即炸）：
   - flex ∩ bonus_faction_reqs = ∅（与 faction_reqs 校验②「同羁绊禁跨档」对齐，本条管跨字段面）；
   - need_star 值 ≥ 2（1 = 无约束 = 不登记，缺省语义）。
4. **docstring 口径**：`flex_factions` 注「与档 ≥1 键互斥（建库校验）」；`need_star` 注「值 ≥ 2 才登记，1★ = 无升星要求 = 不登记（消费端缺省 1）」。
5. 正本：10 号稿 :203 存留表 flex/need_star 行补校验说明（shared_chars 已有同款括号注）；comp-definition skill 如有「辅助 1★ 登记」措辞同步。

### 2.2 行为变化申报

**零行为**。逐消费点验证（本设计前实际读码确认）：

| 消费点 | 形态 | 恒等依据 |
|---|---|---|
| invest_channels `_faction_hit_bonus:175-177` | bonus/flex 同一 or 分支同分值（`INVEST_SOFT if tier ≥ INVEST_STRONG else 0`） | 删 flex 侧键 → bonus 侧命中，返回值不变 |
| `all_factions` property | 集合并 | 重叠键在 bonus 侧保留 |
| deploy_search L2 / `_line_hoard` 采购面 | 只读 `bonus_faction_reqs`（flex 不进） | 不涉及 |
| priority 装配（锁定帧 :298 全量照录 / 未锁帧 :324-325 max 合并 `.get(n,1)`） | 缺省 1 形态 | 删 1 值行 → 表内少名 → 消费端 `get(name,1)` 返回 1 = 原值 |
| priority 消费（:565/:641-656 档 2/3/4 判定） | 纯数值比较（`need ≥ 2`/`need ≤ 1`/`max(need,2)`），**无「∈ 表」成员资格判定** | 数值同值 |
| levelup :198 停留门 | 遍历条目，need=1 时 star ≥ 1 恒真不触发 | 删行后不进循环，同样不触发 |
| 过渡组合生成器 | need_star 源 = TRANSITION_BONDS（独立 tuple），终局清理不涉及 | 不变 |
| tools/ 域 | grep 零命中 | 不涉及 |

测试面：test_priority :527 断言「表 = 字段全量」对照字段现状（删行后字段 35 行 = 表 35 行）恒过；test_faction_migration_identity 锁 `_line_hoard`（factions = core ∪ bonus，flex 不进）不涉及。

### 2.3 知识归宿登记

删掉的 59 行「辅助 1★」不含知识（= 缺省语义的显式化）；6 个 flex 重叠键知识已在档 ≥1 承载（更强形态：有档位目标）。

### 2.4 接口契约

字段签名不变、property 不变；`flex_factions`/`need_star` 的值域收窄由建库校验钉住。grep 验收：`v <= 1` 形态在 COMP_LIBRARY 数据零残留（校验兜底）。
