"""CW 哨兵清理与核岗工具(查旧/杀净/打印标准武装命令/核岗;杀净须显式 --kill)。

背景:runtime-ops.md「哨兵重武三步」节的三次双实例事故反推——「重武」不是一条命令,
是三步动作序列,局间交接时最容易跳步。本工具把清理与核岗固化,给编排者/值班提醒调用
(输出全中文、面向 agent 可读)。

⚠️ 本工具**不自起哨兵**(历史教训:曾用 DETACHED 自起——进程在但退出码无人接收,
报警链自断,哨兵哑了;2026-08-25 用户纠正后移除)。哨兵的「起」永远走**会话后台
任务信道**(退出码=警报,可送达编排者);本工具只管:
  1. 查旧:按命令行匹配 cw_sentinel|cw_early_stop|cw_runs_gap|cw_asset_sentinel
     的 python 进程并列出;
  2. 杀净(--kill 显式才触发;树终杀+杀后复扫断言):匹配进程与其 psutil
      树后代一并 kill(带 2 秒宽限确认);杀后重扫断言零残留——复扫非空自动
      再杀(有界重试),仍非空 exit 2,「杀净」从尽力而为变成可验证出口;
  3. 打印标准武装命令(--print-commands,默认开):按参数列该由编排者以后台任务起的
     命令(默认 sentinel+gap 两件;early_stop 有「首条遥测落后再武装」、asset 是
     「长驻型不随局」纪律,均须显式 --early / --asset 才列入);
  4. 核岗(--verify N):按在岗脚本件数核验,并把在岗状态(脚本名+pid+核对时刻)写入
     rewatch.status(不扫进程表也能看什么在岗);不等 → 非零退出码。

安全默认:无参数 = 只查旧(打印在岗清单+武装命令,零杀)。无参数调用的高频
意图是核对在岗状态,不是清理——查旧无害、杀是破坏性动作,把杀放在显式位
(--kill),防「想核岗手滑无参数」把在岗哨兵整链杀掉。

用法(PowerShell,项目根):
  uv run python tools/cw/rewatch.py                    # 只查旧+打印武装命令(默认零杀)
  uv run python tools/cw/rewatch.py --kill             # 查旧+杀净+打印武装命令
  uv run python tools/cw/rewatch.py --verify 2         # 编排者起完后核岗(期望 2 件)
  uv run python tools/cw/rewatch.py --print-commands --early  # 三件全列(含 early)
  uv run python tools/cw/rewatch.py --selftest         # 干跑:只查旧+列计划,不杀

依赖:psutil(项目既有依赖,pyproject.toml 已声明);武装命令口径与 runtime-ops 一致:
  PYTHONUTF8=1 + `uv run python <脚本真身路径>`——随局三件在 skill scripts 目录,
  资产哨兵例外住 tools/cw/(路径例外单一源 = SCRIPT_HOME/_script_path)。
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
# 哨兵脚本单一源(skill 版本化目录;runtime-ops「哨兵脚本组」节口径:
# 武装命令直接从 skill 目录起,不再用 .debug/temp 下的散拷贝——散拷贝
# 会滞留旧版常量,遥测根迁移后旧拷贝盯死路径 = 哨兵哑掉)
SCRIPTS_DIR = REPO_ROOT / 'skills' / 'sr-od-currency-war-dev' / 'scripts'
# 哨兵运行态文件目录(水位/锁/在岗状态;.debug/temp 约定不变)
WATCH_DIR = REPO_ROOT / '.debug' / 'temp' / 'currency_war'
# 事件哨兵旧水位文件:不删 = 读旧水位误报(局47 实证)
SENTINEL_POS = WATCH_DIR / 'cw_sentinel.pos'
# 在岗状态文件(脚本名+pid+核对时刻,一行一件;核岗时整批重写)——
# 让任何人不扫进程表也能看什么在岗
STATUS_FILE = WATCH_DIR / 'rewatch.status'

# 哨兵脚本名 → (脚本文件名, 武装说明)二元组;消费方按元组解包/取下标
# (rewatch.print_commands 与 cycle_restart 的 arm/supervise 路径),
# 注解须与实值同形——错标单值会让类型检查起诉合法解包
WATCHERS: dict[str, tuple[str, str]] = {
    'sentinel': ('cw_sentinel.py', '事件哨兵(高信号 pattern+卡死+静默双窗)'),
    'gap': ('cw_runs_gap.py', 'runs 断流哨兵'),
    'early': ('cw_early_stop.py', '早停哨兵(纪律:首条遥测落后再武装,须显式 --early)'),
    # 资产哨兵是长驻型(不随局武装/重武),且资产监控面不随局变化——
    # 武装一次基线常驻,故默认组合不含它,须显式 --asset
    'asset': ('cw_asset_sentinel.py',
              '资产完整性哨兵(OCR 模型+CW 模板库基线对比;长驻型,不随局,须显式 --asset)'),
}

WATCHER_CMD_NAMES = ('cw_sentinel', 'cw_early_stop', 'cw_runs_gap', 'cw_asset_sentinel')

# 例外件真身目录表(T-173-r1 验收缺陷 B):资产哨兵是仓库运维工具,住
# tools/cw/ 而非 skill scripts 目录——路径例外单一源在本表,寻址一律走
# _script_path,禁消费方散拼 SCRIPTS_DIR / 文件名(照拼出死命令,2026-09-13
# 验收实测 print_commands 打印不存在的 skill 路径)。缺省不在表 = skill 件。
TOOL_SCRIPTS_DIR = REPO_ROOT / 'tools' / 'cw'
SCRIPT_HOME: dict[str, Path] = {'asset': TOOL_SCRIPTS_DIR}


def _script_path(key: str) -> Path:
    """哨兵脚本真身路径:例外件按 SCRIPT_HOME,其余件在 skill scripts 目录。"""
    return SCRIPT_HOME.get(key, SCRIPTS_DIR) / WATCHERS[key][0]

KILL_GRACE_SEC = 2.0
# 杀净出口的「杀→复扫」总轮数上限(1 轮主杀 + 至多 2 轮复扫再杀;轮数耗尽
# 仍非空 = exit 2 可验证失败)——有界重试,不做无限兜圈
KILL_RESCAN_MAX = 3


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


def collect_tree(procs: list[psutil.Process]) -> list[psutil.Process]:
    """树收编:每个进程经 psutil children(recursive=True) 并入其全部后代,
    按 pid 去重(排除本工具自身),返回「匹配进程 ∪ 后代」的杀集。

    为什么:哨兵实为 pwsh→uv→venv python→base python
    的进程链,今天四层命令行都含脚本名、命令行匹配够用,明天 uv 改实现
    未必——后代命令行不含脚本名/不可读时按命令行抓不到,树语义保证
    链上进程不孤儿化(2026-09-08 实证:单点杀 pwsh 留 uv→python 孤儿,
    占 runs_gap 锁拒新实例+报警链断成哑哨兵)。psutil 单机制:树遍历
    只用 children(recursive=True),不引 taskkill/CIM 第二套。
    """
    out: dict[int, psutil.Process] = {}
    for proc in procs:
        if proc.pid in out or proc.pid == os.getpid():
            continue
        out[proc.pid] = proc
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied,
                                 psutil.ZombieProcess):
            for child in proc.children(recursive=True):
                if child.pid not in out and child.pid != os.getpid():
                    out[child.pid] = child
    return list(out.values())


def _merge_procs(*groups: list[psutil.Process]) -> list[psutil.Process]:
    """按 pid 去重合并多组进程(杀集幸存者 ∪ 复扫命中,防同进程双计)。"""
    merged: dict[int, psutil.Process] = {}
    for group in groups:
        for proc in group:
            merged.setdefault(proc.pid, proc)
    return list(merged.values())


def _kill_procs(victims: list[psutil.Process]) -> list[psutil.Process]:
    """杀一批进程(kill→宽限确认→强杀),返回宽限+强杀后仍存活的成员。

    kill 抑制 NoSuchProcess+AccessDenied:Windows TerminateProcess 是
    原子的——目标死了,或抛 AccessDenied(需管理员),不存在「不抛异常
    但不死」的中间态。杀不动=视作存活返回,交复扫轮有界重试,最终走
    exit 2 可验证失败;不抑制会让真实「需管理员权限」
    场景变成未处理异常(traceback 退 1),绕过 exit 2 契约,消费方
    (编排者后台 job / cycle_restart)拿到契约外退出码。
    """
    for proc in victims:
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            proc.kill()  # 哨兵是旁观进程,无需优雅关闭
    _, alive = psutil.wait_procs(victims, timeout=KILL_GRACE_SEC)
    for proc in alive:
        print(f'  ! pid={proc.pid} 宽限 {KILL_GRACE_SEC}s 未退出,强杀')
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            proc.kill()
    _, still = psutil.wait_procs(alive, timeout=1.0)
    return list(still)


def kill_all(procs: list[psutil.Process]) -> None:
    """杀净(树终杀 + 杀后复扫断言)。

    树终杀:匹配进程+collect_tree 收编的后代一并杀;杀后复扫:重跑
    find_old_watchers,非空自动再杀(KILL_RESCAN_MAX 轮有界重试),仍
    非空 exit 2——把「杀净」从尽力而为变成可验证出口:杀净步骤被绕过
    时(2026-09-08 事故:Stop-Process 杀 pwsh 留 uv→python 孤儿)人忘了
    核,命令会报红。停净判据=「[杀净] …复扫零残留 ✅」或「[杀净]
    无需杀(本来就干净)」二者之一(他信道已停净时只有后者;[复扫]
    前缀行只在重试轮与最终失败出现)。
    """
    if not procs:
        print('[杀净] 无需杀(本来就干净)')
        return
    for round_no in range(1, KILL_RESCAN_MAX + 1):
        victims = collect_tree(procs)
        descendants = [p for p in victims if p.pid not in {q.pid for q in procs}]
        if descendants and round_no == 1:
            print(f'[杀净] 树收编:并入 {len(descendants)} 个后代进程'
                  f'(pid {[p.pid for p in descendants]})')
        still = _kill_procs(victims)
        leftover = find_old_watchers()
        remaining = _merge_procs(still, leftover)
        if not remaining:
            print(f'[杀净] 已杀 {len(procs)} 个匹配进程+树收编后代'
                  f'(宽限 {KILL_GRACE_SEC}s 内全部退出);复扫零残留 ✅')
            return
        procs = remaining
        print(f'[复扫] 第 {round_no} 轮杀后仍有 {len(remaining)} 个哨兵进程'
              f'(pid {[p.pid for p in remaining]}),再杀')
    print(f'[复扫] 失败:{KILL_RESCAN_MAX} 轮杀+复扫后仍有残留'
          f'(pid {[p.pid for p in procs]})——可能需管理员权限,请人工核查')
    sys.exit(2)


def kill_pids_tree(pids: list[int]) -> list[int]:
    """按 pid 树终杀:目标进程+psutil 树收编后代一并 kill。

    cycle_restart 两处单点杀消费点(supervise 兄弟终止 / start_app 失败
    回滚)的复用缝:Popen.terminate() 在 Windows 下不
    级联,只杀 uv 层会孤儿化 venv python→base python 链——两处复用本
    实现,杀语义与 kill_all 单一源,禁在消费点自造第二套树杀。
    返回杀后仍存活的杀集 pid(含树收编后代;空列表 = 全杀净,以「杀集
    成员无一存活」为可验证出口);目标 pid 已死时幂等返回空。
    """
    targets: list[psutil.Process] = []
    for pid in pids:
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            targets.append(psutil.Process(pid))
    if not targets:
        return []
    return [p.pid for p in _kill_procs(collect_tree(targets))]


def print_commands(wanted: list[str]) -> None:
    """打印标准武装命令——哨兵必须由编排者经会话后台任务信道起(退出码=警报可送达),
    本工具不自起(DETACHED 自起=报警链自断,2026-08-25 用户纠正后移除)。"""
    print('[武装命令] 以下命令请由编排者经会话后台任务机制执行(勿在本工具内起):')
    for key in wanted:
        # 寻址单一源 = _script_path(例外件 asset 在 tools/cw/,散拼
        # SCRIPTS_DIR 会打印不存在的死命令,T-173-r1 验收缺陷 B)
        script = _script_path(key)
        note = ''
        if key == 'early':
            note = ';注意首条遥测落后再武装纪律'
        elif key == 'asset':
            note = ';注意长驻型:不随局重武,自主推进期武装一次即可'
        print(f"  {key}: $env:PYTHONUTF8='1'; uv run python {script}({WATCHERS[key][1]}{note})")
    print('[武装命令] 事件哨兵起前删旧水位 cw_sentinel.pos(本工具杀净阶段已顺手处理)')
    print('[武装命令] 起完后用 `--verify N`(N=件数)核岗')


def verify(expected: int) -> None:
    """核岗:按在岗脚本件数核验(一个脚本 = uv→python 进程链,可能 2-3 个进程同命令行,
    按进程数会翻倍,故按「命令行里出现该脚本名」去重计件);并把在岗状态写入
    rewatch.status;不等 → 非零退出。

    已知局限(申报不修):①按名计件——同名双实例仍计 1 件,
    exit 0 检不出实例堆积(打印的 pid 列表供人眼核对);②cmdline 命中即在岗——
    哑孤儿(报警信道已断的残留进程)照样绿,exit 0 ≠ 报警信道活,活性回读
    以 cw_sentinel.pos 心跳推进 / 后台 job 结算为准(runtime-ops「哨兵活性回读」)。
    """
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
    parser = argparse.ArgumentParser(
        description='CW 哨兵清理与核岗工具(查旧/核岗/打印武装命令;杀净须显式 --kill;不自起)',
        epilog='示例:\n'
               '  uv run python tools/cw/rewatch.py             # 只查旧+打印武装命令(默认零杀)\n'
               '  uv run python tools/cw/rewatch.py --kill      # 查旧+杀净+打印武装命令\n'
               '  uv run python tools/cw/rewatch.py --verify 2  # 核岗(期望 2 件在岗)\n'
               '  uv run python tools/cw/rewatch.py --selftest  # 干跑:只查旧+列计划,不杀',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--sentinel', action='store_true', help='武装命令列事件哨兵 cw_sentinel.py')
    parser.add_argument('--gap', action='store_true', help='武装命令列断流哨兵 cw_runs_gap.py')
    parser.add_argument('--early', action='store_true',
                        help='武装命令列早停哨兵 cw_early_stop.py(纪律:首条遥测落后再武装,须显式传)')
    parser.add_argument('--asset', action='store_true',
                        help='武装命令列资产完整性哨兵 cw_asset_sentinel.py'
                             '(长驻型:不随局武装,自主推进期武装一次;须显式传)')
    parser.add_argument('--print-commands', dest='print_commands', action='store_true', default=True,
                        help='杀净后打印标准武装命令(默认开)')
    parser.add_argument('--no-print-commands', dest='print_commands', action='store_false',
                        help='不打印武装命令')
    parser.add_argument('--verify', type=int, metavar='N',
                        help='核岗模式:期望 N 件在岗(编排者起完后调用);不杀不起只核验+写状态文件')
    parser.add_argument('--selftest', action='store_true', help='干跑:只查旧+列计划,不杀不起')
    parser.add_argument('--kill', action='store_true',
                        help='杀净模式:杀掉查旧命中的哨兵进程(树终杀+杀后复扫断言)。'
                             '缺省只查旧零杀——防核岗场景误杀在岗哨兵')
    args = parser.parse_args()

    # 默认两件(sentinel+gap);显式传了任一 flag 则按所传组合(early/asset 只能显式加)
    flags = [k for k in ('sentinel', 'gap', 'early', 'asset') if getattr(args, k)]
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

    if not args.kill:
        # 安全默认:只查旧零杀——无参数调用的高频意图是核对在岗状态,不是清理;
        # 杀是破坏性动作,必须显式 --kill。模式行让调用方明确确认「没有杀」。
        print('[模式] 只查旧(零杀);杀净请显式加 --kill')
        if args.print_commands:
            print_commands(wanted)
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
