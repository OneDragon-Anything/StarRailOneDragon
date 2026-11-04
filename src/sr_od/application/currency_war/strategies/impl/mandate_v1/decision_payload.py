"""mandate_v1 决策载荷(decision_payload 钩子的 v1 实现;纯读投影)。

职责 = 决策帧出口后组装七个键(语义权威版本 =
strategy-docs/strategy-telemetry.md;判据载体出处 =
strategy-docs/22_prep_screen.md 第 6 步与 12_line_and_intention.md
方向状态),两类来源:

- 现读键 5(direction/k_members/k_fallback/transition_
  candidates/member_rank):状态容器 game state + 策略器状态**现读**
  (语义权威版本 = strategy-telemetry.md 键表;window 键已随 entry_signals
  整体退役);
- 产物透传键 2(pick_margin/deploy_margin):词表动作字段与私有槽,
  均为**决策帧出口时点快照**(pick-margin-telemetry design §2.2)。

纯读纪律:本模块零写(不碰 cw4_counters/状态容器域/意向缓存/私有槽——
deploy_margin 读槽后清挂 bridge 覆写,读后清不入本模块);K 空窗
回退分支重推导 = 与备战帧(:func:`entry.emit` 顶段)同函数同参再算一遍
——:func:`cw_intention.k_empty_window_fallback` 及其派生链只读
(无 rng/无计数写面),同帧同输入重算结论一致,不构成第二算法源
(回退单一源仍在 cw_intention,此处禁复制任何兜底逻辑)。

消费契约:``bridge.MandateV1Strategy.decision_payload`` 薄委托本模块;
wrapper 在决策入口返回后调用(入参 result = 入口返回值,产物透传键
pick_margin 的载体),异常由 wrapper 降级 ``{}``(捕获缝
约定,本模块不自行吞异常)。
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    session_scope,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.priority import (
    assemble_priority_context,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.sell_candidates import (
    sell_line_membership,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
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
    k_members = 统一线内名单(:func:`sell_line_membership`,单一准入
    §2.1——候选 ∪ 配方 ∪ 锁定线并集)为空(名单真空)且意向载体在场时,
    走 :func:`cw_intention.k_empty_window_fallback` 回退分支取成员集;
    ``k_fallback`` 记回退分支是否产出成员(hit)与分带名(band):
    band 非空 ⟺ 回退分支已运行(带值 = cw_intention 分带 token,
    'p1_gap'/'p1_lock_band'/'p2plus'),band 空串 ⟺ 分支未运行(名单
    非空或意向缺帧);hit=False 且 band 非空 = 分支运行但派生空集
    (合法空形态)。payload 重推导不写备战帧的
    ``prep_k_fallback_<band>`` 计数(纯读纪律,计数唯一写端在
    entry.emit)。
    """
    k_members = sorted(sell_line_membership(gs))
    fallback = {'hit': False, 'band': ''}
    if not k_members:
        ist = getattr(state_of(gs), 'v3_intention', None)
        if ist is not None:
            from sr_od.application.currency_war.kernel import cw_intention
            members, band = cw_intention.k_empty_window_fallback(
                gs, ist, session=gs, registry=registry)
            fallback = {'hit': bool(members), 'band': band}
            if members:
                k_members = sorted(members)
    return k_members, fallback


def _transition_candidates_key(gs: GameState) -> list[str]:
    """transition_candidates 键:过渡候选槽现值(过渡条目名照录为
    list,JSON 行行自足;过渡锁定后槽随锁定条目域收窄,终局锁定清空
    ——槽语义单一源 = mandate_state.StrategyState.transition_candidates)。"""
    return list(state_of(gs).transition_candidates)


def _member_rank_key(gs: GameState) -> dict[str, tuple[int, int]]:
    """member_rank 键:统一优先级档内序数表((层, 位次) 二元组)现值。

    与卖出评估器**同一装配函数**现算(:func:`priority.
    assemble_priority_context`,禁在本模块复制装配逻辑 = 第二实现):
    终局成员 = (0, 线内序数) / 过渡成员 = (1, 候选位次),重叠归终局
    (装配序承载,零特判)。``deployed_names`` 空集与固定种子 rng =
    占位参数——member_rank 装配只读方向状态与知识卡,不消费部署名集
    (档 1 判定专用字段)与随机流(等价牌随机尾键专用),占位不污染
    rank 现值;rng 显式传占位是为绕开缺省读口 ``priority_rng_of``
    的 scratch 写面(纯读纪律:本模块零写)。表外成员判定端缺省
    :data:`priority.RANK_TRANSITION_BOTTOM` 不在本表(仅装配产物
    照录)。"""
    ctx = assemble_priority_context(
        gs, gs, deployed_names=frozenset(), rng=random.Random(0))
    return dict(ctx.member_rank)


def _pick_margin_key(result: object | None) -> dict | None:
    """pick_margin 键:投资两面选卡帧的次名分量(产物透传键)。

    值源 = 决策入口返回动作实例的 ``margin`` 字段(词表动作字段通道,
    flow 从决策产物拷入;键形与边界值表 = pick-margin-telemetry
    design §2.2-1/2)。非选卡帧(动作无该字段)与刷新建议帧/空候选
    帧 → None(不落值)。纯读:本模块不改动作实例。"""
    return getattr(result, 'margin', None)


def _deploy_margin_key(gs: GameState) -> dict | None:
    """deploy_margin 键:部署定型次名分量(私有槽透传键)。

    值源 = StrategyState.deploy_margin 槽现读(写入端单一源 =
    entry._step5_deploy;键形 = pick-margin-telemetry design §2.2-3,
    帧定界 = bridge 入口清+读后清 → 非部署帧读到恒空/None)。读槽属
    纯读;读后清挂 bridge 覆写(本模块零写纪律不动)。"""
    return state_of(gs).deploy_margin


def build_decision_payload(gs: GameState,
                           registry: DecisionV2Registry | None,
                           result: object | None = None) -> dict:
    """mandate_v1 v1 决策载荷(八键 = 现读 6 + 产物透传 2;调用契约见
    模块 docstring)。

    ``registry`` = 策略器实例注册表(K 空窗回退分支 G 门同参透传,
    与备战帧消费同源);``result`` = 决策入口返回值(pick_margin 的
    通道载体,由 bridge 覆写经 wrapper 传入;直调缺省 None = 该键
    恒 None)。现读键全键 gs/state 现读,零写。
    """
    k_members, k_fallback = _k_members_key(gs, registry)
    return {
        'direction': _direction_key(gs),
        'k_members': k_members,
        'k_fallback': k_fallback,
        # window 键已随 entry_signals 整体退役(2026-11 用户终裁)——历史
        # 落盘数据不受影响,新帧不再产该键
        'transition_candidates': _transition_candidates_key(gs),
        'member_rank': _member_rank_key(gs),
        'pick_margin': _pick_margin_key(result),
        'deploy_margin': _deploy_margin_key(gs),
    }
