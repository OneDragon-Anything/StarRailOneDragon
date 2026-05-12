from typing import Optional

from one_dragon.base.config.yaml_config import YamlConfig
from one_dragon_qt.widgets.setting_card.yaml_config_adapter import YamlConfigAdapter
from sr_od.application.sim_universe.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.application.sim_universe.sim_uni_data import SimUniWorldEnum


class SimUniConfig(YamlConfig):

    def __init__(self, instance_idx: Optional[int] = None):
        YamlConfig.__init__(self, 'sim_universe', instance_idx=instance_idx)

    def get_challenge_config(self, sim_uni_num: int) -> SimUniChallengeConfig:
        """
        获取模拟宇宙对应的挑战配置
        :param sim_uni_num: 第几宇宙
        :return:
        """
        key = 'sim_uni_%02d' % sim_uni_num
        return SimUniChallengeConfig(int(self.get(key, '05')))

    @property
    def sim_uni_03(self) -> str:
        return self.get('sim_uni_03', '05')

    @property
    def sim_uni_04(self) -> str:
        return self.get('sim_uni_04', '05')

    @property
    def sim_uni_05(self) -> str:
        return self.get('sim_uni_05', '05')

    @property
    def sim_uni_06(self) -> str:
        return self.get('sim_uni_06', '05')

    @property
    def sim_uni_07(self) -> str:
        return self.get('sim_uni_07', '05')

    @property
    def sim_uni_08(self) -> str:
        return self.get('sim_uni_08', '05')

    @property
    def sim_uni_09(self) -> str:
        return self.get('sim_uni_09', '05')

    @property
    def weekly_uni_num(self) -> str:
        """
        每周挑战的第几宇宙设置
        :return:
        """
        return self.get('weekly_uni_num', SimUniWorldEnum.WORLD_08.name)

    @weekly_uni_num.setter
    def weekly_uni_num(self, new_value: str):
        self.update('weekly_uni_num', new_value)

    @property
    def weekly_uni_num_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'weekly_uni_num', SimUniWorldEnum.WORLD_08.name)

    @property
    def weekly_uni_diff(self) -> int:
        """
        每周挑战的宇宙难度设置
        :return:
        """
        return self.get('weekly_uni_diff', 0)

    @weekly_uni_diff.setter
    def weekly_uni_diff(self, new_value: int):
        self.update('weekly_uni_diff', new_value)

    @property
    def weekly_uni_diff_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'weekly_uni_diff', 0)

    @property
    def elite_weekly_times(self) -> int:
        """
        每周挑战精英的次数
        :return:
        """
        return self.get('elite_weekly_times', 100)

    @elite_weekly_times.setter
    def elite_weekly_times(self, new_value: int):
        self.update('elite_weekly_times', new_value)

    @property
    def elite_weekly_times_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'elite_weekly_times', 100, 'str', 'int')

    @property
    def elite_daily_times(self) -> int:
        """
        每天挑战的次数
        :return:
        """
        return self.get('elite_daily_times', 15)

    @elite_daily_times.setter
    def elite_daily_times(self, new_value: int):
        self.update('elite_daily_times', new_value)

    @property
    def elite_daily_times_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'elite_daily_times', 15, 'str', 'int')

    def get_challenge_config_adapter(self, sim_uni_num: int) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'sim_uni_%02d' % sim_uni_num, '05')

