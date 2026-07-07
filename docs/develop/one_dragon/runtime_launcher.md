# 集成启动器（RuntimeLauncher）详细设计文档

## 概述

集成启动器是一种将 Python 运行时直接嵌入发行包的启动方案。与原始启动器（需要用户单独安装 Python 和 uv）不同，集成启动器解压即可运行，适合首次安装或不熟悉 Python 环境的用户。

## 整体架构

### 两种启动器对比

| 特性 | 原始启动器 | 集成启动器 |
|------|-----------|-----------|
| 运行方式 | exe → 子进程调用系统 Python | exe 内嵌 Python，直接 import 运行 |
| Python 环境 | 用户自行安装 | 打包在 `.runtime/` 目录中 |
| 代码加载 | 通过系统 Python 执行 `src/` | 通过运行时钩子注入 `src/` 到 `sys.path` |
| 更新机制 | 只更新源码 | 源码自动更新 + 清单兼容性检查 |
| 发行体积 | exe 很小，虚拟环境约 1GB | exe + .runtime 约 100 MB |

### 继承关系

```
LauncherBase          → 基础参数解析、run() 入口
  └── ExeLauncher     → 版本显示、参数构建、pyuac 管理员提升
        └── RuntimeLauncher  → 集成启动器基类：代码同步、控制台隐藏、致命错误弹窗、模板方法
              └── SrLauncher  → 星穹铁道专用入口（导入 sr_full_app.py / sr_application_launcher.py）
```

- `LauncherBase` 和 `ExeLauncher` 位于 `src/one_dragon/launcher/`，是框架通用代码
- `RuntimeLauncher` 也在框架层，提供集成启动器的通用能力
- `SrLauncher` 在 `src/sr_od/win_exe/runtime_launcher.py`，是具体游戏的入口

## 打包机制

### PyInstaller 目录模式

集成启动器使用 PyInstaller 的目录模式（非单文件），运行时文件存放在 `.runtime/` 子目录中。最终目录结构如下：

```
安装目录/
├── OneDragon-RuntimeLauncher.exe    ← 启动入口
├── .runtime/                        ← Python 运行时 + 冻结模块
│   ├── module_manifest.py           ← 外部依赖清单
│   ├── config/project.yml           ← 项目配置
│   └── ...                          ← Python DLL、so、pyd 等
└── src/                             ← 源代码目录（通过 git 同步）
    ├── one_dragon/
    ├── one_dragon_qt/
    ├── sr_od/
    └── onnxocr/
```

### 最小打包策略

为了控制体积和避免冻结代码与 src/ 中的源码冲突，spec 文件只保留极少量必须冻结的模块，其余全部排除。

打包保留的模块（KEEP_TREES）：
- `one_dragon.launcher` — 启动器自身需要的代码
- `one_dragon.version` — 版本号

这些模块及其所有父包和子模块会被保留，其余 `one_dragon.*`、`sr_od.*` 等全部排除。

### 运行时钩子与路径注入

`hook_path_inject.py` 是 PyInstaller 的 runtime_hook，在主脚本执行前运行，完成两件事：

1. 将 `src/` 加入 `sys.path` — 使 `sr_od`、`one_dragon_qt` 等未冻结的顶层包可以被导入
2. 将 `src/one_dragon` 追加到冻结 `one_dragon` 包的 `__path__` — 使 `one_dragon.envs`、`one_dragon.utils` 等未冻结子模块能被找到

第 2 步之所以必要，是因为 `one_dragon` 这个包同时存在于两个位置：`.runtime/` 中有冻结的 `one_dragon.launcher` 和 `one_dragon.version`，`src/one_dragon/` 中有其余子模块。Python 的包系统需要 `__path__` 同时包含两个路径才能正确解析所有子模块。

**维护要点**：如果 KEEP_TREES 中新增了不同的顶层包前缀（比如某天需要冻结 `one_dragon_qt.xxx`），则 `hook_path_inject.py` 中也需要对应追加该包的 `__path__` 扩展。两个文件中都有 NOTE 注释标注了这个耦合关系。

## 模块清单机制

### 问题背景

集成启动器的二进制依赖（pygit2、PySide6 等）打包在 `.runtime/` 中，不会随代码更新而变化。如果代码更新后 `import` 了一个新的外部库，而 `.runtime/` 中没有该库，就会导致 `ModuleNotFoundError`。

### 解决方案

`module_manifest.py` 文件记录了打包时所有源码文件的外部依赖 import 语句。这个文件既打包进 `.runtime/`（作为本地清单），又提交到 git 仓库（作为远程清单）。

代码更新时，`GitService._check_manifest_compatible()` 对比本地清单和目标 commit 的清单：
- 相同 → 兼容，允许更新
- 不同 → 不兼容，阻止更新并提示用户下载新版集成启动器

### 清单路径配置

远程清单的路径不是硬编码的，而是从目标 commit 的 `config/project.yml` 中的 `manifest_path` 字段读取。这样即使清单文件改名或移动位置，只要 `project.yml` 正确指向它就能找到。

### 生成时机

- **打包时**：spec 文件通过 `importlib` 动态加载 `generate_module_manifest.py`，在 Analysis 阶段生成 `module_manifest.py`
- **本地打包**：SR 无打包/发布 CI（有 `test-check.yml` 测试 CI 跑 pytest，无自动打包）；开发者在 `deploy/` 跑 `build_full.bat`（内部调 `generate_module_manifest.py` 生成清单）后手动发布

## 代码同步流程

集成启动器的 `_sync_code()` 方法在每次启动时执行：

1. 记录当前 `sys.modules` 快照（用于后续清理）
2. 延迟导入 `EnvConfig`、`GitService`、`ProjectConfig`（来自 `src/`）
3. 判断是否首次运行（检查 `.git` 目录是否存在）
4. 首次运行 → 克隆仓库；非首次 → 根据 `auto_update_code` 配置决定是否更新
5. 成功后清除同步过程中加载的模块（`del sys.modules[...]`），调用 `importlib.invalidate_caches()`
6. 首次克隆失败 → 退出；后续更新失败 → 打日志继续运行

步骤 5 的模块清理确保了主程序后续导入的是更新后的代码，而非同步过程中缓存的旧版本。

## 错误处理

### 集成启动器的 try/except

`RuntimeLauncher.run_gui_mode()` 和 `run_onedragon_mode()` 将整个执行流程（包括 `_sync_code()` 和子类的 `_do_run_gui()` / `_do_run_onedragon()`）包裹在 try/except 中。任何未捕获的异常都会通过 `_show_fatal_error()` 弹出 Windows MessageBox 并退出，避免闪退后用户看不到错误信息。

### sr_full_app.py 的模块级 try

`sr_full_app.py` 顶层有一个 try/except 包裹所有 import 语句。这是因为 import 阶段的错误（如依赖缺失）发生在 `main()` 被调用之前，集成启动器的 try/except 也能捕获到，但模块级 try 提供了更精确的错误信息。

### SrLauncher 的 src 目录检查

`SrLauncher` 的入口文件在模块级检查 `src/` 目录是否存在。如果用户只解压了 exe 和 .runtime 而遗漏了 src/，会立即弹出 MessageBox 提示，避免后续出现难以理解的 ImportError。

## 发行产物

`build_full.bat` 生成以下产物（在 `deploy/dist/`）：

| 文件 | 内容 | 用途 |
|------|------|------|
| `StarRailOneDragon.zip` | 完整包：Installer + Launcher + RuntimeLauncher + .runtime + config/assets | 首次部署 |
| `StarRailOneDragon-Launcher.zip` | 瘦 Launcher.exe | 就地升级瘦 launcher |
| `StarRailOneDragon-RuntimeLauncher.zip` | RuntimeLauncher.exe + .runtime（不含 src） | 就地升级 runtime |

> 完整包**不含 src/**——首次部署需先跑 Installer（装 uv + clone src），或手动 git clone；RuntimeLauncher 首次启动要求 exe 同级已有 `src/`（顶层模块检查，缺失弹窗报错）。

## 启动器下载卡（UI）

`LauncherDownloadCard` 提供了一个类型下拉框，让用户在「原始启动器」和「集成启动器」之间切换。切换时会：

1. 断开旧版本检查器的信号连接（防止竞态覆盖）
2. 创建新的版本检查器（指向对应的 exe 文件）
3. 重置版本状态并触发重新检查

下载时的备份/回滚机制：
- 下载前将当前 exe 重命名为 `.bak`（集成启动器还会重命名 `.runtime` 为 `.runtime.bak`）
- 下载成功 → 删除备份
- 下载失败 → 回滚备份
