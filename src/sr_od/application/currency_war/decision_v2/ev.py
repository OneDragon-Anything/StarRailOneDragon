"""决策框架 v2 经济期望授权总账(W119/ADR-0347,经济循环总模型步②「切授权」)。

设计依据:.debug/temp/currency_war/cw_dev/deep_read/W113_经济循环总模型设计.md
§3.2(经济期望核算)/§8-6(DP 净新增接线)/§8-3(R 跨位面)/§8-5(扑满守卫)。

本模块是步② 的**授权核算单一源**:
- ``interest_cost``:买/刷新的息机会成本(C_interest,W113 §3.2(b));
- ``dp_posture``:DP 日程表(cw_horizon)姿态查询——v2 栈**首次真实消费**
  DP 解(W115 审计 ③:此前 v2 仅用几何常量,零 DP 消费;解级缓存=
  cw_horizon._solved 的台账指纹 memo,重复查询零成本);
- ``levelup_ev_authorized``:升级通道 EV 总账([12] 息引擎门的收编,
  A1/A2 镜像与 E6 latch 退场后的唯一裁决点);
- ``reward_node_is_battle``:扑满守卫(ADR-0348)——「经济过热」类环境下
  奖励节点带战力要求,按战斗节点处理。

**本模块不 import decision_v2 包内模块**(防环:candidates→discipline 链
在下,arbiter/remediation 在上)——[33] 人口位判据的目标件集由调用方
传入(candidates._target_names 单一源)。
"""
from __future__ import annotations

from dataclasses import dataclass

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_intention import (
    total_remaining_nodes,
)
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)


@dataclass
class RoundPosture:
    """轮内 DP 姿态缓存载体(decide_prep 每轮写 session.v3_dp_posture)。

    round_key=(plane, round_num)——轮键不匹配即失效(策略主循环
    每轮决策入口重算;sim 一轮多决策段共享同轮首查询)。
    """

    round_key: tuple[int, int]
    posture: object


def cross_plane_remaining_nodes(state: GameState) -> int:
    """息损公式的 R(剩余节点)——**显式含下位面**(W113 §8-3/ADR-0347)。

    口径写死:R = 全局剩余节点(``cw_intention.total_remaining_nodes``,
    当前节点 + 后续两位面全部节点)。理由:位面末「存 20 进 P2」的
    保本钱语义——本位面末攒下的金在下位面继续吃息,只有把下位面
    节点计入 R,跨档消费的机会成本才不丢(只算本位面会系统性低估
    位面末的息损)。
    """
    return max(0, total_remaining_nodes(state))


def interest_cost(gold: int, cost: int,
                  state: GameState,
                  recovery_rounds: float | None = None) -> float:
    """C_interest(W113 §3.2(b)):跨过的 10 金档数 × R(跨位面口径)。

    结算息按**花后金**计(结算序:先结算息再进收入,cw_horizon DP 的
    ``interest(g2)`` 同口径)——tiers_crossed = 花前档 − 花后档。

    **口径声明(W113 §3.2(b)⟲R2/F05,W126 落码)**:本式默认是**平面 R
    上界口径**——假设跨档后金停在低档直到位面末,每轮损满息差。
    依 P5⑤ 的口径注记:该口径在「守息纪律语义」下成立([3]「花完
    仍保 50」= 本公式在 50 档边界的自然输出);与之并存的另一口径是
    P6 回档账下界(破档后 1-2 轮回档,真实息损 1-3 金)——上界偏紧
    (拒绝偏多),按保守侧落(P5⑤:「R≥3 即拒」是上界口径的输出,
    **放行边界比它宽,不作为放行阈值承诺**)。

    **W131/ADR-0352 校准落地(sim 对拍后)**:买侧跨档消费改用
    ``recovery_rounds`` 折中口径——R_eff = min(R, recovery_rounds)
    (registry.interest_recovery_rounds,初值 3.0)。依据:①买是
    一次性金→板面资产兑换,破档后随每轮收入 1-2 轮回档(P6 回档账
    下界 1-3 金);「停在低档到位面末」的上界前提描述的是 FORM 段
    持续花钱的政策态,那个态由相位地板(form_floor/interest_floor)
    与层4 地板辖,不在本门重复计罚;②刷新(D)保持上界口径不动——
    D 的花费是同轮可反复的搜寻消耗,「刷穿 50 后继续刷」正是上界
    前件,P5⑤ 金 50/51 拒 D 的退化输出(W126 锁②)逐位保留。
    recovery_rounds 的网格精调(1-5)留后续 sim 批,本值为 P6 下界
    与平面上界的中点偏保守侧。
    """
    if gold <= 0 or cost <= 0:
        return 0
    tiers = gold // 10 - (gold - cost) // 10
    r = cross_plane_remaining_nodes(state)
    if recovery_rounds is not None:
        r = min(r, recovery_rounds)
    return float(max(0, tiers) * r)


def dp_posture(state: GameState, session: StrategySession):
    """DP 日程表姿态查询(W113 §8-6 净新增接线;ADR-0347)。

    真实调 ``cw_horizon`` 解(经生产路径 ``_solved``——持投资策略时
    台账注入,指纹 memo 进程内零成本;首解 ~0.3s 一局至多数个指纹)。
    返回 ``Posture``(save/level_up/refresh_budget);查询异常返回 None
    (调用方保守回退,对局不停——与 ``_horizon_node_goal`` 同款纪律:
    记 [cw!] 可 grep 证据)。
    """
    try:
        from sr_od.application.currency_war.cw_horizon import (
            NODES_PER_PLANE,
            _solved,
        )
        t = ((min(state.plane, 3) - 1) * NODES_PER_PLANE
             + min(max(1, state.round_num), NODES_PER_PLANE) - 1)
        return _solved(list(state.active_strategies or ())).posture(
            t, state.gold, state.level, state.hp, 0.0)
    except Exception as e:   # noqa: BLE001
        log.warning('[cw!][d2][ev] DP 姿态查询异常(p%sr%s gold%s lv%s '
                    'hp%s):%s → 调用方保守回退',
                    state.plane, state.round_num, state.gold,
                    state.level, state.hp, e)
        return None


def round_posture(state: GameState, session: StrategySession):
    """轮内缓存版 dp_posture(decide_prep 每轮算一次写 session;仲裁层
    各 gate 读同一姿态——一轮内多个 gate 消费同一 DP 解,既省查询也
    保证同轮口径一致)。轮键不匹配(裸 session/测试直调)时现算不缓存。"""
    cached = getattr(session, 'v3_dp_posture', None)
    if isinstance(cached, RoundPosture) and cached.round_key \
            == (state.plane, state.round_num):
        return cached.posture
    return dp_posture(state, session)


def _interest_at(gold: int, registry: DecisionV2Registry) -> int:
    return min(registry.interest_cap, max(0, gold) // 10)


def levelup_refresh_saving(state: GameState, session: StrategySession,
                           registry: DecisionV2Registry) -> float:
    """V_level 收益侧的省刷金项(W126/ADR-0349,P5 检验点②)。

    升级把目标核心的刷新概率抬档 → 找牌期望刷金下降,省下的刷金
    是升级的**收益侧金值**(P5 ④ 的「省 28g」口径):

        saving = 刷价 × max(0, E_refresh(L) − E_refresh(L+1))

    E 用批口径(``expected_refreshes_for_card``,star=2,owned=j)——
    **随目标张数 k 自动放大**(P5 边界 a:c=2@L4 k=1 时升级省钱 <
    升级成本 → 判负;k=3 才打平;单看「概率提高」不构成升级理由,
    收益侧必须过 k 放大后的总账)。ΔE≤0(峰值以上,P5 边界 b)→
    saving=0(峰值级/峰值以上停留最优,不设独立「峰值惩罚」判据,
    Z4/[7] 落地声明)。无锁定核心/核心已 2★/该费不可刷 → 0。

    消费点:levelup_ev_authorized ③ 静态 EV 账的 V 侧(金口径,
    与 C 的 R×档损同量级——W123 §3.4 的 V/C 量级不匹配在本批
    V_D/V_level 金口径化后解除)。
    """
    core = _vd_core_of(session)
    if not core:
        return 0.0
    copies = _vd_core_copies(state, core)
    if not copies or max(getattr(d, 'star', 1) or 1
                         for d in copies) >= 2:
        return 0.0
    from sr_od.application.currency_war.cw_chars import CHARACTERS as _CH
    ch = _CH.get(core)
    if ch is None or not ch.cost:
        return 0.0
    from sr_od.application.currency_war.cw_shop_odds import (
        expected_refreshes_for_card,
    )
    j = len(copies)
    e_now = expected_refreshes_for_card(
        state.level, ch.cost, target_star=2, owned=j)
    e_next = expected_refreshes_for_card(
        state.level + 1, ch.cost, target_star=2, owned=j)
    return max(0.0, e_now - e_next) * (state.shop_refresh_cost or 2)


def _vd_core_of(session: StrategySession) -> str:
    """V_D/V_level 共用的目标核心解析(scoring.vd_target_core 同源;
    ev 不 import decision_v2 包内模块——本地复刻判据,两处保持同值)。"""
    from sr_od.application.currency_war.cw_intention import (
        IntentionState,
        intention_core,
    )
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState) or ist.phase != 'locked' \
            or not ist.locked_comp:
        return ''
    from sr_od.application.currency_war.cw_comps import get_comp
    comp = get_comp(ist.locked_comp)
    if comp is None:
        return ''
    return intention_core(comp)


def _vd_core_copies(state: GameState, core: str) -> list:
    """核心的持有副本(deployed∪bench;V_D/V_level 同源口径)。"""
    return [d for d in list(state.deployed or [])
            + [b for b in (state.bench or []) if b is not None]
            if getattr(d, 'char_id', '') == core]


def levelup_ev_authorized(state: GameState, session: StrategySession,
                           registry: DecisionV2Registry,
                           working_gold: int, cost: int,
                           targets: set[str],
                           val: float = 0.0,
                           int_emb: float = 0.0) -> bool:
    """bool 包装:判据本体在 ``levelup_ev_basis``(返回放行臂名;''=拒)。

    ADR-0354 观测拆分(检查器判据重定义批,W131):授权依据=放行臂名,
    行为零改动。判据 docstring 与三路语义见 ``levelup_ev_basis``。
    """
    return levelup_ev_basis(state, session, registry, working_gold,
                            cost, targets, val=val, int_emb=int_emb) != ''


def levelup_ev_basis(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry,
                     working_gold: int, cost: int,
                     targets: set[str],
                     val: float = 0.0,
                     int_emb: float = 0.0) -> str:
    """升级通道 EV 总账裁决,返回**放行臂名**(授权依据单一源)。

    返回:'pop_slot'=① [33] 人口位 / 'dp'=② DP 花费授权 /
    'static_ev'=③ 静态 EV 平台账 / ''=拒。消费点:arbiter 升级门与
    remediation 补偿臂(放行时写入 ``LevelUp.auth_basis`` 观测字段→sim
    账本 LevelUp 行 auth 键→检查器 levelup_interest_engine_gate 判据
    重定义,W131/ADR-0354)、levelup_ev_authorized(bool 包装)。
    ——以下为原判据语义(W119/ADR-0347;W126/ADR-0349 修订):
    升级通道 EV 总账裁决([12] 息引擎门收编;ADR-0347;W126/ADR-0349 修订)。

    可负担性入口门(W126):working_gold < cost → 直接拒(任何授权臂
    都不含「花超本金」——W119 后 gold_floor 对 levelup 让位本函数
    单一裁决,可负担性在此收口)。

    三路放行(任一):
    ① **[33] 人口位**(一等例外,口述 [33]/[32](a);W121 G1 修正
       W113 §3.3 通道 2 的反向措辞):触发 = **cap−deployed==0(位子
       满)∧ bench 有等待上场的框架/目标成型件**——「有单位等上场」的
       字面义是位子满了才需要升;deployed<cap 时该件直接上场即可
       (部署动作,非升级动作;[32](b):cap−deployed≥1 时再升纯浪费)
       → 当轮战力兑现,通常 >C_interest,总账自然放行——[12] 拦的是
       「空位追级」;
       **W126 保险丝修订(34 帧误拒复核)**:人口位的花后下限从
       form_floor 放宽为**可负担性(after≥0)**——W123 实测 34 帧
       「位满+bench 目标件」升级组被 form_floor 拦截(多为
       remediation 多击整组,花后 0-19):人口位的价值=当轮战力
       兑现(具体件上场,非收益端估计),form_floor 防「估乐观」的
       语义对它不适用;抽干金流防护由可负担性+下轮收入自然承接。
    ② **DP 花费授权**(W113 §3.2(d) 单步落地):DP 姿态说升级 **且**
       花后不破息平台(working_gold−cost ≥ interest_floor)——DP 内生
       优化了金/级/存活的全程期望,说升且平台未破即放行;
    ③ **静态 EV 账**:V − C ≥ 0。V = 层3分剥离息分量(升级的等级/
       深度期权值)**+ 省刷金项**(levelup_refresh_saving,k 放大的
       金口径收益侧,W126/P5 检验点②);C = (即时档损 + 满息平台
       延迟损) × R(跨位面):
       - 即时档损 = interest(花前) − interest(花后)(结算按花后金);
       - 平台延迟损 = 花后 < interest_floor 时的满息缺口
         (interest_cap − interest(花后))——息引擎未立时追级把金
         拖在 50 以下,每轮少吃满息差(seed6 病症的账面化)。

    旧门语义对照(收编说明):旧「花后≥50」臂 ⊂ ③(花后≥50 时
    C=0,V≥0 恒放行——层3 levelup 分非负);旧「曾达满息」latch 臂
    随 E6 退场删除——曾满息不构成破平台的授权,破平台必须过账;
    旧 P1 lv<5 宽松门(gate=10)删除——早期升级由 ①/② 承接(人口位
    等着上场是早期升级的主因;DP 对低等级几乎恒说升)。
    """
    after = working_gold - cost
    if after < 0:
        return ''        # 可负担性入口门(W126;gold_floor 已让位本函数)
    # ① [33] 人口位(目标件集由调用方传,candidates._target_names 单一源;
    # W121 G1:cap 满 ∧ bench 有目标件——W113 §3.3 原文「deployed<cap 且
    # bench 有可上件」把判据写反(有余量=直接上场即可,升级纯浪费[32](b))
    from sr_od.application.currency_war.cw_state import bench_occupied
    if len(state.deployed or []) >= state.max_units():
        bench = state.bench or []
        if bench_occupied(bench) > 0 and any(
                b is not None and b.char_id in targets
                for b in bench):
            return 'pop_slot'
    # ② DP 花费授权(平台未破)
    posture = round_posture(state, session)
    if posture is not None and getattr(posture, 'level_up', False) \
            and after >= registry.interest_floor:
        return 'dp'
    # ③ 静态 EV 账(V−C≥0;V 含省刷金项,W126/P5 检验点②)
    v = val - int_emb + levelup_refresh_saving(state, session, registry)
    loss_now = _interest_at(working_gold, registry) \
        - _interest_at(after, registry)
    platform = (registry.interest_cap - _interest_at(after, registry)) \
        if after < registry.interest_floor else 0
    c = (max(0, loss_now) + platform) * cross_plane_remaining_nodes(state)
    return 'static_ev' if v - c >= 0 else ''


#: 扑满守卫环境名(ADR-0348;W113 §8-5/E1):「本局的全部奖励节点替换为
#: 次元/超级次元扑满」的投资环境——奖励节点带战力要求(扑满要打)。
#: 名单从 ``cw_invest_data.PLAZA_PORTALS`` 按效果文本派生(单一源,
#: 版本重跑自动跟上;断言锁见 test_cw_w119)。
def _overheated_env_names() -> frozenset[str]:
    from sr_od.application.currency_war.cw_invest_data import PLAZA_PORTALS
    return frozenset(
        p.name for p in PLAZA_PORTALS
        if '奖励节点替换' in (p.effect or ''))


REWARD_BATTLE_ENVS: frozenset[str] = _overheated_env_names()


def reward_node_is_battle(state: GameState) -> bool:
    """扑满守卫识别(ADR-0348 ↺ 修正 2026-08-26):当前节点为 reward
    且环境命中「经济过热」类(奖励节点替换为扑满)→ 扑满节点。

    **奖励型战斗节点:轻投入凑羁绊刷伤害拿奖励,禁深花保血**(口述
    [16]+math_proofs P8:s<0.277R≈2金,深花远超正期望界;boss/遭遇
    窗的下探授权对扑满全部不适用)。消费面:
    - scoring refresh 轮界豁免×P8 上限(piggy_refresh_round_cap);
    - 遥测:decisions 行/sim 账本 piggy_reward 字段(rounds 视图
      显 P=扑满;②b 观测与实机建档的数据面);
    - **不进** discipline._hard_node(连胜破息地板/报警保血刷新
      授权不辖——↺ 修正撤销的初版接线)。
    挂账(ADR-0348):效果表「奖励型战斗」突变项 / DP 台账指纹 /
    节点识别扑满模板(留实机)/ P8 V 折算与 2 金上限的消费点接线排
    ③(与 V_D 批口径同批)。
    """
    node = getattr(state, 'node_type', '') or ''
    env = getattr(state, 'active_env', '') or ''
    return node == 'reward' and env in REWARD_BATTLE_ENVS
