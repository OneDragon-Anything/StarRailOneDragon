# attack13 — 无前提对抗审查报告(2026-09-15-prep-single-action-contract)

> 审查者 = 干净上下文对抗 agent。对象:①迭代设计三件(README/design/landing,未读 attack1-12);②工作区未提交的 `cw_strategy.py::decide_prep_screen` docstring(as-built 逐句核);③工作区未提交的 `strategy-docs/README.md` 阅读时点行(07 出辖登记篇)与已随 df25f6d94 入库的「策略↔流程契约」行、14-17/19/20/21 分篇行。
> 方法:全部数值/引文/码点直调复核,未采信任何转述(含既有 attack 工件)。行号以本次工作区实态为准。

## 结论

**发现 5 条:高 0 / 中 2 / 低 3。** 审查对象 2(docstring as-built)与审查对象 3(strategy-docs/README.md)零发现。设计主体扎实:签名/None 语义/定稿文本/消费端改写/正本清单 19 条引文与全部行号锚逐字核实无漂移;验收判据互斥性、豁免申报、3.3 闭域完备性均独立重跑成立。两条中危集中在**机械扫尾关键词域之外的死指针/死路径族**:同族问题在 bridge.py 被 §2.3 点名处置,在另两处面内文件却既不收敛也不申报面外。

## 发现清单

### F1(中)`flow/action-logic-state.md` 正本路径笔误族全仓 7 处,设计只登记面内 3 处,面外 4 处零申报

- **位置**:`kernel/cw_game_state.py` L2071、L2074、L2133;`kernel/cw_vocab.py` L801(面外);对照 design §2.2 已登记的 `cw_screen_prep.py` L985/L1000/L1187(面内,本次直调逐处确认在码)。
- **证据**:全仓 grep `flow/action-logic-state`(src 域)= 7 处命中,分布如上;正本实际在 `game_state/action-logic-state.md`(glob 确认存在,`flow/` 下无此文件)。design §2.2 表述为「正本路径笔误**同族实态 3 处**(L985/L1000/L1187)顺带修正」,§1 面外存量申报**只覆盖 changes//归档稿死指针族**(≥10 文件列举),路径笔误族不在其列。
- **攻击过程**:设计对 changes/ 死指针族做了完整的面外申报(§1 第四个「明确不解决」),对同为自己引入的收敛对象「路径笔误族」却只按面内计数陈述,未申报 cw_game_state.py×3 与 cw_vocab.py×1 的面外存量——同一族两种边界纪律,违反自身「同族同批清,不留保留申报口子」的对偶完整性;且扫尾关键词 `action-logic-state` 只作用于四文件,面外 4 处结构性不可见,将来的口径巡检会对这 4 处产生与本次已修 3 处同形的假信号。
- **修正方向**:二选一——①design §1 面外存量申报补一行「`flow/action-logic-state.md` 路径笔误族面外存量 = cw_game_state.py 3 处 + cw_vocab.py 1 处,归全仓注释卫生批顺带」;②直接扩入本批(4 处均为注释 docstring,零行为)。

### F2(中)已删 decision_v2 包死引用:面内 2 处漏收(含 `cw_strategy.py` 模块头失真 as-built 主张),面外 4 处未申报

- **位置**(面内):`strategies/impl/cw_strategy.py` L4-5「唯一内置具现 = ``DecisionV2Strategy``(注册桥在 ``strategies/decision_v2_strategy.py``;default 栈已退役,ADR-0466)」;`strategies/impl/flow.py` L202-203「方法体逐字平移自 ``decision_v2/strategy.py`` DecisionV2Strategy 同名方法」。
- **位置**(面外,注释提及):`telemetry/schema.py` L469、`kernel/cw_equip_wear_plan.py` L256、`kernel/cw_registry.py` L1317、`operations/cw_screen/cw_screen_planner.py` L197。
- **证据**:①`strategies/` 目录实存仅 `__init__.py` 与 `mandate_v1_strategy.py`,`decision_v2_strategy.py` 不存在;全 src 无 `DecisionV2Strategy` 类定义(仅注释提及);②flow/README §2.1 管理器行「注册面封闭集 = {mandate_v1}(decision_v2 已随 commit b94e9cfb 删除)」;③design §2.3 第 5 点对 **bridge.py L9 的同族引用**(`decision_v2/adapter.py`「整包已删,先例指针死」)明确给出「改语义表述或删」的处置——同族同性质指针在本批两个面内文件中却不在任何清单。
- **攻击过程**:L4-5 不是单纯死指针,是**反向的 as-built 失真**(自称的「唯一内置具现」已是已删类,现行唯一具现 = MandateV1Strategy)——与 design §3 备选 C 弃因里「持续误导新策略实现者」同型的危害,且就落在本批第①个改动文件的模块头。机械扫尾 12 词族(`契约 §`/…/`design.md`/`action-logic-state`)对这三行零命中,三分处置兜不住。
- **修正方向**:design §2.1/§2.3 补登记:cw_strategy.py 模块头首段改写为现行口径(唯一内置具现 = mandate_v1,注册桥 = `strategies/mandate_v1_strategy.py`);flow.py L202-203 平移出处改 git 可溯表述或删;面外 4 处注释提及随 F1 同款面外申报录入。

### F3(低)`lifecycle_decision_cycle` docstring 首行「架构设计 §5.1」不可解析指针

- **位置**:`cw_screen_prep.py` L2205 首行「段3-5 单动作决策循环(**架构设计 §5.1** 后三段逐动作迭代)。」
- **证据**:design §2.2 对该 docstring 的处置只覆盖「终结出口枚举整句定稿」,首行未挂。直调 `architecture.md`(活树唯一「架构设计」候选)章节为中文序号(一~九),无 §5.1;flow/README、strategy-docs 亦无对应节——指针在活树内不可解析(疑指已归档的 ADR-0517 迁移批设计件,与 bridge.py 裸「§4.1」同族,后者设计已点名删)。
- **修正方向**:随 §2.2 该 docstring 定稿顺带处置首行(删括注或改语义表述,如「五段生命周期后三段」),或在 §2.2 点名保留申报。

### F4(低)`strategy-docs/22_prep_screen.md` 存量死词表/死路径引用与 item 11 同文件,验收机械判据不可见

- **位置**:L22「组合 `RunDeploy`」、L26「`(+PickBoxCard)`」、L27「`RunEquip`/`RunTools`」、L25「`kernel/cw_prep_actions.py::OpenShop`」。
- **证据**:RunDeploy/RunEquip/RunTools 已随统一词表退役(prep.md §4、screens/README §4 后注、entry.py `_CONDITIONAL` 注释三处互证;CW_ACTION_TYPES 22 类无此三类);PickBoxCard 已删(entry.py L196-197、cw_open_box_action.py L33-34);`cw_prep_actions.py` 现仅承载 PrepObservation 与采晶矿挑选函数,无 OpenShop 转发(grep 确认),OpenShop 单一源在 `cw_vocab.py`。landing item 11 触同文件 L8/L28,但 3.3 闭域三关键词与 PrepAction 裸名扫描对这些行零命中,验收不会发现。
- **修正方向**:item 11 扩两条(L22/L26/L27 词表列改现役载体、L25 指针改 `cw_vocab.py::OpenShop`),或 design §1 申报该存量归属将来批;鉴于本批已触同文件同表,顺手收敛成本近零。

### F5(低)§2.1 基类 docstring「整段替换·同款待遇」读法下输入载体句丢失风险

- **位置**:design §2.1 第 5 款(定稿关键句不含 `session.prep_obs_frame` 输入半句)× §2.3 第 2 点「docstring 核心段以下方定稿关键句**整段替换**,不逐点拼补(**与 §2.1 基类 docstring 同款待遇**)」。
- **证据**:两种读法分歧——按 §2.1 括注(只删「形状遗留注/已退役语义注」)读,输入句保留,无损失;按 §2.3「同款待遇=整段替换」读,基类 docstring 丢失输入载体描述,且与 §2.3 桥定稿句(显式含「输入 = ``session.prep_obs_frame``(缺失即抛错)」)不对称。基类 docstring 是契约的第一落码文档,输入句属「照抄语义」应保内容。
- **修正方向**:§2.1 补一句「输入句(『输入:``session`` 唯一数据总线……``session.prep_obs_frame``……』)原样保留」,或定稿关键句补输入半句。

## 零发现面与已证清单(实际攻击过的面)

### A. 验收判据可执行性专项(landing 3.1/3.3)

- 3.1 验收 8 词 × 全部定稿文本(§2.1 基类句/§2.2 码块与 None 分支注释/主循环头注定稿/lifecycle docstring 定稿/§2.3 五处+桥定稿句/flow.py 两处定稿句)逐词过 = **零互斥**;`decide_from_turn -> list[CwAction]`(bridge L262)豁免申报属实且确非本批改动行。
- design §2.2 扫尾 12 词族对四文件全量重跑:命中与设计枚举一一对应(cw_screen_prep 13 行/bridge 5 行/flow 3 行/cw_strategy 2 行——后者两行即现行 docstring 的「序列契约/序列发射」,随 §2.1 整段删除收敛),**关键词域内枚举完备**;F1/F2 均在域外。
- 3.3 闭域三关键词(`首项/空批/list[PrepAction]`)全树独立重跑:changes/ 外活正本命中恰落清单 #1-#15 + 豁免表(flow/README L77/L81 在历史注节;`proofs/validations/P51_V3_REBUILD.md` L391 直读确认「R31-2 首项=1」系拟合器标签序位,豁免正当);PrepAction 裸名已知三位(projection_contract §4.1 L89「族 B PrepAction 列表」/action_exec §1 L9「备战域 PrepAction 全集」/action-logic-state §3 L161 `PREP_ACTION_TYPES`)逐一在码,`PREP_ACTION_TYPES` 全 src 零定义(仅 cw_prep_actions.py 墓碑头注与 cw_vocab.py L827 教训注),「大小写敏感 grep 不命中、靠 #19 人工覆盖」判据读法成立。
- #14 联动预判正确:prep-executor-actions.md L9 偏差注所引 §3 头原文(#19 改写后)确会失配。

### B. 设计引文与码点直调(全部逐字/逐行属实,零漂移)

- 消费端两循环:decide 调用 L2029/L2234、try-except 同构、F3 形状校验文案「策略输出非 list[CwAction](F3)」L2035-2037/L2240-2242、空批分支「空批(本帧无动作),交回外循环重观察」wait=1.0 L2041/L2246、空批注释「契约 §4」L2039/L2244、F3 校验注释「契约 §2」L2044-2045/L2249-2250、`actions[0]` L2043/L2248、预声明 L2016/L2220、主循环头注块两句死口径 L2004-2014、lifecycle 终结出口枚举「空批/控制流/逻辑态未建模」L2211-2212、`_terminal_exit` 与终结判定注释 L2103-2106/L2306-2321/L2323-2333、R9 分支已删自证 L2110-2113/L2312-2315。
- changes/ 引用恰 5 处:L664/L984/L2103-2106/L2325-2326/L2537;路径笔误面内 3 处 L985/L1000/L1187(首处语句起于 L984 ✓)。
- bridge.py:签名/首句双重死引用 L109、「契约 §3.2/§3.3」L115、「结算惰性 drain」L117(实码 L127 只调 `_consume_prep_direction_frame`)、DESCRIPTION L92、裸「§4.1」L3/L81、「契约 §5」L14、decision_v2/adapter 先例 L9、类首句 L77;`decide_from_turn` 返回 list L259-262、truncate 调用 L290、R196 症5 复检语境 L266。
- 决策核:emit ⑥「无动作 ⇒ 出战」+ `if not out` 补 StartBattle entry.py L936-944;`truncate_frame_stable` 四分类表 11+1+1+4 = **17 类全覆盖**(L200-217),OpenBookcard 决策核零引用(mandate_v1 全包 grep 零命中,发射位 = `_clear_prep_cards` 画面 op 侧,cw_vocab L703-705 自证)⇒ 备战域 18 类 = 17 + OpenBookcard,「17/18」两口径与 entry 头注「18 类」漂移定性全部成立;条件续复检空边(SellBench L309-315/DeployMove L317-324 首位失效槽截空)属实;`_merge_ev_before_frame_end` L1148-1160;包内 4 真实调用(bridge L290/entry L297+L1157/mandate L1965)+ 3 注释提及(mandate L1299 凑息卖、L1753 M1″、L1951-1957 M7 回排)逐点在码;entry 模块头 L16-19 契约工作副本灭失自证 + 重锚 action_exec §1 在码。
- flow.py:墓碑 L422-423/L430、decide_shop_action L695-696/L699、面③四处死指针 L105/L112/L133/L139、`decide_prep_screen` 保持 abstract L33、`_consume_shop_direction_frame` L450 在码。
- 终结集:OpenBoxOp terminal=True(cw_open_box_action.py L39)、OpenShopOp L31、StartBattleOp L53——主循环头注定稿补 OpenBox 有据。
- 遥测键族 `emitter_*`/`deploy_emit_*`/`deploy_exec_*`/`t1_interest_prep_emit`/`wanted_leg_*`/`m1p_*`/`sphere_defer_*` 全实存;`prep_box/prep_tome/prep_spheres` 确系 Emitted.reason 路由标签(entry L462/L464/L498/L513),「勿 grep」提示准确;`telemetry/journal_query.py` 实存。
- 影响面:测试仓 `decide_prep_screen` 仅 test_cw_p2_blood_band.py L213-216 桩子类(`*a, **kw` 形状免疫),空批/取首项/策略输出非/list[CwAction] 零命中;tools/、`replay_to_md.py`(零消费备战契约)、哨兵 4 件(`.dsh/skills/sr-od-currency-war-dev/scripts/` cw_sentinel/cw_batch_stats/cw_early_stop/cw_runs_gap,旧文案零命中)、`legacy_baseline` 全仓零标记——§2.4/§2.5/§2.6 申报全部成立;L1 命令路径实存;ruff select 含 F(F841 必红成立)。

### C. 审查对象 2:`decide_prep_screen` docstring as-built(工作区改后文本)——逐句属实,零发现

①签名仍 `-> list[CwAction]`+波批遗留定性(git diff 对照 HEAD「序列契约 v1,2026-09-03 冻结」确认重写);②输入 = `session.prep_obs_frame`(cw_strategy_session.py L202-206)+ 跨步状态(defer 计数 = sphere_defer_* 挂 strategy_state.cw4_counters、意向状态机挂 session.strategy_state);③两处循环同构只取首项;④列表 = 三遍编排发射组织、`_merge_ev_before_frame_end` 相对序、尾部不消费;⑤空序列合法交回 + stall 兜底归外循环;⑥禁空批表达控制流、终结 = 开箱/开店/出战(三 op terminal=True);⑦已退役语义 + `action_exec.md` §2(机械执行零判效)/§3(无 fail-stop/恢复原语、对账归下一入口)指针真实且内容吻合;⑧帧稳定分类在决策核内辖发射组织;⑨生命周期四件归流程侧(action_key=action_exec §1 L11;执行失败记忆=deploy_fail_counts,action_exec §6 L58 + flow/README §2.2 L82;stall 门=flow/README §4;强制出战=L82 同清单);⑩观察帧缺失即抛错(bridge L120-125 ValueError)。注释规范(中文/持久索引/无会话局部标识符)合规。

### D. 审查对象 3:strategy-docs/README.md——零发现

未提交行(07 出辖登记篇):与表内 07 行「跨局 meta 域:显式声明出辖」一致,插入位与读法通顺。df25f6d94 入库部分:「策略↔流程契约」行(L60)对 flow/README §2 四要点(四身份分离/契约成员 13/单动作循环/序列语义历史注)逐一核实;「flow/ 七篇」= 实数 7 个 .md;14/15/16/17/19/20/21 七行文件全部存在;总纲 00/01/02/04、分篇 10-17+08、18-27 数字与表行一致;03/05/06/09 删除注与实态一致;两张表结构同构。命题集口径行(L13)与 math_proofs 索引「以索引为准」口径一致。

### E. 规范遵循(iteration-design.md + AGENTS.md)

README/总纲/landing 结构合规:§0-§2 齐(单文档即完整设计已申报)、阶段小节七件齐、末阶段=正本更新+清单 ← 阶段标注齐、进度只住 README、无过程叙事措辞、依据就地标注(被引权威源 op-layer §1.1/§1.3/§1.4/§4、flow/README §2.1/§2.2/§2.3、prep.md §4、strategy-work §4 三项——sim 可观测性声明/锚点事前写/实机-sim 分工,均在 skill references L51/L53/L55 逐条实存);外溢面均显式申报自成批,符合 §1.1 边界判定。

### F. 治本核验

§1 归层=表示层成立(消费语义 2026-09-06 落码迁移而签名未跟,flow/README L6 + 两循环实码双向实证);备选 A 治根(契约形状是规范直接对象),核内 list 保留有活机制依据(4 真实调用点 + EV-骨架拓扑合并,非死形状);备选 B/C/D 弃因逐条对权威源核验无空洞(None 通道三点依据:op-layer §1.1 分域句逐字在码 L21、防御空边与 unknown 不可达实证、StartBattle 出战标准 26_battle_settlement.md 在册 + §1.4「备战=开战」恒可用终结);行为零变化论证成立(bridge 取首项与消费端同源同位、空序列→None 逐义映射、wait=1.0 保持、B4 旧 list 返回无论空否均响亮 fail、注册面封闭集无静默垫片)。
