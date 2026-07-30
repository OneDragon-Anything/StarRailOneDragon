import ctypes
import sys
from pathlib import Path

from one_dragon.launcher.runtime_launcher import RuntimeLauncher
from one_dragon.version import __version__

_SRC_DIR = Path(sys.executable).parent / "src"
if not _SRC_DIR.is_dir():
    ctypes.windll.user32.MessageBoxW(
        None,
        f"缺少 src 目录：\n{_SRC_DIR}\n\n请重新解压完整的 WithRuntime 压缩包。",
        "OneDragon 集成启动器",
        0x10,
    )
    sys.exit(1)


class SrLauncher(RuntimeLauncher):
    """星穹铁道启动器"""

    def __init__(self) -> None:
        RuntimeLauncher.__init__(self, "星穹铁道 一条龙 启动器", __version__)

    def _do_run_onedragon(self, launch_args: list[str]) -> None:
        from sr_od.application.sr_application_launcher import main
        main(launch_args)

    def _do_run_gui(self) -> None:
        from sr_od.gui.sr_full_app import main
        main()


if __name__ == '__main__':
    launcher = SrLauncher()
    launcher.run()
