import os
from enum import Enum

from one_dragon.base.config.config_item import ConfigItem, get_config_item_from_enum
from one_dragon.base.config.yaml_config import YamlConfig


class CheckDoneMethods(Enum):

    GAME_CLOSED = ConfigItem(label='游戏被关闭', value='game_closed', desc='游戏被关闭时 认为任务完成')
    SCRIPT_CLOSED = ConfigItem(label='脚本被关闭', value='script_closed', desc='脚本被关闭时 认为任务完成')
    GAME_OR_SCRIPT_CLOSED = ConfigItem(label='游戏或脚本被关闭', value='game_or_script_closed', desc='游戏或脚本被关闭时 认为任务完成')


class ScriptProcessName(Enum):

    ONE_DRAGON_LAUNCHER = ConfigItem(label='一条龙', value='pythonw.exe')
    BGI = ConfigItem(label='BetterGI', value='BetterGI.exe')
    March7th = ConfigItem(label='三月七小助手', value='March7th Assistant.exe')


class GameProcessName(Enum):

    GENSHIN_IMPACT_CN = ConfigItem(label='原神', value='YuanShen.exe')
    GENSHIN_IMPACT_GLOBAL = ConfigItem(label='原神（国际服）', value='GenshinImpact.exe')
    STAR_RAIL_CN = ConfigItem(label='崩坏：星穹铁道', value='StarRail.exe')
    ZZZ_CN = ConfigItem(label='绝区零', value='ZenlessZoneZero.exe')


class ScriptConfig:

    def __init__(self,
                 script_path: str,
                 script_process_name: str,
                 game_process_name: str,
                 run_timeout_seconds: int,
                 check_done: str,
                 stop_chain_when_pause_pressed: bool,
                 kill_script_after_done: bool,
                 kill_game_after_done: bool,
                 script_arguments: str,
                 notify_start: bool,
                 notify_done: bool,
                 script_working_directory: str = None,
                 ):

        self.idx: int = 0  # 下标 由外面控制
        self.script_path: str = script_path  # 运行脚本的路径
        self.script_process_name: str = script_process_name  # 运行脚本的真实进程名称
        self.game_process_name: str = game_process_name  # 运行游戏的真实进程名称
        self.run_timeout_seconds: int = run_timeout_seconds  # 脚本超时时间
        self.check_done: str = check_done  # 怎么判断脚本已经运行完毕
        self.stop_chain_when_pause_pressed: bool = stop_chain_when_pause_pressed  # 是否在按下暂停键时关闭链式调用的脚本
        self.kill_script_after_done: bool = kill_script_after_done  # 是否在运行完毕之后关闭脚本
        self.kill_game_after_done: bool = kill_game_after_done  # 是否在运行完毕之后关闭游戏
        self.script_arguments: str = script_arguments  # 运行脚本的附加参数
        self.notify_start: bool = notify_start  # 是否在脚本开始时通知
        self.notify_done: bool = notify_done  # 是否在脚本完成时通知
        self.script_working_directory: str = script_working_directory  # 运行脚本的工作路径

    @property
    def script_display_name(self) -> str:
        return os.path.basename(self.script_path)

    @property
    def game_display_name(self) -> str:
        game_process_enum = [i for i in GameProcessName if i.value.value == self.game_process_name]
        return game_process_enum[0].value.label if len(game_process_enum) > 0 else self.game_process_name

    @property
    def check_done_display_name(self) -> str:
        config = get_config_item_from_enum(CheckDoneMethods, self.check_done)
        if config is not None:
            return config.value
        else:
            return ''

    @property
    def invalid_message(self) -> str:
        """
        当前配置的非法信息
        """
        if self.script_path is None or len(self.script_path) == 0:
            return '脚本路径为空'
        elif not os.path.exists(self.script_path):
            return f'脚本路径不存在 {self.script_path}'
        elif get_config_item_from_enum(CheckDoneMethods, self.check_done) is None:
            return f'检查完成方式非法 {self.check_done}'
        elif (
                (self.check_done == CheckDoneMethods.GAME_OR_SCRIPT_CLOSED.value.value
                 or self.check_done == CheckDoneMethods.GAME_CLOSED.value.value
                 or self.kill_game_after_done)
              and (self.game_process_name is None or len(self.game_process_name) == 0)
        ):
            return '游戏进程名称为空'
        elif (
                (self.check_done == CheckDoneMethods.GAME_OR_SCRIPT_CLOSED.value.value
                 or self.check_done == CheckDoneMethods.SCRIPT_CLOSED.value.value
                 or self.kill_script_after_done)
                and (self.script_process_name is None or len(self.script_process_name) == 0)
        ):
            return '脚本进程名称为空'
        elif self.run_timeout_seconds <= 0:
            return '运行超时时间必须大于0'


class ScriptChainConfig(YamlConfig):

    def __init__(self, module_name: str, is_mock: bool = False):
        YamlConfig.__init__(
            self,
            module_name,
            sub_dir=['script_chain'],
            is_mock=is_mock, sample=False, copy_from_sample=False,
        )

        self.script_list: list[ScriptConfig] = [
            ScriptConfig(
                script_path=i.get('script_path', ''),
                script_process_name=i.get('script_process_name', ''),
                game_process_name=i.get('game_process_name', ''),
                run_timeout_seconds=i.get('run_timeout_seconds', 3600),
                check_done=i.get('check_done', ''),
                kill_script_after_done=i.get('kill_script_after_done', True),
                kill_game_after_done=i.get('kill_game_after_done', True),
                script_arguments=i.get('script_arguments', ''),
                notify_start=i.get('notify_start', True),
                notify_done=i.get('notify_done', True),
            )
            for i in self.get('script_list', [])
        ]
        self.init_idx()

    def init_idx(self) -> None:
        """
        初始化下标
        :return:
        """
        for i in range(len(self.script_list)):
            self.script_list[i].idx = i

    def save(self):
        self.data = {
            'script_list': [
                {
                    'script_path': i.script_path,
                    'script_process_name': i.script_process_name,
                    'game_process_name': i.game_process_name,
                    'run_timeout_seconds': i.run_timeout_seconds,
                    'check_done': i.check_done,
                    'kill_script_after_done': i.kill_script_after_done,
                    'kill_game_after_done': i.kill_game_after_done,
                    'script_arguments': i.script_arguments,
                    'notify_start': i.notify_start,
                    'notify_done': i.notify_done,
                }
                for i in self.script_list
           ]
        }
        YamlConfig.save(self)

    def add_one(self) -> ScriptConfig:
        """
        新增一个配置 并返回
        :return:
        """
        new_config = ScriptConfig(
            script_path='',
            script_process_name='',
            game_process_name='',
            run_timeout_seconds=3600,
            check_done=CheckDoneMethods.GAME_OR_SCRIPT_CLOSED.value.value,
            kill_script_after_done=True,
            kill_game_after_done=True,
            script_arguments='',
            notify_start=True,
            notify_done=True,
        )
        self.script_list.append(new_config)
        self.init_idx()
        self.save()
        return new_config

    def delete_one(self, index: int) -> None:
        """
        删除一个配置
        :param index:
        :return:
        """
        if index < 0 or index >= len(self.script_list):
            return
        del self.script_list[index]
        self.init_idx()
        self.save()

    def move_up(self, index: int) -> None:
        """
        向上移动一个配置
        :param index:
        :return:
        """
        if index <= 0 or index >= len(self.script_list):
            return
        self.script_list[index], self.script_list[index - 1] = self.script_list[index - 1], self.script_list[index]
        self.init_idx()
        self.save()

    def update_config(self, config: ScriptConfig) -> None:
        """
        更新一个配置
        :param config:
        :return:
        """
        if config.idx < 0 or config.idx >= len(self.script_list):
            return

        self.script_list[config.idx] = config
        self.init_idx()
        self.save()
