"""末日幻影 app 运行记录:恒重置口径。

本 app 是独立工具(不在一条龙),没有「本周期已跑就跳过」的需求——每次
调用都是明确意图,同 ``trailblaze_power_run_record`` 的恒重置口径;
成功/失败状态由框架照常落盘留历史。
"""
from __future__ import annotations

from one_dragon.base.operation.application_run_record import AppRunRecord


class ApocalypticShadowRunRecord(AppRunRecord):

    def __init__(self, instance_idx: int | None = None,
                 game_refresh_hour_offset: int = 0):
        AppRunRecord.__init__(self, 'apocalyptic_shadow', instance_idx=instance_idx,
                              game_refresh_hour_offset=game_refresh_hour_offset)

    def check_and_update_status(self):  # 每次都运行
        self.reset_record()
