# 遭遇选档简化 无前提对抗审查报告

**循环第 16 轮**（2026-09-12；无前提攻击：干净上下文，只信本轮直调核实的代码体、规范原文与脚本实跑；不继承前轮结论）

## 一、结论概览（发现统计）

- **发现：高 0 / 中 3 / 低 6。零实质发现不成立，未达定稿门槛，但已接近**——第 15 轮 13 项修复 9 项干净落地；残留集中在「环写位表述清尾」「拓扑⑥的 1f 路径覆盖缺口」「一处登记路径错指」，无判据数学与宪法对账层新伤。
- 本轮定性：判据数学本体（§1-§5）、宪法程序对账（裁定 6 例外扩大程序 + ADR-0536 退役链）、锁表归属、落码接口可行性全部复核站住；14 组数字脚本复算零错。三个中级发现里两个是第 15 轮修复的不完整落地，一个是新查明的拓扑缺口，均一行到三行可修。
- 术语定义（首次出现）：**环** = GameState 结算观测环（深度 10 的 RoundOutcome 结算行循环缓冲，E-2 新建）；**暗装态** = 判据未过开闸门时的保守缺省行为（恒最低档 + 零刷新）；**开闸门** = 判据从暗装转激活需满足的全部条件；**缺环率** = 归档对局中「应产结算行的节点」里环内无对应行的比例（E-3 离线量测）；**1f 行** = 失败结算页 1（进度条帧）产的 telemetry-only 补录行；**3b 行** = 「前往结算」链上点「前往结算」按钮时产的全写行。

| 级别 | 数量 | 一句话 |
|---|---|---|
| 高 | 0 | — |
| 中 | 3 | ①「环写点 = 创建点两路入环」旧表述 5 处残留（details 契约 1 段内新旧两写位描述并存）；②拓扑⑥残留排除接线在 telemetry_only（1f）路径结构性失效；③landing 正本更新清单 04_survival_budget 路径指向不存在的文件 |
| 低 | 6 | L15-6 装配位形态残留、锚点微漂 ×2、P/B「结构性删失」措辞过强、环深论证枚举漏巨星 + P3 超长形态未申报、「P2r1 +2」无持久指针、README 进度行滞后 |

## 二、指定复核点专项裁定

### ① H-1 修复闭环性：**通过（登记义务闭环；路径错指列中-③）**

- E-4 登记义务已入两处：details :159 与 landing :82 均含裁定 6 登记行，四要素逐项齐——授权日期 2026-09-12 ✓ / 形态 = 结算屏现成读数含 B/P 进遭遇决策 ✓ / v1 不消费辖域 ✓ / 敌方通道退路 ✓；并钉「单一源登记位，防 changes/ 删减后例外溯源断链」。
- 00 §5「hp 进决策的全部例外（**含挂账中**）｜本篇 §3 硬闸门 + 04 §7」现文在册（00_framework.md :56）；裁定 6 属「此两件之外」的用户逐项确认形态，登记位 = 04 §7 与 00 §3 通道语义吻合（04 §7 表头「任何新形态进入前须过 00 §3 硬闸门（逐项用户确认）并在本表登记」）。
- 04_survival_budget.md §7 当前 8 行无裁定 6 行 = E-4 未执行的正常态（阶段进度 0/4），设计侧义务声明完整，不构成发现。
- **闭环缺口**：landing :82 给出的完整路径 `docs/game/currency_war/research/04_survival_budget.md` **不存在**（全库 glob 零命中）。正本 = `docs/develop/sr_od/application/currency_war/strategy-docs/04_survival_budget.md`（00 §5 以同目录相对链接引用可证；hp 授权对账表属策略约束层，按知识归位判据只在 develop 侧）。E-4 执行者照单找不到文件 → 停手回问（无静默错改风险），或更坏：在 game/research 下错建第二源 → 判**中**。

### ② 环写位归一后契约 1 / §8① / §8④ / W239 四处互洽：**主体通过（写位主口径四处一致且时序可行；残留 = 中-①）**

- 四处主口径核对：契约 1「环写位 = 守卫后、观察半直写前（三路调用中过守卫者入环）」、§8①「W239 守卫之后、观察半直写之前——1f 行（过守卫者）与 3b 全写行均入环」、§8④「1f 行 W239 防毒守卫（:372-375）保留现状——其抑制形态不入环」、代码 W239 守卫 `if telemetry_only and _obs.killed is not False: return`（cw_screen_battle_wait.py:372-375）——**守卫在写位之前、抑制形态到不了写位**，四处逻辑自洽。
- 时序可行性（本轮独立推演）：写位落在 :375 与 :418 之间均可行。若落 :375-:377（合并前），`_obs` 以**引用**入环后，:377-382（progress 合并）、:384-387（killed 符号判定）、:395-405（hp 对比兜底）、:406-417（页 1 三项合并）对同一对象原位补全——RoundOutcome 为非 frozen dataclass，setattr 语义成立，环行终态完整；若落 :417 之后，行已完整更稳。两落点都被「守卫后、直写前」文字覆盖，落码者有明确自由度，非矛盾。
- 三调用位独立核实：胜局 :647 / 1f 经 `_record_loss_page` :546（telemetry_only=True）/ 3b :818，全部汇入 `_record_round_outcome` 单执行体；1f 过守卫行（killed=False）可达守卫后代码段，「1f 行保证入环」时序成立。
- **残留**（升中-①）：契约 1 段首仍保留「环写点 = RoundOutcome 创建点两路入环（1f/3b 均入环）」——「创建点」写位描述与同段「守卫后」并存；若字面落进 `read_round_outcome` 体内，守卫拦不住 boss 胜局页 1 幻影行（上轮中-1 矛盾一的原机制未被表述清零）。

### ③ 全量扫尾：**3 中 6 低，见第三节**

除发现清单所列外，四文档全部承重 as-built 断言经直调逐一成立（对账见第六节）。补充一项本轮重点新核：**真值判别子与 GameState 写端全链互洽**——observe 写 `source='observation'`（cw_game_state.py:2278）、carry 写 `source='carried'`（:2291，四态词表 :220）、Field 默认 `(None, 'observation')`（:407-408）、carry 空值早退（:2287-2288）、简报回退只写 session 不写 BoardState（cw_screen_briefing.py:183-186）——首读前 (None,'observation') 态与简报恒值（carried）态均被 `source=='observation' ∧ value 非空` 判别子拒绝，details :70 的三个代码事实断言全部成立。

## 三、发现清单

### 高

（无）

### 中

**中-①｜环写位旧表述 5 处残留，details 契约 1 段内新旧两写位描述并存（中-1 修复不完整）**
- 位置：details :16 段首「环写点 = RoundOutcome **创建点**两路入环（1f/3b 均入环）」与同段尾「环写位 = **守卫后**、观察半直写前（三路调用中过守卫者入环）」并存；同型残留 details :110（§8 表「写端 = RoundOutcome 创建点两路入环」）、details :157（阶段 E-2「环写点 = RoundOutcome 创建点两路入环」）、landing :29 与 :33（两处「环写点 = RoundOutcome 创建点两路入环」）。
- 代码事实：环写位唯一正确落点 = `_record_round_outcome` 内守卫后（上轮中-1 已定谳）；「创建点」字面指向 `read_round_outcome` 体内，落码者读到残留句可能按字面落进构造点 → 守卫失效、boss 胜局页 1 幻影行入环。
- 修正方向：五处统一为「构造唯一点三路过守卫者入环（写位 = `_record_round_outcome` 内 W239 守卫之后、观察半直写之前）」单一表述，「两路」字样全清；README :17 / design :48 已是新表述可作对齐基准。

**中-②｜拓扑⑥残留排除接线在 telemetry_only 路径结构性失效（中-5 修复不完备）**
- 代码事实：`_residual = False if telemetry_only else self._mark_relaunch_residual()`（cw_screen_battle_wait.py:304）——**1f 败局行（telemetry_only=True）的 residual 恒 False**，且此时 `_mark_relaunch_residual` 不被调用（first_settlement_seen 不置位）。
- 缺口推演：relaunch 残留屏若为败局形态（挑战结束 + 进度条 + 前往结算），走 1f 分支 → `_record_loss_page` → telemetry-only 行 killed=False 过 W239 守卫 → 按 §8① 入环，但 residual=False 使拓扑⑥排除判据拦不住它；该行以残留屏真值 plane/round（如 2-6）入新局环，后续新局真实同键行经「后到行缺字段不覆盖先行行」合并被残留值污染。3b 全写路的排除正常（residual 判定生效），救不回已入环的 1f 行。
- 影响面：拓扑⑥「残留行不入新局环（跨局污染消除）」的承诺在败局形态残留屏下不成立；且 E-3 缺环率对账把它量成环内**多行**（非缺行），现行对账判别式（逐节点对账缺行）查不出多行污染。
- 修正方向：残留判定与 telemetry_only 解耦——1f 路径同样取残留判据（`_mark_relaunch_residual` 首调后恒 False，对排除语义幂等安全），或环写位对 telemetry_only 行独立计算「first_settlement_seen 前置态 ∧ is_new_match ∧ 宽限窗」；landing 3.2 与 details §8⑥ 同步补注；W14 对账可加「多行/同键冲突」副判据兜住该形态。

**中-③｜landing 正本更新清单 04_survival_budget 路径指向不存在的文件**
- 位置：landing :82「`docs/game/currency_war/research/04_survival_budget.md` §7 …」——全库 glob 该路径零命中。
- 代码/文档事实：正本 = `docs/develop/sr_od/application/currency_war/strategy-docs/04_survival_budget.md`（00_framework §5 同目录相对链接 `[04_survival_budget.md]` 可证）。
- 修正方向：landing :82 路径改 `strategy-docs/04_survival_budget.md`（与 details :159 无路径写法、00 §5 引用对齐）。

### 低

**低-①｜L15-6 残留：cw_settlement_obs.py 装配位形态仍未注明**
- 上轮建议二选一「注明构造参/后填装配形态 或 文件面补该文件」，本轮两者均未落（landing :33 文件面含 telemetry/schema.py ✓，无 cw_settlement_obs.py；范围段「结算快照取备战帧…」只写装填时点）。按现设计构造点无改动需求（新字段默认 None、调用方 battle_wait 后填），不补文件自洽，但落法仍未指明。修正：landing 3.2 加半句「双扩字段走调用方 `_obs` 后填，构造点签名不动」。

**低-②｜锚点微漂 ×2（语义成立，行号漂）**
- `damage_dealt 生产写端 = cw_settlement_obs.py:450/:494`（landing :33、details :157）——:450 是注释首行，赋值行 = :453；:494 准确。
- `outcomes 写端退役（cw_settlement_obs.py:441）`（details :16）——退役表述实际在 :443 docstring 行。
- 设计头注「并行批迁移后以符号锚为准」已免责，照实登记。

**低-③｜契约 5「P/B 在胜局帧结构性删失」措辞过强**
- 代码事实：胜局页 1（点击空白加速帧）tooltip 瞬窗有读链（cw_screen_battle_wait.py:780-793 暂存 + :406-417 合并入胜局行），P/B 值**可读出**。真实机制 = 胜局不掉血（combat.md:27）→ P/B 无分级信息量 + tooltip 进页瞬窗高频失读（cw_settlement_obs.py:250-252 注释）——「高频删失/无信息量」而非「结构性删失」。方向结论（敌通道胜局帧覆盖更优）不受影响。修正：契约 5 与 design 关键取舍行改「胜局帧 P/B 无分级信息量（胜局不掉血）且 tooltip 瞬窗高频删失」。

**低-④｜§8 环深论证产结算行类型枚举漏「巨星」，P3 超长形态未与跨位面叠加同款申报**
- `parse_settlement_node_type` 词表（生效定义 :49-50）与 `_normalize_node_type`（:582-586）均含「巨星」，EXPECTED_DROP 亦有巨星档——巨星若产结算屏则产行入环；§8 深度论证段枚举「普通战斗/遭遇/boss，奖励节点亦有结算屏…补给零行占用」未提巨星（§8③ 类型集公式「词表 ∖ 补给」已完备覆盖，仅论证段枚举不全；环深上界按「非普行」计数，不受影响）。
- 「位面轮数在册上限 9（P1）」支撑单位面最坏界 2+7=9≤10；P3 全序列未观测（plane_schedule_observed:75），P3 超 10 节点形态（R_between≥9 → 需求 11>10）的 fail-closed 劣化未像跨位面叠加形态（12>10）那样显式申报。修正：论证段补「巨星行入环与否随词表现码」半句 + P3 超长形态并入安全劣化申报。

**低-⑤｜「在册反例 P2r1 败 +2」无持久指针**
- details :56 与 design :87 引「M41 −22 vs P2r1 +2」——M41 侧有代码注释源（cw_settlement_obs.py:169-170「M41 实锤 -22」），P2r1 +2 全库无出处指针。按 iteration-design 写作硬规则（引用须持久索引）补出处或降格为「判读在案（档案指针待补）」。

**低-⑥｜README 进度行滞后**
- README :30「第 14 轮发现已修，第 15 轮待跑」——第 15 轮已跑完（attack.md 即其报告）。随本轮覆写顺手改「第 16 轮待跑」。

## 四、数字复算对账表（脚本实跑，禁心算；g = 1.052）

| 文档断言 | 复算值 | 判定 |
|---|---|---|
| Δ=10 → g≈1.660，门槛 ≤0.602 | 1.6602 / 0.6023 | ✓ |
| Δ=20 → ≈2.756，≤0.363 | 2.7562 / 0.3628 | ✓ |
| Δ=30 → ≈4.576，≤0.219 | 4.5759 / 0.2185（三位四舍五入 0.219） | ✓ |
| 1.052^18 = 2.4905 ≈「三彩 18≈血量×2.5」（economy.md:109） | 2.4905 | ✓ |
| f_min=0.5 → 最大可及净增量 ≈13.7（覆盖净值 6、不及 16） | 13.6734 | ✓ |
| 净值门槛：其二 ≤0.738 / 其三 ≤0.444 / 其四 ≤0.268（净值 = 加成−4 = 6/16/26） | 0.7377 / 0.4444 / 0.2677 | ✓ |
| f_min∈[0.4,0.6] → 恒可及其一/其二；[0.4,0.444] 段并及其三 | 0.6≤0.738 ✓；0.4444 线分隔成立 | ✓ |
| 其一净值 −4 → 比值 1.052^4 恒过门槛 | 1.2248（>1） | ✓ |
| 环深：单位面最坏 2+7=9≤10；跨位面叠加 2+7+3=12>10 | 9 / 12 | ✓ |
| W1 注入态：1.052^−10 = 0.602 ≥ f_min=0.5 | 0.6023 | ✓ |
| README「遭遇败局 ~12.2 [10.32,14.24]」vs P15 索引行 | 12.18 [10.32,14.24]（12.18≈12.2） | ✓ |
| 环深 10 隐含界：R_between+R_after ≤8 | 单位面 7 ✓；跨位面叠加上界 10 >8 → fail-closed 申报成立 | ✓ |
| 深度 10 内「最近 1~2 个遭遇行」同环 | 两遭遇最长间隔 7 行（1-7→2-5）<10 | ✓ |
| 经验档层「≤10 行/局」 | 在册遭遇节点 P1+P2 = 2（P3 未知）≤10 | ✓ |

## 五、第 15 轮 13 项修复验证表

（任务书称 13 项、列 12 符号；L15-1 承接上轮 L-1/L-2/L-3 三锚合并项，L15-5 承接 L-7。逐符号判定如下。）

| 项 | 判定 | 依据（本轮独立核实） |
|---|---|---|
| H-1 裁定 6 登记行 | **已修**（带中-③路径错） | details :159 + landing :82 四要素齐；00 §5「含挂账中」现文 :56；登记义务声明完整，唯一缺口 = landing 路径指错文件（列中-③） |
| 中-1 环写位归一 | **残留** | details 契约 1 尾/§8①/§8④ 主口径已改「守卫后」且四处互洽 ✓；但「创建点两路入环」旧表述残留 5 处（details :16 段首/:110/:157、landing :29/:33），契约 1 段内新旧并存（列中-①） |
| 中-2 W8-W14 残留 | **已修** | landing :33「锁 W1-W6、W7、W8-W13（W14 见 3.3）」、完成判据 :40 同口径 |
| 中-3 difficulty_node 装填语义 | **已修** | details :111「遭遇行无本节点备战帧 → 取前一普通战斗节点备战帧写入值（D_enc 口径，§3）」已补；与契约 2 读点、经验档层 (t, D_enc, fill, killed) 数据点闭环互洽 |
| 中-4 E-3 配对通道 | **已修** | landing :29「journal 行携带 D_enc 口读值与 live 判别子结果」+ details :158「决策帧 D_enc 口读值 + 选档档位 + 结算胜负」；现状 journal 行（cw_screen_encounter.py:320/:438）无此二项 → E-2 扩行义务成立、落码面可行 |
| 中-5 残留排除接线 | **已修但不完备** | details §8⑥「_mark_relaunch_residual 返回值传入环写入位作排除判据」已改；但代码 :304 telemetry_only 短路使 1f 路径失效（列中-②） |
| L15-1 锚点 ×3 | **已修** | reconcile :512-518 ✓（缺行臂「窗内无任何已观测战斗行→采新+留证」逐字在位）；Field :407-408 ✓；enemy_difficulty :1971 ✓ |
| L15-2 词表生效定义 | **已修** | details §8③「生效定义 cw_settlement_obs.py:49-50」——:49-50 为生效第二定义 ✓，无 :37-38 引用残留 |
| L15-3 design 口径差 | **已修** | design :64 开闸门补「∧ 缺环率（单一源 = details §9）」；design :48 改「构造唯一点三路入环」（注：details/landing 侧同句未同步 → 中-①） |
| L15-4 双口径限定词 | **已修** | details :71「首句为原始加成口径的 g 换算展示，非判据阈值——判据阈值见句末净值口径」+ 净值口径括注 |
| L15-5 零接线精确化 | **已修** | 契约 2「合成链零现役接线（marginal_value 经基线核另有消费链，与本判据无关）」——消费链实核：cw_events.decide_encounter :673 import → cw_survey19_hooks.encounter_tier_score :22 → marginal_value，表述与代码逐位一致 |
| L15-6 E-2 文件面补齐 | **部分修复** | telemetry/schema.py 已入 landing :33 文件面 ✓（OutcomeRecord :561 现无双字段，义务成立）；cw_settlement_obs.py 装配位形态未注明（列低-①） |

## 六、已攻击且未发现问题的面对账

1. **判别子与 GameState 写端全链**：observe/carry/write_logic/relay 四口 source 值（:2278/:2291/:2343/:2351）、四态词表 :220、Field 默认、carry 空值早退、简报回退写 session 不写 BoardState（cw_screen_briefing.py:183-186）、enemy_difficulty 全库写端枚举（BoardState 侧仅 cw_observation :2568 observe/:2571 carry 两口）——details :70 三句代码事实断言与 W10 判别子全部成立。
2. **三路拓扑与守卫位置**：RoundOutcome 构造唯一点全库唯一（src grep `RoundOutcome(` 仅 cw_settlement_obs.py:487）；胜局 :647 / 1f :546 / 3b :818；W239 :372-375；1f 不落账（:418 `if not telemetry_only`）；3b 单路径 :812-818；页 1 双暂存采集 :722-744/:770-795、合并消费 :377-382/:384-387/:395-405/:406-417 行号全准；「±N 暂存跨场滞留可翻转胜局行 killed」机理核实成立（分支 2 暂存后 1f 行 killed=None return 跳过消费的路径存在）。
3. **暗装行为等价与接线面**：mandate EV 核双槽 None 期 → 肢 2（奖励未立）恒触发 → `_fail_low`（encounter.py:369-374）恒最低难零刷新，与 W4「逐位一致」一致；strategy_id 值域收缩 mandate_v1（currency_war_config.py:74-83）；基线核 cw_events.decide_encounter :644 在册无现役、flow.py:539-543 dormant 转发与 details §7 表述一致；单卡/无选项帧行为三核一致（encounter.py:345-349、cw_events:659-660、handler idx0 default）；`cw_events` journal 决策行 :320/:438 在册。
4. **ADR-0536 退役融合**：decisions/0536 文件已删（glob 零命中）、INDEX.md :424 墓碑行（语义承接 = 13_pick_family E3 行、编号不复活）、13_pick_family :20 E3 行已改指代码本体无 ADR 指针；现存代码引用直调计数 bridge 3（:145/:148/:149）/ encounter 10 / provisional 4 与 landing 申报逐位一致；provisional.py:96-102 浮层未建档锚准确。
5. **判据源引用**：economy.md:107（档位 {0,10,20,30}）/:109（1.052^18 口径）/:111（遭遇·首领 −4）全准；combat.md:32（遭遇比 boss 凶）/:38-48（达标制 + [27] 采集点）/:62-64（g=1.052 V3.7 拟合）全准；plane_schedule_observed P2 序列（battle/battle/补给/battle/遭遇/奖励/boss）与 §4 案例走查、环深 R_after=3 推导一致；user_playstyle [39] :273-274 收口③⑤与裁定 3/契约 5 语义一致（:274 行号准）；advantage_layouts.md:17 刷新重置语义准；math_proofs P15 索引行（:27）12.18 [10.32,14.24] 与 README ~12.2 一致；P15v2_REPROOF.md 在档（proofs/validations/）。
6. **代码事实申报面**：_normalize_node_type :580-587（含「精英」）；cw_node_obs :29-30 词表/:55 漏读默认档 1/:36-75 读数每卡单条（多件未结构化断言准）/:231 三钻集；EQUIPMENT_ROSTER :233、EQUIPMENTS :51、EQUIP_TOOL_CATEGORY :42 三注册表在位；cw_performance docstring :109 过期断言真实（damage_dealt 已灌值 :453/:494、enemy_hp_after 无写端）；telemetry/schema.py :561 OutcomeRecord 现无双字段；cw_board_state.py 壳已删；RoundOutcome 现役无双扩字段；performance.history 归宿（cw_strategy_session.py:192）；board_state_of 快照链 :284/:406；盲选 chosen_encounter 不写守卫 :217-218；sim 无遭遇决策段（cw_screen_encounter.py:37-38 docstring）；Settlement 准入注释「无决策消费」:547 在册待修订；cw_investments :364 遭遇·首领 −4 修改器注册在册。
7. **判据数学与状态机**：§2 状态表互斥完备性走查（胜/败/删失组合 + 删失优先于 fill 分支 + 保守单调取向）无漏格；暗装短路在窗口提取之前（W4 零刷新与 W3 不足态 refresh=True 不冲突）；条语义判为 (b) 的保守回退臂与 W2/W11 回写面闭环；锁表表注（三常量 + 条语义注入态）E-2/E-3 两阶段口径一致；经验档层空证据弃权、负证据无时效门、盲选行 encounter_tier=None 与 `_record_chosen` 守卫互洽；W9/W10/W11/W12/W13 锁面与代码可行域一致；边际难度账本（cw_difficulty_account）成分缺口断言（品质/−4/Δ_t 缺）与代码体相符。
