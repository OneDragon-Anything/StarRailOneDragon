
from qfluentwidgets import FluentIcon

from one_dragon_qt.widgets.pivot_navi_interface import PivotNavigatorInterface
from one_dragon_qt.widgets.setting_card.app_run_card import AppRunCard
from sr_od.context.sr_context import SrContext
from sr_od.gui.interface.one_dragon.sr_echo_of_war_setting_interface import (
    EchoOfWarSettingInterface,
)
from sr_od.gui.interface.one_dragon.sr_od_setting_interface import SrOdSettingInterface
from sr_od.gui.interface.one_dragon.sr_one_dragon_run_interface import (
    SrOneDragonRunInterface,
)
from sr_od.gui.interface.one_dragon.sr_power_plan_interface import PowerPlanInterface


class SrOneDragonInterface(PivotNavigatorInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx
        PivotNavigatorInterface.__init__(
            self,
            nav_icon=FluentIcon.BUS,
            object_name='one_dragon_interface',
            parent=parent,
            nav_text_cn='一条龙'
        )

        self._app_run_cards: list[AppRunCard] = []

    def create_sub_interface(self):
        self.add_sub_interface(SrOneDragonRunInterface(self.ctx))
        self.add_sub_interface(PowerPlanInterface(self.ctx))
        self.add_sub_interface(EchoOfWarSettingInterface(self.ctx))
        self.add_sub_interface(SrOdSettingInterface(self.ctx))
