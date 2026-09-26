"""货币战争动作上报:开书册卡(report_action_open_bookcard_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。

**后果声明**(动作后果声明化详设 world-decl.md §2 表 #6):applied 出口
构造 ``WorldDecl``(trigger = ''——腾席写端 = 本上报「开卡即腾席」,
backend 活仅呈现专家邀请函弹窗;``next_screen`` = 专家邀请函档,画面档
全表唯一可推),转移事件广播随本动作单轨切换摘除。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    BenchView,
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    _validate_sig,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

#: 开书册卡声明(纯转移;封闭集单一源 = sim 后端 advance 分派表键集)。
_DECL: WorldDecl = WorldDecl(next_screen='货币战争-备战-专家邀请函',
                             trigger='')


def report_action_open_bookcard_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """开书册卡上报:bench 槽位 kind → empty(开卡即腾席)。槽 kind 门 =
    ``'bookcard'``(kind 细分批:书册卡槽不再统一降级 supply_box,容器
    bench kind 细分 = 'bookcard' 单一口径);槽不存在/类型不符 =
    applied=False 零写零声明。applied 出口构造后果声明(:data:`_DECL`,
    纯转移)。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionOpenBookcardParam',
                       evidence=evidence, sig=_grp_sig)

    view = gs.bench.value
    if view is None:
        # bench_unobserved 早退不登记:S6 登记与开卡动作同生——本腿生产
        # 不可达(bench 恒有开局种子 9 空槽视图,cw_game_state 种子底座),
        # 仅测试直构/极端离线形态可达;该形态开卡本身未落地,登记即假阳。
        return LogicOutcome(applied=True, reason='bench_unobserved',
                            world_decl=_DECL)
    slots = list(view.slots)
    _idx = (int(param.slot) - 1 if param.slot is not None
            else next((i for i, s in enumerate(slots)
                       if s is not None and s.kind == 'bookcard'), None))
    if _idx is None or not (0 <= _idx < len(slots)) \
            or slots[_idx] is None or slots[_idx].kind != 'bookcard':
        return LogicOutcome(applied=False, reason='bookcard_slot_missing')
    slots[_idx] = BenchSlot(kind='empty')
    _w(gs.bench, BenchView(slots=slots, capacity=view.capacity),
       'proj_open_item_clear')
    # S6 点击直弹登记(overlay-trigger 3.3;trigger-inventory §1.8:
    # 点书册卡「开启」直接弹五选一——统一入登记,kind = expert_invite)。
    from sr_od.application.currency_war.kernel.cw_overlay_register import (
        KIND_SCREEN_NAMES,
        register_screen_change,
    )
    register_screen_change(
        gs, 'expert_invite', KIND_SCREEN_NAMES['expert_invite'],
        source='s6_click@open_bookcard')
    return LogicOutcome(applied=True, world_decl=_DECL)

