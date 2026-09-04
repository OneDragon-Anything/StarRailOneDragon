# 0134 策略选卡 comp 匹配分(strategy_bindings;星徽套组成型加速)

> **【版本界碑（2026-09-04 存量 review 恢复件）】**本件在 3311c453 存量 review 删除后因活引用恢复（strategy-docs 13_pick_family.md §3 与 `cw_investments.strategy_bindings`/`cw_comps.py` 代码注释仍引 ADR-0134）；恢复后亲验对象仍活（strategy_bindings 函数与 comp 匹分消费链在 kernel 现行），正常在档。对象若后续属已亡栈则按界碑读。

## Status

accepted(2026-08-15;用户问「哪些策略/环境让某阵容特别厉害」—— 绑定分析发现选卡断链)

## Context

绑定扫描(315 策略 + 84 环境):**84 条策略阵容特定**(棱彩星徽套组 = 阵营星徽+核心角色+核心装备三件套,全阵营各一张;金品质阵营质变类 如有神助/燃起来了/装备党/量子力学;互升双子 双龙会/白衣伙伴);环境侧 47 条(概念股定向刷新率/契约送成套角色)。decide_event 此前**完全不看 target_comp** —— 拿到「追击星徽套组→飞霄」时若在玩列车同行,只按品质分乱选。

## Considered Options

- 绑定数据:手填 84 条 faction/char 字段 vs **派生**(strategy_bindings 从名字+效果文本 ∩ FACTIONS/CHARACTERS 注册表键)→ 派生(零维护,新策略自动覆盖;误提取方向安全:空绑定 → 0 分回落先验)。
- 匹配分档:单命中(阵营或角色)= 65(不压白名单 T0 90)vs **双命中(阵营+角色都在 target)= 110 压倒一切** —— 套组语义就是「该 comp 的三件套」,对齐即成型加速,应压倒通用经济 T0;不对齐 = 裸品质分。

## Decision

1. cw_investments.strategy_bindings(strategy) → (factions, chars) frozenset(注册表键文本匹配)。
2. decide_event 加 target_comp 参数(默认 None 向后兼容):绑定 ∩ target.factions/core_chars,每命中 +45 + 基础 20(单命中 65 / 双命中 110);reason 带 comp-hit×N 可观测。
3. default_strategy.decide_invest:strategy kind 传 session.target_comp;env kind 不传(环境定向走 select_comp env_fit,选环境时 comp 未定)。

验证:strategy_bindings 抽取 + comp 匹配 3 断言(双命中压 T0 / 不对齐回落 / 无 target 行为不变);CW 全套 390 passed。
