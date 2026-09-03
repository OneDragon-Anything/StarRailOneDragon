# IMPL_ADV_R192 · 对抗审查报告(无锚轮,自选攻击面)

> 攻击者=全新视角;对象=redesign 四文档正文(IMPL_DESIGN.md / design_economy.md / design_latch.md / design_telemetry.md,主攻面=§6.4-R 及 R189/R190/R191 修注链)+ IMPL_FIX_LEMMAS.md 冻结清单对账;参照件=CONTRACT_SERIES_DECISION.md(契约 v1 用户冻结件;不一致可立案,契约本身不立案)。
> 纪律:计划成形前未读 IMPL_ADV_*.md 与 telemetry 文末登记节;计划成形后为修注链专项读了 IMPL_ADV_R190/R191 与 telemetry R189/R190/R191 登记节(申报)。冻结族(度量家族五装置+cap 消费参数化度量面验证装置)禁攻击禁新增装置;流程侧代码锚(operations/、sim/engine_p1.py)豁免;每症=三元组(文档行号+检验式+结果),代码引用现树亲验,数值/词表锚直调来源复核。

## ① 攻击计划(计划成形时点:通读 IMPL_DESIGN 全文 681 行+core_swap 四输入件+契约 v1 全文+现树策略器侧锚点亲验之后)

自选攻击面=**R191 修复批刚落地的修注链自身**与**R189-4 批1 结构签名的规格自洽**:

1. **冻结基线条款 vs 适配器形态钉死**(主攻):§4.1「decision_v2 保持冻结基线:不改一行」与 §6.4-R ④-2 ②「禁改」两处冻结条款,对照 R191 收编标(步1「现役核 decide_prep_screen 原位返回 [action],DecisionV2Strategy 本体改返回形态」)——本体改形是否=改基线的正面冲突;契约 §1「包一层长度 1 适配器」字面与原位改本体的偏离;现树 strategy.py 亲验落码态。
2. **R189-4 帧稳定截断判的词表辖域**:判所枚举动作名对照现树 `kernel/cw_prep_actions.py` PrepAction 族与 `kernel/cw_state.py` Action 族——备战发射器输出词表(=PrepAction 族,契约 §0/§1 钉死)能否被该判覆盖;判内是否存在备战词表中零存在的死条款;契约 §3「增补条目须回契约改版(v1→v2),禁只改代码」约束下的批1 可落码性。
3. **R189-6 步1 规格文本内部自洽**(R191 钉死后专项):步1 正文/尾注的改造件编号引用与 R190 重编号表、R191 收编标的互引一致性;R191 症2 修复的 grep 模式是否存在复合引用盲区。
4. **修注链引注失准扫描**(计划成形后执行):IMPL_ADV_R190/R191 原文与 telemetry R189/R190/R191 登记节核对——修注声明与正文他处矛盾、「已裁」声明辖域、登记三元组可复算性。
5. **冻结残余对账**:LEMMAS 文末冻结残余清单逐项清点(9 格第 7 项 R182 销账→活 8)+telemetry 侧 3 项=11,与本轮新症零重复核验。

未选面申报:④-2 分臂裁决正文(R189 已显式呈报冻结冲突,处理合规);R189-3 独立前置批论证;冻结族六装置全部未触。

## ② 新症逐条

### 症1(中高)R189-4 帧稳定截断判的词表辖域错配——判枚举的是商店线动作,新核备战发射器的 PrepAction 输出词表大半无截断分类,批1 结构签名照此落码即触发「须回契约 v2 改版」或产生无判动作

- **三元组**:(IMPL_DESIGN.md L581 `truncate_frame_stable(actions)`+L584 判清单「BuyCard(商店)/LevelUp/LevelUpShop=可续;拖拽族(DeployMove/SellBench/SellDeployed/装备拖拽)=条件续;RefreshShop=截断点;CompTransaction=截断点;合成触发=『可能触发合成』的买牌后截断;出战=序列终点」;检验式=①契约 v1 §0/§1(CONTRACT_SERIES_DECISION.md L19-21、L30)钉死备战线词表=`kernel/cw_prep_actions.PrepAction` 族、返回 `list[PrepAction]`;②现树 `grep '^class' kernel/cw_prep_actions.py` 亲跑=具体动作类 17 个:DeferSpheres/BailToOuter/ClickSpheres/OpenBox/OpenTome/PickBoxCard/SellBench/SellDeployed/DeployMove/LevelUp/EnsureShopOpen/EnsureShopClosed/OpenShop/StartBattle/RunBuyPhase/RunDeploy/RunEquip;③`grep '^class' kernel/cw_state.py` 亲跑=BuyCard/LevelUpShop/RefreshShop/CompTransaction/SwapDeploy 系商店线 Action 族成员,**不在 PrepAction 词表**;④现役核规则序亲读(decision_v2/strategy.py L791-797 docstring)=备战发射的实际词表=PickBoxCard/OpenBox/ClickSpheres/腾席链(deploy/卖/升级/DeferSpheres)/Run* 组合(买→部署→装备→出战),零 BuyCard/RefreshShop 直发;结果=**错配成立**)。
- **论证**:R189-4 的 `_emit` 是**备战线**发射器(返回 list[PrepAction]),其截断判却照抄契约 §3 初始枚举全表——该表中备战词表可发射的动作仅 5 类(LevelUp/SellBench/SellDeployed/DeployMove/StartBattle);①判内 6 个词条(BuyCard(商店)/LevelUpShop/RefreshShop/CompTransaction/合成触发=买牌后/装备拖拽)在 PrepAction 词表**零存在**,对备战发射器是死条款——其中「BuyCard(商店)」的「(商店)」限定词本身已自证词表归属,设计批照抄未察;②备战词表 17 类中 **12 类零截断分类**(DeferSpheres/BailToOuter/ClickSpheres/OpenBox/OpenTome/PickBoxCard/EnsureShopOpen/EnsureShopClosed/OpenShop/RunBuyPhase/RunDeploy/RunEquip)——OpenBox(开箱进 overlay)/PickBoxCard(overlay 选卡)/ClickSpheres(球消失)/OpenShop(开商店界面)均改变画面状态,按契约 §2 帧稳定域「能否静态推出」逐动作判的语义**必须**有分类,现全部无判;Run* 组合(现役主流程买→部署→装备→出战的承载形态)同样无判。契约 §3 末句「发射器实现期增补条目须回契约改版(v1→v2),禁只改代码」+IMPL_DESIGN L584 自述同款纪律 ⇒ 批1 落码照 R189-4 结构签名实现 `truncate_frame_stable`,要么立即回契约 v2 补 12 类条目(设计未列此为批1 前置/检查点),要么落出无判动作(违契约纪律)——「落码批照此派单」(L571)的可执行性在签名本体上断裂。telemetry R189 节 L2482 对 R189-4 的登记自称「帧稳定截断发射器=契约 §3 初始枚举…无『实现者自造方向』缺口」,与词表事实不符。
- **修法方向**(供裁决):R189-4 判清单按 PrepAction 词表重写——12 无判类逐类定截断/可续(可按契约 §2 语义先给设计裁定,再按 §3 纪律回契约 v2 补条目,把「契约 v2 改版」显式列为批1 检查点);6 个商店线死词条移出备战发射器判(或显式标注「商店线条款,备战发射器不辖」);同步改 telemetry R189 节登记句。

### 症2(中)R191 收编标「适配器形态钉死=DecisionV2Strategy 本体改返回形态」与 §4.1「不改一行」/④-2 ②「禁改」两处冻结基线条款正面冲突,未回扫未打标;且偏离契约 §1「包一层长度 1 适配器」字面未呈报——「已裁」声明与正文他处矛盾

- **三元组**:(IMPL_DESIGN.md L611 R191 收编标「长度 1 适配器形态=**现役核 decide_prep_screen 原位返回 [action]**(DecisionV2Strategy 本体改返回形态,非包装子类;理由=现役核即 A/B 基线臂,包装层徒增等价门载体)」vs L378(§4.1)「**decision_v2 保持冻结基线:不改一行**;其被测体身份=A/B 的 legacy 臂+判据族分栈锚」+L542(④-2 ②)「现役臂(decision_v2)=冻结基线……§4.1『decision_v2 保持冻结基线:不改一行』**禁改**」;检验式=①grep 'R189|R190|R191' IMPL_DESIGN.md L1-L400 亲跑=§4.1/④-2 两处冻结条款**零修注零 supersede 标**(命中仅 L3/L122 头部与 entry 行);②现树亲验=decision_v2/strategy.py L778-820 `decide_prep_screen` 已改 `-> list` 且 L820 `return [step]   # 长度 1 适配器(dd-020 契约 §1)`+L775-776 兼容入口解包+prep_brain.py L211-220 `_select` 按单元素批消费改造——decision_v2 文件已被改动(超出设计批「零源码」面,系另批落码,但设计权威句仍冲突);③CONTRACT_SERIES_DECISION.md L34-35 亲读=「**现役单动作核包一层长度 1 序列的适配器**」——契约字面=包装形态,R191 裁决=原位改本体,非「包一层(适配器)」;结果=**三边冲突成立**)。
- **论证**:①文档内冲突:L611 裁决令改 DecisionV2Strategy 本体,L378「不改一行」与 L542「禁改」仍以无限定形态并存——按本文档自立纪律(先例=④-2 对冻结冲突的「显式呈报不默改任一边」模式、R32-中① supersede 纪律),冲突须打标或呈报,R191 修注链(含其泛化扫,扫面=「装配/assemble/接线/改造件④」)**未回扫冻结基线条款面**;②裁决理由不对称:④-2 用「改冻结基线臂,违 §4.1」否决编排者倾向,R191 用「包装层徒增等价门载体」的工程偏好理由改同一臂——同一冻结条款在两处承受不同强度的否决标准,无辖域说明;③契约字面偏离未呈报:契约 §1 冻结文字是「包一层…适配器」,原位改本体是另一种机制(行为等价可辩护,但按契约 §6「任何条款改动动版本号,禁静默改义」的版本化纪律,落法与冻结文字的不同应显式呈报——现树 docstring L786 自行重释为「包一层长度 1 序列」,设计文档零呈报)。呈报缺口使「基线臂行为等价」的全部重量压在步1 两个等价门上,而冻结条款的文档态与代码态已不一致。
- **修法方向**:在 L378 与 L542 就地补 supersede/辖域标(「接口形态迁移例外:契约 v1 §1 迁移期适配授权,行为等价门=步1 两域门承载;参数形态禁改保持」),并在 telemetry R191 节补呈报(契约字面「包一层」vs 原位改本体的落法偏差+等价门承接声明)。

### 症3(中低)L611 步1 尾注「(④-1 改造件①②④)」未随 R190 重编号同步——R190 症4/R191 症2 标签互斥病类第三犯,R191 修复的 grep 模式存在复合引用盲区

- **三元组**:(IMPL_DESIGN.md L611 步1 正文「长度 1 适配器+Decision.ops 多元素化+绑定表多元素化+生产备战消费段序列化(**④-1 改造件①②④**)」+L538 R190 重编号权威表「**①**=现役单动作核包长度 1 序列的适配器(原②)、**②**=发射器帧稳定截断(原③)、**③**=生产备战消费段序列化(原④)、**④**=sim 侧两个离线消费点同步(原⑤)」+L611 同行 R190 修注①「本步=R190 重编号①(长度 1 适配器)+③(生产备战消费段序列化)」+L538 R191 收编标(原⑤改判「换核受牿面…非序列化本批必动」);检验式=①按 R190 重编号表读「①②④」={适配器,发射器帧稳定截断,sim 侧两消费点同步}——②属批1 步4(R189-4 结构签名)、④已被 R191 改判非本批必动,与同行 R190 修注钉定的「本步=①+③」矛盾;②按 R189 原编号读「①②④」={Decision.ops 多元素化+绑定表,适配器,生产消费段}——含已被 R190 明文移出本步的 Decision.ops 件;③grep '改造件④' IMPL_DESIGN.md 亲跑=命中仅 L532/L537(R191 改读括注内合法史档引用),与 telemetry R191 节 L2560 的清点一致——但复合引用「改造件①②④」**不含字面「改造件④」**,逃出该 grep 模式;结果=**两种读法均与同批修注矛盾,且 R191 症2 的清点检验式对此构造性失明**)。
- **论证**:这是「编号契约重编号后残留旧引用」病类的第三 instance(R190 症4 修「④-4 结构签名」错指→R191 症2 修「改造件④本体」两处→本条复合引用仍悬空)。R191 泛化扫的检验式是字面 grep,复合编号引用是其天然盲区;修注链自家纪律(重编号批须全量回扫编号引用)两轮未兑现全量。修法=L611 尾注就地补限定(「④-1 改造件①②④(原编号;按 R190 重编号=①+③,②④ 非本步)」),泛化扫检验式补复合引用模式(`改造件[①②③④]` 字符类)。

### 观察项(不计数,禁凑数纪律下如实降级)

- **OBS-1(中低,挂批1 派单前钉死)**:④-3 表 should_switch 行裁决「复用比较器(新核侧消费;参数归宿按 ④-2 分臂=provisional)」与免做⑤「should_switch_e 数学比较器…文件本体零改动」合读——现树比较器签名 `should_switch_e(..., registry=None)`(cw_line_switch.py L154-162 亲验)只吃 registry 实值(L168-174 消费 `reg.line_switch_theta` 等三个注入),provisional【拟】槽位值(缺省 None fail-closed)无入口进该函数。新核臂消费 provisional 符号的**调用形态零规格**:比较器加参数注入重载?新核侧自组比较式+should_switch_e 作对拍锚?两读都合法但形态不同(fail-closed 键 `θ_unavailable` 的挂点随之不同)——R6-5「实现者遇缺输入自造方向」病类的批间形态,建议批1 派单前钉死。
- **正面核实(攻击未中,如实记录)**:R189-0 R190/R191 修注的全部策略器侧代码锚现树复验为真——DecideAdapter 唯一定义=decision_assembly.py L153、绑定表单键 L200-201(`self._binding[decision.ops[0].op_key] = action` 亲读)、src 内零实例化消费(adapter.py/prep_brain.py 仅 docstring 提及,唯一外部消费=sr-od-test/test_cw_expected_state.py);prep_brain assemble L180-198/_select L201-220/decide L223;映射两层锚(decision_assembly.snapshot_from_obs L95 起/adapter decision_state);cw_line_switch should_switch_e L154-175/switch_allowed L143-151/registry 消费 L168-174;cw_plane_table PLANE_FALLBACK_PRIORS L50/schedule_of L70;R191 症1 修注(步3 statefn 缝挂 mandate_v1 内部)与 telemetry L2532 勘误标互指在位;R191 症2 直改(L532/L537「改造件③本体;R191 编号统一」)在位;R191 症3 裁决补记(L562)在位;BATCH0 ④-1..④-5 分歧编号与 R189-1 裁决覆盖对账一致(④-4=流程锚清单申报句在 L534 在位)。

## ③ 流程锚-豁免清单(不计数,2026-09-03 辖域调整)

| 锚 | 批时快照 | 现树(亲跑) | 处置 |
|---|---|---|---|
| cw_screen_prep.py decide_prep_screen 直调两处 | L1193/L1351 | L1227/L1414 | 流程锚-豁免(内容锚在位;R190 顺手项已申报漂移族) |
| cw_screen_prep.py import 段(committed_from/drive_intention) | L1171-1174 | L1203-1205 | 流程锚-豁免 |
| cw_screen_prep.py 备战五段决策段 | L1191-1215 | ~L1225 起 | 流程锚-豁免(序列消费段序列化已部分在树,属流程侧重构不立案) |
| engine_p1.py 利息行 | L752→L757→L768 | L768 `min(_icap, st.gold // 10) + _flat` 亲读 | 流程锚-豁免;flat 半边已兑现申报与现树一致 |
| engine_p1.py L937/L1027(商店线消费/截断) | 2026-09-03 | 未逐行复核(SIM_CONSUMPTION_MAP 单一源) | 流程锚-豁免 |
| sim/cw_replay.py L239-240 | 2026-09-03 | L240 在位 | 流程锚-豁免 |
| cw_plane_table.py schedule_of 消费段 | L70 | 消费段现位 L75-94 | 流程锚-豁免(L50 常量锚恰在位) |

策略器侧锚状态申报:本轮全部亲跑(见 OBS-1 正面核实段),除入症者外零漂移立案。

## ④ 冻结残余对账(口径=11 项,零重复)

- **LEMMAS 侧 8 项**(IMPL_FIX_LEMMAS.md 文末冻结残余清单 L3370-3382 亲读:9 格中第 7 项经 R182 批销账标→活 8):第 1-6 项(R66 七项之六:C_int 双向不对称/有效性门错位/帧统计单元/R65-1 落位缺口/N_gate 版本锚/R65-4 协变量前提)+第 8 项(§5.2 窗口高侧预算未随 cap_sup 化)+第 9 项(F7/M4 行 λ̂_U~0.3 v3.3 前旧坐标)。
- **telemetry 侧 3 项**:第 10 项(R98)/第 11 项(R115)/第 12 项(R162)——口径经 R190/R191 登记节申报一致(「LEMMAS 8+telemetry 3=11」三节复述亲读在案)。
- 本轮三症落点=批1 结构签名词表辖域(症1)/冻结基线条款与修注链冲突(症2)/编号引用同步(症3),均不属于冻结六装置族(D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面验证装置)——症2 触及「冻结基线臂」条款系 §4.1 A/B 对照纪律条款,非度量家族装置,且立案对象=文档未回扫未呈报,非攻击装置本体;未新增任何验证装置类提案(症1 修法方向系契约条目补全建议,载体=契约 v2 版本化通道,非新装置)。零重复立案。

## ⑤ 清洁门申报

- **本轮新症总数=3**(症1 中高/症2 中/症3 中低),另观察 1 项(OBS-1)不计数。无锚轮自选面;全部三症检验式均含现树亲跑/亲读(词表类锚=注册表/词表源文件直调,非被审方转述),无凭记忆行号,无仅公式内部自洽的验证。
- 无凑数:三症各自独立成立(词表辖域/冻结条款冲突/编号残留),证据链最弱一环=症2 的「行为等价可辩护」仅降其 severity 不消其冲突;无压症:症1 系现行权威迁移序批1 签名的可落码性断裂,建议优先排裁(批1 派单前须先裁 12 无判类的截断分类+契约 v2 通道)。
- 申报:计划成形后读了 IMPL_ADV_R190.md/IMPL_ADV_R191.md 与 design_telemetry.md R189/R190/R191 登记节(L2471-2576),用于修注链专项与冻结对账;批时快照=2026-09-03 后现树(只读);文件面=除本文件外零写入、零源码、零 git。
