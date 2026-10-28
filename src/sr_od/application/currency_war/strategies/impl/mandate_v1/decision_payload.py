"""mandate_v1 决策载荷(decision_payload 钩子的 v1 实现;纯读投影)。

职责 = 决策帧出口后,从容器 game state + 策略器状态**现读**三个键组
(语义正本 = strategy-docs/strategy-telemetry.md;判据载体出处 =
strategy-docs/22_prep_screen.md 第 6 步与 12_line_and_intention.md
方向状态):

- ``direction``:方向状态现值(锁定旗/现行方向阵容名/候选快照);
- ``k_members`` + ``k_fallback``:现行 K 名单与它的供给来源标注
  (回退分支命中帧防把回退成员误读为锁定线成员);
- ``window``:终局库成员的上线窗口判据结论现值(候选 A「上阵窗口
  自锁」的复核面——该判据此前无任何落点)。

纯读纪律:本模块零写(不碰 cw4_counters/容器域/意向缓存);K 空窗
回退分支重推导 = 与备战帧(:func:`entry.emit` 顶段)同函数同参再算一遍
——:func:`cw_intention.k_empty_window_fallback` 及其派生链只读
(无 rng/无计数写面),同帧同输入重算结论一致,不构成第二算法源
(回退单一源仍在 cw_intention,此处禁复制任何兜底逻辑)。

消费契约:``bridge.MandateV1Strategy.decision_payload`` 薄委托本模块;
wrapper 在决策入口返回后调用,异常由 wrapper 降级 ``{}``(捕获缝
约定,本模块不自行吞异常)。私有限内访问申报:entry 模块的
``_entry_window_open``/``_ENDGAME_LIBRARY_MEMBERS`` 是窗口判定的
唯一判定核与其数据面常量,同包消费经设计允许。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import (
    COMP_LIBRARY,
    get_comp,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    bench_units_of,
    deployed_rows_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    entry,
    session_scope,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
    predicates,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
        LineMembersView,
    )


def _direction_key(gs: GameState) -> dict:
    """direction 键:方向状态现值三元组。

    - ``locked`` = 锁定线槽非空(:func:`session_scope.line_members_view`
      锁定旗);``comp`` = 现行方向阵容名——锁定线优先,未锁 P1 回落
      过渡配方(:func:`session_scope.direction_comp_of` 组合读口,与
      决策消费同源),两键都空 = None;``candidates`` = 候选快照
      (线名元组现读;锁定后恒空集——锁定写入连带清空)。
    """
    view = session_scope.line_members_view(gs)
    comp = session_scope.direction_comp_of(gs)
    return {
        'locked': view.locked,
        'comp': comp.name if comp is not None else None,
        'candidates': list(state_of(gs).line_candidates),
    }


def _k_members_key(gs: GameState,
                   registry: DecisionV2Registry | None) -> tuple[list[str], dict]:
    """k_members + k_fallback 键:现行 K 名单与其供给来源标注。

    算法与备战帧同源(:func:`entry.emit` 顶段,K 空窗回退分支同参):
    ``predicates.line_members(direction_comp_of(gs))`` 为空(方向键
    None)且意向载体在场时,走
    :func:`cw_intention.k_empty_window_fallback` 回退分支取成员集;
    ``k_fallback`` 记回退分支是否产出成员(hit)与分带名(band):
    band 非空 ⟺ 回退分支已运行(带值 = cw_intention 分带 token,
    'p1_gap'/'p1_lock_band'/'p2plus'),band 空串 ⟺ 分支未运行(方向
    在场或意向缺帧);hit=False 且 band 非空 = 分支运行但派生空集
    (合法空形态)。payload 重推导不写备战帧的
    ``prep_k_fallback_<band>`` 计数(纯读纪律,计数唯一写端在
    entry.emit)。
    """
    k = session_scope.direction_comp_of(gs)
    k_members = list(predicates.line_members(k))
    fallback = {'hit': False, 'band': ''}
    if k is None:
        ist = getattr(state_of(gs), 'v3_intention', None)
        if ist is not None:
            from sr_od.application.currency_war.kernel import cw_intention
            members, band = cw_intention.k_empty_window_fallback(
                gs, ist, session=gs, registry=registry)
            fallback = {'hit': bool(members), 'band': band}
            if members:
                k_members = sorted(members)
    return k_members, fallback


def _window_comp_sequence(view: LineMembersView) -> list[Comp]:
    """窗口判据的阵容查表序(:func:`entry._entry_window_open` 体内
    同式镜像——锁定 = 仅锁定线;未锁定 = 全库):sig 描述取自与窗口
    结论同一查表序的首个信号行,结论与依据同源。"""
    if view.locked:
        return [c for c in (get_comp(view.comp_name),) if c is not None]
    return list(COMP_LIBRARY)


def _window_key(gs: GameState, k_members: list[str]) -> dict[str, dict]:
    """window 键:角色 → 上线窗口判据 {open, sig}。

    角色集 = k_members ∪ 持有域(bench ∪ deployed)出现的终局库成员
    (:func:`entry._ENDGAME_LIBRARY_MEMBERS`)——候选 A「上阵窗口自锁」
    的判域正是被窗口挡在备战席的终局件,只看上场板面会漏掉被挡件,
    故持有域整体纳入。``open`` = :func:`entry._entry_window_open`
    直调(唯一判定核);``sig`` = 该角色在窗口查表序(:func:
    `_window_comp_sequence`)内首个信号行 ``[kind, threshold]``,
    无信号行 = None(open 侧同语义 fail 恒假)。键序 = 角色名排序
    (帧间 diff 稳定)。
    """
    front, back = deployed_rows_of(gs)
    held = {str(getattr(u, 'char_id', '') or '')
            for u in (*bench_units_of(gs), *front, *back) if u is not None}
    chars = sorted(set(k_members) | (held & entry._ENDGAME_LIBRARY_MEMBERS))
    if not chars:
        return {}
    comps = _window_comp_sequence(session_scope.line_members_view(gs))
    window: dict[str, dict] = {}
    for char in chars:
        sig: list | None = None
        for comp in comps:
            row = comp.entry_signals.get(char)
            if row is not None:
                sig = [row[0], row[1]]
                break
        window[char] = {'open': entry._entry_window_open(gs, char),
                        'sig': sig}
    return window


def build_decision_payload(gs: GameState,
                           registry: DecisionV2Registry | None) -> dict:
    """mandate_v1 v1 决策载荷(三键组;调用契约见模块 docstring)。

    ``registry`` = 策略器实例注册表(K 空窗回退分支 G 门同参透传,
    与备战帧消费同源)。全键 gs/state 现读,零写。
    """
    k_members, k_fallback = _k_members_key(gs, registry)
    return {
        'direction': _direction_key(gs),
        'k_members': k_members,
        'k_fallback': k_fallback,
        'window': _window_key(gs, k_members),
    }
