# attack9 —— 备战契约接口收口为单动作 · 无前提对抗审查(第 9 批)

> 审查对象:① 迭代设计 README.md / design.md / landing.md;② `strategies/impl/cw_strategy.py::decide_prep_screen` docstring(工作区未提交修改);③ `strategy-docs/README.md`(工作区未提交修改:「策略↔流程契约」行接口数表述 + 19/20 孤立表格行归位)。
> 方法:设计稿每个代码主张逐点直调(行号锚以符号定位复核)、正本引用逐句对照、闭域 grep 独立重跑、验收判据可执行性专项。未读 attack.md–attack8.md(不在对象面)。

## 发现清单

### F1(中)bridge docstring「输出 = `list[CwAction]`(执行序=列表序)」半句无收敛点名,落地读法两可

- 位置:design.md §2.3(收敛清单五处 + 「`decide_prep_screen` 新 docstring 关键句定稿」段);代码实态 `bridge.py::MandateV1Strategy.decide_prep_screen` docstring 中部(现 L113-115):「输出 = ``list[CwAction]``(执行序=列表序),经帧稳定截断(契约 §3.2 逐类判 + §3.3 fail-closed)。」——为一个连续句。
- 攻击过程:§2.3 收敛清单第 2 项只点名后半「经帧稳定截断(契约 §3.2 逐类判 + §3.3 fail-closed)」;前半「输出 = ``list[CwAction]``(执行序=列表序)」不是灭失契约死引用,不属五处清单任何一条,其改写义务只能由定稿关键句的「输出 = 决策核发射序列的**首个动作**」隐含覆盖。而 landing 3.1 ② 把改写义务表述为「docstring/DESCRIPTION/模块头死引用收敛(§2.3 五处 + 定稿关键句)」——「定稿关键句」定位为附加物而非整段替换指令。实现者按「逐点收敛 + 关键句落位」读法执行时,改第 2 项必然触及同句,必须自行裁断前半去留:
  - 「保留前半」→ docstring 内新旧两个「输出 =」主张并存自相矛盾;该行若出现在 diff 中即为改写行,撞 3.1 验收关键词 `list[CwAction]`(验收红,逼停回查);若实现者整体不触碰该行,则归「未改行」逃过 grep 判据域,验收绿而矛盾残留——**判据域归属随实现选择摆动**,不唯一。
  - 「删除/替换」→ 正确,但该决策在设计稿中无答案,属实现者自行拍板。
- 对照:基类 docstring 同型句(「- 返回:``list[CwAction]``。形状遗留注:…」)在 design §2.1 有「形状遗留注/已退役语义注随本批删除」显式申报,bridge 侧无同等待遇——同一设计稿内同类处理不一致。
- 规范出处:iteration-design.md §5 写作硬规则 2「实现者无需再设计」(该行的命运需实现者裁断 = 未定稿);landing 3.1 验收判据「作用于 diff 新增行/本批改写行,要求零命中」对该行的读法不唯一。
- 修正方向(二选一):① §2.3 收敛清单补一处:「输出 = ``list[CwAction]``(执行序=列表序)」半句随截断句整句改写,以定稿关键句输出句替换;② 在定稿关键句段声明「decide_prep_screen docstring 核心描述段以下列定稿文本整段替换」(与 §2.1 基类「随本批删除」同款措辞)。

### F2(低)design §2.3 面③注释块四处死指针的行号-引文配对错位

- 位置:design.md §2.3(「`flow.py` 面③出辖观察件注释块的已归档设计稿指针四处顺带收敛」条);代码实态 `flow.py` L105/L112/L133/L139。
- 攻击过程:四处行号全部精确命中、数量与处置(删指针或改语义表述)不受影响,无落地风险;但行号与引文内容配对交叉错位。design 写「L112/L133『统一设计稿 §4-8』、L139『统一设计稿 §5-F4』」,直调实态:
  - L105「设计出处 = p2_blood_band_unified_design/DESIGN.md §2.3-5(a)」✓
  - L112「统一设计稿 §4-8」✓
  - L133「统一设计稿 §5-F4」(design 误记为 §4-8)
  - L139 裸「§4-8」(无「统一设计稿」前缀;design 误记为 §5-F4)
- 严重度:低(四处全在、处置一致,不导致漏删或误删;属引文转述失真)。
- 修正方向:配对改为「L105『…DESIGN.md §2.3-5(a)』、L112『统一设计稿 §4-8』、L133『统一设计稿 §5-F4』、L139 裸『§4-8』」。

## 攻击面清单(零发现面,含直调码点)

### A. design.md 码点主张逐条直调(全部属实)

1. 消费端两处决策循环:`cw_screen_prep.py` decide 调用 L2029/L2234、try/except 异常包装两处同构(L2028-2032/L2233-2237)、F3 形状校验与文案「策略输出非 list[CwAction](F3)」(L2033-2037/L2238-2242)、空批 `round_success('空批(本帧无动作),交回外循环重观察', wait=1.0)` 两处(L2038-2041/L2243-2246)、取首项 `actions[0]`(L2043/L2248)、预声明 `actions: list = []`(L2016/L2220)——行号全部精确。
2. 死口径注释:两处「空批合法(契约 §4…)」(L2039/L2244)、两处「F3 校验(契约 §2…)」(L2044-2045/L2249-2250)、lifecycle docstring 终结出口枚举七项「空批/控制流/参数非法/出战(发出即终结)/开店切换/逻辑态未建模/访问上限」(L2211-2212,与 §2.2 定稿五项删三项的映射一致)、主循环头注块两句死口径(「三遍编排序保持…帧级锁按锁纪律重推」L2007-2008、「逻辑态未建模的动作同判保守回退」L2010-2011;同函数 L2112-2113 自证「保守回退分支已删」,R9 死口径定性属实)。
3. `changes/` 引用注释恰 5 处:L664「unified-action-factory 批2b」、L984「design.md unified-action-factory §2.6」(同行 L985「flow/action-logic-state.md」路径笔误属实,该文件实在 `game_state/`)、L2103-2106 与 L2325-2326「design.md unified-action-factory §2.4」、L2537 裸「design.md §2.6」——「全部 5 处」计数与行号全中。
4. 契约成员数:基类 abstract 12(create_session + 11 决策入口)非 abstract 工厂 1(create_state)= 13(`cw_strategy.py` L97-204 逐一数过);与 `flow/README.md` §2.2(每局冷建 2 + 分画面决策入口 11,L53/L60/L84)及模块头 L13-16 三方一致。
5. None 通道三点依据:① op-layer §1.1 L21 分域表述句引文逐字一致;② emit ⑥「无动作 ⇒ 出战」段在码(entry.py L936-944);可达空边 = truncate 首位 SellBench/DeployMove 名-槽复检截空(entry.py L309-324,首位截断返回空 list 实证);unknown 首位边不可达——四分类合计 17 类(_TRUNCATION_POINTS 11 + _TERMINAL 1 + _CONTINUE 1 + _CONDITIONAL 4,entry.py L200-217 实数)覆盖 CW_ACTION_TYPES 备战子集 18 类中的全部决策核可发射类,OpenBookcard 在 entry.py/mandate.py 零引用(直调),发射臂 Emitted 直构类型全集(ClickSpheres/OpenBox/OpenShop/OpenTome/SellBench/StartBattle + 部署/穿戴/工具原子臂)均在 17 类内;entry.py 头注 L15「18 类逐类表」与实态的漂移定性属实(已申报范围外,不计);③ 26_battle_settlement.md 在册承载出战标准(22 号篇 L28 互引);op-layer §1.4 L37「备战 = 开战」恒可用终结原文一致。
6. §2.3 mandate_v1 边界:bridge.decide_prep_screen 现码 L107-130(读 prep_obs_frame、None 抛 ValueError、_consume_prep_direction_frame、decide_from_turn 签名 `registry=self.registry` 返回 list)——拟改边界取首项可直接落码;死引用逐处在码(docstring 首句 L109「契约 v1/v2 接口;序列决策契约正本 = flow/action_exec.md §1」、L115「契约 §3.2 逐类判 + §3.3 fail-closed」、L117「结算惰性 drain」、模块头 L3/L14 裸「§4.1」/「契约 §5」、类 docstring L77「三遍化决策序…+ 序列发射」/L81「§4.1」、DESCRIPTION L92「序列契约 v2 帧稳定截断发射」);「结算惰性 drain 已删除」自证在 `flow.py` L423/L430(docstring 明写「已删除」),实码只调 `_consume_prep_direction_frame`(bridge L127)。
7. 帧稳定分类/截断包内真实调用恰 4 处:bridge L290(truncate 截断发射)+ entry L297(truncate 内 classify)+ entry L1157(`_merge_ev_before_frame_end` 内 classify,R197 症1 合并语义与 §2.3 理由 1 一致)+ mandate L1965(M7 回排 classify);mandate 注释提及 3 处:L1299(凑息卖接线位,L1291 节标题佐证)/L1753(M1″ 生产发射臂段)/L1951-1957(M7 回排就地说明,调用在 L1960-1965)——归属与计数全中。
8. flow.py:decide_shop_action docstring 两处(L695-696「既有波批优先级 逐帧取首项」/L699「结算惰性 drain」)行号精确;商店决策本体 = `mandate_v1/shop.py::decide_shop_action` 顺序候选扫描(逐臂首中即 return,尾 `return CloseShop()` 兜底 L2745,无 entry.emit 式发射组织)——「不虚构发射组织语义」的定稿方向属实;面③四处死指针见 F2。
9. 契约工作副本灭失:CONTRACT_SERIES_DECISION 在 src/ 仅 entry.py L17 一处提及(即灭失自证本身),重锚 flow/action_exec.md §1 属实(action_exec §1 = 词表与注册表节,§1 L9 备战域动作全集在码)。

### B. 审查对象 2:`decide_prep_screen` docstring(cw_strategy.py,工作区未提交修改)as-built 逐句核——十句全部属实

① 签名 `-> list[CwAction]` + 波批遗留定性(git diff 确认 HEAD 为波批口径,工作区已重写为 as-built 口径,与 design §1「现行文本已是 as-built 口径」声明一致);② 输入 = session 黑板 `prep_obs_frame`(`cw_strategy_session.py` L206 在码;写者 = 观察层 cw_screen_prep L977 + 循环直写 L2115/L2315)+ 跨步状态(defer 计数 = entry sphere_defer_* 挂 state_of(session).cw4_counters;意向状态机挂 strategy_state)同 session;③ 「cw_screen_prep 决策循环两处同构、只消费首项」(A.1);④ 「列表 = 决策核三遍编排的发射组织结构,相对序决定首项,尾部不消费」(emit→route_tag→truncate→[0],`_merge_ev_before_frame_end` 相对序实证);⑤ 空序列合法交回外循环 + stall 兜底归外循环(A.1);⑥ 禁空批表达控制流、画面转移走终结动作(OpenBox/OpenShop/StartBattle 三者 `terminal=True`:cw_open_box_action L39/cw_open_shop_action L31/cw_start_battle_action L53);⑦ 已退役语义 + `flow/action_exec.md` §2(机械执行无成败回执)/§3(无 fail-stop/恢复原语)指针真实且内容吻合;⑧ 帧稳定分类在决策核内辖发射组织(entry.py L220/L241);⑨ 生命周期机制四件归流程侧(action_key = action_exec §1 L11;执行失败记忆 = deploy_fail_counts 族 action_exec §6;stall 门 = flow/README §4;强制出战 = cw_screen_prep L496/L505);⑩ 「观察帧缺失即抛错」(bridge L120-125 ValueError)。注释规范合规:中文、引用全为持久索引(文件:节/符号名)、无会话局部标识符、无变更史叙事。

### C. 审查对象 3:strategy-docs/README.md(工作区未提交修改)——与现行事实一致

1. 「策略↔流程契约」行改口「契约成员 13、单动作循环;序列语义为历史注」:13 = flow/README §2 L40「保留总成员 13」;单动作循环 = §2.2 L64/L65 在文;历史注 = §2.2 L77 段头原文;四身份分离 = §2.1——四项全与现行一致,且与审查对象 2 模块头计数三方吻合。
2. 19/20 行归位:git diff 确认为纯移动(行文本零变化),插入位 18→19→20→22 数字序正确,文尾两个孤立行已删。
3. 「flow/ 七篇」:flow/ 目录 7 个 .md(README/outer_loop/exit_chain/action_exec/projection_contract/guards/session),数字成立。
4. §2 分篇表缺 14/15/16/17/21 五篇:与已知范围外申报一致(目录实存 24 篇正文,表列 19 篇),不重复计。

### D. landing.md 正本更新清单与验收可执行性

1. 清单 18 条锚点逐条直调:#1 flow/README L17-18(「决策取│首项」跨行拆分属实,L18 行首「首项」单字面可命中且条目已预告归属)+ L23;#2 L64 引文逐字;#3 projection_contract L89「动作产出 = 族 B PrepAction 列表」/L90「单动作循环逐帧取首项」逐字;#4 action_exec L28;#5 op-layer L14;#6 op-layer L21 分域句逐字(与 design §2.1 依据 1 自引句一致);#7 prep.md L15「输出 `list[PrepAction]`——单动作循环取**首项**消费」;#8 prep.md L32;#9 prep.md L53;#10 screens/README L130;#11 22_prep_screen L8/L28;#12 action_exec L9「备战域 PrepAction 全集」;#13 action-logic-state L163;#14 prep-executor-actions L13;#15 02_mandate_layer L82(「永不返回 None」+「逐帧取最优首项」两半句均在码;姊妹篇 23_shop_screen L4/L10 已是商店域单独口径无需动,01 L179「三态全函数」无关不辖);#16 锁指针复验与 3.2「先指向、3.3 落位后复验」时序自洽;#17 前提属实(OpenBoxOp.terminal=True 直调;§4 L52 整行「非终结」、§5.3 L91 行尾「非终结」、§6 L122-133 无 OpenBox 行,三处实态与条目描述一致);#18 flow/README L6「未建模面保守回退」在码且 R9 死口径定性成立(prep.md §4 L45 与 op-layer §1.4 L38 同证「已删除」)。——引文逐字存在、行号无漂移。
2. 3.3 闭域检查独立重跑(排除 changes/,三关键词「首项|空批|list[PrepAction]」全树)= 恰 18 处命中,逐处归属:清单 #1×2/#2/#3/#4/#5/#6/#7/#8/#9/#10/#11/#13/#14/#15 + 豁免表(flow/README L77/L81 均在「序列语义历史注节」内;`proofs/validations/P51_V3_REBUILD.md` L391 直读确认「R31-2 首项=1」系拟合器标签序位,豁免正当)——**三关键词域内完备且判据唯一可执行**;PrepAction 裸名活正本位恰为已知两处(projection_contract L89/action_exec L9),其余命中均为 `PrepActionExecutor` 合法名(`class PrepAction` 裸类全源码零定义,已亡属实)。
3. 3.1 验收 grep × 定稿文本互斥性:关键词集(空批/取首项/契约 §/契约 v/序列契约/list[CwAction]/结算惰性 drain/§4.1)对 §2.1 基类定稿句、§2.2 码块(含 None 分支注释——「None = 本帧无动作可发…」已不含「空批」)与头注块定稿(「序列消费」不撞「序列契约/序列发射」)、lifecycle docstring 定稿、§2.3 五处收敛新文本与定稿句(「流程侧契约」「发射序列」「单动作循环发射」均不撞相邻词关键词)、flow.py 两处定稿句逐词过 = 零碰撞;豁免申报(`decide_from_turn -> list[CwAction]` 签名,bridge L262)准确——四文件中该关键词的唯一未改行;`§4.1` 在四文件仅 bridge L3/L81 两处(均已点名收敛)。**除 F1 所指一行外,互斥性成立**。
4. 扫尾机制(design §2.2 关键词族三分处置)可操作:四文件内未点名残余(如 flow.py L423/L430「结算惰性 drain 已删除」正面表述、散见 design.md/DESIGN.md 指针)均可经三分处置兜住,「枚举清单可能不全,本扫尾是完备性的机械兜底」定位成立。

### E. 测试与工具影响面(design §2.4/§2.5/§2.6)

1. sr-od-test 全仓 grep `decide_prep_screen` 仅 `test_cw_p2_blood_band.py` L213-216 abstract 桩子类(`*a, **kw`,形状免疫);「空批/策略输出非/list[CwAction]/取首项」测试仓零命中——「在册锁零更新义务」成立。
2. L1 命令路径 `sr-od-test/test/sr_od/application/currency_war/` 实存(Test-Path = True)。
3. `tools/cw/replay_to_md.py`:imports 纯 stdlib(argparse/json/sys/pathlib/typing),按 decisions 记录流渲染备战/商店/补给三类 op 段(L536 起),零策略 import 零契约接口调用——§2.4 零影响成立;`telemetry/journal_query.py` 实存。
4. sim 不可见声明:flow/README §2.3「sim 消费面注记」(L91「sim 引擎唯一决策入口 = 商店决策面(prep 面 sim 不可达)」)与 op-layer §4 次门(L153「cw_replay --diff 只重放商店决策面」)引文转述准确。
5. cw4_counters 计数键族抽查实码在键:emitter_post_truncation_dropped/emitter_conditional_truncated/emitter_unknown_action_truncated(entry.py)、wanted_leg_*(mandate L1015-1045)、t1_interest_prep_emit(mandate L1368)、m1p_*(mandate L1801-1881)、sphere_defer_*(entry L485-516)、deploy_emit_*(mandate L2056-2072 DEPLOY_EMIT_HELD_PREFIX 族);`prep_box/prep_tome/prep_spheres` 系 `Emitted(action, True, '<reason>')` 第三位路由标签(entry L462/L464/L498/L513),非计数键——「勿 grep」提示属实。
6. 工程门前提:ruff select 含 "F"(pyproject [tool.ruff.lint]),F841 死变量告警生效——删除预声明的判据成立。

### F. 行为零变化与治本三问

1. 等价论证:bridge 边界取首项与消费端原取首项同源(同一 decide_from_turn 输出)同位(同 for 循环逐帧调用,次数/时序不变);异常路径仍由消费端 try/except 承接;bridge 返回值恒为 CwAction 实例或 None,恒过新校验谓词——逐位等价成立。
2. B4 第三方面:注册面封闭集 = {mandate_v1}(flow/README §2.1 管理器行实证),「响亮暴露不做静默垫片」与 op-layer §1.3 守卫断言依据一致;`create_state` 缺省 None(B4)同源类比成立(cw_strategy.py L111-115)。
3. 治本核:§1 归层 = 表示层成立(消费语义 2026-09-06 已迁移 vs 返回形状 list 未跟,双向实证);备选 A 修根(契约面形状 = 用户规范直接对象);备选 B 弃因有活机制依据(A.7 四调用点实证);备选 C 弃因成立(形状遗留 = 隐性 bug 温床的机理具体);备选 D 弃因与 op-layer §1.1 分域表述核验一致,「对称本身不是规范条款」无空洞。
4. 规范遵循:design/landing/README 结构对照 iteration-design.md——文档构成(单文档方案合法)、§0-§2 齐、landing 阶段七件齐(3.1/3.2/3.3)、固定末阶段 = 正本更新、依据就地标注、无过程叙事措辞、锁 docstring 不引 changes/、状态「对抗审中」与 README 进度一致——合规。

## 结论

发现总数 **2**:中危 1(F1 bridge docstring 收敛读法两可)、低危 1(F2 死指针引文配对错位)。无高危。设计稿码点主张、正本更新清单锚点、闭域检查域内完备性、验收 grep 互斥性(除 F1 一行)、as-built docstring 十句、文档指针三处改动全部直调属实;F1 建议在定稿前补点名收敛(一处文字修订),F2 为勘误级修正。
