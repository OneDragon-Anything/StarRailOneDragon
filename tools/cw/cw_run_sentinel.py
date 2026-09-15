"""货币战争 运行停滞哨兵(框架外独立进程)。

背景:框架侧原内嵌「停滞 watchdog」(同屏 OCR 指纹采样)已随守卫治理删除
(架构口径:框架只做识别分发与记账,对局状态推进的监测归外部哨兵;框架
留下的观测面 = 每次画面分发出口统一落的 ``[cw-op]`` 主日志行)。本脚本即
该口径的哨兵侧承接:**框架记账,哨兵判读**。

监测的两类停滞形态(日志域):

- 同 op 连发:最近 N 条 ``[cw-op]`` 行 op 名全部相同且该段跨时超过阈值
  ——同屏指纹停滞在日志域的镜像(原 watchdog 的主要捕获形态:执行面
  变换失败/策略闩振荡/活锁,画面认得但流程空转);
- 沉默:超过阈值无任何新 ``[cw-op]`` 行——循环死亡或永动不派发(战斗
  实测 4-5.5 分钟,沉默阈值须留足余量防误报)。

报警通道:**只留证不停机**(与原 watchdog 同语义,bot 可能只是慢)——
写 ``stall_watch.flag``(落位与处理指引和 od-dev-stop-hooks 的哨兵 flag
协议一致)+ 控制台告警行。停机决策归观察者(人工 / 巡检)。

用法::

    uv run python tools/cw/cw_run_sentinel.py            # 常驻轮询(默认 30s)
    uv run python tools/cw/cw_run_sentinel.py --once     # 单次判定(cron/测试)
    uv run python tools/cw/cw_run_sentinel.py --log <路径>

退出码(--once 模式):0 = 正常;2 = 判定停滞(已写 flag)。
仅依赖标准库。
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

#: [cw-op] 行解析(宽松:op 必取,outcome 缺省按 unknown 计)。
_LINE_RE = re.compile(r'\[cw-op\]\s+op=(?P<op>\S+)(?:.*?outcome=(?P<outcome>\S+))?')

#: 日志候选(项目根相对,取 mtime 最新者;--log 可覆盖)。
_LOG_CANDIDATES = (
    Path('.debug/sr_od_mcp/main_server.log'),
    Path('.log/mcp_server.log'),
)

#: stall_watch.flag 落位(与原框架 watchdog 同位,处理协议共用)。
_FLAG_PATH = Path('.debug/currency_war/stall_watch.flag')


def _resolve_log(explicit: str | None) -> Path | None:
    """日志路径解析:显式优先;否则候选里取最近修改且存在的。"""
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    living = [c for c in _LOG_CANDIDATES if c.exists()]
    return max(living, key=lambda c: c.stat().st_mtime) if living else None


def _read_new_lines(path: Path, offset: int) -> tuple[int, list[tuple[float, str]]]:
    """增量读日志:返回(新 offset, [(本机收到时刻, op 名)]。文件截断则重置。"""
    size = path.stat().st_size
    if size < offset:
        offset = 0
    out: list[tuple[float, str]] = []
    if size == offset:
        return offset, out
    now = time.time()
    with path.open('r', encoding='utf-8', errors='replace') as f:
        f.seek(offset)
        for line in f:
            m = _LINE_RE.search(line)
            if m:
                out.append((now, m.group('op')))
        offset = f.tell()
    return offset, out


def _judge(history: list[tuple[float, str]], now: float,
           same_op_count: int, same_op_mins: float,
           silence_mins: float) -> str | None:
    """停滞判定(纯函数,便于测试):返回 None = 正常,否则为停滞形态描述。

    :param history: 增量累计的 (本机收到时刻, op 名) 序列(本进程生命周期内)。
    """
    if not history:
        return None
    tail_ops = [op for _, op in history[-same_op_count:]]
    if (len(tail_ops) >= same_op_count
            and len(set(tail_ops)) == 1
            and now - history[-same_op_count][0] >= same_op_mins * 60):
        return (f'同 op 连发:最近 {same_op_count} 条 [cw-op] 均为'
                f'「{tail_ops[0]}」,跨时 {((now - history[-same_op_count][0]) / 60):.1f} 分钟')
    silence_s = now - history[-1][0]
    if silence_s >= silence_mins * 60:
        return f'沉默:最近一次 [cw-op] 距今 {silence_s / 60:.1f} 分钟(最后 op = {history[-1][1]})'
    return None


def _write_flag(reason: str, tail: list[tuple[float, str]], now: float) -> Path:
    """留证 flag(处理指引与 od-dev-stop-hooks 哨兵协议一致)。"""
    _FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tail_txt = '\n'.join(
        f'  {time.strftime("%H:%M:%S", time.localtime(t))} op={op}'
        for t, op in tail[-12:])
    _FLAG_PATH.write_text(
        '[SENTINEL] 运行停滞哨兵触发(框架外判读;只留证不停机)\n'
        f'形态:{reason}\n'
        f'最近 [cw-op](本哨兵启动以来):\n{tail_txt}\n'
        '处理流程:\n'
        '1. 按最近 op 名判画面(分析截图/日志);未建档 overlay → 建档 + cw_loop 0x 分支;\n'
        '2. 画面已建档 → 查该 op 执行链为何空转(同 op 连发)/ 循环是否死亡(沉默);\n'
        '3. 停机决策归观察者:需要停 → MCP stop_run;处理完删本 flag。\n'
        f'sentinel={time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))}',
        encoding='utf-8')
    return _FLAG_PATH


def main() -> int:
    ap = argparse.ArgumentParser(description='CW 运行停滞哨兵([cw-op] 日志判读,只留证不停机)')
    ap.add_argument('--log', help='日志路径(缺省取候选中最新)')
    ap.add_argument('--interval', type=float, default=30.0, help='轮询间隔秒(默认 30)')
    ap.add_argument('--same-op-count', type=int, default=6, help='同 op 连发判定条数(默认 6)')
    ap.add_argument('--same-op-mins', type=float, default=5.0, help='同 op 连发跨时阈值分钟(默认 5)')
    ap.add_argument('--silence-mins', type=float, default=20.0, help='沉默阈值分钟(默认 20;战斗 4-5.5 分钟,勿低于 10)')
    ap.add_argument('--once', action='store_true', help='单次判定后退出(退出码 0 正常 / 2 停滞)')
    args = ap.parse_args()

    log_path = _resolve_log(args.log)
    if log_path is None:
        print('[cw-sentinel] 未找到运行日志(候选均不存在);--once 退出码 0', file=sys.stderr)
        return 0 if args.once else 1
    print(f'[cw-sentinel] watch={log_path} interval={args.interval}s '
          f'same_op={args.same_op_count}x{args.same_op_mins}min silence={args.silence_mins}min')

    offset = 0
    if log_path.exists():          # 既有历史不回看:只判本哨兵生命周期内的新行
        offset = log_path.stat().st_size
    history: list[tuple[float, str]] = []
    alarmed = False

    while True:
        offset, new_ops = _read_new_lines(log_path, offset)
        history.extend(new_ops)
        verdict = _judge(history, time.time(),
                         args.same_op_count, args.same_op_mins, args.silence_mins)
        if verdict is not None and not alarmed:
            flag = _write_flag(verdict, history, time.time())
            print(f'[cw!][sentinel] 停滞:{verdict} → flag={flag}', file=sys.stderr, flush=True)
            alarmed = True
        elif verdict is None and alarmed:
            print('[cw-sentinel] 停滞解除(画面推进/新派发到位);flag 留存待人工清理', flush=True)
            alarmed = False
        if args.once:
            return 2 if alarmed else 0
        time.sleep(args.interval)


if __name__ == '__main__':
    sys.exit(main())
