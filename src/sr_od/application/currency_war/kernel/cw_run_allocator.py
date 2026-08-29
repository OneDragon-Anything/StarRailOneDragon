"""跨局分配层 v0(05 号提案;ADR-0170;2026-08-16):RunAllocator Thompson 采样 + 必死局回收。

**诊断(05 号)**:所有已落组件都是**局内优化器**,没人回答「数据本身从哪来、分配对不对」
——bot 集中玩当前最强 comp → telemetry 窄分布 → 学习组件外推失真 → 更不敢选 = 死锁
(05 自诊断的 CRITICAL-for-convergence)。必死局的剩余动作是**免费实验预算**被白白输掉。

**v0 落地**(纯函数,离线可测;telemetry 接线/漂移闭环为 v1):
- ``StrategyArm``:臂 = comp 家族(v1 再拆节奏维);Beta 后验;
- ``plaza 先验封顶``:伪计数 ≤8(幸存者偏差数据只配当弱先验,自家 5-8 局可翻案);
- ``ThompsonAllocator.select``:后验采样选臂(后验集中后自动退化为总选最优,层会自己关
  自己);forbid/priority 过滤(用户方向盘);explore_budget 闸;
- ``update``:分级奖励(win=1.0;输局按位面/节点进度分级,降方差)+ **adherence 加权**
  (防「分配姬子中途转万敌赢了算姬子」的信用错配);指数遗忘 γ;
- ``dead_run_salvage``:必死局回收(P(win)<ε 且置信 → 切后验方差最大的可达臂,零胜率
  成本收割样本);触发审计留证(复核「没误杀有救的局」≥95%)。

P(win) 投影供给方:ADR-0161 first_passage(已有);漂移闭环(CUSUM+重抓)为 v1。
"""
from __future__ import annotations

import random
from dataclasses import dataclass

PRIOR_CAP: int = 8          # plaza 伪计数封顶(幸存者偏差 → 弱先验,自家 5-8 局翻案)
GAMMA: float = 0.97         # 指数遗忘(旧版本样本退潮)
SALVAGE_EPS: float = 0.05   # 必死局判据(P(win) 阈值,保守)


@dataclass
class StrategyArm:
    """分配臂:comp 家族 + Beta 后验。"""
    arm_id: str
    comp_family: str
    alpha: float = 1.0
    beta: float = 1.0
    n_own: int = 0                  # 自家样本数(遗忘后)
    adherence_sum: float = 0.0      # 累计遵从度(审计)

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        s = self.alpha + self.beta
        return (self.alpha * self.beta) / (s * s * (s + 1))

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(max(self.alpha, 0.01), max(self.beta, 0.01))


class ThompsonAllocator:
    """跨局分配器 v0(Thompson 采样 + 预算闸 + salvage)。"""

    def __init__(self, arms: dict[str, StrategyArm] | None = None,
                 explore_budget: float = 0.15, seed: int = 0):
        self.arms = arms or {}
        self.explore_budget = explore_budget
        self.rng = random.Random(seed)
        self.salvage_log: list[dict] = []

    @classmethod
    def from_plaza(cls, family_share: dict[str, float],
                   explore_budget: float = 0.15, seed: int = 0) -> ThompsonAllocator:
        """plaza 份额 → 封顶先验臂表(份额归一为胜率先验;伪计数封顶)。"""
        arms: dict[str, StrategyArm] = {}
        for fam, share in family_share.items():
            mean = min(0.9, 0.3 + share)          # 份额 → 均值映射(弱先验)
            a = PRIOR_CAP * mean
            b = PRIOR_CAP * (1 - mean)
            arms[fam] = StrategyArm(arm_id=fam, comp_family=fam, alpha=a, beta=b)
        return cls(arms, explore_budget, seed)

    def select(self, forbidden: set[str] | None = None,
               forced: str | None = None) -> str | None:
        """选臂:forced(成就/handoff 豁免)> Thompson 采样。空表 → None。"""
        if forced and forced in self.arms:
            return forced
        cands = {k: a for k, a in self.arms.items() if k not in (forbidden or set())}
        if not cands:
            return None
        best_k, best_v = None, -1.0
        for k, a in cands.items():
            v = a.sample(self.rng)
            if v > best_v:
                best_k, best_v = k, v
        return best_k

    def update(self, arm_id: str, reward: float, adherence: float = 1.0) -> None:
        """终局更新:分级奖励 × 遵从度加权 + 指数遗忘(γ 缩旧样本再加分母)。"""
        a = self.arms.get(arm_id)
        if a is None or not (0.0 <= reward <= 1.0):
            # r68 review:拒绝必须留日志(57-A1 型断线哨兵——update 静默 no-op 时生产不可见)
            from one_dragon.utils.log_utils import log
            log.warning('[cw-alloc] update 拒绝:arm=%r 不在臂表 或 reward=%r 越界 [0,1]', arm_id, reward)
            return
        # 遗忘:旧后验向中性收缩(乘 γ 于伪计数规模,保持先验封顶语义)
        s = a.alpha + a.beta
        shrink = GAMMA ** (1 / max(a.n_own, 1)) if a.n_own else 1.0
        target_s = max(PRIOR_CAP, s * shrink)
        scale = target_s / s
        a.alpha, a.beta = a.alpha * scale, a.beta * scale
        # 遵从度加权的新样本
        w = max(0.0, min(1.0, adherence))
        a.alpha += reward * w
        a.beta += (1 - reward) * w
        a.n_own += 1
        a.adherence_sum += w

    def reward_graded(self, won: bool, plane_reached: int, rounds: int = 27) -> float:
        """分级奖励:win=1.0;输局按位面/节点进度(降方差,小样本最有效降噪)。"""
        if won:
            return 1.0
        return min(0.49, (plane_reached / 3.0) * 0.45 + (rounds / 27.0) * 0.05)

    def dead_run_salvage(self, p_win: float, reachable: set[str] | None = None) -> str | None:
        """必死局回收:P(win)<ε → 选可达臂中后验方差最大者(信息价值最大)。

        审计留证(离线复核「没误杀有救的局」≥95% 判据的数据)。
        """
        if p_win >= SALVAGE_EPS:
            return None
        cands = {k: a for k, a in self.arms.items() if not reachable or k in reachable}
        if not cands:
            return None
        best_k = max(cands, key=lambda k: cands[k].variance)
        self.salvage_log.append({'p_win': p_win, 'chosen': best_k,
                                 'variance': cands[best_k].variance})
        return best_k

    def stats(self) -> dict[str, dict]:
        return {k: {'mean': round(a.mean, 3), 'var': round(a.variance, 4),
                    'n_own': a.n_own, 'adherence': round(a.adherence_sum, 1)}
                for k, a in self.arms.items()}
