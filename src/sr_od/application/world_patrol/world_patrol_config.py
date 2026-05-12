from typing import Optional

from one_dragon.base.config.yaml_config import YamlConfig
from one_dragon_qt.widgets.setting_card.yaml_config_adapter import YamlConfigAdapter


class WorldPatrolConfig(YamlConfig):

    def __init__(self, instance_idx: Optional[int] = None):
        YamlConfig.__init__(self, 'world_patrol', instance_idx=instance_idx)

    @property
    def team_num(self) -> int:
        return self.get('team_num', 0)

    @team_num.setter
    def team_num(self, new_value: int):
        self.update('team_num', new_value)

    @property
    def team_num_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'team_num', 0, 'str', 'int')

    @property
    def character_1(self) -> str:
        return self.get('character_1', 'none')

    @character_1.setter
    def character_1(self, new_value: str):
        self.update('character_1', new_value)

    @property
    def character_1_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'character_1', 'none')

    @property
    def whitelist_id(self) -> str:
        return self.get('whitelist_id', '')

    @whitelist_id.setter
    def whitelist_id(self, new_value: str):
        self.update('whitelist_id', new_value)

    @property
    def whitelist_id_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'whitelist_id', '')

    @property
    def technique_fight(self) -> bool:
        return self.get('technique_fight', False)

    @technique_fight.setter
    def technique_fight(self, new_value: bool):
        self.update('technique_fight', new_value)

    @property
    def technique_fight_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'technique_fight', False)

    @property
    def technique_only(self) -> bool:
        """
        只使用秘技
        :return:
        """
        return self.get('technique_only', False)

    @technique_only.setter
    def technique_only(self, new_value: bool):
        self.update('technique_only', new_value)

    @property
    def technique_only_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'technique_only', False)

    @property
    def max_consumable_cnt(self) -> int:
        return self.get('max_consumable_cnt', 0)

    @max_consumable_cnt.setter
    def max_consumable_cnt(self, new_value: int):
        self.update('max_consumable_cnt', new_value)

    @property
    def max_consumable_cnt_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'max_consumable_cnt', 0, 'str', 'int')