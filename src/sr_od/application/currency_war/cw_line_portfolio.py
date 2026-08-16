"""线组合管理器 v0(21 号提案;ADR-0172;2026-08-16)。

**诊断(21 号)**:目标生命周期两半,后半(commit 后审判)已被 20 号收编,前半(commit 前
候选管理)仍是手调族:optionality_score 加分 + α(t) 时间曲线 + top-N 惯例 + 0.4 阈值 +
硬绑表 ×1.5——同一物种五种手工近似。四种输法实证:错线 commit(boss 日程只是评分项不构成
否决)/被动等待(池枯竭要等 drought 5 轮)/pivot 无活口(optionality 只加分不构成持有规则)/
版本脆性。

**v0 落地**(core 纯函数;消费端切流与事件统一入口为后续):
- ``Line``:候选线(core_assets + 进出场成本 + 后验 log-odds);
- 五路证据一套更新(``update``):开局 boss 先验(15)/拾取冲击/池似然(16+20)/战况(19)/
  时间线(20)——数学与 20 号同源(对数累加),但从 t=0 对**全部线**跑;
- ``hold_value``:持有价值 H(u) = Σ w_l·V_l(u) + 共享红利 − 容量成本(买入的容量背包边际
  ——「牺牲哪条线的期权」静态估值表达不了);
- ``concentration_gate``:集中触发三条件(后验分离/判别日程耗尽/容量成本>组合增益),
  门限由 17 成本 × 18 姿态定价不拍常数;**交棒协议**:集中 = 注册进 20 号
  HypothesisRegistry 预注册,本层此后静默——零双重管理。

**spread 防线**(最大风险的缓解写进设计):板面/储备严格分离——板面永远下当前最优阵
(不动),组合只活在 bench 与买入侧;证据不判别的局超时强制集中到先验最优(=现状行为,
损失封顶在持有成本)。
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Line:
    """一条候选线:终局方向假设 + 后验(log-odds 空间,0=中性)。"""
    line_id: str
    core_assets: tuple[str, ...] = ()          # 核心单位/装备(共享红利判据)
    entry_cost: float = 0.0                    # 17 formation_cost(进)
    exit_cost: float = 0.0                     # 重入 + 装备沉没(出)
    log_odds: float = 0.0                      # 后验 log(P(线最优)/P(非))
    discriminators_left: int = 3               # 剩余判别事件数(boss 揭示/棱彩/池变化)

    @property
    def posterior(self) -> float:
        """P(线最优) ∈ (0,1)(softmax 由 Portfolio 归一,单线这里是相对量)。"""
        return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, self.log_odds))))

    def shock(self, delta: float) -> None:
        """似然冲击(对数累加;依赖度×幅度)。"""
        self.log_odds = max(-20.0, min(20.0, self.log_odds + delta))


class LinePortfolio:
    """线组合管理器:t=0 起全候选线滚动更新 + 容量配置 + 集中门。"""

    def __init__(self, lines: list[Line], capacity: int = 9,
                 hold_cost_per_slot: float = 0.15):
        self.lines = {ln.line_id: ln for ln in lines}
        self.capacity = capacity                 # bench 槽(buy 持有的硬约束)
        self.hold_cost = hold_cost_per_slot
        self.concentrated: str | None = None     # 集中后本层静默(交棒 20 号)

    # --- 五路证据(统一更新入口) ---
    def boss_prior(self, matchup_scores: dict[str, float]) -> None:
        """开局 boss 日程(15):matchup 分 → 先验冲击(克=压,利=抬;开局一次性)。"""
        for lid, s in matchup_scores.items():
            if lid in self.lines:
                self.lines[lid].shock((s - 0.5) * 4.0)   # 0.5 中性;满分 ±2 log-odds

    def pickup_shock(self, asset: str, dependency: dict[str, float]) -> None:
        """棱彩/环境/巨星拾取:依赖该 asset 的线上跳,无关下压(硬绑表=依赖度 1 特例)。"""
        mean_dep = sum(dependency.values()) / max(len(dependency), 1)
        for lid, dep in dependency.items():
            if lid in self.lines:
                self.lines[lid].shock((dep - mean_dep) * 3.0)

    def pool_feasibility(self, lrs: dict[str, float]) -> None:
        """池似然(16+20):LR>1(池枯证据)→ 压线(线性映射 log-odds)。"""
        for lid, lr in lrs.items():
            if lid in self.lines:
                self.lines[lid].shock(-math.log(max(lr, 1e-6)))

    def battle_evidence(self, gaps: dict[str, float], scale: float = 0.5) -> None:
        """战况(19):该线预期下缺口为正(打不动)→ 压;为负 → 抬。"""
        for lid, g in gaps.items():
            if lid in self.lines:
                self.lines[lid].shock(-g * scale)

    def discriminators_consumed(self, n: int = 1) -> None:
        """判别日程推进(事件发生数);耗尽 → 集中门条件之一满足。"""
        for ln in self.lines.values():
            ln.discriminators_left = max(0, ln.discriminators_left - n)

    # --- 持有价值与容量 ---
    def hold_value(self, unit: str, unit_line_values: dict[str, float]) -> float:
        """H(u) = Σ w_l·V_l(u) + 共享红利 − 容量占用成本。

        共享红利 = 服务多线的期权(char_routes 语义:v0 用「≥2 线非零值」判据);
        容量成本 = hold_cost × 拥挤度(bench 满时边际成本高 —— 牺牲哪条线的期权)。
        """
        w = self.normalized_weights()
        base = sum(w.get(lid, 0.0) * v for lid, v in unit_line_values.items())
        served = sum(1 for v in unit_line_values.values() if v > 0)
        sharing = 0.2 if served >= 2 else 0.0
        crowding = 1.0 if self.capacity <= 2 else 0.5   # 容量逼紧 → 持有更贵
        return base + sharing - self.hold_cost * crowding

    def normalized_weights(self) -> dict[str, float]:
        """后验 softmax 归一(线间相对权重;集中判据的输入)。"""
        los = {lid: ln.log_odds for lid, ln in self.lines.items()}
        m = max(los.values()) if los else 0.0
        exps = {lid: math.exp(v - m) for lid, v in los.items()}
        s = sum(exps.values()) or 1.0
        return {lid: e / s for lid, e in exps.items()}

    # --- 集中门与交棒 ---
    def concentration_gate(self, *, sep_threshold: float = 0.6,
                           max_hold_cost: float = 1.0) -> tuple[bool, str]:
        """集中触发三条件(门限由 17 成本×18 姿态定价,此处收外部参数):
        ① 后验分离:max 权重 ≥ sep_threshold;
        ② 判别日程耗尽:全部线 discriminators_left == 0;
        ③ 容量成本 > 组合期望增益。
        触发 → 集中到 argmax 线并交棒 20 号(concentrated 置位,本层静默)。
        """
        if self.concentrated:
            return True, f'已集中({self.concentrated}),本层静默(交棒 20 号审判)'
        w = self.normalized_weights()
        if not w:
            return False, '无线'
        best = max(w, key=w.get)
        if w[best] >= sep_threshold:
            self.concentrated = best
            return True, f'后验分离:{best} 权重 {w[best]:.2f} ≥ {sep_threshold}'
        if all(ln.discriminators_left == 0 for ln in self.lines.values()):
            self.concentrated = best
            return True, f'判别日程耗尽,强制集中到先验最优 {best}(=现状行为,损失封顶)'
        total_hold = self.hold_cost * self.capacity * 0.2
        if total_hold > max_hold_cost:
            self.concentrated = best
            return True, f'容量成本 {total_hold:.2f} > 组合增益上限,集中 {best}'
        return False, f'多线持有中(top={best} w={w[best]:.2f})'

    def handoff_hypothesis(self) -> tuple[str, dict[int, float]] | None:
        """交棒协议:集中线 → (line_id, p(t) 占位)供 20 号 HypothesisRegistry 注册。"""
        if not self.concentrated:
            return None
        return self.concentrated, {0: 0.0, 8: 0.5, 26: 1.0}
