from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.trailblaze_power import trailblaze_power_const
from sr_od.application.trailblaze_power.trailblaze_power_app import TrailblazePowerApp
from sr_od.application.trailblaze_power.trailblaze_power_config import TrailblazePowerConfig
from sr_od.application.trailblaze_power.trailblaze_power_run_record import TrailblazePowerRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class TrailblazePowerAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, trailblaze_power_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return TrailblazePowerApp(self.ctx)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        config = TrailblazePowerConfig(self.ctx.guide_data, instance_idx)
        return TrailblazePowerRunRecord(
            config,
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
