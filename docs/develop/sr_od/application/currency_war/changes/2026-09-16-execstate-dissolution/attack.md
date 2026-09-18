# execstate-dissolution 设计对抗审报告

> 审查对象:本目录 [design.md](design.md)(§2.1 处置表 21 行 / §2.2 迁移契约 / §2.3 取舍)、[landing.md](landing.md)(3.1-3.6 + 正本清单)、[README.md](README.md)。
> 攻击判据:`docs/develop/harness/iteration-design.md` §7 三核并重;代码事实基准 = **设计提交时点快照**(commit 9192a5e1f 时代的工作区;审查窗口内另有并行批次在飞——3.1 阶段实现与 turnstate-retirement 迭代先后动工,行号以下列证据的快照时点为准,均以符号定位复核)。
> 审查方式:处置表 21 行逐字段全仓 grep 核对消费点申报(核一②)、landing 阶段文件面/判据可验收性(核一③)、design↔landing 同步(核一④)、依据就地标注与符号存在性(核二)、渠道签名对照 game_state/README §3 封闭集(核二③)、未点名字段归属与用户四条裁定的对照(核三①)、治本核验(核三②)。

## 结论先行

**需修订后复审**(1 致命 / 8 重要 / 8 次要;总数 17)。
处置表对 ExecState 全部 21 个具名字段的**覆盖本身完整无遗漏**(见发现 [13] 的正面核验),四条用户裁定的落位方向总体成立;但 #17 行建立在不实的消费点申报上(给双重死亡机制新设容器 Field),多处 landing 判据/文件面不可执行或引用不存在的符号与测试,按现稿立阶段任务会在验收环节翻车。

---

## 逐条发现

### [1] 致命 | design §2.1 #17(v2_round_key/v2_round_sold)+ landing 3.4 | 给双重死亡的机制新设两个 GameState Field(快照流水字段),族归依据与用户裁定自相矛盾

**问题描述**:#17 把 `v2_round_key`/`v2_round_sold` 迁 GameState 新 Field(`round_ledger_key`/`round_sold`,§2.2-1 明确「进 bs_schema 域映射与快照流水」),族归依据为「对账期望账族——**动作上报写的事实账**」。该申报不实:①`v2_round_key` 全仓**零写端**(唯一出现 = 定义处 + `register_round_sold` 的读);其注释声称的维护者「决策层轮键重置段」属已删除的 decision_v2。守卫 `getattr(...,'v2_round_key',None) != key` 的 key 恒为 tuple(非 None)→ `register_round_sold` **恒早退 = 永久 no-op** → `v2_round_sold` 恒空集。②买侧互斥消费面(字段注声称「engine_seed 对集内卡名禁买」)在 src 不存在;现役单一事实源 = mandate_v1 自有载体。③按 design 自己的族标签(对账期望账族),用户裁定③的处置 = **删**——设计却选择迁,族标签与处置互相打脸;§2.3 删期望账的理由(「保留即维持第二对账通道,与铁律冲突」)逐字适用于此:迁入容器 = 把与 mandate 载体并存的第二已卖账铸进容器永久 schema 面。④「轮键自校验语义逐字节不变」= 把一个恒假守卫原样搬进新容器。

**证据**:
- `kernel/cw_round_ledger.py:35`(守卫读,恒不等早退)、`:37-39`(仅此处的惰性初始化,不可达);
- `v2_round_key` 全仓 grep:仅 `cw_exec_state.py:155`(定义)+ 上述读;decision_v2 删除依据 = `flow/README.md` §2.1「注册面封闭集 = {mandate_v1}(decision_v2 已随 commit b94e9cfb 删除)」;
- mandate 侧现役载体:`strategies/impl/mandate_v1/mandate.py:500`(ROUND_SOLD_ATTR='cw4_round_sold_names')、`:503/521/534`(record_round_sold/round_sold_names/sold_this_round)、写入点 :1040/:1267/:1363/:1474、`entry.py:551`;消费 = `shop.py:1198`「单一事实源 = mandate.round_sold_names」;
- design #17 还错标调用方:「live 调用方 cw_shop_action_ops(卖出上报路径)」——实际唯一调用方 = `operations/cw_op/cw_sell_bench_action.py:67-72`(SellBench 落地登记)。

**修复建议**:该行重新处置,二选一并给依据:(a) **删**——`v2_round_key`/`v2_round_sold` 字段 + `register_round_sold` + `cw_sell_bench_action.py:70` 调用桩(与 #1/#10 死面同批,符合裁定③与 §2.3 自己的论证);(b) 显式裁定**复活**(补轮键写端与买侧消费面),单独立项说明为何不用 mandate 载体。另修正调用方归属为 cw_sell_bench_action。

### [2] 重要 | landing 3.4 完成判据/验收凭据 | 引用不存在的测试

**问题描述**:判据「既有测试名(`register_round_sold` 轮键自校验测试不变绿;`record_fresh_buy` sim/live 同口测试不变绿)」+ 验收凭据「既有测试名(不变绿)」——测试仓中**不存在**任何引用 `register_round_sold`/`record_fresh_buy`/`fresh_buys_of`/round_ledger 的测试。凭据不可执行;若意图是「本阶段补测试」,landing 未列该任务与判据。

**证据**:`sr-od-test/` 全仓 grep `register_round_sold|record_fresh_buy|fresh_buys_of|round_ledger` = 零命中。

**修复建议**:判据改为「新增轮键自校验行为测试 + record_fresh_buy 宿主切换同口测试」并列入文件面;或删去测试凭据、说明为何该机制无测试锁(与发现 [1] 的处置联动)。

### [3] 重要 | landing 3.5 文件面 | 缺 #16 的两个消费文件

**问题描述**:design #16 明确申报 `bench_layout_epoch` 消费点 = `cw_screen_buy_cards.py:1002` / `cw_shop_action_ops.py:247`(经 grep 核实**属实**,且这是 #16 仅有的两个消费点),3.5 阶段必须改这两处;但 3.5 文件面 = `kernel/cw_exec_state.py`、`kernel/cw_game_state.py`、`kernel/cw_reconcile.py`、`operations/cw_loop.py`、`cw_screen_prep.py`、`obs/cw_observation.py`、`sr-od-test/`——**两个消费文件均不在列**。按文件面验收会漏改或拒改。

**证据**:`operations/cw_screen/cw_screen_buy_cards.py:1002`、`operations/cw_op/cw_shop_action_ops.py:247`(grep 属实);landing 3.5 文件面清单(landing.md:60)。

**修复建议**:3.5 文件面补列两文件;或把 #16 拆到有完整文件面的独立阶段。

### [4] 重要 | landing 3.1 文件面 | 小于 #2 的实际爆炸半径(已被在飞实现实测证实)

**问题描述**:#2 删装备拖拽失败记忆要求「删三处死读路径(穿戴计划拉黑逻辑随之消失)」——拉黑逻辑删除牵动 `cw_equip_wear_plan` 内计划构建函数的 `exec_state` 参数形状及其调用方:`strategies/impl/mandate_v1/mandate.py:1926-1928`(经 `exec_state_of(session)` 取载体传参)与 `operations/cw_op/cw_op_equip_all.py`。两文件均不在 3.1 文件面(kernel/cw_exec_state.py、kernel/cw_equip_wear_plan.py、sr-od-test/)。实测佐证:本审窗口内并行落地批为完成 3.1 实际同时改动了 mandate.py 与 cw_op_equip_all.py(git status 在飞改动集,后已提交推进)。

**证据**:`cw_equip_wear_plan.py:53`(docstring 锚)/`:402-403`/`:470`(三处死读,审计快照时点在);`mandate.py:1926-1928`(`_build_equip_wear_plan(session, _exec_state_of(session), …)`);并行批 git status 改动集(审计窗口观察)。

**修复建议**:3.1 文件面补列两文件;或范围改述为「`_build_equip_wear_plan` 签名不动、exec_state 参数留置」并论证留置理由。

### [5] 重要 | landing 3.3 完成判据 | 「node_screen_refresh 四字段写端在产」不可达成

**问题描述**:3.3 范围只覆盖 #4/#5/#6 = supply/encounter/strategy 三字段;`env_refresh_used`(§3.4.3)不在本迭代范围(无对应 ExecState 字段,#4-#6 不涉它),且无任何写端(仅声明位与注释锚)。判据要求「`node_screen_refresh` 四字段写端在产(grep 写点)」——按此验收 3.3 **必然失败**。

**证据**:`cw_game_state.py:2657`(`env_refresh_used` 定义,注释仅称「观察通道在册」)、`cw_screen_invest_env.py:327`(注释,无写点);design §2.1 #4-#6 不含 env;landing.md:39。

**修复建议**:判据改「三字段写端在产;env_refresh_used 维持零写端申报不动」。

### [6] 重要 | design §2.1 #5/#6 契约 | 「写点改容器」措辞诱发双计毒化,与代码内明示红线冲突

**问题描述**:遭遇/策略两容器字段的在产写端 = on_outcome 发射钩子(`_on_refresh_emitted`,各 write_logic +1),与 ExecState 置位发生在**同一发射点**(encounter:175 置位 + :176 触发钩子;invest_strategy:330 add + :331 触发钩子)。design #5 的「写点 cw_screen_encounter.py:175」与 #6 的「刷新发射即对应卡 +1」未说明这两行应**删除**(容器 +1 已存在于钩子);若实现者照字面把 :175/:330 改写为容器 +1 = 每次刷新计 2 次——代码注释明示「恰触发一次——**双计即计数毒化**」(cw_screen_encounter.py:133)。另 #6 把写点 `:330`(`.add`)误标为「读点 :330/:468」。

**证据**:`cw_screen_encounter.py:130-137`(注册表申报)、`:144-167`(钩子写容器 +1)、`:169-176`(发射点双写)、`:133`(双计毒化红线);`cw_screen_invest_strategy.py:323-333`(发射点)、`:335-367`(钩子写容器);design.md:28-29。

**修复建议**:#5/#6 契约明确「删 ExecState 置位/清零行(容器写端已在产,禁新增第二写点),读点改容器计数对照注册表余量」,并修正 #6 的读写点标注。

### [7] 重要 | design §2.1 #15(star_regression_count) | 消费点申报失真(停机钩子已退役),删除选项未评估

**问题描述**:#15 族归依据为「产生者 = reconcile 观察边界,消费 = **停机钩子判定**」。代码现状:停机判定已退役,现为「降级为高频留证——每 5 次回退存一张证,**不 stop**」,且代码自注「SIFT 身份修复后**本段连同 _star_stop_hook 删**」——这是一个带删除预告的半退役计数器。设计按「停机钩子簿记」迁 GameState.tracked_books,未按治本判据评估「随段删除」。附注:同一机制的双胞胎防抖态 `session.star_pending_regression`(session 动态属性,不在 ExecState)不在处置表也不在 §1「明确不解决」清单——迁移后同一 star 回退机制分裂 GameState/session 两宿主,设计未表态。

**证据**:`cw_reconcile.py:209`(读)/`:298`(写,唯一写读者申报属实);`:276-283`(留证降级与删除预告自注);`:219`/`:297`(session 动态属性双胞胎)。

**修复建议**:改判**删**(与预告段同批退役)或补「为何保留并迁容器」的依据(如留证采样仍需局级存续);§1「明确不解决」补 `star_pending_regression` 的归属表态(或一并处置)。

### [8] 重要 | design #3/§2.2-4 + landing 3.3/正本清单 | 引用不存在的类名 MandateState

**问题描述**:三处均写「迁 `MandateState` 具名字段」——实际类名 = `StrategyState`,历史名 MandateState 的兼容别名已随迁移尾批清理,类 docstring 明示「消费面一律 import StrategyState」。实现者照文找符号落空;这正是 iteration-design §5.4 要求定稿前逐一核符号存在性的失守点(注:正本 flow/README §2.5 同用旧名,设计若据此转写也应就地核代码)。

**证据**:`strategies/impl/mandate_v1/mandate_state.py:71`(class StrategyState)及其模块头改名归位注;design.md:26/51、landing.md:33/99。

**修复建议**:design/landing 全部改 `StrategyState`;顺手在正本更新清单给 flow/README §2.5 的 MandateState 旧名补一条(现清单只列 §2.5 三态→两态改写,可合并)。

### [9] 重要 | landing 3.2 归段 | telemetry `refreshed` 时点值读点属 #4(3.3)却被划入 3.2,产生跨阶段依赖错误

**问题描述**:supply 确认行 `refreshed` 值的真值源 = `cw_screen_supply_node.py:246`(读 ExecState 旗标)经 `:290`(`'refreshed': _refresh_used`)流入 telemetry,schema.py:642 是注释锚。该读点迁移与 #4 同命运(3.3 才接容器写端),但 landing 3.2(期望账拆除,依赖仅 3.1)把它划入自身范围:3.2 时点改读容器 = 遥测值在 3.2→3.3 窗口恒空(容器尚无 live 写端,仅 sim observe 写);不改则 3.2 判据空转。无论哪种执行法都产生窗口期失真或空判据。

**证据**:`cw_screen_supply_node.py:246/:290`;`telemetry/schema.py:642`(注释锚);landing.md:20/:22(telemetry/schema.py 在 3.2 文件面)/:23(依赖仅 3.1)。

**修复建议**:`refreshed` 读点迁移随 #4 归 3.3(或 3.2 显式申报「仅删 xp_expect_ledger schema 字段,refreshed 归 3.3 处置」并从 3.2 判据移除)。

### [10] 次要 | design §1 | 字段计数自相矛盾(27 / 19 / 实际 21)

**问题描述**:§1 称「ExecState(27 具名字段)」与「19 个具名字段逐一按 §2 处置表落位」——实际 dataclass = **21 个具名字段**,处置表 #1-#20(含 #17 双字段)恰好全覆盖。「27」系照抄代码 docstring 的陈旧注(`cw_exec_state.py:100`「27 具名…2」,该注自身已损坏),「19」两头不靠。覆盖性本身核验通过(无遗漏),但 §1 的两处事实断言均错。

**证据**:`cw_exec_state.py:98-217`(21 字段逐一清点);design.md:11/:13;landing 3.x 各阶段字段名并集 = 21。

**修复建议**:§1 两处计数改 21(处置表覆盖结论不变)。

### [11] 次要 | design §2.1 #20 | 三访问函数宿主地未定,「零改动」申报有前提未写明

**问题描述**:#20 说「`PlaneNodeLedger` 类随迁 cw_game_state.py」,但 `get_node_ledger`/`ledger_node_type`/`ledger_update_plane`(及 `fill_boss_by_position`)留在哪个模块未写。已核实消费面经三口:ObservedRe-exports 自 `cw_exec_state`(`cw_vocab.py:76-102`,含 PlaneNodeLedger 与三函数)、`cw_equip_wear_plan.py:219` 直接 import ledger_node_type 自 cw_exec_state、obs/各画面 op 同源——「全部写读点零改动」**只在三函数留守 cw_exec_state.py 时成立**;若函数随类迁走,零改动申报即假(六消费文件全要改 import)。

**证据**:`cw_vocab.py:76-102`;`cw_equip_wear_plan.py:219`;`obs/cw_observation.py:46-47`;design.md:43。

**修复建议**:#20 写明「三函数留守 cw_exec_state.py(模块保留面),类迁 cw_game_state.py,函数内惰性 import」,零改动申报才闭合。

### [12] 次要 | design #3 通道细节 | state_of 的冷建副作用与 None 态行为未定义

**问题描述**:#3 指定经 `state_of(session)` 读写(依据 flow/README §2.5,该节确有「消费经访问函数(strategy_state_of/impl 侧 state_of)」表述,依据存在)。但 `state_of` 会**冷建 StrategyState 并覆写 `session.strategy_state`**(None/异型时)——第三方策略/裸 session 下有副作用;而 kernel 侧既有跨层通道 `strategy_state_of` 是 None-safe 不冷建的。设计写「字段缺省 False 防御 getattr」暗示读侧防御,与 state_of 的非 None 返回语义不匹配;写端旗标在状态缺席时的行为未定义(现行为 = `_match` None 即跳过)。注册面封闭集 {mandate_v1} 下生产无害,但「执行层写策略器状态」这一跨层语义本身宜落进正本(flow/README 已在正本更新清单,补这条即可)。

**证据**:`mandate_state.py:349-360`(state_of 冷建覆写);`cw_strategy_session.py:76`(strategy_state_of,`mandate_state.py:52-56` 边界注「None = 第三方策略面…kernel 运行时零本包 import」);design.md:26。

**修复建议**:#3 明确:访问函数选型(state_of 的适用前提)或改 None-safe 通道;写端 None/异型态行为(跳过 or 冷建);正本更新清单 flow/README 条目补「执行层读写策略器状态通道」一句。

### [13] 次要 | design §2.2-1 + #12-#14/#17-#18 | 新 Field 的 set 形值、gs_schema 域归属与版本 bump 义务未申报

**问题描述**:①容器现役 Field 无 set 形先例(仅 `Field[dict[str,int]]` 等,`cw_game_state.py:2642/:2658`);#17 `round_sold: Field[set[str]]`、#18 `round_fresh_buys: Field[dict|None]`(值内含 set)的快照行序列化形态未申报。②#17/#18 新字段未指派 gs_schema 域(域键缺失 = 「该域未建模」,`DEFAULT_GS_SCHEMA` 无对应归属);#12-#14 落 match_facts 域属域内容变更,`:135`「域增删或字段语义破坏性变更时 bump 对应域版本」的适用性未表态。landing 正本清单只覆盖 README/fields.md 文字,未提 schema 版本面。

**证据**:`cw_game_state.py:131-162`(DEFAULT_GS_SCHEMA)、`:135`(bump 义务)、`:2642/:2658`(Field 形先例);design.md:40-41/:48。

**修复建议**:逐新字段补:域归属、域版本 bump 与否、值形状(建议 set→申报序列化为 list 或论证 set 直存可行)。

### [14] 次要 | design §2.1 #15/#16/#19 宿主与族标签 | tracked_books 语义稀释、#19 族标签与处置互相矛盾

**问题描述**:①#15/#16/#19 三者塞进 `TrackedBooks`(其申报契约 = 「tracked 主账」槽位表簿记,`cw_game_state.py:2694-2704`),混入停机计数/churn 代次/臂开关,稀释容器申报语义;设计给的依据只是「先例 = tracked_books/settlement_ring」——先例证明的是「非 Field 簿记可存在」,不是「这三者该住 tracked_books」。②#19 标「防重入族」但按裁定②该族处置 = 策略器侧记录,实际处置 = GameState——族标签与处置直接矛盾(其真实语义 = 执行面帧间臂闩,唯一消费 = 一行开合变更日志 `cw_screen_deploy.py:642-646`,按「谁产生/谁消费」甚至可评估直接删)。③#16 标「接管/恢复族(reconcile 纠漂产物)」——纠漂代次与接管/恢复语义不合,族标签牵强(处置本身可行)。

**证据**:`cw_game_state.py:2694-2704`(TrackedBooks 契约);`cw_screen_deploy.py:640-647`(#19 全部读写点);`cw_reconcile.py:387`(#16 唯一写点);design.md:38-39/:42。

**修复建议**:非 Field 簿记设独立宿主组(或给 tracked_books 扩容写依据);#19 改族标签(执行面观测闩)并评估删除;#16 改族标签(纠漂簿记)。

### [15] 次要 | landing 正本更新清单 + design §2.2-6 | 漏 flow/README §2.2 期望账句;沿用已正名废除的 bs_schema

**问题描述**:①`flow/README.md` §2.2 历史注有「**期望态对账保留(现行有效)**:对账时点 = 下一入口,经 `cw_prep_pending_accts` 暂存」——#9 删除该字段后此「现行有效」句失真,正本更新清单未列 flow/README §2.2(只列 §2.5)。②design §2.2-6 用「bs_schema」——全仓已正名 gs_schema(commit 9303fac0b:bs_schema→gs_schema、模块常量与字段同步正名),设计引用了已不存在的符号。

**证据**:`flow/README.md:84`;design.md:53;commit 9303fac0b(git log)。

**修复建议**:正本清单补 flow/README §2.2;design 行文 bs_schema 改 gs_schema。

### [16] 次要 | landing 3.6 完成判据 | 「全仓 grep 归零」与全仓注释锚冲突,字面不可满足

**问题描述**:判据「`ExecState`/`exec_state_of`/`bind_exec_state`/`.exec_state` 全仓(src + sr-od-test)grep 归零」——源码注释中 ExecState 字面锚大量存在且不随符号删除自动消失(mandate.py:486/:499、shop.py:822、cw_screen_deploy.py:743/:958、cw_screen_supply_node.py:23/:38-41、cw_screen_encounter.py:12、cw_screen_invest_strategy.py:18/:128、telemetry/schema.py:536/546/642 等);判据括注豁免仅列「模块内域函数与 cw_strategy_session.py 头注」,覆盖不了上述面。字面执行 = 判据必挂。

**证据**:上列 grep 命中(审计快照时点);landing.md:77。

**修复建议**:判据改「符号引用(import/属性访问/构造)归零;注释历史锚随正本更新清单逐条处置」。

### [17] 次要 | design §2.1 #11 | chosen_supply 写时点偏离 chosen_* 家族「出口验真后写」口径,分叉未申报

**问题描述**:现行写端自注「照 chosen_tome『出口验真后写』口径」(`cw_screen_supply_node.py:291-294`);#11 改「确认即写」并论证了重入覆盖安全(「观察赢覆盖,无账可污」),但未说明:①为何 supply 单独偏离家族口径而 chosen_tome 不跟随;②确认未落地窗内 chosen_supply 短暂持未落地选定——经 grep 现无决策读者(仅写点与字段定义),低危,但口径分叉应在设计显式申报,否则后续 chosen_tome 迁移无先例可循。

**证据**:`cw_screen_supply_node.py:172-198`(:291-294 家族口径注)/`:295-296`(暂存写点);`cw_game_state.py:2713`(chosen_supply 定义,无其他消费点);design.md:34。

**修复建议**:#11 补一句口径申报(「supply 确认即写,chosen_tome 维持验真后写;差异理由 = X」),或两屏一并对齐。

---

## 核验范围与覆盖面申报

**处置表覆盖性(核一①)**:ExecState 设计快照时点 dataclass = 21 具名字段,处置表 #1-#20(含 #17 双字段)+ #21(载体)**全覆盖,无遗漏**——正面结论,仅 §1 计数错(发现 [10])。

**消费点申报逐字段核验结果(核一②)**:

| 字段 | 申报 vs 实核 |
|---|---|
| #1 deploy_fail_counts | ✓ 零写端零读者属实 |
| #2 equip_drag_fail_counts | ✓ 三处死读属实(:53/:402-403/:470,快照时点);牵连面见 [4] |
| #3 megastar_candidate_clicked | ✓ :119/:147/:175 属实;类名与通道问题见 [8]/[12] |
| #4 _supply_refresh_used | ✓ 读 :246、写 :269 属实;schema 归段问题见 [9] |
| #5 _encounter_refresh_used | ✓ :175/:316/:443 属实;双写端风险见 [6] |
| #6 _invest_refresh_used_slots | ✓ :294/:330/:468 属实(:330 系写点,标注误);见 [6] |
| #7 pending_buy_expect | ✓ :1396/:3097-3101/:3485 属实;BuyPurchase 存活与 3.2「留模块删类」括注相容 |
| #8 xp_expect_ledger | ✓ :1477-1486、schema.py:473 属实 |
| #9 cw_prep_pending_accts | ✓ 四段行号逐段属实;正本漏项见 [15] |
| #10 _supply_detour_done | ✓ 全仓仅定义处属实 |
| #11 _pending_chosen_supply | ✓ :162-180/:295 属实;口径分叉见 [17] |
| #12 cw_resumed_match | ✓ 写在 `_mark_session_resumed`(申报 :1059,实 :1129,符号对)、读 cw_observation.py:2694、test:212 命中,均属实 |
| #13/#14 takeover 两字段 | ✓ :2415-2452 读改写属实 |
| #15 star_regression_count | ✓ 209/298 唯一写读者属实;消费面申报失真见 [7] |
| #16 bench_layout_epoch | ✓ 写 reconcile:387、消费 :1002/:247 属实;文件面缺漏见 [3] |
| #17 v2_round_key/v2_round_sold | 申报**不实**——见 [1](本轮唯一致命) |
| #18 cw4_swap_fresh_buys | ✓ :965(已收 gs)/:984/:987/:1018 属实,sim/live 同口单口属实 |
| #19 cw4_swap_arm_on | ✓ :642/:647 属实;族标签与宿主问题见 [14] |
| #20 plane_node_ledger | ✓ 消费经三口属实;函数宿主未定见 [11] |
| #21 载体 | ✓ cw_strategy.py:206 字段/:211 绑定属实;测试面见下 |

**测试面**:设计/landing 点名的 `test_cw_game_state_contract.py` §8(延迟绑定,:344-351)与 `test_cw_shop_unobserved_gate.py:212`(cw_resumed_match)均存在;`_pending_chosen_supply`/`_encounter_refresh_used`/`_invest_refresh_used_slots`/megastar 旗标均有在册测试消费(test_cw_game_state_consume / test_cw_obs_arch_event_screens* / test_cw_obs_arch_phase_screens),landing 各阶段以「sr-od-test/受影响用例」泛列可覆盖;**3.4 点名的两测试不存在**(见 [2])。

**核二② GameState 治理**:Field/非 Field 分界与模块头治理引用**成立**(模块头 :17 治理三件在、fields.md §8.8 治理面在 :1273、tracked_books 非 Field 先例注在 :2694-2704);渠道签名:logic_action/logic_hook 均有在码先例(relay 契约 = logic_hook 族,cw_observation.py:2650-2656),#4-#6/#12-#14 渠道指派合规。「写端未接」前提属实(game_state/README §3.3 node_screen_refresh 行「环境/补给零写端在册」与 fields.md §3.4.1-3.4.4 节存在)。

**核三**:迭代本体(拆第三类载体)是架构级治本,方向成立;反例 = #17(迁僵尸机制,发现 [1])与 #15(带删除预告的状态迁容器而非删,发现 [7])。四个未点名字段的裁定对照:#16/#20 处置合理(问题分别在文件面与函数宿主);#15 处置依据失真;#19 族标签矛盾、可评估删除。

**部分核验/未深核(如实申报)**:①#15 的 `_star_stop_hook` 当前存续状态未独立定位(依据 = reconcile 内注);②#8「decisions 行两文件模型不受影响」仅核 schema.py:473 注释锚,未核决策行 schema 全文;③#20 六个消费文件仅核 import 面,未逐文件核调用形态;④test_cw_shop_unobserved_gate.py:212 与 contract §8 仅定位命中,未读全文上下文;⑤「零写端期间禁按字段值做决策」申报段的精确位置未定位(fields.md §3.4.x 区域存在同类句,landing 3.3 判据的可操作性已因 [5] 另立发现);⑥sim 目录 exec_state 零命中依首轮全量 grep(117 命中全集无 sim 文件)佐证,未逐文件复查。

---

## 复审(r2)

> 对象 = 修订稿(commit 410e01998,design.md/landing.md 全文重写)。只核修订是否成立与有无新失实,不重开全量攻击。修订稿新引入的事实申报逐项回到代码验证(非采信自述)。

### r2-1 逐条闭合判定

| 原# | 判定 | 核验依据 |
|---|---|---|
| [1] 致命 | **闭合** | #17 改判删,删除面经 grep 复核完整:`register_round_sold` 唯一调用方 = cw_sell_bench_action.py:67-70(懒 import + 调用),再无他处;两字段注释锚(cw_exec_state.py:147-148)随字段删除;调用方归属已改正;三条改判依据(零写端/消费面已死/第二已卖账)如实落表,§2.3 取舍二补同构论证。模块去留微瑕见 r2-C。 |
| [2] | **闭合** | landing 3.4 明示「既有测试不存在,本阶段补」,文件面补新增测试;另补卖出落地路径行为对照判据。 |
| [3] | **闭合** | 3.5 文件面补 cw_screen_buy_cards.py + cw_shop_action_ops.py,标注 = #16 消费点。 |
| [4] | **闭合(已实证)** | 3.1 文件面补 cw_op_equip_all.py + mandate.py;「已落地」申报属实——commit 83ea60e5d 实改恰 4 文件(cw_equip_wear_plan/cw_exec_state/cw_op_equip_all/mandate.py),与文件面逐一吻合。 |
| [5] | **闭合** | 判据改「三字段(supply/encounter/strategy)写端在产;env_refresh_used 维持零写端申报不动」,3.3 边界显式排除 env。 |
| [6] | **闭合** | #5/#6 行 + §2.2-3 双计毒化红线条款闭合(「只删 ExecState 置位/清零/add 行,禁新增第二容器写点」);#6 读写点标注修正;新增判据「单次刷新恰 +1 无双计——测试断言」可验;「测试在锁」申报属实(test_cw_obs_arch_phase_screens.py:34/:445 发射型接线锁在册)。 |
| [7] | **闭合** | #15 族标签改「留证采样簿记」并注明 attack [7] 修正;「不评估本迭代删」显式声明为战术取舍(退役前置 = SIFT 修复,另批)——符合「症状修法须声明权衡 + 排期」;`star_pending_regression` 入 §1 明确不解决④。 |
| [8] | **闭合** | 全文 MandateState → StrategyState(design/landing/正本清单),§1② 注明正本 flow/README §2.5 旧名随正本批修正。 |
| [9] | **闭合** | #8 行「3.2 仅删 xp 字段;refreshed 归 3.3(防遥测空窗)」;landing 3.2/3.3 范围与文件面归属注同步。 |
| [10] | **闭合** | §1 两处计数改 21。 |
| [11] | **闭合** | #20 行写明「类迁 cw_game_state.py;三访问函数 + fill_boss_by_position 留守 cw_exec_state.py,函数内惰性 import 类」,零改动申报前提闭合;landing 3.5 同步。 |
| [12] | **闭合** | §2.2-4 通道改 kernel `strategy_state_of`(None-safe 不冷建;符号在 cw_strategy_session.py:76,None-safe 语义依据 = mandate_state.py:52-56 边界注),禁 impl 侧 state_of 从执行层调用;写端缺席态 = 跳过;读侧防御 getattr;正本清单补 flow/README 通道一句。 |
| [13] | **闭合且可执行** | §2.2-1a 逐新字段给域归属(match_facts bump / 新域 round_ledger + 版本项 / 既有 node_screen_refresh);#18 值形状申报 set→list(序列化安全 + 读端量级论证);3.5 判据补「match_facts 域版本 bump 落行(journal 断言)」。 |
| [14] | **闭合(新申报已验证)** | ExecBooks 独立簿记组(§2.2-1b,不塞 tracked_books,含判定依据);#19 族标签改「执行面观测闩」并附删除评估记录——新依据「projection_contract §4.3 在册判读面(臂态位)」**经查属实**(flow/projection_contract.md:101 节、:104 明列「臂态位:ExecState.cw4_swap_arm_on…供判读开合抖动」;该正本锚已在 3.6 正本清单辖内)。 |
| [15] | **闭合** | 正本清单补 flow/README §2.2 条目;行文 bs_schema 已全改 gs_schema。 |
| [16] | **闭合** | 3.6 判据改「符号引用(import/属性访问/构造)归零」,注释锚移交正本清单;正本清单新增专条「注释历史锚处置」列名七文件。 |
| [17] | **闭合** | #11 行口径分叉显式申报(supply 确认即写 + 差异理由 = 载体消亡;chosen_tome 维持家族口径;未落地窗低危——chosen_supply 确无决策读者,r1 已核);landing 3.2 要求注释同步。 |

### r2-2 修订稿新引入申报的事实核验(全部属实)

- 「已落地(commit 83ea60e5d)」:commit 存在,`git show --stat` = 恰修订文件面所列 4 文件。
- design #9 三通道分解「paddle 审计/drag_expect/equip_expect,输入全为 acct 暂存」**属实**:acct dict 键与消费位(cw_screen_prep.py:1997-2000/:3128-3149;paddle 审计 reader_source='paddle_action_audit' :3122);保留的纯观察审计三通道 `_reconcile_faction_display`(:1606)/`_reconcile_shop_pool`(:1674)/`_reconcile_merge_preview`(:1731)存在且仅吃 obs。
- `DragExpect` 族存在(cw_prep_expect.py:52/:70/:100)。
- design #4「sim 已经 observe 在写、本屏无 on_outcome 注册件、无双计面」属实(cw_sim_engine.py:569-571;cw_screen_supply_node.py:38-41)。
- design #6「闸 1 = 屏上余量现读」双闸论证与字段注一致(「可否再刷」权威判定 = 逐卡计数现读,ExecState 集唯一职责 = 同 visit 防重入),visit 清零语义消亡无重入放大面。
- #4/#5「>0 = 已用」语义保真:现役两 ExecState 旗标均无复位点(每局闩),容器累计计数同语义。

### r2-3 残留发现(无致命/重要;两条次要 + 一条提示)

**[r2-A] 次要 | landing 正本更新清单(session.md 条目)| 清单不完整:session.md 正本携带与 r1 [1] 同源的 v2_round_* 误判,删除后多处 as-designed 断言失真,清单未点名。** session.md:94(§2.4 表)称 v2_round_key/sold「**活写端** = register_round_sold 带轮键自校验登记,**live 调用方 = cw_shop_action_ops.py:487**」——两断言皆误(守卫恒假 no-op;唯一调用方 = cw_sell_bench_action.py:70,与 r1 [1] 同一误判谱系);派生面:§3.2 风险表 :150(同轮已卖集评级「中」)、§6.2-4 判读义务(:148/:264)、§6.1 切换批迁移指令(:219/:243「活读写点换源」)均建立在该误判上。#17 改判删后,现行清单只覆盖「§2.4 表落点列/§2 统计行/§4」,上述四处失真不在清零面 → 收尾判据「正本与实现一致」不收敛。**修复:session.md 正本条目补点名(§2.4 该行活写端误判修正、§3.2 风险表行、§6.1 迁移指令作废注、§6.2-4 判读义务注销)。**

**[r2-B] 次要 | landing 3.2 完成判据 | 符号归零清单漏 EquipExpect 族。** 范围含 equip_expect 期望账通道拆除,其载体 = cw_prep_expect.py:457-577 的 `EquipExpect`/`compute_equip_drag_expect`/`compare_equip_expect`/`EquipDragIntent`(消费 = _reconcile_equip_expect :1870),判据只列「BuyExpect/XpLedger/DragExpect 归零」→ EquipExpect 族有成为死码残留的面。**修复:判据符号清单补 EquipExpect 族(或显式并入「存活函数逐一注明」的排除申报面)。**

**[r2-C] 提示(不阻断)| design #17/landing 3.4 | `cw_round_ledger.py` 模块去留未申报**:register_round_sold 是该模块唯一函数,删除后仅剩 docstring;全仓无其他 import 方,删模块可行,但设计未写明「删模块 or 留空壳」——停手令条款下应写明。另正本清单 game_state/README 条目把非 Field 簿记 `plane_node_sequences` 系在「节点域」名下(域 = Field 分组),正本批措辞需归位至簿记申报处(fields.md 条目已覆盖,不阻断)。

### r2-4 试读结论(landing 3.2-3.6 凭这份能开工吗)

**能。** 3.2:通道分解/保留面/符号清单/归段(refreshed 归 3.3)全部落字,唯一缺口 = r2-B 判据符号面;3.3:通道选型(strategy_state_of 禁冷建)、双计红线、env 排除、判据四条均可验;3.4:改判删的删除面完整(唯一调用桩定位)、新增测试义务落文件面、值形状/新域申报可执行;3.5:ExecBooks 宿主、域版本 bump 判据(journal 断言)、三函数留守前提、边界排除(star_pending_regression/_star_stop_hook)齐备;3.6:符号形态归零口径 + 注释锚清单移交正本批,判据可执行。

### r2 结论

**可定稿**——前置完成两处一行级补正(r2-A 正本清单 session.md 条目补点名、r2-B 判据补 EquipExpect 符号),无设计语义级残留;17 条原发现全部闭合,修订稿新引入申报经代码验证无一失实。
