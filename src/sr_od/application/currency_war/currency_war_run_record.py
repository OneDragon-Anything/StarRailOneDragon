# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)


from one_dragon.base.operation.application_run_record import AppRunRecord


class CurrencyWarRunRecord(AppRunRecord):
    """货币战争运行记录。v1 仅用公共字段(运行状态/时间);周期积分等后续按需加。"""

    def __init__(self, instance_idx: int | None = None, game_refresh_hour_offset: int = 0):
        AppRunRecord.__init__(
            self, 'currency_war',
            instance_idx=instance_idx,
            game_refresh_hour_offset=game_refresh_hour_offset,
        )
