# 29 投资策略画面策略(invest strategy screen)

> 画面 = 货币战争-投资策略(局内固定节点的策略卡三选一,可**逐卡**刷新);**能力面** = [../screens/README.md](../screens/README.md) §5.2/§5.5。本篇 = 该画面的**策略面**(宪法六「一画面一策略文件、一画面一策略文档」)。
> 决策本体 = `strategies/impl/mandate_v1/invest_strategy.py::decide / decide_pick`(纯值出口);组件模块同目录 `strategy_economy.py`(现金分)/ `line_value.py`(方向分)/ `gift_value.py`(赠卡分)/ `pick_common.py`(转向轴与自拆台共用件);kernel 机制事实 = `cw_investments`(注册表/STRATEGY_BINDINGS/STRATEGY_GRANTS/is_blood_economy/is_economy_engine/resolve_strategy_canonical);动作包装与同帧去重 = `strategies/impl/flow.py::_decide_invest` kind='strategy' 分支;画面 op = `operations/cw_screen/cw_screen_invest_strategy.py`。判据本体引用不重复,数值单一源在代码(本篇只写常量名)。

## 1. 标尺(统一加法)

- **单位 = 分;1 分 := 1 金等价**(归一化约定,沿 [28_invest_env_screen.md](28_invest_env_screen.md) §1;XP 折算沿 `env_economy.XP_GOLD_RATE` 承载)。
- **总分 = 现金分 + 方向分 + 赠卡分 + 立场分 + 转向轴加分**;取总分最高者,平分按裁决键取先(§3)。禁选不进分值 = 集合排除出候选(§3)。
- 数字三形态:现金通道 = 【注】游戏定义值 + 【推】到达期加权;立场分与转向轴系数 = 【拍】(用户策略立场登记值,合法性来自裁定本身,§2.4/§5);品质序 = 【注】游戏定义。

## 2. 组件语义

### 2.1 现金分(五族通道)

单一入口 = `strategy_economy.strategy_economy_value(canonical, gs) -> (expected_gold, resolved)`;`resolved ∧ > 0` 才计,fail-closed 恒 0(半值禁出)。与 env 屏现金分(`env_economy`,消费 `EnvEconomyEffect`)通道公式分立——两字段空间不同构,公式不可共享。

| 通道族 | 语义 | 折算 |
|---|---|---|
| 一次性金 | `instant_gold` 面值直读 | 面值 |
| 分期金 | 「现在」腿 + 接下来 count 节点腿,count 腿按「剩余节点数 − 1」截断(「接下来」不含当前节点,终局帧不多计) | `gold_next_nodes_amount + gold_next_nodes_amount × min(count, max(剩余节点数−1, 0))` |
| 按节点流 | gold_per_node / xp_per_node / 固定息 interest_flat_per_node | 各自额度 × 剩余节点数,XP 腿过 `XP_GOLD_RATE` |
| boss 节点金 | gold_per_boss_node | × 剩余位面数(boss = 位面末槽,`plane_end_slots` 几何) |
| 待建模族 | 字段级「待建模」分类集 + 卡级登记 `STRATEGY_ECONOMY_PENDING_MODELING`(键 = 规范卡名,值 = 未建模腿清单;辖域 = 无字段腿 ∪ 字段在册未挂值腿) | fail-closed 0 |

- 剩余口径查表单一源 = `cw_plane_table.schedule_of` 位面实际长度,消费符号 = `cw_plane_table.r_remaining`/`r_global`(经策略侧门面 statefn/horizon 复用,禁第三实现);未揭晓位面沿其 `PLANE_FALLBACK_PRIORS` 结构先验回退;gs 节点位置未写帧退化 `(1,1)`。**禁消费** `total_remaining_nodes` 恒按 9/位面计口径(01_math_framework §5 R_全局 行已登记待修缺陷)。
- 口径申报(如实保留的已知偏高):`r_global` 含当前节点,而「进入新节点给金」类通道语义不含已进入的当前节点 → per-node 通道系统性 +1 节点偏差;boss 通道同族(当前节点即位面末槽时多计一笔已发放 boss 金)。取上端 = 现金分计分偏高已知并申报,非防低估。
- 不计分通道(结构登记、永不为分):血本位分区辖(`xp_buy_hp_cost`/`hp_gold_swap`)、难度族(难度→价值需战力建模,宪法一禁域)、期权/远见族(分布假设未证)、负向结构登记(无正账可折)。
- 注册表外经济语义卡(research 在册明列经济结构而未注册 STRATEGY_ECONOMY)= 建模欠账形态:按 0 分申报低估、`STRATEGY_ECONOMY_PENDING_MODELING` 补列代表例;禁凭 research 记载凭直觉给分。
- 构建期校验(import 即炸):`STRATEGY_ECONOMY` 全表字段必须落「计分/待建模/不计」三类之一(未分类 = 建模缺口静默,炸出);卡级登记断言集 = 键为注册表规范名/值非空/economy 在册而全默认者必在册/按辖域规则派生的闭集必在册。

### 2.2 方向分(线价值,comp 空间)

- 触线集 = `STRATEGY_BINDINGS`(kernel 机制事实)命中:阵营绑定腿(阵营线的成员 comp 全体)∪ 角色绑定腿(`comp.core_chars` 含绑定角色,窄口径);未建模卡 → 空集(方向分 0)。
- **统一 comp 空间**:「线」= 阵营线,线价值 = 成员 comp 档分 max;线在调用侧以成员 comp 集表示。**线排除像**:evicted 为 comp 名集合,线排除 ⇔ 该线全体成员 comp ∈ evicted(整体死亡判据);线活则全体成员入集,含已被 evicted 的成员——线级整体排除(未整死的线中已被逐成员仍贡献档分,方向分虚高向,有意选择:线死亡才退场)。
- 三形态:意向已锁线 ∧ 非降格帧 → 基础集 ∩ 锁线阵营线成员 comp 并集(锁线不含候选绑定阵营 → 0;锁线全线死 → 0);未锁线或降格帧 → 基础集全体取 max。
- 判定本体 = `line_value.line_value_best(cand_comps, locked_comps, demoted_endgame)`(三形态共用内层入口;空串/空集 locked 视作未锁;evicted 不入签名——像在候选集构造侧,env 屏经 `line_value` 单阵营入口精确包装同源消费)。线价值档分 = `LINE_STRENGTH_SCORE`(单一源,28 号稿 §2,【拍】)。
- **刷新 N 计数 = 绑定元素空间**(阵营∪角色直读命中锁线单线的元素数,不经触线 comp 集;与方向分 comp 空间分开命名)。

### 2.3 赠卡分

- 登记 = kernel `cw_investments.STRATEGY_GRANTS`(策略卡具名发放白名单:`chars_immediate`/`chars_conditional`/`advisor`,复用 `GiftGrant`;入册判据 = 效果原文「获得…角色名」直读,含无括号裸名;只强化不发放不入;roster-外目标与空名发放自动排除;非「获得」引导的实发放不入)。发放角色归属 = 效果原文机制事实,宪法五第②类留 kernel。
- 「档→分」映射与折减 = 策略层 `gift_value.grant_gift_value`(`GIFT_TIER_SCORE` + advisor ×`ADVISOR_DISCOUNT`「付费期权 < 白得」;档位判定机器 `cw_comps.gift_hit_tier` 留 kernel)。
- 即时集取最高档,条件集降一档;发放角色在未排除候选阵容名单外 → 该发放 0;无赠卡条目的卡赠卡分自然 0。
- 构建期校验(import 即炸):孤儿键(注册表无此卡)/角色名漂移(`CHARACTER_ROSTER` 外)/空发放集/反扫候选闭集防线(机械反扫「获得…roster 名」全表命中 ⊆ grants ∪ 排除白名单,漏登记即炸)。

### 2.4 立场分与系数(【拍】形态)

- 立场查表 = `invest_strategy.STANCE_SCORE`(表只收非零行,行带裁定理由;表外卡恒 0;查表口径 = canonical,与组件解析同源)。现行表无非零行:战力类/契约任务链/期权类等无机械成分卡全部默认 0(用户裁定 2026-09-23,「不为过渡阵容服务」下无机械证据卡不预设正分);未来登记强度效果行按宪法一硬闸门逐项确认。
- 转向轴:`strategy_priority` 子串命中(OCR 容错)→ 加 `pick_common.STEERING_PRIORITY_BONUS`(软偏好——「用户点名是偏好不是支配」,自身成分弱的 priority 卡压不过 S 线方向分,自身成分强时可越过);`strategy_forbid` = 排除出候选(不走分值)。
- 未锁线帧不消费资产信号(全部兼容线计入先验口径;信号精细化挂账;用户知情确认 2026-09-23)。

## 3. 结构分区与平分裁决(交互规则)

- **落地序** = 禁选排除 → 自拆台(辖域护栏)→ 血本位三态序 → 定义型分区 → 组件总分 argmax。
- **禁选**:`strategy_forbid` 子串命中 → 排除出候选;禁选致候选域全空 → 全体候选(含被禁)按组件总分 argmax 最不负分者(用户「有替代永不选」在无替代帧无对象),归因串以 `all-excluded-fallback` 开头(判读面唯一标识)。
- **自拆台**(共用判据单一源 = [13_pick_family.md](13_pick_family.md) 共用判据节,代码 = `pick_common`):板面 持续伤害+减益 ≥ `BOARD_DOT_COUNT_THRESHOLD` 时,克制 DoT/减益的候选排除(`counters_dot` 事实判定);**辖域护栏** = 仅作用于非血非禁候选域,排除后该域空 → 自拆卡回归(自拆是策略回避立场非用户意志,不得制造血卡上位)。
- **血本位三态序**(判据 = `is_blood_economy`,kernel 注册表派生零名单):可入选非血集非空 → 其内竞争;仅非禁血卡可选 → 血卡间竞争;全禁帧 → 全体竞争。
- **定义型分区**(判据 = `augment_affinity` 命中,「拿到即改写本局玩法」机制级声明):竞争域内存在定义型卡 → 域收缩为定义型子集,域内多张按组件总分 argmax——定义型支配为无条件(混合帧 winner 不被非定义型大分越过)。
- **候选解析**统一走 `resolve_strategy_canonical`(归一 + LCS 兜底;LCS 兜底命中即告警 = 观测锚);组件查表全走 canonical。**env 名防御**:入口对候选做 `get_env(o)` 命中断言(防注册表交叉演化下 env 名 LCS 误中策略名),违例候选跳过解析、0 分垫底。
- **空候选帧** = 观察层失约:决策退化 `idx=0` 并标注归因,不抛错不盲发(op 层空候选已 round_fail 拦截,此态仅防御可达)。
- **平分裁决键**:总分 → 无 canonical 候选恒殿后(防并列 0 分帧垃圾名凭槽序压过真卡;垃圾名之间按槽序)→ 品质序(棱彩 > 金 > 银,【注】游戏定义)→ economy 效果有无(谓词 = `economy is not None and economy != EconomyEffect()`,全默认不记 1)→ 槽序(候选序 = 传入序,max 首达)。

## 4. 刷新判据与输出契约(P81 承接)

- 判据本体、谓词形状与优势论证 = `../proofs/p81-invest-refresh-dominance.md`(换基增补节)与 `../proofs/math_proofs.md` P81 行;代码承载 = `invest_strategy._refresh_slots`。本篇不复制逐谓词,只记结构:帧级门(候选恰 3 ∧ 全精确分类 ∧ 帧内无帧级顶级卡 ∧ 锁线帧 max_N≠1)与槽级顶级两谓词分立;帧级门失败 → 整帧不刷;帧级门过 → 槽级动作集(非槽级顶级可刷 ∨ 被禁槽恒入 − F2 唯一 L1 守卫)非空 → 建议刷。
- **帧级顶级类** = 定义型 ∨ 持续通道引擎(`is_economy_engine`);**E-豁免**:被禁卡不入帧级顶级判定、不计 max_N。**槽级顶级类** = 帧级顶级类 ∨ 对齐保护(锁线帧 = 非血 ∧ N≥2 元素命中;未锁线帧 = 非血 ∧ 触 S/A 档线——档位边界取自 `LINE_STRENGTH_SCORE` 无新常数)。
- 刷新分类**精确命中-only**(LCS 不入分类,G8 fail-closed;评分错只排错序、刷新错会弃掉真顶级卡,不对称风险取严);G8 消费序 = 先判帧级门、后取分类。
- **输出契约**:`decide` 返回纯值 `InvestStrategyDecision(idx, reason, total, components)` ∨ `StrategyRefreshSuggestion(reason, slots)`,不含动作词表(flow 包装 `CwActionPickInvestStrategyParam`/`CwActionRefreshInvestCardsParam`;与 env 侧 `RefreshSuggestion` 不共享不继承——两屏刷新语义不同构,同名歧义以屏别前缀消解)。`decide_pick` = 同一评分基线的纯选卡口,永不建议刷(flow 同帧去重 memo 命中后的落选卡入口)。
- handler 三闸(obs 逐槽余量现读/容器 `strategy_refresh_left` 对照/F2 守卫)与同帧去重 memo(建议帧首调发建议 → 三闸全败重调走 `decide_pick` 落选卡并清键 → 再调恢复首调语义)结构归 flow/op 层,判据侧零感知。sim 复用预留 `decide`/`decide_pick`(sim 后端全链呈现本屏,判据改动属可 A/B 面)。
- 选卡结果喂 CommitSignals 为**条件活遥测**(仅定义型卡命中帧产 affinity 信号,一般策略帧不产;决策面零消费)。

## 5. 裁定语境

- **2026-09-08**:「优先经济,然后是终局阵容,不为过渡阵容服务」——两屏对齐源均 = 意向状态三参(`locked_comp`/`demoted_endgame`/`evicted`,flow 直通);消费过渡配方对 target_comp 的对齐语义随之不辖本屏。
- **2026-09-23 会话四项**:
  1. 组件加权融合(总分 = 五组件加法)为准;
  2. S 线档分沿用 `LINE_STRENGTH_SCORE` 现值——高购买力带现金大额越过 S 线 = 「优先经济」方向的兑现,开局帧让位经济;
  3. 战力类等无机械成分卡立场默认 0(立场表无非零行,§2.4);
  4. 资产信号跟随退役知情确认(未锁线帧全部兼容线计入,§2.4)。

## 6. 边界与动机

- **宪法五**(框架层只留游戏原始真值):注册表、绑定表、发放登记、血本位判别、引擎判别、canonical 解析器 = 游戏原始真值与机制事实判定,留 kernel;评序、折算、立场全驻策略层。
- **宪法六**:一画面一策略文件/一画面一策略文档;跨画面共用判据(转向轴/自拆台)单一源 = `mandate_v1/pick_common.py`,文档单一源 = 13 号稿共用判据节(28/29 两篇只留指针);画面文件 → 共用模块单向依赖。
- **不辖**:投资环境屏 = 28 号稿;事件面其余单选画面 = 25 号稿;台账价值的数学判据 = 08 号稿 E2 行(挂 P38 ⑤层参数化,待 derive)。
