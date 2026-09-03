# IMPL_ADV_R196——对抗审查第196轮(无锚轮;攻击面=已落码新核终态)

> 攻击者=全新视角(无锚自选攻击面)。对象=redesign/ 四文档正文+契约 v2 定稿
> (CONTRACT_SERIES_DECISION.md)+IMPL_FIX_LEMMAS.md+**已落定终态代码**
> (`decision/cw4/`、`strategies/mandate_v1_strategy.py`、
> `decision/decision_v2/series_adapter.py`、`sim/ab_core_swap.py`)。
> 步4b(商店线 criteria 接线)在飞文件禁碰、中间态不立案。文件面=本报告
> 单件,除报告外零写入。

## ① 计划

1. 入口分诊走 `sr-od-currency-war-dev`(已加载);定位本轮=对抗审查,
   主场=策略器侧代码 vs 文档规格对账。
2. 攻击面选择(无锚自选):以契约 v2 §3.2/§3.3 逐类对账截断器(判据④)
   → proof 层四函数位 vs §2.7/R192 修注(判据①)→ 骨架硬约束/常数溯源
   (判据①)→ 遥测键与登记节双向对账(判据①/⑤;登记节在计划成形后读)
   → sim A/B 装置(判据③)→ 类型注解(判据⑤)。
3. 证据形态:全部三元组带现树亲读行号+可复跑 grep/值对账(注册表
   `kernel/cw_state` 直调值复核,不用被审方自己的实现复述)。

## ② 新症(7 症)

### 症1(中高)proof 层换线判据在唯一生产调用点结构性空转——alt_comp 恒缺位、k_switched 恒 False,换线事件/塌缩出口构造性零发射,且该空转无任何裁量申报

- **三元组**:`decision/cw4/entry.py` L216-217(`switch = proof.should_switch(state, session, config, registry, skeleton_only=skeleton_only)`——无 `alt_comp` 实参)+L250-251(`_criteria_pass(frame, session, state, k_members, k_switched=False, old_line_members=())` 硬编码)+`decision/cw4/proof.py` L216-217(`if alt_comp is None: return SwitchOutcome(False, 'no_alt')`);检验式=①`grep alt_comp src/sr_od/application/currency_war/decision/cw4` 亲跑=11 命中全在 `proof.py` 定义/消费侧,**entry/bridge/mandate 零供给**(全域 alt 候选枚举仅存于冻结基线 `kernel/cw_intention.py` L957,新核不消费);②`grep k_switched entry.py`=L251 唯一调用点硬编码 `False`;③结果=should_switch 恒 `('no_alt', False)`、`line_switch_sell` 恒 `([], 'no_event')`(sell.py L38-39)。
- **规格冲突**:IMPL_DESIGN §2.7 接线义务明文「proof pass 内每备战期调用一次,**产出换线事件**」;R189-5 落点表 D-P4/D-FM4 均以 proof 层线级状态机换线事件为载体(撤线登记/回锁窗/塌缩)。`proof.py` 自带 alt_comp 参数与 D-P4 回锁窗逻辑(L224-227)全部为不可达死码。**STEP34_REPORT 解释性裁量清单(5 项)未申报此项空转**——裁量 #1 只辖商店线透传(decide_shop_screen/update_target),不辖备战线 proof 层。且 `'no_alt'`/`'no_target'`/`'e_cur_undefined'`/`'relock_window'` 四路 return 零计数(仅三因分键计数),违 §2.7「**不换线也记遥测(决策面可观测)**」——判读面会把恒 no_alt 误读为「判据未标定」(theta_unavailable 仍在计数)。
- **修法方向**:alt 候选供给接入 entry 调用点(枚举源=comp 库/基线同款 get_comp 通道,批属呈裁);或显式登记「换线判据 None-期等价空转」进裁量清单+补 no_alt 分键计数。

### 症2(中)EV pass 冲突处理宣称与实现零对应——`ev_conflict_dropped` 遥测与「先到先得丢弃」均未实现,同序列重复 SellBench 可达

- **三元组**:`decision/cw4/entry.py` L275-276(docstring:「冲突处理:EV 项与已发射骨架动作冲突(如席位)⇒ 先到先得丢弃 + 记遥测(`ev_conflict_dropped`)」)+L279-298(`_criteria_pass` 本体:line_switch_sell/funding_support_sell 结果**直接 append,无任何与骨架 out 的冲突检测、无 ev_conflict_dropped 计数**);检验式=①`grep ev_conflict_dropped src/` 亲跑=仅 entry.py L276 注释一处命中,零计数代码;②`grep ev_conflict_dropped .debug/temp/currency_war/design/design_telemetry.md`=零命中(**键节未登记**,违「design_telemetry 键节=遥测键单一登记源」纪律);③可达构造=骨架 M4 已发射 `SellBench(slot=s)`(mandate.py L262)后,EV pass `funding_support_sell`(sell.py L87 按 star/slot 排序全 bench 扫描,不感知已发射集)对同槽再发 `SellBench(slot=s)`(entry.py L297)——同序列重复卖同槽,第二笔执行必 `progressed=False` 触发 fail-stop 丢弃余下动作(契约 §2),整序列后半被一帧废动作截断。
- **修法方向**:`_criteria_pass` 增加与骨架已发射槽位/动作的冲突过滤+分键计数;或删注释宣称(两取一,禁注释宣称无实现)。

### 症3(中)升档器 λ/血线影子遥测计数对象与登记规格错位——λ 影子键无触发谓词求值恒全帧计数、真键 `advisor_lambda_armed` 零载体、血线影子键 `advisor_bloodline_shadow_armed` 零载体

- **三元组**:`decision/cw4/entry.py` L161-170(`_upgrader_evaluate`:`if not provisional.is_none('P_LAMBDA_QUANTILE'): sig.lambda_shadow_armed = True`——**仅判槽位非 None,零相对分位求值**;血线半边 `thr is not None and hp < thr.value` 计的是真键语义)+L229-235(计数键=`advisor_lambda_shadow_armed`/`advisor_bloodline_armed`/`neardeath_unlock`);检验式=①design_telemetry L67 登记原文:「λ 维:p=None 期 `advisor_lambda_armed` 构造性恒 0(None 期不消费定谳),**照测挂影子键 `advisor_lambda_shadow_armed`(行为无关的观察级计数,与触发率分键)**;血线维同治:……照测挂影子键 `advisor_bloodline_shadow_armed`+provisional 注入形态阈值」;②`grep advisor_lambda_armed\b src/sr_od/application/currency_war/decision/cw4`=零命中(真键无载体)、`grep advisor_bloodline_shadow_armed src/`=零命中(血线影子键无载体);③结果=λ 影子键计数对象=「槽位已标定后的帧全集」而非「影子触发帧」——R29-1/R41-5① 的「触发率照测」两态真表述在 λ 维落空(标定后该键恒等于帧数,无判读力),血线 None 期影子观测完全缺失。
- **定性按装置面纪律**:本案不攻击冻结族(激活率门/检测面装置本体)、不提案新键;修法=实现对齐**既有登记键**的计数对象(λ 影子键补相对分位影子求值;血线 None 期按注入形态阈值挂 `advisor_bloodline_shadow_armed`;真键 `advisor_lambda_armed` 补生产触发位),键集零扩张。

### 症4(中低)`bench_full_buy_abandon` 双失联——mandate docstring 声明产键但代码零计数,且键节未登记

- **三元组**:`decision/cw4/mandate.py` L199-201(docstring:「计数键(session.cw4_counters……):m2_retry_exhausted / dominance_bench_wait / m6_bench_full / m6_overflow_strand / **bench_full_buy_abandon**」)+L270-271(M2 腾席失败路径唯一计数=`m2_retry_exhausted`);检验式=①`grep bench_full_buy_abandon src/`=仅 mandate.py L201 一处(零计数代码);②`grep bench_full_buy_abandon .debug/temp/currency_war/design/design_telemetry.md`=零命中(键节/索引均无);③结果=宣称的「bench 满拒买」第三通道计数不可观测,R102-N1 三通道分键判读在实现侧缺一臂。
- **修法方向**:与 telemetry 键节对齐——或补计数+登记(走登记纪律),或删 docstring 宣称归并 `m2_retry_exhausted` 分键语义。

### 症5(中)截断器与契约 v2 §3.2 逐类判三处不一致——ClickSpheres「条件」实现为恒截断、条件续类零复检、BailToOuter 判型标签漂移

- **三元组**:`decision/cw4/entry.py` L91-94(`classify_frame_stability` 对 ClickSpheres 无条件 `return 'truncation'`)+L78-80/L101-103(SellBench/SellDeployed/DeployMove/RunDeploy/RunEquip 归 `_CONDITIONAL`,但 `truncate_frame_stable` L121-134 对 'conditional' **与 'continue' 同样无条件 append 续发**——名-槽一致性复检/前序累积静态推出/「推不出即截断」分支零实现,仅 L75-77 注释宣称「条件成立」)+L65-70(BailToOuter 入 `_TRUNCATION_POINTS`);检验式=契约 v2 §3.2 亲读:L93 ClickSpheres 行判=「**条件**(常态分支纯收集可续;掉箱分支……末批后截断)」——实现把常态可续分支也截断,序列粒度系统性粗化(每批 ClickSpheres 后即截断重观察);L84/L101/L102 拖拽/RunDeploy/RunEquip 行判=「条件」且依据列明「名-槽一致性复检……**推不出即截断**」为逐动作语义防线——实现无任何复检代码,条件续退化为无条件续;L92 BailToOuter 行=「退役·**终点**(……按序列终点语义)」——实现归截断点(发射行为等价,判型标签与契约表不一致)。17 类覆盖完备性本身核验通过(8+1+2+5+1=17,与 `kernel/cw_prep_actions` 17 具体类对账齐)。
- **修法方向**:按「实现与规格矛盾立案、修实现对齐规格」——ClickSpheres 恢复两分支判(常态可续);conditional 类落「复检/静态推出」实现或回契约打「结构性成立」修订标;BailToOuter 归 `_TERMINAL`。

### 症6(中低)常数双源/字面量绕注册表——BENCH_CAPACITY 重定义、成本 3 两处字面量、S 预留恒 0 使硬约束③空转

- **三元组**:`decision/cw4/mandate.py` L60-61(`BENCH_CAPACITY: int = 9`,注释自称「R8-8 重试上限**注册表直读**」但未 import——`kernel/cw_state.py` L30 `BENCH_CAPACITY: int = 9` 既有单一源,构成第二源)+L347-350(`cheapest_member_cost` 返回字面量 `3`,注释称「1★ 档 3 金注册表值」但零 import;对账=`cw_state` L922 招募费函数/`sell_refund` 族为单一源,现值一致纯系快照巧合)+`decision/cw4/criteria/sell.py` L94(`remaining -= 3  # 1★ 卖回净额(mult×c−fee=1×3−0)`,值与 `cw_state.sell_refund(1,3)=3` 亲算一致但字面量双源;该文件若属步4b 在飞面则本条锚以 mandate 侧为主、此处作同族扫描记录)+L339-344(`_s_reserve` 返回 `b_target(0, 0, 0)`;亲算 s_line.py L20-23:gap=max(0,0−0−0)=0 ⇒ 恒 0 ⇒ `check_s_reserve(gold, cost, 0)` 构造性恒过(L138 `gold-cost < 0` 仅在 cost>gold 时真,与①重复)——四硬约束检查点③「S 预留」在骨架实现中空转,与 §3.2 ③「整买目标预留金不被非 S 组成动作吃掉(辖……M6+dominance_buy)」语义不符;S 值规格=`s_line` 组装(B+饱和线+窗口预留+双刷费),非 b_target 零参退化形)。
- **修法方向**:import 符号名消费(cw_state.BENCH_CAPACITY / cost·refund 族函数);`_s_reserve` 改消费 `s_line` 组装值(或显式登记「interim 恒 0+开闸批接线」呈裁,禁静默)。

### 症7(中低)类型注解缺口(项目硬约束:所有函数签名、类成员变量都要有类型注解)

- **三元组**:清单亲读——`decision/cw4/entry.py` L270-271(`_criteria_pass(frame, session, state, k_members, *, k_switched: bool, ...) -> list`:frame/session/state/k_members 四参零注解、返回裸 `list`)、L174-176(`emit(..., config: object, *, ev_arm: str='full', registry=None) -> list`:registry 零注解、返回裸 list);`decision/cw4/bridge.py` L97-98(`decide_prep_action(self, obs, session, config)`:obs/config 零注解)、L88-89(`_assemble_turn(self, obs, session)` 两参零注解、无返回注解);`strategies/mandate_v1_strategy.py` L42-44(同款 `_assemble_turn(self, obs, session)` 零注解);`decision/decision_v2/series_adapter.py` L42-43(`decide_prep_screen(self, session: StrategySession, config) -> list`:config 零注解、返回裸 list)、L47(同款);`decision/cw4/mandate.py` L369(`_state_view` 无返回注解)、`decision/cw4/proof.py` L79(`key: str` 后注释挤压但注解在,不算)。检验式=逐文件亲读,辖域=本轮审查的六文件,非全仓断言。
- **修法方向**:补 `MandateFrame`/`StrategySession`/`GameState`/`tuple[str,...]`/`list[Emitted]` 等注解(TYPE_CHECKING 导入守纪律)。

### 观察项(不计数)

- **OBS-1**:骨架 §3.1「M5→…→M7 **单帧闭环**」(IMPL_DESIGN L625)与契约 v2 §3.2 OpenShop=截断点(L99)的时序互作用:凡 dominance/M2/M6 发射 `OpenShop` 的帧,截断器在首个 OpenShop 处收口,其后同帧的 M1/M3/M1′/M7 发射项被构造性丢弃(mandate L235/L273/L296/L303/L320 均在 OpenShop 之后仍有发射位)——「单帧闭环」在含开店意图的帧不可达,动作延迟至商店往返后的下一备战期。两规格各自忠实实现,属设计间张力,需裁决(或 IMPL_DESIGN 打「开店帧分帧重评」辖域标),非实现错。
- **OBS-2**:`decision/decision_v2/series_adapter.py` L4 docstring 「D``ecisionV2Strategy``」标记语法笔误(纯文本瑕疵)。

## ③ 豁免(本轮不立案面)

1. **步4b 在飞文件**:`criteria/{buy,refresh,stockpile,equipment,levelup}.py` 未深审(商店线 criteria 接线批在飞,中间态不立案);sell.py 深审原因=其为 entry 生产消费的 prep 帧 EV 面(步4 产物),其中 L94 字面量已按「若该文件属在飞面则以 mandate 侧为主锚」降级表述。
2. **冻结基线臂**:`decision/decision_v2/strategy.py`、`kernel/cw_intention.py` 等基线件按 §4.1「不改一行」豁免(仅作对拍锚读取)。
3. **流程侧代码锚**(cw_screen_prep 消费段、operations/):行号/路径漂移不立案(契约 §7 既裁)。
4. **让路面**:`sim/runner.py`(git status 见并行未提交改动,ab_core_swap 载体申报既裁)。
5. rng 中立性/registry 属性(sim A/B 公平性):`sim/ab_core_swap.py` 亲读——双臂同 `sim_decision_registry()` 派生、逐 seed 配对、新核 prep 面在 sim 零调用(SIM_CONSUMPTION_MAP Q1 同构),未发现违反;零漂移门形态与 R189-6 步1 修注②(a) 一致。数值锚直调复核:`interest.saturation_line(5)=50`=`GOLD_CAP_INTEREST` 派生链亲算;`DEFAULT_INTEREST_CAP=GOLD_CAP_INTEREST//10=5` ✓;`sell_refund(1,3)=3` 亲算 ✓;λ 表加载对象=v3.3 主表(statefn/lambda_death 头注与 IMPL_DESIGN R30-1 修订标一致)✓。

## ④ 冻结对账

- 冻结六装置族(D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面验证装置)本轮零攻击、零新增装置提案:症3 修法=实现对齐既有登记键,键集零扩张;症2/症4 修法涉及的 `ev_conflict_dropped`/`bench_full_buy_abandon` 均系**代码/文档已宣称的键**的对账,非新装置(若裁决取向为「删宣称」则连键都不增)。
- 冻结残余 11 项:本轮未触碰、未重复立案(四文档+LEMMAS 零改动主张下的对账读,无新立案指向残余清单条目)。
- 契约 v2 §3.3 fail-closed 形态:实现(unknown ⇒ 截断+`emitter_unknown_action_truncated` 计数,键已登记 L231)与条款一致 ✓;17 类判覆盖完备 ✓(判型值的三处不一致见症5)。

## ⑤ 清洁门申报

- 文件面=本报告 `IMPL_ADV_R196.md` 单件,除报告外零写入、零源码改动、零 git 操作。
- IMPL_ADV_R1-R195 全程未读(报告内对历史轮的引用均来自 IMPL_DESIGN/telemetry 正文既有修注标,非轮报告原文);telemetry 登记节(L67/L223/L231/L275)在①计划成形后读。
- 无凑数:7 症各自独立成立、检验式均含现树亲跑/亲读/注册表直调;无压症:症1(换线结构性空转)与症2(同槽双卖可达)均系生产行为面断裂,建议优先排裁;最弱一环=症6 的 `_s_reserve` 条(存在「interim 声明」辩护空间,已按呈裁修法表述)。
