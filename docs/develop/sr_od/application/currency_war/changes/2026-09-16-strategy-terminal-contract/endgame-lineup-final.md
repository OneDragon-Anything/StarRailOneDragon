# 终局阵容定版(目标 2「选出终局阵容」承载件)

> 本文档 = 迭代内工件(寿命 = 本迭代),汇总现行代码注册、玩法文档、sim 报告与实机现状,给目标 2 的定版结论。
> 定版内容的长期单一源:玩法知识 = `docs/game/currency_war/research/user_playstyle.md`(条目
> [21]/[23]/[36]/[37]/[38])与 `docs/game/currency_war/research/final_comps/`(逐家族打法);
> 代码注册 = `src/sr_od/application/currency_war/kernel/cw_comps.py`(COMP_LIBRARY)、
> `kernel/cw_intention.py`(锁线状态机)、`kernel/cw_recipe.py`(决策目标单一入口)、
> `knowledge/cw_line_facts.py`(线事实,含花火量子线修正);测试锁 =
> `sr-od-test/test/sr_od/application/currency_war/test_cw_framework_decision.py`。
> 本文档不作长期引用源;下文代码路径省略前缀 `src/sr_od/application/currency_war/`。

## §1 定版结论

**定版性质:本结论定的是「机制上的终局阵容选择」——注册面(候选全集 + 成型判据 + 信号锁定)与锁线机制的现行契约,不是「实证最优阵容」**。位面 3 实证最优的验收归进度账本条目 T-12(终局阵容实机通关位面 3,凭据 = 对局档案 + 复盘结论;账本 = `.debug/progress/2026-09-16-strategy-terminal-contract/dag.jsonl`),见 §3。

### 1.1 候选全集、主口径与备选

- **候选全集 = COMP_LIBRARY(`kernel/cw_comps.py`,20 套)**:v2 家族 12 套(9 家族:姬子列车/圣杯双C/希儿量子/黄泉减益/DOT卡芙卡/欢愉族/大黑塔群攻/白厄反甲/万敌燃血)+ legacy 长尾 8 套(保活不删,但不进锁定候选集——候选线集 = 9 个 v2 家族载体,`cw_intention._v2_comps`)。
- **主口径(注册面默认首选)= 列车同行**(姬子列车家族):注册评级 S 级/成型 easy/前期强度高,依据 = ADR-0152(plaza 784 篇校准:carry 274/在场 358 篇断层第一)+ A850 挂机流口径(全程自动/不凹开局/适应负面环境 → bot 默认首选;COMP_LIBRARY 条目注释)。成型形态 = 8 人口:前台 姬子·启行+花火+瓦尔特+记忆主,后台 三月七+刻律德菈+千冶·刃+符玄/缇宝;家族打法知识 = `docs/game/currency_war/research/final_comps/final_jizi_train.md`。
- **备选 = 其余 v2 家族载体按注册评级参与评分**:命运圣杯红A(S/medium;圣杯任务链产出 carry)、希儿量子(A/medium/前期高;成型判据 = 希儿在场 ∧(量子同频≥2 ∨ 贝洛伯格≥2),常量 `SEELE_OR_LEGS`)、万敌单C(A/medium;全局累积型,上场例外见 1.4)、大黑塔银河学者(A/medium;低档通关是常态)、双王圣杯(A/medium;能量 5 为硬约束)、DOT队(B/easy;`weak_planes` 自注位面 2 = 弱面不产锁线信号)、黄泉减益(A/medium)、绯英欢愉/狼尊欢愉(欢愉族双档,资源锚 6/9 级分流)、反甲白厄(A/hard)。择线权重语义 = user_playstyle [38]:候选默认等权,攻略热度/帖子数永不入权,环境分化只走机制层知识,用户口述最高权威。
- **主口径的准确含义**:「默认首选」是评分先验与兜底偏好,不是每局预设目标——实际锁线由贯穿件信号驱动(1.3);「拿到什么贯穿件走什么线,被锁定的选择不是 pivot」(user_playstyle [23])。

### 1.2 定型判据(「终局线已定型」谁说了算)

决策中心取目标线的单一入口 = `kernel/cw_recipe.py` `decision_target`;定型权威 = `kernel/cw_intention.py` `committed_authority`(唯一合法读端 `committed_from`),两分支任一成立即定型:

1. **分支① 位面 ≥ 2**:进位面 2 起恒定型(定型边界 = 进位面 2,严于玩法文档 P2-P3 分段口径);
2. **分支② 锁线态**:意向状态机 `phase == 'locked'`(P1 内证据门已锁线同样成立)。

两分支有测试锁:`test_decision_target_committed_returns_terminal_line`(两分支同返回 target_comp 本体)与 `test_decision_target_recipe_in_dual_track`(双轨期配方伪 comp/散件口径),见 `sr-od-test/test/sr_od/application/currency_war/test_cw_framework_decision.py`(账本 T-16 锁)。

边界说明:committed 分支返回的 `target_comp` 在不同帧位物化对象不同——P1 配方锁帧物化为配方对伪 comp(`strategies/impl/flow.py` `_refresh_direction_views`,经 `pair_target_comp`);位面 2+ 与 comp 锁帧物化为 COMP_LIBRARY 终局套本体。另 `committed_authority` 权威序还有第三形态:P1 配方锁产物 `p1_pair` 非空亦计定型(ADR-0357 产物形态),本文定型判据按契约两分支表述。

### 1.3 锁线机制(终局线怎么被选中)

- **证据门 = 贯穿件信号**:家族专属羁绊信号(注册表 = `Comp.bond_signal` 字段,从 COMP_LIBRARY 派生;如 列车同行 = 列车同行四人 100% 固定、命运圣杯 = 2 档开任务)命中即产锁线信号。线级选择全局仅一次(user_playstyle [36]:未定型期决策单位是「件」,终局证据门是唯一线级选择;[23] 的形式化)。
- **强制锁线兜底**:未锁线进位面 2/3 入口时强制锁线,对象限定 = 核心已在手 ∨ 再遇窗口期望 ≤ 剩余节点数(`cw_intention._core_reachable`);全不可达时降格终局(`demoted_endgame`,吸收态「赢不了就少输」,不回弹)。
- **弱面过滤**:注册表 `Comp.weak_planes` 自注弱面位面,该线在弱面位面不产锁线信号(如 DOT队 位面 2「被抽陀螺,保命 pivot 不选」)。
- **锁后出口**:miss-N 撤销 / 高层信号改锁 / 驱逐(evicted)→ 弱意向跨线骨架;P1 内终局线冻结换线(定义型强化除外,`cw_recipe.py` 模块不变量);出 P1 后锁定目标 = `locked_comp` 唯一(过渡对副方向退场)。

### 1.4 与过渡线的衔接(过渡 → 终局切换时机语义)

1. **P1 双轨期**:板面(买/上/卖)由过渡配方驱动(框架已定 → 配方伪 comp,仙舟/列车/量子三选一,`cw_recipe._RECIPES`;框架未定 → 终局套散件口径);终局件「买而不上」(user_playstyle [21]:囤备战席,上场窗口 = **该角色的羁绊组齐了才上**,不是孤立等级/进度数字;全局累积型角色例外——技能跨节点累积越早越好,如万敌燃血,且需特定环境才选)。
2. **切换时机(两臂)**:①P1 内证据门锁线先至 → 决策目标立即切终局套;②未锁进位面 2 → 硬边界恒定型,未锁线由入口强制锁线兜底(1.3)。
3. **完成度口径**:定型后的缺口账单按「下一成型档位」算(user_playstyle [37],档位 = `COMP_LIBRARY form_tiers`),不是全终局目标态一口账——否则完成概率读数系统性偏低、定型门过晚开。
4. **量子线恒等衔接**:量子过渡配方 = 希儿量子终局套的雏形,定型时转变成本 ≈ 0(`cw_recipe.py` 量子条目注);花火 = 量子线成员(`knowledge/cw_line_facts.py` 修正后口径:花火阵营 = 盛会之星、无列车阵营,过渡/终局贡献走量子同频流派成员口径;计数归属由同测试文件 `test_framework_counts_owned_vs_merged_semantics` 钉住)。

## §2 证据与缺口

### 2.1 已证面(相对强)

- **机制面(代码 + 测试锁)**:定型权威两分支、决策目标单一入口、锁线状态机(锁定/撤销/强制锁线/降格终局/弱面过滤)均有现行实现与测试锁覆盖(`test_cw_framework_decision.py` 四符号锁)。「机制上的选择契约」成立。
- **知识面(攻略统计校准)**:COMP_LIBRARY 手判层校准自 ADR-0152(plaza 784 篇)+ V4.4 权威评级;终局家族打法逐篇在册(`final_comps/`);过渡与终局的分界有数据实证——`transition_combos.md`:四体系都不含的 49 帖全为直通线(carry 单卡自带输出),无通用羁绊组合过位面 1。
- **sim 就绪面(P1 末对终局线的准备度;两份找问题报告,均为 P1-only 载体)**:
  - 旧引擎批(`.debug/temp/currency_war/sim_find_issues_20260918_030035/report.md`,n=300):终局阵容完成率镜像口径 96%,按帧末口径修正后 97.7%(4 局为观察帧滞后假阴性);出口金中位 122.5。
  - 新引擎批(`.debug/temp/currency_war/sim_find_issues_20260918_034938/report.md`,n=1000):全体局凑齐率 82%(带配方对分母 ≈89.4%);带对死亡 90 局中 79 局只差一件、其中 20 局死时手握 60-92 金——付费刷新全批零开火(R1 全阵容买齐总账结构性封死搜索通道);77 局末行无配方对,其中 28 局曾锁对后丢失且无重锁通道。
  - 这两条属于「过渡 → 终局就绪」的缺陷面,不是终局阵容定义本身的反证(同判定见同目录 `transition-lineup-final.md` §2)。

### 2.2 弱证面

- **终局位面(位面 2/3)决策面:sim 零覆盖**。两批 sim 均为 P1-only 载体(位面 ≥2 未建模),通关率 0 属载体辖域;锁线机制里与位面 2/3 相关的判据(强制锁线的再遇窗口账、`weak_planes`、降格终局)没有任何 sim 证据。
- **sim 战斗/星级面是粗模型**:701/1000 局 P1 中途死亡、末行 hp=1 占 891 局、死亡局中 556 局配方其实已凑齐(成型但全 1★——星级未建模)——hp/死亡面按在册裁定(sim-testing,2026-09-09)禁作判据,只作边界观察。
- **历史实机终局线样本属旧机器世代**:`.debug/currency_war/telemetry/live/runs.jsonl` 中 8 月世代有 committed 终局线(列车同行/希儿量子/DOT队/双王圣杯/万敌单C 等),均出自旧策略核,不能作现行机制(mandate_v1 + 现行锁线状态机)的实证。

### 2.3 证据缺口

- **实机未达位面 2(现行机制下终局线 committed 零样本)**:今日实机局均未达位面 2+(编排者给定口径);runs.jsonl 末次走满 P1 的完整局 `run_20260911_043101` 仅 committed 过渡配方(仙舟+持续伤害),无终局线 committed 记录。
- **位面 3 合成质量面当前不可信**:同名多星星级判读抖动污染 3★ 合成判断(进度账本条目 T-35,已立项未修;账本路径同 §1)——位面 3 的合成/星级相关证据在 T-35 修复前不作依据。
- **结论重申**:本定版 = 「机制上的终局阵容选择」(注册面 + 锁线契约),不是「实证最优」;实证最优的验收载体 = T-12 里程碑(位面 3 实机通关,凭据 = 对局档案 + 复盘结论)。

## §3 风险与待裁

三项编排者待裁项(同目录 `transition-lineup-final.md` §3 已申报「不在定版内」),对本文定版的影响面逐项界定——三者均**不改变「终局阵容是什么 / 怎么锁」的定版本体**,只影响终局线的**获取/装备/囤货支撑面**:

| 待裁项 | 内容 | 对本定版的影响面 |
|---|---|---|
| E9 切换 | 专家邀请函解锁判据分叉:实码 = 在场浓度版,在案规格 = 目标线成员优先版(本迭代 `design.md` 已知分叉挂账行;规格源 = strategy-docs `13_pick_family.md` §2 / `08_events.md` E9 行) | 影响终局件获取通道的定向度:若切换规格版,锁线后邀请函解锁定向服务 `locked_comp` 成员;锁定机制与候选集零变化。切换对成型速度的影响未量化,归后续 sim/实机验证 |
| 泛用腿并轨 | 装备选择锁线态(锁定线 key_fit 命中 +100 压倒泛用腿)与未锁态(仅泛用腿)两态判据是否并轨(`kernel/cw_equip_value.py` `decide_equip_overlay_pick` 双态注;消费位 `operations/cw_screen/cw_screen_equip_pick.py`) | 影响装备向终局线 key_equips 的转移定向;并轨裁决须保锁线态「目标线装备优先」语义不回退,否则削弱终局套成型强度(注册评级前提含装备 top 口径) |
| 预囤加分 | 预囤模式(框架未定)下通用件仍得 +0.15 加分的分叉待裁(测试文件 `test_transition_score_tiers_and_prehoard` ⚠️ 注已申报) | 影响 P1 预囤期囤货构成(通用插件 vs 纯档位件)→ 影响终局线就绪前的存货面与完成率读数;不改变锁线判据。裁决后同步改对应断言(锁注释已申报改法) |

- **位面 3 实证归 T-12**:本定版不预支位面 3 的任何实证结论;T-12 通关如暴露定版偏差(如评分排序系统性偏航、强制锁线对象限定在位面 3 误判、weak_planes 注册失真),按锁线机制修评分/信号注册,本文档随迭代收尾更新。
- **其他边界**:①本文与 `transition-lineup-final.md` 同寿命,`changes/` 内容不作长期引用,长期引用指向文首单一源;②「主口径 = 列车同行」是注册面默认首选,若 T-12 前出现注册层改判(评级/家族重构),以 COMP_LIBRARY 现行注册为准,本文不构成对注册层的约束。
