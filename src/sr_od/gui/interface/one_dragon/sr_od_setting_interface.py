from PySide6.QtWidgets import QWidget
from qfluentwidgets import SettingCardGroup, FluentIcon

from one_dragon.base.operation.application import application_const
from one_dragon_qt.widgets.setting_card.combo_box_setting_card import ComboBoxSettingCard
from one_dragon_qt.widgets.setting_card.switch_setting_card import SwitchSettingCard
from one_dragon_qt.widgets.vertical_scroll_interface import VerticalScrollInterface
from one_dragon.utils.i18_utils import gt
from one_dragon_qt.widgets.column import Column
from sr_od.application.relic_salvage import relic_salvage_const
from sr_od.application.relic_salvage.relic_salvage_config import RelicLevelEnum, RelicSalvageConfig
from sr_od.application.trick_snack import trick_snack_const
from sr_od.application.trick_snack.trick_snack_config import TrickSnackConfig
from sr_od.context.sr_context import SrContext


class SrOdSettingInterface(VerticalScrollInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx
        self.relic_salvage_config: RelicSalvageConfig
        self.trick_snack_config: TrickSnackConfig

        VerticalScrollInterface.__init__(
            self,
            object_name='sr_od_setting_interface',
            content_widget=None, parent=parent,
            nav_text_cn='其他设置'
        )

    def get_content_widget(self) -> QWidget:
        content_widget = Column()

        content_widget.add_widget(self.get_relic_salvage_group())
        content_widget.add_widget(self.get_trick_snack_group())
        content_widget.add_stretch(1)

        return content_widget

    def get_relic_salvage_group(self) -> QWidget:
        group = SettingCardGroup(gt('遗器分解'))

        self.relic_salvage_level_opt = ComboBoxSettingCard(icon=FluentIcon.GAME, title='遗器分解等级',
                                                           options_enum=RelicLevelEnum)
        group.addSettingCard(self.relic_salvage_level_opt)

        self.relic_salvage_abandon_opt = SwitchSettingCard(icon=FluentIcon.GAME, title='全部已弃置')
        group.addSettingCard(self.relic_salvage_abandon_opt)

        return group

    def get_trick_snack_group(self) -> QWidget:
        group = SettingCardGroup(gt('奇巧零食', 'game'))

        self.route_yll6_xzq_opt = SwitchSettingCard(icon=FluentIcon.GAME, title='雅利洛-VI 行政区 罗纳德')
        group.addSettingCard(self.route_yll6_xzq_opt)

        self.route_xzlf_xchzs_opt = SwitchSettingCard(icon=FluentIcon.GAME, title='仙舟「罗浮」 星槎海中枢 货全')
        group.addSettingCard(self.route_xzlf_xchzs_opt)

        self.synthesize_trick_snack = SwitchSettingCard(icon=FluentIcon.GAME, title='自动合成零食（消耗全部材料）')
        group.addSettingCard(self.synthesize_trick_snack)

        return group

    def on_interface_shown(self) -> None:
        VerticalScrollInterface.on_interface_shown(self)

        self.relic_salvage_config = self.ctx.run_context.get_config(
            app_id=relic_salvage_const.APP_ID,
            instance_idx=self.ctx.current_instance_idx,
            group_id=application_const.DEFAULT_GROUP_ID,
        )
        self.trick_snack_config = self.ctx.run_context.get_config(
            app_id=trick_snack_const.APP_ID,
            instance_idx=self.ctx.current_instance_idx,
            group_id=application_const.DEFAULT_GROUP_ID,
        )

        self.relic_salvage_level_opt.init_with_adapter(self.relic_salvage_config.get_prop_adapter('salvage_level'))
        self.relic_salvage_abandon_opt.init_with_adapter(self.relic_salvage_config.get_prop_adapter('salvage_abandon'))

        self.route_yll6_xzq_opt.init_with_adapter(self.trick_snack_config.get_prop_adapter('route_yll6_xzq'))
        self.route_xzlf_xchzs_opt.init_with_adapter(self.trick_snack_config.get_prop_adapter('route_xzlf_xchzs'))
        self.synthesize_trick_snack.init_with_adapter(self.trick_snack_config.get_prop_adapter('synthesize_trick_snack'))

