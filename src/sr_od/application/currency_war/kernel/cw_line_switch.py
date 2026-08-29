"""换线判据:E_rounds 比较 + θ 滞回 + D_min 驻留(DESIGN §③)。

设计=唯一规格:`.debug/temp/currency_war/w328_unformed_posture/DESIGN.md` §③。
核心公式(候选线 c,候选集=过渡引擎池方向):

    distance(c) = need(c) − held(c) − shelf(c)   # 需求张数 − 持有 − 货架可见可买
    E_rounds(c) ≈ distance(c) / per_round(c)
    per_round(c) = (1 + 可负担刷次数) × p̄(c, lv) # 自然刷 1 次/轮 + 买刷;截断到 bench 空位

p̄ 同超几何模型(cw_shop_odds P5 表实值;同 ``ev_proto.p_at_least_one`` 构型:
每格独立,P(格=该费用)=p;给定 m 格该费用,P(至少一张目标)=1−C(同费非
目标,m)/C(同费总,m))。**p̄ 乐观偏差**:理论满池值未扣 NPC 消耗/争夺,
系统性偏乐观 10-20%——判据先修偏再比较:双线 E_rounds 同乘 (1+δ)
(registry.line_switch_debias_delta,默认 0.15),θ(registry.line_switch_theta,
默认 1.0 轮)只承载去偏后的剩余噪声(DESIGN §③修订 1-2)。

切换条件(滞回 + 驻留):

    E_rounds(alt)×(1+δ) + θ < E_rounds(cur)×(1+δ)  且 当前线驻留 ≥ D_min=2

(D_min 压振荡频率硬上限至 1/(2·D_min);退化情形双 inf → 维持原线。)

与 drought bail 的关系(DESIGN §附4):**或-并存**——E_rounds 比较为主判据,
N=5 连续 shop_supply<1.0 的经验观测保留为独立旁路(drought_excluded 死线
名单语义不变):E_rounds=inf 是静态池数学,检测不了「理论可达、实测断供」
的线,后者只有经验观测能测;两路任一触发即弃线。

切换成本:1★ 卖出全额退成本(cw_state.sell_refund)→ 凑齐羁绊前换线近乎
零成本,唯一真实成本=2★ 已合成件折价(−1 金)与 bench 机会成本;D_min 之外
无需额外切换税(DESIGN §③)。辖域=位面前中段;末窗禁换是设计内辖域声明
(末窗的线选择由投影血量判据下的找件 EV 接管)。
"""
from __future__ import annotations

import math

from sr_od.application.currency_war.kernel.cw_comps import Comp
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.kernel.cw_strategy_session import StrategySession


def char_has_tag(ch, tag: str) -> bool:
    """板面标签 = 阵营(factions)∪ 流派(flows)的并集(outcomes board 口径)。"""
    return tag in (getattr(ch, 'factions', None) or ()) \
        or tag in (getattr(ch, 'flows', None) or ())


def p_bar_faction(tag: str, level: int) -> float:
    """p̄:单次刷新至少出 1 张「该标签(阵营∪流派)」件的概率(超几何)。

    多标签联合分布按标签独立取(DESIGN §附5 诚实列表:联合概率高估,
    设计内承认的近似)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.data.cw_shop_odds import (
        DISTINCT_CARDS_PER_COST,
        POOL_COPIES_PER_CARD,
        REFRESH_PROB,
    )
    names = [n for n, ch in CHARACTERS.items()
             if getattr(ch, 'cost', 0) and char_has_tag(ch, tag)]
    if not names:
        return 0.0
    costs = sorted({ch.cost for ch in CHARACTERS.values()
                    if char_has_tag(ch, tag)})
    p_hit_once = 0.0
    shop_slots = 5    # cw_shop_odds.SHOP_SLOTS
    for cost in costs:    # 费用档互斥,可加
        p_cost = REFRESH_PROB.get(level, {}).get(cost, 0.0)
        if p_cost <= 0:
            continue
        a = POOL_COPIES_PER_CARD.get(cost, 9)
        v = DISTINCT_CARDS_PER_COST.get(cost, 13)
        total = v * a
        a_tgt = len([n for n in names
                     if CHARACTERS[n].cost == cost]) * a
        if a_tgt <= 0:
            continue
        for m in range(1, shop_slots + 1):
            if m > total:
                continue
            p_m = math.comb(shop_slots, m) * p_cost ** m \
                * (1 - p_cost) ** (shop_slots - m)
            p_none = (math.comb(total - a_tgt, m) / math.comb(total, m)
                      if total - a_tgt >= m else 0.0)
            p_hit_once += p_m * (1 - p_none)
    return min(1.0, p_hit_once)


def line_distance(comp: Comp, state: GameState) -> int:
    """distance(c) = need − held − shelf(需求张数 − 持有 − 货架可见可买)。

    held 取 board(场上)对阵营档位的占有(超档不计);shelf=本回合 shop
    中「缺档阵营」的可见件数(买走即 held,不计入刷出期望)。
    """
    tiers = getattr(comp, 'form_tiers', None) or {}
    if not tiers:
        return 0
    board = state.board or {}
    need = sum(tiers.values())
    held = sum(min(t, board.get(f, 0)) for f, t in tiers.items())
    shelf = 0
    for c in (state.shop or []):
        f = getattr(c, 'faction', '') or ''
        if f in tiers and board.get(f, 0) < tiers[f]:
            shelf += 1
    return max(0, need - held - shelf)


def e_rounds(comp: Comp, state: GameState,
             registry: DecisionV2Registry | None = None) -> float:
    """E_rounds(c) ≈ distance / per_round(per_round 见模块注释)。

    distance=0 → 0.0(已完成);p̄=0(该等级刷不出)→ inf(静态不可达;
    「实测断供」归 drought bail 旁路,DESIGN §附4)。"""
    reg = registry or DEFAULT_REGISTRY
    dist = line_distance(comp, state)
    if dist <= 0:
        return 0.0
    from sr_od.application.currency_war.kernel.cw_state import (
        BENCH_CAPACITY,
        bench_occupied,
    )
    p = 0.0
    for f in (getattr(comp, 'form_tiers', None) or {}):
        # 标签独立并集:1−∏(1−p_f)(联合概率高估为设计内承认近似,见模块注释)
        p_f = p_bar_faction(f, state.level)
        p = p_f if p <= 0 else 1 - (1 - p) * (1 - p_f)
    if p <= 0:
        return math.inf
    cost = state.shop_refresh_cost or 2
    affordable = max(0, ((state.gold or 0) - reg.interest_floor()) // cost)
    bench_free = max(0, BENCH_CAPACITY - bench_occupied(state.bench or []))
    rolls = min(affordable, bench_free)    # 买刷截断到 bench 空位
    per_round = (1 + rolls) * p
    return dist / per_round


def switch_allowed(state: GameState, session: StrategySession) -> bool:
    """辖域门:位面前中段可换;末窗禁换(设计内辖域声明,DESIGN §③)。

    末窗=本位面末 3 轮(9 轮位面即 r≥7;7 轮位面 P2 即 r≥5)——末窗换线
    = 丢弃已成形板面战力追 0-progress 新线,且 D_min=2 驻留在末窗等价于
    禁换;真值源=``cw_plane_table.nodes_of_plane``(位面轮数,ADR-0366)。
    """
    from sr_od.application.currency_war.kernel.cw_plane_table import nodes_of_plane
    return state.round_num <= nodes_of_plane(session) - 3


def should_switch_e(e_cur: float, e_alt: float, dwell_rounds: int,
                    registry: DecisionV2Registry | None = None) -> tuple[bool, str]:
    """切换裁决(纯数):输入双线 E_rounds 与当前驻留轮数。

    返回 (是否切换, 理由串)。条件:E(alt)×(1+δ)+θ < E(cur)×(1+δ)
    且 dwell≥D_min;退化情形双 inf → 维持原线(理由 'both_inf');
    e_cur=inf 且 e_alt 有限 = 原线静态不可达,不等式恒真(仍受 D_min 辖)。
    """
    reg = registry or DEFAULT_REGISTRY
    if not math.isfinite(e_alt):
        return False, 'alt_inf'
    if math.isfinite(e_cur) and math.isfinite(e_alt):
        if e_cur <= 0:
            return False, 'cur_done'
    k = 1.0 + reg.line_switch_debias_delta
    lhs = e_alt * k + reg.line_switch_theta
    rhs = e_cur * k if math.isfinite(e_cur) else math.inf
    if not lhs < rhs:
        return False, 'theta'
    if dwell_rounds < reg.line_switch_min_dwell:
        return False, f'dwell({dwell_rounds}<{reg.line_switch_min_dwell})'
    return True, 'ok'


#: P2 位面节点模板(economy.md §10.2;表缺/位面锚不符时的投影回退):
#: [战斗, 战斗, 遭遇, 奖励, 遭遇, 奖励, 战斗, boss]——r7 实测表为「?」
#: 占位,按保守规则转战斗+normal 档(未知多算一的一场损失=存活估计更
#: 短=门更紧,保守方向显式声明,多局开局帧复核后改)。
_P2_NODE_TEMPLATE: list[str] = ['battle', 'battle', 'encounter', 'reward',
                                'encounter', 'reward', 'battle', 'boss']

_ZERO_LOSS_NODE_KINDS: frozenset[str] = frozenset({'reward', 'supply'})


def node_loss_kind(node_type: str) -> str:
    """节点型 → 损血档归一(单一源;C4 rounds_alive 投影唯一消费,
    registry.p2_cond_loss_table 同表分档)。boss/遭遇→同名档;奖励/补给→零损档(投影日历轮照走、
    损血 0);其余(普通战斗/精英/缺读/'?' 占位)→ normal 档——未知
    战斗节点按 normal 档(战斗频率最高档)、未知非战斗节点由调用方
    先归零损档,两类缺读不共用一个兜底。"""
    if node_type == 'boss':
        return 'boss'
    if node_type in ('encounter', 'encounter_v2', '遭遇'):
        return 'encounter'
    if node_type in _ZERO_LOSS_NODE_KINDS:
        return 'reward'
    return 'normal'


def _remaining_nodes(session: StrategySession,
                     state: GameState) -> list[str]:
    """本位面从当前轮起到位面末的节点型序列(C4 投影输入)。

    真值源=``session.plane_node_table``(r306 开局帧实读,每备战帧实时
    重写为权威;位面锚=``plane_node_table_plane``,ADR-0368);表缺/
    位面锚不符 → 回退 economy §10.2 位面模板(P2,见
    _P2_NODE_TEMPLATE 注释)。"""
    table = getattr(session, 'plane_node_table', None)
    if table and getattr(session, 'plane_node_table_plane', None) \
            == state.plane:
        seq = list(table)
    else:
        seq = list(_P2_NODE_TEMPLATE)
    start = max(0, int(state.round_num) - 1)
    return seq[start:]


def rounds_alive(state: GameState,
                 session: StrategySession,
                 registry: DecisionV2Registry | None = None) -> int:
    """存活轮数:剩余节点序列逐节点投影(设计=
    `.debug/temp/currency_war/w373_c3c4_redesign/REDESIGN.md` §3.2;
    旧 ceil(hp/等权均值) 除数口径已废除——两个期望时钟必须同一把尺,
    本函数与 E_rounds 同按日历轮计量)。

    语义=「从当前节点起、按日历轮走,到 hp 耗尽为止还能行动的节点数」:
    战斗节点扣条件损血、奖励/补给零损照走、遭遇节点加回血期望(默认
    0 下界,registry.encounter_heal_est);死在结算也先行动过这一轮
    (ra 先 +1 再判死)。hp≤0 → 0。复杂度 O(剩余节点 ≤9)×O(1) 查表。
    """
    reg = registry or DEFAULT_REGISTRY
    if not state.hp or state.hp <= 0:
        return 0
    # 两态口径(M1b,开关=registry.rounds_two_state_enabled,默认关=
    # 零漂移锚):loss=(1−p_win)·条件败面档;开关关或 rung 缺档按
    # p_win=0=每战全损 → loss=条件败面档常数(M1a)——同一份代码,
    # 行为由开关+注入切换(REDESIGN §3.3;幅度源=registry.
    # p2_cond_loss_table,与两态胜率映射(cw_plane_table.p_win_p2)/阈值层同一 registry 标定源,口径
    # 定稿见 ADR-0440;无条件期望表 p2_node_loss_table 是另一 estimand,
    # 消费面=阈值层 _loss_dist)。rung 取样坐标=cw_sim._settle_rung
    #(与 p_win 表的 W346 Δ池采样键同源,ADR-0279 单一源;deployed
    # 全集+星徽,0-2 钳制)——不用 scoring._engines_formed(混合域
    # 加权含 bench 折减项,坐标错位=p_win 偏乐观=门偏松,见
    # registry.p_win_p2_by_rung 注释)。板面过换线延续(引擎四体系
    # 跨线共享),当前板 rung 即新线起始 rung 下界;投影期内 rung
    # 演化(成型升档/卖件回落)未建模,静态取样偏差已声明。
    p_win = 0.0
    if reg.rounds_two_state_enabled and reg.p_win_p2_by_rung:
        from sr_od.application.currency_war.kernel.cw_battle_calib import _settle_rung
        rung = min(2, max(0, _settle_rung(state)))
        p_win = reg.p_win_p2_by_rung.get(rung, 0.0)
    h = float(state.hp)
    ra = 0
    for raw in _remaining_nodes(session, state):
        kind = node_loss_kind(raw)
        h -= (1.0 - p_win) * reg.p2_cond_loss_table.get(kind, 0.0)
        if kind == 'encounter':
            h += reg.encounter_heal_est   # 注入前恒 0(0 下界声明)
        ra += 1            # 日历轮 +1(死在结算也先行动过这一轮)
        if h <= 0:
            break
    return ra              # 走完全表仍 h>0 → ra=剩余节点数(跨位面截断)


def gate_need(state: GameState, session: StrategySession,
              e_alt: float,
              registry: DecisionV2Registry | None = None) -> float:
    """门阈值 need = e_alt×(1+δ) + 兑现余量(+boss CI 半宽,投影路径
    含 boss 节点时)。survival_gate 与反事实判定位(gate_counterfactual)
    的单一公式源——拆出防「门判定式与反事实记账式」双写漂移
    (W665 DESIGN v2 §2.1/R3:两处必须同一把尺,检查器禁第三处复算)。"""
    reg = registry or DEFAULT_REGISTRY
    need = e_alt * (1.0 + reg.line_switch_debias_delta) \
        + reg.line_switch_survival_margin
    if any(node_loss_kind(r) == 'boss'
           for r in _remaining_nodes(session, state)):
        need += reg.line_switch_boss_ci_halfwidth
    return need


def gate_counterfactual(state: GameState, session: StrategySession,
                        e_alt: float,
                        registry: DecisionV2Registry | None = None
                        ) -> bool:
    """反事实判定位 P(f) = [rounds_alive(state) < gate_need(state, e_alt)]
    (W665 DESIGN v2 R3:开臂机制判「反事实拦截精度」的记账真值源)。

    - off 臂(门关):对每次换线事件由 cw_intention._switch_gate_open
      计算并写 session 决策位落账本行;
    - on 臂(门开):**禁再调本函数**——该位即门判定本身
      (_switch_gate_open 直接取 survival_gate 结果,不重复算,守
      W659 攻击 6「检查器/记账双源失明」独立性纪律);
    - 消费面 = A/B 批器读账本行算拦截精度,**检查器禁复算本式**
      (cw_sim_checks 只做位一致性核验)。

    规格缺口标注(W683 攻击 3 核实 off 臂可执行,三处定义当前按合理
    选择落码、待 v3 确认):
    - 判定时点 = 换线事件帧的当帧评估(_switch_gate_open 评估点,每个
      换线辖域帧各记一位,账本行取本轮最后一次评估);
    - 窗口锚 = R/need 全取**当帧** state(含当帧 gold/bench_free 瞬态
      口径,与 FM-10 敏感带声明一致;近帧中位去敏属重标定挂账);
    - 估计量 = rounds_alive(M1a 下界投影)+ gate_need 同式,与 on 臂
      门判定严格同尺。
    """
    reg = registry or DEFAULT_REGISTRY
    if state.plane != 2:
        return False
    if not math.isfinite(e_alt):
        # E=inf = 新线永不完成,门不等式右端 inf,R≥inf 恒假 → 拦是判据
        # 式的直接读出(v3 R-E:拦截归属唯一化到本门;旧「上游已拦」
        # 声明经 W683 核实为假——v2 通道不调 should_switch_e)
        return True
    return rounds_alive(state, session, reg) \
        < gate_need(state, session, e_alt, reg)


def survival_gate(state: GameState, session: StrategySession,
                  e_alt: float,
                  registry: DecisionV2Registry | None = None
                  ) -> tuple[bool, str]:
    """换线存活轮数门(第三道门;registry.line_switch_survival_gate_enabled)。

    判据(REDESIGN §3.4;W665 DESIGN v2 §2.2 定性=方向性启发+fail-safe
    偏紧,非 EV 必要性证明):rounds_alive(剩余节点逐节点投影) ≥
    gate_need(E_rounds(新线))——投影后两边同为日历轮;δ 承载 p̄ 乐观
    先修偏,margin 承载兑现余量与投影近似残差,boss CI 半宽承载借档
    不确定性(registry.line_switch_boss_ci_halfwidth)。换线价值兑现在
    新线成型之后;存活轮数不足=新线永远到不了兑现点,换线期望 0<
    驻留旧线。与既有 θ 滞回/δ 先修偏/D_min 驻留同族串联,不是第二
    换线机制;drought bail 旁路不辖(或-并存结构不变)。

    辖域 plane==2(v3 R-G 收窄:损血表为 P2 标定,P1 不适用;P3 帧消费
    P2 表 → R 高估门偏松 FM-12,P3 扩辖待 p3_cond_loss_table 标定);
    开关关/辖域外 → 放行(零漂移)。e_alt=inf(v3 R-E 勘误,原「上游
    should_switch_e 已拦」声明经 W683 核实为假——v2 通道不调该函数):
    新线永不完成,门不等式右端 inf → **拦**('alt_inf'),拦截归属
    唯一化到本门,p̄=0 线由信号胜出不再落锁。
    """
    reg = registry or DEFAULT_REGISTRY
    if not reg.line_switch_survival_gate_enabled:
        return True, 'gate_off'
    if state.plane != 2:
        return True, 'gate_off'
    if not math.isfinite(e_alt):
        return False, 'alt_inf'
    ra = rounds_alive(state, session, reg)
    need = gate_need(state, session, e_alt, reg)
    if ra >= need:
        return True, 'ok'
    return False, f'survival({ra:.0f}<{need:.2f})'


def register_gate_block(session: StrategySession, cur_name: str,
                        alt_name: str) -> int:
    """拦截日志去重记账(REDESIGN §3.7):按 (当前线,备选线) 线对计
    同局拦截次数,返回累计次数。消费侧约定=次数为 1 时发日志行,>1
    只累加计数(防死锁局每轮刷屏);计数挂在 session(局终随会话销毁)。"""
    seen = getattr(session, 'line_switch_block_counts', None)
    if seen is None:
        seen = {}
        session.line_switch_block_counts = seen
    key = (cur_name, alt_name)
    seen[key] = seen.get(key, 0) + 1
    return seen[key]


def best_alt_line(state: GameState, session: StrategySession, config,
                  score_ctx, registry: DecisionV2Registry | None = None
                  ) -> tuple[object, float]:
    """候选集中 E_rounds 最小且有限的备选线((comp, e) ;无候选 → (None, inf))。

    候选集=select_comp_scored top-N(与选线同一来源,防另造排序);排除
    drought_excluded 死线(drought 名单语义保留)与供给为 0 的线(选线
    供给门同口径)。registry 注入(e_rounds 的金/刷价参数)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import (
        select_comp_scored,
        shop_supply,
    )
    reg = registry or DEFAULT_REGISTRY
    cur_name = session.target_comp.name if session.target_comp else ''
    excluded = set(getattr(session, 'drought_excluded', None) or ())
    best: tuple[object, float] = (None, math.inf)
    for _s, c in select_comp_scored(state, score_ctx, config, top_n=8):
        if c.name == cur_name or c.name in excluded:
            continue
        if shop_supply(c, state) <= 0:
            continue
        e = e_rounds(c, state, reg)
        if e < best[1]:
            best = (c, e)
    return best
