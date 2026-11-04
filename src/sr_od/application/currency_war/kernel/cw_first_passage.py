"""目标函数层 v0:首达生存概率 + 风险姿态三区律。

**诊断**:全栈一致用「均值」计价(02 ΔE[生存]/04 悲观分位/线性插值掉血),
期望泛函在劣势局**方向性选错** —— 教学校验例:两线同 E[掉血]=20,HP=25 必活线 A 与 HP=15
赌尾线 B 的正确选择相反;均值计价完全不区分,「血低→悲观」在必死边缘杀死唯一活路(右尾)。
**K0 实证(本仓 telemetry)**:plane1 掉血 CV=0.62(n=203)、plane2 CV=0.40
(n=35)—— 方差结构显著(>>桶宽 5),非近确定;决策点 hp 分布三区结构真实(0-39 占 43%
= 临界+必死边缘大有人在)→ K0 止损门**通过**,分布 DP 立项成立。

**落地**(纯函数,离线):
- ``hp_floor(board_tier, nodes_left, target_pwin, plane)``:hp 地板反解——最小 hp 使
  P(win) ≥ target_pwin(「手写门变模型定理」的出口;消费位 = sim ``cw_sim_battle``)。
  原 ``first_passage_win``/``risk_posture``/``p_win_lambda`` 三函数已随死代码
  清偿移除(零生产消费面),分布卷积基础(``_survive_cdf``)保留为其留位。

升级路径(并轨 V2):换桶分布转移矩阵、刷新商店 Bernoulli 赌局化、hp 残值补丁为
后续扩展方向(K1-K3 判据)。
"""
from __future__ import annotations

# ⚖️ 单一源(统一):掉血先验基准表持有者 = cw_plane_table
# (起 = 原 DP 标定面的保留归属,物理原语层,被 sim_env/economy 同源消费);
# 本模块引用之并在此定义分布语义(CV/位面乘数)。
from sr_od.application.currency_war.kernel.cw_plane_table import (
    HP_LOSS_MU,  # noqa: F401
)

# (P1 标定基线;P2+ 位面维经 registry.p2_cond_loss_table 标定进模型,
# 见 _loss_dist 边界声明;重尾一击型 boss 掉血 v1 用实测桶替换)
CV_PRIOR: float = 0.5   # 组内变异系数先验(K0 实测 0.4-0.62 的收缩中值)


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
    """单节点掉血分布(板强档 × 位面 → [(掉血量,概率)] 三点离散:μ-σ/μ/μ+σ 截非负)。

    μ 标定源合一:P1 = HP_LOSS_MU 现档
    (P1 零漂移,不走 P2 标定);P2+ = 两态同构 μ(tier)=(1−p(rung(tier)))
    ·L_cond_mix —— 胜率=registry.p_win_p2_by_rung(rung 坐标=board_tier
    0-3 钳 0-2,与 p_win 表 k3 折叠同口径),条件败面=registry.
    p2_cond_loss_table 按位面模板战斗构成混合;P3 不在标定域,别名 P2
    (沿用位面维别名先例)。

    边界声明(与 DP 层的口径关系,「5× 差=语义差为主」判读
    的落点):本层是分布模型 estimand(每节点无条件期望掉血 ± CV 抖动,
    喂首达生存卷积),DP 层是确定性期望递推——两者共用同一标定(胜率表
    +条件败面档)但函数不同,数值对齐 ≠ 函数同一;本层不再持有独立位面
    乘数自由度,位面维全部来自 registry 标定(版本基准=registry.
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


def hp_floor(board_tier: int, nodes_left: int, target_pwin: float, plane: int = 1,
             hp_cap: int = 100) -> int:
    """hp 地板反解(「手写门变模型定理」的核心出口):最小 hp 使 P(win) ≥ target_pwin。

    语义:给定板强/剩余日程/位面,「想以 ≥ target 的概率活到底」至少需要多少血 ——
    保血阈值从手拍常数变生存曲线的导出量。
    单次卷积 + CDF 扫描(P(win) 对 hp 单调);hp_cap 内无解 → 返回 hp_cap(无底可保)。
    """
    cdf = _survive_cdf(board_tier, nodes_left, plane, hp_cap)
    for hp in range(1, hp_cap + 1):
        if cdf[hp] >= target_pwin:
            return hp
    return hp_cap
