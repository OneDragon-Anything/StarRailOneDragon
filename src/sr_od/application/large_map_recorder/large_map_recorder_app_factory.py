from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.application.application_config import ApplicationConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from sr_od.application.large_map_recorder import large_map_recorder_const
from sr_od.application.large_map_recorder.large_map_recorder_config import LargeMapRecorderConfig
from sr_od.application.large_map_recorder.large_map_recorder_app import LargeMapRecorder

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext
    from sr_od.sr_map.sr_map_def import Region


class LargeMapRecorderAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, large_map_recorder_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        config = self.get_config(instance_idx, group_id)
        region = self._get_region_by_prl_id(config.region_prl_id)
        if region is None:
            raise ValueError(f'未找到录制区域 {config.region_prl_id}')

        return LargeMapRecorder(
            ctx=self.ctx,
            region=region,
            floor_list_to_record=LargeMapRecorderConfig.parse_int_list(config.floor_list_text),
            row_list_to_record=LargeMapRecorderConfig.parse_int_list(config.row_list_text),
            col_list_to_record=LargeMapRecorderConfig.parse_int_list(config.col_list_text),
            run_mode=config.run_mode,
        )

    def create_config(self, instance_idx: int, group_id: str) -> ApplicationConfig:
        return LargeMapRecorderConfig(instance_idx, group_id)

    def _get_region_by_prl_id(self, region_prl_id: str) -> Region | None:
        for region in self.ctx.map_data.region_list:
            if region.prl_id == region_prl_id:
                return region
        return None
