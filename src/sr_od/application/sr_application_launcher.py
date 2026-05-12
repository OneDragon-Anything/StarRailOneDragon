import sys

from one_dragon.launcher.application_launcher import ApplicationLauncher
from sr_od.context.sr_context import SrContext


class SrApplicationLauncher(ApplicationLauncher):
    """星铁应用启动器"""

    def __init__(self):
        ApplicationLauncher.__init__(self)

    def create_context(self):
        return SrContext()


def main(args: list[str] | None = None) -> None:
    if args is not None:
        sys.argv = [sys.argv[0]] + args
    launcher = SrApplicationLauncher()
    launcher.run()


if __name__ == '__main__':
    main()
