
import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.prep_actions import SHOP_OPEN_ANIM_S
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def open_shop(op: SrOperation) -> OperationRoundResult:
    """开商店原子核心(W970 批 A 契约 §4.2 ``OpenShopOp``;幂等开店)。

    ``op`` = 宿主 op(编排壳直调时传壳自身,复用其 round_by_* 判定与
    测试替身桩;本文件 ``OpenShopOp`` 独立跑时传自身)。

    幂等:已开(「按钮-收起」可见)→ 直接成功——自动开店场景点击落空
    不判负(W970 §4.2 F7)。未开 → 点「按钮-商店」→ park_cursor →
    固定等待 ``SHOP_OPEN_ANIM_S``(用户口述定值:干净的备战里打开商店
    等 1 秒就够,DD-011 操作完成自等动画)→ 「按钮-收起」验证,未现 =
    点击未生效,fail-closed retry(静默继续会以「店已开」假设读牌面,
    r347 语义)。判稳标志 = 目标画面独有锚「按钮-收起」(「按钮-商店/
    收起」同址,竞速下点击可命中反义按钮 → 收起消失 → retry,不假成功)。
    """
    if op.round_by_find_area(op.screenshot(), SHOP_SCREEN_NAME,
                             '按钮-收起').is_success:
        return op.round_success('商店已开')
    if not op.round_by_find_and_click_area(
            op.screenshot(), '货币战争-备战', '按钮-商店').is_success:
        return op.round_retry('找不到商店/收起按钮', wait=1)
    # 点击后 park:光标停在「按钮-商店」上会污染后继读屏(审计 P0 同型)
    op.park_cursor()
    time.sleep(SHOP_OPEN_ANIM_S)
    if not op.round_by_find_area(op.screenshot(), SHOP_SCREEN_NAME,
                                 '按钮-收起').is_success:
        return op.round_retry('开店未生效(收起未出现)', wait=1)
    return op.round_success('商店已开')


class OpenShopOp(SrOperation):
    """货币战争-备战 → 备战-开商店 原子 op(W970 批 A)。

    生产路径由 BuyShopCards 编排壳直调 :func:`open_shop`(宿主 op 复用);
    本类为独立可跑壳(W970 批 C 流程层接管后成为编排单元,含腾席链 b
    read_only 开店)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-开商店')

    @operation_node(name='开商店', is_start_node=True)
    def open(self) -> OperationRoundResult:
        return open_shop(self)
