from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.trick_snack import trick_snack_const
from sr_od.application.trick_snack.trick_snack_app import TrickSnackApp
from sr_od.application.trick_snack.trick_snack_record import TrickSnackRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class TrickSnackAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, trick_snack_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return TrickSnackApp(self.ctx)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        return TrickSnackRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
