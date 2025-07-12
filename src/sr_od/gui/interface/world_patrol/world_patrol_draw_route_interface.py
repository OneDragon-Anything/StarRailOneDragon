from typing import Optional, List

import yaml
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from cv2.typing import MatLike
from qfluentwidgets import PushButton, PlainTextEdit, SettingCardGroup, ToolButton, FluentIcon, LineEdit

from one_dragon.base.config.config_item import ConfigItem
from one_dragon.base.operation.context_event_bus import ContextEventItem
from one_dragon.base.operation.one_dragon_context import ContextKeyboardEventEnum
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon_qt.widgets.combo_box import ComboBox
from one_dragon_qt.widgets.image_viewer_widget import ImageViewerWidget
from one_dragon_qt.widgets.row import Row
from one_dragon_qt.widgets.setting_card.switch_setting_card import SwitchSettingCard
from one_dragon_qt.widgets.vertical_scroll_interface import VerticalScrollInterface
from sr_od.app.world_patrol import world_patrol_route_draw_utils
from sr_od.app.world_patrol.world_patrol_app import WorldPatrolApp
from sr_od.app.world_patrol.world_patrol_route import WorldPatrolRoute
from sr_od.app.world_patrol.world_patrol_whitelist_config import WorldPatrolWhitelist
from sr_od.config import operation_const
from sr_od.context.sr_context import SrContext
from sr_od.sr_map.sr_map_def import Planet, Region, SpecialPoint


class WorldPatrolDrawRouteInterface(VerticalScrollInterface):

    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx

        VerticalScrollInterface.__init__(
            self,
            object_name='sr_world_patrol_draw_route_interface',
            content_widget=None, parent=parent,
            nav_text_cn='路线绘制'
        )

        self.chosen_planet: Optional[Planet] = None
        self.chosen_region_without_level: Optional[Region] = None
        self.chosen_region_with_level: Optional[Region] = None
        self.chosen_tp: Optional[SpecialPoint] = None
        self.chosen_route: Optional[WorldPatrolRoute] = None

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
        horizontal_layout.addLayout(self.get_left_layout())
        horizontal_layout.addSpacing(5)
        horizontal_layout.addLayout(self.get_middle_layout())
        horizontal_layout.addSpacing(5)
        horizontal_layout.addLayout(self.get_right_layout(), 1)

        # 确保 QHBoxLayout 可以伸缩
        horizontal_layout.setSpacing(0)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)

        # 设置伸缩因子，让 QHBoxLayout 占据空间
        main_layout.addLayout(horizontal_layout, stretch=1)

        return content_widget

    def get_left_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()

        self.personal_opt = SwitchSettingCard(icon=FluentIcon.PEOPLE, title='仅个人使用')
        self.personal_opt.setValue(True)
        layout.addWidget(self.personal_opt)

        # 区域行
        region_row = Row()
        Row()

        self.planet_btn = ComboBox()
        self.planet_btn.setPlaceholderText(gt('选择星球'))
        self.planet_btn.currentIndexChanged.connect(self.on_planet_changed)
        region_row.add_widget(self.planet_btn)

        self.region_without_level_opt = ComboBox()
        self.region_without_level_opt.setPlaceholderText(gt('选择区域'))
        self.region_without_level_opt.currentIndexChanged.connect(self.on_region_without_level_selected)
        region_row.add_widget(self.region_without_level_opt)

        self.region_level_opt = ComboBox()
        self.region_level_opt.setPlaceholderText(gt('切换子区域或楼层'))
        self.region_level_opt.currentIndexChanged.connect(self.on_region_level_selected)
        region_row.add_widget(self.region_level_opt)

        region_row.add_stretch(1)
        layout.addWidget(region_row)

        # 传送点行
        tp_row = Row()

        self.tp_opt = ComboBox()
        self.tp_opt.setPlaceholderText(gt('选择传送点'))
        self.tp_opt.currentIndexChanged.connect(self.on_tp_changed)
        tp_row.add_widget(self.tp_opt)

        tp_row.add_stretch(1)
        layout.addWidget(tp_row)

        # 路线行
        route_row = Row()

        self.existed_route_opt = ComboBox()
        self.existed_route_opt.setPlaceholderText(gt('选择路线'))
        self.existed_route_opt.currentIndexChanged.connect(self.on_route_selected)
        route_row.add_widget(self.existed_route_opt)

        route_row.add_stretch(1)
        layout.addWidget(route_row)

        # 保存按钮行
        save_btn_row = Row()

        self.create_btn = PushButton(text=gt('新建'))
        self.create_btn.clicked.connect(self.on_create_clicked)
        save_btn_row.add_widget(self.create_btn)

        self.save_btn = PushButton(text=gt('保存'))
        self.save_btn.clicked.connect(self.on_save_clicked)
        save_btn_row.add_widget(self.save_btn)

        self.delete_btn = ToolButton(FluentIcon.DELETE)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        save_btn_row.add_widget(self.delete_btn)

        self.cancel_btn = PushButton(text=gt('取消'))
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)
        save_btn_row.add_widget(self.cancel_btn)

        save_btn_row.add_stretch(1)
        layout.addWidget(save_btn_row)

        # 运行行
        run_row = Row()

        self.run_btn = PushButton(text=gt('测试运行'))
        self.run_btn.clicked.connect(self.on_run_clicked)
        run_row.add_widget(self.run_btn)

        self.update_by_text_btn = PushButton(text=gt('按文本更新'))
        self.update_by_text_btn.clicked.connect(self.on_update_by_text_clicked)
        run_row.add_widget(self.update_by_text_btn)

        self.back_btn = PushButton(text=gt('回退 -'))
        self.back_btn.clicked.connect(self.on_back_clicked)
        run_row.add_widget(self.back_btn)

        run_row.add_stretch(1)
        layout.addWidget(run_row)

        # 位置相关的按钮行
        pos_row = Row()

        self.cal_move_btn = PushButton(text=gt('截图移动 F6'))
        self.cal_move_btn.clicked.connect(self.on_cal_move_clicked)
        pos_row.add_widget(self.cal_move_btn)

        self.slow_move_btn = PushButton(text=gt('禁疾跑'))
        self.slow_move_btn.clicked.connect(self.on_slow_move_clicked)
        pos_row.add_widget(self.slow_move_btn)

        self.no_pos_move_btn = PushButton(text=gt('模拟按键移动'))
        self.no_pos_move_btn.clicked.connect(self.on_no_pos_move_clicked)
        pos_row.add_widget(self.no_pos_move_btn)

        self.update_pos_btn = PushButton(text=gt('更新位置'))
        self.update_pos_btn.clicked.connect(self.on_update_pos_clicked)
        pos_row.add_widget(self.update_pos_btn)

        pos_row.add_stretch(1)
        layout.addWidget(pos_row)

        # 战斗行
        battle_row = Row()

        self.battle_btn = PushButton(text=gt('战斗'))
        self.battle_btn.clicked.connect(self.on_battle_clicked)
        battle_row.add_widget(self.battle_btn)

        self.cal_battle_btn = PushButton(text=gt('截图战斗 F7'))
        self.cal_battle_btn.clicked.connect(self.on_cal_battle_clicked)
        battle_row.add_widget(self.cal_battle_btn)

        battle_row.add_stretch(1)
        layout.addWidget(battle_row)

        # 破坏物行
        disposable_row = Row()

        self.disposable_btn = PushButton(text=gt('可破坏物'))
        self.disposable_btn.clicked.connect(self.on_disposable_clicked)
        disposable_row.add_widget(self.disposable_btn)

        self.cal_disposable_btn = PushButton(text=gt('截图可破坏物 F8'))
        self.cal_disposable_btn.clicked.connect(self.on_cal_disposable_clicked)
        disposable_row.add_widget(self.cal_disposable_btn)

        disposable_row.add_stretch(1)
        layout.addWidget(disposable_row)

        # 交互行
        interact_row = Row()

        self.interact_text = LineEdit()
        self.interact_text.setPlaceholderText(gt('交互文本'))
        interact_row.add_widget(self.interact_text)

        self.interact_btn = PushButton(text=gt('交互'))
        self.interact_btn.clicked.connect(self.on_interact_clicked)
        interact_row.add_widget(self.interact_btn)

        interact_row.add_stretch(1)
        layout.addWidget(interact_row)

        # 等待行
        wait_row = Row()

        self.wait_type_opt = ComboBox()
        self.wait_type_opt.set_items([
            ConfigItem('等待大世界', operation_const.WAIT_TYPE_IN_WORLD),
            ConfigItem('等待秒数', operation_const.WAIT_TYPE_SECONDS),
        ], operation_const.WAIT_TYPE_IN_WORLD)
        wait_row.add_widget(self.wait_type_opt)

        self.wait_seconds_text = LineEdit()
        self.wait_seconds_text.setPlaceholderText(gt('最长等待秒数'))
        wait_row.add_widget(self.wait_seconds_text)

        self.wait_btn = PushButton(text=gt('等待'))
        self.wait_btn.clicked.connect(self.on_wait_clicked)
        wait_row.add_widget(self.wait_btn)

        wait_row.add_stretch(1)
        layout.addWidget(wait_row)

        # 秘技行
        tech_row = Row()

        self.ban_tech_btn = PushButton(text=gt('禁用秘技'))
        self.ban_tech_btn.clicked.connect(self.on_ban_tech_clicked)
        tech_row.add_widget(self.ban_tech_btn)

        self.allow_tech_btn = PushButton(text=gt('允许秘技'))
        self.allow_tech_btn.clicked.connect(self.on_allow_tech_clicked)
        tech_row.add_widget(self.allow_tech_btn)

        tech_row.add_stretch(1)
        layout.addWidget(tech_row)

        # 玩法交互行
        gameplay_interaction_row = Row()

        self.gameplay_interact_seconds = LineEdit()
        self.gameplay_interact_seconds.setPlaceholderText(gt('按键秒数'))
        gameplay_interaction_row.add_widget(self.gameplay_interact_seconds)

        self.gameplay_interact_btn = PushButton(text=gt('玩法交互'))
        self.gameplay_interact_btn.clicked.connect(self.on_gameplay_interact_clicked)
        gameplay_interaction_row.add_widget(self.gameplay_interact_btn)

        gameplay_interaction_row.add_stretch(1)
        layout.addWidget(gameplay_interaction_row)

        layout.addStretch(1)

        return layout

    def get_middle_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()

        layout.addWidget(SettingCardGroup(gt('路线指令')))
        self.route_text = PlainTextEdit()
        self.route_text.textChanged
        self.route_text.setMinimumWidth(200)
        self.route_text.setMinimumHeight(500)
        layout.addWidget(self.route_text)

        layout.addStretch(1)

        return layout

    def get_right_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()

        layout.addWidget(SettingCardGroup(gt('大地图')))

        self.large_map_image = ImageViewerWidget()
        self.large_map_image.point_clicked.connect(self.on_large_map_clicked)
        layout.addWidget(self.large_map_image, 1)

        return layout

    def on_interface_shown(self) -> None:
        VerticalScrollInterface.on_interface_shown(self)

        self.ctx.map_data.load_map_data()
        self.update_planet_opt()
        self.update_region_without_level_opt()
        self.update_region_with_level_opt()
        self.update_tp_opt()
        self.update_existed_route_opt()
        self.update_display_by_route()

        self.ctx.listen_event(ContextKeyboardEventEnum.PRESS.value, self.on_key_press)

    def on_interface_hidden(self) -> None:
        VerticalScrollInterface.on_interface_hidden(self)
        self.ctx.unlisten_all_event(self)

    def update_display_by_route(self) -> None:
        """
        根据选择配置更新显示
        :return:
        """
        chosen = self.chosen_route is not None

        self.existed_route_opt.setDisabled(chosen)
        self.create_btn.setDisabled(chosen)
        self.save_btn.setDisabled(not chosen)
        self.delete_btn.setDisabled(not chosen)
        self.cancel_btn.setDisabled(not chosen)

        self.run_btn.setDisabled(not chosen)
        self.update_by_text_btn.setDisabled(not chosen)
        self.back_btn.setDisabled(not chosen)

        can_change_tp = world_patrol_route_draw_utils.can_change_tp(self.chosen_route)
        self.planet_btn.setDisabled(not can_change_tp)
        self.region_without_level_opt.setDisabled(not can_change_tp)
        self.tp_opt.setDisabled(not can_change_tp)

        self.cal_move_btn.setDisabled(not chosen)
        self.slow_move_btn.setDisabled(not chosen)
        self.update_pos_btn.setDisabled(not chosen)

        self.battle_btn.setDisabled(not chosen)
        self.cal_battle_btn.setDisabled(not chosen)

        self.disposable_btn.setDisabled(not chosen)
        self.cal_disposable_btn.setDisabled(not chosen)

        self.interact_text.setDisabled(not chosen)
        self.interact_btn.setDisabled(not chosen)

        self.wait_type_opt.setDisabled(not chosen)
        self.wait_seconds_text.setDisabled(not chosen)
        self.wait_btn.setDisabled(not chosen)

        self.route_text.setDisabled(not chosen)
        self.update_large_map_image()

        if chosen:
            self.route_text.setPlainText(self.chosen_route.route_config_str)
        else:
            self.route_text.setPlainText('')

    def update_planet_opt(self) -> None:
        """
        更新星球选项
        :return:
        """
        if self.chosen_planet is None:
            self.chosen_planet = self.ctx.map_data.planet_list[0]

        self.planet_btn.set_items(
            [ConfigItem(i.display_name, i) for i in self.ctx.map_data.planet_list],
            target_value=self.chosen_planet
        )

    def update_region_without_level_opt(self) -> None:
        """
        更新区域选项
        :return:
        """
        region_list: List[Region] = []
        for region in self.ctx.map_data.region_list:
            if self.chosen_planet is not None and region.planet.np_id != self.chosen_planet.np_id:
                continue

            if region.parent is not None:  # 不显示子区域
                continue

            # 多个楼层只选择一个
            existed = False
            for existed_region in region_list:
                if region.pr_id == existed_region.pr_id:
                    existed = True
                    break
            if existed:
                continue

            region_list.append(region)

        if self.chosen_region_without_level is None:
            self.chosen_region_without_level = region_list[0]
        else:
            for r in region_list:
                if r.pr_id == self.chosen_region_without_level.pr_id:
                    self.chosen_region_without_level = r
                    break
                if self.chosen_region_without_level.parent is not None and r.pr_id == self.chosen_region_without_level.parent.pr_id:
                    self.chosen_region_without_level = r
                    break

        self.region_without_level_opt.set_items(
            [ConfigItem(gt(r.cn, 'game'), r) for r in region_list],
            self.chosen_region_without_level
        )

    def update_region_with_level_opt(self) -> None:
        config_list = []
        for r in self.ctx.map_data.planet_2_region.get(self.chosen_planet.np_id, []):
            if (
                    r.pr_id == self.chosen_region_without_level.pr_id
                    or (r.parent is not None and r.parent.pr_id == self.chosen_region_without_level.pr_id)
            ):
             config_list.append(ConfigItem(r.display_name, r))

        if self.chosen_route is not None:
            region, _ = world_patrol_route_draw_utils.get_last_pos(self.ctx, self.chosen_route)
            self.chosen_region_with_level = self.ctx.map_data.region_with_another_floor(
                self.chosen_region_without_level, region.floor)
        elif self.chosen_region_with_level is None or self.chosen_region_with_level.pr_id != self.chosen_region_without_level.pr_id:
            self.chosen_region_with_level = config_list[0].value

        self.region_level_opt.set_items(config_list, self.chosen_region_with_level)
        self.region_level_opt.setVisible(len(config_list) > 1)

    def update_tp_opt(self) -> None:
        if self.chosen_region_without_level is not None or self.chosen_region_with_level is not None:
            region = self.chosen_region_without_level
            if self.chosen_region_with_level is not None and self.chosen_region_with_level.pr_id == region.pr_id:
                region = self.chosen_region_with_level

            config_list = []
            sp_list = self.ctx.map_data.region_2_sp.get(region.pr_id, [])
            for sp in sp_list:
                if not sp.template_id.startswith('mm_tp') and not sp.template_id.startswith('mm_boss'):
                    continue
                config_list.append(ConfigItem(sp.display_name, sp))

            if len(config_list) > 0 and (
                    self.chosen_tp is None
                    or self.chosen_tp.region.pr_id != region.pr_id
            ):
                self.chosen_tp = config_list[0].value
            self.tp_opt.set_items(config_list, self.chosen_tp)
        else:
            self.tp_opt.set_items([])

    def update_existed_route_opt(self) -> None:
        """
        更新路线选项
        :return:
        """
        if self.chosen_route is not None:  # 已经选择了路线
            return

        region = self.chosen_region_without_level
        if self.chosen_region_with_level is not None:
            region = self.chosen_region_with_level
        personal = self.personal_opt.btn.checked
        route_list = self.ctx.world_patrol_route_data.load_all_route(
            target_planet=self.chosen_planet,
            target_region=region,
            include_public=not personal,
            include_personal=personal,
        )

        config_list = []
        for i in route_list:
            config_list.append(ConfigItem(i.display_name, i))

            if self.chosen_route is not None and self.chosen_route.unique_id == i.unique_id:
                self.chosen_route = i

        self.existed_route_opt.set_items(config_list, self.chosen_route)

    def update_large_map_image(self) -> None:
        img_to_show: MatLike | None = None
        if self.chosen_route is None:
            if self.chosen_tp is None:
                region = self.chosen_region_without_level
                if self.chosen_region_with_level is not None:
                    region = self.chosen_region_with_level
                if region is not None:
                    lm_info = self.ctx.map_data.get_large_map_info(region)
                    if lm_info.raw is not None:
                        img_to_show = lm_info.raw.copy()
            else:
                route = WorldPatrolRoute(self.chosen_tp, {
                    "author": [],
                    "route": []
                }, '')
                img_to_show = world_patrol_route_draw_utils.get_route_image(self.ctx, route)
        else:
            img_to_show = world_patrol_route_draw_utils.get_route_image(self.ctx, self.chosen_route)

        self.large_map_image.set_image(img_to_show)

    def on_route_selected(self, idx: int) -> None:
        self.chosen_route = self.existed_route_opt.itemData(idx)
        
        planet = self.chosen_route.tp.region.planet
        self.chosen_planet = planet
        self.update_planet_opt()
        self.chosen_planet = self.planet_btn.currentData()

        region = self.chosen_route.tp.region
        self.chosen_region_without_level = region
        self.update_region_without_level_opt()
        self.chosen_region_without_level = self.region_without_level_opt.currentData()

        region, _ = world_patrol_route_draw_utils.get_last_pos(self.ctx, self.chosen_route)
        self.chosen_region_with_level = region
        self.update_region_with_level_opt()
        self.chosen_region_with_level = self.region_level_opt.currentData()

        self.update_display_by_route()

    def on_create_clicked(self) -> None:
        if self.chosen_route is not None or self.chosen_tp is None:
            return

        self.chosen_route = self.ctx.world_patrol_route_data.create_new_route(self.chosen_tp, 'DoctorReid',
                                                                              personal=self.personal_opt.btn.checked)
        self.update_display_by_route()

    def on_save_clicked(self) -> None:
        if self.chosen_route is None:
            return

        self.ctx.world_patrol_route_data.save_route(self.chosen_route, 'DoctorReid',
                                                    personal=self.personal_opt.btn.checked)
        self.update_existed_route_opt()

    def on_delete_clicked(self):
        if self.chosen_route is None:
            return
        self.chosen_route.delete()

        self.chosen_route = None
        self.existed_route_opt.setCurrentIndex(-1)
        self.update_display_by_route()

    def on_cancel_clicked(self):
        self.chosen_route = None
        self.existed_route_opt.setCurrentIndex(-1)
        self.update_display_by_route()

    def on_planet_changed(self, idx: int) -> None:
        self.chosen_planet = self.planet_btn.itemData(idx)
        self.update_region_without_level_opt()
        self.update_region_with_level_opt()
        self.update_tp_opt()
        self.update_existed_route_opt()
        self.update_large_map_image()

    def on_region_without_level_selected(self, idx: int) -> None:
        self.chosen_region_without_level = self.region_without_level_opt.itemData(idx)
        self.update_region_with_level_opt()
        self.update_tp_opt()
        self.update_existed_route_opt()
        self.update_large_map_image()

    def on_region_level_selected(self, idx: int) -> None:
        self.chosen_region_with_level = self.region_level_opt.itemData(idx)
        if self.chosen_route is not None:
            last_region, _ = world_patrol_route_draw_utils.get_last_pos(self.ctx, self.chosen_route)
            if last_region.pr_id != self.chosen_region_with_level.pr_id:  # 切换了区域
                world_patrol_route_draw_utils.add_sub_region(self.chosen_route, self.chosen_region_with_level)
            self.update_display_by_route()
        else:
            self.update_tp_opt()
            self.update_existed_route_opt()
            self.update_large_map_image()

    def on_tp_changed(self, idx: int) -> None:
        self.chosen_tp = self.tp_opt.currentData()
        self.update_large_map_image()

    def on_image_size_chosen(self) -> None:
        self.update_large_map_image()

    def get_region_level(self) -> Optional[int]:
        """
        获取当前选择的区域楼层
        :return:
        """
        floor: Optional[int] = None
        if self.chosen_region_without_level is not None:
            floor = self.chosen_region_without_level.floor
        if self.chosen_region_with_level is not None:
            floor = self.chosen_region_with_level.floor
        return floor

    def on_large_map_clicked(self, x: int, y: int) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.add_move(self.ctx, self.chosen_route,
                                               x, y, self.get_region_level())
        self.update_display_by_route()

    def on_key_press(self, event: ContextEventItem) -> None:
        key: str = event.data
        if self.chosen_route is None:
            return
        if key == '-':
            self.on_back_clicked()
        elif key == 'f6':
            self.on_cal_move_clicked()
        elif key == 'f7':
            self.on_cal_battle_clicked()
        elif key == 'f8':
            self.on_cal_disposable_clicked()

    def on_run_clicked(self) -> None:
        if self.chosen_route is None:
            return

        whitelist = WorldPatrolWhitelist('draw_route', is_mock=True)
        whitelist.list = [self.chosen_route.unique_id]
        app = WorldPatrolApp(self.ctx, whitelist=whitelist, ignore_record=True)
        app.execute()

    def on_back_clicked(self) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.pop_last(self.chosen_route)
        self.update_display_by_route()

    def on_slow_move_clicked(self) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.mark_last_move_as_slow(self.chosen_route)
        self.update_display_by_route()

    def on_no_pos_move_clicked(self) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.mark_last_move_as_no_pos(self.ctx, self.chosen_route)
        self.update_display_by_route()

    def on_update_pos_clicked(self) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.mark_last_move_as_update(self.chosen_route)
        self.update_display_by_route()

    def on_cal_move_clicked(self) -> None:
        if self.chosen_route is None:
            return

        next_region, next_pos = world_patrol_route_draw_utils.cal_pos_by_screenshot(self.ctx, self.chosen_route)

        if next_pos is None:
            return

        self.chosen_region_with_level = next_region
        world_patrol_route_draw_utils.add_move(self.ctx, self.chosen_route,
                                               next_pos.x, next_pos.y,
                                               self.get_region_level())
        self.update_display_by_route()

    def on_battle_clicked(self) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.add_patrol(self.chosen_route)
        self.update_display_by_route()

    def on_cal_battle_clicked(self) -> None:
        if self.chosen_route is None:
            return

        next_region, next_pos = world_patrol_route_draw_utils.cal_pos_by_screenshot(self.ctx, self.chosen_route)

        if next_pos is None:
            return

        world_patrol_route_draw_utils.add_move(self.ctx, self.chosen_route,
                                               next_pos.x, next_pos.y,
                                               self.get_region_level())
        world_patrol_route_draw_utils.add_patrol(self.chosen_route)
        self.update_display_by_route()

    def on_disposable_clicked(self) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.add_disposable(self.chosen_route)
        self.update_display_by_route()

    def on_cal_disposable_clicked(self) -> None:
        if self.chosen_route is None:
            return

        next_region, next_pos = world_patrol_route_draw_utils.cal_pos_by_screenshot(self.ctx, self.chosen_route)

        if next_pos is None:
            return

        world_patrol_route_draw_utils.add_move(self.ctx, self.chosen_route,
                                               next_pos.x, next_pos.y,
                                               self.get_region_level())
        world_patrol_route_draw_utils.add_disposable(self.chosen_route)
        self.update_display_by_route()

    def on_interact_clicked(self) -> None:
        if self.chosen_route is None:
            return

        interact_word = self.interact_text.text()
        if interact_word is None or len(interact_word) == 0:
            return

        world_patrol_route_draw_utils.add_interact(self.chosen_route, interact_word)
        self.update_display_by_route()

    def on_wait_clicked(self) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.add_wait(
            self.chosen_route,
            self.wait_type_opt.currentData(),
            str_utils.get_positive_digits(self.wait_seconds_text.text(), 10)
        )
        self.update_display_by_route()

    def on_update_by_text_clicked(self) -> None:
        if self.chosen_route is None:
            return

        route_text = self.route_text.toPlainText()
        # 将文本转化成dict
        route_dict = yaml.load(route_text, Loader=yaml.FullLoader)
        self.chosen_route.init_from_yaml_data(route_dict)

        self.update_display_by_route()

    def on_ban_tech_clicked(self) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.add_ban_tech(self.chosen_route)
        self.update_display_by_route()

    def on_allow_tech_clicked(self) -> None:
        if self.chosen_route is None:
            return

        world_patrol_route_draw_utils.add_allow_tech(self.chosen_route)

    def on_gameplay_interact_clicked(self) -> None:
        if self.chosen_route is None:
            return

        seconds = str_utils.get_positive_digits(self.gameplay_interact_seconds.text(), 0)
        world_patrol_route_draw_utils.add_gameplay_interact(self.chosen_route, seconds)

        self.update_display_by_route()