# attack11 —— 2026-09-15-prep-single-action-contract 无前提对抗审查

> 审查对象:①迭代设计 README.md / design.md / landing.md;②工作区未提交修改 `src/sr_od/application/currency_war/strategies/impl/cw_strategy.py` 的 `decide_prep_screen` docstring(逐句核 as-built 属实);③工作区未提交修改 `docs/develop/sr_od/application/currency_war/strategy-docs/README.md`(「策略↔流程契约」行接口数表述 + 文尾孤立表行 19/20 归位)。所有数值/引文/码点/计数均直调复核,未转述。

## 一、发现清单

### F1(中)正本路径笔误同族 3 处只点名 1 处,扫尾词族兜不住孪生

- **位置**:`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_prep.py` L985、L1000、L1187(均为 `flow/action-logic-state.md` 死路径;正本实际在 `game_state/action-logic-state.md`,flow/ 下无此文件);design.md §2.2 死口径收敛清单。
- **攻击过程**:design §2.2 只点名「L984 同行正本路径笔误顺带修正(『flow/action-logic-state.md』→『game_state/action-logic-state.md』)」。本审查对该文件全量 grep `action-logic-state`:命中 3 处——L985(「R9 逻辑态全覆盖」注释块内,即 design 点名处)、L1000(`_project_prep_obs` SellBench 分支注「flow/action-logic-state.md §2.4 溢出条件行」)、L1187(`_execute_tool_atom` docstring「工具原子逻辑态(R8 七类逐件;规则正本 = ``flow/action-logic-state.md``」)。后两处是独立注释,不与 L984 同块;design §2.2 的收尾扫尾词族(`契约 §`/`契约 v`/`序列契约`/`序列发射`/`空批`/`取首项`/`结算惰性 drain`/`unified-action-factory`/`design.md`/`DESIGN.md`/`统一设计稿`)与 landing 3.1 验收词集(8 词)均不含 `action-logic-state`,对这两处孪生**结构性零命中**。
- **为什么是问题**:该扫尾的自述目标是「防枚举漏孪生,结构性判据……本扫尾是完备性的机械兜底」——本例恰是枚举漏了孪生而机械兜底兜不住的实例;且 design 对 changes/ 引用清理明言「同族同批清,不留保留申报口子」,笔误族同理却只清 1/3。按稿落码后同文件内同族正本指针两套路径并存(L985 指向 game_state/,L1000/L1187 仍指向不存在的 flow/),实现者与验收者都会面对「同一文件两种写法哪个对」的自行判断。
- **修正方向**:design §2.2 死口径清单补点名 L1000/L1187(同款改 `game_state/action-logic-state.md`),或扫尾词族补 `action-logic-state` 一词(全文 grep 三处全入处置)。

### F2(低)清单 #19 修复 action-logic-state.md 后,prep-executor-actions.md L9 偏差注联动过时,处置无口径

- **位置**:landing.md 正本更新清单 #19;`docs/develop/sr_od/application/currency_war/game_state/logic-updates/prep-executor-actions.md` L9(「文档-实现偏差(词表白名单载体)」注)。
- **攻击过程**:L9 现文引用「action-logic-state.md §3 头原文『备战域动作词表 = kernel/cw_prep_actions.py::PREP_ACTION_TYPES 白名单』;实况 = …单一源 = `kernel/cw_vocab.py::CW_ACTION_TYPES`…本篇按实现写入」。清单 #19 把 action-logic-state.md L161 的该句改为 CW_ACTION_TYPES 口径后,L9 所引「§3 头原文」不复存在,偏差注从「记录正本偏差」变成「引用一段已不存在的原文」。清单 #14 只覆盖同文件 L13(发射形态首项句),未给 L9 联动处置。
- **缓解在位**:3.3 闭域检查的裸名人工复核扫描形含 `PREP_ACTION_TYPES`,会命中 L9 并走「新发现(补入清单修毕)」路径——兜底存在,但「修后偏差注是删是改为对齐声明」无口径,依赖实现者自行判断,与 §2.2「逐处点名,实现者不再自行判断改不改」的原则不一致。
- **修正方向**:清单补一条(prep-executor-actions.md L9 偏差注随 #19 联动收敛:删注或改为「已与 action-logic-state.md §3 对齐(CW_ACTION_TYPES 口径)」),并给明处置形态。

### F3(低)bridge.py 模块 docstring L9 引用已删除的 decision_v2/adapter.py,不在 §2.3 点名处置内

- **位置**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/bridge.py` L9(「decision_v2/adapter.py 头注同款分拆先例」);design.md §2.3。
- **攻击过程**:直调文件系统,`strategies/impl/decision_v2` 与 `strategies/decision_v2` 目录均不存在(decision_v2 整包已删,flow/README §2.1「decision_v2 已随 commit b94e9cfb 删除」互证)——L9 是指向已删代码的死指针,与 §2.3 收敛对象同性质(灭失物引用)。§2.3 对 bridge.py 模块 docstring 的点名处置含 L3(`§4.1`)与 L14(`契约 §5`),未含 L9;扫尾词族亦无 `decision_v2`。
- **为什么只是低**:它是「分拆先例」引用而非契约语义引用,不在 §2.3 声明的收敛类(契约工作副本死引用/结算惰性 drain/归档稿指针)的逐字辖域内;不落码也无验收歧义。
- **修正方向**:随 §2.3 ⑤(模块 docstring 同族残留处置)一并点名:改语义表述(如「app/decision 分桶先例」)或删除该括注。

### F4(低)§2.6「哨兵无依赖」申报的证据域不含哨兵脚本实际位置

- **位置**:design.md §2.6(「已核无工具/测试/哨兵依赖旧文案(测试仓与 tools/ 零命中)」)。
- **攻击过程**:哨兵不住 tools/ 也不住测试仓——实际位置 = `.dsh/skills/sr-od-currency-war-dev/scripts/`(cw_sentinel.py / cw_batch_stats.py / cw_early_stop.py / cw_runs_gap.py 四件)。按申报括号内证据域(测试仓与 tools/)复现核查,覆盖不到「哨兵」半句。本审查代跑:四脚本对 `空批|取首项|list[CwAction]|策略输出非` 全部零命中——**申报结论为真,论据域不全**。
- **修正方向**:§2.6 证据域补哨兵实际路径(skill scripts/ 四脚本),或在 landing 3.2 实机烟雾前置核查清单里落一条可执行命令。

## 二、核为属实、不计发现的面(要点)

以下主张均直调证实,列此防后续轮次重复消耗:

- **设计↔代码计数全对**:`CwStrategy` abstract 12 + 工厂 1 = 契约成员 13(grep @abstractmethod 恰 12;create_state 非 abstract);决策核可发射 17 类全被四分类覆盖(`_TERMINAL` 1 + `_TRUNCATION_POINTS` 11 + `_CONTINUE` 1 + `_CONDITIONAL` 4 = 17,+OpenBookcard 画面 op 侧 = 18,与 entry.py 头注「18 类」漂移的定性自洽);帧稳定分类/截断 mandate_v1 包内真实调用恰 4 处(bridge L290、entry L8+L297、mandate L1965),mandate.py 注释提及恰 3 处(L1299/L1753/L1951-1957);cw_screen_prep.py changes/ 引用恰 5 处(L664/L984/L2103-2106/L2325-2326/L2537);flow.py 面③归档稿指针恰 4 处(L105/L112/L133/L139)。
- **行号锚零漂移**:两决策循环(L2029/L2234)、预声明(L2016/L2220)、主循环头注块(L2004-2014)、lifecycle docstring 终结出口枚举(L2211-2212)、空批文案两处(L2041/L2246)、F3 文案四处(L2035/L2037/L2240/L2242)、正本清单 #1-#19 全部引文逐字在码(flow/README L6/L17-18/L23/L64、projection_contract L89-90、action_exec L9/L28、op-layer L14/L21、prep.md L15/L32/L53、screens/README L52/L91/L130、22_prep_screen L8/L28、02_mandate_layer L82、action-logic-state L161/L163、prep-executor-actions L13);#17 前提属实(`cw_open_box_action.py::OpenBoxOp.terminal = True` L39;`_terminal_exit` OpenBox 分支 L2344)。
- **docstring as-built 逐句属实**(工作区改后文本):「逐帧取首项、两处同构」= L2029-2043/L2234-2248 实码;「观察层写入 session.prep_obs_frame」= cw_screen_prep L977 + cw_strategy_session L202-206;「三遍编排发射组织、相对序决定首项」= entry.emit + `_merge_ev_before_frame_end` L903 + bridge L282;「空序列合法交回」= L2038-2041;「终结动作 = 开箱/开店/出战」= 注册表 terminal 三件实证;「机械执行零判效、对账归观察侧」= action_exec §2/§3;「帧稳定分类在决策核内仍活」= entry.classify/truncate;「生命周期机制归流程侧」= action_key/deploy_fail_counts/stall 门/强制出战均在流程与 kernel,策略器零实现。
- **strategy-docs/README.md 修改属实**:19/20 两文件存在、编号序归位(18→19→20→22)、一句话描述与文件标题/内容相符;「契约成员 13、单动作循环;序列语义为历史注」与 flow/README §2(L40/L77/L84)及代码三方一致;flow/ 目录实有 7 个 md(含 README),「七篇」宽口径成立。
- **行为零变化论证成立**:bridge 边界取首项与消费端原取首项同位同值(均在 truncate 之后);emit ⑥ 空则补 StartBattle(L943-944)使常态非空;可达空边 = truncate 条件续复检截空,现走空批 round_success、改后走同义 None 分支;unknown 首位边不可达(17 类全覆盖);测试仓与 tools/ 对旧文案零命中,test_cw_p2_blood_band.py L215-217 桩子类 `*a, **kw` 形状免疫;replay_to_md.py 为 decisions 记录流渲染器、不调备战契约接口;sim 唯一决策入口 = 商店面(flow/README §2.3 L91)。
- **验收判据互斥性成立**:3.1 验收 8 词 × §2.1/§2.2/§2.3 全部定稿文本(含主循环头注定稿的「序列消费」不撞「序列契约/序列发射」、bridge 定稿句「发射序列/空序列」不撞「序列发射/序列契约」)逐词过 = 零互斥;`list[CwAction]` 豁免申报唯一性成立(四文件全量 grep:非改写行仅 bridge L262 decide_from_turn 签名);3.3 豁免表三点均必要且属实(flow/README L77/L81 在历史注节内;P51_V3_REBUILD.md **L391** 直读确认「R31-2 首项=1」系拟合器标签序位);ruff F 在 pyproject select 内(F841「必红」主张成立);`_consume_prep_direction_frame` docstring 自证结算 drain 已删;design §2.6 键族全实存(`emitter_*`/`deploy_emit_*`/`deploy_exec_*`/`t1_interest_prep_emit`/`wanted_leg_*`/`m1p_*`/`sphere_defer_*`),`prep_box/prep_tome/prep_spheres` 确系 `Emitted.reason` 路由标签非计数键;`telemetry/journal_query.py` 存在。

## 三、范围外确认(与任务申报一致,未计入发现)

strategy-docs/README §2 分篇表缺 14/15/16/17/21 五行(既有缺口);entry.py 头注「18 类」计数漂移与决策核内灭失契约引用族(entry.py L8/L15/L194/L210/L221/L245/L254 等命中,≥8 处属实);mandate_v1/shop.py L758 同措辞句在码;CW skill「测试分层」L1 路径笔误(design/landing 内联命令与测试仓实路径一致)。另注:全仓「15 号稿」引用族 30 处(含 cw_screen_prep.py L218/L902/L915)为第三族死指针既有债,设计未声称穷尽全仓死指针且词族不触发,归属将来注释卫生批,不计发现。
