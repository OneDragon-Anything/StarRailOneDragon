from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_config import ApplicationConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.monthly_embers_exchange import (
    monthly_embers_exchange_const,
)
from sr_od.application.monthly_embers_exchange.monthly_embers_exchange_app import (
    MonthlyEmbersExchangeApp,
)
from sr_od.application.monthly_embers_exchange.monthly_embers_exchange_config import (
    MonthlyEmbersExchangeConfig,
)
from sr_od.application.monthly_embers_exchange.monthly_embers_exchange_run_record import (
    MonthlyEmbersExchangeRunRecord,
)

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class MonthlyEmbersExchangeAppFactory(ApplicationFactory):
    """每月余烬兑换 app 工厂:构造参数注入 config 与 run_record(同一缓存
    实例,GUI/MCP 经 run_context.get_config 取到同一份,写立即生效)。"""

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, monthly_embers_exchange_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return MonthlyEmbersExchangeApp(
            self.ctx,
            config=self.get_config(instance_idx, group_id),
            run_record=self.get_run_record(instance_idx),
        )

    def create_config(self, instance_idx: int, group_id: str) -> ApplicationConfig:
        return MonthlyEmbersExchangeConfig(instance_idx, group_id)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        # 刷新偏移按账号配置注入(当日翻转边界与游戏刷新时刻对齐,同 trick_snack)
        return MonthlyEmbersExchangeRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
