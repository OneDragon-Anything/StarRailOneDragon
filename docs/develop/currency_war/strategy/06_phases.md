# 06 实施阶段(分)

> 总见 [README](README.md)。逐阶段:做什么、依赖、测试、游戏边界、完成判据。
> **review r1(方案)修正**:加 replay harness(风险-3,阶段 5.5)、A5 拆分(连贯性-1,阶段 3a/5+)、装备/巨星/遭遇节点决策并入阶段、cw_factions meta 分层(连贯性-2)。

## 已完成
- **阶段 0**(战术层内核 + r1 修 44 条,commit `9399d1b1`+`cd88ce7a`)✅ 非游戏。
- **阶段 1**(A1 蒙特卡洛 D 牌 + A3 阶段键控,commit `d6b68dc4`)✅ 非游戏。

## 待做(非游戏)

### 阶段 2:A2 阵容规划 + 巨星 + 节点决策骨架 + 战斗反馈 — ✅ 已落地(2026-08-04)
- 内容:**COMP_LIBRARY**(阵容库,多维打分:强度+成型难度+契合,**不标"邪道专打"**)+ `Comp` dataclass(含 shared/transition/form_round/version 字段)+ `comp_score`(显式公式)+ `select_comp` + `target_progress_score`(去三重)+ `maybe_pivot`(比较型转型信号)+ `select_megastar`(巨星,03)+ `decide_encounter`/`decide_supply`(08 节点决策,纯逻辑骨架)+ evaluate 整合 target + **`PerformanceTracker` + `RoundOutcome`(双侧:r6 F3)+ `comp_viability`/`comp_prior`(r5 拆)+ `MECHANIC_COUNTERS` + `MECHANIC_SYNERGIES`(双向 debuff=buff,详 10)+ obs_weight schedule + 归一化 expected_drop 先验(详 10)** + 测试。
- 依赖:阶段 1。
- 测试:mock 阵容库 + states → 选对 target/转型/巨星/遭遇;target_progress 去三重。**r6 要求:实现前先写测试锁住交互行为** —— ① open-fold(intentional_fold=True 的 outcome 不污染 comp_viability);② 归一化(boss 掉血多但归一化后不误判弱、不 None);③ pivot 归因(换 comp 后旧 comp 战报 ×0.3 降权);④ 冷启动(delta<1 → None)。这些互配合 bug 纸面推不出,只能测试锁。
- 完成判据:select_comp 各 mock 局面选合理;evaluate 含 target_progress + 通关能力(成型度+装备);节点决策函数齐;4 个交互测试全绿。
- 游戏?**否**。

### 阶段 3a:A4 牌池概率 + 装备模型 — ❌ 待做
- 内容:**SHOP_REFRESH_TABLE**(费用刷新概率表骨架)+ `_sample_shop` 改 cost→char 采样(正确性-3)+ PvE 单玩家牌池计数(正确性-2)+ 装备模型(GameState.equip + **equip_fit(comp) comp 相关评分** + Equip 动作 + 通关能力 eval 项,07)+ D 牌上限修(✅ r5 已修)+ 蒙特卡洛 seed(风险-5)+ 测试。
- 依赖:阶段 2。
- 测试:采样分布;牌池计数;装备加分;可叠加装备超线性;D 牌上限。
- 完成判据:_sample_shop 用概率表+牌池;装备 eval 项;装备超线性 bonus;D 牌上限生效。
- 游戏?**否**(概率表精确值待阶段 6 校准)。

## 待做(需游戏)

### 阶段 4:OCR→GameState 接线 + 状态对账 — ❌ 需游戏
- 内容:所有 `read_*`(gold/round/level/plane/hp/streak/shop_full/bench/bosses/equip/encounter/supply/bench_full)+ read_game_state + reconcile(置信度加权,A6)+ post-action verify(04)+ confidence 字段。
- 依赖:星铁在线 + 备战 screen_info(已有部分)。
- 完成判据:read_game_state 准确读全;reconcile 每回合对账 deployed;post-action verify 单笔对账。
- 游戏?**是**。

### 阶段 5:op 层接线 — ❌ 需游戏
- 内容:BuyShopCards 用 plan(删旧 smart_buy_decision);DeployBench 用 plan 的 Deploy;battle_loop 事件分支用 decide_event/encounter/supply + select_megastar;开局 read_bosses → state.bosses(boss_fit 用;decide_boss_priority 已删);read_game_state+reconcile+maybe_pivot 每回合调;post-action verify 接入。
- **D 牌两阶段 plan(r6 F8)**:`simulate(RefreshShop)` 不更新 shop 内容(刷新后未知),故 plan emit RefreshShop 后当回合无法 emit 新 shop 的 BuyCard(会买旧 shop 的牌)。**op 层**:plan1 可能 emit refresh → 执行刷新 → **重新 OCR shop → plan2 emit buy**。纯逻辑阶段(2-3a)先在 doc 标注此限制,op 接线(阶段 5)实现两阶段。
- 依赖:阶段 4 + 阶段 2。
- 完成判据:`run_standalone_app('currency_war')` 全程用 cw_decisions 决策,跑通不卡死。
- 游戏?**是**。

### 阶段 5.5:replay 测试 harness(风险-3)— ❌ 需游戏(随阶段 5 建)
- 内容:实机跑时**每回合序列化 GameState + 决策 + 结果**到 `.debug/temp/currency_war/runs/<run_id>/`;`replay(run_dir, new_strategy) → decisions_diff`(重放新策略看决策变化);A/B 对比权重(同 replay 两套权重,对比关键决策点)。
- 依赖:阶段 5(bot 跑通才能录)。
- 完成判据:能录局 + replay + A/B 权重对比。**没有它阶段 6 难收敛**(单局方差 >> 权重效果)。
- 游戏?**是**。

### 阶段 5+:A5 战术涌现(多步搜索)— ❌ 待做(非游戏,但依赖搜索深化)
- 内容:A1 加深为 2-3 步蒙特卡洛/expectimax(转型成本/凑整/牌池操纵的多步链可算)→ 删 _maybe_* bolt-on(凑整/牌池从搜索涌现,A5)。
- 依赖:阶段 3a(A4 牌池)+ 多步搜索实现。
- 完成判据:多步搜索;_maybe_sell_for_interest 删除(凑整涌现);转型收益精确。
- 游戏?**否**(纯逻辑;但价值需实机验证)。

### 阶段 6:实机实测 + 迭代 — ❌ 需游戏
- 内容:用 replay harness(5.5)跑若干局 A8,记录每回合;客观指标(胜率/HP/round/羁绊);A/B 权重;反推校准 eval 权重 + 概率表 + COMP_LIBRARY 强度;迭代到目标胜率。
- 依赖:阶段 5 + 5.5。
- 完成判据:A8 胜率达标(先跑基线再定目标);权重有数据支撑。
- 游戏?**是**。

## cw_factions meta 分层(连贯性-2)
cw_factions.py 硬编码 31 羁绊(赛季级 meta),与"config 可热更"原则有张力。**分层**:cw_factions = 赛季级 meta(随版本改代码+测试);config = 用户偏好级 meta(yml 热更)。或把 cw_factions 数据抽到 yml(`assets/game_data/currency_war/factions.yml`)+ 代码只读。至少承认此 trade-off,版本更新时 cw_factions 是必更项。

## 当前推进
星铁未开 → 先做**阶段 2(A2 阵容+巨星+节点决策)+ 阶段 3a(A4 牌池+装备)**(非游戏);阶段 4-6 + 5+(多步搜索,非游戏但靠后)等星铁/按需。

## round 2 补充(新发掘)
- **R2-13 全回合 mock 模拟器(med,高 ROI 早发现战略层 bug)**:阶段 2 加 mock run simulator(敌人 HP 衰减 + 随机发牌 + 每回合 plan)→ 跑 N 局断言胜率/成型率/无死锁。比 replay harness(5.5 需游戏)更早可用,非游戏端到端验证战略层。
- **meta-run 阶段(09)**:阶段 -1(优势布局 preconditioning,需游戏)+ 阶段 6+(钻钞 farming 元循环:超频刷钻→喂优势布局→标准 A8)。【凹开局重开(原阶段 4.5)已删 —— 策略够好该能克服任何开局】
- **R2-14 app 级 circuit breaker(med)**:04 的"多次失败→跳过"是单笔级;加 app 级熔断(连续 K 回合 state 不变/画面未切/OCR 全失败 → abandon run + 告警,防死循环烧时间)。
- **R2-6 全量事件图鉴(med)**:../../../game/currency_war/data/investment_envs(92)+ strategies(268)做成 ranked yml,decide_event 查全量(当前 ~30 白名单,无命中乱选 idx 0)。
- **R2-16 LockShop(low-med)**:cw_state 加 LockShop action(shop 有下回合才买得起的 key 牌时锁住,省自动刷新)。

## round 3 补充(根本盲点:P0/P1/P2)
- **P0-3 eval 校准方法论 → 手调 + side door(2026-08-03 修订,阶段 6)**:阶段 6 "iterate"当前是空的。**主线**(用户定调:不主依赖 ML):① replay/telemetry(F-6,用户认可的"采集")记 eval 特征分解 + 决策 + **观测结果**(掉血/胜负);② **人肉眼复盘** replay,**只手调最敏感 3-5 维**(详 02 权重纪律:hp_safe_threshold / comp_viability 观测权重 schedule / MAX_REFRESH_PER_ROUND / α(t) r_open·r_close / 连败 fold 阈值);research meta 先验权重**固定**不动(版本更新才改);③ 指标用**观测真值**(到达 round 分布 + HP 曲线 + `PerformanceTracker` 掉血趋势),不是拟合的 win_prob;④ eval 权重**设计成可拟合**(别硬编码),为未来留口。**side door(可选,非主线)**:**攒够 N=50 局 replay 后**可启用离线逻辑回归/survival/bandit 拟合(详 02 round4 F-1/F-2/F-7)——但版本短命,不强制。**无 replay 采集 + 观测指标 = 阶段 6 无法收敛**(单局方差 >> 权重效果)。
- **战斗反馈 + 敌人机制阶段(详 10,观测驱动)**:阶段 2(非游戏)建 `PerformanceTracker` + `RoundOutcome` + `comp_viability` 骨架 + `MECHANIC_COUNTERS`(research 粗估)+ 测试;阶段 4-5(游戏)实机 `read_hp` before/after 接 PerformanceTracker + OCR 敌人机制填表;阶段 6 用观测真值手调 `comp_viability` 先验权重。**这是 A8 胜率地基,观测驱动版,非游戏部分不能等到阶段 6**。
- **P2-2 性能预算硬约束(med-high)**:A8 备战阶段超时 = 自动败(掉血)。硬实时预算(如 20s)+ 降级阶梯(t<10s 跳蒙特卡洛、t<5s 纯贪心、t<2s no-op 保命)。**阶段 4 必须实测 OCR 单回合耗时**再定 k(蒙特卡洛采样数),不能拍脑袋 k=8。
- **P2-3 OCR sanity bounds(med)**:每字段 invariant 断言(0≤gold≤~100、1≤level≤10、0≤hp≤max、board count=deployed count);越界 → 丢弃本回合 OCR 用上回合值 + 告警。reconcile 加 **hard assertions**(非软加权),防误读级联(gold 读成 500 → 狂买)。

## round 4 补充(校准收敛 + 确定性 + 可观测)
- **F-1 探索 preset 阶段(详 02 round4)[side door · ML 可选]**:阶段 6 校准前,先跑"探索采样"(K 套 comp 强绑 preset 各 N 局)保证状态覆盖 + 覆盖度指标 + importance weighting。**主线(手调)不强制**;仅当上 ML 拟合 side door 时才需要(无此 = 拟合收敛到占位权重的局部最优)。
- **F-4 全链确定性契约(HIGH)**:replay A/B + 拟合要求整条 pipeline 确定。阶段 5.5 加 `determinism_check`(同输入跑两遍 assert decisions_diff 空)。固定:argmax stable tie-break(字典序最小)、dict 排序 key、浮点阈值、蒙特卡洛 seed、post-action 重试次数。
- **F-6 决策迹 telemetry(MED-HIGH)**:replay 每回合额外序列化 `decision_trace`(candidates + eval_delta 分项 + 蒙特卡洛采样分布 + select_comp 分项 + pivot 信号值)。阶段 6 反推校准全靠它(否则看结果猜原因)。
- **F-7 冷启动(详 02 round4)[side door · ML 可选]**:阶段 6 开头"冷启动:meta 先验权重 + 探索 preset 跑 N 局 → 拟合 v1 → 再正常跑"。**主线(手调)等效**:用 research meta 当手调初值(已做),靠 replay 复盘迭代;正式 ML 拟合 v1 留作 side door。
- **F-11 replay schema 版本(LOW-MED)**:replay 加 schema_version + migrate 函数(策略演进改 GameState 字段时向前兼容),否则旧 replay 作废。
- **F-9 中局死局检测(MED,观测驱动)**:`is_run_dead(state, tracker)`(HP 低 + `recent_hp_loss_trend` 仍高,双门)→ dead 时钻钞 farming 模式 abandon / 标准模式最小损失(纯防御)。与 R2-14 circuit breaker 互补(CB=卡住,这个=没卡但赢不了)。**不依赖预测器**,纯观测。
- **F-12 自适应算力(LOW-MED)**:关键决策(plane3/HP<30/转型/boss前)蒙特卡洛 k 拉到 64+,碾压局 k=4。`criticality=f(plane,hp,pivot,round_to_boss)`,k 自适应。
