# 01 姿态与经济(跨期决策)

> 「钱该花还是攒、什么时候升、什么时候刷」由 **DP 求解器统一回答**,不再有手写的节点节奏表(历史:静态 NodeGoal 表 → DP 切流,ADR-0208;等级节奏权威 = 用户口述,ADR-0126/0128)。本篇:`cw_horizon` / `cw_effect_ledger` / `cw_economy` / `cw_first_passage` / `cw_progress_curves` 的语义。

## 1. cw_horizon:DP 姿态引擎

**是什么**:离线一次性解出的「花钱节奏手册」——对(节点 × 金 × 等级 × 血 × 板强)全状态组合逆向递推,求每状态最优**姿态**;运行时 O(1) 查表。它是全系统唯一做跨全节点(`cw_horizon.TOTAL_NODES`)全局权衡的器官:战术层只看单步,它看「现在省的 50 金到 P3 值多少存活率」。

- **状态空间与递推**:维度与常量(`NODES_PER_PLANE`/`GOLD_MAX`/`LEVEL_MIN·MAX`/`HP_BUCKET`/`RB_STEPS`)见模块头部;金步长为 1(日程 +1/+2 金不得被量化蒸发,ADR-0202);掉血模型 = 板强线性插值 × 难度缩放的**期望近似**;终值含存活奖励 + 金/级/血残值(无血残值会系统性欠升级,V1.1 教训)。
- **姿态空间**:8 个「升?× D0/D2/D4/D6」组合,动作码 int8;`posture()` / `value_at()` 为唯一生产查询口(值/动作表是紧凑数组,`policy`/`value` property 仅为旧测试兼容的惰性物化)。
- **消费端**:`cw_economy`(spend_mode 档位)、`cw_comps`(node goals)、`cw_evaluate`、`cw_plan`、`cw_state`、`cw_telemetry`(影子记录)。
- **效果感知注入**:持有效果改变世界规则时(息 cap / 单击价 / 连胜乘子 / 节点日程)按台账指纹重解(ADR-0202);纯时点金不改变指纹不重解。生产当前查「无效果」基线解,效果解切流由发布层控制。
- **缓存**:解级内存缓存(按台账指纹 memo,同指纹二次调用即时);求解为 numpy 向量化实现;改头部常量后直接重跑即可,无缓存文件需要管理(缓存键含依赖文件内容哈希,改动自动失效)。
- **改常量 checklist**:① 改模块头部常量 → ② 跑模块自带涌现验证(行为对拍锚 = plaza meta 带,band 大幅变化要能解释)→ ③ 全量测试。敏感历史:单击经验价曾因取值过贵导致全路径值坍塌(注释在常量处)。
- **维护红线**:无 ledger 的基线解必须与历史基线逐 posture 一致(零漂移锚,集成测试锁定)——它是离线 A/B 报告的可比性根基。

## 2. cw_effect_ledger:既持效果台账

把「已持有投资卡的效果」从摊平的等效息恢复为**结构化三层**:现金日程(calendar)/ 机制突变(mutations)/ 免费额度(budgets),按四象限路由(时点金/规则改/选卡权/资产)。`cw_horizon` 与 `cw_telemetry` 消费(注入重解 + 指纹记录)。效果分类知识与可建模边界 → [game/research/invest_effects](../../../game/currency_war/research/invest_effects.md);落地与纠错 → ADR-0202/0205。

## 3. cw_economy:经济纯函数层

金/经验/息/刷新成本的纯函数模型(三层共享底层,economy/evaluate/plan 均消费):单击经验模型(单击 XP 常量 `XP_PER_BUY`、门槛自动升级溢出结转,ADR-0129)、重复性效果折算(ADR-0142)、spend_mode 档位(由 DP 姿态导出,**唯一档位源**)。

## 4. 息引擎与例外窗口(语义)

基线是用户口述的人玩节奏(权威,[game/research/user_playstyle](../../../game/currency_war/research/user_playstyle.md)):

- **50 金息引擎**:利息(息律常量 `INTEREST_THRESHOLD`/`GOLD_CAP_INTEREST`,用户口述「每 10 金 1 息、50 封顶」)是默认态;前期 snowball 到 50,中期维持吃息升人口,后期血危花光。
- **无损购买窗口**:金低于无损窗口上限(`cw_plan.NO_LOSS_GOLD_CEILING`;1 息档内)买过渡件不损息还压缩牌库——攒息不拦无损买。
- **连胜破息门**:连胜 ≥ `WIN_STREAK_BREAK_INTEREST` 时破息提质量维持连胜(断连胜亏 > 利息亏,ADR-0117);货币战争**无连败补偿,只计连胜**(ADR-0128)。
- **奖励节点守卫**:必胜节点(无战斗/连胜白拿)刷牌的战斗向理由全关(`_refresh_cap` 收紧)。
- **血量换经济边界**:血危时经济让位保血,但保留重生基数(`line_strategy._REBIRTH_FLOOR`)。

## 5. 压缩买链(1 费免费牌池操纵的执行语义)

地基:1 星买卖净 0、1 费 2 星合成再卖也净 0(cost≥2 才有 1 金手续费,`cw_state.sell_refund`,ADR-0121)→ **1 费各星 = 零成本压缩牌库**。plan 中的压缩买链(`_compress_release` 纯函数 + 扫尾)按此买同费非目标 1 星卡压缩分母、目标到手后再释放。量化幅度与前提 → [game/research/economy §3](../../../game/currency_war/research/economy.md)。

## 6. cw_first_passage:目标函数层

全栈优化目标的单一源:**首达生存概率**(P(reach plane_k) / P(win))+ 风险姿态三区律——替代各处各自为政的「均值计价」(诊断与设计 → ADR-0161)。`cw_state` 消费;P(win) 供给跨局分配层。

## 7. cw_progress_curves:期望进度线

「健康线在节点 t 应有的等级/板强」期望侧基准编译器(ADR-0171),供 `cw_line_tribunal` 的「时间线掉队」通道做对照。

## 8. 边界

- **不预测战斗结果**:掉血模型是期望近似(升级方向 = 换实测桶分布,属设计演进,决策时另立 ADR)。
- 姿态回答「花钱节奏」,**不回答**买哪张/上谁(战术层,03)。
- 电表倒转(砂里淘金)流与优势布局钻钞 farming 不建模(ADR-0211)。
