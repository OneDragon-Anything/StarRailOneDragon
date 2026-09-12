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
from sr_od.application.currency_war.kernel.cw_plane_table import (
    peak_refresh_level,
)


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


def _collapse_window_threshold(omega: float | None) -> float:
    """塌缩带比值线 ω 解析(缺省 = DEFAULT_REGISTRY.omega_collapse_ratio,
    ADR-0475 同源单一值;窗口判据 = 塌缩带比值锚)。

    ω 处置申报【拟】:ω 是策略阈值参数,非游戏定义量——现值为 ADR-0475
    refresh_ev_budget 归零腿的复用值(未独立标定),登记待证形态、不扩
    辖域(判据输入全游戏定义量纪律不破:表值/峰值查表皆游戏定义量,
    ω 仅作窗口比值阈值);fail-closed 语义 = ω 越大窗口越窄。
    """
    if omega is None:
        from sr_od.application.currency_war.kernel.cw_registry import (
            DEFAULT_REGISTRY,
        )
        omega = DEFAULT_REGISTRY.omega_collapse_ratio
    return omega


def tier_search_window(level: int, omega: float | None = None) -> frozenset[int]:
    """档级搜索窗口(档级消费位:压库/凑息/M6;P49 档匹配)。

    判据(塌缩带重锚,承 ADR-0475 塌缩带归零线):费档 c 在搜索窗内
    ⟺ refresh_prob(level,c) ≥ ω×refresh_prob(峰值级(c),c)——等级现读
    REFRESH_PROB,峰值级 = cw_plane_table.peak_refresh_level 查表 argmax,
    ω 见 ``_collapse_window_threshold``。全游戏定义量(概率表 + 峰值查表
    + 注册表 ω 字段),零胜率/零标定带数值。旧 V̄ 门式(p ≥ c_eff/V̄,
    P57 双读法参数化)已随 V̄ 链退役(statefn/vbar 墓碑),
    读法分歧问题随之消解;对拍锚(calib_v2_analysis.json 的 V̄=24.7 全表)
    同批作废。空集语义 = 该级全部费档塌缩(真无窗口帧,非门控)。
    """
    thr = _collapse_window_threshold(omega)
    out: set[int] = set()
    for c in (1, 2, 3, 4, 5):
        p = refresh_prob(level, c)
        if p <= 0:
            continue
        peak = peak_refresh_level(c)
        p_peak = refresh_prob(peak, c)
        if p_peak > 0 and p >= thr * p_peak:
            out.add(c)
    return frozenset(out)


def card_search_window(level: int, omega: float | None = None) -> frozenset[int]:
    """单卡搜索窗口(单卡消费位:ev_buy 追件;p40/p41 追特定卡)。

    判据同 ``tier_search_window`` 的塌缩带锚,概率口径换
    单店命中 ``p_shop``(满池 j=0/taken_c=0,经本模块同一实现——单一源):
    费档 c 在窗内 ⟺ p_shop(level,c) ≥ ω×p_shop(峰值级(c),c)。
    空集语义与作废对拍锚声明同 ``tier_search_window``。
    """
    thr = _collapse_window_threshold(omega)
    out: set[int] = set()
    for c in (1, 2, 3, 4, 5):
        p = p_shop(level, c, 0, 0)
        if p <= 0:
            continue
        peak = peak_refresh_level(c)
        p_peak = p_shop(peak, c, 0, 0)
        if p_peak > 0 and p >= thr * p_peak:
            out.add(c)
    return frozenset(out)


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


def slot_q_tag_by_cost(tag: str, level: int,
                       held_counts: dict[str, int] | None = None,
                       extra_copies_by_cost: dict[int, int] | None = None,
                       ) -> dict[int, float]:
    """标签合格集的**分费档**槽级命中概率 {cost: q_c}(P38 ③层含池衰减)。

    q_c = p(L,c)·(n_c·a_c − j_c)/(v_c·a_c − j_c − t_c):n_c = 该费档带
    标签的卡种数,a_c/v_c = 池参数(注册表);j_c = 已持有该标签卡副本数
    (该费档),t_c = 已持有同费非标签卡副本数——分子分母同扣 j,与
    ``slot_q`` 的 IMPL_ADV_R200 症2 勘误约定同式(分母 = 同费剩余总副本,
    「拥有的 j 张已离开牌库」)。``held_counts`` = 逐角色名副本计数
    (消费方从 bench∪deployed bot 跟踪库存构造);``extra_copies_by_cost``
    = 已定将买、按费档直加 j_c 的同标签副本(货架件「买走即 held」口径,
    无名不可入 held_counts 时走此通道,不参与 t_c)。聚合视图 =
    ``slot_q_tag``;分档视图供消费方取主档(如被阻断动作估值),同源
    禁第二实现。费档分子/分母 ≤ 0 → 该档不计(池耗尽域外)。
    """
    held = held_counts or {}
    extra = extra_copies_by_cost or {}
    member_names = {n for n, ch in CHARACTERS.items()
                    if getattr(ch, 'cost', 0) and _char_has_tag(ch, tag)}
    out: dict[int, float] = {}
    for cost, p in sorted(REFRESH_PROB.get(level, {}).items()):
        if p <= 0:
            continue
        a = POOL_COPIES_PER_CARD[cost]
        v = DISTINCT_CARDS_PER_COST[cost]
        members = [n for n in member_names
                   if getattr(CHARACTERS[n], 'cost', 0) == cost]
        n_c = len(members)
        if n_c <= 0:
            continue
        member_set = set(members)
        j_c = sum(held.get(n, 0) for n in members) \
            + int(extra.get(cost, 0))
        t_c = sum(cnt for name, cnt in held.items()
                  if name not in member_set
                  and getattr(CHARACTERS.get(name), 'cost', None) == cost)
        denom = v * a - j_c - t_c
        numer = n_c * a - j_c
        if denom <= 0 or numer <= 0:
            continue
        out[cost] = p * numer / denom
    return out


def slot_q_tag(tag: str, level: int,
               held_counts: dict[str, int] | None = None,
               extra_copies_by_cost: dict[int, int] | None = None) -> float:
    """标签合格集槽级命中概率 q = Σ_c q_c(P38 ③层;分项单一源 =
    ``slot_q_tag_by_cost``)。单卡标签退化域(n_c=1)与 ``slot_q`` 同式
    一致(测试锁)。全档不计 → 0.0(静态不可达,诚实出「锁劣」向)。"""
    return sum(slot_q_tag_by_cost(tag, level, held_counts,
                                  extra_copies_by_cost).values())


__all__ = [
    'DISTINCT_CARDS_PER_COST', 'POOL_COPIES_PER_CARD',
    'card_search_window', 'expected_refreshes',
    'p_bar_exact', 'p_shop', 'refresh_prob', 'slot_q',
    'slot_q_tag', 'slot_q_tag_by_cost',
    'tier_search_window',
]
