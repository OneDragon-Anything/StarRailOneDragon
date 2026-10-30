"""criteria/refresh——刷新面(§2.4)。

刷新链三组件定型:判据(:func:`refresh_warranted`,三段式查表)→
金线闸(:func:`r2_budget`,预留由 :func:`r2_card_reserve` 供给,调用方
装配)→ 发射。

预测门退役(统一让位优先级迭代 3.4,dismantle §1):旧「目标可买三腿
并集」(:func:`target_buyable`,判据与免费刷新分支的合取门)整门删除
——刷新时点信息不足、精确不可算,用信息最少的时点否决决策是
g_20261029_084447 刷新卡死的直接机制(总纲 §1.2);判据收敛为三段式
分派,免费腿改无条件刷(design §2.2)。该门符号已退役,禁按旧枚举
语义复活接线。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


def refresh_warranted(state: GameState,
                      session: StrategySession) -> tuple[bool, str]:
    """三段式刷新判据主式(shop_session §2.4)。

    **值得刷新 ⟺ 存在「当前星级 < 必要星级」的角色 ∧(等级 ∈ 最优
    概率带 ∨ 等级 > 带上界〔被推过——当前即剩余可达最优〕)**;分派注:
    等级 < 带下界时主式为假 → 不刷、升级优先(停留门覆盖)——三支是同一
    等级轴上的互斥完备分派,主式只取后两支为真。带归属绑定 = 当前停留
    目标的带(多目标费用档升序的当前目标——非逐角色∃带)。段边界:

    - **P1 恒不主动刷新**(阶段优先于锁定态——P1 硬规则锁定局同样
      不刷;载体 = ``plane2_started`` 窗口谓词,宪 2 合规);
    - **P2 未锁窗口**(投资策略选定前的短暂窗口)= 候选缺件驱动:
      候选 top3 缺件中存在「等级 ≥ 其最优概率带下界」的成员 → 可刷
      (概率带命中;金前提照旧由调用方装配);
    - **锁定后** = 星级目标驱动(本函数主式;多目标停留顺序 = 未完成
      星级目标中费用档最低者,「定了 3★ 追到底无降档」由 need_star
      表承载)。

    判据形态 = 查表零计算(用户裁定 2026-10-12「期望价值难算不直观,
    星级目标直接驱动」;原 R1 期望启动门已由本查表判据取代)。目标
    可买合取已随预测门整门删除(统一让位优先级迭代 3.4,dismantle §1:
    刷新时点预测不可算,判据收敛本三分派;该门符号已退役,禁按旧枚举
    语义复活接线)。金前提(R2 预算门,预留 =
    saturation_line + 停留目标实费档)= 调用方装配,不在本函数。
    返回 (是否值得刷,拒因键——判读归因)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
        deployed_rows_of,
        level_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
        state_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
        line_members_view,
        plane2_started_of,
    )
    # 段边界裁决:P1 恒不刷(阶段属性与锁定态正交,shop_session §2.4)。
    if not plane2_started_of(state):
        return False, 'p1_no_refresh'
    level = int(level_of(state))
    view = line_members_view(state)
    if not view.locked:
        # P2 未锁窗口:候选缺件驱动(概率带命中候选 top3 缺件)。
        held: set[str] = set()
        front, back = deployed_rows_of(state)
        for u in (*bench_units_of(state), *front, *back):
            if u is not None:
                held.add(str(u.char_id or ''))
        qualified: list[str] = []
        for comp_name in state_of(state).line_candidates:
            for m in _candidate_members(comp_name, state):
                if m in held:
                    continue
                ch = CHARACTERS.get(m)
                if ch is None or not ch.cost:
                    continue
                lo, _hi = levelup.prob_band_of_cost(int(ch.cost))
                if level >= lo and refresh_prob(level, int(ch.cost)) > 0.0:
                    qualified.append(m)
        if not qualified:
            return False, 'unlocked_no_qualified_gap'
        return True, ''
    # 锁定后:星级目标驱动(带归属绑定 = 当前停留目标的带)。
    target = levelup.stay_target_of(state)
    if target is None:
        return False, 'no_star_target'
    lo, _hi = levelup.prob_band_of_cost(target[2])
    if level < lo:
        # ①带下界 > 当前等级 → 升级优先(升到带内去刷,停留门覆盖),
        # 本判据不刷([3] 语义)。资金序声明(升级推迟期):本支维持
        # 拒绝、不设解锁支——解锁支会在凑金在途帧放行刷,而刷新预留
        # 无整级预留腿(升级触发态与刷新放行态带互斥),刷新烧凑金 →
        # 「金被刷到下界、升级永久 defer」饿死环;资金线推迟态 = 攒金
        # 收敛态(每轮节点收入,金上涨吃息;凑金域唯一出辖 = 终局域
        # ALL IN),非死锁。
        return False, 'stay_gate_upgrade_first'
    # ②等级 ∈ 带 / ③等级 > 带上界(被推过,单调不可降——当前即剩余
    # 可达最优照样刷):主式为真。目标可买合取已随预测门删除(3.4)。
    return True, ''



def _comp_members(comp) -> tuple[str, ...]:
    """线成员(core ∪ shared,注册表序去重——与 line_members_view 同构)。"""
    return tuple(dict.fromkeys(
        list(comp.core_chars) + list(getattr(comp, 'shared_chars', None) or ())))


def _candidate_members(comp_name: str, state: GameState) -> tuple[str, ...]:
    """候选线成员解析(未锁窗口消费):注册表线 → core ∪ shared;
    注册表外线名(过渡内核期的配方对/动态物化产物,get_comp 不可解析)
    → 回退 ``predicates.line_members(target_comp)`` 现行为等价读——
    过渡期滞后债同 :func:`session_scope._recompute_line_state` 申报,
    候选-锁定制内核在产后注册表外名消亡。"""
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    comp = get_comp(comp_name) if comp_name else None
    if comp is not None:
        return _comp_members(comp)
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
        state_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
        predicates,
    )
    target = getattr(state_of(state), 'target_comp', None)
    if target is not None and target.name == comp_name:
        return tuple(predicates.line_members(target))
    return ()


def r2_budget(gold: int, reserve: int, refresh_cost: int) -> bool:
    """付费刷新预算门(r2;分支①=门关闭)。金−预留 ≥ 刷价才批。"""
    return gold - reserve >= refresh_cost


def _entry_cid(x: object) -> str:
    """占席条目 → 身份名(bench 占席条目 = BenchSlot 解包,deployed 行域
    单位直读;P4 容器形统一读点)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    if getattr(x, 'kind', None) is not None:
        u = bench_slot_unit(x)
        return (getattr(u, 'char_id', '') or '') if u is not None else ''
    return (getattr(x, 'char_id', '') or '')


def _entry_star(x: object) -> int:
    """占席条目 → 星级(bench 占席条目 = BenchSlot 解包,deployed 直读)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    if getattr(x, 'kind', None) is not None:
        u = bench_slot_unit(x)
        return int(getattr(u, 'star', 1) or 1) if u is not None else 1
    return int(getattr(x, 'star', 1) or 1)


def qualified_member_costs(buy_members: tuple[str, ...],
                           bench: list, deployed: list,
                           level: int) -> list[int]:
    """合格集成员费带 = 未 2★ 成型 ∧ 该级可刷出(refresh_prob>0)成员的
    注册表 cost 列表(P91 压牌库同轴带偏好单一消费源)。R2 预留 ρ 已改
    锚停留目标实费档(:func:`r2_card_reserve`),不再经本过滤——两判定
    源解耦(旧「同源消费」声明随 ρ 重定义废止)。

    过滤序 = 成型先序(2★ 出域先于可追性判定);注册表缺项/无 cost
    成员跳过。返回升序列表,空列表 = 合格集空(该级无可追成员)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob

    costs: list[int] = []
    for m in buy_members:
        ch = CHARACTERS.get(m)
        if ch is None or not ch.cost:
            continue
        copies = [c for c in list(bench) + list(deployed)
                  if _entry_cid(c) == m]
        if any(_entry_star(c) >= 2 for c in copies):
            continue
        if refresh_prob(int(level), int(ch.cost)) <= 0.0:
            continue
        costs.append(int(ch.cost))
    return sorted(costs)


def r2_card_reserve(state: GameState) -> int:
    """R2 预算门卡价预留 ρ = 当前停留目标实费档(锁定支单一源;
    2026-10-28 用户裁定实费档实现口径:ρ 取 ``levelup.stay_target_of``
    返回目标元组的 target[2] resolved 实费档——变费卡随档,与带判据
    同一目标元组,非注册表基价直查)。

    行为差申报:已 2★ 追 3★ 目标帧,旧「合格集最低费卡价」
    口径被「无 2★ 成型」过滤排除 → 漏留其卡价;新口径按其卡价预留
    (3 费 → 预留 3)。

    分支口径(分行声明,禁混引):
    - 锁定支:stay_target 恒有值(目标空帧三段式判据先拒,R2 不可达),
      ρ = 实费档;
    - 未锁窗口:stay_target 恒空(未完成星级目标集未锁期为空集)→
      ρ = 0,金线 = g* + 刷价——未锁窗口刷新目标 = 候选缺件集,无
      单一目标价,如实声明;兜底值不进任何可达比较(该帧 ρ 分量恒零
      是口径而非缺省)。

    ⚠ 同名异义锚:本 ρ 与 ``statefn/s_line.py`` 的
    ``rho(delta_v_band, delta_v_pop, rounds)``(P48 整买价值率)毫无
    关系,两 ρ 共存于同一模块树,消费禁接错源。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup,
    )
    target = levelup.stay_target_of(state)
    return int(target[2]) if target is not None else 0
