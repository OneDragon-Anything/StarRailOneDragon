"""货币战争动作上报:遭遇节点选择(report_action_pick_encounter_param)。

**发出即写**(迭代 2026-09-21-event-refresh-unify-supply-pick design
§2.4;用户裁定 2026-09-21:选卡点击发出后即结束本次访问,选择事实 = 动作执行时产生):
``CwActionPickEncounterOp`` 确认点击后立即写 ``chosen_encounter``——
写端位置 = op-layer §2.2 动作事实边界(遭遇例外改判,
先例 = 投资域 chosen 迁获得链的显式收窄条款;zero_writes 零写族语义
不容容器写函数留在,照 pick_supply 升格先例迁具名模块)。

值组装 = 容器 ``encounter`` payload 槽 ``options[param.idx]``(与策略
决策同源,param 零扩字段);payload 离屏 / idx 越界 = 观察层失约形态,
留存证据不写(None 保持「无记录」,防盲选固化假值——原画面 op 守卫口径
平移)。**暂态假值窗申报**:确认未生效时容器已持发出意图值,由外循环
重派覆盖自愈;奖励兑现回调对该窗的消费防线 = 兑现后清 chosen(单次
消费,见 ``cw_encounter_selection.claim_encounter_reward``)。

动作上报函数族拆分件(每动作一文件;族规约 = 包 ``cw_action_report.
__init__`` docstring)。本包 → 容器单向依赖。

**后果声明**(动作后果声明化迭代,详设 world-decl.md §2 表 #4):applied
出口构造 ``WorldDecl``(trigger = ``pick_encounter``;``next_screen`` =
商店档——2026-10-29 流程模型对齐:遭遇选完 overlay 关闭回备战,游戏自动
弹出商店,遭遇战由出战动作开打(流程模型单一源 =
``docs/game/currency_war/research/screen_flow_timing.md`` 口述流程模型
节,#14);旧「选档落地即该遭遇战结算」语义(battle_resolve 直达)随
sim 世界模型呈现改造废止),
转移事件广播随本动作单轨切换摘除。
"""
from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    SCREEN_SHOP_PANEL,
    ChannelSig,
    GameState,
    LogicOutcome,
    _emit_defect,
    _validate_sig,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

_PRODUCER: str = 'CwActionPickEncounterOp'

#: 遭遇声明的推进分派类别(封闭集单一源 = sim 后端
#: advance 分派表键集;选完落点 = 关遭遇模态回备战并自动弹店)。
_DECL_TRIGGER: str = 'pick_encounter'


def report_action_pick_encounter_param(gs: GameState, param: Any,
                                       sig: ChannelSig) -> LogicOutcome:
    """遭遇节点选择上报(发出即写:确认点击后立即写 ``chosen_encounter``)。

    值 = payload 槽所选卡 ``(难度档, 奖励文本 join)``;槽离屏 / idx 越界
    = 缺陷留存证据不写(fail-closed)。出参 applied=False = 留存证据未写(非拒绝)。
    applied 出口构造后果声明(pick_encounter;喂入与消费面 =
    ``cw_sim_ports.declare_world`` / sim 后端 advance)。
    """
    _validate_sig(sig, ('logic_action',))
    payload = gs.encounter.value
    idx = int(getattr(param, 'idx', -1))
    options = list(payload.options) if payload is not None else []
    if payload is None or not (0 <= idx < len(options)):
        # 槽离屏/越界 = 观察层失约或盲选 fallback:禁猜,留存证据不写
        #(防把盲选固化成假值;None = 「无记录」)。
        _emit_defect(field_name='chosen_encounter',
                     expected='encounter payload + idx in range',
                     actual=f'payload={payload is not None} idx={idx}',
                     evidence='pick_encounter_report',
                     sig=sig, kind='pick_encounter_chosen_unresolved')
        return LogicOutcome(applied=False, reason='chosen_unresolved')
    _opt = options[idx]
    gs.write_logic(gs.chosen_encounter,
                   (int(_opt.difficulty), '/'.join(_opt.rewards)),
                   produced_by=_PRODUCER, sig=sig)
    return LogicOutcome(
        applied=True, reason='chosen_written',
        world_decl=WorldDecl(next_screen=SCREEN_SHOP_PANEL,
                             trigger=_DECL_TRIGGER))
