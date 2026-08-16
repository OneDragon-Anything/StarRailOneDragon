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

import math

# 掉血分布先验(v0:HP_LOSS_PRIOR 均值 × 离散抖动;telemetry K0:CV p1=0.62/p2=0.40)
# 桶宽 5(hp 桶一致);每个 (板强档, 节点) 的掉血 = 均值 μ 附近 ± 1σ 离散三点分布
# (保守:重尾一击型 boss 掉血在 v1 用实测桶替换,结构不变)。
HP_LOSS_MU: dict[int, float] = {0: 14.0, 1: 7.0, 2: 2.5, 3: 0.8}
CV_PRIOR: float = 0.5   # 组内变异系数先验(K0 实测 0.4-0.62 的收缩中值)

# 三区边界先验(K2 涌现对拍锚:DEAD_HP=20 三门 / HP<40 分档 / 满息 50)
ZONE_CRITICAL_HP: int = 40     # 二区下界(ADR-0141/0143 分档;对拍锚)
ZONE_DEATH_EDGE_HP: int = 20   # 三区下界(DEAD_HP=20;对拍锚)


def _loss_dist(board_tier: int) -> list[tuple[float, float]]:
    """单节点掉血分布(板强档 → [(掉血量, 概率)] 三点离散:μ-σ/μ/μ+σ 截非负)。"""
    mu = HP_LOSS_MU.get(min(3, max(0, board_tier)), 14.0)
    sigma = mu * CV_PRIOR
    lo = max(0.0, mu - sigma)
    mid = mu
    hi = mu + sigma
    # 三点等权(离散近似;实测桶替换后为任意支撑集)
    return [(lo, 1 / 3), (mid, 1 / 3), (hi, 1 / 3)]


def first_passage_win(board_tier: int, hp: int, nodes_left: int) -> float:
    """生存首达概率:剩余 nodes_left 个战斗节点,累计掉血 < hp 的概率(分布卷积 + CDF)。

    数学:掉血 i.i.d. 离散分布 → 总和分布 = n-卷积;P(win) = P(Σ loss < hp)。
    数值:半格步长(2.5)格点卷积,O(nodes × hp_grid × support)。
    """
    if hp <= 0:
        return 0.0
    if nodes_left <= 0:
        return 1.0
    step = 2.5
    n_grid = int(math.ceil(hp / step)) + 1
    # 初始分布:delta(0)
    dist = [0.0] * (n_grid + 1)
    dist[0] = 1.0
    support = _loss_dist(board_tier)
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
    return min(1.0, sum(dist))   # 存活 = 全程未超 hp 格


def p_win_lambda(board_tier: int, hp: int, nodes_left: int) -> float:
    """λ_hp = P(win | hp+1) − P(win | hp):HP 的边际生存价值(峰形曲线的采样点)。"""
    return first_passage_win(board_tier, hp + 1, nodes_left) - first_passage_win(board_tier, hp, nodes_left)


def risk_posture(board_tier: int, hp: int, nodes_left: int) -> str:
    """三区律:盈余 / 临界 / 必死边缘。

    边界由 λ_hp 与 P(win) 联合解出(**非手写 hp 阈值**;弱板长程下「必死边缘」的 hp 绝对
    值可高达 60+ —— 漂移把屏障推远,这正是固定 DEAD_HP=20 类手写门要被替代的证据):
    必死边缘 = P(win) < 35% 且 λ_hp 已回落(±1 血不改大局,该赌右尾);临界 = λ_hp 活跃
    (每点血实质改变活率);盈余 = 其余。
    """
    if hp <= 0:
        return '必死边缘'
    pw = first_passage_win(board_tier, hp, nodes_left)
    lam = p_win_lambda(board_tier, hp, nodes_left)
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


def p_win_projection(level: int, hp: int, nodes_left: int, rb: float = 0.0) -> float:
    """GameState → P(win)(一站式;05 号 salvage 触发量与 19 号计价的入口)。"""
    return first_passage_win(board_tier_of(level, rb), hp, nodes_left)
