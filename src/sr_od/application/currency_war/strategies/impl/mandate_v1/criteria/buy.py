"""criteria/buy——EV 买面(§2.1;支配族 dominance_buy 已移 mandate 邻位)。

发射面 = ``ev_buy_candidates`` + ``ev_buy_veto`` 一体(R7-1):候选生成
与否决门不可拆开旁路。**商店线辖域申报**:EV 买候选的对象(店面牌)在
prep 黑板 ``shop_cards`` 恒 None(PrepObservation 契约,仅买牌阶段刷新)
——本面生产消费点在商店线(``decide_shop_screen``);本批 mandate_v1
商店线=冻结基线透传(见 bridge.py 解释性裁量),EV 买面的商店线接线
随判读批(步6)前的接线批落位,本模块提供判据本体与 fail-closed 语义。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import provisional
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    refund_full_star_ok,
    tier_match,
)


@dataclass
class BuyCandidate:
    """EV 买候选(序 3-5 追加支出域;字段坐标系:shop 槽位 0-based)。"""

    card_name: str
    cost: int
    star: int
    slot_idx: int          # 商店槽位下标(商店线坐标系)
    reason: str = 'ev_buy'


def ev_buy_candidates(gold: int, s_reserve: int, shop_cards: list | None,
                      k_members: tuple[str, ...],
                      level: int = 1,
                      *,
                      window: frozenset[int] | None = None,
                      counters: dict | None = None,
                      ) -> tuple[list[BuyCandidate], str]:
    """EV 买候选生成(发射面前半)。

    fail 方向(R3-4 显式判据 fail-closed 常开):
    - ``shop_cards`` 无(商店线辖外/pick 帧域)⇒ 空候选 + 'shop_domain';
    - u/U_X 未标定(None)⇒ 序 3-5 消费无载 ⇒ 空候选 + 'u_unavailable'
      (对称 fail-closed:买面缺输入 = 不放行,§2.1 E_rev 镜像);
    - 金 < cost + S 预留(检查点③辖 EV 买面;P56 批起 s_reserve =
      可变现息线下界 g* − Σ活期退金投影,语义单一源 = shop.py 预算投影段)
      ⇒ 过滤 + 'ev_buy_s_reserve_reject' 分键计数(R3-R5 分键遥测)。
    候选第三类(R8-6 收窄):活跃窗口档内 ∧ 1★(refund_full)——
    2★+ 档内单无 EV 背书不发射。**单卡消费位窗口**(IMPL_ADV_R200 症5①:
    硬编码 {1,2,3} 占位删除)= 确定性查表(
    ``statefn/odds.card_search_window`` 塌缩带锚,ADR-0516 重锚)。T_SEARCH_A
    布尔门已退役出本消费位(T1 短路径,设计 13_buy_face_design §2.3):
    生产消费位传帧级现算 ``window``(空集=真无窗口帧,非门控);
    ``window=None`` 保留旧调用面(V_MS 门缺读空集——T_SEARCH_A 注入态
    契约路径,生产不再经此)。
    """
    if not shop_cards:
        return [], 'shop_domain'
    if provisional.is_none('U_X'):
        return [], 'u_unavailable'
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.odds import (
        card_search_window,
    )
    out: list[BuyCandidate] = []
    if window is not None:
        t_search: frozenset[int] = window
    elif not provisional.is_none('T_SEARCH_A'):
        t_search = card_search_window(level)  # 单卡消费位:读法乙(旧调用面)
    else:
        t_search = frozenset()   # T_SEARCH_A None ⇒ 活跃窗口空(fail-closed)
    for i, card in enumerate(shop_cards):
        name = getattr(card, 'char_id', '') or ''
        cost = int(getattr(card, 'cost', 0) or 0)
        star = int(getattr(card, 'star', 1) or 1)
        if name in k_members:
            continue            # 线内件走 M2 义务,非 EV 域
        if not tier_match(cost, t_search):
            continue
        if not refund_full_star_ok(star, cost):
            continue            # R11-2:发射背书仅 1★
        if gold - cost < s_reserve:
            # 检查点③(P56 可变现下界):拒因分键计数(R3-R5)
            if counters is not None:
                counters['ev_buy_s_reserve_reject'] = \
                    counters.get('ev_buy_s_reserve_reject', 0) + 1
            continue
        out.append(BuyCandidate(name, cost, star, i))
    return out, ''


def ev_buy_veto(candidate: BuyCandidate, gold: int) -> tuple[bool, str]:
    """EV 买否决门(发射面后半;D 否决域先于放行,R20-7)。

    2★+ 不发射(L-R3-4 命题 3:无 EV 正性证明 ⇒ fail-closed);
    金不足(检查点①)⇒ 拒。
    """
    if candidate.star >= 2:
        return True, 'star2p_no_ev_backing'
    if gold < candidate.cost:
        return True, 'unaffordable'
    return False, ''
