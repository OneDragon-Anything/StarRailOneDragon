"""末日幻影 app 运行时配置。

落点 = config/<实例>/<应用组>/apocalyptic_shadow.yml(ApplicationConfig 口径);
factory 实现 create_config 后,经 config_router 的显式路由条目被 MCP 通用
配置工具(describe/get/set)读写。
"""
from __future__ import annotations

from one_dragon.base.operation.application.application_config import ApplicationConfig
from sr_od.application.treasures_lightward.random_team import DEFAULT_CHARACTER_POOL


class ApocalypticShadowConfig(ApplicationConfig):
    """末日幻影 app 配置(随机选人占位策略 + 领奖开关)。"""

    def __init__(self, instance_idx: int, group_id: str = 'one_dragon'):
        """
        Args:
            instance_idx: 账号实例下标(config 目录编号,1 基,构造期快照)
            group_id: 应用组 id,独立运行固定默认组
        """
        ApplicationConfig.__init__(self, 'apocalyptic_shadow', instance_idx, group_id)

    @property
    def claim_rewards(self) -> bool:
        """挑战成功后是否领取期次祭礼奖励(两 tab 一键全领)。"""
        return self.get('claim_rewards', True)

    @claim_rewards.setter
    def claim_rewards(self, new_value: bool) -> None:
        self.update('claim_rewards', new_value)

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
