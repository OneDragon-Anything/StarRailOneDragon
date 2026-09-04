"""P15v2 条件败局伤害重证:实机对局档案拟合脚本(语料冻结入库件)。

背景:原 P15 的 11.32−0.37·rung 拟合语料(w324_coarse_battle/)已被清理删除,
2026-09-01 裁定「语料已灭=证明不成立」。本脚本从**实机对局档案**
(`.debug/temp/currency_war/replay/matches/match_g_*.json`,结算屏遥测真值,
非 sim 账本)独立重建条件败局伤害 E[|Δhp| | 败, 桶, 节点类型] 的估计,
并把抽取语料冻结到本目录(corpus_battle_loss.jsonl)——**语料随证明入库,
防再次「语料灭=证明不成立」**。

估计口径(P15 口径命题继承):只取 killed=False 的战斗类节点
(battle/encounter/boss;奖励/补给零战力不入)。删失策略:w193 先例,
败局 hp_after≤1 为死亡/败北地板删失(观测 |Δhp|=hp_before 只下界真值),
主估计弃删失样本,同时报「删失按观测值计入」的下界估计——两者同向
向下偏,真值 ≥ 上带。

CI:按局(game)聚类 bootstrap(2000 次重抽),BCA 略(聚类 bootstrap
百分位即够;决策按区间端点稳健性判)。

复跑(双模式):`uv run python tools/cw/proofs/p15/p15v2_fit.py` = **只读自检**
(对入库 corpus 重算并与 fit_results.json 对账,零写入);
`--refreeze` = 显式重冻(裁定过的新冻结才用,重冻后须 commit+回填重证件+同步消费文本)。
"""
from __future__ import annotations

import glob
import hashlib
import json
import random
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from sr_od.application.currency_war.knowledge.cw_engine_facts import (
    engines_count,
)

REPO = Path(__file__).resolve().parents[4]
MATCH_GLOB = REPO / '.debug' / 'temp' / 'currency_war' / 'replay' / 'matches'
OUT_DIR = Path(__file__).resolve().parent

#: 节点类型归一(档案混用中文(结算屏 OCR)与英文(回退))
NODE_NORM = {
    '普通战斗': 'battle', 'battle': 'battle', '战斗': 'battle',
    '遭遇': 'encounter', 'encounter': 'encounter',
    'boss': 'boss', 'Boss': 'boss', '首领': 'boss',
}
BATTLE_CLASS = ('battle', 'encounter', 'boss')
NON_COMBAT = ('奖励', '补给', 'reward', 'supply')

N_BOOT = 2000
SEED = 20260908


def rung_of(outcome: dict, deployed_ids: list[str]) -> int:
    """成型档 = engines_count(board_before, 上场名单)(_settle_rung 同源式)。"""
    bf = outcome.get('board_before') or {}
    names = frozenset(i for i in deployed_ids if i)
    return engines_count(dict(bf), names)


def extract() -> tuple[list[dict], list[dict]]:
    """抽语料:战斗类节点逐行(胜/败都留,供口径对照)+ 局级 provenance。"""
    rows: list[dict] = []
    games: list[dict] = []
    for f in sorted(glob.glob(str(MATCH_GLOB / 'match_g_*.json'))):
        m = json.loads(Path(f).read_text(encoding='utf-8'))
        gid = m.get('game_id') or Path(f).stem
        games.append({
            'game_id': gid,
            'strategy_version': m.get('strategy_version'),
            'n_rounds': len(m.get('rounds') or []),
        })
        for r in m.get('rounds') or []:
            o = r.get('outcome') or {}
            nt = NODE_NORM.get(r.get('node_type') or '')
            if nt is None:
                raw = r.get('node_type') or ''
                if raw in NON_COMBAT:
                    continue
                continue  # 未知类型不入语料(计数见 fit_results.unknown_types)
            killed = o.get('killed')
            if killed is None:
                continue
            delta = r.get('hp_delta')
            hp_after = o.get('hp_after')
            if not isinstance(delta, (int, float)) \
                    or not isinstance(hp_after, (int, float)):
                continue
            dep = [d.get('char_id', '') for d in (r.get('deployed') or [])
                   if isinstance(d, dict)]
            rows.append({
                'game_id': gid,
                'plane': r.get('plane'),
                'round': r.get('round'),
                'node_type': nt,
                'rung': rung_of(o, dep),
                'killed': bool(killed),
                'hp_before': hp_after - delta,
                'hp_after': hp_after,
                'delta': delta,
                'censored': bool(killed is False and hp_after <= 1),
            })
    return rows, games


def boot_ci(vals_by_game: dict[str, list[float]], seed: int) -> list[float]:
    """按局聚类 bootstrap 的 95% CI(局内全取,局重抽)。"""
    gids = sorted(vals_by_game)
    if len(gids) < 2:
        return []
    rng = random.Random(seed)
    means = []
    for _ in range(N_BOOT):
        sample = [vals_by_game[rng.choice(gids)] for _ in gids]
        flat = [v for s in sample for v in s]
        means.append(sum(flat) / len(flat))
    means.sort()
    return [round(means[int(0.025 * len(means))], 2),
            round(means[int(0.975 * len(means)) - 1], 2)]


def cell_stats(rows: list[dict], key_fn) -> dict:
    """逐格:n / 均值 / 聚类 CI(两口径:弃删失=主,删失按观测计=下界)。"""
    main: dict[tuple, dict[str, list[float]]] = defaultdict(dict)
    lower: dict[tuple, dict[str, list[float]]] = defaultdict(dict)
    cens: dict[tuple, int] = defaultdict(int)
    n_all: dict[tuple, int] = defaultdict(int)
    for r in rows:
        k = key_fn(r)
        n_all[k] += 1
        if r['censored']:
            cens[k] += 1
        else:
            main[k].setdefault(r['game_id'], []).append(abs(r['delta']))
        lower[k].setdefault(r['game_id'], []).append(abs(r['delta']))
    out = {}
    for k in sorted(n_all, key=lambda x: str(x)):
        mv = [v for g in main.get(k, {}) for v in main[k][g]]
        lv = [v for g in lower[k] for v in lower[k][g]]
        out[str(k)] = {
            'n': n_all[k],
            'n_censored': cens[k],
            'mean_uncensored': round(sum(mv) / len(mv), 2) if mv else None,
            'ci95_uncensored': boot_ci(main[k], SEED) if mv else [],
            'mean_all_observed': round(sum(lv) / len(lv), 2) if lv else None,
            'ci95_all_observed': boot_ci(lower[k], SEED) if lv else [],
        }
    return out


def main() -> None:
    """双模式(2026-09-04 重设计纪律改造,出处=P15v2_REPROOF §6 检验点):

    - 默认 = **只读自检**:对已入库 corpus 重算统计,与 fit_results.json
      逐位对账(含 corpus sha);零写入——「冻结语料」从此真的冻结,
      自检不再隐式重冻(病根:原 main() 每次运行都从活档案重抽取并回写,
      语料随新对局静默漂移,重证件数值与 artifact 脱钩即此病)。
    - ``--refreeze`` = 显式重冻:原重抽取+回写逻辑,仅在**裁定过的新冻结**
      时使用(重冻后必须:commit 语料与 artifact + 回填重证件主表数值与
      corpus_sha256 + 同步全部消费文本,缺一步=复现链断)。
    """
    import sys
    if '--refreeze' in sys.argv:
        refreeze()
        return
    sys.exit(verify())


def load_corpus() -> list[dict]:
    corpus = OUT_DIR / 'corpus_battle_loss.jsonl'
    return [json.loads(line)
            for line in corpus.read_text(encoding='utf-8').splitlines()
            if line]


#: 三桶族 key_fn 的单一源(verify/refreeze 共用;两路各持一份逐字
#: lambda 时,改其一不改其二 = 自检静默漂移)。
STATS_FAMILIES: dict[str, object] = {
    # 桶族1:位面×节点类型(边际,P51 消费的最低形态)
    'by_plane_node': lambda r: (r['plane'], r['node_type']),
    # 桶族2:位面×节点×轮次(P1 战斗轮次细桶)
    'by_plane_node_round': lambda r: (
        (r['plane'], r['node_type'], r['round'])
        if r['plane'] == 1 and r['node_type'] == 'battle'
        else (r['plane'], r['node_type'],
              'early' if (r['round'] or 0) <= 3 else 'late')),
    # 桶族3:位面×节点×成型档(替代原 11.32−0.37·rung 的桶维)
    'by_plane_node_rung': lambda r: (r['plane'], r['node_type'], r['rung']),
}


def compute_stats(rows: list[dict]) -> dict:
    losses = [r for r in rows if not r['killed']]
    out = {
        'n_battle_class_rows': len(rows),
        'n_loss_rows': len(losses),
        'n_loss_censored': sum(1 for r in losses if r['censored']),
    }
    for name, key_fn in STATS_FAMILIES.items():
        out[name] = cell_stats(losses, key_fn)
    return out


def verify() -> int:
    """只读自检:corpus 重算 vs fit_results.json 对账,零写入。"""
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    corpus_path = OUT_DIR / 'corpus_battle_loss.jsonl'
    res = json.loads((OUT_DIR / 'fit_results.json').read_text(
        encoding='utf-8'))
    sha = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    rows = load_corpus()
    problems: list[str] = []
    if sha != res.get('corpus_sha256'):
        problems.append(
            f'corpus sha 不匹配: 现文件 {sha[:8]} vs 登记 '
            f'{str(res.get("corpus_sha256"))[:8]}(语料被改或 artifact 过期)')
    stats = compute_stats(rows)
    for k in ('n_battle_class_rows', 'n_loss_rows', 'n_loss_censored'):
        if stats[k] != res.get(k):
            problems.append(f'{k}: 重算 {stats[k]} vs 登记 {res.get(k)}')
    # 局集交叉对账(sha 只锁 corpus 本身;corpus 被换入同规模
    # 异局语料且 artifact 同步篡改时,原有对账面不设防——补局集核对)
    prov = res.get('games_provenance') or []
    prov_ids = {g.get('game_id') for g in prov}
    corpus_ids = {r['game_id'] for r in rows}
    if len(prov) != res.get('n_games'):
        problems.append(f"n_games: 登记 {res.get('n_games')} vs "
                        f'provenance 条数 {len(prov)}')
    if corpus_ids - prov_ids:
        problems.append(f'corpus 含 provenance 未登记的局: '
                        f'{sorted(corpus_ids - prov_ids)[:5]}')
    if prov_ids - corpus_ids:
        # 零战斗行局合法(provenance 登记全部扫过局,corpus 只收战斗类行)
        print(f'注: provenance 含 {len(prov_ids - corpus_ids)} 个 '
              f'corpus 零行局(合法=该局无战斗类节点): '
              f'{sorted(prov_ids - corpus_ids)[:5]}')
    for fam in STATS_FAMILIES:
        a, b = stats[fam], res.get(fam) or {}
        for key in sorted(set(a) | set(b)):
            if a.get(key) != b.get(key):
                problems.append(f'{fam}[{key}]: 重算 {a.get(key)} '
                                f'vs 登记 {b.get(key)}')
    if problems:
        print(f'自检 FAIL({len(problems)} 项):')
        for p in problems:
            print(' -', p)
        return 1
    print(f"自检 PASS: corpus sha={sha[:8]} rows={stats['n_battle_class_rows']} "
          f"losses={stats['n_loss_rows']} cens={stats['n_loss_censored']}; "
          '三桶族逐位复现;主表(弃删失主口径/括注下界口径):')
    for k, v in stats['by_plane_node'].items():
        print(f"{k}: n={v['n']}(cens {v['n_censored']}) "
              f"mean={v['mean_uncensored']} ci={v['ci95_uncensored']} "
              f"lower_all={v['mean_all_observed']}")
    return 0


def refreeze() -> None:
    """显式重冻(原 main 逻辑):重抽取+回写,须裁定后使用。"""
    rows, games = extract()
    losses = [r for r in rows if not r['killed']]

    # 语料冻结入库(全部战斗类行,胜/败都留)
    corpus = OUT_DIR / 'corpus_battle_loss.jsonl'
    with corpus.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    res = {
        'generated_at': datetime.now(UTC).isoformat(),
        'source_glob': str(MATCH_GLOB / 'match_g_*.json'),
        'n_games': len(games),
        'n_battle_class_rows': len(rows),
        'n_loss_rows': len(losses),
        'n_loss_censored': sum(1 for r in losses if r['censored']),
        'corpus_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest(),
        'games_provenance': games,
        'censoring_rule': '败局 hp_after<=1 判删失(死亡/败北地板,'
                          '观测 |Δhp|=hp_before 仅下界);主估计弃删失,'
                          'all_observed=按观测值计入的下界口径;两口径同向下偏',
        'bootstrap': f'game-cluster percentile, n={N_BOOT}, seed={SEED}',
        'rung_source': 'engines_count(outcome.board_before, round.deployed '
                       'char_ids) — _settle_rung 同源式',
    }
    for name, key_fn in STATS_FAMILIES.items():
        res[name] = cell_stats(losses, key_fn)
    (OUT_DIR / 'fit_results.json').write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')

    # 控制台摘要(UTF-8)
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print(f"games={res['n_games']} rows={res['n_battle_class_rows']} "
          f"losses={res['n_loss_rows']} censored={res['n_loss_censored']}")
    for k, v in res['by_plane_node'].items():
        print(f"{k}: n={v['n']}(cens {v['n_censored']}) "
              f"mean={v['mean_uncensored']} ci={v['ci95_uncensored']} "
              f"lower_mean={v['mean_all_observed']}")
    print('--- by rung (P1 battle) ---')
    for k, v in res['by_plane_node_rung'].items():
        if 'battle' in k and k.startswith('(1'):
            print(f"{k}: n={v['n']} mean={v['mean_uncensored']} "
                  f"ci={v['ci95_uncensored']}")


if __name__ == '__main__':
    main()
