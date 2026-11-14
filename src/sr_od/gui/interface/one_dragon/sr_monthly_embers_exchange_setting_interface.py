"""每月余烬兑换配置页(一条龙应用设置列表的默认形态)。

config 经 run_context 取 factory 缓存实例(与 app 运行/MCP 写入同一份,
改完下一次 run 即生效);绑定用 YamlConfigAdapter 直连 property
(ApplicationConfig 走 YamlOperator,无 YamlConfig.get_prop_adapter)。
"""

from PySide6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon, SettingCardGroup
from one_dragon.base.operation.application import application_const
from one_dragon_qt.widgets.column import Column
from one_dragon_qt.widgets.setting_card.spin_box_setting_card import (
    SpinBoxSettingCard,
)
from one_dragon_qt.widgets.setting_card.switch_setting_card import (
    SwitchSettingCard,
)
from one_dragon_qt.widgets.setting_card.yaml_config_adapter import (
    YamlConfigAdapter,
)
from one_dragon_qt.widgets.vertical_scroll_interface import (
    VerticalScrollInterface,
)
from one_dragon.utils.i18_utils import gt
from sr_od.application.monthly_embers_exchange import (
    monthly_embers_exchange_const,
)
from sr_od.context.sr_context import SrContext


class MonthlyEmbersExchangeSettingInterface(VerticalScrollInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx

        VerticalScrollInterface.__init__(
            self,
            object_name='sr_monthly_embers_exchange_setting_interface',
            content_widget=None, parent=parent,
            nav_text_cn=gt('每月余烬兑换', 'game')
        )

    def _get_config(self):
        return self.ctx.run_context.get_config(
            app_id=monthly_embers_exchange_const.APP_ID,
            instance_idx=self.ctx.current_instance_idx,
            group_id=application_const.DEFAULT_GROUP_ID,
        )

    def get_content_widget(self) -> QWidget:
        column = Column()

        config = self._get_config()
        group = SettingCardGroup(gt('每月余烬兑换', 'game'))

        self.special_pass_enabled_opt = SwitchSettingCard(
            icon=FluentIcon.SHOP, title='兑换 星轨专票',
            content='90 余烬/张,月限 5 张(跃迁抽卡票)')
        self.special_pass_enabled_opt.init_with_adapter(
            YamlConfigAdapter(config, 'special_pass_enabled', True))
        group.add_setting_card(self.special_pass_enabled_opt)

        self.special_pass_priority_opt = SpinBoxSettingCard(
            icon=FluentIcon.SHOP, title='星轨专票 优先级',
            content='升序兑换;同优先级按 专票>通票>足迹 兜底', minimum=0,
            maximum=99)
        self.special_pass_priority_opt.init_with_adapter(
            YamlConfigAdapter(config, 'special_pass_priority', 10,
                              getter_convert='int', setter_convert='int'))
        group.add_setting_card(self.special_pass_priority_opt)

        self.pass_enabled_opt = SwitchSettingCard(
            icon=FluentIcon.SHOP, title='兑换 星轨通票',
            content='90 余烬/张,月限额度动态(余烬渠道折扣价优先)')
        self.pass_enabled_opt.init_with_adapter(
            YamlConfigAdapter(config, 'pass_enabled', True))
        group.add_setting_card(self.pass_enabled_opt)

        self.pass_priority_opt = SpinBoxSettingCard(
            icon=FluentIcon.SHOP, title='星轨通票 优先级',
            content='升序兑换', minimum=0, maximum=99)
        self.pass_priority_opt.init_with_adapter(
            YamlConfigAdapter(config, 'pass_priority', 20,
                              getter_convert='int', setter_convert='int'))
        group.add_setting_card(self.pass_priority_opt)

        self.tracks_of_destiny_enabled_opt = SwitchSettingCard(
            icon=FluentIcon.SHOP, title='兑换 命运的足迹',
            content='60 余烬/张,月限 1 张(行迹 6→7 突破材料)')
        self.tracks_of_destiny_enabled_opt.init_with_adapter(
            YamlConfigAdapter(config, 'tracks_of_destiny_enabled', True))
        group.add_setting_card(self.tracks_of_destiny_enabled_opt)

        self.tracks_of_destiny_priority_opt = SpinBoxSettingCard(
            icon=FluentIcon.SHOP, title='命运的足迹 优先级',
            content='升序兑换', minimum=0, maximum=99)
        self.tracks_of_destiny_priority_opt.init_with_adapter(
            YamlConfigAdapter(config, 'tracks_of_destiny_priority', 30,
                              getter_convert='int', setter_convert='int'))
        group.add_setting_card(self.tracks_of_destiny_priority_opt)

        column.add_widget(group)
        column.add_stretch(1)
        return column
