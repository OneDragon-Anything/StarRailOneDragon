import os
import shutil
from typing import List

from one_dragon.base.config.yaml_config import YamlConfig
from one_dragon_qt.widgets.setting_card.yaml_config_adapter import YamlConfigAdapter
from one_dragon.utils import os_utils

_MAX_WITH_SAMPLE = 9


class SimUniChallengeConfig(YamlConfig):

    def __init__(self, idx: int, is_mock: bool = False):
        """
        模拟宇宙挑战配置 全局的 无需跟账号挂钩
        """
        YamlConfig.__init__(self, '%02d' % idx,
                            sub_dir=['sim_uni', 'challenge_config'],
                            sample=idx <= _MAX_WITH_SAMPLE,
                            copy_from_sample=idx <= _MAX_WITH_SAMPLE,
                            is_mock=is_mock)

        self.idx = idx

    def _init_after_read_file(self):
        pass

    @property
    def uid(self) -> str:
        return '%02d' % self.idx

    @property
    def name(self) -> str:
        return self.get('name', '')

    @name.setter
    def name(self, new_value: str):
        self.update('name', new_value)

    @property
    def name_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self,  'name', '')

    @property
    def path(self) -> str:
        """
        返回命途ID SimUniPath.name
        :return:
        """
        return self.get('path', '')

    @path.setter
    def path(self, new_value: str):
        self.update('path', new_value)

    @property
    def path_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'path', '')

    @property
    def bless_priority(self) -> List[str]:
        """
        祝福优先级 - 第一优先级
        :return:
        """
        return self.get('bless_priority', [])

    @bless_priority.setter
    def bless_priority(self, new_list: List[str]):
        self.update('bless_priority', new_list)

    @property
    def bless_priority_2(self) -> List[str]:
        """
        祝福优先级 - 第二优先级
        :return:
        """
        return self.get('bless_priority_2', [])

    @bless_priority_2.setter
    def bless_priority_2(self, new_list: List[str]):
        self.update('bless_priority_2', new_list)

    @property
    def level_type_priority(self) -> List[str]:
        """
        楼层优先级
        :return:
        """
        return self.get('level_type_priority', [])

    @level_type_priority.setter
    def level_type_priority(self, new_list: List[str]):
        self.update('level_type_priority', new_list)

    @property
    def curio_priority(self) -> List[str]:
        """
        楼层优先级
        :return:
        """
        return self.get('curio_priority', [])

    @curio_priority.setter
    def curio_priority(self, new_list: List[str]):
        self.update('curio_priority', new_list)

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
        仅秘技开怪
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
    def max_consumable_cnt(self) -> bool:
        return self.get('max_consumable_cnt', 0)

    @max_consumable_cnt.setter
    def max_consumable_cnt(self, new_value: int):
        self.update('max_consumable_cnt', new_value)

    @property
    def max_consumable_cnt_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'max_consumable_cnt', 0)

    @property
    def skip_herta(self) -> bool:
        return self.get('skip_herta', False)

    @skip_herta.setter
    def skip_herta(self, new_value: bool) -> None:
        self.update('skip_herta', new_value)

    @property
    def skip_herta_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'skip_herta', False)


class SimUniChallengeConfigData:

    def __init__(self):
        pass

    def load_all_challenge_config(self) -> List[SimUniChallengeConfig]:
        config_list = []
        for i in range(1, _MAX_WITH_SAMPLE + 1):  # 有模板的部分
            config_list.append(SimUniChallengeConfig(i))

        base_dir = self.get_challenge_config_dir()
        for file in os.listdir(base_dir):
            if not file.endswith('.yml'):
                continue

            if file.endswith('_sample.yml'):
                continue

            idx = int(file[:2])
            if idx <= _MAX_WITH_SAMPLE:
                continue

            config_list.append(SimUniChallengeConfig(idx))

        return config_list

    def get_challenge_config_dir(self) -> str:
        return os_utils.get_path_under_work_dir('config',
                                                'sim_uni', 'challenge_config')

    def get_next_id(self) -> int:
        """
        为新建获取下一个id
        :return:
        """
        base_dir = self.get_challenge_config_dir()
        idx = _MAX_WITH_SAMPLE + 1  # 获取合法的下标
        while True:
            route_dir = os.path.join(base_dir, '%02d' % idx)
            if os.path.exists(route_dir):
                idx += 1
            else:
                break
        return idx

    def create_new_challenge_config(self, sample_idx: int = 0) -> SimUniChallengeConfig:
        """
        创建一个新的配置
        :return:
        """
        idx = self.get_next_id()
        base_dir = self.get_challenge_config_dir()

        from_file = os.path.join(base_dir, '01_sample.yml' if sample_idx == 0 else ('%02d.yml' % sample_idx))
        to_file = os.path.join(base_dir, '%02d.yml' % idx)

        shutil.copy2(from_file, to_file)

        config = SimUniChallengeConfig(idx)
        config._sample = False
        config.file_path = config._get_yaml_file_path()

        return config
