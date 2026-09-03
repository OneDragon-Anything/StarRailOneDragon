"""criteria/sell——EV 卖面(§2.2;fuel_sell/protected_sell 在 mandate/谓词层)。

三个发射/通道位:line_switch_sell(换线塌缩出口)、sell_for_interest
(凑息档 EV 面,臂①旁路)、funding_support_sell(支付能力变现子域,
R13-5 支付支撑通道,两臂同开、mandate=false+funding_support=true)。

fail 方向(§2.2.1 唯一权威规格):不可逆卖面缺输入(λ 表损坏/域外/
第四态无载/sell_refund 损坏)⇒ 不评不卖;u/V_ms🔴 ⇒ line_switch_sell
比较臂无载 ⇒ 不卖 + 出口确定性关闭(proof.should_switch 前置门同构)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.decision.cw4.audit import provisional
from sr_od.application.currency_war.decision.cw4.statefn import predicates
from sr_od.application.currency_war.decision.cw4.statefn.vopt import (
    refund_full_star_ok,
)
from sr_od.application.currency_war.kernel.cw_state import (
    bench_char_cost,
    sell_refund,
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
                      ) -> tuple[list[int], str]:
    """凑息档 EV 面(R20-1 资格谓词:仅桶不动件)。

    对象 = 1★ ∧ 无后台效果 ∧ 与锁线零重叠(R17-2 零参数桶判断;
    挂后台效果资格谓词 = predicates.bench_effect_qualified,语境经
    ``predicates.bench_effect_context(state, unit, k_members)`` 共享
    装配现读——IMPL_ADV_R200 症3:三卖面通道统一消费,禁各通道自拼;
    ``state=None``(旧调用面)按装配函数缺省保守端处置)。
    V_comp 表生成失败(T_SEARCH_A🔴)⇒ 不卖(fail-closed)。
    升档器触发帧 F7 禁令消费位在 entry(顾问信号位)——本函数不自带段判断。
    """
    if provisional.is_none('T_SEARCH_A'):
        return [], 't_search_unavailable'
    out: list[int] = []
    for b in bench:
        name = b.char_id or ''
        if b.star != 1:
            continue
        if not predicates.zero_overlap(name, k_members):
            continue
        if predicates.bench_effect_qualified(
                name, predicates.bench_effect_context(state, b, k_members)):
            continue
        out.append(b.slot)
    return out, ''


def funding_support_sell(gold: int, need_gold: int, bench: list[BenchChar],
                         k_members: tuple[str, ...],
                         state: GameState | None = None,
                         ) -> tuple[list[int], str]:
    """「支付能力变现」子域(R13-5/R14-4:支付支撑通道,两臂同开)。

    触发 = 骨架义务动作金不足(gold < need_gold,硬约束①不满足侧的
    筹资面);变现对象 = 凑息档序同资格(1★ ∧ 无后台效果 ∧ 零重叠,
    语境经 ``predicates.bench_effect_context`` 共享装配现读——症3 三
    通道统一;卖回量最小化 [11]);跨帧语义 = 变现金作用于下一备战期
    义务动作(延迟=1 备战期间隔,进遥测 reason)。无对象 ⇒ 空。
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
