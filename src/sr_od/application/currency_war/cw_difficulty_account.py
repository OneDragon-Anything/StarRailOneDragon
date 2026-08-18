"""难度账本与价值地图 v0(redesign 36 号;ADR-0199):记账恒等式 + 场合依赖定价。

**诊断(36 号)**:难度「可算不可读」——OCR 常空全链路退先验,但主体是**记账恒等式**
(自持选择自己知道);−18% 敌血 flat 惩罚三态同值(大胜值 0/边际值一条命/无解值 0)——
方向对场合全错;200+ 溢出 bug 使「堆难度」从自杀变终局武器,系统看不见。

**v0 落地**(纯函数,离线;36 号 §2.1/§2.2):
- ``DifficultyAccount``:记账恒等式(base + Σaugment Δ + 品质通胀 + 动态项 + 节点曲线),
  OCR 读数对账接口(读到→修正,读不到→账本外推**不回退先验**);
- ``marginal_value``:场合依赖价值 = f(gap 三态 + 阈值[地板 0/溢出 200+/P1 尖峰] +
  版本证据态)——替换 ADR-0141 flat 惩罚(降为对拍锚);
- 溢出 gambit 分支(证据态守卫,refuted 自动退回常态)。

J1(测试):合成账本对拍恒等式;三态价值(大胜≈0/边际峰值/无解→0);溢出反转
(证据态 verified 时堆难度价值跳变);P1 尖峰。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 23 号注册表联动常数(证据态标注)
OVERFLOW_THRESHOLD = 200      # 敌方全属性 −100% 溢出 bug(V4.4 实测 211;UP 实录)
OVERFLOW_EVIDENCE = 'bracketed'   # unverified→verified→refuted;refuted 时 gambit 退役
DIFFICULTY_FLOOR = 0
GROWTH_PER_STREAK = 1.0       # 伟大征服动态项:当前连胜数(实测锚)


@dataclass
class DifficultyAccount:
    """难度记账恒等式(确定性推演,非噪声观测)。"""

    base: float = 100.0                     # 简报 base(职级子档决定)
    augments: dict[str, float] = field(default_factory=dict)   # 自持静态 Δ(注册表)
    quality_inflation: float = 0.0          # 品质通胀累计(每金 +3/棱彩 +6;白银/远见豁免)
    streak: int = 0                         # 伟大征服动态项
    node_curve: float = 0.0                 # 节点曲线(按 node_type,23 注册表)

    def total(self) -> float:
        return (self.base + sum(self.augments.values()) + self.quality_inflation
                + GROWTH_PER_STREAK * self.streak + self.node_curve)

    def reconcile(self, ocr_read: float | None) -> float:
        """对账:读到 → 修正残差进 augments(未知来源桶);读不到 → 账本外推不回退先验。"""
        if ocr_read is None:
            return self.total()
        resid = ocr_read - self.total()
        if abs(resid) > 1e-6:
            self.augments['(reconcile_residual)'] = self.augments.get('(reconcile_residual)', 0.0) + resid
        return self.total()

    @classmethod
    def from_strategies(cls, base: float, strategy_names: list[str],
                        streak: int = 0) -> DifficultyAccount:
        """从持卡注册表建账(v2,ADR-0205 落地:EconomyEffect 难度字段)。

        difficulty_delta 进 augments(节点型限定暂并入静态——遭遇/首领限定建模
        挂 decide_encounter 消费批);difficulty_per_streak 走 streak 动态项。
        品质通胀(API 无数值)不建。
        """
        from sr_od.application.currency_war.cw_investments import get_strategy
        acc = cls(base=base, streak=streak)
        for name in strategy_names:
            s = get_strategy(name)
            if s is None or s.economy is None:
                continue
            e = s.economy
            if e.difficulty_delta:
                acc.augments[name] = float(e.difficulty_delta)
            if e.difficulty_per_streak:
                # 多张动态卡取和(罕见);streak 项在 total() 里按 GROWTH_PER_STREAK 计
                acc.augments[f'{name}(per_streak系数)'] = float(
                    e.difficulty_per_streak - GROWTH_PER_STREAK)
        return acc


def marginal_value(d_now: float, d_delta: float, gap: float, *,
                   node_type: str = 'normal', plane: int = 1,
                   overflow_evidence: str = OVERFLOW_EVIDENCE) -> float:
    """难度边际价值:f(gap 三态 + 阈值 + 版本证据态)。

    gap = E(node,d) − D(吞吐):≪0 大胜(价值≈0)/≈0 边际(峰值)/≫0 无解(→0 该转型)。
    溢出:d_now+d_delta ≥ OVERFLOW 且证据态非 refuted → 价值大跳(终局武器);
    P1 尖峰:plane=1 开局 base 高且一层最凶 → 压低类(d_delta<0)价值放大。
    """
    # 钟形:g(|gap|),边际处峰值
    bell = max(0.0, 1.0 - abs(gap) / 30.0) ** 2
    v = -d_delta * bell       # 降难度(d_delta<0)在边际局正价值
    if plane == 1 and d_delta < 0:
        v *= 1.5              # P1 尖峰:一层遭遇常比 boss 凶,压低类放大
    # 地板:压到 0 以下无增益
    if d_delta < 0 and d_now + d_delta < DIFFICULTY_FLOOR:
        over = DIFFICULTY_FLOOR - (d_now + d_delta)
        v *= max(0.0, 1.0 - over / 10.0)   # 压过头收益衰减
    # 溢出 gambit(版本守卫):堆难度跨 200 阈 → 通关手段,价值反转
    if (d_delta > 0 and d_now + d_delta >= OVERFLOW_THRESHOLD
            and overflow_evidence != 'refuted' and d_now < OVERFLOW_THRESHOLD):
        v += 8.0 * (1.0 if overflow_evidence == 'verified' else 0.5)
    return round(v, 4)
