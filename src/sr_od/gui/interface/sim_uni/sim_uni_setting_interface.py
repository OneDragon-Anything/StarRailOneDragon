import os
import shutil
import subprocess

from PySide6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon, SettingCardGroup

from one_dragon.base.config.config_item import ConfigItem
from one_dragon.utils import os_utils
from one_dragon.utils.log_utils import log
from one_dragon_qt.widgets.column import Column
from one_dragon_qt.widgets.setting_card.push_setting_card import PushSettingCard
from one_dragon_qt.widgets.setting_card.switch_setting_card import SwitchSettingCard
from one_dragon_qt.widgets.vertical_scroll_interface import VerticalScrollInterface
from one_dragon_qt.widgets.setting_card.combo_box_setting_card import ComboBoxSettingCard
from one_dragon_qt.widgets.setting_card.text_setting_card import TextSettingCard
from sr_od.application.sim_universe.sim_uni_data import SimUniWorldEnum
from sr_od.context.sr_context import SrContext


class SimUniSettingInterface(VerticalScrollInterface):


    def __init__(self, ctx: SrContext, parent=None):
        self.ctx: SrContext = ctx

        VerticalScrollInterface.__init__(
            self,
            object_name='sr_sim_uni_setting_interface',
            content_widget=None, parent=parent,
            nav_text_cn='每周配置'
        )

    def _on_auto_simulated_universe_settings_clicked(self) -> None:
        """
            启动 Auto_Simulated_Universe
        """
        work_dir = os_utils.get_work_dir()
        plugin_path = os.path.join(work_dir, *['plugins', 'Auto_Simulated_Universe'])
        gui_script = os.path.join(plugin_path, 'gui.py')

        if not os.path.exists(gui_script):
            log.error(f'GUI脚本不存在: {gui_script}')
            return

        command = [self.ctx.python_service.env_config.python_path]
        script_working_directory = plugin_path
        command.append(gui_script)
        try:
            subprocess.Popen(command, cwd=script_working_directory)
            log.info('差分宇宙GUI已启动')
        except Exception as e:
            log.error(f'启动差分宇宙GUI失败: {e}')

    def _on_save_auto_simulated_universe_settings_clicked(self) -> None:
        """
            保存配置: Auto_Simulated_Universe
        """
        work_dir = os_utils.get_work_dir()
        plugin_path = os.path.join(work_dir, *['plugins', 'Auto_Simulated_Universe'])
        plugin_config_file_path = os.path.join(plugin_path, 'info.yml')

        config_file_path = os.path.join(work_dir,
                                        *['config', '%02d' % self.ctx.current_instance_idx, 'sim_universe_plugin.yml'])
        try:
            if not os.path.exists(plugin_config_file_path):
                log.error(f'差分宇宙默认配置文件不存在: {plugin_config_file_path}')
                return
            # 确保目标目录存在
            os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
            shutil.copy(plugin_config_file_path, config_file_path)
            log.info('差分宇宙配置保存成功')
        except Exception as e:
            log.error(f'保存差分宇宙配置失败: {e}')

    def get_content_widget(self) -> QWidget:
        content_widget = Column()

        self.weekly_sim_uni_num_opt = ComboBoxSettingCard(icon=FluentIcon.GAME, title='模拟宇宙')
        content_widget.add_widget(self.weekly_sim_uni_num_opt)

        # region 差分宇宙
        group_x = SettingCardGroup(title='差分宇宙配置')
        content_widget.add_widget(group_x)

        # todo 如何扔进启动器里/自动下载/更新, 以及下载之后放哪
        self.auto_simulated_universe_settings = PushSettingCard(
            icon=FluentIcon.APPLICATION,
            title='配置Auto_Simulated_Universe',
            content='需要先去github下载该项目放到 plugins/Auto_Simulated_Universe文件夹中',
            text='配置'
        )
        self.auto_simulated_universe_settings.clicked.connect(self._on_auto_simulated_universe_settings_clicked)
        group_x.addSettingCard(self.auto_simulated_universe_settings)

        self.only_points_reward = SwitchSettingCard(
            icon=FluentIcon.GAME, title='每周只打满14000', content='勾选此处的话, Auto_Simulated_Universe 的每周次数可以设置成1',
        )
        group_x.addSettingCard(self.only_points_reward)

        self.save_auto_simulated_universe_settings = PushSettingCard(
            icon=FluentIcon.SAVE_AS,
            title='保存配置文件到当前用户目录',
            content='不同用户主要是开怪秘技角色有区别',
            text='保存'
        )
        self.save_auto_simulated_universe_settings.clicked.connect(self._on_save_auto_simulated_universe_settings_clicked)
        group_x.addSettingCard(self.save_auto_simulated_universe_settings)
        # endregion

        # region 模拟宇宙
        challenge_group = SettingCardGroup(title='模拟宇宙配置')
        content_widget.add_widget(challenge_group)
        self.weekly_sim_uni_diff_opt = ComboBoxSettingCard(icon=FluentIcon.GAME, title='难度')
        challenge_group.addSettingCard(self.weekly_sim_uni_diff_opt)
        self.weekly_plan_times_opt = TextSettingCard(icon=FluentIcon.CALENDAR, title='每周精英次数')
        challenge_group.addSettingCard(self.weekly_plan_times_opt)
        self.daily_plan_times_opt = TextSettingCard(icon=FluentIcon.CALENDAR, title='每日精英次数')
        challenge_group.addSettingCard(self.daily_plan_times_opt)

        self.challenge_opt_list = {}

        for i in SimUniWorldEnum:
            if i.name in ['WORLD_00', 'WORLD_01', 'WORLD_02', 'WORLD_X']:
                continue

            challenge_opt = ComboBoxSettingCard(icon=FluentIcon.GAME, title=i.value.name)
            challenge_group.addSettingCard(challenge_opt)

            self.challenge_opt_list[i.value.idx] = challenge_opt

        content_widget.add_stretch(1)
        return content_widget
        # endregion

    def on_interface_shown(self) -> None:
        VerticalScrollInterface.on_interface_shown(self)

        sim_uni_num_opts = [
            ConfigItem(label=i.value.name, value=i.name)
            for i in SimUniWorldEnum
            if i.name not in ['WORLD_00', 'WORLD_01', 'WORLD_02']
        ]
        self.weekly_sim_uni_num_opt.set_options_by_list(sim_uni_num_opts)
        self.weekly_sim_uni_num_opt.init_with_adapter(self.ctx.sim_uni_config.weekly_uni_num_adapter)

        diff_opts = [ConfigItem(label='默认难度', value=0)]
        for i in SimUniWorldEnum:
            if i.name == self.ctx.sim_uni_config.weekly_uni_num:
                for j in range(1, i.value.max_diff + 1):
                    diff_opts.append(ConfigItem(label=str(j), value=j))
        self.weekly_sim_uni_diff_opt.set_options_by_list(diff_opts)
        self.weekly_sim_uni_diff_opt.init_with_adapter(self.ctx.sim_uni_config.weekly_uni_diff_adapter)

        self.only_points_reward.init_with_adapter(self.ctx.sim_uni_config.only_points_reward_adapter)
        self.weekly_plan_times_opt.init_with_adapter(self.ctx.sim_uni_config.elite_weekly_times_adapter)
        self.daily_plan_times_opt.init_with_adapter(self.ctx.sim_uni_config.elite_daily_times_adapter)

        for idx, opt in self.challenge_opt_list.items():
            opt.set_options_by_list([
                ConfigItem(label=i.name, value='%02d' % i.idx)
                for i in self.ctx.sim_uni_challenge_config_data.load_all_challenge_config()
            ])

            opt.init_with_adapter(self.ctx.sim_uni_config.get_challenge_config_adapter(idx))
