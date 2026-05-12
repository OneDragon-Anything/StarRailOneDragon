from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.support_character import support_character_const
from sr_od.application.support_character.support_character_app import SupportCharacterApp
from sr_od.application.support_character.support_character_run_record import SupportCharacterRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class SupportCharacterAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, support_character_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return SupportCharacterApp(self.ctx)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        return SupportCharacterRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
