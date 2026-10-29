"""货币战争动作上报:关店(report_action_close_shop_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留在 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。

**后果声明**(动作后果声明化详设 world-decl.md §2 表 #18):applied 出口
构造 ``WorldDecl``(trigger = ''——离屏写端 = 本上报,backend 活仅结束本次访问
当前节点屏;shop.md §5 关店回节点屏底层),转移事件广播随本动作单轨切换摘除。
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
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl


def report_action_close_shop_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """关店上报(结构离屏):shop payload 离屏(离屏写渠道 = obs 族,
    内部按 sig.actor 转造 obs 签名);离屏态 = 结构性离屏,零内容写。
    applied 出口构造后果声明(纯转移,next_screen = 备战档——商店模态
    的返回位恒备战底层(2026-10-29 呈现改造后开店 `_present_modal` 的
    `_return_screen` 恒备战),旧推导 ``node_screen_now`` 的位面首例外
    (返回位面过渡屏)对本场景失真——位面过渡屏只在窗起点存在、早被
    点掉,关店恒回备战)。

    消费面 = ``CwActionCloseShopOp`` 执行体自上报(幂等已关/点击已发两
    出口同调,关店时点清场);sim 后端消费 = 声明喂入
    (``cw_sim_ports.declare_world``)驱动 advance 纯转移分支结束本次访问。
    """
    _validate_sig(sig, ('logic_action',))
    if gs.shop.value is not None:
        _off_sig = ChannelSig(family='obs', actor=sig.actor,
                              mode='read', group_id=sig.group_id)
        gs.leave_screen(gs.shop, sig=_off_sig)
    return LogicOutcome(
        applied=True,
        world_decl=WorldDecl(next_screen=SCREEN_PREP_FRAME, trigger=''))
