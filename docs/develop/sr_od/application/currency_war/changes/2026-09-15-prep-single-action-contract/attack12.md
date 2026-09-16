# attack12 — 无前提对抗审查(第 12 轮)

> 审查对象:①本迭代 README.md / design.md / landing.md(未读 attack.md–attack11.md);②`strategies/impl/cw_strategy.py::decide_prep_screen` docstring(工作区态,逐句对照代码核 as-built);③`strategy-docs/README.md`(数字/指向/表格结构)。
> **对象状态勘误**:审查简报称对象③为「工作区未提交修改」,实测该文件工作区已干净——所述改动(「策略↔流程契约」行接口数表述 + 文尾 19/20 孤立行归位,另含 14/15/16/17/21 五行补索引与「阅读时点」行新增)已随 commit `df25f6d94` 入库。本报告按文件现态审查。对象②(`cw_strategy.py`)仍为工作区未提交态,按 `git diff HEAD` 界定改动面。

## 发现清单

### 中

**F1【中】strategy-docs/README.md:15(§2 标题)与 :53(阅读时点行)、:30-43(分篇表)——阅读顺序口径同节自相矛盾**
- 现状:§2 标题仍写「阅读顺序(总 00/01/02/04 → 分 10-13 + 08)」,而 `df25f6d94` 给分篇表补入 14/15/16/17/21 五行、并新增阅读时点行「分篇 **10-17 + 08** 是决策面主干」——同一节内两个口径直接冲突;且 07(meta_run)在「10-17 + 08」与「18-27」两个桶里都不在,阅读时点行对它零归属。
- 影响:本目录自称「唯一现行入口」,读者按标题走会漏 14-17 四篇决策面主干;标题是本批改动生效后变陈旧的(改前表格缺 14-17 时标题与表尚可互证,补行后未同步)。
- 修正方向:标题改「分 10-17 + 08」;阅读时点行补 07 归属一句(如「07 为跨局出辖登记篇,随批查阅」),或显式声明其不入两桶的理由。

### 低

**F2【低】design.md §2.2(L77)——`action-logic-state` 路径笔误枚举重计一处**
- 「L984 同行正本路径笔误顺带修正…同族笔误同批修正(L985/L1000/L1187 三处同款)」:实测 L984 行内并无该路径(它在 L984 起的 changes/ 引用注释的 **L985 续行**),且 L985 又被列入「三处同款」——同一处被计两次,枚举暗示 4 处而全文件实态 **3 处**(L985/L1000/L1187,grep 复核)。
- 机械后果零:扫尾关键词 `action-logic-state` 恰命中全部 3 处,收敛指令本身无歧义。
- 修正方向:改写为「笔误共 3 处(L985/L1000/L1187;L985 即 L984 引用注释的续行)」。

**F3【低】design.md §2.5(L122)、landing.md 3.1(L13)——L1 内联命令含不存在的标记 `legacy_baseline`**
- 实测 sr-od-test 全仓(含 `test/conftest.py` 的 marker 注册节)对 `legacy_baseline` **零命中**;conftest 只注册 `slow`。`-m "not slow and not legacy_baseline"` 的选择集与 `-m "not slow"` 恒等、命令可执行,不构成判据失效;但 design/landing 以「CW skill『测试分层』行路径系在册笔误,以本内联命令为准」自任勘误源,却原样继承了同一行的幻影标记——判据文本不真,且若测试侧将来启用 `--strict-markers` 该命令即红(conftest 注册 `slow` 的注释明言该前景)。
- 修正方向:内联命令删 `and not legacy_baseline`;skill 反馈条目在「路径笔误」外补记该标记同样系死词(两者大概率同源:旧 legacy 基线锁退役后残留)。

**F4【低】design.md §2.2 扫尾关键词族——「结算惰性 drain」兜不住同族变体「结算槽 drain」**
- `flow.py:430`(`_consume_prep_direction_frame` docstring 括注「原前置的**结算槽 drain** 已删除」)与 flow.py:422-3 节头注同性质、同真值,但用词变体不在扫尾族内 → 该命中面永不浮出、永不获三分处置。该处现状为如实的删除声明(预期处置 = 保留申报),**本批零实际后果**;唯扫尾自称「枚举清单可能不全,本扫尾是完备性的机械兜底」,兜底面存在此洞。
- 修正方向:族内 `结算惰性 drain` 扩为 `结算惰性 drain|结算槽 drain`(或直接 `drain`),把 L430 预录为保留申报。

## 零发现面(逐句/逐码点核实证词)

### 对象②:`cw_strategy.py::decide_prep_screen` docstring(L123-144)——as-built 属实,零发现
逐句直调核验:
1. 「现行消费 = 单动作循环逐帧取首项」:生产调用点全仓恰 2 处(`cw_screen_prep.py` L2029 主循环 / L2234 `lifecycle_decision_cycle`),两处均 `action = actions[0]`(L2043/L2248),尾部动作逐帧弃置;
2. 「``cw_screen_prep`` 决策循环两处同构」:try/except 异常包装(L2030-32/L2235-37)、F3 形状校验(L2033-37/L2238-42)、空批分支(L2038-41/L2243-46)逐行同构;
3. 「``session.prep_obs_frame``」载体在册(`kernel/cw_strategy_session.py` L206,写者白名单 = 入口观察段 L977 / 循环逻辑态直写步 L2115/L2315,与 prep.md §3 一致);
4. 「相对序决定首项选择,尾部动作生产不消费」:列表序 = `entry.emit` 编排序 + `truncate_frame_stable` 保序截断(bridge.py L282-291),消费端只取 [0];
5. 「空序列合法…stall 兜底归外循环防线」:空批 → `round_success` 交回(L2041/L2246),外循环无进展守卫兜底(flow/README §4);
6. 「禁用空批表达控制流——画面转移一律走终结动作」:控制流类动作已退役出词表,终结集 = OpenShop/StartBattle/OpenBox(`_terminal_exit` L2334-2351 分支实码);
7. 「已退役语义…落地判定归观察侧对账(单一源 = flow/action_exec.md §2/§3)」:action_exec §2 执行契约(无成败回执)+ §3「无 fail-stop/恢复原语」明文,与 B1 拆除注释(L2012-2014)一致;
8. 「帧稳定分类在决策核内仍活(mandate_v1 entry)」:entry.py `classify_frame_stability`/`truncate_frame_stable` 活码,bridge 决策链真实调用;
9. 「生命周期机制(action_key/执行失败记忆/stall 门/强制出战)归框架流程侧」:与 flow/README §2.2 历史注 L82 同款四方枚举,载体实码在册(action_key = cw_vocab、deploy_fail_counts = ExecState、stall 门 = cw_loop、发射核 = launch admission);
10. 「观察帧缺失即抛错」:唯一具现 bridge.py L120-125 抛 ValueError ✓;flow 中间 ABC 不实现(保持 abstract)✓。
11. 附:模块头 L13-16 与类 docstring L76 的「abstract 12 + 工厂 1 = 13」实数清点一致(abstract 12 个、create_state 非 abstract);「契约形状 = 用户规范对象、本批收口」与 landing 3.1① 衔接无重复处理矛盾(design §1 第三条自洽)。

### 对象③:strategy-docs/README.md——除 F1 外零发现
- 「策略↔流程契约(四身份分离、**契约成员 13**、单动作循环;序列语义为历史注)在其 README §2」:四项全在 flow/README §2 实锚(§2.1 四身份分离表、L40/L84 成员数 13、L6/L16-18 单动作循环、L77 历史注)——改后的接口数表述**属实**(旧文「17 接口」确系过时口径);
- 「flow/(七篇)」:实数 7 个文件(action_exec/exit_chain/guards/outer_loop/projection_contract/README/session)✓;
- 19/20 两行归位:表内位次 18→19→20→21 连续、三列格式同构、文尾孤立行已删(diff 复核)✓;27 篇链接文件全部存在 ✓;
- 「09 架构篇整体迁 `../flow/README.md` §2」:flow/README §2 标题及卷首 L3 收编声明互证 ✓。

### 对象①:design/landing 各码点主张(全部直调成立)
- **消费端两循环**:§2.2 码块与实态逐段对照;「其余段零变化」枚举(异常包装/validate/期望态记账/执行/终结判定/逻辑态直写/段序号置位)与实码吻合;预声明 `actions: list = []` 恰在 L2016/L2220;ruff select 含 `F`(F841 主张成立);新形状谓词对旧 list 返回(空/非空)均 fail 的论证成立(list 非 CwAction 实例);
- **主循环头注释块**:L2004-2014 区域、拟删两句与定稿保留文本逐字对上;lifecycle docstring 终结出口(L2211)「空批/控制流/逻辑态未建模」三项删除依据逐一成立(保守回退分支确已删,L2113/L2312-13 注释自证);
- **死口径/死引用清单**:两处「契约 §4」(L2039/L2244)、两处「契约 §2」(L2044/L2249)、5 处 changes/ 引用(L664/L984/L2103-2106/L2325-2326/L2537)、路径笔误 3 处——与 design 枚举一致(F2 的计数表述瑕疵除外);
- **bridge.py**:首句双重死引用(契约工作副本灭失 + action_exec §1 实为词表节)两半都真;DESCRIPTION/裸 §4.1 两处(L3/L81)/「契约 §5」(L14)/decision_v2 先例(L9,该文件全仓不存在)/类首句(L77)逐处确认;「入口内务 = 结算惰性 drain」死引用属实(实码 L127 只调帧代次消费;flow.py `_consume_prep_direction_frame` docstring 自证);`decide_from_turn` 仍返回 list、bridge 边界取首项方案与消费端原取首项同位;包内「4 处真实调用 + 3 处注释提及」计数逐点验证(bridge L290;entry L297/L1157;mandate L1965 调用 + L1299/L1753/L1951-1957 注释);
- **flow.py**:面③死指针四处(L105/L112/L133/L139)逐处确认;L422-423 墓碑保留申报合理;`decide_shop_action` docstring 两处(L695-696/L699)实文一致;「商店决策本体 = 顺序候选扫描、无发射组织」与 shop.py L1230 选择序结构相证;shop.py L758 同措辞句(已申报范围外)存在性复核无误;
- **None 通道三点依据**:①op-layer §1.1 L21 分域表述逐字存在;②空返回边实锚——emit ⑥ 无动作补 StartBattle(L936-944)常态无空,可达空边 = truncate 首位 SellBench/DeployMove 复检失效截空(entry.py L309-323),unknown 首位边不可达成立(四分类覆盖恰 17 类,CW_ACTION_TYPES 备战域子集清点 = 18 类含 OpenBookcard,mandate_v1 包内 OpenBookcard 零发射,grep 复核);③op-layer §1.4「备战 = 开战」恒可用终结引文属实,26_battle_settlement.md 出战标准在册;
- **sim/回放零影响**:flow/README §2.3 sim 消费面注记、op-layer §4 次门( cw_replay --diff 只重放商店面)、replay_to_md.py 头注(备战/商店/补给三段渲染,零契约接口调用,grep 复核)三点全成立;strategy-work §4「sim 可观测性声明」(L51)与「实机/sim 分工」(L55)引用属实;
- **测试与文案面**:sr-od-test 全仓 `decide_prep_screen` 仅 test_cw_p2_blood_band.py L216 `*a, **kw` 抛错桩(形状免疫),`MandateV1*` 消费面全在商店线,空批/取首项/list[CwAction]/策略输出非 文案零命中;tools/ 与哨兵 4 件(cw_batch_stats/cw_early_stop/cw_runs_gap/cw_sentinel)旧文案零命中;遥测键族直调全在册(emitter_*/deploy_emit_*/deploy_exec_*/t1_interest_prep_emit/wanted_leg_*/m1p_*/sphere_defer_*),`prep_box/prep_tome/prep_spheres` 确系 Emitted.reason 路由标签非计数键(entry.py L462/464/498/513)——「勿 grep」提示准确;telemetry/journal_query.py 存在;
- **landing 验收可执行性专项**:验收 grep 关键词(`空批`/`取首项`/`契约 §`/`契约 v`/`序列契约`/`list[CwAction]`/`结算惰性 drain`/`§4.1`)与 design §2.1/§2.2/§2.3 全部定稿文本逐词互斥(含「发射序列/帧稳定截断/非流程侧契约」等近形词均不触族);`decide_from_turn -> list[CwAction]` 豁免申报属实且该行确非本批改动行;
- **3.3 正本更新清单完备性**:闭域关键词全树实跑(排除 changes/ 与豁免表)——「首项」9 处、「空批」6 处、「list[PrepAction]」2 处命中**全部**被清单 #1-#15 覆盖,零遗漏;豁免表三件逐一验证为真(flow/README 序列语义历史注节 L77-82、changes/ 全目录、P51_V3_REBUILD.md L391「首项=1」确系拟合器标签序位);裸名人工复核「已知位」三处(projection_contract §4.1 L89 / action_exec §1 L9 / action-logic-state §3 L161)恰为全树仅有的死裸名位,其余 PrepAction 命中 37 处逐一核为合法名(PrepActionExecutor/apply_prep_action_logic/cw_prep_actions 模块引用),清单 #19「PREP_ACTION_TYPES 大小写敏感 grep 不命中、靠条目覆盖」的判据读法准确;清单 #14 对 prep-executor-actions.md L9 偏差注的联动处置预判正确(#19 改写后该注所引原文即失配);清单 #17「OpenBox terminal=True」经实码核验(cw_open_box_action.py L39),三处落点(L52/L91/L122-133)与现文一致。

## 范围外观察(不计发现,仅留证)
- `strategy-docs/22_prep_screen.md` L3/L34 引 `../flow/screens-actions-capability.md`(全仓不存在)、L4/L13 引 `../flow/prep_visit.md`(仅存于 .debug 旧 worktree 快照,现 flow/ 七篇中无)——两处死链系既有债;清单 #11 触及该文件但不辖死链,建议与 CW skill 反馈队列同批挂账。
- `game_state/action-logic-state.md` L250 有一处 `design.md unified-action-factory` 引用(正本文档引 changes/,铁律违例族)——属已申报的「面外死指针存量、归全仓注释卫生批」家族,不在本批。
- 哨兵/工具面另有 `.dsh/.../scripts/__pycache__/` 4 个 pyc 与源伴生,非审查面。
