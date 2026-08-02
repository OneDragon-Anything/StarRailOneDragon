import os
import subprocess
import winreg

from one_dragon.base.operation.operation import Operation
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from one_dragon.utils.reg_utils import RegistryPatch
from sr_od.context.sr_context import SrContext

# 星穹铁道会忽略 -screen-width/-screen-height/-screen-fullscreen 命令行参数
# 需要通过注册表设置分辨率和显示模式
_CN_SUBKEY = r'Software\miHoYo\崩坏：星穹铁道'
_INTL_SUBKEY = r'Software\Cognosphere\Star Rail'
_SUPPORTED_REGIONS = frozenset({'cn', 'us', 'eu', 'asia', 'twhkmo'})

_REG_GRAPHICS_SETTINGS = 'GraphicsSettings_PCResolution_h431323223'
_REG_SCREEN_WIDTH = 'Screenmanager Resolution Width_h182942802'
_REG_SCREEN_HEIGHT = 'Screenmanager Resolution Height_h2627697771'
_REG_FULLSCREEN_MODE = 'Screenmanager Fullscreen mode_h3630240806'

# 模块级补丁实例，供 close_game 时恢复
_resolution_patch: RegistryPatch | None = None


def restore_resolution_registry() -> None:
    """恢复注册表中的分辨率设置为打开游戏前的值"""
    if _resolution_patch is not None:
        _resolution_patch.restore()


class OpenGame(Operation):

    def __init__(self, ctx: SrContext):
        self.ctx: SrContext = ctx
        Operation.__init__(self, ctx, op_name=gt('打开游戏'),
                           need_check_game_win=False)

    def _set_resolution_registry(self, width: int, height: int, full_screen: str) -> None:
        """通过注册表设置游戏分辨率和显示模式
        星穹铁道游戏内设置会覆盖命令行的 -screen-width/-screen-height/-screen-fullscreen 参数，需要通过注册表来设置。
        """
        region = self.ctx.game_account_config.game_region
        if region not in _SUPPORTED_REGIONS:
            log.warning('不支持通过注册表设置分辨率的区服: %s，跳过', region)
            return
        subkey = _CN_SUBKEY if region == 'cn' else _INTL_SUBKEY

        # 显示模式转换: config '0'(窗口化) -> registry 3, config '1'(全屏) -> registry 1
        fullscreen_mode = 1 if full_screen == '1' else 3
        is_full_screen = fullscreen_mode == 1

        json_str = f'{{"width":{width},"height":{height},"isFullScreen":{str(is_full_screen).lower()}}}\0'
        values: dict[str, tuple[bytes | int, int]] = {
            _REG_GRAPHICS_SETTINGS: (json_str.encode('ascii'), winreg.REG_BINARY),
            _REG_SCREEN_WIDTH: (width, winreg.REG_DWORD),
            _REG_SCREEN_HEIGHT: (height, winreg.REG_DWORD),
            _REG_FULLSCREEN_MODE: (fullscreen_mode, winreg.REG_DWORD),
        }

        global _resolution_patch
        if _resolution_patch is not None:
            _resolution_patch.restore()

        patch = RegistryPatch(subkey)
        if not patch.backup_and_set(values):
            log.warning('注册表分辨率设置失败，将继续使用当前设置')
            return
        _resolution_patch = patch
        log.info('注册表暂更: 窗口尺寸=%dx%d 显示模式=%s', width, height, '全屏' if is_full_screen else '窗口化')

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
            screen_width = int(screen_size.split('x')[0])
            screen_height = int(screen_size.split('x')[1])
            full_screen = self.ctx.game_config.full_screen

            # 通过注册表设置分辨率和显示模式（命令行参数对星穹铁道无效）
            self._set_resolution_registry(screen_width, screen_height, full_screen)

            popup_window = '-popupwindow' if self.ctx.game_config.popup_window else ''
            monitor = self.ctx.game_config.monitor
            log.info('无边框窗口: %s 显示器: %s', '启用' if self.ctx.game_config.popup_window else '禁用', monitor)
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
