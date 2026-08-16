"""信念层 v0(04 号提案;ADR-0163;2026-08-16):BeliefStore 字段级信念。

**诊断(04 号)**:决策消费的是「OCR 点估计 + 读不到拍安全默认」——M19 hp=100 毒化(读不
到落默认,时间线 100↔真值震荡,复盘误判「P1 零损」)、gold 默认 0(白白扔掉跟踪层明明
知道的「上回合 40 金其间只花 2」)、dead-reckoning 漂 18 回合才暴露。三个提案各自打观察
噪声补丁(01 ±1 容错/02 hp_conf<0.7 剔除/03 保守先验)= 同一问题的三份局部方案。

**v0 落地**(提案 §2.1 核心,BeliefStore 六字段先行中的 3 个高价值字段):
- ``FieldBelief``:支撑集分布(粗桶)+ 证据链(source/value/conf/ts)+ 最后确证时间;
- 更新 = 廉价贝叶斯(观测似然 × 跟踪先验)+ 规则硬约束(sanity bounds → 支撑集截断);
- **读不到 ≠ 证据**:OCR 失败不产生证据,先验原样保留(M19 类毒化在此表示下不可表达);
- 时间衰减:未确证回合数 ↑ → 方差 ↑(漂移表现 为置信衰减,自然触发重确证);
- ``mode_projection()``:GameState 众数投影(消费端零改;提案兼容层)。

与 obs_conflict(ADR-0154 族)的分工:obs_conflict 管「冲突时保旧还是采新」的仲裁与留证;
本层管「值的分布表示」——仲裁是分布更新的一次特例。纯函数 + 离线可测。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Evidence:
    """一条观测证据(带出处与画面态)。"""
    source: str        # 'ocr' | 'sift' | 'track' | 'rule' | 'prior' | 'settlement'
    value: float
    conf: float        # 0..1(可靠性;§2.2 可靠性表 refine,初值手填)
    ts: str = ''
    screen: str = ''   # 画面态(可观测性矩阵的键)


@dataclass
class FieldBelief:
    """单字段信念:粗桶直方图 + 证据链 + 确证时间。字段独立(规模红线,拒绝联合分布)。"""
    name: str
    lo: float                       # 支撑集下界(sanity bound 硬截断)
    hi: float
    buckets: list[float] = field(default_factory=list)   # 桶概率(均分支撑集)
    evidence: list[Evidence] = field(default_factory=list)
    rounds_since_confirm: int = 0
    mode: float = 0.0               # 众数投影缓存

    N_BUCKETS: int = 21             # 类属性默认(dataclass field default 用 init=False 方式)

    def __post_init__(self) -> None:
        if not self.buckets:
            n = type(self).N_BUCKETS
            self.buckets = [1.0 / n] * n

    # --- 内部:值 ↔ 桶 ---
    def _bucket_idx(self, v: float) -> int:
        w = (self.hi - self.lo) / len(self.buckets)
        return min(len(self.buckets) - 1, max(0, int((v - self.lo) / w)))

    def _bucket_center(self, i: int) -> float:
        w = (self.hi - self.lo) / len(self.buckets)
        return self.lo + (i + 0.5) * w

    # --- 更新 ---
    def observe(self, ev: Evidence) -> None:
        """观测更新:似然 = 以观测值为中心的高斯(σ ∝ 支撑集宽 × (1-conf));后验归一。"""
        sigma = max(1e-6, (self.hi - self.lo) * 0.5 * max(0.02, 1.0 - ev.conf))
        new = [0.0] * len(self.buckets)
        for i in range(len(self.buckets)):
            c = self._bucket_center(i)
            new[i] = self.buckets[i] * math.exp(-0.5 * ((c - ev.value) / sigma) ** 2)
        s = sum(new)
        if s > 1e-12:
            self.buckets = [x / s for x in new]
        self.evidence.append(ev)
        if ev.conf >= 0.7:
            self.rounds_since_confirm = 0
        self._refresh_mode()

    def track_transition(self, delta: float, w: float = 0.9) -> None:
        """跟踪转移(过程模型):值平移 delta + 平滑(不确定性微增)。
        例:gold = 上回合 40 − 刷新 2 → 平移 −2;读不到时这就是唯一的推断来源。"""
        shift = int(round(delta / ((self.hi - self.lo) / len(self.buckets))))
        n = len(self.buckets)
        new = [0.0] * n
        for i, p in enumerate(self.buckets):
            j = min(n - 1, max(0, i + shift))
            new[j] += p * w
            # 平滑:小概率扩散到邻桶(过程噪声)
            for dj in (-1, 1):
                k = min(n - 1, max(0, j + dj))
                new[k] += p * (1 - w) / 2
        self.buckets = new
        self.rounds_since_confirm += 1
        self._refresh_mode()

    def decay(self) -> None:
        """回合衰减(无观测时):向均匀漂一点 + 未确证计数 +1(方差 ↑ 的廉价近似)。"""
        n = len(self.buckets)
        eps = 0.02 * min(self.rounds_since_confirm, 10)
        self.buckets = [(1 - eps) * p + eps / n for p in self.buckets]
        self.rounds_since_confirm += 1
        self._refresh_mode()

    # --- 消费 ---
    def _refresh_mode(self) -> None:
        self.mode = self._bucket_center(max(range(len(self.buckets)), key=lambda i: self.buckets[i]))

    def mode_value(self) -> float:
        return self.mode

    def percentile(self, q: float) -> float:
        """分位(悲观/乐观消费:hp 低置信取悲观分位,gold 取乐观保守值)。"""
        acc = 0.0
        for i, p in enumerate(self.buckets):
            acc += p
            if acc >= q:
                return self._bucket_center(i)
        return self._bucket_center(len(self.buckets) - 1)

    def confidence(self) -> float:
        """众数桶概率(粗置信;校准监控 refine 后为可验证概率)。"""
        return max(self.buckets)

    def credible_interval(self, mass: float = 0.9) -> tuple[float, float]:
        """可信区间(不可逆门的 required certainty 检验用)。"""
        order = sorted(range(len(self.buckets)), key=lambda i: -self.buckets[i])
        acc = 0.0
        idx = []
        for i in order:
            acc += self.buckets[i]
            idx.append(i)
            if acc >= mass:
                break
        lo = self._bucket_center(min(idx))
        hi = self._bucket_center(max(idx))
        return (lo, hi)


def make_gold_belief(initial: float = 20.0) -> FieldBelief:
    return FieldBelief('gold', 0.0, 110.0)


def make_hp_belief(initial: float = 100.0) -> FieldBelief:
    return FieldBelief('hp', 0.0, 100.0)


def make_level_belief(initial: int = 1) -> FieldBelief:
    return FieldBelief('level', 1.0, 10.0)
