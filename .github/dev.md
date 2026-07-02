# 1.开发环境

开发环境与常用命令见根目录 [AGENTS.md](../AGENTS.md)。要点：

- Python 3.11.9；包管理用 uv。
- 安装依赖（含 ruff/pytest/pyright 等 dev 工具）：`uv sync --group dev`
- 运行：`uv run python src/sr_od/gui/sr_full_app.py`（需 `PYTHONPATH=src`，详见 AGENTS.md）
- Lint：`uv run ruff check src/<你修改的文件>.py`
- 测试：`uv run pytest sr-od-test/`
- 也可用 `debug.bat` 交互式调试。

# 2.打包

进入 deploy 文件夹

## 2.1.安装器

生成spec文件

```shell
pyinstaller --onefile --windowed --uac-admin --icon="../assets/ui/logo.ico" ../src/sr_od/gui/sr_installer_app.py -n "OneDragon-Installer"
```

spec打包

```shell
pyinstaller "OneDragon-Installer.spec"
```

## 2.2.完整运行器

生成spec文件

```shell
pyinstaller --onefile --uac-admin --icon="../assets/ui/full_app.ico" ../src/sr_od/gui/sr_full_launcher.py -n "OneDragon-Launcher"
```

spec打包
```shell
pyinstaller "OneDragon-Launcher.spec"
```

## 2.3.一条龙运行器

生成spec文件

```shell
pyinstaller --onefile --uac-admin --icon="../assets/ui/scheduler_app.ico" ../src/sr_od/gui/sr_scheduler_launcher.py -n "OneDragon Scheduler"
```

spec打包
```shell
pyinstaller "OneDragon Scheduler.spec"
```
