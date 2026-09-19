"""零写动作族上报集中件(容器零写,等观察覆盖)。

族策略:视觉域/转场/选择类动作的容器写语义 = 零(逐类函数体 =
三行委托 :func:`_report_zero_write`),集中一文件不逐类开文件
(无逐类专辖内容);命名规约完备锁照样逐类点验收口 = 包级
``__getattr__`` 未命中落本模块。语义正本 = 各函数 docstring
(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
)

# —— 零写动作族(视觉域/转场/选择族:容器零写,消费真值归观察——
#    action-logic-state.md 正本申报;函数在场 = 命名规约完备锁对象,
#    调用方统一入口不必分型)——



def _report_zero_write(gs: GameState, param: Any, sig: ChannelSig,
                       note: str) -> LogicOutcome:
    """零写动作统一实现(容器零写,等观察覆盖;applied=True = 动作受理,
    非拒绝)。"""
    _validate_sig(sig, ('logic_action',))
    return LogicOutcome(applied=True, reason=note or 'zero_write')



def report_action_open_box_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """开补给箱上报:开箱即腾席但占席事实归下一入口 heavy 实读(R7
    终结化零窗口),容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(open_box)')



def report_action_furnace_use_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """冶金炉上报:消耗/变换 = 视觉域逻辑态(容器零写,随机面观察收口)。"""
    return _report_zero_write(gs, param, sig, 'zero_write(furnace_use)')



def report_action_privilege_card_use_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """特权赋予卡上报:变换确定面归观察收口,容器零写(工具 −1 = 视觉域)。"""
    return _report_zero_write(gs, param, sig, 'zero_write(privilege_card_use)')



def report_action_wrench_use_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """拆装扳手上报:装备归属面回区 = 视觉域,容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(wrench_use)')



def report_action_precision_wrench_use_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """精密拆装扳手上报:同拆装扳手(无限次用),容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(precision_wrench_use)')



def report_action_staff_projector_use_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """员工投影仪上报:复制体出现 = 观察收口,容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(staff_projector_use)')



def report_action_perfect_projector_use_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """完美投影仪上报:同员工投影仪,容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(perfect_projector_use)')



def report_action_lucky_token_use_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """好运令牌上报:获得面 = 观察收口,容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(lucky_token_use)')



def report_action_open_shop_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """开商店上报:画面态周转(开店事实由 shop payload 观察
    写入),容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(open_shop)')



def report_action_pick_event_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """选事件选项上报(kernel decide_event 返回载体 + sim 脚本动作;
    策略器不发射),容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_event)')



def report_action_pick_encounter_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """遭遇节点选择上报:选择事实 = 画面 handler 消费链,容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_encounter)')



def report_action_pick_supply_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """补给节点选择上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_supply)')



def report_action_pick_invest_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """投资选择上报:容器零写(投资效果 = 授予闩/观察域)。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_invest)')



def report_action_pick_megastar_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """盛会之星选择上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_megastar)')



def report_action_pick_partner_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """列车同行伙伴选择上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_partner)')



def report_action_pick_planner_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """骇入策划选择上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_planner)')



def report_action_pick_star_tome_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """星徽秘典选择上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_star_tome)')



def report_action_pick_wish_trial_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """祈愿试炼选择上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_wish_trial)')



def report_action_pick_box_card_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """武装箱选择上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_box_card)')



def report_action_pick_fortune_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """命运卜者强化三选一上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_fortune)')



def report_action_pick_expert_invite_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """专家邀请函选卡上报:容器零写(现金为王回金 = dict 确认族通道)。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_expert_invite)')



def report_action_pick_equip_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """选择装备三选一上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_equip)')



def report_action_refresh_node_options_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """遭遇刷新建议上报:刷新链 = 同访问重决策,容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(refresh_node_options)')



def report_action_refresh_supply_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """补给刷新建议上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(refresh_supply)')



def report_action_refresh_invest_cards_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """投资逐卡刷新建议上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(refresh_invest_cards)')



def report_action_hold_frame_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """空发射帧上报(等待帧非动作,不进执行链;函数在场 = 命名规约
    完备锁全集覆盖),容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(hold_frame)')
