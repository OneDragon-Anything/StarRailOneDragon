"""货币战争 · 方向载体模块(P1 配方对链 + 囤货/回退接口;纯逻辑,不碰游戏)。

终局线选择归策略层候选-锁定制(mandate_v1.session_scope/line_select:
硬规则查表 + 时点兜底,锁定后不换线,防摇摆由结构承载非滞回参数,
12 号篇 §1);原阵容锁定状态机(信号分层终局阵容锁定/撤销出口①②③/P2 移交
强锁/P3 强锁/降格终局)不存于本模块。本模块保留三族:

- **P1 配方对链**(:func:`update_p1_recipe`/``p1_pair`` 族):过渡
  体系对候选机器(候选重算/门控候选首位/双体系对 form_ok 冻结域/
  超窗/退场)——配方物化链保留项(M5 开局面数据源),位面适用范围由
  调用侧(flow)以窗口谓词承载;
- **囤货与回退接口**(:func:`hoard_target_set`/``k_empty_window_fallback``/
  ``locked_buy_*`` 族):买侧与部署侧的现行读面;``locked_comp``/``phase``
  改为锁定线槽派生缓存(写端 = mandate_v1.session_scope,锁定 ⟺
  target_comp 非空)。P86 无目标期三分支判据的甲/乙臂已随统一让位
  优先级迭代 3.4 退役(K 目标未锁期源切换 = 策略层候选快照三线并集
  ∪ 配方成员;丙分支保利息缺省保留),``no_target_arms`` 判据件
  整删——退役依据见本模块「无目标期囤货缺省」节注;
- **定型权威**(:func:`committed_authority`/:func:`committed_from`):
  规则④「位面 ≥ 2 恒定型」支已停用(P2 时点兜底锁定替代;§1.6 行为
  差申报:P2 入口至兜底锁帧的短窗 = 双轨期口径)。

**教义边界(已退役口述登记簿)**:[21] final 件「买而不上」→ 本模块
只改囤货方向(输出「囤货目标集合」供买侧消费),不改板上、不产出
任何上场/换人动作;[23] 终局线由锁定承载(锁定后不换线)。
"""
from __future__ import annotations

import contextlib
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    refresh_prob,
)
from sr_od.application.currency_war.kernel.cw_comps import (
    COMP_LIBRARY,
    SEELE_CARRY_CHAR,
    SEELE_OR_REQS,
    Comp,
    derive_key_equips,
    form_progress,
    get_comp,
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    TRANSITION_TRAITS,
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
from sr_od.application.currency_war.kernel.cw_line_switch import (
    e_rounds,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    PLANE_NODE_TABLES,
)
from sr_od.application.currency_war.kernel.cw_plugins import (
    cross_line_skeleton as _cross_line_skeleton,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
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

# 无目标期帧(p2plus 带)囤货方向缺省 = 丙分支保利息(空集,不囤)。
# P86 三分支判据的甲臂(方向化囤货)与乙臂(枢纽期权)已随统一让位
# 优先级迭代 3.4 退役(总纲 §2.7【拍】:K 目标未锁期源切换 = 策略层
# 候选快照三线成员并集 ∪ 配方成员,买面与优先级面统一;「机器判活方向
# ∉ 候选 top3」的囤货兑现通道随锁后不换线消亡——与单卡核心囤积同逻辑)。
# 证明处置:p86-proof-batch.md 甲分支定理 A 证明随判据死迁出(3.4 对
# 照项结论),乙分支证明章同批删除,丙分支命题 C 在役保留。

# 跨线骨架件(strategy_v4「目标件」定义节 class3)。弱意向态只囤这批
# (点0:撤销后去向——只囤跨线骨架件)。
# **派生**自 ``cw_plugins.W16_MAJORITY_LINES``
# (≥3 线过半 8 张 + 恰 2 家族过半且非线级 carry 的边界 2 张);
# 派生规则与 ``cw_plugins`` 内同源裁决口径见 ``cw_plugins.cross_line_skeleton``。
# 快照测试校验派生结果(不等 = 数据错)。
CROSS_LINE_SKELETON: tuple[str, ...] = _cross_line_skeleton()


@dataclass
class IntentionState:
    """方向状态载体(P1 配方对链 + kernel 派生缓存;意向层机器
    本体停用后的保留形态——阵容锁定状态机〔信号终局阵容锁定/撤销出口/P2 移交/
    P3 强锁/降格终局〕已删除,终局线锁定归策略层候选-锁定制:
    ``locked_comp``/``phase`` 改为锁定线槽派生缓存,写端 =
    mandate_v1.session_scope〔同步于 refresh/锁定动作〕;``p1_pair`` 族
    = 配方对物化链产物〔保留项〕。机器时代字段(``weak_comp``/
    ``lock_layer``/``evicted``/``demoted_endgame`` 等)无写端恒缺省,
    读端按保守缺省语义消费〔evicted=∅ 恒空集/demoted=False〕)。"""

    phase: str = 'unlocked'            # 'unlocked' | 'locked'(weak 随机器停用不可达;派生缓存,写端 = session_scope)
    locked_comp: str = ''              # 锁定线(COMP_LIBRARY 套名)
    p1_pair: tuple[str, ...] = ()      # P1 配方锁:体系对(过渡体系键;P2+ 恒空)
    """**P1 锁定目标数据形态(显式可读,约束基准契约)**:

    - 读口 = ``strategy_state_of(session).v3_intention.p1_pair``——
      **门控候选首位**(12 号篇 §3:候选首位对级
      支持度 ≥ ``P1_PAIR_LOCK_MIN_SUPPORT`` 才写,否则空对;冻结帧钉
      frozen_pair)的派生态:四体系键的一或二元组(1 元对 = 门控首位
      恰为单体系对的帧——单席满/超满而第二体系未达门槛;渐进第二席
      职能由候选并集承载,不再产渐进 2 元对),按
      ``_P1_PAIR_PREF`` 序规整,非空即「P1 锁定帧目标=该体系对」;
      空元组=空窗期(未锁);P2+ 恒空(P2+ 锁定目标=``locked_comp``)。
    - 体系键域与判据单一源:三羁绊键=``TRANSITION_TRAITS``
      (仙舟/列车同行/持续伤害),希儿系=``SEELE_SYSTEM`` 哨兵键
      (与 ``cw_battle_calib._engines_count`` 同口径)。
    - 遥测:``serialize_intention`` 字段全量序列化自动
      携带(不隐式——单帧测试断言 p1_pair 落 decisions 行)。
    - **后续「通道约束批」(迁移期补充判读:决策通道两面孔按锁定目标约束/
      末轮禁用)以本字段为约束基准**——opportunistic/bond_fallback 通道
      的「目标/非目标」判定输入 = 本字段(非空时)∪ locked_comp
      (scope 族口径 = 过渡候选并集,见 ``locked_buy_scope``;本字段
      的 committed 判定语义见 ``committed_authority`` 序②等价论证)。
    """
    lock_layer: int = 0                # 锁定时信号层(撤销出口②的「更高层级」基准)
    lock_plane: int = 0                # 锁定时机(遥测)
    lock_round: int = 0
    transition_pair: tuple[str, ...] = ()  # ①锁局过渡对副方向
    """**①资格锁定局的过渡对保护副方向(约束基准契约)**:

    - **无写端恒空**(①资格锁定的状态机写点随意向层机器本体停用
      消亡;读端 ``locked_buy_scope``/``locked_faction_scope``/
      ``_update_pair_drought`` 按防御缺省 () 消费);字段保留为
      序列化兼容与历史契约描述。
    - 历史契约(写点在位时的语义,git 历史可溯):非空 ⟺
      plane==1 ∧ phase=='locked';派生口径与 ``p1_pair`` 同族
      (体系对,``_P1_PAIR_PREF`` 序规整)——``p1_pair`` 是配方锁局
      的**锁定产物**,本字段是①锁局的**受保护副方向**;对件享二级
      囤货([22]④)与成型优先([13] P1 验收仍是体系对)。
    - 遥测:``serialize_intention`` 字段全量序列化自动携带。
    """
    forced: bool = False               # 强制终局阵容锁定产生(P3 入口)
    weak_comp: str = ''                # 降级来源线(遥测;弱意向不指向具体线)
    demoted_endgame: bool = False      # 降格终局标记(全不可达;「赢不了就少输」)
    evicted: set[str] = field(default_factory=set)        # 冻结超限移出候选集的线
    pair_evicted: set[str] = field(default_factory=set)
    """R3 断供驱逐集(配方对域;**已退役恒空**:断供驱逐分支
    随未证阈值退役,本字段仅留序列化兼容与派生 exclude 参数占位)。"""
    pair_drought: dict[str, int] = field(default_factory=dict)
    """体系级断供计数器(体系键 → 连续无新件在店轮数;成员在店即清零,
    无商店语境轮冻结)。仅遥测,不再触发驱逐。"""
    shop_supply_streak: dict[str, int] = field(default_factory=dict)
    """体系级在店供给计数器(体系键 → 连续在店轮数;不在店清零,无商店
    语境轮冻结)。仅遥测。
    serialize_intention 全量序列化自动携带。"""
    p1_pair_frozen_obs: tuple[str, ...] = ()
    """P1 配方对观测快照(锁线断头 P2 定向通道设计稿 §2.1/§6,纯观测件):
    plane==1 且派生 pair 非空时随帧覆写为最新非空值——P2 退场后仍可读
    「退场前的冻结副本」,作 ``promote_candidates``(G8 观测载体)的输入。

    - **坐标系/取值时机**:值域 = ``p1_pair`` 同域四体系键一或二元组;
      生成期快照(最近一个非空 P1 派生帧),不随 P2 资产变化刷新;
      跨局随 IntentionState 新建自然清零。
    - **只承归因不作行为**:任何判定/发射逻辑禁消费本字段(行为交付面
      = P65 直证批另行立项,届时按设计稿改 ``p1_pair`` 退场语义,不改
      本快照);grep 守卫钉住唯一写入端与本函数族唯一读端。"""

    p1_pair_frozen: bool = False
    """命题 1b 冻结闩 F:True=方向
    冻结,重算被抑制(冻结的是方向不是板面,买入/部署继续服务
    ``p1_pair_frozen_pair``)。置位 = 事件闩:F=False ∧ 非封印帧 ∧
    **冻结评估域**(全候选空间中对级支持度 ≥1.0 的**双体系对**,扫描序
    = 候选排序键((支持度, 声明序) 降序)不截断——超满对先于恰满对;
    12 号篇 §3 冻结语义)中首个 ``form_progress >= 1.0``
    (板面成型);**单体系对不进冻结域**(「单体系锁停」死锁结构性
    免疫——旧超窗冻结单对形态消亡);空域/空对永不置位;
    fp 回落不自动清位。解冻闭集(p1_pair 域恰两项)= {面③超窗出口,
    位面末(exit_p1)}——闭集之外零解冻事件。与
    ``p1_pair_frozen_obs``(上方,纯观测快照)零行为交互,两字段独立。"""
    p1_pair_frozen_pair: tuple[str, ...] = ()
    """冻结方向身份(F=True 时的在任对;值域 = ``p1_pair`` 同域四体系键
    **二元组**——冻结域 = 双体系对,新制下恒 2 元)。不变式
    **F=True ⟹ 本字段非空**:置位需冻结域 form_ok 首个存在 +
    「外部清除⟹F 同帧归 0」二选一裁决(拒绝为空对新造
    比较语义)⟹ 超窗出口永不对空对求值,「comp 锁后方向真空直到位面末」
    的孤儿态从构造上不可达。"""
    p1_pair_refreeze_hold: tuple[str, ...] = ()
    """超窗解冻后的再闩封印(空 = 无封印)。出口解冻的对在「**门控候选
    首位** == 封印对 ∧ fp 未见回落(<1.0)」期间禁止再闩——防超窗在任对
    陷入「出口→解冻→保持→复位→再触发」逐帧空转环(清除后
    段)。解封两路:门控首位置出不同对(合法换向,新方向自由闩)/
    fp 回落(方向丢失,此后再达成 = 新 form_ok 事件,允许再闩)。"""

    last_event: str = ''               # 最近一次状态转移(判读/遥测锚点)
    revoke_evidence: dict[str, object] = field(default_factory=dict)
    """撤销出口①开窗的证据字段快照(实机判读锚点,设计 R3.5「无证据
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
    - ``equip_targets``:装备材料件(意向线 equip_assign 派生,剔除 equip_taboos);
    - ``mode``:'locked' | 'forced' | 'weak' | 'fallback' | 'demoted_endgame'
      | 'p1_pair' | 'p1_transition'(买侧按 mode 区分囤货语义:意向件照囤/
      插件台阶/兜底方向/降格满配骨架/配方方向)。
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

    取 ``plaza_carry``(实战聚类 carry,交叉核对基准)且在 core_chars 内者;否则
    core_chars 首位。单一核心保证 miss 计数良定义(避免花火/瓦尔特类共享件
    在多线间产生噪声信号)。
    """
    if comp.plaza_carry and comp.plaza_carry in comp.core_chars:
        return comp.plaza_carry
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


# ===== P1 终局阵容锁定资格门=====
# 三门行为无条件化(后治理蓝图):P1 终局线资格门/配方锁/过渡对
# 三门的 sim A/B 已终裁,无开关;A/B 基线分支由 git
# 冻结快照构造(回退 = git revert)。

_ENGINE_BOND_KEYS: frozenset[str] = frozenset(b for b, _t in TRANSITION_TRAITS)
"""三羁绊体系键(仙舟/列车同行/持续伤害;派生自 cw_deploy_logic.TRANSITION_TRAITS
单一源,与 scoring/cw_sim/deploy_logic 的体系判定同源)。希儿系=单卡二元判定
不占羁绊键(与 scoring '希儿系' 哨兵同口径)。"""


#: 希儿系体系键(单卡二元判定,不占羁绊键;与 cw_battle_calib._engines_count
#: 的希儿系哨兵同口径)。
# ⚠️ 权威副本 = knowledge/cw_line_facts.SEELE_SYSTEM;本副本仅为 sim/旧判据
# 未迁消费点保留(迁移完成后随文件删除);勿新增消费。
SEELE_SYSTEM: str = '希儿系'

#: P1 配方对平手序 = 注册表声明序(TRANSITION_TRAITS 声明序 + 希儿系垫底
#: 单卡系)。旧「激活占比降序(列车 .360 > DOT .329 > 仙舟 .292,transition_
#: combos 数据附录)」社区统计平手序已停用 2026-09-04(「未证即停用」裁定;
#: 平手 tiebreak 仅定确定性,不载经验排序)。
_P1_PAIR_PREF: tuple[str, ...] = tuple(
    b for b, _t in TRANSITION_TRAITS) + (SEELE_SYSTEM,)

# ===== 希儿系形态端口(OR 分支 + carry)=====
# 适用范围切分(与支持度端口 ``_seele_system_support`` 机械可检验,
# 禁互相渗透成双源):形态端口读**板面羁绊计数**(gs.board,经
# form_progress),支持度端口读**owned 去重成员计数**(bench∪deployed);
# 本文件 form 链禁出现 _seele_system_support 消费。
# 常量真源 = cw_comps.SEELE_OR_REQS/SEELE_CARRY_CHAR(
# 0621-seele-static-form-or-fold 单一源归位:注册表数据层——静态套
# 条目 import 期消费,留本文件会反向 import 成环;本模块经顶部
# cw_comps 导入消费,禁再写本地第二份)。档位出处
# (transition_combos.md:27/103 + combo_methodology.md:133/143)与
# 量2/量3 挂确认注记随真源常量注释,此处不复制。

P1_PAIR_LOCK_MIN_SUPPORT: float = 1.0
"""配方对锁定门槛(门槛值不变):最高体系支持度 ≥ 此值才锁。

【注】游戏定义激活当量:三羁绊系支持度 = 该体系羁绊计数 / 体系档
(TRANSITION_TRAITS),1.0 = 体系羁绊满员;希儿系支持度 = 分级公式
(``_seele_system_support`` 单一源):希儿 + 任 1 去重放大器 = 1.0
(锁线证据 = 文档「引擎达成那一刻切希儿直通模式」的开线点),希儿
单卡 = 0.5(开线候选,不再即锁——文档「希儿到手 ≠ 希儿线成型」,
docs/game/currency_war/research/combo_methodology.md:138)。旧 0.5
门槛与希儿系 0.6+0.2+0.2 放大器权重的退役裁定不变;
被支持度降档取代的仅是其 post-state「希儿系 = 在手二元
1.0/0.0」条款——分级公式属重新推导(每一项来自文档档位结构
transition_combos.md:27 与注册表计数),非旧手定权重复活。保守方向:锁线门槛
更严 → P1 空窗期(囤跨线骨架件)更长,方向承诺不提前。"""


# ===== ①锁局过渡对保护副方向=====
# 诊断来源:判读节——inject on 口径 strict_mal 0.20 vs off 0.05 的
# 差值 15 局全部来自①资格通道:注入信号 r1 锁终局阵容,其采购集把囤货
# 方向从过渡引擎引开(engines2_by_r6 0.27→0.15)+ evolve 按阵容线换档
# 拆过渡体系(S2 挤出 19/20 mal 局)=主灶在①通道的残留。


def _owned_chars(gs: GameState) -> set[str]:
    """已到手角色名(bench+deployed;不含 shop 可见——[23] 锁定由
    贯穿件=到手,店里出现过不构成方向承诺)。"""
    front, back = deployed_rows_of(gs)
    return {u.char_id for u in (*front, *back, *bench_units_of(gs))
            if u is not None and u.char_id}


def _seele_system_support(owned: set[str]) -> float:
    """希儿系支持度分级公式(单一源;三消费面经 ``_p1_system_support`` 共用)。

        support = 0                               若 希儿 ∉ 手上
                = min(1, max(c_量/2, c_贝/2))     若 希儿 ∈ 手上

    【注】每一项均为文档/注册表定义量,零拟合常数(F5 裁决=去重成员计数):
    - c_量 / c_贝 = ``owned``(bench∪deployed 成员名去重集)中带
      量子同频 / 贝洛伯格标签的成员数——**去重成员计数**(同名多副本
      计 1)= 羁绊激活语义,与 form 分支(羁绊按去重成员激活)同语义,
      对合成零扰动(2★ = 3 副本合并产物,去重前后成员数不变);
    - ÷2 = 文档 OR 分支档位(量≥2 ∨ 贝≥2,docs/game/currency_war/
      research/transition_combos.md:27);max = 文档 OR 结构(凑到任一
      分支即满,取最好分支非均值);
    - 登记的待办指针(C1,前批遗留):量分支档位存在文档内部张力——本式 ÷2 取
      量≥2 主口径(定义表行),combo_methodology.md:133/170 写量 3;
      张力挂玩家确认(挂确认指针),确认改档落
      ``SEELE_OR_REQS``(形态端口单一源)并同步回改本式分母,
      禁两端口各自为政;
    - 登记的待办指针(C1,P86 攻击 r1 中低1 并入):去重计数的未覆盖形态 =
      同名同 1★ 副本对(实证:绯英×2/花火×2 同场合法态,合成进度
      2/3)——去重前后成员数不变,支持度读数零扰动,但「副本进度是否
      应计支持度」属口径确认项,并入 放大器计数口径登记的待办
      (玩家确认同门),确认前维持去重口径(零行为变更);
    - 希儿缺席恒 0:量/贝放大器不能独立当过渡(含希儿 28 帖无一缺希儿
      独立成线,transition_combos.md:27);
    - 希儿单卡(任意星级)= 0.5 不是人为定为值:注册表基准 = 希儿自身双标签
      (CHARACTERS['希儿'].factions=('贝洛伯格'), flows=('量子同频'),
      data/cw_chars.py「希儿」行),她同时计入两池各 1,在文档档位结构
      下直接导出 max(1/2,1/2)=0.5——单卡 0.5 是推导后果。

    坐标系声明(同文件两套计数口径并存,禁默默统一;F5 显式登记,
    分歧裁决权在对表裁定):本公式用**去重成员
    计数**(羁绊激活证据);同文件 ``_asset_thickness`` 及配修甲
    后续同族落点用**星级当量**原语(每副本按 star 计,Σ3^(star−1) 族,
    治「合成被记为倒退」的通用排序面)。两者适用范围不同——支持度回答
    「羁绊激活了几成」,星级当量回答「投入叠了多少」;任一侧禁私自换用
    另一原语。同函数内三羁绊系分支沿用逐副本羁绊计数(与 cw_battle_calib
    ._engines_count 同式)而希儿系两条分支用去重计数,是设计决定非疏漏。
    """
    if '希儿' not in owned:
        return 0.0
    c_quantum = 0
    c_belobog = 0
    for name in owned:
        ch = CHARACTERS.get(name)
        if ch is None:
            continue
        if '量子同频' in ch.flows:
            c_quantum += 1
        if '贝洛伯格' in ch.factions:
            c_belobog += 1
    return min(1.0, max(c_quantum / 2, c_belobog / 2))


def _p1_system_support(gs: GameState) -> dict[str, float]:
    """四过渡体系的手上资产支持度(bench+deployed;注册表阵营∪流派口径,
    与 ``cw_battle_calib._engines_count`` 同式——多阵营件(桑博=贝+DOT)各系并计)。

    三羁绊系 = 羁绊计数 / 体系档(仙舟3/列车2/DOT2,TRANSITION_TRAITS
    单一源;逐副本计数,与希儿系分支的去重口径分立,坐标系声明见
    ``_seele_system_support``);希儿系 = 分级公式
    (``_seele_system_support`` 单一源,去重成员计数:希儿单卡 0.5
    开线候选、希儿+任 1 去重放大器满支持,推导链见其 docstring)。
    旧「希儿在手二元 1.0」post-state 条款被支持度降档取代
    (0.6+0.2+0.2 手定权重已停用,本式为文档口径
    重推非旧值复活)。
    """
    counts: dict[str, int] = {}
    front, back = deployed_rows_of(gs)
    for u in (*front, *back, *bench_units_of(gs)):
        cid = getattr(u, 'char_id', '') or ''
        if not cid:
            continue   # 未识别/占位件:无注册表身份可判,不计(未知名 '?' 口径)
        ch = CHARACTERS.get(cid)
        if ch is None:
            continue
        for f in set(ch.factions) | set(ch.flows):
            counts[f] = counts.get(f, 0) + 1
    sup = {b: counts.get(b, 0) / t for b, t in TRANSITION_TRAITS}
    # 去重成员集(_owned_chars 已是名字集)直喂分级公式;禁在此换回
    # 逐副本计数(坐标系声明见 _seele_system_support docstring)。
    sup[SEELE_SYSTEM] = _seele_system_support(_owned_chars(gs))
    return sup


def p1_gap_window(gs: GameState) -> bool:
    """P1 空窗期判定(只读):bench∪deployed 四体系最高支持度 <
    ``P1_PAIR_LOCK_MIN_SUPPORT``。

    消费位=cw4 商店线方向 pass 的 K 空窗回退门(2026-09-03 第三病灶
    裁定,SEEDS_EMPTY_LEDGER_DIAG §4 第一案):``target_comp`` 值域
    全集含 None,空窗期 K 投影回退 ``hoard_target_set``(本模块,
    单一源)。判定数学与 ``update_p1_recipe`` 的门控同源(同一
    ``_p1_system_support`` + 同一门槛常数,禁另造支持度算式)。
    边界:空板面恒 True(0<0.5);P2+ 调用面约定不覆盖(空窗系 P1 概念)。
    """
    sup = _p1_system_support(gs)
    return max(sup.values(), default=0.0) < P1_PAIR_LOCK_MIN_SUPPORT


#: 过渡候选数(【拍】2026-11-01 用户裁定:与终局候选数同值复用——值单一源 =
#: strategies/impl/mandate_v1/
#: line_select.CANDIDATE_TOP_N;kernel 禁 import impl(依赖矩阵),
#: 两处值禁单侧漂移,改值须两处同改)。
_P1_PAIR_CANDIDATE_TOP_N: int = 3


def _p1_pair_support(pair: tuple[str, ...],
                     sup: dict[str, float]) -> float:
    """对级支持度 = min(各席席级支持度)(木桶语义);单体系对 = 该席席级。

    席级表 = ``_p1_system_support`` 现行值(零口径改动,12 号篇 §3
    席级函数);min 聚合依据 = 「先凑齐」——和/均值使
    单席满的对虚高(木桶语义)。"""
    return min(sup.get(f, 0.0) for f in pair)


def _p1_pair_decl_key(pair: tuple[str, ...]) -> tuple[float, ...]:
    """对级声明序键 = 各席体系在 ``_P1_PAIR_PREF`` 的索引组成的元组;
    短元组(单体系对)同席补 ∞——同首席的双体系对排在单体系对前
    (更完整方向优先),零新常数(PREF 声明序零改动)。"""
    idx = tuple(_P1_PAIR_PREF.index(f) for f in pair)
    return idx + (math.inf,) * (2 - len(idx))


def _p1_pair_lines(pair: tuple[str, ...]) -> tuple[str, ...]:
    """体系对 → COMP_LIBRARY 线名映射(统一阵容评分 design §6 配方锁
    联动):线**主派**羁绊(档 0 首键)∈ 体系对
    羁绊键集(:func:`_pair_bond_keys`,希儿系展开 = 量子同频+贝洛伯格)。

    例:持续伤害对 → (DOT队, 专家桑博DOT)(两线主派键均为
    持续伤害);希儿系对 → (希儿量子,)(专家桑博DOT 的贝洛伯格 2 是
    次档非主派,不入——主派判定防次档键把 DOT 线错挂进希儿系对)。
    """
    bonds = _pair_bond_keys(pair)
    out: list[str] = []
    for c in COMP_LIBRARY:
        # 主羁绊 = 档 0 首键(过渡期读法:结构上档内无次序,此处依赖
        # 迁移规则 {0: form_tiers} 保持插入序保证行为恒等;随配方决策层
        # 退役(3.3);黄泉键序对齐)
        main = next(iter(c.core_faction_reqs), '')
        if main in bonds:
            out.append(c.name)
    return tuple(out)


def _pair_restart_dead(pair: tuple[str, ...], gs: GameState) -> bool:
    """体系对全线重开级判定(design §6:线分含 −100000 的体系对不入
    p1_pair_space 候选):映射线集非空 ∧ 每条线词缀面或 boss 面重开级
    命中(kernel 侧原语 :func:`cw_affinity_table.affix_restart_hit` /
    ``boss_restart_hit``——cw_intention 禁 import 策略层线分引擎,重开级
    命中 = 吃怕/boss 表可判子集;证据/投资分量恒非负不影响判定)。

    线集空(防御,当前四体系全有映射)→ False(fail-open 配方锁照常)。
    扑满强敌(怕档 −150 非重开级)不参与本判定——排除档只认重开级。"""
    from sr_od.application.currency_war.kernel.cw_affinity_table import (
        affix_restart_hit,
        boss_restart_hit,
    )
    lines = _p1_pair_lines(pair)
    if not lines:
        return False
    affixes = tuple(gs.enemy_affixes.value or ())
    bosses = tuple(b for b in (gs.plane_bosses.value or ()) if b)
    return all(affix_restart_hit(ln, affixes)
               or boss_restart_hit(ln, bosses, affixes)
               for ln in lines)


def _p1_pair_space(sup: dict[str, float],
                   gs: GameState | None = None) -> list[tuple[str, ...]]:
    """全候选空间排序序列(不截断):体系对 = 单体系对(4)+ 双体系
    组合(6),按(对级支持度降序, 对级声明序)排序;对内体系按
    ``_P1_PAIR_PREF`` 序规整(与 ``p1_pair`` 值形态同口径)。

    候选 top3 与冻结评估域共用的**单一枚举载体**(§2.3-4「枚举载体
    = 候选机器同源排序函数不截断」);超满对(支持度 >1.0)排在恰满
    对前——冻结扫描序申报(§2.3-4)。排序键确定(支持度 = 羁绊计数/
    档,事件驱动变化,帧间稳定;声明序键两两不同)——防摇摆语义 =
    支持度不变则序不变,替代旧「在任粘滞」(§2.6-6)。

    ``gs`` 非空时启用配方锁联动过滤(design §6 统一阵容评分):全线
    重开级的体系对不入序列(:func:`_pair_restart_dead`——重开级数值排他,
    P1 不往该方向囤牌);过滤后为空(全体系对极低分)→ 回退未过滤序列
    ——配方锁照常运行,不过渡干预终局分(锁定/P2 线分路径零关联)。"""
    pairs: list[tuple[str, ...]] = []
    for i, a in enumerate(_P1_PAIR_PREF):
        pairs.append((a,))
        for b in _P1_PAIR_PREF[i + 1:]:
            pairs.append((a, b))
    ranked = sorted(pairs, key=lambda p: (-_p1_pair_support(p, sup),
                                          _p1_pair_decl_key(p)))
    if gs is None:
        return ranked
    alive = [p for p in ranked if not _pair_restart_dead(p, gs)]
    return alive or ranked


def p1_pair_candidates_of(gs: GameState) -> tuple[tuple[str, ...], ...]:
    """体系对候选机器(只读,不落字段):支持度 > 0 的体系对按
    (对级支持度降序, 对级声明序)取 top ``_P1_PAIR_CANDIDATE_TOP_N``。

    - **希儿系对入候选门槛 = 席级支持度 = 1.0**(与 Q 门槛同值:单卡
      希儿 0.5 不驱动方向,§2.3-2/§2.6-10)——含希儿系的一切对在希儿
      席级未满前全部不入候选;
    - 无羁绊开局(四体系支持度全 0)候选空(§2.3-2),冷启动兜底归
      商店臂(§2.3-8,不在本模块);
    - 消费面 = 配方链重算(:func:`update_p1_recipe` 写槽)与
      ``k_empty_window_fallback`` p1_lock_band 支(同源现算,禁第二
      推导)。
    """
    sup = _p1_system_support(gs)
    seele_ok = sup.get(SEELE_SYSTEM, 0.0) >= P1_PAIR_LOCK_MIN_SUPPORT
    out: list[tuple[str, ...]] = []
    for p in _p1_pair_space(sup, gs):
        if SEELE_SYSTEM in p and not seele_ok:
            continue
        if _p1_pair_support(p, sup) <= 0.0:
            continue
        out.append(p)
        if len(out) >= _P1_PAIR_CANDIDATE_TOP_N:
            break
    return tuple(out)


def _p1_pair_overwindow(pair: tuple[str, ...],
                        gs: GameState,
                        session: StrategySession | None = None,
                        registry: DecisionV2Registry | None = None,
                        ) -> tuple[bool, float, int]:
    """命题 1b 解冻闭集出口①「面③超窗出口」判定(/§2.4)。E(frozen_pair) > R_rem ⟹ 超窗。

    - E = kernel ``e_rounds`` **逐字直调**(零第二估计器,三姊妹门共享
      测量单一源;消费对象 = ``pair_target_comp`` 现行物化产物,与本门
      E(inc)/E(alt) 同物化器同源,超窗判定不失真);
    - R_rem = 场字段求和就地自算(裁决点 9:框架不供视界量;封顶
      modeled planes,位面 ∉ 序列表键集(≥4)= 表外防御 → 0,与
      策略门面 horizon 契约同款;同式双落点 = 策略门面
      statefn/horizon.r_remaining——kernel 禁 import strategies,
      两处禁单侧改式);
    - 零新常量:比较即判据,出口与超窗同一比较单一源。

    **单点兜底充分性(支撑项)**:健康域(E≤R_rem)无需
    出口;超窗/字面零域出口按构造触发——E 有限 ∧ R_rem 随节点推进单调
    不增 ⟹ R_rem 收缩到 E 之下必然发生(末段必越窗),出口是断供盲区的
    唯一合法出口(早退通道 = 空集,诚实申报 §2.4)。返回
    (是否超窗, E, R_rem);目标物化失败(None)按 E=inf 处理 = 超窗
    (不可评估方向不冻结,诚实保守)。E/R_rem 供调用方写遥测分键。
    """
    reg = registry or DEFAULT_REGISTRY
    target = pair_target_comp(pair)
    e_f = (e_rounds(target, gs, reg, session=session)
           if target is not None else math.inf)
    # R_rem 就地自算(裁决点 9:框架不供视界量,场字段求和,封顶
    # modeled planes;同式双落点 = 策略门面 statefn/horizon.r_remaining
    # ——kernel 禁 import strategies,两处禁单侧改式)。位面 ∉ 序列表
    # 键集(≥4)= 表外防御 → 0。
    _tb = gs.node_seq_by_plane.value or PLANE_NODE_TABLES
    r_rem = (sum(len(t) for k, t in _tb.items() if k >= plane_of(gs))
             - round_num_of(gs) + 1) if plane_of(gs) in _tb else 0
    return (not (math.isfinite(e_f) and e_f <= r_rem)), e_f, r_rem


#: R3 断供驱逐已停用(2026-09-04,「未证即停用」裁定):旧
#: PAIR_DROUGHT_EVICT_ROUNDS=5 为「保守先验」,探针批标定登记的待办未兑现,
#: 任何实证引用无效——驱逐(换向动作)不再由未证阈值触发。断供/供给
#: 计数器保留作遥测与撤销证据输入,不再写 pair_evicted;缺口披露:
#: 断供死方向不再被计数驱逐,逃逸改由撤销出口①/③(证据机器)承载。
#: (经济冻结病灶①的根是单向驱逐,本停用连同 un-evict 语义一并失去
#: 载体;pair_evicted 字段保留为空集兼容序列化。)


def _update_pair_drought(gs: GameState, ist: IntentionState,
                         visible: set[str]) -> None:
    """R3 断供供给计数器(每 game-round 恰一次,由 update_intention 驱动)。

    断供驱逐停用后仅计数不驱逐:对四体系全集维护 ``shop_supply_streak``
    (在店供给连续轮)与现任 pair 方向的 ``pair_drought``(断供连续轮),
    供遥测与撤销证据链消费;写 ``pair_evicted`` 的驱逐分支已随未证阈值
    停用(见上方常量注)。
    """
    if plane_of(gs) != 1:
        return
    _shop = gs.shop.value   # payload 域:非当前画面 None(波3 切换)
    shop_names = {getattr(c, 'name', '') or ''
                  for c in shop_payload_content_cards(_shop)}
    all_systems = set(_ENGINE_BOND_KEYS) | {SEELE_SYSTEM}
    for sys in all_systems:
        if not shop_names:
            continue    # 无商店语境轮:冻结(不 +1 不清零)
        if members_in_shop(sys, shop_names):
            ist.shop_supply_streak[sys] = \
                ist.shop_supply_streak.get(sys, 0) + 1
        else:
            ist.shop_supply_streak[sys] = 0
    systems = set(ist.p1_pair) | set(ist.transition_pair)
    if not systems:
        return
    for sys in systems:
        if members_in_shop(sys, shop_names):
            ist.pair_drought[sys] = 0
        else:
            ist.pair_drought[sys] = ist.pair_drought.get(sys, 0) + 1


def members_in_shop(sys: str, shop_names: set[str]) -> bool:
    """体系成员与在店名集是否相交(``_pair_members`` 口径的供给判定;
    提为模块级函数供断供计数与单测共用,禁在消费点另写成员展开)。"""
    return bool(_pair_members((sys,)) & shop_names)


def _pair_members(pair: tuple[str, ...]) -> set[str]:
    """体系对的囤货成员集:各体系羁绊(阵营∪流派)下的注册表成员;
    希儿系 = 希儿 ∪ 量子同频 ∪ 贝洛伯格 成员(放大器池)。"""
    bonds: set[str] = set()
    for sys in pair:
        if sys == SEELE_SYSTEM:
            bonds |= {'量子同频', '贝洛伯格'}
        else:
            bonds.add(sys)
    out: set[str] = set()
    for name, c in CHARACTERS.items():
        if (set(c.factions) | set(c.flows)) & bonds:
            out.add(name)
    if SEELE_SYSTEM in pair:
        out.add('希儿')
    return out


def _pair_bond_keys(pair: tuple[str, ...]) -> set[str]:
    """体系对 → 板面羁绊键集(希儿系展开=量子同频+贝洛伯格;与
    ``_pair_members``/``locked_faction_scope`` 同口径的键侧版本)。"""
    bonds: set[str] = set()
    for sys in pair:
        if sys == SEELE_SYSTEM:
            bonds |= {'量子同频', '贝洛伯格'}
        else:
            bonds.add(sys)
    return bonds


def pair_target_comp(pair: tuple[str, ...]) -> Comp | None:
    """体系对 → 配方伪阵容(P1 配方锁帧的 target 载体物化)。

    语义:把 P1 意向锁定产物定为体系对(p1_pair)后,
    ``strategy_state_of(session).target_comp`` 在配方锁帧恒 None——部署选人/评分管线/
    投资装备钩子等既有 target 消费者从此全盲(断线症状:引擎件
    躺 bench、散脸占板,decisions.target_comp 全程空串)。
    本函数把已锁方向物化为伪阵容,写端单点 =
    策略器方向刷新(flow.CwFlowStrategy._refresh_direction,
    内化;locked_comp 空且 P1 配方锁时调用);方向选择不动(删除的 transition_focus 是
    「从零选收敛方向」,与本物化不同层,非其变体复活)。

    单一口径:
    - factions = ``_pair_bond_keys`` 板面羁绊键;core_chars =
      ``_pair_members`` 全成员(均序化,构造确定);
    - 档 0 分辨序:① ``cw_bridge_pool.BRIDGE_POOL`` 精确匹配
      (键集合相等 → 整组取该桥 engine_bonds;桥池是配方对档位的既有
      单一源,数据底=transition_combos 调研);② 无桥条目的对(希儿系
      组合)→ 档 0 只放**他体系档**(逐体系取桥池任一条的档);
      放大器两条分支挂 ``or_reqs``(``SEELE_OR_REQS``:量≥2 ∨ 贝≥2 任一即
      成,OR 语义)、carry 挂 ``required_deployed``(希儿在板)——
      取代 ②的「桥池档+量子配方档」AND 全档口径
      (借 cw_recipe 完全体档把「凑到任一=成型」塌成「量3∧贝2 全档」,
      且缺 carry 合取支;取代先例 = 对未证 post-state 条款的取代)。
      跨体系 AND 保留:他体系档仍是 AND 分支,OR 只覆盖放大器组(防半对
      冒充)。⚠️ 既有双源分歧申报:列车同行档桥池=2(train_dot)、
      cw_recipe _RECIPES=4(框架单独成型档,语义不同层)——本函数取
      桥池;cw_recipe 量子配方档自此无 pair 物化消费(注册表保留,
      其「框架单独成型档」适用范围不变)。
      注:桥线对平局无平滑性偏好;若 v2 需要
      同等偏好需另行设计。
      """
    if not pair:
        return None
    from sr_od.application.currency_war.kernel.cw_bridge_pool import BRIDGE_POOL

    bonds = _pair_bond_keys(pair)
    tiers: dict[str, int] = {}
    or_reqs: list[tuple[str, int]] = []
    required: tuple[str, ...] = ()
    for combo in BRIDGE_POOL:
        if set(combo.engine_bonds) == bonds:
            tiers = dict(combo.engine_bonds)
            break
    else:
        # 逐体系兜底:取该体系在桥池任一条的档(同源派生,不手写表),
        # 只保留本对键(防兜底混入对外体系);希儿系对再剥掉放大器键
        # (放大器档位归 or_reqs,不进档 0 的 AND 账——)。
        for combo in BRIDGE_POOL:
            for bond, tier in combo.engine_bonds.items():
                tiers.setdefault(bond, tier)
        tiers = {bond: tier for bond, tier in tiers.items() if bond in bonds}
        if SEELE_SYSTEM in pair:
            amp_keys = {bond for bond, _tier in SEELE_OR_REQS}
            tiers = {bond: tier for bond, tier in tiers.items()
                     if bond not in amp_keys}
            or_reqs = list(SEELE_OR_REQS)
            required = (SEELE_CARRY_CHAR,)
    if not tiers:
        return None
    return Comp(
        name='过渡配方·' + '+'.join(pair),
        core_chars=sorted(_pair_members(pair)),
        faction_reqs={0: dict(sorted(tiers.items()))},
        or_reqs=or_reqs,
        required_deployed=required,
    )


def _asset_thickness(comp: Comp, gs: GameState) -> float:
    """候选线资产厚度(骨架件停用后口径):

    板上+bench 中该线终局件数(副本计星级当量:每副本按其 star 计)。
    终件 = core_chars。骨架件折算项已停用(旧 SKELETON_ASSET_WEIGHT=0.5
    设计推断无标定,「未证即停用」→ 保守缺省不计;跨线骨架件仍是囤货
    对象,只是不再抬高本线厚度——撤销出口③的替代证据因此更严)。"""
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


def update_p1_recipe(gs: GameState, ist: IntentionState,
                     registry: DecisionV2Registry | None = None,
                     st: object = None,
                     ) -> IntentionState:
    """P1 过渡配方链驱动(体系对候选机器;每 game-round 恰一次,就地改
    ist 并返回;12 号篇 §3)。

    候选制形态(旧四层谓词族已退役——退役登记 = math_proofs P-T166
    行,考古走 git 历史;现行判据 = 候选排序键纯函数((对级支持度,
    声明序))确定性):

    - **候选重算**:全候选空间排序 → 支持度 > 0 的体系对(希儿系对
      门槛 = 席级 1.0)取 top3 写 ``transition_candidates`` 槽
      (``st`` 策略器状态鸭子参数;写端单一 = 本函数,缺席不写);
    - **p1_pair = 门控候选首位**:首位对级支持度 ≥
      ``P1_PAIR_LOCK_MIN_SUPPORT`` 才写,否则空对(保持旧 gate_first
      语义;与旧派生**含支持度回落帧逐帧等价**——等价性论证见
      ``committed_authority`` 序②注释);渐进第二席职能由候选并集
      承载(§2.6-4),不再产渐进 2 元对;
    - **冻结状态机**:置位评估域收窄为**双体系对全扫描**(排序键同源
      不截断,超满对先于恰满对;取 form_ok 板面成型首个;单体系对
      不进冻结域——「单体系锁停」死锁结构性免疫,§2.6-9)→ 冻结后
      槽写单元素(冻结对,读端零特判);超窗解冻闭集与再一次性标志位封印对双对
      零改动(封印判定的「重派生对」= 门控候选首位);
    - 观测快照(p1_pair_frozen_obs)照旧。位面适用范围由调用侧
      (flow 层)以窗口谓词承载——本函数只在 P1 活动窗被调。
    """
    visible = _visible_chars(gs)
    # 体系级在店供给计数(纯遥测;断供驱逐分支已停用,不触发行为)。
    _update_pair_drought(gs, ist, visible)
    # ── 命题 1b form_ok 冻结状态机(帧序:超窗出口 → 门控首位/冻结
    # 钉向 → 置位评估[双对全扫描];解冻闭集原三项目阵容锁定取代支随
    # 机器停用消亡)──
    _unfroze_this_frame = False
    if ist.p1_pair_frozen and ist.p1_pair_frozen_pair:
        over, e_f, r_rem = _p1_pair_overwindow(
            ist.p1_pair_frozen_pair, gs, None, registry)
        if over:
            # 出口①触发:解冻 + 封印该对(防逐帧空转环);本帧重算
            # 按候选语义执行,在任保持帧对保持且 F=False,直至新
            # form_ok 帧再标志。
            _unfroze_this_frame = True
            ist.p1_pair_refreeze_hold = ist.p1_pair_frozen_pair
            ist.p1_pair_frozen = False
            ist.p1_pair_frozen_pair = ()
            ist.last_event = (
                f'p1_pair:unfreeze_overwindow(E={e_f:.2f},R_rem={r_rem})')
    slot_value: tuple[tuple[str, ...], ...] = ()
    if ist.p1_pair_frozen:
        # 冻结的是方向不是板面:买入/部署继续服务 frozen_pair,
        # 重算被抑制(p1_pair 钉在 frozen_pair 上)。
        pair = ist.p1_pair_frozen_pair
        if pair != ist.p1_pair:
            ist.p1_pair = pair
            ist.last_event = 'p1_pair:' + '+'.join(pair)
        # 冻结收敛:槽写单元素(冻结对,design §2.3-4)。
        slot_value = (pair,)
    else:
        sup = _p1_system_support(gs)
        ranked = _p1_pair_space(sup, gs)
        seele_ok = (sup.get(SEELE_SYSTEM, 0.0)
                    >= P1_PAIR_LOCK_MIN_SUPPORT)
        candidates = [p for p in ranked
                      if (SEELE_SYSTEM not in p or seele_ok)
                      and _p1_pair_support(p, sup) > 0.0
                      ][:_P1_PAIR_CANDIDATE_TOP_N]
        # 门控候选首位:支持度满才有在任对(旧 gate_first 语义);
        # (0,1) 支持度带 p1_pair 恒空(committed 等价性见序②注释)。
        gated = (candidates[0]
                 if candidates and _p1_pair_support(candidates[0], sup)
                 >= P1_PAIR_LOCK_MIN_SUPPORT else ())
        # 超窗再一次性标志位封印(现行状态机零改动):封印对在「门控首位 ==
        # 封印对 ∧ fp 未见回落(<1.0)」期间禁止再一次性标志位;解封两路 =
        # 换向(门控首位 ≠ 封印对)/ fp 回落(方向丢失,此后再达成
        # 才是新 form_ok 事件)。
        if ist.p1_pair_refreeze_hold:
            if gated != ist.p1_pair_refreeze_hold:
                ist.p1_pair_refreeze_hold = ()   # 换向解封
            else:
                _t = pair_target_comp(ist.p1_pair_refreeze_hold)
                fp_v = (form_progress(_t, gs)
                        if _t is not None else 0.0)
                if fp_v < 1.0:
                    ist.p1_pair_refreeze_hold = ()   # fp 回落解封
                elif not _unfroze_this_frame:
                    ist.last_event = ('pair_gate:hold('
                                      + '+'.join(gated) + ')')
        if gated != ist.p1_pair:
            ist.p1_pair = gated
            ist.last_event = ('p1_pair:' + '+'.join(gated)) \
                if gated else 'p1_pair:wait'
        # 置位评估(事件标志):冻结域 = 双体系对全扫描(单体系对不进
        # 域;扫描序 = 候选排序键应用于全空间,超满对先于恰满对),
        # 取 form_ok 首个;封印期内不标志;空域/空对永不置位。
        if not ist.p1_pair_refreeze_hold:
            for p in ranked:
                if len(p) != 2:
                    continue
                if _p1_pair_support(p, sup) < P1_PAIR_LOCK_MIN_SUPPORT:
                    break   # 排序按支持度降序:首见 <门槛 双对即域尽
                _t = pair_target_comp(p)
                if _t is not None and form_progress(_t, gs) >= 1.0:
                    ist.p1_pair_frozen = True
                    ist.p1_pair_frozen_pair = p
                    ist.p1_pair = p   # 置位帧即钉向(与冻结帧同值)
                    ist.last_event = 'p1_pair:freeze:' + '+'.join(p)
                    candidates = [p]   # 冻结收敛同帧生效
                    break
        slot_value = tuple(candidates)
    # 槽写端单一(配方链重算帧覆写;冻结帧单元素/未冻结帧 top3):
    # st 鸭子参数缺席(裸 kernel 调用/异型状态对象)不写,禁双源。
    if st is not None:
        with contextlib.suppress(Exception):
            st.transition_candidates = slot_value
    # 观测快照(唯一写入端):最新非空派生对冻结留档。
    if ist.p1_pair and ist.p1_pair != ist.p1_pair_frozen_obs:
        ist.p1_pair_frozen_obs = ist.p1_pair
    return ist


def clear_p1_recipe(ist: IntentionState, st: object = None) -> None:
    """进 P2:配方锁退场(解冻闭集出口②「位面末」;清除 ⟹ F 同帧归 0)。

    位面适用范围由调用侧窗口谓词判定后调用一次(幂等:空对帧 no-op)。
    ``st``(可选,策略器状态鸭子参数)非空时**同点清空
    ``opening_recipe_comp`` 与 ``transition_candidates``**——配方物化
    链/候选槽写端被 P1 窗口守卫覆盖,进 P2 后永不再写,不清则 P2
    未锁窗读口消费过期 P1 配方(读口守卫:direction 读口「两键都空」
    契约与 K 空窗回退 p2plus 带可达性)。
    """
    if ist.p1_pair:
        ist.p1_pair = ()
        ist.p1_pair_frozen = False
        ist.p1_pair_frozen_pair = ()
        ist.p1_pair_refreeze_hold = ()
        ist.last_event = 'p1_pair:exit_p1'
    if st is not None:
        # 开局面键/过渡候选槽同点清空(写端单一出口;读侧 plane2 守卫
        # = 防御双保险)。异型状态对象(第三方策略面)缺属性 = 无键
        # 可清,吞异常。
        with contextlib.suppress(Exception):
            st.opening_recipe_comp = None
            st.transition_candidates = ()


def _line_hoard(comp: Comp) -> tuple[set[str], set[str]]:
    """意向线囤货采购集(目标件定义节 class2 口径的落地):

    角色件 = core_chars ∪ shared_chars(替班者已并入成员名单承载)
    ∪ 羁绊成员(档 0 ∪ 档 ≥1
    键阵营下的注册表成员——统一读口 core/bonus_faction_reqs);装备件 =
    derive_key_equips(到人配方投影)− equip_taboos
    (具名禁忌;类级禁忌如「护盾件(类)」由买侧/装备层消费,本层不展开)。
    """
    chars = set(comp.core_chars) | set(comp.shared_chars)
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
    taboos = set(comp.equip_taboos)
    equips = {e for e in derive_key_equips(comp) if e not in taboos}
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
# - **丙分支保利息保留**(在役判据):p2plus 带囤货方向恒空集 =
#   不囤、金留线上吃息,合法空集形态。
#
# 数学证明处置(3.4 对照项):甲分支定理 A 证明随判据死迁出
# (p86-proof-batch.md §3.1 删除)、乙分支证明章(定理 B 族/§3.2 资格核)
# 同批删除、丙分支命题 C 与引理 Z/主定理 M 的退役后表述在证明批保留。


def hoard_target_set(gs: GameState, ist: IntentionState,
                     session: StrategySession | None = None,
                     registry: DecisionV2Registry | None = None,
                     visible: set[str] | None = None) -> HoardTarget:
    """锁后效果接口:输出「囤货目标集合」供买侧消费([21]:只改囤货方向,不改板上)。

    - locked/forced:意向线采购集;
    - P1:非阵容锁定局 → 配方方向——体系对成员集
      (p1_pair)/四体系引擎件全集(p1_transition,空窗);
    - unlocked 无信号(P2+):**丙分支保利息缺省**(空集,不囤)——
      P86 三分支判据的甲臂(方向化囤货)与乙臂(枢纽期权)已随统一
      让位优先级迭代 3.4 退役(总纲 §2.7【拍】):未锁无目标帧的囤货
      方向不再取机器判活方向(K 目标未锁期源切换 = 策略层候选快照
      三线成员并集 ∪ 配方成员,由 mandate_v1/shop.py 序 1 义务面承载;
      行为申报 = 弱势局未锁无目标帧从「按机器方向囤」变「保利息缺省」)。
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
    if plane_of(gs) == 1:
        # P1 配方方向:体系对成员集;空窗=四体系全集。
        # 过渡装备随意([20] 装备语义:简易装备随便给,合成件归 final
        # key_equips 判定)——equip_targets 恒空。
        pair = ist.p1_pair or ()
        members = _pair_members(pair) if pair else _pair_members(_P1_PAIR_PREF)
        return HoardTarget(frozenset(members), frozenset(),
                           'p1_pair' if pair else 'p1_transition')
    # p2plus 无目标带:丙分支保利息缺省(空集;甲/乙臂退役后唯一形态)。
    # session/registry/visible 形参保留 = 旧签名兼容(退役后无判据消费)。
    return HoardTarget(frozenset(), frozenset(), 'fallback_hold')


def k_empty_window_fallback(gs: GameState,
                            ist: IntentionState,
                            session: StrategySession | None = None,
                            registry: DecisionV2Registry | None = None,
                            visible: set[str] | None = None,
                            ) -> tuple[frozenset[str], str]:
    """K 空窗回退单一源(经济冻结批病灶①):target_comp=None 时目标成员
    集的分带派生,商店域(shop.py)与准备域(cw4/entry.py)共用本函数——
    禁在任一消费域复制四体系全集/兜底逻辑(第二源)。

    返回 (成员集,分带 token):分带 token 供消费域拼遥测计数键
    (shop 侧键名契约 'shop_k_fallback_<token>' 维持历史键名不变)。
    分带语义:
    - p1_gap:P1 空窗带(支持度 < 锁门槛)→ hoard 四体系引擎件全集
      (消「K 空→零买入→支持度永不涨」死锁环);
    - p1_lock_band:P1 终局阵容锁定过渡带 → 过渡候选首位方向成员
      (候选机器同源现算,12 号篇 §2 K 空窗行——
      「空窗期同样有方向」职能由候选首位承载,禁双源),派生空 ⇒
      链 hoard 全集兜底;
    - p2plus:P2+ → **保利息缺省**(空集,不囤——统一让位优先级迭代
      3.4:K 目标未锁期源切换 = 策略层候选快照三线成员并集 ∪ 配方
      成员,由 mandate_v1/shop.py 序 1 义务面承载;kernel 甲臂判活路径
      退役后本带恒合法空,丙分支语义,contracts 带维度契约同步修订)。
      session/registry/visible 形参保留 = 旧签名兼容(甲臂退役后无
      判据消费)。
    (weak/demoted_endgame 分带已随甲/乙臂退役移除——phase 值域注释
    IntentionState.phase:weak 随机器停用不可达,demoted_endgame 全
    不可达,原分带为不可达死分支非在役判据。)"""
    if plane_of(gs) == 1:
        if p1_gap_window(gs):
            return hoard_target_set(gs, ist).char_targets, 'p1_gap'
        # p1_lock_band 支 = 候选首位成员(候选机器同源现算,只读;
        # 非空 p1_gap_window=False ⟹ 候选恒非空,or 兜底为防御形态)。
        cands = p1_pair_candidates_of(gs)
        members = (frozenset(_pair_members(cands[0]))
                   if cands else frozenset())
        return (members
                or hoard_target_set(gs, ist).char_targets), 'p1_lock_band'
    # p2plus 无目标带:丙分支保利息缺省(合法空集;带即证据)。
    return frozenset(), 'p2plus'


def committed_authority(state: GameState | None,
                        session: StrategySession | None) -> bool:
    """committed(已定型/非双轨期)权威判定(方向层单一派生源)。

    - **权威序**(任一成立即 True;候选-锁定制口径,12 号篇 §2):
      ① ``strategy_state.target_comp`` 非空——锁定线槽非空(定型语义 =
      锁定线非空,12 号篇 §2 判定源:P1 硬规则锁定与
      P2 时点兜底统一承载。原「位面 ≥ 2 恒定型」支已停用——P2 时点
      兜底锁定替代原 P2 恒定型,行为差申报:P2 入口至兜底锁帧之间的
      短窗 committed=False〔双轨期口径〕,锁定时点与原接近);
      ② ``ist.p1_pair`` 非空——P1 配方锁已立(**门控候选首位**,派生
      态产物)。
      **序②门控等价性(行为无变化论证,12 号篇
      §2 committed 行)**:p1_pair = 门控候选首位(对级支持度 ≥1.0 才写)。
      非空 ⟺ 首位支持度 ≥1.0;排序降序 ⟹ 首位 ≥1.0 ⟺ 候选中存在
      支持度 ≥1.0 的对 ⟺ 存在单体系对(席级 ≥1.0,希儿系对此时席级
      也 ≥1.0 过门槛)⟺ 席级最高支持度 ≥1.0 = 旧 gate_first 合格集
      Q 非空——含**支持度回落帧**逐帧等价(回落帧两侧同产空对:
      旧 |Q|=0 → (),新门控首位 <1.0 → ());冻结帧两侧同钉
      frozen_pair(现行钉向语义零改动)。故 committed ⟺ p1_pair 非空
      判定零变化,序②与 ``committed_from`` 消费面(攒息/装备环境/
      穿戴计划)零变化;(0,1) 支持度带的 scope 族翻转另申报
      (§2.6-5,非 committed 面)。
    - **缺供给帧 = 保守侧 False**(=双轨=攒息):策略状态/ist 不可得或
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
    return bool(getattr(ist, 'p1_pair', ()) or ()) if ist is not None else False


def committed_from(session: StrategySession,
                   state: GameState | None = None) -> bool:
    """committed(已定型/非双轨期)唯一合法读端(R1,蓝图 §4.3;
    cw_recipe 决策中心消费它成 kernel→decision 断环边,§3.3-①d;体内仅委托
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
                     transition_candidates: tuple[tuple[str, ...], ...] = (),
                     ) -> frozenset[str] | None:
    """锁定帧买侧目标约束基准。

    opportunistic/bond_fallback 买通道「目标/非目标」判定输入 =
    过渡候选并集(``transition_candidates`` 槽透传;非空时)∪
    ``locked_comp`` 采购集(``IntentionState.p1_pair`` 的约束基准契约,
    本函数是该契约的单一实现);三者皆空(空窗/弱意向/降格终局)→
    None(无锁定帧,不约束——[31]① 空窗期四体系全集是方向,
    不存在「非目标件」)。

    - P1 配方支 = **过渡候选并集**(各候选对 ``_pair_members`` 成员
      并集;12 号篇 §4 locked_buy_scope 行定版:非空边界从「p1_pair
      非空(≥1.0)」移到「候选非空(任一体系 >0)」——(0,1) 支持度带
      从 None 不约束翻转为并集约束,方向纪律提前〔有倾向即约束
      机会买〕,显式申报;冻结后槽单元素 = 冻结对成员,与现行语义
      一致)。``transition_candidates`` 参数缺省 () = 无候选供给
      (调用方未接入调用的过渡形态,配方支空);候选不经 ist 传递(槽在
      策略器状态,写端 = 配方链重算),接入调用消费方传槽值,禁现算
      第二源;
    - 阵容锁定帧(P1①资格通道 / P2+)= ``_line_hoard(comp)`` 角色采购集;
      **①锁局(P1)∪ 过渡候选并集**——二级囤货语义
      ([22]④):对件免 demote/免 final_fence,但不进 hoard 目标件集
      (阵容主序对副序,主方向与核心件优先级不动);
    - weak(撤销后去向=跨线骨架)/demoted_endgame 不覆盖:方向已撤或已
      降格,约束基准不存在(弱意向期的跨线骨架囤货本身不受本约束覆盖)。
    """
    if ist is None:
        return None
    scope: set[str] = set()
    if transition_candidates:
        for p in transition_candidates:
            scope |= _pair_members(tuple(p))
    if getattr(ist, 'transition_pair', ()):
        scope |= _pair_members(tuple(ist.transition_pair))
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

    集合构成 = ``p1_pair`` 成员(若设)+ ``locked_comp`` 采购集;**刻意
    不含 ``transition_pair``**(与 ``locked_buy_scope`` 的唯一差异):
    对件在 分层里是二级囤货——免 demote/fence 的机会性囤货
    (受息律/预算覆盖),不是 M2 骨架义务(无条件照买),升格即越分层,
    故本函数不复用 ``locked_buy_scope`` 直取。需要完整约束基准(对件
    免 demote/fence 面)的消费方仍用 ``locked_buy_scope``。
    **维持 p1_pair 直读申报(12 号篇 §4)**:配方支
    不随 scope 族切候选并集——M2 义务面 = 锁局承诺面,与 scope(机会
    买约束面)刻意分层;新 p1_pair 值形态(单满 1 元对 vs 旧渐进
    2 元对)使 P1 ①锁局 M2 义务集收窄(第二体系件移出 M2 义务面、
    仍在买面候选并集),显式申报。

    **容量可行截断**:``cap_hold`` 非 None 且
    |B| > cap_hold 时返回截断义务集 B'——序 = core∪shared ≻ (p1_pair ∪
    其余 hoard) 同级,级内 cost 升序、注册表声明序 tie-break
    (``_obligation_rank``)。结构依据 = 义务完成金流成本:低费义务先
    闭合(P41②/P76 甲 1★ 全额退净金 0 的可逆性不变量,低费成员往返
    动作成本最低),零自由参数。缺员面 missing(B') 可清空 ⇒ M2 终止
    条件恢复(停摆不动点解除);被截成员退出 M2 义务基座,
    其 M4/部署面保护必要性随之消失(义务基座 = M2 会重买的集合)。
    ``cap_hold=None`` = 宽集(兼容缺省,零漂移;容量不可得帧的
    fail-closed 方向 = 保宽,截断是收紧面不盲收)。

    触发条件 = ``locked_comp`` 非空(终局阵容锁定状态已建立)。未锁帧(P1 配方
    锁帧 locked_comp 恒空;空窗/weak/降格)→ 返回 None,
    消费方维持既有 ``line_members(target_comp)`` 口径——P1 无锁态行为
    零变化的边界基准。
    """
    if ist is None or not getattr(ist, 'locked_comp', ''):
        return None
    scope: set[str] = set()
    if getattr(ist, 'p1_pair', ()):
        scope |= _pair_members(tuple(ist.p1_pair))
    comp = get_comp(ist.locked_comp)
    core_shared: set[str] = set()
    if comp is not None:
        chars, _equips = _line_hoard(comp)
        scope |= chars
        core_shared = set(comp.core_chars) | set(comp.shared_chars)
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
                         transition_candidates: tuple[tuple[str, ...], ...] = (),
                         ) -> frozenset[str] | None:
    """锁定帧的体系(羁绊键)集(evolve 提案/部署围栏消费)。

    与 ``locked_buy_scope`` 同判据的**阵营口径**版本(off-lock
    evolve 提案的 target_factions 不含锁定 faction → 锁定目标件被
    execute_replacement 划进 old_line 整档解除——约束需要的是体系键不是
    件名):

    - P1 配方支 = **过渡候选并集的体系键**(``transition_candidates``
      槽透传,与 ``locked_buy_scope`` 同式扩位,§2.6-5;希儿系展开
      =量子同频+贝洛伯格,与 ``_pair_members`` 同口径;冻结后槽单
      元素 = 冻结对体系键,现行语义一致;参数缺省 () = 无候选供给);
    - 阵容锁定帧(P1①资格通道 / P2+)= ``locked_comp`` 主/副档键
      (``core_faction_reqs`` ∪ ``bonus_faction_reqs``,与 ``_line_hoard`` 档位键同式);
      **①锁局(P1)∪ 过渡候选体系键(与 ``locked_buy_scope``
      同式扩位)**——对体系提案不再按 off-lock 降级/解除,protect 基准
      (cw_evolution 围栏/保留序)同步扩覆盖(R2:换人可以拆引擎不行);
    - 两者皆空(空窗/弱意向/降格终局)→ None(无锁定帧,不约束——[31]①
      空窗期四体系全集是方向,不存在「off-lock 提案」)。
    """
    if ist is None:
        return None
    keys: set[str] = set()
    if transition_candidates:
        for p in transition_candidates:
            for sys in p:
                if sys == SEELE_SYSTEM:
                    keys |= {'量子同频', '贝洛伯格'}
                else:
                    keys.add(sys)
    if getattr(ist, 'transition_pair', ()):
        for sys in ist.transition_pair:
            if sys == SEELE_SYSTEM:
                keys |= {'量子同频', '贝洛伯格'}
            else:
                keys.add(sys)
    if ist.phase == 'locked' and ist.locked_comp:
        comp = get_comp(ist.locked_comp)
        if comp is not None:
            keys |= set(comp.core_faction_reqs) | set(comp.bonus_faction_reqs)
    return frozenset(keys) if keys else None


