# 2026-10-10-ore-reward-attach

## 文档
- 设计总纲:[design.md](design.md)
- 详设:[details/ore-reward-channel.md](details/ore-reward-channel.md) —— 声明注册表、奖励生成函数、GameState 附着域与挂接入口
- 详设:[details/ore-click-consume.md](details/ore-click-consume.md) —— 点击上报兑现改造、策略禁读契约、测试迁移
- 详设:[details/ore-sim-plane-start.md](details/ore-sim-plane-start.md) —— sim 位面开局声明矿、直发金退役、接线与确定性
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:定稿
- 设计对抗:收敛(六轮;报告=[attack.md](attack.md) 存末轮)
- 落地:5/5 done(T-1..T-5,验收 reviews/T-1..T-5-r1.md)
- 正本更新:清零(2c55849ab)

**终态**:迭代收官。遗留项 = 呈现面/色档/自动开启未实采,披露键 `ORE_PLANE_START_PENDING` 在册,实机首遇校。
