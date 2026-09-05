"""r229c 事件哨兵 v5(v4 循环/静默 + STALL 推进语义修复 + 节点滞留检测)。

## 检测面(当前语义)

- [SENTINEL-HIT]:崩溃/停机类关键事件(PATTERNS),命中即退出推送。
- [SENTINEL-STALL]:近 STALL_WIN 秒同特征 WARNING/ERROR 行 ≥ STALL_N 次
  且窗口内**零实质推进**(实质推进判据见下,与 LOOP 分支共用单一源)。
- [SENTINEL-LOOP]:近 LOOP_WIN 秒白名单定向动作行同一归一化签名 ≥ LOOP_N 次、
  跨度 ≥ LOOP_SPAN_MIN,且 LOOP_STALE 内零实质推进(活跃循环卡死)。
- [SENTINEL-NODE-DWELL](v5 新增):同一(位面,轮次)相位被持续观测超过
  DWELL_SEC(默认 900s,env CW_SENTINEL_DWELL_SEC)→ 报警。
  数据源 = state 行(`[cw] state gold=... plane=N round=M node=X`,
  cw_op_buy_cards 发出)与 on_round_end 行(两处都带 plane/round)。
  相位变化即重置计时;判「相位持续」用**首末观测跨度**(last-first ≥ 阈值),
  不是 now-first——战斗/长动画段没有 state 行,那段时间不该计入备战滞留。
  2026-09-03 实证:1-1 节点(reward)卡死 22:30-23:11+,state 行每 ~25s 一条、
  plane=1 round=1 恒定 40min+,跨度判据在 ~22:45(阈值 900s)即可独立报警。
  nodeseq 行(`[cw-director][nodeseq]`)只带位面不带轮次,不作相位源。

## 实质推进(STALL/LOOP 两分支单一判据,2026-09-03 语义修复)

无操作成功**不算推进**。计为推进的只有:
  ① plan 结果行含非零动作:现行流程行 = `[cw][director] OpenShop(...) → ✓
     买牌 plan 买N张 升N次 刷N次 卖N张`(买/升/刷/卖 全 0 = 纯读店空转,
     1-1 卡死循环每 ~23s 一条,旧 PROGRESS 子串判据把它当推进 → STALL
     整局失明);判词用 NONZERO_RE(只认 ≥1 的动作数)。
  ② `[cw][composite]` 复合动作成功(部署/装备等真实执行,prep_actions 发出)。
  ③ state 行/on_round_end 的 round/plane 变化(含新局回绕);「进位面」。
  ④ 点球收集成功(ClickSpheres → ✓,奖励节点无战斗时的唯一推进迹象,
     08-25 回放实证 03:28/17:07 两例缺它误报)。
刻意不算:「→ ✓」「执行成功」「出战成功」等裸成功字样——run 24 实证弹窗
误判下「出战成功」每轮假成功;1-1 卡死实证「OpenShop → ✓」每轮假成功。

## 版本历史(标定依据随版本保留)

| 版本 | 增量 | 标定依据 |
|---|---|---|
| v2 | 只报需介入事件,例行 WARNING 不报 | 第一版把对账纠漂也报了,噪声淹没真警报 |
| v3 | 重复行堆积 STALL + 静默双窗 | 局47 教训 50min 才停;结算/动画段静默 300-600s 三连误报(2026-08-25) |
| v3.4/3.5 | 静默二次确认窗 + 局后空窗 IDLE | 12:51 局后空窗误报 |
| v3.8 | 短开轮询 + 信道周期重探测 | Windows 午夜轮转 rename 被句柄挡死;run 17 信道漂移 |
| v4.0 | 活跃循环卡死 LOOP + 试用期纪律 | run 24 出战被拒循环 53min;参数 N=10/win=1500s/span≥300s/stale=600s(首报警比人工早 ~44min) |
| v4.1 | 活跃局判定第 4 条(decisions 新鲜度) | 2026-09-03 1-1 卡死 26min 零报警:runs/outcomes 双陈旧误判「已终局」,LOOP 整局被 suppress |
| v5 | STALL 推进语义修复(无操作成功≠推进)+ 节点滞留 NODE-DWELL + 词汇审计(见下) | 2026-09-03 1-1 卡死段实机日志回放标定 |

## 词汇审计(v5,对照流程侧代码与 .log/mcp_server.log 全文 grep)

在岗:『Traceback/TypeError/AttributeError/StopIteration』(框架执行出错栈,
log 387 次全是真崩溃栈);『执行失败』(operation.py:695);『STOPPED』
(RunState.STOPPED 终态行);『超时』(log 4 次,均为「对局循环超时→执行失败」
真故障);『stall_watch』(cw_loop.py:366 停滞哨兵警告行);『停机待建档』
(cw_loop.py:1401 round_fail 状态,未触发过,保留);『state gold=』
(cw_op_buy_cards.py:614);『[cw-loop]』『[cw][battle]』『[cw-deploy]』
(cw_loop.py/prep_actions.py/cw_op_deploy.py);『[cw][director]』
(现行 plan 结果行 OpenShop 由 prep_director 发出)。
已死删除:『人工结束』(operation.py:410 注释实证已被 stop_source 机制取代,
全文 grep 0 命中,STOPPED 覆盖同事件);『返回状态 plan』『step1/step2
RunBuyPhase』『[cw][director] step』(W971 备战 step 机→序列契约迁移前的旧核
词汇,全文 grep 0 命中);旧 PROGRESS 元组(『→ ✓』『执行成功』子串判据,
v5 语义修复的根)。
降级保留:『plan_error』当前只写 decisions.jsonl 不进 log(0 命中),留作
决策崩溃日志措辞的兜底,零成本。
刻意不入 LOOP 白名单:『[cw][observe_full]』『[cw][node_votes]』
『[cw-director][nodeseq]』——三者是观测行不是定向动作行,健康局每备战环也
高频出现;1-1 卡死段已被 [cw-loop]+[cw][director] 动作行完全覆盖
(回放实证 22:35 即触发),纳入只扩误报面不补检测缺口。

## 运行环境

日志时间戳无日期(跨天 append),窗口按 HH:MM:SS 回绕计算;
日志轮转(文件变小)时从头读并重置窗口。
离线自测: 环境变量 CW_SENTINEL_LOG / CW_SENTINEL_POS 重定向日志与水位路径;
  CW_SENTINEL_REPLAY_DIR(或 CW_SENTINEL_RUNS / CW_SENTINEL_OUTCOMES)重定向
  活跃局判定文件;CW_SENTINEL_SILENCE / CW_SENTINEL_CONFIRM /
  CW_SENTINEL_DWELL_SEC 覆盖阈值(仅自测)。
  python cw_sentinel.py --selftest: 内置回归(局后空窗→IDLE / 局中静默→SILENCE /
  信道漂移 / 活跃循环→LOOP / 无操作成功循环→STALL 不被假推进掩盖 /
  节点滞留→NODE-DWELL / 正常推进→不误报)。
  python cw_sentinel.py --replay <日志文件>: 历史日志回放——全文件喂行处理逻辑,
  打印全部报警位点(每卡死段一次;不退出不 stop,验证用)。
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
# v4.1 活跃局判定第 4 条:活跃局每备战环落决策帧,decisions 新鲜=局在跑。
DECISIONS_JSONL = Path(os.environ.get(
    'CW_SENTINEL_DECISIONS', str(_REPLAY_DIR / 'decisions.jsonl')))
DECISIONS_FRESH_SEC = int(os.environ.get('CW_SENTINEL_DECISIONS_FRESH', 600))

# v2 原样:只报需介入的事件(第一版把对账纠漂/MISS 例行也报了,噪声淹没真警报)。
# 词汇审计(v5)见文件头;『人工结束』『plan_error』处置理由亦在头注。
PATTERNS = (
    'Traceback',
    'plan_error',
    '执行失败',
    '停机待建档',
    'STOPPED',
    '超时',
    'stall_watch',
    'TypeError',
    'AttributeError',
    'StopIteration',
)
STALL_WIN = 600    # 卡死判定窗口(秒)
STALL_N = 10       # 同特征行阈值
SILENCE_SEC = int(os.environ.get('CW_SENTINEL_SILENCE', 360))  # 静默死锁阈值(秒)
SILENCE_CONFIRM = int(os.environ.get('CW_SENTINEL_CONFIRM', 420))  # v3.4:二次确认窗
OUTCOME_FRESH_SEC = 900  # v3.5:outcomes 近此窗口内有更新 → 视为有活跃局

# ── 实质推进判据(v5,STALL/LOOP 单一源;详见文件头「实质推进」节)──────
# plan 结果行:现行流程 = prep_director 发出的 OpenShop 行;旧核
# 『返回状态 plan』『step1/step2 RunBuyPhase』已随 W971 迁移死亡(全文 grep 0)。
PLAN_LINE = ('[cw][director] OpenShop',)
# 非零动作计数(买N张/升N次/刷N次/卖N张,N≥1);全 0 形态不匹配 = 无操作成功。
NONZERO_RE = re.compile(r'[买升刷卖][1-9]\d*')

# ── v4.0 活跃循环卡死(W180,run 24 标定)─────────────────────────────
LOOP_WIN = int(os.environ.get('CW_SENTINEL_LOOP_WIN', 1500))  # 循环判定窗口(秒)
LOOP_N = int(os.environ.get('CW_SENTINEL_LOOP_N', 10))        # 同签名阈值
# 只数定向动作行(白名单前缀)——OCR/obs 冲突行天然秒级重复,数它们必误报;
# 「对局循环 返回状态 等待」每秒多条,同样排除。词汇审计(v5):
# 『[cw][director] step』已死,由现行 plan 行前缀『[cw][director]』取代;
# 观测行(observe_full/node_votes/nodeseq)刻意不入,理由见文件头。
LOOP_PREFIXES = ('[cw][director]', '[cw-loop]', '[cw][battle]', '[cw-deploy]')
# 实质推进:轮次推进(round/plane 变化;round 减小 = 新局,也是推进)。
# 两种日志形态都认(2026-08-25/26 实测):
#   ① shop 决策行 'state gold=24 hp=84 lv=4 plane=1 round=3 ...'(cw_op_buy_cards);
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

# ── v5 节点滞留(NODE-DWELL;1-1 卡死 26min 实证驱动)──────────────────
# 同一(位面,轮次)相位持续观测超阈值 → 报警。阈值 900s 校准:健康局同一
# 相位的备战观测跨度 ≤5min/轮(20:42-21:19 健康局 round 变化间隔 3-5min),
# 900s 留 3 倍裕度;卡死段首报警=卡死起点+900s(22:30 起 → ~22:45),比
# 人工介入(23:1x)早 ~30min。判「持续」用首末观测跨度,战斗段无 state 行
# 不计入(见文件头 NODE-DWELL 节)。
DWELL_SEC = int(os.environ.get('CW_SENTINEL_DWELL_SEC', 900))
NODE_DWELL_EVIDENCE = Path(os.environ.get(
    'CW_SENTINEL_DWELL_EVIDENCE',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\cw_node_dwell_alert.md'))

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
      3. outcomes.jsonl 近 OUTCOME_FRESH_SEC 内有更新(新局开局初期未写终局记录);
      4. decisions.jsonl 近 DECISIONS_FRESH_SEC 内有更新(v4.1,2026-09-03
         实证缺陷:runs 行局终才写,旧局尾行 result 在位+outcomes 同 id
         陈旧 ⇒ 整个新对局期间被误判「已终局」,LOOP 报警整局被 suppress
         ——备战环卡死 26 分钟零报警;活跃局备战环每轮落决策帧,
         mtime 新鲜即可靠区分)。
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
    try:
        if time.time() - DECISIONS_JSONL.stat().st_mtime < DECISIONS_FRESH_SEC:
            return False  # 决策帧刚更新 → 活跃局(v4.1,见判定链 4)
    except OSError:
        pass
    return True


def _write_evidence(path: Path, title: str, body: list[str]) -> None:
    """报警证据落盘(LOOP/DWELL 共用;失败只打印不抛,报警不能因 IO 丢)。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join([f'# {title}', ''] + body), encoding='utf-8')
    except OSError as e:
        print(f'[sentinel] 证据文件写入失败: {e!r}', flush=True)


# ── v4.0/v5 循环与滞留检测状态(模块级,watch/replay 共用)────────────
loop_recent: deque[tuple[int, str]] = deque()     # (tod, sig) 白名单动作行
loop_progress: deque[int] = deque()               # 实质推进 tod
loop_last_rp: tuple[int, int] | None = None       # 最近一次 state 行的 (round, plane)
loop_sig_lines: dict[str, deque[str]] = {}        # sig → 该签名最近原始行(证据摘录)
# v5 节点滞留:当前相位 (plane, round) 的首/末观测时刻(None=尚无相位)
dwell_phase: tuple[int, int] | None = None
dwell_first: int | None = None
dwell_last: int | None = None
dwell_last_line: str = ''                         # 相位内最近一条 state 行(证据)


def _loop_prune(now_tod: int) -> None:
    """动作行按 LOOP_WIN 剪;推进事件按 LOOP_STALE 剪(阻断时效≠计数窗口)。"""
    while loop_recent and _delta(loop_recent[0][0], now_tod) > LOOP_WIN:
        loop_recent.popleft()
    while loop_progress and _delta(loop_progress[0], now_tod) > LOOP_STALE:
        loop_progress.popleft()


def _dwell_reset() -> None:
    global dwell_phase, dwell_first, dwell_last, dwell_last_line
    dwell_phase = None
    dwell_first = None
    dwell_last = None
    dwell_last_line = ''


def _loop_feed(line: str, tod: int) -> tuple[bool, str, str]:
    """循环+滞留检测喂行:返回 (实质推进?, 报警类别, 载荷)。

    实质推进(任一,记入 loop_progress;判据单一源见文件头):
      ①plan 结果行含非零 买/升/刷/卖;②[composite] 复合动作成功;
      ③state 行 round/plane 变化;④「进位面」;⑤点球收集成功。
    白名单动作行记入 loop_recent;窗口内零推进且同签名 ≥ LOOP_N(跨度达
    LOOP_SPAN_MIN)→ ('loop', 签名, '')。
    state/on_round_end 行同相位持续观测 ≥ DWELL_SEC → ('dwell', 相位描述, '')。
    无报警 → ('', '', '')。
    """
    global loop_last_rp, dwell_phase, dwell_first, dwell_last, dwell_last_line
    progressed = False
    if any(k in line for k in PLAN_LINE) and NONZERO_RE.search(line):
        progressed = True
    if '[cw][composite]' in line and '✓' in line:
        progressed = True   # 部署/装备等复合动作真实执行(prep_actions)
    phase_line = False
    if STATE_GATE in line or 'on_round_end' in line:
        rm_ = ROUND_RE.search(line)
        pm_ = PLANE_RE.search(line)
        if rm_ and pm_:
            phase_line = True
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
    # v5 节点滞留追踪(相位数据源 = state/on_round_end 行)
    if phase_line:
        nm_ = re.search(r'node=(\S+)', line)
        node = nm_.group(1) if nm_ else '?'
        cur = (int(pm_.group(1)), int(rm_.group(1)))
        if dwell_phase is not None and cur == dwell_phase:
            dwell_last = tod
            dwell_last_line = line.strip()[:200]
            if dwell_first is not None and _delta(dwell_first, tod) >= DWELL_SEC:
                return (progressed, 'dwell',
                        f'plane={cur[0]} round={cur[1]} node={node}')
        else:
            dwell_phase = cur
            dwell_first = tod
            dwell_last = tod
            dwell_last_line = line.strip()[:200]
    if any(p in line for p in LOOP_PREFIXES) and '[INFO]' in line:
        s = _sig(line)
        loop_recent.append((tod, s))
        loop_sig_lines.setdefault(s, deque(maxlen=LOOP_N)).append(line.strip()[:200])
    _loop_prune(tod)
    if loop_progress:
        return (progressed, '', '')
    counts: dict[str, int] = {}
    first_tod: dict[str, int] = {}
    for t, s in loop_recent:
        counts[s] = counts.get(s, 0) + 1
        first_tod.setdefault(s, t)
        if counts[s] >= LOOP_N and _delta(first_tod[s], t) >= LOOP_SPAN_MIN:
            return (progressed, 'loop', s)
    return (progressed, '', '')


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
        f'- 触发时刻: {now}(检测窗口 {LOOP_WIN}s / 同签名阈值 {LOOP_N} 次)',
        f'- 卡死签名(归一化,去时间戳/数字): {sig[:150]}',
        '- 窗口内实质推进: 0 次(无 非零买/升/刷/卖,无 round/plane 变化,无进位面)',
        '',
        '## 窗口内该签名最近原始行(最多 {})'.format(LOOP_N),
    ]
    ev += [f'- {ln}' for ln in excerpts]
    ev += [
        '',
        '## 判读与建议动作(处置 SOP 见 .debug/temp/currency_war/cw_处置SOP.md)',
        '1. 先核时间戳与归属(哨兵试用期纪律:旧行重放/中途武装无上下文/局后空窗三类误报)',
        '2. 确认真卡死 → stop_run(本报警已在武装态自动发过 /game/stop)',
        '3. 残局清理: 一键 op CwEntryExit(全入口态) → analyze_screen 确认货币战争-大厅',
        '4. 重启 MCP server(有待加载代码时) → 重连 → 重武哨兵(删 cw_sentinel.pos)→ 起新局',
    ]
    _write_evidence(LOOP_EVIDENCE, '[SENTINEL-LOOP] 活跃循环卡死报警证据', ev)
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


def _dwell_alarm(payload: str, line_end: int | None) -> str:
    """节点滞留报警出口(v5):落证据文件;返回打印文本。"""
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    ev = [
        f'- 触发时刻: {now}(滞留阈值 {DWELL_SEC}s,判据=同相位首末观测跨度)',
        f'- 滞留相位: {payload}',
        f'- 相位首次观测至今的日志跨度: {DWELL_SEC}s+(换相位即重置计时)',
        '- 相位内最近一条 state 行:',
        f'- {dwell_last_line}',
        '',
        '## 判读与建议动作',
        '1. 先核时间戳与归属(哨兵试用期纪律);本报警与 LOOP 互相独立,任一命中均指示节点不前进',
        '2. 确认真卡死 → stop_run;残局清理/重启/重武哨兵流程同 LOOP 报警证据文件',
    ]
    _write_evidence(NODE_DWELL_EVIDENCE, '[SENTINEL-NODE-DWELL] 节点相位滞留报警证据', ev)
    if line_end is not None:
        try:
            MARKER.write_text(str(line_end))
        except OSError:
            pass
    return (f'[SENTINEL-NODE-DWELL] 同一(位面,轮次)相位持续≥{DWELL_SEC}s'
            f'(节点滞留): {payload} | 证据={NODE_DWELL_EVIDENCE}')


# ── 行处理核心(watch 主循环与 --replay 共用)─────────────────────────
_seen_terminal = False   # 武装后是否见过 run 终态行(执行成功/执行失败)
_seen_quiet_noted = False  # 交接窗口提示是否已打印(防每5s刷屏;新行到来时重置)
_confirm_deadline = 0.0


def process_line(line: str, line_end: int | None) -> str | None:
    """喂一行日志;返回报警消息(进程应退出)或 None。

    顺序:陈旧行防线 → PATTERNS(HIT)→ run 终态标记 → 循环/滞留喂行(同时
    产出实质推进)→ STALL(零推进下的 WARNING/ERROR 堆积)→ LOOP/DWELL 报警。
    v5:STALL 的推进判据改与 LOOP 共用「实质推进」(无操作成功不算推进),
    修复 1-1 卡死段「OpenShop 买0张 → ✓」被当推进致 STALL 整局失明的缺陷。
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
    # 设计内自愈白名单(ADR-0529 修订):round_retry 复探超窗重试是复探窗
    # 的有界兜底路径(消耗 node_max_retry 预算),其日志虽走 ERROR 级但属
    # 设计内自愈,不应触发报警退出;真持续卡死由 STALL 堆积检测兜底。
    if '复探超窗重试' in line:
        return None
    if any(p in line for p in PATTERNS):
        return f'[SENTINEL-HIT] {line.strip()}'
    if ('执行成功' in line or '执行失败' in line) \
            and ('指令[' in line or 'app' in line.lower()):
        _seen_terminal = True   # run 生命周期行(粗粒度:区分「run 在」与「run 完」)
    _tod_v = _tod(line)
    if _tod_v is None:
        return None
    # v5 run 边界重置滞留计时:终局/被停行是稳定框架词汇(backend_context 固化行
    # 与 operation 停止来源行)。跨 run 同相位(旧局卡死在 1-1、新局也从 1-1 起)
    # 若不重置,滞留会把上一局的时间算进本局 → 23:29 误报实证。
    if 'terminal=RunState' in line or '已停止[' in line:
        _dwell_reset()
    # v4.0/v5 循环+滞留检测(所有日志级别之外独立计数;同时产出实质推进)
    progressed, kind, payload = _loop_feed(line, _tod_v)
    if progressed:
        progress_tods.append(_tod_v)
        _prune(_tod_v)
    if '[WARNING]' in line or '[ERROR]' in line:
        recent.append((_tod_v, _sig(line)))
        _prune(_tod_v)
        bad = _stall_sig(_tod_v)
        if bad:
            span = _delta(recent[0][0], _tod_v)
            return (f'[SENTINEL-STALL] 近{span}秒同特征行≥{STALL_N}且无实质推进: {bad[:120]}')
    if kind == 'loop':
        # 局已终局(runs.jsonl 有 result)则抑制——08-25 17:07 实证:局末/server
        # 重启间隙,窗口残留旧动作行 + 无新推进,非卡死(与 SILENCE 分支同源守卫;
        # replay 模式不做此查——历史回放时 runs.jsonl 是当前态,不代表历史时刻)。
        if not REPLAY_MODE and _run_ended():
            print(f'[sentinel-loop-suppress] 循环特征命中但活跃局检查判定局已终局'
                  f'(残留窗口),清窗继续: {payload[:80]}', flush=True)
            loop_recent.clear()
            loop_sig_lines.clear()
            return None
        return _loop_alarm(payload, line_end)
    if kind == 'dwell':
        return _dwell_alarm(payload, line_end)
    return None


recent: deque[tuple[int, str]] = deque()  # (tod, sig) 仅 WARNING/ERROR
progress_tods: deque[int] = deque()  # 实质推进时间


def _prune(now_tod: int) -> None:
    while recent and _delta(recent[0][0], now_tod) > STALL_WIN:
        recent.popleft()
    while progress_tods and _delta(progress_tods[0], now_tod) > STALL_WIN:
        progress_tods.popleft()


def _stall_sig(now_tod: int) -> str | None:
    """窗口内有实质推进 → 不判卡死;否则查同签名堆积是否达阈值。"""
    if progress_tods:
        return None
    counts: dict[str, int] = {}
    for _, s in recent:
        counts[s] = counts.get(s, 0) + 1
        if counts[s] >= STALL_N:
            return s
    return None


def _replay(path: str) -> int:
    """历史日志回放:全文件喂 process_line,打印全部报警位点(验证用)。

    每报警后清空循环/滞留窗口,同一卡死段只报一次;HIT/STALL 同样打印(观察面)。
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
                if '[SENTINEL-LOOP]' in msg or '[SENTINEL-NODE-DWELL]' in msg:
                    # 清窗:同一卡死段只报一次(真哨兵报警即退出)。非 LOOP/DWELL
                    # 报警(HIT 等)不清窗——回放目的是循环/滞留检测器标定,历史
                    # Traceback 不该掩盖循环报警时点(真哨兵遇 HIT 会退出,那是
                    # 另一信道)。
                    loop_recent.clear()
                    loop_progress.clear()
                    _dwell_reset()
                recent.clear()
                progress_tods.clear()
    print(f'[replay] {p.name}: {n} 行, 报警 {len(alarms)} 次')
    for ts, msg in alarms:
        print(f'  @{ts} {msg[:200]}')
    return 0 if True else 1


def _selftest() -> int:
    """v5 内置回归:空窗/静默/漂移/循环/无操作成功 STALL/节点滞留/正常推进。"""
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
            # decisions 也重定向+mtime 回拨:v4.1 判定链第 4 条会读真实
            # decisions.jsonl——在岗局的决策帧新鲜会把「局后空窗」用例误判活跃
            (d / 'decisions.jsonl').write_text('{"run_id": "run_x"}\n', encoding='utf-8')
            # outcomes mtime 回拨 1h,排除 FRESH 兜底干扰
            old = time.time() - 3600
            os.utime(d / 'outcomes.jsonl', (old, old))
            os.utime(d / 'decisions.jsonl', (old, old))
            env = dict(os.environ,
                       CW_SENTINEL_LOG=str(log), CW_SENTINEL_POS=str(d / 'pos'),
                       CW_SENTINEL_LOCK=str(d / 'lock'),
                       CW_SENTINEL_RUNS=str(d / 'runs.jsonl'),
                       CW_SENTINEL_OUTCOMES=str(d / 'outcomes.jsonl'),
                       CW_SENTINEL_DECISIONS=str(d / 'decisions.jsonl'),
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
        (d / 'decisions.jsonl').write_text('{"run_id": "run_z"}\n', encoding='utf-8')
        os.utime(d / 'outcomes.jsonl', (old, old))
        os.utime(d / 'decisions.jsonl', (old, old))
        env = dict(os.environ,
                   CW_SENTINEL_LOG=str(log_a), CW_SENTINEL_LOG2=str(log_b),
                   CW_SENTINEL_POS=str(d / 'pos'), CW_SENTINEL_LOCK=str(d / 'lock'),
                   CW_SENTINEL_RUNS=str(d / 'runs.jsonl'),
                   CW_SENTINEL_OUTCOMES=str(d / 'outcomes.jsonl'),
                   CW_SENTINEL_DECISIONS=str(d / 'decisions.jsonl'),
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
    # v4.0/v5 循环/STALL/滞留回归(--replay 路径,不占锁不起线程)
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
        # 案1 run24/1-1 卡死形态:11 轮同循环(state 行 round/plane 恒定 +
        # 同签名动作行,含现行 OpenShop 无操作成功行)→ LOOP
        lines = []
        for i in range(11):
            t = ts(i * 55)
            lines.append(f'{t} [shop.py 394] [INFO]: [cw] state gold=24 hp=84 lv=4 round=3 node=? plane=1 board={{}} target=\'\' fp=-1.00 bench=2\n')
            lines.append(f'{t} [prep_director.py 1338] [INFO]: [cw][director] OpenShop({{\'read_only\': False}}) → ✓ 买牌 plan 买0张 升0次 刷0次 卖0张(+0金,守卫拦0) (gold=24 lv=4 plane=1)\n')
            lines.append(f'{t} [cw_loop.py 1179] [INFO]: [cw-loop] 备战环返回(success=True status=OpenShop ✓)→ 交回顶层分发(下轮全分支重判)\n')
        # 案2 正常局:12 轮,每轮 state 行 round 递增 + 无操作成功行 → 不报警
        lines2 = []
        for i in range(12):
            t = ts(i * 55)
            lines2.append(f'{t} [shop.py 394] [INFO]: [cw] state gold=24 hp=84 lv=4 round={i + 1} node=? plane=1 board={{}} target=\'\' fp=-1.00 bench=2\n')
            lines2.append(f'{t} [prep_director.py 1338] [INFO]: [cw][director] OpenShop({{\'read_only\': False}}) → ✓ 买牌 plan 买0张 升0次 刷0次 卖0张(+0金,守卫拦0) (gold=24 lv=4 plane=1)\n')
            lines2.append(f'{t} [cw_loop.py 1179] [INFO]: [cw-loop] 备战环返回(success=True status=OpenShop ✓)→ 交回顶层分发(下轮全分支重判)\n')
        # 案3(v5)无操作成功循环 + WARNING 堆积:全零 OpenShop 不再算推进 →
        # 同特征 WARNING 堆积达阈值即报 STALL(v4 时代被假推进掩盖)
        lines3 = []
        for i in range(10):
            t = ts(i * 30)
            lines3.append(f'{t} [cw_screen_prep.py 1338] [INFO]: [cw][director] OpenShop({{\'read_only\': False}}) → ✓ 买牌 plan 买0张 升0次 刷0次 卖0张(+0金,守卫拦0) (gold=4 lv=4 plane=1)\n')
            lines3.append(f'{t} [cw_loop.py 972] [WARNING]: [cw!][loop] 备战连续 10 轮 session 无变化 → 留证(无进展)\n')
        # 案4(v5)节点滞留:同 (plane,round) state 行每 60s 一条 ×20(跨度
        # 1140s ≥ 900)→ NODE-DWELL;无白名单动作行,不与 LOOP 混淆
        lines4 = []
        for i in range(20):
            t = ts(i * 60)
            lines4.append(f'{t} [cw_op_buy_cards.py 614] [INFO]: [cw] state gold=4 hp=60 lv=4 plane=1 round=1 node=reward next=reward board={{}}\n')
        # 案5(v5)相位正常轮转:round 每 60s 递增 → 零滞留报警
        lines5 = []
        for i in range(20):
            t = ts(i * 60)
            lines5.append(f'{t} [cw_op_buy_cards.py 614] [INFO]: [cw] state gold=4 hp=60 lv=4 plane=1 round={i + 1} node=battle next=? board={{}}\n')
        for name, text, expect_tag in (
            ('loop_stuck_run24', ''.join(lines), '[SENTINEL-LOOP]'),
            ('normal_progress_nofp', ''.join(lines2), None),
            ('noop_stall_v5', ''.join(lines3), '[SENTINEL-STALL]'),
            ('node_dwell_v5', ''.join(lines4), '[SENTINEL-NODE-DWELL]'),
            ('dwell_healthy_v5', ''.join(lines5), None),
        ):
            log = d / f'{name}.txt'
            log.write_text(text, encoding='utf-8')
            env = dict(os.environ, CW_SENTINEL_LOOP_EVIDENCE=str(d / f'{name}_ev.md'),
                       CW_SENTINEL_DWELL_EVIDENCE=str(d / f'{name}_dwell_ev.md'))
            r = subprocess.run([sys.executable, str(script), '--replay', str(log)],
                               env=env, capture_output=True, text=True, timeout=60,
                               encoding='utf-8', errors='replace')
            out = r.stdout + r.stderr
            has = expect_tag in out if expect_tag else True
            # 零报警用例:任何报警都不该出现;期望用例:只判期望标签(同文件里
            # STALL 与 LOOP 可能同时命中,互不否定)
            no_other = (expect_tag is not None
                        or ('[SENTINEL-LOOP]' not in out
                            and '[SENTINEL-NODE-DWELL]' not in out
                            and '[SENTINEL-STALL]' not in out))
            ok = has and no_other
            last = out.strip().splitlines()[-1] if out.strip() else ''
            print(f"  {'PASS' if ok else 'FAIL'} {name}: 期望 {expect_tag or '零报警'} | 尾行: {last[:110]}")
            cases.append((name, expect_tag or 'no-alarm', ok, last))
    return 0 if all(c[2] for c in cases) else 1


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    print('[selftest] v5 空窗/静默/漂移/循环/无操作成功STALL/节点滞留/正常推进 回归')
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
print(f'[sentinel] armed v5 @ {time.strftime("%H:%M:%S")}, pos={start_pos}, '
      f'log={LOG}, loop(N={LOOP_N},win={LOOP_WIN}s,trial={LOOP_TRIAL}), '
      f'dwell(>{DWELL_SEC}s)', flush=True)

last_line_wall = time.time()


# v3.8(2026-08-26 02:2x 轮转锁死修,根因实锤):原实现长持有日志句柄(readline
# 尾随)——Windows 下开着句柄挡 os.rename,server 的 TimedRotatingFileHandler
# 午夜滚转 PermissionError(WinError 32,日志 Traceback 实锤:轮转 rename 被本
# 哨兵的句柄挡住)。改**短开轮询**:每 POLL_SEC 开→seek→读新增→关,全程不持
# 句柄;外部轮转(rename/截断)由 size<pos 判据捕获。行处理语义逐位保留
# (陈旧行防线/HIT/STALL/LOOP/DWELL/静默双窗/信道重探测)。
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
        _dwell_reset()
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
                    _dwell_reset()
                    last_line_wall = time.time()
                    _seen_quiet_noted = False
                    _skipped_stale = 0
    # 心跳无条件每轮写(2026-09-04 勘误:旧版嵌在 not _lines 分支内,
    # 局活跃日志有流时水位冻结——runtime-ops「哨兵活性回读」以 pos mtime
    # 推进判活,冻结被误读成挂死,两个健康实例被杀)。进程活着 = 水位推进,
    # 与是否读到新行无关;报警路径(上写 _line_end 后 exit)不受影响。
    MARKER.write_text(str(pos))
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
