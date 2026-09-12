"""S(动态目标线)/ B / n̄ / ρ(P48 结构形状;NMF §2 对应行)。

S = B + 息饱和线分量(10×cap_resolved 条件式组装,canonical 表行 10⑤⑥)
+ Σ_w 窗口预留卡价 + E[刷费]×2(P48 ② / 01_strategy_layer §4.4 [41] S 式;
式结构与求和对象以 01 原文为唯一式源,+50 字面系默认局 cap=5 投影——数值
分量按 cap 条件式组装:升帽可达局 10×cap_sup / 不可达局 10×cap_resolved
现值 / 买断制 0,R129 辖域仲裁)。
n̄(resolved 自然 XP 流)= 买牌 +4/张 ∪ 投资每节点/每刷 XP 流逐项求和
(P48 A3;估计器🔴,NMF §3.3 #5)。ρ(整买价值率)= (ΔV_band+ΔV_pop)/R,
仅双臂门真时 >0(摊派口径🔴 #4,均匀摊保守首版)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_economy import XP_PER_BUY
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
    saturation_line,
)


def b_target(need_xp: int, xp_cur: int, nbar: int) -> int:
    """B = 4⌈max(0, need−xp_cur−4n̄)/4⌉(P48 ②;批成本按 XP 单价 4 金取整)。"""
    gap = max(0, need_xp - xp_cur - XP_PER_BUY * nbar)
    return 4 * -(-gap // 4)


def nbar(buy_count_per_round: int = 0,
         invest_xp_per_node: int = 0) -> int:
    """n̄(resolved 自然 XP 流,按轮折算的张数口径)= XP_PER_BUY×买牌数 +
    投资 XP 流(P48 A3;buy=本窗口自然入手张数,invest_xp_per_node=resolved
    投资每节点送 XP 折张——调用方按 cw_investments 注册表现读,禁拍死值)。"""
    return XP_PER_BUY * buy_count_per_round + invest_xp_per_node


def s_line(b: int, cap_resolved: int, window_reserve_costs: list[int],
           expected_refresh_fee: int) -> int:
    """S 动态目标线 = B + 息饱和线 + Σ_w 窗口预留卡价 + E[刷费]×2。

    息饱和线分量 = ``saturation_line(cap_resolved)``(默认局 50/买断制 0/
    息律局按锁存 cap_sup 组装——cap 口径条件式由调用方按 canonical 表
    行 10⑤⑥ 供给 resolved 值);E[刷费]×2 = 双刷预算(P48 窗口口径)。"""
    return (b + saturation_line(cap_resolved)
            + sum(window_reserve_costs) + expected_refresh_fee * 2)


def rho(delta_v_band: float, delta_v_pop: float, rounds: int) -> float | None:
    """ρ(整买价值率)= (ΔV_band+ΔV_pop)/R——**仅双臂门真时 >0**;摊派口径
    【拟】🔴(NMF §3.3 #4,均匀摊保守首版,阈值表随对拍 2 重标)。本函数
    只做结构除式;ΔV 项的标定状态由调用方经 provisional 槽位判定,False 期
    整面 fail-closed(返回 None=不产追加动作,不向骨架渗漏否决,NMF §5.3)。"""
    if rounds <= 0:
        return None
    return (delta_v_band + delta_v_pop) / rounds


__all__ = ['b_target', 'nbar', 'rho', 's_line']
