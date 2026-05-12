from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from sr_od.application.calibrator import calibrator_const
from sr_od.application.calibrator.calibrator import Calibrator

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class CalibratorAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, calibrator_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return Calibrator(self.ctx)
