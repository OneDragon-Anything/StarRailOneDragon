"""货币战争动作上报:遭遇节点选择(report_action_pick_encounter_param)。

**发射即写**(迭代 2026-09-21-event-refresh-unify-supply-pick design
§2.4;用户裁定 2026-09-21:选卡派发即终结,选择事实 = 动作执行时产生):
``CwActionPickEncounterOp`` 确认点击后立即写 ``chosen_encounter``——
写端自画面 op 重入裁决点迁入(op-layer §2.2 动作事实边界遭遇例外改判,
先例 = 投资域 chosen 迁获得链的显式收窄条款;zero_writes 零写族语义
不容容器写函数留守,照 pick_supply 升格先例迁具名模块)。

值组装 = 容器 ``encounter`` payload 槽 ``options[param.idx]``(与策略
决策同源,param 零扩字段);payload 离屏 / idx 越界 = 观察层失约形态,
留证不写(None 保持「无记录」,防盲选固化假值——原画面 op 守卫口径
平移)。**暂态假值窗申报**:确认未生效时容器已持发射意图值,由外循环
重派覆盖自愈;奖励兑现回调对该窗的消费防线 = 兑现后清 chosen(单次
消费,见 ``cw_encounter_selection.claim_encounter_reward``)。

动作上报函数族拆分件(每动作一文件;族规约 = 包 ``cw_action_report.
__init__`` docstring)。本包 → 容器单向依赖。
"""
from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _emit_defect,
    _validate_sig,
)

_PRODUCER: str = 'CwActionPickEncounterOp'


def report_action_pick_encounter_param(gs: GameState, param: Any,
                                       sig: ChannelSig) -> LogicOutcome:
    """遭遇节点选择上报(发射即写:确认点击后立即写 ``chosen_encounter``)。

    值 = payload 槽所选卡 ``(难度档, 奖励文本 join)``;槽离屏 / idx 越界
    = 缺陷留证不写(fail-closed)。出参 applied=False = 留证未写(非拒绝)。
    """
    _validate_sig(sig, ('logic_action',))
    payload = gs.encounter.value
    idx = int(getattr(param, 'idx', -1))
    options = list(payload.options) if payload is not None else []
    if payload is None or not (0 <= idx < len(options)):
        # 槽离屏/越界 = 观察层失约或盲选 fallback:禁猜,留证不写
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
    return LogicOutcome(applied=True, reason='chosen_written')
