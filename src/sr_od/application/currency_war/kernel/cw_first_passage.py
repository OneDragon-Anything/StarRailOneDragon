"""目标函数层 v0:首达生存概率 + 风险姿态三区律。

**诊断**:全栈一致用「均值」计价(02 ΔE[生存]/04 悲观分位/ADR-0155 线性插值掉血),
期望泛函在劣势局**方向性选错** —— 教学校验例:两线同 E[掉血]=20,HP=25 必活线 A 与 HP=15
赌尾线 B 的正确选择相反;均值计价完全不区分,「血低→悲观」在必死边缘杀死唯一活路(右尾)。
**K0 实证(本仓 telemetry)**:plane1 掉血 CV=0.62(n=203)、plane2 CV=0.40
(n=35)—— 方差结构显著(>>桶宽 5),非近确定;决策点 hp 分布三区结构真实(0-39 占 43%
= 临界+必死边缘大有人在)→ K0 止损门**通过**,分布 DP 立项成立。

**v0 落地**(纯函数,离线):
- ``first_passage_win(board_tier, hp, nodes_left)``:掉血桶分布(先验 × 二项抖动)下的
  生存首达概率 —— gambler's ruin 的离散化数值积;
- ``risk_posture(board_tier, hp, nodes_left)``:三区律(盈余/临界/必死边缘),边界由
  P(win) 对 hp 的导数(λ_hp 峰形)解出;
- ``p_win_lambda(board_tier, hp, nodes_left)``:λ_hp = P(win|hp+1) − P(win|hp)(峰形曲线)。

升级路径(ADR-0155 并轨 V2):本模块立出口 API 供消费端(salvage/计价/
evidence 门);换桶分布转移矩阵、D 牌 Bernoulli 赌局化、hp 残值补丁为
后续扩展方向(K1-K3 判据)。
"""
from __future__ import annotations

# ⚖️ 单一源(ADR-0183 统一):掉血先验基准表持有者 = cw_plane_table
# (ADR-0465 起 = 原 DP 标定面的保留归属,物理原语层,被 sim_env/economy 同源消费);
# 本模块引用之并在此定义分布语义(CV/位面乘数)。
from sr_od.application.currency_war.kernel.cw_plane_table import (
    HP_LOSS_MU,  # noqa: F401
)

# (P1 标定基线;P2+ 位面维经 registry.p2_cond_loss_table 标定进模型,
# 见 _loss_dist 边界声明;重尾一击型 boss 掉血 v1 用实测桶替换)
CV_PRIOR: float = 0.5   # 组内变异系数先验(K0 实测 0.4-0.62 的收缩中值)

# 三区边界先验(K2 涌现对拍锚:DEAD_HP=20 三门 / HP<40 分档 / 满息 50)
ZONE_CRITICAL_HP: int = 40     # 二区下界(分档先验;对拍锚)
ZONE_DEATH_EDGE_HP: int = 20   # 三区下界(DEAD_HP=20;对拍锚)


def _p2_lcond_mix() -> float:
    """P2+ 非 boss 战斗槽条件败面档(单节点;两态决策层同款混合单一源:
    registry.p2_cond_loss_table × line_switch._P2_NODE_TEMPLATE 战斗构成)。"""
    from sr_od.application.currency_war.kernel.cw_line_switch import (
        _P2_NODE_TEMPLATE,
        node_loss_kind,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    tbl = DEFAULT_REGISTRY.p2_cond_loss_table
    kinds = [node_loss_kind(nt) for nt in _P2_NODE_TEMPLATE]
    battle = [k for k in kinds if k != 'reward']
    return sum(tbl.get(k, 0.0) for k in battle) / len(battle)


def _loss_dist(board_tier: int, plane: int = 1) -> list[tuple[float, float]]:
    """单节点掉血分布(板强档 × 位面 → [(掉血量, 概率)] 三点离散:μ-σ/μ/μ+σ 截非负)。

    μ 标定源合一(ADR-0440):P1 = HP_LOSS_MU 现档
    (P1 零漂移,不走 P2 标定);P2+ = 两态同构 μ(tier)=(1−p(rung(tier)))
    ·L_cond_mix —— 胜率=registry.p_win_p2_by_rung(rung 坐标=board_tier
    0-3 钳 0-2,与 p_win 表 k3 折叠同口径),条件败面=registry.
    p2_cond_loss_table 按位面模板战斗构成混合;P3 不在标定域,别名 P2
    (沿用位面维别名先例)。

    边界声明(与 DP 层的口径关系,「5× 差=语义差为主」判读
    的落点):本层是分布模型 estimand(每节点无条件期望掉血 ± CV 抖动,
    喂首达生存卷积),DP 层是确定性期望递推——两者共用同一标定(胜率表
    +条件败面档)但函数不同,数值对齐 ≠ 函数同一;本层不再持有独立位面
    乘数自由度,位面维全部来自 registry 标定(版本锚=registry.
    p2_loss_calib_version)。
    """
    if plane <= 1:
        mu = HP_LOSS_MU.get(min(3, max(0, board_tier)), 14.0)
    else:
        from sr_od.application.currency_war.kernel.cw_plane_table import p_win_p2
        mu = (1.0 - p_win_p2(min(2, max(0, int(board_tier))))) * _p2_lcond_mix()
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
    """hp 地板反解(「手写门变模型定理」的核心出口):最小 hp 使 P(win) ≥ target_pwin。

    语义:给定板强/剩余日程/位面,「想以 ≥ target 的概率活到底」至少需要多少血 ——
    保血阈值从手拍常数变生存曲线的导出量(ADR-0176)。
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

    乘子从生存曲线解出,随板强/日程变化 —— 弱板长程的方差尾
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


# ===== 集成接缝(供给方适配器;ADR-0170/0166)=====

def board_tier_of(level: int, rb: float = 0.0) -> int:
    """GameState(等级, 刷牌加成)→ 板强档 0-3(HP_LOSS_MU 的键域;板强基线映射 b_eff 随 DP 退役
    映射 —— 首达层的供给方适配:salvage/计价消费端拿 GameState 即可算 P(win),不必自算板强)。"""
    b = min(3.0, max(0.0, (level - 2) / 2.5) + rb)
    return min(3, max(0, int(b)))


def p_win_projection(level: int, hp: int, nodes_left: int, rb: float = 0.0,
                     plane: int = 1) -> float:
    """GameState → P(win)(一站式;salvage 触发量与计价的入口;v1 位面条件化)。"""
    return first_passage_win(board_tier_of(level, rb), hp, nodes_left, plane)
