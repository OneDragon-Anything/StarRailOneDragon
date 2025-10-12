import time

import cv2
from cv2.typing import MatLike
from typing import ClassVar, Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class ChooseTeam(SrOperation):

    TEAM_NUM_RECT: ClassVar[Rect] = Rect(505, 40, 1380, 105)  # 配队号码
    TURN_ON_RECT: ClassVar[Rect] = Rect(1590, 960, 1760, 1000)  # 【启用】按钮

    def __init__(self, ctx: SrContext, team_num: int, on: bool = False):
        """
        需要在配队管理页面使用 选择对应配队
        :param ctx: 上下文
        :param team_num: 队伍编号
        :param on: 是否需要点击【启用】
        """
        SrOperation.__init__(self, ctx, op_name=gt('选择配队'))
        self.team_num: int = team_num
        self.on: bool = on

    @operation_node(name='选择配队', is_start_node=True)
    def choose_team(self) -> OperationRoundResult:
        if self.team_num == 0:
            return self.round_success()

        screen: MatLike = self.screenshot()

        if not self.in_secondary_ui(screen):
            return self.round_retry('未在配队页面', wait=1)

        num_pos = self.get_all_num_pos(screen)

        if self.team_num not in num_pos:
            # 正常情况应该识别到这么多数字
            # 如果没有的话 可能会是别角色遮挡了 issue #522
            # 先按间距推理补全数字的位置 点击后高亮了就能识别了
            if len(num_pos) < 7:
                new_num_pos = self.infer_num_pos(num_pos)
                if self.team_num in new_num_pos:
                    self.ctx.controller.click(new_num_pos[self.team_num])
                    return self.round_retry(status='推测位置点击', wait=0.5)

            with_larger: bool = False  # 是否有存在比目标数字大的
            for num in num_pos.keys():
                if num > self.team_num:
                    with_larger = True
                    break

            drag_from = ChooseTeam.TEAM_NUM_RECT.center
            drag_to = drag_from + (Point(200, 0) if with_larger else Point(-200, 0))
            self.ctx.controller.drag_to(drag_to, drag_from)

            return self.round_retry('未找到配队', wait=0.5)
        else:
            to_click: Point = num_pos[self.team_num]
            if self.ctx.controller.click(to_click):
                time.sleep(0.5)
                if not self.on:
                    return self.round_success()
                if self.ctx.controller.click(ChooseTeam.TURN_ON_RECT.center):
                    # 因为有可能本次选择配队没有改变队伍 即有可能不需要点启用 这里就偷懒不判断启用按钮是否出现了
                    return self.round_success()

            return self.round_retry('点击配队失败')

    def in_secondary_ui(self, screen: Optional[MatLike] = None) -> bool:
        """
        是否在组队的界面
        :param screen: 屏幕截图
        :return:
        """
        if screen is None:
            screen = self.screenshot()

        return common_screen_state.in_secondary_ui(self.ctx, screen, '队伍')

    def get_all_num_pos(self, screen: Optional[MatLike] = None) -> dict[int, Point]:
        """
        获取所有数字的位置
        :param screen: 屏幕截图
        :return:
        """
        if screen is None:
            screen = self.screenshot()

        part, _ = cv2_utils.crop_image(screen, ChooseTeam.TEAM_NUM_RECT)
        mask1 = cv2.inRange(part, (250, 225, 185), (255, 235, 195))
        mask2 = cv2.inRange(part, (135, 135, 135), (165, 165, 165))
        mask = cv2.bitwise_or(mask1, mask2)
        # cv2_utils.show_image(mask1, win_name='mask1')
        # cv2_utils.show_image(mask2, win_name='mask2')
        # cv2_utils.show_image(mask, win_name='get_all_num_pos', wait=0)

        to_ocr = cv2.bitwise_or(part, part, mask=mask)
        ocr_map = self.ctx.ocr.run_ocr(to_ocr)

        team_num_pos: dict[int, Point] = {}

        for word, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            team_num = str_utils.get_positive_digits(word, err=None)
            if team_num is None:
                continue

            team_num_pos[team_num] = mrl.max.center + ChooseTeam.TEAM_NUM_RECT.left_top

        return team_num_pos

    def infer_num_pos(self, num_pos: dict[int, Point]) -> dict[int, Point]:
        """
        根据已有的数字位置 推测识别不到的数字位置


        Args:
            num_pos:

        Returns:

        """
        if num_pos is None or len(num_pos) == 0:
            return {}

        new_num_pos = {}

        # 先找出最小值和最大值
        min_num: int = 100
        max_num: int = 0

        for num in num_pos.keys():
            new_num_pos[num] = num_pos[num]
            if num < min_num:
                min_num = num
            if num > max_num:
                max_num = num

        # 计算两个相邻数字的平均横坐标间隔
        x_dis_list: list[int] = []
        for num in range(min_num, max_num):
            if num not in num_pos:
                continue

            if num + 1 not in num_pos:
                continue

            x_dis_list.append(num_pos[num + 1].x - num_pos[num].x)

        # 没有足够数字计算距离
        if len(x_dis_list) == 0:
            return num_pos

        avg_x_dis: int = int(sum(x_dis_list) / len(x_dis_list))

        # 先在最小值到最大值范围内 找出缺失位置的补全
        for num in range(min_num, max_num + 1):
            if num in new_num_pos:  # 已经有坐标的 跳过
                continue

            prev_pos = new_num_pos[num - 1]
            curr_pos = prev_pos + Point(avg_x_dis, 0)
            new_num_pos[num] = curr_pos

        # 如果数字还不足 就往两边补全
        while len(new_num_pos) < 7:
            min_num = min_num - 1
            if min_num > 0:
                next_pos = new_num_pos[min_num + 1]
                curr_pos = next_pos - Point(avg_x_dis, 0)
                new_num_pos[min_num] = curr_pos

            max_num = max_num + 1
            prev_pos = new_num_pos[max_num - 1]
            curr_pos = prev_pos + Point(avg_x_dis, 0)
            new_num_pos[max_num] = curr_pos

        return new_num_pos


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()
    op = ChooseTeam(ctx, 1)
    op.execute()


if __name__ == '__main__':
    __debug()