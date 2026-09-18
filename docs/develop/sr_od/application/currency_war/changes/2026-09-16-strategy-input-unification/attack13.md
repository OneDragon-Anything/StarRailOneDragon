# attack13 —— 策略器决策输入统一 · 独立对抗审查（r13）

> 审查对象：本目录 design.md / landing.md / README.md（当前工作树版本）。
> 方法：三核（无前提 / 规范遵循 / 治本）+ 行为零变化申报专攻；数值/口径/引文/码点全部直调复核（代码读体、正本读节、在飞迭代读 README/landing、commit 哈希 `git log` 直查），符号锚与计数词全仓 grep 普查（`src/` 与 `sr-od-test/` 逐仓跑，正本树含 `docs/game/` 排除 `sources/`；rg 从仓库根会因 .gitignore 跳过 sr-od-test，已逐仓跑）。
> 本轮定位：r12 消解后的独立复审。**非零发现轮**：9 条（blocker 0 / major 2 / minor 7）。

---

## 发现清单

### [B1] major | landing.md 正本更新清单（:92-115）+ design.md §2.3 | 路由清点挂点的正本家 `flow/outer_loop.md` 不在预登记清单，三重兜底机制对该新增面全部产出假零

**发现内容**：本批三大交付之一「路由点陈旧清点挂点」（design §2.3：挂点位置、属屏映射、三定义、早退/未知兜底两路径语义）是**外循环每轮固定步骤的结构性新增**，其正本家 = `flow/outer_loop.md`（该篇定位 =「外层循环：两阶段身份分发、路由、轮次推进、停机/遥测钩子」，flow/README §3 导读；§1 结构图 ：18「阶段一 画面身份分发（§2.2）→ 命中即派发并交回」与 §2「画面识别与分发」描述的正是挂点插入位置的前后结构）。落码后该篇与实现不一致（缺挂点步骤、缺新槽离屏机制句），但：①正本更新清单 flow/ 行只列 README/session/projection_contract 三篇，**无 outer_loop.md 行**；②末阶段词表（`decide_` 前缀/`refresh_used`/`encounter_refreshed_in_visit`/`prep_obs_frame`/`PickBoxCard`/五计数词）对该篇的挂点新增面**零命中**——唯一 `decide_` 命中在 ：91（`decide_prep_screen` 入口消费 kernel 判据的描述），批后该句仍真，归类「不辖」，不触发任何更新；③新增面核对单虽有「路由清点与属屏映射」项，但可对账的预登记行只有 fields.md §2.2 行的「`_PAYLOAD_DOMAINS` 属屏映射扩展」（域规则面），**外循环结构面无预登记行锚**。三条兜底全空 → 末阶段「普查对账表零待更新项 + 正本与实现一致」对这处结构变化产出假零。旁证：grep 实证 `outer_loop` 在本迭代 design/landing 全文零出现，unified-obs-reconcile 的 changes 文档亦零出现——无任何在飞批次代管该篇的本次更新。

**修正方向**：正本更新清单补行「`flow/outer_loop.md`（§1 结构图挂点步骤、§2 识别与分发节补路由清点挂点句与新槽离屏机制指针）← 3.1」；核对单「路由清点与属屏映射」项括注双锚（fields.md §2.2 域规则面 + outer_loop.md 结构面）。

### [B2] major | design.md §2.1-4（:65）+ landing.md 3.1（:9）/ 正本更新清单 | 新写端的 journal.md §6 申报面缺席：write_logic 豁免类与路由清点 sig 口径无纸面落点，journal.md 不在清单且词表全零命中

**发现内容**：本批新增两类容器写端，均触及 `game_state/journal.md` §6「写入口 API 面与硬约束」的纸面契约，但该篇既不在正本更新清单、核对单四项亦不含，且 grep 实证 journal.md 全篇对词表全部词项（`decide_`/`refresh_used`/`encounter_refreshed_in_visit`/`prep_obs_frame`/`PickBoxCard`/计数词）**零命中**——普查机制结构上够不到它：

1. **`encounter_refreshed_in_visit` 走 write_logic**（design §2.1-4 明示「渠道 = logic_action 动作上报族」）。journal.md §6 :138-144：「write_logic **仅限设计显式申报豁免的写端**（事件屏 chosen 族/局级事实写端/**刷新计数组**/效果写端申报行/动作发射写点 receipts/账本→字段桥），**其余禁走此口**」。新字段是 **per-visit bool 位**（首调前置写 False × 两路径 + 刷新发射前写 True），语义是「访问内一次性旗标复位/置位」，不是「计数」——豁免类「刷新计数组」字面是否覆盖 bool 位，是实现者必须自行裁定的语义选择（硬规则 2「实现者无需再设计」的违例形态）；且「首调前置复位」作为一类 write_logic 用户（决策路径前置段直写，非发射型）在豁免面无归属类。设计未申报「豁免类扩 bool 位」或「新立『访问内旗标』类」，journal.md 无从跟上。
2. **路由清点挂点经 leave_screen 写入**（渠道①，无需豁免），但 landing 3.1 仅申报「写入口经 leave_screen 同口径带具名 sig」——**family/mode/actor 三元未钉死**。现行唯一 live 离屏先例 = CloseShop 逻辑腿（`cw_game_state.py:2031-2033`：`family='obs', mode='read', actor=沿写链`），「同口径」读者需自行考古该先例；挂点 actor（CwLoop，:324 在册）与 obs/read 口径应一句话定死。
3. journal.md §6 :146-147 硬约束③「域准入白名单（逐格以实码写点全集核源，禁凭概念断格）」自称「机器面=测试锁」——本批写点全集变化（10 域路由清点 + 8 新槽离屏合法化 + 新旗标两写点）后，该白名单的纸面/机器面均需随批对账，landing 3.1/3.4 的测试判据均未点名。

**修正方向**：①正本更新清单补行「`game_state/journal.md` §6（write_logic 豁免类补 per-visit 旗标写端申报行；路由清点 leave_screen 行 sig 口径 = obs/read/actor=CwLoop 先例指针）← 3.1/3.4」；②design §2.1-4 一句话钉死豁免类归属（如「豁免归属 = 刷新计数组域类扩『节点屏访问内旗标』子类」）；③landing 3.1 判据补「路由清点写行 sig 形态与 CloseShop 腿先例一致」断言。

### [m1] minor | design.md §2.2（:89）| 「配套契约（六条）」实列 a–g 七条——计数标签与内容错位

**发现内容**：:89 写「**配套契约（六条）**」，其下实列 **a**（gs_schema 申报 :91）/ **b**（离屏机制 :92）/ **c**（瞬态槽三分语义 :93）/ **d**（选项数据单源 :94）/ **e**（prep_obs 迁移附注 :95）/ **f**（新槽注释 :96）/ **g**（选项类宿主与 import 方向 :97）——**七条**。b 虽为 §2.3 指针仍是独立列项。这是「值对标签错」类错误：实现者按「六条」清点会认定漏了一条或自己多读了一条，契约完备性核对失去锚。

**修正方向**：改「配套契约（七条）」；或把 b 并入 §2.3 指针句、a–f 保持六条。

### [m2] minor | design.md §2.3 挂点时序①（:106）+ landing.md 3.1（:9）| 早退轮无害性论证两处失准：「下轮正常路由补清」在该 run 内不存在；design↔landing 对早退与识别的先后口径相抵

**发现内容**：①design §2.3 与 landing 3.1 均以「下轮（正常路由）补清（陈旧窗口 = 单轮）」论证 `stop_at_prep` 早退轮不清点的无害性。直调 `cw_loop.py:1754-1756`：早退 = `round_success`（「已到可交还退出调度的备战态」）——**CwLoop 该次运行就此终止**，退出链接管，run 内不存在「下轮」；无害的实际承载 = 早退屏（PREP_DIRECT_EXIT_SCREENS = {备战, 备战-免战}）非映射属屏、无 decide 消费、loop 终止后无任何读面、后续新局新容器——结论侥幸成立，依据锚不实（硬规则 1）。②design §2.3 写「stop_at_prep 早退（**识别屏名** ∈ PREP_DIRECT_EXIT_SCREENS 即 return，**其自调的识别**不经过挂点）」——早退判定 :1754 本身就是一次 `get_in_match_screen_name` 识别；landing 3.1 却写「早退**发生在识别之前**，早退轮**无识别结果**不清点」——同一机制两文档口径相抵（design = 早退含自调识别；landing = 早退先于识别）。

**修正方向**：①两处无害性依据改为「早退即本轮 round_success 终止 loop，无后续消费面；容器随局生命周期隔离」；②landing 3.1 改为与 design §2.3 同口径（「早退轮的自调识别不经过挂点，挂点不执行」）。

### [m3] minor | design.md §2.3 豁免与保留（:120）+ landing.md 3.1 | shop 路由清点豁免的编码形态未定死，实现者选错形状即与 CloseShop 既有清点构成双写端

**发现内容**：「shop **保留在映射结构内**……但**标记为路由清点豁免（挂点跳过它）**」——「标记」的机制形态（属屏值哨兵 / 并行豁免集 / 值为 None 等）未定。这不是纯编码风格问题：挂点通用规则是「清属屏 ≠ 当前屏的槽」，若实现者把 shop 的属屏填成具体屏名而无显式豁免通道，则备战/开商店交替识别轮会把 `gs.shop` 经挂点清掉，与 CloseShop 逻辑腿、prep 相位锚 miss 分支两处既有清点形成**三个清点写端并存**（后者是本批 §2.3 自己论证要避免的形态），且开店中段 shop 被清 → `decide_shop_action` 在屏前置抛错 = 生产链断裂。设计意图明确（豁免必须结构性保证），只差一句话钉死编码。

**修正方向**：§2.3 补一句「豁免编码 = 映射值域外的显式豁免集（如 `_ROUTING_CLEAR_EXEMPT = {'shop'}`），挂点按集跳过；属屏值恒为真实建档屏名」。

### [m4] minor | design.md §2.6 live 可观测性申报（:157）+ §2.3 已 None 跳过（:105）| 「每槽每访问至多一行」journal 增量上界在识别瞬态失准轮不成立

**发现内容**：「journal 增量仅发生于『真离屏转换帧』，每槽每访问至多一行」隐含识别每轮稳定的假设。反例链：交回重入型 handler（supply `round_retry` :157、表内屏幕的下一轮重分发）期间任一轮识别 miss 或误识为映射外/非属屏键 → 挂点按「未识别 = 清全部十槽」清掉**在访问槽** → 次轮识别恢复 → handler 常规「OCR → 写槽」重写 → 同一访问同一槽产生清/写**多对** journal 行。行为无碍（写槽先于 decide 的单源纪律兜住决策面），但 §2.6 申报该上界用于「轨迹级 digest 对照须知此形态差」的判读预期——按错误上界对账会把识别瞬态轮的合法增量误判为形态异常。

**修正方向**：上界改述为「每槽每连续属屏段至多一行；识别瞬态失准轮可多一对清/写行（handler 重写覆盖，决策面无感）」。

### [m5] minor | landing.md 正本更新清单 game_state/README 行（:98）| §3.3 画面 payload 域行（README.md:87）的三域括注与成员列批后过期，「增 8 新域行」粒度不覆盖该行改写

**发现内容**：`game_state/README.md` §3.3 域清单表 :87「| 画面 payload 域（shop/encounter/supply） | shop / encounter / supply（非当前画面=None） | ①观察 |」——批后该行标签括注与成员列均过期（画面 payload 域 = 11 域：三旧域 + 8 新 opts 槽，同属 `_PAYLOAD_DOMAINS` 离屏例外族）。清单行指令为「**§3.3 域清单增 8 新域行**——先例 = execstate 新增 round_ledger 域」：按字面执行是**追加 8 行**，:87 既有行的标签/成员改写不在指令面；词表（域键名不在普查词表，`decide_` 等亦不命中）兜不住。同表 ：83 node_screen_refresh 行已获显式枚举补列指令（「域成员枚举句补 encounter_refreshed_in_visit」），:87 行无对应指令——同表两行处置粒度不一致。

**修正方向**：game_state/README 清单行括注补「:87 画面 payload 域行标签与成员列随 8 新槽扩（11 域口径）」。

### [m6] minor | design.md §2.1 纪律 1（:60）vs screens/op-layer.md（:101/:110）+ cw_screen_encounter.py:418 | 「gs 形参 = 容器单例现引用，禁传裁剪视图」与统一观察架构 decide() 输入口径（strategy_input_state 视图）的张力无裁定锚

**发现内容**：本批把契约钉死为「gs 形参 = 容器单例现引用（game_state_of(session) 同一实例）……**禁传副本/裁剪视图**」。而正本 `screens/op-layer.md` 统一观察架构五段模型写「decide() 策略消费：**strategy_input_state 决策视图 → 策略入口**」（:101）、「decide 的输入 = `strategy_input_state`（kernel/cw_gs_view）产出的 **GameState 视图**」（:110），在飞试点文件 cw_screen_encounter.py:418 lifecycle docstring 同口径（「decide（strategy_input_state → decide_encounter）」）。当前生产路径传裸容器（`:302` game_state_of），两叙事暂不冲突；但统一观察架构批若按 op-layer.md 字面把 cw_gs_view 视图接进 decide 入口，即与本批契约纪律 1 正面冲突（视图 = 适配器产物，非容器单例现引用）。设计对该冲突无裁定（哪个口径赢、视图算不算「裁剪视图」、还是届时修订契约句），也未列入 §1.3 不解决清单——留下跨批契约地雷。

**修正方向**：§2.1 纪律 1 或 §1.3 补一句裁定：「本纪律辖本批交付的契约形参；统一观察架构批落地时 cw_gs_view 视图与本纪律的相容性（视图是否满足『容器单例现引用』或契约改形）由该批裁定，登记不解决」。

### [m7] minor | landing.md 正本更新清单 flow/README 行（:94）+ 3.4 归类桶（:58）| flow/README §2.3「决策输入 = obs（黑板）+ session 容器直读」句批后过期：不在清单行枚举面，普查命中但归类桶无「旧口径描述句」类 → 假零路径

**发现内容**：flow/README §2.3 :95「决策本体 = 纯函数（bridge.decide_prep_frame，**决策输入 = obs（黑板）**+ session 容器直读）」——prep_obs 迁容器后「obs（黑板）」载体表述过期（obs 宿主 = gs.prep_obs，黑板槽已退役）。①清单 flow/README 行的枚举面 =「成员计数句四处（§1/§2 卷首/§2.1/§2.2）：成员计数 13+1、统一签名列、黑板输入列改容器槽位列、兼容裁定句」+ §2.5 行——**§2.3 不在其列**；②该句因含 `decide_prep_frame` 会被 `decide_` 前缀普查命中，但 3.4 的归类桶只有「契约调用点 / kernel 纯函数 / 入口内部委托 / 纯注释锚」四类——`decide_prep_frame`（bridge 内部纯函数，符号批后仍存活）会归「入口内部委托」即**不触发周边 prose 修订**，普查产出「零未承载项」的表面对这句旧口径假零。

**修正方向**：清单 flow/README 行补「§2.3 决策输入句『obs（黑板）』改指 gs.prep_obs ← 3.2」；或 3.4 归类桶补第五类「旧口径描述句（符号存活但周边 prose 随批改写）」并在判据要求该类逐条标注承载。

---

## 零发现核声明

### 核三（治本）：零发现

实际攻击过的面：
- §1.2 归层复核：三形状并存（prep/shop 无 gs、pick 族 4–5 参、invest kind、supply/encounter refresh_used）逐成员直读 `cw_strategy.py:93-187` 确无统一约定先例，黑板模式仅落主入口——「约定层」归层成立；
- §2 修根判读：统一签名约定 + 决策输入单源化容器承载 = 立约定治本，非逐 handler 补丁；§1.3 五项「明确不解决」各有独立闭环、承接出处与后批去向（构造注入/session 解散、pick 输出动作化、帧机制合并、旗标语义统一、payload 内容扩展），非「症状修法无排期」形态；
- 跨件半问：execstate（执行层状态退役归容器）→ turnstate（TurnState 删除）→ 本批（决策输入归容器）同族演进方向一致，本批是既定方向的下一格；§2.4「分表现留缝不实现」已声明缝位（flow.py:468-514 直调确认共享段现状）；
- §2.7 五条取舍对照代码现状复验：prep_obs 豁免论证（session 槽从不清空现状）、kernel 纯函数边界（flow.py:489/:520/:526 委托形态）、路由点 vs handler 出口漏 path 论证、typed option 入槽代价（`cw_game_state.py:613/:620` 元组现形状）——无翻案点。

### 核一（无前提）零发现面（B1/B2/m2/m3/m4/m6 之外）

- **§1.1 现状症状全符号锚独立逐条对码（全部成立）**：`prep_obs_frame` 4 写点全在 cw_screen_prep.py（:532/:897/:1599/:1763）+ 3 读点封闭（bridge.py:174、cw_screen_prep.py:1865、cw_equip_wear_plan.py:163）；supply 旗标 = 容器派生 `int(...supply_refresh_used.value or 0) > 0`（cw_screen_supply_node.py:206-213）且 decide 调用仅在 match 在场支（:222，局外实例兜底 :213 不可达入口）、闸命中静默落选卡支（:233 if/elif 结构核实）；encounter 四调用点两路径各一对（:304/:336-337/:439/:466-467）、闸命中日志分支不重决策（:320-325/:452-457）、重入清标志重走 fall-through 无参首调（:254-264）；`gs.shop` 活写端在产、encounter/supply live 清点缺位（live `leave_screen` 恰两处全 shop：cw_game_state.py:2033 CloseShop 腿、cw_observation.py:2618 prep 锚 miss 支；encounter/supply 清点仅在 sim 合成口 ：3970-3971/:4263-4265）；EncounterPayload.options `list[tuple[int,str]]`（:613）/SupplyPayload.options `list[tuple[str,str,bool]]`（:620）；flow.py:471「空 stub」docstring 过期（调用点 cw_screen_invest_strategy.py:404 / cw_screen_invest_env.py:303 直传容器单例）；`node_screen_refresh` 为 DEFAULT_GS_SCHEMA 分组名（:146）非访问路径、supply_refresh_used 为顶层 Field（:2757）；kernel eval-lcs 吃 OCR 原名（cw_events.py:233/:376、cw_investments.py:1320-1322）——槽 #5「规范名禁进决策输入」依据成立；megastar_clicked 读侧 getattr 缺省 False 先例（cw_screen_megastar.py:157）。
- **§2.1 契约签名表与 ABC 逐行对账**：11 现签名/形参名/返回类型逐字节一致；抽象 12 → 13（入口 11 → 12 + create_session）、总成员 13 → 14 推导成立；实现位分布核实（bridge.py:165 唯一 decide_prep_screen 实现、flow.py 无此方法、mandate_v1/shop.py:749 已 gs-first、bridge.py:203 decide_encounter 覆写生产在用）。
- **§2.2/§2.3 机制面**：12 槽位表与代码一一对应（typed 选项类五者同住 cw_events.py:597/:711/:778/:806/:827，cw_events 模块级 import cw_game_state :24——契约 g 循环导入依据成立）；REGISTERED_ACTORS（:285-336）缺席新写端者恰 `CwScreenPlanner`/`CwScreenBoxPick` 两名——登记申报精确；`_PAYLOAD_DOMAINS` 三域（:171）与 leave_screen 域守卫（:3158）；属屏映射 10 行键与 `_dispatch_identity_screen` 分发臂（cw_loop.py:1364-1642）逐行对上（含列车同行/骇入策划/星徽秘典弹窗/备战-武装箱选择四反直觉行；武装箱弹窗 ：1431 派发 CwScreenArmoryBox 无 decide 核实）；挂点时序（早退 ：1754 < 识别 < 分发 ：1821，未知兜底 ：2032/:2083 在分发后循环尾）；「非身份臂语境无 decide 消费」逐臂核（阶段三特殊规则臂道具详情/消耗品/阿哈装备均无契约调用）；已 None 跳过先例（carry）；ChannelSig.group_id 随 write_seq+1 位移先例（flow.py:766-768）。
- **三屏刷新链分形态申报与码面一致**：encounter 同访问重读重决策（:333-337 `_try_refresh` 无条件重读）；supply 发射后交回重入（:263/:157 round_retry）；invest 同型（cw_screen_invest_strategy.py:476-477 pending + round_retry）——「无同访问二次覆盖」申报成立，重入访问常规「OCR → 写槽 → decide」起点链核实。
- **per-visit 旗标四场景等价性推演**：首调 False / 累计闸命中（入口旗标恒 False，与改前缺省一致）/ 刷新重决策 True / 重入重走首调复位 False——与 `cw_screen_encounter.py` 两路径结构逐一相容；写点定死（首调前置/发射与重决策之间）可落位；无 match 守卫跳过写与码面 gate 一致。
- **§2.5 调用方迁移契约**：pick handler 10 文件实存且契约调用点全集 grep 对上（encounter 单文件恰 4 点）；prep 两调用点（:1545/:1712）；buy_cards 防御路径临时 match（:801-802）；planner/invest 局外防御 kernel 直调零改动核实（cw_screen_planner.py:208-212、cw_screen_invest_strategy.py:406-417、cw_screen_invest_env.py 同型）；`mandate_v1/entry.py` 全仓 grep 零 decide_ 契约调用点；sim 树唯一消费点 = cw_replay.py:112 decide_shop_screen（签名不变）；`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`（:114）与 `_act_execute_default`（:1821）/`_open_shop_phase` 死参核实。
- **阶段可验收性试读**：3.1 纯增量零行为（encounter/supply live 无写端 + 新槽恒 None + shop 豁免 → 挂点 no-op 等价）；3.2/3.3/3.4 文件面覆盖各自承诺的全部读写点（attack12-A1 的登记义务已按修正方向二移入 3.1，落地复核在案）；3.5 只读验证面与 §2.6 一致。
- **在飞迭代对账（直调）**：execstate 6/6 done + 正本清零（README + commit ee1f4e337 git 直查）；turnstate 3/3 落 HEAD（7b50d690f/170d8366f/b6e88a902 逐一 git 直查，README 迭代收口 4177482d2）；unified-obs 落地 3/5、3.3 落码 done + 实机验证候窗、3.4 依赖 3.3（landing :49）——§2.8 传递链与协商前置描述与当前 README/landing 逐项一致；3.2/3.3 与 unified-obs 3.4 文件面（cw_screen_prep.py/cw_screen_buy_cards.py）相交申报成立。
- **工具面申报**：cw_replay `--run/--rounds` 现行、`--diff` 退役（模块头在册，直读核实）；决策迹载体 `kernel/cw_decision_trace.py` 实存、decisions 流退役在册；strategy-work §4 `cw_replay --diff` 条目失同步属实（:50 直读）——「既有文档债非本批辖」定性成立。

### 核二（规范遵循）零发现面（m1/m5/m7 之外）

- **四硬规则**：依据就地标注（抽验 20+ 处主张的锚全部可解析：execstate #12-#14 域 bump 先例、#20 非 Field 先例、fields.md §2.2/§3.4/§3.4.4/§3.7.1/§8.1-8.5/§8.8/§9.4、game_state/README §3.3 两条先例行、flow/README §2.4 注册面封闭集、session.md §5.1 B4、ShopPayload.cards asdict 先例、carry None 跳过先例）；无过程叙事（design/landing 正文零「本轮/已改/第 N 轮」措辞，用户裁定指针为权威锚非过程件）；实现者无需再设计试读（例外即 m3/m6/B2-1，已列）；修订后全量同步复查（design↔landing↔README 三向对账，例外即 m5/m7）。
- **形式项**：标题层级合规；README 构成 = 文档+进度两节、无详设行合规、进度单点在 README；landing 六个小节（3.1-3.5+末阶段）七件齐逐一在；attack12.md 实文 4 条（major 1/minor 3）与 README 进度行一致；attack12 四条消解逐项复核落地（A1 登记移 3.1、A2「非穷尽示例」改写、A3 契约 g 辖域扩五槽、A4 表格连续性恢复）。
- **词表普查兜底独立复跑**：`prep_obs_frame` src 23 命中逐条归类全落 3.2 文件面；`decide_` 前缀 src 契约调用点全集落 3.3/3.4/清单一行；`PickBoxCard` 正本残留（18 号篇 §7 :186/:188、25 号篇 :19、box_pick.md:34 删除申报锚、action-logic-state.md:214/:330）被词表+清单两行兜住；计数词五形态命中面（flow/README 六处、session.md:14、strategy-docs/README :33/:60、13/25 号篇、screens/README :107、expert_invite :12、fortune :11）全兜；screens/ 目录 22 篇未列清单者（equip_pick/armory_box/aha_equip_pick/plane_intel/deploy 等）经 `decide_` 前缀/「九接口」普查可达（plane_intel 的 `decide_plane_skip` 非契约 helper 会被普查命中归类，无假零）；`refresh_used` 与 `encounter_refreshed_in_visit` 分词收录正确（后者不含前者子串，单靠 refresh_used 会漏——已分列）。
- **design↔landing↔README 判据同步**：四格对照、单帧锁构造、写槽-决策点计数对账（grep 调用点数 = 写槽点数）、普查范围「两仓 + 正本树（含 docs/game/currency_war/，排除 sources//changes/）」、 proofs/ 排除理由（「非零命中依据」）——多文档口径逐字一致；3.5 回放旁证辖域局限申报与 §2.6 逐字一致。
- **兼容裁定**：干净断申报与 session.md §5.1 B4 原条款的收缩关系在清单行在册；「注册面封闭集 {mandate_v1}」与 flow/README §2.4 及 cw_strategy_manager 现状一致；B4 缺省保留面（create_state）与本批 abstract 面扩张的边界申报清晰。

### 行为零变化申报专攻零发现面（m2/m3/m4 之外）

- 新写端量级（journal 行量/write_seq 位移/group_id 字符串形态）申报与 flow.py:766-768 现形态对上；
- 路由清点时序与两路径语义（挂点位置/早退绕行/未知兜底）与码序一致（无害性论证的措辞失准见 m2，机制本身申报准确）；
- refresh 旗标分支等价（supply 入口读容器与现调用方派生式逐字节相同、局外分支不可达入口）与重入路径（清标志重走 → 无参首调）逐位等价；
- 写失败语义：fail-loud 申报 vs 现行 supply 计数 best-effort（cw_screen_supply_node.py:239-254 try/except）的差异已显式申报为禁类，新写端不继承 best-effort 形态——申报自觉且方向正确；
- prep_obs 读者封闭性（3 读点全集 = 申报全集）；
- 快照 restore 不对称申报（restore rebuild 表仅 node/两行/bench/shop，encounter/supply 直透——attack12 直调 :4073-4096 复核在案，本轮抽验一致）；
- actor 登记义务（缺席者恰 CwScreenPlanner/CwScreenBoxPick 两名，其余八 handler 均在册，CwLoop 在册可供挂点用）；
- 瞬态槽判别信号（「写槽以该分支将调用 decide 为前提」）：逐 handler 零选项不调 decide 守卫在案（encounter :296、supply :222、megastar :163 等），`[]` 写入场景未引入的申报与码面一致；
- sim 可观测性声明（决策面可见、prep 面 sim 不可达、不跑 A/B）与 flow/README §2.3 sim 消费面注记一致。
