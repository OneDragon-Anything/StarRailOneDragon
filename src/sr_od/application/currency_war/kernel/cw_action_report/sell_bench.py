"""货币战争动作上报:卖备战席角色(report_action_sell_bench_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    BENCH_CAPACITY_DEFAULT,
    BenchSlot,
    BenchView,
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    Unit,
    _validate_sig,
)


def report_action_sell_bench_param(gs: GameState, param: Any,
                                   sig: ChannelSig) -> LogicOutcome:
    """卖备战席上报:bench 该槽置 empty + gold +退款 + 装备回收
    (C6 守恒)+ 溢出腿(overflow_warning 在场时腾出槽当帧记溢出件入位,
    容器状态条件域无关;身份两分 = 角色入 unit 槽件 / 占席道具入
    supply_box 槽件,判据 = ``cw_investments.BENCH_ITEM_NAMES``;
    3.2 单账化后容器 bench 即唯一账,原 tracked 对称吸收腿退役)。

    槽位空/占位件非 unit/越界 = 陈旧提案,applied=False 零写(等观察
    覆盖);expect 非空且名不符 = stale_proposal 拒绝(live 提案恒 ''
    零行为)。退款锚 = sell_refund(star, bench_char_cost),与 simulate
    卖出分支同式单一源。
    """
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_economy import (
        bench_char_cost,
        sell_refund,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionSellBenchParam',
                       evidence=evidence, sig=_grp_sig)

    _bview = gs.bench.value
    bench_slots = list(_bview.slots) if _bview is not None else []
    idx = int(param.bench_idx)   # 槽位表下标直取(统一坐标系,零换算)
    if not (0 <= idx < len(bench_slots)) or bench_slots[idx] is None \
            or bench_slots[idx].kind != 'unit' \
            or bench_slots[idx].unit is None:
        return LogicOutcome(
            applied=False, reason=f'bench_idx_out_of_range:{idx}')
    sold = bench_slots[idx].unit
    if getattr(param, 'expect', '') \
            and sold.char_id != param.expect:
        return LogicOutcome(
            applied=False,
            reason=(f'stale_proposal:{param.expect}'
                    f'!={sold.char_id}'))
    bench_slots[idx] = BenchSlot(kind='empty')
    # 溢出腿:席满溢出态(overflow_warning 在场)下卖牌,腾出槽当帧记
    # 溢出件入位(游戏侧行为,prep.md 告警节实机建档;占席道具与角色同款
    # 溢出语义,2026-09-24 用户确认——道具身份落 supply_box 槽件,禁造假
    # 角色;入位角色星级缺读 1 兜底,下帧 heavy 实读覆盖修正,两态制观察赢)。
    _ov_warn = gs.overflow_warning.value
    _ov_id = gs.overflow_card.value
    if _ov_warn and _ov_id:
        from sr_od.application.currency_war.kernel.cw_investments import (
            BENCH_ITEM_NAMES,
        )
        if _ov_id in BENCH_ITEM_NAMES:
            _absorb: BenchSlot = BenchSlot(kind='supply_box')
        else:
            _absorb = BenchSlot(
                kind='unit', unit=Unit(char_id=_ov_id, star=1, equips=[]))
        bench_slots[idx] = _absorb
        _w(gs.overflow_card, '', 'proj_overflow_absorbed')
        _w(gs.overflow_warning, False, 'proj_overflow_cleared')
        # (tracked 第二账已退役:入位件随本函数
        #  bench 整表写单点落主账,原「执行侧对称吸收腿」无可同步。)
    _w(gs.bench, BenchView(slots=bench_slots,
                           capacity=(_bview.capacity
                                     if _bview is not None
                                     else BENCH_CAPACITY_DEFAULT)),
       'proj_sell_bench')
    refund = sell_refund(int(getattr(sold, 'star', 1) or 1),
                         bench_char_cost(sold, gs))
    g = gs.gold.value
    if g is not None:
        _w(gs.gold, int(g) + int(refund), 'proj_sell_refund')
    # 装备回收进 owned 池(C6 装备守恒;原商店腿有/备战域缺口,统一补齐)。
    if sold.equips:
        _w(gs.equips, list(gs.equips.value or []) + list(sold.equips),
           'proj_sell_equips_recover')
    # 事实事件:板面组成变化(sell 落地;overlay 触发层消费,缺省关零开销)
    # (事实事件广播已随事实事件槽退役删除。)
    return LogicOutcome(applied=True,
                        reason=str(getattr(param, 'reason', '') or ''),
                        income=int(refund))

