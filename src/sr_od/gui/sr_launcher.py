from one_dragon.devtools import python_launcher
from one_dragon.launcher.exe_launcher import ExeLauncher
from one_dragon.version import __version__


class SrLauncher(ExeLauncher):
    """星铁启动器"""

    def __init__(self):
        ExeLauncher.__init__(self, "星穹铁道 一条龙 启动器", __version__)

    def run_onedragon_mode(self, launch_args) -> None:
        python_launcher.run_python(["sr_od", "app", "sr_application_launcher.py"], no_windows=False, args=launch_args)

    def run_gui_mode(self) -> None:
        python_launcher.run_python(["sr_od", "gui", "sr_full_app.py"], no_windows=True)


if __name__ == '__main__':
    launcher = SrLauncher()
    launcher.run()
