# ADR-0117:streak 方向驱 plan —— 连胜破息保连胜(C 杠杆 3 winning half,R2-4b)

- **Status**:Accepted(2026-08-13)
- **关联**:02 R2-4b(连败 fold 半已由 HP-gating 覆盖)/ 14 §连胜中「2 胜+」/ ADR 无前置(streak magnitude C2
  + 胜负语义 fixture 已核,均 2026-08-11 就绪)

## Context

auto-chess 连胜/连败都是经济杠杆(C 杠杆)。CW 已接:
- **magnitude(C 杠杆 2)**:`economy_score` 取 `abs(streak)` 对称计档位金(连胜/连败都给金,2026-08-11)。
- **连败 fold 半**:用户 2026-08-12 原则「血量安全→fold(保息攒钱)/ 不安全→急救」,**已由 HP-gating 覆盖**
  (`_phase_weights` HP safe→balanced 不降 economy = 自然保息 fold;HP 危→保血 = 急救)。无需显式「连败→fold」代码。

**剩余 gap = 保连胜半**(`02 R2-4b` / `14 §连胜中`):连胜中(2 胜+)维持连胜 > 吃息(断连胜亏的金 > 一档利息亏)。
旧码 `_saving_for_interest`(gold<50 + 板满 + HP 安全 + 板强 → hold gold 攒息,抑制散买/刷)**不分连胜方向** →
连胜中也攒息 → 不花钱提质量 → 断连胜。缺「连胜中破息」的 plan 行为。

## Decision Drivers

- streak 方向信号已就绪(结算「连胜×N」前缀=方向 → `parse_streak` 带符号 → `session.last_streak` → `state.streak`,
  fixture 核实 2026-08-11)→ 纯逻辑接线,非卡数据/调参。
- 「保连胜>吃息」是 auto-chess 基本功(02 R2-4b / 14 §连胜中),不接线 = 经济系统性低估连胜价值。

## Considered Options

### A. 连胜 ≥ 阈值 → `_saving_for_interest` 破息(采用)
连胜达到阈值 → 不攒息,花钱提质量维持连胜(买 target 升星 / 找 quality)。阈值 = `WIN_STREAK_BREAK_INTEREST = 2`
(auto-chess 连胜金 2 连起档:2 连=1 金、3 连=2 金……故 2 连即值得破息维持)。
- **作用面**:`_saving_for_interest` 同时 gate ① 散买(L688 `_saving`)② 刷新(L764)→ 破息后两者都放开,
  贪心按 eval 提升选 quality 动作(买 target 到 bench 升星 / 刷找 upgrade)。
- **不动 `_saving_for_level`**:攒级是 tempo 投资(升级提 cap + 高费刷新率 → 也助维持连胜),不该破。

### B. 连胜时也放宽 `_refresh_cap`(否决:过度)
连胜破息后 refresh gate 已放开(选项 A),`_refresh_cap` 仍受 `MAX_REFRESH_PER_ROUND` 节流已够;
再放宽上限 = 过度,且 02 R2-4b 只要求「保连胜>吃息」(息维),未要求连胜多刷。**不在本 ADR 范围**。

### C. 给「维持连胜的 buy/deploy」加战术分(否决:模糊 + 调参)
R2-4 旧描述提过「为保连胜提质量的 buy/deploy 加战术分」。否决:① 买什么「提质量」难定义(delta 已由 eval 量,
再加战术分 = 双计);② 属调参(权重),阶段 6 实玩校准,非现在。破息(选项 A)放开 gate 后,贪心自然选 quality 动作。

## Decision

**A**。新增常量 + 抽 helper(`cw_decisions.py`):

```python
WIN_STREAK_BREAK_INTEREST: int = 2   # 连胜 ≥ 此 → 破息(14 §连胜中「2 胜+」)

def _should_save_for_interest(state, config, target_comp) -> bool:
    """全满足 → 攒息;连胜 ≥ WIN_STREAK_BREAK_INTEREST → 破息(保连胜>吃息)。"""
    if state.gold >= INTEREST_THRESHOLD: return False
    if state.deployed_count() < state.max_units(): return False
    if state.hp < effective_hp_threshold(state, config): return False
    if target_comp is None or form_progress(target_comp, state) < COMMIT_FRAC: return False
    return (state.streak or 0) < WIN_STREAK_BREAK_INTEREST   # 连胜 ≥ 阈值 → 破息
```

`_best_improving_action` 内联条件 → 调 `_should_save_for_interest`(条件随连胜项变长,抽 helper 利读 + 可单测)。

**向后兼容**:streak 默认 None/0 → `(0) < 2` True → 攒息行为不变(对局首回合无结算无连胜,不破息,正确)。

## 验证

- 单测 `test_should_save_for_interest_winning_streak_breaks_it`:同场景(板满+gold<50+HP 安全+板强),
  streak=0/连败 → 攒息 True;连胜 3 / 连胜 2(阈值)/ → 破息 False;连胜 1(<阈值)→ 仍攒息。
- 全 CW 测试 312 passed(含 `test_plan_t107_saves_interest_when_board_full_low_gold` 回归:streak 默认 0,攒息不变)。
- live 验待补(连胜 ≥2 的备战帧实跑,看 plan 是否破息花钱 —— 被动等结算源产生连胜)。

## 关联

- 02 R2-4b(fold 半 HP-gating / winning 半本 ADR)/ 14 §连胜中 / 策略需求清单 §5 streak 行。
- C 杠杆 2(magnitude,economy_score)/ `parse_streak`(带符号,结算源)。
