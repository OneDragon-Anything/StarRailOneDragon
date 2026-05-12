import os
from typing import List, Optional

from one_dragon.base.config.yaml_operator import YamlOperator
from one_dragon.utils import os_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.world_patrol import world_patrol_route_utils
from sr_od.sr_map.sr_map_data import SrMapData
from sr_od.sr_map.sr_map_def import Planet, Region, SpecialPoint
from sr_od.application.world_patrol.world_patrol_route import WorldPatrolRoute
from sr_od.application.world_patrol.world_patrol_whitelist_config import WorldPatrolWhitelist, WorldPatrolWhiteListType


class WorldPatrolRouteData:

    def __init__(self, map_data: SrMapData):
        self.map_data: SrMapData = map_data

    def load_all_route(self, whitelist: WorldPatrolWhitelist = None, finished: List[str] = None,
                       target_planet: Optional[Planet] = None,
                       target_region: Optional[Region] = None,
                       include_public: bool = True,
                       include_personal: bool = True,
                       ) -> List[WorldPatrolRoute]:
        """
        加载所有路线
        :param whitelist: 传入后 按名单筛选路线
        :param finished: 传入后 排除已经完成的路线
        :param target_planet: 传入后 筛选相同星球的路线
        :param target_region: 传入后 筛选相同区域的路线 忽略楼层
        :param include_public: 是否包含公共地图
        :param include_personal: 是否包含个人地图
        :return:
        """
        # 需要排除的部分
        finished_unique_id = [] if finished is None else finished

        route_list: List[WorldPatrolRoute] = []

        for planet in self.map_data.planet_list:
            for is_public in [True, False]:
                is_personal = not is_public
                if is_public and not include_public:
                    continue
                if is_personal and not include_personal:
                    continue

                planet_dir = world_patrol_route_utils.get_planet_route_dir(planet, personal=is_personal)

                for route_filename in os.listdir(planet_dir):
                    if not route_filename.endswith('.yml'):
                        continue

                    route_path = os.path.join(planet_dir, route_filename)
                    route = self.load_route_by_yaml_path(route_path,
                                                         target_planet=target_planet,
                                                         target_region=target_region,
                                                         finished_unique_id=finished_unique_id,
                                                         whitelist=whitelist)
                    if route is not None:
                        route_list.append(route)

        log.info('最终加载 %d 条线路 过滤已完成 %d 条 使用名单 %s',
                 len(route_list), len(finished_unique_id), 'None' if whitelist is None else whitelist.name)

        # 白名单的情况下 按照白名单的顺序返回
        if whitelist is not None and whitelist.type == WorldPatrolWhiteListType.WHITE.value.value:
            sorted_route_list = []
            for target_route_id in whitelist.list:
                for route in route_list:
                    if route.unique_id == target_route_id:
                        sorted_route_list.append(route)
                        break
            return sorted_route_list
        else:
            return route_list

    def load_route_by_yaml_path(self, yaml_path: str,
                                target_planet: Optional[Planet] = None,
                                target_region: Optional[Region] = None,
                                finished_unique_id: List[str] = None,
                                whitelist: WorldPatrolWhitelist = None) -> Optional[WorldPatrolRoute]:
        """
        :param yaml_path: 路线文件路径
        :param target_planet: 传入后 筛选相同星球的路线
        :param target_region: 传入后 筛选相同区域的路线 忽略楼层
        :param whitelist: 传入后 按名单筛选路线
        :param finished_unique_id: 传入后 排除已经完成的路线
        """
        yaml_op = YamlOperator(yaml_path)
        route_filename = os.path.basename(yaml_path)

        planet_name = yaml_op.get('planet', None)
        region_name = yaml_op.get('region', None)
        floor = yaml_op.get('floor', None)
        tp_name = yaml_op.get('tp', None)

        planet = self.map_data.best_match_planet_by_name(planet_name)
        if planet is None:
            log.error(f'路线 {route_filename} 无法匹配星球')
            return

        if target_planet is not None and target_planet.np_id != planet.np_id:
            return

        region = self.map_data.best_match_region_by_name(region_name, planet, target_floor=floor)
        if region is None:
            log.error(f'路线 {route_filename} 无法匹配区域')
            return

        if target_region is not None and target_region.pr_id != region.pr_id:
            return

        tp = self.map_data.best_match_sp_by_name(region, gt(tp_name, 'ocr'))
        if tp is None:
            log.error(f'路线 {route_filename} 无法匹配传送点')
            return

        route = WorldPatrolRoute(tp, yaml_op.data, yaml_path)
        route_id = route.unique_id

        if finished_unique_id is not None and route_id in finished_unique_id:
            return

        if whitelist is not None:
            if whitelist.type == 'white' and route_id not in whitelist.list:
                return
            if whitelist.type == 'black' and route_id in whitelist.list:
                return

        return route

    @staticmethod
    def get_personal_route_dir() -> str:
        """
        个人用的路线文件夹
        """
        return os_utils.get_path_under_work_dir('config', 'world_patrol', 'personal')


    def get_new_route_path(self, tp: SpecialPoint, personal: bool = True) -> str:
        """
        获取新路线的文件路径
        """
        existed_route_list = self.load_all_route(target_region=tp.region,
                                                 include_public=not personal,
                                                 include_personal=personal)
        max_route_idx_in_region: int = 0
        max_route_idx_in_tp: int = 0
        for route in existed_route_list:
            if route.tp.region.pr_id == tp.region.pr_id:
                max_route_idx_in_region = max(max_route_idx_in_region, route.route_num_in_region)
            if route.tp.unique_id == tp.unique_id:
                max_route_idx_in_tp = max(max_route_idx_in_tp, route.route_num_in_tp)

        planet_dir = world_patrol_route_utils.get_planet_route_dir(tp.planet, personal)
        route_filename = f'{tp.planet.np_id}_{tp.region.r_id}_R{(max_route_idx_in_region + 1):02d}_{tp.id}_{max_route_idx_in_tp + 1}.yml'
        route_path = os.path.join(planet_dir, route_filename)
        return route_path

    def create_new_route(self, tp: SpecialPoint, author: str, personal: bool = True) -> WorldPatrolRoute:
        """
        根据传送点 创建一条路线
        :param tp:
        :return:
        """
        route_path = self.get_new_route_path(tp, personal)
        return WorldPatrolRoute(tp, {
            'author': [author],
            'route': []
        }, route_path)

    def save_route(self, route: WorldPatrolRoute, author: str, personal: bool = True):
        """
        保存路线
        """
        planet_dir = world_patrol_route_utils.get_planet_route_dir(route.tp.planet, personal=personal)
        route_filename = f'{route.tp.planet.np_id}_{route.tp.region.r_id}_R{route.route_num_in_region:02d}_{route.tp.id}_{route.route_num_in_tp}.yml'
        route_path = os.path.join(planet_dir, route_filename)

        if route.yml_file_path != route_path:
            route.delete()
            route.yml_file_path = self.get_new_route_path(route.tp, personal=personal)
            route.init_route_num()

        route.save()


if __name__ == '__main__':
    d = WorldPatrolRouteData(SrMapData())
    d.load_all_route()
