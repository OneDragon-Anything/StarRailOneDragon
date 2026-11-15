from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.pure_fiction import pure_fiction_const
from sr_od.application.pure_fiction.pure_fiction_app import PureFictionApp
from sr_od.application.pure_fiction.pure_fiction_config import PureFictionConfig
from sr_od.application.pure_fiction.pure_fiction_run_record import PureFictionRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class PureFictionAppFactory(ApplicationFactory):
    """虚构叙事 app 工厂:app/config/运行记录三件全实现,不挂 Context 接线
    (同末日幻影 app 工厂形态)。"""

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, pure_fiction_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return PureFictionApp(
            self.ctx,
            run_record=self.get_run_record(instance_idx),
            instance_idx=instance_idx,
        )

    def create_config(self, instance_idx: int, group_id: str) -> PureFictionConfig:
        return PureFictionConfig(instance_idx, group_id)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        return PureFictionRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
