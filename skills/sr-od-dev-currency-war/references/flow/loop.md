# 外层循环(loop)

> 组件 = `operations/cw_loop.py`(CwLoop)。
> **职责边界**:loop 只做三件事——识别当前画面、派发给对应画面 op、循环运行管理(预检/看门狗/轮次推进信号/局终收尾)。**画面处理逻辑(识别后的交互/试探/行为序列)一律归画面 op——loop 分支里出现点击即违例**;违例族消解申报:出战执行链 6 函数已迁 `prep_actions.py`(与执行器同居,统一执行器 = `prep_actions.py::launch_battle_unified`)、前台无角色弹窗内联分支已改为独立画面 op `CwScreenNoFrontHint` 经阶段一身份分发派发、备战分支交互链已迁 `CwScreenPrep` 特殊流程段(观察 node 段1 子态识别四查 + 决策动作 node 段3 三处置,迭代 2026-11-18-prep-special-flow);残余违例(道具详情弹窗阶段三判定归属)登记在待跟进事项文件「loop 瘦身」条,随下批重构消解。
> 路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。守卫细则见 [guards.md](guards.md);画面 op 形态见 [screen-op.md](screen-op.md)。

四层分工:**外层循环只判断当前画面并派发给对应画面 op;画面 op 负责一次访问内的观察→决策→执行编排;策略器决定当前帧发出什么动作;动作 op 负责单个动作的机械执行(机械发出、不做效果验证;落地判定归观察侧对账)**。

节点推进喂入 = **动作上报 + 画面 op id_mark 确认**:战斗/补给节点终结动作 op 上报(kernel `report_node_advance`,trigger 封闭集 {settle_confirm, supply_finish})+ 画面 op 观察 id_mark 确认(`CwScreenPrep` 备战顶栏 / `CwScreenSupplyNode` 节点条 → kernel `observe_node_anchor`);观察上报链与外循环分支的写入点均不写推进字段(判定语义单一源 = kernel 三个推进函数的注释,cw_game_state.py)。

## 1. 循环结构

```
loop()(@operation_node,预算 = node_max_retry_times,值见代码;cw_loop.py::CwLoop.loop)
  ├─ _iter += 1(运行生命周期边界归哨兵 NODE-DWELL/沉默 watchdog)
  ├─ iter1:分发画面预检(§2)
  ├─ 停滞 watchdog tick(guards.md)
  ├─ 每 10 iter:窗口焦点防线(失焦 → 主动激活)
  ├─ iter1 ∧ 接管局(opened_via=='takeover'):read_game_state(phase='battle_or_transit') 最小读
  │   └─ round>1 ∨ plane>1 → 恢复对局标记 + 接管观察态失效(遥测 record_exogenous)
  ├─ 阶段一 画面身份分发(§2)→ 命中即派发并返回主循环
  ├─ 阶段三 特殊规则(无独立画面档/身份不可表达,§2)
  ├─ 阶段二 备战表面默认分支(双识别标志同帧命中 + 横幅守卫;进入序见 §3)
  ├─ 战斗窗(战斗窗标志位 ∨ 帧级识别标志)→ CwScreenBattleWait
  ├─ 「下一步」→ CwScreenNextButton
  └─ 全不命中 → _handle_unknown_fallback()(guards.md)
```

run 级初始化 = `handle_init`(每次 execute() 开头框架回调):plane/round 缓存清零、**每次运行重建判据**(宿主 = `strategies/impl/cw_strategy.py::CurrencyWarMatch`;判据 = 容器记 `created_run_id` 比对当前 run——容器存在 ∧ 非 None ∧ ≠ 当前 run → 先 `discard_stale_match_container` 再 `establish_new_match('takeover')` 弃旧重建;`None` = 外部装配〔sim 直构〕短路保留;出处 = 2026-11-19-resume-rebuild design §2.4)、开局方式事实 `opened_via`(容器建立时一次写入、运行内不变:`'new_game'` = 入口链新局确凿信号处写入 / `'takeover'` = loop 兜底建、跨 run 重建、商店防御兜底;消费点 = SettlementState 新局标记注入 / 战斗帧恢复检测 / 备战探测检查——**接管局必经一次商店可开性探测**(接管局 = 从对局中途恢复的对局):`opened_via=='takeover'` 且尚未探测过时执行,位面 1 第 1 节点的接管局同样探测)、锁定两字段 per-run 重置(`locked_resume/locked_round`;`locked_sync_done` 不重置〔配对不变量〕)、职级难度 ctx 中转吸收(取走清空防跨局复用)、SettlementState/CwScreenBattleWait 实例化、兜底建容器(`ctx.cw_match is None` 时 `establish_new_match('takeover')`,覆盖绕过入口链直跑 loop 的场景)。手动逐轮验证(max_rounds=1 反复 run_operation)每轮触发重建 → 策略 target 每轮重选 + 商店可开性探测每轮一次(已接受的工作流变更)。

## 2. 画面识别与分发(两阶段身份分发)

> 所有分发经统一包装 `_dispatch_screen_op` 落主日志 `[cw-op]` 行与决策帧保留证据。身份命中分支 = `_dispatch_identity_screen` 精确键派发(键互斥,无顺序语义);**新增画面 = 建档(语料两向验证)+ 处理器分支 + `CW_DISPATCH_SCREENS` 登记,三处缺一不可**。

**判定原语与预检**:

- 画面 id_mark 识别区 = `画面名.area名`(screen_info 建档;`round_by_find_area(..., crop_first=False)`)。iter1 预检分发清单 `CW_DISPATCH_SCREENS`:任一画面档缺失或无 id_mark → log.error 逐条点名(防 merged 漏再生的静默跳过)。
- **文本识别区矩形必须覆盖整条 OCR 行**:识别结果过滤按「OCR 行矩形与识别区矩形重叠 ≥70%」筛选,窄矩形会滤掉整行结果 → id_mark 恒 miss。要短文本判别就选短且独立的行。
- 兜底 OCR 判定(`round_by_ocr`)必须带收紧的 `lcs_percent` 并优先改 area 化——全屏 LCS 共享子序列是历史误匹配事故的根源。

**两阶段分发**:

```
阶段一 身份分发(两段式判定,实机专属;sim 的画面身份由模拟后端状态机直接回答,不截图识别):
    第一段(登记预测优先,实机且 game state 登记 pending 非空时):
    按登记序逐屏 is_target_screen(ctx, frame, screen_name=predicted) 试,
    命中即取该名——登记条目长度通常 ≤2(弹窗动作落地即弹的确定性预测);
    候选过滤 = 仅 screen_name ∈ CW_DISPATCH_SCREENS 的条目(阿哈装备〔aha,
    星神★阿哈装备选择〕类条目的画面档名就是备战画面,没有独立分发画面,
    不参与两段式判定——实机走阶段三特殊规则 + 兜底清空收尾)。
    机制依据 = get_match_screen_name 按 loader 序遍历、传入清单只作过滤集不承序
    ——提速必须两段式,重排清单无效。
    第二段(全扫描,反应式兜底不变):
    name = get_match_screen_name(ctx, frame, CW_DISPATCH_SCREENS)
    (判据 = 各画面建档 id_mark 组合;清单 = 过滤器非优先级,遍历序 = loader 序,
      各画面身份经语料两向验证互不共命中后顺序不起决定作用)
    识别对账行:登记预测非空且实扫结果 ∉ 预测屏名集 → journal arbitrate
    保留证据(判据假阳/延迟呈现漂移警报,best-effort 不阻塞分发)。
    命中 → _dispatch_identity_screen(name, frame) 派发对应画面处理器
    (位面过渡分支含 boss 判别排他:帧含'强敌'片段 → 接管派发 BOSS简报)
阶段三 特殊规则(无独立画面档/身份不可表达;互相识别标志互斥,顺序不起决定作用):
    道具详情弹窗(OCR'聘用书' ∧ 非祈愿屏,祈愿排除为纵深)
    消耗品浮层(OCR'消耗品'∧'拖动到')
    阿哈装备选择(备战档'标识-简易装备',固定策略=点第 1 件,申报)
阶段二 备战表面默认分支(双识别标志:'备战标识-购买经验' ∧ ('按钮-出战' ∨
    '按钮-跳过';第二识别标志免战子态双形态——「按钮-跳过」为定位识别标志非
    id_mark,免战帧身份归免战独立档;横幅中间态守卫:OCR'请选择投资策略'
    lcs 0.8 在场 → round_wait 等展开)
    双识别标志同帧命中 → game state 登记兜底清空(本轮分发未接住任何 pending 条目
     → 整列清;识别到弹窗屏不清——多弹窗条目逐个存活;sim 不走本清,呈现即
     消费由后端收尾)
    → CwScreenPrep 备战单轮(进入序见 §3)
战斗窗(战斗窗标志 _battle_wait_active ∨ 帧级识别 _frame_in_battle_window)
    → CwScreenBattleWait
大厅收尾分支(id_mark 行'标识-创业指南')→ 对局收尾(§7)
下一步(OCR)→ CwScreenNextButton
兜底 全不命中 → _handle_unknown_fallback(guards.md)
```

- **弹窗两屏经阶段一身份分发(出战点击后的弹窗帧接盘)**:出战单击原子发出后渲染的两类真弹窗均已登记 `CW_DISPATCH_SCREENS`——「货币战争-未达上限警告」→ `CwScreenDeployNotFull`(勾「本局不再提示」+ 确认)、「货币战争-提示-前台无角色」→ `CwScreenNoFrontHint`(确认,零恢复动作);弹窗在场时备战两识别标志同帧仍可见,但身份分发先于备战分支命中——弹窗帧由独立弹窗 op 接住,备战分支不受遮蔽影响。
- **链形 dispatch 分支(投资环境链)**:经统一包装两次 dispatch(环境 op → 等待 1-1),链级计数与出口透传契约见 [guards.md](guards.md) §1;链形透传分支(3c)不经连续失败重派上限的既有申报不变。
- **清单排除项与理由**:备战(部署态/补给 revisit 按钮/攻略位移使右上角羁绊面板 id_mark 区不可靠 → 双识别标志默认分支)、补给锁定(其「返回补给阶段」按钮在普通战斗节点 revisit 备战同样出现)、道具详情弹窗(道具名可变无固定身份)/消耗品浮层/阿哈装备(无独立画面档,阶段三特殊规则)。
- **语料纪律(分发身份准入)**:每画面身份须两向验证——本画面全部已存档实机帧 True + 堆叠底图/兄弟画面帧 False(验证脚手架 = 测试仓 screens/ + is_target_screen 离线批跑)。
- **兜底增设判据**:未建档保存的故障形态不作兜底理由——不为无法追溯的形态预建兜底,身份 miss 的真实帧走未知兜底保留证据,证据入库后再议加固。

## 3. 备战表面默认分支的进入序

> 本分支已坍缩为纯识别派发:备战交互三段链(返回投资策略点击/接管局探测+锁定直出战/补给分流)已迁 `CwScreenPrep` 特殊流程段(观察 node 段1 子态识别四查 + 决策动作 node 段3 三处置,迭代 2026-11-18-prep-special-flow;画面 op 侧形态细则见 screen-op.md「备战(CwScreenPrep)特殊」行),以下为 as-built。

**动作发出决策不在本分支**:达标帧的发出决策宿主 = mandate_v1 决策链最先检查的发出点(`decide_prep_screen` 入口消费 kernel `readiness_launch_decision`;出战就绪帧产受限商店访问意图或 `StartBattle` 终点意图,随派发的备战访问 op 落执行;判据与语义 = ../strategy/14_p1_consume_arms.md §9.6/§11.10)。

1. **横幅中间态守卫**:OCR「请选择投资策略」lcs 0.8 在场 → round_wait 等展开(选卡页展开中零可交互元素,不处理);
2. 双识别标志识别(`prep_anchors_hit`)同帧命中 → 兜底清 `_fallback_clear_pending`(本轮分发未接住任何 pending 条目 → 整列清;识别到弹窗屏不清——多弹窗条目逐个存活;sim 不走本清);
3. **max_rounds 停点**:已跑满 → 停止点分两种模式(判据 = `env_config.is_debug`,读取点单点 = 停点段):debug 模式 → round_success 停在备战画面(保留对局现场供采样检查);非 debug 模式 → 以 `STATUS_HANDOFF_PREFIX` 前缀文本交出,app 交接节点走 exit 清场退局回大厅(弃局),重开由下一次 app 运行承载。**停点先于派发,子态帧不再处置**——候选挂起、锁定不确认、返回按钮不点,直接停在画面;停点语义 =「停在备战画面、不跑备战单轮」,子态处置属备战交互(已归画面 op)。停点重跑场景的旧「探测失活」形态已由每次运行重建判据消解(重建容器 `opened_via='takeover'`,接管局的商店可开性探测照跑);
4. 派发 `CwScreenPrep` 备战单轮(`on_result` 回调不变)。子态帧在 op 内走特殊流程:观察 node 段1 四查(0 锁定确认态〔含段3b retry 耗尽后主循环重派发的重入帧,直达出战段〕/ a 返回按钮 / b 接管局探测 / c 补给分流)+ 决策动作 node 段3 三处置(点返回 / `prep_actions.py::locked_resume_sync_and_battle` 同步步骤+出战 / 点「返回补给阶段」),细则见 screen-op.md「备战(CwScreenPrep)特殊」行。**交回契约与失败链**:子态处置均以 round_success 交回(wait 2/3/2);锁定出战未执行 → op 内 retry 保锁(框架预算每访问 1 首跑+3 重试=4 次),耗尽 → 访问 fail → 外循环连续失败计数限 5 次重派发,至多约 20 次出战尝试,≪ 旧形态 loop 节点原地重试预算 400 次。**战斗窗置位统一由外循环 `_on_prep_round` 回调承载**:对一切 success 交回统一置 `_battle_ts` + `_battle_wait_active`(含返回按钮/补给出口的非出战交回——误置位由 CwScreenBattleWait 宽限等待 + 备战 id_mark 白名单兜底分流);出战意图由统一执行器 `prep_actions.py::launch_battle_unified` 落执行;
5. **环让位重入契约**:备战分支处理完(含弹窗让路)必须以 return 结束本轮,下一轮从循环顶重新识别画面,不在同一轮里直接再进备战分支。

## 4. 轮次推进

轮 = 一次"备战环 → 出战 → 战斗 → 结算"。推进信号:

- 出战成功:`_battle_ts = monotonic()`(战斗窗口宽限计时起点,宽限常量 `BATTLE_WATCH_GRACE_S` 覆盖战斗全程)+ `_battle_wait_active=True`;
- 结算:CwScreenBattleWait 完成判据白名单(备战取单识别标志'备战标识-购买经验'宽判定——免战帧亦恒在;双识别标志精判归循环备战分支职责);`saw_settlement` → `_battle_ts=None`;
- **节点推进(外循环零写点)**:序号前进唯一动作入口 = kernel `report_node_advance`——战斗节点终结 = `CwOpSettleConfirm` 转移证据后上报 settle_confirm;补给节点终结 = 出战动作上报 supply_finish(宿主参数 = `CwActionStartBattleParam`;补给选卡确认不推进)。观察 id_mark 确认 = 画面 op 观察 node(`CwScreenPrep` 备战顶栏 / `CwScreenSupplyNode` 补给屏节点条 → kernel `observe_node_anchor`)。外循环与观察上报链均不写推进字段;
- 轮计数 `_settle.rounds_done`(SettlementState;max_rounds 停点消费);
- 节点真值来自备战画面的观察:备战入口全量观察的调用点(`cw_screen_prep.py::_write_prep_node_chain`)读节点行,写入槽序表与位面节点记录字段。

## 5. 循环上限规范

**框架不负责多轮循环的上限限制。** 外循环的轮次推进与画面 op 的决策循环均**不设迭代数上限**——健康循环永不因迭代计数被截断;死循环/不收敛 = **策略实现 bug**,修复在策略侧,框架不兜底(不收敛表现为挂起,可观测)。

- 轮次推进以 `round_wait` 形态继续(迭代不消耗 `node_max_retry_times` 预算;该预算仅失败路径 round_retry 消费);
- **失败类出口不属于迭代上限**:连续 fail 重派上限(`OP_FAIL_REDISPATCH_LIMIT`,guards.md)、未知画面兜底、异常传播 = 对「错误条件」的响应,与迭代计数无关;出口总表见 §6;
- 兜底不变量:每个决策画面的动作空间至少含一个恒可用终结动作(终结 = 结束本次访问;见 `docs/develop/sr_od/application/currency_war/screens/op-layer.md` §1.4)——正确策略必收敛,收敛性由策略侧保证。

## 6. 结束出口表(loop 全部终态出口与 app 交接判定)

> loop op(`cw_loop.py::CwLoop`)的终态出口与 app 编排层的交接判定对应关系。**交接** = loop 结束时把「该退出但还没退」的状态移交 app 退出收尾节点(`currency_war_app.py::CurrencyWarApp._exit_cleanup`)处置,由其调用 `CwEntryExit` 完成退局;loop 的交接出口 = 正常完成、节点出错过多、非 debug 停点弃局三者,都以 `round_success` 出口交接(后两者同走 `STATUS_HANDOFF_PREFIX` 交接前缀)。出口文本常量 = `cw_loop.py` 模块级 `STATUS_LOBBY_DONE`/`STATUS_HANDOFF_PREFIX`(loop 出口与 app 判定共用单一源,禁裸串散写);防线出口的判定契约见 guards.md §1。

**success 出口**:

| 出口 | 文本 | 产出点 | app 交接节点行为 |
|---|---|---|---|
| **交接点①正常完成** | `STATUS_LOBBY_DONE`(「对局结束,回大厅」) | `_lobby_return_collect` 大厅收尾分支(收尾记录写入完成后) | 弹窗守卫 → exit 大厅确认形态 → 置 `ctx.cw_match=None` |
| **交接点②异常超限** | `STATUS_HANDOFF_PREFIX`+计数键(「异常退出交接:<键>」) | `_dispatch_screen_op` 防线段耗尽(默认构造;投资环境链链首按双条件透传同款出口) | 弹窗守卫 → exit 清场退局形态 → 置 `ctx.cw_match=None` |
| max_rounds 停点(debug) | 「已跑 N 轮停备战(达 max_rounds=M)」 | 备战分支停点(先于派发) | 跳过 exit 直接结束(**非退出触发**:验证模式留局采样) |
| max_rounds 停点(非 debug) | `STATUS_HANDOFF_PREFIX`+「停点重开:max_rounds=M」 | 备战分支停点(先于派发) | 弹窗守卫 → exit 清场退局形态(弃局回大厅) → 置 `ctx.cw_match=None`;重开由下一次 app 运行承载 |
| 开局失败/中断(假局守卫) | 「开局失败/中断(未产生对局数据,不记 summary)」 | `_lobby_return_collect` 假局守卫 | 跳过 exit 直接结束(**非退出触发**:已在大厅,对局状态已清) |
| route⑤ 停机位 | 「已到可交还退出调度的备战态(含免战)」 | `loop()` 停机位判定(仅 `stop_at_prep=True` 构造可达) | app 主路径不可达;exit 委托清理的交还点(见 entry-exit.md §3) |

**fail 出口**:

| 出口 | 文本 | 产出点 | app 行为 |
|---|---|---|---|
| 防线耗尽(委托清理模式) | 「<名> 连续 fail 超上限(交上层处置)」 | `_dispatch_screen_op` 防线段耗尽且构造参数 `cleanup_delegate=True` | route⑤ 委托清理实例专用:exit 节点重试承接,其预算耗尽 → exit fail → app 失败收尾(残局可见非静默) |
| 未知画面兜底耗尽 | 「连续 N 帧未识别画面,重试耗尽待建档」 | `_handle_unknown_fallback`(连续 `UNKNOWN_FAIL_THRESHOLD` 轮) | app 失败收尾——画面全盲时 exit 同为识别驱动、无从处置,交接无意义 |
| 框架级失败(非显式出口) | —(框架收敛) | loop 节点重试预算耗尽 / 未捕获异常上抛 / 框架超时;战斗窗宽限提前退出经防线出口收敛至上两行;系统哨兵为最终兜底 | app 失败收尾;残局由下次启动预检恢复链兜底 |

**非退出触发边界**:debug 停点与假局守卫出口虽为 success,但不是退出触发——前者是验证模式的留局采样语义(is_debug=True),后者现场已在大厅且无对局可退;两者落 app 交接节点三形态判定的「其余」分支,跳过退出。非 debug 停点不在本边界内:其出口以 `STATUS_HANDOFF_PREFIX` 前缀交出,落「异常交接」形态走 exit 清场退局回大厅(弃局),重开由下一次 app 运行承载。三形态判定是互补结构,出口文本漂移只会把错形态漏进行为安全的「其余」分支;可升级为结构化 data 载体(`round_success(status, data=…)` 框架既有支持),当前按文本判定的形态保留。

**委托清理模式耗尽维持 fail 的语义**:exit 委托的清理 loop 是新实例,失败计数从零重算;若其耗尽出口翻成交接 success,exit 会误判「清理完成」→ 残局遗留且账面成功(静默失败)。故构造参数 `cleanup_delegate=True` 时耗尽维持 round_fail,由 exit 节点重试承接(防线出口契约 = 双出口,见 guards.md §1 与 `_dispatch_screen_op` docstring)。

**已知噪音与构造点边界申报**:

- sim 直驱构造点耗尽出口翻转:sim 现役直驱 `CwLoop` 的构造点(skill 脚本 `scripts/cw_sim_match_drive.py`、测试 harness sim_backend_runner.py)为默认参构造(交接 success 出口)——sim 决策链确定性驱动、耗尽不可达(前提);若未来触达,拿到的是无消费方解析的交接文本,无害。
- 幻影 run 噪音:route⑤ 委托清理 loop 在运行记录已关闭态会重铸新运行 id(幻影 run),清理段日志归属碎片化;正常完成+弹窗压大厅路径还会触发对局状态重建又立刻被假局守卫拆除,伴随误导性警告「开局阶段即回大厅」(委托态下该警告不表达真实开局失败)。已知噪音申报,治理登记在待跟进事项文件「委托清理 loop 不参与运行记录生命周期」条。

## 7. 停机与遥测钩子

| 钩子 | 内容 | 载体 |
|---|---|---|
| run 收尾 | `after_operation_done` 全路径必达;`close_run` 零落盘,置跨局 run_id 重铸位;局终元数据归宿 = GameState 局终域 match_final 行 | `cw_loop.py::CwLoop.after_operation_done` |
| op 调用流 | 全分支 dispatch 包装统一落:`_dispatch_screen_op` 每次分发在出口落一行主日志 `[cw-op]` 行(`op=<名> plane=<位面> round=<轮次> dur=<秒>s outcome=<ok|fail|error>`;只落出口行,dur = 单调钟差)+ 决策帧保留证据(frame_tag);异常路径补落 outcome='error' 的行后上抛 | server 主日志(`.log/mcp_server.log` / `.log/stdout.log`)+ `decision_frames/` |
| 局终正常收尾(大厅收尾分支) | 假局守卫 + 假 win 守卫(plane==3 精确 ∧ 非死局)+ 局终域 match_final 行 + `close_run` + 对局存档装配 + match 清空 | `cw_loop.py::CwLoop.loop` 大厅收尾分支 |
| 跨局分配器 | ThompsonAllocator 进程级单例,plaza 份额先验;终局 update(更新分支 = comp→统计簇名归一〔`LINE_STAT_CLUSTER` 查表〕;影子期只记后验) | `cw_loop.py::ThompsonAllocator` 单例与终局 update |
