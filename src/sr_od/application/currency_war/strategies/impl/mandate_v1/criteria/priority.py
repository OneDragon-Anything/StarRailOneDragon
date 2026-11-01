"""criteria/priority——角色统一让位优先级判据件(唯一排序判据源)。

规格单一源 = ``changes/2026-10-29-unified-priority/details/priority-model.md``
(八档判定表 §2 / 档内键表 §3 / 在手旗标与随机尾键 §4 / 卖出取用形态 §5);
总纲 = 同目录 design.md §2.1。全部卖出/获取消费点(获取角色流程、溢出、
凑钱凑位、补给选角色)只消费本模块 :func:`sort_key` / :func:`sell_order`,
禁第二排序实现(总纲 §2.9 接口契约 1)。

核心模型(总纲 §2.0):部署先行,优先级服务于让位——部署算法定型档 1,
排序作用于部署定型后的局面,回答「手里这些牌谁该让路」。让路方向 =
key 大者先卖(档位编号大 = 优先级低 = 先卖,与总纲 §2.1 一致);因此
各档内「后卖」类属性(总星级数多/单卡星级高)在键里取负号、先卖类属性
(档 8 概率高/低费)取正号。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
from sr_od.application.currency_war.kernel.cw_economy import sell_refund
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    star_base_copies,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.levelup import (
    stay_target_of,
    unfinished_star_targets,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.protection import (
    CROSS_LINE_KEEP_NAMES,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
    LineMembersView,
    line_members_view,
    plane2_started_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

#: 排序键 = (档位, *档内子键, 退金损失, 在手旗标, 随机尾键),字典序比较;
#: 同档子键定长,跨档比较在档位分量即分出(元组比较短路,无跨型比较)。
PriorityKey = tuple[int | float, ...]

#: 档 7 羁绊名单(用户拍板,design §2.1 档 7 / priority-model §2;
#: 巨星独特加成/敌人受伤提高+同频/护盾强度+伤害增幅/敌人挂离火)。
#: 成员判定 = 角色自报 factions/flows 与本名单求交(单一真相源 =
#: data/cw_factions.py FACTIONS 键 × cw_chars 自报,成员关系派生)。
TIER7_BOND_NAMES: frozenset[str] = frozenset(
    {'盛会之星', '量子同频', '护盾', '减益'})


@dataclass(frozen=True)
class HeldUnit:
    """手持牌(场上/备战位统一形态;priority-model §1)。"""

    name: str
    """角色规范名(注册表键空间)。"""
    star: int
    """该副本星级。"""
    slot: int
    """[索引定义] 持牌容器的槽位表下标(备战位槽位表或上场行域,0 基);
    取值时机 = 生成期快照。判据不消费此键(等价牌的卖出序由随机尾键
    承载,槽位号兜底会引入「先买的先卖」系统性偏差,已拍板废弃)。"""
    deployed: bool
    """是否在部署定型内(场上)。
    [全链零消费声明] 排序键各档全不消费此字段——场上/备战位同档同键
    (在池即可卖 = 统一序列的字面语义,场位身份不参与让位排序);字段
    保留仅作构造面语义自描述,防未来误把「场上」当保护维度接入。"""
    cost: int | None = None
    """牌面当前实费档(档 4/档 8 判定输入;None = 回退注册表起始费)。
    变费卡(现注册表仅银狼LV.999 三档)升费后由装配方供给现值,
    现读单一源 = cw_economy.effective_cost;非变费卡可缺省。"""


@dataclass(frozen=True)
class ShopUnit:
    """商店/补给候选牌(在手旗标恒 = 将获取;priority-model §1)。"""

    name: str
    """角色规范名(注册表键空间)。"""
    star: int
    """牌面星级。"""
    cost: int
    """牌面费用档(店卡自报值;变费卡升费后店卡按当前档出现)。"""


@dataclass(frozen=True)
class PriorityContext:
    """排序所需只读输入的装配体(一次性装配,禁散参;priority-model §1)。

    九项输入对应 priority-model §1 清单(持牌全量快照/部署在场名集/
    锁定线名单视图/候选快照/过渡配方对成员/当前升星目标/必要星级表/
    当前等级/随机流),另含 §3 档 2/3/5 档内序数键的装配产物
    ``member_rank``(知识卡 ``member_priority`` 字段直读合成;迁移期
    形态 = core 0/其余 1,逐角色精调归下一迭代外溢)。字段容器按装配
    后只读约定使用。

    聚合谓词口径:档 2/5/6/7 的「持有最高星/总星级数/名下有无副本」
    均消费 ``held_copies`` 全量快照(备战位 ∪ 前后台),与池子过滤无关
    ——池子过滤只决定哪些牌进入排序输出,聚合判定永远看全量。
    """

    held_copies: dict[str, list[int]]
    """①持牌全量快照:角色名 → 该名全部副本星级列表(读源 = 备战位 ∪
    前后台一次只读取,:func:`held_copies_of`)。"""
    deployed_names: frozenset[str]
    """②部署在场名集(档 1 判定输入;读源 = 部署接口
    ``mandate.select_deployment`` 输出,接口契约见
    details/acquisition-and-sell.md §1)。"""
    line_view: LineMembersView
    """③锁定线名单视图(读口 = session_scope.line_members_view;
    锁定帧档 2/3/5 名单 = members,未锁定帧 = 空名单)。"""
    candidate_members: frozenset[str]
    """④候选快照成员并集(读口 = StrategyState.line_candidates 三线经
    COMP_LIBRARY 成员展开 core ∪ shared;未锁定帧档 2/3/5 名单的候选支;
    锁定帧候选快照恒空集,锁定写入时已清空停算)。"""
    recipe_members: frozenset[str]
    """⑤过渡配方对成员(读口 = ``StrategyState.opening_recipe_comp``
    槽位直读 + **读前判窗**——准入唯一判据 = ``plane2_started_of``
    窗口谓词,进位面 2 即退出,锁定不是退出条件;锁定帧照收 = P1 锁定局
    名单为锁定线 ∪ 配方并集。进 P2 后装配侧配方支恒空集,槽位残留
    不消费〔判窗在直读之前,与 direction_comp_of 读口内防御等价〕;
    kernel 配方支清空写点 = cw_intention.clear_p1_recipe)。"""
    stay_target: tuple[str, int, int] | None
    """⑥当前升星目标 (角色名, 必要星级, 当前实费档)(读口 =
    criteria/levelup.stay_target_of,resolved 实费口径变费卡随档;
    None = 未锁定窗口/无未完成目标,档 4 为空)。"""
    need_star_by_member: dict[str, int]
    """⑦必要星级表(读口 = 锁定帧 unfinished_star_targets 现役单一源;
    未锁定帧 = 候选三线知识卡 need_star 字段 COMP_LIBRARY 直查、命中
    各线取最大值)。表外成员 = 1(无升星要求;判定端缺省,含过渡配方
    物化对象等不在 COMP_LIBRARY 的名字)。"""
    member_rank: dict[str, int]
    """档内优先级序数表(§3 档 2/3/5 ①键):成员名 → 序数,小 = 优先级
    高。装配 = 各活性线知识卡 ``member_priority`` 字段直读
    (cw_comps.member_rank_of,空表/旧数据回退 core 两档派生——总纲
    §2.1.1 迁移期形态 = core 0/其余 1);跨线成员取各线最小序数(最高
    优先,core 优先于非 core);过渡配方成员不入表(统一低档,
    priority-model §3 配方支),表外成员判定端缺省 1。逐角色精调归
    下一迭代外溢。"""
    level: int
    """⑧当前等级(档 8 概率查表键 refresh_prob(level, cost))。"""
    rng: random.Random
    """⑨随机流(档内等价牌的随机尾键;策略器自有随机流
    StrategySession.rng 直用,构造时按 strategy_seed 播种,同 seed
    同序——priority-model §4 定案,不新增派生设施)。"""


def held_copies_of(gs: GameState) -> dict[str, list[int]]:
    """持牌全量快照(备战位 ∪ 前后台一次只读取;priority-model §1 读源)。

    返回角色名 → 该名全部副本星级列表(同名跨星全部副本参与聚合,
    落档边界的「名下最高星/总星级数」以角色名为聚合键)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
        deployed_rows_of,
    )
    copies: dict[str, list[int]] = {}
    front, back = deployed_rows_of(gs)
    for u in (*bench_units_of(gs), *front, *back):
        if u is None or not u.char_id:
            continue
        copies.setdefault(u.char_id, []).append(int(u.star or 1))
    return copies


def assemble_priority_context(
        session: StrategySession,
        gs: GameState,
        *,
        deployed_names: frozenset[str],
        held_copies: dict[str, list[int]] | None = None,
        rng: random.Random | None = None) -> PriorityContext:
    """PriorityContext 生产装配(session/gs 读口一次现取)。

    ``deployed_names`` = 部署接口输出(消费位先经
    ``mandate.select_deployment`` 求目标态);``held_copies`` 缺省 =
    容器现读快照,虚拟重算(获取角色流程)传入升星模拟后的虚拟快照;
    ``rng`` 缺省 = session.rng(策略随机语义单一源)。

    两态名单装配(priority-model §2 档 2 名单源;单一准入 = changes/
    2026-10-30-roster-plane1-union design §2.1):锁定帧 = 锁定线
    名单 ∪ 过渡配方成员(P1 锁定局并集),need_star 表取
    ``unfinished_star_targets``(现役消费单一源,仅此帧适用——表只含
    未达标成员,达标成员判定端按缺省 1 自然落档 8);未锁定帧 = 候选
    三线并集 ∪ 过渡配方成员,need_star 取命中各线最大值(保守方向)。
    配方支两态共用同一读口(槽位直读 + 读前判窗),进 P2 后恒空集。

    序数装配(§3 档 2/3/5 ①键)= 知识卡 ``member_priority`` 字段
    直读(:func:`cw_comps.member_rank_of`,空表/旧数据回退 core 两档
    派生),跨线成员取各线最小序数(最高优先);过渡配方成员不入表
    (统一低档,经判定端缺省 1 承载)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import (
        get_comp,
        member_rank_of,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import level_of
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
        state_of,
    )
    view = line_members_view(gs)
    # 方向状态宿主 = gs.strategy_state(与 line_members_view 同宿主;
    # 生产由 cw_strategy 状态 setter 同源接线,session/gs 同一对象——
    # 装配面统一读 gs 侧,禁两宿主混读出同帧两份方向态)。
    st = state_of(gs)
    members: set[str] = set()
    rank: dict[str, int] = {}
    need_star: dict[str, int] = {}
    candidate_out: frozenset[str] = frozenset()
    if view.locked:
        members = set(view.members)
        comp = get_comp(view.comp_name) if view.comp_name else None
        if comp is not None:
            # 序数表 = 锁定线知识卡字段直读(空表回退两档派生)。配方
            # 伪锁帧的锁名不在 COMP_LIBRARY(comp 为 None)→ 不建表,
            # 全员经下方补缺/判定端缺省走低档 1——配方成员低优先级
            # 规则在此分支的承载(priority-model §3 配方支;伪阵容
            # core_chars 为全员 core 形态,直推即高档,禁读)。
            rank = member_rank_of(comp)
        need_star = {name: int(need) for name, need, _cost
                     in unfinished_star_targets(gs)}
        # 锁定帧候选快照照读口真值冻结为空集(锁定写入连带清空停算,
        # StrategyState.line_candidates 恒 = 空集);档 2/3/5 名单 =
        # 锁定线名单(line_view.members 承载)∪ 配方支(recipe_members,
        # P1 锁定局并集;进 P2 后配方支恒空集,判定端无需重复判窗)。
    else:
        for line_name in st.line_candidates:
            c = get_comp(line_name) if line_name else None
            if c is None:
                # 候选线名解析失败(注册表漂移)跳过该线,与
                # protection.protection_membership 同款「跳过并告警」
                # 保守方向——静默跳过会让档 2/3 名单无声缺线,排错时
                # 只能靠行为反推;告警给出线名才能定位漂移源头。
                log.warning('[cw][priority] 候选线名解析失败(%s),'
                            '跳过该线(档 2/3/5 名单缺线)', line_name)
                continue
            members |= set(c.core_chars)
            members |= set(getattr(c, 'shared_chars', None) or ())
            # 序数表 = 各线知识卡字段直读;跨线成员取各线最小序数
            # (序数小 = 优先级高,core 优先于非 core——与旧「cores
            # 并集命中即 0」等价的合成式)。
            for n, p in member_rank_of(c).items():
                rank[n] = min(rank.get(n, p), p)
            for n, need in (getattr(c, 'need_star', None) or {}).items():
                need_star[n] = max(need_star.get(n, 1), int(need))
        candidate_out = frozenset(members)
    recipe_members: frozenset[str] = frozenset()
    if not plane2_started_of(gs):
        # 配方支槽位直读 + 读前判窗(单一准入 §2.1):配方成员进不进
        # 名单唯一判据 = plane2_started_of,锁定不是退出条件——P1
        # 锁定局配方照收;禁经 direction_comp_of 反推名单(方向读口
        # 回答「现行方向是谁」,其锁定不回落的语义 ≠ 名单退出条件)。
        rc = st.opening_recipe_comp
        if rc is not None:
            recipe_members = frozenset(
                {*rc.core_chars, *(getattr(rc, 'shared_chars', None) or ())})
    # 表内补缺:字段未登记的成员按低档 1 兜底——配方成员(不经字段
    # 直读面)统一低档在此完整承载;表外成员判定端缺省 1 不变。
    for n in members:
        rank.setdefault(n, 1)
    return PriorityContext(
        held_copies=held_copies if held_copies is not None
        else held_copies_of(gs),
        deployed_names=deployed_names,
        line_view=view,
        candidate_members=candidate_out,
        recipe_members=recipe_members,
        stay_target=stay_target_of(gs),
        need_star_by_member=need_star,
        member_rank=rank,
        level=int(level_of(gs)),
        rng=rng if rng is not None else session.rng,
    )


#: 随机流派生流的策略器 scratch 挂载键(键名 = 本模块前缀,mandate_state
#: scratch 命名纪律;生命周期 = 局级,状态对象每局冷建自然隔离)。
_PRIORITY_RNG_SCRATCH_KEY: str = 'priority.tier_rng'


def priority_rng_of(session: object,
                    config: object | None = None) -> random.Random:
    """随机流读口(随机尾键单一取源;priority-model §4)。

    - session 宿主自带 rng 槽(StrategySession 形态——kernel 旁表键位/
      sim 直构)直用,策略随机语义单一源,不新增派生设施;
    - 终态契约过渡形态(session 宿主 = gs 容器,零参 decide 管线传容器
      本体,无 rng 槽):按 ``config.strategy_seed`` 播种局级流并挂策略
      器状态 scratch(键见 :data:`_PRIORITY_RNG_SCRATCH_KEY`)——同
      seed 同局同序满足复现契约;config 缺席帧 None→0,与策略器构造
      段的缺省播法同值(cw_strategy 构造 None→0 固定种子)。
    """
    host = getattr(session, 'rng', None)
    if isinstance(host, random.Random):
        return host
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
        state_of,
    )
    st = state_of(session)
    rng = st.scratch.get(_PRIORITY_RNG_SCRATCH_KEY)
    if not isinstance(rng, random.Random):
        seed = getattr(config, 'strategy_seed', None)
        rng = random.Random(seed if seed is not None else 0)
        st.scratch[_PRIORITY_RNG_SCRATCH_KEY] = rng
    return rng


def _member_names(ctx: PriorityContext) -> frozenset[str]:
    """档 2/3/5 阵容成员名单(两态;priority-model §2 名单源;单一准入
    = roster-plane1-union design §2.1)。

    锁定帧 = 锁定线名单 ∪ 过渡配方对成员(P1 锁定局并集——锁定不是
    配方退出条件;进 P2 后装配侧配方支恒空集,判定端无需重复判窗);
    未锁定帧 = 候选三线成员并集 ∪ 过渡配方对成员。"""
    if ctx.line_view.locked:
        return frozenset(ctx.line_view.members) | frozenset(ctx.recipe_members)
    return frozenset(ctx.candidate_members) | frozenset(ctx.recipe_members)


def _unit_cost(unit: HeldUnit | ShopUnit) -> int:
    """牌的费用档(档 4/档 8 判定输入)。

    商店牌 = 牌面自报费用;手持牌 = 牌面实费档(:attr:`HeldUnit.cost`,
    变费卡升费后由装配方按 cw_economy.effective_cost 现值供给),
    缺省回退注册表现查起始费(CHARACTERS.cost,单一源)。未知名/缺值
    按中费 3 保守估(注册表先例 = mandate.cheapest_member_cost 与
    shop 侧同款口径)。"""
    if isinstance(unit, ShopUnit):
        return int(unit.cost)
    if unit.cost is not None:
        return int(unit.cost)
    ch = CHARACTERS.get(unit.name)
    return int(ch.cost) if ch is not None and ch.cost else 3


def _refund_loss(unit: HeldUnit | ShopUnit) -> int:
    """档内并列金币 tie-break 键(用户裁定 2026-10-30 三,金币维全局
    核查表;roster-plane1-union design §2.2 第 1 项)。

    口径 = 再购同件成本 − 卖出退金:再购成本 = 实费档 × 同名 1★ 基础
    副本折算(合成链重建价,折算单一源 = ``star_base_copies``);退金 =
    ``sell_refund`` 单一源。由此 1★ 全额退损失 0 最优,2★+ 折价(合成
    手续费,cost=1 exempt 同损 0)损失 1——同档并列时选不亏的卖,
    保住已付手续费的资产;主判据仍 = 统一序价值序保资产,本键仅在
    现行档内键全部并列后参与定序。键内方向 = 取负号(损失大 = 后卖
    类属性,与模块头「后卖类属性取负号」约定一致)。"""
    cost = _unit_cost(unit)
    star = int(unit.star or 1)
    return cost * star_base_copies(star) - sell_refund(star, cost)


def _tier7_bond_member(name: str) -> bool:
    """档 7 成员判定(角色自报 factions/flows 与拍板名单求交;
    注册表现查,单一真相源 = cw_chars 自报 × cw_factions 键)。"""
    ch = CHARACTERS.get(name)
    if ch is None:
        return False
    return bool((set(ch.factions) | set(ch.flows)) & TIER7_BOND_NAMES)


def interest_exempt_member(name: str, ctx: PriorityContext) -> bool:
    """凑息卖出豁免谓词(单一源;roster-plane1-union design §2.2 第 5 项)。

    豁免集 = 线内成员 ∧ 手持 ∧ 星未达目标:``is_member ∧
    max_star < max(need, 2)``。成员名单与目标星读口同源(sort_key
    同一装配体:名单 = :func:`_member_names` §2.1 单一准入;need =
    ``need_star_by_member`` 现役读口——锁定帧 unfinished_star_targets/
    未锁帧候选知识卡,表外成员缺省 1;星级按角色名聚合 ``held_copies``
    全量快照)。need ≤ 1 的成员底线两星(与档 5 阵容强度形态同杆),
    need ≥ 2 按目标星——现行排序形态下豁免件 = 档 2 升星主线/档 5
    阵容强度;达标成员(≥ max(need,2))掉档 8 已完成资产,不豁免。

    仅供利息动机卖出场景(节末凑息候选池过滤)消费;被迫类卖出
    (溢出/晶矿/获取让位)全员参与统一序列,禁挂本谓词——动机二分
    (§2.2 第 5 项:为利息而卖不得动阵容在建件;因席位/金币被迫按
    优先级卖出的不受此限)。消费点手搓第二份名单/判据 = 违例。"""
    copies = ctx.held_copies.get(name, [])
    if not copies:
        return False   # 非手持(档 3 店内未获取件)不豁免——卖出池只有手持件,防御位
    max_star = max(copies)
    need = ctx.need_star_by_member.get(name, 1)
    return name in _member_names(ctx) and max_star < max(need, 2)


def sort_key(unit: HeldUnit | ShopUnit,
             ctx: PriorityContext) -> PriorityKey:
    """统一优先级排序键(八档判定按序命中即出 + 档内键 + 在手旗标 +
    随机尾键;规格 = priority-model §2/§3/§4,判定表逐档对齐)。

    让路方向 = key 大者先卖:「后卖」类属性(总星级数多/单卡星级高/
    core 成员/退金损失大)取小键,「先卖」类属性(档 8 概率高/低费)
    取大键;在手旗标 手持 = 0 / 将获取 = 1(同优先级在手优先,总纲
    §2.7);随机尾键 = ctx.rng 现抽,仅全部子键相等(同张手持等价牌群)时
    参与定序,同 seed 同序。

    档内合成序(用户裁定三;现行档内键不删):统一序档 → 现行档内键
    (rank/星级/概率/费用)→ 退金损失(:func:`_refund_loss`,损失小者
    先卖)→ 在手旗标(稳定键)→ 随机尾。

    落档边界(priority-model §2):「名下最高星/总星级数」以角色名
    聚合全部在场+备战副本;升星达标(持有最高星 ≥ need_star)后低星
    冗余副本落档 8;万金油/羁绊角色到两星后掉出档 6/7;档 8 的概率
    分档按概率值(非费用号),概率同值并入同档后按费用号稳定序
    (refresh_prob 缺键返 0,低等级帧 2-5 费撞值时低费先卖有真实
    判别语义)。
    """
    name = unit.name
    in_hand = 0 if isinstance(unit, HeldUnit) else 1
    tail = ctx.rng.random()
    copies = ctx.held_copies.get(name, [])
    max_star = max(copies) if copies else 0
    total_star = sum(copies)
    unit_star = int(unit.star or 1)
    # 退金损失取负入键(损失大 = 后卖):仅同档现行键全并列时参与定序。
    refund_loss = -_refund_loss(unit)
    is_member = name in _member_names(ctx)
    # 档 1 前后台需要出战的(部署算法定型;按角色名命中,含商店同名牌
    # ——在场角色的牌 = 部署需要面)。获取让位评估例外:将获取的 X 不进
    # deployed_names(shop 侧装配时减名)——X 的去留正是评估要回答的问题,
    # 享受部署保护会把「末位 = X → 放弃」分支变成不可达(XT-1 同步)。
    if name in ctx.deployed_names:
        return (1, refund_loss, in_hand, tail)
    # 档 2 有星级要求但还没升到目标星(升星主线;「有星级要求」= need_star
    # ≥ 2,need = 1 即无升星要求——落档边界谓词,need=1 成员未持落档 3 /
    # 已持未到两星落档 5)。
    need = ctx.need_star_by_member.get(name, 1)
    if is_member and need >= 2 and max_star < need:
        return (2, ctx.member_rank.get(name, 1), -total_star, -unit_star,
                refund_loss, in_hand, tail)
    # 档 3 阵容成员还没获取任何副本(仅商店牌可命中:手持牌自身即副本)。
    if is_member and not copies:
        return (3, ctx.member_rank.get(name, 1), refund_loss, in_hand, tail)
    # 档 4 当前升星目标实费档的牌(压牌库价值;阵容成员整体排除——
    # 含已达标成员,其副本按落档边界落档 8;目标为 None 本档为空)。
    if ctx.stay_target is not None and not is_member \
            and _unit_cost(unit) == ctx.stay_target[2]:
        return (4, -unit_star, refund_loss, in_hand, tail)
    # 档 5 成员已获取、无星级要求、还没到两星(阵容强度)。
    if is_member and copies and need <= 1 and max_star < 2:
        return (5, ctx.member_rank.get(name, 1), -total_star,
                refund_loss, in_hand, tail)
    # 档 6 万金油名单还没到两星(全线留用层;到两星掉档 8)。
    if name in CROSS_LINE_KEEP_NAMES and max_star < 2:
        return (6, -total_star, refund_loss, in_hand, tail)
    # 档 7 buff/debuff 羁绊成员还没到两星(到两星掉档 8)。
    if _tier7_bond_member(name) and max_star < 2:
        return (7, -total_star, refund_loss, in_hand, tail)
    # 档 8 兜底:概率高者先卖(容易再遇),同概率档并入同档、低费先卖,
    # 星级高者后卖。
    prob = refresh_prob(ctx.level, _unit_cost(unit))
    return (8, prob, -_unit_cost(unit), -unit_star,
            refund_loss, in_hand, tail)


def sell_order_with_keys(
        units: list[HeldUnit | ShopUnit],
        ctx: PriorityContext) -> list[tuple[HeldUnit | ShopUnit, PriorityKey]]:
    """统一让位序列带排序键(观测面载体;排序实现与 :func:`sell_order`
    同一份——键 = :func:`sort_key` 输出逐位同源,禁消费位自算第二份)。

    返回按键升序的 ``(单位, 排序键)`` 列表(末位 = 最先让路)。观测
    消费位(档位分布/随机尾键命中)从键分量直读:档位 = 键首分量,
    尾键命中 = 池内存在另一件键去尾后与本件全同(等价牌群内部随机
    定序实际生效,priority-model §4 随机域)。
    """
    keyed = [(u, sort_key(u, ctx)) for u in units]
    keyed.sort(key=lambda p: p[1])
    return keyed


def sell_order(units: list[HeldUnit | ShopUnit],
               ctx: PriorityContext) -> list[HeldUnit | ShopUnit]:
    """统一让位序列(priority-model §5 消费侧约定)。

    返回从「最不该卖」到「最先让路」的升序序列(末位 = 最先让路);
    各触发消费位从末位向前取用(让路一张 / 取到凑够为止)。注意:
    逐牌调 :func:`sort_key` 会推进随机流,同 seed 下同输入同序、
    跨次调用不保证逐位复现(随机域 = 手持等价牌群内部,无行为语义
    损失,priority-model §4)。"""
    return [u for u, _k in sell_order_with_keys(units, ctx)]
