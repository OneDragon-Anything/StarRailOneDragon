from typing import Optional

from one_dragon.base.operation.application_run_record import AppRunRecord
from one_dragon.utils import os_utils
from sr_od.application.sim_universe.sim_uni_config import SimUniConfig


class SimUniRunRecord(AppRunRecord):

    def __init__(self, config: SimUniConfig, instance_idx: Optional[int] = None, game_refresh_hour_offset: int = 0):
        AppRunRecord.__init__(self, 'sim_universe', instance_idx=instance_idx,
                              game_refresh_hour_offset=game_refresh_hour_offset)
        self.config = config

    @property
    def run_status_under_now(self):
        """
        基于当前时间显示的运行状态
        :return:
        """
        if self._should_reset_by_dt():
            if os_utils.is_monday(self.get_current_dt()):
                return AppRunRecord.STATUS_WAIT
            elif self.elite_weekly_times >= self.config.elite_weekly_times:  # 已完成本周次数
                return AppRunRecord.STATUS_SUCCESS
            else:
                return AppRunRecord.STATUS_WAIT
        else:
            if self.elite_weekly_times >= self.config.elite_weekly_times or \
                    self.elite_daily_times >= self.config.elite_daily_times:  # 已完成次数
                return AppRunRecord.STATUS_SUCCESS
            else:
                return AppRunRecord.STATUS_WAIT

    def reset_record(self):
        """
        运行记录重置 非公共部分由各app自行实现
        :return:
        """
        AppRunRecord.reset_record(self)
        current_dt = self.get_current_dt()
        if os_utils.get_monday_dt(current_dt) != os_utils.get_monday_dt(self.dt):
            self.weekly_times = 0
            self.elite_weekly_times = 0
        self.daily_times = 0
        self.elite_daily_times = 0

    def add_times(self):
        """
        增加一次完成次数
        :return:
        """
        self.daily_times = self.daily_times + 1
        self.weekly_times = self.weekly_times + 1

    @property
    def weekly_times(self) -> int:
        """
        每周挑战的次数
        :return:
        """
        return self.get('weekly_times', 0)

    @weekly_times.setter
    def weekly_times(self, new_value: int):
        self.update('weekly_times', new_value)

    @property
    def daily_times(self) -> int:
        """
        每天挑战的次数
        :return:
        """
        return self.get('daily_times', 0)

    @daily_times.setter
    def daily_times(self, new_value: int):
        self.update('daily_times', new_value)

    @property
    def elite_weekly_times(self) -> int:
        """
        每周挑战精英的次数
        :return:
        """
        return self.get('elite_weekly_times', 0)

    @elite_weekly_times.setter
    def elite_weekly_times(self, new_value: int):
        self.update('elite_weekly_times', new_value)

    @property
    def elite_daily_times(self) -> int:
        """
        每天挑战的次数
        :return:
        """
        return self.get('elite_daily_times', 0)

    @elite_daily_times.setter
    def elite_daily_times(self, new_value: int):
        self.update('elite_daily_times', new_value)

    def add_elite_times(self, times: int = 1):
        """
        增加挑战精英的次数
        :param times: 本次完成次数
        :return:
        """
        self.elite_daily_times = self.elite_daily_times + times
        self.elite_weekly_times = self.elite_weekly_times + times
