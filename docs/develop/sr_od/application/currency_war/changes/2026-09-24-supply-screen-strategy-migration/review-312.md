# 补给屏策略层迁移 实现提交面对抗审查(review-312)

- 审查对象:主仓 `f07ba95ca`(feat/mcp-backend-sync2 分支头,8 文件 +319/-104)、测试仓 `74683322`(3 文件 +354/-3)。
- 规格单一源:同目录 design.md §2.1-§2.6、landing.md 首节通用工程门 + 3.1 凭据①-⑨ + 3.2 三段式 grep 验收与白名单。
- 审查方式:`git show` 两仓逐 hunk 亲读,每个 hunk 直调代码体核对(docstring 仅作线索);测试/锁做变异推演;三段式 grep 复跑;ruff/pytest 实跑。
- 结论:**通过(无返工项)**。发现 1 中 3 低,全部为锁面覆盖缺口与注释精度问题,不涉行为错误;三项仲裁均为「维持」。

---

## 1. 发现清单

### F1 [中] 两账口径的「穿戴账」半边无行为锁
- 位置:`sr-od-test/test/sr_od/application/currency_war/test_cw_supply_decision.py`(凭据④ 段,`test_demand_counting_and_component_upgrades_two_accounts`)。
- 内容:design §2.2 第 3 级明定 `owned_total` = spare + **行域/备战席穿戴账**(`deployed_rows_of` + `bench_units_of` 成员 equips 透传)。现有全部用例只经 `_set_equips` 构造备用账(`gs.equips`),行域/备战席单位的 equips 恒空——变异推演:`_two_accounts` 丢穿戴账透传(或 `owned_total` 恒传 None 回落 spare),32 锁全绿。landing ⑦ 只钉死了凑星轴的 deployed 展平,装备轴两账的另一支漏锁;「上阵已穿 1 件直击件 → 需求是否已满足」这条生产行为无回归网。
- 修正方向:④ 补一条「备用空 + 上阵/备战席穿戴有」的构造,两账缺一即红。例:key=[X,Y]、`gs.equips` 空、上阵单位穿 1×X → X 已满足(tier 0)、Y 未满足(tier 3)胜出;或反向:key=[X]、上阵已穿 1×X → X 不再直击。注意锁点选「备用与穿戴互补」的帧——「`owned_total=None` 回落 `owned_spare`」的变异在备用账独扛的帧面与正确实现同值,测不出。

### F2 [低] op 内联注释残留不可达触发面「读缺」
- 位置:`operations/cw_screen/cw_screen_supply_node.py:285`。
- 内容:「本面 = 读缺/锚点缺对照兜底」。闸内嵌 decide 后,刷新建议蕴含 `supply_refresh_left ≥ 1`(op 同帧同容器读),对照闸拒绝仅剩 `_refresh_point is None` 一种触发面;design §2.6 明言「读缺分支……不可达」,模块 docstring(:21「锚读缺」)与同函数下一条注释(:288「刷新锚点缺失面」)均已按此收口,唯 :285 残留旧二元面表述。
- 修正方向:「读缺/」二字删去。

### F3 [低] survey19 模块头括注含变更史表述
- 位置:`kernel/cw_survey19_hooks.py:9-10`。
- 内容:括注「(P8 补给重刷判据已删:……;考古走 git 历史。)」——「已删」「考古走 git 历史」是变更史表述(项目规范:变更史归 git 历史,注释只留当前值成立的理由 + 指针)。模块头随删件改写本身是 design §2.6 规定动作,括注里的单一源指针(策略层 supply.py)有当前态价值;同批 `cw_events.py` 模块头的同款改写即为纯当前态表述(「补给选卡决策不在本模块……仅留观察载荷契约」),可对照。
- 修正方向:括注收敛为纯当前态(如「补给重刷判据单一源 = 策略层 supply.py」),去掉过去时与考古指引。

### F4 [低] 刷新判据「无带钻」合取支无独立锁
- 位置:`test_cw_supply_decision.py`(凭据⑤ 段)。
- 内容:现锁的刷/不刷帧全部无钻。变异推演:删 `decide` 的 `not diamonds` 守卫,①多钻帧 left 未构造(None → 内层次数闸 fail-closed 不刷,不红)、⑤/⑧ 帧无钻——全绿。即「带钻帧永不建议刷」这条合取支无回归网。
- 修正方向:⑤ 补一条「单钻 + 非终局成员 + 非 key 件 + left=1 → `SupplyDecision`(带钻 idx)」断言:现实现落选卡,删守卫后返刷新建议即红。

### 表述性备注(不计发现)
- `test_cw_supply_decision.py` 文件头自述「不断言 reason 全文」,⑨ 断言 `reason == 'no-options'` 全文——该字面为 design §2.2 明文规定(「与旧码同形」),断言合法;仅文件头纪律句过宽。
- supply.py `_can_merge_star` 参数注解为裸 `list`(语义靠 docstring 补足),ruff 不拦;项目惯例偏好参数化泛型,顺手项。

---

## 2. 三项仲裁

### 仲裁 a:29 批落地行号漂移,worker 按符号定位删除 —— **裁决:通过,删除面无缺漏、无误删**
- 符号定位核验(HEAD 现址):`SupplyOption` :165 四字段完整(idx/char/equip/has_diamond),docstring 两句旧决策语义(「钻 = 拿到基本赢,碾压一切」「key_equips 契合 + 通用价值排序用」)已按 §2.6 改写为载荷契约描述(「三钻检测集单一源 = cw_node_obs.DIAMOND_EQUIP_NAMES」「OCR 原文,未归一」);`_equip_value` :180 完整保留、体内仍委托 `equip_generic_value`,消费点 :294/:322(planner 装备档回落打分)在产——两处「必须保留」项均完好;`EVENT_PICK_TYPES` :538 四类(SupplyPick 位已除)、`EventPick` :543 四类联合(别名位已除)。
- 删除面三词 grep 实跑:`decide_supply` / `SupplyPick` 在 src 与 sr-od-test **全零命中**;`supply_reroll_decision` 在 src/docs/skills/tools/sr-od-test **全零命中**——物理删除无墓碑成立。
- worker 申报的旧实址(decide_supply :190-221)与 pre-commit diff hunk(`@@ -170,57 +177,12 @@` 内)吻合;漂移属实(现 cw_events 543 行),按符号落批操作正确。
- 逐 hunk 亲读 8 文件:删除集恰 = design §2.6 清单(decide_supply 体 + SupplyPick + 段头注释 + 元组位/联合别名位 + supply_reroll_decision + 旧 +10/key_fit 隶属判据),无集外删除、无误删保留项。

### 仲裁 b:`test_cw_unified_action_4.py:303` SupplyPick 构造替换为 `CwActionPickSupplyParam(idx=0)` —— **裁决:维持(忠实于锁意图,非洗白)**
- 该锁(`test_supply_pick_op_clicks_target_and_confirms`)锁的是 `CwActionPickSupplyOp` 的机械行为(点目标卡 + 确认调用),断言(`clicks == [(500,400)]`、`confirm_calls` 三元)**一字未动**,无任何弱化——洗白的构成要件(松断言/换检查对象)不存在。
- op 构造注解 = `param: CwActionPickSupplyParam`(cw_pick_supply_action.py:49):旧构造 `SupplyPick(idx=0)` 对该注解本就是鸭子式错型,新构造是**类型修正**且更贴生产实态(flow 现役喂 `CwActionPickSupplyParam`)。
- design 原文「实例构造点随删」按字面执行(删构造行)必然连带废掉整条测试,与该机械锁的在册价值(op 层「零行为改动」申报正需要这条回归网)冲突;替换构造载体是「删除 SupplyPick 符号」这一删除面意图的最小忠实执行,SupplyPick 符号在两仓已零残留。
- 一点措辞备注:测试仓 commit message 写「构造点随删」,实为「构造点换载体」,措辞略不精确;代码与申报意图无出入,不构成返工项。

### 仲裁 c:`flow.py::_decide_invest` docstring 一句 —— **裁决:属实注释失真修正,无夹带行为变化,维持**
- 该句宿主 = `_decide_invest` docstring(flow.py:449-454),原文「supply/encounter 等 pick 族消费面不变」断言 supply 仍消费 `target_comp`——本 commit 恰把 supply 消费面改挂 ist(`get_comp` 解析后传 comp 对象),该句随本 commit **即时失真**,不修则留下刚写成的假话;修正句与 :583-589 实码逐点吻合。
- `git show` 核实:该 hunk 仅此一句注释,零代码行变化;本 commit 无其他集外注释/代码夹带(8 文件逐 hunk 过)。
- 流程面建议:该句位不在 design §2.6 收口清单内,属「接线自致失真的必要同步」——后续迭代把「本 commit 使哪些既有注释句为假」预登记进注释收口清单(本批清单按「待删件的既有失真」组织,未含自致失真位)。

---

## 3. 忠实性逐条核对(design §2.2-§2.5,全部达标)

| 规格条 | 实现证据(supply.py 除非另注) |
|---|---|
| 空候选帧 idx=0 no-options | `decide` 首行;⑨ 锁断言 |
| ①钻级:单钻直选;多钻细分进角色/装备轴 | `diamonds` 池 + `pool = diamonds if diamonds else options`,细分复用 2/3 级机器;①锁覆盖单钻/多钻角色细分/多钻装备定序 |
| ②角色级:locked_comp 非 None 激活 | `_endgame_chars`:None 或 demoted → None(空转) |
| core∪shared、不含 transition | `frozenset(core_chars) \| frozenset(shared_chars)`;transition 不入 |
| get_comp 空串无告警 / 失败告警 | flow.py:582 `if _ist.locked_comp:`(空串短路无告警)/ :584-587 解析失败 `log.warning`;flow 接线锁第三帧锁「不存在的套名 → 未锁口径」 |
| 凑星 tiebreak = `same_star_count(char,1,bench,deployed)==2` 且 deployed 展平 | `_can_merge_star` + `_pick_char_level` 内 `front, back = deployed_rows_of(gs); deployed = (*front, *back)`;`_entry_identity` 对二元组返回 None(fail-closed)的语义已亲读核对,⑦ 锁含分跨域构造 + count==1 阴性对照 |
| ③装备级直调 `pick_equipment`(禁第二套) | 2/3 级均直调;`equip_tier` 仅用于 reason 归因串,不参与排序;`pick_equipment` 实码 = (tier, generic_value) 字典序、并列取输入序先(亲读核对) |
| 两账 owned_spare=gs.equips / owned_total=spare+穿戴 | `_two_accounts` 与 `flow.decide_box_card`(:758-779)逐行同口径 |
| ④刷新:三级全空才刷(读法 A 只看档位)+ 闸内嵌读 `gs.supply_refresh_left`(None fail-closed) | `not diamonds and not char_pool and _all_tier_zero(...)`;`_all_tier_zero` 只调 `equip_tier` 不看通用值;`left is not None and left >= 1`;Field[int] 类型亲核(无需 int() 强转);⑤ 锁含读法 A 专用帧 |
| flow 接线:空串 None 无告警/失败告警/`_consume_prep_direction_frame` 保留/refresh_used 预计算删除 | flow.py:577-592(内务 :579 保留;`_left`/`refresh_used` 两行已删);RefreshSuggestion→RefreshParam、Decision→PickParam 包装正确 |
| sim 盲区申报链 | 亲核属实:`_sup_opts` 唯一写点 :221 在 live 读链内,sim 装配下 `sim_or_live_observation` 直返 `_BACKEND.observe(...)` 不执行 live_read → :257 门恒空 → CARD_BODY 兜底;申报「新旧在 sim 中读数恰同」成立 |

行为变化申报①-⑤与实码一致;依赖方向 strategies→kernel 单向成立(kernel 改动文件无 strategies import,grep 命中均为注释文本)。

## 4. 行为锁质量(landing 凭据①-⑨ 逐锁三问)

| 锁 | 锁语义? | design 可独立推导? | 变异敏感?(推演) |
|---|---|---|---|
| ① 单钻支配/多钻细分 | 是(idx 结果) | 是(§2.2 第 1 级) | 删钻支配→②帧红;删钻内角色细分→红钻/蓝钻表外 0 值同分取输入序先→idx 0 红(**具判别力**,价值表亲核) |
| ② 成员卡压高装备卡 | 是 | 是(字典序轴间不可补偿) | 删角色轴→key 直击胜→idx 1 红 |
| ③ 空转帧 | 是,含锁线对照帧 | 是(§2.2 激活条件+防御位) | 降格位失效→对照帧同断言冲突红;解析失败帧由 flow 接线锁兜住 |
| ④ 需求计数/组件升档 | 是(已持够数降档+近兑现) | 是(§2.2 第 3 级) | 回退旧 +10 隶属→case1 红;丢备用账→case2 近兑现退化→红;**穿戴账支无锁(F1)** |
| ⑤ 三级全空才刷+fail-closed | 是(含读法 A 专用帧) | 是(§2.4) | 读法 B(看通用值)→高通用值帧红;left 缺/尽构造红;**「无带钻」支无锁(F4)** |
| ⑥ 席满无特殊分支 | 是(负向锁:无席满分支) | 是(§2.5 席满口径) | 只防「新增分支」类变异,按凭据⑥ 定义执行 |
| ⑦ 凑星分跨域 | 是(正是 landing ⑦ 要求的展平钉死构造) | 是(§2.3) | 二元组直传(漏上阵域)→count=1→idx 1 **红**;tiebreak 误用 ≥1→阴性对照红 |
| ⑧ P1 配方锁帧 | 是(刷+刷尽落选卡两态) | 是(§2.6 申报⑤) | 闸失效→left=0 帧红 |
| ⑨ 空候选帧 | 是(design 明文钉死字面) | 是 | 返回契约变更即红 |
| flow 接线锁 | 是(真 bridge→flow→supply.decide 链,非 stub 自测) | 是(§2.5) | 装载错型/解析丢告警路径→对应帧红;测试直调疑虑不成立——`MandateV1Strategy` 为生产类,意向注入缝(`state.v3_intention`)与 `_ensure_intention` 读缝亲核一致 |

测试纪律:零真实副作用(自造 gs + `write_logic` 独立容器 + 提交进仓的注册表数据)、无源码扫描、无 ≥2s 慢用例(三文件 32 passed,4.4s)。

## 5. 白名单 grep 复跑(landing 3.2 三段式)

- `decide_supply`:src 7 命中,全部白名单内(op docstring ×3 + `match.strategy.decide_supply()` 合法调用点 ×2〔:280/:286〕+ `cw_strategy.py:173` ABC 声明 + `flow.py:569` 入口)。
- `SupplyPick`:src 与 sr-od-test 双仓**零命中**。
- `supply_reroll_decision`:src/docs/skills/tools/sr-od-test **全零命中**(物理删除无墓碑)。
- docs 面 `decide_supply` 命中全部落白名单类:changes/ 历史工件(多迭代)、`flow/README.md:81`(存活指称,入口名仍真实)、3.3 前待收口 docs(screens/supply.md:3/:12/:39、strategy-docs 13 号稿 :20 / 16 号稿 :74、docs/game 两画面文档)——与 landing 3.2 白名单逐类吻合,**白名单外零命中**。
- kernel→strategies 零 import 方向成立(命中均为注释文本)。

## 6. 规范面

- ruff:8 个改动文件实跑,`All checks passed`(本审查复跑,非仅采信申报)。
- 测试实跑:三个受影响文件 32 passed;L1 全量(`-m "not slow"`)复跑通过(见 §7)。
- commit 拆分:主仓单 commit 文件集 = landing 3.1 文件面(supply.py 新、flow.py)∪ 3.2 文件面(cw_events/cw_survey19_hooks/cw_vocab/cw_pick_supply_action/cw_screen_supply_node〔仅注释〕/cw_node_obs〔仅注释〕)恰 8 文件,符合 3.1「入库豁免、随 3.2 一并提交」的原子切换申报;测试仓单 commit 3 文件 = 申报面(step3 docstring 注记、新锁、unified_action_4 两处)。两仓 `git show --stat` 均**无集外文件**。
- op 层零行为改动申报核实:`cw_screen_supply_node.py` diff 中决策/闸/重调代码行全部为上下文行,变更仅 docstring 与注释。

## 7. 实跑记录

- `uv run pytest test_cw_supply_decision.py test_cw_obs_arch_event_screens_step3.py test_cw_unified_action_4.py -q` → **32 passed**。
- `uv run ruff check <8 改动文件>` → All checks passed。
- L1 全量:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow" -q` → **1125 passed**(30.9s,exit 0)。

---

## 8. 修复抽检(主仓 b90b12746 + 测试仓 027ccef0)

抽检方式:两 commit 逐 hunk 亲读 + 现址早退顺序直调 + 两处变异独立复证(临时改 supply.py 后还原,`git diff` 空 = 零残留)。

- **F1**:`test_demand_counting_and_component_upgrades_two_accounts` 增穿戴账互补帧(key=[火力风暴潮,反重力皮靴]/备用空/上阵穿 1×火力风暴潮,断言反重力皮靴 tier 3 胜出)。变异复证:`_two_accounts` 返 `(spare, spare)` → **仅该帧红**(火力风暴潮被误判 tier=3 直击,assert :197),其余 9 锁绿——构造即「备用与穿戴互补」形态,`owned_total` 回落 owned_spare 的变异同样被测出,符合 §1 F1 修正方向。
- **F4**:⑤ 增多钻帧(红钻+三月七/蓝钻,均非成员非 key 件,left=1,断言 Decision idx=0)。变异复证:删 `not diamonds` 守卫 → **仅该帧红**(误返 SupplyRefreshSuggestion,assert :237),其余 9 锁绿。
- **F4 偏差仲裁**:worker 机制说明**属实**——现址 supply.py `decide` 中 `len(diamonds)==1` 早退(:115)先于刷新闸(:126),单钻帧到不了闸面,原 F4 修正方向所举「单钻+left=1」构造确实无判别力;worker 改用多钻构造(唯一能穿过第 1 级、抵达闸面的带钻形态)且帧内角色均非终局成员(隔离出「无带钻」单个合取支),**达成锁意图**。该偏差 = 对本审查修正方向的必要纠偏,非洗白。
- **F2**:cw_screen_supply_node.py:285 改「刷新锚点缺失对照兜底」单支表述 ✓。**F3**:survey19 模块头改纯当前态(「不在本模块:单一源 = 策略层 supply.py」),去「已删/考古」✓。**备注 a**:文件头纪律句收窄为「reason 仅断言 design 明文指定的字面(⑨ no-options)」✓。**备注 b**:`_can_merge_star` 注解参数化(`bench: list[Unit]` / `deployed: tuple[Unit, ...]`,与调用实形吻合),Unit 显式导入 ✓。
- 提交面:主仓 3 文件 +6/-5、测试仓 1 文件 +30/-3,均与申报一致,无集外文件;commit message 引 review-312(仓内持久文件名,合法索引)。
- 复跑:还原后三受影响文件 **32 passed**、ruff 3 文件全过、L1 全量 **1125 passed**(30.0s);supply.py `git diff` 空 = 变异零残留。
- 抽检结论:**通过,无返工项。**
