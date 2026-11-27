# 动作 op(action-op)

> 组件 = `operations/cw_op/`(动作 op 群与注册表)+ `kernel/cw_vocab.py`(统一动作类型清单)+ `kernel/cw_action_report/`(上报函数族)。路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。动作原语(`operations/actions/`,MCP 双消费面)见 SKILL.md §1.4。

## 目录

- §1 执行规范
- §2 动作类型清单与注册表
- §3 上报函数族与回执契约
- §4 转移动作后果声明与喂入
- §5 动作 op 全量清单
- §6 画面 op × 支持的动作 op

## 1. 执行规范

**机械执行**:动作 op 是机械执行——只负责把一个动作发出去(点击/拖拽)+ 如实上报动作事实。禁止做验证,禁止做重试。任何需要验证或需要重试的地方,一律是 bug。

**禁以偶发结案**:不存在偶发丢失——动作未生效必有确定性根因,禁止以偶发结案;失配告警拦停的每个未生效都必须查到根因(如:装备角色专属约束/前置不满足/时序错误),修法落根因层。

**点完即写**:选择动作执行就一定按成功处理——动作 op 点完就立即上报,按成功把结果写进 game state。没有选到/动作没生效就是代码 bug:显式报错修根因,不在 bug 上做无畏的补丁操作。

**参数直接使用(零防御)**:上款「显式报错修根因」的现役形态 = **参数值直接使用、让 Python 自然抛异常报错**;不为建档缺失/参数非法设置检查分支出口。限定例外:下标/坐标类参数的缺失与越界,按下文「坐标按下标取」规范设守卫断言(含禁负下标)。本条与观察侧「识别不到就是 bug」的停机规则是同一族规范,分别约束动作 op 与观察上报。

**零新增读屏**:动作 op 无论执行前还是执行后,都不做观察识别——这是规范,不是取舍。动作 op 的全部职责 = 定位点击/拖拽 + 固定等待 + 上报动作事实。禁止:执行前读屏保留证据、执行后读屏验证或写入记录、以及一切以「读取画面状态」为目的的截图与识别。**唯一允许的查找 = 点击/拖拽目标定位所需的元素查找(找钮/找卡/找槽——瞄准,不是观察)**。画面状态的读取一律归观察域;动作只经上报函数声明事实,真值归下一帧观察。

**入口不做画面级判定,是特意设计**:范围 = `operations/cw_op/` 下的动作 op 类(含不经注册表的结算确认 `CwOpSettleConfirm`)。同目录的 `cw_op_open_shop.py` 不是 op 类,是备战画面 op 调用的一个点开店钮的函数,做法相同。`operations/actions/` 下的动作原语不在此列,它们的入口做法见那个目录的模块说明。下面几条说的是点击、拖拽类的动作 op。重观察动作 `Obs` 不点也不拖,入口是重新读屏——它的入口同样不判画面,但下面关于找目标和点击的话跟它无关。开店动作 `CwActionOpenShopOp` 只在注册表里占一行,用来放终结判定和等待时长;它的执行体在正常路径上不可达(一执行就报断言错误),本条不管它。

- 项目规范要求 op 的入口节点先做画面级判定(根目录 `AGENTS.md` §3;通用写 op 的 skill `od-dev-write-operation` 里是同一条要求)。动作 op 不做这一步:入口直接定位动作目标——找钮、找卡、找槽;或按参数下标从状态容器取坐标(本节「坐标按下标取自状态容器」);或按槽位从画面档取坐标(槽位有的来自参数;买牌 op(`CwActionBuyCardOp`)是自己从状态容器查出这张牌在哪一槽);或直接用参数里给的坐标。
- 项目规范要求:涉及画面切换的操作,点击以后要等画面转移的证据(`AGENTS.md` §3)。动作 op 不等画面转移的证据,也不验证效果(本节「机械执行」「零新增读屏」);点击或拖拽以后的固定等待照做。
- 项目规范禁止靠逐个 area 试命中来推断现在在哪个画面(`AGENTS.md` §3)。动作 op 找目标时的做法不算违例,例:出战 op(`CwActionStartBattleOp`)查不到「按钮-出战」时查「按钮-跳过」,查到就点它——它是在找自己该点的按钮。不管找没找到,它都不据此判断现在在哪个画面。
- 在哪个画面由调用它的一方保证。一条龙自动运行时,调用它的一方是正在运行的画面 op;画面 op 由主循环按画面识别的结果派发(`loop.md` §2)。MCP agent 直接调用时,调用它的一方是这个 agent。
- 调错画面时,动作 op 不会报「画面不对」。找得到目标,它照常点击或拖拽、照常上报。找不到目标,各 op 的表现不一样,下面三个只是例子:出战 op(`CwActionStartBattleOp`)报失败;关店 op(`CwActionCloseShopOp`)按成功返回,回执写「定位缺失」;结算确认 op(`CwOpSettleConfirm`)按成功返回。所以调用它的一方不能靠动作 op 的返回结果知道画面错了。这算调用它的一方的 bug:修那一方,不给动作 op 加判画面。

**单击原子条款**:动作 op = 定位动作本体(读屏豁免仅限动作本体定位)→ 单一机械交互序列 → 自上报。**判据 = 段间有无非本体对象的画面识别/流程反射/收尾(判段间内容,非段数)**:段间识别仅限动作本体定位(确认按钮/目标查找属定位豁免,不属段间识别)= 合法现役形态零改动(pick 族选中→确认两段、CollectOre 点击列);段间识别**非本体对象**(弹窗/收尾面)并分支处理 = 违例(违例形态 = 点击 → 截图识别弹窗 → 分支勾选确认,先例 = StartBattle 旧收尾段,已收缩为单击原子)。点击后世界什么样 op 不管,交回主循环重新识别。

**一动作一文件**:每个动作 op 单独一个文件——`operations/cw_op/` 下一个动作 op 类 = 一个独立文件。命名细则:`<action>` = op 类名 snake 化(`CwActionPickXxxOp` → `cw_pick_xxx_action.py`,与上报侧 `kernel/cw_action_report/<action>.py` 一动作一文件对称);备战域保留域前缀惯例(`cw_prep_*_action.py`);一类多清单行(注册表两行同指一 op)随 op 类单文件落。禁新增捆绑文件。

**坐标按下标取自状态容器**:选择类动作 op 的点击坐标从 game state 按下标获取——策略侧只输出下标(idx),动作 op 按 `param.idx` 从状态容器选项槽取该选项的点击坐标执行;坐标由观察上报写入。键特形:专家邀请函动作类型 `idx = -1`(现金为王)→ 独立 `cash_point` 字段显式分支(禁负下标直取列表——Python 负下标回环 = 静默错点最后一卡);商店域键 = 物理槽 slot(BuyCard 动作类型无 idx,槽 1 基)。坐标域缺席/下标越界/元素缺坐标 = 守卫断言 AssertionError 显式报错,禁控制流分支、禁回退。禁新增第二坐标源。

**记账路径总契约**:动作 op 上报它实际动过的坐标,kernel 记账层用观察产出的坐标伴随域对照表反查出具体内容再记账——名称从「记账键」降级为「反查产物」;名称字段在 op 机械面与 kernel 记账面均零消费(宪法③原样成立)。三条契约:①反查时序不变式——上报反查消费拖前快照,重观察刷新必须晚于上报;②记账后→重观察前的坐标伴随域陈旧条目窗口禁消费(框架侧由动作/重观察交替保证);③反查唯一性前提 = 同一快照内坐标↔条目一一对应(观察路径逐格分类保证,sim 占位路径唯一化保证);反查不到 = 拒单零写(拒单发生在拖拽后,禁止补拖,处置 = 交还框架决策循环刷新对照表重派);反查命中但名单缺条目 = 禁消费窗口违反,以异常响亮暴露(零防御),非拒单路径。全动作 op 迁移继承本契约,不再逐个报批;八批迁移(穿装 WearEquip/工具原子七类/MoveUnit/SellDeployed/SellBench/OpenBookcard/OpenTome/OpenBox)已全量落地收官,记账形态按反查键域分四型并存:①坐标伴随域反查族(键 = `gs.owned_equip_xy`,反查函数 = kernel `cw_game_state.resolve_item_by_xy` 公共口)——首例 WearEquip = 单键(src_cx/src_cy),拒单码 `wear_item_xy_unresolved`;第二适用者工具原子 = **双键**(源工具坐标七类通用 + equip 模式目标件坐标,冶金炉/特权赋予卡两类),拒单码 `tool_xy_unresolved`(源键;精密扳手 consume=False 豁免 = 不拒单、evidence 注记形态)+ `tool_target_xy_unresolved`(equip 目标键),`tool_target_unit_missing` 槽位解析失败升格拒单,反查产物严格移除/状态推导名容错分裂;②槽位反查族(键 = 槽位下标,槽位表本身即名称↔位置对照表,零坐标伴随域;记账载荷 = 槽位反查产物/状态推导名)——第三适用者 MoveUnit/第四适用者 SellDeployed(deployed_idx)/第五适用者 SellBench(bench_idx,bench 装备恒空零改造),代际防线字段 `expect` = 发出点写入、上报层拒单消费(非名称语义参数);③占席件离席直址写族(键 = 槽位下标,占席件槽 kind→empty 直址写零身份反查;不变量 = 每件占席件的离席写端唯一且时点 = 该件的游戏离席时点)——适用者两支:占席件选卡两件 PickStarTome/PickBoxCard(时点 = 选卡落地〔弹窗期件仍占席〕,槽号 = 开件登记携带 `PendingScreen.slot`,登记缺位/槽不符/溢出告警在场 = 不清+披露〔kind `pick_open_slot_uncleared`,evidence 后缀区分出口〕,溢出告警在场实机口径不写让实读承接)+ OpenBookcard 开件上报(第六适用者,**不同态件**:书册卡点开即离席,开件上报腾位直址写即其离席写端,长期保留非候迁;拒单码 `bookcard_slot_missing` 进 round detail,禁补点,处置 = 交还决策循环重读板面按新状态重派;随附纯转移声明 trigger = '',next_screen = `node_screen_now` 底层屏);④零写占位形态(第七/第八适用者 OpenTome/OpenBox,同构)——`param.slot` 读入登记载体与声明载体(非键域反查),零状态容器写端(弹窗期件仍占席),登记(kind `star_tome`/`box_card`)携被点开槽 + 声明携槽(`WorldDecl.slots`),零拒单出口(错槽真值归 heavy 实读对账,总契约三条在本域整族退化;离席归选卡上报清槽,见③)。交替载体 = `StrategyState.cw4_equip_xy_pending`(穿装与工具 aftermath 共置位共用重观察帧;开件三类 aftermath 零置位端)。

**禁止的写法**(禁新增;现存违例登记在待跟进事项文件 `.temp/tracking/currency-war/待跟进事项.md` 的「动作 op 规范违例清偿」条):

- **分两步上报**:点的时候只记一条日志,等确认真的生效了才补写结果(先发出后落地两相形态已全域停用,禁回潮);
- **等下一轮看画面才补写**:点完不写结果,等下一轮重新截屏、看到弹窗没了,才把选择结果补进 game state;
- **探下一个画面才上报**:先看看有没有跳到下一个画面,再决定上报;
- **判重/防重复保护**:选择面绝不第二次给相同的牌(游戏事实),同一个选择不可能被上报两次——真上报了两次只可能是代码 bug,按 bug 修,不为它加防重复保护。

写错了的最终纠正手段 = 下一帧重新读画面,以实际读到的为准;不是在动作层做事后确认。

**归属说明(每类需求去哪一层)**:

| 需求 | 归属层 |
|---|---|
| 「动作有没有生效」的落地判定 | 观察侧对账(reconcile):挂起预期 vs 下一帧实读,失配 = 纠偏或写入缺陷记录行(journal 的 obs_event 行);入口 = 画面 op 生命周期 reconcile 段 |
| 动作失败后的重试 | 决策循环 / 失败网:逻辑态保持事实,下一帧策略对未完成事项自然重派;重派预算由外循环节点轮次预算封顶,无动作级重试 |
| 动作点不响/拖不动本身 | 动作层修可靠性:点击链坐标、时序、确认序列——不为它加验证这种复杂度 |

**决策侧参数现算契约**:动作参数的合法性由**现算纪律**保证,不靠 op 侧校验。同帧性承诺(参数依据与动作执行之间不发生状态变更)只适用于单动作决策环(备战 act 与 shop visit act 每个动作都重新 decide、decide 读 game state → 产参数 → op 立即执行,op 面对的是同一个 game state——坏参数只能是决策逻辑 bug,自然异常即正确处置)。

- 边界载体登记(不适用同帧性纪律句):战斗链批量发射(`launch_prepared_battle`,`prep_actions.py`)——一次产整批 MoveUnit 参数,逐个 execute 之间 game state 被自上报改写;其陈旧化治理 = report 静态域拒绝 + 观察 reconcile。
- 违纪承接双层:纪律下陈旧参数不应存在;违纪现行承接 = ①商店环 proposal 守卫(`cw_shop_action_ops.py::guard_proposal_vs_expected`,loop 级同帧复检)+ ②动作 op 取值自然异常(兜底)。索引类负值形态不炸(to_slot ≤ 0 → `pts[-1]` 合法索引静默错槽)——参数违法类校验收拢到对应动作 op 内、由 op 守卫断言。
- **校验落点契约**:动作参数合法性校验的唯一落点 = **对应动作 op 内守卫断言**(`raise AssertionError`,消息含定位信息——动作类型/参数名/非法值/合法域)——op 是参数语义的唯一所有者,校验随语义走;执行器不设集中参数校验。凡负值/零值可合法索引的槽位参数,守卫断言下界必须显式闭合(现役 = MoveUnit 槽位域守卫,bench/front/back slot 越界与 domain 非法,`cw_move_unit_action.py`)。

## 2. 动作类型清单与注册表

- **动作类型清单单一源** = `kernel/cw_vocab.py::CW_ACTION_TYPES`(统一动作类型清单,封闭——新增动作必须同步登记;漏登记 = 执行面拒「未知动作类型」,动作从未真正执行)。
- **注册表单一源** = `operations/cw_op/cw_action_registry.py`(动作类型清单条目类 → 动作 op 类一张表;`action_op_for`/`action_op_class_for` 全动作唯一注册点;行序 isinstance 首中即返)。清单外类型 = AssertionError 显式报错(非法返回 = 策略器 bug,禁静默跳过)。
- **备战域动作全集**(参数清单单一源 = `kernel/cw_vocab.py` 词表):`CollectOre(points)`(有序晶矿心坐标点击列,挑选逻辑归决策侧)/`OpenBox(slot)`/`OpenTome(slot)`/`OpenBookcard(slot)`(开件三类 slot 必填,备战栏物理槽 1 基,None 语义已随参数清单迁移废除)/`SellBench(bench_idx, income?, reason)`(bench_idx = game state 备战席槽表下标 0-8 基 0;income = 预期回金记录字段)/`SellDeployed(deployed_idx, back_slot_count, income?, reason)`/`MoveUnit(src_domain, src_slot, dst_domain, dst_slot, back_slot_count)`(统一拖动,部署统一批:front/back/bench 任意源 → 任意目标四元组,单坐标系——front 槽 1-4 基 1 / back 槽 1-N 动态基 1(N=`back_capacity_of`;op 参数 = `back_slot_count` 布局档快照 6-9,非 back 目标忽略)/ bench 槽 0-8 基 0,越界 fail-closed)/`WearEquip(src_cx, src_cy, row, slot, back_slot_count)`(坐标参数化穿装单步)/工具原子七类(`tool_cx, tool_cy` 源坐标七类通用;双模类冶金炉/特权赋予卡另带 `tgt_cx, tgt_cy`,char 模式另带 `row, slot`)/`SynthesisConfirm(cx, cy)`/`SynthesisCancel(cx, cy)`(合成确认浮层处置;cx/cy = 浮层上 ✓ / ✕ 按钮中心的 1080p 画面坐标,来源 = game state `synthesis_overlay` 的 `ok_xy` / `cancel_xy`,MCP 直调 = 当帧 extras 同名读数;发出点 = 策略器 `decide_synthesis_overlay`,经备战画面 op 的优先分支消费)/`LevelUp`/`OpenShop`/`StartBattle`/`Obs(scope)`(重观察动作;`in_place` = 缺省,在当前画面原地重新观察上报,零点击零拖拽、不返回主循环;`outer_loop` = 结束本次画面访问、返回主循环后重新观察;现役只被备战决策环调用)。
- `SellBench.reason` = 卖出原因备注字段,仅供日志归因、执行代码不读(**记录非指令**);发出侧取值封闭集 = `cw_prep_actions.SELL_BENCH_REASONS`。
- 动作实例键 `action_key(action)` = 类型 + 参数字段(词表 `action_key_exclude` 排除面除外:全族 `route_tag` 与 pick 族归因载荷字段);现役消费 = 备战决策环日志标识与终结口透传(屏蔽计数消费者已退役,幂等键语义保留)。
- 三刷新建议动作(RefreshNodeOptions/RefreshSupply/RefreshInvestCards)不经注册表(分屏形态各异,刷新链由画面 op 内置动作承载);执行语义全域规范 = **刷新即终结、结束本次访问返回主循环重观察 + 闸 = 剩余次数观察真值**。

## 3. 上报函数族与回执契约

- **上报函数族**(`kernel/cw_action_report/`,一动作一文件):每动作恰一个具名函数 = 该动作的字段写操作语义单点(`report_action_<snake>_param`);分派只允许 op 直调与商店序列驱动器(回放/既有序列测试消费)直调;终结跳写(refresh/close 生产不写)与零写族策略声明在包 `__init__`。
- **点击即上报(全动作通用契约)**:动作 op 不做任何确认、不探下一画面识别标志、不等转移证据——无证据等待 ⇒「上报先于下一节点任何画面渲染」恒成立;节点推进类上报有前置条件检查(kernel 内):只有当 game state 的 `node_pos` 字段已有观察来源(source=observation)的值时,上报才被放行;不满足时把证据写入观察事件行(obs_event),不推进节点。兜底 = 观察 id_mark 确认(kernel `observe_node_anchor` 补推)。推进经生效写入函数 `advance_node_effective` 记入 game state。
- **回执契约**:回执唯一写点 = `note_action_receipt`(`kernel/cw_game_state.py`),shape = `{op, reason='', detail?, screen?, **extra}`;`reason=''` = 正常发出,非空 = 机械受阻事实码(**封闭词表**,新码先登记再使用)。词表与子码枚举单一源 = `prep_actions.py` 码化映射表。上报函数族出参 `LogicOutcome.applied/reason`(拒绝语义)不是回执字段。
- **固定等待族(等待不做效果验证)**:动作后的等待全部是固定时长常量(等待归产生动画的操作),无轮询、无「画面就位才算成功」判读;弹窗/画面是否就位交下一帧观察与外循环画面分支接住。

## 4. 转移动作后果声明与喂入

- 「转移动作」= 执行成功后游戏画面会切换到下一画面的动作(共 19 个)。
- 上报函数在动作生效出口(`applied=True`)构造下一画面声明 `WorldDecl`(`kernel/cw_world_decl.py`):两维 = `next_screen`(动作后确定的下一画面 screen_info 档名,`''` = 无画面/局终)与 `trigger`(推进分派类别,`''` = 纯画面转移);载体 = `LogicOutcome.world_decl`,拒绝/未发出出口 = None。
- 动作 op 自上报后紧跟一行 `cw_sim_ports.declare_world(outcome.world_decl)` 把声明喂给 sim;一次动作多支上报 = 每支上报出口各自紧跟一行;非转移动作 `world_decl` 恒 None,无喂入行。
- 局终:`sequence_next` 无后继时零写入零效果 tick 仍返回 `applied=True, reason='match_end'`,并声明空画面;局终声明事件式,重复上报幂等。
- 喂入行与机械执行同判,op 侧零分支:实机(端口未装)= no-op,sim(装配后)= 驱动后端按 `trigger` 分派推进;sim 消费与对账契约 = `docs/develop/sr_od/application/currency_war/sim/sim-design.md` §6.3。
- **实机面的消费原则**:`WorldDecl` 在实机 = 记账(喂入 no-op,声明随 round 结果 `data` 落 journal 记「预期画面」,供与实读画面 diff 对账作画面漂移早期警报料)——**禁止用作效果验证断言**;动作是否落地以观察边界对账为准。

**转移动作声明终表(19 动作;`trigger` 封闭集单一源 = `sim/cw_sim_backend.py::ADVANCE_TRIGGER_KINDS`)**:

| # | 动作 | 上报落点 | op 落点(`operations/cw_op/`) | trigger | next_screen |
|---|---|---|---|---|---|
| 1 | settle_confirm | `kernel/cw_game_state.py::report_node_advance` | `cw_op_settle_confirm.py` | `node_advance` | 节点序推导(见表下规则) |
| 2 | supply_finish | 同上 | `cw_action_report/start_battle.py`(出战动作) | `node_advance` | 同上 |
| 3 | StartBattle | `cw_action_report/start_battle.py` | `cw_start_battle_action.py` | `battle_resolve` | 货币战争-结算 |
| 4 | PickEncounter | `cw_action_report/pick_encounter.py` | `cw_pick_encounter_action.py` | `battle_resolve` | 货币战争-结算 |
| 5 | OpenBox | `cw_action_report/zero_writes.py` | `cw_open_box_action.py` | `open_box` | 底层屏推导(`node_screen_now`;武装箱选择画面出现事实 = 登记 kind `box_card` 携开件槽;声明 `slots` = (开件槽,)) |
| 6 | OpenBookcard | `cw_action_report/open_bookcard.py` | `cw_open_bookcard_action.py` | `''` | 货币战争-备战(专家邀请函出现事实 = 登记 kind `expert_invite`;**不同态件**:书册卡点开即离席,开件上报直写即其离席写端) |
| 7 | PickInvestEnv | `cw_action_report/pick_invest_env.py` | `cw_pick_invest_action.py`(两行同指一 op) | `pick_invest_env` | 货币战争-备战 |
| 8 | PickInvestStrategy | `cw_action_report/pick_invest_strategy.py` | 同上 | `pick_invest_strategy` | 货币战争-备战 |
| 9 | PickBoxCard | `cw_action_report/zero_writes.py` | `cw_pick_box_card_action.py` | `pick_box_card` | 货币战争-备战 |
| 10 | PickMegastar | `cw_action_report/zero_writes.py` | `cw_pick_megastar_action.py` | `pick_megastar` | 货币战争-备战 |
| 11 | PickPlanner | `cw_action_report/pick_planner.py` | `cw_pick_planner_action.py` | `pick_planner` | 货币战争-备战 |
| 12 | PickSupply | `cw_action_report/pick_supply.py` | `cw_pick_supply_action.py` | `pick_supply` | 货币战争-补给 |
| 13 | PickPartner | `cw_action_report/zero_writes.py` | `cw_pick_partner_action.py` | `''` | 货币战争-备战 |
| 14 | PickFortune | `cw_action_report/zero_writes.py` | `cw_pick_fortune_action.py` | `''` | 货币战争-备战 |
| 15 | PickWishTrial | `cw_action_report/zero_writes.py` | `cw_pick_wish_trial_action.py` | `''` | 货币战争-备战 |
| 16 | PickStarTome | `cw_action_report/zero_writes.py` | `cw_pick_star_tome_action.py` | `''` | 货币战争-备战 |
| 17 | PickExpertInvite | `cw_action_report/zero_writes.py` | `cw_pick_expert_invite_action.py` | `''` | 货币战争-备战 |
| 18 | CloseShop | `cw_action_report/close_shop.py` | `cw_close_shop_action.py` | `''` | 货币战争-备战 |
| 19 | OpenTome | `cw_action_report/zero_writes.py` | `cw_open_tome_action.py` | `open_tome` | 底层屏推导(`node_screen_now`;星徽四选一画面出现事实 = 登记 kind `star_tome` 携开件槽;声明 `slots` = (开件槽,)——sim 无星徽弹窗呈现面、选卡拍不存在,后端据此在开件拍代清席,与实机「选卡拍清槽」的时点分歧在 `_on_open_tome` 披露键申报) |

`node_advance` 两行(#1/#2)的 `next_screen` 不是固定值:由上报函数按节点序表推导下一画面(推导函数 = `cw_game_state.window_stable_screen_now`,节点序来源 = kernel 后继函数 `sequence_next`,`kernel/cw_node_schedule.py`)。推导规则:进入新位面 → 位面过渡画面;战斗/奖励节点进入稳态 → 自动弹店开商店;补给/遭遇/BOSS 简报这类弹窗型节点 → 备战画面之上叠加节点弹窗。唯一例外:位面 1 第 1 节点稳态停在备战画面。无后继节点 = 局终,声明空画面 `''`。「返回节点屏」声明族(#5/#6/#9/#10/#13-#17/#19,构造单点 = `zero_writes._decl_bottom`/`open_bookcard._decl`)的 `next_screen` 按当前底层画面推导(`node_screen_now`:稳态落点恒为备战画面,位面起点例外 = 位面过渡画面;2026-10-29 呈现改版后旧的「节点类型→画面名」映射表已废弃,表内该族行的备战画面值 = 稳态推导值)。#12 补给 = 现役唯一单 op 多支上报。OpenTome 构造声明 trigger='open_tome'/slots 携开件槽(星徽四选一画面的出现事实由登记 kind `star_tome` 携槽承载;声明 = sim 后端无星徽弹窗呈现面时开件拍代清席的喂入通道)。

**overlay(画面浮层,指弹窗/选卡页等盖在底层画面上的 UI 层)登记与动作上报的关系**:弹窗类「画面出现事实」由 game state 登记(`kernel/cw_overlay_register.py` 三个登记入口 + 九类登记目录——封闭集,新增类型必须登记)承载,与动作上报的关系分三族——①**开件直登族**:OpenBox/OpenBookcard/OpenTome 上报内登记(OpenBox/OpenTome 登记携被点开槽 `PendingScreen.slot`),弹窗出现与动作落地同点;②**选卡消费族**:八个 pick 上报函数体内消费同 kind 登记(`consume_screen_change`,sim/实机同一行代码),选卡落地即弹窗处理完毕;其中占席件两件 PickStarTome/PickBoxCard 的选卡上报消费登记取槽并 logic 清该槽(选卡即离席 = 占席件离席的单一写端;溢出告警在场实机口径不写让实读承接、sim 口径经包级注入槽写 empty);③**判据登记族**(不经动作 op):巨星/planner/占卜屋/伙伴/祈愿/阿哈由 kernel 值回调(`kernel/cw_faction_callbacks.py`,deployed 逻辑写尾)或对应上报登记,消费 = 实机在备战画面兜底清空 / sim 懒呈现位。登记生命周期权威版本 = sim/sim-design.md §4。

## 5. 动作 op 全量清单(基准 = `cw_action_registry.py`;行数以代码现值为准)

**商店族**:

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| BuyCard | CwActionBuyCardOp | `cw_buy_card_action.py` | 点买一张牌:槽号按期望态 payload 定长槽阵列解析(身份同一性优先,退化按 (name, star))→ screen_info「商店牌-N」中心点击(槽解析失败/槽号越界 = op 内守卫断言,禁兜底坐标静默点击);恒发出即记账;满栏自动多买补差(k = `merge_buy_k`);落地归观察侧对账。 |
| RefreshShop | CwActionRefreshShopOp | `cw_refresh_shop_action.py` | 刷新商店(终结动作,结束后返回主循环重进 = 入口观察重建牌面):点刷新钮 → 固定等待 1s(`REFRESH_CLICK_SETTLE_WAIT_S`)→ 刷价记账(失读回基价常量)→ 自上报同一上报口三支(计数触发/免费次数扣减分支——None = 未观察保守按付费/随机采样分支 = kernel 采样器 `cw_shop_deal.sample_shop_deal` 经 `write_logic_rand` 写牌面随机态,observe 覆盖差异 = 预期内不进失配告警)。体内零读屏零验证;执行侧零重试。 |
| CloseShop | CwActionCloseShopOp | `cw_close_shop_action.py` | 关店恒可用终结 op:帧上找「按钮-收起」真点击(miss = 店已关,幂等出口)+ 固定等待 + 自上报清场;零转移验证(点击未生效 = 外循环重分发自然重派)。发出条件 = 商店决策无动作可做时主动选它终结本画面访问(全函数契约要求的恒可用终结)。 |

**备战族**:

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| SellBench | CwActionSellBenchOp | `cw_prep_sell_bench_action.py` | 卖备战席角色:drag 备战栏槽中心(area 序 = `bench_idx` game state 备战席槽表下标,零换算)→ 出售区,机械执行后自上报(置 empty + 回金 + 装备回收 + 溢出分支)+ 固定等待 1s。 |
| LevelUp | CwActionLevelUpOp | `cw_prep_level_up_action.py` | 买经验单击:找钮「备战标识-购买经验」单击一次,点击后把鼠标光标移到空白处(防止光标悬停在等级显示区上、让识别读到错误数字);不做授权检查、不做点击计数(击数推导与经验批量支付判断全部上移到动作发出侧代码);金币写入 = op 自上报按 `action.cost`×击数直写。升 N 级需要 N 次点击,N 次点击占 N 帧。 |
| MoveUnit | CwActionMoveUnitOp | `cw_move_unit_action.py` | 统一拖动(全域移动四元组,唯一拖动承载;旧 DeployMove/SwapDeploy 两类已随部署统一批退役):front/back/bench 任意源 → 任意目标,单坐标系(§2);拖拽语义 = 游戏规则:目标槽空 = 放置、有人 = 交换交互,执行层不判断占位、不拒、禁静默换槽;载荷槽越界(含负下标)= op 内守卫断言。拖后零落地判定 + 固定等待 2s(羁绊徽章动画窗);部署差分序消费见本节末尾「层级区别」。 |
| SellDeployed | CwActionSellDeployedOp | `cw_sell_deployed_action.py` | 卖上阵角色:drag 排槽中心 → 出售区(`deployed_idx` → 排/物理槽号内联换算),自上报(摘槽 + 回金 + 装备回收)+ 固定等待 1s。 |
| WearEquip | CwActionWearEquipOp | `cw_wear_equip_action.py` | 穿装备单步(坐标参数化):显式起点 src_cx/src_cy(owned 格心;动作发出侧从 game state 实体坐标字段 `gs.owned_equip_xy` 取,MCP 直调按当帧 extras 传)→ 槽位拖点静态解析(row/slot + back_slot_count → 布局档 area 表,守卫三形越界 = AssertionError,零截图零定位);拖后零落地判定;自上报 = 记账路径总契约首例(按坐标反查件名再写入,反查不到 = `wear_item_xy_unresolved` 拒单零写,round detail 带拒单码);新鲜度 = 装备网格交替标志 `cw4_equip_xy_pending`(cw4 前缀 = 历史策略包代号的遥测键命名残留,该包已删除;置位帧产 `Obs(in_place)`,穿装与工具 aftermath 共用)+ 坐标缺席时跳过该动作、下一帧重观察的自愈双通道。 |
| SynthesisConfirm | CwActionSynthesisConfirmOp | `cw_synthesis_confirm_action.py` | 点合成确认浮层上的 ✓ 一次:按传入坐标单击(坐标守卫 = 非负且在 1080p 画面内,否则 AssertionError 零点击),点完立刻把光标移到装备栏外、再等浮层收起(两段等待 = 模块常量 `COLLAPSE_WAIT_S` + 类属性 `terminal_wait`;先移光标——✓ 中心对着装备栏右列下一行的格子,悬停会弹出框架接不住的装备详情浮窗);零读屏零验证。零写族(上报函数住 `zero_writes.py`):不写 `synthesis_overlay`、不写装备库存——「浮层已处理」与库存真值由下一帧观察覆盖;后果声明 = 仍在备战画面。回执:经执行器分派 = 执行器写、op 不写;直接调用且有对局上下文 = op 自己写一条;没有对局上下文 = 不写。终结动作。 |
| SynthesisCancel | CwActionSynthesisCancelOp | `cw_synthesis_cancel_action.py` | 与确认合成同构,点的是 ✕,等待更短(各自的 `COLLAPSE_WAIT_S` / `terminal_wait`);材料不动,库存无变化。 |
| CollectOre | CwActionCollectOreOp | `cw_collect_ore_action.py` | 点晶矿:载荷 = 有序晶矿心坐标点击列,纯机械逐个点,零读屏零排序零截断(大晶矿优先/上界挑选归决策侧 kernel `select_ore_clicks`);固定等待 2s 等飞行动画;自上报(精确摘除晶矿;晶矿获得的金币窗口期登记与摘除晶矿在上报函数内一并完成)。 |
| OpenBox | CwActionOpenBoxOp | `cw_open_box_action.py` | 开简易武装箱(终结动作,terminal_wait=1.8s;开件三类 slot 必填,None 语义已废除——现算归发出点 `entry._consumable_open_action` 单点;MCP 直调双口径任一:当帧 extras `bench.slots` kind='supply_box' 槽下标+1,或 extras `armory_boxes` 元素 `slot` 字段直传,同一物理槽位号语义):守卫上界 op 内现读备战栏槽位点击坐标表(screen_info 各槽位 area 中心点,1 基,None/越界 = AssertionError 零点击)→ 点「武装箱开启位-{slot}」开启钮区单击(mouse_move 防吞点击;独立 area 族,非备战栏槽本体)→ 固定动画等待;返回主循环按 box_card 登记分发 CwScreenBoxPick 选卡。记账 = 记账路径总契约第八适用者**零写占位形态**:不写任何 game state 字段(弹窗期箱仍占席)+ box_card 登记携被点开槽 + `_decl_bottom(gs,'open_box',slots=(slot,))` 底层屏声明携槽(trigger='open_box' 挂 backend 开箱采样分派);箱体离席归 `pick_box_card` 选卡上报清槽(选卡即离席);本动作没有拒单出口(零写入路径恒 applied=True,错槽真值归全量观察实读对账)。无箱 = 发出点不产动作。 |
| OpenTome | CwActionOpenTomeOp | `cw_open_tome_action.py` | 开秘密典籍(非终结;开件三类 slot 必填,None 语义已废除——现算归发出点 `entry._consumable_open_action` 单点;MCP 直调 = 当帧 extras `bench.slots` kind='tome' 槽下标+1):守卫上界 op 内现读备战栏槽位点击坐标表(1 基,None/越界 = AssertionError 零点击)→ 点「备战栏-{slot}」槽本体一次开启即弹(单击族,mouse_move 防吞点击)→ 固定动画等待;星徽四选一 overlay 经 director 环 overlay-pending 通用路径交回外循环,分发 CwScreenBookcard 接管选卡。记账 = 记账路径总契约第七适用者**零写占位形态**(与 OpenBox 同构):不写任何 game state 字段(弹窗期典籍仍占席)+ star_tome 登记携被点开槽 + `WorldDecl(trigger='open_tome', slots=(slot,))` 声明携槽(sim 无星徽弹窗呈现面、选卡拍不存在,后端据此在开件拍代清席;round data 携声明);典籍离席归 `pick_star_tome` 选卡上报清槽;零拒单出口(错槽真值归 heavy 实读对账)。 |
| OpenBookcard | CwActionOpenBookcardOp | `cw_open_bookcard_action.py` | 开书册卡(访问终结,terminal_wait=1.8;开件三类 slot 必填,None 语义已废除——现算归发出点 `entry._consumable_open_action` 单点;MCP 直调 = 当帧 extras `bench.slots` kind='bookcard' 槽下标+1):守卫上界 op 内现读备战栏槽位点击坐标表(1 基,None/越界 = AssertionError 零点击)→ 点「备战栏-{slot}」槽本体单击(单击族,mouse_move 防吞点击)→ 固定动画等待;专家邀请函弹窗 = 新事实,返回主循环按画面分发 CwScreenExpertInvite 选卡。记账 = 记账路径总契约第六适用者**槽位键退化形态**(不同态件:书册卡点开即离席,开件上报直写即其离席写端,非候迁件):按槽位号直接把该槽置空(kind 'bookcard'→empty),不做身份反查;记账拒单 `bookcard_slot_missing` 进 round detail(禁补点,处置 = 重新读 game state 按新状态重派)。随附纯转移声明 WorldDecl(trigger = '',next_screen = `node_screen_now` 底层屏)。 |

**工具原子七类**(注册表 7 行同指 `CwActionToolUseOp`;参数坐标分三类——①源坐标 `tool_cx`/`tool_cy` 七类通用(owned 工具条目格心 1080p,动作发出侧从 game state 实体坐标字段 `gs.owned_equip_xy` 取,`cw_equip_env.tool_use_params_of` 单点;MCP 直调按当帧 extras.owned_equips 传,单件会话);②equip 模式目标坐标 `tgt_cx`/`tgt_cy`(双模类冶金炉/特权赋予卡才带;不传时传 0,op 用守卫断言拒绝 0 值,源与目标同格也由守卫拒绝);③char 模式 row/slot 半固定(+ `back_slot_count` 布局档 6-9,拖点经 `row_drag_points` 静态解析,+21 权威派生式与穿装统一,后排 7-9 槽可用);守卫断言清单见 op docstring,违例 AssertionError 零拖拽。记账 = 坐标反查双键(`resolve_item_by_xy` 公共口),反查产物严格移除、状态推导名容错;名称字段(item_name/char_name)零消费纯日志;拒单码 = `tool_xy_unresolved`/`tool_target_xy_unresolved`(round detail 带码,禁补拖),`tool_target_unit_missing` 升格拒单;拖拽链 = 穿装批权威链(mouse_move → 拖前固定等待 → duration 1.5 → 拖后固定等待);新鲜度 = 装备网格交替标志 `cw4_equip_xy_pending`(穿装与工具共置位,entry 第 7 步步首检查上提 + 提前 return,置位帧零参数构造)。上报 = 机械执行直接按成功写,记账载体 = `gs.equips` 合并单笔写——消耗移除与效果同笔禁拆两笔):

| 动作类型 | 说明 |
|---|---|
| FurnaceUse | 冶金炉:equip 模式 = 单笔 `write_logic_rand` 合并写(反查产物严格移除工具 ∧ 目标件 → 同类别采样替换;采样池 = `cw_sim_equips.furnace_reroll` 同源);char 模式 = equips rand 合并(工具端严格移除 + 穿戴件端状态推导名容错采样)+ 行域穿戴清空。变异重铸不走获得链。 |
| PrivilegeCardUse | 特权赋予卡:equip 模式 = 单笔 `write_logic` 合并(双键反查,反查产物件名 → `privilege_counterpart` 特权名替换,前置 index 防静默空变换);char 模式 = fail-closed 零写保留证据。 |
| WrenchUse | 拆装扳手:两笔 `write_logic`——equips 合并(源键反查产物严格移除工具 ∧ 追加目标角色全部穿戴件;反查不到 = `tool_xy_unresolved` 拒单零写)+ 行域穿戴清空;工具消耗品 −1 合并同笔。 |
| PrecisionWrenchUse | 精密拆装扳手:同拆装扳手两笔 logic,equips 不移除工具(无限次用不递减);源键反查不到**豁免不拒单**(无消耗笔可拒,拒单 = 物理卸装无账),evidence 注记 `tool_xy_unresolved` 形态。 |
| StaffProjectorUse | 员工投影仪:equips 反查产物严格移除;复制走获得链 `gain_character(char,1★)`(落位→回调→3 合 1 升星);费用上限 ≤3 的前置检查按注册表现读。 |
| PerfectProjectorUse | 完美投影仪:同员工投影仪走链,无费用门。 |
| LuckyTokenUse | 好运令牌:零写入 + 保留证据行(判据现役 fail-closed 永不进准入;写入代码随判据批收敛)。 |

**转场族**:

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| StartBattle | CwActionStartBattleOp | `cw_start_battle_action.py` | 出战单击(终结动作,terminal_wait=3 覆盖点击后弹窗渲染窗):槽位双形态定位(找「按钮-出战」备战+开商店两屏同查;免战子态查「按钮-跳过」同语义点它——动作本体定位豁免)→ 单击 ×1 → 自上报(免战递减内聚,跳过子态事实携带;补给节点形态上报走 supply_finish 推进)→ 终结返回主循环重判。点击后弹窗归独立弹窗 op(经主循环阶段一身份分发接管),op 内零弹窗识别零收尾。round 结果 = 单击已执行(已登记例外;找不到按钮 = False,经执行器 `last_launch_ok` 旁路)。 |
| OpenShop | CwActionOpenShopOp | `cw_open_shop_action.py` | 开店注册行 = terminal 承载行:执行抛 AssertionError(开店流程编排截流在 `cw_screen_prep._act_execute_default` → `_open_shop_phase`,开店由该编排直达、主循环的画面分派被绕过);类属性承载终结判定/等待。开店 = 唯一普通形态(无受限变体)。 |

**观察族**:

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| Obs | CwActionObsOp | `cw_obs_action.py` | 重观察动作,口径由 `scope` 选(值域封闭集 = `cw_vocab.OBS_SCOPES`)。scope='in_place'(缺省)= 在当前画面原地重新观察上报,不返回主循环:执行体 = 宿主画面 op `reobserve_in_visit` 的全量观察链(heavy = 一次读全部槽位/装备/羁绊的重型识别,定义见 screen-op.md)重跑,经观察上报链直接写入 game state;零点击零拖拽;自上报 = 零写占位;非终结,执行后当前帧的观察完整度标记为 full(完整帧),决策环原地续跑;重观察时看到事件浮层 = 抛 `CwObsOverlayBail` 返回主循环重分发。scope='outer_loop' = 结束本次画面访问、返回主循环后重新观察:决策环在参数校验步骤之前分支拦截(不经本表派发、不进执行器、不写动作记录)。动作发出侧没有重观察能力 = AssertionError 显式报错(策略器 bug)。 |

**事件线 pick 族(12 行;域 env = `OverlayPickExecEnv`;op 类体内零决策)**:每屏选择动作 = 一个 `CwActionPickXxxOp`,op 内 = 选中点击 → 确认点击(或点卡即选)→ 自上报;**上报形态 = 全族一步到位**(点完确认或点卡即选后立即按成功写完整结果,不先记日志等确认再补写;确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派)。确认钮不属机械参数 env 传入范围——确认查找与点击 = 动作 op 执行体 `round_by_find_and_click_area`(全族统一;area 缺失 = 显式 round_fail,禁兜底坐标静默点击)。选卡定位终态 = 动作 op 按 idx 从 game state 实体坐标字段自取点击坐标(§1 坐标契约);过渡期形态与例外登记在待跟进事项文件「动作 op 规范违例清偿」条。域载荷逐行 = `idx`(10 行)/`need_select`(巨星)/`branch_type`+`norm_item`(策划)/`unselected`(伙伴)/`match`+`picked`(补给)/`entry_keyword`(投资两屏)。

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| PickEncounter | CwActionPickEncounterOp | `cw_pick_encounter_action.py` | 遭遇节点选卡确认链:点遭遇卡(idx=0 左卡/其余右卡)→ 固定等 0.8s → 「按钮-选择」确认 → 发出即写(值组装 = game state encounter payload 槽所选卡,离屏/越界保留证据不写)。 |
| PickSupply | CwActionPickSupplyOp | `cw_pick_supply_action.py` | 补给节点选卡确认链:`env.target` 点卡 → 固定等 0.6s → 点「按钮-确认」→ 立即自上报完整结果(owned 规范名 0..n 件 + 单位获得写入 + 装备后果链一口写 + 选卡时点检查);选卡确认零推进(补给节点推进归出战动作 supply_finish)。 |
| PickMegastar | CwActionPickMegastarOp | `cw_pick_megastar_action.py` | 盛会之星「选中 → 确认」链(`env.need_select` 驱动)→「按钮-确认选择」确认;纯机械单发,确认未落地 = 下一帧观察复检后纠正。 |
| PickPartner | CwActionPickPartnerOp | `cw_pick_partner_action.py` | 列车同行伙伴确认链:重点选候选(`env.op._pick_point`)→ 固定等 0.7s → 「按钮-确认选择」确认。 |
| PickPlanner | CwActionPickPlannerOp | `cw_pick_planner_action.py` | 骇入策划确认链:`env.target` 点卡(避开「详情」按钮区的选中点几何归决策半)→ 固定等 1.2s → 「按钮-骇入确认」确认 → 确认点击后立即自上报完整结果(条件分支 rider 先行 → equip 分支入栏+后果链 / upgrade 分支变换窗三态 / unknown 保留证据 / unrouted 兜底零写)。 |
| PickInvestStrategy | CwActionPickInvestOp | `cw_pick_invest_action.py` | 投资策略屏选择行(与 PickInvestEnv 两行同指一 op):点选中位 → 固定等 0.7s → 点确认钮 → 立即自上报 → 整支走获得链 `gain_invest_strategy`(无效载荷拒绝 → active_strategies 去重追加 → 效果登记表登记 → 效果分派)。 |
| PickInvestEnv | CwActionPickInvestOp | `cw_pick_invest_action.py` | 投资环境屏选择行(同上共 op):上报 = `param.idx`,名字自 game state `invest_env_opts` 标准名单一源按序号提供 → 整支走获得链 `gain_invest_env`。 |
| PickFortune | CwActionPickFortuneOp | `cw_pick_fortune_action.py` | 命运卜者强化三选一:点卡(game state `fortune_opts_xy[param.idx]`,缺 = 守卫断言)→「按钮-确认选择」确认 → 自上报(零写)。 |
| PickWishTrial | CwActionPickWishTrialOp | `cw_pick_wish_trial_action.py` | 祈愿试炼:点卡(`env.target`)→ 点「按钮-确认选择」确认 → 自上报(零写)。 |
| PickStarTome | CwActionPickStarTomeOp | `cw_pick_star_tome_action.py` | 星徽秘典(点卡即选):选中点击 + 动画等待,零确认步 → 自上报(选卡即离席清槽:消费 star_tome 登记取被点开槽 logic 清;溢出告警在场实机口径不写让实读承接、sim 口径写 empty)。 |
| PickBoxCard | CwActionPickBoxCardOp | `cw_pick_box_card_action.py` | 武装箱(点卡即选):同上形态;自上报 = 选卡即离席清槽(box_card 登记槽,同上口径)。 |
| PickExpertInvite | CwActionPickExpertInviteOp | `cw_pick_expert_invite_action.py` | 专家邀请函(点卡即选):idx=-1 = 现金为王(点「卡-现金为王」区,非候选卡槽)。 |

**层级区别(动作域之外的组合壳/画面 op,不进注册表)**:

- `_open_shop_phase`(`cw_screen_prep.py`):开店编排——OpenShop 动作的流程层执行半(机械开店 → `visit_open_shop` 商店画面 op 直驱);回执 `(完成事实, detail)` 中完成事实 = 商店访问完整收工(非动作成败回执)。
- `PrepActionExecutor`(`prep_actions.py`):备战域执行器——备战动作 op 体迁后的替身函数接缝宿主;`PrepExecEnv` 定义处。
- 部署 = 备战决策环的动作(旧「部署画面 op」已删除):统一部署搜索算出目标上场阵容(`deploy_search.search_deploy_target`,经 `mandate.select_deployment` 定型接口)→ 差分执行器生成动作序列(`deploy_diff.deploy_diff_target_actions`)→ `CwActionMoveUnitOp` 机械拖拽 → 自上报;差分序 = 换星直卖 → 缺位者上场(目标槽被占 = 交换)→ 错位者排位修正 → 多余者下场;计划执行期 = 逐个拖动把计划落到场上,拖动与重观察交替(每发一个统一拖动后下一帧发 `Obs(in_place)` 环内重观察对账,连续 2 次无进展 = 级联卡死 → 计划失败出口);新鲜度守卫 = 下场/交换步涉及本帧刚买件跳过挂起(卖出不拦)。

## 6. 画面 op × 支持的动作 op

> 「支持」= 该画面的策略决策环可产出的动作类型(发出域视角的分组索引;逐动作执行面见 §5)。零策略动作的画面 op(战斗等待/下一步/位面过渡/BOSS 简报/武装箱说明弹窗/阿哈装备选择等固定流程屏)不入表,形态见 [screen-op.md](screen-op.md)。
> **能力面 vs 策略面**:本表按能力面记(画面机制上可做的动作全集);策略面(某策略实际会做的子集)收缩只改决策入口的提案集——动作类型/注册表/上报函数族不随策略收缩删除,被策略弃用的动作在表内保留不删行。

| 画面 op | 文件(`operations/cw_screen/`) | 动作类型集 |
|---|---|---|
| 备战 CwScreenPrep | `cw_screen_prep.py` | SellBench / LevelUp / MoveUnit / SellDeployed / WearEquip / CollectOre / OpenBox / OpenTome / OpenBookcard / 工具七类(见 §5)/ SynthesisConfirm / SynthesisCancel(合成确认浮层处置,经优先分支消费)/ StartBattle(补给节点形态上报走 supply_finish)/ OpenShop / Obs(in_place;outer_loop 分支拦截不派发) |
| 商店访问 CwScreenShop | `cw_screen_shop.py` | BuyCard / RefreshShop / CloseShop |
| 遭遇 CwScreenEncounter | `cw_screen_encounter.py` | PickEncounter + 刷新链(RefreshNodeOptions,不经注册表) |
| 补给 CwScreenSupplyNode | `cw_screen_supply_node.py` | PickSupply + 刷新链(RefreshSupply,不经注册表) |
| 投资策略屏 CwScreenInvestStrategy | `cw_screen_invest_strategy.py` | PickInvestStrategy + 逐卡刷新(RefreshInvestCards,不经注册表) |
| 投资环境屏 CwScreenInvestEnv | `cw_screen_invest_env.py` | PickInvestEnv |
| 巨星 CwScreenMegastar | `cw_screen_megastar.py` | PickMegastar |
| 伙伴 CwScreenPartner | `cw_screen_partner.py` | PickPartner |
| 策划 CwScreenYinLang | `cw_screen_yinlang.py` | PickPlanner |
| 命运卜者 CwScreenFortune | `cw_screen_fortune.py` | PickFortune |
| 祈愿试炼 CwScreenWishTrial | `cw_screen_wish_trial.py` | PickWishTrial |
| 星徽四选一 CwScreenBookcard | `cw_screen_bookcard.py` | PickStarTome |
| 武装箱四选一 CwScreenBoxPick | `cw_screen_box_pick.py` | PickBoxCard |
| 专家邀请函 CwScreenExpertInvite | `cw_screen_expert_invite.py` | PickExpertInvite |

注册表外的执行体(不经 `cw_action_registry.py` 派发):三刷新建议动作走各画面 op 内置刷新链(§2,刷新即终结);结算确认 `CwOpSettleConfirm`(`operations/cw_op/cw_op_settle_confirm.py`,上报 settle_confirm 推进节点)住结算画面,非策略决策环产物。
