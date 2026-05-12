from PySide6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon

from one_dragon.base.config.config_item import ConfigItem
from one_dragon_qt.widgets.column import Column
from one_dragon_qt.widgets.setting_card.editable_combo_box_setting_card import EditableComboBoxSettingCard
from one_dragon_qt.widgets.vertical_scroll_interface import VerticalScrollInterface
from one_dragon_qt.widgets.setting_card.combo_box_setting_card import ComboBoxSettingCard
from one_dragon_qt.widgets.setting_card.switch_setting_card import SwitchSettingCard
from sr_od.application.world_patrol.world_patrol_whitelist_config import load_all_whitelist_list, WorldPatrolWhitelist
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.context.sr_context import SrContext


class WorldPatrolSettingInterface(VerticalScrollInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx

        VerticalScrollInterface.__init__(
            self,
            object_name='sr_setting_world_patrol_interface',
            content_widget=None, parent=parent,
            nav_text_cn='设置'
        )

    def get_content_widget(self) -> QWidget:
        content_widget = Column()

        self.team_num_opt = ComboBoxSettingCard(icon=FluentIcon.PEOPLE, title='使用配队',
                                                content='0代表使用当前配队',
                                                options_list=[ConfigItem(str(i)) for i in range(10)])
        content_widget.add_widget(self.team_num_opt)

        self.character_1_opt = EditableComboBoxSettingCard(icon=FluentIcon.PEOPLE, title='1号位角色',
                                                           content='手动指定1号位角色可以避免识别错误')
        content_widget.add_widget(self.character_1_opt)

        self.whitelist_id_opt = ComboBoxSettingCard(icon=FluentIcon.PEOPLE, title='路线名单')
        content_widget.add_widget(self.whitelist_id_opt)

        self.tech_fight_opt = SwitchSettingCard(icon=FluentIcon.GAME, title='秘技开怪')
        content_widget.add_widget(self.tech_fight_opt)

        self.tech_only_opt = SwitchSettingCard(icon=FluentIcon.GAME, title='仅秘技开怪')
        content_widget.add_widget(self.tech_only_opt)

        self.max_consumable_cnt_opt = ComboBoxSettingCard(icon=FluentIcon.GAME, title='单次最多消耗品个数',
                                                      options_list=[ConfigItem(str(i)) for i in range(6)])
        content_widget.add_widget(self.max_consumable_cnt_opt)

        content_widget.add_stretch(1)

        return content_widget

    def on_interface_shown(self) -> None:
        VerticalScrollInterface.on_interface_shown(self)

        self.team_num_opt.init_with_adapter(self.ctx.world_patrol_config.team_num_adapter)
        config_list = (
                [ConfigItem('游戏识别', 'none')]
                + [ConfigItem(i.cn, i.id) for i in CHARACTER_LIST]
        )
        self.character_1_opt.set_options_by_list(config_list)
        self.character_1_opt.init_with_adapter(self.ctx.world_patrol_config.character_1_adapter)

        self.tech_fight_opt.init_with_adapter(self.ctx.world_patrol_config.technique_fight_adapter)
        self.tech_only_opt.init_with_adapter(self.ctx.world_patrol_config.technique_only_adapter)
        self.max_consumable_cnt_opt.init_with_adapter(self.ctx.world_patrol_config.max_consumable_cnt_adapter)

        config_list = [WorldPatrolWhitelist(i) for i in load_all_whitelist_list()]
        self.whitelist_id_opt.set_options_by_list(
            [ConfigItem('无', value='')]
            +
            [ConfigItem(i.name, i.module_name) for i in config_list]
        )
        self.whitelist_id_opt.init_with_adapter(self.ctx.world_patrol_config.whitelist_id_adapter)
