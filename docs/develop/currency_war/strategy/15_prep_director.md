# 15 备战决策环(PrepDirector)—— 备战编排从固定序列到观察驱动(v3 决策点全景)

> 总见 [README](README.md)。本文:备战画面内「下一步做什么」的决策架构 —— 观察驱动单步决策环,
> 替代 BattlePrepCycle 固定序列。2026-08-14 用户定调(触发:奖励球 + 备战席满,球拖一轮才收);
> **v2 修订**:动作全集原子化(宏动作被否);**v3 修订**:补全**事件域**(投资策略/环境、盛会之星、
> 伙伴、祈愿、遭遇、补给 overlay 选择)与**工具域**(扳手/冶金炉/投影仪使用)—— 决策点全景纳入,
> 两层环架构(外环路由 + 内环步级决策)。ADR-0123 记录决策。

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
    ▼ 备战态
内环 PrepDirector(新,替换 BattlePrepCycle):备战画面步级决策
  while True:
    obs = observe(ctx, screen)                        # ① 统一观察(轻/重分层;P5 含 overlay 态)
    action = strategy.decide_prep_action(obs,         # ② 决策:一个动作(原子为主)
                             session, config)
    if isinstance(action, StartBattle): break        #    环出口 = 出战
    if isinstance(action, BailToOuter): break        #    交外环(事件 overlay,P1-4 过渡期)
    progressed = execute(action)                     # ③ 执行器:动作 → 原语(带完成验证)
    if not progressed: stall += 1                    # ④ 无进展防护(§7)
```

对照目标场景:`有球+bench 9/9+deployed 5/6` → DeployMove(上排腾席)→ 再观察 →
`有球+free=1` → ClickSpheres(上界1)→ 再观察 → … → StartBattle;
`owned 有员工投影仪 + bench 有 3费核心` → UseProjector(核心)→ 再观察(bench 多 1 张核心=3合1 进度)。

## 3. 统一观察(PrepObservation)

决策的单一输入。**组合现成 reader,不新写识别**:

| 字段 | 来源(现成) | 轻/重 |
|---|---|---|
| state: GameState(gold/hp/level/phase/board/deployed/bench) | read_game_state(session tracking 合并) | 重(阶段边界) |
| spheres / boxes | read_reward_spheres / read_supply_boxes | 轻(每步) |
| free_bench_slots: int | 9 − bench 占用(角色+箱都占席) | 轻 |
| deploy_vacancy: int | read_deploy_cap − read_deployed_count | 轻 |
| owned_equips(含 category=工具) | read_equips(SIFT;工具名已在模板库:扳手/冶金炉/投影仪) | 重 |
| overlay_state: None | 投资策略/环境/巨星/伙伴/祈愿/武装箱/遭遇/补给 | 各屏 id_mark 锚点(全已建档) | 轻(P5) |
| overlay_options | 各 handler 现成 _read_options(OCR 卡名) | 重(overlay 态) |
| shop_cards / shop_open | read_shop_cards / 锚点 | 重(买牌阶段) |

**成本控制**:轻观察(CV 级)每步;重观察(SIFT/shop 全读/read_game_state)只在阶段边界或结构变化时。
**shop 开关互斥**(gold 只在开态、HP 只在关态)→ EnsureShopOpen/Closed 动作显式管理。

## 4. 动作全集(原子化 + 决策点全景,v3 核心)

### 4.1 奖励/商店/席位/装备/战斗域(v2 已盘,此处摘要)

| 域 | 原子动作 | 决策依据(现成) | 验证 |
|---|---|---|---|
| 奖励 | ClickSphere / **ClickSpheres(k=min(free,n),带内验早停)** / OpenBox / PickBoxCard | 大球优先;箱必开;k=free-slots 驱动 | 球数−1/overlay 态翻转/owned+ |
| 商店 | BuyCard / BuyXP / LevelUp(=BuyXP×k) / RefreshShop | plan() eval-delta / level_plan / 蒙特卡洛 | 金变/牌变/level+1 |
| 席位 | **SellBench(slot,身份感知)** / **SellDeployed(slot,换阵卸位)** / DeployMove(from,to) | _weakest_bench_idx(保 3合1 件)/ off-target(D-10)/ _should_deploy+_pick_deploy_row | 源空+gold+ / 源空+目标占 |
| 装备 | WearEquip(equip,slot) / Synthesize(defer) | key_equips 优先(角色级分配 P4) | below-icon CV-diff |
| 战斗 | StartBattle(含未达上限确认) | 环出口全件(§7) | 备战标识消失 |
| 观察管理 | EnsureShopOpen/Closed / CloseOverlay(960,530 真空白) | 读取前置/异常恢复 | 锚点翻转 |

### 4.2 工具域(v3 新增,决策函数缺,P4)

工具 = owned 中 category=工具 的装备,**拖到目标上使用**(非穿戴)。机制(cw_equipment_data 权威):

| 动作 | 机制 | 决策要点(函数待写) | 价值 |
|---|---|---|---|
| **UseProjector(员工投影仪, target_char)** | 拖到 ≤3费角色 → 备战席造该角色 1星复制 | **复制谁**:target 核心(≤3费)凑 3合1 直升 2星;无核心可复制→留 | ⭐⭐⭐ 3合1 神器 |
| **UsePerfectProjector(完美投影仪, target_char)** | 任意角色 → 1星复制 | 同上不限费(可复制高费核心) | ⭐⭐⭐ |
| **UseWrench(拆装扳手, target_char)** | 拖到角色 → 取下其所有装备(一次性) | **何时卸**:卖角/换阵前回收装备(装 ≥扳手残值时);精密版无限次 | ⭐⭐ 装备回收 |
| **UseSmelter(冶金炉, target)** | 拖到装备→变同类随机;拖到角色→卸装并全变随机 | **赌重roll**:垃圾装备换随机 ≥ 手动卖;何时值得(期望值) | ⭐⭐ 垃圾转化 |

### 4.3 事件域(overlay 选择,P5 收编进环;决策函数大多现成)

| 动作 | overlay 画面 | 决策依据 | 现状(接线) | 进环 |
|---|---|---|---|---|
| PickInvestOption(kind, idx) | 投资策略/投资环境 | decide_invest(白名单+克制,✅) | HandleInvestStrategy/Env(主循环分支,✅) | P5 |
| PickMegastarOption(idx) | 盛会之星 | decide_megastar(core_chars 命中,✅) | run_megastar_node(✅) | P5 |
| PickPartnerOption(idx) | 选择伙伴 | decide_partner(build_around/core,🟡 输入受限需 SIFT) | handle_select_partner(✅) | P5 |
| PickEncounterOption(idx) | 遭遇其一/其四 | decide_encounter(✅ 非平凡) | HandleEncounter(✅) | P5 |
| PickSupplyOption(idx) | 补给选装备/出钻 | decide_supply(✅) | run_supply_node(✅) | P5 |
| PickWishTrialOption(idx) | 祈愿试炼 | **naive 第1张(决策函数缺:OCR objective+reward 评估)** | HandleWishTrial(✅ 时序) | P5 |

P1-P4 过渡:内环遇 overlay → `BailToOuter` 交主循环现有分支(现 BuyShopCards bail 同模式,零回归风险);
P5 收编:overlay 态进 obs(§3 overlay_state/options),事件决策与 prep 决策**共享同一 obs + session**(治症状6),
主循环瘦身为纯路由(战斗/结算/过渡/大厅)。

### 4.4 决策点全景索引(动作 ↔ 策略需求清单 §2 对齐)

| 决策点 | 决策函数 | 动作 | Phase |
|---|---|---|---|
| 买/升/刷/卖/deploy | plan() | BuyCard/LevelUp/RefreshShop/SellBench/DeployMove | P1(组合)→P2(原子) |
| 奖励收取/腾席 | §5 规则(复用现成评估) | ClickSpheres/OpenBox/SellBench/DeployMove/Defer | **P1** |
| 工具使用 | **缺(待写,§4.2 决策要点)** | UseProjector/UseWrench/UseSmelter | P4 |
| 装备穿戴/合成 | equip_fit/key_equips | WearEquip/Synthesize | P1(组合)→P3 |
| 事件选择(投资/巨星/伙伴/遭遇/补给/祈愿) | decide_*(现成,祈愿缺) | PickXxxOption | P5 |
| 出战时机 | 环出口规则(§7) | StartBattle | P1 |

## 5. 决策规则(v1 规则版)

### 5.1 奖励收取(free-slots 驱动)

```
1) boxes > 0 → OpenBox + PickBoxCard     # 箱白占席,先开=腾席+得装备
2) n_spheres > 0 且 free > 0 → ClickSpheres(k=min(free, n), 大球优先,内验早停)
3) n_spheres > 0 且 free == 0 → 腾席链(5.2)取一步,回 2
4) 球箱皆无 → 主流程(5.3)
```

### 5.2 腾席决策链(每步回环重判)

```
a. deploy_vacancy > 0 且有角色过 _should_deploy → DeployMove(零成本最优)
b. level < 10 且 gold ≥ LEVEL_UP_COST 且 level_plan 允许 → LevelUp(cap+1 → 回 a)
c. _weakest_bench_idx 有可卖(保 3合1 重复件)→ SellBench(身份感知)
d. 全是有用角色 → DeferSpheres(球留置,记 defer 计数)
```

### 5.3 主流程

工具检查(P4+:有投影仪+可复制核心→UseProjector 优先,3合1 价值最高)→ 买(RunBuyPhase→P2 原子)
→ 有可上(DeployMove)→ 有可穿(RunEquip→P3)→ 出口判定(§7)→ StartBattle。每步回环重判。

## 6. 决策接口(CwStrategy 演进)

- 新方法 `decide_prep_action(obs, session, config) -> PrepAction`,**基类默认实现**(v1 规则 = §5,委托
  cw_decisions 既有函数),DefaultStrategy 可覆盖 —— 非 abstract,不破坏插件体系;
- `decide_prep`(批量 shop 计划)保留(RunBuyPhase 内用,P2 溶解);事件 `decide_*`(invest/megastar/
  partner/encounter/supply)保留 —— P5 后由 decide_prep_action 在 overlay 态内部委托调用(单一入口,实现不动);
- Director 是 **SrOperation**(单「决策环」节点 + 内部 while + round_retry 预算);`update_target` 环入口调一次。

## 7. 环出口(出战条件)与防死循环

**出口(StartBattle)**,全部满足:无球 或 球 Defer≥2;无箱;plan() 无正提升;无可上(deploy 满或无候选);
装备无可穿;工具无可用了(P4+)。

**防死循环**:动作级(每动作带验证;fail≥2 本回合屏蔽)+ 环级(stall≥5 或步数>60 → 强制 StartBattle)
+ 出战级(现转移验证 6×0.5s 轮询不动)。

## 8. 迁移路径(P1 环+新域原子 → P5 事件收编)

| Phase | 内容 | 风险控制 |
|---|---|---|
| **P1 环 + 奖励/席位/战斗原子** | Director 环;ClickSpheres/OpenBox/PickBoxCard/SellBench/SellDeployed/DeployMove/StartBattle 全原子;商店/装备组合(RunBuyPhase/RunEquip);遇 overlay → BailToOuter | 新域一次做对;旧 op 内部一行不动;bail 零回归 |
| **P2 买牌原子化** | 拆 plan() 单步;_handle_bench_full 退役;两阶段 hack 淘汰 | fixture 动作序列 diff |
| **P3 部署/装备原子化** | RunEquip→WearEquip;off-target 卖上移为 SellBench/SellDeployed 决策;BattlePrepCycle 退役 | 同上 |
| **P4 工具域** | UseProjector/UseWrench/UseSmelter 原子 + 决策函数(投影仪复制核心最优先做,3合1 高价值) | 新增域,不动旧链 |
| **P5 事件域收编** | overlay 态进 obs(§3);PickXxxOption 进环(内部委托现成 decide_*);主循环瘦身为纯路由;祈愿策略函数补(OCR objective+reward) | 每事件单独收编(投资→巨星→伙伴→…),收编一个验一个 |

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

## 11. 与既有文档关系

- [01 架构](01_architecture.md):本文把「op 层执行」细化为「两层环+原子执行器」,三层不动;
- [02 评估搜索](02_eval_search.md):plan()/evaluate() 复用,调用时机从批量变逐步;
- [08 节点决策](08_node_decisions.md):事件 decide_* 函数即 §4.3 的决策依据,P5 收编不重写;
- 策略需求清单 §2:实现时补「备战步级决策(decide_prep_action)+ 工具使用决策」行。

## 12. 实现落点(代码地图)

```
src/sr_od/application/currency_war/
├── prep_director.py            # 新:PrepDirector(两层环之内环)+ PrepObservation(含 overlay_state)
├── cw_strategy.py              # +decide_prep_action(基类默认:v1 规则 = §5;P5 内部委托 decide_*)
├── cw_decisions.py             # 复用:_should_deploy/_weakest_bench_idx/plan/LEVEL_UP_COST_TABLE
├── prep_actions.py             # 新:原子执行器(奖励/席位/商店/装备/战斗/工具,各带完成验证)
└── operations/
    ├── battle_loop.py          # P5 瘦身为纯路由(事件分支逐个移除)
    ├── prep/battle_prep.py     # P1 挂载点切 PrepDirector;P3 退役
    └── handlers/*              # 事件 handler P5 后退役(决策进环,执行器留)
```
