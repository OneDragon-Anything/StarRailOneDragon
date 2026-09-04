"""q / P_shop / E[refreshes] / p̄:商店概率层(cw_shop_odds 单一源消费)。

NMF §2 三行的包装消费:概率表本体在 ``cw_shop_odds``(【注】注册表),
本模块不重算 E[refreshes(超几何 DP)——直接 import 消费;新增实现仅
q(槽级命中)与 p̄(多项×超几何精确式,P16 修复批口径)。
P41 A2 防错注:第 4 参 c = **同费非目标已拿走数(taken_c),禁传 cost**——
跨档购零压缩系模型结构事实(q_X 不含 taken_Y,P49 (7) 行为断言)。
"""
from __future__ import annotations

import itertools
import math

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    REFRESH_PROB,
    SHOP_SLOTS,
    expected_refreshes,
    refresh_prob,
)
from sr_od.application.currency_war.kernel.cw_state import REFRESH_COST_BASE


def slot_q(level: int, cost: int, j: int, taken_c: int) -> float:
    """槽级命中概率 q = p(L,c) × (a−j)/(v·a − j − taken_c)(NMF §2「q」行;
    P38 ③层口径)。j=特定卡持有数(池衰减),taken_c=同费非目标已拿走数
    (禁传 cost,P41 A2)。分母与注册表权威 ``cw_shop_odds._refresh_dist``
    同式(total = va−j−c,「拥有的 j 张已离开牌库」)——分子分母同扣 j,
    漏扣 j 使 q 随持牌数系统性低估(IMPL_ADV_R200 症2 勘误)。"""
    p = refresh_prob(level, cost)
    if p <= 0:
        return 0.0
    a = POOL_COPIES_PER_CARD[cost]
    v = DISTINCT_CARDS_PER_COST[cost]
    denom = v * a - j - taken_c
    if denom <= 0 or a - j <= 0:
        return 0.0
    return p * (a - j) / denom


def p_shop(level: int, cost: int, j: int = 0, taken_c: int = 0) -> float:
    """单店至少一张目标卡概率 = 1−(1−q)^SHOP_SLOTS(NMF §2「P_shop」行)。

    槽间独立声明(IMPL_ADV_R200 症2 泛化步,不静默换模型):本式假设
    SHOP_SLOTS 个槽位命中独立;注册表权威形态(``_refresh_dist``)是
    「槽位数~B(5,p) + 同店内无放回超几何」——无放回使命中负相关 ⇒
    P(全空)_无放回 ≤ (1−q)^5 ⇒ 独立式**低估** P_shop。适用依据:NMF
    §2「P_shop」行声明形态即独立式(闭式带的近似门,q 单槽量级 ≤~0.05
    时二阶差量 ~C(5,2)·q² 相对偏差 ≤1e-3 量级);消费位影响:a7_lower_
    bound=c/P_shop 高估(保守端)、v_opt 的 c/P_shop 分量高估(fail-open
    端)——与 p_miss 消费面同申报,接线日对拍复核(精确式可经注册表
    ``1 − _refresh_dist(p, v, a, taken_c, 1, j)[0]`` 直算,不另建模型)。
    """
    q = slot_q(level, cost, j, taken_c)
    return 1.0 - (1.0 - q) ** SHOP_SLOTS


def _v_ms_value() -> float | None:
    """V̄ 现读(provisional V_MS 槽位值;None=未标定,fail-closed)。

    开门判据端点=CALIB_REPORT_V2 §2.3 门式:V̄ 取值即 CalibValue.value
    (=带的上沿,如注入形态 24.7);敏感臂判读用带(消费方另取端)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
        provisional,
    )
    cv = provisional.get('V_MS')
    if cv is None or cv.value <= 0:
        return None
    return cv.value


def tier_search_window(level: int, vbar: float | None = None) -> frozenset[int]:
    """档级搜索窗口(读法甲,档级消费位:压库/凑息/M6;P49 档匹配)。

    门式 = CALIB_REPORT_V2 §2.3 读法甲(p40 单步 EV 门 V* = c_eff/P ≤ V̄
    的档级退化:p(L,c) ≥ c_eff/V̄):等级现读 REFRESH_PROB,c_eff =
    REFRESH_COST_BASE——零新自由参数,窗口是「读法×等级×带端」三元状态量
    (两读法逐级矛盾系物理事实,非缺陷)。表值对拍锚=
    calib_v2_analysis.json ``tier_level_gate.e2_24.7``(V̄=24.7 全表)。

    V̄ 取值(T1 短路径,设计 11_shop_decisions §6):生产消费位传帧级
    现算值(``vbar.window_vbar``,P57 双读法;T_SEARCH_A 布尔门已退役出
    窗口消费位);``vbar=None`` 保留旧调用面 = provisional V_MS 槽位现读
    (None ⇒ 空集 fail-closed,不造常数窗口)。
    """
    v = vbar if vbar is not None else _v_ms_value()
    if v is None or v <= 0:
        return frozenset()
    thr = REFRESH_COST_BASE / v
    return frozenset(
        c for c in (1, 2, 3, 4, 5) if refresh_prob(level, c) >= thr)


def card_search_window(level: int, vbar: float | None = None) -> frozenset[int]:
    """单卡搜索窗口(读法乙,单卡消费位:ev_buy 追件;p40/p41 追特定卡)。

    门式 = CALIB_REPORT_V2 §2.3 读法乙(P_shop=1−(1−p/v)^5 满池,p41 ①
    退化式;窗口(c) ⟺ c_eff/P_shop ≤ V̄):P_shop 满池 j=0/taken_c=0
    经本模块 ``p_shop`` 同一实现(单一源);其余同 ``tier_search_window``。
    对拍锚 = calib_v2_analysis.json ``card_level_gate.e2_24.7``(V̄=24.7
    全表;L7 读法甲 {1,2,3,4} vs 读法乙 {2,3} 即两读法分立锁例)。
    V̄ 取值同 ``tier_search_window`` 的 T1 参数化申报。
    """
    v = vbar if vbar is not None else _v_ms_value()
    if v is None or v <= 0:
        return frozenset()
    thr = REFRESH_COST_BASE / v
    return frozenset(
        c for c in (1, 2, 3, 4, 5) if p_shop(level, c, 0, 0) >= thr)


def _char_has_tag(ch: object, tag: str) -> bool:
    return tag in (getattr(ch, 'factions', None) or ()) \
        or tag in (getattr(ch, 'flows', None) or ())


def _tier_stats(tag: str) -> dict[int, tuple[int, int]]:
    """{cost: (目标张数 A, 池总张数 T)}——阵营/流派标签圈目标集(P16 口径)。"""
    out: dict[int, tuple[int, int]] = {}
    for cost in sorted({ch.cost for ch in CHARACTERS.values()
                        if _char_has_tag(ch, tag)}):
        a = POOL_COPIES_PER_CARD[cost]
        v = DISTINCT_CARDS_PER_COST[cost]
        n = len([ch for ch in CHARACTERS.values()
                 if ch.cost == cost and _char_has_tag(ch, tag)])
        if n:
            out[cost] = (n * a, v * a)
    return out


def p_bar_exact(tag: str, level: int) -> float:
    """p̄(换线命中率)精确式 = 多项×超几何(P16 修复批口径,R2-11 对拍锚)。

    ``P(全空) = Σ_{m_c} [5!/Πm_c!·Πp_c^{m_c}] · Π_c C(T_c−A_c, m_c)/C(T_c, m_c)``

    旧 union bound(Σ_cost P(≥1|cost))系并集上界,高估 +8.1% 已勘误——
    禁再产上界口径。分母恒用满池 T=v·a(P16 ①「分子修正+分母满池」)。
    resolved 池突变语境(黑塔纪元 216 池等)下 v_c/a_c 变化 ⇒ 本式参数化
    自动正确(DIRECT_LINE_MATH_CHECK 补注①:公式是参数化的,不用重推;
    池参数 resolved 接线随判据层步 4 落)。
    """
    tiers = sorted(REFRESH_PROB.get(level, {}).items())
    tiers = [(c, p) for c, p in tiers if p > 0]
    stats = _tier_stats(tag)
    n = len(tiers)
    total_none = 0.0
    for m_vec in itertools.product(range(SHOP_SLOTS + 1), repeat=n):
        if sum(m_vec) != SHOP_SLOTS:
            continue
        logp = math.lgamma(SHOP_SLOTS + 1) \
            - sum(math.lgamma(m + 1) for m in m_vec)
        for (_cost, p), m in zip(tiers, m_vec, strict=True):
            logp += m * math.log(p)
        none_prod = 1.0
        for (cost, _p), m in zip(tiers, m_vec, strict=True):
            if m == 0 or cost not in stats:
                continue
            a_tgt, tot = stats[cost]
            none_prod *= (math.comb(tot - a_tgt, m) / math.comb(tot, m)
                          if tot - a_tgt >= m else 0.0)
        total_none += math.exp(logp) * none_prod
    return 1.0 - total_none


__all__ = [
    'DISTINCT_CARDS_PER_COST', 'POOL_COPIES_PER_CARD',
    'card_search_window', 'expected_refreshes',
    'p_bar_exact', 'p_shop', 'refresh_prob', 'slot_q',
    'tier_search_window',
]
