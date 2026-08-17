"""预测台账层 v0(redesign 40 号;ADR-0178):前向预测显式登记 + 环境性记分 + 保真度分区。

**诊断(40 号)**:系统每回合产出前向预测(DP 期望轨迹/池信念面命中率/成本曲线/伤害预算),
但从未落盘、从未对答案 —— 全系统唯一未开采的免费校准数据(forecast scoring,天气预报百年方法论)。
telemetry 三路只记已发生事实;预测与实现值隔一行 join 就能算的残差从未被算。

**v0 落地**(纯函数,离线;40 号 §2 四件套的最小闭环):
- ``Prediction``/``Ledger``:ex-ante 预测登记(点值或区间;零新计算纪律——只登记引擎已算出的量);
- ``reconcile``:预测-实现对账 → 逐条误差(MAE/区间命中),按 (机制族 × 状态分区) 聚合;
- ``FidelityMap``:分区误差台账 + 覆盖计数(n=0 → dark 暗区,39 号探针靶单);
- ``residual_regression``:残差对状态协变量的 OLS 单变量回归(提名缺失耦合项,假设生成非定案)。

J0 自洽锚/J1 首份残差报告见测试与 ADR-0178;消费端门(24 防钻营/34 分区)为增量批次。
落盘第四路 predictions.jsonl 的登记接线挂 telemetry 批次(本层纯函数先行)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Prediction:
    """一条 ex-ante 前向预测(引擎决策时已算出的量;零新计算纪律)。"""

    run_id: str
    round_num: int
    key: str                 # 机制族×量:'income/node' | 'hp/drop' | 'shop/hit' | 'level/cost_path' | ...
    point: float | None = None    # 点预测(分布不可得时)
    lo: float | None = None       # 区间下界(19 号括号法同型)
    hi: float | None = None       # 区间上界
    region: str = ''              # 状态分区键(机制族×位面×等级档,默认派生)


@dataclass
class ScoredError:
    """单条对账结果。"""

    key: str                # 机制族×量
    region: str             # 状态分区
    run_id: str = ''
    round_num: int = 0
    actual: float = 0.0
    error: float = float('nan')   # actual − point;无点预测时 NaN(仅区间判定)
    in_interval: bool | None = None


def region_of(key: str, plane: int = 1, level: int = 1) -> str:
    """状态分区键派生(默认:机制族 × 位面 × 等级档 ≤5/6-8/≥9)。"""
    lv = 'early' if level <= 5 else ('mid' if level <= 8 else 'late')
    return f'{key}|p{plane}|{lv}'


def reconcile(predictions: list[Prediction], actuals: dict[tuple[str, int], dict[str, float]],
              *, plane_of: dict[tuple[str, int], int] | None = None,
              level_of: dict[tuple[str, int], int] | None = None) -> list[ScoredError]:
    """对账:actuals[(run_id, round_num)][key] → 实现值;逐预测记分。

    actuals 由调用方从 outcomes/decisions join 出(本层不读盘,保持纯函数);
    缺实现值的预测跳过(观测缺口,由调用方统计 dark)。
    """
    out: list[ScoredError] = []
    for p in predictions:
        act = actuals.get((p.run_id, p.round_num), {}).get(p.key)
        if act is None:
            continue
        plane = (plane_of or {}).get((p.run_id, p.round_num), 1)
        level = (level_of or {}).get((p.run_id, p.round_num), 1)
        in_iv: bool | None = None
        err = float('nan')
        if p.lo is not None and p.hi is not None:
            in_iv = p.lo <= act <= p.hi
        if p.point is not None:
            err = act - p.point
        out.append(ScoredError(p.key, region_of(p.key, plane, level),
                               p.run_id, p.round_num, act, err, in_iv))
    return out


@dataclass
class RegionStat:
    """单分区聚合统计(保真度分区的一格)。"""

    n: int = 0
    mae: float = 0.0                # 平均绝对误差(点预测;全区间时按 miss 距离)
    bias: float = 0.0               # 平均误差(带符号;系统偏移方向)
    interval_hit_rate: float | None = None   # 区间命中率(None=无区间预测)
    n_interval: int = 0


class FidelityMap:
    """保真度分区台账:(机制族 × 状态分区) → {误差指标, n};n=0 → dark(39 号靶单)。"""

    def __init__(self) -> None:
        self.stats: dict[str, RegionStat] = {}

    def update(self, scored: list[ScoredError]) -> None:
        for se in scored:
            st = self.stats.setdefault(se.region, RegionStat())
            if se.error == se.error:   # 非 NaN(点预测可比)
                st.n += 1
                st.mae += abs(se.error)
                st.bias += se.error
            if se.in_interval is not None:
                st.n_interval += 1
                hit = 1.0 if se.in_interval else 0.0
                prev = st.interval_hit_rate or 0.0
                k = st.n_interval
                st.interval_hit_rate = prev * (k - 1) / k + hit / k

    def finalize(self) -> dict[str, dict]:
        """聚合输出(报告形态)。"""
        out: dict[str, dict] = {}
        for region, st in self.stats.items():
            d: dict = {'n': st.n, 'n_interval': st.n_interval}
            if st.n:
                d['mae'] = round(st.mae / st.n, 3)
                d['bias'] = round(st.bias / st.n, 3)
            if st.interval_hit_rate is not None:
                d['interval_hit_rate'] = round(st.interval_hit_rate, 3)
            out[region] = d
        return out

    def dark_regions(self, expected: set[str]) -> list[str]:
        """暗区:应有覆盖但 n=0 的分区(探针靶单)。expected 由调用方按访达面给。"""
        return sorted(r for r in expected if self.stats.get(r, RegionStat()).n == 0)


def residual_regression(scored: list[ScoredError],
                        covariate: dict[tuple[str, int], float]) -> list[tuple[str, float]]:
    """残差 × 单协变量 OLS(40 号 §2.2):slope 显著非零 → 提名缺失耦合项。

    纯提名(假设生成)非定案 —— 定案走 23 号证据链。返回 (key, slope) 按 |slope| 降序;
    样本 < 8 或方差退化 → 空列表(欠功效如实)。
    """
    import math
    xs, ys, keys = [], [], []
    for se in scored:
        x = covariate.get((se.run_id, se.round_num))
        if x is None or se.error != se.error:
            continue
        xs.append(float(x))
        ys.append(se.error)
        keys.append(se.key)
    if len(xs) < 8:
        return []
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx < 1e-9:
        return []
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
    slope = sxy / sxx
    resid = [y - (my + slope * (x - mx)) for x, y in zip(xs, ys, strict=False)]
    s2 = sum(r * r for r in resid) / max(1, len(resid) - 2)
    se_slope = math.sqrt(s2 / sxx)
    # t 统计量(se≈0 = 完美线性拟合,t=inf 亦显著;sxx 退化已上游剔除)
    t = (slope / se_slope) if se_slope > 1e-300 else (float('inf') if slope != 0 else 0.0)
    if abs(t) < 2.0:
        return []
    by_key: dict[str, float] = {}
    for k in keys:
        by_key[k] = by_key.get(k, 0.0) + abs(slope)
    return sorted(by_key.items(), key=lambda kv: -kv[1])
