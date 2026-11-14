
from one_dragon.base.operation.application.application_config import ApplicationConfig
from sr_od.application.monthly_embers_exchange import monthly_embers_exchange_const


class MonthlyEmbersExchangeConfig(ApplicationConfig):
    """每月余烬兑换 app 配置:三件套各「开关」+ 一条兑换顺序清单。

    数量不可配全部拉满(用户裁定 2026-11-13);兑换顺序 = exchange_order
    有序清单(交互为拖拽排序,2026-11-14 方案 A,取代数字优先级);
    清单自愈:缺失项按 canonical 序(专票>通票>足迹,裁定 8)补尾、未知项
    剔除、重复项去重——读取时实时归一,yml 只在显式写入时变化。
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
                ('special_pass_enabled', True),
                ('pass_enabled', True),
                ('tracks_of_destiny_enabled', True),
                ('exchange_order', list(monthly_embers_exchange_const.MONTHLY_GOODS))):
            if field not in self.data:
                self.data[field] = default

    @staticmethod
    def _as_bool(value) -> bool:
        """MCP set 以字符串透传(value 原样落盘),读取口归一防 str 混入分支。"""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('true', '1', 'yes', 'on')

    @property
    def exchange_order(self) -> list[str]:
        """兑换顺序(英文标识符,保序):缺失项按 canonical 序补尾、未知项
        剔除、重复项去重——yml 手改/半截数据不会让 app 漏兑换任何开启项。"""
        raw = self.get('exchange_order', None)
        if not isinstance(raw, list):
            raw = []
        known = [goods for goods in monthly_embers_exchange_const.MONTHLY_GOODS
                 if goods in raw]
        missing = [goods for goods in monthly_embers_exchange_const.MONTHLY_GOODS
                   if goods not in known]
        return known + missing

    @exchange_order.setter
    def exchange_order(self, new_value: list[str]) -> None:
        self.update('exchange_order', list(new_value))

    @property
    def special_pass_enabled(self) -> bool:
        return self._as_bool(self.get('special_pass_enabled', True))

    @special_pass_enabled.setter
    def special_pass_enabled(self, new_value: bool) -> None:
        self.update('special_pass_enabled', new_value)

    @property
    def pass_enabled(self) -> bool:
        return self._as_bool(self.get('pass_enabled', True))

    @pass_enabled.setter
    def pass_enabled(self, new_value: bool) -> None:
        self.update('pass_enabled', new_value)

    @property
    def tracks_of_destiny_enabled(self) -> bool:
        return self._as_bool(self.get('tracks_of_destiny_enabled', True))

    @tracks_of_destiny_enabled.setter
    def tracks_of_destiny_enabled(self, new_value: bool) -> None:
        self.update('tracks_of_destiny_enabled', new_value)
