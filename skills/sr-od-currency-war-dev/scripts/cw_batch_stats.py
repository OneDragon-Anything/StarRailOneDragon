"""批统计面(九族过程量:资源转化/成型/战斗/供给/达标臂发射/终态/采购面三观察…;2026-09-07 反馈条目落地,发射面/采购观察/必花域观测为后补族)。

定位:第 1 步统计+按指标点名最差局(供第 3 步挑局复盘);怎么判定「表现不好」不在此规定。
两种数据源:
    --sim-batch <名|latest>   sim 批次目录三流账本(ADR-0242 同构)
    --recent N / --match ID   生产对局档案(matches/;词缀条件化分组仅此模式——sim 未建模词条)

用法(项目根):
    uv run python skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py --sim-batch latest
    uv run python skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py --recent 10

口径注记(判读时心里有数):
- 胜/败从 hp 链推导(战斗类节点 hp 下降=败),无显式字段;生产档案用 hp_delta;
- 「核心二星」用「任意 deployed 2★」近似;供给利用的「相关卡」=阵营与板面交集(游戏语义);
- 「危局空转」= 连败≥2 或 hp≤40 窗口内的零动作轮(复盘试金石:140843 局 R4-6 金44-57 连败不花);
- sim 侧无词缀/补给选项(未建模)——词缀分组仅档案模式;补给选择相关率挂档案二期字段缺口;
- 末尾「表现不好的指标→最差局」是纯排序,不拍阈值;哪边算差见各指标括号(高为差/低为差)。
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

SIM_ROOT = Path('.debug/temp/currency_war/sim_runs')
MATCHES = Path('.debug/temp/currency_war/replay/matches')
BATTLE_SKIP = {'奖励', '补给'}
STAGNANT_EPS = 0.02
HP_ALERT = 40          # 危局血线(占位,[18] 报警语义)


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in open(path, encoding='utf-8') if line.strip()]


def pct(vals: list[float], p: float) -> float:
    s = sorted(vals)
    return s[min(int(len(s) * p), len(s) - 1)] if s else float('nan')


# ---------- 数据装配:统一成 row{plane,round,node_type,gold,hp,hp_delta,form,form_ok,level,deployed,factions,acts} ----------

def _sim_rows(batch: Path) -> dict[str, list[dict]]:
    dec = _load(batch / 'decisions.jsonl')
    outs = _load(batch / 'outcomes.jsonl')
    games: dict[str, dict] = {}

    def g(rid: str) -> dict:
        return games.setdefault(rid, {'rounds': {}, 'outs': {}})

    for r in dec:
        st = r.get('state') or {}
        key = (r.get('plane') or 1, r.get('round_num') or 0)
        g(r.get('run_id') or '?')['rounds'][key] = {
            'plane': key[0], 'round': key[1], 'node_type': None,
            'gold': r.get('gold'), 'hp': r.get('hp'), 'hp_delta': None,
            'form': r.get('form_score'), 'form_ok': r.get('form_ok'),
            'level': st.get('level'), 'deployed': st.get('deployed') or [],
            'factions': dict(st.get('board_factions') or {}), 'acts': r.get('actions') or [],
            # 达标臂发射事件(行内 launch 键,engine_p1 建模;None=未触发)
            'launch': r.get('launch'),
            # 采购面三观察计数(行内 obs 键,engine_p1 建模;缺键=旧批)
            'obs': r.get('obs') or {},
        }
    for o in outs:
        g(o.get('run_id') or '?')['outs'][(o.get('plane') or 1, o.get('round_num') or 0)] = o
    for s in _load(batch / 'shop_snapshots.jsonl'):
        if s.get('event') == 'offer':
            g(s.get('run_id') or '?').setdefault(
                'shops', {}).setdefault((s.get('plane') or 1, s.get('round_num') or 0),
                                        []).append(s.get('shop') or [])
    out: dict[str, list[dict]] = {}
    for rid, gd in games.items():
        rows = [gd['rounds'][k] for k in sorted(gd['rounds'])]
        prev_hp = None
        for r in rows:
            r['shop_waves'] = gd.get('shops', {}).get((r['plane'], r['round']), [])
            o = gd['outs'].get((r['plane'], r['round']))
            if o:
                r['node_type'] = o.get('node_type')
                hp_after = o.get('hp_after')
                r['hp_delta'] = (None if prev_hp is None or hp_after is None
                                 else hp_after - prev_hp)
                prev_hp = hp_after
            elif r['hp'] is not None:
                prev_hp = r['hp']
        out[rid] = rows
    return out


def _archive_rows(mid: str) -> dict[str, list[dict]]:
    p = MATCHES / f'match_{mid}.json'
    if not p.exists():
        idx = _load(MATCHES / 'index.jsonl')
        hit = [e['game_id'] for e in idx if e.get('game_id', '').endswith(mid)]
        if not hit:
            raise SystemExit(f'档案不存在:{mid}')
        p = MATCHES / f'match_{hit[-1]}.json'
    m = json.loads(p.read_text(encoding='utf-8'))
    def _waves(raw) -> list[list]:
        if not isinstance(raw, list):
            return []
        ws = []
        for w in raw:
            if isinstance(w, dict):
                w = w.get('shop') or []
            ws.append(w if isinstance(w, list) else [])
        return ws

    rows = [{
        'plane': r.get('plane'), 'round': r.get('round'), 'node_type': r.get('node_type'),
        'gold': r.get('gold'), 'hp': r.get('hp'), 'hp_delta': r.get('hp_delta'),
        'form': r.get('form_score'), 'form_ok': r.get('form_ok'),
        'level': r.get('level'), 'deployed': r.get('deployed') or [],
        'factions': dict(r.get('board') or {}), 'acts': r.get('actions') or [],
        # 档案侧发射面:行动作里的 StartBattle(生产发射核执行痕迹;
        # 档案只记「发生了」,ok 恒 True——发射失败形态仅 sim/生产
        # 计数器有真值,成功率面判读以 sim 批为准)
        'launch': ({'__type__': 'StartBattle', 'ok': True}
                   if any(a.get('__type__') in ('StartBattle', 'LaunchBattle')
                          for a in r.get('actions') or []) else None),
        'shop_waves': _waves(r.get('shop_snapshots')),
        # 档案行无 sim 行内 obs 键(生产决策帧无同构计数)——采购面观察
        # 为 sim 专属,档案模式恒空 dict(统计族退化为 0/None,不误报)
        'obs': {},
    } for r in m.get('rounds', [])]
    affixes: list[str] = []
    for b in (m.get('opening', {}).get('briefing_rows') or []):
        mt = re.search(r'affixes=\[([^\]]*)\]', str(b.get('detail') or ''))
        if mt:
            affixes = [a.strip().strip("'\"") for a in mt.group(1).split(',')]
            break
    eg = m.get('endgame', {}) or {}
    return {'game_id': m.get('game_id', mid), 'rows': rows, 'affixes': affixes,
            'result': eg.get('result'), 'final_hp': eg.get('final_hp'),
            'plane_reached': eg.get('plane_reached')}


# ---------- 指标 ----------

def act_cost(acts: list[dict]) -> int:
    spend = 0
    for a in acts:
        t = a.get('__type__')
        if t == 'BuyCard':
            spend += (a.get('card') or {}).get('cost') or 0
        elif t == 'LevelUp':
            spend += a.get('cost') or 0
        elif t == 'RefreshShop':
            spend += 2
        elif t == 'SellBench':
            spend -= (a.get('cost') or (a.get('card') or {}).get('cost') or 0)
    return spend


def n_act(acts: list[dict], *ts: str) -> int:
    return sum(1 for a in acts if a.get('__type__') in ts)


def zero_action(acts: list[dict]) -> bool:
    return n_act(acts, 'BuyCard', 'LevelUp', 'RefreshShop') == 0


def analyze_game(rows: list[dict]) -> dict:
    m: dict = {}
    spends = [act_cost(r['acts']) for r in rows]
    golds = [r['gold'] for r in rows if r['gold'] is not None]
    income = (golds[-1] - golds[0] + sum(spends)) if golds else 0
    m['花费率'] = round(sum(spends) / income, 2) if income > 0 else float('nan')
    m['空转轮占比'] = round(sum(1 for r in rows if (r['gold'] or 0) >= 3 and zero_action(r['acts']))
                        / max(len(rows), 1), 2)
    # 危局空转:连败≥2(窗口内 hp_delta<0 的战斗轮)或 hp≤40 时的零动作轮
    losses = [bool(r['node_type'] not in BATTLE_SKIP and (r['hp_delta'] or 0) < 0) for r in rows]
    m['危局空转轮数'] = sum(
        1 for i, r in enumerate(rows)
        if zero_action(r['acts']) and ((r['hp'] is not None and r['hp'] <= HP_ALERT)
                                       or (i >= 2 and all(losses[i - 2:i]))))
    m['行动配比'] = {t: sum(n_act(r['acts'], t) for r in rows)
                  for t in ('BuyCard', 'LevelUp', 'RefreshShop', 'SellBench')}
    forms = [r['form'] for r in rows if r['form'] is not None]
    m['末轮成型度'] = forms[-1] if forms else float('nan')
    stag = best_s = 0
    for i in range(1, len(forms)):
        stag = stag + 1 if abs(forms[i] - forms[i - 1]) < STAGNANT_EPS else 0
        best_s = max(best_s, stag)
    m['停滞最长轮数'] = best_s
    for fac, need in (('仙舟', 3), ('持续伤害', 2), ('列车同行', 2)):
        m[f'{fac}{need}达成轮'] = next(
            (r['round'] for r in rows if r['factions'].get(fac, 0) >= need), None)
    m['首个2★轮'] = next(
        (r['round'] for r in rows if any(d.get('star', 0) >= 2 for d in r['deployed'])), None)
    m['上场人数曲线'] = [len(r['deployed']) for r in rows]
    levels = [r['level'] for r in rows if r['level'] is not None]
    m['等级曲线'] = levels
    m['等级爬升'] = (max(levels) - min(levels)) if levels else None
    m['等级末值'] = levels[-1] if levels else None
    # 装备覆盖:穿戴件数/(3×上场人数) 逐轮,末值+均值
    cov = [round(sum(len(d.get('equips') or []) for d in r['deployed'])
                 / max(3 * len(r['deployed']), 1), 2) for r in rows]
    m['装备覆盖末值'] = cov[-1] if cov else None
    m['装备覆盖均值'] = round(statistics.mean(cov), 2) if cov else None
    first_ok = next((i for i, r in enumerate(rows) if r['form_ok']), None)
    m['成型后退档轮数'] = sum(1 for r in rows[first_ok:] if not r['form_ok']) if first_ok is not None else 0
    # F 达标臂发射面(sim = 行内 launch 键;档案 = StartBattle 行动):
    # 成功率 sim 恒 1(发射核必然执行,建模声明见 engine_p1);
    # victim 缺失占比 = 发射时板满∧无合格腾位形态(G1 准入)的占比。
    launches = [r['launch'] for r in rows if r.get('launch')]
    m['发射次数'] = len(launches)
    m['发射成功率'] = (round(sum(1 for L in launches if L.get('ok')) / len(launches), 2)
                    if launches else None)
    m['发射victim缺失占比'] = (round(sum(1 for L in launches
                                     if (L.get('victim') or {}).get('victim_missing'))
                                 / len(launches), 2)
                           if launches else None)
    m['首发轮'] = next((r['round'] for r in rows if r.get('launch')), None)
    # H 采购面三观察(sim 行内 obs 键,engine_p1「采购面三观察计数」块建模;
    # 档案行 obs 恒空 → 0/None,不误报)。观察面只计数不定谳——
    # 「超容→买冻结 / 刷新零用 / 冷启动零买」三形态病灶判定归第 3 步复盘。
    _obs = [r.get('obs') or {} for r in rows]
    m['超容帧数'] = sum(int(o.get('overcap_frames') or 0) for o in _obs)
    _run = _best_run = 0
    for o in _obs:
        _run = _run + 1 if (o.get('overcap_frames') or 0) else 0
        _best_run = max(_best_run, _run)
    m['超容最长连续轮'] = _best_run
    m['超容峰值|B|'] = max((int(o.get('locked_b') or 0) for o in _obs),
                           default=0)
    _avail = sum(int(o.get('refresh_avail_frames') or 0) for o in _obs)
    _refs = sum(int(o.get('refreshes') or 0) for o in _obs)
    m['刷新可得帧'] = _avail
    m['刷新触发率'] = (round(_refs / _avail, 2) if _avail else None)
    _cold = [r for r in rows if r['plane'] == 1 and r['round'] <= 4]
    m['冷启动买次数'] = sum(n_act(r['acts'], 'BuyCard') for r in _cold)
    m['冷启动金花费'] = sum(act_cost(r['acts']) for r in _cold)
    # I 必花域观测三键(20 号稿 §6;sim 行内 obs 键,engine_p1 建模;
    # 档案行 obs 恒空 → 0/空,不误报)。观察面只计数不定谳——零消费帧
    # 判读看归因(物理残量白名单 §3.2 带分键)。
    m['必花域帧数'] = sum(int(o.get('must_spend_zone_frames') or 0)
                          for o in _obs)
    m['必花域零消费帧'] = sum(int(o.get('must_spend_zero_consume') or 0)
                              for o in _obs)
    _ms_layer: dict[str, int] = {}
    for o in _obs:
        for k, v in (o.get('must_spend_layer_hit') or {}).items():
            _ms_layer[k] = _ms_layer.get(k, 0) + int(v or 0)
    m['必花域层命中'] = _ms_layer
    # D 战斗过程
    lo, wo = [], []
    for r in rows:
        if r['node_type'] not in BATTLE_SKIP and r['form'] is not None:
            (lo if (r['hp_delta'] or 0) < 0 else wo).append(r['form'])
    m['最大连败'] = 0
    streak = 0
    for loss in losses:
        streak = streak + 1 if loss else 0
        m['最大连败'] = max(m['最大连败'], streak)
    m['败场形态中位'] = round(statistics.median(lo), 2) if lo else None
    m['胜场形态中位'] = round(statistics.median(wo), 2) if wo else None
    m['败场数'] = sum(losses)
    # F 供给利用(商店侧;补给选项相关率挂档案二期字段缺口)
    shops = []
    for r in rows:
        cards = [c for w in (r.get('shop_waves') or []) for c in (w or [])]
        shops.append((r['factions'], cards, r['acts']))
    m['_shops'] = shops
    m['终态'] = {'plane': rows[-1]['plane'], 'hp': rows[-1]['hp']} if rows else None
    return m


def supply_util(shops: list) -> float | None:
    """相关供给吃掉率:店内与板面阵营相关的牌中,被买入的占比(按轮聚合)。"""
    rel = bought = 0
    for facs, cards, acts in shops:
        bf = set(facs)
        rel_names = {c.get('name') for c in cards if c.get('faction') in bf}
        if rel_names:
            rel += 1
            buys = {a['card']['name'] for a in acts
                    if a.get('__type__') == 'BuyCard' and a.get('card')}
            if rel_names & buys:
                bought += 1
    return round(bought / rel, 2) if rel else None


WORST_METRICS = [  # (指标键, 方向):max=值大更差 / min=值小更差
    ('危局空转轮数', 'max'), ('空转轮占比', 'max'), ('停滞最长轮数', 'max'),
    ('花费率', 'min'), ('装备覆盖均值', 'min'), ('等级爬升', 'min'),
    ('超容最长连续轮', 'max'),
]


def report(rows_by_game: dict[str, dict], title: str) -> None:
    print(f'\n== 批统计面 | {title} | 局数 {len(rows_by_game)} ==')
    ms = {rid: analyze_game(g) for rid, g in rows_by_game.items()}

    def agg(key: str):
        vals = [m[key] for m in ms.values() if isinstance(m.get(key), (int, float))]
        return (round(statistics.median(vals), 2), pct(vals, 0.9)) if vals else None

    print('\n-- A/B 资源转化与行动配比(中位 | p90) --')
    for k in ('花费率', '空转轮占比', '危局空转轮数'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    print('  行动配比(中位):', {k: int(statistics.median([m['行动配比'][k] for m in ms.values()]))
                             for k in ('BuyCard', 'LevelUp', 'RefreshShop', 'SellBench')} if ms else {})
    print('\n-- C 阵容成型(含等级/装备) --')
    for k in ('末轮成型度', '停滞最长轮数', '首个2★轮', '等级末值', '等级爬升',
              '装备覆盖均值', '装备覆盖末值', '成型后退档轮数'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    for fac in ('仙舟3', '持续伤害2', '列车同行2'):
        key = f'{fac}达成轮'
        vals = [m[key] for m in ms.values() if m.get(key) is not None]
        print(f'  {key}: 达成率 {len(vals) / max(len(ms), 1):.0%}'
              f' | 中位轮 {int(statistics.median(vals)) if vals else None}')
    print('\n-- D 战斗过程 --')
    for k in ('败场数', '最大连败', '败场形态中位', '胜场形态中位'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    su = [supply_util(m.pop('_shops')) for m in ms.values()]
    su = [v for v in su if v is not None]
    print('\n-- E 供给利用 --')
    print(f'  相关供给吃掉率(中位 | p10 低尾): '
          f'{statistics.median(su):.2f} | {pct(su, 0.1):.2f}' if su else '  无数据')
    print('\n-- F 达标臂发射面(sim launch 键 / 档案 StartBattle;成功率 sim 恒真值面) --')
    for k in ('发射次数', '发射成功率', '发射victim缺失占比'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    fr = [m['首发轮'] for m in ms.values() if m.get('首发轮') is not None]
    print(f'  首发轮: 达成率 {len(fr) / max(len(ms), 1):.0%}'
          f' | 中位轮 {int(statistics.median(fr)) if fr else None}')
    print('\n-- G 终态 --')
    hps = [m['终态']['hp'] for m in ms.values() if m.get('终态') and m['终态']['hp'] is not None]
    print(f'  终局 hp 中位: {statistics.median(hps) if hps else None}')
    print('\n-- H 采购面三观察(sim obs 键;观察面只计数不定谳) --')
    for k in ('超容帧数', '超容最长连续轮', '刷新可得帧', '冷启动买次数', '冷启动金花费'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    rt = [m['刷新触发率'] for m in ms.values() if m.get('刷新触发率') is not None]
    if rt:
        print(f'  刷新触发率(实刷/可得帧,中位): {statistics.median(rt):.2f}')
    else:
        print('  刷新触发率: 无可得帧(全批零可得或非 sim 数据源)')
    over_games = [rid for rid, m in ms.items() if m.get('超容帧数')]
    print(f'  超容局占比: {len(over_games) / max(len(ms), 1):.0%}')
    cold0 = [rid for rid, m in ms.items()
             if m.get('冷启动买次数') == 0 and m.get('冷启动金花费') is not None]
    print(f'  冷启动零买局占比: {len(cold0) / max(len(ms), 1):.0%}')
    print('\n-- I 必花域观测三键(20 号稿 §6;零消费帧判读看归因) --')
    for k in ('必花域帧数', '必花域零消费帧'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    _ms_tot: dict[str, int] = {}
    for m in ms.values():
        for k, v in (m.get('必花域层命中') or {}).items():
            _ms_tot[k] = _ms_tot.get(k, 0) + v
    print(f'  层命中(L1/L2/L3): {_ms_tot or "无数据"}')
    _zg = [rid for rid, m in ms.items() if m.get('必花域帧数')]
    print(f'  必花域帧出现局占比: {len(_zg) / max(len(ms), 1):.0%}')
    print('\n-- 表现不好的指标 → 体现最重的局(每指标 2 局;第 3 步挑局复盘的抽样单) --')
    for key, d in WORST_METRICS:
        vals = [(m.get(key), rid) for rid, m in ms.items()
                if isinstance(m.get(key), (int, float))]
        if not vals:
            continue
        vals.sort(key=lambda t: t[0], reverse=(d == 'max'))
        word = '高' if d == 'max' else '低'
        print(f'  {key}({word}为差): '
              + '; '.join(f'{rid.split("_s")[-1]}={v}' for v, rid in vals[:2]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--sim-batch', default='', help='sim 批次名或 latest')
    ap.add_argument('--recent', type=int, default=0, help='生产档案最近 N 局')
    ap.add_argument('--match', default='', help='生产档案单局 game_id')
    args = ap.parse_args()
    if args.sim_batch:
        name = args.sim_batch
        batch = (sorted(d for d in SIM_ROOT.iterdir() if d.is_dir())[-1]
                 if name == 'latest' else SIM_ROOT / name)
        if not batch.is_dir():
            raise SystemExit(f'批次不存在:{batch}')
        report(_sim_rows(batch), batch.name)
    elif args.match:
        g = _archive_rows(args.match)
        report({g['game_id']: g['rows']}, g['game_id'])
    elif args.recent:
        idx = _load(MATCHES / 'index.jsonl')[-args.recent:]
        groups: dict[str, dict] = {}
        affix_stat: dict[tuple, list] = {}
        for e in idx:
            p = MATCHES / f"match_{e['game_id']}.json"
            if not p.exists():
                continue
            g = _archive_rows(e['game_id'])
            groups[g['game_id']] = g['rows']
            affix_stat.setdefault(tuple(g['affixes']), {'hps': []})['hps'].append(
                g['final_hp'] if g['final_hp'] is not None else 0)
        report(groups, f'生产档案最近 {len(groups)} 局')
        print('\n-- 词缀条件化分组(sim 未建模词条,仅档案;样本小只列不判) --')
        for af, st in sorted(affix_stat.items(), key=lambda kv: -len(kv[1]['hps'])):
            hps = st['hps']
            print(f'  {len(hps)} 局 | 终局hp中位 {statistics.median(hps):.0f} | {"/".join(af) or "(无词缀记录)"}')
    else:
        ap.error('需 --sim-batch / --recent / --match 之一')


if __name__ == '__main__':
    main()
