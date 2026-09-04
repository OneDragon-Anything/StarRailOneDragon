# ADR 0098 · comp_viability 加 star 维度(star_achievement)

- **Status**: accepted
- **日期**: 2026-08-11
- **关联**: review round-4 HIGH-1(星级进 comp_viability);ADR 0097(streak/transition 等接线轮);commit `672aa838`(read_star);`cw_performance.comp_viability`

## Context(背景)

`comp_viability`(评 current 已 commit comp 可行性)先验 = 0.45·form + 0.30·equip + 0.25·mechanics,**缺星级维度**(review round-4 HIGH-1)。

货币战争限时 AV(行动值)机制下,**星级 = 输出能力**(2/3 星角色伤害更高)—— guides/阵容_ 攻略逐套标「核心追 2-3 星」(银枝必须 3 星 / 万敌 4-5 级追 3 星)。comp_viability 不含 star → 只有「成型度(form)+ 装备 + 词缀适配」,无「核心角色升星程度」→ 高星核心 comp 被低估。

信号就绪度:
- **bot 跟踪 BenchChar.star** 由 `simulate` 维护(`cw_state`:buy=卡星 + 3合1 → star+1),非恒=1。
- `read_star`(commit 672aa838)是 identify_slots 旁路(offline/漂移校验),**不进 bot 跟踪** —— comp_viability 用 bot 跟踪 star(GameState.bench/deployed),本就非恒=1,不需等阶段 4 OCR。

## Decision Drivers(驱动力)

1. **限时 AV 星级=输出**(review HIGH-1):高星核心 → 高输出 → 不超时。comp_viability 缺这维度 = 漏击杀侧。
2. **观测驱动非预测**:用 bot 跟踪 star(simulate 维护的真实升星),不预测战斗输出。
3. **先验 vs 观测归属**:star 是**阵容属性**(持有的核心升到几星),属先验(prior),非回合观测(obs)。form/equip/mech 同层。
4. **bot 跟踪 star 可信**:simulate 维护 buy 卡星 + 3合1 升星(主体路径)。read_star 旁路不参与(offline/漂移用)。

## Considered Options(备选)

### star_achievement 用哪个 star 源
- **A(选)**:bot 跟踪 BenchChar.star(`state.bench/deployed`,simulate 维护)—— comp_viability 评 bot 运行时态,star 源与之一致。
- B:read_star(identify_slots 旁路)—— read_star 不进 bot 跟踪(cw_identity_obs 设计:旁路 offline/漂移校验),comp_viability 用它 = 逻辑错位(评 bot 态却用旁路图)。否。
- C:新建 star OCR 读路径 —— 重复造轮子,bot 跟踪 star 已有。否。

### star_achievement 计法
- **A(选)**:核心角色(`char_id in comp.core_chars`)在 bench/deployed 的平均 star,归一化 `(avg−1)/2`(1 星=0 / 2 星=0.5 / 3 星=1.0)。无核心持有 → 0(早期未成型)。
- B:per-char star 加权进 char_quality —— char_quality 用 `character_priority`(用户偏好),非 star;star 是「升星程度」独立维度,混进 char_quality 语义错。否。
- C:只奖 3 星(阶跃)—— 2 星也是实质提升(输出翻倍级),线性归一化更平滑。否。
- D:star 进观测(obs)非先验 —— star 是阵容属性(先验),非回合结果(obs)。否。

### prior 权重重分配
- **A(选)**:0.40 form + 0.25 equip + 0.20 mechanics + 0.15 star(归一化 sum=1)。star 0.15(中等:低于 form 主项,高于纯调参;限时 AV 星级重要但不压倒成型)。
- B:从 form 大幅让(0.45→0.30,star 0.30)—— form(成型度)仍是最主(star 是成型后的强化),不让太多。否。
- C:加 star 不重分配(sum>1)—— 先验超 1 破归一化。否。

## Decision(决策)

采纳各 A:
1. `star_achievement(comp, state)`(cw_performance):核心角色 bot 跟踪 star 归一化(1=0/2=0.5/3=1.0),无核心持有 → 0。
2. `comp_viability` prior 加 `0.15·star_achievement`,权重重分配 0.40/0.25/0.20/0.15。

## 后果(占位待校准)

- **权重先验占位**(0.15 star / 0.40 form / 0.25 equip / 0.20 mech),**stage6 实跑校准**(客观指标 round/HP/胜负 驱动);值只在代码,文档写语义 + 指常量名。
- **star 可信度边界(2026-08-11 验完)**:star_achievement 用 bot 跟踪 star。调研确认:
  - bot 跟踪 star 来源 = buy(`ShopCard.star=1`,`cw_observation:403`)+ 3合1(`cw_state:231` simulate +1)。
  - **投资策略/巨星给的高星卡 bot 不模拟**(`decide_event:766` / `select_megastar:848` 只选策略/绑定角色,游戏自动给卡;bot 不跟踪给卡效果)→ bot 跟踪 star 漂移(漏这些高星卡,star_achievement 低估)。
  - **接受局限**:star_achievement 反映主升星路径(buy 卡星 + 3合1 玩家主动合);投资策略高星卡漂移被 **obs blend 部分纠**(`perf_for_comp` 实际掉血反映真实强度)+ 长期靠 `identify_slots`/`read_star` 旁路校验(offline/漂移恢复,设计上不进 bot 跟踪避免双写冲突)。
  - **不补 simulate**:投资策略效果 216 条各异 + bot 选策略时不知具体给哪张卡,模拟给卡 star 不切实;漂移是 bot 跟踪层固有问题(动作推演不含游戏自动事件),非 star_achievement 特有。
- comp_viability 冷启动(无核心持有)star=0,prior 较旧(0.625 vs 0.725)—— 早期未成型本就该低,合理。
