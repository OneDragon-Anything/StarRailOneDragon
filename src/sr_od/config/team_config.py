from enum import Enum

from one_dragon.base.config.config_item import ConfigItem


class TeamNumEnum(Enum):
    DEFAULT = ConfigItem('默认配队', 0)
    TEAM_1 = ConfigItem('编队1', 1)
    TEAM_2 = ConfigItem('编队2', 2)
    TEAM_3 = ConfigItem('编队3', 3)
    TEAM_4 = ConfigItem('编队4', 4)
    TEAM_5 = ConfigItem('编队5', 5)
    TEAM_6 = ConfigItem('编队6', 6)
    TEAM_7 = ConfigItem('编队7', 7)
    TEAM_8 = ConfigItem('编队8', 8)
    TEAM_9 = ConfigItem('编队9', 9)


class FileNumEnum(Enum):
    DEFAULT = ConfigItem('默认存档', 0)
    TEAM_1 = ConfigItem('存档1', 1)
    TEAM_2 = ConfigItem('存档2', 2)
    TEAM_3 = ConfigItem('存档3', 3)
    TEAM_4 = ConfigItem('存档4', 4)
