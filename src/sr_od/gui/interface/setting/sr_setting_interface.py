from qfluentwidgets import FluentIcon

from one_dragon_qt.view.setting.setting_custom_interface import SettingCustomInterface
from one_dragon_qt.widgets.pivot_navi_interface import PivotNavigatorInterface
from one_dragon_qt.view.setting.setting_env_interface import SettingEnvInterface
from one_dragon_qt.view.setting.setting_push_interface import SettingPushInterface
from sr_od.context.sr_context import SrContext
from sr_od.gui.interface.setting.sr_setting_game_interface import SrSettingGameInterface
from sr_od.gui.interface.setting.sr_resource_download_interface import SrResourceDownloadInterface


class SrSettingInterface(PivotNavigatorInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx
        PivotNavigatorInterface.__init__(self, object_name='sr_setting_interface', parent=parent,
                                         nav_text_cn='设置', nav_icon=FluentIcon.SETTING)

    def create_sub_interface(self):
        """
        创建下面的子页面
        :return:
        """
        self.add_sub_interface(SrSettingGameInterface(ctx=self.ctx))
        self.add_sub_interface(SrResourceDownloadInterface(ctx=self.ctx))
        self.add_sub_interface(SettingEnvInterface(ctx=self.ctx))
        self.add_sub_interface(SettingPushInterface(ctx=self.ctx))
        self.add_sub_interface(SettingCustomInterface(ctx=self.ctx))
