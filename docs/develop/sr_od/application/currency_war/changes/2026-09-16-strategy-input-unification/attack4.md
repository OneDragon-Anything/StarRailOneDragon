# strategy-input-unification 对抗审查报告（attack4，新一轮独立审查）

> 审查对象 = 本目录 design.md / landing.md / README.md（当前稿，r3 消解后版本）。
> 审查方式 = 无前提对抗（干净上下文、无预设焦点）；判据源全部直调复核（禁转述）：
> iteration-design.md 四硬规则与 §7 三核、strategy-docs/00_framework.md、01_math_framework.md（§1-§3）、
> fields.md（§1/§2.1/§2.2/§2.4/§3.2-§3.4/§3.7.1/§4/§5/§8.6-§8.8/§9 逐节直读）、flow/README.md §2 全节 + flow/session.md、
> strategy-docs 13/22/23/25 篇、代码真值 as-built 直读体（strategies/impl/cw_strategy.py、flow.py、mandate_v1/bridge.py、
> mandate_v1/shop.py、kernel/cw_game_state.py〔含 REGISTERED_ACTORS/game_state_of/leave_screen/_PAYLOAD_DOMAINS/DEFAULT_GS_SCHEMA/EncounterPayload/SupplyPayload〕、
> cw_strategy_session.py、cw_prep_actions.py、cw_equip_wear_plan.py、cw_events.py、cw_decision_trace.py、operations/cw_loop.py、
> operations/cw_screen/ 十 handler（decide 调用点全 grep 对账、观察写点、payload 写端、leave_screen 全调用面、
> handle/lifecycle 双路径）、obs/cw_observation.py、sim/cw_replay.py）、在飞迭代三份（execstate-dissolution / turnstate-retirement /
> unified-obs-reconcile 的 README/design/landing）、仓库 AGENTS.md、strategy-work.md §4/§6。
> 行号 = 审查时点工作树坐标（turnstate-retirement 阶段1/2 与其正本批在本次审查期间落 HEAD：7b50d690f/170d8366f/b6e88a902；
> 引用以符号锚为准）。`prep_obs_frame`/`decide_invest`/`decide_box_card` 做了全仓 grep 锚普查（docs+src 全量逐条归类）。
>
> **发现计数：7 条 = blocker 1 / major 1 / minor 5。**无和稀泥结论；三核均有攻击记录，核一/核二有发现，核三零发现。

## 发现清单

### blocker（定稿门槛：阶段可验收性 / 收尾判据按稿执行必失败）

**B1**｜blocker｜landing.md 正本更新清单 × design.md §2.2-契约 e × landing.md §3.2/§3.4 完成判据（「全量同步复查」硬规则 4 失守）
正本更新清单与历史锚承载面存在系统性漏单：4 份正本文档完全缺席清单、3 处代码符号锚无任何承载阶段，且 3.2/契约 e 的两处括注命题（「锚所在文件已全部入本阶段文件面」）与实况不符——按稿施工，3.2 完成判据不可满足（worker 撞停手令），末阶段「清单清零；正本与实现一致」必然落空。

逐项证据（全部直调复核，行号为当前工作树）：

1. **正本漏单 4 份**（`prep_obs_frame` 在 3.2 落地后全部过期，均不在正本更新清单）：
   - `flow/projection_contract.md:13/:93`（「黑板：session.prep_obs_frame（…读者 = 决策入口）」/「写黑板 session.prep_obs_frame」）——本批正本更新的**核心语义对象**（黑板换宿主），恰漏；
   - `screens/prep.md:13/:22`（「黑板 = session.prep_obs_frame」/「写黑板 session.prep_obs_frame（写者白名单…）」）——备战画面正本；
   - `game_state/action-logic-state.md:50`（「宿主 session.prep_obs_frame」——视觉域动作逻辑态推进的宿主申报）；
   - `game_state/logic-updates/open-bookcard.md:13`（「宿主 session.prep_obs_frame」）。
2. **代码符号锚 3 处无承载阶段**（按契约 e 口径均为「符号改名点随所在文件的切换阶段落码同步改指」，但所在文件不在该阶段文件面；3.5 文件面 = 无〔只读〕，正本清单末行「复核清零 ← 3.5」无法执行，3.5 的兜底句「如分歧 = 按首发点回对应切换线修复重验」也无归属——切换线文件面同样不含这些文件）：
   - `obs/cw_observation.py:2198`（注释「备战观察链的 ``prep_obs_frame.state_gold_trusted``」）→ 应随 3.2，3.2 文件面无此文件；
   - `kernel/cw_events.py:214`（decide_event docstring「锁线 comp 由 decide_invest 从意向状态解析传入」）→ 应随 3.4，3.4 文件面无此文件；
   - `operations/cw_screen/cw_screen_equip_pick.py:49`（「锚 = 意向状态 locked_comp（flow.decide_invest 同源读法）」）→ 应随 3.4，3.4 文件面无此文件（该文件行为零改动申报与此无冲突——改的是注释锚非行为）。
3. **两处括注命题为假**：
   - landing.md §3.2 完成判据「全仓 `prep_obs_frame` 归零（代码体 + 注释锚——**锚所在文件已全部入本阶段文件面**并随落码改指）」——cw_observation.py:2198 为反例；
   - design.md 契约 e「`decide_invest`/`decide_box_card` 注释锚随 3.4，**所在文件已入该阶段文件面**」——cw_events.py:214 与 cw_screen_equip_pick.py:49 为反例。
4. **design.md 契约 e「已知锚面」枚举漏三处**（上述 1-2 的三个代码锚；`decide_box_card` 本体符号存活、其引用锚不受影响，已排除）。
5. 同族说明：3.4 的 grep 判据「`decide_invest(` 契约调用全仓归零」带 `(` 不匹配注释形态；landing 3.5 对叙述性锚「只复核」且文件面为无——注释锚的落码义务只能落在切换线文件面，而这三个文件都不在。

依据 = iteration-design.md §5-4（修订后全量同步复查：design↔landing↔README 全量反查，**正本清单**在列）+ §3.2 + 阶段可验收性（判据与文件面矛盾 = 不可验收，同 attack3 B1 判例）+ strategy-work §6「修复方不得只改被点名处不看同类（泛化步是义务）」（r3-M6 的修复只补了当时点名的 cw_investments/cw_comps/cw_equip_value 三文件与 shop/bridge 模块头，未做全量锚普查——`prep_obs_frame` 72 处、`decide_invest` 18 处的全量归类是本轮直调完成的）。

**修正方向**：①3.2 文件面补 `obs/cw_observation.py`（仅注释锚改指），3.4 文件面补 `kernel/cw_events.py`、`operations/cw_screen/cw_screen_equip_pick.py`（仅注释锚改指）；②正本更新清单补 4 行（projection_contract.md 黑板节、screens/prep.md、game_state/action-logic-state.md、game_state/logic-updates/open-bookcard.md）；③契约 e「已知锚面」枚举补全三处，或把枚举改为「全仓 grep 锚普查对账表」判据（枚举 = 非穷尽申报）。

### major（须修）

**M1**｜major｜landing.md 正本更新清单（节范围粒度）× flow/README.md §2/§2.1/§2.2 × strategy-docs/13_pick_family.md × fields.md §9.4
清单既有行的「节范围」写法不足以保证末阶段完成判据「正本与实现一致」——按行面更新后正本仍残留旧口径，正本内部自相矛盾：

1. **flow/README.md 成员计数句分布三处**，清单行只点名「§2.2 契约接口全景表」：§2 卷引「**契约形状**：契约成员 13 = 分画面决策入口 11(抽象)+ 每局冷建口 2」（§2 标题与 §2.1 之间，不属 §2.2）；§2.1 四身份表契约行「`CwStrategy` ABC(抽象 12 + 非 abstract 工厂 1)」；§2.2 尾注「共 冷建 2 + 决策入口 11(抽象 12 + 工厂 1 = 13)」〔此处在 §2.2 内，行面覆盖〕。批后应为入口 12 / 抽象 13 / 总成员 14——前两处不在清单行范围。
2. **strategy-docs/13_pick_family.md**：清单行范围 =「输入面：选项从容器 payload 读的契约句」，但该篇还有两处契约面事实随批变化：篇头「pick 族 = CwStrategy 的 **9 个**选项决策接口」（拆分后 = 10）；§1 表首行 `decide_invest(kind, options)`（拆为两行，且 `decide_supply`/`decide_encounter` 行的输入形参随 `refresh_used` 退役变化）——均不在「输入面句」表述内。
3. **fields.md §9.4 容器独有域反向汇总**（「…encounter/supply = 记录模型扩面域」枚举行）：8 个新 payload 域 + `encounter_refreshed_in_visit` 入域后该汇总不自含；清单 fields.md 行范围只列 §2.2/§3.4/§3.7.1。

依据 = iteration-design.md §3.1「固定末阶段…判据 = §3.2 清单清零」+ §5-4（正本清单属全量反查对象）；attack3-M6 判同族问题为 major 的先例（其修复解决了代码锚侧，正本节粒度侧未及）。

**修正方向**：①flow/README 清单行改写为「§2 全节契约计数句（卷引/§2.1 表/§2.2 表与尾注）」；②13号篇行补「篇头接口计数与 §1 表 decide_invest 行拆分、supply/encounter 行输入形参」；③fields.md 行补 §9.4 反向汇总（或显式申报「§9.4 不因本批变化」并说明为何新 payload 域不入该汇总）。

### minor（建议）

**m1**｜minor｜design.md §2.2-a/§2.3 × cw_game_state.py:171/:3151-3162（`leave_screen` 守卫面）
`_PAYLOAD_DOMAINS`（现 = `frozenset({'shop','encounter','supply'})`，:171）被申报「扩展为 槽 → 属屏 结构」，但其唯一消费点 `GameState.leave_screen` 的合法域守卫（:3158 `if name not in _PAYLOAD_DOMAINS: raise ValueError(非画面附加域)`）如何跟随未申报：若结构重建后不含 `shop`，既有两处 shop 清点（CloseShop 逻辑腿 cw_game_state.py:2033、prep 相位观察商店锚 miss 分支 cw_observation.py:2617-2619——§2.3 申报「保留未动」）每次调用即 ValueError，商店链全断。另「已 None 跳过」的落点未定死：跳过判定放**挂点**（既有两处清点行为不变，零行为成立）或放 **leave_screen 本体**（既有两处调用点在无 None 语境下行为碰巧等价——观察点已有 `value is not None` 前置守卫、CloseShop 腿由 decide 在屏前置保证非 None——但 §2.6 可观测性申报的口径被实现选型摆布）。
修正方向：§2.3 补两句——「`shop` 保留在映射结构内（leave_screen 守卫面不变，路由清点显式跳过 shop）」「已 None 跳过判定在路由挂点内做，leave_screen 本体不改」。

**m2**｜minor｜design.md §2.8 依赖表（3.2/3.3 行依据列）× landing.md §3.3 文件面 × unified-obs-reconcile/landing.md §3.3/§3.4
①3.3 行依据「`cw_screen_buy_cards.py`/`entry.py` 相交（turnstate）」——`entry.py` **不在本批任何文件面**（design §2.5 明确申报「不在本批文件面」），「相交」不实；真实交集 `mandate_v1/shop.py`（turnstate 阶段2 文件面在列「shop.py（注释）」，turnstate landing:23）在 3.2/3.3 两行均未列（本批 3.2/3.3 均动 shop.py）。②「unified-obs-reconcile 3.4 落码收」是传递前置：其 3.4「依赖：3.3（先武装后拆旧）」（unified-obs landing:49），而其 3.3 完成判据含实机验证期 ≥3 局（候用户窗口，landing:40）——与 design §2.8「实机候窗类验证期不属落码面，不阻任何阶段开工」存在未消解的张力（除非 unified-obs 侧裁定其 3.3 实机验证期不阻其 3.4 开工，该裁定不在本批申报面内）。附注：审查期间 turnstate-retirement 阶段1/2+正本批已落 HEAD，其落码前置事实上已满足——①②属申报失真而非排程风险。
修正方向：①3.3 依据列改「`cw_screen_buy_cards.py`/`shop.py` 相交（turnstate 阶段2）」、3.2 行补 shop.py；②②句补一句对传递链的显式裁定（如「unified-obs 3.4 开工以其 3.3 落码为前提，其验证期窗口不阻——已与该迭代账本对齐」）或改为挂 unified-obs 3.3 落码收 + 3.4 文件面无冲突申报。

**m3**｜minor｜design.md §2.1-4 × landing.md §3.4（`encounter_refreshed_in_visit` 写点规格缺口）
①渠道子型未定死：写 False/True 均「渠道 = logic」，但 `write_logic` 校验合法族 = `('logic_action','logic_hook')` 两可（cw_game_state.py:3185）——计数先例用 `logic_action`+actor='CwScreenEncounter'（cw_screen_encounter.py:246-252 同款面），per-dispatch 复位更像 lifecycle 语义（logic_hook 先例 = 接管协议字段），两选法 journal 行 family 不同、审计归因不同；②写 False 点 = `CwScreenEncounter.__init__` 在无 match 语境（局外/测试构造 `ctx.cw_match=None`）的处置未申报：`game_state_of(None)` 返一次性空载体（cw_game_state.py:2482-2483），写入静默无效——需申报守卫（match None 跳写，同 supply `self._refresh_used` 实例态兜底先例 cw_screen_supply_node.py:120/213）或显式声明一次性写入无害。
修正方向：渠道定死（建议 logic_action+actor='CwScreenEncounter'，与同址累计计数写一致）；__init__ 写点补 match-None 守卫申报。

**m4**｜minor｜landing.md 正本更新清单（25_event_overlays 行）× strategy-docs/25_event_overlays.md §1/§2
范围界定行自设「= 本篇实际节名」标准（武装箱弹窗项如此申报，该篇 §2 表行名核实一致），但同枚举内「**星徽秘典弹窗**」并非该篇任何节名——该篇 §1 用「星徽秘典四选一」、§2 表用「星徽典籍」，均不同名；「列车同行（伙伴）」该篇实际用名「选择伙伴」（有括注 gloss 可解析，但同样非本篇节名）。值对标签错类（攻击纪律重点错误类）：正本批 worker 按名索节时两处需二次语义对齐。
修正方向：枚举项改用该篇实际节名并括注建档屏名（如「星徽秘典四选一（建档屏：货币战争-星徽秘典弹窗）」「选择伙伴（建档屏：货币战争-列车同行）」），或在行首声明「枚举项 = 建档屏名，节名按语义对应」。

**m5**｜minor｜design.md §1.1（顺带勘误句）× §2.1 统一纪律 1 × fields.md §8.7
「迁移批次二」两处引用（§1.1「迁移批次二后调用点直传容器单例」、§2.1「迁移批次二前的 stub 形态正式退役」）指向已删过程件：fields.md §8.7 申报「迁移波次/批次范围/消费切换排期归退役过程件（原单一源 r5-migration-plan，已删，考古走 git 历史）」——「批次二」在活树内不可解析（会话期批次代号，非持久索引），无会话历史的读者只能靠猜。
修正方向：改为语义描述（如「统一 state 迁移完成后」「容器单例直传的现行形态（cw_screen_invest_strategy.py 调用点直调 `game_state_of` 为证）」）。

## 已攻未破的面（零发现申报）

以下各面经直调复核**未发现**问题（列面清单以自证攻击密度，非总体评价）：

- **核一·现状症状逐条对码**：三形状并存（cw_strategy.py:117-187 逐签名实读：prep/shop 两参无 gs、invest 5 参含 kind、supply/encounter 带 refresh_used、pick 族其余 `(options, gs, session, config)`）；supply 调用方容器派生旗标 = `int(gs.supply_refresh_used.value or 0) > 0`（cw_screen_supply_node.py:210-213/:230-232）；encounter 首调缺省 False/重决策传 True/闸本体读累计计数命中仅打日志不重决策（cw_screen_encounter.py:304/:313-342/:439-467，旧 handle 与五段 lifecycle 两路径各一对）；invest 两调用点传 `'strategy'/'env'` + 容器单例（cw_screen_invest_strategy.py:404 / cw_screen_invest_env.py:303）；flow.py:471「state.board 由调用方传空 stub」确已过期；`gs.shop` 活写端在产、live `leave_screen` 恰两处均 shop 域（cw_game_state.py:2033 + cw_observation.py:2617-2619；encounter/supply 清点仅在 sim 合成口 :3970-3971 与一次性投影 :4263-4265）；EncounterPayload/SupplyPayload 现形状与「形状升级」前提一致（cw_game_state.py:610-620）。
- **核一·refresh 旗标等价性**：encounter per-visit 位与改前两态逐字节等价——`CwScreenEncounter` 由 cw_loop 每分派新建（cw_loop.py:1406-1410），`__init__` 写 False 与「访问」对齐；写 True 点 = `_emit_refresh_click`（on_outcome 登记件同址，累计计数写端单点申报属实，无第二计数写点）；「已用」闸三分支（命中日志/无次数/发射）语义保真；刷新重决策仅经「无条件重读」链且不经路由点。supply 入口读累计计数与调用方派生式逐字节可同；无 match 路径不调 decide（cw_screen_supply_node.py:222）。
- **核一·路由清点**：挂点插入点唯一（cw_loop.py:1818-1821 单一 `_dispatch_identity_screen` 调用位之前）；属屏映射十行逐行对分发臂全部属实（含反直觉三行：列车同行:1374/骇入策划:1380/星徽秘典弹窗:1458；武装箱弹窗:1431→CwScreenArmoryBox 无 decide 注属实）；绕行路径（stop_at_prep 早退 :1754-1756、未知兜底）窗口内无 decide 消费论证成立；阶段二双锚/阶段三特殊规则臂/未识别语境清全部十槽无害（该语境无任何 pick decide）；每路由轮「真离屏转换帧每槽至多一行」的量级申报与机制一致。
- **核一·prep_obs 迁移**：4 写点/3 读点全集与申报一致（grep 全量；读者 = bridge:174/cw_equip_wear_plan:163/cw_screen_prep:1865）；`PrepObservation` 含 `set`/`Point`/`BenchChar` 属实（cw_prep_actions.py:70-82）；非 Field 化不入快照流水（full_state_snapshot 只收 Field 面）；`game_state_of` 恒返容器（None→一次性空载体，cw_game_state.py:2482-2483）换源无新崩溃面、fail_reason 通道语义保持；`_open_shop_phase` 的 obs 形参现行零消费属实（:2119-2164 全文实读）。
- **核一·契约面**：成员计数 12→13/13→14 与 ABC 实读相符；统一后签名表与返回类型逐行对码；`decide_shop_screen` 驱动器（flow.py:739/bridge.py:224）与覆写体内 `decide_shop_action` 调用点（flow.py:798/bridge.py:273）申报属实；sim 侧唯一契约消费 = cw_replay.py:112（decide_shop_screen，签名不动），sim 引擎零 pick 入口调用（grep 实证）；`--diff` 退役在册（cw_replay.py 模块头）且 strategy-work §4 确实仍引 `cw_replay --diff`（:50）——design「既有文档债非本批辖」申报属实；决策迹载体 cw_decision_trace 在产。
- **核一·阶段可验收性试读**：3.1 纯增量零行为成立（新槽现状恒 None→清点跳过 = no-op；#3/#4 形状升级无活写端读者）；3.2/3.3/3.4 各自交付态下 ABC/flow/bridge/调用点/测试自洽（共用文件按符号拆分不跨阶段；跨阶段无半迁移态）；3.5/末阶段判据可执行（除 B1/M1 所列清单缺陷）。
- **核二·形式面**：landing 各阶段七件齐；通用工程门单一定义+逐阶段引用；README 模板合规、进度只在 README；无行号锚、无过程叙事（裁定指针形态合规）；引用锚抽查（fields.md §2.2/§3.4.4/§3.7.1/§8.8、flow/README §2.2/§2.3/§2.4/§2.5、session.md §5.1 B4、execstate #12-#14/#20 先例、unified-obs 3.4「旧安灯退役批」节名）全部真实存在；ADR-0517/0583 引用系仓内既有惯例（代码同引；ADR 档案退役为全局既成事实，cw README 在册）。
- **核二·在飞对账**：execstate「6/6 done + 正本清零 ee1f4e337」「#4-#6 已落地（encounter on_outcome 写端/supply live 写端在产）」「域内容变更 bump 先例」「#20 非 Field 先例」逐条相符；unified-obs 3.4 文件面（cw_screen_prep/buy_cards）与本批 3.2/3.3 相交申报属实；turnstate 文件面（bridge/entry/shop 注释/buy_cards）主体相符（失真处见 m2）。
- **核三·治本**：§1.2 归层结论成立——争议确在「从哪个形参进来」的约定层（数据本体每帧同源，代码逐点核实）；§2 是立约定而非逐 handler 症状补丁——一批把 12 入口签名与输入承载一次立死，shop→prep→pick 族三件同根由本批以架构级约定收口（跨件半问过关，非第二件症状修）；「行为零变化」核心主张经新写端量级/路由时序/refresh 分支/prep_obs 封闭性/每阶段切换线五个专攻面攻击后成立（缺陷仅 B1/M1/m1-m5 所列文档面）。
