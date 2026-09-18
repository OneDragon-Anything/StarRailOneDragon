"""货币战争动作上报:点奖励球(report_action_click_spheres_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    SphereSight,
    _validate_sig,
    game_state_of,
)


def report_action_click_spheres_param(gs: GameState, param: Any, sig: ChannelSig,
                                      session: object = None) -> LogicOutcome:
    """点奖励球上报:容器 spheres 载荷坐标精确摘除被点的球 + 备战环
    随机收入待吸收窗(session 在场时按载荷球数开窗,下一可信金读帧
    正向差精确吸收,机理 = ``ExecBooks.prep_sphere_income_pending``)。
    球域未观察或载荷与现值无交集 = 零摘球(等观察覆盖),窗口照开。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionClickSpheresParam',
                       evidence=evidence, sig=_grp_sig)

    # 随机收入待吸收窗(执行侧单写者语义存续;金账本体现察覆盖,禁拍值)
    if session is not None:
        game_state_of(session).exec_books.prep_sphere_income_pending += \
            len(param.points)
    view = gs.spheres.value
    if view is None:
        return LogicOutcome(applied=True, reason='spheres_unobserved')
    _drop = {(int(x), int(y)) for x, y in param.points}
    _pts = tuple(p for p in view.points
                 if (int(p[1]), int(p[2])) not in _drop)
    if len(_pts) == len(view.points):
        return LogicOutcome(applied=True, reason='no_intersection')
    _w(gs.spheres, SphereSight(
        count=len(_pts),
        colors=tuple(dict.fromkeys(p[0] for p in _pts)),
        points=_pts), 'proj_click_spheres_drop')
    return LogicOutcome(applied=True)

