# 武装箱选卡价值升级 设计对抗报告

> 无前提对抗审(干净上下文;对象 = design.md / landing.md / README.md,历史 attack.md 按任务纪律未读、未参考)。
> 三核并重:核一无前提攻击(自行找面)/核二规范遵循(iteration-design 硬规则三条、strategy-work 硬门、阶段可验收性)/核三治本核验(根源两问、跨件半问)。

## 0. 判据源与实跑清单(全部直调原文/原码,禁转述)

- 宪法/流程:`strategy-docs/00_framework.md`、`01_math_framework.md`(§3.6 装备行、§6 三形态)、`.dsh/skills/sr-od-currency-war-dev/references/strategy-work.md`(§1/§3/§4/§5/§6)、`docs/develop/harness/iteration-design.md`(§1.1/§5/§7)。
- 源迭代:`2026-09-12-supply-selection/design.md` + `details/supply-value-spec.md` + `landing.md` + `README.md`(裁定汇编 1-8)。
- 代码真值:`strategies/impl/flow.py`(decide_box_card:654-702、decide_invest:483-529、_refresh_direction_views:392-434、pick 族 target_comp 消费位 :541/:552/:567/:581/:602/:632)、`kernel/cw_prep_expect.py`(MATERIAL_VALUE_TABLE:32-35、material_value:38-40、模块 docstring:1-9)、`kernel/cw_events.py`(_EQUIP_VALUE:712-750、_equip_value:777-779、decide_supply:783-814)、`prep_actions.py`(:211-216 在册裁定注、:411/:577 观察写端、:986-1031 _open_box、:1062-1099 _pick_box_card、:1101-1144 _default_box_card)、`kernel/cw_strategy_session.py:165-167`、`kernel/cw_exec_state.py`(exec_state_of:71、_owned_add:278-282、apply_op_effect:285-373)、`operations/cw_screen/_overlay_confirm.py:35-70`、`operations/cw_op/cw_op_equip_all.py:134-163(register_equip_worn)`、`strategies/impl/pick_bias.py` 全文、`strategies/impl/cw_strategy.py:205-208`、`mandate_v1/bridge.py:72`(MandateV1Strategy 未覆写 decide_box_card,覆写面 = decide_prep_screen/decide_encounter/decide_shop_screen)、`mandate_v1/mandate.py:1640-1658`、`mandate_v1/entry.py:461-467/:665`、`kernel/cw_bench_equips.py:55-95`(穿着自动合成实锤)。
- 注册表/玩法/证明:`data/cw_equipment_data.py` 全量直读 + **实跑**;`kernel/cw_comps.py:107` + **实跑**(COMP_LIBRARY 20 套);`docs/game/currency_war/research/equipment_mechanics.md`(§1.1/§4)、`board_structure.md:59-62`;`proofs/math_proofs.md` P42 行、`01_math_framework.md` §3.6;`docs/game/currency_war/data/equipment.md` 经 git 确认已删除(be62ed454「data/ 冗余清除」)——设计「过期局部文档」定性成立且实为已删文档。
- 测试/sim:`test_cw_material_score.py`、`test_cw_screens_ops.py:41-108`、`test_cw_box_pick_arm.py`、`test_cw_box_open_pick_merged.py`、`test_cw_obs_arch_prep_writeflow.py:360-388`;`sr-od-test/fixtures/cw_fake_game/fake_match.py:740-794`、`rules.py:176-186`、`src/.../sim/` 全域 grep(OpenBox/PickBoxCard 零命中)。
- 注册表实跑结果(本报告数值主张全部出自本次实跑):8 简易件各 **10 配方引用/11 槽**;红钻/蓝钻各 **12 槽**(11 配方);进阶类作材料 **0 引用**;自对配方恰 **10 条**(简易 8 + 红×2/蓝×2→宝钻),与 design.md §2.3 清单逐条一致;现行 COMP_LIBRARY(20 套)中 **5 套存在重复 key_equips**(昼神阿雅 2×反重力皮靴、狼尊欢愉 2×反重力皮靴、命运圣杯红A 2×动能激发剑、追击飞霄 2×火力风暴潮、专家桑博DOT 2×火力风暴潮);无任何套存在「key 件互为另一 key 材料」叠加实例;反甲白厄 key_equips = [以牙还牙甲×2、高周波电锯、以牙还牙甲·特权、热血沸腾拳],`get_comp` 解析正常。

## 1. 发现清单

### F1【阻断】equip_tier/pick_equipment 签名 key_equips frozenset 与需求件数 count 语义互斥,重复 key 阵容(5/20 套)的提权守卫按签名实现即失效

- 位置:design.md §2.1(两签名 `key_equips: frozenset[str] = frozenset()`)vs §2.2(「**需求件数(K)** = `key_equips.count(K)`(key_equips 为可含重复的列表…如阿雅需 2 反重力皮靴,cw_comps.py:107)」)vs §2.3(near_redeem 的「∃ key_equip K(需求未满足)」同用该入参)。
- 证据(直调+实跑):frozenset 既无 `.count()` 且构造即去重;设计自引的注册表注(cw_comps.py:107)与实跑证实 5/20 套重复 key_equips——设计自己用于旧锁重锚示例的反甲白厄就是 2×以牙还牙甲。按签名传 frozenset(comp.key_equips):阿雅持 1(已穿)时 need=1、total=1 → 1<1 假 → 第二只皮靴落 tier 0;设计语义 need=2 → tier 3。若实现者按字面调 `.count()` 则每次已锁态箱决策 AttributeError → `_default_box_card` fail-closed 上抛 → 箱选卡整链不可用。
- 发作场景:实现者照 §2.1 签名落码 → 5 套在册阵容的 key 直击/近兑现提权在「已持部分」帧全部丢失;或按 §2.2 语义落码 → 与声名签名不符,验收无从判对错。
- 修正方向:两签名改 `Sequence[str]`(或 `list[str]`);机器内部 ∈ 判定可自建 set,需求件数只在原序列上 count;B 组锁补一条重复需求帧(昼神阿雅:持 1 穿 1,offer 反重力皮靴 → tier 3)钉住 count 语义。

### F2【重要】landing 3.1「照执源迭代 P-1 全量范围」把 wear 行为变化(S13 stash 移除)带入本批,其验收判据却「归源迭代判据不在此重复断言」——行为变化上线而无归属验收批

- 位置:landing.md §3.1(范围「执行 …landing.md §3.1(P-1)全量范围…六消费位重接」;文件面含 `cw_screen_equip_pick.py`、`test_cw_supply_pick.py`;完成判据「wear S13 归源迭代判据不在此重复断言」)。
- 证据(直调):源迭代 landing §3.1 明文 P-1 含「wear 一处行为变化 = 未锁态 stash_comp +100 移除…锁 S13」;源迭代 README 进度 0/5(未落地)。本批 3.1 若先落地即实施 S13 行为变化,但其判据被显式排除在本批完成判据外;源迭代后续若因范围被本批吸收而不再单跑 P-1,S13 行为锁永久无执行批。且本设计 §3 末行拒绝 sim 侧混入的理由恰是「文件面与验收面双膨胀」,3.1 现状对 wear 面构成同型张力。
- 发作场景:worker 完成 3.1 全部声明判据(全绿)交付 → stash 契合行为已变但任何一方判据都未断言 S13;后续源迭代 P-1 若再跑,S13 锁才被补建——期间实机行为变化无回归资产。
- 修正方向:二选一并显式——①3.1 完成判据纳入 S13(本批实施即本批断言);②3.1 范围收窄为「wear 仅符号重接、行为等价」,stash 移除留源迭代批。

### F3【重要】landing 3.1 对源 P-1 第二件做了未申报的实质修订:material_value 保持手表本体而非「改薄委托」——「全量范围照执」与「② 保持手表原值」在源 spec 文本下直接冲突

- 位置:landing.md §3.1(「执行 …P-1 全量范围…② 保持消费 `cw_prep_expect.material_value` 手表原值**不换源**…box 行为基线 = 现行 flow 实现 argmax 逐点一致」;V2 修订已申报但仅辖锁面)vs 源迭代 `details/supply-value-spec.md` §1.3 件 2(「`cw_prep_expect.material_value` 改薄委托」)。
- 证据(直调+实跑):源 P-1 的「改薄委托」= material_value 转发注册表引用计数;实跑注册表计数 8 简易件全为 10——薄委托落地后 box ② 的分值即从手表(7/6/6/5/5/5/4/3)变为(10×8),档内序改取先、未锁态简易件分值放大,「argmax 逐点一致」基线不可能成立。3.1 要保住基线就必须**不做**薄委托(material_value 在 3.1 阶段保留手表本体),这是对源 spec 件 2 的实质修订,但 landing 只申报了 V2 锁修订、未申报本处。
- 发作场景:worker 按「全量范围照执」读源 spec 件 2 执行薄委托 → box ② 值变 → 3.1 自己的「box 消费位基准帧逐点一致」判据红;或 worker 按本迭代 ② 执行 → 与源 spec 冲突无处对账。两单一源打架,违反 iteration-design 写作硬规则 2(实现者无需再设计)。
- 修正方向:3.1 范围显式补一句申报「material_value 保持手表本体、不改薄委托(薄委托语义随 3.2 退役一并消灭)」;并在源 spec §1.3 件 2 与 §5 V2 行加修订指针(指向本迭代 landing 3.1 版),消两迭代单一源分叉。

### F4【重要】§2.6 行 4b「等价」标签吞掉「mv 相等 ∧ base 不等」子情形——该子情形是未申报的行为变化,照表建锁会漏

- 位置:design.md §2.6 行 4b(「档内两件 material_value 相等 | 取先 | base 相等 → 取先 | 等价」)。
- 证据(直调注册表):现行档内并列判据 = material_value,新制 = base;两判据的并列域不同。实构反例:锁定电光履(key),其配方 = (光能电池, 轮滑鞋),offer 序 [光能电池, 轮滑鞋]——mv 相等(6=6)→ 现行取先 = 光能电池;base 不等(3 vs 4)→ 新制取轮滑鞋。该帧既非 4a(mv 不等)也非 4b 字面(4b 只断言 base 亦相等时取先),行为变化真实存在但全表无行申报、无锁辖。
- 发作场景:B 组按 4b 建「等价回归帧」时若选中的恰是 mv 并列而 base 不并列的牌 → 锁红误判改动错;若避开 → 未申报变化无锁,回归裸奔。
- 修正方向:行 4b 拆两子行——(mv 等 ∧ base 等)= 等价取先;(mv 等 ∧ base 不等)= **变化**(与 4a 同源,档内序换 base),后者补变化锚点锁(可用上述电光履帧,牌名注册表实名)。

### F5【重要】§2.6 行 2「offer 全表外件」锁对象含混:相对哪张表未指明,两种读法一为等价误标变化、一为变化但帧述自相矛盾

- 位置:design.md §2.6 行 2(「未锁态,offer 全表外件 | 恒第 1 张 | base 最大者 | **变化**」;§1.1 gap 1 同源表述)。
- 证据(直调):读法 A(「表外」= 通用值表 `_EQUIP_VALUE` 外):四件全 base 0 → 新制并列取先 = 恒第 1 张 = 现行,该行实为**等价**;读法 B(「表外」= material_value 表外):则火力风暴潮(mv 0、base 6)亦属「mv 表外」,行内变化真实——但帧述「全表外件」与变化子情形(必须含值表内件)矛盾,照字面选牌建锁必然钉在等价帧上。两读法都不能按字面落锁。
- 发作场景:B 组 worker 对行 2 建变化锚点锁 → 要么锁一个两制同结果的伪变化帧(恒绿、无断言力),要么自行猜读法(绕开停手令前置的「无需再设计」)。
- 修正方向:行 2 收窄为「未锁态,offer 含 `_EQUIP_VALUE` 表内件 ∧ 全部 mv 表外」(例:现列 [垃圾袋, 火力风暴潮] → 改后风暴潮),并把「四件全值表外 → 两制同取第 1 张」如实移入等价面或 §1.4 不解决清单。

### F6【次要】§2.2 漂移面「直击 [100,107]」忽略 +30/+mv 叠加分支——机制陈述不真,分离结论侥幸不受影响

- 位置:design.md §2.2(「现行加法三档值域 = 直击 [100,107]、材料 [30,37]、通用 [0,7],三段分离」)。
- 证据(直调+实跑):flow.py:694-699 三个加分项为独立 if(无 elif)——key 件同时是另一 key 件材料时得 100+30+mv,结构上限 137。现行 20 套 comp 实跑无「key 互为材料」实例,值域按当前数据凑巧成立;注册表变化即失真。「值对标签错」类精确性问题(五犯实证错误类),分离结论本身不受影响。
- 修正方向:改述为「直击 [100,107](叠加分支结构上存在、现行库无实例,上限 137)」或加「以现行 COMP_LIBRARY 为域」限定。

### F7【次要】pick_bias.py 不在 3.2 文件面:box 两常数随薄壳化成死值、:32 注释引用将退役的 material_value 表——「全仓零引用」判据按字面 grep 不可达

- 位置:landing.md §3.2(文件面缺 `strategies/impl/pick_bias.py`;完成判据「material_value 迁移完成后全仓零引用(grep 证明)」)。
- 证据(直调):pick_bias.py:29-31 `box_key_equip/box_key_material` 消费位仅 flow.py decide_box_card(3.2 薄壳化后归零)、:32 注释「材料通用性 _material_value 表维持其模块单一源…不变」;3.2 退役 material_value 后该注释指向已删符号,grep material_value 仍命中。
- 发作场景:worker 或按字面扩删 pick_bias.py(越文件面),或留死常数+过期注释然后「零引用」判据造假/被解读收窄。
- 修正方向:3.2 文件面补 pick_bias.py(box 两常数与注释随薄壳化退役;tome/wish 常数保留),或判据改「生产代码零 import、注释残留点名单」。

### F8【次要】README 进度「落地:阶段 0/2 done」与 landing 阶段数(3.1/3.2/末阶段 = 3)不符;与源迭代 README 同口径(0/5,含末阶段)相互矛盾

- 位置:README.md 进度节;iteration-design §4 模板「<阶段 x/y done>」未定义末阶段是否计数。
- 证据:本迭代 landing 实有三阶段;源迭代 5 阶段计为 0/5(含末阶段)。同仓同模板两种口径,编排者照 README 立账易漏末阶段或重记。
- 修正方向:改「0/3」对齐源迭代口径(含末阶段)。

### F9【次要】§2.5 码点错位:「_pick_box_card 一体内完成(prep_actions.py:986-1031)」——该区间实为 _open_box,_pick_box_card 在 :1062-1099

- 位置:design.md §2.5 防御注记。
- 证据(直调)::986-1031 = `_open_box`(含同动作选卡闭环,:1014 直调 _pick_box_card);`_pick_box_card` 本体 :1062-1099。结构主张(决策与点卡同函数、无发射/执行分裂)两函数都成立,但符号名与区间错位属码点精度问题(五犯实证错误类)。
- 修正方向:区间改「:986-1031(_open_box 闭环)/:1062-1099(_pick_box_card 本体)」双锚。

### F10【次要】箱面钻/宝钻 0 分定价未入 §1.4 明确不解决清单——与裁定 1 的价值序存在潜在倒挂,现行打分同病(无回归),但边界应显式声明

- 位置:design.md §1.4(不解决清单);§2.2(base 表外 0)。
- 证据(直调):注册表红钻/蓝钻/财富宝钻 ∈ EQUIPMENTS(特殊类),`_EQUIP_VALUE`/`MATERIAL_VALUE_TABLE` 均无值 → 新旧两制皆 0 分,未锁态排全部有值件之后(幸运星 3 > 宝钻 0);源迭代裁定 1 对钻的定谳是「单件价值高(宝钻 = 团队规模上限+1)」。board_structure.md:61 只证箱 =「4 选 1 装备」,箱池是否含特殊类无在册证据——无证据即无回归实锤,但设计的「输出先验」主张适用域(值表 ~35/158 件覆盖面)未声明,§1.4 亦未把「箱面钻/宝钻定价」列入不解决。
- 修正方向:§1.4 补一行「箱面特殊类(钻/宝钻)/工具/命运/骇客等值表外件的定价:维持表外 0,不解决(登记箱池构成实采钩子后重裁)」,并在 §2.2 注明输出先验的覆盖边界。

## 2. 攻过未破角度清单(实际攻击过的面)

1. **现行打分还原逐点核对**:§1.1 摘要四要素(key +100/材料 +30/mv 0-7/effect_pick_bias 恒 0)与 flow.py:654-702、pick_bias.py:30-31(100.0/30.0)、cw_prep_expect.py:32-35(花7/鞋6/电池6/钻头5/刀5/装甲5/枪4/星3)逐字一致;`effect_pick_bias` bias 恒 0.0 实证(pick_bias.py:49-61,bias 无任何写点);argmax 严格大于取先(:700-701);输入序 = `_pick_box_card` OCR 按 x 排序(:1078)「从左到右取先」成立;无信息 fallback idx=0(:663-664 与 best_s 初值 -1)。「四张全表外恒第 1 张」成立。
2. **库存账写端全量核对**:观察采集全量重写两写端(prep_actions.py:411 M7 分支、:577 front_only 分支,全量 hits 含工具);开箱选卡 +(cw_exec_state.py:338-345 经 apply_op_effect,_open_box:1029 补推进);确认到账 +(_overlay_confirm.py:61-63 → ConfirmBox/ConfirmSupply/ConfirmTome);穿戴 −/+部署位(register_equip_worn:152-155/:158-161);卖场上装备返还 +(cw_exec_state.py:335-337);对账网 compare_equip_expect 存在(cw_prep_expect.py:614-638)。§1.2 清单与代码逐条对上。
3. **在册裁定冲突分析**:prep_actions.py:211-216 原文辖「发射位无评估输入…现读严格不劣…免去发射后执行前漂移」——设计 §2.5 的辨析(开箱决策与点卡同函数闭环、entry.py:465 只发空 PickBoxCard、overlay 帧装备区读取无在册通道【候实证如实标注】)成立,本消费不与裁定冲突。
4. **近兑现定义数学一致性**:交叉对(cnt(X)==0 ∧ 另侧≥1)与自对(cnt==1;0 不升、≥2 已可合、≥3 增量排除)对「选前 0 对 ∧ 选后 ≥1 对」逐域枚举成立;min/整除式与配方 (A,B)/(A,A) 结构一致;两账分工(对数=备用、需求门=总持有)与栏内合成输入面语义吻合;穿戴自动合成机制(wear_synth,cw_bench_equips.py:55-95 实机实锤)提供「选卡解锁 → 经穿戴链到 K」的生产可达路径,推导 2 的「立即交付」方向有机制支撑。
5. **档序推导**:推导 1 同 K 共现帧的结局集包含论证(K+伙伴材料 ⊇ K)成立;P42 ①③ 引文与 math_proofs.md P42 行、01_math_framework §3.6 逐字一致(「近兑现张最贵,绝不喂」),且设计如实声明其为保留面结论、本档序为获取面同构应用、证据强度取最弱一环——引用纪律合规。P42 索引状态「R4 无阻断,对抗收口」可消费(阅读门公理 4)。
6. **违宪扫描**:序数档 3/2/1/0 为纯位次载体(零基数解读);base 表 = `_EQUIP_VALUE` 逐值平移(源迭代定稿裁定「值不再重推,重拍 = 违禁拍值」承袭,ADR-0298/0130/0555 审计链);近兑现/需求守卫零新参数;无开关(§3 直接落码口径);sim 可见性申报(§2.7)与 strategy-work §4 申报义务吻合。
7. **§2.7 三项 sim 定谳复核**:①`FakeMatch._pick_box_card` 无策略调用、card_idx None 恒取第 1(fake_match.py:775);②假箱选项 = 商店角色池名(rules.py:176-186)落 BenchChar 入备战(fake_match.py:786-790),与实机箱「4 选 1 装备」(board_structure.md:61 实机采证)不同物;③`sim/` 全域 grep OpenBox/PickBoxCard 零命中。「结构性不可见、A/B 不可作本批判据」定谳成立。
8. **注册表统计全部实跑**:8×(10 配方/11 槽)、红蓝钻 12 槽、进阶 0 引用、自对 10 条逐条清单一致、V2 修订的「手表梯度与注册表真相互斥」成立(实跑 8 件计数同为 10,手表 7/6/6/5/5/5/4/3 无任何出处对应;源文档 equipment.md 经 git 确认已删除)。
9. **唯一件佐证转述如实**:equipment_mechanics.md §4 原文分级(【代码实锤】6 条 3 组电光履/蓄能帆/绝对热量、语义【口述·印象级】未实测、规划含义【推断】)与设计 §2.2「辅助佐证不作主依据」的引用分级一致;3 组标记注册表直读核对无遗。
10. **旧锁处置可执行性实核**:test_cw_material_score.py 两断言在 locked_comp 重锚后语义保持(反甲白厄 key 含以牙还牙甲,幸运星 tier1 < tier3、材料胜垃圾均复现);test_cw_screens_ops.py 两锁实况(手表值锁 :77-81、回落锁 :99-108)与处置方案对得上;test_cw_obs_arch_prep_writeflow.py:360-388 扫描锚(`decide_box_card` 在场断言)在 match 分支保留 decide_box_card 调用后存活——landing 3.2「扫描锚不受影响」预判正确。
11. **正本更新清单目标存在性**:13_pick_family.md §1/§2 E18 行、08_events.md E18 行(含 material_value 引用与「待 derive」态)实存,清单描述与原文一致。
12. **治本三核**:§1.3 归层(语义层价值模型缺维+锚定错位)成立;修法为根(序数维/两态锚/虚构表根源清除)非症状;跨件半问以「族级清点 + 归口 OQ-3」应答——flow 内剩余 6 个 target_comp 消费位逐一实核存在(decide_encounter/megastar/partner/star_tome/wish_trial/planner),已修轨迹 decide_invest(flow.py:503-508)属实,第三件非盲修、有族级处置声明。
13. **关键取舍表 13 项逐条攻**:近兑现加法制弃用(支配保序论证成立)、宽定义弃用(首对解锁语义自洽)、计数加权弃用(P42 λ 前置如实)、需求守卫(零参数、含已穿形态)、两账分工、回落统一(裁定 6)、现读装备区弃用(裁定辖域辨析)、外溢自立迭代(iteration-design §1.1 合规、禁改源收尾清单)、sim 另立(文件面/验收面纪律)——均未破。
14. **需求守卫模型假设边界**:「超需求零边际」对可叠加 key(火力风暴潮 stacking=True)在第 3 件起仍有正边际——但该假设已显式声明为模型假设、冗余件不打负分落 base 参与排序,属声明域内的取舍,攻击未破(如后续重审,入口 = comp 需求向量定义域)。

## 3. 结论

**本轮不收敛**:1 阻断(F1)+ 4 重要(F2-F5)+ 5 次要(F6-F10)。阻断项在共享机器接口签名的核心语义上(5/20 在册阵容受累),重要项集中在 landing 阶段的验收归属与行为变化表锁对象精度。修正后按对抗循环须以新干净上下文再攻一轮。
