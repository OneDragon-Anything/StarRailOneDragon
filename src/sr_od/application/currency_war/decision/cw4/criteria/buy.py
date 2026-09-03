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

from sr_od.application.currency_war.decision.cw4.audit import provisional
from sr_od.application.currency_war.decision.cw4.statefn.vopt import (
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
                      ) -> tuple[list[BuyCandidate], str]:
    """EV 买候选生成(发射面前半)。

    fail 方向(R3-4 显式判据 fail-closed 常开):
    - ``shop_cards`` 无(商店线辖外/pick 帧域)⇒ 空候选 + 'shop_domain';
    - u/U_X 未标定(None)⇒ 序 3-5 消费无载 ⇒ 空候选 + 'u_unavailable'
      (对称 fail-closed:买面缺输入 = 不放行,§2.1 E_rev 镜像);
    - 金 < cost + S 预留(检查点③辖 EV 买面)⇒ 过滤。
    候选第三类(R8-6 收窄):活跃窗口档内 ∧ 1★(refund_full)——
    2★+ 档内单无 EV 背书不发射。**单卡消费位窗口**(IMPL_ADV_R200 症5①:
    硬编码 {1,2,3} 占位删除)= 运行时确定性查表 CALIB_REPORT_V2 §2.3
    读法乙(``statefn/odds.card_search_window``:等级现读 REFRESH_PROB、
    V̄ 现读 provisional V_MS、c_eff=REFRESH_COST_BASE,零新自由参数;
    V_MS 缺读 ⇒ 空集 fail-closed)。
    """
    if not shop_cards:
        return [], 'shop_domain'
    if provisional.is_none('U_X'):
        return [], 'u_unavailable'
    from sr_od.application.currency_war.decision.cw4.statefn.odds import (
        card_search_window,
    )
    out: list[BuyCandidate] = []
    t_search: frozenset[int] = frozenset()   # T_SEARCH_A None ⇒ 活跃窗口空(fail-closed)
    if not provisional.is_none('T_SEARCH_A'):
        t_search = card_search_window(level)  # 单卡消费位:读法乙确定性查表
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
            continue            # 检查点③:S 预留
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


def p2_lock_buy() -> bool:
    """P2 锁线核心卡(§2.11 P25 钩子占位):默认关——线内核心卡走 M2 义务。"""
    return False
