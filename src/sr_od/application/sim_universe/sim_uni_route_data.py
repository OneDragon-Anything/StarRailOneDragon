import os
from cv2.typing import MatLike
from typing import List, Optional

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.log_utils import log
from sr_od.application.sim_universe.sim_uni_route import SimUniRoute
from sr_od.application.sim_universe.sim_uni_data import SimUniLevelType
from sr_od.sr_map.sr_map_data import SrMapData


class SimUniRouteData:

    def __init__(self, map_data: SrMapData):
        self.map_data: SrMapData = map_data
        self.level_type_2_route_list: dict[str, List[SimUniRoute]] = {}

    def get_route_list(self, level_type: SimUniLevelType) -> List[SimUniRoute]:
        """
        获取宇宙对用的路线配置列表
        :param level_type: 楼层类型
        :return:
        """
        key = level_type.route_id
        if key in self.level_type_2_route_list:
            return self.level_type_2_route_list[key]

        arr = []
        base_dir = SimUniRoute.get_uni_base_dir(level_type.route_id)
        for sub in os.listdir(base_dir):
            sub_dir = os.path.join(base_dir, sub)
            if not os.path.isdir(sub_dir):
                continue
            route = self.load_one_route(level_type, sub)
            if route is None:
                continue
            arr.append(route)

        self.level_type_2_route_list[key] = arr
        return arr

    def load_one_route(self, level_type: SimUniLevelType, sub: str) -> Optional[SimUniRoute]:
        """
        加载一条路线
        :param level_type: 楼层类型
        :param sub: 路线下标
        :return:
        """
        base_dir = SimUniRoute.get_uni_base_dir(level_type.route_id)
        sub_dir = os.path.join(base_dir, sub)
        mm = os.path.join(sub_dir, 'mm.png')
        route = os.path.join(sub_dir, 'route.yml')

        if not os.path.exists(mm) or not os.path.exists(route):
            return None

        return SimUniRoute(level_type.route_id, self.map_data, int(sub))

    def clear_cache(self):
        self.level_type_2_route_list.clear()

    def match_best_sim_uni_route(self, uni_num: int, level_type: SimUniLevelType, mm: MatLike) -> Optional[SimUniRoute]:
        """
        根据开始点的小地图的截图 找到最合适的路线
        :param uni_num: 第几宇宙
        :param level_type: 楼层类型
        :param mm: 开始点的小地图截图
        :return:
        """
        route_list = self.get_route_list(level_type)
        target_route: Optional[SimUniRoute] = None
        target_mr: Optional[MatchResult] = None

        for same_world in [True, False]:  # 先匹配当前世界的 再匹配其他世界的
            for route in route_list:
                if (uni_num in route.support_world) != same_world:
                    continue
                source = route.mm
                template = cv2_utils.crop_image_only(mm, Rect(30, 30, 160, 160))
                mr = cv2_utils.match_template(source, template, threshold=0.6, only_best=True)

                if mr.max is None and route.mm2 is not None:
                    source = route.mm2
                    template, _ = cv2_utils.crop_image(mm, Rect(30, 30, 160, 160))
                    mr = cv2_utils.match_template(source, template, threshold=0.6, only_best=True)

                if mr.max is None:
                    continue

                if target_route is None or target_mr.confidence < mr.max.confidence:
                    target_route = route
                    target_mr = mr.max

        if target_route is not None and uni_num not in target_route.support_world:
            target_route.add_support_world(uni_num)
            target_route.save()

        if target_mr is not None:
            log.debug(f'当前匹配路线置信度 {target_mr.confidence:.2f}')

        return target_route


