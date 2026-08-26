# -*- coding: utf-8 -*-
"""runs 断流探测器(2026-08-23):补「局终但 runs.jsonl 无行」盲区。
原理:tail decisions.jsonl 的 run_id——当某 run 的「最后一轮 node_type 出现
战斗/boss 且 hp 已低」或「decisions 停更但 get_run_status 显示 idle」时,
runs.jsonl 应有新行;对局自然终局后 5 分钟仍无对应 run 行 → RUNS_GAP 报警
(stop 截断结算流/写端异常两种可能,人工判)。
armed 时快照已知 run_id 集合(历史悬挂不报);之后每 30s:decisions 出现
新的未结算 run_id 记入 seen_new;decisions 停更>300s 且 seen_new 有 run
在 runs.jsonl 找不到 → 报警退出。

v2(2026-08-26 效率修):原版每 30s 把 decisions.jsonl/runs.jsonl **全量重读**
+逐行 JSON 解析——decisions 已 11MB 且随对局无限增长,CPU 线性上涨(实测
33.8 CPU-秒/90min,为事件哨兵 30 倍)。改增量尾随:记 pos 只解析新增字节,
尾部半行存内存下轮拼接,文件变小(轮换/清理)时一次性全量重建。判据语义
与 v1 逐位一致(v1 的 last_dec_wall 本就不参与报警条件——报警活性判据=
decisions mtime,保留)。
同批加单实例锁(2026-08-26 重复武装事故:两次武装各起一套进程)与日志
信道自动探测(server 重启后落点在两候选间漂移,今晚实证)。
"""
import json
import os
import sys
import time
from pathlib import Path

import psutil

sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

REP = Path(os.environ.get(
    'CW_RUNSGAP_REP',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\replay'))
# 2026-08-26 信道自动探测:server 重启后日志落点漂移(.log/mcp_server.log 与
# .debug/sr_od_mcp/main_server.log),取 mtime 最新;env CW_RUNSGAP_LOG 优先。
_REPO = Path(r'D:\code\workspace\StarRailOneDragon')
_LOG_CANDIDATES = (_REPO / '.log' / 'mcp_server.log',
                   _REPO / '.debug' / 'sr_od_mcp' / 'main_server.log')


def _pick_log() -> Path:
    env = os.environ.get('CW_RUNSGAP_LOG')
    if env:
        return Path(env)
    alive = [p for p in _LOG_CANDIDATES if p.exists()]
    if not alive:
        return _LOG_CANDIDATES[0]
    return max(alive, key=lambda p: p.stat().st_mtime)


LOG = _pick_log()
# 单实例锁:已有活实例 → 退出;陈旧锁(pid 死/复用为非本脚本)自动覆盖。
LOCK = Path(os.environ.get(
    'CW_RUNSGAP_LOCK',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\cw_runs_gap.lock'))

STALL_S = 300


def _acquire_lock() -> bool:
    if LOCK.exists():
        try:
            old = psutil.Process(int(LOCK.read_text().strip()))
            if 'cw_runs_gap' in ' '.join(old.cmdline()).lower():
                print(f'[runsgap] 已有实例在岗 pid={old.pid},本次退出(防重复武装)', flush=True)
                return False
        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied,
                psutil.ZombieProcess):
            pass   # 陈旧锁 → 覆盖
    LOCK.write_text(str(os.getpid()))
    return True


class JsonlTail:
    """增量 run_id 采集:记 pos 只解析新增字节;半行存内存下轮拼接;
    文件变小(轮换/清理)时全量重建(重建后 ids 完整、pos 对齐文件尾)。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.ids: set[str] = set()
        self.pos = 0
        self._rem = ''
        self.full_scan()

    def full_scan(self) -> None:
        self.ids = set()
        self._rem = ''
        if not self.path.exists():
            self.pos = 0
            return
        data = self.path.read_bytes()
        self.pos = len(data)
        self._parse(data)

    def _parse(self, data: bytes) -> None:
        """解析新字节:与上轮半行拼接;尾半行(无换行)留在 _rem 等下轮。"""
        text = self._rem + data.decode('utf-8', errors='replace')
        cut = text.rfind('\n') + 1
        self._rem = text[cut:]
        for ln in text[:cut].splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                rid = json.loads(ln).get('run_id')
            except json.JSONDecodeError:
                continue
            if rid:
                self.ids.add(rid)

    def refresh(self) -> None:
        try:
            size = self.path.stat().st_size
        except OSError:
            return
        if size < self.pos:
            print(f'[runsgap] {self.path.name} 变小(轮换/清理),全量重建', flush=True)
            self.full_scan()
            return
        if size == self.pos:
            return
        with self.path.open('rb') as fh:
            fh.seek(self.pos)
            data = fh.read()
        self.pos += len(data)
        self._parse(data)


if not _acquire_lock():
    sys.exit(0)

dec = JsonlTail(REP / 'decisions.jsonl')
runs = JsonlTail(REP / 'runs.jsonl')
baseline = dec.ids - runs.ids   # 历史悬挂(如被 stop 截断的旧局)不报
print(f'[runsgap] armed v2 @ {time.strftime("%H:%M:%S")} '
      f'baseline 悬挂={len(baseline)} 已结算={len(runs.ids & dec.ids)} '
      f'log={LOG}', flush=True)

seen_new: set[str] = set()
_cur_log = LOG   # 当前活信道:每轮重探测(见下),活性判据始终以最新信道 mtime 为准
while True:
    time.sleep(30)
    # 信道周期重探测(2026-08-26 run 17 实证:server 重启后落点在两候选间漂移,
    # 武装时单点探测后信道再翻 → 盯死旧文件 mtime 会把「server 正常干活」误判
    # 为静默)。本循环本就每 30s stat 一次,把 stat 对象换成重探测后的当前信道:
    # 切换瞬间旧文件 mtime 陈旧不会被采信(取 mtime 最新候选 = 新信道)。
    _cand = _pick_log()
    if _cand != _cur_log:
        print(f'[runsgap] 日志信道漂移 {_cur_log} → {_cand},活性判据切换', flush=True)
        _cur_log = _cand
    try:
        dec.refresh()
        runs.refresh()
    except Exception as e:  # noqa: BLE001
        print(f'[runsgap] 读异常(继续): {e}', flush=True)
        continue
    # 未结算 run_id = decisions 有而 runs 没有(减武装基线);
    # 出现新的未结算 id = 有局在跑/刚跑过,继续守望
    hanging = {r for r in dec.ids if r not in runs.ids} - baseline
    fresh = hanging - seen_new
    if fresh:
        seen_new |= fresh
        continue
    # 无新悬挂:查 decisions 活性——停更超窗且仍有已见局缺 runs 行 → 报
    mtime_age = time.time() - (REP / 'decisions.jsonl').stat().st_mtime
    if mtime_age <= STALL_S or not (seen_new - runs.ids):
        continue
    # 11:2x 首报误报修正:decisions 停更 ≠ 对局已停——P2 开局长流程
    # (简报/投资环境/换面动画)也会停更 5min+。加 run 状态闸:主日志
    # 90s 内有新行(=server 活跃)则推迟,直到日志也静默才报。
    try:
        log_age = time.time() - _cur_log.stat().st_mtime
    except Exception:   # noqa: BLE001
        log_age = 999
    if log_age < 90:
        continue   # server 还在干活(长过渡),再等
    pending = seen_new - runs.ids
    print(f'[RUNS-GAP] 对局已停({int(mtime_age)}s 无新决策+日志静默{int(log_age)}s)但 runs 缺行: '
          f'{sorted(pending)}(stop 截断结算流或写端异常,人工判)', flush=True)
    sys.exit(0)
