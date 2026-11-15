from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.apocalyptic_shadow import apocalyptic_shadow_const
from sr_od.application.apocalyptic_shadow.apocalyptic_shadow_app import (
    ApocalypticShadowApp,
)
from sr_od.application.apocalyptic_shadow.apocalyptic_shadow_config import (
    ApocalypticShadowConfig,
)
from sr_od.application.apocalyptic_shadow.apocalyptic_shadow_run_record import (
    ApocalypticShadowRunRecord,
)

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class ApocalypticShadowAppFactory(ApplicationFactory):
    """末日幻影 app 工厂:app/config/运行记录三件全实现,不挂 Context 接线
    (app 构造时显式传入记录实例,config 由 app 内部按同参数构造,两处指向
    同一 yaml 文件)。"""

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, apocalyptic_shadow_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return ApocalypticShadowApp(
            self.ctx,
            run_record=self.get_run_record(instance_idx),
            instance_idx=instance_idx,
        )

    def create_config(self, instance_idx: int, group_id: str) -> ApocalypticShadowConfig:
        return ApocalypticShadowConfig(instance_idx, group_id)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        return ApocalypticShadowRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
