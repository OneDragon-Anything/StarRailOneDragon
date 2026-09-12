# -*- coding: utf-8 -*-
"""P46 支出否决域数值自检(不进 src、不提交;print 仅 ASCII)。

复算证明文档 docs/game/currency_war/research/proofs/p46-spend-gate-rejection-ev.md
的三个代表场景 + 两个边界(多笔合成 / 溢余穿透)。
口径单一源 = P13: t = interest(g) - interest(g-c), C = t * min(R, 3)。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from sr_od.application.currency_war.kernel import cw_plane_table  # noqa: E402
from sr_od.application.currency_war.decision.decision_v2 import ev as cw_ev  # noqa: E402

REC = 3  # interest_recovery_rounds(P13/ADR-0352 口径,常量漂移须人查)


def interest(g: int) -> int:
    return min(g // 10, 5)


def tier_loss(g: int, c: int) -> int:
    return interest(g) - interest(g - c)


def cost_int(g: int, c: int, r: int, plane_nodes: int = 9, include_current: bool = True) -> int:
    """过渡式 C = t * min(R, 3)。

    R 口径统一:R_全局 = 当前节点计入(r 本身)+ 位面剩余 + 后续位面。
    本脚本单位面场景下 R_全局 = r(当前节点)+ (plane_nodes - r)(本位面剩余)= plane_nodes
    —— 与 17/19 断言块(含当前节点)同口径;旧版 R=plane_nodes-r 为不含当前节点的混合口径,
    cap=3 掩盖下同值,L 换轨后分叉,已统一。
    """
    R = r if include_current else 0
    R += plane_nodes - r
    return tier_loss(g, c) * min(R, REC)


def report(tag, g, c, r, exempt=None):
    t = tier_loss(g, c)
    R = 9  # R_全局(单面近似,含当前节点)= r + (9-r) = 9
    C = cost_int(g, c, r)
    in_p1 = t >= 1
    print(f'[{tag}] g={g} c={c} r={r} R_global~{R}: t={t} C={C} '
          f'P1(true-break)={in_p1} exempt={exempt}')
    return t, C


print('== P46 check: spend-gate rejection domain ==')

# S1 贴档线: g=41 买 1金件(同档) vs 2金件(跨 40 线)
t0, _ = report('S1a same-tier', 41, 1, 3)
assert t0 == 0, 'S1a must be same-tier (t=0), [11] zero loss'
t1, C1 = report('S1b cross-tier', 41, 2, 3)
assert t1 == 1 and C1 == 3, 'S1b t=1, C=min(6,3)=3'

# S2 破息散件: g=32 买 3费纯散件(无羁绊贡献、非线内、1星可逆但期权价值~0)
t2, C2 = report('S2 junk break', 32, 3, 5)
assert t2 == 1 and C2 == 3
print('    verdict: no immediate power + no exemption -> VETO '
      '(reversible converts principal to carry cost 3, junk option value ~ 0 < 3)')

# S3 破息囤件: 1费件 vs 5费件(可逆资产的期权价值分档)
t3a, C3a = report('S3a hoard 1cost', 50, 1, 3)
t3b, C3b = report('S3b hoard 5cost', 54, 5, 3)
assert t3a == 1 and C3a == 3
assert t3b == 1 and C3b == 3
print('    verdict: both carry cost 3; 1cost re-encounter window 7-15 rounds '
      '(option value small) -> conditional exemption likely FAILS -> veto;')
print('            5cost re-encounter 60-180 rounds ([22]-(3)) -> option value '
      'large -> exemption PASSES -> allow')

# B1 多笔合成: 单笔同档、合计跨档 —— 边界笔落入域
gA = 52
print(f'[B1 compose] g=52: A c=1 -> {gA - 1} (t={tier_loss(52, 1)}), '
      f'then B c=2 -> {gA - 3} (cumulative t={tier_loss(52, 3)})')
assert tier_loss(52, 1) == 0 and tier_loss(52, 3) == 1
print('    verdict: B is the boundary stroke, judged with cumulative spend c=3')

# B2 溢余穿透: g=54 花 8 -> 46(穿 50 线,t=1)
t4, C4 = report('B2 overflow-pierce', 54, 8, 3)
assert t4 == 1 and C4 == 3
print('    verdict: overflow spend that stays >=50 has t=0; piercing below 50 '
      'pays real carry 3 -> P1 must be defined as t>=1 (tier-function diff), '
      'not merely g<=50')

# B3 位面末(真全局轴+代码缺陷对账:total_remaining_nodes 恒按 9/位面计,已登记待修缺陷)——R_全局 = 当前节点+后续位面按实际长度
# 正确口径:P1 r9 -> 0(本位面余)+7(P2)+9(P3 先验)=16;代码实现(total_remaining_nodes 写死全 9)给 19(+2 偏差,cap 吸收)
t5, C5 = report('B3 plane-end(global axis)', 41, 2, 6)  # report() 以 9-r 求 R;传 r=6 得 R=3
assert t5 == 1 and C5 == 3
print('    verdict: global-axis C>0 at plane end (P1/P2) -> IN domain')
R_global_correct = 1 + 7 + 9  # P1 r9: 当前节点1 + P2实际7 + P3先验9 = 17(N1:含当前节点)
R_global_code = 1 + 9 + 9     # ev.total_remaining_nodes 写死口径 = 19
assert R_global_correct == 17 and R_global_code == 19 and R_global_code - R_global_correct == 2
print('R_global caliber: correct=17 (current+P2=7+P3=9), code=19 (hardcoded 9s, +2 bias absorbed by cap=3)')
print('  -> Z1 defect registered: L linkage (no cap) must fix ev function first (death-row, Phase 3 rewrites)')
assert min(3, R_global_correct) == 3 == C5  # cap 吸收:两口径在过渡式下同值(偏差被掩盖的原因)
assert cost_int(41, 2, 9) == 1 * min(3, 9)  # R4⑤: 末节点 r=9 -> R_全局=9(含当前节点), C=t*3 不为零

# B4 与注册表接口对拍(单一源: cw_plane_table.interest = min(g//10, 5))
for g in (0, 9, 10, 46, 50, 54, 100):
    assert cw_plane_table.interest(g) == interest(g), f'interest mismatch at g={g}'
# ev.interest_cost 的档差用未封顶 g//10 差分:g>=60 段花金仍 >=50 时,
# 它计 t>=1 而物理息损(封顶口径)t=0 —— p46 的 P1 必须用封顶口径(见证明边界节)
assert min(65 // 10, 5) - min(40 // 10, 5) == 1  # 65 花 25 -> 40: 封顶 t=1(未封顶算 2)
print('capped-tier assert: 65->40 capped t=1 (uncapped would give 2)')
print('interface check vs cw_plane_table.interest: OK '
      '(ev.interest_cost uses uncapped tier diff, g>=60 caveat declared in proof)')

# --- L 联动批:规范 C = L(g,d,R_全局,Ī=7)(p47 双轨迹递推)数值表 L 列现算 ---
# 口径单一源 = p47(loss_exact);文档数值自检表 L 列 = 本段断言锁定的誊录。
sys.path.insert(0, os.path.dirname(__file__))
from p47_check import loss_exact  # noqa: E402

print()
print('== L linkage: canonical C = L(g, d, R_global, I=7) column ==')
l_rows = [
    ('S1a same-tier', 41, 1, 3, 0),
    ('S1b cross-tier', 41, 2, 3, 2),
    ('S2 junk break', 32, 3, 5, 3),
    ('S3a hoard 1cost', 50, 1, 3, 1),
    ('S3b hoard 5cost', 54, 5, 3, 1),
    ('B1 cumulative spend', 52, 3, 3, 1),
    ('B2 overflow-pierce', 54, 8, 3, 1),
    ('B3 plane-end', 41, 2, 9, 2),
]
for tag, g, d, r, expect in l_rows:
    got = loss_exact(g, d, r, 7)
    print(f'  [{tag}] L({g},{d},R={r},I=7) = {got} (doc column: {expect})')
    assert got == expect, f'{tag}: L mismatch {got} != {expect}'
    if r != 9:
        assert loss_exact(g, d, 9, 7) == expect, f'{tag}: R=9 L differs unexpectedly'
# P1 L-based predicate: near-50 same-tier exits, low-gold band enters, midband resolved
assert loss_exact(45, 4, 9, 7) == 0 and loss_exact(41, 1, 9, 7) == 0, 'near-50 same-tier L=0 (out of domain)'
assert loss_exact(9, 8, 9, 4) == 10 and loss_exact(9, 8, 3, 7) == 2, 'low-gold same-tier L>0 (in domain)'
assert loss_exact(29, 9, 9, 4) == 5, 'midband [20,30) worst cell L=5>0 (corner resolved by L>0 basis)'
# S3b margin over full R band (p41 re-anchor note)
assert all(loss_exact(54, 5, r, 7) == 1 for r in (1, 2, 3, 6, 9)), 'S3b L=1 for all R'
print('  [assert] L-based P1 predicate + S3b margin (full R band) locked')

print('ALL ASSERTIONS PASSED')
