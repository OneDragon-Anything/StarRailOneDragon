
import time

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.kernel.cw_screen_report.open_shop import (
    CwOpOpenShopObs,
)
from sr_od.application.currency_war.prep_actions import SHOP_OPEN_ANIM_S
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _note_receipt(op: SrOperation, applied: bool, reason: str) -> None:
    """开商店动作回执(R2 §3.2.5;渠道②,唯一写点 = kernel 口)。

    三出口全簿记:点击已发 = applied=true;幂等已开(无动作可发)/入口
    观察失败(动作没发出)= applied=false + reason——失败可见性(exec_events
    收编)。发出即簿记非验证(不读屏核验);journal 常开回执
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
        note_action_receipt(gs, op='CwOpOpenShop', applied=applied,
                            reason=reason, screen=SHOP_SCREEN_NAME,
                            actor='CwOpOpenShop')
    except Exception as e:  # noqa: BLE001  回执失败不阻塞动作链
        from one_dragon.utils.log_utils import log
        log.warning('[cw][receipt] 开商店回执写入失败(不阻塞): %s', e)


def _open_shop_already_open(op: SrOperation) -> OperationRoundResult:
    """幂等已开出口构造(单一构造点;观察 node 门命中与动作 node 重入
    裁决共用):applied=false 回执(无动作可发)+ success;禁第二份
    (总纲契约 1 共享零转录)。"""
    _note_receipt(op, False, '商店已开(幂等入口观察,无动作可发)')
    return op.round_success('商店已开')


def open_shop(op: SrOperation) -> OperationRoundResult:
    """开商店原子核心(W970 批 A 契约 §4.2 ``CwOpOpenShop``;幂等开店)。

    ``op`` = 宿主 op(编排壳直调时传壳自身,复用其 round_by_* 判定与
    测试替身桩;本文件 ``CwOpOpenShop`` 独立跑时经其两 node 形态驱动)。

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


class CwOpOpenShop(SrOperation):
    """货币战争-备战 → 备战-开商店 原子 op(W970 批 A;推进型两 node 形态)。

    生产路径由编排壳直调 :func:`open_shop`(宿主 op 复用);本类为独立
    可跑壳(流程层接管后成为编排单元的机械开店臂)。

    两 node 形态(推进型空决策,幂等原子动作零策略消费;无 report——
    空决策形态无对账面/无容器域,kernel/cw_screen_report/open_shop.py
    只含 obs 类与「无 report」声明):

    - 观察 node = 画面门:「按钮-收起」可见(商店锚)→ 目标已达成 →
      幂等出口早退(:func:`_open_shop_already_open`,回执 + success,与
      直调首臂逐位同);miss → 进决策动作 node(纯读判定,不点击)。
    - 决策动作 node = 现役推进体逐位(点击 + park + 动画等待 + 回执)+
      重入裁决(顶部幂等门:重入帧商店锚在 = 上轮点击已落地 → 幂等出口;
      miss = 未落地 → 重发点击),循环推进 = round_wait(不烧节点重试
      预算;不收敛 = 动作实现 bug 响亮暴露,无防御上限)。

    幂等观察无「已发」旗标:收起锚可见与否即全部裁决,首入/重入同义。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-开商店')
        # 观察结果(观察 node 产物,决策动作 node/测试消费;无 report)。
        self._obs: CwOpOpenShopObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """画面门:「按钮-收起」可见 = 商店已开 → 幂等出口早退。"""
        screen = self.last_screenshot
        on_screen = self.round_by_find_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起').is_success
        self._obs = CwOpOpenShopObs(on_screen=on_screen, screen=screen)
        if on_screen:
            return _open_shop_already_open(self)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作')
    def act(self) -> OperationRoundResult:
        """重入裁决(幂等门)→ 点击推进体逐位 → round_wait 循环推进。"""
        # 重入裁决(现役幂等入口观察语义逐位):重入帧商店锚在 = 上轮
        # 点击已落地(店已开)→ 幂等出口;miss = 未落地 → 重发点击。
        if self.round_by_find_area(self.last_screenshot, SHOP_SCREEN_NAME,
                                   '按钮-收起').is_success:
            return _open_shop_already_open(self)
        if not self.round_by_find_and_click_area(
                self.screenshot(), '货币战争-备战', '按钮-商店').is_success:
            # 入口观察失败 = 动作没发出(职责未完成)→ fail 如实交回。
            _note_receipt(self, False, '找不到商店/收起按钮')
            return self.round_fail('找不到商店/收起按钮')
        # 点击后 park:光标停在「按钮-商店」上会污染后继读屏(审计 P0 同型)
        self.park_cursor()
        time.sleep(SHOP_OPEN_ANIM_S)
        _note_receipt(self, True, '')
        # 机械交回(验证废除):店开没开由下一轮重入裁决/下一帧观察侧
        # 对账自然闭环;循环推进 = round_wait(不烧节点重试预算)。
        return self.round_wait(wait=1)
