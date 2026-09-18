# strategy-input-unification 对抗审查报告（attack5，新一轮独立审查）

> 审查对象 = 本目录 design.md / landing.md / README.md（r4 消解后当前稿）。
> 审查方式 = 无前提对抗（干净上下文、无预设焦点）；判据源全部直调复核（禁转述）：
> iteration-design.md（四硬规则 + §7 三核 + §3 阶段七件 + §3.2 正本清单）、strategy-docs/00_framework.md、01_math_framework.md、
> fields.md（§2.1/§2.2/§2.4/§2.5/§3.4 全节/§3.7.1/§4.2/§8.8/§9.4 逐节直读）、flow/README.md（§1-§5 全读）、flow/session.md（§3/§5.1）、
> flow/projection_contract.md、strategy-docs 13/22/23/25 篇 + 16 号稿 + strategy-docs/README、screens/ 全目录（prep/shop/encounter/supply/
> invest 双篇/megastar/partner/planner/bookcard/wish_trial/box_pick/README）、game_state/README + action-logic-state + logic-updates/open-bookcard、
> 代码真值 as-built 直读体（cw_strategy.py、flow.py、mandate_v1/bridge.py、kernel/cw_game_state.py〔_PAYLOAD_DOMAINS/DEFAULT_GS_SCHEMA/
> leave_screen/carry/game_state_of/EncounterPayload/SupplyPayload/node_screen_refresh 域〕、cw_strategy_session.py、cw_prep_actions.py、
> cw_equip_wear_plan.py、cw_events.py（decide_event 族与 option dataclass 全读）、cw_decision_trace.py、cw_loop.py（分发臂/dispatch/stop_at_prep 全段）、
> cw_screen 十 handler（decide 调用点/写点/防御路径/刷新链逐文件实读）、obs/cw_observation.py（leave_screen 调用位）、sim/cw_replay.py、
> sim/cw_sim_nodes.py、cw_screen_state.py（PREP_DIRECT_EXIT_SCREENS））、在飞迭代三份（execstate-dissolution / turnstate-retirement /
> unified-obs-reconcile 的 README/design/landing + 正本清单）、AGENTS.md §8-§11、strategy-work.md §6、cw_screen_state/entry 链。
> 行号 = 审查时点工作树坐标（HEAD = 5b83cdbb5；设计稿引用的四个 commit ee1f4e337/7b50d690f/170d8366f/b6e88a902 经 git cat-file 核实存在）。
> `prep_obs_frame`（全仓 81 处）与 `decide_invest`（全仓 61 处）做了 grep 普查逐条归类；正本侧另按 decide_* 全族 + refresh_used + 九接口计数词
> 做了**全正本树**（changes/ 除外）普查——本轮 blocker 即出自该普查（见 B1）。
>
> **发现计数：8 条 = blocker 1 / major 1 / minor 6。**无和稀泥结论；三核均有攻击记录，核一/核二有发现，核三零发现。

## 发现清单

### B1｜blocker｜landing.md「正本更新清单」× screens/ 画面篇族 + game_state/README.md + strategy-docs/README.md（硬规则 4「全量同步复查」失守；attack4-B1 同类残留，面积更大）

正本更新清单的本批漏单面经**全正本树普查**（changes/ 除外，对 decide_* 全族符号 + refresh_used + 「九接口/pick 族 9」计数词逐文件 grep）核实为 **14 份正本文档 + 1 处枚举行**——全部在本批落地后过期、全部不在清单。按稿施工，末阶段「清单清零；正本与实现一致」（landing 末阶段完成判据）必然落空，同 attack4-B1 判 blocker 的同一判据。

逐文件证据（全部直调核实，锚为审查时点行号）：

1. **screens/encounter.md**（← 3.4）：L12「决策入口 = 契约 `decide_encounter(options, gs, session, config, refresh_used)`」——签名/形参双重过期（新契约 `(gs, session, config)`、`refresh_used` 退役）；L28 调用形状伪码 `pick = decide_encounter(options, game_state_of(session), session, config)`；L31/L37 刷新腿「带 refresh_used=True 重决策」流程句（入口旗标改读容器位）。
2. **screens/supply.md**（← 3.4）：L12「契约 `decide_supply(options, gs, session, config, refresh_used)`」；L29/L31 调用形状伪码（`refresh_used` 实参消亡）。
3. **screens/invest_strategy.md**（← 3.4）：L3/L14「`decide_invest('strategy', ...)`」；L35 调用形状伪码——`decide_invest` 拆分后符号消亡。
4. **screens/invest_env.md**（← 3.4）：L3/L12/L24 同上（`decide_invest('env', ...)`）。
5. **screens/megastar.md**（← 3.4）：L12「契约 `decide_megastar(options, gs, session, config)`」（新签名 `(gs, session, config)`，options 转容器槽）；L3/L22 同锚。
6. **screens/partner.md**（← 3.4）：L12 契约签名行；L33 流程伪码 `decide_partner(GameState 视图)`。
7. **screens/planner.md**（← 3.4）：L12 契约签名行；L26 流程伪码。
8. **screens/bookcard.md**（← 3.4）：L11「契约 `decide_star_tome(factions, gs, session, config)`」；L22 调用形状伪码。
9. **screens/wish_trial.md**（← 3.4）：L12 契约签名行；L23 调用形状伪码。
10. **screens/box_pick.md**（← 3.4）：L12「契约 `decide_box_card(names, gs, session, config)`」（names 转容器槽 `gs.box_card_names`）；L25。
11. **screens/shop.md**（← 3.3）：L40 调用形状伪码 `action = strategy.decide_shop_action(session, config)`——3.3 切 `(gs, session, config)` 后过期。
12. **screens/README.md**（← 3.4）：L77「决策 = pick 族 `decide_invest`」（符号拆分消亡）；L107「决策 = pick 族九接口 + decide_box_card」——**计数句 9→10**。
13. **game_state/README.md**（← 3.1/3.4）：L83 域成员枚举行「节点屏刷新计数域(node_screen_refresh) | encounter_refresh_used / supply_refresh_used / env_refresh_used / strategy_refresh_used」——`encounter_refreshed_in_visit` 入该域后枚举不自含。
14. **strategy-docs/README.md**（← 3.4）：L33 篇目行「13 | pick 族薄判据：**九接口**决策规格 + 事件面目录」——计数 9→10。

附注：**sim/sim-wiring.md** L90（node_screen_refresh 域成员枚举）同 G13 类过期面，一并入清单或显式申报不入（该篇属 sim 正本，域成员枚举同理不自含）。

依据 = iteration-design.md §3.2（正本更新清单是末阶段唯一消费面，清单清零 = 收尾完成）+ §5-4（design↔landing↔README 全量反查，正本清单在列）+ AGENTS.md §9 双层文档流（正本「永远与代码现状一致」+ 迭代收尾义务）+ attack4-B1 判例（4 份正本漏单 = blocker；本轮漏单面 14+1 处，同类同判）。

**修正方向**：正本更新清单补 14 行（screens/ 篇族 11 份按各自 ← 阶段标注：shop.md ← 3.3，其余画面篇与 screens/README ← 3.4；game_state/README.md 域成员枚举行 ← 3.1/3.4；strategy-docs/README.md 篇目行 ← 3.4），sim/sim-wiring.md 一并补行或显式申报豁免理由。

### M1｜major｜landing.md「正本更新清单」已列行的节范围失准（attack4-B1/M1 修复不彻底的四处残留）

清单已把这些文档列入，但各行的**节范围括注与 ← 归属**罩不住本批造成的实际过期锚——按行面执行末阶段后正本仍残留旧口径（attack4-M1 同类，其判 major）：

1. **game_state/action-logic-state.md 行**：「（动作 op 写入面涉及新槽/新字段的行）← 3.4」——该篇真实过期锚是 **L50**「另有一个非容器落点：备战观察帧……宿主 `session.prep_obs_frame`」：①宿主换名是 **3.2**（prep_obs 迁移）造成，← 3.4 归属错；②3.2 后 `gs.prep_obs` 是**容器**（非 Field）字段，该行「非容器落点」的定性整体反转，需改写而非机械改名——「新槽/新字段」的括注既不点名 L50 也提示不了定性反转。
2. **game_state/logic-updates/open-bookcard.md 行**：「（星徽秘典选卡逻辑写面涉及 decide_star_tome 输入面的行）← 3.4」——**值对标签错**：直读该篇全篇（47 行），它是**书册卡道具（OpenBookcard 动作）逐动作逻辑态篇**（篇名「书册(OpenBookcard)逐动作逻辑态」；§1 = 点开占席书册卡道具、§6 锚 = `PrepActionExecutor._open_bookcard`），**全篇零处 decide_star_tome**（星徽秘典选卡 = `CwScreenBookcard`/`decide_star_tome`，另一实体，screens/bookcard.md 辖）。该行的范围描述指向一篇中不存在的内容；该篇真实过期锚 = **L13**「宿主 `session.prep_obs_frame`；写口 = `_project_prep_obs` OpenBookcard 分支」（3.2 宿主换名）。
3. **flow/README.md 行**：「成员计数句三处（§2 卷首「契约形状」段、§2.1 四身份表契约行、§2.2 契约接口全景表……）」——漏 **§1 四层结构总图 L32**「pick 族 9 接口与冷建/结算收编仍由 flow.py 中间 ABC 承载」：第四处计数句（3.4 后 pick 族 = 10），不在三处枚举内。attack4-M1-1 的修复按「三处」枚举收口，未做计数句全篇普查（strategy-work §6 泛化步未走完）。
4. **strategy-docs/25_event_overlays.md 行**：范围 =「十入口对应画面……的输入面句；选择装备……零改动」——漏该篇**篇头 L4**「九接口决策规格 = 13_pick_family.md」计数句（3.4 后 = 十接口）。同轮已把「星徽秘典四选一」改成本篇 §1 实名（attack4-m4 部分消解），但计数句面未及。

依据 = iteration-design.md §5-4 + §3.1（末阶段判据 = §3.2 清单清零）+ attack4-M1 判 major 的同族先例。

**修正方向**：①action-logic-state.md 行改「← 3.2/3.4」并括注补「L50 备战观察帧宿主句改写（非容器落点定性随 gs.prep_obs 入容器反转）」；②open-bookcard.md 行改写为「书册卡（OpenBookcard 动作）逻辑态篇：L13 备战观察帧宿主句改指 gs.prep_obs ← 3.2」（删 decide_star_tome 误述）；③flow/README 行改「成员计数句四处（§1 结构图 pick 族 9 接口行 + §2 卷首 + §2.1 表 + §2.2 表）」；④25_event_overlays 行补「篇头九接口计数句」。

### M2｜minor｜design.md §1.3 × §2.2-a：新域键计数自相矛盾（值对标签错，攻击纪律重点错误类）

§1.3「解决」段写「②决策输入数据全部经容器承载（**新增 9 域键** + 升级 2 域形状 + ……）」；§2.2-a 写「**8 个新域键**（#5–#12，各自独立域键）+ 2 个变域 bump（#3/#4）+ `node_screen_refresh` 域版本 +1」。直数槽位表：#5–#12 恰 8 个新槽 = 8 个新域键；`encounter_refreshed_in_visit` 入既有 `node_screen_refresh` 域（bump 非新键，§2.1-4 明确）；`prep_obs` 明确不占域键（契约 e）。§1.3 的 9 无从着落——多计 1。另 ② 的枚举漏列 `encounter_refreshed_in_visit` 新字段（它是 refresh_used 退役的承载，属决策输入容器化的一部分，仅在 §2.1-4 出现）。
**修正方向**：§1.3 改「新增 8 域键」，枚举补「+ encounter per-visit 刷新位新字段（node_screen_refresh 域 bump）」。

### M3｜minor｜design.md §2.8 在飞冲突面两处依据失实（依据就地标注硬规则 1）

1. 3.3 行依据列「`mandate_v1/shop.py` 相交（**其落码批注释项**）」不可解析：unified-obs-reconcile 剩余落码阶段（3.4 旧安灯退役批）文件面 = run_state/cw_screen_prep/cw_screen_buy_cards/cw_shop_action_ops/telemetry 两篇/test 注释，**无 mandate_v1/shop.py**；其 grep 词表（exec_fail/classify_spend_unit/plan_gold_flow/_spend_unit_ 等 10 词）对 mandate_v1 全包 grep **零命中**；turnstate-retirement 已收尾（README 3/3 done + 正本清零）非在飞。「其落码批」指代悬空，按稿无法核出该「相交」来自哪个在飞批。3.3 的前置本身仍成立（cw_screen_buy_cards.py 相交真实），但依据列一半失实会误导排程核对。
2. 末阶段行括注「（flow/README、**session.md**、fields.md 文档面顺序约束）」——session.md 不在 unified-obs-reconcile 正本更新清单（其清单 10 行无 session.md；全目录 grep 零提及），对 unified-obs 正本批的文档面顺序约束不成立；turnstate 正本批已收尾亦无顺序约束可言。
**修正方向**：①3.3 依据列改「`cw_screen_buy_cards.py` 相交（其 3.4 旧安灯退役批）」，shop.py 项删除或改注「turnstate 阶段2 注释面，已收尾消解」；②括注删 session.md。

### M4｜minor｜design.md §2.5 调用方迁移契约：invest 双 handler 的局外防御路径漏申报（「实现者无需再设计」缺口）

§2.5 对 `cw_screen_planner.py` 防御路径有显式行（「局外 kernel 直调，签名随改，kernel 直调保持」），但同型面在 **cw_screen_invest_strategy.py**（L405-418：无 match → 裸 `GameState` 构造 + 直调 kernel `decide_event`）与 **cw_screen_invest_env.py**（L304-310 同构）各存在一处，design/landing 全文未提。新契约下这两处语义需申报定死：无 match → 无 session 容器 → **不写槽**、kernel 直调保持（planner 先例平移）；实现者按 §2.5 首行「OCR 产物写本屏槽 → 以 (gs, session, config) 调 decide」字面执行会在此撞「无 gs 可写」的未定义态。
**修正方向**：§2.5 首行补一句「invest_strategy/invest_env 的局外无 match 防御路径同 planner 先例：不写槽、kernel `decide_event` 直调保持」。

### M5｜minor｜design.md §2.1-4 encounter 窗语义括注机制错位

「窗语义：True 后若重读失败未重决策，位残留至本访问终（**路由清点离屏兜底，§2.3**）」——`encounter_refreshed_in_visit` **不在** §2.3 十行属屏映射内（映射 = 10 个 payload 槽；该字段随 §2.3 只享受 prep_obs/shop 两豁免申报，未入映射），路由清点不清它。残留位的实际复位机制 = 同句后半「下访问新实例起点写 False 复位」；括注把复位归给一个不管该字段的机制，读者据此去 §2.3 找兜底会落空。行为面无影响（残留窗内无读者），属规格自洽问题。
**修正方向**：括注改为「（残留窗内无 decide 读者；复位 = 下访问新实例 __init__ 写 False，不经 §2.3 路由清点）」。

### M6｜minor｜landing.md 3.2/3.4 锚普查判据的类别集不完备

3.2 判据「`prep_obs_frame` 符号名（含注释形态）**全仓逐条归类**——每条锚标注承载（本阶段换源/改指）」、3.4 判据「……等 9 符号名全仓逐条归类——契约调用点/kernel 纯函数/入口内部委托/纯注释锚**四类**」。实测全仓 grep：`prep_obs_frame` 81 处中约半数落在**其他迭代的 changes/ 过程件**（2026-09-15-prep-single-action-contract 的 design/attack×13、2026-09-16-prep-visit-op 等——历史对抗引文与已定稿设计句），`decide_invest` 61 处中同类占比可观。这些文件是已收尾迭代的历史档案，既非「换源/改指」对象也不属 3.4 四类中任一类——按现判据 worker 只能自造类别或误改历史件（后者违过程件冻结惯例）。
**修正方向**：两判据各补一类「已收尾迭代过程件/历史档案锚：登记不承载（changes/ 寿命随迭代，禁回改）」，或把普查范围显式限定为「src + 正本树（changes/ 除外）+ 本迭代目录」。

### M7｜minor｜cw_strategy.py 契约计数句随批变化无显式承载

模块头 L13-16（「分画面决策入口 11 = abstract 12……保留总成员 13」）与类 docstring L72-74（「备战 1 / 商店 1 / **pick 族 9**」）的计数句随本批变 12/13/14 与 pick 族 10。所在文件虽在 3.2/3.4 文件面（随编辑自然触及），但：3.4 锚普查按 decide_* 符号名 grep **不命中计数句**（「pick 族 9」无符号），正本清单辖正本不辖代码注释——attack4-M1 确立的「计数句需逐处点名」纪律在代码侧无承载申报。
**修正方向**：landing 3.4 范围补一句「`cw_strategy.py` 模块头/类 docstring 契约计数句随批同步（11→12 / abstract 13 / 总成员 14 / pick 族 10）」。

### M8｜minor｜README.md 进度行「复审待新报告」× 定稿门槛表述

README 进度「设计对抗:进行中(……r4=……已逐条消解,复审待新报告)」——iteration-design §6 定稿门槛 = 「攻击收敛 + 试读过」，收敛判据 = 零发现轮；本行把收敛条件表述为「待新报告」（有新报告即收敛？还是待零发现轮？）两读。流程进度的下一状态判定依据不唯一，README 作为进度单一源应可判定。
**修正方向**：改为「复审待零发现轮（或试读过）后定稿」。

## 核三（治本）零发现 + 实际攻击过的面清单

- **§1.2 归层结论**：直调核实争议面确在「形参从哪进来」的约定层——12 入口的数据本体每帧同源（pick 族 handler 均以同帧 OCR 产物直传，`game_state_of` 容器单例现行在用），非表示/语义层问题；「契约签名形状从未立约定」与 ABC/flow/bridge 三层现状相符。
- **§2 治本性**：本批 = 一次性立死「签名形状 + 输入承载」两条约定（12 入口一表收口），非逐 handler 症状补丁；与 shop 黑板容器化、备战 state 槽退役的既定演进同轨（§2.7 取舍一有在档演进指针）；终态方向（构造注入/零参/session 解散）显式登记为后批 = 战术切片带排期，非无限期挂账——「同族修法第二件升架构级」的跨件半问由本批的约定级收口满足。
- **行为零变化核心主张**：经五专攻面独立复验——①新写端量级（per-visit False 写/刷新 True 写/路由清点已 None 跳过，journal/write_seq/gs_prov 形态差 §2.6 已申报且与 `_swap`/`carry` 实码语义相符）；②路由清点时序（挂点唯一插入位 cw_loop.py:1818-1821 实证；stop_at_prep 早退屏 = PREP_DIRECT_EXIT_SCREENS{'货币战争-备战','货币战争-备战-免战'} 均非映射属屏，绕行无害论证成立）；③refresh 旗标分支等价（encounter 首调缺省 False/重决策 True/闸读累计计数三分支逐位对码 cw_screen_encounter.py:304-342/439-470；supply 派生式逐字节同构 cw_screen_supply_node.py:206-213/230-232；kernel `decide_encounter` True/False 两枝可分叉实读 cw_events.py:670）；④prep_obs 读者封闭性（4 写点/3 读点全集 grep 复核，与 §2.2 #1 白名单一致）；⑤每阶段切换线独立可绿（3.1 纯增量恒 None no-op、3.2/3.3/3.4 各自交付态签名-调用点-测试自洽、串行依赖共用文件面成立）——均未发现行为面缺陷。

## 已攻未破的其他面（零发现申报，列面自证攻击密度）

- 现状症状逐条对码：三形状并存、supply/encounter 旗标语义、invest 两画面一方法、`decide_invest` docstring stub 句过期、选项双源（`gs.shop` 活写在产 / encounter+supply 活写端缺位、live `leave_screen` 恰两处均 shop 域 + sim 合成口两处）、payload 现形状——逐条属实。
- `_PAYLOAD_DOMAINS`/`leave_screen` 守卫面（attack4-m1 修复句与实码一致：shop 保留映射内、跳过落点在挂点、leave_screen 无条件写语义不动）；`carry` None 跳过先例属实（cw_game_state.py:3126-3132）。
- 属屏映射十行逐行对分发臂核实（含反直觉三行与「武装箱弹窗 → CwScreenArmoryBox 无 decide」注）；`PrepObservation` set/Point/BenchChar 非 JSON 形状、typed option 全族 JSON 安全（cw_events.py 数据类逐字段）、`EncounterOption` 等定义位属实。
- 契约成员计数 12→13/13→14 与 ABC 实读相符；统一签名表与返回类型逐行对码；B4 收缩申报与 session.md §5.1/`strategy_state_of` docstring 口径一致。
- 形式面：landing 六阶段七件齐、通用工程门首节单一定义 + 逐阶段引用（可解析先例合规）、README 模板合规、design/landing 正文无过程叙事、无行号锚；execstate #12-#14/#20、unified-obs 3.4「旧安灯退役批」、fields.md §2.2/§3.4.4/§3.7.1/§8.8、flow/README §2.3/§2.4、session.md §5.1 B4、cw_replay `--diff` 退役在册、strategy-work §4 `--diff` 失同步申报——引用锚抽查全部真实。
- 在飞对账：execstate 6/6 + ee1f4e337、turnstate 3/3 落 HEAD 三 commit、unified-obs 3/5 剩余面（3.4 文件面与本批 3.2/3.3 相交、3.5 正本批顺序约束）逐一核实；3.1/3.4 与 unified-obs 剩余面零交集成立。
