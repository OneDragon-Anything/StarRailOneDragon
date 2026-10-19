"""节点日程与标定表模块(纯常量/纯函数;零 DP、零 session 写端)。

起,本模块是生产路径消费的**真值/标定面**
的保留归属(D3 契约:真值消费者迁保留表函数模块,禁内联常量置换——
``nodes_of_plane`` 是会话自适应真值(P1=9/P2=7/P3 进表自适应),
``p_win_p2`` 是两态胜率函数(BLUEPRINT §3.1 N4 继续消费),内联任一处
= 修掉的 P2 计 9 病灶成批回流)。日程感知 DP 规划器
已按 BLUEPRINT §3 裁决退出生产路径,不在本模块。

**现役口径(9 制几何层停用)**:节点身份 = ``(位面, 轮)`` 序位键,
逐位面节点类型序列唯一真值 = ``cw_node_schedule`` 真值表 + GameState
场字段 ``node_seq_by_plane``(修饰局 10/8、默认局 9/7;None 未注册态
回退默认表)。数量语义的视界量不在此层(裁决点 9:框架不向策略
供视界量,序列模块只留键原语;策略侧经 mandate_v1/statefn/horizon
门面场字段自算,kernel 判据点就地求和)——9 制几何层 11 符号
(schedule_of/node_t_of/r_remaining 族/plane_offsets/plane_end_slots/
NODES_PER_PLANE/TOTAL_NODES/DEFAULT_PLANE_LENGTHS/PLANE_FALLBACK_PRIORS)
已整体停用,迁移对照 = 迭代 abolish-node-ordinal
details/horizon-cleanup.md §2-§6。

承载面(按消费面划定的最小集):
- 本位面轮数真值:nodes_of_plane(实况读、不夹);
- 升级费用查询:clicks_to_level/level_cost(逐帧现读单价 =
  kernel cw_economy.xp_click_cost,本表只供次数);
- 息封顶常量:GOLD_CAP_INTEREST(息闭式本体 = kernel cw_economy
  .interest 唯一源,DEFAULT_INTEREST_CAP 由其派生);
- 损血先验表:HP_LOSS_MU(原 DP 模块 HP_LOSS_PRIOR 平移,
  统一的单一源,消费方=cw_first_passage 分布模型);
- P2 两态胜率映射:p_win_p2(registry.p_win_p2_by_rung 分段线性,
  阈值层与 排程共用);
- 概率峰值级查表:peak_refresh_level(目标费用档 → 峰值级,规则倡导审读 §1.3
  R4 排程判据的查表分量)。
"""
from __future__ import annotations


def _probe_books(session):
    """探针簿记宿主解析(终态契约 §A′:gs.node_books 单一源)。

    双形态宿主:GameState 本体(终态零参 decide 直传 self.gs)→ 直读
    node_books;session/裸对象(过渡期旧读法)→ 经 game_state_of 桥;
    None → 一次性空载体,回退语义与旧 getattr 缺省同型。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
        NodeBooks,
        game_state_of,
    )
    if session is None:
        return NodeBooks()
    if isinstance(session, GameState):
        return session.node_books
    return game_state_of(session).node_books


# ===== 经济先验 =====
GOLD_CAP_INTEREST: int = 50   # 息封顶(10 金 1 息、5 档封顶)
XP_CLICK_COST_FLAT: int = 4   # 购买经验单击价先验(实测 4-8 取下限;
# 生产升级费现读 = kernel cw_economy.xp_click_cost,本值仅 level_cost 先验用)

#: nodes_of_plane 表缺回退告警的一次性指纹(防每帧刷屏;同 [cw!] 可 grep 纪律)
_NODES_OF_PLANE_WARNED: set[str] = set()


def nodes_of_plane(session) -> int:
    """本位面轮数真值(单一源)。

    真值源 = ``gs.node_books.plane_node_table``(开局帧实读槽序表,
    cw_screen_prep 每位面首帧写、位面内恒定):P1=9 槽、P2=7 槽(16 局
    语料实证;P2=7 的判定语义依据 = cw_discipline_rules plane_last_
    battle「P2 boss@r7 判正,旧按 9 计永不触发」),P3 首局进表即自适应。
    表缺(裸 session/None/sim P1 段/开局首帧前)→ 回退**节点序列默认表
    P1 长** = ``len(node_sequence_of(1, 场字段现值 or None))``(修饰局
    10 / 默认局 9,真值随序列表,不设独立长度常量)并记一次性
    ``[cw!][plane_table]`` 告警(P3 真值未知期,回退事件即记档通道)。

    P1 等价性:生产 P1 表恒 9 槽(默认局;修饰局 P1 实长 10 由场字段
    回退承接)→ 两路 P1 取值同源。duck-typed 读 session。
    """
    table = _probe_books(session).plane_node_table
    if table:
        return len(table)
    from one_dragon.utils.log_utils import log as _log
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
        game_state_of,
    )
    from sr_od.application.currency_war.kernel.cw_node_schedule import (
        node_sequence_of,
    )
    if session is None:
        seqs = None
    elif isinstance(session, GameState):
        seqs = session.node_seq_by_plane.value or None
    else:
        seqs = game_state_of(session).node_seq_by_plane.value or None
    fallback = len(node_sequence_of(1, seqs))
    global _NODES_OF_PLANE_WARNED
    key = repr(type(session).__name__)
    if key not in _NODES_OF_PLANE_WARNED:
        _NODES_OF_PLANE_WARNED.add(key)
        _log.warning('[cw!][plane_table] plane_node_table 缺(%s)→ 本位面轮数'
                     '回退节点序列默认表 P1=%d(表回填后自适应)',
                     key, fallback)
    return fallback


# ===== 标定表/纯函数 =====

# 板强 → 每战斗节点期望掉血先验基准表(统一单一源;消费方
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


#: XP 门槛表:权威表 = cw_economy.XP_TO_NEXT_LEVEL(单一源;
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
    """升一级总金先验(次数 × flat 单击价;现读单价版 =
    kernel cw_economy.xp_click_cost,本函数仅供先验/测试口径)。"""
    return clicks_to_level(level) * XP_CLICK_COST_FLAT


# (``plane_table.interest`` 已删:与
#  kernel cw_economy.interest 同形双源、全仓零生产调用——息闭式唯一源
#  = kernel cw_economy.interest(cap 参数化,消费 cap_resolved 链)。)


def peak_refresh_level(cost: int) -> int:
    """目标费用档 → 刷新概率峰值级(REFRESH_PROB 表 Lv1-9 段 argmax;
    规则倡导审读 §1.3 R4 排程判据②的查表分量)。并列取高档([7] 口述
    「允许高一档」:峰值平手时高一级的相邻档概率差可忽略,而提前一级
    到位=多一轮峰值窗口)。cost 越界(非 1-5)→ 夹到边界档。
    lv10 显式排除:峰值搜索域 = 1-9——lv10 是满级终端态,「要不要停
    在 lv9 不冲 lv10」由 lv9→10 特档单独覆盖(摊还账闭式,P35:标定带内
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
