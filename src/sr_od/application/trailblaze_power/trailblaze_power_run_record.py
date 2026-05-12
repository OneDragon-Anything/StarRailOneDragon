import time
from typing import Optional

from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.trailblaze_power.trailblaze_power_config import TrailblazePowerConfig


class TrailblazePowerRunRecord(AppRunRecord):

    def __init__(self, tp_config: TrailblazePowerConfig,
                 instance_idx: Optional[int] = None, game_refresh_hour_offset: int = 0):
        self.tp_config: TrailblazePowerConfig = tp_config
        AppRunRecord.__init__(self, 'trailblaze_power', instance_idx=instance_idx,
                              game_refresh_hour_offset=game_refresh_hour_offset)

    def check_and_update_status(self):  # 每次都运行
        self.reset_record()

