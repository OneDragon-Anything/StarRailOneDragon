# comp-readout-unification

阵容读口统一：数据字段层与派生读口层分家立法 + 四批收敛（成员集 / carry 锚含分配器键 / 装备投影 / 数据卫生）。

## 文档

- 设计总纲：[design.md](design.md)
- 详设：[details/members-readout.md](details/members-readout.md)（批 A：终局成员集读口）
- 详设：[details/carry-anchor.md](details/carry-anchor.md)（批 B：carry 单名锚统一）
- 详设：[details/equip-projection.md](details/equip-projection.md)（批 C：装备投影化）
- 详设：[details/roster-hygiene.md](details/roster-hygiene.md)（批 D：双列清理与语义诚实化）
- 落地：[landing.md](landing.md)
- 对抗报告：[attack.md](attack.md)

## 进度

- 迭代设计：**定稿**（两轮对抗收敛：首轮三核+对照、复审无前提；必改项全部落文）
- 设计对抗：收敛 · 报告=[attack.md](attack.md) / [attack2.md](attack2.md)
- 落地：阶段 4/4 done（含批 C2/C3 追加段；明细见 landing.md 与 commit 链 88ffb2161/80969ddc6/543325f05/b1751631b/519e19ea7/c8ecef224/2cdcc8447）
- 正本更新：done（清单清零；k_members 行核销零改动、p42 引用修正核销已完成）
