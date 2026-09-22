"""货币战争 消耗品详情浮层 op(空决策形态,A4)。

获消耗品奖励(投资策略「星星相印」给【员工投影仪】等)后游戏自动弹介绍
modal(0f')的处理迁移:点 modal 右上 × 关,无验效。× 复用同族建档
「货币战争-道具详情弹窗/按钮-关闭」(消耗品 modal 与聘用书 modal 同为
道具详情弹窗家族,× 同位;**待实机核**:消耗品帧上该坐标未实机复点)。
替代 ESC 的理由:× 是弹窗内坐标永远安全,ESC 在 modal 已自关时落备战
会误弹「中断挑战」(bug#2)。背景(原分支注释):2026-08-06 实跑
plane2 supply 后弹「员工投影仪」modal,flat retry ~19min 失败——非策略死,
UI 弹窗卡死。签名「消耗品」(类型 label) AND 「拖动到」(拖动使用说明,
只出现在消耗品详情 modal,备战底部消耗品栏无)→ 双条件精确,不误匹配备战;
装备类详情 modal(无「拖动到」)是长尾,观察到再补。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口门(双 OCR 条件,与外循环 0f' 分发判定同源同参:双 lcs 0.9 精确
签名;miss 未发 = round_fail 交回外循环重判,「下一帧重判」是外循环
职责)+ obs{on_screen} 挂实例属性(空决策形态无 report:本屏零容器
写点,obs 类住 kernel/cw_screen_report/consumable_overlay.py,import
构造即可)。决策动作 node = 重入裁决顶部(点 × 已发 → 双签名 miss =
已离开本画面 → success 交回——出口 = 入口观察的合法重判,非动作层
判效;在 = 再推进)→ area 读「按钮-关闭」+ mouse_move+click 单次推进
(同 CwScreenItemDetailPopup,同族 modal 的 bug#1 缓解保留)→
round_wait 循环(不烧节点重试预算,不收敛 = 动作 bug 响亮暴露,无防御
上限;「推进动作未落地」= round_fail 如实交回)。本类入口信号 = 自有
双 OCR 判定(覆写形态),重入裁决有观察信号可用,无「免锚发出即
success」出口。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.consumable_overlay import (
    CwScreenConsumableOverlayObs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenConsumableOverlay(SrOperation):
    """消耗品详情浮层:双 OCR 条件入口,点右上 × 关闭。"""

    #: 关闭控件:同族「道具详情弹窗」的右上 ×(道具详情弹窗家族共用)
    CLOSE_SCREEN = '货币战争-道具详情弹窗'
    CLOSE_AREA = '按钮-关闭'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-消耗品浮层')
        # 推进已发标志(验证废除形态):区分「首发 miss = 误分发 fail 交回」
        # 与「重入 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenConsumableOverlayObs | None = None

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:双 OCR 签名(与外循环 0f' 分发判定同源同参,双 lcs 0.9)。"""
        return (self.round_by_ocr(screen, '消耗品', lcs_percent=0.9).is_success
                and self.round_by_ocr(screen, '拖动到', lcs_percent=0.9).is_success)

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + obs{on_screen} 装载(空决策形态无 report)。

        门 miss = 首发误分发(分发判定帧命中 ∧ op 新帧门 miss 的过渡帧):
        fail 交回外循环重判,不在 op 内等待重探。"""
        screen = self.last_screenshot
        if not self.entry_ok(screen):
            return self.round_fail(
                f'{self.op_name}入口锚未命中(交回外循环重判)')
        self._obs = CwScreenConsumableOverlayObs(on_screen=True, screen=screen)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=2)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 单次推进 → round_wait(预算 = 现役值 2 保留)。"""
        if self._advanced_once and not self.entry_ok(self.last_screenshot):
            # 重入裁决(验证废除形态):重入 miss = 已离开本画面 → success
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
        """推进处理:读「按钮-关闭」center → mouse_move+click(缺失 =
        False 如实交回;mouse_move 同 CwScreenItemDetailPopup 的 bug#1
        缓解保留)。"""
        _close = area_center(self.ctx, self.CLOSE_AREA, self.CLOSE_SCREEN)
        if _close is None:
            return False
        self.ctx.controller.mouse_move(_close)
        self.ctx.controller.click(_close)
        return True
