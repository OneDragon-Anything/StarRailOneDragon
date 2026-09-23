"""kernel 事件钩子槽(事件钩子契约;sim 统一迭代 design.md §2)。

经本槽广播两类事件,订阅方 = sim 后端(install_sim_backend 装配时接通
sink;3.2 消费):

- **转移事件**(:class:`TransitionEvent`)——引发画面转移的动作落地,
  具名封闭集 :data:`TRANSITION_EVENT_KINDS`(盘点方法与成员依据 =
  docs/develop/sr_od/application/currency_war/changes/2026-09-23-
  sim-backend-unification/details/flow-seam.md 附录 B:以
  ``cw_action_registry`` 注册表全量动作为底集,按 ``screens/`` 各篇 §5
  终结/交回表筛「落地引发画面转移」者);广播点 = 对应上报函数 applied
  落地出口。
- **事实事件**(:class:`FactEvent`)——不引发画面转移的世界变化
  (overlay 触发层消费);现役成员:板面组成变化(deploy / 买牌合成 /
  sell / wear 落地后)、升星事件;广播点 = 对应上报函数写后。

模块级槽 + 缺省关(None = 零开销直返)+ 装配点显式接通,先例 =
``cw_game_state.set_defect_sink``。实机缺省关 = 零行为变化;旧引擎
(sim/cw_sim_engine 自驱动路径)不接 sink,广播对旧链零触达。

依赖方向:本模块零 kernel 内部依赖(事件形状自足),供上报函数族与
容器上报单向 import,禁反向(防 import 环)。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps

from one_dragon.utils.log_utils import log


@dataclass(frozen=True)
class TransitionEvent:
    """转移事件(引发画面转移的动作落地)。

    ``kind`` ∈ :data:`TRANSITION_EVENT_KINDS`(封闭集,emit 校验);
    ``detail`` = 归因旁证(actor 等),后端语义消费以 kind 为准。
    """

    kind: str
    detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FactEvent:
    """事实事件(不引发画面转移的世界变化;overlay 触发层消费)。"""

    kind: str
    detail: dict = field(default_factory=dict)


#: 转移事件封闭集(成员与依据 = flow-seam 详设附录 B;emit 时集外
#: ValueError 响亮,防广播点漂移出集)。逐成员 = 动作上报落地名:
#: settle/supply_confirm = 终结动作节点推进(``NODE_ADVANCE_TRIGGERS``);
#: start_battle = 出战(交回外循环战斗分支);pick_* = 事件单选族 12 屏
#: 选卡确认(overlay 消失回底层屏);open_box = 开箱(武装箱选择画面
#: 出现);open_bookcard = 开书册卡(专家邀请函弹窗出现);close_shop =
#: 关店(商店 overlay 收起回备战)。
TRANSITION_EVENT_KINDS: frozenset[str] = frozenset({
    'settle_confirm',
    'supply_confirm',
    'start_battle',
    'pick_encounter',
    'pick_supply',
    'pick_megastar',
    'pick_partner',
    'pick_planner',
    'pick_invest_env',
    'pick_invest_strategy',
    'pick_fortune',
    'pick_wish_trial',
    'pick_star_tome',
    'pick_box_card',
    'pick_expert_invite',
    'open_box',
    'open_bookcard',
    'close_shop',
})

#: 事实事件现役成员(overlay 触发层消费面;随 3.2 触发目录扩充)。
FACT_EVENT_KINDS: frozenset[str] = frozenset({
    'board_changed',
    'star_up',
})

#: 转移事件外送钩子(**缺省关** = None 零开销;订阅方 = sim 后端)。
_TRANSITION_SINK: Callable[[TransitionEvent], None] | None = None
#: 事实事件外送钩子(**缺省关**)。
_FACT_SINK: Callable[[FactEvent], None] | None = None


def set_transition_event_sink(fn: Callable[[TransitionEvent], None] | None) -> None:
    """注入转移事件订阅(注入槽模式,None = 关,缺省态)。"""
    global _TRANSITION_SINK
    _TRANSITION_SINK = fn


def set_fact_event_sink(fn: Callable[[FactEvent], None] | None) -> None:
    """注入事实事件订阅(注入槽模式,None = 关,缺省态)。"""
    global _FACT_SINK
    _FACT_SINK = fn


def emit_transition_event(kind: str, detail: dict | None = None) -> None:
    """广播转移事件(封闭集校验;缺省关 = 零开销直返)。

    集外 kind = ValueError 响亮(广播点漂移出封闭集 = 接线 bug,禁静默);
    sink 异常吞并告警(订阅方故障不得阻断上报链,与 defect sink 同纪律)。
    """
    if kind not in TRANSITION_EVENT_KINDS:
        raise ValueError(
            f'转移事件集外 kind: {kind!r}(封闭集 = '
            f'{sorted(TRANSITION_EVENT_KINDS)})')
    if _TRANSITION_SINK is None:
        return
    try:
        _TRANSITION_SINK(TransitionEvent(kind=kind,
                                         detail=detail or {}))
    except Exception as e:  # noqa: BLE001  订阅方故障不阻断上报链
        log.warning('[cw-event] 转移事件订阅异常(不阻塞): %s', e)


def emit_fact_event(kind: str, detail: dict | None = None) -> None:
    """广播事实事件(缺省关 = 零开销直返;sink 异常吞并告警)。"""
    if kind not in FACT_EVENT_KINDS:
        raise ValueError(
            f'事实事件集外 kind: {kind!r}(封闭集 = '
            f'{sorted(FACT_EVENT_KINDS)})')
    if _FACT_SINK is None:
        return
    try:
        _FACT_SINK(FactEvent(kind=kind, detail=detail or {}))
    except Exception as e:  # noqa: BLE001  订阅方故障不阻断上报链
        log.warning('[cw-event] 事实事件订阅异常(不阻塞): %s', e)


def transition_event_on_applied(kind: str) -> Callable:
    """上报函数装饰器:applied=True 出口广播转移事件(封闭集接线)。

    覆盖上报函数全部 applied 出口(多出口函数免逐 return 接线,新增
    出口自动入广播面);applied=False(拒绝/留证未写)= 零广播。
    广播时点 = 上报函数写后、返回调用方前(design 事件钩子契约)。
    ``outcome.applied`` 鸭子读取(不 import LogicOutcome,防 kernel 内
    import 环)。
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            outcome = fn(*args, **kwargs)
            if getattr(outcome, 'applied', False):
                emit_transition_event(kind)
            return outcome
        return wrapper
    return deco
