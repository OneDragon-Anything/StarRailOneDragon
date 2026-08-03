# 02 评估层 + 搜索层(分)

> 总见 [README](README.md)。战术层:`evaluate`(局面打分)+ `plan`(动作搜索)。A1(蒙特卡洛 D 牌)+ A3(阶段键控)**已实现**;A4(牌池概率)+ A8 上下文 + 鲁棒性 **待做**。
> **review r1(方案)修正**:A4 牌池改 PvE 单玩家(正确性-2)、采样顺序 cost→char(正确性-3)、~~加 A8 邪道 eval 项~~(**2026-08-03 反转:邪道非必需**,见下"通关能力 eval")、aggression 用法(连贯性-4)、蒙特卡洛 seed/鲁棒性(风险-5/6)、D 牌上限(✅ r5 已修)。
>
> **2026-08-03 哲学修订(用户定调,覆盖 round3/4 的 battle_predictor + ML 训练主线)**:
> - **不建精确战斗预测器** —— 原 P0-1 `battle_predictor → (win_prob, expected_hp_loss)` 改为**观测驱动**(详 10):`PerformanceTracker` 记录每回合 OCR 掉血/胜负,反馈给保血阈值/遭遇难度/死局/comp 强度。信号是 ground truth、版本鲁棒,不需要战斗 sim。
> - **ML 训练不为主线** —— round4 的 F-1(off-policy 覆盖)/F-2(survival)/F-7(冷启动拟合)降级为 **side door**(数据攒够谁想玩再上,版本短命不值主线投入)。**保留** F-3(α(t) 承诺-期权时间衰减,非 ML)/F-4(全链确定性,给 replay 复盘 A/B)/F-6(决策迹 telemetry = 用户认可的"采集")/F-10(risk/tail,降级为 tiebreaker)。
> - **权重纪律(r5,防手调不收敛)**:eval 已膨胀到 20+ 维权重全标"待校准" → 20 维手调 = 随机游走。**改**:① research meta 先验权重**固定**(标"V4.4 先验",不标"待校准",版本更新才改);② 阶段 6 手调**只调最敏感 3-5 维**(`hp_safe_threshold` / comp_viability 观测权重 schedule / `MAX_REFRESH_PER_ROUND` / α(t) 的 r_open/r_close / 连败 fold 阈值);③ ML side door 给**明确触发点**:攒够 N=50 局 replay 后可启用离线逻辑回归拟合(非模糊"以后再说")。详 06 阶段6。

## A3 阶段键控 eval(✅ 已实现 + review agent 经济学校准)
evaluate = `_phase_weights(plane, hp)` 加权的(羁绊+经济+角色质量)。**2026-08-03 修正(review agent + 用户)**:前期 economy **不该压低**(利息越早到 50 越好、滚雪球)。原"plane1→economy 0.4"把"前期"和"保血"混淆。现:**HP 危险(hp<HP_DANGER=40)→(1.2,0.4,1.2)保血**(任何位面);**plane3→(1.3,0.3,1.3)锁血**;**其余健康→(1,1,1)平衡**(economy 不压、snowball)。economy_score 利息项由 level_plan 驱动(经济统一论;`economy_mode` 已删,见 README D);synergy 有高 ceiling 潜力项;char_quality 计 bench+deployed。**待校准**:HP_DANGER(A8 高难调高,待 difficulty 字段)+ win_streak(连胜保连胜>吃息,待 read_streak)+ phase 权重值实机(阶段 6)。
**hp 阈值统一走 config(r5,代码漂移修)**:当前 `_phase_weights` 硬编码 `hp < 40`(`cw_decisions.py`),方案各处 hp<30(转型)/hp<50(连败)。**阶段 2 改**:所有 hp 阈值走 `config.hp_safe_threshold` + 偏移系数(转型 0.75×、死局 0.5×、连败 fold 1.5×),删硬编码;`_phase_weights` 签名加 threshold 参数。

**经济统一论(2026-08-03 用户框架,接战略层)**:D 牌/买牌/买经验都是**花钱的一环**。方法论:维持 ≥50 金(息引擎)→ **超出 50 的钱免费该花**,花在哪由 **`target_comp.level_plan[当前等级]`** 导向(level_up / roll 找几费 / stable),tempo 例外(streak/HP 危/断档)可破息。**当前代码缺这条接法**(`economy_score` 已封顶 5 档=金>50 隐式 free,但 plan 花超额金是纯贪心 eval delta、无 level_plan 导向)→ 待战略层 `select_comp` 落地 target_comp 后接(详 03"经济统一论" + `level_plan` 字段)。level_plan 曲线随 COMP_LIBRARY 填(用户选 B:框架先定)。

## A1 蒙特卡洛 D 牌(✅ 已实现)
`_refresh_expected_delta`:扣刷新金后采样 k 个 shop,各取最优 buy+deploy eval 均值 − base。把「何时 D 牌」从无法建模变可计算。simulate 极快,实机可跑。

### D 牌上限(✅ r5 修死代码 + review agent 改动态)
原 `sum(1 for a in []) < 2` 是死代码(永远 0)→ 不防无限刷。**r5 修**:`plan` 追踪已刷次数经 `refresh_budget` 传 `_best_improving_action`。**review agent 再修(固定 2 太死)**:改**动态上限** `_refresh_cap(state)` —— 基线 2,**关键回合放宽到 4**(plane3/升 8 搜核心、HP 危险锁血急救);待补:拿刷新减费策略(砂里淘金/加油站)→ 6(需 active_strategies 字段)。注:电表倒转(砂里淘金循环无限金)是已知场景但**难+耗时、非推荐 bot 玩法**(用户),不主动追。测试 `test_refresh_cap_dynamic` 锁定。

## A4 牌池概率模型(❌ 待做,PvE 单玩家,正确性-2)

**修正(r1)**:gameplay.md 明确这是 **PvE**(3 位面×6 关 vs 脚本 boss,"零和博弈"是赛季名非 PvP)。**没有"其他人"**,牌池只有你自己抽 → 牌池建模**更简单**(只跟踪自己 buy,无需推断他人)。

**方案**:
- **费用刷新概率表** `SHOP_REFRESH_TABLE: dict[int, list[float]]`(每等级出 1-5 费概率;meta,实机校准)。
- **牌池计数(review agent 校准)**:⚠️ **别套 TFT 的 29/22/18**(那是云顶/金铲铲多人池;货币战争是**单人 vs AI**)。按**统一 9 张/种**建模(5 费🟢确认,1-4 费🟡推测一致),做成可调 `POOL_SIZE_PER_CARD=9`,实机校准。bot 自己 buy 减 1;sell 是否回池需实机确认(通常不回)。**纯单玩家**。
- **1 星买卖无损 → 免费操纵牌池(review agent 🟢)**:卖出退金 1 星=招募费(=cost;2 星=cost×3、3 星=cost×9 🟡推算)→ **买 1 星(1 金)再卖(返 1 金)= 净 0、牌池 −1**。故"买目标卡**同费用**的其他 1 星卡 → 卖掉"可零成本消耗该费用池 → 目标牌刷新概率 ↑。这是 shop_strategy 该编码的战术(需 BenchChar 带 cost 字段做精确 sell_refund,A4 实现时补)。
- **采样顺序(r1 正确性-3)**:`_sample_shop` 改为**先按等级采费用(概率表)→ 再在该费用池里按角色均匀采**(角色→阵营反查,../data/characters.md 74 角色可用)。当前"先阵营后费用"高估小阵营。
- D 牌期望用真实概率表 + 牌池计数 → 更准;**牌池操纵**(买同费用非目标 1 星卡)在单玩家模型下成立且近乎免费。

## 通关能力 eval(成型度 + 装备,非邪道 gating;2026-08-03 修正)

**修正(用户实战经验)**:**邪道/cheese win-con 非必需** —— 之前被攻略带偏("A8 80 亿血必须靠物质分解液/反甲/仙舟神君邪道")。实际:**好好构筑阵容 + 找装备,很多阵容都能通关**,差别在**成型难度**(好不好凑)。boss 击杀 = f(阵容质量 + 装备 + 阵型),不是特殊邪道需求。**删原 `a8_context_score`(物质分解液/反甲/神君邪道 bonus) —— 不把"邪道持有"当强度关键项。**

**新方案**:eval 的"通关能力"用**通用 comp 质量**表达,不特殊化邪道:
- `comp_viability`(详 10)= 成型度(form_progress)+ **装备质量**(key_equips_owned,T0 装备如反重力皮靴/永动机等通用强装,详 07)+ 机制克制 + 观测。物质分解液/反甲/仙舟神君只是"可选的强阵容/强装备"之一,**不单独 gate**。
- COMP_LIBRARY(03)comp 的 `strength` 标**综合强度 + 成型难度**(用户强调:成型难度是关键维度),不标"邪道专打 A8 S"。运行时 select_comp 按场面选**易成型又够强**的。
- 物质分解液等"每回合叠加"的装备,若实机确认有超线性收益,在 `equip_fit(comp)`(07,**comp 相关**)按超线性(`count**1.5`)处理 —— 只对把这类装备列入 stacking_equips 的 comp 算分,不单独 A8-gate、不通用裸分。

**实测校准**:具体哪些阵容/装备在 A8 真能通关、成型难度排序,等实玩多局再校准(用户:实玩增强了解)。当前是"通用质量"框架,不预判邪道。

## A5 战术涌现(❌ 待做,依赖多步搜索,移阶段 5+,连贯性-1)

**修正(r1)**:A5 需多步搜索(凑整/牌池从 eval+搜索涌现),当前 A1 单步+蒜特卡洛不够。**A5 移到阶段 5+(多步搜索实现后)**,不放在阶段 3。阶段 3 只做 A4(牌池概率表,独立可做)。

## ~~aggression 用法~~(已删,2026-08-03 配置口重设计)
**`aggression` 已删**(README D:虚)。eval 的"侵略性"由 **comp 驱动**(level_plan/成型节奏)+ **tempo 例外**(连胜连败 streak/HP 危险破息)表达,不再用全局 aggression 旋钮。用户要影响节奏 → 走配置 4 轴优先/禁止/build_around + playstyle 预设(后续)。

## 蒙特卡洛稳定性 + 未校准鲁棒性(风险-5/6)
- **seeded RNG(r1 风险-5)**:生产用 seeded(如 `random.Random(round_num + plane*100)`),保证同局面确定性决策(可调试);k 提到 16-32 降翻转;边缘 delta(|delta|<ε)保守不 D。
- **未校准鲁棒性(r1 风险-6)**:LEVEL_UP_COST_TABLE/SHOP_REFRESH_COST/概率表 是占位。加**敏感性分析**(cost ±20% 决策是否翻转);实机校准优先级:升金价 > 刷新率 > 卖出回金。承认阶段 6 前数值是占位。

## round 2 补充(新发掘)
- **R2-4 连胜奖励 econ(med-high)**:gameplay 确认"连续获胜额外金币"+ research"断连胜亏的钱比利息亏多"。economy_score 加 `streak_val = min(streak, cap)·STREAK_WEIGHT`(需 read_streak);为"保连胜提质量"的 buy/deploy 加战术分。当前只算利息+等级,系统性低估保连胜。
- **R2-4b 连败经济 / open-fold 战术(r5 新增,high,auto-chess 核心盲区)**:当前 `is_losing_streak`(详 10)→ 转保守(保息/防御 deploy/急救 D)。**漏了连败也是经济**:auto-chess 连败也给匹配金,故意输攒钱后期 all-in 翻盘(open-fold)是核心战术。当前逻辑会在该认输攒钱的 plane1-2 反而花钱急救,把"连败翻盘"打成"又输又穷"。**修法(分阶段)**:
  - `is_losing_streak` 且 `hp > STREAK_FOLD_HP`(≈50)且 `plane < 3` → **继续连败攒钱**:不急救 D、不抢升等级、吃连败金 + 利息(守息至上),买牌只买能成型后翻盘的 key 牌(不为当前关提质量)。
  - `hp ≤ STREAK_FOLD_HP` 或 `plane == 3`(再输就死)→ 才急救 D 翻盘。
  - economy_score 加 `loss_streak_val = min(loss_streak, cap)·LOSS_STREAK_WEIGHT`(连败档位金);plan 的贪心在 fold 态降权"为当前关提质量"的 buy/deploy。
  - 这是 auto-chess 高手核心直觉,比调 eval 权重影响大得多。需 `read_streak`(连胜/连败档位,OCR)。
- **R2-7 可叠加关键装备的超线性收益(med,2026-08-03 去邪道化 + comp 相关)**:反重力皮靴/物质分解液等"每回合+15% 可无限叠加"的装备 → **早拿有复利**,不应 plane3-gate。`equip_fit(comp)`(07,**comp 相关**)对把这类装备列入 `stacking_equips` 的 comp(如昼神阿雅用反重力靴)用超线性(`count**1.5` 或复利 `(1.15)**count`),**随 plane 递增**(早拿复利、plane3 强化)而非 gate;别的 comp 持有同靴不算分。反重力皮靴("找鞋战争")对鞋队 comp 所有 plane 高分。**注:这些是"强装备"不是"邪道必需"**(见 02"通关能力 eval"修正)。
- **R2-17 延迟预算(low-med)**:每回合总延迟预算(OCR+reconcile+select_comp+蒙特卡洛 plan)+ 超预算降级(k=32→8→0、select_comp 缓存、跳多步)。备战阶段有时限,A8 不能超时。
- **R2-8 胜负反馈(med,2026-08-03 改观测驱动)**:原设想 crude `battle_predictor → (win_prob, expected_hp_loss)` 预测掉血 —— **改为观测**:`PerformanceTracker` 记每回合**实际**掉血/胜负(详 10),economy 用观测掉的血调保血阈值(动态 HP 预算替代静态 hp<40)。不预测,只反馈。

## round 3 补充(根本盲点:P0 + P1)
- **P0-1/2 → 观测驱动(2026-08-03 修订,详 10)**:eval 是"局面质量"proxy,不是"能否打赢/掉血",A8 核心是**战斗结果**问题 —— 这个反馈环成立。但**实现方式从"预测"改为"观测"**:不建 `battle_predictor`(精确战斗 sim 不可维护、版本敏感),改用 `PerformanceTracker`(每回合 OCR 掉血/胜负 → ground-truth 反馈)。保血/连胜/急救D/遭遇难度/升等级全用**观测到的掉血趋势**(`recent_hp_loss_trend`/`is_losing_streak`)动态调,替代静态 hp<40。comp 强度用 `comp_viability`(先验 + 观测)。**仍是 data→tactical 反馈环,但反馈来自结果而非预测**。
- **P0-3 eval 校准方法论(critical,改 06)**:eval 权重全程"占位待阶段 6 校准",但阶段 6 "iterate"是空的(无指标/搜索方法/判断标准;mock 用同 eval = 循环论证)。**方法论**:① 把 eval 权重做成**可拟合** —— replay 每局记 (eval 特征分解 synergy X/economy Y/char Z/target_progress W, 是否胜, 剩余HP) → 离线**逻辑回归/分位回归**拟合权重(推理纯代码,训练离线,不违"无 LLM");② 明确指标 `P(win|run)` + `E[HP at boss]` + 到达 round 分布;③ 参数搜索用 **bandit/贝叶斯优化**(高维权重手调不收敛)。replay(5.5)必须记 eval 特征分解(P3-1),否则没数据拟合。
- **P1-1 optionality_score / 灵活性(high)**:A8 是方差生存战,eval 只奖励 commit(target_progress 向单一 target 推进),不奖励**保持灵活性**。加 `optionality_score` —— bench 角色同时属于 ≥2 可行 comp 的数量(用 COMP_LIBRARY.shared_chars 反查);holding transition_chars 给正分;过早卖 shared_chars 扣分。与 target_progress 平衡(承诺 vs 期权)。这是 auto-chess 高手核心直觉。
- **P1-5 可叠加装备超线性(high,详 07)**:反重力皮靴每回合+15% 可无限叠加 → 早 commit 有复利。`equip_fit(comp)`(comp 相关)对把反重力靴列入 `stacking_equips` 的 comp(如昼神阿雅)用超线性 `count**1.5` 或复利 `(1.15)**count`,非线性 len;对没列入的 comp 不算分(同件装备 comp 相关)。

## round 4 补充(校准方法论统计根基 + 自洽性)

> **2026-08-03 哲学修订**:本节 F-1/F-2/F-7 是 **ML 训练管线**,降级为 **side door**(数据攒够可选,版本短命不值主线)。主线校准改为"手调 + replay 肉眼复盘 + 观测结果当指标"(详 06 阶段6)。**保留** F-3(α(t),非 ML)/F-4(确定性)/F-6(采集 telemetry)/F-10(risk/tail,观测驱动)。

- **F-1 off-policy 覆盖缺口(CRITICAL-for-convergence)**:校准链 replay(旧权重跑)→ 拟合新权重 是 off-policy 迭代,可收敛**前提是探索覆盖足够**。占位权重下 bot 只访问低质/单一 comp 状态 → 拟合权重对"好权重才到的强状态"(成型邪道/转型中段/plane3 高经济)零覆盖 → 外推失真。**修**:① 显式探索 preset(强制 K 套不同 comp 强绑 + economy_mode/aggression 各跑 N 局);② 覆盖度指标(replay 记 synergy_vector×plane×round 经验分布,拟合前断言各 comp×plane×阶段样本≥阈值);③ importance weighting / 分位回归(off-policy 修正);④ active learning(优先跑不确定性最高的状态)。
- **F-2 survival 分析替代二元胜(HIGH)**:`P(win|run)` 逻辑回归把"round5暴毙"和"round17惜败"当同样 label=0,浪费 90% 信号。改 **survival analysis**(Cox/AFT):label=(到达round, 是否通关)right-censored,"活得更久"显式奖励。或最低成本 `reached_round + 通关×bonus` 有序回归。
- **F-3 commitment-optionality 时间衰减公式(HIGH,r5 修 r_open;2026-08-03 用户细化备选数)**:`eval += α(t)·target_progress + (1-α(t))·optionality`;`α(t)=clamp((round-r_open)/(r_close-r_open),0,1)`,**r_open≈2**(r5:从 4 提前 —— 观测驱动需早 commit 才有可归因掉血信号,详 10"观测 vs optionality")、r_close≈12(plane2末必须commit)。**备选几套(N≈2-3)只要不影响经济,看哪个核心先到**(用户);核心到了(commit 信号 α 升)收敛到 **commit 1 + pivot 1**。**已知 tradeoff**:持多套时观测难归因(r6),commit 后 comp_tag 才清晰 —— 靠"核心到了尽早 commit"平衡。早 commit 产生观测、晚定型。
- **F-7 冷启动 meta 先验(MED-HIGH)**:首 N 局用占位权重 = 垃圾数据。把 research §10 meta(Top10 决策/推荐 comp 强度/阶段直觉)**显式编码为初始权重**(meta 先验待校准,非"占位")+ 首批跑探索 preset(F-1)保证数据有信息量。
- **F-10 risk/tail 意识(LOW,r5 降级)**:原设想 `risk_penalty=λ·max(0, P(未来3回合累积掉血>剩余HP)-τ)` 蒙特卡洛未来掉血分布 —— **砍战斗 sim 后无计算基础**(未来敌人类型会变,线性外推/历史位面经验都误估)。**降级为粗 tiebreaker**:用 `recent_hp_loss_trend` 线性外推 + 大方差,仅作"是否该守息降尾部死局概率"的弱提示,**不进主 eval**。"守息 vs all-in" 的理论根据(留 gold=买未来 flexibility)仍成立,靠 economy_score + optionality 体现,不需要精确尾部概率。
- **F-4 全链确定性契约(HIGH,详 04/05)**:replay A/B 对比要求整条 pipeline 确定(不只蒙特卡洛 seed):argmax tie-break、dict 迭代序、浮点比较阈值、post-action 重试。列非确定来源 + 固定 + determinism_check。
