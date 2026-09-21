# 2026-09-21-pool-kernel-promotion(池升格批)

> 承接:银狼升星记账批 §2.7(池派生升格 kernel 为效果批前置);用户机制定谳
> 2026-09-20(随机授予采样空间 = 剩余池对应费用档桶)。

## 文档
- 设计总纲:[design.md](design.md)
- 落地:[landing.md](landing.md)(未起草——定稿后拆阶段)

## 进度
- 迭代设计:定稿(四轮核一无前提攻击收敛:r1 major 2 + minor 6、r2 major 1 + minor 8、r3 major 0 + minor 3、r4 major 0 + minor 5,全量清偿,试读过)
- 设计对抗:四轮收敛 · 报告=[attack.md](attack.md) + [attack2.md](attack2.md) + [attack3.md](attack3.md) + [attack4.md](attack4.md)
- 落地:done(主仓 `6db7b1c3f` + 测试仓 `31099cfa`;独立审查通过 = [reviews/impl-review-r1.md](reviews/impl-review-r1.md) + 收口凭据 [reviews/accept-r1.md](reviews/accept-r1.md);L1 916 绿)
- 正本更新:无独立清单(本批正本面 = 代码内 docstring/头注,随落码交付)
- 遗留挂账:sim 域 changes/ 引用正本收敛(sim 域既有欠账,审查员 r1 观察②);装备池三处范畴统一(另批);估值族档传参七处(starup §2.6)
