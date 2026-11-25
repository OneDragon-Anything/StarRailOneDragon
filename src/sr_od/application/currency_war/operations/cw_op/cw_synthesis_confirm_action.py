"""确认合成动作 op(CwActionSynthesisConfirmOp):按坐标点一次合成确认浮层上的 ✓。

合成确认浮层是备战画面的子态(不是独立画面):框架在装备栏内找到成对的 ✕/✓ 定位
浮层,把按钮中心写进状态容器 ``synthesis_overlay`` 字段,策略器据此发出本动作。本 op
只负责把这一下点出去——零读屏、零验证、零重试:点击落没落地由下一帧观察判定(点击
没生效时下一帧仍读到浮层,会再进一次这个动作;连续未收起的出口 = 备战画面 op 的
处置计数)。

机械执行后 op 内直调自己的上报函数 ``report_action_synthesis_confirm_param``
(零写:状态容器不写任何字段,库存真值归下一帧观察)。

终结动作:点完返回主循环重新观察——浮层收起后的备战画面要全量重读。两段等待分开:
op 内等待 = 浮层收起动画,终结口等待 = 访问结束后的余量。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_synthesis_confirm_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
    note_action_receipt,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionSynthesisConfirmParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv
    from sr_od.operations.sr_operation import SrOperation

#: op 内等待(秒):浮层收起动画。点完到确认消失实测约 3 秒,另留 1 秒余量——等得太短,
#: 收起动画中段的下一帧会再点一次。
COLLAPSE_WAIT_S: float = 3.0

#: 画面尺寸(点击坐标守卫的上界;项目运行基准 1080p)。
_SCREEN_WIDTH: int = 1920
_SCREEN_HEIGHT: int = 1080

_OP_NAME: str = 'CwActionSynthesisConfirmOp'


def _note_receipt(op: SrOperation, cx: int, cy: int) -> None:
    """直接调用时的回执(唯一写点 = kernel ``note_action_receipt``;reason = '' =
    点击已正常发出)。

    经备战执行器分派时执行器已经写了唯一一条回执,op 内不重复写——判据 = ``env`` 或
    ``env.executor`` 缺席;没有对局上下文时跳过(kernel 口同款)。回执是动作事实的簿记,
    不是验证。
    """
    env = getattr(op, 'env', None)
    if env is not None and getattr(env, 'executor', None) is not None:
        return
    try:
        gs = game_state_from_ctx(getattr(op, 'ctx', None))
        if gs is None:
            return
        note_action_receipt(gs, op=_OP_NAME, reason='',
                            detail=f'点击({cx},{cy})', screen='货币战争-备战',
                            actor=_OP_NAME)
    except Exception as e:  # noqa: BLE001  回执失败不阻塞动作链
        log.warning('[cw][receipt] 确认合成回执写入失败(不阻塞): %s', e)


class CwActionSynthesisConfirmOp(CwOperation):
    """确认一次装备合成:点掉备战画面上的合成确认浮层,合成产物入库。
    起点:货币战争-备战画面,合成确认浮层在场;终点:仍在备战画面,浮层收起。
    副作用:消耗两件合成材料,产物入库,不可逆。

    :param param: 确认合成动作参数。cx/cy = 浮层上 ✓ 按钮中心的 1080p 画面坐标
        (直接调用时取当帧 extras 的 ``synthesis_overlay.ok_xy``);字段语义与取值时机
        见词表类 docstring。
    :param env: 执行环境。经备战执行器分派时传入;直接调用时缺省 None(回执的写法靠它
        区分:执行器分派 = 执行器写回执,直接调用 = op 自己写)。
    """

    #: 终结动作(浮层收起后的备战画面要全量重读,返回主循环)。
    terminal = True

    #: 终结口等待(秒):访问结束后的余量,加在 op 内等待之后。
    terminal_wait = 1.0

    def __init__(self, ctx: SrContext, param: CwActionSynthesisConfirmParam,
                 env: PrepExecEnv | None = None):
        CwOperation.__init__(self, ctx, op_name=_OP_NAME,
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='synthesis_confirm', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """确认合成:坐标守卫 → 点 ✓ 一次 → 光标移到装备栏外 → 等浮层收起。"""
        action: CwActionSynthesisConfirmParam = self.param
        cx, cy = int(action.cx), int(action.cy)
        if not (0 <= cx < _SCREEN_WIDTH and 0 <= cy < _SCREEN_HEIGHT):
            # 坐标违法 = 决策逻辑 bug 或调用方传错,守卫断言响亮暴露,零点击。
            raise AssertionError(
                f'CwActionSynthesisConfirmParam 坐标越界({cx},{cy});'
                f'画面 0-{_SCREEN_WIDTH - 1} × 0-{_SCREEN_HEIGHT - 1},零点击')
        target = Point(cx, cy)
        if cw_sim_ports.mechanical_io_allowed():
            self.ctx.controller.mouse_move(target)   # 防吞点击(先例 = 开箱动作 op)
            self.ctx.controller.click(target)
            _note_receipt(self, cx, cy)   # 调用点在点击发出之后
            # 点击已发出,收起动画期间光标在哪都不影响结果;先移开,才不会在动画中途
            # 悬停到装备上——✓ 中心正对着装备栏右列下一行的格子,不移开的话浮层收起
            # 后会弹出装备详情浮窗,那个浮窗框架接不住。
            self.park_cursor(before_wait=0.0, after_wait=0.1)
            time.sleep(COLLAPSE_WAIT_S)
        # else sim:机械分支静默跳过(sim 不呈现这个浮层),自上报照走。
        gs = game_state_from_ctx(self.ctx)
        world_decl = None
        if gs is not None:
            outcome = report_action_synthesis_confirm_param(
                gs, action,
                ChannelSig(family='logic_action', actor=type(self).__name__,
                           mode='compute'))
            world_decl = outcome.world_decl
            cw_sim_ports.declare_world(world_decl)
        detail = f'确认合成:已点 ✓({cx},{cy})'
        log.info('[cw][synthesis] %s', detail)
        return self.round_success(detail, data=world_decl)
