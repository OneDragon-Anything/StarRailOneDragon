"""画面额外识别器(recognizer)的扫描器:扫描 sr_od 包,发现并注册 recognizer。

镜像 ``operation_registry.scan_operations`` 的扫描套路(``_SCAN_ROOTS`` + ``_iter_py_modules``
rglob + ``__module__`` 守卫 + 模块级 ``_CACHE``),唯一差异:扫描期**无参实例化**每个
recognizer 子类(op 扫描是纯反射不实例化,因为 ``SrOperation.__init__`` 有副作用)。
recognizer 无状态(screen_name 是类属性),实例化一次缓存复用。

供 ``backend_context.analyze`` 在画面精准命中后按 ``screen_name`` 查表调用。
详见 ``docs/superpowers/specs/2026-08-09-screen-recognizer-design.md``。
"""
import importlib
import inspect
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import (
    RecognizerScanResult,
    ScreenRecognizer,
    ScreenRecognizerRegistry,
)
from one_dragon.utils import os_utils

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

# 同 operation_registry 的两个扫描根:recognizer 既可随 app 代码放(currency_war/recognizers/),
# 也可在通用 operation 包下(如登录/菜单等非 app 画面的 recognizer)。两边都扫,自动发现。
_SCAN_ROOTS: list[str] = ['sr_od.operations', 'sr_od.application']
_CACHE: RecognizerScanResult | None = None


def _iter_py_modules(pkg: str) -> Iterator[str]:
    """遍历扫描根包下所有 .py(跳过 ``__init__.py``),产出 dotted module path。

    与 ``operation_registry._iter_py_modules`` 同构(就地重写,不 import 其私有 ``_`` 函数)。
    """
    src_root = Path(os_utils.get_work_dir()) / 'src'
    pkg_dir = src_root.joinpath(*pkg.split('.'))
    if not pkg_dir.is_dir():
        return
    for f in pkg_dir.rglob('*.py'):
        if f.name == '__init__.py':
            continue
        rel = f.relative_to(pkg_dir).with_suffix('')
        yield f'{pkg}.{".".join(rel.parts)}'


def _is_recognizer(module_name: str, cls: object) -> bool:
    """ScreenRecognizer 子类 + __module__ 守卫(防 re-export)+ 排除基类/*Base。"""
    if not inspect.isclass(cls) or not issubclass(cls, ScreenRecognizer):
        return False
    if cls is ScreenRecognizer:
        return False
    if getattr(cls, '__module__', None) != module_name:
        return False
    return not cls.__name__.endswith('Base')


def scan_recognizers(ctx: 'SrContext', refresh: bool = False) -> RecognizerScanResult:
    """扫描 _SCAN_ROOTS,挑 ScreenRecognizer 子类 → 无参实例化 → 按 .screen_name 注册。

    单模块 import 失败 / 重复 screen_name / 实例化失败 记 failures 不中断;结果缓存,
    ``refresh=True`` 重扫。``ctx`` 占位(扫描纯反射,保持接口与 ``scan_operations`` 一致)。

    Args:
        ctx: SrContext(占位,保持与其它 backend 接口一致)。
        refresh: 是否强制重扫(忽略缓存)。

    Returns:
        扫描结果(registry + failures)。
    """
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE

    registry = ScreenRecognizerRegistry()
    failures: list[str] = []
    for pkg in _SCAN_ROOTS:
        for module in _iter_py_modules(pkg):
            try:
                mod = importlib.import_module(module)
            except Exception as e:  # noqa: BLE001 单模块失败不中断
                failures.append(f'{module}: {e}')
                continue
            for _name, attr in vars(mod).items():
                if not _is_recognizer(module, attr):
                    continue
                try:
                    instance = attr()  # 无参实例化(stateless;ctx/image 每 recognize 传)
                    err = registry.register(instance)
                    if err is not None:
                        failures.append(f'{module}.{attr.__name__}: {err}')
                except Exception as e:  # noqa: BLE001 实例化失败不中断
                    failures.append(f'{module}.{attr.__name__} 实例化失败: {e}')

    result = RecognizerScanResult(registry=registry, failures=failures)
    _CACHE = result
    return result


def get_recognizer(ctx: 'SrContext', screen_name: str) -> ScreenRecognizer | None:
    """analyze 便捷入口(走缓存):按 screen_name 取识别器,无则 None。"""
    return scan_recognizers(ctx).registry.get(screen_name)
