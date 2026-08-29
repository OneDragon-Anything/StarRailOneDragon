"""构建指纹(server 进程身份;W596 防御件,源自 W593 定位批方案①)。

背景:改代码必须重启 server 才生效,而旧进程仍在飞时磁盘代码与运行行为错位
(实证:局22 worn=0 根因 = server 进程跑旧构建,三段证据合围耗半天,见
`.debug/temp/currency_war/w593_equip_wear/DESIGN.md` §2.3)。本模块让
「哪个构建的进程在跑」随时可查:启动时 log 一行 + 落盘指纹文件。

纯观测/记账件:不改任何业务行为;git 不可用(打包环境/非 git 目录)时
降级为 `unknown`,不阻塞启动。
"""
import subprocess
from datetime import datetime
from pathlib import Path

# 项目根(本文件 = src/sr_od/backend/build_info.py → parents: backend/sr_od/src/根)。
# git 命令的 cwd 必须在仓库内,否则 rev-parse 解析到别的仓库或失败。
_PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

_fingerprint_cache: str | None = None


def _run_git(args: list[str]) -> str | None:
    """跑一条 git 命令返 stdout 首行;任何失败(git 缺失/非仓库/超时)返 None。"""
    try:
        proc = subprocess.run(
            ['git'] + args,
            cwd=_PROJECT_ROOT, capture_output=True, text=True,
            timeout=5, encoding='utf-8', errors='replace',
        )
    except Exception:   # noqa: BLE001  指纹是观测件,任何失败都降级不阻塞
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or '').strip().splitlines()
    return out[0].strip() if out else None


def get_build_fingerprint() -> str:
    """构建指纹短串:`<git短hash>` 或 `<git短hash>+dirty`(工作区有未提交改动)或 `unknown`。

    进程内缓存(git 调用不便宜;指纹语义 = 进程启动时的磁盘代码状态,
    运行中代码再变也不该改变本进程的指纹)。
    """
    global _fingerprint_cache
    if _fingerprint_cache is not None:
        return _fingerprint_cache
    fp = _run_git(['rev-parse', '--short', 'HEAD'])
    if fp is None:
        fp = 'unknown'
    else:
        dirty = _run_git(['status', '--porcelain'])
        if dirty:   # porcelain 有输出 = 工作区有未提交改动
            fp += '+dirty'
    _fingerprint_cache = fp
    return fp


def log_build_fingerprint() -> str:
    """启动期记一次构建指纹:log 首行 + 指纹文件落盘。返回指纹串。

    指纹文件 = `.debug/sr_od_mcp/build_fingerprint.txt`(每进程启动覆写:
    pid + 启动时刻 + 指纹)。为什么文件与 log 双写:mcp_server.log 跨重启追加
    且有轮转,判读「现在在跑哪个构建」要 O(1) 读一个文件,不用翻日志找最近一行。
    落盘失败静默(log 已有一份),指纹是观测件不因 IO 阻塞启动。
    """
    from one_dragon.utils.log_utils import log
    fp = get_build_fingerprint()
    log.info('[build] server 构建指纹=%s pid=%s 启动=%s 项目根=%s',
             fp, _pid(), datetime.now().isoformat(timespec='seconds'), _PROJECT_ROOT)
    try:
        marker = _PROJECT_ROOT / '.debug' / 'sr_od_mcp' / 'build_fingerprint.txt'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            f'fingerprint={fp}\npid={_pid()}\n'
            f'started_at={datetime.now().isoformat(timespec="seconds")}\n',
            encoding='utf-8')
    except Exception:   # noqa: BLE001
        pass
    return fp


def _pid() -> int:
    """进程号(log 行与指纹文件共用;独立小函数便于测试桩化)。"""
    import os
    return os.getpid()
