import os
from typing import Optional, List, Tuple, Any

from one_dragon.base.geometry.point import Point
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.config import operation_const
from sr_od.sr_map.sr_map_def import Region, SpecialPoint


class WorldPatrolRouteOperation:

    def __init__(self, op: str, data: Any = None, idx: int = 0):
        self.op: str = op
        """指令类型 operation_const"""

        self.data: Any = data
        """
        指令数据
        move, update_pos: (x, y, floor) - 坐标和切换楼层
        patrol, disposable: 攻击，无data
        interact: 交互文本
        wait: (type, timeout) - 等待类型和超时时间
        """

        self.idx: int = idx
        """指令下标 仅在画图时有用"""


class WorldPatrolRoute:

    def __init__(self, tp: SpecialPoint,
                 route_data: dict,
                 yml_file_path: str):
        self.author_list: List[str] = []
        self.tp: Optional[SpecialPoint] = tp
        self.route_list: List[WorldPatrolRouteOperation] = []

        self.is_new: bool = False  # 新否新路线未保存

        self.yml_file_path: str = yml_file_path
        self.is_personal: bool = yml_file_path.find('personal') != -1
        self.route_num_in_region: int = 0
        self.route_num_in_tp: int = 0
        self.init_from_yaml_data(route_data)
        self.init_route_num()

    def init_from_yaml_data(self, yaml_data: dict):
        self.author_list = yaml_data.get('author', [])
        yml_route_list = yaml_data.get('route', [])
        self.route_list = []
        for yml_route_item in yml_route_list:
            item = WorldPatrolRouteOperation(op=yml_route_item['op'],
                                             data=yml_route_item.get('data', None))
            self.route_list.append(item)
        self.init_idx()

    def init_idx(self):
        """
        重新初始化下标
        :return:
        """
        idx = 1
        for item in self.route_list:
            item.idx = idx
            idx += 1

    def init_route_num(self) -> None:
        """
        初始化显示名称
        :return:
        """
        if self.yml_file_path == '':  # 绘制路线页面 未新建时候的路径
            return
        route_id = self.unique_id
        id_arr = route_id.split('_')
        if self.is_personal:
            id_arr.pop(0)

        self.route_num_in_tp = 1 if len(id_arr[-1]) > 1 else int(id_arr[-1])
        self.route_num_in_region = int(id_arr[4][1:])

    @property
    def display_name(self):
        """
        用于前端显示路线名称
        :return:
        """
        old_name = '%s_%s_%s_%02d' % (
            gt(self.tp.planet.cn),
            gt(self.tp.region.cn),
            gt(self.tp.cn),
            self.route_num_in_region
        )
        if self.is_personal:
            return f'个人_{old_name}'
        else:
            return old_name

    @property
    def unique_id(self) -> str:
        """
        唯一标识 用于各种配置中保存
        :return:
        """
        if self.is_personal:
            return f'personal_{os.path.basename(self.yml_file_path)[:-4]}'
        else:
            return os.path.basename(self.yml_file_path)[:-4]

    def save(self):
        """
        保存
        :return:
        """
        file_path = self.yml_file_path
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(self.route_config_str)
        log.info('保存成功 %s', file_path)
        self.is_new = False

    def delete(self):
        """
        删除路线
        :return:
        """
        file_path = self.yml_file_path
        if os.path.exists(file_path):
            os.remove(file_path)
        log.info('删除成功 %s', file_path)

    def add_author(self, new_author: str, save: bool = True):
        """
        增加一个作者
        :param new_author: 作者名称
        :param save: 是否保存
        :return:
        """
        if self.author_list is None:
            self.author_list = []
        if new_author not in self.author_list:
            self.author_list.append(new_author)
        if save:
            self.save()

    @property
    def route_config_str(self) -> str:
        cfg: str = ''
        if self.tp is None:
            return cfg
        last_floor = self.tp.region.floor
        cfg += "author: %s\n" % self.author_list
        cfg += "planet: '%s'\n" % self.tp.planet.cn
        cfg += "region: '%s'\n" % self.tp.region.cn
        cfg += "floor: %d\n" % last_floor
        cfg += "tp: '%s'\n" % self.tp.cn
        cfg += "route:\n"
        for route_item in self.route_list:
            cfg += f"  - idx: {route_item.idx}\n"
            if route_item.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE,
                                 operation_const.OP_UPDATE_POS]:
                cfg += "    op: '%s'\n" % route_item.op
                pos = route_item.data
                if len(pos) > 2 and pos[2] != last_floor:
                    cfg += "    data: [%d, %d, %d]\n" % (pos[0], pos[1], pos[2])
                    last_floor = pos[2]
                else:
                    cfg += "    data: [%d, %d]\n" % (pos[0], pos[1])
            elif route_item.op == operation_const.OP_NO_POS_MOVE:
                cfg += "    op: '%s'\n" % route_item.op
                cfg += "    data: [%d, %d, %d]\n" % (route_item.data[0], route_item.data[1], route_item.data[2])
            elif route_item.op in [operation_const.OP_PATROL, operation_const.OP_DISPOSABLE, operation_const.OP_CATAPULT]:
                cfg += "    op: '%s'\n" % route_item.op
            elif route_item.op == operation_const.OP_INTERACT:
                cfg += "    op: '%s'\n" % route_item.op
                cfg += "    data: '%s'\n" % route_item.data
            elif route_item.op == operation_const.OP_GAMEPLAY_INTERACT:
                cfg += "    op: '%s'\n" % route_item.op
                cfg += "    data: ['%s']\n" % route_item.data[0]
            elif route_item.op == operation_const.OP_WAIT:
                cfg += "    op: '%s'\n" % route_item.op
                cfg += "    data: ['%s', '%s']\n" % (route_item.data[0], route_item.data[1])
            elif route_item.op == operation_const.OP_ENTER_SUB:
                cfg += "    op: '%s'\n" % route_item.op
                cfg += "    data: ['%s', '%s']\n" % (route_item.data[0], route_item.data[1])
            elif route_item.op in [operation_const.OP_ALLOW_TECH, operation_const.OP_BAN_TECH]:
                cfg += "    op: '%s'\n" % route_item.op

        return cfg

    def reset(self, new_route_list: Optional[List] = None):
        """
        重置所有指令
        :return:
        """
        if new_route_list is None:
            self.route_list = []
        else:
            self.route_list = new_route_list

    def add_catapult(self):
        """
        增加交互指令
        :return:
        """
        to_add = WorldPatrolRouteOperation(op=operation_const.OP_CATAPULT)
        self.route_list.append(to_add)
        self.init_idx()

    def switch_floor(self, new_floor: int):
        """
        在最后一个移动指令中变更楼层
        :param new_floor:
        :return:
        """
        if self.empty_op:
            return

        last_idx = len(self.route_list) - 1
        last_op = self.route_list[last_idx]
        if last_op.op not in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE]:
            return

        self.route_list[last_idx].data = (
            self.route_list[last_idx].data[0],
            self.route_list[last_idx].data[1],
            new_floor
        )

    @property
    def empty_op(self) -> bool:
        """
        当前指令为空
        :return:
        """
        return self.route_list is None or len(self.route_list) == 0

    @property
    def last_sub_region_op(self) -> Optional[WorldPatrolRouteOperation]:
        """
        最后一个子区域的中文
        :return:
        """
        if self.empty_op:
            return None
        op = None
        for o in self.route_list:
            if o.op == operation_const.OP_ENTER_SUB:
                op = o
        return op
