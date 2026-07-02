from typing import ClassVar, Optional, Callable

from cv2.typing import MatLike

from basic import str_utils, Point
from basic.i18_utils import gt
from basic.img import cv2_utils
from basic.log_utils import log
from sr.context.context import Context
from sr.image.sceenshot import screen_state
from sr.operation import Operation, OperationOneRoundResult, OperationResult
from sr.screen_area.screen_treasures_lightward import ScreenTreasuresLightWard
from sr.treasures_lightward.treasures_lightward_const import TreasuresLightwardTypeEnum


class TlCheckTotalStar(Operation):
    """
    需要先在 忘却之庭 或者 虚构叙事 选择关卡的页面
    检测右下角数字判断当前星数
    返回附加状态 = 成功时是当前星数，失败时是原因
    """
    STATUS_FULL_STAR: ClassVar[str] = '满星'
    EMPTY_POINT: ClassVar[Point] = Point(900, 100)

    def __init__(self, ctx: Context, schedule_type: TreasuresLightwardTypeEnum,
                 op_callback: Optional[Callable[[OperationResult], None]] = None):
        super().__init__(ctx, try_times=5,
                         op_name='%s %s' % (gt(schedule_type.value), gt('获取总星数')),
                         op_callback=op_callback
                         )
        self.schedule_type: TreasuresLightwardTypeEnum = schedule_type

    def _execute_one_round(self) -> OperationOneRoundResult:
        screen: MatLike = self.screenshot()

        if not screen_state.in_secondary_ui(screen, self.ctx.ocr, self.schedule_type.value):
            self.ctx.controller.click(TlCheckTotalStar.EMPTY_POINT)  # 有可能时在显示说明 点击空白地方跳过
            log.info('等待%s加载', self.schedule_type.value)
            return self.round_retry('未在%s画面' % self.schedule_type.value, wait=1)

        star = self._get_star_cnt(screen)

        if star == -1:
            return self.round_retry('获取不到星数', wait=1)
        elif (self.schedule_type == TreasuresLightwardTypeEnum.FORGOTTEN_HALL and star > 36) or \
                (self.schedule_type == TreasuresLightwardTypeEnum.PURE_FICTION and star > 12):
            return self.round_retry('星数值异常 %d' % star, wait=1)
        else:
            full_star = (self.schedule_type == TreasuresLightwardTypeEnum.FORGOTTEN_HALL and star == 36) or \
                (self.schedule_type == TreasuresLightwardTypeEnum.PURE_FICTION and star == 12)
            return self.round_success(status=TlCheckTotalStar.STATUS_FULL_STAR if full_star else None, data=star)

    def _get_star_cnt(self, screen: MatLike) -> int:
        """
        获取星数
        :param screen: 屏幕截图
        :return: 星数。如果没有获取到就返回-1
        """
        area = ScreenTreasuresLightWard.FH_TOTAL_STAR.value
        part = cv2_utils.crop_image_only(screen, area.rect)
        # cv2_utils.show_image(part, win_name='_get_star_cnt')
        ocr_str = self.ctx.ocr.run_ocr_single_line(part, strict_one_line=True)
        return str_utils.get_positive_digits(ocr_str, -1)
