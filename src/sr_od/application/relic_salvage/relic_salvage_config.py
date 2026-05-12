from enum import Enum
from typing import List, Optional

from one_dragon.base.config.config_item import ConfigItem
from one_dragon.base.config.yaml_config import YamlConfig
from one_dragon.utils.i18_utils import gt
from sr_od.application.trailblaze_power.trailblaze_power_config import TrailblazePowerPlanItem
from sr_od.interastral_peace_guide.guide_data import SrGuideData
from sr_od.interastral_peace_guide.guide_def import GuideMission


class RelicLevelEnum(Enum):

    LEVEL_4 = ConfigItem('4星及以下')
    LEVEL_5 = ConfigItem('5星及以下')


class RelicSalvageConfig(YamlConfig):

    def __init__(self, instance_idx: Optional[int] = None):
        YamlConfig.__init__(self, 'relic_salvage', instance_idx=instance_idx)

    @property
    def salvage_level(self) -> str:
        return self.get('salvage_level', RelicLevelEnum.LEVEL_4.value.value)

    @salvage_level.setter
    def salvage_level(self, new_value: str) -> None:
        self.update('salvage_level', new_value)

    @property
    def salvage_abandon(self) -> bool:
        """
        全选已弃置
        :return:
        """
        return self.get('salvage_abandon', False)

    @salvage_abandon.setter
    def salvage_abandon(self, new_value: bool) -> None:
        self.update('salvage_abandon', new_value)
