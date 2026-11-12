import os
import subprocess

from one_dragon.base.operation.operation import Operation
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext


class OpenGame(Operation):
    """启动游戏客户端进程(按账户管理配置的路径与启动参数),不进行登录。
    起点:任意(游戏未运行);终点:游戏窗口出现,停在登录相关画面(未登录态)。
    """

    def __init__(self, ctx: SrContext):
        """
        :param ctx: 上下文
        """
        self.ctx: SrContext = ctx
        Operation.__init__(self, ctx, op_name=gt('打开游戏'),
                           need_check_game_win=False)

    @operation_node(name='打开游戏', is_start_node=True, screenshot_before_round=False)
    def open_game(self) -> OperationRoundResult:
        """
        打开游戏
        :return:
        """
        if self.ctx.game_account_config.game_path == '':
            return self.round_fail('未配置游戏路径，请前往 [ 账户管理 ] -> [ 游戏路径 ] 手动设置')
        full_path = self.ctx.game_account_config.game_path
        # 获取文件夹路径
        dir_path = os.path.dirname(full_path)
        exe_name = os.path.basename(full_path)
        log.info('尝试自动启动游戏 路径为 %s', full_path)
        command = f'cmd /c "start "" /d "{dir_path}" "{exe_name}"'
        if self.ctx.game_config.launch_argument:
            screen_size = self.ctx.game_config.screen_size
            screen_width = screen_size.split('x')[0]
            screen_height = screen_size.split('x')[1]
            full_screen = self.ctx.game_config.full_screen
            popup_window = '-popupwindow' if self.ctx.game_config.popup_window else ''
            monitor = self.ctx.game_config.monitor
            arguement = f'{self.ctx.game_config.launch_argument_advance} -screen-width {screen_width} -screen-height {screen_height} -screen-fullscreen {full_screen} {popup_window} -monitor {monitor}'
            command = f'{command} {arguement}'
        command = f'{command} & exit"'
        log.info('命令行指令 %s', command)

        # 若启动器使用了进程组管理，使用 CREATE_BREAKAWAY_FROM_JOB 可使子进程从 job object 中逃离，
        # 避免 OneDragon-Launcher.exe 退出后游戏被一并杀死。
        subprocess.Popen(
            command,
            creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB
        )
        return self.round_success(wait=5)
