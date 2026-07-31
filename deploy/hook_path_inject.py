"""PyInstaller 运行时 Hook：将外部 src/ 加入模块搜索路径。"""

import sys
from pathlib import Path

_src = Path(sys.executable).parent / "src"
sys.path.insert(0, str(_src))

# 与 OneDragon-RuntimeLauncher.spec 中的 KEEP_TREES 保持一致。
import one_dragon
one_dragon.__path__.append(str(_src / "one_dragon"))

import one_dragon.launcher
one_dragon.launcher.__path__.append(str(_src / "one_dragon" / "launcher"))
