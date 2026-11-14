from PySide6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon, SettingCardGroup

from one_dragon.base.operation.application import application_const
from one_dragon.utils.i18_utils import gt
from one_dragon_qt.widgets.column import Column
from one_dragon_qt.widgets.setting_card.combo_box_setting_card import (
    ComboBoxSettingCard,
)
from one_dragon_qt.widgets.setting_card.spin_box_setting_card import SpinBoxSettingCard
from one_dragon_qt.widgets.setting_card.switch_setting_card import SwitchSettingCard
from one_dragon_qt.widgets.setting_card.yaml_config_adapter import YamlConfigAdapter
from one_dragon_qt.widgets.vertical_scroll_interface import VerticalScrollInterface
from sr_od.application.monthly_embers_exchange import monthly_embers_exchange_const
from sr_od.application.relic_salvage.relic_salvage_config import RelicLevelEnum
from sr_od.context.sr_context import SrContext


class SrOdSettingInterface(VerticalScrollInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx

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
        content_widget.add_widget(self.get_monthly_embers_exchange_group())
        content_widget.add_stretch(1)

        return content_widget

    def get_monthly_embers_exchange_config(self):
        """每月余烬兑换配置:经 run_context 取 factory 缓存实例(与 app 运行/MCP
        写入同一份,改完下一次 run 即生效;ApplicationConfig 走 YamlOperator
        无 get_prop_adapter,adapter 直连 property 构造)。"""
        return self.ctx.run_context.get_config(
            app_id=monthly_embers_exchange_const.APP_ID,
            instance_idx=self.ctx.current_instance_idx,
            group_id=application_const.DEFAULT_GROUP_ID,
        )

    def get_monthly_embers_exchange_group(self) -> QWidget:
        config = self.get_monthly_embers_exchange_config()
        group = SettingCardGroup(gt('每月余烬兑换', 'game'))

        self.mee_special_pass_enabled_opt = SwitchSettingCard(
            icon=FluentIcon.SHOP, title='兑换 星轨专票',
            content='90 余烬/张,月限 5 张(跃迁抽卡票)')
        self.mee_special_pass_enabled_opt.init_with_adapter(
            YamlConfigAdapter(config, 'special_pass_enabled', True))
        group.addSettingCard(self.mee_special_pass_enabled_opt)

        self.mee_special_pass_priority_opt = SpinBoxSettingCard(
            icon=FluentIcon.SHOP, title='星轨专票 优先级',
            content='升序兑换;同优先级按 专票>通票>足迹 兜底', minimum=0,
            maximum=99)
        self.mee_special_pass_priority_opt.init_with_adapter(
            YamlConfigAdapter(config, 'special_pass_priority', 10,
                              getter_convert='int', setter_convert='int'))
        group.addSettingCard(self.mee_special_pass_priority_opt)

        self.mee_pass_enabled_opt = SwitchSettingCard(
            icon=FluentIcon.SHOP, title='兑换 星轨通票',
            content='90 余烬/张,月限额度动态(余烬渠道折扣价优先)')
        self.mee_pass_enabled_opt.init_with_adapter(
            YamlConfigAdapter(config, 'pass_enabled', True))
        group.addSettingCard(self.mee_pass_enabled_opt)

        self.mee_pass_priority_opt = SpinBoxSettingCard(
            icon=FluentIcon.SHOP, title='星轨通票 优先级',
            content='升序兑换', minimum=0, maximum=99)
        self.mee_pass_priority_opt.init_with_adapter(
            YamlConfigAdapter(config, 'pass_priority', 20,
                              getter_convert='int', setter_convert='int'))
        group.addSettingCard(self.mee_pass_priority_opt)

        self.mee_tracks_enabled_opt = SwitchSettingCard(
            icon=FluentIcon.SHOP, title='兑换 命运的足迹',
            content='60 余烬/张,月限 1 张(行迹 6→7 突破材料)')
        self.mee_tracks_enabled_opt.init_with_adapter(
            YamlConfigAdapter(config, 'tracks_of_destiny_enabled', True))
        group.addSettingCard(self.mee_tracks_enabled_opt)

        self.mee_tracks_priority_opt = SpinBoxSettingCard(
            icon=FluentIcon.SHOP, title='命运的足迹 优先级',
            content='升序兑换', minimum=0, maximum=99)
        self.mee_tracks_priority_opt.init_with_adapter(
            YamlConfigAdapter(config, 'tracks_of_destiny_priority', 30,
                              getter_convert='int', setter_convert='int'))
        group.addSettingCard(self.mee_tracks_priority_opt)

        return group

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

        self.relic_salvage_level_opt.init_with_adapter(self.ctx.relic_salvage_config.get_prop_adapter('salvage_level'))
        self.relic_salvage_abandon_opt.init_with_adapter(self.ctx.relic_salvage_config.get_prop_adapter('salvage_abandon'))

        self.route_yll6_xzq_opt.init_with_adapter(self.ctx.trick_snack_config.get_prop_adapter('route_yll6_xzq'))
        self.route_xzlf_xchzs_opt.init_with_adapter(self.ctx.trick_snack_config.get_prop_adapter('route_xzlf_xchzs'))
        self.synthesize_trick_snack.init_with_adapter(self.ctx.trick_snack_config.get_prop_adapter('synthesize_trick_snack'))

