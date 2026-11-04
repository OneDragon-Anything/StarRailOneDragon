"""货币战争动作上报:出战(report_action_start_battle_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。状态容器、写入口与观察
写端留在 ``kernel/cw_game_state``,本包 → 状态容器单向依赖。
语义权威版本 = 函数 docstring(自 cw_game_state 逐字迁移)。

**后果声明**(动作后果声明化迭代,详设 world-decl.md §2 表 #3):applied
出口构造 ``WorldDecl``——常规出口 trigger = ``battle_resolve``、
``next_screen`` = 结算屏(权威 = screens/prep.md §5 出战终结 + sim
``_resolve_battle`` 呈现);免战跳过出口 trigger = ``battle_skip``、
``next_screen`` = 跳过后下一节点窗稳态屏(:func:`_skip_next_screen`,
权威 = screens/prep.md §5 免战跳过直达下一节点),转移事件广播随本
动作单轨切换摘除。
"""

from __future__ import annotations

from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    _NODE_PLANE_TRANSITION_SCREEN,
    SCREEN_BOSS_BRIEFING,
    SCREEN_PREP_FRAME,
    SCREEN_SETTLE,
    SCREEN_SHOP_PANEL,
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
    effective_node_pos,
    game_state_of,
    report_node_advance,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    PLANE_NODE_TABLES,
    sequence_next,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

#: 出战声明的推进分派类别(详设 §2 表 #3;封闭集单一源 = sim 后端
#: advance 分派表键集,值零新词沿用归并过程名)。
_DECL_TRIGGER: str = 'battle_resolve'

#: 免战跳过声明的推进分派类别(免战牌建模;封闭集单一源同上,与 sim
#: ``ADVANCE_TRIGGER_KINDS`` 两侧同批扩)。
_SKIP_DECL_TRIGGER: str = 'battle_skip'


def _skip_next_screen(gs: GameState) -> str:
    """免战跳过声明的 ``next_screen`` 推导(跳过后**下一节点窗**稳态屏)。

    规则与 :func:`cw_game_state.window_stable_screen_now` 同族,但求值
    对象 = 被跳节点的后继序位——上报构造时点生效序位仍是被跳节点,不能
    直调该函数。序 = 生效序位 → :func:`cw_node_schedule.sequence_next`
    后继 → 位面首(``pos[0] > 1 and pos[1] == 1`` 全式,与
    ``window_stable_screen_now`` 同式)= 位面过渡屏;弹窗型节点(补给/
    遭遇/BOSS 简报)= 节点弹窗档;battle/reward = 开商店档;1-1 = 备战档。
    序列权威源 = 场字段 ``node_seq_by_plane`` 现值(None 回退默认表,与
    ``window_stable_screen_now`` 逐字同源,禁直查默认表——改节点序列
    环境下声明预测与呈现才真同源)。

    后继 None / 表外位面 / 槽越界 = 局终事件式空串(消费端 = sim
    ``_on_node_advance_terminal`` 终局分支,禁任何 SETTLE 类回退;
    跳过辖域默认仅普通战斗、三位面均 boss 收尾,现规则集不可达,辖域
    校准扩入位面末节点时本臂转可达)。
    """
    pos = effective_node_pos(gs)
    nxt = (sequence_next(pos, gs.node_seq_by_plane.value)
           if pos is not None else None)
    if nxt is None:
        return ''
    seqs = gs.node_seq_by_plane.value
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    seq = tables.get(nxt[0])
    if seq is None or nxt[1] > len(seq):
        return ''
    if nxt[0] > 1 and nxt[1] == 1:
        return _NODE_PLANE_TRANSITION_SCREEN
    kind = seq[nxt[1] - 1]
    if kind == 'supply':
        return '货币战争-补给'
    if kind == 'encounter':
        return '货币战争-遭遇节点'
    if kind == 'boss':
        return SCREEN_BOSS_BRIEFING
    if nxt == (1, 1):
        return SCREEN_PREP_FRAME
    return SCREEN_SHOP_PANEL


def report_action_start_battle_param(gs: GameState, param: Any, sig: ChannelSig,
                                     session: object = None,
                                     skip_substate: bool = False) -> LogicOutcome:
    """出战上报:hp/gold/streak 由结算屏观察覆盖接管,唯一逻辑推进 =
    免战牌跳过递减(上报时递减,非「验证落地后」;标记由出战 op 上报,
    递减 best-effort,未登记 → consume_use 返 None 零动作)。
    applied 出口构造后果声明喂入 ``cw_sim_ports.declare_world`` / sim
    后端 advance:常规出口 = (结算屏, battle_resolve);免战跳过出口 =
    (下一节点窗稳态屏, battle_skip)——跳过事实走声明通道(裁决点 1
    默认案 A),声明按 op 点击事实分支、不随递减簿记成败回改(递减缺席
    = 状态副本照跳、簿记缺失,回改会让 sim 照打战斗与实机分叉)。

    **补给节点分支**(2026-10-29 流程模型对齐):supply 节点出战 =
    完成节点(无战斗无结算屏,流程模型单一源 =
    ``docs/game/currency_war/research/screen_flow_timing.md`` 口述流程
    模型节——补给选完回备战,出战即进下一回合)→ 转
    :func:`report_node_advance`(trigger = ``supply_finish``)按终结动作
    推进,声明由该入口构造(node_advance,下一画面按其推导);补给
    节点不在免战跳过辖域,分支先于跳过声明构造,二者不共现。
    """
    _validate_sig(sig, ('logic_action',))
    node = gs.node.value
    if node is not None and node.kind == 'supply':
        return report_node_advance(gs, trigger='supply_finish')
    if skip_substate:
        decl = WorldDecl(next_screen=_skip_next_screen(gs),
                         trigger=_SKIP_DECL_TRIGGER)
    else:
        decl = WorldDecl(next_screen=SCREEN_SETTLE, trigger=_DECL_TRIGGER)
    if skip_substate and session is not None:
        from sr_od.application.currency_war.kernel.cw_investments import (
            STRATEGY_EFFECTS,
        )
        _spec = STRATEGY_EFFECTS.get('免战牌')
        if _spec is not None:
            _left = game_state_of(session).effects.consume_use(_spec.id)
            if _left is not None:
                log.info('[cw][battle] 免战牌跳过上报 → 次数递减(余 %s)', _left)
                return LogicOutcome(
                    applied=True,
                    reason=f'remaining_uses→{_left}(跳过上报递减)',
                    world_decl=decl)
    return LogicOutcome(applied=True, world_decl=decl)
