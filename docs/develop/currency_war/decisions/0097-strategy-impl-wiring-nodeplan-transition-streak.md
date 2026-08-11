# ADR 0097 · 策略实现接线轮(node_plan / evaluate α-blend 接法 / transition_tempo / streak 杠杆 / A4.3 牌池)

- **Status**: accepted
- **日期**: 2026-08-11
- **关联**: ADR 0021(骨架×参数)、ADR 0091(REFRESH_PROB 权威表)、ADR 0092(可得性理论法)、ADR 0096(optionality/α(t) 正交);strategy/14 §2(节点节奏骨架);review round-4(阵容调研后 2 HIGH 建模 gap);commit(本批 cw_decisions + streak 观测链)

## Context(背景)

策略方案定型(工件 `4_策略设计/` + round-4 阵容调研坐实大方向)后进入**实现接线轮**:把 `strategy/` 14 doc 的设计(node_plan 骨架)、review round-4 HIGH-2(过渡羁绊)、fixture 核实的 streak 语义、ADR 0096 的 α-blend 语义,落地进 `cw_decisions.py` 战术层 + streak 观测链。

落地前战术层缺这几根信号:
- **节奏**:plan() 升级 gate 用 `_expected_level`(round/plane 平滑曲线),关键 inflection 不够果断(bot 不按人玩节奏升人口)。
- **早期保血**:evaluate 只奖 target 成型 + 基础羁绊,**早期未成型被重罚**(不该)且**无过渡羁绊 tempo**(DOT 慢热 P1 弱死根因之一:限时 AV 下前期无输出 → 超时掉血)。
- **streak 经济**:auto-chess 连胜/连败给档位金,`state.streak` 恒 0(读不到),economy 不消费 → 少一根经济杠杆。
- **α-blend 接法**:ADR 0096 定了 optionality 与 commit 正交,**但 evaluate 未接线**(commit 项恒权、optionality 未奖)。
- **D 牌采样**:`_sample_cost` 手估 pool(低级也采 5 费),与 ADR 0091 权威刷新概率表不一致 → D 牌蒙特卡洛估值偏差。

## Decision Drivers(驱动力)

1. **像人一样玩**(strategy/ README 核心哲学):人按节点节奏升人口、早期凑过渡羁绊稳血、连胜保连胜。
2. **观测驱动非预测驱动**:只用现成真信号(board 阵营数 OCR、结算 streak OCR、REFRESH_PROB 权威表),不建精确战斗模拟器。
3. **限时 AV(行动值)根因**:前期输出低 → 超时 → 掉血;过渡羁绊是前期输出基础设施。
4. **不双源**:node_plan 用阵容无关通用骨架(14 §2),不为每 comp 写 level_plan;过渡羁绊用全局基础设施,非 per-comp。
5. **治本不叠补丁**:streak 先把 magnitude 接进 economy(一根杠杆),方向驱 plan(保连胜 vs fold)留 R2-4b 显式做,不在 economy 里塞方向逻辑。

## Considered Options(备选,最值钱)

### node_plan(节奏骨架)
- **A(选)**:通用 `NodeGoal` dataclass + `_DEFAULT_NODE_PLAN`(7 节点规则,P1 saving/interest/hold、P2 level、P3 allin)+ `get_node_goal(plane, round)`;plan() / `_best_improving_action` 用 `target_level` 作等级 gate 地板(替 `_expected_level`)。
- B:纯 `_expected_level` 平滑曲线 —— 不够果断(关键 inflection 不提前),bot 节奏滞后。否。
- C:per-comp `level_plan`(每 comp 自带升人口节奏)—— 双源(骨架×参数分裂),违背 14 §2 阵容无关骨架。否。
- **关键 inflection**:P2 早推 7、2-5 推 8 搜核心、P3 推 9-10,比平滑曲线**提前**;`_maybe_sell_for_interest` 在 allin/level spend_mode 跳卖息(节奏与囤息相悖)。

### evaluate α-blend 接法(ADR 0096 落地)
- **A(选)**:commit 项 = `α·TARGET_PROGRESS·remaining + BENCH_TARGET`(BENCH_TARGET 始终奖励攒核心件,**不随 α 缩**);optionality 项 = `(1−α)·optionality_score`;transition 项 = `(1−α)·transition_tempo`。
- B:纯 commit(早期重罚未成型)—— 早期未成型是正常的,重罚逼 bot 强行凑成型 → churn。否。
- C:纯 optionality(晚期不奖励成型)—— 晚期必须成型,不罚 → 永远保期权不 commit。否。
- D:commit 项整体随 α(BENCH_TARGET 也 (1−α))—— 早期不该奖励攒核心件?错,早期也要攒核心件(深堆 delta)。BENCH_TARGET 不随 α。否。
- **α 来源**:`alpha_t(state)`(R_OPEN=2 → R_CLOSE=12 ramp;ADR 0096 定义)。target=None(reactive)→ commit 项归零,只剩 optionality + 基础分(A3 向后兼容)。

### transition_tempo(过渡羁绊,review round-4 HIGH-2)
- **A(选)**:`TRANSITION_FACTIONS` = {仙舟, 狼狩, 持续伤害, 列车同行, 贝洛伯格}(能打伤害的早期羁绊,人上人级,comps/README「开局过渡分级」);`transition_tempo_score` = board 凑出(≥2)的过渡羁绊计数(cap 2)× `TRANSITION_TEMPO_BONUS=3.0`,乘 `(1−α)`(早期强调,fades as commit)。
- B:per-comp 过渡羁绊 —— 双源(每 comp 自带过渡),且早期 comp 未定,违背"早期灵活"。否。
- C:无过渡(纯等成型)—— DOT 慢热 P1 无过渡羁绊支撑 → 限时 AV 超时掉血 → 死根因。否。
- D:与 synergy 双重堆(transition 也按阵营激活数计)—— flat-per-羁绊(只奖"凑出 ≥2"的早期 tempo),非堆 synergy 分。否(防双计)。
- **信号**:`state.board` 阵营数 OCR → 真信号现成(D-20 备战 recognizer 产)。

### streak 杠杆(economy C 杠杆)
- **A(选)**:`parse_streak`(结算「连胜×N」/「连败×N」前缀=方向 → signed)→ `RoundOutcome.streak` → `session.last_streak` → `state.streak` → `economy_score` 取 magnitude(`min(abs(streak), STREAK_CAP=5) × STREAK_WEIGHT=2`,对称:连胜/连败都给档位金)。
- B:方向驱 plan(连胜→保连胜 / 连败→fold)—— 需 plan 行为改造,是 R2-4b(02 连败 fold + 保连胜)。先接 economy magnitude(一根杠杆先到位),方向留 R2-4b 显式做,不在 economy 塞方向逻辑(治本不混层)。本轮不选,排期。
- C:从备战 `read_streak` 读 —— fixture 核实备战只读 magnitude 无方向(前缀在结算屏),源不对。否。
- D:magnitude 带方向符号进 economy —— auto-chess 连胜/连败都给档位金(对称),方向是 plan 层语义,混进 economy 评分会双语义。否。
- **fixture 核实(2026-08-11)**:结算屏 OCR 含「连胜×0」形态,前缀连胜/连败 = 方向;备战 read_streak null(不显示 streak)。故 streak 源改结算。

### A4.3 _sample_cost(D 牌蒙特卡洛采样)
- **A(选)**:用 `REFRESH_PROB`(ADR 0091 权威表)`rng.choices(costs, weights=probs)` 按真实刷新概率采;无数据(Lv<4 纯 1 费 / 越界)→ 1 费。
- B:保留手估 pool(低级也采 5 费)—— 与权威表不一致,低级不该出 5 费,D 牌估值偏差。否。

## Decision(决策)

采纳各 A:
1. **node_plan**:`NodeGoal` + `_DEFAULT_NODE_PLAN`(7 规则)+ `get_node_goal`;plan() / `_best_improving_action` 用 `target_level` 替 `_expected_level`;`_maybe_sell_for_interest` 在 spend_mode allin/level 跳过。**值(V4.4 先验,占位,阶段 6 实玩校准)**。
2. **evaluate α-blend 接法**:`α·progress + BENCH_TARGET + (1−α)·optionality + (1−α)·transition`。BENCH_TARGET 不随 α;target=None → commit 项归零(A3 向后兼容)。
3. **transition_tempo**:`TRANSITION_FACTIONS` 5 阵营 + `transition_tempo_score`(board≥2 计数,cap 2,×3.0),(1−α) 早期。
4. **streak 杠杆**:`parse_streak`→`RoundOutcome.streak`→`session.last_streak`→`state.streak`→`economy_score` magnitude(C 杠杆 2,cap 5)。方向驱 plan 留 R2-4b。
5. **A4.3 _sample_cost**:REFRESH_PROB 按概率采。

## 后果(占位待校准)

- 上述权重 / 阈值 / 先验表(STREAK_WEIGHT=2、TRANSITION_TEMPO_BONUS=3.0、_DEFAULT_NODE_PLAN 目标等级)均为 **V4.4 先验占位**,阶段 6 实玩校准(客观指标 round/HP/gold/胜负 驱动);**值只在代码,文档写语义 + 指常量名**(文档同步规则)。
- **未做(显式排期,非跳过)**:① spend_mode → economy_score 权重(§2.2,与 `_phase_weights` 重叠需统一);② danger_d(卡 difficulty/hp_trend OCR,3.5 建档后);③ streak 方向驱 plan(保连胜/连败 fold,R2-4b)。
