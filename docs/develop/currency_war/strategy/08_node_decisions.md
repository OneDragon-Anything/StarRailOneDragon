# 08 节点决策:遭遇 / 补给 / 巨星(分,完整性-2/3/5 补)

> 总见 [README](README.md)。review r1(方案)发现:遭遇难度选择、巨星强化、补给出钻 三块节点决策 naive 或缺失。这些是 A8 高胜率的关键节点决策(非买/deploy/升/刷新的核心循环,但每局必遇)。

## 决策接线状态(2026-08-07 全面自检,用户指令「所有决策操作都要接入策略」)

> 对照本节 + 01/05,逐决策点核查「handler 是否调 decide_*」。详 `.debug/temp/currency_war/decision_wiring_audit.md`。
> 模式:handler 应 **read 选项 → 调 `strategy.decide_*` → 点选中项**,非硬编码默认。

| 决策点 | 策略函数 | reader | handler 接入 | 状态 |
|---|---|---|---|---|
| 买牌 | `plan` ✅ | `read_shop_cards` ✅ | BuyShopCards ✅ | ✅ 接入(D-90 修 refresh) |
| 投资环境/策略 | `decide_invest`→`decide_event` ✅ | OCR 卡名 ✅ | HandleInvest* ✅ | ✅ 接入 |
| **遭遇** | `decide_encounter` ✅ | `read_encounter_options` ✅(D-91) | HandleEncounter ✅(D-91) | ✅ **接入**(D-91) |
| 补给 | `decide_supply` ✅ | `read_supply_options` ❌缺 | RunSupplyNode ❌(默认中牌) | ❌ 待接 |
| 巨星 | `select_megastar` ✅ | `read_megastar_options` ✅(D-95) | RunMegastarNode ✅(D-95 选+D-96 两步) | ✅ **接入**(D-95/D-96) |
| 伙伴 | (PartnerOption,fn 待写) | 候选名 OCR ❌缺 | HandleSelectPartner ❌(取最左) | ❌ 待接 |
| 部署 | plan 的 `DeployMove`(被 shop.py 跳过) | 备战席身份 ❌(SIFT 失败 D-84) | DeployBench ❌(naive 填位) | ❌ blocked by 身份 |

**接入 4 / 未接 4**(原未接 5,遭遇 D-91 接入)。未接的补给/巨星/伙伴:decide_* 就绪,缺 reader(需 live 到画面建)。部署 blocked by 角色身份(半身立绘 SIFT 不可行)。

## 遭遇节点(decide_encounter,完整性-3,high)

**问题**:research §10.2「A8 遭遇常比 boss 凶;**可刷新 1 次**;阵容未成型选最低难度 + 刷新避开**急速制冷/正当防卫**(最难)」。当前 battle_loop naive「选左遭遇」,decide_event(白名单子串)**无法表达难度选择**(遭遇选项是难度档,非白名单项)。

**方案**:
```
decide_encounter(options, state, target_comp, config) → (idx, refresh?)
- options = 每个遭遇分支的(难度档 + 词缀 + 奖励),OCR 读(read_encounter_options,需游戏)。
- 阵容未成型(deployed_count 低 / target_comp 进度低)→ 选最低难度。
- **词缀好坏按当前 comp 判(2026-08-03,接 debuff=buff 洞察)**:用 `mechanics_fit(target_comp, 该分支词缀)`
  (详 10 MECHANIC_COUNTERS/SYNERGIES)——
  - 词缀**克** target_comp(如禁速 vs 速度依赖)+ 无对策(能量饮料/绝对热量)→ refresh 避开 / 选低难度。
  - 词缀**利** target_comp(如正当防卫 vs 燃血万敌)→ **不怕,甚至挑高难度**(debuff 对它是 buff)。
  - 中性 → 按成型度+奖励正常选。
- 有对策装备(克类词缀的对策)→ 可挑高难度拿奖励(A8 高奖励)。
- 刷新已用 → 选最低难度。
```
**数据**:遭遇词缀表(急速制冷/正当防卫/同步行动/决战在即/... research §10.2)+ 对策装备映射(正当防卫→能量饮料/绝对热量)。**需游戏** OCR。

> **状态(2026-08-04,D-19)**:`decide_encounter` 纯逻辑骨架**已实现 + 4 测试绿**(`cw_decisions.py`):未成型→低难度 / 全分支克 comp→刷新 / 成型+利 comp(debuff=buff)→高难度。`EncounterOption`(idx/难度/词缀/奖励)+ `EncounterPick`(idx/refresh/reason)。**handler 接线待阶段 5**(`read_encounter_options` OCR + `handle_encounter` 改调,替代 naive 选左)。

## 巨星强化(select_megastar,完整性-2,high)

**详 [03 阵容规划](03_comp_planning.md#巨星选择)**:`select_megastar(state, target_comp) → char`。盛会之星羁绊核心决策(花火/星期日/知更鸟/黑天鹅 各给不同全队 buff)。target_comp.core_chars 含盛会之星 → 绑该角色;否则按 buff 契合。battle_loop「确认选择」分支改调此函数。

## 补给节点(decide_supply,完整性-5,med)

**详 [07 装备](07_equipment.md#补给节点决策)**:`decide_supply(options, state, config) → (idx, refresh?)`。补给角色带红/蓝钻 → 选它(拿到基本赢);无钻按 鞋(反重力靴)> 电池(永动机)> 花(分解液/能量饮料);未出钻 → 刷新 1 次。与 target_comp.key_equips 契合优先。

> **状态(2026-08-04,D-20)**:`decide_supply` 纯逻辑骨架**已实现 + 4 测试绿**(带钻优先 / 无钻刷新找钻 / key_equips 契合 +10 + 通用装备价值 `_EQUIP_VALUE`)。`SupplyOption`(idx/角色/装备/带钻)+ `SupplyPick`。**handler 接线待阶段 5**(`read_supply_options` OCR + 钻视觉判定,接 `handle_supply`)。

## 接入 battle_loop
battle_loop 的事件分支(当前各 naive「选左」)改为:
- 遭遇分支 → `decide_encounter`。
- 巨星/确认选择分支 → `select_megastar`。
- 补给分支 → `decide_supply`。
- 投资环境/策略分支 → `decide_event`(已有,白名单)。
每个节点决策都是纯函数(读 OCR options + state + config → 选择),可独立测。

## 数据需求(游戏边界)
- 遭遇选项(难度/词缀):OCR。**需游戏**。
- 巨星候选:OCR(确认选择画面的候选角色)。**需游戏**。
- 补给选项 + 带钻:OCR。**需游戏**。
- 词缀表 + 对策映射:meta(研究 + 实机)。**非游戏**可建。

## 测试(纯逻辑)
- decide_encounter:未成型→最低难度;高危词缀+无对策→刷新;有对策→高难度。
- select_megastar:target.core_chars 含盛会之星→绑;否则 buff 契合。
- decide_supply:带钻优先;无钻 鞋>电池>花;未出钻→刷。
