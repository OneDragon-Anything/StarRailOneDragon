# P51 v2 等待成本引理标定脚本(临时,可重跑,不入库)
# 与 v1(waiting_cost_lemma_calib.py)的结构差异:
#   1. 清除全部血换算系数(γ_hp/γ_win 出局)——W 不再经「金/血」换算链,
#      消掉 v1 的双计缺陷(P51_VALIDATION 门①1.2)与末轮掉血/胜轮+2 口径缺陷(门①1.4,
#      本脚本不再消费 hp 差分,两缺陷因结构移除而消失);
#   2. W_upside = 连胜金收入差(纯金流,胜负轮非息收入差)按板面战力桶带 CI;
#   3. W_floor  = λ(战力桶,短视界) × E[局终金销毁],局终=match-final(跨位面最后一轮,
#      非 v1 的位面 1 末;门①1.4 口径修正);
#   4. 分层/CI 一律 run 级 cluster bootstrap(120 局 = 6 数据集 × 40 run)。
# 数据:AB_{cw3,legacy_v2}_n40_{s0,r2,r3}(r1 无逐轮账本,只有聚合 JSON,不进逐轮标定)。
# 运行:$env:PYTHONPATH='src'; uv run python .debug/temp/currency_war/redesign/p51_v2_calib.py
import json
import random
import sys
from pathlib import Path
from statistics import mean, median

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE.parents[3] / 'src'))

# ---- 注册表直调(门②锚,不用任何被审方自证数字)----
from sr_od.application.currency_war.kernel.cw_economy import (  # noqa: E402
    LOSS_GOLD_BY_NODE,
    STREAK_GOLD_TABLE,
    streak_gold,
)

# 数据集口径:legacy_v2 在 s0/r2/r3 三轮间代码未变 → 同 seed 同轨迹(逐轮账本仅 run_id
# 标签不同);合并统计会三倍重复计数假缩 CI —— pooled 一律只用 legacy r3 一份。
DATASETS = [
    (side, tag, BASE / f'AB_{side}_n40_{tag}')
    for side in ('cw3', 'legacy_v2')
    for tag in ('s0', 'r2', 'r3')
]
POOLED = [('cw3', t) for t in ('s0', 'r2', 'r3')] + [('legacy_v2', 'r3')]
N_BOOT = 2000
ALPHA = 0.05


def load_rounds(d: Path) -> list[dict]:
    """逐轮 join:decisions(决策前状态+本轮收入)× outcomes(节点/胜负/轮后 hp)。"""
    dec = {}
    for line in (d / 'decisions.jsonl').read_text(encoding='utf-8').splitlines():
        r = json.loads(line)
        dec[(r['run_id'], r['plane'], r['round_num'])] = r
    rows = []
    for line in (d / 'outcomes.jsonl').read_text(encoding='utf-8').splitlines():
        o = json.loads(line)
        r = dec.get((o['run_id'], o['plane'], o['round_num']))
        if r is None:
            continue
        sim = r.get('sim') or {}
        # 纯金流差(注册表锚,见 Part A):不用逐轮收入分解(其 streak 字段结算时相
        # 偏移,亲验 58 例中 38 例与注册表错位 1 档,事件金亦混入,不可靠)
        st = (r.get('state') or {}).get('streak') or 0
        node = o['node_type']
        node_key = 'boss' if node == '首领' else ('encounter' if node == '遭遇' else 'battle')
        rows.append({
            'run': r['run_id'],
            'plane': o['plane'],
            'round': o['round_num'],
            'node': node,
            'node_key': node_key,
            'battle': ('战斗' in node) or (node == '首领'),
            'gold': r['gold'],
            'hp': r['hp'],
            'power': sim.get('deployed_power') or 0,
            'win': 1 if (o.get('sim') or {}).get('killed') else 0,
            # 该战斗轮的胜负纯金流差(金):胜=连胜表按当前连胜级,败=该节点败轮底金
            'flow_diff': streak_gold(st) - LOSS_GOLD_BY_NODE[node_key],
            'streak': st,
        })
    return rows


def load_finals(d: Path) -> dict[str, dict]:
    """局终记录(match-final):每 run 跨位面最后一轮的决策金/结算后 hp。"""
    dec, out = {}, {}
    for line in (d / 'decisions.jsonl').read_text(encoding='utf-8').splitlines():
        r = json.loads(line)
        k = r['run_id']
        if k not in dec or (r['plane'], r['round_num']) > (dec[k]['plane'], dec[k]['round_num']):
            dec[k] = r
    for line in (d / 'outcomes.jsonl').read_text(encoding='utf-8').splitlines():
        o = json.loads(line)
        k = o['run_id']
        if k not in out or (o['plane'], o['round_num']) > (out[k]['plane'], out[k]['round_num']):
            out[k] = o
    return {
        k: {'gold': dec[k]['gold'], 'hp_after': out[k]['hp_after'],
            'plane': out[k]['plane'], 'round': out[k]['round_num']}
        for k in dec if k in out
    }


def pbin(power: int) -> str:
    return 'p<=7' if power <= 7 else ('p8-12' if power <= 12 else 'p13+')


def boot_ci(stat_fn, runs, n=N_BOOT, seed=42):
    """run 级 cluster bootstrap:stat_fn(run 子集) -> float|None;返回 (点估, lo, hi)。"""
    pt = stat_fn(runs)
    rng = random.Random(seed)
    vals = []
    m = len(runs)
    for _ in range(n):
        sample = [runs[rng.randrange(m)] for _ in range(m)]
        v = stat_fn(sample)
        if v is not None:
            vals.append(v)
    if not vals:
        return pt, float('nan'), float('nan')
    vals.sort()
    lo = vals[int(ALPHA / 2 * len(vals))]
    hi = vals[min(len(vals) - 1, int((1 - ALPHA / 2) * len(vals)))]
    return pt, lo, hi


print(f'注册表锚(直调 kernel/cw_economy):STREAK_GOLD_TABLE={STREAK_GOLD_TABLE} '
      f'LOSS_GOLD_BY_NODE={LOSS_GOLD_BY_NODE}')
print(f'纯金流差理论带(连胜表 1-4 vs 败轮底金 2/4):{min(STREAK_GOLD_TABLE) - max(LOSS_GOLD_BY_NODE.values()):+d}'
      f' ~ {max(STREAK_GOLD_TABLE) - min(LOSS_GOLD_BY_NODE.values()):+d} 金/战\n')

data = {}     # (side,tag) -> rows
finals = {}   # (side,tag) -> {run: final}
for side, tag, d in DATASETS:
    data[(side, tag)] = load_rounds(d)
    finals[(side, tag)] = load_finals(d)

# ============ Part C:局终金口径复算(可复用验证亲算值)============
print('=== C. 局终金(match-final,跨位面最后一轮;非位面末)===')
for side in ('cw3', 'legacy_v2'):
    for tag in ('s0', 'r2', 'r3'):
        fs = finals[(side, tag)]
        gs = [f['gold'] for f in fs.values()]
        gs_dead = [f['gold'] for f in fs.values() if f['hp_after'] <= 0]
        dead = len(gs_dead)
        runs = sorted(fs)
        _, lo, hi = boot_ci(lambda rs, fs=fs: mean([fs[r]['gold'] for r in rs]), runs)
        # v3 附带(T3 裁决):死亡口径=末轮 hp_after<=0;补「死亡局中位」列——
        # legacy 侧存活局(打赢 P2r7 首领)携金未销毁,全体中位混入未销毁量,销毁叙述按死亡局口径收敛
        print(f'{side} {tag}: n={len(gs)} 死亡={dead}/{len(gs)} 全体中位={median(gs):.1f} '
              f'死亡局中位={median(gs_dead):.1f} '
              f'均值={mean(gs):.1f} (95%CI [{lo:.0f},{hi:.0f}])')
print()

# ============ Part A:W_upside(连胜金收入差,板面战力桶)============
print('=== A. W_upside:Δp(囤金胜率差) × Δflow_reg(注册表锚纯金流差,金/战) ===')
print('   Δflow_reg(轮) = streak_gold(当前连胜级) - LOSS_GOLD_BY_NODE[节点];'
      '基础金/息/事件金两侧对消,不入差分\n')


def upside_stat(rows_by_run, bucket):
    """统计量:Δp(桶内 g>50 vs g<=50 胜率差) × Δflow_reg(桶内战斗轮纯金流差均值)。"""
    bat = [r for r in rows_by_run if r['battle'] and pbin(r['power']) == bucket]
    if not bat:
        return None
    hi = [r for r in bat if r['gold'] > 50]
    lo = [r for r in bat if r['gold'] <= 50]
    if not hi or not lo:
        return None
    dp = mean(r['win'] for r in hi) - mean(r['win'] for r in lo)
    dfl = mean(r['flow_diff'] for r in bat)
    return {'dp': dp, 'dfl': dfl, 'n': len(bat),
            'p_hi': mean(r['win'] for r in hi), 'p_lo': mean(r['win'] for r in lo)}


for side in ('cw3', 'legacy_v2', 'pooled'):
    pool = POOLED if side == 'pooled' else [(side, tag) for tag in ('s0', 'r2', 'r3')]
    runs = []
    for s, t in pool:
        by_run = {}
        for r in data[(s, t)]:
            r = dict(r, side=s)
            by_run.setdefault(r['run'], []).append(r)
        runs.extend(list(by_run.values()))
    for bucket in ('p<=7', 'p8-12', 'p13+'):

        def stat(sample, bucket=bucket):
            rows = [r for rs in sample for r in rs]
            return upside_stat(rows, bucket)

        base = stat(runs)
        if base is None:
            print(f'{side} {bucket}: n=0(无战斗轮样本)')
            continue
        rng = random.Random(7)
        prods = []
        m = len(runs)
        for _ in range(N_BOOT):
            sample = [runs[rng.randrange(m)] for _ in range(m)]
            v = stat(sample)
            if v is not None:
                prods.append(v['dp'] * v['dfl'])
        prods.sort()
        lo = prods[int(ALPHA / 2 * len(prods))] if prods else float('nan')
        hi = prods[min(len(prods) - 1, int((1 - ALPHA / 2) * len(prods)))] if prods else float('nan')
        print(f'{side} {bucket}: n={base["n"]} Δp={base["dp"]:+.3f} '
              f'(p_hi={base["p_hi"]:.3f} p_lo={base["p_lo"]:.3f}) '
              f'Δflow_reg={base["dfl"]:+.2f} '
              f'→ W_upside={base["dp"] * base["dfl"]:+.2f} 金/轮 95%CI [{lo:+.2f},{hi:+.2f}]')
print()

# ============ Part B:W_floor = λ_death(桶,短视界) × (存量金 g + 未来纯金流)============
# §R.3 判决口径:λ_death 参数化在 (板面战力桶, 剩余轮数/视界) —— hp 不入任何自变量,
# hp=0 只是死亡事件定义([39] 决策面纪律:hp 是下游表征,不作因果输入)。
# 销毁量按 run 内实现轨迹分解:final_gold = g(当轮存量,核心项) + (final_gold − g)(未来纯金流净额)。
print('=== B. W_floor:λ3(桶) × (存量金 g + 未来纯金流);存量/未来分解 ===')
# 口径注(v3 必修3):λ3 是 3 轮累积危险率,下面打印的 W_floor 值=整个 3 轮窗口的总敞口
# 整窗归因显示,数值约夸大每轮边际量视界倍(≈3×)——只作区间敞口注记,禁作每轮边际成本引用。
K = 3  # 短视界:距局终 ≤3 轮
for side in ('cw3', 'legacy_v2', 'pooled'):
    pool = POOLED if side == 'pooled' else [(side, t) for t in ('s0', 'r2', 'r3')]
    runs = []
    for key in pool:
        by_run = {}
        for r in data[key]:
            by_run.setdefault(r['run'], []).append(r)
        finals_this = finals.get(key, {})
        for run_id, rr in by_run.items():
            if run_id not in finals_this:
                continue
            fin = finals_this[run_id]
            runs.append([dict(r, dist_end=(fin['plane'] - r['plane']) * 100 + (fin['round'] - r['round']),
                               side=key[0], final_gold=fin['gold'], died=fin['hp_after'] <= 0)
                         for r in rr])
    all_rows = [r for rs in runs for r in rs]
    n_dead_runs = sum(1 for rs in runs if rs and rs[0]['died'])
    for bucket in ('p<=7', 'p8-12', 'p13+'):
        sel = [r for r in all_rows if pbin(r['power']) == bucket]
        if not sel:
            continue
        lam3 = mean(1 if (r['died'] and r['dist_end'] <= K) else 0 for r in sel)
        # 分解:D = g(存量,核心项) + (final − g)(未来纯金流净额,含后续收支)
        g_bar = mean(r['gold'] for r in sel)
        phi_bar = mean(r['final_gold'] - r['gold'] for r in sel)
        d_bar = g_bar + phi_bar

        def floor_stat(sample, bucket=bucket):
            rows = [r for rs in sample for r in rs if pbin(r['power']) == bucket]
            if not rows:
                return None
            lam = mean(1 if (r['died'] and r['dist_end'] <= K) else 0 for r in rows)
            g = mean(r['gold'] for r in rows)
            phi = mean(r['final_gold'] - r['gold'] for r in rows)
            return lam * (g + phi)

        _, lo, hi = boot_ci(floor_stat, runs)
        share = g_bar / d_bar if d_bar else float('nan')
        print(f'{side} {bucket}: n轮={len(sel)} λ3={lam3:.3f} '
              f'D分解: 存量g={g_bar:.1f}(占比{share:.0%}) + 未来纯金流={phi_bar:+.1f} '
              f'→ W_floor敞口(3轮窗)={lam3 * d_bar:.2f} 金 95%CI [{lo:.2f},{hi:.2f}] '
              f'(死亡 run {n_dead_runs}/{len(runs)})')
    # ---- v3 必修2:λ 补桶×节点类型分层 ----
    # 复验门④-3:首领轮占比桶间 40% vs 11%,不分层的桶级 λ 有节点难度混杂(符号翻转风险,
    # §Λ 估计器纪律一)。逐节点类型重估 λ3 并给单独 CI(补溯源表「λ 无单独 CI」缺口)。
    print('  桶×节点分层 λ3(直测,run 级 cluster bootstrap 95%CI):')
    for bucket in ('p<=7', 'p8-12', 'p13+'):
        for nk in ('battle', 'encounter', 'boss'):
            def lam_stat(sample, bucket=bucket, nk=nk):
                rows = [r for rs in sample for r in rs
                        if pbin(r['power']) == bucket and r['node_key'] == nk]
                if not rows:
                    return None
                return mean(1 if (r['died'] and r['dist_end'] <= K) else 0 for r in rows)
            sel_nk = [r for r in all_rows if pbin(r['power']) == bucket and r['node_key'] == nk]
            if not sel_nk:
                continue
            pt, lo, hi = boot_ci(lam_stat, runs)
            print(f'    {side} {bucket}×{nk}: n={len(sel_nk)} '
                  f'λ3={pt:.3f} [{lo:.3f},{hi:.3f}]')
    # ---- v3 必修1:换掉「距终>6 轮 λ3=0.000」论据腿(构造性恒真) ----
    # dist_end 以已实现轨迹末轮为锚:距终>6 的轮按定义不可能在 3 轮内死亡,该条件期望恒 0
    # 与数据无关。改用非循环证据:①前瞻轮序危险率(死亡发生在第几轮,决策时轮序可观测);
    # ②桶构成(桶×侧 dist_end 分布,复验 V5 口径)。
    death_rounds = [rs[-1]['round'] + (rs[-1]['plane'] - 1) * 100 for rs in runs if rs and rs[0]['died']]
    run_lens = [rs[-1]['round'] + (rs[-1]['plane'] - 1) * 100 for rs in runs if rs]
    if death_rounds and run_lens:
        print(f'  前瞻轮序危险率(v3 论据腿,轮序=决策时可观测): '
              f'死亡轮序中位={median(death_rounds):.0f} vs 局长中位={median(run_lens):.0f} '
              f'(死亡集中发生于局末段;早期轮序死亡发生率见桶构成)')
    for bucket in ('p<=7', 'p8-12', 'p13+'):
        parts = []
        for s in ('cw3', 'legacy_v2'):
            sel_s = [r for r in all_rows if r['side'] == s and pbin(r['power']) == bucket]
            if sel_s:
                ds = sorted(r['dist_end'] for r in sel_s)
                parts.append(f'{s} n={len(sel_s)} dist_end中位={ds[len(ds) // 2]} '
                             f'距终≤6占比={sum(1 for d in ds if d <= 6) / len(ds):.1%}')
        print(f'  桶构成 {bucket}: ' + ' | '.join(parts))
print()

# ============ 附:升级时点分布(XP 通道滞后声明 P37 的实证面)============
print('=== 附. 升级动作发生时金位(附表,XP 通道到账滞后 d>=1 的声明支撑)===')
for side in ('cw3', 'legacy_v2'):
    ups = []
    for tag in ('s0', 'r2', 'r3'):
        for line in (BASE / f'AB_{side}_n40_{tag}' / 'decisions.jsonl').read_text(
                encoding='utf-8').splitlines():
            r = json.loads(line)
            for a in r.get('actions') or []:
                if a.get('__type__') == 'LevelUp':
                    ups.append(r['gold'])
                    break
    ups.sort()
    if ups:
        q25 = ups[int(0.25 * len(ups))]
        print(f'{side}: n={len(ups)} 升级轮金位 中位={median(ups):.0f} q25={q25} '
              f'金<50 占比={sum(1 for g in ups if g < 50) / len(ups):.2%}')
