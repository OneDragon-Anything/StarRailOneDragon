# attack10 —— 备战契约接口收口为单动作(无前提对抗审查)

> 审查对象:design.md / landing.md / README.md(本目录);`strategies/impl/cw_strategy.py::decide_prep_screen` docstring(工作区未提交修改);`strategy-docs/README.md`(工作区未提交修改)。
> 方法:全部数值/引文/码点直调复核(代码本体、正本文档、测试仓、tools/);行号以当次工作区实态为准。**未读同目录 attack.md–attack9.md**(既有审查工件,不在对象面);发现全部来自本报告自取证据。
> 已知范围外(不重复计发现,与任务书申报一致):strategy-docs/README §2 分篇表缺 14/15/16/17/21 五行;entry.py 头注「18 类」计数漂移与决策核内灭失契约工作副本引用族(设计 §1/§2.1 已申报归属);CW skill「测试分层」行 L1 路径笔误(design §2.5/landing 3.1 已内联正确命令,本报告直调确认内联路径 `sr-od-test/test/sr_od/application/currency_war` 实存)。

## 一、发现清单

### F1(中)设计边界申报不完备:changes/ 引用同族残留债(四文件面之外)无归属申报

- 位置:`design.md` §1「明确不解决」第三条(`entry.py`/`mandate.py` 契约工作副本引用族「归决策核行为变更大批顺带收敛」)+ §2.2(「同族同批清,不留保留申报口子」仅辖四文件)。
- 攻击过程:按 §2.2 扫尾关键词族(`unified-action-factory`/`design.md`/`DESIGN.md`/`统一设计稿`)对本批四文件之外全仓直扫,同属「代码禁引 changes/ 内容」铁律(AGENTS.md「文档规范」铁律段)与 .debug 归档稿死指针族的引用至少存在于:
  - `operations/cw_op/cw_action_registry.py` L1(「design.md §2.3」)、L7(「design.md §2.4」)、L12(「unified-action-factory 批2b R3」)、L147(「design.md §2.5」);
  - `strategies/impl/mandate_v1/adapter.py` L8/L45/L70;`criteria/contracts.py` L272;`criteria/levelup.py` L48/L350/L439;`mandate_state.py` L44;`economy_cycle.py` L3(`.debug/temp/.../DESIGN.md` 路径);`sell_gate.py` L617/L1014;`statefn/predicates.py` L265-266/L279/L317;`criteria/sell.py` L164/L167;`entry.py` L212/L659/L919/L921;`mandate.py` L297/L299/L1619-1620/L1723/L1914/L1976/L2205。
- 失真点:§1 的不解决清单把残留债地图窄化为「决策核内灭失契约工作副本引用族」并给了归属批(决策核行为变更大批);实态是同族债横跨 registry/adapter/criteria/mandate_state/economy_cycle/sell_gate/statefn 等 ≥10 个文件,其中多数既不在「决策核」辖内、也不属「契约工作副本」子族,**没有任何归属申报**。读者按 §1 建立的残留债地图会漏掉这一整块;「决策核行为变更大批顺带收敛」的归属承诺实际只覆盖残缺子集。
- 影响:无行为影响、非本批义务(本批四文件面自身清理完备,5 处实数经独立复核准确);属设计依据失真(边界完整性),残留债有永久无人认领风险。
- 修正方向:§1 不解决清单补一条「归档设计稿/changes 裸名指针族(四文件面之外:registry/adapter/criteria/mandate_state/economy_cycle/sell_gate/statefn 等)同为既有债,归属待登记(或并入决策核行为变更大批的顺带清单并扩其申报面)」;或在 landing 3.3 后附既有债登记项,不让它停留在无声状态。

### F2(中)正本更新清单/3.3 裸名人工复核「已知位」漏挂:`game_state/action-logic-state.md` §3 L161 死符号指针 `kernel/cw_prep_actions.py::PREP_ACTION_TYPES`

- 位置:`landing.md` 正本更新清单 #13(只改同段 L163「首项」句)与 3.3 完成判据(裸名人工复核「已知位 = projection_contract.md §4.1 与 action_exec.md §1」);正本本体 `game_state/action-logic-state.md` L161。
- 攻击过程:①直调 `kernel/cw_prep_actions.py` 模块头(本报告直读):「本模块原为族B 备战动作词表宿主(PrepAction 动作全集 + PREP_ACTION_TYPES + action_key);统一词表归一…后动作词表退役,单一真相源 = kernel.cw_vocab(CW_ACTION_TYPES)」——`PREP_ACTION_TYPES` 为已亡符号,全 src 仅存于该墓碑注与 `cw_vocab.py` L827 教训注;②`action-logic-state.md` L161 现行句「备战域动作词表 = `kernel/cw_prep_actions.py::PREP_ACTION_TYPES` 白名单」指向死符号,且与 `flow/action_exec.md` §1(「词表单一源 = kernel/cw_vocab.py::CW_ACTION_TYPES」,即本批清单 #12 修完后该篇的口径)正本间互斥;③机械判据逐一体检:闭域三关键词(首项/空批/list[PrepAction])对该行零命中(本报告独立全树重跑证实);「PrepAction」大小写敏感裸名 grep 不命中 `PREP_ACTION_TYPES`(全大写下划线形);3.3 裸名人工复核的已知位枚举不含 action-logic-state.md §3。
- 后果:批后该死指针在**已被本批修改的同一小节隔壁**(#13 改 L163)存活,是「正本与实现一致」验收域内的已知反例而三道判据(关键词/裸名 grep/已知位清单)全部拦不住。
- 修正方向:正本更新清单补条目「action-logic-state.md §3 L161:词表白名单改指 `kernel/cw_vocab.py::CW_ACTION_TYPES`」;或把 3.3 裸名人工复核口径改为大小写不敏感 `prep.?action` 全形扫描并把该处列入已知位。

### F3(低)flow.py L422-423 节头注含扫尾关键词「结算惰性 drain」,设计未点名、未给归类理由

- 位置:`design.md` §2.3(flow.py 点名 6 处:L105/L112/L133/L139/L695-696/L699);实码 `strategies/impl/flow.py` L422-423:「`# ===== 决策入口统一内务:黑板帧代次消费(ADR-0583 §3.2/§3.4;原前置的结算惰性 drain 已删除)=====`」。
- 攻击过程:本报告按 §2.2 关键词族对 flow.py 全文独立实扫,除设计点名的 6 处外还有此 1 处命中(`结算惰性 drain`)。该处与 bridge L117/flow L699 的死口径性质不同——它是「已删除」墓碑注(事实正确),三分处置下合理归宿是「保留申报」,但设计既未点名也未申报理由,实现者需自行裁断,与 §2.2「逐处点名,实现者不再自行判断改不改」的定稿纪律相抵(机械兜底可兜住,故低)。
- 修正方向:§2.3 补一句:flow.py L422-423 节头注 = 墓碑注保留申报(理由:已删除标记非死口径);或顺带把括号半句收敛掉。

### F4(低)同一句族两态:设计改 flow.py L695-696 的「既有波批优先级 逐帧取首项」,语源本体 `mandate_v1/shop.py` L758 同措辞既不清理也不申报

- 位置:`design.md` §2.3(flow.py `decide_shop_action` docstring 定稿「选择序 = 决策本体候选扫描序,逐帧恰取一个动作」);实码 `strategies/impl/mandate_v1/shop.py` L758:「选择序 = 既有波批优先级逐帧取首项(ADR-0517 §映射…)」。
- 攻击过程:直调 shop.py `decide_shop_action`(L749 起):全函数、优先级序顺序扫描返首个可行动作——设计对其「顺序候选扫描、无 entry.emit 式发射组织」的定性属实,flow.py 侧定稿文本不虚构语义(该点成立)。但 shop.py 本体 L758 与被改句同源同文、不在四文件面、landing 3.1 范围的「不含:商店线判据」也未点名它。批后同一机制在 flow.py 称「候选扫描序」、在其决策本体自述称「波批优先级取首项」,一族两态;后续任何复用 3.1 关键词集的 src 侧口径巡检会对 shop.py 产生假命中与困惑(shop.py 句语义仍真,故低)。
- 修正方向:§2.3 补一句申报:「shop.py L758 本体措辞系同语源、语义仍真,不在本批文件面,登记为将来商店线批顺带收敛」。

## 二、核实为真(要点;完整码点见攻击面清单)

- 审查对象 2(`decide_prep_screen` docstring,工作区 diff 前后对照):现行 as-built 文本十句主张逐句属实——①签名仍 `-> list[CwAction]`、波批遗留定性(git diff:HEAD 版为「序列契约 v1,2026-09-03 冻结」,工作区已重写为 as-built 口径,与 design §1「现行文本已是 as-built 口径;landing 3.1 ① = 新契约语义落位非重复处理」声明一致);②输入 = `session.prep_obs_frame`(写者白名单 = cw_screen_prep L977,读者声明 = cw_strategy_session L204);③「两处消费循环同构取首项」(L2029/L2234 调用、L2043/L2248 `actions[0]`);④列表 = 三遍编排发射组织(bridge `decide_from_turn` L259-291:emit→route_tag→truncate);⑤空序列合法 + stall 兜底归外循环(L2038-2041/L2243-2246,wait=1.0);⑥画面转移走终结动作;⑦已退役语义 + `flow/action_exec.md` §2(执行契约无成败回执)/§3(无 fail-stop、对账归下一入口)指针真实且内容吻合;⑧帧稳定分类在决策核内仍活;⑨生命周期四件归流程侧(与 flow/README §2.2 L82 同清单);⑩观察帧缺失即抛错(bridge L120-125 ValueError)。零发现。
- 审查对象 3(`strategy-docs/README.md` 工作区 diff):「策略↔流程契约」行「契约成员 13、单动作循环;序列语义为历史注」——13 = abstract 12 + 工厂 1,与 cw_strategy.py 模块头/类头及 flow/README §2.2(L40/L84)三方一致;两个孤立表格行 19/20 已归位 §2 分篇表(L38-39,编号序介于 18/22 之间,行结构完好),目标文件 `19_reinforce_channel_and_survival_discount.md`/`20_large_balance_must_spend.md` 实存、一句话概括与篇首主题相符;文尾残行删除干净;「flow/ 七篇」实数 7 个 md。零发现。
- 验收判据可执行性专项:①3.1 验收 grep 八关键词(`空批/取首项/契约 §/契约 v/序列契约/list[CwAction]/结算惰性 drain/§4.1`)对 §2.1 基类定稿句、§2.2 码块与 None 分支注释、主循环头注定稿(「序列消费」不撞「序列契约/序列发射」)、lifecycle docstring 定稿、§2.3 全部定稿文本(含 bridge 定稿句「决策核发射序列」不撞「序列发射」)逐词过 = **零互斥**;豁免申报(`decide_from_turn -> list[CwAction]` 签名 = bridge L262 未改行)准确。②3.3 闭域三关键词(首项/空批/list[PrepAction])本报告独立全树重跑:changes/ 之外活正本命中恰落清单 #1-#15 + 豁免表(`flow/README` L77/L81 历史注节、`proofs/validations/P51_V3_REBUILD.md` L391 直读确认「R31-2 首项=1」系拟合器标签序位,豁免正当)——**域内完备**;F2 的缺口在关键词域之外。③四文件扫尾:5 处 changes/ 引用实数准确(L664/L984+985/L2103-2106/L2325-2326/L2537);「flow/action-logic-state.md → game_state/action-logic-state.md」笔误属实(flow/ 下无此文件)。

## 三、实际攻击过的面(逐面,含直调码点)

1. **消费端两循环实态**:`cw_screen_prep.py` L2004-2014(头注块,「三遍编排序保持…取首项…」与「逻辑态未建模…保守回退」两句在位)、L2015-2016(`_visit_acts`/`actions: list = []` 预声明)、L2025-2043(主循环 decide 调用/try-except 文案/F3 形状校验文案「策略输出非 list[CwAction](F3)」/空批分支 detail 与 wait=1.0/取首项)、L2044-2050(「契约 §2」F3 validate 注释)、L2102-2115(终结判定注释 + changes/ 引用 + 逻辑态直写)、L2118-2121(访问上限交回)、L2204-2212(lifecycle docstring 终结出口枚举含「空批/控制流/逻辑态未建模」)、L2218-2255(lifecycle 同构段逐行)、L2306-2321(终结/直写/上限)、L2323-2354(`_terminal_exit` docstring「design.md unified-action-factory §2.4」+ OpenBoxOp 分支)——与 design §2.2 before 描述逐行吻合,新码块可直接落码。
2. **changes/ 引用 5 处实数**:L664/L984-985/L2103-2106/L2325-2326/L2537 独立 grep 复核恰 5 处;L2537 同点自证 OpenBookcard 系画面 op 侧发射(cw_screen_prep `_clear_prep_cards` 直构经执行器)。
3. **决策核零改动面**:`bridge.py` 全文(L1-31 模块头 §4.1/契约 §5/L77 类 docstring/L81/L92 DESCRIPTION/L107-130 `decide_prep_screen` + ValueError/L259-291 `decide_from_turn -> list[CwAction]`);`entry.py` L1-42(模块头「18 类」与契约工作副本灭失自证)、L194-238(四分类表:_TERMINAL 1 + _TRUNCATION_POINTS 11 + _CONDITIONAL 4 + _CONTINUE 1 = 17)、L241-324(`truncate_frame_stable`:unknown fail-closed、首位 SellBench/DeployMove 复检截空、`emitter_*` 计数)、L441/L936(⑥ 无动作 ⇒ StartBattle)、L462/464/498/513(`prep_box/prep_tome/prep_spheres` = `Emitted.reason` 第三参);`mandate.py` L1298-1299/L1753/L1956-1965(注释 3 处 + M7 回排 classify 调用)。
4. **契约成员数与注册面**:cw_strategy.py 全文(abstract 12 + create_state 工厂 = 13;B4 缺省 None L111-115;封闭集);flow/README §2.1 L47/§2.2 L40/L53-66/L77-84(备战接口行 L64 引文逐字、历史注节、契约成员数);flow.py L194-213(L105/112 死指针)、L450-467(`_consume_shop_direction_frame`)、L422-431(`_consume_prep_direction_frame` docstring「结算槽 drain 已删除」自证)、L688-740(`decide_shop_action` L695-696/L699 引文逐字)、L742 起(`decide_shop_screen` 驱动器)。
5. **None 通道三点依据**:entry ⑥ 段、truncate 防御边、17/18 类计数(`cw_vocab.py` L830-839 CW_ACTION_TYPES 备战子集实数 18;分类表覆盖 17;OpenBookcard 唯画面 op 侧)——三点全部直调成立。
6. **正本更新清单 18 条引文逐条直调**:flow/README L6(「未建模面保守回退」在卷首迁移注)/L17-18(「决策取│首项」跨行拆分属实,L18 行首「首项」可命中)/L23/L64;projection_contract L89-90(「族 B PrepAction 列表」裸名句在位);action_exec L9(「备战域 PrepAction 全集」)/L28;op-layer L14/L21(分域表述引文逐字);prep.md L15/L32/L33/L53;screens/README L52/L91/L122-133/L130;22_prep_screen L8/L28;02_mandate_layer §7 L82(「永不返回 None」+「逐帧取最优首项」同句);action-logic-state L163;prep-executor-actions L13;P51_V3_REBUILD L391 豁免正当;`cw_action_registry.py` OpenBoxOp `terminal = True`(cw_open_box_action.py L39)+ screens/README §6 无 OpenBox 行(item #17 前提全部成立)。
7. **sim/回放/测试/工具影响面**:sim 消费仅商店驱动器(cw_replay.py L112 直调 `decide_shop_screen`;flow/README §2.3/§2.4 注记);`tools/cw/replay_to_md.py` 头注自证离线记录渲染、tools/ 全目录 grep 旧文案与 `decide_prep_screen` 零命中;sr-od-test 全仓 `decide_prep_screen` 仅 `test_cw_p2_blood_band.py` L213-216 桩子类(`*a, **kw` 形状免疫),「空批/list[CwAction]/取首项/非 list」零命中——「在册锁零更新义务」「无工具/测试/哨兵依赖旧文案」成立(skill scripts 同样零命中);`src/.../telemetry/journal_query.py` 实存(§2.6 基线来源路径有效);L1 命令路径实存。
8. **遥测键族**:`emitter_*`(entry 计数写点)、`deploy_emit_*`/`deploy_exec_*`、`t1_interest_prep_emit`(mandate L1368)、`wanted_leg_*`(L1015-1045)、`m1p_*`(L1801-1881)、`sphere_defer_*`(entry L485-516)实码在键;`prep_box/prep_tome/prep_spheres` 系 reason 标签非计数键——§2.6 键族写死与「勿 grep」提示属实。
9. **规范遵循**(iteration-design.md):README 两节模板合规(无详设行正确删除);design §0/§1/§2(单文档方案即完整设计)+ §3 取舍齐;landing 三阶段七件齐、固定末阶段 = 正本更新、清单行「文件:节 ← 阶段」格式合规;依据就地标注密度达标;定稿文本无过程叙事;changes/ 引用寿命纪律(设计/landing 引 design.md 自身合法,寿命 = 迭代)。
10. **治本核**:§1 归层 = 表示层成立(消费语义 2026-09-06 已迁移而签名未跟,双向实证);备选 A(契约面收口 + 核内 list 保留)有活机制依据(首项选择序 4 真实调用 + EV-骨架拓扑合并),非症状补丁;备选 B/C/D 弃因对权威源(op-layer §1.1 分域句/§1.4 恒可用终结/规范主诉求)逐条核验无空洞;None 通道三点依据全部直调成立;行为零变化论证(bridge 取首项与消费端同源同位、空序列→None 逐义映射、B4 旧 list 空否均 fail、无静默垫片)自洽。

## 四、结论

- 发现总数 **4**:中 2(F1 边界申报不完备、F2 正本清单/裸名已知位漏挂)+ 低 2(F3 扫尾命中未点名、F4 同句族两态未申报)。
- 高危:**0**。设计的事实面(码点/引文/行号/计数/键族/测试影响面/验收判据互斥性与闭域完备性)经全面直调**无一失真**;审查对象 2、3 零发现。
- F1/F2 均为「完备性申报」缺口而非事实错误:不修不会导致实现错误或行为变更,但会留下无归属的既有债(F1)与三道判据全盲的正本-实现矛盾(F2),建议在定稿前随设计修订一并收口。
