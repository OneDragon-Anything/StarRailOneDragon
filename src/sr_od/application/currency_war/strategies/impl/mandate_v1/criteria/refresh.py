"""criteria/refresh——刷新面(§2.4)。

四函数位(r0_stop/r1_start/r2_budget/crisis_refresh_invariant,
R10-3 缺行封死后的完备集)。D-D(硬节点备战补强门)落点:
``hard_node_reinforce_gate`` 按节点类型(遭遇/boss)接线 P26 备战门 +
P40 刷新门的语境输入(共根组 2:威胁语境进决策输入)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

# 硬节点类型(节点行识别词;D-D 语境维)
HARD_NODE_TYPES: frozenset[str] = frozenset({'encounter', 'boss'})


def r0_stop(no_qualifying_set: bool, budget_exhausted: bool) -> bool:
    """R0 维持结构门/R0-2 结构判据(覆盖刷新循环停止;零参数)。

    合格集空(店面无目标域卡)∨ 预算递推耗尽 ⇒ 停刷。结构位,分支①
    保留(旁路 r1/r2 后无循环可停,递推输入=店面快照+金,仍良定义——
    R10-3 适用范围交叠声明)。
    """
    return no_qualifying_set or budget_exhausted


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
    星级目标直接驱动」);原 R1 期望启动门(路径总账比较式)已由本查表
    判据取代(P40/P47/P54 命题本体保留已登记)。金前提
    (利息线账 R2 预算门 + 整级预留保护)与 P92 拦刷门 = 调用方装配,
    不在本函数。返回 (是否值得刷,拒因键——判读归因)。
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
        for comp_name in state_of(state).line_candidates:
            for m in _candidate_members(comp_name, state):
                if m in held:
                    continue
                ch = CHARACTERS.get(m)
                if ch is None or not ch.cost:
                    continue
                lo, _hi = levelup.prob_band_of_cost(int(ch.cost))
                if level >= lo and refresh_prob(level, int(ch.cost)) > 0.0:
                    return True, ''
        return False, 'unlocked_no_qualified_gap'
    # 锁定后:星级目标驱动(带归属绑定 = 当前停留目标的带)。
    target = levelup.stay_target_of(state)
    if target is None:
        return False, 'no_star_target'
    lo, _hi = levelup.prob_band_of_cost(target[2])
    if level < lo:
        # ①带下界 > 当前等级 → 升级优先(升到带内去刷,停留门覆盖),
        # 本判据不刷([3] 语义)。
        return False, 'stay_gate_upgrade_first'
    # ②等级 ∈ 带 / ③等级 > 带上界(被推过,单调不可降——当前即剩余
    # 可达最优照样刷):主式为真。
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


def r1_start(ev_positive: bool | None) -> tuple[bool, str]:
    """付费刷新动作发出点(r1)。EV 正性判据输入 None(未标定)
    ⇒ 不刷(fail-closed)。

    R1 启动门现行判据 = ``refresh_warranted`` 三段式查表(shop_session
    §2.4;原路径总账比较式判据面已由查表判据取代),
    本函数零调用面。保留 = 四函数位完备集
    (r0_stop/r1_start/r2_budget/crisis_refresh_invariant,R10-3
    缺行封死),禁按旧 EV 正性语义复活接线。
    """
    if ev_positive is None:
        return False, 'ev_unavailable'
    return ev_positive, ''


def r2_budget(gold: int, reserve: int, refresh_cost: int) -> bool:
    """付费刷新预算门(r2;分支①=门关闭)。金−预留 ≥ 刷价才批。"""
    return gold - reserve >= refresh_cost


def crisis_refresh_invariant(gold: int, hp_critical: bool) -> bool:
    """P36-a 危机不变式(executor 结构位承载,本函数=纯数供交叉核对)。

    危局帧刷新维持结构约束(危机成因不可达优先于危机特设出口,
    [39] 裁定——hp 只进读数位)。返回 True = 不变式成立(允许刷新)。"""
    return not (hp_critical and gold <= 0)


def hard_node_reinforce_gate(node_type: str | None, gold: int,
                             floor_gold: int) -> tuple[bool, str]:
    """D-D 硬节点备战补强门(P26 备战门+P40 刷新门按节点类型接线)。

    下一节点 ∈ HARD_NODE_TYPES ∧ 金 ≥ 保利息下界 ⇒ 放行补强意图
    (定向 D 缺档件/治疗件);非硬节点 ⇒ 关。Δp_prep 挂标定
    (标定前形态 = 结构门,数值加权随标定批)。
    """
    if node_type not in HARD_NODE_TYPES:
        return False, 'not_hard_node'
    if gold < floor_gold:
        return False, 'gold_below_floor'
    return True, ''


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
    注册表 cost 列表(P91 活跃搜索方向费带单一源;P40 合格集资格过滤与
    ``r2_card_reserve`` 同款语义,本函数为该过滤的公共承载位——R2 预留
    卡价 min 消费与 P91 压牌库同轴带偏好同源,禁第二份过滤实现)。

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
                  if _entry_cid(c) == m]
        if any(_entry_star(c) >= 2 for c in copies):
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
    禁进 kernel 经济层破坏其输入纯度;P54 floor 的 ρ/Σ预留分量同源消费,
    禁第二实现)。

    ⚠ 同名异义锚:本 ρ(P54「合格集最低费卡价」)与
    ``statefn/s_line.py`` 的 ``rho(delta_v_band, delta_v_pop, rounds)``
    (P48 整买价值率)毫无关系,两 ρ 共存于同一模块树,消费禁接错源。

    可追过滤等级:缺省=当前级;R2 消费位在 R1 选定 L* 之后,调用方
    (shop.py R1 段)按 L* 重估传入——R1 已选等级的出牌面覆盖 R2 预留
    卡价(用当前级过滤会在 L*≠当前级帧错档;原 P71-b 升级预算闸取缺省
    当前级的消费位已随升级触发统一批删除)。升级侧花后金下界 =
    ``levelup_fund_gate`` 同链(saturation_line)。

    证明单一源 = p54-r2-interest-floor §②(零新自由参数:ρ 锚
    CHARACTERS 注册表 cost,非字面量)。可追过滤与 R1 装配侧
    (shop.py ``_r1_ledger_terms``)同一(该级出此费 refresh_prob>0 ∧
    无 2★)——语义单一源不复制。单卡下界口径(P54 A2:P40 待标定清单
    「最低费卡价 × 期望命中数」在单刷波粒度下的整数下界;多命中超出
    部分 = 下一波 R2 重估补足的显式让渡,非破线刷新)。合格集空 ⇒ 0:
    该帧 R1 必先以 no_chaseable_member 关闭,R2 不可达,兜底值不进
    任何可达比较。

    实现注:成员过滤消费 ``qualified_member_costs`` 公共承载位
    (P91 同轴带同源;本函数语义/签名/返回值零变化——纯内部重构,
    test_cw_interest_floor 私有名直引面不受影响)。
    """
    # 等级缺省读 = 容器读口 level_of(单型;显式 level 传入时跳过读,
    # 存量对账面传非容器载体须带显式 level)
    if level is None:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            level_of,
        )
        _lvl = level_of(state)
    else:
        _lvl = int(level)
    costs = qualified_member_costs(k_members, bench, deployed, _lvl)
    return min(costs) if costs else 0


def all_channel_buy_exists(gold: int, g_star: int, cap_resolved: int,
                           bench_free: int, seat_recoverable: bool,
                           missing_costs: list[int],
                           stockpile_costs: list[int],
                           merge_pair_costs: list[int],
                           level: int,
                           ev_face_open: bool,
                           window_nonempty: bool,
                           plugin_budget_open: bool = False,
                           order4_zone_open: bool = False,
                           c1_floor_cost: int | None = None,
                           ) -> bool:
    """P92 全通道可实现买入集非空判定尺(math_proofs P92;面②六桶审计
    ①桶判定的单一源,「已登记结构的严格化非新门」口径)。

    语义:「任何店产都不会触发买入」的全通道语义(p40 :25/:63)——
    四买入通道(dominance 1★ 净 0 / 义务 M2 / EV 买面 / 合成完备购)
    的帧级可达性并集。全部为假 ⇒ 付费刷新净差 = −(c_eff+L) < 0 严格
    (P92 命题),消费位(R1 发出前)据此拦阻。与已登记 R0-1 的分工:
    R0-1(E=∅,成员合格性维)在 r1_commitment_account 先行;本判定尺
    补其已登记语义的席满维(p40 :63「bench 满到没过渡牌可买」)与可购性
    维(金不足且不可腾),两维在现行实现缺位。

    逐通道口径(出处):
    - dominance:``mandate.dominance_buy_eligible`` 直调(金>g* ∧ 席,
      零第二实现)+ 结算线 单一源 ``shop.check_settlement_line``
      直调(最便宜 1★ 形态;审查H2 修:原内联 gold−1 ≥ g* 系第二
      实现,该谓词设立理由恰是防穿线判据漂移)——任一店产 1★ 线外件
      即触发,池非空故只查帧级资格;
    - 义务 M2(缺员+分支①囤分支):∃成员「该级可刷出(refresh_prob>0)
      ∧ 金 ≥ 注册表 cost ∧ 席可落」;席可落 = bench_free>0 ∨
      ``seat_recoverable``(腾位可达判定,调用方传店帧腾位分支同参
      ``mandate.fuel_sell_candidates`` 资格面非空——存在可变现 1★
      燃料件,M4 腾位/M2 通道的席位前置可满足;判定与腾位动作发出点同一
      单源,装配单一入口 = ``shop.p92_seat_recoverable``,禁金额投影
      代理。旧「P56 投影 liquid_refund>0 代理」已停用:其排除集口径
      (projection 并 T3 活跃集 ≠ 腾位分支 defer 放行)与布尔化
      (Σ退金>0 ≠ 资格非空)两向漂移随收窄一次消除,判定本体零改);
    - EV 买面:``ev_face_open``(调用方传 not provisional.is_none
      ('U_X');生产恒 None ⇒ 恒 False,如实建模现决策机器)∧ 席 ∧
      ``window_nonempty``;
    - 合成完备购(M2b):∃同名 1★×2 配对「refresh_prob(level,base)>0
      ∧ 金 ≥ base」——**满栏不阻断**(merge §2.5 机制事实,p76「深追
      不受席满阻断」,买入即自动合成净释放 1 席);
    - 序 2 场况插件(通道集重建):``plugin_budget_open``
      (会话累计额度 > 0——上阵空位已登记即有可买形态,板面差一人档
      的插件件刷新可出;席位面并入 seat_ok);
    - 序 4 压牌库分支(②(b) 死金/档 1/M6/垫件):``order4_zone_open``
      (富余帧〔金 > g*〕或奖励帧死金形态的帧级可达——M6/档 1/垫件
      的富余触发域与 ②(b) 的奖励帧低金域并集,调用方装配);
    - C1 恒买邻位:``c1_floor_cost``(注册表核心最低费,非 None 即
      通道池非空)∧ 席 ∧ 金 ≥ 最低费——核心在售即买,池非空故只查
      帧级资格(与 dominance 通道同款口径)。

    输入全为帧级现读/注册表量,零新自由参数;调用方装配候选 cost 列表
    (缺员/囤分支/配对),判定尺只做通道合取判定。
    """
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        mandate,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.shop import (
        check_settlement_line,
    )

    seat_ok = bench_free > 0 or seat_recoverable
    # ① dominance 1★ 净 0(资格门单源直调 + 结算线 单一源
    # check_settlement_line 直调,最便宜 1★ 形态;审查H2 修)
    if mandate.dominance_buy_eligible(gold, bench_free, cap_resolved) \
            and check_settlement_line(gold, 1, g_star)[0]:
        return True
    # ② 义务 M2:缺员(0→1)与分支①囤分支(1→2)同通道两形态
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
    # ⑤ 序 2 场况插件(通道集重建;插件件落 bench——席位维
    # = seat_ok;席满帧的置换路径由 seat_recoverable 分支承载)
    if plugin_budget_open and seat_ok:
        return True
    # ⑥ 序 4 压牌库分支(②(b) 死金/档 1/M6/垫件的帧级可达;席位维 =
    # 至少一席可落——席满帧置换拒后无买入即无通道)
    if order4_zone_open and (bench_free >= 1 or seat_recoverable):
        return True
    # ⑦ C1 恒买邻位(核心在售即买;池非空只查帧级资格)
    return (c1_floor_cost is not None and seat_ok
            and gold >= int(c1_floor_cost))
