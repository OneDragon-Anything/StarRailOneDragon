"""货币战争 出战确认弹窗(「可出战角色人数未达上限」)处理 op(从主循环拆出)。

勾「本局不再提示」+ 确认,解除 bench-full 警告阻塞出战。

勾选/确认坐标进 screen_info(``currency_war_deploy_not_full``):``勾选-本局不再提示`` +
``按钮-确认``,task#20 已完成;本 op 经 ``cw_observation.area_center`` 读,缺失才用兜底常量。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleDeployNotFull(SrOperation):
    """出战人数未达上限弹窗:勾本局不再提示 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-未达上限警告'   # screen_info 画面(currency_war_deploy_not_full.yml)
    # 勾选/确认:screen_info center(task#20);常量=screen_info 缺失兜底。
    CHECKBOX_NO_PROMPT: ClassVar[Point] = Point(912, 589)   # 兜底;首选 area_center('勾选-本局不再提示')
    BTN_CONFIRM: ClassVar[Point] = Point(1159, 653)          # 兜底;首选 area_center('按钮-确认')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-未达上限确认')

    @operation_node(name='未达上限确认', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # lcs_percent=0.8:防「能量上限」(投资策略描述)与「未达上限」共享「上限」(2/4=0.5)误匹配(见 battle_loop 0d)。
        if not self.round_by_ocr(screen, '未达上限', lcs_percent=0.8).is_success:
            return self.round_fail('非未达上限弹窗')
        _check = area_center(self.ctx, '勾选-本局不再提示', HandleDeployNotFull.SCREEN_NAME) or HandleDeployNotFull.CHECKBOX_NO_PROMPT
        _confirm = area_center(self.ctx, '按钮-确认', HandleDeployNotFull.SCREEN_NAME) or HandleDeployNotFull.BTN_CONFIRM
        self.ctx.controller.click(_check)
        time.sleep(0.3)
        self.ctx.controller.click(_confirm)
        return self.round_success(wait=3)
