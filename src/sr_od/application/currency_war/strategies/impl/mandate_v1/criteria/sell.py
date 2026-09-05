"""criteria/sell——EV 卖面(§2.2;fuel_sell/protected_sell 在 mandate/谓词层)。

三个发射/通道位:line_switch_sell(换线塌缩出口)、sell_for_interest
(凑息档 EV 面,臂①旁路)、funding_support_sell(支付能力变现子域,
R13-5 支付支撑通道,两臂同开、mandate=false+funding_support=true)。

fail 方向(§2.2.1 唯一权威规格):不可逆卖面缺输入(λ 表损坏/域外/
第四态无载/sell_refund 损坏)⇒ 不评不卖;u/V_ms🔴 ⇒ line_switch_sell
比较臂无载 ⇒ 不卖 + 出口确定性关闭(proof.should_switch 前置门同构)。
凑息卖自 T1 语义重写批(设计 13_buy_face_design §2.2)起 = 回拉发射位
(金位触发+目标量止盈,函数 docstring 单一源),无 fail-closed 输入面。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_state import (
    bench_char_cost,
    sell_refund,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import provisional
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    refund_full_star_ok,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_state import BenchChar, GameState


def line_switch_sell(old_line_members: tuple[str, ...],
                     new_line_members: tuple[str, ...],
                     bench: list[BenchChar], deployed: list[BenchChar],
                     state: GameState, *, k_switched: bool,
                     ) -> tuple[list[int], str]:
    """换线塌缩出口(§2.2 主比较式的发射位;k_switched=K 已按 K′ 更新)。

    返回 (拟卖 bench slot 列表, 归因键)。发射前置:
    - K 未切换 ⇒ 无对象(空,'no_event');
    - u/V_ms【拟】None(全🔴延迟态,§2.2.1 第 4 行)⇒ 不卖 +
      'switchline_exit_blocked'(塌缩出口整体延迟至标定后);
    - 候选 = 旧线成员 ∧ 非新线成员 ∧ protected_sell 恒不卖对象排除
      (骨架/贯穿件 = 新旧线交集成员保留)。
    比较式本体(V_opt/V_power 全式)消费 u/V_ms 数值——全式未落位期
    (含 U_X/V_MS 注入态)返回**保守子集而非全集**(IMPL_ADV_R200 症5③
    「全堵→全卖」悬崖修):保守子集 = 燃料类件(1★ ∧ sell_refund 全额
    可退,``refund_full_star_ok``)——依据=p41-hoard-sell-ev 燃料类支配性
    论证(零重叠∧1★全额退 ⇒ 卖出净成本=0,卖错代价≈0);2★+/部分退
    件卖错损失不可逆(手续费+V_opt 再遇账),注入态无全式比较 ⇒ 保守
    保留至 vopt 全式落位。全式接线后本子集语义由比较式取代。
    """
    if not k_switched:
        return [], 'no_event'
    if provisional.is_none('U_X') or provisional.is_none('V_MS'):
        return [], 'switchline_exit_blocked'
    out: list[int] = []
    for b in bench:
        name = b.char_id or ''
        if name in old_line_members and name not in new_line_members:
            # 注入态保守子集:仅燃料类(1★ 全额可退)放行,其余保留
            if not refund_full_star_ok(b.star, bench_char_cost(b)):
                continue
            out.append(b.slot)
    return out, ''


def sell_for_interest(gold: int, bench: list[BenchChar],
                      cap_resolved: int,
                      k_members: tuple[str, ...],
                      state: GameState | None = None,
                      *,
                      prefer_names: tuple[str, ...] = (),
                      counters: dict | None = None,
                      exclude_names: frozenset[str] | set[str] = frozenset(),
                      ) -> tuple[list[int], str]:
    """凑息卖·回拉发射位(T1 语义重写;设计 13_buy_face_design §2.2)。

    语义重写三项(R2-N4,取代旧「T_SEARCH_A 注入态资格全集无差别全发」):
    ① **金位触发(缺口驱动)**:买/花后投影金 ``gold`` < 息线
       g* = saturation_line(cap_resolved) 才发射,缺口 = g* − gold;
       非缺口帧零发射(返回 'not_needed',与 funding_support 触发形态同构);
    ② **目标量止盈**:remaining 递减贪心(funding_support ``remaining``
       模板同构移植,零待证依赖;任意确定序贪心都能卖够,序只影响效率
       ——p49 ⑤ 每金序/[11] 最小化为效率升级项,非本位前件),
       Σrefund ≥ 缺口即止,不多卖一张;
    ③ **槽位布尔门退役**:T_SEARCH_A 裸布尔检查退出本消费位(窗口数值
       链归 P57 裁决,与本重写分账)。

    资格谓词不变(1★ ∧ 零重叠 ∧ 无后台效果,与 funding_support_sell 同一;
    语境经 ``predicates.bench_effect_context`` 共享装配现读——症3 三通道
    统一,``state=None`` 按装配缺省保守端处置)。序:``prefer_names``
    (刚买件名集合,R2-N1 发射约束:首卖刚买件使连带卖出损失=0;帧投影
    架构下刚买件尚未入 bench,按名匹配同资格在册件)优先,其余按
    (star, slot) 升序(funding_support 同款序)。

    分键遥测(R3-R5 四字段,设计 §3.2;counters=None 时不记):
    ``t1_interest_emit_frames``(发射帧数)/``t1_interest_gap_total``(缺口
    累计)与 ``t1_interest_sellback_total``(实际卖回累计,两者之比=覆盖
    缺口率)/``t1_pullback_gold_ge_gstar``(回拉后投影金 ≥ g* 帧数=金位
    轨迹)。

    凑息禁令(血线硬地板解锁包件②,≤15 族在册授权):死亡线帧不凑息
    ——金不卖回,当轮转化优先(14号稿 §5.4 Y7 口径);返回
    ([], 'blood_floor') 零静默分键。state=None = 语境缺失,禁令按保守端
    照禁(fail-closed:禁令是授权约束,缺读不构成豁免)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        p1_blood_floor,
    )
    if state is None or p1_blood_floor(state):
        return [], 'blood_floor'
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
        saturation_line,
    )
    g_star = saturation_line(cap_resolved)
    gap = g_star - int(gold or 0)
    if gap <= 0:
        return [], 'not_needed'

    def _count(key: str, n: int = 1) -> None:
        if counters is not None:
            counters[key] = counters.get(key, 0) + n

    qualified: list[BenchChar] = []
    for b in bench:
        name = b.char_id or ''
        if b.star != 1:
            continue
        if not predicates.zero_overlap(name, k_members):
            continue
        if name in exclude_names:
            continue   # P60:买面义务集成员禁入卖出资格集(防义务换手)
        if predicates.bench_effect_qualified(
                name, predicates.bench_effect_context(state, b, k_members)):
            continue
        qualified.append(b)
    # 序:刚买件优先(R2-N1),其余 (star, slot) 升序(确定性)
    prefer = set(prefer_names)
    qualified.sort(key=lambda b: (0 if (b.char_id or '') in prefer else 1,
                                  b.star, b.slot))
    out: list[int] = []
    remaining = gap
    sellback = 0
    for b in qualified:
        out.append(b.slot)
        # 1★ 卖回净额 = sell_refund(1, 注册表 cost)(与 funding_support
        # 同款:bench_char_cost 未知名保守估 3,禁字面量双源)
        refund = sell_refund(1, bench_char_cost(b))
        remaining -= refund
        sellback += refund
        if remaining <= 0:
            break
    _count('t1_interest_emit_frames')
    _count('t1_interest_gap_total', gap)
    _count('t1_interest_sellback_total', sellback)
    if sellback >= gap:
        _count('t1_pullback_gold_ge_gstar')
    return out, ''


def funding_support_sell(gold: int, need_gold: int, bench: list[BenchChar],
                         k_members: tuple[str, ...],
                         state: GameState | None = None,
                         *,
                         exclude_names: frozenset[str] | set[str] = frozenset(),
                         ) -> tuple[list[int], str]:
    """「支付能力变现」子域(R13-5/R14-4:支付支撑通道,两臂同开)。

    触发 = 骨架义务动作金不足(gold < need_gold,硬约束①不满足侧的
    筹资面);变现对象 = 凑息档序同资格(1★ ∧ 无后台效果 ∧ 零重叠,
    语境经 ``predicates.bench_effect_context`` 共享装配现读——症3 三
    通道统一;卖回量最小化 [11]);跨帧语义 = 变现金作用于下一备战期
    义务动作(延迟=1 备战期间隔,进遥测 reason)。无对象 ⇒ 空。
    ``exclude_names`` = 买面义务集成员禁入(P60,与凑息卖/M4 燃料同款)。
    """
    if gold >= need_gold:
        return [], 'not_needed'
    out: list[int] = []
    remaining = need_gold - gold
    for b in sorted(bench, key=lambda x: (x.star, x.slot)):
        name = b.char_id or ''
        if b.star != 1:
            continue
        if not predicates.zero_overlap(name, k_members):
            continue
        if name in exclude_names:
            continue   # P60:买面义务集成员禁入卖出资格集
        if predicates.bench_effect_qualified(
                name, predicates.bench_effect_context(state, b, k_members)):
            continue
        out.append(b.slot)
        # 1★ 卖回净额 = sell_refund(1, 注册表 cost) 派生(R196 症6:
        # 禁字面量 3 双源——bench_char_cost 未知名保守估 3 与旧值同构)
        remaining -= sell_refund(1, bench_char_cost(b))
        if remaining <= 0:
            break
    return out, ''
