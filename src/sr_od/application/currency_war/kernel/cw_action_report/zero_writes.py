"""零写动作族上报集中件(容器零写,等观察覆盖)。

族策略:视觉域/转场/选择类动作的容器写语义 = 零(逐类函数体 =
三行委托 :func:`_report_zero_write`),集中一文件不逐类开文件
(无逐类专覆盖内容);命名规约完备锁照样逐类点验收束 = 包级
``__getattr__`` 未命中落本模块。语义正本 = 各函数 docstring
(自 cw_game_state 逐字迁移)。

工具原子七类(冶金炉/特权赋予卡/拆装扳手/精密拆装扳手/员工投影仪/
完美投影仪/好运令牌)不在零写族:上报升格为容器写(机械执行直接
上报写容器),分步实现正本 = 同包 ``tool_use``;包级 ``__getattr__``
命名规约解析具名模块先于本模块。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    SCREEN_PREP_FRAME,
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
)
from sr_od.application.currency_war.kernel.cw_overlay_register import (
    consume_screen_change,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

# —— 转移动作声明常量(动作后果声明化详设 world-decl.md §2 表 #5/#9/
#    #10/#13-#17;画面档名字面值权威 = assets/game_data/screen_info 档名,
#    备战档复用容器常量;trigger 封闭集单一源 = sim 后端 advance 分派表
#    键集,值零新词沿用现役动作名)——

#(声明改底层屏):open_box 声明 next_screen 回归
# 备战底屏——武装箱选择画面的出现事实改由登记(kind = box_card,上报内
# register)承载;trigger='open_box' 保留(backend 开箱采样过程仍挂触发分派)。
_DECL_OPEN_BOX: WorldDecl = WorldDecl(
    next_screen=SCREEN_PREP_FRAME, trigger='open_box')
_DECL_PICK_BOX_CARD: WorldDecl = WorldDecl(
    next_screen=SCREEN_PREP_FRAME, trigger='pick_box_card')
_DECL_PICK_MEGASTAR: WorldDecl = WorldDecl(
    next_screen=SCREEN_PREP_FRAME, trigger='pick_megastar')
#: 纯转移选卡族共用(pick_partner/fortune/wish_trial/star_tome/
#: expert_invite:选卡落地 = 零写占位,真值归观察 → trigger = '' 纯画面
#: 转移,backend 仅按 next_screen 幂等交回,详设 §3 '' 行)。
_DECL_PREP_PURE: WorldDecl = WorldDecl(next_screen=SCREEN_PREP_FRAME,
                                       trigger='')

# —— 零写动作族(视觉域/转场/选择族:容器零写,消费真值归观察——
#    action-logic-state.md 正本申报;函数在场 = 命名规约完备锁对象,
#    调用方统一入口不必分型)——



def _report_zero_write(gs: GameState, param: Any, sig: ChannelSig,
                       note: str,
                       decl: WorldDecl | None = None) -> LogicOutcome:
    """零写动作统一实现(容器零写,等观察覆盖;applied=True = 动作受理,
    非拒绝)。转移类动作随附后果声明(构造义务 = 动作后果声明化迭代
    总纲 design.md §2.2 契约 2;非转移类 decl 缺省 None = 无声明可喂)。"""
    _validate_sig(sig, ('logic_action',))
    return LogicOutcome(applied=True, reason=note or 'zero_write',
                        world_decl=decl)



def report_action_open_box_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """开补给箱上报:开箱即腾席但占席事实归下一入口 heavy 实读(R7
    终结化零窗口),容器零写。applied 出口构造后果声明(open_box;
    武装箱选择画面出现;喂入与消费面 = ``cw_sim_ports.declare_world`` /
    sim 后端 advance)。点击直弹登记(
     §1.7:点备战栏箱位「开启」直接弹四选一——
    统一入登记,kind = box_card;声明 next_screen 语义回归底层屏归
    3.4 消费面,本模块不改声明)。"""
    from sr_od.application.currency_war.kernel.cw_overlay_register import (
        KIND_SCREEN_NAMES,
        register_screen_change,
    )
    register_screen_change(
        gs, 'box_card', KIND_SCREEN_NAMES['box_card'],
        source='s6_click@open_box')
    return _report_zero_write(gs, param, sig, 'zero_write(open_box)',
                              decl=_DECL_OPEN_BOX)


# 工具族七上报(report_action_furnace_use_param / report_action_privilege_card_
# use_param / report_action_wrench_use_param / report_action_precision_wrench_
# use_param / report_action_staff_projector_use_param / report_action_perfect_
# projector_use_param / report_action_lucky_token_use_param)= 容器写形态,
# 单一源 = 同包 tool_use(冶金炉采样池 sim 同源 + 投影仪走获得链);包级
# ``__getattr__`` 命名规约解析具名模块先于本模块,直接 import 零写委托
# 的旧消费面已改直取具名模块。



def report_action_open_shop_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """开商店上报:画面态周转(开店事实由 shop payload 观察
    写入),容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(open_shop)')



def report_action_pick_event_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """选事件选项上报(CwActionPickEventParam 参数载体 + sim 脚本动作;
    策略器不发出),容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_event)')


# report_action_pick_invest_param / report_action_pick_equip_param /
# report_action_pick_supply_param / report_action_pick_encounter_param
# 不在零写族(移具名模块):pick_equip / pick_supply = 分步→即时实现
# (同包具名模块);pick_invest 拆为
# pick_invest_strategy / pick_invest_env(即时上报形态:机械链发出即按
# 成功写完整结果,action_ops.md §1 增补 2;策略支整支走获得链
# gain_invest_strategy,环境支走 gain_invest_env);pick_encounter 在同包
# pick_encounter.py(发出即写 chosen_encounter,选择事实 =
# 动作执行时产生,用户裁定 2026-09-21)。包级 ``__getattr__`` 命名规约
# 解析具名模块先于本模块,直接 import 零写委托的旧消费面已改直取
# 具名模块。



def report_action_pick_megastar_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """盛会之星选择上报:容器零写。applied 出口构造后果声明(pick_megastar;
    交回备战,详设 world-decl.md §2 表 #10)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (两世界同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'megastar')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_megastar)',
                              decl=_DECL_PICK_MEGASTAR)



def report_action_pick_partner_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """列车同行伙伴选择上报:容器零写。applied 出口构造后果声明
    (纯转移交回备战,详设 world-decl.md §2 表 #13)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (两世界同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'partner')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_partner)',
                              decl=_DECL_PREP_PURE)



def report_action_pick_star_tome_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """星徽秘典选择上报:容器零写。applied 出口构造后果声明(纯转移
    交回备战,详设 world-decl.md §2 表 #16)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (两世界同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'star_tome')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_star_tome)',
                              decl=_DECL_PREP_PURE)



def report_action_pick_wish_trial_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """祈愿试炼选择上报:容器零写。applied 出口构造后果声明(纯转移
    交回备战,详设 world-decl.md §2 表 #15)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (两世界同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'wish_trial')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_wish_trial)',
                              decl=_DECL_PREP_PURE)



def report_action_pick_box_card_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """武装箱选择上报:容器零写。applied 出口构造后果声明(pick_box_card;
    选卡即终结交回备战,详设 world-decl.md §2 表 #9;装备入栏归 backend)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (两世界同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'box_card')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_box_card)',
                              decl=_DECL_PICK_BOX_CARD)



def report_action_pick_fortune_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """命运卜者强化三选一上报:容器零写。applied 出口构造后果声明
    (纯转移交回备战,详设 world-decl.md §2 表 #14)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (两世界同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'fortune')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_fortune)',
                              decl=_DECL_PREP_PURE)



def report_action_pick_expert_invite_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """专家邀请函选卡上报:容器零写(现金为王回金 = dict 确认族通道)。
    applied 出口构造后果声明(纯转移交回备战,详设 world-decl.md §2
    表 #17)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (两世界同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'expert_invite')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_expert_invite)',
                              decl=_DECL_PREP_PURE)



# —— 刷新建议三动作(遭遇/补给/投资):参数类在册(CW_ACTION_TYPES)、
#    生产动作发出面留守画面 op 刷新链,不经动作 op 自上报——本组函数零生产
#    调用方,在场 = 命名规约完备锁对象(test_cw_action_report_contract
#    遍历词表逐类断言「每动作恰一个上报函数」),禁当死代码删除。——



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
