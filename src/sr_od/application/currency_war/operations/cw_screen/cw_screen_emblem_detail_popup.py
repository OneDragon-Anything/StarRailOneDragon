"""货币战争 星徽详情弹窗 op(空决策形态;ADR-0584,A8)。

「XX星徽套组」详情面板(1d,点球/装备操作误点开星徽图标)的处理迁移:
点右上 X 关回备战,无验效。**刻意不用 ESC**(bug#2,原分支注释随迁,
禁在 op 内「顺手统一」成 ESC):面板已关时 ESC 落备战弹「中断挑战」;
X 是弹窗内坐标永远安全。背景:2026-08-17 M53 停机建档。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口门(双锚其一:「标识-流派星徽」area 锚 ∨「标识-套组标题」,与外
循环 1d 分发判定同源;miss 未发 = round_fail 交回外循环重判,「下一帧
重判」是外循环职责)+ obs{on_screen} 挂实例属性(空决策形态无 report:
本屏零容器写点,obs 类住 kernel/cw_screen_report/emblem_detail_popup.py,
import 构造即可)。决策动作 node = 重入裁决顶部(点 X 已发 → 双锚 miss
= 已离开本画面 → success 交回——出口 = 入口观察的合法重判,非动作层
判效;在 = 再推进)→ 点「按钮-关闭」单次推进(success_wait=1 同原分支
内联值)→ round_wait 循环(不烧节点重试预算,不收敛 = 动作 bug 响亮
暴露,无防御上限;「推进动作未落地」= round_fail 如实交回)。本类入口
信号 = 自有双锚判定(覆写形态),重入裁决有观察信号可用,无「免锚发出
即 success」出口。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_screen_report.emblem_detail_popup import (
    CwScreenEmblemDetailPopupObs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenEmblemDetailPopup(SrOperation):
    """星徽详情弹窗:双锚入口其一,点「按钮-关闭」(不用 ESC,见模块头)。"""

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-星徽详情')
        # 画面档名/主锚(与外循环 1d 分发判定同源;实例属性)
        self._screen_name: str = '货币战争-星徽详情'
        self._entry_area: str = '标识-流派星徽'
        # 推进已发标志(验证废除形态):区分「首发锚 miss = 误分发 fail 交回」
        # 与「重入锚 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenEmblemDetailPopupObs | None = None

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:双锚其一即接管(与外循环 1d 分发判定同源)。"""
        if self.round_by_find_area(screen, self._screen_name,
                                   self._entry_area,
                                   crop_first=False).is_success:
            return True
        return self.round_by_find_area(
            screen, self._screen_name, '标识-套组标题',
            crop_first=False).is_success

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + obs{on_screen} 装载(空决策形态无 report)。

        门 miss = 首发误分发(分发判定帧命中 ∧ op 新帧门 miss 的过渡帧):
        fail 交回外循环重判,不在 op 内等待重探。"""
        screen = self.last_screenshot
        if not self.entry_ok(screen):
            return self.round_fail(
                f'{self.op_name}入口锚未命中(交回外循环重判)')
        self._obs = CwScreenEmblemDetailPopupObs(on_screen=True, screen=screen)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=2)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 单次推进 → round_wait(预算 = 现役值 2 保留)。"""
        if self._advanced_once and not self.entry_ok(self.last_screenshot):
            # 重入裁决(验证废除形态):重入锚 miss = 已离开本画面 → success
            # 交回;旗标清(实例级,单 op 生命周期语义)。
            self._advanced_once = False
            return self.round_success(
                f'{self.op_name}已推进(重入观察:已离开本画面)', wait=1)
        if not self.progress_once():
            return self.round_fail(f'{self.op_name}推进动作未落地')
        self._advanced_once = True
        # 循环推进 = round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮
        # 暴露,无防御上限)。
        return self.round_wait(f'{self.op_name}推进已发,重入观察裁决', wait=1)

    def progress_once(self) -> bool:
        """推进处理:点「按钮-关闭」(success_wait=1 同原分支内联值)。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, self._screen_name, '按钮-关闭',
            success_wait=1).is_success
