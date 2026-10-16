# 画面 op 层设计(op-layer · 行为规范 + 上报接口 + 形态分型 + 观察解析工具箱)

> 本文 = 画面 op 层唯一设计正本:**§1 行为规范**(每个画面 op 必须表现成什么样,合同)、**§2 上报接口**(观察数据怎么进容器)、**§3 形态分型**(35 画面 op 的形态分类)、**§4 适用范围边界**(本层不承载的机制)、**§5 观察解析工具箱**(obs/ 地图)、**§6 流程转点观测锚**(在库机制)。各画面的具体文档 = 同目录各篇(一画面一文档,索引 = [README.md](README.md))。代码锚 = `文件::符号名`(路径根 = `src/sr_od/application/currency_war/`)。
> 术语:全库术语表 = [README.md](README.md)「术语表」节(内置动作/零判效/落地复查/观察即真值/逻辑态/对账/容器/帧与帧代次/返回主循环/中断恢复的对局/动作类型清单/数字来源标注四形态/“零X/X即Y”句式)。**逻辑态** = 动作执行后不经观察、按游戏规则推算并直写容器(GameState,游戏状态对象,下同)的预期状态,例:买牌后金币 −40、备战席 +1;下一帧观察不符以实际观察为准。**obs** = 一个画面一次观察的结果对象(类型化载荷);**report** = 该画面在 kernel 侧的上报函数,把 obs 写进容器。**GameState/记录模型** 字段级正本 = [../game_state/fields.md](../game_state/fields.md)——记录模型管「记什么」,本文管「谁在什么时机喂进去、决策怎么消费、动作怎么落回」;冲突以字段正本为准。

## §1 行为规范

### 1.1 总则:每个画面 op = 两个 node(观察 → 决策动作),直继承 SrOperation

画面 op 不设共享基类:每个画面一个独立类直继承框架 `SrOperation`,类内声明两个 node。

```
画面 op 入口
  ├─ 观察 node(is_start_node):
  │    门(画面身份/节点完成判定;身份门 miss = round_fail 返回主循环重新判定,
  │        完成门 miss = 画面已离开,round_success 结束本次访问;就绪等待变体门
  │        (已登记唯一,WaitOneOne)= 未就绪未超时 = round_wait 等下一帧,
  │        超时 = round_fail(见下方「已登记变体」条))
  │    → 显式读屏(本 op 唯一读屏点)→ 组装 CwScreenXxxObs
  │    → report_screen_xxx_obs(gs, obs) 落容器(match/gs 缺席的局外兜底路径跳过)
  │    → obs 挂实例属性,round_success 进决策动作 node
  └─ 决策动作 node:
       落地复查(顶部;仅限未迁移屏:上轮动作已发 → 画面标志不在 = 已生效
         → 补记录 + success 结束本次访问;即时上报屏 = 发出即终结,零落地复查)
       → 决策(从容器零参读;恰一个动作;备战空动作 = CwActionObsParam
         scope='outer_loop' 合法结束本次访问——原 HoldFrame 并入,用户裁定 2026-09-20;
         备战域发出决策 = mandate_v1 决策链最先检查的发出点(`bridge._launch_front_check`,
         `decide_prep_screen` 入口消费),出战就绪帧短路三遍编排直接产
         受限商店访问/出战意图——决策面在策略器,CwScreenPrep 决策段
         消费意图落执行)
       → 动作(经动作 op 机械执行;动作 op 自上报推进逻辑态,不读屏)
       → round_wait 循环推进(node runner 每轮给新帧)
```

- **两 node 职责**:观察 node = 门 + 读屏 + 观察结果上报,无循环、小预算(已登记变体例外唯一 = 等待 1-1 就绪等待,见下条变体注);决策动作 node = 落地复查(仅限未迁移屏)+ 决策 + 动作,迭代一律 `round_wait`(不烧 node 重试预算)。act node 保留在用 `node_max_retry_times` 值(仅框架异常路径消费,不新建上限机制)。**投资两屏/补给/遭遇/策划/装备已迁即时上报 + 发出即终结形态**(用户裁定 2026-09-21,action_ops.md §1「用户裁定(点完即写)」;遭遇 = 事件屏刷新链统一迭代拉齐,策划/装备 = 删除两步写法的迭代拉齐):零落地复查——发出确认链(动作 op 内点完确认或点卡即选,立即按成功写结果)后 `round_success` 终结返回主循环;确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派,修法 = 点击链可靠性。
- **已登记变体:等待 1-1 就绪等待(全部画面 op 中唯一观察轮询;用户裁定特殊等待)**:`operations/cw_screen/cw_screen_wait_one_one.py::CwScreenWaitOneOne` 的观察 node = 就绪轮询主体。这条特例存在的原因:1-1 开局补给动画长且无结束标志(`docs/game/currency_war/research/screen_flow_timing.md` #5/#29;op 模块头「用户裁定特殊等待」)——无画面身份门可判:备战 id_mark「货币战争-备战.标识-备战阶段」在开局补给与备战两个阶段出现在同一位置、区分不了画面,只能判「备战面板就绪」而非画面身份;无完成门可判:未就绪 ≠ 画面已离开,miss 即 success 结束本次访问会落未知画面重判;无动作可迭代:act 零动作,循环无处挂靠。所以轮询放在观察 node 里,这是全库唯一允许观察 node 内循环的特例。口径:id_mark 命中 = obs 装载 + 占位 report → `round_success` 进 act(无动作 success 结束本次访问);未就绪未超时 = `round_wait(ONE_ONE_POLL_INTERVAL_S)` 等下一帧(wait 语义不耗框架 retry 预算);超时 ≥ `ONE_ONE_MAX_WAIT_S` = 存图保留证据 + `round_fail` 交外循环(失败治理出口)。边界:①闭集 = 本条唯一,新增观察轮询屏先登记本条再写入代码;②固定超时 = 失败治理出口非迭代上限,与「循环无上限规范」不冲突(彼条适用于决策动作 node 循环与外循环轮次推进,失败类出口不属于迭代上限);③轮询轮与超时轮不装载 obs,id_mark 判定外不读屏——读屏点纪律不放宽;④超时后重派预算归外循环(`operations/cw_loop.py::CwLoop.OP_FAIL_REDISPATCH_LIMIT` 网)不变。as-built 细节单一源 = [wait_one_one.md](wait_one_one.md);行为测试 = `sr-od-test/test/sr_od/application/currency_war/test_obs_arch_phase_screens.py::test_wait_one_one_anchor_hit_and_poll_round_wait` / `::test_wait_one_one_timeout_leaves_evidence`。
- **观察标准化门(用户裁定 2026-09-22,全域行为规范)**:观察内容在所属域存在标准注册数据(名字类:投资环境/投资策略/角色/装备等注册表)时,观察 node 必须在观察时把读数转换成标准注册数据再上报——转换两段:①形变归一(分隔符/全半角等 OCR 形变族)后精确匹配;②不中再 LCS 相似匹配(域级单一实现 `kernel/cw_obs_core.py::lcs_resolve_strict`,阈值常量住各屏);两段皆不中 = 转换失败。**相似匹配(LCS)阶段执行次高分差拒判——最高分未明显高于次高分(差值不足已登记常量)= 歧义 = 转换失败,禁直接取最高分**(先例 = 投资环境屏;用户裁定 2026-09-22 全族统一)。**任一候选转换失败 = 观察失败**:观察 node round_fail 早退、不写容器不上报,交外循环重观察重读(读不准重读,禁带病上报)。多候选命中同一注册名(选项互斥屏)= 识别质量不足以区分,同判转换失败——重复名合法的观察面(同卡多张/名单类)不适用此判,各屏转换成功性的附加边界由屏契约(screens/ 各篇)登记。标准化后下游全链只在标准名上工作:决策消费标准名打分;动作上报只携带选择序号(idx),名字由容器标准名单一源按序号提供,动作/上报层零名字转换。收敛在途:投资环境屏已落地;其余名字类观察屏为登记已登记的待修问题,逐批收敛,禁新增未标准化直报。
- **选择坐标观察上报(用户裁定 2026-09-22,全域行为规范)**:观察上报选项时,除将识别内容归一化到标准注册数据(观察标准化门,本节前条)外,还必须一并上报该选项的具体坐标存入 game state——即选中这类选项的具体坐标;归一化与坐标在同一次观察一并入容器。**坐标单一真相源 = 观察上报**:由决策侧半现算改为观察时上报——策略侧只输出下标,动作 op 根据下标从 game state 获取坐标来执行;命名规约(名字由容器单一源按序号提供,本节前条)的同款思路扩展到坐标,动作/上报层零坐标现算。适用范围 = 商店与各需选择的 overlay。判断标准(防双义):点击坐标是不是"这次观察读到的选项"的一部分。是(哪怕位置固定,如商店 5 个槽位)→ 坐标必须随观察一起上报;不是(确认钮/刷新钮等固定控件)→ 仍从 screen_info 现取。过渡期:容器还没有坐标字段的新画面,随该画面第一批建字段,不允许临时从环境对象现算坐标(禁第二坐标源不因骨架未落而豁免)。收敛在途:在用坐标源形态不一(多数 = 决策半现算经 env 传入动作 op;遭遇 = 动作 op 内 area 现取,缺失显式失败;商店 = 动作侧 screen_info 现取),逐批收敛到观察上报,禁新增第二坐标源。
- **决策控制分层铁律(用户裁定 2026-09-21;规范单一源 = [../flow/README.md](../flow/README.md) §1)**:凡用于**控制决策行为**的闸门与判断(政策闸/动作发出闸/花金与消费限制/动作值域过滤)必须在**策略侧**实现(策略器决策时自限,会话状态存 StrategyState);流程侧——含画面 op 的决策动作 node——**禁止任何形式的决策闸门与政策判断**。决策动作 node 的职责只有两件:调策略器拿动作、把动作交给动作 op 执行。流程侧的合法判断面仅限:防 bug 守卫断言(非控制流)、失败治理与停机(失败出口非决策)。出现「需要判断该不该放某个动作过」= 分层错误,修法 = 迁策略侧。
- **画面 op 不支持局外单独调用(用户裁定 2026-09-22)**:画面 op 是对局上下文内的组件,不支持脱离对局(`cw_match` 缺席)单独调用调试,此类支持代码不做。不设单跑防御分支;无 match 场景属未支持用法,由上下文缺失自然失败(用户裁决 2026-09-22 全族删门),不设任何兜底决策路径——流程侧兜底决策同时受决策控制分层铁律(本节前条)禁止。
- **循环无上限规范(用户裁定)**:框架不负责多轮循环的上限限制——决策动作 node 的循环与外循环轮次推进均不设迭代数上限(无防御帽、无兜底计数,健康循环永不因计数被截断);不收敛/死循环 = **策略实现 bug**,响亮暴露(挂起可观测),修策略根因。失败类出口(异常 fail、外循环 fail 熔断、未知画面兜底)不属于迭代上限。循环兜底不变量 = 1.4 恒可用终结。
- **出口三语义**:决策动作 node 的循环只有三种出口——①**终结动作**(1.4,执行即本访问结束返回主循环;投资两屏/补给/遭遇/策划/装备的选卡确认链按此语义:发出即终结);②**落地复查成功**(动作已生效,补记录后结束本次访问;仅限未迁移屏);③**异常 fail**(策略异常/执行异常,错误传播交外循环,非防御上限;投资两屏/遭遇的空候选/决策无有效输出也走此出口——不发出无依据的动作;遭遇空候选 = 不点击直接结束本次访问、返回主循环重新识别画面,禁盲选派发)。备战域另有合法结束本次访问通道:策略器返回 `CwActionObsParam(scope='outer_loop')`(本帧无动作,返回主循环重新观察;原 HoldFrame 并入,`kernel/cw_vocab.py::CwActionObsParam`)= round_success 返回主循环,不折算战替身;策略发出 `CwActionObsParam(scope='in_place')` 环内重观察见事件 overlay = `CwObsOverlayBail`(动作 op 抛出,决策循环捕获)返回主循环重新分发(画面路由归外循环,环内不消化)。
- **落地复查放在决策动作 node 顶部(仅限未迁移屏)**:「确认已发 → 下一轮标志不在 = 已生效」是动作生效判定,属循环出口判定,不回观察 node。chosen_* 类落地记录在此刻写(见 §2 动作事实边界;巨星/伙伴 = 选择点维持(发出前写,各屏文档 §6 已登记)、祈愿/星徽等 = 落地复查点维持,投资两屏已改动作执行时经获得链记,遭遇已改动作侧发出即写,补给的确认即写由画面 op 选卡分支承载)。
- **显式读屏只在观察 node**:决策动作 node 迭代用 node runner 进 node 时给的 `last_screenshot`(`round_wait` 每轮新帧)。除观察 node 外,画面 op 内不调 `screenshot()`。**已登记例外只有三类**:①**(动作通道)**策略显式发出 `CwActionObsParam(scope='in_place')`(环内重观察)= 经注册表派发 `CwActionObsOp` → 宿主画面 op `reobserve_in_visit`(在用 = `CwScreenPrep`)重跑 heavy 观察链——漏斗直写容器即「重新观察上报」,决策环原地续跑(通道细则 = [../flow/action_exec.md](../flow/action_exec.md) §3);②**(终结分支保留证据读)**终结动作执行后、结束本次访问前的一次机械重读——零决策零判效,读数只作缺陷台账保留证据输入,不进决策、不判生效(生效判定仍归落地复查/观察对账;在用 = `cw_screen_invest_env.py::CwScreenInvestEnv._decide_and_act` 刷新终结分支的刷后帧重读,依据 = 用户裁定 2026-09-14 刷新零效果保留证据 + 统一动作工厂批次的裁决(把该重读迁到观察侧))。③**(编排壳直调机械动作读)**:画面 op 自己的循环里直接调用底层动作函数(如开店)时,允许函数内部再截一次屏。原因:宿主截图是本轮开始拍的,循环里前面的动作已改变画面,函数必须取新帧才能判断「店是否已开」。这次截屏只用于:判断动作是否已做过、找到点击目标;不做观察上报、不写游戏状态、不做决策。在用成员封闭集 = `operations/cw_op/cw_op_open_shop.py::open_shop`(宿主 op 限 = `CwScreenPrep`);宿主语境封闭清单 = 该成员的全部生产直调点,编辑时点现值一处——`cw_screen_prep.py::CwScreenPrep._open_shop_phase`(显式开店);新成员与新宿主语境先登记本条再写入代码,禁类推扩员。新增读屏点必须先登记本条再写入代码;除上述三例外,其余路径不读屏。
- **外循环形态不变**:画面识别分发、轮次推进、停机/遥测钩子([../flow/outer_loop.md](../flow/outer_loop.md))不随本规范改动。

### 1.2 动作 op 契约与动作粒度

- **动作 op 形态** = `CwActionXxxOp`(框架 `SrOperation` 子类,构造 = `(ctx, param, env)`):机械执行后直调自己的上报函数(`kernel/cw_action_report/report_action_<snake>_param`),逻辑态由上报函数族独占写入,动作 op 自身不记账。**上报 = 点完即写完整结果**(用户裁定 2026-09-21,契约单一源 = action_ops.md §1「用户裁定(点完即写)」:执行即按成功处理,分步上报/落地证据等待禁;有容器写的全部 pick 屏(投资两屏/补给/遭遇/策划/装备)已按此形态即时上报,先发出后落地证据的两步写法与证据标志已全域清除)。执行异常上抛。**验证不是生命周期段**:动作 op 只管机械执行,禁做任何验证、禁设「验证失败→重试/恢复」编排;动作未生效(观察正确而下一帧对账失配)的处置 = 修动作执行链本身的可靠性(点击链坐标/时序/确认序列),禁止以验证+重试结构兜底。**观察识别不是动作 op 的职责**(用户裁定 2026-09-21,规范单一源 = action_ops.md §2 上报通道与判效边界):动作 op 无论执行前后均不做观察识别——不保留证据读、不验证读、不读数落账;唯一允许的查找 = 点击/拖拽目标定位(瞄准,不是观察);画面状态的读取一律归观察域,真值归下一帧观察。节点推进上报(结算/补给确认的 `report_node_advance` 调用)同样**点击即上报**——不探下一画面 id_mark、不等转移证据、不设证据 miss 分支(用户裁定 2026-09-21,原「转移证据上报时点门例外」随证据机制整体停用;推进落账的唯一门 = kernel 观察态门)。
- **overlay 登记消费(选卡动作族)**:八个选卡上报(pick_partner/pick_megastar/pick_planner/pick_wish_trial/pick_fortune/pick_star_tome/pick_box_card/pick_expert_invite)在函数体内消费同 kind 的容器登记(`kernel/cw_overlay_register.py::consume_screen_change`,sim/实机同一行代码)——选卡动作落地即弹窗处理完毕,消费归上报不归执行器。开件三动作(open_box/open_bookcard/open_tome)上报内**直登**(kind = box_card/expert_invite/star_tome,成功分支才登记)。判据登记(巨星/planner/占卜屋/伙伴/祈愿/阿哈)归 kernel 值回调(`kernel/cw_faction_callbacks.py`,deployed 逻辑写尾)与相关上报,**不经动作 op**。宿主画面 op(备战/商店)在每动作执行后检查容器登记非空 → 确定性提前返回主循环(取代等重观察发现弹窗);外循环身份解析对登记条目两段式优先(pending 首中),识别回备战底屏兜底清空(生命周期正本 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。
- **动作后果声明喂入(转移动作;全集与声明终值 = [../flow/action_ops.md](../flow/action_ops.md) §4.8)**:转移类上报函数在 `applied=True` 出口构造后果声明 `WorldDecl`(`kernel/cw_world_decl.py`,两维 = `next_screen` 下一画面档名 + `trigger` 推进分派类别;载体 = `LogicOutcome.world_decl`,拒绝/未发出出口 = None),动作 op 在自上报出口紧跟一行 `cw_sim_ports.declare_world(outcome.world_decl)` 喂入(多支上报 = 每支出口各自紧跟一行),round 结果 `data` 携带最后一份声明;非转移动作无喂入行。声明对实机 = **数据面**:journal 记「预期画面」供与实读画面 diff 对账(画面漂移早期警报料),禁作判效断言;实机端口未装 = no-op,喂入行与机械执行同判零分支。喂入在动作 op 内(上报出口 `LogicOutcome` 在手即喂),画面 op 派发点不转递、结束本次访问判断不消费声明——结束本次访问语义仍由注册表 `terminal` 单独承载(refresh 族「访问终结但画面档不变」与局终「必须结束本次访问但无下一画面」为此边界两锚)。sim 面 = 声明即驱动(`trigger` 分派 + `next_screen` 等值对账,契约正本 = [../sim/sim-design.md](../sim/sim-design.md) §6.3)。
- **动作粒度**:买一张 = 一个 op、卖一张 = 一个 op、买经验一击 = 一个 op(单击 +4XP;升级 = XP 过门槛表结果,非动作)、刷新 = 一个 op。**满栏例外**:板凳满时点合成槽位,游戏机制自动多买至 3 的倍数张(每张原价)——一击多张 = 一个动作 op,逻辑态直写按实际张数计。复合宏动作(整档替换)已全链停用。
- **每个动作 op 单独一个文件(用户裁定 2026-09-22)**:动作 op 一 op 一文件,禁多个动作 op 同居一个文件——与上报侧 `kernel/cw_action_report/<action>.py` 每动作一文件对称(§2.1);禁新增同类同居。

### 1.3 守卫断言与对账边界

- **合法性判定全部内化于策略器**(提议侧约束);执行侧只余**守卫断言**——防 bug 路栏而非控制流分支,非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)。在用守卫 = `operations/cw_op/cw_shop_action_ops.py::guard_proposal_vs_expected`(提案对象在期望态存在且未被消费——防策略器算术 bug,恒炸)。守卫登记(逐屏条目,新增屏随其批补录):
  - 命运卜者:`operations/cw_screen/cw_screen_fortune.py::CwScreenFortune.act` 决策出口——守卫①:decide_fortune 返回动作类型清单外的值/None = 具名 round_fail,不发出无依据的动作(§1.1 出口③);守卫②:pick.idx 越界 = 守卫断言 AssertionError(本节)。
  - 星徽秘典:`operations/cw_screen/cw_screen_bookcard.py::CwScreenBookcard.act` 决策出口——守卫①:候选空 = 具名 round_fail,不发出无依据的动作(§1.1 出口③);守卫②:decide_star_tome 返回动作类型清单外的值/None = 具名 round_fail,不发出无依据的动作(§1.1 出口③);守卫③:pick.idx 越界 = 守卫断言 AssertionError(本节)。
  - 专家邀请函:`operations/cw_screen/cw_screen_expert_invite.py::CwScreenExpertInvite.act` 决策出口——守卫①:decide_expert_invite 返回动作类型清单外的值/None = 具名 round_fail,不发出无依据的动作(§1.1 出口③);守卫②:pick.idx 域外 = 守卫断言 AssertionError(本节;动作类型值域 0..3 ∨ -1,-1 = 现金为王放行,域外负值禁并入现金分支)。
  - 选择伙伴(列车同行):`operations/cw_screen/cw_screen_partner.py::CwScreenPartner.act` 决策出口——守卫①:候选空 = 具名 round_fail,不发出无依据的动作(§1.1 出口③);守卫②:decide_partner 返回动作类型清单外的值/None = 具名 round_fail,不发出无依据的动作(§1.1 出口③);守卫③:pick.idx 越界 = 守卫断言 AssertionError(本节)。
  - 遭遇节点二选一:`operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act` 决策出口——守卫①:decide_encounter 返回动作类型清单外的值/None = 具名 round_fail,不发出无依据的动作(§1.1 出口③);守卫②:pick.idx 越界 = 守卫断言 AssertionError(本节)。
守卫不读屏。op 框架既有的重试/等待语义属 execute 执行实现层,不算第二道合法性门。
- **对账唯一发生点 = 观察边界(硬规则)**:对账(推算状态 vs 下一帧实读逐项比对,对不上 = 有 bug)唯一合法时点 = **观察数据经 report 进入 game state 的观察边界**(画面 op 观察 node / 动作自上报后的下一观察帧),由 game state 执行比对与仲裁(`kernel/cw_reconcile.py`;锚定机制属 game state 层内部实现);**其余任何状态/op 层不做双态比对,也不做店内原地重建**——动作级「发出即登记 + 下一帧对账」不属于双态比对(归观察侧闭环)。**摄入逻辑住屏文件**:该画面观察进容器的全部逻辑(写点/屏级门/派生/对账特判)住 kernel 屏文件(§2),op 层只组装 obs 并调用 report;依赖读帧的观察审计链(如备战羁绊显示核对)不迁 kernel,保留在画面 op 观察 node(§2 适用范围边界)。

### 1.4 终结动作集与期望态生命周期

- **终结动作是一等动作**(策略器主动选择,不是循环逃生口);执行即画面 op 结束、返回主循环。**恒可用终结不变量**:每个决策画面的动作空间至少含一个恒可用终结动作(商店 = 关店、备战 = 开战、单选族 = 确认、等待/切换类 = 推进)。终结判定现值 = 注册表 op 类 `terminal`/`terminal_wait` 属性,消费点经 `action_op_class_for` 读取(禁消费点私表);终结集总表 = [README.md](README.md) §6。
- **刷新 = 终结(全刷新链统一规范,用户裁定 2026-09-21)**:一切「刷新/重掷」类动作(商店 `RefreshShop`;事件屏三刷新建议动作——遭遇/补给/投资两屏)= 终结动作:执行 = 点钮 + 固定动画等待 → 本访问结束返回主循环 → 重进 = 入口重建,新牌面/新选项由入口观察现读。理由 = 刷新是唯一引入新事实的动作,牌面/选项 = 决策输入,决策输入必须经入口观察重建(观察即真值)——**禁访问内重读新选项、禁观察上报二次覆盖写、禁重调决策**(§1.1 读屏点纪律的刷新链具体化)。违反处 = 登记的待修问题,逐批改掉,禁新增(遭遇/补给链已修复,在用全链合规)。
- **刷新闸 = 剩余语义观察真值(全域,用户裁定 2026-09-21)**:「可否再刷」判定一律消费屏显「剩余次数：N」观察读数——观察 report 摄入 `*_refresh_left` 剩余语义字段(读缺跳写,None = 未观察;字段先例 = `env_refresh_left`/`strategy_refresh_left`,`../game_state/fields.md` §3.4.3/§3.4.4);**禁「已用计数」推算**(原 `encounter_refresh_used`/`supply_refresh_used` 两已用字段已随剩余语义化停用,全链现为剩余语义观察写端)。**商店域接入(非例外)**:免费刷新次数 = `gs.free_refresh_left`(Field,剩余语义;观察锚定 = 入口观察漏斗 shop-open 段刷新钮三态,免费态锚次数/付费域锚 0/判不出跳写)。**商店刷新与事件画面不同**:读不到次数时不拒绝刷新(次数只用于记账,刷不刷由策略决定);免费次数字段有三个写入来源(观察读取、刷新后扣减、发放时登记),不一致时触发既有的字段失配告警。
- **期望态生命周期**:入口观察(重建,即对账)→ 逐动作逻辑态直写(经动作自上报函数族,不读屏)→ 终结(失效,返回主循环下次重建)。逐动作转移函数的写入分支规格 = [../game_state/logic-updates/](../game_state/logic-updates/README.md)(动作类型清单逐动作有逻辑态分支;清单外的动作类型 = AssertionError 响亮暴露)。
- **字段未观察态**:席位主域(bench/deployed)的「未观察」态由锚定标志 `tracked_account_observed` 承载(三态语义:None 缺省可信/False 失效未锚定,值不可消费/True 已锚定)——无任何观察锚定,与「已观察下的空」类型可分。进入 = 显式失效事件;退出 = 入口观察对账的屏幕真值写回。观察 vs 逻辑对账(含升星确认比较基线 = 主域席位视图现读,无平行第二账)唯一发生点 = §1.3 观察边界。策略消费口唯一 = game state。策略默认实现 = 商店开遇未观察 → 返回关店 → 外循环重判落回备战 → 入口观察锚定后再进店;未观察跳过的访问留遥测分键,连续循环 = 锚定失败显式失败出口,禁静默重试。
- **读屏点**:显式读屏只在画面 op 的观察 node;终结结束后外循环重分发,下一次访问的观察 node 即下一次读屏。

### 1.5 形态判据

- 画面 op 按观察/决策/上报三面的有无分型(全形态/多屏管线/节点循环/推进型空决策/画面框 op/驻留状态机/重型屏),判据与 35 屏分类总表 = §3。

## §2 上报接口(kernel/cw_screen_report/)

### 2.1 包形态

- **每画面一文件**:obs 类与该画面上报函数同居(`kernel/cw_screen_report/<画面snake>.py`);与动作侧 `kernel/cw_action_report/<action>.py` 每动作一文件对称。文件名 = 画面 snake;`__init__.py` 不暴露模块(项目惯例),消费方按画面文件名直接 import。
- **命名机械规约**:obs 类 = `CwScreenXxxObs`(商店框 op = `CwOpXxxObs`);上报函数 = `report_screen_<snake>_obs`(obs 类去前缀 `CwScreen` 去后缀 `Obs` 转 snake)。与动作上报函数族同约定:**一个「上报」概念一个形状**,动作/画面观察两族互不混用,都禁按类型聚合的分派转移函数。完备测试遍历包内 obs 类,断言 report 函数在场/不在场分侧(推进型不在场)。
- **节点推进上报族例外(触发矩阵外)**:节点推进上报走 kernel `report_node_advance`(trigger 封闭集 `{settle_confirm, supply_confirm}`),不设 `report_action_*`/`report_screen_*` 形态——推进是节点域容器语义(经推进生效原语 `advance_node_effective`),不是单动作逻辑态或单画面观察。形态归属:`settle_confirm` 宿主 = `CwOpSettleConfirm`(画面框 op 形态——非动作注册表面、无 CwAction param,构造与命名从 `CwOpOpenShop` 惯例);`supply_confirm` 宿主 = 补给确认动作 `CwActionPickSupplyOp`(注册表动作,上报点旁调);锚定写端 = `CwScreenPrep`/`CwScreenSupplyNode` 观察 node(→ `observe_node_anchor`)。
- **obs 类**:该画面一次观察的类型化载荷,字段 = 该屏读到的结构化结果 + 稳定帧引用(`screen: Any`,实机识别域载体)。纯数据:只可 import kernel 既有类型 + `cv2.typing.MatLike`。
- **sig 逐位沿原值**:上报函数的 `ChannelSig`(family/actor/evidence)沿用该画面原写点原值(如 actor='CwScreenEncounter');journal 写行语义与迁出前连续。sig 缺省 = 函数体内按原值构造;对 obs 字段缺失的防御口径与原写点一致(读缺 = 跳过写,不加强不减弱)。

### 2.2 适用范围边界

- **屏文件 = 该画面观察进容器的全部逻辑的家**:①写点(类型化 obs 载荷 → 容器字段,含屏级幂等门/懒写/恒覆写等写法);②该屏更新逻辑(写点之上的派生/优先级);③该屏对账特判(只在类型化 obs 载荷上运算的观察 vs 逻辑态比对)。**判断线(按角色分流):类型化 obs 载荷的生产半(识别 + 标准化转换,含跨帧读数稳定化、读数有效性门)住观察侧(画面 op 观察 node 或 obs/ 工具箱);落容器半(写点/屏级写门/写点之上的派生/观察 vs 逻辑对账特判)进 kernel 屏文件,恒只在类型化载荷上运算**——识别机制不出观察域,kernel 不碰像素的纪律不破;kernel→obs 直依被分包矩阵禁止,观察侧纯函数以「函数体搬进」kernel 屏文件的方式落地,不是 import。
- **漏斗边界**:`obs/cw_observation.py::read_game_state` 漏斗内部的容器写端 = 既有观察边界,不经 report 接口、不重复承接(备战/买牌的整包观察直写容器,report 相应保持占位或不设摄入面)。
- **动作事实边界(硬规则)**:chosen_*(选择落地记录)与 per-visit 位由画面 op 自身处理——其值在「确认已生效」落地复查后才可信,记账随判定点走(落地复查点/选择点),不进 report。**三个例外(均为显式用户裁定迁移)**:①**投资域收窄条款(用户裁定 2026-09-21,投资两屏迁移时扩为双屏)**:投资环境/投资策略两屏的选择事实(active_env/active_strategies)经**动作落地获得链**记(动作 op 点完确认立即上报 → `kernel/cw_gain_chain.py::gain_invest_env`/`gain_invest_strategy` 写选择事实 + 赠卡入席/溢出落位/效果账本登记,正本 = [../game_state/gain-chain.md](../game_state/gain-chain.md));②**遭遇条目(事件屏刷新链统一迭代)**:`chosen_encounter` 写端 = 动作侧发出即写(`kernel/cw_action_report/pick_encounter.py`,值组装 = 容器 payload 槽;兑现后清 = 单次消费);③**补给即写**(确认即写,由画面 op 选卡分支承载,时点前置)。其余 chosen_*(巨星/伙伴/祈愿/星徽等)维持由画面 op 自身处理(迁移归后续批次)。
- **刷新计数不在画面 op 层**:节点屏刷新计数全域 = 剩余语义观察写端——投资两屏 = `strategy_refresh_left`/`env_refresh_left`、补给 = `supply_refresh_left`、遭遇 = `encounter_refresh_left`(**均在各屏观察 report 内摄入,读缺跳写**,用户裁定 2026-09-21:game state 记录画面可观察的剩余次数);原「已用」计数(`*_refresh_used`)与遭遇 per-visit 位已停用。画面 op 决策环不识别计数、不写计数。

## §3 形态分型(35 画面 op)

画面 op 共 35 个:`operations/cw_screen/` 33 类 + 画面框 2 类(`operations/cw_op/cw_op_open_shop.py::CwOpOpenShop`、`operations/cw_op/cw_op_settle_confirm.py::CwOpSettleConfirm`;`CwOpCloseShop` 编排壳已停用——关店执行位并入动作 op `CwActionCloseShopOp` 真机械执行,见 §4 动作面。原 CwScreenEquipPick 随选择装备屏误判停用删除,2026-09-22)。分七型:

复盘认知同步义务锚(journal-review-renderer 迭代裁定,2026-10-16):**新增/停用画面 op 须同步渲染器 `tools/cw/replay_to_md.py` 画面注册表**。判定口径 = actor 带 `CwScreen` 前缀且未入 `ACTOR_REGISTRY` → 复盘报告显影「未注册写入者」缺口尾注(响亮暴露,防静默);豁免 = 快照章形态 op(CwScreenPrep/CwScreenShop/CwScreenBattleWait,由 `current_screen` 值开章,不经 actor 判定)与已知动作类豁免清单 `_ACTION_ACTOR_EXEMPT`(历史动作命名,如 CwScreenBuyCards)。同步动作:新增画面 op → 补 `ACTOR_REGISTRY`(章名/决策面/0 观察键集)与 `SCREEN_REGISTRY`(快照屏 id);新增 CwScreen 前缀动作类 → 补 `_ACTION_ACTOR_EXEMPT`。

| 型 | 判据 | 屏清单 | report |
|---|---|---|---|
| **全形态** | 观察 node + 决策动作 node + report;决策动作 node 承载完整决策循环(落地复查/分支刷新/确认链)——其中简报/BOSS 简报/位面过渡/等待 1-1/未达上限弹窗/简易武装箱六屏为**空决策变体**:决策动作 node = 落地复查 + 固定推进,零策略器问询(与各屏文档「空决策形态」声明同义;归本型仅因两 node + report 齐备;其中等待 1-1 = §1.1 已登记就绪等待变体,观察轮询口径与边界单一源见彼条) | CwScreenEncounter(刷新终结分支 + 选卡发出即终结;遭遇扩围迭代)、CwScreenSupplyNode、CwScreenInvestStrategy、CwScreenInvestEnv、CwScreenBriefing、CwScreenBossBriefing、CwScreenWaitOneOne、CwScreenDeployNotFull、CwScreenPlaneTransition(链观察)、CwScreenBoxPick、CwScreenArmoryBox | 11 屏全设;其中 WaitOneOne/DeployNotFull/ArmoryBox 在用代码中不写容器,接口为统一形态占位;BossBriefing 为真实写面(BOSS 类型直定;写语义单一源 = `kernel/cw_screen_report/boss_briefing.py`) |
| **节点循环** | overlay 单选族:两 node,决策动作 node = 零参决策 + 选卡确认链派发(`CwActionPickXxxOp` 经注册表,机械链在动作 op 内,选卡动作统一迭代);投资两屏/补给/遭遇/策划 = 发出后 `round_success` 终结(即时上报形态,零落地复查),其余屏 `round_wait` 循环推进 | CwScreenMegastar(轻门 + 懒读先例:确认访问不重读候选;选中半迁入动作 op)、CwScreenPartner、CwScreenYinLang、CwScreenFortune、CwScreenWishTrial、CwScreenBookcard、CwScreenExpertInvite | 7 屏全设(候选写 `*_opts` 槽;原 CwScreenEquipPick 随选择装备屏误判停用删除,2026-09-22) |
| **推进型空决策** | 无选择面无容器域:观察 node = 门判定;决策动作 node = 单步推进 + 落地复查;**无 report 接口** | CwScreenNextButton、CwScreenPlaneDetail、CwScreenConsumableOverlay、CwScreenEmblemDetailPopup、CwScreenItemDetailPopup、CwScreenInterruptDialog、CwScreenRefreshOddsPopup、CwScreenRoleDetailOverlay、`cw_screen_shop_card_detail.py::CwScreenShopCardDetailPopup`、CwScreenPrepLockedReturn、CwScreenAhaEquipPick(11) | 无(obs 类只记入口裁决;完备测试断言函数不在场) |
| **画面框 op**(用户裁定 2026-09-22 入表) | 不入常规分发(无 CwAction param,不经动作注册表与画面分发漏斗)、随宿主流程构造直驱(生产路径 = 宿主画面 op 委托 `execute()`);形态各自已登记 | CwOpOpenShop(推进型只读/导航两 node 变体;直调形态 `open_shop` 的读屏例外 = §1.1 例外③)、CwOpSettleConfirm(单 node 驻留,宿主 = `CwScreenBattleWait` ②段委托;推进上报 = `report_node_advance(trigger='settle_confirm')`,节点推进上报族例外 = §2.1)。(CwOpCloseShop 编排壳已停用——关店执行位并入动作 op `CwActionCloseShopOp` 真机械执行,见本节尾停用件注 2。) | 无(OpenShop = obs 只记入口裁决;SettleConfirm 推进上报走 `report_node_advance`,不经 report 接口) |
| **驻留状态机**(用户裁定豁免两 node) | 内部 while 处理结算帧、逐轮分类;出口判定(大厅终局锚/完成白名单)与分支链的轮次耦合拆进两 node 会切开 | CwScreenBattleWait(单 node `wait()`;内部结算链 `_write_settlement_observation`/`apply_settlement_cover`/SettlementState 零改动) | report 占位(结算覆盖写端在结算域,非画面观察记账) |
| **多屏管线**(用户裁定豁免两 node) | 单屏识别体的逐位面子步 = 显式 `node_from` 边图(识别/点开子步各自独立 node 与重试预算,逐子步验收);拆进两 node 会把子步序列塞回单 node 内部循环(退回不可逐屏验收的巨型节点);开/关转场(进屏/出屏)归编排 op,本形态不设决策动作 node | CwScreenPlaneIntel(6 node:识别位面 1 → 点开位面 2 → 识别位面 2 → 点开位面 3 → 识别位面 3 → 上报;识别失败 = node 重试,耗尽 = op fail 响亮暴露;编排 = [plane_intel.md](plane_intel.md)) | report 设(`report_screen_plane_intel_obs`:`plane_bosses`/`enemy_affixes` 写门——已有真值不覆写/词缀幂等) |
| **重型屏** | 观察 = 既有漏斗 + op 层散落写点并入;决策动作 = 无帽循环 | CwScreenPrep(观察 node = 环装配 + heavy 观察 + 接管补采委派(编排单一源 = `CwEntryPlaneIntel`,委派结果透传)+ 纯观察审计保留;决策动作 node = 单动作决策 `while True` 循环,无防御上限;可选域经 report 落容器)、CwScreenShop(观察 node = 兜底建核(独立单跑)+ 点击点位/升级钮/刷新钮 area 锚定 + 入口段 `_shop_entry_read` 含未识别卡停机闸 + 段首簿记(段序号/帧代次 full/预算披露/状态行/决策帧);决策动作 node = 单动作 round_wait 循环(容器零参决策 → 守卫 → 注册表派发 execute,含 CloseShop 真点击)→ 终结读注册表结束本次访问,循环内零读屏) | prep = 可选域(链域)report;shop = report 占位(容器写端在漏斗) |

停用件 1:`CwScreenDeploy`(部署机画面 op)已停用删除——部署 = 备战决策环动作(`CwActionDeployMoveParam` 原子序经 `CwActionDeployMoveOp` 机械执行 + `report_action_deploy_move_param` 自上报逻辑态),部署判定单一源驻 `kernel/cw_deploy_logic.py`,路径速查 = [deploy.md](deploy.md)。停用件 2:`CwOpCloseShop`(关店编排壳)已停用删除——关店 = 决策动作 `CwActionCloseShopParam` 经注册表由 `CwActionCloseShopOp` 执行体真机械执行(见 [shop.md](shop.md) §4)。合计 11 + 7 + 11 + 1 + 1 + 2 = 33(cw_screen)+ 画面框 2 = 35。

注(选卡动作统一迭代 + 投资两屏拆类):单选族 13 屏的选卡动作全集并入为 13 个 pick 动作 op 行(投资两屏拆类后 = `CwActionPickInvestStrategyParam`/`CwActionPickInvestEnvParam` 两行同指 `CwActionPickInvestOp`,全节点循环/全形态单选屏经注册表派发),op 内 = 选中 → 确认(或点卡即选)→ 自上报(**有容器写的投资两屏/补给/遭遇/策划/装备 = 点完即写完整结果**,两步写法/证据标志全域清零;其余屏 = 不写游戏状态的占位上报);刷新链由画面 op 内置动作执行,全域终结语义(§1.4)。

## §4 适用范围边界(本层不承载的机制)

- **画面 op 基类/端口/段迹/登记注册表/决策帧假环境分支不存在**:画面 op 只有"观察 node + 决策动作 node"两个节点,没有其他生命周期结构;下列旧机制已整体删除、不得复活(详 git 历史):五段生命周期基类、观察/动作适配器端口与装配点分流、生命周期段迹、on_outcome 落地登记注册表、决策帧观察证据注入分支。观察/决策两段职责由两 node 直接承载(§1),观察进容器由 report 接口承载(§2)。
- **刷新计数记账不在画面 op 层;闸口径全域 = 剩余语义观察写端**(规范单一源 = §1.4「刷新闸 = 剩余语义观察真值」):`*_refresh_left` 由各屏观察 report 摄入(读缺跳写,None = 未观察),画面 op 只保留 obs 刷新读数与读端闸,不写计数、不做已用推算。**商店域接入**:`free_refresh_left` 三写端同格(观察锚定 = 漏斗 shop-open 段/动作扣减 = 刷新上报函数/发放登记 = 两效果桥;None = 未观察保守按付费——次数是记账面非决策闸,细节 = §1.4 商店域接入行);付费/全量刷新计数留效果账本累计。原已用计数遗留(`encounter_refresh_used`/`supply_refresh_used`)已随剩余语义化停用,全链合规。
- **观察审计链保留在画面 op**:依赖读帧的观察审计住画面 op——备战羁绊显示对账住观察 node,投资环境刷新零效果保留证据住决策动作 node 刷新终结分支(其读屏 = §1.1 已登记例外②);均消费 obs/ 工具箱识别产物,不迁 kernel、不进 report。
- **策略判据面不在本层**:买/卖/升/刷数学归策略器(策略文档区);画面 op 只做容器零参读 + 动作编排放大。

## §5 观察解析工具箱(obs/)

一屏一解析器;识别机制不出观察域(§2 适用范围边界),解析器只回答「读到什么/可不可信」。清单(符号 = `obs/<模块>::符号`):

| 模块 | 管什么 |
|---|---|
| `cw_observation.py` | 备战屏观测主漏斗:`read_game_state` 容器直写 + 轻量回执(观察流/PHASE_FIELD_SPEC 逐字段门) |
| `cw_observe_full.py` | heavy 全面识别组装层(备战入口单次;装备域三路) |
| `cw_identity_obs.py` | 备战屏视觉身份观测(SIFT,非 OCR;bench/deployed 槽位身份) |
| `currency_war_char_id.py` | 角色识别 SIFT 模板匹配(生产用立绘模板库) |
| `currency_war_cv.py` | 备战阶段传统 CV 检测工具 |
| `cw_faction_obs.py` | 羁绊面板显示侧识别 + 与计算侧羁绊计数对账 |
| `cw_back_layout.py` | 后排槽位布局(公式 + CV 实测双通道对账) |
| `cw_equipment.py` | 装备视觉识别(手维护) |
| `cw_node_obs.py` | 节点选项观测(遭遇/补给/伙伴 → 类型化 Option) |
| `cw_node_reader.py` | 节点行类型识别(纯 CV;`read_node_sequence` 包装接入) |
| `cw_megastar_obs.py` | 巨星观察域:候选检测(弹窗标签带限定 OCR 定卡 1..N + 逐卡立绘 SIFT 交叉验证,xy = 该卡标签中心 + 已登记卡身线随卡自带)+ 标准化失败裁决门(规范 = §1.1「观察标准化门」) |
| `cw_briefing_obs.py` | 简报屏观测(敌人词缀 + 位面首领) |
| `cw_settlement_obs.py` | 结算屏观测(战后小队 HP) |
| `cw_shop_refresh_obs.py` | 商店刷新钮标价/按钮态现场 OCR |
| `cw_arbitration.py` | 观察层读数多源仲裁统一注册面 |
| `cw_resume_lock.py` | 中断恢复对局(locked-resume)检测纯函数 |
| `cw_anchor.py` | 流程转点观测锚机制(ANCHOR_REGISTRY/AnchorSpec/emit_anchor;见 §6) |

**类型化载荷出料**:`kernel/cw_screen_report/` 包 = 各画面 obs 类 + `report_screen_<snake>_obs` 上报函数同居处(§2;每画面一文件,与动作侧 `kernel/cw_action_report/` 对称)——obs/ 解析器产读数,kernel 屏文件承载「读数 → 容器」的落写语义。

## §6 流程转点观测锚(机制在库,接线待批)

- **锚** = 在流程确定性转点上触发的一次结构化观测,三要素 = 确定性触发时点 × 该时点权威事实集 × 落载体登记;是画面/动作上报面族的观测扩员,不是新机制。目的 = 让框架提供更准确的游戏观察数据(事件事实零读屏即确定;事后从散点帧推断是多次实证的缺陷类)。**观测-only 边界**:只做记录面,状态改写/效果施加出栈(payload 预留 effect_ref 槽位恒空,非空 = 红)。
- **触发三型**:landed(动作生效事实,如买牌落地 = 卡名/扣金/合成判定三事实同点唯一可得处)/ emitted(动作发出即登记,如遭遇·策略刷新计数)/ boundary(流程边界:进节点/进位面/结算)。锚点事件集 = 登记式封闭集(`kernel/cw_anchor.py::ANCHOR_REGISTRY`,在用闭集 8 锚;新锚先登记再接线,集外 = 红);**当前无生产调用点**(惰性纯机制面),动作锚接线随执行器并入批次、boundary 触发口待裁决,禁实现时静默选型。
- **锚行封装**:anchor_id/trigger_type/时点键/payload/scope(口径域:global|plane|unit,防跨批口径混用)/evidence_refs(判定事实型必填)/produced_by。载体三面全部复用既有设施:事件行 = ExogenousEvent kind 枚举扩展(schema 修订归一个批次,防逐锚散改)、状态锚 = GameState 既有写入 API(source 标注 `anchor:<id>`)、计数 = 效果账本既有挂点。
- **防双源声明**:锚是上报接口面的登记清单面,非平行触发机制;与采集钩子(临时采样)适用范围互补禁混同;与停机钩子无交(锚永不触碰 run 状态);帧观察 → 锚 → 遥测落盘是一条管道的三段,锚不产生独立数据域。节点推进权威 = **终结动作上报(`report_node_advance`)+ 观察锚定(`observe_node_anchor`)**(判定语义单一源 = [../game_state/node-derivation.md](../game_state/node-derivation.md) §3.3),非统一 state 派生规则;锚行禁携带第二份节点序计数。
