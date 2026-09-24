"""kernel 事实事件钩子槽(事件钩子契约,正本 = docs/develop/sr_od/
application/currency_war/sim/sim-design.md §6.3)。

经本槽广播事实事件(:class:`FactEvent`)——不引发画面转移的世界变化
(overlay 触发层消费);现役成员:板面组成变化(deploy / 买牌合成 /
sell / wear 落地后)、升星事件;广播点 = 对应上报函数写后。

引发画面转移的动作后果不经本槽——走 ``cw_world_decl.WorldDecl``
声明通道(``cw_sim_ports.declare_world`` 喂入 sim 后端 advance)。

模块级槽 + 缺省关(None = 零开销直返)+ 装配点显式接通,先例 =
``cw_game_state.set_defect_sink``。实机缺省关 = 零行为变化;sim 后端
订阅点 = ``sim/cw_sim_backend.install_backend``(装配即接通,卸载复位)。

依赖方向:本模块零 kernel 内部依赖(事件形状自足),供上报函数族与
容器上报单向 import,禁反向(防 import 环)。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from one_dragon.utils.log_utils import log


@dataclass(frozen=True)
class FactEvent:
    """事实事件(不引发画面转移的世界变化;overlay 触发层消费)。"""

    kind: str
    detail: dict = field(default_factory=dict)


#: 事实事件现役成员(overlay 触发层消费面;随触发目录扩充)。
FACT_EVENT_KINDS: frozenset[str] = frozenset({
    'board_changed',
    'star_up',
})

#: 事实事件外送钩子(**缺省关** = None 零开销;订阅方 = sim 后端)。
_FACT_SINK: Callable[[FactEvent], None] | None = None


def set_fact_event_sink(fn: Callable[[FactEvent], None] | None) -> None:
    """注入事实事件订阅(注入槽模式,None = 关,缺省态)。"""
    global _FACT_SINK
    _FACT_SINK = fn


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
