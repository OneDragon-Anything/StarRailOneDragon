from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from qfluentwidgets import CaptionLabel, FluentIcon, LineEdit
from typing import List

from one_dragon.base.config.config_item import ConfigItem
from one_dragon_qt.widgets.editable_combo_box import EditableComboBox
from one_dragon_qt.widgets.setting_card.multi_push_setting_card import MultiLineSettingCard
from one_dragon_qt.widgets.vertical_scroll_interface import VerticalScrollInterface
from one_dragon.utils.i18_utils import gt
from one_dragon_qt.widgets.column import Column
from one_dragon_qt.widgets.combo_box import ComboBox
from sr_od.app.trailblaze_power.trailblaze_power_config import TrailblazePowerPlanItem
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.config.team_config import TeamNumEnum
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideMission


class EchoOfWarPlanCard(MultiLineSettingCard):

    changed = Signal(int, TrailblazePowerPlanItem)

    def __init__(self, ctx: SrContext,
                 idx: int, plan: TrailblazePowerPlanItem):
        self.ctx: SrContext = ctx
        self.idx: int = idx
        self.plan: TrailblazePowerPlanItem = plan

        self.mission_combo_box = ComboBox()
        self.mission_combo_box.currentIndexChanged.connect(self.on_mission_changed)

        self.team_opt = ComboBox()
        self.team_opt.currentIndexChanged.connect(self.on_team_changed)

        self.character_combo_box = EditableComboBox()
        self.character_combo_box.currentIndexChanged.connect(self.on_character_changed)

        run_times_label = CaptionLabel(text='已运行次数')
        self.run_times_input = LineEdit()
        self.run_times_input.textChanged.connect(self._on_run_times_changed)

        plan_times_label = CaptionLabel(text='计划次数')
        self.plan_times_input = LineEdit()
        self.plan_times_input.textChanged.connect(self._on_plan_times_changed)

        MultiLineSettingCard.__init__(
            self,
            icon=FluentIcon.CALENDAR,
            title='',
            line_list=[
                [
                    self.mission_combo_box,
                    self.team_opt,
                    self.character_combo_box,
                ],
                [
                    run_times_label,
                    self.run_times_input,
                    plan_times_label,
                    self.plan_times_input,
                ]
            ]
        )

        self.init_with_plan(plan)

    def init_mission_combo_box(self) -> None:
        tab = self.ctx.guide_data.best_match_tab_by_name(gt('生存索引', 'game'))
        category = self.ctx.guide_data.best_match_category_by_name(gt('历战余响', 'game'), tab)
        config_list = self.ctx.guide_data.get_mission_list_in_power_plan(category)
        target_mission = config_list[0].value
        for i in config_list:
            mission: GuideMission = i.value
            if mission.unique_id == self.plan.mission_id:
                target_mission = mission
                break

        self.plan.mission_id = target_mission.unique_id
        self.plan.mission = target_mission

        self.mission_combo_box.set_items(config_list, self.plan.mission)

    def init_team_opt(self) -> None:
        """
        初始化预备编队的下拉框
        """
        config_list = [i.value for i in TeamNumEnum]
        self.team_opt.set_items(config_list, self.plan.team_num)

    def init_character_box(self) -> None:
        config_list = (
                [ConfigItem('无', 'none')]
                + [ConfigItem(i.cn, i.id) for i in CHARACTER_LIST]
        )
        self.character_combo_box.set_items(config_list, self.plan.support)

    def init_run_times_input(self) -> None:
        self.run_times_input.blockSignals(True)
        self.run_times_input.setText(str(self.plan.run_times))
        self.run_times_input.blockSignals(False)

    def init_plan_times_input(self) -> None:
        self.plan_times_input.blockSignals(True)
        self.plan_times_input.setText(str(self.plan.plan_times))
        self.plan_times_input.blockSignals(False)

    def init_with_plan(self, plan: TrailblazePowerPlanItem) -> None:
        """
        以一个体力计划进行初始化
        """
        self.plan = plan

        self.init_mission_combo_box()
        self.init_team_opt()
        self.init_character_box()

        self.init_run_times_input()
        self.init_plan_times_input()

    def on_category_changed(self, idx: int) -> None:
        self.init_mission_combo_box()

        self.update_by_history()

        self._emit_value()

    def on_mission_changed(self, idx: int) -> None:
        mission: GuideMission = self.mission_combo_box.itemData(idx)
        self.plan.mission_id = mission.unique_id
        self.plan.mission = mission

        self.update_by_history()
        self._emit_value()

    def on_team_changed(self, idx: int) -> None:
        self.plan.team_num = self.team_opt.currentData()
        self._emit_value()

    def on_character_changed(self, idx: int) -> None:
        self.plan.support = self.character_combo_box.itemData(idx)
        self._emit_value()

    def _on_run_times_changed(self) -> None:
        self.plan.run_times = int(self.run_times_input.text())
        self._emit_value()

    def _on_plan_times_changed(self) -> None:
        self.plan.plan_times = int(self.plan_times_input.text())
        self._emit_value()

    def _emit_value(self) -> None:
        self.changed.emit(self.idx, self.plan)

    def update_by_history(self) -> None:
        """
        根据历史记录更新
        """
        mission: GuideMission = self.mission_combo_box.currentData()
        history = self.ctx.power_config.get_history_by_uid(mission.unique_id)
        if history is None:
            return

        self.plan.team_num = history.team_num
        self.plan.support = history.support
        self.plan.plan_times = history.plan_times
        self.plan.run_times = 0

        self.init_team_opt()
        self.init_character_box()
        self.init_plan_times_input()


class EchoOfWarSettingInterface(VerticalScrollInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx

        VerticalScrollInterface.__init__(
            self,
            object_name='sr_echo_of_war_setting_interface',
            content_widget=None, parent=parent,
            nav_text_cn='历战余响'
        )

    def get_content_widget(self) -> QWidget:
        self.content_widget = Column()

        self.card_list: List[EchoOfWarPlanCard] = []

        return self.content_widget

    def on_interface_shown(self) -> None:
        VerticalScrollInterface.on_interface_shown(self)

        self.update_plan_list_display()

    def update_plan_list_display(self):
        plan_list = self.ctx.echo_of_war_config.plan_list

        if len(plan_list) > len(self.card_list):

            while len(self.card_list) < len(plan_list):
                idx = len(self.card_list)
                card = EchoOfWarPlanCard(self.ctx, idx, plan_list[idx])
                card.changed.connect(self.on_plan_item_changed)

                self.card_list.append(card)
                self.content_widget.add_widget(card)

        for idx, plan in enumerate(plan_list):
            card = self.card_list[idx]
            card.init_with_plan(plan)

        while len(self.card_list) > len(plan_list):
            card = self.card_list[-1]
            self.content_widget.remove_widget(card)
            card.deleteLater()
            self.card_list.pop(-1)

        for card in self.card_list:
            card.mission_combo_box.setDisabled(True)

        self.content_widget.add_stretch(1)

    def on_plan_item_changed(self, idx: int, plan: TrailblazePowerPlanItem) -> None:
        self.ctx.echo_of_war_config.update_plan(idx, plan)
