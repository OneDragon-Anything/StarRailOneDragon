"""T-165 泄金阶梯 A/B 判读脚本(判前预注册执行面;设计方案 §4)。

判据单一源 = ``.debug/temp/currency_war/attacks/t165_p2_conversion/
设计方案.md`` §4.2(A-H 判据与线)/§4.1(批结构与 seed 纪律)。本脚本
只执行预注册口径,不新增/不改指标定义与线;跑批后禁改。

批结构(§4.1):改前基线批 → 改后处理批;``--n 200 --pool snapshot``
同池指纹(跨日必核,指纹不等拒读);**双批 seed 段不相交**(实现批定,
登记即锁——本脚本启动即校验不相交并输出两段登记块)。

T-169 污染声明(任务书口径):涉引擎周期/成型率指标在 T-169 修复前
不测。本脚本 ``--mode unpolluted``(缺省)只判「泄金次数/金轨迹类」
不受污染判据(A/G + 臂发射计数归因键),B/E/C 只打印 defer 行;
``--mode full``(候 T-169 修复后)恢复 B 判读。D/H 恒只报不设线,
F 挂 T-168 域恒只报。

判据与线(§4.2 摘录;基线池指纹 0e091d4d 批):
- A:P2 CwActionRefreshShopParam:CwActionBuyCardParam 比,基线 ≈4.9:1 → 线 ≤3.5:1(方向线非
  拍定判据;采纳判据仍=数学结构+方向票一致+无回归)。
- B:终局阵容完成率 4/100 → ≥8/100(弱证据+功效注,mode=full 才判)。
- D:位面末出口金 ≥50 占比(只报;~1.3x 膨胀读数禁当达标证据)。
- G:ALL IN 窗 ∧ P21 域(hp ≤ 停升级线,kernel p1/p2_levelup_stop_hp
  单一源现查)帧非支A XP 支出局数 = 0(判据级 0 容忍);支A 判读 =
  CwActionLevelUpParam 动作行 dec_board_full/dec_bench_2star 披露键(T-135 决策帧
  真值),缺披露键的击单独计数不进 0 容忍(防旧账本假红)。
- H:P1 R5+ 刷新:买比 + 位面末息基(只报)。
- 归因四支判读键(§4.2):档 1/档 2/dominance 摘旗后发射计数按
  CwActionBuyCardParam.reason 分臂输出——处理臂三键全 0 = 实现 bug 信号(归因①)。

用法(项目根):
    uv run python tools/cw/ab_t165_leak_ladder.py \
        --new <处理批目录> --base <基线批目录> [--mode unpolluted] \
        [--out result.json]

自测(合成样本,已知答案验证口径与判定分支):
    uv run python tools/cw/ab_t165_leak_ladder.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))

# ---------------- 预注册常量(设计方案 §4.2;跑批后禁改) ----------------

#: A 线:P2 CwActionRefreshShopParam:CwActionBuyCardParam 比 ≤3.5(方向线;基线 ≈4.9:1)。
LINE_A_P2_REFRESH_BUY_RATIO: float = 3.5
#: B 线:终局阵容完成率 ≥8/100(弱证据;仅 mode=full 判,T-169 前 defer)。
LINE_B_FORM_OK_RATE: float = 0.08
#: G 线:P21 域内非支A XP 支出局数 = 0(判据级,0 容忍)。
LINE_G_NON_SUPPORT_XP_GAMES: int = 0
#: 归因①判读键:处理臂新发射面(reason 词表;全 0 = 实现 bug 信号)。
TREATMENT_ARM_REASONS: tuple[str, ...] = (
    'press_buy_deployable', 'm6_stockpile', 'dominance_buy')

DEFER_ROWS: tuple[str, ...] = (
    'B(成型率;T-169 修复前不测,--mode full 恢复)',
    'C(hp≤25 揣金≥50;改挂 P2 域候授权批)',
    'E(血线硬地板激活率;挂 hp 闸批,总图实施序第 5 步)',
    'F(P1 R5+ 零卖出∧出口 b_t≤4;T-168 域,只观测不设线)',
)


# ---------------- 数据装配(与 tools/cw/ab_judge.py 同一账本契约) ----------------


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f'缺账本文件:{path}')
    return [json.loads(line) for line in
            open(path, encoding='utf-8') if line.strip()]


def _seed_of(run_id: str) -> int:
    """run_id 约定 = 批目录名 + ``_s<seed>``(runner.write_batch_ledger)。"""
    idx = run_id.rfind('_s')
    if idx < 0 or not run_id[idx + 2:].lstrip('-').isdigit():
        raise SystemExit(f'run_id 无 _s<seed> 后缀,无法解析 seed:{run_id}')
    return int(run_id[idx + 2:])


def load_batch(batch_dir: Path) -> dict[int, list[dict]]:
    """读批次目录 → {seed: 局决策行列表}(按位面/轮排序)。"""
    games: dict[str, list[dict]] = {}
    for row in _load_jsonl(batch_dir / 'decisions.jsonl'):
        games.setdefault(row.get('run_id') or '?', []).append(row)
    by_seed: dict[int, list[dict]] = {}
    for rid, rows in games.items():
        rows.sort(key=lambda r: ((r.get('plane') or 0),
                                 (r.get('round_num') or 0)))
        seed = _seed_of(rid)
        if seed in by_seed:
            raise SystemExit(f'同批出现重复 seed:{rid}')
        by_seed[seed] = rows
    return by_seed


# ---------------- 单局指标 ----------------


def game_metrics(rows: list[dict], *, stop_hp_of_plane) -> dict:
    """单局泄金/金轨迹类指标(§4.2 A/D/G/H 口径;零 hp 判定面污染)。

    ``stop_hp_of_plane`` = 位面 → 停升级线读数(调用侧用 kernel
    p1/p2_levelup_stop_hp 现查注入;本函数不自查 registry,保纯函数)。
    """
    m: dict = {
        'p2_refresh': 0, 'p2_buycard': 0,
        'p1_r5_refresh': 0, 'p1_r5_buycard': 0,
        'plane_end_gold_ok': 0, 'plane_end_gold_n': 0,
        'g_non_support_xp': 0, 'g_support_xp': 0, 'g_unknown_xp': 0,
        'g_violation_hps': [],
        'arm_reason_counts': {},
    }
    plane_last_gold: dict[int, tuple[int, float]] = {}
    # 决策帧 hp 口径(sim/checks/segments.py _blood_budget_levelup_events
    # 同款):账本行 hp = 本轮回后结算值,决策发生在本轮回战斗之前 ⇒
    # 决策帧 hp = 上一行 hp(逐行滚动;局首帧无上一行 = 开局满血恒不
    # 触线,跳过);跨位面连续(P2 首帧决策 hp = P1 末行 hp,与生产
    # 进场继承同真值)。
    prev_hp: int | None = None
    for r in rows:
        plane = r.get('plane') or 0
        rnd = r.get('round_num') or 0
        acts = r.get('actions') or []
        hp_decision = prev_hp
        if r.get('hp') is not None:
            prev_hp = int(r['hp'])
        if plane == 2:
            for a in acts:
                t = a.get('__type__')
                if t == 'CwActionRefreshShopParam':
                    m['p2_refresh'] += 1
                elif t == 'CwActionBuyCardParam':
                    m['p2_buycard'] += 1
        if plane == 1 and rnd >= 5:
            for a in acts:
                t = a.get('__type__')
                if t == 'CwActionRefreshShopParam':
                    m['p1_r5_refresh'] += 1
                elif t == 'CwActionBuyCardParam':
                    m['p1_r5_buycard'] += 1
        # 位面末金(每行 last-wins;行序已按轮排序)
        g = r.get('gold')
        if g is not None:
            cur = plane_last_gold.get(plane)
            if cur is None or rnd >= cur[0]:
                plane_last_gold[plane] = (rnd, float(g))
        # G:ALL IN 窗(node=boss ∧ 轮=位面末,镜像 check_levelup_budget_gate
        # 的 is_allin 口径)∧ P21 域(hp ≤ 停升级线,决策帧口径见上)帧的
        # XP 类支出
        node = (r.get('sim') or {}).get('node') or ''
        stop_hp = stop_hp_of_plane(plane)
        if (node in ('boss', '首领')
                and r.get('round_num') == max(
                    (x.get('round_num') or 0) for x in rows
                    if (x.get('plane') or 0) == plane)
                and hp_decision is not None
                and stop_hp is not None
                and hp_decision <= stop_hp):
            for a in acts:
                if a.get('__type__') not in ('CwActionLevelUpParam', 'CwActionLevelUpShopParam'):
                    continue
                full, two = a.get('dec_board_full'), a.get('dec_bench_2star')
                if isinstance(full, bool) and isinstance(two, bool):
                    if full and two:
                        m['g_support_xp'] += 1
                    else:
                        m['g_non_support_xp'] += 1
                        m['g_violation_hps'].append(hp_decision)
                else:
                    m['g_unknown_xp'] += 1   # 缺披露键:不进 0 容忍(防假红)
        for a in acts:
            if a.get('__type__') == 'CwActionBuyCardParam':
                reason = a.get('reason') or ''
                m['arm_reason_counts'][reason] = \
                    m['arm_reason_counts'].get(reason, 0) + 1
    for _rnd, g in plane_last_gold.values():
        m['plane_end_gold_n'] += 1
        if g >= 50:
            m['plane_end_gold_ok'] += 1
    return m


def aggregate(games: dict[int, list[dict]], *, stop_hp_of_plane) -> dict:
    """批级聚合(A/D/G/H + 臂发射计数;§4.2 口径)。"""
    per = {s: game_metrics(rows, stop_hp_of_plane=stop_hp_of_plane)
           for s, rows in games.items()}
    n = max(len(per), 1)
    p2r = sum(g['p2_refresh'] for g in per.values())
    p2b = sum(g['p2_buycard'] for g in per.values())
    arm_counts: dict[str, int] = {}
    for g in per.values():
        for k, v in g['arm_reason_counts'].items():
            arm_counts[k] = arm_counts.get(k, 0) + v
    g_hps = [hp for g in per.values() for hp in g['g_violation_hps']]
    return {
        'n_games': len(per),
        'A_p2_refresh_buycard_ratio': (p2r / p2b) if p2b else float('inf'),
        'A_p2_refresh': p2r, 'A_p2_buycard': p2b,
        'D_plane_end_gold_ge50_rate': sum(g['plane_end_gold_ok']
                                          for g in per.values()) / n,
        'G_games_non_support_xp': sum(1 for g in per.values()
                                      if g['g_non_support_xp'] > 0),
        'G_non_support_xp_actions': sum(g['g_non_support_xp']
                                        for g in per.values()),
        'G_support_xp_actions': sum(g['g_support_xp']
                                    for g in per.values()),
        'G_unknown_disclosure_actions': sum(g['g_unknown_xp']
                                            for g in per.values()),
        'G_violation_hp_readings': g_hps,
        'H_p1_r5_refresh': sum(g['p1_r5_refresh'] for g in per.values()),
        'H_p1_r5_buycard': sum(g['p1_r5_buycard'] for g in per.values()),
        'arm_reason_counts': dict(sorted(arm_counts.items())),
        'form_ok_games': None,   # B:成型率账本字段判读归 mode=full,不在此算
    }


# ---------------- 判读 ----------------


def judge(new_dir: Path, base_dir: Path, *, mode: str = 'unpolluted') -> dict:
    """预注册判读:seed 不相交校验 + 指纹同池校验 + A/G 判定 + D/H 读数。"""
    new_fp = json.loads((new_dir / 'manifest.json').read_text(
        encoding='utf-8')).get('pool_fingerprint', '') \
        if (new_dir / 'manifest.json').exists() else ''
    base_fp = json.loads((base_dir / 'manifest.json').read_text(
        encoding='utf-8')).get('pool_fingerprint', '') \
        if (base_dir / 'manifest.json').exists() else ''
    if not new_fp or new_fp != base_fp:
        raise SystemExit(f'pool_fingerprint 不一致或缺失,拒绝判读(§4.1 同池'
                         f'指纹跨日必核):新={new_fp!r} 基线={base_fp!r}')

    # 停升级线读数(kernel 单一源现查;消费既有 hp 读数,零新增消费点)
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        p1_levelup_stop_hp,
        p2_levelup_stop_hp,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    stop_hp_of_plane = {1: p1_levelup_stop_hp(DEFAULT_REGISTRY),
                        2: p2_levelup_stop_hp(DEFAULT_REGISTRY)}

    new_games = load_batch(new_dir)
    base_games = load_batch(base_dir)
    seeds_new, seeds_base = set(new_games), set(base_games)
    # §4.1:双批 seed 段不相交(登记即锁;相交 = 批结构违例拒读)。
    if seeds_new & seeds_base:
        raise SystemExit(f'双批 seed 段相交,违 §4.1 预注册批结构:'
                         f'{sorted(seeds_new & seeds_base)[:10]} ...')
    new_m = aggregate(new_games, stop_hp_of_plane=stop_hp_of_plane.get)
    base_m = aggregate(base_games, stop_hp_of_plane=stop_hp_of_plane.get)

    a_ok = new_m['A_p2_refresh_buycard_ratio'] <= LINE_A_P2_REFRESH_BUY_RATIO
    g_ok = new_m['G_games_non_support_xp'] <= LINE_G_NON_SUPPORT_XP_GAMES
    arm_fired = {r: new_m['arm_reason_counts'].get(r, 0)
                 for r in TREATMENT_ARM_REASONS}
    arm_all_zero = all(v == 0 for v in arm_fired.values())
    checks = {
        'A_p2_refresh_buycard': {
            'value': new_m['A_p2_refresh_buycard_ratio'],
            'line': LINE_A_P2_REFRESH_BUY_RATIO, 'verdict':
                'PASS' if a_ok else 'FAIL',
            'note': '方向线非拍定判据;采纳判据=数学结构+方向票一致+无回归'},
        'G_p21_domain_non_support_xp': {
            'value': new_m['G_games_non_support_xp'],
            'line': LINE_G_NON_SUPPORT_XP_GAMES,
            'verdict': 'PASS' if g_ok else 'FAIL',
            'note': '判据级 0 容忍;violating 帧 hp 读数按带记录'
                    f"(hp={new_m['G_violation_hp_readings'][:20]})"},
    }
    if mode == 'full':
        # B 判读(候 T-169 修复后启用;账本 form_ok 字段)
        form_ok_new = _form_ok_rate(new_games)
        checks['B_form_ok_rate'] = {
            'value': form_ok_new, 'line': LINE_B_FORM_OK_RATE,
            'verdict': 'PASS' if form_ok_new >= LINE_B_FORM_OK_RATE
            else 'FAIL',
            'note': '弱证据+功效注(§4.2):禁单独作采纳依据'}
    defer = list(DEFER_ROWS)
    if mode == 'unpolluted':
        defer.insert(0, '本判读 = unpolluted 模式(候 T-169);B/E/C/F 未判')
    verdict = ('PASS' if all(c['verdict'] == 'PASS' for c in checks.values())
               and not (arm_all_zero and mode == 'full') else 'FAIL')
    return {
        'prereg': '设计方案.md §4(t165_p2_conversion;泄金阶梯+ALL IN 类别'
                  '过滤单处理批)',
        'mode': mode,
        'pool_fingerprint': new_fp,
        'seed_segments': {
            'treatment': sorted(seeds_new),
            'baseline': sorted(seeds_base),
            'disjoint': True,
        },
        'stop_hp_lines': {'P1': stop_hp_of_plane[1], 'P2': stop_hp_of_plane[2]},
        'checks': checks,
        'treatment': new_m,
        'baseline': base_m,
        'arm_emission_attribution': {
            'counts': arm_fired,
            'all_zero_note': ('处理臂三键全 0 = 实现 bug 信号(§4.2 归因①)'
                              if arm_all_zero else ''),
        },
        'deferred': defer,
        'verdict': verdict,
    }


def _form_ok_rate(games: dict[int, list[dict]]) -> float:
    """B 取数:任一决策行 form_ok=true 的局占比(M3 口径)。"""
    if not games:
        return float('nan')
    hit = sum(1 for rows in games.values()
              if any(r.get('form_ok') is True for r in rows))
    return hit / len(games)


def render_human(res: dict) -> str:
    lines = ['== T-165 泄金阶梯 A/B 判读(判据 = 设计方案 §4 预注册)==',
             f"mode={res['mode']} | 指纹 {res['pool_fingerprint'][:8]}"
             f" | 处理批 {res['treatment']['n_games']} 局"
             f" / 基线批 {res['baseline']['n_games']} 局"
             f" | 总判 **{res['verdict']}**"]
    seg = res['seed_segments']
    lines.append(f"seed 段登记(不相交已锁):处理 {seg['treatment'][:5]}..."
                 f" / 基线 {seg['baseline'][:5]}...")
    lines.append(f"停升级线读数(kernel 单一源):P1≤{res['stop_hp_lines']['P1']}"
                 f" / P2≤{res['stop_hp_lines']['P2']}")
    for k, c in res['checks'].items():
        lines.append(f"  {k}: value={c['value']} line={c['line']}"
                     f" → {c['verdict']}({c['note']})")
    lines.append(f"  臂发射归因(处理批):{res['treatment']['arm_reason_counts']}")
    lines.append(f"  {res['arm_emission_attribution']['all_zero_note']}")
    lines.append('  只报不设线:D 处理 '
                 f"{res['treatment']['D_plane_end_gold_ge50_rate']:.3f}"
                 f" / 基线 {res['baseline']['D_plane_end_gold_ge50_rate']:.3f}"
                 f";H(P1 R5+)刷 {res['treatment']['H_p1_r5_refresh']}"
                 f":买 {res['treatment']['H_p1_r5_buycard']}")
    lines.append('  defer:' + ' | '.join(res['deferred']))
    return '\n'.join(lines)


# ---------------- 自测(合成样本;已知答案验证口径) ----------------


def _write_row(batch: Path, rid: str, plane: int, rnd: int, *, gold: int,
               hp: int | None, acts: list[dict], node: str = '',
               form_ok: bool | None = None) -> None:
    row = {'run_id': rid, 'plane': plane, 'round_num': rnd,
           'gold': gold, 'actions': acts, 'sim': {'node': node}}
    if hp is not None:
        row['hp'] = hp
    if form_ok is not None:
        row['form_ok'] = form_ok
    (batch / 'decisions.jsonl').open('a', encoding='utf-8').write(
        json.dumps(row, ensure_ascii=False) + '\n')


def _buy(reason: str, cost: int = 1) -> dict:
    return {'__type__': 'CwActionBuyCardParam', 'reason': reason,
            'card': {'name': reason, 'cost': cost}}


def _make_batch(batch: Path, *, seeds: range, p2_ratio_rows: bool,
                g_violation: bool, arms: bool) -> None:
    batch.mkdir(parents=True)
    (batch / 'manifest.json').write_text(
        json.dumps({'pool_fingerprint': 'a' * 32}), encoding='utf-8')
    for s in seeds:
        rid = f'{batch.name}_s{s}'
        # P2 行:处置臂买多刷少(A 达标),基线形刷多买少(A 超)
        n_refresh, n_buy = ((1, 5) if p2_ratio_rows else (5, 1))
        acts = ([{'__type__': 'CwActionRefreshShopParam', 'cost': 2}] * n_refresh
                + [_buy('m6_stockpile' if arms else 'm2_line_member')] * n_buy)
        # P2 首行(hp=10:作为 boss 行的「上一行」供决策帧 hp 滚动取数)
        _write_row(batch, rid, 2, 2, gold=60, hp=10, acts=acts)
        # P1 R5+ 读数行
        _write_row(batch, rid, 1, 6, gold=40, hp=40, acts=[_buy('ev_buy')])
        # 位面末金行(D)
        _write_row(batch, rid, 1, 9, gold=55 if not g_violation else 10,
                   hp=55, acts=[])
        # G 行:ALL IN boss 末轮,决策帧 hp = 上一行结算 10(≤P2 线 21)
        # 含非支A CwActionLevelUpParam
        g_act = [{'__type__': 'CwActionLevelUpParam', 'cost': 4,
                  'dec_board_full': False, 'dec_bench_2star': False}]
        _write_row(batch, rid, 2, 7, gold=20, hp=10, node='boss',
                   acts=g_act if g_violation else [])


def self_test() -> list[str]:
    failures: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix='ab_t165_selftest_'))
    new, base = tmp / 'treat', tmp / 'base'
    _make_batch(new, seeds=range(100, 105), p2_ratio_rows=True,
                g_violation=False, arms=True)
    _make_batch(base, seeds=range(200, 205), p2_ratio_rows=False,
                g_violation=False, arms=False)
    res = judge(new, base, mode='unpolluted')
    if res['verdict'] != 'PASS':
        failures.append(f'自测 S-A 总判应 PASS,得 {res["verdict"]}')
    if res['treatment']['A_p2_refresh_buycard_ratio'] != 0.2:
        failures.append('S-A 处理臂 A 比值应为 1/5')
    if res['checks']['G_p21_domain_non_support_xp']['value'] != 0:
        failures.append('S-A G 应为 0')
    if res['arm_emission_attribution']['counts'].get('m6_stockpile') != 25:
        failures.append('S-A m6_stockpile 臂计数应 25(5 局 × 5 买)')
    # S-B:G 违例 + A 超线 → FAIL
    bad = tmp / 'bad'
    _make_batch(bad, seeds=range(300, 303), p2_ratio_rows=False,
                g_violation=True, arms=True)
    res2 = judge(bad, base, mode='unpolluted')
    if res2['verdict'] != 'FAIL':
        failures.append(f'S-B 总判应 FAIL,得 {res2["verdict"]}')
    if res2['treatment']['G_violation_hp_readings'] != [10, 10, 10]:
        failures.append('S-B 违例帧 hp 读数应 [10,10,10]')
    # S-C:seed 相交拒读(§4.1 批结构违例)
    try:
        judge(new, new, mode='unpolluted')
        failures.append('S-C seed 相交应 SystemExit')
    except SystemExit:
        pass
    return failures


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--new', help='处理批目录')
    ap.add_argument('--base', help='基线批目录')
    ap.add_argument('--mode', choices=('unpolluted', 'full'),
                    default='unpolluted',
                    help='unpolluted=T-169 修复前(B 不判);full=恢复 B 判读')
    ap.add_argument('--out', help='结果 JSON 落盘路径(可选)')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        failures = self_test()
        if failures:
            print('SELF-TEST FAIL:')
            for f in failures:
                print(' -', f)
            sys.exit(1)
        print('SELF-TEST PASS(合成样本已知答案全对)')
        return
    if not args.new or not args.base:
        ap.error('--new 与 --base 必填(或 --self-test)')
    res = judge(Path(args.new), Path(args.base), mode=args.mode)
    print(render_human(res))
    if args.out:
        Path(args.out).write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
