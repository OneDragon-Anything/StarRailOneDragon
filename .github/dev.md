# 1.开发环境

## 1.1.Python

推荐使用 [3.11.9](https://www.python.org/downloads/release/python-3119/)

## 1.2.虚拟环境

普通运行

```shell
pip install -r requirements-dev.txt
```

开发额外

```shell
pip install -r requirements-dev-ext.txt
```

生成最终使用

```shell
pip-compile --annotation-style=line --index-url=https://pypi.tuna.tsinghua.edu.cn/simple --output-file=requirements-prod.txt requirements-dev.txt
```

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
