"""从跃迁页进入商店 —— 跃迁页点「商店兑换」打开商店页。

起点要求在跃迁页（单一职责；其他画面起点请先用 BackToNormalWorldPlus /
ReadWarpStatusOp 等导航到跃迁页）。商店默认打开在星芒兑换 tab；余烬兑换
tab 的切换与余烬数量/兑换次数读数见 [ShopSwitchTabOp](shop_switch_tab.py)
与消费 skill 跃迁抽卡.md。

用途：票+星琼不足时按消费 skill 流程向用户提供「商店余烬兑换」选项——
打开商店确认余烬数量与专票兑换剩余次数（余烬兑换页专票 90 余烬/张，每月
限量 5 张）。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_WARP_SCREEN: str = '跃迁'
_SHOP_SCREEN: str = '商店'


class EnterShopFromWarpOp(SrOperation):
    """从跃迁页点「商店兑换」进入商店页(默认星芒兑换 tab)。
    起点:跃迁页(单一职责,不做跨画面导航);终点:商店页。

    结果状态：
    - ``SHOP_OPENED``：商店页已打开（默认星芒兑换 tab）；
    失败：起点不在跃迁页（本 op 不做跨画面导航，单一职责）。
    """

    def __init__(self, ctx: SrContext):
        """
        :param ctx: 上下文
        """
        SrOperation.__init__(self, ctx, op_name=gt('进入商店'),
                             node_max_retry_times=15)

    @operation_node(name='前往商店', is_start_node=True)
    def enter_shop(self) -> OperationRoundResult:
        """跃迁页点「按钮-商店兑换」，until 商店页 tab 锚出现。

        商店页锚用「tab-常驻商店」文本（商店页常显的顶层 tab,跃迁页无此
        文本,互斥可靠）。
        """
        if self.check_and_update_current_screen(
                screen_name_list=[_WARP_SCREEN]) != _WARP_SCREEN:
            return self.round_fail('起点不在跃迁页,请先导航到跃迁页(本 op 只做跃迁页→商店)')
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _WARP_SCREEN, '按钮-商店兑换',
            until_find_all=[(_SHOP_SCREEN, 'tab-常驻商店')],
            success_wait=2, retry_wait=2)
        if result.is_success:
            return self.round_success(status='SHOP_OPENED', wait=1)
        return result

    @node_from(from_name='前往商店', status='SHOP_OPENED')
    @operation_node(name='收尾')
    def finish(self) -> OperationRoundResult:
        """终点节点:无动作,状态已由上一节点给出。"""
        return self.round_success(status='SHOP_OPENED', wait=0.5)
