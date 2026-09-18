"""开店动作 op(CwActionOpenShopOp)——动作 op 重组批③ 换壳(原
``OpenShopOp``,ActionOp ABC → 框架 SrOperation;design.md §1.1/§1.2)。
注册行 = terminal 承载行。

**本 op 的执行在正常路径不可达**:CwActionOpenShopParam 的流程编排是画面
op 流程职责(``cw_screen_prep._act_execute_default`` 截流 →
``_open_shop_phase``),按「流程编排留守」划分不进动作 op;注册行的用途 =
终结判定/等待时长经注册表读类属性(terminal/terminal_wait)。可达(经
注册表分派到本 op 执行)= 分派漏斗被绕过,AssertionError 响亮暴露防
静默复活。read_only 两形态 = 动作字段承载,消费在流程层编排,与注册表
无关。上报:不调(不可达路径,design.md §1.2「不调」行)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenShopParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenShopOp(SrOperation):
    """开店(注册行 = terminal 承载行;执行抛 AssertionError)。

    终结动作:开店切商店画面(非帧稳定)→ 本备战访问终结,交回外循环
    重识别;终结等待 = ``terminal_wait``(与原决策循环 ``wait=1.0`` 逐字
    等价,等价测试锁 = test_cw_unified_action_3)。
    """

    #: 终结动作(开店切商店画面,交回外循环重识别)。
    terminal = True

    #: 终结交回等待秒数(与原决策循环 wait=1.0 逐字等价)。
    terminal_wait = 1.0

    def __init__(self, ctx: SrContext, param: CwActionOpenShopParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionOpenShopOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_shop', is_start_node=True)
    def run(self) -> OperationRoundResult:
        raise AssertionError(
            'CwActionOpenShopParam 不经动作 op 执行(流程层编排:cw_screen_prep.'
            '_act_execute_default 截流 → _open_shop_phase);本注册行 = '
            'terminal 承载行,正常路径不可达,可达即分派漏斗被绕过'
            '(design.md unified-action-factory §2.4)')
