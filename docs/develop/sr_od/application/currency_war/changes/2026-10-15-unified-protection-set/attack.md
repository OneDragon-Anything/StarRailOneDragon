# 统一保护集(买卖身份同源) 对抗审查报告(第八轮)

> 审查对象 = 本目录 design.md / landing.md / README.md 三件套(全文精读,当前态)。
> 判据源 = strategy-docs 00/01/02/11/12(全文)、math_proofs P41/P46/P47/P49/P78/P86/P92/P96 行与 proofs 单篇(p77/p86/p96)、validations/P31_VALIDATION.md、现役代码(cw_intention.py 全文 1922 行 / shop.py 全文 2196 行 / sell_gate.py 全文 1098 行 / sell_candidates.py 全文 / buy.py 全文 / cw_card_identity.py 全文 / cw_engine_facts.py / cw_line_facts.py / bridge.py / flow.py 方向段 / entry.py 凑息与兜底段 / session_scope 关键读口 / mandate.py 计数键段 / cw_deploy_logic 锚点 / cw_comps 注册表段 / cw_chars 数据段;断言读代码体,docstring 仅线索)、测试仓 test_dead_stock_pair.py(实际载体直读)、玩法 research(stage_transitions Q2 / user_playstyle [22]/[28] 直查)、流程规范(iteration-design / strategy-work / sim-testing)、病灶局复盘报告实档(seed 与拒买锚逐行对),全部直调复核。
> 纪律声明:无前提独立攻击,结论只看证据;零过程叙事引用前轮报告内容。

## 1. 发现清单

### F1【重要】3.2 完成判据「`transition_release_names` src 消费面 grep 清零」在 3.2 自身边界内不可达——判据可达性破口

- 位置:`landing.md:33`(3.2 判据)↔ `landing.md:26`(3.2 边界)、`landing.md:43/:49`(3.3 判据);根锚 = `src/sr_od/application/currency_war/kernel/cw_card_identity.py:57-69`。
- 论断:3.2 要求「④分支/`transition_release_names`/`line_identity_tier` **src 代码符号消费面**零残留(grep 清零申报,域 = src + sr-od-test 消费点)」,但 `transition_release_names` 在 3.2 收口后仍有一个 src 代码级引用残留——`cw_card_identity.sell_hold_exclusion_names()` 函数体内对它的调用(`cw_card_identity.py:69`)。该函数的退役归 3.3(landing 3.3 范围明文「函数退役」),而 3.2 边界明文「卖面其余消费点不动(归 3.3)」。
- 证据(直调):
  1. `cw_card_identity.py:57-69`:`sell_hold_exclusion_names()` 返回 `frozenset(CORE_SINGLE_CARD_REGISTRY) | transition_release_names()`——函数体内部调用,非注释非文档。
  2. `transition_release_names` 全部 src 引用(grep 全量):`cw_card_identity.py:43`(定义)/`:69`(sell_hold_exclusion_names 内调用)/`:108`(line_identity_tier 内调用)、`mandate.py:1251`(deadlock 计数,3.2 范围重定义)、`shop.py:1089`(transition_hold_locked_frame 计数,3.2 范围重定义)、`shop.py:62`(import,④分支用,3.2 退役)。
  3. 3.2 收口自己的点(④分支、两计数键、line_identity_tier 函数与四个消费点)后,`:69` 的调用仍在——grep `transition_release_names` 在 src 命中非零,3.2 判据按字面不可通过。
  4. 要在 3.2 内清零只能改 `sell_hold_exclusion_names` 函数体——而其全部消费面(funding 兜底池/垫件谓词/P78-5′ 分支②/会话内筹资分支②,`sell_gate.py:1015`、`sell_candidates.py:425`、`entry.py:746`、`shop.py:1314-1318`)的迁移归属阶段 = 3.3(design §2.3 表「归属阶段」列),3.2 提前改函数体 = 越阶段改卖面行为,违 3.2 自身边界。
- 推理链:判据(账本立任务唯一源)按字面验收必然红;实现者只能私自收窄判据域(绕审拍板)或越边界改 3.3 归属面(违停手令)——两样都是流程事故。design §2.4 的退役判据原文(「src 代码符号消费面 grep 清零」)本身无错,错在 landing 把 `transition_release_names` 的清零时点整体放在 3.2。
- 修正方向:landing 3.2 判据把 `transition_release_names` 的清零排除项写死——「`cw_card_identity.sell_hold_exclusion_names` 函数体内调用除外,随 3.3 函数退役收口」;或把 `transition_release_names` 清零判据整体移入 3.3(与 `sell_hold_exclusion_names` 同批)。两案都不动 design。

### F2【重要】复现局行为锚「爻光被买入(首个买入差异)」与设计自身机制矛盾;「分叉后货架演化不可判」的豁免逻辑未一致适用;椒丘锚存在空转通过风险

- 位置:`design.md:129`(§2.6 复现局)、`landing.md:61`(3.4 完成判据第一条)。
- 论断:按设计自己的囤货臂机制推演,改后跑 seed 20261012 的**首个买入差异不是 r3 爻光**;且自首个差异帧起局轨迹分叉,r3 货架内容不可判——设计对饮月分支正是以「分叉后货架演化不可判」为由改为单帧 fixture 承载(§2.6 同段),却对爻光设局级断言,同一逻辑未一致适用;「椒丘全程不被卖」在分叉局中存在断言空转通过形态。
- 证据(直调):
  1. 病灶局 r1 店面含**三月七[1费]**(复盘报告实档 `.debug/temp/currency_war/sim_review_1/review_g_20261015_154239.md` §1 r1 op②:「店面 5 张 = 三月七[1费] 貊泽[1] 翡翠[1]×3……零购买」);三月七 = 列车同行成员(TRANSITION_PACK carry;`cw_chars` 注册表列车阵营)→ 属保护集过渡域成员(§2.1 四体系全体)。
  2. 囤货臂命中条件(design §2.2)= 保护集成员 ∧ 未持有首副本 ∧ 未锁定帧;r1 帧金 10 ≥ 1 费、备战席 8/9 有空位、未锁定——**r1 即命中囤货臂**(病灶局 r1 零购买是 op 层「开店未生效,sim 接缝」形态;若该 op 形态复现则 r1 无差异,则 r2 店面**停云[1]**(仙舟成员,复盘 r2 op②)同命中囤货臂)。无论哪种,**首个买入差异 ≠ r3 爻光**。
  3. r1/r2 买入改变金/备战席/状态后,后续货架为分叉演化——设计自己给饮月的豁免句(§2.6:「饮月分支由 r6 单帧 fixture 承载(**分叉后货架演化不可判**,不设局级断言)」)对爻光同样成立:分叉后 r3 店面是否仍出现爻光,设计无法断言。
  4. 椒丘在病灶局经 **r2 晶矿**到手(复盘 r2 op①:「入账:三月七、赛飞儿、**椒丘**……」),非商店路径;分叉局的晶矿产出序列随局演化,椒丘可能不入场——「椒丘全程不被卖」在椒丘缺席局**空转通过**,不构成卖面修复的行为证据。
- 推理链:3.4 第一条完成判据(行为锚断言 = 病灶翻转)按设计机制推演会得到「首个差异在 r1/r2、爻光断言不可靠、椒丘断言可能空转」的执行结果——验收时锚不中,按 strategy-work §4「锚点没中 = 改动没生效或假设错,两者都要查」将触发一次本可避免的回查。
- 修正方向:复现局锚改为**分叉鲁棒的结构锚**——例:「首个买入差异的目标 ∈ 保护集成员」∧「全局长无保护集成员卖出事件(卖出遥测按成员 ∈ 保护集过滤后计数 = 0;椒丘在场的局逐名核对)」;爻光/饮月分支统一由 3.2 单帧 fixture 承载(现状爻光已入 3.2 fixture,删局级爻光断言即可)。landing 3.4 判据第一条同步改。

### F3【次要】「`transition_char` 键随④/策展退役删除」依据错位——键源是每线打工牌注册表字段,与④无代码耦合,删除损失可辨性且无取代申报

- 位置:`design.md:72`(§2.3 D7 段:「`transition_char` 与 `transition_component` 两键随④/策展退役**删除**」)、`landing.md:26`(「`transition_char` 键随④删除」)。
- 论断:`transition_char` 拒因键的判定源是 `Comp.transition_chars`(每线注册表字段,语义「早期打工牌(后期卖)」),不是 TRANSITION_PACK 策展名单,也不是④放行集——④退役不触碰该字段,「随④退役」不构成其删除理由;design 只为 `transition_component` 给了取代键(`protection_member_rejected`),对 `transition_char` 的可辨性损失零申报。
- 证据(直调):
  1. `kernel/cw_comps.py:115`:`transition_chars: list[str] = field(default_factory=list)  # 早期打工牌(后期卖)`——COMP_LIBRARY 每线字段,与 TRANSITION_PACK(知识层策展名单,`cw_line_facts.py:47`)分属两个注册表。
  2. `shop.py:395`:`trans = (set(getattr(comp, 'transition_chars', []) or []) ...)`——D7 的 trans 分支消费点;`shop.py:458` 的 `transition_component` 分支消费的才是 `line_identity_tier`(④身份源)。
  3. 删除后果:非保护打工件(如风堇——`cw_chars.py:129` 昼之半神/治疗/燃血,非四体系 bonds;艾丝妲等)在售未买帧的拒因从 `transition_char` 落入 `non_line`,而 `non_line` 桶同时是「全店 non_line 死锁」判读的观察面(11 §7 空候选帧判据),判读污染面真实存在。
- 修正方向:保留 `transition_char` 键(它不依赖④,零退役联动);或显式申报打工件可辨性损失并指认判读补偿面。二选一,禁维持现状的错位依据。

### F4【次要】prereg 报警观察面在 landing 3.4 完成判据枚举不全——design↔landing 失同步(同族前例复发形态)

- 位置:`design.md:120-121`(§2.6 prereg 观察集)↔ `landing.md:64`(3.4 判据)。
- 论断:design §2.6 prereg 的**存活报警线 = hp 低点带 / 位面 2 入口率**、**报警观察面 = 出口金带、凑息失败频率、买卡笔数分布**;landing 3.4 判据枚举为「点亮率/成型率/形态达标率/通关率/存活带/凑息失败频率」——缺**出口金带**与**买卡笔数分布**两项,「存活带」一词未明示覆盖**位面 2 入口率**。验收凭据按 landing 字面走会漏项,prereg 完整性在验收端打折。
- 证据:两处原文逐项对(见上);iteration-design 硬规则 4(修订后全量同步复查,design↔landing 判据同步)为规范出处;本迭代同族失同步已有前科(设计文档自身 §1 提及 m2_stockpile/四类排除面/帧态提取三处历史失同步)。
- 修正方向:landing 3.4 判据补全两项观察面并拆写「hp 低点带 / 位面 2 入口率」,或改为显式引用「design §2.6 prereg 观察集全集」。

### F5【次要】末阶段「非身份活消费逐点裁决(迁移或保留),不预设」无裁决判据——对直接 import 者保留选项结构性不存在,试读到该步停摆

- 位置:`design.md:86`(§2.4 末行)、`landing.md:69`(末阶段范围)。
- 论断:设计把 `cw_deploy_logic.py` fw_carry / `cw_recipe` / `cw_transition` 等非身份活消费的处置推迟到末阶段「grep 全清点逐点裁决(迁移或保留)」,但未给**裁决判据**(什么条件迁、迁到哪个源、什么算死码删除);且 `cw_recipe.py:24` 是模块级 `from ...knowledge.cw_line_facts import TRANSITION_PACK`(:41/:51/:60 以 carry/partial 档构 core_chars)、`cw_deploy_logic.py:374` fw_carry 按档位标签过滤——§2.4 同时裁定 TRANSITION_PACK **符号删除**,对这些直接 import 的活消费,「保留」选项结构性不存在,实际裁决空间只剩「迁数据源或随死码删除」。worker 按停手令(iteration-design 硬规则 2 卡点②)撞到无判据的逐点选择只能回设计——末阶段试读不可开工。
- 证据(直调):`cw_recipe.py:24/41/51/60`、`cw_deploy_logic.py:374`(`fw_carry = {n for n,(f,t) in TRANSITION_PACK.items() ...}`,部署面消费)、`cw_transition.py:33/48/54/196`(旧判据残留副本,cw_card_identity docstring 明令勿新增消费)。另注:fw_carry/cw_recipe 消费的是**档位标签**(carry/partial/drop),与 §1 根因 3「档位标签被买卖身份误用」同类——它们算不算「身份消费面」的分类边界,设计也未定。
- 修正方向:预设裁决判据并点名已知消费点归类,例如:「档位标签类消费 → 迁注册表现算/bond_members 派生新源;无消费死码 → 随符号删除;fw_carry(部署面)与 cw_recipe(配方面)点名定归属」;把「不预设」收缩为「清点发现表外消费点时按本判据归类」。

## 2. 实际攻击过的面清单(复核方式)

| # | 面 | 复核方式与结果 |
|---|---|---|
| 1 | §1 现状症状五项(5 张次拒买/r3 卖椒丘/对照局/复盘报告指针/seed) | 复盘报告实档逐行对:r1 三月七(行38)/r3 爻光+卖椒丘(行73-77)/r4 希儿席满(行93、行182)/r6·r8 饮月(行109/134/222-223)/5 张次口径与排除注(行182 对照≥6 张次的口径收紧已内联申报)✓;seed 20261012(报告 §0 元信息)✓ |
| 2 | 根因 1「身份域缺失」买面侧 | shop.py 直读:序1 缺口分支只吃 obligation_members(:1073)、m2_stockpile 要求同名已持 1(:1415)、④分支 committed 门(:1475)+ 10 人策展集(cw_line_facts TRANSITION_PACK carry/partial 逐一清点 = 10)✓ 原文证实 |
| 3 | 根因 1 卖面侧 | sell_candidates.sell_line_membership 两分支(锁定=view.members/未锁=候选 top3,:283-308)+ 装配 A 静态持有两集(sell_gate.identity_exclusions,:886)✓;椒丘=drop 档不在④放行集 → 现行可卖 ✓ 病灶机理成立 |
| 4 | 根因 2「定型语义混淆」 | cw_intention.committed_authority 权威序①②(:1623-1647)+ shop ④分支 `if not committed_from`(:1475)→ 配方对物化帧④恒关 ✓ 原文证实;12 §1.2「P1 板面恒过渡体系」引文对 ✓ |
| 5 | 根因 3「策展/现算双源」 | TRANSITION_PACK 13 人逐行清点(cw_line_facts:47-72,Early≥8% 注释)= 13 ✓;桑博不在包、持续伤害 flow 在注册表(cw_chars:105)→ 现算扩员主张成立 ✓ |
| 6 | §2.1 全部锚 | knowledge/cw_engine_facts.TRANSITION_TRAITS 存在且派生式同源声明 ✓;_bond_members 私有待公开化(:96)✓;is_seele_system_member 存在(kernel/cw_deploy_logic:159)✓;_p1_system_support/_seele_system_support 持有域与 ≥1.0 判定逐式核(bench∪deployed;希儿在场门;希儿双标签自计推导 0.5)✓;seele_system_formed 板面域区分(cw_deploy_logic:140-145)✓;GUARD_SYSTEM_TIERS 存在且设计声明不消费 ✓;锁定槽写点宿主 bridge.py:225-226/260-261(两入口同点调 refresh_line_if_needed)✓;清空点 flow.py:228(clear_p1_recipe 配方退场同点)✓;签名含持有名单→锁定槽随支持度重算的逻辑自洽 ✓ |
| 7 | §2.2 五处收窄面 | 逐一码点核对:m2_stockpile 循环含 _fund_or_none(:1414-1448)/M6 排除(:1712)/press_buy_deployable 排除(:1617)/垫件补位支排除(:1774)/ev_buy 入参(buy.py:81 k_members 排除)✓;M2b 宽集(:1453)✓;_dg_gap 宽集推导(:1553)✓;P60 宽集(:1076)✓;P91 带输入 qualified_member_costs(buy_members)(:1695)✓;P92 _p92_stockpile 宽集(:2132-2136)✓——设计申报的每一处「现行从宽集」都与代码一致 |
| 8 | §2.2 囤货臂机制 | 门序引文对码([11]/P46 豁免类「资产可逆」= 01 §3.1/11 §1 原文)✓;席满置换账候选经装配 A 自动排除保护件(3.3 后)✓;出口键/买因 hold 归类与 sell_gate 登记链(register_launch hold 资格断言)兼容 ✓;P1 锁定局「囤臂不聚焦」与序1 并集承载一致 ✓ |
| 9 | §2.3 五消费面表 + 身份段拆分 | sell_hold_exclusion_names 六处消费(含 identity_exclusions)全数清点,表 5 面 + §2.3 首条身份段 = 全覆盖无遗漏 ✓;line_members_view.locked/members 读口(session_scope:161-170/354-367)✓;P78-5′ 分支②语义(entry.py:721-752:分支①人口位/arm0 全量放行、分支②对象 ∈ holds 即拒)→ 保护件仅分支①可放行的推论与「两分支必要条件满足时可放行」表述相容 ✓ |
| 10 | §2.3 凑息观测键 | 写点锚 entry.py:1349-1395 节末凑息段 ✓;判定式三合取可在该段实现;反事实支枚举域与场景池(备战席∪场上无关角色)同域 ✓ |
| 11 | §2.4 退役表 | line_identity_tier 四消费点全清点(D7:458/②(b):1560/C1:1959/hold 硬闸 sell_gate:276)✓;C1 直判 = TIER_REGISTRY_CORE 即 `name in CORE_SINGLE_CARD_REGISTRY`(cw_card_identity:106-107)→ 行为零变化主张成立 ✓;CORE_SINGLE_CARD_REGISTRY = {希儿, 银狼LV.999}(cw_comps:507-514)与「希儿/银狼LV.999」表述 ✓;hold 硬闸分档表与现行 `_hold_qualification_ok`(name_ok=静态集∪hub;tier==transition→1★闸,else True)对读,「其余 gate=True 实际不可达」成立(hold 类买入闭集 = C1 核心+protection_hoard)✓;两计数键写点(shop.py:1087-1094/mandate.py:1251-1253)存在且宿主标注正确 ✓ |
| 12 | §2.5 行为变化申报 8 条 | 逐条与机制对推:P1 扩益(④门关→囤臂全域)✓;P2 短窗收窄(committed=False 短窗④现行活)✓;攒批资金链(entry._bench_liquid_gold:755-784 现读「非线内 1★」→ 保护件剔除修法锚存在)✓;银狼存量残角(装配 A 现行排除 core、liquid 未排)✓ 申报成立 |
| 13 | §2.6 验证设计 | 批跑/重放删除、A/B 挂起、hp/金类校准前不作判据(sim-testing 原文行对)✓;零漂移门豁免逻辑(门辖非行为批,11 §7.4 原文)✓;单帧六元组与「方向态构造值」申报对复盘报告完整性审计 ✓;r3 fixture 钉面核实:风堇非四体系成员(cw_chars:129)故无需钉,藿藿/青雀(仙舟)/佩拉(贝洛伯格)钉 owned 后爻光为唯一未持有保护成员,断言成立 ✓ |
| 14 | §2.6 保全清单十条 | 逐条对源:11 §6.5 门族(凑息发出帧/floor 零违例/富余滞留/<271/M6 子门)、02 §8 命题 A 八项+目标②组逐项点名核(零动作轮/花费率/SellBench/成型率/hp/bench 满拒买/升级投入金/CompTransaction 全在 02 §8 原文)、FM-1(11 §5)、零漂移(11 §7.4)、P86 实现批三锚(p86 单篇:3「错向囤积 2→0/带内烧费 5→0/枢纽动作发出>0」)、P96 载体勘误(test_cw_dead_pair_exit 源文件已不存在仅 .pyc 残留;实际载体 test_dead_stock_pair.py 存在且 kept_identity 断言在其 :438)——十条全部真实且有出处 ✓ |
| 15 | §2.7 关键取舍 | 五组取舍的放弃理由均引既有裁定/命题([22]④/[21]/[22]①、user_playstyle 原文行对;「修④门 vs 退役」的策展口径论证与根因 3 一致)✓ |
| 16 | 11_shop_decisions 全文(六序/§2/§3/§4.0/§4.1/§5/§6.5/§7.4) | 通读;六序承继行/②(b) 位次/Z1 装配单一源/P78-4 维持现状裁决与条件化后续门(两计数键定义)逐一对码 ✓;Z1 现行排除集与保护集的差集(扩员成员+贯穿件星期日类)落入 §2.5 申报覆盖 ✓ |
| 17 | 12/02/00/01 宪法对读 | 候选-锁定制/committed 权威序/P41② 不卖 fail-closed 条款/位面参数化不变量(设计无位面字面量新增;plane2_started 窗口谓词承继)✓ |
| 18 | math_proofs P41/P46/P47/P49/P78/P86/P92/P96 行 | 逐行直读;P46 豁免类/P41② 分类表/P78 通道集与兜底/P92 挂起与结构判据/P96 N=3 与载体指针陈旧(勘误申报正确)✓;proofs/p77、p86、p96 单篇与 validations/P31_VALIDATION.md 存在性 glob ✓ |
| 19 | 现役代码身份源/常量 | cw_card_identity 全文/cw_line_facts 全文/cw_engine_facts 全文/CORE_SINGLE_CARD_REGISTRY 构成/cw_chars 关键成员 bonds(椒丘=持续伤害、爻光=仙舟、佩拉=贝洛伯格、风堇=昼之半神非四体系)逐个直调 ✓ |
| 20 | 测试仓实际载体 | test_dead_stock_pair.py 直读(imports line_identity_tier/transition_release_names → 3.2 grep 域含 sr-od-test 的判据可执行)✓ |
| 21 | 流程规范 | iteration-design.md(四条硬规则/阶段七件——landing 五个阶段小节七件逐段核对齐 ✓/README 模板合规 ✓;硬规则 2→F5、硬规则 4→F4);strategy-work(§3 无开关合规 ✓/§4 指标纪律与可观测性声明 ✓/§6 prereg 硬门——保全清单十条覆盖既有线族,逐条性核实通过 ✓);sim-testing(A/B 挂起态、冒烟批载体 test_sim_smoke_batch.py 与 cw_sim_match_drive.py 存在性 ✓) |
| 22 | 核三·治本 | §1 三层根因全部代码证实(面 2-5);§2.7「修④门 vs 退役」= 拒症状修法取架构级收口 ✓;买面/卖面/④ 三处同根统一进单一保护集 = 跨件半问的架构级回应,非逐件补丁 ✓ |

## 3. 试读结论(逐阶段可开工性)

- **3.1 可开工**。写点/清空点宿主锚、成员枚举单一源、点亮判定复用面、四条单帧判据(含持有域分辨用例)全部齐备且锚点真实。注记(非阻断):点亮判定复用的 `_p1_system_support`/`_seele_system_support` 是 kernel 私有符号,strategies 侧跨模块 import 私有符号的形态设计未如 `bond_members` 一样声明公开化——可开工,风格债留给实现批按现状 import 即可。
- **3.2 修 F1 后可开工**。范围/文件面/判据覆盖 design §2.2 全部点(逐项核对无缺);r3/r6 单帧 fixture 的钉面经成员 bonds 直调核实充分(风堇非保护成员无需钉)。修 F1(判据排除项或时点移动)前,该阶段验收凭据不可达成。
- **3.3 可开工**。五消费面迁移表与 landing 拆分(3.2 hold 分支/3.3 其余四点)一致;身份段拆分保持 base 口径与 P78-5 减法②、P96 (b) 分支基准不变的申报与消费点实况吻合。
- **3.4 修 F2/F4 后可开工**。冒烟批与单局驱动器载体存在;保全清单十条真实;但第一条完成判据(复现局行为锚)按设计机制推演不可靠(首个差异帧错位 + 分叉后货架不可判 + 椒丘空转通过),判据枚举漏两项报警观察面。
- **末阶段 修 F5 后可开工**。正本更新清单八行,所列文档与节全部存在(含 proofs/validations 各篇、cw_intention:1419-1420 注释行);「非身份活消费逐点裁决」无判据为该阶段唯一停摆点。
- **阶段间过渡态注记(非发现)**:3.2 落地后、3.3 落地前,囤货臂已买入的成员尚无卖面保护(置换/凑息/筹资可卖)——分阶段交付的固有窗口,建议在 3.2 边界或 3.3 依赖行补一句申报,连续派工时无实际风险。
- **总判定**:design 主体(根因归层、保护集单一源、退役面清点、行为变化申报、保全清单)证据扎实、治本成立;5 项发现中 2 项重要(F1 判据可达性、F2 复现局锚)集中在 **landing 验收端**而非设计机制本身,修正均为判据文本级,不动方案。修完 F1-F5 可达定稿门槛。
