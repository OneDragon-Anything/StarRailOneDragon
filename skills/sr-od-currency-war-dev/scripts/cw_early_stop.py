# -*- coding: utf-8 -*-
"""早停监视 v3(只报不停,停局决策归主 agent)。

判据 v3(2026-08-25 目标函数修正,对齐口述 [28]+[18],用户点破五局误判后重写;
2026-08-26 W94 口径修正注释——只改说明,判据逻辑不动,逻辑重构归后续批):
  **位面1的目标=[28] 双指标验收:息基保住 × 形态达标**(出口 ~50 金是守息的
  表征,不是单指标验收目标;[28] 最高权威:进 P2 应携 ~50 金;赢 boss 但
  花光=「打过了也没经济通关」)。
  - 真停局候选:P1 出口金 < 50(息基未保住表征,候选线索非验收线)或 HP=1
    (真死局);
  - HP<70 → **[P1-HP-LOW-OBSERVE] 观察报警不停局**([18]:hp 低=运营质量报警
    不是 ALL IN/停局触发;正确响应=判读看形态/金/锁线,不是停);
  - 判读框架(配套,cw skill 判读前置门):P1 目标=[28] 双指标(息基保住×
    power_baseline 形态白名单内)+过渡核心 2★([13] 成型停手线)——HP 单维
    从来不是 P1 验收,出口金单维也不是(表征非验收)。
  历史:v1(2026-08-24) P1 末 HP 读 outcomes 真值;v0 用 decisions 备战帧。
  v3 之前 HP<70 即 ALERT 推荐停局——五局实证此为错误目标函数(五局全被
  误停/误判,判读叙事被带偏)。

数据源:replay/decisions.jsonl 每轮追加(state 含 hp/plane/streak)+
outcomes.jsonl(hp_after/gold_after 真值)。

watch 模式(默认,武装在有局时):tail 文件,plane==2 首行出现 = P1 结束,
评估后继续看下一局;真停局候选 → [EARLY-STOP-ALERT] 打印+exit(推送唤醒);
HP 低 → [P1-HP-LOW-OBSERVE] 打印后继续 watch。
新 run_id 切换时若旧局死在 P1 未评估 → 记一行 RUN_ENDED_IN_P1。
附加信号:P1 期间 streak 首次转负 → 打印 [STREAK-BROKEN] 记录(不退出)。
启动时文件 mtime 超 15 分钟 → NO_ACTIVE_RUN 退出(无局可看,误武装的自愈)。
--replay 模式(离线回验):整文件扫描,逐局输出 P1 末 HP/金 与 would-alert。
环境变量:CW_EARLYSTOP_JSONL(数据文件)、CW_EARLYSTOP_TH(HP 观察线,默认70)、
CW_EARLYSTOP_GOLD_TH(金验收线,默认50)、CW_EARLYSTOP_OUTCOMES(真值源)。
"""
import json
import os
import sys
import time
from pathlib import Path

import psutil

sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

# 单实例锁(2026-08-26 重复武装事故后三件齐备):已有活实例 → 退出;陈旧锁自动覆盖。
LOCK = Path(os.environ.get(
    'CW_EARLYSTOP_LOCK',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\cw_early_stop.lock'))


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

JSONL = Path(os.environ.get(
    'CW_EARLYSTOP_JSONL',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\replay\decisions.jsonl'))
OUTCOMES = Path(os.environ.get(
    'CW_EARLYSTOP_OUTCOMES',
    r'D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\replay\outcomes.jsonl'))
TH = int(os.environ.get('CW_EARLYSTOP_TH', '70'))
STALE_SEC = 900          # 启动时 mtime 超此值 = 无活跃局
IDLE_NOTE_SEC = 1800     # watch 中无新行的提醒阈值(打印不退出)


def p1_final_hp_from_outcomes(rid: str) -> int | None:
    """v1:当前局 P1 最后一条 outcomes 行的 hp_after(结算屏真值)。

    outcomes 只在结算时落行(战斗/奖励/遭遇/boss),p1 r9 boss 行的
    hp_after 即 P1 终值——boss 伤害可见(v0 缺陷的修复点)。
    全文件扫 rid 行(局级量级,几十行),无 P1 行返 None(采集缺口)。
    """
    if not OUTCOMES.exists():
        return None
    last: int | None = None
    with OUTCOMES.open(encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if d.get('run_id') != rid:
                continue
            if d.get('plane') != 1:
                continue
            hp = d.get('hp_after')
            if isinstance(hp, int):
                last = hp
    return last


def p1_exit_gold_from_outcomes(rid: str) -> int | None:
    """v3:P1 末金(进 P2 前的携金,[28] 50 金通关 P1 的验收值)。

    outcomes 现无 gold_after 字段(2026-08-25 核)——回退读 decisions.jsonl
    该局 P1 末轮的 state.gold(boss 备战帧金≈出口金,boss 轮 [32] 禁高消费
    故备战帧≈真值);两处都无返 None(采集缺口,判 observe 不判 ALERT)。
    """
    if not OUTCOMES.exists():
        return None
    # 先试 outcomes(未来加 gold_after 时自动启用)
    last: int | None = None
    with OUTCOMES.open(encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if d.get('run_id') != rid or d.get('plane') != 1:
                continue
            g = d.get('gold_after')
            if isinstance(g, int):
                last = g
    if last is not None:
        return last
    # 回退:decisions 的 P1 末行 state.gold
    if not JSONL.exists():
        return None
    with JSONL.open(encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if d.get('run_id') != rid or d.get('plane') != 1:
                continue
            g = (d.get('state') or {}).get('gold')
            if isinstance(g, int):
                last = g
    return last


GOLD_TH = int(os.environ.get('CW_EARLYSTOP_GOLD_TH', '50'))  # [28] 位面1节奏基准


class RunState:
    """单局的 P1 追踪。"""

    def __init__(self, rid: str) -> None:
        self.rid = rid
        self.p1_last_hp: int | None = None
        self.p1_evaluated = False
        self.streak_noted = False

    def feed(self, plane, hp: int | None, streak) -> str | None:
        """喂一行;返回报警消息(或 None)。"""
        if plane == 1:
            if hp is not None:
                self.p1_last_hp = hp
            if not self.streak_noted and isinstance(streak, int) and streak < 0:
                self.streak_noted = True
                print(f'[STREAK-BROKEN] {self.rid} P1 streak={streak}(连胜断,经济信号)', flush=True)
            return None
        if plane is not None and plane > 1 and not self.p1_evaluated:
            self.p1_evaluated = True
            # v1:优先 outcomes 真值(boss 后),回退 decisions 备战帧
            true_hp = p1_final_hp_from_outcomes(self.rid)
            if true_hp is not None:
                final_hp, src = true_hp, 'outcomes'
            elif self.p1_last_hp is not None:
                final_hp, src = self.p1_last_hp, 'FALLBACK-DECISIONS'
            else:
                print(f'[SKIP] {self.rid} 无 P1 遥测行(采集缺口),不判', flush=True)
                return None
            # v3([28] 目标函数修正):金是 P1 验收主判据,HP 降为观察信号
            exit_gold = p1_exit_gold_from_outcomes(self.rid)
            gold_part = f' 出口金={exit_gold}' if exit_gold is not None else ' 出口金=?'
            # 真停局候选:P1 出口金 < 50([28] 未达标)或 HP=1(真死局)
            if exit_gold is not None and exit_gold < GOLD_TH:
                return (f'[EARLY-STOP-ALERT] {self.rid} 位面1出口金={exit_gold} < {GOLD_TH} '
                        f'(src={src}{gold_part} HP={final_hp};[28] 50金通关P1 未达——早停候选)')
            if final_hp <= 1:
                return (f'[EARLY-STOP-ALERT] {self.rid} 位面1结束 HP={final_hp} '
                        f'(src={src}{gold_part};真死局——早停候选)')
            # HP 低=观察报警([18] hp 是运营质量报警不是停局触发),不推荐停局
            if final_hp < TH:
                print(f'[P1-HP-LOW-OBSERVE] {self.rid} P1末HP={final_hp} < {TH} '
                      f'(src={src}{gold_part};[18] 报警观察不停局——判读看形态/金/锁线)', flush=True)
                return None
            print(f'[P1-OK] {self.rid} P1末HP={final_hp} ≥ {TH}{gold_part} (src={src})', flush=True)
        return None


def _parse(line: str):
    import json
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        return None
    rid = d.get('run_id')
    if rid is None:
        return None
    st = d.get('state') or {}
    return rid, d.get('plane'), d.get('hp', st.get('hp')), st.get('streak')


def replay() -> None:
    """离线回验:逐局 P1 末 HP + would-alert。"""
    runs: dict[str, RunState] = {}
    order: list[str] = []
    for raw in JSONL.open(encoding='utf-8'):
        if not raw.strip():
            continue
        parsed = _parse(raw)
        if parsed is None:
            continue
        rid, plane, hp, streak = parsed
        if rid not in runs:
            runs[rid] = RunState(rid)
            order.append(rid)
        runs[rid].feed(plane, hp, streak)
    print(f'replay {JSONL.name}: {len(order)} 局,阈值 P1末HP<{TH}(src=outcomes)')
    n_alert = 0
    for rid in order:
        s = runs[rid]
        if not s.p1_evaluated:
            print(f'  {rid}: 死于P1/无P2行, P1末HP={s.p1_last_hp}')
            continue
        true_hp = p1_final_hp_from_outcomes(rid)
        v0_hp = s.p1_last_hp
        final = true_hp if true_hp is not None else v0_hp
        gold = p1_exit_gold_from_outcomes(rid)
        # v3 判据:金 <50 → ALERT([28] 未达);HP=1 → ALERT(死局);HP 低 → observe
        hit = False
        why = 'ok'
        if gold is not None and gold < GOLD_TH:
            hit, why = True, f'金{gold}<{GOLD_TH}([28]未达)'
        elif final is not None and final <= 1:
            hit, why = True, f'HP{final}=死局'
        n_alert += hit
        drift = '' if true_hp == v0_hp or true_hp is None or v0_hp is None \
            else f' (v0备战帧={v0_hp}, 真值差={true_hp - v0_hp:+d})'
        gtxt = f' 金={gold}' if gold is not None else ' 金=?'
        print(f'  {rid}: P1末HP={final}{gtxt}{drift} -> {"ALERT("+why+")" if hit else "ok/observe"}')
    print(f'would-alert {n_alert}/{len(order)}')


def watch() -> None:
    if not _acquire_lock():
        sys.exit(0)
    if not JSONL.exists():
        print(f'[FATAL] {JSONL} 不存在', flush=True)
        sys.exit(1)
    age = time.time() - JSONL.stat().st_mtime
    if age > STALE_SEC:
        print(f'[NO_ACTIVE_RUN] {JSONL.name} mtime {int(age)}s 前,无局在跑', flush=True)
        sys.exit(0)
    cur: RunState | None = None
    buf = ''
    last_row_wall = time.time()
    noted_idle = False
    print(f'[earlystop] armed @ {time.strftime("%H:%M:%S")} th={TH} pos=end-of-file', flush=True)
    # 中途武装回填(06:0x 实证:局中途武装时 P1 行在 pos 之前,P2 首行到来
    # 会误报「无 P1 遥测行」):武装时从文件尾向上回扫最近的行,若当前局
    # 仍处 P1,预填 p1_last_hp——恢复 P1 上下文。只回填 hp,不追历史报警。
    import json as _json
    with JSONL.open(encoding='utf-8', errors='replace') as _fh:
        _fh.seek(0, 2)
        _tail_start = max(0, _fh.tell() - 200_000)   # 末 200KB 足够覆盖一局
        _fh.seek(_tail_start)
        _tail = _fh.read().splitlines()
    for _ln in reversed(_tail):
        try:
            _d = _json.loads(_ln)
        except Exception:
            continue
        if _d.get('run_id') is None or _d.get('plane') is None:
            continue
        if _d['plane'] == 1:
            cur = RunState(_d['run_id'])
            cur.p1_last_hp = _d.get('hp')
            cur.streak_noted = True   # 历史不追报
            print(f'[earlystop] 回填当前局 { _d["run_id"] } P1 上下文 hp={_d.get("hp")}', flush=True)
            break
        break   # 尾行已是 P2+:当前局 P1 已结束,从头等下一局(不回填)
    with JSONL.open(encoding='utf-8', errors='replace') as fh:
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
                rid, plane, hp, streak = parsed
                if cur is None or rid != cur.rid:
                    if cur is not None and not cur.p1_evaluated:
                        print(f'[RUN_ENDED_IN_P1] {cur.rid} P1末HP={cur.p1_last_hp}(未进P2)', flush=True)
                    cur = RunState(rid)
                msg = cur.feed(plane, hp, streak)
                if msg:
                    print(msg, flush=True)
                    sys.exit(0)
            else:
                if JSONL.stat().st_size < fh.tell():  # 文件被替换(purge/重建) → 从头重置
                    fh.seek(0)
                    cur = None
                    buf = ''
                    print('[earlystop] 文件变小(轮换/清理),重置追踪', flush=True)
                    continue
                if not noted_idle and time.time() - last_row_wall > IDLE_NOTE_SEC:
                    noted_idle = True
                    print(f'[IDLE] {IDLE_NOTE_SEC}s 无新遥测行(局可能已结束或战斗漫长)', flush=True)
                time.sleep(10)


if __name__ == '__main__':
    if '--replay' in sys.argv:
        replay()
    else:
        watch()
