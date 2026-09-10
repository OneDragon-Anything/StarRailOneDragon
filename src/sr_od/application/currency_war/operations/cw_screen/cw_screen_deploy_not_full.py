
"""货币战争 出战确认弹窗(「可出战角色人数未达上限」)处理 op(从主循环拆出)。

勾「本局不再提示」+ 确认,解除 bench-full 警告阻塞出战。

勾选/确认坐标进 screen_info(``currency_war_deploy_not_full``):``勾选-本局不再提示`` +
``按钮-确认``,task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,缺失才用兜底常量。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    emit_overlay_confirm,
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenDeployNotFull(SrOperation):
    """出战人数未达上限弹窗:勾本局不再提示 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-未达上限警告'   # screen_info 画面(currency_war_deploy_not_full.yml)
    # 勾选/确认:screen_info center(task#20);常量=screen_info 缺失兜底。
    CHECKBOX_NO_PROMPT: ClassVar[Point] = Point(912, 589)   # 兜底;首选 area_center('勾选-本局不再提示')
    BTN_CONFIRM: ClassVar[Point] = Point(1159, 653)          # 兜底;首选 area_center('按钮-确认')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-未达上限确认')
        # 确认已发待重入裁决标志(单 op 生命周期):区分「首发锚 miss = 误分发
        # fail 交回」与「重入锚 miss = 弹窗已关 success 交回」(验证废除形态:
        # 用户裁定 2026-09-10 动作 op 禁验证,落地由下一轮重入入口观察裁决)。
        self._confirm_pending: bool = False

    @operation_node(name='未达上限确认', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 用 screen_info id_mark area(标识-未达上限警告)位置区分,非全屏 LCS:防「能量上限」(投资策略描述)
        # 与「未达上限」共享「上限」(2/4=0.5)误匹配(见 cw_loop 0d)。area 位置不同 → 不命中。
        _hit = self.round_by_find_area(
            screen, CwScreenDeployNotFull.SCREEN_NAME, '标识-未达上限警告').is_success
        if not _hit:
            if self._confirm_pending:
                # 重入裁决(观察驱动):上轮确认已发 → 锚不在 = 弹窗已关(落地
                # 与否归下一帧观察侧重分发;此处只认「本画面处理完结」)。
                self._confirm_pending = False
                return self.round_success('未达上限弹窗已关(重入观察裁决)', wait=3.0)
            return self.round_fail('非未达上限弹窗')
        self._confirm_pending = False
        _check = area_center(self.ctx, '勾选-本局不再提示', CwScreenDeployNotFull.SCREEN_NAME) or CwScreenDeployNotFull.CHECKBOX_NO_PROMPT
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenDeployNotFull.SCREEN_NAME) or CwScreenDeployNotFull.BTN_CONFIRM
        safe_click(self, _check, tag='cw-deploywarn')
        time.sleep(0.3)
        # 确认 + 机械交回(验证废除:不读屏判「弹窗关没关」,落地由下一轮重入
        # 入口观察裁决;锚仍在 = 重做一次,计节点预算)。原「点了就 success」
        # 不观察 → bug#1/勾选未生效 flat-loop 防线由重入裁决 + 预算耗尽 bail 承接。
        self._confirm_pending = True
        return emit_overlay_confirm(self, confirm_point=_confirm, entry_keyword='未达上限',
                                    lcs_percent=0.8, success_wait=3.0, tag='cw-deploywarn')
