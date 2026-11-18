# 外层循环(loop)

> 组件 = `operations/cw_loop.py`(CwLoop)。
> **职责边界**:loop 只做三件事——识别当前画面、派发给对应画面 op、循环运行管理(预检/看门狗/轮次推进信号/局终收尾)。**画面处理逻辑(识别后的交互/试探/行为序列)一律归画面 op——loop 分支里出现点击即违例**;违例族消解申报:出战执行链 6 函数已迁 `prep_actions.py`(与执行器同居,统一执行器 = `prep_actions.py::launch_battle_unified`)、前台无角色弹窗内联分支已改为独立画面 op `CwScreenNoFrontHint` 经阶段一身份分发派发;残余违例(道具详情弹窗阶段三判定归属/备战分支交互链)登记在跨迭代挂账板「loop 瘦身」条,随下批重构消解。
> 路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。守卫细则见 [guards.md](guards.md);画面 op 形态见 [screen-op.md](screen-op.md)。

四层分工判据:**外层循环管「现在是哪个画面、交给谁」;画面指挥管「一次访问内观察→决策→执行的编排」;策略步进管「给一帧期望态提什么动作」;动作执行管「一个动作怎么落地」(机械发出、零判效;落地判定归观察侧对账)**。

节点推进喂入 = **动作上报 + 画面 op id_mark 确认**:战斗/补给节点终结动作 op 上报(kernel `report_node_advance`,trigger 封闭集 {settle_confirm, supply_finish})+ 画面 op 观察 id_mark 确认(`CwScreenPrep` 备战顶栏 / `CwScreenSupplyNode` 节点条 → kernel `observe_node_anchor`);观察漏斗与外循环分支写点不写推进域(判定语义单一源 = `docs/develop/sr_od/application/currency_war/game_state/node-derivation.md`)。

## 1. 循环骨架

```
loop()(@operation_node,预算 = node_max_retry_times,值见代码;cw_loop.py::CwLoop.loop)
  ├─ _iter += 1(运行生命周期边界归哨兵 NODE-DWELL/沉默 watchdog)
  ├─ iter1:分发画面预检(§2)
  ├─ 停滞 watchdog tick(guards.md)
  ├─ 每 10 iter:窗口焦点防线(失焦 → 主动激活)
  ├─ iter1 ∧ 新局:read_game_state(phase='battle_or_transit') 最小读
  │   └─ round>1 ∨ plane>1 → 恢复对局标记(遥测 record_exogenous)
  ├─ 阶段一 画面身份分发(§2)→ 命中即派发并返回主循环
  ├─ 阶段三 特殊规则(无独立画面档/身份不可表达,§2)
  ├─ 阶段二 备战表面默认分支(双识别标志同帧命中 + 横幅守卫;进入序见 §3)
  ├─ 战斗窗(战斗窗标志位 ∨ 帧级识别标志)→ CwScreenBattleWait
  ├─ 「下一步」→ CwScreenNextButton
  └─ 全不命中 → _handle_unknown_fallback()(guards.md)
```

run 级初始化 = `handle_init`(每次 execute() 开头框架回调):plane/round 缓存清零、`_is_new_match = ctx.cw_match is None`(续跑支持:cw_match 已存在则延用,手动逐轮验证靠此跨 run 延续 match)、职级难度 ctx 中转吸收(取走清空防跨局复用)、SettlementState/CwScreenBattleWait 实例化、新局兜底 `establish_new_match`。

## 2. 画面识别与分发(两阶段身份分发)

> 所有分发经统一包装 `_dispatch_screen_op` 落主日志 `[cw-op]` 行与决策帧保留证据。身份命中分支 = `_dispatch_identity_screen` 精确键派发(键互斥,无顺序语义);**新增画面 = 建档(语料两向验证)+ 处理器分支 + `CW_DISPATCH_SCREENS` 登记,三处缺一不可**。

**判定原语与预检**:

- 画面 id_mark 识别区 = `画面名.area名`(screen_info 建档;`round_by_find_area(..., crop_first=False)`)。iter1 预检分发清单 `CW_DISPATCH_SCREENS`:任一画面档缺失或无 id_mark → log.error 逐条点名(防 merged 漏再生的静默跳过)。
- **文本识别区矩形必须覆盖整条 OCR 行**:识别结果过滤按「OCR 行矩形与识别区矩形重叠 ≥70%」筛选,窄矩形会滤掉整行结果 → id_mark 恒 miss。要短文本判别就选短且独立的行。
- 兜底 OCR 判定(`round_by_ocr`)必须带收紧的 `lcs_percent` 并优先改 area 化——全屏 LCS 共享子序列是历史误匹配事故的根源。

**两阶段分发**:

```
阶段一 身份分发(两段式判定,实机专属;sim 身份 = 后端状态机答口):
    第一段(登记预测优先,实机且状态容器登记 pending 非空时):
    按登记序逐屏 is_target_screen(ctx, frame, screen_name=predicted) 试,
    命中即取该名——登记条目长度通常 ≤2(弹窗动作落地即弹的确定性预测);
    候选过滤 = 仅 screen_name ∈ CW_DISPATCH_SCREENS 的条目(aha 类条目的屏档名
    = 备战底屏,无独立分发屏,不参与两段式——实机走阶段三反应式 + 兜底清收尾)。
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
    双识别标志同帧命中 → 状态容器登记兜底清空(本轮分发未接住任何 pending 条目
     → 整列清;识别到弹窗屏不清——多弹窗条目逐个存活;sim 不走本清,呈现即
     消费由后端收尾)
    → CwScreenPrep 备战单轮(进入序见 §3)
战斗窗(战斗窗标志 _battle_wait_active ∨ 帧级识别 _frame_in_battle_window)
    → CwScreenBattleWait
大厅收尾分支(id_mark 行'标识-创业指南')→ 对局收尾(§6)
下一步(OCR)→ CwScreenNextButton
兜底 全不命中 → _handle_unknown_fallback(guards.md)
```

- **弹窗两屏经阶段一身份分发(出战点击后的弹窗帧接盘)**:出战单击原子发出后渲染的两类真弹窗均已登记 `CW_DISPATCH_SCREENS`——「货币战争-未达上限警告」→ `CwScreenDeployNotFull`(勾「本局不再提示」+ 确认)、「货币战争-提示-前台无角色」→ `CwScreenNoFrontHint`(确认,零恢复动作);弹窗在场时备战两识别标志同帧仍可见,但身份分发先于备战分支命中——弹窗帧由独立弹窗 op 接住,备战分支不受遮蔽影响。
- **清单排除项与理由**:备战(部署态/补给 revisit 按钮/攻略位移使右上角与棋盘标签 id_mark 不可靠 → 双识别标志默认分支)、补给锁定(其「返回补给阶段」按钮在普通战斗节点 revisit 备战同样出现)、道具详情弹窗(道具名可变无固定身份)/消耗品浮层/阿哈装备(无独立画面档,阶段三特殊规则)。
- **语料纪律(分发身份准入)**:每画面身份须两向验证——本画面全部已存档实机帧 True + 堆叠底图/兄弟画面帧 False(验证脚手架 = 测试仓 screens/ + is_target_screen 离线批跑)。
- **兜底增设判据**:未建档保存的故障形态不作兜底理由——不为无法追溯的形态预建兜底,身份 miss 的真实帧走未知兜底保留证据,证据入库后再议加固。

## 3. 备战表面默认分支的进入序

> 本分支现状含前置交互链(锁定探针/分流点击)与内联关闭,属「loop 瘦身」挂账的违例面,重构后本节改写;以下为 as-built 记录。

双识别标志同帧命中后按序(本分支无前置插入位置):

**动作发出决策不在本分支**:达标帧的发出决策宿主 = mandate_v1 决策链最先检查的发出点(`decide_prep_screen` 入口消费 kernel `readiness_launch_decision`;出战就绪帧产受限商店访问意图或 `StartBattle` 终点意图,随第 5 步派发的备战访问 op 落执行;判据与语义 = strategy-docs/14_p1_consume_arms.md §9.6/§11.10)。

1. "返回投资策略选择"按钮在 → 点去选策略(上游策略屏处理失败 symptom,计数报警);
2. **恢复局(locked-resume)检测**:候选 = 新 match ∧ 首个备战相位 round>1;点一下商店按钮试探:能打开 = 未锁定,打不开 = 锁定恢复态;锁定态跳过全部备战交互,经统一执行器(恢复模式,含屏态复验与浮层安全检查)直接出战并置战斗窗,出战成功即解除(`prep_actions.py::locked_resume_sync_and_battle`);
3. 可控轮数:`max_rounds` 已跑满 → round_success 停备战屏;
4. 补给节点分流:nodeseq current=supply → 点"返回补给阶段"进补给屏(用节点类型判,非按钮——battle 节点也有该按钮);
5. 派发 `CwScreenPrep` 备战单轮。**访问结束契约置战斗窗**:出战意图由统一执行器 `prep_actions.py::launch_battle_unified` 落执行,op 以终结出口 success 结束本次访问;外循环 `_on_prep_round` 回调见 success 返回即置 `_battle_ts` + `_battle_wait_active`(非出战出口的 success 返回误置位由 CwScreenBattleWait 宽限等待 + 备战 id_mark 白名单兜底分流);
6. **环让位重入契约**:备战分支处理完(含弹窗让路)必须以 return 结束本轮,下一轮从循环顶重新识别画面,不在同一轮里直接再进备战分支。

## 4. 轮次推进

轮 = 一次"备战环 → 出战 → 战斗 → 结算"。推进信号:

- 出战成功:`_battle_ts = monotonic()`(战斗窗口宽限计时起点,宽限常量 `BATTLE_WATCH_GRACE_S` 覆盖战斗全程)+ `_battle_wait_active=True`;
- 结算:CwScreenBattleWait 完成判据白名单(备战取单识别标志'备战标识-购买经验'宽判定——免战帧亦恒在;双识别标志精判归循环备战分支职责);`saw_settlement` → `_battle_ts=None`;
- **节点推进(外循环零写点)**:序号前进唯一动作入口 = kernel `report_node_advance`——战斗节点终结 = `CwOpSettleConfirm` 转移证据后上报 settle_confirm;补给节点终结 = 出战动作上报 supply_finish(宿主参数 = `CwActionStartBattleParam`;补给选卡确认不推进)。观察 id_mark 确认 = 画面 op 观察 node(`CwScreenPrep` 备战顶栏 / `CwScreenSupplyNode` 补给屏节点条 → kernel `observe_node_anchor`)。外循环与观察漏斗均不写推进域;
- 轮计数 `_settle.rounds_done`(SettlementState;max_rounds 停点消费);
- 节点真值:节点行观察归备战观察域——备战入口 heavy 观察消费位(`cw_screen_prep.py::_write_prep_node_chain`)写槽序表/台账。

## 5. 循环上限规范

**框架不负责多轮循环的上限限制。** 外循环的轮次推进与画面 op 的决策循环均**不设迭代数上限**——健康循环永不因迭代计数被截断;死循环/不收敛 = **策略实现 bug**,修复在策略侧,框架不兜底(不收敛表现为挂起,可观测)。

- 轮次推进以 `round_wait` 形态继续(迭代不烧 `node_max_retry_times` 预算;该预算仅失败路径 round_retry 消费);
- **失败类出口不属于迭代上限**:连续 fail 重派网(`OP_FAIL_REDISPATCH_LIMIT`,guards.md)、未知画面兜底、异常传播 = 对「错误条件」的响应,与迭代计数无关;
- 兜底不变量:每个决策画面的动作空间至少含一个恒可用终结动作(终结 = 结束本次访问;见 `docs/develop/sr_od/application/currency_war/screens/op-layer.md` §1.4)——正确策略必收敛,收敛性由策略侧保证。

## 6. 停机与遥测钩子

| 钩子 | 内容 | 载体 |
|---|---|---|
| run 收尾 | `after_operation_done` 全路径必达;`close_run` 零落盘,置跨局 run_id 重铸位;局终元数据归宿 = GameState 局终域 match_final 行 | `cw_loop.py::CwLoop.after_operation_done` |
| op 调用流 | 全分支 dispatch 包装统一落:`_dispatch_screen_op` 每次分发在出口落一行主日志 `[cw-op]` 行(`op=<名> plane=<位面> round=<轮次> dur=<秒>s outcome=<ok|fail|error>`;只落出口行,dur = 单调钟差)+ 决策帧保留证据(frame_tag);异常路径补落 outcome='error' 的行后上抛 | server 主日志(`.log/mcp_server.log` / `.log/stdout.log`)+ `decision_frames/` |
| 局终正常收尾(大厅收尾分支) | 假局守卫 + 假 win 守卫(plane==3 精确 ∧ 非死局)+ 局终域 match_final 行 + `close_run` + 对局存档装配 + match 清空 | `cw_loop.py::CwLoop.loop` 大厅收尾分支 |
| 跨局分配器 | ThompsonAllocator 进程级单例,plaza 份额先验;终局 update(更新分支 = comp→统计簇名归一〔`LINE_STAT_CLUSTER` 查表〕;影子期只记后验) | `cw_loop.py::ThompsonAllocator` 单例与终局 update |
