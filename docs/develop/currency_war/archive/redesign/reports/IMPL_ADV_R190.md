# IMPL_ADV_R190 · 货币战争策略器重构设计文档 对抗审查 第190轮(无锚轮)

> 攻击对象:redesign/ 四文档正文(IMPL_DESIGN.md 为重点、新 §6.4-R 主攻面;design_economy/design_latch/design_telemetry 正文体)+ IMPL_FIX_LEMMAS.md 冻结项清单(只读对账)。参照(非攻击对象)=CONTRACT_SERIES_DECISION.md(契约 v1,2026-09-03 用户整包批准冻结)。
> 文件面声明:本文件是本轮**唯一写入**;对象文档全只读;代码/底账仅只读引证。辖域裁定=2026-09-03(流程侧代码锚豁免;策略器侧锚照常立案)。
> 无锚纪律执行:攻击计划成形前未读 IMPL_ADV_*.md 与 design_telemetry.md 文末登记节;计划成形后为冻结残余对账与 R189 呈报核验读了 telemetry R188/R189 节(申报)。

---

## ① 攻击计划

**面选与理由**(通读四文档正文+BATCH0_RESLICE_INPUT/FIXPOOL_EMITTER_DIGEST/SIM_CONSUMPTION_MAP 三底账+契约 v1 全文后成形):

1. **§6.4-R 与冻结契约 v1 的一致性**(主攻):R189 是结构性新增且自称「与契约原生一致零翻案」——契约是用户裁决冻结件,文档与它的不一致可立案;重点核 ④-1 形状裁决、R189-4 结构签名/截断枚举、mandate 字段定性、④-2 冻结原文处理。→ 命中症3。
2. **§6.4-R 代码锚与现树拓扑对账**(策略器侧锚照常立案):R189-0「重构实体」解剖、④-5 输入面映射锚、④-3 现役对应物分档、R189-2 免做/改造/新建三档锚,逐个亲跑验证。→ 命中症1/症5。
3. **迁移序各步验收判据的可执行性/检出力**(R6-5「实现者遇缺输入自造方向」与 R14-2「必红/必绿锚」病类的迁移序形态):步 0-6 每步验收对象是否真被该判据覆盖。→ 命中症2。
4. **引用标签与计数完备**(R9-1「权威表缺行/悬空引用」病类):④ 编号引用、R189-5「14+1」对底账、三个新增对拍计数附注。→ 命中症4;其余核过未中(14+1 与 FIXPOOL §2① 逐行对上;三计数提议=FIXPOOL §5 附注三件逐字一致;D-B 先决 P7/F4 度量先修/D-lv7 检查点均与底账 §3/§4/§5 对齐)。
5. 弃攻面申报:④-2 分臂裁决本身(冻结原文优先+显式呈报,处理合规);R189-3 独立前置批论证(A/B 归因切分,推理链完整);数值锚(狸 flat=2@cw_investments.py L242 亲验、PLANE_FALLBACK_PRIORS(9,9,9)@L50/schedule_of@L70 亲验、sim_baseline_20260902_v3 落档亲验、`grep 'NMF §'`=51 与 telemetry R189 计数对账亲验)——全部复核通过零缺陷。

## ② 新症逐条

### 症1(中高)R189-0「重构实体=替换 prep_brain._select 的委托」拓扑断言失真——生产备战决策不经 prep_brain/DecideAdapter

- **三元组**:(IMPL_DESIGN.md L532「生产管线已在树且冻结可用(decision_assembly.py 的 DecideAdapter/黑板契约 + prep_brain.py 的装配点管线 + 执行回放);『重构实体』=替换 `prep_brain._select` 对现役 `strategy.decide_prep_screen` 的委托」;检验式=`grep -r 'DecideAdapter' src/` 消费者亲跑+`Select-String 'decide_prep_screen|prep_brain' operations/cw_screen/cw_screen_prep.py` 亲跑;结果=**DecideAdapter 在 src/ 零消费者**(唯一定义处 decision_assembly.py L153;唯一外部消费=sr-od-test/test_cw_expected_state.py),生产备战消费点=`operations/cw_screen/cw_screen_prep.py` **L1193/L1351 两处直调 `match.strategy.decide_prep_screen(session, config)`**,cw_screen_prep 从 prep_brain 仅 import `committed_from, drive_intention` 两个方向层助手(L1171-1174 亲读),不调 assemble/decide/_select)。
- **断言与代码不符的两半边**:①「生产管线(decision_assembly+prep_brain)已在树且冻结可用」——组件在树为真,但该链路**不在生产路径**((DecideAdapter→prep_brain.decide→_select) 全链无生产调用者);②「重构实体=替换 _select 的委托」——替换 _select 对生产行为零影响;config 切 strategy_id 之所以即换核,恰因生产消费点是 cw_screen_prep 的 `match.strategy`(L1193),与 _select 无关。④-1 L537「分歧实质是现役管线为步级单动作(**Decision.ops 单元素**)」同病:生产的步级单动作形态由 cw_screen_prep 直调单动作接口承载,Decision.ops=(op,) 单元素(prep_brain.py L244-245 亲验)是**离线/测试装配路径**的形态——把生产形态归因到错误载体。
- **连带影响**:R189-2「改造①prep_brain._select/策略注册面」与改造件①②(Decision.ops/适配器/绑定表)的「生产」定性失据(见症2/症3 连带);自引输入 SIM_CONSUMPTION_MAP L17 本已列明 cw_screen_prep:1193,1351 调用面,设计批未对「哪条链在生产」做消费者核验。
- **修法建议**:R189-0 重构实体改述=「生产消费点=cw_screen_prep 直调的 `match.strategy.decide_prep_screen`;装配链(decision_assembly.DecideAdapter→prep_brain)系离线/测试路径,其序列化改造件定性降级或补『接线进生产』的显式批件」;④-1「现役管线为步级单动作」的载体改指 cw_screen_prep 消费段(改造件④本体)。

### 症2(中高)R189-6 步1 验收判据对 prep 线改造件零检出力;④-5「适配器零漂移门」防线在 prep 域不可达

- **三元组**:(IMPL_DESIGN.md L611(步1 验收=「零漂移门(现役核 vs 现役核包长度 1 适配器,同 seed 同池同注册表视图 **SimResult.ledger** 逐位相等,SIM_CONSUMPTION_MAP ③-2)+流程侧零感知+sim/checks 契约锁(序列形状/截断不变式)」)+L556(④-5「prep 域正确性防线=契约锁+**适配器零漂移门**+实机,不在 sim A/B 辖内」);检验式=SIM_CONSUMPTION_MAP Q1(§6.4-R 自引输入)「decide_prep_screen 在 sim/ 零调用」+sim 三消费点亲验(engine_p1.py:937/cw_replay.py:240/checks/decision_v2.py:177 全部=decide_shop_screen)+症1 拓扑证据;结果=**sim 无任何通道驱动 prep 线/适配器/Decision**——SimResult.ledger 与 sim/checks 契约锁均不覆盖步1 改造件①②④(Decision.ops 多元素化/长度 1 适配器/cw_screen_prep 序列化),零漂移门对这些组件**必绿或不可执行**;④-5 声称的 prep 域防线第二腿「适配器零漂移门」无 sim 载体,与同节自引的 Q1 结论直接矛盾(R14-2 定性过的必绿锚病在迁移序验收面的形态)。
- **实质**:步1 真正的验收对象(prep 线序列化:生产消费段行为不变+适配器等价)落在三件判据的覆盖域之外;「流程侧零感知」被断言但无可执行载体(未指定测试/回放对拍)。SIM_CONSUMPTION_MAP ③-2 的零漂移门原文语境=商店路径换核 A/B(其适配器对象=商店线),§6.4-R 把它平移为 prep 线接线批的门,载体错置。
- **修法建议**:步1 验收拆两域——sim 可观测面(商店线,零漂移门辖域显式收窄到此)+prep 线可执行门(cw_screen_prep 消费契约不变的生产侧回归测试,或离线 prep 帧经适配器路径的决策等价对拍);④-5 防线改「契约锁+**prep 线等价门(生产/离线载体)**+实机」,删「适配器零漂移门」或补其可达载体。

### 症3(中)④-1 改造件①(Decision 多元素化)与契约 §1 形状裁决正面冲突,未按契约「回 v2 改版」通道处置亦未给豁免论证(特别提示面)

- **三元组**:(IMPL_DESIGN.md L538(改造件①「`Decision.ops` 多元素化+执行侧逐 op 回放绑定表(现绑定表单键,decision_assembly.py 批时快照=L200-201)」)+L537(④-1 依据句自称「零翻案……须改造的是接线不是设计」);检验式=CONTRACT_SERIES_DECISION.md L36-40 亲读(「形状裁决:生产接口=裸 list……`Decision/AtomOp` 层**不进生产接口**——DirectorV2 引擎退役后它仅存 sim/离线驱动用途……**若流程侧重构需要 Decision 形状,回本契约改版,禁静默双轨**」);结果=改造件①把 Decision 形状扩入序列化接线(多元素 ops+多键绑定表),文档既未呈报契约 v2 提案、也未论证「Decision 属接口外内层、不受该条款辖」——按冻结契约读=须回 v2,按文档读=缺豁免论证,两读均无着落)。
- **必要性称重**(任务书特别提示的回应):结合症1 拓扑——生产消费段(cw_screen_prep)按契约应消费裸 `list[PrepAction]`;Decision 多元素化实际只服务离线/测试装配路径(该路径非生产)。即:**生产序列化不依赖改造件①**;它要么应降级为「离线装配路径序列化(非生产受牽面)」并同步解除 R189-0 的『生产管线』定性,要么(若坚持其生产地位)按契约 L40 走 v2 呈报。现文本把它列为「序列化的全部受牽面」第一件并排进步1,两不相靠=契约自己预警过的「静默双轨」悬置形态。
- **备注**:绑定表单键锚本身属实(decision_assembly.py L200-201 亲读:`self._binding[decision.ops[0].op_key] = action`)——锚无错,错在与契约裁决的处置通道。契约本身不立案为缺陷(用户裁决件);立案对象=文档未按契约通道处置。

### 症4(中低)「④-4」标签两处互斥指派:R189-6 步4 引「④-4 结构签名」,而分歧单一源与登记节的 ④-4=流程锚清单

- **三元组**:(IMPL_DESIGN.md L614(步4「……④-3 新建四函数位/**④-4 结构签名**/修复池落点表按 R189-5……」);检验式=BATCH0_RESLICE_INPUT.md ④ L136-140 亲读(④-4=「流程锚-待重切清单(不立案为缺陷,2026-09-03 辖域裁定)」)+design_telemetry.md R189 节 L2480 亲读(「④-4 系流程锚清单不属裁决项,按对账底稿辖域裁定处置」);结果=同一编号「④-4」在 §6.4-R 步4=「结构签名」、在分歧清单单一源与登记节=「流程锚清单」,互斥;且 IMPL_DESIGN 正文内 R189-1「四分歧裁决」跳过 ④-4 **零申报**(申报只活在 telemetry 登记节,设计正文读者按「分歧清单单一源=BATCH0 ④」追索会找到错误的 ④-4 内容;R189-4 结构签名草案自身也未声明对应任何 ④ 项)。
- **修法建议**:步4「④-4 结构签名」改「R189-4 结构签名」;R189-1 头部补一句「④-4=流程锚清单非裁决项,处置见 telemetry R189 节」的正文内申报。

### 症5(低)④-5「decision_assembly.py L95-148 的 GameState 映射」锚实体错指——该段映射产物是 Snapshot,GameState 化在 decision_v2/adapter.py

- **三元组**:(IMPL_DESIGN.md L556(「其投影源亦=prep_obs_frame(经 decision_assembly.py 批时快照 L95-148 的 **GameState 映射**)」);检验式=decision_assembly.py L95-148 亲读(=`snapshot_from_obs`,签名 `PrepObservation → Snapshot`,返回 contracts 层 Snapshot 数据类)+decision/decision_v2/adapter.py L94-117 亲读(`_anchor_state`/`decision_state`,Snapshot→kernel GameState);结果=L95-148 不是 GameState 映射——obs→Snapshot 与 Snapshot→GameState 两层映射被并作一层且实体名错指)。
- **语义影响**:「单一源=黑板」结论不受影响(链路方向描述正确),属锚实体命名错账;但按 R74-1/R76-1 载体链的精确性标准(GameState 生命周期曾是裁决承重点),输入面权威句的映射层名不应错。

## ③ 流程锚-豁免清单(不计数,辖域裁定 2026-09-03)

| 锚 | 现树核验 | 处置 |
|---|---|---|
| IMPL_DESIGN L569/R92-4「engine_p1 利息行=L752」 | 亲跑=利息行现位 **L757**(`'interest': min(_icap, st.gold // 10)`,L757 亲读;不含 flat 分量的语义主张与现码一致) | 流程锚-豁免(漂移不立案) |
| R189-1 ⑤「engine_p1.py L937 系商店线/L1027 截断」 | 亲验 L937=`decide_shop_screen`、L1027=RefreshShop break-redecide——**锚在位无漂移**,仅申报辖域归属 | 流程锚-豁免 |
| 契约 §7/改造件④「cw_screen_prep.py L1191-1215 备战五段决策段」 | 亲验 L1193 直调 decide_prep_screen 在位(段界行号未逐行核) | 流程锚-豁免 |
| L85 R76-2 标内 engine_p1 L762-766 等 sim 基建族锚 | 未逐个复核(R188 已按豁免处置) | 流程锚-豁免 |

(策略器侧锚本轮全部亲跑:decision_assembly L95-148/L200-201、prep_brain L180-198/L201-211/L244-245、cw_line_switch L143-151/L154-175/L168-174、cw_plane_table L50/L70、cw_strategy 备战线/商店线契约段、`grep stop_flag src/`=0、`grep cap_sup src/`=0、cw_investments L242/L110、strategies/ 注册桥、cw_strategy_manager 校验机制、cw_replay L239-240、sim/checks/decision_v2.py 存在性——除入症者外全部与文档断言一致。)

## ④ 冻结残余对账节

- 冻结残余口径=**11 项**(LEMMAS 文末冻结残余清单 9 格中第 7 项经 R182 销账标→活 8 项;telemetry 侧第 10/11/12 项口径,经 R184「#11 并入申报」处置后 telemetry 承 3 项;最新 R188/R189 节均按 11 项申报,亲读在案)。
- 本轮 5 症逐条对账:症1/2/4/5 落迁移序拓扑/验收载体/引用标签/锚实体面,症3 落契约 v1 处置通道(契约=用户裁决件,非冻结族六面装置;立案对象=文档侧未处置,非契约缺陷)——**无一触及 D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面验证装置**,与 11 项冻结残余零重叠、零重复立案;未攻击冻结族、未新增验证装置提案(症2 修法建议的「prep 线等价门」系迁移序接线批验收载体建议,非度量面验证装置——若判为装置面扩张,可降级为「步1 验收判据辖域申报修正」处理,症2 的立案本体是必绿锚错账不受影响)。

## ⑤ 清洁门申报

- **本轮新症总数=5**(中高 2:症1/症2;中 1:症3;中低 1:症4;低 1:症5)。
- 无凑数立案:症5(低)系锚实体错指,按 R74-1/R76-1 载体精确性标准独立成症;无零新症压真症:症1/症2 系 §6.4-R 主干断言与现树/自引输入的直接冲突,证据全部亲跑。
- 申报:计划成形后为冻结对账与 ④-2/④-4 呈报核验读了 design_telemetry R188/R189 节(登记节,纪律允许时点后);IMPL_ADV_*.md 全程未读(本轮即 §6.4-R 首轮攻击,glob 亲验无 IMPL_ADV_R189.md)。
- 批时快照:2026-09-03 后现树(git 零触,只读);所有行号=本轮亲跑亲读,文档行号以 681 行现行版为准。
