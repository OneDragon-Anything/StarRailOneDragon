"""r229c 事件哨兵 v5.3(HIT 分级驻留 + 游标恒锚尾;活跃局判定切 journal;v4 循环/静默 + v5 STALL 语义 + 节点滞留 + v5.3 备战环空转)。

## 检测面(当前语义)

- [SENTINEL-HIT](v5.1 分级·关键即退):崩溃栈(Traceback/TypeError/
  AttributeError/StopIteration)/停机终态(STOPPED/停机待建档/plan_error)/
  超时——命中即退出推送。处置依据:审计 0 自愈、run 已断,「退出=事件」
  是唯一即时信道,不能降级到轮询。数据源 = server 主日志(op_journal 面,
  删除波 1 未触及);『plan_error』词源=旧 decisions 流的决策崩溃措辞,
  该流停写后此词在日志恒 0 命中(与 v5 时代一致,纯兜底词汇保留)。
- [SENTINEL-HIT-CONT](v5.1 分级·一般驻留):『执行失败』(单 op 失败,
  有自愈实录 2026-09-08 08:09;且常来自共享日志的其他活动,对 CW 是外活动
  噪声)与『stall_watch』(停滞前兆,升级判定本就归 STALL)——首见打印 +
  整体重写证据文件(cw_hit_alert.md,内容=本纪元全部已报签名+首见行摘录+
  首见时刻)后**驻留续侦不退进程**;纪元内同签名只报一次(复发升级由 STALL
  独立承担,续侦面重复报无增量信息)。非退出事件:消费方核读证据即可,
  不重武——重武三步会杀掉在岗实例(见 autonomous-loop §3)。
  回退开关 CW_SENTINEL_HIT_EXIT_ALL=1 恢复 v5 全即退。--replay 下『执行失败』
  『stall_watch』的打印标签同为 HIT-CONT(replay 本就不退出,观察面)。
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
  - [SENTINEL-PREP-SPIN](v5.3 新增):备战分发行持续到达 ∧ 零实质推进 ≥
    SPIN_SEC(默认 600s,env CW_SENTINEL_SPIN_SEC)→ 报警。节奏锚 =
    `[cw-op] op=备战 plane=` 分发行(每备战轮必落);窗自上一实质推进后的首个
    备战行起算,任一实质推进即重置。补观察断流盲区:认知冻结形态无 state 行
    (NODE-DWELL 失明)、备战行让日志不沉默(SILENCE 失明)、无警告(STALL
    失明)、零动作(LOOP 失明)。心跳采样退役(2026-09-15)后的承接面。

## 实质推进(STALL/LOOP 两分支单一判据,2026-09-03 语义修复)

无操作成功**不算推进**。计为推进的只有:
  ① plan 结果行含非零动作:现行流程行 = `[cw][director] CwActionOpenShopParam(...) → ✓
     买牌 plan 买N张 升N次 刷N次 卖N张`(买/升/刷/卖 全 0 = 纯读店空转,
     1-1 卡死循环每 ~23s 一条,旧 PROGRESS 子串判据把它当推进 → STALL
     整局失明);判词用 NONZERO_RE(只认 ≥1 的动作数)。
  ② `[cw][composite]` 复合动作成功(部署/装备等真实执行,prep_actions 发出)。
  ③ state 行/on_round_end 的 round/plane 变化(含新局回绕);「进位面」。
  ④ 采晶矿收集成功(CwActionCollectOreParam → ✓,奖励节点无战斗时的唯一推进迹象,
     08-25 回放实证 03:28/17:07 两例缺它误报)。
刻意不算:「→ ✓」「执行成功」「出战成功」等裸成功字样——run 24 实证弹窗
误判下「出战成功」每轮假成功;1-1 卡死实证「CwActionOpenShopParam → ✓」每轮假成功。

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
| v5.1 | HIT 分级(关键即退/一般驻留续侦+纪元内同因去重+证据文件)+ 游标恒锚尾不变量(武装/轮转/漂移一律从当前尾起扫,水位文件退役为纯活性心跳) | 2026-09-09 01:13-01:14 脏纪元三连自退实证(死亡实例留新鲜小值水位被信任=重放向量,哨兵逐格啃完脏纪元期间全盲)+ 2026-09-08 70min 补位空窗实证(HIT 即退纯损) |
| v5.3 | 备战环空转 PREP-SPIN(备战行持续 ∧ 零实质推进 ≥ 600s → 报警;心跳采样退役后的观察断流检测承接) | 心跳采样删除裁定(2026-09-15);效果账本自推进迁移迭代设计 3.3 哨兵交接;采样窗精化挂效果域批 M3 |
| v5.2 | 活跃局判定数据源切 journal(_run_ended 重写:尾实机段 match_final 收口+行 ts 新鲜;runs/outcomes/decisions 三流写入端已随删除波 1 停写,旧判定链武装即误判「已终局」);实机段形态过滤(run_%Y%m%d_%H%M%S,fake_/sim_/harness 段不采信——journal 多写者单文件新形态) | T-257(删除波 1 落地审新立项);journal 行结构=kernel/cw_board_state._swap/write_match_final,段隔离约定=sim/cw_delta_pool_gen.QUARANTINED_RUN_PREFIXES |

## 词汇审计(v5,对照流程侧代码与 .log/mcp_server.log 全文 grep)

在岗:『Traceback/TypeError/AttributeError/StopIteration』(框架执行出错栈,
log 387 次全是真崩溃栈);『执行失败』(operation.py:695);『STOPPED』
(RunState.STOPPED 终态行);『超时』(log 4 次,均为「对局循环超时→执行失败」
真故障);『stall_watch』(cw_loop.py:366 停滞哨兵警告行);『停机待建档』
(cw_loop.py:1401 round_fail 状态,未触发过,保留);『state gold=』
(cw_op_buy_cards.py:614);『[cw-loop]』『[cw][battle]』『[cw-deploy]』
(cw_loop.py/prep_actions.py/cw_op_deploy.py);『[cw][director]』
(现行 plan 结果行 CwActionOpenShopParam 由 prep_director 发出)。
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
扫描起点不变量(v5.1):起点 ∈ {进入监视时的文件尾} ∪ {单调前进的已读位置}
——武装一律锚尾(水位文件退役为纯活性心跳,只按 mtime 消费,值不进游标),
日志轮转/截断锚定新纪元当前尾,信道漂移切新文件当前尾。历史字节永不在
扫描集合内,脏日志纪元(有历史 ERROR 行)结构性不重放。
离线自测: 环境变量 CW_SENTINEL_LOG / CW_SENTINEL_POS 重定向日志与水位路径;
  CW_SENTINEL_REPLAY_DIR(或 CW_SENTINEL_JOURNAL)重定向活跃局判定账面
  (v5.2 起 = state/journal.jsonl 单文件;旧 CW_SENTINEL_RUNS/OUTCOMES/
  DECISIONS 三 env 随三流退役删除);CW_SENTINEL_SILENCE /
  CW_SENTINEL_CONFIRM / CW_SENTINEL_DWELL_SEC / CW_SENTINEL_JOURNAL_FRESH /
  CW_SENTINEL_JOURNAL_TAIL / CW_SENTINEL_RUN_RE 覆盖阈值与段形态(仅自测);
  CW_SENTINEL_HIT_EVIDENCE 重定向 HIT 证据路径;
  CW_SENTINEL_HIT_EXIT_ALL=1 恢复 v5 全即退(缺省分级)。
  python cw_sentinel.py --selftest: 内置回归(15 用例:局后空窗→IDLE /
  局中静默→SILENCE / 信道漂移[含漂移后 CONT 去重清零轻断言] / 活跃循环→LOOP /
  无操作成功循环→STALL 不被假推进掩盖 / 节点滞留→NODE-DWELL / 备战空转→PREP-SPIN / 正常推进→不误报 /
  v5.1 七锁:轮转锚尾 L1 / 武装锚尾脏纪元 L2 / 新行双路命中 L3 /
  同因去重+运行边界清零 L4 / 异因仍报 L5 / 升级通道 L6 / 终局标记 L7)。
  python cw_sentinel.py --replay <日志文件>: 历史日志回放——全文件喂行处理逻辑,
  打印全部报警位点(每卡死段一次;不退出不 stop,验证用)。
  python cw_sentinel.py --dry-ended <journal>: 活跃局判定单点干跑——对给定
  journal 跑一次 _run_ended() 打印 ENDED=True/False 退出(判定矩阵验证用)。
"""
import contextlib
import json
import os
import re
import sys
import time
from collections import deque
from datetime import datetime
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
_REPLAY_DIR = Path(os.environ.get('CW_SENTINEL_REPLAY_DIR', r'D:\code\workspace\StarRailOneDragon\.debug\currency_war\telemetry\live'))
# v5.2 活跃局判定数据源切 journal(T-257):v4.1 的 runs/outcomes/decisions
# 三流写入端已随删除波 1(T-243)从 src 删除——三流 mtime 冻结在停写时刻,
# 判定链恒走「runs 尾行有 result+同 id outcomes 陈旧+decisions 陈旧」→
# _run_ended() 恒 True → LOOP 报警整局被 suppress+局后空窗外的静默误判 IDLE
# (实机窗武装必误报的机制)。journal = state/journal.jsonl 唯一账面。
JOURNAL_JSONL = Path(os.environ.get(
    'CW_SENTINEL_JOURNAL', str(_REPLAY_DIR / 'state' / 'journal.jsonl')))
# journal 行内 ts(isoformat)距 now 小于此窗 → 活跃局(v4.1 判定链 3/4 的
# journal 合并等价:journal 是每次 state 写入产行的高频账面,行新鲜即可靠
# 区分;缺省 600 沿 v4.1 decisions 新鲜窗)。行 ts 而非文件 mtime:journal
# 是多写者单文件(sim 批 fake_/sim_ 段、harness 短 id 段交错),文件 mtime
# 会被非实机段写入污染。
JOURNAL_FRESH_SEC = int(os.environ.get('CW_SENTINEL_JOURNAL_FRESH', 600))
# 实机段形态(telemetry/state.start_run 铸造口径 run_%Y%m%d_%H%M%S);
# fake_/sim_ 段与 harness 短 id 段不采信(隔离约定 =
# sim/cw_delta_pool_gen.QUARANTINED_RUN_PREFIXES,三件哨兵同口径)。
RUN_ID_RE = re.compile(os.environ.get('CW_SENTINEL_RUN_RE', r'^run_\d{8}_\d{6}$'))
# _run_ended() 每次调用的尾读字节量:只需覆盖「尾实机段的收口行」
# (match_final 局终才落=段尾),不追段首。缺省 4MB:真实 journal 实测(2026-09-11)
# sim 测试段单次可写 4MB+ 行(fake 段 receipts 数千行),512KB 尾窗会被整段
# 挤出导致「尾窗无实机段行」;4MB ≈ 典型 sim 单次写入量,实机段行不被挤出。
# 成本可控:判定只在静默分支/LOOP 抑制时调用(非 5s 主循环节奏),4MB 读+
# 解析 ≈ 秒级。仍可被更大写入挤出 → 错误方向=判活跃(保守,不吞告警)。
JOURNAL_TAIL_CHUNK = int(os.environ.get('CW_SENTINEL_JOURNAL_TAIL', 4 * 1048576))

# v2 原样:只报需介入的事件(第一版把对账纠漂/MISS 例行也报了,噪声淹没真警报)。
# 词汇审计(v5)见文件头;『人工结束』『plan_error』处置理由亦在头注。
# v5.1 分级:原 PATTERNS 全集 10 词按「即退/驻留」拆两表,成员不增不减——
# 分级依据全部取自 v5 词汇审计的既有语义认定,未新造判定。
# 关键(即退):崩溃栈/运行已死/停机终态,审计 0 自愈;送达信道=「退出=事件」
# 即时推送,降级到轮询等于让最关键事件走最弱信道。『超时』必先于续侦表判:
# 此类行同含『执行失败』(短路序,见 process_line)。
HIT_EXIT_PATTERNS = (
    'Traceback',
    'plan_error',
    '停机待建档',
    'STOPPED',
    '超时',
    'TypeError',
    'AttributeError',
    'StopIteration',
)
# 一般(驻留续侦):有自愈实录(『执行失败』,2026-09-08 08:09 失败→自愈→局继续)
# 或前兆信号(『stall_watch』归 STALL 通道)——报一次+纪元内同签名去重,不退进程。
HIT_CONT_PATTERNS = ('执行失败', 'stall_watch')
# 回退开关:恢复 v5 全即退(试用期若判分级过激,一行环境变量回旧世界)。
# 缺省分级生效,防「缺省关悬置」反模式。
HIT_EXIT_ALL = os.environ.get('CW_SENTINEL_HIT_EXIT_ALL', '0') == '1'
HIT_EVIDENCE = Path(os.environ.get(
    'CW_SENTINEL_HIT_EVIDENCE',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\cw_hit_alert.md'))
STALL_WIN = 600    # 卡死判定窗口(秒)
STALL_N = 10       # 同特征行阈值
SILENCE_SEC = int(os.environ.get('CW_SENTINEL_SILENCE', 360))  # 静默死锁阈值(秒)
SILENCE_CONFIRM = int(os.environ.get('CW_SENTINEL_CONFIRM', 420))  # v3.4:二次确认窗

# ── 实质推进判据(v5,STALL/LOOP 单一源;详见文件头「实质推进」节)──────
# plan 结果行:现行流程 = prep_director 发出的 CwActionOpenShopParam 行;旧核
# 『返回状态 plan』『step1/step2 RunBuyPhase』已随 W971 迁移死亡(全文 grep 0)。
PLAN_LINE = ('[cw][director] CwActionOpenShopParam',)
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
# 08-25 只认①时三类正常段误报实证:采晶矿爆发(CwActionCollectOreParam 同签名一局 7-10 次)
# /备战相位进入/部署跳过——②缺位 → round 推进不可见。
STATE_GATE = 'state gold='
ROUND_RE = re.compile(r'round=(\d+)')
PLANE_RE = re.compile(r'plane=(\d+)')
# 推进事件的「阻断时效」(秒):推进后此窗口内不判循环(采晶矿爆发等单轮高频
# 正常动作靠它豁免);超时后即使窗口里还有更早的推进行,只要同签名动作行
# 已重复满阈值仍报警——run 24 实证:推进停在 04:34:02,若阻断时效=整个
# LOOP_WIN(1500s) 则 04:59 才报,浪费 16min。
LOOP_STALE = int(os.environ.get('CW_SENTINEL_LOOP_STALE', 600))
# 同签名首末出现最小跨度(秒):区分「持续循环」与「单轮爆发」。奖励节点采晶矿
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
# ── v5.3 备战环空转(PREP-SPIN;认知冻结形态专用,补其余四面的共同盲区)──
SPIN_SEC = int(os.environ.get('CW_SENTINEL_SPIN_SEC', 600))
SPIN_EVIDENCE = Path(os.environ.get(
    'CW_SENTINEL_SPIN_EVIDENCE',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\cw_sentinel_spin_ev.md'))
SPIN_ANCHOR = '[cw-op] op=备战 plane='   # 节奏锚:备战分发行(每备战轮必落;含 plane= 防误配「备战暗色锁定」)
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


def _journal_tail_rows(chunk: int) -> list[dict] | None:
    """读 journal 尾部 chunk 的全部可解析行(坏行逐行跳过 = journal.md §5
    宽容消费契约);None = 文件不可读(调用方按「活跃」保守处理)。"""
    try:
        with open(JOURNAL_JSONL, 'rb') as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - chunk))
            tail = fh.read().decode('utf-8', errors='replace')
    except OSError:
        return None
    rows: list[dict] = []
    for ln in tail.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            rows.append(rec)
    return rows


def _run_ended() -> bool:
    """v3.5 活跃局检查(离线,纯读 journal);v5.2 数据源切 journal。

    False=有活跃局(走原双窗),True=局已终局。判定链(任一命中「活跃」
    即返回 False;数据全部只采实机形态段 RUN_ID_RE,fake_/sim_/harness 段
    不采信——journal 多写者单文件,sim 段行不构成「有局/已终局」证据):
      1. journal 不可读/无实机段行 → 活跃(保守,不弱化局中告警);
      2. 尾实机段(末条实机段行的 run_id)无 match_final 收口行 → 活跃
         (段未收口=局在打或异常未收口;后者由静默/STALL 通道报警,不该
         在这里当「已终局」吞掉告警——v4.1 事故方向的守卫);
      3. 末条实机段行 ts 距今 < JOURNAL_FRESH_SEC → 活跃(局终后下一局
         开局初期行流尚未推进/局中长动画段的兜底,沿 v4.1 第 4 条语义)。
      其余(尾段已收口+行流陈旧)= 局后空窗 → True(IDLE 优雅退出)。
    对应关系(v4.1 判定链 → v5.2):旧 1「runs 尾行无 result」≈ 新 2
    (match_final 是 runs 的 journal 收编载体,局终才落);旧 2「outcomes
    有更新局」≈ 新 3(尾段行新鲜即有新活动);旧 3/4(outcomes/decisions
    mtime 新鲜)≈ 新 3(journal 行频高于旧两流,判定更强)。
    """
    rows = _journal_tail_rows(JOURNAL_TAIL_CHUNK)
    if not rows:   # None(不可读)或空(无行)→ 保守按活跃
        return False
    real = [r for r in rows
            if isinstance(r.get('run_id'), str) and RUN_ID_RE.match(r['run_id'])]
    if not real:
        return False   # 尾窗内无实机段行 → 保守按活跃
    last_rid = real[-1]['run_id']
    if not any(r['run_id'] == last_rid and r.get('row') == 'write'
               and r.get('field') == 'match_final' for r in real):
        return False   # 尾实机段未收口 → 活跃(判定链 2)
    try:
        last_ts = datetime.fromisoformat(str(real[-1].get('ts') or ''))
        age = time.time() - last_ts.timestamp()
        if age < JOURNAL_FRESH_SEC:
            return False   # 末条实机段行新鲜 → 活跃(判定链 3)
    except (ValueError, OSError, OverflowError):
        return False   # ts 缺失/不可解析 → 保守按活跃
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
# v5.3 备战环空转:自上一实质推进以来的首个备战分发行时刻(None=窗未武装)
spin_first: int | None = None
spin_last_line: str = ''                          # 窗内最近一条备战行(证据)


def _spin_reset() -> None:
    global spin_first, spin_last_line
    spin_first = None
    spin_last_line = ''


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
      ③state 行 round/plane 变化;④「进位面」;⑤采晶矿收集成功。
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
    # 采晶矿(晶矿收集)成功 = 实质游戏状态推进——08-25 回放实证:奖励节点无战斗
    # → 无 on_round_end,旧格式 state 行缺位,采晶矿爆发(单轮 4-7 次)是唯一推进
    # 迹象;不认它则奖励段跨 600s 即误报(03:28/17:07 两例实证)。
    if 'CwActionCollectOreParam' in line and '→ ✓' in line:
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
        f'## 窗口内该签名最近原始行(最多 {LOOP_N})',
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
        with contextlib.suppress(OSError):
            MARKER.write_text(str(line_end))
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
        with contextlib.suppress(OSError):
            MARKER.write_text(str(line_end))
    return (f'[SENTINEL-NODE-DWELL] 同一(位面,轮次)相位持续≥{DWELL_SEC}s'
            f'(节点滞留): {payload} | 证据={NODE_DWELL_EVIDENCE}')


def _spin_feed(line: str, tod: int) -> tuple[str, str] | None:
    """备战环空转喂行(v5.3):锚 = 备战分发行,窗 = 自上一实质推进的首个锚行起算。

    任一实质推进由 process_line 调 _spin_reset 重置;锚行持续到达而推进持续
    缺席 ≥ SPIN_SEC → ('spin', 证据摘录)。返回 None = 未武装/未到期。
    """
    global spin_first, spin_last_line
    if SPIN_ANCHOR not in line:
        return None
    if spin_first is None:
        spin_first = tod
    spin_last_line = line.strip()[:200]
    if _delta(spin_first, tod) >= SPIN_SEC:
        return ('spin', f'备战行自 {spin_first} 持续≥{SPIN_SEC}s;最近: {spin_last_line}')
    return None


def _spin_alarm(payload: str, line_end: int | None) -> str:
    """备战环空转报警出口(v5.3):落证据文件;返回打印文本。"""
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    ev = [
        f'- 触发时刻: {now}(空转阈值 {SPIN_SEC}s,判据=备战行持续 ∧ 零实质推进)',
        '- 窗内最近一条备战行:',
        f'- {spin_last_line}',
        '',
        '## 判读与建议动作',
        '1. 形态 = 备战环在转、零实质推进(state/on_round_end/动作行全哑)——认知冻结类'
        '(观察断流/决策坏/动作全败),症状抓取不依赖成因',
        '2. 确认 → stop_run;留证/残局清理/重武流程同 NODE-DWELL 证据文件',
    ]
    _write_evidence(SPIN_EVIDENCE, '[SENTINEL-PREP-SPIN] 备战环空转报警证据', ev)
    if line_end is not None:
        with contextlib.suppress(OSError):
            MARKER.write_text(str(line_end))
    return (f'[SENTINEL-PREP-SPIN] 备战行持续∧零实质推进≥{SPIN_SEC}s'
            f'(备战环空转): {payload} | 证据={SPIN_EVIDENCE}')


# ── v5.1 D3 HIT 分级驻留状态 ────────────────────────────────────────
# 已报 CONT 签名 → (首见行摘录, 首见时刻)。去重键复用 _sig(与 STALL 同源,
# 不引入第二套归一化);不做 occurrence 计数(升级归 STALL,证据文件只答
# 「报过什么」,还避免每行重写的高频 IO)。纪元边界四处清零:武装(进程全新,
# 自然为空)/轮转锚尾/信道漂移锚尾/运行边界(与 _dwell_reset 同点同因)。
hit_reported: dict[str, tuple[str, str]] = {}


def _hit_reset() -> None:
    """CONT 去重表纪元边界清零:新纪元/新局重新获得首见报警权。

    跨局复发的同一签名不被旧纪元的去重吞掉(与 _dwell_reset 同点同因:
    终态/被停行是稳定框架词汇,标志上一局已结束)。
    """
    hit_reported.clear()


def _hit_cont(line: str) -> str | None:
    """一般词汇 HIT(执行失败/stall_watch)驻留续侦处置,返回 CONT 报警文本。

    纪元内同签名首见必报+整体重写证据文件;复见静默(返回 None,但调用方
    不因此提前 return——该行仍照常进 STALL/LOOP/DWELL 喂行)。两种返回都
    不退出进程:非退出事件,消费协议=核读证据不重武。
    """
    s = _sig(line)
    if s in hit_reported:
        return None
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    hit_reported[s] = (line.strip()[:200], now)
    ev = [
        f'- 报警时刻: {now}(v5.1 分级:一般词汇驻留续侦,非退出事件,实例在岗)',
        f'- 纪元内已报签名数: {len(hit_reported)}',
        '',
        '## 本纪元已报签名(按首见顺序:时刻 + 首见行摘录)',
    ]
    ev += [f'- [{t0}] {excerpt}' for excerpt, t0 in hit_reported.values()]
    ev += [
        '',
        '## 判读与建议动作',
        '1. 本报警非退出事件:核读本文件、按试用期纪律核时间戳归属(旧行重放/'
        '中途武装无上下文/局后空窗三类误报在 CONT 面同样可能),仅此而已',
        '2. 禁按退出协议重武:重武三步会杀掉在岗实例,丢纪元内去重/静默计时'
        '等在岗状态并制造空窗(单实例锁只兜底裸重武,防不了杀净)',
        '3. 同签名复发的升级判定归 STALL/LOOP 通道(窗口统计),不在本文件',
    ]
    _write_evidence(HIT_EVIDENCE, '[SENTINEL-HIT-CONT] 一般词汇报警证据(驻留续侦)', ev)
    return f'[SENTINEL-HIT-CONT] {line.strip()[:150]} | 证据={HIT_EVIDENCE}'


# ── 行处理核心(watch 主循环与 --replay 共用)─────────────────────────
_seen_terminal = False   # 武装后是否见过 run 终态行(执行成功/执行失败)
_seen_quiet_noted = False  # 交接窗口提示是否已打印(防每5s刷屏;新行到来时重置)
_confirm_deadline = 0.0


def process_line(line: str, line_end: int | None) -> tuple[str, bool] | None:
    """喂一行日志;返回 (报警消息, 是否退出进程) 或 None。

    v5.1 返回协议:关键事件(HIT/STALL/LOOP/DWELL)=(消息, True)→ 主循环
    打印后写水位并 exit(0);一般词汇首见 CONT=(消息, False)→ 只打印不退
    (驻留续侦)。--replay 收集全部消息做回放摘要(观察面)。
    顺序:陈旧行防线 → 白名单豁免 → 关键表 HIT → 续侦表 CONT(纪元内同签名
    去重,不提前 return)→ run 终态标记 → 循环/滞留喂行(同时产出实质推进)
    → STALL(零推进下的 WARNING/ERROR 堆积)→ LOOP/DWELL 报警。
    v5:STALL 的推进判据改与 LOOP 共用「实质推进」(无操作成功不算推进),
    修复 1-1 卡死段「CwActionOpenShopParam 买0张 → ✓」被当推进致 STALL 整局失明的缺陷。
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
    # 设计内自愈白名单(修订):round_retry 复探超窗重试是复探窗
    # 的有界兜底路径(消耗 node_max_retry 预算),其日志不应触发 HIT 报警
    # 退出——但仅豁免 HIT,行仍向下喂 STALL/loop 累积(重试耗尽后的
    # op_fail 终态行不含白名单词,照常报警;真持续卡死双通道兜底)。
    # v5.1(A3 序):白名单豁免挂在关键/续侦两表的总判定之前,语义与 v5
    # 单表一致——若只挂关键表前,白名单行将开始打 CONT(未申报的行为变更)。
    _whitelisted = '复探超窗重试' in line
    _cont_msg: str | None = None
    if not _whitelisted:
        # 总短路序:关键表先判(『超时』行同含『执行失败』,即此因)→ 续侦表。
        if any(p in line for p in HIT_EXIT_PATTERNS):
            return (f'[SENTINEL-HIT] {line.strip()}', True)
        if HIT_EXIT_ALL and any(p in line for p in HIT_CONT_PATTERNS):
            return (f'[SENTINEL-HIT] {line.strip()}', True)   # 回退开关=恢复 v5 即退
        if any(p in line for p in HIT_CONT_PATTERNS):
            # 驻留续侦:首见得 CONT 文本,复见得 None;两种情况都继续向下喂行
            #(v5 在此提前 return,连 _seen_terminal 标记都到不了——run 以
            # 执行失败终局时静默分支 seen_terminal 判据恒假,属潜伏失配,v5.1 顺带修复)。
            _cont_msg = _hit_cont(line)
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
        _hit_reset()   # v5.1:运行边界=纪元边界,新局重新获得 CONT 首见报警权
        _spin_reset()   # v5.3:运行边界重置空转窗
    # v4.0/v5 循环+滞留检测(所有日志级别之外独立计数;同时产出实质推进)
    progressed, kind, payload = _loop_feed(line, _tod_v)
    if progressed:
        progress_tods.append(_tod_v)
        _prune(_tod_v)
        _spin_reset()   # v5.3:任一实质推进重置备战空转窗
    _spin_hit = _spin_feed(line, _tod_v)   # v5.3:备战分发行武装/判窗
    if '[WARNING]' in line or '[ERROR]' in line:
        recent.append((_tod_v, _sig(line)))
        _prune(_tod_v)
        bad = _stall_sig(_tod_v)
        if bad:
            span = _delta(recent[0][0], _tod_v)
            return (f'[SENTINEL-STALL] 近{span}秒同特征行≥{STALL_N}且无实质推进: {bad[:120]}',
                    True)
    if kind == 'loop':
        # 局已终局(journal 尾实机段有 match_final 收口行)则抑制——08-25 17:07
        # 实证:局末/server 重启间隙,窗口残留旧动作行 + 无新推进,非卡死
        # (与 SILENCE 分支同源守卫;replay 模式不做此查——历史回放时 journal
        # 是当前态,不代表历史时刻)。
        if not REPLAY_MODE and _run_ended():
            print(f'[sentinel-loop-suppress] 循环特征命中但活跃局检查判定局已终局'
                  f'(残留窗口),清窗继续: {payload[:80]}', flush=True)
            loop_recent.clear()
            loop_sig_lines.clear()
            # 不在此返回:落到函数尾统一收尾,本行若同时为 CONT 首见则不丢首报
        else:
            return (_loop_alarm(payload, line_end), True)
    elif kind == 'dwell':
        return (_dwell_alarm(payload, line_end), True)
    elif _spin_hit is not None:
        if not REPLAY_MODE and _run_ended():
            _spin_reset()   # 残留窗口(局已终局),清窗继续
        else:
            return (_spin_alarm(_spin_hit[1], line_end), True)
    if _cont_msg is not None:
        return (_cont_msg, False)   # 驻留续侦:只打印不退,主循环继续喂行
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
    v5.1:『执行失败』『stall_watch』的标签为 HIT-CONT(分级驻留;replay 本就
    不退出,标签变化纯观察面),且纪元内同签名去重——重复形态只报首见。
    """
    global REPLAY_MODE
    REPLAY_MODE = True
    p = Path(path)
    n = 0
    alarms: list[tuple[str, str]] = []
    with p.open(encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            n += 1
            _res = process_line(raw, None)
            msg = _res[0] if _res is not None else None
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
    """v5.1 内置回归(17 用例):空窗/静默/漂移[含漂移清零轻断言]/循环/
    无操作成功 STALL/节点滞留/正常推进 + 七锁(轮转锚尾/武装锚尾/新行双路/
    同因去重+运行边界清零/异因仍报/升级通道/终局标记)。"""
    import subprocess
    import tempfile

    script = Path(__file__).resolve()
    cases = []

    def _now_hms() -> str:
        """当前时刻的日志时间戳前缀。历史行时间戳一律用当前时刻——绕过
        陈旧行防线:锁必须证明游标层独自防住重放,不许搭防线便车。"""
        lt = time.localtime()
        return f'[{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}]'

    def _spawn_resident(d: Path, name: str,
                        extra_env: dict[str, str] | None = None,
                        ) -> tuple[subprocess.Popen, Path]:
        """续侦类用例(漂移/七锁)共用子进程启动。

        stdout/stderr 重定向临时文件+父进程轮读——现有 PIPE+communicate 技术
        阻塞到进程退出,做不了「存活期」断言,续侦类锁必须观测存活态。
        env 全量重定向(日志/水位/锁/遥测/三份证据):测试零真实副作用,
        HIT 证据同样必须重定向,不许写生产 cw_hit_alert.md。
        """
        out = d / f'{name}_out.txt'
        env = dict(os.environ,
                   CW_SENTINEL_LOG=str(d / 'log.txt'),
                   CW_SENTINEL_POS=str(d / 'pos'),
                   CW_SENTINEL_LOCK=str(d / 'lock'),
                   CW_SENTINEL_REPLAY_DIR=str(d),   # runs/outcomes/decisions 全落本例目录
                   CW_SENTINEL_POLL='1',
                   CW_SENTINEL_HIT_EVIDENCE=str(d / 'hit_ev.md'),
                   CW_SENTINEL_LOOP_EVIDENCE=str(d / 'loop_ev.md'),
                   CW_SENTINEL_DWELL_EVIDENCE=str(d / 'dwell_ev.md'))
        if extra_env:
            env.update(extra_env)
        # with 退出只关父进程句柄:子进程已在 Popen 时继承了自己的句柄,写不中断
        with open(out, 'w', encoding='utf-8', errors='replace') as fh:
            proc = subprocess.Popen([sys.executable, str(script)], env=env,
                                    stdout=fh, stderr=fh)
        return proc, out

    def _read_out(out: Path) -> str:
        """轮读子进程输出文件;瞬时共享冲突按空串处理(下轮重试)。"""
        try:
            return out.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return ''

    def _wait_out(out: Path, substr: str, timeout: float) -> bool:
        """轮读直到 substr 出现;超时 False。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if substr in _read_out(out):
                return True
            time.sleep(0.2)
        return False

    def _wait_out_count(out: Path, substr: str, count: int, timeout: float) -> bool:
        """轮读直到 substr 出现次数达 count;超时 False。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if _read_out(out).count(substr) >= count:
                return True
            time.sleep(0.2)
        return False

    def _wait_exit(proc: subprocess.Popen, timeout: float) -> bool:
        """轮询进程直到退出;超时 False(仍存活)。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if proc.poll() is not None:
                return True
            time.sleep(0.2)
        return False

    def _append_log(path: Path, text: str) -> None:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(text)

    def _kill(proc: subprocess.Popen) -> None:
        """终止续侦子进程并等句柄释放。Windows 上 TerminateProcess 后内核
        异步收尾子进程残留句柄,紧接的临时目录删除会撞 WinError 32
        (实测:L1 输出文件 unlink 共享冲突),wait 后给一拍余量。"""
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        time.sleep(0.3)

    def _last_line(o: str) -> str:
        return o.strip().splitlines()[-1][:110] if o.strip() else ''
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_st_') as td:
        tdp = Path(td)
        now = time.localtime()
        hms = f'[{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}]'
        # 共用:局中日志若干行后静默(时间戳用当前时刻,绕过 stale-line 跳过)
        log_lines = ''.join([
            f'{hms} [operation.py 431] [INFO]: 指令[ 货币战争-对局循环 ] 节点 检测游戏窗口 -> 对局循环 返回状态 等待\n',
            f'{hms} [onnx_ocr_matcher.py 472] [DEBUG]: OCR结果 [] 耗时 0.27\n',
        ])
        # v5.2 journal 夹具:行 ts 用陈旧常量(文件 mtime 不再参与判定,
        # 行内 ts 才是新鲜度源——「陈旧」由 ts 表达)。
        _STALE_TS = '2020-01-01T00:00:00'
        def _jrow(rid: str, field: str = 'gold') -> str:
            return json.dumps({'v': 1, 'ts': _STALE_TS, 'run_id': rid,
                               'row': 'write', 'field': field, 'after': 1,
                               'same_value': False, 'state': {'values': {}},
                               'sig': {}, 'note': '', 'evidence_refs': []},
                              ensure_ascii=False) + '\n'
        for name, journal_text, expect in (
            # 局后空窗:尾实机段已收口(match_final 在场)+行陈旧 → IDLE(12:51 场景)
            ('idle_after_run',
             _jrow('run_20260901_000001') + _jrow('run_20260901_000001', 'match_final'),
             '[RUN-ENDED-IDLE]'),
            # 局中静默:尾实机段未收口(无 match_final)→ 活跃 → 双窗后仍报 SILENCE
            ('active_run_silence',
             _jrow('run_20260901_000002'),
             '[SENTINEL-SILENCE]'),
        ):
            d = tdp / name
            d.mkdir()
            log = d / 'log.txt'
            log.write_text(log_lines, encoding='utf-8')
            (d / 'state').mkdir()
            (d / 'state' / 'journal.jsonl').write_text(journal_text, encoding='utf-8')
            env = dict(os.environ,
                       CW_SENTINEL_LOG=str(log), CW_SENTINEL_POS=str(d / 'pos'),
                       CW_SENTINEL_LOCK=str(d / 'lock'),
                       CW_SENTINEL_JOURNAL=str(d / 'state' / 'journal.jsonl'),
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
    # v3.7 信道漂移回归 + v5.1 漂移纪元清零轻断言:武装盯 A → A 上见 CONT#1 →
    # B 变最新触发漂移切换(锚尾+清 CONT 去重表)→ B 上追加同签名行 → CONT#2
    # 复现=漂移纪元边界确实清了表(去重表清零点之「信道漂移」,锁面原本无覆盖);
    # 随后按新信道静默走 IDLE 退出。
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_drift_') as td:
        d = Path(td)
        log_a = d / 'log_a.txt'
        log_b = d / 'log_b.txt'
        quiet = (f'{_now_hms()} [operation.py 431] [INFO]: 指令[ 货币战争-对局循环 ]'
                 f' 节点 检测游戏窗口 -> 对局循环 返回状态 等待\n'
                 f'{_now_hms()} [onnx_ocr_matcher.py 472] [DEBUG]: OCR结果 [] 耗时 0.27\n')
        fail_a = (f'{_now_hms()} [operation.py 695] [ERROR]: 指令[ 货币战争-对局循环 ]'
                  f' 节点 检测游戏窗口 执行失败\n')
        log_a.write_text(quiet, encoding='utf-8')
        log_b.write_text('', encoding='utf-8')
        old = time.time() - 3600
        os.utime(log_b, (old, old))   # B 初始陈旧 → 武装时选 A
        # v5.2:静默尾段预期「已收口+陈旧」→ _run_ended()=True → IDLE 退出路径
        _stale_ts = '2020-01-01T00:00:00'
        (d / 'state').mkdir()
        (d / 'state' / 'journal.jsonl').write_text(''.join(
            json.dumps({'v': 1, 'ts': _stale_ts, 'run_id': 'run_20260901_000003',
                        'row': 'write', 'field': f, 'after': 1, 'same_value': False,
                        'state': {'values': {}}, 'sig': {}, 'note': '',
                        'evidence_refs': []}, ensure_ascii=False) + '\n'
            for f in ('gold', 'match_final')), encoding='utf-8')
        proc, out = _spawn_resident(d, 'drift', extra_env={
            'CW_SENTINEL_LOG': str(log_a), 'CW_SENTINEL_LOG2': str(log_b),
            'CW_SENTINEL_SILENCE': '8', 'CW_SENTINEL_CONFIRM': '3',
            'CW_SENTINEL_REPROBE': '2'})
        time.sleep(1.5)   # 等子进程完成武装(盯 A)
        _append_log(log_a, fail_a)                    # A 上首见 → CONT#1
        c1 = _wait_out(out, '[SENTINEL-HIT-CONT]', 10)
        log_b.write_text(quiet, encoding='utf-8')     # B 变最新 → 触发漂移
        drift = _wait_out(out, '日志信道漂移', 15)     # 等到切换打印=锚尾已定,再喂 B
        _append_log(log_b, fail_a)                    # 同签名(去时间戳同键)
        c2 = _wait_out_count(out, '[SENTINEL-HIT-CONT]', 2, 10)
        try:
            proc.wait(timeout=60)                     # 静默 → 活跃局检查判终局 → IDLE
        except subprocess.TimeoutExpired:
            proc.kill()
        o = _read_out(out)
        ok = (c1 and drift and c2
              and '日志信道漂移' in o and '[RUN-ENDED-IDLE]' in o
              and '[SENTINEL-SILENCE]' not in o
              and o.count('[SENTINEL-HIT-CONT]') == 2)
        print(f"  {'PASS' if ok else 'FAIL'} channel_drift: 期望 漂移切换+CONT清零复现+IDLE"
              f" | 尾行: {_last_line(o)}")
        cases.append(('channel_drift', '漂移切换+CONT清零复现+IDLE', ok, _last_line(o)))
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
        # 同签名动作行,含现行 CwActionOpenShopParam 无操作成功行)→ LOOP
        lines = []
        for i in range(11):
            t = ts(i * 55)
            lines.append(f'{t} [shop.py 394] [INFO]: [cw] state gold=24 hp=84 lv=4 round=3 node=? plane=1 board={{}} target=\'\' fp=-1.00 bench=2\n')
            lines.append(f'{t} [prep_director.py 1338] [INFO]: [cw][director] CwActionOpenShopParam({{\'read_only\': False}}) → ✓ 买牌 plan 买0张 升0次 刷0次 卖0张(+0金,守卫拦0) (gold=24 lv=4 plane=1)\n')
            lines.append(f'{t} [cw_loop.py 1179] [INFO]: [cw-loop] 备战环返回(success=True status=CwActionOpenShopParam ✓)→ 交回顶层分发(下轮全分支重判)\n')
        # 案2 正常局:12 轮,每轮 state 行 round 递增 + 无操作成功行 → 不报警
        lines2 = []
        for i in range(12):
            t = ts(i * 55)
            lines2.append(f'{t} [shop.py 394] [INFO]: [cw] state gold=24 hp=84 lv=4 round={i + 1} node=? plane=1 board={{}} target=\'\' fp=-1.00 bench=2\n')
            lines2.append(f'{t} [prep_director.py 1338] [INFO]: [cw][director] CwActionOpenShopParam({{\'read_only\': False}}) → ✓ 买牌 plan 买0张 升0次 刷0次 卖0张(+0金,守卫拦0) (gold=24 lv=4 plane=1)\n')
            lines2.append(f'{t} [cw_loop.py 1179] [INFO]: [cw-loop] 备战环返回(success=True status=CwActionOpenShopParam ✓)→ 交回顶层分发(下轮全分支重判)\n')
        # 案3(v5)无操作成功循环 + WARNING 堆积:全零 CwActionOpenShopParam 不再算推进 →
        # 同特征 WARNING 堆积达阈值即报 STALL(v4 时代被假推进掩盖)
        lines3 = []
        for i in range(10):
            t = ts(i * 30)
            lines3.append(f'{t} [cw_screen_prep.py 1338] [INFO]: [cw][director] CwActionOpenShopParam({{\'read_only\': False}}) → ✓ 买牌 plan 买0张 升0次 刷0次 卖0张(+0金,守卫拦0) (gold=4 lv=4 plane=1)\n')
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
        # 案6(v5.3)备战环空转:备战分发行每 60s 一条 ×12(跨度 660s ≥ 600)且零实质
        # 推进 → PREP-SPIN;state 行缺席(NODE-DWELL 盲区形态)
        lines6 = []
        for i in range(12):
            t = ts(i * 60)
            lines6.append(f'{t} [cw_loop.py 2271] [INFO]: [cw-op] op=备战 plane=1 round=3 outcome=ok\n')
        # 案7(v5.3)备战环健康:备战行 + state 行 round 递增(实质推进重置)→ 零报警
        lines7 = []
        for i in range(12):
            t = ts(i * 60)
            lines7.append(f'{t} [cw_loop.py 2271] [INFO]: [cw-op] op=备战 plane=1 round={i + 1} outcome=ok\n')
            lines7.append(f'{t} [cw_op_buy_cards.py 614] [INFO]: [cw] state gold=4 hp=60 lv=4 plane=1 round={i + 1} node=battle next=? board={{}}\n')
        for name, text, expect_tag in (
            ('loop_stuck_run24', ''.join(lines), '[SENTINEL-LOOP]'),
            ('normal_progress_nofp', ''.join(lines2), None),
            ('noop_stall_v5', ''.join(lines3), '[SENTINEL-STALL]'),
            ('node_dwell_v5', ''.join(lines4), '[SENTINEL-NODE-DWELL]'),
            ('dwell_healthy_v5', ''.join(lines5), None),
            ('prep_spin_v53', ''.join(lines6), '[SENTINEL-PREP-SPIN]'),
            ('prep_spin_healthy_v53', ''.join(lines7), None),
        ):
            log = d / f'{name}.txt'
            log.write_text(text, encoding='utf-8')
            env = dict(os.environ, CW_SENTINEL_LOOP_EVIDENCE=str(d / f'{name}_ev.md'),
                       CW_SENTINEL_DWELL_EVIDENCE=str(d / f'{name}_dwell_ev.md'),
                       CW_SENTINEL_SPIN_EVIDENCE=str(d / f'{name}_spin_ev.md'))
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
                            and '[SENTINEL-PREP-SPIN]' not in out
                            and '[SENTINEL-STALL]' not in out))
            ok = has and no_other
            last = out.strip().splitlines()[-1] if out.strip() else ''
            print(f"  {'PASS' if ok else 'FAIL'} {name}: 期望 {expect_tag or '零报警'} | 尾行: {last[:110]}")
            cases.append((name, expect_tag or 'no-alarm', ok, last))
    # ── v5.1 七锁(2026-09-09 01:13 脏纪元三连自退 + 2026-09-08 70min 补位
    #    空窗实证驱动;构造与变异纪律=文件头 v5.1 语义)。续侦类存活断言全走
    #    「stdout 重定向临时文件+轮读」;历史行时间戳一律当前时刻(不搭陈旧
    #    防线便车,锁死的是游标层/分级层本身)。────────────────────────────
    _FAIL_A = ('[operation.py 695] [ERROR]: 指令[ 货币战争-对局循环 ]'
               ' 节点 检测游戏窗口 执行失败')
    _CRIT = '[prep_director.py 1] [ERROR]: Traceback (most recent call last):'
    _BOUNDARY = '[run_context.py 88] [INFO]: run 已停止[mcp:stop_run]'

    # L1 轮转锚尾锁:arm(无 pos)→ 过 2 轮询 → 更小文件整替(模拟轮转,内含
    # 新鲜 Traceback)→ 过 3 轮询 → 追加良性新行。锚尾语义必须:全程零 HIT*、
    # 出现轮转锚尾打印、进程存活且良性行后仍在岗。
    # 变异 M1:轮转分支回退 pos=0 → 整替件内 Traceback 被重放 HIT,红。
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_L1_') as td:
        d = Path(td)
        log = d / 'log.txt'
        # 初文件必须大于整替件:size<pos 才构成轮转;整替件仅 1 行必然更小
        log.write_text(''.join(
            f'{_now_hms()} [onnx_ocr_matcher.py 472] [DEBUG]: OCR结果 [] 耗时 0.2{i}\n'
            for i in range(3)), encoding='utf-8')
        proc, out = _spawn_resident(d, 'L1')
        time.sleep(2.2)   # 过 2 轮询,锚定初文件尾
        log.write_text(f'{_now_hms()} {_CRIT}\n', encoding='utf-8')   # 整替=变小
        time.sleep(3.3)   # 过 3 轮询,轮转分支必已走
        o = _read_out(out)
        ok = ('[SENTINEL-HIT' not in o and '锚定新纪元尾部' in o
              and proc.poll() is None)
        _append_log(log, f'{_now_hms()} [onnx_ocr_matcher.py 472] [DEBUG]: OCR结果 [] 耗时 0.31\n')
        time.sleep(2.2)   # 良性新行后仍存活(锚尾后继续增量)
        o = _read_out(out)
        ok = ok and '[SENTINEL-HIT' not in o and proc.poll() is None
        _kill(proc)
        print(f"  {'PASS' if ok else 'FAIL'} L1_rotation_anchor_tail:"
              f" 期望 零HIT*+锚尾打印+存活 | 尾行: {_last_line(o)}")
        cases.append(('L1_rotation_anchor_tail', '零HIT*+锚尾打印+存活', ok, _last_line(o)))

    # L2 武装锚尾锁(脏纪元验收主锁,criteria 前半「arm 后 ≤60s 无重放 HIT」):
    # 预填新鲜历史(Traceback+执行失败)→ 无 pos 武装 → POLL=1s 观测 60s:
    # 零 [SENTINEL-HIT] 且零 [SENTINEL-HIT-CONT](历史一个不咬)+心跳 mtime 推进
    # +武装打印锚尾语义。
    # 变异 M2:恢复 MARKER 信任块并以小值毒化 pos → arm 后数秒 HIT,红。
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_L2_') as td:
        d = Path(td)
        log = d / 'log.txt'
        log.write_text(f'{_now_hms()} {_CRIT}\n{_now_hms()} {_FAIL_A}\n', encoding='utf-8')
        proc, out = _spawn_resident(d, 'L2')
        t0 = time.time()
        time.sleep(5)   # 首个心跳已落
        hb1 = (d / 'pos').stat().st_mtime if (d / 'pos').exists() else 0.0
        dirty_red = False
        while time.time() - t0 < 60:   # criteria 口径:观测满 60s
            o = _read_out(out)
            if '[SENTINEL-HIT' in o or proc.poll() is not None:
                dirty_red = True   # 历史被重放,或进程提前退出
                break
            time.sleep(1)
        hb2 = (d / 'pos').stat().st_mtime if (d / 'pos').exists() else 0.0
        o = _read_out(out)
        ok = (not dirty_red and '[SENTINEL-HIT' not in o
              and '武装恒锚尾' in o and hb2 > hb1 and proc.poll() is None)
        _kill(proc)
        print(f"  {'PASS' if ok else 'FAIL'} L2_armed_anchor_tail:"
              f" 期望 脏纪元60s零HIT*+心跳推进+存活 | 尾行: {_last_line(o)}")
        cases.append(('L2_armed_anchor_tail', '脏纪元60s零HIT*+心跳推进+存活',
                      ok, _last_line(o)))

    # L3 新行命中锁(验收后半「新行仍能命中」):脏历史在场的前提下新行双路——
    # 追加新鲜 执行失败 → CONT 且进程存活(驻留);追加新鲜 Traceback → HIT 且
    # exit(0)(关键即时推送不弱化)。
    # 变异 M3:续侦词并入关键表 → 执行失败处直接退,存活断言红。
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_L3_') as td:
        d = Path(td)
        log = d / 'log.txt'
        log.write_text(f'{_now_hms()} {_CRIT}\n', encoding='utf-8')
        proc, out = _spawn_resident(d, 'L3')
        time.sleep(2.2)
        _append_log(log, f'{_now_hms()} {_FAIL_A}\n')
        cont = _wait_out(out, '[SENTINEL-HIT-CONT]', 10)
        time.sleep(1.5)   # CONT 后确认没有跟着退出(驻留)
        alive = proc.poll() is None
        _append_log(log, f'{_now_hms()} {_CRIT}\n')
        exited = _wait_exit(proc, 10)
        o = _read_out(out)
        ok = (cont and alive and exited
              and '[SENTINEL-HIT-CONT]' in o and '[SENTINEL-HIT]' in o
              and proc.returncode == 0)
        _kill(proc)
        print(f"  {'PASS' if ok else 'FAIL'} L3_newline_dual_path:"
              f" 期望 CONT存活+HIT退出 | 尾行: {_last_line(o)}")
        cases.append(('L3_newline_dual_path', 'CONT存活+HIT退出', ok, _last_line(o)))

    # L4 同因去重锁 + 运行边界清零轻断言:同签名两条(仅时间戳不同)→ CONT 恰
    # 1 次;喂终态行(运行边界=纪元边界,与 _dwell_reset 同点)后同签名再现 →
    # CONT 第 2 次=边界确实清了表(去重表清零点之「运行边界」,锁面原本无覆盖)。
    # 变异 M4:去重表查找短路(每见必报)→ 3 报即红;边界清零缺失 → 1 报即红。
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_L4_') as td:
        d = Path(td)
        log = d / 'log.txt'
        log.write_text('', encoding='utf-8')
        proc, out = _spawn_resident(d, 'L4')
        time.sleep(2.2)   # 锚定空尾
        _append_log(log, f'{_now_hms()} {_FAIL_A}\n')
        _wait_out(out, '[SENTINEL-HIT-CONT]', 10)        # 报#1
        _append_log(log, f'{_now_hms()} {_FAIL_A}\n')    # 同签名(去时间戳同键)
        time.sleep(2.2)   # 等该行被读:复见必须静默
        _append_log(log, f'{_now_hms()} {_BOUNDARY}\n')  # 运行边界:清表
        time.sleep(1.2)
        _append_log(log, f'{_now_hms()} {_FAIL_A}\n')    # 新局首见 → 应再报
        again = _wait_out_count(out, '[SENTINEL-HIT-CONT]', 2, 10)
        # 第 3 报探测窗:绿态必超时(同因静默);去重失效变异(每见必报)下第 3 报
        # 在一个轮询内落地——给足落地时间再计数,否则变异态读到瞬时 count=2 假绿
        _ = _wait_out_count(out, '[SENTINEL-HIT-CONT]', 3, 3)
        o = _read_out(out)
        ok = (again and o.count('[SENTINEL-HIT-CONT]') == 2
              and proc.poll() is None)
        _kill(proc)
        print(f"  {'PASS' if ok else 'FAIL'} L4_dedup_boundary_reset:"
              f" 期望 同因恰1报+边界后复现共2报+存活 | 尾行: {_last_line(o)}")
        cases.append(('L4_dedup_boundary_reset', '同因恰1报+边界后复现共2报+存活',
                      ok, _last_line(o)))

    # L5 异因仍报锁:执行失败 后跟不同签名 stall_watch 行 → 两个不同 CONT 各 1 次。
    # 变异 M5:去重键退化为全局单键 → 第二异因被吞,1 报即红。
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_L5_') as td:
        d = Path(td)
        log = d / 'log.txt'
        log.write_text('', encoding='utf-8')
        proc, out = _spawn_resident(d, 'L5')
        time.sleep(2.2)
        _append_log(log, f'{_now_hms()} {_FAIL_A}\n')
        _wait_out(out, '[SENTINEL-HIT-CONT]', 10)
        _append_log(log, f'{_now_hms()} [cw_loop.py 366] [WARNING]:'
                         ' [cw!][loop] stall_watch 备战连续 3 轮 session 无变化 → 留证\n')
        second = _wait_out_count(out, '[SENTINEL-HIT-CONT]', 2, 10)
        o = _read_out(out)
        ok = (second and o.count('[SENTINEL-HIT-CONT]') == 2
              and 'stall_watch' in o and proc.poll() is None)
        _kill(proc)
        print(f"  {'PASS' if ok else 'FAIL'} L5_distinct_cause_reported:"
              f" 期望 异因两报各1次+存活 | 尾行: {_last_line(o)}")
        cases.append(('L5_distinct_cause_reported', '异因两报各1次+存活', ok, _last_line(o)))

    # L6 升级通道锁:10 条同签名 [ERROR] 执行失败(单窗内、无实质推进)→
    # 第 10 条触发 STALL 且进程退——证明续侦不吞升级(STALL 判据与去重正交:
    # WARNING/ERROR 全量进 recent,不看是否 CONT 报过)。
    # 变异 M6:续侦分支提前 return → recent 不进 → STALL 不触发,存活即红。
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_L6_') as td:
        d = Path(td)
        log = d / 'log.txt'
        log.write_text('', encoding='utf-8')
        proc, out = _spawn_resident(d, 'L6')
        time.sleep(2.2)
        t = _now_hms()
        _append_log(log, ''.join(f'{t} {_FAIL_A}\n' for _ in range(10)))
        exited = _wait_exit(proc, 15)
        o = _read_out(out)
        ok = (exited and '[SENTINEL-STALL]' in o
              and o.count('[SENTINEL-HIT-CONT]') == 1 and proc.returncode == 0)
        _kill(proc)
        print(f"  {'PASS' if ok else 'FAIL'} L6_stall_escalation:"
              f" 期望 第10条STALL退出+CONT恰1 | 尾行: {_last_line(o)}")
        cases.append(('L6_stall_escalation', '第10条STALL退出+CONT恰1', ok, _last_line(o)))

    # L7 终局标记修复锁(行为增量):『指令[...] 执行失败』行喂到后进入静默
    # 双窗(短阈值;journal 尾实机段未收口使 _run_ended() 为假(v5.2);
    # 夹具不得混入『执行成功』——该行在 v5/v5.1 都会置位标记,混入即毁判别力)。
    # v5 下该行的标记置位到不了(HIT 判定即提前返回,准确说是仅 执行失败 行
    # 的置位丢失,执行成功 行本就置位);v5.1 续侦喂行后应走 [sentinel-quiet]
    # 路径:无 SILENCE 报警、进程在岗。
    # 变异 M7:续侦面恢复提前 return → 置位到不了 → 走 SILENCE 报警分支,红。
    with tempfile.TemporaryDirectory(prefix='cw_sentinel_L7_') as td:
        d = Path(td)
        log = d / 'log.txt'
        log.write_text('', encoding='utf-8')
        (d / 'state').mkdir()
        (d / 'state' / 'journal.jsonl').write_text(
            json.dumps({'v': 1, 'ts': '2020-01-01T00:00:00',
                        'run_id': 'run_20260901_000004', 'row': 'write',
                        'field': 'gold', 'after': 1, 'same_value': False,
                        'state': {'values': {}}, 'sig': {}, 'note': '',
                        'evidence_refs': []}, ensure_ascii=False) + '\n',
            encoding='utf-8')   # 尾段未收口(无 match_final)→ 判活跃
        proc, out = _spawn_resident(d, 'L7', extra_env={
            'CW_SENTINEL_SILENCE': '3', 'CW_SENTINEL_CONFIRM': '3'})
        time.sleep(2.2)
        _append_log(log, f'{_now_hms()} {_FAIL_A}\n')
        _wait_out(out, '[SENTINEL-HIT-CONT]', 10)
        quiet = _wait_out(out, '[sentinel-quiet]', 10)
        time.sleep(7)   # 越过 SILENCE(3)+CONFIRM(3):误走 SILENCE 分支者此处已退
        o = _read_out(out)
        ok = (quiet and proc.poll() is None
              and '[sentinel-quiet]' in o and '[SENTINEL-SILENCE]' not in o)
        _kill(proc)
        print(f"  {'PASS' if ok else 'FAIL'} L7_terminal_mark_via_cont:"
              f" 期望 quiet路径+无SILENCE+存活 | 尾行: {_last_line(o)}")
        cases.append(('L7_terminal_mark_via_cont', 'quiet路径+无SILENCE+存活',
                      ok, _last_line(o)))
    return 0 if all(c[2] for c in cases) else 1


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    print('[selftest] v5.3 十七用例回归:空窗/静默[journal 判定]/漂移/循环/STALL/滞留/推进'
          ' + 七锁(轮转锚尾/武装锚尾/新行双路/同因去重/异因仍报/升级通道/终局标记)')
    sys.exit(_selftest())

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--replay':
    if len(sys.argv) < 3:
        print('用法: cw_sentinel.py --replay <日志文件>', flush=True)
        sys.exit(2)
    sys.exit(_replay(sys.argv[2]))

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--dry-ended':
    # v5.2 活跃局判定单点干跑(T-257):对给定 journal(缺省=现役路径)跑一次
    # _run_ended() 打印 ENDED=… 退出;纯判定面输出,不进监视循环不占锁。
    if len(sys.argv) > 2:
        JOURNAL_JSONL = Path(sys.argv[2])
    print(f'ENDED={_run_ended()} (journal={JOURNAL_JSONL})', flush=True)
    sys.exit(0)

if not REPLAY_MODE and not _acquire_lock():
    sys.exit(0)
# ── v5.1 D1 武装游标:恒锚尾(不变量:扫描起点 ∈ {进入监视时尾} ∪ {单调前进})──
# 2026-09-09 01:13-01:14 三连自退实证的自持链:死亡实例报警路径写
# MARKER=line_end → 十分钟内重武信任该新鲜小值 → 从历史中段续扫 → 撞新鲜
# 历史 ERROR → 再死、水位再前爬——哨兵像啃玉米一样把脏纪元啃完,期间监控
# 全盲。「信任水位」整体退役:水位文件降级为纯活性心跳(runtime-ops 活性
# 回读只消费 mtime),值不再进入游标;武装起点恒为武装时刻的文件尾。
# LOG 缺失守卫(搭车件,现行武装即崩):pos 以 None 起始,由 _read_new_lines()
# 首见成功 stat 时锚定当时尾(锚定发生在该函数内 size<pos 比较之前,否则
# None<int 直接 TypeError);禁用 0 兜底——0 在合法起点集合之外,文件稍后
# 以带历史形态出现时又是重放。
pos: int | None
try:
    pos = LOG.stat().st_size   # 进入监视时的文件尾
except OSError:
    pos = None                 # 日志尚不存在 → 首见成功 stat 时锚尾
_pos_show = '待日志首见锚尾' if pos is None else str(pos)
print(f'[sentinel] armed v5.1 @ {time.strftime("%H:%M:%S")}, pos={_pos_show}(武装恒锚尾), '
      f'log={LOG}, loop(N={LOOP_N},win={LOOP_WIN}s,trial={LOOP_TRIAL}), '
      f'dwell(>{DWELL_SEC}s), spin(>{SPIN_SEC}s), hit(分级,exit_all={HIT_EXIT_ALL})', flush=True)

last_line_wall = time.time()


# v3.8(2026-08-26 02:2x 轮转锁死修,根因实锤):原实现长持有日志句柄(readline
# 尾随)——Windows 下开着句柄挡 os.rename,server 的 TimedRotatingFileHandler
# 午夜滚转 PermissionError(WinError 32,日志 Traceback 实锤:轮转 rename 被本
# 哨兵的句柄挡住)。改**短开轮询**:每 POLL_SEC 开→seek→读新增→关,全程不持
# 句柄;外部轮转(rename/截断)由 size<pos 判据捕获(v5.1 起处置=锚定新纪元
# 当前尾,不再是回零重读)。行处理语义除 HIT 分级(v5.1,见文件头)外逐位
# 保留(陈旧行防线/STALL/LOOP/DWELL/静默双窗/信道重探测)。
POLL_SEC = float(os.environ.get('CW_SENTINEL_POLL', '5'))
_log_path = LOG            # 当前活信道(漂移切换后更新)
_last_probe = time.time()  # 上次信道重探测时刻
_buf = ''                  # 尾部半行(写入中),下轮拼接
_skipped_stale = 0


def _read_new_lines() -> list[tuple[str, int]]:
    """短开读新增行:返回 [(行文本含换行, 行尾偏移)];轮转锚定新纪元当前尾。

    行尾偏移按解码后字节累计,损坏字节被 errors='replace' 替换的场景可能偏
    几字节——只用于 MARKER(心跳/报警位点),偏差无害(最多重读半行被解析跳过)。
    """
    global pos, _buf
    try:
        size = _log_path.stat().st_size
    except OSError:
        return []
    if pos is None:
        # v5.1 D1 搭车件:武装时日志尚不存在 → 首见成功 stat 即锚定当时尾
        #(该时刻才是真正「进入监视」的时刻,符合不变量的进入时尾语义)。
        # 锚定必须先于下方 size<pos 比较(否则 None < int 直接 TypeError);
        # 禁用 0 兜底:0 在合法起点集合之外,见武装块注释。
        pos = size
    if size < pos:
        # v5.1 D2 轮转/截断:旧纪元坐标失效 → 锚定新纪元当前尾,历史不重放。
        # v5 及以前此处置 pos=0=整文件重放,是 2026-09-09 脏纪元自毁循环的
        # 向量之一(武装信任水位是另一个,已在武装块拆除)。检测边界:
        # size<pos 只能测「新纪元未长过旧 pos」的轮转;新文件在一个轮询间隔
        # 内长过旧 pos 则漏检(需单间隔重写整旧文件长度,本项目日志速率下
        # 不可达;漏检后果=跳过新纪元前缀的丢失窗,不重放不崩溃)。
        print(f'[sentinel] 日志轮转/截断,锚定新纪元尾部 pos={size}'
              f'(其已有内容按纪元边界跳过)', flush=True)
        pos = size
        _buf = ''   # 旧文件半行残尾必须弃:拼进新纪元首行会造伪行
        recent.clear()
        progress_tods.clear()
        loop_recent.clear()
        loop_progress.clear()
        _dwell_reset()
        _hit_reset()   # v5.1:纪元边界,CONT 去重表清零(新纪元重获首见报警权)
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
        _res = process_line(_line, _line_end)
        if _res is None:
            continue
        _msg, _fatal = _res
        print(_msg, flush=True)
        if not _fatal:
            continue   # v5.1 CONT 驻留:非退出事件,实例保持在岗继续侦
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
                    pos = _new_size   # v5.1:切到新文件当前尾(锚尾先例,历史不回读)
                    _buf = ''
                    recent.clear()
                    progress_tods.clear()
                    loop_recent.clear()
                    loop_progress.clear()
                    _dwell_reset()
                    _hit_reset()   # v5.1:纪元边界,CONT 去重表清零
                    last_line_wall = time.time()
                    _seen_quiet_noted = False
                    _skipped_stale = 0
    # 心跳无条件每轮写(2026-09-04 勘误:旧版嵌在 not _lines 分支内,
    # 局活跃日志有流时水位冻结——runtime-ops「哨兵活性回读」以 pos mtime
    # 推进判活,冻结被误读成挂死,两个健康实例被杀)。进程活着 = 水位推进,
    # 与是否读到新行无关;报警路径(写 _line_end 后 exit)不受影响。
    # v5.1:值退役为纯活性指标(游标不再读它);pos 尚未锚定(None,武装时
    # 日志缺失)写 '-1' 占位——写 "None" 字符串会让任何按 int 解析水位的
    # 工具崩,可解析占位两全(仅 mtime 被消费,值本身无人读)。
    MARKER.write_text('-1' if pos is None else str(pos))
    if time.time() - last_line_wall > SILENCE_SEC:
            # v3.5(12:51 误报修):静默判定前先做「活跃局检查」(v5.2 起离线读
            # state/journal.jsonl 尾窗;v5.1 及以前读 runs/outcomes/decisions,
            # 三流已随删除波 1 停写退役)。局已自然终局 → 局后空窗是正常交接
            # 状态,IDLE 提示 + 优雅退出,不走 SILENCE 报警;
            # 局仍活跃 → 维持原双窗逻辑(结算屏/动画段误报防护不弱化)。
            if _run_ended():
                print(f'[RUN-ENDED-IDLE] 静默{int(time.time()-last_line_wall)}s 且活跃局检查判定'
                      f'局已终局(journal={JOURNAL_JSONL.name} 尾实机段已收口)'
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
