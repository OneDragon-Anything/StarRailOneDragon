# 10 战斗反馈(观测驱动)+ 敌人机制克制(分)

> 总见 [README](README.md)。
> **哲学(2026-08-03 用户定调)**:**不建精确战斗模拟器**(星铁战斗太复杂、版本会迭代、维护不起)。人看的是"这回合掉了多少血 / boss 血条动没动"这个**结果**。故用**观测驱动**(OCR ground-truth 反馈),不用预测模型。
> **review r5**:修了 9 个观测信号单点漏洞(节点分层 / 冷启动 / 锁血 / HP 差分 / confidence / comp 拆分 / obs schedule)。
> **review r6**:发现 r5 把观测扶正后引入 **4 个交互级漏洞**(open-fold 污染 / node_type 完全划分致 boss None / 观测只测生存不测击杀 / pivot 后 comp 归因脱钩),本文逐一修。**r6 结论:剩余交互 bug 需代码验证,纸面已到边际 → 阶段 2 实现时用测试锁住交互行为**。

## 核心哲学:观测驱动 ≠ 预测驱动

| 维度 | 预测驱动(放弃) | 观测驱动(采用) |
|---|---|---|
| 信号来源 | 打之前算赢率/掉血(需战斗 sim) | 打之后读**双侧**结果(我掉血 + boss 掉血/击杀) |
| 版本鲁棒 | 差(改数值 sim 失准) | 好(结果就是结果) |
| 维护成本 | 极高 | 低(OCR) |

唯一保留"预测"色彩的是**粗可行性启发式**(几条规则,不是模型)。

## RoundOutcome(双侧观测,r6 F3/F4/F1)

```python
@dataclass
class RoundOutcome:
    round_num: int
    plane: int
    node_type: str              # 普通战斗/精英/遭遇/boss
    comp_tag: str               # 打这关时的 current target comp 名(r6 F4:obs 按 comp 归因)
    intentional_fold: bool      # 本回合是否"故意输攒钱"态(plan fold 写入;r6 F1:排除污染)
    # —— 自身侧(生存信号)——
    hp_after: int               # OCR 结算后 HP(hp_delta = 本回合 − 上回合,差分)
    hp_confidence: float        # OCR 置信度(0-1);低置信(<0.7)不进 trend
    # —— 敌方侧(击杀信号,r6 F3:观测不能只测生存)——
    enemy_hp_after: int | None  # boss/敌人剩余 HP(OCR;None=游戏不暴露)
    damage_dealt: int | None    # 本回合造成伤害(OCR;None=不暴露)
    killed: bool | None         # 是否击杀 boss(OCR 结算;None=不可观测)
```

**双侧观测(r6 F3 + 2026-08-03 修正)**:HP trend 只测"**生存**"(我掉了多少血),不直接测"**通关能力**"。**但按用户实战经验,通关能力 = f(阵容质量 + 装备 + 阵型),不是特殊邪道需求** —— 好好构筑 + 找装备,很多阵容都能通,差别在成型难度。所以"测不准击杀"没那么致命:通关能力主要靠 `comp_viability` 的先验(成型度 + 装备质量)+ 观测确证。RoundOutcome 仍**带敌方侧**(enemy_hp_after / damage_dealt / killed)—— 用来**观测确证**"这阵容真打得动 boss 吗"(对 boss 节点),是 comp 质量的经验校准来源,不是"邪道验证救命稻草"。**阶段 4 实机确认**:游戏是否暴露 boss HP / 伤害 / 击杀结算(`won` 在 PvE 可能恒真 = 每关都进下关,不能当击杀信号)。**若敌方侧不可观测** → 通关能力靠 `comp_viability` 先验(成型度 + 装备质量)兜底 + 阶段 6 实玩校准,HP trend 管生存。诚实承认这是观测驱动的一个盲区,但非致命(通关主要靠构筑质量)。

**伤害基准学习(2026-08-03 用户细化,F3 的正面解法)**:敌方侧 `damage_dealt` 不只当场确证,还**跨局累积**成"通关所需伤害"基准:
- 每局 boss 节点记录 `damage_dealt`(我们造成的伤害)+ 是否 `killed`。
- 跨局聚合 → 总结 `required_damage[difficulty]`(该难度下 historically 杀死 boss 所需的每回合伤害阈值;从"杀了 boss 的局"的伤害分布取下界)。
- **comp_viability 的击杀能力** = 当前 comp 观测 `damage_dealt` 是否达 `required_damage[difficulty]`(达 = 打得动,boss 战有底气)。
- **跨难度反推**:从 A8 的 `required_damage` 按 boss HP/难度缩放推 A7/A6 所需(用户:"根据难度反推其他难度所需伤害")。难度数据少时用缩放,攒够后用各难度实测。
- **两级精度**:① 粗(总可得,若 `killed` 可观测)= 每 comp 类型在各难度的击杀率基准;② 精(若 `damage_dealt` 可观测)= 每回合伤害阈值。
- **越跑越准 + 版本自适应**:基准随每局观测更新,V4.5 改数值后重新累积(符合"观测驱动 + 边玩边挖")。`difficulty` 配置字段决定用哪档基准。

## PerformanceTracker(r6 F1/F2/F4/F6)

```python
class PerformanceTracker:
    history: list[RoundOutcome]
    _last_hp_after: int | None

    def record(self, outcome) -> None:
        """存档;低置信 outcome 打标不进 trend(防 OCR 抖动)。"""

    def recent_hp_loss_trend(self, comp_tag: str | None = None, window: int = 4) -> float | None:
        """归一化掉血 trend(r6 F2):hp_delta / expected_drop(node_type),全部样本进**同一条** trend
        (不按 node_type 完全划分 —— 那会让 boss 观测永久 None + obs 随节点类型震荡)。
        expected_drop: 先验(各 node_type 相对掉血,见代码 `expected_drop`)+ 历史该类型均值 refine。
        过滤:intentional_fold=True 排除(r6 F1,防"故意输"污染);comp_tag 过滤(r6 F4,旧 comp ×0.3 降权而非全删)。
        冷启动(r6 F6):产出的 delta 数 < 1(需 ≥2 outcome 才有首个差分)→ 返回 None。"""

    def is_losing_streak(self, comp_tag: str | None = None, window: int = 3) -> bool:
        """近 window 回合 won=False 占多数(排除 intentional_fold)。样本不足 → False。"""

    def boss_kill_signal(self, window: int = 2) -> float | None:
        """boss 节点专用短 trend(跨位面累计):用 damage_dealt / killed(r6 F3)。
        boss 节点稀疏(18 回合约 3 次),长 window 凑不齐 → 短 window + 跨位面。None 时退通用 comp 质量先验。"""

    def perf_for_comp(self, comp_tag: str) -> float | None:
        """某 comp 的归一化表现(供 comp_viability 观测项)。pivot 后旧 comp 观测 ×0.3 降权(r6 F4)。"""
```

**归一化 vs 完全划分(r6 F2,修 r5 过度修正)**:r5 的"perf_on_node_type 只同类型比"过度修正 —— boss 节点稀疏(`perf_on_node_type('boss')` 长期 None)+ obs 随 current_node_type 震荡。改**归一化**:`hp_delta / expected_drop(node_type)` 全部样本进同一条 trend,既消除"打 boss 掉得多=我弱"偏差,又不丢样本、不震荡。boss 另留短 trend(上方 `boss_kill_signal`)辅助。

## 冷启动 fallback(r5 + r6 F6)

第 1-2 回合 / 新 comp 刚 pivot,观测样本不足。**约定**:trend 方法样本不足(产 delta < 1)→ 返回 `None`;调用方判 None → 退静态先验(保血阈值 `hp < config.hp_safe_threshold`;comp_viability 观测项权重 = 0;is_run_dead → False)。差分需 **≥2 outcome 才有首个 delta**(r6 F6:不是"≥1 outcome")。

## 粗可行性启发式(comp 强度;r5 拆双签名 + r6 F4 comp_tag)

```python
def comp_viability(state, current_comp, plane, tracker) -> float:   # 评 CURRENT(已 commit)→ pivot/eval
    obs = tracker.perf_for_comp(current_comp.name)                   # 归一化 + comp_tag 过滤;None 当冷启动
    rounds_seen = len([o for o in tracker.history if o.comp_tag == current_comp.name])
    obs_weight = 0.0 if obs is None else obs_schedule(rounds_seen)   # 随观测轮次 0→obs_max(见代码;冷启动纯先验)
    prior_weight = 1.0 - obs_weight
    return clamp(prior_weight * (                                 # 先验各项权重见代码(form/equip/mechanics)
        w_form * form_progress(current_comp, state)
      + w_equip * equip_fit(current_comp, state)  # 装备(comp 相关:持有该 comp.key_equips + 它用的可叠加装备,详 07;非通用裸分)
      + w_mech * mechanics_fit(current_comp, current_enemy_mechanics(state))
    ) + obs_weight * obs, 0, 1)

def comp_prior(candidate_comp, state, plane) -> float:              # 评 CANDIDATE(未 commit)→ select_comp
    return clamp(                                                     # 纯先验,无观测
        0.4 * form_progress(candidate_comp, state)
      + 0.3 * equip_fit(candidate_comp, state)   # 装备 comp 相关(详 07)
      + 0.2 * mechanics_fit(candidate_comp, current_enemy_mechanics(state))
      + 0.1 * research_meta_strength(candidate_comp), 0, 1)
```
`comp_score`(03)的 ground term:`comp_score += w_battle * comp_viability(...)`(current target);select_comp 评分 candidate 用 `comp_prior`。**装备/巨星都 comp 相关**(详 07 equip_fit;巨星 select_megastar 按 target_comp 选,不单独评分)。

## 死局检测(三门,r5 + r6 F9)

```python
def is_run_dead(state, tracker, next_node_type) -> bool:
    trend = tracker.recent_hp_loss_trend(window=3)
    if trend is None:
        return False
    if state.hp < DEAD_HP and trend > TREND_THRESHOLD:
        return next_node_type in ("boss", "遭遇", "精英")   # 锁不住血的节点才真死
    return False
```
**锁血门(r6 F9)**:"普通关可能锁血翻盘"依赖锁血机制 —— **阶段 4 实机确认**货币战争是否有锁血;无则删 next_node_type 门,纯 HP+trend 两门。

## helper 语义(r6 F10,补未定义引用)

- `current_node_type(state)` = **刚打完的节点类型**(obs 是观测不是预测;别用"即将打的")。
- `current_enemy_mechanics(state)` = 当前位面/boss 的机制集合(OCR/节点跟踪;`MECHANIC_COUNTERS` key)。
- `form_progress(comp, state)` = `Σ_f min(board[f], form_tiers[f]) / form_tiers[f]`(成型度 0..1)。
- `equip_fit(comp, state)` = 装备 comp 相关评分(持有 comp.key_equips + 它用的可叠加装备超线性 + 狼狩 bonus,详 07)。**comp 驱动,非通用裸分**。
- `mechanics_fit(comp, mechanics)` = 1 − 命中 `MECHANIC_COUNTERS` 的克制惩罚 + 命中 `MECHANIC_SYNERGIES` 的受利加成(双向;详上"敌人机制:克+利")。
- `research_meta_strength(comp)` = research meta 强度先验(S/A/B→分,见 `strength_base` 代码)。

## 敌人机制:克 + 利(双向,2026-08-03 用户洞察)

**机制名跨版本稳;用于 comp 选择/避开,不是预测掉血。砍掉** ThreatProfile 的 `base_hp`/`base_dps`/`turns_to_kill`(预测模型用,版本敏感)。

**关键(用户点出)**:**同一个词缀对不同阵容方向相反** —— "debuff"对有的 comp 是 buff。故模型**双向**:

```python
MECHANIC_COUNTERS: dict[str, list[str]] = {       # 机制 → 克制的 comp 属性
    "禁速":      ["速度依赖"],       # 电视机:克昼神阿雅/鞋队
    "反伤/高防":  ["高频低单次"],     # 琥珀王/死龙/酒杯怪:克反甲白厄式高频
    "冻结":      ["慢速/卡行动值"],   # 急速制冷:克慢速队
    "AoE/集火":  ["脆皮后排无盾"],
}
MECHANIC_SYNERGIES: dict[str, list[str]] = {      # 机制 → 受利的 comp 属性(用户:debuff=buff)
    "反伤":      ["燃血"],           # 正当防卫:反伤让燃血队掉血 → 角斗场记录 → 伤害更高(详下万敌例)
    "AoE/集火":  ["燃血"],           # 群伤让燃血队掉血叠伤害
    "持续伤害":  ["燃血"],           # DoT 也喂燃血角斗场
    "禁速":      ["慢速爆发"],        # (待核)慢速队反而不怕禁速
}
# mechanics_fit = 1 − counter_penalty(命中 MECHANIC_COUNTERS)+ synergy_bonus(命中 MECHANIC_SYNERGIES)
```

**万敌/燃血 = debuff=buff 的典型(🟢 米游社 factions.md 原文)**:
- 【燃血角斗场】:"记录已损失生命值,每 10000 点额外 +3% 伤害增幅" → **燃血队靠掉血叠伤害**。
- 燃血队员:刃/万敌/风堇/千冶·刃/镜流/长夜月/遐蝶/布洛妮娅(characters.md)。
- 故 **正当防卫(反伤)**:克高频阿雅(counter)、**利燃血万敌(synergy)** —— 同一词缀双向。bot 在正当防卫局应**升权燃血 comp**(万敌单 C / 反击杰哥/万敌流,research §10)。
- **"掉血=收益"web(更广)**:燃血 comp + 投资策略「星际和平保险/保险/先亏后盈」(按已损失生命给金/装备,../../../game/currency_war/data/investment_strategies.md)—— 燃血队天生掉血,这些策略额外补益。

机制名跨版本稳;具体 boss/词缀属哪个机制随版本变(随 ../../../game/currency_war/data/competitors.md 实机 OCR 更新)。比"boss 名→counter 阵营"名字查表更鲁棒。**数据需游戏**(实机 OCR 敌人机制/词缀;`enemy_affixes` 字段,见下)。

## 前导 vs 滞后(别把观测当万能药)

掉血 trend 是**滞后**信号。`comp_viability` 前 3 项先验(form/equip/mechanics)是**前导结构信号**(还没成型 → 提前预警),观测是事后确证。两者互补。**r6 补充**:观测还在 3 场景失效 —— open-fold 故意输(F1 标记堵)、boss 战稀疏(F2 归一化 + F3 敌方侧)、pivot 后旧 comp 战报(F4 comp_tag 堵)。观测不是万能药,是"普通关生存反馈 + boss 战通关确证(若可得)+ comp 质量先验兜底"的组合。

## 与现有架构的整合

```
每回合:PerformanceTracker.record(round_outcome)   # 双侧 OCR + comp_tag + fold 标记
    ↓
eval / decide_encounter / select_comp / maybe_pivot:
  - 保血阈值(recent_hp_loss_trend 归一化,冷启动退静态)
  - 遭遇难度(is_losing_streak,排除 fold)
  - comp_viability(先验 + perf_for_comp 观测);select_comp 用 comp_prior
  - 死局(三门)
  - 机制克制(避开被克 comp)
```

## 阶段(06)
- **阶段 2(非游戏)**:PerformanceTracker + RoundOutcome(双侧)+ comp_viability/comp_prior + is_run_dead + MECHANIC_COUNTERS + **MECHANIC_SYNERGIES(双向)** + obs_weight schedule + 归一化 expected_drop 先验 + **r6 要求:finding 1/2/4/6(open-fold 污染 / boss None / pivot 归因 / 冷启动 None)必须先写测试用例锁住交互行为,再实现**。纯逻辑可测。
- **阶段 4-5(需游戏)**:实机确认 HP 差分时机 / **敌方侧可观测性(boss HP/伤害/击杀,r6 F3)/ 锁血机制(r6 F9)**;OCR 接 PerformanceTracker。
- **阶段 6**:观测真值手调 comp_viability 先验权重(手调 + replay,**非 ML**)。

## 测试(纯逻辑,r6 强化交互锁)
- PerformanceTracker:归一化 trend(boss 掉血多但归一化后不误判弱);intentional_fold 排除;comp_tag 过滤(pivot 后旧 comp ×0.3);样本不足(delta<1)→ None;低置信不进 trend。
- comp_viability:成型度高+装备质量好→高分;被机制克制→降分;obs None→纯先验;rounds_seen 增→obs_weight 升。
- comp_prior:candidate 无观测项。
- is_run_dead:HP 低+trend 高+下回合 boss→True;普通关→False(待 F9 确认锁血);obs None→False。
- MECHANIC_COUNTERS:禁速 vs 速度依赖→mechanics_fit 低(克)。
- MECHANIC_SYNERGIES:反伤 vs 燃血(万敌)→mechanics_fit 高(利,debuff=buff)。
