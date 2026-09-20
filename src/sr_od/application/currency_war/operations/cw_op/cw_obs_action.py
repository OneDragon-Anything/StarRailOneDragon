"""环内重观察动作 op(CwActionObsOp):策略发射 :class:`CwActionObsParam`
→ 宿主画面 op 观察链重跑 + 漏斗直写容器(= 重新观察上报),决策环原地
续跑(不交回外循环)。

与观察 node 的分界:观察 node = 访问入口全段(清场/开商店收起/接管补采/
纯观察审计族);本 op = 访问内最小重观察(仅 heavy 漏斗直写),入口专属
段不在辖域。帧代次 'full' 标注归决策循环写点(与逐动作 'none' 标注同点
分派,帧代次写点单处)。

事件 overlay 在场 = 抛 :class:`CwObsOverlayBail` 交回外循环重分发
(画面识别与路由归外循环,环内不消化 overlay;捕获点 =
``cw_screen_prep.act``,控制流异常先例 = StopBrakeShortCircuit)。

⚠️ 读屏点规范的在册例外:op-layer §1.1「显式读屏只在观察 node」自本 op
起增设动作通道例外——决策环内仅策略显式发射 CwActionObs 才触发读屏,
其余路径仍零读屏(循环内零读屏不变量改述见 flow/action_exec.md §3)。
非终结。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_obs_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionObsParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwObsOverlayBail(RuntimeError):
    """环内重观察发现事件 overlay → 交回外循环重分发的控制流异常。

    抛出点 = :class:`CwActionObsOp` 执行体(重观察回执 event_overlay
    非空);捕获点 = ``cw_screen_prep.act`` 决策循环(交回语义与观察 node
    的 overlay 早退一致:无计数,round_success 交外环)。"""
    def __init__(self, overlay_tag: str) -> None:
        RuntimeError.__init__(self, f'重观察见事件overlay({overlay_tag})')
        self.overlay_tag = overlay_tag


class CwActionObsOp(SrOperation):
    """环内重观察:宿主 heavy 观察链重跑(漏斗直写容器 = 上报),
    零点击零拖拽;落地/对账语义 = 观察边界本体(观察赢)。非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionObsParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionObsOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='reobserve', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """重观察执行体:宿主重观察(漏斗直写容器)→ 自上报(零写占位,
        动作回执统一形态)→ overlay 在场 = bail 交回外循环。

        宿主能力解析:``env.op`` 必须提供 ``reobserve_in_visit``(现役唯一
        宿主 = 备战画面 op CwScreenPrep);缺席 = 决策域未接线重观察通道
        (策略器在无能力域发射 CwActionObs = 策略器 bug)响亮暴露。
        """
        host = self.env.op
        reobserve = getattr(host, 'reobserve_in_visit', None)
        if not callable(reobserve):
            raise AssertionError(
                f'[cw-action][obs] 发射域无重观察能力:env.op='
                f'{type(host).__name__} 未接线 reobserve_in_visit'
                '(CwActionObs 现役只在备战决策环可用;非法发射 = 策略器 '
                'bug,响亮暴露)')
        obs = reobserve()
        # —— 自上报(机械执行后;零写族:容器更新通道 = 观察漏斗本体)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_obs_param(
                gs, self.param,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        if obs.event_overlay is not None:
            # 画面路由归外循环:overlay 在场环内不消化,交回重分发
            #(观察 node 同语义早退;不计数)。
            raise CwObsOverlayBail(obs.event_overlay)
        detail = ('环内重观察完成(漏斗直写容器;决策环原地续跑,'
                  f'shop_open={obs.shop_open})')
        log.info(f'[cw][obs] {detail}')
        return self.round_success(detail)
