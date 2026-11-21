"""货币战争动作上报:主角光环选择记账(report_action_aura_select_param)。

主角光环 = 位面末 BOSS 战前的强制选择(确认后本位面主角绑定生效,
光环随位面重选)。选择落地记录归动作上报(game-state.md §3:
chosen/落地类不进观察上报)——写端位置 = ``CwScreenAuraSelect`` 判效
双锚过(回备战 ∧ 光环屏标题 miss)后:此时三步链(选卡/拖主角/微距
确认)已完成,拖拽落点 = 末次成功拖拽的抓点卡(判效 miss 换抓点重试
语义下,重试漂移落点如实记账,见 op 侧 ``_grab_point_for`` 换抓点序)。

值域 = 前排物理槽 1 基(坐标系申报住 ``aura_slot`` 字段注释,单一源)。
抓点落后排(op 判效重试极端形态)= 越本域值域,op 侧跳写不调本函数
(交下一备战帧观察收尾);本函数对域外值显式报错(值域守卫,禁静默)。

动作上报函数族拆分件(每动作一文件;族规约 = 包 ``cw_action_report.
__init__`` docstring)。本包 → 状态容器单向依赖。主角光环选择非词表
``CwActionXxxParam`` 类(画面 op 内嵌动作),不在 CW_ACTION_TYPES 完备
测试覆盖域。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_game_state import (
    DEPLOYED_FRONT_CAPACITY_DEFAULT,
    ChannelSig,
    GameState,
    _validate_sig,
)

_PRODUCER: str = 'CwScreenAuraSelect'


def report_action_aura_select_param(gs: GameState, slot: int, *,
                                    sig: ChannelSig) -> None:
    """主角光环选择记账:光环归属前排槽写 ``aura_slot``(逻辑态)。

    Args:
        gs: 局内状态容器。
        slot: 光环归属前排物理槽号(1 基,1..前排容量);域外 = ValueError
            (值域守卫显式报错,禁钳位禁静默——调用方漂移形态由 op 侧
            跳写闸拦截,到达本函数的域外值 = 调用方 bug)。
        sig: 渠道②签名(logic_action;actor = 调用 op)。
    """
    _validate_sig(sig, ('logic_action',))
    slot = int(slot)
    if not 1 <= slot <= DEPLOYED_FRONT_CAPACITY_DEFAULT:
        raise ValueError(
            f'[cw-aura] aura_slot 值域外:{slot}(合法 = 1..'
            f'{DEPLOYED_FRONT_CAPACITY_DEFAULT} 前排物理槽;禁静默收下)')
    gs.write_logic(gs.aura_slot, slot, produced_by=_PRODUCER,
                   evidence='aura_select_verify_passed', sig=sig)
