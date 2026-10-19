from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from sr_od.application.account_profile import account_profile_const
from sr_od.application.account_profile.account_profile_app import AccountProfileApp

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class AccountProfileAppFactory(ApplicationFactory):
    """账号档案扫描工厂:GUI 独立应用运行列表可选;DEFAULT_GROUP=False 不进一条龙默认编排。

    无运行记录(扫描随时可跑,无需按周期记状态)、无配置——两者均不实现 create_*。
    """

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, account_profile_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return AccountProfileApp(self.ctx)
