
from one_dragon.base.operation.application.application_config import ApplicationConfig
from sr_od.application.monthly_synthesize import monthly_synthesize_const


class MonthlySynthesizeConfig(ApplicationConfig):
    """每月合成 app 配置:各月限物品的合成开关。

    数量不可配全部拉满(用户裁定 2026-11-15);开关默认开(用户裁定 3);
    默认值补进内存 data(不落盘):MCP get_config 读原始 data 字典,缺省键
    会读到 null 误导调用方。
    """

    def __init__(self, instance_idx: int, group_id: str):
        ApplicationConfig.__init__(
            self,
            app_id=monthly_synthesize_const.APP_ID,
            instance_idx=instance_idx,
            group_id=group_id,
        )
        for field, default in (
                (f'{item}_enabled', True)
                for item in monthly_synthesize_const.MONTHLY_ITEMS):
            if field not in self.data:
                self.data[field] = default

    @staticmethod
    def _as_bool(value) -> bool:
        """MCP set 以字符串透传(value 原样落盘),读取口归一防 str 混入分支。"""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('true', '1', 'yes', 'on')

    @property
    def self_modeling_resin_enabled(self) -> bool:
        return self._as_bool(self.get('self_modeling_resin_enabled', True))

    @self_modeling_resin_enabled.setter
    def self_modeling_resin_enabled(self, new_value: bool) -> None:
        self.update('self_modeling_resin_enabled', new_value)
