"""win_model M1 训练脚本(LR+L2 可解释胜率模型,影子模式不接 sim)。

用途:从 replay 语料(outcomes × decisions join,最近战前帧口径,与
``win_model_build_table.py`` 同键)构建训练表,训练 L2 正则逻辑回归
预测 ``killed``(战斗胜负),输出系数表(特征重要性)+ 评估(AUC/acc/
校准/bootstrap CI)+ 修复前后分层敏感性。**只读 replay 语料,不写**;
产物落 ``--out-dir``(默认 ``.debug/temp/currency_war/models/``)。

复跑命令(仓库根):
    $env:PYTHONPATH='src'; uv run python tools/cw/win_model_m1.py

CLI:
    [--out-dir PATH]     产物目录(默认 .debug/temp/currency_war/models/)
    [--seed N]           随机种子(默认 30,与 W30 对齐)
    [--holdout-frac F]   按 run 的留出比例(默认 0.25)
    [--dry-run]          只出特征统计+留出划分方案,不产模型工件

设计依据:
- ADR 草稿 ``win_model_design/ADR_草稿.md`` §2/§4(M1 特征工程+离线训练);
- 训练脚本设计稿 ``sim_压测_批41/win_model训练脚本设计稿.md``(按 run 分层
  留出/基线臂/工件 schema/零方差披露);
- 特征单一源 = ``cw_win_features.features_from_deployed``(deployed 派生
  基础特征)+ 本脚本新特征(rung/engine_pieces/core2_count/top1_share/
  gold_before),数值均引用注册表(不复制数值)。

特征 schema v1 见 ``features_schema_m1.json``(本批产物,含数据来源标注)。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))

from sr_od.application.currency_war.cw_chars import CHARACTERS  # noqa: E402
from sr_od.application.currency_war.cw_line_defs import ENGINE_FACTIONS  # noqa: E402
from sr_od.application.currency_war.cw_sim import _engines_count  # noqa: E402
from sr_od.application.currency_war.cw_win_features import (  # noqa: E402
    features_from_deployed,
)

REPLAY = REPO / '.debug/temp/currency_war/replay'
BATTLE_NODE_TYPES = ('普通战斗', '遭遇', 'boss')

# --- 引擎实体单一源(transition_combos.md;与 W30 探针对齐) ---
CORE_CHARS = frozenset({'藿藿', '丹恒·饮月', '爻光', '希儿'})
TRIO = ('藿藿', '丹恒·饮月', '爻光')
DOT_POOL = ('艾丝妲', '椒丘', '卡芙卡', '桑博')
SEELE = '希儿'

# --- 特征列序(工件 schema 单一顺序;零方差列保留、系数自然学 0) ---
NUM_FEATURES = [
    'char_count', 'star_sum', 'star2_plus', 'total_cost',
    'max_tier', 'tier3_count', 'tier_sum', 'n_tier1', 'n_tier2',
    'rung', 'engine_pieces', 'core2_count', 'top1_share',
    'gold_before', 'dot_pieces', 'engine_trio', 'seele', 'round_num',
]
NT_FEATURES = [f'nt_{nt}' for nt in BATTLE_NODE_TYPES]
FEATURE_COLS = NUM_FEATURES + NT_FEATURES


def iter_jsonl(p: Path):
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def extra_features(deployed: list[dict], feats: dict) -> dict:
    """新特征(deployed 派生;数据来源标注见 features_schema_m1.json)。"""
    bow = feats['bow']
    names = frozenset(bow.keys())
    fc = feats['faction_counts']
    n_chars = feats['char_count'] or 0
    th = {int(k): v for k, v in feats['tier_hist'].items()}
    engine_pieces = sum(
        1 for cid in bow
        if (set(getattr(CHARACTERS.get(cid), 'factions', ()))
            | set(getattr(CHARACTERS.get(cid), 'flows', ())))
        & ENGINE_FACTIONS)
    core2 = sum(1 for d in deployed
                if (d.get('char_id') or '').strip() in CORE_CHARS
                and (d.get('star') or 0) >= 2)
    top1_share = (max(fc.values()) / n_chars) if fc and n_chars else 0.0
    return {
        'star2_plus': sum(c for k, c in feats['star_hist'].items()
                          if int(k) >= 2),
        'tier_sum': sum(k * v for k, v in th.items()),
        'n_tier1': th.get(1, 0),
        'n_tier2': th.get(2, 0),
        'rung': _engines_count(fc, names),
        'engine_pieces': engine_pieces,
        'core2_count': core2,
        'top1_share': round(top1_share, 4),
        'engine_trio': sum(bow.get(c, 0) for c in TRIO),
        'dot_pieces': sum(bow.get(c, 0) for c in DOT_POOL),
        'seele': bow.get(SEELE, 0),
    }


def build_table(outcomes_path: Path, decisions_path: Path,
                out_path: Path | None) -> tuple[list[dict], dict]:
    """outcomes × decisions join 构建训练表(同 win_model_build_table 口径)。

    最近战前帧:优先同 round_num 最后一帧,否则 round_num 小于结算轮的
    最后一帧(与 board_before「最近战前观察」同口径)。
    """
    frames_by_run: dict[str, list[dict]] = defaultdict(list)
    for row in iter_jsonl(decisions_path):
        frames_by_run[row.get('run_id') or ''].append(row)

    reasons: Counter[str] = Counter()
    rows: list[dict] = []
    for o in iter_jsonl(outcomes_path):
        if (o.get('node_type') or '') not in BATTLE_NODE_TYPES:
            continue
        killed = o.get('killed')
        if not isinstance(killed, bool):
            reasons['label_unknown_killed'] += 1
            continue
        run_id = o.get('run_id') or ''
        rnd = o.get('round_num')
        frames = frames_by_run.get(run_id)
        if not frames:
            reasons['no_decisions_for_run'] += 1
            continue
        cand = [f for f in frames if f.get('round_num') == rnd]
        fallback = False
        if not cand:
            cand = [f for f in frames
                    if isinstance(f.get('round_num'), int)
                    and isinstance(rnd, int) and f['round_num'] < rnd]
            fallback = True
        if not cand:
            reasons['no_pre_battle_frame'] += 1
            continue
        frame = cand[-1]
        state = frame.get('state') or {}
        deployed = state.get('deployed') or []
        feats = features_from_deployed(deployed)
        gold = state.get('gold')
        if not isinstance(gold, (int, float)):
            gold = frame.get('gold')
        rows.append({
            **{k: feats[k] for k in feats if k in NUM_FEATURES},
            **extra_features(deployed, feats),
            'gold_before': gold,
            **{f'nt_{nt}': 1 if o.get('node_type') == nt else 0
               for nt in BATTLE_NODE_TYPES},
            'killed': killed,
            'run_id': run_id,
            'round_num': rnd,
            'node_type': o.get('node_type'),
            'era': 'post' if run_id.startswith('run_20260825') else 'pre',
            'join_fallback_round': fallback,
        })
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open('w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    stats = {
        'rows': len(rows),
        'pos': sum(1 for r in rows if r['killed']),
        'neg': sum(1 for r in rows if not r['killed']),
        'failure_reasons': dict(reasons),
        'post_rows': sum(1 for r in rows if r['era'] == 'post'),
        'post_pos': sum(1 for r in rows
                        if r['era'] == 'post' and r['killed']),
    }
    return rows, stats


def to_matrix(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    y = np.array([1 if r['killed'] else 0 for r in rows], dtype=int)
    X = np.array([[float(r[c] if r[c] is not None else 0.0)
                   for c in FEATURE_COLS] for r in rows], dtype=float)
    return X, y, [r['run_id'] for r in rows]


def make_lr(class_weight: str | None) -> Pipeline:
    return Pipeline([
        ('scaler', StandardScaler()),
        ('lr', LogisticRegression(penalty='l2', C=1.0, max_iter=3000,
                                  class_weight=class_weight,
                                  random_state=30)),
    ])


def group_holdout(runs: list[str], y: np.ndarray,
                  frac: float, seed: int,
                  rare_ok: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """按 run 分组的留出划分(防泄漏)。

    稀有格(boss-pos / 遭遇-pos)整体进训练集:含稀有 pos 的 run 强制
    进训练侧(设计稿 §3 硬要求,报告中显式声明)。
    """
    rng = np.random.RandomState(seed)
    run_to_idx: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(runs):
        run_to_idx[r].append(i)
    run_ids = list(run_to_idx.keys())
    # 稀有格 run = 该 run 含 boss-pos 或 遭遇-pos 行
    rare_runs = {r for r, idx in run_to_idx.items()
                 if any(y[i] == 1 and runs[i] == r
                        and rows_by_nt[i] in ('boss', '遭遇')
                        for i in idx)} if rare_ok else set()
    pool = [r for r in run_ids if r not in rare_runs]
    n_hold = max(1, int(round(len(pool) * frac)))
    held = set(rng.choice(pool, size=n_hold, replace=False).tolist())
    tr = np.array([i for r, idx in run_to_idx.items()
                   for i in idx if r not in held])
    te = np.array([i for r, idx in run_to_idx.items()
                   for i in idx if r in held])
    return tr, te


rows_by_nt: dict[int, str] = {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default=str(
        REPO / '.debug/temp/currency_war/models'))
    ap.add_argument('--seed', type=int, default=30)
    ap.add_argument('--holdout-frac', type=float, default=0.25)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    table_path = out_dir / 'train_table_m1.jsonl'

    rows, stats = build_table(REPLAY / 'outcomes.jsonl',
                              REPLAY / 'decisions.jsonl', table_path)
    X, y, runs = to_matrix(rows)
    global rows_by_nt
    rows_by_nt = {i: r['node_type'] for i, r in enumerate(rows)}

    pos = stats['pos']
    neg = stats['neg']
    print(f'train table: rows={stats["rows"]} pos={pos} neg={neg} '
          f'neg_ratio={neg / stats["rows"]:.3f}')
    print(f'  post-fix rows={stats["post_rows"]} pos={stats["post_pos"]} '
          f'(run_20260825_*); failure={stats["failure_reasons"]}')
    print(f'  zero-variance: '
          f'{[(c, "CONST") for c in NUM_FEATURES if X[:, FEATURE_COLS.index(c)].std() == 0]}')

    if args.dry_run:
        tr, te = group_holdout(runs, y, args.holdout_frac, args.seed)
        print(f'  holdout(by-run, frac={args.holdout_frac}): '
              f'train={len(tr)} holdout={len(te)} '
              f'holdout_pos={int(y[te].sum())} '
              f'held_runs={sorted({runs[i] for i in te})}')
        print('  dry-run: 特征统计+划分方案已出,未产模型工件。')
        return

    # ---- 按 run 分层留出(主评估) ----
    tr, te = group_holdout(runs, y, args.holdout_frac, args.seed)
    print(f'holdout: train={len(tr)} holdout={len(te)} '
          f'holdout_pos={int(y[te].sum())}')
    print(f'  held runs: {sorted({runs[i] for i in te})}')

    # 双臂:默认不加权 vs class_weight=balanced(消融记录)
    results: dict = {}
    for arm, cw in [('default', None), ('balanced', 'balanced')]:
        m = make_lr(cw).fit(X[tr], y[tr])
        p_te = m.predict_proba(X[te])[:, 1]
        auc = roc_auc_score(y[te], p_te) if len(set(y[te])) == 2 else None
        acc = float(((p_te >= 0.5).astype(int) == y[te]).mean())
        # 基线臂:node_type 边际胜率查表(训练集数出,留出集同表预测)
        base_map: dict[str, float] = {}
        for nt in BATTLE_NODE_TYPES:
            sub = [i for i in tr if rows[i]['node_type'] == nt]
            base_map[nt] = (y[sub].mean() if sub else 0.0)
        p_base = np.array([base_map[rows[i]['node_type']] for i in te])
        base_auc = (roc_auc_score(y[te], p_base)
                    if len(set(y[te])) == 2 else None)
        base_acc = float(((p_base >= 0.5).astype(int) == y[te]).mean())
        results[arm] = {
            'holdout_auc': auc, 'holdout_acc': acc,
            'baseline_node_type_auc': base_auc,
            'baseline_node_type_acc': base_acc,
            'base_map': base_map,
            'coefficients': {c: float(w) for c, w in zip(
                FEATURE_COLS, m.named_steps['lr'].coef_[0], strict=True)},
            'intercept': float(m.named_steps['lr'].intercept_[0]),
        }
        print(f'  [{arm}] holdout AUC={auc:.3f} acc={acc:.3f} | '
              f'baseline(node_type查表) AUC={base_auc:.3f} acc={base_acc:.3f}')

    # ---- GroupKFold 5 折 OOF(稳健性交叉验证,按 run 分组) ----
    gkf = GroupKFold(n_splits=5)
    oof = np.zeros(len(y))
    fold_aucs, fold_pos = [], []
    for _fold, (ftr, fte) in enumerate(gkf.split(X, y, runs)):
        fm = make_lr(None).fit(X[ftr], y[ftr])
        fp = fm.predict_proba(X[fte])[:, 1]
        oof[fte] = fp
        if len(set(y[fte])) == 2:
            fold_aucs.append(roc_auc_score(y[fte], fp))
        fold_pos.append(int(y[fte].sum()))
    cv_auc = float(np.mean(fold_aucs)) if fold_aucs else None
    cv_auc_std = float(np.std(fold_aucs)) if fold_aucs else None
    print(f'  GroupKFold5 OOF: AUC={cv_auc:.3f}±{cv_auc_std:.3f} '
          f'fold_auc={[round(a, 3) for a in fold_aucs]} '
          f'fold_pos={fold_pos}')

    # ---- block bootstrap CI(按 run 重采样 OOF AUC) ----
    rng = np.random.RandomState(args.seed)
    run_idx = defaultdict(list)
    for i, r in enumerate(runs):
        run_idx[r].append(i)
    run_ids = list(run_idx.keys())
    boot_aucs = []
    for _ in range(1000):
        sample = [i for _ in range(len(run_ids))
                  for i in run_idx[rng.choice(run_ids)]]
        if len(set(y[sample])) == 2:
            boot_aucs.append(roc_auc_score(y[sample], oof[sample]))
    ci_lo, ci_hi = (float(np.percentile(boot_aucs, 2.5)),
                    float(np.percentile(boot_aucs, 97.5))) if boot_aucs else (None, None)
    print(f'  OOF AUC bootstrap(按run重采样, n=1000) 95%CI=[{ci_lo:.3f},{ci_hi:.3f}]')

    # ---- 校准曲线:整体分桶 + 按 node_type ----
    calib = {}
    q = np.percentile(oof, [20, 40, 60, 80])
    edges = [0.0] + [float(v) for v in q] + [1.0]
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        m_ = (oof >= lo) & (oof <= hi)
        if m_.sum() >= 5:
            calib[f'{lo:.2f}-{hi:.2f}'] = {
                'n': int(m_.sum()), 'pred_mean': float(oof[m_].mean()),
                'actual_win': float(y[m_].mean())}
    calib_nt = {}
    for nt in BATTLE_NODE_TYPES:
        m_ = np.array([r['node_type'] == nt for r in rows])
        if m_.sum() >= 5:
            calib_nt[nt] = {
                'n': int(m_.sum()), 'pred_mean': float(oof[m_].mean()),
                'actual_win': float(y[m_].mean())}
    print('  calib(整体分桶 pred vs actual):',
          json.dumps(calib, ensure_ascii=False))
    print('  calib(按node_type):',
          json.dumps(calib_nt, ensure_ascii=False))

    # ---- 修复前后分层敏感性:全量模型在 post 子集 vs pre 子集 ----
    full = make_lr(None).fit(X, y)
    p_all = full.predict_proba(X)[:, 1]
    sens = {}
    for era in ('pre', 'post'):
        m_ = np.array([r['era'] == era for r in rows])
        sens[era] = {
            'n': int(m_.sum()), 'pos': int(y[m_].sum()),
            'auc': (float(roc_auc_score(y[m_], p_all[m_]))
                    if len(set(y[m_])) == 2 else None),
            'acc': float(((p_all[m_] >= 0.5).astype(int) == y[m_]).mean())}
    print('  era 分层(全量模型):', json.dumps(sens, ensure_ascii=False))

    # 系数表(标准化后可比)+ 方向判读
    coef = sorted(results['default']['coefficients'].items(),
                  key=lambda kv: -abs(kv[1]))
    print('coefficients(standardized, default arm):')
    for c, w in coef:
        print(f'  {c:>16s} {w:+.3f}')

    # ---- 产物落盘 ----
    model_path = out_dir / 'cw_win_model_m1.joblib'
    joblib.dump(full, model_path)
    meta = {
        'schema': 'cw_win_model_lr_m1_v1',
        'model_id': 'cw_win_model_m1_lr_l2',
        'feature_order': FEATURE_COLS,
        'feature_schema_ref': 'features_schema_m1.json(同目录)',
        'n': stats['rows'], 'pos': pos, 'neg': neg,
        'neg_ratio': round(neg / stats['rows'], 4),
        'post_fix': {'rows': stats['post_rows'], 'pos': stats['post_pos']},
        'fingerprint': {
            'rows': stats['rows'], 'pos': pos, 'neg': neg,
            'seed': args.seed,
            'table_file': table_path.name,
            'trained_at': '2026-08-25',
        },
        'holdout': {
            'frac': args.holdout_frac, 'held_runs': sorted({runs[i] for i in te}),
            'train_n': int(len(tr)), 'holdout_n': int(len(te)),
            'holdout_pos': int(y[te].sum()),
        },
        'arms': results,
        'groupkfold5_oof': {
            'auc_mean': cv_auc, 'auc_std': cv_auc_std,
            'fold_auc': fold_aucs, 'fold_pos': fold_pos,
            'bootstrap_ci95': [ci_lo, ci_hi],
        },
        'calibration': {'buckets': calib, 'by_node_type': calib_nt},
        'era_sensitivity': sens,
        'zero_variance_features': [c for c in NUM_FEATURES
                                   if X[:, FEATURE_COLS.index(c)].std() == 0],
        'label_source': 'outcomes.killed(实机结算真值,ADR-0306 权威口径)',
        'shadow_only': True,
    }
    meta_path = out_dir / 'cw_win_model_m1_meta.json'
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding='utf-8')
    print(f'\nsaved: {model_path}\n       {meta_path}\n       {table_path}')


if __name__ == '__main__':
    main()
