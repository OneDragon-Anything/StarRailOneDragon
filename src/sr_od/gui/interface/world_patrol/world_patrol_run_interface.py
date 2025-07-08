from typing import Optional

from PySide6.QtWidgets import QWidget
from qfluentwidgets import HyperlinkCard, FluentIcon

from one_dragon.base.operation.application_base import Application
from one_dragon.utils.log_utils import log
from one_dragon_qt.view.app_run_interface import AppRunInterface
from one_dragon_qt.widgets.column import Column
from one_dragon_qt.widgets.setting_card.push_setting_card import PushSettingCard
from sr_od.app.sr_application import SrApplication
from sr_od.app.world_patrol.world_patrol_app import WorldPatrolApp
from sr_od.context.sr_context import SrContext


class WorldPatrolRunInterface(AppRunInterface):

    def __init__(self,
                 ctx: SrContext,
                 parent=None):
        self.ctx: SrContext = ctx
        self.app: Optional[SrApplication] = None

        AppRunInterface.__init__(
            self,
            ctx=ctx,
            object_name='sr_world_patrol_run_interface',
            nav_text_cn='运行',
            parent=parent,
        )

    def get_widget_at_top(self) -> QWidget:
        content = Column()

        self.help_opt = HyperlinkCard(icon=FluentIcon.HELP, title='使用说明', text='前往', content='先看说明 再使用与提问',
                                      url='https://onedragon-anything.github.io/sr/zh/docs/feat_world_patrol.html')
        content.add_widget(self.help_opt)

        self.reset_opt = PushSettingCard(icon=FluentIcon.SYNC, title='重置运行记录', text='重置')
        self.reset_opt.clicked.connect(self.on_reset_clicked)
        content.add_widget(self.reset_opt)

        return content

    def get_app(self) -> Application:
        return WorldPatrolApp(self.ctx)

    def on_reset_clicked(self) -> None:
        self.ctx.world_patrol_record.reset_record()
        log.info('运行记录已重置')
