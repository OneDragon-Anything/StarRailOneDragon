# 外层循环（outer_loop）

> 反向规格化来源 = `operations/cw_loop.py`（CwLoop）。职责：对局内唯一循环——每轮截图后按优先级匹配画面分支，把控制权交给对应画面 op（经 dispatch 包装统一落遥测）；驱动轮次推进（备战→出战→战斗→结算→回备战）；承载停机与遥测钩子。路径根 = `src/sr_od/application/currency_war/`。
> 数字三形态：本篇数字多为流程预算/阈值（框架常量，非策略判据），不进决策门，按"常量名 = 代码单一源"纪律书写；涉策略语义的数字标三形态。

## 1. 循环骨架

```
loop()（@operation_node，node_max_retry_times=400；cw_loop.py::CwLoop.loop）
  ├─ _iter += 1；> MAX_ITER=2000（≈66min 预算）→ round_fail('对局循环超时')（cw_loop.py::CwLoop.MAX_ITER）
  ├─ iter1：分发锚可解析预检（§2.2）
  ├─ 停滞 watchdog tick（guards.md §2）
  ├─ 每 10 iter：窗口焦点防线（失焦 → 主动激活；cw_loop.py::CwLoop.loop r15 焦点防线段）
  ├─ iter1 ∧ 新局：read_game_state(phase='battle_or_transit') 最小读
  │   └─ round>1 ∨ plane>1 → 恢复对局标记（遥测 record_exogenous；cw_loop.py::CwLoop.loop iter1 新局段）
  │   （新局策略状态冷建已前移 establish_new_match 进对局时点;生命周期钩子
  │    on_match_start 已随 ADR-0583 收编删除,冷建唯一口 = create_session）
  ├─ 分支序匹配（§2）→ 命中即执行并 round_wait 返回
  └─ 全不命中 → _handle_unknown_fallback()（guards.md §4）
```

run 级初始化 = `handle_init`（每次 execute() 开头框架回调；`cw_loop.py::CwLoop.handle_init`）：plane/round 缓存清零、`_is_new_match = ctx.cw_match is None`（续跑支持：cw_match 已存在则延用，手动逐轮验证靠此跨 run 延续 match）、职级难度 ctx 中转吸收（取走清空防跨局复用）、SettlementState/CwScreenBattleWait 实例化、新局兜底 `establish_new_match`。

## 2. 画面识别与路由（分支序 = 优先级，序位纪律）

### 2.1 判定原语

- 画面锚 = `画面名.area名`（screen_info 建档；`round_by_find_area(..., crop_first=False)`）。全部分支判定锚登记在 `DISPATCH_AREA_ANCHORS`（`cw_loop.py::CwLoop.DISPATCH_AREA_ANCHORS`），iter1 预检可解析性——缺失逐条 log.error，把"配置缺失"在第一轮炸到日志面（dd-029，防 merged 漏再生的静默跳过）。
- 兜底 OCR 判定（`round_by_ocr`）必须带收紧的 `lcs_percent` 并优先改 area 化——历史误匹配事故（投资策略屏被未达上限分支吞等）均源于全屏 LCS 共享子序列。

### 2.2 分支序（浮层先于备战双锚；序位漏项 = 实机事故源，锁测试钉死）

> **处理列自 T-121（ADR-0584）起全部为画面 op 调用**——外循环只管识别分派，推进处理（含弹窗关闭）一律在 op 内；每次分发经统一包装 `_dispatch_screen_op` 落 op_journal 行（telemetry/op_journal.py，op 调用流）与决策帧留证。分发判定/排他/序位/守卫域归属不变（§2.1 判定原语、guards.md；守卫钩子经 on_result 调用点邻接闭包留在分支体）。标「新·推进」= 空决策形态 op（`screen_op.md` §8.3），标「经包装」= 既有 op 本次接包装。

| 序 | 分支 | 判定 | 处理 |
|---|---|---|---|
| 0a0 | 选择装备 overlay | 双 id_mark 门（标题+副题） | CwScreenEquipPick（经包装）；**必须先于 0a**（副题同为"请选择1个"） |
| 0a | 选择伙伴 | id_mark | CwScreenPartner（经包装） |
| 0a2 | 银狼策划事件 | id_mark | CwScreenPlanner（经包装,失败 round_retry） |
| 0a3 | 命运卜者强化 | 双 id_mark | CwScreenFortune（经包装） |
| 0a4 | 位面详情 | 标题锚 | **CwScreenPlaneDetail（新·推进）**:点关闭+验消失迁入 op;关不掉经包装映射 round_retry |
| 0b | 巨星强化（盛会之星） | 独有标题 | CwScreenMegastar（经包装） |
| 0c | 遭遇节点 | id_mark | CwScreenEncounter（经包装） |
| 0d | 未达上限警告 | id_mark | CwScreenDeployNotFull（经包装） |
| 0e | 投资策略三选一 | **双信号+复探**(N5 分发判别稳定化):id_mark ∨ OCR 全短语「请选择投资策略」(lcs 0.8);miss 且备战双锚命中(穿透形态)→ 短窗复探一次 | CwScreenInvestStrategy（经包装;双信号+复探判定留外循环）。OCR 全短语腿为「优先 area 化」（§2.1）的**显式豁免**：浮层淡入期 id_mark 单探测不稳定（第十五局 15:14 空挥 37s 实证），复探窗口 = 执行层时序常量；常规帧（双锚未命中）零 OCR 零复探 |
| 0e1 | 补给阶段 | id_mark | CwScreenSupplyNode（经包装;成功 → `_record_supply_outcome` 合成 outcome 行留外循环回调:补给是唯一无结算屏节点,source='synthetic_supply'） |
| 0f | 武装箱弹窗 | id_mark | CwScreenArmoryBox（经包装） |
| 0e2 | 商店刷新概率表弹窗 | id_mark | **CwScreenRefreshOddsPopup（新·推进）**;× 已 area 化(按钮-关闭概率表,中心=原 (1501,263)),mouse_move bug#1 缓解在 op 内 |
| 0e3 | 道具详情弹窗（聘用书类） | OCR'聘用书' ∧ 非祈愿屏 | **CwScreenItemDetailPopup（新·推进）**;祈愿排他留外循环;× 已 area 化(中心=原 (1862,65)) |
| 0f' | 消耗品详情浮层 | OCR'消耗品'∧'拖动到' 双条件 | **CwScreenConsumableOverlay（新·推进）**;ESC 关 |
| 0g | 阿哈装备选择 | 备战屏'标识-简易装备' | **CwScreenAhaEquipPick（新·推进,固定策略=点第 1 件,申报）**;首件已 area 化(中心=原 (626,250)) |
| 0h | 祈愿试炼 | id_mark | CwScreenWishTrial（经包装;点卡选中→确认→验关） |
| 0i | 星徽秘典四选一 | id_mark（命中即接管，不放行备战分支） | CwScreenBookcard（经包装） |
| 0k | 专家邀请函 | id_mark（同上） | CwScreenExpertInvite（经包装） |
| 0t | 商店卡牌详情弹窗（T-163 实机事故建档:奖励节点点球误触开的角色 offer 购买页） | 双 id_mark 门:'按钮-购买' ∧ '按钮-角色详情'（弹窗前景独有锚,双锚全中才接管;判据单一源 `_shop_card_detail_anchor_hit`） | **CwScreenShopCardDetailPopup（新·推进,T-163）**:点 X(按钮-关闭,cw_lobby_close 同族模板)→ 验 X 消失 → 交回重判（店开 → 0n 商店访问接管购买;备战 → 备战环）;**绝不点购买**（买不买归商店域,关闭动作不代替购买决策）;on_fail_retry 消费 retry 池。序位 0 系——弹窗暗色衬底遮蔽底层全部锚（T-163 实证:开商店三锚/备战双锚 OCR 全灭）,不先分流 = 事故形态 |
| 0m | 备战暗色锁定子态族 | 右上"返回XX选择"按钮锚 | **CwScreenPrepLockedReturn（新·推进）**;两画面档参数化(策略锁定/遭遇锁定,分发处传命中的那对) |
| 0n | 备战-开商店(商店浮层态) | 开商店画面档三 id_mark(购买经验+按钮-收起+标识-备战阶段;与干净备战的按钮-出战天然互斥,idmark 审计批定稿) | 转交商店访问路径(ADR-0562):CwScreenPrep.visit_open_shop **经包装(元组适配形),op='商店访问' 行补齐 = S11 对齐**——入口观察→策略器逐动作决策→CloseShop 终结收店;路由层禁硬编码收起。分键 branch_shop_open_hit + visit_ok/_fail |
| 0j | 前台无角色提示 | id_mark | 直管恢复链保留(边界申报:发射核/战斗窗口状态耦合,op 化挂后续批);**经包装链形补 op='前台无角色恢复' 行**;确认 → 带落点验证重部署 → 验前排≥1 → 本迭代内再出战;重试上限 FRONTLESS_REDEPLOY_LIMIT=2 |
| 0p | BOSS 简报 | area 锚 ∨ 共享判别 `is_boss_briefing_texts`（误读鲁棒） | CwScreenBossBriefing（经包装补行）;**先于备战双锚**（横幅遮挡下双锚仍透出命中）;streak 复位留外循环回调 |
| 0q | 位面过渡 | OCR'点击空白处继续' ∧ 非 boss 帧（两画面排他） | CwScreenPlaneTransition（经包装）;误分发型 fail streak/超限 round_fail 留外循环回调（PLANE_MISDISPATCH_LIMIT=3） |
| 0r | 位面简报 | id_mark | CwScreenBriefing（经包装补行） |
| 0s | 投资环境（开场/接管局） | id_mark | CwScreenInvestEnv → CwScreenWaitOneOne（经包装补行×2;链序=等备战锚就绪,用户裁定特殊等待） |
| **1** | **备战** | **双锚**：'备战标识-购买经验' ∧ '按钮-出战' 同帧命中 | CwScreenPrep（**经包装**,journal='备战'）;进入序/达标臂/守卫域见 §3(臂族/守卫留外循环) |
| 1b/1d/1g | 详情弹窗族 | **1b 锚化（T-163）**:archive 双锚其一 '按钮-装备推荐' ∨ '装备详情-合成公式'（判据单一源 `_role_detail_anchor_hit`;原全屏 OCR'可合成列表'∨'角色详情'退役——「角色详情」与 0t 弹窗底部按钮全等共享 LCS 1.0,收紧无济于事 = 事故判据根,§2.1 存量欠账清偿）/ 星徽双锚 / 中断挑战锚 | **CwScreenRoleDetailOverlay / CwScreenEmblemDetailPopup / CwScreenInterruptDialog（新·推进）**;1b 点空白经 find_and_click(success_wait=1.5)+验「装备推荐」消失,on_fail_retry 消费 retry 池;1d「不用 ESC」理由随迁 op;1g 外生 popup 行随迁、「绝不点放弃并结算」红线随迁 |
| 战斗窗 | `_battle_wait_active`（出战驻留闩）∨ 帧锚 `_frame_in_battle_window` | CwScreenBattleWait（经包装;三段式：等结算→结算处理→白名单完成,团灭终局分叉交回 3c;settle 注入/窗口关/闩清留外循环回调=守卫域） |
| 3c | 回大厅（'标识-创业指南'） | area | 直管收口保留（遥测红线:runs summary/分配器/存档写端不迁移）;**经包装链形补 op='回大厅收口' 行**（§5） |
| 5 | 前进按钮 | OCR'下一步' | **CwScreenNextButton（新·推进）** |
| 兜底 | 全不命中 | — | `_handle_unknown_fallback`（guards.md §4;不经包装） |

overlay 分支必须在备战(1)前检测：overlay 叠备战时"购买经验"会透出命中，先查备战会误派（多处实机事故，见各分支注释）。

## 3. 备战分支（分支 1）的进入序（cw_loop.py::CwLoop.loop 备战分支段）

双锚命中后按序：

1. `_battle_ts = None`（战斗窗口关，watch 恢复）；
2. **环级无进展守卫**计数（guards.md §1；`cw_loop.py::CwLoop.loop` 备战分支 G3 计数段）；
3. "返回投资策略选择"按钮在 → 点去选策略（上游策略屏处理失败 symptom，计数报警）；
4. **策略失活早停**检查（查上一轮心跳；guards.md §5）；
5. **恢复局（locked-resume）检测**：候选 = 新 match ∧ 首个备战相位 round>1；商店探针（点商店→验收起）区分锁定/未锁；锁定态跳过全部备战交互直接出战，出战成功即解除（`cw_loop.py::locked_resume_sync_and_battle`）；
6. 可控轮数：`max_rounds` 已跑满 → round_success 停备战屏（单/多轮验证）；
7. 补给节点分流：nodeseq current=supply → 点"返回补给阶段"进补给屏（用节点类型判，非按钮——battle 节点也有该按钮）；
8. 预清场：试用角色揭示卡（≤3 轮，免费 2★，非策略决策不进 director）+ 书册卡（≤2 轮，CwScreenExpertInvite 全链）；
9. **达标即出战臂**（ADR-0557 判据核 + ADR-0570 armed 质量合取 + ADR-0566 发射帧仲裁）：armed 判定通过（kernel `readiness_launch_decision` 单一源；判据 = 配方完备 fp≥1.0 ∧〔板面承重满额 ∨ 部署计划不可得 fail-open〕——质量维 = B_t 通道承重结构零自由参数式，ADR-0570；推迟帧 `quality.defer_by_quality` 观测位显影，推迟上界 = 换血翻真 ∨ 计划耗尽 ∨ 金尽收益耗尽臂）→ 浮层在场闸（锚表扫描 + 遭遇 OCR 兜底；命中 ⇒ 本轮交浮层接管面）→ **发射帧受限消费仲裁**（ADR-0566：`_prep_anchors_hit` 预检通过才执行；溢出段 g>g* 开一次受限商店访问——open_shop → `run_buy_waves(spend_gate=预算闸)` → close_shop，闸拒因 = 花后金位跌破息线 g*；带内段 fail-closed 不开店；访问失败路径 abort 保画面交停机接管；该访问落第三载体 op 行 op='发射帧仲裁商店访问',ADR-0584 §5.1）→ 发射核 `readiness_battle_launch`（内部屏态复验 = 纵深防线；仲裁切屏后复验未过 ⇒ stale 弃射落守卫链，弃射帧带 `launch_arbitrage_abandoned_launch` defect 分键）。发射成功复位失败计数并 round_wait；
10. `CwScreenPrep(self.ctx).execute()`——**备战单轮**（prep_visit.md；达标臂发射失败连续 3 次放弃短路回落本链，防线 C1）；
11. 失败 streak ≥5 → round_fail 交兜底链；成功 → `_battle_ts` 置位 + `_battle_wait_active=True`；
12. **环让位重入契约**：director 返回（含 overlay bail）后必经 return → 下轮 loop 顶全分支重判，不在同一迭代内直接回备战分支（`cw_loop.py::CwLoop.loop` 备战分支尾环让位段）。

## 4. 轮次推进

轮 = 一次"备战环 → 出战 → 战斗 → 结算"。推进信号：
- 出战成功：`_battle_ts = monotonic()`（战斗窗口宽限计时起点，BATTLE_WATCH_GRACE_S=600 覆盖实测 4-5.5min 战斗）+ `_battle_wait_active=True`；
- 结算：CwScreenBattleWait 完成判据白名单（备战双锚单锚宽判定命中即 success 交回）；`saw_settlement` → `_battle_ts=None`；
- 轮计数 `_settle.rounds_done`（SettlementState，结算链收编；max_rounds 停点消费）；
- 节点真值：备战观察段的节点探针写 session（current 左移推断优先 + upcoming 存下轮；`cw_screen_prep.py::CwScreenPrep._probe_node_type`）。

## 5. 停机与遥测钩子

| 钩子 | 内容 | 载体 |
|---|---|---|
| runs summary 收口 | `after_operation_done` 全路径必达；未写 summary 的对局补写 stopped/abandoned（真假局判定 = "从未观察到对局态"才算假局） | `cw_loop.py::CwLoop.after_operation_done` |
| op 调用流 | **全分支 dispatch 包装统一落**（T-121/ADR-0584）：`_dispatch_screen_op` 每次分发写 op_journal enter/exit 成对行（0n='商店访问'/1='备战'/3c='回大厅收口'…）+ 决策帧留证（frame_tag）；异常路径补发 outcome='error' 的 exit 行后上抛（孤儿 enter 回归进程中断专属，ADR-0584 §5.2）；仲裁触发商店访问为包装外唯一补行点（op='发射帧仲裁商店访问'，三载体口径 = ADR-0584 §5.1） | `telemetry/op_journal.jsonl` + `decision_frames/` |
| 局终正常收口（3c） | 假局守卫 + 假 win 守卫（plane==3 精确 ∧ 非死局）+ record_run_summary（final_hp 走 `_last_true_hp` 防 100 兜底毒化）+ 对局存档装配 + match 清空（生命周期钩子 on_match_end 已随 ADR-0583 删除,原实现 no-op 零行为） | `cw_loop.py::对局循环分支 3c（局终正常收口）` |
| 跨局分配器 | ThompsonAllocator 进程级单例，plaza 份额先验；终局 update（臂 = comp→plaza_carry 归一；影子期只记后验） | `cw_loop.py::ThompsonAllocator 单例与终局 update` |
| 补给合成 outcome | 见 §2.2 分支 0e1 | `cw_loop.py::补给节点完成合成 outcome 段（分支 0e1，见 §2.2）` |
| 关键点快照 `_snap` | 选人/事件屏 debug 截图 + 全量 OCR 日志（验证后去掉；非关键路径 best-effort） | `cw_loop.py::CwLoop._snap` |

## 6. ⚠️ 现状违宪待改标记（本篇辖内）

- ⚠️ **恢复局判定无位面字面问题**——本篇辖内无位面字面门。boss 简报/位面过渡两画面排他（0p/0q）为画面识别纪律，非机制辖域。
- ⚠️ **MAX_ITER=2000 计入战斗 round_wait**（`cw_loop.py::CwLoop.MAX_ITER` 类常量待优化注）：迭代预算被战斗时长消耗是已知待办（"MAX_ITER 应只计动作迭代"），非判据违例，登记为流程债。
