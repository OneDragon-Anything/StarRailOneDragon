from cv2.typing import MatLike

from basic.i18_utils import gt
from basic.img import MatchResult
from sr.context.context import Context
from sr.operation import Operation, OperationOneRoundResult
from sr.operation.unit.forgotten_hall import get_mission_num_pos, get_mission_star_by_num_pos


class CheckMissionStar(Operation):

    def __init__(self, ctx: Context, mission_num: int):
        """
        找到关卡的数字 判断下方的星星数量
        返回附加状态为星数
        :param ctx: 应用上下文
        :param mission_num: 扫描哪个关卡 1~12
        """
        super().__init__(ctx, try_times=20, op_name='%s %d' % (gt('逐光捡金 获取关卡星数'), mission_num))
        self.mission_num: int = mission_num

    def _execute_one_round(self) -> OperationOneRoundResult:
        screen: MatLike = self.screenshot()

        num_result: MatchResult = get_mission_num_pos(self.ctx, self.mission_num, screen, drag_when_not_found=True)
        if num_result is None:
            return self.round_retry('未找到关卡')

        star: int = get_mission_star_by_num_pos(self.ctx, screen, num_result)

        return self.round_success(str(star), data=star)
