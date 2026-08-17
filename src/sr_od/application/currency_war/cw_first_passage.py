"""目标函数层 v0(18 号提案;ADR-0161;2026-08-16):首达生存概率 + 风险姿态三区律。

**诊断(18 号)**:全栈一致用「均值」计价(02 ΔE[生存]/04 悲观分位/ADR-0155 线性插值掉血),
期望泛函在劣势局**方向性选错** —— 教学校验例:两线同 E[掉血]=20,HP=25 必活线 A 与 HP=15
赌尾线 B 的正确选择相反;均值计价完全不区分,「血低→悲观」在必死边缘杀死唯一活路(右尾)。
**K0 实证(本仓 telemetry,2026-08-16)**:plane1 掉血 CV=0.62(n=203)、plane2 CV=0.40
(n=35)—— 方差结构显著(>>桶宽 5),非近确定;决策点 hp 分布三区结构真实(0-39 占 43%
= 临界+必死边缘大有人在)→ K0 止损门**通过**,分布 DP 立项成立。

**v0 落地**(纯函数,离线):
- ``first_passage_win(board_tier, hp, nodes_left)``:掉血桶分布(先验 × 二项抖动)下的
  生存首达概率 —— gambler's ruin 的离散化数值积;
- ``risk_posture(board_tier, hp, nodes_left)``:三区律(盈余/临界/必死边缘),边界由
  P(win) 对 hp 的导数(λ_hp 峰形)解出;
- ``p_win_lambda(board_tier, hp, nodes_left)``:λ_hp = P(win|hp+1) − P(win|hp)(峰形曲线)。

升级路径(提案主张三,ADR-0155 并轨 V2):cw_horizon 掉血插件换桶分布转移矩阵、D 牌
Bernoulli 赌局化、hp 残值补丁删除 —— 本模块先立出口 API 供消费端(02/05/evidence 门),
K1-K3 判据随后。
"""
from __future__ import annotations

# ⚖️ 单一源(49 号 J0 子承普查命中 → ADR-0183 统一):掉血先验基准表持有者 = cw_horizon
# (物理原语层,被 sim_env/economy 同源消费);本模块引用之并在此定义分布语义(CV/位面乘数)。
# 旧 HP_LOSS_MU 本地副本(与 cw_horizon.HP_LOSS_PRIOR 同值异名)删除,防双源漂移。
from sr_od.application.currency_war.cw_horizon import (
    HP_LOSS_PRIOR as HP_LOSS_MU,  # noqa: F401
)

# (P1 标定基线;位面难度经 PLANE_LOSS_SCALE 进模型;重尾一击型 boss 掉血 v1 用实测桶替换)
CV_PRIOR: float = 0.5   # 组内变异系数先验(K0 实测 0.4-0.62 的收缩中值)

# 位面难度乘数(v1,18 号 V2 位面条件化;ADR-0176):
# 锚 = 0174 实测 P2-1 弱板掉 19/节点 vs P1 ~10(≈1.9×)+ cw_horizon.difficulty_scale
# P2 段 1.5-1.95 / P3 段 1.8-2.2 的收缩中值。P2 略低于实测上限(混合板强)。
PLANE_LOSS_SCALE: dict[int, float] = {1: 1.0, 2: 1.6, 3: 1.9}

# 三区边界先验(K2 涌现对拍锚:DEAD_HP=20 三门 / HP<40 分档 / 满息 50)
ZONE_CRITICAL_HP: int = 40     # 二区下界(ADR-0141/0143 分档;对拍锚)
ZONE_DEATH_EDGE_HP: int = 20   # 三区下界(DEAD_HP=20;对拍锚)


def _loss_dist(board_tier: int, plane: int = 1) -> list[tuple[float, float]]:
    """单节点掉血分布(板强档 × 位面 → [(掉血量, 概率)] 三点离散:μ-σ/μ/μ+σ 截非负)。

    μ = HP_LOSS_MU(P1 基线)× PLANE_LOSS_SCALE(位面难度;v1 先验,实测桶替换后同结构)。
    """
    mu = HP_LOSS_MU.get(min(3, max(0, board_tier)), 14.0) * PLANE_LOSS_SCALE.get(min(3, max(1, plane)), 1.0)
    sigma = mu * CV_PRIOR
    lo = max(0.0, mu - sigma)
    mid = mu
    hi = mu + sigma
    # 三点等权(离散近似;实测桶替换后为任意支撑集)
    return [(lo, 1 / 3), (mid, 1 / 3), (hi, 1 / 3)]


def _survive_cdf(board_tier: int, nodes_left: int, plane: int, hp_cap: int,
                 step: float = 0.5) -> list[float]:
    """一次卷积 → P(Σ loss < hp) 的查表(cdf[hp] for hp in 0..hp_cap)。

    step=0.5(细格):强板 μ≈0.8 在 2.5 粗格下会被取整归零 → 地板假性=1、
    位面乘子病态(v1 实测;细格后强板微掉血保留分辨率)。
    """
    n_grid = int(round(hp_cap / step))
    dist = [0.0] * (n_grid + 1)
    dist[0] = 1.0
    support = _loss_dist(board_tier, plane)
    for _ in range(nodes_left):
        nxt = [0.0] * (n_grid + 1)
        for i, p in enumerate(dist):
            if p <= 0:
                continue
            for loss, q in support:
                j = i + int(round(loss / step))
                if j <= n_grid:   # 超格 = 死亡,不计入
                    nxt[j] += p * q
        dist = nxt
    # cdf[hp] = P(Σ loss < hp) = Σ_{j: j·step < hp} dist[j](严格小于:Σ==hp 即死)
    cdf = [0.0] * (hp_cap + 1)
    run = 0.0
    j = 0
    for hp in range(hp_cap + 1):
        lim = hp / step   # j < lim ⟺ j·step < hp
        while j < n_grid + 1 and j < lim:
            run += dist[j]
            j += 1
        cdf[hp] = min(1.0, run)
    return cdf


def first_passage_win(board_tier: int, hp: int, nodes_left: int, plane: int = 1) -> float:
    """生存首达概率:剩余 nodes_left 个战斗节点,累计掉血 < hp 的概率(分布卷积 + CDF)。

    数学:掉血 i.i.d. 离散分布 → 总和分布 = n-卷积;P(win) = P(Σ loss < hp)。
    """
    if hp <= 0:
        return 0.0
    if nodes_left <= 0:
        return 1.0
    return _survive_cdf(board_tier, nodes_left, plane, hp)[hp]


def hp_floor(board_tier: int, nodes_left: int, target_pwin: float, plane: int = 1,
             hp_cap: int = 100) -> int:
    """hp 地板反解(18 号「手写门变模型定理」的核心出口):最小 hp 使 P(win) ≥ target_pwin。

    语义:给定板强/剩余日程/位面,「想以 ≥ target 的概率活到底」至少需要多少血 ——
    保血阈值从手拍常数变生存曲线的导出量(0174 位面乘子的模型替代,ADR-0176)。
    单次卷积 + CDF 扫描(P(win) 对 hp 单调);hp_cap 内无解 → 返回 hp_cap(无底可保)。
    """
    cdf = _survive_cdf(board_tier, nodes_left, plane, hp_cap)
    for hp in range(1, hp_cap + 1):
        if cdf[hp] >= target_pwin:
            return hp
    return hp_cap


def plane_hp_ratio(board_tier: int, nodes_left: int, target_pwin: float = 0.6,
                   plane: int = 2) -> float:
    """位面阈值乘子(P_win 地板比;ADR-0176):hp_floor(plane) / hp_floor(P1)。

    替代 0174 手写 ×1.25/×1.5:乘子从生存曲线解出,随板强/日程变化 —— 弱板长程的方差尾
    使所需缓冲超线性增长(ratio 高),强板短程近似线性(ratio 低)。内部用扩展 hp_cap=400
    计算(弱板长程两原在真实血上限内可能均无解 → 真实 cap 下 ratio 假性=1;乘子是无量纲
    比,不受实际血量约束;输出侧仍夹 [1.0, 2.0] 防先验失真外溢)。
    """
    p1 = hp_floor(board_tier, nodes_left, target_pwin, plane=1, hp_cap=400)
    pk = hp_floor(board_tier, nodes_left, target_pwin, plane=plane, hp_cap=400)
    if p1 <= 0:
        return 1.0
    return min(2.0, max(1.0, pk / p1))


def p_win_lambda(board_tier: int, hp: int, nodes_left: int, plane: int = 1) -> float:
    """λ_hp = P(win | hp+1) − P(win | hp):HP 的边际生存价值(峰形曲线的采样点)。"""
    return (first_passage_win(board_tier, hp + 1, nodes_left, plane)
            - first_passage_win(board_tier, hp, nodes_left, plane))


def risk_posture(board_tier: int, hp: int, nodes_left: int, plane: int = 1) -> str:
    """三区律:盈余 / 临界 / 必死边缘。

    边界由 λ_hp 与 P(win) 联合解出(**非手写 hp 阈值**;弱板长程下「必死边缘」的 hp 绝对
    值可高达 60+ —— 漂移把屏障推远,这正是固定 DEAD_HP=20 类手写门要被替代的证据):
    必死边缘 = P(win) < 35% 且 λ_hp 已回落(±1 血不改大局,该赌右尾);临界 = λ_hp 活跃
    (每点血实质改变活率);盈余 = 其余。
    """
    if hp <= 0:
        return '必死边缘'
    pw = first_passage_win(board_tier, hp, nodes_left, plane)
    lam = p_win_lambda(board_tier, hp, nodes_left, plane)
    if pw < 0.35 and lam < 0.01:
        return '必死边缘'
    if lam >= 0.01 and pw < 0.95:
        return '临界'
    return '盈余'


def posture_guidance(posture: str) -> str:
    """三区 → 策略姿态指导(消费端文案;对应散落手写门的统一)。"""
    return {
        '盈余': '方差无视:卖血换经济/囤息(满息基调)',
        '临界': '方差回避:弃息 D 保血/避高难遭遇(danger_d 语义)',
        '必死边缘': '方差追求:弃息全 D 追星/转高上限 comp/赌高方差事件(「低血不卡息,留20」)',
    }.get(posture, '')


# ===== 集成接缝(供给方适配器;ADR-0170/0166 documented,本轮接线) =====

def board_tier_of(level: int, rb: float = 0.0) -> int:
    """GameState(等级, 刷牌加成)→ 板强档 0-3(HP_LOSS_MU 的键;与 cw_horizon.b_eff 同源
    映射 —— 首达层的供给方适配:salvage/计价消费端拿 GameState 即可算 P(win),不必自算板强)。"""
    b = min(3.0, max(0.0, (level - 2) / 2.5) + rb)
    return min(3, max(0, int(b)))


def p_win_projection(level: int, hp: int, nodes_left: int, rb: float = 0.0,
                     plane: int = 1) -> float:
    """GameState → P(win)(一站式;05 号 salvage 触发量与 19 号计价的入口;v1 位面条件化)。"""
    return first_passage_win(board_tier_of(level, rb), hp, nodes_left, plane)
