# -*- coding: utf-8 -*-
"""W454 G1 标定:散件单卡 1★→2★ 直接增量 vs 体系激活增量(离线复算,零实机)。

数据源(在盘逐帧 sim 台账,w42/w43 各 n=400,池指纹 fd48f135):
  .debug/temp/currency_war/cw_dev/baselines/w42_old_arm_p1_n400_s0_fd48f135/
  .debug/temp/currency_war/cw_dev/baselines/w43_new_arm_p1_n400_s0_fd48f135/

方法与预注册判读规则见同目录 CALIB_DESIGN.md(口径:胜利=sim.killed,Δhp=sim.delta;
事件=1★→2★ 合成 vs 引擎跨档激活;对照=同层(轮桶×e_before×cap)非事件战斗 + 事件自身前窗)。
纯标准库实现,复跑:uv run python w454_g1_calib.py(建议 PYTHONIOENCODING=utf-8)。
"""
import json
import math
import random
from collections import defaultdict
from pathlib import Path

BASE = Path('.debug/temp/currency_war/cw_dev/baselines')
LEDGERS = [
    BASE / 'w42_old_arm_p1_n400_s0_fd48f135',
    BASE / 'w43_new_arm_p1_n400_s0_fd48f135',
]
BATTLE_NODES = {'普通战斗', '首领'}
# 过渡体系阈值表(单一源 docs/game/currency_war/research/transition_combos.md 定稿)
ENGINE_MIN = {'仙舟': 3, '持续伤害': 2, '列车同行': 2}
HILDA = '希儿'
ROUND_BUCKET = lambda r: 'r1-3' if r <= 3 else ('r4-6' if r <= 6 else 'r7-9')


def engine_e(board_factions: dict, deployed_names: set) -> int:
    """体系达成数 e(封顶 2),口径=transition_combos 阈值;希儿系=希儿在场∧(量子≥2∨贝洛伯格≥2)。"""
    e = 0
    for fac, need in ENGINE_MIN.items():
        if board_factions.get(fac, 0) >= need:
            e += 1
    if HILDA in deployed_names and (board_factions.get('量子', 0) >= 2 or board_factions.get('贝洛伯格', 0) >= 2):
        e += 1
    return min(e, 2)


def is_transition_member(faction: str, name: str) -> bool:
    return faction in ENGINE_MIN or name == HILDA


def load_runs(ledger: Path) -> dict:
    """返回 {run_id: {'dec': [帧按 ts], 'out': [战斗结局按 ts]}}。"""
    runs = defaultdict(lambda: {'dec': [], 'out': {}})
    with open(ledger / 'decisions.jsonl', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            runs[r['run_id']]['dec'].append(r)
    with open(ledger / 'outcomes.jsonl', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            runs[r['run_id']]['out'][r['ts']] = r
    for v in runs.values():
        v['dec'].sort(key=lambda r: r['ts'])
    return dict(runs)


def extract_events(runs: dict, src: str):
    """状态机提取:星升事件 S、体系激活事件 A,附各自前窗基线与同层对照键。"""
    events = []
    battles = []  # 全部战斗窗(对照池):dict(src, run, ts, round, e_before, cap, win, delta, event_ts=set)
    for run_id, v in sorted(runs.items()):
        dec, out = v['dec'], v['out']
        copies = defaultdict(int)      # 角色名 -> 持有 1★ 副本数
        cost = {}                      # 角色名 -> 卡费(由最近一次买入记)
        star = defaultdict(int)        # 角色名 -> 当前最高星(0/1/2)
        merged_once = set()            # 已发生 1★→2★ 的角色(辖域:只记首次)
        prev_e = None
        prev_fac = {}
        run_events = []
        battle_rows = []
        # 先扫战斗窗(含事件 ts 集合,供对照池排除)
        for r in dec:
            ts, rnd = r['ts'], r['round_num']
            fac = r['state'].get('board_factions', {})
            dep_names = {d['char_id'] for d in r['state'].get('deployed', [])}
            e_now = engine_e(fac, dep_names)
            o = out.get(ts)
            is_battle = o is not None and o['node_type'] in BATTLE_NODES
            row = None
            if is_battle:
                row = {'src': src, 'run': run_id, 'ts': ts, 'round': rnd,
                       'e_before': prev_e if prev_e is not None else e_now,
                       'cap': r['state'].get('cap'), 'win': bool(o['sim']['killed']),
                       'delta': int(o['sim']['delta']), 'event_ts': set()}
                battle_rows.append(row)
            # 引擎跨档激活 A:相邻帧 e 抬升
            if prev_e is not None and e_now > prev_e and e_now <= 2:
                run_events.append({'kind': 'A', 'run': run_id, 'ts': ts, 'round': rnd,
                                   'e_before': prev_e, 'e_after': e_now, 'row': row})
            if row is not None:
                row['e_calc_now'] = e_now
            prev_e, prev_fac = e_now, fac
        # 再扫 actions 提取合成事件 S(需与上面 row 对齐:同帧 row)
        row_by_ts = {b['ts']: b for b in battle_rows}
        prev_e2 = None
        for r in dec:
            ts = r['ts']
            for a in r.get('actions', []):
                if a['__type__'] == 'BuyCard':
                    name = a['card']['name']
                    cost[name] = a['card'].get('cost', 1)
                    copies[name] += 1
                    if copies[name] >= 3 and name not in merged_once:
                        merged_once.add(name)
                        star[name] = 2
                        copies[name] -= 3
                        run_events.append({'kind': 'S', 'run': run_id, 'ts': ts,
                                           'round': r['round_num'],
                                           'name': name, 'faction': a['card']['faction'],
                                           'cost': cost[name],
                                           'member': is_transition_member(a['card']['faction'], name),
                                           'row': row_by_ts.get(ts)})
                elif a['__type__'] == 'SellBench':
                    name = a.get('name')
                    inc = a.get('income', 0)
                    if name is None:
                        continue
                    if star.get(name, 0) == 2 and inc >= 3:
                        star[name] = 0  # 卖 2★
                    elif copies.get(name, 0) > 0:
                        copies[name] -= 1  # 卖 1★(3费1★ income=3 歧义帧按 1★ 记,见 DESIGN §4)
        # e_before 修正:A 事件帧若也是战斗帧,row 的 e_before 用跨档前值
        for ev in run_events:
            if ev['kind'] == 'A' and ev['row'] is not None:
                ev['row']['e_before'] = ev['e_before']
        events.extend(run_events)
        battles.extend(battle_rows)
    return events, battles


def next_battles_after(battles_by_run, run, ts, k=1):
    """事件后同局前 k 个战斗窗。"""
    lst = battles_by_run[run]
    return [b for b in lst if b['ts'] > ts][:k]


def prev_battle_before(battles_by_run, run, ts):
    lst = battles_by_run[run]
    cand = [b for b in lst if b['ts'] < ts]
    return cand[-1] if cand else None


def strat_key(b):
    return (ROUND_BUCKET(b['round']), b['e_before'] if b['e_before'] is not None else 9, b['cap'])


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float('nan')


def se_prop(win_list):
    n = len(win_list)
    if n == 0:
        return float('nan')
    p = sum(win_list) / n
    return math.sqrt(p * (1 - p) / n)


def welch(a, b):
    """返回 (diff, se_diff)。a/b 为 0/1 列表(胜率)或数值列表(hp)。"""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float('nan'), float('nan')
    ma, mb = mean(a), mean(b)
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    se = math.sqrt(va / na + vb / nb)
    return ma - mb, se


def bootstrap_ratio(ev_vals, ctl_vals, n=2000, seed=7):
    """A/S 倍数的不确定度:对两个净增量分别自助重抽。"""
    rng = random.Random(seed)
    ratios = []
    for _ in range(n):
        ea = mean(rng.choice(ev_vals) for _ in range(len(ev_vals)))
        ec = mean(rng.choice(ctl_vals) for _ in range(len(ctl_vals)))
        sa = mean(rng.choice(ev_vals) for _ in range(len(ev_vals)))
        sc = mean(rng.choice(ctl_vals) for _ in range(len(ctl_vals)))
        if abs(sc) < 1e-9:
            continue
        ratios.append(ea / sa if abs(sa) > 1e-9 else None)
    return ratios


def net_estimate(events, battles_by_run, all_battles, metric):
    """净增量 = 事件窗值 − 同层对照均值,分层加权;附自身前窗差。"""
    # 对照池:排除事件帧(任意 S/A,用 is_event 标记)
    strat_controls = defaultdict(lambda: {'win': [], 'delta': []})
    for b in all_battles:
        if b['is_event']:
            continue
        strat_controls[strat_key(b)]['win'].append(int(b['win']))
        strat_controls[strat_key(b)]['delta'].append(b['delta'])
    treat = {'win': [], 'delta': [], 'prev_win': [], 'prev_delta': [], 'net_win': [], 'net_delta': []}
    n_used = n_noctl = 0
    for ev in events:
        if ev['row'] is None:
            continue
        b = ev['row']
        ctl = strat_controls.get(strat_key(b))
        if not ctl or not ctl['win']:
            n_noctl += 1
            continue
        n_used += 1
        mv = int(b['win']) if metric == 'win' else b['delta']
        cv = ctl[metric]
        treat['net_' + metric].append(mv - mean(cv))
        treat[metric].append(mv)
        pb = prev_battle_before(battles_by_run, (b['src'], b['run']), b['ts'])
        if pb is not None:
            pv = int(pb['win']) if metric == 'win' else pb['delta']
            treat['prev_' + metric].append(pv)
    return {'n_used': n_used, 'n_noctl': n_noctl,
            'raw': mean(treat[metric]), 'net': mean(treat['net_' + metric]),
            'prev': mean(treat['prev_' + metric]),
            'net_vals': treat['net_' + metric]}


def main():
    all_events, all_battles = [], []
    battles_by_run = defaultdict(list)
    for ledger in LEDGERS:
        src = ledger.name.split('_')[0]
        runs = load_runs(ledger)
        ev, bt = extract_events(runs, src)
        all_events.extend(ev)
        all_battles.extend(bt)
        for b in bt:
            battles_by_run[(src, b['run'])].append(b)
    # 事件标记到战斗窗
    ev_keys = set()
    for e in all_events:
        if e['row'] is not None:
            ev_keys.add((e['row']['src'], e['row']['run'], e['ts']))
    for b in all_battles:
        if (b['src'], b['run'], b['ts']) in ev_keys:
            b['is_event'] = True
        else:
            b['is_event'] = False

    s_events = [e for e in all_events if e['kind'] == 'S']
    a_events = [e for e in all_events if e['kind'] == 'A']
    s_with_battle = [e for e in s_events if e['row'] is not None]
    a_with_battle = [e for e in a_events if e['row'] is not None]
    s_loose = [e for e in s_with_battle if not e['member']]
    s_member = [e for e in s_with_battle if e['member']]
    a_e01 = [e for e in a_with_battle if e['e_before'] == 0]
    a_e12 = [e for e in a_with_battle if e['e_before'] == 1]

    print(f'== 事件提取 ==')
    print(f'S 合成事件总数={len(s_events)}  其中事件帧即战斗帧={len(s_with_battle)} '
          f'(体系成员={len(s_member)} 散件={len(s_loose)})')
    print(f'A 激活事件总数={len(a_events)}  战斗帧={len(a_with_battle)} (e0->1={len(a_e01)} e1->2={len(a_e12)})')
    print(f'对照战斗窗总数={sum(1 for b in all_battles if not b["is_event"])} / 全部战斗窗={len(all_battles)}')

    results = {}
    for metric in ('win', 'delta'):
        print(f'\\n== 指标: {"次战胜率" if metric == "win" else "次战 Δhp"} ==')
        for label, evs in (('S_全部合成', s_with_battle), ('S_散件', s_loose),
                           ('A_全部激活', a_with_battle), ('A_e0->1', a_e01), ('A_e1->2', a_e12)):
            est = net_estimate(evs, battles_by_run, all_battles, metric)
            results[f'{label}_{metric}'] = est
            pv = est['prev']
            print(f'{label}: n={est["n_used"]}(无对照弃={est["n_noctl"]}) '
                  f'原始={est["raw"]:.4f} 前窗基线={pv:.4f} 净(分层对照)={est["net"]:.4f}')

    # 主估计:A/S 净增量比(welch + 自助,两个指标;S 分全部/散件两口径)
    print('\\n== P20 量级裁决(预注册判据见 CALIB_DESIGN §2) ==')
    for metric, unit in (('win', '胜率'), ('delta', 'Δhp')):
        ea = results[f'A_全部激活_{metric}']
        for slabel in ('S_全部合成', 'S_散件'):
            es = results[f'{slabel}_{metric}']
            if es['n_used'] and ea['n_used']:
                d, se = welch(ea['net_vals'], es['net_vals'])
                lo, hi = d - 1.96 * se, d + 1.96 * se
                ratio = ea['net'] / es['net'] if abs(es['net']) > 1e-9 else float('inf')
                print(f'{unit} {slabel}: A净={ea["net"]:.4f} S净={es["net"]:.4f} '
                      f'差={d:.4f} CI[{lo:.4f},{hi:.4f}] 倍数A/S={ratio:.2f}')
            else:
                print(f'{unit} {slabel}: 样本不足(A n={ea["n_used"]} / S n={es["n_used"]})')

    out = {'events_S': len(s_events), 'events_S_battle': len(s_with_battle),
           'events_S_loose': len(s_loose), 'events_A': len(a_events),
           'results': {k: {kk: (vv if not isinstance(vv, list) else None)
                           for kk, vv in v.items()} for k, v in results.items()}}
    Path('results_w454.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('\\n[written] results_w454.json')


if __name__ == '__main__':
    main()
