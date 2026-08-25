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

**与旧件的关系(载体批新旧交替)**:`cw_signal_lock.py`(Phase A 信号 2 层,
LineV1 载体)与 `cw_line_library_v1` 是旧件,本模块是其 v4 后继——按 COMP_LIBRARY
v2 家族键工作;旧件随 ADR-0336 删除(不再存在),接线已切换。

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
    AUGMENT_COMP_AFFINITY,
    COMP_LIBRARY,
    ENV_COMP_AFFINITY,
    V2_FAMILIES,
    Comp,
    derive_key_equips,
    get_comp,
)
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
    """锁线/撤销状态机(未锁 unlocked / 锁定 locked / 弱意向 weak)。"""

    phase: str = 'unlocked'            # 'unlocked' | 'locked' | 'weak'
    locked_comp: str = ''              # 锁定线(COMP_LIBRARY 套名)
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
      (买侧按 mode 区分囤货语义:意向件照囤/插件台阶/兜底方向/降格满配骨架)。
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
        if comp_name in AUGMENT_COMP_AFFINITY.get(s, {}):
            return True
    return comp_name in ENV_COMP_AFFINITY.get(state.active_env, {})


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
        for comp_name, w in ENV_COMP_AFFINITY.get(state.active_env, {}).items():
            if get_comp(comp_name) is not None:
                out.append(IntentionSignal(1, 'env', comp_name,
                                           f'环境[{state.active_env}]×{w}', w))
    for s in state.active_strategies:
        for comp_name, w in AUGMENT_COMP_AFFINITY.get(s, {}).items():
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
    for c in comps:
        core = intention_core(c)
        if core and core in visible:
            out.append(IntentionSignal(3, 'core_card', c.name,
                                       f'核心[{core}]可见', 1.0))

    # ④ 资源:升费资源等特殊系统锚(④层)。
    # 数据缺口声明:升费资源(道具)暂无 GameState 字段——以升费链角色到手
    # (cost_escalation['角色'] 在 bench/deployed)作「资源到位」代理;字段接入后扩。
    owned = {bc.char_id for bc in list(state.bench) + list(state.deployed)
             if bc is not None and bc.char_id}
    for c in comps:
        ce = c.special_systems.get('cost_escalation')
        if ce and ce.get('角色') in owned:
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
    - weak:只囤跨线骨架件(撤销后去向);
    - unlocked 无信号:⑤兜底 = 绯英档采购集(「无信号时的默认落点」);
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
    if ist.phase == 'weak':
        return HoardTarget(frozenset(CROSS_LINE_SKELETON), frozenset(), 'weak')
    comp = get_comp(FALLBACK_COMP_NAME)
    if comp is None:
        return HoardTarget(frozenset(CROSS_LINE_SKELETON), frozenset(), 'fallback')
    chars, equips = _line_hoard(comp)
    return HoardTarget(frozenset(chars), frozenset(equips), 'fallback')
