
import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.prep_actions import SHOP_OPEN_ANIM_S
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _note_receipt(op: SrOperation, applied: bool, reason: str) -> None:
    """开商店动作回执(R2 §3.2.5;渠道②,唯一写点 = kernel 口)。

    三出口全簿记:点击已发 = applied=true;幂等已开(无动作可发)/入口
    观察失败(动作没发出)= applied=false + reason——失败可见性(exec_events
    收编)。发出即簿记非验证(不读屏核验);journal 常开(ADR-0634)回执
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
        note_action_receipt(bs, op='CwOpOpenShop', applied=applied,
                            reason=reason, screen=SHOP_SCREEN_NAME,
                            actor='CwOpOpenShop')
    except Exception as e:  # noqa: BLE001  回执失败不阻塞动作链
        from one_dragon.utils.log_utils import log
        log.warning('[cw][receipt] 开商店回执写入失败(不阻塞): %s', e)


def open_shop(op: SrOperation) -> OperationRoundResult:
    """开商店原子核心(W970 批 A 契约 §4.2 ``CwOpOpenShop``;幂等开店)。

    ``op`` = 宿主 op(编排壳直调时传壳自身,复用其 round_by_* 判定与
    测试替身桩;本文件 ``CwOpOpenShop`` 独立跑时传自身)。

    幂等入口观察:已开(「按钮-收起」可见)→ 直接成功——自动开店场景
    点击落空不判负(W970 §4.2 F7),重入轮由本观察裁决出口。未开 → 点
    「按钮-商店」→ park_cursor → 固定等待 ``SHOP_OPEN_ANIM_S``(用户口述
    定值:干净的备战里打开商店等 1 秒就够,操作完成自等动画)→
    **机械交回**(验证废除,用户裁定 2026-09-10:动作 op 只管机械执行
    禁止验证;M1③ 发出即职责完成,调用方不问成败)——不再验「收起出现」,
    店开没开由下一轮重入幂等观察 / 下一帧观察侧对账(0n 三锚/备战帧读
    互斥)自然闭环。找不到商店/收起按钮 = 入口观察失败(动作没发出)→
    fail 如实交回。

    R2:三出口各落一条动作回执(見 :func:`_note_receipt`;幂等已开 =
    无动作可发的 applied=false 事实,非成败判定)。
    """
    if op.round_by_find_area(op.screenshot(), SHOP_SCREEN_NAME,
                             '按钮-收起').is_success:
        _note_receipt(op, False, '商店已开(幂等入口观察,无动作可发)')
        return op.round_success('商店已开')
    if not op.round_by_find_and_click_area(
            op.screenshot(), '货币战争-备战', '按钮-商店').is_success:
        # 入口观察失败 = 动作没发出(职责未完成)→ fail 如实交回(与
        # 「点击已发」的机械 retry 区分,直调消费面按 is_success 分流)。
        _note_receipt(op, False, '找不到商店/收起按钮')
        return op.round_fail('找不到商店/收起按钮')
    # 点击后 park:光标停在「按钮-商店」上会污染后继读屏(审计 P0 同型)
    op.park_cursor()
    time.sleep(SHOP_OPEN_ANIM_S)
    _note_receipt(op, True, '')
    return op.round_retry('开商店点击已发,重入观察裁决', wait=1)


class CwOpOpenShop(SrOperation):
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
