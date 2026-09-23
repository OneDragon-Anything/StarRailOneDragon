# T-17 商店框开店 修法设计(op_open_shop)

## 0. 元信息
- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决+坐标规范增补待裁决(对抗轨迹:r1 未收敛 5 条→修订→r2 未收敛 3 条→修订→r3 收敛 0 条;坐标增补节定点对抗(`.debug/progress/2026-09-22-cw-screen-review/reviews/coord-attack-T15-16-17.md`)未收敛 6 条低(本稿 A-4/A-5/A-6)→按攻击结论修订 §4[A-4 商店域站点全集 3→5 补两转换函数 docstring + vocab legacy x 注显式豁免;A-5 批1 两义务补录('shop' 域版本 bump + sim 不建模)进 §4.1 与 T-37 登记行;A-6 pick 类计数 12→11],状态维持待用户裁决)
- 审查依据:F-1..F-3 编号与差距认定 = `.debug/progress/2026-09-22-cw-screen-review/reports/T-17-r1.md`(总判定「有问题(高0 中1 低2)」);本文逐条回应
- 对抗修订:`.debug/progress/2026-09-22-cw-screen-review/reviews/T-17-attack-r1.md`(A-1..A-5;r2 复核四条实质解决)与 `reviews/T-17-attack-r2.md`(N-1..N-3)已逐条处置;处置落点 = §1.2 与 §2.2 不解决节(A-1/A-5 证据改述与计数口径)、§2.1 修法 B 插入文本与依据②(A-3 正本文本;N-1 宿主封闭清单)、§0 时点关系行与 §2.4 在册段(A-2 交叠申报;N-1 直调宿主面收缩申报、A-4/N-2 搁浅兜底按读点类别拆分)、§2.4 T-37 登记条目(N-1 条目 5、N-2 条目 1)、§2.4 验证门 2/3(N-3 词表 R2 裸 token、N-1 宿主清单 grep 门)
- 口径:代码锚 = `文件::符号名`,路径根 = `src/sr_od/application/currency_war/`;文档路径根 = `docs/develop/sr_od/application/currency_war/`;行号 = 审查时点快照仅供对照
- 时点关系(申报):在飞迭代 `changes/2026-09-21-shop-refresh-terminal/` 与本稿**代码文件面零交叠**(其 landing 3.4 文件面不含 `cw_op_open_shop.py`);文档面 `screens/op-layer.md` 为共同编辑文件但**编辑区不交叠**(本稿 §1.1 vs 在册 §3/§1.4/§4/头注计数),token 级不同条目可合流、后落批对账(细则 = §2.4)。其 landing 3.4 退役 `CwOpCloseShop`/`close_shop` 并明确保留 `open_shop(self)` 显式开店直调点(details/shop-visit-loop.md §2.2「幂等,不变」),同时仲裁段直调点(`cw_loop.py::_launch_frame_arbitration`)随仲裁段整段退役出清——直调宿主面收缩申报 = §2.4;对 F-1/F-2/F-3 各自的影响见 §2.4
- 本稿辖面 = F-1..F-3;审查报告 §3 已核对一致面(词表登记/terminal 承载行/两条开店路径归属/上报分工/shop.md as-built/零策略器问询等)不立修法,本稿不动

## 1. 问题与动机

### 1.1 F-1(中)画面 op 未登记读屏点(act node 冗余现取 + 直调形态不在册)
- 现状症状:`operations/cw_op/cw_op_open_shop.py` 两处读屏形态。①两 node 形态 `CwOpOpenShop.act` 点击瞄准行(L129-130)调 `self.screenshot()` 现取帧——同轮 node runner 已给新帧(`screenshot_before_round` 缺省 True,`one_dragon/base/operation/operation_node.py`),同函数重入裁决(L126)与观察 node(L112)均已用 `last_screenshot`,此处再取 = 同轮第二次截图。②直调形态 `open_shop(op)`(L67/L70)两处 `op.screenshot()`——生产直调点两处,宿主 op 同为 `CwScreenPrep`:`operations/cw_screen/cw_screen_prep.py::CwScreenPrep._open_shop_phase`(:959,显式开店路径)与 `operations/cw_loop.py::_launch_frame_arbitration`(:550,发射帧仲裁段;入口 = restricted_spend 截流分支 `cw_screen_prep.py` :822-837,注释自述「意图化仅换宿主,函数原样复用」)。两语境同为 bare-loop、宿主帧取自节点轮首、环内前序动作已改屏,现取帧为瞄准结构性必需,但该形态不在例外清单。
- 规范条款:`screens/op-layer.md` §1.1「显式读屏只在观察 node……除观察 node 外,画面 op 内不调 screenshot()。在册例外只有两类……新增读屏点必须先登记本条再落码;除上述两例外,其余路径零读屏」。
- 根因归层:约定层(读屏点登记纪律的封闭清单被绕过——两 node 形态属冗余现取、直调形态属漏登记;非决策越权、非行为性违规,审查判「契约面不一致」中)。
- 解决到哪:两 node 形态读点消除(act 改用 runner 帧,修后全程零现取);直调形态按登记纪律扩登 §1.1 例外(一次性登记、条件收窄、成员封闭集);同族残留登记分流(§2.4)。
- 明确不解决:直调形态帧新鲜度与 `SHOP_OPEN_ANIM_S` 动画窗的实机时序验证(报告 §4 无法核对面,静态审查不判时序);`operations/cw_op/cw_op_settle_confirm.py::CwOpSettleConfirm.confirm` 读点(非本审查对象,登记归属待裁);`operations/cw_op/cw_op_close_shop.py` 读点(随在册 3.4 整文件退役自愈)。

### 1.2 F-2(低)注释出处形态违 AGENTS §8(会话局部标识符/悬空 ADR/变更史时态)
- 现状症状:本文件九站点(逐站点替换表见 §2.2)——`R2 §3.2.5`/`渠道②`(L17)、`ADR-0634`(L21;ADR 文件本体不存在 = 引用悬空:仓库无 `decisions/` 目录;但「唯一提及在 changes/ 工件」为误——持久代码即有同标签共现 32 处(`kernel/cw_state_journal.py` 模块头/`kernel/cw_game_state.py`/`obs/cw_observation.py`/telemetry 族/`prep_actions.py` 等,已列 §2.2 同族清单),悬空认定本身不受影响;审查报告 F-2 同句同误,汇总批对报告修订自裁)、`总纲契约 1`(L43)、`W970 批 A 契约 §4.2`(L49)、`W970 §4.2 F7`(L55)、`M1③`(L59)、`不再验「收起出现」`(L59,变更史时态)、`R2:`(L64)、`审计 P0 同型`(L76/L134)、`W970 批 A;`(L84)。
- 规范条款:仓库根 AGENTS.md §8「注释禁会话局部标识符(W 轮次号/rN/批N/[N] 等);出处要么持久索引(ADR-NNNN、文件路径、符号名)要么纯语义描述;变更史不进注释」。
- 根因归层:表示层(注释出处形态;被注行为语义全部合规)。
- 解决到哪:本文件九站点逐点改写为「纯现役语义句或持久索引」(全替换文本见 §2.2,语义零变化);悬空 ADR 引用改指持久语义申报位(`kernel/cw_state_journal.py` 模块头「常开语义」);同族存活面登记分流(§2.4)。
- 明确不解决:他文件同型 token(多文件存活,底册见 §2.2 不解决节;精确计数不作稿面申报——计数随 pattern/scope 变,归 T-37 统一 pattern 复核登记);ADR-0634 家族出路的裁决本身(候选 = 用户命令立 ADR 锚定 / 全族改纯语义;AGENTS §9 ADR 仅经用户命令创建,非本稿可决);「用户裁定 2026-09-10」日期化裁定引用(全仓通行出处形态,报告未列违例,本稿保留;若汇总裁决收紧,统一批处理)。

### 1.3 F-3(低)分型总数口径漂移(表头 37 vs 正文/代码 36)
- 现状症状:六处「37」——`screens/op-layer.md` 头注(L3)/§1.5(L62)/§3 标题(L81),`screens/README.md` 卷首(L4)/§3 标题(L34),`flow/README.md` §1 总图(L19);op-layer §3 正文合计行「11 + 8 + 13 + 1 + 1 + 2 = 36」与代码实况(`operations/cw_screen/` 34 类 + 商店框 2 类)一致,合计行本身无漂移。
- 规范条款:`screens/README.md` §0「逐屏形态分类总表(37 屏)= op-layer.md §3」——两正本互引且计数不一致。
- 根因归层:表示层(文档计数快照漂移;部署机退役后表头未回头改,T-2 稿 F-6 同认定)。
- 解决到哪:零新增修法面——本稿 grep 全量复核六处与 T-2 `changes/2026-09-22-screen-review/buy_cards.md` §2.6 清单逐位同集,归属全沿其分流(五处并入在册正本更新批、screens/README 卷首归 T-2 批、搁浅兜底),本稿只作归口声明与零新增复核(§2.3)。
- 明确不解决:`CwOpSettleConfirm`(画面框 op 形态第三件,单 node 驻留)不入 §3 分型表的结构裁决(现口径,报告括注确认,登记 T-37 供裁决);分型清单短名风格统一(T-2 §2.6 排版批)。

## 2. 方案

### 2.1 F-1:act node 改 runner 帧(读点消除)+ 直调形态登记 §1.1 例外③

**修法 A|两 node 形态读点消除**(`operations/cw_op/cw_op_open_shop.py::CwOpOpenShop.act`):

```python
# 现文(L129-130):
        if not self.round_by_find_and_click_area(
                self.screenshot(), '货币战争-备战', '按钮-商店').is_success:
# 改为(仅首参):
        if not self.round_by_find_and_click_area(
                self.last_screenshot, '货币战争-备战', '按钮-商店').is_success:
```

- 依据:`screens/op-layer.md` §1.1「决策动作 node 迭代用 node runner 进 node 时给的 last_screenshot(round_wait 每轮新帧)」;帧供给 = `operation_node.py` `screenshot_before_round` 缺省 True,每轮进 node 自动新帧;同帧先例 = 同函数重入裁决行与观察 node 均用 `last_screenshot`。重入裁决与点击瞄准之间零动作零画面变化,同一帧两用语义等价;`round_by_find_and_click_area` 首参即帧,传 runner 帧为全仓画面 op 通行形态。
- 修后形态:两 node 形态全程零 `screenshot()` 调用,act 与 §1.1 两 node 合同逐字一致,无需任何登记。

**修法 B|直调形态登记例外**(正本 = `screens/op-layer.md` §1.1 在册例外清单,例外②句号后增③;同句「在册例外只有两类」改「三类」、「除上述两例外」改「除上述三例外」。插入文本):

> ③**(编排壳直调机械臂读)** 宿主画面 op 的 bare-loop 决策环直调原子机械函数(无 node runner 轮界帧供给:宿主 `last_screenshot` 取自节点轮首,环内前序动作已改屏,现取帧为该原子动作结构性必需)——函数内读数用途封闭 = 自带幂等门判定(推进型空决策的门判定流程义务,§3 判据;非观察上报、零逻辑态写(容器事实仅动作回执簿记,kernel receipts 唯一写点)、零决策)+ 点击目标定位(瞄准,不是观察,`flow/action_ops.md` §1 增补 3 同口径);落地对账仍归下一帧观察侧,机械交回语义不变。现役成员封闭集 = `operations/cw_op/cw_op_open_shop.py::open_shop`(宿主 op 限 = `CwScreenPrep`);宿主语境封闭清单 = 该成员的全部生产直调点,编辑时点现值两处——`cw_screen_prep.py::CwScreenPrep._open_shop_phase`(显式开店)与 `cw_loop.py::_launch_frame_arbitration`(发射帧仲裁段;该段退役时本点随之出清,清单随正本修订同步收缩);新成员与新宿主语境先登记本条再落码,禁类推扩员。

- 登记要件逐条依据:①结构性必需 = 宿主决策环(`CwScreenPrep` 单动作 `while True` 循环,op-layer §3 重型屏行)内前序动作(DeployMove/卖出/买经验等)改屏后宿主帧失真,直调点无轮界刷新——两直调语境同构(`_open_shop_phase` 显式开店与 `_launch_frame_arbitration` 仲裁段的宿主帧同取自节点轮首),`open_shop` 幂等门与点击瞄准必须取调用时点帧;②读数用途封闭 = `open_shop` 的两读(幂等门 `round_by_find_area` + 点击瞄准 `round_by_find_and_click_area`)零 obs 组装、零 report、除动作回执簿记外零容器写(容器事实 = `note_action_receipt` 动作回执,簿记非画面读数;`game_state/fields.md` §8 执行回执唯一写点——与例外③正本文本括注同源);③对账归观察侧 = 机械交回现役申报(`open_shop` docstring,验证废除用户裁定 2026-09-10)。
- 成员封闭集注记:`CwOpCloseShop`/`close_shop` 同型读点**不登③**——其宿主文件在在册 3.4 删除面内,补登将死读点 = 登记即过期(过渡窗内维持现状不扩员,在册落地即消亡;搁浅判据与兜底动作 = §2.4 在册段)。

**关键取舍**:
- act node「改 runner 帧」vs「登记例外」:改帧。runner 帧在场时登记读屏 = 给无结构理由的同轮第二截图发许可,稀释封闭清单;审查差距说明同指向(「改用 last_screenshot 即可消除」)。
- 直调形态四选一:「登记例外」vs「改用宿主 `last_screenshot`」vs「消灭直调(改构造 `CwOpOpenShop` 跑两 node 形态)」vs「调用方取帧传入」:登记例外。宿主帧结构性失真(bare-loop 前序动作改屏),改用即引入错点/漏点风险;消灭直调与在册裁决冲突(shop-visit-loop.md §2.2 保留直调「幂等,不变」,且决策环内嵌套 run_operation 加重编排面);传帧只是把读点挪进调用方,登记问题原样存在且读点更散。登记与审查倾向(「修法二选一:登记例外 / 改用 runner 帧」)和在册时点双对齐。
- 例外命名按「用途 + 语境」收窄而非按文件名/符号名:防文件改名(在册 3.5 有类名正名先例)使登记失锚;四要件(宿主形态/帧供给缺失/用途封闭/成员封闭集)任一不满足即出清单,防例外变漏洞。

### 2.2 F-2:注释逐站点现役化改写(九站点全替换文本)

文件 = `operations/cw_op/cw_op_open_shop.py`。改写原则 = 删会话局部标识符、悬空 ADR 改持久语义申报位、变更史时态改现役规则句;行为语义零变化(AGENTS §8)。

| # | 站点 | 现文(节选) | 改写后 |
|---|---|---|---|
| 1 | `_note_receipt` docstring 首行(L17) | 「(R2 §3.2.5;渠道②,唯一写点 = kernel 口)」 | 「(唯一写点 = kernel 口 `note_action_receipt`)」 |
| 2 | 同 docstring 末句(L21) | 「journal 常开(ADR-0634)回执写入无条件」 | 「journal 常开(语义申报 = `kernel/cw_state_journal.py` 模块头)回执写入无条件」 |
| 3 | `_open_shop_already_open` docstring(L41-43) | 「观察 node 门命中与动作 node 重入裁决共用……禁第二份(总纲契约 1 共享零转录)」 | 「观察 node 门命中、动作 node 重入裁决与直调形态共用……同语义出口禁第二处构造(单一构造点防多份转录漂移)」 |
| 4 | `open_shop` docstring 首行(L49) | 「开商店原子核心(W970 批 A 契约 §4.2 `CwOpOpenShop`;幂等开店)」 | 「开商店原子核心(`CwOpOpenShop`/编排壳直调两形态共用;幂等开店)」 |
| 5 | 同 docstring 幂等段(L55) | 「点击落空不判负(W970 §4.2 F7),重入轮由本观察裁决出口」 | 「点击落空不判负,重入轮由本观察裁决出口」 |
| 6 | 同 docstring 机械交回段(L58-59) | 「M1③ 发出即职责完成……不再验「收起出现」」 | 「发出即职责完成……不验「收起出现」」(「用户裁定 2026-09-10」保留,见 §1.2 不解决节) |
| 7 | 同 docstring 回执段(L64) | 「R2:三出口各落一条动作回执(見 :func:`_note_receipt`;…)」 | 「三出口各落一条动作回执(见 :func:`_note_receipt`;…)」(顺手正字:見→见) |
| 8 | park 注释两处(L76 直调体 / L134 act) | 「# 点击后 park:光标停在「按钮-商店」上会污染后继读屏(审计 P0 同型)」 | 删「(审计 P0 同型)」,park 理由句保留 |
| 9 | `CwOpOpenShop` 类 docstring 首行(L84) | 「原子 op(W970 批 A;推进型两 node 形态)」 | 「原子 op(推进型两 node 形态)」 |

- 依据:站点 1 唯一写点语义 = `game_state/fields.md` §8;站点 2 持久索引目标在册核实(`kernel/cw_state_journal.py` 模块头「常开语义:本模块无开关,生产装配 = currency_war_app」;目标锚自身残留 ADR-0634 标签与 `decisions/` 路径引用,随同族批清偿(T-37),本稿改指其语义申报句不新增第二源);站点 3「与直调形态共用」为现役事实(`open_shop` L69 幂等臂 `return _open_shop_already_open(op)`)。
- **关键取舍**:「逐点改写、语义保留」vs「整段重写注释」vs「先立 ADR 再保留编号引用」:逐点改写。整段重写 = 无谓 churn 且丢现存正确语义;立 ADR = AGENTS §9 用户命令制,非本稿可决(候选登记 T-37);悬空引用改指 `cw_state_journal.py` 模块头 = AGENTS §8 二选一中取持久索引(可点验)优于纯语义描述。

**不解决(同族分流登记,§2.4 T-37 清单消费)**:grep 口径申报——token 集 = `R2 §3.2.5|渠道②|W970|W971|M1③|审计 P0|总纲契约|ADR-0634`,scope = `src/sr_od/application/currency_war`;精确计数不作稿面申报(计数随 pattern/scope 变,全量清单以统一 pattern 由 T-37 复核登记,本清单作归属底册不作计数基准)。存活面底册:`cw_screen_buy_cards.py`(:474/:479/:628/:720/:1252/:1291)、`prep_actions.py`(:450/:458)、`operations/cw_loop.py`(多处)、`operations/cw_screen/_overlay_confirm.py`(:11)、`kernel/cw_game_state.py`(多处)、`kernel/cw_vocab.py`(:319)、`kernel/cw_state_journal.py`(模块头自引)、`kernel/cw_deploy_logic.py`(:659 渠道②)、`operations/cw_screen/cw_screen_bookcard.py`(:189 渠道②+ADR-0634)、`operations/cw_op/cw_prep_level_up_action.py`(:83 审计 P0)、`obs/cw_observation.py`、`obs/cw_settlement_obs.py`、`cw_screen_battle_wait.py`(多处)、`cw_flow_const.py`、`cw_entry_start.py`、`cw_strategy_manager.py`、`telemetry/` 族(cli/match_archive/defects/journal_query/schema)、`kernel/cw_reconcile.py`、`kernel/cw_observe.py`、`operations/dev/drag_cw_char.py`;另有 `cw_op_close_shop.py` 全文件同型(随在册 3.4 退役自愈,不单列批次)。

### 2.3 F-3:计数漂移归口声明(零新增修法面)

- 复核结论:本稿 grep 全量复核,正本目录内「37 画面|37 屏」命中恰六处(`screens/op-layer.md` L3/L62/L81、`screens/README.md` L4/L34、`flow/README.md` L19),与 T-2 稿 `changes/2026-09-22-screen-review/buy_cards.md` §2.6 清单**逐位同集,零新增**;op-layer §3 合计行 36 与代码实况一致,无第三处漂移形态。
- 归口(全部沿 T-2 §2.6,本稿不双改):五处(op-layer 三处/screens README §3 标题/flow README 总图)并入在册 `changes/2026-09-21-shop-refresh-terminal/` 正本更新批(其清单 op-layer 行「计数同步」、screens README §3 行、flow README 总图重写行认领);`screens/README.md` 卷首(L4)归 T-2 落地批;计数现值口径(各处不自持快照数,值 = 执行时点 op-layer §3 合计行现值;在册落地后 `CwOpCloseShop` 退役 36→35)与搁浅兜底(认领批搁浅时 T-2 批一次改齐六处)同沿 T-2。跨稿对账载体 = T-37 汇总。
- 本稿影响面申报:F-1/F-2 修法不增删 op 类、不改 `CwOpOpenShop` 分型归属(维持推进型空决策「商店框,只读/导航变体」行),合计行现值不受本稿任何批影响。
- 同族登记(T-37):推进型名单行「CwOpOpenShop/CwOpCloseShop(商店框…)」中 CwOpCloseShop 的退役改动在在册 op-layer 行认领面内,本稿不重复;`CwOpSettleConfirm`(画面框 op 形态第三件)不在 §3 表内属现口径而非漂移(报告括注确认),是否入表 = 分型结构裁决,登记 T-37 供裁决,本稿不动。
- **关键取舍**:「本稿重立归属分流」vs「归口声明沿 T-2」:后者。同一漂移面两稿各立分流 = 双改源,T-37 对账必冲突;T-2 已含现值口径、五处认领、卷首自辖与搁浅兜底,归口链完整,本稿复核 + 声明即可。

### 2.4 跨稿对账、时点关系与落地验证门

**与在册 `changes/2026-09-21-shop-refresh-terminal/`**:**本稿修法代码文件面零交叠**(其 landing 3.4 文件面含 `cw_op_close_shop.py`(退役)、`cw_loop.py` 与 `cw_screen_prep.py`,不含 `cw_op_open_shop.py`);文档面共同编辑文件 = `screens/op-layer.md` 但**编辑区不交叠**(本稿 §1.1 例外清单 vs 在册正本更新清单 op-layer 行的 §3 分型表/§1.4/§4/头注计数),token 级不同条目可合流、后落批对账(口径同本节 T-2 段)。`open_shop(self)` 显式开店直调点被在册明确保留(details/shop-visit-loop.md §2.2「幂等,不变」)——例外③登记的是长期存活形态,非过渡补丁。**直调宿主面收缩申报(N-1)**:`_open_shop_phase` 直调点不被在册触及、原样保留;仲裁段直调点(`cw_loop.py::_launch_frame_arbitration` 内 `open_shop`(:550)/`close_shop`(:590)各一)随仲裁段整段退役消亡——在册落地后直调形态宿主语境由两处收窄为一,例外③宿主清单随之收缩(同步义务 = 本节 T-37 清单第 5 条;若在册先落,本稿批编辑例外③时点现值即单直调点)。`close_shop` 两读点(①直调形态 `close_shop` 函数体 `op.screenshot()`,调用语境两处 = `_open_shop_phase` 与仲裁段;②节点形态 `CwOpCloseShop.act` 的 `self.screenshot()`):在册按期落地 = 随文件/仲裁段退役自愈(修法 B 不补登);**搁浅兜底(判据 + 动作;登记条目 = 本节 T-37 清单第 1 条)**:判据 = T-37 汇总时点在册 landing 3.4 未完成 → 届时由本稿落地批按 T-2 §2.5 同款兜底,**按读点类别拆分**——直调读点(无 runner 帧)扩登进例外③成员封闭集;节点读点(`CwOpCloseShop.act` 的 `self.screenshot()`,runner 帧在场)按修法 A 同款改 `last_screenshot`(例外③要件① = 帧供给缺失,节点形态读点不合登,塞入 = 再造冗余现取缺陷类);或经 T-37 显式裁决豁免/另批退役。防汇总延宕下未登记读点无限期在跑。执行序:两批互不依赖,可任意序执行,两序皆自洽(先我后彼 → 条目 5 收缩义务;先彼后我 → 本稿编辑时点现值即单直调点);唯 `screens/op-layer.md` 并发编辑按上述合流对账。

**与 T-2 `buy_cards.md`**:F-3 归口见 §2.3。`screens/op-layer.md` §1.1 例外清单为共同编辑区——T-2 F-5 备选/兜底态改写例外②句(终结臂/对拍留证读扩登),本稿新增③条目,token 级不同条目可合流,后落批对账;T-2 主修法态(段尾观测块随在册退役、§1.1 不扩登)与本稿零冲突。

**T-37 登记条目(本稿名下全部让渡面,汇总批逐条消费;条目 1/5 触发态执行者 = 本稿落地批,其余由汇总批/归属批处置)**:
1. `close_shop` 读点搁浅兜底义务(判据与动作 = 本节在册段,按读点类别拆分:直调读点扩登例外③、节点读点改 `last_screenshot`;触发即由本稿落地批执行,非 T-37 代办);
2. F-2 注释同族底册(§2.2 不解决节,含 `cw_deploy_logic.py`/`cw_screen_bookcard.py`/`cw_prep_level_up_action.py` 三文件补列)+ ADR-0634 出路候选(用户命令立 ADR 锚定 / 全族改纯语义;含 `cw_state_journal.py` 模块头语义申报锚自身的标签残留,§2.2 站点 2 依据);
3. `CwOpSettleConfirm.confirm` 同型冗余现取(node runner 帧在场,§1.1 不解决节)归属待裁——结算/战斗等待面审查稿或 T-37;
4. F-3 同族:推进型名单行 CwOpCloseShop 退役改动(在册认领面,§2.3)、`CwOpSettleConfirm` 入表分型结构裁决(§2.3);
5. 例外③宿主语境清单收缩同步(N-1):在册仲裁段落地后 `cw_loop.py::_launch_frame_arbitration` 直调点出清,`screens/op-layer.md` §1.1 例外③宿主清单随正本修订收缩(义务归在册正本更新批扩展或 T-37 兜底;若在册先落,本稿批编辑时点现值即单直调点,本条自然失效)。

**落地验证门(人工 grep,禁立源码扫描测试,AGENTS §10.4)**:
1. `cw_op_open_shop.py` 内 `self.screenshot()` 零命中(修法 A);`op.screenshot()` 恰两处且全部位于 `open_shop()` 直调体(例外③唯一成员)。
2. `cw_op_open_shop.py` 内注释词表 `W970|W971|R2|渠道②|总纲契约|审计 P0|M1③|ADR-0634|不再验` 零命中(§2.2 改写后;`R2` 取裸 token——本文件无合法 R2 残留,裸词覆盖站点 7 的「R2:」形态)。
3. `screens/op-layer.md` §1.1 例外清单含③,「三类/三例外」措辞与成员封闭集文本和 §2.1 一致;例外③宿主语境清单与 grep `open_shop(` 生产直调点现值一致(文档对照 + grep)。
4. CW 快速集(`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`)全绿——注释改写零行为变化;act 改 `last_screenshot` 后帧供给路径不变(fixture harness 每轮供帧,观察 node 同款既有用法);`test_cw_unified_action_3` 终结承载行锁/备战环终结集锁不受本稿触及。

## 4. 坐标规范增补(op-layer :35/:48)

> **基准** = 正本新入两条款(commit 9c8e9016b,用户裁定 2026-09-22):`screens/op-layer.md` §1.1 **:35「选择坐标观察上报」**(适用范围 = 商店与各需选择的 overlay;坐标单一真相源 = 观察上报;策略侧只输出下标、动作 op 按下标自 game state 取坐标执行;现役逐批收敛,禁新增第二坐标源)与 §1.2 **:48「每个动作 op 单独一个文件」**。增补前置设计底册 = `.debug/progress/2026-09-22-cw-screen-review/reports/coord-norm-addenda-plan.md`(下称「底册」;T-17 增补点清单 = 其 §2.5)。
> **性质 = 登记级增补,零行为变更**:商店域坐标收敛不随本稿批——宿主 = 商店域收敛批(底册 §4 批3;骨架经五选卡屏收敛验证后再动商店,BuyCard 高频动作面);本节只做欠账登记与辖域澄清,§0-§2 已收敛修法面不动,防「文档批沉默 = 默认保留」(planner.md §4 同款判语)。
> **增补节修订轨迹(coord-attack)**:`.debug/progress/2026-09-22-cw-screen-review/reviews/coord-attack-T15-16-17.md` 判本节未收敛 6 条低(本稿 A-4/A-5/A-6),已按攻击结论就地修订,零行为设计变更——A-4 = §4.1 站点全集 3→5(`shop_card_to_container`/`shop_cards_to_legacy` 两转换函数 docstring 补录为站点 4/5 随收敛批同批改写;`cw_vocab.py::ShopCard.x` legacy 注显式豁免不入全集),T-37 登记行站点全集同步;A-5 = §4.1 补批1 字段骨架批两义务('shop' 域版本 bump 1→2 + sim 不建模值恒 None),T-37 登记行同步(登记行自足申报,不依赖底册原文);A-6 = §4.2 pick 类计数 12→11(equip pick 已随选择装备屏退役;正本 :48 现值已同步为 11,底册 §3.1 表 equip 行归底册随批修订面)。

### 4.1 增补一(:35)商店域「坐标不入存储」欠账登记

**结论**:商店域现役形态 = 「牌位点击坐标不入存储,执行侧按槽号从 screen_info 现取」——形态上非选卡屏族「决策半现算经 env.target」而是**动作侧现取**,同属「非观察上报」坐标源 = :35 欠账(底册 §2.5 增补点 1)。三站点逐字现文(行号 = 审查时点快照仅供对照,定位 = 符号锚,§0 口径同;同判句族补录后站点全集 = 三站点 + 两转换函数 docstring,见本节「同判句族漏站补录」):

**站点 1** = `kernel/cw_game_state.py::ShopCard` 类注(:509-511,docstring 坐标句):

> 牌位点击坐标不入存储——坐标单一真相源 = screen_info「商店牌-N」区域
> (cw_obs_core.shop_card_click_points);入存储的是**槽号**(观察事实,
> 见 slot 字段),执行侧按槽号从 screen_info 现取坐标。

**站点 2** = `game_state/fields.md` §3.3.1(:637-638,商店牌行 shop 语义段):

> **槽位坐标系:数组下标 +1 = 物理槽**;点击坐标单一真相源 =
> screen_info「商店牌-N」区域(不入存储)。

**站点 3** = `operations/cw_op/cw_buy_card_action.py::CwActionBuyCardOp.run` 现取消费链(定位注释 :76-83、坐标注释 :99-105、越界门 :110、取点执行 :118-119):

> ```python
> # 点击定位 = 牌自带物理槽号 slot(读链写入)→ screen_info
> # 「商店牌-N」现取(W6 波 4 双 ShopCard 归一:容器牌无 x 坐标,
> # 坐标单一真相源 = screen_info,设计件 §2.5-5)。身份匹配优先
> # 同一性(action 由决策核自 payload 产出),退化按 (name, star)
> # ——匹配下标仅作槽号缺失时的兜底锚,见下方点击解析。
> # 槽号主源 = payload 定长槽阵列位置(三态模型:数组下标+1 =
> # 物理槽;身份同一性优先,退化 (name, star));card.slot 兼容
> # 字段降为最后兜底(退役面审计)。
> ```
>
> ……(中略:身份匹配与槽号解析,与坐标源无涉)……
>
> ```python
> # 点击坐标 = 牌自带实测槽位(观察期读链写入的物理槽号)→ screen_info
> # 「商店牌-N」中心。紧凑下标只在牌行满列期与物理槽位等价:游戏买入
> # 后不压缩剩余卡位(牌行打洞),紧凑列表全体下标偏离物理槽位,按下标
> # 取固定槽坐标 = 点击落空槽框(实机局实证:1 槽空、卡在 2-5 槽时恒打
> # 1 槽框,「买牌点击不注册」根因;布局双源同族 = ADR-0646 bench 布局
> # 错位的商店牌行版)。槽号缺省(0 = sim/离线构造、修复前旧档)退回
> # 紧凑下标映射(旧行为)。
> ……
> if not (1 <= _slot_no <= len(env.click_pts)):
>     ……
> pt = env.click_pts[_slot_no - 1]
> op.ctx.controller.click(pt)
> ```

现取链 = `env.click_pts`(`operations/cw_op/cw_shop_action_ops.py::ShopExecEnv.click_pts`,:83)← `operations/cw_screen/cw_screen_shop.py` :469 `shop_card_click_points(self.ctx)` ← `kernel/cw_obs_core.py::shop_card_click_points`(:69-82,screen_info「商店牌-1..5」area 中心)。

**同判句族漏站补录(coord-attack A-4,站点全集 3→5)**:同一文件另有两处「坐标单一真相源 = screen_info / 按 slot 现取」政策声明未入原站点全集——

- **站点 4** = `kernel/cw_game_state.py::shop_card_to_container` docstring(:1040-1046):「x 是旧版独有的执行域字段,容器不入存储(坐标单一真相源 = screen_info)」(:1044)。`fields.md` §3.3.1 边界段(:649-651)指认本函数 = 帧侧牌 → 容器牌**唯一映射函数**(权威面)。
- **站点 5** = `kernel/cw_game_state.py::shop_cards_to_legacy` docstring(:1057-1082):「执行侧 buy 发射从 screen_info「商店牌-N」区域按 slot 现取(黑板帧链自持 x,不经本函数)」(:1063-1065)。

收敛批退役 `ShopCard` 类注坐标句 + fields.md §3.3.1 改写后,两处转换函数 docstring 的旧真相源申报与新真值源(观察上报容器 `ShopPayload.card_points`)矛盾,随收敛批**同批改写**(坐标源半句改指容器 `card_points` 按 slot 上报,槽号透传与「转换只许在本节两映射函数发生」单一源语义保留);T-37 登记行站点全集按「三站点 + 两转换函数 docstring」消费(登记行原文已同步,§4.3)。

**显式豁免申报**:`cw_vocab.py::ShopCard.x`(:108「牌位中心 x(购买点击坐标)」)= legacy/sim 域字段的构造期注——legacy 类型属 sim/黑板域随推演内核收编长期并存(`cw_game_state.py` 转换视图区块在册申报),容器侧转换视图恒置 0 不消费(`shop_cards_to_legacy` `x=0` 在册),**不入 :35 收敛站点全集**;其「购买点击坐标」陈旧括注随商店域收敛批顺手改写为「恒 0,执行点击不经此字段」(零行为,非豁免项)。

**登记形态(收敛终态;宿主 = 商店域收敛批,底册 §2.5 增补点 1 + §1.8(c) + §4 批3)**:入口观察(`cw_screen_shop.py::_shop_entry_read` → `obs/cw_observation.py::read_shop_cards` 链)一并上报 `ShopPayload.card_points`(`kernel/cw_game_state.py::ShopPayload`,:551;`tuple[tuple[int, int], ...]` 定长 5,数组下标 +1 = 物理槽,与 ShopSlot 既有槽位坐标系同格——底册 §1.2 商店牌行特形)+ BuyCard 动作 op 改自容器按 slot 取点执行(缺席/越界 = 守卫断言 AssertionError 响亮暴露,禁回退 screen_info 二次取点——回退即第二坐标源,:35 明文禁)+ `fields.md` §3.3.1 改写(目标文本 = 底册 §1.8(c))+ `ShopCard` 类注坐标句退役 + 两转换函数 docstring 同批改写(coord-attack A-4 补录,站点 4/5 见前)。**批1 字段骨架批义务(coord-attack A-5 补录;两项随骨架批先行落笔,非批3)**:①`'shop'` 域版本 bump——`DEFAULT_GS_SCHEMA` :191 `'shop': 1` 在册,`ShopPayload.card_points` 扩字段按底册 §1.8(b)「C 类 payload 扩字段 = 域版本 bump(shop payload 所属域)」随批1 bump(1→2);②sim 不建模申报——sim 无画面识别,`card_points` 值恒 None(sim 写入面不入,底册 §1.4-W4)。T-15/T-16 同面申报齐备(T-15 §4.2/§4.5、T-16 §4.1(5)/§4.5),三稿申报粒度对齐。收敛批落地前站点全集(三站点 + 两转换函数 docstring)= 欠账形态在册运行;本稿零行为批一处不改。

### 4.2 增补二(:35)静态控件锚不入坐标域的辖域澄清 + (:48)零涉申报

**辖域澄清(对齐底册 §1.6 辖域边界)**::35 辖面 = **随观察帧变化的选项/候选坐标**(选卡/选选项的点击目标);**不辖 = 静态控件锚**——确认钮/刷新钮/开商店按钮/收起按钮等稳定 UI 锚 = screen_info area 执行期现取(现取 + 兜底常量模式;op-layer §1.2「唯一允许的查找 = 点击/拖拽目标定位(瞄准,不是观察)」在册),**现状维持,不入坐标域**。判据 = 坐标是否随「本次观察读到什么」变化。

**本稿具体面**:`open_shop` 的「按钮-收起」幂等门读(:67-68)与「按钮-商店」点击(:70-71)= 静态控件锚(screen_info area 现取),:35 不辖;商店域同判面 = `cw_screen_shop.py` `_level_btn`(买经验,:470)与「按钮-刷新」(:474)`area_center` 现取。故 **F-1 修法 A(act 改 runner 帧)与修法 B(直调形态登记例外③)不受 :35 影响,零连带**——两修法辖的是显式读屏点登记纪律(op-layer §1.1),与坐标域分属两条款。

**(:48)零涉申报**:商店域动作 op 全部一类一文件已合规——`CwActionBuyCardOp`(`cw_buy_card_action.py`)/`CwActionRefreshShopOp`(`cw_refresh_shop_action.py`)/`CwActionCloseShopOp`(`cw_close_shop_action.py`)/`CwActionLevelUpOp`(`cw_prep_level_up_action.py`),无动作 op 驻 `operations/cw_op/cw_overlay_pick_action.py`(该文件 **11 个 pick 类** = 五选卡屏族,拆分归底册 §3 独立批;coord-attack A-6:equip pick 已随选择装备屏退役——`CwActionPickEquipParam` 退役在册 `cw_vocab.py`、零写族迁出申报 `zero_writes.py` :70-72;正本 :48 现值已同步为 11,底册 §3.1 表仍列 `cw_pick_equip_action.py` 行 = 旧值,删行归底册随批修订面;11 类无一商店域,零涉结论不变)——**:48 零涉,无欠账无连带**。

### 4.3 验收锚与 T-37 登记行(原文)

**验收锚**(底册 §2.5):①登记行在册可查——商店域欠账 + 收敛批入口 = 本节 §4.1 登记条目 + 底册 §1.8(c) 目标文本;②本稿修法面零行为变化申报维持(§2.4 落地验证门四条不变)。

**T-37 登记行(追加一条,原文如下,汇总批消费)**:

> - [T-37 登记][欠账] 商店域(T-17)::35 选择坐标观察上报欠账——牌位点击坐标现役「不入存储,执行侧按槽号从 screen_info 现取」,站点全集 = 三站点 + 两转换函数 docstring(coord-attack A-4)= `kernel/cw_game_state.py::ShopCard` 类注坐标句(:509-511)/ `game_state/fields.md` §3.3.1(:637-638)/ `operations/cw_op/cw_buy_card_action.py` 现取消费链(:76-119)/ `kernel/cw_game_state.py::shop_card_to_container` docstring 坐标源句(:1044)/ `kernel/cw_game_state.py::shop_cards_to_legacy` docstring 按 slot 现取句(:1063-1065;两转换函数 docstring 随收敛批同批改写,`cw_vocab.py::ShopCard.x` :108 legacy 注显式豁免不入全集);收敛终态 = 入口观察(`_shop_entry_read` → `read_shop_cards` 链)一并上报 `ShopPayload.card_points`(定长 5,下标 ↔ 物理槽 1-5)+ BuyCard 动作 op 自容器按 slot 取点 + fields.md §3.3.1 改写(目标文本 = 底册 §1.8(c))+ ShopCard 类注坐标句退役;批1 字段骨架批义务随行 = `'shop'` 域版本 bump(1→2)+ `card_points` sim 不建模(值恒 None)(coord-attack A-5,登记行自足申报);宿主 = 商店域收敛批(底册 §4 批3,骨架经五屏验证后再动);本稿零行为批只登记,登记原文 = `changes/2026-09-22-screen-review/op_open_shop.md` §4。
