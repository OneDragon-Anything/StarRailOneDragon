# T-21 BOSS简报 修法设计(boss_briefing)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 未收敛 3 条低→修订→r2 收敛 0 条)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-21-r1.md`(发现 F-1..F-4;总判定 = 有问题,高 0 中 2 低 2)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准,落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`,行号仅作本稿定位辅助。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)。
- 修法性质:F-1..F-4 全部为文档语义更新与注释/测试措辞清理,**零行为变化**(无任何逻辑/签名/常量改动;src 唯一触碰 = 一行 docstring,sr-od-test 唯一触碰 = 测试函数名/docstring/断言消息/模块头申报行)。

## 1. 问题与动机

### 1.1 F-1 op-layer §3 全形态行 report 列把 BossBriefing 仍申报为占位(中)

- **现状症状**(审查报告 F-1):`screens/op-layer.md` §3 全形态行 report 列尾句申报「11 屏全设;其中 BossBriefing/WaitOneOne/DeployNotFull/ArmoryBox 现役零容器摄入面,接口为统一形态占位」。代码真值 = `kernel/cw_screen_report/boss_briefing.py::report_screen_boss_briefing_obs` 已是**真实写面**:经 `_write_derived_node_type` 直定 boss 节点类型(目标 = 现 hist,actor='CwScreenBossBriefing'),门 = obs.on_screen 假早退 / hist 未推进禁猜零写。完备锁 `sr-od-test/test/sr_od/application/currency_war/test_cw_screen_report_ports.py` 与代码同侧:`_SCREENS` 把 boss_briefing 计入「18 实体写点」组、`_PLACEHOLDERS = (armory_box, wait_one_one, deploy_not_full, battle_wait, buy_cards)` 不含之,锁注记申报「boss_briefing 已于 2026-09-20-node-advance-action-report 切换批升级为真实写面——BOSS 类型直定(目标 = 现 hist)」,写语义专项锁在节点域锁(`test_cw_game_state_contract.py::test_boss_briefing_report_types_hist_node`、`test_cw_node_chain.py` 直定路径、`test_cw_node_advance_scenarios.py`)。三证(代码 + 完备锁 + 节点域锁)齐指真实写面,唯一不符面 = 正本 §3 该句。
- **根因归层**(根源两问):①根在哪层 = **约定层**——迁移批(2026-09-20-node-advance-action-report)收尾时正本同步漏了 op-layer §3 该句(AGENTS.md §9 迭代收尾义务「代码实现后更新正本」未走全),代码与锁均正确,不是语义或行为错误;②修的是根 = 辖内正本申报向代码与锁全量对齐(改写现在时申报,非加注打补丁)。F-2 与本件同根(同一迁移批的不同残留面),本稿以同一范式一次覆盖,不立第二套机制。
- **解决到哪**:op-layer §3 全形态行 report 列一处改写(§2.1);完备锁断言方向核对——锁已与代码一致,**零测试改动**,修法方向 = 文档向代码与锁对齐,禁反向改锁凑一致。
- **明确不解决**:WaitOneOne/DeployNotFull/ArmoryBox 三屏的占位申报(与代码一致,保留);battle_wait(驻留状态机行)/buy_cards(重型屏行)的占位申报(合法形态);boss_briefing 直定写语义在 §3 的展开(§3 = 分型总表,只申报「占位 vs 真实写面 + 形态」,写语义单一源 = kernel 屏文件,展开即第二源)。

### 1.2 F-2 boss_briefing.md §2/§3/§4「占位/零容器写点/零 GameState 写端」与代码不符(中)

- **现状症状**(审查报告 F-2):`screens/boss_briefing.md` §3「report = `report_screen_boss_briefing_obs` 占位调用(本屏现役零容器写点,接口为统一形态占位;match/gs 缺席跳过)。零 GameState/session 写端(纯过场,无观察上报面)。」;§2「+ obs{on_screen} + 占位 report 调用」;§4 对照表上报列「现役零容器写点」。「零 GameState 写端」字面为假——report 实写 boss 节点类型至 `gs.node`(op 模块头自述「boss 类型直定写端,目标 = 现 hist」)。
- **根因归层**:**约定层**,F-1 同根(同一迁移批收尾未清完的措辞面)落在画面篇;另有三处同根残留随本条一并收敛(附记):①审查报告已附记的测试仓残留——行为锁 `test_cw_obs_arch_phase_screens.py::test_boss_briefing_observe_gate_and_placeholder_report` 的函数名/docstring/断言消息仍称「占位」(断言体与代码兼容);②op 观察节点 docstring 标题行「横幅门 + obs{on_screen} → 占位 report 接线」——其 docstring 正文段已自述直定,仅标题行是同批残留(同款句式在 `cw_screen_wait_one_one.py`/`cw_screen_deploy_not_full.py`/`cw_screen_armory_box.py` 三屏为真占位表述,正确保留,不在修法面);③同测试文件模块头「判别单一源消费面锁」条以在役时态申报「`is_boss_briefing_texts` 消费点集合迁移前后不变(cw_loop / cw_screen_battle_wait / cw_screen_boss_briefing;防转录顺手复制判别逻辑)」,而锁体已退役、删除在册于同文件尾(「三审整删…源码扫描形态(README 禁止清单);防线归 review 与代码规范」)——申报面与同文件实况相悖,申报未随退役批同步(与 F-1/F-2 根因同型)。
- **解决到哪**:§2/§3/§4 三节一次成文改写(§2.2 主表);附记 A(测试仓函数名/docstring/消息 + 模块头消费面锁申报订正)、附记 B(op docstring 标题行)随本条一并改,否则 §2.2 验证门不收口。
- **明确不解决**:§6「零写端」——其为**动作侧**口径(README.md §2 模板 §6 职责 = 动作 → 哪个上报函数;本屏无动作 op、无 `report_action_*` 调用,审查项⑥已核一致),观察侧写端归 §3 记载,两节分工不动;report 函数本体(代码现役即目标,零行为变化);其余画面篇的「占位 report」表述(真占位,正确)。

### 1.3 F-3 §1 消费点计数「第四消费点」与「三处消费同源」自相矛盾(低)

- **现状症状**(审查报告 F-3):`screens/boss_briefing.md` 卷首红线记「三处消费同源(op 内锚兜底 / `CwScreenBattleWait._hit_completion_anchor` 完成白名单 / 外循环阶段一位面过渡身份臂排他接管)」,§1 却两处独记「第四消费点」。全 src grep `is_boss_briefing_texts` 运行时消费恰 3 处:`cw_screen_boss_briefing.py`(op 内锚兜底)、`cw_screen_battle_wait.py::hit_settle_completion_anchor`(完成白名单)、`cw_loop.py`(位面过渡身份臂排他接管)。
- **根因归层**:**表示层**——「第四」= 0q 兜底(同段自述 2026-09-16 退役)退役后的残留计数,与卷首枚举及 op 模块头「三处消费同源」失对位。
- **解决到哪**:§1 两处序数改「第三消费点」,与卷首红线枚举序(①op 锚兜底 ②battle_wait 白名单 ③loop 排他臂)机械对位(§2.3)。
- **明确不解决**:判别单一源红线本身、`BOSS_BRIEFING_TOKENS` 词表、三处消费点接线(零改动);已删的 getsource 形态消费面锁不重建(源码扫描测试禁令,行为锁文件在册申报「三审整删」);该删除的同文件模块头过期「在役」申报不属本条辖域——订正归 F-2 附记 A3(同文件同根清扫),F-3 只管 §1 计数。

### 1.4 F-4 game 侧 #26 校准对象列「bot 处理」句滞后且未在册(低)

- **现状症状**(审查报告 F-4):`docs/game/currency_war/research/screen_flow_timing.md` #26 校准对象列记「bot 处理:cw_loop 分支 2 OCR『点击空白处继续』命中即点——与口径一致,运行时无需接线」。现役 = 阶段一画面身份分发专用 op:`cw_loop.py` 按身份「货币战争-BOSS简报」派发 `CwScreenBossBriefing`(身份锚 = 画面档双 id_mark 徽记模板 + 提示文本),观察门 = 徽记模板锚 miss → 「强敌」片段判别兜底,不 OCR 提示文案;`grep cw_loop` 无旧「分支 2」OCR 提示处理残留。#26 口述时序列本体(「点击空白处继续」出现即稳定、可点)仍有效且被 README.md §5.1 / boss_briefing.md §9 正确引用,失真的只是「bot 处理」列。该滞后未列入任何在册欠账(开放设计注①仅覆盖 #14/#27)。
- **根因归层**:**约定层**——旧接线被身份分发专用 op 取代后,game 侧档案的 bot 处理列未随更;develop 侧在册欠账登记机制(开放设计注)未覆盖该句,滞后不可发现。
- **解决到哪**:①develop 侧在册登记——`screens/boss_briefing.md` 开放设计注新增注③(本批落);②game 侧修正文本方向在本稿 §2.4 给出,供 game 侧文档批采纳;**本批不改 game 侧正本**。
- **明确不解决**:#14/#27「BOSS 简报关闭后自动开店」过期口径(已在册注①,本稿不清偿不重述);#26 口述时序列本体;game 侧其余任何行。

- **在册核对一致项**:审查报告 §3 十项一致面与在册欠账两项(game 侧 #14/#27「自动开店」过期口径、`test_cw_anchor_exclusion.py` 锁面缺档)本稿不立修法,仅作为各修法不得触碰的现状边界——落地时禁借同步之名改动这些在码/在册语义。

## 2. 方案

### 2.1 F-1 修法:op-layer §3 report 列 BossBriefing 移出占位、申报真实写面

| # | 位置 | 现状(病句核心) | 目标语义 |
|---|---|---|---|
| 1 | `screens/op-layer.md` §3 全形态行 report 列(cell 尾) | 「11 屏全设;其中 BossBriefing/WaitOneOne/DeployNotFull/ArmoryBox 现役零容器摄入面,接口为统一形态占位」 | 「11 屏全设;其中 WaitOneOne/DeployNotFull/ArmoryBox 现役零容器摄入面,接口为统一形态占位;BossBriefing 为真实写面(BOSS 类型直定;写语义单一源 = `kernel/cw_screen_report/boss_briefing.py`)」——cell 只申报形态归属(真实写面)+ 形态名(BOSS 类型直定)+ 单一源指针,机制与写目标语义不进分型表(与 §1.1 明确不解决的自设边界收敛为一) |

依据:代码 = `kernel/cw_screen_report/boss_briefing.py::report_screen_boss_briefing_obs`(写点 = `_write_derived_node_type(gs, 'boss', target_ord=int(hist), actor='CwScreenBossBriefing', trigger_screen=SCREEN_BOSS_BRIEFING, seq=gs.write_seq+1)`;门 = obs.on_screen 假早退 / hist None 禁猜零写);锁 = 完备锁 `_PLACEHOLDERS` 不含 boss_briefing + 锁注记迁移申报、节点域锁 `test_boss_briefing_report_types_hist_node`(hist 未推进零写/直定 boss/零序号写);规范 = AGENTS.md §9(正本永远与代码现状一致 + 迭代收尾义务)。

**验证门**:`screens/op-layer.md` grep `BossBriefing 为真实写面` 恰 1 命中(真实写面申报在档)∧ grep `其中 BossBriefing` 零命中(占位连排串不再含 BossBriefing——现值 = 「其中 BossBriefing/WaitOneOne/…」,修后 = 「其中 WaitOneOne/…」)。判据说明:不可用「BossBriefing 命中行与占位不共现」的行级判据——修后该表行合法保留其余三屏「占位」申报,与「BossBriefing」同行共现是预期形态,行级 grep 恒红;正向断言按目标串逐条机械可判。另:`sr-od-test` 完备锁 `_SCREENS`/`_NO_REPORT`/`_PLACEHOLDERS` 三集合零 diff。

**取舍**:

- 备选 A:占位列举不动、cell 尾加「BossBriefing 已升级」脚注——放弃:与代码不符的现在时申报即使加注仍会被当现役契约引用(本发现病灶即引用落空);正本改写语义,不留双申报。
- 备选 B:把 boss_briefing 直定写门补进端口锁 `_WRITE_CASES` 作写入断言——放弃:直定写语义专项锁已在节点域锁在册(完备锁注记指明归属),搬入 = 同语义第二锁(测试只覆盖核心,两条测同一件事 = 冗余);端口锁侧维持现状即与修法一致。
- 备选 C:cell 保留机制摘要(经 `_write_derived_node_type` 直定、目标 = 现 hist),改放宽 §1.1 边界为「允许一句机制摘要 + 单一源指针」(多屏管线 cell 有写门摘要先例)——放弃:两条路均可自洽,但放宽边界使「cell 内机制摘要」成为合法形态,kernel 写语义再变(原语/写目标)时表内摘要即再滞后点,正是 F-1 同病的复发面;收紧 cell 后分型表恒只申报形态归属,机制经单一源指针一步直达,漂移面最小。cell 深度与 §1.1 边界两处必须收敛为一,本稿选收紧 cell 一侧。

### 2.2 F-2 修法:boss_briefing.md 三节一次成文 + 同根附记清扫

主表(行为零改动,修的是画面篇 as-built):

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `screens/boss_briefing.md` §3 末两句 | 「report = `report_screen_boss_briefing_obs` 占位调用(本屏现役零容器写点,接口为统一形态占位;match/gs 缺席跳过)。零 GameState/session 写端(纯过场,无观察上报面)。」 | 整段改写:「report = `report_screen_boss_briefing_obs`——BOSS 类型直定:经 `_write_derived_node_type` 直定 boss 节点类型,目标 = 现 hist(简报屏仍是 boss 类型权威);门 = `obs.on_screen` 假早退 / hist 未推进禁猜零写;幂等 = 同 hist 重报走 `_write_derived_node_type` 冲突纪律(同节点同类型 = 同值重写行);match/gs 缺席跳过(局外兜底路径)。写端边界:GameState 写端 = boss 节点类型直定一行,零 node_ord 序号写(序号推进半部已退役——boss 节点序由结算确认上报推进);session 写端 = 零。」 |
| 2 | 同文件 §2 观察 node 列举 | 「+ obs{on_screen} + 占位 report 调用;」 | 「+ obs{on_screen} + report 调用(boss 类型直定,目标 = 现 hist;见 §3);」 |
| 3 | 同文件 §4 对照表上报列 | 「无自上报(观察上报 = `report_screen_boss_briefing_obs` 占位调用,观察 node 承载;现役零容器写点)」 | 「无自上报(观察上报 = `report_screen_boss_briefing_obs`,观察 node 承载;boss 类型直定,见 §3)」——「无自上报」主语 = 动作侧留守臂(本屏无 `report_action_*`),保留 |

附记表(同根残留,随本条一并改;A1/A2 = 审查报告 F-2 已附记面,A3 = 同文件同根面自查增补,B = 同款句式面自查增补):

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| A1 | sr-od-test `test_cw_obs_arch_phase_screens.py::test_boss_briefing_observe_gate_and_placeholder_report` 函数名 | 名含 `placeholder_report`(全测试仓唯一定义、零外部引用,改名安全) | 改 `test_boss_briefing_observe_gate_and_report_wiring` |
| A2 | 同测试 docstring 与断言注释/失败消息 | docstring「obs 装载 + 占位 report 接线恰一次(match/gs 在场;本屏现役零容器写点,接口为统一形态占位)」;断言注释「② 横幅在 → obs 装载 + 占位 report 恰一次」;失败消息「占位 report 接线恰一次(统一形态调用)」 | 依次改「obs 装载 + report 接线恰一次(match/gs 在场;boss 类型直定,目标 = 现 hist)」「② 横幅在 → obs 装载 + report 恰一次」「report 接线恰一次(统一形态调用)」。**断言体零改动**(早退语义/零点击/obs 装载/桩替身恰一次——report 以 monkeypatch 桩计数,与写面形态无关) |
| A3 | 同文件模块头「判别单一源消费面锁」条 | 在役时态申报「`is_boss_briefing_texts` 消费点集合迁移前后不变(cw_loop / cw_screen_battle_wait / cw_screen_boss_briefing;防转录顺手复制判别逻辑)」——锁体已随三审整删退役,删除在册于同文件尾(源码扫描形态,README 禁止清单;防线归 review 与代码规范) | 改退役申报现在时:「判别单一源消费面锁已随三审整删退役(见文件尾在册注;源码扫描测试禁令不重建),防线归 review 与代码规范」——与文件尾在册注同文,零新语义 |
| B | `operations/cw_screen/cw_screen_boss_briefing.py::observe` docstring 标题行 | 「横幅门 + obs{on_screen} → 占位 report 接线。」(docstring 正文段已自述「boss 类型直定,目标 = 现 hist」,仅标题行残留) | 「横幅门 + obs{on_screen} → report 接线(boss 类型直定)。」——同款句式在 `cw_screen_wait_one_one.py`/`cw_screen_deploy_not_full.py`/`cw_screen_armory_box.py` 三屏为真占位表述,**禁顺手改** |

依据:代码 = `kernel/cw_screen_report/boss_briefing.py` 全文(模块头/函数 docstring/写点)+ op 模块头「boss 类型直定写端,目标 = 现 hist」;规范 = screens/README.md §2(画面篇 as-built 永远与代码现状一致)+ AGENTS.md §9;「boss 节点序由结算确认上报推进」= kernel 屏文件 docstring「序号推进半部已随旧腿退役」+ 完备锁注记;附记 A3 依据 = 同测试文件尾在册注(「三审整删…源码扫描形态(README 禁止清单);防线归 review 与代码规范」)。

**验证门(三树)**:

- docs:`screens/boss_briefing.md` grep `占位|零容器` 零命中;grep `零写端` 仅 §6 一处(动作侧口径)保留。
- src:`cw_screen_boss_briefing.py` grep `占位` 零命中(wait_one_one/deploy_not_full/armory_box 三文件命中保留,不在门内)。
- 测试仓:`test_cw_obs_arch_phase_screens.py` BOSS 简报段 grep `占位` 零命中;模块头 grep `消费点集合迁移前后不变` 零命中(A3 退役申报生效);`uv run pytest sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py -k boss_briefing` 通过(改名后行为锁全绿)。

**取舍**:

- 备选 A:§3 只删占位句、不补直定语义——放弃:画面篇 §3 是「本屏读什么、什么进 GameState」的契约节,直定门/幂等/零序号写是读者重建「report 到底写不写、写什么」的必备语义;删而不补 = 契约缺页,读者被迫下钻 kernel 屏文件才能回答本节职责内的问题。
- 备选 B:§6 同批补「观察侧写端见 §3」指针——放弃:§6 动作侧零写端与审查项⑥一致,非失真面;加指针属表述优化,超本发现辖域(§1.2 明确不解决),不立修法。

### 2.3 F-3 修法:§1 消费点计数对齐「三处消费同源」

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `screens/boss_briefing.md` §1 误派链根治句 | 「…+ 外循环阶段一位面过渡身份臂 boss 判别排他(第四消费点);原 0q 兜底随…」 | 序数改「(第三消费点)」,余句不动 |
| 2 | 同文件 §1 排他接管条目标题 | 「**阶段一位面过渡身份臂排他(第四消费点)**」 | 「**阶段一位面过渡身份臂排他(第三消费点)**」 |

依据:全 src grep `is_boss_briefing_texts` 运行时消费恰 3 处 = `cw_screen_boss_briefing.py`(op 内锚兜底)/`cw_screen_battle_wait.py::hit_settle_completion_anchor`(完成白名单)/`cw_loop.py`(位面过渡身份臂排他接管);卷首红线与 op 模块头枚举序 = ①op 锚兜底 ②battle_wait 白名单 ③loop 排他臂,身份臂 = 第三;「第四」= 0q 兜底(2026-09-16 退役,§1 同段自述)退役后的残留计数。

**验证门**:`screens/boss_briefing.md` grep `第四消费点` 零命中;grep `消费点` 各命中行计数口径全篇一致(三)。

**取舍**:备选 = §1 去序数化(两处只写「排他接管」,不与卷首枚举对位)——放弃:误读击穿事故的防线之一 = 消费点计数可机械核对(卷首枚举 ↔ 全码 grep 数对得上),序数对位是该核对工具的载体;历史事故恰源于计数漂移,保留对位、改对数值比重构枚举改动更小且保防守价值。

### 2.4 F-4 修法:develop 侧在册登记 #26 bot 处理句滞后 + game 侧修正文本方向

**件 1(本批落,develop 侧在册)**:`screens/boss_briefing.md` 开放设计注新增注③,目标语义(整条照此成文):

> ③ game 侧时序 #26 校准对象列「bot 处理」句(cw_loop 分支 2 OCR「点击空白处继续」命中即点)描述的是已退役旧接线;现役 = 阶段一画面身份分发专用本 op(观察门 = 徽记模板锚 ∨「强敌」片段判别兜底,不 OCR 提示文案,见 §1/§3)。#26 口述时序列本体(「点击空白处继续」出现即稳定、可点)仍有效且被 README §5.1 正确引用,不在修正面。修正归 game 侧文档批。

**件 2(登记诉求,game 侧文档批落笔,本批零改动)**:`docs/game/currency_war/research/screen_flow_timing.md` #26 校准对象列「bot 处理」句替换方向(供 game 侧批采纳,采纳时按其正本行文风格组织):

> bot 处理:阶段一画面身份分发专用 op `CwScreenBossBriefing`(观察门 = 徽记模板锚 ∨「强敌」片段判别兜底,不 OCR 提示文案)→ 点「区域-空白点击」推进一次 → 交回外循环重判(boss 战直接开打,商店不开);位面过渡身份帧含 boss 判别片段时由外循环身份臂排他接管派发同 op。

依据:件 1 登记 = 审查 F-4「未在册」差距的直接收口(在册机制先例 = 同篇注①对 #14/#27 的登记方式);件 2 文本 = `cw_loop.py` 身份派发段(按「货币战争-BOSS简报」身份派发)与位面过渡身份臂排他接管段 + `cw_screen_boss_briefing.py` 观察门/act 的现役 as-built;game 侧批辖域 = 「game 侧档案修正归 game 侧文档批」(同篇注①在册口径)。

**验证门**:`screens/boss_briefing.md` 开放设计注含注③且语义同上;`docs/game/currency_war/research/screen_flow_timing.md` 本批零 diff(game 侧正本不在本批文件面)。

**取舍**:备选 = 本批直接改 game 侧 #26——放弃:同篇 #14/#27 同性质欠账的在册处置口径 = 「修正归 game 侧文档批」(注①);本批单点代改 #26 会造成同一正本两种欠账处置口径,且 game 侧正本的滞后句应归 game 侧批一次对账清偿,逐句零星代改破坏批辖域分层。

### 2.5 落地文件面总表(单文档方案的修正面汇总)

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `screens/op-layer.md` | §3 全形态行 report 列一处(F-1) | 正本语义更新 |
| `screens/boss_briefing.md` | §1 两处计数(F-3)、§2/§3/§4(F-2)、开放设计注③(F-4)——同文件一次成文 | 画面篇 as-built 同步 + 在册登记 |
| `operations/cw_screen/cw_screen_boss_briefing.py` | observe docstring 标题行一处(F-2 附记 B) | 注释 |
| sr-od-test `test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py` | BOSS 简报测试函数名/docstring/断言消息 + 模块头消费面锁申报订正(F-2 附记 A1/A2/A3;断言体零改动) | 测试措辞 |
| (登记面,归 game 侧文档批)`docs/game/currency_war/research/screen_flow_timing.md` | #26 校准对象列「bot 处理」句(F-4 件 2,替换方向见 §2.4) | game 侧修正 |

统一验收:全部修法零行为变化(src 唯一 diff = 一行 docstring,sr-od-test 唯一 diff = 函数名/docstring/消息/模块头申报行,断言体逐字不动);§2.1/§2.2/§2.3/§2.4 四道验证门全部通过;修后口径互查——`screens/boss_briefing.md` §1/§2/§3/§4 ↔ op 模块头 ↔ `kernel/cw_screen_report/boss_briefing.py` 模块头 ↔ `screens/op-layer.md` §3 ↔ `screens/README.md` §5.1 五处无新分叉。
