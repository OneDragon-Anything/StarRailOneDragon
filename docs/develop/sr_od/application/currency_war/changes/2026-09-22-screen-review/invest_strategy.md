# T-6 投资策略 修法设计(invest_strategy)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 未收敛 4 条→修订→r2 收敛;残留 N-1 低=登记面跨稿归属,转 T-37 汇总)
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-6-r1.md`(F-1..F-5;总判定「有问题(高0 中4 低1)」)。涉事代码与代码内文档以仓库现状为真值逐处核读(含对审查报告命中点的复核,复核修正见 §2.5);本文定位一律符号锚 / 文档节号(行号不作定位依据,约定 = flow/README.md 卷首);文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`。
- 真值基线 = 本文修订时点工作树(并行落地批已清偿 F-2 症状面,改判见 §1.2/§2.2);**落地批动笔前若代码/正本已再变,以落地时点现状重新对账后再动笔,禁按本文过期症状照稿落地**(与 T-1/T-3 稿同款条款)。

## 1. 问题与动机

### 1.1 F-1(中)画面 op 局外防御路径内产选卡决策(决策控制分层违例面,无正本登记)

- 现状症状:`operations/cw_screen/cw_screen_invest_strategy.py::CwScreenInvestStrategy._decide_and_act` 的无 match(局外独立跑)分支——不调策略器(无策略器可调),而是在画面 op 内直调 kernel 判据 `kernel/cw_events.py::decide_event`(喂裸空容器 `GameState(schema_version=GAME_STATE_SCHEMA_VERSION)`)组装 `CwActionPickInvestStrategyParam` 并照常派发执行选卡确认链(显式跳过刷新链)。该路径仅独立跑可达(生产对局 cw_loop 分发时 match 恒在);画面篇 `screens/invest_strategy.md` §4 已自申报该分支,但 as-built 自申报不等于正本背书。
- 根因归层:**流程层**。决策控制分层铁律(规范单一源 = flow/README.md §1)字面:「流程侧(外循环 / 画面 op / 动作执行)禁止任何形式的决策闸门与政策判断……决策的值域与节拍永远由策略器在决策时决定」;op-layer.md §1.1:决策动作 node 的职责只有两件——调策略器拿动作、把动作交给动作 op 执行——局外无策略器,两件都无从履行,直调 kernel 判据组装决策 = 流程侧产决策。op-layer §1.1 对局外的在册豁免仅辖上报面(「report_screen_xxx_obs 落容器(match/gs 缺席的局外兜底路径跳过)」),不辖决策面。且与同族遭遇屏处置不一致:`operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act` 局外/空候选 = 零决策零点击 round_success 终结交回重读(已核读证实)。
- 解决到哪:删局外决策分支,match=None 早退零决策零点击 round_success 终结交回(方向①,方案与取舍见 §2.1);`screens/invest_strategy.md` §4 对应分支申报同步。
- 明确不解决:`operations/cw_screen/cw_screen_invest_env.py` 同款局外分支(已核读证实同病,归 T-7 投资环境审查辖域,本稿只登记同族联动面);遭遇屏局外面 = **在册合规先例,现状即零决策交回,无需修**(`cw_screen_encounter.py::CwScreenEncounter.act` :159-165;T-4 稿 §2.1 修的是其决策无效盲选回退/pick idx 静默钳位面,与本条不同面,其「明确不解决」明令勿误伤本面);观察 node 的局外跳过 report 面(在册豁免,合规不动);空候选 round_fail 契约(在册裁定「没有选到就是代码 bug」,与局外无关)。

### 1.2 F-2(中,修订改判:已清偿销项)cw_overlay_pick_action.py 模块头对 pick_invest 的形态申报陈旧

- 原症状(审查报告 F-2 所记,落地前快照):模块 docstring「自上报统一」段申报「上报发射相零写……」+「银狼闭环迭代起三线例外:pick_invest / pick_equip / pick_supply = 分步实现(落地相在画面 op 重入裁决出口/节点完成门,证据闩语义)」,与同文件即时单相实现矛盾。
- **修订时点重核结论(以工作树现状为真值)**:该症状面已被并行落地批(选择装备/骇入策划单相化批)清偿——模块头「自上报统一」段现文 = 「原『发射/落地两相』例外(invest/equip/supply/planner……)已随投资两屏、供给、装备、策划各迁移批全域清偿(用户裁定 = action_ops.md §1 增补 2):现役全族 = 机械链发出后立即一口写完整结果,容器写语义单点 = 各上报函数,零证据闩零重入裁决补写面」,pick_invest 面现役申报正确;正本 flow/action_ops.md §4.5 已改「上报形态 = 全族即时上报……发射/落地两相与证据闩形态已全域清偿,零重入裁决补写面,禁新增分步写法」,PickPlanner/PickEquip 两行已是即时单相详注;原报告所引旧文本在工作树零命中(逐句核读证实)。
- 根因归层:约定层(原判成立——族级代码内文档未随迁移同步);修法主体已由并行批代为执行,本发现**关闭(销项)**,无落地面。
- 解决到哪:销项登记 + 两件连带处置(见 §2.2):①supply_node.md §2.4 目标文本与落地现状/正本冲突登记(禁照抄,防过期症状照稿回写 = 对现役回归);②模块头残留批史叙事与 design § 引用(禁形一/二命中)收回本稿 F-5 辖域清理(§2.5)。
- 明确不解决:该段的文本归口重写(T-37 汇总已登记归口 = T-4 修订版 encounter.md §2.3,supply_node §2.4 段规格作废;本稿 F-5 只清禁形引用不动申报口径,两批以先落者为准、后落者按落地时点现状对账,禁双写);`CwActionPickInvestOp` 类 docstring(申报正确,不动);`pick_invest_strategy.py`/`pick_invest_env.py` 模块头「即时上报形态」段(正确;拆分史句归 F-5);pick_planner/pick_equip/supply 三类 run 注释内的 design § 引用(归 T-10/T-9/T-5 F-7 辖域,联动面登记)。

### 1.3 F-3(中)logic-updates 正本(README 索引)未随 pick-op-unify/投资两屏迁移批更新

- 现状症状:`game_state/logic-updates/README.md` 三面:①「逐动作专篇索引」事件线 pick 族表无 PickInvestStrategy/PickInvestEnv 行——两注册行实存(`operations/cw_op/cw_action_registry.py` 两行同指 `CwActionPickInvestOp`,action_ops.md §4.5 在册),反被归入「7 个 handler 自管 pick 子类……由各画面 handler 自管消费链,不经注册表」bullet,与现状(注册行在册、经注册表工厂派发、即时上报整支走获得链落 `active_strategies`)直接矛盾;②「注册表 26 行 / 20 op 类」「事件线 pick 族(5 行)」等计数已被 pick-op-unify 批与投资两屏拆类抛离(action_ops.md §4 基准 = 36 行);③按该 README 自定的「一行一文件」规则,PickInvest 两注册行缺专篇——active_strategies 写语义(按名字去重追加/无效载荷拒绝)散记于 gain-chain.md §2.4 / fields.md §3.4.4,logic-updates 侧零落点。
- 根因归层:约定层(正本索引随批同步缺口,申报面遗漏)。
- 解决到哪:该 README 统改权已由 T-1(备战)设计稿(prep.md §2.4)认领(T-5 稿 §2.2 交叉面声明同证),本稿只交三项内容:①PickInvest 索引行目标语义;②「handler 自管不经注册表」句删除的诉求登记;③专篇缺位的二选一决策(新增 pick-invest.md 专篇,骨架见 §2.3)。
- 明确不解决:README 文件本体动笔(归 T-1 统改批,本稿三项为其实施输入);其余 pick 行目标语义(PickEncounter 归 T-4、PickSupply 归 T-5);计数类陈述重述(T-4 F-2 已立「以代码现值为准」口径,本稿沿用不另立);投资环境支行为面复核(归 T-7)。

### 1.4 F-4(中)invest_strategy.md §4 决策体图缺「三闸全败 → 同访问重调落选卡」现役分支

- 现状症状:现役行为 = 刷新建议帧但闸 1/2/3 全部拒绝时,同访问内重调 `decide_invest_strategy()` 一次落选卡(重调仍返回刷新 → act=None → 汇入「决策无有效选卡输出」round_fail 显式失败);画面篇 `screens/invest_strategy.md` §4 决策体图只画「单次决策 → 刷新/选卡/fail」三分支,未申报重调分支与 round_fail 汇入路径,§5 终结表与 §8 守卫节亦未提。对照同族 encounter.md §4(分支刷新行)/§8(「刷新单次」条)对同款「闸拒绝重调一次」逐字申报,本篇漏申报。附带(不单独计条):§4 坐标引用多处仅 area 名无画面名前缀(screens/README.md §2 纪律字面「坐标一律 `画面名.area名`」,§1 分发锚有全形先例)。
- 根因归层:约定层(画面篇 as-built 漏申报)。**非行为违规**:重调发生在任何刷新执行之前、未引入新事实,不触 op-layer.md §1.4「禁重调决策」的刷新链禁令;策略规格正本在册(strategy-docs/13_pick_family.md §1 invest 行「重决策仍经本入口」),策略侧同帧去重契约在册(`strategies/impl/flow.py::CwFlowStrategy._decide_invest` docstring:scratch 键 = (kind, 候选元组),「建议帧首调发建议、紧随重调落选卡」)。
- 解决到哪:§4 决策体图补分支申报 + 坐标引用全形;§5 终结表、§8 守卫节同步。零代码变更。
- 明确不解决:行为本体(在册合规);遭遇屏同款申报(已在册);投资环境屏同款面(归 T-7);op-layer.md §1.4 条款措辞(在册正确,本分支属在册形态不涉修订)。

### 1.5 F-5(低)注释纪律存量:勘误史叙述与会话局部编号

- 现状症状(辖域三文件;依据 = AGENTS.md §8「变更史不进注释」「引用必须是持久索引(禁会话局部标识符)」):`operations/cw_screen/cw_screen_invest_strategy.py`——CARD_CLICK_Y 常量注释块勘误史(I16「卡底 820 选中」推翻叙述 + 「旧 doc 均过时」)+「task#20」+「三审 off-by-one」+ 模块 docstring 退役/拆除史叙述(「visit 起点单点复位已随防重入宿主退役」「验效双通道已拆除(用户裁定 2026-09-10;2026-09-14 收敛为零比对)」)+ ENTRY_REPROBE 注的「旧实现……修法」对照叙事;`operations/cw_op/cw_overlay_pick_action.py`——模块头禁形引用(批史叙事与 design § 引用,自 F-2 销项收回本节处置,见 §2.5)+「task#103 化债,W265」「局29」「r326/P1⑦」「r327(终审 E)」;`kernel/cw_action_report/pick_invest_strategy.py`——模块头「自 pick_invest.py 拆分(投资两屏迁移批……)……原『发射相意图遥测/落地相证据闩』分步上报随拆分废除」拆分史段。
- 根因归层:约定层(注释面随批同步缺口;与遭遇屏同类存量,T-4 F-5 同族)。
- 解决到哪:清理准则沿用 T-3 设计稿(battle_wait.md §2.6)已立五条(禁形一·会话局部标识符 / 禁形二·变更史 / 改写方向 / 保留豁免 / 一次成文),对本稿辖域三文件清理;命中面与豁免面清单见 §2.5;标注「与全仓注释卫生批(建议中,battle_wait.md §2.6 同族联动面)合并执行亦可」。
- 明确不解决:obs 解析器文件(报告已核干净;`cw_node_obs.py` 遗留面归 T-4 F-5);`pick_invest_env.py` 模块头同款拆分史(:8-9,归 T-7,登记联动面);正本 `flow/action_ops.md` §4.5 行文中的任务号(非代码注释面,登记联动面);策划/装备等他屏类的语义复核(归 T-8..T-10 辖域,本稿只清编号不清语义)。

### 1.6 已核对一致面与正面结论

报告 §3 十项一致面(投资域收窄条款/逐卡刷新留守臂/剩余语义观察写端/派发即终结/零容器写与写槽分域/决策无有效输出处置/观察上报/动作 op 行/九节文档骨架/旧符号清零)核对通过,不立修法。正面核对结论特别记一笔:本屏**无 T-4 F-1 同类盲选回退**——决策返回 None/词表外类型/idx 越界/重调仍刷新,全部 = round_fail 显式失败,零盲选零静默钳位(`test_invest_strategy_empty_opts_fail_not_blindfire` 在册),出口③语义合规。

## 2. 方案

### 2.1 F-1 修法(核心:方向①,对齐同族遭遇屏)

**代码面**(`operations/cw_screen/cw_screen_invest_strategy.py::CwScreenInvestStrategy._decide_and_act`,本稿唯一行为变更点):

1. 删局外 else 分支整段(直调 `decide_event` 组装选卡 param,含内嵌 `GameState`/`GAME_STATE_SCHEMA_VERSION` 局部 import)。
2. match 判空提前为早退出口,置于空候选检查**之后**(顺序依据:空候选 = OCR 读缺 bug 面显式失败,契约与局外无关,在册锁 `test_invest_strategy_empty_opts_fail_not_blindfire` 不回退):

```python
match = self.ctx.cw_match
if match is None:
    # 局外独立跑(无策略器可调)= 零决策零点击终结交回(遭遇屏同款
    # 处置;决策控制分层铁律:画面 op 不产决策,局外兜底决策路径废除
    # ——flow/README.md §1;op-layer.md §1.1 两件职责)。
    log.info('[cw-strat] 局外无 match → 零决策零点击终结交回')
    return self.round_success('局外无 match,零决策零点击终结交回', wait=1.5)
act = match.strategy.decide_invest_strategy()
refresh_slots: tuple[int, ...] = ()
if isinstance(act, CwActionRefreshInvestCardsParam):
    refresh_slots = act.slots
```

3. 刷新臂守卫条件 `if refresh_slots and match is not None:` → `if refresh_slots:`(match 恒在场,后半条件随局外早退死码化,删除)。
4. 顶部 import 清理:`from ...kernel.cw_events import (decide_event, is_economy_engine)` 删 `decide_event`(唯一消费点 = 已删分支;`is_economy_engine` 保留,`_guard_classify` 消费)。
5. `_decide_and_act` docstring 补出口句:「局外无 match = 零决策零点击 round_success 终结交回(遭遇屏同款;flow/README.md §1 决策控制分层铁律)。」

**行为变化申报**:独立跑该屏(经 run_operation/独立应用直跑)不再完整走选卡——原局外分支以裸空容器 decide_event 产决策并真实点击选卡确认链;生产对局(cw_loop 分发)零行为变化(路径不可达面)。

**测试面**(`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py` 投资策略臂):现役测试全部经 match 桩(`SimpleNamespace(strategy=...)`)或空候选早退,无测试消费局外分支(单一源 = 该文件投资策略段核读),零回退;补一锁(建议名 `test_invest_strategy_no_match_zero_decision_handback`):ctx.cw_match = None + 非空候选 obs → act = round_success、点击记录为空、零派发零上报。

**文档面**(`screens/invest_strategy.md`):§4 伪代码「(无 match 局外防御 = 裸空容器 decide_event,且显式跳过刷新链)」行替换为「(无 match 局外 = 零决策零点击 round_success 终结交回——遭遇屏同款;生产对局分发恒有 match,该出口仅独立跑可达)」;§5 终结表补行:`| 局外无 match(仅独立跑可达) | 访问终结 | round_success 交回(零决策零点击;画面 op 不产决策,flow/README §1 铁律) |`。

**关键取舍**:

1. **方向①(删局外决策、零点击交回)vs 方向②(保留通道 + op-layer §1.1 增补「局外兜底决策」条款 + 画面篇申报,as-built 背书)**:取①。①是铁律字面的唯一合理解——「决策的值域与节拍永远由策略器在决策时决定」,局外无策略器可调 = 零决策是该句的直接结论,方向②需为铁律新开例外条款;①族内一致(遭遇屏在先例,已核读);①生产不可达——独立跑非生产契约,为不可达路径扩正本条款 = 正本为死代码背书,且族内两态并存会让后续逐屏审查重复重裁(投资环境屏同病即同族第 2 件,统一按①收敛免逐屏补条款)。代价 = 独立跑行为面损失(见行为变化申报),而该面此前本无验收语义(裸空容器 decide_event 的输出无正本规格、无测试锁),选卡确认链 end-to-end 验证归局内实跑或 harness 测试(fixture_controller 桩 match)。
2. **早退出口用 round_success 而非 round_fail**:局外不可决策非失败(与遭遇屏「零点击终结交回重读」同语义);round_fail 会喂外环连续 fail 重派网与哨兵噪音,且局外语境下外循环重进无重观察收益(无 match 可重建),交回即终结是唯一有意义的落点。

### 2.2 F-2 处置(修订改判:销项登记,零落地面)

- **销项结论**(以修订时点工作树为真值重核):模块头「自上报统一」段现役申报 = 全族即时单相(原两相例外已全域清偿),pick_invest 面申报正确,三面互证一致——①模块头现文(:15-24);②`CwActionPickInvestOp.run` 即时单相体 + 类 docstring「即时上报」;③正本 flow/action_ops.md §4.5 :119「上报形态 = 全族即时上报……禁新增分步写法」。原报告 F-2 症状无残留,**本发现关闭**;禁按原报告症状照稿落地(照落 = 把过期申报写回现役,对已落地批构成回归)。
- **连带登记①(supply_node.md §2.4 冲突登记;归宿 = T-5 稿修订/T-37 汇总,本稿不代改)**:其目标文本「**分步欠账两行** = pick_equip / pick_planner(发射相仅意图遥测,落地相在画面 op 重入裁决出口证据闩……)」与「即时单相三线」成员集已被 T-8/T-9 落地批抛离(现役有容器写屏 = 投资两屏/补给/遭遇/策划/装备五屏,零分步两相),**禁照抄实施**;该段规格并已被 T-37 跨稿裁决作废(模块头段归口改 = T-4 修订版 encounter.md §2.3,登记见 `.debug/progress/2026-09-22-cw-screen-review/dag.jsonl` T-37 note 01:27:47)。
- **连带登记②(模块头禁形引用收回本稿 F-5 辖域)**:模块头现文含批史叙事与 design § 引用(「design.md §1.1/§1.2」「撤销 2026-09-18 动作 op 重组批 §1.1……」「迭代 2026-09-21」等),按 battle_wait.md §2.6 准则 1/2 属应清面;原「归 F-2 不另动」路由随 F-2 销项失效,收回本稿 §2.5 处置(与 T-4 修订版归口重写的协调规则见 §2.5 模块头行)。
- 依据:模块头现文逐句核读;action_ops.md §4.5 :119 与 PickPlanner/PickEquip 行现文(即时单相详注);`CwActionPickInvestOp.run` 现役体;T-37 跨稿裁决登记(dag.jsonl T-37 两条 note)。
- **关键取舍**:销项而非照原报告并入实施——设计前提被并行批更新后,唯一正确动作 = 以落地时点现状重对账(§0 真值基线条);对照过期症状「修」一遍,销项是唯一不产生回归的落点。

### 2.3 F-3 修法(三项内容,并入 T-1 统改批实施)

**归属声明**:`game_state/logic-updates/README.md` 文件统改权 = T-1 设计稿(prep.md §2.4)已认领;本稿不动该文件,以下三项为其统改的实施输入,与 T-4(PickEncounter 行 + pick 族表行集对齐)/T-5(PickSupply 行)的行级目标语义同表共存。计数类陈述沿用 T-4 F-2 已立口径:以 `operations/cw_op/cw_action_registry.py` 现值为准,不照抄任何稿面数字。

**跨稿接缝登记(与 T-1 统改批,三项)**:

1. **缺档申报联动收敛**:prep.md §2.4-1 快照括注「缺档 9 行(8 个 pick 行 + Obs 行……补篇外溢不批)」与 §2.4-6①/§2.5.2 的 `prep-executor-actions.md` §4「pick 族专篇五篇(其余行缺档,见 README 索引)」句,与本稿新增 pick-invest.md 互斥——专篇落档后 pick 缺档 8→6(13 pick 行已盖 7:encounter/supply/megastar/partner/planner 各 1 + invest 2;Obs 行不受影响),上述两处须随专篇落档同步收敛;归宿 = **T-1 统改批吸收本稿专篇信息后一次写对**(prep.md §2.4-5 跨稿承接只点名 T-2/T-4/T-5,本条即 T-6 接缝登记,待 T-1 侧/T-37 汇总双边化)。
2. **落地顺序约束**:pick-invest.md 与 README 两索引行**同批落地,或专篇先行**;禁索引行先行(防 README 先挂 `pick-invest.md` 悬空链)。
3. **行文本归一声明**:prep.md §2.4-2 已给 invest 两行档位归型(即时单相档,「整支走获得链」),与本稿 §2.3(1) 长行文本同档不冲突;落表文本**以本稿 §2.3(1) 为准**(粒度对齐同表 T-5 PickSupply 行详注形态),向 T-1 稿回写登记。

**(1)PickInvest 索引行目标语义**(事件线 pick 族表增两行;行文本机械转录自正本,非本稿新设计):

```
| PickInvestStrategy | `CwActionPickInvestOp` | [pick-invest.md](pick-invest.md) | `report_action_pick_invest_strategy_param`(即时单相:整支走获得链 `gain_invest_strategy`——无效载荷拒绝(`pick_invest_invalid_payload` 留证)→ active_strategies 按名字去重追加 → 效果账本登记腿 best-effort(失败 `gain_chain_strategy_register_failed` 不阻塞)→ `on_strategy_gained` 效果分派;reason=`gain_chain_applied`;语义单一源 = gain-chain.md §2.4) |
| PickInvestEnv | `CwActionPickInvestOp` | [pick-invest.md](pick-invest.md) | `report_action_pick_invest_env_param`(即时单相:整支走获得链 `gain_invest_env`——active_env 注册 + portal 登记 + `on_env_gained` 效果枚举;reason=`gain_chain_applied`;语义单一源 = gain-chain.md §2.1) |
```

依据:`kernel/cw_action_report/pick_invest_strategy.py` / `pick_invest_env.py` 模块头(写语义现值);`kernel/cw_gain_chain.py` 对应链函数;flow/action_ops.md §4.5 PickInvestStrategy/PickInvestEnv 两行;fields.md §3.4.4(active_strategies 写端 = 动作落地获得链)。环境支若 T-7 审查发现行为面差异,归 T-7 修订,不影响两行「同指一 op/即时上报/链式落账」骨架先行。

**(2)「handler 自管不经注册表」句删除的诉求登记**:README「词表在册、不经注册表分发」节「**7 个 handler 自管 pick 子类**(PickInvest/PickStarTome/...)由各画面 handler 自管消费链,不经注册表」bullet 整条删除——该 7 类已全部随 pick-op-unify 批收编为注册行(单一源 = `cw_action_registry.py` 现值 + action_ops.md §4.5 全表)。T-4 F-2 已主张同条整删,prep.md §2.4-3 亦已认领整行删除;本稿诉求与两者一致并入,无独立落点,不保「仅摘 PickInvest」的半删中间态。

**(3)新决策点:新增 pick-invest.md 专篇(选此案,取舍附后)**。文件 = `game_state/logic-updates/pick-invest.md`,族文件形态(两注册行一篇,先例 = tools.md「工具原子 7 行同指一 op 类」);骨架(实现者照骨架转录正本成文,无需再设计):

- **卷首**:定位(逐动作分篇;PickInvestStrategy/PickInvestEnv 两行同指一 op,族文件先例 = tools.md)+ 语义单一源声明(策略支 = gain-chain.md §2.4、环境支 = §2.1;字段级正本 = fields.md §3.4.4/§3.4.3;本篇为接线面摘要,冲突以正本为准)。
- **§1 动作是什么**:两 param 类字段(`idx`/`reason`/`norm_name` = 归一规范名);op 载体 `CwActionPickInvestOp`(机械链同构:点选中 → 0.7s → 确认,屏间差异全部经 `OverlayPickExecEnv` 显式传入);注册两行;发射位 = 投资策略/投资环境两画面 op 决策半经注册表工厂 `action_op_for` 派发(依据 = action_ops.md §4.5 两行)。
- **§2 逻辑态域集**:`active_strategies`(名单+品质,fields.md §3.4.4)/ `active_env`(§3.4.3)/ effect_inventory 登记腿(fields.md §5.1)/ chars、equips 赠卡腿(gain-chain.md §2.2/§2.3);写入口 = 两上报函数,即时单相(确认点击后一次调用写全部效果,action_ops.md §1 增补 2)。
- **§3 确定面转移规则**(策略支逐腿,一句 + 正本指针,零参数复述):无效载荷拒绝(归一后空/'?' 零写 + `pick_invest_invalid_payload` 留证)→ `active_strategies` 按名字去重追加(跳写后登记/效果腿照常,零幂等闸)→ 效果账本登记腿 best-effort(`register_strategy` + burst 桥 + 板面重写桥;`session=None` 跳过;失败 `gain_chain_strategy_register_failed` 不阻塞)→ `on_strategy_gained` 效果分派(赠卡入席腿:骇客狼 `gain_character` 链式时序 + 改件 `gain_equipment(rand=True)` 采样子链 + `on_equipment_gained` 回调);环境支按 gain-chain.md §2.1 转录。依据 = gain-chain.md §2.4 + fields.md §3.4.4。
- **§4 随机面**:链入口 `rand=False` 确定性;效果体含采样(骇客改件)对其子链翻转 `rand=True`(gain-chain.md §5)。
- **§5 拒绝语义**:无效载荷 = 链内零写 + 留证(输入拒绝,非防重复保护);重复上报 = 零幂等闸、跳写去重仅为数据卫生,bug 面按 bug 治理(gain-chain.md §2.4 腿 1)。
- **§6 kernel 符号锚**:`kernel/cw_vocab.py` 两 param 类;`operations/cw_op/cw_action_registry.py` 两行;`operations/cw_op/cw_overlay_pick_action.py::CwActionPickInvestOp`/`OverlayPickExecEnv`;`kernel/cw_action_report/pick_invest_strategy.py`/`pick_invest_env.py`;`kernel/cw_gain_chain.py::gain_invest_strategy`/`gain_invest_env`。
- **§7 语义验证**:`test_cw_yinlang_phase32.py`(即时上报/无效载荷/去重/骇客链)+ `test_cw_gain_chain.py`(链腿)+ `test_cw_unified_action_4.py`(注册表分派)。依据拆注:test_cw_yinlang_phase32.py / test_cw_unified_action_4.py = `screens/invest_strategy.md` §9 在册申报;test_cw_gain_chain.py 实存依据 = T-6-r1 报告 §3.7(§9 测试锁清单未列——附带诉求登记:`screens/invest_strategy.md` §9 测试锁清单补该文件一行「获得链锁」,随本稿 invest_strategy.md 文档批一并落,见 §2.6 总表)。

**关键取舍(专篇 vs 修订规则豁免「投资两屏索引行直指 gain-chain.md」)**:取专篇。①「一行一文件」是 README 自立的完备性保障(每个注册动作在执行纪律域有语义落点),为单一家族修订规则 = 正本规则开口,后续同类链式落账动作出现时归属歧义;豁免案还需动 README 总则段映射粒度措辞,超出索引行修正的最小面。②族文件先例在册(tools.md),两行一篇不破规则。③T-4 已将 pick-encounter.md 改写为全形专篇,同族同形状降低后续审查与维护成本;索引行落点留在 logic-updates 目录内,目录自足。④双抄本漂移风险以「接线面 only + 单一源声明」对冲——专篇零复述链参数细节,四腿各一句 + 指针,二抄本面收缩到低频变更的接线事实(发射位/域集/符号锚);代价 = 多维护一个薄文件,可接受。

### 2.4 F-4 修法(screens/invest_strategy.md 三节同步 + 坐标全形;零代码变更)

**§4 决策体图**——在「逐卡刷新」分支闸 3 行之后、「点刷新钮」行之前插入目标文本:

```
│    三闸全败(建议帧但无槽可执行)→ 同访问重调一次落选卡:
│      策略侧同帧去重(scratch 键 = (kind, 候选元组):建议帧首调发建议、
│      紧随重调落选卡,零选卡漂移;依据 = strategies/impl/flow.py::
│      _decide_invest docstring、strategy-docs/13_pick_family.md §1 invest
│      行「重决策仍经本入口」;重调发生在任何刷新执行之前、零新事实,
│      不触 op-layer.md §1.4「禁重调决策」的刷新链禁令——在册形态非违例)
│        重调返回选卡 → 落「选卡确认链」分支;
│        重调仍返回刷新(策略器未实现去重 = bug 面)→ act=None
│          → 汇入「决策无有效选卡输出」round_fail 显式失败(单次重调,
│            零二次重调零循环,对照 encounter.md §4 同款申报口径)
```

**§4 坐标引用补全形**(screens/README.md §2 纪律「坐标一律 `画面名.area名`」):①「点『刷新次数N』文本锚 + 固定偏移」→「点『货币战争-投资策略.区域-刷新次数行』OCR 命中文本中心 + 固定偏移 `_REFRESH_BTN_DX`(-88, safe_click)」(该 area 为计数行 OCR 带,依据 = `obs/cw_node_obs.py::read_invest_refresh_counts` 的 screen_info 单一真相源注);②选卡派发行「定位点 = 「区域-卡名行」center[兜底常量] + 该卡 center-x,确认钮 = 「按钮-确认」center[兜底常量]」→「定位点 = 『货币战争-投资策略.区域-卡名行』center(缺失兜底常量 `CARD_CLICK_Y`)+ 该卡 center-x,确认钮 = 『货币战争-投资策略.按钮-确认』center(缺失兜底常量 `CONFIRM`)」。

**§5 终结表补行**:`| 三闸全败重调仍返回刷新 | 显式失败 | round_fail(「决策无有效输出」同出口;策略器同帧去重未实现的 bug 面响亮暴露,零二次重调) |`。

**§8 守卫与防线补条**:`- 同帧去重契约(三闸全败重调):重调仍返回刷新 = 策略器未实现去重的 bug 面 →「决策无有效选卡输出」round_fail 显式失败;去重单一源 = 策略器(flow.py::_decide_invest scratch 键),画面 op 只重调一次、重调仍刷新即弃,零循环。` 原「空候选/决策无有效输出」条不动(重调仍刷新汇入该出口,两表行互指)。

**关键取舍**:申报照实现写(单次重调 + 防御弃权 act=None),不引入「循环重调直到出选卡」之类新语义——as-built 义务是申报现役,不是 redesign;测试面零新增(该分支为文档缺口非行为变更,现役锁 `test_strategy_refresh_terminal_handback` 的 decide_calls==1 断言辖正常帧,不受影响)。

### 2.5 F-5 修法(辖域三文件注释卫生,准则与清单)

**清理准则**(沿用 = battle_wait.md §2.6 五条,本稿不重立):禁形一·会话局部标识符(W 轮次号/审计轮次号 rN/task#N/T-N 任务号/局N 单局指称/指向迭代过程件的 design § 引用);禁形二·变更史叙述(何时改的/从什么改成什么/勘误过程);改写方向(收敛为「结论→出处→边界」当前时态,裁定语义保留可指正本条款);保留豁免(ADR 引用、「N 局实证」类纯语义、退役申报史注句式〔细化见 prep.md §2.5.3 准则③:指称退役机制本身可保留,禁写成现役指向〕、screen_info 坐标与兜底常量定义注);一次成文(模块头段与 T-37 归口重写同段交叠处只落一次,协调规则见下表模块头行)。判据细化一条:「N 局实证/实跑暴露」= 统计语义豁免;「局N」= 指称某一次具体对局的编号,禁形。

**命中面与处置**(报告命中点逐条核读后的全集;行号为定位辅助):

| 文件 | 点位 | 处置 |
|---|---|---|
| `cw_screen_invest_strategy.py` | CARD_CLICK_Y 注释块(:107-111,I16 勘误史 +「旧 doc 均过时」对照) | 准则1/2:I16/「↺ 推翻」/旧 doc 对照清出;保留当前语义(选中点击 = 卡名行 y≈474,白边 + 确认亮;点卡底/描述区不选中 → 确认灰置 → 整局阻塞风险),出处改纯语义(「实机点验:点卡名 → 白边选中 → 确认推进」);兜底常量与 area_center 首选关系保留 |
| 同上 | 「task#20」(:117) | 准则1:编号清出;保留「确认按钮:screen_info『按钮-确认』center;常量=兜底」 |
| 同上 | 「三审 off-by-one」(:186-188) | 准则1:审查轮次号清出;保留判定语义(末次复探结果必须消费:循环内 if 只判上一轮采样,锚恰在窗口末拍出现仍会误报失败) |
| 同上 | 模块 docstring(「visit 起点单点复位已随防重入宿主退役」「验效双通道已拆除(用户裁定 2026-09-10;2026-09-14 收敛为零比对)」) | 准则2:前者整句删(现役无此机制,纯退役申报);后者收敛为当前时态「访问内刷后零比对(刷后不重读不比对不重决策)」+ 指正本 op-layer.md §1.4;「(投资两屏迁移批)」批名标签保留(裸批名豁免,见下) |
| 同上 | ENTRY_REPROBE_* 注(:119-126,「旧实现单探测 miss 即 round_fail……修法(复探=短窗+新截图)」对照叙事) | 准则2:旧实现/修法对照收敛为当前机制语义(首探 miss → 短窗复探,窗口内命中即继续;超窗 round_retry,防无限等真非目标屏);ADR-0529 引用与「20/21 局」实证描述保留(豁免) |
| `cw_overlay_pick_action.py` | 模块头(:1-29,禁形引用;自 F-2 销项收回本节处置) | 准则1 清出:「design.md §1.1/§1.2」(:1-3)、「撤销 2026-09-18 动作 op 重组批 §1.1『零上报例外登记』」(:15-16)、「(迭代 2026-09-21,……)」迭代名指针(:21-22,裁定语义由 action_ops.md §1 增补 2 指针承载);保留:全族即时单相现役语义(零改动)、「原『发射/落地两相』例外已随……全域清偿」退役申报史注句式(prep.md §2.5.3 准则③:指称退役机制本身,可保留)与批名标签。**与 T-37 归口协调**:该段申报文本归口 = T-4 修订版 encounter.md §2.3(T-37 登记,supply_node §2.4 段规格作废),本节只清禁形引用不动申报口径;若归口重写先落盘,本面以其落点对账、已清则销项,禁双写(一次成文) |
| 同上 | 「task#103 化债,W265」(:281) | 准则1:编号清出;保留「确认钮中心从 screen_info 读;缺失兜底常量」 |
| 同上 | 「r327 终审 E」(:372 docstring / :409 注)、「局29」(:398)、「r326/P1⑦」(:407) | 准则1:编号清出;周边语义不动(裁决词全词/避开详情按钮区选中点/防线归属句——策划类语义本体归 T-10 辖域,本稿只清编号) |
| 同上 | 六类 docstring「pick-op-unify 批收编」(:494/:539/:583/:625/:668/:704) | **豁免保留**,并修正报告命中记录:核读证实代码侧**无**「…,T-3」任务号(六处均为裸批名);「T-3」编号实存面 = flow/action_ops.md §4.5 行文(正本文档,非代码注释面)——登记联动面,处置归正本维护/汇总批 |
| `kernel/cw_action_report/pick_invest_strategy.py` | 模块头「自 pick_invest.py 拆分(投资两屏迁移批……)……原『发射相意图遥测/落地相证据闩』分步上报随拆分废除」段 | 准则2:拆分史整段删;保留「即时上报形态」段(申报正确)+「本包 → 容器单向依赖」句——目标尾形 = 「……正本 = game_state/gain-chain.md)。本包 → 容器单向依赖。」 |

**豁免面全集**:ADR 引用(ADR-0132/0529/0600);「20-22 局实证」类纯语义描述;裸批名出处标签(pick-op-unify 批/投资两屏迁移批,判据 = supply_node.md §2.7 收敛判据:非过程件指针、非叙事句);screen_info 坐标/兜底常量/日志 tag 的定义注释(AGENTS §8 字段坐标系与取值时机语义)。

**实施规则**:准则做三文件全文件扫描,上表为已核对点位、非穷举;与全仓注释卫生批(建议中)合并执行亦可,同段一次成文。**同族联动面登记(不扩改)**:`pick_invest_env.py` 模块头 :8-9 同款拆分史(归 T-7);`flow/action_ops.md` §4.5 三行「…,T-3」任务号(正本文档面,归正本维护);`cw_overlay_pick_action.py` 内 supply/planner/equip 类注释的 design § 引用(:231/:272 归 T-5 F-7 补给链辖域;:420 planner、:124 env 数据类「银狼闭环 design」腿型注归 T-10;:612 equip 归 T-9)——均不在本稿三文件禁形清单内,随各屏审查/清理批处置。

**验证门**:三文件按准则 1 禁形模式(task#/W 审计轮次/r 审计轮次/T-N 任务号/局N 单局指称/迭代件 design § 引用)grep 零命中(豁免面除外;`cw_overlay_pick_action.py` 模块头内他屏类 design § 引用按联动面归属剔除);`uv run ruff check` 通过;`git diff` 确认零逻辑改动。

### 2.6 落地文件面总表(合并实施对账用)

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `operations/cw_screen/cw_screen_invest_strategy.py` | F-1(局外早退 + import 清理)+ F-5 注释卫生 | 行为变更(仅 F-1)+ 注释 |
| `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py` | F-1 补一锁(局外零决策交回) | 测试 |
| `operations/cw_op/cw_overlay_pick_action.py` | F-5 注释卫生(编号命中 + 模块头禁形引用收回处置,§2.5;与 T-37 归口协调规则同见 §2.5) | 注释 |
| `kernel/cw_action_report/pick_invest_strategy.py` | F-5 模块头拆分史段删除 | 注释 |
| `docs/.../screens/invest_strategy.md` | F-1(§4/§5)+ F-4(§4/§5/§8)+ §9 测试锁清单补 `test_cw_gain_chain.py` 一行(§2.3 ③ 附带诉求) | 画面篇 as-built |
| `docs/.../game_state/logic-updates/pick-invest.md` | F-3 ③ 新增专篇(落地顺序约束见 §2.3 接缝登记 2) | 正本新增 |
| (登记面)`docs/.../game_state/logic-updates/README.md` | F-3 ①②(统改权 = T-1;行级目标语义 = 本稿 §2.3;接缝三项 = §2.3 跨稿接缝登记) | 登记面 |
| (登记面)supply_node.md §2.4 目标文本冲突、T-37 模块头归口(T-4 修订版 encounter.md §2.3) | F-2 销项连带登记(§2.2) | 登记面 |
| (登记面)`cw_screen_invest_env.py` 局外分支、`pick_invest_env.py` 拆分史、`flow/action_ops.md` §4.5 任务号、`cw_overlay_pick_action.py` 内他屏类 design § 引用 | 同族联动面(归 T-7 / T-5 F-7 / T-9 / T-10 / 正本维护) | 登记面 |

其余文件零触碰;F-1 之外全部零行为变更(纯文档/注释);F-2 = 销项零落地。
