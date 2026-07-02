import time

from cv2.typing import MatLike

from basic.i18_utils import gt
from basic.img import MatchResult
from sr.context.context import Context
from sr.operation import Operation, OperationOneRoundResult
from sr.operation.unit.forgotten_hall import get_mission_num_pos


class ChooseMission(Operation):

    def __init__(self, ctx: Context, mission_num: int):
        """
        根据关卡数字 点击对应的关卡
        :param ctx: 应用上下文
        :param mission_num: 选择哪个关卡 1~10
        """
        super().__init__(ctx, try_times=5, op_name='%s %d' % (gt('逐光捡金 选择关卡'), mission_num))
        self.mission_num: int = mission_num

    def _execute_one_round(self) -> OperationOneRoundResult:
        screen: MatLike = self.screenshot()

        num_result: MatchResult = get_mission_num_pos(self.ctx, self.mission_num, screen, drag_when_not_found=True)
        if num_result is None:
            return self.round_retry('未找到关卡')

        if self.ctx.controller.click(num_result.center):
            time.sleep(1.5)  # 等待加载页面
            return self.round_success()
        else:
            return self.round_retry('点击关卡失败')
