r"""经济循环总模型:储备制(R*/义务/通道容量)(ADR-0445)。

设计=唯一规格:`.debug/temp/currency_war/w471_economy_cycle/DESIGN.md`
(W481 对抗审计修复项 A-1/A-2 内建)。核心语义:金账从「地板制」(只
规定花后下限)改为「储备制」——任何时刻金 g 与储备上限 R* 的差
``(g − R*)+`` 是负有转化义务的死钱,每轮必须经三条转化通道(升级/
刷新/买牌)之一转成战力,义务 = max(既有臂义务, min(溢余, C_t))。

- **R\* = 息线 + 窗口(≤3 轮)排程升级费**:息线(50)以内持有弱占优
  (0.1/轮 无风险收益 vs 战力链 ≤0.012,ADR-0443 同一笔账反向使用);
  排程升级是价格/时点已知的确定性转化,为其持金不是死钱。窗口 h =
  min(3, 到本位面末节点轮数)——h>3 的升级应即时执行而非长期储蓄。
  排程判据=DP 姿态 level_up(ev.round_posture 单一源);升级费逐帧现读
  (state.level_up_cost OCR 优先,缺省 XP_CLICK_COST_FLAT;W481 A-4:
  不用粗估表)。
- **C_t 通道容量**(结构上限,由既有层逐帧算出):升级计划费 +
  可买非期权件账(bench 余量约束)+ 刷价×min(6, DP 授权刷数)。
  **A-1 修复**:formation_gold_account 对未跨档件给
  ``d_rem × engine_jump_gold`` 的正账是「按兑现价卖期权」(W469 已
  实测死法),这类期权件**不计入容量**——容量只计当帧跨档件
  (买入后四体系达成数 +1,``_crosses_engine_tier`` 结构性判定)与
  3合1 合成件(买入即 2★ 完成);**A-2 修复(声明+约束)**:每买
  一件占一个 bench 槽,槽位是下一轮跨档件的物理前置——容量按 bench
  空槽逐件扣减计入该机会成本(合成件净腾槽不占)。
- **义务帧兑现**:release 臂(posture_release)消费 overflow/obligation
  作为预算下界;g≥0 硬钳制在 authorize_release_refresh(W477 披露的
  执行层透支修复)。
- **息基守卫收窄**:息线以内的常态帧(g≤R*)行为零漂移(义务只在
  溢余段激活;I-1 锚)。

P2 刷新容量 12 < 收入 13-19 的扩容评估 = 披露面(判读层义务帧兑现率
分布),本模块不改刷新帽(设计 §4 风险声明③)。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)

#: 储备窗口上界(轮;设计 §1.3:h = min(到下一 boss 节点轮数, 3)——
#: 更远的排程升级应即时执行而非长期储蓄,结构界非拍值)。
RESERVE_WINDOW_ROUNDS: int = 3

#: 刷新通道容量上界(刷数;cw_horizon._ACTION_ROLLS 的 DP 上限 6 刷
#: 同源,不另造第二把尺)。
REFRESH_ROLL_CAP: int = 6


def _upgrade_scheduled(state: GameState, session: StrategySession) -> bool:
    """排程升级判据(DP 姿态 level_up 单一源;None=DP 不可达,保守 False)。"""
    return schedule_upgrade(state, session)


def schedule_upgrade(state: GameState, session: StrategySession) -> bool:
    """排程升级判据(蓝图 §3.4 R4 可替换接缝;公开纯函数)。

    消费方接口形状 = 布尔判据;现役实现 = DP 姿态 level_up 单一源,
    未来换排程查表时只改本函数体,消费方不变。
    """
    from sr_od.application.currency_war.decision_v2.ev import round_posture
    posture = round_posture(state, session)
    return posture is not None and bool(getattr(posture, 'level_up', False))


def refresh_ev_budget(state: GameState, session: StrategySession) -> int:
    """刷新 EV 授权刷数(蓝图 §3.4 R4 可替换接缝;公开纯函数)。

    现役实现 = DP 姿态 refresh_budget 单一源;DP 不可达/无授权 → 0
    (保守侧:容量缩、义务缩)。未来换单步 EV 计算时只改本函数体。
    """
    from sr_od.application.currency_war.decision_v2.ev import round_posture
    posture = round_posture(state, session)
    if posture is None:
        return 0
    return int(getattr(posture, 'refresh_budget', 0) or 0)


def upgrade_plan_fee(state: GameState) -> int:
    """下一级升级总费(逐帧现读:OCR 单击价优先,缺省 flat 常量)。"""
    from sr_od.application.currency_war.cw_horizon import clicks_to_level
    from sr_od.application.currency_war.cw_state import (
        XP_CLICK_COST_FALLBACK,
    )
    click = state.level_up_cost or XP_CLICK_COST_FALLBACK
    return clicks_to_level(state.level) * click


def _rounds_to_plane_end(state: GameState, session: StrategySession) -> int:
    """到本位面末节点(= boss 节点)的剩余轮数(含当前轮;缺读兜底 0
    =不储蓄,保守侧:R* 退化为息线,义务面变宽但方向安全)。"""
    from sr_od.application.currency_war.cw_horizon import nodes_of_plane
    try:
        total = nodes_of_plane(session)
    except Exception:
        return 0
    return max(0, total - state.round_num)


def reserve_cap(state: GameState, session: StrategySession,
                registry: DecisionV2Registry) -> int:
    r"""R\*(t) = interest_floor + Σ 窗口内排程升级费(设计 §1.3)。

    窗口 h = min(3, 到本位面末节点轮数);只储蓄下一级费用——多级
    排程在逐帧重算下自愈(升级完成一轮后 R* 自然滚动到下一级;W481
    A-4:误估最坏=一个升级费量级 ≤50 金,双向有界)。

    守息线取 `interest_cap × 10`(息帽同源派生,W611 §2.2 恒等式):
    基参数下 5×10=50==interest_floor,行为零漂移;写法保证「守息线
    ≤ 封顶线」结构性成立——两者同源,不可能出现守息线高于持有增益
    归零点(息帽截断点)的态。策略级息帽 override(interest_cap_override)
    走 ledger/DP 通道,registry 息帽与之分离时以封顶线为准(设计 §2.2
    规则原文);分离面=已知缺口,如实挂账。
    """
    h = min(RESERVE_WINDOW_ROUNDS,
            _rounds_to_plane_end(state, session))
    floor = registry.interest_cap * 10
    if h <= 0 or not _upgrade_scheduled(state, session):
        return floor
    return floor + upgrade_plan_fee(state)


def overflow(state: GameState, session: StrategySession,
             registry: DecisionV2Registry) -> int:
    """溢余段 (g − R*)+(义务压力的原料;≤0 = 无义务帧)。"""
    return max(0, (state.gold or 0) - reserve_cap(state, session, registry))


def _crosses_engine_tier(state: GameState, name: str) -> bool:
    """店内件「当帧跨档」判定(结构性:买入后四体系达成数 +1)。

    判据单一源=cw_deploy_logic.engines_count(与 deploy/形态维同一把
    尺);板面羁绊计数取 state.board,候选贡献经 CHARACTERS 阵营/流派
    ∩ TRANSITION_TRAITS(与 scoring._cand_system_bonds 同口径)。
    A-1 刀法:仅此判定为真的件计入容量,未跨档期权件(q<1,W469
    已实测死法)不计。"""
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    from sr_od.application.currency_war.cw_deploy_logic import (
        TRANSITION_TRAITS,
        engines_count,
    )
    ch = CHARACTERS.get(name)
    if ch is None:
        return False
    bonds = set(ch.factions or ()) | set(ch.flows or ())
    fac = dict(state.board or {})
    if not (bonds & {b for b, _t in TRANSITION_TRAITS}):
        return False
    dep_names = {d.char_id for d in (state.deployed or []) if d is not None}
    before = engines_count(fac, dep_names)
    for b in bonds:
        fac[b] = fac.get(b, 0) + 1
    after = engines_count(fac, dep_names)
    return after > before


def _scan_shop_buy_accounts(state: GameState,
                            registry: DecisionV2Registry,
                            ) -> tuple[list[int], list[int]]:
    """店内件两路账单单次扫描(防双计;调用方按需取路)。

    - countable:非期权正账件费用(A-1 刀法:当帧跨档 ∪ 3合1 合成,
      合成件不占槽);
    - fill:O1 备战空位填补件费用(其余件;A-2 同一槽位账——槽位
      先扣跨档件已占数,满槽后不再扩账);升序返回(容量口径取最便宜
      k 件=保守侧,买入质量序在 candidates/scoring 放行面)。
    """
    from sr_od.application.currency_war.cw_state import (
        bench_occupied,
        will_merge_on_buy,
    )
    costs: list[int] = []
    fill: list[int] = []
    bench_free = max(0, registry.bench_capacity
                     - bench_occupied(state.bench or []))
    for sc in (state.shop or []):
        name = getattr(sc, 'name', '') or ''
        if not name:
            continue
        merge = will_merge_on_buy(sc, state.bench, state.deployed)
        if merge:
            costs.append(sc.cost or 3)   # 合成件不占槽
            continue
        if bench_free <= 0:
            continue    # A-1/A-2:未跨档期权件与满槽帧均不扩账
        bench_free -= 1
        if _crosses_engine_tier(state, name):
            costs.append(sc.cost or 3)
        else:
            fill.append(sc.cost or 3)
    fill.sort()
    return costs, fill


def _countable_buy_costs(state: GameState, session: StrategySession | None,
                         registry: DecisionV2Registry) -> list[int]:
    """店内「非期权」正账件费用表(A-1 刀法)。

    countable = ①当帧跨档完成件(买入后四体系达成数 +1)∪ ②3合1
    合成件(买入即 2★ 完成,价值在星级阶梯非板面差分)。原配对信号
    (ADR-0446)退回后,跨档判定改本结构性口径——语义与 S1/S2 的
    「当帧跨档」同一集合(信号判定的核心即此跨档事实)。
    """
    return _scan_shop_buy_accounts(state, registry)[0]


def bench_fill_account(state: GameState, registry: DecisionV2Registry) -> int:
    """O1 备战空位填补通道的容量分量(W611 设计 §1.2/§1.3)。

    溢余帧备战有空位时,店内其余件(非跨档非合成)按费用升序取「剩余
    空槽」件的费用和计入 C_t——义务在「无目标帧」的容量不再结构性为
    0(局20/局23 支出冻结的根:comp 空→正 EV 帧空→C_t=0→义务恒 0)。
    数学依据=设计 §1.3:溢余段买 1★ 退全款+利息不减(息帽截断),
    已实现成本 0、收益≥0(压库+bench 期权),弱占优、参数无关。
    买入放行面([31] 限域质量序)在 candidates/scoring,随 W607 二波
    后接线;本分量先接通 flip/义务预算的容量判定与存息准入门。
    """
    return sum(_scan_shop_buy_accounts(state, registry)[1])


def channel_capacity(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry,
                     posture=None) -> int:
    """C_t = 升级计划费 + 非期权可买账 + 刷价×min(6, DP 授权刷数)。

    ``posture``:调用方已有的 DP 姿态(避免重查);None 时内部现查。
    刷新分量取 DP refresh_budget(既有 DP 层逐帧算出的授权刷数,
    单一源;设计 §1.2「C_t 由既有 DP/评分层逐帧算出」)。DP 不可达
    时刷新分量计 0(容量缩→义务缩,保守方向)。
    """
    from sr_od.application.currency_war.decision_v2.ev import round_posture
    if posture is None:
        posture = round_posture(state, session)
    total = 0
    if posture is not None and getattr(posture, 'level_up', False):
        total += upgrade_plan_fee(state)
    total += sum(_countable_buy_costs(state, session, registry))
    total += bench_fill_account(state, registry)
    if posture is not None:
        rolls = min(REFRESH_ROLL_CAP,
                    int(getattr(posture, 'refresh_budget', 0) or 0))
        total += (state.shop_refresh_cost or 2) * rolls
    return total


def obligation(state: GameState, session: StrategySession,
               registry: DecisionV2Registry, posture=None) -> int:
    """义务花销 f = min((g − R*)+, C_t)(设计 §1.4;0=无义务)。"""
    r = overflow(state, session, registry)
    if r <= 0:
        return 0
    return min(r, channel_capacity(state, session, registry, posture))
