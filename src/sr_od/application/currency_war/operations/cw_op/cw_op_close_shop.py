
import time

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.kernel.cw_screen_report.close_shop import (
    CwOpCloseShopObs,
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
    关店上报(report_action_close_shop_param,``leave_screen``),但
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
    """幂等已关出口构造(单一构造点;观察 node 门 miss 与动作 node 重入
    裁决共用):applied=false 回执(无动作可发)+ success;禁第二份
    (总纲契约 1 共享零转录)。"""
    _note_receipt(op, False, '商店已关(幂等入口观察,无动作可发)')
    _clear_shop_payload(op)
    return op.round_success('商店已关(收起不在,幂等入口观察)')


def close_shop(op: SrOperation) -> OperationRoundResult:
    """关商店原子核心(W970 批 A 契约 §4.2 ``CwOpCloseShop``)。

    ``op`` = 宿主 op(编排壳直调时传壳自身,复用其 round_by_* 判定与
    测试替身桩;本文件 ``CwOpCloseShop`` 独立跑时经其两 node 形态驱动)。

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


class CwOpCloseShop(SrOperation):
    """备战-开商店 → 货币战争-备战 原子 op(W970 批 A;推进型两 node 形态)。

    生产路径由编排壳直调 :func:`close_shop`(宿主 op 复用);本类为独立
    可跑壳(W970 批 C 流程层接管后成为编排单元)。

    两 node 形态(推进型空决策,幂等原子动作零策略消费;无 report——
    空决策形态无对账面/无容器域,kernel/cw_screen_report/close_shop.py
    只含 obs 类与「无 report」声明):

    - 观察 node = 画面门(商店在屏判定):「按钮-收起」不可见 = 店已关
      (异常入口与上轮已点掉同判)→ 幂等出口早退
      (:func:`_close_shop_already_closed`,回执 + 清场 + success,与直调
      miss 臂逐位同);可见 → 进决策动作 node(纯读判定,不点击)。
    - 决策动作 node = 现役推进体逐位(「收起」融合判定点击单一机械调用 +
      动画等待 + 回执 + 清场)+ 重入裁决(现役 miss 臂语义:重入帧
      「收起」不在 = 上轮点击已落地 → 幂等出口;可见 = 未落地 → 重发),
      循环推进 = round_wait(不烧节点重试预算;不收敛 = 动作实现 bug
      响亮暴露,无防御上限)。

    幂等观察无「已发」旗标:收起锚可见与否即全部裁决,首入/重入同义。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-关商店')
        # 观察结果(观察 node 产物,决策动作 node/测试消费;无 report)。
        self._obs: CwOpCloseShopObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """画面门:「按钮-收起」不在 = 店已关 → 幂等出口早退。"""
        screen = self.last_screenshot
        on_screen = self.round_by_find_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起').is_success
        self._obs = CwOpCloseShopObs(on_screen=on_screen, screen=screen)
        if not on_screen:
            return _close_shop_already_closed(self)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作')
    def act(self) -> OperationRoundResult:
        """现役推进体逐位(「收起」融合判定点击)+ 重入裁决 + round_wait。"""
        # 「收起」融合判定点击(现役 miss 臂 = 重入裁决:重入帧收起不在 =
        # 上轮点击已落地/店已关 → 幂等出口;可见 = 点击未生效 → 重发)。
        if not self.round_by_find_and_click_area(
                self.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success:
            return _close_shop_already_closed(self)
        time.sleep(SHOP_CLOSE_ANIM_S)
        _note_receipt(self, True, '')
        # 商店族字段清理挂点(W971 04-shop §2):关店机械口即 kernel 侧
        # 清场口,见 _clear_shop_payload。
        _clear_shop_payload(self)
        # 机械交回(验证废除):收起消失与否由下一轮重入裁决/下一帧观察
        # 侧对账自然闭环;循环推进 = round_wait(不烧节点重试预算)。
        return self.round_wait(wait=1)
