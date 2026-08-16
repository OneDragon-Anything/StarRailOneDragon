"""期望进度曲线 p(t) 编译器(ADR-0171 §6 documented;2026-08-16 轮15)。

**背景**:20 号审判层(ADR-0171)的「时间线掉队」通道需要期望侧基准 ——「健康线在节点 t
应长到哪」(plaza 三阶段 roster 的第五种用法;17 号成本曲线的对偶)。v0 编译器从
``PLAZA_CARRY_CLUSTERS`` 现有字段(按费用档与节奏 label)导出**检查点进度曲线**,供
``LineHypothesis.expected`` 灌入。

v0 语义:进度 = 板面成型度代理(等级轨迹归一)。节奏 label(5/6/7 级搜牌/速升 8/9)按
人类实证给了「何时到达哪个等级」;三阶段人口(Early 3.65→Final 9.31)给成形人数曲线。
编译产出:节点(0-26)→ 期望进度 ∈ [0,1](0=开局,1=完全成型),按节奏档分曲线。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_plaza_comps import PLAZA_CARRY_CLUSTERS

NODES_TOTAL: int = 27   # 3 位面 × 9 节点(与 cw_horizon 同源)

# 节奏档 → 检查点(节点, 期望等级)锚(从 plaza labels 语义:v0 手标锚点,
# J1 阴性组回放校准后由数据替换 —— 预注册纪律:锚错先改锚不改机制)
_TEMPO_ANCHORS: dict[str, list[tuple[int, int]]] = {
    '5级搜牌': [(2, 3), (5, 5), (8, 6), (14, 7), (20, 8), (26, 8)],
    '6级搜牌': [(2, 3), (5, 4), (8, 6), (13, 7), (19, 8), (26, 8)],
    '7级搜牌': [(2, 3), (5, 5), (8, 7), (14, 8), (20, 8), (26, 9)],
    '速升8级': [(2, 4), (5, 6), (8, 8), (14, 8), (20, 9), (26, 9)],
    '速升9级': [(2, 4), (5, 6), (8, 8), (13, 9), (20, 9), (26, 9)],
}

# 归一:等级 1→10 映射进度 0→1(v0 线性;Final 9.31 人口实证 ~0.92 处)
_LV_MIN, _LV_MAX = 1, 10


def _interp(anchors: list[tuple[int, int]], node: int) -> float:
    """锚点线性插值 → 节点处期望进度。"""
    if node <= anchors[0][0]:
        lo = anchors[0]
        return max(0.0, (lo[1] - _LV_MIN) / (_LV_MAX - _LV_MIN))
    if node >= anchors[-1][0]:
        hi = anchors[-1]
        return (hi[1] - _LV_MIN) / (_LV_MAX - _LV_MIN)
    for (n0, l0), (n1, l1) in zip(anchors, anchors[1:], strict=False):
        if n0 <= node <= n1:
            t = (node - n0) / max(n1 - n0, 1)
            lv = l0 + (l1 - l0) * t
            return (lv - _LV_MIN) / (_LV_MAX - _LV_MIN)
    return 0.0


def expected_curve(tempo: str) -> dict[int, float]:
    """节奏档 → {节点: 期望进度}(检查点粒度:每 2 节点)。"""
    anchors = _TEMPO_ANCHORS.get(tempo, _TEMPO_ANCHORS['7级搜牌'])
    return {n: round(_interp(anchors, n), 3) for n in range(0, NODES_TOTAL, 2)}


def dominant_tempo(carry: str) -> str | None:
    """carry 聚类 → 主流节奏档(labels argmax;n≥15 聚类才有统计意义)。"""
    best, best_n = None, 0
    for cl in PLAZA_CARRY_CLUSTERS:
        if cl.carry == carry and cl.n_posts >= 15:
            raw = cl.labels or ()
            items = raw.items() if isinstance(raw, dict) else raw   # tuple[(k,v)] 容错
            for tempo, n in items:
                if tempo in _TEMPO_ANCHORS and n > best_n:
                    best, best_n = tempo, n
    return best


def expected_curve_for_carry(carry: str) -> dict[int, float] | None:
    """carry → 期望曲线(主流节奏档;无统计意义的聚类 → None,预注册不灌)。"""
    tempo = dominant_tempo(carry)
    return expected_curve(tempo) if tempo else None
