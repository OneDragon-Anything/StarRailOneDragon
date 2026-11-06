"""货币战争 · 方向载体模块(过渡候选机器 + 囤货/回退接口;纯逻辑,不碰游戏)。

终局线选择归策略层候选-锁定制(mandate_v1.session_scope/line_select:
硬规则查表 + 时点兜底,锁定后不换线,防摇摆由结构承载非滞回参数,
12 号篇 §1);原阵容锁定状态机(信号分层终局阵容锁定/撤销出口①②③/P2 移交
强锁/P3 强锁/降格终局)不存于本模块。本模块保留三族:

- **过渡候选机器**(:func:`update_transition_candidates`/
  ``transition_locked``/条目集族):过渡层方向机器(计分三面/候选
  top3/候选内成型锁定)——comp-structure-unification 3.3 落地,旧 P1
  配方对链(update_p1_recipe/``p1_pair`` 族)已随配方决策层退役删除,
  过渡层生命周期挂钩终局锁定事件(锁定写入即退役清空);
- **囤货与回退接口**(:func:`hoard_target_set`/``k_empty_window_fallback``/
  ``locked_buy_*`` 族):买侧与部署侧的现行读面;``locked_comp``/``phase``
  改为锁定线槽派生缓存(写端 = mandate_v1.session_scope,锁定 ⟺
  target_comp 非空)。P86 无目标期三分支判据的甲/乙臂已随统一让位
  优先级迭代 3.4 退役(K 目标未锁期源切换 = 策略层候选快照三线并集
  ∪ 过渡层贡献名单;丙分支保利息缺省保留);
- **定型权威**(:func:`committed_authority`/:func:`committed_from`):
  规则④「位面 ≥ 2 恒定型」支已停用(P2 时点兜底锁定替代;§1.6 行为
  差申报:P2 入口至兜底锁帧的短窗 = 双轨期口径)。

**教义边界(已退役口述登记簿)**:[21] final 件「买而不上」→ 本模块
只改囤货方向(输出「囤货目标集合」供买侧消费),不改板上、不产出
任何上场/换人动作;[23] 终局线由锁定承载(锁定后不换线)。
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    refresh_prob,
)
from sr_od.application.currency_war.kernel.cw_comps import (
    TRANSITION_COMBO_PARTS,
    TRANSITION_LIBRARY,
    Comp,
    bond_score_members,
    derive_key_equips,
    form_progress,
    get_comp,
    transition_bond_of,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
    level_of,
    max_units_of,
    plane_of,
    round_num_of,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_line_scales import (
    FEAR_PENALTY,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    PLANE_NODE_TABLES,
)
from sr_od.application.currency_war.kernel.cw_plugins import (
    cross_line_skeleton as _cross_line_skeleton,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )

# ===== 常量(意向层机器停用后保留的常量;撤销/信号族随机器删除)=====

# 无目标期帧囤货缺省:P86 三分支判据的甲臂(方向化囤货)与乙臂(枢纽
# 期权)已随统一让位优先级迭代 3.4 退役(总纲 §2.7【拍】:K 目标未锁期
# 源切换 = 策略层候选快照三线成员并集 ∪ 配方成员,买面与优先级面统一;「机器判活方向
# ∉ 候选 top3」的囤货兑现通道随锁后不换线消亡——与单卡核心囤积同逻辑)。
# 证明处置:p86-proof-batch.md 甲分支定理 A 证明随判据死迁出(3.4 对
# 照项结论),乙分支证明章同批删除;丙分支(换现保利息,命题 C)域
# = 旧 p2plus 位面带,已随 comp-structure-unification 3.3 换轴废除
# (未终局锁定帧过渡层照常活跃,终局锁定帧恒有方向)——命题 C 表述
# 留档证明批,在役消费面不复存在(见下方退役注记)。

# 跨线骨架件(strategy_v4「目标件」定义节 class3)。弱意向态只囤这批
# (点0:撤销后去向——只囤跨线骨架件)。
# **派生**自 ``cw_plugins.W16_MAJORITY_LINES``
# (≥3 线过半 8 张 + 恰 2 家族过半且非线级 carry 的边界 2 张);
# 派生规则与 ``cw_plugins`` 内同源裁决口径见 ``cw_plugins.cross_line_skeleton``。
# 快照测试校验派生结果(不等 = 数据错)。
CROSS_LINE_SKELETON: tuple[str, ...] = _cross_line_skeleton()


@dataclass
class IntentionState:
    """方向状态载体(过渡候选机器 + kernel 派生缓存;意向层机器
    本体停用后的保留形态——阵容锁定状态机〔信号终局阵容锁定/撤销出口/P2 移交/
    P3 强锁/降格终局〕已删除,终局线锁定归策略层候选-锁定制:
    ``locked_comp``/``phase`` 改为锁定线槽派生缓存,写端 =
    mandate_v1.session_scope〔同步于 refresh/锁定动作〕;``transition_
    locked`` = 过渡层锁定态〔写端 = ``update_transition_candidates``,
    comp-structure-unification 3.3;旧 P1 配方对链字段族已随配方决策层
    退役删除〕。机器时代字段(``weak_comp``/``lock_layer``/``evicted``/
    ``demoted_endgame`` 等)无写端恒缺省,
    读端按保守缺省语义消费〔evicted=∅ 恒空集/demoted=False〕)。"""

    phase: str = 'unlocked'            # 'unlocked' | 'locked'(weak 随机器停用不可达;派生缓存,写端 = session_scope)
    locked_comp: str = ''              # 锁定线(COMP_LIBRARY 套名)
    lock_layer: int = 0                # 锁定时信号层(撤销出口②的「更高层级」基准)
    lock_plane: int = 0                # 锁定时机(遥测)
    lock_round: int = 0
    forced: bool = False               # 强制终局阵容锁定产生(P3 入口)
    weak_comp: str = ''                # 降级来源线(遥测;弱意向不指向具体线)
    demoted_endgame: bool = False      # 降格终局标记(全不可达;「赢不了就少输」)
    evicted: set[str] = field(default_factory=set)        # 冻结超限移出候选集的线
    # (体系对域字段族——p1_pair/transition_pair/pair_evicted/pair_drought/
    #  shop_supply_streak/p1_pair_frozen_obs/p1_pair_frozen/p1_pair_frozen_
    #  pair/p1_pair_refreeze_hold——已随配方决策层退役删除,考古走 git
    #  历史;驱动端 _update_pair_drought 无存活调用。)
    transition_locked: str = ''
    """过渡锁定条目名(空 = 未锁;非空 = 锁定条目名;写端单一 =
    ``update_transition_candidates``)。

    - 候选槽内条目成型即锁,锁后不换、不解、不重评(两套阵容库独立、
      各自候选与锁定,用户 2026-11-04 裁定;候选外条目偶然凑齐羁绊
      不锁——计分门控防偶然锁定);
    - 与终局锁定互不覆写:终局锁定写入点 = 过渡层退役清空出口
      (候选槽、本字段同点清空);位面切换不触发退役;
    - 承接旧 ``transition_locked_systems`` 槽的全部职责(锁定后的保护
      对象载体,合并裁定——不并存两套锁定态);
    - 遥测:``serialize_intention`` 字段全量序列化自动携带。
    """

    last_event: str = ''               # 最近一次状态转移(判读/遥测标记点)
    revoke_evidence: dict[str, object] = field(default_factory=dict)
    """撤销出口①开窗的证据字段快照(实机判读标记点,设计 R3.5「无证据
    字段的开窗=守卫失效」;serialize_intention 全量序列化自动携带)。

    - 写入端 = update_intention 撤销出口①开窗分支(唯一写入点,每次
      开窗整体覆写);keys:kind/miss_count/n_req/q/eps/alt_comp/e_alt/
      asset_thickness/a_min(语义见该分支注释)。出口③
      (supply_infeasible)同字段载体:kind/g_locked/alt_comp/g_alt/
      eps/h_eff/hp(见该分支注释)。
    - 清空时机 = _lock(重锁即证据消费完毕)与冻结驱逐/降格(转移
      不经撤销,证据随之失效)。空 dict = 本局尚无撤销开窗。"""

@dataclass(frozen=True)
class HoardTarget:
    """锁后效果的输出契约:囤货目标集合(买侧唯一消费面;不改板上)。

    - ``char_targets``:角色件集合(意向线骨架采购集 / 跨线骨架 / 兜底线);
    - ``equip_targets``:装备材料件(意向线 equip_assign 投影);
    - ``mode``:'locked' | 'forced' | 'p1_pair' | 'p1_transition'
      (锁定线采购集/强制锁定/过渡层方向采购集〔两层候选并集或锁定
      条目〕/空窗回退见即买并集;token 名沿用历史键面——遥测判读
      兼容,weak/fallback/demoted_endgame 分带已随各自判据退役)。
    """

    char_targets: frozenset[str]
    equip_targets: frozenset[str]
    mode: str


# ===== 内部派生 =====

# (旧 _v2_comps「v2 候选过滤(排除 legacy 线)」已删:消费端早已零调用——
#  统一部署/选线体系替代 v2 候选机制后死链,8 条 legacy 线实际一直
#  正常参与选线;Comp.family 字段随链退役,git 可溯)


def intention_core(comp: Comp) -> str:
    """一条线的「意向核心」(撤销计数③口径的具名核心)。

    = ``core_chars[0]``(首位=定义件契约,与 ``cw_comps.carry_anchor`` 同源
    ——carry 派生化后两读口归一,不再是两个概念;火花星间旅人线随主C 裁定
    收尾为火花)。单一核心保证 miss 计数良定义(避免花火/瓦尔特类共享件
    在多线间产生噪声信号)。
    """
    return comp.core_chars[0] if comp.core_chars else ''


def _visible_chars(gs: GameState) -> set[str]:
    """当前可见角色规范名:shop 在店 + bench/deployed 到手(识别层已归一)。"""
    names: set[str] = set()
    _shop = gs.shop.value   # payload 域:非当前画面 None(波3 切换)
    for card in shop_payload_content_cards(_shop):
        if card.name:
            names.add(card.name)
    front, back = deployed_rows_of(gs)
    for u in (*front, *back, *bench_units_of(gs)):
        if u is not None and u.char_id:
            names.add(u.char_id)
    return names


def plane_remaining_nodes(gs: GameState, session=None) -> int:
    """位面内剩余节点数(含当前轮;冻结超限的对照量)。

   :位面轮数按 ``nodes_of_plane(session)`` 本位面真值(P2=7;
    旧按全局 9 计使 P2 冻结超限对照量虚高 2 轮)。session 缺省 None →
    回退节点序列默认表 P1 长(裸调用/旧签名兼容;与 nodes_of_plane
    再基同款,不设独立长度常量)。
    """
    from sr_od.application.currency_war.kernel.cw_node_schedule import (
        node_sequence_of,
    )
    from sr_od.application.currency_war.kernel.cw_plane_table import nodes_of_plane
    n = nodes_of_plane(session) if session is not None \
        else len(node_sequence_of(1, None))
    r = min(max(1, round_num_of(gs)), n)
    return n - r + 1


def total_remaining_nodes(gs: GameState) -> int:
    """全局剩余节点数(可达性对照量;视界封顶 modeled planes)。

    场字段求和(裁决点 9 就地自算;旧恒按 9/位面 27 制闭式已随视界族
    停用修正——29 号稿 :26 登记的禁消费缺陷同步闭账):剩余 =
    Σ_{p>=plane} len − round + 1(含当前节点);位面 ∉ 序列表键集(≥4)
    = 表外防御 → 0(与策略门面 horizon 契约同款);None(未注册)
    回退默认表。唯一消费 = ``_core_reachable`` 遭遇窗门。"""
    seqs = gs.node_seq_by_plane.value
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    p = plane_of(gs)
    if p not in tables:
        return 0
    return sum(len(t) for k, t in tables.items() if k >= p) \
        - round_num_of(gs) + 1


def encounter_window_rounds(char_name: str, level: int) -> float:
    """单张核心的「再遇窗口」期望轮数(≈1/q;[22]③ 弃购期望账的静态近似)。

    近似(设计推断,sim 校准):单格出该角色概率 r = p(level,cost) × 剩余副本占
    同费剩余池比(忽略 depletion 细节,取 1/v);5 格商店至少一张 q = 1-(1-r)^5;
    期望轮 = 1/q。窗口未开(p=0)→ inf。
    """
    ch = CHARACTERS.get(char_name)
    if ch is None:
        return 0.0   # 未识别角色:不构成不可达证据,按立即可达处理
    p = refresh_prob(level, ch.cost)
    if p <= 0:
        return float('inf')
    v = DISTINCT_CARDS_PER_COST.get(ch.cost, 13)
    r = p / v   # 单格出该角色近似;owned depletion 留 sim 校准

    q = 1.0 - (1.0 - r) ** 5
    return 1.0 / q if q > 0 else float('inf')


def _core_reachable(comp: Comp, gs: GameState,
                     visible: set[str]) -> bool:
    """强制终局阵容锁定对象限定:核心已在手 或 再遇窗口期望 ≤ 剩余节点数(点0〔修N4〕)。"""
    core = intention_core(comp)
    if not core:
        return False
    if core in visible:
        return True
    return encounter_window_rounds(core, level_of(gs)) <= total_remaining_nodes(gs)




def _owned_chars(gs: GameState) -> set[str]:
    """已到手角色名(bench+deployed;不含 shop 可见——[23] 锁定由
    贯穿件=到手,店里出现过不构成方向承诺)。"""
    front, back = deployed_rows_of(gs)
    return {u.char_id for u in (*front, *back, *bench_units_of(gs))
            if u is not None and u.char_id}


def _asset_thickness(comp: Comp, gs: GameState) -> float:
    """候选线资产厚度:

    板上+bench 中该线终局件数(副本计星级当量:每副本按其 star 计)。
    终件 = core_chars。非终局件(跨线骨架件等)不抬本线厚度——撤销
    出口③的替代证据因此更严。"""
    _front, _back = deployed_rows_of(gs)
    pool = [*_front, *_back, *bench_units_of(gs)]
    star_of = {u.char_id: u.star for u in pool
               if u is not None and u.char_id}
    return float(sum(star_of.get(name, 0) for name in comp.core_chars))


def _core_miss_q(core: str, level: int) -> float:
    """核心单轮「至少一张出现」概率 q=1−(1−r)^5(5 格商店;与
    encounter_window_rounds 同一静态近似,r=p/v 忽略 depletion)。

    窗口未开(refresh_prob=0)或角色未识别 → 0.0(调用方按上限保险
    接管,不进闭式)。"""
    ch = CHARACTERS.get(core)
    if ch is None:
        return 0.0
    p = refresh_prob(level, ch.cost)
    if p <= 0:
        return 0.0
    r = p / DISTINCT_CARDS_PER_COST.get(ch.cost, 13)
    return 1.0 - (1.0 - r) ** 5




def p2_supply_horizon(gs: GameState,
                      session: StrategySession | None = None) -> int:
    """P2 有效供给视界 H = 位面剩余节点数(registry cw_plane_table 单一源,
    ``plane_remaining_nodes`` 本位面真值,P2=7)。

    H 只含日程维:视界回答「还剩几轮等得到缺件供给」,可行性 G 门
    (``line_completion_feasibility``)在 H 上取幂。hp 不入本视界
    (hp 是对局结果不是策略决策输入,2026-10-28 用户裁定;迭代
    changes/2026-10-28-hp-purge-refresh-reform R-3 删血项、机制保留
    ——行为变化 = 可行性与回退带不再随血低收紧,含 P2 未锁定窗口
    囤货方向;``k_empty_window_fallback`` 机器与消费链不受影响)。
    适用范围 = P2(P1/P3 调用面禁用——消费位自守)。
    """
    return plane_remaining_nodes(gs, session)




def line_completion_feasibility(gs: GameState,
                                comp: Comp | None,
                                session: StrategySession | None = None,
                                visible: set[str] | None = None) -> float:
    """P2 终局阵容锁定可行性 G = P(线核心缺件在有效视界 H 内全部现身)。

    两维合成(供给概率 × 剩余日程,零新自由参数):
    - 供给概率:每缺件单轮出现率 q = ``_core_miss_q``(cw_shop_odds
      refresh_prob × DISTINCT_CARDS_PER_COST 注册表派生,与
      ``encounter_window_rounds``/``core_miss_n_required`` 同一静态
      近似,忽略 depletion——设计先例同边界);
    - 视界 H = ``p2_supply_horizon``(位面剩余节点数;R-3 删血项后
      H = 日程维单分量,可行性/回退带不再随血低收紧);
    - 单件视界内现身率 F_m = 1−(1−q_m)^H,线完成率 G = ∏ F_m
      (缺件独立近似,构造性高估面如实声明:共同刷窗正相关使真实
      G 偏低,判据方向=只用于「不可行」侧的保守开闸,高估方向安全)。

    适用范围语义:
    - 终件口径 = core_chars(与 ``_asset_thickness`` 终件一致);
      shared/替班不计——可行性回答「这条线的核心能否凑齐」,不是
      「杂件买得到吗」;
    - 缺件已到手或在店(visible)→ 该件 F=1(完成路径已兑现;
      在店件当轮可买, affordability 归花钱层,意向层不双计);
    - 某缺件该级不出(refresh_prob=0)→ G=0(等级不可达,先验零);
    - 阵容为 None → 0.0。

    消费位(update_intention,全部 plane==2):P2 移交强锁候选门槛 /
    P2 信号缓锁门 / 已锁定终局阵容供给不可行降级(出口③)。判据阈值 =
    registry.revoke_miss_tolerance_eps(ε,既有单一源):G ≤ ε 意即
    「完成概率压不进证据噪声带以下」的反面——比撤销出口①的证据门槛
    (miss ≥ N_req,P2 视界内不可达的 21-42 轮)更强的先验不可行。
    可行性差 ≠ 不终局阵容锁定(P25 终局阵容锁定价值覆盖富余段核心出现即买):本判据
    只覆盖「锁向承诺」的准入与断供降级,不撤线内件买入义务。
    """
    if comp is None:
        return 0.0
    h_eff = p2_supply_horizon(gs, session)
    if h_eff <= 0:
        return 0.0
    vis = _visible_chars(gs) if visible is None else visible
    owned = _owned_chars(gs)
    g = 1.0
    for m in comp.core_chars:
        if m in owned or m in vis:
            continue
        q = _core_miss_q(m, level_of(gs))
        if q <= 0.0:
            return 0.0
        g *= 1.0 - (1.0 - q) ** h_eff
        if g <= 0.0:
            break
    return g


# ===== 终局阵容锁定断点观测分键(纯观测件;原分键前缀登记
# LOCK_PATH_OBS_KEY_PREFIXES 随观测写端未接入调用删除——声明的前缀键
# (weakplane_exempt_eval/p2_handoff_/promote_candidate_/intention_frame_ 等)
# 全仓零写点,宣称的守卫测试 test_cw_lock_path_obs_keys 已不存在;
# 语义存档 = math_proofs P65-P67 与 proofs/p65-promote-candidate-set-reachability.md)=====


# ===== 过渡阵容库候选机器(comp-structure-unification 3.3 新机器)=====
# 用户裁定(2026-11-04):过渡层与终局层两套阵容库独立,各自候选与锁定;
# 计分一维(成员持有)先行 + 词缀/boss 统一减分制(纯减分、不设排除特殊
# 逻辑——量子熄火等词缀实际效果是暂时性削弱,过渡期战斗强度低下不构成
# 不可玩;减分足够大时条目自然排不进前 3,评分体系自然涌现软排除)。

#: 过渡词缀/boss 减分表(键 = 词缀注册名或 boss 名;值 = 被克制的羁绊名
#: 列表)。行集依据 = cw_affinity_table 线级登记的羁绊投影:希儿量子行
#: (量子熄火/丢失幸运/免死金牌/极速制冷/以人为本 → 克量子同频+贝洛伯格,
#: 即克含量子/贝洛伯格键的组合条目)、DOT队行(净化身心 → 敌解负面拆
#: DOT 结算,克持续伤害)、万敌行(永久创伤 → 克燃血)、boss 克制登记
#: (深穹智械科技/红绿灯 → 克救世主/燃血)。燃血/救世主两键过渡组合
#: 条目暂无命中(零命中,留供登记更新——boss 行克制键随线级登记同源
#: 维护)。粒度(or-reqs-retirement 3.2):量子/贝键命中含希儿量2/希儿贝2
#: 块的 7 条组合各减一次(双修条「希儿量2+希儿贝2」两边都含、按条目
#: 只计 1 次),其余 3 条组合(仙舟3+DOT2/仙舟3+列车2/DOT2+列车2)上位。
TRANSIT_AFFIX_PENALTY: dict[str, list[str]] = {
    '量子熄火': ['量子同频', '贝洛伯格'],  # 克量子/贝键组合条目(希儿量子行登记)
    '丢失幸运': ['量子同频', '贝洛伯格'],  # 同上
    '免死金牌': ['量子同频', '贝洛伯格'],  # 同上
    '极速制冷': ['量子同频', '贝洛伯格'],  # 同上
    '以人为本': ['量子同频', '贝洛伯格'],  # 同上
    '净化身心': ['持续伤害'],             # 敌解负面拆 DOT 结算(DOT队行登记)
    '永久创伤': ['燃血'],                 # 万敌行登记(过渡组合条目暂无燃血键)
    '深穹智械科技': ['救世主'],            # boss 克制登记(同上,暂零命中)
    '红绿灯': ['救世主', '燃血'],          # boss 克制登记(同上,暂零命中)
}

#: 过渡减分单一档:命中一条克制源对条目档 0 键 → 固定负分,量级与终局
#: 怕档一致(cw_line_scales.FEAR_PENALTY);不设重开级天文数字档。
#: 终局线分的词缀/boss 面不动(线级登记更细,与本表数据同源、粒度分工)。
TRANSIT_AFFIX_PENALTY_SCORE: float = float(FEAR_PENALTY)

#: 过渡候选数(与终局候选数 CANDIDATE_TOP_N 同值复用;kernel 禁
#: import 策略层实现,两处值禁单侧漂移,改值须两处同改)。
#: 策略层消费点 = shop.py 过渡货架资格臂虚拟帧切片(or-reqs-retirement
#: 3.4:虚拟/实机帧同 N 经本常量单一源,禁调用侧复制字面量)。
_TRANSITION_CANDIDATE_TOP_N: int = 3


def transition_entry_of(name: str) -> Comp | None:
    """过渡条目名 → ``TRANSITION_LIBRARY`` 条目;未知名返 None。"""
    for e in TRANSITION_LIBRARY:
        if e.name == name:
            return e
    return None


def transition_member_set(comp: Comp) -> set[str]:
    """过渡组合条目的计分基准集 = 见即买集(单一源,禁消费点自算)。

    combo 展开:查 ``TRANSITION_COMBO_PARTS`` → 两块 ``bond_score_members``
    并集(点名块贡献点名件;羁绊/混合块贡献点名 ∪ 羁绊全体注册成员——
    ``bond_members`` 阵营∪流派口径);并集按角色去重(一名角色跨点名与
    多羁绊阵营只计 1 分)由集合语义天然承载。未知名(防御态,含旧库
    退役条目名)返空集。
    """
    parts = TRANSITION_COMBO_PARTS.get(comp.name)
    if parts is None:
        return set()
    out: set[str] = set()
    for part_name in parts:
        blk = transition_bond_of(part_name)
        if blk is not None:
            out |= bond_score_members(blk)
    return out


def transition_library_buy_now_union() -> frozenset[str]:
    """过渡库全体条目见即买并集(冷启动/空窗回退键域单一源)。

    承接设计 §3 死循环防线:候选槽为空的帧,买面回退目标 = 本并集
    (点名型贡献点名集;羁绊型贡献羁绊全体注册成员;混合型贡献两者
    并集)——替代旧回退带的四体系羁绊成员并集。见即买 → 持有 →
    计分 > 0 → 候选形成 → 方向确立,死循环闭环。
    """
    out: set[str] = set()
    for e in TRANSITION_LIBRARY:
        out |= transition_member_set(e)
    return frozenset(out)


def transition_active_entries(st: object) -> tuple[Comp, ...]:
    """过渡层活跃条目序(保护/囤货/部署圈人/名单消费的条目域单一源)。

    - 过渡锁定(``transition_locked`` 非空)= (锁定条目,)——其他过渡
      候选配件失去成员档,让位序低位逐步舍弃(锁后不换);
    - 未过渡锁定 = 候选槽条目序(槽存条目名;未注册名跳过);
    - 终局锁定帧由调用方判窗(候选槽/过渡锁定态在终局锁定写入点同点
      清空,本函数对空输入自然返回空元组)。
    ``st`` = 策略器状态鸭子类型参数(读 ``transition_candidates`` 槽与
    ``v3_intention.transition_locked``)。
    """
    ist = getattr(st, 'v3_intention', None)
    tl = getattr(ist, 'transition_locked', '') if ist is not None else ''
    if tl:
        e = transition_entry_of(str(tl))
        return (e,) if e is not None else ()
    out: list[Comp] = []
    for name in (getattr(st, 'transition_candidates', None) or ()):
        e = transition_entry_of(str(name))
        if e is not None:
            out.append(e)
    return tuple(out)


def transition_member_union(st: object) -> frozenset[str]:
    """过渡层贡献成员并集(保护名单/买面名单口径单一源):
    活跃条目见即买集的并集。"""
    out: set[str] = set()
    for e in transition_active_entries(st):
        out |= transition_member_set(e)
    return frozenset(out)


def transition_scores(held: frozenset[str] | set[str],
                      sources: tuple[str, ...]) -> list[tuple[str, float]]:
    """过渡组合条目计分与排序(纯函数;or-reqs-retirement 3.2 契约 B):
    持有分(:func:`transition_member_set` 计分成员域 ∩ held 计数)+ 词缀/
    boss 减分面,过滤总分 > 0,按(分数降序, 注册序)返回有序全序列表。

    实机帧(``update_transition_candidates``)与虚拟帧(货架资格臂,详设四)
    各自切片取前 N(纯切片);排序键在函数内单一实现——禁调用侧自排
    (tie-break 分叉 = 虚拟候选序与实机锁定序分叉)。
    """
    order = {e.name: i for i, e in enumerate(TRANSITION_LIBRARY)}
    out: list[tuple[str, float]] = []
    for entry in TRANSITION_LIBRARY:
        score = float(len(transition_member_set(entry) & held))
        keys = set(entry.core_faction_reqs)
        for src in sources:
            hit = TRANSIT_AFFIX_PENALTY.get(src)
            if hit and keys & set(hit):
                score += TRANSIT_AFFIX_PENALTY_SCORE
        if score > 0.0:
            out.append((entry.name, score))
    out.sort(key=lambda ns: (-ns[1], order[ns[0]]))
    return out


def update_transition_candidates(gs: GameState, ist: IntentionState,
                                 st: object = None,
                                 ) -> IntentionState:
    """过渡候选机器驱动(每 game-round 恰一次,就地改 ist 并返回;
    调用位置 = 外层流程方向节拍贵段,窗口守卫 = 未终局锁定帧——
    终局锁定写入即整体退役,位面切换不触发)。

    三面(用户 2026-11-04 裁定:与终局线分同构的统一评分,纯减分制
    无特殊逻辑):

    - **持有分**:条目计分基准集(:func:`transition_member_set` = 两块
      ``bond_score_members`` 并集)∩ 持有(在场 ∪ 备战席)的成员数
      (集合语义按角色去重);开局全 0;
    - **词缀/boss 减分面**:开局简报已观察的克制源
      (``enemy_affixes`` ∪ ``plane_bosses``)命中条目档 0 键
      (:data:`TRANSIT_AFFIX_PENALTY`)→ 每条命中源固定减
      :data:`TRANSIT_AFFIX_PENALTY_SCORE`;简报未观察帧自然不触发
      (fail-closed = 输入缺失时取「不动作」的保守分支);
    - **候选**:计分与排序 = :func:`transition_scores`(单一实现),
      取前 ``_TRANSITION_CANDIDATE_TOP_N`` 写 ``transition_candidates``
      槽(存过渡条目名;写端单一 = 本函数,``st`` 鸭子类型参数缺席
      不写,禁双源)。

    **锁定评估域 = 候选槽内条目**(用户裁定口径「当某个候选的过渡阵容
    达成后」;3.2 组合制:锁定对象 = 组合条目——两羁绊完整组合,单羁绊
    凑出时任何组合条目 fp < 1.0 自然不锁):候选槽内条目
    ``form_progress``(条目, 板面) ≥ 1.0 即锁 ``ist.transition_locked``
    (锁定条目名)——锁后不换、不解、不重评;候选外条目偶然凑齐羁绊
    (板面羁绊计数达标但零成员持有)不锁,计分门控防偶然锁定。
    """
    held = _owned_chars(gs)
    sources = (*(gs.enemy_affixes.value or ()),
                *(b for b in (gs.plane_bosses.value or ()) if b))
    ranked = transition_scores(held, sources)
    names = tuple(name for name, _s in ranked[:_TRANSITION_CANDIDATE_TOP_N])
    if st is not None:
        with contextlib.suppress(Exception):
            st.transition_candidates = names
    if not ist.transition_locked:
        for name in names:
            entry = transition_entry_of(name)
            if entry is not None and form_progress(entry, gs) >= 1.0:
                ist.transition_locked = name
                ist.last_event = f'transition_lock:{name}'
                break
    return ist


def _line_hoard(comp: Comp) -> tuple[set[str], set[str]]:
    """意向线囤货采购集(目标件定义节 class2 口径的落地):

    角色件 = 终局成员集(``comp.members``;替班者已并入成员名单承载)
    ∪ 羁绊成员(档 0 ∪ 档 ≥1
    键阵营下的注册表成员——统一读口 core/bonus_faction_reqs);装备件 =
    derive_key_equips(到人配方投影)。
    """
    chars = set(comp.members)
    factions = set(comp.core_faction_reqs) | set(comp.bonus_faction_reqs)
    if factions:
        for name, c in CHARACTERS.items():
            #  修法2:目标集判定用「阵营 ∪ 流派」全集与档位键
            # 作交集——旧版只查 c.factions,而档位键常含**流派系羁绊**
            # (万敌单C 档 0 燃血=flows、DOT 持续伤害、黄泉减益、击破等),
            # flows 成员(刃/镜流/布洛妮娅 等)被目标集排除 → 终局阵容锁定采购面残
            # ( Ring1:燃血 8 成员 3 名缺位)。泛化修正,非万敌特判
            # (candidates 的 _char_factions 同式全集口径)。
            if (set(c.factions) | set(c.flows)) & factions:
                chars.add(name)
    equips = set(derive_key_equips(comp))
    return chars, equips


# ===== 无目标期囤货缺省(统一让位优先级迭代 3.4 退役注记)=====
# 原状 = P86 无目标期三分支判据(适用范围 = p2plus 无目标帧;活跃域 =
# 位面 2,证明批引理 Z):甲分支(方向化囤货,定理 A)/ 乙分支(枢纽
# 期权,定理 B 族)/ 丙分支(换现保利息,命题 C)。
#
# 退役裁定(总纲 §2.7【拍,按裁决模式推导可翻案】):
# - **甲分支判活路径退役**:未锁无目标帧的囤货方向不再取机器判活方向
#   ——非候选 top3 的方向囤其成员无兑现通道(锁后不换线),与单卡核心
#   囤积/囤货臂同逻辑;K 目标未锁期源切换 = 策略层候选快照三线成员
#   并集 ∪ 配方成员(mandate_v1/shop.py 序 1 义务面装配,与优先级档
#   2/3/4/5/7 名单同源);
# - **乙分支已定退役**:hub 与候选体系重叠(多线复用件 ∈ 候选线并集
#   → 档 2/3/4/5/7 承载买入与保留),通道经 12 号稿「动作并入序 1」后
#   空心化,死链三段全断(hub_option_names/structural_candidate_lines/
#   NoTargetArms.hub_names 随本批删除);
# - **丙分支域随 3.3 换轴消亡**(3.4 修订注:原注「在役判据」已失效):
#   丙分支辖域 = 旧 p2plus 位面带(未锁 P2+ 无目标帧),该带已随
#   comp-structure-unification 3.3 换轴废除(未终局锁定帧过渡层照常
#   活跃、终局锁定帧恒有方向,k_empty_window_fallback 只余 p1_gap/
#   p1_lock_band 两带且构造性非空)——「不囤、金留线上吃息」的合法
#   空集形态不再有到达帧,在役消费面清零。
#
# 数学证明处置(3.4 对照项):甲分支定理 A 证明随判据死迁出
# (p86-proof-batch.md §3.1 删除)、乙分支证明章(定理 B 族/§3.2 资格核)
# 同批删除、丙分支命题 C 与引理 Z/主定理 M 的退役后表述在证明批保留
# (留档口径;丙分支域消亡见上条,不再按在役判据引用)。


def hoard_target_set(gs: GameState, ist: IntentionState,
                     session: StrategySession | None = None,
                     registry: DecisionV2Registry | None = None,
                     visible: set[str] | None = None) -> HoardTarget:
    """锁后效果接口:输出「囤货目标集合」供买侧消费([21]:只改囤货方向,不改板上)。

    - 终局锁定(locked_comp 非空):终局线采购集(现行);
    - **未终局锁定 = 过渡层活跃帧**(换轴:原「位面 1 配方带/位面 2 起
      恒空」位面分带废除,过渡机制生命周期挂钩终局锁定事件)——
      过渡锁定 → 锁定条目采购集(见即买集);未过渡锁定 → **两层候选
      并集**(过渡候选条目并集 ∪ 终局候选三线成员并集,候选快照槽);
    - 两层候选皆空的帧 → 过渡库全体条目见即买并集(§3 死循环防线:
      见即买 → 持有 → 计分 > 0 → 候选形成,闭环)。
    过渡装备随意([20] 装备语义:简易装备随便给,合成件归 final
    key_equips 判定)——过渡支 equip_targets 恒空。
    (weak/demoted_endgame 分带随分支退役移除——phase 值域注释
    IntentionState.phase:weak 随机器停用不可达,demoted_endgame 全
    不可达,分带为不可达死分支非在役判据。)
    """
    if ist.phase == 'locked' and ist.locked_comp:
        comp = get_comp(ist.locked_comp)
        if comp is not None:
            chars, equips = _line_hoard(comp)
            return HoardTarget(frozenset(chars), frozenset(equips),
                               'forced' if ist.forced else 'locked')
    st = strategy_state_of(session) if session is not None else None
    chars: set[str] = set(transition_member_union(st)) if st is not None \
        else set()
    if st is not None:
        # 终局候选三线成员并集(core ∪ shared,与 k_members 名单同口径)
        for name in (getattr(st, 'line_candidates', None) or ()):
            c = get_comp(str(name))
            if c is not None:
                chars |= set(c.members)
    if chars:
        return HoardTarget(frozenset(chars), frozenset(), 'p1_pair')
    # 候选槽为空的回退:过渡库见即买并集(§3)
    return HoardTarget(transition_library_buy_now_union(), frozenset(),
                       'p1_transition')


def k_empty_window_fallback(gs: GameState,
                            ist: IntentionState,
                            session: StrategySession | None = None,
                            registry: DecisionV2Registry | None = None,
                            visible: set[str] | None = None,
                            ) -> tuple[frozenset[str], str]:
    """K 空窗回退单一源(经济冻结批病灶①):现行方向读口
    (``session_scope.direction_comp_of``)为 None 的帧的目标成员集
    分带派生,商店域(shop.py)与准备域(entry.py/decision_payload)
    共用本函数——禁在任一消费域复制兜底逻辑(第二源)。

    返回 (成员集,分带 token):分带 token 供消费域拼遥测计数键
    (shop 侧键名契约 'shop_k_fallback_<token>' 维持历史键名不变)。
    分带语义(换轴改造:旧 p2plus 位面带随「未终局锁定帧过渡层照常
    活跃」废除——终局锁定帧恒有方向〔锁定线〕,本函数不可达):
    - p1_gap:两层候选与过渡候选全空(方向真空)→ hoard 回退
      (过渡库见即买并集;消「K 空→零买入→计分来源永不涨」死锁环);
    - p1_lock_band:过渡候选首位条目见即买集(候选机器同源现读,
      禁双源),派生空 ⇒ 链 hoard 回退兜底。
    session/registry/visible 形参保留 = 旧签名兼容。"""
    st = strategy_state_of(session) if session is not None else None
    entries = transition_active_entries(st) if st is not None else ()
    if entries:
        members = frozenset(transition_member_set(entries[0]))
        return (members or hoard_target_set(
            gs, ist, session=session, registry=registry).char_targets), \
            'p1_lock_band'
    return hoard_target_set(gs, ist, session=session,
                            registry=registry).char_targets, 'p1_gap'


def committed_authority(state: GameState | None,
                        session: StrategySession | None) -> bool:
    """committed(已定型/非双轨期)权威判定(方向层单一派生源)。

    - **权威序**(任一成立即 True;候选-锁定制口径,12 号篇 §2):
      ① ``strategy_state.target_comp`` 非空——锁定线槽非空(定型语义 =
      锁定线非空,12 号篇 §2 判定源:P1 硬规则锁定与
      P2 时点兜底统一承载。原「位面 ≥ 2 恒定型」支已停用——P2 时点
      兜底锁定替代原 P2 恒定型,行为差申报:P2 入口至兜底锁帧之间的
      短窗 committed=False〔双轨期口径〕,锁定时点与原接近);
      ② ``ist.transition_locked`` 非空——过渡锁定已立(锁定条目名,
      序②替代口径:原读配方对 p1_pair,语义连续 = P1 方向已定型,
      committed 全部消费面零改动)。
      **缺供给帧 = 保守侧 False**(=双轨=攒息):策略状态/ist 不可得或
      字段缺失时**禁止**缺省 True——True=已定型=激进侧,攒息门/双轨
      买门全开(供给点清单 D2:拔掉供给探针下必须落保守侧,变异测试钉住)。
    - 消费契约:全部消费点经本函数或 ``decision_v2.prep_brain
      .committed_from``(唯一读端,内部委托本函数)取值。
    - **state 形态 = 状态容器单例**(波3 切换;禁新消费点再喂旧帧或手造
      鸭子镜像)。
    """
    st = strategy_state_of(session) if session is not None else None
    if st is not None and getattr(st, 'target_comp', None) is not None:
        return True
    ist = getattr(st, 'v3_intention', None) if st is not None else None
    return bool(getattr(ist, 'transition_locked', '') or '') \
        if ist is not None else False


def committed_from(session: StrategySession,
                   state: GameState | None = None) -> bool:
    """committed(已定型/非双轨期)唯一合法读端(R1,蓝图 §4.3;
    装备环境/穿戴计划等 kernel 消费面经它取值(体内仅委托
    本模块 ``committed_authority``,kernel 内自洽)。

    - 有现读 state(状态容器单例)→ 直取权威派生;
    - 无现读 state 的调用面:plane 取 session 状态容器单例(game_state_of),
      也不可得时仅凭 ist 判定(缺供给 = 保守 False,同 D2)。

    grep 守卫「session 侧双轨字段直读点归零(本函数之外)」;
    变异测试:拔掉意向供给(ist=None 且 plane<2)必须落 False 保守侧
    (穿透测试=test_cw_session_separation 的 committed_authority 直接校验
    + test_intention 交叉核对帧)。
    decision_v2.prep_brain 本名保留 import 重定向,消费方调用零改。
    """
    if state is not None:
        return committed_authority(state, session)
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of,
    )
    return committed_authority(game_state_of(session), session)


def locked_buy_scope(ist: IntentionState | None,
                     transition_candidates: tuple[str, ...] = (),
                     ) -> frozenset[str] | None:
    """锁定帧买侧目标约束基准。

    opportunistic/bond_fallback 买通道「目标/非目标」判定输入 =
    过渡层成员并集(槽语义改造:``transition_candidates`` 槽存过渡
    条目名,经 :func:`transition_member_set` 展开;过渡锁定 = 锁定
    条目成员,未过渡锁定 = 候选条目并集)∪ ``locked_comp`` 采购集;
    两者皆空(空窗/降格终局)→ None(无锁定帧,不约束——[31]① 空窗期
    见即买并集是方向,不存在「非目标件」)。

    - 过渡支 = **候选并集**(候选非空即约束——有倾向即约束机会买,
      显式申报;``transition_candidates`` 参数缺省 () = 无候选供给,
      过渡锁定态经 ist 读,候选不经 ist 传递〔槽在策略器状态,写端 =
      候选机器重算〕,接入调用消费方传槽值,禁现算第二源);
    - 终局锁定帧 = ``_line_hoard(comp)`` 角色采购集(终局锁定时过渡层
      已退役清空,过渡支恒空——防御双保险);
    - weak(撤销后去向=跨线骨架)/demoted_endgame 不覆盖:方向已撤或已
      降格,约束基准不存在(弱意向期的跨线骨架囤货本身不受本约束覆盖)。
    """
    if ist is None:
        return None
    scope: set[str] = set()
    if getattr(ist, 'transition_locked', ''):
        e = transition_entry_of(str(ist.transition_locked))
        if e is not None:
            scope |= transition_member_set(e)
    for name in (transition_candidates or ()):
        e = transition_entry_of(str(name))
        if e is not None:
            scope |= transition_member_set(e)
    if ist.phase == 'locked' and ist.locked_comp:
        comp = get_comp(ist.locked_comp)
        if comp is not None:
            chars, _equips = _line_hoard(comp)
            scope |= chars
    return frozenset(scope) if scope else None


def locked_buy_membership(ist: IntentionState | None,
                          cap_hold: int | None = None,
                          ) -> frozenset[str] | None:
    """锁定帧(locked_comp 非空)买侧 line membership 的正典口径
    (消费域 = mandate_v1 商店线买入判定链:买入义务集 + 拒因遥测;
    卖免面/刷新账不覆盖,见消费域的买面/卖免面拆分注释)。

    双源断裂机制:锁定帧的买入 membership 旧按
    ``predicates.line_members(target_comp)``(comp core∪shared)判,而
    终局阵容锁定语义的采购集权威 = ``_line_hoard``(含档 0∪档 ≥1
    档位键的阵营∪流派全集成员,修法2 同口径)——实机对局
    g_20260905_035710 锁「列车同行」后,同阵营成员(开拓者·欢愉/
    丹恒·饮月,非该 comp core∪shared)被判 ``non_line``、M2 骨架义务
    买入被跳过,锁定帧自相矛盾(M2「终局阵容锁定成员照买」,审查定性 = 实现
    断裂非设计缺口)。修复 = 锁定帧买入判定统一消费本函数,购买侧与
    锁定侧同源。

    集合构成 = 过渡锁定条目成员(若设;终局锁定帧过渡层已退役,恒空
    ——防御位)+ ``locked_comp`` 采购集(槽语义改造:原 ``p1_pair``
    直读 + ``_pair_members`` 展开改为读过渡层状态——锁定条目,与
    scope 族同源);故本函数与 ``locked_buy_scope`` 的差异随终局锁定
    帧过渡支恒空而收敛(保留两函数形态,消费域分层语义不变)。
    **M2 义务面 = 锁局承诺面**(12 号篇 §4):与 scope(机会买约束面)
    刻意分层。

    **容量可行截断**:``cap_hold`` 非 None 且
    |B| > cap_hold 时返回截断义务集 B'——序 = core∪shared ≻ (过渡层
    成员 ∪ 其余 hoard) 同级,级内 cost 升序、注册表声明序 tie-break
    (``_obligation_rank``)。结构依据 = 义务完成金流成本:低费义务先
    闭合(P41②/P76 甲 1★ 全额退净金 0 的可逆性不变量,低费成员往返
    动作成本最低),零自由参数。缺员面 missing(B') 可清空 ⇒ M2 终止
    条件恢复(停摆不动点解除);被截成员退出 M2 义务基座,
    其 M4/部署面保护必要性随之消失(义务基座 = M2 会重买的集合)。
    ``cap_hold=None`` = 宽集(兼容缺省,零漂移;容量不可得帧的
    fail-closed 方向 = 保宽,截断是收紧面不盲收)。

    触发条件 = ``locked_comp`` 非空(终局阵容锁定状态已建立)。未锁帧
    (过渡层活跃帧 locked_comp 恒空;空窗/weak/降格)→ 返回 None,
    消费方维持既有 ``line_members(target_comp)`` 口径——无终局锁态
    行为零变化的边界基准。
    """
    if ist is None or not getattr(ist, 'locked_comp', ''):
        return None
    scope: set[str] = set()
    if getattr(ist, 'transition_locked', ''):
        e = transition_entry_of(str(ist.transition_locked))
        if e is not None:
            scope |= transition_member_set(e)
    comp = get_comp(ist.locked_comp)
    core_shared: set[str] = set()
    if comp is not None:
        chars, _equips = _line_hoard(comp)
        scope |= chars
        core_shared = set(comp.members)
    if not scope:
        return None
    if cap_hold is not None and len(scope) > cap_hold:
        return frozenset(_obligation_truncate(scope, core_shared, cap_hold))
    return frozenset(scope)


def _obligation_rank(names: set[str] | frozenset[str]) -> list[str]:
    """截断级内序:cost 升序,注册表声明序
    tie-break。确定性关键:候选序从注册表声明序出发(迭代 CHARACTERS
    过滤),稳定排序保声明序——从 set 迭代会因哈希序使同费 tie-break
    跨进程不确定(禁)。注册表外残名(识别占位类)排末尾(名序稳定),
    不参与费率比较。"""
    known = sorted(
        (n for n in CHARACTERS if n in names),
        key=lambda n: int(CHARACTERS[n].cost or 0))
    return known + sorted(n for n in names if n not in CHARACTERS)


def _obligation_truncate(scope: set[str], core_shared: set[str],
                         cap_hold: int) -> list[str]:
    """容量可行截断:core∪shared 优先全保
    (级内超容时按级内序自截),余量按级内序补 (p1_pair ∪ 其余 hoard)。

    前提:core_shared ⊆ scope(``_line_hoard`` chars 含 core∪shared 构造
    保证)。级内序 = ``_obligation_rank``(cost 升序,声明序 tie-break)。
    """
    kept_core = _obligation_rank(core_shared)[:cap_hold]
    rest_budget = cap_hold - len(kept_core)
    if rest_budget <= 0:
        return kept_core
    rest_rank = _obligation_rank(scope - core_shared)
    return kept_core + rest_rank[:rest_budget]


def locked_buy_cap_hold(state: GameState | None) -> int | None:
    """容量可行截断的容量上界单源。

    = ``BENCH_CAPACITY + max_units(level)``(现读;lv8 = 17 实用持有
    容量,旧固定分母 BENCH_CAPACITY+DEPLOYED_CAPACITY=19 高估,|B|=18
    已不可达而不告警)。缺读 fail-closed 方向 = 返回 None ⇒ 消费方保宽
    (现行为,零漂移端)——容量不可得帧不做截断收紧。

    state 形态 = 状态容器单型(读口 = level_of/max_units_of;None = 缺读,
    谓词弃权路径)。
    """
    if state is None:
        return None
    level = level_of(state)
    if level <= 0:
        return None
    try:
        mu = int(max_units_of(state))
    except Exception:   # noqa: BLE001  容量派生缺供给 = 保宽
        return None
    if mu <= 0:
        return None
    return BENCH_CAPACITY + mu


# (锁定线配方底线门豁免 locked_line_recipe_floor_conflict 已随部署统一批
#  丁丁批纳入统一管理删除:配方底线门(recipe_floor_holds/RECIPE_FLOOR_*)随七桶
#  选人族退役——选人 = 统一部署搜索定型,「列车 core 不被补部署绕回上板」
#  的底线语义由搜索评分承载,unified-deploy-order §2/§4。)


def locked_faction_scope(ist: IntentionState | None,
                         transition_candidates: tuple[str, ...] = (),
                         ) -> frozenset[str] | None:
    """锁定帧的体系(羁绊键)集(evolve 提案/部署围栏消费)。

    与 ``locked_buy_scope`` 同判据的**阵营口径**版本(off-lock
    evolve 提案的 target_factions 不含锁定 faction → 锁定目标件被
    execute_replacement 划进 old_line 整档解除——约束需要的是体系键不是
    件名):

    - 过渡支 = **过渡层条目的羁绊键**(槽语义改造:``transition_candidates``
      槽存过渡条目名,取条目 ``core_faction_reqs`` 键集;组合条目档 0
      键 = 两块羁绊键,希儿系组合的量/贝键天然在档;过渡锁定 = 锁定条目键,
      未过渡锁定 = 候选条目并集;参数缺省 () = 无候选供给);
    - 终局锁定帧 = ``locked_comp`` 主/副档键
      (``core_faction_reqs`` ∪ ``bonus_faction_reqs``,与 ``_line_hoard`` 档位键同式;
      终局锁定时过渡层已退役清空,过渡支恒空——防御双保险);
    - 两者皆空(空窗/降格终局)→ None(无锁定帧,不约束——[31]①
      空窗期见即买并集是方向,不存在「off-lock 提案」)。
    """
    if ist is None:
        return None
    keys: set[str] = set()
    if getattr(ist, 'transition_locked', ''):
        e = transition_entry_of(str(ist.transition_locked))
        if e is not None:
            keys |= set(e.core_faction_reqs)
    for name in (transition_candidates or ()):
        e = transition_entry_of(str(name))
        if e is not None:
            keys |= set(e.core_faction_reqs)
    if ist.phase == 'locked' and ist.locked_comp:
        comp = get_comp(ist.locked_comp)
        if comp is not None:
            keys |= set(comp.core_faction_reqs) | set(comp.bonus_faction_reqs)
    return frozenset(keys) if keys else None


