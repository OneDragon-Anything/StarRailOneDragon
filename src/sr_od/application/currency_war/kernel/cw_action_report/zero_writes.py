"""零写动作族上报集中件(容器零写,等观察覆盖)。

族策略:视觉域/转场/选择类动作的容器写语义 = 零(逐类函数体 =
三行委托 :func:`_report_zero_write`),集中一文件不逐类开文件
(无逐类专辖内容);命名规约完备锁照样逐类点验收口 = 包级
``__getattr__`` 未命中落本模块。语义正本 = 各函数 docstring
(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from one_dragon.utils.log_utils import log
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



# report_action_pick_invest_param / report_action_pick_equip_param /
# report_action_pick_supply_param 已迁出零写族(银狼闭环迭代 design.md
# §2.3 与 §2.2 确定性通道宿主迁移):分步实现正本 = 同包 pick_invest /
# pick_equip / pick_supply(两相语义,效果腿绑「overlay 已关」落地证据
# 闩);包级 ``__getattr__`` 命名规约解析具名模块先于本模块,直接 import
# 零写委托的旧消费面已随迁改直取具名模块。



def report_action_pick_megastar_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """盛会之星选择上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_megastar)')



def report_action_pick_partner_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """列车同行伙伴选择上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_partner)')



def report_action_pick_planner_param(gs: GameState, param: Any, sig: ChannelSig,
                                     *, leg_type: str = '',
                                     norm_item: str = '') -> LogicOutcome:
    """骇入策划选择上报(发射相 = 仅登记意图遥测,容器零写;银狼闭环
    design.md §2.1①)。

    - ``leg_type``/``norm_item`` = 决策半腿型载荷(classify_planner_leg
      产物,经 OverlayPickExecEnv 随发射透传);意图遥测 = 日志行(行级
      台账无「意图」行型,不强造——同 pick_invest 申报);
    - **效果腿不在发射相应用**:幂等 = 证据闩,效果在「overlay 已关」
      落地证据(重入裁决出口)应用一次——应用宿主 =
      cw_screen_yinlang.apply_pick_planner_landing(本批宿主,记账函数
      迁入 kernel/cw_action_report/pick_planner.py = 推广批,
      design §2.1⑤);
    - 容器零写,消费真值归观察(原零写委托语义保持)。"""
    _validate_sig(sig, ('logic_action',))
    log.info('[cw-pick-planner] 意图遥测:leg_type=%s norm_item=%s idx=%s'
             '(效果腿候证据闩)', leg_type or '?', norm_item or '',
             getattr(param, 'idx', '?'))
    return LogicOutcome(applied=True, reason='intent_only')



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



def report_action_refresh_node_options_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """遭遇刷新建议上报:刷新链 = 同访问重决策,容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(refresh_node_options)')



def report_action_refresh_supply_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """补给刷新建议上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(refresh_supply)')



def report_action_refresh_invest_cards_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """投资逐卡刷新建议上报:容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(refresh_invest_cards)')



def report_action_obs_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """重观察上报(CwActionObsParam):本动作的容器更新通道 = 观察
    漏斗本体(宿主 heavy 观察链直写,观察边界对账),动作上报面零写;
    函数在场 = 命名规约完备锁对象 + op 自上报回执统一形态。"""
    return _report_zero_write(gs, param, sig, 'zero_write(obs)')
