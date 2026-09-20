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
  排程判据 = ``schedule_upgrade`` 确定性费用查表核(批 3 预算收权,
  W615 §1.3 R4 规则集;原 DP 姿态 level_up 供给退役);升级费逐帧现读
  (state.level_up_cost OCR 优先,缺省 XP_CLICK_COST_FLAT;W481 A-4:
  不用粗估表)。
- **C_t 通道容量**(结构上限,由既有层逐帧算出):升级计划费 +
  可买非期权件账(bench 余量约束)+ 刷价×刷新预算(refresh_ev_budget
  预算式,值域 [0,6])。
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

分包期 0b(§3.3-①a/①b):两接缝(schedule_upgrade/refresh_ev_budget)
与其依赖族(reserve_cap/upgrade_plan_fee/_registry_of/is_emergency/
_vd_core_of/REFRESH_ROLL_CAP/储备窗口常数)下沉 kernel 桶 cw_economy(物理居包根,期 1 归位)
(原 kernel→decision 断环边:cw_economy.get_node_goal 标量投影体内懒
import 决策包)。本模块只余容量/义务核算层;接缝符号在函数内懒 import
自 cw_economy——monkeypatch 桩点重钉至 cw_economy 符号后,属性动态
解析保证拦截语义不变。

P2 刷新容量 12 < 收入 13-19 的扩容评估 = 披露面(判读层义务帧兑现率
分布),本模块不改刷新帽(设计 §4 风险声明③)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sr_od.application.currency_war.kernel.cw_economy import (
    refresh_cost_effective,
    reserve_cap,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_entries_of,
    bench_free_slots,
    deployed_rows_of,
    gold_of,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


def _crosses_engine_tier(gs: GameState, name: str) -> bool:
    """店内件「当帧跨档」判定(结构性:买入后四体系达成数 +1)。

    判据单一源=cw_deploy_logic.engines_count(与 deploy/形态维同一把
    尺);板面羁绊计数取 state.board,候选贡献经 CHARACTERS 阵营/流派
    ∩ TRANSITION_TRAITS(与 scoring._cand_system_bonds 同口径)。
    A-1 刀法:仅此判定为真的件计入容量,未跨档期权件(q<1,`w469_convergence_ab/`
    已实测死法)不计。"""
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        TRANSITION_TRAITS,
        engines_count,
    )
    ch = CHARACTERS.get(name)
    if ch is None:
        return False
    bonds = set(ch.factions or ()) | set(ch.flows or ())
    fac = dict(gs.board.value or {})
    if not (bonds & {b for b, _t in TRANSITION_TRAITS}):
        return False
    front, back = deployed_rows_of(gs)
    dep_names = {d.char_id for d in (*front, *back) if d is not None}
    before = engines_count(fac, dep_names)
    for b in bonds:
        fac[b] = fac.get(b, 0) + 1
    after = engines_count(fac, dep_names)
    return after > before


def _scan_shop_buy_accounts(gs: GameState,
                            registry: DecisionV2Registry,
                            ) -> tuple[list[int], list[int]]:
    """店内件两路账单单次扫描(防双计;调用方按需取路)。

    - countable:非期权正账件费用(A-1 刀法:当帧跨档 ∪ 3合1 合成,
      合成件不占槽);
    - fill:O1 备战空位填补件费用(其余件;A-2 同一槽位账——槽位
      先扣跨档件已占数,满槽后不再扩账);升序返回(容量口径取最便宜
      k 件=保守侧,买入质量序在 candidates/scoring 放行面)。
    """
    costs: list[int] = []
    fill: list[int] = []
    from sr_od.application.currency_war.kernel.cw_economy import card_cost
    from sr_od.application.currency_war.kernel.cw_merge_simulate import (
        will_merge_on_buy,
    )
    _entries = bench_entries_of(gs)
    _payload_cards = shop_payload_content_cards(gs.shop.value)
    # 席空数 = 定长容量基线 − 占席条目数(容器 kind 口;未观察 = 全空,
    # registry.bench_capacity 基线口径零漂移——容量改写语义差异与
    # e_rounds 同挂设计裁定)
    _free_raw = bench_free_slots(gs)
    bench_free = (registry.bench_capacity if _free_raw is None
                  else max(0, int(_free_raw)))
    front, back = deployed_rows_of(gs)
    _deployed_units = [d for d in (*front, *back) if d is not None]
    for sc in _payload_cards:
        name = getattr(sc, 'name', '') or ''
        if not name:
            continue
        merge = will_merge_on_buy(sc, _entries, _deployed_units)
        if merge:
            costs.append(card_cost(sc))   # 合成件不占槽
            continue
        if bench_free <= 0:
            continue    # A-1/A-2:未跨档期权件与满槽帧均不扩账
        bench_free -= 1
        if _crosses_engine_tier(gs, name):
            costs.append(card_cost(sc))
        else:
            fill.append(card_cost(sc))
    fill.sort()
    return costs, fill


def _countable_buy_costs(gs: GameState, session: StrategySession | None,
                         registry: DecisionV2Registry) -> list[int]:
    """店内「非期权」正账件费用表(A-1 刀法)。

    countable = ①当帧跨档完成件(买入后四体系达成数 +1)∪ ②3合1
    合成件(买入即 2★ 完成,价值在星级阶梯非板面差分)。原配对信号
    (ADR-0446)退回后,跨档判定改本结构性口径——语义与 S1/S2 的
    「当帧跨档」同一集合(信号判定的核心即此跨档事实)。
    """
    return _scan_shop_buy_accounts(gs, registry)[0]


def bench_fill_account(gs: GameState, registry: DecisionV2Registry) -> int:
    """O1 备战空位填补通道的容量分量(`w611_econ_cycle/` 设计 §1.2/§1.3)。

    溢余帧备战有空位时,店内其余件(非跨档非合成)按费用升序取「剩余
    空槽」件的费用和计入 C_t——义务在「无目标帧」的容量不再结构性为
    0(局20/局23 支出冻结的根:comp 空→正 EV 帧空→C_t=0→义务恒 0)。
    数学依据=设计 §1.3:溢余段买 1★ 退全款+利息不减(息帽截断),
    已实现成本 0、收益≥0(压库+bench 期权),弱占优、参数无关。
    买入放行面([31] 限域质量序)在 candidates/scoring,随 `w607_affix_consumption/` 二波
    后接线;本分量先接通 flip/义务预算的容量判定与存息准入门。
    """
    return sum(_scan_shop_buy_accounts(gs, registry)[1])


def channel_capacity(gs: GameState, session: StrategySession,
                     registry: DecisionV2Registry) -> int:
    """C_t = 升级计划费 + 非期权可买账 + 刷价×刷新预算。

    刷新分量取 ``refresh_ev_budget`` 预算式(查表核单一址,预算收权
    批 ADR-0465;合法 0 帧契约见该函数 docstring)。接缝符号懒 import
    自 kernel 侧 cw_economy(局部别名绑定):monkeypatch 桩点重钉至
    cw_economy 符号后经属性访问动态解析,拦截语义不变。
    """
    from sr_od.application.currency_war.kernel import cw_economy as _ke
    total = 0
    if _ke.schedule_upgrade(gs, session):
        total += _ke.upgrade_plan_fee(gs)
    total += sum(_countable_buy_costs(gs, session, registry))
    total += bench_fill_account(gs, registry)
    rolls = _ke.refresh_ev_budget(gs, session)
    total += refresh_cost_effective(None, 0, gs=gs) * rolls
    return total


def overflow(gs: GameState, session: StrategySession) -> int:
    """溢余段 (g − R*)+(义务压力的原料;≤0 = 无义务帧)。

    R* 单一源 = kernel cw_economy.reserve_cap(模块级 import:纯查表
    函数,无桩点契约;守息线分量已归一 session resolved 链,registry
    旋钮不再辖本缝——ADR-0598)。"""
    return max(0, gold_of(gs) - reserve_cap(gs, session))


def obligation(gs: GameState, session: StrategySession,
               registry: DecisionV2Registry) -> int:
    """义务花销 f = min((g − R*)+, C_t)(设计 §1.4;0=无义务)。"""
    r = overflow(gs, session)
    if r <= 0:
        return 0
    return min(r, channel_capacity(gs, session, registry))


def tier_truncated_spend(gold: int, want: int, essential: bool) -> int:
    """溢余消费的息档边界截断(纯金额;`w645_proposal_v2/` 提案 E-v2)。

    利息 = gold//10 cap 5,按节点结算,当轮息损 = interest(轮初金) −
    interest(轮末金),首末金量的纯函数、路径无关 → 花后不跨 10 的倍数
    档则息损 0(P13/[11] 同档零息损)。本函数按「息档结构直接输出
    ``gold % 10``」截断非必要溢余支出金额,零标定参数(数学先行硬门的
    合格形态)。

    - essential=True → 不截断,原样返回 want。两枝由消费点显式分类:
      ①正账件(跨档/合成件,买账已过 scoring 单一裁决面)——一张牌
      不可拆,截断即弃购,弃购代价归 P1 再遇窗口口径,不在本函数辖内;
      ②M-A 定向刷新车道(arbiter 定向授权分支,directed_refresh_budget,
      P1 末窗/boss 窗)——末窗没有下轮重摇,截断后残差不足一刷 = 定向
      搜索永久丢失,截断代价是无穷大而非「推迟一轮」,弱占优前提对该
      车道为假。函数自身不判车道(车道判定单一址留在 arbiter 分支结构)。
    - essential=False(常态刷新逐笔、release 预算内的负分搜索等非必要
      溢余支出)→ 截断为 min(want, gold % 10):花后不跨息档,息损 0;
      不花的余量结转下轮(义务逐帧重算,R* 与 C_t 下帧重出,结转零成本、
      不产生第二义务)。

    调用契约:返回值 < want = 本笔不放行(消费不可拆,不花部分金额,
    也不替调用方改写金额)——截断只裁「可不可花满」,放行裁决仍在既有
    预算门(authorize_release_refresh 等);量级按严口径 1 金/档报
    1-2 金/局,主判如实降级「方向披露」(提案 E-v2 §2 量级双口径)。
    """
    if essential:
        return want
    return min(want, gold % 10)


def disclose_budget(state: Any, session: StrategySession,
                    registry: DecisionV2Registry | None = None) -> None:
    """预算现算 + 遥测披露面写点(合并体;T-88 决策环数据流断链修复,
    裁决 = ADR-0571;算值直写披露字段)。

    装配纪律(派生值不落 session)的立法目的 = 根治**决策输入**读跨帧
    旧共享态的污染类缺陷;本写点四字段 + 键戳是**遥测披露面**,不入
    决策输入——决策输入 = obs(黑板)+ session 容器直读,披露面字段
    禁决策消费(语义锚 = mandate_state.py 披露字段注释与守卫锁
    test_cw_budget_disclosure;禁令防线 = review 与代码规范:禁读约束
    已申报于本包模块 docstring)。写端只有本函数与商店执行回执位
    (operations/cw_screen/cw_screen_buy_cards.accrue_release_spent,
    只累计 spent);读端 = recorder sess_* 透传(telemetry/schema.py
    sess_reserve_cap 族)+ cw_decision_trace 披露族封闭清单
    (kernel/cw_decision_trace.py)。

    逐字段语义(合并验收锚):
    - ``state``:session 容器单例(帧轴 plane/round 与金读的单一来源;
      None = 缺省取 ``game_state_of(session)``,店开帧调用通道);
    - reserve_cap/obligation:现算值幂等覆写(同帧同值,重入无副作用);
    - overflow:``max(0, gold − reserve_cap)`` 纯派生直算——禁二次调
      ``economy_cycle.overflow``(其内部再调 reserve_cap,双算分叉面);
    - 键戳 (plane, round) 变更 ⇒ spent/reason 轮界清零后盖新戳:与
      schema「sess_release_spent 每轮入口清零」「sess_release_reason
      当轮义务来源」两契约对齐(F5 裁决二选一之①:reason 并入键戳
      清零块,杜绝跨轮陈读);不复用 v3_release_round(W332b 旧轮语义);
      同键重入不清 spent;
    - ``registry``:P6 注入单源(W636 A)——各接缝消费同一 registry
      实例,None → DEFAULT_REGISTRY(禁混用 state_of(session).
      v3_registry 死通道)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        reserve_cap,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of,
        gold_of,
        plane_of,
        round_num_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.economy_cycle import (
        obligation,
    )
    reg = registry or DEFAULT_REGISTRY
    gs = state if state is not None else game_state_of(session)
    st = state_of(session)
    key = (plane_of(gs), round_num_of(gs))
    if st.v3_disclosure_key != key:
        st.v3_release_spent = 0
        st.v3_release_reason = ''
        st.v3_disclosure_key = key
    cap = int(reserve_cap(gs, session))
    st.v3_reserve_cap = cap
    st.v3_reserve_overflow = max(0, gold_of(gs) - cap)
    st.v3_release_budget = int(obligation(gs, session, reg))


def disclose_budget_at_shop_frame(state: Any, session: StrategySession,
                                  registry: DecisionV2Registry | None = None,
                                  ) -> None:
    """店开观察帧披露覆写(T-88 双写语义第二写点;ADR-0571 §2.2)。

    备战决策入口披露帧处于关店态,F2 门(cw_screen_prep:gold 仅店开态
    可信,关店读空)使披露态 gold 不可得(缺省 0)⇒ overflow/obligation
    在 prep 帧恒 0——「金未采」已知语义,非真 0(实机首局
    g_20260907_025608 锚⑤定谳)。本写点在商店入口观察帧(店开,gold
    过 F2 门为真值)走同一现算链重算并覆写三预算字段:
    overflow/budget 变帧现值;键戳同轮 ⇒ 不清 spent(轮界清零由键戳
    承载,本写点只比较不盖戳)。豁免面与「禁决策消费」禁令同
    ``disclose_budget``;调用方 = operations/cw_screen/cw_screen_buy_
    cards 段顶(best-effort,失败降级保留 prep 值)。
    """
    disclose_budget(state, session, registry)
