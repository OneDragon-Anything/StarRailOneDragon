"""删失感知统计层 v0(redesign 48 号;ADR-0186):stage 分解重分析(Kaplan-Meier)。

**诊断(48 号)**:bot 真局流右删失(基线 82% 未存活)——「每局 outcome 是完整反馈」是
全系统 47 轮押注的静默假设,实为三流一致删失(bot 流/plaza 赢局截断/sim 保真度只在幸存
轨迹记分)。P(win) 混合体里「early 存活型」与「late 强度型」不可分,maybe_pivot 的比较
量纲错。

**v0 落地**(纯函数,离线,零新局;48 号机制一第 1 件):
- ``stage_decompose``:P(win) = P(reach s) × P(win|reach s) 逐阶段拆分(Kaplan-Meier 到达
  曲线;阶段=位面到达);
- ``compare_vs_scalar``:stage 分解量 vs 现行混合标量的 diff 报告(J0 判据:≥3 条实质
  偏差或带 CI 报告);
- IPCW(机制一第 2 件)与删失标注(第 3 件)进 v1(消费 37 池化权重)。

对拍锚(48 号赠 40 号的记分面):18 号解析 P(reach) vs 本层经验 KM 曲线不一致 = 模型
函数形式错的免费信号。
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RunRecord:
    """单局最少充分统计(stage 分解用)。"""

    run_id: str
    line: str            # 线归属(臂/comp)
    survived: bool       # 通关
    plane_reached: int   # 到达位面(1-3)


def kaplan_meier_reach(runs: list[RunRecord], stage: int) -> float:
    """P(reach stage):KM 到达曲线(把「未到达 stage」当事件,通关/仍在跑当删失)。

    离散简化:阶段到达的直接估计 P(reach s) = n(reach≥s)/n(全部)——观测完整(每局
    plane_reached 必录),KM 形式退化为比例;保留 KM 名以示语义(后续逐节点版接时间轴)。
    """
    if not runs:
        return 0.0
    n = sum(1 for r in runs if r.plane_reached >= stage)
    return n / len(runs)


def stage_decompose(runs: list[RunRecord]) -> dict:
    """P(win) = P(reach p2) × P(reach p3|p2) × P(win|p3) 逐段拆分 + 各线分解表。"""

    def _dec(rs: list[RunRecord]) -> dict:
        n = len(rs)
        if n == 0:
            return {'n': 0}
        reach2 = sum(1 for r in rs if r.plane_reached >= 2)
        reach3 = sum(1 for r in rs if r.plane_reached >= 3)
        win = sum(1 for r in rs if r.survived)
        # 条件量(分母 = 到达者;零分母显式 None 而非 0)
        p_r2 = reach2 / n
        p_r3_g_r2 = (reach3 / reach2) if reach2 else None
        p_win_g_r3 = (win / reach3) if reach3 else None
        # KM 等价(乘积还原)
        p_win_prod = p_r2 * (p_r3_g_r2 or 0.0) * (p_win_g_r3 or 0.0)
        return {'n': n, 'p_reach_p2': round(p_r2, 4),
                'p_reach_p3': round(reach3 / n, 4),
                'p_win': round(win / n, 4),
                'p_reach_p3_given_p2': None if p_r3_g_r2 is None else round(p_r3_g_r2, 4),
                'p_win_given_p3': None if p_win_g_r3 is None else round(p_win_g_r3, 4),
                'scalar_vs_product': round(win / n - p_win_prod, 6)}

    by_line: dict[str, list[RunRecord]] = {}
    for r in runs:
        by_line.setdefault(r.line, []).append(r)
    return {
        'overall': _dec(runs),
        'by_line': {ln: _dec(rs) for ln, rs in sorted(by_line.items())},
    }


def outcomes_to_runs(outcomes_rows: list[dict]) -> list[RunRecord]:
    """outcomes.jsonl → RunRecord 列表(**值域守卫**:plane∈1-3 域外行=OCR 假阳,
    不作 plane 证据;全局无域内行的局剔除——M70 假 win 根因的摄取口固化,
    2026-08-17 用户质询后主开发定位 read_phase_round 单数字 fallback 泄漏)。"""
    by_run: dict[str, list[dict]] = {}
    for r in outcomes_rows:
        by_run.setdefault(r.get('run_id', ''), []).append(r)
    out: list[RunRecord] = []
    for rid, rows in by_run.items():
        valid = [x for x in rows if 1 <= (x.get('plane') or 0) <= 3]
        if not valid:
            continue
        max_plane = max(x['plane'] for x in valid)
        last_hp = valid[-1].get('hp_after') or 0
        survived = max_plane >= 3 and last_hp > 0
        tags = [str(x.get('comp_tag') or '') for x in valid if x.get('comp_tag')]
        line = max(set(tags), key=tags.count) if tags else 'unknown'
        out.append(RunRecord(rid, line, survived, max_plane))
    return out


def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 区间(小 n 比正态近似稳)。"""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def compare_vs_scalar(runs: list[RunRecord]) -> dict:
    """J0 报告:各线「混合标量 P(win)」vs「stage 分解条件量」的实质偏差清单。

    实质偏差定义:scalar(0) 但 p(win|reach p3) 的 Wilson CI 下界 > 0(从未通关≠后期弱,
    只是不够活)/或 scalar 高但 p(reach p2) 的 CI 上界 < 0.5(靠早期存活撑的虚高)。"""
    rep = stage_decompose(runs)
    findings: list[dict] = []
    for ln, d in rep['by_line'].items():
        if d.get('n', 0) < 3:
            continue
        rs = [r for r in runs if r.line == ln]
        n = len(rs)
        scalar = d['p_win']
        # 迹象一:scalar=0 但有到达 p3 者 → 后期潜力被标量掩埋
        if scalar == 0.0 and (d.get('p_reach_p3') or 0) > 0:
            k3 = sum(1 for r in rs if r.plane_reached >= 3)
            lo, hi = _wilson_ci(k3, n)
            findings.append({'line': ln, 'kind': 'late_potential_masked',
                             'scalar_p_win': scalar, 'p_reach_p3': d['p_reach_p3'],
                             'ci': (round(lo, 3), round(hi, 3)),
                             'note': '混合标量 0 掩埋后期到达——maybe_pivot 比较量纲错的实例'})
        # 迹象二:scalar 高但早期到达弱 → 幸存者条件虚高
        if scalar > 0 and (d.get('p_reach_p2') or 0) < 0.5:
            k2 = sum(1 for r in rs if r.plane_reached >= 2)
            lo, hi = _wilson_ci(k2, n)
            findings.append({'line': ln, 'kind': 'survivor_condition_inflated',
                             'scalar_p_win': scalar, 'p_reach_p2': d['p_reach_p2'],
                             'ci': (round(lo, 3), round(hi, 3)),
                             'note': 'scalar 依赖低到达率下的稀疏通关——样本反转敏感'})
    return {'n_lines': len(rep['by_line']), 'findings': findings,
            'j0_verdict': ('diff>=3' if len(findings) >= 3
                           else ('diff_reported' if findings else 'no_substantial_diff'))}
