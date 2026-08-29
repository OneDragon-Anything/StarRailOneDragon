"""离线权重搜索器 v0(redesign 24 号;ADR-0194):CEM 闭环 + 防退化三件套。

**诊断(24 号)**:手调权重 = 人肉坐标下降(六代补丁互相打架是收敛慢的化石);几十维
耦合权重无闭式解、plaza 给不出联合最优、真局 05 结构上搜不动——这片地没人耕。

**v0 落地**(纯函数,离线;24 号 §2.2 最小闭环):
- ``WeightSpace``:权重向量空间(维度=name/当前值/先验中心/σ;硬边界:用户权威规则与
  23 号机制常数不进空间);
- ``cem_search``:交叉熵方法(初始化=手调先验中心;适应度=配对种子库存活率
  − L2 先验正则;精英重采样);防退化三件套=先验 L2 正则+域随机化(DR:适应度在
  环境参数分布上评估——v0 以种子族多样代理)+ 13 合约硬约束(挂消费批次);
- ``evaluate_weights``:策略工厂(w → policy 参数)在固定种子库上评估——CRN 配对压方差。

J1(测试·小规模):合成可提升空间(已知更优点)→ CEM 收敛方向正确;
J2(测试):注入 sim 偏差(胜率虚高陷阱)→ 无正则冠军虚高,带正则受界——护栏真在防。
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class WeightDim:
    """一维权重(先验 = 手调值中心 N(v, σ))。"""

    name: str
    prior: float
    sigma: float = 0.3
    lo: float = 0.0
    hi: float = 10.0


@dataclass
class WeightSpace:
    """权重空间(24 号 §2.1;敏感度门分波挂消费批次)。"""

    dims: tuple[WeightDim, ...]

    def prior_vector(self) -> list[float]:
        return [d.prior for d in self.dims]

    def clamp(self, xs: list[float]) -> list[float]:
        return [min(d.hi, max(d.lo, x)) for x, d in zip(xs, self.dims, strict=True)]


def _l2_penalty(xs: list[float], center: list[float]) -> float:
    return sum((x - c) ** 2 for x, c in zip(xs, center, strict=True))


def evaluate_weights(xs: list[float], fitness_fn, seed_bank: list[int],
                     *, l2_coeff: float = 0.0, center: list[float] | None = None) -> float:
    """CRN 配对评估:固定种子库上平均适应度 − L2 正则(域随机化由种子族多样性代理)。"""
    raw = sum(fitness_fn(xs, s) for s in seed_bank) / max(1, len(seed_bank))
    if l2_coeff > 0 and center is not None:
        raw -= l2_coeff * _l2_penalty(xs, center)
    return raw


def cem_search(space: WeightSpace, fitness_fn, *, seed_bank: list[int],
               n_pop: int = 16, n_elite: int = 4, n_gen: int = 8,
               l2_coeff: float = 0.05, rng: random.Random | None = None) -> dict:
    """CEM:初始化=先验中心 → 每代采样 n_pop、精英 n_elite 重拟合(均值+σ 收缩)。

    返回 {best, best_fitness, history};防退化三件套之三件中 L2 在适应度内、
    种子族=DR 代理、13 合约硬约束挂消费端(轨迹检查器接入点)。
    """
    rng = rng or random.Random(7)
    center = space.prior_vector()
    sigmas = [d.sigma for d in space.dims]
    best, best_fit = list(center), evaluate_weights(
        center, fitness_fn, seed_bank, l2_coeff=l2_coeff, center=center)
    history: list[dict] = []
    for _g in range(n_gen):
        pop = [space.clamp([rng.gauss(c, s) for c, s in zip(center, sigmas, strict=True)])
               for _ in range(n_pop)]
        pop.append(list(center))    # 保留当前中心(单调性锚:精英不劣于父代)
        fits = [evaluate_weights(p, fitness_fn, seed_bank, l2_coeff=l2_coeff, center=center)
                for p in pop]
        order = sorted(range(len(pop)), key=lambda i: -fits[i])
        if fits[order[0]] > best_fit:
            best, best_fit = list(pop[order[0]]), fits[order[0]]
        elite = [pop[i] for i in order[:n_elite]]
        k = len(elite)
        center = [sum(p[j] for p in elite) / k for j in range(len(space.dims))]
        sigmas = [max(0.02, 0.85 * s) for s in sigmas]   # 几何收缩
        history.append({'best_fit': round(best_fit, 4),
                        'center': [round(c, 3) for c in center]})
    return {'best': [round(x, 4) for x in best], 'best_fitness': round(best_fit, 4),
            'prior': space.prior_vector(), 'history': history}
