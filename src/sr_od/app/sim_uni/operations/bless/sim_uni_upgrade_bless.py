import cv2
from cv2.typing import MatLike
from typing import Optional, List, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class SimUniUpgradeBless(SrOperation):

    UPGRADE_BTN: ClassVar[Rect] = Rect(1566, 960, 1862, 1011)  # 强化
    EXIT_BTN: ClassVar[Rect] = Rect(1829, 40, 1898, 95)  # 退出
    BLESS_RECT: ClassVar[Rect] = Rect(60, 216, 1368, 955)  # 所有祝福的框
    LEFT_RECT: ClassVar[Rect] = Rect(1680, 50, 1770, 80)  # 剩余碎片的数字

    STATUS_UPGRADE: ClassVar[str] = '强化成功'
    STATUS_NO_UPGRADE: ClassVar[str] = '无法强化'

    def __init__(self, ctx: SrContext):
        """
        模拟宇宙 强化祝福
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('强化祝福')))

        self.left_num: int = 0  # 剩余碎片数量
        self.upgrade_list: List[MatchResult] = []  # 可升级的祝福的点击位置
        self.upgrade_idx: int = 0  # 当前需要升级的祝福下标

    @operation_node(name='识别剩余碎片', is_start_node=True)
    def check_left(self) -> OperationRoundResult:
        """
        识别剩余的碎片数量
        :return:
        """
        screen = self.screenshot()

        state = sim_uni_screen_state.get_sim_uni_screen_state(self.ctx, screen, self.ctx.ocr, upgrade_bless=True)

        if state != sim_uni_screen_state.ScreenState.SIM_UPGRADE_BLESS.value:
            return self.round_retry('未在祝福强化页面', wait=1)

        num = self._get_left_num(screen)
        if num is None:
            return self.round_retry('识别剩余碎片失败', wait=1)
        else:
            self.left_num = num
            return self.round_success()

    def _get_left_num(self, screen: MatLike) -> Optional[int]:
        """
        识别剩余的碎片数量
        :return:
        """
        part = cv2_utils.crop_image_only(screen, SimUniUpgradeBless.LEFT_RECT)
        digit_str = self.ctx.ocr.run_ocr_single_line(part)
        return str_utils.get_positive_digits(digit_str, err=None)

    @node_from(from_name='识别剩余碎片')
    @operation_node(name='识别可升级祝福')
    def check_can_upgrade(self) -> OperationRoundResult:
        """
        识别可升级的祝福 按剩余碎片数量保留
        :return:
        """
        screen = self.screenshot()
        self._get_bless_pos_list(screen)

        return self.round_success()

    def _get_bless_pos_list(self, screen: MatLike) -> None:
        """
        获取一个可以强化的祝福位置
        :param screen: 屏幕截图
        :return: 可强化的祝福列表 每个元素对应碎片数量的识别结果 MatchResult.data=升级祝福需要的碎片
        """
        part = cv2_utils.crop_image_only(screen, SimUniUpgradeBless.BLESS_RECT)
        money_icon_mrl = self.ctx.tm.match_template(part, 'sim_uni', 'store_money',
                                                    ignore_template_mask=True, threshold=0.65, only_best=False)

        total_num: int = 0  # 当前累计使用的碎片数量
        # cv2_utils.show_image(part, money_icon_mrl, win_name='all')
        for mr in money_icon_mrl:
            lt = SimUniUpgradeBless.BLESS_RECT.left_top + mr.center + Point(15, -15)
            rb = SimUniUpgradeBless.BLESS_RECT.left_top + mr.center + Point(65, 12)
            digit_rect = Rect(lt.x, lt.y, rb.x, rb.y)
            digit_part = cv2_utils.crop_image_only(screen, digit_rect)
            white_part = cv2_utils.get_white_part(digit_part)
            to_ocr = cv2.bitwise_and(digit_part, digit_part, mask=white_part)
            # cv2_utils.show_image(white_part, win_name='digit_part', wait=0)
            ocr_result = self.ctx.ocr.run_ocr_single_line(to_ocr)
            digit = str_utils.get_positive_digits(ocr_result, 0)
            if digit == 0:
                continue
            if total_num + digit > self.left_num:
                continue
            total_num += digit
            self.upgrade_list.append(MatchResult(1, digit_rect.x1, digit_rect.x2, digit_rect.width, digit_rect.height,
                                                 data=digit))
            if total_num + 100 > self.left_num:  # 比较粗糙认为最少要100才能强化
                break

    @node_from(from_name='识别可升级祝福')
    @node_from(from_name='点击空白', status=STATUS_UPGRADE)
    @operation_node(name='选择祝福')
    def choose_bless(self) -> OperationRoundResult:
        """
        选择一个祝福
        :return:
        """
        if self.upgrade_idx >= len(self.upgrade_list):
            return self.round_success(SimUniUpgradeBless.STATUS_NO_UPGRADE)

        screen = self.screenshot()

        state = sim_uni_screen_state.get_sim_uni_screen_state(self.ctx, screen, self.ctx.ocr, upgrade_bless=True)

        if state != sim_uni_screen_state.ScreenState.SIM_UPGRADE_BLESS.value:
            return self.round_retry('未在祝福强化页面', wait=1)

        self.ctx.controller.click(self.upgrade_list[self.upgrade_idx].center)
        self.upgrade_idx += 1
        return self.round_success(SimUniUpgradeBless.STATUS_UPGRADE, wait=0.2)

    @node_from(from_name='选择祝福', status=STATUS_UPGRADE)
    @operation_node(name='升级')
    def upgrade(self) -> OperationRoundResult:
        """
        升级
        :return:
        """
        screen = self.screenshot()

        if self._can_upgrade(screen):
            click = self.ctx.controller.click(SimUniUpgradeBless.UPGRADE_BTN.center)
            if click:
                return self.round_success(SimUniUpgradeBless.STATUS_UPGRADE, wait=2)
            else:
                return self.round_retry('点击强化失败')
        else:
            return self.round_success(SimUniUpgradeBless.STATUS_NO_UPGRADE)

    def _can_upgrade(self, screen: MatLike) -> bool:
        part = cv2_utils.crop_image_only(screen, SimUniUpgradeBless.UPGRADE_BTN)
        white = cv2_utils.get_white_part(part)
        to_ocr = cv2.bitwise_and(part, part, mask=white)
        ocr_result = self.ctx.ocr.run_ocr_single_line(to_ocr)

        return str_utils.find_by_lcs(gt('强化', 'ocr'), ocr_result, percent=0.1)

    @node_from(from_name='升级', status=STATUS_UPGRADE)
    @operation_node(name='点击空白')
    def click_empty(self) -> OperationRoundResult:
        """
        点击空白继续
        :return:
        """
        screen = self.screenshot()
        state = sim_uni_screen_state.get_sim_uni_screen_state(self.ctx, screen, self.ctx.ocr,
                                                              upgrade_bless=True, empty_to_close=True)

        if state == sim_uni_screen_state.ScreenState.SIM_UPGRADE_BLESS.value:
            return self.round_success(SimUniUpgradeBless.STATUS_NO_UPGRADE)
        else:
            self.round_by_click_area('模拟宇宙', '点击空白处关闭')
            return self.round_success(SimUniUpgradeBless.STATUS_UPGRADE, wait=1)

    @node_from(from_name='识别剩余碎片', success=False)
    @node_from(from_name='升级', status=STATUS_NO_UPGRADE)
    @node_from(from_name='选择祝福', status=STATUS_NO_UPGRADE)
    @operation_node(name='退出')
    def exit(self) -> OperationRoundResult:
        """
        退出强化页面
        :return:
        """
        click = self.ctx.controller.click(SimUniUpgradeBless.EXIT_BTN.center)
        if click:
            return self.round_success(wait=1)
        else:
            return self.round_retry('退出失败')