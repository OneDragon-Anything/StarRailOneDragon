"""P2 承接快照(W224 Phase 0,ADR-0399;设计件 08_p2_handoff §3.2/§4.2)。

**Phase 0 = 纯观测层,零行为变更**:``handoff_snapshot`` 是纯函数——
P1→P2 切换时点(plane>=2 本位面首轮 decide_prep 入口)对带入 P2 的
资产状态算一次七维向量,写 ``session.v3_handoff``(派生量模式,同
``v3_phase``:每局现算、不落跨轮存储、免疫 session 丢失);sim 侧同
函数经 ``session.v3_handoff`` 采样进 ``SimResult.p2_handoff``(与
``p2_gold_carried`` 同批披露);生产侧进 decisions 遥测行
(``DecisionTrace.handoff``)。

维度(设计 §3.2;装备维分期后置——生产 equips 落盘链 W222 已修,
但快照口径先不辖,后续批再上):

- 血量 ``hp``(出口 hp;run 28 型判别维);
- 板面形态 ``engines``(deployed 体系数,``cw_sim._engines_count``
  单一源)/``form_score``(与 phase.form_score 同口径;run 26 型主判别维);
- 星级深度 ``core2_count``(上场 star>=2 计数)/``star_sum``(上场星级和
  ——run 26 全 1★ = 此维归零实证)。**口径收窄声明**:设计稿原文是
  「核心/体系件 star>=2 计数」,但「核心/体系件」名集依赖意向 session
  态,离线回放(快照必须可喂历史 outcomes 重建态,设计 §4.4 案 b)
  不可复算 → 双口径漂移;故统一为**上场件全量 star 口径**(纯 state
  可算,生产/sim/离线回放三面同式);
- 等级/人口 ``level``/``deployed_n``;
- 经济 ``gold``(出口金;[28] 表征维);
- 锁线形态 ``locked``/``locked_comp``/``hoard_n``(散局承接口径不同)。

**档位(tier)派生**:分档判据与 P2 存活 outcome 挂钩标定(设计 §4.1
判据①:档位×P2 存活单调;切点由 outcome 单调性定,禁手拍)。切点常量
在下方,标定证据与单调性结论见 ADR-0399 与
``.debug/temp/currency_war/w224_handoff/``(21 run 真值语料离线回放)。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from dataclasses import replace as dataclasses_replace

from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)


@dataclass
class HandoffSnapshot:
    """P1→P2 承接快照(七维向量 + 派生档位;纯观测,零行为消费)。

    取值时机 = P2 本位面首轮 decide_prep 入口(进场继承完成后、
    任何 P2 决策/动作前);sim 案 b 臂 = 真值进场态起跑的首轮。
    """

    hp: int = 0                  # 出口血量(带进 P2 的 hp;继承块原样)
    engines: int = 0             # deployed 体系数(_engines_count 单一源)
    form_score: float = 0.0      # 板面形态连续量(phase.form_score 同口径)
    core2_count: int = 0         # 上场 star>=2 计数(口径见模块 docstring)
    star_sum: int = 0            # 上场星级和(全 1★ 板 = deployed_n 同值)
    level: int = 1               # 出口等级
    deployed_n: int = 0          # 上场件数(deployed 占用数,ADR-0392)
    gold: int = 0                # 出口金([28] 表征维)
    locked: bool = False         # 进 P2 时意向是否 locked
    locked_comp: str = ''        # 锁定线名(''=未锁)
    hoard_n: int = 0             # 囤货目标件数(session.v3_hoard.char_targets)

    def as_dict(self) -> dict:
        """遥测/sim 账本披露形态(含派生档位)。"""
        d = asdict(self)
        d['hp_tier'] = handoff_hp_tier(self.hp)
        d['board_tier'] = handoff_board_tier(self)
        d['tier'] = handoff_tier(self)
        return d


# ----- 档位切点(outcome 单调性标定;证据见 ADR-0399)-----
#: 切点标定 = 48 run 真值语料(21 run W193 语料 + 后续新增;离线回放
#: 脚本 ``.debug/temp/currency_war/w224_handoff/calibrate.py`` 产物
#: ``calibration.json``)按存活轮数单调性扫描候选切点族定档:
#: - hp 维 (20,50):档位 0/1/2 → P2 存活轮均值 0.17/2.25/4.5
#:   (n=30/12/6,严格单调;died_share 全 0 = 语料内 P2 死局多无结算行,
#:   该指标在语料内退化,数据边界见 ADR);
#: - 板面维 (engines≥1) ∧ (core2≥1):档位 0/1 → 1.18/1.36
#:   (n=34/14,单调);更严切点(eng≥2 或 c2≥2)单调破坏(回炉证据);
#: - 总档位 = min(hp,板面):0/1 → 0.98/3.00(n=42/6,单调)。
#:   **总档位实际两档**(板面维单切点封顶 1 → min 上限 1);hp 高端
#:   区分度归 hp 维独享(hp_tier),总档位只作承接不足判定。
HANDOFF_HP_CUTS: tuple[int, ...] = (20, 50)
HANDOFF_BOARD_ENGINE_CUTS: tuple[int, ...] = (1,)
HANDOFF_BOARD_CORE2_CUTS: tuple[int, ...] = (1,)


def handoff_hp_tier(hp: int) -> int:
    """hp 维档位(0=最差):切点=HANDOFF_HP_CUTS(标定证据见 ADR-0399)。

    tier = 超过的切点数(hp<=cut0 → 0;cut0<hp<=cut1 → 1;…)。
    """
    return sum(1 for c in HANDOFF_HP_CUTS if hp > c)


def handoff_board_tier(s: HandoffSnapshot) -> int:
    """板面质量维档位(0=最差):engines 与 core2 双键取小
    (run 26 型 = engines 达标但星级维归零 → 板面档被 core2 压低)。"""
    t_eng = sum(1 for c in HANDOFF_BOARD_ENGINE_CUTS if s.engines >= c)
    t_c2 = sum(1 for c in HANDOFF_BOARD_CORE2_CUTS if s.core2_count >= c)
    return min(t_eng, t_c2)


def handoff_tier(s: HandoffSnapshot) -> int:
    """总档位(0=承接最差)= hp 维与板面维取小(短板决定承接质量;
    run 28=hp 维短板 / run 26=板面维短板,两局各自命中主罚维)。"""
    return min(handoff_hp_tier(s.hp), handoff_board_tier(s))


def handoff_snapshot(state: GameState,
                     session: StrategySession | None = None,
                     registry: DecisionV2Registry | None = None,
                     ) -> HandoffSnapshot:
    """承接快照纯函数(state 必需;session/registry 可缺省=离线回放形态)。

    纯函数契约:不写 state/session、不耗 rng、可在历史 outcomes 重建态
    上离线复算(设计 §4.4)——因此维度全部取自 state 或可缺省的
    session 只读字段。挂载点(生产/sim 共用)= decision_v2.strategy
    decide_prep 入口的位面首帧块(P2 首轮算一次写 session.v3_handoff)。
    **时点语义**:进场继承完成后**首轮 decide_prep 入口**——hp/board/
    deployed 域同「P1 出口」;gold 已含 P2 r1 轮收入(生产/sim 同构,
    亦与离线标定语料同口径——标定读的 decisions 行即此时点)。
    """
    from sr_od.application.currency_war.cw_sim import (
        _board_factions_of,
        _engines_count,
    )
    from sr_od.application.currency_war.decision_v2.phase import form_score

    deployed = [d for d in (state.deployed or []) if d is not None]
    fac = _board_factions_of(deployed)
    dep_names = frozenset(
        getattr(d, 'char_id', '') or '' for d in deployed)
    stars = [int(getattr(d, 'star', 1) or 1) for d in deployed]
    reg = registry if registry is not None else _default_registry()
    ist = getattr(session, 'v3_intention', None) if session else None
    locked = (getattr(ist, 'phase', '') == 'locked'
              and bool(getattr(ist, 'locked_comp', '')))
    hoard = getattr(session, 'v3_hoard', None) if session else None
    return HandoffSnapshot(
        hp=int(state.hp or 0),
        engines=_engines_count(fac, dep_names),
        form_score=round(form_score(state, reg), 4),
        core2_count=sum(1 for x in stars if x >= 2),
        star_sum=sum(stars),
        level=int(state.level or 1),
        deployed_n=len(deployed),
        gold=int(state.gold or 0),
        locked=locked,
        locked_comp=(getattr(ist, 'locked_comp', '') or '') if locked else '',
        hoard_n=len(getattr(hoard, 'char_targets', ()) or ())
        if hoard is not None else 0,
    )


def handoff_gate_gap(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry | None = None) -> int:
    """P1 末窗承接门缺口(W227/ADR-0400;设计件 08 §4.2 Phase 1 挂载
    点 a/b 的共用判据,单一源)。

    返回承接缺口单位数:0=不辖(开关关/非 P1 末窗/投影档位已达标);
    >0=投影承接档位距 ``registry.handoff_gate_tier_target`` 的差。
    辖域 = plane==1 且 round_num>=registry.handoff_gate_min_round
    (末窗 r8-r9 boss 窗,设计件 §4.2)——**只辖末窗**是「P1 非末窗
    零漂移门」的结构前提(设计件 §4.1 判据 3),调用方无需重复判窗。

    投影档位 = ``handoff_snapshot`` 在**当前轮决策入口**现算(纯函数,
    hp/board 取现值 = 「若末窗后带当前资产进 P2」的近端投影;末窗内
    距 P2 出口 ≤2 轮,板面/血量漂移有限,run 28/31 型低血局的主罚维
    hp 在此投影下已可判)。**hp 维 boss 投影(W238/ADR-0403,设计件
    09 §3.1)**:``registry.handoff_boss_project`` 开时,末窗快照 hp 维
    由「当前 hp(boss 前)」换「boss 后投影 hp」——修标定口径错位
    (``HANDOFF_HP_CUTS`` 的标定语料是 P2 进场真值 hp=**boss 结算后**
    (ADR-0399),末窗喂 boss 前 hp = hp 维系统性高估一档);投影公式
    与常数表语义见 ``registry`` W238 块。快照本身不动(Phase 0 语义
    = P2 进场真值,两层口径各归各位)。消费面:

    - ``filters.formed_stop_active``(挂载点 a:成型停手承接维——
      缺口>0 不停手继续投资);
    - ``arbiter.interest_rule`` 买侧 EV 账(挂载点 b:承接缺口项,
      末窗破息投资授权放宽)。

    观测:``session.v3_handoff_gap``(sim 账本轮行 handoff_gap);投影
    hp 披露 ``session.v3_handoff_hp_proj``(投影开时写,sim 账本轮行
    handoff_hp_proj;关时不写=零漂移)。
    """
    reg = registry if registry is not None else _default_registry()
    if not reg.handoff_gate_enabled:
        return 0
    if state.plane != 1 or state.round_num < reg.handoff_gate_min_round:
        return 0
    snap = handoff_snapshot(state, session, reg)
    if reg.handoff_boss_project:
        snap = dataclasses_replace(
            snap, hp=boss_projected_hp(state, snap.hp, reg))
        if session is not None:
            session.v3_handoff_hp_proj = snap.hp
    return max(0, reg.handoff_gate_tier_target - handoff_tier(snap))


def star_directed_gap(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry | None = None) -> int:
    """末窗星级定向授权缺口(W242/ADR-0405,W232 挂账 C 项;设计件 08
    §4.2 Phase 1b 星级投资方向)。

    返回值语义 = ``handoff_gate_gap``(单一源复用,不建第二套缺口公式)
    在 ``registry.handoff_star_directed`` 开时的值;flag 关/gate 关/
    非末窗/投影达标 → 0(=零行为,三 flag 正交的结构前提:本 flag 只在
    门开路径内被消费,单独开=零行为,与 ``handoff_boss_project`` 同式)。

    消费面(C 项定向授权的两半,ADR-0405 授权点论证):

    - ``candidates`` 生成层:gap>0 时放行同名副本候选生成(r410 守卫 +
      方向门,= W232 A/B 豁免的 gap 条件化分支——不是授权点:不豁免
      评分/约束,copies_cap/r408/bench 容量照常辖);
    - ``arbiter`` 非正分门:gap>0 时放行 'copy' 标签买候选(W231 主因:
      副本评分零维被结构性拒,到不了 EV 账);**授权值本身零新增**——
      EV 账由 ``interest_rule`` 的 W227 缺口项
      (``handoff_ev_gap_bonus``×gap)独担,防双计。
    """
    reg = registry if registry is not None else _default_registry()
    if not reg.handoff_star_directed:
        return 0
    return handoff_gate_gap(state, session, reg)


def directed_refresh_budget(state: GameState, session: StrategySession,
                            registry: DecisionV2Registry | None = None,
                            ) -> int:
    """定向 D 牌授权窗预算(M-A,W252/ADR-0409;W249 诊断修法)。

    病灶(W249 §H3):**策略从不支付搜索成本**——追名 peak 卡死在 2 张
    时(场上已有 2 张同名目标件,距 3合1 只差最后一张),策略的刷新
    预算分配为零(P1 全程均值 0.44 次/局),双核心(core2≥2)全链不可达。
    本函数返回当前轮可用的**有界刷新预算**(次数):0=不授权。

    辖域判据(与 C 项 ``star_directed_gap`` 同族同窗):
    - ``registry.handoff_refresh_directed`` 开(默认关);
    - ``handoff_gate_gap > 0`` 承接缺口成立(gap 单一源复用;gate 关时
      恒 0——本 flag 与 gate/boss 投影三 flag 正交,单独开=零行为,
      W242 C 项先例);
    - 存在「追名 peak≥2」的目标件:**意向目标名集**(``_core_names``,
      candidates 层单一源)中某名的全场在手副本(star 加权,
      ``star_weighted_copies``)恰 ≥2 且 <3 ——即该名距 2★ 只差最后
      一张,补跳的期望刷新代价(~6-17 次,E 随费用档)在金余量允许
      的尾部窗口内才开始有意义;peak<2(收集线远未起步,自然进店
      即可见即购)或已 3 份(copies_cap 照辖)不授权。

    预算额 = min(registry.directed_refresh_per_round 每轮上限,
                 registry.directed_refresh_game_cap − 本局已消耗)
    (两常量 registry 单一源;初值来自 W249 白盒估算:每合资格轮 ≤2 次、
    每局 ≤6 次 ≈ 覆盖一颗 2★ 的第二跳)。**只产出预算数,不产生任何
    动作**;消费方是 arbiter 刷新收尾裁决(有界放行),实际金消耗 =
    放行次数 × 刷价。

    防双计(W232 A/B/W242 C 各辖买牌维,M-A 辖刷新维,互斥边界):买牌
    授权路径(interest_rule 缺口项/copy 标签放行)不动;本函数只在
    arbiter 刷新分支被消费——一个 RefreshShop 候选要么走 V_D 正分/
    gold_floor 地板(既有路径,预算开/关逐位一致),要么凭本预算在有界
    额度内放行,同一动作不存在两条授权来源叠加。
    """
    reg = registry if registry is not None else _default_registry()
    if not reg.handoff_refresh_directed:
        return 0
    from sr_od.application.currency_war.decision_v2.candidates import (
        _core_names,
    )
    # 追名 peak≥2 判据:目标集内某名 star 加权副本 ∈ [2,3)(差最后一张)
    for name in _core_names(session):
        c = _weighted_copies_of(name, state)
        if 2 <= c < 3:
            break
    else:
        return 0
    gap = handoff_gate_gap(state, session, reg)
    if gap <= 0:
        return 0
    used = getattr(session, 'v3_dir_refresh_used', 0)
    return max(0, min(reg.directed_refresh_per_round,
                      reg.directed_refresh_game_cap - used))


def _weighted_copies_of(name: str, state: GameState) -> int:
    """单名 star 加权副本数(deployed∪bench;
    ``cw_sim.star_weighted_copies`` 单一源转发,防第二公式)。"""
    from sr_od.application.currency_war.cw_sim import (
        star_weighted_copies,
    )
    return star_weighted_copies(name, state)


def boss_projected_hp(state: GameState, hp_now: int,
                      registry: DecisionV2Registry) -> int:
    """boss 后投影 hp(W238/ADR-0403,设计件 09 §3.1;纯函数;
    W240/ADR-0404 键改净星深)。

    hp_proj = hp + 2(r8 奖励胜,唯一正项) − E[boss 伤害|净星深档];
    r9(直面 boss)无 +2。档键 = 净星深桶(min(净星深//3,5)*3,净星深
    =上场件 Σ(star−1),``cw_sim.deployed_star_depth`` 单一源,与 Δ池
    boss 桶采样键同口径,不建第二套分桶;W240 起替旧 Σboard 桶——
    Σboard 下 3合1 升星使键落浅桶而浅桶期望伤害更大,与 [27] 机制
    相反);缺桶走 ``handoff_boss_e_damage_default``(全池未删失均值)。
    常数表标定口径(删失剔除)与已知边界(样本存活偏差)见 registry
    W238/W240 块与 ADR-0403/0404。钳制 [0, 100](与 sim hp 结算钳制
    同界,HP_UPPER_BOUND 语义)。
    """
    from sr_od.application.currency_war.cw_sim import (
        _DEPTH_BUCKET_W,
        deployed_star_depth,
    )
    depth = deployed_star_depth(state)
    bucket = min(depth // _DEPTH_BUCKET_W, 5) * _DEPTH_BUCKET_W
    dmg = registry.handoff_boss_e_damage.get(
        bucket, registry.handoff_boss_e_damage_default)
    bonus = (registry.handoff_boss_reward_bonus
             if state.round_num == registry.handoff_gate_min_round else 0)
    return max(0, min(100, int(round(hp_now + bonus - dmg))))


def _default_registry() -> DecisionV2Registry:
    """延迟 import(与 phase.py 同式,防 import 环)。"""
    from sr_od.application.currency_war.decision_v2.registry import (
        DEFAULT_REGISTRY,
    )
    return DEFAULT_REGISTRY
