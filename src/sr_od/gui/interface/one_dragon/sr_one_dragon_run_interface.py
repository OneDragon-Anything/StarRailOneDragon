from one_dragon.base.operation.one_dragon_app import OneDragonApp
from one_dragon_qt.view.one_dragon.one_dragon_run_interface import OneDragonRunInterface
from sr_od.application.one_dragon_app.sr_one_dragon_app import SrOneDragonApp
from sr_od.context.sr_context import SrContext


class SrOneDragonRunInterface(OneDragonRunInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx
        OneDragonRunInterface.__init__(
            self,
            ctx=ctx,
            parent=parent,
            help_url='https://onedragon-anything.github.io/sr/zh/docs/feat_one_dragon.html'
        )

    def get_one_dragon_app(self) -> OneDragonApp:
        return SrOneDragonApp(self.ctx)

