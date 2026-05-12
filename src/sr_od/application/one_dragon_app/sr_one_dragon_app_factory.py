from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from sr_od.application.one_dragon_app import sr_one_dragon_app_const
from sr_od.application.one_dragon_app.sr_one_dragon_app import SrOneDragonApp

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class SrOneDragonAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, sr_one_dragon_app_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return SrOneDragonApp(self.ctx)
