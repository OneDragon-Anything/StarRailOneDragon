from one_dragon.base.operation.application.application_config import ApplicationConfig
from sr_od.application.monthly_embers_exchange import monthly_embers_exchange_const


class MonthlyEmbersExchangeConfig(ApplicationConfig):
    """每月余烬兑换 app 配置:三件套各「开关 + 优先级」。

    数量不可配全部拉满(用户裁定 2026-11-13);兑换顺序 = priority 升序,
    同值按固定序兜底 专票 > 通票 > 足迹(默认值 10/20/30 即默认顺序)。
    """

    def __init__(self, instance_idx: int, group_id: str):
        ApplicationConfig.__init__(
            self,
            app_id=monthly_embers_exchange_const.APP_ID,
            instance_idx=instance_idx,
            group_id=group_id,
        )
        # 默认值补进内存 data(不落盘):MCP get_config 读原始 data 字典,
        # 缺省键会读到 null 误导调用方(describe 的默认值语义同样靠它)
        for field, default in (
                ('special_pass_enabled', True), ('special_pass_priority', 10),
                ('pass_enabled', True), ('pass_priority', 20),
                ('tracks_of_destiny_enabled', True),
                ('tracks_of_destiny_priority', 30)):
            if field not in self.data:
                self.data[field] = default

    @property
    def special_pass_enabled(self) -> bool:
        return self.get('special_pass_enabled', True)

    @special_pass_enabled.setter
    def special_pass_enabled(self, new_value: bool) -> None:
        self.update('special_pass_enabled', new_value)

    @property
    def special_pass_priority(self) -> int:
        return self.get('special_pass_priority', 10)

    @special_pass_priority.setter
    def special_pass_priority(self, new_value: int) -> None:
        self.update('special_pass_priority', new_value)

    @property
    def pass_enabled(self) -> bool:
        return self.get('pass_enabled', True)

    @pass_enabled.setter
    def pass_enabled(self, new_value: bool) -> None:
        self.update('pass_enabled', new_value)

    @property
    def pass_priority(self) -> int:
        return self.get('pass_priority', 20)

    @pass_priority.setter
    def pass_priority(self, new_value: int) -> None:
        self.update('pass_priority', new_value)

    @property
    def tracks_of_destiny_enabled(self) -> bool:
        return self.get('tracks_of_destiny_enabled', True)

    @tracks_of_destiny_enabled.setter
    def tracks_of_destiny_enabled(self, new_value: bool) -> None:
        self.update('tracks_of_destiny_enabled', new_value)

    @property
    def tracks_of_destiny_priority(self) -> int:
        return self.get('tracks_of_destiny_priority', 30)

    @tracks_of_destiny_priority.setter
    def tracks_of_destiny_priority(self, new_value: int) -> None:
        self.update('tracks_of_destiny_priority', new_value)
