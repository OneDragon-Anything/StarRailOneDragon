# IMPL_ADV_R197 —— 换核终态 A/B 前最后一攻(无锚轮)

> 攻击者:全新视角(R196 修复批未参与;IMPL_ADV_R* 全族禁读纪律遵守,本轮未读任何 IMPL_ADV_*.md——佐证:本报告所有引注均为本轮亲读文件+行号)。对象:redesign 四文档(design_economy/latch/telemetry/DESIGN_MANDATE_LAYER 选读相关节)+ 契约 v2(CONTRACT_SERIES_DECISION.md)+ IMPL_FIX_LEMMAS.md(冻结对账,通读通用纪律节)+ 终态代码全量亲读(cw4/entry·shop·mandate·proof·bridge·criteria/sell、series_adapter、ab_core_swap、decision_v2/strategy.py 透传面)+ 测试亲读(test_cw4_mandate_v1 / test_cw4_shop_line / test_cw_core_ab_harness)。
> 攻击面(任务书指定):①R196 修复自身的引注失准/修而不净;②步4b 商店波判据式真实性;③A/B 公平性终审;④两轮修复叠加后的回归缝隙。判据同源:规格对账/数值锚直调/rng 中立/契约逐类/注解规范。
> 结论:**9 症(高2/中高1/中2/低4),本轮零代码修复(清洁门:禁凑数修复)**;编排者小件 OBS-1 已落地(IMPL_DESIGN L625 辖域标,见文末)。**步6 A/B 前建议至少裁决症1/症2/症5**——三症均直接决定 A/B 测量面的有效性。

---

## 症1(高)塌缩出口发射序结构性失效:EV pass 追加在截断点之后,line_switch_sell 在换线生效主场景被静默丢弃

**三元组**:
- 规格:IMPL_DESIGN §2.2 protected_sell 行(L190)「唯一出口 = 换线后 K 已更新的下一备战期 V_opt+V_power 塌缩」;L123(R9-2:K′ 生效帧的 line_switch_sell 调用返回即构成「已评估」);契约 v2 §3.2 OpenShop=截断点(L99「序列在此收口」)。
- 代码:`entry.emit` 拼装序 = 骨架 pass(`out`)→ EV pass `_criteria_pass` **append 到同一列表尾部**(entry.py L371-396);而 `mandate.run_mandate` 在新线有缺口成员时发 `OpenShop`(mandate.py L281/L285,reason='m2_buy';dominance/M6 亦发,L242/L328);`decide_from_turn` 最终 `truncate_frame_stable`(bridge.py L153-159)遇截断点即返回前缀,**截断点之后追加的一切 EV 发射被丢弃且零计数**(entry.py L189-191,截断点丢弃系判型内语义,不进任何 counter)。
- 测试:`test_entry_k_switched_real_value`(test_cw4_mandate_v1.py L642-674)直调 `entry.emit`——**不过截断器**;`TestR196EvConflictDrop`(L677-718)直调 `entry._criteria_pass`。截断测试(L721-749)用手搓序列,不含「mandate 含 OpenShop + EV 卖面并存」形态。组装点 `decide_from_turn` 对该交互零覆盖。

**机理**:换线生效帧(K 已翻为 K′)恰是新线成员缺口的典型帧 ⇒ `missing` 非空 ⇒ M2 发 OpenShop(截断点)⇒ EV pass 的 line_switch_sell(及 funding_support)发射全部落在 OpenShop 之后 ⇒ 截断丢弃。`k_switched` 系单帧实值化(entry.py L334-341,帧尾 prev_line_name 覆写)⇒ 下一备战期窗口关闭,塌缩出口**永久错过**且无遥测可辨「评估了不卖」vs「发射被截断丢弃」。旧线件此后仅能经 M4 fuel_sell 被**机会性**卖出(旧线成员对新 K 零重叠=fuel 候选正对象,mandate.py L262/L269)——绕过 V_opt+V_power 比较,protected_sell「唯一出口=塌缩比较」的规格承诺在生产主路径不可达。R9-2 的「调用返回即重置」只救了 stop_flag 语义,救不了发射面。

**修复方向(呈报,不落码)**:EV pass 发射前检查骨架输出是否已含截断点/终点——含 ⇒ EV 面本帧不 append(或换帧重评:k_switched 窗口从「单帧」改「至首次成功评估发射」,与 R9-2 同型解耦);并补「塌缩发射被截断丢弃」独立计数键。判据式测试须走 `decide_from_turn` 全链。

## 症2(高)换线事件→K 翻转因果链无生产载具:update_target 透传基线意向机,cw4 should_switch 是影子权威

**三元组**:
- 规格:IMPL_DESIGN L91/L101/L625(R1-3:换线属证明层 proof/line_selector,K 变更下一备战期生效);entry.py L328-331 注释「K 翻转由 update_target(下帧)承载」。
- 代码:`MandateV1Strategy` 继承 `DecisionV2Strategy.update_target`(bridge.py L20-23 透传声明「禁自创」);decision_v2/strategy.py L276-314 的 update_target 由 **v3 意向状态机** `update_intention` 决定 `session.target_comp`——判据体系(锁线/撤销/miss 计数)与 cw4 proof.should_switch(θ/D_min/δ/should_switch_e,P16)完全独立。cw4 的事件输出只有 `register_eviction`(回锁窗)+`switchline_event` 计数,**不写 target_comp**。
- 测试:`test_entry_k_switched_real_value` L670 `session.target_comp = comps[1]` **手动执行了生产中不存在的一步**;`test_relock_window_blocks_within_dmin`(L605-640)同样手动翻转+手动 register_eviction。

**判读**:两条互斥读法必居其一,须编排者裁决入档:(a) 设计=A/B 期换线权威仍归基线意向机(新核只换 prep/shop 决策)——则 should_switch/relock 窗/drought 全部为行为无效面,「换线接线修活」应降格为「影子求值接线」,且 A/B 判前锁须显式声明「两臂换线行为恒等(共用 update_target)」,否则臂间 diff 归因会误含换线路径;(b) 设计=新核自有换线(R1-3 字面)——则透传声明与 R1-3 冲突,事件→翻转缺生产接线,回锁窗拦截的是不控 K 的影子事件、形同虚设。现状代码两头不靠:测试在单元层各自为真,生产链路上「谁翻 K」与「谁判换线」是两个不通信的权威(双源,判据纪律「记忆单一源」同型病)。另:基线翻转不经 cw4 事件 ⇒ 无 eviction 登记 ⇒ 回锁窗对真实翻转零保护。

## 症3(中高)商店波卖出无同槽冲突守卫——R196 症2「先到先得丢弃」修而不净(只修了 prep 线)

**三元组**:R196 症2 修复形态 = prep `_criteria_pass`/skeleton 分支的 `sold_slots` 集合 + `ev_conflict_dropped` 计数(entry.py L382-396/L423-437)。商店侧 `decide_shop_wave` 的 funding_support(L413-434)与 sell_for_interest(L396-410)与 M4 fuel sell(L233-250)共享同一 pre-wave bench 快照,**无任何已卖 idx 去重**——`funding_support_sell` 从全量 bench 选槽(criteria/sell.py L77-103,无排除参数)。同波对同一 bench_idx 双 SellBench ⇒ 执行侧第二笔 progressed=False 触发 fail-stop,整序列后半被一帧废动作截断(与 prep 侧被修掉的病同型)。测试:test_cw4_shop_line 无任何同槽冲突用例(①-⑥ 全节亲读)。另卖面小账:sell_for_interest 发射后 `bench_free += 1` 但 **gold 不加 income**(L410,与 M4 的 L247-248 不对称)——后续买面金投影保守偏低,方向安全但口径不一致,随症3 一并修。

## 症4(中)商店发射器条件续无「名-槽一致性复检」载体 + 词表超集(LevelUp)未回契约

- 契约 §3.1 拖拽族行(L70):「逐动作语义防线=名-槽一致性复检;board 空位/星级合成须按前序动作累积静态推出,推不出即截断」。`shop.truncate_shop_frame_stable` 对拖拽族(SellBench/SellDeployed/DeployMove/SwapDeploy)**无条件放行**(shop.py L155-174,无 bench_slots 参数、无复检分支);docstring(L95-97/L128)引注契约却未实现该防线。若语义防线归执行侧 `expect` 字段承载,则 prep 侧 R196 新增的发射器内复检(entry.py L170-185)与之构成**双源不对称**——同族防线两域两种载体,须择一申报。测试 `test_drag_family_conditional_continue`(test_cw4_shop_line L255-261)断言「条件续=原样通过」——**锁的是实现回声,不是契约判据语义**(判据式真实性缺口,攻击面②命中)。
- `_SHOP_CONTINUE` 与截断词表含 `LevelUp`(shop.py L94/L157-159)——契约 §3.1 商店域 8 类(减 PickEvent)不含 LevelUp(prep 域类,经 LevelUpShop is-a 关系混入 isinstance 命中)。词表超集=§3.3 fail-closed 通道被静默放宽(LevelUp 若流入商店线将被「可续」而非 unknown 截断),违 §3.3 附章「增补条目须回契约改版,禁只改代码」+R195 症1 辖域纪律。修法:词表收紧为契约 8 类(LevelUpShop 已 is-a LevelUp,isinstance 判序先具体后抽象即可)或回契约补行。

## 症5(中)A/B 公平性终审:门组不对称 + 双 harness 并存,新臂确定性与池指纹守卫在 ab_core_swap 侧缺位

- `ab_core_swap.baseline_self_pairing_gate` 只证 decision_v2 臂零漂移;**新臂(mandate_v1)无对应自配对门**——若新核存在非确定性(或意外消费局内 rng),步6 配对差会把噪声混入处理效应且无门可红。rng 中立在代码里只是注释契约(shop.py L22「零 rng 消费」),`test_rng_neutral`(test_cw4_shop_line L448-457)只锁 session.rng 不动,不辖局内引擎 rng 流。
- `arm_diff_probe`/双臂工厂**无池指纹一致性守卫**;带守卫的 `runner.simulate_core_ab`(test_cw_core_ab_harness 三锁:零漂移/自配对/指纹守卫)是另一套 harness。两套并存且「runner 侧正式合流入口待裁」(ab_core_swap.py L3-5)——**步6 前必须裁决用哪套**:若用 ab_core_swap,守卫缺位;若用 runner.simulate_core_ab,ab_core_swap 的门组成为无消费死码。判前锁应补一条「新臂自配对零漂移」门(与基线门对称),并声明换线路径两臂恒等性(症2 裁决的下游)。
- 公平性已核项(申报无症):两臂同 `sim_decision_registry()` 派生、同 seed、registry 属性经构造注入、ev_arm 非法值回落 full 两域一致(shop.py L205-208 / bridge.py L150-152)。

## 症6(低中)need=3 字面量双源,注释失准

shop.py L414-415 `need = 3` 注释称「1★ 档 3 金注册表值」——未走注册表/`bench_char_cost` 派生,与 criteria/sell.py L98-99(R196 症6:「禁字面量 3 双源」)直接顶撞;引注失准+常数单源违例。修法:need 缺省改 `bench_char_cost` 未知名保守估的同一派生,或引注册表常量名。

## 症7(低)drought 计数器只写不读;evicted「逐帧」口径与实现不符

- `LineState.drought` 累计(proof.py L300-305)+商店侧重置(shop.py L436-441),但 cw4 内**无消费端**:换线排除读 `session.drought_excluded`(proof.py L193,cw4 无写端)、撤线判据不消费 drought。若 D-A45 设计有「干旱撤线」消费位则缺接线;若无限,须申报为纯遥测(现形态=只写计数器,行为面空转)。
- `LineState.evicted` docstring「撤线登记后逐帧 +1」(proof.py L67-68)——实际步进载体=`update_line_state`,而 prep 实体面(球/箱/典籍/overlay)早退帧**不步进**(entry.py L299-309 在 proof pass 之前 return)。窗口按「备战期」计量,非「帧」;方向保守(窗偏长),但注解口径与实现不符,按注解规范改述。

## 症8(低)死常量与边缘兜错缺位(申报清单)

- `entry._CONDITIONAL_COMPOSITE`(L92)定义后零消费(分类经 `_CONDITIONAL` fallthrough 达成同效)——死代码,删或接进 `classify_frame_stability` 显式分支。
- `_lambda_quantile_armed`(L220-246):CI 上端高于全序最大值时 `idx=None ⇒ None`(最危端反不评估)——与「域外同判 None」规格自洽,但属危险端观察盲区(None 期影子键语义),挂账至标定批。
- `should_switch` alt_comp 外部传入路径 `e_rounds(alt)` 无兜错(proof.py L270;自派生路径已试算安全,外部传参系测试专用——生产禁外部传参应加注)。

## 症9(低)商店波存在性信号用初始金而非投影金

`dominance_buy_eligible(int(state.gold or 0), ...)`(L277)与 M6 存在性 `int(state.gold or 0) > g_star`(L324)消费**决策前**存量金;同波 M2/M3 支出后投影金已降。实际支出由 `check_affordable(gold=投影金)` 兜住(支出安全无损),失真仅及存在性计数键口径(dominance_bench_wait/m6_* 的触发面),申报即可,不构成行为面缺陷。

---

## 清洁门申报

- **禁凑数/禁压症遵守**:本轮零代码修复、零测试改动;9 症全部为呈报待裁,未为「清零」做任何美化。唯一写入=本报告;另一编辑=编排者小件(OBS-1,任务书明示豁免)。
- **冻结纪律**:冻结族未攻击、未新增装置;IMPL_FIX_LEMMAS 冻结对账与冻结残余 11 项未触碰(本轮未发现与残余账交叉的新证据,无新增对账行;OBS-1 裁决=编排者既裁方案 a,契约零改动,与残余账无涉)。流程锚豁免援引:症1/症2 的截断发射序/战略层钩子属流程面交互,本轮仅攻击决策侧拼装序与接线真实性,未裁流程侧框架。
- **telemetry 登记节**:计划成形后读——本轮零修复,不涉及新键登记(症1/症3 建议的计数键留待修复批登记)。
- **IMPL_ADV_*.md 禁读**:遵守(引注全部来自本轮亲读)。
- 未跑测试(零代码改动的纯审查轮;OBS-1 为文档编辑,无可跑面)。

## 编排者小件记录(OBS-1 裁决落地)

IMPL_DESIGN.md §7 要点 4(L625)「…M6→M7 单帧闭环…(R1-3)」处追加辖域标:「【R197 辖域标(OBS-1 裁决落地,R196 编排者裁=方案 a,契约不动):开店帧分帧重评——OpenShop 系契约 v2 §3.2 截断点,备战序列在开店处收口,商店波决策归 decide_shop_screen 另帧;本「单帧闭环」辖域=备战帧内部编排,不含开店往返】」。三元组:IMPL_DESIGN L625(编辑点)↔ 契约 v2 §3.2 OpenShop 行(L99)↔ cw4/shop.decide_shop_wave 另帧载体(bridge.py L118-137)。已亲验编辑落盘(grep 单帧闭环现 3 处命中含 L625 新标)。

## 附:步6 前置裁决清单(编排者视角排序)

1. 症2 裁决(换线权威归属)——决定 A/B 两臂是否换线恒等,判前锁 v6 前置语句的一部分;
2. 症1 修复(塌缩发射序)——不修则 protected_sell 规格在生产不可达,臂②「卖出带」预期指标(L626)的测量对象缺一类;
3. 症5 裁决(harness 合流 + 新臂自配对门)——A/B 测量工具有效性;
4. 症3/症4/症6 可随修复批;症7/8/9 挂账即可。
