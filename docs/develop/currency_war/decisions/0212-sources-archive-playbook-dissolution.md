# 0212 · 外部存档层(sources)定名与 playbook 溶解归位

- **Status**: Accepted(2026-08-19)
- **Context**: 文档清理第四刀(前三刀:be62ed45 data 冗余 / 40798ce9 v0 死代码 / 122e3621 strategy 地层重建 + ADR-0210 真理模型)。遗留两处结构性错位:
  1. `guides/` 定位是外部攻略保真存档,但转录时混入我们的批注(代码指针/对账表/实现待办/bot 叙述),部分已指向被删文件(economy_research),存档不纯;
  2. `develop/currency_war/playbook/`(2026-08-15 建)定义为「进入我们策略的打法知识」,但**「进入策略」是状态不是变更驱动** —— 打法知识随游戏版本与证据变(= research 同驱动),不随代码架构变(≠ develop);以采纳状态做目录准入 → 内容随实现来回搬家 + 「改 COMP_LIBRARY 须同步改卡」的双向同步义务,腐化最快(建 3 天 ADR-0210 四禁 4/4 命中,README 目录表粘坏,§7-N 引用悬空)。
- **Decision Drivers**: ADR-0210 四禁与归位判据;用户定调「guides 存爬下来的原文,尽量原文、不改」+「playbook 放我们整理过、确认过、进入策略的内容」。
- **Considered Options**:
  - A. 保留 playbook 目录、清理状态标记 —— 否:准入条件仍是移动状态,腐化引擎还在;双向同步义务违反 as-built。
  - B. playbook 搬到独立顶层目录 —— 否:多一个目录不解决驱动错位,反而多一处归属判断。
  - C. **溶解归位(选中)**:打法卡本质 = 我们的玩法知识(research 同驱动、同证据分级循环),进 `game/currency_war/research/comps/`;「确认过/进入策略」降维为层的**策展规则**(只写有实战接触的 comp)+ 行级证据标签(`[先验:攻略]`→`[实战:ADR-NN]` 升格),不作为目录准入。
- **Decision**:
  1. **guides/ → sources/ 更名 + 保真剥离(一次性)**:目录名从内容类型(guides=攻略)改为层性质(sources=原始材料);剥净四类批注,只留来源元数据头(源链接/版本/日期/转录方式/已知 ASR 误差)+ 版本时效注;原文一字不动。保真纪律(元数据头标准/单向管线/提炼≠复制)入 docs/game/README.md「玩法知识分层」。
  2. **单向管线成文**:sources(原文,冻结)→ research(我们的,随证据更新)→ 注册表/strategy;认知演进只改 research 不回流存档;新版本素材 = 新文件进档,旧档不覆盖。
  3. **playbook 7 文件溶解**:5 张 comp 卡 → `research/comps/`(去四禁,证据标签保留);跨 comp 节奏教义(过渡体系/买牌纪律)→ `research/transitions.md`;「当前 bot 主 comp」类快照删(主选臂由 run_allocator 动态定,ADR-0170);维护约定被 game/README research 纪律覆盖。
  4. **大黑塔「导师阿雅流」裁定迁入**(自 playbook README,裁定本身不变):依赖未修 bug(银河学者经验统计把记忆召唤算入,攻略自标 ❌娱乐),不进 COMP_LIBRARY、不建打法卡;bug 修复前临时要玩见 sources 原文。
  5. **V3.7 公共三篇对拍提炼补缺**:已应用知识多数在 Cut 1-3 已进 research/注册表;缺口补 `research/combat.md`(伤害三乘区/星级/血量星/连胜经济)、`transitions.md`(P1 骨架/护航/买牌纪律);牌池副本「27/9 vs 30/25/18/10/9」版本冲突入 economy §1;投资策略品质→难度口径(必修一金+3/彩+6 vs 白银−3)入 economy §9 未决表。
  6. `cw_comps.py` 条目注释:打法卡路径改指 research/comps/(悬空的火花条目注释删);「改此条目须同步」义务删除(打法卡是游戏知识非字段镜像)。
- **影响面**:game/currency_war(sources 更名+剥离+README、research +comps/+transitions/+combat、economy §1/§9 补)、develop/currency_war(playbook/ 删除)、AGENTS.md 归位条措辞、docs/game/README.md 玩法知识分层节、docs/game/gameplay/currency_war.md 指针。冻结 ADR(0097/0098/0152/0210)中的 guides/ 旧路径留作历史引用。
