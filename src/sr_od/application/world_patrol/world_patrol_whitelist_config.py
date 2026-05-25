import os
from enum import Enum
from typing import List

from one_dragon.base.config.config_item import ConfigItem
from one_dragon.base.config.yaml_config import YamlConfig
from one_dragon_qt.widgets.setting_card.yaml_config_adapter import YamlConfigAdapter
from one_dragon.utils import os_utils


class WorldPatrolWhiteListType(Enum):

    WHITE = ConfigItem('白名单', 'white')
    BLACK = ConfigItem('黑名单', 'black')


class WorldPatrolWhitelist(YamlConfig):

    def __init__(self, file_name: str, is_mock: bool = False):
        YamlConfig.__init__(self, file_name, sample=False, is_mock=is_mock,
                            sub_dir=['world_patrol', 'whitelist'])
        self.old_module_name: str = file_name

    @property
    def valid(self) -> bool:
        return self.type in ['white', 'black'] and len(self.list) > 0

    @property
    def type(self) -> str:
        return self.get('type', WorldPatrolWhiteListType.WHITE.value.value)

    @type.setter
    def type(self, new_value: str):
        self.update('type', new_value)

    @property
    def type_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'type', WorldPatrolWhiteListType.WHITE.value.value)

    @property
    def name(self) -> str:
        return self.get('name', '未命名')

    @name.setter
    def name(self, new_value: str):
        self.update('name', new_value)

    @property
    def name_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'name', '未命名')

    @property
    def list(self) -> List[str]:
        return self.get('list', [])

    @list.setter
    def list(self, new_value: List[str]):
        self.update('list', new_value)


def load_all_whitelist_list() -> List[str]:
    """
    加载所有名单
    :return:
    """
    whitelist_id_arr: List[str] = []
    dir_path = os_utils.get_path_under_work_dir('config', 'world_patrol', 'whitelist')
    for filename in os.listdir(dir_path):
        idx = filename.find('.yml')
        if idx == -1:
            continue
        whitelist_id_arr.append(filename[0:idx])

    return whitelist_id_arr


def create_new_whitelist() -> WorldPatrolWhitelist:
    """
    创建一个新的名单 并返回对应名称
    :return:
    """
    module_name_list: List[str] = []
    dir_path = os_utils.get_path_under_work_dir('config', 'world_patrol', 'whitelist')
    for filename in os.listdir(dir_path):
        if not filename.endswith('.yml'):
            continue
        module_name_list.append(filename[:-4])

    idx: int = 1
    while True:
        module_name: str = f'名单_{idx}'
        if module_name not in module_name_list:
            break
        idx += 1

    config = WorldPatrolWhitelist(module_name)

    return config
