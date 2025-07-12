import os
from PySide6.QtWidgets import QWidget, QFileDialog
from qfluentwidgets import SettingCardGroup, FluentIcon, PushSettingCard

from one_dragon_qt.widgets.column import Column
from one_dragon_qt.widgets.vertical_scroll_interface import VerticalScrollInterface
from one_dragon_qt.widgets.setting_card.combo_box_setting_card import ComboBoxSettingCard
from one_dragon_qt.widgets.setting_card.key_setting_card import KeySettingCard
from one_dragon_qt.widgets.setting_card.switch_setting_card import SwitchSettingCard
from one_dragon_qt.widgets.setting_card.text_setting_card import TextSettingCard
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.config.game_config import GameRegionEnum, RunModeEnum
from one_dragon.base.config.basic_game_config import TypeInputWay, ScreenSizeEnum, FullScreenEnum, MonitorEnum
from sr_od.context.sr_context import SrContext


class SrSettingGameInterface(VerticalScrollInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx

        VerticalScrollInterface.__init__(
            self,
            object_name='sr_setting_game_interface',
            content_widget=None, parent=parent,
            nav_text_cn='游戏设置'
        )

    def get_content_widget(self) -> QWidget:
        content_widget = Column()

        content_widget.add_widget(self._get_basic_group())
        content_widget.add_widget(self._get_launch_argument_group())
        content_widget.add_widget(self._get_key_group())
        content_widget.add_stretch(1)

        return content_widget

    def _get_basic_group(self) -> QWidget:
        basic_group = SettingCardGroup(gt('游戏基础'))

        self.input_way_opt = ComboBoxSettingCard(icon=FluentIcon.CLIPPING_TOOL, title='输入方式',
                                                 options_enum=TypeInputWay)
        basic_group.addSettingCard(self.input_way_opt)

        self.run_opt = ComboBoxSettingCard(icon=FluentIcon.GAME, title='疾跑', options_enum=RunModeEnum)
        basic_group.addSettingCard(self.run_opt)

        self.use_quirky_snacks_opt = SwitchSettingCard(icon=FluentIcon.CAFE, title='只用奇巧零食')
        basic_group.addSettingCard(self.use_quirky_snacks_opt)

        return basic_group

    def _get_launch_argument_group(self) -> QWidget:
        launch_argument_group = SettingCardGroup(gt('启动参数'))

        self.launch_argument_switch = SwitchSettingCard(icon=FluentIcon.SETTING, title='启用')
        self.launch_argument_switch.value_changed.connect(self._on_launch_argument_switch_changed)
        launch_argument_group.addSettingCard(self.launch_argument_switch)

        self.screen_size_opt = ComboBoxSettingCard(icon=FluentIcon.SETTING, title='窗口尺寸', options_enum=ScreenSizeEnum)
        launch_argument_group.addSettingCard(self.screen_size_opt)

        self.full_screen_opt = ComboBoxSettingCard(icon=FluentIcon.SETTING, title='全屏', options_enum=FullScreenEnum)
        launch_argument_group.addSettingCard(self.full_screen_opt)

        self.popup_window_switch = SwitchSettingCard(icon=FluentIcon.SETTING, title='无边框窗口')
        launch_argument_group.addSettingCard(self.popup_window_switch)

        self.monitor_opt = ComboBoxSettingCard(icon=FluentIcon.SETTING, title='显示器序号', options_enum=MonitorEnum)
        launch_argument_group.addSettingCard(self.monitor_opt)

        self.launch_argument_advance = TextSettingCard(
            icon=FluentIcon.SETTING,
            title='高级参数',
            input_placeholder='如果你不知道这是做什么的 请不要填写'
        )
        launch_argument_group.addSettingCard(self.launch_argument_advance)

        # self.help_opt = HyperlinkCard(icon=FluentIcon.HELP, title='使用说明', text='前往',
        #                               url='https://onedragon-anything.github.io/sr/zh/docs/feat_launch_argument.html')
        # self.help_opt.setContent('先看说明 再使用与提问')
        # launch_argument_group.addSettingCard(self.help_opt)

        # 这里可以补充文档后取消注释

        return launch_argument_group

    def _get_key_group(self) -> QWidget:
        key_group = SettingCardGroup(gt('游戏按键'))

        self.key_interact_opt = KeySettingCard(icon=FluentIcon.GAME, title='交互')
        key_group.addSettingCard(self.key_interact_opt)

        self.key_technique_opt = KeySettingCard(icon=FluentIcon.GAME, title='秘技')
        key_group.addSettingCard(self.key_technique_opt)

        self.key_open_map_opt = KeySettingCard(icon=FluentIcon.GAME, title='地图')
        key_group.addSettingCard(self.key_open_map_opt)

        self.key_esc_opt = KeySettingCard(icon=FluentIcon.GAME, title='返回')
        key_group.addSettingCard(self.key_esc_opt)

        self.key_gameplay_interaction_opt = KeySettingCard(icon=FluentIcon.GAME, title='玩法交互')
        key_group.addSettingCard(self.key_gameplay_interaction_opt)

        return key_group

    def on_interface_shown(self) -> None:
        VerticalScrollInterface.on_interface_shown(self)

        self.input_way_opt.init_with_adapter(self.ctx.game_config.type_input_way_adapter)
        self.run_opt.init_with_adapter(self.ctx.game_config.run_mode_adapter)
        self.use_quirky_snacks_opt.init_with_adapter(self.ctx.game_config.use_quirky_snacks_adapter)

        self.launch_argument_switch.init_with_adapter(self.ctx.game_config.get_prop_adapter('launch_argument'))
        self.screen_size_opt.init_with_adapter(self.ctx.game_config.get_prop_adapter('screen_size'))
        self.full_screen_opt.init_with_adapter(self.ctx.game_config.get_prop_adapter('full_screen'))
        self.popup_window_switch.init_with_adapter(self.ctx.game_config.get_prop_adapter('popup_window'))
        self.monitor_opt.init_with_adapter(self.ctx.game_config.get_prop_adapter('monitor'))
        self.launch_argument_advance.init_with_adapter(self.ctx.game_config.get_prop_adapter('launch_argument_advance'))
        self._update_launch_argument_part()

        self.key_interact_opt.init_with_adapter(self.ctx.game_config.get_prop_adapter('key_interact'))
        self.key_technique_opt.init_with_adapter(self.ctx.game_config.get_prop_adapter('key_technique'))
        self.key_open_map_opt.init_with_adapter(self.ctx.game_config.get_prop_adapter('key_open_map'))
        self.key_esc_opt.init_with_adapter(self.ctx.game_config.get_prop_adapter('key_esc'))
        self.key_gameplay_interaction_opt.init_with_adapter(self.ctx.game_config.get_prop_adapter('key_gameplay_interaction'))

    def _update_launch_argument_part(self) -> None:
        """
        启动参数部分更新显示
        :return:
        """
        value = self.ctx.game_config.launch_argument
        self.screen_size_opt.setVisible(value)
        self.full_screen_opt.setVisible(value)
        self.popup_window_switch.setVisible(value)
        self.monitor_opt.setVisible(value)
        self.launch_argument_advance.setVisible(value)

    def _on_launch_argument_switch_changed(self) -> None:
        self._update_launch_argument_part()
