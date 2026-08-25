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
                  state: GameState) -> int:
    """C_interest(W113 §3.2(b)):跨过的 10 金档数 × R(跨位面口径)。

    结算息按**花后金**计(结算序:先结算息再进收入,cw_horizon DP 的
    ``interest(g2)`` 同口径)——tiers_crossed = 花前档 − 花后档。
    """
    if gold <= 0 or cost <= 0:
        return 0
    tiers = gold // 10 - (gold - cost) // 10
    return max(0, tiers) * cross_plane_remaining_nodes(state)


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


def levelup_ev_authorized(state: GameState, session: StrategySession,
                          registry: DecisionV2Registry,
                          working_gold: int, cost: int,
                          targets: set[str],
                          val: float = 0.0,
                          int_emb: float = 0.0) -> bool:
    """升级通道 EV 总账裁决([12] 息引擎门收编;ADR-0347)。

    三路放行(任一):
    ① **[33] 人口位**(一等例外,口述 [33]/[32](a);W121 G1 修正
       W113 §3.3 通道 2 的反向措辞):触发 = **cap−deployed==0(位子
       满)∧ bench 有等待上场的框架/目标成型件**——「有单位等上场」的
       字面义是位子满了才需要升;deployed<cap 时该件直接上场即可
       (部署动作,非升级动作;[32](b):cap−deployed≥1 时再升纯浪费)
       → 当轮战力兑现,通常 >C_interest,总账自然放行——[12] 拦的是
       「空位追级」;
    ② **DP 花费授权**(W113 §3.2(d) 单步落地):DP 姿态说升级 **且**
       花后不破息平台(working_gold−cost ≥ interest_floor)——DP 内生
       优化了金/级/存活的全程期望,说升且平台未破即放行;
    ③ **静态 EV 账**:V − C ≥ 0。V = 层3分剥离息分量(升级的等级/
       深度期权值);C = (即时档损 + 满息平台延迟损) × R(跨位面):
       - 即时档损 = interest(花前) − interest(花后)(结算按花后金);
       - 平台延迟损 = 花后 < interest_floor 时的满息缺口
         (interest_cap − interest(花后))——息引擎未立时追级把金
         拖在 50 以下,每轮少吃满息差(seed6 病症的账面化)。

    旧门语义对照(收编说明):旧「花后≥50」臂 ⊂ ③(花后≥50 时
    C=0,V≥0 恒放行——层3 levelup 分非负);旧「曾达满息」latch 臂
    随 E6 退场删除——曾满息不构成破平台的授权,破平台必须过账;
    旧 P1 lv<5 宽松门(gate=10)删除——早期升级由 ①/② 承接(人口位
    等着上场是早期升级的主因;DP 对低等级几乎恒说升)。
    ① 的保险丝:花后仍须 ≥ form_floor([33] 人口位是阵容服务,不是
    抽干金流的许可——EV 授权的花费同样止于本金下限)。
    """
    after = working_gold - cost
    # ① [33] 人口位(目标件集由调用方传,candidates._target_names 单一源;
    # W121 G1:cap 满 ∧ bench 有目标件——W113 §3.3 原文「deployed<cap 且
    # bench 有可上件」把判据写反(有余量=直接上场即可,升级纯浪费[32](b))
    from sr_od.application.currency_war.cw_state import bench_occupied
    if after >= registry.form_floor \
            and len(state.deployed or []) >= state.max_units():
        bench = state.bench or []
        if bench_occupied(bench) > 0 and any(
                b is not None and b.char_id in targets
                for b in bench):
            return True
    # ② DP 花费授权(平台未破)
    posture = round_posture(state, session)
    if posture is not None and getattr(posture, 'level_up', False) \
            and after >= registry.interest_floor:
        return True
    # ③ 静态 EV 账(V−C≥0)
    v = val - int_emb
    loss_now = _interest_at(working_gold, registry) \
        - _interest_at(after, registry)
    platform = (registry.interest_cap - _interest_at(after, registry)) \
        if after < registry.interest_floor else 0
    c = (max(0, loss_now) + platform) * cross_plane_remaining_nodes(state)
    return v - c >= 0


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
    """扑满守卫(ADR-0348;口述定谒 2026-08-26=低危战斗):当前节点为
    reward 且环境命中「经济过热」类(奖励节点替换为扑满)→ 扑满节点。

    扑满关不掉血(全局机制 0hp 保底 1hp,机制真值),真损失=打不过
    没奖励——处置=确保伤害阵容拿奖励,**非深花保血**:
    - 战斗向刷新理由开放(scoring refresh 轮界门豁免,金保底保留);
    - 地板不降(discipline._hard_node 不辖)。
    挂账项(ADR-0348):投资效果表「奖励节点变战斗(低危)」机制突变项 /
    DP 台账指纹 / 节点识别扑满模板(cw_node_reader 自陈未建,留实机)。
    """
    node = getattr(state, 'node_type', '') or ''
    env = getattr(state, 'active_env', '') or ''
    return node == 'reward' and env in REWARD_BATTLE_ENVS
