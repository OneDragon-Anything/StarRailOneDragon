# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 策略发现管理器(StrategyManager + StrategyInfo)。

对标 ``ApplicationFactoryManager`` 的「约定式文件扫描 + BUILTIN/THIRD_PARTY 双源 + 元数据 +
去重 + 热重载」,但**省掉 factory 间接层**(策略比应用简单:无 config/run_record 机制,``cls()``
即可实例化)。复用 ``one_dragon.utils.plugin_module_loader``。

两个来源(同 app 插件):
- ``BUILTIN``:``src/sr_od/application/currency_war/strategies/``(内置策略,如 ``default_strategy.py``)。
- ``THIRD_PARTY``:项目根 ``plugins/currency_war_strategies/<子目录>/``(参赛者放这;**不能直接放根**,
  须在子目录里 —— 同 app 插件规则)。

约定(比 app 插件更轻):
- 扫描目录下所有 ``.py``(**无后缀过滤** —— 区别 app 插件的 ``*_factory.py`` rglob),找 ``CwStrategy``
  的子类(``__module__`` 匹配本文件,排除导入的基类 + ``_abstract=True`` 中间辅助 ABC)。
- **一个文件只注册一个策略**(多真实策略取首个);``STRATEGY_ID`` 唯一性强校验(重复报错,指明首注册位)。
- 无 ``_factory.py`` / ``_const.py`` 配对(元数据全类属性,§11.3.1)→ 实例化 ``cls()``(无参)。

设计见 ``docs/develop/currency_war/strategy/11_strategy_plugin.md`` §11.5;决策见 。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from one_dragon.base.operation.application.plugin_info import PluginSource
from one_dragon.utils.log_utils import log
from one_dragon.utils.plugin_module_loader import (
    ensure_sys_path,
    import_module_from_file,
    resolve_module_name,
)
from sr_od.application.currency_war.cw_strategy import CwStrategy

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


@dataclass
class StrategyInfo:
    """一个策略的元数据(GUI 下拉展示 + 调试定位;借鉴 ``PluginInfo`` 但加 ``file_path``)。"""
    strategy_id: str                                   # 唯一 id(去重键)
    name: str                                          # GUI 显示名(STRATEGY_NAME)
    author: str = ""                                   # 参赛者/作者
    version: str = "0.1"                               # 语义化版本
    description: str = ""                              # 一句话描述打法
    source: PluginSource = PluginSource.BUILTIN        # BUILTIN / THIRD_PARTY(扫描时定,非用户控)
    module_name: str = ""                              # dotted 模块名(调试/import 用)
    plugin_dir: Path | None = None                     # 策略所在目录(GUI 展示来源)
    file_path: Path | None = None                      # 策略文件路径(调试定位;PluginInfo 无,本设计新增)

    @property
    def is_third_party(self) -> bool:
        """是否第三方策略。"""
        return self.source == PluginSource.THIRD_PARTY


class StrategyManager:
    """货币战争策略发现管理器(扫描 / 加载 / 刷新 / 实例化;/§11.5)。

    构造签名对标 ``ApplicationFactoryManager``(收 ctx + plugin_dirs 元组列表),但发现逻辑为策略
    定制(无 ``_factory``/``_const`` 配对、无 default group/priority)。
    """

    def __init__(self, ctx: SrContext, plugin_dirs: list[tuple[Path, PluginSource]]):
        """初始化。

        Args:
            ctx: SrContext(plugin_dirs 来源 + 未来 GUI 共用)。
            plugin_dirs: 策略目录列表,每项 (path, source)(来源 ``SrContext.currency_war_strategy_plugin_dirs``)。
        """
        self.ctx: SrContext = ctx
        self._plugin_dirs: list[tuple[Path, PluginSource]] = plugin_dirs
        self._infos: dict[str, StrategyInfo] = {}        # {strategy_id: StrategyInfo}
        self._classes: dict[str, type[CwStrategy]] = {}  # {strategy_id: 类}(实例化用,避免重复扫)
        self._scan_failures: list[tuple[Path, str]] = []  # 最近一次扫描失败记录
        self._added_sys_paths: set[str] = set()          # 跟踪已加到 sys.path 的路径(THIRD_PARTY 相对导入)
        self._discovered: bool = False

    @property
    def plugin_dirs(self) -> list[tuple[Path, PluginSource]]:
        """策略目录列表。"""
        return self._plugin_dirs

    @property
    def strategies(self) -> list[StrategyInfo]:
        """所有已发现策略(GUI 下拉用)。未发现则先 discover。"""
        self._ensure_discovered()
        return list(self._infos.values())

    @property
    def scan_failures(self) -> list[tuple[Path, str]]:
        """最近一次扫描失败记录。"""
        return self._scan_failures

    def _ensure_discovered(self) -> None:
        if not self._discovered:
            self.discover()

    def discover(self, reload_modules: bool = False) -> list[StrategyInfo]:
        """发现所有策略:扫描所有插件目录,自动发现并加载 ``CwStrategy`` 子类。

        清空旧信息后重扫;``STRATEGY_ID`` 重复抛错指明首注册位(对标 app 插件 ``APP_ID`` 唯一性)。
        """
        self._infos.clear()
        self._classes.clear()
        self._scan_failures.clear()

        for plugin_dir, source in self._plugin_dirs:
            if not plugin_dir.is_dir():
                continue
            self._scan_directory(plugin_dir, reload_modules, source)

        self._discovered = True
        log.info(
            f"[cw-strategy] 发现 {len(self._infos)} 个策略, "
            f"{len(self._scan_failures)} 个失败: "
            f"{[info.strategy_id for info in self._infos.values()]}"
        )
        return list(self._infos.values())

    def _scan_directory(self, directory: Path, reload_modules: bool,
                        source: PluginSource) -> None:
        """扫描目录下所有 ``.py``,逐文件尝试加载策略(无后缀过滤,区别 app 插件)。"""
        for f in sorted(directory.rglob("*.py")):
            try:
                self._load_strategy_from_file(f, reload_modules, source, directory)
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                self._scan_failures.append((f, error_msg))
                log.warning(f"[cw-strategy] 加载策略文件 {f} 失败: {error_msg}")

    def _load_strategy_from_file(self, file: Path, reload_modules: bool,
                                 source: PluginSource, base_dir: Path) -> None:
        """从文件加载策略类(统一 spec_from_file_location;THIRD_PARTY 加 plugins 到 sys.path 支持相对导入)。"""
        # 1. 解析 module_name + module_root
        result = resolve_module_name(file, source, base_dir)
        if result is None:
            raise ImportError(f"无法解析模块路径: {file}")
        module_name, module_root = result

        # 2. 第三方插件校验:必须放子目录(不能直接放 plugins 根)
        try:
            relative_path = file.relative_to(module_root)
        except ValueError as e:
            raise ImportError(f"无法计算相对路径: {file}") from e
        rel_parts = relative_path.parts
        if source == PluginSource.THIRD_PARTY and len(rel_parts) < 2:
            raise ImportError(
                f"第三方策略不能直接放在 plugins 根目录: {file.name},"
                f"请放在子目录中(如 plugins/currency_war_strategies/my_strategy/{file.name})"
            )

        # 3. THIRD_PARTY:加 plugins 目录到 sys.path(支持相对导入)
        if source == PluginSource.THIRD_PARTY:
            ensure_sys_path(module_root, self._added_sys_paths)

        # 4. 模块加载/重载
        if module_name in sys.modules:
            if reload_modules:
                unload_prefix = self._get_unload_prefix(module_name, source, rel_parts)
                if unload_prefix:
                    self._unload_modules(unload_prefix)
                module = import_module_from_file(file, module_name, module_root, reload=True)
            else:
                module = sys.modules[module_name]
        else:
            module = import_module_from_file(file, module_name, module_root)

        # 5. 查找并注册策略类(每文件最多一个真实策略)
        self._find_strategy_in_module(module, module_name, file, source)

    def _get_unload_prefix(self, module_name: str, source: PluginSource,
                           rel_parts: tuple[str, ...]) -> str | None:
        """热重载时卸载的模块前缀(同 ApplicationFactoryManager 语义)。"""
        if source == PluginSource.THIRD_PARTY:
            return rel_parts[0] if rel_parts else None
        parent, _, _ = module_name.rpartition('.')
        return parent or None

    def _unload_modules(self, pkg_name: str) -> None:
        """卸载某前缀的所有模块。"""
        modules_to_remove = [
            name for name in sys.modules if name == pkg_name or name.startswith(f"{pkg_name}.")
        ]
        for name in modules_to_remove:
            del sys.modules[name]
        log.debug(f"[cw-strategy] 卸载策略模块: {modules_to_remove}")

    def _find_strategy_in_module(self, module: ModuleType, module_name: str,
                                 file: Path, source: PluginSource) -> None:
        """在模块中查找 ``CwStrategy`` 子类并注册(每文件最多一个真实策略)。

        排除:``CwStrategy`` 基类本身、``_abstract=True`` 中间辅助 ABC、``__module__`` 不匹配(导入的基类)、
        无 ``STRATEGY_ID``(未设 id 的基类)。``STRATEGY_ID`` 重复抛错指明首注册位。
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not (isinstance(attr, type) and issubclass(attr, CwStrategy) and attr is not CwStrategy):
                continue
            if getattr(attr, '_abstract', False):          # 中间辅助 ABC(如 RushBase),不注册
                continue
            if getattr(attr, '__module__', '') != module_name:  # 导入的基类,非本文件定义
                continue
            sid = getattr(attr, 'STRATEGY_ID', '')
            if not sid:                                     # 未设 id 的基类/桩,不注册
                continue
            if sid in self._infos:
                existing = self._infos[sid]
                raise ImportError(
                    f"重复的 STRATEGY_ID '{sid}',当前模块 {module_name},"
                    f"首次注册于 {existing.module_name}"
                )
            self._infos[sid] = StrategyInfo(
                strategy_id=sid,
                name=getattr(attr, 'STRATEGY_NAME', '') or sid,
                author=getattr(attr, 'AUTHOR', ''),
                version=getattr(attr, 'VERSION', '0.1'),
                description=getattr(attr, 'DESCRIPTION', ''),
                source=source,
                module_name=module_name,
                plugin_dir=file.parent,
                file_path=file,
            )
            self._classes[sid] = attr
            log.debug(f"[cw-strategy] 注册策略: {sid} ({attr_name}) source={source.value}")
            return                                          # 每文件最多一个真实策略

    def get_strategy_class(self, strategy_id: str) -> type[CwStrategy] | None:
        """按 id 取策略类(未发现先 discover)。无则 None。"""
        self._ensure_discovered()
        return self._classes.get(strategy_id)

    def instantiate(self, strategy_id: str) -> CwStrategy:
        """按 id 实例化策略(``cls()`` 无参)。找不到 → 回退 ``DefaultCwStrategy``(§11.5)。"""
        cls = self.get_strategy_class(strategy_id)
        if cls is None:
            log.warning(f"[cw-strategy] 未找到策略 '{strategy_id}',回退 DefaultCwStrategy")
            from sr_od.application.currency_war.strategies.default_strategy import (
                DefaultCwStrategy,
            )
            return DefaultCwStrategy()
        return cls()
