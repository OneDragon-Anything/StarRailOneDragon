# 29 投资策略画面策略(invest strategy screen)

> 画面 = 货币战争-投资策略(局内固定节点的策略卡三选一,可**逐卡**刷新);**能力面** = [../screens/README.md](../screens/README.md) §5.2/§5.5。本篇 = 该画面的**策略面**(宪法六「一画面一策略文件、一画面一策略文档」)。
> 决策本体 = `strategies/impl/mandate_v1/invest_strategy.py::decide / decide_pick`(纯值出口);组件模块同目录 `strategy_economy.py`(现金分)/ `line_select.py`(方向分锚点线)/ `gift_value.py`(赠卡分)/ `pick_common.py`(转向轴与克制减分共用件);kernel 机制事实 = `cw_investments`(注册表/STRATEGY_BINDINGS/STRATEGY_GRANTS/is_blood_economy/is_economy_engine/resolve_strategy_canonical)与 `cw_invest_channels`(投资通道派生)/`cw_line_scales`(数量级标尺);动作包装与同帧去重 = `strategies/impl/flow.py::_decide_invest` kind='strategy' 分支;画面 op = `operations/cw_screen/cw_screen_invest_strategy.py`。判据权威定义引用不重复,数值单一源在代码(本篇只写常量名)。
> 术语(首现定义):**单一源** = 该信息的唯一权威出处;**帧** = 一次截取游戏画面并做一次决策的时点;**对账** = 预期记账状态与实际读数的比对核验;**fail-closed** = 读不到数据时默认走保守分支;**视界** = 决策考虑的未来时间跨度(此处 = 剩余节点数);**终局阵容已锁定**(`locked_comp`)= 最终阵容已确定、此后围绕它买牌的状态;**血本位** = 扣血换收益的卡族(如奋斗协议/不等价交换);**数字来源标注(四种)**:【注】游戏定义值 /【推】已证推导 /【拟】观测估计 /【拍】用户立场登记值。

## 1. 标尺(统一加法)

- **单位 = 分;1 分 := 1 金等价**(归一化约定,沿 [28_invest_env_screen.md](28_invest_env_screen.md) §1;XP 折算沿 `env_economy.XP_GOLD_RATE` 承载)。
- **总分 = 现金分 + 方向分 + 赠卡分 + 立场分 + 转向轴加分 + 克制减分**(统一阵容评分迭代,2026-11-03);取总分最高者,平分按裁决键取先(§3)。禁选不进分值 = 集合排除出候选(§3)。量纲申报:方向分/克制减分携线分数量级(`cw_line_scales`:实证升档 750/定义卡 500/强档 300/中档 150),与金等价标尺合并是统一评分设计的用户确定的形态——定义卡支配由 +500 压过现金满档实现。
- 数字来源标注(四种):现金通道 = 【注】游戏定义值 + 【推】到达期加权;方向分/克制减分 = 【注】通道派生 × 数量级标尺;立场分与转向轴系数 = 【拍】(用户策略立场登记值,合法性来自裁定本身,§2.4/§5);品质序 = 【注】游戏定义。

## 2. 组件语义

### 2.1 现金分(五族通道)

单一入口 = `strategy_economy.strategy_economy_value(canonical, gs) -> (expected_gold, resolved)`;`resolved ∧ > 0` 才计,fail-closed 恒 0(半值禁出)。与 env 屏现金分(`env_economy`,消费 `EnvEconomyEffect`)通道公式分立——两字段空间不同构,公式不可共享。

| 通道族 | 语义 | 折算 |
|---|---|---|
| 一次性金 | `instant_gold` 面值直读 | 面值 |
| 分期金 | 「现在」项 + 接下来 count 个节点的项,count 项按「剩余节点数 − 1」截断(「接下来」不含当前节点,终局帧不多计) | `gold_next_nodes_amount + gold_next_nodes_amount × min(count, max(剩余节点数−1, 0))` |
| 按节点流 | gold_per_node / xp_per_node / 固定利息 interest_flat_per_node | 各自额度 × 剩余节点数,XP 项过 `XP_GOLD_RATE` |
| boss 节点金 | gold_per_boss_node | × 剩余 boss 数(场字段序列自当前节点(含)起 `'boss'` kind 直查;封顶 modeled planes) |
| 待建模族 | 字段级「待建模」分类集 + 卡级登记 `STRATEGY_ECONOMY_PENDING_MODELING`(键 = 规范卡名,值 = 未建模项清单;适用范围 = 无字段项 ∪ 字段已登记未挂值项) | fail-closed 0 |

- 剩余口径单一源 = 策略门面 `statefn/horizon` 场字段自算(`r_remaining`/`r_global`,长度真值源 = `gs.node_seq_by_plane` 位面实际长度,None = 未注册态回退默认表;禁第三实现);视界(决策考虑的未来跨度)封顶 modeled planes(场字段键集位面 1+位面 2,位面 3 = 建模域外 = 局终,不可达轮不计;位面 ∉ 序列表键集契约 = 返回 0);gs 节点位置未写帧退化 `(1,1)`(沿 env 屏先例)。`total_remaining_nodes` 已随缺陷修正改场字段求和(与门面同值,`01_math_framework.md` §5 R_全局 行口径)。
- 口径申报(如实保留的已知偏高):`r_global` 含当前节点,而「进入新节点给金」类通道语义不含已进入的当前节点 → per-node 通道系统性 +1 节点偏差;boss 通道同族(当前节点即位面末槽时多计一笔已发放 boss 金)。取上端 = 现金分计分偏高已知并申报,非防低估。
- 不计分通道(结构登记、永不为分):血本位(扣血换收益的卡族,如奋斗协议/不等价交换)分区(`xp_buy_hp_cost`/`hp_gold_swap`)、难度族(难度→价值需战力建模,宪法一禁域)、期权/远见族(分布假设未证)、负向结构登记(无正账可折)。
- 注册表外经济语义卡(research 已登记明列经济结构而未注册 STRATEGY_ECONOMY)= 建模待修问题形态:按 0 分申报低估、`STRATEGY_ECONOMY_PENDING_MODELING` 补列代表例;禁凭 research 记载凭直觉给分。
- 构建期校验(import 即炸):`STRATEGY_ECONOMY` 全表字段必须落「计分/待建模/不计」三类之一(未分类 = 建模缺口静默,炸出);卡级登记断言集 = 键为注册表规范名/值非空/economy 已登记而全默认者必已登记/按适用范围规则派生的闭集必已登记。

### 2.2 方向分(通道派生)

**统一阵容评分迭代(2026-11-03)复活为通道派生分量**(旧「绑定关系命中候选阵容集取 LINE_STRENGTH_SCORE 档分」链已随 strength 字段整链下线,考古走 git 历史):

- 方向分 = 卡 × **选卡锚点线**的线分引擎加分:锚 = `line_select.anchor_line_of`(锁定帧〔非降格〕= 锁定线;未锁帧 = 证据门版候选首名,**P1/P2 同一公式**——旧查表〔augment_affinity,已退役〕同样不依赖锁定帧,行为变更仅在锚点抖动面与锚缺失面,入 sim);加分 = `cw_invest_channels.strategy_line_bonus`(实证覆盖升档/定义卡/⑤引擎匹配/③星徽效果原文;查询入口先归一)。
- **defining 布尔退役**:顶级保护(「不刷掉」)= 方向分 ≥ `invest_strategy.DEFINING_BONUS_MIN`(强档阈值,一处常数 = 定义卡档 +500;实证升档 +750 同过)——不再查亲和表,锚缺失帧方向分 0 → 不保护(保守缺省)。
- 降格帧锚点回候选首名(锁线阵营不再辖选卡方向);空候选帧锚缺失 → 方向分/克制减分恒 0。

### 2.3 赠卡分

- 登记 = kernel `cw_investments.STRATEGY_GRANTS`(策略卡具名发放白名单:`chars_immediate`/`chars_conditional`/`advisor`,复用 `GiftGrant`;入册判据 = 效果原文「获得…角色名」直读,含无括号裸名;只强化不发放不入;roster-外目标与空名发放自动排除;非「获得」引导的实发放不入)。发放角色归属 = 效果原文机制事实,宪法五第②类留 kernel。
- 「档→分」映射与折减 = 策略层 `gift_value.grant_gift_value`(`GIFT_TIER_SCORE` + advisor ×`ADVISOR_DISCOUNT`「付费期权 < 白得」;档位判定机器 `cw_comps.gift_hit_tier` 留 kernel)。
- 即时集取最高档,条件集降一档;发放角色在未排除候选阵容名单外 → 该发放 0;无赠卡条目的卡赠卡分自然 0。
- 构建期校验(import 即炸;2026-10-28 治理后只留漂移哨):孤儿键(注册表无此卡)/角色名漂移(`CHARACTER_ROSTER` 外)/反扫候选闭集防线(机械反扫「获得…roster 名」全表命中 ⊆ grants ∪ 排除白名单,漏登记即炸)。

### 2.4 立场分与系数(【拍】形态)

- 立场查表 = `invest_strategy.STANCE_SCORE`(表只收非零行,行带裁定理由;表外卡恒 0;查表口径 = canonical,与组件解析同源)。现行表无非零行:战力类/契约任务链/期权类等无机械成分卡全部默认 0(用户裁定 2026-09-23,「不为过渡阵容服务」下无机械证据卡不预设正分);未来登记强度效果行按宪法一硬闸门逐项确认。
- 转向轴:`strategy_priority` 子串命中(OCR 容错)→ 加 `pick_common.STEERING_PRIORITY_BONUS`(软偏好——「用户点名是偏好不是支配」,自身成分弱的 priority 卡仍是软偏好,自身成分强时可越过);`strategy_forbid` = 排除出候选(不走分值)。
- 未锁定终局阵容帧不消费资产信号(全部兼容阵容计入先验口径;信号精细化登记待办;用户知情确认 2026-09-23)。

## 3. 结构分区与平分裁决(交互规则)

- **落地序** = 阵容冲突护栏 → 禁选排除 → 血本位三态序(血本位 = 扣血换收益的卡族,如奋斗协议/不等价交换;三态见下)→ 组件总分 argmax。旧「自拆台排除」与「定义型分区」随布尔排除位退役(统一阵容评分迭代):克制改选卡减分分量(本节下方)、定义型支配由方向分 +500 数值实现。
- **阵容冲突护栏**(指向集单一源 = `kernel/cw_investments.env_faction_scope`/`strategy_faction_scope`):候选卡阵容指向集与基准空交 → 出域排除。基准 = 锁定线 `Comp.factions`(锁定帧,历史误持不入基;降格帧锁线不入基回持有基)∨ 已持有投资(环境+策略)指向并集(未锁定帧);基准空(无指向持有 ∧ 未锁定)→ 不辖,选卡与无护栏逐位一致。出域标记在评分帧逐卡承载,排除在结构分区第一步域收缩;全部候选出域 → 回退全体候选 argmax(tag `off-direction fallback`)。刷新侧出域卡与被禁同款处置(见 §4)。依据:策略槽只服务本局阵容方向——手里已有圣杯环境时,服务仙舟/银河学者的组件卡(琼玉专家:青雀/黑塔纪元类)对本局无用且挤占策略槽。
- **禁选**:`strategy_forbid` 子串命中 → 排除出候选;禁选致候选域全空 → 全体候选(含被禁)按组件总分 argmax 最不负分者(用户「有替代永不选」在无替代帧无对象),原因编码以 `all-excluded-fallback` 开头(判读面唯一标识)。
- **克制减分**(counters_dot 硬排除迁移,共用判据单一源 = [13_pick_family.md](13_pick_family.md) 共用判据节,代码 = `pick_common`):克制锚点线主派的候选给选卡分 −`cw_line_scales.COUNTER_PICK_PENALTY`(克制档,纯加权非排除);主派→受克属性映射批 1 为直接同名对(持续伤害→DoT/减益→减益/燃血→燃血),触发时序差异申报 = 现行板面 DoT/减益计数 ≥2(成型后)→ 新锚点线主派即触发(P1 更早更广),行为变更入 sim。
- **血本位三态序**(判据 = `is_blood_economy`,kernel 注册表派生零名单):有非血卡可选 → 非血卡内部竞争;只剩非禁血卡可选 → 血卡之间竞争;全部被禁 → 全体候选一起竞争。
- **候选解析**统一走 `resolve_strategy_canonical`(归一 + LCS 兜底;LCS 兜底命中即告警 = 观测点);组件查表全走 canonical。**env 名防御**:入口对候选做 `get_env(o)` 命中断言(防注册表交叉演化下 env 名 LCS 误中策略名),违例候选跳过解析、0 分垫底。
- **空候选帧** = 观察层失约:决策退化 `idx=0` 并标注原因,不抛错不盲发(op 层空候选已 round_fail 拦截,此态仅防御可达)。
- **平分裁决键**:总分 → 无 canonical 候选恒殿后(防并列 0 分帧垃圾名凭槽序压过真卡;垃圾名之间按槽序)→ 品质序(棱彩 > 金 > 银,【注】游戏定义)→ economy 效果有无(谓词 = `economy is not None and economy != EconomyEffect()`,全默认不记 1)→ 槽序(候选序 = 传入序,max 首达)。

## 4. 刷新判据与输出契约(P81 承接)

- 判据权威定义、谓词形状与优势论证 = `../proofs/p81-invest-refresh-dominance.md`(换基增补节)与 `../proofs/math_proofs.md` P81 行;代码承载 = `invest_strategy._refresh_slots`。本篇不复制逐谓词,只记结构:帧级门(候选恰 3 ∧ 全精确分类 ∧ 帧内无帧级顶级卡 ∧ 终局阵容已锁定帧 max_N≠1)与槽级顶级两谓词分立;帧级门失败 → 整帧不刷;帧级门过 → 槽级动作集(非槽级顶级可刷 ∨ 被禁槽恒入 − F2 唯一首层守卫)非空 → 建议刷。
- **帧级顶级类** = 派生顶级(方向分 ≥ `DEFINING_BONUS_MIN`,§2.2)∨ 持续通道引擎(`is_economy_engine`);**E-豁免**:被禁卡与阵容冲突出域卡不入帧级顶级判定、不计 max_N、恒入刷新动作集(出域卡占槽应刷掉换本局阵容方向卡机会;F2 唯一首层守卫的 L1 集合同样剔除出域槽)。**槽级顶级类** = 帧级顶级类 ∨ 对齐保护(终局阵容已锁定帧 = 非血 ∧ N≥2 元素命中;未锁定终局阵容帧 = 恒 False——锚缺失帧方向分 0,保守向不保护)。
- 刷新分类**精确命中-only**(LCS 不入分类,按对抗审查条目 G8 取保守兜底;评分错只排错序、刷新错会弃掉真顶级卡,不对称风险取严);G8 消费序 = 先判帧级门、后取分类。
- **输出契约**:`decide` 返回纯值 `InvestStrategyDecision(idx, reason, total, components)` ∨ `StrategyRefreshSuggestion(reason, slots)`,不含动作类型值(flow 包装 `CwActionPickInvestStrategyParam`/`CwActionRefreshInvestCardsParam`;与 env 侧 `RefreshSuggestion` 不共享不继承——两屏刷新语义不同构,同名歧义以屏别前缀消解)。`decide_pick` = 同一评分基线的纯选卡口,永不建议刷(flow 同帧去重 memo 命中后的落选卡入口)。
- handler 三闸(obs 逐槽余量现读/状态容器(GameState) `strategy_refresh_left` 对照/F2 守卫)与同帧去重 memo(建议帧首调发建议 → 三闸全败重调走 `decide_pick` 落选卡并清键 → 再调恢复首调语义)结构归 flow/op 层,判据侧零感知。sim 复用预留 `decide`/`decide_pick`(sim 后端全链呈现本屏,判据改动属可 A/B 面)。
- 选卡结果喂 CommitSignals 为**条件活遥测**(仅通道加分非零卡命中帧产信号,一般策略帧不产;判读口径 = 通道派生线分加分〔`cw_line_scales` 数量级〕,非旧 0..1 亲和权重,跨批判读勿混读;决策面零消费)。

## 5. 裁定语境

- **2026-10-17**(阵容冲突护栏):「前面选择了圣杯的环境,琼玉专家和黑塔纪元对应的终局阵容和圣杯冲突,所以排除——未锁定终局阵容之前,看的是和其他环境、策略有没有冲突;锁定了终局阵容之后,就是看和终局阵容有没有冲突。」排除 = 域收缩非负分(负分须拍自由参数,违背本篇零拍值纪律);环境侧同判据(权威版本 = 28 号稿 §3)。
- **2026-09-08**:「优先经济,然后是终局阵容,不为过渡阵容服务」——两屏对齐源均 = 意向状态三参(`locked_comp`/`demoted_endgame`/`evicted`,flow 直接透传);消费过渡配方对 target_comp 的对齐语义随之不适用于本屏。
- **2026-09-23 会话四项**:
  1. 组件加权融合(总分 = 五组件加法)为准;
  2. S 档阵容档分沿用 `LINE_STRENGTH_SCORE` 现值——高购买力带现金大额越过 S 档阵容 = 「优先经济」方向的兑现,开局帧让位经济;
  3. 战力类等无机械成分卡立场默认 0(立场表无非零行,§2.4);
  4. 资产信号跟随停用知情确认(未锁定终局阵容帧全部兼容阵容计入,§2.4)。

## 6. 边界与动机

- **阵容冲突护栏的基准取「已持有投资指向并集」而非「方向线」**(锁定后切锁线阵营):方向线判定要处理信号时序(锁定写入滞后于信号到手)、P2 兜底锁定、P1 配方帧三类形态,每类都有失明/抖动补丁;持有指向模型基准只看现值,三类形态不存在。同一持有面存在三种消费口径,分野(统一阵容评分迭代后):**投资通道派生**(`kernel/cw_invest_channels`,回答「这张卡给哪条线加几分」——线分与选卡方向分共用)、**指向集**(本护栏,回答「这张卡与已有阵容方向冲不冲突」)、**候选锚点线**(`line_select.anchor_line_of`,回答「当前朝哪条线选卡」——锁定帧/候选首名)——三问三答不禁双口径。
- **出域 = 域收缩非负分**:负分须拍「多大负分压得过各类正分」的自由参数,违背本篇零拍值纪律;排除语义 = 裁定「不可选」非「不优」,排除后剩余域 argmax 照常。
- **指向集为宽口径**:角色分支 = 注册表 factions 全集 ∪ 成员分支(线 core∪shared),与方向分触线集的窄口径(角色分支只认线 core,防方向分虚高)分工——护栏问「为谁服务」(全像),方向分问「对锁定线值几分」(主轴)。
- **宪法五**(框架层只留游戏原始真值):注册表、绑定表、发放登记、血本位判别、引擎判别、canonical 解析器 = 游戏原始真值与机制事实判定,留 kernel;评序、折算、立场全驻策略层。
- **宪法六**:一画面一策略文件/一画面一策略文档;跨画面共用判据(转向轴/克制减分)单一源 = `mandate_v1/pick_common.py`,文档单一源 = `13_pick_family.md` 共用判据节(`28_invest_env_screen.md`/本篇两篇只留指针);画面文件 → 共用模块单向依赖。
- **不适用**:投资环境屏 = `28_invest_env_screen.md`;事件面其余单选画面 = `25_event_overlays.md`;台账价值的数学判据 = `08_events.md` E2 行(登记 P38 ⑤层参数化,待 derive)。
