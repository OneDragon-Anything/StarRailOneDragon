"""货币战争动作上报:穿装备(report_action_wear_equip_param)。

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
    _validate_sig,
)


def report_action_wear_equip_param(gs: GameState, param: Any, sig: ChannelSig,
                                   session: object = None) -> LogicOutcome:
    """穿装备上报(穿戴原子,发出即记账):owned −1(在册才减)+ tracked
    目标角色 equips +1。row/slot = 画面物理槽位(词表定义),物理→下标
    换算单一函数 = ``deployed_idx_of``(执行坐标边)。session 缺席 =
    tracked 腿跳过(离线形态)。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_exec_state import (
        deployed_idx_of,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionWearEquipParam',
                       evidence=evidence, sig=_grp_sig)

    owned = list(gs.equips.value or [])
    if param.item_name in owned:
        owned.remove(param.item_name)
        _w(gs.equips, owned,
           f'owned[{param.item_name}] -1(穿戴)')
    if session is not None:
        idx = deployed_idx_of(param.row, param.slot)
        dep = list(gs.tracked_books.deployed or [])
        if 0 <= idx < len(dep) and dep[idx] is not None:
            dep[idx].equips = list(getattr(dep[idx], 'equips', None) or []) \
                + [param.item_name]
    return LogicOutcome(applied=True)

