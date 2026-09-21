# 2026-09-21-pool-kernel-promotion 设计对抗审查报告(核一·无前提攻击·第三轮)

- 攻击对象:`design.md`(单文档方案,定稿态;已吸收前两轮 attack.md/attack2.md 全部发现的重写稿 v3)
- 审查标准:`docs/develop/harness/iteration-design.md` §5 写作硬规则、§7 攻击面(核一)
- 审查方式:全库 grep 对账 + 源码/测试仓/权威源逐点核验,无预设焦点;全新上下文,前两轮发现仅作 A 部分核对输入
- 路径约定:证据路径省略前缀——src 侧 = `src/sr_od/application/currency_war/`,测试侧 = `sr-od-test/test/sr_od/application/currency_war/`,changes 侧 = `docs/develop/sr_od/application/currency_war/changes/`
- 工作树热态说明:核锚时点工作树未提交面 = 两份 game 侧 research 文档(`equipment_mechanics.md`/`invest_effects.md`,均为定谳记档)与本迭代目录本身;并行批(晶矿采样器/collect_ore 随机态接线)已以 commit `9e9c71db9` 落地。**全部锚点按当前工作树实况核对,零漂移**(详见「核验通过面」1)。

---

## A. 第二轮发现(F9–F17)修订核验

| 项 | 结论 | 核验要点 |
|---|---|---|
| F9 [major] 契约空间与交付空间不一致(≥9 耦合未决) | **落地** | §2.2 双出口成立:`drawable_names`(商店出口,档匹配 ∧ 剩余>0 ∧ held<9,三条件)与 `grant_bucket_names`(授予出口,档匹配 ∧ 剩余>0,不含 ≥9),披露键 `grant_bucket_no_nine_filter_v0` 具名;两出口共用 `_remaining_and_held` 单源。§2.5 取舍表「效果批出口」行同口径。授予出口无 ≥9 与 game 侧 `research/invest_effects.md:69`(全员晋升条:「是否受 ≥9 清空约束未证,采样建模按均匀 v0 + 实测校准」)两向吻合,无矛盾。 |
| F10 [minor] 迁移清单缺 `_remaining_and_held` | **落地** | §2.1 改「五函数…迁入(含私有共用体)」并逐一列签名——与实况逐字吻合(`fixed_pool`:33/`held_copies`:54/`_remaining_and_held`:73/`remaining_pool`:90/`drawable_names`:100);§2.6 文件面以 `kernel/cw_pool.py`(新建)整体覆盖。 |
| F11 [minor] docstring 层 changes/ 节号标记与禁引冲突 | **落地**(一处字面张力) | §2.1「头注与 docstring 重写(非逐字随迁):M06/U10/U11 等 changes/ 节号标记一律改语义表述 + 持久索引」+「禁携带原文件的 changes/ 引用」,与「唯一语义改造 = 档过滤」分层清楚。张力:同节「其余函数零改动」须按语义层读(与 docstring 重写并存),实现者可自行调和,不构成再设计点。 |
| F12 [minor] §1.2 化石论证 | **未完全落地** | 「残余数额无关紧要」半句已删;但同 bullet 残留其压缩形态「**旧档桶全桶不可抽**」(design.md:49)。无例外定谳下,升费后旧费用档桶对其余 3 费名照常可抽,该句按字面(主语 = 旧档桶)仍不成立、按另一读法(主语 = 银狼)则主语缺位——与 F12 攻击点同源的歧义残句,未按修正方向删除。 |
| F13 [minor] 追加定谳记录指针缺失 | **落地** | §1.2「两段记录处 = `research/equipment_mechanics.md` §7 升费边角段」——实核该文件 :144-172(§7)两段定谳都在(2026-09-18 :157-166、2026-09-21 在架卡 :168-170;该文件工作树有未提交修订,现态即含两段,指针落在实况上);§1.2 的 changes↔changes 互引已移除。 |
| F14 [minor] 守恒炸错文案指错病灶层 | **落地** | §2.0「守恒炸错文案去层归因:原『sim 内部 bug』改『池派生与持有约束不一致』(测试零断言该文本,改文案零代价)」——测试仓 grep「牌池守恒破/sim 内部 bug」零断言复核属实,现行文案在 `sim/cw_sim_pool.py:83-85`。 |
| F15 [minor] sim 开局抽名点未入边界表 | **落地(修出残留 → 本轮 F18)** | §1.4 补行点名 `cw_sim_opening.py::_uniform_char_of_cost(:87-93)`,锚实况吻合、等价条件(sim 不写档)与不迁裁定清楚。残留:行内「sim 内**第二处**按档抽名点」计数被并行批落地推翻——见本轮 F18。 |
| F16 [minor] 试用句失效指针未入重写范围 | **落地** | §2.3 点名「试用角色」句一并处置、定性其 `equipment_mechanics.md §7` 指针失效(实核 §7 :144-172 零试用内容,现行错指针仍在 `sim/cw_sim_special.py:21-22`)、试用权威改指 `docs/game/gameplay/currency_war.md:81`(实核 :81 = 试用角色,2026-08-13 用户确认)。 |
| F17 [minor] 状态行过程叙事 | **未落地** | §0 状态词换「定稿」,但括注过程叙事原样保留且加长:「两轮核一无前提攻击收敛:r1 major 2 + minor 6、r2 major 1 + minor 8 全量清偿,试读过」(design.md:8-10)——轮次号、发现计数、「全量清偿」正是 F17 攻击的过程叙事,规范卡点明列「『本轮/修订后/已改』类措辞即打回」。同文信息已合规落在 README 进度节,设计侧应删。 |

### 用户新定谳记档一致性(任务指定核对)

**一致,无矛盾。**「商店在架卡随升费同变」(2026-09-21)在设计侧三处转述互相咬合:§1.2(升费后全场银狼含在架卡一律新费用档 + 两段记录处指针)、§2.5 held 键行(「同名即同档定谳无例外(2026-09-21 追加在架卡),按名归并即正确」)——与 game 侧 `equipment_mechanics.md:168-170` 逐点吻合。`invest_effects.md:69` B 类全员晋升条(2026-09-21 用户裁定:**场上单位回归牌库,先回归后重抽,刚回归副本立即可被抽中;装备归属未采证两向皆可能;≥9 约束未证,均匀 v0**)与设计授予出口 v0 口径(不含 ≥9 过滤 + 披露键)互洽——但该条蕴含的**调用时序权威未进设计引用链**,见本轮 F19。

---

## B. 本轮新发现(编号续接第二轮,自 F18 起)

### F18 [minor] | design.md §1.4(殃及 §1.1 治本叙事) | 边界清点在并行批落地后失真:晶矿(奖励球)角色掉落采样器已是**在役 kernel 侧按档抽名点**,排除行仍按「候效果批未落地」口径写;sim 开局行「第二处」计数随之失效

- **发现**:§1.4 奖励球排除行写「奖励球是否池驱动采证 | 效果批辖」,把该面归为未落地的效果批辖域。实况:晶矿角色掉落采样器**已落地并在役**——`kernel/cw_ore_reward.py::roll_ore_reward`(:88-92)按 `REFRESH_PROB[level]` 抽费用档后 `rng.choice(chars_by_cost(cost))` **注册表均匀抽名**,零 held/剩余池/≥9 感知;消费点 = `kernel/cw_action_report/collect_ore.py:135`(实机上报函数,sim 经上报函数族同用,「sim 旁路接线」已随 commit `9e9c71db9` 落地);v0 披露面在册(`ORE_ASSUMPTION_KEYS`,`cw_ore_reward.py:44-49`;口径正本 = `docs/game/currency_war/research/sphere_rewards.md`、`game_state/logic-updates/collect-ore.md:11`)。「奖励球 = 晶矿」实名实证 = `docs/game/screens/currency_war_prep.md:72`。后果有二:①排除行的现状归属失真——这不是「候效果批采证」的未落地面,而是一个**已存在的第二采样模型**(注册表均匀 vs 本批交付的剩余池档桶),2026-09-20 池定谳与晶矿 v0(同日用户临时拍定)并存,晶矿角色掉落是否切 `grant_bucket_names` = 真开放问题,但设计让读者以为该面尚无代码;②§1.4 sim 开局行「sim 内第二处按档抽名点」计数失效(现役按档抽名点 ≥3:池出口、sim_opening、ore_reward)。F15 同类问题第二例——清点靠手工枚举、无完备性手段,按「同族第 2 件问共同根」,建议顺手把清点手段写进 §1.4(grep `chars_by_cost`/按档抽名全域)而非第三次手工枚举。本批执行面(文件清单/迁移清单)不受影响,故 minor。
- **证据**:`kernel/cw_ore_reward.py:88-92`(:22 import `chars_by_cost`)、`kernel/cw_action_report/collect_ore.py:135`、`cw_ore_reward.py:44-49`;`docs/game/screens/currency_war_prep.md:72`、`docs/game/currency_war/research/sphere_rewards.md:1-8`;design.md:76(奖励球行)、:80(「第二处」);changes/2026-09-20-logic-rand-sampling/attack.md:14-17(v0 口径与在册冲突的对抗史)。
- **修正方向**:§1.4 奖励球行改现状申报(「晶矿角色掉落采样 = `kernel/cw_ore_reward.py::roll_ore_reward` 已落地在役,现口径 = 注册表按档均匀,v0 披露键 `ore_*` 在册;是否切 `grant_bucket_names` = 未裁,候校准批/效果批,本批点名不迁」);sim 开局行去「第二处」计数;可选补一句清点手段声明。

### F19 [minor] | design.md §2.2/§2.0 | grant 出口的消费调用契约两维未闭:调用时序前置与采样分布对象均无申报,决定时序的 2026-09-21 定谳不在设计引用链

- **发现**:①**时序维**:出口是纯函数、只吃 gs,held 派生绑定「已落容器的状态」(`held_copies` 经 `bench_units_of(gs)`/`deployed_rows_of(gs)` 读容器,`sim/cw_sim_pool.py:61-63`;无工作副本/覆盖入参)。全员晋升定谳「**先回归后重抽**,刚回归的副本立即可被抽中」(`invest_effects.md:69`)⇒ 消费方唯一合法调用形态 = **先把回归/摘除写落 gs、再查询**(中间态进容器随机态行;gain-chain 的工作副本范式 `merge_step_once`,`kernel/cw_gain_chain.py:148`,对采样不可套用——工作副本上派生不出 held)。这一前置与「不支持投机采样」的边界,设计只写「随机面采样由消费方辖」一笔,消费方(效果批)只能从代码反推;且决定该时序的 2026-09-21 定谳未入设计引用链(§2.2 只引 2026-09-20 采样空间定谳)。②**分布维**:出口返回名集(去重列表,同 `drawable_names` 形态),消费方抽名分布(名均匀 vs 按剩余副本数加权)是真实语义分叉(各名剩余数不同:27 副本卡持有后 1..26 浮动);`invest_effects.md:69` 只写「按均匀 v0」未指均匀对象,设计披露键 `grant_bucket_no_nine_filter_v0` 只盖 ≥9 一维——分布维度两侧都没定。两维都不波及本批实现(出口本体语义已定),是声明面缺口,故 minor。
- **证据**:`sim/cw_sim_pool.py:54-70`(held 仅容器派生)、design.md:120-126(§2.2 出口契约,无时序/分布申报)、:90-92(§2.0「本批只供采样空间查询」);`invest_effects.md:69`(先回归后重抽 + 「均匀 v0」未指对象);`kernel/cw_gain_chain.py:148`(工作副本先例不可套用于采样的对照面)。
- **修正方向**:§2.2 grant 出口补两句:①「调用前置 = 回归/摘除写已落 gs 后查询;采样空间 = 已提交容器态的剩余池,不支持工作副本派生(时序权威 = `invest_effects.md` B 类全员晋升条,2026-09-21)」;②「抽名分布 v0 = 消费方申报面(建议名均匀,同 sim 发牌先例;校准随 `logic_rand_outcome` 收口)」。

### F20 [minor] | design.md §2.3/§1.4(M22 行) | 2026-09-21 在架卡定谳的「商店半腿」未随折叠传播:「零特例」申报只盖池出口,在架卡重标属商店载荷腿,M22 边界申报缺这半句

- **发现**:在架卡定谳被折叠进 §1.2(held 归并依据)与 §2.4/§2.5,但 §2.3 的透传申报(「sim 将来模拟升费动作写档,池自动跟上——接线自然,**零特例**」)与 §1.4 M22 行(「sim 银狼升费行为建模(planner 选择后变换)」)都只按池出口口径写。实况:在架重标**不归池**——sim 商店载荷的卡 cost 是发牌时快照(`cw_sim_shop.py:91-93`,`cost=cost, star=1, cost_source='roster'`;`cost_source` 三值词表 = `kernel/cw_game_state.py:506-510`;sim 买卡透传 `cost_source`,`kernel/cw_action_report/buy_card.py:95`),池出口跟档写只保证**后续发牌**正确,不重标已上架卡。M22 将来建模升费时,若按「写档 = 零特例」的现文理解,商店显示/买价腿会漏在架重标——恰是 2026-09-21 定谳明示的机制半边。非本批执行面问题(升费建模本就 M22 辖、§1.4 已排除),是定谳折叠不完整的边界申报缺口,故 minor。
- **证据**:design.md:141-144(§2.3「零特例」)、:78(§1.4 M22 行);`docs/game/currency_war/research/equipment_mechanics.md:168-170`(在架卡定谳);`sim/cw_sim_shop.py:91-93`、`kernel/cw_game_state.py:506-510`、`kernel/cw_action_report/buy_card.py:95`。
- **修正方向**:§1.4 M22 行补半句(「升费行为建模含**在架卡重标**(2026-09-21 定谳的商店半腿;sim 商店卡 cost 为发牌时快照,池出口跟档不覆盖此腿)」);§2.3「零特例」收紧为「**池出口**零特例」。

---

## 试读(假自己是实现者,凭 v3 能否开工)

**能开工。** 逐项:

1. **`kernel/cw_pool.py`**:五函数 + `EXPERT_COPIES_ASSUMED` 常量清单具名(签名与实况逐字吻合);头注/docstring 重写规则可执行(M06/U10/U11/M05 等 changes/ 节号 → 语义表述 + 持久索引,持久索引已给定 = `research/economy.md` §1、`data/cw_shop_odds.py`;禁携带 changes/ 引用;守恒文案改句已给);唯一语义改造点(过滤条件 → `effective_cost`)与 None 归约语义均有代码锚。
2. **测试动作清单具名且实况吻合**:`test_cw_sim_pool.py` import 切换面 = :28-34 五个**公开**名(私有函数不在 import 面,切换无暗礁),7 测/3 直测行号(:54/:69/:89/:107/:125/:139/:148)精确;新锁四条均可构造——≥9 清空构造先例在册(:95 单 3★ = 9 副本),双出口分野锁的「held ∈ [9,26] 1/2 费卡」由 3★/2★/1★ 组合即得(27 副本卡 remaining 恒正,held=9 即触发清空边界);档 = 4 写点先例 = `pick_planner.py:213`(`write_logic(gs.lv999_cost_tier, …)`);`test_cw_sim_equips.py` 改面 = 删 :50/:53 两 import + :148-155 整测,留守三符号消费不受累。
3. **仅剩两处近自明微选择**(不构成阻塞):披露键常量的宿主/形态(键名已定;先例 = 假设键常量面,`cw_gain_effects.py:48`/`cw_ore_reward.py:44`);「其余函数零改动」按语义层读(见 A 表 F11)。

---

## 核验通过面(逐项核过、无发现)

1. **符号/锚全量核实,零漂移**(工作树实况,含在飞 commit `9e9c71db9` 后):池四函数 + 私有(:33/:54/:73/:90/:100)、档过滤行 :109、守恒炸错 :82-86、唯一消费方 `cw_sim_shop.py:43`(import)/:87(调用)、`cw_sim_special.py` :39/:45-58(两死符号)/:21-22(试用句)/:6-11(头注 M21 段)、引擎 :159-162(只 import 留守两符号)/:473/:528-529(deal_shop 不传 extra_experts)、`POOL_COPIES_PER_CARD` = `data/cw_shop_odds.py:33`({1:27,2:27,3:9,4:9,5:9})、`effective_cost` = `kernel/cw_economy.py:158`(签名 `(gs, char_id)`,None→3 归约 :175-177,docstring :159 申报「随机授予采样空间」辖域)、`cw_sim_opening.py::_uniform_char_of_cost` :87-93。
2. **包布局与档写点复核属实**:kernel/ 全域零 sim import(grep 现树);sim/ 全域零 `lv999_cost_tier` 写点(写端仅 `pick_planner.py:213`/`deploy_move.py:131`)→ §2.3「无害透传」前提在现树成立。
3. **双出口与在库 gain-chain 无重复桶逻辑(任务 B2 指定核)**:`cw_gain_chain.py`/`cw_gain_effects.py` 全文零 `chars_by_cost`/池派生;`gain_character` 收具体 `(name, star)`(落位→回调→合成),采样全在调用方;在库唯一另一采样 = `roll_hacker_mod`(装备硬编码名单池,非角色按档,披露键在册)。按档抽名/池派生全域 grep 对账:池出口 + sim_opening(§1.4 已点名)+ `cw_ore_reward.py:88-92`(漏点 → F18);其余 `POOL_COPIES_PER_CARD` 消费 = 估值族(`statefn/odds.py:37`/`vopt.py:95`/`cw_line_switch.py:86`)与审计行,均在不解决表既有覆盖内。
4. **装备池排除面现态成立**:`tool_use.py` `furnace_mutate_pool`:87/`furnace_mutate_sample`:99(消费 :219/:258);同种子对拍锁在册(`test_cw_tool_use_report.py:187-209`,与 `cw_sim_equips.furnace_reroll` 逐次等值);`cw_affix_effects.py:278-282` 冶金炉行申报「采样池 = furnace_reroll 同源」——仍双实现 + 锁,与设计假设无冲突。
5. **权威源对齐**:`economy.md` §1(:8 副本数逐值吻合;:10 ≥9 =「清空该牌在**商店**的库存」——商店域措辞即 §2.2 双出口分野的定谳依据;:15 派生池不变量);`equipment_mechanics.md` §7 两段定谳(:157-170);`gameplay/currency_war.md:81`(试用权威)。
6. **治本核**:§1.3 归层(架构层/模块归属)成立——池是跨 sim/实机采样共享概念,升格 = 根因修复非症状;在飞批(晶矿采样器/gain-chain)没有绕开池另起第二份**池派生**的苗子(F18 是第二份**抽名口径**而非池派生,且自有 v0 披露域)。装备池排除面对拍锁已护、无未防护面。
7. **A 部分附带核**:`invest_effects.md:69` 与设计授予出口 v0 口径互洽(≥9 未证 ↔ 出口不含 ≥9 + 披露键);两文件工作树未提交修订内容即定谳记档本体,与设计转述一致。

---

## 总结论

**修订后收敛(无结构性返工)。** 主体方案(搬家非重写、双出口、M21 退役、透传形态、测试随迁等价锁)经第三轮全量复核继续成立;全部锚点在含并行批落地后的工作树实况上零漂移。本轮无 major;3 条 minor 均为**声明面**点状修订(F18 §1.4 边界清点按现状改写两行 / F19 grant 出口补调用前置与分布语义两句 / F20 M22 行补在架重标半句),另有两项第二轮发现的清偿缺口需补:F12 残句「旧档桶全桶不可抽」(design.md:49)删除、F17 状态行过程叙事(design.md:8-10)删除。

计数:major 0,minor 3(F18 边界清点失真:晶矿采样器已在役 + 「第二处」计数失效;F19 grant 出口消费契约两维未闭;F20 在架卡重标维度未随定谳传播到 M22 边界)。A 部分 F9–F17:7 项落地(F11/F15 带备注),F12 部分落地,F17 未落地;用户新定谳记档一致性核过,无矛盾。
