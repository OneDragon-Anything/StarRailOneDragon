"""cw4 证明层(线选择与终局)——换核批 1 落地(R189-1 ④-3 裁决四函数位;
裁决原文已删档,取回口径=ADR-0644)。

规格单一源:
- 证明层承载者=本模块四函数位(should_switch/证据门/stop_buy/signal_arm)
  全套新建,现役件只作对拍锚;decision_v2 属冻结基线臂,改造它=改基线;
  换线生命周期/证据门/换线机器现行规格=12_line_and_intention.md;
- 换线比较器(P16)与停手线判据、直通线入口=12_line_and_intention.md
  §1-§3;直通线谱系与开局形态=13 号稿 COMP_LIBRARY 域;
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

计数载体:``state_of(session).cw4_counters``(dict,bridge 每局创建;键登记
单一源=下方键清单与写点,原 design_telemetry 键节已删档,取回口径=
ADR-0644——本模块产键:theta_unavailable(聚合)+
theta_unavailable_theta/_d_min/_delta(成因分桶观察件;聚合与成因
不同键防混计)/ switchline_skipped /
switchline_exit_blocked / switchline_no_alt / switchline_no_target /
switchline_e_cur_undefined / switchline_relock_window[R196 修复批:
「不换线也记遥测」的归因分键补齐——四路 return 原先零计数]/
evidence_gate_evaluated / evidence_gate_sandwich_suff /
evidence_gate_sandwich_band / evidence_gate_sandwich_below_nec /
evidence_gate_sandwich_pathological / evidence_gate_unavailable(聚合)+
evidence_gate_unavailable_<成因>(成因分桶观察件;接线批 T-213 影子
评估键,ADR-0637——零行为面,键登记惯例=产键模块 docstring)。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import SHOP_SLOTS
from sr_od.application.currency_war.kernel import cw_line_switch
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
    bench_occupied,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_plane_table import r_remaining
from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
    calibration,
    provisional,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
    budget,
    odds,
    predicates,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    a7_lower_bound,
    p_complete,
    p_miss,
    v_comp_marginal,
    v_opt,
    v_slot,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.kernel.cw_vocab import Comp
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

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
    - ``k_name``:当前生效目标线名(state_of(session).target_comp 的 comp 名投影,
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
      (换线排除读 ``state_of(session).drought_excluded``,cw4 无写端)——A/B 期
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
    st = getattr(state_of(session), 'cw4_line_state', None)
    if not isinstance(st, LineState):
        st = LineState()
        state_of(session).cw4_line_state = st
    return st


def _count(session: StrategySession, key: str) -> None:
    counters = getattr(state_of(session), 'cw4_counters', None)
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


def switch_param_missing() -> list[str]:
    """θ/D_min/δ 三参缺失清单(R24-2 成因分桶观察件;零语义——只读
    provisional,不改变 resolve_switch_params 的判返回值)。

    返回缺失槽位名('theta'/'d_min'/'delta' 子集,全在 = 空表)。
    分键纪律:既有聚合键 ``theta_unavailable`` 原样保留(聚合口径,
    兼容旧判读);成因键 = ``theta_unavailable_<槽位名>``,**不同键
    防混淆**(20260905_194344-simfind 报告问题 2 的刷新臂分键同纪律
    ——归因键不复用聚合键,禁混计)。
    """
    missing: list[str] = []
    if provisional.get('THETA') is None:
        missing.append('theta')
    if provisional.get('D_MIN') is None:
        missing.append('d_min')
    if provisional.get('DELTA_HYST') is None:
        missing.append('delta')
    return missing


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


@dataclass(frozen=True)
class LockSandwichFrame:
    """锁线夹界帧(P76 §4.3/§4.4 各项的帧级数值载体;装配器 =
    ``assemble_lock_frame``,接线批 T-213/ADR-0637)。

    字段坐标系(写入端 = 接线批装配器;取值时机 = 锁线评估帧现算):
    - ``e_p_next``:E[P′] 等待一帧后的期望完成概率(P38 同机,集中协议);
    - ``o_plus``:O⁺ 反超期权上界 = Σ P_i^port·(V_i−V_*)⁺(§4.4 union
      bound+优势上界;值因子挂 V_ms 同源,§7 #1);
    - ``f_plus``:F⁺ 兜底保留上界 = (1−P)·Σ(P_miss·C_rescue+1)
      (u=1 消参,§7 #5);
    - ``b_plus``:B⁺ 压库收益上界(P49 线性律);
    - ``c_hold``:C = C_hold(H_{−*}) 携带成本——差分口径仅侧线件
      (修正 4:按组合全集计则双计 ℓ* 件携带,压低阈值偏早锁);
    - ``d_death``:D = Δλ_death·(g+Φ) 死亡风险增量(P51 区间敞口口径,
      禁边际引用/禁 hp 价值换算;λ 挂【拟】);
    - ``band_domain_ok``:ε₂ 带值辖域位(r1 返工,T-278/ADR-0639 修订):
      装配帧 (max m, r_remaining) 全落标定网格域
      (``calibration.E2_DOMAIN_*``,注册表有界维)为 True;域外
      False ⇒ 门出 unavailable[e2_domain](P76 丙.4「带外不声明」
      的落码形态,禁欠覆盖的 θ̂_suff 静默进夹界;R 维全轴覆盖由
      复现脚本数值验证承载;缺省 True = 手工构造帧兼容)。

    任一数值字段 None = 该项帧级未装配 ⇒ 门整体「不可评」(§7 #1 数值
    门禁消费;reason 带成因分键,仿 theta_unavailable 归因可辨纪律)。
    """

    e_p_next: float | None = None
    o_plus: float | None = None
    f_plus: float | None = None
    b_plus: float | None = None
    c_hold: float | None = None
    d_death: float | None = None
    band_domain_ok: bool = True


def evidence_gate(missing: list[tuple[int, float]],
                  refresh_budget: int,
                  frame: LockSandwichFrame | None = None) -> tuple[bool, str]:
    """证据门 P38(④-3 表第二行:新建;P76 §5.5 夹界形态重写,ADR-0628)。

    ``missing`` = [(缺口张数, 单张出现概率 q), ...](线距离分解,
    生产单一源 = ``line_missing_decomposition``);``refresh_budget`` =
    传入 p_complete 的**试验数**(接线批调用方按 P38 ②层槽试验口径装配,
    q = 单槽命中概率,见 ``assemble_lock_frame``;字面「刷新数」读法
    退役)
    ——**仅作 p_complete 试验数条件,不再构成否决**(§5.5.2 域 α 重判:
    锁线是配置承诺不是购买,其价值不需要刷新预算——预算耗尽不构成
    「不锁」的理由)。

    判定 = P76 §4.4 可计算夹界(落码形态;替换旧序数 pc>0——§5.5.3
    「θ̂_nec > 0 的域禁 0 阈值」):

    - θ̂_suff = clamp(E[P′] + (O⁺+F⁺+B⁺−C−D)/Δ + ε₂, 0, 1)——右侧全上界
      +ε₂ 集中度二阶带余量(丙.4 净支配的落码归宿),P ≥ θ̂_suff ⇒ 锁不劣;
    - θ̂_nec = clamp(E[P′] − (C+D)/Δ, 0, 1)——右侧下界 O=F=B=0,
      P < θ̂_nec ⇒ 锁劣;
    - 两截断之间 = 夹界未决 ⇒ 不过门(维持现状,旧 fail 方向);
    - suff 截断前原始值 >1 ⇒ A-丁.2 病态域(终局期权压过 C+D,夹界空)
      ⇒ 出口 = 不进单线锁判定(§4.4 处置:等反超/换线机器接管),
      独立分键,不与带内未决混计;
    - 闭式解 <0(域 α 深处)⇒ 截 0 = 无条件锁(戊.2「该域应最早锁」的
      结构涌现)。

    Δ=V_C−V_F 与 ε₂ 走 provisional【拟】槽位(§7 #1:θ* 点值与数值门
    禁消费——None 期门输出「不可评」+成因分键,绝不向骨架层渗漏为否决,
    NMF §5.3)。丁.4 引理域 V_C>V_F:Δ≤0 系域外输入,同归不可评。
    本门已接线(接线批 T-213/ADR-0637:entry 证明 pass 影子评估,输出只
    进分键计数零行为面;P76 修正 5 的零调用点状态自此终结,权威面切换
    = 标定落地且门数值可评后的另案裁决批)。装配单一源 =
    ``assemble_lock_frame``。
    """
    if not missing:
        return True, 'complete'
    if frame is None:
        frame = LockSandwichFrame()
    causes: list[str] = []
    delta_calib = provisional.get('V_C_MINUS_V_F')
    if delta_calib is None:
        causes.append('delta')
    e2_calib = provisional.get('E2_CONCENTRATION_BAND')
    if e2_calib is None:
        causes.append('e2')
    for name in ('e_p_next', 'o_plus', 'f_plus', 'b_plus',
                 'c_hold', 'd_death'):
        if getattr(frame, name) is None:
            causes.append(name)
    if not frame.band_domain_ok:
        # ε₂ 带值标定网格域外(装配端判定,calibration.E2_DOMAIN_*):
        # 带外不消费带值——静默欠覆盖会使 θ̂_suff 偏低、「P≥θ̂_suff ⇒
        # 锁不劣」保证失效(fail-open),故 fail-closed 归不可评
        # (r1 返工,T-278/ADR-0639 修订;P76 丙.4「带外不声明」落码)。
        causes.append('e2_domain')
    delta = delta_calib.value if delta_calib is not None else None
    if delta is not None and delta <= 0:
        causes.append('delta_non_positive')
    if causes:
        return False, ('sandwich_unavailable['
                       + ','.join(sorted(causes)) + ']')

    e2 = e2_calib.value
    p = p_complete(missing, refresh_budget)
    cost_side = frame.c_hold + frame.d_death
    gain_side = frame.o_plus + frame.f_plus + frame.b_plus
    suff_raw = frame.e_p_next + (gain_side - cost_side) / delta + e2
    if suff_raw > 1.0:
        return False, 'sandwich_pathological'
    th_suff = min(1.0, max(0.0, suff_raw))
    th_nec = min(1.0, max(0.0, frame.e_p_next - cost_side / delta))
    if p >= th_suff:
        return True, f'sandwich_suff(p={p:.4f},suff={th_suff:.4f})'
    if p < th_nec:
        return False, f'sandwich_below_nec(p={p:.4f},nec={th_nec:.4f})'
    return False, (f'sandwich_band(p={p:.4f},nec={th_nec:.4f},'
                   f'suff={th_suff:.4f})')


def _held_counts(gs) -> dict[str, int]:
    """逐角色名副本计数(bench∪deployed 容器席位 bot 记录库存;槽位模型
    None 跳过,空名不计)。``odds.slot_q_tag``/帧装配的池衰减 j/t 输入
    载体。换算单一源 = 波 1 席位读口族。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
        deployed_slots_of,
    )
    counts: dict[str, int] = {}
    for bc in (list(bench_slots_of(gs)) + list(deployed_slots_of(gs))):
        name = getattr(bc, 'char_id', '') if bc is not None else ''
        if name:
            counts[name] = counts.get(name, 0) + 1
    return counts


def _char_cost(name: str) -> int:
    """角色注册表费用(查表;未知名 = 0,消费端按「不计」域外处置)。"""
    ch = CHARACTERS.get(name)
    return int(getattr(ch, 'cost', 0) or 0) if ch is not None else 0


def _missing_items(comp: Comp | None,
                   gs) -> list[tuple[str, int, float,
                                    dict[int, float]]]:
    """线缺口分解内部形态 [(档标签, 缺口张数, 聚合 q, 分费档明细)]——
    ``line_missing_decomposition`` 与 ``assemble_lock_frame`` 的共享单一
    实现(禁第二实现漂移);公开契约视图见前者。"""
    if comp is None:
        return []
    from sr_od.application.currency_war.kernel.cw_game_state import (
        level_of,
        shop_cards_to_legacy,
    )
    prog = cw_line_switch.tier_progress(comp, gs)
    if not prog:
        return []
    held = _held_counts(gs)
    items: list[tuple[str, int, float, dict[int, float]]] = []
    for f, (need_t, held_t, shelf_t) in prog.items():
        m = need_t - held_t - shelf_t
        if m <= 0:
            continue   # 已满足件剔除(P38 配方)
        # 货架件「买走即 held」口径(line_distance 同式):按费档直加
        # 同标签池衰减 j(无名货架卡不可入 held_counts,走 extra 通道)。
        extra: dict[int, int] = {}
        if shelf_t > 0:
            _payload = gs.shop.value
            _shop_view = (shop_cards_to_legacy(shop_payload_content_cards(_payload))
                          if _payload is not None else [])
            for c in _shop_view:
                if (getattr(c, 'faction', '') or '') == f:
                    cost = int(getattr(c, 'cost', 0) or 0)
                    if cost:
                        extra[cost] = extra.get(cost, 0) + 1
        bd = odds.slot_q_tag_by_cost(f, level_of(gs), held, extra)
        items.append((f, m, sum(bd.values()), bd))
    return items


def line_missing_decomposition(comp: Comp | None,
                               gs) -> list[tuple[int, float]]:
    """线缺口分解 [(缺口张数 m, 单槽命中概率 q)]——``evidence_gate``
    输入单一源(接线批 T-213 前全仓无同形产物,T-124 审 Q2b 指认;
    ADR-0637)。

    件模型 = P38:form_tiers 逐档一项(段表登记批前现状口径,段表落地
    由该批泛化);m_t = max(0, need−held−shelf) **逐档 clamp**——完成
    事件 = 各档各自满足,一档超持不帮另一档补缺,与 ``line_distance``
    的全局 clamp 标量口径(E_rounds 距离近似)有意分歧、不统一,分解
    口径单一源 = ``cw_line_switch.tier_progress``;已满足件(m≤0)剔除
    (P38 配方)。q_t = ``odds.slot_q_tag``(P38 ③层含池衰减,货架件
    计入同档衰减)。q≤0 的项照常入表(p_complete 对 q≤0 返 0 → 必要侧
    拒,静态不可达线诚实出「锁劣」向);缺口空 → 空表(调用方按
    complete 域处置,本函数不发 complete)。
    """
    return [(m, q) for _tag, m, q, _bd in _missing_items(comp, gs)]


def assemble_lock_frame(gs, session: StrategySession,
                        ) -> tuple[list[tuple[int, float]], int,
                                   LockSandwichFrame]:
    """证据门评估帧装配单一源(接线批 T-213/ADR-0637;试验数升级 =
    标定批 T-278/ADR-0639 按 P38 ⑤层金位递推):返回
    ``(missing, trials, frame)``。

    试验数口径(P38 ②层槽试验,docstring 钉死):``trials = SHOP_SLOTS
    × (R_全局 + 可负担付费刷数)``。R_全局 = ``cw_plane_table.r_remaining``
    (到局终剩余节点,NMF §2 单一源);付费刷数 = P38 ⑤层预算递推
    (``statefn/budget.p38_budget_recursion``,金位逐轮模拟单一源;
    B<0 = 缺口件买不起域 → trials=0 且 P:=0,P38「买到即计数前提
    破产」保守分支)。**B<0 域的门内落点申报(r1 修正,原 below_nec
    表述不实)**:exhausted ⇒ e_p_next=0 ⇒ θ̂_nec=clamp(0−cost/Δ)=0,
    `p<th_nec` 恒假 ⇒ 实际落 sandwich_band,典型格(cost ≥ gain+
    ε₂·Δ)落 suff 截 0=无条件放行锁——「永不完成线的锁背书」属换线
    机器领地、P76 夹界模型外,禁靠截 0 语义默认放行:**P=0 域的
    suff 放行显式裁决已列入装配批义务清单**(ADR-0639 §4)。刷新预算
    解耦语义不回归(P76 §5.5.2:本域耗尽的是购卡预算)。逐项口径与
    简化申报见 budget 模块 docstring(resolved 息帽泛化/升级金单步
    v1/不动点保守端)。

    六帧项逐条(P76 §4.4 可计算夹界;界方向逐条申报):
    - ``e_p_next`` = p_complete(missing, trials − SHOP_SLOTS)——等待一帧 =
      组合协议下本线只自然刷一次(一阶主通道,丙.4);S_side 分流不扣 =
      对等待协议乐观 → E[P′] 高估 → suff/nec 两侧判据均保守(拒向)。
    - ``f_plus`` = (1−P)·Σ_{x∈H−*}(P_miss,x·C_rescue,x + 1)——u=1 已消参
      (P76 §7 #5 免标定);H−* = bench∪deployed 中不在 K 成员名的侧线件
      (修正 4 差分口径);C_rescue,x = ``a7_lower_bound``(P41 A7 形,
      c/p_shop),不可达件(p_shop=0)只保留 +1 手续费项——永不出现件
      无重建期权,如实剔除。
    - ``b_plus`` = Σ_{x∈H−*} ``v_comp_marginal``(P49 线性律)——毛值作
      上界臂消费(不扣 C_sat 同槽双计,上界方向安全;净扣归标定批);
      未知名/费档域外(0)不计。
    - ``c_hold`` = C_int + C_sat。C_int = |H_S| 金(最小卖回协议手续费级
      上界,乙.1 段 2;H_S = star≥2∧cost≥2 侧线件;1 金 = 甲.2 定理
      手续费机制真值非拍定)。C_sat = ``v_slot(free, blocked)``×P_block
      (乙.2;free>1 ⇒ v_slot=0 在库免手写门);P_block =
      min(1, Σ_i p_shop,i)(乙.2 上界式的 Σ 项;压库候选率 P_comp v1
      未入,申报);blocked = 各缺件主费档 ``v_opt(u=1)``(P76 §7 #3
      V_opt 侧先行的落码形态;j=0 = 值侧满池上界,保 c_hold 上界形态)。
    - ``o_plus`` = None(价值因子 (V_i−V_*)⁺ 挂 V_ms【拟】P76 §7 #1,
      P_i^port 侧线组合评估面未落)——None 期门恒「不可评」诚实沉默。
    - ``d_death`` = None(Δλ_death 两协议板强路径差量挂 λ 连续模型
      【拟】P76 §7 #2;λ 表为 PL 键点值无协议差键)。

    门可评前置(敞口更新,申报于 ADR-0637):Δ/ε₂ 注入(标定批
    T-278 已落,``audit/calibration.apply``)**且** o_plus/d_death
    装配落地(值因子标定批之后续装配批)之前,门对一切缺口帧恒
    ``sandwich_unavailable``〔o_plus,d_death〕。
    """
    k = getattr(state_of(session), 'target_comp', None)
    items = _missing_items(k, gs)
    missing = [(m, q) for _tag, m, q, _bd in items]
    # 可达件(q>0)期望购买成本与张数:P38 ⑤层预算输入。q≤0 静态
    # 不可达件不计——它永不出现,购账不发生而 P=0 已由 p_complete
    # 承载,入账反会虚增 B<0 域(budget 模块 docstring 同申报)。
    purchase_cost = 0.0
    missing_copies = 0
    for _tag, m, q, bd in items:
        if q <= 0 or not bd:
            continue
        purchase_cost += m * sum(c * p_c for c, p_c in bd.items()) / q
        missing_copies += m
    plan = budget.p38_budget_recursion(gs, session, purchase_cost,
                                       missing_copies)
    held = _held_counts(gs)
    k_members = set(predicates.line_members(k))
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
        deployed_slots_of,
        gold_of,
        level_of,
        plane_of,
        round_num_of,
    )
    level = level_of(gs)
    # 刷新费缺省 = 建模基价常量单一源(SHOP_REFRESH_COST;原魔数 2 双写
    # 收敛,budget.py 同族先例——数值恒同,禁字面量第二份)。
    from sr_od.application.currency_war.kernel.cw_economy import (
        SHOP_REFRESH_COST as _SHOP_REFRESH_COST,
    )
    refresh_cost = int(gs.shop_refresh_cost.value
                       or _SHOP_REFRESH_COST)
    r_rem = r_remaining(session, plane_of(gs), round_num_of(gs))
    trials = (0 if plan.exhausted
              else SHOP_SLOTS * max(0, int(r_rem) + int(plan.refreshes)))
    # ε₂ 带值辖域(注册表有界维 m/r_rem;域外帧 fail-closed 归
    # unavailable[e2_domain],禁欠覆盖带值进夹界——r1 返工,
    # calibration 单一源;R 维全轴覆盖由脚本数值验证承载)
    band_domain_ok = calibration.band_in_domain(
        max((m for m, _q in missing), default=0), int(r_rem))

    # H−* 侧线件清单 (名, 星, 费)(K 成员名 = predicates.line_members)
    side: list[tuple[str, int, int]] = []
    for bc in (list(bench_slots_of(gs)) + list(deployed_slots_of(gs))):
        name = getattr(bc, 'char_id', '') if bc is not None else ''
        if name and name not in k_members:
            side.append((name, int(getattr(bc, 'star', 1) or 1),
                         _char_cost(name)))

    p_lock = 0.0 if plan.exhausted else p_complete(missing, trials)

    f_sum = 0.0
    b_plus = 0.0
    for name, _star, cost in side:
        j_x = held.get(name, 0)
        t_x = sum(cnt for nm, cnt in held.items()
                  if nm != name and _char_cost(nm) == cost)
        ps = odds.p_shop(level, cost, j_x, t_x)
        rescue = a7_lower_bound(level, cost, refresh_cost, j_x, t_x)
        if math.isfinite(rescue) and ps > 0:
            f_sum += p_miss(level, cost, j_x, t_x) * rescue + 1.0
        else:
            f_sum += 1.0   # 不可达件:只保留清算手续费项
        if 1 <= cost <= 5:
            b_plus += v_comp_marginal(cost, level, taken=t_x,
                                      refresh_cost=refresh_cost)
    f_plus = (1.0 - p_lock) * f_sum

    h_s = sum(1 for _name, star, cost in side if star >= 2 and cost >= 2)
    c_hold = float(h_s)
    p_block_terms: list[float] = []
    blocked: list[float] = []
    for _tag, _m, q_i, bd in items:
        if q_i > 0:
            p_block_terms.append(1.0 - (1.0 - q_i) ** SHOP_SLOTS)
        if bd:
            c_star = max(bd, key=bd.get)
            blocked.append(v_opt(level, c_star, 1.0, 0,
                                 gold_of(gs),
                                 refresh_cost))
    free = BENCH_CAPACITY - bench_occupied(bench_slots_of(gs))
    c_sat = min(1.0, sum(p_block_terms)) * v_slot(free, blocked)
    c_hold += c_sat

    frame = LockSandwichFrame(
        e_p_next=(0.0 if plan.exhausted
                  else p_complete(missing, max(0, trials - SHOP_SLOTS))),
        o_plus=None,
        f_plus=f_plus,
        b_plus=b_plus,
        c_hold=c_hold,
        d_death=None,
        band_domain_ok=band_domain_ok,
    )
    return missing, trials, frame


def evaluate_evidence_gate(gs, session: StrategySession,
                           ) -> tuple[bool, str] | None:
    """证据门影子评估(接线批 T-213/ADR-0637;entry 证明 pass 每备战帧
    消费)。返回 ``(ok, reason)`` 仅供测试/调试,调用方**不消费返回值
    做任何行为**。

    影子面声明(R197 症2 同族;在册先例 = should_switch「已接线 +
    fail-closed 封印休眠」,12 号稿 §3 as-built):输出只进
    ``cw4_counters`` 分键计数——封印期(Δ/ε₂/V_ms/Δλ【拟】全 None)门恒
    「不可评」诚实显影,**绝不向骨架层渗漏为否决**(NMF §6/§5.3);
    权威面切换(S1→S3 证据门接管)= 标定落地且门数值可评后的另案裁决批。

    键推导 = reason 前缀('(' 前段;reason 携数值禁作键,防键基数爆炸);
    不可评 = 聚合键 + 成因分桶键(**聚合与成因不同键防混计**,R24-2
    theta_unavailable 同款纪律)。缺口空/无目标线帧不评估(锁线时机
    问题不存在;complete 直过路径留给门内语义,影子面不产计数噪声)。
    """
    if getattr(state_of(session), 'target_comp', None) is None:
        return None
    missing, trials, frame = assemble_lock_frame(gs, session)
    if not missing:
        return None
    _count(session, 'evidence_gate_evaluated')
    ok, reason = evidence_gate(missing, trials, frame)
    key = reason.split('(', 1)[0]
    if key.startswith('sandwich_unavailable'):
        _count(session, 'evidence_gate_unavailable')
        for cause in reason[len('sandwich_unavailable'):].strip('[]').split(','):
            cause = cause.strip()
            if cause:
                _count(session, f'evidence_gate_unavailable_{cause}')
    elif key:
        _count(session, f'evidence_gate_{key}')
    return ok, reason


def best_alt_comp(gs, session: StrategySession,
                  registry: DecisionV2Registry | None) -> Comp | None:
    """换线候选线供给(R196 症1 接线;§2.7 接线义务的 alt 半边)。

    候选集 = COMP_LIBRARY(证明层 comp 知识单一源,§1 proof 行「CwSimFrame
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
    cur = getattr(state_of(session), 'target_comp', None)
    cur_name = getattr(cur, 'name', '') if cur is not None else ''
    excluded = set(getattr(state_of(session), 'drought_excluded', None) or ())
    best: Comp | None = None
    best_e: float = math.inf
    for comp in COMP_LIBRARY:
        if not getattr(comp, 'core_chars', None):
            continue
        if comp.name == cur_name or comp.name in excluded:
            continue
        try:
            _gs_supply = gs
            if shop_supply(comp, _gs_supply) <= 0:
                continue
            e = cw_line_switch.e_rounds(comp, _gs_supply, registry,
                                        session=session)
        except Exception:   # noqa: BLE001  候选评估退化态:跳过该候选(可观测)
            continue
        if e < best_e:
            best, best_e = comp, e
    return best


def should_switch(gs, session: StrategySession,
                  config: object, registry: DecisionV2Registry | None,
                  *, skeleton_only: bool = False,
                  alt_comp: Comp | None = None) -> SwitchOutcome:
    """换线判据(§2.7;R192 修注调用形态)。

    【R197 症2 影子面声明(编排者裁=方案 a,A/B 期换线共用基线权威)】
    本函数输出在 A/B 期为**影子面**:只发遥测(归因分键/switchline_
    event 计数)与登记回锁窗,**不写 target_comp**——K 翻转的生产载具
    = decision_v2 意向状态机(ADR-0583 起内化为 flow 层方向刷新,
    两臂同源恒等,臂间 diff 归因不含换线路径)。cw4 自有换线
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
        # 聚合键原样(兼容旧判读)+ 成因分桶键(R24-2 观察件;switch_
        # param_missing 缺失清单直读,零第二套判返回语义)。
        _count(session, 'theta_unavailable')
        for _slot in switch_param_missing():
            _count(session, f'theta_unavailable_{_slot}')
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
    cur = getattr(state_of(session), 'target_comp', None)
    if cur is None:
        _count(session, 'switchline_no_target')
        return SwitchOutcome(False, 'no_target')
    try:
        e_cur = cw_line_switch.e_rounds(cur, gs, reg, session=session)
    except Exception:   # noqa: BLE001  线距离退化态:维持原线,可观测
        _count(session, 'switchline_e_cur_undefined')
        return SwitchOutcome(False, 'e_cur_undefined')
    if alt_comp is None:
        # R196 症1:调用点缺省 ⇒ 证明层自派生(best_alt_comp;§2.7 接线
        # 义务——entry 生产调用点不再构造性恒 no_alt)
        alt_comp = best_alt_comp(gs, session, reg)
        if alt_comp is None:
            _count(session, 'switchline_no_alt')
            return SwitchOutcome(False, 'no_alt')
    ok, _reason = cw_line_switch.should_switch_e(
        e_cur, cw_line_switch.e_rounds(alt_comp, gs, reg,
                                       session=session),
        ls.dwell, reg)
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
