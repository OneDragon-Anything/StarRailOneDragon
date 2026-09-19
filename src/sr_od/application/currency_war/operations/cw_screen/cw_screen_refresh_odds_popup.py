"""货币战争 商店刷新概率表弹窗 op(空决策形态;ADR-0584,A2)。

采晶矿误触开后遮出战按钮的实机事故补分支(0e2)的处理迁移:点 × 关闭,
无验效(关闭确认由下轮外循环重判承接)。× 坐标已 area 化
(``货币战争-商店刷新概率表``/``按钮-关闭概率表``,矩形中心 = 原 Point
(1501,263),坐标单一真相源);``mouse_move`` 先行保留(bug#1 缓解:
恢复原语同坐标点击曾落空,原分支注释)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口锚门(「标识-刷新概率表」,与外循环 0e2 分发判定同源同参;miss 未发
= round_fail 交回外循环重判,「下一帧重判」是外循环职责)+ obs{
on_screen} 挂实例属性(空决策形态无 report:本屏零容器写点,obs 类住
kernel/cw_screen_report/refresh_odds_popup.py,import 构造即可)。决策
动作 node = 重入裁决顶部(点 × 已发 → 锚 miss = 已离开本画面 → success
交回——出口 = 入口观察的合法重判,非动作层判效;锚在 = 再推进)→
area 读「按钮-关闭概率表」+ mouse_move+click 单次推进 → round_wait
循环(不烧节点重试预算,不收敛 = 动作 bug 响亮暴露,无防御上限;
「推进动作未落地」= round_fail 如实交回)。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.refresh_odds_popup import (
    CwScreenRefreshOddsPopupObs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenRefreshOddsPopup(SrOperation):
    """商店刷新概率表弹窗:点 × 关闭(mouse_move bug#1 缓解保留)。"""

    CLOSE_AREA = '按钮-关闭概率表'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-商店刷新概率表')
        # 画面档名/入口锚(与外循环 0e2 分发判定同源同参;实例属性)
        self._screen_name: str = '货币战争-商店刷新概率表'
        self._entry_area: str = '标识-刷新概率表'
        # 推进已发标志(验证废除形态):区分「首发锚 miss = 误分发 fail 交回」
        # 与「重入锚 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenRefreshOddsPopupObs | None = None

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:本画面锚校验(area 键原语,与分发判定同源同参)。"""
        return self.round_by_find_area(
            screen, self._screen_name, self._entry_area,
            crop_first=False).is_success

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口锚门 + obs{on_screen} 装载(空决策形态无 report)。

        门 miss = 首发误分发(分发判定帧命中 ∧ op 新帧锚 miss 的过渡帧):
        fail 交回外循环重判,不在 op 内等待重探。"""
        screen = self.last_screenshot
        if not self.entry_ok(screen):
            return self.round_fail(
                f'{self.op_name}入口锚未命中(交回外循环重判)')
        self._obs = CwScreenRefreshOddsPopupObs(on_screen=True, screen=screen)
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
        # 空锚 = 免锚出口(无「已离开」观察信号,发出即 success);本屏锚
        # 非空,分支结构性不可达,逐位保留空锚语义(参数化屏 = 备战暗色
        # 锁定为可达形态)。否则循环推进 = round_wait(不烧节点重试预算;
        # 不收敛 = 动作 bug 响亮暴露,无防御上限)。
        if not self._entry_area:
            return self.round_success(f'{self.op_name}推进已发(免锚)')
        return self.round_wait(f'{self.op_name}推进已发,重入观察裁决', wait=1)

    def progress_once(self) -> bool:
        """推进处理:读「按钮-关闭概率表」center → mouse_move+click
        (缺失 = False 如实交回;建档缺失场景分发锚预检会先炸,此处兜不
        命中;mouse_move bug#1 缓解保留)。"""
        close = area_center(self.ctx, self.CLOSE_AREA, self._screen_name)
        if close is None:
            return False
        self.ctx.controller.mouse_move(close)
        self.ctx.controller.click(close)
        return True
