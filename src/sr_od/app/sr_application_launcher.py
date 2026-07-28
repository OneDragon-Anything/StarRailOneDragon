"""向后兼容入口。

老版本 ``OneDragon-Launcher.exe`` 硬编码调用 ``sr_od.app.sr_application_launcher``，
实际逻辑已迁移到 :mod:`sr_od.application.sr_application_launcher`。
本模块不写任何逻辑，仅做转发，保证旧 exe 仍可启动。
"""
from sr_od.application.sr_application_launcher import (  # noqa: F401
    SrApplicationLauncher,
    main,
)

if __name__ == '__main__':
    main()
