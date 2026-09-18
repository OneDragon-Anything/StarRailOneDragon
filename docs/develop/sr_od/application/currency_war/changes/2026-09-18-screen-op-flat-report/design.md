# 2026-09-18-screen-op-flat-report 迭代设计（总纲）

## 0. 元信息

- 迭代目标：货币战争画面 op 层架构收敛——废弃画面 op 基类，每个画面 op 独立成类直继承 `SrOperation`，统一「观察 node → 决策动作 node」两段形态；每个画面一个观察结果类 `CwScreenXxxObs`；`GameState` 提供每画面独立上报接口 `report_xxx(obs)` 承载该画面观察数据的落容器逻辑。（依据：用户裁定，2026-09-18 设计确认会话，共五轮修正收敛——基类废弃/多 node/round_wait 循环/无防御上限/动作上报模型修正与范围收缩。）
- 状态：定稿（设计对抗以用户五轮逐项裁定代行：①基类废弃+独立类+obs 类+report 接口；②多 node 拆分+对账段去除；③循环 round_wait+on_outcome 退役；④无防御上限；⑤刷新计数出辖——动作 op 侧另会话改动，用户转达协调。）
- 文档清单：无详设（单文档方案，本文件即完整设计；分屏契约总表见 §2.6）。

## 1. 问题与动机

- 现状症状：
  - 画面 op 层存在两级基类 `cw_screen_op_base.py::CwScreenOpBase`（五段生命周期 run_lifecycle + on_outcome 登记注册表 + 观察/动作适配器端口位）与 `_progression_base.py::CwProgressionScreenOp`（推进型空决策基类）；37 个 op 类挂在基类上（§2.6 总表）。
  - 每个 op 的 handle()/run() 顶部有装配点分流：`cw_game_ports` 两端口完整在场（仅测试装配）→ 五段生命周期路径；缺省 None → 生产直连旧路径。生产恒走旧路径，五段路径仅测试仓 obs_arch 测试族驱动（依据：`cw_game_ports.py` 缺省 `(None, None)`；生产零 `install_game_ports` 调用点；grep 实证 sim/ 引擎零消费端口）。
  - op 对 game state 的观察数据写点散落在 op 内部各处（如 `cw_screen_encounter.py::_decide_encounter_action` 内写 `gs.encounter` 槽；`cw_screen_megastar.py::_do_action` 内写 `gs.megastar_opts`），摄入职责错放在 op 层。
  - 刷新次数记账双源：观察侧 OCR「剩余次数:N」只作访问内局部值，bot 侧自记计数（`gs.encounter_refresh_used` 经 on_outcome 注册表在画面 op 内 +1）与观察真值并行。
- 根因归层：**架构/约定层**——「统一观察架构」试点（基类 + 五段生命周期 + 适配器端口 + 装配点分派）的机制复杂度与收益不匹配，双路径并存期未收敛；观察数据摄入职责错放在 op 层而非 game state。
- 解决到哪：基类与生命周期/端口/登记表机制退役；单路径两 node 形态；观察数据落容器收归 `GameState.report_xxx`；测试与正本文档同步。
- 明确不解决（防范围外溢）：
  - **刷新次数记账全域**（`encounter_refresh_used`/`strategy_refresh_used` 的写端模型、「观察上报 + 动作上报 → game state 扣减」改造）——动作 op 侧由另一会话改动中，用户负责转达协调（用户裁定⑤）；本迭代画面 op 侧只做：on_outcome 钩子随基类退役（计数写端在画面 op 内的现存机制消失，缺口由动作 op 会话承接），`refresh_left` 观察 read 侧与门读 `gs` 字段原样保留，**不新建也不改造计数通道**；
  - **动作 op 侧一切改动**（`cw_op/` 动作执行体、`ActionOp` 契约、`apply_*_action_logic` 逻辑态族）——另会话辖域，本迭代不触碰；
  - `CwScreenDeploy`（1829 行，已直继承 `SrOperation`）的 obs 化——单独立批评估（用户裁定 #4）；
  - 观察漏斗 `obs/cw_observation.py::read_game_state` 内部结构与其容器写端（既有观察边界，§2.3）；
  - kernel 内部实现面（星级抖动门 `cw_reconcile.py`、缺陷台账）——game state 内部，op 无感；
  - 策略判据面（买/卖/升/刷数学）零触碰。

## 2. 方案

### 2.1 画面 op 形态（两 node 骨架）

```python
@dataclass
class CwScreenXxxObs:
    ...  # 该画面观察结果（字段 = 现役 XxxObservation 逐位平移，见 §2.2）

class CwScreenXxx(SrOperation):
    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        # 入口门（画面锚/标识判定；不命中 = round_fail 交回外循环重判，语义 = 现役首发锚 miss）
        # 读屏 → CwScreenXxxObs
        # gs.report_xxx(obs)   # 观察数据落容器（§2.3）
        # obs 挂实例属性；round_success 进决策动作 node
        ...

    @operation_node(name='决策动作')
    def act(self) -> OperationRoundResult:
        # 决策 → 动作；循环推进 = round_wait（不烧 node 重试预算）
        # 终结动作/重入裁决（锚不在 = 动作已落地）= round_success 交回外循环
        # 策略异常/执行异常 = round_fail（错误传播，非防御上限）
        ...
```

- **循环语义（用户裁定）**：正常迭代一律 `round_wait`；node 重试预算不再承担循环计数。循环唯一出口 = 终结动作、重入裁决成功、异常 fail。**不设防御上限**——决策循环不收敛 = 策略实现 bug，响亮暴露（不收敛场景挂起可观测，修策略根因，不加兜底帽）。（依据：用户裁定「循环用 round_wait」「不设防御上限，有问题就是策略实现的问题」；恒可用终结不变量 = screens/op-layer.md §1.4 已在册——每个决策画面动作空间至少含一个恒可用终结动作，正确策略必收敛。）
- **重入裁决留在 act node 顶部**（pending 语义屏：确认发出后下一轮迭代查锚，锚不在 = 落地 → 补记录 → success）。它是循环出口判定，属动作落地 adjudication，不回观察 node。（依据：现役 `cw_screen_encounter.py::handle` 顶部重入裁决语义逐位平移。）
- **读屏点唯一化**：显式读屏（`op.screenshot()`）只在观察 node；act node 迭代用 node runner 进 node 时给的 `last_screenshot`（round_wait 每轮新帧，与现役 handle retry 每轮新截同语义）。（依据：`cw_loop.py:933` 注释「截图由 node runner 进 @operation_node 时给」；现役 handle retry 机制同源。）
- **节点预算**：观察 node 小预算（门 fail 交回，无循环）；act node 保留现役 node_max_retry_times 值（round_wait 不计数后预算近惰性，仅框架异常路径消费），不新建上限机制。
- **推进型空决策屏同构两 node**：观察 node = 锚判定（hit → success 进 act；miss+未推进 = fail 交回）；act node = 单次推进 + 重入裁决（现役 `_progression_base.py::handle` 语义逐位内联，12 屏各持一份，不设共享基类/共享骨架函数——用户裁定每 op 独立类，模式一致即重复）。

### 2.2 观察结果类 `CwScreenXxxObs`

- **住址**：`kernel/cw_screen_report/<screen>.py`——**每画面一文件,obs 类与该画面 `report_screen_*_obs` 函数同居**(用户裁定⑦:一律直接每画面一个文件,推进型也不例外,避免后续再拆;与动作侧 `kernel/cw_action_report/<action>.py` 每动作一文件对称)。文件名 = 画面 snake;`__init__.py` 不暴露模块(项目惯例)。obs 类字段 = 现役 `XxxObservation` 逐位平移(帧引用字段保留),推进型屏 obs = 入口裁决 `{on_screen: bool, screen}`。kernel 纯数据:obs 类只可 import kernel 既有类型 + `cv2.typing.MatLike`。
- **命名映射**：现役 `XxxObservation`（散住各 op 文件）→ `CwScreenXxxObs`，字段逐位平移不改语义；帧引用字段（`screen: Any`）保留（实机识别域载体，与现役一致）。
- **读时机保真（用户裁定 #2）**：迁移不增加读屏。懒读语义保留（典型 = `CwScreenMegastar`：确认访问不重读候选，obs.options 仅在「本访问将选择」时填充，字段注释写明门槛条件）；单发 overlay 屏升级为「入口观察一次读 → report 写槽 → 决策只消费 obs/game state」（读写同帧等价，即 screens/op-layer.md §1.1 既有目标形态）。
- **推进型屏 obs**：每屏仍建 `CwScreenXxxObs`（记录入口裁决结果，如 `on_screen: bool`），**不设 report 接口**（空决策形态无对账面/无容器域，依据：ADR-0584 空决策合同 + 用户裁定 #6）。

### 2.3 `report_screen_*_obs` 上报接口族

- **形状**：`kernel/cw_screen_report/<screen>.py` 模块级函数，一画面一函数(与 obs 类同居，§2.2):`def report_screen_<snake>_obs(gs: GameState, obs: CwScreenXxxObs, *, sig: ChannelSig | None = None) -> None`。**与动作上报函数族 `report_action_*_param` 同约定**(用户裁定六:一个「上报」概念一个形状)——命名机械规约同构(obs 类 `CwScreenXxxObs` 去前缀 `CwScreen` 去后缀 `Obs` 转 snake);完备锁测试遍历包内 obs 类断言函数在场/推进型不在场;两族(动作/画面观察)互不混用,都禁按类型聚合的分派转移函数。sig 缺省 = 函数体内构造签名,**actor/ family/evidence 逐位沿用该画面现役写点原值**(如 actor='CwScreenEncounter')——REGISTERED_ACTORS 零扩面,**cw_game_state.py 本迭代零改动**(用户裁定⑦配套;并行会话在飞该文件,零触碰即零冲突),journal 写行语义与现役逐位连续。
- **辖域边界（硬规则）**：屏文件 = **该画面观察进容器的全部逻辑的家**——①写点转录；②**该屏更新逻辑**（写点之上的屏级门/派生/优先级，如幂等门/懒写/双写 baseline）；③**该屏对账逻辑**（类型化 obs 载荷之上的观察 vs 逻辑态特判，纯函数可随迁移批从 obs 桶逐步迁入，如商店池一致性核对）。判断线 = **只在类型化载荷上运算 → 进屏文件；要摸帧 → 留在观察侧**（识别机制不出端口，kernel 零像素纪律不破；依赖读帧的审计链留守 op 观察段）。kernel→obs 直依仍被分包矩阵禁止——迁入的对账纯函数以 obs 桶函数体「搬进」kernel 屏文件的方式落地，不是 import（依据：flow/README §2.3 分包矩阵）。
- **漏斗边界**：`read_game_state` 漏斗内部的容器写端 = 既有观察边界，不动（用户裁定 #3）；prep/买牌的 report 函数只收编 op 层散落写点（接管补采写点 `takeover_*`/`plane_bosses`/`enemy_affixes`、`node_path` 写点、结算观察写点等，逐屏清单见 §2.6；重型屏辖域细化随 T-5 迁移批落地，landing 带注）。
- **动作事实边界（硬规则）**：chosen_*（选择落地记录）留守画面 op 的重入裁决点——其值在「确认已落地」重入观察后才可信，记账随判定点走（用户裁定会话确认）。刷新计数**不适用**此边界（§2.4 出辖）。
- 对账段不复存在：基类 `lifecycle_reconcile` 随基类退役；prep/买牌的观察审计消费 = 观察处理（留守 observe node），非独立对账段（用户裁定「对账我理解是已经没有了的」）。

### 2.4 刷新次数记账——出辖申报（用户裁定⑤）

- **全域出辖**：刷新计数（`encounter_refresh_used`/`strategy_refresh_used`）的写端模型改造与「动作上报 → game state 扣减」均归动作 op 会话（用户转达协调），本迭代不设计、不落地、不预留接口。
- 本迭代画面 op 侧的机械事实与处置：
  - on_outcome 登记注册表（在册两件刷新计数钩子）随基类退役，**画面 op 内的计数写端消失**（`cw_screen_encounter.py::_on_refresh_emitted`/`cw_screen_invest_strategy.py` 同构件不转录、不替代）——缺口由动作 op 会话承接，本迭代接受该过渡态（用户裁定「不需要关注」）；
  - `refresh_left` 观察 read（OCR「剩余次数:N」）原样保留为 obs 字段 + 门读 `gs` 字段原样保留（读端语义零改动）；
  - 不新建计数通道、不动 gs 计数字段定义。

### 2.5 退役面（迁移完成后删除）

| 退役件 | 位置 | 前置 |
|---|---|---|
| `CwScreenOpBase` 五段生命周期/注册表/端口位 | `operations/cw_screen/cw_screen_op_base.py` 整文件 | 全部 op 迁移完成 |
| `CwProgressionScreenOp` | `operations/cw_screen/_progression_base.py` 整文件 | 12 推进型屏内联完成 |
| 端口机制（协议 + 安装槽 + install/uninstall） | `cw_game_ports.py` 整文件 | op 分流删净 + 买牌波循环两处端口消费改直连 + 测试改桩 |
| 决策帧假环境留证分支 | `operations/decision_frame_hooks.py::save_decision_frame` 的 `observation_source()` 分支 | 端口退役 |
| 段迹机制 `_lifecycle_trace` / `_lifecycle_mark` | 随基类删除 | obs_arch 测试断言同步改写 |
| 适配器类 `XxxLiveObservationAdapter` / `PrepLiveActionAdapter` | 各 op 文件内 | 对应 op 迁移完成 |
| 旧观察类名 `XxxObservation` | 各 op 文件内（平移入 kernel 后删除） | 对应 op 迁移完成 |

- 退役判据（用户裁定 #5）：op 分流删净后 `cw_game_ports` 生产消费面为零、测试消费面改桩 `_observe` 注入 obs——整机制退役，不留零消费死代码。

### 2.6 分屏契约总表（37 类）

（「report 接口」列为短名，全称按 §2.3 机械规约 = `report_screen_<短名>_obs`；「无」= 不设 report。）

形态列：**全** = 全形态（观察 node + 决策动作 node + report）；**环** = 节点循环 overlay（两 node，act 为单动作节点循环）；**推** = 推进型空决策（两 node 内联，无 report）；**重** = 重型屏（漏斗边界按 §2.3）。

| op 类 | 形态 | obs 类 | report 接口 | 迁移要点（写点收编清单） |
|---|---|---|---|---|
| CwScreenEncounter | 全 | CwScreenEncounterObs | report_encounter | `gs.encounter` 写槽×2 收编；refresh_left 留 obs 字段（§2.4 出辖）；`encounter_refreshed_in_visit` 置位留守决策面；chosen_encounter 留守重入裁决点 |
| CwScreenMegastar | 环 | CwScreenMegastarObs | report_megastar | `megastar_opts` 写槽收编（懒读保真）；chosen_megastar 留守选择点 |
| CwScreenEquipPick | 环 | CwScreenEquipPickObs | report_equip_pick | equip 选项写点收编；chosen 留守 |
| CwScreenPartner | 环 | CwScreenPartnerObs | report_partner | 同构 |
| CwScreenPlanner | 环 | CwScreenPlannerObs | report_planner | 同构 |
| CwScreenFortune | 环 | CwScreenFortuneObs | report_fortune | 同构 |
| CwScreenWishTrial | 环 | CwScreenWishTrialObs | report_wish_trial | 同构 |
| CwScreenBookcard | 环 | CwScreenBookcardObs | report_bookcard | 同构 |
| CwScreenExpertInvite | 环 | CwScreenExpertInviteObs | report_expert_invite | 同构 |
| CwScreenSupplyNode | 全 | CwScreenSupplyNodeObs | report_supply | 选项写槽收编（刷新面按 §2.4 出辖） |
| CwScreenInvestStrategy | 全 | CwScreenInvestStrategyObs | report_invest_strategy | 逐卡选项写点收编；strategy_refresh_used 写端按 §2.4 出辖（钩子随基类退役不转录） |
| CwScreenInvestEnv | 全 | CwScreenInvestEnvObs | report_invest_env | 投资环境选项写点收编 |
| CwScreenArmoryBox | 环 | CwScreenArmoryBoxObs | report_armory_box | 武装箱选项写点收编 |
| CwScreenBriefing | 全 | CwScreenBriefingObs | report_briefing | 词缀/首领写点收编 |
| CwScreenBossBriefing | 全 | CwScreenBossBriefingObs | report_boss_briefing | boss 写点收编 |
| CwScreenWaitOneOne | 全 | CwScreenWaitOneOneObs | report_wait_one_one | 观察写点收编（实施时按现役写点定） |
| CwScreenDeployNotFull | 全 | CwScreenDeployNotFullObs | report_deploy_not_full | 同构 |
| CwScreenPlaneTransition | 全 | CwScreenPlaneTransitionObs | report_plane_transition | `node_path`/`node_path_baseline` 写点收编 |
| CwScreenPlaneIntel | 重 | CwScreenPlaneIntelObs | report_plane_intel | 采集产物写点收编；关闭回写段按 §2.3 边界拆分 |
| CwScreenBattleWait | 重 | CwScreenBattleWaitObs | report_battle_wait | 结算观察单一写点（`_write_settlement_observation`）收编 |
| CwScreenPrep | 重 | CwScreenPrepObs | report_prep | op 层写点收编（`takeover_tries`/`takeover_collect_done`/`plane_bosses`/`enemy_affixes`/`node_path`×2）；漏斗内部不动；审计链留守 observe node |
| CwScreenBuyCards | 重 | CwScreenBuyCardsObs | report_buy_cards | 入口收据为 obs；op 层观察写点收编；两处端口消费（波循环入口观察/动作口）改直连现役链 |
| CwOpOpenShop | 推 | CwOpOpenShopObs | 无 | 推进型内联（只读/导航变体） |
| CwOpCloseShop | 推 | CwOpCloseShopObs | 无 | 同上 |
| CwScreenBoxPick | 全 | CwScreenBoxPickObs | report_box_pick | 已直继承；补 obs + report（`write_logic` 写点收编） |
| 12 推进型屏：NextButton / PlaneDetail / ConsumableOverlay / EmblemDetailPopup / ItemDetailPopup / InterruptDialog / RefreshOddsPopup / RoleDetailOverlay / ShopCardDetailPopup / PrepLockedReturn / AhaEquipPick | 推 | CwScreenXxxObs（入口裁决） | 无 | 骨架内联（§2.1 末条） |

（表中「同构」= 与族内先例屏逐位同构迁移；实施时以先例屏 diff 为模板。）

### 2.7 依赖与装配不变量

- 依赖方向不变：operations → kernel 单向；kernel 零像素触达；`kernel/cw_screen_obs.py` 只依赖 kernel 既有类型（`cw_events`/`cw_vocab`/`cv2.typing`）。
- `report_xxx` 对 `obs` 字段缺失的防御口径与现役写点一致（如 match/gs 缺席 = 跳过写，桩面安全），逐点平移不加强不减弱。
- 商店框 op（OpenShop/CloseShop）与 `cw_flow_const.py`/`_overlay_confirm.py` 共享 helper 不在退役面。

### 2.8 测试策略

- obs_arch 测试族（`test_cw_obs_arch_event_screens.py` / `_closing_screens.py` / `_event_screens_step3.py` / `_phase_screens.py`）随对应族迁移批改写：删端口装配与段迹断言，改桩 `op._observe`（或观察 node 的读屏函数注入点）直接注入 obs 驱动单路径；容器写入断言改经 report 接口路径。
- `test_cw_game_ports`（端口协议守卫）随端口退役删除；`_cw_helpers.py` 的 `install_dispatch_stub_ports`/`uninstall_ports` 删除，消费方改直接驱动。
- 收口锁变更：现役「凡 op 祖链达 SrOperation 者必为 CwScreenOpBase 后代」AST 断言随基类退役删除，改为「cw_screen/ 顶层 op 类必直继承 SrOperation」的形状锁（防基类回潮）。
- 行为锁语义保留：各屏在册行为锁的断言面（点击序列/容器终值/round 语义）不变，仅驱动方式与断言载体随新形态调整。
- 每迁移批验证 = ruff（改动文件）+ 该族测试 + `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`（L1 ≈2.5min，收口跑）；收口批跑全量 L3。

### 2.9 关键取舍

- **两 node 而非单 handle**（用户裁定 vs 单节点内聚）：多 node 使观察/决策两段结构显形，框架 node 序先例充分（`cw_entry_exit` 14 节点）；代价 = obs 经实例属性跨 node 传递 + 节点预算重排，收益 = 与用户目标形态一致。
- **round_wait 循环 + 无上限**（用户裁定 vs round_retry 预算循环/防御帽）：正常迭代非失败不应烧重试预算；不收敛 = 策略 bug 响亮暴露，不加兜底。风险（内部死循环挂起）接受为显式权衡，依赖恒可用终结不变量兜住正确策略面。
- **report 收编纯数据写点、审计链留守**（vs 审计链全量入 kernel）：kernel→obs 直依被分包矩阵禁止；全量迁审计链入 kernel 是独立大改，超出本迭代边界（§1 明确不解决）。
- **重写 op-layer.md 正本而非增量修补**：基类机制章（§2/§4）退役后正本结构大变，重写成本低于逐节修补失真风险。
