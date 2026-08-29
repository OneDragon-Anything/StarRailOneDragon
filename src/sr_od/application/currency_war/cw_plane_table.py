"""节点日程与标定表模块(纯常量/纯函数;零 DP、零 session 写端)。

重构迁移迁移批 3(ADR-0465)(ADR-0465) 起,本模块是原 DP 模块(git prior art)中被生产路径消费的**真值/标定面**
的保留归属(`w623_batch3_pre-mortem/` D3:真值消费者迁保留表函数模块,禁内联常量置换——
``nodes_of_plane`` 是会话自适应真值(P1=9/P2=7/P3 进表自适应,ADR-0366),
``p_win_p2`` 是两态胜率函数(BLUEPRINT §3.1 N4 继续消费),内联任一处
= ADR-0366 修掉的 P2 计 9 病灶成批回流)。原模块的日程感知 DP 规划器
(求解/姿态/节点目标接缝)已按 BLUEPRINT §3 裁决退出生产
路径并整文件删除,git 历史为 prior art。

承载面(按消费面划定的最小集):
- 位面日程几何:NODES_PER_PLANE/TOTAL_NODES/DEFAULT_PLANE_LENGTHS/
  plane_offsets/plane_end_slots/schedule_of/nodes_of_plane;
- 升级费用查询:clicks_to_level/level_cost(逐帧现读单价由消费方
  economy_cycle.upgrade_plan_fee 承担,本表只供次数);
- 息闭式:interest/GOLD_CAP_INTEREST(min(g//10,5) 截断点);
- 损血先验表:HP_LOSS_MU(原 DP 模块 HP_LOSS_PRIOR 平移,ADR-0183
  统一的单一源,消费方=cw_first_passage 分布模型);
- P2 两态胜率映射:p_win_p2(registry.p_win_p2_by_rung 分段线性,
  阈值层与迁移迁移批 3(ADR-0465)(ADR-0465) 排程共用);
- 概率峰值级查表:peak_refresh_level(目标费用档 → 峰值级,`w615_rules_advocacy/` §1.3
  R4 排程判据的查表分量)。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_state import XP_PER_BUY, XP_TO_NEXT_LEVEL

# ===== 日程/经济先验(原 DP 模块常量平移,消费面逐位一致) =====
NODES_PER_PLANE: int = 9
TOTAL_NODES: int = NODES_PER_PLANE * 3
GOLD_CAP_INTEREST: int = 50   # 息封顶(10 金 1 息、5 档封顶)
XP_CLICK_COST_FLAT: int = 4   # 购买经验单击价先验(ADR-0129 实测 4-8 取下限;
# 生产升级费走 economy_cycle.upgrade_plan_fee 的 OCR 现读,本值仅 level_cost 先验用)

#: nodes_of_plane 表缺回退告警的一次性指纹(防每帧刷屏;同 [cw!] 可 grep 纪律)
_NODES_OF_PLANE_WARNED: set[str] = set()

# ===== 位面日程(槽序排布;ADR-0368,迁移审计 w169(git 历史)) =====
#: 日程先验:(位面1, 位面2, 位面3) 各自轮数。P1=9 结构已知;P2 真值 7
#: 但以 session 表为准(生产自适应);P3 未知期保持 9 先验。
DEFAULT_PLANE_LENGTHS: tuple[int, int, int] = (
    NODES_PER_PLANE, NODES_PER_PLANE, NODES_PER_PLANE)


def plane_offsets(pl: tuple[int, ...] = DEFAULT_PLANE_LENGTHS) -> tuple[int, ...]:
    """日程 → 各位面起始槽(累计偏移;(9,9,9)→(0,9,18))。"""
    offs: list[int] = []
    acc = 0
    for length in pl:
        offs.append(acc)
        acc += length
    return tuple(offs)


def plane_end_slots(pl: tuple[int, ...] = DEFAULT_PLANE_LENGTHS) -> frozenset[int]:
    """日程 → 各位面末槽(boss 奖金槽;(9,9,9)→{8,17,26})。"""
    offs = plane_offsets(pl)
    return frozenset(offs[i] + pl[i] - 1 for i in range(len(pl)))


def schedule_of(session) -> tuple[int, int, int]:
    """位面日程真值(ADR-0368,单一源)。

    真值源 = ``session.plane_lengths_seen``(prep_director 每位面首帧随
    plane_node_table 记录的「本局已揭晓位面轮数」序列,P3 进表即自适应);
    未揭晓位面回退 9 先验。脏表守卫:每位面长度夹 [1, NODES_PER_PLANE]
    (同 `w154_p2d/`/ADR-0366 超长脏表封顶语义)。duck-typed 读 session。
    """
    seen = getattr(session, 'plane_lengths_seen', None) or []
    out = []
    for i in range(3):
        length = int(seen[i]) if i < len(seen) else NODES_PER_PLANE
        out.append(min(max(length, 1), NODES_PER_PLANE))
    return tuple(out)


def nodes_of_plane(session) -> int:
    """本位面轮数真值(ADR-0366,迁移审计 w167(git 历史) 口径断层修复的单一源)。

    真值源 = ``session.plane_node_table``(r306 开局帧实读槽序表,
    prep_director 每位面首帧写、位面内恒定):P1=9 槽、P2=7 槽(16 局
    语料实证)、P3 首局进表即自适应。表缺(裸 session/None/sim P1 段/
    开局首帧前)→ 回退 ``NODES_PER_PLANE=9`` 先验并记一次性
    ``[cw!][plane_table]`` 告警(P3 真值未知期,回退事件即记档通道)。

    P1 等价性:生产 P1 表恒 9 槽;sim P1 段不写表(ADR-0362 只在 P2
    进场写)→ 两路 P1 取值 ≡ 先验常量。duck-typed 读 session。
    """
    table = getattr(session, 'plane_node_table', None)
    if table:
        return len(table)
    from one_dragon.utils.log_utils import log as _log
    global _NODES_OF_PLANE_WARNED
    key = repr(type(session).__name__)
    if key not in _NODES_OF_PLANE_WARNED:
        _NODES_OF_PLANE_WARNED.add(key)
        _log.warning('[cw!][plane_table] plane_node_table 缺(%s)→ 本位面轮数'
                     '回退先验 NODES_PER_PLANE=%d(表回填后自适应)',
                     key, NODES_PER_PLANE)
    return NODES_PER_PLANE


# ===== 标定表/纯函数 =====

# 板强 → 每战斗节点期望掉血先验基准表(ADR-0183 统一单一源;消费方
# = cw_first_passage 分布模型的 μ 侧。键=板强档 0-3)。
HP_LOSS_MU: dict[int, float] = {0: 14.0, 1: 7.0, 2: 2.5, 3: 0.8}


def p_win_p2(b: float) -> float:
    """板强 b → P2 战斗条件胜率(registry.p_win_p2_by_rung 分段线性;
    两态投影与阈值层共用的板强→胜率映射单一源)。"""
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    tbl = DEFAULT_REGISTRY.p_win_p2_by_rung
    x = min(2.0, max(0.0, float(b)))
    i = int(x)
    frac = x - i
    lo = tbl.get(i, 0.0)
    hi = tbl.get(min(2, i + 1), lo)
    return lo + (hi - lo) * frac


# XP 门槛表:cw_state 权威表从 3 级起(1/2 级游戏内近乎白送,表未收录)→ 本地先验补 1/2 级
_XP_NEED: dict[int, int] = {1: 4, 2: 4, **XP_TO_NEXT_LEVEL}


def clicks_to_level(level: int) -> int:
    """当前级 → 下一级所需购买经验次数(ceil;(need)/XP_PER_BUY;xp 结转忽略,原子近似)。"""
    need = _XP_NEED.get(level, 84)
    return max(1, -(-need // XP_PER_BUY))


def level_cost(level: int) -> int:
    """升一级总金先验(次数 × flat 单击价;现读单价版在
    economy_cycle.upgrade_plan_fee,本函数仅供先验/测试口径)。"""
    return clicks_to_level(level) * XP_CLICK_COST_FLAT


def interest(gold: int) -> int:
    """息闭式:min(g//10, 息帽档数)。截断点=息线(守息线同源派生,
    `w611_econ_cycle/` §2.2 恒等式:interest_cap×10)。"""
    return min(gold // 10, GOLD_CAP_INTEREST // 10)


def peak_refresh_level(cost: int) -> int:
    """目标费用档 → 刷新概率峰值级(REFRESH_PROB 表 argmax;`w615_rules_advocacy/` §1.3
    R4 排程判据②的查表分量)。并列取高档([7] 口述「允许高一档」:
    峰值平手时高一级的相邻档概率差可忽略,而提前一级到位=多一轮
    峰值窗口)。cost 越界(非 1-5)→ 夹到边界档。"""
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    c = min(5, max(1, int(cost)))
    best_l, best_p = 1, -1.0
    for lv in range(1, 10):
        p = refresh_prob(lv, c)
        if p >= best_p:
            best_p, best_l = p, lv
    return best_l
