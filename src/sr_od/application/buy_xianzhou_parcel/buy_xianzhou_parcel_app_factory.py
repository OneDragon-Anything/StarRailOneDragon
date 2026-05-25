from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.buy_xianzhou_parcel import buy_xianzhou_parcel_const
from sr_od.application.buy_xianzhou_parcel.buy_xianzhou_parcel_app import BuyXianzhouParcelApp
from sr_od.application.buy_xianzhou_parcel.buy_xianzhou_parcel_run_record import BuyXianZhouParcelRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class BuyXianzhouParcelAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, buy_xianzhou_parcel_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return BuyXianzhouParcelApp(self.ctx)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        return BuyXianZhouParcelRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
