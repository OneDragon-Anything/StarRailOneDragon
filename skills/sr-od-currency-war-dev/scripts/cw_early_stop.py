"""早停监视 v4(只报不停,停局决策归主 agent;T-257:尾读源切 journal)。

## 判据 v3→v4(判据数值与报警契约不变,数据源面切 journal)

判据 v3(2026-08-25 目标函数修正,用户点破五局误判后重写;判据权威 =
docs/game/currency_war/research/user_playstyle.md 口述登记簿 [28](P1 守息
过程+双指标验收)+[18](hp 低=报警观察非触发);2026-08-26 口径修正只改
本说明,判据逻辑不动):
  **位面1的目标=[28] 双指标验收:息基保住 × 形态达标**(出口 ~50 金是守息的
  表征,不是单指标验收目标;[28] 最高权威:进 P2 应携 ~50 金;赢 boss 但
  花光=「打过了也没经济通关」)。
  - 真停局候选:P1 出口金 < 50(息基未保住表征,候选线索非验收线)或 HP=1
    (真死局);
  - HP<70 → **[P1-HP-LOW-OBSERVE] 观察报警不停局**([18]:hp 低=运营质量报警
    不是 ALL IN/停局触发;正确响应=判读看形态/金/锁线,不是停)。

## 数据源 v3→v4(journal.md §1/§4;删除波 1 后旧流停写)

v3 读 decisions.jsonl(state.hp/plane/streak)+ outcomes.jsonl(hp_after 真值,
金回退 decisions 备战帧)。删除波 1(T-243)后两流写入端已删(哨兵武装即
NO_ACTIVE_RUN 自愈退出,永远看不到 P1→P2)。v4 尾读 journal
(state/journal.jsonl,唯一账面),逐项等价映射:

- plane → 行内 ``state.values.node.plane``(节点派生写端=观察汇聚的派生
  管线,kernel/cw_board_state.observe_screen_context,备战帧写入);
- hp   → 行内 ``state.values.hp``。v3 的双源结构(outcomes 结算真值优先/
  decisions 备战帧回退)在 journal 上收敛为单源:journal 的 hp 走写入闸
  (BoardState hp 字段注释 §3.2.13——非真读帧不经 observe,失读走 carry
  不产行),行流 hp 值天然含「结算覆盖后的真值」(P1 末行= boss 结算后
  覆盖值),精度不低于旧 outcomes hp_after;报警文本 src 标签统一标
  journal,v3 的 FALLBACK-DECISIONS 标签随双源结构消亡。
- gold → 行内 ``state.values.gold``(备战帧观察+买卖扣金 logic 写入,比
  v3 的「备战帧≈出口金」更精确——扣金即时入账)。
- streak → 行内 ``state.values.streak``。
- 活跃判定(启动 mtime 闸)→ journal mtime(journal 是每次 state 写入
  产行的高频账面,活性语义强于旧 decisions mtime)。

## watch 模式(默认,武装在有局时)

tail journal,plane≥2 首行出现 = P1 结束,评估后继续看下一局;真停局候选
→ [EARLY-STOP-ALERT] 打印+exit(推送唤醒);HP 低 → [P1-HP-LOW-OBSERVE]
打印后继续 watch。新 run_id 段切换时若旧局死在 P1 未评估 → 记一行
RUN_ENDED_IN_P1。附加信号:P1 期间 streak 首次转负 → 打印 [STREAK-BROKEN]
记录(不退出)。启动时 journal mtime 超 15 分钟 → NO_ACTIVE_RUN 退出
(无局可看,误武装的自愈)。

--replay 模式(离线回验):journal 全文件扫描,逐局输出 P1 末 HP/金 与
would-alert(判据面与 watch 同一 feed)。

环境变量:CW_EARLYSTOP_JSONL(journal 路径)、CW_EARLYSTOP_TH(HP 观察线,
默认 70)、CW_EARLYSTOP_GOLD_TH(金验收线,默认 50)、CW_EARLYSTOP_LOCK。

历史:v1(2026-08-24) P1 末 HP 读 outcomes 真值;v0 用 decisions 备战帧;
v3 金主判据([28]);v4 尾读源切 journal(本版)。
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import psutil

sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

# 单实例锁(2026-08-26 重复武装事故后三件齐备):已有活实例 → 退出;陈旧锁自动覆盖。
LOCK = Path(os.environ.get(
    'CW_EARLYSTOP_LOCK',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\cw_early_stop.lock'))

JOURNAL = Path(os.environ.get(
    'CW_EARLYSTOP_JSONL',
    r'D:\code\workspace\StarRailOneDragon\.debug\currency_war\telemetry\live'
    r'\state\journal.jsonl'))
TH = int(os.environ.get('CW_EARLYSTOP_TH', '70'))
STALE_SEC = 900          # 启动时 mtime 超此值 = 无活跃局
IDLE_NOTE_SEC = 1800     # watch 中无新行的提醒阈值(打印不退出)

GOLD_TH = int(os.environ.get('CW_EARLYSTOP_GOLD_TH', '50'))  # [28] 位面1节奏基准
# 实机段形态(telemetry/state.start_run 铸造口径 run_%Y%m%d_%H%M%S);
# fake_/sim_ 段与 harness 短 id 段不采信(隔离约定 =
# sim/cw_delta_pool_gen.QUARANTINED_RUN_PREFIXES,三件哨兵同口径)。
RUN_ID_RE = re.compile(os.environ.get('CW_EARLYSTOP_RUN_RE', r'^run_\d{8}_\d{6}$'))


def _acquire_lock() -> bool:
    if LOCK.exists():
        try:
            old = psutil.Process(int(LOCK.read_text().strip()))
            if 'cw_early_stop' in ' '.join(old.cmdline()).lower():
                print(f'[earlystop] 已有实例在岗 pid={old.pid},本次退出(防重复武装)', flush=True)
                return False
        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied,
                psutil.ZombieProcess):
            pass
    LOCK.write_text(str(os.getpid()))
    return True


def _parse(line: str):
    """journal 行 → (run_id, plane, hp, streak, gold);非实机段/坏行返回 None。

    journal 是多写者单文件:sim 批 fake_/sim_ 段与 harness 短 id 段同流交错
    (隔离约定 = sim/cw_delta_pool_gen.QUARANTINED_RUN_PREFIXES),只认实机
    段形态 run_%Y%m%d_%H%M%S(telemetry/state.start_run 铸造口径)。坏行
    逐行跳过 = journal.md §5 宽容消费契约。字段从行内 state.values 快照取
    (journal.md §4 自足快照行),缺字段返 None(调用方按「无数据」处理)。"""
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        return None
    rid = d.get('run_id')
    if not isinstance(rid, str) or not RUN_ID_RE.match(rid):
        return None
    values = (d.get('state') or {}).get('values') or {}
    node = values.get('node') or {}
    plane = node.get('plane')
    return (rid, plane, values.get('hp'), values.get('streak'), values.get('gold'))


class RunState:
    """单局的 P1 追踪。"""

    def __init__(self, rid: str) -> None:
        self.rid = rid
        self.p1_last_hp: int | None = None
        self.p1_last_gold: int | None = None
        self.p1_evaluated = False
        self.streak_noted = False

    def feed(self, plane, hp: int | None, streak, gold: int | None) -> str | None:
        """喂一行 journal 快照;返回报警消息(或 None)。"""
        if plane == 1:
            if hp is not None:
                self.p1_last_hp = hp
            if gold is not None:
                self.p1_last_gold = gold
            if not self.streak_noted and isinstance(streak, int) and streak < 0:
                self.streak_noted = True
                print(f'[STREAK-BROKEN] {self.rid} P1 streak={streak}(连胜断,经济信号)', flush=True)
            return None
        if plane is not None and plane > 1 and not self.p1_evaluated:
            self.p1_evaluated = True
            # v4:单源 journal(P1 段末行快照值;行流含结算覆盖,见文件头)
            if self.p1_last_hp is None and self.p1_last_gold is None:
                print(f'[SKIP] {self.rid} 无 P1 journal 行(采集缺口),不判', flush=True)
                return None
            final_hp = self.p1_last_hp
            exit_gold = self.p1_last_gold
            src = 'journal'
            gold_part = f' 出口金={exit_gold}' if exit_gold is not None else ' 出口金=?'
            # v3 判据([28] 目标函数修正)原样:金是 P1 验收主判据,HP 降为观察信号
            if exit_gold is not None and exit_gold < GOLD_TH:
                return (f'[EARLY-STOP-ALERT] {self.rid} 位面1出口金={exit_gold} < {GOLD_TH} '
                        f'(src={src}{gold_part} HP={final_hp};[28] 50金通关P1 未达——早停候选)')
            if final_hp is not None and final_hp <= 1:
                return (f'[EARLY-STOP-ALERT] {self.rid} 位面1结束 HP={final_hp} '
                        f'(src={src}{gold_part};真死局——早停候选)')
            # HP 低=观察报警([18] hp 是运营质量报警不是停局触发),不推荐停局
            if final_hp is not None and final_hp < TH:
                print(f'[P1-HP-LOW-OBSERVE] {self.rid} P1末HP={final_hp} < {TH} '
                      f'(src={src}{gold_part};[18] 报警观察不停局——判读看形态/金/锁线)', flush=True)
                return None
            print(f'[P1-OK] {self.rid} P1末HP={final_hp} ≥ {TH}{gold_part} (src={src})', flush=True)
        return None


def replay() -> None:
    """离线回验:journal 全文件扫描,逐局 P1 末 HP/金 + would-alert。"""
    runs: dict[str, RunState] = {}
    order: list[str] = []
    for raw in JOURNAL.open(encoding='utf-8', errors='replace'):
        if not raw.strip():
            continue
        parsed = _parse(raw)
        if parsed is None:
            continue
        rid, plane, hp, streak, gold = parsed
        if rid not in runs:
            runs[rid] = RunState(rid)
            order.append(rid)
        runs[rid].feed(plane, hp, streak, gold)
    print(f'replay {JOURNAL.name}: {len(order)} 实机段,阈值 P1末HP<{TH} 金<{GOLD_TH}(src=journal)')
    n_alert = 0
    for rid in order:
        s = runs[rid]
        if not s.p1_evaluated:
            print(f'  {rid}: 死于P1/未进P2, P1末HP={s.p1_last_hp} 金={s.p1_last_gold}')
            continue
        final, gold = s.p1_last_hp, s.p1_last_gold
        hit = False
        why = 'ok'
        if gold is not None and gold < GOLD_TH:
            hit, why = True, f'金{gold}<{GOLD_TH}([28]未达)'
        elif final is not None and final <= 1:
            hit, why = True, f'HP{final}=死局'
        n_alert += hit
        gtxt = f' 金={gold}' if gold is not None else ' 金=?'
        print(f'  {rid}: P1末HP={final}{gtxt} -> {"ALERT("+why+")" if hit else "ok/observe"}')
    print(f'would-alert {n_alert}/{len(order)}')


def watch() -> None:
    if not _acquire_lock():
        sys.exit(0)
    if not JOURNAL.exists():
        print(f'[FATAL] {JOURNAL} 不存在', flush=True)
        sys.exit(1)
    age = time.time() - JOURNAL.stat().st_mtime
    if age > STALE_SEC:
        print(f'[NO_ACTIVE_RUN] {JOURNAL.name} mtime {int(age)}s 前,无局在跑', flush=True)
        sys.exit(0)
    cur: RunState | None = None
    buf = ''
    last_row_wall = time.time()
    noted_idle = False
    print(f'[earlystop] armed v4 @ {time.strftime("%H:%M:%S")} th={TH} '
          f'gold_th={GOLD_TH} pos=end-of-file journal={JOURNAL.name}', flush=True)
    # 中途武装回填(06:0x 实证:局中途武装时 P1 行在 pos 之前,P2 首行到来
    # 会误报「无 P1 遥测行」):武装时从文件尾向上回扫最近的行,若当前局
    # 仍处 P1,预填 p1_last_hp/p1_last_gold——恢复 P1 上下文。只回填数值,
    # 不追历史报警。
    with JOURNAL.open(encoding='utf-8', errors='replace') as _fh:
        _fh.seek(0, 2)
        _tail_start = max(0, _fh.tell() - 2_000_000)   # 末 2MB(journal 行≈KB 级,足覆盖一局)
        _fh.seek(_tail_start)
        _tail = _fh.read().splitlines()
    for _ln in reversed(_tail):
        parsed = _parse(_ln)
        if parsed is None:
            continue
        rid, plane, hp, streak, gold = parsed
        if plane == 1:
            cur = RunState(rid)
            cur.p1_last_hp = hp
            cur.p1_last_gold = gold
            cur.streak_noted = True   # 历史不追报
            print(f'[earlystop] 回填当前局 {rid} P1 上下文 hp={hp} gold={gold}', flush=True)
            break
        break   # 尾行已是 P2+:当前局 P1 已结束,从头等下一局(不回填)
    with JOURNAL.open(encoding='utf-8', errors='replace') as fh:
        fh.seek(0, 2)  # 从文件尾开始:只看武装后的新局
        while True:
            line = fh.readline()
            if line:
                last_row_wall = time.time()
                noted_idle = False
                buf += line
                if not buf.endswith('\n'):
                    continue  # 半行,等写完
                full, buf = buf, ''
                parsed = _parse(full)
                if parsed is None:
                    continue
                rid, plane, hp, streak, gold = parsed
                if cur is None or rid != cur.rid:
                    if cur is not None and not cur.p1_evaluated:
                        print(f'[RUN_ENDED_IN_P1] {cur.rid} P1末HP={cur.p1_last_hp}'
                              f' 金={cur.p1_last_gold}(未进P2)', flush=True)
                    cur = RunState(rid)
                msg = cur.feed(plane, hp, streak, gold)
                if msg:
                    print(msg, flush=True)
                    sys.exit(0)
            else:
                if JOURNAL.stat().st_size < fh.tell():  # 文件被替换(purge/重建) → 从头重置
                    fh.seek(0)
                    cur = None
                    buf = ''
                    print('[earlystop] 文件变小(轮换/清理),重置追踪', flush=True)
                    continue
                if not noted_idle and time.time() - last_row_wall > IDLE_NOTE_SEC:
                    noted_idle = True
                    print(f'[IDLE] {IDLE_NOTE_SEC}s 无新 journal 行(局可能已结束或战斗漫长)', flush=True)
                time.sleep(10)


if __name__ == '__main__':
    if '--replay' in sys.argv:
        replay()
    else:
        watch()
