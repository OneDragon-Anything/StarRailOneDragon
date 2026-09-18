# 策略器决策输入统一 迭代设计（总纲）

## 0. 元信息

- 迭代目标（用户裁定 2026-09-16，会话讨论三条）：
  1. **投资两画面拆分**：`decide_invest(kind)` 一分二（`decide_invest_strategy` / `decide_invest_env`），画面→方法恢复一一对应；
  2. **入参统一**：策略器基类全部决策方法统一为 `decide_<画面>(gs, session, config)`；
  3. **决策输入入容器**：画面选项/观察载荷由画面 op 上报到 game state 观察态（画面 payload 域），策略从容器读、不再收载荷参数。
- 终态方向（本迭代**不**落地）：构造注入 `(gs, config)` + 零参 decide + StrategySession 解散 + StrategyState 外部读者显式化——自成后批迭代。本迭代 = 其第一批，交付零行为变化前提下的统一签名基线。
- 状态：对抗审中
- 文档清单：无独立详设——本篇 §2 即完整设计（契约签名表 + payload 槽位表 + 离屏机制 + 迁移契约），深度按「实现者无需再设计」标准。

## 1. 问题与动机

### 1.1 现状症状（符号锚，行号不书）

- **契约签名三形状并存**（`strategies/impl/cw_strategy.py` ABC）：备战/商店两主入口吃旁路——`decide_prep_screen(session, config)` 读 `session.prep_obs_frame`、`decide_shop_action(session, config)` 内部取 `game_state_of(session)`，均无 gs 形参；pick 族 9 入口收 `(options, gs, session, config)` 4–5 参直传；其中 `decide_invest` 另带 `kind` 字符串分叉，`decide_supply`/`decide_encounter` 另带 `refresh_used` 布尔。两处旗标的现行语义（直调代码核实）：supply 调用方传**容器派生旗标**（`gs.supply_refresh_used` 派生，`cw_screen_supply_node.py` 调用点），闸命中静默落选卡支；encounter 调用方首调不传（缺省 False）、仅**本访问刷新后的重决策**传 True（`cw_screen_encounter.py` 调用点），闸命中时打日志分支并不重决策——两屏闸命中行为形态不同（log 分支 vs 静默），本批均原样保留。
- **选项数据双源**：画面 op handler 本地 OCR 构造 typed option 列表（`EncounterOption` 等，`kernel/cw_events.py`）传参；容器画面 payload 域按规格本应承载同源数据——`gs.shop` 活写端在产；`gs.encounter`/`gs.supply`（`EncounterPayload`/`SupplyPayload`，`kernel/cw_game_state.py`）**活写端缺位**（live 仅 `leave_screen` 置 None 两处：CloseShop 逻辑腿属 shop；encounter/supply 的清点只在 sim 合成口）。
- **投资一方法两画面**：`cw_screen_invest_strategy`/`cw_screen_invest_env` 两画面调同一 `decide_invest(kind, ...)`——其余画面皆一画面一方法，唯独此处靠字符串参数分叉。
- 顺带勘误：`flow.py` `decide_invest` docstring「state.board 由调用方传空 stub」已过期（现调用点已直传容器单例，`cw_screen_invest_strategy.py`/`cw_screen_invest_env.py` 调用点在册），随本批修正。

### 1.2 根因归层

**约定层**。契约签名形状从未立过统一约定——黑板模式（ADR-0517/ADR-0583）先落在备战/商店主入口，pick 族沿用参数直传惯性；容器「画面 payload」域已建立且治理规则齐备（fields.md §2.2 例外、§3.7.1 域版本），但从未被定为「决策输入的唯一承载方式」。非语义层问题：每帧喂给策略的事实没有争议，争议只在「从哪个形参进来」。

### 1.3 解决到哪 / 明确不解决

**解决**：①契约 12 决策入口签名统一 `(gs, session, config)`；②决策输入数据全部经容器承载（新增 8 域键 + `prep_obs` 非 Field 容器字段 + 升级 2 域形状 + encounter/supply payload 活写端接通 + 路由点陈旧清点，见 §2.2/§2.3）；③invest 拆分。**行为零变化**（每帧同输入值、同决策输出、同动作流），验证设计见 §2.6。

**明确不解决**（各自自成迭代或行为批，防范围外溢）：
- 构造注入 `(gs, config)`、零参 decide、StrategySession 解散、StrategyState 外部读者（~100+ 处 `strategy_state_of` getattr 面）显式化——**后批**（承接出处 = 本迭代讨论，落地时另立 changes/ 目录）；
- pick 族输出动作化（返回动作 op 而非 Pick/索引）与备战 `None` 显式化——**独立第三轴**，未立项；
- 帧代次标注（`session.prep_frame_class`/`shop_frame_class`）与 gs `mark_frame_obs`/`FrameObsLevel` 两套帧语义机制的合并——随 session 解散批；
- supply/encounter 两屏「已用」旗标语义的统一（现状 supply=局内累计派生、encounter=本访问位，本批逐字节保真不统一）——行为批议题，登记不解决；
- payload 槽位内容扩展（投资候选带品质、遭遇带刷新剩余等 fields.md §3.4 已规格但今日 decide 不消费的面）——行为批，不混入形状批；
- 统一观察架构批的 decide() 输入视图口径与本批「gs 形参 = 容器单例现引用」的衔接（当前不冲突；该批落地时裁决视图化形态，登记不解决）；
- kernel 纯函数（`cw_events.decide_event` 族）签名与判据——零改动（见 §2.8 取舍）。

## 2. 方案

### 2.1 契约签名统一（`cw_strategy.py` ABC）

统一形状：**`decide_<画面>(gs: GameState, session: StrategySession, config) -> <现状返回类型不变>`**。

| 现签名 | 统一后 | 返回（不变） |
|---|---|---|
| `decide_prep_screen(session, config)` | `decide_prep_screen(gs, session, config)` | `CwAction \| None` |
| `decide_shop_action(session, config)` | `decide_shop_action(gs, session, config)` | `Action` |
| `decide_invest(kind, options, gs, session, config)` | 拆 `decide_invest_strategy(gs, session, config)` / `decide_invest_env(gs, session, config)` | `PickEvent` |
| `decide_supply(options, gs, session, config, refresh_used=False)` | `decide_supply(gs, session, config)` | `SupplyPick` |
| `decide_encounter(options, gs, session, config, refresh_used=False)` | `decide_encounter(gs, session, config)` | `EncounterPick` |
| `decide_megastar(options, gs, session, config)` | `decide_megastar(gs, session, config)` | `MegastarPick` |
| `decide_partner(options, gs, session, config)` | `decide_partner(gs, session, config)` | `PartnerPick` |
| `decide_planner(options, gs, session, config)` | `decide_planner(gs, session, config)` | `PlannerPick` |
| `decide_star_tome(options, gs, session, config)` | `decide_star_tome(gs, session, config)` | `int` |
| `decide_wish_trial(options, gs, session, config)` | `decide_wish_trial(gs, session, config)` | `int` |
| `decide_box_card(names, gs, session, config)` | `decide_box_card(gs, session, config)` | `int` |

统一纪律（共五条；各入口 docstring 契约，措辞沿用 shop/prep 现行形态推广）：

1. **gs 形参 = 容器单例现引用**（`game_state_of(session)` 同一实例，调用方直传；禁传副本/裁剪视图——历史 stub 形态正式退役）。
2. **在屏前置 = 本入口的 payload 槽处于可决策态**（离屏 None 进决策 = 观察层失约 → 抛错，禁静默按空态决策；现 `decide_shop_action` 的 shop=None 抛错、`decide_prep_screen` 的帧缺失抛错，同型推广到 pick 族）。瞬态槽三分语义见 §2.2-c。
3. **形参位次恒定** `(gs, session, config)`；config 仍按参注入（构造无参现状保持，构造注入属后批）。
4. **`refresh_used` 形参退役（仅 supply/encounter 有此形参）**，逐字节保真方案：
   - **supply**：入口读顶层容器字段 `gs.supply_refresh_used`（域键 `node_screen_refresh` 仅是 `DEFAULT_GS_SCHEMA` 版本分组名，非访问路径），派生式与现调用方逐字节相同 → 等价。
   - **encounter**：现状旗标语义 = 「本次决策调用会话内已发生刷新」——**适用单位 = 每次 handle 调用**，非每次 op 实例：首调缺省 False、刷新发射后的重决策 True、**重入裁决重走后的再次首调复位 False**（重入路径实证：`cw_screen_encounter.py` 锚在 = 清标志重走后再次无参首调）。容器累计计数（`gs.encounter_refresh_used`）不进入口（第 2+ 遭遇节点首调即见 True，产生可读分歧，禁）。等价承载 = 新顶层容器字段 `gs.encounter_refreshed_in_visit: Field[bool]`（渠道 = `logic_action` 动作上报族）。写点定死（**写 False 与写 True 同型可靠性**）：**写 False 点 = `CwScreenEncounter` 各决策路径（handle 路径与 lifecycle 路径）每次进入的首调前置段**——复位随 handle 进入而非实例构造（重入重走必须复位，否则重入首调收 True 与现状 False 分歧）；**写 True 点 = 刷新发射分支内、重决策发起前的同步直写——两点均为同步直写、失败即异常上抛响亮暴露，禁吞异常 best-effort 形态（失败窗静默读错值 = 基线核刷新枝 idx 分叉的禁类）**；无 match 语境（局外直构 op）经 `cw_match` None 守卫跳过写（缺席跳过，与 execstate #3 megastar_clicked 写侧同型）。窗语义：True 残留窗口 = 刷新发射至同 handle 内重决策之间；跨 handle 无读面（下 handle 首调前置复位 False；本字段为顶层字段**不在路由清点辖域**，无离屏清点路径）——复位规则随字段注释申报。**读侧 None 语义**：未写态读 None 缺省按 False（保守向；生产不可达——首调前置先于任何决策；第三方/测试直调入口的口径，先例 = megastar_clicked 读侧 getattr 缺省 False）。**journal 归属钉死**：本字段走 write_logic 常规规则进快照流水，**不适用** journal.md §6 的「刷新计数组」豁免类（该类字面辖计数器，不辖 per-visit bool 位；写入频次 = 每访问 1–2 次，流水成本可忽略）。handler 侧「本局已用」闸与日志分支原样保留（读累计计数，现状不动）。
   - **invest 无 refresh 输入**：kernel `decide_event` 不收计数、ABC 现签名无该形参；fields.md §3.4.4 逐卡刷新计数闸 = handler 既有事实（闸 2），非入口契约，本批零触碰。
   - 与 execstate-dissolution 的分工：其 #4–#6 删 ExecState 旗标、收口 handler 读点（读累计计数）；本批新增的 `encounter_refreshed_in_visit` 是**策略入口输入位**（本访问语义），两者并存不互代——该字段随正本批入 fields.md 规格。
5. **契约成员计数**：抽象成员 12 → 13（决策入口 11 → 12 + 冷建口 create_session）；非 abstract 工厂 `create_state` 不变，成员总数 13 → 14。flow/README §2 形状注随正本批同步。依赖与在飞冲突见 §2.8。

**兼容裁定（第三方插件契约破坏申报）**：本批 = 契约破坏性变更（删除 abstract `decide_invest`、新增两个 abstract 入口、其余决策入口签名全改）——存量第三方策略实现类在新 ABC 下实例化即 TypeError。裁定 = **干净断、不留兼容壳**（用户裁定 2026-09-16 会话；依据 = 注册面封闭集 {mandate_v1}，flow/README §2.4——decision_v2 基线臂已删除终结，契约当前为内部面；留壳 = 债）。session.md §5.1 B4 缺省条款的辖域（「新增 abstract 钩子」的兼容）随本批收缩申报：`create_state` 非 abstract 缺省保留，其余契约面不设兼容层；契约形状修订随正本批入 flow/README §2。

### 2.2 画面 payload 槽位表（决策输入容器化）

| # | 槽位 | 类型 | 唯一写者 | 读者 | 现状→动作 |
|---|---|---|---|---|---|
| 1 | `gs.prep_obs` | `PrepObservation \| None`（**非 Field 容器字段**，见配套契约 e） | CwScreenPrep 观察链（observe_full 装配 / 破墙派生帧 / 逻辑态直写步；写点白名单 4 处全在 `cw_screen_prep.py`，直赋换宿主） | decide_prep_screen；`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`（穿戴计划唯一事实源）；`cw_screen_prep.py::_act_execute_default` OpenShop 腿死参喂死读点（`obs` 形参现行零消费，处置写死 = 换源，死参保留不删——删参属 `_open_shop_phase` 签名面，超本批最小面） | 自 `session.prep_obs_frame` **迁入**（session 槽退役）；**语义豁免申报**：本槽不入「离屏置 None」payload 家族（见 §2.3）——现状 session 槽即从不清空、新鲜度 = 写或沿用、读者纪律 = 备战访问内消费，豁免 = 零行为；heavy/light 分层与帧内字段语义全部不动 |
| 2 | `gs.shop` | `ShopPayload \| None` | 既有观察段 | decide_shop_action | 不动（仅签名切换） |
| 3 | `gs.encounter` | `EncounterPayload`（**现名沿用，不改名**；形状升级：`options: list[tuple[int, str]]` → `list[EncounterOption]`） | CwScreenEncounter（活写端本批接通） | decide_encounter | 域已有；域版本 bump |
| 4 | `gs.supply` | `SupplyPayload`（**现名沿用**；形状升级：`options: list[tuple[str, str, bool]]` → `list[SupplyOption]`） | CwScreenSupplyNode（活写端本批接通） | decide_supply | 同上 |
| 5 | `gs.invest_strategy_opts` | `list[str] \| None`（**OCR 原文名**，与现 decide 输入逐字节一致；规范名归一只归 `strategy_refresh_used` 计数键，禁进决策输入——kernel eval-lcs 形变评分吃原名） | CwScreenInvestStrategy | decide_invest_strategy | 新增 |
| 6 | `gs.invest_env_opts` | `list[str] \| None`（OCR 原文名） | CwScreenInvestEnv | decide_invest_env | 新增 |
| 7 | `gs.megastar_opts` | `list[MegastarOption] \| None` | CwScreenMegastar | decide_megastar | 新增 |
| 8 | `gs.partner_opts` | `list[PartnerOption] \| None` | CwScreenPartner | decide_partner | 新增 |
| 9 | `gs.planner_opts` | `list[PlannerOption] \| None` | CwScreenPlanner | decide_planner | 新增 |
| 10 | `gs.star_tome_opts` | `list[str] \| None` | CwScreenBookcard | decide_star_tome | 新增 |
| 11 | `gs.wish_trial_opts` | `list[str] \| None` | CwScreenWishTrial | decide_wish_trial | 新增 |
| 12 | `gs.box_card_names` | `list[str] \| None` | CwScreenBoxPick | decide_box_card | 新增 |

配套契约（**七条**）：

- **a. gs_schema 申报**（fields.md §3.7.1 治理）：**8 个新域键**（#5–#12，各自独立域键——先例 = shop/encounter/supply 每画面一域）+ **2 个变域 bump**（#3/#4 形状升级）+ **`node_screen_refresh` 域版本 +1**（新顶层字段 `encounter_refreshed_in_visit` 入该域 = 域内容变更，execstate #12-#14「域扩展即 bump」先例）。`prep_obs` 为非 Field 容器字段（契约 e），不占域键、不入快照流水。typed option dataclass 经 asdict 序列化（`ShopPayload.cards` 先例），值形状 JSON 序列化安全。
- **b. 离屏机制**：见 §2.3（路由点陈旧清点；prep_obs 豁免）。
- **c. 瞬态槽三分语义**（#3–#12；fields.md §2.2「在屏失读沿用旧值」为持久事实设计，对逐访问瞬态槽细化为）：**离屏 = None**；**在屏失读帧 = 不写不读**（handler 走自身失败安全分支——现状零选项/OCR miss 即不调 decide 同型，禁把上一访问的旧选项喂本帧决策）；**在屏读得 = 覆盖**。判别信号定死 = **「写槽以该分支将调用 decide 为前提」**（写槽动作只存在于 handler 已决定调用 decide 的分支内；OCR miss 与真空选项在识别面同形返回 `[]`，现状 handler 零选项即走盲点默认**不调 decide 亦不写槽**——故本批不引入 `[]` 写入场景，空列表写槽若未来行为批引入须同步申报）。**刷新重决策腿分屏形态申报**（三屏刷新链形态不同，禁统一改形）：**encounter = 同访问内二次「读得=覆盖」**——刷新后的重决策前，必须以重读产物（重截图重 OCR，既有「无条件重读」链原样）覆盖写槽，方可再调 decide，禁沿用刷新前旧槽内容；**supply/invest = 发射后交回重入型**——刷新发射即 return（supply 经 round_retry 重入下一轮重读重决策，invest 同型），无同访问二次覆盖，重入访问走常规「OCR → 写槽 → decide」起点链天然单源。结构防线 = **「每次决策恰以当次观察产物为单源」纪律**（decide 只在写槽之后调用；encounter 同访问重读链与 supply/invest 重入链均为既有行为本体，不算双源；单帧锁/流程锁逐 handler 锁此单源性）。`prep_obs` 不适用本条（豁免域，沿用旧行为）。
- **d. 选项数据单源**：handler 的 OCR 产物是唯一来源——写槽后调 decide。kernel 纯函数（`decide_event`/`decide_encounter` 等）签名与判据零改动，仍收 typed options 列表；策略入口从槽取列表传入（数据来源组装职责归策略入口，kernel 保持纯函数纪律）。
- **e. prep_obs 迁移附注**：`StrategySession.prep_obs_frame` 字段删除；**存储形态 = 非 Field 容器字段**（直赋读写，与 `tracked_books`/`exec_books` 同型访问口；先例 = execstate #20 `plane_node_sequences` 非 Field 处置）。理由：`PrepObservation` 含 `set`/`Point`/`BenchChar` 非 JSON 安全形状，Field 化须值形状改造（set→list、Point→元组）——该形状进 `spheres` 发射面（ClickSpheres 排序消费 `Point`），改造 = 全链涟漪违零行为；非 Field 化则不入快照流水，可观测面与现状 session 槽完全一致（零变化）。4 写点 = 直赋换宿主，无 observe/carry/write_logic 渠道语义；「破墙派生帧」等来源分级已由 `PrepObservation` 字段注释内部承载（heavy/light 语义），不新增 evidence 面。`prep_frame_class`/`shop_frame_class` 两触发信号槽**本批不动**（非决策输入，归后批帧机制合并）。**注释历史锚处置口径（唯一）**：符号改名点随所在文件的切换阶段落码同步改指（prep_obs 锚随 3.2；`decide_invest`/`decide_box_card` 注释锚随 3.4，所在文件已入该阶段文件面）；纯叙述性历史锚随正本更新批复核清零。已知锚面（**非穷尽示例**——穷尽性由各切换线的全仓 grep 锚普查对账表保证）= `cw_strategy.py`/`cw_screen_prep.py`/`obs/cw_observation.py`/`mandate_v1/shop.py`/`bridge.py` 模块头（prep_obs，随 3.2）；`kernel/cw_events.py`/`cw_screen_equip_pick.py`/`cw_investments.py`/`cw_comps.py`/`cw_equip_value.py`（decide_invest/decide_box_card 注释，随 3.4）。
- **f. 新槽注释**：全部带归属申报与坐标系注释（归属判据双锚 = 「谁产生/谁消费」宿主 `flow/session.md` §2 + fields.md §8.8 字段准入四问；带索引语义者加 `[索引定义]`）。
- **g. 选项类宿主与 import 方向**（payload 槽承载 typed 选项类的槽位，即 #3/#4/#7/#8/#9——五者选项类同住 `cw_events.py`，其模块级 import `cw_game_state`，容器反向 import 选项类即循环导入，禁）：选项类宿主不变（`kernel/cw_events.py`）；各 payload 槽**类型注解字符串化 + `TYPE_CHECKING` 承载**（先例 = session `prep_obs_frame` 刻意字符串注解、容器内先例 `cw_game_state.py` 字符串注解形态）；序列化经 `dataclasses.asdict` 鸭子形（运行时对象仍为选项类实例，无类型依赖）。#5/#6/#10/#11/#12 为 `list[str]` 纯标量形，无此问题。

### 2.3 离屏机制（payload 域的 live 置 None 写端）

**放弃「leave_screen 改域集遍历」方案**——商店对备战是覆盖态不是兄弟屏（fields.md §3.3），既有两处 live 清点（CloseShop 逻辑腿、prep 相位观察商店锚 miss 分支）都发生在备战仍在屏语境，全域遍历会清掉 `prep_obs` 令关店后首次 `decide_prep_screen` 抛错。改为：

- **路由点陈旧清点**：外循环每轮「画面识别结果产出后、阶段一身份分发（`cw_loop.py::_dispatch_identity_screen` 调用）之前」设单一挂点，按**属屏映射**清除 payload 槽。语义三定义：
  - **路由屏取值**：识别命中且在映射内 = 该屏名，只清属屏 ≠ 它的槽；映射外建档屏 / 非身份臂语境（阶段二备战双锚、阶段三特殊规则臂）/ 未识别 = 清全部十槽（这些语境无任何 decide 消费，清点只影响审计面）。
  - **已 None 跳过**：槽值已 None 跳过清点写（不占 write_seq 版本、不落 journal 行；先例 = 容器 `carry` 的 None 跳过）——journal 增量仅发生于「真离屏转换帧」，每槽每访问至多一行。
  - **挂点时序与两路径语义（钉死）**：挂点 = 「识别产出后、阶段一身份分发调用前」（复用当轮识别结果，零二次识别）。两条非常规路径语义分立：①`stop_at_prep` 早退（识别屏名 ∈ PREP_DIRECT_EXIT_SCREENS 即 round_success 终止本轮 loop）发生在**挂点之前**——早退轮挂点不执行、不清点，清点顺延至 loop 下一次路由周期；无害申报 = 早退屏非映射属屏、窗口内无 decide 消费。②未知兜底停机发生在分发之后的循环尾——**不绕行**，本轮已按「未识别 = 清全部十槽」清点。
  属屏映射单一源 = **扩展既有 `_PAYLOAD_DOMAINS`**（`cw_game_state.py`，现含 shop/encounter/supply 三域）为 `槽 → 属屏` 结构（不为 schema 增分类维度，防双源）。属屏 = `_dispatch_identity_screen` 分发键（建档屏名），10 行清点全集（键以 `cw_loop.py` 分发臂为锚）：
  | 槽 | 属屏（分发键） |
  |---|---|
  | `gs.encounter` | 货币战争-遭遇节点 |
  | `gs.supply` | 货币战争-补给 |
  | `gs.invest_strategy_opts` | 货币战争-投资策略 |
  | `gs.invest_env_opts` | 货币战争-投资环境 |
  | `gs.megastar_opts` | 货币战争-盛会之星 |
  | `gs.partner_opts` | 货币战争-列车同行（选择伙伴的建档屏名，反直觉行） |
  | `gs.planner_opts` | 货币战争-骇入策划（反直觉行） |
  | `gs.star_tome_opts` | 货币战争-星徽秘典弹窗（反直觉行） |
  | `gs.wish_trial_opts` | 货币战争-祈愿试炼 |
  | `gs.box_card_names` | 货币战争-备战-武装箱选择（注：`货币战争-武装箱弹窗` 派发 CwScreenArmoryBox，无 decide 调用不产槽） |
- **豁免与保留**：属屏映射值结构 = `(属屏, route_clearable)` 二元组——`prep_obs` 不入映射（§2.2 #1 豁免申报）；`shop` **保留在映射结构内**（既有两处 `leave_screen(gs.shop, …)` 的域守卫校验依赖映射含 shop——移出即 ValueError）且 `route_clearable = False`（编码 = 二元组第二位 False，挂点清点循环显式跳过——无自由文本「标记」，防填错形状触发挂点通用规则清 gs.shop，与 CloseShop 腿构成双写端/开店中段 decide 抛错）；shop **既有两处显式清点保留** = CloseShop 逻辑腿 + prep 相位观察商店锚 miss 分支，为 shop 域唯一清点源。「已 None 跳过」实现落点 = **路由挂点侧**（挂点读槽值判 None 跳过），`leave_screen` 本体不动（其无条件写语义是既有清点两处所依赖的现状）。**清点写入口形态** = 经 `leave_screen(槽, sig=…)`（与既有两处清点同口径）；**sig 钉死** = family/mode 引用既有 CloseShop 腿清点行的同一常量源（禁新造第二 family），`actor = 'cw_loop_route_clear'`（区分写端），group_id 沿用 write_seq 形态——journal 行与既有清点行同族、可按 actor 过滤。
- **等价性论证**：挂点只清「路由判定已离开属屏」的槽——此刻该屏访问已终（事件 overlay 消失路由回备战时，pick/encounter/supply 槽的访问已结束）；handler 内部重决策环（如 encounter 刷新后重决策）不经路由点，槽保活——**重决策前以重读产物覆盖写槽（§2.2-c 刷新重决策腿），非沿用旧槽**。被清的槽本就属「非当前画面 = None」结构事实语义（fields.md §2.2 例外），无读者在清点与下次覆盖之间消费它。
- **效果**：#3–#12 十槽在 live 首次获得离屏写端（修「活写端缺位」）；「None = 观察层失约」守卫真实可达；dump gs 审计面无陈旧非 None 槽。sim 合成口 `leave_screen` 调用不动（sim 口自足）。

### 2.4 invest 拆分

- `decide_invest_strategy(gs, session, config)` / `decide_invest_env(gs, session, config)` 两入口共享 kernel `cw_events.decide_event`（D* 三参解析、信号喂入、`_consume_prep_direction_frame` 入口内务全部同现状；P1 期两 kind 同实现——**分表现留缝不实现**，缝 = 两入口各自独立的方法位）。`kind` 字符串分支消亡。
- flow.py 现 `decide_invest` 方法体拆两半：共享段（入口内务 + D* 解析 + CommitSignals affinity 喂入）收私有 helper，两入口各自传 src（'invest_strategy'/'invest_env'）与本屏槽。
- 消费点同步：`cw_screen_invest_strategy.py` 调 `decide_invest_strategy`、`cw_screen_invest_env.py` 调 `decide_invest_env`（'strategy'/'env' 字符串实参消亡）。

### 2.5 调用方迁移契约

| 调用面 | 改动 |
|---|---|
| pick 族画面 op handler（10 文件：invest_strategy/invest_env/supply_node/encounter/megastar/partner/planner/bookcard/wish_trial/box_pick） | OCR 产物写本屏槽（observation 覆盖）→ 以 `(gs, session, config)` 调 decide；本地 typed option 构造改为写槽的数据装配（同一次 OCR，无第二次识别）；**每 handler 的写槽-决策改形须同时覆盖旧 handle 与五段 lifecycle 两路径**（encounter 单文件 4 个 decide 调用点 = 两路径各首调/重决策一对；调用点全集以 grep 计数为准）；encounter/supply 的 payload 活写端随此接通；encounter 另维护 `encounter_refreshed_in_visit`（写点定死见 §2.1-4）；encounter/supply 刷新重决策腿 = 重读产物覆盖写槽后再 decide（既有「无条件重读」链原样，§2.2-c） |
| `cw_screen_prep.py`（decide_prep_screen 两调用点） | 传 `gs = game_state_of(session)`；观察链写点 `session.prep_obs_frame =` 改 `gs.prep_obs =` |
| `kernel/cw_equip_wear_plan.py` | `getattr(session, 'prep_obs_frame', None)` 改 `game_state_of(session).prep_obs`（同点改名 + 宿主解析换源） |
| `cw_screen_buy_cards.py`（run_buy_waves 单动作循环 + 防御路径裸 match 构造） | 签名随改；防御路径语义不变 |
| `cw_screen_planner.py` / `cw_screen_invest_strategy.py` / `cw_screen_invest_env.py` 局外防御路径（无 match 语境 kernel 纯函数直调） | **零改动**（kernel 纯函数签名不变，直调不涉槽）；核对申报在案 |
| `cw_loop.py` | 路由点陈旧清点挂点（§2.3） |
| `flow.py` `decide_shop_screen` 驱动器 + `bridge.py` 同名覆写 | **驱动器签名不动**（非契约成员，内部已自取容器）；两者内部对 `decide_shop_action` 的调用点随新签名传 gs（flow 缺省体 + `MandateV1Strategy.decide_shop_screen` 覆写体——sim 回放/序列锁消费的正是覆写体） |
| `strategies/impl/mandate_v1/entry.py` | **不在本批文件面**（全仓 grep 无 decide_* 契约调用点；prep 决策链参数面归 turnstate-retirement 辖——该迭代已收尾落 HEAD，无残留冲突） |
| sim / 回放（`sim/cw_replay.py` 等） | 驱动器路径自动随批；sim 引擎不调 pick 入口、不建模 prep_obs（prep 面 sim 不可达，flow/README §2.3 sim 消费面注记 + §2.4 归因域限定）→ sim 侧改动收敛于驱动器内调用点 |
| `kernel/cw_strategy_session.py` | `prep_obs_frame` 槽删除；`strategy_state_of` 等访问口不动 |

实现位分布申报（各入口的实现位置，切换线按此覆盖）：`decide_prep_screen` = `bridge.py` 覆写体（唯一实现）；`decide_shop_action` = `flow.py` 缺省实现 + `mandate_v1/shop.py` 本体（已 gs-first 零改动）；`decide_encounter` = `flow.py` 缺省体 + `bridge.py` 覆写体（**生产在用**）；其余 pick 入口 = `flow.py` 缺省实现。

测试仓（sr-od-test）随批：契约形状锁（成员计数与签名形状）、单帧锁构造翻新（断言对象不变——本批输出载体不变）、帧类写点守卫锁（prep_obs 写点改名涉及项）、handler 级行为锁（§2.6）。

### 2.6 验证

- **主凭据（可出事面的直接覆盖）**：
  1. **decide 层语义锁**：单帧锁构造翻新后语义断言对象不变；invest 拆分同帧对照（同槽产物 → 同 PickEvent）；encounter 入口 `encounter_refreshed_in_visit` **四格对照**（首调 False / 累计闸命中后建议降格 / 刷新重决策 True / **重入重走首调复位 False**——各格与改前逐返回相同）。
  2. **handler 级行为锁**（fixture_controller 流程测试，逐 handler 剧本：观察帧 → 写槽 → decide → 点击断言）：专锁 encounter **四格**（首调 / 累计计数命中闸「建议刷新但本局已用」/ 刷新后重决策 / **重入重走首调复位 False**）与空选项分支（不调 decide）；逐 handler 锁「每次决策恰以当次观察产物为单源」（§2.2-c 结构防线的回归化）。
  3. L1 快速集全绿 + 直接受影响域点名；收口 L3 全量一次。
- **旁证（辖域局限显式申报；工具 = 现行可执行形态）**：改前/改后各跑现行回放（`python -m sr_od.application.currency_war.sim.cw_replay` 的 `--run/--rounds` 面）全 run 输出落盘 + 逐轮 plan 串文本 diff——仅覆盖 shop 驱动器路径（`decide_shop_action` 签名切换）；对 pick handler 链、payload 活写端、路由清点、prep_obs 迁移**结构性零覆盖**（sim 不调 pick 入口、不建模 prep_obs）——旁证非主凭据，防「空真当验证」。注：旧 `--diff` 分歧对比模式已退役（`sim/cw_replay.py` 模块头在册），strategy-work §4 所引 `cw_replay --diff` 条目与现行工具失同步 = 既有文档债，非本批辖。
- **终验 = 实机一局 smoke**：预测锚点 = 决策迹（现行载体 = `kernel/cw_decision_trace`；其前身的 decisions 流写入端已随删除波 1 物理退役、在册禁复用）与改前同难度局对照无行为性分歧（识别噪声照旧）；候实机窗口执行，登记进度树——不阻代码收口，**阻迭代收尾**。
- **live 可观测性变化申报**：新写端使 journal 行量增加、`write_seq` 位移（下游 `ChannelSig.group_id` 字符串形态随 `gs.write_seq+1` 变化）、快照行 gs_prov 出现新域行；路由清点因「已 None 跳过」（§2.3）每槽每「在屏→离屏」转换至多一行，**交回重入型 handler（supply/invest）的识别瞬态轮可产生「清点 + 重写」多对行**（重入链形态使然，非异常）——digest 对照按此形态预期，勿以单一上界误判；决策面不受影响。**快照 restore 面不对称申报**：encounter/supply payload 升级后，restore 侧仍循 shop 手写重建先例不扩展——两 payload 经「其余域直透」落 dict（现役消费面 = 回放 shop 驱动器，不受影响）；该判读面边界随正本批在 fields.md §8.1-8.5 结构符号指针节申报。
- **sim 可观测性声明**（策略工作 §4 纪律）：本批改契约签名与数据载体层，sim 决策面（decide_shop_screen 驱动器 → decide_shop_action）可见且输入零变化；prep 屏编排域 sim 结构性不可达。不跑 sim A/B（无可比行为差异，A/B 无对象）。

### 2.7 关键取舍

- **载荷入容器 vs 保参（结构统一）**：用户裁定入容器。附加依据：容器由此成为决策输入的单一审计面（回放/判读 dump gs 即重建「策略当时看见什么」——前提 = 离屏机制真实运转，见 §2.3）；与商店牌面入容器、备战观察 state 槽退役的既定演进同轨（载体正本 = flow/session.md，契约正本 = flow/README §2.2）。代价 = 暂态数据进持久容器——由域规则（离屏置 None）+ 唯一写者 + 在屏前置守卫 + 单源纪律兜住。
- **encounter「已用」为何新增 per-visit 字段而不读累计计数**：累计计数的语义是「本局曾刷过」，入口旗标的语义是「本访问已刷过」——前者在第 2+ 节点首调即真，产生 refresh 旗标/reason/选择 idx 的可读分歧（基线核 `cw_events` 刷新建议枝 True/False 两枝 idx 可分叉）。逐字节保真只有 per-visit 位一条路；语义统一（两屏旗标口径归一）是行为批议题，本批不解决（§1.3 登记）。
- **prep_obs 为何豁免离屏清点**：现状 session 槽即从不清空，读者纪律（备战访问内消费）已兜住陈旧性；并入 payload 家族需新增 live 清点写端（行为面扩张）且与覆盖嵌套结构纠缠（§2.3 论证）。豁免 = 零行为 + 最小机制。
- **typed option 直接入槽 vs 槽存原始元组由策略侧转换**：入槽（单源，无二次派生；encounter/supply 现存元组形状本就与 typed option 不同源并存，正是双源病灶）。代价 = 两域形状升级 + 域版本 bump，一次性。类型名沿用现符号（`EncounterPayload`/`SupplyPayload`），不改名。
- **kernel 纯函数签名不动**：判据层（decide_event 族）是纯函数，输入来源本就该由调用方组装；动它 = 把载体重构外溢进判据层，违背「形状批零行为」边界。
- **离屏机制为何走路由点而非 handler 出口**：handler 出口清点存在漏 path（overlay 可经外循环分支/中断弹窗等非常规路径退出，漏清 = 审计面陈旧）；路由挂点是每轮分发前的固定单点、取值规则全覆盖（§2.3 三定义），绕行路径（早退/未知兜底）的下轮补清语义已在册且无害。代价 = 清点时机与 handler 访问结束非严格对齐（先清后终的窗口内槽已 None）——该窗口内无读者（访问已终），无害。

### 2.8 落地依赖与在飞冲突面

**已满足前置**：execstate-dissolution（6/6 done + 正本清零，commit ee1f4e337）——其 #4–#6（ExecState 旗标删除、读点收口、容器计数写端）已全部落地，本批 encounter「闸留 handler（读累计计数）+ per-visit 位进入口」的分工即建在其落地现状上；无残留同文件在飞面。对账义务移入落地：3.4 阶段完成判据含「encounter 刷新链与 execstate 落地现状对账核对」（见 landing）。turnstate-retirement 落码阶段已收（阶段 1/2 + 正本批落 HEAD 7b50d690f/170d8366f/b6e88a902，其工作树在飞改动已入 HEAD）。

在飞前置**按阶段文件面拆解**（一刀切「收尾」前置会误伤零交集阶段）：unified-obs 3.4 落码收存在传递链——其 3.4 依赖其 3.3、其 3.3 完成判据含候窗实机验证期，故 3.2/3.3 开工实际受该链传递阻塞；处置 = 开工前与 unified-obs 协商二选一：解耦其 3.3 实机验证与 3.4 落码（验证期并行落码），或本批 3.2/3.3 排其候窗后——本设计不预设协商结果，落地排期以协商为准；若其实机验证产出落码回改，按在飞冲突协议重排本批受影响阶段：

| 阶段 | 前置 | 依据（文件面交集） |
|---|---|---|
| 3.1 增量槽位面 | 无 | 本阶段面 = `kernel/cw_game_state.py` + `operations/cw_loop.py` + 测试，与 unified-obs 剩余阶段面零交集 |
| 3.2 备战线切换 | unified-obs-reconcile 3.4 落码收 | `cw_screen_prep.py` 相交 |
| 3.3 商店线切换 | unified-obs-reconcile 3.4 落码收 | `cw_screen_buy_cards.py` 相交（其 3.4 旧安灯退役批） |
| 3.4 pick 族切换 | 无在飞相交 | `bridge.py` 相交面已随 turnstate 收尾消解 |
| 3.5 / 末阶段 | 全部落码阶段收；**末阶段（正本更新）另须 unified-obs 的正本更新批先收**（flow/README、fields.md 文档面顺序约束） | 文档面 |
