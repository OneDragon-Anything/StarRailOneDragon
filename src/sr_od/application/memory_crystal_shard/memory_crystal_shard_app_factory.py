from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.config.game_account_config import GameAccountConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application
from one_dragon.base.operation.application_run_record import AppRunRecord
from sr_od.application.memory_crystal_shard import memory_crystal_shard_const
from sr_od.application.memory_crystal_shard.memory_crystal_shard_app import MemoryCrystalShardApp
from sr_od.application.memory_crystal_shard.memory_crystal_shard_run_record import MemoryCrystalShardRunRecord

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


class MemoryCrystalShardAppFactory(ApplicationFactory):

    def __init__(self, ctx: SrContext):
        ApplicationFactory.__init__(self, memory_crystal_shard_const)
        self.ctx: SrContext = ctx

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return MemoryCrystalShardApp(self.ctx)

    def create_run_record(self, instance_idx: int) -> AppRunRecord:
        return MemoryCrystalShardRunRecord(
            instance_idx,
            GameAccountConfig(instance_idx).game_refresh_hour_offset,
        )
