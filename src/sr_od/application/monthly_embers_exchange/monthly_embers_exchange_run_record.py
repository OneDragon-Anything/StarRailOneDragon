
from one_dragon.base.operation.application_run_record import (
    AppRunRecord,
    AppRunRecordPeriod,
)


class MonthlyEmbersExchangeRunRecord(AppRunRecord):
    """每月余烬兑换运行记录:周期 DAILY + 业务字段(购买数量/跳过明细/余额)。

    DAILY 取舍依据:期限口径(月历/版本周)未分辨,日周期在两口径下额度
    解锁后都最迟次日补上(设计文档 design.md §2.4);「已换不重买」由
    购买 op 的售罄拦截承担,不靠记录层月内跳过。

    字段生命周期:bought_* 当日周期累计(同日重跑累加,失败重跑不丢已购);
    skip_note 单次运行诊断(运行开始清零,防跨次叠加过期观察);
    balance_left 最近一次观测。日界翻转 reset_record 全清。
    """

    def __init__(self, instance_idx: int | None = None,
                 game_refresh_hour_offset: int = 0):
        AppRunRecord.__init__(self, 'monthly_embers_exchange',
                              instance_idx=instance_idx,
                              game_refresh_hour_offset=game_refresh_hour_offset,
                              record_period=AppRunRecordPeriod.DAILY)

    @property
    def bought_pass(self) -> int:
        return self.get('bought_pass', 0)

    @property
    def bought_special_pass(self) -> int:
        return self.get('bought_special_pass', 0)

    @property
    def bought_tracks_of_destiny(self) -> int:
        return self.get('bought_tracks_of_destiny', 0)

    @property
    def skip_note(self) -> str:
        return self.get('skip_note', '')

    @property
    def balance_left(self) -> int | None:
        return self.get('balance_left', None)

    def record_purchase(self, goods: str, bought: int) -> None:
        """记录单项购买数量(字段名 = bought_{goods},goods 为英文标识符)。"""
        self.update(f'bought_{goods}', self.get(f'bought_{goods}', 0) + bought)

    def record_skip(self, note_entry: str, append: bool = True) -> None:
        """追加跳过明细一项(``goods:STATUS`` 格式;首项不带分隔分号)。"""
        existing = self.skip_note
        if not existing or not append:
            self.update('skip_note', note_entry)
        else:
            self.update('skip_note', f'{existing};{note_entry}')

    def clear_skip_note(self) -> None:
        """清空跳过明细(每次运行开始调用)。

        字段生命周期:bought_* = 当日周期累计(失败重跑不丢已购数量),
        skip_note = 单次运行的诊断(跨次叠加会混入上次的过期观察),
        balance_left = 最近一次观测。日界翻转由 reset_record 全清。
        """
        self.update('skip_note', '')

    def record_balance_left(self, balance_left: int | None) -> None:
        """记录最后一项兑换后余额(尽力留痕,读不出 = None)。"""
        self.update('balance_left', balance_left)

    def reset_record(self) -> None:
        """状态复位 + 业务字段清零(父类只复位状态,业务字段各 app 自清)。"""
        AppRunRecord.reset_record(self)
        self.update('bought_pass', 0)
        self.update('bought_special_pass', 0)
        self.update('bought_tracks_of_destiny', 0)
        self.update('skip_note', '')
        self.update('balance_left', None)
