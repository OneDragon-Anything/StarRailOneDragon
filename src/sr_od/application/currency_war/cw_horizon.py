"""日程感知资源规划器 V1.1(03 号重设计提案;DP + 影子价格;2026-08-16)。

**V1 = 涌现验证**(03 号 §4 判据):只喂机制常量,检验能否从第一性原理复现人类 meta
(plaza 784 篇 labels:主流「7级搜牌」338 / 「速升8」 / 少数「速升9」140;P1 末 lv7 /
P2 早上 8 = ADR-0126 实测)+ 用户满息基调(2026-08-16:高难度下持续满息才有金推等级/
追星 —— 应从影子价格涌现,而非手写门)。

V1.0 首跑失败暴露的三缺口(V1.1 修):
1. 中途死亡价值太软 → 死亡=0(与终局存活 SURVIVAL_W 对比,活命绝对优先);
2. 升级→板强→掉血链断裂 → 板强 b = f(等级)[deploy cap = level,游戏机制] + 刷牌加成 rb;
3. 检验标准错 → 按位面分段带(P1 末 6-8 / P2 末 7-9 / P3 7-9),非全程常数。

掉血项 = 可替换插件(平坦先验 × 位面难度曲线;后续接 PerformanceTracker/outcome model)。
纯函数,不碰游戏/session;离线可测。机制常量单一源:XP 表(cw_state)/概率表(cw_shop_odds)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_state import XP_PER_BUY, XP_TO_NEXT_LEVEL

# ===== 日程/经济先验(后续由 read_node_sequence / EconomyEffect 实测覆盖) =====
NODES_PER_PLANE: int = 9
TOTAL_NODES: int = NODES_PER_PLANE * 3
BASE_INCOME: int = 5
STREAK_INCOME: int = 3        # 连胜档(2 连 +1 递增封 4;取常态均值 3)
BOSS_BONUS: int = 2
GOLD_CAP_INTEREST: int = 50   # 息封顶(10 金 1 息、5 档封顶)
XP_CLICK_COST_FLAT: int = 4   # 购买经验单击价(ADR-0129 实测 4-8 区间,取下限;敏感校准点:
# V1.0 用 4+lv 过贵(lv7 单击 11 金)→ 6→7 需 110 金 → DP 判升不起 → 板 0 → P2 必死 → 全路径值 0)


# XP 门槛表:cw_state 权威表从 3 级起(1/2 级游戏内近乎白送,表未收录)→ 本地先验补 1/2 级
_XP_NEED: dict[int, int] = {1: 4, 2: 4, **XP_TO_NEXT_LEVEL}

# 板强 → 每战斗节点期望掉血(平坦先验 × 位面难度曲线;插件可替换)。
# 校准原则(涌现验证地形):好节奏(及时升人口+追星)可活、乱玩(板 0-1)必死 —— V1.0 首版
# {0:14,1:8,2:3.5,3:1.5}+陡难度曲线下 A8 无解(全路径死 → 值全 0 → DP 退化存息)。
HP_LOSS_PRIOR: dict[int, float] = {0: 14.0, 1: 7.0, 2: 2.5, 3: 0.8}


def difficulty_scale(t: int) -> float:
    """位面难度曲线(A8:敌人难度随位面/节点走高;M29-M39 实测 P2 是墙)。"""
    plane, node = divmod(t, NODES_PER_PLANE)
    if plane == 0:
        return 0.5 if node < 4 else (0.9 if node < 8 else 1.4)
    if plane == 1:
        return 1.5 + 0.05 * node
    return 1.8 + 0.05 * node


def b_base(level: int) -> float:
    """等级 → 板强基线(deploy cap = level 的机制映射:L4≈1/L7≈2/L9+≈满)。"""
    return min(2.6, max(0.0, (level - 2) / 2.5))


def b_eff(level: int, rb: float) -> float:
    """板强 = 等级基线 + 刷牌加成(买牌/追星,封顶 3)。"""
    return min(3.0, b_base(level) + rb)


RB_STEPS: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
RB_MAX: float = 1.0


def clicks_to_level(level: int) -> int:
    """当前级 → 下一级所需购买经验次数(ceil;(need)/XP_PER_BUY;xp 结转忽略,原子近似)。"""
    need = _XP_NEED.get(level, 84)
    return max(1, -(-need // XP_PER_BUY))


def level_cost(level: int) -> int:
    """升一级总金(次数 × 单击价;V1 平坦价,敏感校准点见常量注释)。"""
    return clicks_to_level(level) * XP_CLICK_COST_FLAT


def interest(gold: int) -> int:
    return min(gold // 10, GOLD_CAP_INTEREST // 10)


def node_income(t: int, b: float | None = None) -> int:
    """节点收入:基础 + 连胜档(**板强耦合**:b≥2.2 打得赢吃 4 金连胜档;b 弱连败 1 金 ——
    真实机制里连胜金是经济主件,板弱 = 掉血 + 收入掉档双输;V1.1 平坦 3 金切断该耦合,
    DP 用安全余量换利息系统性欠升级,与 meta「P1 末必 7」相悖,故耦合)。"""
    inc = BASE_INCOME + (4 if (b is None or b_eff_level_free(b)) else 1)
    if (t + 1) % NODES_PER_PLANE == 0:
        inc += BOSS_BONUS
    return inc


def b_eff_level_free(b: float) -> bool:
    return b >= 2.2


# ===== DP =====
GOLD_STEP, GOLD_MAX = 5, 110
HP_BUCKET, HP_MIN, HP_MAX = 5, 5, 100
LEVEL_MIN, LEVEL_MAX = 1, 10
SURVIVAL_W = 10.0
GOLD_RESIDUAL_W, LEVEL_RESIDUAL_W, HP_RESIDUAL_W = 0.02, 0.05, 0.03


@dataclass
class Posture:
    save: bool = True
    level_up: bool = False
    refresh_budget: int = 0
    v: float = 0.0
    tag: str = ''


@dataclass
class HorizonSolution:
    policy: dict[tuple, Posture] = field(default_factory=dict)
    value: dict[tuple, float] = field(default_factory=dict)

    def posture(self, t: int, gold: int, level: int, hp: int, rb: float) -> Posture:
        g5 = min(gold // GOLD_STEP * GOLD_STEP, GOLD_MAX)
        h5 = min(max(hp, HP_MIN), HP_MAX) // HP_BUCKET * HP_BUCKET
        rbi = min(range(len(RB_STEPS)), key=lambda i: abs(RB_STEPS[i] - rb))
        return self.policy.get((t, g5, min(max(level, LEVEL_MIN), LEVEL_MAX), h5, rbi)) or Posture(tag='fallback')


def _hp_loss(t: int, level: int, rb: float) -> float:
    """掉血 = 先验在 b_eff 上**线性插值**(非整数桶):板强每 +0.1 都有平滑边际 —— 整数桶会把
    b2.2 与 b2.6 判同档,升级失去全部边际收益,V1.1 实测 P1 末停 lv5 不追(band 违例根因)。"""
    b = b_eff(level, rb)
    lo = min(3, max(0, int(b)))
    frac = b - lo
    hi = min(3, lo + 1)
    base = HP_LOSS_PRIOR[lo] + (HP_LOSS_PRIOR[hi] - HP_LOSS_PRIOR[lo]) * frac
    return base * difficulty_scale(t)


def solve() -> HorizonSolution:
    """逆向递推。状态 (t, g5, L, h5, rbi) ≈ 27×23×10×20×5 ≈ 620k × 8 姿态 ≈ 5M 评估(分钟级,离线)。"""
    sol = HorizonSolution()
    g_list = list(range(0, GOLD_MAX + 1, GOLD_STEP))
    h_list = list(range(HP_MIN, HP_MAX + 1, HP_BUCKET))
    # 终局:活着 = 存活奖励 + 残余资源(金/等级/hp;hp 残值 = 对未来波动的缓冲 —— 无此项则
    # 存活一旦确保血量边际为 0,DP 用安全余量换利息,系统性欠升级,V1.1 实测);死亡=0
    for g in g_list:
        for L in range(LEVEL_MIN, LEVEL_MAX + 1):
            for h in h_list:
                for rbi, _rb in enumerate(RB_STEPS):
                    sol.value[(TOTAL_NODES, g, L, h, rbi)] = (
                        SURVIVAL_W + GOLD_RESIDUAL_W * g + LEVEL_RESIDUAL_W * L + HP_RESIDUAL_W * h)
    for t in range(TOTAL_NODES - 1, -1, -1):
        for g in g_list:
            for L in range(LEVEL_MIN, LEVEL_MAX + 1):
                for h in h_list:
                    for rbi, rb in enumerate(RB_STEPS):
                        best_v, best_p = -1e18, Posture()
                        _lc = level_cost(L) if L < LEVEL_MAX else None
                        # 遍历序 = 花费降序(升级先/多刷先):值平局时偏好进取姿态(防「全 0 平局退化存息」)
                        for lv_up in (1, 0):
                            if lv_up and (_lc is None or g < _lc):
                                continue
                            for rolls in (6, 4, 2, 0):
                                spend = (_lc or 0) * lv_up + 2 * rolls
                                if spend > g:
                                    continue
                                g2 = g - spend
                                L2 = min(LEVEL_MAX, L + lv_up)
                                # 刷牌加成:期望买牌永久提升板强(封顶;边际随接近顶衰减)
                                _up = 0.12 * rolls
                                rb2 = min(RB_MAX, rb + _up if rb + _up < RB_MAX else RB_MAX)
                                rbi2 = min(range(len(RB_STEPS)), key=lambda i: abs(RB_STEPS[i] - rb2))
                                g3 = min(GOLD_MAX, (g2 + node_income(t, b_eff(L2, rb2))
                                                    + interest(g2)) // GOLD_STEP * GOLD_STEP)
                                drop = _hp_loss(t, L2, rb2)
                                h_raw = h - drop
                                if h_raw <= 0:
                                    v = 0.0   # 死亡终端:任何活路 > 死
                                else:
                                    h3 = min(HP_MAX, max(HP_MIN, int(h_raw) // HP_BUCKET * HP_BUCKET))
                                    v = sol.value[(t + 1, g3, L2, h3, rbi2)]
                                if v > best_v:
                                    tag = ('升级' if lv_up else '') + (f'+D{rolls}' if rolls else '')
                                    if not tag:
                                        tag = '存息'
                                    best_v, best_p = v, Posture(save=(spend == 0), level_up=bool(lv_up),
                                                                refresh_budget=rolls, v=v, tag=tag or '存息')
                        sol.value[(t, g, L, h, rbi)] = best_v
                        sol.policy[(t, g, L, h, rbi)] = best_p
    return sol


# ===== V1 涌现验证 =====

def _expected_band(t: int) -> tuple[int, int]:
    """plaza meta 目标带:P1 末 lv6-8 / P2 末 lv7-9 / P3 保持 7-9(主流 7 级搜牌,速升9 是少数)。"""
    plane, node = divmod(t, NODES_PER_PLANE)
    if plane == 0:
        return (2, 4) if node < 3 else ((4, 6) if node < 6 else (6, 8))
    if plane == 1:
        return (6, 8) if node < 4 else (7, 9)
    return (7, 9)


def validate_emergence() -> dict:
    """DP 指导轨迹 → 与 plaza meta 对拍(离线,无游戏)。"""
    sol = solve()
    t, g, L, h, rb = 0, 10, 1, 100, 0.0
    trace = []
    while t < TOTAL_NODES:
        p = sol.posture(t, g, L, h, rb)
        spend = (level_cost(L) if p.level_up else 0) + 2 * p.refresh_budget
        g2 = g - spend
        L = min(LEVEL_MAX, L + (1 if p.level_up else 0))
        rb = min(RB_MAX, rb + 0.12 * p.refresh_budget)
        g = min(GOLD_MAX, g2 + node_income(t, b_eff(L, rb)) + interest(g2))
        h_raw = h - _hp_loss(t, L, rb)
        trace.append({'t': t, 'plane': t // NODES_PER_PLANE + 1, 'node': t % NODES_PER_PLANE + 1,
                      'gold': g, 'level': L, 'hp': max(0, int(h_raw)), 'board': round(b_eff(L, rb), 2),
                      'posture': p.tag})
        if h_raw <= 0:
            break
        h = h_raw
        t += 1
    band_ok = [(_expected_band(tr['t'])[0] <= tr['level'] <= _expected_band(tr['t'])[1]) for tr in trace]
    golds = [tr['gold'] for tr in trace]
    return {
        'survived': t >= TOTAL_NODES - 1 and h > 0,
        'final': {'t': t, 'gold': g, 'level': L, 'hp': int(h)},
        'band_pass_rate': sum(band_ok) / len(band_ok),
        'band_violations': [tr for tr, ok in zip(trace, band_ok, strict=True) if not ok],
        'gold_max': max(golds),
        'interest_engine_nodes': sum(1 for x in golds if x >= GOLD_CAP_INTEREST),
        'level_end_p1': trace[min(8, len(trace) - 1)]['level'] if len(trace) > 8 else None,
        'level_end_p2': trace[min(17, len(trace) - 1)]['level'] if len(trace) > 17 else None,
        'trace': trace,
    }


if __name__ == '__main__':
    import json
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    rep = validate_emergence()
    print(json.dumps({k: v for k, v in rep.items() if k != 'trace'}, ensure_ascii=False, indent=1))
    print('\n轨迹:')
    for tr in rep['trace']:
        print(f"  p{tr['plane']}-{tr['node']} gold={tr['gold']:>3} lv={tr['level']} hp={tr['hp']:>3}"
              f" b={tr['board']:.1f} → {tr['posture']}")


# ===== 接缝:DP 姿态 → NodeGoal(ADR-0155;get_node_goal 影子模式消费) =====

_SOLVED: HorizonSolution | None = None


def _solved() -> HorizonSolution:
    """惰性解一次(离线秒-分钟级;进程内缓存)。"""
    global _SOLVED
    if _SOLVED is None:
        _SOLVED = solve()
    return _SOLVED


def _horizon_node_goal(plane: int, round_num: int, gold: int, level: int, hp: int):
    """DP 姿态 → NodeGoal 映射(spend_mode 由姿态导出;None = 缺解回退表)。

    姿态语义:升级=level_up True → target_level=level+1/rush_level;D 预算>0 → d_search;
    存息 → interest(spend_mode);两者皆有 → level(升级优先,D 预算进 refresh_budget 语义,
    _refresh_cap 另有其表,此处 action_focus 表意)。
    """
    t = (min(plane, 3) - 1) * NODES_PER_PLANE + min(round_num, NODES_PER_PLANE) - 1
    if not (0 <= t < TOTAL_NODES):
        return None
    try:
        from sr_od.application.currency_war.cw_economy import NodeGoal
        p = _solved().posture(t, gold, level, hp, 0.0)
        if p.level_up:
            return NodeGoal(min(10, level + 1), 'level', 'rush_level')
        if p.refresh_budget > 0:
            return NodeGoal(level, 'adaptive', 'd_search')
        return NodeGoal(level, 'interest', 'hold')
    except Exception:   # noqa: BLE001  影子接缝 best-effort:任何异常回退表
        return None
