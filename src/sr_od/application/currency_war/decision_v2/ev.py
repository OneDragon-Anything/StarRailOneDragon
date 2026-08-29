"""决策框架 v2 经济期望授权总账(迁移审计 w119(git 历史)/ADR-0347,经济循环总模型步②「切授权」)。

设计依据:.debug/temp/currency_war/cw_dev/deep_read/W113_经济循环总模型设计.md
§3.2(经济期望核算)/§8-6(DP 净新增接线)/§8-3(R 跨位面)/§8-5(扑满守卫)。

本模块是步② 的**授权核算单一源**:
- ``interest_cost``:买/刷新的息机会成本(C_interest,迁移审计 w113(git 历史) §3.2(b));
- ``round_posture``/``build_round_posture``:轮姿态生产者(迁移迁移批 3(ADR-0465)(ADR-0465) 预算
  收权后 = 确定性预算核的载体装配;原 DP 姿态查询已随 DP 退役);
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

from sr_od.application.currency_war.cw_intention import (
    total_remaining_nodes,
)
from sr_od.application.currency_war.cw_state import (
    GameState,
    deployed_occupied,  # ADR-0392 helper 导入
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.posture import Posture
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)


@dataclass
class RoundPosture:
    """轮姿态轮缓存载体(decide_prep 每轮写 session.v3_dp_posture)。

    round_key=(plane, round_num)——轮键不匹配即失效(策略主循环
    每轮决策入口重算;sim 一轮多决策段共享同轮首查询)。
    posture 字段现 = 确定性预算核产出(预算收权批(ADR-0465);字段名 dp_posture
    为历史沿用的 session 槽位名)。
    """

    round_key: tuple[int, int]
    posture: object


def cross_plane_remaining_nodes(state: GameState) -> int:
    """息损公式的 R(剩余节点)——**显式含下位面**(迁移审计 w113(git 历史) §8-3/ADR-0347)。

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
    """C_interest(迁移审计 w113(git 历史) §3.2(b)):跨过的 10 金档数 × R(跨位面口径)。

    结算息按**花后金**计(结算序:先结算息再进收入,与息闭式
    ``cw_plane_table.interest`` 同口径)——tiers_crossed = 花前档 − 花后档。

    **口径声明(迁移审计 w113(git 历史) §3.2(b)⟲R2/F05,`w126_b_arm/` 落码)**:本式默认是**平面 R
    上界口径**——假设跨档后金停在低档直到位面末,每轮损满息差。
    依 P5⑤ 的口径注记:该口径在「守息纪律语义」下成立([3]「花完
    仍保 50」= 本公式在 50 档边界的自然输出);与之并存的另一口径是
    P6 回档账下界(破档后 1-2 轮回档,真实息损 1-3 金)——上界偏紧
    (拒绝偏多),按保守侧落(P5⑤:「R≥3 即拒」是上界口径的输出,
    **放行边界比它宽,不作为放行阈值承诺**)。

    **`w131_a2n_arm/`/ADR-0352 校准落地(sim 对拍后)**:买侧跨档消费改用
    ``recovery_rounds`` 折中口径——R_eff = min(R, recovery_rounds)
    (registry.interest_recovery_rounds,初值 3.0)。依据:①买是
    一次性金→板面资产兑换,破档后随每轮收入 1-2 轮回档(P6 回档账
    下界 1-3 金);「停在低档到位面末」的上界前提描述的是 FORM 段
    持续花钱的政策态,那个态由相位地板(form_floor/interest_floor)
    与层4 地板辖,不在本门重复计罚;②刷新(D)保持上界口径不动——
    D 的花费是同轮可反复的搜寻消耗,「刷穿 50 后继续刷」正是上界
    前件,P5⑤ 金 50/51 拒 D 的退化输出(`w126_b_arm/` 锁②)逐位保留。
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


#: 非战斗节点 token 集(battles_left_plane 的排除口径;英文=Hu 槽序表词表,
#: 中文=结算屏归一词表,双词表容错)。巨星(megastar)按战斗计(有伤害
#: 要求的节点,[27] 掉血辖)。
NON_BATTLE_NODE_TOKENS: frozenset[str] = frozenset({
    'reward', 'supply', '奖励', '补给',
})


def battles_left_plane(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> float:
    """本位面剩余战斗节点推导(P1/P2 同法,ADR-0425;`w154_p2d/`/ADR-0361 立
    P2 口径,math_proofs P15 立确定性命题)。

    推导源=``session.plane_node_table``(开局帧槽序表:**每位面一张**,
    prep_director 位面首帧重写、位面内恒定,ADR-0368;P1=9 槽/P2=7 槽,
    ADR-0366)——从当前轮起数非战斗 token(reward/supply/奖励/补给)
    之外的剩余槽位数(未知 token 按战斗计:每个节点默认是战斗,
    reward/supply 才是例外;表只辖本位面槽,越界槽不数)。

    表缺失/越界(裸 session/sim 无表局/开局首帧前)→ 退
    ``registry.battles_left_est``(骨架缺省,保守侧)。
    """
    from sr_od.application.currency_war.cw_plane_table import NODES_PER_PLANE
    table = getattr(session, 'plane_node_table', None) or []
    r = state.round_num
    if table:
        # 表只辖本位面(表长=本位面轮数,ADR-0366);超长脏表以
        # NODES_PER_PLANE 为最大先验封顶(`w154_p2d/` 越界槽不数守卫保留)
        remaining = [str(t) for t in table[max(0, r - 1):min(len(table), NODES_PER_PLANE)]]
        if remaining:
            return float(sum(
                1 for t in remaining if t not in NON_BATTLE_NODE_TOKENS))
    return float(registry.battles_left_est)


#: `w154_p2d/`/ADR-0361 的 P2 命名消费点别名(P1/P2 同法后保留旧名,ADR-0425)
battles_left_p2 = battles_left_plane


def build_round_posture(state: GameState, session: StrategySession,
                        registry: DecisionV2Registry | None = None) -> Posture:
    """轮姿态生产者(预算收权批(ADR-0465);确定性预算核单一址)。

    level_up = economy_cycle.schedule_upgrade(查表核,含预告态);
    refresh_budget = economy_cycle.refresh_ev_budget(预算式,合法 0 帧
    契约见该函数)。三路消费方(排程/R*/arbiter 授权/scoring 窗)共调
    同两接缝(R4 单一址),本函数只负责把两个标量装进轮姿态载体 +
    打遥测标签(词汇表 v2 判前锁,见 decision_v2.posture.Posture)。
    ``registry`` 显式透传(P6 注入面单源:与 prep_brain._budget 同一
    实例,禁静默落缺省表)。原 ``dp_posture``(原 DP 求解面姿态
    查询)随 DP 退役删除;「查询不可达 → None → 各消费点保守回退」的
    级联面随之消灭(`w623_batch3_pre-mortem/` D0:确定性核在任意帧恒有定义,无 None 形状)。
    """
    from sr_od.application.currency_war.decision_v2.economy_cycle import (
        refresh_ev_budget,
        schedule_upgrade,
    )
    level_up = schedule_upgrade(state, session, registry)
    rolls = refresh_ev_budget(state, session, registry)
    if level_up:
        tag = '升级' + (f'+D{rolls}' if rolls else '')
    elif rolls:
        tag = f'+D{rolls}'
    else:
        tag = '存息'
    return Posture(save=(not level_up and rolls == 0), level_up=level_up,
                   refresh_budget=rolls, v=0.0, tag=tag)


def round_posture(state: GameState, session: StrategySession) -> Posture:
    """轮内缓存版姿态(decide_prep 每轮算一次写 session;仲裁层各 gate
    读同一姿态——一轮内多个 gate 消费同一次预算核算,既省重算也保证
    同轮口径一致)。确定性核恒有定义,本函数不再返回 None。

    辖域声明(`w635_batch3_attack/` F6c):缓存命中 = decide_prep 写入的 **release 包装后**
    姿态;缓存 miss(测试/回放直调)现算返回**未包装**的裸预算核姿态
    ——release 包装(latch/预算合并)唯一所有者 = 生产主链每轮入口的
    ``posture_release.evaluate_release``,本函数不做二级包装(防第二
    latch 判定源)。消费方若在主链之外需要包装语义,显式调 evaluate_release。
    """
    cached = getattr(session, 'v3_dp_posture', None)
    if isinstance(cached, RoundPosture) and cached.round_key \
            == (state.plane, state.round_num):
        return cached.posture
    return build_round_posture(state, session)


def _interest_at(gold: int, registry: DecisionV2Registry) -> int:
    return min(registry.interest_cap, max(0, gold) // 10)


def levelup_refresh_saving(state: GameState, session: StrategySession,
                           registry: DecisionV2Registry) -> float:
    """V_level 收益侧的省刷金项(`w126_b_arm/`/ADR-0349,P5 检验点②)。

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
    与 C 的 R×档损同量级——`w123_b_arm/` §3.4 的 V/C 量级不匹配在本批
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

    ADR-0354 观测拆分(检查器判据重定义批,`w131_a2n_arm/`):授权依据=放行臂名,
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
    重定义,`w131_a2n_arm/`/ADR-0354)、levelup_ev_authorized(bool 包装)。
    ——以下为原判据语义(迁移审计 w119(git 历史)/ADR-0347;`w126_b_arm/`/ADR-0349 修订):
    升级通道 EV 总账裁决([12] 息引擎门收编;ADR-0347;`w126_b_arm/`/ADR-0349 修订)。

    可负担性入口门(`w126_b_arm/`):working_gold < cost → 直接拒(任何授权臂
    都不含「花超本金」——迁移审计 w119(git 历史) 后 gold_floor 对 levelup 让位本函数
    单一裁决,可负担性在此收口)。

    三路放行(任一):
    ① **[33] 人口位**(一等例外,口述 [33]/[32](a);迁移审计 w121(git 历史) G1 修正
       迁移审计 w113(git 历史) §3.3 通道 2 的反向措辞):触发 = **cap−deployed==0(位子
       满)∧ bench 有等待上场的框架/目标成型件**——「有单位等上场」的
       字面义是位子满了才需要升;deployed<cap 时该件直接上场即可
       (部署动作,非升级动作;[32](b):cap−deployed≥1 时再升纯浪费)
       → 当轮战力兑现,通常 >C_interest,总账自然放行——[12] 拦的是
       「空位追级」;
       **`w126_b_arm/` 保险丝修订(34 帧误拒复核)**:人口位的花后下限从
       form_floor 放宽为**可负担性(after≥0)**——`w123_b_arm/` 实测 34 帧
       「位满+bench 目标件」升级组被 form_floor 拦截(多为
       remediation 多击整组,花后 0-19):人口位的价值=当轮战力
       兑现(具体件上场,非收益端估计),form_floor 防「估乐观」的
       语义对它不适用;抽干金流防护由可负担性+下轮收入自然承接。
    ② **DP 花费授权**(迁移审计 w113(git 历史) §3.2(d) 单步落地):DP 姿态说升级 **且**
       花后不破息平台(working_gold−cost ≥ interest_floor)——DP 内生
       优化了金/级/存活的全程期望,说升且平台未破即放行;
    ③ **静态 EV 账**:V − C ≥ 0。V = 层3分剥离息分量(升级的等级/
       深度期权值)**+ 省刷金项**(levelup_refresh_saving,k 放大的
       金口径收益侧,`w126_b_arm/`/P5 检验点②);C = (即时档损 + 满息平台
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
        return ''        # 可负担性入口门(`w126_b_arm/`;gold_floor 已让位本函数)
    # 淘金客姿态:升级通道退役(`w621_sim_explore/` 实证 LevelUp 退役是刷驱姿态主驱动;
    # 谓词单一址 = cw_investments.refresh_invest_active,与排程核同址)。
    # 全臂关闭(含①人口位),与 `w621_sim_explore/` sim 注入臂「LevelUp 全抑制」同口径;
    # 等级回落为预期方向(w630 协议出口 9 预期带 7.0-8.6)。
    from sr_od.application.currency_war.cw_investments import (
        refresh_invest_active,
    )
    if refresh_invest_active(state):
        return ''
    # ① [33] 人口位(目标件集由调用方传,candidates._target_names 单一源;
    # 迁移审计 w121(git 历史) G1:cap 满 ∧ bench 有目标件——迁移审计 w113(git 历史) §3.3 原文「deployed<cap 且
    # bench 有可上件」把判据写反(有余量=直接上场即可,升级纯浪费[32](b))
    from sr_od.application.currency_war.cw_state import bench_occupied
    if deployed_occupied(state.deployed or []) >= state.max_units():   # ADR-0392
        bench = state.bench or []
        if bench_occupied(bench) > 0 and any(
                b is not None and b.char_id in targets
                for b in bench):
            return 'pop_slot'
    # 息线以下支出门(方向三,registry.below_floor_spend_gate_enabled
    # 默认关=零漂移;ADR-0434):花后 < interest_floor 时默认拒,仅
    # E1(人口位,臂①已在上方原样返回=收编)与 E3(零息损,⌊gold/10⌋
    # 不变)可达。② DP 臂本就要求 after≥interest_floor,门下自然不达,
    # 零改动;收窄的是 ③ 静态 EV 账——它在 boss 前冲级语境放行过负期望
    # 破息花(`w410_p1_process_quality/` 实证:r9 破息笔中位 32 金换 2 档息损,胜率传导上界
    # 0.12 < 过账所需 0.30)。前置门位置=臂①之后②之前:E1 优先级最高,
    # 例外是白名单不是加分。
    if registry.below_floor_spend_gate_enabled \
            and after < registry.interest_floor() \
            and (working_gold - cost) // 10 < working_gold // 10:
        return ''    # below_floor_spend:息线以下破档升级无例外
    # ② 排程花费授权(平台未破;预算收权批(ADR-0465):确定性查表核单一址,
    # 排程=预告态,可负担性由上方入口门+本行平台判据收口)
    from sr_od.application.currency_war.decision_v2.economy_cycle import (
        schedule_upgrade,
    )
    if schedule_upgrade(state, session) \
            and after >= registry.interest_floor():
        return 'dp'
    # ③ 静态 EV 账(V−C≥0;V 含省刷金项,`w126_b_arm/`/P5 检验点②)
    v = val - int_emb + levelup_refresh_saving(state, session, registry)
    loss_now = _interest_at(working_gold, registry) \
        - _interest_at(after, registry)
    platform = (registry.interest_cap - _interest_at(after, registry)) \
        if after < registry.interest_floor() else 0
    c = (max(0, loss_now) + platform) * cross_plane_remaining_nodes(state)
    return 'static_ev' if v - c >= 0 else ''


#: 扑满守卫环境名(ADR-0348;迁移审计 w113(git 历史) §8-5/E1):「本局的全部奖励节点替换为
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
