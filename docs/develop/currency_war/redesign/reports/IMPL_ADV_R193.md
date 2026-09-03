# IMPL_ADV_R193 · 对抗审查报告(无锚轮,自选攻击面)

> 攻击者=全新视角;对象=redesign 四文档正文(IMPL_DESIGN.md §6.4-R 与 R189-R192 修注链主攻)+IMPL_FIX_LEMMAS.md 冻结对账;**新增攻击面=CONTRACT_V2_PROPOSAL.md**(提案件:分域/12 类判/§3.3 fail-closed——提案自身一致性、判据推理链、与 v1 正文及 cw_prep_actions/cw_state 现树的对账);参照件=CONTRACT_SERIES_DECISION.md(v1,用户冻结,本身不立案;「提案该不该存在」不攻——R192 症1 既裁)。
> 纪律:计划成形前未读 IMPL_ADV_*.md 与 telemetry 登记节;计划成形后为修注链专项与冻结对账读了 IMPL_ADV_R192.md 与 design_telemetry.md R192 登记节、IMPL_FIX_LEMMAS.md 冻结残余清单(申报,见⑤)。冻结族(D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面验证装置)禁攻击禁新增装置——本轮对 §3.3 计数键的立案按任务书指示以「装置面扩张」定性并给降级建议,非攻击冻结族本体、非新增装置。流程侧代码锚豁免;步1/步2 实施批在飞文件(decision/cw4、series_adapter、cw_screen_prep 等)中间态不立案。每症=三元组(文档行号+检验式+结果),代码引用现树亲验,词表/数值锚直调来源文件复核。

## ① 攻击计划(计划成形时点:通读契约 v1 全文 119 行+CONTRACT_V2_PROPOSAL 全文 68 行+IMPL_DESIGN §6.4-R 全节(L515-620)+IMPL_FIX_LEMMAS 头部与结构、现树 kernel/cw_prep_actions.py 与 kernel/cw_state.py 词表亲验之后)

自选攻击面=**v2 提案与两词表现树的对账**(提案的核心主张是词表辖域分域,故对账面=词表源文件直调)与**提案/修注链的结构自洽**:

1. **分域表的词表覆盖完备性**(主攻):v2 §3.1 商店线域表、§3.2 备战线域表逐行对照 `kernel/cw_state.py` Action 族与 `kernel/cw_prep_actions.py` PrepAction 族的**现役发射集**——分域是否把 v1 混排表的覆盖迁移全了;「原样迁移零改义」(§4 diff#4)是否为真。
2. **提案文档结构自洽**:§0 变更概要「其余条款零改动」与提案自身章节编号的对账;diff 清单 5 项与正文实际变更的互摄。
3. **§3.3 fail-closed 条款的装置面定性**:新计数键 `prep_emit_unclassified_action` 的设立通道 vs 遥测键单一源(design_telemetry 键登记纪律)。
4. **判据推理链逐类核**(契约 §2 帧稳定域语义):12 新判逐类对照动作 dataclass 语义与执行器编排事实(OpenShop read_only 双分支/ClickSpheres 掉箱/OpenTome 选卡归属)。
5. **修注链专项**:R192 三修注+提案的引注失准/与正文冲突/「已裁」声明矛盾;登记节三元组可复算性(计划成形后执行)。
6. **冻结残余对账**:LEMMAS 8+telemetry 3=11 项逐项清点,与本轮新症零重复核验。

未选面申报:12 类判的截断/可续**取向**本身(逐类核读后取向均保守方向或与执行器编排事实相容,无一例可证伪翻案——ClickSpheres「末批后截断」、OpenBox/OpenTome「作最后动作」均按 §2「该动作本身可作为序列最后一个动作发出」合法);④-2 分臂裁决正文;R189-3 前置批论证;冻结族六装置全部未触。

## ② 新症逐条

### 症1(中高)v2 §3.1 商店线域拖拽族行覆盖丢失——Action 族现役发射的 SellBench/DeployMove/SellDeployed 三类在分域后零分类,「行内容承 v1 原样迁移」(§4 diff#4)失真;系 R192 症1「词表辖域错配」在商店线域的镜像复发

- **三元组**:(CONTRACT_V2_PROPOSAL.md L22「拖拽族(SwapDeploy 系/装备拖拽,商店线侧)| 条件 | …」+L62 diff#1「分域两表」+L65 diff#4「商店线域行内容 | 原样迁移,零改义」vs CONTRACT_SERIES_DECISION.md L67 v1 拖拽族行「拖拽族(DeployMove/SellBench/SellDeployed/装备拖拽)| 条件 | …」;检验式=①`grep '^class' kernel/cw_state.py` 亲跑=Action 族含 SellBench(L521)/DeployMove(L585)/SellDeployed(L651)/SwapDeploy(L671)四拖拽类,§3.1 表仅名 SwapDeploy 系——SellBench/DeployMove/SellDeployed 三名零出现(§3.1 全表亲读,BuyCard/LevelUpShop/拖拽族/RefreshShop/CompTransaction/合成触发六行);②商店线决策管线现役发射亲验=decision_v2/candidates.py L504 `SellBench(bench_idx=…)`、L599/L616 `DeployMove(bench_idx=…)`,decision_v2/remediation.py L340/L450 `SellBench(bench_idx=…)`、L687 `SwapDeploy(…)`,kernel/cw_evolution.py L1588 `SellDeployed(…)`(valley_rollback)——三类均 cw_state 形态(bench_idx/d_idx 坐标系,非 PrepAction 物理槽位形态),系 decide_shop_screen 词表内的现役产出;③备战线域 §3.2 L34 的「SellBench / SellDeployed / DeployMove」行辖=PrepAction 词表(物理槽位坐标系),对 cw_state 同名类零辖(分域正是按接口切);结果=**覆盖丢失成立**)。
- **论证**:v1 混排单表的拖拽族行同时覆盖两词表的拖拽类;v2 分域把该行拆两半时,商店线域半边只写下「SwapDeploy 系/装备拖拽」,v1 行内明文的 DeployMove/SellBench/SellDeployed 三个 Action 族类名在 3.1 表中消失——而它们是商店线决策核(candidates/remediation/evolution)的现役发射类。后果:①diff#4「原样迁移,零改义」与事实矛盾(行枚举实质变更且丢失覆盖);②按提案自身 §3.3 的 fail-closed 逻辑(「词表内但无分类动作→截断+计数」),商店线域若照 3.1 落码,现役每一笔 remediation 补偿 SellBench/DeployMove 都成「无分类动作」——正好复刻 R192 症1 攻击的病类(词表辖域缺口),只是从备战侧换到商店侧;③即使按宽读「SwapDeploy 系=同族拖拽泛指」,行文本相对 v1 已改写(枚举→泛指),diff#4 仍失真,且「系」的外延(是否含卖出的 SellBench)无判据可定。次要:§3.1 亦无 cw_state.LevelUp 基类行——docstring 亲读(L566-568)「唯一产出者=decide_shop_screen(产 LevelUpShop);兼容期旧入口已随退役批删除」,基类发射入口已删,可按死词条标注处置,但提案对 v1 合并行「LevelUp / LevelUpShop」的拆分迁移同样未申报。
- **修法方向**(供裁决):§3.1 拖拽族行恢复显式枚举「SwapDeploy/DeployMove/SellBench/SellDeployed(商店线侧,bench_idx/d_idx 坐标系)」,与 §3.2 的同名 PrepAction 行各自带坐标系限定词互斥消歧;diff#4 改「原样迁移,枚举随分域补坐标系限定与商店线侧类名补全」;LevelUp 基类按「兼容面死词条」标注(同 BailToOuter 退役标注先例)。

### 症2(中)提案 §4 章节编号与 v1 §4 正面冲突——「其余条款 §4…零改动」与「版本变更记录见 §4」同句互斥,v2 定稿组装规则自相矛盾

- **三元组**:(CONTRACT_V2_PROPOSAL.md L12「其余条款(§0/§1/§2/§4/§5/§6/§7)**零改动**。版本变更记录见 §4。」+L58「## 4. 版本变更记录(v1→v2 diff 清单)」vs CONTRACT_SERIES_DECISION.md L75「## 4. 空批与控制流(冻结)」;检验式=两文件亲读:提案自身章节=§0/§3(含 3.1-3.3)/§4,提案的 §4=版本变更记录;v1 的 §4=空批与控制流(冻结条款,含「策略器禁用空批表达任何控制流」);结果=**同句两处「§4」指向互斥实体,冲突成立**)。
- **论证**:按提案 L3 声明的定稿路径「经批准定稿后按契约 §6 版本纪律(v1→v2,禁静默改义)替换正文」,组装规则=替换 §3+其余条款零改动(§4=空批与控制流保持);但提案又把自己的「版本变更记录」编为 §4——定稿产物将出现两个 §4,或须把版本变更记录挪位/把 v1 §5-§7 重编号,两者都违反 diff#5「§0/§1/§2/§4/§5/§6/§7 零改动」的字面。L12 一句之内「§4…零改动」与「版本变更记录见 §4」同时成立 only if 两个 §4 并存——契约是接口冻结件、编号是其引用骨架(本文档与 IMPL_DESIGN 修注链大量按「契约 §N」引用),双 §4 使一切「契约 §4」引用变得两义。此系编号病类在新立文件上的再发(R192 症3 自计第三犯,本条为同病类在提案结构层的新 instance)。
- **修法方向**:提案的版本变更记录改编为 §3.4 或文末无编号附章(「版本变更记录」非契约条款,不占条款号);L12 改「其余条款(§0/§1/§2/§4/§5/§6/§7)零改动;版本变更记录见文末附章」。

### 症3(中低,按任务书指示以「装置面扩张」定性)§3.3 新计数键 `prep_emit_unclassified_action` 经契约通道设立遥测计数面,未走 design_telemetry 键登记纪律——契约正文成为遥测键的第二登记源(双源形态)

- **三元组**:(CONTRACT_V2_PROPOSAL.md L56「并按动作键记 `prep_emit_unclassified_action` 计数遥测披露。该键 >0 即发射器词表覆盖缺口信号」;检验式=①grep 'prep_emit_unclassified' design_telemetry.md 全文亲跑=唯一命中 R192 修复批叙事行(L2589,批处置记录),**键节零登记**(design_telemetry 定位=观察键全集单一源,skill 单一源地图明文);②grep 同键 src/sr_od/application/currency_war/telemetry/ 亲跑=零命中(未落码,纯文档态);③先例对拍=既有 fail-closed 分键(θ_unavailable/chi_unavailable/switchline_blank_fallback_frozen 族)均走 design_telemetry 键节登记+R24-2 分键纪律,无一例在契约/设计正文立法键名;结果=**装置面扩张成立:提案在契约条款层新立一个计数遥测键,登记面缺位**)。
- **论证**:§3.3 的**行为半边**(fail-closed 截断+禁猜测分类+禁静默丢弃+键>0 须回契约改版)是契约层合法条款,与冻结族无涉;但**计数键半边**把键名、计数粒度(「按动作键」)写进契约正文,使契约成为该遥测键的第一个权威登记处——v2 定稿后 design_telemetry 若补登记即双源(契约版 vs 键节版,改键名须动两处),若不补即键全集单一源被击穿(键在契约里活着、在键全集里不存在)。此属度量面装置的扩张(新增观察计数面),非冻结族本体(冻结六装置未触),但违反本仓库遥测键单一源纪律的通道要求。
- **降级建议**(治本方向):§3.3 拆两层——契约层只立行为条款(fail-closed 截断+「须回本契约改版补条目」义务+「缺口须可观测」义务);计数键的键名/粒度/分键归实现期 design_telemetry 键登记纪律承载(R24-2 分键先例),或随 v2 定稿批在 design_telemetry 键节同步登记并在契约内只写指针(「披露载体见遥测键登记」),契约不立法具体键名。

### 症4(中低)§3.2 PickBoxCard 行与其自称「§0 零改动」的辖域张力零申报——v1 §0 明文将 box_card 列为契约辖外(「动作编排归画面 op」),提案在不动 §0 的前提下给该类立截断判,diff 清单零申报

- **三元组**:(CONTRACT_V2_PROPOSAL.md L46「PickBoxCard | 截断点 | overlay 语境动作:选卡后 overlay 关闭…」+L66 diff#5「§0/§1/§2/§4/§5/§6/§7 | 冻结 | 零改动」vs CONTRACT_SERIES_DECISION.md L15-18 §0「**pick 类不在本轮**(decide_invest/supply/encounter/megastar/partner 及具体类上的 planner/star_tome/wish_trial/**box_card**):它们是选项决策,动作编排归画面 op」;检验式=两文亲读:box_card∈§0 辖外清单;提案 3.2 表给 PickBoxCard 立行、OpenTome 行(L45)自己还引「契约 §0:pick 类不在序列契约辖内」作截断依据;diff 5 项无一项申报 pick 辖域;结果=**张力成立**)。
- **论证**:提案自己的 OpenTome 行引 §0 论证「后续选卡决策归 pick 语境」,同一张 3.2 表又给 §0 明文辖外的 box_card 类立截断判——按 §0 字面,PickBoxCard 的动作编排归画面 op、不属序列契约辖内,3.2 该行是僭越;按词表完备性 necessity(PrepAction 17 类逐类判正是 R192 症1 修复的主张,发射器确实可发射该类),该行又必须有。两读都通而提案未申报取哪读:若「截断判辖 ≠ pick 决策收编」,§0 应加一句辖域注(截断表辖全部词表成员,编排权归属不变);若属收编,则触动 §0 须进 diff 清单。现状=v2 定稿后 §0 与 §3.2 的辖域声明互相打架,与提案 L3「判据…可推翻。每判附推理链」的自我要求不符。
- **修法方向**:diff 清单补第 6 项「§3.2 对 §0 辖外的 box_card 类立截断判:辖域声明=截断判辖全部 PrepAction 词表成员(发射面),pick 选项决策编排权归属(画面 op)不变,非 §0 收编」;或 §0 加对等辖域注。

### 症5(中低)R192 症3「钉死读法」残留:已判「非本批必动」的④仍留在步1 改造件枚举内,scope 标记与钉死读法内部失谐;且其依赖的登记检验式亲跑不可复算(L538 零命中)

- **三元组**:(IMPL_DESIGN.md L611 步1 标题「…生产备战消费段序列化(**④-1 改造件①②④**)」+同行 R192 修注「②=发射器帧稳定截断的**契约锁**…发射器本体改造在批1 步4…④=sim 侧两个离线消费点同步(R191 收编标已改判『换核受牽面』,**非序列化本批必动,随换核批承载**);步1 改造主体另含 R190 重编号③」vs design_telemetry.md L2588 症3 行登记检验式「grep '改造件[①②③④]' 命中=L532/L537/**L538(重编号权威表)**/L561/L611」;检验式=①grep '①②④' IMPL_DESIGN.md 全文亲跑=命中仅 L611 一处(该半边复算✓);②grep '改造件[①②③④]' IMPL_DESIGN.md 全文亲跑=命中 **4 行=L532/L537/L561/L611,L538 零命中**——L538 亲读=「改造件列全(序列化的全部受牽面):①…」,编号不邻「改造件」三字,不匹配该模式;结果=**登记检验式不可复算成立;尾注 scope 失谐成立**)。
- **论证**:①钉死读法把尾注三枚举项中的②重释为「契约锁」(在步1,合法)、④判「随换核批承载」(不在步1)——枚举作为步1 改造件的 scope 标记,三枚举项之一被同注明文移出本步,标记与内容失谐:读者按尾注索步1 范围仍会取到假成员(④),须再读同注的排除句才能得到真集合(①+③+②契约锁);这与 R190 修注① 当年直接写「本步=R190 重编号①+③」的干净形态相比是倒退,正确修法本是改枚举而非重释枚举。②登记节检验式是「打标不删史」审计链的可复算承诺,L538 命中声明亲跑为假——修复批自己的清点账与文档事实有错位(错账方向:多报一行,恰是「重编号权威表」所在行,即该表实际不含可被该 grep 命中的形态,编号邻接假设失效),后续轮按此检验式复算将误判闭合证据在位。
- **修法方向**:L611 尾注括注改「(④-1 改造件①③;②的契约锁=本步验收第三项;④已改判换核受牽面移出本步)」;design_telemetry L2588 检验式勘误(实际命中 4 行,L538 以内容锚另行指认)。

### 观察项(不计数,禁凑数纪律下如实降级)

- **OBS-1(低,引注失准)**:提案 L29「槽位坐标系=PrepAction 物理槽位,与**族 A** 坐标系差异不辖截断判」——「族 A/族 B」定义载体=kernel/cw_state.py L509-512 模块注释(族 A=状态/账本坐标系,族 B=画面坐标系),契约两文件内零定义零指针,契约读者不可解析;建议提案补指针「(族 A/B 定义=kernel/cw_state.py 模块注释)」。
- **OBS-2(低,推理链措辞过强,取向不翻案)**:提案 L49 OpenShop read_only=True 分支依据「读数时点与回环分支不可由发射器静态推出」——cw_prep_actions.py L113-115 docstring 亲读,read_only=True 路径系定式编排(CwOpOpenShop 幂等→观察刷新→不调商店决策→CwOpCloseShop→回备战),「回环分支」的实际分叉面有限;但判=截断点系保守方向(发射器不续发),与 §2 语义相容,不立案,仅记推理链论据弱于结论。
- **正面核实(攻击未中,如实记录)**:①备战词表 17 类亲跑(`grep '^class' kernel/cw_prep_actions.py`+PREP_ACTION_TYPES L142-148 白名单亲读)=提案 12 新判类名与 5 承判类名逐一相符,零多零漏;5+12=17 恰合;②4 退役类标注(BailToOuter/EnsureShopOpen/EnsureShopClosed/RunBuyPhase)与现树 docstring 亲读一致(EnsureShopOpen/Closed L97-104「W970 批 C 退役(dd-017)…仅存续旧环/离线兼容面」、RunBuyPhase L127「执行器组合分支已随 BuyShopCards 壳退役删除」+全树 grep BuyShopCards 壳只余注释/复用指针);③OpenShop read_only 双分支描述与 docstring L111-115 逐句相容;④v1 §4「控制流动作不进 execute 验证链」引用(提案 L41)准确;⑤R192 反转标的契约引文「包一层长度 1 序列的适配器」=v1 L34-35 亲读逐字相符;⑥R192 修注(L584/L549/L611)与 telemetry R192 勘误标(L2503)全部在位;⑦登记节症1 检验式①(17 类亲跑)复算为真。

## ③ 流程锚-豁免清单(不计数)

本轮主攻面为契约提案与词表对账,策略器侧锚(candidates/remediation/evolution/cw_state/cw_prep_actions)全部亲跑入症或入正面核实,零漂移立案。未引用 operations/ 与 sim/engine_p1.py 流程锚(无需);步1/步2 实施批在飞文件(decision/cw4、series_adapter、cw_screen_prep 序列消费段)中间态未立案、未消费为证据。

## ④ 冻结残余对账(口径=11 项,零重复)

- **LEMMAS 侧 8 项**(IMPL_FIX_LEMMAS.md L3370-3382 亲读,9 格中第 7 项带 R182 销账标→活 8):第 1-6 项(R66 七项之六)+第 8 项(§5.2 窗口高侧预算未随 cap_sup 化)+第 9 项(F7/M4 行 λ̂_U~0.3 v3.3 前旧坐标)——清单文末零新增零改动,本轮亲读确认。
- **telemetry 侧 3 项**:第 10 项(R98)/第 11 项(R115)/第 12 项(R162)——口径「LEMMAS 8+telemetry 3=11」与 R190/R191/R192 登记节复述一致。
- 本轮五症落点=提案分域表词表覆盖(症1)/提案章节编号结构(症2)/遥测计数键登记通道(症3)/pick 辖域申报(症4)/修注枚举与登记检验式(症5),均不属冻结六装置族——症3 立案对象=**提案新增**度量面装置的设立通道(双源形态),非攻击既有冻结装置本体、亦非本轮新增任何验证装置提案(降级建议方向=拆层去键,收缩装置面);其余四症纯文档结构/对账层。零重复立案。

## ⑤ 清洁门申报

- **本轮新症总数=5**(症1 中高/症2 中/症3 中低/症4 中低/症5 中低),另观察 2 项(OBS-1/OBS-2)不计数。无锚轮自选面=契约 v2 提案+修注链;全部五症检验式均含现树亲跑/亲读(词表类锚=cw_prep_actions.py/cw_state.py/decision_v2 管线源文件直调;grep 复算=登记检验式逐条重跑),无凭记忆行号,无仅公式内部自洽的验证。
- 无凑数:五症各自独立(词表覆盖/编号结构/装置通道/辖域申报/枚举残留),任删其一其余仍立;无压症:症1 系提案核心主张(分域)的自洽性断裂——定稿前不修,商店线域照落即复发 R192 症1 病类,建议随 v2 定稿裁决一并处置(批1 派单前置件链上,提案本就是 R192 症1 的修复载体)。
- 申报:计划成形后读了 IMPL_ADV_R192.md 全文、design_telemetry.md R192 登记节(L2503/L2579-2590)、IMPL_FIX_LEMMAS.md 冻结残余清单(L3370-3382),用于修注链专项、检验式复算与冻结对账;telemetry 登记节其余部分未读。批时快照=2026-09-03 后现树(只读);文件面=除本报告外零写入、零源码、零 git。
