from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.currency_war import currency_war_const
from sr_od.application.currency_war.currency_war_app import CurrencyWarApp
from sr_od.application.currency_war.currency_war_run_record import CurrencyWarRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class CurrencyWarAppFactory(ApplicationFactory):
    """货币战争应用工厂。经 ApplicationFactoryManager 自动发现(本目录 currency_war_app_factory.py + currency_war_const.py)。"""

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, currency_war_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return CurrencyWarApp(self.ctx)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        return CurrencyWarRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
