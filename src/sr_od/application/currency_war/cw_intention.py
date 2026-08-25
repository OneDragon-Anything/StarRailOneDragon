"""货币战争 · 终局意向模块(strategy_v4 点0 实现;纯逻辑,不碰游戏/板上)。

单一规格源:`.debug/temp/currency_war/cw_dev/deep_read/strategy_v4.md` 点0
(信号分层①-⑤ / 撤销析取 / 窗口冻结语义 / 强制锁线对象限定 + 降格终局);
攻略信号数据:`comp_definitions_v2.md` 各套(欢愉族绯英档=⑤兜底、黑塔纪元 65%、
万敌 1 费开局即在等)。

**教义边界(user_playstyle)**:
- [21] final 件「买而不上」→ 本模块锁线后**只改囤货方向**(输出「囤货目标集合」
  供买侧消费),不改板上、不产出任何上场/换人动作;
- [23] 终局线由贯穿件锁定,不是 pivot → 锁定后撤销**只有两个出口**(析取):
  ①意向核心 N 轮不可得(只计刷新窗已开的轮,窗口冻结语义);②更高层级替代
  信号且过可达性对照。分数涌现换线不进本模块。
- [23]/[21] 的 P1 时序面(ADR-0341):贯穿件 P1 可买可囤([21] bench 等窗口),
  但**终局专属线(锁线方向不含过渡引擎)在 P1 的③/④锁线证据被资格门拦下**——
  资格 = ①类(策略/环境亲和;transitions §1「拿到逆天投资策略才配锁直通线」);
  P2/P3 ③照旧([23] 路径不变,本门只收紧 P1 时机)。

**与旧件的关系(载体批新旧交替)**:`cw_signal_lock.py`(Phase A 信号 2 层,
LineV1 载体)与 `cw_line_library_v1` 是旧件,本模块是其 v4 后继——按 COMP_LIBRARY
v2 家族键工作;旧件随 ADR-0336 删除(不再存在),接线已切换。

**P1 过渡配方锁(W145/ADR-0357)**:位面 1 的锁定产物=过渡配方体系对
(transition_combos 两两组合;[20] 过渡是配方不是散买),终局 comp 锁定
只保留①类资格通道,P2+ 照旧锁 comp。详见 ``P1_RECIPE_LOCK`` 注释。

模块构成:
- ``detect_signals(state)``:信号分层判定(①策略驱动/②类专属羁绊/③核心卡/
  ④资源/⑤由解析侧兜底,本函数不发⑤信号);
- ``IntentionState``:锁线/撤销状态机(未锁/锁定/弱意向 + 降格终局标记),
  ``update_intention(state, ist)`` 每回合驱动;
- ``hoard_target_set(state, ist)``:锁后效果接口——输出囤货目标集合(角色件 +
  装备件),买侧唯一消费面。

数值标注「设计推断,sim 校准」的常量属 strategy_v4「悬而未决·W10 摆动域」,
不写死语义进文档。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_comps import (
    COMP_LIBRARY,
    V2_FAMILIES,
    Comp,
    augment_affinity,
    augment_env_affinity,
    derive_key_equips,
    get_comp,
)
from sr_od.application.currency_war.cw_deploy_logic import TRANSITION_TRAITS
from sr_od.application.currency_war.cw_horizon import NODES_PER_PLANE, TOTAL_NODES
from sr_od.application.currency_war.cw_plugins import (
    cross_line_skeleton as _cross_line_skeleton,
)
from sr_od.application.currency_war.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    refresh_prob,
)
from sr_od.application.currency_war.cw_state import GameState

# ===== 常量(设计推断,sim 校准;strategy_v4 点0 / W10 摆动域)=====
CORE_MISS_N: int = 6
"""撤销出口①阈值:意向核心 N 轮不可得 → 撤销(设计推断,sim 校准)。
计数分母 = 该核心刷新窗已开的轮(窗口冻结语义,见 LineTrack)。"""
SKELETON_ASSET_WEIGHT: float = 0.5
"""资产最厚度量的骨架件系数(设计推断,sim 校准;strategy_v4〔修N5〕口径:
厚度 = 终局件数(副本计星级当量)+ 骨架件数 × 本系数)。"""
FAMILY_BOND_MIN_COUNT: int = 2
"""②类专属羁绊信号阈值:板上+bench 该羁绊计数 ≥ 此值 → 家族信号
(设计推断,sim 校准;取 2 = 「开局即战力档」下限,DOT2/护盾2 同口径)。"""

# ⑤无信号兜底线(comp_definitions_v2 欢愉族·绯英档:「门槛全游戏最低,
# 6 级搜绯英三星,无信号时的默认落点」)。四体系顺来牌支归点2,P1 侧不在本模块。
FALLBACK_COMP_NAME: str = '绯英欢愉'

# 跨线骨架件(strategy_v4「目标件」定义节 class3)。弱意向态只囤这批
# (点0:撤销后去向——只囤跨线骨架件)。
# W50(W47 条2 裁决①):**派生**自 ``cw_plugins.W16_MAJORITY_LINES``
# (≥3 线过半 8 张 + 恰 2 家族过半且非线级 carry 的边界 2 张),不再
# 手写——手写快照的脱锚风险(W45 判定)消除;派生规则与 W16 A2 口径
# 见 ``cw_plugins.cross_line_skeleton``。快照测试锁派生结果 == 原 10 名
# (不等 = 数据错)。
CROSS_LINE_SKELETON: tuple[str, ...] = _cross_line_skeleton()

# ②类专属信号注册表(family → 专属羁绊名)。W47 统一化:原手编 crosswalk
# 迁移为 ``Comp.bond_signal`` 数据字段(cw_comps 各条,值从本表原样迁移;
# 判断层手编数据化——COMP_LIBRARY 演进时随家族条目走,不再双源),本表改为
# 从 COMP_LIBRARY v2 家族派生。语义注(来源=comp_definitions_v2 各套「核心/副档」栏):
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


@dataclass
class IntentionState:
    """锁线/撤销状态机(未锁 unlocked / 锁定 locked / 弱意向 weak)。

    P1(W145/ADR-0357):锁定产物=过渡配方体系对(``p1_pair``)——终局 comp
    锁定只保留①类资格通道;P2+ ``p1_pair`` 恒空,comp 锁定照旧。
    """

    phase: str = 'unlocked'            # 'unlocked' | 'locked' | 'weak'
    locked_comp: str = ''              # 锁定线(COMP_LIBRARY 套名)
    p1_pair: tuple[str, ...] = ()      # P1 配方锁:体系对(过渡体系键;P2+ 恒空)
    lock_layer: int = 0                # 锁定时信号层(撤销出口②的「更高层级」基准)
    lock_plane: int = 0                # 锁定时机(遥测)
    lock_round: int = 0
    forced: bool = False               # 强制锁线产生(P3 入口)
    weak_comp: str = ''                # 降级来源线(遥测;弱意向不指向具体线)
    demoted_endgame: bool = False      # 降格终局标记(全不可达;「赢不了就少输」)
    evicted: set[str] = field(default_factory=set)        # 冻结超限移出候选集的线
    tracks: dict[str, LineTrack] = field(default_factory=dict)
    last_event: str = ''               # 最近一次状态转移(判读/遥测锚点)


@dataclass(frozen=True)
class HoardTarget:
    """锁后效果的输出契约:囤货目标集合(买侧唯一消费面;不改板上)。

    - ``char_targets``:角色件集合(意向线骨架采购集 / 跨线骨架 / 兜底线);
    - ``equip_targets``:装备材料件(意向线 equip_assign 派生,剔除 equip_taboos);
    - ``mode``:'locked' | 'forced' | 'weak' | 'fallback' | 'demoted_endgame'
      | 'p1_pair' | 'p1_transition'(买侧按 mode 区分囤货语义:意向件照囤/
      插件台阶/兜底方向/降格满配骨架;P1 两态=配方对成员集/空窗引擎全集,
      ADR-0357)。
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


def plane_remaining_nodes(state: GameState) -> int:
    """位面内剩余节点数(含当前轮;冻结超限的对照量)。"""
    r = min(max(1, state.round_num), NODES_PER_PLANE)
    return NODES_PER_PLANE - r + 1


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
    """直通终局线资格判定(ADR-0338;W85 五局同型根因修复)。

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


# ===== P1 锁线资格门(W101/ADR-0341;sim A/B 通道)=====
P1_FINAL_LINE_GATE: bool = True
"""P1 终局专属线锁线证据门(ADR-0341)。False=关闭(sim A/B 基线臂)。
诊断来源:W97 §5 P0-1——万敌单C 被③锁 30.5%(61/200),hp 19.7 vs DOT 类
过渡线 28.5-30.7(差 9-11);三线合计 36.5% 局,反事实 +~3.3 hp。"""

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
    与 W85 ②门同一资格源 _direct_line_qualified)。P2/P3 不辖——
    [21] 上场窗口(姬子=7级/万敌=1-9 变阵点)与 1-8 换血点都在 P1 之后,
    终局线在 P2 起锁是 [23] 全文语义。
    """
    if not P1_FINAL_LINE_GATE or state.plane != 1:
        return False
    if _p1_transition_eligible(comp):
        return False
    return not _direct_line_qualified(state, comp.name)


# ===== P1 过渡配方锁(W145/ADR-0357;sim A/B 通道)=====
P1_RECIPE_LOCK: bool = True
"""P1 意向锁定产物=过渡配方体系对(ADR-0357)。False=关闭(sim A/B
基线臂,回 W143 前行为:P1 ②③④可锁终局 comp)。

诊断来源:W143 §3.3——56/100 锁 DOT 系 comp(仅覆盖 DOT2 单引擎,
第二体系件对锁定策略是「非目标件」),engines2 成率 10-19%;绯英⑤兜底
方向零引擎覆盖成率 5%;vs 希儿量子 33%。P1 锁终局 comp 与 [20]
「过渡是配方不是散买」系统性错配。"""

#: 希儿系体系键(单卡二元判定,不占羁绊键;与 cw_sim._engines_count
#: 的希儿系哨兵同口径)。
SEELE_SYSTEM: str = '希儿系'

#: P1 配方对平手序 = 激活占比降序(transition_combos 数据附录:
#: 列车 .360 > DOT .329 > 仙舟 .292;希儿系垫底=单卡依赖)。
_P1_PAIR_PREF: tuple[str, ...] = ('列车同行', '持续伤害', '仙舟', SEELE_SYSTEM)

P1_PAIR_LOCK_MIN_SUPPORT: float = 0.5
"""配方对锁定门槛:最高体系支持度 ≥ 此值才锁(=三羁绊系 ≥1 件或
希儿在手;设计推断,sim 校准)。空窗期([31]① 开局常态)不锁,
囤货方向落四体系全集(p1_transition)。"""


def _owned_chars(state: GameState) -> set[str]:
    """已到手角色名(bench+deployed;不含 shop 可见——[23] 锁定由
    贯穿件=到手,店里出现过不构成方向承诺)。"""
    return {bc.char_id for bc in list(state.bench) + list(state.deployed)
            if bc is not None and bc.char_id}


def _p1_system_support(state: GameState) -> dict[str, float]:
    """四过渡体系的手上资产支持度(bench+deployed;注册表阵营∪流派口径,
    与 ``cw_sim._engines_count`` 同式——多阵营件(桑博=贝+DOT)各系并计)。

    三羁绊系 = 羁绊计数 / 体系档(仙舟3/列车2/DOT2,TRANSITION_TRAITS
    单一源);希儿系 = 希儿在手 0.6 基础分(3费单卡即战力)+ 量2/贝2
    各 0.2(放大器点火;transition_combos 希儿线节)。
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
    if '希儿' in _owned_chars(state):
        sup[SEELE_SYSTEM] = (
            0.6
            + (0.2 if counts.get('量子同频', 0) >= 2 else 0.0)
            + (0.2 if counts.get('贝洛伯格', 0) >= 2 else 0.0)
        )
    else:
        sup[SEELE_SYSTEM] = 0.0
    return sup


def _derive_p1_pair(state: GameState) -> tuple[str, ...]:
    """P1 配方对派生:支持度 top-2(平手按激活占比序),规整为
    ``_P1_PAIR_PREF`` 序的二元组;最高支持度未达门槛 → ()(空窗不锁)。

    体系对随资产**重派生**([20]「变体按来牌选」——支持度只增,变更
    是来牌选型不是 pivot;[23] 冻结语义辖终局线,不辖 P1 配方)。
    """
    sup = _p1_system_support(state)
    ranked = sorted(sup, key=lambda k: (-sup[k], _P1_PAIR_PREF.index(k)))
    if sup[ranked[0]] < P1_PAIR_LOCK_MIN_SUPPORT:
        return ()
    return tuple(sorted(ranked[:2], key=_P1_PAIR_PREF.index))


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
    """候选线资产厚度(点0〔修N5〕口径,勿动):

    板上+bench 中该线终局件数(副本计星级当量:每副本按其 star 计)+ 骨架件数 ×
    SKELETON_ASSET_WEIGHT。终件 = core_chars;骨架件 = 跨线骨架名单 ∩ (core∪shared)。
    """
    pool = list(state.deployed) + list(state.bench)
    star_of = {bc.char_id: bc.star for bc in pool
               if bc is not None and bc.char_id}
    final_pieces = sum(star_of.get(name, 0) for name in comp.core_chars)
    skeleton = (set(CROSS_LINE_SKELETON)
                & (set(comp.core_chars) | set(comp.shared_chars)))
    skeleton_pieces = sum(1 for name in skeleton if name in star_of)
    return float(final_pieces) + skeleton_pieces * SKELETON_ASSET_WEIGHT


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
    ist.lock_layer = sig.layer if not forced else 1   # 强制锁线视作最高层(不可被出口②撤)
    ist.lock_plane = state.plane
    ist.lock_round = state.round_num
    ist.forced = forced
    ist.weak_comp = ''
    ist.last_event = ('forced_lock:' if forced else 'lock:') + sig.comp_name


def update_intention(state: GameState, ist: IntentionState) -> IntentionState:
    """每回合驱动锁线/撤销状态机(就地改 ist 并返回;不碰 GameState)。

    序:降格终局短路 → 锁定态撤销检查(冻结 → miss-N → 高层信号)→
    未锁/弱意向解析(新信号锁线,否则⑤兜底方向)→ P3 入口强制锁线。
    """
    if ist.demoted_endgame:
        return ist   # 降格终局是 absorbing 态(点7 止损序同构,不回弹)
    visible = _visible_chars(state)
    sigs = [s for s in detect_signals(state) if s.comp_name not in ist.evicted]
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
            if track.frozen_rounds > plane_remaining_nodes(state):
                ist.evicted.add(ist.locked_comp)
                ist.phase = 'unlocked'
                ist.locked_comp = ''
                ist.lock_layer = 0
                ist.last_event = f'evict:frozen:{track.frozen_rounds}'
                sigs = [s for s in sigs if s.layer != 3]   # 不触发③
        else:
            track.frozen_rounds = 0
            if core in visible:
                track.miss_count = 0
            else:
                track.miss_count += 1
                if track.miss_count >= CORE_MISS_N:
                    # 撤销出口①:核心 N 轮不可得(只计开窗轮)→ 降级弱意向
                    ist.phase = 'weak'
                    ist.weak_comp = ist.locked_comp
                    ist.locked_comp = ''
                    ist.lock_layer = 0
                    ist.last_event = f'revoke:miss{track.miss_count}'
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
                    ist.last_event = f'revoke:higher:{s.comp_name}(L{s.layer})'
                    revoked = True
                    break   # 「直至新信号」——本轮撤,下轮新信号再锁

    if ist.phase in ('unlocked', 'weak') and not revoked:
        # P1 过渡配方锁(W145/ADR-0357):P1 的锁定产物=体系对;
        # ②③④信号不再锁终局 comp(终局 comp 锁定移至 P2+)——
        # 只保留①类资格通道(直通终局线资格,ADR-0338/0341 语义零改动)。
        # 方向产物=按手上资产派生的体系对(transition_combos 两两组合)。
        if state.plane == 1 and P1_RECIPE_LOCK:
            sigs = [s for s in sigs
                    if _direct_line_qualified(state, s.comp_name)]
            pair = _derive_p1_pair(state)
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

    # 强制锁线(P3 入口无意向;点0〔修N4〕对象限定)
    if state.plane >= 3 and ist.phase != 'locked':
        cands = [c for c in _v2_comps()
                 if c.name not in ist.evicted and _core_reachable(c, state, visible)]
        if cands:
            best = sorted(
                cands,
                key=lambda c: (-_asset_thickness(c, state),
                               encounter_window_rounds(intention_core(c), state.level)),
            )[0]
            _lock(ist, state, IntentionSignal(1, 'forced', best.name,
                                              'P3资产最厚', 1.0), forced=True)
        else:
            # 全部不可达 → 降格终局:四体系过渡板深档强化+通用骨架满配
            ist.demoted_endgame = True
            ist.phase = 'unlocked'
            ist.locked_comp = ''
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
    - P1(W145/ADR-0357):非 comp 锁定局 → 配方方向——体系对成员集
      (p1_pair)/四体系引擎件全集(p1_transition,空窗);绯英⑤兜底
      不再辖 P1(零引擎覆盖,W143 实证 e2 成率 5%);
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
    if state.plane == 1 and P1_RECIPE_LOCK:
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
