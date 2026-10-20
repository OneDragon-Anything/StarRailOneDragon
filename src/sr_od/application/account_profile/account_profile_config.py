"""账号档案扫描配置:扫描模式等运行参数。"""
from enum import Enum

from one_dragon.base.config.yaml_config import YamlConfig


class ScanModeEnum(Enum):

    FULL = 'full'                # 全量覆盖:所有识别到的角色都重新读取档案
    INCREMENTAL = 'incremental'  # 增量更新:只读取档案里没有的角色


class AccountProfileConfig(YamlConfig):

    def __init__(self, instance_idx: int | None = None):
        YamlConfig.__init__(self, 'account_profile', instance_idx=instance_idx)

    @property
    def scan_mode(self) -> str:
        return self.get('scan_mode', ScanModeEnum.INCREMENTAL.value)

    @scan_mode.setter
    def scan_mode(self, new_value: str) -> None:
        self.update('scan_mode', new_value)
