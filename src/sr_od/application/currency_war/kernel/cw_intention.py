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
  交 dd-033 P2 移交重锁(可逆,不写 evicted)。分数涌现换线不进本模块。
- [23]/[21] 的 P1 时序面(ADR-0341):贯穿件 P1 可买可囤([21] bench 等窗口),
  但**终局专属线(锁线方向不含过渡引擎)在 P1 的③/④锁线证据被资格门拦下**——
  资格 = ①类(策略/环境亲和;transitions §1「拿到逆天投资策略才配锁直通线」);
  P2/P3 ③照旧([23] 路径不变,本门只收紧 P1 时机)。

**P1 过渡配方锁(ADR-0357)**:位面 1 的锁定产物=过渡配方体系对
(transition_combos 两两组合;[20] 过渡是配方不是散买),终局 comp 锁定
只保留①类资格通道,P2+ 照旧锁 comp。(配方锁行为无条件,
见本文件「P1 锁线资格门」节注释)。

模块构成:
- ``detect_signals(state)``:信号分层判定(①策略驱动/②类专属羁绊/③核心卡/
  ④资源/⑤由解析侧兜底,本函数不发⑤信号);
- ``IntentionState``:锁线/撤销状态机(未锁/锁定/弱意向 + 降格终局标记),
  ``update_intention(state, ist)`` 每回合驱动;
- ``hoard_target_set(state, ist)``:锁后效果接口——输出囤货目标集合(角色件 +
  装备件),买侧唯一消费面。

数值标注「设计推断,sim 校准」的常量属 strategy_v4「悬而未决·摆动域」,
不写死语义进文档。
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    refresh_prob,
)
from sr_od.application.currency_war.kernel.cw_comps import (
    COMP_LIBRARY,
    STRONG_ENV_MECHS,
    V2_FAMILIES,
    Comp,
    augment_affinity,
    augment_env_affinity,
    derive_key_equips,
    get_comp,
    merged_mechanic_tables,
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import TRANSITION_TRAITS
from sr_od.application.currency_war.kernel.cw_line_switch import (
    e_rounds,
)
from sr_od.application.currency_war.kernel.cw_plane_table import (
    NODES_PER_PLANE,
    TOTAL_NODES,
)
from sr_od.application.currency_war.kernel.cw_plugins import (
    cross_line_skeleton as _cross_line_skeleton,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
)
from sr_od.application.currency_war.kernel.cw_state import (
    GameState,
    iter_occupied_deployed,  # ADR-0392 helper 导入
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
# (SKELETON_ASSET_WEIGHT=0.5 已退役 2026-09-04,ADR-0519:设计推断无标定链,
# 「未证即退役」;保守缺省 0 = 资产厚度只数终局件星级当量,纯游戏定义计数。)
FAMILY_BOND_MIN_COUNT: int = 2
"""②类专属羁绊信号阈值:板上+bench 该羁绊计数 ≥ 此值 → 家族信号。

【注】游戏定义量:信号族专属羁绊(银河学者/夜之半神/列车同行等)的
羁绊首档均为 2 人(cw_factions 注册表 counts[0]),阈值 = 信号族最小
激活档,非经验拟合(ADR-0519 组4-B 复核)。"""

# ⑤无信号兜底线(comp_definitions_v2 欢愉族·绯英档:「门槛全游戏最低,
# 6 级搜绯英三星,无信号时的默认落点」)。四体系顺来牌支归点2,P1 侧不在本模块。
FALLBACK_COMP_NAME: str = '绯英欢愉'

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
    dd-034 候选①线级同构)。"""


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

    - 读口 = ``session.v3_intention.p1_pair``——四体系键的二元组,按
      ``_P1_PAIR_PREF`` 序规整,非空即「P1 锁定帧目标=该体系对」;
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
    - 派生口径与 ``p1_pair`` 同源(``_derive_p1_pair``,四体系支持度
      top-2,随资产重派生)——两字段是同一口径在不同锁定帧的实例;
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
    """R3 断供驱逐集(配方对域;**已退役恒空**,ADR-0519:断供驱逐分支
    随未证阈值退役,本字段仅留序列化兼容与派生 exclude 参数占位)。"""
    pair_drought: dict[str, int] = field(default_factory=dict)
    """体系级断供计数器(体系键 → 连续无新件在店轮数;成员在店即清零,
    无商店语境轮冻结)。ADR-0519 后仅遥测,不再触发驱逐。"""
    shop_supply_streak: dict[str, int] = field(default_factory=dict)
    """体系级在店供给计数器(体系键 → 连续在店轮数;不在店清零,无商店
    语境轮冻结)。ADR-0519 后仅遥测(旧「驱逐加速门」已随驱逐退役)。
    serialize_intention 全量序列化自动携带。"""
    # (supply_drought 方向侧供给衰减计数器已随兑现链开关族删除——旧方案
    #  清退批,清查报告 OLD_MIX_AUDIT §1.3。)
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


def _visible_chars(state: GameState) -> set[str]:
    """当前可见角色规范名:shop 在店 + bench/deployed 到手(识别层已归一)。"""
    names: set[str] = set()
    for card in state.shop:
        if card.name:
            names.add(card.name)
    for bc in list(state.bench) + list(state.deployed):
        if bc is not None and bc.char_id:
            names.add(bc.char_id)
    return names

def _bond_counts(state: GameState) -> dict[str, int]:
    """板上 + bench 的羁绊计数(board 已含 deployed 聚合;bench 逐件加)。"""
    counts: dict[str, int] = dict(state.board)
    for bc in state.bench:
        if bc is not None and bc.faction and bc.faction != '?':
            counts[bc.faction] = counts.get(bc.faction, 0) + 1
    return counts


def plane_remaining_nodes(state: GameState, session=None) -> int:
    """位面内剩余节点数(含当前轮;冻结超限的对照量)。

    ADR-0366:位面轮数按 ``nodes_of_plane(session)`` 本位面真值(P2=7;
    旧按全局 9 计使 P2 冻结超限对照量虚高 2 轮)。session 缺省 None →
    回退 P1 先验(裸调用/旧签名兼容)。
    """
    from sr_od.application.currency_war.kernel.cw_plane_table import nodes_of_plane
    n = nodes_of_plane(session) if session is not None else NODES_PER_PLANE
    r = min(max(1, state.round_num), n)
    return n - r + 1


def total_remaining_nodes(state: GameState) -> int:
    """全局剩余节点数(可达性对照量;封顶 3 位面)。"""
    p = min(max(1, state.plane), 3)
    r = min(max(1, state.round_num), NODES_PER_PLANE)
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


def _core_reachable(comp: Comp, state: GameState,
                     visible: set[str]) -> bool:
    """强制锁线对象限定:核心已在手 或 再遇窗口期望 ≤ 剩余节点数(点0〔修N4〕)。"""
    core = intention_core(comp)
    if not core:
        return False
    if core in visible:
        return True
    return encounter_window_rounds(core, state.level) <= total_remaining_nodes(state)


def _direct_line_qualified(state: GameState, comp_name: str) -> bool:
    """直通终局线资格判定(ADR-0338)。

    资格单一源 = 亲和表反查(**派生,不手写名单**):
    - 策略侧:任一持有策略 ``s ∈ state.active_strategies`` 在
      ``AUGMENT_COMP_AFFINITY`` 中指向该 comp(如 黑塔纪元→大黑塔银河学者);
    - 环境侧:``state.active_env`` 在 ``ENV_COMP_AFFINITY`` 中指向该 comp
      (如 银河学者概念股→大黑塔银河学者)。

    无任何表项的 comp(万敌单C/DOT队/黄泉线等)恒无资格 —— 它们的终局线
    只能由③核心卡(贯穿件到手,[23] 合法)或后续注册的资格项锁线。
    """
    for s in state.active_strategies:
        if comp_name in augment_affinity(s):
            return True
    return comp_name in augment_env_affinity(state.active_env)


def _line_env_qualified(state: GameState, comp_name: str) -> bool | None:
    """累积型线强环境判据(ADR-0461)。

    语义出处:「全局累积型角色越早越好,但需特定环境才强,**无环境不选**」
    (user_playstyle [21] 例外条款)+ accumulator_family §3(万敌强环境=
    敌方多动/反伤类)§4.2 前提②「当前/将遇敌方词缀 ∈ 该成员强环境集」。

    返回三态:
    - ``None`` = 判据不辖或信息缺失(comp 无 hp_charge_stack 累积成员 /
      强环境集未建模 / ``state.enemy_affixes`` 空=词缀可信位缺失)——调用方
      必须放行(ADR-0107 动态权重剔除同款:缺信息不造硬结论,不猜);
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
    if not state.enemy_affixes:
        return None
    affix_map, _, _ = merged_mechanic_tables()
    mech = {affix_map.get(a, a) for a in state.enemy_affixes}
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
    - ⑤兜底线(FALLBACK_COMP_NAME):未锁分支的囤货=同线采购集
      (hoard_target_set),门对其恒 no-op;
    - 希儿 ∈ core:希儿系=四体系之一,单卡即战力(伤害在希儿技能层);
    - 主/副档 ∩ 三羁绊体系键 ≠ ∅:锁线方向=意向线主/副档羁绊
      (discipline 方向期阵营门的消费对象),档位即体系 → 锁了仍在买引擎件
      (DOT队/专家桑博DOT/列车同行;[20] 过渡是配方——4列车保送 P2 即其
      升级层)。
    其余线=终局专属(万敌单C/黄泉减益/双王圣杯/命运圣杯红A/大黑塔银河学者/
    狼尊欢愉/反甲白厄):前期战力来自通用引擎池而非自身目标件
    (transition_combos 直通终局线节),锁线会把囤货方向从过渡引擎上引开。
    """
    if comp.name == FALLBACK_COMP_NAME:
        return True
    if '希儿' in comp.core_chars:
        return True
    tier_keys = set(comp.form_tiers) | set(comp.sub_tiers)
    return bool(tier_keys & _ENGINE_BOND_KEYS)


def _p1_gate_blocks(state: GameState, comp: Comp) -> bool:
    """P1 终局专属线锁线证据门是否拦下该线(ADR-0341)。

    拦截 = 门开 ∧ plane==1 ∧ 非过渡线 ∧ 无①类资格(策略/环境亲和,
    与②门同一资格源 _direct_line_qualified)。P2/P3 不辖——
    [21] 上场窗口(姬子=7级/万敌=1-9 变阵点)与 1-8 换血点都在 P1 之后,
    终局线在 P2 起锁是 [23] 全文语义。
    """
    if state.plane != 1:
        return False
    if _p1_transition_eligible(comp):
        return False
    return not _direct_line_qualified(state, comp.name)


#: 希儿系体系键(单卡二元判定,不占羁绊键;与 cw_battle_calib._engines_count
#: 的希儿系哨兵同口径)。
# ⚠️ 权威副本 = knowledge/cw_line_facts.SEELE_SYSTEM;本副本仅为 sim/旧判据
# 未迁消费点保留(迁移完成后随文件删除);勿新增消费。
SEELE_SYSTEM: str = '希儿系'

#: P1 配方对平手序 = 注册表声明序(TRANSITION_TRAITS 声明序 + 希儿系垫底
#: 单卡系)。旧「激活占比降序(列车 .360 > DOT .329 > 仙舟 .292,transition_
#: combos 数据附录)」社区统计平手序已退役 2026-09-04(ADR-0519「未证即退役」;
#: 平手 tiebreak 仅定确定性,不载经验排序)。
_P1_PAIR_PREF: tuple[str, ...] = tuple(
    b for b, _t in TRANSITION_TRAITS) + (SEELE_SYSTEM,)

P1_PAIR_LOCK_MIN_SUPPORT: float = 1.0
"""配方对锁定门槛(ADR-0519 后口径):最高体系支持度 ≥ 此值才锁。

【注】游戏定义激活当量:支持度 = 该体系羁绊计数 / 体系档(TRANSITION_
TRAITS),1.0 = 体系羁绊满员(羁绊档可完整凑齐)——锁线证据回到游戏
定义计数。旧值 0.5(「三羁绊系 ≥1 件或希儿在手」,设计推断 sim 校准)
与希儿系 0.6+0.2+0.2 放大器权重已按「未证即退役」退役;希儿系为单卡
体系,支持度 = 希儿在手二元(1.0/0.0)。保守方向:锁线门槛更严 →
P1 空窗期(囤跨线骨架件)更长,方向承诺不提前。"""


# ===== ①锁局过渡对保护副方向(ADR-0367)=====
# 诊断来源:ADR-0367 判读节——inject on 口径 strict_mal 0.20 vs off 0.05 的
# 差值 15 局全部来自①资格通道:注入信号 r1 锁终局 comp,其采购集把囤货
# 方向从过渡引擎引开(engines2_by_r6 0.27→0.15)+ evolve 按 comp 线换档
# 拆过渡体系(S2 挤出 19/20 mal 局)=ADR-0357 主灶在①通道的残留。


def _owned_chars(state: GameState) -> set[str]:
    """已到手角色名(bench+deployed;不含 shop 可见——[23] 锁定由
    贯穿件=到手,店里出现过不构成方向承诺)。"""
    return {bc.char_id for bc in list(state.bench) + list(state.deployed)
            if bc is not None and bc.char_id}


def _p1_system_support(state: GameState) -> dict[str, float]:
    """四过渡体系的手上资产支持度(bench+deployed;注册表阵营∪流派口径,
    与 ``cw_battle_calib._engines_count`` 同式——多阵营件(桑博=贝+DOT)各系并计)。

    三羁绊系 = 羁绊计数 / 体系档(仙舟3/列车2/DOT2,TRANSITION_TRAITS
    单一源);希儿系 = 希儿在手二元 1.0(单卡体系,到手即完整;旧
    0.6+量2/贝2 各 0.2 放大器权重已随 ADR-0519 退役)。
    """
    counts: dict[str, int] = {}
    for bc in list(state.bench) + list(state.deployed):
        if bc is None or not bc.char_id:
            if bc is not None and bc.faction and bc.faction != '?':
                counts[bc.faction] = counts.get(bc.faction, 0) + 1
            continue
        ch = CHARACTERS.get(bc.char_id)
        if ch is None:
            continue
        for f in set(ch.factions) | set(ch.flows):
            counts[f] = counts.get(f, 0) + 1
    sup = {b: counts.get(b, 0) / t for b, t in TRANSITION_TRAITS}
    sup[SEELE_SYSTEM] = 1.0 if '希儿' in _owned_chars(state) else 0.0
    return sup


def p1_gap_window(state: GameState) -> bool:
    """P1 空窗期判定(只读):bench∪deployed 四体系最高支持度 <
    ``P1_PAIR_LOCK_MIN_SUPPORT``。

    消费位=cw4 商店线方向 pass 的 K 空窗回退门(2026-09-03 第三病灶
    裁定,SEEDS_EMPTY_LEDGER_DIAG §4 第一案):``target_comp`` 值域
    全集含 None,空窗期 K 投影回退 ``hoard_target_set``(本模块,
    单一源)。判定数学与 ``_derive_p1_pair`` 的不锁分支同源(同一
    ``_p1_system_support`` + 同一门槛常数,禁另造支持度算式)。
    边界:空板面恒 True(0<0.5);P2+ 调用面约定不辖(空窗系 P1 概念)。
    """
    sup = _p1_system_support(state)
    return max(sup.values(), default=0.0) < P1_PAIR_LOCK_MIN_SUPPORT


def _derive_p1_pair(state: GameState,
                    exclude: frozenset[str] = frozenset(),
                    registry: DecisionV2Registry | None = None,
                    ) -> tuple[str, ...]:
    """P1 配方对派生:支持度 top-2(平手按激活占比序),规整为
    ``_P1_PAIR_PREF`` 序的二元组;最高支持度未达门槛 → ()(空窗不锁)。

    ``exclude``:R3 断供驱逐的体系键集(移出候选后重派生;蓝图 §4.3-R3)。
    体系对随资产**重派生**([20]「变体按来牌选」——支持度只增,变更
    是来牌选型不是 pivot;[23] 冻结语义辖终局线,不辖 P1 配方)。
    (兑现链方向侧的供给感知支持度/切换滞回已随旧方案清退批删除——
    realization_chain 开关族出局,清查报告 OLD_MIX_AUDIT §1.3。)
    """
    sup = _p1_system_support(state)
    ranked = [k for k in sorted(sup, key=lambda k: (-sup[k], _P1_PAIR_PREF.index(k)))
              if k not in exclude]
    if not ranked or sup[ranked[0]] < P1_PAIR_LOCK_MIN_SUPPORT:
        return ()
    return tuple(sorted(ranked[:2], key=_P1_PAIR_PREF.index))


#: R3 断供驱逐已退役(2026-09-04,ADR-0519「未证即退役」):旧
#: PAIR_DROUGHT_EVICT_ROUNDS=5 为「保守先验」,探针批标定挂账未兑现,
#: 任何实证引用无效——驱逐(换向动作)不再由未证阈值触发。断供/供给
#: 计数器保留作遥测与撤销证据输入,不再写 pair_evicted;缺口披露:
#: 断供死方向不再被计数驱逐,逃逸改由撤销出口①/③(证据机器)承载。
#: (经济冻结病灶①的根是单向驱逐,本退役连同 un-evict 语义一并失去
#: 载体;pair_evicted 字段保留为空集兼容序列化。)

#: 供给确认阈值(轮)。原 = 驱逐阈值取半派生,驱逐退役后唯一残消费 =
#: 撤销出口③的证据合取项(线内在店断供 ≥ 此值 ∧ G ≤ ε 才允许降级)。
#: 【拟】经验阈值待证(ADR-0519 登记);保守向 = 合取更严 → 撤销更难,
#: 降级仍可逆(不写 evicted),与出口③「防误杀」设计同向。
PAIR_SUPPLY_CONFIRM_ROUNDS: int = 2


def _update_pair_drought(state: GameState, ist: IntentionState,
                         visible: set[str]) -> None:
    """R3 断供供给计数器(每 game-round 恰一次,由 update_intention 驱动)。

    ADR-0519 后仅计数不驱逐:对四体系全集维护 ``shop_supply_streak``
    (在店供给连续轮)与现任 pair 方向的 ``pair_drought``(断供连续轮),
    供遥测与撤销证据链消费;写 ``pair_evicted`` 的驱逐分支已随未证阈值
    退役(见上方常量注)。
    """
    if state.plane != 1:
        return
    shop_names = {getattr(c, 'name', '') or '' for c in (state.shop or [])}
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


def p1_early_pair(state: GameState,
                  ist: IntentionState | None) -> tuple[str, ...]:
    """P1 早期新件买入门的配方对读口(ADR-0372;只读,不落字段)。

    与 ``_derive_p1_pair`` 同口径(支持度 top-2 + ``_P1_PAIR_PREF`` 序
    规整),但**未锁形态期同样派生**(无 ``P1_PAIR_LOCK_MIN_SUPPORT``
    门槛)——这是对现行 ``p1_pair``/``transition_pair`` 仅锁后非空的
    语义扩展:买入门要的是「当前资产下的配方方向」,空窗期([31]①
    四体系不一定开局凑到)同样有 top-2 方向,不该因为不够锁而没方向。

    - 锁定帧优先用意向字段(①锁局 transition_pair / 配方锁 p1_pair
      ——两字段是同一口径在不同锁定帧的实例);
    - 未锁/空窗/weak:现场派生(无门槛);
    - P1 外恒 ()(买入门只辖 P1)。
    """
    if state.plane != 1:
        return ()
    if ist is not None:
        tp = tuple(getattr(ist, 'transition_pair', ()) or ())
        if tp:
            return tp
        pp = tuple(getattr(ist, 'p1_pair', ()) or ())
        if pp:
            return pp
    sup = _p1_system_support(state)
    exclude = frozenset(getattr(ist, 'pair_evicted', ()) or ()) if ist is not None else frozenset()
    ranked = [k for k in sorted(sup, key=lambda k: (-sup[k], _P1_PAIR_PREF.index(k)))
              if k not in exclude]
    return tuple(sorted(ranked[:2], key=_P1_PAIR_PREF.index))


def p1_early_pair_members(state: GameState,
                          ist: IntentionState | None) -> frozenset[str]:
    """P1 锁线过渡带的囤货成员集(只读;FIX_REVIEW_20260903 R3① 单一源)。

    辖域 = P1 ∧ 支持度已达锁线门槛但 pair 尚未锁帧(``update_intention``
    逐 game-round 跑,商店波内滞后)——该带旧核有 ``p1_early_pair`` 方向
    (无门槛 top-2),新核商店线 K 投影经本函数取成员集,禁在消费位
    复制 top-2/成员集推导。成员投影 = ``_pair_members(p1_early_pair(...))``
    (与 hoard_target_set P1 分支同一成员投影算子);pair 派生为空
    (如 pair_evicted 全驱逐)⇒ 空集,消费位自行链 hoard_target_set
    空窗全集兜底。P1 外恒空集(``p1_early_pair`` 同辖域)。
    """
    pair = p1_early_pair(state, ist)
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
    ``session.target_comp`` 在配方锁帧恒 None——部署选人/评分管线/
    投资装备钩子等既有 target 消费者从此全盲(断线症状:引擎件
    躺 bench、散脸占板,decisions.target_comp 全程空串)。
    本函数把已锁方向物化为伪 comp,写端单点 =
    ``decision_v2.strategy.update_target``(locked_comp 空且 P1 配方锁
    时调用);方向选择不动(ADR-0442 删除的 transition_focus 是
    「从零选收敛方向」,与本物化不同层,非其变体复活)。

    单一口径:
    - factions = ``_pair_bond_keys`` 板面羁绊键;core_chars =
      ``_pair_members`` 全成员(均序化,构造确定);
    - form_tiers 分辨序:① ``cw_bridge_pool.BRIDGE_POOL`` 精确匹配
      (键集合相等 → 整组取该桥 engine_bonds;桥池是配方对档位的既有
      单一源,数据底=transition_combos 调研);② 无桥条目的对(希儿系
      组合)→ 逐体系取桥池任一条的档 + 希儿系并 ``cw_recipe`` 量子配方
      档(量子同频+贝洛伯格,希儿系板面键=量子系,口径同展开)。
      ⚠️ 已知双源分歧:列车同行档桥池=2(train_dot)、cw_recipe
      _RECIPES=4(框架单独成型档,语义不同层)——本函数取桥池;
      分歧裁决与合流判据见 ADR-0459。
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
    for combo in BRIDGE_POOL:
        if set(combo.engine_bonds) == bonds:
            tiers = dict(combo.engine_bonds)
            break
    else:
        # 逐体系兜底:取该体系在桥池任一条的档(同源派生,不手写表);
        # 希儿系补量子配方档后,只保留本对键(防兜底混入对外体系)。
        for combo in BRIDGE_POOL:
            for bond, tier in combo.engine_bonds.items():
                tiers.setdefault(bond, tier)
        if SEELE_SYSTEM in pair:
            from sr_od.application.currency_war.kernel.cw_recipe import recipe_comp
            _q = recipe_comp('量子')
            if _q is not None:
                tiers.update(_q.form_tiers)
        tiers = {bond: tier for bond, tier in tiers.items() if bond in bonds}
    if not tiers:
        return None
    return Comp(
        name='过渡配方·' + '+'.join(pair),
        factions=sorted(bonds),
        core_chars=sorted(_pair_members(pair)),
        form_tiers=dict(sorted(tiers.items())),
        strength='A',
        form_difficulty='easy',
    )


def detect_signals(state: GameState) -> list[IntentionSignal]:
    """信号分层判定(①策略驱动 > ②类专属羁绊 > ③核心卡 > ④资源)。

    返回分层信号列表(未排序;消费方按 layer 升序 / weight 降序取最优);
    ⑤无信号兜底不在此产出——列表为空时解析侧落 FALLBACK_COMP_NAME。
    冻结超限已移出候选集(evicted)的线不产信号(等同信号未发生)。
    """
    out: list[IntentionSignal] = []
    comps = _v2_comps()
    # 注:evicted 过滤由 IntentionState 携带,detect_signals 是纯函数不读状态机;
    # 调用方(update_intention)负责过滤。直接消费方请走 update_intention。
    visible = _visible_chars(state)

    # ① 策略驱动:投资环境 / 投资策略字段出现 → 对应线(近硬绑亲和表)
    if state.active_env:
        for comp_name, w in augment_env_affinity(state.active_env).items():
            if get_comp(comp_name) is not None:
                out.append(IntentionSignal(1, 'env', comp_name,
                                           f'环境[{state.active_env}]×{w}', w))
    for s in state.active_strategies:
        for comp_name, w in augment_affinity(s).items():
            if get_comp(comp_name) is not None:
                out.append(IntentionSignal(1, 'strategy', comp_name,
                                           f'策略[{s}]×{w}', w))

    # ② 类专属:家族专属羁绊信号(板上+bench 计数达阈;希儿量子/白厄反甲无②)。
    # ADR-0338 资格门:羁绊副产品计数(学者2/夜半2/列车2 等)不是直通资格
    # ——直通终局线的锁线资格 = 持有对应投资策略/环境(亲和表反查);
    # 无资格不发②信号(意向保持 unlocked,囤货落⑤兜底,P1 板面归四体系
    # 过渡逻辑;贯穿件到手走③,[23] 合法路径不变)。
    counts = _bond_counts(state)
    for fam, bond in FAMILY_BOND_SIGNALS.items():
        if counts.get(bond, 0) >= FAMILY_BOND_MIN_COUNT:
            for c in comps:
                if c.family == fam and _direct_line_qualified(state, c.name):
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
            if _p1_gate_blocks(state, c):
                continue
            out.append(IntentionSignal(3, 'core_card', c.name,
                                       f'核心[{core}]可见', 1.0))

    # ④ 资源:升费资源等特殊系统锚(④层)。
    # 数据缺口声明:升费资源(道具)暂无 GameState 字段——以升费链角色到手
    # (cost_escalation['角色'] 在 bench/deployed)作「资源到位」代理;字段接入后扩。
    # ADR-0341:④与③同为「卡/资源到手」证据类,P1 终局专属线同门。
    owned = {bc.char_id for bc in list(state.bench) + list(state.deployed)
             if bc is not None and bc.char_id}
    for c in comps:
        ce = c.special_systems.get('cost_escalation')
        if ce and ce.get('角色') in owned:
            if _p1_gate_blocks(state, c):
                continue
            out.append(IntentionSignal(4, 'resource', c.name,
                                       f'升费链[{ce.get("角色")}]已到手', 0.5))
    return out


def _asset_thickness(comp: Comp, state: GameState) -> float:
    """候选线资产厚度(ADR-0519 后口径):

    板上+bench 中该线终局件数(副本计星级当量:每副本按其 star 计)。
    终件 = core_chars。骨架件折算项已退役(旧 SKELETON_ASSET_WEIGHT=0.5
    设计推断无标定,「未证即退役」→ 保守缺省不计;跨线骨架件仍是囤货
    对象,只是不再抬高本线厚度——撤销出口③的替代证据因此更严)。"""
    pool = list(iter_occupied_deployed(state.deployed)) \
        + [b for b in state.bench if b is not None]
    star_of = {bc.char_id: bc.star for bc in pool
               if bc is not None and bc.char_id}
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


def p2_supply_horizon(state: GameState,
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
    plane_left = plane_remaining_nodes(state, session)
    hp = int(getattr(state, 'hp', 0) or 0)
    blood_rounds = math.ceil(hp / float(reg.vd_p2_loss)) if hp > 0 else 0
    return min(plane_left, blood_rounds)


def line_completion_feasibility(state: GameState,
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
    h_eff = p2_supply_horizon(state, session, registry)
    if h_eff <= 0:
        return 0.0
    vis = _visible_chars(state) if visible is None else visible
    owned = _owned_chars(state)
    g = 1.0
    for m in comp.core_chars:
        if m in owned or m in vis:
            continue
        q = _core_miss_q(m, state.level)
        if q <= 0.0:
            return 0.0
        g *= 1.0 - (1.0 - q) ** h_eff
        if g <= 0.0:
            break
    return g


def _best_supply_feasible_alt(state: GameState,
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
        if state.plane in (c.weak_planes or ()):
            continue
        core = intention_core(c)
        if not core or core not in visible:
            continue
        g = line_completion_feasibility(state, c, session, reg, visible)
        if g > reg.revoke_miss_tolerance_eps \
                and (best is None or g > best[1]):
            best = (c.name, g)
    return best


def _p2_signal_supply_ok(state: GameState,
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
        state, comp, session, reg, visible) > reg.revoke_miss_tolerance_eps


def _revoke_alt_evidence(state: GameState, visible: set[str],
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
        if not _core_reachable(c, state, visible):
            continue
        thk = _asset_thickness(c, state)
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


def _lock(ist: IntentionState, state: GameState, sig: IntentionSignal,
          forced: bool = False) -> None:
    ist.phase = 'locked'
    ist.locked_comp = sig.comp_name
    ist.p1_pair = ()   # comp 锁定取代配方锁(ADR-0357:①资格通道)
    # ADR-0367:①锁局(P1∧配方锁开)同时派生过渡对副方向
    # (与 p1_pair 同口径;P2+ 强制锁线/旧通道 P1 锁均不辖)。
    ist.transition_pair = (
        _derive_p1_pair(state, exclude=frozenset(ist.pair_evicted))
        if state.plane == 1
        else ()
    )
    ist.lock_layer = sig.layer if not forced else 1   # 强制锁线视作最高层(不可被出口②撤)
    ist.lock_plane = state.plane
    ist.lock_round = state.round_num
    ist.forced = forced
    ist.weak_comp = ''
    ist.revoke_evidence = {}   # 重锁=证据消费完毕(字段契约见 IntentionState)
    ist.last_event = ('forced_lock:' if forced else 'lock:') + sig.comp_name


def update_intention(state: GameState, ist: IntentionState,
                     session: StrategySession | None = None,
                     registry: DecisionV2Registry | None = None
                     ) -> IntentionState:
    """每回合驱动锁线/撤销状态机(就地改 ist 并返回;不碰 GameState)。

    序:降格终局短路 → 锁定态撤销检查(冻结 → miss-N → 高层信号)
    → 未锁/弱意向解析(新信号锁线,否则⑤兜底方向)→ P3 入口强制锁线。
    (C4 存活轮数门接线 _switch_gate_open、门闩与换线门决策位/闩已随
    旧方案清退批删除,清查报告 OLD_MIX_AUDIT §1.3——默认关开关族出局,
    换线裁决回归 E_rounds/θ/δ/D_min 主判据。)
    """
    if ist.demoted_endgame:
        return ist   # 降格终局是 absorbing 态(点7 止损序同构,不回弹)
    if state.plane != 1 and ist.transition_pair:
        # 出 P1:过渡对副方向退场(ADR-0367;P2+ 锁定目标=locked_comp 唯一)
        ist.transition_pair = ()
    visible = _visible_chars(state)
    # (原「门闩位面切换清零」分支只在闩置位后生效;门闩删除后默认行为
    # =位面切换不清 miss_count——维持删除前生产默认,零漂移。)
    # R3 断供驱逐(ADR-0465):每 game-round 恰一次的体系级断供计数
    # (pair 方向在场时辖;断供计数写 pair_drought,驱逐分支已退役
    # ADR-0519,pair_evicted 恒空集——派生 exclude 参数留兼容)。
    _update_pair_drought(state, ist, visible)
    sigs = [s for s in detect_signals(state) if s.comp_name not in ist.evicted]
    # 弱面位面过滤(经济冻结批,病灶③):注册表自注 weak_planes 含当前
    # 位面的线不产锁线信号——单一源=Comp.weak_planes 注册项自注(如
    # DOT队 weak_planes=(2,)「P2 被抽陀螺,保命 pivot 不选」)。旧形态
    # 只滤 maybe_pivot 保命路径,③核心卡可见信号(P2r1 卡芙卡在场)绕过
    # 过滤锁出 P2 弱面线,选线即死路(实机局 g_20260904_042657)。
    _pre_wp = len(sigs)
    sigs = [s for s in sigs
            if state.plane not in (getattr(get_comp(s.comp_name),
                                            'weak_planes', ()) or ())]
    if len(sigs) != _pre_wp:
        log.info('[cw][intention] 弱面过滤 %d→%d 信号(plane=%s)',
                 _pre_wp, len(sigs), state.plane)
    revoked = False   # 本轮是否发生撤销(出口①miss/出口②):撤后当轮不重锁——
    # 「意向降级为弱意向……直至新信号」= 新信号指下一轮起的信号;同轮撤+锁会让
    # 弱意向态不可观测(判读/遥测断档),状态机一回合最多一次转移。

    if ist.phase == 'locked':
        comp = get_comp(ist.locked_comp)
        core = intention_core(comp) if comp else ''
        track = _track(ist, ist.locked_comp)
        ch = CHARACTERS.get(core) if core else None
        window_open = bool(ch) and refresh_prob(state.level, ch.cost) > 0
        if not window_open:
            # 窗口冻结:未开窗不计 miss;冻结超位面剩余节点 → 移出候选集,
            # 意向回⑤无信号态——**不触发③**(该轮③信号被排除)
            track.frozen_rounds += 1
            # ADR-0366:冻结超限对照量按本位面真值(session 透传,P2=7)。
            if track.frozen_rounds > plane_remaining_nodes(state, session):
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
            shop_names = {getattr(c, 'name', '') or '' for c in (state.shop or [])}
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
                    core, state.level, reg.revoke_miss_tolerance_eps)
                if track.miss_count >= max(CORE_MISS_N, n_req):
                    ev = _revoke_alt_evidence(
                        state, visible, ist.locked_comp, ist.evicted,
                        reg.revoke_evidence_min_thickness)
                    if ev is not None:
                        # 撤销出口①:断供证据 + 替代资产证据齐备 → 降级弱意向
                        alt_name, thk = ev
                        q = _core_miss_q(core, state.level)
                        alt_comp = get_comp(alt_name)
                        e_alt = (e_rounds(alt_comp, state, reg)
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
            # 降级到 unlocked 让 dd-033 的 P2 移交(handoff_lock)机制
            # 下一轮确定性地重锁到可行线,换线不绕信号运气。与出口①
            # 同构的可逆性:降级不写 evicted,现线缺件兑现(买到)/血量
            # 回升(H 变大)/升级(q 变大)后 G 恢复即可经信号/移交重锁
            # (un-evict 同款,经济冻结批语义)。核心在店帧不辖(当轮
            # 可买,缺件集即缩,G 会被低估)。全线不可行(无 G>ε 替代)
            # 不降级:任何换线都是 ε 级噪声,P25 锁线价值保留。
            if (not revoked and state.plane == 2 and core
                    and core not in visible
                    and track.member_drought >= PAIR_SUPPLY_CONFIRM_ROUNDS):
                _reg_f = registry or DEFAULT_REGISTRY
                g_locked = line_completion_feasibility(
                    state, comp, session, _reg_f, visible)
                if g_locked <= _reg_f.revoke_miss_tolerance_eps:
                    alt = _best_supply_feasible_alt(
                        state, ist, session, _reg_f, visible,
                        exclude=ist.locked_comp)
                    if alt is not None:
                        alt_name, g_alt = alt
                        _h = p2_supply_horizon(state, session, _reg_f)
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
                            'hp': int(getattr(state, 'hp', 0) or 0),
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
                if new_comp and _core_reachable(new_comp, state, visible):
                    ist.phase = 'weak'
                    ist.weak_comp = ist.locked_comp
                    ist.locked_comp = ''
                    ist.lock_layer = 0
                    ist.transition_pair = ()   # weak 不辖(ADR-0367,同 scope 契约)
                    ist.revoke_evidence = {}   # 出口②非证据组 A/B 通道(字段契约)
                    ist.last_event = f'revoke:higher:{s.comp_name}(L{s.layer})'
                    revoked = True
                    break   # 「直至新信号」——本轮撤,下轮新信号再锁


    if ist.phase == 'locked' and state.plane == 1:
        # ADR-0367:①锁局过渡对随资产重派生(同 p1_pair 语义——
        # 「变体按来牌选」[20],支持度只增,非 pivot;[23] 冻结语义辖
        # 终局线,不辖过渡副方向)。配方锁局(phase='unlocked')不进本支。
        pair = _derive_p1_pair(state, exclude=frozenset(ist.pair_evicted),
                               registry=registry)
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
        if state.plane == 2:
            _reg_f2 = registry or DEFAULT_REGISTRY
            _n0 = len(sigs)
            sigs = [s for s in sigs
                    if _p2_signal_supply_ok(state, s, session, _reg_f2,
                                            visible)]
            if len(sigs) != _n0:
                log.info('[cw][intention] P2 供给可行性缓锁 %d→%d 信号',
                         _n0, len(sigs))
        # H1 锁线环境判据(行为无条件化):累积型线强环境不命中(False)的信号
        # 本轮不锁(缓锁——「无环境不选」只辖**主动选线**,已锁线与判据
        # 不辖(None)/信息缺失帧不拦;观察期=line_env_lock_min_round)。
        # 已锁分支(上方 locked)有意不过此滤:环境缺失不没收已锁线
        # (accumulator_family §3 同义)。
        _reg_env = registry or DEFAULT_REGISTRY
        if state.round_num >= _reg_env.line_env_lock_min_round:
            _n0 = len(sigs)
            sigs = [s for s in sigs
                    if _line_env_qualified(state, s.comp_name) is not False]
            if len(sigs) != _n0:
                log.info('[cw][intention] 环境判据缓锁 %d→%d 信号(affixes=%s)',
                         _n0, len(sigs), state.enemy_affixes)
        # P1 过渡配方锁(ADR-0357):P1 的锁定产物=体系对;
        # ②③④信号不再锁终局 comp(终局 comp 锁定移至 P2+)——
        # 只保留①类资格通道(直通终局线资格,ADR-0338/0341 语义零改动)。
        # 方向产物=按手上资产派生的体系对(transition_combos 两两组合)。
        if state.plane == 1:
            sigs = [s for s in sigs
                    if _direct_line_qualified(state, s.comp_name)]
            pair = _derive_p1_pair(state, exclude=frozenset(ist.pair_evicted),
                                   registry=registry)
            if pair != ist.p1_pair:
                ist.p1_pair = pair
                ist.last_event = ('p1_pair:' + '+'.join(pair)) \
                    if pair else 'p1_pair:wait'
        elif ist.p1_pair:
            # 进 P2:配方锁退场,comp 锁定通道照旧(P2+ 锁定产物=终局 comp)
            ist.p1_pair = ()
            ist.last_event = 'p1_pair:exit_p1'
        best = _best_signal(sigs)
        if best is not None:
            _lock(ist, state, best)
        elif ist.phase == 'weak':
            ist.last_event = ist.last_event or 'weak:hold'
        # 无信号:保持 unlocked——囤货方向落⑤兜底(hoard_target_set 处理)


    # 强制锁线(位面入口无意向;点0〔修N4〕对象限定)。经济冻结批扩 P2:
    # P2 开局必须有目标(目标移交/重 assignment)——P1 配方锁在 P2 退场
    # (p1_pair:exit_p1)后,若信号未锁(unlocked),旧形态落⑤兜底囤货但
    # target_comp=None,准备域决策引擎无方向空转;现在 P2 unlocked 帧
    # 按「weak_planes 过滤 ∧ 核心可达 ∧ 资产最厚」强制 assignment(同 P3
    # 语义)。P3 起维持原辖域(phase!='locked');P2 收窄到 unlocked:
    # weak 态是撤销机器在册的意向降级,强制锁会踩掉其「直至新信号」语义。
    # 位面强锁候选同过 weak_planes 过滤(P3 旧分支未滤,同病灶③面)。
    # P2 无可达候选 ⇒ 保持 unlocked(⑤兜底绯英档方向,位面余量尚在,
    # 不降格终局;降格=终局不可达判定,归 P3)。
    # P2 移交守卫:撤销当轮(出口①/②/③)不接同一轮的移交重锁——
    # 「状态机一回合最多一次转移」纪律(revoked 注);下一轮由移交通道
    # 正常重锁(P3 强锁辖域不受本守卫影响,维持既有语义)。
    _p2_handoff = (state.plane == 2 and ist.phase == 'unlocked'
                   and not revoked)
    if (state.plane >= 3 or _p2_handoff) and ist.phase != 'locked':
        # P2 移交候选补「锁线可行性」门(锁线可行性批):G > ε 才可锁
        # ——锁线前先验证可达性(供给概率×剩余轮×血预算,注册表派生
        # 零新参数),不可行线不进强锁候选;全不可行 ⇒ 无候选 ⇒ 保持
        # unlocked(dd-033 ⑤兜底语义=「降级目标」面,不降格终局)。
        # P3 分支不动(强锁/降格终局辖域原语义,本批只辖 P2)。
        _reg_h = registry or DEFAULT_REGISTRY
        cands = [c for c in _v2_comps()
                 if c.name not in ist.evicted
                 and state.plane not in (c.weak_planes or ())
                 and _core_reachable(c, state, visible)
                 and (state.plane != 2
                      or line_completion_feasibility(
                          state, c, session, _reg_h, visible)
                      > _reg_h.revoke_miss_tolerance_eps)]
        if cands:
            best = sorted(
                cands,
                key=lambda c: (-_asset_thickness(c, state),
                               encounter_window_rounds(intention_core(c), state.level)),
            )[0]
            _lock(ist, state, IntentionSignal(1, 'forced', best.name,
                                              '资产最厚', 1.0), forced=True)
            if _p2_handoff:
                # 移交锁与 P3 强制锁分事件标签(判读可辨「P2 开局移交」与
                # 「P3 入口强制」;标签风格同 last_event 'p1_pair:' 族)。
                ist.last_event = 'handoff_lock:' + best.name
        elif state.plane >= 3:
            # 全部不可达 → 降格终局:四体系过渡板深档强化+通用骨架满配
            ist.demoted_endgame = True
            ist.phase = 'unlocked'
            ist.locked_comp = ''
            ist.revoke_evidence = {}   # 降格不经撤销,证据随之失效
            ist.last_event = 'demote:endgame'
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


def hoard_target_set(state: GameState, ist: IntentionState) -> HoardTarget:
    """锁后效果接口:输出「囤货目标集合」供买侧消费([21]:只改囤货方向,不改板上)。

    - locked/forced:意向线采购集;
    - P1(ADR-0357):非 comp 锁定局 → 配方方向——体系对成员集
      (p1_pair)/四体系引擎件全集(p1_transition,空窗);绯英⑤兜底
      不再辖 P1(零引擎覆盖,sim 实证 e2 成率 5%);
    - weak:只囤跨线骨架件(撤销后去向);
    - unlocked 无信号(P2+):⑤兜底 = 绯英档采购集(「无信号时的默认落点」);
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
    if state.plane == 1:
        # P1 配方方向(ADR-0357):体系对成员集;空窗=四体系全集。
        # 过渡装备随意([20] 装备语义:简易装备随便给,合成件归 final
        # key_equips 判定)——equip_targets 恒空。
        pair = ist.p1_pair or ()
        members = _pair_members(pair) if pair else _pair_members(_P1_PAIR_PREF)
        return HoardTarget(frozenset(members), frozenset(),
                           'p1_pair' if pair else 'p1_transition')
    if ist.phase == 'weak':
        return HoardTarget(frozenset(CROSS_LINE_SKELETON), frozenset(), 'weak')
    comp = get_comp(FALLBACK_COMP_NAME)
    if comp is None:
        return HoardTarget(frozenset(CROSS_LINE_SKELETON), frozenset(), 'fallback')
    chars, equips = _line_hoard(comp)
    return HoardTarget(frozenset(chars), frozenset(equips), 'fallback')


def k_empty_window_fallback(state: GameState,
                            ist: IntentionState) -> tuple[frozenset[str], str]:
    """K 空窗回退单一源(经济冻结批病灶①):target_comp=None 时目标成员
    集的分带派生,商店域(shop.py)与准备域(cw4/entry.py)共用本函数——
    禁在任一消费域复制四体系全集/兜底逻辑(第二源)。

    返回 (成员集, 分带 token):分带 token 供消费域拼遥测计数键
    (shop 侧键名契约 'shop_k_fallback_<token>' 维持历史键名不变)。
    分带语义与 shop.py 旧内联派生逐款同源:
    - p1_gap:P1 空窗带(支持度 < 锁门槛)→ hoard 四体系引擎件全集
      (消「K 空→零买入→支持度永不涨」死锁环);
    - p1_lock_band:P1 锁线过渡带 → p1_early_pair 无门槛方向,派生空
      (全驱逐)⇒ 链 hoard 全集兜底;
    - p2plus:P2+ → hoard 分带(unlocked=绯英⑤兜底/weak=跨线骨架/
      demoted=骨架满配)。
    """
    if state.plane == 1:
        if p1_gap_window(state):
            return hoard_target_set(state, ist).char_targets, 'p1_gap'
        return (p1_early_pair_members(state, ist)
                or hoard_target_set(state, ist).char_targets), 'p1_lock_band'
    return hoard_target_set(state, ist).char_targets, 'p2plus'


def committed_authority(state: GameState | None,
                        session: StrategySession | None) -> bool:
    """committed(已定型/非双轨期)权威判定(方向层单一派生源)。

    - **权威序**(任一成立即 True):
      ① ``state.plane >= 2``——P2 起恒定型(语义边界同旧 update_target:
         定型边界=进位面 2,严于文档口径 P2-3);
      ② ``session.v3_intention.phase == 'locked'``——意向状态机已锁线;
      ③ ``ist.p1_pair`` 非空——P1 配方锁已立(ADR-0357 产物形态)。
    - **缺供给帧 = 保守侧 False**(=双轨=攒息):ist 不可得/字段缺失时
      **禁止**缺省 True——True=已定型=激进侧,攒息门/双轨买门全开
      (供给点清单 D2:拔掉供给探针下必须落保守侧,变异锁钉住)。
    - 消费契约:全部消费点经本函数或 ``decision_v2.prep_brain
      .committed_from``(唯一读端,内部委托本函数)取值;
      state/session 侧双轨字段降级为兼容残留(读点归零,
      grep 守卫锁),写端退役随老栈(strategy 层)老栈退役(ADR-0466/0469)。
    """
    if state is not None and getattr(state, 'plane', 1) >= 2:
        return True
    ist = getattr(session, 'v3_intention', None) if session is not None else None
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

    - 有现读 state → 直取权威派生;
    - 无现读 state 的调用面:plane 取 session.last_state(框架末次读值);
      也不可得时仅凭 ist 判定(缺供给 = 保守 False,同 D2)。

    grep 守卫锁「session 侧双轨字段直读点归零(本函数之外)」;
    变异锁:拔掉意向供给(ist=None 且 plane<2)必须落 False 保守侧
    (穿透锁=test_cw_w620_migration_b1/test_cw_w653_c7_zero_drift)。
    decision_v2.prep_brain 本名保留 import 重定向,消费方调用零改。
    """
    if state is not None:
        return committed_authority(state, session)
    return committed_authority(getattr(session, 'last_state', None), session)


def drive_intention(state: GameState, session: StrategySession,
                    registry: DecisionV2Registry | None = None) -> None:
    """意向状态机驱动点(P7 契约,批 2 方向层接管):每 game-round 恰一次。

    - 锚定 = 决策环入口(ops 环入口 update_target 之前调用);驱动键 =
      (plane, round_num),段级重入守卫 = session.v3_intention_key
      (与策略栈 update_target 的驱动共享同一键面——双驱动并存天然幂等,
      同轮重入不重复计数,miss/冻结分母 = 轮不膨胀);
    - ist 归属(session 保留清单裁决,P4):``v3_intention`` 是跨轮状态机
      计数器族(miss_count/frozen_rounds/evicted/tracks),显式归 session
      保留清单;局级重置由「每局新建 StrategySession」保证,跨局零残留
      (行为锁 test_cw_w628);
    - registry 显式参数(P6):撤销阈值/门判据注入面直达状态机,禁在
      折叠后静默落缺省表——缺省 None 只用于无注入臂的缺省栈。

    (自 decision_v2.prep_brain 迁入意向域单一源;prep_brain 本名保留
    re-export,消费方调用零改。)
    """
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState):
        ist = IntentionState()
        session.v3_intention = ist
    key = (getattr(state, 'plane', 1), getattr(state, 'round_num', 1))
    if getattr(session, 'v3_intention_key', None) == key:
        return   # 同轮已驱动:幂等出口(重入只保派生视图刷新,不计数)
    session.v3_intention_key = key
    update_intention(state, ist, session, registry=registry)


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


def locked_buy_membership(ist: IntentionState | None) -> frozenset[str] | None:
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
    if comp is not None:
        chars, _equips = _line_hoard(comp)
        scope |= chars
    return frozenset(scope) if scope else None


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
    ist = getattr(session, 'v3_intention', None)
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


# ===== 遥测序列化下沉(serialize_intention 语义归本模块:序列化的是本模块
# 的 IntentionState,cw_telemetry 反向 import 本节符号(telemetry→kernel 合法向)。
# ⚠️ 权威副本 = knowledge/cw_serialize(_to_jsonable/
# serialize_intention;telemetry 保留层消费已全部改接)。本节副本仅为 sim
# (ledger_hooks/engine_p1)/旧判据未迁消费点保留(sim 禁动),
# 迁移完成后随文件删除;勿新增消费。

def _to_jsonable(obj: Any) -> Any:
    """dataclass / 基础类型 → JSON 可序列化(递归)。"""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, set):
        return sorted(_to_jsonable(x) for x in obj)
    if isinstance(obj, Path):
        return str(obj)
    return obj


def serialize_intention(ist: Any) -> dict[str, Any] | None:
    """v3 意向状态(IntentionState)→ JSON-safe dict。

    ADR-0336 后锁定真值在 ``session.v3_intention``,但 decisions 行
    只有恒空的 v1 遗留键(``v2_locked_line``/``v2_mode``)——实机判读
    「锁定时点/锁定目标」不可读,只能日志考古。本序列化把意向状态机
    全量落遥测(锁定目标改过渡配方(ADR-0357)的实机验证依赖它)。

    - ``None`` = session 无意向状态机(default 栈/未初始化)——与
      「有意向未锁」(dict 且 ``phase='unlocked'``)显式区分,消费方
      不用猜;
    - dict 按字段全量序列化(dataclass fields 遍历,set→sorted list,
      嵌套 LineTrack 同构)——IntentionState 字段演进(如配方锁设计件调整
      锁定语义)时自动跟上,不改本函数。

    **可变容器深拷贝(ADR-0378)**:dict/list 字段值经
    ``_to_jsonable`` 递归拷贝(嵌套 dataclass 走 asdict=深拷贝)——
    ``tracks: dict[str, LineTrack]`` 是**活引用**,旧版直接把引用
    落进账本行,session 后续轮原地改 LineTrack 会污染**已落账的
    早期行**(sim P2 段改写同局 P1 行的 tracks,P2 谱系分布验证的对比门曾排除
    该字段)。tuple/str 不可变,原样保留(类型不漂移)。

    只读不碰 ``cw_intention``;非 dataclass 输入退 None。
    """
    if not is_dataclass(ist):
        return None
    out: dict[str, Any] = {}
    for f in fields(ist):
        v = getattr(ist, f.name)
        if isinstance(v, set):
            out[f.name] = sorted(v)
        elif is_dataclass(v):
            out[f.name] = _to_jsonable(v)
        elif isinstance(v, (dict, list)):
            # ADR-0378:可变容器深拷贝落账(活引用污染防线,
            # 见 docstring);tuple 不可变不辖(类型不漂移)
            out[f.name] = _to_jsonable(v)
        else:
            out[f.name] = v
    return out
