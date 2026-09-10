
import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.prep_actions import SHOP_CLOSE_ANIM_S
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _note_receipt(op: SrOperation, applied: bool, reason: str) -> None:
    """关商店动作回执(R2 §3.2.5;渠道②,唯一写点 = kernel 口)。

    两出口全簿记:点击已发 = applied=true;幂等已关(无动作可发)=
    applied=false + reason。发出即簿记非验证;journal 常开(ADR-0634)回执
    写入无条件,无局跳过在 kernel 口。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_board_state import (
            board_state_from_ctx,
            note_action_receipt,
        )
        bs = board_state_from_ctx(getattr(op, 'ctx', None))
        if bs is None:
            return
        note_action_receipt(bs, op='CwOpCloseShop', applied=applied,
                            reason=reason, screen=SHOP_SCREEN_NAME,
                            actor='CwOpCloseShop')
    except Exception as e:  # noqa: BLE001  回执失败不阻塞动作链
        from one_dragon.utils.log_utils import log
        log.warning('[cw][receipt] 关商店回执写入失败(不阻塞): %s', e)


def close_shop(op: SrOperation) -> OperationRoundResult:
    """关商店原子核心(W970 批 A 契约 §4.2 ``CwOpCloseShop``)。

    ``op`` = 宿主 op(编排壳直调时传壳自身,复用其 round_by_* 判定与
    测试替身桩;本文件 ``CwOpCloseShop`` 独立跑时传自身)。

    幂等入口观察:「收起」不在 = 店已关(异常入口与上轮已点掉同判)→
    直接成功(与 open_shop 幂等对称;W970 原「找不到收起不假成功」语义
    随验证废除退役——店已关 = 本 op 目标已达成,非冒充)。店开 → 点
    「按钮-收起」→ 固定等待 ``SHOP_CLOSE_ANIM_S``(DD-011 操作完成自等
    动画,screen_flow_timing #15 实测 ~1s)→ **机械交回**(验证废除,
    用户裁定 2026-09-10:动作 op 只管机械执行禁止验证;M1③ 发出即职责
    完成,调用方不问成败)——不再验「收起消失」,关没关由下一轮重入幂等
    观察/下一帧观察侧对账(0n 三锚/备战双锚)自然闭环。

    R2:两出口各落一条动作回执(見 :func:`_note_receipt`)。
    """
    if not op.round_by_find_and_click_area(
            op.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success:
        _note_receipt(op, False, '商店已关(幂等入口观察,无动作可发)')
        return op.round_success('商店已关(收起不在,幂等入口观察)')
    time.sleep(SHOP_CLOSE_ANIM_S)
    _note_receipt(op, True, '')
    # TODO(P2 黑板落地时启用):商店族字段清理挂点——W971 04-shop §2
    # 「CwOpCloseShop 完成承诺含商店族字段清理」;字段清理随黑板/流程层
    # 批次落地,本批只留挂点不实现。
    # 机械交回(验证废除):收起消失与否由下一轮重入幂等观察裁决。
    return op.round_retry('关商店点击已发,重入观察裁决', wait=1)


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
