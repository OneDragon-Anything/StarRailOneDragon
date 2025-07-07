from typing import List

from one_dragon.base.operation.one_dragon_app import OneDragonApp
from sr_od.app.assignments.assignments_app import AssignmentsApp
from sr_od.app.buy_xianzhou_parcel.buy_xianzhou_parcel_app import BuyXianzhouParcelApp
from sr_od.app.memory_crystal_shard.memory_crystal_shard_app import MemoryCrystalShardApp
from sr_od.app.claim_email.email_app import EmailApp
from sr_od.app.daily_training.daily_training_app import DailyTrainingApp
from sr_od.app.echo_of_war.echo_of_war_app import EchoOfWarApp
from sr_od.app.nameless_honor.nameless_honor_app import NamelessHonorApp
from sr_od.app.relic_salvage.relic_salvage_app import RelicSalvageApp
from sr_od.app.sim_uni.sim_uni_app import SimUniApp
from sr_od.app.sr_application import SrApplication
from sr_od.app.support_character.support_character_app import SupportCharacterApp
from sr_od.app.trailblaze_power.trailblaze_power_app import TrailblazePowerApp
from sr_od.app.trick_snack.trick_snack_app import TrickSnackApp
from sr_od.app.world_patrol.world_patrol_app import WorldPatrolApp
from sr_od.context.sr_context import SrContext
from sr_od.operations.enter_game.open_and_enter_game import OpenAndEnterGame
from sr_od.operations.enter_game.switch_account import SwitchAccount


class SrOneDragonApp(OneDragonApp, SrApplication):

    def __init__(self, ctx: SrContext):
        app_id = 'sr_one_dragon'
        op_to_enter_game = OpenAndEnterGame(ctx)
        op_to_switch_account = SwitchAccount(ctx)

        SrApplication.__init__(self, ctx, app_id)
        OneDragonApp.__init__(self, ctx, app_id,
                              op_to_enter_game=op_to_enter_game,
                              op_to_switch_account=op_to_switch_account)

    def get_app_list(self) -> List[SrApplication]:
        from sr_od.app.notify.notify_app import NotifyApp
        return [
            AssignmentsApp(self.ctx),
            EchoOfWarApp(self.ctx),
            TrailblazePowerApp(self.ctx),
            WorldPatrolApp(self.ctx),
            SimUniApp(self.ctx),
            RelicSalvageApp(self.ctx),
            EmailApp(self.ctx),
            BuyXianzhouParcelApp(self.ctx),
            MemoryCrystalShardApp(self.ctx),
            TrickSnackApp(self.ctx),
            SupportCharacterApp(self.ctx),
            DailyTrainingApp(self.ctx),
            NamelessHonorApp(self.ctx),
            NotifyApp(self.ctx)
        ]


def __debug():
    ctx = SrContext()
    # 加载配置
    ctx.init_by_config()

    # 异步加载OCR
    ctx.async_init_ocr()

    if ctx.env_config.auto_update:
        from one_dragon.utils.log_utils import log
        log.info('开始自动更新...')
        ctx.git_service.fetch_latest_code()

    app = SrOneDragonApp(ctx)
    app.execute()

    from one_dragon.base.config.one_dragon_config import AfterDoneOpEnum
    if ctx.one_dragon_config.after_done == AfterDoneOpEnum.SHUTDOWN.value.value:
        from one_dragon.utils import cmd_utils
        cmd_utils.shutdown_sys(60)
    elif ctx.one_dragon_config.after_done == AfterDoneOpEnum.CLOSE_GAME.value.value:
        ctx.controller.close_game()


if __name__ == '__main__':
    __debug()
