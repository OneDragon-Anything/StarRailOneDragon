# attack4 —— 无前提对抗审查(2026-09-15-prep-single-action-contract)

> 审查对象:①README.md/design.md/landing.md(迭代设计三件套);②工作区未提交的 `strategies/impl/cw_strategy.py::decide_prep_screen` docstring;③工作区未提交的 `strategy-docs/README.md`(契约行改表述 + 19/20 两行归位)。未读同目录 attack.md/attack2.md/attack3.md 作对象(既有审查工件;三份文件存在于目录、设计稿已含对其的响应痕迹,本报告发现独立直调得出)。
> 结论:**发现 6 条(中 1 / 低 5),无高危**。三件套的码点主张、引文、计数、行号锚经直调全部属实(见 §2 攻击面清单);发现集中在验收判据可执行性与索引完备性。

## 1. 发现清单

### F1(中)3.1 验收 grep「作用于本批四文件 diff 行,要求零命中」在两种自然读法下均不可满足
- 位置:`landing.md` L14(3.1 阶段「验收凭据形式」);关联 `design.md` §2.3(决策核 list 保留)。
- 攻击过程:关键词集含 `list[CwAction]` 等死口径措辞,「diff 行」未定义语义,逐一验两种读法:
  - 读法 A(diff 全行,含被删 `-` 行):被删行**按构造必含关键词**——本批收敛的正是这些措辞(`cw_strategy.py` L122-133 现行 docstring 与签名即含 `list[CwAction]`/`序列契约`/`取首项`/`空批`;`flow.py` L699 含 `结算惰性 drain`;`bridge.py` L3/L90-92/L109/L114-115/L117 含 `§4.1`/`序列契约`/`契约 v`/`契约 §`/`结算惰性 drain`)。零命中不可能。
  - 读法 B(改后四文件全文):`bridge.py::decide_from_turn` 签名 L262 `) -> list[CwAction]:` 被**设计刻意保留**(§2.3「决策核调用不变(`decide_from_turn`…仍返回 list)」+ §3 备选 A「决策核内保留 list」),关键词 `list[CwAction]` 必命中。零命中同样不可能。
  - 唯一可执行读法 = 仅 `+` 行/本批改写行(即「防旧口径关键词回潮」的本意),判据未写明。
- 后果:实现者或验收者按字面执行 `git diff | grep` 或改后全文 grep,均得到必然红的结果,要么误判不通过、要么自行 reinterpret(绕过判据)。
- 修正方向:改述为「作用于本批四文件 diff 的新增行(+ 行)/本批改写行,要求零命中」,并在判据边申报豁免:「`decide_from_turn` 签名 `list[CwAction]` = 决策核内 list 发射组织契约(§2.3/备选 A),合法保留」。

### F2(低)清单 #1 括注「机械 grep 不可见」与 3.3 现行关键词集矛盾(理由过期)
- 位置:`landing.md` L43(清单 #1);关联 3.3 关键词集(L36,「首项」单字面)。
- 攻击过程:直调 grep「首项」对 `flow/README.md` 全树——L18 行首即「首项→期望态计算→执行…」,**单字面 grep 必命中**。括注「『决策取/首项』被框图换行拆成两行,机械 grep 不可见」只在旧关键词「取首项」(词组)时代成立;关键词改为单字面后该理由失真。人工复核指令本身无害(保留合理),但过期理由会诱导实现者把 L18 的 grep 命中误判为「清单外新发现」而非本条目处置。
- 修正方向:括注改为「词组级 grep 不可见(跨行拆分);单字面『首项』可命中 L18,该命中按本条目处置」。

### F3(低)基类 docstring 改写无定稿文本,3.1 八关键词规避约束未对其申明
- 位置:`design.md` §2.1(只给语义未给定稿)/`landing.md` L5(3.1 ①「docstring 按新契约改写(§2.1 语义)」)。
- 攻击过程:直调现行 `cw_strategy.py` L122-133——工作区 docstring 自身含 `取首项`/`空批`/`序列契约`/`list[CwAction]` 四个验收关键词。同批对 §2.2 码块与 bridge docstring 已按「定稿关键句防关键词回潮」处理(§2.2 码块注释、§2.3 定稿句均已规避),唯独基类 docstring 无定稿文本、也无「改写须规避 3.1 关键词集」的显式义务;实现者若在改写中保留任何现行措辞(如「波批序列契约遗留」的历史注句),验收 grep 即红并落入 F1 同款困惑。
- 修正方向:§2.1 或 landing 3.1 ① 补基类 docstring 定稿关键句,或明示「改写后不得含 3.1 关键词集任一词」。

### F4(低)§2.2 改写遗留 `actions: list = []` 死预声明,收敛清单未点名(ruff 门内必红)
- 位置:`design.md` §2.2(改写码块与死口径收敛清单);实码 `cw_screen_prep.py` L2016(主循环)/L2220(`lifecycle_decision_cycle`)。
- 攻击过程:两处循环体外的预声明 `actions: list = []` 在现行码里被循环内 `actions = decide_prep_screen(...)` 复用;§2.2 改写把变量定名为 `result` 且完成判据要求「代码形状与 §2.2 码块一致」→ 预声明成「赋值后永不使用」。项目 ruff `select` 含 `F`(pyflakes,F841)(`pyproject.toml` L60-63),通用工程门 `ruff check` 必红;§2.2 死口径收敛清单与「其余段零变化(枚举)」均未含该行,实现者需自行拍板删除。
- 修正方向:§2.2 收敛清单补一条「两处循环外 `actions: list = []` 预声明随改写删除」。

### F5(低)迭代 README 进度行只串 attack.md,同目录 attack2/attack3 索引断链
- 位置:`changes/2026-09-15-prep-single-action-contract/README.md` L13。
- 攻击过程:直调目录清单——attack.md/attack2.md/attack3.md 三份并存,README 进度行「报告=[attack.md](attack.md)」只链第一份;iteration-design.md §4 规定 README 职责 = 「串文档、记进度」,模板单链接形态与多报告现实脱节,后两轮报告从索引不可达。
- 修正方向:进度行列全三份(或链最新收敛轮 + 其余并列),如「报告=[attack.md](attack.md)/[attack2.md](attack2.md)/[attack3.md](attack3.md)」。

### F6(低)strategy-docs/README.md 分篇表缺现存 14/15/16/17/21 五篇(既有缺口,非本批引入)
- 位置:`strategy-docs/README.md` §2 分篇表(L29-45)。
- 攻击过程:直调目录 glob——`14_p1_consume_arms.md`/`15_observation_multisource_arbitration.md`/`16_evaluation_tables_reassessment.md`/`17_stall_form_spend_authority.md`/`21_opening_window_and_tool_consume.md` 五篇在库,两张表(总纲 + 分篇)均无行;文尾注(L47)只交代 03/05/06/09 删除,未交代这五篇的收编口径。19/20 归位后「唯一现行入口」的索引覆盖缺口仍在。
- 修正方向:补五行「一句话」行,或在 §2 显式申报本表收编范围(如「观测/评估类篇不按决策点分篇,索引见 X」)。

## 2. 实际攻击过的面(直调码点/文档逐列)

### 对象①:迭代设计三件套
- **§1/§2.1 码点主张**:`decide_prep_screen` 签名返回 list(`cw_strategy.py` L120-122)✓;消费端两处、~L2029/~L2234 行号锚精确(`cw_screen_prep.py` L2029/L2234)✓;每帧 `actions[0]` 两处 ✓;空批分支 `round_success('空批(本帧无动作),交回外循环重观察', wait=1.0)` 文案与申报一致 ✓;契约成员数 13(12 abstract + create_state 工厂,`cw_strategy.py` L97-115 逐一数过;单一源 `flow/README.md` §2.2 L40/L84 同数)✓;「观察帧缺失即抛错」「生命周期机制归流程侧」两条现行纪律原文(flow/README §2.2 L64/L82)✓;B4 注册面封闭集 = {mandate_v1}(flow/README §2.1 L47)✓;`create_state` 缺省 None(L104-115)✓。
- **§2.1 依据 2(None 通道)**:`entry.py`「⑥ 无动作 ⇒ 出战」段 L936-944(`if not out: append(StartBattle)`,常态无空)✓;可达空边 = `truncate_frame_stable` 条件续复检首位 `SellBench`/`DeployMove` 引用失效槽位截空(L309-324 fail 分支先 `_cut` 后 append,首位即空)✓;unknown 首位边不可达——四分类表 11+1+4+1 = 17 类,与 entry.py 可发射 import 集(L77-96)恰合 ✓;备战词表全集 18 类(`cw_vocab.py::CW_ACTION_TYPES` 21 类去商店域 4 类 + SwapDeploy 不在白名单,= 18)含 OpenBookcard 画面 op 侧发射(open-bookcard.md 发射位 = `_clear_prep_cards`)✓;entry.py 头注「18 类逐类表」L15 存在、与 17 分类数的漂移定性属实 ✓。
- **§2.3 mandate_v1 边界**:bridge docstring 四处死引用逐一在码(L109「契约 v1/v2 + action_exec §1」/L114-115「契约 §3.2+§3.3」/L117「结算惰性 drain」/L3 模块头裸「§4.1」+L90-92 DESCRIPTION「序列契约 v2」)✓;「实码只调帧代次消费」——`decide_prep_screen` 体 L127 仅 `_consume_prep_direction_frame`,`flow.py::_consume_prep_direction_frame` docstring L430 自证 drain 已删 ✓;「帧稳定分类/截断包内 4 处真实调用」——bridge L290(truncate)+ entry L297/L1157(classify)+ mandate L1965(classify,M7 回排)✓;注释提及 3 处——mandate L1298-1299(凑息卖接线位)/L1752-1753(M1″ 影子面不辖)/L1951-1957(M7 回排就地说明)✓;`_merge_ev_before_frame_end` 在码(entry L1140,R197 症1 语义 L25-35)✓;新 docstring 定稿句与 3.1 关键词集零碰撞(逐词过)✓。
- **§2.2 消费端改写**:现行段(decide→F3 形状校验→空批分支→取首项)与码块 before 逐行吻合(L2028-2043/L2233-2248 两处同构)✓;死口径五处全在码(L2039/L2244「契约 §4」、L2044/L2249「契约 §2」、L2211 lifecycle docstring「终结出口语义 = 空批/…」、L2007-2008 头注「逐帧取首项」、L2010-2011「逻辑态未建模的动作同判保守回退」)✓;新码块 try/except 保留与异常文案、`wait=1.0` 保留、B4 谓词(非 None 且非 CwAction,旧 list 空否均 fail)行为推演成立 ✓。
- **§2.4 sim/回放零影响**:flow/README §2.3 L91 sim 消费面注记 ✓;全 src grep `decide_prep_screen` 生产调用仅 cw_screen_prep 两处 ✓;op-layer §4 L153「cw_replay --diff 只重放商店决策面」✓;`tools/cw/replay_to_md.py` 零策略 import、按 decisions 帧渲染(`_op_kind` 返回 prep/shop/supply 三类)✓。
- **§2.5 测试锁**:sr-od-test 全仓 grep `decide_prep_screen` 仅 `test_cw_p2_blood_band.py` L215-217 桩子类(`*a, **kw`,raise NotImplementedError,不触达)✓;「空批/list[CwAction]/策略输出非」测试仓与 tools/ 零命中 ✓。
- **§2.6 验证**:计数键族逐一在码——`emitter_*`(entry L293/L299/L311/L319)、`deploy_emit_*`(mandate L2061-2063)、`deploy_exec_*`(cw_screen_deploy L143-145,且 L136 自证写入 `cw4_counters`)、`t1_interest_prep_emit`(mandate L1368)、`wanted_leg_*`(mandate L1015/L1038/L1045)、`m1p_*`(mandate L1801-1881)、`sphere_defer_*`(entry L485-516)✓;`prep_box/prep_tome/prep_spheres` 系 `Emitted.reason` 路由标签非计数键(entry L462/L464/L498/L513)✓;`telemetry/journal_query.py` 在码(src/.../telemetry/journal_query.py)✓;MCP 重启引用(AGENTS「MCP」节)属实 ✓。
- **正本更新清单 15 条锚点句逐条直调**:#1 flow/README L17-18(「决策取/首项」跨行拆分属实)+ L23 ✓;#2 L64 引文逐字 ✓;#3 projection_contract L89「族 B PrepAction 列表」/L90「逐帧取首项」逐字 ✓;#4 action_exec L28 ✓;#5 op-layer L14 ✓;#6 op-layer L21 分域句逐字 ✓;#7 prep.md L15 ✓;#8 prep.md L32 ✓;#9 prep.md L53 ✓;#10 screens/README L130 ✓;#11 22_prep_screen L8/L28 ✓;#12 action_exec L9 ✓;#13 action-logic-state L163 ✓;#14 prep-executor-actions L13 ✓;#15 02_mandate_layer L82(「策略器 = 全函数…永不返回 None」+「逐帧取最优首项」)✓。
- **3.3 闭域检查完备性(独立全树重跑)**:「首项」63 命中 → 清单 #1/2/3/4/5/7/8/11/13/14/15 全覆盖 + 豁免(P51 L391 属实——「R31-2 首项=1」系拟合器标签序位;另一迭代 `changes/2026-09-14-unified-action-factory/design.md` L362 归「changes/ 全目录」豁免);「空批」→ flow/README L77/L81(历史注节豁免正当)+ #6/#8/#9/#10 全覆盖;「list[PrepAction]」→ #2/#7 全覆盖;PrepAction 裸名人工位 = projection_contract §4.1(#3)+ action_exec §1(#12),其余命中全为 `PrepActionExecutor` 合法执行器名 ✓。豁免表完备且必要。
- **三核(核一/核三)**:§1 归层表示层成立(消费语义 2026-09-06 落码、签名 list 未跟,双向实证);§2 修根 = 契约面形状收口,核内 list 保留有活机制依据(首项选择序 4 调用点);备选 A-D 弃因论证直调无空洞(D 与 op-layer §1.1 分域表述核验一致);None 等价推演含边界(今日 None 返回值落空批成功分支、明日落 None 分支,同 `round_success` 交回,逐义等价)。
- **规范遵循(核二)**:四节齐(README 文档+进度/design §0-§2+取舍/landing 阶段+清单)✓;三阶段小节七件齐 ✓;末阶段 = 正本更新 + 清单清零判据 ✓;依据就地标注(本报告逐条直调即其验证)✓;changes/ 引用寿命(3.2 锁指针指 flow/README §2.2 非 changes/)✓;无过程叙事措辞 ✓。

### 对象②:docstring(cw_strategy.py 工作区未提交版,L123-144)
- 十句 as-built 主张逐句核:**零发现**——①list 遗留定性 + 现行消费取首项(签名 L122;消费端两处)✓;②输入 `session.prep_obs_frame`(session L206)+ defer 计数/意向状态机挂 strategy_state→session ✓;③三遍编排发射组织、尾部不消费(emit→truncate→`[0]`)✓;④空序列合法 + stall 兜底归外循环(与消费端 L2040 注释同口径)✓;⑤画面转移走 OpenShop/StartBattle 终结(prep.md §5:StartBattle 唯一完成态/OpenShop 备战环终结)✓;⑥已退役语义 + `flow/action_exec.md` §2(机械执行无成败回执)/§3(无 fail-stop/恢复原语)指针真实且内容吻合 ✓;⑦帧稳定分类在决策核内仍活(entry 实码)✓;⑧生命周期四件(action_key/执行失败记忆[=flow/README L82 deploy_fail_counts 族]/stall 门/强制出战)与正本同清单 ✓;⑨观察帧缺失抛错(bridge L120-125 ValueError 实码)✓;⑩注释规范:中文、引用全为持久索引(文件:节/符号名)、无变更史叙事(「迁移后」系现状成因非勘误过程)✓。

### 对象③:strategy-docs/README.md 工作区未提交版
- 契约行(L54):「四身份分离、契约成员 13、单动作循环;序列语义为历史注」对 flow/README §2 现行事实逐项吻合(13 = flow/README L40;单动作循环 L64-65;历史注 L77)✓;旧「17 接口」确为失真计数,改后准确 ✓。「flow/ 七篇」计数直调 glob 恰 7 个 .md ✓。
- 19/20 归位:两文件在库且行句为合理一句话(20 号篇 L6/L54 自有「旱期金出口分层」术语,行句有据)✓;表内格式合法、位次(18→19→20→22)正确 ✓;文尾两孤立行已删除(全文读毕确认)✓。缺口见 F6(既有)。

## 3. 裁决

- 设计本体(接口语义/None 通道论证/边界适配/行为零变化证明面/sim 不可见声明)直调后**无实质缺陷**,可支撑实现。
- F1 为唯一中危:验收判据按字面不可执行,落码批验收时会卡;修一句话 + 一条豁免申报即可解。
- F2-F6 均为低危文字/索引完备性问题,可随 F1 一并在「对抗审中」状态收口,不动摇设计。
