"""r229c 事件哨兵 v4(v3 事件/卡死/静默 + 活跃循环卡死检测)。

v2 保留: 只报需介入的事件(崩溃栈/ERROR/停机/plan_error),例行 WARNING 不报。
v3 新增:
  A) 重复行堆积卡死(skill 防坑清单判据的脚本化,局47 教训 50min 才停):
     近 STALL_WIN 秒内同一特征 WARNING/ERROR 行 ≥ STALL_N 次,
     且窗口内无任何推进行 → [SENTINEL-STALL]。
     - OCR DEBUG 行天然高频重复(实测每秒多条),故只统计 WARNING/ERROR 级;
     - 推进行取 INFO 级动作结果(实机日志实证,非 OCR 按钮文字):
       '[cw][composite]' / '→ ✓' / '执行成功' / '出战成功'
  B) 静默死锁(双窗确认 v3.4): 见过行后连续 SILENCE_SEC 无新行 → 进入二次确认
     窗(打印 sentinel-watch 提示不退出);确认窗 SILENCE_CONFIRM 内仍零新行 →
     [SENTINEL-SILENCE](真僵死两窗皆静默,不漏报)。单窗直报已废——战斗结算屏/
     长动画等待段(无 OCR 循环→日志静默 300-600s)三连误报实证(2026-08-25)。

v3.5(2026-08-25 12:51 误报修)「局后空窗误报」: 双窗防的是局中静默(结算/动画
  段),没防「局已自然终局后的空闲静默」——静默判定前加「活跃局检查」(离线纯读
  replay/runs.jsonl+outcomes.jsonl):终局 → [RUN-ENDED-IDLE] 优雅退出;活跃 →
  原双窗。
v3.8(2026-08-26 02:2x)短开轮询: 不长持日志句柄(挡 Windows 午夜轮转 rename);
  信道 mtime 周期重探测(server 重启后日志落点漂移)。

v4.0(2026-08-27 W180,run 24 实证驱动)「活跃循环卡死」检测:
  run 24(60min 局)卡死于「前台区域无角色」出战被拒循环——日志**不静默**(每
  ~56s 一轮新行,step1 买0张 → step2 RunDeploy 已部署角色 → step4「出战成功」
  (误判)→ 弹窗确认 → 下一轮),v3 的 STALL 分支(只数 WARNING/ERROR + 要求窗口
  内零「→ ✓」推进行)对此**永不触发**:循环里全是 INFO 动作结果行。实测卡死
  段 04:34:32-05:27:17(~53min,65 次同循环),人工 ~53min 后才停。
  判据(单一源=CW skill 防坑清单「局中卡死巡检=日志重复度」的推广):
    近 LOOP_WIN 秒内,同一**归一化签名**(去时间戳+数字)的定向动作行
    (白名单前缀:[cw][director] step / [cw-loop] / [cw][battle] / [cw-deploy])
    重复 ≥ LOOP_N 次,且窗口内**零实质推进**(实质推进 = ①非零 买/升/刷/卖
    (plan 结果行);②state 行 round/plane 变化(含新局回绕);③「进位面」)
    → [SENTINEL-LOOP]。
  「出战成功」**刻意不算推进**——run 24 实证弹窗误判下它每轮都假成功。
  参数标定: run 24 循环周期 ~55s,N=10 ≈ 9-10min 触发(第一报警位点实测
  ~04:43,比人工早 ~44min);窗口 1500s 容纳慢周期(2min/循环)。
  防误报设计: 正常局每轮都有 state 行(round 递增)→ 任何 25min 窗口内必有
  推进,永不报警;run22/23 的孤立「前台无角色」瞬态弹窗(01:15/01:59/02:01/
  03:25/03:27 共 5 次,恢复了)远低于 N=10,不触发。
  报警动作(试用期纪律,runtime-ops): 默认 CW_SENTINEL_TRIAL=1 **只报警**——
  落证据文件(触发时间/窗口特征行摘录/建议动作)后退出;观察期标定零误报后,
  由编排者改 CW_SENTINEL_TRIAL=0 武装自动处置:POST {CW_SENTINEL_HTTP}/game/stop
  (MCP HTTP 停止信号,与 stop_run 同通道;**restart/起局永不自动**——实机
  编排保留给主 agent)。

日志时间戳无日期(跨天 append),窗口按 HH:MM:SS 回绕计算;
日志轮转(文件变小)时从头读并重置窗口。
离线自测: 环境变量 CW_SENTINEL_LOG / CW_SENTINEL_POS 重定向日志与水位路径;
  CW_SENTINEL_REPLAY_DIR(或 CW_SENTINEL_RUNS / CW_SENTINEL_OUTCOMES)重定向
  活跃局判定文件;CW_SENTINEL_SILENCE / CW_SENTINEL_CONFIRM 覆盖阈值(仅自测)。
  python cw_sentinel.py --selftest: 内置回归(局后空窗→IDLE / 局中静默→SILENCE /
  信道漂移 / 活跃循环→LOOP / 正常推进→不误报)。
  python cw_sentinel.py --replay <日志文件>: 历史日志回放——全文件喂行处理逻辑,
  打印全部 [SENTINEL-LOOP] 报警位点(每卡死段一次;不退出不 stop,验证用)。
"""
import json
import os
import re
import sys
import time
from collections import deque
from pathlib import Path

import psutil

sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

REPLAY_MODE = False   # --replay 回放态: 关闭陈旧行防线/静默分支/单实例锁/自动 stop

# 2026-08-26 信道自动探测:server 重启后日志落点会漂移(.log/mcp_server.log 与
# .debug/sr_od_mcp/main_server.log 两个候选,今晚实证重启后旧文件死透哨兵变哑)。
# 取 mtime 最新的候选;env CW_SENTINEL_LOG 显式指定时优先。
_REPO = Path(r'D:\code\workspace\StarRailOneDragon')
_LOG_CANDIDATES = (_REPO / '.log' / 'mcp_server.log',
                   _REPO / '.debug' / 'sr_od_mcp' / 'main_server.log')


def _pick_log() -> Path:
    env = os.environ.get('CW_SENTINEL_LOG')
    if env:
        # 仅自测:CW_SENTINEL_LOG2 提供第二候选,构造「信道漂移」回归
        env2 = os.environ.get('CW_SENTINEL_LOG2')
        if env2:
            pair = [Path(env), Path(env2)]
            alive = [p for p in pair if p.exists()]
            if not alive:
                return pair[0]
            return max(alive, key=lambda p: p.stat().st_mtime)
        return Path(env)
    alive = [p for p in _LOG_CANDIDATES if p.exists()]
    if not alive:
        return _LOG_CANDIDATES[0]
    return max(alive, key=lambda p: p.stat().st_mtime)


LOG = _pick_log()
# 信道周期重探测间隔(秒)。默认 60——只在静默分支重探测(读不到新行时),
# 不随 5s 主循环节奏刷 stat(2026-08-26 run 17 实证:武装后信道再翻,哨兵盯死
# 旧文件直到静默误报;武装时单点探测不够,需周期复探)。env 可调仅自测加速。
REPROBE_SEC = float(os.environ.get('CW_SENTINEL_REPROBE', 60))
MARKER = Path(os.environ.get('CW_SENTINEL_POS', r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\cw_sentinel.pos'))
# 单实例锁(2026-08-26 重复武装事故:23:27/23:33 两次武装各起一套进程,哨兵
# 重复不报错但加倍吃资源且水位文件互相踩)。已有活实例 → 本次退出;
# 陈旧锁(pid 已死/被复用为非本脚本进程)自动覆盖,无需手工清理。
LOCK = Path(os.environ.get('CW_SENTINEL_LOCK', r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\cw_sentinel.lock'))


def _acquire_lock() -> bool:
    """单实例锁:返回 False = 已有活实例在岗(本进程不跑)。"""
    if LOCK.exists():
        try:
            old = psutil.Process(int(LOCK.read_text().strip()))
            if 'cw_sentinel' in ' '.join(old.cmdline()).lower():
                print(f'[sentinel] 已有实例在岗 pid={old.pid},本次退出(防重复武装)', flush=True)
                return False
        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied,
                psutil.ZombieProcess):
            pass   # 陈旧锁 → 覆盖
    LOCK.write_text(str(os.getpid()))
    return True
_REPLAY_DIR = Path(os.environ.get('CW_SENTINEL_REPLAY_DIR', r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\replay'))
RUNS_JSONL = Path(os.environ.get('CW_SENTINEL_RUNS', str(_REPLAY_DIR / 'runs.jsonl')))
OUTCOMES_JSONL = Path(os.environ.get('CW_SENTINEL_OUTCOMES', str(_REPLAY_DIR / 'outcomes.jsonl')))

# v2 原样:只报需介入的事件(第一版把对账纠漂/MISS 例行也报了,噪声淹没真警报)
PATTERNS = (
    'Traceback',
    'plan_error',
    '执行失败',
    '停机待建档',
    'STOPPED',
    '人工结束',
    '超时',
    'stall_watch',
    'TypeError',
    'AttributeError',
    'StopIteration',
)
PROGRESS = ('[cw][composite]', '→ ✓', '执行成功', '出战成功')  # 推进行(动作结果)
STALL_WIN = 600    # 卡死判定窗口(秒)
STALL_N = 10       # 同特征行阈值
SILENCE_SEC = int(os.environ.get('CW_SENTINEL_SILENCE', 360))  # 静默死锁阈值(秒)
SILENCE_CONFIRM = int(os.environ.get('CW_SENTINEL_CONFIRM', 420))  # v3.4:二次确认窗
OUTCOME_FRESH_SEC = 900  # v3.5:outcomes 近此窗口内有更新 → 视为有活跃局

# ── v4.0 活跃循环卡死(W180,run 24 标定)─────────────────────────────
LOOP_WIN = int(os.environ.get('CW_SENTINEL_LOOP_WIN', 1500))  # 循环判定窗口(秒)
LOOP_N = int(os.environ.get('CW_SENTINEL_LOOP_N', 10))        # 同签名阈值
# 只数定向动作行(白名单前缀)——OCR/obs 冲突行天然秒级重复,数它们必误报;
# 「对局循环 返回状态 等待」每秒多条,同样排除。
LOOP_PREFIXES = ('[cw][director] step', '[cw-loop]', '[cw][battle]', '[cw-deploy]')
# 实质推进:非零 买/升/刷/卖(只认 plan 结果行,防遥测文本偶合误命中)
NONZERO_RE = re.compile(r'[买升刷卖][1-9]\d*')
PLAN_LINE = ('返回状态 plan', 'step1 RunBuyPhase', 'step2 RunBuyPhase')
# 实质推进:轮次推进(round/plane 变化;round 减小 = 新局,也是推进)。
# 两种日志形态都认(2026-08-25/26 实测):
#   ① shop 决策行 'state gold=24 hp=84 lv=4 plane=1 round=3 ...'(08-26 起);
#   ② 战斗回合行 '[cw-loop] on_round_end plane=1 round=9 ...'(两期通用)。
# 08-25 只认①时三类正常段误报实证:点球爆发(ClickSpheres 同签名一局 7-10 次)
# /备战相位进入/部署跳过——②缺位 → round 推进不可见。
STATE_GATE = 'state gold='
ROUND_RE = re.compile(r'round=(\d+)')
PLANE_RE = re.compile(r'plane=(\d+)')
# 推进事件的「阻断时效」(秒):推进后此窗口内不判循环(点球爆发等单轮高频
# 正常动作靠它豁免);超时后即使窗口里还有更早的推进行,只要同签名动作行
# 已重复满阈值仍报警——run 24 实证:推进停在 04:34:02,若阻断时效=整个
# LOOP_WIN(1500s) 则 04:59 才报,浪费 16min。
LOOP_STALE = int(os.environ.get('CW_SENTINEL_LOOP_STALE', 600))
# 同签名首末出现最小跨度(秒):区分「持续循环」与「单轮爆发」。奖励节点点球
# 单轮可爆发 4-7 次同一签名(44s 内),run 24 卡死循环 10 次跨 ~500s——跨度
# <300s 的纯爆发不算卡死(08-25 03:28/17:07 两例误报的根因)。
LOOP_SPAN_MIN = int(os.environ.get('CW_SENTINEL_LOOP_SPAN', 300))
# 试用期纪律(runtime-ops):TRIAL=1(默认)= 只报警落证据不处置;观察期标定
# 零误报后由编排者显式改 0 武装自动 stop。AUTOSTOP=1 且 TRIAL=0 时才真停。
LOOP_TRIAL = os.environ.get('CW_SENTINEL_TRIAL', '1') != '0'
LOOP_AUTOSTOP = os.environ.get('CW_SENTINEL_AUTOSTOP', '0') == '1'
LOOP_HTTP = os.environ.get('CW_SENTINEL_HTTP', 'http://127.0.0.1:24001')
LOOP_EVIDENCE = Path(os.environ.get(
    'CW_SENTINEL_LOOP_EVIDENCE',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\cw_loop_alert.md'))

TS_RE = re.compile(r'^\[(\d{2}):(\d{2}):(\d{2})')
NUM_RE = re.compile(r'\d+')


def _tod(line: str) -> int | None:
    """解析行首 [HH:MM:SS → 当日秒数;无时间戳返回 None。"""
    m = TS_RE.match(line)
    if not m:
        return None
    h, mi, s = (int(g) for g in m.groups())
    return h * 3600 + mi * 60 + s


def _sig(line: str) -> str:
    """去时间戳 + 数字归一 → 同模板警告行同签名(「备战席已满」×N 同签名)。"""
    return NUM_RE.sub('#', TS_RE.sub('', line))[:160]


def _delta(a: int, b: int) -> int:
    """b-a 秒数,按日志无日期跨午夜回绕计算。"""
    return (b - a) % 86400


def _jsonl_tail(path: Path, chunk: int = 8192) -> dict | None:
    """读 jsonl 尾行解析为 dict(只读尾部 chunk,容忍半行/损坏)。"""
    try:
        with open(path, 'rb') as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - chunk))
            tail = fh.read().decode('utf-8', errors='replace')
        lines = [ln for ln in tail.splitlines() if ln.strip()]
        if not lines:
            return None
        rec = json.loads(lines[-1])
        return rec if isinstance(rec, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _run_ended() -> bool:
    """v3.5 活跃局检查(离线,纯读文件):False=有活跃局(走原双窗),True=局已终局。

    判定链(任一命中「活跃」即返回 False):
      1. runs.jsonl 尾行无 result(终局记录缺失/文件不可读)→ 可能有局在跑;
      2. outcomes.jsonl 尾行 run_id ≠ runs 尾行 run_id → 更新的局已产出回合记录;
      3. outcomes.jsonl 近 OUTCOME_FRESH_SEC 内有更新(新局开局初期未写终局记录)。
    12:51 误报场景:runs 尾行 = run_20260825_115418 result=loss(已终局),
    outcomes 尾行同 run_id 且 mtime 陈旧 → 判 ended → IDLE 优雅退出。
    """
    last_run = _jsonl_tail(RUNS_JSONL)
    if last_run is None or not last_run.get('result'):
        return False  # 无终局记录 → 按活跃处理(保守,不弱化局中告警)
    last_outcome = _jsonl_tail(OUTCOMES_JSONL)
    if last_outcome is not None:
        if last_outcome.get('run_id') != last_run.get('run_id'):
            return False  # 更新的局在产出回合 → 活跃
        try:
            if time.time() - OUTCOMES_JSONL.stat().st_mtime < OUTCOME_FRESH_SEC:
                return False  # 回合记录刚更新过 → 活跃(开局初期兜底)
        except OSError:
            pass
    return True


# ── v4.0 循环检测状态(模块级,watch/replay 共用)──────────────────────
loop_recent: deque[tuple[int, str]] = deque()     # (tod, sig) 白名单动作行
loop_progress: deque[int] = deque()               # 实质推进 tod
loop_last_rp: tuple[int, int] | None = None       # 最近一次 state 行的 (round, plane)
loop_sig_lines: dict[str, deque[str]] = {}        # sig → 该签名最近原始行(证据摘录)


def _loop_prune(now_tod: int) -> None:
    """动作行按 LOOP_WIN 剪;推进事件按 LOOP_STALE 剪(阻断时效≠计数窗口)。"""
    while loop_recent and _delta(loop_recent[0][0], now_tod) > LOOP_WIN:
        loop_recent.popleft()
    while loop_progress and _delta(loop_progress[0], now_tod) > LOOP_STALE:
        loop_progress.popleft()


def _loop_feed(line: str, tod: int) -> str | None:
    """v4.0 循环检测喂行:返回报警签名(或 None)。

    实质推进(任一)记入 loop_progress,窗口内有推进即不判循环:
      ①plan 结果行含非零 买/升/刷/卖;②state 行 round/plane 变化;③「进位面」。
    白名单动作行记入 loop_recent;窗口内零推进且同签名 ≥ LOOP_N → 报警。
    """
    global loop_last_rp
    progressed = False
    if any(k in line for k in PLAN_LINE) and NONZERO_RE.search(line):
        progressed = True
    m = STATE_GATE in line or 'on_round_end' in line
    if m:
        rm_ = ROUND_RE.search(line)
        pm_ = PLANE_RE.search(line)
        if rm_ and pm_:
            rp = (int(rm_.group(1)), int(pm_.group(1)))
            if loop_last_rp is not None and rp != loop_last_rp:
                progressed = True   # round 递增 = 过轮;变化(含回绕)= 新局/进位面
            loop_last_rp = rp
    if '进位面' in line:
        progressed = True
    # 点球(奖励球收集)成功 = 实质游戏状态推进——08-25 回放实证:奖励节点无战斗
    # → 无 on_round_end,旧格式 state 行缺位,点球爆发(单轮 4-7 次)是唯一推进
    # 迹象;不认它则奖励段跨 600s 即误报(03:28/17:07 两例实证)。
    if 'ClickSpheres' in line and '→ ✓' in line:
        progressed = True
    if progressed:
        loop_progress.append(tod)
    if any(p in line for p in LOOP_PREFIXES) and '[INFO]' in line:
        s = _sig(line)
        loop_recent.append((tod, s))
        loop_sig_lines.setdefault(s, deque(maxlen=LOOP_N)).append(line.strip()[:200])
    _loop_prune(tod)
    if loop_progress:
        return None
    counts: dict[str, int] = {}
    first_tod: dict[str, int] = {}
    for t, s in loop_recent:
        counts[s] = counts.get(s, 0) + 1
        first_tod.setdefault(s, t)
        if counts[s] >= LOOP_N and _delta(first_tod[s], t) >= LOOP_SPAN_MIN:
            return s
    return None


def _loop_stop() -> str:
    """自动处置:POST /game/stop(MCP HTTP,与 stop_run 同通道)。

    restart/起局永不自动——实机编排保留给主 agent(任务书铁律)。
    """
    import urllib.request
    try:
        req = urllib.request.Request(LOOP_HTTP + '/game/stop', method='POST',
                                     data=b'', headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8', errors='replace')[:300]
        return f'HTTP {resp.status}: {body}'
    except Exception as e:   # noqa: BLE001  停止失败也要把报警打出去
        return f'停止请求失败: {e!r}'


def _loop_alarm(sig: str, line_end: int | None) -> str:
    """循环报警出口:落证据文件 + (试用期外且武装时)自动 stop;返回打印文本。"""
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    excerpts = list(loop_sig_lines.get(sig, []))
    ev = [
        '# [SENTINEL-LOOP] 活跃循环卡死报警证据',
        '',
        f'- 触发时刻: {now}(检测窗口 {LOOP_WIN}s / 同签名阈值 {LOOP_N} 次)',
        f'- 卡死签名(归一化,去时间戳/数字): {sig[:150]}',
        f'- 窗口内实质推进: 0 次(无 非零买/升/刷/卖,无 round/plane 变化,无进位面)',
        '',
        '## 窗口内该签名最近原始行(最多 {})'.format(LOOP_N),
    ]
    ev += [f'- {ln}' for ln in excerpts]
    ev += [
        '',
        '## 判读与建议动作(处置 SOP 见 .debug/temp/currency_war/cw_处置SOP.md)',
        '1. 先核时间戳与归属(哨兵试用期纪律:旧行重放/中途武装无上下文/局后空窗三类误报)',
        '2. 确认真卡死 → stop_run(本报警已在武装态自动发过 /game/stop)',
        '3. 残局清理: 一键 op ExitCurrencyWarMatch(全入口态) → analyze_screen 确认货币战争-大厅',
        '4. 重启 MCP server(有待加载代码时) → 重连 → 重武哨兵(删 cw_sentinel.pos)→ 起新局',
    ]
    try:
        LOOP_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        LOOP_EVIDENCE.write_text('\n'.join(ev), encoding='utf-8')
    except OSError as e:
        print(f'[sentinel] 证据文件写入失败: {e!r}', flush=True)
    stop_note = '试用期=只报警不处置(CW_SENTINEL_TRIAL=1)'
    if not LOOP_TRIAL and LOOP_AUTOSTOP and not REPLAY_MODE:
        stop_note = '已自动处置 /game/stop → ' + _loop_stop()
    msg = (f'[SENTINEL-LOOP] 近{LOOP_WIN}s同签名动作行≥{LOOP_N}次且零实质推进'
           f'(活跃循环卡死,run24 形态): {sig[:120]} | 证据={LOOP_EVIDENCE} | {stop_note}')
    if line_end is not None:
        try:
            MARKER.write_text(str(line_end))
        except OSError:
            pass
    return msg


# ── 行处理核心(watch 主循环与 --replay 共用)─────────────────────────
_seen_terminal = False   # 武装后是否见过 run 终态行(执行成功/人工结束/执行失败)
_seen_quiet_noted = False  # 交接窗口提示是否已打印(防每5s刷屏;新行到来时重置)
_confirm_deadline = 0.0


def process_line(line: str, line_end: int | None) -> str | None:
    """喂一行日志;返回报警消息(进程应退出)或 None。

    语义与 v3.8 内联版逐位一致(PATTERNS→HIT / WARNING·ERROR→STALL / 静默
    状态由 watch 循环管理),新增 v4.0 LOOP 分支。
    """
    global _seen_terminal
    _t = _tod(line)
    if _t is not None and not REPLAY_MODE:
        # 水位竞态防线(04:16 实证):pos 落后真实消费点 → 旧行重放;
        # 行时间戳与当前时刻差 >10min 判旧跳过(不告警不计数)。
        _now = time.localtime()
        _now_tod = _now.tm_hour * 3600 + _now.tm_min * 60 + _now.tm_sec
        if (_now_tod - _t) % 86400 > 600:
            return None
    if any(p in line for p in PATTERNS):
        return f'[SENTINEL-HIT] {line.strip()}'
    if ('执行成功' in line or '人工结束' in line or '执行失败' in line) \
            and ('指令[' in line or 'app' in line.lower()):
        _seen_terminal = True   # run 生命周期行(粗粒度:区分「run 在」与「run 完」)
    _tod_v = _tod(line)
    if _tod_v is None:
        return None
    if '[WARNING]' in line or '[ERROR]' in line:
        recent.append((_tod_v, _sig(line)))
        _prune(_tod_v)
        bad = _stall_sig(_tod_v)
        if bad:
            span = _delta(recent[0][0], _tod_v)
            return (f'[SENTINEL-STALL] 近{span}秒同特征行≥{STALL_N}且无推进: {bad[:120]}')
    elif any(p in line for p in PROGRESS):
        progress_tods.append(_tod_v)
        _prune(_tod_v)
    # v4.0 活跃循环卡死(所有日志级别之外独立计数;WARNING 分支已 return 前处理)
    loop_bad = _loop_feed(line, _tod_v)
    if loop_bad:
        # 局已终局(runs.jsonl 有 result)则抑制——08-25 17:07 实证:局末/server
        # 重启间隙,窗口残留旧动作行 + 无新推进,非卡死(与 SILENCE 分支同源守卫;
        # replay 模式不做此查——历史回放时 runs.jsonl 是当前态,不代表历史时刻)。
        if not REPLAY_MODE and _run_ended():
            print(f'[sentinel-loop-suppress] 循环特征命中但活跃局检查判定局已终局'
                  f'(残留窗口),清窗继续: {loop_bad[:80]}', flush=True)
            loop_recent.clear()
            loop_sig_lines.clear()
            return None
        return _loop_alarm(loop_bad, line_end)
    return None


recent: deque[tuple[int, str]] = deque()  # (tod, sig) 仅 WARNING/ERROR
progress_tods: deque[int] = deque()  # 推进行时间


def _prune(now_tod: int) -> None:
    while recent and _delta(recent[0][0], now_tod) > STALL_WIN:
        recent.popleft()
    while progress_tods and _delta(progress_tods[0], now_tod) > STALL_WIN:
        progress_tods.popleft()


def _stall_sig(now_tod: int) -> str | None:
    """窗口内有推进行 → 不判卡死;否则查同签名堆积是否达阈值。"""
    if progress_tods:
        return None
    counts: dict[str, int] = {}
    for _, s in recent:
        counts[s] = counts.get(s, 0) + 1
        if counts[s] >= STALL_N:
            return s
    return None


def _replay(path: str) -> int:
    """历史日志回放:全文件喂 process_line,打印全部 LOOP 报警位点(验证用)。

    每报警后清空循环窗口,同一卡死段只报一次;HIT/STALL 同样打印(观察面)。
    """
    global REPLAY_MODE
    REPLAY_MODE = True
    p = Path(path)
    n = 0
    alarms: list[tuple[str, str]] = []
    with p.open(encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            n += 1
            msg = process_line(raw, None)
            if msg:
                ts = TS_RE.match(raw)
                alarms.append((ts.group(0) if ts else f'line{n}', msg))
                if '[SENTINEL-LOOP]' in msg:
                    # 清窗:同一卡死段只报一次(真哨兵报警即退出)。非 LOOP 报警
                    # (HIT 等)不清窗——回放目的是循环检测器标定,历史 Traceback
                    # 不该掩盖循环报警时点(真哨兵遇 HIT 会退出,那是另一信道)。
                    loop_recent.clear()
                    loop_progress.clear()
                recent.clear()
                progress_tods.clear()
    print(f'[replay] {p.name}: {n} 行, 报警 {len(alarms)} 次')
    for ts, msg in alarms:
        print(f'  @{ts} {msg[:200]}')
    return 0 if True else 1


def _selftest() -> int:
    """v4.0 内置回归:局后空窗/局中静默/信道漂移/活跃循环/正常推进不误报。"""
    import subprocess
    import tempfile

    script = Path(__file__).resolve()
    cases = []
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_st_') as td:
        tdp = Path(td)
        now = time.localtime()
        hms = f'[{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}]'
        # 共用:局中日志若干行后静默(时间戳用当前时刻,绕过 stale-line 跳过)
        log_lines = ''.join([
            f'{hms} [operation.py 431] [INFO]: 指令[ 货币战争-对局循环 ] 节点 检测游戏窗口 -> 对局循环 返回状态 等待\n',
            f'{hms} [onnx_ocr_matcher.py 472] [DEBUG]: OCR结果 [] 耗时 0.27\n',
        ])
        for name, runs_tail, outcomes_tail, expect in (
            # 局后空窗:终局记录已落,无更新局 → IDLE(12:51 场景)
            ('idle_after_run',
             '{"run_id": "run_x", "result": "loss"}\n',
             '{"run_id": "run_x", "round_num": 3}\n',
             '[RUN-ENDED-IDLE]'),
            # 局中静默:终局记录缺 result → 活跃 → 双窗后仍报 SILENCE
            ('active_run_silence',
             '{"run_id": "run_y", "result": ""}\n',
             '{"run_id": "run_y", "round_num": 1}\n',
             '[SENTINEL-SILENCE]'),
        ):
            d = tdp / name
            d.mkdir()
            log = d / 'log.txt'
            log.write_text(log_lines, encoding='utf-8')
            (d / 'runs.jsonl').write_text(runs_tail, encoding='utf-8')
            (d / 'outcomes.jsonl').write_text(outcomes_tail, encoding='utf-8')
            # outcomes mtime 回拨 1h,排除 FRESH 兜底干扰
            old = time.time() - 3600
            os.utime(d / 'outcomes.jsonl', (old, old))
            env = dict(os.environ,
                       CW_SENTINEL_LOG=str(log), CW_SENTINEL_POS=str(d / 'pos'),
                       CW_SENTINEL_LOCK=str(d / 'lock'),
                       CW_SENTINEL_RUNS=str(d / 'runs.jsonl'),
                       CW_SENTINEL_OUTCOMES=str(d / 'outcomes.jsonl'),
                       CW_SENTINEL_SILENCE='3', CW_SENTINEL_CONFIRM='3',
                       CW_SENTINEL_POLL='1')
            r = subprocess.run([sys.executable, str(script)], env=env,
                               capture_output=True, text=True, timeout=120,
                               encoding='utf-8', errors='replace')
            out = r.stdout + r.stderr
            ok = expect in out and (expect != '[SENTINEL-SILENCE]' or '[RUN-ENDED-IDLE]' not in out)
            cases.append((name, expect, ok, out.strip().splitlines()[-1] if out.strip() else ''))
    for name, expect, ok, last in cases:
        print(f"  {'PASS' if ok else 'FAIL'} {name}: 期望 {expect} | 尾行: {last[:110]}")
    # v3.7 信道漂移回归:武装时盯 A,B 为旧 mtime;武装后 B 被写入(变最新)→
    # 静默分支周期重探测应切换到 B(打印漂移行),随后按新信道静默走 IDLE 退出。
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_drift_') as td:
        d = Path(td)
        log_a = d / 'log_a.txt'
        log_b = d / 'log_b.txt'
        log_a.write_text(log_lines, encoding='utf-8')
        log_b.write_text('', encoding='utf-8')
        old = time.time() - 3600
        os.utime(log_b, (old, old))   # B 初始陈旧 → 武装时选 A
        (d / 'runs.jsonl').write_text('{"run_id": "run_z", "result": "loss"}\n', encoding='utf-8')
        (d / 'outcomes.jsonl').write_text('{"run_id": "run_z", "round_num": 2}\n', encoding='utf-8')
        os.utime(d / 'outcomes.jsonl', (old, old))
        env = dict(os.environ,
                   CW_SENTINEL_LOG=str(log_a), CW_SENTINEL_LOG2=str(log_b),
                   CW_SENTINEL_POS=str(d / 'pos'), CW_SENTINEL_LOCK=str(d / 'lock'),
                   CW_SENTINEL_RUNS=str(d / 'runs.jsonl'),
                   CW_SENTINEL_OUTCOMES=str(d / 'outcomes.jsonl'),
                   CW_SENTINEL_SILENCE='8', CW_SENTINEL_CONFIRM='3',
                   CW_SENTINEL_REPROBE='2')
        proc = subprocess.Popen([sys.executable, str(script)], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding='utf-8', errors='replace')
        time.sleep(1.5)   # 等子进程完成武装(盯 A)
        log_b.write_text(log_lines, encoding='utf-8')   # B 变最新 → 触发漂移
        try:
            out_b, _ = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
            out_b, _ = proc.communicate()
        out = out_b or ''
        ok = '日志信道漂移' in out and '[RUN-ENDED-IDLE]' in out and '[SENTINEL-SILENCE]' not in out
        last = out.strip().splitlines()[-1] if out.strip() else ''
        print(f"  {'PASS' if ok else 'FAIL'} channel_drift: 期望 漂移切换+IDLE | 尾行: {last[:110]}")
        cases.append(('channel_drift', '日志信道漂移', ok, last))
    # v4.0 活跃循环回归(--replay 路径,不占锁不起线程):直接子进程跑 --replay
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_loop_') as td:
        d = Path(td)
        base = time.localtime()
        def ts(sec_off: int) -> str:
            t = time.struct_time((base.tm_year, base.tm_mon, base.tm_mday,
                                  base.tm_hour, base.tm_min, base.tm_sec,
                                  0, 0, 0))
            ep = time.mktime(t) + sec_off
            lt = time.localtime(ep)
            return f'[{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}]'
        # 案1 run24 形态:11 轮同循环(state 行 round/plane 恒定 + 同签名动作行)
        lines = []
        for i in range(11):
            t = ts(i * 55)
            lines.append(f'{t} [shop.py 394] [INFO]: [cw] state gold=24 hp=84 lv=4 round=3 node=? plane=1 board={{}} target=\'\' fp=-1.00 bench=2\n')
            lines.append(f'{t} [prep_director.py 633] [INFO]: [cw][director] step2 RunDeploy → ✓ 部署 已部署角色\n')
            lines.append(f'{t} [battle_loop.py 890] [INFO]: [cw-loop] 前台无角色提示 → 确认关闭(下轮 PrepDirector 前排保证重部署)\n')
        # 案2 正常局:12 轮,每轮 state 行 round 递增 + 偶发非零买 → 不报警
        lines2 = []
        for i in range(12):
            t = ts(i * 55)
            lines2.append(f'{t} [shop.py 394] [INFO]: [cw] state gold=24 hp=84 lv=4 round={i + 1} node=? plane=1 board={{}} target=\'\' fp=-1.00 bench=2\n')
            lines2.append(f'{t} [prep_director.py 633] [INFO]: [cw][director] step1 RunBuyPhase → ✓ 买牌 plan 买{i % 3}张 升0次 刷0次 卖0张(gold=24 lv=4 plane=1)\n')
            lines2.append(f'{t} [prep_director.py 633] [INFO]: [cw][director] step2 RunDeploy → ✓ 部署 已部署角色\n')
        for name, text, expect_loop in (
            ('loop_stuck_run24', ''.join(lines), True),
            ('normal_progress_nofp', ''.join(lines2), False),
        ):
            log = d / f'{name}.txt'
            log.write_text(text, encoding='utf-8')
            env = dict(os.environ, CW_SENTINEL_LOOP_EVIDENCE=str(d / f'{name}_ev.md'))
            r = subprocess.run([sys.executable, str(script), '--replay', str(log)],
                               env=env, capture_output=True, text=True, timeout=60,
                               encoding='utf-8', errors='replace')
            out = r.stdout + r.stderr
            has = '[SENTINEL-LOOP]' in out
            ok = has == expect_loop
            last = out.strip().splitlines()[-1] if out.strip() else ''
            print(f"  {'PASS' if ok else 'FAIL'} {name}: 期望 {'LOOP报警' if expect_loop else '零报警'} | 尾行: {last[:110]}")
            cases.append((name, 'LOOP' if expect_loop else 'no-LOOP', ok, last))
    return 0 if all(c[2] for c in cases) else 1


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    print('[selftest] v4.0 局后空窗/局中静默/信道漂移/活跃循环/正常推进 回归')
    sys.exit(_selftest())

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--replay':
    if len(sys.argv) < 3:
        print('用法: cw_sentinel.py --replay <日志文件>', flush=True)
        sys.exit(2)
    sys.exit(_replay(sys.argv[2]))

if not REPLAY_MODE and not _acquire_lock():
    sys.exit(0)
# pos 残留防线(W133 低危②):单实例锁生效后,武装时见到的 pos 只可能来自已死
# 前实例(报警退出写 fh.tell() / 被 kill 未写)——mtime 陈旧(>10min)的 pos 与
# 锁保护下的「本实例上次心跳」必然不匹配,按残留处理重置到 EOF,防旧行回放。
# 新鲜 pos 仍信任(显式分支:v2 的 and/or 链在 pos=0 时回落 EOF 的潜伏 bug 保留修复)。
start_pos = None
if MARKER.exists():
    try:
        if time.time() - MARKER.stat().st_mtime <= 600:
            start_pos = int(MARKER.read_text().strip())
    except (ValueError, OSError):
        pass
if start_pos is None:
    start_pos = LOG.stat().st_size
print(f'[sentinel] armed v4.0 @ {time.strftime("%H:%M:%S")}, pos={start_pos}, '
      f'log={LOG}, loop(N={LOOP_N},win={LOOP_WIN}s,trial={LOOP_TRIAL})', flush=True)

last_line_wall = time.time()


# v3.8(2026-08-26 02:2x 轮转锁死修,根因实锤):原实现长持有日志句柄(readline
# 尾随)——Windows 下开着句柄挡 os.rename,server 的 TimedRotatingFileHandler
# 午夜滚转 PermissionError(WinError 32,日志 Traceback 实锤:轮转 rename 被本
# 哨兵的句柄挡住)。改**短开轮询**:每 POLL_SEC 开→seek→读新增→关,全程不持
# 句柄;外部轮转(rename/截断)由 size<pos 判据捕获。行处理语义逐位保留
# (陈旧行防线/HIT/STALL/LOOP/静默双窗/信道重探测)。
POLL_SEC = float(os.environ.get('CW_SENTINEL_POLL', '5'))
pos = start_pos
_log_path = LOG            # 当前活信道(漂移切换后更新)
_last_probe = time.time()  # 上次信道重探测时刻
_buf = ''                  # 尾部半行(写入中),下轮拼接
_skipped_stale = 0


def _read_new_lines() -> list[tuple[str, int]]:
    """短开读新增行:返回 [(行文本含换行, 行尾偏移)];轮转重置从头。

    行尾偏移按解码后字节累计,损坏字节被 errors='replace' 替换的场景可能偏
    几字节——只用于 MARKER(重武装位点),偏差无害(最多重读半行被解析跳过)。
    """
    global pos, _buf
    try:
        size = _log_path.stat().st_size
    except OSError:
        return []
    if size < pos:   # 日志轮转/截断重写(重建变小)→ 从头读
        print('[sentinel] 日志轮转,重置窗口', flush=True)
        pos = 0
        _buf = ''
        recent.clear()
        progress_tods.clear()
        loop_recent.clear()
        loop_progress.clear()
        return []
    if size == pos:
        return []
    try:
        with open(_log_path, 'rb') as fh:
            fh.seek(pos)
            data = fh.read()
    except OSError:
        return []
    chunk_start = pos
    pos += len(data)
    text = _buf + data.decode('utf-8', errors='replace')
    cut = text.rfind('\n') + 1
    _buf = text[cut:]
    out: list[tuple[str, int]] = []
    off = chunk_start
    for ln in text[:cut].splitlines():
        off += len(ln.encode('utf-8', errors='replace')) + 1
        out.append((ln + '\n', off))
    return out


while True:
    _lines = _read_new_lines()
    if _lines:
        last_line_wall = time.time()
        _seen_quiet_noted = False
    for _line, _line_end in _lines:
        _msg = process_line(_line, _line_end)
        if _msg:
            print(_msg, flush=True)
            MARKER.write_text(str(_line_end))
            sys.exit(0)
    if not _lines:
        # 信道周期重探测(2026-08-26 run 17 实证):仅在静默分支每 REPROBE_SEC
        # 重跑 _pick_log();活信道变了 → 切到新文件当前尾(不回读历史),窗口
        # 清空,静默计时重新起算(防切换瞬间误报)。
        if time.time() - _last_probe >= REPROBE_SEC:
            _last_probe = time.time()
            _cand = _pick_log()
            if _cand != _log_path:
                try:
                    _new_size = _cand.stat().st_size
                except OSError:
                    _new_size = None
                if _new_size is not None:
                    print(f'[sentinel] 日志信道漂移 {_log_path} → {_cand},切换', flush=True)
                    _log_path = _cand
                    pos = _new_size
                    _buf = ''
                    recent.clear()
                    progress_tods.clear()
                    loop_recent.clear()
                    loop_progress.clear()
                    last_line_wall = time.time()
                    _seen_quiet_noted = False
                    _skipped_stale = 0
        MARKER.write_text(str(pos))  # pos 每轮更新 = 心跳(watchdog 用)
        if time.time() - last_line_wall > SILENCE_SEC:
            # v3.5(12:51 误报修):静默判定前先做「活跃局检查」(离线读
            # replay/runs.jsonl + outcomes.jsonl)。局已自然终局 → 局后空窗
            # 是正常交接状态,IDLE 提示 + 优雅退出,不走 SILENCE 报警;
            # 局仍活跃 → 维持原双窗逻辑(结算屏/动画段误报防护不弱化)。
            if _run_ended():
                _last = _jsonl_tail(RUNS_JSONL) or {}
                print(f'[RUN-ENDED-IDLE] 静默{int(time.time()-last_line_wall)}s 且活跃局检查判定'
                      f'局已终局(runs.jsonl 尾行 result={_last.get("result", "?")})'
                      f'——局后空窗属正常交接,哨兵退出不报警', flush=True)
                sys.exit(0)
            if _seen_terminal:
                # v3.3:quiet 提示只打一次(21 分钟刷屏实战实证);新行到来时重置。
                if not _seen_quiet_noted:
                    print(f'[sentinel-quiet] run 已结束,{int(time.time()-last_line_wall)}s 静默属交接窗口,继续等(新局日志会恢复输出)', flush=True)
                    _seen_quiet_noted = True
            else:
                # v3.4(三连误报修):结算屏/长动画等待段本就静默 300-600s——
                # 静默满 SILENCE 后再等 SILENCE_CONFIRM 二次窗,期间无任何新行
                # 才报;真僵死两窗皆静默照报不漏。
                if not _seen_quiet_noted:
                    _confirm_deadline = time.time() + SILENCE_CONFIRM
                    _seen_quiet_noted = True
                    print(f'[sentinel-watch] 静默{int(time.time()-last_line_wall)}s>={SILENCE_SEC}s '
                          f'(v3.4:结算/动画等待段常见误源)——进入二次确认窗 '
                          f'{SILENCE_CONFIRM}s,期间新行即解除', flush=True)
                elif time.time() >= _confirm_deadline:
                    # 二次确认到期再查一次活跃局:静默期间终局记录可能刚落盘。
                    if _run_ended():
                        print('[RUN-ENDED-IDLE] 二次确认窗到期,活跃局检查判定局已终局'
                              '——局后空窗属正常交接,哨兵退出不报警', flush=True)
                        sys.exit(0)
                    print(f'[SENTINEL-SILENCE] 静默{int(time.time()-last_line_wall)}s '
                          f'(含二次确认窗 {SILENCE_CONFIRM}s 无输出,进程级异常确认)', flush=True)
                    sys.exit(0)
    time.sleep(POLL_SEC)
