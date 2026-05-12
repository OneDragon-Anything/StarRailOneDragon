from typing import Optional

from one_dragon.base.operation.application_run_record import AppRunRecord, AppRunRecordPeriod
from one_dragon.utils import os_utils


class EchoOfWarRunRecord(AppRunRecord):

    def __init__(self, instance_idx: Optional[int] = None, game_refresh_hour_offset: int = 0):
        AppRunRecord.__init__(self, 'echo_of_war', instance_idx=instance_idx,
                              record_period=AppRunRecordPeriod.WEEKLY,
                              game_refresh_hour_offset=game_refresh_hour_offset)

    def reset_record(self):
        """
        运行记录重置 非公共部分由各app自行实现
        :return:
        """
        AppRunRecord.reset_record(self)
        self.left_times = 3

    @property
    def run_status_under_now(self):
        """
        基于当前时间显示的运行状态
        :return:
        """
        current_dt = self.get_current_dt()
        sunday_dt = os_utils.get_sunday_dt(self.dt)
        if current_dt > sunday_dt:
            return AppRunRecord.STATUS_WAIT
        elif self.left_times == 0:
            return self.run_status
        else:
            return AppRunRecord.STATUS_WAIT

    @property
    def left_times(self) -> int:
        return self.get('left_times', 3)

    @left_times.setter
    def left_times(self, new_value: int):
        self.update('left_times', new_value)
