
import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.prep_actions import SHOP_CLOSE_ANIM_S
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def close_shop(op: SrOperation) -> OperationRoundResult:
    """关商店原子核心(W970 批 A 契约 §4.2 ``CwOpCloseShop``)。

    ``op`` = 宿主 op(编排壳直调时传壳自身,复用其 round_by_* 判定与
    测试替身桩;本文件 ``CwOpCloseShop`` 独立跑时传自身)。

    点「按钮-收起」→ 固定等待 ``SHOP_CLOSE_ANIM_S``(DD-011 操作完成
    自等动画,screen_flow_timing #15 实测 ~1s)→ 「收起消失」验证
    (刚点的元素消失 = 真转移信号;未消失 = 点击未落地 → fail-closed
    retry,防下个 op 在「店仍开」假设上读关态字段)。找不到收起按钮 =
    店可能已关(异常入口),同样 retry 不假成功。
    """
    if not op.round_by_find_and_click_area(
            op.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success:
        return op.round_retry('找不到收起按钮(商店可能已关)', wait=1)
    time.sleep(SHOP_CLOSE_ANIM_S)
    if op.round_by_find_area(op.screenshot(), SHOP_SCREEN_NAME,
                             '按钮-收起').is_success:
        return op.round_retry('收起未生效(收起按钮仍在)', wait=1)
    # TODO(P2 黑板落地时启用):商店族字段清理挂点——W971 04-shop §2
    # 「CwOpCloseShop 完成承诺含商店族字段清理」;字段清理随黑板/流程层
    # 批次落地,本批只留挂点不实现。
    return op.round_success('商店已收起')


class CwOpCloseShop(SrOperation):
    """备战-开商店 → 货币战争-备战 原子 op(W970 批 A)。

    生产路径由 BuyShopCards 编排壳直调 :func:`close_shop`(宿主 op 复用);
    本类为独立可跑壳(W970 批 C 流程层接管后成为编排单元)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-关商店')

    @operation_node(name='关商店', is_start_node=True)
    def close(self) -> OperationRoundResult:
        return close_shop(self)
