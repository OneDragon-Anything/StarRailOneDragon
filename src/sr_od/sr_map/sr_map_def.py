from typing import Optional

from one_dragon.base.geometry.point import Point
from one_dragon.utils.i18_utils import gt


class Planet:

    def __init__(self, num: int, uid: str, cn: str):
        self.num: int = num  # 编号 用于强迫症给文件排序
        self.id: str = uid  # 用在找文件夹之类的
        self.cn: str = cn  # 中文

    def __repr__(self):
        return '%02d - %s' % (self.num, self.cn)

    @property
    def n_id(self):
        """
        编号ID
        :return:
        """
        return 'P%02d' % self.num

    @property
    def np_id(self):
        """
        带编号的唯一ID
        :return:
        """
        return '%s_%s' % (self.n_id, self.id)

    @property
    def display_name(self):
        return gt(self.cn)


class RegionSet:
    """一个区域的合集 是不区分楼层的 也就是 assets/game_data/world_patrol_map/P01_KJZHT/P01_KJZHT.yml 里面的内容"""

    def __init__(
            self,
            num: int,
            uid: str,
            cn: str,
            floors: list[int] | None = None,
            parent_region_name: str | None = None,
            parent_region_floor: int | None = None,
            enter_template_id: str | None = None,
            enter_lm_pos: list[int] | None = None,
    ):
        self.num: int = num  # 编号 方便列表排序
        self.id: str = uid  # 通常是中文的拼音 与num组成唯一标识 用于文件命名
        self.cn: str = cn  # 中文
        self.floors: list[int] = floors if floors is not None else [0]  #  楼层列表
        self.parent_region_name: str = parent_region_name  # 父区域的中文名称
        self.parent_region_floor: int = parent_region_floor  # 父区域的楼层
        self.enter_template_id: str = enter_template_id  # 父区域进入本子区域时的图标的模板id
        self.enter_lm_pos: list[int] = enter_lm_pos # 父区域进入本子区域时的图标在大地图上的坐标


class Region:

    def __init__(self, num: int, uid: str, cn: str, planet: Planet,
                 floor: int = 0,
                 parent: Optional = None,
                 enter_template_id: Optional[str] = None,
                 enter_lm_pos: Optional[Point] = None,
                 large_map_scale: Optional[int] = None):
        self.num: int = num  # 编号 方便列表排序
        self.id: str = uid  # 通常是中文的拼音 与num组成唯一标识 用于文件命名
        self.cn: str = cn  # 中文 用在OCR
        self.planet: Planet = planet
        self.floor: int = floor
        self.parent: Region = parent  # 子区域才会有 属于哪个具体区域
        self.enter_template_id: str = enter_template_id  # 子区域才会有 入口对应的模板ID
        self.enter_lm_pos: Point = enter_lm_pos  # 子区域才会有 在具体区域的哪个位置进入
        self.large_map_scale: int = 0 if large_map_scale is None else large_map_scale

    def __repr__(self):
        return '%s - %s' % (self.cn, self.id)

    @property
    def r_id(self) -> str:
        """
        星球+区域ID 用于不区分楼层的场景
        :return:
        """
        return 'R%02d_%s' % (self.num, self.id)

    @property
    def pr_id(self) -> str:
        """
        星球+区域ID 用于不区分楼层的场景
        :return:
        """
        return '%s_%s' % (self.planet.np_id, self.r_id)

    @property
    def l_str(self) -> str:
        """
        层数 正数用 l1 负数用 b1
        :return:
        """
        if self.floor == 0:
            return ''
        elif self.floor > 0:
            return '_F%d' % self.floor
        elif self.floor < 0:
            return '_B%d' % abs(self.floor)
        else:
            return ''

    @property
    def rl_id(self) -> str:
        """
        区域在星球下的唯一ID 用于文件夹
        :return 区域id + 楼层id
        """
        return '%s%s' % (self.r_id, self.l_str)

    @property
    def prl_id(self) -> str:
        """
        区域唯一ID 用于唯一标识
        :return 星球id + 区域id + 楼层id
        """
        return '%s_%s' % (self.planet.np_id, self.rl_id)

    @property
    def another_floor(self) -> bool:
        return self.floor != 0

    @property
    def display_name(self) -> str:
        if self.another_floor:
            return '%s %s' % (gt(self.cn, 'game'), gt('%d层' % self.floor, 'ocr'))
        else:
            return gt(self.cn, 'game')


class SpecialPoint:

    def __init__(self, uid: str, cn: str, region: Region, template_id: str, lm_pos: tuple, tp_pos: Optional[tuple] = None):
        self.id: str = uid  # 英文 用在找图
        self.cn: str = cn  # 中文 用在OCR
        self.region: Region = region  # 所属区域
        self.planet: Planet = region.planet  # 所属星球
        self.template_id: str = template_id  # 匹配模板
        self.lm_pos: Point = Point(lm_pos[0], lm_pos[1])  # 在大地图的坐标
        self.tp_pos: Point = Point(tp_pos[0], tp_pos[1]) if tp_pos is not None else self.lm_pos  # 传送落地的坐标

    def __repr__(self):
        return '%s - %s' % (self.cn, self.id)

    @property
    def display_name(self):
        return gt(self.cn, 'game')

    @property
    def unique_id(self):
        return '%s_%s' % (self.region.prl_id, self.id)
