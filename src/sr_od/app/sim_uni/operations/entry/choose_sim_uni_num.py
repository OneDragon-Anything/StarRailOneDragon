from cv2.typing import MatLike
from typing import ClassVar, Optional, Callable

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.sim_uni_const import UNI_NUM_CN
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class ChooseSimUniNum(SrOperation):

    CURRENT_BTN: ClassVar[Point] = Point(1276, 567)  # 选择当前宇宙
    PREVIOUS_BTN: ClassVar[Point] = Point(1216, 198)  # 换到上一个宇宙
    NEXT_BTN: ClassVar[Point] = Point(1173, 929)  # 换到下一个宇宙

    STATUS_RESTART: ClassVar[str] = '重新开始'
    STATUS_CONTINUE: ClassVar[str] = '继续'

    def __init__(self, ctx: SrContext, num: int,
                 op_callback: Optional[Callable[[OperationResult], None]] = None):
        """
        需要在模拟宇宙入口页面中使用 且先选择了普通模拟宇宙
        选择对应的宇宙 如果有进行中的宇宙 会先继续完成
        返回结果中的 data 为实际挑战的第几宇宙
        :param ctx:
        :param num: 第几宇宙 支持 1~8
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s %d' % (gt('模拟宇宙', 'game'), gt('选择宇宙'), num),
                             op_callback=op_callback)

        self.num: int = num

    @operation_node(name='选择', node_max_retry_times=10, is_start_node=True)
    def choose(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()

        if not common_screen_state.in_secondary_ui(self.ctx, screen,
                                                   sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value):
            # 有可能出现了每周第一次打开的积分奖励进度画面 随便点击一个地方关闭
            self.round_by_click_area('通用画面', '左上角标题')
            return self.round_retry('未在模拟宇宙页面', wait=1)

        current_num = self._get_current_num(screen)

        if current_num is None:
            return self.round_retry('未识别到模拟宇宙数字', wait=1)
        elif current_num == self.num:
            self.ctx.controller.click(ChooseSimUniNum.CURRENT_BTN)
            return self.round_success(status=ChooseSimUniNum.STATUS_RESTART, wait=2, data=self.num)
        else:
            if self._is_going(screen):
                self.ctx.controller.click(ChooseSimUniNum.CURRENT_BTN)
                return self.round_success(status=ChooseSimUniNum.STATUS_CONTINUE, wait=2, data=current_num)

            if current_num > self.num:
                self.ctx.controller.click(ChooseSimUniNum.PREVIOUS_BTN)
                return self.round_retry('未选择目标宇宙', wait=2)
            else:
                self.ctx.controller.click(ChooseSimUniNum.NEXT_BTN)
                return self.round_retry('未选择目标宇宙', wait=2)

    def _get_current_num(self, screen: Optional[MatLike]) -> Optional[int]:
        """
        获取当前选择了哪个宇宙
        :param screen: 屏幕截图
        :return:
        """
        if screen is None:
            screen = self.screenshot()

        area_name_list = ['当前宇宙名称-1', '当前宇宙名称-2']
        for area_name in area_name_list:
            area = self.ctx.screen_loader.get_area('模拟宇宙', area_name)
            part = cv2_utils.crop_image_only(screen, area.rect)
            # cv2_utils.show_image(part, win_name='choose_sim_uni_num', wait=0)

            ocr_result = self.ctx.ocr.run_ocr_single_line(part)

            for num, word in UNI_NUM_CN.items():
                if str_utils.find_by_lcs(gt('第%s世界' % word, 'ocr'), ocr_result, percent=1):
                    return num

        return None

    def _is_going(self, screen: Optional[MatLike] = None) -> bool:
        """
        当前宇宙是否进行中
        :param screen: 屏幕截图
        :return:
        """
        if screen is None:
            screen = self.screenshot()

        area_name_list = ['宇宙入口-进行中-1', '宇宙入口-进行中-2']
        for area_name in area_name_list:
            result = self.round_by_find_area(screen, '模拟宇宙', area_name)
            if result.is_success:
                return True
        return False


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_for_sim_uni()
    ctx.start_running()
    op = ChooseSimUniNum(ctx, num=1)
    op.execute()


if __name__ == '__main__':
    __debug()
