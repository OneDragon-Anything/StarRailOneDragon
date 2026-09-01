"""货币战争 active effect inventory(在场效果清单)——效果模型机制层(骨架实现)。

**定位**(骨架契约经效果清单专项设计评审定稿;框架源 = 淘金客效果规格报告 Part 1):
- 本文件只放**机制**(类型 + inventory 读端/追踪端纯逻辑);
- **数据**(哪些策略是什么效果)在 ``cw_investments.STRATEGY_EFFECTS`` overlay——
  与 ``STRATEGY_ECONOMY`` 同键空间同构建校验,防两套手维护面漂移;
- 生产与 sim 同一实现(sim 结算效果时同步维护 inventory;效果规格契约);
- **零决策行为**:任何决策路径不消费本模块产出——查表接入归后续
  姿态面/执行预判面。

**EffectSpec 四元组**(每条策略 = 一条效果规格):
触发时机(trigger)× 持续期(duration)× 效果类型(category)× bot 待办(duties),
payload 承载效果数值/战场语义;经济/状态类复用 ``cw_investments.EconomyEffect``
同一实例(单一源,不复制字段)。

**与 cw_effect_ledger 的关系**:ledger(``cw_effect_ledger.py``)是消费端派生视图
(从 EconomyEffect 聚合出 DP 日程/突变结构),本模块是其上游。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 仅类型注解引用(项目规范允许);运行时 payload 按对象持有,
    # 类型一致性校验在 cw_investments 构建层(那里有真类)做 isinstance。
    from sr_od.application.currency_war.kernel.cw_investments import EconomyEffect


class TriggerKind(StrEnum):
    """效果触发时机(语义出自效果规格设计评审定稿)。"""
    INSTANT = 'instant'            # 选卡当场结算(即时金/全场重写类)
    PLANE_START = 'plane_start'    # 每个位面开始时(固定理财)
    NODE_ENTER = 'node_enter'      # 进入节点时(特战资金/Gemi狸免费刷)
    BATTLE_END = 'battle_end'      # 战斗结算时(气氛组系)
    LEVEL_UP = 'level_up'          # 升级时(节节高升;商业间谍战场段)
    ON_REFRESH = 'on_refresh'      # 每次刷新时(淘金客/概率事件/采购专员计数)
    ON_MERGE = 'on_merge'          # 合成时(武力刷新)
    ON_SELL = 'on_sell'            # 出售时(降本增效语义面)
    SUPPLY_PHASE = 'supply_phase'  # 补给阶段
    CONDITIONAL = 'conditional'    # 条件窗口(躺平冻结/经验就是财富改道/成长基金到级)


class DurationKind(StrEnum):
    """效果持续期。"""
    ONCE = 'once'              # 一次性
    PERMANENT = 'permanent'    # 持有期永久
    N_NODES = 'n_nodes'        # 持续 duration_nodes 个节点(躺平 3 节点)
    WHILE_HELD = 'while_held'  # 与持有绑定(策略卡缺省;独立值供词缀源对齐语义)


class EffectKind(StrEnum):
    """效果类型四分类(效果规格设计评审定纲)。"""
    ECONOMY = 'economy'          # 经济改变(金/XP/刷新/利息流)
    STATE = 'state'              # 状态改变(发给自己的经验/金/血)
    BATTLEFIELD = 'battlefield'  # 战场改变(商店改写/偷牌/板面重掷/自动操作)
    UNIT_BUFF = 'unit_buff'      # 单位强化(游戏侧自算,bot 仅登记零响应)


@dataclass(frozen=True)
class DutyFlags:
    """bot 待办标志(「识」= 识别入 inventory 是所有条目缺省义务,不设位)。"""
    track: bool = False    # 需 inventory 计数器/剩余期
    predict: bool = False  # 执行动作前置知识(shop 读牌/买牌对账须预知)
    respond: bool = False  # 决策姿态改变


@dataclass(frozen=True)
class BattlefieldEffect:
    """战场改变族 payload(只建类型;数值随条目按官方原文填,不猜)。"""
    shop_rewrite: bool = False              # 商店改写(采购专员同费面/市场干预 3 费面)
    steal_on_level_up: int = 0              # 升级时偷商店最贵 N 张(商业间谍=3)
    auto_buy_owned: bool = False            # 自动购买场上已有角色(Gemi狸)
    free_refresh_on_node_enter: int = 0     # 进节点免费刷 N 次(Gemi狸=2)
    board_rewrite: str = ''                 # 板面重写语义('upgrade_all_cost+1'/'sell_all'/…)
    bench_reroll: str = ''                  # 备战席区间重掷(乱成一锅粥族;未建条目)
    counter_every: int = 0                  # 每 N 次刷新计数门槛(采购专员金 7/彩 5)


@dataclass(frozen=True)
class UnitBuffRef:
    """单位强化引用(官方效果原文;~155 条游戏侧自算,bot 零响应;效果规格判读)。"""
    effect_text: str


@dataclass(frozen=True)
class EffectSpec:
    """一条投资策略的效果规格(四元组 + 二义标注)。

    - id/name 必须与 ``cw_invest_data.PLAZA_AUGMENTS`` 官方条目一致(构建层校验
      id+name 双匹配,改名/移除 import 即炸)。
    - payload 类型与 category 的对应:ECONOMY/STATE→EconomyEffect、
      BATTLEFIELD→BattlefieldEffect、UNIT_BUFF→UnitBuffRef(构建层校验)。
    - pending/verdict:效果文本二义条目 pending=True,**不拍死**——verdict 保持
      None 直到实采定谳;消费端见 pending=True 必须走
      notes 声明的保守支。
    """
    id: str                       # plaza 稳定 id(cw_invest_data 主键)
    name: str                     # 规范名(canon,=注册表键;禁昵称,如 Gemi狸 的
                                  # 官方卡名是「双手狸开键盘！」,见 204101)
    trigger: TriggerKind
    duration: DurationKind
    category: EffectKind
    payload: EconomyEffect | BattlefieldEffect | UnitBuffRef
    duties: DutyFlags = DutyFlags()
    duration_nodes: int = 0       # N_NODES 类的持续节点数;**自然数计数非索引**(躺平=3);
                                  # 恒稳(注册期常量,登记时拷入 ActiveEffect.remaining_nodes)
    pending: bool = False         # True=效果文本有二义未实采定谳
    verdict: str | None = None    # 实采定谳回填('改道吞引擎XP' 等);None=未定谳
    notes: str = ''               # 语义出处与歧义内容(pending 条目必写保守支)


# ===== 计数器键常量(键名不散落字符串,防漂移)=====
class CounterKey:
    REFRESH = 'refresh'   # 刷新计数(采购专员门槛/Gemi狸)
    BUY = 'buy'           # 购买计数(返利系每 3 张 5 费)


# 事件标记键(追踪端标记,非策略计数器;下划线前缀与策略计数器空间隔离)
_EVENT_LEVEL_UP = '_event_level_up'
_EVENT_BATTLE_END = '_event_battle_end'


@dataclass
class ActiveEffect:
    """一条在场效果实例(spec + 来源 + 登记时点 + 余期/计数器)。"""
    spec: EffectSpec
    source: str                # 'strategy' | 'portal' | 'affix'(P0 只产 'strategy',
                               # 后两值是环境源/词缀源辖域的 schema 预留)
    acquired_t: int | None     # 登记时点;节点序 = (plane-1)*9+round,**基 1**;
                               # 登记期快照(与 battle_loop _now_t 同式)
    remaining_nodes: int | None  # N_NODES 类余期;**自然数计数非索引**;None=不限;
                                 # 挂点(tick_node)现读递减
    remaining_uses: int | None   # 次数类余量(免战牌×2 等);挂点现读递减
    counters: dict[str, int] = field(default_factory=dict)   # CounterKey 键 → 计数


class ActiveEffectInventory:
    """session 级在场效果清单。纯数据 + 读端/追踪端;零 import 包内模块(可离线单测)。

    写端(挂点调用)现状:仅「升级事件」已接生产
    (prep_actions._level_up 成功返回处,on_level_up);选卡/进节点/结算三挂点的
    register/tick 接线未接。
    """

    def __init__(self) -> None:
        self.entries: list[ActiveEffect] = []
        # 事件标记:键 → 计数(_EVENT_* 常量);on_level_up/on_battle_end 写
        self._events: dict[str, int] = {}

    # —— 登记端 ——
    def register_strategy(self, spec: EffectSpec, acquired_t: int | None) -> ActiveEffect:
        """策略获得 → 入清单。acquired_t 坐标系见 ActiveEffect.acquired_t。"""
        entry = ActiveEffect(
            spec=spec, source='strategy', acquired_t=acquired_t,
            remaining_nodes=spec.duration_nodes if spec.duration == DurationKind.N_NODES else None,
            remaining_uses=None,
        )
        self.entries.append(entry)
        return entry

    # —— 查表端(形状保证;决策消费归后续)——
    def by_category(self, category: EffectKind) -> list[ActiveEffect]:
        return [e for e in self.entries if e.spec.category == category]

    def by_trigger(self, trigger: TriggerKind) -> list[ActiveEffect]:
        return [e for e in self.entries if e.spec.trigger == trigger]

    def first(self, spec_id: str) -> ActiveEffect | None:
        for e in self.entries:
            if e.spec.id == spec_id:
                return e
        return None

    def counter(self, spec_id: str, key: str) -> int:
        """按 (spec_id, key) 读计数——多策略同 key 天然隔离,不串账。"""
        e = self.first(spec_id)
        return e.counters.get(key, 0) if e is not None else 0

    _ACTION_TRIGGER: dict[str, TriggerKind] = {
        'level_up': TriggerKind.LEVEL_UP,
        'refresh': TriggerKind.ON_REFRESH,
        'node_enter': TriggerKind.NODE_ENTER,
        'battle_end': TriggerKind.BATTLE_END,
    }

    def predict_for(self, action: str) -> list[ActiveEffect]:
        """执行动作 → 需前置知(predict)的在效果集。

        action 映射见 _ACTION_TRIGGER;未知 action 保守返回**全部** predict 条目
        (漏预知的代价是读牌/对账误判,多给不错给)。
        """
        trigger = self._ACTION_TRIGGER.get(action)
        if trigger is None:
            return [e for e in self.entries if e.spec.duties.predict]
        return [e for e in self.entries
                if e.spec.duties.predict and e.spec.trigger == trigger]

    # —— 追踪端(挂点调用;纯逻辑,sim 与生产同一实现)——
    def tick_node(self) -> None:
        """进节点边界:N_NODES 类余期递减,归零移除。

        余期是自然数计数(非索引):登记 3 → 三次 tick 后移除(躺平 3 节点)。
        """
        for e in list(self.entries):
            if e.remaining_nodes is None:
                continue
            e.remaining_nodes -= 1
            if e.remaining_nodes <= 0:
                self.entries.remove(e)

    def on_level_up(self) -> None:
        """升级事件标记(挂点 = prep_actions._level_up 成功返回处)。"""
        self._events[_EVENT_LEVEL_UP] = self._events.get(_EVENT_LEVEL_UP, 0) + 1

    def on_battle_end(self) -> None:
        """战斗结算事件标记(挂点候选 = strategy.on_round_end 回调;未接)。"""
        self._events[_EVENT_BATTLE_END] = self._events.get(_EVENT_BATTLE_END, 0) + 1

    def event_count(self, kind: str) -> int:
        return self._events.get(kind, 0)

    def bump(self, spec_id: str, key: str, n: int = 1) -> None:
        """计数器自增(刷新/购买等动作侧调用;未接动作点)。"""
        e = self.first(spec_id)
        if e is not None:
            e.counters[key] = e.counters.get(key, 0) + n
