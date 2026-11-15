"""虚构叙事 app 运行时配置。

落点 = config/<实例>/<应用组>/pure_fiction.yml(ApplicationConfig 口径)。
虚构叙事的期次奖励领取 op 未建模,故无领奖开关;config_router 不设路由条目
(唯一字段 character_pool 为列表,set_config 本就写不了,describe 无可展示
的可写字段),改池直接编辑本 yaml。
"""
from __future__ import annotations

from one_dragon.base.operation.application.application_config import ApplicationConfig
from sr_od.application.treasures_lightward.random_team import DEFAULT_CHARACTER_POOL


class PureFictionConfig(ApplicationConfig):
    """虚构叙事 app 配置(随机选人占位策略)。"""

    def __init__(self, instance_idx: int, group_id: str = 'one_dragon'):
        """
        Args:
            instance_idx: 账号实例下标(config 目录编号,1 基,构造期快照)
            group_id: 应用组 id,独立运行固定默认组
        """
        ApplicationConfig.__init__(self, 'pure_fiction', instance_idx, group_id)

    @property
    def character_pool(self) -> list[str]:
        """随机选人候选池(角色中文名,与编队屏列表卡识别名同口径);
        配置为空列表时回落默认快照池。"""
        pool: list[str] = self.get('character_pool', DEFAULT_CHARACTER_POOL)
        if not pool:
            return list(DEFAULT_CHARACTER_POOL)
        return list(pool)

    @character_pool.setter
    def character_pool(self, new_value: list[str]) -> None:
        self.update('character_pool', new_value)
