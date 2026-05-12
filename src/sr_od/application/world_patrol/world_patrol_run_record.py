import numpy as np
from typing import List, Optional

from one_dragon.base.operation.application_run_record import AppRunRecord


class WorldPatrolRunRecord(AppRunRecord):

    def __init__(self, instance_idx: Optional[int] = None, game_refresh_hour_offset: int = 0):
        self.finished: List[str] = []
        self.time_cost: dict[str, List] = {}
        AppRunRecord.__init__(self, 'world_patrol', instance_idx=instance_idx,
                              game_refresh_hour_offset=game_refresh_hour_offset)
        self.finished = self.get('finished', [])
        self.time_cost = self.get('time_cost', {})

    def reset_record(self):
        AppRunRecord.reset_record(self)
        self.finished = []

        self.update('finished', self.finished, False)

        self.save()

    def add_record(self, route_id: str, time_cost):
        self.finished.append(route_id)
        if route_id not in self.time_cost:
            self.time_cost[route_id] = []
        self.time_cost[route_id].append(time_cost)
        while len(self.time_cost[route_id]) > 3:
            self.time_cost[route_id].pop(0)

        self.update('run_time', self.app_record_now_time_str(), False)
        self.update('dt', self.dt, False)
        self.update('finished', self.finished, False)
        self.update('time_cost', self.time_cost, False)
        self.save()

    def get_estimate_time(self, route_id: str):
        if route_id not in self.time_cost:
            return 0
        else:
            return np.mean(self.time_cost[route_id])
