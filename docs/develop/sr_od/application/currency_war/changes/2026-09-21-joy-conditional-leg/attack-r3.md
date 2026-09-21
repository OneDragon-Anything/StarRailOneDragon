# joy-conditional-leg 设计·第三轮对抗攻击报告(独立新视角)

> 攻击对象:`design.md`(定稿态)+ `landing.md` + `README.md`;处置表复核对象 = `attack.md`
> r1/r2 处置记录。规范依据 = `docs/develop/harness/iteration-design.md` §7 三核。
> 本轮 = 全新眼睛:前两轮未覆盖的面、处置引入的新面、「所有人都以为对」的暗默认。
> 证据全部为仓库现状实读。共 6 条发现(0 阻断 / 3 应修 / 3 建议)。

---

## 1. 符号/锚全量核验结果(先行声明,不计发现)

以下本轮独立实读相符,不作为攻击点:

- `pick_planner.py:58` 两相形态/:73-78 发射相零写/:79-88 三腿分派+兜底(现状 reason='weaken_leg_zero_write',`leg_type=''` 与 `'weaken'` 共用此兜底)/`:19-20`/:67/:88 weaken 字样行号——design §2.2-7③ 行号锚逐个相符 ✓
- `cw_screen_yinlang.py:195`(node_max_retry_times=5)/:204-222(重入裁决出口;`:205` _confirm_pending 置 False、:210-211 载荷清空、:213 `_mgs is not None` 局外门、:214 落地相调用)/:255-256(载荷重建)——r1 发现 3 引用的失效通道语义逐行复核成立 ✓;classify 恒产非空 leg_type(`cw_events.py:1019` 空文本 → unknown),生产 leg_type='' 不可达,''直调 = 纯测试形态,design §2.6「兜底形态」注记准确 ✓
- `cw_overlay_pick_action.py:124`(leg_type 词表注释)/:404(`_confirm_pending=True` 重置)/:418(发射相调用,evidence 缺省)锚准;发射相 actor=PlannerPickOp、落地相 actor=CwScreenYinLang,rider 随落地相 sig 归因与既有腿一致 ✓
- `anchor_aware_write`(`cw_game_state.py:1792-1807`,`rand or not prep_anchored_of(gs)` 短路)与 r1 处置后 design §2.2-3「rand 形参优先于锚定状态」口径一致 ✓;`test_cw_gain_chain.py:244-262` 臂 1/2/3 锁实存,§2.6「与既有臂 3 锁同语义」引用准确 ✓
- observe 通道:`cw_game_state.py:2476-2484`(logic_rand 差异 → `logic_rand_outcome` 行,等值不产行)、:2485-2495(logic 失配 → 三分流)、:863(`observe_vs_logic_mismatch` kind 实存)——§2.6 校准面判据与 §2.5-1「无失配网」申报锚全准 ✓
- `roll_hacker_mod`(`cw_gain_effects.py:59-63`,`rng.choice` 纯函数)与 `gain_invest_strategy`/`on_strategy_gained` 的 `rng: Random | None = None` 缺省形态(:530/:688)——§2.2-2「rng 注入先例」两个先例均在册,形态可唯一推出 ✓
- import 无环:pick_planner 新增消费面 cw_gain_chain/cw_investments,二者 import 面(cw_gain_chain:64 已 import cw_investments)均不回指 cw_action_report ✓;`PLANNER_LEG_WEAKEN` 全 src 仅 cw_events.py:908 定义处,零外部 import,删除安全 ✓
- 撤闩面:`JOY_PROVISIONAL_KIND` 4 处(:90/:616/:640/:651-653)全在删除面;模块 docstring 失败安全句(:21-22「best-effort 边界只在登记/遥测申报腿内」)将被 rider 调用点级例外证伪——§2.2-6「模块 docstring 失败安全自述同步改写」已辖,且 gain-chain.md §6 申报已在正本清单(r2-2 处置)✓
- ENV_GIFTS 欢愉契约条目(cw_investments.py:1575-1581):chars_immediate=('银狼LV.999',)/chars_conditional=(('火花', 触发条件文),('开拓者·欢愉', 触发条件文))——r1 核验相符 ✓
- **rider 先行与腿内容器交互(本轮独立推演,安全)**:rider 在分派前授予写 bench(logic_rand)后,upgrade 腿 `view = gs.bench.value`(:149)为**腿内现读**、已含 rider 新授予单位,`merge_cascade_write(orig_view=view)` 级联推演正确继承之;equip 腿写 equips 域与 rider 的 bench 域零交集;同帧「logic_rand + logic」双写分属不同字段,通道互不污染。前两轮未验过的交互面,核明无问题 ✓
- **active_env 无二次覆写暗默认(本轮重点核查,成立)**:投资环境 = 开局一次性选择——`node-derivation.md` E3「位面过渡 → 投资环境(0s)| 零(**开局事件**)」、sim-redesign design「开局 (1,1) 无策略选卡——entry 第二屏即投资环境屏」与「投资环境在场 = 显式参数」、`screen_flow_timing.md` #11/#29(P1 boss → 位面过渡 → 直进 2-1,无环境选择)。active_env 单写端 = gain_invest_env,一局恰调一次,欢愉契约在册判定无「环境中途替换致漏判」缺口 ✓
- tool-gain-report 在飞批目录实存(`changes/2026-09-21-tool-gain-report/`),§2.7 依赖指针真实 ✓
- 「欢愉契约」与「战技点契约」条件腿同名单位「火花」(cw_investments.py:1565):在册判定挂 active_env、evidence 前缀区分来源,零干扰 ✓;evidence `joy_conditional:<名>` 与链内 `#place`/`#mergeN` 后缀(:489)兼容,前缀计数判读不受影响 ✓

---

## 2. 发现清单

### r3-1 [应修] | design §0 状态行 | 状态失同步 + 过程叙事双违规:正文仍「草案(r1 攻击 11 条处置完毕,候复审)」,README 已「定稿」

- **问题**:①状态失同步——iteration-design.md §6「未决 = 停在草案/对抗审中,**状态由总纲 §0 表达**」,README 进度已改「迭代设计:定稿(攻击收敛·试读过)」,而 design §0 仍写「状态:草案(r1 攻击 11 条处置完毕,候复审)」——同一迭代两份文档对流程状态各执一词,r2 复攻 §4 明文预告「r2 后需同步更新进度行」,编排者只更新了 README,§0 漏网;②过程叙事——括号内「r1 攻击 11 条处置完毕,候复审」是「第几轮攻击 + 处置进度」叙事,硬规则 3(无过程叙事)的卡点措辞直接命中。落地批立任务时「定稿才可派工」的门槛判定将以哪份文档为准产生歧义。
- **证据**:design.md:16「- 状态:草案(r1 攻击 11 条处置完毕,候复审)」;README.md:8「- 迭代设计:定稿(r1 11 条 + r2 5 条处置完毕;攻击收敛·试读过)」;iteration-design.md §5 硬规则 3、§6 状态语义。
- **处置方向**:§0 状态行改「状态:定稿」,删过程叙事括号(进度归 README 一处,硬规则明确)。

### r3-2 [应修] | design §2.2-7② + 退役判据 | decide_planner docstring 中文弱化档引用残留缺口:「三层定序自述删除」辖不住散布在其他条目里的两处弱化档引用,且「grep weaken 清零」判据对纯中文表述零辖域

- **问题**:r1 发现 6 处置把 decide_planner 注释面收进「docstring 三层定序自述删除」,但实码弱化档引用不止「三层定序自述」一处:①:844-846 三层定序句(辖内 ✓);②:852 升费档条目内「**(100−60,落到弱化档之下=投资无处兑现)**」——降档语义锚定在「低于弱化档 55 分」这个已退役的比较对象上,弱化档删除后该句失真且 40 分降档的自述依据需重写,不在「三层定序自述」字面辖域;③:856 装备档条目内「(+15,**只在装备档内排前,不跨域压弱化档**)」——同上;④:853-854 弱化档条目本体(删打分连带删,✓)。而退役判据「全仓(src)grep weaken 残留清零」是英文字面检索——decide_planner docstring 全部弱化表述均为中文(「弱化档」「全场弱化」),**grep 'weaken' 对这段零命中**:就算实现者删了 55 分打分、docstring 一字未动,判据仍绿,残留失真不被验收捕获。恰是裁定③「没找到证据的就是不存在」的验收盲区。
- **证据**:cw_events.py:844-846(「ADR-0524 定形(16 号稿 §1.7):三层定序结构 = 升费档 > 弱化档 > 装备档」)/:852(「落到弱化档之下=投资无处兑现」)/:853-854(弱化档条目)/:856(「不跨域压弱化档」)/:881-884(弱化档打分本体);design §2.2-7②(「及其 docstring 三层定序自述删除」)与判据句(「全仓(src)grep weaken 残留清零」);grep 实测:decide_planner 段无 'weaken' 字面。
- **处置方向**:§2.2-7② 扩为「decide_planner docstring 弱化档**全部表述**(三层定序句/:852 降档语义句——降档依据改写为两档制下的现役表述/:856 不跨域句/弱化档条目)同步两档制;判据补中文域,如「grep 'weaken|弱化档' 于 cw_events.py decide_planner 段清零(碰撞治理注释 :903/:1005 的『弱化』为合法保留,判据域限定函数段)」。

### r3-3 [应修] | design §2.4 接管局边界 | 申报双失准:依据「C 类不种」张冠李戴(active_env 系 A 类种 '');「条件腿在接管段不可达」对「接管恰逢开局选卡画面」通道不成立

- **问题**:①依据失实——§2.4「active_env 接管局无写端(**C 类不种**,gs-opening-seed §2.2)」:gs-opening-seed 分诊表实文 active_env 列 **A 类——种**(种子值 '';C 类仅 selected_difficulty/enemy_difficulty 两字段);fields.md §2.6 局级事实域同列 active_env 种 ''。active_env 接管局恒 '' 的真实依据 =「A 类种子 '' + 开局链写端不复现」,与「C 类不种(接管局无观察源,种 = 错一整局无人纠正)」语义相反,依据就地标注错挂。②结论过强——「条件腿在接管段不可达」存在真实例外通道:cw_loop 画面分发对「货币战争-投资环境」**无开局/接管区分**(分发分支按画面身份命中即派发),接管/重启恰逢投资环境选卡画面时 CwScreenInvestEnv 确认链**即时上报** → gain_invest_env 照常执行 → active_env 有写端、on_env_gained 送银狼(A 类种子 bench=[] 已种,落位成功)→ **锚定后条件腿完全可达**。run 中途 stop/重启是常态运维形态(第八局接管实证在册),开局段 stop 重启的真实窗口存在。申报「不可达,真值归观察覆盖」把该通道的授予面错误归入观察兜底。
- **证据**:cw_loop.py:1498-1519(「货币战争-投资环境」分发分支,无接管门);cw_screen_invest_env.py:309-311(确认链即时上报);pick_invest_env.py:47-50(canon 非空直调 gain_invest_env,rand=False);cw_gain_chain.py:464-478(active_env 写 + on_env_gained 链);gs-opening-seed design.md:90(`active_env | '' |` 在 A 类表)/:115-120(C 类 = selected_difficulty/enemy_difficulty);fields.md:119-120(局级事实域含 active_env '');cw_game_state.py:1775(`_seed(gs.active_env, '')`);cw_loop.py:829-832(第八局接管实证,stop 重启形态在册)。
- **处置方向**:§2.4 接管局条改写——①依据改「A 类种 ''(gs-opening-seed 分诊表 active_env 行)」;②分形态申报:中段接管(容器冷建、开局链不复现)active_env 恒 '' → 条件腿不可达,真值归观察覆盖;接管恰逢投资环境选卡画面(loop 分发)→ active_env 有写端、on_env_gained 照常,条件腿锚定后可达,与正常局同语义。

### r3-4 [建议] | design §2.2-2 | 采样候选集来源未定义:字面「随机[火花, 开拓者·欢愉]」诱导硬编码,与 ENV_GIFTS 声明性数据成第二抄本

- **问题**:候选集在 ENV_GIFTS['欢愉契约'].chars_conditional 已结构化在册((单位名, 触发条件描述)二元组);r1 复攻留档亦认定「chars_conditional 消费面 = 本模型 + 判读」。但 design 正文未写候选集单一源,§2.1/§2.2-2 字面只有固定二元列表——实现者照文硬编码 `['火花', '开拓者·欢愉']`,游戏版本调整候选集时 ENV_GIFTS(判读/族批消费)与 rider 硬编码两处漂移,违数据单一源纪律。语义可从 r1 留档推出,但留档非设计正文,「实现者无需再设计」差一步。
- **证据**:cw_investments.py:1577-1580(chars_conditional 结构);design §2.1「随机[火花, 开拓者·欢愉]」/§2.2-2「random.choice 均匀二选一」(无来源裁定);attack.md r1 留档「chars_conditional 字段保留为声明性档案(消费面 = 本模型 + 判读)」。
- **处置方向**:§2.2-2 补一句裁定——「候选集单一源 = `ENV_GIFTS['欢愉契约'].chars_conditional` 名字列(数据驱动,禁硬编码第二份)」;若裁定硬编码,则显式声明 chars_conditional 降级为判读档案并说明理由。

### r3-5 [建议] | design §2.2-1 | 缺陷行 expected/actual/evidence 三字段内容未落(r2 发现 5 处置不完整,复核节同记)

- **问题**:r2 发现 5 的处置方向含两部分——「except Exception 词表」+「缺陷行 expected='条件腿授予成功' actual=异常摘要,evidence=joy_conditional:<单位名>」;r2 处置记录只采纳了前者,design §2.2-1 现文仅 `kind = 'joy_conditional_grant_failed'`,缺陷行其余字段仍由实现者拍板。登记腿先例(:472-475/:587-591)字段形态为 expected=中文目标/actual='…异常:{e}'/evidence=链前缀,可对齐,但未就地标注 = 实现者需自行开先例文件(与 r2-5 立发现时同一判据)。
- **证据**:design §2.2-1 现文(仅 kind + except 词表);attack.md r2 处置表 r2-5 行(采纳范围只列 except);cw_gain_chain.py:472-475/:587-591(先例字段形态)。
- **处置方向**:§2.2-1 补「缺陷行 expected='条件腿授予成功' actual=异常摘要,evidence=`joy_conditional:<单位名>`(对齐登记腿先例字段形态;单位名在调用点已采样可知)」。

### r3-6 [建议] | landing §3.1 完成判据第一条 | 「通道语义」括号缺覆盖校准面断言,§2.6 判据组成在账本唯一源面不全

- **问题**:design §2.6 通道语义条由两半组成——①「source 仍 = logic_rand」+②「授予校准面断言 = 覆盖时落 `logic_rand_outcome` 行(零 observe_vs_logic_mismatch)」;landing 判据行「通道语义(未闩=rand/置闩后 rand 授予仍 = logic_rand,rand 形参优先于闩)」只承载①,行首「行为对照 design §2.2-§2.5」的引用域又不含 §2.6(②的宿主节)。阶段小节 = 账本立任务唯一源,照现文立任务则②校准面断言漏立,与 r2 发现 1 同型(判据面在 landing 不完整)但幅度小(断言语义本身在 design 无争议)。
- **证据**:landing.md:28;design §2.6 通道语义条全文;cw_game_state.py:2476-2484(outcome 行发射语义)。
- **处置方向**:landing 判据行「通道语义」括号补「覆盖校准面 = logic_rand_outcome 行(零 observe_vs_logic_mismatch)」,与 design §2.6 对齐。

---

## 3. 已查证为协调的点(攻击过、不成立,留档防复议)

- **触发路径封闭性**:生产落地相唯一入口 = CwScreenYinLang 重入裁决出口(cw_screen_yinlang.py:214;classify 恒产非空 leg_type,:1019);发射相调用点(cw_overlay_pick_action.py:418)evidence 缺省先于 rider 落点 return,零触发;局外 `_mgs is None` 不调 report(:213)。无第四调用点(grep 全 src)。
- **在册判定的时序与幂等**:active_env 一局恰一次写(开局一次性选择,见 §1 暗默认核查),判定值在落地相期间恒定;「恰一次授予」由证据闩计数承载(r1 发现 3 已申报失效通道,本轮复核 :205-211/:255-256/:404 实码一致)。
- **星级先验的处置哲学分岔合理**:immediate 腿 1★ 先验「先验错 = 响停修因」(rand=False → 失配网可见)vs 条件腿 1★ 先验「观察覆盖静默校准」(rand=True → 无失配网)——两者处置差异由通道差异决定,非双标。
- **授予时点差**(弹窗出现 vs 确认关闭)已在 §2.8「残余不确定(分布形态/授予时点/星级先验)」辖域内,观察/outcome 行自然校准,无新增暴露面。
- **bench 挤压/溢出**:gain_character 固定时序(席满 → overflow 写;溢出位被占 → 零写留证)为链纪律,生产容器 bench 冷建即种(A 类)不可达 None;§2.5-2 已申报高频触发的 bench 压力面。
- **upgrade 腿前置计数不受 rider 干扰**:rider 授予的是火花/开拓者·欢愉(非银狼),`(银狼LV.999, 2★)` 恰一枚判定零影响;腿内现读语义见 §1。
- **「发射相意图遥测」日志措辞**、`leg_type=''` 兜底形态、`_PLANNER_PRODUCER` 归因、evidence 后缀兼容:零新增面。
- **test 面可判定性**:§2.6 各判据(三腿恰一次/发射相零/''兜底/rand 通道/撤闩等价形式/退役锁)逐条可落断言;test_cw_yinlang_phase32.py:160/:273-286 既有断言的改写由退役锁判据隐含(r1 已留档「可执行」,本轮复核维持)。

## 4. 前两轮已裁决面复核(只记复核后认为处置有误/不完整者)

- **r2-5(缺陷行字段标注)处置不完整**:处置方向含「except 词表 + 缺陷行 expected/actual/evidence」两部分,处置记录仅采纳前者,design §2.2-1 至今缺字段内容——已立为 r3-5(建议),方向仍循 r2 原处置,补落即可,不构成翻案。
- **r1-6(weaken 注释面清点)处置有残余缺口**:「decide_planner docstring 定序自述同步」仍辖不住 :852/:856 两处散布引用,且 r2-3 修订后的 grep 判据对中文表述盲——已立为 r3-2(应修),系处置范围定义(「三层定序自述」)偏窄 + 判据域(英文字面)不足,非方向错误。
- **其余 13 条处置(r1 全部 11 条 + r2-1/r2-2/r2-3/r2-4)**:逐条对照修订版实文复核,落点真实、方向正确、与实码一致,无翻案。

## 5. 试读结论(逐阶段「凭这份能开工吗」)

- **3.1 rider + 撤闩 + weaken 退役**:**可开工**——r2 两处单点修订后语义选择已全部写死;r3-2/r3-4/r3-5 属注释面/单一源/字段标注面,不构成开工阻塞,随修订顺手收口;r3-3 申报面失准不改变实现行为(rider 逻辑两种接管形态下行为均正确),修订 §2.4 文字即可。
- **末阶段正本更新**:清单与 r2 处置后自洽;r3-6 为判据行补全,不涉清单。

## 6. 收敛判定

**维持定稿,无需再轮全量复攻。** 0 阻断;3 条应修(r3-1 状态行同步、r3-2 注释面+判据域补齐、r3-3 接管局申报改写)均为申报/注释/依据面单点修订,无语义选择翻盘、无判据不可实现;3 条建议(r3-4/5/6)顺手收口。修订完成后按现设计落地。

---

## r3 处置记录(单点修订,本节由编排者记)

| 发现 | 处置 | 落点 |
|---|---|---|
| r3-1 状态行失同步+过程叙事 | 采纳:状态改「定稿(r1 11 条 + r2 5 条处置完毕;r3 独立复攻 0 阻断维持定稿,应修三条已折入本稿)」 | design §0 |
| r3-2 中文弱化引用缺口+判据域 | 采纳:§2.2-7② 点名 :852/:856 两处散布引用;退役判据改双语「grep `weaken\|弱化档`」并注明中文引用对英文字面 grep 零辖域 | design §2.2-7 |
| r3-3 接管局申报双失准 | 采纳:重定性——active_env 属 A 类(种子 ''),bot 走过投资环境屏即照常写入(分发无开局/接管门),锚定后条件腿可达;残留局限窄化为「接管前已选而 bot 未走过该屏 → 保持 '' → rider 不授予,真值归观察」;§1 明确不解决行同步改写 | design §1/§2.2/§2.4 |
| r3-4 采样候选集来源 | 采纳:候选集单一源 = `ENV_GIFTS['欢愉契约'].chars_conditional` 名集,禁字面硬编码第二抄本 | design §2.2-2 |
| r3-5 缺陷行字段未落 | 采纳:补 expected/actual/evidence 字段内容(循 r2-5 原处置方向) | design §2.2-1 |
| r3-6 landing 判据缺校准面断言 | 采纳:第一判据补「覆盖校准面 = 覆盖时落 logic_rand_outcome 行」 | landing 3.1 |
