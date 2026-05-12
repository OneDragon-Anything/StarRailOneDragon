from __future__ import annotations

from one_dragon.base.operation.application.application_config import ApplicationConfig
from sr_od.application.large_map_recorder import large_map_recorder_const


class LargeMapRecorderConfig(ApplicationConfig):

    def __init__(self, instance_idx: int, group_id: str):
        ApplicationConfig.__init__(
            self,
            app_id=large_map_recorder_const.APP_ID,
            instance_idx=instance_idx,
            group_id=group_id,
        )

    @property
    def region_prl_id(self) -> str:
        return self.get('region_prl_id', '')

    @region_prl_id.setter
    def region_prl_id(self, new_value: str) -> None:
        self.update('region_prl_id', new_value)

    @property
    def run_mode(self) -> str:
        return self.get('run_mode', 'all')

    @run_mode.setter
    def run_mode(self, new_value: str) -> None:
        self.update('run_mode', new_value)

    @property
    def floor_list_text(self) -> str:
        return self.get('floor_list_text', '')

    @floor_list_text.setter
    def floor_list_text(self, new_value: str) -> None:
        self.update('floor_list_text', new_value)

    @property
    def row_list_text(self) -> str:
        return self.get('row_list_text', '')

    @row_list_text.setter
    def row_list_text(self, new_value: str) -> None:
        self.update('row_list_text', new_value)

    @property
    def col_list_text(self) -> str:
        return self.get('col_list_text', '')

    @col_list_text.setter
    def col_list_text(self, new_value: str) -> None:
        self.update('col_list_text', new_value)

    @staticmethod
    def parse_int_list(value: str) -> list[int] | None:
        if not value or not value.strip():
            return None

        return [int(item.strip()) for item in value.split(',') if item.strip()]