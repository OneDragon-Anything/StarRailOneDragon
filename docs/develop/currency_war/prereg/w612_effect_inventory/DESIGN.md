# W612 · active effect inventory 骨架 — 设计增量(两段式第一段,零 src 改动)
> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期记录,类名保持当时事实,未改)。

> 性质:DESIGN 增量。单一框架源 = `.debug/temp/currency_war/w610_gold_digger_spec/REPORT.md` Part 1(下称 W610-P1)。
> 本批只做**策略源**的 P0 骨架;环境(`source='portal'`)与词缀(`source='affix'`)双源注册是 W607 辖域,本批只在 schema 里预留 `source` 枚举值,不写其数据、不建其管道。
> 挂点真实性逐条验证见同目录 `HOOKS.md`;测试计划见 `TEST_PLAN.md`。

---

## 1. EffectSpec 数据模型

### 1.1 字段定义(W610-P1 §1.0 四元组)

```python
class TriggerKind(StrEnum):
    INSTANT = 'instant'          # 选卡当场结算(即时金/即时经验)
    PLANE_START = 'plane_start'  # 每个位面开始时(固定理财)
    NODE_ENTER = 'node_enter'    # 进入节点时(特战资金/加油站/双手狸开键盘免费刷)
    BATTLE_END = 'battle_end'    # 战斗结算时(气氛组系)
    LEVEL_UP = 'level_up'        # 升级时(节节高升;商业间谍战场段)
    ON_REFRESH = 'on_refresh'    # 每次刷新时(淘金客/概率事件/采购专员计数)
    ON_MERGE = 'on_merge'        # 合成时(武力刷新)
    ON_SELL = 'on_sell'          # 出售时(降本增效语义面)
    SUPPLY_PHASE = 'supply_phase'  # 补给阶段
    CONDITIONAL = 'conditional'  # 条件窗口(躺平冻结/成长基金到级/存款回报零花条件)

class DurationKind(StrEnum):
    ONCE = 'once'                # 一次性
    PERMANENT = 'permanent'      # 持有期永久(策略卡的缺省)
    N_NODES = 'n_nodes'          # N 节点(躺平 3 节点/长期主义 3 次)
    WHILE_HELD = 'while_held'    # 与持有绑定(=permanent 的策略别名,保留独立值便于词缀源对齐语义)

class EffectKind(StrEnum):
    ECONOMY = 'economy'          # 经济改变(金/XP/刷新/利息流)
    STATE = 'state'              # 状态改变(发经验/发金/发血——发给自己的资源)
    BATTLEFIELD = 'battlefield'  # 战场改变(商店改写/偷牌/板面重掷/装备重掷/自动操作)
    UNIT_BUFF = 'unit_buff'      # 单位强化(游戏侧自算,bot 仅登记)

class DutyFlags:                 # frozen dataclass, 四个 bool
    track: bool = False          # 需 inventory 计数器/剩余期
    predict: bool = False        # 执行动作前置知识(shop 读牌/买牌对账须预知)
    respond: bool = False        # 决策姿态改变
    # 「识」(识别入 inventory)是所有条目的缺省义务,不设标志位

@dataclass(frozen=True)
class EffectSpec:
    id: str                # plaza 稳定 id(cw_invest_data 主键,如 '301601')
    name: str              # 规范名(canon,=注册表键)
    trigger: TriggerKind
    duration: DurationKind
    category: EffectKind
    payload: EconomyEffect | BattlefieldEffect | UnitBuffRef   # 见 §1.2
    duties: DutyFlags = DutyFlags()
    notes: str = ''        # 语义出处与二义标注(「待采」记于此,不拍死)
```

**注释纪律**(项目硬约束,落码时执行):凡带节点索引/计数的字段(`remaining_nodes`/`remaining_uses`/`acquired_t`/计数器 dict)必须声明**坐标系**(节点序 = `(plane-1)*9 + round`,基 1,与 battle_loop `_now_t` 同式)与**取值时机**(登记期快照 / 挂点递减现读)。

### 1.2 payload 类型

- **economy / state 类** → 复用既有 `EconomyEffect`(cw_investments.py:52,**原样引用实例,不复制字段**)。淘金客等高频件在 `STRATEGY_ECONOMY` 已有 89 条建模,EffectSpec.payload 直接持同一实例,经济聚合 `aggregate_economy` 不动——**无双源**(一条 EconomyEffect 实例被 overlay 与 EffectSpec 共享,值只写一处)。
- **battlefield 类** → 新 payload 族(本批只定义类型,**不填游戏数值**,数值是 W607/后续批辖域):

```python
@dataclass(frozen=True)
class BattlefieldEffect:
    shop_rewrite: bool = False        # 商店改写(采购专员同费面/市场干预 3 费面)
    steal_on_level_up: int = 0        # 升级时偷最贵 N 张(商业间谍=3)
    auto_buy_owned: bool = False      # 自动购买场上已有角色(双手狸开键盘)
    free_refresh_on_node_enter: int = 0   # 进节点免费刷 N 次(Gemi狸=2)
    board_rewrite: str = ''           # 板面重写族描述('upgrade_all_cost'/'sell_all'/…)
    bench_reroll: str = ''            # bench 区间重掷(乱成一锅粥)
    counter_every: int = 0            # 每 N 次刷新计数门槛(采购专员 7/5;计数器挂 inventory)
```

- **unit_buff 类** → `UnitBuffRef(effect_text: str)` 仅登记官方原文(W610-P1 §1.2-D:~155 条游戏侧自算,bot 零响应),本批不建条目。

### 1.3 数据落位依据(**建议:两处分工,不新建 effect_registry 模块**)

| 内容 | 落位 | 依据 |
|---|---|---|
| `TriggerKind`/`DurationKind`/`EffectKind`/`DutyFlags`/`EffectSpec`/`BattlefieldEffect`/`UnitBuffRef` + `ActiveEffect`/`ActiveEffectInventory` | **新模块 `cw_effect_inventory.py`** | ① inventory 是 session 级**有状态**运行时对象,与 cw_investments(静态注册表,1030 行)职责不同;② 生产与 sim 同源消费(W610-P1 §1.3-1),独立模块让 sim import 不牵动注册表层;③ 遵循项目「核心实体建 model 类 + 注册表」模式,新域新文件与 cw_effect_ledger.py 同级同风格 |
| `STRATEGY_EFFECTS: dict[str, EffectSpec]`(overlay) | **cw_investments.py 内,与 `STRATEGY_ECONOMY` 并列** | ① 两层架构既定纪律:base(cw_invest_data 生成勿手编)× 人工 overlay,孤儿校验在 `_build_registry`(cw_investments.py:314-316)已存在,把 EffectSpec overlay 纳入同一构建校验 = 免费获得「版本更新改名即炸」防线;② 单一源:键=注册表规范名,与 STRATEGY_ECONOMY 同键空间,防两套 overlay 键漂移 |
| ❌ 不建独立 effect_registry 模块 | — | 该模块若同时装 spec 数据 + inventory,会把静态注册与 session 状态耦在一个文件;若只装 spec 数据,则与 cw_investments overlay 层形成两个手维护 overlay 面 = 双源。数据进 cw_investments、机制进 cw_effect_inventory 是最小分裂面 |

**与 cw_effect_ledger.py 的关系(防双源,必须写清)**:ledger v0(`AggregateEffect`/`build_ledger`/`effects_from_strategies`)是**派生视图**——从 STRATEGY_ECONOMY 聚合出 DP 可消费的日程/突变结构。P0 之后语义链为:`STRATEGY_EFFECTS(spec 层,含 trigger/duration/计数语义)` → inventory(在场实例)→ 各消费端(ledger 仍是其一,后续批迁移)。**本批不改 ledger、不改 effects_from_strategies**;ledger 读的仍是 STRATEGY_ECONOMY 同一实例,无漂移。

## 2. inventory 读端(接口形状;决策/执行接线不在本批)

```python
@dataclass
class ActiveEffect:
    spec: EffectSpec
    source: str                     # 'strategy' | 'portal' | 'affix'(本批只产 'strategy')
    acquired_t: int                 # 登记时点,节点序 (plane-1)*9+round,基 1;登记期快照
    remaining_nodes: int | None     # N_NODES 类的余期;None=不限;挂点递减(现读)
    remaining_uses: int | None      # 次数类余量(免战牌×2/高效决策 burst);挂点递减(现读)
    counters: dict[str, int]        # 刷新计数/购买计数/免战次数等;键名常量枚举(REFRESH/BUY/…)

class ActiveEffectInventory:
    """session 级在场效果清单。纯数据 + 读端;写端(各挂点调用)在后续批接线。"""
    entries: list[ActiveEffect]

    # —— 登记端(后续批由选卡 handler/词缀管道调用)——
    def register_strategy(self, spec: EffectSpec, acquired_t: int) -> ActiveEffect: ...
    # —— 查表端(P0 只保证形状)——
    def by_category(self, category: EffectKind) -> list[ActiveEffect]: ...
    def by_trigger(self, trigger: TriggerKind) -> list[ActiveEffect]: ...
    def counter(self, spec_id: str, key: str) -> int: ...          # 计数器读
    def first(self, spec_id: str) -> ActiveEffect | None: ...
    def predict_for(self, action: str) -> list[ActiveEffect]: ...  # 'level_up'/'refresh'/'buy'→
                                                                   # duties.predict 命中集(商业间谍/
                                                                   # Gemi狸/采购专员三实证场景)
    # —— 追踪端(挂点调用,后续批接线;P0 实现 pure 逻辑,配单测)——
    def tick_node(self, now_t: int) -> None      # N_NODES 递减+过期移除;now_t 同坐标系
    def on_battle_end(self) -> None              # BATTLE_END 触发类标记(本批只计数,不产效果)
    def on_level_up(self) -> None                # LEVEL_UP 触发标记
    def bump(self, spec_id: str, key: str, n: int = 1) -> None   # 计数器自增(刷新/购买)
```

设计要点:① 追踪端是**纯逻辑**(传入事件、改内部状态),不 import 任何 op/obs 模块 → 可离线单测,sim 与生产同一实现(W610-P1 §1.3-1);② `predict_for` 返回条目集而非布尔,消费端后续批自行取 payload;③ 查表全走 spec_id/枚举,**禁止按策略名字符串散落 if**(W610-P1 §1.0-2 本意)。

## 3. 首批 EffectSpec 条目(9 条;语义全引 cw_invest_data.py 官方原文 + W610-P1;二义标「待采」)

| id | name | trigger | duration | category | payload 来源 | duties | 备注 |
|---|---|---|---|---|---|---|---|
| 301601 | 淘金客 | ON_REFRESH | WHILE_HELD | STATE | 复用 `STRATEGY_ECONOMY['淘金客']`(xp_per_refresh=2);官方文「每次消耗金币刷新…获得2经验值」 | respond | 免费刷不产 XP(文本「消耗金币」充分;W610 §1.5-2 挂实采);姿态谓词=P1-1 辖域 |
| 201801 | 固定理财 | PLANE_START | PERMANENT | STATE | 复用 overlay;官方文「现在以及每个位面开始时,获得4经验值和2次免费刷新」 | track+respond | **待采**:「现在」的即时段与每位面段是否同一 trigger 双发(overlay 注释已标注位面开始部分拆分,见 cw_investments.py:219) |
| 103601 | 经验就是财富 | CONDITIONAL(经验获得事件) | WHILE_HELD | ECONOMY | 官方文「获得经验时,改为获取等量金币(购买经验除外)。获得4金币」(instant_gold=4 已在 overlay) | respond | **待采(=W610 §1.4.1 四歧义)**:改道是否吞策略给的 XP/转换同事件性/上限/变体;定谳前 spec.notes 保守支=「吞」 |
| 300201 | 商业间谍 | LEVEL_UP(战场段)+ CONDITIONAL(降价段) | WHILE_HELD | BATTLEFIELD | battlefield: steal_on_level_up=3 + 复用 overlay(xp_buy_cost_discount=1) | **predict**+respond | 官方文「购买经验的花费减1,升级时刷新商店,并偷取其中最贵的3个角色」;predict=shop 读牌/买牌对账前置知(P2-2 首件) |
| 204101 | 双手狸开键盘!(Gemi狸) | NODE_ENTER | WHILE_HELD | BATTLEFIELD | battlefield: free_refresh_on_node_enter=2, auto_buy_owned=True | **predict**+track | 官方文见 cw_invest_data.py:156;代买使「牌自己消失」,读牌对账必须预知(W610 §1.5-6 挂账时序) |
| 201201/303101 | 采购专员·金/彩 | ON_REFRESH(计数门槛) | WHILE_HELD | BATTLEFIELD | battlefield: counter_every=7/5, shop_rewrite=True + overlay(refresh_surprise_every) | **track**+predict+respond | 计数器=inventory `counters['refresh']`;备战席最左语义,M5 仲裁挂设计不建模 |
| 102701 | 全员晋升 | INSTANT | ONCE | BATTLEFIELD | battlefield: board_rewrite='upgrade_all_cost+1' | predict | 板面重写族代表;官方文 cw_invest_data.py:67;board/target 全量失效→后续批 update_target 强制重派生(本批不接) |
| 102801 | 人力重组 | INSTANT | ONCE | ECONOMY | 复用 overlay(free_refresh_burst=5, sell_price_mult=2.0);官方文 cw_invest_data.py:68 | predict | 出售卖价×2+免费购:执行时序编排 M8,登记面本批完成 |
| 102001 | 躺平 | CONDITIONAL | N_NODES(3) | ECONOMY | overlay(instant_gold=20)+inventory remaining_nodes=3 | **track**+respond | inventory 余期追踪首例;官方文核对于落码批(注册表原文在 102001,落码时逐字引用) |

扩展纪律:后续条目按 W610-P1 §1.2 全量表逐族补,每条必带官方原文索引(id)与 duties 判定;凡文本二义 → notes 标「待采+歧义内容」,禁拍死。

## 4. 锁(P0 交付四锁;测试计划细节见 TEST_PLAN.md)

1. **EffectSpec 构造锁**:frozen dataclass 不可变;`payload` 类型与 `category` 一致性校验(ECONOMY/STATE→EconomyEffect,BATTLEFIELD→BattlefieldEffect,UNIT_BUFF→UnitBuffRef)在注册表构建时断言;孤儿键(import 即炸)复用 `_build_registry` 校验。
2. **inventory 登记/查表/剩余期锁**:register→by_category/by_trigger/predict_for 往返;`tick_node` 对 N_NODES 条目递减与过期移除的单帧锁(躺平 3 节点:0→3 递减、第 3 次移除);counter 独立性(多策略同 key 不串账——按 spec_id 隔离)。
3. **四挂点真实性证据锁**:HOOKS.md 的逐挂点代码证据(文件:行号 + 引用行),落码批以「挂点存在性」断言固化为注释索引;任一挂点后续重构移动时,测试报红即知证据过期。
4. **双源边界锁**:本批不新增任何 `source='portal'/'affix'` 数据条目;schema 枚举预留值存在性断言(防后续批误删枚举导致 W607 对齐破裂);STRATEGY_ECONOMY 89 条零改动(与现值 hash 对拍,防实现批顺手改经济值)。
