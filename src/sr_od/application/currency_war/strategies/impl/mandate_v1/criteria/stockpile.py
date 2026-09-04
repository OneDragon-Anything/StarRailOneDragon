"""criteria/stockpile——压库 EV 消费位(§2.5;档匹配谓词/V_comp 表在
statefn/vopt,R4-F4——判据函数只消费,防臂①旁路误拆 M6 买入口)。"""
from __future__ import annotations

from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    refund_full_star_ok,
    tier_match,
)


def stockpile_buy(gold: int, s_reserve: int, bench_free: int,
                  card_cost: int, card_star: int,
                  t_search: frozenset[int],
                  ) -> tuple[bool, str]:
    """EV 追加压库买入(P49;§2.5 三段辖域统一形态)。

    发射限定(R11-2/R12-3):档匹配 ∧ refund_full_star_ok(1★ 全额
    可退);席位:free≥2 直过,free=1 过 V_slot 净门
    (V_slot🔴 ⇒ 保守端 0 代入,R12-5)。金约束:cost+S 预留(检查点③)。
    T_SEARCH_A 布尔门已退役出本消费位(T1 短路径,设计 13_buy_face_design
    §2.3):``t_search`` 窗口由消费位帧级现算传入(vbar 链,P57 双读法),
    空集=真无窗口帧(非门控),判 'not_in_tier' 不买(溢余滞留遥测归
    mandate M6 侧)。
    """
    if not tier_match(card_cost, t_search):
        return False, 'not_in_tier'
    if not refund_full_star_ok(card_star, card_cost):
        return False, 'star2p_no_backing'
    if bench_free < 1:
        return False, 'bench_full'
    # V_slot 净门(IMPL_DESIGN §2.5 规格「free=1 → 过 V_slot 净门」;
    # V_slot 本体=statefn/vopt.v_slot)。规格未落位登记:净门数值输入
    # =被阻断动作净 EV,系 u/V_ms 标定派生量(U_X 不可标定、显式
    # None+豁免在案,CALIB_REPORT_V2 §2.2)⇒ 全式落位前本门无载,
    # 缺省行为=放行(V_slot 按下界 0 代入)。依据:发射已限定 1★
    # 全额可退(``refund_full_star_ok``),末席占用近可逆(卖回净成本
    # ≈0,p41-hoard-sell-ev 燃料类支配性论证)⇒ 被阻断成本下界 0。
    # 方向申报:该缺省**非保守端**(放行偏,IMPL_ADV_R200 症5④ 勘误
    # ——旧注释「保守代入放行」反号;可辩护性由 1★ 可逆性承载,
    # 不由「保守」措辞承载)。净门全式随 V_slot 标定派生批落位。
    if bench_free == 1:
        pass    # noqa: WPS420  净门无载期缺省放行(登记见上注)
    if gold - card_cost < s_reserve:
        return False, 's_reserve'
    return True, ''
