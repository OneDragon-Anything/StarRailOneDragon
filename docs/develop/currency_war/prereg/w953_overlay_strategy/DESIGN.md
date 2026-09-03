# W953 · overlay 选择类决策接入策略层：全量盘点 + 接口架构设计

> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期预登记设计记录,类名保持当时事实,未改)。

> 任务来源：用户指令「所有的选择都应该接入策略层……策略基类应该给每个 overlay 留一个实现接口,现在有做到吗?」
> 本文纯盘点 + 设计，未动任何代码。证据均为表达式级（文件:行 + 代码原文摘录）。

---

## 一、全量盘点总表（overlay 选择类处理器 × 接入状态）

判级：
- **已接入** = handler 把候选面喂 `match.strategy.decide_*`（策略层可感知局面），决策逻辑在 decision_v2 策略对象内；
- **部分接入** = 存在策略层实现但活路径没走到 / 只覆盖一半语义；
- **未接入** = 选择逻辑硬编码在 handler（kernel 函数直调 / 内联打分 / 固定值）。

| # | 处理器（文件） | overlay / 选择对象 | 当前选卡逻辑所在层 | 接入状态 | 表达式级证据 |
|---|---|---|---|---|---|
| 1 | HandleInvestEnv（`operations/handlers/handle_invest_env.py`） | 投资环境 3 选 1 | 策略层（decision_v2） | **已接入** | L126 `pick = match.strategy.decide_invest('env', names, match.session.last_state or GameState(), match.session, config)` |
| 2 | HandleInvestStrategy（`handlers/handle_invest_strategy.py`） | 投资策略 3 选 1 | 策略层 | **已接入** | L376 `pick = match.strategy.decide_invest('strategy', names, …)` |
| 3 | HandleSupplyBox（`handlers/handle_supply_box.py`） | 武装箱装备 4 选 1 | 策略层（`DecisionV2Strategy.decide_box_card`），handler 保留旧内联回落 | **已接入***（*但有 ABC 缺口，见 §二） | `pick_box_card` L~55 `idx = match.strategy.decide_box_card(names, _st, match.session, …)`；except 分支回落内联 `key_equips`→`material_value`（L~66-70） |
| 4 | HandleEncounter（`handlers/handle_encounter.py`） | 遭遇难度二选一 | 策略层 | **已接入** | L~80 `pick = match.strategy.decide_encounter(options, _state, match.session, _cfg)` |
| 5 | HandleSelectPartner（`handlers/handle_select_partner.py`） | 选择伙伴（step1 候选） | 策略层 | **已接入** | L805 `pick = match.strategy.decide_partner(options, _state, match.session, _cfg)` |
| 6 | RunMegastarNode（`run_nodes/run_megastar_node.py`） | 巨星候选选择 | 策略层 | **已接入** | `_do_action` 内 `pick = match.strategy.decide_megastar(options, _state, match.session, _cfg)` |
| 7 | RunSupplyNode（`run_nodes/run_supply_node.py`） | 补给 N 选 1 + 刷新 | 策略层 | **已接入** | `pick = match.strategy.decide_supply([o for o, _ in opts], _state, match.session, _cfg, refresh_used=_refresh_used)` |
| 8 | battle_loop `_handle_star_tome_pick`（`operations/battle_loop.py:342`） | 星徽秘典四选一 | 策略层（`DecisionV2Strategy.decide_star_tome`），但调用点在 loop 内联而非独立 handler | **已接入***（*ABC 缺口同 #3；调用点位置待批迁移） | L365 `idx = _match.strategy.decide_star_tome([c[0] for c in cards], _st, _match.session, _cfg)` |
| 9 | **HandlePlannerEvent**（`handlers/handle_planner_event.py`） | 银狼「我来当策划」二选一 | **kernel 固定偏好**（`cw_events.decide_planner`：升费基础分 100 压倒） | **未接入**（策略对象实现存在但活路径没走） | L563 `pick = decide_planner(options, _st or GameState(), _tgt)`，import 自 `kernel/cw_events`——**没有经过 `match.strategy`**。`DecisionV2Strategy.decide_planner`（decision_v2/strategy.py:600）存在但本 handler 从不调用 → 类 docstring 自证：「decide_planner 现固定升费优先(滚动投资),未接决策层局面感知」 |
| 10 | HandleWishTrial（`handlers/handle_wish_trial.py`） | 祈愿试炼 objective 选卡 | 策略层（`DecisionV2Strategy.decide_wish_trial`） | **已接入***（*ABC 缺口；except 回落第 1 张） | `idx = _match.strategy.decide_wish_trial(objs, _st, _match.session, …)`，`except Exception … fallback 第1张` |
| 11 | **HandleEquipPick**（`handlers/handle_equip_pick.py`） | 选择装备三选一 | **handler 内联打分** | **未接入** | 内联循环 `for ke in key_equips: if ke and ke in t: s += 100.0` + `('伤害','强度','提高')` 文本规则（handle 函数体）；全文件无 `decide_` 调用、无 strategy 引用 |
| 12 | **HandleFortunePicker**（`handlers/handle_fortune_picker.py`） | 命运卜者强化三选一 | **handler 内联关键词打分** | **未接入** | 内联 `for kw, w in (('伤害倍率',3.0),('强度提高',2.0),('层数提高',2.0),('伤害',1.0),('提高',0.5)): if kw in t: s += w`；reason 自证 `f'text_rule(best_score={best_s})'` |
| 13 | **HandleBookcard.choose**（`handlers/handle_bookcard.py`） | 专家邀请函 5 选 1（4 角色 + 现金为王） | **handler 模块级纯函数**（`choose_expert_index`：主力阵营→在场阵营→现金为王） | **未接入** | `idx = choose_expert_index(card_bonds, board)`；该函数是 handler 文件内定义的固定判据，无 strategy/session/config 入参 |
| 14 | HandleSelectPartner step2（同 #5 文件） | 盛会之星「强化角色」目标 | **硬编码中心立绘** | **未接入**（意向已产、执行面缺） | `target = Point(960, 300)` 写死；姊妹证据：run_megastar_node docstring「强化角色=决策意向已接(`registry.megastar_enhance_enabled` 默认关→`MegastarPick.enhance_char_id`)，执行面未接(候选坐标未建档)」 |
| 15 | CollectRewardSpheres（`handlers/handle_reward_sphere.py`） | 奖励球收取顺序 | handler 启发式（大球优先） | **非策略选择**（收取顺序非卡选；登记备查） | `max(spheres, key=lambda t: t[2])`（按半径） |
| 16 | HandleDeployNotFull / HandleArmoryBoxDialog / HandleBriefing | 固定单动作弹窗（勾选+确认 / 点×关闭 / 读数+下一步） | — | **无选择语义**（不属本议题，登记完备性） | handle_deploy_not_full 固定勾「本局不再提示」+确认；handle_armory_box 点×关闭 |

### 完备性交叉核对

- `operations/handlers/` 实有 16 个业务文件（除 `_overlay_confirm.py` 工具、`__init__.py`）：collect_plane_intel（情报采集，无选择）、handle_armory_box、handle_bookcard、handle_briefing、handle_deploy_not_full、handle_encounter、handle_equip_pick、handle_fortune_picker、handle_invest_env、handle_invest_strategy、handle_planner_event、handle_reward_sphere、handle_select_partner、handle_supply_box、handle_wish_trial——**逐个均已入表**（#1-16）。
- `operations/run_nodes/` 3 个：run_node（基类）、run_megastar_node（#6）、run_supply_node（#7）——均已入表。
- overlay 分支派发源 `battle_loop.py` 分支清单已扫（0b 巨星 / equip_pick / select_partner / planner / fortune / star_tome / supply / wish_trial / encounter / invest / bookcard / armory / deploy_not_full）——与表一致，无第 17 个选择面。

---

## 二、策略基类接口现状：per-overlay 钩子有没有留全？

**结论：没有做到「每个 overlay 一个接口」。** 现状分三层：

### 2.1 `CwStrategy` ABC（`decision/cw_strategy.py:57`）——只有 5 个 overlay 钩子

ABC 全部 abstract 钩子清单（L104-158）：`update_target` / `decide_prep` / `decide_prep_action` / `decide_invest` / `decide_supply` / `decide_encounter` / `decide_megastar` / `decide_partner`（+ 3 生命周期 + create_session）。

**overlay 选择里缺了 4 个**：策划事件（planner）、星徽秘典（star_tome）、祈愿试炼（wish_trial）、武装箱（box_card）。

### 2.2 后 4 个的实现长在具体策略类上，调用点鸭子类型直调

`DecisionV2Strategy`（`decision/decision_v2/strategy.py`）在 ABC 之外追加了 4 个**具体方法**：`decide_planner`(L600) / `decide_star_tome`(L608) / `decide_wish_trial`(L647) / `decide_box_card`(L685)。调用点（handle_supply_box / handle_wish_trial / battle_loop:365）直接 `match.strategy.decide_xxx(...)`：

- 违反插件契约：`cw_strategy.py` 模块 docstring 明言「换对象 = 换打法，不动框架」「自定义策略：继承 CwStrategy 实现全部钩子」——但一个只实现 ABC 的第三方策略在遇到这 4 个 overlay 时直接 `AttributeError`（wish_trial/box_card 有 try/except 吞掉回落第 1 张；**star_tome 的 except 回落是盲点卡1 并点击**）；
- 违反「handler 不写死」的验收口径：回落值（第 1 张/卡1）重新变回 handler 内固定偏好。

### 2.3 连策略对象都没碰的 3 个面（#9 例外 + #11/#12/#13）

- **#9 策划事件**：`DecisionV2Strategy.decide_planner` 已实现且非平凡（银狼线/在场判定），但活 handler 走 `kernel/cw_events.decide_planner` 直调——**策略对象的局面感知版本是死码**。这是「部分接入」里最接近已完成的一件：只差 handler 改一行调用点。
- **#11 装备三选一 / #12 命运卜者 / #13 专家邀请函**：策略层**不存在任何对应实现**（decision_v2/strategy.py 与 kernel/cw_events.py 均无 decide_equip_pick / decide_fortune / decide_expert），选择逻辑 100% 在 handler。

### 2.4 附带发现（接入面之外的语义债）

- `decide_supply`/`decide_encounter` 的 ABC 与实现签名都带 `refresh_used`，但 refresh 决策（刷不刷）在 supply 上由策略返回 `SupplyPick.refresh` 消费，encounter 上 ABC 默认 `refresh_used=False` 形参在 handler 调用点根本没传——接口语义两钩子不对齐。
- sim 侧（`sim/engine_p1.py`）直用 kernel `decide_supply` 纯函数，live 走 `DecisionV2Strategy.decide_supply` 再委托同一 kernel 函数——目前同源，但若策略对象将来覆盖 `decide_supply`，sim 与 live 将静默分叉（迁移批须带 sim 对拍）。

---

## 三、架构设计：策略基类 per-overlay 实现接口

### 3.1 设计原则（对齐 decision_v2 既有形态，不另起炉灶）

沿用三个既有模式，不发明新机制：

1. **「handler 出快照 → 策略出 Pick」的既有钩子形态**：输入=局面快照（`GameState`（通常 `session.last_state`）+ 候选面 OCR 结构）+ `StrategySession` + `config`，输出=带 `idx` 与 `reason` 的 Pick dataclass——与 `EncounterOption/EncounterPick`、`PartnerOption/PartnerPick` 同构（kernel/cw_events.py L209-542 已是模板）。
2. **ABC 纯接口 + 具现类委托 kernel 纯函数**：与 `decide_supply`（ABC abstract → `DecisionV2Strategy` 委托 `cw_events.decide_supply`）完全同形；sim 可继续直用 kernel 纯函数，策略对象可自由覆盖。
3. **局面感知复用 decision_v2 既有资产**：新钩子的打分优先消费 `session.target_comp`（intention 消费模式，见 `decide_invest` 的 target 命中加分、`decide_star_tome` 的 target_factions/board/framework 三源打分）、`state.board`、`session.commit_signals`——不新增感知通道。

### 3.2 接口定义（新增 7 个 ABC 钩子）

在 `CwStrategy` 增加（全部 abstract，与既有 8 决策钩子并列）：

```python
# ===== overlay 决策钩子(补全;既有 5 个之外) =====

@abstractmethod
def decide_planner(self, options: list[PlannerOption], state: GameState,
                   session: StrategySession, config) -> PlannerPick:
    """银狼「我来当策划」二选一。options=左右卡 OCR 文本。"""

@abstractmethod
def decide_star_tome(self, options: list[str], state: GameState,
                     session: StrategySession, config) -> int:
    """星徽秘典四选一。options=去「星徽」后缀的阵营名;返回索引。"""

@abstractmethod
def decide_wish_trial(self, options: list[str | None], state: GameState,
                      session: StrategySession, config) -> int:
    """祈愿试炼选卡。options=各卡 objective 文字(None=OCR 空)。"""

@abstractmethod
def decide_box_card(self, names: list[str], state: GameState,
                    session: StrategySession, config) -> int:
    """武装箱/邀请函类装备卡 N 选 1。返回索引; -1 无约定(禁,默认 0)。"""

@abstractmethod
def decide_equip_pick(self, names: list[str], state: GameState,
                      session: StrategySession, config) -> int:
    """「选择装备」三选一(节点弹层)。options=卡名带 OCR 文本。"""

@abstractmethod
def decide_fortune_pick(self, options: list[str], state: GameState,
                        session: StrategySession, config) -> int:
    """命运卜者系强化效果 N 选一。options=卡文字聚合。"""

@abstractmethod
def decide_expert_invite(self, bonds: list[str | None], board: dict[str, int],
                         state: GameState, session: StrategySession,
                         config) -> int:
    """专家邀请函 5 选 1。bonds=各卡解析羁绊(None=未解析);返回 -1=现金为王。"""
```

要点：

- **`decide_planner` 的返回类型已存在**（`PlannerPick`，cw_events.py L484），ABC 收编后 `DecisionV2Strategy.decide_planner` 现有实现原地升级为具现，零新逻辑。
- **`decide_expert_invite` 的输入对齐 #13 既有解析产物**（`bonds`/`board` 已由 handler 解析），策略只做选择——观察与决策继续分离（策略「绝不碰屏幕」的模块红线，cw_strategy.py docstring）。
- 返回 `int` 还是 Pick 对象？既有钩子两种都有（`decide_star_tome`/`decide_wish_trial`/`decide_box_card` 返回 int；`decide_planner` 返回 Pick）。**新钩子取「缺 reason 面就 int、有遥测归因需求就 Pick」**：为统一遥测归因（`record_event_choice` 的 reason 字段），建议新增 4 个（equip_pick/fortune_pick/expert_invite + 补 planner 外的三个 int 钩子暂不破坏）保持现状，仅新三件直接定义 Pick（`EquipPickPick`/`FortunePick`/`ExpertInvitePick`：`idx` + `reason`），存量三件在批 2 统一升 Pick 时再改签名（带 config 开关双跑）。

### 3.3 默认实现策略

不做「ABC 带 默认实现」（ABC 现行纪律 = 全 abstract 纯接口，`cw_strategy.py` L64「本 ABC 的钩子全 abstract」）。默认实现按既有惯例放两处：

1. **kernel 纯函数**（可被 sim 与策略对象共用）：
   - `decide_planner` → 已有 `cw_events.decide_planner`（原地收编）；
   - `decide_box_card` → 现居 `DecisionV2Strategy.decide_box_card` 内联体，下沉为 `cw_events.decide_box_card`（依赖 `cw_prep_expect.material_value` + `cw_equipment_data`，均 kernel/data 桶，无分包违规）；
   - `decide_equip_pick`/`decide_fortune_pick` → 把 handler 内联关键词表下沉 `cw_events`（打分权重进注册表常量，值不写散）；
   - `decide_expert_invite` → `handle_bookcard.choose_expert_index` 整体平移 `cw_events`（纯函数、已有单测锁行为，平移不改语义）。
2. **`DecisionV2Strategy` 具现 = 薄委托 + decision_v2 增强**：委托 kernel 纯函数打底，再按局面加成（模式同 `decide_invest`：kernel 分 + `session.target_comp` 命中加成 + `commit_signals` 喂入）。

### 3.4 处理器 → 策略层的调用规约（写进 handler 模板）

统一为现有 5 个已接入钩子的成熟模式，四条硬规约：

1. **唯一入口**：handler 只允许 `pick = match.strategy.decide_<overlay>(snapshot…)`；禁再出现 `from …cw_events import decide_xxx` 直调（#9 违例形态，批 1 修）。
2. **局面快照口径**：一律 `state = match.session.last_state or GameState()`（overlay 下 board 不可读，用上次备战快照；ADR-0144 语义），禁 new 空 stub（#9 现传 `_st or GameState()` 合规，批内统一注释）。
3. **无 match 防御路径显式声明**：局外独立跑（match is None）才允许直调 kernel 纯函数作防御回落，注释标明「防御:无 match」——沿用 handle_invest_env 现行写法，禁止第三种路径。
4. **策略异常回落必须经策略层**：try/except 的 fallback 不写死「第 1 张」，改为调 kernel 纯函数（= 策略的默认实现），并 `record_event_choice(reason='strategy_error_fallback')`——把「策略崩了」变成可归因遥测而非静默盲点。

### 3.5 存量硬编码迁移路径（分批）

| 批 | 面 | 内容 | 开关/风险判定 | 验证 |
|---|---|---|---|---|
| **批 1（接线修正，1 件）** | #9 策划事件 | `handle_planner_event.py` L563 改调 `match.strategy.decide_planner`（实现已存在）；`decide_planner` 上 ABC（abstract） | 零行为变化：`DecisionV2Strategy.decide_planner` 本就委托同一 kernel 函数（L606 `return cw_events.decide_planner(options, state, session.target_comp)`），活路径只是绕远 | L1 快速集 + 现有 planner 单测；行为对拍：同输入 kernel vs 策略对象输出相等（sim 一批可证） |
| **批 2（ABC 收编 4 钩子，签名冻结）** | #3/#8/#10 + ABC | `decide_box_card`/`decide_star_tome`/`decide_wish_trial` 上 ABC abstract；实现体从 `DecisionV2Strategy` 下沉 kernel 纯函数 + 具现改薄委托；三处调用点 try/except 回落改走 kernel 纯函数（规约 4） | 中风险：三处调用点行为路径重构（虽语义等价）；第三方自定义策略从此必须实现 4 钩子——**只此一批可以一次做完**（本项目唯一具现就是 DecisionV2Strategy，无第三方在飞） | decision_v2 单测全量（含 box_card recipes 修正锁）、star_tome/wish_trial 既有行为锁不跟绿先判锁；sim 对拍 box_card |
| **批 3（新钩子 × 3：handler 硬编码迁入）** | #11/#12/#13 | 定义 `decide_equip_pick`/`decide_fortune_pick`/`decide_expert_invite`（ABC + Pick 类型 + kernel 纯函数 + DecisionV2 薄委托）；三个 handler 改调策略层，内联打分整体平移 kernel | 低风险：打分逻辑逐字平移，权重值不动（先接后调，策略调优另批走 strategy-work 流水线） | `choose_expert_index` 单测随函数平移；三个 handler 新增「策略层 vs 旧内联」同输入对拍单测（平移不改语义的锁） |
| **批 4（半接入面收口，可并行）** | #14 巨星强化角色 step2 + #9 深化 | ①巨星 step2「强化角色」候选建档 + `MegastarPick.enhance_char_id` 执行面接线（开关注释挂账兑现，`registry.megastar_enhance_enabled` 生命周期按 strategy-work「策略开关」门重审）；②`decide_planner` 从 kernel 固定升费偏好升级为局面感知打分（decision_v2 侧重写具现，kernel 版保底）——这才轮到「何时升费不是最优」的策略表达 | ④②是策略行为变更（非接线），必须走 strategy-work 改前流水线（读玩法文档→命题→sim A/B）；①需先画面建档（od-dev-screen-onboarding） | sim A/B（升费策略命题）；实机验证 step2 交互 |
| **批 5（接口卫生收尾）** | 全量 | ①`decide_supply`/`decide_encounter` 的 `refresh_used` 语义对齐（encounter 调用点传参或删形参）；②存量 int 钩子统一升 Pick（可选，遥测归因完备时再做）；③`operations/battle_loop.py:342` star_tome 内联块拆独立 handler（调用点位置与其它 overlay 对齐）；④cw_strategy.py docstring 钩子计数(「12 钩子」)更新 | 纯卫生，依赖批 2 落定后做 | L1 + 文档三同步（ADR + as-built 07_plugin + 代码注释引 ADR） |

依赖关系：批 1 独立可先行（一行接线）；批 2 是批 3/5 的前置（ABC 形态定调）；批 3 与批 4① 互不依赖可并行；批 4② 依赖批 2（钩子上 ABC 后才能独立演进具现）。每批独立 commit，批内文件面互不重叠，可多子 agent 并行（批 3 三个 handler 可再拆三个单件）。

### 3.6 明确不做

- 不引入 overlay 注册表/分发框架——7+5 个钩子在 ABC 上平铺即可，13 个面不需要元编程；
- 不动 `_overlay_confirm`/点击坐标体系（观测/执行面与决策面继续分离）；
- 不在本次批改任何打分权重值（#11/#12/#13 平移时逐字保真），策略调优一律走 strategy-work 独立批 + sim 验证。

---

## 四、验收对照（任务书三问）

1. **「所有的选择都接入策略层了吗」**——没有。13 个选择面中 8 个已接入（#1-#8、#10），1 个实现存在但没接活线（#9），3 个纯 handler 硬编码（#11/#12/#13），1 个意向/执行断裂（#14）。
2. **「策略基类给每个 overlay 留接口了吗」**——没有。ABC 只留 5 个 overlay 钩子，planner/star_tome/wish_trial/box_card 长在具体类上靠鸭子调用，equip_pick/fortune_pick/expert_invite 连具现都没有。
3. **形态对齐**——§3 全部沿用既有模式（kernel 纯函数 + 具现薄委托 + session.target_comp 局面消费），零新框架。
