# T-3 战斗等待·结算 修法设计(battle_wait)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:触顶定稿,残留 3 低按用户裁定**残留随批清偿**(对抗轨迹:r1 未收敛 4 条→修订→r2 未收敛 3 条→修订→r3 未收敛 3 条→修订→r4 触 4 轮上限;清偿 = N-r4-1 登记面第五条与 §2.7 行 8 计数「两处」改「三处」并补 15_observation §1 观察通道登记表 hp 行(L16)+ N-r4-2 门② 归属句去「flow 侧」限定对齐 §2.7 行 8(§1.1 括注同步)+ N-r4-3 边界句补「改名重锚族」排除声明(§1.1 括注与 §2.2),修法主体零改动——三条处方均一行级声明/计数修补)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-3-r1.md`(发现 F-1..F-6;总判定 = 有问题,高 0 中 3 低 3)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准,落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`,行号仅作本稿定位辅助。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)。
- 修法性质:F-1..F-6 全部为文档语义更新与注释清理,**零行为变化**(无任何逻辑/签名/常量改动)。

## 1. 问题与动机

### 1.1 F-1 结算策略半「槽保留」声明与代码不符(中)

- **现状症状**(审查报告 F-1):终态契约批已把 `session.pending_round_outcomes` 槽连同其写半整体删除——全树 grep `round_outcomes` 仅命中注释,`StrategySession` 无该字段、无任何写点/读点;但三处正本/模块头仍以现在时描述「槽保留为只写不读的观察累积面」:`flow/README.md` §2.2 非契约成员 bullet 与生命周期注(两处)、`screens/battle_wait.md` §6「策略半入槽」条、`strategies/impl/flow.py::CwFlowStrategy` 模块头辖域列表。同注中观察半列举「performance.record/last_streak/last_hp 过置信门/last_hp_t」的 last_streak/last_hp/last_hp_t 三个 session 锚均已退役,列举未随迁。
- **根因归层**(根源两问):①根在哪层 = **约定层为主、语义层为辅**——机制删除批的收尾没有「退役符号引用面全量清查」这道门,删除动作与记载更新解耦,记载面(语义层)于是留下现在时死句;②修的是根还是症状 = 本稿两件事并做:辖内记载面全量改写为现役契约(治已发生的漂移),并给落地批配可机械验证的收尾判据(全树 grep 退役符号仅允许命中「已删除」申报语义,§2.1 验证门)——把本批辖内的约定缺口用判据关上。F-2/F-5 与本件同根(同一删除批的不同残留面),本稿以同一范式一次覆盖,不立第二套机制(跨件半问答案:同根,禁逐件症状补丁)。
- **解决到哪**:`flow/README.md` §2.2 两处、`screens/battle_wait.md` §6、`flow.py` 模块头改为现役归宿口径;审查 F-1 现状摘录点名的两处代码注释残留(`kernel/cw_strategy_session.py` StrategySession 字段区断句残段、`cw_screen_battle_wait.py` 方法体删除申报注)同批收敛;`_record_round_outcome` docstring 标题「+ 策略半入槽」半句为本稿自查增补(#6 修)。
- **明确不解决**:正本侧的同源漂移(`screens/prep.md` 可信门条括号句、`strategy-docs/04_survival_budget.md` §7 表 #6 行、`strategy-docs/26_battle_settlement.md` 卷首供数句、`flow/session.md` §2.1 留存清册多行、`strategy-docs/15_observation_multisource_arbitration.md` 缺陷定位与豁免面两处及 §1 观察通道登记表 hp 行(L16))——审查报告未单列,登记为 §2.2 同源登记面待裁决(清点方法 = §2.2 验证门②:无同名字容器符号的 session 锚族——含 last_owned_equips/briefing_affixes/briefing_bosses——已入 token 模式;同名容器族不入 token 模式,归 session.md 清册小批人工对账;改名重锚族(prep_frame_class/shop_frame_class)不入 token,处置归属 = T-1 稿面a F-3 登记面(其门5 辖零命中);equip/briefing 族现在时残留处置归属 = T-1 稿已登记面);`kernel/cw_strategy_session.py` 其余退役账注块的墓碑风格(归 §2.6 全仓注释卫生批);『删除批收尾清查缺口』的流程级根,本稿验证门只保本批修后零残留、不防下一删除批复发——跨批处置登记为 §2.1 跨批登记面(归宿建议与不立的权衡见彼处)。

### 1.2 F-2 gated_hp 条目与代码不符(中)

- **现状症状**(审查报告 F-2):`flow/README.md` §2.3 仍记「**gated_hp**(结算 HP 新鲜度门,单一实现的 helper):结算真值仅在可信窗口内覆盖现读——观测质量门,非决策输入」;全树 grep `gated_hp|apply_hp_freshness_gate` 仅命中退役申报注释,helper 不存在。现役形态 = `kernel/cw_hp_policy.py::decision_hp`(gs.hp 直读)+ `hp_decision_trusted_of`(容器可信位)。
- **根因归层**:与 F-1 同根(同一删除批的收尾清查缺口,症状落在 §2.3 装配矩阵条目);语义层表现为「机制已死、条目仍以现在时给契约」。修法范式与验证门同 §2.1,不重复立论。
- **解决到哪**:§2.3 条目改写为现役决策 hp 读口与可信位契约(依据指针同步从 04_survival_budget §7 表 #6 改指 `cw_hp_policy` 符号锚 + `../game_state/fields.md` §2.1)。
- **明确不解决**:§2.2 所列五处登记面(prep.md 括号句、04_survival_budget 表 #6、26_battle_settlement 卷首句、session.md 清册、15_observation 两处;登记面不扩本稿落地文件面);`kernel/cw_hp_policy.py` 模块头自身的迭代件引用(归 §2.6 卫生批)。

### 1.3 F-3 battle_wait.md §4/§8/§9 未随「继续挑战臂迁 CwOpSettleConfirm」更新(中)

- **现状症状**(审查报告 F-3):画面篇仍写点击与长按兜底发生在宿主 `_dispatch_frame` 内、并声明「全部动作 = 驻留状态机内的留守机械臂」;实际该臂 = 委托独立画面框 op `cw_op/cw_op_settle_confirm.py::CwOpSettleConfirm`(点击 + M39 长按兜底 + 遭遇奖励兑现回调 + `report_node_advance(trigger='settle_confirm')` 推进上报),宿主仅保留采集钩子/读点/指纹计数/委托与失败 bail。§4「上报」列(「无自上报」)与 §9 遥测面亦未反映「货币战争-结算确认」op 的 journal 行与节点推进上报(`action_exec.md` §2.1 已在册,唯画面篇未同步)。
- **根因归层**:**约定层**——编排迁移批的收尾义务清单漏了画面篇 as-built 同步(代码已迁、文档未迁),不是语义或表示错误(代码现状正确且两正本一致)。修法 = 文档同步到现役编排,属记载面单面。
- **解决到哪**:`screens/battle_wait.md` §4(开头声明/动作对照表行 1/分支表行 1)、§8(长按兜底句)、§9(遥测面)四处同步。
- **明确不解决**:任何行为变化(代码零改动);`screens/README.md` §5.6 概述行(未点名委托 op,但概述粒度不构成失真,审查未列发现,不动)。

### 1.4 F-4 陈旧指称与悬空引用集(低)

- **现状症状**(审查报告 F-4):§5 出口表写白名单符号为 `COMPLETION_ANCHORS`(实符号 = `cw_screen_battle_wait.py::SETTLE_COMPLETION_ANCHORS`);§6「节点类型」行写「结算屏权威 > session 节点探针值 > 槽序表兜底」(代码现役 = 首领识别锚 > gs 推导 > 探针表,探针表宿主 = `gs.node_books` 非 session);开放设计注③描述的模块头不一致已消解、剩余「详见交付偏差清单」为无路径悬空引用(指向会删减的迭代过程件);§3/§6 未记结算金读链现役形态(token 解析失败 → `read_settle_gold_opt` 右上角定点读 + 稳定门)。
- **根因归层**:**表示层**(符号名/指称随迁移漂移)+ **约定层**(正本引用指向无路径过程件,违反「代码与正本文档禁引 changes/ 内容」与「引用必须是持久索引」)。
- **解决到哪**:四个点位逐条改正(§2.4)。
- **明确不解决**:各时序值的实机充分性(报告 §4 已声明静态审查不判)。

### 1.5 F-5 结算链代码注释引用已退役符号(低)

- **现状症状**(审查报告 F-5):`kernel/cw_plane_table.py::node_t_of` docstring 以现在时把 `session.last_hp_t` 写点与 `cw_hp_policy.apply_hp_freshness_gate` 当契约对方(均已删,现役生产消费点 = battle_wait killed hp 对比兜底的轮次邻接门时基);`kernel/cw_economy.py` STREAK 段注释称「结算源 session.last_streak 方向可靠」(已删,真值归宿 = gs.streak 结算覆盖写端)。读者按注释找符号落空。
- **根因归层**:语义层——F-1/F-2 同根家族的注释面残留件(删除批清查缺口),修法范式同 §2.1。
- **解决到哪**:审查两处 + `cw_plane_table.py` 同文件同病两 docstring(审查未单列)改现役消费面口径(§2.5)。
- **明确不解决**:`node_t_of`/`schedule_of`/`nodes_of_plane` 函数行为与其消费点(零改动);cw_plane_table/cw_economy 之外文件的同类残留(卫生批)。

### 1.6 F-6 审查对象注释面普遍存在 W/rN/迭代任务号与变更史叙述(低)

- **现状症状**(审查报告 F-6):`operations/cw_screen/cw_screen_battle_wait.py`(模块头及全文件)与 `operations/cw_op/cw_op_settle_confirm.py`(模块头)系统性出现 W 轮次号(W971/W7/W239)、审计轮次号(r68 等)、迭代任务/设计件编号(T-42/E-2/P1.5/05-battle §N/「迭代 2026-09-20-… design §N;landing §N」/攻击 BN)与「何时改/从什么改成什么/迁入迁出」叙述,命中 AGENTS.md §8 两种禁形。
- **根因归层**:**约定层**——注释纪律(AGENTS §8「禁会话局部标识符」「变更史不进注释」)为后立规范,存量注释未回溯清理,且无周期性卫生机制;本批只清审查对象,机制缺口的根治 = 另立批。
- **解决到哪**:两文件命中点按统一清理准则清零(§2.6),并登记同族联动面。
- **明确不解决**:CW 全域乃至全仓的存量注释卫生(建议另立全仓注释卫生批,本稿不外推命中清单、不扩文件面)。

- **在册核对一致项**:审查报告 §3 已确认一致的面(驻留豁免申报、settle_confirm 推进上报契约、对账唯一发生点、观察质量门、决策控制铁律、结算时序与终结语义、观察半单一写点成立、九节其余面)本稿不立修法,仅作为各修法不得触碰的现状边界——落地时禁借清理之名改动这些在码语义。

## 2. 方案

### 2.1 F-1 修法:结算「槽」叙述整批退役

逐点位给目标语义(语义选择唯一;行文由实现者按各正本既有行文风格组织,不逐字代写):

| # | 位置 | 现状(病句核心) | 目标语义 |
|---|---|---|---|
| 1 | `flow/README.md` §2.2 非契约成员 bullet(`~~_drain_pending_round_outcomes~~` 条尾) | 「……裁决落地删除;`session.pending_round_outcomes` 槽保留为观察半累积面」 | 尾句改:「槽连同写半已整删,现不存在(`StrategySession` 无该字段,全树零写点零读点);结算真值现役归宿 = `kernel/cw_game_state.py::apply_settlement_cover` 容器覆盖 + `performance.history`」 |
| 2 | `flow/README.md` §2.2 注(生命周期) | 「观察半(performance.record/last_streak/last_hp 过置信门/last_hp_t)= battle_wait 结算点即时直写(……单一写点),策略半原经 `session.pending_round_outcomes` 待加工槽惰性 drain——该消费半已随退役批删除,**槽保留为只写不读的观察累积面**。旧 `decide_prep_action` 薄委托已删(P5 挂账兑现)」 | 改写为:「旧 `on_round_end` 拆两半——观察半 = battle_wait 结算点**即时直写**(`cw_screen_battle_wait._write_settlement_observation` 单一写点 → `performance.record`;同点过 hp 置信门更新 `SettlementState.last_outcome_hp`),策略半(`session.pending_round_outcomes` 待加工槽惰性 drain)已随消费侧退役**整删——槽与写半均不存在**。旧 `decide_prep_action` 薄委托已删(git 历史可溯)」。要点:观察半列举剔除 last_streak/last_hp/last_hp_t 三个已退役 session 锚,补入现役的 `SettlementState.last_outcome_hp` 置信门 |
| 3 | `screens/battle_wait.md` §6「策略半入槽」条 | 「**策略半入槽**:`session.pending_round_outcomes` 追加 `RoundOutcome`(只写不读的结算观察累积面)」 | 整条删除;同节「观察半直写」条补一短句:「同点过 `hp_confidence ≥ 0.9` 门更新 `SettlementState.last_outcome_hp`(summary final_hp 真值源)」,使画面篇与 `flow/README.md` §2.2 注的观察半口径同文 |
| 4 | `strategies/impl/flow.py::CwFlowStrategy` 模块头辖域列表 | 「`session.pending_round_outcomes` 槽 = 观察半累积面(决策消费侧已退);」 | 整行删除——辖域列表记「有什么」,已删机制零辖域 |
| 5 | `kernel/cw_strategy_session.py` StrategySession 字段区「结算观察累积槽」残段(审查 F-1 摘录点名) | 断句残段:「……拆两半的存活半)。观察层在(终态契约 §B:pending_round_outcomes 槽已删……本槽只写不读;……)」——句子断头、括号失衡、删除申报内自相矛盾(「本槽只写不读」) | 收敛为单句删除申报:「pending_round_outcomes 槽已随消费侧 drain 退役整删——结算真值归宿 = gs 结算覆盖写端(`apply_settlement_cover`)+ `performance.history`」;迭代件引用(「终态契约 §B」)清出,ADR-0638 引用保留;残段内另两枚持久指针——ADR-0583 §2.5 与 `04_survival_budget §7 #7/#8`——随收敛**一并弃置**(删除申报的出处指针 = ADR-0638 单枚足够,不留多枚出处抄本) |
| 6 | `operations/cw_screen/cw_screen_battle_wait.py::_record_round_outcome` docstring 标题 | 「P1.5 观测回路:结算屏 → read_round_outcome → 观察半直写 + 策略半入槽」(标题现在时含已删半句;「P1.5」归 §2.6) | 标题改「结算观测回路:结算屏 → read_round_outcome → 观察半直写(策略半已删,见下)」——与同 docstring 正文的删除申报及 `screens/battle_wait.md` §6 既有「结算观测回路」称谓同文 |

依据(全点位共用):代码真值 = `kernel/cw_strategy_session.py` 字段区退役注(§B 槽已删)、`cw_screen_battle_wait.py::_write_settlement_observation`(观察半 = `performance.record` 单一写点)、`_record_round_outcome` 覆盖写段(`apply_settlement_cover` 容器半 + `hp_confidence ≥ 0.9` 门写 `last_outcome_hp`);规范 = AGENTS.md §9(正本永远与代码现状一致)。

**验证门(本修法完成判据,落地批照此对账)**:对 `src/sr_od/application/currency_war` 全树 grep `pending_round_outcomes|round_outcomes`,仅允许命中删除申报语义的注释;任何现在时的「保留 / 累积面 / 入槽」陈述 = 未完成。

**取舍**:

- 备选 A:保留「槽保留为只写不读」句、外加退役注解——放弃:与代码不符的现在时陈述即使加注仍会被当现役契约引用(字段不存在,引用即落空),这正是本发现的病灶。
- 备选 B:`flow/README.md` §2.2 注整段删除——放弃:旧 `on_round_end` 拆两半的归宿语义(观察半单一写点、结算真值归宿)是正本必备契约,删注即丢依据;正本改写语义,不删记载。
- 备选 C(#5):残段整块删除——放弃:块内「结算真值归宿」指针是读者找真值链的导航,收敛为单句申报即保指针;墓碑是否全删归 §2.6 卫生批统一裁决,本点位只修断句与自相矛盾。

**跨批登记面(流程级根的处置登记)**:上方验证门辖本批落地;『删除/迁移批收尾缺「退役符号引用面全量清查」门』的流程级根若不流程化,下一删除批同族症状(F-1/F-2/F-5 型)原样复发。处置登记:给删除/迁移批收尾补固定门——批内每个被删除的符号/机制,在落地文档「末阶段:正本更新」的完成判据中登记一行「全树 grep `<符号>`,仅允许命中删除申报语义」。归宿候选两选:①harness 级迭代文档规范(`docs/develop/harness/iteration-design.md`)landing 模板固定判据(全局通用,首选);②CW 域迭代收尾义务先行落地。**建议另立小批**(独立迭代子目录;harness 规范不在本批画面审查文件面),并与 §2.6 全仓注释卫生批**并案裁决**(卫生批的增量防线腿与本门同根)。若裁决不立,战术权衡显式声明:省一次小批启动成本,代价 = 每个删除批的引用面清查退回人工自觉、复发概率高,同族症状再现时再修——本稿接受该残余风险。

### 2.2 F-2 修法:gated_hp 条改写为现役决策 hp 读口契约

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `flow/README.md` §2.3 gated_hp 条 | 「**gated_hp**(结算 HP 新鲜度门,单一实现的 helper,符号锚见代码):结算真值仅在可信窗口内覆盖现读——观测质量门,非决策输入(`../strategy-docs/04_survival_budget.md` §7 表 #6)」 | 条目改名「**决策 hp 读口与可信位**」,语义改写:「hp 决策消费面统一读口 = `kernel/cw_hp_policy.py::decision_hp`(gs.hp 直读)——『上一真值』由结算覆盖写端 + carried 语义承载(`../game_state/fields.md` §2.1);可信位另经 `kernel/cw_hp_policy.py::hp_decision_trusted_of`(`gs.hp.source ∈ {observation, carried}`,prior/logic fail-closed),禁与本口混写双位判定;新增 hp 决策消费点必经读口或登记豁免(消费同门申报纪律 = cw_hp_policy 模块头,承接 ADR-0583 §2.4)。原『gated_hp 结算 HP 新鲜度门』(可信窗覆盖现读)已删除,失读窗不再有锚补,识别失准走识别优化批(git 历史可溯)」。依据指针从 04_survival_budget §7 表 #6 改指 cw_hp_policy 符号锚 + fields.md §2.1 |

依据:代码 = `kernel/cw_hp_policy.py` 模块头(辖域申报:`decision_hp` 直读、`hp_decision_trusted_of` 容器可信位、旧新鲜度门随锚退役删除)、`decision_hp`/`hp_decision_trusted_of` 函数 docstring;规范 = AGENTS.md §9。

**同源登记面**(同根残留,审查报告未单列;不扩本稿落地文件面,建议随本迭代正本更新批一并清点,目标语义如各条):

- `strategy-docs/04_survival_budget.md` §7 表 #6 行:行主语改「决策 hp 读口与可信位」,符号锚列改 `cw_hp_policy.decision_hp`/`hp_decision_trusted_of`,授权状态列改「已落地」——该表自申报为 hp 消费「唯一登记处」,留死行 = 登记处失真。
- `strategy-docs/26_battle_settlement.md` 卷首「结算读数供数」句:hp 真值链改「结算读点经结算覆盖写端直入 gs(`apply_settlement_cover`),决策消费经 `cw_hp_policy.decision_hp` 读口」(现文指已删符号 `strategies/impl/cw_strategy.py::gated_hp`)。
- `flow/session.md` §2.1 留存清册:`last_hp`/`last_hp_t` 等多行所列字段已随终态契约批删除,清册需一次 as-built 对账收敛(划线退役或删行)——面较大,建议独立小批,不与本稿捆绑。
- `screens/prep.md` §3 可信门条括号句:「(`cw_strategy.py::gated_hp` = 策略实现层既有调用点的薄委托)」以现在时指已删符号——处置 = **删除括号句,主句「门」随 §2.2 #1 口径改「读口」**(「统一经 `kernel/cw_hp_policy.py::decision_hp` 读口;可信位另经 `hp_decision_trusted_of`」),避免 flow/README 称「读口」、prep.md 称「门」的同一机制两正本称谓第二源;薄委托归宿 git。
- `strategy-docs/15_observation_multisource_arbitration.md` 三处——缺陷定位叙述与「显式豁免面」申报两处(含已退役 `last_level_obs` 现在时链;cap 失读兜底链指称)+ §1 观察通道登记表 hp 行(L16:「③对账层 `session.last_hp_real`;④二值化第三级」及结论列「+对账层+trusted 位」「`read_hp_opt`/`reconcile_hp()`」现在时死引用)——处置 = 按现役容器真值链改写(L16 对账层句与 reconcile_hp() 列随同一处置:对账腿已随 hp 锚删除简化,现役 = hp 直读通道 + 可信位;现役符号锚随该篇 as-built 对账核定),归 F-1 同源登记面。

**取舍**:备选 = 删除 §2.3 条目——放弃:§2.3 是装配与依赖矩阵,hp 决策消费的读口/可信位/申报纪律是现役装配语义,删条即让「决策 hp 必经读口」纪律在 flow 正本失去登记位;且 04_survival_budget §7 表作为唯一登记处需要对应行,删条会加深两处口径分裂。

**验证门(双树)**:①src 树(判据同 §2.1 验证门):grep `gated_hp|apply_hp_freshness_gate` 仅允许命中删除申报语义;②docs 树(登记面收口判据):对 `docs/develop/sr_od/application/currency_war/` 下 `flow/` + `screens/` + `strategy-docs/` 三目录 grep `gated_hp|apply_hp_freshness_gate|pending_round_outcomes|last_streak|last_hp|last_hp_t|last_hp_real|upcoming_types|last_node_type|nodeseq_probe_anchor|node_type_current|hp_suspect|last_level_obs|star_pending_regression|last_owned_equips|briefing_affixes|briefing_bosses`,命中行逐条分类——删除申报语义(「已删除/已退役/已删」且无现在时契约/宿主/归属陈述)= 合格;任何现在时契约陈述 = 登记面漏项(补入上列清单或随正本更新批修正);零漏项 = 登记面收口。模式族边界:token 收终态契约批退役且**无同名字容器符号**的 session 锚(last_owned_equips/briefing_affixes/briefing_bosses 的 gs 正本名分别为 equips/enemy_affixes/plane_bosses,无同名冲突,可机械清扫);**真同名容器族** = active_env/active_strategies/selected_difficulty/enemy_difficulty/chosen_megastar/chosen_partner 与 node_books 探针三槽(plane_node_table/plane_node_table_plane/plane_lengths_seen)——不入 token 模式(grep 必命中 gs 同名域现行引用,机械分类不可判),该族 docs 残留归 session.md §2.1 清册独立小批**人工对账**;**改名重锚族** = prep_frame_class/shop_frame_class(终态契约 §B 退役,gs 正本 = frame_class_prep/frame_class_shop,改名重锚无同名容器)——不入 token 模式,处置归属 = T-1 稿面a F-3 登记面(其门5 辖零命中);equip/briefing 族现在时残留的**处置归属** = T-1 稿已登记面(含 strategy-docs 侧 `strategy-docs/10_prep_decisions.md` L155/L156 的 T-1 外溢登记;本稿门②仅负责扫出)。

### 2.3 F-3 修法:battle_wait.md 三节同步「继续挑战臂委托 CwOpSettleConfirm」现役编排

行为零改动(代码现状即目标),修的是画面篇 as-built。四点位:

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `screens/battle_wait.md` §4 开头声明 | 「本屏无注册表动作 op、无策略器问询,**全部动作 = 驻留状态机内的留守机械臂**」 | 改为「动作 = 驻留状态机内的留守机械臂 + 一个画面框 op 委托臂(继续挑战推进 = `cw_op/cw_op_settle_confirm.py::CwOpSettleConfirm`,形态归属 = op-layer.md §2.1 节点推进上报族例外——非动作注册表面、无 CwAction param)」 |
| 2 | §4 动作对照表行 1(继续挑战推进臂) | 发出方式 = 宿主留守臂内点继续挑战 + 长按兜底;上报列 =「无自上报」 | 发出方式 = 「宿主采集与结算链(采集钩子 `settle_frame_collect` → 读点前等 1.5s + 重截 → `_record_round_outcome` → 新帧指纹计数)后**委托 `CwOpSettleConfirm`**:点击『货币战争-结算.按钮-继续挑战』→ 停留 ≥`CwOpSettleConfirm.SETTLE_STAY_LONG_PRESS` 轮长按 `SETTLEMENT_NEXT` 兜底 → 遭遇奖励兑现回调(`kernel/cw_encounter_selection.py::claim_encounter_reward`)→ `report_node_advance(trigger='settle_confirm')` 点击即上报;宿主对 op 失败 `round_fail` bail」。上报列 = 「节点推进上报 settle_confirm(action_exec.md §2.1;宿主侧无动作上报)」。触发返回列 = 「否(非终结):op `round_success` 交回宿主 `round_wait` 驻留,出口判定 = 宿主 ③段白名单」 |
| 3 | §4 分支表行 1(挑战成功结算) | 「……→ 点『按钮-继续挑战』;点击未生效停留 ≥SETTLE_STAY_LONG_PRESS 轮 → 长按 SETTLEMENT_NEXT 兜底推进」 | 尾段改「→ 委托 `CwOpSettleConfirm`(点击/长按兜底/兑现回调/settle_confirm 推进上报随 op);op 失败 → bail 交外循环兜底链」;宿主侧保留段(采集钩子/1.5s+重截/`_record_round_outcome`/指纹计数)不动 |
| 4 | §8 长按兜底句 + §9 遥测面 | §8:「结算屏点击未生效的长按兜底(见 §4 分支表)」;§9:仅记「战斗等待」journal op 名 | §8 改:「结算屏点击未生效的长按兜底(宿主 = `cw_op/cw_op_settle_confirm.py`:`SETTLE_STAY_LONG_PRESS` 轮阈值 + `SETTLEMENT_NEXT` 长按点;见 §4)」。§9 补两件:①journal op 名 = 「战斗等待」+ 委托 op「货币战争-结算确认」(日志前缀 `[cw-settle-confirm]`);②节点推进上报 = settle_confirm 的 journal 行(actor 归因 = `kernel/cw_game_state.py::_NODE_ADVANCE_ACTORS` → CwOpSettleConfirm;判定语义指针 = action_exec.md §2.1 / game_state/node-derivation.md §3.3);既有缺陷分键/`[cw!]` bail 留证条目不变 |

依据:代码现状 = `cw_screen_battle_wait.py::_dispatch_frame` ②段(构造 `CwOpSettleConfirm(self.ctx)` 并 `execute()`,成功 `round_wait`、失败 `round_fail` bail)、`cw_op_settle_confirm.py` 全文(点击 → 长按兜底 → 兑现回调先于上报 → `round_success` 交回宿主);规范在册 = `flow/action_exec.md` §2.1、`screens/op-layer.md` §2.1(节点推进上报族例外)、`game_state/node-derivation.md` §3.3(触发点 1)。

**取舍**:备选 = 把 §4 行 1 的「动作 op(词表参数)」列改记为注册表动作 op——放弃:`op-layer.md` §2.1 已定谳 settle_confirm 宿主 = 画面框 op 形态、非动作注册表面,画面篇照抄注册表口径即造第二源冲突;保留「无注册表动作 op」行名 + 发出方式列写委托,是唯一与两正本同时自洽的记法。

**取舍(机制俗称「M39」)**:本修法目标语义与正本全文一律不用「M39」——机制定位 = `CwOpSettleConfirm.SETTLE_STAY_LONG_PRESS`/`SETTLEMENT_NEXT` 符号锚 + 语义描述(点击未生效停留 ≥3 轮 → 长按兜底推进)。备选 = 保留「M39」为在役俗称并给 §2.6 准则 4 增补豁免——放弃:对局编号无可检索的持久索引,半年后读者无法解析该词;符号锚已完整定位机制,俗称零增量导航价值;且与注释禁形(AGENTS.md §8「禁会话局部标识符」)冲突,留之即本节与 §2.6 内部不一致。

### 2.4 F-4 修法:陈旧指称与悬空引用逐条改正

| # | 位置 | 现状 | 目标语义 | 依据 |
|---|---|---|---|---|
| 1 | `screens/battle_wait.md` §5 出口表 `back_to_loop` 行 | 「完成白名单 `COMPLETION_ANCHORS` 任一」 | 「完成白名单 `cw_screen_battle_wait.py::SETTLE_COMPLETION_ANCHORS` 任一(判定本体 = 同文件 `hit_settle_completion_anchor`)」 | 符号实名 = `cw_screen_battle_wait.py`(白名单常量 + 判定函数);screens/README.md §2(符号锚 = `文件::符号名`,as-built) |
| 2 | §6「节点类型」行 | 「结算屏权威 > session 节点探针值 > 槽序表兜底(`_node_type_from_table`)」 | 「首领识别锚(『货币战争-结算.标识-首领』画面位)> gs 推导(`kernel/cw_game_state.py::node_kind_of`;session 识别源已退役,单一源 = 容器)> 探针表兜底(`_node_type_from_table`,宿主 = `gs.node_books.plane_node_table`)> 缺省『普通战斗』;词汇表统一 = `_normalize_node_type`」 | 代码 = `cw_screen_battle_wait.py` 节点优先序段(首领锚 → `node_kind_of` → `_node_type_from_table` → 缺省)与 `_node_type_from_table` 实现(读 `gs.node_books`);session 探针宿主退役 = `kernel/cw_strategy_session.py` §A′ 注。同段代码注释的「§A′ 重锚面,宿主迁移另子件」过期子句随 §2.6 清理一并清出 |
| 3 | 开放设计注③ | ①「模块头『自动战斗检测本批不做/接口预留』与已实现自愈链不一致」——模块头现文已改「已落地」,不一致已消解;②「详见交付偏差清单」为无路径悬空引用 | **整条删除**。配套:代码模块头自动战斗检测段的「语义申报 = screens/battle_wait.md 开放设计注③」指针,随 §2.6 注释清理改指「screens/battle_wait.md §4(等待结算画面行·自动战斗自愈臂)与 §8(连续命中计时)」 | 模块头现文(`cw_screen_battle_wait.py` 自动战斗检测段「已落地」);§4/§8 已完整承载该语义(判定 = 双锚连续命中 ~5s;动作 = 点「按钮-自动战斗开关」;判效 = 单帧误判防护 + 动作后 wait 覆盖生效窗) |
| 4 | §3 观察面 + §6 容器半覆盖写条 | 未记结算金读链现役形态 | §3 解析器清单补 `read_settle_gold_opt`,并加一句读链语义:「结算金:`parse_settlement_assets` token 解析失败(当前版本结算布局无『存量 <N>』token)→ `read_settle_gold_opt` 右上角货币计数定点读 + 稳定门(首读失败补采一帧;帧间不一致取末帧 + 冲突留证,补采上限 = `SETTLE_GOLD_MAX_POLLS`);token 与定点读双失败且胜局 = 落全帧 token 留证行供解析器加固对账;败局页无面板,读失败为预期形态」。§6 容器半条补:「金读链现役形态见 §3;读失败 = gold 缺席不写(本局无金真值覆盖)」 | 调用链 = `cw_screen_battle_wait.py` 结算覆盖写段金读部分;稳定门 = `obs/cw_settlement_obs.py::read_settle_gold_opt` docstring 与 `SETTLE_GOLD_MAX_POLLS` |

**取舍**(注③):备选 = 注③改写为现役语义申报条保留——放弃:该语义的正位承载 = §4/§8 两节,注③保留即同语义第二源,重演 F-1/F-2 的双源漂移根;删注 + 代码指针改节在同一段注释内完成(§2.6 清理必触同段),零额外成本。

### 2.5 F-5 修法:注释改现役消费面口径(F-5 两处;cw_plane_table 同文件同病增补)

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `kernel/cw_plane_table.py::node_t_of` docstring | 首句「hp 新鲜度门时基(全局节点号)」;「同式契约」段的契约对方 = `cw_screen_battle_wait` 的 `session.last_hp_t` 写点与 `cw_hp_policy.apply_hp_freshness_gate` 时基契约节(均已删) | 首句改「全局节点号(battle_wait killed hp 对比兜底轮次邻接门的时基)」;契约段改现役口径:「全局节点号 t 的同源派生纪律:凡 t 语义消费必经本函数派生,禁单侧改式——单侧改式 = 轮次邻接门判域静默漂移(现役生产消费点 = `cw_screen_battle_wait._record_round_outcome` 的 killed hp 对比兜底)」;「替代表迁波曾内联 `(plane-1)*9` 字面量」的迁波叙事收敛为纯语义 why(位面真值可短于 9 时字面量使后位面段系统性偏大) |
| 2 | `kernel/cw_economy.py` STREAK 段注释 | 「streak 带符号(连胜 + / 连败 −,结算源 session.last_streak 方向可靠)」 | 「streak 带符号(连胜 + / 连败 −);真值归宿 = gs.streak 结算覆盖写端(`kernel/cw_game_state.py::apply_settlement_cover` 的 streak_after,写点 = battle_wait 结算观测),经济/观察消费读容器」 |
| 3 | `kernel/cw_plane_table.py::schedule_of` 与 `::nodes_of_plane` 两 docstring「真值源 =」句(同文件同病,审查 F-5 未单列) | 「真值源 = ``session.plane_lengths_seen``」/「真值源 = ``session.plane_node_table``」(§A′ 探针族 session 份已退役) | 改「真值源 = `gs.node_books.plane_lengths_seen`」/「真值源 = `gs.node_books.plane_node_table`」——同文件 `_probe_books` 桥与模块头 §A′ 申报即证,两函数代码体已读容器,注释未随 |

依据:`node_t_of` 现役生产消费点全树 grep 仅 `cw_screen_battle_wait.py` killed 兜底一处(与 `screens/battle_wait.md` §6「killed 兜底链」行在册口径同文);streak 真值链 = `cw_screen_battle_wait.py` 覆盖写段 `streak_after=...` + `kernel/cw_strategy_session.py` §B 注;schedule_of/nodes_of_plane 现役真值源 = `gs.node_books`(同文件 `_probe_books` 桥 + §A′ 模块头申报)。

**取舍**(node_t_of):备选 = 删除「同式契约」段——放弃:同源派生、禁单侧改式的约束在现役消费面仍成立(killed 兜底的轮次邻接门依赖 t 口径唯一),删约束句即丢防漂移契约;只换契约对方,不删契约。

### 2.6 F-6 修法:审查对象两文件注释卫生清理

**范围**:`operations/cw_screen/cw_screen_battle_wait.py`(全文件)、`operations/cw_op/cw_op_settle_confirm.py`(全文件,报告点名模块头)。零逻辑改动,注释/docstring 单面。

**清理准则(实现者照此机械执行,命中即改写)**:

1. **禁形一·会话局部标识符**:W/w 轮次与审计号(W971/W7/W239/w28)、R/r 审计号(R5/r3/r68/r362/r363)、迭代任务与设计件编号(P1.5/P4/T-42/E-2/E-3/C-1/F11/攻击 BN)、实机对局俗称(M39)、指向迭代过程件的引用(「迭代 2026-09-20-node-advance-action-report design §N;landing §N」「05-battle §N」「交付偏差清单」),以及指向 `.debug/` 等 gitignore 过程件的路径引用(他机/清理后不可解析,不构成持久索引)——一律清出;出处改持久索引(文件路径/符号名/正本文档+节)或纯语义描述(ADR 档案已退役,禁新增 ADR-NNNN 引用)。
2. **禁形二·变更史叙述**:「何时改的/从什么改成什么/勘误过程」(换装史、迁出迁回/随迁/平移、「本批只做」「逐位零改动」「已随 XX 废除」类批次叙事)——归 git 历史;注释只留当前语义 + 持久指针。墓碑注释(为已删符号留在原位的整段申报)随之清出,除非其「现役真值归宿」指针仍有导航价值——有则收敛为单句指针(形如 §2.1 #5)。
3. **改写方向**:每处命中改写为「结论→出处→边界」的当前语义;用户裁定日期随变更史清出,裁定语义本身保留并可指正本条款(如 op-layer.md §1.2 / action_exec.md §2.1);实证类出处改纯语义描述(「实机对局实证:<机制>」),日期、局号与对局俗称(M39 类)一并归 git——机制定位靠符号锚 + 语义描述,不留无锚俗称(改写示例:「长按兜底(实机对局实证:『继续挑战』点击不响应时结算屏停留 ≥3 轮 → 长按兜底推进)」)。
4. **保留豁免**:驻留状态机豁免申报(模块头,被 op-layer.md §3 与 battle_wait.md 卷首引用)必须以当前语义保留——只清其批次叙事,不删豁免理由与结构判据;ADR 引用不豁免:一律按全树 ADR 清扫批(R7 底册 `reports/R7-adr-verdict.md` §3 工单)口径处置——删号留语义或删死指针;本稿豁免清单其余各项不受影响。`screen_flow_timing #N` 为 game 侧持久索引,保留;`SettlementState` 字段坐标系/取值时机/写入端语义(AGENTS.md §8 字段定义注释要求)逐字保留。
5. **跨修法交叠(一次成文,不分批触碰同段)**:模块头自动战斗检测段 = 清 W971 + 改注③指针(§2.4 #3);`_record_round_outcome` docstring = 清 P1.5/平移叙事 + 修标题半句(§2.1 #6);②段委托注释 = 清「landing §N/攻击 BN/裁定日期」+ 委托分工语义与 §2.3 同文。

**代表命中面**(准则做全文件扫描,此表为已核对点位、非穷举;行号为设计稿定位辅助):

| 文件 | 点位(现文摘要素) | 处置 |
|---|---|---|
| cw_screen_battle_wait.py | 模块头(「W971 05-battle §1;P4 收编」、收编来源/分支随迁清单、「遥测连续性红线(W971…)」、迁移批次叙事「本批只做/逐位零改动/F11 例外清单」) | 按准则 1/2 清;豁免语义与结构判据保留(准则 4) |
| 同上 | `SETTLE_COMPLETION_ANCHORS` 注(「2026-09-16 从标题 OCR 锚换装」「曾随结算确认 op 迁出……迁回本文件独用——用户裁定 2026-09-21」) | 变更史清出;保留「BOSS简报锚 = 阵营徽记模板(OCR 标题误读免疫)」与「位面简报不列」边界 |
| 同上 | `SettlementState` 字段表(「r3 live 修」「迁移审计 w28」)、类常量注释群(「随迁自 cw_loop」「二轮审计裁决 5,随迁」「W971…超时兜底」)、类体注(长按兜底「M39……迁入 CwOpSettleConfirm……攻击 B2 归属界定」段) | 按准则 1/2 清;长按兜底归属语义保留并改当前时态(「点击/长按兜底/推进上报宿主 = `CwOpSettleConfirm`,本类保留结算链记与 ③段白名单出口」);「M39」俗称清出(§2.3 取舍) |
| 同上 | `_cw_selection_write`/`_cw_selection_capture`(E-2/E-3)、`_record_round_outcome`(P1.5/平移叙事)、「(W239)」×4、「W7 refs 迁移」×2、「r68 页1 progress 合并」、「(T-42)」、「迁移批次二,任务书件 8/R5 迁移规划 W1 ⑤」、`_defeat_latch_by_secondary`/`_mark_relaunch_residual`/`_normalize_node_type`/`_node_type_from_table`(二轮审计/r363/r362/w28/随迁)、`count_settlement_obs_coverage_miss` docstring 的 `.debug/` 深检路径引用 | 按准则 1/2 清;「refs = journal (run_id,v) 对账锚」「残留屏豁免」「同窗校验」等现役判定语义逐条保留;覆盖率守卫背景收敛为纯语义(「长战斗形态曾实锤整窗零结算观测行」) |
| 同上 | ②段委托注释(「landing §3.2;随 op 迁移……用户裁定 2026-09-21……攻击 B2 归属界定」)、文件尾五段生命周期退役墓碑 | 按准则 1/2 清;委托分工语义保留(与 §2.3 同文);墓碑删除 |
| cw_op_settle_confirm.py | 模块头(「迭代 2026-09-20-node-advance-action-report design §2.3 触发点 1;landing §3.2」「原 R3 缝结构性消失」)、类 docstring(「design §2.3 触发点 1,去证据门形态 2026-09-21」「攻击 B2」)、「M39 长按兜底(2026-08-16 3-1 实证)」注与停留计数注(M39/日期/局号清出,机制改符号锚 + 语义描述,准则 3 改写示例)、`SETTLEMENT_NEXT` 注(「画面 op 规范符合性判读 2026-09-12 整改项」) | 按准则 1/2/3 清;规范指针改指 action_exec.md §2.1 / op-layer.md §2.1 / node-derivation.md §3.3;「去证据门 = 点击即上报」「观察态门为唯一门」「归属界定(点击/长按兜底/兑现回调/推进上报随 op,结算链留宿主)」语义逐条保留 |

**同族联动面**(不扩本稿范围):该禁形遍布 CW 全域(已核对样本:`kernel/cw_hp_policy.py` 模块头「终态契约(2026-09-16-strategy-terminal-contract)」迭代件引用、`kernel/cw_strategy_session.py` 退役账注块群、obs/kernel 多文件 W/rN 残留)——**建议另立全仓注释卫生批**(独立迭代,按本节准则全仓扫描执行),本稿不外推命中清单、不扩文件面;**该批须含增量防线腿**(周期性卫生机制或退役批收尾清查门,与 §2.1 跨批登记面同根、宜并案裁决)——只清存量无防线 = 清完再脏。

**验证门(双门)**:

- 门一·模式扫描:两文件 `grep -nE '[Ww]\d+\b|\b[Rr]\d+\b|T-\d+|E-\d+|C-\d+|P\d+(\.\d+)?\b|M\d+\b|攻击 B\d|(design|landing) §\d|交付偏差清单|0[1-9]-battle|\d{4}-\d{2}-\d{2}|\.debug[/\\]'` 零命中。族覆盖:W/w 轮次与审计号(W971/W7/W239/w28)、R/r 审计号(R5/r68/r362/r363)、迭代任务号(T-42/E-2/E-3/C-1/P1.5/P4)、对局俗称(M39)、攻击轮次编号(攻击 B2)、文字型迭代件引用(design §N / landing §N / 交付偏差清单 / 05-battle)、ISO 日期(裁定/实证/换装类叙述)、gitignore 过程件路径(.debug/)。词边界防误伤:`\b[Rr]\d+\b` 不伤 `round`/`RunLoop`/`ADR-NNNN`(R 与数字间有连字符、R 前无词边界,均不命中),`M\d+\b` 不伤 `SETTLEMENT`,`P\d+` 与 `C-\d+` 不伤 `SETTLE_P1_BATTLE_TS` 类下划线标识符(P1 后跟下划线,词边界不成立)。模式与保留语义冲突时实现者停手回本稿提请修订,禁自行豁免。
- 门二·人工复查(模式不可判的形态):范围 = 两文件全文逐注释段(模块头/类与函数 docstring/行注释)按 AGENTS.md §8 两禁形人工判——重点 = 指向已退役设计件的「XX 设计 §N / 统一观察架构 §N / EXPECTED_STATE §2」类文字引用、语义级变更史叙述;判不准的停手提请,禁自行拍板。
- 收尾三件:`uv run ruff check` 两文件通过;`git diff` 确认零逻辑改动;§2.1/§2.2 验证门(退役符号零现在时)同步通过。

### 2.7 落地文件面总表(单文档方案的修正面汇总)

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `flow/README.md` | §2.2 两处(F-1)、§2.3 一条(F-2) | 正本语义更新 |
| `screens/battle_wait.md` | §3/§4/§5/§6/§8/§9/注③(F-1/F-3/F-4;同文件多点建议一次成文) | 画面篇 as-built 同步 |
| `strategies/impl/flow.py` | 模块头辖域列表删一行(F-1) | 注释 |
| `kernel/cw_strategy_session.py` | 字段区残段收敛单句(F-1) | 注释 |
| `operations/cw_screen/cw_screen_battle_wait.py` | 注释卫生(F-6)+ `_record_round_outcome` 标题半句(F-1)+ 自动战斗检测段指针改节(F-4) | 注释 |
| `operations/cw_op/cw_op_settle_confirm.py` | 注释卫生(F-6) | 注释 |
| `kernel/cw_plane_table.py` | 三处 docstring 现役口径(node_t_of + schedule_of/nodes_of_plane 同病增补)(F-5) | 注释 |
| `kernel/cw_economy.py` | 一处注释现役口径(F-5) | 注释 |
| (登记面,待用户裁决)`screens/prep.md` §3 可信门括号句、`strategy-docs/04_survival_budget.md` §7 表 #6、`strategy-docs/26_battle_settlement.md` 卷首供数句、`flow/session.md` §2.1 清册、`strategy-docs/15_observation_multisource_arbitration.md` 三处 | F-1/F-2 同源登记面(docs 树清点方法 = §2.2 验证门②;equip/briefing 族处置归属 = T-1 稿已登记面,真同名容器族归 session.md 清册小批人工对账,改名重锚族归 T-1 稿面a F-3 登记面) | 文档 |
| (登记面,待用户裁决,建议另立小批)删除/迁移批收尾「退役符号引用面全量清查」固定门——归宿 = harness 迭代文档规范 landing 模板固定判据(首选)或 CW 迭代收尾义务先行;与全仓注释卫生批的增量防线腿并案裁决 | 流程级根跨批处置(§2.1 跨批登记面) | 规范/流程 |

统一验收:§2.1/§2.2 验证门 grep 零现在时命中;§2.6 双门通过;全部修法零行为变化(无逻辑 diff);`screens/battle_wait.md` 修后与 `flow/README.md` §2.2 注、`action_exec.md` §2.1、`op-layer.md` §2.1、`node-derivation.md` §3.3 五处口径互查一致。
