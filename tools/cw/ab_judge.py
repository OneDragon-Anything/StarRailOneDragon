"""CW sim A/B 判读脚本(cw3 新层 vs 旧层;判前锁纪律:本脚本先于对拍数据落盘)。

判据单一源 = 判前锁:
``.debug/temp/currency_war/redesign/PREREG_cw3_vs_legacy_AB.md``(v1)。
本脚本只执行 §1–§3 口径,不新增/不改任何指标定义、δ、红线;跑完 A/B 后禁改。

数据源 = 新旧两侧各一个 sim 批次目录(``decisions.jsonl`` / ``outcomes.jsonl`` /
``shop_snapshots.jsonl`` / ``manifest.json``,同 seed 配对,seed 从 run_id 后缀
``_s<seed>`` 解析)。单局聚合口径复用 ``cw_batch_stats.py`` 的定义
(花费率/空转轮占比/危局空转/最大连败/行动配比/末轮成型度);runner summary 键
(``p2_entered_rate``/``avg_final_hp``,定义见
``src/sr_od/application/currency_war/sim/runner.py`` report dict)优先从批次目录
``summary.json`` 读,缺文件时按同一定义从账本现算(输出里标 summary_source)。

统计(锁 §2):每指标逐 seed 配对差 Δ=新−旧;率类(M1/M2/M3)配对 bootstrap
1000 次取 2.5 分位为 95% 置信下界;连续量(M4/M5/M6)正态近似
(均值 − 1.96×sd/√n)。非劣判定(锁 §3):差向朝下的指标(M1–M5)
下界 ≥ −δ 过线;M6 差向朝上(δ 行原文「升高不得超 5pp」),对称地
上界 ≤ +δ 过线——同一「不劣」语义在两个方向上的展开。下/上界落在
[−δ, −δ+0.3δ](M6 为 [δ−0.3δ, δ])= 贴线通过,输出单列(锁 §3 险胜条款)。

哨兵(锁 §1):S1–S5 任一越线 = 总判 FAIL,与主指标无关。

用法(项目根,两侧批次目录):
    uv run python tools/cw/ab_judge.py --new <新层批目录> --old <旧层批目录> \
        [--planes 2] [--planned-rounds N] [--out result.json]

自测(合成样本,已知答案验证每个指标与判定分支):
    uv run python tools/cw/ab_judge.py --self-test
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import tempfile
from pathlib import Path

# ---------------- 判前锁常量(与 PREREG v1 §1/§3 逐字对应,禁改) ----------------

MAIN_METRICS: dict[str, dict] = {
    # worse='low': 值小为差,非劣=Δ 置信下界 ≥ −δ;worse='high': 值大为差(仅 M6)。
    'M1': {'name': '存活通关率', 'kind': 'rate', 'delta': 0.05, 'worse': 'low'},
    'M2': {'name': 'P2入口率', 'kind': 'rate', 'delta': 0.05, 'worse': 'low'},
    'M3': {'name': '成型达成率', 'kind': 'rate', 'delta': 0.05, 'worse': 'low'},
    'M4': {'name': '末轮成型度', 'kind': 'cont', 'delta': 0.05, 'worse': 'low'},
    'M5': {'name': '花费率', 'kind': 'cont', 'delta': 0.05, 'worse': 'low'},
    'M6': {'name': '空转轮占比', 'kind': 'cont', 'delta': 0.05, 'worse': 'high'},
}
BORDERLINE_BAND = 0.3   # 贴线带宽 = δ 的 30%(锁 §3 险胜条款)
BOOTSTRAP_ITERS = 1000  # 锁 §2:配对 bootstrap 1000 次
BOOTSTRAP_SEED = 0      # 判读可复现:bootstrap 重采样固定种子
BATTLE_SKIP = {'奖励', '补给'}  # cw_batch_stats 口径:奖励/补给轮不计败胜
HP_ALERT = 40           # 危局血线(cw_batch_stats 同值)
P1_ROUNDS = 9           # sim 引擎段表:planes=2 时计划轮数 = 9 + 7(锁附录 A 场景)
P2_ROUNDS = 7

# ---------------- PREREG v5 主门(p17 三闸结构;hp 只进读数位) ----------------

# v5 依据链:p17(proofs/p17-ab-hp-measure-legality.md,hp 作主门不合法)+
# 01_strategy_layer §4.7【已裁定 [39]】+ user_playstyle [28]/[39] + 用户裁定
# (实机从未通关,通关率判幻影;sim 仅 2 位面测不到 P3 真通关)。
# 结构:主门 1 形态达标(双指标)/ 主门 2 带金占比 / 结果位 P1 通过率;
# 非劣界统一 +0 容差(置信下界 ≥0,恰为 0=贴线通过单列)。
V5_MAIN_METRICS: dict[str, dict] = {
    # 主门 1a:成型轮次中位数不劣于旧(全局轮序=首条 form_ok 行;未成型=计划+1);
    # 轮次越大=成型越晚=越差,故差向朝上(worse='high',对称展开沿 v1 M6 条款)
    'G1a': {'name': '成型轮次中位数', 'kind': 'cont', 'delta': 0.0, 'worse': 'high'},
    # 主门 1b:过渡配方达标率(engines_count 口径=form_ok 行存在)不降
    'G1b': {'name': '过渡配方达标率(engines_count口径)', 'kind': 'rate',
            'delta': 0.0, 'worse': 'low'},
    # 主门 2:位面末携金>50 的局占比(息基纪律直接读数)不低于旧
    'G2': {'name': '带金占比(位面末>50)', 'kind': 'rate', 'delta': 0.0,
           'worse': 'low'},
    # 结果位:P1 通过率 = r9 首领结算 killed 率(战斗结算符号,非 hp 量);
    # killed 是校准层代理(sim.runner 写入 = 结算 delta>=0),非真击败判定
    'G3': {'name': 'P1通过率(r9首领delta≥0代理)', 'kind': 'rate',
           'delta': 0.0, 'worse': 'low'},
}

#: G3 门语义披露(呈报口径,随判读输出强制携带;判据结构不变——只修
#: 措辞与披露,不改判定算式)。两事实来源:sim.runner 写 killed =
#: 结算 delta>=0(校准层符号代理,战斗校准下非真击败判定);sim 位面
#: 推进不以 boss 击败为门。逐局 0/1 率上门的绝对水平低时判别力弱:
#: ±1 局翻转即换判——G3 红/差只构成「扰动存在」证据,不构成臂间
#: 优劣证据。绝对水平不写死数值(单一源=本批数据现算,判读输出带
#: 各臂绝对率)。
G3_SEMANTICS_NOTE = (
    'killed=结算delta≥0校准层代理(非真boss击败;sim进位不以击败为门),'
    '逐局0/1门判别力弱:绝对率低时±1局翻转即换判——本门读数只构成'
    '扰动存在证据,不构成臂间优劣证据')

# ---------------- 数据装配 ----------------


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f'缺账本文件:{path}')
    return [json.loads(line) for line in
            open(path, encoding='utf-8') if line.strip()]


def _seed_of(run_id: str) -> int:
    """run_id 约定 = 批目录名 + ``_s<seed>``(runner.write_batch_ledger);取 seed。"""
    idx = run_id.rfind('_s')
    if idx < 0 or not run_id[idx + 2:].lstrip('-').isdigit():
        raise SystemExit(f'run_id 无 _s<seed> 后缀,无法配对:{run_id}')
    return int(run_id[idx + 2:])


def load_batch(batch_dir: Path) -> tuple[dict[int, dict], dict]:
    """读批次目录 → ({seed: 局数据}, manifest)。局数据 = 决策/结算行按局分组。"""
    games: dict[str, dict] = {}
    for row in _load_jsonl(batch_dir / 'decisions.jsonl'):
        g = games.setdefault(row.get('run_id') or '?', {'dec': [], 'out': []})
        g['dec'].append(row)
    for row in _load_jsonl(batch_dir / 'outcomes.jsonl'):
        games.setdefault(row.get('run_id') or '?',
                         {'dec': [], 'out': []})['out'].append(row)
    by_seed: dict[int, dict] = {}
    for rid, g in games.items():
        g['dec'].sort(key=lambda r: (r.get('plane') or 0, r.get('round_num') or 0))
        g['out'].sort(key=lambda r: (r.get('plane') or 0, r.get('round_num') or 0))
        seed = _seed_of(rid)
        if seed in by_seed:
            raise SystemExit(f'同批出现重复 seed,无法配对:{rid}')
        by_seed[seed] = g
    manifest_path = batch_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) \
        if manifest_path.exists() else {}
    return by_seed, manifest


def load_summary(batch_dir: Path) -> dict:
    """runner summary(可选):批次目录 summary.json;缺 = 从账本现算。"""
    p = batch_dir / 'summary.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


# ---------------- 单局指标(cw_batch_stats 口径逐条对齐) ----------------


def act_cost(acts: list[dict]) -> int:
    """局内一轮行动花费(cw_batch_stats.act_cost 同式)。"""
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


def _zero_action(acts: list[dict]) -> bool:
    return not any(a.get('__type__') in ('BuyCard', 'LevelUp', 'RefreshShop')
                   for a in acts)


def game_metrics(g: dict, *, planes: int, planned_rounds: int) -> dict:
    """单局全部指标取数(锁 §1 字段级口径;S3 死锁局也在此判)。"""
    dec, out = g['dec'], g['out']
    # hp 链:按 cw_batch_stats——结算行 hp_after 为主,决策行 hp 兜底,逐轮推 hp_delta
    rows = [{'plane': r.get('plane') or 0, 'round': r.get('round_num') or 0,
             'gold': r.get('gold'), 'hp': r.get('hp'),
             'form': r.get('b_t', r.get('form_score')), 'form_ok': r.get('form_ok'),  # b_t 优先(新数据),form_score 回退读历史
             'acts': r.get('actions') or []} for r in dec]
    out_by_key = {(r.get('plane') or 0, r.get('round_num') or 0): r for r in out}
    prev_hp = None
    losses: list[bool] = []
    for r in rows:
        o = out_by_key.get((r['plane'], r['round']))
        if o:
            hp_after = o.get('hp_after')
            r['hp_delta'] = (None if prev_hp is None or hp_after is None
                             else hp_after - prev_hp)
            r['node_type'] = o.get('node_type')
            prev_hp = hp_after
        else:
            r['hp_delta'] = None
            r['node_type'] = None
            if r['hp'] is not None:
                prev_hp = r['hp']
        losses.append(bool(r['node_type'] not in BATTLE_SKIP
                           and (r['hp_delta'] or 0) < 0))

    m: dict = {}
    # M1 存活通关:结算末行 hp_after>0 且位面覆盖到批配置末位面(未删失)
    m['M1'] = float(bool(out and (out[-1].get('hp_after') or 0) > 0
                         and max((r.get('plane') or 0) for r in out) == planes))
    # M2 P2 入口(局级 0/1;分母=全部局,与 runner p2_entered_rate 同定义)
    m['M2'] = float(any((r.get('plane') or 0) >= 2 for r in out))
    # M3 成型达成:decisions 存在 form_ok=true 行
    m['M3'] = float(any(r.get('form_ok') is True for r in dec))
    forms = [r['form'] for r in rows if r.get('form') is not None]
    m['M4'] = forms[-1] if forms else float('nan')
    # M5 花费率:act_cost 合计 / 推算收入(末金−首金+花费)
    spends = [act_cost(r['acts']) for r in rows]
    golds = [r['gold'] for r in rows if r.get('gold') is not None]
    income = (golds[-1] - golds[0] + sum(spends)) if golds else 0
    m['M5'] = (sum(spends) / income) if income > 0 else float('nan')
    # M6 空转轮占比:金≥3 且零买入/升级/刷新的轮占比
    m['M6'] = (sum(1 for r in rows if (r.get('gold') or 0) >= 3
                   and _zero_action(r['acts'])) / max(len(rows), 1))
    # S1 危局空转:hp≤40 或前两轮皆败窗口内的零动作轮数
    m['S1'] = float(sum(
        1 for i, r in enumerate(rows)
        if _zero_action(r['acts'])
        and ((r.get('hp') is not None and r['hp'] <= HP_ALERT)
             or (i >= 2 and losses[i - 2] and losses[i - 1]))))
    # S2 最大连败
    streak = best = 0
    for lost in losses:
        streak = streak + 1 if lost else 0
        best = max(best, streak)
    m['S2'] = float(best)
    # S3 死锁局:结算行数 < 计划轮数一半(轮转卡死/提前删失)
    m['S3'] = float(len(out) < planned_rounds / 2)
    # S4 行动量:BuyCard+LevelUp 合计(局级,聚合取中位)
    m['S4'] = float(sum(1 for r in rows for a in r['acts']
                        if a.get('__type__') in ('BuyCard', 'LevelUp')))
    # S5 终局 hp(仅哨兵/报告,不作主指标——锁 §1 纪律条款)
    m['final_hp'] = (out[-1].get('hp_after')
                     if out and out[-1].get('hp_after') is not None
                     else float('nan'))
    return m


# ---------------- 聚合与统计(锁 §2) ----------------


def _median(vals: list[float]) -> float:
    vals = [v for v in vals if v == v]  # 滤 NaN
    return statistics.median(vals) if vals else float('nan')


def bootstrap_lb(diff: list[float]) -> float:
    """配对 bootstrap 95% 置信下界(2.5 分位;率类用,锁 §2)。"""
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(diff)
    means = sorted(
        sum(diff[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(BOOTSTRAP_ITERS))
    return means[min(int(0.025 * BOOTSTRAP_ITERS), n - 1)]


def normal_lb(diff: list[float]) -> float:
    """正态近似 95% 置信下界(连续量用,锁 §2)。"""
    n = len(diff)
    mean = sum(diff) / n
    if n < 2:
        return mean
    sd = statistics.stdev(diff)
    return mean if sd == 0 else mean - 1.96 * sd / (n ** 0.5)


def judge_main(mid: str, new_vals: list[float], old_vals: list[float],
               spec: dict | None = None) -> dict:
    """单主指标:配对差 + 置信界 + 非劣/贴线判定(锁 §2/§3;spec 缺省=v1 M 系)。"""
    spec = spec or MAIN_METRICS[mid]
    delta = spec['delta']
    diff = [n - o for n, o in zip(new_vals, old_vals, strict=True)]
    if any(v != v for v in new_vals) or any(v != v for v in old_vals) or not diff:
        return {'verdict': 'INSUFFICIENT', 'delta': None,
                'note': '存在 NaN 局或无配对样本,无法验证非劣(按不过线计)'}
    if spec['kind'] == 'rate':
        lower, upper = bootstrap_lb(diff), float('nan')
        bound = lower
    else:
        lower = normal_lb(diff)
        upper = 2 * (sum(diff) / len(diff)) - lower  # 对称展开:上界 = 2×均值 − 下界
        bound = lower if spec['worse'] == 'low' else upper
    if spec['worse'] == 'low':
        edge = -delta + BORDERLINE_BAND * delta   # 贴线带 = [−δ, −δ+0.3δ]
        verdict = ('FAIL' if bound < -delta
                   else 'BORDERLINE' if bound <= edge else 'PASS')
    else:
        edge = delta - BORDERLINE_BAND * delta    # M6 贴线带 = [δ−0.3δ, δ]
        verdict = ('FAIL' if bound > delta
                   else 'BORDERLINE' if bound >= edge else 'PASS')
    return {'verdict': verdict, 'delta': sum(diff) / len(diff),
            'ci_lower': lower, 'ci_upper': upper, 'delta_limit': delta}


def judge_sentinels(new_gm: dict[int, dict], old_gm: dict[int, dict],
                    new_sum: dict, old_sum: dict) -> dict[str, dict]:
    """S1–S5 哨兵红线(锁 §1,任一越线=FAIL,无折中)。"""
    res: dict[str, dict] = {}
    n1, n2 = _median([g['S1'] for g in new_gm.values()]), \
        _median([g['S1'] for g in old_gm.values()])
    res['S1'] = {'tripped': n1 > n2 + 2, 'new': n1, 'old': n2,
                 'redline': '新中位 > 旧中位 + 2'}
    m1, m2 = _median([g['S2'] for g in new_gm.values()]), \
        _median([g['S2'] for g in old_gm.values()])
    res['S2'] = {'tripped': m1 > m2 + 1, 'new': m1, 'old': m2,
                 'redline': '新中位 > 旧中位 + 1'}
    dead = [g for g in new_gm.values() if g['S3'] == 1.0]
    rate = len(dead) / max(len(new_gm), 1)
    res['S3'] = {'tripped': rate > 0.01 and len(dead) >= 2,
                 'new_rate': rate, 'new_count': len(dead),
                 'redline': '局占比 > 1% 且 ≥2 局'}
    a1, a2 = _median([g['S4'] for g in new_gm.values()]), \
        _median([g['S4'] for g in old_gm.values()])
    res['S4'] = {'tripped': a1 < a2 / 2, 'new': a1, 'old': a2,
                 'redline': '新中位 < 旧中位一半'}
    h1 = new_sum.get('avg_final_hp', _median([g['final_hp']
                                              for g in new_gm.values()]))
    h2 = old_sum.get('avg_final_hp', _median([g['final_hp']
                                              for g in old_gm.values()]))
    drop = (h2 - h1) / h2 if h2 else float('nan')
    res['S5'] = {'tripped': drop == drop and drop > 0.25,
                 'new': h1, 'old': h2, 'drop': drop,
                 'redline': '相对旧层跌幅 > 25%'}
    return res


# ---------------- v5 主门(p17 三闸;hp 只进度量仪,通关率=尾部参考) ----------------


def game_metrics_v5(g: dict, *, planes: int, planned_rounds: int) -> dict:
    """v5 单局取数(p17 三闸字段映射;复用 v1 game_metrics 的经济/哨兵口径)。"""
    m = game_metrics(g, planes=planes, planned_rounds=planned_rounds)
    dec, out = g['dec'], g['out']
    # 主门 1a:成型轮次 = 首条 form_ok 行的全局轮序((plane−1)×P1_ROUNDS+round);
    # 未成型局按计划轮数+1 计入(最差值,保证可配对且方向正确)
    form_rounds = [((r.get('plane') or 1) - 1) * P1_ROUNDS
                   + (r.get('round_num') or 0)
                   for r in dec if r.get('form_ok') is True]
    m['G1a'] = float(min(form_rounds)) if form_rounds \
        else float(planned_rounds + 1)
    # 主门 1b:过渡配方达标率(engines_count 口径=form_ok 行存在;v3/v4 收敛声明)
    m['G1b'] = m['M3']
    # 主门 2:位面末携金>50 —— 每个已打位面末轮的 gold,局级=各位面末达标占比
    plane_last: dict[int, tuple[int, float]] = {}
    for r in dec:
        p = r.get('plane') or 1
        if r.get('gold') is not None:
            cur = plane_last.get(p)
            if cur is None or (r.get('round_num') or 0) >= cur[0]:
                plane_last[p] = ((r.get('round_num') or 0), float(r['gold']))
    m['G2'] = (sum(1 for _, gv in plane_last.values() if gv > 50)
               / len(plane_last)) if plane_last else float('nan')
    # 结果位:P1 通过率 = P1 首领(r9)结算 sim.killed=true;killed 语义 =
    # 校准层代理(sim.runner 写入 = 结算 delta>=0,非真击败判定);
    # sim 位面推进不以 boss 击败为门(未击败也可能进 P2),账本无首领行
    # 时兜底 = M2(进 P2 率,同代理族口径)——不是「击败是进位充要前提」。
    # 呈报披露见 G3_SEMANTICS_NOTE(随 judge_v5/v6 输出携带)。
    p1_boss = [r for r in out if (r.get('plane') or 0) < 2
               and r.get('node_type') == '首领']
    m['G3'] = (float(any((r.get('sim') or {}).get('killed') is True
                         for r in p1_boss)) if p1_boss else m['M2'])
    # 度量仪读数(hp 只进读数位,p17):P1 末 hp
    p1_out = [r for r in out if (r.get('plane') or 0) < 2]
    m['hp_p1_end'] = float(p1_out[-1]['hp_after']) \
        if p1_out and p1_out[-1].get('hp_after') is not None else float('nan')
    # 尾部参考:通关率(只观察不计判)
    m['clear_rate_ref'] = m['M1']
    return m


def judge_v5(new_dir: Path, old_dir: Path, *, planes: int,
             planned_rounds: int) -> dict:
    """PREREG v5 判读:p17 三闸主门(+0 容差)+ S1–S3 红线 + hp 度量仪读数。"""
    new_gm, new_mf = load_batch(new_dir)
    old_gm, old_mf = load_batch(old_dir)
    fp_new = new_mf.get('pool_fingerprint', '')
    fp_old = old_mf.get('pool_fingerprint', '')
    if not fp_new or fp_new != fp_old:
        raise SystemExit(f'pool_fingerprint 不一致或缺失,拒绝判读:'
                         f'新={fp_new!r} 旧={fp_old!r}')
    seeds = sorted(set(new_gm) & set(old_gm))
    missing = sorted(set(new_gm) ^ set(old_gm))
    new_sum, old_sum = load_summary(new_dir), load_summary(old_dir)
    new_m = {s: game_metrics_v5(new_gm[s], planes=planes,
                                planned_rounds=planned_rounds) for s in seeds}
    old_m = {s: game_metrics_v5(old_gm[s], planes=planes,
                                planned_rounds=planned_rounds) for s in seeds}
    mains: dict[str, dict] = {}
    for mid, spec in V5_MAIN_METRICS.items():
        r = judge_main(mid, [new_m[s][mid] for s in seeds],
                       [old_m[s][mid] for s in seeds], spec=spec)
        if spec['kind'] == 'rate':
            r['new_rate'] = sum(new_m[s][mid] for s in seeds) / max(len(seeds), 1)
            r['old_rate'] = sum(old_m[s][mid] for s in seeds) / max(len(seeds), 1)
        else:
            r['new_median'] = _median([new_m[s][mid] for s in seeds])
            r['old_median'] = _median([old_m[s][mid] for s in seeds])
        mains[mid] = {'name': spec['name'], **r}
    # G3 门语义披露(呈报口径修正:绝对率随输出携带、代理语义随 headline)
    mains['G3']['semantics'] = G3_SEMANTICS_NOTE
    # 尾部参考:通关率(两侧只观察;v5 裁定不计判)
    tail = {
        'clear_rate': {side: sum(m[s]['clear_rate_ref'] for s in seeds)
                       / max(len(seeds), 1)
                       for side, m in (('new', new_m), ('old', old_m))},
        'note': '通关率=尾部参考指标(实机从未通关;sim 仅 2 位面测不到 P3 真通关)',
    }
    # 哨兵:S1–S3 保留红线(非 hp 输入);S5 降级度量仪读数(v5 行)
    v1_sent = judge_sentinels(new_m, old_m, new_sum, old_sum)
    hard_sentinels = {k: v1_sent[k] for k in ('S1', 'S2', 'S3')}
    # 度量仪(hp 轨迹差分读数;归因用,不进判定——p17 度量合法性判定)
    valid_pairs = [s for s in seeds
                   if new_m[s]['hp_p1_end'] == new_m[s]['hp_p1_end']
                   and old_m[s]['hp_p1_end'] == old_m[s]['hp_p1_end']]
    instrument = {
        'S5_终局hp(降级读数,不计判)': {k: v for k, v in v1_sent['S5'].items()
                                        if k != 'tripped'},
        'S4_行动量中位(读数,不计判)': {'new': v1_sent['S4']['new'],
                                        'old': v1_sent['S4']['old']},
        'hp_P1末配对差均值': (sum(new_m[s]['hp_p1_end'] - old_m[s]['hp_p1_end']
                                  for s in valid_pairs) / max(len(valid_pairs), 1)),
    }
    main_all_pass = all(mains[m]['verdict'] in ('PASS', 'BORDERLINE')
                        for m in mains)
    any_tripped = any(v['tripped'] for v in hard_sentinels.values())
    return {
        'prereg': 'PREREG_cw3_vs_legacy_AB.md v5(p17 三闸重写版)',
        'pool_fingerprint': fp_new,
        'n_pairs': len(seeds),
        'seeds_unpaired': missing,
        'summary_source': {'new': 'summary.json' if new_sum else 'ledger',
                           'old': 'summary.json' if old_sum else 'ledger'},
        'metric_correction': ('用户裁定指标修正:v5 重判=判读口径修正,非事后挑数据'
                              '——修正理由=实机从未通关 + p17 判定 hp 作 A/B 主门'
                              '不合法(五级传导+策略可卖血),hp 只进读数位;'
                              '数据同 seed 同指纹,原始账本未动'),
        'main_gates': mains,
        'tail_reference': tail,
        'sentinels_hard': hard_sentinels,
        'hp_instrument': instrument,
        'verdict': ('FAIL' if any_tripped
                    else 'PASS' if main_all_pass else 'FAIL'),
        'verdict_reason': (
            '哨兵越线:' + '/'.join(k for k, v in hard_sentinels.items()
                                   if v['tripped']) if any_tripped
            else 'v5 三闸主门全过(+0 容差)' if main_all_pass
            else '主门未全过:' + '/'.join(
                k for k, v in mains.items()
                if v['verdict'] not in ('PASS', 'BORDERLINE'))),
    }


def render_human_v5(res: dict) -> str:
    lines = ['== CW sim A/B 判读(判据 = PREREG v5,p17 三闸重写版)==',
             f"指纹 {res['pool_fingerprint'][:8]} | 配对 {res['n_pairs']} 对"
             f" | 总判 **{res['verdict']}**({res['verdict_reason']})",
             f"summary 来源:{res['summary_source']}",
             f"重判声明:{res['metric_correction']}"]
    if res['seeds_unpaired']:
        lines.append(f'⚠ 未配对 seed:{res["seeds_unpaired"]}')
    lines.append('\n-- v5 主门(p17 三闸;Δ=新−旧;非劣界 +0 容差) --')
    for mid, r in res['main_gates'].items():
        if r['verdict'] == 'INSUFFICIENT':
            lines.append(f'  {mid} {r["name"]}: INSUFFICIENT({r.get("note", "")})')
            continue
        if V5_MAIN_METRICS[mid]['kind'] == 'rate':
            ref = (f"新率 {r.get('new_rate', float('nan')):.3f}"
                   f" / 旧率 {r.get('old_rate', float('nan')):.3f}")
        else:
            ref = (f"新中位 {r.get('new_median', float('nan')):.3f}"
                   f" / 旧中位 {r.get('old_median', float('nan')):.3f}")
        ci = (f"CI[{r['ci_lower']:.4f}" if r['ci_lower'] == r['ci_lower']
              else 'CI[?')
        ci += (f", {r['ci_upper']:.4f}]" if r['ci_upper'] == r['ci_upper']
               else ', ?]')
        lines.append(f'  {mid} {r["name"]}: Δ={r["delta"]:+.4f} {ci} '
                     f'δ={r["delta_limit"]} → {r["verdict"]}({ref})')
        if mid == 'G3':
            lines.append(f'    ⚠ 语义披露:{r.get("semantics", "")}')
    tr = res['tail_reference']['clear_rate']
    lines.append(f"\n-- 尾部参考(不计判) --\n  通关率:新 {tr['new']:.3f}"
                 f" / 旧 {tr['old']:.3f}({res['tail_reference']['note']})")
    lines.append('\n-- 哨兵 S1–S3(任一越线=FAIL) --')
    for sid, r in res['sentinels_hard'].items():
        kv = ' | '.join(f'{k}={v}' for k, v in r.items()
                        if k not in ('tripped', 'redline'))
        lines.append(f'  {sid}: {"越线" if r["tripped"] else "OK"}({kv})')
    lines.append('\n-- 度量仪读数(hp 等;归因用,不进判定) --')
    for name, r in res['hp_instrument'].items():
        if isinstance(r, dict):
            kv = ' | '.join(f'{k}={v}' for k, v in r.items())
        elif r == r:
            kv = f'value={r:.3f}'
        else:
            kv = 'value=nan'
        lines.append(f'  {name}: {kv}')
    return '\n'.join(lines)


def self_test_v5() -> list[str]:
    """v5 自测:三闸主门 + 度量仪降级 + 哨兵保留,已知答案用例。"""
    import shutil
    tmp = Path(tempfile.mkdtemp(prefix='ab_judge_v5_selftest_'))
    failures: list[str] = []
    fp = 'deadbeef' * 8
    games = [{'seed': s} for s in range(40)]

    # 场景 V-A:同分布 → 主门无 FAIL(Δ=0 → 贴线 BORDERLINE)、S1–S3 OK、
    # 总判 PASS、通关率参考可读、度量仪 hp 配对差=0
    a_new, a_old = tmp / 'VA_new', tmp / 'VA_old'
    _make_batch(a_new, [dict(g) for g in games], fp)
    _make_batch(a_old, [dict(g) for g in games], fp)
    r = judge_v5(a_new, a_old, planes=2, planned_rounds=16)
    if not all(v['verdict'] in ('PASS', 'BORDERLINE')
               for v in r['main_gates'].values()):
        failures.append('V-A 主门应全 PASS/BORDERLINE:' +
                        str({k: v['verdict'] for k, v in r['main_gates'].items()}))
    if any(v['tripped'] for v in r['sentinels_hard'].values()):
        failures.append('V-A S1–S3 不应越线')
    if r['verdict'] != 'PASS':
        failures.append(f"V-A 总判应 PASS,得 {r['verdict']}")
    if r['tail_reference']['clear_rate']['new'] != 1.0:
        failures.append('V-A 通关率参考应可读=1.0')
    if r['hp_instrument']['hp_P1末配对差均值'] != 0.0:
        failures.append('V-A 度量仪 hp 配对差应为 0')

    # 场景 V-B:主门 1a 成型轮次 FAIL(新侧 20 局成型推迟到第 9 轮,配对差>0、
    # 方差 0 → 置信下界=均值>0,worse='low' 值大=差 → FAIL)
    b_old = tmp / 'VB_old'
    b_new = tmp / 'VB_new'
    _make_batch(b_old, [dict(g) for g in games], fp)
    _make_batch(b_new, [{'seed': s, 'form_from': 8} if s < 20
                        else {'seed': s} for s in range(40)], fp)
    rb = judge_v5(b_new, b_old, planes=2, planned_rounds=16)
    if rb['main_gates']['G1a']['verdict'] != 'FAIL':
        failures.append('V-B G1a 应 FAIL,'
                        f"得 {rb['main_gates']['G1a']['verdict']}")

    # 场景 V-C:主门 1b FAIL(新侧 8 局 form_ok 全程 false → 达标率 Δ=−0.2)
    c_old = tmp / 'VC_old'
    c_new = tmp / 'VC_new'
    _make_batch(c_old, [dict(g) for g in games], fp)
    _make_batch(c_new, [{'seed': s, 'form_ok': False} if s < 8
                        else {'seed': s} for s in range(40)], fp)
    rc = judge_v5(c_new, c_old, planes=2, planned_rounds=16)
    if rc['main_gates']['G1b']['verdict'] != 'FAIL':
        failures.append('V-C G1b 应 FAIL,'
                        f"得 {rc['main_gates']['G1b']['verdict']}")

    # 场景 V-D:主门 2 两分支。位面末金由 end_gold 控制:旧侧恒 60(占比 1);
    # 新侧 20 局位面末金 10(占比 0.5)→ FAIL;新侧同 60 → 同分布贴线。
    d_old = tmp / 'VD_old'
    _make_batch(d_old, [{'seed': s, 'end_gold': 60} for s in range(40)], fp)
    d_bad = tmp / 'VD_bad'
    d_good = tmp / 'VD_good'
    _make_batch(d_bad, [{'seed': s, 'end_gold': 60} if s >= 20
                        else {'seed': s, 'end_gold': 10} for s in range(40)], fp)
    _make_batch(d_good, [{'seed': s, 'end_gold': 60} for s in range(40)], fp)
    rd = judge_v5(d_bad, d_old, planes=2, planned_rounds=16)
    if rd['main_gates']['G2']['verdict'] != 'FAIL':
        failures.append('V-D-bad G2 应 FAIL,'
                        f"得 {rd['main_gates']['G2']['verdict']}")
    if judge_v5(d_good, d_old, planes=2, planned_rounds=16) \
            ['main_gates']['G2']['verdict'] not in ('PASS', 'BORDERLINE'):
        failures.append('V-D-good G2 应非 FAIL')

    # 场景 V-E:结果位 P1 通过率 FAIL(4 局未进 P2 → 无首领行,兜底走
    # M2;sim 语义=进位不以击败为门,兜底是同代理族口径非充要前提)
    e_new = tmp / 'VE_new'
    e_old = tmp / 'VE_old'
    _make_batch(e_old, [dict(g) for g in games], fp)
    _make_batch(e_new, [{'seed': s, 'entered': False} if s < 4
                        else {'seed': s} for s in range(40)], fp)
    re1 = judge_v5(e_new, e_old, planes=2, planned_rounds=16)
    if re1['main_gates']['G3']['verdict'] != 'FAIL':
        failures.append('V-E G3 应 FAIL,'
                        f"得 {re1['main_gates']['G3']['verdict']}")

    # 场景 V-F:S3 死锁红线在 v5 仍生效;hp 大跌只进度量仪、不带越线位
    f_new = tmp / 'VF_new'
    _make_batch(f_new, [{'seed': s, 'deadlock': True} if s < 2
                        else {'seed': s, 'hp_final': 10}
                        for s in range(40)], fp)
    rf = judge_v5(f_new, a_old, planes=2, planned_rounds=16)
    if not rf['sentinels_hard']['S3']['tripped']:
        failures.append('V-F S3 应越线')
    if rf['verdict'] != 'FAIL':
        failures.append(f"V-F 总判应 FAIL,得 {rf['verdict']}")
    if any(v.get('tripped') for v in rf['hp_instrument'].values()
           if isinstance(v, dict)):
        failures.append('V-F 度量仪 S5 读数不应带越线位(已降级)')

    shutil.rmtree(tmp, ignore_errors=True)
    return failures


# ---------------- v6 三臂判读(判读器迁移;IMPL_DESIGN §5.1 行 1/2) ----------------

# v6 被测体叙述(R9 次要):三臂 = 单被测体两因子
# strategy_id∈{decision_v2, mandate_v1} × ev_arm∈{skeleton_only, full},
# 取三格:③=decision_v2 基线 / ①=mandate_v1+skeleton_only / ②=mandate_v1+full。
# 对照结构 = 预指定主对照 ②−①(EV 增量,命题 B,按锁内阈值门判读)+
# 次对照 ①-③(命题 A 非劣参照,仅描述性报告、不进门)——判读后禁
# 增删/更换对照(多重比较以预指定单门承载)。
ARM_FACTORS: dict[str, dict] = {
    '①': {'strategy_id': 'mandate_v1', 'ev_arm': 'skeleton_only'},
    '②': {'strategy_id': 'mandate_v1', 'ev_arm': 'full'},
    '③': {'strategy_id': 'decision_v2', 'ev_arm': None},
}
#: headline 措辞限定(CALIB_REPORT_V2 §3 裁决附条件②):U_X/T_SEARCH_A
#: 豁免 ⇒ 五面两臂恒等关闭,B1/B2 含共同降级分量——不得读作全量
#: 处理效应;归因域=sim 测量域=shop 决策面(IMPL_ADV_R200 症7)。
V6_HEADLINE_NOTE = ('headline=已开闸面处理效应 + 共同降级分量(披露计数)'
                    '显式分离:B1/B2 不得读作全量处理效应;归因域=shop '
                    '决策面(prep 面 sim 不可达)')


def _require_formal_ab_prereg(manifest: dict, label: str) -> dict:
    """症4 判读器侧防线:formal 批 manifest 必须携带 prereg 块且全绿。

    块由 ``sim/ab_core_swap.formal_ab_prereg_manifest()`` 产出(跑批侧
    序列化进 manifest):v6 检查单 + V_GAP 注入态 + 显式豁免批文 +
    活性守卫豁免快照。缺块 / v6 未绿 / V_GAP=None 且无豁免批文 ⇒
    拒读(零刷新事故形态复演必须红;与 ab_core_swap.require 双防线)。
    """
    blk = manifest.get('formal_ab_prereg')
    if not isinstance(blk, dict):
        raise SystemExit(
            f'formal A/B 批({label})manifest 缺 formal_ab_prereg 块,'
            '拒绝判读(判前锁 v6 硬前置;IMPL_ADV_R200 症4——跑批侧须经 '
            'ab_core_swap.require_v6_green_for_formal_ab 并把 '
            'formal_ab_prereg_manifest() 落进 manifest)')
    if not blk.get('v6_ok'):
        raise SystemExit(f'formal A/B 批({label})prereg 块 v6 未全绿,拒绝判读')
    if blk.get('vgap_state') == 'none' and 'V_GAP' not in (
            blk.get('formal_ab_exemptions') or {}):
        raise SystemExit(
            f'formal A/B 批({label})V_GAP=None 且无 V_GAP 显式豁免批文'
            '(对无关槽位的批文不构成本行豁免)——'
            '零刷新事故形态,拒绝判读(IMPL_ADV_R200 症4 行 17;'
            'V6_CLEANUP_REVIEW F2 槽位绑定)')
    return blk


def judge_v6(arm_dirs: dict[str, Path], *, planes: int,
             planned_rounds: int) -> dict:
    """PREREG v6 判读:三臂单被测体两因子;预指定主对照 ②−① 进门,
    次对照 ①-③ 仅描述性;强制披露 + headline 措辞限定。

    ``arm_dirs`` = {'①': path, '②': path, '③': path}(键词表见
    ARM_FACTORS)。主对照复用 v5 三闸主门(p17 结构,+0 容差)与
    S1–S3 硬哨兵;次对照只报 Δ 与 CI,不产 verdict。每臂 manifest 须
    携带 formal_ab_prereg 块(症4)与 cw4_disclosure 块(披露①)。
    """
    if set(arm_dirs) != set(ARM_FACTORS):
        raise SystemExit(f'v6 判读需三臂目录 {sorted(ARM_FACTORS)},'
                         f'得 {sorted(arm_dirs)}')
    data: dict[str, tuple[dict[int, dict], dict]] = {}
    preregs: dict[str, dict] = {}
    disclosures: dict[str, dict] = {}
    fp: str | None = None
    for label, d in arm_dirs.items():
        gm, mf = load_batch(d)
        preregs[label] = _require_formal_ab_prereg(mf, label)
        disc = mf.get('cw4_disclosure')
        if not isinstance(disc, dict):
            raise SystemExit(
                f'formal A/B 批({label})manifest 缺 cw4_disclosure 块,'
                '拒绝判读(预注册①:CALIB_REPORT_V2 §3.2 强制披露清单——'
                '跑批侧按 ab_core_swap.cw4_disclosure_from_session 逐局聚合)')
        disclosures[label] = disc
        f = mf.get('pool_fingerprint', '')
        if not f or (fp is not None and f != fp):
            raise SystemExit(f'三臂 pool_fingerprint 不一致或缺档({label}):'
                             f'{f!r} vs {fp!r}')
        fp = f if fp is None else fp
        data[label] = (gm, mf)
    seeds = sorted(set(data['①'][0]) & set(data['②'][0]) & set(data['③'][0]))
    if not seeds:
        raise SystemExit('三臂无共同 seed,无法配对')

    def _metrics(label: str) -> dict[int, dict]:
        return {s: game_metrics_v5(data[label][0][s], planes=planes,
                                   planned_rounds=planned_rounds)
                for s in seeds}

    m1, m2, m3 = _metrics('①'), _metrics('②'), _metrics('③')
    # 预指定主对照 ②−①(进门):v5 三闸主门 + 硬哨兵
    mains: dict[str, dict] = {}
    for mid, spec in V5_MAIN_METRICS.items():
        r = judge_main(mid, [m2[s][mid] for s in seeds],
                       [m1[s][mid] for s in seeds], spec=spec)
        r['contrast'] = '②−①(预指定主对照,EV 增量)'
        # 绝对率随门输出(度量诚实:v6 曾只报 Δ/CI,报告侧绝对率无单一
        # 源可回对 → 手填数不可复现;现由本判读器从同批账本现算)
        if spec['kind'] == 'rate':
            r['②_rate'] = sum(m2[s][mid] for s in seeds) / max(len(seeds), 1)
            r['①_rate'] = sum(m1[s][mid] for s in seeds) / max(len(seeds), 1)
        mains[mid] = {'name': spec['name'], **r}
    mains['G3']['semantics'] = G3_SEMANTICS_NOTE
    v1_sent = judge_sentinels(m2, m1, load_summary(arm_dirs['②']),
                              load_summary(arm_dirs['①']))
    hard_sentinels = {k: v1_sent[k] for k in ('S1', 'S2', 'S3')}
    # 次对照 ①-③(仅描述性,不进门):只报 Δ 与 CI,无 verdict
    secondary: dict[str, dict] = {}
    for mid, spec in V5_MAIN_METRICS.items():
        diff = [m1[s][mid] - m3[s][mid] for s in seeds]
        mean = sum(diff) / len(diff)
        sd = (statistics.stdev(diff) if len(diff) > 1 and
              statistics.stdev(diff) else 0.0)
        secondary[mid] = {
            'name': spec['name'], 'delta_1m3': mean,
            'ci_lo_normal': mean - 1.96 * sd / (len(diff) ** 0.5),
            'note': '次对照 ①-③(命题 A 非劣参照):仅描述性,不进门'
                    '(v6 多重比较声明:预指定主对照单门)'}
        if spec['kind'] == 'rate':
            # ③ 基线绝对率(G3 判别力披露的参照面:绝对水平低 → ±1 局
            # 翻转即换判,与 G3_SEMANTICS_NOTE 并读)
            secondary[mid]['③_rate'] = (sum(m3[s][mid] for s in seeds)
                                        / max(len(seeds), 1))
    main_all_pass = all(mains[m]['verdict'] in ('PASS', 'BORDERLINE')
                        for m in mains)
    any_tripped = any(v['tripped'] for v in hard_sentinels.values())
    return {
        'prereg': 'PREREG_cw3_vs_legacy_AB.md v6(三臂单被测体两因子;'
                  '预指定主对照 ②−①;判读器迁移=v6 词表/对照结构落地)',
        'arm_factors': {k: dict(v) for k, v in ARM_FACTORS.items()},
        'pool_fingerprint': fp,
        'n_pairs': len(seeds),
        'headline_note': V6_HEADLINE_NOTE,
        'main_gates': mains,
        'secondary_descriptive': secondary,
        'sentinels_hard': hard_sentinels,
        'disclosure': disclosures,
        'formal_ab_prereg': preregs,
        'verdict': ('FAIL' if any_tripped
                    else 'PASS' if main_all_pass else 'FAIL'),
        'verdict_reason': (
            '哨兵越线:' + '/'.join(k for k, v in hard_sentinels.items()
                                   if v['tripped']) if any_tripped
            else '预指定主对照 ②−① 三闸全过(+0 容差)' if main_all_pass
            else '主对照未全过:' + '/'.join(
                k for k, v in mains.items()
                if v['verdict'] not in ('PASS', 'BORDERLINE'))),
    }


def render_human_v6(res: dict) -> str:
    lines = ['== CW sim A/B 判读(判据 = PREREG v6,三臂两因子)==',
              f"指纹 {res['pool_fingerprint'][:8]} | 配对 {res['n_pairs']} 对"
              f" | 总判 **{res['verdict']}**({res['verdict_reason']})",
              f"⚠ headline 措辞限定:{res['headline_note']}"]
    lines.append('\n-- 主对照 ②−①(预指定,进门;Δ=②−①;+0 容差) --')
    for mid, r in res['main_gates'].items():
        if r['verdict'] == 'INSUFFICIENT':
            lines.append(f'  {mid} {r["name"]}: INSUFFICIENT({r.get("note", "")})')
            continue
        ci = f"CI[{r['ci_lower']:.4f}, {r['ci_upper']:.4f}]"
        ref = (f" | 率 ②{r.get('②_rate', float('nan')):.3f}"
               f"/①{r.get('①_rate', float('nan')):.3f}"
               if '②_rate' in r else '')
        lines.append(f'  {mid} {r["name"]}: Δ={r["delta"]:+.4f} {ci} '
                     f'→ {r["verdict"]}{ref}')
        if mid == 'G3':
            lines.append(f'    ⚠ 语义披露:{r.get("semantics", "")}')
    lines.append('\n-- 次对照 ①-③(仅描述性,不进门) --')
    for mid, r in res['secondary_descriptive'].items():
        ref = (f" | ③率 {r['③_rate']:.3f}" if '③_rate' in r else '')
        lines.append(f'  {mid} {r["name"]}: Δ={r["delta_1m3"]:+.4f}'
                     f'(CI_lo {r["ci_lo_normal"]:+.4f}{ref};{r["note"]})')
    lines.append('\n-- 硬哨兵 S1–S3(主对照 ② vs ①;任一越线=FAIL) --')
    for sid, r in res['sentinels_hard'].items():
        kv = ' | '.join(f'{k}={v}' for k, v in r.items()
                        if k not in ('tripped', 'redline'))
        lines.append(f'  {sid}: {"越线" if r["tripped"] else "OK"}({kv})')
    lines.append('\n-- 强制披露计数(共同降级分量;随 headline) --')
    for label, disc in res['disclosure'].items():
        kv = ' | '.join(f'{k}={v}' for k, v in sorted(disc.items())) or '(空)'
        lines.append(f'  臂{label}: {kv}')
    return '\n'.join(lines)


def self_test_v6() -> list[str]:
    """v6 自测:①缺 prereg 块拒读(零刷新事故形态)②V_GAP=None 无豁免
    拒读 ③全件齐备判读通过(主对照进门/次对照描述性/披露渲染)。"""
    import shutil
    tmp = Path(tempfile.mkdtemp(prefix='ab_judge_v6_selftest_'))
    failures: list[str] = []
    fp = 'deadbeef' * 8
    games = [{'seed': s} for s in range(40)]
    arms = {}
    for label in ('①', '②', '③'):
        d = tmp / f'arm{label}'
        _make_batch(d, [dict(g) for g in games], fp)
        arms[label] = d

    # 场景 W-A:manifest 无 prereg 块 ⇒ 拒读(症4 事故形态)
    try:
        judge_v6(dict(arms), planes=2, planned_rounds=16)
        failures.append('W-A 缺 prereg 块应 SystemExit')
    except SystemExit:
        pass

    def _patch_manifest(label: str, blk: dict | None, disc: dict | None,
                        v6_ok: bool = True) -> None:
        p = arms[label] / 'manifest.json'
        m = {'pool_fingerprint': fp}
        if blk is not None:
            m['formal_ab_prereg'] = blk
        if disc is not None:
            m['cw4_disclosure'] = disc
        p.write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')

    def _blk(v6_ok: bool = True, vgap: str = 'injected',
             exempt: dict | None = None) -> dict:
        return {'v6_rows': [], 'v6_ok': v6_ok, 'vgap_state': vgap,
                'formal_ab_exemptions': exempt or {},
                'liveness_exempt_disclosure': {}}

    # 场景 W-B:prereg 块在但 V_GAP=none 且无豁免 ⇒ 拒读(行 17 判读侧)
    for label in arms:
        _patch_manifest(label, _blk(vgap='none'),
                        {'shop_ev_u_unavailable': 3})
    try:
        judge_v6(dict(arms), planes=2, planned_rounds=16)
        failures.append('W-B V_GAP=none 无豁免应 SystemExit')
    except SystemExit:
        pass

    # 场景 W-C:全件齐备(V_GAP 注入态)⇒ 判读通过;主对照全贴线
    # BORDERLINE(两侧同分布)、次对照带描述性注记、披露渲染、措辞限定在。
    for label in arms:
        _patch_manifest(label, _blk(),
                        {'shop_ev_u_unavailable': 2, 'shop_r1_ev_unavailable': 5})
    r = judge_v6(dict(arms), planes=2, planned_rounds=16)
    if r['verdict'] != 'PASS':
        failures.append(f'W-C 总判应 PASS(同分布贴线),得 {r["verdict"]}')
    if not all('仅描述性' in s['note']
               for s in r['secondary_descriptive'].values()):
        failures.append('W-C 次对照应仅描述性')
    if any('verdict' in s for s in r['secondary_descriptive'].values()):
        failures.append('W-C 次对照不得带 verdict(不进门)')
    human = render_human_v6(r)
    if '不得读作全量处理效应' not in human:
        failures.append('W-C headline 措辞限定缺失')
    if 'shop_r1_ev_unavailable=5' not in human:
        failures.append('W-C 披露计数未随 headline 渲染')
    if 'mandate_v1' not in json.dumps(r['arm_factors']):
        failures.append('W-C 三臂词表(mandate_v1/ev_arm)缺失')

    shutil.rmtree(tmp, ignore_errors=True)
    return failures


# ---------------- 总判读 ----------------


def judge(new_dir: Path, old_dir: Path, *, planes: int,
          planned_rounds: int) -> dict:
    new_gm, new_mf = load_batch(new_dir)
    old_gm, old_mf = load_batch(old_dir)
    fp_new, fp_old = new_mf.get('pool_fingerprint', ''), \
        old_mf.get('pool_fingerprint', '')
    if not fp_new or fp_new != fp_old:
        raise SystemExit(
            f'pool_fingerprint 不一致或缺失,拒绝判读(锁 §2 重放要件):'
            f'新={fp_new!r} 旧={fp_old!r}')
    seeds = sorted(set(new_gm) & set(old_gm))
    missing = sorted(set(new_gm) ^ set(old_gm))
    new_sum, old_sum = load_summary(new_dir), load_summary(old_dir)
    new_m = {s: game_metrics(new_gm[s], planes=planes,
                             planned_rounds=planned_rounds) for s in seeds}
    old_m = {s: game_metrics(old_gm[s], planes=planes,
                             planned_rounds=planned_rounds) for s in seeds}
    mains = {}
    for mid in MAIN_METRICS:
        if mid == 'M2' and 'p2_entered_rate' in new_sum:
            # 锁 §1:M2 点值取 runner summary;bootstrap 仍用局级 0/1 配对序列
            pt = new_sum['p2_entered_rate'] - old_sum['p2_entered_rate']
            r = judge_main(mid, [new_m[s]['M2'] for s in seeds],
                           [old_m[s]['M2'] for s in seeds])
            r['delta'] = pt
            r['note'] = '点值=runner summary p2_entered_rate'
        else:
            r = judge_main(mid, [new_m[s][mid] for s in seeds],
                           [old_m[s][mid] for s in seeds])
        r['new_median' if MAIN_METRICS[mid]['kind'] == 'cont' else 'new_rate'] = \
            _median([new_m[s][mid] for s in seeds]) \
            if MAIN_METRICS[mid]['kind'] == 'cont' \
            else sum(new_m[s][mid] for s in seeds) / max(len(seeds), 1)
        r['old_median' if MAIN_METRICS[mid]['kind'] == 'cont' else 'old_rate'] = \
            _median([old_m[s][mid] for s in seeds]) \
            if MAIN_METRICS[mid]['kind'] == 'cont' \
            else sum(old_m[s][mid] for s in seeds) / max(len(seeds), 1)
        mains[mid] = {'name': MAIN_METRICS[mid]['name'], **r}
    sentinels = judge_sentinels(new_m, old_m, new_sum, old_sum)
    main_all_pass = all(mains[m]['verdict'] in ('PASS', 'BORDERLINE')
                        for m in mains)
    any_tripped = any(v['tripped'] for v in sentinels.values())
    return {
        'prereg': 'PREREG_cw3_vs_legacy_AB.md v1',
        'pool_fingerprint': fp_new,
        'n_pairs': len(seeds),
        'seeds_unpaired': missing,
        'summary_source': {'new': 'summary.json' if new_sum else 'ledger',
                           'old': 'summary.json' if old_sum else 'ledger'},
        'main_metrics': mains,
        'sentinels': sentinels,
        'verdict': ('FAIL' if any_tripped
                    else 'PASS' if main_all_pass else 'FAIL'),
        'verdict_reason': (
            '哨兵越线:' + '/'.join(k for k, v in sentinels.items()
                                   if v['tripped']) if any_tripped
            else '全部主指标非劣过线' if main_all_pass
            else '主指标未全过线:' + '/'.join(
                k for k, v in mains.items()
                if v['verdict'] not in ('PASS', 'BORDERLINE'))),
    }


def render_human(res: dict) -> str:
    lines = ['== CW sim A/B 判读(判据 = PREREG v1)==',
             f"指纹 {res['pool_fingerprint'][:8]} | 配对 {res['n_pairs']} 对"
             f" | 总判 **{res['verdict']}**({res['verdict_reason']})",
             f"summary 来源:{res['summary_source']}"]
    if res['seeds_unpaired']:
        lines.append(f'⚠ 未配对 seed:{res["seeds_unpaired"]}')
    lines.append('\n-- 主指标(Δ=新−旧;非劣界见 δ) --')
    for mid, r in res['main_metrics'].items():
        if r['verdict'] == 'INSUFFICIENT':
            lines.append(f'  {mid} {r["name"]}: INSUFFICIENT(数据不足)')
            continue
        if MAIN_METRICS[mid]['kind'] == 'rate':
            ref = f"新率 {r.get('new_rate'):.3f} / 旧率 {r.get('old_rate'):.3f}"
        else:
            ref = f"新中位 {r.get('new_median'):.3f} / 旧中位 {r.get('old_median'):.3f}"
        ci = (f"CI[{r['ci_lower']:.4f}" if r['ci_lower'] == r['ci_lower'] else 'CI[?')
        ci += (f", {r['ci_upper']:.4f}]" if r['ci_upper'] == r['ci_upper'] else ', ?]')
        lines.append(f'  {mid} {r["name"]}: Δ={r["delta"]:+.4f} {ci} '
                     f'δ={r["delta_limit"]} → {r["verdict"]}({ref})')
    lines.append('\n-- 哨兵(任一越线=FAIL) --')
    for sid, r in res['sentinels'].items():
        kv = ' | '.join(f'{k}={v}' for k, v in r.items()
                        if k not in ('tripped', 'redline'))
        lines.append(f'  {sid}: {"🚨越线" if r["tripped"] else "OK"}({kv})')
    return '\n'.join(lines)


# ---------------- 合成样本自测(本批无 A/B 数据;已知答案验证) ----------------


def _write_game(batch: Path, seed: int, *, planes: int = 2, planned: int = 16,
                clear: bool = True, entered: bool = True, form_ok: bool = True,
                form_score: float = 0.9, hp_final: float = 60,
                loss_streak: int = 0, idle_rounds: int = 0,
                danger_idle: int = 0, n_buys: int = 6, n_levels: int = 2,
                deadlock: bool = False, form_eps: float = 0.0,
                form_from: int = 4, end_gold: float | None = None) -> None:
    """写一局合成账本。参数直映各指标(декISIONS/OUTCOMES 两流,契约见锁附录 B)。"""
    rid = f'{batch.name}_s{seed}'
    n_rounds = 4 if deadlock else planned  # 死锁局:结算行数 < 计划一半
    dec_p = batch / 'decisions.jsonl'
    out_p = batch / 'outcomes.jsonl'
    hp = hp_final + loss_streak * 5  # 结算后回到 hp_final,途中多掉连败段
    for i in range(n_rounds):
        plane = 1 if i < 9 else 2
        rnd = i + 1 if plane == 1 else i - 8
        if plane == 2 and not entered:
            break  # 未进 P2:只写 P1 段
        idle = i < idle_rounds + danger_idle
        acts = [] if idle else (
            [{'__type__': 'BuyCard', 'card': {'cost': 3, 'name': f'c{j}'}}
             for j in range(n_buys)]
            + [{'__type__': 'LevelUp', 'cost': 4} for _ in range(n_levels)])
        # 位面末轮(P1 末=i=8;P2 末=最后一轮)可注入指定携金(G2 自测用)
        plane_end = (i == 8) or (i == n_rounds - 1)
        gold = (end_gold if (end_gold is not None and plane_end)
                else (30 if idle else 2))
        dec_p.open('a', encoding='utf-8').write(json.dumps({
            'run_id': rid, 'plane': plane, 'round_num': rnd,
            'gold': gold, 'hp': hp,
            'form_score': form_score + (form_eps if i % 2 else -form_eps),
            'form_ok': form_ok and i >= form_from, 'actions': acts,
            'state': {'level': 8},
        }, ensure_ascii=False) + '\n')
        # 连败段放最前:hp_delta<0 的战斗轮
        lost = i < loss_streak
        hp = (hp_final if i == n_rounds - 1
              else hp - (5 if lost else 0))
        out_p.open('a', encoding='utf-8').write(json.dumps({
            'run_id': rid, 'plane': plane, 'round_num': rnd,
            'node_type': '普通战斗', 'hp_after': hp, 'sim': {'killed': not lost},
        }, ensure_ascii=False) + '\n')
    if clear and not deadlock and planes >= 2 and entered:
        pass  # 末行已在 plane=2 且 hp_final>0 → 通关


def _make_batch(path: Path, games: list[dict], fingerprint: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for kw in games:
        _write_game(path, kw.pop('seed'), **kw)
    (path / 'manifest.json').write_text(json.dumps(
        {'pool_fingerprint': fingerprint}), encoding='utf-8')


def self_test() -> int:
    """合成样本自测:每个指标与每个判定分支各有一条已知答案用例。"""
    import shutil
    tmp = Path(tempfile.mkdtemp(prefix='ab_judge_selftest_'))
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    fp = 'deadbeef' * 8
    # 场景 A:两侧全同 → 主指标全 PASS、哨兵全 OK、总判 PASS
    a_new, a_old = tmp / 'A_new', tmp / 'A_old'
    games = [{'seed': s} for s in range(40)]
    _make_batch(a_new, [dict(g) for g in games], fp)
    _make_batch(a_old, [dict(g) for g in games], fp)
    r = judge(a_new, a_old, planes=2, planned_rounds=16)
    check(r['verdict'] == 'PASS', f'A 总判应 PASS,得 {r["verdict"]}')
    check(all(v['verdict'] == 'PASS' for v in r['main_metrics'].values()),
          'A 主指标应全 PASS:' + str({k: v['verdict']
                                      for k, v in r['main_metrics'].items()}))
    check(not any(v['tripped'] for v in r['sentinels'].values()),
          'A 哨兵不应越线')
    check(r['n_pairs'] == 40 and not r['seeds_unpaired'], 'A 配对应 40 对')

    # 场景 B:M1 率类 FAIL(新少通关 4 局,Δ≈−0.1,bootstrap 下界 < −0.05)
    b_new, b_old = tmp / 'B_new', tmp / 'B_old'
    old_g = [{'seed': s} for s in range(40)]
    new_g = [{'seed': s, 'clear': False, 'entered': False} if s < 4
             else {'seed': s} for s in range(40)]
    _make_batch(b_new, new_g, fp)
    _make_batch(b_old, old_g, fp)
    # C:M4 贴线带 BORDERLINE(新侧 form_score = 0.85±0.0005,Δ≈−0.0495、方差 0)
    c_new, c_old = tmp / 'C_new', tmp / 'C_old'
    _make_batch(c_old, [{'seed': s} for s in range(40)], fp)
    _make_batch(c_new, [{'seed': s, 'form_score': 0.85, 'form_eps': 0.0005}
                        for s in range(40)], fp)
    r4 = judge(c_new, c_old, planes=2, planned_rounds=16)
    check(r4['main_metrics']['M4']['verdict'] == 'BORDERLINE',
          f'C M4 应 BORDERLINE,得 {r4["main_metrics"]["M4"].get("verdict")} '
          f"CI={r4['main_metrics']['M4'].get('ci_lower')}")
    check(r4['main_metrics']['M1']['verdict'] == 'PASS', 'C M1 应 PASS')
    # B:M1 FAIL 复验(新侧 4 局未通关未进 P2)
    rb = judge(b_new, b_old, planes=2, planned_rounds=16)
    check(rb['main_metrics']['M1']['verdict'] == 'FAIL',
          f'B M1 应 FAIL,得 {rb["main_metrics"]["M1"]["verdict"]}')
    check(rb['main_metrics']['M2']['verdict'] == 'FAIL',
          f'B M2 应 FAIL(同批未进 P2),得 {rb["main_metrics"]["M2"]["verdict"]}')
    # B 总判 FAIL(主指标未全过)
    check(rb['verdict'] == 'FAIL', f'B 总判应 FAIL,得 {rb["verdict"]}')

    # 场景 D:M6 方向性非劣(差向朝上,δ=+0.05)。
    # 局占比量化粒度 = 1/计划轮数:32 轮/局使 Δ 步长 0.03125 < δ,
    # 可构造「小幅升高过线」与「大幅升高 FAIL」两侧。
    d_ok_n = tmp / 'D_ok_new'
    d_bad_n = tmp / 'D_bad_new'
    d_old = tmp / 'D_old'
    _make_batch(d_old, [{'seed': s, 'idle_rounds': 2, 'planned': 32}
                        for s in range(40)], fp)
    _make_batch(d_ok_n, [{'seed': s, 'idle_rounds': 3, 'planned': 32}
                         for s in range(40)], fp)
    _make_batch(d_bad_n, [{'seed': s, 'idle_rounds': 6, 'planned': 32}
                          for s in range(40)], fp)
    check(judge(d_ok_n, d_old, planes=2, planned_rounds=32)
          ['main_metrics']['M6']['verdict'] == 'PASS',
          'D-ok M6(Δ=+0.03125)应干净 PASS')
    check(judge(d_bad_n, d_old, planes=2, planned_rounds=32)
          ['main_metrics']['M6']['verdict'] == 'FAIL',
          'D-bad M6(Δ=+0.125)应 FAIL')

    # 场景 E:哨兵逐个越线(E1 危局空转 / E2 连败 / E3 死锁 / E4 行动塌缩 / E5 hp 塌方)。
    # E1 构造:连败 5 轮窗口内前 6 轮零动作 → 每局危局空转 4 轮,全 40 局命中
    # → 新中位 4 > 旧中位 0 + 2(cw_batch_stats 危局口径:连败窗口或 hp 低线;
    #   首轮无前序 hp 不计败,故连败从第 2 轮起算)。
    e_old = tmp / 'E_old'
    _make_batch(e_old, [{'seed': s} for s in range(40)], fp)
    arms = {
        'S1': [{'seed': s, 'loss_streak': 5, 'danger_idle': 6}
               for s in range(40)],
        'S2': [{'seed': s, 'loss_streak': 5} if s < 20 else {'seed': s}
               for s in range(40)],
        'S3': [{'seed': s, 'deadlock': True} if s < 2 else {'seed': s}
               for s in range(40)],
        'S4': [{'seed': s, 'n_buys': 2, 'n_levels': 0} for s in range(40)],
        'S5': [{'seed': s, 'hp_final': 30} for s in range(40)],
    }
    for sid, games in arms.items():
        d = tmp / f'E_{sid}_new'
        _make_batch(d, games, fp)
        r = judge(d, e_old, planes=2, planned_rounds=16)
        check(r['sentinels'][sid]['tripped'], f'E {sid} 哨兵应越线')
        check(r['verdict'] == 'FAIL', f'E {sid} 总判应 FAIL')
        check(sid in r['verdict_reason'], f'E {sid} 越线原因应点名')

    # 场景 F:指纹不一致 → 拒判
    f_new = tmp / 'F_new'
    _make_batch(f_new, [{'seed': 0}], 'ffffffff' * 8)
    try:
        judge(f_new, e_old, planes=2, planned_rounds=16)
        check(False, 'F 指纹不一致应 SystemExit')
    except SystemExit:
        pass

    shutil.rmtree(tmp, ignore_errors=True)
    if failures:
        print('自测失败:')
        for f in failures:
            print(' -', f)
        return 1
    print('自测通过:11 个场景(A 同分布 PASS / B 率类 FAIL / C 贴线 BORDERLINE /'
          ' D M6 方向 / E 五哨兵逐个越线 / F 指纹拒判)全部命中已知答案。')
    return 0


# ---------------- CLI ----------------


def main() -> None:
    # Windows 控制台缺省 GBK:Δ/− 等符号会炸输出,cw_sim CLI 同款防御
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--new', default='', help='新层 sim 批次目录')
    ap.add_argument('--old', default='', help='旧层 sim 批次目录')
    ap.add_argument('--planes', type=int, default=2, help='批配置位面数(M1 末位面)')
    ap.add_argument('--planned-rounds', type=int, default=0,
                    help='批配置单局计划轮数(S3 分母;缺省 = 9+7×(planes−1))')
    ap.add_argument('--out', default='', help='机器可读结论 JSON 落盘路径')
    ap.add_argument('--prereg', choices=['v1', 'v5', 'v6'], default='v1',
                    help='判前锁版本:v1=原 6 主指标+5 哨兵;v5=用户裁定修正'
                         '(5 主指标+通关率降尾部参考,修订表 v5 行);'
                         'v6=三臂单被测体两因子(①mandate_v1/skeleton '
                         '②mandate_v1/full ③decision_v2;预指定主对照 '
                         '②−①;强制 prereg/披露块)')
    ap.add_argument('--arm1', default='', help='v6 臂①目录(mandate_v1 skeleton)')
    ap.add_argument('--arm2', default='', help='v6 臂②目录(mandate_v1 full)')
    ap.add_argument('--arm3', default='', help='v6 臂③目录(decision_v2 基线)')
    ap.add_argument('--self-test', action='store_true',
                    help='合成样本自测(不读真实数据;v1+v5 两套)')
    args = ap.parse_args()
    if args.self_test:
        v1_fails = self_test()   # 内部打印结论,返回 0/1
        fails = ([] if v1_fails == 0
                 else [f'v1 自测失败(见上方输出,exit={v1_fails})'])
        fails += self_test_v5()
        if fails:
            print('v5 自测失败:')
            for f in fails:
                print(' -', f)
            sys.exit(1)
        fails_v6 = self_test_v6()
        if fails_v6:
            print('v6 自测失败:')
            for f in fails_v6:
                print(' -', f)
            sys.exit(1)
        print('v5 自测通过:V-A 同分布主门全过+度量仪 hp 差=0 / V-B G1a 成型推迟 '
              'FAIL / V-C G1b 成型塌 FAIL / V-D G2 带金占比两分支(低→FAIL,'
              '同分布→非FAIL)/ V-E G3 未进P2 FAIL / V-F S3 红线仍生效+度量仪无'
              '越线位,全部命中已知答案。')
        print('v6 自测通过:W-A 缺 prereg 块拒读 / W-B V_GAP=none 无豁免拒读'
              '(症4 事故形态复演红)/ W-C 全件齐备判读(主对照进门+次对照'
              '描述性+披露随 headline+措辞限定)。')
        sys.exit(0)
    if not (args.new and args.old):
        ap.error('需 --new/--old 批次目录对,或 --self-test')
    planned = args.planned_rounds or (P1_ROUNDS + P2_ROUNDS * (args.planes - 1))
    if args.prereg == 'v6':
        if not (args.arm1 and args.arm2 and args.arm3):
            ap.error('v6 判读需 --arm1/--arm2/--arm3 三臂目录')
        res = judge_v6({'①': Path(args.arm1), '②': Path(args.arm2),
                        '③': Path(args.arm3)},
                       planes=args.planes, planned_rounds=planned)
        human = render_human_v6(res)
    elif args.prereg == 'v5':
        res = judge_v5(Path(args.new), Path(args.old), planes=args.planes,
                       planned_rounds=planned)
        human = render_human_v5(res)
    else:
        res = judge(Path(args.new), Path(args.old), planes=args.planes,
                    planned_rounds=planned)
        human = render_human(res)
    if args.out:
        Path(args.out).write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'机器可读结论已落盘:{args.out}')
    print(human)
    # 判读脚本不替流程做决定,但退出码给编排用:0=过线,1=不过线
    sys.exit(0 if res['verdict'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
