# 外层循环（outer_loop）

> 反向规格化来源 = `operations/cw_loop.py`（CwLoop）。职责：对局内唯一循环——每轮截图后按**两阶段身份分发**把控制权交给对应画面处理器（经 dispatch 包装统一落遥测）；驱动轮次推进（备战→出战→战斗→结算→回备战）；承载停机与遥测钩子。路径根 = `src/sr_od/application/currency_war/`。
> 数字三形态：本篇数字多为流程预算/阈值（框架常量，非策略判据），不进决策门，按"常量名 = 代码单一源"纪律书写；涉策略语义的数字标三形态。

## 1. 循环骨架

```
loop()（@operation_node，node_max_retry_times=400；cw_loop.py::CwLoop.loop）
  ├─ _iter += 1(运行生命周期边界归哨兵 NODE-DWELL/沉默 watchdog,guards.md §2)
  ├─ iter1：分发画面预检（§2.1）
  ├─ 停滞 watchdog tick（guards.md §2）
  ├─ 每 10 iter：窗口焦点防线（失焦 → 主动激活；cw_loop.py::CwLoop.loop 窗口焦点防线段）
  ├─ iter1 ∧ 新局：read_game_state(phase='battle_or_transit') 最小读
  │   └─ round>1 ∨ plane>1 → 恢复对局标记（遥测 record_exogenous；cw_loop.py::CwLoop.loop iter1 新局段）
  │   （新局策略状态冷建已前移 establish_new_match 进对局时点;生命周期钩子
  │    on_match_start 已随单动作循环迁移收编删除,冷建唯一口 = create_session）
  ├─ 阶段一 画面身份分发（§2.2）→ 命中即派发并交回
  ├─ 阶段三 特殊规则（无独立画面档/身份不可表达,§2.2）
  ├─ 阶段二 备战表面默认分支（双锚 + 横幅守卫;进入序见 §3）
  ├─ 战斗窗（闩 ∨ 帧锚）→ CwScreenBattleWait
  ├─ 「下一步」→ CwScreenNextButton
  └─ 全不命中 → _handle_unknown_fallback()（guards.md §2）
```

run 级初始化 = `handle_init`（每次 execute() 开头框架回调；`cw_loop.py::CwLoop.handle_init`）：plane/round 缓存清零、`_is_new_match = ctx.cw_match is None`（续跑支持：cw_match 已存在则延用，手动逐轮验证靠此跨 run 延续 match）、职级难度 ctx 中转吸收（取走清空防跨局复用）、SettlementState/CwScreenBattleWait 实例化、新局兜底 `establish_new_match`。

### 1.1 循环上限规范（用户裁定，2026-09-19）

**框架不负责多轮循环的上限限制。** 外循环的轮次推进与画面 op 的决策循环均**不设迭代数上限**——健康循环永不因迭代计数被截断；死循环/不收敛 = **策略实现 bug**，修复在策略侧，框架不兜底（不收敛表现为挂起，可观测）。

- 轮次推进以 `round_wait` 形态继续（`loop()` 各分支，迭代不烧 `node_max_retry_times` 预算；该预算仅失败路径 round_retry 消费）；
- **失败类出口不属于迭代上限**：连续 fail 重派网（`OP_FAIL_REDISPATCH_LIMIT`，guards.md §2）、未知画面兜底、异常传播 = 对「错误条件」的响应，与迭代计数无关；
- 兜底不变量：每个决策画面的动作空间至少含一个恒可用终结动作（op-layer.md §1.4）——正确策略必收敛，收敛性由策略侧保证。

## 2. 画面识别与分发（两阶段身份分发；判据单一源 = 各画面建档 id_mark 组合）

### 2.1 判定原语与预检

- 画面锚 = `画面名.area名`（screen_info 建档；`round_by_find_area(..., crop_first=False)`）。iter1 预检分发清单 `CW_DISPATCH_SCREENS`：任一画面档缺失或无 id_mark → log.error 逐条点名，把"配置缺失"在第一轮炸到日志面（防 merged 漏再生的静默跳过）。
- **文本锚矩形必须覆盖整条 OCR 行**：识别结果过滤按「OCR 行矩形与锚矩形重叠 ≥70%」筛选,窄矩形会滤掉整行结果 → 锚恒 miss(列车同行副题锚实例)。要短文本判别就选短且独立的行。
- 兜底 OCR 判定（`round_by_ocr`）必须带收紧的 `lcs_percent` 并优先改 area 化——历史误匹配事故（投资策略屏被未达上限分支吞等）均源于全屏 LCS 共享子序列。

### 2.2 两阶段分发

> **所有分发经统一包装 `_dispatch_screen_op` 落主日志 `[cw-op]` 行**与决策帧留证。身份命中臂 = `_dispatch_identity_screen` 精确键派发（键互斥,无顺序语义）;新增画面 = 建档（语料两向验证）+ 处理器臂 + `CW_DISPATCH_SCREENS` 登记,三处缺一不可。

```
阶段一 身份分发：name = get_match_screen_name(ctx, frame, CW_DISPATCH_SCREENS)
        （判据 = 各画面建档 id_mark 组合;清单 = 过滤器非优先级,遍历序 = loader 序,
          各画面身份经语料两向验证互不共命中后顺序不承重）
        命中 → _dispatch_identity_screen(name, frame) 派发对应画面处理器
        （位面过渡臂含 boss 判别排他:帧含'强敌'片段 → 接管派发 BOSS简报,
          防 boss 帧位面锚可读时误派过渡 op）
阶段三 特殊规则（无独立画面档/身份不可表达;互相锚互斥,顺序不承重）：
        道具详情弹窗（OCR'聘用书' ∧ 非祈愿屏,祈愿排除为纵深）
        消耗品浮层（OCR'消耗品'∧'拖动到'）
        阿哈装备选择（备战档'标识-简易装备',固定策略=点第 1 件,申报）
阶段二 备战表面默认分支（双锚：'备战标识-购买经验' ∧ '按钮-出战';横幅中间态守卫：
        OCR'请选择投资策略' lcs 0.8 在场 → round_wait 等展开,#30 裁定）
        → CwScreenPrep 备战单轮（进入序/守卫域见 §3；发射决策宿主 = 策略层前置发射位）
战斗窗（闩 _battle_wait_active ∨ 帧锚 _frame_in_battle_window）→ CwScreenBattleWait
3c 大厅（身份行'标识-创业指南'）→ 对局收口（§5;遥测红线写端保留本 loop）
5   下一步（OCR）→ CwScreenNextButton
兜底 全不命中 → _handle_unknown_fallback（guards.md §2）
```

- **清单排除项与理由**：备战（部署态/补给 revisit 按钮/攻略位移使右上角与棋盘标签锚不可靠,语料 18/57 误杀 → 双锚默认分支）、补给锁定（其「返回补给阶段」按钮在普通战斗节点 revisit 备战同样出现,#18 接线暂缓裁定的延续）、道具详情弹窗（道具名可变无固定身份）/消耗品浮层/阿哈装备（无独立画面档,阶段三特殊规则）。
- **语料纪律（分发身份准入）**：每画面身份须两向验证——本画面全部已存档实机帧 True + 堆叠底图/兄弟画面帧 False;备战扩展锚语料误杀事故即缺此验证所致(验证脚手架 = 测试仓 screens/ + is_target_screen 离线批跑)。
- **序位不承重的依据**：原「浮层先于备战」序位补偿的是「锚命中≠前台」;现由各浮层自身精确身份承载。补给锁定族以自身「返回XX选择」文字锚进阶段一;旧选择装备 overlay 与列车同行的锚碰撞由列车同行整行副题锚消解;投资策略横幅中间态 = 身份天然 miss + 阶段二守卫等待(#30)。
- **行为边界变化申报**：角色详情弹窗/星徽详情弹窗/中断挑战弹窗由「备战分支后置」改为阶段一身份先行（专属处理器带验效关闭,与备战环入口清场双通道收敛）;位面过渡节点锚误读帧从 OCR 派发改为兜底等待（下一轮 OCR 命中即恢复,不再即时派发）。

### 2.3 分支号索引（0x 记法定义）

**记法定义**：0x 分支号 = `cw_loop.py` 主循环画面分发 if 分支的注释顺序编号（历史演化物）。现行分发已改两阶段（§2.2）：阶段一按画面建档名派发（无号，映射 = `_dispatch_identity_screen` 的 `if name == '货币战争-XX'` 链），0x 号只保留在阶段三特殊规则与备战/收口等段。**权威源 = cw_loop.py 分发段注释块**，本表与代码注释冲突时以代码为准。

现行号：

| 号 | 辖域 | 判定/处理器 |
|---|---|---|
| 0e3 | 道具详情弹窗（聘用书类） | OCR'聘用书' ∧ 非祈愿屏；点 × 关 |
| 0f' | 消耗品详情浮层 | OCR'消耗品' ∧ '拖动到'；关浮层 |
| 0g | 阿哈大悦装备选择 overlay | 备战档'标识-简易装备'；固定策略点第 1 件 |
| 0n | 商店访问（备战分支内子分支） | 开商店态三 id_mark 锚；[cw-op] 行 op='商店访问' |
| 1 | 备战阶段默认分支 | 双锚；CwScreenPrep |
| 3c | 回大厅收口（局终正常收口） | 身份行'标识-创业指南' |
| 5 | 下一步 | OCR；CwScreenNextButton |

> **兜底增设判据（用户裁定）**：未建档保存的故障形态不作兜底理由——不为无法追溯的形态预建兜底，身份 miss 的真实帧走未知兜底（guards.md §2）留证，证据入库后再议加固。位面过渡的 boss 帧排他仍保留在阶段一位面过渡身份臂（boss 判别片段，判别单一源）。

已退役号（读旧档案/旧文档时按此对号）：0a（选择伙伴，现役载体 = 阶段一身份行「货币战争-列车同行」分发 CwScreenPartner）/ 0a2（选择装备重试腿，随选择装备屏退役删除）/ 0a3（命运卜者强化，现役载体 = 专家邀请函屏内命运卜者强化卡，CwScreenExpertInvite）/ 0a4（位面详情弹窗，现役载体 = 阶段一身份行「货币战争-位面详情」分发 CwScreenPlaneDetail）/ 0b（巨星，现役载体 = 阶段一身份行「货币战争-盛会之星」分发 CwScreenMegastar）/ 0c（遭遇节点，现役载体 = 阶段一身份行「货币战争-遭遇节点」分发 CwScreenEncounter）/ 0d（未达上限警告，现役载体 = 阶段一身份行「货币战争-未达上限警告」分发 CwScreenDeployNotFull）/ 0e（投资策略浮层系，现役载体 = 阶段一身份行「货币战争-投资策略」分发 CwScreenInvestStrategy）/ 0e1（补给阶段（0e 系子号），现役载体 = 阶段一身份行「货币战争-补给」分发 CwScreenSupplyNode）/ 0e2（商店刷新概率表弹窗，现役载体 = 阶段一身份行「货币战争-商店刷新概率表」分发 CwScreenRefreshOddsPopup）/ 0f（武装箱弹窗分支（旧，与消耗品旧 ESC 臂共用裸号），现役载体 = 阶段一身份行「货币战争-武装箱弹窗」分发 CwScreenArmoryBox）/ 0f2（备战武装箱选择画面，现役载体 = 阶段一身份行「货币战争-备战-武装箱选择」）/ 0h（祈愿试炼，现役载体 = 阶段一身份行「货币战争-祈愿试炼」分发 CwScreenWishTrial）/ 0i（星徽秘典弹窗，现役载体 = 阶段一身份行「货币战争-星徽秘典弹窗」分发 CwScreenBookcard）/ 0j（恢复链）/ 0k（专家邀请函弹窗，现役载体 = 阶段一身份行「货币战争-备战-专家邀请函」分发 CwScreenExpertInvite）/ 0m（补给锁定族）/ 0p（BOSS 简报误读兜底，2026-09-16 随徽记模板锚换装+兜底裁定退役）/ 0q（位面过渡误读兜底，同批退役，见上退役记录）/ 0r（位面简报，现役载体 = 阶段一身份行「货币战争-简报」）/ 0s（投资环境）/ 0t（商店卡牌详情弹窗，现役载体 = 阶段一身份行「货币战争-商店卡牌详情」分发 CwScreenShopCardDetailPopup）/ 0a0（选择装备 overlay——2026-09-22 用户裁定该屏为古老时期误判、游戏内不存在，画面 op/建档/词表/策略口全套退役删除）/ 1b、1d、1g（详情弹窗族，现役载体 = 阶段一身份先行）/ 1f、2、3、3b、6（战斗结算系，现役载体 = 战斗窗 + 结算三段式）。旧尾句所指「screens/README §5 等处文档残留旧号」已随退役号清偿批清偿：screens/README §5 现仅 0n 在役、零退役号残留；各号现役载体如上，读旧档案按此对号。

## 3. 备战表面默认分支的进入序（cw_loop.py::CwLoop.loop 备战分支段）

双锚命中后按序（本分支无前置挂点——战斗时间戳清理与心跳采样/效果账本 tick 分别退役与迁出：前者无消费者，后者归 kernel 推进生效原语尾段，节点推进 = 终结动作上报 + 画面 op 锚定，外循环不写节点域）：

**发射决策不在本分支**：达标帧发射决策宿主 = mandate_v1 前置发射位（`decide_prep_screen` 入口消费 kernel `readiness_launch_decision`；armed 帧产受限商店访问意图或 `StartBattle` 终点意图，随第 5 步派发的备战访问 op 落执行；判据与语义 = [../strategy-docs/14_p1_consume_arms.md](../strategy-docs/14_p1_consume_arms.md) §9.6/§11.10）。

1. "返回投资策略选择"按钮在 → 点去选策略（上游策略屏处理失败 symptom，计数报警）；
2. **恢复局（locked-resume）检测**：候选 = 新 match ∧ 首个备战相位 round>1；商店探针（点商店→验收起）区分锁定/未锁；锁定态跳过全部备战交互经统一执行器（face=resume，含屏态复验与浮层安全检查——防误触补齐）直接出战并置战斗窗，出战成功即解除（`cw_loop.py::locked_resume_sync_and_battle`）；
3. 可控轮数：`max_rounds` 已跑满 → round_success 停备战屏（单/多轮验证）；
4. 补给节点分流：nodeseq current=supply → 点"返回补给阶段"进补给屏（用节点类型判，非按钮——battle 节点也有该按钮）；
5. 派发 `CwScreenPrep` 备战单轮（两 node:观察 node(heavy 观察+接管补采+审计留守)+ 决策动作 node（单动作决策循环）, [../screens/prep.md](../screens/prep.md)；环入口清场收编于观察段）。**交回契约置战斗窗**：出战意图由 op 内统一执行器 `launch_battle_unified`（face=armed）落执行，op 以终结出口 success 交回承载「本访问结束」；外循环 `_on_prep_round` 回调见 success 交回即置 `_battle_ts` + `_battle_wait_active`（非出战出口的 success 交回误置位由 CwScreenBattleWait 宽限等待 + 备战白名单锚兜底分流）；
6. **环让位重入契约**：director 返回（含 overlay bail）后必经 return → 下轮 loop 顶全分支重判，不在同一迭代内直接回备战分支（`cw_loop.py::CwLoop.loop` 备战分支尾环让位段）。

## 4. 轮次推进

轮 = 一次"备战环 → 出战 → 战斗 → 结算"。推进信号：
- 出战成功：`_battle_ts = monotonic()`（战斗窗口宽限计时起点，BATTLE_WATCH_GRACE_S=600 覆盖实测 4-5.5min 战斗）+ `_battle_wait_active=True`；
- 结算：CwScreenBattleWait 完成判据白名单（备战双锚单锚宽判定命中即 success 交回）；`saw_settlement` → `_battle_ts=None`；
- **节点推进（外循环零写点）**：序号前进唯一动作入口 = kernel `report_node_advance`——战斗节点终结 = `CwOpSettleConfirm` 转移证据（完成判据白名单命中）后上报 settle_confirm；补给节点终结 = `CwActionPickSupplyOp` 确认（until = 下一节点备战锚）后上报 supply_confirm。观察锚定 = 画面 op 观察 node（`CwScreenPrep` 备战顶栏 / `CwScreenSupplyNode` 补给屏节点条 → kernel `observe_node_anchor`）。历史开局链分支写点已整体退役，外循环与观察漏斗均不写推进域（判定语义单一源 = [../game_state/node-derivation.md](../game_state/node-derivation.md)）；
- 轮计数 `_settle.rounds_done`（SettlementState，结算链收编；max_rounds 停点消费）；
- 节点真值：节点行观察归备战观察域——备战入口 heavy 观察消费位（`cw_screen_prep.py::_write_prep_node_chain`，识别复用 `observe_full` 现役 `read_node_sequence` 调用）写槽序表/台账（[../screens/prep.md](../screens/prep.md) §3）。

## 5. 停机与遥测钩子

| 钩子 | 内容 | 载体 |
|---|---|---|
| run 收口 | `after_operation_done` 全路径必达;`close_run` 零落盘,置跨局 run_id 重铸位;局终元数据归宿 = GameState 局终域 match_final 行 | `cw_loop.py::CwLoop.after_operation_done` |
| op 调用流 | **全分支 dispatch 包装统一落**：`_dispatch_screen_op` 每次分发在出口落一行主日志 `[cw-op]` 行（`op=<名> plane=<位面> round=<轮次> dur=<秒>s outcome=<ok|fail|error>`，0n='商店访问'/1='备战'/3c='回大厅收口'…；只落出口行，dur = 单调钟差）+ 决策帧留证（frame_tag）；异常路径补落 outcome='error' 的行后上抛；op_journal 流已随 2026-09-15 用户裁定退役，存量档案双键切片只读 | server 主日志（`.log/mcp_server.log` / `.debug/sr_od_mcp/main_server.log`）+ `decision_frames/` |
| 局终正常收口（3c） | 假局守卫 + 假 win 守卫（plane==3 精确 ∧ 非死局）+ 局终域 match_final 行 + `close_run` + 对局存档装配 + match 清空 | `cw_loop.py::对局循环分支 3c（局终正常收口）` |
| 跨局分配器 | ThompsonAllocator 进程级单例，plaza 份额先验；终局 update（臂 = comp→plaza_carry 归一；影子期只记后验） | `cw_loop.py::ThompsonAllocator 单例与终局 update` |
| 关键点快照 `_snap` | 选人/事件屏 debug 截图 + 全量 OCR 日志（验证后去掉；非关键路径 best-effort） | `cw_loop.py::CwLoop._snap` |
