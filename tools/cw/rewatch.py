"""CW 哨兵清理与核岗工具(查旧 → 杀净 → 打印标准武装命令 → 核岗)。

背景:runtime-ops.md「哨兵重武三步」节的三次双实例事故反推——「重武」不是一条命令,
是三步动作序列,局间交接时最容易跳步。本工具把清理与核岗固化,给编排者/值班提醒调用
(输出全中文、面向 agent 可读)。

⚠️ 本工具**不自起哨兵**(历史教训:曾用 DETACHED 自起——进程在但退出码无人接收,
报警链自断,哨兵哑了;2026-08-25 用户纠正后移除)。哨兵三件的「起」永远走**会话后台
任务信道**(退出码=警报,可送达编排者);本工具只管:
  1. 查旧:按命令行匹配 cw_sentinel|cw_early_stop|cw_runs_gap 的 python 进程并列出;
  2. 杀净:全部 kill(带 2 秒宽限确认);
  3. 打印标准武装命令(--print-commands,默认开):按参数列该由编排者以后台任务起的
     命令(默认 sentinel+gap 两件;early_stop 有「首条遥测落后再武装」纪律,须显式
     --early 才列入);
  4. 核岗(--verify N):按在岗脚本件数核验,并把在岗状态(脚本名+pid+核对时刻)写入
     rewatch.status(不扫进程表也能看什么在岗);不等 → 非零退出码。

用法(PowerShell,项目根):
  uv run python tools/cw/rewatch.py                    # 查旧+杀净+打印武装命令
  uv run python tools/cw/rewatch.py --verify 2         # 编排者起完后核岗(期望 2 件)
  uv run python tools/cw/rewatch.py --print-commands --early  # 三件全列(含 early)
  uv run python tools/cw/rewatch.py --selftest         # 干跑:只查旧+列计划,不杀

依赖:psutil(项目既有依赖,pyproject.toml 已声明);武装命令口径与 runtime-ops 一致:
  PYTHONUTF8=1 + `uv run python .debug/temp/currency_war/<脚本>.py`。
"""
import argparse
import contextlib
import os
import re
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
# 在岗状态文件(脚本名+pid+核对时刻,一行一件;核岗时整批重写)——
# 让任何人不扫进程表也能看什么在岗
STATUS_FILE = WATCH_DIR / 'rewatch.status'

# 哨兵脚本名 → 武装说明
WATCHERS: dict[str, str] = {
    'sentinel': ('cw_sentinel.py', '事件哨兵(高信号 pattern+卡死+静默双窗)'),
    'gap': ('cw_runs_gap.py', 'runs 断流哨兵'),
    'early': ('cw_early_stop.py', '早停哨兵(纪律:首条遥测落后再武装,须显式 --early)'),
}

WATCHER_CMD_NAMES = ('cw_sentinel', 'cw_early_stop', 'cw_runs_gap')
KILL_GRACE_SEC = 2.0


def _cmdline_text(proc: psutil.Process) -> str:
    """拼进程完整命令行为单行小写文本,供匹配;取不到(已退出/权限)返回空串。"""
    try:
        return ' '.join(proc.cmdline()).lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return ''


def _is_on_duty(text: str, name: str) -> bool:
    """词级匹配(W133 低危①):裸子串 `name in text` 会把 'cw_sentinel_x' 类
    同前缀名误计在岗 → --verify 假绿。正则 \b 边界('_' 是词字符,前缀延长名
    不构成边界)排除;匹配语义其余不变。"""
    return bool(text) and re.search(rf'\b{re.escape(name)}\b', text) is not None


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
        if any(_is_on_duty(text, name) for name in WATCHER_CMD_NAMES):
            found.append(proc)
    return found


def print_old_list(procs: list[psutil.Process]) -> None:
    """打印查旧结果(含每进程命令行摘要)。"""
    if not procs:
        print('[查旧] 无哨兵进程在岗')
        return
    print(f'[查旧] 发现 {len(procs)} 个哨兵进程:')
    for proc in procs:
        text = _cmdline_text(proc) or '(命令行不可读)'
        print(f'  - pid={proc.pid} name={proc.name()} :: {text}')


def kill_all(procs: list[psutil.Process]) -> None:
    """杀净:全部 kill,带 2 秒宽限确认,超时强杀。"""
    if not procs:
        print('[杀净] 无需杀(本来就干净)')
        return
    for proc in procs:
        with contextlib.suppress(psutil.NoSuchProcess):
            proc.kill()  # 哨兵是旁观进程,无需优雅关闭
    _, alive = psutil.wait_procs(procs, timeout=KILL_GRACE_SEC)
    for proc in alive:
        print(f'  ! pid={proc.pid} 宽限 {KILL_GRACE_SEC}s 未退出,强杀')
        with contextlib.suppress(psutil.NoSuchProcess):
            proc.kill()
    _, still = psutil.wait_procs(alive, timeout=1.0)
    if still:
        pids = [p.pid for p in still]
        print(f'[杀净] 失败:pid {pids} 杀不掉')
        sys.exit(2)
    print(f'[杀净] 已杀 {len(procs)} 个(宽限 {KILL_GRACE_SEC}s 内全部退出)')


def print_commands(wanted: list[str]) -> None:
    """打印标准武装命令——哨兵必须由编排者经会话后台任务信道起(退出码=警报可送达),
    本工具不自起(DETACHED 自起=报警链自断,2026-08-25 用户纠正后移除)。"""
    print('[武装命令] 以下命令请由编排者经会话后台任务机制执行(勿在本工具内起):')
    for key in wanted:
        script = WATCH_DIR / WATCHERS[key][0]
        note = ';注意首条遥测落后再武装纪律' if key == 'early' else ''
        print(f"  {key}: $env:PYTHONUTF8='1'; uv run python {script}({WATCHERS[key][1]}{note})")
    print('[武装命令] 事件哨兵起前删旧水位 cw_sentinel.pos(本工具杀净阶段已顺手处理)')
    print('[武装命令] 起完后用 `--verify N`(N=件数)核岗')


def verify(expected: int) -> None:
    """核岗:按在岗脚本件数核验(一个脚本 = uv→python 进程链,可能 2-3 个进程同命令行,
    按进程数会翻倍,故按「命令行里出现该脚本名」去重计件);并把在岗状态写入
    rewatch.status;不等 → 非零退出。"""
    procs = find_old_watchers()
    on_duty: dict[str, list[int]] = {name: [] for name in WATCHER_CMD_NAMES}
    for proc in procs:
        text = _cmdline_text(proc)
        for name in WATCHER_CMD_NAMES:
            if _is_on_duty(text, name):
                on_duty[name].append(proc.pid)
    duty = {name for name, pids in on_duty.items() if pids}
    n = len(duty)
    # 状态文件整批重写(每件一行:脚本名+pid 链+核对时刻);原子写(W133 低危③):
    # 写临时文件 + os.replace——两处并发核岗时整批直写会互踩(last-writer-wins
    # 半写态),replace 在同目录保证原子替换,读方永远见完整批次。
    checked_at = time.strftime('%Y-%m-%d %H:%M:%S')
    lines = [f'{name} pids={",".join(map(str, on_duty[name]))} checked={checked_at}'
             for name in sorted(duty)]
    tmp = STATUS_FILE.with_name(STATUS_FILE.name + '.tmp')
    tmp.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
    os.replace(tmp, STATUS_FILE)
    if n == expected:
        detail = ', '.join(sorted(duty)) if duty else '(无)'
        print(f'[核岗] {n} 件在岗(期望 {expected};{detail};进程数 {len(procs)})✅')
        print(f'[核岗] 在岗状态已写入:{STATUS_FILE}')
    else:
        print(f'[核岗] 失败:在岗 {n} 件 ≠ 期望 {expected}({sorted(duty)};详见 {STATUS_FILE})❌')
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description='CW 哨兵清理与核岗工具(查旧→杀净→打印武装命令→核岗;不自起)')
    parser.add_argument('--sentinel', action='store_true', help='武装命令列事件哨兵 cw_sentinel.py')
    parser.add_argument('--gap', action='store_true', help='武装命令列断流哨兵 cw_runs_gap.py')
    parser.add_argument('--early', action='store_true',
                        help='武装命令列早停哨兵 cw_early_stop.py(纪律:首条遥测落后再武装,须显式传)')
    parser.add_argument('--print-commands', dest='print_commands', action='store_true', default=True,
                        help='杀净后打印标准武装命令(默认开)')
    parser.add_argument('--no-print-commands', dest='print_commands', action='store_false',
                        help='不打印武装命令')
    parser.add_argument('--verify', type=int, metavar='N',
                        help='核岗模式:期望 N 件在岗(编排者起完后调用);不杀不起只核验+写状态文件')
    parser.add_argument('--selftest', action='store_true', help='干跑:只查旧+列计划,不杀不起')
    args = parser.parse_args()

    # 默认两件(sentinel+gap);显式传了任一 flag 则按所传组合(early 只能显式加)
    flags = [k for k in ('sentinel', 'gap', 'early') if getattr(args, k)]
    wanted = flags if flags else ['sentinel', 'gap']

    if args.verify is not None:
        verify(args.verify)
        return

    procs = find_old_watchers()
    print_old_list(procs)

    if args.selftest:
        plan = ', '.join(wanted)
        print(f'[干跑] 计划武装组合: {plan}({"含 early,注意首条遥测纪律" if "early" in wanted else "early 未列"})')
        print('[干跑] --selftest 模式:不杀不起,到此为止')
        return

    kill_all(procs)
    # 事件哨兵旧水位清理(杀净后顺手做;不删 = 下次武装读旧水位误报)
    if 'sentinel' in wanted and SENTINEL_POS.exists():
        SENTINEL_POS.unlink()
        print(f'[杀净] 已顺手删旧水位 {SENTINEL_POS.name}')
    if args.print_commands:
        print_commands(wanted)


if __name__ == '__main__':
    main()
