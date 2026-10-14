"""criteria/levelup——升级面判据(概率主轴 + 整级预授权)。

判据体系 = 迭代 2026-10-12-prep-shop-workflow-redesign 实现
(设计唯一源 = details/line_and_upgrade.md §2;触发五分支/支出形态/
拦截层处置逐节对齐):

- **触发五分支并集**(§2.1):arm0(need > level 机制分支)∨ 人口位(三元
  谓词)∨ 富余段-L3 ∨ 概率账(覆盖锁定后 ∧ plane2_started 双条件)∨
  停留门升级优先分支(同双条件——P1 硬规则锁定子局星级目标存在仍不覆盖,
  判据位排除 P1 冲级);
- **支出形态**(§2.2):判据通过 → 整级预授权(置键含授权批成本/
  授权血成本上界)→ 变现序列(每帧一卖至缺口闭合或候选穷尽)→
  执行帧发购买经验整批(实付上界 = 授权值,不再逐帧重闸)→ 清键
  ——「买一半」缺陷(逐帧单击 × 静态阈值逐帧重闸)的机制级修复;
- **拦截层**(§2.3 处置表):保留 = 保底金门(``guarantee_floor_gate``
  ——发出前全域最终硬检查)/ P21 血预算线(``level_spend_blocked``)/
  等级帽闸(``lv9_stop``/``xp_ledger_stop``);已停用 = 调度保利息门
  (arm2 结构保利息门——利息线纪律由 [17] 富余语义承载,行为等价)/
  P72(3a) 全段式量闸(其「整批推迟」与概率主轴攒钱语义合并,预留
  保护由整买预留约束承接)/ λ 顾问(生产态构造性零介入,撤槽 =
  工程清理)/ 血线地板解锁(濒死响应 = 修经济/阵容本身)。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


def lv9_stop(level: int, level_max: int) -> bool:
    """等级上限停(义务侧消费)。历史键名 'lv9_stop':cap=9 旧语义时代
    命名,现语义 =「等级达注册表 level_max 即拒发升级」——键串保留
    不改名(改键牵连判读脚本与历史档案可比性,纯改名无收益)。

    单一源 = 注册表 ``level_max``(kernel/cw_registry.py,实机真值 10,
    与 cw_economy.xp_apply_clicks「封顶 10」live 机制语义同源);sim 与
    live 同一规则核共享本单一源(原 ``sim_decision_registry`` 注入视图
    已停用)。⚠ 与同文件 ``cap_resolved``(利息
    上限)毫无数值或语义关联,禁接错源。

    ``level_max`` = 消费位传上下文注册表的 ``.level_max``(禁裸常数),
    **必填**:消费位(备战第 3 步/会话内升级检查两处)已全量接线,
    过渡缺省通道已拆除;禁新消费位依赖缺省。
    """
    return level >= level_max


def xp_ledger_stop(xp_progress: tuple[int, int] | None,
                   level_max: int) -> bool:
    """XP 期望账本升级停判据(lv9_stop 的轮内盲区补位,与 lv9_stop
    同位合取消费;语义锚 = 推进算子单一源 ``kernel/cw_economy.
    xp_apply_clicks``)。

    为什么需要(病灶实测):商店域逻辑态直写只写 xp 元组不写 level
    域(升档等观察覆盖,kernel/cw_action_report 上报函数族
    CwActionLevelUpShopParam 行);ALL IN 窗逐击决策环(decide_shop_screen 驱动器
    逐动作直写推进)内 level 域滞留轮初值 ⇒ lv9_stop 恒 False,而
    clicks_to_next_level 按推进后元组的新级 need 续算 ⇒ 同窗内连买
    下级(sim n100 s77000 段 44/100 局 R9 击数超整买上限,批计 ≥864 金,
    20260913 sim 找问题报告问题 1)。本判据改读「XP 期望账本」——

    判据式:元组不变量 = need 槽恒为 ``XP_TO_NEXT_LEVEL[账本真等级]``
    (xp_apply_clicks 写端写入,跨门槛推进后 need 槽换新级门槛;门槛表
    按级严格递增)⇒ ``need >= XP_TO_NEXT_LEVEL[level_max]`` ⟺ 账本真
    等级 ≥ level_max,即已到/越过升级目标,拒发。

    跨域同构:sim/live 消费同一函数,注入视图 level_max 同源 = 10
    (``kernel/cw_economy.py::MAX_PLAYER_LEVEL`` 单一尺,sim 重做反转后
    不存在第二把尺);门槛表键域 3-9 无表项 ⇒ 判据两域恒不覆盖,停止语义
    两域同由 lv9_stop 承载。

    ``xp_progress`` = 容器 ``gs.xp.value`` 原样透传(缺读 None 不覆盖,
    与 clicks_to_next_level 的缺省兜底方向一致——停判据缺读宁可放行
    交 lv9_stop/量闸管辖,不制造静默拒)。单一源 = kernel
    ``cw_economy.XP_TO_NEXT_LEVEL``,禁第二份表。
    """
    if not xp_progress or len(xp_progress) < 2:
        return False
    from sr_od.application.currency_war.kernel.cw_economy import (
        XP_TO_NEXT_LEVEL,
    )
    threshold = XP_TO_NEXT_LEVEL.get(int(level_max))
    if threshold is None:
        return False   # level_max 无门槛表项(live=10):判据不覆盖
    return int(xp_progress[1]) >= threshold


def spend_unified(clicks_to_next: int, gold: int, click_cost: int) -> bool:
    """P48 整买纪律(D-BUYNOTE):整批 XP 放行判据。

    仅当「一次买齐到下一级」的金够付时放行(clicks×click_cost ≤ gold)
    ——散买 XP(买不够升级)零收益,拦截(line_and_upgrade §2.2 裸金
    足支的判据位;P72(1) 整买形态 = Leontief 互补的实现载体)。
    """
    if clicks_to_next <= 0:
        return False
    return gold >= clicks_to_next * click_cost


def _plane_round_of(state: GameState) -> tuple[int, int]:
    """(plane, round_num) 容器读(读口单一源,prep 链容器化段 2 起
    gs 单形态)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        plane_of,
        round_num_of,
    )
    return plane_of(state), round_num_of(state)


def _max_units_of(state: GameState) -> int:
    """可上阵数容器读(读口单一源 max_units_of)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        max_units_of,
    )
    return max_units_of(state)


# ============================================================ 最优概率带(§2.1 停留门)


def prob_band_of_cost(cost: int) -> tuple[int, int]:
    """费用档 → 最优概率带 (下界,上界)(line_and_upgrade §2.1 停留门)。

    带 = **搜索域 1..9 内** REFRESH_PROB 概率峰值的等级区间,平顶整段
    取全部峰值等级(1 费带 [1,3] 类)——成员由 REFRESH_PROB 直接计算。
    禁写成「全域最高值区间 ∩ ≤9」:4/5 费全域峰在 lv10(0.40/0.25),
    截掉得空集;域内峰口径下 4/5 费带 = [9,9](lv9 的 0.30/0.10)。

    lv10 出域依据:P35 已证停手窗 lv9→10 恒负 + ``peak_refresh_level``
    在产表即此口径(1..9 域内取峰,cw_plane_table);带成员与该表的
    关系 = 带上界取 max(带)(单点峰形态,并列取高档),peak_refresh_
    level 作域上限校验,非带定义本体(line_and_upgrade §2.1 带成员
    规则与在产载体关系申报)。
    """
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    c = min(5, max(1, int(cost)))
    probs = [refresh_prob(lv, c) for lv in range(1, 10)]
    peak = max(probs)
    return probs.index(peak) + 1, 9 - probs[::-1].index(peak)


def _held_max_star(state: GameState, name: str) -> int:
    """同名持有最高星(bench ∪ 场上全场域;未持有 = 0)。

    星级目标完成判定 = 持有最高星 ≥ 必要星级(need_star 以「追到底」
    语义登记,合成路径的中间拷贝由最高星天然承载,line_and_upgrade
    §1.5)。"""
    best = 0
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
        deployed_rows_of,
    )
    front, back = deployed_rows_of(state)
    for u in (*bench_units_of(state), *front, *back):
        if u is not None and (u.char_id or '') == name:
            best = max(best, int(u.star or 1))
    return best


def _held_copies_folded(state: GameState, name: str) -> int:
    """同名持有基础副本折算数(3 合 1:star s → 3^(s-1);bench ∪ 场上)。

    期望刷次的 owned 修正输入(与 kernel ``_owned_core_copies`` 同式;
    该函数为目标核心私有,本处为任意缺件名的一般化读法)。"""
    n = 0
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
        deployed_rows_of,
    )
    front, back = deployed_rows_of(state)
    for u in (*bench_units_of(state), *front, *back):
        if u is not None and (u.char_id or '') == name:
            n += 3 ** (int(u.star or 1) - 1)
    return n


def unfinished_star_targets(state: GameState) -> list[tuple[str, int, int]]:
    """未完成星级目标集(line_and_upgrade §1.5/§2.1;锁定线 need_star
    驱动)。

    锁定线 need_star 表中持有最高星 < 必要星级的成员,返回
    (角色名,必要星级,当前实费档)。定义 3★ 就追到底无降档、定义
    2★ 即完成(§1.5);辅助 1★ 持有即完成,未持有者入集(首张即目标)。
    费用档 = ``effective_cost`` 当前实费 resolved 口径(银狼系变费后
    实档,档漂移时带随之重取)。未锁定期 = 空集(停留门覆盖锁定后,
    line_and_upgrade §2.1)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    from sr_od.application.currency_war.kernel.cw_economy import (
        effective_cost,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
        line_members_view,
    )
    view = line_members_view(state)
    if not view.locked:
        return []
    comp = get_comp(view.comp_name) if view.comp_name else None
    if comp is None:
        return []
    out: list[tuple[str, int, int]] = []
    for name, need in (comp.need_star or {}).items():
        need_i = int(need)
        if _held_max_star(state, name) < need_i:
            out.append((name, need_i, effective_cost(state, name)))
    return out


def stay_target_of(state: GameState) -> tuple[str, int, int] | None:
    """当前停留目标 = 未完成星级目标中费用档最低者(shop_session §2.4
    多目标停留顺序:先低费后高费,与搜牌等级节奏一致;并列取注册表
    名序,确定性)。"""
    targets = unfinished_star_targets(state)
    if not targets:
        return None
    return min(targets, key=lambda t: (t[2], t[0]))


def _locked_and_plane2(state: GameState,
                       session: StrategySession) -> bool:
    """概率账/停留门分支的共同适用范围门:锁定后 ∧ plane2_started 双条件。

    P1 硬规则锁定子局星级目标存在仍不覆盖(P1 不冲级)——概率账收益
    = P2 起未来刷新期望改善,P1 视界内不消费;P1 经验论证在案(到
    7 级为 P2 人口目标,P1 冲级与「P1 恒不刷」及经验账冲突,
    line_and_upgrade §2.1)。窗口谓词形态 = ``plane2_started_of``
    (3.1 交付,宪法第 2 条合规)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
        line_members_view,
        plane2_started_of,
    )
    return line_members_view(state).locked and plane2_started_of(state)


def stay_gate_upgrade_first(state: GameState,
                            session: StrategySession) -> bool:
    """停留门升级优先分支(line_and_upgrade §2.1 停留门的主动面)。

    当前停留目标未完成 ∧ 其最优概率带下界 > 当前等级 → 升级触发
    (升到带内去刷,[3]「目标费用在更高等级概率更大 → 升级」)。三支
    分派互斥完备:①带下界 > 等级 = 本分支真(升级优先);②等级 ∈ 带 /
    ③等级 > 带上界(被推过,单调不可降,当前即剩余可达最优)= 本分支
    假(停留刷新,延迟升级——刷新判据归 shop_session §2.4)。
    """
    if not _locked_and_plane2(state, session):
        return False
    target = stay_target_of(state)
    if target is None:
        return False
    lo, _hi = prob_band_of_cost(target[2])
    from sr_od.application.currency_war.kernel.cw_game_state import (
        level_of,
    )
    return lo > level_of(state)


#: 概率账缺件集聚合口径的 provisional 槽名(line_and_upgrade §2.1/§4
#: 两处同口径声明):缺件集多成员的期望改善聚合,现行 = 单核代表
#: (在产保守形态——多成员同受升级受益帧 benefit 低估 → 检验偏严);
#: 求和/瓶颈口径为切换候选【拟·owner = 编排者、期限 = 一个对局周期】
#: ——未决前一律单核代表,禁混用。
LEVELUP_MISSING_SET_AGG_SLOT: str = 'LEVELUP_MISSING_SET_AGG'

#: 单核代表的槽位注入值语义(求和/瓶颈切换候选的登记面):None =
#: 'single_core'(单核代表);注入 'sum'/'bottleneck' = 切换聚合口径
#: ——本批只落单核代表消费,切换值的消费面随标定值注入批接续。
_AGG_SINGLE_CORE: str = 'single_core'


def _missing_aggregate_mode() -> str:
    """缺件集聚合口径现读(provisional 槽;None/未注入 = 单核代表)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
        provisional,
    )
    cv = provisional.get(LEVELUP_MISSING_SET_AGG_SLOT)
    return str(cv.value) if cv is not None else _AGG_SINGLE_CORE


def _expected_refreshes_for_target(level: int, cost: int, need: int,
                                   owned: int) -> float:
    """追星目标的期望刷次(完成档张数 k = 3^(need-1):1★=1/2★=3/3★=9;
    超几何 DP 单一源 = ``cw_shop_odds.expected_refreshes``,pool 参数
    与 ``expected_refreshes_for_card`` 同表——k 表按 need_star 展开是
    本口径的一般化,非第二份概率口径)。"""
    from sr_od.application.currency_war.data.cw_shop_odds import (
        DISTINCT_CARDS_PER_COST,
        POOL_COPIES_PER_CARD,
        expected_refreshes,
        refresh_prob,
    )
    c = min(5, max(1, int(cost)))
    k = 3 ** (int(need) - 1)
    return expected_refreshes(
        refresh_prob(level, c),
        DISTINCT_CARDS_PER_COST.get(c, 13),
        POOL_COPIES_PER_CARD.get(c, 9),
        0, k, owned)


def prob_account_ok(state: GameState,
                    session: StrategySession) -> bool:
    """概率账(line_and_upgrade §2.1 主判据;覆盖锁定后 ∧ plane2_started
    双条件,载体 = 锁定线缺件集)。

    判据式:升一级后「找到缺件的期望刷次下降量」折算的金价值
    (期望刷次下降量 × 单次刷价 c_eff 画面实读)> 升级整级成本 +
    期间息损 → 该升。期间息损 = P47 双轨迹递推 L 项(``loss_exact``,
    输入面 = 金/收入日程/剩余视界,与刷新账同源)。

    缺件集聚合口径 = 单核代表【拟】(provisional 槽
    :data:`LEVELUP_MISSING_SET_AGG_SLOT`,None = 单核;求和/瓶颈为
    切换候选):代表 = 缺件集中费用档最低者(与停留目标同序——概率
    账评估的「找到缺件的期望改善」以同一目标为锚,查表确定式零拟合)。
    量化地基 = ``expected_refreshes``(P40 超几何 DP)+ REFRESH_PROB +
    门槛表(``XP_TO_NEXT_LEVEL``)+ 买经验单价(画面实读)。
    """
    if not _locked_and_plane2(state, session):
        return False
    targets = unfinished_star_targets(state)
    if not targets:
        return False
    if _missing_aggregate_mode() != _AGG_SINGLE_CORE:
        # 切换口径未落消费面:fail-closed 回单核代表(禁未决口径混用,
        # line_and_upgrade §2.1「未决前一律单核代表」)。
        pass
    name, need, cost = min(targets, key=lambda t: (t[2], t[0]))
    owned = _held_copies_folded(state, name)
    from sr_od.application.currency_war.kernel.cw_economy import (
        cap_resolved_of_session,
        clicks_to_next_level,
        level_of,
        loss_exact,
        net_income,
        refresh_cost_effective,
        xp_click_cost,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        gold_of,
        plane_of,
        round_num_of,
    )
    level = level_of(state)
    e_l = _expected_refreshes_for_target(level, cost, need, owned)
    e_l1 = _expected_refreshes_for_target(level + 1, cost, need, owned)
    # 升级后反不可追(e_l1==0 且 e_l>0)⇒ False。前提:现行 REFRESH_PROB
    # 满足「一旦出牌永不消失」单调性,该形态现表下不可达;池突变换表
    # 失去该单调性时守卫生效,防「升级后 E 归零」被误读成无穷收益。
    if e_l1 == 0.0 and e_l > 0.0:
        return False
    if not (math.isfinite(e_l) and math.isfinite(e_l1)):
        return e_l <= 0.0 < e_l1   # 当前级不可追而上级可追:纯解锁收益
    benefit = refresh_cost_effective(gs=state) * (e_l - e_l1)
    if benefit <= 0:
        return False               # 概率不升反降(内峰回落档):无收益面
    u_gold = clicks_to_next_level(state) * xp_click_cost(state)
    if u_gold <= 0:
        return True                # 满级/零费边界:成本侧空,收益即过
    # R_剩余就地自算(裁决点 9:框架不供视界量,场字段求和,封顶
    # modeled planes;与 cw_intention._p1_pair_overwindow 同式互锚)。
    from sr_od.application.currency_war.kernel.cw_node_schedule import (
        PLANE_NODE_TABLES,
    )
    _tb = state.node_seq_by_plane.value or PLANE_NODE_TABLES
    rounds = (sum(len(t) for k, t in _tb.items() if k >= plane_of(state))
              - round_num_of(state) + 1) if plane_of(state) in _tb else 0
    ibar = net_income(round_num_of(state), 0)
    c_int = loss_exact(gold_of(state), u_gold, rounds, ibar,
                       cap=cap_resolved_of_session(session))
    return benefit > u_gold + c_int


# ============================================================ 五分支触发(§2.1 触发源并集)

#: 五分支触发键(发出 auth_basis 记录值域;line_and_upgrade §2.1 触发源
#: 并集)。优先序 = 人口位 > arm0 > 富余段 > 停留门 > 概率账(战力当轮
#: 兑现的义务分支在前,优化路径在后;人口位/arm0/富余段为义务/机制分支,
#: 不受攒息约束——[12]/[33] 明文例外)。
ARM_POPULATION: str = 'pop_slot'
ARM_ARM0: str = 'arm0'
ARM_MUST_SPEND: str = 'must_spend'
ARM_STAY_GATE: str = 'stay_gate'
ARM_PROB_ACCOUNT: str = 'prob_account'


def upgrade_trigger(gs: GameState, session: StrategySession,
                    registry: DecisionV2Registry | None = None,
                    ) -> tuple[bool, str]:
    """升级触发五分支并集(line_and_upgrade §2.1 触发源并集;主入口)。

    五分支(∨ 语义完整承继 20 号稿三源 + 概率账 + 停留门):
    ① 人口位(三元谓词:板满 ∧ 阵营相关等待件不限星级 ∧ 上场边际
       贡献 > 0——由板满+共享羁绊结构承载,w>0 板面谓词,P39 分支一);
    ② arm0(need > level 机制分支,等级落后于上阵人数需求;14 号稿
       §4.2 现量版);
    ③ 富余段-L3(g > 10×cap_resolved 富余金零息,「金这么多都是要
       花的」,20 号稿 L3 出口);
    ④ 停留门升级优先分支(覆盖锁定后 ∧ plane2_started);
    ⑤ 概率账(主判据,覆盖锁定后 ∧ plane2_started)。

    奖励帧抑制覆盖升级触发(reward_node_suppressed 闸,消费位 = 本函数
    调用方前置;P80 待裁决,登记为待办)。返回 (是否触发,分支键——多分支同帧
    命中按 :data:`ARM_POPULATION` 等五键声明的优先序取首,auth_basis
    记录用)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        in_must_spend_zone,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_entries_of,
        bench_units_of,
        deployed_rows_of,
        gold_of,
        level_of,
        max_units_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
        predicates,
    )
    bench_units = list(bench_units_of(gs))
    front, back = deployed_rows_of(gs)
    deployed = [d for d in (*front, *back) if d is not None]
    cap = max_units_of(gs)
    bench_names = [str(u.char_id or '') for u in bench_units
                   if u is not None]
    deployed_names = [str(u.char_id or '') for u in deployed]
    # ① 人口位(P39 分支一三元;deploy_cap 真值链 = 当前可上阵数)。
    if cap is not None and predicates.arm1_existence(
            len(deployed), bench_names, deployed_names, cap):
        return True, ARM_POPULATION
    # ② arm0(need > level)。k_members 解析:锁定态 = 锁定线名单;
    # 未锁定期 target_comp = None(锁定线槽空)⇒ 成员集恒空 ⇒ arm0
    # 名义在列、实际仅锁定后可触发(review-37 R3:设计 §2.1 将 arm0
    # 列为未锁定期触发之一,实现适用范围 = 锁定后——未锁定期无星级目标
    # 语义承载〔旧配方伪 comp need_star 基本为空,行为差近零〕,
    # 张力申报随正本更新批;bench 输入 = 占席条目域〔arm0_need
    # 解包口径〕)。
    from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
        line_members_view,
    )
    view = line_members_view(gs)
    k_members = view.members if view.locked else ()
    arm0, _key = predicates.arm0_level_lag(
        level_of(gs), gs.level.value is not None,
        deployed, list(bench_entries_of(gs)), k_members, cap)
    if arm0:
        return True, ARM_ARM0
    # ③ 富余段-L3(域内帧判定单一源 in_must_spend_zone;20 号稿三源
    # ∨ 合并语义完整承继)。
    if in_must_spend_zone(gold_of(gs), session):
        return True, ARM_MUST_SPEND
    # ④ 停留门升级优先分支 / ⑤ 概率账(双条件适用范围内)。
    if stay_gate_upgrade_first(gs, session):
        return True, ARM_STAY_GATE
    if prob_account_ok(gs, session):
        return True, ARM_PROB_ACCOUNT
    return False, ''


# ============================================================ 保底金门(P72(3a) 内保留件)


def _plane_last_battle(gs: GameState,
                       session: StrategySession) -> bool:
    """位面末最后一战判定(cw4 消费面;单一源 =
    decision_v2.discipline.plane_last_battle 的重导出委托,禁第二实现;
    模块私有——非判据面函数,不入契约/旁路枚举表)。kernel 侧波 2 已切
    容器签名,容器 gs 直读。"""
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        plane_last_battle as _plb,
    )
    return _plb(gs, session)


def terminal_all_in(gs: GameState, session: StrategySession) -> bool:
    """终局域末战 ALL IN 判定(位面末战 ∧ R_全局 ≤ 1)。

    单一源供两处消费::func:`guarantee_floor_gate` 明确不在设计范围内半支与优化分支
    (概率账/停留门)的利息线差额保留豁免(末位面末战后金无任何消费
    场景,P41 终局清仓恒优/P23 死亡域攥金价值恒零——ALL IN 维持花光
    原语义,P72/P83 收窄口径)。``r_remaining`` 门面场字段自算查表
    (R 含当前节点,决策帧最小值 = 末位面末战的 1;禁自推位面数——
    宪法 01 §8-1 位面参数化不变量)。
    """
    if not _plane_last_battle(gs, session):
        return False
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.horizon import (
        r_remaining,
    )
    return r_remaining(session, *_plane_round_of(gs)) <= 1


def guarantee_floor_gate(gs: GameState, session: StrategySession,
                         gold: int, clicks: int, click_cost: int,
                         cap_resolved: int) -> bool:
    """保底金门(line_and_upgrade §2.3 P72(3a) 内保底金门行——单一
    裁决消两读):升级整批发出前的**全域最终硬检查**,真 = 放行。

    检查式:预估花后金 ≥ 1 利息档(下界值单一源 =
    ``DEFAULT_REGISTRY.boss_floor`` = 10)。概率账不覆盖「升了不许
    花穿」,正交(P72 已证命题的保底下界)。调用方传「预估花后金」
    形态时 clicks/click_cost 传 0/1(gold 直比;攒批口径下的保守下界
    = 裸金 + 活期退金 − 批成本)。

    明确不在设计范围内两支(任一真 = 不设下界,让位语义各有已登记出处):
    - **终局域**::func:`terminal_all_in` 单一源(ALL IN 维持花光原
      语义);
    - **买断制**:cap_resolved = 0 ⇒ 息账整体消解(p47 A1),下界
      失去推导基座,金出口归一般判据。

    下界值推导链:域③「非末位面持金未来效用 > 0/利息档纪律覆盖」
    (math_proofs P83)⇒ 下界落利息档结构 ⇒ g ≥ 10 是「下一向位面首息
    存在」的机制判等式(interest 的 10 = 利息档宽 = 斜率倒数,g<10 首息
    恒 0)⇒「保一档不多保」= 最小绑定支配论证。同值异据约束 =
    **现存半侧**(P48②):彼据(release 泄息通道 P1 出口金生存边际)
    消费位已随自驱动引擎停用、彼据侧修订重推义务灭失——boss_floor
    修订的单侧重推约束照旧(此侧为息通道非退化判等式,断言只锁同值
    不锁同据)。
    """
    if terminal_all_in(gs, session):
        return True          # 终局域:末位面末战,域③前提失效
    if cap_resolved == 0:
        return True          # 买断制:息账消解,下界无推导基座
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    return gold - clicks * click_cost >= DEFAULT_REGISTRY.boss_floor


# (原 P72(3a) 全段式量闸 ``levelup_budget_gate`` 单体拆解:量闸本体
# 删除——其「整批推迟」与概率主轴攒钱语义合并,预留保护由整买预留
# 约束承接;保底金门保留为 :func:`guarantee_floor_gate` 发出前检查位;
# 支A 兑现链谓词随量闸消亡(其「量闸否决存在性」的消解对象不存在了)。
# 处置依据 = line_and_upgrade §2.3 处置表 P72(3a) 行。)


def level_spend_blocked(gs: GameState, session: StrategySession,
                        registry: DecisionV2Registry | None = None) -> bool:
    """P21 血预算线(危机带内整批经验授权让位保命面;line_and_upgrade
    §2.3 保留件——P21 已证:hp ≤ 停升级线内升级收益到账 ≥1 战之后,
    EV 严格为负)。动作发出点(备战第 3 步/会话内升级检查)消费;富余段
    域内让位照 20 号稿(调用方判域)。

    ``registry`` = 上下文注册表(停付线字段 vd_p2_loss 族的单一源口径);
    ``None`` 回读缺省表 = 直调兼容约定,禁新消费位依赖缺省。

    两支,全部单一源判据,零新自由参数:
    - ``discipline.blood_budget_levelup_blocked``(P21 停升级线);
    - P2 危机带 ``discipline.p2_crisis_band``(hp ≤ ceil(2×vd_p2_loss)
      ≈41 = P21 d=2「到账更慢」档)。
    ALL IN 豁免(位面末 boss 战花光,[18])两支共享——末战花光是
    时机判断非血线判断。hp 不可信帧 fail-closed 拒付(危机会在内)。

    血线地板解锁让位支(死亡线帧停付让位)已停用
    (line_and_upgrade §2.3 血线地板解锁行;正典依据 user_playstyle
    [39]「HP 不作决策依据」——濒死响应 = 修经济/阵容本身,[18] 报警
    语义)。
    """
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        blood_budget_levelup_blocked,
        p2_crisis_band,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    if blood_budget_levelup_blocked(gs, session, reg):
        return True
    if _plane_last_battle(gs, session):
        return False    # ALL IN 窗:停手让位(与血预算支同一豁免序)
    return p2_crisis_band(gs, session, reg)


def batch_form(level: int, target_level: int) -> bool:
    """批量成型判据(目标级差>0 才有批;义务侧消费)。"""
    return level < target_level


def pop_slot(deployed_count: int, deploy_cap: int, gold: int,
             bench_candidates: int, floor_gold: int, *,
             buyable_candidate: bool = False, bench_free: int = 0,
             ) -> tuple[bool, str]:
    """D-lv7(OPEN 检查点):「满编+富金+bench 有候补 → 升 cap 上人」覆盖。

    返回 (是否发出升 cap 意图,决策迹理由——不触发时显式理由,
    R189-5 D-lv7 行:「判据合法不触发须显式理由进决策迹」)。

    前置放宽(14号稿 §4.3,零参数):「bench_candidates > 0」改为
    「bench 有候选 ∨ 买入面有可即时买入的线内候选(affordable ∧
    bench_free ≥ 1)」——从「已持有候补」放宽到「买得起候补」。
    """
    if deployed_count < deploy_cap:
        return False, 'not_full'          # 未满编:普通 M1 部署覆盖
    has_candidate = bench_candidates > 0 or (buyable_candidate
                                             and bench_free >= 1)
    if not has_candidate:
        return False, 'no_bench_candidate'
    if gold < floor_gold:
        return False, 'gold_below_floor'
    return True, 'full_rich_with_candidate'
