"""货币战争动作上报:主角光环选择记账(report_action_aura_select_param)。

主角光环 = 位面末 BOSS 战前的强制选择(确认后本位面主角绑定生效,
光环随位面重选)。选择落地记录归动作上报(game-state.md §3:
chosen/落地类不进观察上报)——写端位置 = ``CwScreenAuraSelect`` 判效
双锚过(回备战 ∧ 光环屏标题 miss)后:此时三步链(选卡/拖主角/微距
确认)已完成,拖拽落点 = 末次成功拖拽的抓点卡(判效 miss 换抓点重试
语义下,重试漂移落点如实记账,见 op 侧 ``_grab_point_for`` 换抓点序)。

两字段同拍写(同一选择落地事件的两个事实):
- ``aura_slot`` = 光环归属前排槽(值域 = 前排物理槽 1 基,坐标系申报住
  ``aura_slot`` 字段注释,单一源)。抓点落后排(op 判效重试极端形态)=
  越本域值域,op 侧跳写不调本函数(交下一备战帧观察收尾);本函数对域外值
  显式报错(值域守卫,禁静默)。
- ``chosen_aura`` = 选中的光环标准名,按 ``aura_idx``(光环卡序号,0 = 左)
  取自 ``aura_select_opts`` 名单单一源(标准化产物)——上报层零名字转换
  (game-state.md §2 标准化纪律);名单缺席 / 序号越界 = AssertionError
  (观察未上报即选择落地 = 调用方 bug)。消费点 = 上阵规模占用派生
  (``cw_game_state.team_size_used_of``:光环代价按名查),不记账则超限态
  算不出来。

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
                                    aura_idx: int, sig: ChannelSig) -> None:
    """主角光环选择记账:光环归属前排槽写 ``aura_slot``、选中光环名写
    ``chosen_aura``(两字段同拍,逻辑态)。

    Args:
        gs: 局内状态容器。
        slot: 光环归属前排物理槽号(1 基,1..前排容量);域外 = ValueError
            (值域守卫显式报错,禁钳位禁静默——调用方漂移形态由 op 侧
            跳写闸拦截,到达本函数的域外值 = 调用方 bug)。
        aura_idx: 选中的光环卡序号(0 = 左 / 1 = 右,与 ``aura_select_opts``
            同序;名字按序号取自该名单,本函数零名字转换)。名单缺席 /
            序号越界 = AssertionError;两字段任一校验失败 = 整笔零写。
        sig: 渠道②签名(logic_action;actor = 调用 op)。
    """
    _validate_sig(sig, ('logic_action',))
    slot = int(slot)
    if not 1 <= slot <= DEPLOYED_FRONT_CAPACITY_DEFAULT:
        raise ValueError(
            f'[cw-aura] aura_slot 值域外:{slot}(合法 = 1..'
            f'{DEPLOYED_FRONT_CAPACITY_DEFAULT} 前排物理槽;禁静默收下)')
    opts = list(gs.aura_select_opts.value or [])
    aura_idx = int(aura_idx)
    if not 0 <= aura_idx < len(opts) or not opts[aura_idx]:
        raise AssertionError(
            f'[cw-aura] chosen_aura 取名失败:aura_select_opts={opts!r} '
            f'idx={aura_idx}(观察未上报即选择落地 / 序号越界 = 调用方 bug,'
            f'禁静默)')
    gs.write_logic(gs.aura_slot, slot, produced_by=_PRODUCER,
                   evidence='aura_select_verify_passed', sig=sig)
    gs.write_logic(gs.chosen_aura, str(opts[aura_idx]), produced_by=_PRODUCER,
                   evidence='aura_select_verify_passed', sig=sig)
