"""货币战争 · 终局意向模块(strategy_v4 点0 实现;纯逻辑,不碰游戏/板上)。

单一规格源:`.debug/temp/currency_war/cw_dev/deep_read/strategy_v4.md` 点0
(信号分层①-⑤ / 撤销析取 / 窗口冻结语义 / 强制锁线对象限定 + 降格终局);
攻略信号数据:`comp_definitions_v2.md` 各套(欢愉族绯英档=⑤兜底、黑塔纪元 65%、
万敌 1 费开局即在等)。

**教义边界(user_playstyle)**:
- [21] final 件「买而不上」→ 本模块锁线后**只改囤货方向**(输出「囤货目标集合」
  供买侧消费),不改板上、不产出任何上场/换人动作;
- [23] 终局线由贯穿件锁定,不是 pivot → 锁定后撤销**只有两个出口**(析取):
  ①意向核心断供证据(三条件合取:miss ≥ max(CORE_MISS_N, N_req 闭式)
  ∧ 存在异线核心可达 ∧ 异线资产厚度 ≥ A_min——统计证据+替代资产证据,
  只计刷新窗已开的轮,窗口冻结语义);②更高层级替代
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
只保留①类资格通道,P2+ 照旧锁 comp。(配方锁行为无条件,F5 清偿见本文件 ADR-0357 落点注释)。

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
    gate_counterfactual,
    register_gate_block,
    survival_gate,
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
    """**P1 锁定目标数据形态(ADR-0357;显式可读,约束基准契约)**:

    - 读口 = ``session.v3_intention.p1_pair``——四体系键的二元组,按
      ``_P1_PAIR_PREF`` 序规整,非空即「P1 锁定帧目标=该体系对」;
      空元组=空窗期(未锁);P2+ 恒空(P2+ 锁定目标=``locked_comp``)。
    - 体系键域与判据单一源:三羁绊键=``TRANSITION_TRAITS``
      (仙舟/列车同行/持续伤害),希儿系=``SEELE_SYSTEM`` 哨兵键
      (与 ``cw_battle_calib._engines_count`` 同口径)。
    - 遥测:``serialize_intention(分包期 3 自 telemetry 下沉)`` 字段全量序列化自动
      携带(不隐式——单帧锁断言 p1_pair 落 decisions 行,见 W145 测试)。
    - **后续「通道约束批」(W143 补充判读:决策通道两面孔按锁定目标约束/
      末轮禁用)以本字段为约束基准**——opportunistic/bond_fallback 通道
      的「目标/非目标」判定输入 = 本字段(非空时)∪ locked_comp。
    """
    lock_layer: int = 0                # 锁定时信号层(撤销出口②的「更高层级」基准)
    prev_lock_layer: int = 0
    """被撤线的原锁层暂存(设计件 w665_p2p3_linegate/DESIGN.md §3-3 R-C/FM-11):撤销出口①/②
    降级 weak 时写入被撤的 lock_layer;门闩一次性回锁时恢复到 lock_layer,
    使出口②撤销面不被回锁信号( layer=1 )收窄。生命周期=回锁消费后保留
    至位面切换(闩清零时一并清零,陈旧值不跨位面);0=无暂存。"""
    lock_plane: int = 0                # 锁定时机(遥测)
    lock_round: int = 0
    transition_pair: tuple[str, ...] = ()  # ①锁局过渡对副方向(W166/ADR-0367)
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
    - 遥测:``serialize_intention(分包期 3 自 telemetry 下沉)`` 字段全量序列化自动携带。
    """
    forced: bool = False               # 强制锁线产生(P3 入口)
    weak_comp: str = ''                # 降级来源线(遥测;弱意向不指向具体线)
    demoted_endgame: bool = False      # 降格终局标记(全不可达;「赢不了就少输」)
    evicted: set[str] = field(default_factory=set)        # 冻结超限移出候选集的线
    pair_evicted: set[str] = field(default_factory=set)
    """R3 断供驱逐(配方对域):断供超限移出候选的**体系键**集(ADR-0465;
    蓝图 §4.3-R3 冻结驱逐语义从 LineTrack 推广到配方对)。与 ``evicted``
    分域:本集辖体系键(TRANSITION_TRAITS ∪ SEELE_SYSTEM),不与
    comp 套名混淆;驱逐后 pair 重派生时排除(消费面 = ``_derive_p1_pair``
    /``p1_early_pair`` 的 exclude 参数)。局级重置随 ist 族(每局新建
    StrategySession,跨局零残留)。"""
    pair_drought: dict[str, int] = field(default_factory=dict)
    """R3 断供驱逐的体系级断供计数器(体系键 → 连续无新件可见轮数;
    计数语义同 LineTrack.frozen_rounds——成员在可见面(在店∪到手)
    出现即清零)。"""
    supply_drought: dict[str, int] = field(default_factory=dict)
    """方向侧供给衰减计数器(W802 兑现链方向侧;体系键 → 连续零在店
    轮数 t,support′ = γ^t·support + β·[成员在店] 的衰减坐标)。
    [坐标系] 键域 = TRANSITION_TRAITS 三羁绊 ∪ SEELE_SYSTEM;取值时机 =
    每 game-round 恰一次由 update_intention._update_supply_decay 现读
    shop 刷新(成员在店清零,零在店 +1);缺键 = 尚无观测帧(排序侧
    退纯资产支持度,不施加衰减/加项)。开关关恒空 dict(零漂移)。"""
    tracks: dict[str, LineTrack] = field(default_factory=dict)
    last_event: str = ''               # 最近一次状态转移(判读/遥测锚点)
    revoke_evidence: dict[str, object] = field(default_factory=dict)
    """撤销出口①开窗的证据字段快照(实机判读锚点,设计 R3.5「无证据
    字段的开窗=守卫失效」;serialize_intention 全量序列化自动携带)。

    - 写入端 = update_intention 撤销出口①开窗分支(唯一写入点,每次
      开窗整体覆写);keys:kind/miss_count/n_req/q/eps/alt_comp/e_alt/
      asset_thickness/a_min(语义见该分支注释)。
    - 清空时机 = _lock(重锁即证据消费完毕)与冻结驱逐/降格(转移
      不经撤销,证据随之失效)。空 dict = 本局尚无撤销开窗。"""
    # ===== W948 转型臂状态族(设计件 w948_transform_design/DESIGN.md §2;
    # registry.intention_stagnation_arm_enabled / p2_entry_weak_target_enabled
    # 默认关=恒缺省值零漂移;全部消费/写入点在 update_intention 与
    # hoard_target_set,遥测经 serialize_intention 全量序列化自动携带)=====
    stagnate_cool: dict[str, int] = field(default_factory=dict)
    """停滞改判冷却驻留(W948 防振荡;线名 → 触发位面号):每线每位面至多
    一次停滞降级(事件频率上界=线数,结构性排除逐帧摇摆;位面切换时非当前
    位面的条目清位面切换段)。写入端 = update_intention 停滞触发分支(唯一)。"""
    stagnate_plane: int = 0
    """停滞窗级计数所属位面(坐标系=位面序;0=尚无计数):位面切换时
    update_intention 入口检测不一致即清全部窗级计数(陈旧进度证据不跨位面)。"""
    stagnate_rounds_in_window: int = 0
    """当前评估窗内已计入的驱动轮数(坐标系=窗内轮,分母=registry
    .stagnate_window_rounds;取值时机=每驱动轮恰一次,update_intention 写)。"""
    stagnate_windows_hit: int = 0
    """连续停滞窗数(坐标系=连续窗,分母=registry.stagnate_windows;任一窗
    判非停滞即归零)。达阈值即触发停滞降级,触发后清零。"""
    stagnate_gap_ref: int | None = None
    """窗首帧的锁线采购集缺口快照(gap=锁线 hoard 角色目标件中尚未到手的件数;
    None=窗首帧未采样)。对照量:窗末 gap 未下降(收敛度不足)=停滞条件之一。"""
    stagnate_hp_ref: int | None = None
    """窗首帧 hp 快照(战力侧确证:窗末 hp 净下降才计停滞,防金筹措期误判;
    None=窗首帧未采样)。"""
    stagnate_form_ok_all: bool = True
    """窗内 form_ok 恒 False 贯穿位(当帧谓词逐帧 AND;form_ok 读
    session.v3_form_ok 最近一次成型判定,缺帧=False=计入未成型)。
    True=整窗未成型(停滞资格在);窗界评估后清回 True 重开。"""
    stagnate_weak_rounds: int = 0
    """stagnate-weak 态持续驱动轮数(含触发轮;坐标系=轮,取值时机=每驱动轮;
    phase 离开 weak 或证据被消费即清零)。salvage_window_rounds 的对照量。"""
    stagnate_salvage: bool = False
    """salvage 续命子模式在效位(W948 出口分支·丙;weak 的子模式,非
    absorbing——新信号仍可落新线救回)。写入端 = update_intention salvage
    推导段(唯一);读端 = hoard_target_set(mode='salvage' 采购集转向)。
    P3 demoted_endgame(absorbing)语义零改动,不进本字段辖域。"""
    weak_placeholder: str = ''
    """P2 入口弱目标占位线名(W948 伴生入口·乙;'' =无占位):进 P2 清
    p1_pair 后仍 unlocked 且无即时信号时,按带入资产(资产最厚,与 P3 强制
    锁线同判据)派生的初始假设方向。可被任何信号推翻(不进 locked 态,只
    改 hoard 方向,优先于⑤绯英兜底);读端 = hoard_target_set
    (mode='p2_weak_target')。坐标系=线名(COMP_LIBRARY 套名)。"""


@dataclass(frozen=True)
class HoardTarget:
    """锁后效果的输出契约:囤货目标集合(买侧唯一消费面;不改板上)。

    - ``char_targets``:角色件集合(意向线骨架采购集 / 跨线骨架 / 兜底线);
    - ``equip_targets``:装备材料件(意向线 equip_assign 派生,剔除 equip_taboos);
    - ``mode``:'locked' | 'forced' | 'weak' | 'fallback' | 'demoted_endgame'
      | 'p1_pair' | 'p1_transition' | 'salvage' | 'p2_weak_target'(买侧按
      mode 区分囤货语义:意向件照囤/插件台阶/兜底方向/降格满配骨架/
      W948 salvage 续命=跨线骨架停线内投入/p2_weak_target 弱占位方向,
      ADR-0357/ADR-0509)。
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


def _line_env_qualified(state: GameState, comp_name: str) -> bool | None:
    """累积型线强环境判据(W607 H1;ADR-0461)。

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


# ===== P1 锁线资格门(W101/ADR-0341)=====
# F5 清偿(ADR-0465 后治理蓝图,git 历史):原模块级 flag P1_FINAL_LINE_GATE/P1_RECIPE_LOCK/
# P1_LOCK_TRANSITION_PAIR 删除,行为无条件化——三门的 sim A/B 已终裁
# (0341/0357/0367),开臂前置因冻结令消失=第 4 态清理;A/B 基线臂改由
# git 冻结快照构造(flag=False 回退通道随之消失,回退=git revert)。

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
    if state.plane != 1:
        return False
    if _p1_transition_eligible(comp):
        return False
    return not _direct_line_qualified(state, comp.name)


#: 希儿系体系键(单卡二元判定,不占羁绊键;与 cw_battle_calib._engines_count
#: 的希儿系哨兵同口径)。
SEELE_SYSTEM: str = '希儿系'

#: P1 配方对平手序 = 激活占比降序(transition_combos 数据附录:
#: 列车 .360 > DOT .329 > 仙舟 .292;希儿系垫底=单卡依赖)。
_P1_PAIR_PREF: tuple[str, ...] = ('列车同行', '持续伤害', '仙舟', SEELE_SYSTEM)

P1_PAIR_LOCK_MIN_SUPPORT: float = 0.5
"""配方对锁定门槛:最高体系支持度 ≥ 此值才锁(=三羁绊系 ≥1 件或
希儿在手;设计推断,sim 校准)。空窗期([31]① 开局常态)不锁,
囤货方向落四体系全集(p1_transition)。"""


# ===== ①锁局过渡对保护副方向(W166/ADR-0367)=====
# 诊断来源:W164 §1.3——inject on 口径 strict_mal 0.20 vs off 0.05 的
# 差值 15 局全部来自①资格通道:注入信号 r1 锁终局 comp,其采购集把囤货
# 方向从过渡引擎引开(engines2_by_r6 0.27→0.15)+ evolve 按 comp 线换档
# 拆过渡体系(S2 挤出 19/20 mal 局)=W145 主灶(ADR-0357)在①通道的残留。


def _owned_chars(state: GameState) -> set[str]:
    """已到手角色名(bench+deployed;不含 shop 可见——[23] 锁定由
    贯穿件=到手,店里出现过不构成方向承诺)。"""
    return {bc.char_id for bc in list(state.bench) + list(state.deployed)
            if bc is not None and bc.char_id}


def _p1_system_support(state: GameState) -> dict[str, float]:
    """四过渡体系的手上资产支持度(bench+deployed;注册表阵营∪流派口径,
    与 ``cw_battle_calib._engines_count`` 同式——多阵营件(桑博=贝+DOT)各系并计)。

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


def _derive_p1_pair(state: GameState,
                    exclude: frozenset[str] = frozenset(),
                    registry: DecisionV2Registry | None = None,
                    drought: dict[str, int] | None = None,
                    prev_pair: tuple[str, ...] = (),
                    ) -> tuple[str, ...]:
    """P1 配方对派生:支持度 top-2(平手按激活占比序),规整为
    ``_P1_PAIR_PREF`` 序的二元组;最高支持度未达门槛 → ()(空窗不锁)。

    ``exclude``:R3 断供驱逐的体系键集(移出候选后重派生;蓝图 §4.3-R3)。
    体系对随资产**重派生**([20]「变体按来牌选」——支持度只增,变更
    是来牌选型不是 pivot;[23] 冻结语义辖终局线,不辖 P1 配方)。

    ``drought``/``prev_pair``/``registry``:方向侧供给感知支持度
    (``_supply_prime``,γ 衰减)与切换滞回(``_pair_hysteresis``,P16
    δ 复用)的输入;开关关时三项不被消费(排序退纯资产支持度,逐位
    旧行为——W802 兑现链方向侧零漂移锚)。
    """
    reg = registry or DEFAULT_REGISTRY
    sup = _supply_prime(_p1_system_support(state), drought, reg)
    ranked = [k for k in sorted(sup, key=lambda k: (-sup[k], _P1_PAIR_PREF.index(k)))
              if k not in exclude]
    ranked = _pair_hysteresis(prev_pair, ranked, sup, reg)
    if not ranked or sup[ranked[0]] < P1_PAIR_LOCK_MIN_SUPPORT:
        return ()
    return tuple(sorted(ranked[:2], key=_P1_PAIR_PREF.index))


#: R3 断供驱逐阈值(轮;保守先验 ≥5,同老栈 DROUGHT_BAIL 同族先验;
#: 探针批标定挂账=说服包 R3 断供探针)。语义:某体系成员连续 N 轮
#: 不在可见面(在店∪到手)→ 该体系移出 pair 候选、pair 重派生。
PAIR_DROUGHT_EVICT_ROUNDS: int = 5


def _update_pair_drought(state: GameState, ist: IntentionState,
                         visible: set[str]) -> None:
    """R3 断供驱逐计数器(每 game-round 恰一次,由 update_intention 驱动)。

    辖域 = P1 ∧ 有 pair 方向(p1_pair ∪ transition_pair);对 pair 内每
    体系:成员集(``_pair_members``)与**在店新件**(shop——「补不进的
    新件」量的是供给渠道,到手资产不救供给,蓝图 §4.3-R3 原文语义)
    无交集 → 连续断供 +1,有交集清零;断供 ≥
    ``PAIR_DROUGHT_EVICT_ROUNDS`` → 体系入 ``pair_evicted``、计数清零、
    pair 下轮派生自然排除(重派生消费面在 update_intention 的两个
    pair 派生支)。
    """
    if state.plane != 1:
        return
    systems = set(ist.p1_pair) | set(ist.transition_pair)
    if not systems:
        return
    shop_names = {getattr(c, 'name', '') or '' for c in (state.shop or [])}
    for sys in systems:
        if sys in ist.pair_evicted:
            continue
        members = _pair_members((sys,))
        if members & shop_names:
            ist.pair_drought[sys] = 0
            continue
        n = ist.pair_drought.get(sys, 0) + 1
        ist.pair_drought[sys] = n
        if n >= PAIR_DROUGHT_EVICT_ROUNDS:
            ist.pair_evicted.add(sys)
            ist.pair_drought[sys] = 0
            ist.last_event = f'evict:pair_drought:{sys}:{n}'


def _update_supply_decay(state: GameState, ist: IntentionState,
                         registry: DecisionV2Registry | None) -> None:
    """方向侧供给衰减计数(W802 兑现链设计侧四;每 game-round 恰一次,
    与断供驱逐同一驱动点)。对 support′ 支持度全体系键:成员在店 →
    清零;零在店 → +1。开关关恒不动(supply_drought 保持空 dict,
    排序侧退纯资产支持度——零漂移)。驱逐计数器(pair_drought)与本
    计数器分域:前者辖 pair 成员资格(硬驱逐),本计数辖所有体系的
    相对排序(连续单调衰减),作用面不同(W796 面 5「量级相近≠等效」)。
    """
    reg = registry or DEFAULT_REGISTRY
    if not (reg.realization_chain_enabled
            and reg.realization_direction_enabled):
        return
    shop_names = {getattr(c, 'name', '') or '' for c in (state.shop or [])}
    for bond, _t in TRANSITION_TRAITS:
        if _bond_members(bond) & shop_names:
            ist.supply_drought[bond] = 0
        else:
            ist.supply_drought[bond] = ist.supply_drought.get(bond, 0) + 1
    if '希儿' in shop_names:
        ist.supply_drought[SEELE_SYSTEM] = 0
    else:
        ist.supply_drought[SEELE_SYSTEM] = \
            ist.supply_drought.get(SEELE_SYSTEM, 0) + 1


def _supply_prime(sup: dict[str, float], drought: dict[str, int] | None,
                  registry: DecisionV2Registry) -> dict[str, float]:
    """γ 衰减供给感知支持度 support′(设计侧四;P31① 落码形态):

        support′(s,t) = γ^t·support(s) + β·[成员在店]

    - t = ``supply_drought`` 连续零在店轮数(缺键=尚无观测帧 → 纯资产
      支持度,不施加衰减也不加项——首帧不造基准偏置);
    - γ 经验带 [0.7,0.8] 量级锚(注册表 realization_direction_gamma,
      sim 扫描标定挂账);β = realization_direction_beta(占位);
    - 「成员在店」= 衰减计数当帧清零(t==0)——ρ 窗口 W 占位 1 帧,
    β/λ/W 同批标定(PREREG §6)。
    """
    if not (registry.realization_chain_enabled
            and registry.realization_direction_enabled) or not drought:
        return sup
    out: dict[str, float] = {}
    for k, v in sup.items():
        t = drought.get(k)
        if t is None:
            out[k] = v
        elif t == 0:
            out[k] = v + registry.realization_direction_beta
        else:
            out[k] = v * (registry.realization_direction_gamma ** t)
    return out


def _pair_hysteresis(prev_pair: tuple[str, ...],
                     ranked: list[str], sup: dict[str, float],
                     registry: DecisionV2Registry) -> list[str]:
    """方向切换滞回(P16 复用,δ=``registry.line_switch_theta`` 单一源;
    锁 #7):support′ 差 < θ 不切换——现方向 top 保持在位(防振荡频率
    硬上限 1/(2·D_min) 的排序层等价形态)。开关关/prev 不在候选集
    (已被驱逐等)→ 序不变。"""
    if not (registry.realization_chain_enabled
            and registry.realization_direction_enabled):
        return ranked
    if not prev_pair or prev_pair[0] not in ranked:
        return ranked
    if sup[ranked[0]] - sup[prev_pair[0]] < registry.line_switch_theta:
        return [prev_pair[0]] + [k for k in ranked if k != prev_pair[0]]
    return ranked


def p1_early_pair(state: GameState,
                  ist: IntentionState | None) -> tuple[str, ...]:
    """P1 早期新件买入门的配方对读口(W179/ADR-0372;只读,不落字段)。

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
    """体系对 → 配方伪 comp(P1 配方锁帧的 target 载体物化;W578)。

    语义:ADR-0357 把 P1 意向锁定产物定为体系对(p1_pair)后,
    ``session.target_comp`` 在配方锁帧恒 None——部署选人/评分管线/
    投资装备钩子等既有 target 消费者从此全盲(断线实锤:局20/22
    引擎件躺 bench、散脸占板,decisions.target_comp 全程空串)。
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
      分歧裁决与合流判据见 ADR(W578)。
      注:桥线平局偏好语义(原 cw_bridge_pool.pick_bridge 的 r253
      P1 tie-break 偏 xianzhou_dot)已随选桥函数退役,若 v2 需要
      同等平滑性偏好需另行设计。
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
    """候选线资产厚度(点0〔修N5〕口径,勿动):

    板上+bench 中该线终局件数(副本计星级当量:每副本按其 star 计)+ 骨架件数 ×
    SKELETON_ASSET_WEIGHT。终件 = core_chars;骨架件 = 跨线骨架名单 ∩ (core∪shared)。
    """
    pool = list(iter_occupied_deployed(state.deployed)) \
        + [b for b in state.bench if b is not None]
    star_of = {bc.char_id: bc.star for bc in pool
               if bc is not None and bc.char_id}
    final_pieces = sum(star_of.get(name, 0) for name in comp.core_chars)
    skeleton = (set(CROSS_LINE_SKELETON)
                & (set(comp.core_chars) | set(comp.shared_chars)))
    skeleton_pieces = sum(1 for name in skeleton if name in star_of)
    return float(final_pieces) + skeleton_pieces * SKELETON_ASSET_WEIGHT


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
    证据(设计=`.debug/temp/currency_war/w396_r2r3_design/DESIGN.md`
    R3.1;治 W386 BP1「拍死计数把正常噪声送进撤销」)。ε 取
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
    # W166/ADR-0367:①锁局(P1∧配方锁开)同时派生过渡对副方向
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


def _switch_gate_open(ist: IntentionState, state: GameState,
                      session: StrategySession | None,
                      sig: IntentionSignal,
                      registry: DecisionV2Registry | None) -> bool:
    """C4 存活轮数门在 v2 换线通道的接线(判据单一源=cw_line_switch
    .survival_gate;W376 实证 default 栈消费点不在生产 v2 栈后的补线)。

    辖域=撤销出口①/②降级弱意向后、新信号锁**另一条线**(weak_comp≠
    候选线)——这是 v2 栈语义下的「换线」决策位置;初始锁线(unlocked
    →lock)、同线重锁(weak_comp==候选线)与 P3 强制锁线(无在先承诺
    线,兜底语义)均非换线,不辖。门内部自辖 plane≥2 与总开关
    (line_switch_survival_gate_enabled 关=放行,零漂移);e_alt=候选线
    E_rounds(cw_line_switch.e_rounds,与 default 栈换线判据同尺);
    registry 由调用方注入(None=缺省表,与 cw_line_switch 同惯例),
    DecisionV2Strategy 透传 self.registry 使 A/B 注入臂可达。
    拦截记账=register_gate_block 线对去重(同对同局只发一次日志,
    消费侧约定同 default 栈)。
    """
    if not (ist.phase == 'weak' and ist.weak_comp
            and sig.comp_name != ist.weak_comp):
        return True
    comp = get_comp(sig.comp_name)
    if comp is None:
        return True
    e_alt = e_rounds(comp, state, registry)
    reg = registry or DEFAULT_REGISTRY
    ok, why = survival_gate(state, session, e_alt, registry)
    # 决策位记账(设计件 w665_p2p3_linegate/DESIGN.md §3-2/R3,决策位纪律平移(ADR-0470 同款)):拦截位
    # 与反事实判定位写 session(帧级;update_intention 每帧入口清零),
    # 检查器只做位一致性核验、禁复算判据式。on 臂=门判定本身即该位,
    # 不重复算(守卫独立性);off 臂=gate_counterfactual 反事实记账。
    if session is not None:
        session.v3_line_gate_blocked = not ok
        session.v3_line_gate_cf_blocked = (
            (not ok) if reg.line_switch_survival_gate_enabled
            else gate_counterfactual(state, session, e_alt, reg))
    if ok:
        return True
    if session is not None:
        cnt = register_gate_block(session, ist.weak_comp, sig.comp_name)
    else:
        cnt = 1   # 无 session 时无从挂计数,按首拦口径发日志
    if cnt == 1:
        log.warning('[cw][d2] 存活轮数门拦换线 %s → %s:%s (hp=%s,新线E=%.2f)',
                    ist.weak_comp, sig.comp_name, why, state.hp, e_alt)
    return False


def _stagnation_tick(state: GameState, ist: IntentionState,
                     session: StrategySession | None,
                     registry: DecisionV2Registry | None) -> bool:
    """W948 转型臂·停滞评估窗推进与降级触发(设计件
    w948_transform_design/DESIGN.md §2.1-§2.2;ADR-0509)。

    辖域=仅 P2 锁定态(P1 有自有滞回重派生,P3 有强制锁线/降格既有通道)。
    判据=过程量「锁线采购集缺口收敛度」(窗界对照 gap_t vs gap_{t-W},
    gap = 锁线 hoard 角色目标件中尚未到手件数,存量单一源 = _line_hoard;
    **不升格 form_score 进判据**——ADR-0353 裁定其为纯遥测口径,重新升格
    = 推翻既有裁决):窗末 gap 未下降(无收敛)∧ hp 净下降(战力侧确证,
    防「金筹措期」误判)∧ form_ok 恒 False 贯穿评估窗(当帧谓词逐帧 AND,
    读 session.v3_form_ok 最近一次成型判定)= 一个停滞窗;连续
    registry.stagnate_windows 个停滞窗 → 触发降级。

    触发动作完全复用撤销出口①的降级形态与 revoke_evidence 字段契约
    (phase: locked→weak / weak_comp=原线 / prev_lock_layer 暂存),证据
    kind 独立命名 'stagnate'(进度侧证据,不新增出口①的供给侧证据类型,
    ADR-0319/0436 划界见 DESIGN §2.7);不走 _switch_gate_open 门拦截路径、
    不受回锁闩抑制(那是 weak→异线锁的事),撤后当轮不重锁由调用方置
    revoked 承接(状态机一回合最多一次转移语义不变)。

    防振荡(DESIGN §2.1):单向降级(本函数只做 locked→weak,不反向);
    冷却驻留 stagnate_cool[线]=位面(同线本位面只改判一次)。

    返回 True=本轮发生停滞降级(调用方据此置 revoked);开关关恒 False
    且不写任何状态(零漂移)。
    """
    reg = registry or DEFAULT_REGISTRY
    if not reg.intention_stagnation_arm_enabled:
        return False
    if state.plane != 2:
        return False
    line = ist.locked_comp
    comp = get_comp(line) if line else None
    if comp is None:
        return False
    if ist.stagnate_cool.get(line) == state.plane:
        return False   # 冷却驻留:同线本位面至多一次改判
    ist.stagnate_plane = state.plane   # 计数所属位面(位面切换清零键)
    gap = len([c for c in _line_hoard(comp)[0] if c not in _owned_chars(state)])
    hp = state.hp
    if bool(getattr(session, 'v3_form_ok', False)):
        ist.stagnate_form_ok_all = False
    if ist.stagnate_gap_ref is None:   # 窗首帧采样(窗界对照基准)
        ist.stagnate_gap_ref = gap
        ist.stagnate_hp_ref = hp
    ist.stagnate_rounds_in_window += 1
    if ist.stagnate_rounds_in_window < reg.stagnate_window_rounds:
        return False
    # 窗界评估:对照窗首快照;窗末值滚入下窗首(窗间无缝衔接)
    g0 = ist.stagnate_gap_ref if ist.stagnate_gap_ref is not None else gap
    h0 = ist.stagnate_hp_ref if ist.stagnate_hp_ref is not None else hp
    stagnant = gap >= g0 and hp < h0 and ist.stagnate_form_ok_all
    ist.stagnate_rounds_in_window = 0
    ist.stagnate_gap_ref = gap
    ist.stagnate_hp_ref = hp
    ist.stagnate_form_ok_all = True
    if not stagnant:
        ist.stagnate_windows_hit = 0
        return False
    ist.stagnate_windows_hit += 1
    if ist.stagnate_windows_hit < reg.stagnate_windows:
        return False
    # 触发:降级 weak(出口①同款字段契约;kind='stagnate')
    ist.prev_lock_layer = ist.lock_layer
    ist.phase = 'weak'
    ist.weak_comp = line
    ist.locked_comp = ''
    ist.lock_layer = 0
    ist.transition_pair = ()   # weak 不辖(W166,同 scope 契约)
    ist.revoke_evidence = {
        'kind': 'stagnate',
        'windows': ist.stagnate_windows_hit,
        'gap_from': g0,
        'gap_to': gap,
        'hp_from': h0,
        'hp_to': hp,
        'plane': state.plane,
    }
    ist.stagnate_cool[line] = state.plane
    ist.stagnate_windows_hit = 0
    ist.stagnate_rounds_in_window = 0
    ist.stagnate_gap_ref = None
    ist.stagnate_hp_ref = None
    ist.last_event = (f'revoke:stagnate:{line}'
                      f'(gap {g0}->{gap},hp {h0}->{hp})')
    return True


def _p2_entry_weak_target(state: GameState, ist: IntentionState,
                          visible: set[str]) -> str:
    """W948 伴生入口·乙:P2 空位的弱占位线派生(设计件
    w948_transform_design/DESIGN.md §2.1;registry.p2_entry_weak_target_enabled
    默认关=不派生)。

    判据=带入资产最厚(与 P3 强制锁线同式:候选 = v2 家族 ∖ evicted ∧
    核心可达;排序 = _asset_thickness 降序,平局取候选序首位——确定性,
    sim 可锁)。弱占位只是初始假设:不进 locked 态、可被任何信号推翻,
    停滞臂对它同样辖(经 weak 下游)。
    """
    cands = [c for c in _v2_comps()
             if c.name not in ist.evicted
             and _core_reachable(c, state, visible)]
    if not cands:
        return ''
    return sorted(cands,
                  key=lambda c: -_asset_thickness(c, state))[0].name


def update_intention(state: GameState, ist: IntentionState,
                     session: StrategySession | None = None,
                     registry: DecisionV2Registry | None = None
                     ) -> IntentionState:
    """每回合驱动锁线/撤销状态机(就地改 ist 并返回;不碰 GameState)。

    序:降格终局短路 → 锁定态撤销检查(冻结 → miss-N → 高层信号 →
    停滞评估〔W948 转型臂,registry.intention_stagnation_arm_enabled 辖,
    ADR-0509〕)→ 未锁/弱意向解析(新信号锁线,否则⑤兜底方向)→
    P3 入口强制锁线。
    """
    if ist.demoted_endgame:
        return ist   # 降格终局是 absorbing 态(点7 止损序同构,不回弹)
    if state.plane != 1 and ist.transition_pair:
        # 出 P1:过渡对副方向退场(W166;P2+ 锁定目标=locked_comp 唯一)
        ist.transition_pair = ()
    visible = _visible_chars(state)
    # 换线门决策位逐帧清零(设计件 w665_p2p3_linegate/DESIGN.md §3-2;帧级坐标系:本轮无
    # 换线辖域评估 → 位=False,防上帧位残留污染账本行)
    if session is not None:
        session.v3_line_gate_blocked = False
        session.v3_line_gate_cf_blocked = False
    # 门闩位面切换清零(设计件 w665_p2p3_linegate/DESIGN.md §3-3 末条):闩=位面内滞回,
    # 出位面即清;同步清各线 miss_count(陈旧断供证据不跨位面驱动出口①)
    # 与 prev_lock_layer(暂存已消费,不跨位面残留)。
    if session is not None and getattr(session, 'v3_line_gate_latch', False) \
            and getattr(session, 'v3_line_gate_latch_plane', None) \
            != state.plane:
        session.v3_line_gate_latch = False
        session.v3_line_gate_latch_plane = None
        for t in ist.tracks.values():
            t.miss_count = 0
        ist.prev_lock_layer = 0
    # W948 停滞计数位面切换清零(设计件 w948_transform_design/DESIGN.md §2.2
    # 数据流末条:窗级进度证据与冷却驻留不跨位面;弱占位同理退场。开关关恒
    # 跳过=零漂移)。
    _reg948 = registry or DEFAULT_REGISTRY
    if _reg948.intention_stagnation_arm_enabled \
            and ist.stagnate_plane not in (0, state.plane):
        ist.stagnate_plane = 0
        ist.stagnate_rounds_in_window = 0
        ist.stagnate_windows_hit = 0
        ist.stagnate_gap_ref = None
        ist.stagnate_hp_ref = None
        ist.stagnate_form_ok_all = True
        ist.stagnate_salvage = False
        ist.stagnate_weak_rounds = 0
        ist.stagnate_cool = {k: v for k, v in ist.stagnate_cool.items()
                             if v == state.plane}
    if _reg948.p2_entry_weak_target_enabled and ist.weak_placeholder:
        ist.weak_placeholder = ''
    # R3 断供驱逐(ADR-0465):每 game-round 恰一次的体系级断供计数
    # (pair 方向在场时辖;驱逐写入 pair_evicted,下方两派生支消费)。
    _update_pair_drought(state, ist, visible)
    # 方向侧供给衰减计数(W802;开关关恒不动——零漂移)
    _update_supply_decay(state, ist, registry)
    sigs = [s for s in detect_signals(state) if s.comp_name not in ist.evicted]
    revoked = False   # 本轮是否发生撤销(出口①miss/出口②):撤后当轮不重锁——
    # 「意向降级为弱意向……直至新信号」= 新信号指下一轮起的信号;同轮撤+锁会让
    # 弱意向态不可观测(判读/遥测断档),状态机一回合最多一次转移。

    if ist.phase == 'locked':
        # 门闩存续期(设计件 w665_p2p3_linegate/DESIGN.md §3-3 R-A):同位面闩置位后撤销出口
        # ①②抑制——「锁线保生存」吸收态,miss 照涨但无消费(砍断周期环
        # 驱动源,§3-4 轨迹证明闩后零转移)。窗口冻结驱逐(evict)非出口
        # ①②,保留自身语义(刷新窗冻结超限属候选集卫生,非换线裁决)。
        latch_active = (
            session is not None
            and getattr(session, 'v3_line_gate_latch', False)
            and getattr(session, 'v3_line_gate_latch_plane', None)
            == state.plane)
        comp = get_comp(ist.locked_comp)
        core = intention_core(comp) if comp else ''
        track = _track(ist, ist.locked_comp)
        ch = CHARACTERS.get(core) if core else None
        window_open = bool(ch) and refresh_prob(state.level, ch.cost) > 0
        if not window_open:
            # 窗口冻结:未开窗不计 miss;冻结超位面剩余节点 → 移出候选集,
            # 意向回⑤无信号态——**不触发③**(该轮③信号被排除)
            track.frozen_rounds += 1
            # ADR-0366:冻结超限对照量按本位面真值(session 透传,P2=7)
            # D3 修正(W696 审计):驱逐纳入闩辖——驱逐产生设计外转移
            # locked→unlocked→同帧可无门落新线,破坏闩「转移冻结」吸收
            # 态(DESIGN v3 §3-3)。裁决=闩存续期驱逐**挂起**(非触发闩
            # 语义合法转移):frozen_rounds 继续累计,位面切换清闩后恢复
            # 既有驱逐路径(下一位面首帧即按累计值正常处置,不跨位面失察)。
            if latch_active:
                pass
            elif track.frozen_rounds > plane_remaining_nodes(state, session):
                ist.evicted.add(ist.locked_comp)
                ist.phase = 'unlocked'
                ist.locked_comp = ''
                ist.lock_layer = 0
                ist.transition_pair = ()   # 锁撤销 → 副方向随之退场(W166)
                ist.revoke_evidence = {}   # 驱逐不经撤销,证据随之失效
                ist.last_event = f'evict:frozen:{track.frozen_rounds}'
                sigs = [s for s in sigs if s.layer != 3]   # 不触发③
        else:
            track.frozen_rounds = 0
            if core in visible:
                track.miss_count = 0
            else:
                track.miss_count += 1
                # 撤销出口①(三条件合取,缺一不开窗;设计 R3.1):
                #   ① miss ≥ max(CORE_MISS_N, N_req)——N_req 由 ε 容忍
                #     概率闭式推导(证据组 A),CORE_MISS_N 保留为上限保险
                #     (防牌池数据异常使 N_req 过小);仅达拍死计数不再
                #     开窗(W386 BP1:门放行噪声换线的病灶在此收窄)。
                #   ② 证据组 B:存在异线 comp 核心可达 ∧ 资产厚度 ≥ A_min
                #     (registry.revoke_evidence_min_thickness,冻结池
                #     随机厚度基线 f0 曲线 5% 点测量值,见其注释)。
                # 误开窗操作定义(开窗局到局末未发生「新线落锁且新线
                # 最终成型(form_score 达标)」=纯扰动)与 A/B 判据
                # (注入臂 n=300/臂、池指纹锚,生产阈值零动):
                #   a) evidence 臂触发率 >0 且逐例带证据字段(off 臂 ≈0
                #      与 W379 实测一致;off 臂逐位=零漂移锚);
                #   b) 开窗局中新线成型局 ≥2/3,低于此=证据组 B 分辨力
                #      不足,回炉 A_min/ε;
                #   c) 开窗局 P2 存活轮数分布不后移(C3 无效判据口径)→
                #      出口在 sim 牌池概念无效,如实记「结构件」,不硬开臂。
                reg = registry or DEFAULT_REGISTRY
                n_req = core_miss_n_required(
                    core, state.level, reg.revoke_miss_tolerance_eps)
                if not latch_active and \
                        track.miss_count >= max(CORE_MISS_N, n_req):
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
                        ist.prev_lock_layer = ist.lock_layer   # v3 R-C:原锁层暂存(闩回锁恢复)
                        ist.phase = 'weak'
                        ist.weak_comp = ist.locked_comp
                        ist.locked_comp = ''
                        ist.lock_layer = 0
                        ist.transition_pair = ()   # weak 不辖(W166,同 scope 契约)
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
        if ist.phase == 'locked' and not latch_active:
            # 撤销出口②:更高层级替代信号 + 可达性对照(层级高≠必换;
            # 门闩存续期抑制,v3 §3-3)
            for s in sigs:
                if s.comp_name == ist.locked_comp or s.layer >= ist.lock_layer:
                    continue
                new_comp = get_comp(s.comp_name)
                if new_comp and _core_reachable(new_comp, state, visible):
                    ist.prev_lock_layer = ist.lock_layer   # v3 R-C:原锁层暂存
                    ist.phase = 'weak'
                    ist.weak_comp = ist.locked_comp
                    ist.locked_comp = ''
                    ist.lock_layer = 0
                    ist.transition_pair = ()   # weak 不辖(W166,同 scope 契约)
                    ist.revoke_evidence = {}   # 出口②非证据组 A/B 通道(字段契约)
                    ist.last_event = f'revoke:higher:{s.comp_name}(L{s.layer})'
                    revoked = True
                    break   # 「直至新信号」——本轮撤,下轮新信号再锁

        # W948 转型臂:停滞评估与降级触发(设计件 w948_transform_design/
        # DESIGN.md §2.1;ADR-0509)。锁线的第三种降级转移:不走门拦截路径、
        # 不受回锁闩抑制(闩辖出口①②,停滞是进度侧证据通道);撤后当轮
        # 不重锁——与出口①/②同 revoked 语义(状态机一回合最多一次转移)。
        # 降级后的执行侧消费契约(对账锚=match g_20260831_082322 复盘候选#2
        # 「evolve 执行线 vs locked_comp 脱节」):本臂只保证 hoard 单一消费面
        # 即时换面(weak→骨架 / salvage→停线内投入);alloc/evolve 是否跟随
        # hoard 属分配器/演进域一致性断言,不归本臂辖(裁决=w954 REPORT §5)。
        if ist.phase == 'locked' and _stagnation_tick(
                state, ist, session, registry):
            revoked = True

    if ist.phase == 'locked' and state.plane == 1:
        # W166/ADR-0367:①锁局过渡对随资产重派生(同 p1_pair 语义——
        # 「变体按来牌选」[20],支持度只增,非 pivot;[23] 冻结语义辖
        # 终局线,不辖过渡副方向)。配方锁局(phase='unlocked')不进本支。
        pair = _derive_p1_pair(state, exclude=frozenset(ist.pair_evicted),
                               registry=registry,
                               drought=ist.supply_drought,
                               prev_pair=tuple(ist.transition_pair or ()))
        if pair != ist.transition_pair:
            ist.transition_pair = pair
            ist.last_event = ('lock_pair:' + '+'.join(pair)) \
                if pair else 'lock_pair:wait'

    if ist.phase in ('unlocked', 'weak') and not revoked:
        # H1 锁线环境判据(行为无条件化;三开关清偿——原
        # registry.line_env_gate_enabled 开关已删,四步清偿证据归
        # w628_migration_b2/STATUS):累积型线强环境不命中(False)的信号
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
        # P1 过渡配方锁(W145/ADR-0357):P1 的锁定产物=体系对;
        # ②③④信号不再锁终局 comp(终局 comp 锁定移至 P2+)——
        # 只保留①类资格通道(直通终局线资格,ADR-0338/0341 语义零改动)。
        # 方向产物=按手上资产派生的体系对(transition_combos 两两组合)。
        if state.plane == 1:
            sigs = [s for s in sigs
                    if _direct_line_qualified(state, s.comp_name)]
            pair = _derive_p1_pair(state, exclude=frozenset(ist.pair_evicted),
                                   registry=registry,
                                   drought=ist.supply_drought,
                                   prev_pair=tuple(ist.p1_pair or ()))
            if pair != ist.p1_pair:
                ist.p1_pair = pair
                ist.last_event = ('p1_pair:' + '+'.join(pair)) \
                    if pair else 'p1_pair:wait'
        elif ist.p1_pair:
            # 进 P2:配方锁退场,comp 锁定通道照旧(P2+ 锁定产物=终局 comp)
            ist.p1_pair = ()
            ist.last_event = 'p1_pair:exit_p1'
        best = _best_signal(sigs)
        # W948 伴生入口·乙:P2 空位弱占位(设计件 §2.1;默认关=零漂移)。
        # 无即时信号的 unlocked 帧按带入资产派生占位方向(只改 hoard 指向,
        # 不锁线、可被任何信号推翻,优先于⑤绯英兜底);有信号/弱意向/已撤
        # 帧退场('' =兜底语义回归)。
        _reg948p = registry or DEFAULT_REGISTRY
        if _reg948p.p2_entry_weak_target_enabled and state.plane >= 2:
            ist.weak_placeholder = (
                _p2_entry_weak_target(state, ist, visible)
                if ist.phase == 'unlocked' and best is None else '')
        if best is not None:
            # C4 存活轮数门(换线辖域见 _switch_gate_open;门放行才落锁,
            # 被拦=保持弱意向待后续信号,状态机单回合最多一次转移语义不变)
            if _switch_gate_open(ist, state, session, best, registry):
                _lock(ist, state, best)
            else:
                ist.last_event = (f'gate_hold:{ist.weak_comp}'
                                  f'->{best.comp_name}')
                # 门感知滞回闩(设计件 w665_p2p3_linegate/DESIGN.md §3-3 R-A,取代被再攻击推翻(见设计件 v3 修订块)
                # 的 N=2 计数回锁):本位面首次门拦截置闩 + 闩置位帧一次性
                # 回锁原线。为什么是闩不是计数:单调性——R<E(alt)+m 首次
                # 成立后位面内近似单调(§3-3),「后续帧不该再换线」与门
                # 判据一致;计数回锁缺单调性,周期-3 环是结构必然(设计件 v3 修订块引攻击证据)。
                # 回锁经 _switch_gate_open 同线豁免语义(状态机内单址);
                # 恢复 prev_lock_layer(FM-11 消解,回锁信号 layer=1 不许
                # 收窄出口②撤销面)。原线 E=inf 子情形:闩仍置位、状态停
                # weak——静态不可达原线的跨线骨架囤货/demoted/P3 兜底是
                # 合法终态(§3-4,行为锁钉住)。闩存续期出口①②抑制(上方
                # locked 分支),位面切换清零(入口段)。
                if session is not None and not (
                        session.v3_line_gate_latch
                        and session.v3_line_gate_latch_plane == state.plane):
                    session.v3_line_gate_latch = True
                    session.v3_line_gate_latch_plane = state.plane
                    wcomp = get_comp(ist.weak_comp) \
                        if ist.phase == 'weak' else None
                    if ist.phase == 'weak' and wcomp is not None \
                            and math.isfinite(e_rounds(wcomp, state, registry)):
                        relock_name = ist.weak_comp   # _lock 会清 weak_comp,先取
                        _lock(ist, state, IntentionSignal(
                            1, 'gate_relock', relock_name,
                            '门闩一次性回锁原线(锁线保生存)', 1.0))
                        ist.lock_layer = ist.prev_lock_layer or 1   # FM-11
                        ist.last_event = f'gate_relock:{relock_name}'
        elif ist.phase == 'weak':
            ist.last_event = ist.last_event or 'weak:hold'
        # 无信号:保持 unlocked——囤货方向落⑤兜底(hoard_target_set 处理)

    # W948 出口分支·丙:salvage 续命子模式在效位推导(设计件 §2.1;ADR-0509)。
    # salvage 是 weak 的子模式,**非 absorbing**——新信号仍可照常落新线救回;
    # P3 入口 demoted_endgame(absorbing)语义零改动,不进本段辖域。
    # deadline 条件 = 本位面剩余节点 ≤ salvage_deadline_nodes;window 条件 =
    # stagnate-weak 持续 > salvage_window_rounds 轮仍无新线落锁(计数含触发轮,
    # 证据被消费/离开 weak 即清)。开关关恒不写(字段缺省 False=零漂移)。
    _reg948s = registry or DEFAULT_REGISTRY
    if _reg948s.intention_stagnation_arm_enabled:
        if ist.phase == 'weak' \
                and ist.revoke_evidence.get('kind') == 'stagnate':
            ist.stagnate_weak_rounds += 1
            ist.stagnate_salvage = bool(
                plane_remaining_nodes(state, session)
                <= _reg948s.salvage_deadline_nodes
                or ist.stagnate_weak_rounds > _reg948s.salvage_window_rounds)
        else:
            ist.stagnate_salvage = False
            if ist.phase != 'weak':
                ist.stagnate_weak_rounds = 0

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
    - P1(W145/ADR-0357):非 comp 锁定局 → 配方方向——体系对成员集
      (p1_pair)/四体系引擎件全集(p1_transition,空窗);绯英⑤兜底
      不再辖 P1(零引擎覆盖,W143 实证 e2 成率 5%);
    - weak:只囤跨线骨架件(撤销后去向);salvage(W948,ADR-0509):
      stagnate-weak 的续命子模式,同骨架采购集但语义=停止线内投入;
    - P2+ unlocked 弱占位(W948·乙,ADR-0509):无信号空位的弱目标方向,
      优先于⑤兜底;
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
        if ist.stagnate_salvage:
            # W948 出口分支·丙(ADR-0509):salvage 续命采购集 = 跨线骨架,
            # 停止购入原线终局件(「停止给死线供血」);金流改道归危机臂按
            # 其自身判据开火,本分支不授权任何支出数值(DESIGN §2.6 划界)。
            # 当帧战力散件的散件采购归既有 opportunistic 通道,不经本接口。
            return HoardTarget(frozenset(CROSS_LINE_SKELETON), frozenset(),
                               'salvage')
        return HoardTarget(frozenset(CROSS_LINE_SKELETON), frozenset(), 'weak')
    # W948 伴生入口·乙(ADR-0509):P2+ 空位弱占位方向——优先于⑤兜底
    #(弱目标=有依据的初始假设,绯英=无信号默认落点;优先级 DESIGN §1.1)。
    # 开关关恒走原路径(weak_placeholder 恒空=零漂移)。
    if ist.weak_placeholder:
        pc = get_comp(ist.weak_placeholder)
        if pc is not None:
            chars, equips = _line_hoard(pc)
            return HoardTarget(frozenset(chars), frozenset(equips),
                               'p2_weak_target')
    comp = get_comp(FALLBACK_COMP_NAME)
    if comp is None:
        return HoardTarget(frozenset(CROSS_LINE_SKELETON), frozenset(), 'fallback')
    chars, equips = _line_hoard(comp)
    return HoardTarget(frozenset(chars), frozenset(equips), 'fallback')


def committed_authority(state: GameState | None,
                        session: StrategySession | None) -> bool:
    """committed(已定型/非双轨期)权威判定(方向层接管(git 历史);单一派生源)。

    - **权威序**(任一成立即 True):
      ① ``state.plane >= 2``——P2 起恒定型(语义边界同旧 update_target:
         定型边界=进位面 2,严于文档口径 P2-3);
      ② ``session.v3_intention.phase == 'locked'``——意向状态机已锁线;
      ③ ``ist.p1_pair`` 非空——P1 配方锁已立(W145/ADR-0357 产物形态)。
    - **缺供给帧 = 保守侧 False**(=双轨=攒息):ist 不可得/字段缺失时
      **禁止**缺省 True——True=已定型=激进侧,攒息门/双轨买门全开
      (供给点清单 D2:拔掉供给探针下必须落保守侧,变异锁钉住)。
    - 消费契约:全部消费点经本函数或 ``decision_v2.prep_brain
      .committed_from``(唯一读端,内部委托本函数)取值;
      state/session 侧双轨字段降级为兼容残留(读点归零,
      grep 守卫锁),写端退役随老栈(strategy 层)老栈退役(ADR-0466/0469)。

    与旧语义(CommitSignals.ready 合取)的分歧属方向层接管预期区,
    逐帧对拍产物归 w628_migration_b2 对照报告。
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
    """committed(已定型/非双轨期)唯一合法读端(R1,蓝图 §4.3;分包期
    0b 单元4 自 decision_v2.prep_brain 单符号下沉 kernel——cw_recipe
    决策中心消费它成 kernel→decision 断环边,§3.3-①d;体内仅委托
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


def locked_buy_scope(ist: IntentionState | None) -> frozenset[str] | None:
    """锁定帧买侧目标约束基准(W150/ADR-0359;W143 补充判读的通道半边)。

    opportunistic/bond_fallback 买通道「目标/非目标」判定输入 =
    ``p1_pair``(非空时)∪ ``locked_comp`` 采购集(``IntentionState.p1_pair``
    的约束基准契约,本函数是该契约的单一实现);两者皆空(空窗/弱意向/
    降格终局)→ None(无锁定帧,不约束——[31]① 空窗期四体系全集是方向,
    不存在「非目标件」)。

    - P1 配方锁定帧 = ``_pair_members(p1_pair)``(体系对两体系全成员,
      含其二体系——对成员集本身即两体系的并);
    - comp 锁定帧(P1①资格通道 / P2+)= ``_line_hoard(comp)`` 角色采购集;
      **①锁局(P1)∪ 过渡对成员集(W166/ADR-0367)**——二级囤货语义
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


def locked_faction_scope(ist: IntentionState | None) -> frozenset[str] | None:
    """锁定帧的体系(羁绊键)集(W155/ADR-0360;evolve 提案/部署围栏消费)。

    与 ``locked_buy_scope`` 同判据的**阵营口径**版本(W147 归因:off-lock
    evolve 提案的 target_factions 不含锁定 faction → 锁定目标件被
    execute_replacement 划进 old_line 整档解除——约束需要的是体系键不是
    件名):

    - P1 配方锁定帧 = ``p1_pair`` 体系键(希儿系展开=量子同频+贝洛伯格,
      与 ``_pair_members`` 同口径);
    - comp 锁定帧(P1①资格通道 / P2+)= ``locked_comp`` 主/副档键
      (``form_tiers`` ∪ ``sub_tiers``,与 ``_line_hoard`` 档位键同式);
      **①锁局(P1)∪ 过渡对体系键(W166/ADR-0367,与 ``locked_buy_scope``
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


# ===== 遥测序列化下沉(分包期 3:serialize_intention 自 telemetry/cw_telemetry.py
# 下沉本模块——sim 桶消费它而 sim 禁依 telemetry(分包目标矩阵),序列化的是本模块
# 的 IntentionState,随符号归位);cw_telemetry 反向 import 本节符号(telemetry→kernel 合法向)。

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
    """v3 意向状态(IntentionState)→ JSON-safe dict(迁移审计 w146(git 历史))。

    ADR-0336 后锁定真值在 ``session.v3_intention``,但 decisions 行
    只有恒空的 v1 遗留键(``v2_locked_line``/``v2_mode``)——实机判读
    「锁定时点/锁定目标」不可读,只能日志考古。本序列化把意向状态机
    全量落遥测(`w145_recipe_lock/` 锁定目标改过渡配方的实机验证依赖它)。

    - ``None`` = session 无意向状态机(default 栈/未初始化)——与
      「有意向未锁」(dict 且 ``phase='unlocked'``)显式区分,消费方
      不用猜;
    - dict 按字段全量序列化(dataclass fields 遍历,set→sorted list,
      嵌套 LineTrack 同构)——IntentionState 字段演进(如 `w145_recipe_lock/` 调整
      锁定语义)时自动跟上,不改本函数。

    **可变容器深拷贝(`w194_p2line/`/ADR-0378)**:dict/list 字段值经
    ``_to_jsonable`` 递归拷贝(嵌套 dataclass 走 asdict=深拷贝)——
    ``tracks: dict[str, LineTrack]`` 是**活引用**,旧版直接把引用
    落进账本行,session 后续轮原地改 LineTrack 会污染**已落账的
    早期行**(sim P2 段改写同局 P1 行的 tracks,`w193_p2sim/` 对比门曾排除
    该字段)。tuple/str 不可变,原样保留(类型不漂移)。

    只读不碰 ``cw_intention``(并行批在改);非 dataclass 输入退 None。
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
            # `w194_p2line/`/ADR-0378:可变容器深拷贝落账(活引用污染防线,
            # 见 docstring);tuple 不可变不辖(类型不漂移)
            out[f.name] = _to_jsonable(v)
        else:
            out[f.name] = v
    return out
