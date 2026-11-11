"""criteria/priority——角色统一让位优先级判据件(唯一排序判据源)。

判定规格单一源 = strategy-docs/32_unified_sell_priority.md(下称 32 号稿)
(排序输入与两态名单 §2 / 十档判定表 §3 / 保留张与落档边界 §4-§5 /
档内键口径注 §6 / 在手旗标与随机尾键 §7 / 卖出取用形态 §8)。全部
卖出/获取消费点(获取角色流程、溢出、凑钱凑位、补给选角色)只消费
本模块 :func:`sort_key` / :func:`sell_order`,禁第二排序实现(32 号稿 §1)。

核心模型:部署先行,优先级服务于让位——部署算法定型档 1,
排序作用于部署定型后的局面,回答「手里这些牌谁该让路」。让路方向 =
key 大者先卖(档位编号大 = 优先级低 = 先卖);因此
各档内「后卖」类属性(总星级数多/单卡星级高)在键里取负号、先卖类属性
(档 10 概率高/低费)取正号。

成员档双层装配(32 号稿 §2):终局成员 =
实候选(证据门版快照)三线并集,过渡成员 = 过渡候选各对成员并集
(``transition_candidates`` 槽展开),进同一档判定(2/3/4/5/7)谓词
同构;``member_rank`` 键 = (层, 位次) 二元组,字典序承载「同档占位、
档内垫底」,十档结构与键域零改动。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
from sr_od.application.currency_war.kernel.cw_economy import sell_refund
from sr_od.application.currency_war.kernel.cw_intention import (
    transition_active_entries,
    transition_member_union,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    star_base_copies,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.levelup import (
    stay_target_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.line_select import (
    CANDIDATE_TOP_N,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.protection import (
    CROSS_LINE_KEEP_NAMES,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
    LineMembersView,
    line_members_view,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        SimAcquisition,
    )

#: 排序键 = (档位, *档内子键, 退金损失, 在手旗标, 随机尾键),字典序比较;
#: 同档子键定长,跨档比较在档位分量即分出(元组比较短路,无跨型比较)。
#: 成员档(2/3/4/5/7)①键为 (层, 位次) 二元组(嵌套元组分量,同档内
#: 同型比较;§2.4-3)。
PriorityKey = tuple[int | float | tuple[int, int], ...]

#: member_rank 判定端缺省(表外/非候选成员)= 过渡层末位 (1, CANDIDATE_TOP_N)
#: ——与第三候选并列垫底,由后续键判别(32 号稿 §2
#: 成员档序数键;复用候选数常数,零新数值)。
RANK_TRANSITION_BOTTOM: tuple[int, int] = (1, CANDIDATE_TOP_N)

#: 档 9 羁绊名单(原档 7,名单与成员判定不变、仅档号位移;用户决定,
#: 判定表权威版本 = 32 号稿 §3 档 9 行;
#: 巨星独特加成/敌人受伤提高+同频/护盾强度+伤害增幅/敌人挂离火)。
#: 成员判定 = 角色自报 factions/flows 与本名单求交(单一真相源 =
#: data/cw_factions.py FACTIONS 键 × cw_chars 自报,成员关系派生)。
TIER7_BOND_NAMES: frozenset[str] = frozenset(
    {'盛会之星', '量子同频', '护盾', '减益'})


@dataclass(frozen=True)
class HeldUnit:
    """手持牌(场上/备战位统一形态;32 号稿 §2)。"""

    name: str
    """角色规范名(注册表键空间)。"""
    star: int
    """该副本星级。"""
    slot: int
    """[索引定义] 持牌状态容器的槽位表下标(备战位槽位表或上场行域,0 基);
    取值时机 = 生成期快照。判据不消费此键(等价牌的卖出序由随机尾键
    承载,槽位号兜底会引入「先买的先卖」系统性偏差,已用户决定废弃)。"""
    deployed: bool
    """是否在部署定型内(场上)。
    [全链零消费声明] 排序键各档全不消费此字段——场上/备战位同档同键
    (在池即可卖 = 统一序列的字面语义,场位身份不参与让位排序);字段
    保留仅作构造面语义自描述,防未来误把「场上」当保护维度接入。"""
    cost: int | None = None
    """牌面当前实费档(档 6/档 10 判定输入;None = 回退注册表起始费)。
    变费卡(现注册表仅银狼LV.999 三档)升费后由装配方供给现值,
    现读单一源 = cw_economy.effective_cost;非变费卡可缺省。"""


@dataclass(frozen=True)
class ShopUnit:
    """商店/补给候选牌(在手旗标恒 = 将获取;32 号稿 §2)。"""

    name: str
    """角色规范名(注册表键空间)。"""
    star: int
    """牌面星级。"""
    cost: int
    """牌面费用档(店卡自报值;变费卡升费后店卡按当前档出现)。"""


@dataclass(frozen=True)
class PriorityContext:
    """排序所需只读输入的装配体(一次性装配,禁散参;32 号稿 §2)。

    输入清单与各字段读口见 32 号稿 §2(持牌全量快照/部署在场名集/
    锁定线名单视图/候选快照/过渡候选成员/当前升星目标/必要星级表/
    当前等级/随机流,另含档 2/3/4/5/7 档内序数键的装配产物
    ``member_rank``(知识卡 ``member_priority`` 字段直读合成;迁移期
    形态 = core 0/其余 1,逐角色精调归下一迭代外溢))。字段结构按装配
    后只读约定使用。

    聚合谓词口径:档 2/3/4/5/7/8/9 的「持有最高星/总星级数/名下有无副本」
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
    锁定帧成员档(2/3/4/5/7)名单 = members,未锁定帧 = 空名单)。"""
    candidate_members: frozenset[str]
    """④实候选成员并集(读口 = StrategyState.line_candidates 三线经
    COMP_LIBRARY 成员展开 core ∪ shared;**证据门版快照**——12 号篇
    §1.2 候选入选证据门:零证据线不入候选,热度只作有
    证据线间排序;未锁定帧成员档名单的终局半边。锁定帧候选快照恒空集,
    锁定写入时已清空停算)。"""
    recipe_members: frozenset[str]
    """⑤过渡层贡献名单(读口 = ``cw_intention.transition_active_entries``
    活跃条目经 ``transition_member_set`` 展开〔锁定 = 锁定条目成员,
    未锁 = 候选条目并集〕+ **读前判据 = 终局锁定态**——终局锁定即恒空,
    候选槽/锁定态在锁定写入点同点清空;未终局锁定帧照常贡献,含位面 2
    未终局锁定帧〔换轴:过渡机制生命周期挂钩终局锁定事件〕)。未锁定帧
    成员档名单的过渡半边(32 号稿 §2 双层名单)。"""
    stay_target: tuple[str, int, int] | None
    """⑥当前升星目标 (角色名, 必要星级, 当前实费档)(读口 =
    criteria/levelup.stay_target_of,resolved 实费口径变费卡随档;
    None = 未锁定窗口/无未完成目标,档 6 为空)。"""
    need_star_by_member: dict[str, int]
    """⑦必要星级表(读口 = 锁定帧锁定线知识卡 need_star 字段全量
    照录——达标成员不缺省,完成品保护档 2/4 的锁定帧判定输入;
    未锁定帧 = 实候选三线知识卡 need_star 字段 COMP_LIBRARY 直查、命中
    各线取最大值 + 过渡条目点名成员按条目 need_star 值入表〔命中多条
    目取最大值,保守方向〕)。**未点名过渡成员不入表**(统一缺省 1
    ——§2.3-5 过渡成员星级要求统一 need=1);表外成员 = 1(无升星
    要求;判定端缺省,含羁绊半边放大器/凑数件等不经 COMP_LIBRARY
    查询面的名字)。"""
    member_rank: dict[str, tuple[int, int]]
    """档内优先级序数表(档 2/3/4/5/7 ①键,取值规则 = 32 号稿 §2):
    成员名 → (层, 位次) 二元组,
    小 = 优先级高。终局成员 = (0, 线内序数)——各活性线知识卡
    ``member_priority`` 字段直读(cw_comps.member_rank_of,空表/旧数据
    回退 core 两档派生 = core 0/其余 1,32 号稿 §2 取值规则),
    跨线成员取各线最小序数(字典序 min,core 优先于非 core);过渡
    成员 = (1, 线内两档位次)(条目 ``member_rank_of`` 的 core=0/其余=1,
    跨多条目同名成员取最小位次,与终局侧同构);重叠成员归终局(装配序
    终局在前 + 过渡 setdefault,rank 取终局值,零特判)。表外成员判定端缺省
    :data:`RANK_TRANSITION_BOTTOM` = (1, CANDIDATE_TOP_N)。逐角色
    精调归下一迭代外溢。"""
    level: int
    """⑧当前等级(档 10 概率查表键 refresh_prob(level, cost))。"""
    rng: random.Random
    """⑨随机流(档内等价牌的随机尾键;策略器自有随机流
    StrategySession.rng 直用,构造时按 strategy_seed 播种,同 seed
    同序——32 号稿 §7 定案,不新增派生设施)。"""


def held_copies_of(gs: GameState) -> dict[str, list[int]]:
    """持牌全量快照(备战位 ∪ 前后台一次只读取;32 号稿 §2 读源)。

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


def _transition_member_ranks(entries) -> dict[str, tuple[int, int]]:
    """过渡层活跃条目 → 成员位次表((1, 线内两档位次);32 号稿 §2)。

    位次 = ``cw_comps.member_rank_of`` 的线内两档(core=0/其余=1——
    过渡条目 shared 空,点名成员位次 0、羁绊半边放大器/凑数件表外
    落判定端缺省 RANK_TRANSITION_BOTTOM);层值恒 1 = 过渡层。
    多条目同名成员跨条目取最小位次(与终局侧「跨线取最小序数」同构)。
    条目域单一源 = ``cw_intention.transition_active_entries``(锁定
    条目在前;成员展开单一源 = transition_member_set,禁消费点另写)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import member_rank_of
    out: dict[str, tuple[int, int]] = {}
    for entry in entries:
        for n, p in member_rank_of(entry).items():
            r = (1, p)
            cur = out.get(n)
            if cur is None or r < cur:
                out[n] = r
    return out


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
    状态容器现读快照,虚拟重算(获取角色流程)传入升星模拟后的虚拟快照;
    ``rng`` 缺省 = session.rng(策略随机语义单一源)。

    两态名单装配(成员档 2/3/4/5/7 名单源;双层 = 32 号稿 §2):
    终局锁定帧 = 锁定线名单(过渡层在终局锁定写入点退役清空,
    过渡支恒空),need_star 表 = 锁定线知识卡 need_star 字段全量
    照录(达标成员不缺省——need≥2 完成品保护档 2 的锁定帧判定输入;
    ``unfinished_star_targets`` 本体不动,其「未完成目标」原始语义与
    其余消费位不受影响);未锁定帧 = 实候选(证据门版快照)三线并集
    ∪ 过渡层贡献名单(``transition_active_entries`` 展开:过渡锁定 =
    锁定条目成员,未过渡锁定 = 候选条目并集),need_star 取命中各线
    最大值(保守方向),**过渡条目点名成员按条目 need_star 值入表**
    (命中多条目/与终局候选同名取最大值;未点名过渡成员缺省 1,
    §2.3-5)。过渡支两态共用同一读口,读前判据 = **终局锁定态**
    (换轴:过渡机制生命周期挂钩终局锁定事件,位面 2 未终局锁定帧
    过渡层照常活跃)。

    序数装配(档 2/3/4/5/7 ①键,(层, 位次) 二元组;§2.4-3)
    = 知识卡 ``member_priority`` 字段直读(:func:`cw_comps.member_rank_of`,
    空表/旧数据回退 core 两档派生)包 ``(0, 线内序数)``,跨线成员取
    各线最小序数(最高优先);过渡成员按条目 ``member_rank_of`` 线内
    两档(core=0/其余=1)包 ``(1, 线内两档位次)``(跨条目同名取最小
    位次,与终局侧「跨线取最小序数」同构);装配序终局在前 + 过渡
    ``setdefault`` ——重叠成员 rank 取终局值(零特判)。
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
    # 生产由 cw_strategy 状态 setter 同源接入调用,session/gs 同一对象——
    # 装配面统一读 gs 侧,禁两宿主混读出同帧两份方向态)。
    st = state_of(gs)
    members: set[str] = set()
    rank: dict[str, tuple[int, int]] = {}
    need_star: dict[str, int] = {}
    candidate_out: frozenset[str] = frozenset()
    if view.locked:
        members = set(view.members)
        comp = get_comp(view.comp_name) if view.comp_name else None
        if comp is not None:
            # 序数表 = 锁定线知识卡字段直读(空表回退两档派生),包
            # (0, 线内序数)。comp 为 None(锁名不在 COMP_LIBRARY,
            # 注册表漂移防御位)→ 不建表,全员经下方补缺/判定端缺省
            # 走低档。(原「配方伪锁帧」承载说明随配方决策层退役——
            # 锁定线名现恒为 COMP_LIBRARY 成员。)
            rank = {n: (0, p) for n, p in member_rank_of(comp).items()}
        # need_star 表 = 知识卡字段全量照录,达标成员不缺省:缺省 1 会
        # 让 need≥2 完成品保护谓词在锁定帧永不命中、达标完成品错落
        # 无星级要求档——「只收未达标成员」是 unfinished_star_targets
        # 的「未完成目标」原始语义,不满足本表语义,本帧不经其装配
        # (其本体与升级触发/停留目标等其余消费位不受影响);comp 为
        # None(漂移)→ 表空,判定端缺省照旧。
        need_star = {name: int(need) for name, need
                     in (getattr(comp, 'need_star', None) or {}).items()}
        # 锁定帧候选快照照读口真值冻结为空集(锁定写入连带清空停算,
        # StrategyState.line_candidates 恒 = 空集);终局锁定帧过渡层
        # 已在锁定写入点退役清空(recipe_members 恒空),成员档
        # (2/3/4/5/7)名单 = 锁定线名单(line_view.members 承载)。
    else:
        for line_name in st.line_candidates:
            c = get_comp(line_name) if line_name else None
            if c is None:
                # 候选线名解析失败(注册表漂移)跳过该线,与
                # protection.protection_membership 同款「跳过并告警」
                # 保守方向——静默跳过会让成员档(2/3/4/5/7)名单无声
                # 缺线,排错时只能靠行为反推;告警给出线名才能定位
                # 漂移源头。
                log.warning('[cw][priority] 候选线名解析失败(%s),'
                            '跳过该线(档 2/3/4/5/7 名单缺线)', line_name)
                continue
            members |= set(c.members)
            # 序数表 = 各线知识卡字段直读,包 (0, 线内序数);跨线成员
            # 取各线最小序数(二元组字典序 min,(0,·) 域内 = 序数最小,
            # core 优先于非 core——与旧「cores 并集命中即 0」等价的
            # 合成式)。
            for n, p in member_rank_of(c).items():
                r_final = (0, p)
                rank[n] = min(rank.get(n, r_final), r_final)
            for n, need in (getattr(c, 'need_star', None) or {}).items():
                need_star[n] = max(need_star.get(n, 1), int(need))
        candidate_out = frozenset(members)
    # 表内补缺:字段未登记的终局成员按 (0, 1) 兜底(终局层低位次);
    # 表外成员判定端缺省 RANK_TRANSITION_BOTTOM 不变。
    for n in members:
        rank.setdefault(n, (0, 1))
    # 过渡支(换轴:过渡成员进不进名单唯一判据 = 终局锁定态——未终局
    # 锁定即照常贡献,终局锁定即恒空〔候选槽/锁定态在锁定写入点同点
    # 清空〕;原位面判窗 plane2_started_of 随生命周期挂钩终局锁定事件
    # 废除,位面 2 未终局锁定帧过渡层照常活跃)。禁经 direction_comp_of
    # 反推名单(方向读口回答「现行方向是谁」,其锁定不回落的语义 ≠
    # 名单退出条件)。装配序在终局半边 + 补缺之后:setdefault 承载
    # 重叠归终局(rank 取终局值,零特判)与跨条目最小位次。
    transition_members: frozenset[str] = frozenset()
    if not view.locked:
        entries = transition_active_entries(st)
        transition_ranks = _transition_member_ranks(entries)
        transition_members = transition_member_union(st)
        for n, r in transition_ranks.items():
            rank.setdefault(n, r)
        # need_star 申报(行为变化):过渡条目点名成员按条目 need_star
        # 值入表(命中多条目/与终局候选同名取最大值,保守方向),未点名
        # 过渡成员仍缺省 1(§2.3-5)——铁三角 2★ 达标受完成品保护、
        # 希儿 3★ 进升星主线。
        for entry in entries:
            for n, need in (getattr(entry, 'need_star', None) or {}).items():
                need_star[n] = max(need_star.get(n, 1), int(need))
    return PriorityContext(
        held_copies=held_copies if held_copies is not None
        else held_copies_of(gs),
        deployed_names=deployed_names,
        line_view=view,
        candidate_members=candidate_out,
        recipe_members=transition_members,
        stay_target=stay_target_of(gs),
        need_star_by_member=need_star,
        member_rank=rank,
        level=int(level_of(gs)),
        rng=rng if rng is not None else session.rng,
    )


#: 随机流派生流的策略器 scratch 挂载键(键名 = 本模块前缀,mandate_state
#: scratch 命名纪律;生命周期 = 局级,状态对象每局全新创建自然隔离)。
_PRIORITY_RNG_SCRATCH_KEY: str = 'priority.tier_rng'


def assemble_candidate_eval(
        session: StrategySession,
        gs: GameState,
        *,
        sim: SimAcquisition,
        base_bench_len: int,
        target: dict[str, tuple[str, int]],
        name: str, star: int, cost: int,
        config: object | None = None,
) -> tuple[PriorityContext, list[HeldUnit | ShopUnit]]:
    """候选评估装配整函数(获取让位〔11 号稿 §4.0 步 4〕与补给选角
    〔30 号篇 §2.1〕的统一入口;补给统一优先级裁定后两域同一实现)。

    三段一体,禁消费位手搓第二份装配:虚拟持牌全量快照聚合 →
    优先级装配(档 1 名集 = 定型名集减候选名)→ 让位池构造(部署外
    全集 = 虚拟备战位 ∪ 虚拟场上部署外件)。域差异仅候选牌三件套由
    调用方给值(商店 X 按牌面带费;补给候选恒 1★、选卡零成本——
    零成本进键 = 档 10 概率分量取 0〔免费件无「再遇成本」语义〕、
    档 6 压牌库带永不含)。

    - ``sim`` = 升星连锁模拟产物;``base_bench_len`` = 快照备战位长
      (置入新牌的 origin 哨兵 = len(bench),据此甄别新牌本体,由
      ShopUnit 承载不双计——新牌的在手影子抢先会失真末位判定);
    - ``target`` = 虚拟定型输出(``select_deployment`` 返回值;名集
      消费 = frozenset(target))。候选名只从档 1 名集减去、不从
      ``target`` 本体剔除(虚拟定型仍含候选参与板面构成,存量件的
      档 1 排除面不因减名变化):候选 = 「假设性入场者」,其去留
      正是评估要回答的问题,进档 1 保护会经虚拟定型自我保护、
      「末位 = 候选」分支在纳入统一结构形态不可达;
    - 返回 ``(ctx, units)``:``units`` 末位恒为候选 ShopUnit(将获取
      旗标);存量件以 HeldUnit(在手旗标)承载,部署定型内件(档 1
      按名命中)与系统召唤件(不可卖物理门;席位占用仍由虚拟局面
      如实承载)不入池。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        effective_cost,
    )
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
        predicates,
    )
    v_bench = [bs for _i, bs in sim.bench]
    # 段 1:虚拟持牌全量快照(档 2/3/4/5/7/8/9 聚合谓词看虚拟局面
    # 全量——含置入候选与升星连锁产物,与池子过滤无关)。
    v_copies: dict[str, list[int]] = {}
    for u in (*(bench_slot_unit(b) for b in v_bench), *sim.field):
        if u is not None and u.char_id:
            v_copies.setdefault(str(u.char_id), []).append(
                int(u.star or 1))
    # 段 2:优先级装配——档 1 名集 = 定型名集减候选名(dict 冒
    # frozenset 的类型面问题随统一装配消除,名集恒 frozenset)。
    ctx = assemble_priority_context(
        session, gs,
        deployed_names=frozenset(target) - {name},
        held_copies=v_copies,
        rng=priority_rng_of(session, config))
    # 段 3:让位池 = 部署外全集(bench 侧 + field 侧同构过滤:定型
    # 内件不入池、系统件不入池;field 撤下件〔虚拟定型换人后被移出
    # 定型的在场件〕入池——两域同一比较域)。
    target_names = frozenset(target)
    units: list[HeldUnit | ShopUnit] = []
    for orig, bs in sim.bench:
        if orig >= base_bench_len:
            continue   # 置入的新牌 = 由 ShopUnit 承载,不双计
        u = bench_slot_unit(bs)
        if u is None or not u.char_id:
            continue
        if predicates.is_unsellable_system_unit(str(u.char_id)):
            continue
        if str(u.char_id) in target_names:
            continue   # 档 1(部署定型内,按名命中)不入让位池
        units.append(HeldUnit(
            str(u.char_id), int(u.star or 1), orig, False,
            cost=(effective_cost(gs, str(u.char_id)) or None)))
    for _di, u in enumerate(sim.field):
        if u is None or not u.char_id:
            continue
        if predicates.is_unsellable_system_unit(str(u.char_id)):
            continue
        if str(u.char_id) in target_names:
            continue
        units.append(HeldUnit(
            str(u.char_id), int(u.star or 1), _di, True,
            cost=(effective_cost(gs, str(u.char_id)) or None)))
    units.append(ShopUnit(name, star, cost))
    return ctx, units


def priority_rng_of(session: object,
                    config: object | None = None) -> random.Random:
    """随机流读口(随机尾键单一取源;32 号稿 §7)。

    - session 宿主自带 rng 槽(StrategySession 形态——kernel 旁表键位/
      sim 直构)直用,策略随机语义单一源,不新增派生设施;
    - 终态契约过渡形态(session 宿主 = gs 状态容器,零参 decide 管线传状态容器
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
    """成员档(2/3/4/5/7)阵容成员名单(双层;32 号稿 §2 名单源)。

    终局锁定帧 = 锁定线名单(过渡层已退役清空,装配侧恒空——判定端
    无需重复判据);未锁定帧 = 实候选(证据门版)三线成员并集 ∪
    过渡层贡献名单。"""
    if ctx.line_view.locked:
        return frozenset(ctx.line_view.members) | frozenset(ctx.recipe_members)
    return frozenset(ctx.candidate_members) | frozenset(ctx.recipe_members)


def _unit_cost(unit: HeldUnit | ShopUnit) -> int:
    """牌的费用档(档 6/档 10 判定输入)。

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
    核查表;退金损失键口径 = 32 号稿 §6)。

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
    """档 9 成员判定(原档 7,名单与判定规则不变、仅档号位移;
    角色自报 factions/flows 与用户决定名单求交;
    注册表现查,单一真相源 = cw_chars 自报 × cw_factions 键)。"""
    ch = CHARACTERS.get(name)
    if ch is None:
        return False
    return bool((set(ch.factions) | set(ch.flows)) & TIER7_BOND_NAMES)


def interest_exempt_member(name: str, ctx: PriorityContext) -> bool:
    """凑息卖出豁免谓词(单一源;32 号稿 §9 凑息豁免行/11 号稿 §4.0 场景表)。

    豁免集 = 线内成员 ∧ 手持 ∧ 星未达目标:``is_member ∧
    max_star < max(need, 2)``。成员名单与目标星读口同源(sort_key
    同一装配体:名单 = :func:`_member_names` 双层并集;need =
    ``need_star_by_member`` 现役读口——锁定帧锁定线知识卡全量照录/
    未锁帧实候选知识卡,过渡候选成员不入表缺省 1(§2.4-5 豁免语义
    对过渡成员同构生效:need=1 → 底线两星,未满两星的过渡在建件
    同受豁免);星级按角色名聚合 ``held_copies`` 全量快照)。
    need ≤ 1 的成员底线两星(与档 7 阵容强度形态同杆),
    need ≥ 2 按目标星——现行排序形态下豁免件 = 档 3 升星主线/档 7
    阵容强度;达标成员(≥ max(need,2))经完成品保护档 2/4 殿后、
    非保留张副本落兜底档 10,均不豁免。

    仅供利息动机卖出场景(节末凑息候选池过滤)消费;被迫类卖出
    (溢出/晶矿/获取让位)全员参与统一序列,禁挂本谓词——动机二分
    (§2.2 第 5 项:为利息而卖不得动阵容在建件;因席位/金币被迫按
    优先级卖出的不受此限)。消费点手搓第二份名单/判据 = 违例。"""
    copies = ctx.held_copies.get(name, [])
    if not copies:
        return False   # 非手持(档 5 店内未获取件)不豁免——卖出池只有手持件,防御位
    max_star = max(copies)
    need = ctx.need_star_by_member.get(name, 1)
    return name in _member_names(ctx) and max_star < max(need, 2)


def is_kept_unit(unit: HeldUnit | ShopUnit, unit_star: int,
                 copies: list[int]) -> bool:
    """保留张谓词(排序单位 = 单张牌的核心判定位;档 2/档 4 完成品
    保护共用)。

    本张是该名保留张 = 本张星级 == 名下最高星 且 该最高星在此名下
    仅此一张(``unit_star == max_star ∧ copies.count(max_star) == 1``;
    ``copies`` = 该名全部副本星级聚合快照)。等价群自愈语义:同星
    多张时全部不属保留张(等价牌先卖哪张无差别,全落兜底档 10),
    任一张卖出后名下张数变化,剩余最高星张自动恢复保留身份。

    身份域:仅 :class:`HeldUnit`(在手牌)可为保留张,:class:`ShopUnit`
    (候选牌)恒 False——获取让位评估的虚拟语境下,将获取的 X 不享受
    完成品保护,「末位 = X → 放弃买入」分支保持可达(与 X 不进档 1
    部署保护同构:保护对象 = 已入手资产,候选值不值得买仍由让位试探
    回答,不由排序身份预支)。
    """
    if not isinstance(unit, HeldUnit):
        return False
    max_star = max(copies) if copies else 0
    return unit_star == max_star and copies.count(max_star) == 1


def sort_key(unit: HeldUnit | ShopUnit,
             ctx: PriorityContext) -> PriorityKey:
    """统一优先级排序键(十档判定按序命中即出 + 档内键 + 在手旗标 +
    随机尾键;档内序数键与随机流契约 = 32 号稿 §2/§7,判定表
    权威版本 = 32 号稿 §3,本函数体为实现、逐档注释为行内定位)。

    让路方向 = key 大者先卖:「后卖」类属性(总星级数多/单卡星级高/
    core 成员/退金损失大)取小键,「先卖」类属性(档 10 概率高/低费)
    取大键;在手旗标 手持 = 0 / 将获取 = 1(同优先级在手优先,总纲
    §2.7);随机尾键 = ctx.rng 现抽,仅全部子键相等(同张手持等价牌群)时
    参与定序,同 seed 同序。

    档内合成序(用户裁定三;现行档内键不删):统一序档 → 现行档内键
    (rank/星级/概率/费用)→ 退金损失(:func:`_refund_loss`,损失小者
    先卖)→ 在手旗标(稳定键)→ 随机尾。成员档 ①键 rank = (层, 位次)
    二元组(32 号稿 §2:终局 (0, 线内序数)/
    过渡 (1, 候选位次)/表外缺省 :data:`RANK_TRANSITION_BOTTOM`)——
    字典序承载「同档占位、档内垫底」:同档内过渡成员键恒大于终局
    成员,先让路。

    落档边界:「名下最高星/总星级数」以角色名聚合全部在场+备战副本;
    排序单位 = 单张牌——同名的牌按保留张身份(:func:`is_kept_unit`)
    分家,星级要求内的完成品(每名保留恰好一张最高星)居档 2/4,要求
    以外的多余副本与同星等价群落兜底档 10(等价群自愈:任一张卖出后
    剩余最高星张自动恢复保留身份);万金油/羁绊角色到两星后掉出
    档 8/9;档 10 的概率分档按概率值(非费用号),概率同值并入同档后
    按费用号稳定序(refresh_prob 缺键返 0,低等级帧 2-5 费撞值时低费
    先卖有真实判别语义)。
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
    # 档 2 完成品保护:need≥2 达标成员的保留张(名下最高星的唯一张,
    # 含超额完成如 3★)。排序单位 = 单张牌:达标名下的冗余副本(低星/
    # 同星多张)保留谓词不中、档 3 亦不中(max_star 已达标),自然落
    # 兜底档 10(零新增显式判定路径)。
    need = ctx.need_star_by_member.get(name, 1)
    if is_member and need >= 2 and max_star >= need \
            and is_kept_unit(unit, unit_star, copies):
        return (2, ctx.member_rank.get(name, RANK_TRANSITION_BOTTOM),
                -total_star, -unit_star, refund_loss, in_hand, tail)
    # 档 3 有星级要求但还没升到目标星(升星主线;「有星级要求」= need_star
    # ≥ 2,need = 1 即无升星要求——落档边界谓词,need=1 成员未持落档 5 /
    # 已持未到两星落档 7)。
    if is_member and need >= 2 and max_star < need:
        return (3, ctx.member_rank.get(name, RANK_TRANSITION_BOTTOM),
                -total_star, -unit_star, refund_loss, in_hand, tail)
    # 档 4 完成品保护:need≤1(无星级要求)成员到两星后的保留张——
    # 底线两星口径,2★ 本体与超额 3★ 均按实际最高星受保;凑两星中间态
    # (max_star<2)不入本档,走档 7 过程保护;空 copies 由 max_star≥2
    # 与保留谓词双重自然排除。
    if is_member and need <= 1 and max_star >= 2 \
            and is_kept_unit(unit, unit_star, copies):
        return (4, ctx.member_rank.get(name, RANK_TRANSITION_BOTTOM),
                -total_star, -unit_star, refund_loss, in_hand, tail)
    # 档 5 阵容成员还没获取任何副本(仅商店牌可命中:手持牌自身即副本)。
    if is_member and not copies:
        return (5, ctx.member_rank.get(name, RANK_TRANSITION_BOTTOM),
                refund_loss, in_hand, tail)
    # 档 6 当前升星目标实费档的牌(压牌库价值;阵容成员整体排除——
    # 成员副本按完成品保护档 2/4、升星主线档 3 或凑两星档 7 各归其档;
    # 目标为 None 本档为空)。
    if ctx.stay_target is not None and not is_member \
            and _unit_cost(unit) == ctx.stay_target[2]:
        return (6, -unit_star, refund_loss, in_hand, tail)
    # 档 7 成员已获取、无星级要求、还没到两星(阵容强度/凑两星过程
    # 保护;原档 5 语义原样保留,仅档号位移)。
    if is_member and copies and need <= 1 and max_star < 2:
        return (7, ctx.member_rank.get(name, RANK_TRANSITION_BOTTOM),
                -total_star, refund_loss, in_hand, tail)
    # 档 8 万金油名单还没到两星(全线留用层;到两星掉兜底档 10)。
    if name in CROSS_LINE_KEEP_NAMES and max_star < 2:
        return (8, -total_star, refund_loss, in_hand, tail)
    # 档 9 buff/debuff 羁绊成员还没到两星(到两星掉兜底档 10)。
    if _tier7_bond_member(name) and max_star < 2:
        return (9, -total_star, refund_loss, in_hand, tail)
    # 档 10 兜底:概率高者先卖(容易再遇),同概率档并入同档、低费先卖,
    # 星级高者后卖。
    prob = refresh_prob(ctx.level, _unit_cost(unit))
    return (10, prob, -_unit_cost(unit), -unit_star,
            refund_loss, in_hand, tail)


def sell_order_with_keys(
        units: list[HeldUnit | ShopUnit],
        ctx: PriorityContext) -> list[tuple[HeldUnit | ShopUnit, PriorityKey]]:
    """统一让位序列带排序键(观测面载体;排序实现与 :func:`sell_order`
    同一份——键 = :func:`sort_key` 输出逐位同源,禁消费位自算第二份)。

    返回按键升序的 ``(单位, 排序键)`` 列表(末位 = 最先让路)。观测
    消费位(档位分布/随机尾键命中)从键分量直读:档位 = 键首分量,
    尾键命中 = 池内存在另一件键去尾后与本件全同(等价牌群内部随机
    定序实际生效,32 号稿 §7 随机域)。
    """
    keyed = [(u, sort_key(u, ctx)) for u in units]
    keyed.sort(key=lambda p: p[1])
    return keyed


def sell_order(units: list[HeldUnit | ShopUnit],
               ctx: PriorityContext) -> list[HeldUnit | ShopUnit]:
    """统一让位序列(32 号稿 §8 消费侧约定)。

    返回从「最不该卖」到「最先让路」的升序序列(末位 = 最先让路);
    各触发消费位从末位向前取用(让路一张 / 取到凑够为止)。注意:
    逐牌调 :func:`sort_key` 会推进随机流,同 seed 下同输入同序、
    跨次调用不保证逐位复现(随机域 = 手持等价牌群内部,无行为语义
    损失,32 号稿 §7)。"""
    return [u for u, _k in sell_order_with_keys(units, ctx)]
