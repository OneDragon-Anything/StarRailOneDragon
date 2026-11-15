"""虚构叙事 app 运行记录:恒重置口径(同末日幻影 app——独立工具,每次
调用都是明确意图,无周期跳过需求;成功/失败状态由框架落盘留历史)。"""
from __future__ import annotations

from one_dragon.base.operation.application_run_record import AppRunRecord


class PureFictionRunRecord(AppRunRecord):

    def __init__(self, instance_idx: int | None = None,
                 game_refresh_hour_offset: int = 0):
        AppRunRecord.__init__(self, 'pure_fiction', instance_idx=instance_idx,
                              game_refresh_hour_offset=game_refresh_hour_offset)

    def check_and_update_status(self):  # 每次都运行
        self.reset_record()
