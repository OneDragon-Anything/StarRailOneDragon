# 0110 acquirability 牌池感知(P(≥1张)扣 1/v + held 副本消耗;review#6)

Status: accepted
Date: 2026-08-12

## Context
review#6(用户根因):「牌库有限(买掉即减)→ 识别手上牌是算 acq 的核心,为什么不去识别前后台和备战」。
原 `acquirability_factor = min(refresh_prob(level, cost))`(ADR-0092 理论法)有两缺陷:
1. **漏 ÷v**:它返「该**费用**的刷新率」,但 1 格该费用里只 1/v 是该角色(v=同费种类数 9-14)→
   高估特定角色可得性 ~v 倍(1费核心被当 acq=1.0,实 ~0.3)。
2. **不扣 held**:牌库有限,玩家持有的副本已离池 → 剩余少 → 越难再刷。原码完全不读 held。

ADR-0109 定了牌池副本数(27/9),数据齐 → 可治本。

## Decision Drivers
- 用户根因:held 副本消耗牌池 → 必须 read(用户:「识别你手上有什么牌是算 acq 核心」)。
- 正确性:acq 应量「该**角色**刷出率」非「该费用刷出率」。

## Considered Options

### A. 牌池感知 P(≥1张),扣 held,用现有超几何 —— **选定**
`acq = min over core of [1 - _refresh_dist(p_cost, v, a, c=0, k=1, j=held)[0]]`
- P(单次刷新 5 格中 ≥1 张该角色),用 ``_refresh_dist`` 精确超几何(M~B(5,p_cost) 出费用格数 →
  超几何出该角色),与 D牌蒙特卡洛同模型。
- **j = 玩家持有该角色基础副本**(3合1 折算:1星1/2星3/3星9/4星27),由 `_held_base_copies(state)`
  从 state.bench+deployed(seed 自 session.tracked_*,带 char_id+star)算 → j↑ → rem_target=a-j ↓ → acq ↓。
- 忽略 NPC 消耗(c=0,保守:只扣自己持有的;NPC 共享池待实机核,见 currency_war.md)。
- select_comp 乘子仍 `0.5+0.5·acq`(ADR-0105 次级 tiebreak):牌池感知后范围收窄 ~0.005-0.3 →
  乘子 0.50-0.65,仍提供「低费核心早期更易刷」的 tiebreak 区分(1费×0.65 vs 5费×0.50)。

### B. 只 ÷v 不扣 held
修缺陷 1 不修 2。否 —— 用户根因就是 held(「识别手上牌」),不扣 held 没解决用户点出的问题。

### C. 用 expected_refreshes(到 2 星的期望刷新数)转 [0,1]
更贴近「D 牌到成型」但:① 需选 target_star(2/3);② E→[0,1] 转换是额外调参;③ held 接线一样要做。
A 更直接(单次刷新可得性,select_comp 量级一致),C 留给 D牌蒙特卡洛(cw_decisions 已用)。

## Decision
选 A。`acquirability_factor(core_chars, level, held=None)`;`_held_base_copies(state)` 从 bench+deployed
折基础副本;select_comp 算 held 传入。state.bench/deployed 由 shop.py:185 seed session.tracked_*
(带身份+star)→ 无需新 ScoreContext 接线。

## Consequences
- acq 量级正确化(特定角色非该费用):1费核心 acq 从 1.0 → ~0.31(早期);持有副本后进一步降。
- select_comp 偏好「未大量持有 + 低费 + 该等级能刷」的核心(牌池未耗 + 易刷)—— 符合「低费核心不赌」设计。
- 依赖 session.tracked_* 可靠(simulation,deploy 后 SIFT 纠漂;漂移时 held 偏差 → acq 偏差,但作次级
  tiebreak 影响有限)。read_game_state 仍不读 bench/deployed 身份(用 session 跟踪),后续可加 SIFT 直读增强。
- 测试:旧 `test_acquirability_factor_level_cost`(断言 min refresh_prob)→ 重写 `test_acquirability_factor_pool_aware`
  (验 ÷v + held 消耗 + 空 core);加 `test_held_base_copies_folds_star`(star 折基础副本)。
- 297 测试过。
- **NPC 共享池消耗(c)仍忽略**(保守,待实机核是否共享);卖回是否回池待核 —— 这些影响 acq 精度但不阻塞主路径。
