"""28 号 Tier-2 落地:常数区间稳健性扫描(结论翻转临界点)。

主张(28 号 §2 主张3):机制常数带证据区间(XP_CLICK_COST_FLAT 4-8、刷新费、息参数),
关键结论(如 Tier-1 的无死锁证明)在区间内是否稳健?输出「结论翻转临界点」清单——
哪个常数、取到什么值,结论翻转(死锁出现/消失)。这是 24 号权重搜索的前置(28 号
论证过:结论不稳的常数该先收窄区间,不该搜权重)。

扫描法:对每个常数,在其证据区间网格取值,重跑 Tier-1 穷举,记录 verdict 变化。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field

sys.stdout.reconfigure(encoding='utf-8')

from sr_od.application.currency_war import cw_deadlock_prover as dp


@dataclass
class FlipPoint:
    """一个结论翻转临界点。"""

    constant: str
    value: float
    verdict_before: str
    verdict_after: str


@dataclass
class RobustnessReport:
    flips: list[FlipPoint] = field(default_factory=list)
    scanned: list[tuple[str, int]] = field(default_factory=list)   # (常数, 点数)

    @property
    def verdict(self) -> str:
        return 'ROBUST' if not self.flips else f'FLIPS x{len(self.flips)}'


def scan_refresh_cost(lo: int = 1, hi: int = 4) -> RobustnessReport:
    """SHOP_REFRESH_COST 区间扫描(证据区间 1-4,当前 2)。"""
    rep = RobustnessReport()
    prev = None
    for v in range(lo, hi + 1):
        dp.REFRESH_COST = v
        r = dp.enumerate_deadlocks()
        verdict = r.verdict
        if prev is not None and verdict != prev:
            rep.flips.append(FlipPoint('SHOP_REFRESH_COST', v, prev, verdict))
        prev = verdict
    rep.scanned.append(('SHOP_REFRESH_COST', hi - lo + 1))
    return rep


def scan_income(lo: int = 3, hi: int = 7) -> RobustnessReport:
    """BASE_INCOME 区间扫描(证据区间 3-7,当前 5):活性条件的救援力度。

    注:base income 硬编码 5 在活性条件里 —— 扫描它 = 模拟低收入环境的死锁出现。
    """
    rep = RobustnessReport()
    prev = None
    src_fn = dp._progress_actions_available
    for v in range(lo, hi + 1):
        # 动态改收入:包装活性条件(收入 v 而非 5)

        def _wrap(gold, level, bench, refresh_cap=4, _inc=v, _orig=src_fn):
            ok0, why0 = _orig(gold, level, bench, refresh_cap)
            if ok0:
                return ok0, why0
            # 平凡贫困态:用 _inc 收入重判
            g2 = gold + _inc + min(gold // 10, dp.INTEREST_CAP // 10)
            ok2, why2 = _orig(g2, level, bench, refresh_cap)
            if ok2:
                return True, f'低收入救援({_inc})后可行动'
            return False, f'低收入{_inc}两步死锁: {why0}'
        dp._progress_actions_available = _wrap
        r = dp.enumerate_deadlocks()
        verdict = r.verdict
        if prev is not None and verdict != prev:
            rep.flips.append(FlipPoint('BASE_INCOME', v, prev, verdict))
        prev = verdict
    dp._progress_actions_available = src_fn
    rep.scanned.append(('BASE_INCOME', hi - lo + 1))
    return rep


if __name__ == '__main__':
    for rep in (scan_refresh_cost(), scan_income()):
        print(f'{rep.verdict}: scanned={rep.scanned}')
        for f in rep.flips:
            print(f'  翻转: {f.constant}={f.value} {f.verdict_before} → {f.verdict_after}')
