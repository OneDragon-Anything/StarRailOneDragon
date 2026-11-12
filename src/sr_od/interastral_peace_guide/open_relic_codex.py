"""打开智库的遗器图鉴页(导航 op)。

用途:快速到达「智库 → 遗器」图鉴列表页,查看遗器套装收录情况
(每套卡片显示 x/4 或 x/2 部位收录数;列表尾部锁定卡 = 未获得套装)。

组合复用:``OpenDataBankOp``(任意起点 → 智库主页)→
``SelectDataBankTabOp(DataBankTab.RELIC)``(主页点遗器分类 → 遗器图鉴)。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.menu.open_data_bank import OpenDataBankOp
from sr_od.operations.menu.select_data_bank_tab import DataBankTab, SelectDataBankTabOp
from sr_od.operations.sr_operation import SrOperation


class OpenRelicCodexOp(SrOperation):
    """导航到智库的遗器图鉴列表页。

    失败:智库主页 / 遗器图鉴判定持续不命中(详情见两个子 op)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=gt('打开遗器图鉴'),
                             node_max_retry_times=20)

    @operation_node(name='进入智库', is_start_node=True)
    def open_data_bank(self) -> OperationRoundResult:
        """任意起点 → 智库主页。"""
        op = OpenDataBankOp(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='进入智库')
    @operation_node(name='选择遗器分类')
    def select_relic_tab(self) -> OperationRoundResult:
        """智库主页 → 遗器图鉴列表页(已在遗器页时幂等直过)。"""
        op = SelectDataBankTabOp(self.ctx, DataBankTab.RELIC)
        return self.round_by_op_result(op.execute())
