"""criteria/refresh——刷新面(§2.4)。

四函数位(r0_stop/r1_start/r2_budget/crisis_refresh_invariant,
R10-3 缺行封死后的完备集)。D-D(硬节点备战补强门)落点:
``hard_node_reinforce_gate`` 按节点类型(遭遇/boss)接线 P26 备战门 +
P40 刷新门的语境输入(共根组 2:威胁语境进决策输入)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_state import (
        GameState,
    )

# 硬节点类型(节点行识别词;D-D 语境维)
HARD_NODE_TYPES: frozenset[str] = frozenset({'encounter', 'boss'})


def r0_stop(no_qualifying_set: bool, budget_exhausted: bool) -> bool:
    """R0 维持结构门/R0-2 结构判据(辖刷新循环停止;零参数)。

    合格集空(店面无目标域卡)∨ 预算递推耗尽 ⇒ 停刷。结构位,臂①
    保留(旁路 r1/r2 后无循环可停,递推输入=店面快照+金,仍良定义——
    R10-3 辖域交叠声明)。
    """
    return no_qualifying_set or budget_exhausted


def r1_start(ev_positive: bool | None) -> tuple[bool, str]:
    """付费刷新发射位(r1)。EV 正性判据输入 None(V̄ 封印/未标定)
    ⇒ 不刷(fail-closed)。

    墓碑纪律标注(ADR-0516):生产消费者已随 V̄ 链退役——R1 启动门
    现行判据 = ``r1_commitment_account`` 路径总账(装配在 shop.py),
    本函数零调用面。保留 = 四函数位完备集(r0_stop/r1_start/r2_budget/
    crisis_refresh_invariant,R10-3 缺行封死),禁按旧 EV 正性语义
    复活接线(旧 V̄_net 比较项属已退役的胜率建模链)。
    """
    if ev_positive is None:
        return False, 'ev_unavailable'
    return ev_positive, ''


def r1_commitment_account(total_ledger: float, budget: int) -> tuple[bool, str]:
    """R1 启动门·形式二可负担性判定(ADR-0516;路径总账判据)。

    刷新启动 iff ``c_eff·E(D|L*) + Σ卡费 + L(g, spend, R_剩余, Ī)
    ≤ 可用预算 = g − g*``(g* = saturation_line(cap_resolved)
    = 10×cap_resolved)。装配侧(shop.py)算总账并选 L*(形式二等级
    选择输出:留级账 T_stay vs 升一级账 T_up 取小,升级账含 U_L 及其
    息损);本函数只做比较。输入全为游戏定义量(REFRESH_PROB 池参数/
    XP 表/息律),零胜率建模(用户裁定 2026-09-04;旧 V̄_net 比较项
    已随 V̄ 链退役,statefn/vbar 墓碑)。

    边界:``total_ledger`` 非有限(无可追成员:E=∅ 或该级不出此费)
    ⇒ 不启动——P40 R0-1「合格集空 ⇒ EV 恒负」的刷新侧特例;
    ``budget ≤ 0``(金在息线 g* 及以下)⇒ 恒不启动——息线双侧修正
    (ADR-0516 修正③:停级买牌也压金破息,两侧都过 g* 账)由比较式
    结构承载,不另设门。
    """
    import math

    if not math.isfinite(total_ledger):
        return False, 'no_chaseable_member'
    return ((True, '') if total_ledger <= budget
            else (False, 'account_over_budget'))


def r2_budget(gold: int, reserve: int, refresh_cost: int) -> bool:
    """付费刷新预算门(r2;臂①=门关闭)。金−预留 ≥ 刷价才批。"""
    return gold - reserve >= refresh_cost


def crisis_refresh_invariant(gold: int, hp_critical: bool) -> bool:
    """P36-a 危机不变式(executor 结构位承载,本函数=纯数供对拍)。

    危局帧刷新维持结构约束(危机成因不可达优先于危机特设出口,
    [39] 裁定——hp 只进读数位)。返回 True = 不变式成立(允许刷新)。"""
    return not (hp_critical and gold <= 0)


def hard_node_reinforce_gate(node_type: str | None, gold: int,
                             floor_gold: int) -> tuple[bool, str]:
    """D-D 硬节点备战补强门(P26 备战门+P40 刷新门按节点类型接线)。

    下一节点 ∈ HARD_NODE_TYPES ∧ 金 ≥ 守息下界 ⇒ 放行补强意图
    (定向 D 缺档件/治疗件);非硬节点 ⇒ 关。Δp_prep 挂标定
    (标定前形态 = 结构门,数值加权随标定批)。
    """
    if node_type not in HARD_NODE_TYPES:
        return False, 'not_hard_node'
    if gold < floor_gold:
        return False, 'gold_below_floor'
    return True, ''


def qualified_member_costs(buy_members: tuple[str, ...],
                           bench: list, deployed: list,
                           level: int) -> list[int]:
    """合格集成员费带 = 未 2★ 成型 ∧ 该级可刷出(refresh_prob>0)成员的
    注册表 cost 列表(P91 活跃搜索方向费带单一源;P40 合格集资格过滤与
    ``r2_card_reserve`` 同款语义,本函数为该过滤的公共承载位——R2 预留
    卡价 min 消费与 P91 压库同轴带偏好同源,禁第二份过滤实现)。

    过滤序 = 成型先序(2★ 出域先于可追性判定,test_cw_refresh_ledger
    锁 A 锁定的判定顺序);注册表缺项/无 cost 成员跳过。返回升序列表,
    空列表 = 合格集空(该级无可追成员)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob

    costs: list[int] = []
    for m in buy_members:
        ch = CHARACTERS.get(m)
        if ch is None or not ch.cost:
            continue
        copies = [c for c in list(bench) + list(deployed)
                  if (getattr(c, 'char_id', '') or '') == m]
        if any((getattr(c, 'star', 1) or 1) >= 2 for c in copies):
            continue
        if refresh_prob(int(level), int(ch.cost)) <= 0.0:
            continue
        costs.append(int(ch.cost))
    return sorted(costs)


def r2_card_reserve(k_members: tuple[str, ...],
                    bench: list, deployed: list,
                    state: GameState,
                    level: int | None = None) -> int:
    """R2 预算门 Σ预留卡价 ρ = 合格集最低费卡价(公共单一源;修 R2 批
    实现,原 shop 模块私有实现提升至此——落点裁定 = 方案审 v2:ρ 依赖
    ``data/cw_chars.CHARACTERS`` 注册表与 ``refresh_prob`` 现读,属判据面,
    禁进 kernel 经济层破坏其输入纯度;P54 floor 与 P71-b 升级预算闸
    (ADR-0560)的 ρ/Σ预留分量同源消费,禁第二实现)。

    ⚠ 同名异义锚:本 ρ(P54「合格集最低费卡价」)与
    ``statefn/s_line.py`` 的 ``rho(delta_v_band, delta_v_pop, rounds)``
    (P48 整买价值率)毫无关系,两 ρ 共存于同一模块树,消费禁接错源。

    可追过滤等级:缺省=当前级;R2 消费位在 R1 选定 L* 之后,调用方
    (shop.py R1 段)按 L* 重估传入——R1 已选等级的出牌面辖 R2 预留
    卡价(用当前级过滤会在 L*≠当前级帧错档)。P71-b 预算闸消费取
    缺省当前级:闸在升级授权前评估,预留口径与 P54 floor「满息档 +
    至少一张命中卡可买」同帧同等级(见 levelup.levelup_budget_gate)。

    证明单一源 = p54-r2-interest-floor §②(零新自由参数:ρ 锚
    CHARACTERS 注册表 cost,非字面量)。可追过滤与 R1 装配侧
    (shop.py ``_r1_ledger_terms``)同一(该级出此费 refresh_prob>0 ∧
    无 2★)——语义单一源不复制。单卡下界口径(P54 A2:P40 待标定清单
    「最低费卡价 × 期望命中数」在单刷波粒度下的整数下界;多命中超出
    部分 = 下一波 R2 重估补足的显式让渡,非破线刷新)。合格集空 ⇒ 0:
    该帧 R1 必先以 no_chaseable_member 关闭,R2 不可达,兜底值不进
    任何可达比较。

    实现注:T-263 批起成员过滤消费 ``qualified_member_costs`` 公共承载位
    (P91 同轴带同源;本函数语义/签名/返回值零变化——纯内部重构,
    test_cw_interest_floor 私有名直引面不受影响)。
    """
    costs = qualified_member_costs(k_members, bench, deployed,
                                   int(state.level or 1) if level is None
                                   else int(level))
    return min(costs) if costs else 0


def all_channel_buy_exists(gold: int, g_star: int, cap_resolved: int,
                           bench_free: int, seat_recoverable: bool,
                           missing_costs: list[int],
                           stockpile_costs: list[int],
                           merge_pair_costs: list[int],
                           level: int,
                           ev_face_open: bool,
                           window_nonempty: bool,
                           ) -> bool:
    """P92 全通道可实现买入集非空判定尺(math_proofs P92;面②六桶审计
    ①桶判定的单一源,「在册结构的严格化非新门」口径)。

    语义:「任何店产都不会触发买入」的全通道语义(p40 :25/:63)——
    四买入通道(dominance 1★ 净 0 / 义务 M2 / EV 买面 / 合成完备购)
    的帧级可达性并集。全部为假 ⇒ 付费刷新净差 = −(c_eff+L) < 0 严格
    (P92 命题),消费位(R1 发射前)据此拦阻。与在册 R0-1 的分工:
    R0-1(E=∅,成员合格性维)在 r1_commitment_account 先行;本判定尺
    补其在册语义的席满维(p40 :63「bench 满到没过渡牌可买」)与可购性
    维(金不足且不可腾),两维在现行实现缺位。

    逐通道口径(出处):
    - dominance:``mandate.dominance_buy_eligible`` 直调(金>g* ∧ 席,
      零第二实现)+ 结算线 ADR-0624 单一源 ``shop.check_settlement_line``
      直调(最便宜 1★ 形态;落地审 H2 修:原内联 gold−1 ≥ g* 系第二
      实现,该谓词设立理由恰是防穿线判据漂移)——任一店产 1★ 线外件
      即触发,池非空故只查帧级资格;
    - 义务 M2(缺员+臂①囤腿):∃成员「该级可刷出(refresh_prob>0)
      ∧ 金 ≥ 注册表 cost ∧ 席可落」;席可落 = bench_free>0 ∨
      ``seat_recoverable``(腾席可达代理,调用方传 P56 投影
      liquid_refund>0——存在可变现 1★ 燃料件时 M4 腾席/M2 通道的
      席位前置可满足。**代理偏宽申报**:高估腾席可达 ⇒ 门偏不拦 ⇒
      保守端 = 现行为,P92 拦阻只在确定严格劣帧开火);
    - EV 买面:``ev_face_open``(调用方传 not provisional.is_none
      ('U_X');生产恒 None ⇒ 恒 False,如实建模现决策机器)∧ 席 ∧
      ``window_nonempty``;
    - 合成完备购(M2b):∃同名 1★×2 配对「refresh_prob(level,base)>0
      ∧ 金 ≥ base」——**满栏不阻断**(merge §2.5 机制事实,p76「深追
      不受席满阻断」,买入即自动合成净释放 1 席)。

    输入全为帧级现读/注册表量,零新自由参数;调用方装配候选 cost 列表
    (缺员/囤腿/配对),判定尺只做通道合取判定。
    """
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        mandate,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.shop import (
        check_settlement_line,
    )

    seat_ok = bench_free > 0 or seat_recoverable
    # ① dominance 1★ 净 0(资格门单源直调 + 结算线 ADR-0624 单一源
    # check_settlement_line 直调,最便宜 1★ 形态;落地审 H2 修)
    if mandate.dominance_buy_eligible(gold, bench_free, cap_resolved) \
            and check_settlement_line(gold, 1, g_star)[0]:
        return True
    # ② 义务 M2:缺员(0→1)与臂①囤腿(1→2)同通道两形态
    if seat_ok:
        for cost in missing_costs:
            if refresh_prob(level, cost) > 0.0 and gold >= cost:
                return True
        for cost in stockpile_costs:
            if refresh_prob(level, cost) > 0.0 and gold >= cost:
                return True
    # ③ EV 买面(生产 fail-closed:U_X None ⇒ 通道恒空)
    if ev_face_open and seat_ok and window_nonempty:
        return True
    # ④ 合成完备购(满栏不阻断;第三张可刷出且买得起)
    for base in merge_pair_costs:
        if refresh_prob(level, base) > 0.0 and gold >= base:
            return True
    return False
