# 备战契约接口收口为单动作 · 对抗审查报告(attack7)

> 审查对象:本目录 README.md / design.md / landing.md;`src/sr_od/application/currency_war/strategies/impl/cw_strategy.py::CwStrategy.decide_prep_screen` docstring(工作区未提交修改,逐句核 as-built 属实);`docs/develop/sr_od/application/currency_war/strategy-docs/README.md`(工作区未提交修改,核数字/指向/表格结构)。
> 方法:无前提对抗;数值/口径/引文/码点全部直调代码与正本文档复核,未转述。行号为撰写时工作区实态,以符号定位为准。

## 结论

发现 6 条:**高 0 / 中 3 / 低 3**。审查对象 2(docstring as-built)与审查对象 3(strategy-docs/README 两处修改)本体零发现;发现全部落在设计稿/落地稿的依据失真与验收判据可执行性上。

## 发现清单

### F1(中)changes/ 引用注释清单计数与形态失真,且有一处引用在「点名 + 扫尾」两层检查下都拦不住

- 位置:design.md L75(`changes/` 引用注释条目);landing.md L5(3.1 范围 ③「两处 `changes/` 引用清理」)。
- 直调事实(`cw_screen_prep.py` 全文件 grep `design\.md|unified-action-factory`):
  - 设计称「实态 4 处(L664、L984、L2103-2106、L2325-2326,**均引「design.md unified-action-factory §2.4」**)」。实态:
    - L664(`_observe` 装配段注释)实文 =「已随 **unified-action-factory 批2b** 退役删除」——**无 design.md 指针、无 §2.4**;
    - L984(`_project_prep_obs` docstring)实文 =「design.md unified-action-factory **§2.6**」——§ 号非 2.4;
    - L2103-2106(主循环终结判定注释)与 L2325-2326(`_terminal_exit` docstring)= §2.4,仅这两处与描述相符。
  - 另有 **L2537**(书册卡分支注释):「书册卡(R10 链拆,**design.md §2.6**):…」——同族 changes/ 引用(指向已删档/将删档的迭代设计稿裸名),**不在 4 处点名内**;且该行不含任何 §2.2 扫尾关键词族(`契约 §`/`契约 v`/`序列契约`/`序列发射`/`空批`/`取首项`/`结算惰性 drain`/`unified-action-factory`)——design.md 声称「枚举清单可能不全,本扫尾是完备性的机械兜底」,对 changes/ 引用家族该兜底**结构性失效**(裸 design.md 引用无关键词可命中)。
  - 引用族实态合计 = **5 处**,非 4 处;landing 3.1 范围 ③ 写「两处」与 design「4 处全部清理」互相矛盾。
- 后果:按稿施工,L2537 的 changes/ 引用必然存活,与「同族同批清,不留保留申报口子」直接矛盾;实现者在 L664 找不到「design.md §2.4」可删,违反「实现者不再自行判断改不改」的自身承诺。
- 修正方向:①清单补 L2537 并给处置(删裸 design.md 指针、保留「书册卡识别 → 改产 OpenBookcard 动作经执行器发射 → 本访问交回」语义表述);②L664/L984 的形态描述按实态改写(「unified-action-factory 批2b」/「§2.6」);③四文件扫尾关键词族补 `design.md` 裸名;④landing 3.1 范围 ③ 的「两处」改为「全部(实态见 design §2.2,5 处)」。

### F2(中)L1 快速集的「分层命令单一源」指向不存在的路径,验收判据按其声明源不可执行

- 位置:design.md L118(§2.5「分层命令单一源 = CW skill『测试分层』行」);landing.md L13(3.1 完成判据「L1 快速集」)、L26(3.2 完成判据「L1 全量绿」)。
- 直调事实:CW skill(`.dsh/skills/sr-od-currency-war-dev/SKILL.md` 单一源地图「测试分层」行,`references/strategy-work.md` L62 同)写死命令路径 = `sr-od-test/test/sr_od/app/currency_war`;实际目录 = `sr-od-test/test/sr_od/application/currency_war/`(`sr_od/app/` 下仅 `sim_uni`,无 `currency_war`)。按单一源执行,pytest 直接报「file or directory not found」——3.1/3.2 的 L1 判据按其声明的源**无法执行**(报错虽响亮,但判据源失效属依据失真;landing 3.2 文件面 `sr-od-test/test/sr_od/application/currency_war/` 本身是对的,矛盾在命令单一源)。
- 修正方向:landing 3.1/3.2 判据内联正确路径命令(`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow and not legacy_baseline"`)并注明 skill 行待勘误;skill 本体修正不在本批文件面,另行走 skill 反馈。

### F3(中)flow.py `decide_shop_action` 第一处定稿替换文本「决策核发射组织序」与商店核实态不符且无依据标注

- 位置:design.md L101(§2.3 flow.py 顺带收敛第 1 处);落点 = `strategies/impl/flow.py::CwFlowStrategy.decide_shop_action` docstring(L688-701)。
- 直调事实:该决策本体 = `mandate_v1/shop.py::decide_shop_action`,选择机制 = 候选构造 → 优先级序扫描 → 首个可行动作返回(shop.py 自身 docstring L758「选择序 = 既有波批优先级逐帧取首项」+ 函数内分节注释 L1230「---- ③ 选择序逐帧取首项 ----」自证)。商店线**不存在** entry.emit 式「发射组织」(该词在码内的既定所指 = entry.py 三遍编排 + 帧稳定截断发射器)。即:现行句子「选择序 = 既有波批优先级 逐帧取首项」与决策本体自述一致、本身属实;设计未论证其为何属死口径,即把它替换为「选择序 = 决策核发射组织序,逐帧恰取一个动作」——前半句对商店核失真。定稿文本将被逐字落码(landing 3.1 ④「§2.3 定稿文本」),失真随之入库;且 shop.py 本体同族措辞不在四文件面,批后同句一族两态(flow.py 改、shop.py 留)。
- 修正方向:定稿改为如实表述,如「选择序 = 决策本体候选扫描序,逐帧恰取一个动作」;或将 shop.py L758/L1230 两处纳入同批收敛并扩文件面(需同步过 landing 验收 grep 的 diff 域约束)。

### F4(低)「画面转移一律走 OpenShop/StartBattle 终结动作」对终结集实态不穷尽

- 位置:`cw_strategy.py` L133-134(现行未提交 docstring 句);design.md L37(§2.1 定稿句原样保留该句)。
- 直调事实:备战终结集实态 = {StartBattle, OpenShop, **OpenBox**}(`cw_screen_prep.py::CwScreenPrep._terminal_exit` L2334-2354 三专支;OpenBox 终结化 = R7 批2a,L2344-2351「开箱即引入新事实(武装箱选择画面出现…)→ 本访问交回」)。策略发射 OpenBox 同样经动作选择把访问终结并转入武装箱选择画面(OpenBookcard 链同理,但不经决策接口、由画面 op 侧发射)。按「域间转移」读法该句可辩护(开店/出战 = 离开备战域),但按字面「画面转移一律走 OpenShop/StartBattle」与终结集不符,面向第三方策略作者的契约句会被误读。
- 修正方向:定稿改「域间转移(开店/出战)一律走 OpenShop/StartBattle 终结动作」,或加括注「画面内弹窗类转移(OpenBox/书册卡)由外循环分发承接,亦不经 None 表达」。

### F5(低)landing 3.3 完成判据末句「正本与实现一致」无界,存在清单外已知反例使其按字面不可满足

- 位置:landing.md L37(3.3 完成判据末句)。
- 直调事实(均非本批造成、均不在 3.3 关键词域「首项/空批/list[PrepAction]」内):
  - `screens/README.md` §4 动作词表表 L52 把 `ClickSpheres`/`OpenBox`/`OpenTome`/`OpenBookcard` 记为「非终结」,而实码 OpenBoxOp terminal=True(见 F4 的 `_terminal_exit` L2344 专支);§6 终结集总表亦无 OpenBox 行——正本内部 §4 与 §6 及实现三方互相矛盾;
  - `flow/README.md` 卷首 L6「(入口单次 + 逐动作逻辑态直写 + **未建模面保守回退**)」——保守回退分支已随 R9 删除(`prep.md` §4 L45、`op-layer.md` §1.4 L38 均已改为「已删/已废」,唯 flow/README 卷首漏改)。
  - 该判据若按字面全树执行,本批永远无法验收通过;若按隐性范围理解执行,则判据表述失真。
- 修正方向:把末句限定为「本批改动面正本与实现一致」;两处反例补入正本更新清单顺带修,或显式登记为既有债另批收敛。

### F6(低)design §2.3 第 4 条引文与实文有出入(定位无误,引文掉字)

- 位置:design.md L99。
- 直调事实:设计引类 docstring 第二段为「pick 族缺省实现(**基线零改动**,§4.1)」;bridge.py L80-81 实文 =「pick 族缺省实现(基线**本体**零改动,§4.1)」——引文掉「本体」二字。点位唯一、不影响施工,属引文转述精度问题。
- 修正方向:引文对齐实文。

## 零发现面与实际攻击过的面(含直调码点)

1. **审查对象 2:`decide_prep_screen` docstring as-built 逐句核——零发现**。①签名 `-> list[CwAction]`(L121-122)+ 波批遗留定性 = HEAD 版「序列契约 v1,2026-09-03 冻结」(git diff 核对)与 design §1 症状一致;②输入 `session.prep_obs_frame`(`kernel/cw_strategy_session.py` L206;写者 = `cw_screen_prep.py` L977,读者 = bridge L120)、跨步状态 defer 计数(`entry.py` L485-516 挂 `state_of(session).cw4_counters`)与意向状态机(`flow.py` L407-420)同 session ✓;③「两处消费循环同构取首项」(`cw_screen_prep.py` L2029/L2234 调用、L2043/L2248 `actions[0]`)✓;④「列表 = 决策核三遍编排发射组织,相对序决定首项」(`bridge.decide_from_turn` L259-291:emit → route_tag → `truncate_frame_stable`;R197 症1 `_merge_ev_before_frame_end` = entry.py L25-35)✓;⑤「空序列合法交回外循环,stall 兜底归外循环防线」(L2038-2041/L2243-2246)✓;⑥「已退役语义 + `flow/action_exec.md` §2(执行契约,无成败回执 L15)/§3(无 fail-stop/恢复原语 L31,对账 L30)」指针真实且内容吻合 ✓;⑦「帧稳定分类在决策核内仍活」(`classify_frame_stability` L220;调用 bridge L290 + entry L297/L1157 + mandate L1965 = 4 处真实调用,另 mandate 注释提及 L1298-1299/L1753/L1956-1957 三处——design §2.3 理由 2 计数逐一对上)✓;⑧「生命周期四件归流程侧」(`action_key` = `cw_vocab.py` L846;执行失败记忆 = `cw_exec_state.py` L111 `deploy_fail_counts`;stall 门 = flow/README §4;强制出战 = screens/README §6 L133)与 `flow/README.md` §2.2 L82 正本同清单 ✓;⑨「观察帧缺失即抛错」(bridge L120-125 ValueError 实码)✓;⑩注释规范(中文、持久索引、无变更史叙事、无会话局部标识符)✓。唯一瑕疵 = ⑥「画面转移一律走…」句,见 F4。
2. **审查对象 3:strategy-docs/README.md 两处修改——零发现**。①「策略↔流程契约」行(L54):「契约成员 13」与 `flow/README.md` §2.2 L40/L53/L60/L84(保留总成员 13 = 抽象 12 + 工厂 1)及 `cw_strategy.py` 模块头 L12-16 逐一数过一致;「单动作循环」「序列语义为历史注」与 flow/README §2.2 历史注节(L77-82)一致;指向「其 README §2」正确;②19/20 两行(L38-39):两文件均存在(`19_reinforce_channel_and_survival_discount.md`/`20_large_balance_must_spend.md` 直读头部,一句话概括与篇名/术语相符)、三列结构与表头一致、按编号序落在 18 与 22 之间;文尾孤立行已删净(文件止于 §5 纪律列表)。缺 14/15/16/17/21 行系已申报范围外,不计。
3. **design §1 症状/归层**:消费端全集 = 全 src grep `decide_prep_screen` 仅两处生产调用(sim/replay/tools 零消费);~L2029/~L2234 行号锚精确;2026-09-03 冻结(HEAD docstring)/2026-09-06 落码(`flow/README.md` L6)双向实证;表示层归层成立。
4. **design §2.1**:契约成员数 13(逐成员数过);「观察帧缺失即抛错」「生命周期归流程侧」原文保留 ✓;None 三点依据——⑥ 无动作 ⇒ 出战(entry.py L441/L936-944 实码)、可达空边 = `truncate_frame_stable` 首位 SellBench/DeployMove 引用失效槽位截空(L309-324,R196 症5 L254 属活防线)、unknown 首位边不可达(四分类 1+11+4+1 = 17 类全覆盖;备战词表 18 类 = 17 + OpenBookcard,后者系画面 op 侧发射 = `cw_screen_prep.py` L2537-2539 直构,不经决策核;entry.py 头注「18 类」计数漂移属实、按申报不动)、B4(基类 `create_state` 缺省 None = cw_strategy.py L104-115)、出战标准 = `strategy-docs/26_battle_settlement.md`(L3/L8 实读)、op-layer §1.1 L21 分域句/§1.3 守卫断言/§1.4 恒可用终结逐句对上。
5. **design §2.2**:码块与实码逐行吻合(try/except 文案、F3 现行 status/warning「策略输出非 list[CwAction](F3)」L2037/L2242、空批 detail 文案与 wait=1.0、`actions: list = []` 预声明 L2016/L2220、「契约 §4」注释 L2039/L2244、「契约 §2:参数非法交回留证」L2044/L2249、头注块 L2004-2011 跨行句与「逻辑态未建模…保守回退」死口径(L2112-2113/L2312-2313 同函数自证分支已删)、lifecycle docstring 终结出口枚举 L2211-2212 三删除目标全在码);新 None 分支与空批分支逐义等价(round_success + wait=1.0);B4 谓词对旧 list 形状(空否均 fail)推演成立;定稿文本对 3.1 八关键词逐词过 = 零碰撞。
6. **design §2.3**:bridge 六处死引用(L3/L13-14/L77/L90-92/L109/L114-115/L117)逐处实读在码;L109「双重死引用」核实(`flow/action_exec.md` §1 实为「动作词表与注册表」节;契约工作副本灭失自证 = entry.py L17-18);扫尾关键词族对四文件的命中全覆盖核查(唯一漏网 = L2537,见 F1;flow.py L423「结算惰性 drain 已删除」系扫尾将命中、处置应为保留申报的如实历史注,不构成缺口);`_consume_prep_direction_frame`/`_consume_shop_direction_frame` 实存(flow.py L425/L450)且 drain 已删自证(L422-423/L430)。
7. **design §2.4**:`flow/README.md` §2.3 L91 sim 消费面注记、op-layer §4 L153 次门表述、`tools/cw/replay_to_md.py` 头注(离线渲染 decisions 记录流,零策略 import)逐一对上;`telemetry/journal_query.py` 存在。
8. **design §2.5/§2.6**:sr-od-test 全仓 `decide_prep_screen` 仅 `test_cw_p2_blood_band.py` L213-217 桩子类(`*a, **kw`,形状免疫);`空批`/`取首项`/`actions[0]`/`list[CwAction]`/`策略输出非` 在 sr-od-test 与 tools/ 零命中;计数键族 `emitter_*`/`deploy_emit_*`/`deploy_exec_*`/`t1_interest_prep_emit`(mandate.py L1368)/`wanted_leg_*`/`m1p_*`/`sphere_defer_*` 全部实码在键,`prep_box`/`prep_tome`/`prep_spheres` 系 `Emitted` 第三参 reason 路由标签(entry.py L462/L464/L498/L513)非计数键——「勿 grep」提示属实;ruff select 含 F(F841 生效,pyproject L60-70)。
9. **landing 3.1-3.3 阶段结构与验收可执行性**:七件齐、依赖/优先级合规、末阶段 = 正本更新合规;3.1 验收 grep 的 diff 域定义、`decide_from_turn` 豁免申报(bridge L262 未改行)成立;3.3 闭域检查按「首项 / 空批 / list[PrepAction]」全树独立重跑——全部命中归属清单 #1-#15 或豁免表(`flow/README.md` L77/L81 历史注节、changes/ 全目录、`proofs/validations/P51_V3_REBUILD.md` L391 直读确认系拟合器标签规则「R31-2 首项=1」、豁免正当);PrepAction 裸名已知位 = projection_contract.md §4.1(L89,§4.1 节锚实存 L83)与 action_exec.md §1(L9),其余命中均为 `PrepActionExecutor` 合法名——三关键词域内**完备且可执行**;缺口在关键词域之外(F1/F5)。
10. **正本更新清单 15 条逐条直调**:flow/README L17-18(「决策取│首项」跨行拆分属实,L18 行首「首项」单字面可命中且条目已预告归属)/L23/L64、projection_contract L89-90、action_exec L28/L9、op-layer L14/L21、prep.md L15/L32/L53、screens/README L130、22_prep_screen L8/L28、action-logic-state L163、prep-executor-actions L13、02_mandate_layer L82(「永不返回 None」+「逐帧取最优首项」两半句都在)——引文逐字存在、行号无漂移、改写口径与 design §2.1 一致;条目 #16 锁指针复验与 3.2 的「先指向、3.3 复验」时序自洽(3.1-3.3 间正本暂滞后于实现,由条目自身申报管理,不构成缺口)。
11. **规范遵循核(iteration-design.md / AGENTS.md)**:README 四节模板合规、进度只在 README;design §0-§3 齐、单文档方案合法、依据就地标注覆盖率高;landing 三阶段七件齐 + 正本更新清单合规;design/landing 无过程叙事;README 引 attack.md-attack6.md 系迭代内工件合法引用;「用户 2026-09-15 策略基座规范核查」以日期+事件语义描述作裁定指针,合规。
12. **治本核**:表示层归层成立(消费语义已迁移、表示未跟,双向实证);备选 A(契约面收口、核内 list 保留)有活机制依据(首项选择序 4 调用点 + `_merge_ev_before_frame_end` + M7 回排),非症状补丁;备选 B/C/D 弃因逐条对权威源(op-layer §1.1 分域句、op-layer §1.4)核验无空洞;None 通道、行为零变化、第三方兼容面(B4 封闭集 {mandate_v1} = flow/README §2.1 L47、响亮暴露不做垫片)申报自洽。

## 已知范围外遵从声明

未重复计列:strategy-docs/README §2 分篇表缺 14/15/16/17/21 五行(既有缺口,已申报);entry.py 头注「18 类」计数漂移与决策核内灭失契约工作副本引用族(design §1/§2.1 已申报归决策核行为变更大批,本批核内零改动边界不含)。
