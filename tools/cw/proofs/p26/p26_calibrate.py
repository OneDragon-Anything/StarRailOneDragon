"""P26 参数标定:Δp_prep 条件表 + L_node 分位带(纯离线管线,零拟合零常数加码)。

背景(math_proofs P26 双挂账采集批;流程/进度.md「P26参数标定采集批」行):
备战期决策的期望收益标定需要两个条件分布——
① Δp_prep:给定备战态桶(三维桶键 = 围栏内支出额 / carry 装备数 /
   engines 成型档)与下一节点型,输掉该节点的概率(败率 + CI);
② L_node:给定下一节点型、条件在「输」上的伤害分布尾部带分位 + CI。

数据源(单一源,零新读链):
- decisions.jsonl 行 ``p26_prep_obs``(键面单一源 =
  ``telemetry.schema.P26_PREP_OBS_FIELDS``,当前 = node_type_next;
  语义见 DecisionTrace.p26_prep_obs 注——原始 token 不映射不猜,
  分桶映射归本脚本离线做);
- outcomes.jsonl 行结算三项遥测授权面(damage_base /
  damage_unfinished_progress / hp_after),join 键 (run_id, plane, round_num);
- 桶维来源:围栏内支出额 = decisions 行 ``sess_release_spent``
  (v3 实花面,授权围栏内全渠道);carry 装备数 = decisions 行
  ``state.deployed[].equips`` 合计;成型档 = ``engines_count``
  (outcome.board_before, 上场名单)——与 p15 冻结核 rung_source 同式。

诚实性纪律:实机 p26_prep_obs 自第二十五局起才落盘,当前样本不足——
桶 n<10 或节点型败面 n<30 时**逐桶/逐型诚实标 insufficient + 定向补样**,
不硬跑不硬估;总样本不足时结果标 status=insufficient。本脚本只产
标定报告,零拟合常数进策略代码,结论候用户裁。

复跑方式:
- ``uv run --env-file .env python tools/cw/proofs/p26/p26_calibrate.py``
  = 对 replay 转储实跑,产出 fit_results.json + REPORT.md;
- ``--selftest`` = 构造最小合成数据自验分桶/CI 计算,零外部数据依赖。
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from sr_od.application.currency_war.knowledge.cw_engine_facts import (
    engines_count,
)

REPO = Path(__file__).resolve().parents[4]
REPLAY_DIR = REPO / '.debug' / 'temp' / 'currency_war' / 'replay'
OUT_DIR = Path(__file__).resolve().parent

N_BOOT = 2000
SEED = 20260906

#: 质量门(P26 采集批申报口径):每桶 n≥10;L_node 败面样本 ≥30/节点型。
MIN_BUCKET_N = 10
MIN_LOSS_PER_NODE = 30

#: 围栏内支出额的分桶边界(分析用声明桶,非策略常数;候用户裁重划)。
SPEND_BIN_EDGES: tuple[int, ...] = (1, 6, 16, 31)
SPEND_BIN_LABELS: tuple[str, ...] = ('0', '1-5', '6-15', '16-30', '31+')

#: 下一节点 token 归一(战斗类才进 Δp/L_node 面;其余 token 计入 excluded,
#: 不猜语义)。battle 侧口径与 p15 NODE_NORM 同源收窄。
NODE_NORM = {
    '普通战斗': 'battle', 'battle': 'battle', '战斗': 'battle',
    '遭遇': 'encounter', 'encounter': 'encounter',
    'boss': 'boss', 'Boss': 'boss', '首领': 'boss',
}
BATTLE_CLASS = ('battle', 'encounter', 'boss')

#: L_node 分位带(条件败面伤害尾部;声明口径,非策略常数)。
QUANTILES: tuple[float, ...] = (0.50, 0.75, 0.90, 0.95)


def spend_bin(spend: int | None) -> str:
    """围栏内支出额 → 声明桶标签;None(旧行/缺面)= 'na' 诚实缺省。"""
    if spend is None:
        return 'na'
    for i, edge in enumerate(SPEND_BIN_EDGES):
        if spend < edge:
            return SPEND_BIN_LABELS[i]
    return SPEND_BIN_LABELS[-1]


def carry_equip_count(state: dict) -> int | None:
    """carry 装备数 = 战前上场名单装备合计;deployed 缺面 = None。"""
    dep = state.get('deployed')
    if not isinstance(dep, list):
        return None
    total = 0
    for d in dep:
        if isinstance(d, dict):
            eq = d.get('equips')
            if isinstance(eq, list):
                total += len(eq)
    return total


def extract(replay_dir: Path) -> tuple[list[dict], dict]:
    """抽语料:p26_prep_obs 备战帧 × 同 (run_id, plane, round_num) 结算行。"""
    outcomes: dict[tuple, dict] = {}
    n_out_rows = 0
    opath = replay_dir / 'outcomes.jsonl'
    if opath.exists():
        for line in opath.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            n_out_rows += 1
            outcomes[(r.get('run_id'), r.get('plane'),
                      r.get('round_num'))] = r
    rows: list[dict] = []
    n_dec_rows = 0
    n_with_obs = 0
    excluded_nt: dict[str, int] = defaultdict(int)
    dpath = replay_dir / 'decisions.jsonl'
    if dpath.exists():
        for line in dpath.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            n_dec_rows += 1
            obs = d.get('p26_prep_obs')
            if not isinstance(obs, dict):
                continue
            n_with_obs += 1
            nt_raw = str(obs.get('node_type_next') or '')
            nt = NODE_NORM.get(nt_raw)
            if nt is None:
                excluded_nt[nt_raw or '<empty>'] += 1
                continue
            o = outcomes.get((d.get('run_id'), d.get('plane'),
                              d.get('round_num')))
            state = d.get('state') or {}
            killed = (o or {}).get('killed')
            db = (o or {}).get('damage_base')
            du = (o or {}).get('damage_unfinished_progress')
            # 结算三项授权面:两分量齐 = 观测伤害;缺任一 = 删失显式可辨
            # (tooltip miss),不猜不补。
            dmg = (db + du) if isinstance(db, (int, float)) \
                and isinstance(du, (int, float)) else None
            dep_ids = [str(x.get('char_id', '')) for x in
                       (state.get('deployed') or []) if isinstance(x, dict)]
            rows.append({
                'run_id': d.get('run_id'),
                'plane': d.get('plane'),
                'round': d.get('round_num'),
                'node_type_next': nt,
                'spend_bin': spend_bin(
                    d.get('sess_release_spent')
                    if isinstance(d.get('sess_release_spent'), int) else None),
                'carry_equip': carry_equip_count(state),
                'rung': engines_count(
                    dict((o or {}).get('board_before') or {})
                    if o else {}, dep_ids),
                'has_outcome': o is not None,
                'killed': killed,
                'damage': dmg,
            })
    stats = {
        'n_decision_rows': n_dec_rows,
        'n_rows_with_p26_obs': n_with_obs,
        'n_outcome_rows': n_out_rows,
        'excluded_node_tokens': dict(sorted(excluded_nt.items())),
    }
    return rows, stats


def boot_ci(by_run: dict[str, list[float]], seed: int) -> list[float]:
    """按局(run)聚类 bootstrap 的 95% CI(百分位法;先例=p15 boot_ci)。"""
    rids = sorted(by_run)
    if len(rids) < 2:
        return []
    rng = random.Random(seed)
    stats: list[float] = []
    for _ in range(N_BOOT):
        sample = [by_run[rng.choice(rids)] for _ in rids]
        flat = [v for s in sample for v in s]
        stats.append(sum(flat) / len(flat))
    stats.sort()
    return [round(stats[int(0.025 * len(stats))], 4),
            round(stats[int(0.975 * len(stats)) - 1], 4)]


def loss_rate_table(rows: list[dict]) -> dict:
    """Δp_prep 条件表:桶键三维(支出桶/carry 装备数/成型档)× 节点型。

    每桶:n / n_loss / 败率 / 聚类 CI / 质量门标记(桶 n<10 = insufficient)。
    """
    cells: dict[tuple, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list))
    n_all: dict[tuple, int] = defaultdict(int)
    for r in rows:
        if not r['has_outcome'] or r['killed'] is None:
            continue
        k = (r['spend_bin'], r['carry_equip'], r['rung'],
             r['node_type_next'])
        n_all[k] += 1
        cells[k][str(r['run_id'])].append(0.0 if r['killed'] else 1.0)
    out = {}
    for k in sorted(n_all, key=str):
        by_run = cells[k]
        n = n_all[k]
        flat = [v for s in by_run.values() for v in s]
        rate = sum(flat) / len(flat)
        ci = boot_ci(by_run, SEED)
        out[str(k)] = {
            'n': n,
            'n_loss': int(sum(flat)),
            'loss_rate': round(rate, 4),
            'ci95': ci,
            'gate': 'ok' if n >= MIN_BUCKET_N else
                    f'insufficient: n<{MIN_BUCKET_N}/桶(定向补样)',
        }
    return out


def l_node_table(rows: list[dict]) -> dict:
    """L_node 分位带:按节点型,条件败面伤害分布尾部(分位 + 聚类 CI)。

    删失(结算两分量缺一)不入分位样本,只计 n_censored;节点型败面
    样本 < MIN_LOSS_PER_NODE 标定向补样。
    """
    obs: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list))
    cens: dict[str, int] = defaultdict(int)
    n_loss: dict[str, int] = defaultdict(int)
    for r in rows:
        if not r['has_outcome'] or r['killed'] is None or r['killed']:
            continue
        nt = r['node_type_next']
        n_loss[nt] += 1
        if r['damage'] is None:
            cens[nt] += 1
        else:
            obs[nt][str(r['run_id'])].append(float(r['damage']))
    out = {}
    for nt in sorted(n_loss):
        by_run = obs.get(nt, {})
        flat = sorted(v for s in by_run.values() for v in s)
        cell: dict = {
            'n_loss': n_loss[nt],
            'n_censored': cens.get(nt, 0),
        }
        if flat:
            cell['damage_observed'] = len(flat)
            cell['quantiles'] = {
                f'p{int(q * 100)}': round(
                    flat[min(int(q * len(flat)), len(flat) - 1)], 2)
                for q in QUANTILES
            }
            # 分位 CI:同聚类 bootstrap,对每个分位分别取百分位带
            rids = sorted(by_run)
            if len(rids) >= 2:
                rng = random.Random(SEED)
                boots: list[list[float]] = []
                for _ in range(N_BOOT):
                    sample = [by_run[rng.choice(rids)] for _ in rids]
                    s = sorted(v for g in sample for v in g)
                    boots.append([s[min(int(q * len(s)), len(s) - 1)]
                                  for q in QUANTILES])
                cell['quantile_ci95'] = {
                    f'p{int(q * 100)}': [
                        round(boots[int(0.025 * len(boots))][i], 2),
                        round(boots[int(0.975 * len(boots)) - 1][i], 2)]
                    for i, q in enumerate(QUANTILES)
                }
        cell['gate'] = ('ok' if n_loss[nt] >= MIN_LOSS_PER_NODE else
                        f'insufficient: 败面 n<{MIN_LOSS_PER_NODE}'
                        '/节点型(定向补样)')
        out[nt] = cell
    return out


def compute(rows: list[dict], src_stats: dict, source: str) -> dict:
    """汇总 fit_results 冻结核(p15 格式风格 + status/质量门口径)。"""
    joined = [r for r in rows if r['has_outcome']]
    res: dict = {
        'generated_at': datetime.now(UTC).isoformat(),
        'source': source,
        'schema_single_source':
            'telemetry.schema.P26_PREP_OBS_FIELDS (node_type_next)',
        'bucket_dims': {
            'spend': 'decisions.sess_release_spent → 声明桶 '
                     f'{SPEND_BIN_LABELS}(edges={list(SPEND_BIN_EDGES)},'
                     '分析桶非策略常数)',
            'carry_equip': 'decisions.state.deployed[].equips 合计',
            'rung': 'engines_count(outcome.board_before, deployed char_ids)'
                    ' — _settle_rung 同源式',
        },
        'join_key': '(run_id, plane, round_num)',
        'censoring_rule': '结算两分量(damage_base/damage_unfinished_progress)'
                          '缺一 = L_node 删失显式可辨,不入分位样本只计数',
        'bootstrap': f'run-cluster percentile, n={N_BOOT}, seed={SEED}',
        'quality_gate': {
            'bucket': f'n>={MIN_BUCKET_N}/桶',
            'l_node': f'败面 n>={MIN_LOSS_PER_NODE}/节点型',
        },
        **src_stats,
        'n_joined_rows': len(joined),
    }
    if len(joined) < MIN_BUCKET_N:
        res['status'] = ('insufficient: 实机 p26_prep_obs 样本不足'
                         f'(join 后 n={len(joined)} < {MIN_BUCKET_N}),'
                         '不硬跑;待采集批补样后重跑')
        res['delta_p_prep'] = {}
        res['l_node'] = {}
        return res
    res['status'] = 'partial: 已出表,逐桶/逐型 gate 见各 cell'
    res['delta_p_prep'] = loss_rate_table(joined)
    res['l_node'] = l_node_table(joined)
    return res


def write_report(res: dict, path: Path) -> None:
    """可读 REPORT.md(面向人,直白表述)。"""
    lines = ['# P26 参数标定报告(候用户裁;零拟合常数进策略代码)', '']
    lines.append(f'- 生成时间:{res["generated_at"]}')
    lines.append(f'- 数据源:{res["source"]}')
    lines.append(f'- 状态:**{res["status"]}**')
    lines.append(f"- decisions 行 {res['n_decision_rows']},其中带 "
                 f"p26_prep_obs {res['n_rows_with_p26_obs']} 行;"
                 f"outcomes 行 {res['n_outcome_rows']};join 后 "
                 f"{res['n_joined_rows']} 行")
    if res.get('excluded_node_tokens'):
        lines.append(f"- 非战斗类下一节点 token(不入表):"
                     f"{res['excluded_node_tokens']}")
    lines.append('')
    if res['delta_p_prep']:
        lines.append('## Δp_prep 条件表(桶键 = 支出桶/carry装备数/成型档/'
                     '下一节点型)')
        lines.append('')
        lines.append('| 桶 | n | 败数 | 败率 | CI95 | 门 |')
        lines.append('|---|---|---|---|---|---|')
        for k, v in res['delta_p_prep'].items():
            lines.append(f"| {k} | {v['n']} | {v['n_loss']} | "
                         f"{v['loss_rate']} | {v['ci95']} | {v['gate']} |")
        lines.append('')
    if res['l_node']:
        lines.append('## L_node 分位带(条件败面伤害,按下一节点型)')
        lines.append('')
        for nt, v in res['l_node'].items():
            lines.append(f"### {nt}:{v['gate']}")
            lines.append(f"- 败面 n={v['n_loss']}(删失 {v['n_censored']})")
            if 'quantiles' in v:
                lines.append(f"- 分位:{v['quantiles']}")
            if 'quantile_ci95' in v:
                lines.append(f"- 分位 CI95:{v['quantile_ci95']}")
            lines.append('')
    lines.append('## 结论使用边界')
    lines.append('')
    lines.append('- 本报告为纯标定产出;任何桶/分位进入策略代码前须经'
                 '用户裁与对抗审查,脚本自身不写任何策略常数。')
    lines.append('- 样本不足的桶/节点型只代表「当前无证据」,不代表'
                 '「无差异」;定向补样优先补 insufficient 高频桶。')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    rows, src_stats = extract(REPLAY_DIR)
    res = compute(rows, src_stats, str(REPLAY_DIR))
    (OUT_DIR / 'fit_results.json').write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
    write_report(res, OUT_DIR / 'REPORT.md')
    print(f"status: {res['status']}")
    print(f"decisions={src_stats['n_decision_rows']} "
          f"with_p26_obs={src_stats['n_rows_with_p26_obs']} "
          f"joined={res['n_joined_rows']}")
    print('产出: fit_results.json + REPORT.md (tools/cw/proofs/p26/)')
    return 0


def _selftest() -> int:
    """最小合成数据自验:分桶正确性 + CI 计算 + 质量门标记,零外部数据。"""
    import io
    import tempfile
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    assert spend_bin(0) == '0' and spend_bin(5) == '1-5' \
        and spend_bin(15) == '6-15' and spend_bin(30) == '16-30' \
        and spend_bin(99) == '31+' and spend_bin(None) == 'na'

    with tempfile.TemporaryDirectory() as td:
        rd = Path(td)
        dec: list[str] = []
        out: list[str] = []
        # 局 A:10 帧同桶(battle, 高败率);局 B:10 帧同桶(encounter 零败)
        for i in range(10):
            dec.append(json.dumps({
                'run_id': 'runA', 'plane': 1, 'round_num': i + 1,
                'sess_release_spent': 3, 'p26_prep_obs':
                    {'node_type_next': 'battle'},
                'state': {'deployed': [
                    {'char_id': 'x', 'equips': ['e1', 'e2']},
                    {'char_id': 'y', 'equips': []}]}}))
            out.append(json.dumps({
                'run_id': 'runA', 'plane': 1, 'round_num': i + 1,
                # 前 8 轮败(killed=False),后 2 轮胜
                'killed': i >= 8, 'damage_base': 10,
                'damage_unfinished_progress': 5,
                'board_before': {'仙舟': 2}}))
        for i in range(10):
            dec.append(json.dumps({
                'run_id': 'runB', 'plane': 1, 'round_num': i + 1,
                'sess_release_spent': None,
                'p26_prep_obs': {'node_type_next': 'encounter'},
                'state': {'deployed': []}}))
            out.append(json.dumps({
                'run_id': 'runB', 'plane': 1, 'round_num': i + 1,
                'killed': False, 'damage_base': None,
                'damage_unfinished_progress': None, 'board_before': {}}))
        # 非 battle 下一节点 + 无 obs 行:不入表
        dec.append(json.dumps({'run_id': 'runB', 'plane': 1,
                               'round_num': 99, 'sess_release_spent': 0,
                               'p26_prep_obs': {'node_type_next': '补给'},
                               'state': {}}))
        dec.append(json.dumps({'run_id': 'runB', 'plane': 1,
                               'round_num': 98, 'state': {}}))
        (rd / 'decisions.jsonl').write_text('\n'.join(dec), encoding='utf-8')
        (rd / 'outcomes.jsonl').write_text('\n'.join(out), encoding='utf-8')

        rows, stats = extract(rd)
        assert stats['n_rows_with_p26_obs'] == 21, stats
        assert stats['excluded_node_tokens'] == {'补给': 1}, stats
        assert len(rows) == 20  # 21 obs - 1 非战斗
        r0 = rows[0]
        assert r0['spend_bin'] == '1-5' and r0['carry_equip'] == 2 \
            and r0['node_type_next'] == 'battle', r0
        assert rows[10]['spend_bin'] == 'na'

        joined = [r for r in rows if r['has_outcome']]
        tbl = loss_rate_table(joined)
        k_battle = str(('1-5', 2, 0, 'battle'))
        assert k_battle in tbl, sorted(tbl)
        c = tbl[k_battle]
        assert c['n'] == 10 and c['n_loss'] == 8, c
        assert abs(c['loss_rate'] - 0.8) < 1e-9
        # n=10 恰达质量门 → ok(边界:门是 n<10 判 insufficient)
        assert c['gate'] == 'ok', c
        # 局内相关 → 单局全败(killed=False 全同局)→ 败率 1.0;
        # 单局一桶 CI 退化 [](聚类重抽 <2 局不估)
        k_enc = str(('na', 0, 0, 'encounter'))
        assert k_enc in tbl and tbl[k_enc]['loss_rate'] == 1.0
        assert tbl[k_enc]['n_loss'] == 10 and tbl[k_enc]['ci95'] == []

        ltab = l_node_table(joined)
        assert ltab['battle']['n_loss'] == 8
        assert ltab['battle']['damage_observed'] == 8
        assert ltab['battle']['quantiles']['p50'] == 15.0, ltab['battle']
        assert ltab['encounter']['n_censored'] == 10
        assert 'quantiles' not in ltab['encounter']  # 全删失不入分位
        assert ltab['encounter']['gate'].startswith('insufficient')

        res = compute(rows, stats, str(rd))
        assert res['status'].startswith('partial'), res['status']
        rep = Path(td) / 'REPORT.md'
        write_report(res, rep)
        assert 'insufficient' in rep.read_text(encoding='utf-8')
    print('selftest PASS: 分桶/CI/删失/质量门/报告 全部符合预期')
    return 0


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(_selftest())
    sys.exit(main())
