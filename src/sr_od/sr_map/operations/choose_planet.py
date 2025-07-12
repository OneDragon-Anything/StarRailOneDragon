import time

import cv2
from cv2.typing import MatLike
from typing import Optional, List

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.config import game_const
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.sr_map import large_map_utils
from sr_od.sr_map.sr_map_def import Planet


class ChoosePlanet(SrOperation):

    def __init__(self, ctx: SrContext, planet: Planet):
        """
        在大地图页面 选择到对应的星球
        默认已经打开大地图了
        :param planet: 目标星球
        """
        self.planet: Planet = planet  # 目标星球
        SrOperation.__init__(self, ctx,
                             op_name='%s %s' % (gt('选择星球'), self.planet.display_name))

    @operation_node(name='选择', node_max_retry_times=10, is_start_node=True)
    def choose(self) -> OperationRoundResult:
        screen = self.screenshot()
        # 根据左上角判断当前星球是否正确
        planet = large_map_utils.get_planet(self.ctx, screen)
        if planet is not None and planet.np_id == self.planet.np_id:
            return self.round_success()

        if planet is not None:  # 在大地图
            log.info('当前在大地图 准备选择 星轨航图')
            result = self.round_by_find_and_click_area(screen, '大地图', '星轨航图')
            if result.is_success:
                return self.round_wait(result.status, wait=1)
            else:
                return self.round_retry(result.status, wait=0.5)
        else:
            log.info('当前在星轨航图')
            ocr_planet_list = self.get_planet_pos(screen)

            target_pos: Optional[MatchResult] = None
            with_planet_before_target: bool = False  # 当前屏幕上是否有目标星球之前的星球

            for planet in self.ctx.map_data.planet_list:
                for ocr_planet_mr in ocr_planet_list:
                    if ocr_planet_mr.data == self.planet:
                        target_pos = ocr_planet_mr
                        break
                    if ocr_planet_mr.data == planet:
                        with_planet_before_target = True

                if target_pos is not None:
                    break

                if planet == self.planet:
                    break

            if target_pos is not None:
                self.choose_planet_by_pos(target_pos)
                return self.round_wait(wait=3)
            else:  # 当前屏幕没有目标星球的情况
                drag_from = Point(game_const.STANDARD_RESOLUTION_W // 2, 100)
                drag_to = drag_from + Point(-400 if with_planet_before_target else 400, 0)
                self.ctx.controller.click(drag_from)  # 这里比较神奇 直接拖动第一次会失败
                self.ctx.controller.drag_to(drag_to, drag_from)
                return self.round_retry(wait=1)

    def get_planet_pos(self, screen: MatLike) -> List[MatchResult]:
        """
        获取星轨航图上 星球名字的位置
        :param screen: 屏幕截图
        :return: 星球位置 data中是对应星球 Planet
        """
        # 二值化后更方便识别字体
        gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
        _, mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        part = cv2.bitwise_and(screen, screen, mask=mask)

        words = [p.cn for p in self.ctx.map_data.planet_list]
        ocr_map = self.ctx.ocr.match_words(part, words, lcs_percent=self.ctx.game_config.planet_lcs_percent)

        result_list: List[MatchResult] = []
        for ocr_word, mrl in ocr_map.items():
            planet = self.ctx.map_data.best_match_planet_by_name(ocr_word)
            if planet is not None:
                mr = mrl.max
                mr.data = planet
                result_list.append(mr)

        return result_list

    def choose_planet_by_pos(self, pos: MatchResult):
        """
        根据目标位置 点击选择星球
        :param pos:
        :return:
        """
        drag_from = pos.center
        drag_to = drag_from + Point(0, -100)
        self.ctx.controller.drag_to(drag_to, drag_from)  # 这里比较奇怪 需要聚焦一段时间才能点击到星球
        time.sleep(0.1)
        self.ctx.controller.click(drag_to, press_time=1)