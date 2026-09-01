# p39 数值自检脚本(证明 docs/game/currency_war/research/proofs/p39-levelup-ev.md 配套)
# 入库 tools/cw/proofs/(可重跑复核;只读代码注册表,不碰游戏)
import sys

import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST, POOL_COPIES_PER_CARD, REFRESH_PROB,
    expected_refreshes, refresh_prob,
)

SHOP_REFRESH_COST = 2          # cw_state.REFRESH_COST_BASE(粗估常量)
XP_PER_BUY = 4                 # cw_state 单一源
XP_TO_NEXT_LEVEL = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}
XP_CLICK_GOLD = 4              # flat-4(ADR-0275 实机 VLM 三帧)


def upgrade_gold(lv: int) -> int:
    need = XP_TO_NEXT_LEVEL[lv]
    clicks = -(-need // XP_PER_BUY)
    return clicks * XP_CLICK_GOLD


def er(lv, cost, star, owned=0, c=0):
    from sr_od.application.currency_war.data.cw_shop_odds import expected_refreshes_for_card, expected_refreshes
    if star == 0:  # 找 1 张:便捷函数的 {2:3,3:9}.get 默认 k=3 会吞掉 1,直调底层
        return expected_refreshes(refresh_prob(lv, cost), DISTINCT_CARDS_PER_COST[cost],
                                  POOL_COPIES_PER_CARD[cost], c, 1, owned)
    return expected_refreshes_for_card(lv, cost, star, owned, c)


print('=== 表:期望刷新数 E(level) × 场景 ===')
scenarios = [
    ('3费 2星(k=3)', 3, 2, [5, 6, 7, 8]),
    ('3费 3星(k=9)', 3, 3, [6, 7, 8, 9]),
    ('4费 2星(k=3)', 4, 2, [6, 7, 8, 9, 10]),
    ('5费 2星(k=3)', 5, 2, [7, 8, 9, 10]),
    ('5费 1张(k=1)', 5, 0, [7, 8, 9, 10]),
]
for name, cost, star, levels in scenarios:
    row = [name]
    for lv in levels:
        e = er(lv, cost, star)
        row.append(f'L{lv} p={refresh_prob(lv, cost):.2f} E={e:.1f} (金{e * SHOP_REFRESH_COST:.0f})')
    print(' | '.join(row))

print()
print('=== 升级金成本(XP 表,cw_state;±20% 标定态)===')
for lv in sorted(XP_TO_NEXT_LEVEL):
    print(f'  L{lv}->L{lv + 1}: {upgrade_gold(lv)} 金')

print()
print('=== 移位价值 ΔV = (E_L − E_L+1) × 2金 vs 升级成本(同窗口搜牌)===')
pairs = [
    ('3费2星核心', 3, 2, 6),
    ('3费3星追三', 3, 3, 6),
    ('4费2星核心', 4, 2, 7),
    ('4费2星核心', 4, 2, 8),
    ('5费2星核心', 5, 2, 8),
    ('5费找1张', 5, 0, 8),
]
for name, cost, star, lv in pairs:
    e0, e1 = er(lv, cost, star), er(lv + 1, cost, star)
    dv = (e0 - e1) * SHOP_REFRESH_COST
    print(f'  {name} L{lv}(E={e0:.1f})→L{lv + 1}(E={e1:.1f}): ΔV={dv:.1f}金; 升级成本={upgrade_gold(lv)}金')

print()
print('=== 口述规则对拍:峰值级 vs +1 级(各费档 argmax p 的等级)===')
for cost in range(1, 6):
    best = max(REFRESH_PROB, key=lambda l: refresh_prob(l, cost))
    probs = {l: refresh_prob(l, cost) for l in range(best, 11)}
    print(f'  {cost}费: 峰值级=L{best} p={probs[best]:.2f}; L{best + 1} p={probs.get(best + 1, 0):.2f}')

print()
print('=== 段带例(3费+4费等权带,w3=w4=1,k=3)===')
band = {}
for lv in (7, 8, 9, 10):
    e3 = er(lv, 3, 2)
    e4 = er(lv, 4, 2)
    band[lv] = e3 + e4
    print(f'  L{lv}: E3={e3:.1f} E4={e4:.1f} SigmaE={band[lv]:.1f}')
for lv in (7, 8, 9):
    dv = (band[lv] - band[lv + 1]) * SHOP_REFRESH_COST
    u = upgrade_gold(lv)
    verdict = '净正->升级' if dv >= u else '净负->停止'
    print(f'  L{lv}->L{lv + 1}: DeltaV_band={dv:.1f} vs U={u} => {verdict}')
print('  (贪心停止点既非3费峰(L7)亦非4/5费峰(L10)——段带解不在单费峰值级)')
# 断言锁(表值进锁防静默漂移;容差0.05按未舍入值,边际锁容差0.3吸收打印舍入)
assert abs(band[7] - 118.9) < 0.05 and abs(band[8] - 73.1) < 0.05 and abs(band[9] - 69.9) < 0.05 and abs(band[10] - 71.5) < 0.05
assert abs((band[7] - band[8]) * 2 - 91.5) < 0.3
print('  [assert] 段带表值锁定通过')

# --- L 联动批:A4 的 C_int = L(g,U_L,R_全局,Ī) 边界门现算(p47 双轨迹递推,Ī 中位 7) ---
# 口径单一源 = p47(loss_exact);此段复算文档 A4/数值表的「5费单张 L8→L9」「4费2星 L7→L8」门区间。
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from p47_check import loss_exact  # noqa: E402

print()
print('=== L 联动批:C_int = L(g,U_L,R_global,I=7) 边界门(g=74+-10 亲算) ===')
for d, dv, tag in ((72, 84.0, '5cost single L8->L9'), (52, 103.3, '4cost 2star L7->L8')):
    for R in (3, 9):
        # 扫描域注(终局总攻击扫描域勘误):g 从 d 起(金位低于批成本的格买不起,无门义)到 84;
        # 文档带「3-20」的 3 来自 g=d 端(d=72 时恰可买),[64,84] 子扫描会漏 g=d-8 的低端——全带 [d,84] 才与文档对齐
        ls = [loss_exact(g, d, R, 7) for g in range(d, 85) if g >= d]
        print(f'  {tag} R_global={R}: L={min(ls)}-{max(ls)} -> gate {dv} vs {d + min(ls)}-{d + max(ls)}')
        if d == 72 and R == 3:
            assert min(ls) == 10 and max(ls) == 14, '5cost R=3 gate band 82-86'
        if d == 72 and R == 9:
            assert min(ls) == 13 and max(ls) == 20, '5cost R=9 gate band 85-92 (all fail)'
        if d == 52:
            assert max(ls) <= 20, '4cost gate passes full band (103.3 vs <=72)'
# 边界翻转点:R=3 时仅高位段过门(84 >= 72+L 即 L<=12)
assert loss_exact(78, 72, 3, 7) == 12 and loss_exact(76, 72, 3, 7) == 13
print('  [assert] flip point R=3: g>=78 pass (L<=12), g<=76 fail -- "upgrade" NOT default')
# I 带 [6,8] 全带包络(文档 A4 勘误注:初稿预告 81-86/81-92 的真实口径)
for R in (3, 9):
    allv = [loss_exact(g, 72, R, i) for g in range(64, 85) if g >= 72 for i in (6, 7, 8)]
    print(f'  envelope I in [6,8] R={R}: gate 84 vs {72 + min(allv)}-{72 + max(allv)}')
print('  [assert] L linkage gates locked')
