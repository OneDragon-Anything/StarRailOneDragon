from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem
from qfluentwidgets import PushButton, FluentIcon, TableWidget, ToolButton, PlainTextEdit
from typing import Optional, List

from one_dragon.base.config.config_item import ConfigItem
from one_dragon_qt.widgets.combo_box import ComboBox
from one_dragon_qt.widgets.vertical_scroll_interface import VerticalScrollInterface
from one_dragon_qt.widgets.row import Row
from one_dragon_qt.widgets.setting_card.combo_box_setting_card import ComboBoxSettingCard
from one_dragon_qt.widgets.setting_card.push_setting_card import PushSettingCard
from one_dragon_qt.widgets.setting_card.switch_setting_card import SwitchSettingCard
from one_dragon_qt.widgets.setting_card.text_setting_card import TextSettingCard
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import SimUniPath, SimUniBlessLevel, SimUniBlessEnum, SimUniCurioEnum, \
    SimUniLevelTypeEnum, level_type_from_id
from sr_od.context.sr_context import SrContext


class SimUniChallengeConfigInterface(VerticalScrollInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx

        VerticalScrollInterface.__init__(
            self,
            object_name='sr_sim_uni_challenge_interface',
            content_widget=None, parent=parent,
            nav_text_cn='挑战配置'
        )

        self.chosen_config: Optional[SimUniChallengeConfig] = None
        self.edit_priority: Optional[str] = None

    def get_content_widget(self) -> QWidget:
        """
        子界面内的内容组件 由子类实现
        :return:
        """
        content_widget = QWidget()
        # 创建 QVBoxLayout 作为主布局
        main_layout = QVBoxLayout(content_widget)

        # 创建 QHBoxLayout 作为中间布局
        horizontal_layout = QHBoxLayout()

        # 将 QVBoxLayouts 加入 QHBoxLayout
        horizontal_layout.addLayout(self.get_left_layout(), stretch=1)
        horizontal_layout.addLayout(self.get_right_layout(), stretch=1)

        # 确保 QHBoxLayout 可以伸缩
        horizontal_layout.setSpacing(0)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)

        # 设置伸缩因子，让 QHBoxLayout 占据空间
        main_layout.addLayout(horizontal_layout, stretch=1)

        return content_widget

    def get_left_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()

        # 按键行
        btn_row = Row()
        layout.addWidget(btn_row)

        self.existed_yml_btn = ComboBox()
        self.existed_yml_btn.setPlaceholderText(gt('选择已有'))
        self.existed_yml_btn.currentIndexChanged.connect(self.on_config_chosen)
        btn_row.add_widget(self.existed_yml_btn)

        self.create_btn = PushButton(text=gt('新建'))
        self.create_btn.clicked.connect(self.on_create_clicked)
        btn_row.add_widget(self.create_btn)

        self.copy_btn = PushButton(text=gt('复制'))
        self.create_btn.clicked.connect(self.on_copy_clicked)
        btn_row.add_widget(self.copy_btn)

        self.delete_btn = ToolButton(FluentIcon.DELETE)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        btn_row.add_widget(self.delete_btn)

        self.cancel_btn = PushButton(text=gt('取消'))
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)
        btn_row.add_widget(self.cancel_btn)

        btn_row.add_stretch(1)

        self.name_opt = TextSettingCard(icon=FluentIcon.INFO, title='名称')
        layout.addWidget(self.name_opt)

        self.path_opt = ComboBoxSettingCard(icon=FluentIcon.INFO, title='命途')
        layout.addWidget(self.path_opt)

        self.tech_fight_opt = SwitchSettingCard(icon=FluentIcon.GAME, title='秘技开怪')
        layout.addWidget(self.tech_fight_opt)

        self.tech_only_opt = SwitchSettingCard(icon=FluentIcon.GAME, title='仅秘技开怪')
        layout.addWidget(self.tech_only_opt)

        self.max_consumable_cnt_opt = ComboBoxSettingCard(icon=FluentIcon.GAME, title='单次最多消耗品个数',
                                                      options_list=[ConfigItem(str(i), value=i) for i in range(6)])
        layout.addWidget(self.max_consumable_cnt_opt)

        self.skip_herta_opt = SwitchSettingCard(icon=FluentIcon.GAME, title='跳过黑塔')
        layout.addWidget(self.skip_herta_opt)

        self.bless_1_opt = PushSettingCard(icon=FluentIcon.GAME, title='祝福第一优先级', text='修改')
        self.bless_1_opt.clicked.connect(self.on_bless_1_edit_clicked)
        layout.addWidget(self.bless_1_opt)

        self.bless_1_input = PlainTextEdit()
        self.bless_1_input.textChanged.connect(self.on_bless_1_input_changed)
        layout.addWidget(self.bless_1_input)

        self.bless_2_opt = PushSettingCard(icon=FluentIcon.GAME, title='祝福第二优先级', text='修改')
        self.bless_2_opt.clicked.connect(self.on_bless_2_edit_clicked)
        layout.addWidget(self.bless_2_opt)

        self.bless_2_input = PlainTextEdit()
        self.bless_2_input.textChanged.connect(self.on_bless_2_input_changed)
        layout.addWidget(self.bless_2_input)

        self.curio_opt = PushSettingCard(icon=FluentIcon.GAME, title='奇物优先级', text='修改')
        self.curio_opt.clicked.connect(self.on_curio_edit_clicked)
        layout.addWidget(self.curio_opt)

        self.curio_input = PlainTextEdit()
        self.curio_input.textChanged.connect(self.on_curio_input_changed)
        layout.addWidget(self.curio_input)

        self.level_type_edit_opt = PushSettingCard(icon=FluentIcon.GAME, title='楼层优先级', text='修改')
        self.level_type_edit_opt.clicked.connect(self.on_level_type_edit_clicked)
        layout.addWidget(self.level_type_edit_opt)

        self.level_type_input = PlainTextEdit()
        self.level_type_input.textChanged.connect(self.on_level_type_input_changed)
        layout.addWidget(self.level_type_input)

        layout.addStretch(1)

        return layout

    def get_right_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()

        self.bless_btn_row = Row()
        layout.addWidget(self.bless_btn_row)

        self.bless_path_opt = ComboBox()
        self.bless_path_opt.set_items(
            [
                ConfigItem(i.value, i)
                for i in SimUniPath
            ],
            SimUniPath.HUNT
        )
        self.bless_path_opt.currentIndexChanged.connect(self.update_bless_table)
        self.bless_btn_row.add_widget(self.bless_path_opt)

        self.bless_level_opt = ComboBox()
        self.bless_level_opt.set_items(
            [
                ConfigItem(i.value, i)
                for i in SimUniBlessLevel
            ],
            SimUniBlessLevel.WHOLE
        )
        self.bless_level_opt.currentIndexChanged.connect(self.update_bless_table)
        self.bless_btn_row.add_widget(self.bless_level_opt)

        self.bless_btn_row.add_stretch(1)

        self.bless_table = TableWidget()
        self.bless_table.verticalHeader().hide()
        self.bless_table.setColumnCount(2)
        self.bless_table.setColumnWidth(0, 350)
        self.bless_table.setColumnWidth(1, 50)
        self.bless_table.setHorizontalHeaderLabels([
            gt('祝福', 'game'),
            gt('添加'),
        ])
        self.bless_table.setMinimumHeight(600)
        layout.addWidget(self.bless_table)

        self.curio_name_opt = TextSettingCard(icon=FluentIcon.GAME, title='名称搜索')
        self.curio_name_opt.value_changed.connect(self.update_curio_table)
        layout.addWidget(self.curio_name_opt)

        self.curio_table = TableWidget()
        self.curio_table.verticalHeader().hide()
        self.curio_table.setColumnCount(2)
        self.curio_table.setColumnWidth(0, 350)
        self.curio_table.setColumnWidth(1, 50)
        self.curio_table.setHorizontalHeaderLabels([
            gt('奇物', 'game'),
            gt('添加'),
        ])
        self.curio_table.setMinimumHeight(600)
        layout.addWidget(self.curio_table)

        self.level_type_table = TableWidget()
        self.level_type_table.verticalHeader().hide()
        self.level_type_table.setColumnCount(2)
        self.level_type_table.setColumnWidth(0, 350)
        self.level_type_table.setColumnWidth(1, 50)
        self.level_type_table.setHorizontalHeaderLabels([
            gt('楼层类型'),
            gt('添加'),
        ])
        self.level_type_table.setMinimumHeight(600)
        layout.addWidget(self.level_type_table)

        layout.addStretch(1)

        return layout

    def on_interface_shown(self) -> None:
        VerticalScrollInterface.on_interface_shown(self)

        self.existed_yml_btn.set_items(
            [
                ConfigItem(i.name, i)
                for i in self.ctx.sim_uni_challenge_config_data.load_all_challenge_config()
            ]
        )

        self.edit_priority = None
        self.update_display_by_config()
        self.update_bless_table()
        self.update_curio_table()
        self.update_level_type_table()
        self.update_priority_input_display()

    def update_display_by_config(self) -> None:
        chosen = self.chosen_config is not None

        self.existed_yml_btn.setDisabled(chosen)
        self.create_btn.setDisabled(chosen)
        self.copy_btn.setDisabled(not chosen)
        self.delete_btn.setDisabled(not chosen)
        self.cancel_btn.setDisabled(not chosen)

        self.name_opt.setDisabled(not chosen)
        self.path_opt.setDisabled(not chosen)
        self.tech_fight_opt.setDisabled(not chosen)
        self.tech_only_opt.setDisabled(not chosen)
        self.max_consumable_cnt_opt.setDisabled(not chosen)
        self.skip_herta_opt.setDisabled(not chosen)
        self.bless_1_opt.setDisabled(not chosen)
        self.bless_1_input.setDisabled(not chosen)
        self.bless_2_opt.setDisabled(not chosen)
        self.bless_2_input.setDisabled(not chosen)
        self.curio_opt.setDisabled(not chosen)
        self.curio_input.setDisabled(not chosen)
        self.level_type_edit_opt.setDisabled(not chosen)
        self.level_type_input.setDisabled(not chosen)

        if chosen:
            self.name_opt.init_with_adapter(self.chosen_config.name_adapter)
            self.path_opt.set_options_by_list([ConfigItem(i.value, i.name) for i in SimUniPath])
            self.path_opt.init_with_adapter(self.chosen_config.path_adapter)
            self.tech_fight_opt.init_with_adapter(self.chosen_config.technique_fight_adapter)
            self.tech_only_opt.init_with_adapter(self.chosen_config.technique_only_adapter)
            self.max_consumable_cnt_opt.init_with_adapter(self.chosen_config.max_consumable_cnt_adapter)
            self.skip_herta_opt.init_with_adapter(self.chosen_config.skip_herta_adapter)

            self.bless_1_input.blockSignals(True)
            self.bless_1_input.setPlainText('\n'.join([SimUniBlessEnum[i].value.title for i in self.chosen_config.bless_priority]))
            self.bless_1_input.blockSignals(False)

            self.bless_2_input.blockSignals(True)
            self.bless_2_input.setPlainText('\n'.join([SimUniBlessEnum[i].value.title for i in self.chosen_config.bless_priority_2]))
            self.bless_2_input.blockSignals(False)

            self.curio_input.blockSignals(True)
            self.curio_input.setPlainText('\n'.join([SimUniCurioEnum[i].value.name for i in self.chosen_config.curio_priority]))
            self.curio_input.blockSignals(False)

            self.level_type_input.blockSignals(True)
            self.level_type_input.setPlainText('\n'.join([level_type_from_id(i).type_name for i in self.chosen_config.level_type_priority]))
            self.level_type_input.blockSignals(False)

    def update_bless_table(self, idx: int = None) -> None:
        path: SimUniPath = self.bless_path_opt.currentData()
        level: SimUniBlessLevel = self.bless_level_opt.currentData()

        bless_list = [i for i in SimUniBlessEnum if i.value.path == path and i.value.level == level]
        self.bless_table.setRowCount(len(bless_list))

        for idx in range(len(bless_list)):
            bless: SimUniBlessEnum = bless_list[idx]
            add_btn = ToolButton(FluentIcon.ADD, parent=None)
            # 按钮的点击事件绑定route.unique_id
            add_btn.setProperty('bless_name', bless.name)
            add_btn.clicked.connect(self.on_bless_added)

            self.bless_table.setItem(idx, 0, QTableWidgetItem(bless.value.title))
            self.bless_table.setCellWidget(idx, 1, add_btn)

    def update_curio_table(self, value=None) -> None:
        curio_name = self.curio_name_opt.line_edit.text().strip()

        curio_list = [
            i
            for i in SimUniCurioEnum
            if (
                   curio_name == ''
                   or i.value.name.find(curio_name) != -1
                   or i.value.py.lower().find(curio_name.lower()) != -1
            )
        ]
        self.curio_table.setRowCount(len(curio_list))

        for idx in range(len(curio_list)):
            curio: SimUniCurioEnum = curio_list[idx]
            add_btn = ToolButton(FluentIcon.ADD, parent=None)
            # 按钮的点击事件绑定route.unique_id
            add_btn.setProperty('curio_name', curio.name)
            add_btn.clicked.connect(self.on_curio_added)

            self.curio_table.setItem(idx, 0, QTableWidgetItem(curio.value.name))
            self.curio_table.setCellWidget(idx, 1, add_btn)

    def update_level_type_table(self) -> None:
        level_enum_list = [i for i in SimUniLevelTypeEnum]
        self.level_type_table.setRowCount(len(level_enum_list))
        for idx in range(len(level_enum_list)):
            level_type: SimUniLevelTypeEnum = level_enum_list[idx]
            add_btn = ToolButton(FluentIcon.ADD, parent=None)
            # 按钮的点击事件绑定route.unique_id
            add_btn.setProperty('level_type_name', level_type.name)
            add_btn.clicked.connect(self.on_level_type_added)

            self.level_type_table.setItem(idx, 0, QTableWidgetItem(level_type.value.type_name))
            self.level_type_table.setCellWidget(idx, 1, add_btn)

    def update_priority_input_display(self) -> None:
        chosen = self.chosen_config is not None
        self.bless_1_input.setVisible(chosen and self.edit_priority == 'bless_1')
        self.bless_2_input.setVisible(chosen and self.edit_priority == 'bless_2')

        edit_bless = self.edit_priority in ['bless_1', 'bless_2']
        self.bless_btn_row.setVisible(edit_bless)
        self.bless_table.setVisible(edit_bless)

        self.curio_input.setVisible(chosen and self.edit_priority == 'curio')
        edit_curio = self.edit_priority == 'curio'
        self.curio_name_opt.setVisible(edit_curio)
        self.curio_table.setVisible(edit_curio)

        self.level_type_input.setVisible(chosen and self.edit_priority == 'level_type')
        edit_level_type = self.edit_priority == 'level_type'
        self.level_type_table.setVisible(edit_level_type)

    def on_config_chosen(self, idx: int) -> None:
        self.chosen_config = self.existed_yml_btn.currentData()
        self.update_display_by_config()

    def on_create_clicked(self) -> None:
        if self.chosen_config is not None:
            return

        self.chosen_config = self.ctx.sim_uni_challenge_config_data.create_new_challenge_config()
        self.update_display_by_config()

    def on_copy_clicked(self) -> None:
        if self.chosen_config is None:
            return

        self.chosen_config = self.ctx.sim_uni_challenge_config_data.create_new_challenge_config(self.chosen_config.idx)
        self.update_display_by_config()

    def on_delete_clicked(self):
        if self.chosen_config is None:
            return
        self.chosen_config.delete()

        self.chosen_config = None
        self.update_display_by_config()

    def on_cancel_clicked(self):
        self.chosen_config = None
        self.update_display_by_config()

    def on_bless_1_edit_clicked(self) -> None:
        if self.chosen_config is None:
            return

        if self.edit_priority == 'bless_1':
            self.edit_priority = None
        else:
            self.edit_priority = 'bless_1'

        self.update_priority_input_display()

    def on_bless_1_input_changed(self) -> None:
        if self.chosen_config is None:
            return

        bless_list = self.convert_text_2_bless_list(self.bless_1_input.toPlainText())

        # 更新文本框显示
        new_full_text = '\n'.join([i.value.title for i in bless_list])
        self.bless_1_input.blockSignals(True)
        self.bless_1_input.setPlainText(new_full_text)
        self.bless_1_input.blockSignals(False)

        # 更新配置
        self.chosen_config.bless_priority = [i.name for i in bless_list]

    def on_bless_2_edit_clicked(self) -> None:
        if self.chosen_config is None:
            return

        if self.edit_priority == 'bless_2':
            self.edit_priority = None
        else:
            self.edit_priority = 'bless_2'

        self.update_priority_input_display()

    def on_bless_2_input_changed(self) -> None:
        if self.chosen_config is None:
            return

        bless_list = self.convert_text_2_bless_list(self.bless_2_input.toPlainText())

        # 更新文本框显示
        new_full_text = '\n'.join([i.value.title for i in bless_list])
        self.bless_2_input.blockSignals(True)
        self.bless_2_input.setPlainText(new_full_text)
        self.bless_2_input.blockSignals(False)

        # 更新配置
        self.chosen_config.bless_priority_2 = [i.name for i in bless_list]

    def convert_text_2_bless_list(self, full_text: str) -> List[SimUniBlessEnum]:
        bless_enum_list = []
        bless_title_list = []
        for bless_enum in SimUniBlessEnum:
            bless_enum_list.append(bless_enum)
            bless_title_list.append(bless_enum.value.title)

        result_list = []
        line_text_arr = full_text.split('\n')
        for line_text in line_text_arr:
            idx = str_utils.find_best_match_by_difflib(line_text, bless_title_list)
            if idx is not None and idx != -1:
                result_list.append(bless_enum_list[idx])

        return result_list

    def on_bless_added(self) -> None:
        if self.chosen_config is None:
            return
        if self.edit_priority not in ['bless_1', 'bless_2']:
            return

        btn = self.sender()
        if btn is not None:
            bless_name = btn.property('bless_name')
            bless = SimUniBlessEnum[bless_name]

            input_component = self.bless_1_input if self.edit_priority == 'bless_1' else self.bless_2_input
            input_component.setPlainText(input_component.toPlainText() + '\n' + bless.value.title)

    def on_curio_edit_clicked(self) -> None:
        if self.chosen_config is None:
            return

        if self.edit_priority == 'curio':
            self.edit_priority = None
        else:
            self.edit_priority = 'curio'

        self.update_priority_input_display()

    def on_curio_input_changed(self) -> None:
        if self.chosen_config is None:
            return

        curio_enum_list = []
        curio_title_list = []
        for curio_enum in SimUniCurioEnum:
            curio_enum_list.append(curio_enum)
            curio_title_list.append(curio_enum.value.name)

        input_curio_list = []
        full_text = self.curio_input.toPlainText()
        for line_text in full_text.split('\n'):
            idx = str_utils.find_best_match_by_difflib(line_text, curio_title_list)
            if idx is not None and idx != -1:
                input_curio_list.append(curio_enum_list[idx])

        self.chosen_config.curio_priority = [i.name for i in input_curio_list]

        self.curio_input.blockSignals(True)
        self.curio_input.setPlainText('\n'.join([i.value.name for i in input_curio_list]))
        self.curio_input.blockSignals(False)

    def on_curio_added(self) -> None:
        if self.chosen_config is None:
            return

        if self.edit_priority != 'curio':
            return

        btn = self.sender()
        if btn is not None:
            curio_name = btn.property('curio_name')
            curio = SimUniCurioEnum[curio_name]
            self.curio_input.setPlainText(self.curio_input.toPlainText() + '\n' + curio.value.name)

    def on_level_type_edit_clicked(self) -> None:
        if self.chosen_config is None:
            return
        if self.edit_priority == 'level_type':
            self.edit_priority = None
        else:
            self.edit_priority = 'level_type'

        self.update_priority_input_display()

    def on_level_type_input_changed(self) -> None:
        if self.chosen_config is None:
            return

        level_type_enum_list = []
        level_type_title_list = []
        for level_type_enum in SimUniLevelTypeEnum:
            level_type_enum_list.append(level_type_enum)
            level_type_title_list.append(level_type_enum.value.type_name)

        input_level_type_list = []
        full_text = self.level_type_input.toPlainText()
        for line_text in full_text.split('\n'):
            idx = str_utils.find_best_match_by_difflib(line_text, level_type_title_list)
            if idx is not None and idx != -1:
                input_level_type_list.append(level_type_enum_list[idx])

        self.chosen_config.level_type_priority = [i.value.type_id for i in input_level_type_list]

        self.level_type_input.blockSignals(True)
        self.level_type_input.setPlainText('\n'.join([i.value.type_name for i in input_level_type_list]))
        self.level_type_input.blockSignals(False)

    def on_level_type_added(self) -> None:
        if self.chosen_config is None:
            return
        if self.edit_priority != 'level_type':
            return
        btn = self.sender()
        if btn is not None:
            level_type_name = btn.property('level_type_name')
            level_type = SimUniLevelTypeEnum[level_type_name]
            self.level_type_input.setPlainText(self.level_type_input.toPlainText() + '\n' + level_type.value.type_name)