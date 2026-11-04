# 阵容结构统一（comp-structure-unification）

## 文档
- 设计总纲:[design.md](design.md)
- 详设:[details/faction-priority.md](details/faction-priority.md) —— 羁绊优先级结构
- 详设:[details/counter-tables.md](details/counter-tables.md) —— 克制表直写
- 详设:[details/transition-library.md](details/transition-library.md) —— 过渡阵容库与配方决策层退役
- 详设:[details/press-stockpile.md](details/press-stockpile.md) —— 富余买入并入压牌库与 P88 退役
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:**定稿**——七轮无前提对抗收敛（累计 105 点全部消化；第七轮零高危，其中 2 中 4 低随轮修复：混合断言测试拆分口径、冷启动退出判据换轴第八节点、README 陈旧行、路径/叙事措辞、cw_transition 注释清理面）。关键裁定全部归档：A/B 不做（实机观察验证）、涉及面存量黑话清理（方案 5）、过渡层生命周期挂钩终局锁定事件（判据换轴八节点）、过渡评分统一减分制（纯减分无排除特殊逻辑）、克制数据拆两张独立表、三型过渡条目
- 设计对抗:七轮完成收敛 · 报告=[attack.md](attack.md)～[attack7.md](attack7.md)；派单含实现者走查必查维度（用户裁定：试读由对抗覆盖）；定稿规则 = 有阻断须再攻确认（用户裁定），第七轮零高危故收敛成立
- 落地:5/5 done（3.1-3.4 + 固定末阶段共 5 节，明细见 landing.md）
- 正本更新:完成（T-5 r1 提交 6b81a16fe + 返工提交；12 条清单清零 + P65/P88 退役标注 + 注释清理 + 黑话终扫；遗留申报见 .debug/progress 报告 T-5-r1.md）
