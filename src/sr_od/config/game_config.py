from enum import Enum
from typing import Optional

from one_dragon.base.config.basic_game_config import BasicGameConfig
from one_dragon.base.config.config_item import ConfigItem
from one_dragon.base.geometry.point import Point
from one_dragon_qt.widgets.setting_card.yaml_config_adapter import YamlConfigAdapter


class GameRegionEnum(Enum):

    CN = ConfigItem('国服', 'CN')
    ASIA = ConfigItem('亚服', 'Asia')
    AMERICA = ConfigItem('美服', 'America')
    EUROPE = ConfigItem('欧服', 'Europe')
    HKMOTW = ConfigItem('港澳台', 'hkmotw')


class RunModeEnum(Enum):
    """疾跑模式"""

    OFF = ConfigItem('不启用', 0)
    BTN = ConfigItem('通过按钮切换', 1)
    AUTO = ConfigItem('长按进入疾跑状态', 2)


class GameLanguageEnum(Enum):
    """游戏语言"""
    CN = ConfigItem('简体中文', 'cn')
    EN = ConfigItem('English', 'en')


PLANET_LCS_PERCENT = {
    'cn': 0.55,
    'en': 0.55
}

REGION_LCS_PERCENT = {
    'cn': 0.55,
    'en': 0.7
}

SPECIAL_POINT_LCS_PERCENT = {
    'cn': 0.55,
    'en': 0.55
}

CHARACTER_NAME_LCS_PERCENT = {
    'cn': 0.1,
    'en': 0.3
}


class MiniMapPos:

    def __init__(self, x, y, r):
        # 原点
        self.x = int(x)
        self.y = int(y)
        self.r = int(r)
        # 矩形左上角
        self.lx = self.x - self.r - 3
        self.ly = self.y - self.r - 3
        # 矩形右下角
        self.rx = self.x + self.r + 3
        self.ry = self.y + self.r + 3

    def __repr__(self):
        return "(%d, %d) %.2f" % (self.x, self.y, self.r)

    @property
    def mm_center(self) -> Point:
        """
        小地图截图上 中心点的坐标
        :return:
        """
        return Point((self.rx - self.lx) // 2, (self.ry - self.ly) // 2)


class GameConfig(BasicGameConfig):

    def __init__(self, instance_idx: Optional[int] = None):
        BasicGameConfig.__init__(self, instance_idx=instance_idx)
        self.mini_map_pos: MiniMapPos = MiniMapPos(139, 149, 93)

    @property
    def run_mode(self) -> int:
        """
        疾跑模式
        :return:
        """
        return self.get('run_mode', RunModeEnum.BTN.value.value)

    @run_mode.setter
    def run_mode(self, new_value: int):
        """
        更新疾跑模式
        :return:
        """
        self.update('run_mode', new_value)

    @property
    def run_mode_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'run_mode', RunModeEnum.BTN.value.value,
                                 'int', 'int')

    @property
    def turn_dx(self) -> float:
        return self.get('turn_dx', 27)

    @turn_dx.setter
    def turn_dx(self, new_value: float):
        self.update('turn_dx', new_value)

    @property
    def lang(self) -> str:
        """
        游戏语言
        :return:
        """
        return self.get('lang', GameLanguageEnum.CN.value.value)

    @lang.setter
    def lang(self, new_value: str):
        """
        更新游戏语言
        :return:
        """
        self.update('lang', new_value)

    def lang_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'lang', GameLanguageEnum.CN.value.value)

    @property
    def planet_lcs_percent(self):
        return PLANET_LCS_PERCENT[self.lang]

    @property
    def region_lcs_percent(self):
        return REGION_LCS_PERCENT[self.lang]

    @property
    def special_point_lcs_percent(self):
        return SPECIAL_POINT_LCS_PERCENT[self.lang]

    @property
    def character_name_lcs_percent(self):
        return CHARACTER_NAME_LCS_PERCENT[self.lang]

    @property
    def key_interact(self) -> str:
        """
        交互按钮
        :return:
        """
        return self.get('key_interact', 'f')

    @key_interact.setter
    def key_interact(self, new_value):
        """
        更新交互按钮
        :return:
        """
        self.update('key_interact', new_value)

    @property
    def key_interact_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'key_interact', 'f')

    @property
    def key_technique(self) -> str:
        """
        秘技按钮
        :return:
        """
        return self.get('key_technique', 'e')

    @key_technique.setter
    def key_technique(self, new_value):
        """
        更新秘技按钮
        :return:
        """
        self.update('key_technique', new_value)

    @property
    def key_open_map(self) -> str:
        """
        秘技按钮
        :return:
        """
        return self.get('key_open_map', 'm')

    @key_open_map.setter
    def key_open_map(self, new_value):
        """
        更新秘技按钮
        :return:
        """
        self.update('key_open_map', new_value)

    @property
    def key_esc(self) -> str:
        return self.get('key_esc', 'esc')

    @key_esc.setter
    def key_esc(self, new_value):
        self.update('key_esc', new_value)

    @property
    def key_gameplay_interaction(self) -> str:
        return self.get('key_gameplay_interaction', 'space')

    @key_gameplay_interaction.setter
    def key_gameplay_interaction(self, new_value):
        self.update('key_gameplay_interaction', new_value)

    @property
    def use_quirky_snacks(self) -> bool:
        """
        只使用奇巧零食
        :return:
        """
        return self.get('use_quirky_snacks', True)

    @use_quirky_snacks.setter
    def use_quirky_snacks(self, new_value: bool):
        """
        只使用奇巧零食
        :return:
        """
        self.update('use_quirky_snacks', new_value)

    @property
    def use_quirky_snacks_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'use_quirky_snacks', True)

    @property
    def win_title(self) -> str:
        """
        游戏窗口名称 只有区服有关
        """
        return '崩坏：星穹铁道'
