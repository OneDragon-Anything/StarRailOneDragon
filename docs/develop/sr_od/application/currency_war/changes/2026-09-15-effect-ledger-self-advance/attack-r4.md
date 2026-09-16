# 设计对抗报告·第四轮:容器直读与依赖面

> 攻击规范:`docs/develop/harness/iteration-design.md` §7(三核)/§5(写作硬规则三条)。
> 本轮聚焦 = 容器直读新方案(提交 dd2af7fc7 + 5988e448b,经济参数撤注册式提供方改 game state 内部自含)与前三轮未照过的灯下黑(漏斗序依赖/观测可见性/八格矩阵/发放时点申报完备性/落地试读);前轮已修面(attack.md F1-F12、attack-r2.md N1-N4、attack-r3.md R3-1~R3-2)不重开,仅对 R3-3 复核闭合度。
> 版本基准:现工作树 HEAD = 5988e448b;其下唯一在飞代码提交 94f2c3675(金失配归因批)未触及本设计锚文件(cw_game_state/cw_observation/cw_loop 零改动)。设计内个别行号锚相对 R3 基线再有漂移(如「cw_loop.py:1895-1899 禁令」实测 :1900-1904、observe_screen_context 漏斗调用点 :2682 实测 :2695),按 R3 约定以符号名定位、不判失实。本文行号均为现树实测。

## 结论

**仍有阻断项(1 项,小改可定稿)**:容器直读本体成立——镜像同步时滞窗与两源分叉在生产拓扑下均无可达形态,与现码 tick 直读 `session.active_strategies` 等价;节点类型 × 胜败八格全格等价或已申报。但**条件族免费刷新(本金充裕/+,常态在册高频卡)的采样金窗随发放时点前移而改变且未申报**(R4-3):发放从备战帧提前到 0q/0p 进入帧后,「按 bs.gold 现值评估、金未读零授予不补发」的条件族采样值从「该节点备战帧现读金」变为「上一读数沿用金(缺本战斗胜金)」,而 `free_refresh_balance` 是纯 logic 域无观察纠偏,漂移留存整局——行为变化申报与 landing 回归判据双双缺位,按「带开放问题的定稿不存在」门槛打回;裁决采样窗 + 补申报/判据即收口。另 5 项次要(R4-1/2/4/5/6)可一批小改。

## 发现清单

### R4-1 1.d 反解伪码仍与 helper 实签名不符:缺 kind 实参,R3-3 修复不完整(次要)

- 位置:design.md §2 方案 1.d(:29)
- 问题:现稿 `_nk = _node_key_for_ord(effective)` 仍为**单参调用**;实签名 `_node_key_for_ord(ordinal: int, kind: str) -> NodeKey`(`cw_game_state.py:3240-3246`,kind 为必填位置参数,类型派生消费)。R3-3 的修正(0b6905238「伪码对齐 helper 签名」)只修了解包半边(`plane, round_num = _nk.plane, _nk.round_num`,NodeKey 禁二元解包已消除),实参半边未修——按字面实现即 TypeError(缺必填实参),与 R3-3 原判同型,属已闭项回潮(半闭合)。
- 依据:design.md:29;`cw_game_state.py:3240-3246`。
- 建议规格文本:改为「`_nk = _node_key_for_ord(effective, node_type)`,取 `_nk.plane`/`_nk.round_num`(kind 槽位仅喂 node_type 现值,不影响反解出的 plane/round)」,或直书公式 `plane=(effective-1)//9+1, round_num=(effective-1)%9+1`。

### R4-2 「观察同步写端」锚点失实:所引行号是 sim 真值合成口,非生产写端(次要)

- 位置:design.md §2 方案 2(:40)
- 问题:「容器自持字段,§3.4.4;观察同步写端现值 = `cw_game_state.py:3574`」——:3574 在 `synthesize_from_game_state`(:3398-3577)内,该函数是 **sim 真值直写合成口**(`feed_sim_truth` 包装,生产引擎零调用,:3584-3587 自我申报),与「策略选卡后先于首个节点边界落账」的 live 时序论证无关。生产容器写端实为两处:①选卡确认裁决出口 handler 的 `write_logic`(`cw_screen_invest_strategy.py:545-559`,session append 与容器写同函数体同步);②漏斗载体中继(`cw_observation.py:2657`,relay 仅补从未写过的字段,`cw_game_state.py:3011`)。时点结论本身成立,但引用支撑了错误对象——硬规则 1(引用真实)同类缺陷,与 R3-3/F10 同族。
- 依据:`cw_game_state.py:3398-3602`(合成口 + 包装)/`:3574-3576`;`cw_screen_invest_strategy.py:533-559`;`cw_observation.py:2644-2658`;`cw_game_state.py:2994-3022`(relay 语义)。
- 建议规格文本:「容器写端 = ①选卡确认裁决出口 handler write_logic(session append 与容器写同步双写)②漏斗 relay(仅补从未写过字段,恢复局首帧补写);策略选卡后先于首个节点边界落账」。

### R4-3 条件族免费刷新采样金窗随发放时点前移而变,行为变化申报缺失(重要,阻断定稿)

- 位置:design.md §2 方案 1.c(:24)与行为变化申报(:42-48);landing.md 3.2 完成判据(:26-31)
- 问题:发放桥条件族语义 = 「按 bs.gold 现值评估——金 > above 时每额外 step 金 +1 次、至多 cap;金未读(None)= 条件不可评估 → 本拍零授予(…授予量随当拍现值变化,**不补发历史拍**)」(`cw_game_state.py:1198-1207` docstring;活载体 = 本金充裕/+,50/10/3,`cw_investments.py:260-294` 注册在册,数十套推荐阵容点名的高频卡)。发放闸 = advanced 位,推进提前到弹窗/0q/0p 进入帧后,条件族采样窗随之改变:
  1. **0q 位面过渡帧**(boss 胜后入场帧):分支写点(`cw_loop.py:1010-1039`)只写上下文、零金写;battle_or_transit 相位 spec 仅 phase_round(`cw_observation.py:2112`)不读金 → 采样金 = 上一读数沿用值((p,9) 备战帧金,**缺 boss 胜利金**)——与现码(该节点备战帧现读金,含胜金,`cw_loop.py:1947-1953`)存在 10 金档带移位 → 单次授予 ±1~3 档漂移;
  2. **0p BOSS简报帧**:同机制,boss 节点条件族在 0p 帧按沿用金评估,与现码 boss 备战帧评估存在商店期消费窗差;
  3. `free_refresh_balance` 是纯 logic 域(「写入=仅逻辑,无 UI 观察通道」,`cw_game_state.py:2595-2596`),漂移无观察纠偏,留存整局。
  行为变化申报七条(:42-48)无刷新余额条目(「账本推进」措辞不覆盖采样窗语义);landing 3.2 的 F1/F7 回归均不辖授予量。附注:官方卡文「每次进入新节点时…」方向上,进入帧评估反而更贴卡文,但进入帧金样本是沿用陈值——「时点更对、样本更旧」,净效应未裁决,恰属须拍板的开放语义。
- 依据:`cw_game_state.py:1190-1231`(桥全文)/`:2595-2596`;`cw_observation.py:2100-2113`(PHASE_FIELD_SPEC);`cw_loop.py:1010-1039`(分支写点零金写)/`:1947-1953`(现码采样点);`cw_investments.py:260-294`。
- 建议规格文本(二选一,推荐 (i) 零机制):(i) **申报接受**——行为变化申报增一条「条件族免费刷新(本金充裕系)采样窗随发放时点前移:进入帧按当拍容器金现值评估(0q/0p 帧为上一读数沿用值,缺本战斗胜金;None → 该拍零授予且不补发);静态每节点族(加油站/搜打撤/双手狸)不受影响」,landing 3.2 增判据「0q 入场帧条件族授予量 = 按沿用金的一次性评估,后续备战帧零补发」;(ii) **维持现码窗**——条件族评估递延至该节点首个备战帧(静态族照进入帧发,条件族挂独立小水位),landing 3.1 增判据「0q 推进帧条件族零授予、备战帧补评估」。

### R4-4 容器值 None(零策略期常态)未纳入空缺省语义:字面实现 TypeError → 段失败告警刷屏(次要)

- 位置:design.md §2 方案 2(:40「空列表 → 聚合缺省」);landing.md 3.1 判据⑥(:12)
- 问题:relay 的会话侧值已确立闸拒写空表(`cw_game_state.py:3015-3016`「列表…非空才中继——中继空值会把未知固化成正式值」),未取任何策略的窗口容器值 = **None(非 [])**;守卫通过(settlement/streak 可知)∧ 零持卡帧可达「直读 None」——字面实现 `aggregate_economy(self.active_strategies.value)` 即 TypeError,被 1.f 整段兜住后 settle/project 该帧一并跳过 + 逐帧一条「效果推进段失败」warning(现码 `or []` 同窗静默,`cw_loop.py:1951-1953`)。判据⑥「容器 active_strategies 空」未区分 None/[] 两态。`or []` 是自然实现、实际风险低,但失败路径规格应钉死(R2 N4 同课)。
- 依据:`cw_game_state.py:2994-3022`(relay 空值拒写)/`:2591`(字段);`cw_loop.py:1951-1953`;design.md:40;landing.md:12。
- 建议规格文本(方案 2 内一句):「容器值 None(从未写过,零策略期常态)同空列表处置 → 聚合缺省(1.0/0/None)参数下金结算照常」;landing 判据⑥措辞改「容器 active_strategies 为 None 或 []」。

### R4-5 漏斗金序是段数值正确性的隐性依赖,设计只申报「不调整」未声明依赖(次要)

- 位置:design.md §2 方案 1.d(:36「漏斗内金 observe 与本段的既有先后序不为本迭代调整」)
- 问题:现状序实证 = 漏斗容器直写块内金写(`cw_observation.py:2539-2544`,observe/carry)**严格先于** observe_screen_context 调用(:2695),接线后效果段居其尾段,息基与条件族采样都取本帧金。该序一旦被重排(直写块后移/字段写序调整),息基静默变为上帧金——对账安灯虽能事后显影失配,但属「推算 bug 形态返修」而非设计约束。设计句只声明「不动它」,没声明「段正确性**依赖**它、方向是金先于段」——实现者与后续重构者都无法从设计文本复原这条约束(漏斗刚经历 _feed_board_state 合并重构,再排概率真实)。附申报完备性附注:息基值相对现码有系统性前移(现码 tick 在备战分支入口 = 上轮漏斗后的金,含上一备战轮动作消费;新段在本帧 observe 后、本帧动作前),「金结算时点与参数源」申报条已涵盖时点迁移,金额 Δ 宜在回归预期言明,防测试按「与现码金额逐位一致」立断言。
- 依据:`cw_observation.py:2493-2699`(直写块 → observe_screen_context 次序);`cw_loop.py:1885-1974`(现码 tick 在分支入口 = 上轮数据);design.md:36/44-45。
- 建议规格文本(1.d 内一句):「依赖声明:息基与条件族采样取 bs.gold 现值,正确性依赖漏斗内『金 observe/carry 先于 observe_screen_context』的既有序(本迭代不调整亦不重排;重排漏斗写序须同批复核本段)」;landing 3.2 增一句「备战帧结算息基 = 本帧金读数(非上一帧),与现码存在动作消费窗差,断言按本帧口径立」。

### R4-6 boundary_settled_ord 未规格化进 full_state_snapshot:静默跳过语义下离线零证据(次要)

- 位置:design.md §2 方案 1.d(:26「新工程字段 `boundary_settled_ord`(非 Field,同 `node_hist_ord` 形态)」)
- 问题:`node_hist_ord` 先例 = 普通属性直赋(`cw_game_state.py:2729-2735`)**且**列入 `full_state_snapshot` 工程结构段(:2897);每条 journal 行内嵌当时快照(:2798 写行/:2844 观察行),离线判读因此看得到 hist。水位若只按「同形态」自然实现而不进快照,则:结算跳过面全静默(守卫失败/金未读/total≤0 均无告警,design :34-35 申报语义)+ 水位不可见 → 「这节点为什么没结金」离线零证据(金写行只在结算成功时存在)。「同 node_hist_ord 形态」按最自然读法只辖存储形态,快照成员资格属实现者拍板点。
- 依据:`cw_game_state.py:2729-2735/2857-2899/2798/2844`;design.md:26/34-35。
- 建议规格文本(1.d 水位条补一句):「`boundary_settled_ord` 与 `node_hist_ord` 同列进 `full_state_snapshot` 工程结构段(离线判读『结没结、结到哪』的证据面)」;landing 3.1 增判据「快照含 boundary_settled_ord 且随水位落点更新」。

## 各方向判定表

| # | 方向 | 判定 | 一行理由 |
|---|---|---|---|
| 1a | 容器直读·镜像同步时滞 | 非问题(等价) | 生产容器写端 = handler 同步双写(`cw_screen_invest_strategy.py:545-559`)+ 漏斗 relay 先于同帧效果段(`cw_observation.py:2657` < :2695),推进帧集内无「session 已有/容器未写」可达窗;恢复局靠 relay 首帧补写 ∧ 弹窗腿禁用,开局空容器被 settlement None 守卫天然挡住 |
| 1b | 容器直读·两源分叉 | 非问题 | session 唯一变更写端 = handler append(无移除路径)且与容器写同体同步;relay 仅补从未写过字段(:3011);sim 合成口/标量投影是独立世界不共容器——无永久分叉形态 |
| 1c | 容器直读·空缺省语义 | 非问题(缺省核对✓)+ 1 缺口 | `aggregate_economy([])` → `EconomyEffect()` 缺省恰 = mult 1.0/flat 0/cap None,与 settle 的 `interest_cap_resolved(None)`→默认帽链接一致;但 None(零策略期常态)未声明 → R4-4 |
| 2 | 漏斗序依赖 | 是问题(次要) | 现状序 = 金写(:2539-2544)先于段(:2695)实证成立、与现码同窗无回归;但该序是息基/条件采样的隐性正确性依赖,设计只写「不调整」未声明依赖方向与重排约束 → R4-5 |
| 3 | boundary_settled_ord 观测可见性 | 是问题(次要) | node_hist_ord 先例含快照成员资格(:2897);水位不进快照 + 跳过全静默 = 离线「为什么没结金」零证据 → R4-6 |
| 4 | 节点类型 × 胜败八格 | 非问题 | combat/reward/boss 胜格 = 备战帧同窗同参(kind 镜像现值、派生序==镜像序)等价;四败格 = 双方同一败局闸静默跳过;supply 标准形态双方都不 logic 结算(已申报)、divert 形态备战帧 kind='supply' 结算等价;reward 的 settlement 停留上一战斗与 boss 规则③同批直定均在类型派生/容器域先于段执行,0p/0q 推进帧被备战帧闸挡住不结算——结算面无未申报行为差 |
| 5 | 发放时点迁移申报完备性 | 是问题(重要) | 条件族(本金充裕系)按当拍 bs.gold 现值评估且 None→零授予不补发(`cw_game_state.py:1198-1207`),发放提前到 0q/0p 帧后采样金变为沿用陈值(缺战斗胜金)且 free_refresh_balance 无观察纠偏——申报与回归判据双双缺位 → R4-3;其余时点族(gold_at_node_offset=超发货币 t+5 等)不经本段消费(settle 辖域排除,`cw_effect_inventory.py:1102-1105`),不构成本迭代语义面 |
| 6 | 试读 landing 3.1/3.2 | 可开工,5 处拍板点 | ①段函数签名与「备战帧」事实入参形态(独立直调函数如何获知本帧是否备战帧——入参还是读 bs.current_screen;判据式 ctx==SCREEN_PREP_FRAME 未写出)②容器 None 处置(R4-4)③`_node_key_for_ord` 实参(R4-1)④水位进不进快照(R4-6)⑤条件族采样窗裁决(R4-3);测试文件「或新增同域测试文件」已留余地可接受——前三轮已钉死面(frame 内联式/三分支水位/守卫清单/日志形状/原子切换)均无需再拍板 |
