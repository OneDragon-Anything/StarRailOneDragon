# 0096. optionality/α(t) 与 commit 不矛盾 —— 管不同决策(eval vs pivot)

- **Status**: accepted
- **Date**: 2026-08-11
- **原编号**: D-96(解 review round-2 残留 HIGH-1)

## Context
review round-2 指出:策略里同时有两套"灵活"机制 —— α(t) 线性坡(14 §4 / 03 F-3,eval 里 `α·target_progress + (1-α)·optionality`,早灵活晚承诺)和 softened commit(12 §F1,commit 后 prefilter 放过过渡/通用辅助)。reviewer 担心两者矛盾:round5 α(t)=0.3(eval 70% 期权,鼓励"买别的方向牌")但 target_committed=True(prefilter 拒"别的成型方向")→ α(t) 鼓励的行为正是 prefilter 拒的。

## Decision Drivers
- 两套机制都为"灵活",但不能自相矛盾
- 用户玩法修正(commit 渐进 / 通用辅助该买 / optionality 是基础设施)

## Considered Options
1. **α(t) 主、commit 降为 α 连续行为**:target_committed 改 α-continuous —— 大改 + 失去 commit 的反振荡布尔语义(否)
2. **softened commit 主、α(t)/optionality 删**:失去"早期保期权"的 eval 维度,且 optionality 函数已实现(否)
3. **厘清两者作用域(不同决策),非二选一(选中)**:optionality/α 在 eval;commit 在 pivot;optionality 限定"通用角色" → 自洽

## Decision
**两机制管不同决策,正交,不矛盾**(reviewer 的矛盾来自把 optionality 误读成"买别的成型方向核心"):

| 机制 | 作用在 | 管什么 | 语义 |
|---|---|---|---|
| **α(t)/optionality** | **evaluate**(买/deploy/sell) | bench 持有**通用角色**(属 ≥2 comp)给正分 | 早重期权(保通用角色)→ 晚重 target_progress(commit);权重渐变 |
| **commit(target_committed)** | **maybe_pivot**(换 target) | target 粘性,防 board 抖动驱动的信号1 翻转振荡 | 布尔:commit 后不因"略优 comp"弃 target |

**关键限定(自洽的根)**:`optionality_score` 只奖 **bench 上属 ≥2 comp 的通用角色/通用辅助/transition**(符玄/知更鸟/花火/爻光/缇宝/桑博…),**不奖"别的成型方向的独家核心"**。softer prefilter(commit 后)放过的正是这些通用角色(optionality 奖的),拒的是**别的成型方向独家核心**(optionality 也不奖)→ **两机制对同一张牌给一致判断**(通用角色:eval 奖 + prefilter 放;独家 off-direction 核心:eval 不奖 + prefilter 拒)。

→ round5 α=0.3 场景:eval 高权 optionality 鼓励买**通用角色**(符玄这类),prefilter 也放通用角色 —— 一致,不矛盾。reviewer 的"α 鼓励买别的方向"是把 optionality 误当"买 off-direction 核心"了。

## Consequences
- 正向:两机制共存自洽,无需删任一;optionality 接线时按"通用角色"scope(CHAR_VERSATILE 集合 = 属≥2 comp),别扩到 off-direction 核心。
- 负向:需建并维护"通用角色"集合(从 COMP_LIBRARY shared_chars ∪ core_chars 反查 ≥2 者);调研出的通用角色清单(符玄/知更鸟…)是其源数据。
- 边界:optionality 不解决"早期是否该切换 target 方向"(那是 commit/maybe_pivot 的事,由 form_progress + 信号1/2/3 管);commit 不解决"bench 该持哪些 versatile 牌"(那是 optionality 的事)。

## Links
- `· docs/develop/currency_war/strategy/03_comp_planning.md`(optionality P1-1 + 掉血归因)/ `12_comp_commitment.md`(commit F1)/ `14_phase_skeleton.md`(§4 A 轴 α(t))`
- 关联:review round-2 HIGH-1 / `4_策略设计/策略需求清单.md` §5(optionality 接线)/ `流派扩充调研.md`(通用角色清单)
