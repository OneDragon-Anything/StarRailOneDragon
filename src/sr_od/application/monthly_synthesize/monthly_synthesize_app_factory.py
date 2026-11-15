from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_config import ApplicationConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.monthly_synthesize import monthly_synthesize_const
from sr_od.application.monthly_synthesize.monthly_synthesize_app import (
    MonthlySynthesizeApp,
)
from sr_od.application.monthly_synthesize.monthly_synthesize_config import (
    MonthlySynthesizeConfig,
)
from sr_od.application.monthly_synthesize.monthly_synthesize_record import (
    MonthlySynthesizeRunRecord,
)

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class MonthlySynthesizeAppFactory(ApplicationFactory):
    """每月合成 app 工厂:构造参数注入 config 与 run_record(同一缓存
    实例,GUI/MCP 经 run_context.get_config 取到同一份,写立即生效)。"""

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, monthly_synthesize_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return MonthlySynthesizeApp(
            self.ctx,
            config=self.get_config(instance_idx, group_id),
            run_record=self.get_run_record(instance_idx),
        )

    def create_config(self, instance_idx: int, group_id: str) -> ApplicationConfig:
        return MonthlySynthesizeConfig(instance_idx, group_id)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        # 刷新偏移按账号配置注入(月界翻转边界与游戏刷新时刻对齐,同余烬兑换)
        return MonthlySynthesizeRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
