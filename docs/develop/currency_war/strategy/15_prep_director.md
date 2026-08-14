# 15 备战决策环(PrepDirector)—— 备战编排从固定序列到观察驱动(v2 原子化修订)

> 总见 [README](README.md)。本文:备战画面内「下一步做什么」的决策架构 —— 观察驱动单步决策环,
> 替代 BattlePrepCycle 固定序列。2026-08-14 用户定调(触发:奖励球 + 备战席满,球拖一轮才收);
> **v2 修订(同日用户 review)**:动作全集原子化(初版宏动作被否 —— FreeBench 藏卖角色决策、
> CollectSpheres 粒度含糊),奖励球收取改为 **free-slots 驱动**。ADR-0123 记录决策。

## 1. 问题(为什么改)

现状 BattlePrepCycle = **固定流水线** `(收球→买牌→部署→装备→出战)`,编排顺序硬编码,不看画面状态。README 核心哲学「观测驱动而非预测驱动」只落实到**回合级**(hp_trend/对账),备战内部是开环。具体症状:

| # | 症状 | 根因 |
|---|---|---|
| 1 | 奖励球 + 席满 → 收球 op 中断,腾席在买牌 op 里,时序脱节 → **球拖一整轮才收**(每轮漏收=损失) | 腾席决策被硬编码在「买牌」节点内,收球触不到 |
| 2 | `_handle_bench_full` 无脑卖 bench-1..3(位置式,不认身份)→ 可能卖掉核心角色 | 腾席无身份感知,而价值评估(`_weakest_bench_idx`)早已存在但只在 plan() 内 |
| 3 | 腾席候选不完整:不考虑「拖到前后台空位」「升级扩容」这类更优解 | 腾席不是一个决策点,是买牌 op 的副作用 |
| 4 | plan() 是批量快照,RefreshShop 后动作过期 → shop.py 需两阶段 hack(执行至首个刷新→重OCR→重plan) | 批量计划 vs 状态会变 |

用户目标场景(2026-08-14):「现在有奖励未领,然后备战又满了,就要解决备战满的问题 —— 可能拖到前后台,可能找一个无关紧要角色卖掉,可能都有用不能卖,奖励球就留着。做了一步之后,再识别,再决定下一步怎么做。」

## 2. 目标架构(是什么)

```
PrepDirector(新编排 op,替换 BattlePrepCycle 在主循环中的位置)
  while True:
    obs = observe(ctx, screen)                        # ① 统一观察(轻/重分层)
    action = strategy.decide_prep_action(obs,         # ② 决策:一个动作(原子为主)
                             session, config)
    if isinstance(action, StartBattle): break        #    环出口 = 出战
    progressed = execute(action)                     # ③ 执行器:动作 → 原语(带完成验证)
    if not progressed: stall += 1                    # ④ 无进展防护(见 §7)
```

对照目标场景走一遍:`obs: 有球 + bench 9/9 + deployed 5/6(deploy 有空位)` →
`DeployMove(最弱可上角色 → 后排空位)` → 执行(强化板 + 腾 1 席,验证源空目标占)→ 再观察 →
`obs: 有球 + free=1` → `ClickSpheres(上界 1,大球优先)` → 执行(验证球减;若给角色→free=0 早停)→
再观察 → … → 无球无箱无正提升 → StartBattle。

## 3. 统一观察(PrepObservation)

决策的单一输入。**组合现成 reader,不新写识别**:

| 字段 | 来源(现成) | 轻/重 |
|---|---|---|
| state: GameState(gold/hp/level/phase/board/deployed/bench) | read_game_state(session tracking 合并) | 重(阶段边界) |
| spheres: list[(color, center, r)] | read_reward_spheres(HoughCircles) | 轻(每步) |
| boxes: list[(slot, center)] | read_supply_boxes(TM) | 轻(每步) |
| free_bench_slots: int | 9 − bench 占用(角色 + **箱都占席**,2026-08-14 实测) | 轻(bench 占用 CV/跟踪) |
| deploy_vacancy: int | read_deploy_cap − read_deployed_count | 轻 |
| owned_equips | read_equips(SIFT) | 重 |
| shop_cards / shop_open | read_shop_cards / 锚点 | 重(买牌阶段) |

**成本控制**:轻观察(CV 级:球 Hough/箱 TM/bench 占用灰度/部署数 OCR)每步做;重观察(SIFT 身份/
shop 全读/read_game_state)只在阶段边界或轻观察检测到结构变化时刷新。**shop 状态互斥**(gold 只在
shop 开态可读,HP 只在关态):观察层标 shop_open,需要 gold 的决策在 shop 域动作前自然开 shop。

## 4. 动作全集(原子化盘点,v2 核心)

**每个现有 op 拆到底**(执行原语 = 一次点击/一次拖拽;语义动作 = 决策单位,可对应多个原语循环):

### 4.1 原子动作清单(决策单位 × 执行 × 验证 × 现有出处)

| 域 | 动作 | 参数 | 决策依据(现成) | 执行原语 | 完成验证 | 现有出处 |
|---|---|---|---|---|---|---|
| 奖励 | **ClickSphere** | (color,r,center) 选哪个球 | 球价值(大球优先;内容不可预知) | click(球心) | 球数−1;掉箱→boxes+1 | CollectRewardSpheres 现逻辑 |
| 奖励 | **ClickSpheres(k)** | k=上界 | **free-slots 驱动:k=min(free, n_spheres)** | ClickSphere×k **带内验**:逐球点+逐球轻验,早停(球尽/席满/掉箱/点不动) | 同上,批内完成 | 新(从收球 op 抽单球步) |
| 奖励 | **OpenBox** | slot | 有箱必开(箱白占 1 席;开=腾席+得装备) | click(槽开启文字区) | 武装箱 overlay 出现 | HandleSupplyBox |
| 奖励 | **PickBoxCard** | 卡名/序 | key_equips 命中 > 材料通用性表 > 第1卡 | click(卡身) | overlay 关 + owned+ | HandleSupplyBox |
| 商店 | **BuyCard** | idx(1-5) | plan() eval-delta | click(牌) | 金−/牌消失/bench+ | shop.py L214 |
| 商店 | **BuyXP** | 一次(+4 XP) | (不单独决策) | click(购买经验) | XP 进度+ | shop.py L231 |
| 商店 | **LevelUp**(语义) | 至 level+1 | plan()/level_plan/_expected_level | BuyXP×k 循环 | level 数字+1 | shop.py 现循环 |
| 商店 | **RefreshShop** | — | plan() 蒙特卡洛 D 牌 | click(刷新) | 5 牌全变 | shop.py L238 |
| 席位 | **SellBench** | slot(**身份感知:卖谁是指令参数**) | _weakest_bench_idx(非核心;⚠️ 保留 3合1 重复件:目标核心的同名 2 张别卖) | drag(槽→出售区,走 drag_char) | 源槽空 + gold+ | deploy_bench 卖拖拽(位置式版在 _handle_bench_full,P2 退役) |
| 席位 | **DeployMove** | from_slot, (row, idx) | _should_deploy + _pick_deploy_row | drag(拖上任,DragCwChar) | 源空 + 目标占(CV) | deploy_bench/DragCwChar |
| 装备 | **WearEquip** | equip, board_slot | key_equips 优先(角色级分配 P4) | drag(装备→槽) | below-icon CV-diff | EquipAll 单步 |
| 装备 | Synthesize | equipA+B | 配方需求(**defer**,现 EquipAll 触发式) | — | — | EquipAll 触发现状 |
| 战斗 | **StartBattle** | — | 环出口全件(§7) | click(出战) + 未达上限确认 | 备战标识消失(6×0.5s 轮询) | battle_prep 现逻辑 |
| 观察管理 | EnsureShopOpen / EnsureShopClosed | — | 读 gold / 读 HP 前置 | click(商店/收起) | 锚点状态翻转 | shop.py 现逻辑 |
| 恢复 | CloseOverlay | — | 异常 overlay(角色详情等) | click(960,530 真空白) | overlay 消失 | PANEL_CLOSE(ADR 修正后) |

### 4.2 组合动作(仅过渡期,P2/P3 溶解为原子)

| 动作 | Phase | 映射 | 退役 |
|---|---|---|---|
| RunBuyPhase | P1 | BuyShopCards op 整体(内部 plan 两阶段不动) | P2(拆为 BuyCard/LevelUp/RefreshShop/SellBench 原子步,淘汰两阶段 hack + _handle_bench_full) |
| RunEquip | P1 | EquipAll op 整体 | P3(拆为 WearEquip 步) |
| RunDeploy | P1 | DeployBench op 整体 | P3(其内 _sell_offtarget_deployed 上移为 SellBench 决策) |

**P1 原则:新域(奖励/席位/战斗)从第一天就是原子** —— 这是本次重构的动机所在,一次做对;
旧域(商店/装备)内部逻辑重(live 验过的两阶段/CV 验穿),组合过渡一个 Phase 再拆。

## 5. 决策规则(v1 规则版,腾席链是核心)

### 5.1 奖励收取(free-slots 驱动,用户定调)

```
obs: n_spheres, boxes, free = 9 − bench占用(箱占席), deploy_vacancy

1) boxes > 0 → OpenBox + PickBoxCard      # 箱白占席,先开=腾席+得装备,零损失
2) n_spheres > 0 且 free > 0
     → ClickSpheres(k = min(free, n_spheres), 大球优先)
       执行内验逐球早停:球尽 / free→0(给了角色或箱) / 掉箱(转 1 再回来) / 点不动(→ 5.2)
3) n_spheres > 0 且 free == 0 → 腾席决策链(5.2)取一步,执行后回 2
4) n_spheres == 0 且 boxes == 0 → 买/部署/穿/出战 流程
```

### 5.2 腾席决策链(优先级,每步回环重判)

```
a. deploy_vacancy > 0 且有 bench 角色过 _should_deploy
     → DeployMove(上排:强化板 + 腾席,零成本最优)
b. level < 10 且 gold ≥ LEVEL_UP_COST_TABLE[level+1] 且 level_plan/期望等级允许
     → LevelUp(cap+1 → 产生 deploy 空位 → 回 a)
c. _weakest_bench_idx 有可卖(非核心;保留 3合1 重复件 —— 目标核心同名 2 张在凑第 3 张,不卖)
     → SellBench(身份感知;替位置式卖 bench-1..3)
d. 全是有用角色 → DeferSpheres(球留置;记 defer 计数,出口条件与下轮决策用)
```

全部复用现成评估函数(`_should_deploy`/`_weakest_bench_idx`/`LEVEL_UP_COST_TABLE`/level_plan)。

### 5.3 主流程(奖励处理完后的常规推进)

买(RunBuyPhase→P2 原子)→ 有可上且有空位(DeployMove,单步)→ 有可穿(RunEquip→P3 WearEquip)
→ 出口判定(§7)→ StartBattle。每步回环重判(买了牌可能产生新 deploy 意图)。

## 6. 决策接口(CwStrategy 演进)

- 新方法 `decide_prep_action(obs, session, config) -> PrepAction`,**基类给默认实现**(v1 规则版 = §5,委托
  cw_decisions 既有函数),DefaultStrategy 可覆盖 —— 非 abstract,不破坏插件体系;
- `decide_prep`(批量 shop 计划)保留:RunBuyPhase 内部经 BuyShopCards 间接使用,P2 溶解;
- Director 是 **SrOperation**(单「决策环」节点 + 内部 while + round_retry 预算),替换主循环挂载点;
- `update_target` 环入口调一次(现语义)。

## 7. 环出口(出战条件)与防死循环

**出口(StartBattle)**,全部满足:
- 无球 或 球连续 Defer≥2(留置判定,防反复尝试);
- 无箱;
- plan() 无正提升动作(现贪心终止条件);
- 无 deploy 空位可填 或 无 bench 角色可上;
- 装备无可穿(EquipAll/WearEquip no-op)。

**防死循环(分层)**:
- 动作级:每原子动作带完成验证(§4.1 验证列);fail → 计数;同动作 fail≥2 → 本回合屏蔽;
- 环级:连续 stall≥5 或总步数>60(可配)→ 强制 StartBattle([cw!] log 供诊断);
- 出战级:现 battle_prep 转移验证(6×0.5s 轮询 + retry)不动。

## 8. 迁移路径(原子优先,v2 修订)

| Phase | 内容 | 风险控制 |
|---|---|---|
| **P1 环 + 新域原子** | Director 环;**奖励域(ClickSpheres/OpenBox/PickBoxCard)+ 席位域(SellBench 身份感知/DeployMove 单步)+ StartBattle 全原子**;商店/装备域用组合动作(RunBuyPhase/RunEquip) | 新域一次做对(动机所在);旧 op 内部一行不动 |
| **P2 买牌原子化** | RunBuyPhase 拆为 plan() 单步动作 → 原子执行器;_handle_bench_full 退役(腾席已环级);两阶段 hack 自然淘汰 | 同 fixture 动作序列 diff 对照 P1 |
| **P3 部署/装备原子化** | RunEquip→WearEquip;DeployBench 内卖 off-target 上移为 SellBench 决策;BattlePrepCycle 退役 | 同上 |
| **P4(可选)装备角色级分配 / Synthesize / SwapBoard** | defer 项按需 | — |

每 Phase 独立 live 验证(`run_operation` 稳定 M=3),不并行。

## 9. 测试策略

- **决策单测**(表驱动):obs → action。必测:球+free>0→ClickSpheres(k=free);球+free=0+空位→DeployMove;
  球+free=0+可升→LevelUp;球+free=0+弱角色→SellBench;球+free=0+全核心→DeferSpheres;有箱→OpenBox 优先;
  出口全件→StartBattle;stall 屏蔽;
- **执行器单测**:每原子动作 mock controller + fixture 断言验证逻辑(球减/源空/金变);
- **Director fixture 测**:fixture 屏序列(现 reward_spheres_8/5/4 + box_open)→ 断言动作序列;
- **回归**:现有 op 测试不动;P3 前 BattlePrepCycle 保留可切回。

## 10. 开放问题(默认已选,可推翻)

| 问题 | 默认 | 备选 |
|---|---|---|
| 球收取粒度 | ClickSpheres(k=free) 带内验早停(决策一次,执行内逐球验证) | 纯单球(决策 n 次,观察多)/ 纯批(无内验,危险) |
| 球价值排序 | r 大优先(金>蓝>灰) | comp 需求感知(策略-stage) |
| LevelUp 粒度 | 语义动作(循环 BuyXP 至 level+1) | BuyXP 单点也进决策(噪声大,不取) |
| 卖角保留件 | 3合1 重复件不卖(目标核心同名 ≥2 张在凑) | 纯 _weakest_bench_idx(可能卖掉凑星件,不取) |
| WearEquip 目标选择 | P1-P3 槽位级(key_equips 优先);角色级分配 P4 | P1 就角色级(需 comp 角色定位数据,不就) |
| stall 预算 | 5 步 / 60 总步 | 实跑校准 |

## 11. 与既有文档关系

- [01 架构](01_architecture.md):本文把「op 层执行」细化为「决策环+原子执行器」,三层不动;
- [02 评估搜索](02_eval_search.md):plan()/evaluate() 复用,调用时机从批量变逐步;
- [04 状态对账](04_state_reconciliation.md):obs.state 即对账产物;
- 策略需求清单 §2:实现时补「备战步级决策(decide_prep_action)」行。

## 12. 实现落点(代码地图,P1)

```
src/sr_od/application/currency_war/
├── prep_director.py            # 新:PrepDirector(环)+ PrepObservation + PrepAction(原子全集)
├── cw_strategy.py              # +decide_prep_action(基类默认:v1 规则 = §5)
├── cw_decisions.py             # 复用:_should_deploy/_weakest_bench_idx/plan/LEVEL_UP_COST_TABLE
├── prep_actions.py             # 新:原子执行器(ClickSphere/OpenBox/PickBoxCard/SellBench/DeployMove/
│                               #     LevelUp/StartBattle,各带完成验证;从现有 op 抽单步)
└── operations/
    ├── prep/battle_prep.py     # P1 挂载点切 PrepDirector;P3 退役
    └── handlers/handle_reward_sphere.py  # P1 后退役(逻辑并入原子执行器)
```
