"""CW 哨兵重武三步工具(查旧 → 杀净 → 重武 → 验稳态)。

背景:runtime-ops.md「哨兵重武三步」节的三次双实例事故反推——「重武」不是一条命令,
是三步动作序列,局间交接时最容易跳步。本工具把该序列固化成一次调用,给编排者/值班
提醒调用(输出全中文、面向 agent 可读)。

步骤:
  1. 查旧:按命令行匹配 cw_sentinel|cw_early_stop|cw_runs_gap 的 python 进程并列出;
  2. 杀净:全部 kill(带 2 秒宽限确认,超时强杀);
  3. 重武:起指定组合(默认 sentinel+gap 两件;early_stop 有「首条遥测落后再武装」纪律,
    需显式 --early 才起);事件哨兵重武前删 cw_sentinel.pos 旧水位(--keep-pos 可保留);
  4. 验稳态:起后等 3 秒,按进程数核验(期望 = 所起件数),输出「N 件在岗」结论;
    验失败 → 非零退出码。

用法(PowerShell,项目根):
  uv run python tools/cw/rewatch.py --selftest          # 干跑:只查旧+列计划,不杀不起
  uv run python tools/cw/rewatch.py                     # 默认重武 sentinel+gap
  uv run python tools/cw/rewatch.py --sentinel --gap --early   # 三件全起

依赖:psutil(项目既有依赖,pyproject.toml 已声明);启动口径与 runtime-ops 一致:
  PYTHONUTF8=1 + `uv run python .debug/temp/currency_war/<脚本>.py`。
"""
import argparse
import contextlib
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

# 仓库根(本脚本在 tools/cw/ 下)
REPO_ROOT = Path(__file__).resolve().parents[2]
# 哨兵脚本目录(gitignore 区,不入 git 但运行时存在)
WATCH_DIR = REPO_ROOT / '.debug' / 'temp' / 'currency_war'
# 事件哨兵旧水位文件:不删 = 读旧水位误报(局47 实证)
SENTINEL_POS = WATCH_DIR / 'cw_sentinel.pos'

# 哨兵脚本名 → 武装说明(顺序即默认启动顺序)
WATCHERS: dict[str, str] = {
    'sentinel': ('cw_sentinel.py', '事件哨兵(高信号 pattern+卡死+静默双窗)'),
    'gap': ('cw_runs_gap.py', 'runs 断流哨兵'),
    'early': ('cw_early_stop.py', '早停哨兵(纪律:首条遥测落后再武装,须显式 --early)'),
}

KILL_GRACE_SEC = 2.0
SETTLE_WAIT_SEC = 3.0


def _cmdline_text(proc: psutil.Process) -> str:
    """拼进程完整命令行为单行小写文本,供匹配;取不到(已退出/权限)返回空串。"""
    try:
        return ' '.join(proc.cmdline()).lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return ''


def find_old_watchers() -> list[psutil.Process]:
    """查旧:按命令行匹配三个哨兵脚本名的进程(排除自身)。"""
    me = os.getpid()
    found: list[psutil.Process] = []
    for proc in psutil.process_iter():
        if proc.pid == me:
            continue
        text = _cmdline_text(proc)
        if not text:
            continue
        if any(name.lower() in text for name in ('cw_sentinel', 'cw_early_stop', 'cw_runs_gap')):
            found.append(proc)
    return found


def print_old_list(procs: list[psutil.Process]) -> None:
    """打印查旧结果(含每进程命令行摘要)。"""
    if not procs:
        print('[1/4 查旧] 无残留哨兵进程(干净)')
        return
    print(f'[1/4 查旧] 发现 {len(procs)} 个残留哨兵进程:')
    for proc in procs:
        text = _cmdline_text(proc) or '(命令行不可读)'
        print(f'  - pid={proc.pid} name={proc.name()} :: {text}')


def kill_all(procs: list[psutil.Process]) -> None:
    """杀净:全部 kill,带 2 秒宽限确认,超时强杀。"""
    if not procs:
        print('[2/4 杀净] 无需杀(本来就干净)')
        return
    for proc in procs:
        with contextlib.suppress(psutil.NoSuchProcess):
            proc.kill()  # 直接 kill:哨兵是旁观进程,无需优雅关闭
    _, alive = psutil.wait_procs(procs, timeout=KILL_GRACE_SEC)
    for proc in alive:
        print(f'  ! pid={proc.pid} 宽限 {KILL_GRACE_SEC}s 未退出,强杀')
        with contextlib.suppress(psutil.NoSuchProcess):
            proc.kill()
    _, still = psutil.wait_procs(alive, timeout=1.0)
    if still:
        pids = [p.pid for p in still]
        print(f'[2/4 杀净] 失败:pid {pids} 杀不掉')
        sys.exit(2)
    print(f'[2/4 杀净] 已杀 {len(procs)} 个(宽限 {KILL_GRACE_SEC}s 内全部退出)')


def arm(wanted: list[str], keep_pos: bool) -> None:
    """重武:删旧水位(按需)+ 起指定组合。"""
    # 事件哨兵旧水位清理(不删 = 读旧水位误报)
    if 'sentinel' in wanted and not keep_pos:
        if SENTINEL_POS.exists():
            SENTINEL_POS.unlink()
            print(f'[3/4 重武] 已删除旧水位 {SENTINEL_POS.name}(--keep-pos 可保留)')
        else:
            print(f'[3/4 重武] 无旧水位 {SENTINEL_POS.name}(无需删)')
    elif 'sentinel' in wanted and keep_pos:
        print(f'[3/4 重武] --keep-pos:保留旧水位 {SENTINEL_POS.name}')

    env = {**os.environ, 'PYTHONUTF8': '1'}
    detach = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    for key in wanted:
        script = WATCH_DIR / WATCHERS[key][0]
        if not script.exists():
            print(f'[3/4 重武] 失败:脚本不存在 {script}')
            sys.exit(2)
        # 口径与 runtime-ops 一致:uv run python <脚本>,后台脱离本进程存活
        subprocess.Popen(
            ['uv', 'run', 'python', str(script)],
            cwd=REPO_ROOT,
            env=env,
            creationflags=detach,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        print(f'[3/4 重武] 已起 {key} → {WATCHERS[key][0]}({WATCHERS[key][1]})')


def verify(expected: int) -> None:
    """验稳态:等 3 秒后按在岗脚本件数核验(一个脚本 = uv→python 进程链,可能 2-3 个
    进程同命令行,按进程数会翻倍,故按「命令行里出现该脚本名」去重计件);不等 → 非零退出。"""
    time.sleep(SETTLE_WAIT_SEC)
    procs = find_old_watchers()
    # 按脚本名归类:件数 = 出现在命令行里的不同哨兵脚本数
    names = ('cw_sentinel', 'cw_early_stop', 'cw_runs_gap')
    on_duty = {name for name in names for p in procs if name in (_cmdline_text(p) or '')}
    n = len(on_duty)
    if n == expected:
        detail = ', '.join(sorted(on_duty)) if on_duty else '(无)'
        print(f'[4/4 验稳态] {n} 件在岗(期望 {expected};{detail};进程数 {len(procs)})✅ 重武完成')
    else:
        pids = [p.pid for p in procs]
        print(f'[4/4 验稳态] 失败:在岗 {n} 件 ≠ 期望 {expected}({sorted(on_duty)};pids={pids})❌')
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description='CW 哨兵重武三步工具(查旧→杀净→重武→验稳态)')
    parser.add_argument('--sentinel', action='store_true', help='起事件哨兵 cw_sentinel.py')
    parser.add_argument('--gap', action='store_true', help='起断流哨兵 cw_runs_gap.py')
    parser.add_argument('--early', action='store_true',
                        help='起早停哨兵 cw_early_stop.py(纪律:首条遥测落后再武装,须显式传)')
    parser.add_argument('--keep-pos', action='store_true',
                        help='重武事件哨兵时保留 cw_sentinel.pos 旧水位(默认删)')
    parser.add_argument('--selftest', action='store_true', help='干跑:只查旧+列计划,不杀不起')
    args = parser.parse_args()

    # 默认两件(sentinel+gap);显式传了任一 flag 则按所传组合(early 只能显式加)
    flags = [k for k in ('sentinel', 'gap', 'early') if getattr(args, k)]
    wanted = flags if flags else ['sentinel', 'gap']

    procs = find_old_watchers()
    print_old_list(procs)

    if args.selftest:
        plan = ', '.join(wanted) if wanted else '(无)'
        print(f'[干跑] 计划重武组合: {plan}({"含 early,注意首条遥测纪律" if "early" in wanted else "early 未起"})')
        print('[干跑] --selftest 模式:不杀不起,到此为止')
        return

    kill_all(procs)
    arm(wanted, args.keep_pos)
    verify(len(wanted))


if __name__ == '__main__':
    main()
