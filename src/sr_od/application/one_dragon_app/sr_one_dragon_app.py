from one_dragon.base.operation.application import application_const
from one_dragon.base.operation.one_dragon_app import OneDragonApp
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.enter_game.open_and_enter_game import OpenAndEnterGame
from sr_od.operations.enter_game.switch_account import SwitchAccount


class SrOneDragonApp(OneDragonApp, SrApplication):

    def __init__(self, ctx: SrContext):
        op_to_enter_game = OpenAndEnterGame(ctx)
        op_to_switch_account = SwitchAccount(ctx)

        SrApplication.__init__(
            self,
            ctx=ctx,
            app_id=application_const.ONE_DRAGON_APP_ID,
        )
        OneDragonApp.__init__(
            self,
            ctx=ctx,
            op_to_enter_game=op_to_enter_game,
            op_to_switch_account=op_to_switch_account,
        )


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

