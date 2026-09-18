# attack10 —— 策略器决策输入统一 对抗审查报告(r10)

> 审查日期 2026-09-16。无前提独立审查:攻击对象 = 本目录 design.md / landing.md / README.md;判据源自取(迭代文档规范、策略层宪法、fields.md、flow/ 契约、正本树全族、src 与 sr-od-test 代码真值、三在飞迭代、AGENTS.md、strategy-work §6)。全部数值/口径/引文/码点直调复核,未采信任何前轮报告。

## 发现清单(共 10 条:blocker 0 / major 3 / minor 7)

### [F1] major —— 路由挂点插入点断言与 `cw_loop.loop()` 现有行序冲突,「每轮必经/无绕行」在可落位插入点上不成立

- **位置**:design.md §2.3(「路由点陈旧清点」「绕行路径核查」);landing.md 3.1(范围「插入点 = 画面识别产出后、`_dispatch_identity_screen` 调用前」;完成判据「未识别轮剧本断言……钉死插入点每轮必经的回归锁」)
- **发现**:design 断言「挂点钉在『识别产出后、任何分支分发与早退判断之前』的每轮必经位——stop_at_prep 早退与未知兜底停机均发生在该位之后」。代码事实(直调核实):`operations/cw_loop.py` 的 `loop()` 中,`screen = self.last_screenshot`(L1740)→ **stop_at_prep 早退**(L1754-1756,`get_in_match_screen_name(...) in PREP_DIRECT_EXIT_SCREENS` 即 return)→ 阶段一识别 `_match_name = get_match_screen_name(...)`(L1818)→ 分发(L1821)。即 stop_at_prep 早退在阶段一识别/分发**之前**。由此两种落位:
  - (a) 挂点复用 `_match_name`(钉 L1818 与 L1821 之间)——字面满足「`_dispatch_identity_screen` 调用前」,但 stop_at_prep 早退轮在该位之前已 return,**绕行面真实存在**,「每轮无条件清点、无绕行面」为假;landing 3.1 的字面插入点即此位,照 landing 立任务必落此处。
  - (b) 挂点钉早退之前——该位置上没有任何已产出的画面识别结果可复用(早退判断用的是另一识别函数 `get_in_match_screen_name`,阶段一用的是 `get_match_screen_name(CW_DISPATCH_SCREENS)` 子集),挂点须自跑一次全集识别(热路径成本翻倍,设计未申报),或重构 loop 行序(超「单一挂点」申报面)。
  - 后果评估:早退轮绕行的影响 = 该轮(备战态、无 decide 消费)不清槽,审计面残留、下一局新容器自然清零——行为面近乎无害,但本批是行为零变化批,其等价性论证与 3.1 回归锁建立在该断言上,断言失实须修。
- **修正方向**:三选一并同步 design/landing——①钉 (a) 位并如实申报「stop_at_prep 早退轮绕行(该轮无 decide 消费、绕行无害,已离开属屏的槽由下轮补清语义兜底)」,修订「无绕行面」表述,3.1 判据补 stop_at_prep 早退轮的清点行为断言;②钉 (b) 位并申报挂点自跑识别的成本与识别函数选型;③把 stop_at_prep 早退判断挪到挂点之后(申报 loop 结构改动面)。推荐 ①,代价最小且诚实。

### [F2] major —— §2.2-c「刷新重决策腿 = 同访问内二次『读得=覆盖』」与 supply(及 invest)现状刷新链机制不符,存在引入行为变化的实现歧义

- **位置**:design.md §2.2-c(契约 c「刷新重决策腿」);landing.md 3.4(「encounter/supply 刷新重决策腿 = 重读产物覆盖写槽后再 decide(既有『无条件重读』链原样,§2.2-c)」)
- **发现**:三屏刷新链机制不同构(直调核实):
  - encounter = **同 handle 内**重读重决策(`cw_screen_encounter.py` L331-337/L461-467:`_emit_refresh_click` → `_try_refresh` 重读 → 同轮带 `refresh_used=True` 再 decide);
  - supply = 刷新分支点击后**直接 return**(`cw_screen_supply_node.py` L302-310),重决策靠 round_retry 重入下一轮(observe 门复检 → `_do_action` 重跑 → 重新 `read_supply_options` → 以容器累计计数派生 `refresh_used=True` 再 decide);且 supply 的选项读取本就发生在决策段内而非观察段(`SupplyObservation` 只携带 screen 帧,L131);
  - invest = 逐卡刷新为终结动作、点钮后本访问即交回,重入后重观察重决策(`cw_screen_invest_strategy.py` L422-424 注记、screens/invest_strategy.md L3)。
  design §2.2-c 与 landing 3.4 将 encounter/supply 并列表述为「同访问内二次读得=覆盖」——「同访问内二次」仅对 encounter 成立;supply 无此环节。实现者面临未被回答的语义选择:按文档照 encounter 模式在 supply 加「同访问内重读重决策」= **行为变化**(现状:刷新轮 return、选卡发生在下一轮重入);按现状保留重入模式则「同访问内二次」条款对 supply 落空,且「grep 调用点数 = 写槽点数」判据在重入轮语义下(写槽点在重入轮的决策段)与调用点的对应关系含糊。
- **修正方向**:§2.2-c 按屏分形态申报:encounter = 访问内二次重读覆盖;supply/invest = 重入轮次的重读覆盖(重入轮 observe/决策段产物写槽后再 decide,现状链原样);landing 3.4 同步,并把「每次决策恰以当次观察产物为单源」的判据口径明确为「每 decide 调用点前置恰一次当次访问内写槽(含重入轮)」。

### [F3] major —— `encounter_refreshed_in_visit` 写 False 点失败语义未定死,与写 True 点的对称缺口

- **位置**:design.md §2.1 纪律 4(「写 True 点 = 刷新发射分支内、重决策发起前的同步直写——禁挂吞异常的 best-effort 钩子……禁降级为『失败窗读 False』」;「写 False 点 = 各决策路径每次进入的首调前置段」)
- **发现**:设计对写 True 点定死了失败语义(同步直写、异常上抛、显式禁止 best-effort 及「失败窗读 False」——理由 = 基线核刷新枝 idx 分叉禁类),对写 False 点只定了位置,未定失败语义。写 False 失败场景:上一访问刷新后 True 残留(跨 handle 窗在册)+ 本访问首调前置复位失败 → 首调读 True → 刷新建议枝不可达 → 与现状首调 False 产生 refresh 旗标/reason/idx 分歧——**与设计自己为写 True 点列的禁类同型**(基线核 `cw_events.decide_encounter` L670 `if not refresh_used and ...` 两枝 idx 可分叉)。「实现者遇到写 False 失败怎么办」在设计内无答案(best-effort?上抛?静默跳过?),违「实现者无需再设计」。
- **修正方向**:写 False 点与写 True 点同型定死(同步直写、失败异常上抛;`cw_match` None 守卫跳过条款同样覆盖 False 写),并在字段注释申报中补「复位失败即响亮暴露,禁降级」一句;或显式论证 False 失败的差异后果并给出处置。

### [F4] minor —— 正本更新清单预登记面漏列四处命中(普查机制兜底,清单精度不足)

- **位置**:landing.md「正本更新清单」节
- **发现**(全词表普查核实,范围 = 正本树排除 sources/changes/proofs):
  1. `flow/session.md` L14「后契约形状 = 每局冷建 2 + 分画面决策入口 11」计数词句——session.md 清单行只列 prep_obs 退役/B4 收缩,未含计数词;
  2. `strategy-docs/README.md` L60「契约成员 13」句——清单行只列「13 号篇篇目行九接口」;
  3. `screens/expert_invite.md` L12、`screens/fortune.md` L11 的「(未接)picked 族九接口」句——两篇整个不在清单;
  4. 「九接口」在正本树存在两种书面口径:flow/README §2.2 与 13 号篇 = 9 含 decide_box_card(九名列表在册);screens/README.md L107「pick 族九接口 + decide_box_card」与 25 号篇表格行 = 九接口不含 box_card 的旧口径——拆分后两种口径计数同为 10,但书面修订形式不同,清单未申报双口径,末阶段归类时可能漏改其一。
- **修正方向**:把 1–3 补进预登记行(清单自declared 非封闭集、普查兜底在案,故仅 minor);第 4 点在 25 号篇/screens README 的更新动作中显式归一口径(建议统一为 flow/README 的含 box_card 口径)。

### [F5] minor —— landing 3.4 判据豁免条款引用不存在的「kernel 纯函数同名」

- **位置**:landing.md 3.4 完成判据(「`decide_invest(` 契约调用全仓归零(kernel 纯函数同名签名与策略入口体内对 kernel 的委托调用除外)」)
- **发现**:`kernel/cw_events.py` 无 `decide_invest` 同名函数(invest 的 kernel 判据 = `decide_event`,签名 `(options, config, gs, ...)`);有 kernel 同名的是 decide_supply/decide_encounter/decide_planner。「decide_invest( 的 kernel 同名豁免」对象不存在;该词形的合法残留仅注释锚(如 `cw_investments.py` L975-977)与归零后的符号改名锚。
- **修正方向**:豁免语改为「(策略入口体内对 `cw_events.decide_event` 的委托调用及注释锚除外)」或直接删豁免语——归零判据本体不受影响。

### [F6] minor —— landing 3.2 的「契约计数句随签名批同步改写」为空转申报

- **位置**:landing.md 3.2 范围(「`cw_strategy.py` 模块头/类 docstring 契约计数句随签名批同步改写(计数词不进符号 grep,人工复核项)」)
- **发现**:3.2 仅切 `decide_prep_screen` 签名,契约计数(决策入口 11/抽象 12/总成员 13/pick 族 9)在该阶段**不变**,计数句无可改内容;计数真正变化发生在 3.4(invest 拆分,11→12/12→13/13→14/9→10)。该行实义应为 prep 契约描述改指(ABC docstring「输入 = `session.prep_obs_frame`」等),「计数句」用词误导实现者找不存在的改写对象。
- **修正方向**:3.2 该项改口径为「prep 入口契约描述/docstring 改指(含模块头 `session.prep_obs_frame` 表述)」;计数句改写明确归 3.4(该阶段已有同类项,不缺)。

### [F7] minor —— §2.2-f 依据标注错位:「谁产生/谁消费」的判据源不在 fields.md §8.8

- **位置**:design.md §2.2 配套契约 f(「全部带『谁产生/谁消费』归属申报与坐标系注释(fields.md §8.8 治理面同款)」)
- **发现**:fields.md §8.8 的治理判据是「字段准入四问」(①谁消费②影响什么决策③能否算出④识别质量元数据);「谁产生/谁消费」四问(①谁产生②谁消费③生命周期④自然宿主)的正本宿主 = `flow/session.md` §2 归类判据。引用锚存在但内容不对应,属「值对标签错」轻度形态。
- **修正方向**:依据改为「flow/session.md §2 归类判据 + fields.md §8.8 字段准入四问」双锚,或按 §8.8 四问补齐 8 新槽 + 新字段的逐项答案。

### [F8] minor —— README 定稿门槛表述与对抗纪律字面冲突

- **位置**:README.md 进度节(「复审待零发现轮或仅 minor 轮即提请定稿」)
- **发现**:对抗纪律出处(strategy-work §6)明文「发现→修→再攻(新干净上下文),直至零发现」「每批修改……零发现才收口」——minor 亦是发现。「仅 minor 轮即提请定稿」是对硬门的字面软化;若属用户已接受的操作口径,应在文中给裁定指针,否则按纪律执行。
- **修正方向**:收紧为「零发现轮提请定稿」,或补「minor 处置由用户裁定豁免」指针。

### [F9] minor —— shop 豁免行的映射结构形态未定死;`_PAYLOAD_DOMAINS` 扩展对 `leave_screen` 守卫面的连带变化未申报

- **位置**:design.md §2.3(「shop 保留在映射结构内……标记为路由清点豁免(挂点跳过它)」;「属屏映射单一源 = 扩展既有 `_PAYLOAD_DOMAINS`……为槽 → 属屏结构」)
- **发现**:①「映射内标记豁免」的具体承载未定(属屏值特殊化/伴生豁免集/挂点侧硬编码跳过),实现者有自由度;②`leave_screen` 现守卫 = `name not in _PAYLOAD_DOMAINS` 抛 ValueError(`cw_game_state.py` L3158),映射扩为十槽属屏结构后 8 个新 opts 槽自动成为 `leave_screen` 合法域——守卫面放宽是本批连带效果,设计未申报(顺带:路由挂点清点的写入口形态——复用 `leave_screen` 及其 sig 形态 family='obs'/actor='CwLoop'(在册)/evidence='left_screen'——也未明说,虽为唯一合理路径)。
- **修正方向**:钉死映射结构(如 `dict[str, str]` + 独立 `_ROUTING_EXEMPT` 冻结集)与挂点写入口(经 `leave_screen`,sig 口径写出);在 §2.3 补一句「扩展后 leave_screen 合法域 = 十槽,守卫放宽申报」。

### [F10] minor —— §2.5 迁移契约表 planner/invest 防御路径行「签名随改」无对象

- **位置**:design.md §2.5(`cw_screen_planner.py` 防御路径行、invest 两文件防御路径行)
- **发现**:两处局外防御路径直调 kernel 纯函数(`cw_screen_planner.py` L212 直调 `decide_planner`、`cw_screen_invest_strategy.py` L417/L418 直调 `decide_event`),kernel 签名本批零改动(§2.2-d)——「签名随改」无对象;行实义 = 防御路径保持 kernel 直调、不写槽不读槽(无 match 无 session 无容器宿主)。
- **修正方向**:两行「改动」列改为「kernel 直调保持(签名不动),不涉槽;该文件内 match 分支的签名切换由 pick 族行辖」。

## 零发现面(实际攻击过且未发现问题的面)

- **现状症状断言对码**(design §1.1 全部符号锚):契约 11 入口三形状、pick 族 9 参形、`decide_invest` kind 分叉、supply/encounter 旗标语义(supply=容器累计派生/闸命中静默落选卡支 `cw_screen_supply_node.py` L230-233、encounter=首调缺省 False/重决策 True/重入清标志重走 `cw_screen_encounter.py` L254-264/L304/L336/L439/L466)、`gs.shop` 活写端在产/encounter/supply 活写端缺位(live `leave_screen` 仅两处 shop:`cw_observation.py` L2618 prep 锚 miss 分支、`cw_game_state.py` L2033 CloseShop 逻辑腿;encounter/supply 清点仅在 sim 合成口 L3965-3971/L4263-4265)、invest 一方法两画面、flow.py decide_invest docstring「空 stub」过期(调用点已直传容器单例)——全部属实。
- **契约签名表**(§2.1)与 `cw_strategy.py` ABC 逐行对账:11 现签名/返回类型/`decide_box_card(names,...)` 形参名、抽象 12+工厂 1=13 计数——逐字节一致;统一后 12 入口/抽象 13/总 14 的计数推导成立。
- **容器字段与治理**(§2.2):`EncounterPayload.options: list[tuple[int, str]]`/`SupplyPayload.options: list[tuple[str, str, bool]]` 现形状、`_PAYLOAD_DOMAINS` 三域现值、`DEFAULT_GS_SCHEMA` 分组键语义(node_screen_refresh 仅 schema 分组名)、8 新域键先例(每画面一域)、域版本 bump 先例(match_facts 域 2 = execstate #12-#14)、carry 的 None 跳过先例、`PrepObservation` set/Point/BenchChar 非 JSON 形状与 spheres 发射面涟漪论证、session `prep_obs_frame` 刻意字符串注解先例——全部属实。
- **容器 API 语义**:`observe` 拒 None、`write_logic` 渠道族 ('logic_action','logic_hook')、`relay` 空值闸、`REGISTERED_ACTORS` 缺 CwScreenPlanner/CwScreenBoxPick(补登记断言准确)、`_validate_sig` 显式炸错防线——与设计引用一致。
- **瞬态槽三分语义与判别信号**:空选项分支不调 decide 亦不写槽(encounter L296/L431、supply L222、bookcard/box_pick/wish_trial/megastar/partner 同型)——「OCR miss 与真空选项同形返回 []」属实。
- **refresh 旗标等价性**:per-visit 位方案的四格等价论证(首调 False/累计闸命中日志分支/刷新重决策 True/重入重走复位)对 encounter 逐格核实成立;累计计数进入口的可读分歧论证(第 2+ 节点首调即 True、基线核两枝 idx 分叉)成立;handler 侧累计闸与日志分支原样保留的可行面成立;无 match 语境 `cw_match` None 守卫跳过写与 execstate #3 megastar_clicked 写侧同型属实。
- **离屏机制等价性论证**(§2.3):覆盖态论据(fields.md §3.3 商店覆盖备战)、既有两处 live 清点的备战在屏语境、路由点清点对「已离开属屏」的覆盖完备性(识别 miss/映射外建档屏/阶段二双锚/阶段三臂各语境走查)、已 None 跳过不占版本先例(carry L3131)、先清后终窗口无读者——论证链无破绽(插入点行序问题除外,见 F1)。
- **调用方迁移契约**(§2.5)调用点全集普查:src 侧 `match.strategy.decide_*` 全部 17 处 + bridge/flow 内部委托 + `cw_replay.py` L112 驱动器消费全部落在迁移表内,无遗漏调用面;entry.py 零 decide_ 契约调用属实;`mandate_v1/shop.py` gs-first 形态属实(L749);`bridge.decide_prep_screen` 唯一实现(flow.py 无此方法)属实;`_open_shop_phase` obs 形参零消费属实(L2119-2164);`_build_equip_wear_plan` 读点与 fail_reason 通道属实;buy_cards 防御路径临时 match 构造属实(L801-817)。
- **kernel 纯函数零改动边界**:`decide_event` 签名与 D* 三参解析、`decide_supply`/`decide_encounter`/`decide_planner` 委托形态、eval-lcs 形变评分吃原名(cw_events L233/L376)、invest 无 refresh 输入(decide_event 无该形参、闸 2 = handler 既有事实)——边界划分手稳。
- **sim/回放面**:sim 引擎不调 pick 入口、不建模 prep_obs(sim 树 grep 仅注释提及)属实;`--diff` 退役在册(`cw_replay.py` L11 模块头)、`--run/--rounds` 现行形态属实;快照 restore 不对称申报与 `restore_state_snapshot` L4003-4014 一致(shop 在手写重建表、encounter/supply 直透);`ChannelSig.group_id` 随 `write_seq+1` 形态(flow.py L768、bridge.py L259)属实;不跑 sim A/B 的申报合规(strategy-work §4 无可比行为差异)。
- **在飞冲突面**(§2.8):execstate 6/6 done + 正本清零(README 与 commit ee1f4e337 双验证)、turnstate 阶段 1/2+正本落 HEAD(7b50d690f/170d8366f/b6e88a902 三 hash 均真实存在)、unified-obs 3.4 未收与 3.2/3.3 文件面相交(`cw_screen_prep.py`/`cw_screen_buy_cards.py` 与 unified-obs landing 3.4 删除面比对属实)、3.1/3.4 与在飞剩余阶段面零交集核验——前置判断成立。
- **词表普查兜底充分性**(landing 3.2/3.4/末阶段):`prep_obs_frame` 两仓+正本树全部命中落在阶段文件面/正本清单内(6 个正本文件逐一对上);`decide_` 前缀词表可兜全部命中;`PickBoxCard` 残留面(entry.py L194/L456、cw_open_box_action.py、cw_screen_armory_box.py、cw_screen_box_pick.py、25 号篇 L19)在普查范围内;计数词普查正本树命中 6 处 flow/README + session.md + strategy-docs/README + 13/25 号篇 + screens 族——词表可兜(漏列处见 F4)。
- **docs/game 命中面真实性**:两篇 supply 文档「refresh_used=True」句在册(L39 两处)、投资两篇「空 board stub」失真句在册(currency_war_invest_env.md L33/currency_war_invest_strategy.md L34)——清单断言属实。
- **正本落点真实性**:fields.md §8.1-8.5/§9.4(容器独有域反向汇总段在册 L1440-1446)、game_state/README §3.3 域清单(round_ledger 先例行在册 L91)、flow/README 四处计数句位置(L32/L47/L53/L91)——全部可解析。
- **形式项**(iteration-design.md):三文档构成齐(design/landing/README)、阶段小节七件齐(3.1–3.5+末阶段逐一对照)、通用工程门引用式合规、design 状态与 README 进度同步(对抗审中)、设计正文无进度/过程句、§0 文档清单(单文档方案)合规、依据就地标注密度抽查(高,关键主张均带源)。
- **核三·治本**:§1.2 归层(约定层——契约形状从未立统一约定/容器 payload 域从未定为唯一承载)成立;§2 修的是约定+机制本体(统一签名约定+输入唯一承载+唯一写者表+离屏机制),非逐点补丁;后批项(构造注入/session 解散/StrategyState 显式化)显式排期,符合「症状修法须声明战术权衡+排期根治」;同族方向是商店线容器化的延续批而非第 N 件症状补丁。

## 结论

无 blocker。3 条 major(F1 挂点插入点断言与 loop 行序冲突、F2 刷新重决策腿机制失真、F3 写 False 失败语义缺口)均可在局部修订内消解,不动摇方案本体;消解后建议进入零发现复攻轮。
