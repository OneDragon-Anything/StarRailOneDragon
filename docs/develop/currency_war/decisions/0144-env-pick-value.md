# ADR-0144: 环境侧选卡价值分接入(env_eval 83 条)——env 恒 0 分问题终结

## Status

Accepted(2026-08-15)

## Context

- 环境侧 83 条全量评估产出(env_eval_full.tsv;ADR-0142 同口径)。评估实证两大结构差异:①synergy 主导(47/83 阵营定向)非策略侧的 economy 主导;②量化口径断层 —— yes-direct 仅 1 条(蓝海),环境效果全是整局规则(费率覆写/分期/重复触发),EconomyEffect 现有字段结构性装不下。
- **接线前真 gap**:decide_event 里 env 名不在策略注册表 → 恒 0 分 → fallback **恒选第一张**(M19 16:07 实测选了 idx0 增发货币,非决策)。开局环境屏三张全 0 分纯靠运气。

## Decision Drivers

1. 环境无品质分级(图鉴亦无)→ 不能套策略侧品质先验,基准分是唯一可分层信号。
2. 阵营定向类(概念股/邀请/契约)价值依赖 comp 对齐 —— 开局选时 comp 未定(裸分),局中环境屏(联席决策 2-6 节点)comp 已定(条件分)。
3. 防一次性错装:评估点名 6 条(增发货币/成功经验/二手市场/长线利好/策略大师/劳务派遣合同)不可装 instant_gold/xp_per_node —— 本 ADR 不装(EnvEconomyEffect 扩字段待后续)。

## Considered Options

- A. 基准分 + 阵营条件分 floor + HP 钩子,进 decide_event ✅:与策略侧(ADR-0143)同消费点,env 分支独立不搅策略路径。
- B. 等 EnvEconomyEffect 建完再接:量化是慢工程,选卡改进不该被字段缺口阻塞;基准分与字段化正交。
- C. env 白名单 config:白名单只解决头部,且与注册表双源漂移(0143 已否)。

## Decision

1. `InvestmentEnv.pick_value: int = 0`;ENV_PICK_VALUE 表(83 条,TSV 派生)replace 合并。
2. `ENV_FACTION_MATCH_FLOOR`(概念股 78/邀请 70/契约 72):faction ∩ target_comp.factions 时提到 floor;未匹配吃裸基准分。
3. `ENV_SURVIVAL_BONUS`(白银时代/敌后破坏 +15,人身意外险 +10):hp<40 降难度求稳钩子。
4. decide_event env 分支:策略 miss 且 env 命中 → 基准分/faction floor/HP 钩子。~~已知局限:OCR 形变 env 名可能 LCS 误中~~(**修订 0144b,评审 212c+自查双实证:canonical env 名即有 29/83 误中——增发货币→超发货币0.75 等;env 命中一律跳过 pick_value_of 与 _option_rarity 的 LCS 兜底,commit 71bbfb9b**)。
5. **default_strategy 修订 ADR-0134**:env kind 也传 target_comp —— 开局 None(行为同旧),局中环境屏 comp 已定使阵营条件分生效。
6. 两 handler(invest_env/invest_strategy)用 `session.last_state or GameState()` 替空 stub:~~持有策略用真值~~(**勘误 2026-08-15 评审:decide_event 不读 active_strategies,该半句不成立**;实际收益 = HP 分档真值 + on_dot 惩罚路径激活——后者原是死配置被顺手救活,方向正确)。空 stub hp=100 恒满血,曾致 0141 惩罚全部按满血档)。

## 后续

- EnvEconomyEffect(环境整局规则字段化:费率覆写/分期/重复触发)待设计 —— 53 条 yes-new-field 是输入。
- codex 数据质量点(增发货币 6/8/10 vs 12 等)局间图鉴核。
