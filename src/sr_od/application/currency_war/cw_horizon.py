"""日程感知资源规划器 V1(03 号重设计提案;DP + 影子价格;2026-08-16)。

**V1 定位 = 涌现验证,不是切流**:只喂机制常量(升价/息规则/商店概率/节点收入/掉血先验),
离线解「剩余日程上的最优资源调度」,检验能否从第一性原理复现人类 meta:
- plaza 784 篇节奏 labels(1费 carry→5级搜 / 3费→7级搜 / 5费→9级;P1 末 7 / P2 早 8);
- 用户满息基调(2026-08-16):高难度下持续满息才有金推等级/追星 —— 在什么日程/血量
  条件下 DP 自己给出「攒到 50」的姿态(而非手写门)。

**通过判据(V1)**:DP 解的姿态序列与 plaza labels 的等级停留带一致(±1 级),且金轨迹
呈现「息引擎攒 50 → 花到 0/10 的脉冲」形态(人类 meta 的「卡利息慢慢升级」)。
不通过 = 精确定位模型缺哪块(掉血项/收入项/约束),零实机成本。

机制常量单一源:XP_TO_NEXT_LEVEL/XP_PER_BUY(cw_state)、REFRESH_PROB/POOL_COPIES(cw_shop_odds)、
INTEREST_THRESHOLD(cw_factions)。掉血项是**可替换插件**(V1 用平坦先验,后续接
PerformanceTracker/outcome model)。

纯函数,不碰游戏/session;离线可测。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_shop_odds import (
    refresh_prob,
)
from sr_od.application.currency_war.cw_state import XP_PER_BUY, XP_TO_NEXT_LEVEL

# ===== 日程结构(先验;后续由 read_node_sequence 实测覆盖) =====
# 每位面节点数(M39 实测 9;boss 在位面末)。节点类型先验:8 普通 + 1 boss/位面。
NODES_PER_PLANE: int = 9
BASE_INCOME: int = 5          # 每节点基础奖励金(结算屏「基础奖励 5」实测)
BOSS_BONUS: int = 2           # boss 节点额外金(粗估,calibration 点)
WIN_STREAK_STEP: int = 1      # 连胜每步 +1 金(2 连起;粗估)

# 掉血先验(V1 平坦;插件可替换):按板强档的每战斗节点期望掉血。
# 板强档 b: 0=散装 1=半成型 2=成型 3=强。数值为 PerformanceTracker.EXPECTED_DROP 量级先验。
HP_LOSS_PRIOR: dict[int, float] = {0: 14.0, 1: 8.0, 2: 3.5, 3: 1.5}
HP_DANGER: int = 30          # 低于此血 → 生存约束收紧(安全分位用)
GOLD_CAP_INTEREST: int = 50  # 息封顶档(INTEREST_THRESHOLD 同源;显式命名供 DP 用)

# 升级花费:每击 4 XP 花 4+lv 金(按钮实读 level_up_cost≈4+lv;ADR-0129)。
def xp_click_cost(level: int) -> int:
    return 4 + level

def clicks_to_level(level: int, cur_xp: int) -> int:
    """当前级 → 下一级还需购买经验次数(ceil;(need-cur)/XP_PER_BUY)。"""
    need = XP_TO_NEXT_LEVEL.get(level, 84)
    return max(0, -(-(need - cur_xp) // XP_PER_BUY))

# ===== DP 状态与求解 =====
# 状态离散化:金(步长 5,0..110)、等级(1..10)、血(桶宽 5,20..100)、节点位置(0..27)、板强档(0..3)。
# 值函数 V[t][g][L][h][b] = 从该状态起、按最优姿态到日程终点的期望生存分。
# 姿态动作(不定买谁):{存息(0 击 0 刷), 升级 k 击(k≤4), D 刷 r 次(r≤6), 升+刷 组合}。

GOLD_STEP: int = 5
GOLD_MAX: int = 110
HP_BUCKET: int = 5
HP_MIN: int = 20
HP_MAX: int = 100
LEVEL_MIN: int = 1
LEVEL_MAX: int = 10
BOARD_TIERS: int = 4
TOTAL_NODES: int = NODES_PER_PLANE * 3

SURVIVAL_W: float = 10.0     # 终局存活奖励
GOLD_RESIDUAL_W: float = 0.02  # 终局残余金 ε 权重(03 号:max P(活)+ε·E(残金))
LEVEL_RESIDUAL_W: float = 0.05


@dataclass
class Posture:
    """某状态下的最优姿态(DP 解的运行时消费物;03 号 NodeGoal 的未来替身)。"""
    save: bool = True            # 本节点是否「存息」(不升级不 D)
    xp_clicks: int = 0           # 买经验次数(0..4)
    refresh_budget: int = 0      # D 刷预算(0..6)
    quality_spend: int = 0       # 提质量花费档(0=不花,1..3 = 板强档目标提升档,V1 概略)
    v: float = 0.0               # 该姿态的值
    tag: str = ''                # 诊断标签(如 '攒息-满息未达'/'追级-息后余金'/'D牌-窗口内')


@dataclass
class HorizonSolution:
    """DP 全解(离线算一次,运行时查表)。"""
    # policy[(t,g,L,h,b)] = Posture;值函数同键 float。
    policy: dict[tuple, Posture] = field(default_factory=dict)
    value: dict[tuple, float] = field(default_factory=dict)

    def posture(self, t: int, gold: int, level: int, hp: int, board: int) -> Posture:
        """运行时查询(连续值离散化进表);缺键回退保守姿态(存息)。"""
        g5 = min(gold // GOLD_STEP * GOLD_STEP, GOLD_MAX)
        h5 = min(max(hp, HP_MIN), HP_MAX) // HP_BUCKET * HP_BUCKET
        return self.policy.get((t, g5, min(max(level, LEVEL_MIN), LEVEL_MAX), h5, board)) or Posture(
            save=True, tag='fallback')


def interest(gold: int) -> int:
    """息:每 10 金 1 息,封顶 5(GOLD_CAP_INTEREST=50)。"""
    return min(gold // 10, GOLD_CAP_INTEREST // 10)


def node_income(t: int, streak: int) -> int:
    """节点收入(先验):基础 5 + boss 附加 + 连胜步。streak 为当前连胜数。"""
    inc = BASE_INCOME
    if (t + 1) % NODES_PER_PLANE == 0:
        inc += BOSS_BONUS
    if streak >= 2:
        inc += min(streak - 1, 4) * WIN_STREAK_STEP
    return inc


def _roll_uplift(refreshes: int, level: int, target_cost: int, owned: int, copies_wanted: int) -> float:
    """D 刷的板强档期望提升(V1 概略插件)。

    每次 refresh 出目标费用期望张数 = 5×p(level,cost);其中目标牌占比 = 1/v(超几何期望)。
    板强档近似:凑齐 copies_wanted 张(如 2星=3 张)升一档。给**单调有界**的插值,
    不精确建模(那是 outcome model 的事),只保序:更多刷 → 更接近升档,边际递减。
    """
    p = refresh_prob(level, target_cost)
    if p <= 0:
        return 0.0
    per_refresh = 5 * p / max(DISTINCT_CARDS_PER_COST_CACHE.get(target_cost, 13), 1)
    expected = per_refresh * refreshes + owned
    # 边际递减到达 copies_wanted(如 3 张 = 2星)
    import math
    return max(0.0, 1.0 - math.exp(-expected / max(copies_wanted, 1)))


DISTINCT_CARDS_PER_COST_CACHE: dict[int, int] = {1: 14, 2: 13, 3: 13, 4: 12, 5: 9}


def solve(hp_loss_fn=None, board_cost_fn=None) -> HorizonSolution:
    """离线解剩余日程 DP(逆向递推;~27×23×10×17×4 ≈ 1.7e5 状态 × ~40 姿态 ≈ 7e6 评估,秒级)。

    Args:
        hp_loss_fn: (board_tier, t) → 期望掉血(V1 默认平坦先验;插件可替换成 tracker 实测)。
        board_cost_fn: (board_tier_from, to) → 提质量花费金(V1:每档 10 金粗估)。
    """
    if hp_loss_fn is None:
        hp_loss_fn = lambda b, t: HP_LOSS_PRIOR[b]  # noqa: E731
    if board_cost_fn is None:
        board_cost_fn = lambda f, t: 10 * max(0, t - f)  # noqa: E731

    sol = HorizonSolution()
    g_range = list(range(0, GOLD_MAX + 1, GOLD_STEP))
    h_range = list(range(HP_MIN, HP_MAX + 1, HP_BUCKET))
    # 终局边界:存活权重 + 残余资源
    for g in g_range:
        for L in range(LEVEL_MIN, LEVEL_MAX + 1):
            for h in h_range:
                for b in range(BOARD_TIERS):
                    sol.value[(TOTAL_NODES, g, L, h, b)] = (
                        SURVIVAL_W + GOLD_RESIDUAL_W * g + LEVEL_RESIDUAL_W * L
                        if h > HP_DANGER else SURVIVAL_W * 0.3 + GOLD_RESIDUAL_W * g
                    )
    # 逆向递推
    for t in range(TOTAL_NODES - 1, -1, -1):
        for g in g_range:
            for L in range(LEVEL_MIN, LEVEL_MAX + 1):
                for h in h_range:
                    for b in range(BOARD_TIERS):
                        best_v = -1e18
                        best_p = Posture()
                        # 姿态枚举:存息(基线)/ 升 k 击 / D r 刷 / 升+刷
                        # 提质量(板强档):与 D 刷互为替代路径,V1 合并进 D 刷的 board 提升。
                        for xp_k in (0, 2, 4):
                            for roll_r in (0, 2, 4, 6):
                                spend = xp_k * xp_click_cost(L) + roll_r * 2
                                if spend > g:
                                    continue
                                g_after_spend = g - spend
                                # 升级:每击 4 XP;击数推等级(xp 精确追踪略,V1 按每 2 击≈1 级概略)
                                L2 = min(LEVEL_MAX, L + (xp_k // 2))
                                # D 刷的板强档期望提升(概略插件;target_cost 随等级)
                                tgt_cost = 1 if L <= 3 else (2 if L <= 5 else (3 if L <= 7 else 4))
                                board_up = _roll_uplift(roll_r, L2, tgt_cost, owned=b, copies_wanted=3)
                                b2_expect = min(BOARD_TIERS - 1, b + board_up)
                                # 下一状态:节点结算(收入+息)→ 战斗(掉血);金对齐步长(收入含奇数)
                                inc = node_income(t, streak=2)
                                g_next = min(GOLD_MAX,
                                             (g_after_spend + inc + interest(g_after_spend)) // GOLD_STEP * GOLD_STEP)
                                # 板强档按期望线性化(V1;精确需按档枚举)
                                h_drop = hp_loss_fn(int(round(b2_expect)), t)
                                h_next_raw = h - h_drop
                                # 生存约束:桶不越过 HP_MIN(=死)
                                if h_next_raw <= 0:
                                    v_next = 0.0   # 死亡终端
                                else:
                                    h_next = min(HP_MAX, max(HP_MIN, int(h_next_raw) // HP_BUCKET * HP_BUCKET))
                                    v_next = sol.value[(t + 1, g_next, L2, h_next, int(round(b2_expect)))]
                                # 姿态即时分(V1 概略:残余资源 ε 已在终局;这里只传 v_next)
                                v = v_next
                                if v > best_v:
                                    best_v = v
                                    tag = []
                                    if xp_k > 0:
                                        tag.append(f'升{xp_k}击')
                                    if roll_r > 0:
                                        tag.append(f'D{roll_r}')
                                    if not tag:
                                        tag.append('存息')
                                    best_p = Posture(save=(xp_k == 0 and roll_r == 0),
                                                     xp_clicks=xp_k, refresh_budget=roll_r,
                                                     quality_spend=0, v=v, tag='-'.join(tag))
                        sol.value[(t, g, L, h, b)] = best_v
                        sol.policy[(t, g, L, h, b)] = best_p
    return sol


# ===== V1 涌现验证(离线脚本入口) =====

def _validate_emergence() -> dict:
    """模拟一条 DP 指导的轨迹,输出与 plaza labels 的对拍报告(离线,无游戏)。"""
    sol = solve()
    # 初始:t=0,金 10,lv1(开局),hp 100,板 0(散装)
    t, g, L, h, b = 0, 10, 1, 100, 0
    trace = []
    streak = 0
    while t < TOTAL_NODES:
        p = sol.posture(t, g, L, h, b)
        trace.append({'t': t, 'plane': t // NODES_PER_PLANE + 1, 'node': t % NODES_PER_PLANE + 1,
                      'gold': g, 'level': L, 'hp': h, 'board': b, 'posture': p.tag,
                      'xp': p.xp_clicks, 'roll': p.refresh_budget})
        # 执行姿态(与 solve 转移一致)
        spend = p.xp_clicks * xp_click_cost(L) + p.refresh_budget * 2
        g = max(0, g - spend)
        L = min(LEVEL_MAX, L + (p.xp_clicks // 2))
        tgt_cost = 1 if L <= 3 else (2 if L <= 5 else (3 if L <= 7 else 4))
        b = min(BOARD_TIERS - 1, b + _roll_uplift(p.refresh_budget, L, tgt_cost, b, 3))
        inc = node_income(t, streak=2)
        g = min(GOLD_MAX, g + inc + interest(g))
        h_drop = HP_LOSS_PRIOR[int(round(b))]
        h = max(0, h - h_drop)
        if h <= 0:
            trace[-1]['dead'] = True
            break
        t += 1
    # 对拍:各节点等级 vs plaza meta(P1末7/P2早8/P3末9-10)
    checks = []
    for tr in trace:
        exp_level = 7 if tr['t'] < 9 else (8 if tr['t'] < 18 else 9)
        checks.append({'t': tr['t'], 'level': tr['level'], 'plaza_expected': exp_level,
                       'match': abs(tr['level'] - exp_level) <= 1})
    # 金轨迹形态:息引擎脉冲(攒 50 → 花)
    gold_series = [tr['gold'] for tr in trace]
    report = {
        'survived': h > 0 and t >= TOTAL_NODES - 1,
        'final': {'t': t, 'gold': g, 'level': L, 'hp': h, 'board': b},
        'level_check': {'pass_rate': sum(c['match'] for c in checks) / len(checks),
                        'checks': checks},
        'gold_max': max(gold_series), 'gold_avg': sum(gold_series) / len(gold_series),
        'interest_hits_50': max(gold_series) >= GOLD_CAP_INTEREST,
        'trace': trace,
    }
    return report


if __name__ == '__main__':
    import json
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    rep = _validate_emergence()
    print(json.dumps({k: v for k, v in rep.items() if k != 'trace'}, ensure_ascii=False, indent=1))
    print('\n轨迹(每节点):')
    for tr in rep['trace']:
        print(f"  p{tr['plane']}-{tr['node']} gold={tr['gold']:>3} lv={tr['level']} hp={tr['hp']:>3}"
              f" board={tr['board']:.1f} → {tr['posture']}")
