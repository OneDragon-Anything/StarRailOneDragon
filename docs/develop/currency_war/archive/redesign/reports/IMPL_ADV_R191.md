# IMPL_ADV_R191 · 对抗审查第 191 轮(无锚轮,2026-09)

> 攻击者=全新视角;对象=redesign/ 四文档(IMPL_DESIGN 重点 §6.4-R 及 R188/R189/R190 修注链 / design_economy / design_latch / design_telemetry 正文+登记节)/IMPL_FIX_LEMMAS(冻结项清单对账);参照=CONTRACT_SERIES_DECISION(冻结契约,不立案)。本轮无锚,自选攻击面。文件面声明:除本文件外零写入;零源码、零 git。

## ① 攻击计划(通读正文后成形)

通读序:IMPL_DESIGN 全文(重点 §6.4-R L528-616 及其 R188/R189/R190 修注链、§1 I/O 表、§6.4 历史档)→ design_economy(含 E4.2 canonical 表/文末 R189 附节)→ design_latch(含 L1-L6/文末附节)→ design_telemetry 正文+键节(登记节在计划成形后才读)→ CONTRACT_SERIES_DECISION → core_swap 三输入件(BATCH0_RESLICE_INPUT/FIXPOOL_EMITTER_DIGEST/SIM_CONSUMPTION_MAP,§6.4-R L530 声明的单一源)→ 代码现树亲验。

面选与理由:
- **A. R190 修注拓扑定性 vs 迁移序结构一致性回扫**(主攻):R190 症1 把装配链(DecideAdapter→prep_brain)勘误为「离线/测试路径」,而迁移序步 3/R189-2 改造② 恰把新核的 statefn 输入缝建在这条链上——勘误是否回扫了依赖该定性的下游步,是 R190 修复批「修而不净」的最高危面。
- **B. 修注链代码锚现树亲验**(策略器侧立案、流程侧豁免):R189-0/R190 修注的全部代码断言(DecideAdapter 定义/消费面、cw_screen_prep import 面、映射两层锚、cw_line_switch、cw_plane_table、cw_investments 注册表值、engine_p1 利息行形态)。
- **C. 标签/编号互斥专项**(R190 症4 同病类在修复批自身文字中的复发):改造件重编号后,同批其他修注对「改造件④」的引用是否仍自洽。
- **D. 单一源兑现与裁决覆盖核对**:R189 声明的文档改动落点(economy/latch 附节、telemetry 登记、IMPL_HISTORY 索引)是否如实;④-4「不属裁决项」处置是否把其中的待裁项一并合法处置。
- **E. 数值锚注册表直调**:interest_cap_override 值域(开源节流 9/利息上调 10/买断制 0)、GOLD 族常量等,不经被审方转述。

未选面申报:冻结族六装置(D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面)禁攻击未触;§2.0 顾问架构与 §7 批摘要链的历史标群非本轮重点(有 R164 双载体分工声明辖)。

## ② 新症逐条

### 症1(中高)R190 拓扑勘误后,步 3/R189-2 改造② 的 statefn 输入缝仍钉在已判「离线/测试路径」的装配链上——生产新核的 TurnState/statefn 输入通路在现行权威迁移序中零载体

- **三元组**:(IMPL_DESIGN.md L532 R189-0 R190 修注③ + L561 改造② + L613 步3 + L577;检验式=①L532 修注③ 明文「decision_assembly.DecideAdapter→prep_brain.assemble/decide/_select 系**离线/测试路径**…其序列化改造若要进生产须显式接线批件」+④「生产件真实清单=黑板契约+committed_from/drive_intention+cw_screen_prep 消费段」(不含 assemble/TurnState);②L613 步3=「**assemble/TurnState 状态量缝**:statefn 输入挂进装配点…④-5 单一源钉死」,L561 改造②=「prep_brain.assemble/TurnState 扩为 statefn 输入缝」;③L577 R189-4 结构签名=`_emit(self, turn: TurnState)`,新核批1 消费 TurnState;④R189-6 步 0-6 全文亲读(grep「接线」零命中)——迁移序无任何一步把 assemble/TurnState 接进生产路径,也无一步声明 mandate_v1.decide_prep_screen 内部自建 TurnState;⑤现树亲验:生产路径=cw_screen_prep.py L1225/L1383 直调 `match.strategy.decide_prep_screen`,cw_screen_prep 从 prep_brain 仅 import `committed_from, drive_intention`(L1203-1205 亲读),现役 DecisionV2Strategy.decide_prep_screen(strategy.py L775 起)零 assemble 调用(Select-String 'assemble' strategy.py 零命中);结果=**矛盾成立**)。
- **论证**:R190 修正拓扑后,prep_brain.assemble 在现树无任何生产调用者;而现行权威迁移序把新核(生产换核实体=match.strategy 持有 mandate_v1)的 statefn 输入缝与「TurnState 投影字段零双源」验收都建在 assemble 上。新核在生产被调时其 TurnState 从何而来,迁移序三选一皆缺位:(a)新核内部直调 prep_brain.assemble ⇒ assemble 由新消费转为生产件,与 L532 修注③「离线/测试路径」定性及④「生产件真实清单」正面冲突,且按修注③自家纪律「进生产须显式接线批件」——该批件在 R189-6 步 0-6 中零载体;(b)新核绕开 assemble 自行从 prep_obs_frame 组装 ⇒ 与步3「单一写端/防投影散落成第二 statefn」的目的自相冲突(第二投影源);(c)维持装配链接线 ⇒ 无步承载。R190 泛化扫(telemetry R190 节 L2532 行)对 L561/L613 的处置=「核过未中…若 statefn 缝**将来**须进生产消费同样受『显式接线批件』约束(申报挂账,不立案)」——条件错置:不是「将来若须」,步3+步4 组成的现行计划自身已触发该需求;且「申报挂账」无挂账载体(判前锁 v6/迁移序/缺陷清单均无此条)。此为 R52-3 自立纪律(「约束无限定而执行有限定、无人对差集负责的形态禁存」)在修复批泛化扫上的复发,亦即 R190 症群(拓扑失真)只修了 R189-0 一处、未回扫依赖旧拓扑的迁移序结构——修而不净。
- **修法方向**(供裁决,不代裁):在 R189-6 中显式补一步(或步3 内子项)钉死生产 TurnState 通路(新核 decide_prep_screen 内直调 assemble 并同步改 L532 修注③ 的路径定性辖域,或声明装配链接线批件并入步1 序列契约接线批),并把「离线/测试路径」表述按「现树现消费面=离线/测试;批1 起经新核内部调用转生产件」精确化。

### 症2(中低)改造件重编号后,同批修注内「改造件④」两读互斥——R190 症4 标签互斥病类在修复批自身文字复发

- **三元组**:(IMPL_DESIGN.md L538 修注 vs L532/L537 修注;检验式=L538 R190 修注明文「R190 后生产序列化受牽面重编号:**①**=…**③**=生产备战消费段序列化(原④)、**④**=sim 侧两个离线消费点同步(原⑤)」;而同批 L532 R189-0 修注末句=「④-1 所称『现役管线步级单动作』的生产载体=cw_screen_prep 消费段(**改造件④**本体)」、L537 ④-1 修注①=「生产的步级单动作形态由 cw_screen_prep 直调单动作接口承载(**改造件④**本体)」、telemetry R190 节 L2514 同款「(改造件④本体)」;结果=「改造件④」在 R190 后语境下按重编号读=sim 侧两离线消费点同步,按三处修注本意读=生产备战消费段序列化(=重编号后的③),两读互斥)。
- **论证**:三处「改造件④」均系 R190 修复批自身落笔的文字,与同批 L538 重编号声明同时生效;读者按重编号追索「改造件④」会取到 sim 侧同步这个错误对象。这正是 R190 症4(④-4/R189-4 错指)所修病类(标签互斥错指)的新实例,且发生在宣布重编号的同批内——编号契约自家未对齐。修法=三处就地补限定(「改造件④(原编号,=R190 重编号③)」)或统一改用重编号后序号。

### 症3(低)④-4「cw4 命名待裁」项被 R189-2 无裁决记录地默认采纳

- **三元组**:(BATCH0_RESLICE_INPUT.md L140 vs IMPL_DESIGN.md L562;检验式=BATCH0 ④-4 末条=「文档 §1 包树落位 decision/cw4/…**命名(是否仍叫 cw4)待裁**」;R189-1 头部(L534)定 ④-4=「流程锚-待重切清单,不属裁决项,处置见 design_telemetry.md R189 节」;telemetry R189 节(L2479-2480)对 ④-4 的处置仅=「系流程锚清单不属裁决项,按对账底稿辖域裁定处置」;而 IMPL_DESIGN L562 R189-2 新建①=「**cw4 包本体**(statefn 8 模块+audit 3 模块先行…)」+§1 L85「落位 decision/cw4/」——grep §6.4-R 全节零「命名待裁/待用户」字样;结果=待裁项被计划正文当既定名采纳,无裁决/呈报/挂账记录)。
- **论证**:④-4 被分类为「流程锚清单不属裁决项」,但其末条实质是**命名裁决待办**而非流程锚漂移;按「待裁项禁静默落定」的既有纪律(先例=④-2 对冻结冲突的显式呈报模式),R189-2 应在采用 cw4 名处携带待裁标记或呈报记录。现文本读者无从得知该名仍在待裁状态。修法=R189-2 新建① 补一行待裁申报(或补记裁决依据)。

### 观察项(不计数,禁凑数纪律下如实降级)

- **OBS-1**:R189-6 步1 R190 修注②(b) 的「适配器输出==[旧核输出] 逐帧恒等」断言,其检出力依赖适配器形态(纯包装构造下恒真);修注未钉死适配器是否=策略级 wrapper(含 decide_shop_screen 透传)。若为策略级 wrapper,(a) 域零漂移门有真实对象(透传保真);若为 prep-only 适配器,(a) 门在步1 无受检对象。建议落码批在 ④-1 改造件①(重编号)定义处钉死形态,两域门的载体声明随之自洽。
- **OBS-2**:④-1 重编号④「sim 侧两个离线消费点同步」列于「生产序列化受牽面」——SIM_CONSUMPTION_MAP ②清单第 3/4 条的同步条件(接口签名/帧契约变化)对商店线不成立(契约 v1 商店线冻结「无(现状冻结)」),该两点的真实受牽面=换核(新核 decide_shop_screen 支持)非序列化;类目错置,行为面零影响。
- **正面核实(攻击未中,如实记录)**:R189-0 R190 修注全部代码断言现树亲验为真——DecideAdapter 唯一定义=decision_assembly.py L153、src 内零实例化消费(adapter.py 仅 docstring 提及)、唯一外部消费=sr-od-test/test_cw_expected_state.py L214、install_obs_ports(currency_war_app 生产接线)不含 DecideAdapter;cw_screen_prep 直调两处+import 面如修注所述;映射两层锚(snapshot_from_obs L95/adapter._anchor_state L94·decision_state L117)、prep_brain L180/L201/L244-245、decision_assembly L200-201 绑定表单键、cw_line_switch should_switch_e L154-175/switch_allowed L143/registry 消费 L168-174、cw_plane_table PLANE_FALLBACK_PRIORS L50、cw_investments 开源节流 9/利息上调 10/买断制 0(L153-155 注册表直读)、engine_p1 利息行 L768 形态 `min(_icap, st.gold // 10) + _flat`(R190 顺手项申报与现树一致)——全部在位。

## ③ 流程锚-豁免清单(不计数,2026-09-03 辖域调整)

| 锚 | 批时快照 | 现树 | 处置 |
|---|---|---|---|
| cw_screen_prep.py decide_prep_screen 直调两处 | L1193/L1351 | L1225/L1383(亲跑) | 流程锚-豁免(R190 顺手项已申报漂移,内容锚在位) |
| cw_screen_prep.py import 段 | L1171-1174 | L1203-1205 | 流程锚-豁免(同上) |
| cw_screen_prep.py 备战五段决策段 | L1191-1215 | ~L1225 起 | 流程锚-豁免 |
| engine_p1.py 利息行 | L752→L757(R190 攻击批)→L768(R190 修复批) | L768,含 `_flat` | 流程锚-豁免;「flat 半边已兑现」申报与现树一致(亲读) |
| engine_p1.py L937/L1027(商店线消费/截断) | 2026-09-03 | 未逐行复核(SIM_CONSUMPTION_MAP 单一源) | 流程锚-豁免 |
| sim/cw_replay.py L239-240 | 2026-09-03 | L240 在位 | 流程锚-豁免 |
| cw_plane_table.py L70(schedule_of 消费段) | 2026-09-03 | 消费段现位 L75-94 | 流程锚-豁免(kernel 但属流程真值源锚漂移;L50 常量锚恰在位) |

策略器侧锚状态申报(照常立案辖,本轮全部命中未立案):cw_observation.py `read_game_state` 批时 L1851→现 L1946(漂移;修注自带「批时快照」限定+内容锚 `def read_game_state`/`reconcile_hp`(现 L1996-2013)在位,按行号=批时快照+内容锚纪律不立案,留档备查)。

## ④ 冻结残余对账节(口径=11 项,零重复立案)

- **LEMMAS 侧 8 项**(IMPL_FIX_LEMMAS 文末冻结残余清单;第 7 项已经 R182 批销账,12→11 计数在案):第 1-6 项(R66 七项之六)+第 8 项(§5.2 窗口高侧预算未随 cap_sup 化)+第 9 项(F7/M4 行 λ̂_U~0.3 v3.3 前旧坐标)。本轮攻击面 A-E 均未触碰上述对象,零重复立案。
- **telemetry 侧 3 项**:第 10 项(R98;激活率门行 L67 裸符号 cap 无核读标)、第 11 项(R115;L69 激活率门验收级节呈现已 supersede 锚零打标)、第 12 项(R162;L75 D_ε 门监督面行引注止 R56,权威侧 R57-R60 零同步)。本轮零触碰、零重复。
- 本轮三症两观察均落在 §6.4-R 迁移序/修注链(主链文档结构面),不属于冻结六装置族(D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面验证装置),未新增任何验证装置类提案。

## ⑤ 清洁门申报

- **本轮新症总数=3**(症1 中高/症2 中低/症3 低),另观察 2 项(OBS-1/OBS-2)不计数。无锚轮自选面,全部三症均经现树亲跑/亲读检验(检验式见各三元组),无凭记忆行号,无仅公式内部自洽的验证。
- 冻结族禁攻击面零触碰;冻结残余 11 项对账零重复;清洁门计数如实申报——既未凑数立案,亦未压症(症1 为对现行权威迁移序的结构性缺口,建议优先排裁)。
