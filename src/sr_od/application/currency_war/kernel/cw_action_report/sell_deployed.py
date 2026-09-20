"""货币战争动作上报:卖上阵角色(report_action_sell_deployed_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_exec_state import (
    deployed_indexed_to_rows,
    deployed_rows_to_indexed,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    _validate_sig,
)


def report_action_sell_deployed_param(gs: GameState, param: Any, sig: ChannelSig,
                                      session: object = None) -> LogicOutcome:
    """卖场上单位上报:deployed 槽表摘槽(置 None 不移位)→ front/back
    rows 整表平移写(board 随行写派生)+ gold +退款 + 装备回收。
    deployed_idx 越界/空槽或 expect 失配 = applied=False 零写。

    P1 容器原生:deployed 工作副本 = 行域下标派生表(§2.1 下标派生
    单一源),零中间形。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_economy import (
        bench_char_cost,
        sell_refund,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionSellDeployedParam',
                       evidence=evidence, sig=_grp_sig)

    dep_slots = deployed_rows_to_indexed(gs.front_row.value, gs.back_row.value)
    idx = int(param.deployed_idx)   # 槽位表下标直取(统一坐标系)
    if not (0 <= idx < len(dep_slots)) or dep_slots[idx] is None:
        return LogicOutcome(
            applied=False, reason=f'deployed_idx_out_of_range:{idx}')
    if getattr(param, 'expect', '') \
            and dep_slots[idx].char_id != param.expect:
        return LogicOutcome(
            applied=False,
            reason=(f'stale_proposal:{param.expect}'
                    f'!={dep_slots[idx].char_id}'))
    scratch = list(dep_slots)
    sold = scratch[idx]
    scratch[idx] = None
    front, back = deployed_indexed_to_rows(scratch)
    _w(gs.front_row, front, 'proj_sell_deployed_front')
    _w(gs.back_row, back, 'proj_sell_deployed_back')
    refund = sell_refund(int(getattr(sold, 'star', 1) or 1),
                         bench_char_cost(sold))
    g = gs.gold.value
    if g is not None:
        _w(gs.gold, int(g) + int(refund), 'proj_sell_deployed_gold')
    if sold.equips:
        _w(gs.equips, list(gs.equips.value or []) + list(sold.equips),
           'proj_sell_deployed_equips')
    return LogicOutcome(applied=True,
                        reason=str(getattr(param, 'reason', '') or ''),
                        income=int(refund))
