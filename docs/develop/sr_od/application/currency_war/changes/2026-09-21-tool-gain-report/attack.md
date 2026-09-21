# tool-gain-report 设计·核一无前提攻击报告

> 攻击对象:`design.md`(草案态,单文档方案)。前置依赖已核:gain-chain design.md 全文、
> iteration-design.md §5/§7。纸面对纸面 + 纸面对实码;所有证据为仓库现状实读。
> 结论只看证据。共 11 条发现(4 major / 7 minor)。

---

## 1. 符号/锚全量核验结果(先行声明,不计发现)

以下设计引用的符号与锚**逐个实读相符**,不作为攻击点:

- `cw_vocab.py:571-661` 七参数类字段:冶金炉/特权卡 `target_kind`+`item_name`/`row`/`slot`;扳手/精密扳手/员工投影仪/完美投影仪/令牌 `row`/`slot` —— 与 design.md §1.2 相符。
- `cw_equip_env.py:626-628` 特权卡判据 = 「对应进阶成品在手(栏内拖法)」库存腿独产;全仓 `CwActionPrivilegeCardUseParam(`/`CwActionFurnaceUseParam(` 构造点仅 `strategies/impl/mandate_v1/entry.py:798-801` 且均 `target_kind='equip'` —— 「拖角色腿从未发射」成立。令牌 `rc_missing` fail-closed(:668-670)、投影仪 `cold_start_later`(:665-667)、扳手 `dest_unready`(:662-664)在册。
- `zero_writes.py` 七工具函数(`:43-81`)现签名 `(gs, param, sig)` 与 design §2.1「同形」表述相符(但见发现 6)。
- `cw_tool_use_action.py:70-78` `_REPORT_BY_CLASS` 注册表、`:126-129` 统一三参调用形态实读确认。
- `cw_game_state.py:1971` `consumables: Field[list[str]]` 字段在库(fields.md §3.2.16;design 未写行号,任务书给的 :2027 实为 `frame_class_shop`,设计文档本身无此错)。
- 四桥在库:`spawn_equip_bench_unit`(cw_effect_inventory.py:1000)、`grant_equip_item`(:1051)、`transform_equip_to_privilege`(:1073,签名 `(gs, source_name, *, frame='')`,与 design §2.2 调用形态相符)、`transform_worn_equip_to_privilege`(:1213,本批 fail-closed 不消费)。
- `cw_gain_chain.py` **已存在**(三原语 + 三回调 + `GainOutcome` 全数落地,模块自述 3.1 语义落地、零生产接线)——gain-chain 的裁定③④⑤、`rand` 必带、零吞错、未观察留证等 design §1.2/§2.3 引述与实码逐条相符。
- 骇客改件先例(`pick_invest.py:57-89`)、`test_cw_unified_action_4.py` 在库,design §1.2/§2.4 引用有效。

---

## 2. 发现清单

### 发现 1 [major] | design.md §2.0/§2.2 | 工具消耗记账载体与实况容器冲突:特权卡「按成功处理」的写法会在**每次成功使用后触发失配安灯停局**

- **发现**:§2.2 各行的工具消耗只写 `consumables −1`,而效果腿写的 `gs.equips` 列表派生自**消耗前的现读**(含工具件自身)。实况是:**工具件本来就住在 `gs.equips` 里**(备战入口观察「全量名单入记录,工具件照录」;策略器工具发射快照即 `gs.equips` 现读,「全量含工具」口径)。于是特权卡库存腿:桥 `transform_equip_to_privilege` 把「含特权赋予卡自身」的列表做替换后 `write_logic` 写回 → 拖曳成功、游戏消耗掉卡 → 下次备战入口 heavy 实读 equips 少了这张卡 → `observe()` 命中 logic 失配 → 真失配 → 安灯钩子 `stop_running`(生产已武装)。**成功的动作 = 停局**,与 §1.1 自己的动机(「拖曳失败应由对账暴露而非静默吞掉」)正好反向。同理命中:扳手回区腿、冶金炉拖角色腿②(均 `write_logic` 写 equips 且不摘工具件;二者现役发射位 fail-closed,属延迟引爆)。冶金炉拖装备腿②走 `write_logic_rand`,工具消失被随机面吸收为 `logic_rand_outcome`——连失败也一并吞掉(与 §1.1 动机相反的另一半)。员工/完美投影仪不写 equips,观察覆盖静默记账,反而是干净的。**现役唯一准入的工具 = 特权赋予卡(库存腿)→ 本设计落地即触发,第一张卡就停局。**
- **证据**:
  - `operations/cw_screen/cw_screen_prep.py:338-350`(观察写端「全量名单入记录,工具件照录」→ `gs.equips`);
  - `strategies/impl/mandate_v1/mandate.py:200`(`gs.equips` 现读「全量含工具」口径)、`entry.py:732`;
  - `sim/cw_sim_equips.py:268-272`(sim 扳手腿的工具消耗 = `owned.remove('拆装扳手')` 改 `gs.equips`——消耗即从 equips 摘除的既有建模先例);
  - `kernel/cw_effect_inventory.py:1082-1089`(桥用含工具的 `inv` 全量替换写回,`write_logic`);
  - `kernel/cw_game_state.py:2360-2371`(`observe()` logic 失配路由;equips 无吸收规则,`_absorb_slot_reorder/_absorb_board_derived` 均不辖 equips);
  - `currency_war_app.py:125-128` + `kernel/cw_mismatch_policy.py:95-121`(安灯生产武装 = `stop_running`);
  - `docs/game/currency_war/research/equipment_mechanics.md:79`(特权赋予卡「用后消失」)。
- **修正方向**:工具消耗的容器表达必须落在 `gs.equips` 上——同一逻辑写内做多重视集移除(工具件 + 效果改写),或各效果腿构造新列表时排除已消耗工具件;`gs.consumables` 要么在本批给出真实读端计划、要么明示退役/降级并在 fields.md §3.2.16 一并收口。逐工具重走一遍「写什么→下一观察比对什么→失配意味着什么」的推演表,把「成功=失配」路径全部排除后 §2.0 的承诺才成立。

### 发现 2 [major] | design.md §1.2/§2.2/§2.3 | `gs.consumables` 是零读端死字段:「消耗 −1 → 下一帧观察对账暴露失败」对该字段结构性不成立,且与三处在册申报冲突

- **发现**:全 `src/` 检索 `consumables` 仅 3 处命中:字段声明(cw_game_state.py:1971)、域注释(:176)、审计行(cw_projection_audit.py:191)。**不存在任何观察写端,也不存在任何逻辑写端**——写了永远不被覆盖、不被比对、不被读。§2.0「拖曳失败 = 失配响停修因」的机制前提是「下一帧观察覆盖该字段」,对 consumables 该前提为空:失败静默、账面永久污染、后续多重集移除叠加在脏值上。同时:①审计行现申报 `AUDIT_OBSERVATION_ONLY`(「有观察读端但零逻辑写端」)——读端声明本身与代码不符,本批再加逻辑写端则申报彻底失真;②fields.md §3.2.16 申报的观察写端「本屏道具区覆盖」未实现、逻辑写端「RunTools 用工具」指向**已退役**的组合壳(cw_equip_env.py:49、mandate.py:2078「组合壳 RunEquip/RunTools 删除退役」);③design §1.2 把该字段当「基线事实」引用,未标注上述任何缺口。fail-closed 边角(§1.4 令牌零写)之所以「无账也无害」,恰是因为整条 consumables 通道是死的——这个巧合不该作为设计依据。
- **证据**:`src/` 全量 grep `consumables` 仅上述 3 处;`kernel/cw_projection_audit.py:191-198`(consumables/occupied_equips 两行 `AUDIT_OBSERVATION_ONLY` + 写端单一源申报);`docs/develop/sr_od/application/currency_war/game_state/fields.md:438-443`(§3.2.16 写端完整清单,两项均死);`cw_equip_env.py:49`、`strategies/impl/mandate_v1/mandate.py:2078`(RunTools 退役)。
- **修正方向**:与发现 1 合并裁决消耗的容器归属。若保留 consumables:先补观察读端(识别面工作,超出本批范围须显式立项)并把审计行/fields.md 写端清单改到与现实一致;若不保留:从语义表删除 consumables 行,申报正本同步面(fields.md §3.2.16、`PROJECTION_AUDIT` 两行 + 人读镜像 projection-audit.md)列入本批文件面。gain-chain §2.6-6 有「字段申报面随批同步」的在册先例可循。

### 发现 3 [major] | design.md §2.1 | EQUIP_WRITE_SIDES「四行收口为已接线」未指明是哪四行,且收口后至少三行的写端值(sidebar 值)必然失真,词表封闭校验没有本批写端的合法形态

- **发现**:①「接线候工具上报形态」注记在码中恰四行:员工投影仪(:262)、完美投影仪(:265)、特权赋予卡(:279-280)、好运令牌(:289-290)。其中**好运令牌本批裁定零写、写端随 R9 判据批**(§2.2)——把它的注记收口为「已接线」与语义表自相矛盾(除非收口文案显式保留「上报层零写+留证,容器写端随 R9」)。②本批真正发生写端迁移的行反而不带该注记:冶金炉行值 `'observation'`(:324,注记 :274-275)、拆装扳手行值指向 `op:CwActionSellBenchParam/RunTools 装备转移链`(:326——RunTools 已退役,行已失真,本批新建上报腿后更失真)、员工/完美投影仪行值 `'bridge:spawn_equip_bench_unit'`(:320-321——本批投影仪改走 `gain_character`,不再消费该桥)。③`_validate_equip_write_sides` 值词表封闭(`bridge:`/`contribution:`/`op:`/`observation` 四形,`bridge:` 目标必须在 cw_effect_inventory 可解析,:351-371)——指向新建 `tool_use.py` 上报函数的行没有任何合法写法,设计未交代加形还是用 `op:` 形承载。实现者按「四行注释收口」字面执行会漏掉真正要改的行、改错不该改的行。
- **证据**:`kernel/cw_affix_effects.py:260-290`(四行注记与冶金炉/扳手注记原文)、`:307-333`(side 值全表)、`:336-371`(键集恰等 + 值词表封闭 + bridge 目标解析校验)、`kernel/cw_effect_inventory.py:1210`(第四处「接线候」注记,transform_worn 桥头)。
- **修正方向**:逐行点名列出本批申报表改动面(行 → 旧值 → 新值 → 注记文案),覆盖:冶金炉(观察→本批写端)、扳手/精密扳手(退役锚→本批写端)、员工/完美投影仪(spawn 桥→链路径)、特权赋予卡(桥保留,注记收口)、好运令牌(注记收口文案带零写语义);并为「上报函数」定一个词表合法形(扩 `report:` 形或复用 `op:` 形,二选一写死),同步构建校验。

### 发现 4 [major] | design.md §2.0/§2.2 | 投影仪走链的复制行为(凑三合成、席满溢出)无游戏侧依据,属在未证行为上接线

- **发现**:§2.2 员工/完美投影仪行裁「是(落位/溢出/回调/升星全走链)」,无任何依据标注。game 侧仅有:官方升星规则「**招募** 3 个同名同星 → 自动升星,凑齐即合」(`docs/game/gameplay/currency_war.md:73`,官方核实语境是招募/买牌);投影仪条目「备战席创造其 1 星复制……**受备战席槽约束**」(`equipment_mechanics.md:76-77`)。两条都不能推出:①投影仪复制凑满三只是否触发合成(官方规则字面是状态式的「凑齐即合」,支持设计,但验证语境只在招募通道);②席满时复制是**溢出入位**还是**拒绝落位/拖曳无效**——「受备战席槽约束」的措辞甚至更接近拒绝;③复制落点槽位是否等于 `bench_place` 的首空槽预测。猜错任一条的实机形态 = bench logic 写被实读证伪 → 安灯停局假阳性(或漏记)。对照:同设计对冶金炉变异后果明确标了「候采证」(§1.4),对投影仪却没有同等处理。
- **证据**:`docs/game/gameplay/currency_war.md:73`、`docs/game/currency_war/research/equipment_mechanics.md:76-77`、`docs/game/currency_war/research/merge_mechanics.md`(落点规则全部源自买牌通道);design.md §2.2 投影仪两行无依据标注。
- **修正方向**:二选一并写入设计——(a)补证:引用或实测确认「复制=获得角色」在合成/溢出/落点上与招募同规,标注出处;(b)标候采证:比照 §1.4 冶金炉行,给实机采证点与推翻后的升格路径,在此之前投影仪行不进「已接线」申报(现役投影仪发射位 fail-closed,不接线无实机代价)。

### 发现 5 [minor] | design.md §2.2 | 冶金炉采样池口径:有未引用的 sim 同款先例;「注册表类别=游戏『同类型』」的成员资格轴未进披露,且与 game 文档一条在册待实测项相接

- **发现**:「注册表同类别集 − 自身、等概率均匀」与 sim 既有实现**逐字同构**(`sim/cw_sim_equips.py:282-290` `furnace_reroll`:「同 category 池均匀,排除自身」)——这是最强依据,设计未引。同时 game 文档对「同类型」无注册表定义,且在册待实测项「**刷新结果池是否含光能电池(简易池 8 件 vs 标准 7 件口径)**」(`equipment_mechanics.md:239`)正是池成员资格问题——注册表口径隐含选了「8 件」边,该取舍未披露(HACKER_MOD 先例披露的恰是「池数据缺口」这个成员资格轴,pick_invest.py:60-68;本设计只披露了「分布未实测」,漏了成员轴)。骇客改件「卡文口径 ≠ 注册表类别」的教训在先,同类风险不应只靠 outcome 行事后校准。
- **证据**:`sim/cw_sim_equips.py:282-290`;`docs/game/currency_war/research/equipment_mechanics.md:73`(「同类型随机」无定义)、`:239`(待实测项);`kernel/cw_action_report/pick_invest.py:60-77`(先例的披露形态)。
- **修正方向**:补引 sim 先例;披露键覆盖「池成员 = 注册表同类别」这一建模假设本身,并点名与简易池 8/7 待实测项的关系(注册表口径含光能电池);均匀分布假设维持现披露。

### 发现 6 [minor] | design.md §2.1/§2.0 | 冶金炉 rng 注入与「七函数同形三参 + op 统一分派」未闭环;「实现时对齐」是未定稿措辞

- **发现**:§2.1 先写「签名与现役零写版同形 `(gs, param, sig)`」,同段又给冶金炉加 `rng` 关键字——两句话矛盾。实机调用点是无分派的统一三参直调(`cw_tool_use_action.py:126-129`),命名规约冒烟锁对**每个**动作类以 `fn(gs, param, sig)` 三参调用(`sr-od-test/test/sr_od/application/currency_war/test_cw_action_report_contract.py:58`)——rng 若无缺省值,契约锁与 op 直调同时 TypeError。「注入源与 pick_invest 采样链同源,实现时对齐」把唯一剩余的自由度留给实现者(违反「实现者无需再设计」;草案态可,定稿不可)。
- **证据**:`kernel/cw_action_report/pick_invest.py:225-241`(先例形态 = `rng: random.Random | None = None` 关键字缺省,函数体内兜底 `random.Random()`);`operations/cw_op/cw_tool_use_action.py:126-129`;`test_cw_action_report_contract.py:34-60`。
- **修正方向**:写死为 `rng: random.Random | None = None`(先例同形,实机不传 = 未播种猜测、sim/测试传流键),op 侧三参调用零改动,契约锁天然兼容;删除「实现时对齐」措辞。

### 发现 7 [minor] | design.md §2.2 | 投影仪 `gain_character` 调用形态缺必填参数,且工具域 producer 新名未定

- **发现**:语义表写 `gain_character(char_id, 1, rand=False)`;落地签名是 `gain_character(gs, name, star, *, rand, sig, evidence, producer)`(cw_gain_chain.py:439-441),`sig`/`evidence`/`producer` 均为无缺省 keyword-only 必填——按表直写即 TypeError。producer 取值也未定:gain-chain 纪律是「新写端新名,不沿用旧名伪装连续」(gain-chain §2.1),工具域链调用的 producer(以及 evidence 词根)应显式定名,否则容器写 produced_by 归属与失配豁免注册表归因都会含糊。
- **证据**:`kernel/cw_gain_chain.py:439-441`、`:50-52`(GAIN_CHAIN_PRODUCER 新名纪律);design.md §2.2 投影仪两行。
- **修正方向**:语义表补全调用形态(含 sig 来源 = op 现役 `ChannelSig(family='logic_action',...)`;evidence 词根如 `tool_projector`;producer 常量名定死)。

### 发现 8 [minor] | design.md §1.4/§2.2 | 「变异产物是否触发获得后果」采证点没有采集机制,且后果表成员确可入炉池(场景可达非空想)

- **发现**:§1.4 把「变异 ≠ 获得」列为实机采证点、裁定不触发 `on_equipment_gained`——开放问题本身合法,但本批没有为它布置任何采集手段:冶金炉 equips 腿走 `write_logic_rand`,产物猜错只落 `logic_rand_outcome` 行(记的是「采样 vs 实读」);若游戏真对产物送角色(如炉产出 分身墨镜Max/数据拷贝仪Max——三者同属注册表 `特殊` 类别、互在彼此的 v0 池内,`EQUIP_ACQUIRE_CONSEQUENCES` cw_effect_inventory.py:1360-1364),多出的银狼只会被 bench 观察静默覆盖,无行可查,采证无从谈起。
- **证据**:`kernel/cw_effect_inventory.py:1360-1364`(后果表成员与类别);`sim/cw_sim_equips.py:288-289`(同类别池 ⇒ 后果件可为产物);design.md §1.4 对应行(无采集机制)。
- **修正方向**:给采证点定观测面(如 rand outcome 行补记产物类别命中后果表的标记,或留证行),否则该开放问题永远只能靠人工复盘碰运气。

### 发现 9 [minor] | design.md §2.2/§2.3 | 留证出口与异常粒度的命名锚不准:gain-chain 裁定⑤的落地机制是 kernel `_emit_defect` 专用 kind,不是 telemetry `record_defect`;桥 None 返回的处置未指定;令牌留证行 kind 未定

- **发现**:§2.2 两处写「`record_defect` 留证不停机(gain-chain 裁定⑤同款)」——「同款」实码是 `_emit_defect` + 专用 kind 常量(`DEFECT_BENCH_UNOBSERVED` 等,cw_gain_chain.py:54-59);telemetry 的 `record_defect` 是另一个分级出口(telemetry/defects.py),两者行为不同。二选一都行,但设计应点名出口与 kind 词表(现只给特权卡 char 腿一个 kind `tool_privilege_worn_unsupported`;令牌零写留证行、扳手/投影仪目标单位缺失行、桥返回 None 行的 kind 均未定)。另:`transform_equip_to_privilege` 对「库存未观察/无此件」静默返回 None(cw_effect_inventory.py:1082-1084),不抛错不落行——§2.3 说「未观察 = bug 面零写 + 留证」,但桥自身不落证,谁消费 None 落证、kind 是什么,设计未写。
- **证据**:`kernel/cw_gain_chain.py:54-59,336-344,464-471`;`telemetry/defects.py`(record_defect 分级出口);`kernel/cw_effect_inventory.py:1073-1090`;design.md §2.2/§2.3。
- **修正方向**:点名留证出口(kernel `_emit_defect` 沿 gain-chain 同款最顺)、补齐 kind 词表、写明桥 None 返回的消费与留证责任在 tool_use 上报函数。

### 发现 10 [minor] | design.md §2.1 | 文件面清单缺口:随批失真的既有注释/申报面未列入更新范围

- **发现**:本批语义落地后以下在册文字即失真,§2.1 文件面均未列:`cw_vocab.py` 七类 docstring(冶金炉「产物不可预知 → 随机面观察收口」:574-579;特权卡 char 腿「逻辑态只写工具 −1」:596-598,与 fail-closed 零写新约相抵);`cw_tool_use_action.py` 模块头与 detail 文案「零对拍,消费归观察」(:1-9,:130);`cw_effect_inventory.py:1210` 桥头「接线候」注记;发现 2/3 已列的审计行与 fields.md 写端清单。单文档无 landing,这些正本同步面至少要在 §2.1 列全,否则落地批与未来 landing 都会漏。
- **证据**:`kernel/cw_vocab.py:571-605`;`operations/cw_op/cw_tool_use_action.py:1-9,130`;`kernel/cw_effect_inventory.py:1210`。
- **修正方向**:§2.1 文件面逐项补列(或声明「随发现 1-3 的修正面一并收口」)。

### 发现 11 [minor] | design.md 卷首/§0 | 依赖表述未钉阶段:gain-chain 原语已落地(3.1),本批真正需要的只是它;「gain-chain 落地批交付」字面会把本批过度闸在 3.2 接线之后

- **发现**:卷首写「依赖 = gain-chain 落地批交付 `kernel/cw_gain_chain.py`(未落地前本批不开工)」。实码:该文件已在库,三原语 + 回调 + 单级合成全数落地,模块自述「零生产接线;首个接入面(投资环境落地相)归 3.2」——即 gain-chain 落地的 3.1(原语)已完成、3.2(投资环境接线)未完成。本批只消费原语,不需要 3.2。依赖写法应钉到「gain-chain 落地 3.1 交付的原语面」,避免「整批落地才开工」的误读(也避免与 3.2 的在飞改动抢文件)。
- **证据**:`kernel/cw_gain_chain.py:1-21`(模块头:3.1 落地、零生产接线、3.2 预告);design.md 卷首承接出处行。
- **修正方向**:依赖句改为按阶段钉死(3.1 原语面),并注明与 gain-chain 3.2 无文件冲突面(若 `pick_invest.py` 等有交集则列明)。

---

## 3. 已查证为协调的点(攻击过、不成立,留档防复议)

- **「失配响停」机制本身**(§2.0):生产安灯确已武装、真失配确会 `stop_running`(`currency_war_app.py:125-128`),设计措辞与机制相符——失灵的只是 consumables 这一个字段(发现 2)与被随机面吸收的冶金炉装备腿(发现 1),不是机制理解错。
- **特权卡 char 腿 fail-closed**、**令牌零写随 R9**:判据面与构造点双重证实永不发射,fail-closed 留证的失败安全(§1.4)自洽。
- **变异面不走链的数量不变论证**:冶金炉/特权卡产物数量不变、无「获得」时点的回调枚举成员,裁定自洽(后果触发风险已在发现 8 另行覆盖)。
- **扳手回区腿与既有 op 写端无双写**:申报行指向的 RunTools 腿已退役,现役无同类容器写端,新建腿不构成双写(但申报行失真归发现 3)。
- **零写退役的测试爆炸半径**:sr-od-test 对 `zero_writes` 的引用仅 3 个契约/命名规约测试(test_cw_action_report_contract / test_cw_pick_channels_t60 / test_cw_unified_action_2a),包级 `__getattr__` 命名规约下迁移到 `tool_use.py` 天然兼容;`test_cw_unified_action_4` 在库,§2.4 回归面有效。

## 4. 试读结论(逐节「凭这份能开工吗」)

- 逐工具写端锁/扳手回区/费用门防御/原子 op 回归:**可开工**(语义表 + 实码足够)。
- 消耗腿写什么容器:**不可开工**——发现 1/2 未裁决前,照表实现即产出「成功即停局」的实机行为。
- 申报表收口:**不可开工**——发现 3,行集与词表形态未定。
- rng 注入/链调用形态:**不可开工**(机械层面可自行补齐,但属「实现者再设计」,发现 6/7)。

## 5. 总结论

**需修订后收敛。** 计数:major 4(发现 1-4)、minor 7(发现 5-11);另留档 5 条已查证协调点。
核心修正责任:①工具消耗的容器归属与逐工具失配推演重走(发现 1/2,一体裁决);②申报表改动面逐行点名 + 词表形态定案(发现 3);③投影仪走链行为补证或标候采证(发现 4)。minor 各条随修订顺手收口。
