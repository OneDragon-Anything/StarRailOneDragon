"""开店动作 op(CwActionOpenShopOp)——动作 op 重组 换壳(原
``OpenShopOp``,ActionOp ABC → 框架 SrOperation;op-layer.md §1.2 动作
op 契约)。注册行 = terminal 承载行。

**本 op 的执行在正常路径不可达**:CwActionOpenShopParam 的流程编排是画面
op 流程职责(``cw_screen_prep._act_execute_default`` →
``_open_shop_phase``),按「流程编排留在原位」划分不进动作 op;注册行的用途 =
终结判定/等待时长经注册表读类属性(terminal/terminal_wait)。可达(经
注册表分派到本 op 执行)= 分派漏斗被绕过,AssertionError 响亮暴露防
静默复活。上报:不调(不可达路径)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenShopParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenShopOp(CwOperation):
    """开店(注册行 = terminal 承载行;执行抛 AssertionError)。

    终结动作:开店切商店画面(非帧稳定)→ 本备战访问终结,返回主循环
    重识别;终结等待 = ``terminal_wait``(与原决策循环 ``wait=1.0`` 逐字
    等价,等价测试锁 = test_action_registry 终结集锁)。
    """

    #: 终结动作(开店切商店画面,返回主循环重新识别)。
    terminal = True

    #: 终结返回等待秒数(与原决策循环 wait=1.0 逐字等价)。
    terminal_wait = 1.0

    def __init__(self, ctx: SrContext, param: CwActionOpenShopParam,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionOpenShopOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_shop', is_start_node=True)
    def run(self) -> OperationRoundResult:
        raise AssertionError(
            'CwActionOpenShopParam 不经动作 op 执行(流程层编排:cw_screen_prep.'
            '_act_execute_default → _open_shop_phase);本注册行 = '
            'terminal 承载行,正常路径不可达,可达即分派漏斗被绕过')
