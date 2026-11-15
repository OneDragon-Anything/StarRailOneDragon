
from one_dragon.base.operation.application_run_record import (
    AppRunRecord,
    AppRunRecordPeriod,
)


class MonthlySynthesizeRunRecord(AppRunRecord):
    """每月合成运行记录:周期 MONTHLY。

    MONTHLY 依据:自塑尘脂的每月合成上限按自然月刷新(画面文案「本月还可
    合成」,与兑换商店月限口径一致;跨月复位行为待跑过一个完整月界复核)
    ——「月内跳过」语义成立:每月首跑合成完毕标完成后,月内不再跑(用户
    裁定 4:进一条龙默认组)。

    失败不标完成(用户裁定 2:材料不足是失败)——一条龙日批自动重跑补做,
    残骸攒够的当次跑成。业务字段:resin_quota_confirmed = 当月「额度确实
    用尽」锚(成功合成或读到额度 0 时置位)——用于裁定「首屏未见物品」的
    成因(沉底排序律,实测):已锚 = 额度用尽(标本月完成),未锚 = 材料
    不足或额度被人手用尽(判失败重试,用户裁定 2)。自然月翻转 reset_record
    全清。
    """

    def __init__(self, instance_idx: int | None = None,
                 game_refresh_hour_offset: int = 0):
        AppRunRecord.__init__(self, 'monthly_synthesize',
                              instance_idx=instance_idx,
                              game_refresh_hour_offset=game_refresh_hour_offset,
                              record_period=AppRunRecordPeriod.MONTHLY)

    @property
    def resin_quota_confirmed(self) -> bool:
        return self.get('resin_quota_confirmed', False)

    def mark_resin_quota_confirmed(self) -> None:
        """置当月额度耗尽锚(成功合成 / 读到额度 0 时调用,当月不回退)。"""
        self.update('resin_quota_confirmed', True)

    def reset_record(self) -> None:
        """状态复位 + 业务字段清零(父类只复位状态,业务字段各 app 自清)。"""
        AppRunRecord.reset_record(self)
        self.update('resin_quota_confirmed', False)
