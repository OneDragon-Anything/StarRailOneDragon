from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.email import email_const
from sr_od.application.email.email_app import EmailApp
from sr_od.application.email.email_run_record import EmailRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class EmailAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, email_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return EmailApp(self.ctx)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        return EmailRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
