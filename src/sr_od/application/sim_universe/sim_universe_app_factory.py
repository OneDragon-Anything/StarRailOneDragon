from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.sim_universe import sim_universe_const
from sr_od.application.sim_universe.sim_uni_app import SimUniApp
from sr_od.application.sim_universe.sim_uni_config import SimUniConfig
from sr_od.application.sim_universe.sim_uni_run_record import SimUniRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class SimUniverseAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, sim_universe_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return SimUniApp(self.ctx)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        config = SimUniConfig(instance_idx)
        return SimUniRunRecord(
            config,
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
