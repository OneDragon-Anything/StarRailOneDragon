
import time
from typing import Any

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.cw_game_ports import (
    action_sink,
    observation_source,
)
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
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
        from sr_od.application.currency_war.kernel.cw_game_state import (
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


def _open_shop_already_open(op: SrOperation) -> OperationRoundResult:
    """幂等已开出口构造(单一构造点)。

    旧路径首臂与变体 observe 早退(收编批 T-45)共享同一构造:
    applied=false 回执(无动作可发)+ success;禁第二份(两路径共享
    零转录,总纲契约 1)。
    """
    _note_receipt(op, False, '商店已开(幂等入口观察,无动作可发)')
    return op.round_success('商店已开')


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
        return _open_shop_already_open(op)
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


class CwOpOpenShop(CwScreenOpBase):
    """货币战争-备战 → 备战-开商店 原子 op(W970 批 A)。

    生产路径由 BuyShopCards 编排壳直调 :func:`open_shop`(宿主 op 复用);
    本类为独立可跑壳(W970 批 C 流程层接管后成为编排单元,含腾席链 b
    read_only 开店)。

    统一观察架构收编(B4 挂账批,账本 T-45;变体形态先例 =
    ``CwProgressionScreenOp``):改挂 ``CwScreenOpBase`` 作只读/导航变体
    ——幂等原子动作零策略消费,decide 空申报 = 本屏无策略消费的合同
    声明(B4 选项②)。``open`` 节点顶部装配点分流(架构设计 §9.1 并存
    纪律):两端口完整在场(测试 harness 显式装配)→ ``run_lifecycle()``
    走变体五段;缺省 None = 生产直连 :func:`open_shop` 旧路径,原序列
    逐位保留,生产行为零变化。变体五段映射:observe = 幂等入口观察裁决
    (纯读,已开 → 幂等出口早退;点击动作不进观察段)、reconcile/decide =
    空申报(幂等原子动作无对账面/无策略消费)、act 及其后 = 整体委托
    :func:`open_shop`(旧体单一共享零第二转录;其动作半的「找不到 fail /
    点击已发 retry(wait=1) 重入观察裁决」出口原位保留)、on_outcome =
    无登记件(注册表缺席 = 零动作)。幂等观察无「已发」旗标:收起锚
    可见与否即全部裁决,首入/重入同义——异于总纲契约 6「已发旗标」
    定谳辖域(同推进型变体理由,重入出口随骨架映射住 observe 段)。
    """

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-开商店')

    @operation_node(name='开商店', is_start_node=True)
    def open(self) -> OperationRoundResult:
        # 装配点分流(架构设计 §9.1 并存期;先例锚 = cw_screen_encounter
        # 同式判据):两端口完整在场 → 变体五段;缺省 None = 生产直连
        # 下方旧路径(原序列逐位保留)。节点预算归本装饰器,不随路径变。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        return open_shop(self)

    # ---- 变体五段(只读/导航形态;动作半与旧路径共享旧体,零第二转录)----

    def lifecycle_observe(self) -> tuple[Any, OperationRoundResult | None]:
        """段1 observe:幂等入口观察裁决(:func:`open_shop` 首臂纯读转录)。

        「按钮-收起」可见 = 商店已开 → 幂等出口早退(构造共享
        :func:`_open_shop_already_open`,回执 + success 与旧路径首臂
        逐位同);未开 → 不早退,动作半交决策循环。纯读判定
        (:meth:`round_by_find_area`,不点击)——点击动作归委托体,
        观察段零变异。
        """
        if self.round_by_find_area(self.screenshot(), SHOP_SCREEN_NAME,
                                   '按钮-收起').is_success:
            return None, _open_shop_already_open(self)
        return None, None

    def lifecycle_reconcile(self, payload: Any) -> None:
        """段2 reconcile:空申报(幂等原子动作无对账面)。"""
        return None

    def lifecycle_decision_cycle(self, payload: Any) -> OperationRoundResult:
        """段3-5:decide 空申报 + act 整体委托 :func:`open_shop`。

        decide 空申报 = 本屏无策略消费的合同声明(B4 选项②原语义);
        act 半 = 旧体委托(单一共享;重入观察裁决出口在其动作半,原位
        保留);on_outcome = 无登记件(注册表缺席 = 零动作)。
        """
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = open_shop(self)
        self._lifecycle_mark('on_outcome')
        return rs
