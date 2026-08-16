"""伤害双账本 v0(19 号提案;ADR-0166;2026-08-16)。

**诊断(19 号)**:战斗结果的主干不是黑盒——己方输出**直接测**(结算屏总伤害,
``read_total_damage`` 已实现求和读数但被钉死 diagnostic;``RoundOutcome.damage_dealt``
字段早留好从未灌值)、敌方需求**机制算**(boss 血量 ≈ base × 1.052^难度,公式已建档;
超时扣血 = f(剩余进度) → 扣血量本身编码伤害进度);胜负判定是簿记不等式:AV 限内
我方总伤 ≥ 敌方总血预算 → 过。hp_delta 从「被学的标签」变「被推导的结果」。

**v0 落地**(纯逻辑层,读数接线/结算屏建档是 L1 门后续):
- ``enemy_budget(node_type, difficulty, base)``:敌方入账 E(node) = base × 1.052^d;
- ``record_battle(damage_dealt, won)`` + ``calibrate()``:**不等式括号法**——每战产生
  硬约束对(赢 ⇒ D ≥ E;超时 ⇒ D < E),base 的可行区间随样本收紧(非回归,十几战可定);
- ``gap(budget, throughput, av_rounds)``:对账缺口(预检/计价/分诊三用);缺口 × λ_hp
  (ADR-0161)折金 → fold vs 急救阈值由缺口算出;
- ``modifier_value(d_delta, d_current)``:难度修改器解析定价(银−4 ≈ 削 18% 敌血 = 白赚)。

与 02 号(未落地)的关系:主效应归账本,统计层只学词缀×comp 交互残差;与 15 号(敌情
定性)互补:一个管「怕什么」,一个管「要打多少」。「赢 ⇒ D≥E」天然是物理合约,可挂
13 号回溯审计(校准漂移报警)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

GROWTH_PER_DIFFICULTY: float = 1.052   # 每 +1 难度 +5.2% 血("每+8≈+50%"建档公式)

# 节点类型 base 先验(相对单位;校准收紧。P1 战斗 1.0 基准)
NODE_BASE_PRIOR: dict[str, float] = {
    'battle': 1.0, 'elite': 1.8, 'boss': 6.0, 'encounter': 1.2, 'reward': 0.0,
}


@dataclass
class BattleConstraint:
    """一战产生的不等式约束:won → D ≥ E(budget);lost(超时)→ D < E。"""
    damage: float
    budget_est: float
    won: bool


@dataclass
class DamageLedger:
    """伤害双账本:敌方预算(入账)+ 己方实测(出账)+ 不等式对账校准。"""

    base: dict[str, tuple[float, float]] = field(default_factory=lambda: dict(NODE_BASE_PRIOR))
    constraints: list[BattleConstraint] = field(default_factory=list)
    # 己方吞吐实测(出账):每 comp 族均值(plaza 份额先验冷启动,v0 单池)
    throughput_est: float = 0.0
    throughput_n: int = 0

    # --- 敌方入账 ---
    def enemy_budget(self, node_type: str, difficulty: int, base_scale: float = 1.0) -> float:
        prior = self.base.get(node_type)
        lo, hi = prior if isinstance(prior, tuple) else (prior or 1.0, prior or 1.0)
        mid = (lo + hi) / 2
        return mid * base_scale * (GROWTH_PER_DIFFICULTY ** difficulty)

    # --- 己方出账 ---
    def record_throughput(self, damage: float) -> None:
        """结算屏总伤害入账(实测;intentional_fold 局不入 —— 口径纪律)。"""
        n = self.throughput_n
        self.throughput_est = (self.throughput_est * n + damage) / (n + 1)
        self.throughput_n += 1

    # --- 对账回路 ---
    def record_battle(self, damage: float, won: bool, node_type: str,
                      difficulty: int, base_scale: float = 1.0) -> None:
        """一战入账:吞吐实测 + base 不等式约束(won ⇒ D ≥ E;超时 ⇒ D < E)。"""
        self.record_throughput(damage)
        est = self.enemy_budget(node_type, difficulty, base_scale)
        self.constraints.append(BattleConstraint(damage, est, won))
        self._tighten(node_type, difficulty, base_scale)

    def _tighten(self, node_type: str, difficulty: int, base_scale: float) -> None:
        """括号法收紧 base 区间:赢局 D → base 上界线索(D/[s·g^d] 为 base 下界样本);
        超时局 D → base 上界样本。区间宽度单调不增(取历史交)。"""
        g = GROWTH_PER_DIFFICULTY ** difficulty * base_scale
        lo, hi = self.base.get(node_type, (0.0, 10.0))
        for c in self.constraints:
            b_obs = c.damage / g
            if c.won:
                lo = max(lo, min(b_obs * 0.9, 10.0))     # 赢 ⇒ base ≤ ~b_obs(overkill 余量)
            else:
                hi = min(hi, b_obs * 1.1)                # 超时 ⇒ base > ~b_obs
        if lo > hi:   # 约束冲突(模型错/难度曲线错)→ 放宽到包络,L2 违反率会暴露
            lo, hi = min(lo, hi), max(lo, hi)
        self.base[node_type] = (lo, hi)

    # --- 对账输出(三用) ---
    def gap(self, node_type: str, difficulty: int, base_scale: float = 1.0) -> float:
        """缺口 = 预算 − 吞吐实测(负 = 白过/钱照省;正 = 打不动)。"""
        return self.enemy_budget(node_type, difficulty, base_scale) - self.throughput_est

    def predict_win(self, node_type: str, difficulty: int, base_scale: float = 1.0) -> bool:
        return self.gap(node_type, difficulty, base_scale) <= 0

    def modifier_value(self, d_delta: int, node_type: str = 'battle',
                       difficulty: int = 10, base_scale: float = 1.0) -> float:
        """难度修改器解析定价:ΔE = E×(1 − 1.052^Δd)/E(相对值;银−4 ≈ −18% 敌血)。"""
        e0 = self.enemy_budget(node_type, difficulty, base_scale)
        e1 = self.enemy_budget(node_type, difficulty + d_delta, base_scale)
        return (e1 - e0) / e0 if e0 else 0.0

    def diagnosis(self, damage_last: float, share_drop: float | None = None) -> str:
        """分诊:输出缺口型(伤害低)vs 有效输出衰减型(份额骤降 = 被机制针对/站位)。"""
        if share_drop is not None and share_drop < -0.2:
            return '衰减型(份额骤降:机制针对/站位,接阵型层与 matchup)'
        return '缺口型(伤害不足:fold vs 急救由缺口×λ_hp 计价)'
