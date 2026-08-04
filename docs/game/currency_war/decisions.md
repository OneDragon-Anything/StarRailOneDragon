# 货币战争 · 决策日志(Decision Log)

> **试点规范(2026-08-03,暂仅货币战争)**:设计文档 = **干净的正文(strategy/)= what** + **本日志 = why**。
> 正文只讲"设计是什么",依据/备选/历史放这里,分开不混写。
>
> **格式**:append-only 按时间倒序(新决策加在顶部)。每条 `D-NN` 紧凑条目:
> - **决策**:一句话 what。
> - **为什么**:why(用户定调/实据/权衡)。
> - **备选**:考虑过什么、为什么不选(**最值钱的字段**,防后人重复扯皮)。
> - **状态**:采用/实验/推翻。反转用 `↺ 推翻 D-XX`。
> - `· §X` 反引到正文(strategy/0N 或 data/)。
>
> **粒度**:密度可变 —— 重磅架构决策多写,权重/数值一句话。不追求一决策一文件(决策多,奢侈)。
> 老条目不改正文(append-only);推翻就新写一条标 supersedes。

---

## D-23 (2026-08-04) EnterCurrencyWar wait_lobby 防御性加固(前往参与仍在→重点击)· 入口 op
- **决策**:`wait_lobby` 加分支 —— `前往参与` 仍在(transport click 没落地)→ `round_by_ocr_and_click` 重点击。放「创业指南」(大厅)之后、弹窗/F 分支之前。
- **为什么**:全流程跑卡 `wait_lobby` 重试 37x 失败,根因:停在指南页(「货币战争」分类 + 「前往参与」按钮都在)→ F 分支(`货币战争 AND NOT 前往参与`)被跳过 → 无分支命中 → 死循环。上个节点(前往参与)的 transport click 没落地(bug#1)→ 角色没传送 → 停指南页。重点击兜底。
- **备选**:① 提 node_max_retry(推翻:不解决根因,仍死循环);② 改 F 分支条件(推翻:不该在指南页按 F)。防御性重点击 = happy path 不受影响(传送成功则前往参与消失,分支不触发)。
- **状态**:采用(防御性加固;**需游戏验证** —— 下个干净对局跑 EnterCurrencyWar 看是否还卡)。`· 入口 op`

## D-22 (2026-08-04) hp 阈值统一 config.hp_safe_threshold(D-18 unification 落地)· strategy/02 §A3
- **决策**:加 `config.hp_safe_threshold`(默认 40 = HP_DANGER);`_phase_weights(plane,hp,hp_threshold=HP_DANGER)`、`_refresh_cap(state,hp_threshold)`、`maybe_pivot`(`0.75×threshold`)签名加参数带默认。evaluate/plan 经 `getattr(config,'hp_safe_threshold',HP_DANGER)` 传入。
- **为什么**:02 §A3 要求 hp 阈值单一源(原散落 `HP_DANGER=40` + `maybe_pivot hp<30` 硬编码);A8 高难需调高阈值(difficulty 派生)。**默认 = HP_DANGER → 行为不变**(64 测试绿),但单一源 + difficulty 可调 + 偏移系数集中(转型 0.75×;死局 0.5× / 连败 1.5× 待相应函数实现时补)。
- **备选**:① 直接删 HP_DANGER 全走 config(推翻:默认值仍 40,保留常量作 default + 测试引用更稳);② 不做(推翻:design 02 §A3 指示 + 审计标的 divergence)。
- **状态**:采用(D-18 hp 项落地;64+1 测试绿)。`· §02 §A3`

## D-21 (2026-08-04) optionality_score + α(t) 纯函数(承诺-期权)· strategy/02/03 P1-1+F-3
- **决策**:实现 `optionality_score(state)`(bench 角色属 **≥2 COMP_LIBRARY comp**[``shared_chars ∪ core_chars``]→ 加分,保期权/容错)+ `alpha_t(state)`(总回合 <R_OPEN→0 纯期权 / >R_CLOSE→1 纯承诺,线性)。R_OPEN/R_CLOSE/OPTIONALITY_WEIGHT **值在代码**(阶段 6 实玩校准)。
- **为什么**:A8 方差生存战,过早 commit 单一 comp 遇克/缺牌即死(plane2 死因之一);保 ≥2 comp 可行 → 容错。design P1-1/F-3 标 high。
- **备选**:① 直接集成进 evaluate(推迟:改核心 eval 行为需 P0 游戏验证才稳,先做零件);② 不做(推翻:high 优先 + 直接关系 plane2 生存)。
- **状态**:采用(纯函数 + 2 测试绿;**evaluate 集成延后** —— ``α·target_progress + (1-α)·optionality`` 混合,待 P0 解阻后集成 + 游戏验证)。`· §02/03 P1-1/F-3`

## D-20 (2026-08-04) decide_supply 纯逻辑骨架实现 · strategy/07/08
- **决策**:实现 `decide_supply(options, state, target_comp, config, refresh_used) → SupplyPick`(纯函数,design 07/08 骨架)。规则:带钻(红/蓝)→ 选(基本赢,碾压);全无钻 + 刷新未用 → 刷新找钻;刷新已用 → ``key_equips`` 契合(+10 命脉级)+ 通用装备价值(鞋>电池>花,``_EQUIP_VALUE`` 代码表)。新 ``SupplyOption``(idx/角色/装备/带钻)+ ``SupplyPick``。
- **为什么**:补给节点 naive「选中牌」(``handle_supply``)无视钻/key_equips;design 07/08。钻 = 拿到基本赢(用户),碾压;key_equips comp 相关(D-07)。先纯逻辑(可独立测),handler 接线(``read_supply_options`` OCR + 钻视觉判定)待阶段 5。
- **备选**:① 通用 equip_score(推翻:脱 comp 无意义,D-07);② 等阶段 5 OCR 一起(推翻:纯逻辑可独立测,符合先零件后整体)。
- **状态**:采用(纯逻辑 + 4 测试绿;handler 待 ``read_supply_options`` 阶段 5)。`· §07/08 补给`

## D-19 (2026-08-04) decide_encounter 纯逻辑骨架实现 · strategy/08
- **决策**:实现 `decide_encounter(options, state, target_comp, config, refresh_used) → EncounterPick`(纯函数,design 08 骨架)。规则:未成型→低难度;全分支词缀克 comp(``mechanics_fit``<0.4)+ 刷新未用→刷新换批;成型 + 词缀利 comp(debuff=buff)→高难度拿奖励;刷新已用→按最优选。新 ``EncounterOption``(idx/难度/词缀/奖励)+ ``EncounterPick``(idx/refresh/reason)数据类。
- **为什么**:遭遇节点 naive「选左」(``handle_encounter``)无法表达难度/词缀决策;design 08 标 high。词缀用 ``mechanics_fit``(debuff=buff,D-05)判克/利 comp。先做纯逻辑(阶段 2 骨架,可独立测),handler 接线(OCR ``read_encounter_options``)待阶段 5。
- **备选**:① 扩 ``decide_event`` 白名单(推翻:遭遇是难度档非白名单项,decide_event 表达不了);② 等阶段 5 OCR 一起做(推翻:纯逻辑可独立测 + 早发现 bug,符合"先零件后整体")。
- **状态**:采用(纯逻辑 + 4 测试绿;handler 接线待 ``read_encounter_options`` 阶段 5)。`· §08 遭遇`

## D-18 (2026-08-04) 配置层对齐:经济统一论落地后的取舍 · strategy/02 §A3 + README §A/D
- **决策**:① `economy_mode` **保留**(作 eval 权重微调:interest_first/rush_level 调利息/等级项),不按原 README §D 删除;② `aggression` **删除**(死字段,cw_decisions 不用);③ hp 阈值统一走 `config.hp_safe_threshold`(02 §A3)+ config 重写(forbid/build_around/handoff/difficulty/manage_meta_run)**缓做**(deferred)。
- **为什么**:① level_plan 是**硬 gate**(D-14,主导花费指令),economy_mode 只调 eval 权重(非花费决策)→ 二者**不冲突**(原 README "和 level_plan 打架"的删除理由在 hard-gate 落地后不成立);且 economy_mode 有测试锁定(test_economy_mode_effects),删 = 行为变更 + 破测试,无收益。② aggression 全代码不用,设计早判"虚"已删,代码残留。③ hp 统一 / config 重写是干净但触及 `_phase_weights` 签名 + 测试 + GUI 的重构,非"修漂移",单列任务。
- **备选**:按原 README §A/D 全删 economy_mode/aggression + 一次重写 config(推翻:① economy_mode 删除理由失效;② config 重写大,且 cw_comps 已 `getattr` 防御读取新字段,可增量加不必一次重写)。
- **状态**:采用(①② 已做;③ deferred,见 process_log/insights)。`· §02 §A3 / README §A/D`

## D-17 (2026-08-04) eval / comp_score 权重实跑校准 · strategy/02 §A3 + 03 comp_score
- **决策**:V4.4 research 先验权重经 2026-08-04 实跑(replay 32 局 + bot)校准:`INTEREST_WEIGHT 2→4`、`LEVEL_WEIGHT 3→6`、`SYNERGY_TIER_EXPONENT=1.5`(收敛:深化 delta>散新)、`OFF_TARGET_DISCOUNT 0.3→1.0`(revert,改用 commitment prefilter D-15)、`W_PROG 0.35→0.45` / `W_STR 0.10→0.05`(select_comp 偏好可成型而非纯高强度)、`TARGET_PROGRESS_WEIGHT=15`。
- **为什么**:实跑发现原值致 bot 不攒金(息 delta = 牌 synergy → 无差别买)、不升等级(level benefit < interest loss)、select_comp 锁高强度但不可成型 comp(列车同行 S 但商店没牌 → 不收敛)。提权后 bot 攒到 50 + 升级 + 选可成型 comp。
- **备选**:维持 research 先验占位值(推翻:实跑证明不收敛)。阶段 6 再用 replay 精调最敏感 3-5 维。
- **状态**:采用(实跑驱动,待阶段 6 replay 精调)。`· §02 §A3 / §03`

## D-16 (2026-08-04) shop_supply:select_comp 降权不可得 comp(task#25)· strategy/03
- **决策**:`select_comp` 对核心阵营在当前 shop/board **不可得**的 comp ×0.3 降权(新 helper `shop_supply`)。
- **为什么**:实跑发现 select_comp 锁高强度 comp(列车同行 S=1.0)但商店刷不出其牌 → board 散、永不成型 → plane1 重伤。降权使 select 偏好**可得** comp(万敌 燃血:1 > 列车同行 0 可得)。
- **备选**:① 纯按 comp_score 不考虑可得性(推翻:锁死不可成型 comp);② P1-2 `ENV_COMP_AFFINITY` 硬绑(更强形式,待实玩补全 T0 env 表)。
- **状态**:采用。`· §03 select_comp`

## D-15 (2026-08-04) commitment prefilter + OFF_TARGET_DISCOUNT revert(task#16)· strategy/02
- **决策**:target_comp 设定时,`_best_improving_action` 用 **prefilter** —— shop 有 target 卡(阵营∈target.factions / ∈core_chars)可买时,跳过纯 off-target 散牌(**只 gate 新 buys,不动已持有 board 的 eval**);`OFF_TARGET_DISCOUNT` revert 0.3→1.0(不打折 board synergy)。
- **为什么**:原 OFF_TARGET_DISCOUNT=0.3 打折 board synergy 致 bot 卖成型 off-target 深堆(churn)= regression。prefilter 只影响"买什么新牌"不影响"已堆的怎么评分"→ 聚焦深化 target 且不破坏现有 board。target_comp 参数保留(prefilter 复用,OFF_TARGET_DISCOUNT effect 暂关)。
- **备选**:① OFF_TARGET_DISCOUNT 打折 board(↺ 推翻,致 churn);② 无 commitment(纯 reactive,不聚焦)。
- **状态**:采用。`· §02 commitment`

## D-14 (2026-08-04) level_plan 从"导向"升级为"硬 gate"(task#18)· strategy/03 经济统一论
- **决策**:`plan()` 中 level_plan `action="level_up"` + 够钱 → **直接执行 LevelUp**(每轮 ≤1 级),不进贪心 eval 候选。语义从 D-08 的"导向(eval 权重)"升级为"**花费指令(directive)**"。comp 无 level_plan 时退回通用曲线 `_DEFAULT_LEVEL_GOAL`。
- **为什么**:replay 32 局「升 0 次」根因 —— 贪心 eval 对"花大金升级"的利息损失短视:LevelUp 候选 delta 永负(花 48 金 → 利息档 5→0 损 -20,level_val 仅 +6)→ 永不选中 → bot 卡 lv5-6 → 弱 comp → plane2 死。level_plan 说升 + afford → 信任计划而非短视 eval。tempo 破息在所不惜(升级 = 解锁高费刷新率 + 出战位,关键长期投资)。
- **备选**:① 仅提 LEVEL_WEIGHT 让 eval 自发选升级(部分采用 D-17 提 3→6,但单靠 eval 权重不够稳,hard gate 兜底);② 每 comp 手填 level_plan(保留:comp 有则优先,无则通用曲线兜底,保证所有 comp 有合理经济行为)。
- **状态**:采用。`· §03 经济统一论 / §02 plan`

## D-13 (2026-08-03) 击破 tiers V4.4 修正 2/4/6/9 · data/factions
- **决策**:`击破` FactionInfo tiers 用 `(2,4,6,9)`(原 `(2,4,6,8,10)`)。
- **为什么**:官方赛季文 76641553,V4.4 姬子成专家顾问,tiers 下调。
- **备选**:无(实据,非权衡)。
- **状态**:采用。

## D-12 (2026-08-03) 领域模型注册表 + 单一真相源派生 · 工程化
- **决策**:核心实体建正规 model 类 + 注册表(Character / Faction / Equipment / InvestmentEnv+Strategy);派生关系而非硬编码 —— `ENV_FACTION_MAP`←`INVESTMENT_ENVS.faction`、`DISTINCT_CARDS_PER_COST`←`chars_by_cost`、`Faction.members()`←`CHARACTERS` 反查。
- **为什么**:用户定调工程化质量,别写屎山;单一真相源改一处自动传导(否则多处硬编码易脱节)。
- **备选**:裸 dict + 散字符串(推翻:重复硬编码,改一处要同步多处)。
- **状态**:采用。

## D-11 (2026-08-03) 观测 trend 归一化而非完全划分 · strategy/10
- **决策**:`recent_hp_loss_trend` 用 `hp_delta / expected_drop[node_type]` 归一化,全部样本进**同一条** trend(不按 node_type 完全划分);boss 另留短 trend。
- **为什么**:review r5 的"完全划分"致 boss 观测永久 None + obs 随节点类型震荡;归一化既消除"打 boss 掉得多=我弱"偏差,又不丢样本。
- **备选**:按 node_type 完全划分(↺ 推翻 r5 过度修正;boss 稀疏 + 震荡)。
- **状态**:采用(r6 修 r5)。

## D-10 (2026-08-03) comp_viability 冷启动早返回纯先验 · strategy/10
- **决策**:obs=None(无观测)时直接返回纯先验,不 blend。
- **为什么**:`obs_weight × obs`(0×None)会 TypeError 崩溃;且无观测时纯先验就是最佳估计。
- **备选**:用先验填 None 再 blend(多余,先验已在公式里)。
- **状态**:采用(bug-driven,测试发现)。

## D-09 (2026-08-03) 列车同行(姬子·启行)= bot 默认首选 comp · data/comp_library
- **决策**:V4.4 列车同行 comp 作 bot 默认首选(strength S)。
- **为什么**:A850 挂机流攻略(76824096):"全程自动、不凹开局、适应任何负面环境" —— 完美适配 bot。V4.4 评级真神。
- **备选**:昼神阿雅(已降 B)/命运圣杯红A(S 但联动获取门槛)。
- **状态**:采用。

## D-08 (2026-08-03) 经济统一论:level_plan 驱动超额金 · strategy/03
- **决策**:D牌/买牌/买经验是"花钱的一环",非三件事。维持 ≥50 金(息引擎),**超额(>50 不生息,免费)该花**,花哪由 `target_comp.level_plan[当前等级]` 决定(level_up/roll/stable);tempo(连胜连败/HP危险/战力断档)例外破息。
- **为什么**:用户框架 —— 超额的钱白该花,花哪由成型路线导向。
- **备选**:D牌/买牌/买经验三件独立决策(推翻:割裂,忽略超额金的"免费"性)。
- **状态**:采用。**接法已落地**(`plan` level_plan 硬 gate[D-14] + `select_comp`/`maybe_pivot`[cw_comps] + shop.py 接线;2026-08-04)。

## D-07 (2026-08-03) 一切评分 comp 相关 · strategy/03/07/10
- **决策**:装备/巨星/词缀好坏都挂钩 `target_comp`(`equip_fit`/`mechanics_fit`/`select_megastar`),不设独立绝对评分项。
- **为什么**:反重力皮靴对昼神阿雅(需2靴)是命脉、对别 comp 不一定;知更鸟幸运一击只对暴击队值钱;正当防卫对阿雅是克、对万敌燃血是利。
- **备选**:通用 equip_score + 通用词缀表(推翻:脱离 comp 的绝对评分无意义)。
- **状态**:采用。

## D-06 (2026-08-03) V4.4 阿雅 strength S→B · data/comp_library
- **决策**:V4.4 昼神阿雅 comp strength B(V3.8 曾标 S "最轮椅")。
- **为什么**:米游社合集 76807134 V4.4 评级(试用+0命),阿雅降 B —— 需反重力皮靴×2+速度投资,试用/0命下难成型。
- **备选**:保留 S(与 V4.4 实测 meta 矛盾)。
- **状态**:采用。↺ 推翻 V3.8 "最轮椅 S" 先验。

## D-05 (2026-08-03) debuff 可能是 buff(mechanics_fit 双向)· strategy/10
- **决策**:敌人词缀对 comp 是 counter 还是 synergy,**双向判**(同一词缀对不同 comp 方向相反)。`comp.mechanic_attributes` + 全局 `MECHANIC_COUNTERS`/`MECHANIC_SYNERGIES`。
- **为什么**:正当防卫(反伤)对高频队是克、对燃血队(万敌)是利(反伤让燃血掉血→角斗场记录→伤害更高)。但**永久创伤**(掉血减上限)**克**燃血 —— 反例,故燃血非"所有掉血都利"。
- **备选**:通用高危词缀表(推翻:同词缀不同 comp 方向相反,通用表错)。
- **状态**:采用。

## D-04 (2026-08-03) 持久化/跨局状态默认不碰 · strategy/09
- **决策**:bot 默认**不动**玩家跨局继承(优势布局/钻钞);`manage_meta_run=false`。仅**局内**状态(买/deploy/升/D牌)默认自动。
- **为什么**:防打乱玩家长期投入(优势布局是玩家自己攒的 buff);持久化破坏性操作 opt-in。
- **备选**:默认自动激活最优布局(推翻:风险大,可能毁玩家投入)。
- **状态**:采用。

## D-03 (2026-08-03) 不凹开局重开 · strategy/09
- **决策**:策略**不依赖重开**找好开局;够好就该能"理智"克服任何开局。
- **为什么**:重开是玩家行为不是策略;策略鲁棒性应内含,不该靠重开掩盖。
- **备选**:opening reroll(推翻)。
- **状态**:采用。仅 `handoff=true + 好开局`用例保留"刷好开局交手玩家"。

## D-02 (2026-08-03) 邪道非必需(通关=成型度+装备)· strategy/02/03
- **决策**:不把"邪道装备/特殊 win-con"(物质分解液/反甲/仙舟神君邪道)当 comp 强度关键项;通关能力 = f(成型度 + 装备质量 + 阵型),差别在**成型难度**。
- **为什么**:用户实战 —— 好好构筑阵容+找装备,很多阵容都能通 A8;被攻略带偏("A8 80亿血必须靠邪道")。
- **备选**:标"邪道 A8 专项 S"(↺ 推翻;与实战矛盾)。删 `a8_wincon_holdings`。
- **状态**:采用。

## D-01 (2026-08-03) 砍精确战斗模拟器 + ML,改观测驱动 · strategy/01/10
- **决策**:**不建**战斗模拟器(打前预测赢率/掉血),**不建** ML 训练管线;改用 OCR **观测结果**(每回合掉血/胜负/boss血条)当反馈信号。
- **为什么**:星铁战斗太复杂(回合序/弱点/击破/能量/战技点)OCR 反推不出可信模型;且版本迭代改数值,预测模型会废、维护不起。结果信号扎根在结果上,版本鲁棒。用户定调"像人一样玩"(人看掉血,不算赢率)。
- **备选**:① 精确 sim(推翻:维护成本极高 + 版本废);② ML 训练(推翻:训练价值版本短命,V4.4 训的 V4.5 废);③ 粗可行性启发式(**保留**为 comp_viability 先验,非预测)。
- **状态**:采用。ML 只采集(debug telemetry 序列化决策迹),**不主依赖**。
