# 动作 op 清单与执行规范(action_ops)
> 术语:本篇所用货币战争域术语的统一定义见 [../terminology.md](../terminology.md)。

> 从代码反推,来源 = `operations/cw_op/cw_action_registry.py`(动作注册表,§4 清单完备性基准)+ `kernel/cw_vocab.py`(统一动作类型清单)+ `operations/cw_op/cw_<action>_action.py`(动作 op 文件群)。路径根 = `src/sr_od/application/currency_war/`(下文相对路径均在此根下,§4.6 例外处另行写全)。**规范正文的单一源 = 本文件 §1**;[action_exec.md](action_exec.md) §2 只留指针与执行面契约表。

## 1. 规范(单一源)

**用户裁定(原文)**:动作 op 是机械执行——只负责把一个动作发出去(点击/拖拽)+ 如实上报动作事实。禁止做验证,禁止做重试。任何需要验证或需要重试的地方,一律是 bug。

**用户裁定（禁以偶发结案）**:**不存在偶发丢失——动作未生效必有确定性根因,禁止以偶发结案**;失配告警（发现失配即报警并停机）拦停的每个未生效都必须查到根因(如:装备角色专属约束/前置不满足/时序错误),修法落根因层。

**用户裁定（点完即写,2026-09-21）**:**选择动作执行就一定按成功处理——动作 op 点完就立即上报,按成功把结果写进 game state。没有选到/动作没生效就是代码 bug:显式报错修根因,不在 bug 上做无畏的补丁操作。**

**应用条款(零防御,用户裁定 2026-10-17)**:上款「显式报错修根因」的现役形态 = **取值直接使用、Python 自然异常**;不为建档缺失/参数违法设检查出口。**限定域申报**:下标/坐标域参数的缺席与越界按「坐标按下标取自状态容器(GameState)」裁定守卫断言(含禁负下标)——该裁定域 = 选择类 pick 族;DeployMove 拖拽域按用户终裁适用对账治理链(参数违法类校验收拢动作 op 内守卫断言,见下「决策侧参数现算契约」段)。pick 族既有显式出口条目不被本句判为待修,逐批收敛。与观察域「识别不到就是 bug」停机闸(住 `screens/shop.md`)为观察/动作两域同族规范。

**用户裁定（零新增读屏,2026-09-21）**:**动作 op 无论执行前还是执行后,都不做观察识别——这是规范,不是取舍。** 动作 op 的全部职责 = 定位点击/拖拽 + 固定等待 + 上报动作事实。禁止:执行前读屏保留证据(裁片/快照)、执行后读屏验证或落账(牌名/真值/转移证据)、以及一切以「读取画面状态」为目的的截图与识别。唯一允许的查找 = 点击/拖拽**目标定位**所需的元素查找(找钮/找卡/找槽——瞄准,不是观察)。画面状态的读取一律归观察域(画面 op 观察 node / 观察漏斗);动作只经上报函数声明事实,真值归下一帧观察。

「零新增读屏」裁定的现役违例 = 已知待修问题(逐批清理,禁新增):
- `cw_start_battle_action.py` 出战后单帧弹窗识别(执行后转移面识别)= 待修问题,清法候批。
- (商店域两处旧问题——`cw_buy_card_action.py` 买前裁片、`cw_refresh_shop_action.py` 刷前两口径/刷新钮真值/刷后牌名三处读——已修复,现役商店动作 op 全链零读屏。)

**用户裁定（一动作一文件,2026-09-22）**:**每个动作 op 单独一个文件——`operations/cw_op/` 下一个动作 op 类 = 一个独立文件。** 命名细则:`<action>` = op 类名 snake 化(`CwActionPickXxxOp` → `cw_pick_xxx_action.py`,与上报侧 `kernel/cw_action_report/<action>.py` 一动作一文件对称);备战域保留域前缀惯例(`cw_prep_*_action.py`);一类多清单行(注册表两行同指一 op)随 op 类单文件落。捆绑多 op 的文件违反本条款,禁新增捆绑文件。

**用户裁定（坐标按下标取自状态容器,2026-09-22）**:**选择类动作 op 的点击坐标从 game state 按下标获取——策略侧只输出下标(idx),动作 op 按 `param.idx` 从状态容器选项槽取该选项的点击坐标执行;坐标由观察上报写入(规范单一源 = screens/op-layer.md §1.1「选择坐标观察上报」)。** 键特形:专家邀请函动作类型 `idx = -1`(现金为王)→ 独立 `cash_point` 字段显式分支(禁负下标直取列表——Python 负下标回环 = 静默错点最后一卡);商店域键 = 物理槽 slot(BuyCard 动作类型无 idx,槽 1 基)。坐标域缺席/下标越界/元素缺坐标 = 守卫断言 AssertionError 显式报错,禁控制流分支、禁回退。画面 op 决策半现算机械坐标经 env 传参的旧形态(如 `OverlayPickExecEnv.target`)= 待修问题,随收敛批停用;禁新增第二坐标源。

禁止的写法(现有代码里还存在的 = 待修问题,逐批改掉;禁新增):

- **分两步上报**:点的时候只记一条日志,等确认真的生效了才补写结果(先发出后落地两相形态已全域停用,现役零例,禁回潮);
- **等下一轮看画面才补写**:点完不写结果,等下一轮重新截屏、看到弹窗没了,才把选择结果补进 game state;
- **探下一个画面才上报**:先看看有没有跳到下一个画面,再决定上报;
- **判重/防重复保护**:选择面绝不第二次给相同的牌(游戏事实),同一个选择不可能被上报两次——真上报了两次只可能是代码 bug,按 bug 修,不为它加防重复保护。

写错了的最终纠正手段 = 下一帧重新读画面,以实际读到的为准;不是在动作层做事后确认。

**归属说明(每类需求去哪一层)**:

| 需求 | 归属层 |
|---|---|
| 「动作有没有生效」的落地判定 | 观察侧对账(reconcile):挂起预期 vs 下一帧实读,失配 = 纠偏/缺陷台账;入口 = 画面 op 生命周期 reconcile 段 |
| 动作失败后的重试 | 决策循环 / 失败网:逻辑态保持事实,下一帧策略对未完成事项自然重派;重派预算由外循环节点轮次预算封顶(`node_max_retry_times`),无动作级重试 |
| 动作点不响/拖不动本身 | 动作层修可靠性:点击链坐标、时序、确认序列——不为它加验证这种复杂度 |

在档更完整表述(用户裁定 2026-09-10,裁定原文现住 `screens/op-layer.md` §1.2「验证不是生命周期段」节;原宿主 `operations/cw_screen/cw_screen_op_base.py` 类 docstring 已随该基类停用删除):「动作 op 只管机械执行,禁止做任何验证,也禁止在画面 op做验证。如果观察正确,动作 op 没生效,那就是动作 op 有 bug,不应该为了 bug 增加验证这种复杂度。」同款裁定另见 `operations/cw_screen/_overlay_confirm.py` 模块头(零验证形态(用户裁定:动作层不做效果验证,判效归下一帧观察))。

op 形态(动作 op 重组 as-built):动作 op = `CwActionXxxOp`,继承框架 `SrOperation`(原 `cw_action_base.py::ActionOp` ABC 已删除),构造签名 = `(ctx, param, env)`,域依赖经 env 结构化传入(`PrepExecEnv`/`ShopExecEnv`/`OverlayPickExecEnv`);op 内机械执行后**直调自己的上报函数**(`kernel/cw_action_report/report_action_<snake>_param`,状态容器逻辑态单点;发出即职责完成;返回值已登记例外与旁路字段语义见本文件 §2.3)。

**转移动作后果声明与喂入(as-built)**:

- 「转移动作」= 落地后世界画面/进程前进的动作(全集 18,声明终值表 = §4.8)。
- 上报函数在动作生效出口(`applied=True`)构造下一画面声明 `WorldDecl`(`kernel/cw_world_decl.py`):两维 = `next_screen`(动作后确定的下一画面 screen_info 档名,`''` = 无画面/局终)与 `trigger`(推进分派类别,`''` = 纯画面转移);载体 = `LogicOutcome.world_decl`,拒绝/未发出出口 = None。
- 动作 op 自上报后紧跟一行 `cw_sim_ports.declare_world(outcome.world_decl)` 把声明喂给 sim;一次动作多支上报 = 每支上报出口各自紧跟一行(现役唯一多支 = 补给:选卡上报 + 节点推进上报两支),round 结果 `data` 携带最后一份声明;非转移动作 `world_decl` 恒 None,无喂入行。
- 局终(无后继):`sequence_next` 无后继(超出建模域)时零写入零效果 tick 仍返回 `applied=True, reason='match_end'`,并声明空画面 `WorldDecl(next_screen='', trigger='node_advance')`——局终声明事件式,重复上报幂等(同 run 再发的 `match_end` = 同一终局事件,零状态破坏)。`applied` 契约 = 「实际推进落账位」,在 `report_node_advance` 终局出口单点扩展为「终结动作落地事实」。
- 喂入行与机械执行同判,op 侧零分支:实机(端口未装)= no-op,sim(装配后)= 驱动后端按 `trigger` 分派推进;sim 消费与对账契约权威版本 = [../sim/sim-design.md](../sim/sim-design.md) §6.3。

**overlay 登记与动作上报的关系(as-built)**:弹窗类「画面出现事实」由状态容器登记(`kernel/cw_overlay_register.py` 三个登记入口 + 九类登记目录——封闭集,新增类型必须登记)承载,与动作上报的关系分三族——①**开件直登族**:OpenBox/OpenBookcard/OpenTome 上报内登记(kind = `box_card`/`expert_invite`/`star_tome`,成功分支才登),弹窗出现与动作落地同点;②**选卡消费族**:八个 pick 上报(pick_partner/pick_megastar/pick_planner/pick_wish_trial/pick_fortune/pick_star_tome/pick_box_card/pick_expert_invite)函数体内消费同 kind 登记(`consume_screen_change`,sim/实机同一行代码),选卡落地即弹窗处理完毕;③**判据登记族**(不经动作 op):巨星/planner/占卜屋/伙伴/祈愿/阿哈由 kernel 值回调(`kernel/cw_faction_callbacks.py`,deployed 逻辑写尾)或对应上报登记,消费 = 实机备战底屏兜底清空 / sim 懒呈现位。登记生命周期权威版本 = [../sim/sim-design.md](../sim/sim-design.md) §4。

**决策侧参数现算契约(用户裁定 2026-10-17)**:动作参数的合法性由**现算纪律**保证,不靠 op 侧校验。同帧性承诺限定域 = 单动作决策环(备战 act `operations/cw_screen/cw_screen_prep.py` 单动作决策循环每动作重 decide、shop visit act `operations/cw_screen/cw_screen_shop.py` 单动作循环;decide 读状态容器 → 产参数 → op 立即执行,op 面对同一状态容器——坏参数只能是决策逻辑 bug,自然异常即正确处置)。

- **边界载体登记(现役生产路径,不适用同帧性纪律句)**:战斗链批量发射(`launch_prepared_battle`,`operations/cw_loop.py`)——`_battle_chain_deploy_moves` 一次产整批 DeployMove 参数,逐个 execute 间状态容器被自上报改写。其陈旧化治理 = report 静态域拒绝 + 观察 reconcile(既有),「持有窗口 = 同一发射批内」为该路径的登记豁免;除战斗链外全仓无第二处参数跨决策帧持有。
- **违纪承接双层**:纪律下陈旧参数不应存在;违纪现行承接 = ①商店环 proposal 守卫(`cw_shop_action_ops.py::guard_proposal_vs_expected`,loop 级同帧复检,既有)+ ②动作 op 取值自然异常(兜底)。自然异常覆盖边界:Python 语义会炸的形态(None/正越界);索引类负值形态不炸(to_slot ≤ 0 → `pts[-1]` 合法索引静默错槽)——**参数违法类校验收拢到对应动作 op 内、由 op 守卫断言**(`raise AssertionError`,消息语义保留;BuyCard 槽解析/槽号越界、DeployMove 落位越界含 to_slot ≥ 1 下界闭合负下标缺口);集中式 validate() 的逐动作参数分支已按同原则全部退役进各 op(校验落点单一形态 = 下「校验落点契约」)。
- **校验落点契约(用户裁定 2026-10-17)**:动作参数合法性校验的唯一落点 = **对应动作 op 内守卫断言**(`raise AssertionError`,消息含定位信息——动作类型/参数名/非法值/合法域)——op 是参数语义的唯一所有者,校验随语义走;执行器不设集中参数校验(原 `PrepActionExecutor.validate` 已随批退役,决策环调用点随之删除;集中式 if-elif 链迫使执行器知晓全部动作参数语义 = 按层打散参数知识,废弃理由随本条申报)。与「用户裁定（坐标按下标取自状态容器,2026-09-22）」的关系:该裁定的「守卫断言 AssertionError 显式报错,禁控制流分支、禁回退(禁负下标直取列表——负下标回环 = 静默错点)」即本条的坐标域先例,危害分析引彼条原文——凡负值/零值可合法索引的槽位参数,守卫断言下界必须显式闭合(现役 = DeployMove `to_slot ≥ 1`);与「用户裁定（点完即写,2026-09-21）」的关系:守卫断言即「显式报错修根因,不在 bug 上做无畏的补丁操作」在参数域的现役形态——参数违法 = 确定性 bug,响亮暴露修根因,不吸收、不回退、不静默纠偏。
- **落点指针**:BuyCard 行 = §4.1;DeployMove 行 = §4.2;坐标裁定域 = 本节上文「用户裁定（坐标按下标取自状态容器）」。

## 2. 边界澄清(什么属于申报,什么属于验证)

### 2.1 动作未生效的治理链(现行为模型申报)

动作 op 层的三件落地判读机制(部署/买牌/穿戴:动作发出后的画面差读数申报、连续未生效计数锁存、重派刹车)已全部拆除——动作 op 层不存在「动作是否生效」的判定面,残留即违 §1。现行为模型:

- **动作 op = 机械执行 + 发出即记账**:点击/拖拽发出即记账(账本/逻辑态直写);机械不能发出(定位缺失/无对象/输入契约拒绝)= round_fail 未发出事实,受阻细节由回执 `reason` 码承载(§5 回执契约)——这是「发出」侧的动作事实,不是效果判定。
- **动作未生效的治理链**:下一入口 heavy 帧实读对账(挂起预期 vs 实读)失配 → 失配告警停机 → 按真 bug 追根因(根因纪律见 §1 用户裁定（禁以偶发结案）:不存在偶发丢失,禁止以偶发结案)。
- **决策环按新观察自然重规划**:重派 = 决策循环按新观察自然重派,预算由外循环节点轮次预算封顶,无动作级重试;系统性吞输入由决策环通用失败网/哨兵兜底。

### 2.2 固定等待族(等待不是判效)

动作后的等待全部是固定时长常量(等待归产生动画的操作):采晶矿 2s / 开箱 1.8s(`terminal_wait`)/ 开典籍、开书册卡 `_OVERLAY_ANIM_WAIT_S` / 刷新 1s(`REFRESH_CLICK_SETTLE_WAIT_S`)/ 卖出 1s / 穿戴拖前 settle 0.5s(`PREP_DRAG_SETTLE_WAIT_S`)/ 工具拖拽后 1.5s / 部署拖后 2.0s(羁绊徽章动画)/ 出战弹窗 1s(`POST_CLICK_WAIT_S`)/ pick 确认 0.6–1.2s / 遭遇与补给刷新 2s(重掷动画覆盖,时序 #19/#23)。无轮询、无「画面就位才算成功」判读;弹窗/画面是否就位交下一帧观察与外循环画面分支接住。

### 2.3 上报通道(动作事实怎么出去)

- **prep 域旁路字段** `env.detail`(`PrepExecEnv`;`env.emitted` 零消费死字段已随 receipt-applied-retire 退役——未发出事实的承载 = 回执 `reason` 码,见 §5 回执契约):机械执行摘要;节点直调 `op.run()` 的 round 结果恒 success(单节点动作 op 零重试语义,框架循环机制归外层包络与访问结束面所有)。
- **返回值已登记例外**:已登记例外仅 `CwActionStartBattleOp`(round 结果 = 点击序列已执行,找不到按钮 = False——未发出事实非判效,消费面 = 执行器 `last_launch_ok` 旁路 → `cw_loop` 战斗分支;按钮/弹窗确认 area 缺失零检查 = 取值直接使用自然异常报错);`CwActionBuyCardOp` 槽解析/槽号越界两防御口已改 op 内守卫断言 AssertionError(「决策侧参数现算契约」段),round 结果恒成功态 = 发出事实(与 action_exec.md §2 失败通道句对齐);`CwActionWearEquipOp` 回恒 success,落地与否不是返回值语义,归观察侧对账(§2.1)。prep 域 round 结果失败态 = 机械未发出事实(定位缺失/无空槽),非效果判定。
- **pick 族旁路** `env.round_result`:轮次流转语义,不是动作成败回执;`operations/cw_screen/_overlay_confirm.py::emit_overlay_confirm` = 机械确认 + 固定等待 + 无条件 round_retry——不读屏判「是否生效」。**待修问题标注(§1「用户裁定（点完即写）」)**:「落地与否由下一轮重入的入口观察裁决(入口词不在 = 已离开本画面返回 success;仍在 = 重做确认)」的现役写法 = 待修问题,逐批改为「确认点完立即上报结果,本次访问直接结束」;禁新增。
- **落地登记注册表**:已随历史批次停用消失(`cw_screen_op_base` / `EMIT_TRIGGERED_DECLARED` 现为零符号,2026-09-21 清理);节点屏刷新计数全域 = 剩余语义观察写端(`encounter_refresh_left`/`supply_refresh_left`/`env_refresh_left`/`strategy_refresh_left`,各屏观察 report 摄入;遭遇/补给 sim 写端与补 sim 写面差异见 fields.md §3.4.1/§3.4.2;原 on_outcome 发出型钩子与 live +1 写点均已停用)。

## 3. 偏离清单

核查面 = §4 全量清单(注册表行数/op 类数以代码现值为准,清点单一源 = `cw_action_registry.py::_REGISTRY`)逐文件核读 + `operations/cw_op/` 全目录 grep(`until_find_all`/`until_not_find_all` 零命中) + **§4.7 组合壳/直调体全量**(2026-10-16 open-shop-action-spec 批教训:open_shop 直调体曾带幂等观察/落地复查/round_retry,因住 §4.7 区躲过历轮清点,在 sim 机械 IO 关闭下放大为回执与业务事实相反——核查面自该批起覆盖组合壳,逐条对「验证/重试/判断」三禁):**零条**「动作 op 内做画面转移 until 验证」或「op 内自带重试循环」形态(open_shop 直调体已按规范重组为单段机械执行 + 发出即记账恒 True);注释面与实现一致,无旧口径残留。

## 4. 全量清单(基准 = `operations/cw_op/cw_action_registry.py`)

覆盖声明:注册表**全行**列示(现值 35 行;§4.1–§4.5,动作类型清单条目类 → op 类逐行对齐;投资两屏拆类后 PickInvestStrategy/PickInvestEnv 两行同指一 op;计数以代码现值为准);动作类型清单 `kernel/cw_vocab.py::CW_ACTION_TYPES` 共 38 类(现值),除注册表现值 35 键外,其余 3 类不经注册表分发,见 §4.6。§4.1–§4.5 文件路径省略前缀 `operations/cw_op/`。决策循环逐动作消费细则 = [../screens/prep.md](../screens/prep.md) §4,不在本篇重复。

### 4.1 商店族(3 行)

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| BuyCard | CwActionBuyCardOp | `cw_buy_card_action.py` | 点买一张牌:槽号按期望态 payload 定长槽阵列解析(身份同一性优先,退化按 (name, star))→ screen_info「商店牌-N」中心点击(槽解析失败/槽号越界 = op 内守卫断言 AssertionError——「决策侧参数现算契约」段,禁兜底坐标静默点击);恒发出即记账(total_buy / spend_executed / bought_names,满栏多买补差 k = `merge_buy_k`);落地与否归观察侧对账(§2.1)。参数 = `action.card`(ShopCard)。发出条件 = 商店决策面产 BuyCard(义务/策略买入)。 |
| RefreshShop | CwActionRefreshShopOp | `cw_refresh_shop_action.py` | 刷新商店(终结动作,结束后返回主循环重进 = 入口观察重建牌面):点刷新钮 → 固定等待 1s(`REFRESH_CLICK_SETTLE_WAIT_S`;等待不是判效)→ 刷价记账(状态容器刷价现值读口,失读回基价常量)→ 自上报 `report_action_refresh_shop_param` 同一上报口三支(计数触发 `record_refresh` paid/total;免费次数扣减分支 = `gs.free_refresh_left` Field 值判定与扣减,None = 未观察保守按付费——次数是记账面非决策闸;随机采样分支 = kernel 采样器 `cw_shop_deal.sample_shop_deal` 经 `write_logic_rand` 写牌面随机态,observe 覆盖差异 = 预期内不进失配告警)。体内零读屏零验证(§1「用户裁定（零新增读屏）」合规);「刷新是否生效」归观察侧对账,执行侧零重试。发出条件 = 商店决策产 RefreshShop(现役发出点 = 利息线闸门,策略语义见 strategy-docs)。 |
| CloseShop | CwActionCloseShopOp | `cw_close_shop_action.py` | 关店恒可用终结 op:执行位 = 帧上找「按钮-收起」真点击(miss = 店已关,幂等出口;miss 回执 reason 码 = `定位缺失(按钮-收起)`,见 §5)+ 固定等待 + 自上报 `report_action_close_shop_param` 清场;零转移验证(点击未生效 = 外循环重分发自然重派)。发出条件 = 商店决策无动作可做时主动选它终结本画面访问(全函数契约要求的恒可用终结)。 |

### 4.2 备战族(9 行,含工具原子 7 行;注册表单类型单行)

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| SellBench | CwActionSellBenchOp | `cw_prep_sell_bench_action.py` | 卖备战席角色:drag 备战栏槽中心(area 序 = `bench_idx` 状态容器槽表下标,零换算)→ 出售区(`prep_actions.drag_bench_to_sell` 单一源),机械执行后 op 自上报 `report_action_sell_bench_param`(状态容器逻辑态单点:置 empty + 回金 + 装备回收 + 溢出分支)+ 固定等待 1s(卖出金币动画)。发出条件 = 备战策略产 SellBench;`reason` 为归因记录字段非指令。 |
| LevelUp | CwActionLevelUpOp | `cw_prep_level_up_action.py` | 买经验单击:找钮「备战标识-购买经验」(env 锚定优先,回落自读 area = 业务定位逻辑;按钮坐标取值直接使用,缺失零检查 = 使用点自然异常报错,禁兜底坐标)单击一次 + 光标 park(防光标压等级显示区毒化 OCR);零授权零计数(击数推导/经验批支付门全上移发出点,击数 > 0 = 每帧发出前置);金币写入 = op 自上报 `report_action_level_up_param` 按 `action.cost`×击数直写。升 N 击 = N 帧。发出条件 = 备战策略产 LevelUp(cost 现算装载)。 |
| DeployMove | CwActionDeployMoveOp | `cw_deploy_move_action.py` | bench→上阵单步拖拽(腾位链专用):源拖点 = `bench_idx` area 序直取,落位 = 载荷 `(to_row, to_slot)` 直指(排内 1 基画面槽号 → 对应排 area 序 `to_slot - 1` 取拖点;落位意图全部在载荷,执行边零现读零决定);拖拽语义 = 游戏规则:目标槽空 = 放置、有人 = 交换交互,执行层不判断占位、不拒、禁静默换槽;载荷槽越出画面槽位数(含 <1 负下标)= 参数违法,op 内守卫断言 AssertionError(「决策侧参数现算契约」段;坐标裁定域禁负下标——负下标回环 = 静默错点)。拖后零落地判定,落地归观察侧对账(§2.1)+ 固定等待 2s(羁绊徽章动画窗,保留面)。发出条件 = 备战策略按部署计划单一源(`mandate_v1/deploy_plan.py::deploy_plan_moves`)逐帧产 DeployMove(bench_idx / to_row / to_slot / faction)。 |
| SellDeployed | CwActionSellDeployedOp | `cw_sell_deployed_action.py` | 卖上阵角色:drag 排槽中心 → 出售区(`deployed_idx` → 排/物理槽号内联换算;落点 `sell_point` 单一源),机械执行后 op 自上报 `report_action_sell_deployed_param`(状态容器逻辑态单点:摘槽 + 回金 + 装备回收)+ 固定等待 1s。发出条件 = 备战策略产 SellDeployed(deployed_idx = deployed 槽表下标)。 |
| WearEquip | CwActionWearEquipOp | `cw_wear_equip_action.py` | 穿装备单步:owned 网格按名定位源件 → 拖至目标角色排槽(row/slot = 画面物理槽 1 基);拖后零落地判定,落地归观察侧对账(§2.1);目标槽位坐标取值直接使用,缺失零检查 = 拖拽使用点自然异常报错;源件未定位(owned 网格现读落空)= 未发出事实(round_fail 受阻码,下帧重派重算计划)。机械执行后 op 自上报 `report_action_wear_equip_param`(状态容器 equips 写 owned −1 + 目标角色 equips +1)。发出条件 = 备战策略穿戴计划(kernel `_build_equip_wear_plan`)逐帧取首项产 WearEquip(item_name / char_name / row / slot)。 |
| CollectOre | CwActionCollectOreOp | `cw_collect_ore_action.py` | 点晶矿:载荷 = 有序晶矿心坐标点击列,纯机械逐个点(mouse_move + click + park),零读屏零排序零截断(大晶矿优先/上界挑选归决策侧 kernel `select_ore_clicks`);固定等待 2s 等飞行动画;席满未点开的晶矿由下一帧观察回补。机械执行后 op 自上报 `report_action_collect_ore_param`(状态容器精确摘晶矿 + 晶矿金窗登记内聚)。发出条件 = 备战策略产 CollectOre(points = 按点击序的坐标列)。 |
| OpenBox | CwActionOpenBoxOp | `cw_open_box_action.py` | 开简易武装箱(终结动作,terminal_wait=1.8s):`read_armory_boxes` 识别 → 点「开启」(槽中心 + `BOX_OPEN_DY=41`)→ 固定动画等待;返回主循环,武装箱选择画面分发选卡。无箱/指定槽无箱 = 不发出(`emitted=False`)。发出条件 = 备战策略产 OpenBox(slot=None = 第一箱)。 |
| OpenTome | CwActionOpenTomeOp | `cw_open_tome_action.py` | 开秘密典籍(非终结):`read_tomes` 识别 → 点槽一次开启(游戏侧单次点击即弹)→ 固定动画等待;星徽四选一 overlay 弹出由外循环阶段一身份分发 CwScreenBookcard 接管选卡。无典籍/槽不匹配 = 不发出。机械执行后 op 自上报 `report_action_open_tome_param`(腾位写入)。发出条件 = 备战策略产 OpenTome(slot=None = 第一典籍)。 |
| OpenBookcard | CwActionOpenBookcardOp | `cw_open_bookcard_action.py` | 开书册卡(**访问终结**,`terminal_wait=1.8`):`find_bookcards` 识别 → 点槽中心 → 固定动画等待(`_OVERLAY_ANIM_WAIT_S`);开卡 = 专家邀请函弹窗在场 = 新事实,返回主循环按该画面分发选卡(`CwScreenExpertInvite`)。无卡/槽不匹配 = 不发出。机械执行后 op 自上报 `report_action_open_bookcard_param`(腾位写入)。发出条件 = 策略器 entry ① prep 实体面卡片臂(状态容器 bench kind `'bookcard'` 触发;原入口清场段 `cw_screen_prep._clear_prep_cards` 代发通道已撤销,用户裁定 2026-09-19 开卡时机归策略器)。 |

工具原子七类(注册表 7 行同指 `CwActionToolUseOp`;机械半 = owned 网格按注册名定位工具 icon → 拖至目标(equip 模式 = owned 目标件 icon;char 模式 = 角色排槽中心)→ 固定等待 1.5s;零消耗确认交叉核对,消费真值 = 下一帧装备区读数。上报 = **机械执行直接上报写状态容器**(用户裁定 2026-09-21:动作 op 不判成败,上报无条件按成功写;字段写操作权威版本 = `kernel/cw_action_report/tool_use.py`,记账载体 = `gs.equips` 合并单笔写——消耗移除与效果同笔禁拆两笔;冶金炉/特权卡变异面不走获得链不触发获得回调,投影仪复制走 `gain_character` 链,零写分支统一保留证据 `tool_*` 缺陷行)。发出条件 = 装备域判据适用面 `cw_equip_env.evaluate_tool_actions` 准入后策略产动作):

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| FurnaceUse | CwActionToolUseOp | `cw_tool_use_action.py` | 冶金炉:equip 模式 = 单笔 `write_logic_rand` 合并写(移除工具 ∧ 目标件 → 同类别采样替换;采样池 = `cw_sim_equips.furnace_reroll` 同源,rng 关键字带缺省);char 模式 = ①equips rand 合并(移除工具+穿戴+各件采样替换)②行域穿戴清空 logic。变异面不走链;采样命中后果表键集落采证行 `furnace_mutate_consequence_candidate`。 |
| PrivilegeCardUse | CwActionToolUseOp | `cw_tool_use_action.py` | 特权赋予卡:equip 模式分支 = 单笔 `write_logic` 合并(移除工具 ∧ 目标件名 → `privilege_counterpart` 特权名替换);char 模式分支 = fail-closed（信息缺失时宁可不写,不猜值）零写保留证据(待实机测试,`tool_privilege_worn_unsupported`)。 |
| WrenchUse | CwActionToolUseOp | `cw_tool_use_action.py` | 拆装扳手:两笔 `write_logic`——equips 合并(移除工具 ∧ 追加目标角色全部穿戴件)+ 行域穿戴清空;工具消耗品 −1 合并同笔。 |
| PrecisionWrenchUse | CwActionToolUseOp | `cw_tool_use_action.py` | 精密拆装扳手:同拆装扳手两笔 logic,**equips 不移除工具**(无限次用不递减)。 |
| StaffProjectorUse | CwActionToolUseOp | `cw_tool_use_action.py` | 员工投影仪:①equips `write_logic` 移除工具;②复制走获得链 `gain_character(char,1★)`(落位→回调→3 合 1 升星;复制触发三合一 = 口述·权威 2026-09-21);费用门 ≤3 注册表现读前置查(防御纵深,超门保留证据零写)。 |
| PerfectProjectorUse | CwActionToolUseOp | `cw_tool_use_action.py` | 完美投影仪:同员工投影仪走链,无费用门。 |
| LuckyTokenUse | CwActionToolUseOp | `cw_tool_use_action.py` | 好运令牌:零写 + 保留证据行(`tool_token_not_admitted`;判据适用面现役 fail-closed 永不进准入,发出点登记待办、禁无判据发出;写端随判据批收敛)。 |

### 4.3 转场族(2 行)

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| StartBattle | CwActionStartBattleOp | `cw_start_battle_action.py` | 出战点击序列(终结动作,terminal_wait=3):找「按钮-出战」(备战+开商店两屏查,叠加帧兼容;免战子态查「按钮-跳过」同语义点它,子态经 `env.skip_substate` 上报)→ mouse_move + click → 固定等 1s → 单帧截图清点两类真弹窗(未达上限警告 = 勾选+确认;前台无角色 = 确认;弹窗检查业务逻辑保留,弹窗确认 area 取值直接使用,缺失零检查 = 确认点击使用点自然异常报错)**[§1「用户裁定（零新增读屏）」登记的待修问题:执行后转移面识别,清法候批]**;零转移验证,返回主循环重判。round 结果 = 点击序列已执行(已登记例外;找不到按钮 = False,经执行器 `last_launch_ok` 旁路)。机械执行后 op 自上报 `report_action_start_battle_param`(免战递减内聚)。发出条件 = 备战策略产 StartBattle(环出口,豁免屏蔽)。 |
| OpenShop | CwActionOpenShopOp | `cw_open_shop_action.py` | 开店注册行 = terminal 承载行:执行抛 AssertionError(开店流程编排截流在 `cw_screen_prep._act_execute_default` → `_open_shop_phase`,可达即分派漏斗被绕过);类属性承载终结判定/等待(terminal=True,terminal_wait=1.0)。开店 = 唯一普通形态(无受限变体;受限会话进出店同走本路径,访问内消费由策略决策入口自限)。发出条件 = 备战策略产 OpenShop(进商店访问的唯一入口动作)。 |

### 4.4 观察族(1 行)

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| Obs | CwActionObsOp | `cw_obs_action.py` | 重观察动作,口径由 `scope` 选(值域封闭集(新增取值必须登记) = `cw_vocab.OBS_SCOPES`)。**scope='in_place'**(缺省)= 当前画面重新观察上报,不返回主循环:执行体 = 宿主画面 op `reobserve_in_visit`(现役唯一宿主 = 备战 CwScreenPrep)heavy 观察链重跑,漏斗直写状态容器 = 观察边界对账;零点击零拖拽;自上报 = 零写占位(状态容器更新通道 = 观察漏斗本体);非终结,执行后帧代次标 full(终局意向重估触发,同入口帧;贵段消费侧键守卫限频),决策环原地续跑。重观察见事件 overlay = 抛 `CwObsOverlayBail` 返回主循环重分发(捕获点 = 备战决策循环,画面路由归外循环)。**scope='outer_loop'** = 返回主循环重新观察:决策环在参数校验步骤之前**分支拦截**(不经本表派发、不进执行器、不写动作记录,行为 = 原 HoldFrame「本帧无动作」帧已并入,用户裁定 2026-09-20),注册行仅为完备测试在场 + in_place 路径派发用。发出域无重观察能力(env.op 未接入调用)= AssertionError 显式报错(策略器 bug)。发出条件 = 策略需要新鲜观察(in_place = 随机面/不确定面动作后要真值再决策;outer_loop = 本帧无动作,返回主循环重判/等待,自旋防护归外循环 stall 防线)。 |

### 4.5 事件线 pick 族(12 行;域 env = `OverlayPickExecEnv`;机械参数适用范围见段首申报,op 类体内零决策)。**登记消费**:全族八个有上报的 pick 函数体首段消费同 kind 状态容器登记(§1「overlay 登记与动作上报的关系」族②;aha 无上报 → 实机兜底清空/sim 懒呈现位消费)。**坐标源待修问题(§1「用户裁定（坐标按下标取自状态容器）」,用户裁定 2026-09-22)**:全族现役坐标源形态不一——多数 = 决策半现算经 `env.target`,遭遇 = 动作 op 内 area 现取(取值直接使用,缺失零检查 = 使用点自然异常报错),伙伴 = `env.op._pick_point` 决策半现取——逐屏收敛到「观察上报入状态容器坐标伴随域(fields.md §3.4.5a)、动作 op 按 idx 自取」;收敛完成前现形态为合法过渡,禁新增第二坐标源(待修问题登记先例 = StartBattle 行的零新增读屏违例)。

**机械参数适用范围(as-built;申报单一源)**:

- 适用范围 = 选卡定位 + 域载荷,经 env 传入;确认钮不属机械参数 env 传入范围——确认查找与点击 = 动作 op 执行体 `round_by_find_and_click_area`(全族统一,用户裁定 2026-09-22;§1「用户裁定（零新增读屏）」「瞄准」已登记唯一允许查找;area 缺失 = 显式 round_fail,禁兜底坐标静默点击);投资两屏 `env.confirm` 变体随同批停用。
- 选卡定位 = `env.target`(决策半现算,过渡期屏;已收敛屏 = 动作 op 按 idx 自状态容器坐标伴随域取点,巨星先行);例外两行:PickEncounter = op 体内 `area_center` 候选卡(取值直接使用)、PickPartner = 宿主属性经 `env.op`。选卡定位坐标待修问题 = 本节标题行(§1「用户裁定（坐标按下标取自状态容器）」,观察上报收敛),此处不重复。
- 域载荷逐行 = `idx`(10 行 = 全族除 PickEncounter/PickPlanner)/`need_select`(巨星)/`branch_type`+`norm_item`(策划)/`unselected`(伙伴)/`match`+`picked`(补给)/`entry_keyword`(投资两屏/卜者组装而 run 体现役未消费);PickEncounter 组装 = 零域字段。(件名归一现役在决策半与动作上报层 = op-layer.md §1.1 :34 登记的待修问题,收敛终态 = 观察侧转换、动作上报只携 idx,逐批收敛禁新增)
- 「op 类体内零决策」= 零选择/零分支型判定(全在决策半),瞄准定位查找非决策。逐行落点 = 各行动作列/对照表。

逐行 as-built 对照(段首附表,与各行动作列互查):

| 行 | 选中定位源 | 确认钮源 |
|---|---|---|
| PickEncounter | 体内 `area_center`(遭遇卡-其一/其二;取值直接使用,缺失 = 使用点自然异常;env 组装 = op-only) | 体内 `round_by_find_and_click_area`(按钮-选择) |
| PickSupply | `env.target` | 体内 `round_by_find_and_click_area`(按钮-确认) |
| PickMegastar | 状态容器 `megastar_opts[idx].xy`(env idx-only;`need_select` 开关经 env) | 体内 `round_by_find_and_click_area`(按钮-确认选择) |
| PickPartner | `env.op._pick_point`(宿主画面 op 属性;env 无 target) | 体内 `round_by_find_and_click_area`(按钮-确认选择) |
| PickPlanner | `env.target` | 体内 `round_by_find_and_click_area`(按钮-骇入确认) |
| PickInvestStrategy / PickInvestEnv | `env.idx` / `env.target` | 体内 `round_by_find_and_click_area`(按钮-确认,屏名按宿主屏类解析) |
| PickFortune | 状态容器 `fortune_opts_xy[param.idx]`(env op-only) | 体内 `round_by_find_and_click_area`(按钮-确认选择) |
| PickWishTrial | `env.target` | 体内 `round_by_find_and_click_area`(按钮-确认选择) |
| PickBoxCard / PickStarTome / PickExpertInvite | `env.target` | 无确认步(点卡即选) |

**上报形态 = 全族即时上报**(§1「用户裁定（点完即写）」;有字段写操作的各屏 = 投资两屏/补给/遭遇/策划/装备,点完确认或点卡即选后立即按成功写完整结果;其余屏 = 零写占位上报):先发出后落地的两相与证据锁存形态已全域清除,零落地复查补写面,禁新增分步写法。

| 动作类型 | op 类 | 文件 | 说明 |
|---|---|---|---|
| PickEncounter | CwActionPickEncounterOp | `cw_pick_encounter_action.py` | 遭遇节点选卡确认链(事件屏统一迭代改即时上报):点遭遇卡(`idx`=0 左卡/其余右卡;area 取值直接使用,缺失零检查 = 使用点自然异常报错,禁兜底坐标)→ 固定等 0.8s → 「按钮-选择」area 查找点击确认(`round_by_find_and_click_area`,全族统一)→ **发出即写** `report_action_pick_encounter_param`(`kernel/cw_action_report/pick_encounter.py`:值组装 = 状态容器 `encounter` payload 槽所选卡,离屏/越界保留证据不写);点击发出后即结束本次访问,落地归观察侧。发出条件 = overlay 决策半产 PickEncounter(idx = 候选下标)。 |
| PickSupply | CwActionPickSupplyOp | `cw_pick_supply_action.py` | 补给节点选卡确认链(即时单相):`env.target` 点卡 → 固定等 0.6s → 点「按钮-确认」→ **立即自上报完整结果** `report_action_pick_supply_param`(owned 规范名 0..n 件(首件 + 附加件名组,画面 y 序)+ 单位获得写入 + 装备后果链一口写;三个 applied 出口前统一调选卡时点检查 `check_strategy_take_all_supply`——全都要·银 R-choice 插入位置,事件消耗制选卡即耗,未持卡零扰)+ `report_node_advance(supply_confirm)`;点击发出后即结束本次访问,确认未生效由外循环重识别重派;刷新圆钮点击留在画面 op。发出条件 = 决策半产 PickSupply(param 携归一件名/附加件名组/角色名;`env.target` 坐标现算 = §1「用户裁定（坐标按下标取自状态容器）」收敛完成前的合法过渡形态)。 |
| PickMegastar | CwActionPickMegastarOp | `cw_pick_megastar_action.py` | 盛会之星「选中 → 确认」链(`env.need_select` 驱动:True = 先点状态容器 `megastar_opts[idx].xy` 候选选中 + 固定等 0.6s;False = 跳过选中直发确认)→ 「按钮-确认选择」area 查找点击确认(`round_by_find_and_click_area`,全族统一)→ 固定等 0.9s;纯机械单发,确认未落地 = 下一帧门复检自愈(宿主 `round_wait` 循环推进,不烧节点重试预算)。发出条件 = 决策半产 PickMegastar(选中半迁入本 op;`chosen_megastar` 写端与选中旗标留在画面 op,派发前写)。 |
| PickPartner | CwActionPickPartnerOp | `cw_pick_partner_action.py` | 列车同行伙伴确认链:未选中实证(或首轮强制)下重点选候选(`env.op._pick_point`)→ 固定等 0.7s → 「按钮-确认选择」area 查找点击确认(`round_by_find_and_click_area`,全族统一;找不到 = round_retry 上报,交框架轮次机制);脉冲计数与选中态宿主 = 画面 op。发出条件 = 决策半产 PickPartner。 |
| PickPlanner | CwActionPickPlannerOp | `cw_pick_planner_action.py` | 骇入策划确认链(即时单相):`env.target` 点卡(避开卡内「详情」按钮区的选中点几何归决策半单一源)→ 固定等 1.2s → 「按钮-骇入确认」area 查找点击确认(`round_by_find_and_click_area`,全族统一);点卡 = 机械单发(无详情面板检测;面板若真弹出归下一帧外循环重识别自愈)。**确认点击后立即自上报完整结果** `report_action_pick_planner_param`(`kernel/cw_action_report/pick_planner.py`:条件分支 rider 先行 → equip 分支入栏+后果链 / upgrade 分支变换窗三态+档行 `lv999_cost_tier` / unknown 保留证据 / unrouted 兜底零写,`branch_type`/`norm_item` 经 env 随派发透传);点击发出后即结束本次访问,确认未生效由外循环重识别重派。发出条件 = 决策半产 PickPlanner。 |
| PickInvestStrategy | CwActionPickInvestOp | `cw_pick_invest_action.py` | 投资策略屏选择行(投资两屏迁移批:清单拆类,与 PickInvestEnv 两行同指一 op,机械链同构):点选中位(`env.idx`/`env.target` 决策半现算)→ 固定等 0.7s → 点确认钮 → **立即自上报完整结果** `report_action_pick_invest_strategy_param`(session 自 ctx 取)→ 整支走获得链 `kernel/cw_gain_chain.py::gain_invest_strategy`(无效载荷拒绝 → active_strategies 按名字去重追加 → 效果账本登记分支 → `on_strategy_gained` 效果分派;出参 reason=`gain_chain_applied`)。 |
| PickInvestEnv | CwActionPickInvestOp | `cw_pick_invest_action.py` | 投资环境屏选择行(同上共 op):点选中位 → 固定等 0.7s → 点确认钮 → **立即自上报完整结果** `report_action_pick_invest_env_param`(上报 = `param.idx`,名字自状态容器 `invest_env_opts` 标准名单一源按序号提供——观察层标准化门产出,规范 = op-layer.md §1.1;状态容器缺读/idx 越界 = 显式失败)→ 整支走获得链 `gain_invest_env`(无效载荷拒绝 = 链内零写保留证据 `pick_invest_invalid_payload` → active_env 注册 + portal 登记 + `on_env_gained` 效果枚举;出参 reason=`gain_chain_applied`)。 |
| PickFortune | CwActionPickFortuneOp | `cw_pick_fortune_action.py` | 命运卜者强化三选一(已并入现行形态;坐标随上报收敛改取点源):点卡(状态容器 `fortune_opts_xy[param.idx]`,缺 = 守卫断言)→ 「按钮-确认选择」area 查找点击确认(`round_by_find_and_click_area`,全族统一)→ 自上报(零写)。 |
| PickWishTrial | CwActionPickWishTrialOp | `cw_pick_wish_trial_action.py` | 祈愿试炼(已并入现行形态):点卡(`env.target`)→ 点「按钮-确认选择」area 确认 → 自上报(零写)。 |
| PickStarTome | CwActionPickStarTomeOp | `cw_pick_star_tome_action.py` | 星徽秘典(点卡即选):选中点击 + 动画等待,零确认步 → 自上报(零写)。 |
| PickBoxCard | CwActionPickBoxCardOp | `cw_pick_box_card_action.py` | 武装箱(点卡即选):同上形态。 |
| PickExpertInvite | CwActionPickExpertInviteOp | `cw_pick_expert_invite_action.py` | 专家邀请函(点卡即选):idx=-1 = 现金为王(点「卡-现金为王」区,非候选卡槽)。 |
| PickEquip | ~~CwActionPickEquipOp~~ | — | **已停用**(2026-09-22 用户裁定:选择装备屏为古老时期误判、游戏内不存在——画面 op/动作 op/动作类型/上报函数全套删除;本行留名供旧档案对号)。 |

### 4.6 动作类型已登记、不经注册表分发的类(3 类)

- `RefreshNodeOptions` / `RefreshSupply` / `RefreshInvestCards`:三刷新建议动作,走各画面既有点击链(遭遇刷新终结分支/补给刷新终结分支/投资逐卡刷新)。**执行语义全域规范 = 刷新即终结、结束本次访问返回主循环重观察 + 闸 = 剩余次数观察真值**(规范单一源 = [../screens/op-layer.md](../screens/op-layer.md) §1.4;遭遇/补给两链已随剩余次数化修复,全链合规)。
- (Obs `scope='outer_loop'` 口径同为分支拦截型、不经本表派发,但其动作类型有注册行(§4.4 in_place 路径派发用),不属本节「无注册行」豁免面。)

### 4.7 层级区别:动作域之外的组合壳 / 画面 op(不进注册表,列出以划清「动作 op」边界)

- `CwScreenDeploy`(部署机画面 op)**已停用删除**——部署 = 备战决策环动作:`CwActionDeployMoveParam` 原子序列由 mandate 动作发出点逐帧现算,经 `CwActionDeployMoveOp` 机械拖拽 + 自上报 `report_action_deploy_move_param` 推进部署逻辑态(路径速查 = [../screens/deploy.md](../screens/deploy.md));落地事实归备战环入口观察对账。
- `CwOpCloseShop`(`operations/cw_op/cw_op_close_shop.py`)**已停用删除**——关店执行位并入动作 op `CwActionCloseShopOp` 真机械执行(幂等已关出口 + 清场上报;编排壳的「拦截 + no-op + 代点」旧形随商店访问两 node 化消亡,见 [../screens/shop.md](../screens/shop.md) §4)。
- `_open_shop_phase`(`operations/cw_screen/cw_screen_prep.py`):开店编排——OpenShop 动作的流程层执行半(机械开店 `open_shop`(`operations/cw_op/cw_op_open_shop.py`,规范动作形态:单段机械执行 + 发出即记账恒 True,定位缺失 = 唯一受阻码出口(reason=`定位缺失(按钮-商店)`,回执契约见 §5);sim 机械 IO 关闭下点击经端口 click_answer 受理 = 状态副本(GameState)推进通道,呈现/离屏牌面补写/刷价由其触发) → `visit_open_shop` 商店画面 op 直驱;开店 = 唯一普通形态,无受限变体);回执 `(完成事实, detail)` 中完成事实 = 商店访问完整收工(非动作成败回执)。
- `run_buy_waves`(`operations/cw_screen/cw_screen_shop.py` 前身文件)**已停用删除**——商店访问 = 画面 op 两 node 规范形态(`CwScreenShop`:观察 node 恰一次 + 决策动作 node round_wait 单动作循环,全动作统一路径零特例拦截;规范权威版本 = [../screens/shop.md](../screens/shop.md) §2/§4);段机器(波循环/段间判定/段尾对账)随伪终结刷新一并消亡。
- `PrepActionExecutor`(`prep_actions.py`):备战域执行器——备战动作 op 体迁后的替身函数的接缝(stub seam)宿主(原方法薄委托);`PrepExecEnv` 定义处。

### 4.8 转移动作后果声明终表(18 动作)

喂入契约 = §1「转移动作后果声明与喂入」。`trigger` = sim 后端推进分派类别(封闭集单一源 = `sim/cw_sim_backend.py::ADVANCE_TRIGGER_KINDS`;`''` = 纯画面转移,sim 仅按 `next_screen` 推进画面,零专属过程);`next_screen` = 声明的下一画面 screen_info 档名。声明列终值(上报落点 = 声明构造处,op 落点 = 喂入行所在动作 op):

| # | 动作 | 上报落点 | op 落点(`operations/cw_op/`) | trigger | next_screen |
|---|---|---|---|---|---|
| 1 | settle_confirm | `kernel/cw_game_state.py::report_node_advance` | `cw_op_settle_confirm.py` | `node_advance` | 节点序推导(见表下规则) |
| 2 | supply_confirm | 同上(同函数按确认来源参数分) | `cw_pick_supply_action.py` | `node_advance` | 同上 |
| 3 | StartBattle | `cw_action_report/start_battle.py` | `cw_start_battle_action.py` | `battle_resolve` | 货币战争-结算 |
| 4 | PickEncounter | `cw_action_report/pick_encounter.py` | `cw_pick_encounter_action.py` | `battle_resolve` | 货币战争-结算 |
| 5 | OpenBox | `cw_action_report/zero_writes.py` | `cw_open_box_action.py` | `open_box` | 货币战争-备战-武装箱选择 |
| 6 | OpenBookcard | `cw_action_report/open_bookcard.py` | `cw_open_bookcard_action.py` | `''` | 货币战争-备战(专家邀请函画面的出现事实 = 登记 kind `expert_invite`,上报内直登) |
| 7 | PickInvestEnv | `cw_action_report/pick_invest_env.py` | `cw_pick_invest_action.py`(与 #8 两行同指一 op) | `pick_invest_env` | 货币战争-备战 |
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

`node_advance` 两行(#1/#2)的 `next_screen` 非固定值:由上报函数按 kernel 后继原语 `sequence_next`(`kernel/cw_node_schedule.py`,带场字段现值参)+ 生效序位 `effective_node_pos` 推导——`sequence_next` 无后继(超出建模域)= 局终声明事件式 `''`(`reason='match_end'`);位面切换轮 = `货币战争-位面过渡`;其余按新节点类型映射(battle/reward→备战、supply→补给、encounter→遭遇节点、boss→BOSS 简报)。#12 补给 = 现役唯一单 op 多支上报:选卡上报声明(#12)先喂,节点推进上报声明(#2)后喂,round `data` 携带后者。纯转移类(#6/#13-#18)选卡/关店的字段写操作端全在其上报函数内(腾位/零写占位/离屏),后端只按 `next_screen` 幂等返回。OpenTome 不构造声明(零画面转移语义:腾位后底层屏恒备战,星徽四选一画面的出现事实 = 登记 kind `star_tome` 承载,呈现随下一动作 advance 收尾),非转移集成员。

## 5. 回执契约(receipts)

动作执行回执的**单一权威版本 = fields.md「动作 op 行为模型」段的回执契约节**(shape/词表/invariant/LogicOutcome 边界),本节只留动作域视角的指针与登记义务:

- 回执唯一写点 = `note_action_receipt`(`kernel/cw_game_state.py`),shape = `{op, reason='', detail?, screen?, **extra}`;`reason=''` = 正常发出,非空 = 机械受阻事实码(**封闭词表**,新码先登记本节再使用)。
- 词表与子码枚举单一源 = `prep_actions.py` 码化映射表;收缩后闭集(用户裁定 2026-10-17 建档缺失检查段删除 + 参数违法类改 op 守卫断言后) = `定位缺失(按钮-商店)`/`定位缺失(按钮-收起)`/`未执行:定位缺失(按钮-出战|按钮-跳过)`/`未执行:无简易武装箱|无秘密典籍|无书册卡|owned 网格未定位族`——旧「五族不变」表述作废;`未生效:*` 族随 StartBattle 弹窗 area 缺失检查删除零供给退役,`槽解析失败`|`槽号越界` 随 BuyCard 两防御口改 op 内守卫断言退役(商店 visit 环映射表 `_SHOP_VISIT_BLOCK_CODES` 整表退役)。
- 边界:上报函数族出参 `LogicOutcome.applied/reason`(拒绝语义,§4 各行与 logic-updates 权威版本)**不是回执字段**——受理附注不入回执,拒绝可见性 = 后续批(outcome 冒泡机制,独立设计)。
- `applied` 布尔已退役(receipt-applied-retire 批):退役前历史 journal 回执含 applied 键,渲染器排除表承接,旧数据不迁移。
