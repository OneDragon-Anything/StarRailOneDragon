from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.daily_training import daily_training_const
from sr_od.application.daily_training.daily_training_app import DailyTrainingApp
from sr_od.application.daily_training.daily_training_run_record import DailyTrainingRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class DailyTrainingAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, daily_training_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return DailyTrainingApp(self.ctx)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        return DailyTrainingRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
