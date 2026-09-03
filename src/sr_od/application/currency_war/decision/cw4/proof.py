"""cw4 证明层(线选择与终局)——IMPL_DESIGN §6.4-R 步4,④-3 裁决四函数位。

规格单一源:
- IMPL_DESIGN §6.4-R R189-1 ④-3(证明层承载者=cw4/proof 四函数位全套新建,
  现役件只作对拍锚;decision_v2 属冻结基线臂,改造它=改基线);
- §2.7(换线 P16 + 停手线)+ §2.7.1(直通线入口注记七条);
- R192 修注(should_switch 新核臂调用形态钉死):参数解析序 =
  provisional【拟】槽位(THETA/D_MIN/δ 滞回)→ 解析成功:以解析实参调用
  ``kernel/cw_line_switch.should_switch_e`` 比较(比较器签名不加重载、
  文件本体零改动)→ θ/D_min/δ 任一 None:不评估 + ``theta_unavailable``
  分键计数(R24-2:禁复用 switchline_skipped/switchline_exit_blocked——
  归因三因[臂①旁路/出口不可用/判据未标定]可辨);
- R10-5/R9-2/R11-1(stop_buy=「当前线 K 成型」纯分类谓词,逐备战期
  证明 pass 后重评,评估对象恒为该帧生效 K);
- 修复池 D-A45(干旱计数器事件语义:买入目标件即重置;撤线前先核手上
  目标件存量)+ D-P4(切线滞回)——共根组 3「线级状态机事件集」的
  cw4 侧载体(事件/滞回字段集中于本模块 ``LineState``,各判据共用)。

计数载体:``session.cw4_counters``(dict,bridge 每局创建;键登记见
design_telemetry 键节——本模块产键:theta_unavailable / switchline_skipped /
switchline_exit_blocked / switchline_no_alt / switchline_no_target /
switchline_e_cur_undefined / switchline_relock_window[R196 修复批:
「不换线也记遥测」的归因分键补齐——四路 return 原先零计数])。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.decision.cw4.audit import provisional
from sr_od.application.currency_war.decision.cw4.statefn import predicates
from sr_od.application.currency_war.decision.cw4.statefn.vopt import p_complete
from sr_od.application.currency_war.kernel import cw_line_switch

if TYPE_CHECKING:
    from sr_od.application.currency_war.decision.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.kernel.cw_state import Comp, GameState

# 直通线信号谱(§2.7.1 注记 1:开局信号=证明层输入,obs 层登记)。
# 当前可判定的信号载体 = session.active_strategies(投资策略 handler 写端,
# kernel/cw_strategy_session.py 写入先例)——「黑塔纪元」系①类策略驱动
# 信号(改写牌库结构,A3 分层表)。其余信号(圣杯/万敌/昼神)的观测面
# (契约/数量/速度流)在 obs 层尚无实体字段,登记为待接线(检查点呈报,
# 见 STEP34_REPORT 解释性裁量清单)。
DIRECT_LINE_SIGNAL_STRATEGIES: tuple[str, ...] = ('黑塔纪元',)


@dataclass
class LineState:
    """线级状态机(共根组 3):事件集与滞回字段的单一源。

    字段坐标系/取值时机:
    - ``k_name``:当前生效目标线名(session.target_comp 的 comp 名投影,
      证明 pass 每帧现读比对,变化时 dwell 清零——R1-3:K 变更下一备战期
      生效由 entry 只登记不翻转承载);
    - ``dwell``:当前线驻留轮数(证明 pass 逐帧 +1,K 名变化时归 0);
    - ``drought``:目标件干旱计数(D-A45):每证明 pass「手上(板∪bench)
      目标线件存量 = 0」时 +1,存量 ≥1 时重置 0——买入重置事件等价物
      (prep 帧观察不到商店买入瞬时事件,以存量 ≥1 为重置判据,语义 =
      「已持有目标件时干旱不累计更不撤线」原文);
    - ``evicted``:(线名, 撤线后步数)——回锁禁止窗载体(D-P4)。
      计量口径(【R197 症7 勘误,原「逐帧 +1」失准】):步进载体 =
      ``update_line_state``,每个**到达证明 pass 的备战期帧** +1——
      prep 实体面(球/箱/典籍/overlay)早退帧在证明 pass 之前 return,
      不步进本窗。窗口判据按备战期数计量,方向保守(窗偏长);
      ``since`` 的比较对象 D_min 系备战期维参数。
    - ``drought`` 读端申报(R197 症7):cw4 内 drought 无行为消费端
      (换线排除读 ``session.drought_excluded``,cw4 无写端)——A/B 期
      drought 计数器=纯遥测影子面(与 should_switch 同族影子声明,
      R197 症2 裁决),drought→drought_excluded 的行为接线=过线后批。
    """

    k_name: str = ''
    dwell: int = 0
    drought: int = 0
    evicted: tuple[str, int] | None = None


@dataclass
class SwitchOutcome:
    """should_switch 输出(事件 + 归因分键,禁混计)。"""

    event: bool
    key: str            # ''=评估通过路径;'switchline_skipped'/'theta_unavailable'/'switchline_exit_blocked'/…
    alt_comp: object | None = None


def _line_state(session: StrategySession) -> LineState:
    """session 侧线级状态机唯一入口(局内持久,局终随 session 销毁)。"""
    st = getattr(session, 'cw4_line_state', None)
    if not isinstance(st, LineState):
        st = LineState()
        session.cw4_line_state = st
    return st


def _count(session: StrategySession, key: str) -> None:
    counters = getattr(session, 'cw4_counters', None)
    if isinstance(counters, dict):
        counters[key] = counters.get(key, 0) + 1


def stop_buy(k: Comp | None, held_names: list[str],
             deployed_names: list[str]) -> bool:
    """停手线(R4-F8 函数位;R10-5 谓词语义钉死)。

    成型判定 = K 目标线单位齐备 ∧ 无待补缺口:线内全部成员名已出现在
    板(deployed)∪bench(held)——「当前线 K 成型」的分类谓词输出,
    评估对象恒为当前生效线 K、逐备战期随 M2 分类重评(证明 pass 后、
    M2 分类前由 entry 调用)。外因破成型(合成/装备消耗)⇒ 重评自然
    归 0,无锁存。
    """
    members = predicates.line_members(k)
    if not members:
        return False
    owned = set(held_names) | set(deployed_names)
    return all(m in owned for m in members)


def signal_arm(session: StrategySession) -> str | None:
    """信号直锁边(§2.7.1 S0──信号──▶S3;R11-3:两臂同开不旁路)。

    返回命中的直通线信号名(未命中 None)。当前可判定载体 =
    session.active_strategies ∩ DIRECT_LINE_SIGNAL_STRATEGIES;
    信号谱其余成员(圣杯契约/万敌数量/昼神速度流)的 obs 层观测面
    未落,显式登记待接线(禁按名称硬编码逐件枚举线配方——注记 6)。
    """
    actives = getattr(session, 'active_strategies', None) or []
    for sig in DIRECT_LINE_SIGNAL_STRATEGIES:
        if sig in actives:
            return sig
    return None


def resolve_switch_params() -> tuple[float, int, float] | None:
    """θ/D_min/δ 滞回三参解析(R192 修注;R23-5 归宿=provisional【拟】)。

    任一 None ⇒ 返回 None(should_switch 不评估 + theta_unavailable 记数,
    R24-2)。δ(P16 滞回)与 δ_prior(窗口平移)语义无关(R34-4 撞名
    消解)——本函数只辖前者。
    """
    theta = provisional.get('THETA')
    d_min = provisional.get('D_MIN')
    delta = provisional.get('DELTA_HYST')
    if theta is None or d_min is None or delta is None:
        return None
    return float(theta.value), int(d_min.value), float(delta.value)


def evidence_gate(missing: list[tuple[int, float]],
                  refresh_budget: int) -> tuple[bool, str]:
    """证据门 P38(④-3 表第二行:新建)。

    ``missing`` = [(缺口张数, 单张出现概率 q), ...](线距离分解,
    cw_line_switch/odds 侧产物);``refresh_budget`` = 本窗口可用刷新数。

    实现 = **序数形态**(零参数):对候选线的缺口集算 p_complete
    (statefn/vopt,P38 ③层闭式),可补齐线中取最大者过门;无缺口
    (missing 空)⇒ 直接过门。P_complete 阈值【拟】槽位未立(标定批
    挂账),阈值形态落码前禁自造数值门——fail 方向:缺输入(空缺口
    集/零预算且仍有缺口)⇒ 不过门(线维持现状)。
    """
    if not missing:
        return True, 'complete'
    if refresh_budget <= 0:
        return False, 'no_budget'
    pc = p_complete(missing, refresh_budget)
    if pc > 0.0:
        return True, f'p_complete={pc:.4f}'
    return False, 'p_complete_zero'


def best_alt_comp(state: GameState, session: StrategySession,
                  registry: DecisionV2Registry | None) -> Comp | None:
    """换线候选线供给(R196 症1 接线;§2.7 接线义务的 alt 半边)。

    候选集 = COMP_LIBRARY(证明层 comp 知识单一源,§1 proof 行「GameState
    + comp 知识(COMP_LIBRARY)」)− 当前线 − drought 排除线(session
    .drought_excluded,基线 best_alt_line 同款读法)。证据门 P38 序数形态
    以两个零参数前置承载:①静态可达(e_rounds 有限——p̄>0,缺口可刷到);
    ②shop 供给 >0(基线供给门同口径)。取 e_rounds 最小者为候选 alt。

    工程裁量申报(R196,编排者任务书「候选集来源推导+显式呈报」):规格
    未给候选集枚举来源,p_complete 阈值门【拟】未立(证据门 fail 方向=
    缺输入不过门——此处以「e 有限 ∧ 供给>0」的序数半边先行,p_complete
    数值门随标定批接入);候标定批前 θ/D_min/δ/U_X/V_ms 任一 None 期
    should_switch 整体 fail-closed,本函数输出不被消费(空转零行为面)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import (
        COMP_LIBRARY,
        shop_supply,
    )
    cur = getattr(session, 'target_comp', None)
    cur_name = getattr(cur, 'name', '') if cur is not None else ''
    excluded = set(getattr(session, 'drought_excluded', None) or ())
    best: Comp | None = None
    best_e: float = math.inf
    for comp in COMP_LIBRARY:
        if not getattr(comp, 'core_chars', None):
            continue
        if comp.name == cur_name or comp.name in excluded:
            continue
        try:
            if shop_supply(comp, state) <= 0:
                continue
            e = cw_line_switch.e_rounds(comp, state, registry)
        except Exception:   # noqa: BLE001  候选评估退化态:跳过该候选(可观测)
            continue
        if e < best_e:
            best, best_e = comp, e
    return best


def should_switch(state: GameState, session: StrategySession,
                  config: object, registry: DecisionV2Registry | None,
                  *, skeleton_only: bool = False,
                  alt_comp: Comp | None = None) -> SwitchOutcome:
    """换线判据(§2.7;R192 修注调用形态)。

    【R197 症2 影子面声明(编排者裁=方案 a,A/B 期换线共用基线权威)】
    本函数输出在 A/B 期为**影子面**:只发遥测(归因分键/switchline_
    event 计数)与登记回锁窗,**不写 target_comp**——K 翻转的生产载具
    = decision_v2 意向状态机(``MandateV1Strategy.update_target``
    透传,两臂同源恒等,臂间 diff 归因不含换线路径)。cw4 自有换线
    接线(事件→target_comp、drought→drought_excluded)=过线后批;
    禁删影子机(遥测持续供验证)。

    评估序(归因分键逐路 return,禁混计):
    1. 臂①旁路(skeleton_only)⇒ 恒 false + ``switchline_skipped``
       (§4.2.1 should_switch 行:发射位旁路=恒 false,换线事件零发射);
    2. θ/D_min/δ 任一 None ⇒ 不评估 + ``theta_unavailable``
       (R24-2 第三成因独立分键;K 冻结在当前线);
    3. 出口可用性前置(R13-1①):u/V_ms【拟】None ⇒ 塌缩出口不可用
       ⇒ 不登记 + ``switchline_exit_blocked``(§2.2.1 第 4 行全🔴
       延迟态的等价 fail-closed——u🔴 ⇒ V_slot 构造性🔴,R15-3);
    4. 解析成功 ⇒ dataclasses.replace 构造解析实参的 registry 视图,
       调 ``should_switch_e`` 比较(比较器本体零改动);回锁禁止窗
       (D-P4)叠加在事件侧:撤线窗口内同线回锁阻断。
    """
    if skeleton_only:
        _count(session, 'switchline_skipped')
        return SwitchOutcome(False, 'switchline_skipped')
    params = resolve_switch_params()
    if params is None:
        _count(session, 'theta_unavailable')
        return SwitchOutcome(False, 'theta_unavailable')
    # 出口可用性前置:line_switch_sell 比较 u/V_ms 系【拟】未标定 ⇒
    # 出口确定性延迟(§2.2.1 第 4 行)——换线不登记,K 冻结(滞留螺旋
    # 构造性封死的既裁退化形态)。
    if provisional.is_none('U_X') or provisional.is_none('V_MS'):
        _count(session, 'switchline_exit_blocked')
        return SwitchOutcome(False, 'switchline_exit_blocked')

    import dataclasses

    theta, d_min, delta = params
    reg = registry
    if reg is not None:
        reg = dataclasses.replace(reg, line_switch_theta=theta,
                                  line_switch_min_dwell=d_min,
                                  line_switch_debias_delta=delta)
    ls = _line_state(session)
    cur = getattr(session, 'target_comp', None)
    if cur is None:
        _count(session, 'switchline_no_target')
        return SwitchOutcome(False, 'no_target')
    try:
        e_cur = cw_line_switch.e_rounds(cur, state, reg)
    except Exception:   # noqa: BLE001  线距离退化态:维持原线,可观测
        _count(session, 'switchline_e_cur_undefined')
        return SwitchOutcome(False, 'e_cur_undefined')
    if alt_comp is None:
        # R196 症1:调用点缺省 ⇒ 证明层自派生(best_alt_comp;§2.7 接线
        # 义务——entry 生产调用点不再构造性恒 no_alt)
        alt_comp = best_alt_comp(state, session, reg)
        if alt_comp is None:
            _count(session, 'switchline_no_alt')
            return SwitchOutcome(False, 'no_alt')
    ok, _reason = cw_line_switch.should_switch_e(
        e_cur, cw_line_switch.e_rounds(alt_comp, state, reg), ls.dwell, reg)
    if not ok:
        return SwitchOutcome(False, '')
    # D-P4 回锁禁止窗:撤线登记窗口内,同线回锁阻断(滞回半边;
    # θ/D_min 已在比较器内承载主滞回,本窗为线级事件侧补充)。
    if ls.evicted is not None:
        name, since = ls.evicted
        if name == getattr(alt_comp, 'name', '') and since < d_min:
            _count(session, 'switchline_relock_window')
            return SwitchOutcome(False, 'relock_window')
    return SwitchOutcome(True, '', alt_comp=alt_comp)


def update_line_state(session: StrategySession, k: Comp | None,
                      held_names: list[str],
                      deployed_names: list[str]) -> LineState:
    """证明 pass 线级状态机步进(entry 每备战期证明 pass 后调用一次)。

    - K 名变化 ⇒ dwell 归 0(新线驻留起点);同名 ⇒ dwell +1;
    - 干旱计数(D-A45):目标线成员在板∪bench 存量 ≥1 ⇒ 重置 0,
      存量 =0 ⇒ +1(「已持有目标件时干旱不累计」原文语义);
    - 撤线窗口步进:evicted 非空 ⇒ 计数 +1。
    """
    ls = _line_state(session)
    name = getattr(k, 'name', '') if k is not None else ''
    if name != ls.k_name:
        ls.k_name = name
        ls.dwell = 0
    else:
        ls.dwell += 1
    members = predicates.line_members(k)
    owned = set(held_names) | set(deployed_names)
    if any(m in owned for m in members):
        ls.drought = 0
    else:
        ls.drought += 1
    if ls.evicted is not None:
        ls.evicted = (ls.evicted[0], ls.evicted[1] + 1)
    return ls


def register_eviction(session: StrategySession, line_name: str) -> None:
    """撤线事件登记(should_switch 事件被 entry 采纳为换线时调用;D-P4)。

    A/B 期=影子面登记(只写回锁窗状态,不影响 target_comp——R197
    症2 裁决;真实翻转不经 cw4 事件时本窗对真实翻转不设防,系方案 a
    的已裁形态,过线后批接线时一并收口)。
    """
    ls = _line_state(session)
    ls.evicted = (line_name, 0)
