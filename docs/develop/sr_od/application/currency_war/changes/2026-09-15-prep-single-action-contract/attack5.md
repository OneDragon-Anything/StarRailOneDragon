# 攻击报告 attack5(无前提对抗审查 · 第四批)

> 审查对象:①迭代设计三件(README.md / design.md / landing.md,按当前工作区状态);②`cw_strategy.py::decide_prep_screen` 工作区未提交 docstring(as-built 逐句核);③`strategy-docs/README.md` 工作区未提交修改(接口数表述 + 19/20 两行归位)。
> 方法:设计稿每个码点主张直调代码/正本文档复核;验收判据可执行性专项(关键词与定稿文本互斥性、判据域读法、豁免完备性、闭域检查独立重跑);三核并重。数值/引文/行号一律本报告自查,不转述既有攻击工件(attack.md–attack4.md 未读)。

## 1. 发现清单

### F1(中)design §2.3 / landing 3.1:bridge.py 死引用「逐一收敛」清单漏 2 处,且均逃过两道机械检查

- 位置:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/bridge.py` L14 与 L77;design.md §2.3 死引用清单(①–④)/ landing.md 3.1 范围②。
- 攻击过程(直调):
  - bridge.py **L14**(模块 docstring 第二段):「生产路径保持『cw_screen_prep 只写黑板+调一个 decide』,**契约 §5 职责分界**,不加生产接线步,R191 裁决」——「契约 §5」与 §2.3 已点名的「契约 §4 / §3.2 / §3.3」同族,同指已灭失的契约工作副本(灭失自证 = `entry.py` L17-18「契约正本 CONTRACT_SERIES_DECISION.md 工作副本灭失(全仓零命中)」+ `projection_contract.md` §6 G8)。§2.3 四处点名不含它。
  - bridge.py **L77**(类 docstring 首句):「新核(mandate_v1):三遍化决策序(证明→骨架→EV)**+ 序列发射**」——与同批被改写的 DESCRIPTION(L90-92「序列契约 v2 帧稳定截断发射」)同族口径;契约面收口后类级「序列发射」表述过期,未点名。
  - **为何两道机械检查都拦不住**:L14/L77 不在实现者的编辑点内(改 decide_prep_screen 方法体/docstring、DESCRIPTION、模块首段)→ 留存为「未改行」,3.1 验收 grep(`契约 §` 等)只打 **diff 新增行/本批改写行** → 不命中;3.3 闭域检查作用域 = `docs/` 全树,**不含 src/** → 不命中。design/landing 双双声称「死引用逐一收敛」「已点名全部死口径收敛处」,完备性声明失真。
  - 全集复核:四文件面内「契约 §N / 契约 vN / 序列契约」逐处清点(cw_strategy L123 随整体改写消亡;cw_screen_prep L2039/2044/2244/2249 已点名;bridge L92/109/115 已点名;entry.py/mandate.py 不在文件面)——L14 是唯一漏网的灭失契约引用。
- 附(低,同条目顺手修):§2.3 ④「模块 docstring 首段裸『§4.1』→ **删括注**(『config 切 strategy_id 即换核』已足表意)」措辞两读——删「§4.1」死指针保留其余(与「已足表意」自洽的唯一读法),还是删整个括注?建议写死为「删『§4.1』指针,其余保留」。
- 修正方向:§2.3 死引用清单补 L14(「契约 §5 职责分界」改语义表述,如「职责分界 = flow/README.md §2.1」)与 L77(「序列发射」→ 与 DESCRIPTION 新措辞同款「单动作循环发射(核内序列为发射组织)」);或 3.1 验收凭据对 bridge.py 模块头/类 docstring **全文**(非 diff 域)补一次同款关键词复核。

### F2(中)design §2.2:`lifecycle_decision_cycle` docstring 终结出口枚举漏挂两个死出口,其中之一 design 自己判过死

- 位置:`cw_screen_prep.py` L2211-2212(`lifecycle_decision_cycle` docstring):「终结出口语义 = 空批/**控制流**/参数非法/出战(发出即终结)/开店切换/**逻辑态未建模**/访问上限」;design.md §2.2 死口径清单第 3 条只点名「空批」→「无动作(None)」。
- 攻击过程(直调):
  - 「控制流」出口:控制流类动作已整体退役出词表(DeferSpheres 族删除;`flow/README.md` §2.2 历史注 L81;`op-layer.md` §2.5 同口径)——现循环体逐段核(L2229-2321)实际出口 = 空批/停机刹车/执行异常 fail/参数非法交回留证/终结(出战·开店)/访问上限,无控制流出口。
  - 「逻辑态未建模」出口:「未建模 → 返回 None 保守回退」分支已删,词表外 = AssertionError 响亮暴露(`cw_screen_prep.py` L1180「R9 保守回退分支已删,禁静默」、L2313;`prep.md` §4 L45)。**design §2.2 第 4 条自己把主循环头注的同款死主张(L2010-2011「逻辑态未建模的动作同判保守回退」)点名收敛**——同一死主张在 lifecycle docstring 的孪生出现却漏挂,内部可证。
  - 后果:实现者按点名只改「空批」,收口后该 docstring 仍向读者申报两个不存在的出口;3.1 grep 关键词(空批等)对残留的「控制流/逻辑态未建模」零命中,3.3 不涉 src,同样漏网。
- 修正方向:design §2.2 死口径第 3 条扩为整句定稿:「终结出口语义 = 无动作(None)/参数非法交回留证/出战(发出即终结)/开店切换/访问上限」,删「控制流」「逻辑态未建模」两项。

### F3(中)landing 清单 #6:op-layer §1.1 L21 前半句「策略器全函数」无分域保留,与本批新契约及 design 自身论证冲突;同族句在 02 号篇已分域处理、此处未处理

- 位置:`screens/op-layer.md` L21 前半句「**策略器全函数**:『无动作可做』的表达 = 直接选终结动作(如关店)」;landing.md 清单 #6 只改该行后半句(None/空批分域从句)。
- 攻击过程:
  - 本批落码后备战契约 = 恰一动作 / None(None = 本帧无动作合法交回)。design §2.1 依据 3 明确论证:「StartBattle 是受判据辖制的决策动作……不等于『无动作必须表达为出战』」——即 design 自己的词汇里,备战域「无动作」的表达 = **None,不是终结动作**。而改写后的 L21 前半句仍无分域地主张「『无动作可做』的表达 = 直接选终结动作」,与同句后半(备战域 None 合法)及 design 依据 3 直接顶牛;新策略实现者按前半句会把「本帧无动作」实现成 StartBattle,正是本迭代要消灭的误读。
  - **处理不一致实证**:同一「策略器 = 全函数」原则句在 `strategy-docs/02_mandate_layer.md` §7(L82)由清单 #15 显式改为分域表述(「商店域策略器 = 全函数……;备战域策略器返回恰一个动作……」);op-layer L21 的姊妹句漏施同款处理。
  - **机械检查盲区**:该半句不含 3.3 任何关键词(首项/空批/list[PrepAction]),也不含 3.1 关键词;改写后长期存活,闭域检查与「正本与实现一致」的 grep 凭据均拦不住。
- 修正方向:清单 #6 扩为整行改写,前半句同步分域(如「策略器 = 商店域全函数(『无动作可做』= CloseShop);备战域返回恰一个动作,『本帧无动作』= None 合法交回」),或至少给前半句加「(商店域)」辖域限定。

### F4(低)flow.py `decide_shop_action` docstring 内残留「逐帧取首项」措辞,与本批消亡概念撞词

- 位置:`strategies/impl/flow.py` L695-696(同 docstring,仅 L699「结算惰性 drain」被 3.1 ④ 点名):「决策本体 = `mandate_v1/shop.decide_shop_action`(选择序 = 既有波批优先级**逐帧取首项**)」。
- 攻击过程:该行是未改行 → 逃过 3.1 diff 域 grep;语义上它描述商店核内部「按波批优先序每帧取最优动作」,不算错,但本批正在把「取首项」从契约词汇中消灭,同文件、同一 docstring 内的存活撞词会让后续任何按本批关键词集做的 src 侧口径巡检(含 3.1 验收同款 grep 的复用)产生假命中与困惑。
- 修正方向:3.1 ④ 顺带把该半句改为「逐帧取波批优先序最优动作」一类非撞词表述(零行为,docstring-only)。

### F5(低)本批文件面内既有 changes/ 长期引用未登记未收敛(既有债,非本批新造)

- 位置:`cw_screen_prep.py` L2103 与 L2325-2326:两处代码注释引「design.md unified-action-factory §2.4」——指向 `changes/2026-09-14-unified-action-factory/design.md`,属 AGENTS.md「文档规范」铁律「代码与正本文档禁引 changes/ 内容(长期引用)」的违例;该迭代目录按铁律会被不定期删减,届时指针死亡。
- 攻击过程:本批正是该文件的注释/死口径收敛批(设计主题 = 死引用清零),但死口径清单按「取首项/契约 §/空批」族枚举,未覆盖「changes/ 引用」这一引用寿命族;3.1 关键词集不含 `design.md`/`unified-action-factory`,验收 grep 拦不住。非本批新造、不影响行为,故记低;但「收敛批路过债而不登记」与治本口径不符。
- 修正方向:三选一并落进 design/landing:①顺带收敛(把 §2.4 的终结判定语义改写进注释或改指正本 `flow/action_exec.md` §3 / `screens/prep.md` §4);②在正本更新清单或豁免表显式登记「已知未收敛债」;③明示超出本批辖域、另行立项(需一句话声明,防后人误判遗漏)。

## 2. 零发现面申报

### 2.1 审查对象 2:`decide_prep_screen` docstring as-built 十句逐句核 —— 零发现

直调证据逐句:①签名 `-> list[CwAction]` + 波批遗留定性 + 现行消费取首项(`cw_strategy.py` L121-122;消费端 `cw_screen_prep.py` L2043/L2248 `actions[0]` 两处同构;单动作循环 2026-09-06 落码 = `flow/README.md` 卷首)✓;②输入 `session.prep_obs_frame`(`cw_strategy_session.py` L202-206)+ 跨步状态 defer 计数(`entry.py` L494 sphere_defer_streak 系 `cw4_counters` 挂 strategy_state→session)与意向状态机(`flow.py` `_ensure_intention`)✓;③列表 = 决策核三遍编排发射组织、尾部不消费(`emit` L432 → `truncate_frame_stable` L241 → `[0]`)✓;④空序列合法 + stall 兜底归外循环(消费端 L2038-2041/L2243-2246 与拟 None 分支逐义等价)✓;⑤画面转移走 OpenShop/StartBattle 终结(`prep.md` §5)✓;⑥已退役语义 + `flow/action_exec.md` §2(机械执行无成败回执 L15)/§3(无 fail-stop L31)指针真实且内容吻合 ✓;⑦帧稳定分类在决策核内仍活(`entry.py` L220/L241,包内 4 真实调用:bridge L290、entry L297/L1157、mandate L1965)✓;⑧生命周期四件(action_key = `cw_vocab.py` L846/执行失败记忆 = `deploy_fail_counts` 族/stall 门/强制出战)与 `flow/README.md` L82 正本同清单 ✓;⑨观察帧缺失即抛错(`bridge.py` L120-125 ValueError)✓;⑩注释规范:中文、引用全为持久索引、无变更史叙事、无会话局部标识符 ✓。git diff 核对:HEAD 版为「序列契约 v1(2026-09-03 冻结)」波批口径,工作区已重写为 as-built 口径,与 design §1「现行文本已是 as-built 口径;3.1 ① 改写 = 新契约语义落位」声明一致。

### 2.2 审查对象 3:strategy-docs/README.md 工作区修改 —— 零发现

①19/20 两行归位:两文件存在(glob 实证),一句话概括与各篇标题/结构吻合(19 = 补强通道重估 §2 + 生存折现消费位 §3;20 = 必花域 §2 + 旱期金出口分层 §3),插入位(18 与 22 之间)数值有序,文尾两个孤立表格行已删净(§5 以三条纪律收尾,无残表)✓;②「策略↔流程契约」行:「契约成员 13」= flow/README §2 卷首「抽象 12 + 工厂 1 = 保留总成员 13」且与 `cw_strategy.py` 实际 abstract/工厂逐一数过(12+1)一致;「单动作循环」= flow/README §1;「序列语义为历史注」= §2.2 历史注节;「flow/ 七篇」= glob 实证恰 7 个 .md ✓。

## 3. 验收判据可执行性专项结论

- **3.1 关键词集 × 定稿文本互斥性**:八个关键词逐一比对 §2.1 基类 docstring 定稿、§2.2 码块(注释/detail/F3 文案)、§2.3 bridge docstring 定稿——零碰撞 ✓;`list[CwAction]` 豁免申报必要且准确(`decide_from_turn` 签名住 bridge.py L259-262,本批文件面内、非改动行)✓;「新增行/本批改写行」判据域读法唯一,被删行天然携带关键词的问题已被判据域排除 ✓。唯 F1/F2/F4 表明 diff 域 grep 对**未改行的同族残留**结构性失明,不能单独承担「死口径清零」验收(故 F1 给出全文复核补强建议)。
- **3.3 闭域检查独立重跑**(本报告按 `首项|空批|list[PrepAction]` 全树重跑):「首项」全部命中 → 清单 #1/2/3/4/5/7/8/11/13/14/15 全覆盖 + 豁免(`proofs/validations/P51_V3_REBUILD.md` L391「R31-2 首项=1」属实系拟合器标签序位;`changes/2026-09-14-unified-action-factory/design.md` L362 归 changes/ 豁免);「空批」→ flow/README L77/L81(历史注节,豁免正当)+ #6/#8/#9/#10 全覆盖;「list[PrepAction]」→ #2/#7 全覆盖;PrepAction 裸名独立重扫(`PrepAction[^E]` 口径)→ 活正本仅 projection_contract L89(#3)/action_exec L9(#12)两处,已知位清单完备,其余命中全为 `PrepActionExecutor` 合法名 ✓。闭域检查对三关键词**完备且可执行**;其盲区(「全函数」类无关键词死口径)已由 F3 实证并给修正。
- **判据正本引文核对**:landing 清单 16 条锚点句逐条直调(README L17-18 跨行拆分/L23/L64、projection_contract L89-90、action_exec L28/L9、op-layer L14/L21、prep.md L15/L32/L53、screens/README L130、22_prep_screen L8/L28、action-logic-state L163、prep-executor-actions L13、02_mandate_layer L82)——引文逐字存在、行号无漂移 ✓。
- **阶段可独立验收性**:3.1(四文件改写,验收 = 测试名 + grep)/3.2(锁 + 烟雾锚点,判据不依赖 3.3 未完成部分,指针先行+复验已写明)/3.3(清单清零 + 闭域三分处置)七件齐、依赖链单线、可独立派工验收 ✓。

## 4. 三核结论

- **核一(无前提)**:消费端全集直调——`decide_prep_screen` 全 src 仅 `cw_screen_prep.py` 两处调用(design 消费端枚举完备);sim/replay/tools 零消费 prep 面(§2.4 零影响成立,replay_to_md 纯 stdlib 离线渲染实证);测试影响面盘点实证(全仓仅 `test_cw_p2_blood_band.py` L215-217 `*a, **kw` 桩,空批/形状文案锁零命中)。发现 = F1/F2/F3 的清单完备性缺口(设计边界完整性)。
- **核二(规范遵循)**:四节齐/阶段七件齐/README 进度态一致/引用寿命分层合法(锁 docstring 指针指正本不引 changes/)/无过程叙事(R196/R197 系在册缺陷类持久编号,非会话局部)。发现 = F5(changes/ 引用寿命铁律,既有债)。
- **核三(治本)**:§1 归层表示层成立(消费语义 2026-09-06 已迁移、签名 list 未跟,双向实证);§2 修根 = 契约面形状收口,核内 list 保留有活机制依据(首项选择序 4 调用点直调实证,`_merge_ev_before_frame_end` L1140/L903、M7 回排 L1951-1970);备选 A–D 弃因逐一核无空洞(D 的弃因与 op-layer §1.1 分域句直调吻合);None 通道三点依据全验证(⑥ 空则补 StartBattle = `entry.py` L943-944 实码;可达空边 = truncate 首位 SellBench/DeployMove 复检截空 L309-324 实码;unknown 首位边不可达 = 决策核可发射 17 类全被四分类覆盖、分类表 11+1+1+4=17 直调数过;OpenBookcard 画面 op 侧发射 = `cw_screen_prep.py` L2587 直构实证;entry.py 头注「18 类」= 备战域词表 18 类 vs 分类表 17,既有漂移申报属实);B4 第三方兼容面(封闭集 {mandate_v1}、旧 list 空否均 fail、响亮暴露不做垫片)边界申报自洽。无治本级异议。

## 5. 攻击面清单(实际攻击过的面)

1. 迭代设计三件:结构合规(iteration-design.md 四节/七件/阶段依赖/README 进度)、§0-§3 全部码点主张、验收判据可执行性专项(§3 节)、正本更新清单 16 条引文逐字、闭域检查三关键词 + 裸名人工位独立重跑、豁免表必要性与充分性。
2. 消费端实态:`cw_screen_prep.py` L2007-2011(头注)/L2016/L2220(预声明)/L2029/L2234(调用点)/L2033-2043/L2238-2248(F3·空批·取首项)/L2044·L2249(契约 §2 注释)/L2103/L2325(changes/ 引用)/L2211-2212(lifecycle docstring)/两循环尾段(终结判定·逻辑态直写·访问上限)逐段对。
3. 策略边界:`bridge.py` L1-31(模块头)/L76-130(类 docstring·DESCRIPTION·decide_prep_screen·装配缝)/L247-291(decide_from_turn·截断语境);`flow.py` L422-448(帧代次消费 + drain 已删自证)/L688-740(decide_shop_action);`entry.py` L1-42(头注·18 类·契约灭失自证)/L156-238(分类四元组·17 类覆盖)/L241-331(truncate 逐边)/L432-441/L903/L936-944(emit·⑥ 补 StartBattle)/L1140-1157(合并);`mandate.py` L1299/L1753(注释提及)/L1951-1970(M7 回排)/L1801-1881(m1p_* 键);`cw_vocab.py` L834-843(词表 22 类逐一数)/L846(action_key);`cw_strategy_session.py` L202-206(prep_obs_frame)。
4. 判据源正本:flow/README(§1 架构图/L23/L40/L47/L64/§2.2 历史注 L77-82/§2.3 L91)、action_exec(§1 L9/§2 L15/§3 L28·L31)、projection_contract(§4.1 L89-90/§6 G8)、op-layer(§1.1 L14/L21/§1.4/§4 L153)、prep.md(L13/L15/L32/L44/L45/L53)、screens/README(§6 L130)、22_prep_screen(L8/L28)、02_mandate_layer(§7 L82)、game_state 两处(L163/L13)。
5. 工具与测试:`sr-od-test` 全仓(decide_prep_screen/空批/list[CwAction]/actions[0]/策略输出非)、`tools/cw/replay_to_md.py`(import 面·op 段渲染)、`telemetry/journal_query.py`(旧文案零依赖)、遥测键族(emitter_*/t1_interest_prep_emit/wanted_leg_*/m1p_*/sphere_defer_*/prep_box 系 reason 标签)逐一实证。
6. 审查对象 2/3:见 §2 零发现申报。

> 范围外申报确认(不计发现):strategy-docs/README §2 分篇表确缺 14/15/16/17/21 五篇(glob 对照实证,既有缺口);entry.py 头注「18 类」计数漂移(design §2.1 已申报不动,本报告 §4 核三实证其漂移机制)。
