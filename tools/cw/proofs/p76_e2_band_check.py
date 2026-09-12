"""P76 标定批数值自检(T-278/ADR-0639,r1 返工域):ε₂ 集中度二阶带全生产域包络 + Δ 三因子打印。

不进 src;重跑:PYTHONPATH=src uv run python tools/cw/proofs/p76_e2_band_check.py
正本:P76 §3.4(丙.4 净二阶带两反向通道)+ §4.4(ε₂ 并入夹界余量);
标定设计 = .debug/temp/currency_war/T-278-标定设计.md(r1 同步);注入载体 =
mandate_v1/audit/calibration.py(值断言:包络 ≤ 注入值)。

网格域(r1 返工:必须覆盖生产消费域,与 calibration.E2_DOMAIN_* 一致):
- m ∈ {1..6} = 注册表 form_tiers needs 全集(20 comp 全扫,巡海击破 6 为上界;
  = 强制辖域 E2_DOMAIN_M_MAX,域外装配端 fail-closed);
- L ∈ {1..10}(等级全域);
- T = r_remaining ∈ {1..27}(日程全长 (9,9,9),r1 修正:原网格 24 漏日程上界;
  = 强制辖域 E2_DOMAIN_R_REMAIN_MAX,域外装配端 fail-closed);
- R ∈ {0..60 步 2} ∪ {80..1200 步 20}(付费刷数生产无界,不作强制辖域——
  全轴数值验证承载:峰密区细步长 + 小 q 长尾峰区粗步长,重算包络与
  峰密区一致,大 R 双臂概率饱和、带差趋零);
- 标签域 = CHARACTERS 全体 factions∪flows(零樱桃挑选)。

通道构造(P76 §3.4「ε₂ = 增富+收入流的二阶带」):
- ①池衰减增富:组合协议侧线支出(≤2R 金,即本协议全部付费刷预算)买
  主费档非目标 → 该费档非目标副本离池 t_c 加深 → ℓ* 目标密度升 →
  完成概率升。上限形态 = slot_q_tag 经 held_counts 非成员通道直算。
- ②收入流差:组合协议板弱败多,败轮底金(2/4)对低档连胜金(1-2)
  的金差 ≤ +2 金/战(P76 §3.4/P51 B1 同源量级)× T 战 → T 次付费刷
  → +SHOP_SLOTS·T 槽试验。
"""
from __future__ import annotations

import math

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    SHOP_SLOTS,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.audit.calibration import (
    E2_CONCENTRATION_BAND,
    E2_DOMAIN_M_MAX,
    E2_DOMAIN_R_REMAIN_MAX,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.odds import (
    slot_q_tag_by_cost,
)


def p_complete(m: int, q: float, trials: int) -> float:
    """P38 闭式 Binomial 尾(与 vopt.p_complete 同式;大 N 域用对数
    空间逐项,防 int·float 溢出——R 轴长尾网格 n 可达 ~6e3)。"""
    if q <= 0 or m > trials:
        return 0.0
    if q >= 1.0:
        return 1.0
    if trials <= 10000:
        return 1.0 - sum(math.comb(trials, x) * q ** x
                         * (1.0 - q) ** (trials - x) for x in range(m))
    from math import exp, lgamma, log, log1p
    total = 0.0
    for x in range(m):
        logc = (lgamma(trials + 1) - lgamma(x + 1)
                - lgamma(trials - x + 1))
        total += exp(logc + x * log(q) + (trials - x) * log1p(-q))
    return 1.0 - total


def _tags() -> list[str]:
    out: set[str] = set()
    for ch in CHARACTERS.values():
        if not getattr(ch, 'cost', 0):
            continue
        out.update(getattr(ch, 'factions', ()) or ())
        out.update(getattr(ch, 'flows', ()) or ())
    return sorted(out)


def _nonmember_of_cost(tag: str, cost: int) -> str | None:
    for name, ch in CHARACTERS.items():
        if getattr(ch, 'cost', 0) != cost:
            continue
        tags = set(getattr(ch, 'factions', ()) or ()) \
            | set(getattr(ch, 'flows', ()) or ())
        if tag not in tags:
            return name
    return None


def main() -> None:
    # R 轴混合分辨率(全轴数值验证):峰密区细步长 + 长尾峰区粗步长
    r_grid = list(range(0, 61, 2)) + list(range(80, 1201, 20))
    best = 0.0
    best_ch1 = 0.0
    best_ch2 = 0.0
    best_cfg = None
    for level in range(1, 11):
        for tag in _tags():
            base_qd = slot_q_tag_by_cost(tag, level, {}, {})
            if not base_qd or sum(base_qd.values()) <= 0:
                continue
            q0 = sum(base_qd.values())
            c_star = max(base_qd, key=base_qd.get)
            a = POOL_COPIES_PER_CARD[c_star]
            v = DISTINCT_CARDS_PER_COST[c_star]
            nm = _nonmember_of_cost(tag, c_star)
            enriched: dict[int, float] = {}
            for paid in r_grid:
                drained = min(v * a - 1, (2 * paid) // c_star)
                q_enr = q0
                if nm is not None and drained > 0:
                    qd2 = slot_q_tag_by_cost(tag, level, {nm: drained}, {})
                    s = sum(qd2.values())
                    q_enr = s if s > 0 else q0
                enriched[paid] = q_enr
            for need in range(1, E2_DOMAIN_M_MAX + 1):
                for rounds in range(1, E2_DOMAIN_R_REMAIN_MAX + 1):
                    for paid in r_grid:
                        trials = SHOP_SLOTS * (rounds + paid)
                        p0 = p_complete(need, q0, trials)
                        d1 = p_complete(need, enriched[paid], trials) - p0
                        d2 = p_complete(need, q0,
                                        trials + SHOP_SLOTS * rounds) - p0
                        best_ch1 = max(best_ch1, d1)
                        best_ch2 = max(best_ch2, d2)
                        cand = max(d1, 0.0) + max(d2, 0.0)
                        if cand > best:
                            best = cand
                            best_cfg = (level, tag, need, rounds, paid,
                                        round(d1, 4), round(d2, 4))
    print(f'epsilon2 full-domain envelope = {best:.4f} '
          f'(ch1 max {best_ch1:.4f} / ch2 max {best_ch2:.4f})')
    print(f'argmax cfg (level, tag, need, rounds, paid, d1, d2) = {best_cfg}')
    assert best <= E2_CONCENTRATION_BAND.value, \
        f'包络 {best:.4f} 超出注入值 {E2_CONCENTRATION_BAND.value}'
    print(f'assert envelope <= injected {E2_CONCENTRATION_BAND.value} OK')

    # Δ = V_C−V_F 三因子打印(全部已发表在库值,直引禁重算;
    # P51 §4-B-2 分层表(同节点 battle 对比)/ P52 对账 1)
    dlam = 0.341 - 0.065
    exposure = 221.7
    print(f'Delta factors: dlam={dlam:.3f} (P51 §4-B-2 battle 对比 '
          f'p8-12 0.341 − p≤7 0.065), E={exposure} (pooled p≤7 '
          f'g74.4+Phi147.3), W=2 windows')
    print(f'Delta point = {dlam * exposure * 2:.1f} 金 (ci [0, '
          f'{0.391 * exposure * 3:.1f}];λ3 上包络 = pooled 分层表最高 '
          f'95%CI 上端 p8-12×battle,小样本侧格排除口径见 ADR-0639)')


if __name__ == '__main__':
    main()
