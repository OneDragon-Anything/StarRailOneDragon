# 15 备战决策环(PrepDirector)—— 备战编排从固定序列到观察驱动(v7 三轮盲审修订,定稿)

> 总见 [README](README.md)。本文:备战画面内「下一步做什么」的决策架构 —— 观察驱动单步决策环,
> 替代 BattlePrepCycle 固定序列。2026-08-14 用户定调(触发:奖励球 + 备战席满,球拖一轮才收);
> **v2**:动作全集原子化(宏动作被否);**v3**:决策点全景(事件域 + 工具域);
> **v4**:显式**框架/策略分离**(用户定调:「这块应该只是框架,要和具体策略分离开来,可以有多种策略实现」
> —— 对齐 11 号插件机制,环是框架,规则是策略);**v5**:review agent 修订(带代码行号证据的 3 HIGH + 7 MED):
> 事件域「已接线✅」事实性错误(四屏实为停机隔离态)、工具域 12 件全量分类、命运圣杯任务系统补全、
> §5.1 空转环/gold 互斥/bail 规则等伪码漏洞;**v6(二轮 review)**:defer_count 环级清零语义(H-1)、
> 弹层 bail 三层优先级与计数生命周期(H-2)、控制流动作入全集 §4.2b(H-3)、P1 动作集补 LevelUp/
> EnsureShopOpen(H-4)、ADR 正文按现行版重写(M-1)+ 全部 M/L 修订;**v7(三轮盲审,零先验)**:P1 补 RunDeploy
> 组合(保 DeployBench 四项板上行为:D-10 换血/同角色去重/前排保证/cap 门 —— `_should_deploy`+`_pick_deploy_row`
> 不足以复现,全原子切换=静默回归)、ADR 残留清干净、§13 P1 接口规格附录(slot 物理槽位语义/execute 三失败
> 路径/恢复原语映射/屏蔽粒度/obs 恒空)、ping-pong 兜底修正(MAX_ITER 非 node_max_retry)、武装箱选卡归属、
> StartBattle 先 execute 后 break、第三方钩子兼容注、三采集钩子去向。**定稿,可开工 P1**。ADR-0123 记录决策。
>
> **P1 已落地(2026-08-14)**:框架 `prep_director.py`(环 + PrepObservation + F1-F8)+ 原子执行器
> `prep_actions.py` + ABC 钩子 `decide_prep_action`(cw_strategy)+ DefaultCwStrategy §5.1-5.3 具现 +
> 挂载切换(battle_loop 备战分支 → PrepDirector,BattlePrepCycle 退役为 P3 前回退路径)。决策单测 17 项
> (`sr-od-test/.../test_prep_director.py`)。**待 live 验证**(`run_operation` 稳定 M=3,§8)。

## 1. 问题(为什么改)

现状 BattlePrepCycle = **固定流水线** `(收球→买牌→部署→装备→出战)`,编排顺序硬编码,不看画面状态。README 核心哲学「观测驱动而非预测驱动」只落实到**回合级**(hp_trend/对账),备战内部是开环。具体症状:

| # | 症状 | 根因 |
|---|---|---|
| 1 | 奖励球 + 席满 → 收球 op 中断,腾席在买牌 op 里,时序脱节 → **球拖一整轮才收** | 腾席决策被硬编码在「买牌」节点内,收球触不到 |
| 2 | `_handle_bench_full` 无脑卖 bench-1..3(位置式)→ 可能卖掉核心角色 | 腾席无身份感知,而价值评估(`_weakest_bench_idx`)早已存在但只在 plan() 内 |
| 3 | 腾席候选不完整:不考虑「拖到前后台空位」「升级扩容」这类更优解 | 腾席不是一个决策点,是买牌 op 的副作用 |
| 4 | plan() 是批量快照,RefreshShop 后动作过期 → shop.py 需两阶段 hack | 批量计划 vs 状态会变 |
| 5 | **工具(扳手/冶金炉/投影仪)从不使用** —— EquipAll 只过滤跳过(category=工具),员工投影仪「造核心 1 星复制=直凑 3合1」这种高价值动作完全缺位 | 工具使用不在任何 op 的动作空间里 |
| 6 | 事件 overlay 决策(投资策略/巨星/伙伴/祈愿)散在主循环各分支 handler 内,与备战决策两套世界(obs 不共享、session 上下文重复传) | 事件处理与 prep 编排分层割裂 |

用户定调(2026-08-14):「策略应该是根据当前画面输出下一步做什么」—— 涵盖奖励收取、腾席、**投资策略选择、扳手使用、冶金炉使用、盛会之星选择**等全部决策点;做一步 → 再识别 → 再决定。

## 2. 两层环架构(是什么)

```
外环 CurrencyWarRunLoop(主循环,已有):屏幕级路由
    战斗 / 结算 / 位面过渡 / 备战(→ 内环) / 事件 overlay(P1-4 交分支 handler;P5 进内环) / 大厅
    ⚠️ 其中祈愿/补给/投资×2 四屏现处停机隔离态(battle_loop:216-227,§4.3),巨星/伙伴/遭遇才是活 handler(L-3)
    ▼ 备战态
内环 PrepDirector(新,替换 BattlePrepCycle):备战画面步级决策
  while True:
    obs = observe(ctx, screen)                        # ① 统一观察(轻/重分层;P5 含 overlay 态)
    action = strategy.decide_prep_action(obs,         # ② 决策:一个动作(原子为主)
                             session, config)
    progressed = execute(action)                     # ③ 执行器:动作 → 原语(带完成验证;StartBattle 亦经此,验证=备战标识消失,L-2)
    if isinstance(action, StartBattle) and progressed: break  #    环出口 = 出战(执行且验证成功后才退出;未过 → stall 走恢复链)
    if isinstance(action, BailToOuter): break        #    交外环(事件 overlay,P1-4 过渡期;框架信号不走验证)
    if not progressed: stall += 1                    # ④ 无进展防护(§7)
```

对照目标场景:`有球+bench 9/9+deployed 5/6` → DeployMove(上排腾席)→ 再观察 →
`有球+free=1` → ClickSpheres(上界1)→ 再观察 → … → StartBattle;
`owned 有员工投影仪 + bench 有 3费核心` → UseProjector(核心)→ 再观察(bench 多 1 张核心=3合1 进度)。

## 3. 统一观察(PrepObservation)

决策的单一输入。**组合现成 reader,不新写识别**:

| 字段 | 来源(现成) | 轻/重 |
|---|---|---|
| state: GameState(gold/hp/level/phase/board) | read_game_state(session tracking 合并)。**⚠️ gold 只在 shop 开态可读**(关态读空;开态也间歇读 0,shop.py:181-187 重读缓解)—— 需 gold 的决策先 EnsureShopOpen | 重(阶段边界) |
| bench_chars / deployed_chars(身份+星级,SIFT) | read_bench_chars / read_deployed_chars + session tracking 合并;**环入口对账一步**(read≠tracking 漂移是既有 bug 源,deploy_bench._reconcile_tracking / battle_prep._verify_recognition 钩子的继任宿主) | 重(环入口 + 结构变化) |
| spheres / boxes | read_reward_spheres / read_supply_boxes(⚠️ 已知未验边界:owned 装备溢出遮奖励区 → 可能漏/误,保守消费) | 轻(每步) |
| free_bench_slots: int | 9 − bench 占用(角色+箱都占席) | 轻 |
| deploy_vacancy: int | read_deploy_cap − read_deployed_count | 重(P1 实现:heavy 刷新 + light 沿用缓存;原「轻」标注已过期) |
| owned_equips(含 category=工具,12 件模板全在库) | read_equips(SIFT) | 重 |
| overlay_state / overlay_options(P5) | 各屏 id_mark 锚点 + handler 现成 _read_options。**⚠️ 现状:祈愿/补给/投资策略/投资环境四屏 yml 已建但 id_mark 模型待核(疑独立屏非 overlay,battle_loop:216-227 停机隔离中);巨星/伙伴/遭遇/武装箱 ✅ 建档可依** | 轻/重 |
| shop_cards / shop_open | read_shop_cards / 锚点 | 重(买牌阶段) |

**观察缓存失效**:事件动作(补给给装备/圣杯给改件/买牌)改变结构 → 强制失效重读(单线程无竞态,但须显式)。

**成本控制**:轻观察(CV 级)每步;重观察(SIFT/shop 全读/read_game_state)只在阶段边界或结构变化时。
**shop 开关互斥**(gold 只在开态、HP 只在关态)→ EnsureShopOpen/Closed 动作显式管理。

## 4. 动作全集(原子化 + 决策点全景,v3 核心)

### 4.1 奖励/商店/席位/装备/战斗域(v2 已盘,此处摘要)

| 域 | 原子动作 | 决策依据(现成) | 验证 |
|---|---|---|---|
| 奖励 | ClickSphere / **ClickSpheres(k=min(free,n),带内验早停)** / OpenBox / PickBoxCard | 大球优先;箱必开;k=free-slots 驱动 | 球数−1/overlay 态翻转/owned+ |
| 商店 | BuyCard / LevelUp(执行=购买经验按钮循环点至 level+1,单次点击不作为独立决策动作,L-2) / RefreshShop | plan() eval-delta / level_plan / 蒙特卡洛 | 金变/牌变/level+1 |
| 席位 | **SellBench(slot,身份感知)** / **SellDeployed(slot,换阵卸位)** / DeployMove(from,to) | _weakest_bench_idx(**现版无 3合1 件保护待加**,cw_decisions:412-435)/ off-target(D-10)/ _should_deploy+_pick_deploy_row | 源空+gold+ / 源空+目标占 |
| 装备 | WearEquip(equip,slot) / Synthesize(defer) | key_equips 优先(角色级分配 P4) | below-icon CV-diff |
| 战斗 | StartBattle(含未达上限确认) | 环出口全件(§7) | 备战标识消失 |
| 观察管理 | EnsureShopOpen/Closed / CloseOverlay(960,530 真空白) | 读取前置/异常恢复 | 锚点翻转 |

### 4.2 工具域(v3 新增,决策函数缺,P4)

工具 = owned 中 category=工具 的装备,**拖到目标上使用**(非穿戴)。机制(cw_equipment_data 权威):
**12 件工具全量分类**(cw_equipment_data 权威;v5 review 修订 —— v3 只盘 4 件漏主动类):

| 类 | 项(动作) | 机制 | 决策要点(策略层,函数待写) | Phase |
|---|---|---|---|---|
| **主动-复制** | **UseProjector**(员工投影仪) | 拖到 ≤3费角色 → 备战席造 1星复制。**前置:free>0(复制体占席,与腾席链交互)** | 复制 target 核心(≤3费)凑 3合1;无核心可复制→留 | P4 |
| 主动-复制 | **UsePerfectProjector**(完美投影仪) | 任意角色 → 1星复制(前置同上) | 同上不限费;**注意时效**:5F 令咒协议给的 8 个仅当节点有效 | P4 |
| 主动-转化 | **UseWrench**(拆装扳手/精密版) | 拖到角色 → 取下其所有装备(一次性/无限) | 卖角/换阵前回收装备(装值≥残值才值得) | P4 |
| 主动-转化 | **UseSmelter**(冶金炉) | 拖装备→同类随机;拖角色→卸装全变随机 | 垃圾装备赌重roll(期望值) | P4 |
| **主动-升级** | **UsePrivilegeCard**(特权赋予卡) | 拖到进阶装备 → 变对应特权装备(**免费升特权**) | key_equips/特权装备价值命中时用;**高价值** | P4 |
| **主动-选择** | **UseLuckyToken**(好运令牌) | 拖到角色 → 从 4 件推荐进阶装备**选 1**(含 4 选 1 子 overlay) | equip_fit 打分选;触发子决策面(同 PickBoxCard 模式) | P4 |
| 被动 | 财富宝钻(团队规模+1)/红钻/蓝钻(星徽合成材料) | 无使用动作 | 宝钻影响 deploy_cap(§3 已读);钻类归 **Synthesize** 材料 | — |
| **待核** | 垃圾袋/金垃圾袋(category=工具但给属性) | 疑似穿戴语义 | 穿戴 vs 使用待核(现被 EquipAll 一刀切过滤,P3 随 WearEquip 一并核) | P3 核 |


### 4.2b 控制流动作(v6 修 H-3:F3 自违反补齐)

| 动作 | 语义 | 执行契约 | F3 豁免说明 |
|---|---|---|---|
| **DeferSpheres** | 球留置,本环不再尝试(框架 no-op) | **不计 stall、计步数**(§7 预算仍约束);仅奖励域合法(球>0 时策略可出);框架对策略可见的幂等信号 —— 同环重复出由 defer_count 门挡 | 控制流信号非游戏动作,F3 域外豁免;策略不可用任意 no-op 刷步(其余动作须带验证,验证失败计 stall) |
| **BailToOuter** | 中止本环,交外环处理(弹层/事件) | 框架信号,环 break;**外环重入重建 Director 时 stall/屏蔽/defer 计数全清零**(v6 修 H-2c);外环侧重入次数受既有 node_max_retry_times 预算兜底(battle_loop.py:190) | 同上;P5 后事件收编进环,此动作仅剩真异常弹层用 |

**执行器返回契约**:游戏动作 → progressed: bool(验证过);控制流动作 → 框架处理,不走 execute 验证链。
### 4.3 事件域(overlay 选择,P5 收编进环;决策函数大多现成)

| 动作 | overlay 画面 | 决策依据 | 现状(v5 review 核实) | 进环 |
|---|---|---|---|---|
| PickInvestOption(kind, idx) | 投资策略/投资环境 | decide_invest(白名单+克制) | handler 代码在但 **🚫 停机隔离中**(battle_loop:216-227,疑独立屏非 overlay,待重建档) | P5(前置重建档) |
| PickMegastarOption(idx) | 盛会之星 | decide_megastar(core_chars 命中,✅) | run_megastar_node(✅) | P5 |
| PickPartnerOption(idx) | 选择伙伴 | decide_partner(build_around/core,🟡 输入受限需 SIFT) | handle_select_partner(✅) | P5 |
| PickEncounterOption(idx) | 遭遇其一/其四 | decide_encounter(✅ 非平凡) | HandleEncounter(✅) | P5 |
| PickSupplyOption(idx) | 补给选装备/出钻 | decide_supply | run_supply_node 流程通(ADR-0119)但**🚫 独立屏态停机隔离中**(待重建档) | P5(前置重建档) |
| PickWishTrialOption(idx) | 祈愿试炼 | **naive 第1张(决策函数缺:OCR objective+reward 评估)** | HandleWishTrial 代码在但 **🚫 停机隔离中**(建档 3.9 未做) | P5(前置 3.9) |
| **PickGrailQuestOption(idx)** | **命运圣杯任务二选一**(F 羁绊 2F/3F/4F/5F 展开触发,备战中弹) | **缺(待写;含 5F 令咒协议[-88HP 换 8 完美投影仪,需 ≥88HP 当关用完]/诅咒圣杯「3-4 后别接」/鲜血神殿激活态等高策略约束,详 docs/game/currency_war/guides/阵容_命运圣杯红A.md:22-46)** | 🚫 未建档(3.10 待确认);与工具域强联动(投影仪时效) | P5(前置 3.10 建档) |

P1-P4 过渡:内环遇 overlay → BailToOuter 交主循环分支。**⚠️ 现状语义(v5 核实)**:祈愿/补给/投资×2 四屏在主循环也是停机隔离态(battle_loop:216-227;yml 已建但未完整建档核实,L-4)→ bail 后同样停机,**与现状行为一致故零回归,但离「可用 handler」还差重建档**;巨星/伙伴/遭遇 bail 后走真 handler。
P5 收编前置:**overlay-vs-独立屏重建档**(3.9 祈愿/3.10 圣杯/补给/投资 id_mark 模型核实)→ 逐事件收编(巨星/伙伴/遭遇先,投资/补给/祈愿/圣杯后)→ 事件与 prep 决策共享 obs+session,主循环瘦身为纯路由。**P5 出口补充**:补给节点备战出口 = GoToSupplyScreen(点「返回补给阶段」,battle_loop:326-335 nodeseq 分流);备战被锁态出口 = GoPickStrategy(battle_loop:206)—— 两动作进 P5 动作集,出口判定需节点类型感知(nodeseq current)。

### 4.4 决策点全景索引(动作 ↔ 决策归属 ↔ 策略需求清单 §2 对齐;「决策函数」均属策略层,框架不实现)

| 决策点 | 决策函数 | 动作 | Phase |
|---|---|---|---|
| 买/升/刷 | plan() | BuyCard/LevelUp/RefreshShop | P1(组合 RunBuyPhase)→P2(原子) |
| 卖(席位域) | _weakest_bench_idx(待加 3合1 保护) | SellBench/LevelUp(腾席 b 步) | **P1 原子** |
| deploy(部署域) | plan() + **四项板上行为(D-10 换血/去重 5.1.7/前排保证 5.1.6/cap 门 5.1.8,现住 DeployBench 内,v7 注:非 naive,`_should_deploy`+`_pick_deploy_row` 不足以复现)** | RunDeploy(组合,P1)/DeployMove(原子,仅腾席链) | P1 组合 → P3 原子化时四行为上移策略 |
| 奖励收取/腾席 | §5 规则(复用现成评估) | ClickSpheres/OpenBox/SellBench/DeployMove/Defer | **P1** |
| **武装箱选卡** | _pick_card 现成(handle_supply_box:100-110,key_equips→材料通用性;v7 修三轮 M-3:P1 住执行器默认,PickBoxCard(idx=None) 触发;P5 上移策略) | PickBoxCard | P1(执行器默认)/P5(策略) |
| 工具使用 | **缺(待写,§4.2 十二件分类)** | UseProjector/UseWrench/UseSmelter/UsePrivilegeCard/UseLuckyToken | P4 |
| 装备穿戴/合成 | equip_fit/key_equips | WearEquip/Synthesize | P1(组合)→P3 |
| 事件选择(投资/巨星/伙伴/遭遇/补给/祈愿) | decide_*(现成,祈愿缺) | PickXxxOption | P5(前置:投资/补给/祈愿重建档) |
| **圣杯任务二选一(F 羁绊展开触发)** | **缺(待写;5F 令咒/诅咒圣杯等高策略约束)** | PickGrailQuestOption | P5(前置 3.10 建档) |
| 出战时机 | 环出口规则(§7) | StartBattle | P1 |

## 5. 框架不变式 vs 策略实现(v4 核心分离)

**环(PrepDirector)是框架** —— 不含任何玩法判断,只保证以下**不变式**(任何策略都必须在之上运行);
**「下一步做什么」的全部判断是策略**(CwStrategy 子类,可多实现 + 热插拔,见 11 号插件机制)。
§5.1-5.3 的规则降级为 `DefaultCwStrategy` 的**参考实现**(v1 规则版),非框架一部分。

### 5.0 框架不变式(环保证,策略可依赖)

```
F1 单步契约: 每步 = observe → decide_prep_action(obs) → execute(带验证) → 再 observe
F2 观察真实: obs 只由现成 reader 产出(框架不造数据);shop 开关互斥**由框架校验读取前置态**(不匹配报错),切换由 EnsureShopOpen/Closed 动作显式执行(v6 修 M-4)
F3 动作合法域: 策略输出的动作必须在 §4 动作全集内;框架校验参数(槽位存在/idx 界内)后执行
F4 验证与防护: 框架执行每动作并做完成验证;fail 计数/stall 屏蔽/预算强制出战(§7)对策略透明
F5 出口兜底: 策略不给 StartBattle 且 stall/预算耗尽 → 框架强制出战(策略挂了流程不断)
F6 无状态策略: 环不污染策略实例;跨步意图(defer 计数等)走 StrategySession(11 号原则 1)
F7 可换策略: strategy_id 由配置选(11 号);换策略只换决策,不换观察/执行/防护
F8 可回放: obs+action 序列落 telemetry(对齐 11 号「可离线测+可复盘」;replay 评分用)

**P1 交付范围(v6 修 M-7)**:F1-F7 全量 + F8 仅「obs+action 落盘」(复用 cw_telemetry);replay 评分后置(远期)
```

### 5.1 策略实现示例:奖励收取(free-slots 驱动;DefaultCwStrategy 参考实现)

```
1) boxes > 0 → OpenBox(下步观察弹层后 PickBoxCard;F1 单步契约,两步非一步,L-5)     # 箱白占席,先开=腾席+得装备
2) n_spheres > 0 且 free > 0 → ClickSpheres(k=min(free, n), 大球优先,内验早停;**掉箱即停回环**由规则 1 统筹 —— v5 定,替 handle_reward_sphere 现内联开箱行为)
3) n_spheres > 0 且 free == 0 且 defer_count < 2 → 腾席链(5.2)取一步,回 2(**DeferSpheres 时 defer_count+1,门=2 防规则 2↔3 空转环**;⚠️ **defer_count 是环级计数,Director 每次环入口由框架清零** —— session 字段、框架管重写,防局级累积把腾席链永久禁用,v6 修 H-1)
4) 球箱皆无 或 defer_count ≥ 2 → 主流程(5.3)【球留置;defer 不计 stall】
```

### 5.2 策略实现示例:腾席链(每步回环重判;优先级是默认策略的选择,非框架强制)

```
a. deploy_vacancy > 0 且有角色过 _should_deploy → DeployMove(零成本最优)
b. level < 10 且 gold ≥ LEVEL_UP_COST 且 level_plan 允许 → LevelUp(cap+1 → 回 a)。**gold 来源(⚠️ v5 修 M2):shop 关态不可读(读空/0)** —— 决策前 EnsureShopOpen 重读,或 session 跟踪金 + 动作后回读;勿裸调 read_gold 于关态
c. _weakest_bench_idx 有可卖(保 3合1 重复件)→ SellBench(身份感知)
d. 全是有用角色 → DeferSpheres(球留置,记 defer 计数进 session)
```

### 5.3 策略实现示例:主流程推进

工具检查(P4+:有投影仪+可复制核心→UseProjector 优先,3合1 价值最高)→ 买(RunBuyPhase→P2 原子)
→ 有可上(DeployMove)→ 有可穿(RunEquip→P3)→ 出口判定(§7)→ StartBattle。每步回环重判。
**P1 实现注(round-2 MED-4/LOW-1)**:主流程以 session.prep_phase 阶段位实现(环入口清零,出动作时前移 —— 阶段位是「本环走到哪段」的位置记忆,非每步从头重判;球/箱/腾席规则仍在每步全量重判);update_target 由框架在**环入口**调一次(shop.py:166 的 RunBuyPhase 内调用 = P1 允许的双调)。

> **换策略示例**:一个激进策略可以完全重写 5.1-5.3(如「血量健康期无视球先买牌,残血期才收球卖角换金」),
> 或继承 DefaultCwStrategy 只覆盖腾席链(如「永不卖角色,宁可留球」)。框架层(观察/验证/防护/回放)零改动。

## 6. 决策接口分层(v4:框架 vs 策略,对齐 11 号 ABC+Default 模板方法)

| 层 | 内容 | 变更频率 |
|---|---|---|
| **框架(PrepDirector + prep_actions)** | 环循环/观察组装/动作合法性校验/执行原语/完成验证/stall 防护/出口兜底/telemetry 落盘 | 稳(玩法知识零嵌入) |
| **策略接口(CwStrategy,11 号 ABC)** | **新增钩子 `decide_prep_action(obs, session, config) -> PrepAction`(abstract)**;既有 decide_prep/decide_invest/decide_supply/decide_encounter/decide_megastar/decide_partner 保留(P5 后由 decide_prep_action 在 overlay 态内部委托) | 接口稳定 |
| **默认策略(DefaultCwStrategy)** | decide_prep_action 具现 = §5.1-5.3 参考实现(委托 cw_decisions 既有函数:plan/_should_deploy/_weakest_bench_idx);继承者可整体覆盖或只覆盖局部 | 随玩法迭代 |
| **第三方策略(plugins/currency_war_strategies/)** | 继承 CwStrategy 全自研,或继承 Default 只覆盖关心的钩子(11 号两路) | 自由 |

要点:
- **ABC 钩子 abstract 化**(与 11 号原则 2 一致:ABC 纯接口;逻辑进 Default;⚠️ 破坏性接口变更:既有第三方子类需实现该钩子或临时具现 NotImplementedError 过渡,P1 同步更新 Default,L-5)—— v3 的「基类给默认实现」
  违反 11 号分层,v4 修正:default 实现住在 DefaultCwStrategy,不是 ABC;
- Director 是 **SrOperation**(单「决策环」节点 + 内部 while + round_retry 预算);`update_target` 环入口调一次;
- **P5 事件收编后**:所有决策(步级 + 事件)经 decide_prep_action 单一入口 —— 事件 decide_* 变为其内部
  委托的辅助钩子(实现不动,调用点收敛),策略作者只在入口写分发;
- **测试对齐 11 号 §11.10**:策略纯逻辑可离线测(喂构造 obs 断言 action);框架环用 mock controller 测;
  换策略不改框架测试。

## 7. 环出口(出战条件)与防死循环

**出口(StartBattle)**,全部满足:无球 或 球 Defer≥2(**环内计数,环入口清零,下轮重判** —— 留置是本轮决定非整局决定,v6 修 H-1);无箱;plan() 无正提升;无可上(deploy 满或无候选);
装备无可穿;工具无可用了(P4+)。

**防死循环(分层,v6 定优先级与生命周期,修 H-2)**:
- **优先级(P1 实现定稿,review round-1 H-2 修订;ADR-0123)**:动作验证失败 → 同一动作连续 2 次失败 → 恢复原语(**一次/动作实例**;分型:点空白/已建档 modal ESC/点 ×)→ 恢复后仍连败 2 = 恢复无效 → **按恢复原语分型上抛**:关过已知弹层仍败 = 弹层顽固/未知 → **BailToOuter**(环让位,外环弹层分支/停机钩子接手);仅兜底点空白(无已知弹层)仍败 = 状态/识别类失败 → **本环屏蔽**该动作实例(策略须换路;StartBattle 豁免)。屏蔽与 bail 不双响应(各管辖一类失败:屏蔽 = 动作级熔断环继续;bail = 环级让位);
- 动作级:每动作带验证;同动作 fail≥2 → 本环屏蔽(**StartBattle 豁免**;屏蔽命中时:该步计 stall + telemetry 记录,框架**拒绝执行**被屏蔽动作 —— 策略确定性重提案同动作会被拒,不静默跳过,修 M-5);
- 环级:stall≥5 或步数>60 → 强制 StartBattle(**P1 判定式:v6 修 H-2b —— 去「无弹层」前提(overlay_state 是 P5 字段,P1 不可判),改为「连续 K(=5) 步零进展 **且恢复原语已试尽(同动作连败 2 次已触发过)**」—— 恢复试尽仍零进展,强制品是最后手段;弹层场景实际走不到这(恢复无效先 bail 了)**);
- 出战级:现转移验证 6×0.5s 轮询不动;
- **外环 ping-pong 防护**:bail → 外环 → 重入重建 Director(stall/屏蔽/defer 计数全清零)若再 bail,由主循环 **MAX_ITER=2000 对局预算兜底**(⚠️ v7 修三轮 M-1:round_wait 不消耗 node 重试预算(operation.py:453-461 仅 RETRY 递增),勿引 node_max_retry_times);连续 bail≥3 同因 → 记 [cw!] 升诊断(**计数宿主 = StrategySession 局级字段,不在环重建清零清单内**,局终销毁)。
**排除清单(非决策点,框架与策略都不处理)**:攻略/教学/数据银行/数据统计按钮(纯信息查看)、商店刷新概率表弹窗(纯展示)、惊喜盒(倒计时自动开启,点击仅 tooltip)、商店锁定(shop_locked 字段全仓无读写 + 备战无锁定按钮 → CW 无此机制,字段按「None 不说谎」原则清理)。「不处理」指不作决策目标;概率表弹窗作为遮挡仍会被恢复原语关闭(点 ×,L-1)。

**组合动作命名映射**(L1):RunBuyPhase=BuyShopCards / RunEquip=EquipAll / RunDeploy=DeployBench(代码实名)。
**组合动作 progressed 语义弱化**(round-2 MED-6):P1 组合动作 progressed = 子 op is_success(含 no-op 成功,如「备战席已满清警告」),非严格状态进展;默认策略因 prep_phase 单调无活害,P2 原子化消除。自定义策略勿依赖组合动作清 stall。
P1 允许 update_target 双调(Director 环入口 + shop.py:166 各一次,无害);P2 溶解 RunBuyPhase 时删 shop.py 内调用(L7)。
P1 挂载切换时搬 battle_prep 的临时采集钩子进 Director 观察阶段:_verify_recognition/_probe_node_type 搬;**_verify_equipped 不搬**(随 RunEquip 组合动作保留在 EquipAll 后调用,采样不断,L-1)。

## 8. 迁移路径(P1 环+新域原子 → P5 事件收编)

| Phase | 内容 | 风险控制 |
|---|---|---|
| **P1 环 + 奖励/席位/战斗原子** | Director 环;ClickSpheres/OpenBox/PickBoxCard/SellBench/SellDeployed/DeployMove(仅腾席链)/StartBattle + **LevelUp + EnsureShopOpen/Closed**(v6 修 H-4:腾席链 b 步与 gold 读取需此三原子,实现极薄 = 各一个 click+锚点验证)全原子;商店/装备组合(RunBuyPhase/RunEquip)+ **RunDeploy(DeployBench 整体,v7 修三轮 H-2:保 D-10 换血/同角色去重 5.1.7/前排保证 5.1.6/cap 门 5.1.8 四项板上行为 —— `_should_deploy`+`_pick_deploy_row` 不足以复现(cw_decisions:511-521/809-820 无此四项),全原子切换会静默回归;且组合部署避免逐 DeployMove 触发 SIFT 重观察);四行为 P2/P3 部署域原子化时上移策略规则)**;遇 overlay → BailToOuter。**⚠️ P1 残留风险(M-6):defer-尽(free==0)仍进 RunBuyPhase 时,shop.py 内 _handle_bench_full 位置式卖(症状2)活着 —— 默认策略加门:进 RunBuyPhase 前保证 free>0,否则跳过买牌直奔出口** | 新域一次做对;旧 op 内部一行不动;bail 零回归 |
| **P2 买牌原子化** | 拆 plan() 单步;_handle_bench_full 退役;两阶段 hack 淘汰 | fixture 动作序列 diff |
| **P3 部署/装备原子化** | RunEquip→WearEquip;off-target 卖上移为 SellBench/SellDeployed 决策;BattlePrepCycle 退役 | 同上 |
| **P4 工具域** | UseProjector/UseWrench/UseSmelter 原子 + 决策函数(投影仪复制核心最优先做,3合1 高价值) | 新增域,不动旧链 |
| **P5 事件域收编** | overlay 态进 obs(§3);PickXxxOption 进环(内部委托现成 decide_*,含圣杯 PickGrailQuestOption);出口补 GoToSupplyScreen/GoPickStrategy;主循环瘦身为纯路由;祈愿策略函数补(OCR objective+reward) | **前置:祈愿 3.9/圣杯 3.10/补给/投资×2 重建档**;收编顺序 = 巨星/伙伴/遭遇先(已建档),投资/补给/祈愿/圣杯后(重建档完);收编一个验一个 |

每 Phase 独立 live 验证(`run_operation` 稳定 M=3),不并行。

## 9. 测试策略

- **决策单测**(表驱动):球+free>0→ClickSpheres(k=free);球+free=0 链各分支;有箱→OpenBox 优先;
  投影仪+3费核心→UseProjector(P4);overlay 态→对应 PickXxx(P5);出口全件→StartBattle;stall 屏蔽;
- **执行器单测**:每原子动作 mock controller + fixture 断言验证;
- **Director fixture 测**:fixture 屏序列 → 断言动作序列;
- **回归**:现有 op/handler 测试不动;P3 前 BattlePrepCycle 可切回;P5 每事件收编前后主循环分支保留一版。

## 10. 开放问题(默认已选,可推翻)

| 问题 | 默认 | 备选 |
|---|---|---|
| 球收取粒度 | ClickSpheres(k=free) 带内验早停 | 纯单球(观察多)/纯批(危险) |
| 球价值排序 | r 大优先 | comp 需求感知(策略-stage) |
| 卖角保留件 | 3合1 重复件不卖 | 纯 _weakest_bench_idx |
| 工具决策优先级 | P4 内先投影仪(复制核心),扳手/冶金炉后(需期望值模型) | 全一起做(慢) |
| 事件收编节奏 | P5 每事件单独收编逐一验 | 一次全收(回归风险大) |
| 祈愿策略 | P5 补(OCR objective+reward → 易完成度/契合打分) | 保持 naive |
| stall 预算 | 5 步 / 60 总步 | 实跑校准 |
| 框架/策略边界微调 | §5.0 八条不变式;策略可完全重写 5.1-5.3 | 不变式加多(过度约束策略)/加少(框架失守) 都待实跑反馈 |

## 11. 与既有文档关系

- [01 架构](01_architecture.md):本文把「op 层执行」细化为「两层环+原子执行器」,三层不动;
- [02 评估搜索](02_eval_search.md):plan()/evaluate() 复用,调用时机从批量变逐步;
- [08 节点决策](08_node_decisions.md):事件 decide_* 函数即 §4.3 的决策依据,P5 收编不重写;
- 策略需求清单 §2:实现时补「备战步级决策(decide_prep_action)+ 工具使用决策」行。

## 12. 实现落点(代码地图)

```
src/sr_od/application/currency_war/
├── prep_director.py            # 新【框架】:PrepDirector(两层环之内环)+ PrepObservation(overlay_state P1 恒 None,P5 填充,L-4)+ 不变式F1-F8
├── cw_strategy.py              # 【接口】+decide_prep_action(abstract ABC 钩子)
├── strategies/default_strategy.py  # 【默认策略】decide_prep_action 具现 = §5.1-5.3 参考实现
├── cw_decisions.py             # 复用:_should_deploy/_weakest_bench_idx/plan/LEVEL_UP_COST_TABLE
├── prep_actions.py             # 新:原子执行器(奖励/席位/商店/装备/战斗/工具,各带完成验证)
└── operations/
    ├── battle_loop.py          # P5 瘦身为纯路由(事件分支逐个移除)
    ├── prep/battle_prep.py     # P1 挂载点切 PrepDirector;P3 退役
    └── handlers/*              # 事件 handler P5 后退役(决策进环,执行器留)
```

## 13. P1 接口规格(附录;v7 补三轮 M-2,开工前置)

### 13.1 PrepAction 关键定义(dataclass 草案,实现可微调)

```
# slot 语义(全局统一):物理槽位 —— 备战栏 1-9 / 前排 1-4 / 后排 1-6;非 bench 列表下标!
# ⚠️ 现有 cw_state.SellBench(bench_idx) 与 _weakest_bench_idx 返回的是 bench 列表下标(cw_state.py:169),
#   执行器负责换算:slot = bench 列表第 idx 个 BenchChar 的 bc.slot(物理槽位);策略层输出一律物理槽位。
SellBench(slot: int)              # 卖备战槽 slot(1-9)
SellDeployed(row: str, slot: int) # 卖已上阵(row front/back + 槽位)
DeployMove(from_slot: int, to_row: str, to_slot: int)  # 腾席链专用(P1)
LevelUp() / EnsureShopOpen() / EnsureShopClosed() / StartBattle()
ClickSphere(center: Point) / ClickSpheres(max_k: int)  # 单球/带上界批(内验早停)
OpenBox(slot: int) / PickBoxCard(card_idx: int | None) # None=执行器内嵌默认选卡(v7 修三轮 M-3)
DeferSpheres() / BailToOuter(reason: str)              # 控制流(§4.2b)
RunBuyPhase() / RunDeploy() / RunEquip()               # 组合(P1 过渡)
```

### 13.2 execute 失败契约(三路径)

| 路径 | 语义 | 框架行为 |
|---|---|---|
| 验证失败 | 动作执行但完成验证不过(球没少/槽没空) | 计该动作实例 fail;连败 2 次 → 恢复原语 → 无效 bail(§7) |
| 参数非法 | F3 校验不过(slot 越界/动作被屏蔽) | **拒绝执行 + log + 该步计 stall + telemetry 记录**(策略下步重提案;M-5 全量语义) |
| 执行异常 | 原语抛异常(控制器/图异常) | 上抛 = 本环 fail(外层 op retry 机制接管) |

**屏蔽计数粒度**:按「动作类型 + 参数」实例计(SellBench(3) 与 SellBench(5) 各自计数)。

### 13.3 恢复原语 × 已知弹层映射(P1 清单)

| 弹层 | 关闭原语 | 建模状态 |
|---|---|---|
| 消耗品详情 modal | ESC | ✅ 已建档(battle_loop:287-295) |
| 可合成列表 overlay | ESC | ✅ 已建档(battle_loop:339-346) |
| 概率表弹窗 | 点 ×(1502,258) | ✅ 已建档(shop_refresh_odds) |
| 角色详情面板 | CloseOverlay 点空白(960,530;⚠️ 700,400 旧值前排有人时=前排-1 槽,已修) | ✅ 3.12 建档 |
| 武装箱选择 overlay | **非恢复对象**(是决策面,非异常) | ✅ 3.15 建档 |
| 其余未知弹层 | CloseOverlay 点空白(960,530 真空白=前后排之间) | — 兜底 |

### 13.4 PrepObservation P1 恒空字段

overlay_state / overlay_options(P5 填充)、shop_cards(仅买牌阶段刷新)—— P1 其余场景恒 None/空,策略不得依赖。
