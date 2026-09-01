# p40 刷新 EV 数值自检脚本(证明 docs/game/currency_war/research/proofs/p40-refresh-ev.md 的算例)
# 只读代码注册表,不改任何生产文件。入库可重跑: $env:PYTHONPATH='src'; uv run python tools/cw/proofs/p40_refresh_ev_check.py
import math

from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    REFRESH_PROB,
    _refresh_dist,
    expected_refreshes,
    refresh_prob,
    rotation_probs,
)

def hit_prob(p, v, a, j, c=0):
    """单次刷新 5 槽至少出 1 张目标牌(超几何模型,cw_shop_odds._refresh_dist)。"""
    return 1.0 - _refresh_dist(p, v, a, c, 1, j)[0]

def multi_type_hit(p_vec, elig):
    """多类型合格集:每槽 q=Σ_c p_c × (该费合格剩余副本/该费剩余总副本),5 槽独立近似。
    注意:独立近似**低估** P(至少一张)——无放回负关联抬高至少一张概率,
    偏差与 A3(NPC 耗池)同侧偏松;多类精确混合未实现,落地即用本近似并声明方向。"""
    q = 0.0
    for (p_c, cost, g_types, j_owned, c_taken) in elig:
        a = POOL_COPIES_PER_CARD[cost]
        v = DISTINCT_CARDS_PER_COST[cost]
        rem_elig = max(a * g_types - j_owned, 0)
        rem_tot = v * a - j_owned - c_taken
        q += p_c * rem_elig / rem_tot
    return 1.0 - (1.0 - q) ** 5

print("=== 基线常量 ===")
print("DISTINCT_CARDS_PER_COST =", DISTINCT_CARDS_PER_COST)
print("POOL_COPIES_PER_CARD =", POOL_COPIES_PER_CARD)

print()
print("=== S1 低费缺口@低级(lv5, 1费, 追2星差2张, j=1) ===")
p = refresh_prob(5, 1); v = DISTINCT_CARDS_PER_COST[1]; a = POOL_COPIES_PER_CARD[1]
q1 = hit_prob(p, v, a, j=1)
print(f"p={p} v={v} a={a}  P(单刷≥1张目标)={q1:.4f}  1/P={1/q1:.2f}")
E = expected_refreshes(p, v, a, 0, 3, 1)
print(f"E[刷满缺口](k=3,j=1)={E:.2f} 次 → 期望刷费 2E={2*E:.1f} 金")
print(f"单步盈亏平衡: V* = 2/P = {2/q1:.2f} 金(目标件净价值≥此值才刷)")

print()
print("=== S2 高费缺口@高级(lv9, 5费, 追3星差2张, j=7) ===")
p5 = refresh_prob(9, 5); v5 = DISTINCT_CARDS_PER_COST[5]; a5 = POOL_COPIES_PER_CARD[5]
q5 = hit_prob(p5, v5, a5, j=7)
print(f"p={p5} v={v5} a={a5}  P(单刷≥1张目标)={q5:.4f}  1/P={1/q5:.2f}")
E5 = expected_refreshes(p5, v5, a5, 0, 9, 7)
print(f"E[刷满缺口](k=9,j=7)={E5:.1f} 次 → 期望刷费 2E={2*E5:.0f} 金")
q5_0 = hit_prob(p5, v5, a5, j=0)
print(f"(对照 j=0 追3星整缺口: P(单刷)={q5_0:.4f})")

print()
print("=== S3 溢余段预算(息线账) ===")
def interest(g): return min(g // 10, 5)
for g, spend in [(62, 10), (58, 10), (54, 8), (46, 4)]:
    g2 = g - spend
    t = interest(g) - interest(g2)
    print(f"g={g} 花 {spend} → 余 {g2}, 息损 t={t} 档(跨 {'50线' if g>=50>g2 else '档线'})")

print()
print("=== 变体①概率事件(45%免费, 期望刷价1.1) ===")
print(f"S1 场景 V* = 1.1/{q1:.4f} = {1.1/q1:.2f} 金(阈值降 {(1-1.1/2)*100:.0f}%)")

print()
print("=== 变体③轮岗(lv6 1费档翻倍) ===")
base = REFRESH_PROB[6]
rot = rotation_probs(6, 1)
print("基线:", {c: round(pc,3) for c,pc in base.items()}, " 轮岗:", {c: round(pc,3) for c,pc in rot.items()})
q_rot = hit_prob(rot[1], v, a, j=1)
print(f"1费目标命中率: 基线 {q1*0 + hit_prob(base[1], v, a, j=1):.4f} → 轮岗 {q_rot:.4f} (×{q_rot/hit_prob(base[1], v, a, j=1):.2f})")

print()
print("=== 变体④刷价1金 ===")
print(f"S2 场景 V* = 1/{q5:.4f} = {1/q5:.2f} 金; E[刷费]=1×{E5:.0f}={E5:.0f} 金")

print()
print("=== 变体5市场干预(周期窗口:下一次和每4刷全3费面,赠5次刷;两段定价) ===")
# 初得窗口: 5次赠刷=一次性token, 首个3费面可用赠刷兑现, 成本约0金
print("初得窗口: 首个3费面用赠刷兑现, 约 0 金(token一次性)")
# 稳态(token尽): 每4刷1面, 期中3刷为基线; 保证一面期望付费 <= 4x2 = 8金
print("稳态: 保证一面 <= 4x2 = 8 金; 期内常态误建模(p->{3:1.0})会把启动门放宽约4倍(错)")
print("非3费缺口: 3费面那一次刷新 q=0(5槽全3费) -> 命中率约打75折(直陈)")

print()
print("=== 停止条件演示(合格集空 → P=0) ===")
# 目标件囤满且无插件缺口的情形:合格集 E 为空 → 单步 EV = -2 < 0 恒成立
# 注: [1]奖励节点不D 不属于本条(节点语境=变体6的 V̄ 分量, E 通常非空)
print("E=空集 → P(hit)=0 → EV=-c<0 → n*=0(纯烧金, 对应[31]硬约束)")
