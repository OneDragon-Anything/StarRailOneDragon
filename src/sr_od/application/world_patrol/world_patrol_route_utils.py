from one_dragon.utils import os_utils
from sr_od.sr_map.sr_map_def import Planet


def get_planet_route_dir(planet: Planet, personal: bool = False) -> str:
    """
    获取星球的路线文件夹目录
    :param planet:
    :param personal: 是否私人配置
    :return:
    """
    if personal:
        return os_utils.get_path_under_work_dir('config', 'world_patrol', 'personal', planet.np_id)
    else:
        return os_utils.get_path_under_work_dir('config', 'world_patrol', planet.np_id)