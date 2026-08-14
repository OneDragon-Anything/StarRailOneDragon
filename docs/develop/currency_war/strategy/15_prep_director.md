# 15 备战决策环(PrepDirector)—— 备战编排从固定序列到观察驱动

> 总见 [README](README.md)。本文:备战画面内「下一步做什么」的决策架构 —— 观察驱动单步决策环,
> 替代 BattlePrepCycle 固定序列。2026-08-14 用户定调(场景触发:奖励球 + 备战席满,现架构球要拖一轮才收)。
> ADR-0123 记录决策。

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
    action = strategy.decide_prep_action(obs,         # ② 决策:单步原子动作
                             session, config)
    if isinstance(action, StartBattle): break        #    环出口 = 出战
    progressed = execute(action)                     # ③ 执行器:动作 → 原语/子 op
    if not progressed: stall += 1                    # ④ 无进展防护(见 §6)
```

对照目标场景走一遍:`obs: 有球 + bench 9/9 + deployed 5/6(deploy 有空位)` →
`decision: DeployMove(最弱可上角色, 后排)` → 执行(强化板 + 腾 1 席)→ 再观察 →
`obs: 有球 + bench 8/9` → `decision: ClickSphere(最大球)` → 执行(球内容入账/可能又占席)→ 再观察 → … → 无球无正提升 → StartBattle。

## 3. 统一观察(PrepObservation)

决策的单一输入。**组合现成 reader,不新写识别**:

| 字段 | 来源(现成) | 轻/重 |
|---|---|---|
| state: GameState(gold/hp/level/phase/board/deployed/bench) | read_game_state(session tracking 合并,现成) | 重(阶段边界) |
| spheres: list[(color, center, r)] | read_reward_spheres(HoughCircles,快) | 轻(每步) |
| boxes: list[(slot, center)] | read_supply_boxes(TM,快) | 轻(每步) |
| owned_equips | read_equips(SIFT) | 重 |
| deploy_vacancy: int | read_deploy_cap - read_deployed_count | 轻 |
| shop_cards / shop_open | read_shop_cards / 锚点 | 重(买牌阶段) |

**成本控制(关键,防每步全量观察太慢)**:轻观察(CV 级:球 TM/Hough + 部署数 OCR)每步做;
重观察(SIFT 身份/shop 全读/read_game_state)只在**阶段边界**(进入买牌阶段前/部署前)或轻观察
检测到结构变化(球消失/部署数变)时刷新。执行器执行宏动作期间自己管观察(现有 op 内部逻辑不动)。

## 4. 动作空间(PrepAction)

**Phase1 用宏动作(整 op 当一步),Phase2+ 细化为原子动作**。与 `cw_state.Action` 的关系:
buy 域(买/卖/升/刷/移)复用现 dataclass;新增 sphere/box/equip/battle 域:

| 动作 | Phase | 执行器映射 | 语义 |
|---|---|---|---|
| OpenBoxes | P1 | HandleSupplyBox(op 整体) | 开掉所有箱(腾席+得装备) |
| CollectSpheres(n) | P1 | CollectRewardSpheres 调用(可限 1 球) | 收球,n=1 时单球观察驱动 |
| FreeBench(kind) | P1 | 腾席原语(kind 见 §5) | 为收球/买牌腾 1 席 |
| RunBuyPhase | P1 | BuyShopCards(op 整体) | 买牌阶段(内部 plan 两阶段,暂不动) |
| RunDeploy | P1 | DeployBench(op 整体) | 部署阶段 |
| RunEquip | P1 | EquipAll(op 整体) | 穿戴阶段 |
| DeferSpheres | P1 | no-op(标记) | 球留置(都有用不能卖),下轮再看 |
| StartBattle | P1 | 出战(现 battle_prep 逻辑) | 环出口 |
| (P2 原子化) ClickSphere/OpenBox/PickBoxCard/BuyCard/LevelUp/RefreshShop/SellBench/DeployMove/WearEquip | P2+ | 买牌内部化时启用 | 逐步重观察,顺带淘汰 shop.py 两阶段 hack(RefreshShop 后自然重读 shop) |

## 5. 腾席决策(核心规则,用户场景的答案)

触发:球/箱待收 但 bench 满(点不动);或买牌需要席位。优先级:

```
1. deploy 空位存在 且 有 bench 角色满足 _should_deploy(现成)
   → DeployMove(上排:强化板 + 腾席,零成本最优)
2. 否则 升级可扩容(level<10 且 gold≥LEVEL_UP_COST 且 level_plan 允许)
   → LevelUp(cap+1 → 产生 deploy 空位 → 回到 1)
3. 否则 有可卖角色(_weakest_bench_idx 非核心/非重复凑星)
   → SellBench(身份感知,替位置式卖 bench-1..3)
4. 否则 全是有用角色 → 不腾,DeferSpheres(球留着,继续买/穿/出战)
```

全部复用现成评估函数(`_should_deploy`/`_weakest_bench_idx`/`LEVEL_UP_COST_TABLE`/level_plan),
v1 规则只是把它们从 plan() 内部提到环级。

## 6. 环出口(出战条件)与防死循环

**出口(StartBattle)**,全部满足:
- 无球 或 球连续 Defer(留置判定,防反复尝试);
- 无箱;
- plan() 无正提升动作(现贪心终止条件,即买牌阶段自然结束);
- 无 deploy 空位可填 或 无可上角色;
- EquipAll no-op(无可穿)。

**防死循环(分层)**:
- 动作级:执行后 obs 关键计数不变(球数/金/等级/部署数/owned)→ 该动作计 fail;同动作 fail≥2 → 本回合屏蔽;
- 环级:连续 stall≥5 或总步数>60(预算,可配)→ 强制 StartBattle(保流程推进,记 [cw!] log 供诊断);
- 出战级:现 battle_prep 的转移验证(6×0.5s 轮询 + retry)不动。

## 7. 决策接口(CwStrategy 演进)

- 新方法 `decide_prep_action(obs, session, config) -> PrepAction`,**基类给默认实现**(规则版,委托 cw_decisions 既有函数),DefaultStrategy 可覆盖 —— 非 abstract,不破坏插件体系;
- `decide_prep`(批量 shop 计划)保留,P1 内部由 RunBuyPhase 经 BuyShopCards 间接使用,P2 拆掉;
- Director 本身是 **SrOperation**(单「决策环」节点 + 内部 while + round_retry 预算),在主循环中替换 BattlePrepCycle 的挂载点;
- 战略层 `update_target` 在环入口调一次(现语义:每备战回合一次)。

## 8. 迁移路径(不砸 live 验证过的链)

| Phase | 内容 | 风险控制 |
|---|---|---|
| **P1 外环替换** | PrepDirector + 宏动作;决策 v1=规则(箱→开;球→收[单球];席满阻球→FreeBench 一步;买;部署;穿;出战)。**收球-腾席闭环当轮完成** | 三个子 op 内部**一行不动**(live 验过);director 只编排 |
| **P2 买牌内部化** | RunBuyPhase 拆为 plan() 动作逐步执行;_handle_bench_full 退役(腾席已是环级决策);两阶段 hack 自然淘汰 | 对照 P1 双跑(同 fixture 动作序列 diff) |
| **P3 部署/装备内部化** | 同法细化;BattlePrepCycle 退役 | 同上 |

每 Phase 独立 live 验证(`run_operation` 稳定 M=3,项目阈值惯例),不并行推进。

## 9. 测试策略

- **决策单测**(表驱动,纯逻辑):obs → action。必测用例:球+满席+有空位→DeployMove;球+满席+全核心→DeferSpheres;球+满席+弱角色→SellBench;无球无提升→StartBattle;stall 屏蔽;
- **Director fixture 测**:mock controller + fixture 屏序列(现 reward_spheres_8/5/4 + box_open 已可用)→ 断言动作序列;
- **回归**:现有 op 测试全不动;BattlePrepCycle 在 P3 前保留可一键切回(配置开关或保留类)。

## 10. 开放问题(默认已选,可推翻)

| 问题 | 默认 | 备选 |
|---|---|---|
| 决策粒度 | P1 宏 / P2 原子 | 全宏(简单但无单球反馈)/ 全原子(慢) |
| 球价值评估 | 大球优先(r 排序,现 op 逻辑) | 策略层按 comp 需求评估(策略-stage) |
| stall 预算 | 5 步 / 60 总步 | 实跑校准 |
| 装备穿戴纳入环 | P3 | P1 就纳(EquipAll 已是 no-op 安全) |

## 11. 与既有文档关系

- [01 架构](01_architecture.md):本文把「op 层执行」细化为「决策环+执行器」,战术/战略/数据三层不动;
- [02 评估搜索](02_eval_search.md):plan()/evaluate() 复用,只是调用时机从「每回合批量」变为「环内逐步」;
- [04 状态对账](04_state_reconciliation.md):obs 的 state 即对账产物;
- 策略需求清单 §2 决策点表:新增「备战步级决策(decide_prep_action)」行(实现时补)。

## 12. 实现落点(代码地图,P1)

```
src/sr_od/application/currency_war/
├── prep_director.py            # 新:PrepDirector(op)+ PrepObservation + PrepAction
├── cw_strategy.py              # +decide_prep_action(默认实现:规则版)
├── cw_decisions.py             # 复用:_should_deploy/_weakest_bench_idx/plan
└── operations/
    ├── prep/battle_prep.py     # P1 挂载点切 PrepDirector;P3 退役
    └── handlers/handle_reward_sphere.py  # P1 后 CollectRewardSpheres 增加「收 1 球」参数化
```
