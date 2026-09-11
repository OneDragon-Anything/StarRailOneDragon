"""journal 收口断流探测器 v3(2026-09-11,T-257:尾读源切 journal)。

## 为什么改造

前身「runs 断流探测器」(2026-08-23)尾读 decisions.jsonl 采集 run_id、对账
runs.jsonl 行——删除波 1(T-243)后 runs/decisions 两流写入端已从 src 删除
(哨兵武装时两流 mtime 冻结在停写时刻:decisions 恒「停更」、runs 恒「缺行」,
武装即误报)。本版把尾读源切到 journal(state/journal.jsonl,唯一账面)。

## 检查项语义对照(旧→新,判据等价映射)

- 「decisions 出现新 run_id = 有局在跑」→「journal 出现实机形态新 run 段」。
  实机段形态 = ``run_`` + 8 位日期 + ``_`` + 6 位时刻(正则 ``^run_[0-9]{8}_[0-9]{6}``
  锚定,telemetry/state.start_run 铸造口径);
  journal 是多写者单文件(sim 批 fake_/sim_ 段、harness 短 id 段与实机段
  交错追加),不过滤则 sim 段写入会污染「有局/停更」判据——隔离前缀约定
  = sim/cw_delta_pool_gen.QUARANTINED_RUN_PREFIXES,哨兵侧按正选实机段
  实现(白名单形态而非黑名单前缀:新写者形态未知时默认不采信,保守)。
- 「runs.jsonl 缺行 = 结算流断」→「实机段无 match_final 收口行」。runs 流
  已消亡,runs 的 journal 收编载体 = 局终域 match_final 行(kernel/
  cw_board_state.write_match_final,一段一行,局终收口时落)。报警词保留
  [RUNS-GAP](下游消费词汇不破)。**接线状态申报(T-257 落地审定性)**:
  match_final 在线收口写点在 W3 批接线(本脚本交付时点 HEAD 上 write_match_final
  无生产调用点,cw_loop 两调用点系 W3 工作树在飞)——接线入库前生产局终了
  **不会**产行,「段无 match_final」对每局正常终了恒真,不构成故障证据。
  故本版报警路径前置**过渡守卫**(判据=全账实机段 mf 行总数,见武装块注):
  守卫激活期报警静默,账面出现首个收口行自动解除;W3 接线验收后守卫可删。
- 「decisions mtime 停更」→「实机段行流对哨兵可见的新鲜度」。journal 文件
  mtime 会被 sim 段写入污染,不可用;改记「最后一次见到实机段行的本地时刻」。
- 「主日志 90s 静默闸」不变(op_journal 保留,server 活跃判据照旧)。

## 历史版本

- v2(2026-08-26 效率修):增量尾随替代全量重读;单实例锁;日志信道自动
  探测。本版沿用其结构与锁/信道机制。
- v1(2026-08-23):初版。
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import psutil

sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

REP = Path(os.environ.get(
    'CW_RUNSGAP_REP',
    r'D:\code\workspace\StarRailOneDragon\.debug\currency_war\telemetry\live'))
# journal 唯一账面(删除波 1 后 runs/decisions 停写,state/journal.jsonl =
# 流程侧唯一落盘流;journal.md §1。与旧流同根,state/ 子目录。
JOURNAL = Path(os.environ.get(
    'CW_RUNSGAP_JOURNAL', str(REP / 'state' / 'journal.jsonl')))
# 实机段形态(telemetry/state.start_run 铸造口径 run_%Y%m%d_%H%M%S);
# fake_/sim_ 段与 harness 短 id 段一律不采信(隔离约定 =
# sim/cw_delta_pool_gen.QUARANTINED_RUN_PREFIXES,这里按正选实现)。
RUN_ID_RE = re.compile(os.environ.get('CW_RUNSGAP_RUN_RE', r'^run_\d{8}_\d{6}$'))
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


class JournalTail:
    """journal 增量尾随(v2 JsonlTail 的 journal 段状态版):记 pos 只解析
    新增字节;半行存内存下轮拼接;文件变小(轮换/清理)时全量重建。

    产出段状态(segs):run_id → {'mf': 段内已见 match_final 收口行}。
    只收实机形态段(RUN_ID_RE 过滤,sim/harness 段行不进状态)。
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.segs: dict[str, dict] = {}
        self.mf_rows = 0   # 全账实机段 match_final 收口行总数(过渡守卫判据,见武装块注)
        self.pos = 0
        self._rem = ''
        self.full_scan()

    def full_scan(self) -> None:
        self.segs = {}
        self.mf_rows = 0
        self._rem = ''
        if not self.path.exists():
            self.pos = 0
            return
        data = self.path.read_bytes()
        self.pos = len(data)
        self._parse(data)

    def _parse(self, data: bytes) -> bool:
        """解析新字节:与上轮半行拼接;尾半行(无换行)留在 _rem 等下轮。
        坏行逐行跳过(journal.md §5 宽容消费契约,禁把半行当合法行)。
        返回本批是否见到实机段行(行流活性信号)。"""
        text = self._rem + data.decode('utf-8', errors='replace')
        cut = text.rfind('\n') + 1
        self._rem = text[cut:]
        seen_real = False
        for ln in text[:cut].splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            rid = row.get('run_id')
            if not rid or not RUN_ID_RE.match(str(rid)):
                continue
            seen_real = True
            seg = self.segs.setdefault(str(rid), {'mf': False})
            if row.get('row') == 'write' and row.get('field') == 'match_final':
                seg['mf'] = True
                self.mf_rows += 1
        return seen_real

    def refresh(self) -> bool:
        """增量读;返回本批是否见到实机段行。"""
        try:
            size = self.path.stat().st_size
        except OSError:
            return False
        if size < self.pos:
            print(f'[runsgap] {self.path.name} 变小(轮换/清理),全量重建', flush=True)
            self.full_scan()
            return False   # 重建的历史行不算新鲜(行 ts 是过去,非本批到达)
        if size == self.pos:
            return False
        with self.path.open('rb') as fh:
            fh.seek(self.pos)
            data = fh.read()
        self.pos += len(data)
        return self._parse(data)

    def hanging_ids(self) -> set[str]:
        """未收口实机段(无 match_final 行的段)。"""
        return {rid for rid, seg in self.segs.items() if not seg['mf']}


if not _acquire_lock():
    sys.exit(0)

# 干跑/自测覆盖(仅自测改小,沿 cw_sentinel 自测 env 先例):轮询间隔/停更窗/
# 主日志闸。生产缺省:停更窗 300s(v2 时代 decisions 停更口径)、间隔 30s、
# 主日志静默闸 90s(v2 时代 P2 开局长流程误报修正口径),三者数值与 v2 一致。
INTERVAL_S = float(os.environ.get('CW_RUNSGAP_INTERVAL', '30'))
STALL_S = int(os.environ.get('CW_RUNSGAP_STALL', '300'))
LOG_QUIET_S = float(os.environ.get('CW_RUNSGAP_LOG_AGE', '90'))

jt = JournalTail(JOURNAL)
baseline = jt.hanging_ids()   # 历史悬挂(如被 stop 截断的旧局)不报
# 过渡守卫(T-257 落地审打回件;W3 批接线 match_final 在线收口写点,接线入库前
# 生产局终了不产行——本报警判据「段无 match_final」在接线前对每局正常终了
# 恒真,武装即每局必报)。守卫判据 = 全账实机段 match_final 行总数 jt.mf_rows:
# 为 0 = 写点在库产出能力从未被观测到,「段缺收口行」不可归因(未接线 vs
# 写端异常分不开)→ 候报自愈退出;运行中账面出现首个 mf 行(= 接线落地且
# 首局实跑收口)即解除,恢复正常报警。抑制窗口因此收敛于「接线 commit 前
# 的实机窗」;W3 接线验收后守卫可删,删除前为无害保守。
guard_quiet = jt.mf_rows == 0
print(f'[runsgap] armed v3 @ {time.strftime("%H:%M:%S")} '
      f'journal={JOURNAL} baseline 悬挂段={len(baseline)} '
      f'已收口段={sum(1 for s in jt.segs.values() if s["mf"])} '
      f'mf行={jt.mf_rows}'
      f'{" [守卫:写点未观测到产出,收口断流报警抑制中]" if guard_quiet else ""} '
      f'log={LOG}', flush=True)

# 干跑钩子(--selftest-dry 配套,生产不触发):SMOKE=1 武装快照验证即退;
# SMOKE_GAP=1 时把 NEWSEG 指定段以未收口行注入 journal 文件(模拟新局出现
# 后停止更新),缩窗后应走 [RUNS-GAP] 报警路径(守卫未激活时)或「守卫抑制」
# 说明(武装时账面无任何 mf 行);SMOKE_UNGUARD=1 时再由后台线程延迟注入
# 一条 match_final 行(模拟 W3 接线落地首局收口),应见「守卫解除」打印且
# 随后未收口段恢复报警能力。
if os.environ.get('CW_RUNSGAP_SMOKE') == '1':
    sys.exit(0)
if os.environ.get('CW_RUNSGAP_SMOKE_GAP') == '1':
    def _smoke_row(field: str, rid: str) -> str:
        return json.dumps({'v': 1, 'ts': '2020-01-01T00:00:00', 'run_id': rid,
                           'row': 'write', 'field': field, 'after': 1,
                           'same_value': False, 'state': {'values': {}},
                           'sig': {}, 'note': '', 'evidence_refs': []}) + '\n'
    _rid = os.environ.get('CW_RUNSGAP_SMOKE_NEWSEG', 'run_20000101_000000')
    with JOURNAL.open('a', encoding='utf-8') as _fh:
        _fh.write(_smoke_row('gold', _rid))
    if os.environ.get('CW_RUNSGAP_SMOKE_UNGUARD') == '1':
        import threading
        def _unguard() -> None:
            time.sleep(INTERVAL_S * 1.5)
            with JOURNAL.open('a', encoding='utf-8') as fh:
                fh.write(_smoke_row('match_final', 'run_20000101_000099'))
        threading.Thread(target=_unguard, daemon=True).start()

seen_new: set[str] = set()
last_seen_wall = time.time()   # 实机段行流新鲜度(武装时视为刚见过,防武装即报)
_cur_log = LOG   # 当前活信道:每轮重探测(见下),活性判据始终以最新信道 mtime 为准
while True:
    time.sleep(INTERVAL_S)
    # 信道周期重探测(2026-08-26 run 17 实证:server 重启后落点在两候选间漂移,
    # 盯死旧文件 mtime 会把「server 正常干活」误判为静默)。取 mtime 最新候选。
    _cand = _pick_log()
    if _cand != _cur_log:
        print(f'[runsgap] 日志信道漂移 {_cur_log} → {_cand},活性判据切换', flush=True)
        _cur_log = _cand
    try:
        if jt.refresh():
            last_seen_wall = time.time()   # 实机段行流仍在到达(对局活着)
    except Exception as e:  # noqa: BLE001
        print(f'[runsgap] 读异常(继续): {e}', flush=True)
        continue
    if guard_quiet and jt.mf_rows > 0:
        guard_quiet = False
        print('[runsgap] 过渡守卫解除:账面出现首个 match_final 收口行'
              '(写点接线已落地,恢复收口断流报警)', flush=True)
    hanging = jt.hanging_ids() - baseline
    fresh = hanging - seen_new
    if fresh:
        seen_new |= fresh
        last_seen_wall = time.time()   # 有新实机段(新局在跑/刚跑过)
        continue
    # 已见未收口段 = seen_new 中仍无 match_final 的段(等价旧 seen_new - runs.ids)
    pending = seen_new & jt.hanging_ids()
    # 无新悬挂段:查实机段行流活性——停更超窗且仍有已见未收口段 → 候报。
    # 活性判据 = 最后一次见到实机段行的本地时刻(journal 文件 mtime 被
    # sim 段写入污染不可用;armed 起算,增量见行即刷新)。
    seen_age = time.time() - last_seen_wall
    if seen_age <= STALL_S or not pending:
        continue
    # 实机段停更 ≠ 对局已停——P2 开局长流程(简报/投资环境/换面动画)也会
    # 停更 5min+(v2 时代 decisions 同形实证)。加主日志闸:90s 内有新行
    # (=server 活跃)则推迟,直到日志也静默才报。
    try:
        log_age = time.time() - _cur_log.stat().st_mtime
    except Exception:   # noqa: BLE001
        log_age = 999
    if log_age < LOG_QUIET_S:
        continue   # server 还在干活(长过渡),再等
    if guard_quiet:
        # 过渡守卫命中:写点产出从未被观测(接线前),「段缺收口行」不可归因。
        # 自愈退出(NO_ACTIVE_RUN 同型):守卫期本报警无能力也不该占单实例锁
        # 死守(锁会挡住接线落地后的新实例武装);W3 接线后经常规重武三步
        # 起新实例即恢复判据(新实例武装时账面已有 mf 行,守卫不激活)。
        print(f'[runsgap] 收口断流候报被过渡守卫抑制,自愈退出(写点未观测到'
              f'产出,疑似 match_final 在线收口接线未落地=W3 批辖域;接线后'
              f'重武即恢复正常判据): {sorted(pending)}', flush=True)
        sys.exit(0)
    pending_list = sorted(pending)
    print(f'[RUNS-GAP] 对局已停(实机段行流 {int(seen_age)}s 无新增+日志静默{int(log_age)}s) '
          f'但段无 match_final 收口行: {pending_list}'
          f'(stop 截断收口流转或写端异常,人工判)', flush=True)
    sys.exit(0)
