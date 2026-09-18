
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
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_from_ctx,
            note_action_receipt,
        )
        gs = game_state_from_ctx(getattr(op, 'ctx', None))
        if gs is None:
            return
        note_action_receipt(gs, op='CwOpCloseShop', applied=applied,
                            reason=reason, screen=SHOP_SCREEN_NAME,
                            actor='CwOpCloseShop')
    except Exception as e:  # noqa: BLE001  回执失败不阻塞动作链
        from one_dragon.utils.log_utils import log
        log.warning('[cw][receipt] 关商店回执写入失败(不阻塞): %s', e)


def _clear_shop_payload(op: SrOperation) -> None:
    """关店时点 kernel 侧 shop payload 清场(W971 04-shop §2 预留挂点落地:
    「CwOpCloseShop 完成承诺含商店族字段清理」)。

    Why: ``proj_buy_payload`` 买后 logic 态的唯一既有清场写端 =
    ``apply_shop_action_logic`` 的 CwActionCloseShopParam 分支(``leave_screen``),但
    生产链 CwActionCloseShopParam 被「终结不入序列」约定截在决策驱动器外
    (decide_shop_screen 收尾 return,不进 apply),机械关店只点按钮不喂
    kernel → 买后 payload 跨轮残留,下轮开店帧实读证伪 → 安灯停局
    (run_20260918_063249 实证:上轮买后 4 空槽+残影 vs 新波 5 卡)。
    本口 = 「非当前画面 = None」结构语义(§2.2 画面附加域)在机械关店
    时点的落地,点击已发/幂等已关两出口同清(已关残留同样陈旧)。
    容器缺席/已 None 静默跳过;失败不阻塞动作链(同回执 best-effort)。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
            game_state_from_ctx,
        )
        gs = game_state_from_ctx(getattr(op, 'ctx', None))
        if gs is None or gs.shop.value is None:
            return
        gs.leave_screen(gs.shop, sig=ChannelSig(
            family='obs', actor='CwOpCloseShop',
            screen=SHOP_SCREEN_NAME, mode='read'))
    except Exception as e:  # noqa: BLE001  清场失败不阻塞动作链
        from one_dragon.utils.log_utils import log
        log.warning('[cw][shop] 关店清场写入失败(不阻塞): %s', e)


def _close_shop_already_closed(op: SrOperation) -> OperationRoundResult:
    """幂等已关出口构造(单一构造点)。

    旧路径 miss 臂与变体 observe 早退(收编批)共享同一构造:
    applied=false 回执(无动作可发)+ success;禁第二份(两路径共享
    零转录,总纲契约 1)。
    """
    _note_receipt(op, False, '商店已关(幂等入口观察,无动作可发)')
    _clear_shop_payload(op)
    return op.round_success('商店已关(收起不在,幂等入口观察)')


def close_shop(op: SrOperation) -> OperationRoundResult:
    """关商店原子核心(W970 批 A 契约 §4.2 ``CwOpCloseShop``)。

    ``op`` = 宿主 op(编排壳直调时传壳自身,复用其 round_by_* 判定与
    测试替身桩;本文件 ``CwOpCloseShop`` 独立跑时传自身)。

    幂等入口观察:「收起」不在 = 店已关(异常入口与上轮已点掉同判)→
    直接成功(与 open_shop 幂等对称;W970 原「找不到收起不假成功」语义
    随验证废除退役——店已关 = 本 op 目标已达成,非冒充)。店开 → 点
    「按钮-收起」→ 固定等待 ``SHOP_CLOSE_ANIM_S``(操作完成自等
    动画,screen_flow_timing #15 实测 ~1s)→ **机械交回**(验证废除,
    用户裁定 2026-09-10:动作 op 只管机械执行禁止验证;M1③ 发出即职责
    完成,调用方不问成败)——不再验「收起消失」,关没关由下一轮重入幂等
    观察/下一帧观察侧对账(0n 三锚/备战双锚)自然闭环。

    R2:两出口各落一条动作回执(見 :func:`_note_receipt`)。
    """
    if not op.round_by_find_and_click_area(
            op.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success:
        return _close_shop_already_closed(op)
    time.sleep(SHOP_CLOSE_ANIM_S)
    _note_receipt(op, True, '')
    # 商店族字段清理挂点(W971 04-shop §2)随本批落地:关店机械口即
    # kernel 侧清场口,见 _clear_shop_payload。
    _clear_shop_payload(op)
    # 机械交回(验证废除):收起消失与否由下一轮重入幂等观察裁决。
    return op.round_retry('关商店点击已发,重入观察裁决', wait=1)


class CwOpCloseShop(CwScreenOpBase):
    """备战-开商店 → 货币战争-备战 原子 op(W970 批 A)。

    生产路径由 BuyShopCards 编排壳直调 :func:`close_shop`(宿主 op 复用);
    本类为独立可跑壳(W970 批 C 流程层接管后成为编排单元)。

    统一观察架构收编(B4 挂账批;变体形态先例 =
    ``CwProgressionScreenOp``):改挂 ``CwScreenOpBase`` 作只读/导航变体
    ——幂等原子动作零策略消费,decide 空申报 = 本屏无策略消费的合同
    声明(B4 选项②)。``close`` 节点顶部装配点分流(架构设计 §9.1 并存
    纪律):两端口完整在场(测试 harness 显式装配)→ ``run_lifecycle()``
    走变体五段;缺省 None = 生产直连 :func:`close_shop` 旧路径,原序列
    逐位保留,生产行为零变化。变体五段映射:observe = 幂等入口观察裁决
    (纯读,「收起」不在 = 店已关 → 幂等出口早退;点击动作不进观察段)、
    reconcile/decide = 空申报(幂等原子动作无对账面/无策略消费)、
    act 及其后 = 整体委托 :func:`close_shop`(旧体单一共享零第二转录,
    含「收起」融合判定点击的旧路径单一机械调用;其「点击已发
    retry(wait=1) 重入观察裁决」出口原位保留)、on_outcome = 无登记件
    (注册表缺席 = 零动作)。幂等观察无「已发」旗标:收起锚可见与否即
    全部裁决,首入/重入同义——异于总纲契约 6「已发旗标」定谳辖域
    (同推进型变体理由,重入出口随骨架映射住 observe 段)。
    """

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-关商店')

    @operation_node(name='关商店', is_start_node=True)
    def close(self) -> OperationRoundResult:
        # 装配点分流(架构设计 §9.1 并存期;先例锚 = cw_screen_encounter
        # 同式判据):两端口完整在场 → 变体五段;缺省 None = 生产直连
        # 下方旧路径(原序列逐位保留)。节点预算归本装饰器,不随路径变。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        return close_shop(self)

    # ---- 变体五段(只读/导航形态;动作半与旧路径共享旧体,零第二转录)----

    def lifecycle_observe(self) -> tuple[Any, OperationRoundResult | None]:
        """段1 observe:幂等入口观察裁决(:func:`close_shop` miss 臂纯读转录)。

        「按钮-收起」不在 = 店已关(异常入口与上轮已点掉同判)→ 幂等
        出口早退(构造共享 :func:`_close_shop_already_closed`,回执 +
        success 与旧路径 miss 臂逐位同);命中 → 不早退,动作半交决策
        循环。纯读判定(:meth:`round_by_find_area`,不点击)——旧路径
        的「收起」融合判定点击(单一机械调用)整体归委托体,观察段
        零变异。
        """
        if not self.round_by_find_area(self.screenshot(), SHOP_SCREEN_NAME,
                                       '按钮-收起').is_success:
            return None, _close_shop_already_closed(self)
        return None, None

    def lifecycle_reconcile(self, payload: Any) -> None:
        """段2 reconcile:空申报(幂等原子动作无对账面)。"""
        return None

    def lifecycle_decision_cycle(self, payload: Any) -> OperationRoundResult:
        """段3-5:decide 空申报 + act 整体委托 :func:`close_shop`。

        decide 空申报 = 本屏无策略消费的合同声明(B4 选项②原语义);
        act 半 = 旧体委托(单一共享;重入观察裁决出口原位保留);
        on_outcome = 无登记件(注册表缺席 = 零动作)。
        """
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = close_shop(self)
        self._lifecycle_mark('on_outcome')
        return rs
