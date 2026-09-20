"""货币战争 · 终局意向模块(strategy_v4 点0 实现;纯逻辑,不碰游戏/板上)。

单一规格源:strategy_v4 设计件「点0」
(信号分层①-⑤ / 撤销析取 / 窗口冻结语义 / 强制锁线对象限定 + 降格终局);
攻略信号数据:`comp_definitions_v2.md` 各套(欢愉族绯英档=⑤兜底、黑塔纪元 65%、
万敌 1 费开局即在等)。

**教义边界(user_playstyle)**:
- [21] final 件「买而不上」→ 本模块锁线后**只改囤货方向**(输出「囤货目标集合」
  供买侧消费),不改板上、不产出任何上场/换人动作;
- [23] 终局线由贯穿件锁定,不是 pivot → 锁定后撤销**只有三个出口**
  (前两个为析取,第三个为 P2 供给可行视界独立通道):
  ①意向核心断供证据(三条件合取:miss ≥ max(CORE_MISS_N, N_req 闭式)
  ∧ 存在异线核心可达 ∧ 异线资产厚度 ≥ A_min——统计证据+替代资产证据,
  只计刷新窗已开的轮,窗口冻结语义);②更高层级替代
  信号且过可达性对照;③P2 线完成率 G ≤ ε(供给概率×剩余轮×血预算,
  注册表派生零新参数)∧ 线内在店断供 ≥ PAIR_SUPPLY_CONFIRM_ROUNDS
  (观测证据合取,防误杀活线)且存在可行替代线(先验 G>ε ∧ 替代线
  核心在店/在手=已验证可达)——降级到 unlocked
  交 P2 移交重锁(handoff_lock;可逆,不写 evicted)。分数涌现换线不进本模块。
- [23]/[21] 的 P1 时序面(ADR-0341):贯穿件 P1 可买可囤([21] bench 等窗口),
  但**终局专属线(锁线方向不含过渡引擎)在 P1 的③/④锁线证据被资格门拦下**——
  资格 = ①类(策略/环境亲和;transitions §1「拿到逆天投资策略才配锁直通线」);
  P2/P3 ③照旧([23] 路径不变,本门只收紧 P1 时机)。

**P1 过渡配方锁(ADR-0357)**:位面 1 的锁定产物=过渡配方体系对
(transition_combos 两两组合;[20] 过渡是配方不是散买),终局 comp 锁定
只保留①类资格通道,P2+ 照旧锁 comp。(配方锁行为无条件,
见本文件「P1 锁线资格门」节注释)。

模块构成:
- ``detect_signals(gs)``:信号分层判定(①策略驱动/②类专属羁绊/③核心卡/
  ④资源/⑤由解析侧兜底,本函数不发⑤信号);
- ``IntentionState``:锁线/撤销状态机(未锁/锁定/弱意向 + 降格终局标记),
  ``update_intention(gs, ist)`` 每回合驱动;
- ``hoard_target_set(gs, ist)``:锁后效果接口——输出囤货目标集合(角色件 +
  装备件),买侧唯一消费面;无目标期帧(P2+ 无信号)囤货方向 = 三臂判据
  (P86;甲臂候选机器强锁门逐字/乙臂枢纽期权资格核/丙臂守息缺省,
  见「P86 无目标期三臂判据」节)。

数值标注「设计推断,sim 校准」的常量属 strategy_v4「悬而未决·摆动域」,
不写死语义进文档。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    refresh_prob,
)
from sr_od.application.currency_war.kernel.cw_comps import (
    COMP_LIBRARY,
    CORE_SINGLE_CARD_REGISTRY,
    SEELE_CARRY_CHAR,
    SEELE_OR_LEGS,
    STRONG_ENV_MECHS,
    V2_FAMILIES,
    Comp,
    augment_affinity,
    augment_env_affinity,
    char_routes,
    derive_key_equips,
    form_progress,
    get_comp,
    merged_mechanic_tables,
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    RECIPE_FLOOR_TRAIN_CAP,
    TRANSITION_TRAITS,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    bench_char_cost,
    sell_refund,
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
from sr_od.application.currency_war.kernel.cw_plane_table import (
    NODES_PER_PLANE,
    TOTAL_NODES,
    r_remaining,
)
from sr_od.application.currency_war.kernel.cw_plugins import (
    cross_line_skeleton as _cross_line_skeleton,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_lazy,
    strategy_state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )

# ===== 常量(设计推断,sim 校准;strategy_v4 点0 摆动域)=====
CORE_MISS_N: int = 6
"""撤销出口①阈值:意向核心 N 轮不可得 → 撤销(设计推断,sim 校准)。
计数分母 = 该核心刷新窗已开的轮(窗口冻结语义,见 LineTrack)。"""
FAMILY_BOND_MIN_COUNT: int = 2
"""②类专属羁绊信号阈值:板上+bench 该羁绊计数 ≥ 此值 → 家族信号。

【注】游戏定义量:信号族专属羁绊(银河学者/夜之半神/列车同行等)的
羁绊首档均为 2 人(cw_factions 注册表 counts[0]),阈值 = 信号族最小
激活档,非经验拟合)。"""

# 无目标期帧囤货方向由三臂判据输出(甲臂=候选机器强锁门逐字/乙臂=
# 枢纽期权资格核/丙臂=守息缺省),见本模块「P86 无目标期三臂判据」节。

# 跨线骨架件(strategy_v4「目标件」定义节 class3)。弱意向态只囤这批
# (点0:撤销后去向——只囤跨线骨架件)。
# **派生**自 ``cw_plugins.W16_MAJORITY_LINES``
# (≥3 线过半 8 张 + 恰 2 家族过半且非线级 carry 的边界 2 张);
# 派生规则与 ``cw_plugins`` 内同源裁决口径见 ``cw_plugins.cross_line_skeleton``。
# 快照测试锁派生结果(不等 = 数据错)。
CROSS_LINE_SKELETON: tuple[str, ...] = _cross_line_skeleton()

# ②类专属信号注册表(family → 专属羁绊名)。从 COMP_LIBRARY v2 家族派生
# (``Comp.bond_signal`` 数据字段,cw_comps 各条承载)——COMP_LIBRARY 演进时
# 随家族条目走,不与判断层双源。语义注(来源=comp_definitions_v2 各套「核心/副档」栏):
# 万敌燃血=夜之半神 2(96% 必配,主档)/DOT卡芙卡=持续伤害(开局即战力)/
# 姬子列车=列车同行(四人 100% 固定)/黄泉减益=减益(4-6 档主体,到前 DOT 班底
# 共享牌桌)/欢愉族=欢愉(绯英/银狼两档共用主体)/圣杯双C=命运圣杯(2 档开任务
# =燃料线入口)/大黑塔群攻=银河学者(星级总量成长)。
# 希儿量子/白厄反甲**无②信号**(bond_signal=None):量子/贝是放大器不是独立
# 伤害源(点2 卡4 语义),白厄=独立羁绊绑死单卡(只走③)。
FAMILY_BOND_SIGNALS: dict[str, str] = {
    c.family: c.bond_signal
    for c in COMP_LIBRARY
    if c.family in V2_FAMILIES and c.bond_signal
}


@dataclass(frozen=True)
class IntentionSignal:
    """一条分层意向信号(①>②>③>④;⑤不产出,由解析侧兜底)。"""

    layer: int          # 1-4(小=高优先)
    kind: str           # 'env' | 'strategy' | 'family_bond' | 'core_card' | 'resource'
    comp_name: str      # 指向 COMP_LIBRARY 套名
    evidence: str       # 证据描述(遥测/判读用)
    weight: float       # 同层排序(亲和权重;大者优先)


@dataclass
class LineTrack:
    """一条候选线的撤销计数器(窗口冻结语义载体)。

    - ``miss_count``:刷新窗**已开**且核心不可得的轮数(分母只计开窗轮);
    - ``frozen_rounds``:刷新窗**未开**的连续轮数(冻结计数器;窗口重开即清零);
      冻结超过位面剩余节点数 → 该线移出候选集(点0〔修A1〕)。
    """

    miss_count: int = 0
    frozen_rounds: int = 0
    member_drought: int = 0
    """线级在店供给断供计数(出口③证据组;窗口冻结语义同 frozen_rounds):
    有商店语境轮且 core∪shared 无任何成员在店 +1,有成员在店清零,
    无商店语境轮冻结。阈值复用 ``PAIR_SUPPLY_CONFIRM_ROUNDS``(出现
    观测按 1/轮累积、缺席证据按 (1−q)<1/轮 累积的同一离散化推导,
    与断供供给确认计数同构)。"""


@dataclass
class IntentionState:
    """锁线/撤销状态机(未锁 unlocked / 锁定 locked / 弱意向 weak)。

    P1(ADR-0357):锁定产物=过渡配方体系对(``p1_pair``)——终局 comp
    锁定只保留①类资格通道;P2+ ``p1_pair`` 恒空,comp 锁定照旧。
    """

    phase: str = 'unlocked'            # 'unlocked' | 'locked' | 'weak'
    locked_comp: str = ''              # 锁定线(COMP_LIBRARY 套名)
    p1_pair: tuple[str, ...] = ()      # P1 配方锁:体系对(过渡体系键;P2+ 恒空)
    """**P1 锁定目标数据形态(ADR-0357;显式可读,约束基准契约)**:

    - 读口 = ``strategy_state_of(session).v3_intention.p1_pair``——四体系键的
      一或二元组(1 元对 = ADR-0616 §2.1 在册边缘帧:门槛过滤先行后第二席
      零资格不再入对;|Q|=1 帧),按 ``_P1_PAIR_PREF`` 序规整,非空即
      「P1 锁定帧目标=该体系对」;
      空元组=空窗期(未锁);P2+ 恒空(P2+ 锁定目标=``locked_comp``)。
    - 体系键域与判据单一源:三羁绊键=``TRANSITION_TRAITS``
      (仙舟/列车同行/持续伤害),希儿系=``SEELE_SYSTEM`` 哨兵键
      (与 ``cw_battle_calib._engines_count`` 同口径)。
    - 遥测:``serialize_intention`` 字段全量序列化自动
      携带(不隐式——单帧锁测试断言 p1_pair 落 decisions 行)。
    - **后续「通道约束批」(迁移期补充判读:决策通道两面孔按锁定目标约束/
      末轮禁用)以本字段为约束基准**——opportunistic/bond_fallback 通道
      的「目标/非目标」判定输入 = 本字段(非空时)∪ locked_comp。
    """
    lock_layer: int = 0                # 锁定时信号层(撤销出口②的「更高层级」基准)
    lock_plane: int = 0                # 锁定时机(遥测)
    lock_round: int = 0
    transition_pair: tuple[str, ...] = ()  # ①锁局过渡对副方向(ADR-0367)
    """**①资格锁定局的过渡对保护副方向(ADR-0367;约束基准契约)**:

    - 非空 ⟺ plane==1 ∧ phase=='locked'(此时 P1 的 comp 锁只可能来自
      ①资格通道;配方锁行为无条件,F5 清偿);
      其余(P2+/配方锁局/weak/降格/空窗)恒空。
    - 派生口径与 ``p1_pair`` 同源(``_derive_p1_pair``,ADR-0616 §2.1/§2.3
      门槛先行+在任优先单席易手,随资产重派生)——两字段是同一口径在不同
      锁定帧的实例;
      ``p1_pair`` 是配方锁局的**锁定产物**,本字段是①锁局的**受保护
      副方向**(comp 采购集仍为主方向,[23] 直通权不变)。
    - 语义:对件享二级囤货([22]④,便宜囤对件不与 comp 主方向抢预算)
      与成型优先([13] P1 验收仍是体系对);消费面 =
      ``locked_buy_scope``/``locked_faction_scope``(∪ 同式扩展,买侧
      免 demote/fence + evolve 保护基准扩辖)+ ``_direction_factions``
      (pair 通道放行)+ ``form_ok``(成型停手加体系对判据)。
    - 遥测:``serialize_intention`` 字段全量序列化自动携带。
    """
    forced: bool = False               # 强制锁线产生(P3 入口)
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
      本快照);grep 守卫锁钉住唯一写入端与本函数族唯一读端。"""

    p1_pair_frozen: bool = False
    """命题 1b 冻结闩 F(ADR-0616 §2.2):True=方向
    冻结,重派生被抑制(冻结的是方向不是板面,买入/部署继续服务
    ``p1_pair_frozen_pair``)。置位 = 事件闩:F=False ∧ 重派生对非空 ∧
    ``form_progress(pair_target_comp(pair))>=1.0``(board-only 口径单一源,
    cw_comps.py);空对永不置位;fp 回落不自动清位。解冻闭集(p1_pair 域
    恰三项)= {面③超窗出口, 位面末(exit_p1), comp 锁定取代(``_lock``
    域退出类清除)}——闭集之外零解冻事件(ADR-0616 §2.2)。与
    ``p1_pair_frozen_obs``(上方,纯观测快照)零行为交互,两字段独立。"""
    p1_pair_frozen_pair: tuple[str, ...] = ()
    """冻结方向身份(F=True 时的在任对;值域 = ``p1_pair`` 同域四体系键
    二元组)。不变式 **F=True ⟹ 本字段非空**:置位需重派生对非空 +
    「外部清除⟹F 同帧归 0」二选一裁决(ADR-0616 §2.2,拒绝为空对新造
    比较语义)⟹ 超窗出口永不对空对求值,「comp 锁后方向真空直到位面末」
    的孤儿态从构造上不可达。"""
    p1_pair_refreeze_hold: tuple[str, ...] = ()
    """超窗解冻后的再闩封印(空 = 无封印)。出口解冻的对在「重派生对 ==
    封印对 ∧ fp 未见回落(<1.0)」期间禁止再闩——防超窗在任对陷入
    「出口→解冻→保持→复位→再触发」逐帧空转环(ADR-0616 §2.2 清除后
    段)。解封两路:重派生出不同对(合法换向,新方向自由闩)/ fp 回落
    (方向丢失,此后再达成 = 新 form_ok 事件,允许再闩)。"""

    tracks: dict[str, LineTrack] = field(default_factory=dict)
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
      插件台阶/兜底方向/降格满配骨架/配方方向,ADR-0357)。
    """

    char_targets: frozenset[str]
    equip_targets: frozenset[str]
    mode: str


# ===== 内部派生 =====

def _v2_comps() -> list[Comp]:
    """候选线集 = COMP_LIBRARY 中 v2 家族键非 legacy 的套(9 家族载体)。"""
    return [c for c in COMP_LIBRARY if c.family in V2_FAMILIES]


def intention_core(comp: Comp) -> str:
    """一条线的「意向核心」(撤销计数③口径的具名核心)。

    取 ``plaza_carry``(实战聚类 carry,对拍锚)且在 core_chars 内者;否则
    core_chars 首位。单一核心保证 miss 计数良定义(避免花火/瓦尔特类共享件
    在多线间产生噪声信号)。
    """
    if comp.plaza_carry and comp.plaza_carry in comp.core_chars:
        return comp.plaza_carry
    return comp.core_chars[0] if comp.core_chars else ''


def _visible_chars(gs: GameState) -> set[str]:
    """当前可见角色规范名:shop 在店 + bench/deployed 到手(识别层已归一)。"""
    names: set[str] = set()
    _shop = gs.shop.value   # payload 域:非当前画面 None(W6 波3 切换)
    for card in shop_payload_content_cards(_shop):
        if card.name:
            names.add(card.name)
    front, back = deployed_rows_of(gs)
    for u in (*front, *back, *bench_units_of(gs)):
        if u is not None and u.char_id:
            names.add(u.char_id)
    return names

def _bond_counts(gs: GameState) -> dict[str, int]:
    """板上 + bench 的羁绊计数(board 已含 deployed 聚合;bench 逐件加,
    §2.1 faction 注册表派生 = char_first_faction 单一源,未知名不计)。"""
    counts: dict[str, int] = dict(gs.board.value or {})
    from sr_od.application.currency_war.data.cw_chars import char_first_faction
    for u in bench_units_of(gs):
        fac = char_first_faction(getattr(u, 'char_id', '') or '')
        if fac and fac != '?':
            counts[fac] = counts.get(fac, 0) + 1
    return counts


def plane_remaining_nodes(gs: GameState, session=None) -> int:
    """位面内剩余节点数(含当前轮;冻结超限的对照量)。

    ADR-0366:位面轮数按 ``nodes_of_plane(session)`` 本位面真值(P2=7;
    旧按全局 9 计使 P2 冻结超限对照量虚高 2 轮)。session 缺省 None →
    回退 P1 先验(裸调用/旧签名兼容)。
    """
    from sr_od.application.currency_war.kernel.cw_plane_table import nodes_of_plane
    n = nodes_of_plane(session) if session is not None else NODES_PER_PLANE
    r = min(max(1, round_num_of(gs)), n)
    return n - r + 1


def total_remaining_nodes(gs: GameState) -> int:
    """全局剩余节点数(可达性对照量;封顶 3 位面)。"""
    p = min(max(1, plane_of(gs)), 3)
    r = min(max(1, round_num_of(gs)), NODES_PER_PLANE)
    t = (p - 1) * NODES_PER_PLANE + r - 1
    return max(0, TOTAL_NODES - t)


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
    """强制锁线对象限定:核心已在手 或 再遇窗口期望 ≤ 剩余节点数(点0〔修N4〕)。"""
    core = intention_core(comp)
    if not core:
        return False
    if core in visible:
        return True
    return encounter_window_rounds(core, level_of(gs)) <= total_remaining_nodes(gs)


def _direct_line_qualified(gs: GameState, comp_name: str) -> bool:
    """直通终局线资格判定(ADR-0338)。

    资格单一源 = 亲和表反查(**派生,不手写名单**):
    - 策略侧:任一持有策略 ``s ∈ gs.active_strategies`` 在
      ``AUGMENT_COMP_AFFINITY`` 中指向该 comp(如 黑塔纪元→大黑塔银河学者);
    - 环境侧:``gs.active_env`` 在 ``ENV_COMP_AFFINITY`` 中指向该 comp
      (如 银河学者概念股→大黑塔银河学者)。

    无任何表项的 comp(万敌单C/DOT队/黄泉线等)恒无资格 —— 它们的终局线
    只能由③核心卡(贯穿件到手,[23] 合法)或后续注册的资格项锁线。
    """
    for s in (gs.active_strategies.value or []):
        if comp_name in augment_affinity(s):
            return True
    return comp_name in augment_env_affinity(gs.active_env.value or '')


def _line_env_qualified(gs: GameState, comp_name: str) -> bool | None:
    """累积型线强环境判据(ADR-0461)。

    语义出处:「全局累积型角色越早越好,但需特定环境才强,**无环境不选**」
    (user_playstyle [21] 例外条款)+ accumulator_family §3(万敌强环境=
    敌方多动/反伤类)§4.2 前提②「当前/将遇敌方词缀 ∈ 该成员强环境集」。

    返回三态:
    - ``None`` = 判据不辖或信息缺失(comp 无 hp_charge_stack 累积成员 /
      强环境集未建模 / ``gs.enemy_affixes`` 空=词缀可信位缺失)——调用方
      必须放行(动态权重剔除同款:缺信息不造硬结论,不猜);
    - ``True`` = 词缀机制 tag 与强环境集命中;
    - ``False`` = 累积型线但环境不命中(「无环境不选」的事实面)。

    词缀→机制归一走 ``AFFIX_MECHANIC_MAP`` 单一源(未知词缀原样透传,与
    ScoreContext.mechanics 同构);未入映射的词缀(如 灼热轰炸)按不命中
    处理(宁缺勿错,见 STRONG_ENV_MECHS 注释)。消费方=update_intention
    的锁线信号过滤(行为无条件化,开关清偿决议(git 历史)),已锁线不辖
    (环境缺失只「不主动选」,不没收已锁线——accumulator_family §3 同义)。
    """
    comp = get_comp(comp_name)
    if comp is None:
        return None
    acc_types = set((comp.global_accumulators or {}).values())
    if 'hp_charge_stack' not in acc_types:
        return None
    need = STRONG_ENV_MECHS.get('hp_charge_stack')
    if not need:
        return None
    if not (gs.enemy_affixes.value or []):
        return None
    affix_map, _, _ = merged_mechanic_tables()
    mech = {affix_map.get(a, a) for a in (gs.enemy_affixes.value or [])}
    return bool(mech & need)


# ===== P1 锁线资格门(ADR-0341)=====
# 三门行为无条件化(ADR-0465 后治理蓝图):P1 终局线资格门/配方锁/过渡对
# 三门的 sim A/B 已终裁(ADR-0341/0357/0367),无开关;A/B 基线臂由 git
# 冻结快照构造(回退 = git revert)。

_ENGINE_BOND_KEYS: frozenset[str] = frozenset(b for b, _t in TRANSITION_TRAITS)
"""三羁绊体系键(仙舟/列车同行/持续伤害;派生自 cw_deploy_logic.TRANSITION_TRAITS
单一源,与 scoring/cw_sim/deploy_logic 的体系判定同源)。希儿系=单卡二元判定
不占羁绊键(与 scoring '希儿系' 哨兵同口径)。"""


def _p1_transition_eligible(comp: Comp) -> bool:
    """线的锁线方向是否仍喂养过渡引擎(资格门的「过渡线」支;ADR-0341)。

    三支全部派生,无手写线名(ADR-0338「派生优于快照」同款):
    - 希儿 ∈ core:希儿系=四体系之一,单卡即战力(伤害在希儿技能层);
    - 主/副档 ∩ 三羁绊体系键 ≠ ∅:锁线方向=意向线主/副档羁绊
      (discipline 方向期阵营门的消费对象),档位即体系 → 锁了仍在买引擎件
      (DOT队/专家桑博DOT/列车同行;[20] 过渡是配方——4列车保送 P2 即其
      升级层)。
    其余线=终局专属(万敌单C/黄泉减益/双王圣杯/命运圣杯红A/大黑塔银河学者/
    狼尊欢愉/反甲白厄):前期战力来自通用引擎池而非自身目标件

    """
    if '希儿' in comp.core_chars:
        return True
    tier_keys = set(comp.form_tiers) | set(comp.sub_tiers)
    return bool(tier_keys & _ENGINE_BOND_KEYS)


def _p1_gate_blocks(gs: GameState, comp: Comp) -> bool:
    """P1 终局专属线锁线证据门是否拦下该线(ADR-0341)。

    拦截 = 门开 ∧ plane==1 ∧ 非过渡线 ∧ 无①类资格(策略/环境亲和,
    与②门同一资格源 _direct_line_qualified)。P2/P3 不辖——
    [21] 上场窗口(姬子=7级/万敌=1-9 变阵点)与 1-8 换血点都在 P1 之后,
    终局线在 P2 起锁是 [23] 全文语义。
    """
    if plane_of(gs) != 1:
        return False
    if _p1_transition_eligible(comp):
        return False
    return not _direct_line_qualified(gs, comp.name)


#: 希儿系体系键(单卡二元判定,不占羁绊键;与 cw_battle_calib._engines_count
#: 的希儿系哨兵同口径)。
# ⚠️ 权威副本 = knowledge/cw_line_facts.SEELE_SYSTEM;本副本仅为 sim/旧判据
# 未迁消费点保留(迁移完成后随文件删除);勿新增消费。
SEELE_SYSTEM: str = '希儿系'

#: P1 配方对平手序 = 注册表声明序(TRANSITION_TRAITS 声明序 + 希儿系垫底
#: 单卡系)。旧「激活占比降序(列车 .360 > DOT .329 > 仙舟 .292,transition_
#: combos 数据附录)」社区统计平手序已退役 2026-09-04(「未证即退役」裁定;
#: 平手 tiebreak 仅定确定性,不载经验排序)。
_P1_PAIR_PREF: tuple[str, ...] = tuple(
    b for b, _t in TRANSITION_TRAITS) + (SEELE_SYSTEM,)

# ===== 希儿系形态端口(OR 腿 + carry,ADR-0613)=====
# 辖域切分(与批序 2 支持度端口 ``_seele_system_support`` 机械可检验,
# 禁互相渗透成双源):形态端口读**板面羁绊计数**(gs.board,经
# form_progress),支持度端口读**owned 去重成员计数**(bench∪deployed);
# 本文件 form 链禁出现 _seele_system_support 消费。
# 常量真源 = cw_comps.SEELE_OR_LEGS/SEELE_CARRY_CHAR(ADR-0621
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


# ===== ①锁局过渡对保护副方向(ADR-0367)=====
# 诊断来源:ADR-0367 判读节——inject on 口径 strict_mal 0.20 vs off 0.05 的
# 差值 15 局全部来自①资格通道:注入信号 r1 锁终局 comp,其采购集把囤货
# 方向从过渡引擎引开(engines2_by_r6 0.27→0.15)+ evolve 按 comp 线换档
# 拆过渡体系(S2 挤出 19/20 mal 局)=ADR-0357 主灶在①通道的残留。


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
      计 1)= 羁绊激活语义,与 form 腿(羁绊按去重成员激活)同语义,
      对合成零扰动(2★ = 3 副本合并产物,去重前后成员数不变);
    - ÷2 = 文档 OR 腿档位(量≥2 ∨ 贝≥2,docs/game/currency_war/
      research/transition_combos.md:27);max = 文档 OR 结构(凑到任一
      腿即满,取最好腿非均值);
    - 挂账指针(C1,前批遗留):量腿档位存在文档内部张力——本式 ÷2 取
      量≥2 主口径(定义表行),combo_methodology.md:133/170 写量 3;
      张力挂玩家确认(ADR-0608 挂确认指针),确认改档落
      ``SEELE_OR_LEGS``(形态端口单一源,ADR-0613)并同步回改本式分母,
      禁两端口各自为政;
    - 挂账指针(C1,P86 攻击 r1 中低1 并入):去重计数的未覆盖形态 =
      同名同 1★ 副本对(实证:绯英×2/花火×2 同场合法态,合成进度
      2/3)——去重前后成员数不变,支持度读数零扰动,但「副本进度是否
      应计支持度」属口径确认项,并入 ADR-0613 放大器计数口径挂账
      (玩家确认同门),确认前维持去重口径(零行为变更);
    - 希儿缺席恒 0:量/贝放大器不能独立当过渡(含希儿 28 帖无一缺希儿
      独立成线,transition_combos.md:27);
    - 希儿单卡(任意星级)= 0.5 不是拍定值:注册表锚 = 希儿自身双标签
      (CHARACTERS['希儿'].factions=('贝洛伯格',), flows=('量子同频',),
      data/cw_chars.py「希儿」行),她同时计入两池各 1,在文档档位结构
      下直接导出 max(1/2,1/2)=0.5——单卡 0.5 是推导后果。

    坐标系声明(同文件两套计数口径并存,禁默默统一;F5 显式登记,
    分歧裁决权在对表裁定):本公式用**去重成员
    计数**(羁绊激活证据);同文件 ``_asset_thickness`` 及配修甲
    后续同族落点用**星级当量**原语(每副本按 star 计,Σ3^(star−1) 族,
    治「合成被记为倒退」的通用排序面)。两者辖域不同——支持度回答
    「羁绊激活了几成」,星级当量回答「投入叠了多少」;任一侧禁私自换用
    另一原语。同函数内三羁绊系腿沿用逐副本羁绊计数(与 cw_battle_calib
    ._engines_count 同式)而希儿系两腿用去重计数,是设计决定非疏漏。
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
    单一源;逐副本计数,与希儿系腿的去重口径分立,坐标系声明见
    ``_seele_system_support``);希儿系 = 分级公式
    (``_seele_system_support`` 单一源,去重成员计数:希儿单卡 0.5
    开线候选、希儿+任 1 去重放大器满支持,推导链见其 docstring)。
    旧「希儿在手二元 1.0」post-state 条款被支持度降档取代
    (0.6+0.2+0.2 手定权重已退役,本式为文档口径
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
    单一源)。判定数学与 ``_derive_p1_pair`` 的不锁分支同源(同一
    ``_p1_system_support`` + 同一门槛常数,禁另造支持度算式)。
    边界:空板面恒 True(0<0.5);P2+ 调用面约定不辖(空窗系 P1 概念)。
    """
    sup = _p1_system_support(gs)
    return max(sup.values(), default=0.0) < P1_PAIR_LOCK_MIN_SUPPORT


def _p1_fuel_excluded(bc: object, incumbent_members: frozenset[str]) -> bool:
    """命题 2 排除谓词 Ex_I(x) 的单件判定(P41② 燃料类单一源口径,
    ADR-0616 §2.3)。

    Ex_I(x) ⟺ char_id≠'' ∧ star(x)=1 ∧ refund_full(x) ∧ name(x)∉K(I)
    (零重叠;参照系 = 重评时刻在任对现值 I 的成员集,先于本次计票,
    非循环)。**卫语句在调用方**:I=() ⟹ Ex≡False(空窗不排除——无此
    卫则 1★ 全额可退件在空窗被误排除,与空窗语义相反;命题方案审 F11)。

    - refund_full 判定与买侧共享谓词 ``statefn.vopt.refund_full_star_ok``
      同式(star==1 ∧ sell_refund==cost):kernel 侧镜像实现——布局依赖
      矩阵禁 kernel 反向 import strategies(同 flow 观察件落位申报先例),
      「禁第二燃料名单」辖燃料**名字集**(K(I) 注册表标签扫描派生,禁
      手抄名单),退金表改动时本式与买侧同源读 ``sell_refund`` 同步;
    - 1★ 下 refund_full 机械恒真,仍显式保留 = P41② 类资格条款
      (防退金表改动时静默失配,ADR-0616 §2.3)。
    """
    cid = getattr(bc, 'char_id', '') or ''
    if not cid:
        return False   # 件型适用面:装备/纯标签件无星级与卖出语义,不排除
    star = int(getattr(bc, 'star', 1) or 1)
    if star != 1:
        return False
    cost = bench_char_cost(bc)   # type: ignore[arg-type]
    if sell_refund(star, cost) != cost:
        return False
    return cid not in incumbent_members


def _p1_system_ordering(gs: GameState,
                        incumbent: tuple[str, ...],
                        ) -> dict[str, float]:
    """四过渡体系的排序维支持度(ADR-0616 §2.3 命题 2 新定义;合成中性
    计票,燃料剔除)——与门槛维(``_p1_system_support``,现行值零变化)
    双量纲分立,坐标系声明见 ``_seele_system_support`` docstring 与
    ADR-0608/ADR-0616(两维计数原语禁互换)。

    - 三羁绊系 sup_units(f) = Σ(非燃料成员星级当量 3^(star−1))/tier_f
      (tier = TRANSITION_TRAITS tiers[0];**逐副本**计数):3×1★→1×2★
      分子不变 = 合成中性;无帽,超满档可 >1.0(满档=1.0 跨体系可比,
      消「绝对当量偏向高档体系」偏置的归一化比值)。
    - 第④格换算式(排序维×希儿系腿):sup_units(希儿系) = 0(希儿无
      非燃料在手副本)否则 min(1.0, max(u_量/2, u_贝/2)),u_X = 该腿
      **去重成员**星级当量之和(同名取最高星;min 封顶 = 继承现行分级
      公式值域,推导链五项见 ADR-0616 §2.3)。排除谓词对 u 同样生效
      (命题 2 封闭性 (i)「排序维逐系计数对燃料类增量封闭」是全称——
      含希儿系;1★ 希儿在非在任帧因此不计排序证据,其 0.5 读数在
      希儿系进在任对或 2★ 后成立,与「单卡开线候选」门槛维读法分立)。
    - 燃料 = ``_p1_fuel_excluded``(P41② 类;K(I) = ``_pair_members``
      (在任对);I=() ⟹ Ex≡False 卫语句在此落实)。
    """
    k_members = frozenset(_pair_members(incumbent)) if incumbent \
        else frozenset()
    per: dict[str, float] = {}
    dedup_star: dict[str, int] = {}
    front, back = deployed_rows_of(gs)
    for bc in (*front, *back, *bench_units_of(gs)):
        if bc is None:
            continue
        cid = getattr(bc, 'char_id', '') or ''
        if not cid:
            continue
        ch = CHARACTERS.get(cid)
        if ch is None:
            continue
        star = int(getattr(bc, 'star', 1) or 1)
        if incumbent and _p1_fuel_excluded(bc, k_members):
            continue   # Ex 件贡献恒 0(排序维对燃料类增量封闭);
            # 卫语句:I=() ⟹ Ex≡False(空窗不排除,命题方案审 F11)
        dedup_star[cid] = max(dedup_star.get(cid, 0), star)
        eq = 3 ** (star - 1)
        for f in set(ch.factions) | set(ch.flows):
            per[f] = per.get(f, 0.0) + eq
    out = {b: per.get(b, 0.0) / t for b, t in TRANSITION_TRAITS}
    if '希儿' in dedup_star:
        u_q = sum(3 ** (s - 1) for n, s in dedup_star.items()
                  if '量子同频' in (CHARACTERS[n].flows or ()))
        u_b = sum(3 ** (s - 1) for n, s in dedup_star.items()
                  if '贝洛伯格' in (CHARACTERS[n].factions or ()))
        out[SEELE_SYSTEM] = min(1.0, max(u_q / 2, u_b / 2))
    else:
        out[SEELE_SYSTEM] = 0.0
    return out


def _progressive_second_seat(gs: GameState,
                             incumbent: tuple[str, ...],
                             registry: DecisionV2Registry | None,
                             session: StrategySession | None,
                             ) -> tuple[str, ...] | None:
    """单体系点火后的第二体系渐进方向(两体系组合目标候选;[20] 配方渐进)。

    判定尺 = kernel 成型线(cw_battle_calib._transition_formed:四体系
    **两两组合**=成型,「单个体系点火不等于成型」)与玩法 [20]/[13]
    (过渡=两两组合配方渐进;单体系达标不是成型,不停手)。门槛维合格集
    内无挑战者(chall=∅)时,第二席不能等满支持度自证(无第二体系目标 →
    不买第二体系件 → 永无满支持的自证死锁,sim 批 20260918_073401 问题 1:
    65.6% 局终态锁停在单体系),改为按「期望完成轮数最小」选向。

    选择判据 = argmin ``e_rounds(pair_target_comp(inc∪{c}), gs)``
    (kernel 单一估计器,与 ``_p1_pair_gate``/``_p1_pair_overwindow`` 同源;
    零新常数零新参数族)。该估计器天然承载三判据:in-store(货架可见件
    计入 line_distance 的 shelf 腿)、概率峰(当前等级费档出现概率
    p_bar_faction)、手上资产(tier_progress held 腿)——[3] 概率级判据
    与「变体按来牌选」的落码形态。平手按 ``_P1_PAIR_PREF`` 声明序
    (纯确定性);E=inf(静态不可达)排末位,由可行性门统一拒绝。
    物化失败(None)的候选跳过;全失败返回 None(保持单体系对)。

    返回候选对本身,可行性(E ≤ R_rem)由调用方的 ``_p1_pair_gate``
    统一裁决(单一比较源;门拒 = 渐进窗口关闭,保持单体系对 = 现行为)。
    """
    if len(incumbent) != 1:
        return None
    inc_f = incumbent[0]
    best: tuple[str, ...] | None = None
    best_key: tuple[float, int] | None = None
    for f in _P1_PAIR_PREF:
        if f in (inc_f, SEELE_SYSTEM):
            # 希儿系不参选:①E 估计器对它结构性失真(无桥条目的对在
            # pair_target_comp 兜底里剥掉量/贝放大器键,form_tiers 只剩
            # 他体系档,tier_progress 视角恒「已完成」→ E 虚假为 0);
            # ②希儿系是 carry 单卡依赖(transition_combos 定义行:无希儿
            # 时量/贝不能独立当过渡)——零证据渐进选它 = 最高风险向。
            # 其合法入场 = Q 门槛路径(支持度 ≥1.0 = 希儿+放大器在手,
            # chall 非空支,语义不变)。
            continue
        cand_pair = tuple(sorted((inc_f, f), key=_P1_PAIR_PREF.index))
        comp = pair_target_comp(cand_pair)
        if comp is None:
            continue
        e = e_rounds(comp, gs, registry, session=session)
        key = (e, _P1_PAIR_PREF.index(f))
        if best_key is None or key < best_key:
            best_key, best = key, cand_pair
    return best


def _p1_pair_eased(gs: GameState,
                   incumbent: tuple[str, ...] = (),
                   gate_first: bool = True,
                   registry: DecisionV2Registry | None = None,
                   session: StrategySession | None = None,
                   ) -> tuple[tuple[str, ...], tuple[str, ...] | None]:
    """夺席算子 T(ord, I, Q)(ADR-0616 §2.1 在任优先单席易手核;§2.3
    门槛过滤先行组合谓词)。返回 (派生对, 换席候选):换席候选非 None
    = 本帧发生「最弱在任席被挑战者排序维严格超出」的席位易手,配方对
    锁域生产路径再过命题 3 可行性门(§2.4 后置合取)。

    - Q = 门槛维 ≥ ``P1_PAIR_LOCK_MIN_SUPPORT`` 的合格集(gate_first;
      ``gate_first=False`` = 无门槛合格集 = 四体系全集,仅供
      ``p1_early_pair`` 无门槛物化面并批消费——编排者裁决①);
    - |I∩Q|=0 空窗进入:按 (−ord, PREF) 取前 min(2,|Q|) 席;
    - |I∩Q|=1:留任席无条件保持,最佳挑战者填空席(空席填充不触动
      已占用席 = §2.3(iv) 申报帧类,不辖可行性门);挑战者空集时的
      渐进填充(第二体系方向 = argmin E 两体系对,候选走 ``_p1_pair_gate``
      可行性门,门拒保持单体系对)= ``_progressive_second_seat``
      (语义与死锁依据见其 docstring;kernel 成型线两两组合,[20] 配方渐进
      ——单体系点火非成型,对必须可向第二体系扩张)。
    - |I∩Q|=2:只换最弱席,**每帧至多一席易手**;换席条件 =
      ord(最佳挑战者) > ord(最弱席)**严格大于**——平手 = 零优势证据,
      换席成本确定存在(囤货集作废、跟线投资重置),不换席弱支配换席
      (支配性论证消参数,零新数值);最弱席并列按 PREF 注册表声明序
      定序(平手仅定确定性,不载经验排序,同 P1 配方对平手序口径)。
    - 引理链(ADR §2.1):静态无环、至多 2 次易手收敛——A→B→A 振荡
      构造性不可达;恒自洽式 pair≠() ⟺ Q≠∅(gate_first 时 ⟺
      ``p1_gap_window``=False)由 |Q|=0 返回 () 保持。
    """
    sup = _p1_system_support(gs)
    if gate_first:
        q = [f for f in _P1_PAIR_PREF
             if sup.get(f, 0.0) >= P1_PAIR_LOCK_MIN_SUPPORT]
    else:
        q = list(_P1_PAIR_PREF)
    if not q:
        return (), None
    su = _p1_system_ordering(gs, incumbent)

    def ordv(f: str) -> float:
        return su.get(f, 0.0)

    pref = _P1_PAIR_PREF.index
    inc = [f for f in incumbent if f in q]
    chall = [f for f in q if f not in inc]
    if not inc:
        top = sorted(q, key=lambda f: (-ordv(f), pref(f)))[:min(2, len(q))]
        return tuple(sorted(top, key=pref)), None
    inc_pair = tuple(sorted(inc, key=pref))
    if len(inc) == 1:
        if chall:
            fill = min(chall, key=lambda f: (-ordv(f), pref(f)))
            return tuple(sorted(inc + [fill], key=pref)), None
        # 渐进通道(单体系点火 → 两体系组合目标;[20]/kernel 成型线):
        # 第二席按 argmin E 选向,产出候选对交调用方可行性门——门开 =
        # 对升级两体系(买/部署/换入三面向第二体系渐进,readiness 随
        # 两档 AND 自动对齐 kernel 成型线);门拒 = 渐进窗口关闭
        #(E > R_rem),保持单体系对 = 旧行为(fp≥1.0 冻结 → 停手战)。
        return inc_pair, _progressive_second_seat(gs, inc, registry, session)
    weakest = min(inc, key=lambda f: (ordv(f), pref(f)))
    if chall:
        best = min(chall, key=lambda f: (-ordv(f), pref(f)))
        if ordv(best) > ordv(weakest):
            cand = tuple(sorted(
                [f for f in inc if f != weakest] + [best], key=pref))
            return inc_pair, cand
    return inc_pair, None


def _p1_pair_gate(candidate: tuple[str, ...],
                  gs: GameState,
                  registry: DecisionV2Registry | None = None,
                  session: StrategySession | None = None,
                  ) -> tuple[bool, float, int]:
    """命题 3 可行性门(ADR-0616 §2.4):E(alt_pair) ≤ R_rem 才许换席。

    E = kernel ``e_rounds`` **逐字直调**(消费对象 = ``pair_target_comp``
    现行物化产物,与超窗出口同物化器同源,零第二估计器);R_rem =
    ``cw_plane_table.r_remaining`` 单一源读法。实现 = 超窗出口判定
    ``_p1_pair_overwindow`` 的取反薄壳(同一比较单一源,门与出口同闸)。
    返回 (是否放行, E, R_rem);目标物化失败(None)按 E=inf = 拒
    (不可评估方向不换席,fail-closed 保守向,与出口读法一致)。
    零新常量:比较即判据。"""
    over, e_alt, r_rem = _p1_pair_overwindow(
        candidate, gs, session, registry)
    return (not over), e_alt, r_rem


def _derive_p1_pair(gs: GameState,
                    incumbent: tuple[str, ...] = (),
                    registry: DecisionV2Registry | None = None,
                    session: StrategySession | None = None,
                    ) -> tuple[str, ...]:
    """P1 配方对派生(ADR-0616 四层谓词结构;面①②③):门槛维过滤先行
    (Q 两席都查 1.0)→ 在任优先单席易手 → 命题 3 可行性门后置合取
    (换席候选 E> R_rem ⟹ 保持原对)→ 非在任席间平手按 ``_P1_PAIR_PREF``
    注册表声明序。边缘帧按在册申报:|Q|=1 → 1 元对;|Q|=0 → () 空窗。

    - ``incumbent`` = 重评时刻在任对现值 I(调用方传 ``ist.p1_pair`` /
      ``ist.transition_pair``;_lock 域切换帧传 () ——域切换不继承,
      合法换向)。I 先于本次计票,是排除谓词参照系非循环输入。
    - 旧 ``exclude`` 参数随断供驱逐退役恒空,本批随消费点
      删除(零行为差;ADR-0616 §10 登记项裁决归落码批)。
    - **「支持度只增」旧自述已废止**:卖出降计数(T2)与合成降计数
      (T3)两形态下支持度真实下降,sim 实证证伪「只增」前提;方向
      稳定性现在由在任优先+门槛先行+合成中性排序维的结构保证承载,
      非资产单调性假设(证伪记录与冻结语义入册 = ADR-0357 修订 +
      ADR-0616 §3,变更史不进注释)。
    - 旧「兑现链方向侧供给感知支持度/切换滞回」仍随旧方案清退批删除
      (realization_chain 开关族出局,清查报告 OLD_MIX_AUDIT §1.3);
      本重构是谓词结构消环,非滞回参数复活(零 θ/δ/D_min 第二参数族)。

    命题 1b(ADR-0616 §2.2):本函数是重派生派生器,**F 冻结期间不被
    进入**(抑制在调用方 update_intention P1 段;调用时机/闩/出口归
    状态机,本函数保持纯派生)。
    """
    pair, cand = _p1_pair_eased(gs, incumbent, registry=registry,
                                session=session)
    if cand is not None:
        ok, _e_alt, _r_rem = _p1_pair_gate(cand, gs, registry, session)
        if ok:
            return cand
    return pair


def _p1_pair_overwindow(pair: tuple[str, ...],
                        gs: GameState,
                        session: StrategySession | None = None,
                        registry: DecisionV2Registry | None = None,
                        ) -> tuple[bool, float, int]:
    """命题 1b 解冻闭集出口①「面③超窗出口」判定(ADR-0616 §2.2/§2.4)。E(frozen_pair) > R_rem ⟹ 超窗。

    - E = kernel ``e_rounds`` **逐字直调**(零第二估计器,三姊妹门共享
      测量单一源;消费对象 = ``pair_target_comp`` 现行物化产物,与本门
      E(inc)/E(alt) 同物化器同源,超窗判定不失真);
    - R_rem = ``cw_plane_table.r_remaining`` 单一源读法(到局终,与 P84
      门同读法);
    - 零新常量:比较即判据,出口与超窗同一比较单一源。

    **单点兜底充分性(承重项,ADR-0616 §2.2)**:健康域(E≤R_rem)无需
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
    r_rem = r_remaining(session, plane_of(gs), round_num_of(gs))
    return (not (math.isfinite(e_f) and e_f <= r_rem)), e_f, r_rem


#: R3 断供驱逐已退役(2026-09-04,「未证即退役」裁定):旧
#: PAIR_DROUGHT_EVICT_ROUNDS=5 为「保守先验」,探针批标定挂账未兑现,
#: 任何实证引用无效——驱逐(换向动作)不再由未证阈值触发。断供/供给
#: 计数器保留作遥测与撤销证据输入,不再写 pair_evicted;缺口披露:
#: 断供死方向不再被计数驱逐,逃逸改由撤销出口①/③(证据机器)承载。
#: (经济冻结病灶①的根是单向驱逐,本退役连同 un-evict 语义一并失去
#: 载体;pair_evicted 字段保留为空集兼容序列化。)

#: 供给确认阈值(轮)。原 = 驱逐阈值取半派生,驱逐退役后唯一残消费 =
#: 撤销出口③的证据合取项(线内在店断供 ≥ 此值 ∧ G ≤ ε 才允许降级)。
#: 【拟】经验阈值待证(挂账);保守向 = 合取更严 → 撤销更难,
#: 降级仍可逆(不写 evicted),与出口③「防误杀」设计同向。
PAIR_SUPPLY_CONFIRM_ROUNDS: int = 2


def _update_pair_drought(gs: GameState, ist: IntentionState,
                         visible: set[str]) -> None:
    """R3 断供供给计数器(每 game-round 恰一次,由 update_intention 驱动)。

    断供驱逐退役后仅计数不驱逐:对四体系全集维护 ``shop_supply_streak``
    (在店供给连续轮)与现任 pair 方向的 ``pair_drought``(断供连续轮),
    供遥测与撤销证据链消费;写 ``pair_evicted`` 的驱逐分支已随未证阈值
    退役(见上方常量注)。
    """
    if plane_of(gs) != 1:
        return
    _shop = gs.shop.value   # payload 域:非当前画面 None(W6 波3 切换)
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


def p1_early_pair(gs: GameState,
                  ist: IntentionState | None) -> tuple[str, ...]:
    """P1 早期新件买入门的配方对读口(ADR-0372;只读,不落字段)。

    **在任纪律并批(ADR-0616 §3.3 裁决①)**:未锁
    形态期的方向派生从「无门槛 top-2 逐帧纯重派生」并入本批在任纪律——
    同一夺席算子作用于**无门槛合格集**(``_p1_pair_eased(gate_first=
    False)``,排序维/燃料剔除同款),不再是无记忆重派生。

    玩法论证(为什么 early_pair 进在任序列,非拍脑袋):
    - 方向的消费面与锁后对同构:本读口的产出经 ``p1_early_pair_members``
      / 商店线 K 投影 / flow 物化(``_refresh_direction_views``)驱动
      买侧囤货——买的是「朝该方向凑配方」的体系件([20]「过渡是配方
      不是散买」,docs/game/currency_war/research/transition_combos.md
      四体系配方结构)。方向在 sub-gate 帧间翻转 = 囤货集作废(已购
      旧方向件不再是目标)+ 跟线投资重置,与锁后换席的切换成本**同一
      实体**;平手 = 零优势证据时不换向弱支配换向,支配性论证不因
      门槛未达而失效。
    - 病灶同根:ADR-0616 §1 诊断实证的「无记忆重派生 + 排序
      证据被合成/燃料污染」摇摆链,26 事件中 2 例经本面(sub-gate 帧
      物化)发生——买侧跟方向反复横跳与锁域 relapse 是同一根在买侧
      截面;只治锁域不治买侧 = 症状搬家。
    - 空窗期同样有方向的原语义保留(ADR-0372 经济冻结批:四体系不一定
      开局凑到,[31]①;I=() 空窗进入形态 = 算子的 |I∩Q|=0 臂),改变的
      只是「进对之后怎么守」——在任席只在真证据(排序维严格超出)下
      让位。P1 外恒 ()(买入门只辖 P1)。

    - 锁定帧优先用意向字段(①锁局 transition_pair / 配方锁 p1_pair
      ——两字段是同一口径在不同锁定帧的实例);
    - 未锁/空窗/weak:无门槛合格集上按在任算子派生(本帧在任链已空时
      为 |I∩Q|=0 空窗进入形态,取排序维 top-2;排序维参照系 I=() 时
      排除谓词恒 False 卫语句,与命题 2 一致);
    - 可行性门与 form_ok 冻结不辖本面:本读口是买侧软方向(不落字段、
      不构成锁定承诺),辖门/闩会把锁域状态机语义漏进只读派生
      (ADR-0616 §2.4 门辖「配方对席位翻转」= 锁域)。
    """
    if plane_of(gs) != 1:
        return ()
    if ist is not None:
        tp = tuple(getattr(ist, 'transition_pair', ()) or ())
        if tp:
            return tp
        pp = tuple(getattr(ist, 'p1_pair', ()) or ())
        if pp:
            return pp
    pair, _cand = _p1_pair_eased(gs, (), gate_first=False)
    return pair


def p1_early_pair_members(gs: GameState,
                          ist: IntentionState | None) -> frozenset[str]:
    """P1 锁线过渡带的囤货成员集(只读;FIX_REVIEW_20260903 R3① 单一源)。

    辖域 = P1 ∧ 支持度已达锁线门槛但 pair 尚未锁帧(``update_intention``
    逐 game-round 跑,商店波内滞后)——该带旧核有 ``p1_early_pair`` 方向
    (无门槛合格集在任算子方向,ADR-0616 §3.3 裁决①并批),新核商店线
    K 投影经本函数取成员集,禁在消费位复制 top-2/成员集推导。成员投影
    = ``_pair_members(p1_early_pair(...))``
    (与 hoard_target_set P1 分支同一成员投影算子);pair 派生为空
    (P1 外)⇒ 空集,消费位自行链 hoard_target_set
    空窗全集兜底。P1 外恒空集(``p1_early_pair`` 同辖域)。
    """
    pair = p1_early_pair(gs, ist)
    return frozenset(_pair_members(pair)) if pair else frozenset()


# ⚠️ 权威副本 = knowledge/cw_line_facts._bond_members(telemetry/schema ρ 实测
# 消费已改接);本副本仅为旧判据未迁消费点保留(迁移完成后随文件删除);勿新增消费。
def _bond_members(bond: str) -> set[str]:
    """单羁绊成员名集(阵营∪流派全成员口径,与 ``_pair_members`` 同式;
    希儿系=希儿∪两放大器阵营成员)。方向侧供给衰减的在店判据单一源。"""
    if bond == SEELE_SYSTEM:
        bonds: set[str] = {'量子同频', '贝洛伯格'}
        out: set[str] = {'希儿'}
    else:
        bonds = {bond}
        out = set()
    for name, c in CHARACTERS.items():
        if (set(c.factions) | set(c.flows)) & bonds:
            out.add(name)
    return out


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
    """体系对 → 配方伪 comp(P1 配方锁帧的 target 载体物化;ADR-0459)。

    语义:ADR-0357 把 P1 意向锁定产物定为体系对(p1_pair)后,
    ``strategy_state_of(session).target_comp`` 在配方锁帧恒 None——部署选人/评分管线/
    投资装备钩子等既有 target 消费者从此全盲(断线症状:引擎件
    躺 bench、散脸占板,decisions.target_comp 全程空串)。
    本函数把已锁方向物化为伪 comp,写端单点 =
    策略器方向刷新(flow.CwFlowStrategy._refresh_direction,ADR-0583
    内化;locked_comp 空且 P1 配方锁时调用);方向选择不动(ADR-0442 删除的 transition_focus 是
    「从零选收敛方向」,与本物化不同层,非其变体复活)。

    单一口径:
    - factions = ``_pair_bond_keys`` 板面羁绊键;core_chars =
      ``_pair_members`` 全成员(均序化,构造确定);
    - form_tiers 分辨序:① ``cw_bridge_pool.BRIDGE_POOL`` 精确匹配
      (键集合相等 → 整组取该桥 engine_bonds;桥池是配方对档位的既有
      单一源,数据底=transition_combos 调研);② 无桥条目的对(希儿系
      组合)→ form_tiers 只放**他体系档**(逐体系取桥池任一条的档);
      放大器两腿挂 ``or_legs``(``SEELE_OR_LEGS``:量≥2 ∨ 贝≥2 任一即
      成,OR 语义)、carry 挂 ``required_deployed``(希儿在板)——
      ADR-0613 取代 ADR-0459 ②的「桥池档+量子配方档」AND 全档口径
      (借 cw_recipe 完全体档把「凑到任一=成型」塌成「量3∧贝2 全档」,
      且缺 carry 合取支;取代先例 = ADR-0608 对未证 post-state 条款的取代)。
      跨体系 AND 保留:他体系档仍是 AND 腿,OR 只辖放大器组(防半对
      冒充)。⚠️ 既有双源分歧申报:列车同行档桥池=2(train_dot)、
      cw_recipe _RECIPES=4(框架单独成型档,语义不同层)——本函数取
      桥池;cw_recipe 量子配方档自此无 pair 物化消费(注册表保留,
      其「框架单独成型档」辖域不变)。
      注:桥线对平局无平滑性偏好;若 v2 需要
      同等偏好需另行设计。
    - level_plan 不设:升级账退默认(升级通道的息引擎前置是独立
      杠杆,不搭本批车)。
    """
    if not pair:
        return None
    from sr_od.application.currency_war.kernel.cw_bridge_pool import BRIDGE_POOL

    bonds = _pair_bond_keys(pair)
    tiers: dict[str, int] = {}
    or_legs: list[tuple[str, int]] = []
    required: tuple[str, ...] = ()
    for combo in BRIDGE_POOL:
        if set(combo.engine_bonds) == bonds:
            tiers = dict(combo.engine_bonds)
            break
    else:
        # 逐体系兜底:取该体系在桥池任一条的档(同源派生,不手写表),
        # 只保留本对键(防兜底混入对外体系);希儿系对再剥掉放大器键
        # (放大器档位归 or_legs,不进 form_tiers 的 AND 账——ADR-0613)。
        for combo in BRIDGE_POOL:
            for bond, tier in combo.engine_bonds.items():
                tiers.setdefault(bond, tier)
        tiers = {bond: tier for bond, tier in tiers.items() if bond in bonds}
        if SEELE_SYSTEM in pair:
            amp_keys = {bond for bond, _tier in SEELE_OR_LEGS}
            tiers = {bond: tier for bond, tier in tiers.items()
                     if bond not in amp_keys}
            or_legs = list(SEELE_OR_LEGS)
            required = (SEELE_CARRY_CHAR,)
    if not tiers:
        return None
    return Comp(
        name='过渡配方·' + '+'.join(pair),
        factions=sorted(bonds),
        core_chars=sorted(_pair_members(pair)),
        form_tiers=dict(sorted(tiers.items())),
        strength='A',
        form_difficulty='easy',
        or_legs=or_legs,
        required_deployed=required,
    )


def detect_signals(gs: GameState) -> list[IntentionSignal]:
    """信号分层判定(①策略驱动 > ②类专属羁绊 > ③核心卡 > ④资源)。

    返回分层信号列表(未排序;消费方按 layer 升序 / weight 降序取最优);
    ⑤无信号兜底不在此产出——列表为空时解析侧落三臂判据(无目标期帧)。
    冻结超限已移出候选集(evicted)的线不产信号(等同信号未发生)。
    """
    out: list[IntentionSignal] = []
    comps = _v2_comps()
    # 注:evicted 过滤由 IntentionState 携带,detect_signals 是纯函数不读状态机;
    # 调用方(update_intention)负责过滤。直接消费方请走 update_intention。
    visible = _visible_chars(gs)

    # ① 策略驱动:投资环境 / 投资策略字段出现 → 对应线(近硬绑亲和表)
    if gs.active_env.value:
        for comp_name, w in augment_env_affinity(gs.active_env.value).items():
            if get_comp(comp_name) is not None:
                out.append(IntentionSignal(1, 'env', comp_name,
                                           f'环境[{gs.active_env.value}]×{w}', w))
    for s in (gs.active_strategies.value or []):
        for comp_name, w in augment_affinity(s).items():
            if get_comp(comp_name) is not None:
                out.append(IntentionSignal(1, 'strategy', comp_name,
                                           f'策略[{s}]×{w}', w))

    # ② 类专属:家族专属羁绊信号(板上+bench 计数达阈;希儿量子/白厄反甲无②)。
    # ADR-0338 资格门:羁绊副产品计数(学者2/夜半2/列车2 等)不是直通资格
    # ——直通终局线的锁线资格 = 持有对应投资策略/环境(亲和表反查);
    # 无资格不发②信号(意向保持 unlocked,P1 板面归四体系过渡逻辑,
    # P2+ 无目标期囤货方向由三臂判据承接[P86];贯穿件到手走③,
    # [23] 合法路径不变)。
    counts = _bond_counts(gs)
    for fam, bond in FAMILY_BOND_SIGNALS.items():
        if counts.get(bond, 0) >= FAMILY_BOND_MIN_COUNT:
            for c in comps:
                if c.family == fam and _direct_line_qualified(gs, c.name):
                    out.append(IntentionSignal(
                        2, 'family_bond', c.name,
                        f'{bond}×{counts[bond]}(≥{FAMILY_BOND_MIN_COUNT})', 0.5))

    # ③ 核心卡:具名意向核心在店/到手
    # ADR-0341 P1 资格门:终局专属线(锁线方向不含过渡引擎)在 P1 的③证据
    # 被拦下(贯穿件照买照囤 [21],只是不构成 P1 锁线证据);过渡线/持资格
    # 线/P2+/门关照旧。证据类=「某张卡在场」,非①类「策略/环境」。
    for c in comps:
        core = intention_core(c)
        if core and core in visible:
            if _p1_gate_blocks(gs, c):
                continue
            out.append(IntentionSignal(3, 'core_card', c.name,
                                       f'核心[{core}]可见', 1.0))

    # ④ 资源:升费资源等特殊系统锚(④层)。
    # 数据缺口声明:升费资源(道具)暂无容器字段——以升费链角色到手
    # (cost_escalation['角色'] 在 bench/deployed)作「资源到位」代理;字段接入后扩。
    # ADR-0341:④与③同为「卡/资源到手」证据类,P1 终局专属线同门。
    _front, _back = deployed_rows_of(gs)
    owned = {u.char_id for u in (*_front, *_back, *bench_units_of(gs))
             if u is not None and u.char_id}
    for c in comps:
        ce = c.special_systems.get('cost_escalation')
        if ce and ce.get('角色') in owned:
            if _p1_gate_blocks(gs, c):
                continue
            out.append(IntentionSignal(4, 'resource', c.name,
                                       f'升费链[{ce.get("角色")}]已到手', 0.5))
    return out


def _asset_thickness(comp: Comp, gs: GameState) -> float:
    """候选线资产厚度(骨架件退役后口径):

    板上+bench 中该线终局件数(副本计星级当量:每副本按其 star 计)。
    终件 = core_chars。骨架件折算项已退役(旧 SKELETON_ASSET_WEIGHT=0.5
    设计推断无标定,「未证即退役」→ 保守缺省不计;跨线骨架件仍是囤货
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


def core_miss_n_required(core: str, level: int, eps: float) -> int:
    """证据组 A 的断供轮数闭式:N_req = ⌈ln ε / ln(1−q)⌉。

    推导:P(N 轮未现 | 单轮出现率 q) = (1−q)^N ≤ ε——「核心实际可达
    却连续 N_req 轮缺席」的概率压到 ε 以下,缺席才从噪声升级为断供
    证据(设计=撤销证据闭式设计件 R3 节;治 ADR-0436 载明的
    「拍死计数把正常噪声送进撤销」病灶)。ε 取
    registry.revoke_miss_tolerance_eps(默认 5%)。实表代入
    (cw_shop_odds):3 费@lv5 q=0.069→N_req=42,3 费@lv7 q=0.135→21,
    1 费@lv5→27——拍死值 CORE_MISS_N=6 的缺席在 q≈0.07 下自然概率
    ≈0.65,纯属噪声,定量坐实「6 是多容易误触发」。

    q=0(窗口关/未识别)→ 返回 CORE_MISS_N:闭式无定义,退上限保险
    (该情形走冻结语义,本值不实际辖判)。"""
    q = _core_miss_q(core, level)
    if q <= 0.0 or q >= 1.0:
        return CORE_MISS_N
    return max(1, math.ceil(math.log(eps) / math.log(1.0 - q)))


def p2_supply_horizon(gs: GameState,
                      session: StrategySession | None = None,
                      registry: DecisionV2Registry | None = None) -> int:
    """P2 有效供给视界 H = min(位面剩余节点, ⌈hp / vd_p2_loss⌉)。

    三维中「剩余轮 × 血预算」的合取面(供给概率维在
    ``line_completion_feasibility`` 内取幂)。零新自由参数,两个输入
    全部是既有单一源:
    - 位面剩余节点 = ``plane_remaining_nodes``(ADR-0366 本位面真值,P2=7);
    - 血预算轮数 = ⌈hp / registry.vd_p2_loss⌉——vd_p2_loss=20.05 是
      P12/P21 已采的 P2 单战期望掉血(registry 单一源),血预算语义与
      ``decision_v2.discipline.p2_crisis_band``(2×vd_p2_loss)同源:
      还能承受几次 P2 败战,就还剩几轮「等得到供给」的有效窗口。

    辖域 = P2(vd_p2_loss 是 P2 量,P1/P3 调用面禁用——消费位自守)。
    hp≤0(濒死帧)→ 0(视界为零,任何线都不可达)。
    """
    reg = registry or DEFAULT_REGISTRY
    plane_left = plane_remaining_nodes(gs, session)
    # hp 决策消费点统一经政策层读口(挂账兑现:原「上游门后值传递」
    # 过渡支随 W6 波 4 改经 decision_hp,hp施门下沉kernel政策层设计
    # §2.4/§2.3;容器 hp = 门前真值,门在此消费点显式施)。
    from sr_od.application.currency_war.kernel.cw_hp_policy import (
        decision_hp,
    )
    hp = int(decision_hp(gs, session) or 0)
    blood_rounds = math.ceil(hp / float(reg.vd_p2_loss)) if hp > 0 else 0
    return min(plane_left, blood_rounds)


def line_completion_feasibility(gs: GameState,
                                comp: Comp | None,
                                session: StrategySession | None = None,
                                registry: DecisionV2Registry | None = None,
                                visible: set[str] | None = None) -> float:
    """P2 锁线可行性 G = P(线核心缺件在有效视界 H 内全部现身)。

    三维合成(供给概率 × 剩余轮 × 血预算,零新自由参数):
    - 供给概率:每缺件单轮出现率 q = ``_core_miss_q``(cw_shop_odds
      refresh_prob × DISTINCT_CARDS_PER_COST 注册表派生,与
      ``encounter_window_rounds``/``core_miss_n_required`` 同一静态
      近似,忽略 depletion——设计先例同边界);
    - 视界 H = ``p2_supply_horizon``(剩余节点 ∧ 血预算轮数);
    - 单件视界内现身率 F_m = 1−(1−q_m)^H,线完成率 G = ∏ F_m
      (缺件独立近似,构造性高估面如实声明:共同刷窗正相关使真实
      G 偏低,判据方向=只用于「不可行」侧的保守开闸,高估方向安全)。

    辖域语义:
    - 终件口径 = core_chars(与 ``_asset_thickness`` 终件一致);
      shared/替班不计——可行性回答「这条线的核心能否凑齐」,不是
      「杂件买得到吗」;
    - 缺件已到手或在店(visible)→ 该件 F=1(完成路径已兑现;
      在店件当轮可买, affordability 归花钱层,意向层不双计);
    - 某缺件该级不出(refresh_prob=0)→ G=0(等级不可达,先验零);
    - comp 为 None → 0.0。

    消费位(update_intention,全部 plane==2):P2 移交强锁候选门槛 /
    P2 信号缓锁门 / 已锁线供给不可行降级(出口③)。判据阈值 =
    registry.revoke_miss_tolerance_eps(ε,既有单一源):G ≤ ε 意即
    「完成概率压不进证据噪声带以下」的反面——比撤销出口①的证据门槛
    (miss ≥ N_req,P2 视界内不可达的 21-42 轮)更强的先验不可行。
    可行性差 ≠ 不锁线(P25 锁线价值辖溢余段核心出现即买):本判据
    只辖「锁向承诺」的准入与断供降级,不撤线内件买入义务。
    """
    if comp is None:
        return 0.0
    h_eff = p2_supply_horizon(gs, session, registry)
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


def _best_supply_feasible_alt(gs: GameState,
                              ist: IntentionState,
                              session: StrategySession | None,
                              reg: DecisionV2Registry,
                              visible: set[str],
                              exclude: str) -> tuple[str, float] | None:
    """供给可行替代线top-1(出口③的换线目标;与 ``_revoke_alt_evidence``
    同构的「异线」口径:排除当前线与 evicted,弱面位面过滤同款)。

    **双门槛**(A/B 两轮实证收敛,见 REPORT):
    1. G > ε(先验可行);
    2. 替代线意向核心在店/在手([23] 贯穿件语义:锁向承诺只有贯穿件
       到手才算「已验证可达」——G 略高于 ε 的替代线自己也完成不了,
       换过去是拿血量赌先验,A/B s3 局实证为净伤害)。
    可行线集空 → None(全不可行时维持现任锁——任何换线都是 ε 级噪声,
    P25 锁线价值保留,不折腾)。返回 (线名, G) 或 None。"""
    best: tuple[str, float] | None = None
    for c in _v2_comps():
        if c.name == exclude or c.name in ist.evicted:
            continue
        if plane_of(gs) in (c.weak_planes or ()):
            continue
        core = intention_core(c)
        if not core or core not in visible:
            continue
        g = line_completion_feasibility(gs, c, session, reg, visible)
        if g > reg.revoke_miss_tolerance_eps \
                and (best is None or g > best[1]):
            best = (c.name, g)
    return best


def _p2_signal_supply_ok(gs: GameState,
                         sig: IntentionSignal,
                         session: StrategySession | None,
                         reg: DecisionV2Registry,
                         visible: set[str]) -> bool:
    """P2 信号缓锁门的单信号判据(见 update_intention 消费位注)。
    核心在店/在手 → 放行;否则 G > ε 才放行。"""
    comp = get_comp(sig.comp_name)
    if comp is None:
        return True
    core = intention_core(comp)
    if core and core in visible:
        return True
    return line_completion_feasibility(
        gs, comp, session, reg, visible) > reg.revoke_miss_tolerance_eps


def _revoke_alt_evidence(gs: GameState, visible: set[str],
                         locked_comp: str, evicted: set[str],
                         a_min: float) -> tuple[str, float] | None:
    """证据组 B:I_evidence = ∃ 异线 comp:``_core_reachable`` ∧
    ``_asset_thickness`` ≥ A_min(意图证据本体——「有没有另一条线正在
    实际生长」,区别于噪声与断供共有的「本线缺了多久」;设计 R3.1)。

    - ``_core_reachable`` 复用出口②的可达对照,不造第二把尺;
    - 排除当前锁定线(「异线」字面)与 evicted 冻结超限线(已证明
      不可续的线不是「生长中的替代资产」);
    - 多条满足取厚度最大者(证据强度排序;选线权仍在信号分层,
      证据只回答「可不可以撤」,不回答「撤向哪」)。
    返回 (comp 名, 厚度) 或 None。"""
    best: tuple[str, float] | None = None
    for c in _v2_comps():
        if c.name == locked_comp or c.name in evicted:
            continue
        if not _core_reachable(c, gs, visible):
            continue
        thk = _asset_thickness(c, gs)
        if thk >= a_min and (best is None or thk > best[1]):
            best = (c.name, thk)
    return best


def _best_signal(signals: list[IntentionSignal]) -> IntentionSignal | None:
    """分层取最优:layer 升序 → weight 降序 → 库序(stable)。"""
    if not signals:
        return None
    return sorted(signals, key=lambda s: (s.layer, -s.weight))[0]


def _track(ist: IntentionState, comp_name: str) -> LineTrack:
    if comp_name not in ist.tracks:
        ist.tracks[comp_name] = LineTrack()
    return ist.tracks[comp_name]


# ===== 锁线断头观测分键(纯观测件;设计语义 = 锁线断点按断点位置分键的
# 定向观测,分键清单 = 下行前缀全集逐键注。原锁线断头 P2 定向通道设计稿
# 未入库已灭失(原件名 lock_path_p2_channel_design/DESIGN.md);语义存档 =
# math_proofs P65-P67 与 proofs/p65-promote-candidate-set-reachability.md)=====
# 四分键禁合并为单一「锁线失败」键(设计稿 §6 断点定位粒度确认);全部
# 只承归因不作目标值——42 跳对照警示:有锁对照批 hp 中位反而 0.0,锁定率
# 与结局无单调关系,禁入验收通过线禁作优化目标。零行为守卫:观测位只
# 计数,不改任何判定/发射结果(守卫锁 = sr-od-test test_cw_lock_path_obs_keys)。

#: 观测分键前缀全集(strategy_state_of(session).cw4_counters;与既有键族零交集,设计稿 §4 条款③)。
LOCK_PATH_OBS_KEY_PREFIXES: tuple[str, ...] = (
    'weakplane_exempt_eval',          # G5:信号曾生成但被弱面剔(+豁免判据分支)
    'p2_supply_gate_cull',            # G6:信号存活但被 G≤ε 缓锁剔除
    'neardeath_direction_obs_',       # G6/G7:濒死带定向观测(H=血预算轮数≤1 帧)
    'p2_handoff_',                    # G7:移交帧/候选空帧计数
    'promote_candidate_',             # G8:晋升候选集纯派生非空率
    'intention_frame_',               # 锁定率分母:意向驱动帧数(按位面)
    'intention_locked_frame_',        # 锁定率分子:phase=='locked' 帧(按位面)
)


def _near_death_band(gs: GameState,
                     registry: DecisionV2Registry | None = None,
                     session: StrategySession | None = None) -> bool:
    """濒死带观测判定(零新参数):0 < hp ≤ ``vd_p2_loss``,即血预算
    轮数 ⌈hp/vd_p2_loss⌉ == 1——与 ``p2_supply_horizon`` 血预算支同式,
    只辖观测分键(设计稿 §2.3 观测件;授权面出辖 §12-7 并案批)。"""
    # hp 决策消费点统一经政策层读口(挂账兑现,同 p2_supply_horizon)。
    from sr_od.application.currency_war.kernel.cw_hp_policy import (
        decision_hp,
    )
    hp = int(decision_hp(gs, session) or 0)
    if hp <= 0:
        return False
    return math.ceil(hp / float((registry or DEFAULT_REGISTRY).vd_p2_loss)) == 1


def _bump_obs(session: StrategySession | None, key: str) -> None:
    """观测分键计数(strategy_state_of(session).cw4_counters 容器;键登记惯例同 mandate_v1)。

    双形态宿主(终态契约 §2.6 kernel 注入化):入参即 StrategyState
    (带 cw4_counters 属性)→ 直用;session/None → 旧路径(strategy_state_lazy;
    None 纯逻辑直调静默跳过)。容器缺席惰性建空 dict(先例 =
    mandate_v1/entry.py 初始化面)——只写计数,不碰任何判定输入,零行为。"""
    if session is None:
        return
    st = session if hasattr(session, 'cw4_counters') \
        else strategy_state_lazy(session)
    if st is None:
        return   # 工厂未注册(第三方策略面):kernel 不代建,静默跳过
    st.cw4_counters[key] = st.cw4_counters.get(key, 0) + 1


def promote_candidates(gs: GameState,
                       ist: IntentionState,
                       session: StrategySession | None = None,
                       registry: DecisionV2Registry | None = None,
                       visible: set[str] | None = None) -> list[Comp]:
    """晋升候选集纯派生(设计稿 §2.1 公式;本批为 G8 观测载体,零行为)。

    公式(与 P2 移交候选 :1345 同判据形状,输入换 p1_pair 冻结快照):
    ``{ c ∈ v2 comps : c ∉ evicted ∧ (form_tiers ∪ sub_tiers) ∩
    pair 体系键 ≠ ∅ ∧ plane ∉ weak_planes ∧ _core_reachable ∧
    (plane != 2 或 G > ε) }``。输入 = ``p1_pair_frozen_obs``(退场前
    冻结副本,空 = P1 无配方方向,候选恒空)。

    - **行为交付面出辖**:排序与锁定消费归 P65 直证批(设计稿 §6 验收
      序「①前置观测」),本函数禁入任何行为消费点;
    - 体系键交集用 ``_pair_bond_keys``(希儿系展开=量子同频+贝洛伯格,
      与 ``locked_faction_scope`` 同口径,不另造键展开)。"""
    pair = tuple(ist.p1_pair_frozen_obs or ())
    if not pair:
        return []
    reg = registry or DEFAULT_REGISTRY
    vis = _visible_chars(gs) if visible is None else visible
    bonds = _pair_bond_keys(pair)
    out: list[Comp] = []
    for c in _v2_comps():
        if c.name in ist.evicted:
            continue
        if not (set(c.form_tiers) | set(c.sub_tiers)) & bonds:
            continue
        if plane_of(gs) in (c.weak_planes or ()):
            continue
        if not _core_reachable(c, gs, vis):
            continue
        if plane_of(gs) == 2 and line_completion_feasibility(
                gs, c, session, reg, vis) <= reg.revoke_miss_tolerance_eps:
            continue
        out.append(c)
    return out


def _lock(ist: IntentionState, gs: GameState, sig: IntentionSignal,
          forced: bool = False) -> None:
    ist.phase = 'locked'
    ist.locked_comp = sig.comp_name
    ist.p1_pair = ()   # comp 锁定取代配方锁(ADR-0357:①资格通道)
    # 命题 1b 解冻闭集出口③「comp 锁定取代」(ADR-0616 §2.2):域退出类
    # 清除,外部清除 ⟹ F 同帧归 0(F=1⟹对非空不变式的写点侧半边)。
    # 冻结保护配方方向不被噪声重派生,不保护已被合法方向替代取代的承诺。
    ist.p1_pair_frozen = False
    ist.p1_pair_frozen_pair = ()
    ist.p1_pair_refreeze_hold = ()
    # ADR-0367:①锁局(P1∧配方锁开)同时派生过渡对副方向
    # (与 p1_pair 同口径;P2+ 强制锁线/旧通道 P1 锁均不辖)。
    # incumbent=():comp 锁定 = 域切换,合法换向不继承旧在任
    # (ADR-0616 §2.2「域切换不继承」同款语义)。
    ist.transition_pair = (
        _derive_p1_pair(gs)
        if plane_of(gs) == 1
        else ()
    )
    ist.lock_layer = sig.layer if not forced else 1   # 强制锁线视作最高层(不可被出口②撤)
    ist.lock_plane = plane_of(gs)
    ist.lock_round = round_num_of(gs)
    ist.forced = forced
    ist.weak_comp = ''
    ist.revoke_evidence = {}   # 重锁=证据消费完毕(字段契约见 IntentionState)
    ist.last_event = ('forced_lock:' if forced else 'lock:') + sig.comp_name


def update_intention(gs: GameState, ist: IntentionState,
                     session: StrategySession | None = None,
                     registry: DecisionV2Registry | None = None,
                     st=None
                     ) -> IntentionState:
    """每回合驱动锁线/撤销状态机(就地改 ist 并返回;直吃容器 GameState)。

    序:降格终局短路 → 锁定态撤销检查(冻结 → miss-N → 高层信号)
    → 未锁/弱意向解析(新信号锁线,否则⑤兜底方向)→ P3 入口强制锁线。
    (C4 存活轮数门接线 _switch_gate_open、门闩与换线门决策位/闩已随
    旧方案清退批删除,清查报告 OLD_MIX_AUDIT §1.3——默认关开关族出局,
    换线裁决回归 E_rounds/θ/δ/D_min 主判据。)
    """
    if ist.demoted_endgame:
        # 吸收态短路也计入锁定率分母(帧末恒 unlocked,分子自然不计;
        # 漏计会虚高锁定率——分键口径声明见函数尾计数块)。
        _plane_key = f'p{min(max(1, plane_of(gs)), 3)}'
        _bump_obs(st or session, f'intention_frame_{_plane_key}')
        return ist   # 降格终局是 absorbing 态(点7 止损序同构,不回弹)
    if plane_of(gs) != 1 and ist.transition_pair:
        # 出 P1:过渡对副方向退场(ADR-0367;P2+ 锁定目标=locked_comp 唯一)
        ist.transition_pair = ()
    visible = _visible_chars(gs)
    # (原「门闩位面切换清零」分支只在闩置位后生效;门闩删除后默认行为
    # =位面切换不清 miss_count——维持删除前生产默认,零漂移。)
    # R3 断供驱逐(ADR-0465):每 game-round 恰一次的体系级断供计数
    # (pair 方向在场时辖;断供计数写 pair_drought,驱逐分支已随未证阈值
    # 退役,pair_evicted 恒空集——派生 exclude 参数留兼容)。
    _update_pair_drought(gs, ist, visible)
    sigs = [s for s in detect_signals(gs) if s.comp_name not in ist.evicted]
    # 弱面位面过滤(经济冻结批,病灶③):注册表自注 weak_planes 含当前
    # 位面的线不产锁线信号——单一源=Comp.weak_planes 注册项自注(如
    # DOT队 weak_planes=(2,)「P2 被抽陀螺,保命 pivot 不选」)。旧形态
    # 只滤 maybe_pivot 保命路径,③核心卡可见信号(P2r1 卡芙卡在场)绕过
    # 过滤锁出 P2 弱面线,选线即死路(实机局 g_20260904_042657)。
    _pre_wp = len(sigs)
    _pre_sigs = sigs
    sigs = [s for s in sigs
            if plane_of(gs) not in (getattr(get_comp(s.comp_name),
                                            'weak_planes', ()) or ())]
    if len(sigs) != _pre_wp:
        log.info('[cw][intention] 弱面过滤 %d→%d 信号(plane=%s)',
                 _pre_wp, len(sigs), plane_of(gs))
        # G5 观测分键(设计稿 §6):信号曾生成但被弱面剔——逐被剔信号
        # 计 eval,并按豁免判据(设计稿 §2.2:厚度 ≥ A_min ∧ 意向核心
        # 在店/在手)预演分支(fail-closed 期只计数,豁免行为不落)。
        # fail 支=厚度不足是「维持零通道」组拼合式的必要输入(§6)。
        _reg_wp = registry or DEFAULT_REGISTRY
        _a_min = _reg_wp.revoke_evidence_min_thickness
        _kept = {y.comp_name for y in sigs}
        for s in (x for x in _pre_sigs if x.comp_name not in _kept):
            comp_wp = get_comp(s.comp_name)
            if comp_wp is None:
                continue
            _bump_obs(st or session, 'weakplane_exempt_eval')
            thk = _asset_thickness(comp_wp, gs)
            core = intention_core(comp_wp)
            core_vis = bool(core) and core in visible
            if thk >= _a_min and core_vis:
                _bump_obs(st or session, 'weakplane_exempt_eval_hit')
            elif thk < _a_min:
                _bump_obs(st or session, 'weakplane_exempt_eval_fail_thickness')
            else:
                _bump_obs(st or session, 'weakplane_exempt_eval_fail_visible')
    revoked = False   # 本轮是否发生撤销(出口①miss/出口②):撤后当轮不重锁——
    # 「意向降级为弱意向……直至新信号」= 新信号指下一轮起的信号;同轮撤+锁会让
    # 弱意向态不可观测(判读/遥测断档),状态机一回合最多一次转移。

    if ist.phase == 'locked':
        comp = get_comp(ist.locked_comp)
        core = intention_core(comp) if comp else ''
        track = _track(ist, ist.locked_comp)
        ch = CHARACTERS.get(core) if core else None
        window_open = bool(ch) and refresh_prob(level_of(gs), ch.cost) > 0
        if not window_open:
            # 窗口冻结:未开窗不计 miss;冻结超位面剩余节点 → 移出候选集,
            # 意向回⑤无信号态——**不触发③**(该轮③信号被排除)
            track.frozen_rounds += 1
            # ADR-0366:冻结超限对照量按本位面真值(session 透传,P2=7)。
            if track.frozen_rounds > plane_remaining_nodes(gs, session):
                ist.evicted.add(ist.locked_comp)
                ist.phase = 'unlocked'
                ist.locked_comp = ''
                ist.lock_layer = 0
                ist.transition_pair = ()   # 锁撤销 → 副方向随之退场(ADR-0367)
                ist.revoke_evidence = {}   # 驱逐不经撤销,证据随之失效
                ist.last_event = f'evict:frozen:{track.frozen_rounds}'
                sigs = [s for s in sigs if s.layer != 3]   # 不触发③
        else:
            track.frozen_rounds = 0
            # 线级在店供给断供计数(出口③证据组):有店轮无任何线内
            # 成员(core∪shared)在店 +1,有成员清零,无店轮冻结。
            _shop = gs.shop.value   # payload 域:非当前画面 None(W6 波3 切换)
            shop_names = {getattr(c, 'name', '') or ''
                          for c in shop_payload_content_cards(_shop)}
            if shop_names:
                line_members_seen = bool(
                    shop_names & (set(comp.core_chars)
                                  | set(comp.shared_chars))) if comp else False
                track.member_drought = (0 if line_members_seen
                                        else track.member_drought + 1)
            if core in visible:
                track.miss_count = 0
            else:
                track.miss_count += 1
                # 撤销出口①(三条件合取,缺一不开窗;设计 R3.1):
                #   ① miss ≥ max(CORE_MISS_N, N_req)——N_req 由 ε 容忍
                #     概率闭式推导(证据组 A),CORE_MISS_N 保留为上限保险
                #     (防牌池数据异常使 N_req 过小);仅达拍死计数不再
                #     开窗(ADR-0436:门放行噪声换线的病灶在此收窄)。
                #   ② 证据组 B:存在异线 comp 核心可达 ∧ 资产厚度 ≥ A_min
                #     (registry.revoke_evidence_min_thickness,冻结池
                #     随机厚度基线 f0 曲线 5% 点测量值,见其注释)。
                # 误开窗操作定义(开窗局到局末未发生「新线落锁且新线
                # 最终成型(form_score 达标)」=纯扰动)与 A/B 判据
                # (注入臂 n=300/臂、池指纹锚,生产阈值零动):
                #   a) evidence 臂触发率 >0 且逐例带证据字段(off 臂 ≈0
                #      实测;off 臂逐位=零漂移锚);
                #   b) 开窗局中新线成型局 ≥2/3,低于此=证据组 B 分辨力
                #      不足,回炉 A_min/ε;
                #   c) 开窗局 P2 存活轮数分布不后移(C3 无效判据口径)→
                #      出口在 sim 牌池概念无效,如实记「结构件」,不硬开臂。
                reg = registry or DEFAULT_REGISTRY
                n_req = core_miss_n_required(
                    core, level_of(gs), reg.revoke_miss_tolerance_eps)
                if track.miss_count >= max(CORE_MISS_N, n_req):
                    ev = _revoke_alt_evidence(
                        gs, visible, ist.locked_comp, ist.evicted,
                        reg.revoke_evidence_min_thickness)
                    if ev is not None:
                        # 撤销出口①:断供证据 + 替代资产证据齐备 → 降级弱意向
                        alt_name, thk = ev
                        q = _core_miss_q(core, level_of(gs))
                        alt_comp = get_comp(alt_name)
                        e_alt = (e_rounds(alt_comp,
                                          gs, reg,
                                          session=session)
                                 if alt_comp is not None else math.inf)
                        ist.phase = 'weak'
                        ist.weak_comp = ist.locked_comp
                        ist.locked_comp = ''
                        ist.lock_layer = 0
                        ist.transition_pair = ()   # weak 不辖(ADR-0367,同 scope 契约)
                        ist.revoke_evidence = {
                            'kind': 'miss',
                            'miss_count': track.miss_count,
                            'n_req': n_req,
                            'q': round(q, 4),
                            'eps': reg.revoke_miss_tolerance_eps,
                            'alt_comp': alt_name,
                            'e_alt': (round(e_alt, 3)
                                      if math.isfinite(e_alt) else None),
                            'asset_thickness': round(thk, 2),
                            'a_min': reg.revoke_evidence_min_thickness,
                        }
                        ist.last_event = (
                            f'revoke:miss{track.miss_count}'
                            f'(n_req={n_req},q={q:.3f},alt={alt_name}'
                            f',thk={thk:.1f})')
                        revoked = True
            # 撤销出口③(P2 供给可行视界降级,锁线可行性批):
            # 条件 = P2 ∧ 窗开 ∧ 核心不在店/在手 ∧ 线完成率 G ≤ ε ∧
            # 线内在店断供 ≥ PAIR_SUPPLY_CONFIRM_ROUNDS ∧ 存在 G > ε
            # 的可行替代线。语义:出口①的证据门槛 N_req(3费@lv7=21 轮)
            # 在 P2 的 7 轮视界内不可达——死守一条供给空缺线既无法完成
            # 也无法被证据机器合法放弃(R5 死法族主因:10 死亡局锁线波
            # 线内件出现率 16.7%,hp0 终持金≥100)。**断供证据合取是
            # 防误杀的关键**:G ≤ ε 只是先验不可行,引擎线(列车同行等
            # 成员持续在售)仍可能功能良好,A/B 实证(s3 局)无证据合取
            # 时会撤掉活线换死线——先验 + 观测断供双证据才构成「线死」。
            # 降级到 unlocked 让 P2 移交(handoff_lock)机制
            # 下一轮确定性地重锁到可行线,换线不绕信号运气。与出口①
            # 同构的可逆性:降级不写 evicted,现线缺件兑现(买到)/血量
            # 回升(H 变大)/升级(q 变大)后 G 恢复即可经信号/移交重锁
            # (un-evict 同款,经济冻结批语义)。核心在店帧不辖(当轮
            # 可买,缺件集即缩,G 会被低估)。全线不可行(无 G>ε 替代)
            # 不降级:任何换线都是 ε 级噪声,P25 锁线价值保留。
            if (not revoked and plane_of(gs) == 2 and core
                    and core not in visible
                    and track.member_drought >= PAIR_SUPPLY_CONFIRM_ROUNDS):
                _reg_f = registry or DEFAULT_REGISTRY
                g_locked = line_completion_feasibility(
                    gs, comp, session, _reg_f, visible)
                if g_locked <= _reg_f.revoke_miss_tolerance_eps:
                    alt = _best_supply_feasible_alt(
                        gs, ist, session, _reg_f, visible,
                        exclude=ist.locked_comp)
                    if alt is not None:
                        from sr_od.application.currency_war.kernel.cw_hp_policy import (
                            decision_hp as _decision_hp_disc,
                        )
                        alt_name, g_alt = alt
                        _h = p2_supply_horizon(gs, session, _reg_f)
                        ist.phase = 'unlocked'
                        ist.weak_comp = ist.locked_comp
                        ist.locked_comp = ''
                        ist.lock_layer = 0
                        ist.transition_pair = ()
                        ist.revoke_evidence = {
                            'kind': 'supply_infeasible',
                            'g_locked': round(g_locked, 4),
                            'alt_comp': alt_name,
                            'g_alt': round(g_alt, 4),
                            'eps': _reg_f.revoke_miss_tolerance_eps,
                            'h_eff': _h,
                            'hp': int(_decision_hp_disc(gs, session) or 0),  # 读法声明同 p2_supply_horizon(政策层读口)
                            'member_drought': track.member_drought,
                        }
                        ist.last_event = (
                            f'revoke:supply_infeasible:{alt_name}'
                            f'(g={g_locked:.3f},g_alt={g_alt:.3f}'
                            f',h={_h})')
                        revoked = True
        if ist.phase == 'locked':
            # 撤销出口②:更高层级替代信号 + 可达性对照(层级高≠必换)
            for s in sigs:
                if s.comp_name == ist.locked_comp or s.layer >= ist.lock_layer:
                    continue
                new_comp = get_comp(s.comp_name)
                if new_comp and _core_reachable(new_comp, gs, visible):
                    ist.phase = 'weak'
                    ist.weak_comp = ist.locked_comp
                    ist.locked_comp = ''
                    ist.lock_layer = 0
                    ist.transition_pair = ()   # weak 不辖(ADR-0367,同 scope 契约)
                    ist.revoke_evidence = {}   # 出口②非证据组 A/B 通道(字段契约)
                    ist.last_event = f'revoke:higher:{s.comp_name}(L{s.layer})'
                    revoked = True
                    break   # 「直至新信号」——本轮撤,下轮新信号再锁


    if ist.phase == 'locked' and plane_of(gs) == 1:
        # ADR-0367:①锁局过渡对随资产重派生(同 p1_pair 语义——
        # 「变体按来牌选」[20],非 pivot)。方向稳定性由 ADR-0616 四层
        # 谓词结构承载(门槛先行+在任优先单席易手+合成中性排序维+
        # 可行性门),非「支持度只增」资产单调性假设——该前提已被
        # sim 实证证伪(卖出/合成降计数,ADR-0616 §3,ADR-0357 修订)。
        # [23] 冻结语义辖终局线,不辖过渡副方向;在任 I = 现值
        # transition_pair(域内重评,先于本次计票)。
        pair = _derive_p1_pair(gs, incumbent=ist.transition_pair,
                               registry=registry, session=session)
        if pair != ist.transition_pair:
            ist.transition_pair = pair
            ist.last_event = ('lock_pair:' + '+'.join(pair)) \
                if pair else 'lock_pair:wait'

    if ist.phase in ('unlocked', 'weak') and not revoked:
        # P2 信号供给可行性缓锁门(锁线可行性批):候选信号线的核心
        # 不在店/在手 ∧ 线完成率 G ≤ ε ⇒ 本轮不锁(与 H1 环境判据同款
        # 「缓锁」语义,只辖主动选线,已锁线不辖)。核心在店的信号不辖
        # ——当轮可买,P25「核心出现即买」的锁线价值优先,且买入后
        # 缺件集即缩。辖域=plane==2(vd_p2_loss 血预算与 7 轮视界都是
        # P2 量;P1 配方锁/P3 强锁语义不动)。防的是出口③降级后的
        # 立即重锁死循环与 ①②亲和信号把方向锁进供给空缺线(R5 死亡
        # 局 5 条不同锁线全部低供给:任何线都可能供给不济,锁前先验
        # 可达性)。
        if plane_of(gs) == 2:
            _reg_f2 = registry or DEFAULT_REGISTRY
            _n0 = len(sigs)
            # G6 观测分键(设计稿 §6):信号存活至缓锁门但被 G≤ε 剔除。
            # 濒死带定向观测(设计稿 §2.3,只计数不定谳):濒死带 = 血预算
            # 轮数 ⌈hp/vd_p2_loss⌉ == 1(零新参数,与 p2_supply_horizon 血
            # 预算支同式;G 数值分布不入计数容器,走既有 revoke_evidence
            # 遥测面)。授权设计(濒死换向豁免)出辖设计稿 §12-7 并案批,
            # fail-closed 前行为零变更。
            _nd = _near_death_band(gs, _reg_f2, session)
            if _nd:
                _bump_obs(st or session, 'neardeath_direction_obs_frame')
            sigs = [s for s in sigs
                    if _p2_signal_supply_ok(gs, s, session, _reg_f2,
                                            visible)]
            if len(sigs) != _n0:
                log.info('[cw][intention] P2 供给可行性缓锁 %d→%d 信号',
                         _n0, len(sigs))
                _bump_obs(st or session, 'p2_supply_gate_cull')
                if _nd:
                    _bump_obs(st or session, 'neardeath_direction_obs_supply_cull')
        # H1 锁线环境判据(行为无条件化):累积型线强环境不命中(False)的信号
        # 本轮不锁(缓锁——「无环境不选」只辖**主动选线**,已锁线与判据
        # 不辖(None)/信息缺失帧不拦;观察期=line_env_lock_min_round)。
        # 已锁分支(上方 locked)有意不过此滤:环境缺失不没收已锁线
        # (accumulator_family §3 同义)。
        _reg_env = registry or DEFAULT_REGISTRY
        if round_num_of(gs) >= _reg_env.line_env_lock_min_round:
            _n0 = len(sigs)
            sigs = [s for s in sigs
                    if _line_env_qualified(gs, s.comp_name) is not False]
            if len(sigs) != _n0:
                log.info('[cw][intention] 环境判据缓锁 %d→%d 信号(affixes=%s)',
                         _n0, len(sigs), gs.enemy_affixes.value)
        # P1 过渡配方锁(ADR-0357):P1 的锁定产物=体系对;
        # ②③④信号不再锁终局 comp(终局 comp 锁定移至 P2+)——
        # 只保留①类资格通道(直通终局线资格,ADR-0338/0341 语义零改动)。
        # 方向产物=按手上资产派生的体系对(transition_combos 两两组合)。
        if plane_of(gs) == 1:
            sigs = [s for s in sigs
                    if _direct_line_qualified(gs, s.comp_name)]
            # ── 命题 1b form_ok 冻结状态机(ADR-0616 §2.2)──
            # 帧序:①超窗出口(F=True 时先判,解冻后本帧重派生照走)
            # → ②重派生(F=True 抑制,方向= frozen_pair;F=False 帧走
            # 在任优先算子+命题 3 可行性门 §2.1/§2.4)→ ③置位评估
            # (事件闩)。解冻闭集(p1_pair 域恰三项):超窗出口(①)/
            # 位面 exit_p1(下方 elif)/comp 锁定取代(_lock 域退出类)。
            _unfroze_this_frame = False
            if ist.p1_pair_frozen and ist.p1_pair_frozen_pair:
                over, e_f, r_rem = _p1_pair_overwindow(
                    ist.p1_pair_frozen_pair, gs, session, registry)
                if over:
                    # 出口①触发:解冻 + 封印该对(防「出口→解冻→保持→
                    # 复位→再触发」逐帧空转环);本帧重派生按派生语义执行,
                    # 在任保持帧对保持且 F=False,直至新 form_ok 帧再闩。
                    _unfroze_this_frame = True
                    ist.p1_pair_refreeze_hold = ist.p1_pair_frozen_pair
                    ist.p1_pair_frozen = False
                    ist.p1_pair_frozen_pair = ()
                    ist.last_event = (
                        f'p1_pair:unfreeze_overwindow'
                        f'(E={e_f:.2f},R_rem={r_rem})')
            if ist.p1_pair_frozen:
                # 冻结的是方向不是板面:买入/部署继续服务 frozen_pair,
                # 重派生被抑制(p1_pair 钉在 frozen_pair 上)。
                pair = ist.p1_pair_frozen_pair
                if pair != ist.p1_pair:
                    ist.p1_pair = pair
                    ist.last_event = 'p1_pair:' + '+'.join(pair)
            else:
                # 在任优先单席易手(ADR-0616 §2.1,I=现值 p1_pair 先于
                # 本次计票)+ 命题 3 可行性门后置合取(§2.4:仅辖换席
                # 候选;空窗首进/空席填充/在任保持不辖门)。registry/
                # session 透传 = 单体系点火渐进通道的 E 估计器输入
                # (_progressive_second_seat;与 gate 估计同源同参)。
                pair, cand = _p1_pair_eased(gs, ist.p1_pair,
                                            registry=registry, session=session)
                gate_e: float = 0.0
                gate_r: int = 0
                gate_denied = False
                if cand is not None:
                    ok, gate_e, gate_r = _p1_pair_gate(
                        cand, gs, registry, session)
                    if ok:
                        pair = cand
                    else:
                        gate_denied = True
                fp_v: float | None = None
                if ist.p1_pair_refreeze_hold:
                    if pair != ist.p1_pair_refreeze_hold:
                        ist.p1_pair_refreeze_hold = ()   # 换向解封
                    else:
                        _t = pair_target_comp(pair)
                        fp_v = (form_progress(_t,
                                              gs)
                                if _t is not None else 0.0)
                        if fp_v < 1.0:
                            # fp 回落 = 方向丢失;此后再达成才是新
                            # form_ok 事件,允许再闩(§2.2 清除后段)。
                            ist.p1_pair_refreeze_hold = ()
                        elif not _unfroze_this_frame:
                            # 超窗在任保持帧类(F=0 期)的路由读数
                            # (§2.4「保持+pair_gate 路由读数,如实显影」;
                            # 出口帧本身保留 unfreeze 事件不覆写)。
                            ist.last_event = ('pair_gate:hold('
                                              + '+'.join(pair) + ')')
                if gate_denied:
                    # 门拒 = 保持原对 + pair_gate 拒因分键(§2.4;
                    # 门拒帧派生对必等于在任对,p1_pair 字段零写入)。
                    ist.last_event = (f'pair_gate:deny(E={gate_e:.2f},'
                                      f'R_rem={gate_r})')
                elif pair != ist.p1_pair:
                    ist.p1_pair = pair
                    if cand is not None and pair == cand:
                        # 过门换席帧走 pair_gate 路由子键(E/R_rem 入键,
                        # ADR §4 事件分键条款三子键之一)。
                        ist.last_event = ('pair_gate:route:' + '+'.join(pair)
                                          + f'(E={gate_e:.2f},'
                                          f'R_rem={gate_r})')
                    else:
                        ist.last_event = ('p1_pair:' + '+'.join(pair)) \
                            if pair else 'p1_pair:wait'
                # 置位评估(事件闩):空对永不置位;封印期内不闩。
                if pair and not ist.p1_pair_refreeze_hold:
                    if fp_v is None:
                        _t = pair_target_comp(pair)
                        fp_v = (form_progress(_t,
                                              gs)
                                if _t is not None else 0.0)
                    if fp_v >= 1.0:
                        ist.p1_pair_frozen = True
                        ist.p1_pair_frozen_pair = pair
                        ist.last_event = 'p1_pair:freeze:' + '+'.join(pair)
            # 观测快照(唯一写入端):最新非空派生对冻结留档,供 P2 期
            # promote_candidates 消费(p1_pair 本体在 exit_p1 清空,见下)。
            if pair and pair != ist.p1_pair_frozen_obs:
                ist.p1_pair_frozen_obs = pair
        elif ist.p1_pair:
            # 进 P2:配方锁退场(解冻闭集出口②「位面末」,清除 ⟹ F 同帧
            # 归 0),comp 锁定通道照旧(P2+ 锁定产物=终局 comp)
            ist.p1_pair = ()
            ist.p1_pair_frozen = False
            ist.p1_pair_frozen_pair = ()
            ist.p1_pair_refreeze_hold = ()
            ist.last_event = 'p1_pair:exit_p1'
        best = _best_signal(sigs)
        if best is not None:
            _lock(ist, gs, best)
        elif ist.phase == 'weak':
            ist.last_event = ist.last_event or 'weak:hold'
        # 无信号:保持 unlocked——囤货方向落三臂判据(hoard_target_set 处理)


    # 强制锁线(位面入口无意向;点0〔修N4〕对象限定)。经济冻结批扩 P2:
    # P2 开局必须有目标(目标移交/重 assignment)——P1 配方锁在 P2 退场
    # (p1_pair:exit_p1)后,若信号未锁(unlocked),旧形态落⑤兜底囤货但
    # target_comp=None,准备域决策引擎无方向空转;现在 P2 unlocked 帧
    # 按「weak_planes 过滤 ∧ 核心可达 ∧ 资产最厚」强制 assignment(同 P3
    # 语义)。P3 起维持原辖域(phase!='locked');P2 收窄到 unlocked:
    # weak 态是撤销机器在册的意向降级,强制锁会踩掉其「直至新信号」语义。
    # 位面强锁候选同过 weak_planes 过滤(P3 旧分支未滤,同病灶③面)。
    # P2 无可达候选 ⇒ 保持 unlocked(P86 三臂判据接管囤货方向:甲臂空帧
    # 由乙臂枢纽期权/丙臂守息缺省承接,位面余量尚在,不降格终局;
    # 降格=终局不可达判定,归 P3)。
    # P2 移交守卫:撤销当轮(出口①/②/③)不接同一轮的移交重锁——
    # 「状态机一回合最多一次转移」纪律(revoked 注);下一轮由移交通道
    # 正常重锁(P3 强锁辖域不受本守卫影响,维持既有语义)。
    _p2_handoff = (plane_of(gs) == 2 and ist.phase == 'unlocked'
                   and not revoked)
    if (plane_of(gs) >= 3 or _p2_handoff) and ist.phase != 'locked':
        # G7/G8 观测分键(设计稿 §6):移交帧分母;候选空帧(handoff_lock
        # 零发射的直接断点);濒死带出口去向;晋升候选集纯派生非空率
        # (G8,输入 = p1_pair_frozen_obs,零行为)。与 G5/G6 分键交叉
        # = 「整局零锁定」摆动局可逐门分解断点(禁合并单键)。
        if _p2_handoff:
            _bump_obs(st or session, 'p2_handoff_frame')
            if _near_death_band(gs, registry, session):
                _bump_obs(st or session, 'neardeath_direction_obs_handoff_frame')
        _reg_h = registry or DEFAULT_REGISTRY
        if _p2_handoff and ist.p1_pair_frozen_obs:
            _bump_obs(st or session, 'promote_candidate_frame')
            if promote_candidates(gs, ist, session, _reg_h, visible):
                _bump_obs(st or session, 'promote_candidate_nonempty')
        # P2 移交候选补「锁线可行性」门(锁线可行性批):G > ε 才可锁
        # ——锁线前先验证可达性(供给概率×剩余轮×血预算,注册表派生
        # 零新参数),不可行线不进强锁候选;全不可行 ⇒ 无候选 ⇒ 保持
        # unlocked(⑤兜底语义=「降级目标」面,不降格终局)。
        # P3 分支不动(强锁/降格终局辖域原语义,本批只辖 P2)。
        cands = [c for c in _v2_comps()
                 if c.name not in ist.evicted
                 and plane_of(gs) not in (c.weak_planes or ())
                 and _core_reachable(c, gs, visible)
                 and (plane_of(gs) != 2
                      or line_completion_feasibility(
                          gs, c, session, _reg_h, visible)
                      > _reg_h.revoke_miss_tolerance_eps)]
        if cands:
            best = sorted(
                cands,
                key=lambda c: (-_asset_thickness(c, gs),
                               encounter_window_rounds(intention_core(c), level_of(gs))),
            )[0]
            _lock(ist, gs, IntentionSignal(1, 'forced', best.name,
                                              '资产最厚', 1.0), forced=True)
            if _p2_handoff:
                # 移交锁与 P3 强制锁分事件标签(判读可辨「P2 开局移交」与
                # 「P3 入口强制」;标签风格同 last_event 'p1_pair:' 族)。
                ist.last_event = 'handoff_lock:' + best.name
        elif plane_of(gs) >= 3:
            # 全部不可达 → 降格终局:四体系过渡板深档强化+通用骨架满配
            ist.demoted_endgame = True
            ist.phase = 'unlocked'
            ist.locked_comp = ''
            ist.revoke_evidence = {}   # 降格不经撤销,证据随之失效
            ist.last_event = 'demote:endgame'
        elif _p2_handoff:
            # G7 观测分键:候选空帧——unlocked 帧零候选 ⇒ handoff_lock
            # 零发射(「整局零锁定」摆动的最直接断点;设计稿 §6)。
            _bump_obs(st or session, 'p2_handoff_cand_empty')
            if _near_death_band(gs, _reg_h, session):
                _bump_obs(st or session, 'neardeath_direction_obs_handoff_empty')

    # 锁定率帧计数(设计稿 §6「锁定率入批统计披露」;分母 = 意向驱动帧,
    # 分子 = 帧末 phase=='locked';按位面分列,与 cw_batch_stats 的
    # planes/locked_frames 同域口径。只承归因:锁定率与结局无单调关系,
    # 禁作优化目标。生产驱动面 = flow.CwFlowStrategy._refresh_direction
    #(ADR-0583 内化;本模块 drive_intention 生产调用点已清零,保留作
    # 纵深防御),共用 strategy_state_of(session).v3_intention_key 段级重入守卫 ⇒ 每 game-round 恰一次)。
    _plane_key = f'p{min(max(1, plane_of(gs)), 3)}'
    _bump_obs(st or session, f'intention_frame_{_plane_key}')
    if ist.phase == 'locked' and ist.locked_comp:
        _bump_obs(st or session, f'intention_locked_frame_{_plane_key}')
    return ist


def _line_hoard(comp: Comp) -> tuple[set[str], set[str]]:
    """意向线囤货采购集(目标件定义节 class2 口径的 v1 落地):

    角色件 = core_chars ∪ shared_chars ∪ 替班者 ∪ 羁绊成员(form_tiers/sub_tiers
    键阵营下的注册表成员);装备件 = derive_key_equips(到人配方投影)− equip_taboos
    (具名禁忌;类级禁忌如「护盾件(类)」由买侧/装备层消费,本层不展开)。
    """
    chars = set(comp.core_chars) | set(comp.shared_chars)
    for sub in comp.substitute_plan:
        if sub.get('替班者'):
            chars.add(sub['替班者'])
    factions = set(comp.form_tiers) | set(comp.sub_tiers)
    if factions:
        for name, c in CHARACTERS.items():
            # W65 修法2(ADR-0323):目标集判定用「阵营 ∪ 流派」全集与档位键
            # 作交集——旧版只查 c.factions,而档位键常含**流派系羁绊**
            # (万敌单C form_tiers 燃血=flows、DOT 持续伤害、黄泉减益、击破等),
            # flows 成员(刃/镜流/布洛妮娅 等)被目标集排除 → 锁定线采购面残
            # (W64 Ring1:燃血 8 成员 3 名缺位)。泛化修正,非万敌特判
            # (candidates 的 _char_factions 同式全集口径)。
            if (set(c.factions) | set(c.flows)) & factions:
                chars.add(name)
    taboos = set(comp.equip_taboos)
    equips = {e for e in derive_key_equips(comp) if e not in taboos}
    return chars, equips


# ===== P86 无目标期三臂判据(落码批;命题/证明单一源 =
# docs/develop/sr_od/application/currency_war/proofs/p86-no-target-period-fund-allocation.md
# (正本 §2/§4)+ p86-proof-batch.md(证明批 §3/§4/§6))=====
# 辖域 = p2plus 无目标期帧(商店决策帧 ∧ target_comp=None ∧ 意向供给在场
# ∧ 未降格终局;活跃域 = 位面 2,证明批引理 Z)。p1_gap/p1_lock_band 显式
# 出辖(证明批 §4.1 必答⑥裁决);weak/demoted_endgame 分带仍走跨线骨架
# (正本 §6.2-4,不在退役面)。
#
# 三臂:甲臂(方向化囤货)= 候选机器强锁门逐字判活的方向集(定理 A);
# 乙臂(枢纽期权)=「覆盖数 ≥ 2 ∧ 非单卡注册身份」资格核(定理 B1/B2/B5);
# 丙臂(换现守息)= 两臂皆空帧缺省(命题 C,辖买卡买面与卖面资格,
# 不辖升级/刷新既有授权)。判据零新数值:ε 复用机器常量
# revoke_miss_tolerance_eps,覆盖数边界 2 = 单线依赖否定的结构量(定义值
# 非阈值,随命题文本声明)。

K_FALLBACK_SOURCE_THREE_ARM: str = 'three_arm'
"""p2plus 带合法空的来源证据 token(契约维度,证明批 §4.6-2):k_fallback
空集仅在 source 标明判据臂评估产出时放行;无来源空 = 「回退字面量空元组
但保留声明」复发形态,违例。单一源 = 本常量(contracts 契约面同值引用)。"""

_NO_TARGET_HUB_MIN_COVER: int = 2
"""乙臂资格核覆盖数边界(证明批 §3.2 定理 B5:单线依赖否定在身份档商集
上的补集边界)。定义量非调参阈值——「2」= 覆盖数 ≥ 2 即不依赖任何单一线,
随命题文本声明,禁按经验常数理解或调整。"""


def structural_candidate_lines(gs: GameState,
                               ist: IntentionState) -> frozenset[str]:
    """𝕃(f) 结构候选线集(证明批 §3.2 定义):

    只施加两类排除——意图稳定排除(``ist.evicted``,意向层显式出局的线)与
    注册表静态排除(``weak_planes``,注册表数据);**不施加**任何供给筛
    (``_core_reachable``)或概率筛(G)——理由 = 乙臂跨帧期权价值恰恰
    spanning 判死线的后续复活帧,解耦独立性见定理 B2-3;把帧变量筛放进
    覆盖集会让枢纽资格随帧闪烁,乙臂退化成甲臂的影子筛。
    """
    return frozenset(
        c.name for c in COMP_LIBRARY
        if c.name not in ist.evicted
        and plane_of(gs) not in (c.weak_planes or ()))


def hub_covered_lines(gs: GameState, ist: IntentionState,
                      char_name: str) -> frozenset[str]:
    """枢纽 h 的覆盖集 C_h(f)(char_routes 复用网络口径,core∪shared 计入)
    与结构候选线集的交集;乙臂资格核与同帧仲裁第一层的共享输入。"""
    routes = char_routes().get(char_name, set())
    return frozenset(routes & set(structural_candidate_lines(gs, ist)))


def _build_char_declaration_index() -> dict[str, int]:
    """角色卡注册表声明序索引表(模块级一次构建;COMP_LIBRARY 静态)。"""
    idx: dict[str, int] = {}
    for comp in COMP_LIBRARY:
        for name in list(comp.core_chars) + list(comp.shared_chars):
            if name and name not in idx:
                idx[name] = len(idx)
    return idx


_CHAR_DECL_INDEX: dict[str, int] = _build_char_declaration_index()


def char_declaration_index(name: str) -> int:
    """角色卡注册表声明序索引(P86 同帧仲裁第三层的确定性序单一源,
    证明批 §4.4:剩余并列按注册表声明序,纯确定性零语义承载)。

    坐标系 = COMP_LIBRARY 逐套 core∪shared 首现序(与 hub_option_names
    枚举序同源同一构建式,禁消费方第二套排序);取值时机 = 导入期快照
    (注册表静态)。不在册名(散件/识别噪声)返回 len(全集) 垫底。"""
    return _CHAR_DECL_INDEX.get(name, len(_CHAR_DECL_INDEX))


def hub_option_names(gs: GameState, ist: IntentionState) -> tuple[str, ...]:
    """乙臂资格核(P86 证明批 §3.2 终裁形态;定理 B5):

    HUB(h) ⟺ cov(h) ≥ 2 ∧ h ∉ CORE_SINGLE_CARD_REGISTRY——覆盖数按
    覆盖集 C_h(f)(注册表派生)计;银狼LV.999 型注册单卡依赖核心的
    「覆盖 2」是家族内计数不构成跨线灵活性,身份排除结构性必要(定理
    B5 三层:语义/通道[防与规则③双通道注册]/判例),禁档间谓词复用
    (正本 §6.2-3:line_identity_tier 三分档是身份单一源)。

    输入面 = (COMP_LIBRARY, ist.evicted, plane_of(gs), weak_planes,
    CORE_SINGLE_CARD_REGISTRY)——G/``_core_reachable`` 禁入(定理 B2
    解耦独立性的实现守卫,静态锁 = test_cw_no_target_three_arms.py 锁 2)。
    返回序 = 注册表声明序(逐套 core∪shared 首现序;同帧仲裁第三层的
    确定性序,证明批 §4.4)。
    """
    routes = char_routes()
    lines = structural_candidate_lines(gs, ist)
    out: list[str] = []
    seen: set[str] = set()
    for comp in COMP_LIBRARY:
        for name in list(comp.core_chars) + list(comp.shared_chars):
            if not name or name in seen:
                continue
            seen.add(name)
            if name in CORE_SINGLE_CARD_REGISTRY:
                continue
            if len(routes.get(name, set()) & lines) >= _NO_TARGET_HUB_MIN_COVER:
                out.append(name)
    return tuple(out)


def arm_a_live_direction(gs: GameState, ist: IntentionState,
                         session: StrategySession | None = None,
                         registry: DecisionV2Registry | None = None,
                         visible: set[str] | None = None) -> str:
    """甲臂资格(P86 证明批 §3.1 定理 A):候选机器强锁门**原样逐字**
    放行的方向集的首方向。

    三要素逐字继承位面 2 移交候选门(:1600-1607 同式):同一谓词
    ``line_completion_feasibility``、同一常量 ``revoke_miss_tolerance_eps``、
    同一 plane 条件语义(``plane != 2 or G > ε``);方向选择 = 机器自身
    选择序(资产厚度降序 → 再遇窗口,与强锁分支同式,证明批 §4.4 第二层
    机器原生序)。机器判死(G ≤ ε)方向按公理 1 fail-closed 不授权囤货,
    零新数字;G=0 是判死的极端实例不是定义。已知缺口(缓锁豁免角漏授,
    保守向、机器锁后 M2 自纠)= 证明批 §3.1-4 申报,显影分键归消费位。

    **promote_candidates 禁入本调用链**(G8 观测载体,码内明文禁入任何
    行为消费点,cw_intention.py 消费位注;正本 §2.2 F11)。"""
    reg = registry or DEFAULT_REGISTRY
    vis = _visible_chars(gs) if visible is None else visible
    cands = [c for c in _v2_comps()
             if c.name not in ist.evicted
             and plane_of(gs) not in (c.weak_planes or ())
             and _core_reachable(c, gs, vis)
             and (plane_of(gs) != 2
                  or line_completion_feasibility(gs, c, session, reg, vis)
                  > reg.revoke_miss_tolerance_eps)]
    if not cands:
        return ''
    return sorted(
        cands,
        key=lambda c: (-_asset_thickness(c, gs),
                       encounter_window_rounds(intention_core(c), level_of(gs))),
    )[0].name


def arm_a_corner_names(gs: GameState, ist: IntentionState,
                       session: StrategySession | None = None,
                       registry: DecisionV2Registry | None = None,
                       visible: set[str] | None = None) -> tuple[str, ...]:
    """甲臂漏授角方向集(证明批 §3.1-4/§6 增量 7 的判读显影输入):

    plane==2 无目标帧上,方向 d 过 evicted/weak/_core_reachable 三门但
    G(d) ≤ ε 判死,且意向核心在店/在手——该角机器缓锁门(core 可见短路
    G)构造可达,甲臂按强锁门逐字不授权。与无信号判死是两个可辨状态,
    独立分键,禁混桶。"""
    reg = registry or DEFAULT_REGISTRY
    vis = _visible_chars(gs) if visible is None else visible
    out: list[str] = []
    if plane_of(gs) != 2:
        return tuple(out)
    for c in _v2_comps():
        if c.name in ist.evicted or plane_of(gs) in (c.weak_planes or ()):
            continue
        if not _core_reachable(c, gs, vis):
            continue
        core = intention_core(c)
        if core and core in vis \
                and line_completion_feasibility(gs, c, session, reg, vis) \
                <= reg.revoke_miss_tolerance_eps:
            out.append(c.name)
    return tuple(out)


@dataclass(frozen=True)
class NoTargetArms:
    """三臂判据帧输出(无目标期帧的资金配置判定件;消费面 = hoard_target_set
    终支与 mandate_v1 商店域乙臂发射位)。

    - ``direction``:甲臂方向线名('' = 判死全灭/甲臂空);
    - ``char_targets``:判据臂囤货成员集(甲臂判活 = 方向采购集;甲臂空
      = 空集——丙臂守息带合法空,契约经 k_fallback_source 证据放行);
    - ``hub_names``:乙臂资格核过枢纽名(注册表声明序;出域帧恒空);
    - ``corner_names``:甲臂漏授角方向名(判读显影,行为零消费)。
    """

    direction: str
    char_targets: frozenset[str]
    hub_names: tuple[str, ...] = ()
    corner_names: tuple[str, ...] = ()


def no_target_arms(gs: GameState, ist: IntentionState,
                   session: StrategySession | None = None,
                   registry: DecisionV2Registry | None = None,
                   visible: set[str] | None = None) -> NoTargetArms:
    """三臂帧判定入口(无目标期帧域守卫内聚:phase=='unlocked' ∧ 未降格
    ∧ 位面 ≥ 2;p1 两带与 weak/demoted 分带显式出辖,出域帧返回空甲乙)。"""
    if (ist.demoted_endgame or ist.phase != 'unlocked'
            or plane_of(gs) < 2):
        return NoTargetArms('', frozenset())
    direction = arm_a_live_direction(gs, ist, session, registry, visible)
    hubs = hub_option_names(gs, ist)
    if direction:
        comp = get_comp(direction)
        if comp is not None:
            chars, _equips = _line_hoard(comp)
            return NoTargetArms(direction, frozenset(chars), hubs)
        return NoTargetArms('', frozenset(), hubs)
    return NoTargetArms('', frozenset(), hubs,
                        arm_a_corner_names(gs, ist, session, registry,
                                           visible))


def hoard_target_set(gs: GameState, ist: IntentionState,
                     session: StrategySession | None = None,
                     registry: DecisionV2Registry | None = None,
                     visible: set[str] | None = None) -> HoardTarget:
    """锁后效果接口:输出「囤货目标集合」供买侧消费([21]:只改囤货方向,不改板上)。

    - locked/forced:意向线采购集;
    - P1(ADR-0357):非 comp 锁定局 → 配方方向——体系对成员集
      (p1_pair)/四体系引擎件全集(p1_transition,空窗);
    - weak:只囤跨线骨架件(撤销后去向);
    - unlocked 无信号(P2+):P86 三臂判据——甲臂判活 = 机器强锁门逐字
      首方向采购集;甲臂空 = 空集(乙臂枢纽期权在商店域发射位获取,
      丙臂守息缺省)。
      session/registry/visible 缺省时 G 视界回退先验(裸调用/旧签名兼容)。
    - demoted_endgame:降格终局 = 通用骨架满配(四体系板深强化归点4/点6,不在本模块)。
    """
    if ist.demoted_endgame:
        return HoardTarget(frozenset(CROSS_LINE_SKELETON), frozenset(),
                           'demoted_endgame')
    if ist.phase == 'locked' and ist.locked_comp:
        comp = get_comp(ist.locked_comp)
        if comp is not None:
            chars, equips = _line_hoard(comp)
            return HoardTarget(frozenset(chars), frozenset(equips),
                               'forced' if ist.forced else 'locked')
    if plane_of(gs) == 1:
        # P1 配方方向(ADR-0357):体系对成员集;空窗=四体系全集。
        # 过渡装备随意([20] 装备语义:简易装备随便给,合成件归 final
        # key_equips 判定)——equip_targets 恒空。
        pair = ist.p1_pair or ()
        members = _pair_members(pair) if pair else _pair_members(_P1_PAIR_PREF)
        return HoardTarget(frozenset(members), frozenset(),
                           'p1_pair' if pair else 'p1_transition')
    if ist.phase == 'weak':
        return HoardTarget(frozenset(CROSS_LINE_SKELETON), frozenset(), 'weak')
    # P86 三臂(p2plus 无目标带;①面退役处置 = 替换为三臂判据,正本 §4.2):
    arms = no_target_arms(gs, ist, session, registry, visible)
    if arms.direction:
        comp = get_comp(arms.direction)
        if comp is not None:
            chars, equips = _line_hoard(comp)
            return HoardTarget(frozenset(chars), frozenset(equips),
                               'fallback_arm_a')
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

    返回 (成员集, 分带 token):分带 token 供消费域拼遥测计数键
    (shop 侧键名契约 'shop_k_fallback_<token>' 维持历史键名不变)。
    分带语义与 shop.py 旧内联派生逐款同源:
    - p1_gap:P1 空窗带(支持度 < 锁门槛)→ hoard 四体系引擎件全集
      (消「K 空→零买入→支持度永不涨」死锁环);
    - p1_lock_band:P1 锁线过渡带 → p1_early_pair 无门槛方向(在任算子,
      ADR-0616 §3.3 裁决①),派生空 ⇒ 链 hoard 全集兜底;
    - p2plus:P2+ → hoard 分带(unlocked=三臂判据[P86:甲臂方向集/合法空
      (丙臂守息,空集带 k_fallback_source 证据)]/weak=跨线骨架/
      demoted=骨架满配)。session/registry/visible 透传甲臂 G 门
      (缺省回退先验,与 hoard_target_set 同款)。"""
    if plane_of(gs) == 1:
        if p1_gap_window(gs):
            return hoard_target_set(gs, ist).char_targets, 'p1_gap'
        return (p1_early_pair_members(gs, ist)
                or hoard_target_set(gs, ist).char_targets), 'p1_lock_band'
    return (hoard_target_set(gs, ist, session, registry, visible)
            .char_targets, 'p2plus')


def committed_authority(state: GameState | None,
                        session: StrategySession | None) -> bool:
    """committed(已定型/非双轨期)权威判定(方向层单一派生源)。

    - **权威序**(任一成立即 True):
      ① ``state 位面 >= 2``——P2 起恒定型(语义边界沿用方向重估时代的
         定型边界 = 进位面 2,严于文档口径 P2-3;载体史见 ADR-0583 内化锚):
      ② ``strategy_state_of(session).v3_intention.phase == 'locked'``——意向状态机已锁线;
      ③ ``ist.p1_pair`` 非空——P1 配方锁已立(ADR-0357 产物形态)。
    - **缺供给帧 = 保守侧 False**(=双轨=攒息):ist 不可得/字段缺失时
      **禁止**缺省 True——True=已定型=激进侧,攒息门/双轨买门全开
      (供给点清单 D2:拔掉供给探针下必须落保守侧,变异锁钉住)。
    - 消费契约:全部消费点经本函数或 ``decision_v2.prep_brain
      .committed_from``(唯一读端,内部委托本函数)取值;
      state/session 侧双轨字段降级为兼容残留(读点归零,
      grep 守卫锁),写端退役随老栈(strategy 层)老栈退役(ADR-0466/0469)。
    - **state 形态 = 容器单例**(W6 波3 切换;plane 经 ``plane_of`` 读口)。
      波5 过渡兼容支(旧帧 plane 属性直读)已随 last_state 链
      退役批删除(本形态注即其退役指针,指针兑现);禁新消费点再喂
      旧帧或手造鸭子镜像(同型鸭子桥禁令,_PlaneShim 已随波3 消亡)。
    """
    if state is not None:
        if plane_of(state) >= 2:
            return True
    ist = getattr(strategy_state_of(session), 'v3_intention', None) if session is not None else None
    if ist is None:
        return False
    if getattr(ist, 'phase', '') == 'locked':
        return True
    return bool(getattr(ist, 'p1_pair', ()) or ())


def committed_from(session: StrategySession,
                   state: GameState | None = None) -> bool:
    """committed(已定型/非双轨期)唯一合法读端(R1,蓝图 §4.3;
    cw_recipe 决策中心消费它成 kernel→decision 断环边,§3.3-①d;体内仅委托
    本模块 ``committed_authority``,kernel 内自洽)。

    - 有现读 state(容器单例)→ 直取权威派生;
    - 无现读 state 的调用面:plane 取 session 容器单例(game_state_of),
      也不可得时仅凭 ist 判定(缺供给 = 保守 False,同 D2)。

    grep 守卫锁「session 侧双轨字段直读点归零(本函数之外)」;
    变异锁:拔掉意向供给(ist=None 且 plane<2)必须落 False 保守侧
    (穿透锁=test_cw_session_separation 的 committed_authority 直锁
    + test_cw_migration_direction_layer 对拍帧)。
    decision_v2.prep_brain 本名保留 import 重定向,消费方调用零改。
    """
    if state is not None:
        return committed_authority(state, session)
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of,
    )
    return committed_authority(game_state_of(session), session)


def drive_intention(gs: GameState, session: StrategySession,
                    registry: DecisionV2Registry | None = None) -> None:
    """意向状态机驱动点(P7 契约):每 game-round 恰一次。

    - 锚定 = 决策入口方向刷新(ADR-0583 内化后,唯一活跃生产驱动者 =
      flow.CwFlowStrategy._refresh_direction;本函数生产调用点已清零,
      键守卫保留作纵深防御——同一键面误驱动天然幂等);驱动键 =
      (plane, round_num),段级重入守卫 = strategy_state_of(session).v3_intention_key
      (与策略器方向刷新共享同一键面——并存天然幂等,
      同轮重入不重复计数,miss/冻结分母 = 轮不膨胀);
    - ist 归属(session 保留清单裁决,P4):``v3_intention`` 是跨轮状态机
      计数器族(miss_count/frozen_rounds/evicted/tracks),显式归 session
      保留清单;局级重置由「每局新建 StrategySession」保证,跨局零残留
      (行为锁 test_cw_migration_direction_layer);
    - registry 显式参数(P6):撤销阈值/门判据注入面直达状态机,禁在
      折叠后静默落缺省表——缺省 None 只用于无注入臂的缺省栈。

    (自 decision_v2.prep_brain 迁入意向域单一源;prep_brain 本名保留
    re-export,消费方调用零改。)
    """
    st = strategy_state_lazy(session)
    ist = st.v3_intention if st is not None else None
    if not isinstance(ist, IntentionState):
        if st is None:
            return   # 工厂未注册(第三方策略面):kernel 不代建,跳过驱动
        ist = st.v3_intention = IntentionState()
    key = (plane_of(gs), round_num_of(gs))
    if st.v3_intention_key == key:
        return   # 同轮已驱动:幂等出口(重入只保派生视图刷新,不计数)
    st.v3_intention_key = key
    update_intention(gs, ist, session, registry=registry)


def locked_buy_scope(ist: IntentionState | None) -> frozenset[str] | None:
    """锁定帧买侧目标约束基准(ADR-0359)。

    opportunistic/bond_fallback 买通道「目标/非目标」判定输入 =
    ``p1_pair``(非空时)∪ ``locked_comp`` 采购集(``IntentionState.p1_pair``
    的约束基准契约,本函数是该契约的单一实现);两者皆空(空窗/弱意向/
    降格终局)→ None(无锁定帧,不约束——[31]① 空窗期四体系全集是方向,
    不存在「非目标件」)。

    - P1 配方锁定帧 = ``_pair_members(p1_pair)``(体系对两体系全成员,
      含其二体系——对成员集本身即两体系的并);
    - comp 锁定帧(P1①资格通道 / P2+)= ``_line_hoard(comp)`` 角色采购集;
      **①锁局(P1)∪ 过渡对成员集(ADR-0367)**——二级囤货语义
      ([22]④):对件免 demote/免 final_fence,但不进 hoard 目标件集
      (comp 主序对副序,主方向与核心件优先级不动);
    - weak(撤销后去向=跨线骨架)/demoted_endgame 不辖:方向已撤或已
      降格,约束基准不存在(弱意向期的跨线骨架囤货本身不受本约束辖)。
    """
    if ist is None:
        return None
    scope: set[str] = set()
    if ist.p1_pair:
        scope |= _pair_members(tuple(ist.p1_pair))
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
    卖免面/刷新账不辖,见消费域的买面/卖免面拆分注释)。

    双源断裂机制:锁定帧的买入 membership 旧按
    ``predicates.line_members(target_comp)``(comp core∪shared)判,而
    锁线语义的采购集权威 = ``_line_hoard``(含 form_tiers∪sub_tiers
    档位键的阵营∪流派全集成员,W65 修法2 同口径)——实机对局
    g_20260905_035710 锁「列车同行」后,同阵营成员(开拓者·欢愉/
    丹恒·饮月,非该 comp core∪shared)被判 ``non_line``、M2 骨架义务
    买入被跳过,锁定帧自相矛盾(M2「锁线成员照买」,审查定性 = 实现
    断裂非设计缺口)。修复 = 锁定帧买入判定统一消费本函数,购买侧与
    锁定侧同源。

    集合构成 = ``p1_pair`` 成员(若设)+ ``locked_comp`` 采购集;**刻意
    不含 ``transition_pair``**(与 ``locked_buy_scope`` 的唯一差异):
    对件在 ADR-0367 分层里是二级囤货——免 demote/fence 的机会性囤货
    (受息律/预算辖),不是 M2 骨架义务(无条件照买),升格即越分层,
    故本函数不复用 ``locked_buy_scope`` 直取。需要完整约束基准(对件
    免 demote/fence 面)的消费方仍用 ``locked_buy_scope``。

    **容量可行截断(ADR-0647)**:``cap_hold`` 非 None 且
    |B| > cap_hold 时返回截断义务集 B'——序 = core∪shared ≻ (p1_pair ∪
    其余 hoard) 同级,级内 cost 升序、注册表声明序 tie-break
    (``_obligation_rank``)。结构依据 = 义务完成金流成本:低费义务先
    闭合(P41②/P76 甲 1★ 全额退净金 0 的可逆性不变量,低费成员往返
    动作成本最低),零自由参数。缺员面 missing(B') 可清空 ⇒ M2 终止
    条件恢复(停摆不动点解除);被截成员退出 M2 义务基座,
    其 M4/部署面保护必要性随之消失(义务基座 = M2 会重买的集合)。
    ``cap_hold=None`` = 宽集(兼容缺省,零漂移;容量不可得帧的
    fail-closed 方向 = 保宽,截断是收紧面不盲收)。

    触发条件 = ``locked_comp`` 非空(锁线状态已建立)。未锁帧(P1 配方
    锁帧 locked_comp 恒空,ADR-0357;空窗/weak/降格)→ 返回 None,
    消费方维持既有 ``line_members(target_comp)`` 口径——P1 无锁态行为
    零变化的边界锚。
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
    """截断级内序(ADR-0647):cost 升序,注册表声明序
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
    """容量可行截断(ADR-0647):core∪shared 优先全保
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
    """容量可行截断的容量上界单源(ADR-0647)。

    = ``BENCH_CAPACITY + max_units(level)``(现读;lv8 = 17 实用持有
    容量,旧固定分母 BENCH_CAPACITY+DEPLOYED_CAPACITY=19 高估,|B|=18
    已不可达而不告警)。缺读 fail-closed 方向 = 返回 None ⇒ 消费方保宽
    (现行为,零漂移端)——容量不可得帧不做截断收紧。

    state 形态 = 容器单型(读口 = level_of/max_units_of;None = 缺读,
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


def locked_line_recipe_floor_conflict(ist: IntentionState | None) -> bool:
    """锁定线语境豁免条件(1)(配方底线门;单一源,ADR-0564)。

    = ``ist.locked_comp`` 非空 ∧ ``get_comp`` 可解析 ∧
    ``comp.form_tiers.get('列车同行', 0)`` > ``RECIPE_FLOOR_TRAIN_CAP``
    (门封顶档,自 cw_deploy_logic import——本模块本就 import
    TRANSITION_TRAITS,顺向合法;helper 若落 cw_deploy_logic 反向
    import get_comp 成环,故驻本模块)。

    判据形态与 ``locked_buy_membership`` 同族(触发条件同为
    locked_comp 非空单判;不查 phase——``_lock`` 中 phase 与
    locked_comp 同点同置、清空路径同点清,不存在「locked_comp 非空而
    phase≠locked」的常态;若未来状态机引入该瞬态,消费面复审豁免
    条件,方向宁可少开)。只看 form_tiers 不看 sub_tiers:门冲突语义
    = **成型目标档**超封顶(sub_tiers 是副档目标;注册表无 sub_tiers
    含列车同行的 comp)。

    ⚠️ 禁改 scope 成员判:``locked_faction_scope`` = p1_pair ∪
    transition_pair ∪ locked_comp 主副档键——P1 配方锁(桥对)帧
    locked_comp='' 但 scope 非空,桥池列车目标档=2(=门封顶,无冲突,
    过渡纪律应全额生效);scope 成员判会把门在过渡期打开 = 重开
    r288 暴露面。本函数只读 locked_comp,结构上不可触达 p1_pair。

    失效安全(fail-safe,不依赖清空路径枚举完整):locked_comp 逐帧
    重读,任一清空路径(驱逐/撤销换 weak/撤销换 unlocked/降格终局,
    赋空点五处)或套名解析失败(get_comp 返 None)都自动关豁免;
    换线自动关豁免(fail-safe)。
    """
    if ist is None or not getattr(ist, 'locked_comp', ''):
        return False
    comp = get_comp(ist.locked_comp)
    if comp is None:
        return False
    return comp.form_tiers.get('列车同行', 0) > RECIPE_FLOOR_TRAIN_CAP


def locked_faction_scope(ist: IntentionState | None) -> frozenset[str] | None:
    """锁定帧的体系(羁绊键)集(ADR-0360;evolve 提案/部署围栏消费)。

    与 ``locked_buy_scope`` 同判据的**阵营口径**版本(off-lock
    evolve 提案的 target_factions 不含锁定 faction → 锁定目标件被
    execute_replacement 划进 old_line 整档解除——约束需要的是体系键不是
    件名):

    - P1 配方锁定帧 = ``p1_pair`` 体系键(希儿系展开=量子同频+贝洛伯格,
      与 ``_pair_members`` 同口径);
    - comp 锁定帧(P1①资格通道 / P2+)= ``locked_comp`` 主/副档键
      (``form_tiers`` ∪ ``sub_tiers``,与 ``_line_hoard`` 档位键同式);
      **①锁局(P1)∪ 过渡对体系键(ADR-0367,与 ``locked_buy_scope``
      同式扩位)**——对体系提案不再按 off-lock 降级/解除,protect 基准
      (cw_evolution 围栏/保留序)同步扩辖(R2:换血可以拆引擎不行);
    - 两者皆空(空窗/weak/降格终局)→ None(无锁定帧,不约束——[31]①
      空窗期四体系全集是方向,不存在「off-lock 提案」)。
    """
    if ist is None:
        return None
    keys: set[str] = set()
    if ist.p1_pair:
        for sys in ist.p1_pair:
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
            keys |= set(comp.form_tiers) | set(comp.sub_tiers)
    return frozenset(keys) if keys else None


def alloc_reason_consistency(session, target_faction: str = '',
                             target_comp_name: str = '') -> str:
    """执行侧目标 vs 意向层权威的一致性断言(纯函数,零行为;设计单一源 =
    执行分配器设计件 §2 正式范围):执行侧消费只读意向层权威
    状态,禁读自身缓存线名)。

    断言式:执行目标 ∈ 意向权威语义集 = 锁定体系集
    (``locked_faction_scope``)。与 cw_evolution._off_lock_opt 同判据的
    **断言面**(彼为约束面,本函数只观察不拦截)。

    - 意向载体缺失或无锁定帧(空窗/weak/降格终局,scope=None)→ ''
      ——弱意向期的跨线骨架/弱占位本身在语义集内,不辖;
    - comp 来源目标的主档键或目标 faction 与锁定体系集有交集 → '';
    - 否则返回脱节报警标签 ``'off_lock:<目标>'``(消费方 =
      execute_replacement 构造事务时的观察日志 + sim 检查网/测试锁)。
    """
    ist = getattr(strategy_state_of(session), 'v3_intention', None)
    scope = locked_faction_scope(ist if isinstance(ist, IntentionState)
                                 else None)
    if scope is None:
        return ''
    if target_comp_name:
        comp = get_comp(target_comp_name)
        if comp is not None and (set(comp.form_tiers) & set(scope)):
            return ''
    if target_faction and target_faction in set(scope):
        return ''
    return f'off_lock:{target_comp_name or target_faction}'

