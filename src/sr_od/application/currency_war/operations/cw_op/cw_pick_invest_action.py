"""投资选择确认链动作 op(:class:`CwActionPickInvestOp` 单类文件,
一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

投资环境/投资策略两屏共用 op(注册表两行同指):机械链同构,屏间差异
全部经 env 显式传入;机械链发出后按 param 类型机械分派自上报单口
(``report_action_pick_invest_strategy_param`` /
``report_action_pick_invest_env_param``)。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.pick_invest_env import (
    report_action_pick_invest_env_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.pick_invest_strategy import (
    report_action_pick_invest_strategy_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickInvestEnvParam,
    CwActionPickInvestStrategyParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    emit_overlay_confirm,
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickInvestOp(SrOperation):
    """投资选择确认链(投资环境/投资策略两屏共用 op,注册表两行同指;
    词表拆类后按 param 类型机械分派上报函数)。

    机械链同构:点选中位(safe_click bug#1 缓解)→ 固定等待 →
    确认(emit_overlay_confirm 机械交回)。屏间差异全部经 env 显式
    传入(定位点 = 决策半从各自建档 area 现算;确认钮中心 = 决策半
    从各自「按钮-确认」现取;裁决词 = '投资环境'/'投资策略'),op
    类体内零决策零读屏。

    **即时上报**(action_ops.md §1 用户裁定增补 2):机械链发出后
    立即按 param 类型自上报完整结果并写入 game state(策略 →
    ``gain_invest_strategy`` 整链;环境 → ``gain_invest_env`` 整链);
    无分步、无落地证据等待——确认未生效 = 代码 bug,归点击链可靠性
    治理。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext,
                 param: CwActionPickInvestStrategyParam | CwActionPickInvestEnvParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickInvestOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_invest', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡选中 → 选中动画等待 → 确认)+ 立即上报完整结果。"""
        action = self.param
        env = self.env
        op = env.op
        # 点卡选中(bug#1 缓解:click 前 mouse_move)→ 选中动画固定等待。
        safe_click(op, env.target, tag='cw-pick-invest')
        time.sleep(0.7)
        # 确认 + 机械交回(验证废除:不读屏判「overlay 关没关」;裁决词 =
        # 各屏入口标题,经 env.entry_keyword 传入)。
        env.round_result = emit_overlay_confirm(
            op, confirm_point=env.confirm,
            entry_keyword=env.entry_keyword, tag='cw-pick-invest')
        # 立即自上报完整结果(点完即写入 game state;session 与
        # game_state_from_ctx 同源自 ctx 取,kernel 禁自取上下文条款的
        # 调用方义务在此履行)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            _sig = ChannelSig(family='logic_action',
                              actor=type(self).__name__, mode='compute')
            _session = getattr(getattr(self.ctx, 'cw_match', None),
                               'session', None)
            if isinstance(action, CwActionPickInvestStrategyParam):
                report_action_pick_invest_strategy_param(
                    gs, action, _sig, session=_session)
            else:
                report_action_pick_invest_env_param(
                    gs, action, _sig, session=_session)
        return self.round_success('投资选择确认链已发(结果已即时上报)')
