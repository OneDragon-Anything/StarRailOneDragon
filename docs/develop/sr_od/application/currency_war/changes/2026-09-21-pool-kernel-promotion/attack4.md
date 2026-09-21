# 2026-09-21-pool-kernel-promotion 设计对抗审查报告(核一·无前提攻击·第四轮)

- 攻击对象:`design.md`(单文档方案,定稿态;已吸收前三轮 attack.md/attack2.md/attack3.md 全部发现的重写稿)
- 审查标准:`docs/develop/harness/iteration-design.md` §5 写作硬规则、§7 攻击面(核一)
- 审查方式:全库 grep 对账 + 源码/测试仓/权威源逐点核验,无预设焦点;全新上下文,前三轮发现仅作 A 部分核对输入
- 路径约定:证据路径省略前缀——src 侧 = `src/sr_od/application/currency_war/`,测试侧 = `sr-od-test/test/sr_od/application/currency_war/`,changes 侧 = `docs/develop/sr_od/application/currency_war/changes/`
- 工作树实况说明(核锚时点):r3 时在飞的三批已全部 commit 落地——投资两屏迁移/投资 pick 拆类 `0358aa60a`、获得链扩员(效果面拆出 cw_gain_effects)`8b882118b`、冶金炉作用域白名单 `b51e792c2`;另有 r3 后新落地的银狼卖价档感知批 `7b9c0d158`(bench_char_cost 档感知 + 四处账实卖价链传 gs)。工作树仅剩 `changes/2026-09-21-tool-gain-report/README.md` 一处未提交修改。**全部锚点按当前工作树实况核对,池批自身文件面的锚零漂移**(详见「核验通过面」1);邻批落地引发的交叠面变化见 B 部分发现。

---

## A. 前三轮发现(F1–F20)修订核验

| 项 | 结论 | 核验要点 |
|---|---|---|
| F1 [major] M21 测试仓消费未申报 | **落地** | §1.1-3「src 侧零消费 + 测试仓有消费」与实况一致(两符号 import 在 `test_cw_sim_equips.py:50/:53`,旧口径断言 :148-155,现核吻合);§2.4 :161-162 退役改面具名、§2.6 :184-185 文件面含该文件。 |
| F2 [major] 证伪可检测性申报无支撑 | **落地** | §2.5 held 键行 = 「同名即同档定谳无例外(2026-09-21 追加在架卡),按名归并即正确,无证伪分支」;「由观察对账暴露再升」全文清除(grep 无残留)。 |
| F3 [minor] import 方向笔误 | **落地** | §2.0 :86「import 方向 = sim→kernel(合法且现役;kernel 全域零 sim import)」;kernel/ 全域零 sim import 现树复核属实。 |
| F4 [minor] 依据指针失效 | **落地** | 副本数依据 = `research/economy.md` §1;「包布局矩阵」已改可核验表述「kernel 全域零 sim import,grep 实测」。 |
| F5 [minor] extra_experts 现役事实未申报 | **落地** | §1.4 :76「生产零传参(唯一调用方 `cw_sim_engine.py:528` 不传,传参仅测试)」——engine :528 现核无该参;§2.1 :97-98 同口径呼应。 |
| F6 [minor] 头注改写范围不全 | **落地** | §2.3 :137-140「M21 段整段重写」点名「星级×上场态双输入」句与「池面天然只出 3 费档/无需额外过滤器」句——与现行头注 `cw_sim_special.py:9-11` 两处旧口径逐一对应。 |
| F7 [minor] 对拍基准未定义 + 测试动作不具名 | **落地** | §2.0 :87「等价锁 = 现役测试原样随迁(§2.4)」;§2.4 具名:`test_cw_sim_pool.py` 1 文件 7 测、import 切换、3 直测 :54/:69/:89(与实况逐行吻合)、文件名不改。 |
| F8 [minor] changes/ 引用随迁 | **落地** | §2.1 :100-103「头注与 docstring 重写(非逐字随迁)…禁携带原文件的 changes/ 引用」(现行 `cw_sim_pool.py:3-4` 自引 changes 正本属实,待迁移处置)。 |
| F9 [major] 契约空间与交付空间不一致(≥9 耦合) | **落地** | §2.2 :118-128 双出口(`drawable_names` 商店出口三条件 / `grant_bucket_names` 授予出口无 ≥9)+ §2.5 取舍表同口径;两出口共用 `_remaining_and_held` 单源。 |
| F10 [minor] 迁移清单缺 `_remaining_and_held` | **落地** | §2.1 :94-96 五函数含私有共用体,签名与实况逐字吻合(:33/:54/:73/:90/:100)。 |
| F11 [minor] docstring 层 changes/ 节号标记与禁引冲突 | **落地**(r3 注记保留) | §2.1 :100 头注与 docstring 一并纳入重写;「其余函数零改动」按语义层读(与 docstring 重写并存),实现者可自行调和,维持 r3 判定。 |
| F12 [minor] §1.2 化石论证 | **落地** | 残句「旧档桶全桶不可抽」已删——grep「旧档桶」仅剩 :159「旧档桶账面不出负值」,是守恒跨档安全锁的申报(升费后账面 remaining 不为负),主语与语义均正确,非化石。 |
| F13 [minor] 追加定谳记录指针缺失 | **落地** | §1.2 :45-46「两段记录处 = `research/equipment_mechanics.md` §7 升费边角段」——实核 §7 :162-174 两段定谳都在(同名即同档 :164-167、在架卡 :168-170;另有 :171-172 卖价段为 r3 后新增,与本批无关,不碍指针);design.md 对 changes/ 的互引已清零(grep 证实)。 |
| F14 [minor] 守恒炸错文案指错病灶层 | **落地** | §2.0 :104-105「文案去层归因:原『sim 内部 bug』改『池派生与持有约束不一致』(测试零断言该文本)」——测试仓 grep「sim 内部 bug/牌池守恒破」现树零命中复核属实;现行文案在 `cw_sim_pool.py:83-85`。 |
| F15 [minor] sim 开局抽名点未入边界表 | **落地** | §1.4 :77 点名 `cw_sim_opening.py::_uniform_char_of_cost(:87-93)`,锚实况吻合;「第二处」计数已随 F18 修订移除。 |
| F16 [minor] 试用句失效指针未入重写范围 | **落地** | §2.3 :139-140 点名「试用角色」句一并处置、定性 §7 指针失效、试用权威改指 `docs/game/gameplay/currency_war.md:81`(现行错指针仍在 `cw_sim_special.py:21-22`,属待迁移现状,申报正确)。 |
| F17 [minor] 状态行过程叙事 | **落地** | §0 :8 状态行 = 「定稿(试读过;对抗报告 = 同目录 attack.md / attack2.md / attack3.md)」——轮次号、发现计数、「全量清偿」等过程叙事已清零(grep「清偿/r1/r2/r3/修订/本轮/已改」零命中)。「试读过」= 定稿门槛组成部分,报告指针 = 同目录文件指针非叙事,判合规;边缘注记:报告清单与 README 进度节职责重叠,信息住 README 即足,设计侧保留不构成违例。 |
| F18 [minor] 边界清点失真(晶矿采样器已在役) | **落地** | §1.4 :78 奖励球行改现状申报:「`kernel/cw_ore_reward.py:88-92`(REFRESH_PROB 抽档 + 注册表均匀抽名,零池感知;v0 披露在册;消费 = `collect_ore.py:135`,实机/sim 同用)已落地在役,归其本批申报;本批点名不迁」——两锚现核吻合(cw_ore_reward :88-92、collect_ore :135)。 |
| F19 [minor] grant 出口消费契约两维未闭 | **落地** | §2.2 :121-124 双维披露(≥9 维 `grant_bucket_no_nine_filter_v0` + 分布维 `grant_bucket_uniform_by_name_v0` 按名均匀);:125-127 调用时序契约(「先回归后重抽」引 `invest_effects.md` B 类;消费方须先写落容器再采样;merge_step_once 不适用)——`invest_effects.md:69` 现核逐点吻合。 |
| F20 [minor] 在架卡重标未随定谳传播到 M22 边界 | **落地** | §2.3 :146-148「⚠️ 在架卡重标不归池(sim 商店卡 cost = 发牌时快照,`cw_sim_shop.py:91-93`;实机买卡透传同源)——sim 若模拟升费,在架重标是商店面独立腿,归 M22 申报」;§1.4 :75 M22 行补「在架卡重标半腿不归池…M22 需单列(§2.3)」;§2.3 :145 已收紧为「**池出口**自动跟上」。`cw_sim_shop.py:91-93` 快照实况吻合。 |

**A 部分结论:20/20 落地**(F11/F17 带边缘注记,均不构成再设计点或违例)。前三轮全部 major(F1/F2/F9)的修订经现树复核成立。

---

## B. 本轮新发现(编号续接第三轮,自 F21 起)

### F21 [minor] | design.md §1.4(「策略估值族档传参」排除行) | r3 后卖价档感知批(7b9c0d158)部分清偿了设计所引挂账清单的「卖退款」行,残留的预期回金估值半腿在两份挂账之间无认领——排除行引用的清单已与实况分叉

- **发现**:§1.4 :74 排除行「策略估值族档传参(`refresh_prob` 等)| 精度面,另行挂账(银狼升星记账批 §2.6 已列)」引用的清单,现状 = `changes/2026-09-20-yinlang-starup-accounting/design.md` §2.6 :228「卖退款 `sell_refund`×`bench_char_cost` | **未定谳** | ❌ | 实机采证账」+ :229「估值概率族(refresh_prob/DISTINCT/POOL_COPIES 调用方传参)| 当前档 | ❌ | 估值族账」。r3 后 `7b9c0d158` 已定谳(升费后卖价按新费用档,记档 `equipment_mechanics.md:171-172`)并把**账实半腿**迁完(sell_bench.py:101 / sell_deployed.py:67 / cw_effect_inventory.py:798 / telemetry/schema.py:187 四处传 gs),但清单两行未回写,且**估值半腿**(预期回金判据/注记,不带 gs 七处:`sell_gate.py:1019`、`shop.py:1165`、`criteria/sell.py:134/:287/:384`、`prep_actions.py:548`、`tool_use.py:479`)既不在已清偿的「卖退款采证账」(已定谳)、也不在 :229 所列「估值**概率**族」(refresh_prob/DISTINCT/POOL_COPIES,不含卖退款组合)——成为两账之间的无主面。后果量级:升费银狼(3→4/5 费)在这七处按注册表起始费估价,1★ 卖价少算 1 金、2★ 少算 3 金;判据面(`sell_gate >= gap`、criteria 凑金)低估回金 → 方向保守(不卖/少卖),非账实错误。设计本身的双口径论述无矛盾(§1.2 :24「读口 = `cw_economy.effective_cost`」指档感知读口唯一;`bench_char_cost` 不带 gs = 起始费属静态口径,合法),缺口在**排除行引用的挂账依据已失准**,按引用追账会追到「未定谳」的过时行。
- **证据**:`changes/2026-09-20-yinlang-starup-accounting/design.md:93/:228/:229`;commit `7b9c0d158` 文件面(sell_bench/sell_deployed/cw_effect_inventory/schema + equipment_mechanics 记档);不带 gs 调用面七处(行号如上);`kernel/cw_economy.py:144-160`(bench_char_cost 双口径分支)与 :172-178(effective_cost docstring「语义双轨边界…挂账清单见设计 §2.6」同指该失准清单);sim 侧卖卡复用 kernel 账实腿(`sim/cw_sim_actions.py:121-123`)→ sim 卖价档恒 None 归约起始费,行为不变(设计「sim 无害透传」前提不受影响)。
- **修正方向**:§1.4 该行补现状半句(「卖退款账实半腿已随卖价档感知批定谳迁移;预期回金估值面(不带 gs 的 sell_refund×bench_char_cost 判据/注记)仍挂估值族账」);治本 = starup §2.6 清单回写归该批维护,不塞本批。

### F22 [minor] | design.md §2.0/§2.1 | 守恒炸错「语义原样」只申报了文案层,未申报炸错宿主从 sim 迁 kernel 后的后果变化:实机效果链消费时 raise = 上抛 = run 停,且实机 held 派生自带观测噪声,「负值不可能由合法动作产生」的 sim 论证对实机不成立

- **发现**:§2.0 对守恒炸错的申报 = 文案去层归因(:104-105)+「守恒炸错……语义原样」(:85)。炸错行为本体(raise ValueError,`cw_sim_pool.py:82-86`)原样迁 kernel 是合理基线,但**同一炸错在两个宿主层的后果语义不同**,设计未申报:①sim 语境——引擎自写容器、自洽性有保证,炸 = sim 内部不一致 = sim 局失败;kernel/实机语境——效果批(全员晋升等)将来经 `grant_bucket_names` 消费,raise 穿 `cw_gain_chain`(仅有的两处 try/except :453-455/:558-571 均为登记腿 best-effort,主写腿不兜底)与 action_report 链上抛 = operation 失败 = 实机 run 停(停机现场处置归 od-dev-stop-hooks 协议域)。②触发面扩张——炸错的不可达论证住 `remaining_pool` docstring(:94「负值不可能由合法动作产生(买上限受池约束)」),这是 **sim 语境**论证;实机侧 held 由观察容器派生(bench/deployed 读数),观测噪声(单位身份/星级误读)可造 held > fixed 形状(如 3★ 银狼在场 + 误读另一单位为银狼LV.999),炸错触发条件从「内部 bug」扩为「观测噪声也可触发」。设计对这两点均无申报——读者只能从「语义原样」反推,而「原样」恰是 misleading 的(宿主变了)。
- **证据**:`sim/cw_sim_pool.py:82-86`(炸点)/:94(合法动作论证);design.md :85(:84 段)/:104-105;`kernel/cw_gain_chain.py:453-455/:558-571`(登记腿才兜底);效果批消费前置现状 = 全员晋升零逻辑写观察收口(`cw_effect_inventory.py:728-730`)——炸错当前无实机发生面,效果批接管采样后成立,故 minor。
- **修正方向**:§2.0 补一句申报(「炸错宿主语义:kernel 版炸错 = 池派生输入不一致的显式暴露,穿消费链上抛(实机 = run 失败停机);实机侧 held 为观察派生,观测噪声可触发;效果批消费时的捕获/留证降级形态归效果批申报,本批保留直接炸」)——声明面一句,不改执行面。

### F23 [minor] | design.md §2.1/§1.4(U10 行) | grant_bucket_names 透传 extra_experts 的「保留透传」缺信息源申报:设计定稿后落地的「骇客专家:银狼」效果含商店池腿(零容器写),效果批将来拿什么填该参数无答案

- **发现**:§2.1 :97-98「`extra_experts` 生产零传参为现役事实,随 U10 披露保留透传」——保留口径对存量 `drawable_names` 成立(测试回归在用),对**新增的** grant 出口,申报没有回答消费方的信息源问题。r3 后 `8b882118b` 落地的效果面给出具体案例:「骇客专家:银狼」(`kernel/cw_gain_effects.py:77-142`)的第 2 腿 = 「银狼加入本局商店池——**商店池无容器字段(逐帧观察为真值),零容器写**,遥测行申报」(:85-86,:110-114 `shop_pool_decl` defect 行)。这正是 U10「专家入池」的首个现役效果实例,而它的入池状态**无处读**:效果批将来消费 `grant_bucket_names` 时,要么从 `active_strategies` 派生(卡在册 ⇒ 专家已入池——派生口径需设计),要么新增容器状态(观察链批已明示商店池无字段)——实现者自择 = 撞「实现者无需再设计」的墙。另有一层未定谳被透传形状隐含:「专家 ∈ 授予采样空间」无任何定谳(骇客专家入的是**商店**池;授予通道是否含专家未裁),透传参数的存在暗示了该形状却无依据标注。
- **证据**:design.md :76(U10 行)/:97-98;`cw_gain_effects.py:85-86/:110-114`(shop_pool 零写腿);`sim/cw_sim_pool.py:46-50`(extra_experts 通道 = fixed_pool 具名追加)。执行面不受影响(本批只建出口,消费归效果批),minor。
- **修正方向**:§2.1 或 §1.4 U10 行补一句:「专家入池状态的载体(active_strategies 派生或新增容器状态)与『专家可被授予』的定谳随 U10/效果批;本批透传仅为与 drawable_names 签名对称的扩展位」。

### F24 [minor] | design.md §1.4/§2.5(装备池排除行) | 「对拍锁已护」的依据在冶金炉白名单批(b51e792c2)后失真:锁的等值域收窄至白名单内,且 sim 引擎冶金炉腿(无白名单旧口径)与实机定谳分叉、无披露

- **发现**:§1.4 :72 与 §2.5 排除装备池统一的理由 = 「对拍锁已护」。r3 后 `b51e792c2` 给 kernel 侧 `furnace_mutate_pool` 加了作用域白名单(简易/进阶,非白名单 fail-closed + 越白名单穿戴件保留留证),**sim 侧 `furnace_reroll` 未同步**(`cw_sim_equips.py:282-290`,仍对任意注册表装备出同类别池),而 sim 引擎冶金炉动作走的就是这条旧腿(`cw_sim_engine.py:423/:426/:434` → `apply_furnace_equip_mode` → `furnace_reroll`)。后果:①对拍锁(`test_cw_tool_use_report.py:214-226`)现态仍绿,但样本域已如实收窄到白名单内(:217 注释「样本限作用域白名单内」)——「两实现等价」的声明域从全域缩为白名单内;②sim 引擎对非白名单目标(特殊件)会变异(旧行为),实机定谳 = 拒绝(白名单)——**sim 行为与实机定谳分叉且无披露键**,sim 校准/对拍数据在该域被旧口径污染。排除裁定本身仍成立(装备池统一有自己的「问题→方案→验收」闭环,按 iteration-design.md §1.1 自成新迭代),但设计用来支撑它的依据现状描述失真。
- **证据**:design.md :72/:176;`tool_use.py:85-97`(白名单定谳)/`cw_sim_equips.py:282-290`(无白名单)/`cw_sim_engine.py:434`(sim 腿消费);`test_cw_tool_use_report.py:214-226`(锁绿,样本域收窄申报在册)。装备池统一归另批,本批执行面不受影响,minor。
- **修正方向**:§1.4 装备池行按现状改写(「对拍锁(白名单内)在册且绿;白名单批后 sim 冶金炉腿未同步白名单、与实机定谳分叉无披露——归装备池统一批申报处置」);sim 腿分叉本体归装备池统一批/白名单批补披露,不塞本批。

### F25 [minor] | design.md §0/§1.1 | 迭代存在前提「2026-09-20 采样空间定谳」无持久记录处:全库唯一转述在 starup 批 changes/ 设计件内,寿命脆弱——与 F13 已修的同类问题同族残留

- **发现**:§1.1 :19-20 引「用户机制定谳(口述·权威 2026-09-20):随机获取角色效果的采样空间 = 剩余池对应费用档桶」——这是本迭代立项的直接前提(§0 迭代目标同措辞),但设计未给记录处,且全库核验:game 侧两份记档文件(`equipment_mechanics.md`/`invest_effects.md`)均无此定谳条目;唯一转述 = `changes/2026-09-20-yinlang-starup-accounting/design.md` §2.7:239-240(changes/ 寿命,清理即死);`invest_effects.md:69` 全员晋升条只蕴含「采样在回池后的池上」,未写「费用档桶」全称,不构成等价记档。F13(在架卡定谳补 §7 指针)已确立「口述定谳应有持久记档处」的先例,本条是同族残留——依据标注规则(§5 规则 1)下,读者无从对账这条定谳的原文与边界。
- **证据**:design.md :5-7(§0)/:19-20(§1.1);game 侧 grep「剩余池」仅 `invest_effects.md:69` 一处且非该定谳;`changes/2026-09-20-yinlang-starup-accounting/design.md:239-240`。
- **修正方向**:game 侧补记档(`invest_effects.md` 随机授予族或 `economy.md` 采样空间条,注 2026-09-20 口述出处)后设计引持久指针;或最低限度在 §1.1 并列现有最持久出处(starup §2.7 转述 + invest_effects.md:69 印证)并声明寿命。

---

## 试读(假自己是实现者,凭当前版 + 当前工作树能否开工)

**能开工。** 逐项(r3 试读重走,邻批落地后复核):

1. **`kernel/cw_pool.py`**:五函数 + `EXPERT_COPIES_ASSUMED` 清单具名,签名与实况逐字吻合;import 面 = {data.cw_chars, data.cw_shop_odds, kernel.cw_game_state, kernel.cw_economy}——cw_economy 虽被 7b9c0d158 改过(bench_char_cost 档感知分支),`effective_cost` 签名与语义未变,import 面无暗礁;头注/docstring 重写规则、守恒文案改句、唯一语义改造点(过滤 → `effective_cost`)与 None 归约语义均有代码锚。
2. **测试动作具名且现况吻合**:`test_cw_sim_pool.py` import 面 = :28-34 五个公开名(现状确认);7 测(:54/:69/:89/:107/:125/:139/:148)、3 直测行号精确;:63-64 extra_experts 传参回归与 :65 `match='注册表'` 断言随迁仍成立。新锁四条构造先例在册:≥9(:95 3★=9 副本)、档 = 4 写点(`pick_planner.py:213`/`deploy_move.py:131` 现核)、双出口分野(3★+低星组合构 held ∈ [9,26])、守恒跨档。`test_cw_sim_equips.py` 改面 = 删 :50/:53 两 import + :148-155 整测,留守三符号(:51/:52/:54)不受累。
3. **近自明微选择(不阻塞,与 r3 相同)**:披露键常量的宿主/形态;「其余函数零改动」按语义层读(A 表 F11)。

---

## 核验通过面(逐项核过、无发现)

1. **符号/锚全量核实,池批文件面零漂移**(工作树实况,含四批邻批 commit 后):池四函数 + 私有(`fixed_pool`:33/`held_copies`:54/`_remaining_and_held`:73/`remaining_pool`:90/`drawable_names`:100)、档过滤行 :109、守恒炸错 :82-86、唯一消费方 `cw_sim_shop.py:43`(import)/:87(调用)、发牌快照 :91-93、`cw_sim_special.py` :39/:45-58(两死符号)/:21-22(试用句)/:9-11(头注旧口径)、`POOL_COPIES_PER_CARD` = `data/cw_shop_odds.py:33`({1:27,2:27,3:9,4:9,5:9})、`effective_cost` = `kernel/cw_economy.py:166`(None→3 归约 :185,docstring :167 申报「随机授予采样空间」辖域)、`cw_sim_opening.py:87-93`、`cw_ore_reward.py:88-92` + `collect_ore.py:135`、engine deal_shop :528(无 extra_experts)、pick_planner 档写点 :213、deploy_move 档写点 :131。
2. **包布局与档写点复核属实**(邻批后):kernel/ 全域零 sim import;sim/ 全域零 `lv999_cost_tier` 写点(grep 现树零命中)→ §2.3「档感知对 sim 无害透传」前提现树成立。
3. **在飞/邻批交叠核(任务指定)**:四批 commit(`0358aa60a` 投资两屏 + pick 拆类、`8b882118b` 获得链扩员、`b51e792c2` 冶金炉白名单、`7b9c0d158` 卖价档感知)的文件面与池批文件面(`kernel/cw_pool.py` 新建 / `sim/cw_sim_pool.py` 删 / `sim/cw_sim_shop.py` / `sim/cw_sim_special.py` / 两测试文件)**零同文件交集**——无同文件冲突风险。在飞面无新增「按档抽名/池消费」:`cw_gain_effects.py` 全文唯一采样 = `roll_hacker_mod`(装备硬编码名单池,披露键在册,非角色按档);`pick_invest` 拆类(pick_invest_env/pick_invest_strategy)不涉池;效果消费前置 `apply_board_rewrite` 现态 = 全员晋升零逻辑写观察收口、人力重组出售面确定性退款(cw_effect_inventory.py:721-738),均不经池出口。效果批将来接 `grant_bucket_names` 的挂载点(获得链 `on_strategy_gained` 回调机制)已随 `8b882118b` 就位,与 §2.2 时序契约兼容。
4. **B2 附带核(任务指定问项)**:①`effective_cost` docstring 的「两口径不互借」句与 bench_char_cost 新分支的关系——docstring :172-174 的分野指「未注册名 0 vs 未知 3」,bench_char_cost 自身 docstring(:145-149)完整申报了带/不带 gs 双支语义,代码层自洽;失准面在挂账清单文档,归 F21。②sim 侧卖价模型——sim 卖卡动作复用 kernel 账实腿(`cw_sim_actions.py:121-123`),sim gs 档恒 None → 卖价 = 起始费,行为不变;sim 将来写档(M22)则卖价腿自动跟上,与 §2.3「池出口自动跟上」申报同构且覆盖面更宽,无矛盾。③`cw_intention.py:689` 的 `sell_refund(star, cost) != cost` 判定(1★ 全额退)与档无关,不受分叉影响。
5. **权威源对齐**:`equipment_mechanics.md` §7 升费边角段(:162-174)现状 = 三段定谳(同名即同档/在架卡随升费同变/卖价随新费用档),§1.2「两段记录处」指针落在本批相关两段上;`invest_effects.md:69`(先回归后重抽 + ≥9 未证 + 均匀 v0)与 §2.2 双维披露互洽。
6. **治本核**:§1.3 归层(架构层/模块归属)成立——池升格 = 根因修复;在飞批无绕开池另起第二份**池派生**的苗子(gain_effects 的骇客改件池是装备名单池非角色池,F23 的 shop_pool 腿是零写申报非第二派生)。装备池排除裁定按 iteration-design.md §1.1 判据(独立闭环)防得住;「另批统一」边界在 F24 申报现状修正后仍防得住。§1.4 按档抽名清点(F18 修订后)= 池出口 + sim_opening + ore_reward 三点具名,完备性经 grep `chars_by_cost`/池函数消费面对账无第五点。
7. **依据标注逐条核**(除 F25 外均实):副本数(:38 → cw_shop_odds.py:33 逐值吻合 + economy.md §1)、同名即同档两段记录处(:45-46 → §7 现状)、effective_cost 辖域(:48 → :167)、sim→kernel import 现役(:50 → cw_sim_pool.py:23)、测试面基线(:51-53 → 现况逐行)、装备池对拍锁(:56 → 锁绿但见 F24 域注记)、sim_opening(:77 → :87-93)、晶矿采样器(:78 → :88-92/:135)、时序定谳(:126 → invest_effects.md:69)、发牌快照(:147 → :91-93)。

---

## 总结论

**修订后收敛(无结构性返工;全部发现为声明面点状修订)。**

主体方案(搬家非重写、双出口、M21 退役、透传形态、测试随迁等价锁)经第四轮全量复核继续成立;池批自身文件面的锚在四个邻批 commit 落地后的工作树上零漂移,池批与在飞/邻批无同文件冲突。本轮无 major;5 条 minor 全部是 **r3 后邻批落地引发的交叠面声明缺口或依据失真**(F21 挂账清单引用失准 + 预期回金估值半腿无认领 / F22 守恒炸错跨层后果未申报 / F23 extra_experts 信息源未闭合 / F24 装备池排除行「对拍锁已护」现态失真 / F25 立项定谳无持久记录处),均不动执行面;其中 F24 附带的 sim 冶金炉腿与实机定谳分叉是行为面事实,但归属装备池统一批/白名单批,非本设计缺陷。

计数:major 0,minor 5(F21 挂账清单失准 / F22 炸错宿主语义未申报 / F23 专家入池信息源缺口 / F24 装备池排除依据失真 + sim 腿分叉 / F25 立项定谳记录处缺失)。A 部分 F1–F20:20/20 落地(F11/F17 带边缘注记,不构成违例);F12 化石句与 F17 状态行过程叙事均已清净。
