# 2026-10-10-env-conditional-grants

## 文档
- 设计总纲:[design.md](design.md)
- 详设:[details/env-conditional-grant.md](details/env-conditional-grant.md) —— 条件达成发放机制(登记表/触发检查/随机态发放/done 标记)+ 宝钻获得回调
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:定稿
- 设计对抗:收敛(三轮:有条件通过→有条件通过→定点复核通过;报告=[attack.md](attack.md) 存末轮)
- 落地:4/4 done(T-1..T-4,验收 reviews/T-1..T-4-r1.md)
- 正本更新:清零(506a5ab45)

**终态**:迭代收官。遗留项 = 补给带钻选项的钻类型未建模(sim 聚合计数,其 cap 联动随钻类型建模另批,见 design §1「明确不解决」)。
