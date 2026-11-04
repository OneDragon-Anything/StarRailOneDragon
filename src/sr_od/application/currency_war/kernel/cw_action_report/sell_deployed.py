"""货币战争动作上报:卖上阵角色(report_action_sell_deployed_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。状态容器、写入口与观察写
端留在 ``kernel/cw_game_state``,本包 → 状态容器单向依赖。
语义权威版本 = 函数 docstring(自 cw_game_state 逐字迁移)。
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

    deployed_idx = 前排 0-3 / 后排 4+(排内 1 基槽号,值域随
    ``back_capacity_of`` 动态 6-9 扩格——SellDeployed 坐标域扩展
    (unified-deploy-order §4:D4-2/D5-2 三落点之一,扩格帧直卖不再
    截断);读侧直读 deployed 视图子表,不经定长 10 截断桥。"""
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

    view = gs.deployed.value
    # 定长截断桥(deployed_indexed_of_view 后排 [:6])不适用:扩格帧
    # 后排 7-9 直卖消费位切直读动态视图(桥本体与其余消费方零改动)。
    front: list = list(view.front_slots or []) if view is not None else []
    back: list = list(view.back_slots or []) if view is not None else []
    idx = int(param.deployed_idx)   # 前排 0-3 / 后排 4+ 排内 1 基直址
    if not (0 <= idx < len(front) + len(back)) \
            or (front + back)[idx] is None:
        return LogicOutcome(
            applied=False, reason=f'deployed_idx_out_of_range:{idx}')
    _sold = (front + back)[idx]
    if getattr(param, 'expect', '') \
            and _sold.char_id != param.expect:
        return LogicOutcome(
            applied=False,
            reason=(f'stale_proposal:{param.expect}'
                    f'!={_sold.char_id}'))
    if idx < len(front):
        sold = front[idx]
        front[idx] = None
    else:
        sold = back[idx - len(front)]
        back[idx - len(front)] = None
    from sr_od.application.currency_war.kernel.cw_game_state import (
        DeployedView,
    )
    _w(gs.deployed, DeployedView(front_slots=front, back_slots=back),
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
