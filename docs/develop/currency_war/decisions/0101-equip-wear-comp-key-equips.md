# 0101 — EquipAll 穿戴接 comp.key_equips 优先(替 naive wearable[0])

- Status: accepted
- 日期: 2026-08-12
- 相关: 根索引缺口 4(该接入未接入)/ ADR-0098 comp_viability / D-17 装备=最高杠杆 / `equip_fit`(cw_comps:472)/ `decide_supply`(cw_decisions:915,补给已用 key_equips)

## Context

`EquipAll`(全员装备 op)动作层 **naive**:穿戴时取 `wearable[0]`(`read_equips` 返回的**第一个**穿戴类),无 comp 优先、无目标角色选择(按前排空槽顺序穿)。

而 `equip_fit(comp, state)`(cw_comps:472,装备契合度评分)**已在 comp 评估层接入** —— `comp_score = ... + W_EQUIP * equip_fit`(`cw_comps:586`)+ `comp_viability`(`cw_performance:215`),选 comp 时考虑装备适配;`decide_supply`(cw_decisions:915)补给选装备也已按 `target_comp.key_equips` 契合(+10 碾压通用价值)。

**唯独穿戴动作层(EquipAll)没接 comp** —— 补给选了 comp 命脉装备,但穿戴时穿第一个(可能把命脉件穿给了非核心角色 / 或穿了非命脉件占槽)。这是根索引「该接入未接入」缺口之一,A8 装备是最高杠杆(D-17)。

## Decision Drivers

1. **comp 驱动原则**(`equip_fit` docstring 明示):「不设通用 equip_score,一切从 `target_comp.key_equips` 出发」—— 同件装备对不同 comp 价值不同(反重力皮靴对阿雅命脉,对反甲流一般),通用评分会错。
2. **A8 高杠杆**:装备强度直接决定能否赢第二位面 boss(deploy ~50% 板输第二位面,装备是提板强度的关键杠杆)。
3. **该接入未接入**:`equip_fit` 评分 + decide_supply 都 comp 驱动了,穿戴动作层是最后一块未接的拼图。

## Considered Options

### A. EquipAll 按 `target_comp.key_equips` 优先穿(选中)

穿戴候选 `wearable` 按 `target_comp.key_equips` 排序:命脉件在前,其余原序。`_prioritize_wearable(wearable, key_equips)` 纯函数(可单测),`EquipAll` 拿 `session.target_comp.key_equips` 调它。无 target / 无 key_equips → 原序(等价旧行为,reactive 不破)。

- ✅ comp 驱动(与 equip_fit / decide_supply 同源)
- ✅ 动作机制不变(D-78 drag 验穿已 live 过),只改「选哪件」
- ✅ 纯函数可单测,multiplicity 消费(阿雅 2 反重力皮靴都优先)
- ⚠️ 不改「穿给谁」(仍按前排空槽顺序)—— 角色级装备分配是更大改动,留后续(需 comp 角色定位数据)

### B. 通用 equip_score(每件装备独立价值评分)—— 否决

给每件装备一个通用价值分,穿戴按分排序。

- ❌ 违反 comp 驱动原则:同件对不同 comp 价值不同(反重力皮靴 阿雅=命脉 / 反甲流=一般),通用分会错配
- ❌ 与 `equip_fit` 设计哲学冲突(equip_fit 明确「不设通用 equip_score,从 comp.key_equips 出发」)

### C. 不改(穿 wearable[0])—— 否决

维持 naive。

- ❌ 该接入未接入缺口仍在
- ❌ A8 装备高杠杆未利用

## Decision

**选 A**。加 `_prioritize_wearable(wearable, key_equips)` 纯函数(`equip_all.py` module 级):

- `key_equips` 命中的件排前(按 `wearable` 出现顺序消费 `remaining`,非 key_equips 顺序),其余原序在后
- `key_equips` 含重复 → 按 multiplicity 消费(命中的重复件也优先,但不超额 —— 阿雅 2 反重力皮靴,wearable 有 2 都优先;key_equips 只 1 则只消费 1,第二个回原序)
- `key_equips=None / []` → 原序(等价旧行为)

`EquipAll.equip_all()` 拿 `self.ctx.cw_match.session.target_comp.key_equips`(同 deploy_bench 模式),调 `_prioritize_wearable` 排序 `wearable`,再取 `wearable[0]` 穿。日志加 `[key_equip优先]` / `[通用]` tag 便于 live 看是否 comp 驱动生效。

**不改动作机制**(drag 穿戴 + avatar-slot CV-diff 验穿 D-78 不变),只改选件。**不改角色级分配**(仍按前排空槽顺序穿,不按 comp 角色定位 —— 那是更大改动,留后续)。

## 验证

- 单测 `test_prioritize_wearable_comp_driven`(test_cw_equipment.py):无 target→原序 / 命中→优先 / multiplicity 消费 + 不超额。18 测试绿。
- live 验待游戏条件:备战 owned 有穿戴装备(补给出)+ 有 target_comp → `run_operation BattlePrepCycle` 看日志 `[cw-equip] drag <命脉件> ... [key_equip优先]`(非第一个件)。
