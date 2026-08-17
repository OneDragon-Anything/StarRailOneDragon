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

from dataclasses import dataclass

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
# D1(ADR-0202/53 号网格约束):金步长 5→1——台账日程的 +1/+2 级小额度(长期主义 7/按劳 1)
# 在步长 5 下被量化静默蒸发;状态空间 27×111×10×20×5 ≈ 3M × 8 姿态,求解分钟级(实测
# ~3min),可忽略。posture() 的 g5 归一同步兼容(步长 1 下 gold//1*1=gold 恒等)。
GOLD_STEP, GOLD_MAX = 1, 110
HP_BUCKET, HP_MIN, HP_MAX = 5, 5, 100
LEVEL_MIN, LEVEL_MAX = 1, 10
SURVIVAL_W = 10.0
GOLD_RESIDUAL_W, LEVEL_RESIDUAL_W, HP_RESIDUAL_W = 0.02, 0.05, 0.03


@dataclass(slots=True)
class Posture:
    save: bool = True
    level_up: bool = False
    refresh_budget: int = 0
    v: float = 0.0
    tag: str = ''


_ACTION_ROLLS = {0: 0, 1: 2, 2: 4, 3: 6}
# v6 热路径预表(posture 微优化,ADR-0202 v7):tag 按动作码预拼(消每次字符串构造);
# rolls 用元组下标(消 dict 哈希);rb 量化 bisect(消 5 档线性 min)。
_TAG_OF_ACTION = ('存息', '+D2', '+D4', '+D6', '升级', '升级+D2', '升级+D4', '升级+D6')
_ROLLS_OF_ACTION = (0, 2, 4, 6, 0, 2, 4, 6)


def _rb_to_index(rb: float) -> int:
    """连续板强 → 最近档索引(与旧版 min(|steps−rb|) 逐位同语义)。"""
    from bisect import bisect_left
    i = bisect_left(RB_STEPS, rb)
    if i <= 0:
        return 0
    if i >= len(RB_STEPS):
        return len(RB_STEPS) - 1
    return i if (RB_STEPS[i] - rb) <= (rb - RB_STEPS[i - 1]) else i - 1


class HorizonSolution:
    """DP 解。v5 起内部为 numpy flat 数组(求解向量化 + 缓存 ~MB 级),对外三访问口:

    - ``posture(t, gold, level, hp, rb)``:O(1) flat 索引 → 按需构造 Posture(查询低频);
    - ``value_at(...)``:同上,标量值;
    - ``policy`` / ``value``(property):**惰性物化 dict 视图**(旧消费端[测试/审计]兼容;
      生产路径不应触碰)。
    布局 flat:((t*NG+gi)*NLEV+Li)*NH+hi)*NR+rbi;动作码 0=存息 1=+D2 2=+D4 3=+D6
    4=升级 5=升+D2 6=升+D4 7=升+D6。
    (非 dataclass:类级布局常数与缓存字段不进字段序;手写 __init__)
    """

    _act: object = None            # np.ndarray[int8] flat
    _val: object = None            # np.ndarray[float64] flat
    _policy_cache: dict[tuple, Posture] | None = None
    _value_cache: dict[tuple, float] | None = None
    _lc_of: dict[int, int] | None = None   # Li → level_cost(物化 Posture 的 v/tag 不含,
    # spend 由动作码+此处恢复;v 存于 _val)

    # —— 布局常数(类级,物化/posture 共用)——
    _NG: int = GOLD_MAX // GOLD_STEP + 1
    _NH: int = (HP_MAX - HP_MIN) // HP_BUCKET + 1
    _NR: int = len(RB_STEPS)
    _NLEV: int = LEVEL_MAX - LEVEL_MIN + 1

    def __init__(self, act=None, val=None) -> None:
        self._act = act
        self._val = val
        self._policy_cache = None
        self._value_cache = None

    # 兼容旧字段式访问(构造空解的旧调用路径)
    @property
    def policy(self) -> dict[tuple, Posture]:
        if self._policy_cache is None:
            self._materialize()
        return self._policy_cache

    @property
    def value(self) -> dict[tuple, float]:
        if self._value_cache is None:
            self._materialize()
        return self._value_cache

    @policy.setter
    def policy(self, d: dict) -> None:
        self._policy_cache = d

    @value.setter
    def value(self, d: dict) -> None:
        self._value_cache = d

    def _idx(self, t: int, gold: int, level: int, hp: int, rbi: int) -> int:
        # int() 强转:调用方可能传 float(validate_emergence 的 h_raw 演化是 float;
        # 旧 dict 版 float 键静默 miss → fallback,新版显式取整 —— 兼容且更诚实)
        # v6 布局 [t, Li, gi, hi, rbi](向量化求解的产出序;Li 内层使 (g,h,rbi) 块连续)
        t = int(t)
        if t >= TOTAL_NODES:
            t = TOTAL_NODES - 1
        gi = min(int(gold) // GOLD_STEP, self._NG - 1)
        Li = min(max(int(level), LEVEL_MIN), LEVEL_MAX) - LEVEL_MIN
        hi = (min(max(int(hp), HP_MIN), HP_MAX) - HP_MIN) // HP_BUCKET
        return (((t * self._NLEV + Li) * self._NG + gi) * self._NH + hi) * self._NR + int(rbi)

    def posture(self, t: int, gold: int, level: int, hp: int, rb: float) -> Posture:
        if self._act is None:
            return self.policy.get(
                (t, min(gold // GOLD_STEP * GOLD_STEP, GOLD_MAX),
                 min(max(level, LEVEL_MIN), LEVEL_MAX),
                 min(max(hp, HP_MIN), HP_MAX) // HP_BUCKET * HP_BUCKET,
                 min(range(len(RB_STEPS)), key=lambda i: abs(RB_STEPS[i] - rb)))
            ) or Posture(tag='fallback')
        # v7 热路径:预表 + bisect 最近邻(实测 ~2.3→~1µs;每回合数次查询,一局省微秒级,
        # 但影子模式全量对拍/批量评估场景次数放大 10^4)
        rbi = _rb_to_index(rb)
        i = (((min(int(t), TOTAL_NODES - 1) * self._NLEV
               + min(max(int(level), LEVEL_MIN), LEVEL_MAX) - LEVEL_MIN)
              * self._NG + min(int(gold) // GOLD_STEP, self._NG - 1))
             * self._NH + (min(max(int(hp), HP_MIN), HP_MAX) - HP_MIN) // HP_BUCKET
            ) * self._NR + rbi
        a = int(self._act[i])
        return Posture(save=(a == 0), level_up=a >= 4,
                       refresh_budget=_ROLLS_OF_ACTION[a], v=float(self._val[i]),
                       tag=_TAG_OF_ACTION[a])

    def value_at(self, t: int, gold: int, level: int, hp: int, rb: float) -> float:
        return float(self._val[self._idx(t, gold, level, hp, _rb_to_index(rb))])

    def _materialize(self) -> None:
        """数组 → dict 视图(旧消费端兼容;一次性;t 层 0..TOTAL_NODES-1;
        v6 布局 [t, Li, gi, hi, rbi] flat)。"""
        self._policy_cache = {}
        self._value_cache = {}
        if self._act is None:
            return
        act, val = self._act, self._val
        for t in range(TOTAL_NODES):
            for Li in range(self._NLEV):
                L = Li + LEVEL_MIN
                base_tL = (t * self._NLEV + Li) * self._NG
                for gi in range(self._NG):
                    g = gi * GOLD_STEP
                    base_g = (base_tL + gi) * self._NH
                    for hi in range(self._NH):
                        h = hi * HP_BUCKET + HP_MIN
                        base = (base_g + hi) * self._NR
                        for rbi in range(self._NR):
                            i = base + rbi
                            a = int(act[i])
                            lv_up = a >= 4
                            rolls = {0: 0, 1: 2, 2: 4, 3: 6}[a % 4]
                            tag = ('升级' if lv_up else '') + (f'+D{rolls}' if rolls else '') or '存息'
                            self._policy_cache[(t, g, L, h, rbi)] = Posture(
                                save=(a == 0), level_up=lv_up, refresh_budget=rolls,
                                v=float(val[i]), tag=tag)
                            self._value_cache[(t, g, L, h, rbi)] = float(val[i])


def _hp_loss(t: int, level: int, rb: float) -> float:
    """掉血 = 先验在 b_eff 上**线性插值**(非整数桶):板强每 +0.1 都有平滑边际 —— 整数桶会把
    b2.2 与 b2.6 判同档,升级失去全部边际收益,V1.1 实测 P1 末停 lv5 不追(band 违例根因)。"""
    b = b_eff(level, rb)
    lo = min(3, max(0, int(b)))
    frac = b - lo
    hi = min(3, lo + 1)
    base = HP_LOSS_PRIOR[lo] + (HP_LOSS_PRIOR[hi] - HP_LOSS_PRIOR[lo]) * frac
    return base * difficulty_scale(t)


def solve(ledger=None) -> HorizonSolution:
    """逆向递推。状态 (t, g5, L, h5, rbi) ≈ 27×23×10×20×5 ≈ 620k × 8 姿态 ≈ 5M 评估(分钟级,离线)。

    ledger(ADR-0202/53 号盲区 2 根治,effect-blind 修复):EffectLedger 注入 →
    收入/息/成本全走台账突变视图(node_income_with/interest_with/level_cost_with);
    None = 现状平坦常量(零漂移锚,全部既有测试与 0181/0190 A/B 基线锚定此路径)。
    """
    from sr_od.application.currency_war.cw_effect_ledger import (
        interest_with,
        level_cost_with,
        node_income_with,
    )
    _has_ledger = ledger is not None

    def _income(t: int, b2: float) -> int:
        if _has_ledger:
            # 台账路径:基础+连胜档在 DP 侧算,乘子/日程由 mutations/calendar 注入
            base = BASE_INCOME + (4 if b_eff_level_free(b2) else 1)
            if (t + 1) % NODES_PER_PLANE == 0:
                base += BOSS_BONUS
            streak_part = 4 * 1.0   # 连胜档金(node_income 的 +4 已入 base;此处保持同构)
            return int(node_income_with(t, float(base) - 4.0, streak_part, ledger))
        return node_income(t, b2)

    def _interest(g2: int) -> int:
        if _has_ledger:
            return interest_with(g2, ledger, default_cap=GOLD_CAP_INTEREST // 10)
        return interest(g2)

    def _level_cost(L: int) -> int:
        if _has_ledger:
            return int(level_cost_with(clicks_to_level(L), ledger,
                                       base_click_cost=float(XP_CLICK_COST_FLAT)))
        return level_cost(L)

    # ===== v6:numpy 向量化逆向递推(标量版逐位对拍通过后替换;ADR-0202 v6) =====
    # 布局 V/ACT [t, Li, gi, hi, rbi] —— Li 外提使 (g,h,rbi) 块连续;固定
    # (t, Li, lv_up, rolls) 时 g3 是 (g,rbi) 仿射、h3 是 (h,rbi) 平移截断 → 整块
    # fancy-index 批量转移;8 姿态按花费降序序扫(tie-break「strict > 才换」与标量版
    # 逐位一致,对拍锚:ACT 全等 + VAL max|diff|=0)。求解 ~0.3s。
    import numpy as _np
    _NLEV = LEVEL_MAX - LEVEL_MIN + 1
    _NHP = (HP_MAX - HP_MIN) // HP_BUCKET + 1
    _NRB = len(RB_STEPS)
    _NG = GOLD_MAX // GOLD_STEP + 1
    _rolls_code = {0: 0, 2: 1, 4: 2, 6: 3}
    _g_grid = _np.arange(_NG) * GOLD_STEP
    _h_grid = _np.arange(_NHP) * HP_BUCKET + HP_MIN
    _L_grid = _np.arange(LEVEL_MIN, LEVEL_MAX + 1)

    _V = _np.zeros((TOTAL_NODES + 1, _NLEV, _NG, _NHP, _NRB))
    _ACT = _np.zeros((TOTAL_NODES, _NLEV, _NG, _NHP, _NRB), dtype=_np.int8)
    # 终局(广播:存活奖励 + 金/级/血残值;死亡 0 由初始化承载)
    _V[TOTAL_NODES] = (SURVIVAL_W
                       + GOLD_RESIDUAL_W * _g_grid[None, :, None, None]
                       + LEVEL_RESIDUAL_W * _L_grid[:, None, None, None]
                       + HP_RESIDUAL_W * _h_grid[None, None, :, None])

    for t in range(TOTAL_NODES - 1, -1, -1):
        # 每 t 预表(纯函数,量小标量算)
        _drop = _np.zeros((_NLEV, _NRB))
        _inc = _np.zeros((_NLEV, _NRB), dtype=_np.int64)
        for Li in range(_NLEV):
            for rbi in range(_NRB):
                _drop[Li, rbi] = _hp_loss(t, int(_L_grid[Li]), RB_STEPS[rbi])
                _inc[Li, rbi] = _income(t, b_eff(int(_L_grid[Li]), RB_STEPS[rbi]))
        _rbi2_map = {rolls: _np.array([
            min(range(_NRB), key=lambda i: abs(RB_STEPS[i] - min(RB_MAX, rb + 0.12 * rolls)))
            for rb in RB_STEPS]) for rolls in (6, 4, 2, 0)}
        _int_tab = _np.array([_interest(g2v) for g2v in range(GOLD_MAX + 1)])
        _Vn = _V[t + 1]
        for Li in range(_NLEV):
            _lc = _level_cost(int(_L_grid[Li])) if _L_grid[Li] < LEVEL_MAX else None
            _best_v = _np.full((_NG, _NHP, _NRB), -1e18)
            _best_a = _np.zeros((_NG, _NHP, _NRB), dtype=_np.int64)
            for lv_up in (1, 0):
                if lv_up and _lc is None:
                    continue
                for rolls in (6, 4, 2, 0):
                    _spend = (_lc or 0) * lv_up + 2 * rolls
                    _g2 = _g_grid - _spend                       # [NG]
                    _feas = _g2 >= 0
                    _L2i = min(_NLEV - 1, Li + lv_up)
                    _r2 = _rbi2_map[rolls]                       # [NR] 目标板强档
                    # 转移参数随 (L2, rbi2) 变 → 按 rbi 维向量化 [NR]
                    _dropR = _drop[_L2i][_r2]                    # [NR]
                    _incR = _inc[_L2i][_r2]                      # [NR]
                    _g2s = _np.where(_feas, _g2, 0)
                    _g3 = _np.clip(_g2s[:, None] + _incR[None, :]
                                   + _int_tab[_g2s][:, None], 0, GOLD_MAX) // GOLD_STEP  # [NG,NR]
                    _h_raw = _h_grid[:, None] - _dropR[None, :]  # [NH,NR]
                    _alive = _h_raw > 0
                    _h3v = _np.clip(_np.floor(_h_raw).astype(_np.int64) // HP_BUCKET * HP_BUCKET,
                                    HP_MIN, HP_MAX)
                    _hidx = (_h3v - HP_MIN) // HP_BUCKET         # [NH,NR]
                    _v = _Vn[_L2i][_g3[:, None, :], _hidx[None, :, :], _r2[None, None, :]]
                    _v = _np.where(_alive[None, :, :], _v, 0.0)      # 死亡终端
                    _v = _np.where(_feas[:, None, None], _v, -1e18)  # 不可行不参与
                    _take = _v > _best_v
                    _best_v = _np.where(_take, _v, _best_v)
                    _best_a = _np.where(_take, (4 if lv_up else 0) + _rolls_code[rolls], _best_a)
            _V[t, Li] = _best_v
            _ACT[t, Li] = _best_a.astype(_np.int8)
    # 产出 flat 一维(posture/_materialize 按同布局索引;act int8 ≈ 3MB,val ≈ 25MB)
    return HorizonSolution(act=_ACT.ravel().copy(), val=_V[:TOTAL_NODES].ravel().copy())


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


def ledger_fingerprint(ledger) -> str:
    """台账指纹:只有改 DP 世界模型的字段参与(calendar+mutations)——纯时点金
    (instant_gold 类,overlay 73 条中 52 条)不进台账,指纹天然不变 → 命中即免重算。"""
    import hashlib
    if ledger is None:
        return 'base'
    m = ledger.mutations
    payload = repr((
        sorted(ledger.calendar.items()),
        m.interest_cap, m.xp_click_delta, m.win_reward_mult,
        m.free_refresh_per_node, m.free_refresh_burst,
        m.refresh_surprise_every, m.gold_per_three_5cost,
        m.xp_per_refresh, m.xp_per_node,
        m.refresh_price_after, m.refresh_discount_at,
    ))
    return hashlib.md5(payload.encode()).hexdigest()[:12]


_CACHE_MEMO: dict[str, HorizonSolution] = {}


def solve_cached(ledger=None) -> HorizonSolution:
    """按台账指纹的进程内 memo(v6:求解向量化后 ~0.3s,**盘 pickle 层已移除**——
    读 27MB 盘缓存比直接重解更慢,缓存变成负资产;memo 仍保留:同指纹重复查询零成本,
    台账注入场景(每持卡组合)各自 memo)。"""
    fp = ledger_fingerprint(ledger)
    if fp not in _CACHE_MEMO:
        _CACHE_MEMO[fp] = solve(ledger)
    return _CACHE_MEMO[fp]


def _solved() -> HorizonSolution:
    """惰性解一次(进程内 memo;生产路径入口)。"""
    global _SOLVED
    if _SOLVED is None:
        _SOLVED = solve_cached()
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
