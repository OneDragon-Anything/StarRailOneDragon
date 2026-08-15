# 11 策略插件机制(Strategy Plugin)

> 总见 [README](README.md)。本文:把货币战争的「决策大脑」抽象成**可替换的 `CwStrategy`** + **自动发现机制(对标 app 插件)** + **每局会话状态 `StrategySession`**,服务两个目标:**① 用户自写策略、用自己的打法玩货币战争;② 社区策略比赛**。
>
> **why 见** [`decisions.md` D-34](../decisions/INDEX.md)。本文只讲 what(接口/结构/接线/交付路径)。
> 相关:[01 架构](01_architecture.md)(三层:数据→战术→战略,本机制把战术+战略层决策统一收口到一个可替换对象)、[02 eval+搜索](02_eval_search.md)、[05 数据接线](05_data_wiring.md)(GameState 单一真相源)、[06 实施阶段](06_phases.md)(replay harness 5.5 与本文比赛评分共用)。

---

## 11.0 目标与非目标

**目标**
- **单一替换切口**:一个 `CwStrategy` 对象 = 一整套局内打法(备战买牌/升等级/D 牌 + 全部事件节点 + target_comp 选择/转型 + boss 克制)。换对象 = 换打法,不动框架。
- **跨步状态有家**:策略可在一局内记住跨回合的东西(target_comp、连胜计数、「这轮攒金升 8」的意图……),不再用 `BuyShopCards._target_comp` 这种 class-attr hack。
- **可发现 + 可插拔**:第三方策略按约定丢一个文件/包就自动出现在 GUI 下拉里(对标现有 `ApplicationFactoryManager` 的 app 插件体验)。
- **可离线测 + 可复盘**:策略是纯逻辑(只吃 GameState、出 Action,不碰屏幕),可用 fixture unit 测,也能对录制的 telemetry 跑 replay(比赛评分 + 未来 ML side-door 共用)。
- **公平可比**:每局 `StrategySession.rng` 可种子化 → A/B 权重/策略可复现;OCR/时序非确定性是框架职责,不在策略控制面内。

**非目标(YAGNI)**
- **不沙箱、不做代码隔离**:策略与现有第三方 app 插件同威胁模型 —— **进程内全信任**(项目根 `plugins/` 已被 `ApplicationFactoryManager` 自动 import 并运行)。比赛应在受信任环境跑。本机制不引入新威胁面。
- **不在本机制内做跨局持久化学习**:`StrategySession` 是**每局内存态**,对局结束销毁。跨局采集走既有 telemetry(见 [10](10_battle_and_enemies.md) PerformanceTracker),不在这里造第二套。
- **不重写 OCR/op 执行层**:策略只决策,框架(数据层 + op 层)负责读屏、点击、对账。本文不动 [05](05_data_wiring.md) 的接线,只改「决策怎么被调用」。

---

## 11.1 设计原则(4 条)

1. **无状态策略 + 显式会话(`StrategySession`)** —— `CwStrategy` 实例**不持有可变的每局状态**;所有跨步状态放进 `StrategySession`,由框架在每局开始创建、传入每个钩子、局终销毁。收益:策略实例可反复 instantiate、可单元测(喂构造好的 state 即可)、无隐藏实例状态 → 不会跨局泄漏。⚠️ **真实对局仍单跑道串行跑**(`CurrencyWarRunLoop` 是 `SrOperation`,要真游戏在线);「批量评分」靠 §11.10 的 replay 回放,**不是**并行跑真实对局。
2. **ABC 抽象 + Default 具现(模板方法)** —— `CwStrategy` ABC 的钩子是**抽象的**(纯接口,ABC 自身**不含**内置逻辑);`DefaultCwStrategy(CwStrategy)` 是**内置全具现**(每个钩子 P1 委托既有模块函数、P2 把逻辑迁进自身),即 `STRATEGY_ID="default"` 的注册策略。自定义策略两条路:① 继承 `CwStrategy` **自己实现全部钩子**(完整自研打法);② 继承 `DefaultCwStrategy` **只覆盖关心的几个**(其余继承内置,低门槛、比赛友好)。⚠️ **本文 §11.3 各钩子的「默认实现」一律指 `DefaultCwStrategy` 的具现,非 ABC 自身**(ABC 钩子是 abstract)。
3. **复用既有契约** —— 输入用 [05](05_data_wiring.md) 的 `GameState`(OCR 填充、已类型化),输出用既有 `Action` union + `SupplyPick`/`EncounterPick`/`PickEvent`。**不另起炉灶造第二套类型**,降低迁移成本与漂移。
4. **发现机制对标 app 插件** —— `StrategyManager` 照搬 `ApplicationFactoryManager` 的「约定式文件扫描 + BUILTIN/THIRD_PARTY 双源 + 元数据 + 去重 + 热重载」,**但省掉 factory 间接层**(策略比应用简单:无 config/run_record 机制,`cls()` 即可实例化),复用 `one_dragon.utils.plugin_module_loader`。

---

## 11.2 组件总览

```
                      ┌─────────────────────────────────────────────┐
 配置(CurrencyWarConfig) │ strategy_id = "default"(或已发现的任意 id)    │
                      └──────────────────────────┬──────────────────┘
                                 StrategyManager.discover() 扫描发现
                                 BUILTIN(src/.../currency_war/strategies/)
                                 THIRD_PARTY(plugins/currency_war_strategies/)
                                                 │
                      ┌──────────────────────────▼──────────────────┐
                      │   CurrencyWarRunLoop(对局主循环 = 比赛的一局) │
                      │   match 开始:                                 │
                      │     strategy = StrategyManager.instantiate(id)│
                      │     session  = strategy.create_session(config)│ ← 每局新建
                      │     ctx.cw_match = CurrencyWarMatch(strategy,  │
                      │                                      session)   │ ← 挂 ctx,op 可读
                      │     strategy.on_match_start(state,session,cfg) │
                      └──────────────────────────┬──────────────────┘
                                 每个决策点(备战/事件/节点)框架 OCR 读真值
                                 → 调 strategy.<hook>(state, session, config, ...)
                                 ← 返回 Action[] / XxxPick(纯数据)
                                                 │
                      ┌──────────────────────────▼──────────────────┐
                      │  op 层执行(BuyShopCards/DeployBench/Handle*)  │
                      │  按 Action 点击/拖拽;战后 OCR 观测掉血/胜负    │
                      │  → strategy.on_round_end(state,session,obs)   │ ← 观测驱动
                      └──────────────────────────┬──────────────────┘
                                 match 结束:
                      │     strategy.on_match_end(session, outcome)   │
                      │     ctx.cw_match = None(清场,防跨局污染)       │
```

> 注:上图把「match 开始」4 步画在同一框示意;严格说前 3 步(实例化 / `create_session` / 挂 `ctx.cw_match`)在 `CurrencyWarRunLoop.__init__`(无截图),`on_match_start` 在 `loop()` 首次截图后调 —— 见 §11.7。

四个新组件:`CwStrategy`(ABC,大脑接口)、`StrategySession`(每局状态)、`StrategyManager`(发现)、`DefaultCwStrategy`(内置默认实现)。加 `CurrencyWarMatch`(运行时持有 strategy+session 的轻容器,挂 ctx)。

---

## 11.3 `CwStrategy` ABC(大脑接口)

> 放 `src/sr_od/application/currency_war/cw_strategy.py`。**纯逻辑**:所有钩子只吃 `GameState`/选项 + 出 `Action`/`Pick`,**绝不碰屏幕/`ctx.controller`**(读屏与点击是框架职责)。这样策略可离线测、可 replay。

### 11.3.1 元数据(类属性)

策略身份与展示信息**全部类属性**,扫描时读(无 `_const.py` sidecar —— 策略比应用简单,不需要单独元数据文件):

```python
class CwStrategy(ABC):
    STRATEGY_ID: str        # 唯一 id(如 "default"/"aggressive_rush"),去重键
    STRATEGY_NAME: str      # GUI 显示名(如 "内置默认策略")
    AUTHOR: str = ""        # 参赛者/作者
    VERSION: str = "0.1"    # 语义化版本
    DESCRIPTION: str = ""   # 一句话描述打法
    _abstract: bool = False  # 扫描器内部:True = 中间辅助 ABC,不注册(非展示元数据,见 §11.5)
```

`STRATEGY_ID` 重复 → `StrategyManager` 报错(对标 app 插件 `APP_ID` 唯一性)。

### 11.3.2 构造:无状态

```python
def __init__(self) -> None: ...
```

**无参**(或仅取不变常量)。不收 `ctx`、不收 `config` —— 策略跨局跨账号复用,配置**每次调用按参传入**。可变每局状态一律走 `session`。

### 11.3.3 生命周期钩子

| 钩子 | 何时调 | 默认实现 | 用途 |
|---|---|---|---|
| `create_session(self, config) -> StrategySession` | 每局开始(run loop) | 返回空白 `StrategySession`(rng 留默认;**由 run loop 按 `config.strategy_seed` 覆盖**,见 §11.7) | 策略可覆盖以注入自己的 session 子类 / 初始 memory |
| `on_match_start(self, state, session, config) -> None` | 每局开始 | no-op | 初始化跨步状态(如设初始 target意向) |
| `on_round_end(self, state, session, config, obs: RoundOutcome) -> None` | 每场战斗后 | `session.performance.record(obs)` | **观测驱动**:喂掉血/胜负 → session(策略可覆盖做自适应) |
| `on_match_end(self, session, config, outcome: MatchOutcome) -> None` | 每局结束 | no-op | 局终收尾(策略可学习/记日志;比赛评分钩子) |

### 11.3.4 决策钩子(逐个)

> 签名里的 `state: GameState` 由框架 OCR 填([05](05_data_wiring.md));`session: StrategySession` 持跨步状态;`config: CurrencyWarConfig` 持用户偏好。返回类型用既有 dataclass。

**① `update_target` —— 战略层:选/转型 target_comp(替代 `select_comp`+`maybe_pivot`+`_target_comp` class-attr)**

```python
def update_target(self, state: GameState, session: StrategySession,
                  config: CurrencyWarConfig) -> None
```

- 框架在每个备战回合 `decide_prep` **之前**调一次。实现**写 `session.target_comp`**(首轮选;其后按信号 pivot;无强信号保持)。
- **为什么不并进 `decide_prep`**:target 是战略层 + 跨回合稳定(只在 pivot 信号才切),且**别的钩子**(补给/遭遇/巨星)也要读 `session.target_comp`,这些钩子在备战回合**之间**触发 → target 必须独立住在 session 里、由独立钩子维护。
- 默认实现:首轮 `select_comp(state, make_score_context(state), config)`;其后 `maybe_pivot(...)`,无 pivot 则保持(等价现 shop.py 逻辑,但状态进 session)。

**② `decide_prep` —— 备战 shop 计划(买/升/D牌/deploy/卖)**

```python
def decide_prep(self, state: GameState, session: StrategySession,
                config: CurrencyWarConfig) -> list[Action]
```

- 返回动作序列(`BuyCard`/`LevelUp`/`RefreshShop`/`DeployMove`/`SellBench`)。读 `session.target_comp` 作战略导向、`session.rng` 作蒙特卡洛。
- 默认实现:调既有 `plan(state, config, config.faction_priority, rng=session.rng, target_comp=session.target_comp)`。
- **deploy 处理**:策略可 emit `DeployMove`(逐单位 deploy);但 v1 框架仍用 `DeployBench`(deploy-all,按等级封顶)兜底,**忽略逐单位 deploy**(= 现行为)。⚠️ **自定义策略注意**:你 emit 的 `DeployMove` 在 v1 会被**静默丢弃**(框架 deploy-all 覆盖)—— 别指望它生效,直到「框架尊重逐单位 deploy」落地(后续)。**本文不强制改 deploy 行为**,只把口子留好。

**③ `decide_invest` —— 投资策略/投资环境 3 选 1(替代 `decide_event`)**

```python
def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                  state: GameState, session: StrategySession,
                  config: CurrencyWarConfig) -> PickEvent
```

- `kind` 区分「投资策略」/「投资环境」。⚠️ **P1 两个 kind 走同一 `decide_event`**(行为等价);「分表」是 P2+ 议题,自定义策略**不应假设** kind 不同会带来不同行为(签名先开口子,但默认实现不分)。
- `options` = OCR 读到的卡名列表。
- 默认实现:调既有 `decide_event(options, config, state)`。

**④ `decide_supply` —— 补给选装备/出钻(替代 `decide_supply`,目前 TODO)**

```python
def decide_supply(self, options: list[SupplyOption], state: GameState,
                  session: StrategySession, config: CurrencyWarConfig,
                  refresh_used: bool = False) -> SupplyPick
```

- 默认实现:调既有 `cw_decisions.decide_supply(options, state, session.target_comp, config, refresh_used)`。
- ⚠️ **OCR 未就绪**:`read_supply_options` 今天不存在(D-20 把补给 OCR 推到阶段 5)。**P1 钩子存在 + 默认委托,但 `RunSupplyNode` 不 rewire**(维持今天盲点 (900,550));handler 接线随补给 OCR 一起落到阶段 5。

**⑤ `decide_encounter` —— 遭遇难度/词缀避开(替代 `decide_encounter`,目前 TODO)**

```python
def decide_encounter(self, options: list[EncounterOption], state: GameState,
                     session: StrategySession, config: CurrencyWarConfig,
                     refresh_used: bool = False) -> EncounterPick
```

- 默认实现:调既有 `cw_decisions.decide_encounter(options, state, session.target_comp, config, refresh_used)`。
- ⚠️ **D-39 修正 D-35**:遭遇节点**有** 3 难度选择 UI(遭遇其一/其二/其三 + 选择,2026-08-05 实跑再证实),`HandleEncounter` 已 re-activate(`battle_loop` 0c,lcs 0.9 检测)。但 handler 暂用**启发式默认选左卡(遭遇其一=最易)**,`decide_encounter` 钩子 + 选项 OCR(难度/词缀/奖励)接线留 refine(handler TODO)。钩子**不再 dormant**,caller 待接(读选项 → decide_encounter → 选难度)。

**⑥ `decide_megastar` —— 巨星选候选(新钩子,目前 handler 写死左候选)**

```python
def decide_megastar(self, options: list[MegastarOption], state: GameState,
                    session: StrategySession, config: CurrencyWarConfig) -> MegastarPick
```

- `MegastarOption(idx, char_id="")`(`char_id` = OCR/SIFT 读到的候选角色名,供匹配)、`MegastarPick(idx, reason="")`。**新 dataclass,放 `cw_decisions.py`**(与同类 `SupplyPick`/`EncounterPick` 并列;注:既有 Pick 分散 —— `PickEvent` 在 cw_state.py、Supply/Encounter 在 cw_decisions.py,本机制不强制归拢,新节点 Pick 跟 Supply/Encounter 走 cw_decisions.py)。
- 默认实现**委托既有 `cw_comps.select_megastar`**(三步:① `target.core_chars` 含该巨星 → 绑该角色;② 否则按 `target.mechanic_attributes` 经 `MEGASTAR_BY_ATTRIBUTE` 反查推荐;③ 无 → 首个),拿到**角色名**后:名在 `options` 的 `char_id` 中 → 该 idx;名不在 options 或返回 None(仅当候选为空)→ idx=0(等价现「左候选花火」行为)。`Comp.core_chars`/`mechanic_attributes` 定义见 [03](03_comp_planning.md)。
- ⚠️ **OCR 未就绪**:`read_megastar` 今天不存在。**P1 钩子存在 + 默认委托,但 `RunMegastarNode` 不 rewire**(候选 char_id 全为 `""` → 匹配恒失败 → 默认 idx=0 = 今天盲点左候选;rewire 无意义,等 OCR)。handler 接线随 OCR 落到阶段 5。

**⑦ `decide_partner` —— 选择伙伴(新钩子,目前 handler 写死 stage 立绘)**

```python
def decide_partner(self, options: list[PartnerOption], state: GameState,
                   session: StrategySession, config: CurrencyWarConfig) -> PartnerPick
```

- `PartnerOption(idx, char_id="")`、`PartnerPick(idx, reason="")`(**新 dataclass,放 `cw_decisions.py`**,同 ⑥)。
- 默认实现:优先 `config.character_build_around` / `session.target_comp.core_chars` 命中;否则 idx=0。⚠️ P1 不 rewire,handler 仍写死点 `STAGE_PORTRAIT(1048,299)`;「idx=0」是 OCR 接线后(P1.5+)的等价描述,非今天行为本身。
- ⚠️ **OCR 未就绪**:`read_partner` 今天不存在;`HandleSelectPartner` 现盲点 stage 立绘。**P1 钩子存在 + 默认委托,但 handler 不 rewire**(char_id 全 `""` → 默认 idx=0 = 今天盲点)。随 OCR 落到阶段 5。

**⑧ ~~`decide_boss_priority`~~ —— 已删(2026-08-12)**:boss 克制是 **comp-vs-boss 机制级**(走 `boss_fit`/`comp.countered_by_bosses` + task#73 机制建模),非阵营级。原「boss→降权阵营」是错模型 + 全代码库零调用死代码,已从 ABC + DefaultCwStrategy + cw_decisions 删除。boss 数据采完(bosses.md 20 boss 机制),真 boss counter = task#73 机制建模(comp 机械属性 vs boss 机制,策略-stage)。

> **钩子完备性**:以上 7 个决策钩子 + 3 个生命周期钩子(`on_match_start`/`on_round_end`/`on_match_end`)+ `create_session`(session factory,每局调一次、非决策点)= 覆盖 [01 §决策点×层归属](01_architecture.md) 表里**除『装备合成/分配』(❌待做,留作未来钩子 `decide_equip`,不在首版)外的全部局内决策**,并**新增** `decide_partner`(「选择伙伴」overlay —— 旧表未列此决策点)。
>
> ⚠️ **P1 调用就绪度**(决定哪些钩子 P1 真被框架调):只有 `update_target`/`decide_prep`(备战,OCR 全)+ `decide_invest`(投资,OCR 卡名已有)+ 生命周期骨架 **在 P1 被调**。`decide_supply`/`decide_megastar`/`decide_partner` 钩子在 ABC 里就位、默认委托,但 **P1 无 caller**(缺选项 OCR / 缺 dispatch),随阶段 5 OCR 落地才接;`decide_encounter` 按 D-35 dormant(遭遇=普通战斗无选项 UI)。**hook 全部在 P1 冻结**,caller 分批接 —— 别把「hook 存在」误读成「P1 就能跑」。

---

## 11.4 `StrategySession`(每局状态)

> 放 `src/sr_od/application/currency_war/cw_strategy.py`(**与 `CwStrategy`/`CurrencyWarMatch` 同模块**,不单列 `cw_session.py` —— 参赛者 import 路径统一,见 §11.14)。

```python
@dataclass
class StrategySession:
    """一局货币战争的跨步状态(框架每局新建,局终销毁;策略读写)。"""
    target_comp: Comp | None = None        # 战略层目标阵容(update_target 维护)
    rng: random.Random = field(default_factory=random.Random)  # 可种子化(公平/replay)
    performance: PerformanceTracker = field(default_factory=PerformanceTracker)  # 观测反馈
    memory: dict[str, Any] = field(default_factory=dict)       # 策略私有 scratch(见下方说明)
    # 进度镜像(跨步看趋势用;每回合框架刷新)
    plane: int = 1
    round_num: int = 1
```

> - **观测历史读 `session.performance.history`**(`PerformanceTracker` 内部的 `list[RoundOutcome]` 是 source of truth,`record(obs)` 写、`recent_hp_loss_trend`/`_qualifying` 读)。**不另设 `session.history`**(避免双源脱节)。
> - **`memory` 是 deliberate escape hatch**(策略私有 scratch,如连胜计数/「这轮攒金升 8」意图);核心领域实体(`Comp`/`RoundOutcome`/`MatchOutcome`)仍走正规类型,不塞进 memory(对齐 AGENTS.local.md 工程化原则)。
> - **导入**:`dict[str, Any]` 需 `from typing import Any`;`PerformanceTracker` **顶部 import**(`field(default_factory=PerformanceTracker)` 需类对象,**不能** `TYPE_CHECKING`);`Comp` 仅类型注解 → 可 `TYPE_CHECKING`。模块顶已有 `from __future__ import annotations`。

- **生命周期**:`CurrencyWarRunLoop.__init__` 经 `strategy.create_session(config)` 创建 → 挂 `ctx.cw_match.session` → 每个钩子收到的就是它 → `CurrencyWarRunLoop` 局终置 `ctx.cw_match = None`。
- **rng 种子**:框架按 `config.strategy_seed`(int|None)在 `create_session` 后覆盖 `session.rng`。`None` = 每局真随机(生产);固定 int = 调试复现。⚠️ **只能种子化策略内部随机**(默认策略蒙特卡洛 D 牌走 `session.rng`,替代现 `plan` 自建的 `random.Random()`);**游戏侧行局演化(商店刷什么牌、boss 是谁、掉多少血)是服务端决定,种子化不到**。且 `session.rng` 有状态、随 `plan` 调用次数推进 —— OCR 时序若让某回合多刷一次,种子相同也会偏移。故「同 seed 复现」**只对固定输入序列(replay)成立**,对真实对局脆弱(详 §11.9/§11.10)。
- **performance**:复用既有 [`PerformanceTracker`](../../src/sr_od/application/currency_war/cw_performance.py)(观测驱动核心,见 [10](10_battle_and_enemies.md));`on_round_end` 默认 `record(obs)`。

**`MatchOutcome`(局终结算,框架构造,传给 `on_match_end`)—— 新 dataclass,放 `cw_state.py`:**
```python
@dataclass
class MatchOutcome:
    won: bool = False        # 是否通关(3 位面全清)
    final_plane: int = 1     # 到达位面
    final_round: int = 1     # 位面内轮次
    final_hp: int = 0        # 终局小队 HP
```
⚠️ 由 run loop 在 `round_success('对局结束')` 前构造,**依赖结算屏 OCR**(读终局 HP/位面/轮次)—— 这是**游戏侧新接线**,今天未接(同 on_round_end,见 §11.7/§11.12)。

---

## 11.5 `StrategyManager`(发现,对标 `ApplicationFactoryManager`)

> 放 `src/sr_od/application/currency_war/cw_strategy_manager.py`。

**两个来源**(同 app 插件):
- `BUILTIN`:`src/sr_od/application/currency_war/strategies/`(内置策略放这,如 `default_strategy.py`)。
- `THIRD_PARTY`:项目根 `plugins/currency_war_strategies/<子目录>/`(参赛者放这;**不能直接放根**,须在子目录里 —— 同 app 插件规则)。

**约定**(比 app 插件更轻):
- 扫描目录下所有 `.py`(**无后缀过滤** —— 区别 app 插件的 `*_factory.py` rglob),找 `CwStrategy` 的子类(`__module__` 匹配本文件,排除导入的基类)。**一个文件只注册一个策略**:若同文件有中间辅助 ABC(如 `class RushBase(DefaultCwStrategy)`),须用类属性(如 `_abstract = True`)或命名约定排除,否则会和真策略一起被注册。
- **无 `_factory.py` / `_const.py` 配对**(策略无 config/run_record 机制,`cls()` 即可实例化)→ 元数据全部类属性(§11.3.1)。
- 实例化:`cls()`(无参);失败记入 `scan_failures` 并跳过(同 app 插件容错)。

**基建复用**:`one_dragon.utils.plugin_module_loader` 的 `resolve_module_name` / `ensure_sys_path` / `import_module_from_file`(THIRD_PARTY 加 `plugins/` 到 `sys.path` 让相对导入能用)+ 热重载(`reload_modules`)。

**去重 + 元信息**:`STRATEGY_ID` 唯一性强校验(重复报错,指明首注册位);`StrategyInfo(strategy_id, name, author, version, description, source, module_name, plugin_dir, file_path)` 列表供 GUI 下拉(`plugin_dir`/`file_path` 供 GUI 展示来源 + 调试定位;**借鉴** `PluginInfo`,但 `PluginInfo` 本身无 `file_path`,本设计新增)。

**接口**(构造签名对标 `ApplicationFactoryManager`):
```python
class StrategyManager:
    def __init__(self, ctx: SrContext,
                 plugin_dirs: list[tuple[Path, PluginSource]]): ...   # 同 ApplicationFactoryManager
    def discover(self, reload_modules: bool = False) -> list[StrategyInfo]
    def get_strategy_class(self, strategy_id: str) -> type[CwStrategy] | None
    def instantiate(self, strategy_id: str) -> CwStrategy        # 找不到 → 回退 DefaultCwStrategy
    @property
    def strategies(self) -> list[StrategyInfo]                   # GUI 下拉用
```
`plugin_dirs` 来源:在 **`SrContext`** 加属性 `currency_war_strategy_plugin_dirs`(`currency_war_*` 是 SR 业务,放 `SrContext` 不污染公共框架,符 AGENTS.md「星铁业务只在 sr_od/」;勿放 `OneDragonContext`),返回 `[(<repo>/src/sr_od/application/currency_war/strategies/, BUILTIN), (<repo>/plugins/currency_war_strategies/, THIRD_PARTY)]`。⚠️ **目录与 app 插件不同**(app 是 `sr_od/application` + `plugins/`,策略是 currency_war 子目录)、**扫描规则也不同**(无 `*_factory.py` 后缀);别照抄 `application_plugin_dirs` 的实现,只借其 `(dir, PluginSource)` 元组 + `is_dir()` 守卫(目录不存在返空)的形式。见 §11.13。

> 实现可直接仿照 [`ApplicationFactoryManager`](../../../src/one_dragon/base/operation/application/application_factory_manager.py) 的 `_scan_directory`/`_load_factory_from_file`/`_register_plugin_metadata`,把 `ApplicationFactory` 换成 `CwStrategy`、删掉 `_const` 配对校验即可。

---

## 11.6 `DefaultCwStrategy`(内置默认实现,分两阶段)

> 放 `src/sr_od/application/currency_war/strategies/default_strategy.py`。`STRATEGY_ID = "default"`,是 `config.strategy_id` 的默认值 → **不配置就是今天的打法**。

**阶段 1(Phase 1,薄封装委托 —— 零行为变化)**

每个钩子默认实现**直接调既有模块函数**,逻辑不动。

> ⚠️ **`update_target` 的 state 来源(M6,钉死「行为等价」)**:框架在调 `update_target` 前,必须像现 `shop.py:111-113` 那样读一份 state —— 即「shop 关闭帧读 hp 真值 → 覆盖到 `state.hp` → 开 shop 读 gold/board/shop」产出的 state(现 `plan` 前的 `_tgt_state` 就是它)。直接用 `read_game_state(self.screenshot())` 不覆盖 hp → target 决策的 hp 输入与今天不同 → `maybe_pivot` 的 hp_safe 信号误/漏触发 → **不是零行为变化**。接线时由框架负责产出这份 state 传入(策略不自己截图)。

```python
class DefaultCwStrategy(CwStrategy):
    STRATEGY_ID = "default"
    STRATEGY_NAME = "内置默认策略"
    DESCRIPTION = "阶段键控 eval + 硬门贪心 + 蒙特卡洛 D 牌 + 阵容规划(见 02/03)"

    def update_target(self, state, session, config):
        score_ctx = make_score_context(state)   # ScoreContext,非 SrContext(重命名避免与 self.ctx 混淆)
        if session.target_comp is None:
            cands = select_comp(state, score_ctx, config)
            session.target_comp = cands[0] if cands else None
        else:
            # tracker=session.performance:maybe_pivot 目前不读 tracker(信号3 走 state.hp;tracker 是声明未用的占位,与其 docstring「待接」一致)→ 传不传都不影响行为;tracker 驱动的保命观测是 P1.5 工作
            piv = maybe_pivot(state, score_ctx, config, session.target_comp, tracker=session.performance)
            if piv is not None:
                session.target_comp = piv

    def decide_prep(self, state, session, config):
        return plan(state, config, config.faction_priority,
                    rng=session.rng, target_comp=session.target_comp)
    # decide_invest → decide_event;decide_supply/encounter → 既有同名;...
```

**阶段 2(Phase 2,地道重构 —— 内部改写,接口冻结)**

把 `cw_decisions` + `cw_comps` 的逻辑**迁移成 `DefaultCwStrategy` 的方法**,权重表(`CATEGORY_WEIGHT`/`INTEREST_WEIGHT`/`LEVEL_UP_COST_TABLE`/…)变为类常量,删掉模块级函数。**接口在阶段 1 已冻结**,阶段 2 是纯内部重构 + 测试须保持绿。这是「成本不计、做到最好」的终点态;阶段 1 先把口子做实不阻塞它。

---

## 11.7 接线改动(框架如何调用)

> 这步把「直接调模块函数」改成「走当前激活的 strategy 对象」,并干掉 `_target_comp` class-attr hack。**核心是行为等价**(默认策略 = 今天打法)。

**运行时持有(`CurrencyWarMatch`)**

轻容器,挂 `ctx`(子 op 都拿得到 `self.ctx`):
```python
@dataclass
class CurrencyWarMatch:
    strategy: CwStrategy
    session: StrategySession
```
- `SrContext.__init__` **显式声明** `self.cw_match: CurrencyWarMatch | None = None`,并在 `reload_instance_config` 里重置(同 `pos_info`/`team_info`/`sim_uni_info` 模式)。**不要动态 setattr**(会破坏类型检查/mypy)。
- 子 op 读:`match = self.ctx.cw_match; match.strategy.decide_prep(state, match.session, config)`。
- **替代设计(备查)**:把 match 沿 op 链路传参(类比 ctx);但 `BuyShopCards`/各 handler 都要改构造签名,成本高于挂 ctx。现择「挂 ctx + 严格生命周期(局终置 None)」—— 与现 `reset_phase_round_cache()`/telemetry run_id 同侧语义。

**`CurrencyWarRunLoop.__init__`(每局开始)** —— ⚠️ `__init__` 时 `SrOperation` 还没有 `last_screenshot`(截图由 node runner 在进 `@operation_node` 时提供),**不能在此 `read_game_state`**。故拆两步:

```python
# __init__ 里(无截图,只建会话):
config = CurrencyWarConfig(self.ctx.current_instance_idx)
strategy = StrategyManager(self.ctx, self.ctx.currency_war_strategy_plugin_dirs).instantiate(config.strategy_id)
session = strategy.create_session(config)
if config.strategy_seed is not None:
    session.rng = random.Random(config.strategy_seed)
self.ctx.cw_match = CurrencyWarMatch(strategy, session)
# 删掉:BuyShopCards._target_comp = None(状态进 session)+ battle_loop.py:67 同行重置
```
```python
# loop() 节点顶部,用 _iter 守卫只调一次(node runner 进节点前已设 last_screenshot):
if self._iter == 1:
    strategy.on_match_start(read_game_state(self.ctx, self.last_screenshot), session, config)
```
（实现者也可改成独立 `@operation_node def _start` 在 `loop` 之前,二选一。）**P1 `on_match_start` 的 state 是尽力而为的普通 `read_game_state`**(默认实现 no-op;自定义策略只作信息读取,**不**做 hp 覆盖 —— hp 覆盖是 `update_target` 的事,见 §11.6)。

**局终**(`round_success('对局结束')` 前):P1 用默认构造的桩 `strategy.on_match_end(session, MatchOutcome())`(`MatchOutcome` 字段全默认;默认方法 no-op);**真实 outcome 填充(结算屏 OCR)属 P1.5**。随后 `self.ctx.cw_match = None`(防跨局污染,替代现 `reset_phase_round_cache()` 同侧语义)。

**`BuyShopCards.buy`(shop.py)**
- 删掉 `select_comp`/`maybe_pivot`/`BuyShopCards._target_comp` 整段(§shop.py:108-120)。
- 改为:
  ```python
  match = self.ctx.cw_match
  match.strategy.update_target(state, match.session, config)   # 写 session.target_comp
  actions = match.strategy.decide_prep(state, match.session, config)
  ```
- `_target_comp` class-attr 彻底删;target 名从 `match.session.target_comp` 取(日志/telemetry)。

**各 handler(事件节点)** —— ⚠️ **P1 只 rewire 今天有 OCR 的 handler**(`decide_invest`);其余钩子在 ABC 里就位 + 默认委托,但 **handler 不动**(OCR 缺 / dispatch 已删),随阶段 5 OCR 落地再接(见 §11.3.4 各钩子 ⚠️ + §11.12)。

- **P1 rewire** —— `HandleInvestStrategy`/`HandleInvestEnv`:`decide_event(names, config, stub)` → `match.strategy.decide_invest(kind, names, state, match.session, config)`。⚠️ 投资 overlay 叠在备战上时 **board 不可读**,`state.board` **传空 dict(stub)**(不取 session 旁路 —— `StrategySession` 无 last_board 字段);默认 `decide_invest` 对空 board 降级容错(现 `decide_event` 只用 board 判 DoT 克制,空 board = 不惩罚,安全)。
- **P1 不 rewire(钩子在、默认委托、handler 维持今天盲点,随阶段 5 OCR 落地)** —— `RunSupplyNode`(补给 OCR 缺)、`RunMegastarNode`/`HandleSelectPartner`(候选 char_id OCR 缺 → 默认 idx=0 = 今天盲点)、`boss counter`(boss_fit/countered_by_bosses;decide_boss_priority 已删错模型)。`RunMegastarNode`/`HandleSelectPartner` 的 bug#1 `mouse_move`+`click` 缓解是**执行层**,与策略层无关,rewire 与否都保留。
- **D-35 后 dead(不 rewire、待删)** —— `HandleEncounter`(遭遇无选项 UI;`decide_encounter` dormant)。

**观测驱动回路** —— ⚠️ **今天未接线**:`battle_loop.py` 现在既不构造 `RoundOutcome`、也不调 `PerformanceTracker.record`(`cw_observation.py` 自注「PerformanceTracker 待阶段 4-5 接线」)。也就是说「每场战斗后 OCR 掉血/胜负」是**从无到有的新 OCR 工作**,不是改个调用名。

- **P1 期间这两个钩子不被调用**(框架不构造 `RoundOutcome`/真实 `MatchOutcome` → 没东西可喂)。注意:默认实现**本身**是 `session.performance.record(obs)`(§11.3.3,非空),只是 **P1 没人调它** → `performance` 保持空。区别「默认方法体 = record」与「P1 是否被调用 = 否」。
- **真正的接线**是独立工作项(§11.12 标「需游戏」):在每场战斗结算处新增 OCR(读 HP 差分、判 killed、判 node_type)→ 构造 `RoundOutcome` → `match.strategy.on_round_end(...)`;终局构造 `MatchOutcome` → `on_match_end(...)`。接位点需实机确认「每场战斗后是否有独立结算屏」(现 run loop 是「点击空白加速 → 继续挑战」,未见独立结算屏,属阶段 4 探查)。
- 这是 [10](10_battle_and_enemies.md) PerformanceTracker 的输入源;本机制只把「谁来喂」标准化成钩子,不承担 OCR 接线本身。

---

## 11.8 配置 + GUI

**`CurrencyWarConfig` 加字段**:
```python
self.strategy_id: str = self.get('strategy_id', 'default')
self.strategy_seed: int | None = self.get('strategy_seed', None)  # None=真随机;int=A/B 复现
```
`save()` 同步写。

**GUI**:备战/策略设置页加两个 setting card:
- 「策略」下拉:选项 = `StrategyManager.strategies`(`STRATEGY_NAME` + `(AUTHOR)`),值 = `STRATEGY_ID`。
- 「随机种子(调试/复现)」数字框(空 = 随机)。
- 用既有 `YamlConfigAdapter` / `AdapterInitMixin` 模式(AGENTS.md §架构落点)。

---

## 11.9 比赛支持

| 维度 | 做法 |
|---|---|
| **发布** | 参赛者按 §11.5 把 `CwStrategy` 子类丢 `plugins/currency_war_strategies/<我的策略>/` → 自动进 GUI 下拉(同 app 插件体例) |
| **公平/复现** | `strategy_seed` 只种子化**策略内部随机**(默认策略蒙特卡洛 D 牌);**游戏侧行局演化(发牌/boss/掉血)不可种子化**。同 seed ≠ 同序列局复现(真实对局);rng 有状态、随 plan 调用次数推进,时序偏移即失复现。真正可复现的只有**固定输入序列的 replay**(§11.10) |
| **评分** | 既有 telemetry(决策迹 + 结算)记录每局;`on_match_end(outcome)` 是评分钩子。**真实胜率 A/B 必须阶段 6 实机大样本**(换策略 → 行为变 → 游戏演化路径变 → obs 序列变);replay `batch_score` 只比「面对**同一 obs 序列**的**决策差异**」,不是换策略后的真实胜率(详 §11.10 局限) |
| **隔离/威胁模型** | **进程内全信任**,与第三方 app 插件同(`plugins/` 已自动 import 执行)。**不沙箱**;比赛在受信任环境跑。诚实记录,不假装安全 |
| **低门槛** | 模板方法默认实现 → 参赛者继承 `DefaultCwStrategy` 只覆盖 1-2 个钩子即可参赛 |

---

## 11.10 测试

**离线 unit(每个钩子纯函数)**
- 给定 `(GameState fixture, StrategySession, config)` → 断言返回的 `Action[]`/`Pick`。
- 默认策略:复用 `cw_decisions`/`cw_comps`/`cw_performance` 现有全部测试(P1 行为等价 → 这些测试应原样绿,不写死具体数免漂)。
- 加:session 生命周期测试(每局新建/局终销毁/rng 种子可复现)、`StrategyManager` 发现+去重+THIRD_PARTY 加载测试(用临时目录构造假插件)。

**Replay / 比赛评分 harness(与 [06](06_phases.md) 阶段 5.5 共用)**
- `replay(strategy, trace)` —— 把录制的 telemetry(`decisions.jsonl` + 结算)回放给某策略,断言决策或统计结局。
- `batch_score(strategy_ids, n_matches, seed)` —— 对每个策略跑 N 局(固定 seed 序列),汇总胜率/到关/HP → 排行榜。这是**比赛裁判** + 未来 ML side-door 的同一通道。
- ⚠️ **replay 评测的局限(off-policy / 分布偏移)**:obs 序列是**当时跑的策略**产生的;直接拿来评**别的**策略会失真(换策略 → 行为变 → 游戏演化路径变 → obs 序列本就不同)。故 replay 只能比「面对同一 obs 序列的决策差异」,**不能**测出换策略后的真实胜率 —— 那必须阶段 6 实机 A/B(单跑道串行,大样本)。replay 的真实价值是**回归测试**(策略改版后面对历史局面决策是否退化)+ 调试,不是最终胜率裁判。
- 放 `src/sr_od/application/currency_war/cw_strategy_test_harness.py`(逻辑层,不需游戏)。

---

## 11.11 向后兼容

- `config.strategy_id` 默认 `"default"` → **行为与今天完全一致**(阶段 1 默认策略委托未改动的模块函数)。
- `_target_comp` class-attr hack 删除 → 状态进 `session.target_comp`,语义等价(每局重置已是现行为)。
- 现有 `cw_decisions`/`cw_comps` 模块函数在阶段 1 **保留**(默认策略 + 旧测试仍直接调);阶段 2 才删。

---

## 11.12 实施阶段(交付路径)

> **P1 已落地(2026-08-05,D-36)** ✅ + **P1.5 观测回路已落地(2026-08-06,D-48~52)** ✅:接口+接线 + on_round_end 观测回路(结算屏→read_round_outcome→performance.record 记 hp trend)+ 失败屏 hp=0 conf=1.0(D-51)+ node_type 推断「首领」→boss(D-52)。实机验证(DOT队 plane1 r1-9 记 hp 62→0)。
>
> **弱阵 + 事件长尾修(2026-08-06,D-54~60)**:① **D-58** env 接线 bug(已选投资环境从不存 `state.active_env` → `env_fit`/T0 硬绑静默失效)→ StrategySession 加 `active_env` + HandleInvestEnv 写 + update_target copy;② **D-59** 弱阵:maybe_pivot 信号1 阈值随 best vs target 成型难度调节(best 易 + target 未成型 → ×0.7,倾向易成型 comp,慢 comp 拖死);③ **D-54/57/60** 事件 flat-loop(消耗品 modal / app _in_match 大厅误判 / choose_partner 硬编码坐标落间隙)。**待新局全验**(env 绑定 + 易 comp pivot + choose_partner)。**next**:据新局结果迭代弱阵(commitment/roll-for-target:target 过粘时 plan 该 roll 找 target 阵营不买 off-target 散牌)+ P2 comp_viability 观测 blend。

| 阶段 | 内容 | 游戏? | 风险 |
|---|---|---|---|
| **P1 接口 + 接线(零行为变化)** ✅ | `CwStrategy` ABC + `StrategySession` + `CurrencyWarMatch` + `StrategyManager` + `DefaultCwStrategy`(薄委托)+ config 字段 + 干掉 `_target_comp` hack + 离线 unit。**P1 只 rewire 有 OCR 的**:`shop.py`(prep)+ `handle_invest_*`(invest)+ 生命周期骨架(`on_match_start` 尽力而为 / `on_match_end` 桩 / `on_round_end` 不调)。supply/megastar/partner/boss 钩子在 ABC 就位但 **handler 不动**(OCR 缺 / dispatch 已删,随阶段 5);encounter dormant(D-35) | 否 | 低(默认逻辑不动) |
| **P1.5 观测回路接线** ✅ | 每场战斗结算 OCR → `RoundOutcome` → `on_round_end`(D-48);失败屏 hp=0 conf=1.0(D-51)+ node_type 推断(D-52)。终局 `MatchOutcome` 仍 P1 桩(真实 outcome 填充待) | 已接 | 中(结算屏形态已确认:挑战结束/挑战失败/继续挑战) |
| **P2 地道化** | `cw_decisions`+`cw_comps` 逻辑迁进 `DefaultCwStrategy` 方法,删模块函数,权重转类常量 | 否 | 中(动已测战术层,测试须保绿) |
| **P3 比赛基建** | replay harness + batch_score + 第三方策略骨架示例 + 参赛者文档 | 否(评分逻辑)/ 是(录 trace) | 低 |

P1 先落地 → 插件口子立刻可用(用户/参赛者可写策略);P2 是内部质量;P3 是比赛运营。**接口在 P1 冻结**,P2/P3 不破坏它。

---

## 11.13 文件清单

**新增**
- `src/sr_od/application/currency_war/cw_strategy.py`(`CwStrategy` ABC + `StrategySession` + `CurrencyWarMatch`,同模块;参赛者 import 路径统一)
- `src/sr_od/application/currency_war/cw_strategy_manager.py`(`StrategyManager` + `StrategyInfo`)
- `src/sr_od/application/currency_war/strategies/default_strategy.py`(`DefaultCwStrategy`)
- `src/sr_od/application/currency_war/strategies/__init__.py`
- `src/sr_od/application/currency_war/cw_strategy_test_harness.py`(replay + batch_score,P3)
- `sr-od-test/` 新增 strategy manager/session/default strategy 测试

**改动(P1 本阶段交付)**
- `currency_war_config.py`(+`strategy_id`/`strategy_seed` + save)
- `operations/battle_loop.py`(run loop 建/毁 match + `on_match_start`(`loop()` 顶部 `if self._iter==1` 守卫)/ `on_match_end`(P1 桩 `MatchOutcome()`);**删两处:① `BuyShopCards._target_comp` class attr(shop.py)② battle_loop.py:67 每局重置行**(状态进 session)。`on_round_end` 喂观测属 P1.5,不在 P1)
- `operations/prep/shop.py`(走 `strategy.update_target` + `decide_prep`;`state` 由框架产(shop 关闭帧 hp 覆盖,见 §11.6 M6);删 `_target_comp` class attr)
- `operations/handlers/handle_invest_strategy.py` / `handle_invest_env.py`(→ decide_invest;board 传空 stub)
- `src/sr_od/application/currency_war/cw_decisions.py`(+ `MegastarOption`/`MegastarPick`/`PartnerOption`/`PartnerPick` —— ABC 钩子签名需要,**P1 就定义**,即便暂无 caller)
- `src/sr_od/application/currency_war/cw_state.py`(+ `MatchOutcome` —— `on_match_end` P1 桩需要)
- `src/sr_od/context/sr_context.py`(+ `cw_match: CurrencyWarMatch | None` 显式声明 + `reload_instance_config` 重置(同 `pos_info`,不要动态 setattr)+ `currency_war_strategy_plugin_dirs` 属性)
- GUI 设置页(+ 策略下拉 + 种子框)

**后续阶段改动(非 P1,随 OCR / 观测回路落地)**
- `operations/run_nodes/run_supply_node.py`(→ decide_supply,随补给 OCR,阶段 5)
- `operations/run_nodes/run_megastar_node.py`(→ decide_megastar,随候选 char_id OCR)
- `operations/handlers/handle_select_partner.py`(→ decide_partner,随 char_id OCR)
- boss OCR 接入点(→ state.bosses → boss_fit/countered_by_bosses;decide_boss_priority 已删)
- 观测回路 ✅(P1.5,D-48~52):每场战斗结算 OCR → `RoundOutcome` → `on_round_end`(performance.record 记 hp trend);终局 `MatchOutcome` 仍桩(待真实 outcome 填充)

**删除 dead handler**(全代码库仅注释 + 残留 `.pyc`,无实际 import)
- `operations/handlers/handle_megastar.py`(D-31 后被 `RunMegastarNode` 替代)
- `operations/handlers/handle_encounter.py`(D-35 后遭遇无选项 UI;`decide_encounter` 纯逻辑 + 测试**暂留** dormant)
- `operations/handlers/handle_supply.py`(D-29 后被 `RunSupplyNode` 替代)

---

## 11.14 示例:第三方策略骨架(参赛者照此写)

```python
# plugins/currency_war_strategies/rush_level_demo/rush_level.py
from sr_od.application.currency_war.cw_strategy import CwStrategy, StrategySession
from sr_od.application.currency_war.strategies.default_strategy import DefaultCwStrategy

class RushLevelStrategy(DefaultCwStrategy):
    """只覆盖备战:更激进升等级(抢高费刷新率),其余照内置。"""
    STRATEGY_ID = "rush_level_demo"
    STRATEGY_NAME = "演示·猛冲等级"
    AUTHOR = "社区参赛者"
    VERSION = "0.1"
    DESCRIPTION = "比默认更早升等级、少囤息。仅演示插件机制。"

    def decide_prep(self, state, session, config):
        # 复用默认 plan,但把 target 偏向高费(自定义逻辑)
        actions = super().decide_prep(state, session, config)
        # ... 自定义调整 ...
        return actions
```

丢进 `plugins/currency_war_strategies/rush_level_demo/` → GUI 下拉自动出现「演示·猛冲等级」。**无需改框架代码、无需注册**。
