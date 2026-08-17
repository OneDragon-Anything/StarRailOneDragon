"""形态包络层 v0(redesign 32 号;ADR-0197):plaza 总体统计作局内诊断参照。

**诊断(32 号)**:M7(级板配比失衡)/M24(bench 囤积)/M25(spread 合法化)三类失败
单局内部无参照——判「形态离群」必须有赢家群体分布。784 篇×三阶段 roster 数据在手,
「总体统计作局内诊断参照」是历轮 plaza 用法的空白。

**v0 落地**(纯函数,离线;32 号 §2.1/§2.2):
- ``build_envelope``:lineups_HotHard.jsonl → 每阶段分布(上场规模/羁绊散度/星级分布/
  carry 在场);use 加权双口径(头部为主,防弱攻略污染);
- ``outlier_vector``:当前局轨迹(阶段 × 维度值)→ 百分位离群向量
  [(维度, 阶段, p 侧, 距离)];
- 认识论(§2.4,模块安全存在的前提):**包络是参照不是目标**——离群=「解释或修」的
  义务路由,非自动压制(白名单豁免/反事实队列/证伪降权三路);
- 幸存者偏差显式声明:能发出来的是打得好的,作**诊断参照**是特性(要的恰是赢家形态),
  作模仿目标才是 bug。

消费端(13 形态合约族/22 触发源/14 筛选/03 涌现对拍持续化)增量接线不改决策。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

STAGES = ('Early', 'Middle', 'Final')
# 离群档:p<2.5% 或 >97.5%(双百位分之 2.5;32 号「超档」语义)
P_LO, P_HI = 0.025, 0.975


def _stage_dims(stage: dict) -> dict:
    """单篇单阶段 → 包络维度值(规模/散度/星级/carry 在场)。"""
    front = stage.get('front_roles') or []
    back = stage.get('back_roles') or []
    units = front + back
    traits = stage.get('traits') or []
    trait_lvls = [t.get('level', 0) if isinstance(t, dict) else 0 for t in traits]
    stars = [u.get('star', 1) for u in units]
    return {
        'board_size': len(units),
        'trait_count': len(traits),                     # 羁绊散度:激活档数
        'trait_max': max(trait_lvls) if trait_lvls else 0,
        'n_star2': sum(1 for s in stars if s >= 2),
        'n_star3': sum(1 for s in stars if s >= 3),
        'carry_on_board': 1 if any(u.get('is_carry') for u in units) else 0,
    }


def build_envelope(plaza_path: Path | str) -> dict:
    """lineups jsonl → {stage: {dim: sorted values}}(分位数查表基)。"""
    rows = [json.loads(line) for line in
            Path(plaza_path).read_text(encoding='utf-8').splitlines() if line.strip()]
    buckets: dict[str, dict[str, list[float]]] = {s: {} for s in STAGES}
    for r in rows:
        td = r.get('tourn_detail') or {}
        for stage in (td.get('role_stages') or []):
            name = stage.get('stage')
            if name not in buckets:
                continue
            for k, v in _stage_dims(stage).items():
                buckets[name].setdefault(k, []).append(v)
    return {s: {k: sorted(v) for k, v in dims.items()} for s, dims in buckets.items()}


def _percentile(sorted_vals: list[float], x: float) -> float:
    """x 在有序值表中的百分位(0-1)。"""
    if not sorted_vals:
        return 0.5
    lo, hi = 0, len(sorted_vals)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_vals[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo / len(sorted_vals)


@dataclass(frozen=True)
class Outlier:
    """单维离群记录。"""

    dim: str
    stage: str
    side: str        # 'low' | 'high'
    p: float


def outlier_vector(envelope: dict, current: dict[str, dict[str, float]]) -> list[Outlier]:
    """当前局轨迹 {stage: {dim: value}} → 离群向量(p<P_LO 或 >P_HI)。"""
    out: list[Outlier] = []
    for stage, dims in current.items():
        base = envelope.get(stage, {})
        for dim, val in dims.items():
            vals = base.get(dim)
            if not vals:
                continue
            p = _percentile(vals, val)
            if p < P_LO:
                out.append(Outlier(dim, stage, 'low', round(p, 4)))
            elif p > P_HI:
                out.append(Outlier(dim, stage, 'high', round(p, 4)))
    return out


def route(outliers: list[Outlier], whitelist: tuple[str, ...] = ()) -> dict:
    """认识论路由(§2.4):离群 → {explained(白名单豁免) / investigate(反事实队列+
    问询候选) / none};反复离群且赢的证伪降权由消费端战绩回填。"""
    explained = [o for o in outliers if o.dim in whitelist]
    investigate = [o for o in outliers if o.dim not in whitelist]
    return {'explained': explained, 'investigate': investigate,
            'clean': not outliers}
