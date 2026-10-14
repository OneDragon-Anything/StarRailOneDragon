"""货币战争动作上报:卖上阵角色(report_action_sell_deployed_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察写
端留在 ``kernel/cw_game_state``,本包 → 容器单向依赖。
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


def report_action_sell_deployed_param(gs: GameState, param: Any, sig: ChannelSig,
                                      session: object = None) -> LogicOutcome:
    """卖场上单位上报:deployed 视图摘槽(置 None 不移位)→ 单字段整值
    替换写(board 随行写派生;一次写 = 一次完整语义
    变更)+ gold +退款 + 装备回收。
    deployed_idx 越界/空槽或 expect 失配 = applied=False 零写。

    deployed_idx = 动作坐标系定长 10 下标(0-3 前排 / 4-9 后排槽 1-6;
    窗口期桥,后排 7-9 扩展格超出动作坐标系不可卖——tracked 表硬上限
    同族边界,3.2 续覆盖)。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_economy import (
        bench_char_cost,
        sell_refund,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        deployed_indexed_of_view,
        deployed_view_of_indexed,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionSellDeployedParam',
                       evidence=evidence, sig=_grp_sig)

    view = gs.deployed.value
    dep_slots = deployed_indexed_of_view(view)
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
    _w(gs.deployed, deployed_view_of_indexed(scratch, view),
       'proj_sell_deployed')
    refund = sell_refund(int(getattr(sold, 'star', 1) or 1),
                         bench_char_cost(sold, gs))
    g = gs.gold.value
    if g is not None:
        _w(gs.gold, int(g) + int(refund), 'proj_sell_deployed_gold')
    if sold.equips:
        _w(gs.equips, list(gs.equips.value or []) + list(sold.equips),
           'proj_sell_deployed_equips')
    # 事实事件:板面组成变化(sell 落地;overlay 触发层消费,缺省关零开销)
    # (事实事件广播已停用。)
    return LogicOutcome(applied=True,
                        reason=str(getattr(param, 'reason', '') or ''),
                        income=int(refund))
