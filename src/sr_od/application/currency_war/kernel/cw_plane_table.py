"""节点日程与标定表模块(纯常量/纯函数;零 DP、零 session 写端)。

ADR-0465 起,本模块是生产路径消费的**真值/标定面**
的保留归属(D3 契约:真值消费者迁保留表函数模块,禁内联常量置换——
``nodes_of_plane`` 是会话自适应真值(P1=9/P2=7/P3 进表自适应,ADR-0366),
``p_win_p2`` 是两态胜率函数(BLUEPRINT §3.1 N4 继续消费),内联任一处
= ADR-0366 修掉的 P2 计 9 病灶成批回流)。日程感知 DP 规划器
已按 BLUEPRINT §3 裁决退出生产路径,不在本模块。

承载面(按消费面划定的最小集):
- 位面日程几何:NODES_PER_PLANE/TOTAL_NODES/DEFAULT_PLANE_LENGTHS/
  plane_offsets/plane_end_slots/schedule_of/nodes_of_plane/node_t_of;
- 升级费用查询:clicks_to_level/level_cost(逐帧现读单价由消费方
  economy_cycle.upgrade_plan_fee 承担,本表只供次数);
- 息封顶常量:GOLD_CAP_INTEREST(息闭式本体 = kernel cw_economy
  .interest 唯一源,DEFAULT_INTEREST_CAP 由其派生);
- 损血先验表:HP_LOSS_MU(原 DP 模块 HP_LOSS_PRIOR 平移,ADR-0183
  统一的单一源,消费方=cw_first_passage 分布模型);
- P2 两态胜率映射:p_win_p2(registry.p_win_p2_by_rung 分段线性,
  阈值层与 ADR-0465 排程共用);
- 概率峰值级查表:peak_refresh_level(目标费用档 → 峰值级,规则倡导审读 §1.3
  R4 排程判据的查表分量)。
"""
from __future__ import annotations


# ===== 日程/经济先验 =====
NODES_PER_PLANE: int = 9
TOTAL_NODES: int = NODES_PER_PLANE * 3
GOLD_CAP_INTEREST: int = 50   # 息封顶(10 金 1 息、5 档封顶)
XP_CLICK_COST_FLAT: int = 4   # 购买经验单击价先验(ADR-0129 实测 4-8 取下限;
# 生产升级费走 economy_cycle.upgrade_plan_fee 的 OCR 现读,本值仅 level_cost 先验用)

#: nodes_of_plane 表缺回退告警的一次性指纹(防每帧刷屏;同 [cw!] 可 grep 纪律)
_NODES_OF_PLANE_WARNED: set[str] = set()

# ===== 位面日程(槽序排布;ADR-0368) =====
#: 日程先验:(位面1, 位面2, 位面3) 各自轮数。P1=9 结构已知;P2 真值 7
#: 但以 session 表为准(生产自适应);P3 未知期保持 9 先验。
DEFAULT_PLANE_LENGTHS: tuple[int, int, int] = (
    NODES_PER_PLANE, NODES_PER_PLANE, NODES_PER_PLANE)

#: schedule_of 未揭晓位面的回退先验(逐面):(9, 9, 9)。端点纪律:
#: 未揭晓位面真值不可判 ⇒ 回退统一取结构上端(位面长度上限 9),
# 消除回退低于真值时 horizon 的系统性低估通道(低回退会把不可逆卖面门槛压低)。
# 语料众数观测(5/6 完整局为 7)是参考记录而非逐局真值,不作回退依据。
# 与 DEFAULT_PLANE_LENGTHS(几何缺省,裸调用/测试兼容口径 9,9,9)数值相同但
# 语义分立——后者只作 plane_offsets/plane_end_slots/build_ledger 的参数缺省,
# 生产调用方应显式传 schedule_of(session) 实际长度,两者禁互替。
PLANE_FALLBACK_PRIORS: tuple[int, int, int] = (
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

    真值源 = ``session.plane_lengths_seen``(cw_screen_prep 每位面首帧随
    plane_node_table 记录的「本局已揭晓位面轮数」序列,P3 进表即自适应);
    未揭晓位面回退 ``PLANE_FALLBACK_PRIORS`` 逐面先验(9, 9, 9)——端点纪律
对称化:未揭晓真值不可判,统一取语料分布上端(位面长度上限 9)。
    脏表守卫:每位面长度夹 [1, NODES_PER_PLANE]
    (同 ADR-0366 超长脏表封顶语义)。duck-typed 读 session。
    """
    seen = getattr(session, 'plane_lengths_seen', None) or []
    out = []
    for i in range(3):
        length = int(seen[i]) if i < len(seen) else PLANE_FALLBACK_PRIORS[i]
        out.append(min(max(length, 1), NODES_PER_PLANE))
    return tuple(out)


def node_t_of(session: object, plane: object, round_num: object) -> int | None:
    """hp 新鲜度门时基(全局节点号):前序位面**实际长度**和 + 位面内轮次。

    长度源 = ``schedule_of(session)``(P1=9/P2=7/P3 进表自适应;ADR-0368
    单一源)——替代表迁波曾内联的 ``(plane-1)*9`` 字面量(假设每位面 9
    节点,P2 真值 7 时 P3 段系统性偏大 +2,判读底稿中危项 1,与 dd-003
    「禁写死 9」同型)。session 缺席(None/裸对象)或日程未揭晓 → 回退
    ``PLANE_FALLBACK_PRIORS``=(9,9,9),该态下取值与旧字面量逐位相同
    (迁移期等价口径,sim/裸 session 零行为差)。plane/round 缺效(None/0)
    → None = 门恒等支(与各消费位旧守卫同型)。

    **同式契约**:hp 新鲜度门的 now_t 产出位(决策读口)与结算锚写点
    (``cw_screen_battle_wait`` 的 ``session.last_hp_t``)必须同经本函数
    派生,禁单侧改式(单侧改式 = gap 判域静默漂移,契约正文见
    ``cw_hp_policy.apply_hp_freshness_gate`` 时基契约节)。
    """
    if not plane or not round_num:
        return None
    lengths = schedule_of(session)
    return sum(lengths[:int(plane) - 1]) + int(round_num)


def nodes_of_plane(session) -> int:
    """本位面轮数真值(ADR-0366,单一源)。

    真值源 = ``session.plane_node_table``(开局帧实读槽序表,
    cw_screen_prep 每位面首帧写、位面内恒定):P1=9 槽、P2=7 槽(16 局
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


#: XP 门槛表:权威表 = cw_economy.XP_TO_NEXT_LEVEL(候裁9 迁居后单一源;
#: 1/2 级游戏内近乎白送,权威表未收录 → 本地先验补 1/2 级)。惰性取表:
#: 本模块保持 kernel 纯表叶位(零 kernel 模块级依赖),免词汇迁移环。
_XP_NEED: dict[int, int] | None = None
_XP_PER_BUY: int = 4


def _xp_need() -> dict[int, int]:
    global _XP_NEED
    if _XP_NEED is None:
        from sr_od.application.currency_war.kernel.cw_economy import (
            XP_PER_BUY,
            XP_TO_NEXT_LEVEL,
        )
        _XP_NEED = {1: 4, 2: 4, **XP_TO_NEXT_LEVEL}
        global _XP_PER_BUY
        _XP_PER_BUY = XP_PER_BUY
    return _XP_NEED


def clicks_to_level(level: int) -> int:
    """当前级 → 下一级所需购买经验次数(ceil;(need)/XP_PER_BUY;xp 结转忽略,原子近似)。"""
    need = _xp_need().get(level, 84)
    return max(1, -(-need // _XP_PER_BUY))


def level_cost(level: int) -> int:
    """升一级总金先验(次数 × flat 单击价;现读单价版在
    economy_cycle.upgrade_plan_fee,本函数仅供先验/测试口径)。"""
    return clicks_to_level(level) * XP_CLICK_COST_FLAT


# (第二息实现 ``plane_table.interest`` 已删(ADR-0598 随批清理):与
#  kernel cw_economy.interest 同形双源、全仓零生产调用——息闭式唯一源
#  = kernel cw_economy.interest(cap 参数化,消费 cap_resolved 链)。)


def peak_refresh_level(cost: int) -> int:
    """目标费用档 → 刷新概率峰值级(REFRESH_PROB 表 Lv1-9 段 argmax;
    规则倡导审读 §1.3 R4 排程判据②的查表分量)。并列取高档([7] 口述
    「允许高一档」:峰值平手时高一级的相邻档概率差可忽略,而提前一级
    到位=多一轮峰值窗口)。cost 越界(非 1-5)→ 夹到边界档。
    lv10 显式排除:峰值搜索域 = 1-9——lv10 是满级终端态,「要不要停
    在 lv9 不冲 lv10」由 lv9→10 特档单独辖(摊还账闭式,P35:标定带内
    停手窗恒负);若把 lv10 计入峰值级,排程判据②会用「峰值级>当前级」
    绕过该特档门,与既裁停手结论打架(表内 lv10 的 5费概率 0.25 高于
    lv9 的 0.10,不做排除即会命中此形态)。
    """
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    c = min(5, max(1, int(cost)))
    best_l, best_p = 1, -1.0
    for lv in range(1, 10):
        p = refresh_prob(lv, c)
        if p >= best_p:
            best_p, best_l = p, lv
    return best_l


# ===== 视界层 R_剩余族(自 strategies statefn/horizon 下沉单一源,
# ===== kernel 判据(schedule_upgrade 的 U_L 阈值检验)消费 R_剩余,下沉
# ===== 保持「kernel 禁 import strategies」桶依赖矩阵;statefn/horizon 改
# ===== import 重定向,消费方调用零改——与 schedule_upgrade 下沉同款先例)=====


def r_remaining_in_plane(node_in_plane: int, plane_length: int) -> int:
    """本位面剩余节点数(含当前节点;node_in_plane 为 1 基槽序)。"""
    return max(0, plane_length - (node_in_plane - 1))


def r_global(session: object, plane: int, node_in_plane: int) -> int:
    """R_全局 = 当前节点 + 后续位面按**实际长度**求和(NMF §2「R_全局」行)。

    长度全部来自 ``schedule_of(session)``(启动必载真值);金跨位面继承
    ⇒ 视界跨位面求和;禁任何路径引用 NODES_PER_PLANE 先验替代 session 表。
    """
    lengths = schedule_of(session)
    total = r_remaining_in_plane(node_in_plane, lengths[plane - 1])
    for i in range(plane, len(lengths)):
        total += lengths[i]
    return total


def r_remaining(session: object, plane: int, node_in_plane: int) -> int:
    """R_剩余(到局终的总剩余轮数;Φ̂=Ī×R_剩余 的组成因子,R2-8)。"""
    return r_global(session, plane, node_in_plane)
