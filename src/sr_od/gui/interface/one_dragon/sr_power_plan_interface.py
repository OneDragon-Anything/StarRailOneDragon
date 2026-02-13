from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from qfluentwidgets import PrimaryPushButton, PushButton, FluentIcon, CaptionLabel, LineEdit, ToolButton, Dialog
from typing import List

from one_dragon.base.config.config_item import ConfigItem
from one_dragon_qt.widgets.column import Column
from one_dragon_qt.widgets.combo_box import ComboBox
from one_dragon_qt.widgets.editable_combo_box import EditableComboBox
from one_dragon_qt.widgets.vertical_scroll_interface import VerticalScrollInterface
from one_dragon_qt.widgets.setting_card.multi_push_setting_card import MultiLineSettingCard
from one_dragon_qt.widgets.setting_card.multi_push_setting_card import MultiPushSettingCard
from one_dragon_qt.widgets.setting_card.switch_setting_card import SwitchSettingCard
from sr_od.app.trailblaze_power.trailblaze_power_config import TrailblazePowerPlanItem
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.config.team_config import TeamNumEnum
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideMission


class PowerPlanCard(MultiLineSettingCard):

    changed = Signal(int, TrailblazePowerPlanItem)
    delete = Signal(int)
    move_up = Signal(int)
    move_top = Signal(int)

    def __init__(self, ctx: SrContext,
                 idx: int, plan: TrailblazePowerPlanItem):
        self.ctx: SrContext = ctx
        self.idx: int = idx
        self.plan: TrailblazePowerPlanItem = plan

        self.category_combo_box = ComboBox()
        self.category_combo_box.currentIndexChanged.connect(self.on_category_changed)

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

        self.move_up_btn = ToolButton(FluentIcon.UP, None)
        self.move_up_btn.clicked.connect(self._on_move_up_clicked)
        self.move_top_btn = ToolButton(FluentIcon.PIN, None)
        self.move_top_btn.clicked.connect(self._on_move_top_clicked)
        self.del_btn = ToolButton(FluentIcon.DELETE, None)
        self.del_btn.clicked.connect(self._on_del_clicked)

        MultiLineSettingCard.__init__(
            self,
            icon=FluentIcon.CALENDAR,
            title='',
            line_list=[
                [
                    self.category_combo_box,
                    self.mission_combo_box,
                    self.team_opt,
                    self.character_combo_box,
                ],
                [
                    run_times_label,
                    self.run_times_input,
                    plan_times_label,
                    self.plan_times_input,
                    self.move_up_btn,
                    self.move_top_btn,
                    self.del_btn,
                ]
            ]
        )

        self.init_with_plan(plan)

    def init_category_combo_box(self) -> None:
        config_list = self.ctx.guide_data.get_category_list_in_power_plan()
        self.category_combo_box.set_items(config_list, self.plan.mission.cate)

    def init_mission_combo_box(self) -> None:
        category = self.category_combo_box.currentData()
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
                [ConfigItem('无', 'none'), ConfigItem('随机', 'random')]
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

        self.init_category_combo_box()
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

    def _on_move_up_clicked(self) -> None:
        self.move_up.emit(self.idx)

    def _on_move_top_clicked(self) -> None:
        self.move_top.emit(self.idx)

    def _on_del_clicked(self) -> None:
        self.delete.emit(self.idx)

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


class PowerPlanInterface(VerticalScrollInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx

        VerticalScrollInterface.__init__(
            self,
            object_name='sr_power_plan_interface',
            content_widget=None, parent=parent,
            nav_text_cn='体力计划'
        )

    def get_content_widget(self) -> QWidget:
        self.content_widget = Column()

        self.loop_opt = SwitchSettingCard(icon=FluentIcon.SYNC, title='循环执行', content='开启时 会循环执行到体力用尽')
        self.content_widget.add_widget(self.loop_opt)

        self.cancel_btn = PushButton(icon=FluentIcon.CANCEL, text='撤销')
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)

        self.remove_all_completed_btn = PushButton(
            icon=FluentIcon.DELETE, text='删除已完成'
        )
        self.remove_all_completed_btn.clicked.connect(self._on_remove_all_completed_clicked)

        self.remove_all_btn = PushButton(
            icon=FluentIcon.DELETE, text='删除所有'
        )
        self.remove_all_btn.clicked.connect(self._on_remove_all_clicked)

        self.remove_setting_card = MultiPushSettingCard(btn_list=[
            self.cancel_btn,
            self.remove_all_completed_btn,
            self.remove_all_btn
        ], icon=FluentIcon.DELETE, title='删除体力计划')
        self.content_widget.add_widget(self.remove_setting_card)

        self.card_list: List[PowerPlanCard] = []

        self.plus_btn = PrimaryPushButton(text='新增')
        self.plus_btn.clicked.connect(self._on_add_clicked)
        self.content_widget.add_widget(self.plus_btn, stretch=1)

        return self.content_widget

    def on_interface_shown(self) -> None:
        VerticalScrollInterface.on_interface_shown(self)

        self.loop_opt.init_with_adapter(self.ctx.power_config.loop_adapter)
        self.update_plan_list_display()

    def on_interface_hidden(self) -> None:
        VerticalScrollInterface.on_interface_hidden(self)

    def update_plan_list_display(self):
        plan_list = self.ctx.power_config.plan_list

        if len(plan_list) > len(self.card_list):
            self.content_widget.remove_widget(self.plus_btn)

            while len(self.card_list) < len(plan_list):
                idx = len(self.card_list)
                card = PowerPlanCard(self.ctx, idx, plan_list[idx])
                card.changed.connect(self._on_plan_item_changed)
                card.delete.connect(self._on_plan_item_deleted)
                card.move_up.connect(self._on_plan_item_move_up)
                card.move_top.connect(self._on_plan_item_move_top)

                self.card_list.append(card)
                self.content_widget.add_widget(card)

            self.content_widget.add_widget(self.plus_btn, stretch=1)

        for idx, plan in enumerate(plan_list):
            card = self.card_list[idx]
            card.init_with_plan(plan)

        while len(self.card_list) > len(plan_list):
            card = self.card_list[-1]
            self.content_widget.remove_widget(card)
            card.deleteLater()
            self.card_list.pop(-1)

    def _on_add_clicked(self) -> None:
        self.ctx.power_config.add_plan()
        self.update_plan_list_display()

    def _on_plan_item_changed(self, idx: int, plan: TrailblazePowerPlanItem) -> None:
        self.ctx.power_config.update_plan(idx, plan)

    def _on_plan_item_deleted(self, idx: int) -> None:
        self.ctx.power_config.delete_plan(idx)
        self.update_plan_list_display()

    def _on_plan_item_move_up(self, idx: int) -> None:
        self.ctx.power_config.move_up(idx)
        self.update_plan_list_display()

    def _on_plan_item_move_top(self, idx: int) -> None:
        self.ctx.power_config.move_top(idx)
        self.update_plan_list_display()

    def _on_remove_all_completed_clicked(self) -> None:
        dialog = Dialog('警告', '是否删除所有已完成的体力计划？', self)
        dialog.setTitleBarVisible(False)
        dialog.yesButton.setText('确定')
        dialog.cancelButton.setText('取消')
        if dialog.exec():
            self.plan_list_backup = self.ctx.power_config.plan_list.copy()
            not_completed_plans = [plan for plan in self.ctx.power_config.plan_list
                                if plan.run_times < plan.plan_times]
            self.ctx.power_config.plan_list = not_completed_plans.copy()
            self.ctx.power_config.save()
            self.cancel_btn.setEnabled(True)
        self.update_plan_list_display()

    def _on_remove_all_clicked(self) -> None:
        dialog = Dialog('警告', '是否删除所有体力计划？', self)
        dialog.setTitleBarVisible(False)
        dialog.yesButton.setText('确定')
        dialog.cancelButton.setText('取消')
        if dialog.exec():
            self.plan_list_backup = self.ctx.power_config.plan_list.copy()
            self.ctx.power_config.plan_list.clear()
            self.ctx.power_config.save()
            self.cancel_btn.setEnabled(True)
        self.update_plan_list_display()

    def _on_cancel_clicked(self) -> None:
        self.ctx.power_config.plan_list = self.plan_list_backup.copy()
        self.cancel_btn.setEnabled(False)
        self.update_plan_list_display()
