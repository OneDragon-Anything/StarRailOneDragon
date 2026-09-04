# ADR-0147: roll 可负担性门 —— P2 满血连刷烧金终结

## Status

Accepted(2026-08-15;live 验证待 M22+)

## Context

- M20 死亡窗(评审 f3ab 离线复现):P2 r2 hp35→1,gold 18→0;**5 轮 plan 各提案 4 刷**,执行器硬墙实刷 4×2 金;放行分支 = 列车同行 lv7 roll 分支(**满血也 cap=4,每个 plan 恒触发**)+ hp<55 叠加。
- 根因(离线复现实证):散板 8 阵营下 MC 期望**恒正**(+9.02)——任何采样牌都算"强化已有阵营"(REINFORCE_BONUS+4),而 eval 中金币边际成本 ≈0(仅 10 倍息档边界有价)→ 刷恒赚。单修 MC 只认 target(a-strict 仍 +1.75)/修 hp 降权/修息档谁都翻不了符号。
- 用户基准(economy_research §7):「P2 稳定≥50 吃息,少主动刷新」。
- 事实修正:列车同行 lv7 roll 的是 **3费姬子(p=0.40 峰值)**,非"4-5费稀疏"(初判有误)。

## Decision Drivers

1. 金计价替 MC 符号:MC 的金币边际成本≈0 是结构性的(修 eval 牵全局 churn),用**期望花费 vs 预算金**直接判,不动全局 eval。
2. 已有资产接线:cw_shop_odds.expected_refreshes(超几何精确)**已实现未接线**(docstring 明言待接线)——本次接上,零新模型。
3. roll 让位语义:不可负担 → roll 分支不放宽 cap → node plan(P2 推 8)主导 → 行为回到"少刷多买经验"(基准 #3/#7)。

## Considered Options

- **a) MC 只认 target**:单独无效(正号即刷;+1.75 仍正);附属可行(超几何采样校准 + 散件×0.3),留后续。
- **b) 急救货检**:真实 target 命中率 40-50% → 门半数放行,近无效;且 roll 分支满血也放宽,货检不覆盖。否。
- **c) concentration 收紧**:死亡轮的买全是合法 reinforce(深化已有阵营)非开新阵营,罚打不中;与 0.3 折扣 revert 史同族。否。
- **d2) roll 可负担性门 ✅** + **d1) spend_mode 进场金门槛**(穷→saving,下一步)。

## Decision

1. `cw_economy.roll_affordable(state, config, target_comp)`:E[刷到下一张核心]×2金(`expected_refreshes(k=1)`,非凑 2星——后者 22 刷/44 金会让门永不放行)vs 预算金(gold − `_xp_gold_floor`);且 gold ≥ 4(两刷起判)。
2. `_refresh_cap` 的 roll 分支加门(签名加 config 可选参,plan 调用透传);不可负担 → 不放宽(基线 cap=2)。
3. 边界实测(列车 lv7 3费):期望 6.9 刷/13.7 金;xp_floor=20 → **gold≥35 放行,≤30 拦截**——恰是用户基准「P2 稳定≥50」的邻域数学表达。M20 死亡态(18/5)全拦。

## 验证判据(评审给定)

- 离线 ✓:死亡态过门 → roll 分支不放宽(test_roll_affordable_gate_adr0147)。
- live(下局起):P2 进场金 ≥30、P2 人均主动刷 ≤2(中位 0)、存活过 2-5、进 P3 时 HP。
- 后续(d1):spend_mode 进场金门槛(P2 穷进场 → saving 重建息引擎)。

## 关联

- ADR-0146(选卡刷新建议)是「事件 3 选 1」的刷新;本 ADR 是「商店 D 牌」的刷新预算——两条刷新线独立。
