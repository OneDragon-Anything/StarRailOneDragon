import cv2
import numpy as np
import os
import shutil
import yaml
from cv2.typing import MatLike
from typing import List, Optional, Tuple

from one_dragon.base.geometry.point import Point
from one_dragon.utils import cv2_utils, os_utils
from one_dragon.utils.i18_utils import gt
from sr_od.app.world_patrol.world_patrol_route import WorldPatrolRouteOperation
from sr_od.config import operation_const
from sr_od.sr_map.sr_map_data import SrMapData
from sr_od.sr_map.sr_map_def import Region


class SimUniRoute:

    def __init__(self, route_id: str,
                 map_data: SrMapData,
                 idx: Optional[int] = None):
        """
        模拟宇宙路线配置，每条路线最后应该结束在选择下一关之前
        :param route_id: 楼层分类id
        :param idx: 下标。为空时说明是新建路线
        """
        self.map_data: SrMapData = map_data

        self.support_world: Optional[List[int]] = None  # 可以在第几宇宙中使用
        self.route_id: str = route_id

        self.idx: Optional[int] = None
        self.mm: Optional[MatLike] = None
        self.mm2: Optional[MatLike] = None  # 有极少数地图 重进后初始小地图不一样
        self.region: Optional[Region] = None
        self.start_pos: Optional[Point] = None
        self.op_list: List[WorldPatrolRouteOperation] = []
        self.next_pos_list: Optional[List[Point]] = None  # 下一楼层入口位置
        self.reward_pos: Optional[Point] = None  # 沉浸奖励
        self.algo: int = 1  # 使用算法

        if idx is None:
            self._create_new_route()
        else:
            self.idx = idx
            self._read_route()

    def load_from_route_yml(self, data: dict):
        self.support_world = data.get('support_world', [])
        planet_name = data['planet']
        planet = self.map_data.get_planet_by_cn(planet_name)
        region_name = data['region']
        floor = data['floor']
        self.region = self.map_data.best_match_region_by_name(gt(region_name, 'game'), planet=planet, target_floor=floor)
        self.start_pos = Point(data['start_pos'][0], data['start_pos'][1])
        self.op_list = [WorldPatrolRouteOperation(**i) for i in data.get('op_list', [])]
        self.next_pos_list = [Point(i[0], i[1]) for i in data.get('next_pos_list', [])]
        self.reward_pos = Point(data['reward_pos'][0], data['reward_pos'][1]) if 'reward_pos' in data else None
        self.algo = data.get('algo', 1)

    def _create_new_route(self):
        """
        新建一个模拟宇宙路线
        :return:
        """
        base_dir = SimUniRoute.get_uni_base_dir(self.route_id)
        self.idx = 1  # 获取合法的下标
        while True:
            route_dir = os.path.join(base_dir, '%03d' % self.idx)
            if os.path.exists(route_dir):
                self.idx += 1
            else:
                break
        self.op_list = []
        self.next_pos_list = []

    def _read_route(self):
        dir_path = self.get_route_dir_path()
        self.mm = cv2_utils.read_image(os.path.join(dir_path, 'mm.png'))
        self.mm2 = cv2_utils.read_image(os.path.join(dir_path, 'mm2.png'))
        with open(os.path.join(dir_path, 'route.yml'), 'r', encoding='utf-8') as file:
            route = yaml.safe_load(file)
            self.load_from_route_yml(route)

    @property
    def uid(self) -> str:
        """
        路线唯一标识 = 楼层类型 + 下标
        :return:
        """
        return SimUniRoute.get_uid(self.route_id, self.idx)

    @property
    def display_name(self) -> str:
        """
        展示名称
        :return:
        """
        return '%s %03d %s' % (
            self.route_id,
            self.idx,
            self.region.display_name
        )

    @staticmethod
    def get_uni_base_dir(level_type: str) -> str:
        """
        获取选定宇宙对应的文件夹位置
        :param level_type:
        :return:
        """
        return os_utils.get_path_under_work_dir('config', 'sim_uni', 'map',
                                                '%s' % level_type)

    @staticmethod
    def get_uid(level_type: str, idx: int) -> str:
        """
        路线唯一标识 = 楼层类型 + 下标
        :return:
        """
        return '%s_%03d' % (level_type, idx)

    def get_route_dir_path(self) -> str:
        """
        获取路线对应文件夹的位置
        :return:
        """
        return os_utils.get_path_under_work_dir('config', 'sim_uni', 'map',
                                                '%s' % self.route_id,
                                                '%03d' % self.idx)

    def save(self):
        """
        保存
        :return:
        """
        route_dir = self.get_route_dir_path()
        mm_path = os.path.join(route_dir, 'mm.png')
        if not os.path.exists(mm_path):
            cv2.imwrite(mm_path, self.mm)

        route_path = os.path.join(route_dir, 'route.yml')
        with open(route_path, "w", encoding="utf-8") as file:
            file.write(self.get_route_text())

    def get_route_text(self) -> str:
        """
        获取当前路线的文本
        :return:
        """
        cfg: str = ''
        if self.region is None:
            return cfg

        if self.support_world is not None and len(self.support_world) > 0:
            cfg += 'support_world: %s\n' % self.support_world

        cfg += "planet: '%s'\n" % self.region.planet.cn
        cfg += "region: '%s'\n" % self.region.cn
        cfg += "floor: %d\n" % self.region.floor
        cfg += f'algo: {self.algo}\n'
        cfg += "start_pos: [%d, %d]\n" % (self.start_pos.x, self.start_pos.y)

        if len(self.next_pos_list) == 0:
            cfg += "next_pos_list: []\n"
        else:
            cfg += "next_pos_list:\n"
            for pos in self.next_pos_list:
                cfg += "  - [%d, %d]\n" % (pos.x, pos.y)

        if self.reward_pos is not None:
            cfg += "reward_pos: [%d, %d]\n" % (self.reward_pos.x, self.reward_pos.y)

        if len(self.op_list) == 0:
            cfg += "op_list: []\n"
        else:
            cfg += "op_list:\n"
            last_floor = self.region.floor
            for route_item in self.op_list:
                if route_item.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE, operation_const.OP_NO_POS_MOVE,
                                        operation_const.OP_UPDATE_POS]:
                    cfg += "  - op: '%s'\n" % route_item.op
                    pos = route_item.data
                    if len(pos) > 2 and pos[2] != last_floor:
                        cfg += "    data: [%d, %d, %d]\n" % (pos[0], pos[1], pos[2])
                        last_floor = pos[2]
                    else:
                        cfg += "    data: [%d, %d]\n" % (pos[0], pos[1])
                elif route_item.op in [operation_const.OP_PATROL, operation_const.OP_DISPOSABLE]:
                    cfg += "  - op: '%s'\n" % route_item.op
                elif route_item.op == operation_const.OP_INTERACT:
                    cfg += "  - op: '%s'\n" % route_item.op
                    cfg += "    data: '%s'\n" % route_item.data
                elif route_item.op == operation_const.OP_WAIT:
                    cfg += "  - op: '%s'\n" % route_item.op
                    cfg += "    data: ['%s', '%s']\n" % (route_item.data[0], route_item.data[1])
        return cfg

    def delete(self):
        """
        删除路线
        :return:
        """
        route_dir = self.get_route_dir_path()
        shutil.rmtree(route_dir)

    @property
    def is_last_op_move(self) -> bool:
        """
        最后一个操作是移动
        :return:
        """
        l = len(self.op_list)
        if l == 0:
            return False
        op = self.op_list[l - 1].op
        return op == operation_const.OP_MOVE or op == operation_const.OP_SLOW_MOVE

    @property
    def no_battle_op(self) -> bool:
        """
        整个路线中没有战斗
        :return:
        """
        for op in self.op_list:
            if op.op == operation_const.OP_PATROL:
                return False
        return True

    @property
    def last_pos(self) -> Tuple[Region, Point]:
        """
        获取最后的位置 应该是最后一个 op=move 的位置
        :return:
        """
        region = self.region
        pos = self.start_pos
        if self.op_list is None or len(self.op_list) == 0:
            return region, pos
        for op in self.op_list:
            if op.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE, operation_const.OP_NO_POS_MOVE]:
                pos = Point(op.data[0], op.data[1])
                if len(op.data) > 2 and op.data[2] != region.floor:
                    region = self.map_data.best_match_region_by_name(gt(region.cn, 'game'), planet=region.planet, target_floor=op.data[2])
        return region, pos

    @property
    def next_pos(self) -> Optional[Point]:
        if self.next_pos_list is None or len(self.next_pos_list) == 0:
            return None
        avg_pos_x = np.mean([pos.x for pos in self.next_pos_list], dtype=np.uint16)
        avg_pos_y = np.mean([pos.y for pos in self.next_pos_list], dtype=np.uint16)
        return Point(avg_pos_x, avg_pos_y)

    def add_support_world(self, num: int):
        """
        添加一个支持的世界
        :param num: 第几世界
        :return:
        """
        if self.support_world is None:
            self.support_world = []
        if num not in self.support_world:
            self.support_world.append(num)
            self.support_world.sort()

    @property
    def last_op(self) -> Optional[WorldPatrolRouteOperation]:
        if self.op_list is None or len(self.op_list) == 0:
            return None
        else:
            return self.op_list[-1]

    def add_move(self, pos: Point, patrol: bool = False):
        """
        增加一个移动指令
        :param pos:
        :param patrol: 是否追加一个攻击指令
        :return:
        """
        self.op_list.append(WorldPatrolRouteOperation(op=operation_const.OP_MOVE, data=[pos.x, pos.y]))
        if patrol:
            self.op_list.append(WorldPatrolRouteOperation(op=operation_const.OP_PATROL))

    def switch_floor(self, floor: int):
        """
        只有最后一个指令是移动时生效
        将该指令多加一个楼层
        :param floor:
        :return:
        """
        if self.op_list is None or len(self.op_list) == 0:
            return
        idx = len(self.op_list) - 1
        if self.op_list[idx].op not in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE, operation_const.OP_NO_POS_MOVE]:
            return
        self.op_list[idx].data = [
            self.op_list[idx].data[0],
            self.op_list[idx].data[1],
            floor
        ]
