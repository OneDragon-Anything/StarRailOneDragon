# 0021. 阶段节奏骨架 = 阵容无关骨架 × 阵容参数

- **Status**: accepted
- **Date**: 2026-08-09
- **原编号**: D-21

## Context
用户要"总结每阵容每阶段做什么"灵活支持所有 T1。工程化解法 = 不为每阵容写流程,而是骨架统一 + 参数化。写进 `strategy/14_phase_skeleton.md`。

## Decision Drivers
- 每阵容硬编码流程不灵活(新增阵容要写流程)
- 纯 eval 驱动无阶段骨架 → 缺节奏指导(何时升/D/all-in,A8 节奏关键)
- 等级曲线是通用节奏地基(bwiki 完整刷新概率表 Lv1-10)

## Considered Options
1. 每阵容硬编码一套阶段流程(不灵活)
2. 纯 eval 驱动无阶段骨架(缺节奏指导)
3. 骨架 × 参数:统一骨架 + `level_plan` 接缝填阵容参数(选中)

## Decision
策略骨架 = **阵容无关的通用节奏(一套)× 阵容参数(每 comp 填 `level_plan`/`factions`/`core_chars`/`key_equips`)**。核心:等级曲线驱动(+ bwiki 完整刷新概率表作 `level_plan` 硬地基)+ 节点×等级×动作骨架 + 经济线 + 骨架/参数分离(`level_plan` 接缝)。

## Consequences
- 正向:灵活支持所有 T1,新增阵容只填参数;节奏有指导。
- 负向:不改核心策略代码(核心锁①未过);`level_plan` 填 comp 是①过后实现。
- 边界:升级费用🔴待图鉴;V4.4 评级🟢(推翻 V3.7 阿雅降 B)。

## Links
- `· docs/develop/currency_war/strategy/14_phase_skeleton.md`
- 关联 D-NN:D-91(刷新概率表实机落地)、D-94(14 升级合并 15)、D-95(方案定型)
