# 第 3 轮对抗审(核一·无前提攻击):PickPlanner/PickEquip 两相上报清偿

> 攻击对象 = 本目录 design.md / landing.md 现稿(README 仅上下文)。权威源 = action_ops.md / action_exec.md / op-layer.md / fields.md / logic-updates/pick-planner.md / planner.md / equip_pick.md / screens/README.md §5.5 + 代码实况 + 测试实况。attack.md / attack2.md 仅作历轮清偿核对,不锚定。全部引用行号 = 本轮实读现盘。

## ① 总判

**需修订(不可定稿)**:发现 6 条,阻塞 2 条。方案主体(单相化契约、逐屏差异、时序等价论证、分支类型实码口径、joy 收口序)经逐条对码核验成立,历轮 attack/attack2 的 7 项发现在现稿中均已真清偿;但 §2.2 消费点迁移总表在本轮新事实(joy rider 批已提交,带出 `test_cw_gain_chain.py` 的 `EVIDENCE_OVERLAY_CLOSED` 消费面)下不完备,且 `logic-updates/pick-planner.md` 正本更新条目口径过窄(§3/§5/文件头的两相表述不在清单与兜底 grep 覆盖内)。修毕 F1/F2 即可收敛。

## ② 逐条发现

### F1 [阻塞] design §2.2 消费点迁移总表遗漏 `test_cw_gain_chain.py` 的 `EVIDENCE_OVERLAY_CLOSED` 消费面(import + 10 调用,已提交)

- **位置**:design.md §2.2 表「`EVIDENCE_OVERLAY_CLOSED`(pick_planner.py 自持)」行;landing.md 3.2 文件面/验收凭据。
- **问题**:全仓 grep(本轮实测)显示 `sr-od-test/test/sr_od/application/currency_war/test_cw_gain_chain.py:40-43` `from ...pick_planner import (EVIDENCE_OVERLAY_CLOSED, report_action_pick_planner_param)`,并以 `evidence=EVIDENCE_OVERLAY_CLOSED` 调用 **10 处**(:615/:633/:646/:654/:661/:684/:713/:732/:757/:782,joy rider 授予测试族)。该消费面随 commit 14dd40977「欢愉契约条件分支 rider 建模」**已入库**(attack2 复核时点在 joy 批提交之前,其「src+test 无遗漏」结论因此过期)。后果三连:①3.2 删 `evidence` 参数后这 10 处调用直接 TypeError → 「L1 全绿含其测试」不可达;②design 验收锚 3「`EVIDENCE_OVERLAY_CLOSED` 全域 grep 零命中(范围含 sr-od-test)」永红;③§2.2 表把 planner 侧消费点枚举为「`cw_screen_yinlang.py` import+调用;`test_cw_yinlang_phase32.py`(10+ 处)」,worker 按表执行改完两文件后 grep 仍剩一整文件,停手令。landing 3.2 文件面「受影响测试(含 test_cw_yinlang_phase32.py)」未点名该文件。
- **权威源证据**:test_cw_gain_chain.py :40-43/:615-782(本轮实读);`git log --oneline -- .../pick_planner.py` 首行 = 14dd40977;action_ops.md §1 禁止清单 + design §3 锚 3。
- **建议修法**:§2.2 该行现消费点补「`test_cw_gain_chain.py`(joy rider 测试族,import+10 调用,commit 14dd40977 已入库)」;landing 3.2 文件面与验收凭据点名该文件(改写 = 删 `evidence=` kwarg,断言本体即 rider 行为测试,测试面归属按 F4 澄清)。

### F2 [阻塞] 正本更新清单对 `logic-updates/pick-planner.md` 条目口径过窄:§3 :23 `_confirm_pending` 步、§5 :33 重入裁决表述、文件头 :3「两相上报」均不在清单与兜底 grep 覆盖内;且 :14 锚内容与描述错位

- **位置**:landing.md「正本更新清单」第 7 条:「过期『单一定义在 pick_invest』句修正(:14/:37)+ evidence 分相表述清除」。
- **问题**:实读该文件,「单一定义在 pick_invest」句**仅在 :37**;:14 是「落地相(evidence = `EVIDENCE_OVERLAY_CLOSED`…)」分相表述——锚内容与描述错位(attack.md F2 同款形态)。更重要的是清除面不全:文件头 :3「**两相上报**(银狼升星记账批 2026-09-20…设计 = changes/…design.md §2.2)」、§2 :13 发射相 bullet、§3 转移规则 :23「`op._confirm_pending = True`」整步、§5 :33「确认未落地不重试不判效——下一轮重入入口观察裁决」、§7 :41「两相语义 = pick 族证据闩形态」——单相化后全部失真,但既不含常量字面量(兜底 grep 一段抓不到)、也不在 action_ops §4.5/action_exec §2(兜底 grep 二段的限定范围),按清单字面执行 = 永不清除,违反 AGENTS §9「正本必须自足、与代码现状一致」与末阶段判据「正本与实现一致」。另 :3 与 §9 引用 `changes/` 设计稿,属正本禁引(末阶段「禁引纪律自查」泛覆盖,但宜点名)。
- **权威源证据**:logic-updates/pick-planner.md :3/:13/:23/:33/:37/:41(本轮实读);landing.md 正本更新清单第 7 条 + 兜底条;docs/develop 下 AGENTS.md §9 铁律。
- **建议修法**:条目改为「全篇两相/重入裁决/`_confirm_pending` 表述清除(文件头 :3、§2 :13-14、§3 :23、§5 :33、§6 符号锚 :37、§7 :41;『单一定义在 pick_invest』句在 :37)+ §3 :22-24 转移规则重写为单相时点 + changes/ 引用(:3/:49)摘除」,或把兜底 grep 二段范围扩为「action_ops §4.5、action_exec §2、logic-updates/pick-planner.md、screens/planner.md、screens/equip_pick.md」。

### F3 [建议] `_pick_pending`/`_pending_pick` 的测试消费面遗漏 `test_cw_screen_two_node_family.py` :296-348

- **位置**:design.md §2.2 表「`_pick_pending`/`_pending_pick`(equip_pick)| 本文件读写点 | 删」;landing.md 3.1 文件面。
- **问题**:`test_cw_screen_two_node_family.py::test_equip_act_decides_from_container_and_round_wait` 对 `CwScreenEquipPick` 断言 `rs.result == WAIT`(:346)与 `op._pick_pending is True`(:348)——3.1 删属性 + act 改 `round_success` 后双断言必红。§2.2 表声明消费点 =「本文件读写点」是事实性不完备(误导 worker 以为测试面只剩 t60 EQUIP_EVIDENCE);landing 3.1 文件面「受影响测试(含…)」未点名。可由通用工程门跑测试发现,故降为建议。
- **权威源证据**:test_cw_screen_two_node_family.py :296-348(本轮实读);cw_screen_equip_pick.py :74/:79/:125-129/:169/:180。
- **建议修法**:§2.2 该行现消费点补「`test_cw_screen_two_node_family.py` equip act 测试(:346/:348)」;landing 3.1 文件面点名并声明改写为「派发即 round_success + 零重入裁决标志」断言。

### F4 [建议] joy rider「未提交改动在盘」申报事实已过期(rider 已随 commit 14dd40977 提交);joy 批测试面的改写归属与「rider 分支行为测试归 joy 批」边界未澄清

- **位置**:design.md §2.1 planner 条「joy rider 在盘申报(attack2 F4 事实化):…已以未提交改动在盘」、§2.3 收口序①「joy 批先提交其 rider」;landing.md 3.2 依赖。
- **问题**:git 实况:`pick_planner.py` 工作树干净,`_grant_joy_conditional`(+rng)与 `test_cw_gain_chain.py` evidence 调用均已入库(14dd40977)。收口序①实际已满足——设计前提陈述失真(方向无害:依赖已达成,比「待提交」更安全)。但衍生一点:3.2 必须机械改写 joy 批的 `test_cw_gain_chain.py`(删 `evidence=` kwarg,见 F1),与「rider 分支行为测试归 joy 批验收面、本批验收锚不含 rider 专项测试」的边界声明存在字面张力——宜显式声明「3.2 对该文件仅做调用签名机械改写,断言语义(rider 行为)不改不校验」。
- **权威源证据**:`git log` 14dd40977;`git status --short` 无 src 改动;pick_planner.py :94/:107-142(在盘即已提交形态)。
- **建议修法**:§2.1/§2.3/landing 3.2 依赖措辞改为「rider 已随 commit 14dd40977 提交(原『未提交在盘』申报截至本稿时点已过期);3.2 对 `test_cw_gain_chain.py` 仅删 `evidence` kwarg 机械改写,rider 行为测试归 joy 批验收面」。

### F5 [建议] cw_vocab 两个 param docstring 内「落地相/两相语义」措辞不在申报注释连带面,兜底 grep 亦不覆盖

- **位置**:landing.md 3.1「`CwActionPickEquipParam.norm_item` 字段注释改写(归一换源)+ `CwActionPickSupplyParam.norm_item` T-1 遗留过期注释顺手清」。
- **问题**:实读 cw_vocab.py:`CwActionPickSupplyParam` docstring :735-736「上报**落地相**按实际开出内容应用(…pick_supply **两相语义**)」、`CwActionPickEquipParam` docstring :910-911「上报**落地相**装备入账分支 = 入栏 + 获得后果链…(pick_equip **两相语义**)」——supply 句是 T-1 后本已失真、equip 句本批后失真,均无 `EVIDENCE_OVERLAY_CLOSED` 字面量(兜底 grep 一段抓不到),措辞范围又不属兜底二段的两文件。「norm_item 注释改写」括注「(归一换源)」收窄了口径,worker 只换函数名即视为完成 → 两相措辞存活。
- **权威源证据**:cw_vocab.py :733-736、:907-911(本轮实读)。
- **建议修法**:landing 3.1 该句扩为「两处 docstring 整段改写(norm_item 归一换源 + 落地相/两相语义措辞清为单相)」。

### F6 [建议] screens/README.md 正本更新仅点名 §5.5;§6 :138「单选族确认离开」行的即时上报枚举迁移后同样失真

- **位置**:landing.md 正本更新清单第 4 条「screens/README.md:§5.5 单选族表(两行上报形态更新)」。
- **问题**:README.md :109(§5.5 段落)「两相欠账(策划/装备屏现役)…迁移归后续批(外溢任务 T-5 在册)」确需更新 ✓;但 §6 总表 :138「单选族确认离开…投资两屏/补给/遭遇 = **派发确认链即 round_success 终结交回**(即时上报形态…)」——本批后策划/装备同入该形态,枚举不点名即不完整;该行无「两相/落地相/发射相」字样、无常量,两段兜底 grep 均抓不到。量级:枚举不完整而非错误陈述,建议级。
- **权威源证据**:screens/README.md :109/:138(本轮实读)。
- **建议修法**:清单第 4 条扩为「§5.5 两相欠账段 + §6 :138 即时上报枚举行」。

## ③ 全量同步复查结果表

| 复查面 | 结果 |
|---|---|
| design §1 ↔ §2 ↔ landing 三阶段边界 | ✓ 无遗漏无越界:§1.3 解决①②③与 §2.0/§2.1/§2.2 逐项对应;不解决面(upgrade 前置校验、classify_planner_leg、零写族 chosen 留守[op-layer §2.2 :78 支持]、equip 判据)与 landing「不含」声明一致;正本更新面全部回指 landing 清单。§1.3 之外未见未申报面(cw_vocab 两注释、模块头自述段均在 §2.2 表)——F5 属口径过窄非漏报文件 |
| 历轮(attack/attack2)发现清偿核对 | F1 action_exec :24 入清单 ✓(锚实存);F2 planner.md 五处锚全实存(:12/:24/:48-49/:55/:76)✓;F3 op-layer :33/:43/:96/§3 锚实存 ✓;F4 joy 收口序在稿 ✓(但事实陈述过期 → 本轮 F4);F5 分支类型口径与实码一致 ✓(classify_planner_leg 现役不产出 weaken,cw_events.py :1005-1008「弱化兜底档已退役…落步 4 unknown」逐字支持);F6 模块头三线例外自述段实存(cw_overlay_pick_action.py :19-24)且 3.2 归属正确 ✓;F7 cw_vocab :733 锚精确 ✓ |
| 关键主张依据对码 | §1.1 现状锚全部实存且如述(pick_planner.py :86-104 四分支、yinlang :204-222 证据闩、equip_pick :125-138、PickPlannerOp :408 置位、PickEquipOp 发射相 :609-615);§2.0 时序等价论证成立(旧落地相在同 op visit 内 round_wait 轮到达,期间无外循环观察介入 bench/front/back);§2.1 归一升级依据成立(equip_pick docstring :156-157「未锁态语义(仅泛用分支)」在册、`normalize_registry_equip_name` T-1 已建[cw_events.py :951]、注册表实数 158[实测 `len(EQUIPMENT_ROSTER)`=158]);§2.3 upgrade 重复应用论据与 `_apply_upgrade_transform` 实码一致(二次上报 count=0 → `planner_upgrade_source_missing`,档行不二次 +1)✓;增补 2 禁止清单第 4 条 =「判重/防重复保护」✓;增补 3 合规自查成立(`emit_overlay_confirm` 体内零 OCR[实读 :91-118],归一组装留画面 op)✓ |
| 正本清单条目节名/行号真实性 | action_ops §4.5 ✓;action_exec :24 ✓(且 supply 误列欠账由「supply 确认行复核」覆盖);op-layer :43(§1.2 欠账句)/:33(§1.1 枚举句)/:96(§3 注)/§3 节点循环行 :88 ✓;planner.md :12/:55/:76 ✓;equip_pick.md ✓;pick-planner.md **✗ :14 锚错位 + 清除面不全(F2)**;screens/README §5.5 ✓(**§6 :138 漏 → F6**) |
| 消费点迁移总表 vs 全仓 grep | `EVIDENCE_OVERLAY_CLOSED`:src 4 文件 ✓;t60 EQUIP_EVIDENCE(:40/:127/:218)✓;yinlang_phase32 import+10 调用 ✓;**test_cw_gain_chain.py import+10 调用 ✗ 遗漏(F1)**。`_pick_pending`/`_pending_pick`:equip_pick 本文件 ✓ + bookcard/expert_invite 同名异类型属彼屏(表已限定)✓ + **two_node_family :348 ✗ 遗漏(F3)**。`_confirm_pending`/`_pending_leg`/`_pick_param`:yinlang 本文件 + planner op :408 ✓;partner(:355)/fortune/deploy_not_full/wish_trial/bookcard 同名属彼屏 ✓ 无过度。`normalize_equip_name`:equip_pick 组装点(:47/:168)✓、本体与银狼域消费面不动 ✓、supply_node 已用 registry 入口 ✓。模块头三线例外段 ✓。cw_vocab 两处 ✓(措辞口径 → F5) |
| 规范遵循(action_ops §1 三条裁定 / op-layer §1.4) | 增补 2 ✓(点完即写、禁验证重试防重、重复应用风险按裁定接受);增补 3 ✓(零新增读屏,定位查找合法);op-layer §1.1 出口①形态对齐(派发即终结)✓;§2.2 chosen 留守边界不破 ✓;固定等待族口径(1.2s/pick 确认 0.6-1.2s)✓ |
| 分支类型实码口径 | equip(命中入栏+后果链 / '' 翻来源留证,含多命中 equip+'')/ upgrade(三态+档行,序 = 容器观察→档封顶→计数→变换→档行→级联)/ unknown(弱化词落此)/ unrouted 兜底 —— 与 pick_planner.py :95-104、:145-169、:172-274 逐分支一致 ✓ |

## ④ 试读结论(逐阶段)

- **3.1 worker**:能开工——pick_equip 单相语义、归一换源、文件面、判据均可执行;风险 = 按 §2.2 表以为测试面仅 t60 EQUIP_EVIDENCE,漏 two_node_family equip act 测试(F3),跑测试可兜住;norm_item 注释改写口径歧义(F5)。
- **3.2 worker**:能开工,单相语义与 rider 迁移挂点描述充分;但按现稿改完 yinlang + phase32 后,`test_cw_gain_chain.py` 10 处调用崩(evidence 参数已删)且任何清单条目都不指向它(F1)——worker 要么自行越发现、要么判据红停手。依赖声明「joy 批提交在飞改动」与树况不符(F4,核树即释)。
- **正本更新批 worker**:action_ops/action_exec/op-layer/planner.md/equip_pick.md 条目凭现稿可开工(锚齐);`logic-updates/pick-planner.md` 条目按字面执行 = :14 改不动(无该句)、:23/:33/:3/:41 永不清(F2)——「看情况」级歧义,不可开工。
- **验收者**:锚 1/2 行为级可判;锚 3 grep 在 sr-od-test 范围永红(F1),不可判。

## ⑤ 零发现面声明

以下面经本轮针对性核查**零发现**:design §2.0 统一契约与增补 2/3 合规性;§2.1 逐屏机械链与现码等价性(等待时长/确认链/点卡几何);§2.2 表已列条目的存在性与迁移方向;§2.3 全部四项取舍的论据与实码一致性(含 upgrade 重复应用修正论据);验收锚 1/2 行为口径;landing 3.1/3.2/末阶段依赖与优先级;三阶段互相覆盖无越界;`EQUIPMENT_ROSTER`=158 实测;`emit_overlay_confirm` 零读屏;`cw_screen_supply_node` T-1 模板先例引用;action_ops §4.5/§4.6、op-layer §1.4 刷新链规范与本批无涉面。边界完整性除 F2/F5/F6 所指口径问题外无其他遗漏。
