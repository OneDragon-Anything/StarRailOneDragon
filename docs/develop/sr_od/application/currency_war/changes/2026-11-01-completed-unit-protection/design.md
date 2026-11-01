# 完成品保护档(统一序列按张分档)迭代设计(总纲)

## 0. 元信息

- 迭代目标:修复统一让位序列的「2★ 完成品旋转门清算」缺陷——用户裁定采用档位结构方案(2026-11-01,会话拍板:①线内 need≥2 达标完成品插入原档 2 之前;②线内无星级要求已到 2★ 的保留张插入原档 3 之前;③同名星级要求以外多余副本落兜底档;④无星级要求成员凑第二张**不算**多余——底线两星口径,凑两星过程保护保留,2026-11-01 用户改定「2★ 还是挺容易达成的」)。
- 状态:定稿(五轮对抗收敛,见 attack.md;语义本体面 R5 起零发现)
- 文档清单:无详设(单文档方案,本篇即完整设计)
- 现象出处:局 g_20261101_125430 复盘候选 A-1 主候选(复盘报告与调研报告为 `.debug/temp/` 临时区过程件,不保证长期留存;结论已内联本篇 §1,现象证据锚 = 该局 journal,局 id 持久)

## 1. 问题与动机

- 现状症状:席满常态下(未锁定 P1,义务面宽集 ≈20-22 名 > 容量 13-14,每个商店决策帧必满),每笔买入的获取让位从统一序列末位取牺牲者;落档边界「升星达标后低星冗余副本落档 8」加上同名聚合判档,使**已达标 2★ 完成品与名下冗余 1★ 一同坠入兜底档**,与天生杂牌共用「概率高者先卖」键,被优先清算。该局 8 笔获取让位卖出取用档全为兜底档(计数器 `acquire_swap_sell_tier_8=8/8`),其中乱破 2★(need=2 追星目标件,买入当局即被卖)与翡翠 2★(need=1,晶矿喂食合成)为完成品本体。
- 根因归层:**语义层**——排序判定以「角色名聚合」为单位(一名一档),而让位的真实对象是「一张牌」;落档边界把「星级达标」翻译成了「已完成资产、最先牺牲」,只算了金币账(退金=重建价),未算重建时间账。实现与 11 号稿 §4.0、priority-model §2 逐条一致(调研 §2.3 核对表),非代码 bug,是判据设计缺陷。
- 解决到哪:统一序列改为**按张判档**——同名的牌分家:星级要求内的完成品(每名保留恰好一张最高星)升入保护档,要求以外的多余副本落兜底档。
- 明确不解决:①席满压力源(义务面宽集 vs 容量的结构性张力,囤货面收窄属压力侧,用户裁定另批立项);②兜底档内部定价的连续化(重建对价补键方案已评估、用户选择档位结构方案,不叠加上迭代);③万金油/羁绊角色到 2★ 掉兜底(既有落档边界,不在本迭代改动面)。

## 2. 方案(单文档完整设计)

### 2.1 系统级变化

`criteria/priority.py::sort_key` 八档判定表改十档。方向约定不变:键大者先卖;先命中先定档;档内合成序 = 档内键 → 退金损失 → 在手旗标 → 随机尾键(用户裁定三,现行约定不变)。核心语义变化:**排序单位从「角色名」变为「单张牌」**——谓词新增「本张是该名保留张」判定位,同一名下的不同副本可落不同档。

**保留张定义**(谓词共用,记 `is_kept_unit`):本张星级 == 名下最高星(`unit_star == max_star`)**且**该最高星在该名下仅此一张(`copies.count(max_star) == 1`)。等价群自愈语义:同星多张时全部不属保留张(全落兜底,等价牌群先卖哪张无差别);任何一次卖出后名下张数变化,剩余最高星张自动恢复保留身份——真实生效例 = 名下 [2,2](两星等价群):双双落兜底,卖一张后剩张 `count==1` 恢复档 4 保护。(1★×2 不是自愈的有效例:1★ 副本由档 7 保护,不消费保留张谓词,勿作测试写点。)

**保留张身份域**:仅 `HeldUnit`(在手牌)可为保留张;`ShopUnit`(候选牌)**恒非保留张**——获取让位评估的虚拟语境下,将获取的 X 不享受完成品保护,「末位 = X → 放弃买入」分支保持可达。这与现行防自我保护论证同构(X 不进档 1 保护的同一理由:`priority.py:320-326`,XT-1):保护的对象是**已入手的资产**,「这张候选值不值得买」仍由让位试探回答,不由排序身份预支。

### 2.2 十档判定表(键首分量重编 1..10)

| 档 | 谓词(按序命中即出) | 档内键(大者先卖) | 来源 |
|---|---|---|---|
| 1 | `name in deployed_names`(不变) | `(refund_loss, in_hand, tail)` | 现行档 1 |
| 2 | `is_member ∧ need≥2 ∧ max_star≥need ∧ is_kept_unit` | `(member_rank, -total_star, -unit_star, refund_loss, in_hand, tail)`(-unit_star **有判别力**:档 2 成员为不同名的保留张,跨名最高星可变〔2★/3★ 完成品并存〕,高星完成品后卖) | **新增**:need≥2 完成品 |
| 3 | `is_member ∧ need≥2 ∧ max_star<need` | `(member_rank, -total_star, -unit_star, refund_loss, in_hand, tail)`(原键不变) | 现行档 2 |
| 4 | `is_member ∧ need≤1 ∧ max_star≥2 ∧ is_kept_unit`(空 `copies` 由 `is_kept_unit` 自然排除〔`max_star=0 ≠ unit_star`〕,谓词无需显式 `copies` 项) | `(member_rank, -total_star, -unit_star, refund_loss, in_hand, tail)`(原档 5 键补 `-unit_star`:档 4 成员为不同名的保留张,跨名最高星可变〔2★/3★〕,高星完成品后卖——与档 2 同构) | **新增**:无星级要求完成品(两星及以上,含超额 3★) |
| 5 | `is_member ∧ not copies`(仅商店牌可命中) | `(member_rank, refund_loss, in_hand, tail)` | 现行档 3 |
| 6 | `stay_target 非空 ∧ not is_member ∧ cost==stay_target[2]` | `(-unit_star, refund_loss, in_hand, tail)` | 现行档 4 |
| 7 | `is_member ∧ copies ∧ need≤1 ∧ max_star<2` | `(member_rank, -total_star, refund_loss, in_hand, tail)`(原键不变) | 现行档 5(凑两星过程保护,语义与位置不变,仅编号位移) |
| 8 | `name in CROSS_LINE_KEEP_NAMES ∧ max_star<2` | `(-total_star, refund_loss, in_hand, tail)` | 现行档 6 |
| 9 | `_tier7_bond_member ∧ max_star<2` | `(-total_star, refund_loss, in_hand, tail)` | 现行档 7 |
| 10 | 兜底(含成员多余副本,见 2.3) | `(prob, -cost, -unit_star, refund_loss, in_hand, tail)` | 现行档 8,谓词零改动 |

依据:档位插入位置与口径 = 2026-11-01 用户裁定(§0);现行档谓词与键 = `priority.py:488-555` 现值;`member_rank` 读口不变(`PriorityContext.member_rank`,档 2/3/4/5/7 共用序数键——跨线取最高优先/配方成员统一低档的取值规则正本化后归 32 号稿)。

### 2.3 落档边界(修订后全量)

1. **need≥2 未达标名**:全部副本(含中间态多张)留档 3 升星主线——合成需要,不算多余(用户口径:多余判定只在达标后生效)。
2. **need≥2 已达标名**:保留张(最高星唯一张,含超额完成如 3★)档 2;其余副本(低星 1★、超额同星 2★)自然落档 10——档 2/3/4/6/7/8/9 谓词全不命中,无需新增显式谓词。**need 表装配前提**:本档在锁定帧成立的前提 = `need_star_by_member` 锁定帧装配补全(达标成员按知识卡照录,不再缺省 1;见 §2.5-1)。
3. **need≤1 名(底线两星口径)**:`max_star<2`(凑两星过程,含 1★×1 与 1★×2 中间态)全部副本留档 7 保护(现行档 5 行为不变);`max_star≥2` 后保留张档 4(2★ 本体与超额 3★ 均可,按实际最高星),名下多余副本(1★ 与超额同星 2★)落档 10(2026-11-01 用户裁定)。同星等价群(如名下 [2,2])双双非保留张 → 同落档 10,卖一张后剩张自愈恢复档 4(§2.1)。
4. **万金油/羁绊到 2★**:非成员身份者掉兜底(现行边界不变,档号 10);**兼为线内成员者**(身份可叠加,test_priority.py 花火三身份件自证)按 §2.3-2/3 以成员保留张身份落档 2/4 受保——行为变化,见 §2.5。
5. **虚拟获取语境**(获取让位评估):`simulate_acquired_units` 的连锁合成产物进入 `v_copies` 后,同名聚合重算,**存量件**按虚拟快照现算保留张身份——X 获取后 X 名已有的完成品张(如 1★ 喂食合成出的 2★)按档 2/4 受保;**X 自身恒非保留张**(§2.1 身份域)——1★ X 按其名下状态落既有保护档(need≥2 未达标名 → 档 3;凑两星名 → 档 7;无星级要求已两星名 → 档 10,与现行各档行为一致),2★ 直出 X 落档 10——「末位 = X → 放弃」对一切候选牌保持可达,现行 decline 行为不变。虚拟聚合读口 = `priority.py:338-344` v_copies,不变。

### 2.4 不变式(防回归锚)

- 兜底档谓词零改动:成员多余副本**不新增显式判定路径**,靠档 2/3/4/6/7/8/9 谓词不命中自然落兜底。
- 凑息豁免谓词 `interest_exempt_member`(`max_star < max(need, 2)` 豁免未达标在建件)**逻辑不动**——它辖的是「未达标在建件在凑息场景免卖」,与完成品保护正交;达标完成品在凑息场景经新档 2/4 自然殿后,行为自动改善。
- 统一序列单一源不变:全部卖出触发只消费 `sort_key`,禁第二排序实现(priority-model 接口契约 1)。
- 零新数值:十档全为序数,不引入任何新常数(零调参骨架合规,strategy-work §1)。

### 2.5 行为变化申报(全量)

1. need≥2 达标完成品(如乱破 2★):兜底档 → 档 2,未锁定帧与锁定帧一致。**伴随装配修正**:锁定帧 `need_star_by_member` 现装配自 `unfinished_star_targets`(只收未达标成员,达标成员缺省 1——`priority.py:233-234`/`levelup.py:198-201`),缺省 1 会使本档谓词 `need≥2` 在锁定帧永不命中、完成品错落档 4;本迭代在 priority 装配支内补全——锁定帧对锁定线成员按知识卡 `need_star` 全量照录(达标成员不缺省),`levelup.unfinished_star_targets` 本体不动(其原始语义「未完成目标」与其余消费位不受影响)。
2. need≤1 两星完成品(如翡翠 2★):兜底档 → 档 4。同上。
3. need≤1 凑两星过程(未到 2★ 的全部副本):**行为不变**——底线两星口径(2026-11-01 用户改定),原档 5 保护域原样保留(档号 5→7)。
4. need≥2 达标名下冗余 1★:原本即落兜底,行为不变(档号 8→10)。
5. need≤1 两星后名下多余 1★:原本即落兜底,行为不变(档号 8→10)。
6. **候选牌获取决策:行为不变(显式申报)**——X 恒非保留张(§2.1 身份域),2★ 直出候选在席满帧仍可「末位 = X → 放弃」decline,与现行一致;若不设此域,2★ 直出 X 将以保留张身份自入档 2/4,获取决策从「可能 decline」翻转为「必买」,并开启「卖另一成员完成品凑 X」的牺牲链——禁。
7. 观测键域:`<take>_tier_<1..8>` → `<take>_tier_<1..10>`(`shop.py:1083` 动态格式化,零代码分支改动)。**跨批对照申报**:历史批 `tier_5`/`tier_8` 与新数据同名不同义,跨日对照须按批所属代码版本分域判读。
8. `supply.py` 补给选角色消费 `sort_key`(:202-211 排序定位):候选角色含完成品时胜出序变化(成员完成品更易保留)——方向与保护语义一致,行为变化如实申报。
9. 部署搜索 `deploy_search._unit_sort_key` 为独立键实现,不受影响(grep 确认无 sort_key 消费)。
10. 万金油/羁绊身份与线内成员身份叠加的角色(如花火):其 2★ 保留张现行落兜底,本迭代起按成员身份落档 2/4 受保——§2.3-4 语义统一的必然后果,如实申报;非成员身份的万金油/羁绊 2★ 掉兜底不变。

### 2.6 消费面清单(实现+测试+文档)

**代码**:
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/priority.py`:sort_key 十档重排(§2.2);保留张谓词(§2.1,含 ShopUnit 排除支);锁定帧 `need_star_by_member` 装配补全(§2.5-1,装配支内改,`levelup.unfinished_star_targets` 本体不动);`interest_exempt_member`、模块头/docstring/**模块级常量 `#:` 注释**(如 TIER7_BOND_NAMES 行)/运行时日志文案的档号表述跟改(逻辑不动,仅表述);docstring 与注释内 priority-model §X 引用随 3.1 重写面/3.3 表述面逐一跟改为 32 号稿 §X 或中性表述;模块头规格锚改指 32 号稿归正本阶段。
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell_candidates.py`:`:128`/`:443` 附近「达标线内件掉档 8 已完成资产」注释跟改(语义:完成品居档 2/4,冗余副本落兜底档);`:35`「概率表保留为档 8 分档」→「兜底档分档」;`:240` 观测载荷注释档域 1..8 → 1..10;`:10-11` **双锚分账**(`priority-model §5` → 32 号稿;`acquisition-and-sell §3` → 11 号稿 §4.0)、`:246`/`:359` → 32 号稿;锚改指统一归正本阶段,细则 = landing 正本清单。
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`:头注 `<take>_tier_<1..8>` → `<1..10>`(:34/:41);`:825`/`:856`「与优先级档 2/3/5 名单同源」→ 新成员档族口径(档 2/3/4/5/7);`:859`(「受档 6 保护」→ 新档号);`:1115`「统一序八档判定」→ 十档。
- `src/sr_od/application/currency_war/telemetry/schema.py`:键表节注释 `<1..8>` → `<1..10>`(:196)。
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/statefn/predicates.py`:`:9`(模块头)与 `:83` 档号表述跟改。
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/supply.py`:`:164`「同名凑星价值由档 2 成员星目标聚合承载」→「档 3」(旧档 2 = need≥2 未达标升星主线,新编号档 3)。
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/protection.py`:`:9`/:41/:47-48(万金油「档 6 数据源/到两星掉档 8」旧口径跟改;CROSS_LINE_KEEP_NAMES docstring 在役职责域同步)。
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell.py`:`:103`/:237 档号表述跟改(3.3);`:185`/:297(行内「档 7」表述 →「档 9」+ priority-model § 锚改指 32 号稿,锚归正本阶段、同行档号表述随锚一并跟改)。
- `src/sr_od/application/currency_war/kernel/cw_comps.py`:`:247`/`:315`「档 2/3/5 档内①键」知识卡单一源 docstring 跟改(新档族档 2/3/4/5/7);`:248`「规格 = changes/…priority-model.md §3」规格锚正本阶段改指 32 号稿——priority-model 退役后该引用死亡。
- `src/sr_od/application/currency_war/data/cw_chars.py`:`:44`(「该维度由统一序列档 7 判定承载」→ 档 9)。
- `src/sr_od/application/currency_war/kernel/cw_intention.py`:`:1294`「档 2/3/5 承载买入与保留」跟改。

**测试**(改测试 = 重推语义,docstring 引本篇 §2.2/§2.3 为设计出处):
- `sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/test_priority.py`:逐档断言全面重写(十档表);落档边界新增例(达标 2★ 进档 2〔**未锁与锁定两帧各断言一次**,§2.5-1〕/ need≤1 2★ 进档 4 / need≤1 凑两星中间态留档 7 / need≤1 两星后多余 1★ 落兜底 / need≥2 达标名 [2,1] → 1★ 落兜底 / need≥2 两星等价群 [2,2] 双双落兜底卖一张自愈恢复档 2 / need≤1 两星等价群 [2,2] 自愈恢复档 4 / 2★ 直出候选 X 落兜底非档 2)。
- `sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/test_sell_candidates.py`:档序断言跟改(「档 8→档 7」类按新档号)。
- `sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/shop/test_acquire_yield.py`:垫件/X 末位断言跟改;**新增**:2★ 直出候选帧「末位 = X → 放弃」可达断言(§2.5-6)。
- `sr-od-test/test/sr_od/application/currency_war/operations/cw_screen/test_prep_pipeline.py`:`self_rescue_sell_tier_8` → `tier_10`(该场景取用杂件落兜底)。
- `sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/supply/test_decide.py`、`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_supply.py`:档号断言跟改;**新增**:成员 2★ 完成品候选的胜出序用例(§2.5-8 行为申报的回归锁)。
- `sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/test_priority.py` 补:花火型三身份叠加件 2★ 保留张落档 2/4 用例(§2.5-10 行为申报的回归锁;现 fixture 断言的非成员支 2★→兜底仍保留作对照)。
- `sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_no_target_three_arms.py`:`:153`/:192 docstring 档号引用跟改(轻)。
- `sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/test_protection.py`:`:130` 档号引用跟改。
- `sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/shop/test_shop_session_loop.py`:`:336` 档号引用跟改。
- `sr-od-test/test/sr_od/application/currency_war/kernel/test_cw_comps.py`:`:183` 档号引用跟改。

**正本文档**(落点见 landing 正本更新清单):排序规格**正本化**——现行规格单一源住在上一迭代目录(`changes/2026-10-29-unified-priority/details/priority-model.md`,被 `priority.py:3` 等多处长引,违反「代码与正本禁引 changes/」铁律),本迭代借规格变更之机把十档判定规格升正本:`strategy-docs/` 新篇(编号顺延,`32_unified_sell_priority.md`),**范围 = design §2.1-§2.3 as-built 化 + priority-model 现行有效内容收编:§1(PriorityContext 输入契约/确定性约束)、§2 幸存语义(成员名单两态/配方支判窗/need_star 两态取值按 §2.5-1 新口径/无表项缺省规则/聚合口径——凡未被本篇 §2.2 取代者照录)、§3 非表行口径(兜底档概率分档口径注〔按概率值非费用号/同值并入/低费稳定序/refresh_prob 缺键返 0/基线概率表投资轮岗不感知〕与序数键取值规则——凡未被本篇 §2.2 表列承载者照录)、§4(随机流实例)、§5(卖出取用形态与池子)**——priority-model 退役后其全部节的规格无家可归,只迁判定表会留死亡引用。`priority.py:3`、`cw_comps.py:248`、`sell_candidates.py:10-11`、`sell.py:185/:297` 锚改指 32 号稿;`priority-model.md` 与姊妹迭代 `acquisition-and-sell.md` 规格锚随 changes 寿命退役(32 号稿收编后成自足正本)。**存量债登记(非本批处置)**:仓库内其余 changes/ 引用(grep 清单为准;已知 `priority.py` 内 5+ 处〔acquisition-and-sell/roster-plane1-union/总纲 design〕、`mandate.py:1224/:1291/:1317`、`supply.py:44/:158` 等)与本迭代正本化同类但属既有存量,不在本批文件面内,后续批另行清定。**XT-2 清定归属本批**(姊妹迭代 supply-unified 稿的同项以本批 32 号稿为准,交接声明见 landing 正本清单)。

### 2.7 验证法

1. **单帧测试**(§2.6 测试清单;回归资产,先于 sim):十档逐档断言 + 旋转门同型局面(达标 2★ 在席满让位帧不做 victim,替代 victim = 兜底杂件或放弃买入)。
2. **L1 快速集**:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 全量一次通过。
3. **sim 单局行为抽查**(非采纳判据,实现验证):同 seed 局复跑,`acquire_swap_sell_tier_*` 分布中完成品取用应消失;观测口径按 §2.5-7 声明(键域变更,禁与旧批直接同名对比)。A/B 批工具挂起期间,跨局统计验证挂起;本改动为结构档位方案(用户拍板),A/B 不构成采纳裁决(strategy-work §3)。
4. 实机验收:按当期目标行判据,连续多局;hp/胜负维不进判读(sim-testing 边界)。
5. **受影响验收线保全清单**(strategy-work §6 prereg 硬门):本批为判据/策略层改动,受让位序行为通道影响的已登记验收线逐线盘点——①位面 1 出口金(经济链经让位买卖;判据线值不动〔零新数值〕,预期方向正向:完成品保留减少重买支出);②过渡凑齐率/2★ 到手率(直接受益面);③终局金/终局阵容完成率(下游,预期正向);④存活/hp(sim 失真维不进判读,实机复核)。各线判据口径与线值本批零改动,变化仅在行为通道;落地前对照当期迭代 criteria 行与 proofs 判据节做一次盘点确认无遗漏线,量化复核在 A/B 工具恢复后补,实机按当期目标行连续多局验收。

### 2.8 关键取舍

- **档位结构方案(本篇)vs 卖出重建对价补键(调研选项三)**:对价方案连续量调键、冲突面小,但把「完成品值多少」隐入连续键,判读不可解释;用户裁定取档位结构——完成品保护是明确的策略立场(显式、可断言、可单帧固化),与「统一序列价值序由档位结构承载」的现行设计哲学同构(priority-model 接口契约)。
- **保留张限「每名一张」而非「每名达标星级全部副本」**:同星多张等价(概率/退金全同),名额制在逐牌纯函数下不可实现;等价群自愈语义(§2.1)以零状态达成等效——任一张被卖后剩余张自动获保,等效于「卖到只剩一张为止」。
- **凑两星过程保护保留(底线两星口径)vs 收紧为「每名一张」**:收紧方案的省位收益以放弃无星级要求成员的 2★ 强化路线为代价;用户改定保留凑两星保护(2026-11-01:「2★ 还是挺容易达成的」)——完成度路线优先于席位节省,与档 5 既有「阵容强度」语义一致。
- **不设身份豁免、不动兜底谓词**:身份豁免已被 2026-10-29 统一优先级迭代废除(统一序列单一源),本次回归档位结构承载保护,不重引入豁免谓词。
