"""cw4 商店会话循环 decide_shop_action(shop_session §1-§5;迭代
2026-10-12-prep-shop-workflow-redesign 会话重写)。

**会话模型**(shop_session §1):一次会话 = 开店动作到关店动作之间的
全部商店域决策;跨刷新重进(op 级)延续同一会话;会话终结 = 输出关店
动作。入口三条路径(契约 A):① 备战第 5 步开店;② 游戏侧自动开店;
③ 金位读数开商店(读数形态,非处理性会话不置标记)。入口统一行为 =
本决策函数首查 visit 内务与 ``shop_handled`` 标记(已处理 → 立即关店;
受限访问帧豁免)。

**店内动作边界**(用户裁定 2026-10-12 + 能力面):店内可做 = 买牌/
卖备战席/刷新;店内不做 = 卖场上角色、点消耗品、拖角色上阵
(部署统一店外)、购买经验(用户裁定 2026-10-17:商店画面不买经验,
升级在备战画面做——前置升级检查收窄为升级意图出口,命中且可发射即
关店转场,design §2.1)。卖备战席在店内发出(执行链 = 3.5 端口接线
批交付);2026-09-14 收缩裁定废止(判例 screens-actions-capability §5
的「卖备战/买经验收缩至备战期」已直删,用户裁定 2026-10-13)。

**单动作循环与零读屏规范不变**:刷新维持「访问终结」(op 结束 → 外
循环重识别 → 商店 op 重新入口观察;刷新导致的 op 重进仍是同一会话)。

本模块是 mandate_v1 商店线的决策本体,唯一输入 = 容器单例
``game_state_of(session)``(GameState;写者 = 商店入口观察段/动作上报
逻辑态直写;live 与 sim 同一决策本体同链消费,零第二输入面)。

rng 中立:本模块零 rng 消费(会话流派生契约)。

计数键(state_of(session).cw4_counters;键登记单一源 = 各键写点注释):
会话循环键族 = shop_visit_restricted_frame / shop_close_read_noop /
acquire_swap_*(席满买入六步流程:_sell/_declined/_merge_free_buy/
stale_idx)/ session_funding_sell(_fallback_sell/
leg_reject/exhausted)/ scene_plugin_buy_hit(_no_seat/budget_exhausted)/
core_c1_make_room_sell/core_locked_c1_make_room_sell /
shop_refresh_*(三段式判据拒因族)/ levelup_*(会话升级意图门族:资格
门拒因 + levelup_transition_close 转场关店;键语义与写点注释见各分支
段);
承继键族(m2/m2_stockpile/m2b/protection_hoard/dead_gold_press/press_buy_
deployable/m6/fuel_filler_stall/ev/core/dominance/p90/p91/p94)随各分支
并入保留,键语义与写点注释见各分支段(原 transition 族随 ④ 转投分支
退役删除,统一保护集 design §2.2;protection_hoard 三键 = 其语义承接)。P86 三分支旧键族(shop_no_target_*/
hub_option_*)随并入停用(对照表 = 迭代目录 P86 并入对照)。

M2 停摆续段缓存:商店域 cw4_m2_stall_latch 族已停用;席满
表达 = 席满买入六步流程(3.2 置换账替换),不再有「无候选输入不变续段」的
重复帧面。
"""
from __future__ import annotations

import contextlib
import math
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS, get_char
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.data.cw_shop_odds import (
    expected_refreshes_for_card,
    reencounter_window_frames,
    refresh_prob,
)
from sr_od.application.currency_war.kernel import cw_intention
from sr_od.application.currency_war.kernel.cw_board_by_row import board_by_row
from sr_od.application.currency_war.kernel.cw_comps import (
    CORE_SINGLE_CARD_REGISTRY,
    get_comp,
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    deploy_target_sets,
    deployed_bond_counts,
    record_fresh_buy,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    bench_char_cost,
    card_cost,
    effective_cost,
    effective_refresh_prob,
    in_must_spend_zone,
    interest,
    refresh_cost_effective,
    sell_refund,
)
from sr_od.application.currency_war.kernel.cw_exec_state import BENCH_CAPACITY
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    GameState,
    Unit,
    bench_entries_of,
    deployed_rows_of,
    effective_node_pos,
    gold_of,
    level_of,
    max_units_of,
    plane_of,
    round_num_of,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    merge_material_stale_names,
    same_star_count,
    star_base_copies,
)
from sr_od.application.currency_war.kernel.cw_reward_node import (
    reward_node_suppressed,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionBuyCardParam,
    CwActionCloseShopParam,
    CwActionDeployMoveParam,
    CwActionRefreshShopParam,
    CwActionSellBenchParam,
    CwActionSellDeployedParam,
    ShopCard,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    entry,
    mandate,
    proof,
    sell_gate,
    session_scope,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
    provisional,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    buy as crit_buy,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import contracts
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    refresh as crit_refresh,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    shop_session as shop_sess,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    stockpile as crit_stockpile,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.sell_candidates import (
    evaluate_sell_candidates,
    sell_line_membership,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
    can_deploy_single,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# 贯穿件恒囤名单单一源已迁 protection(design §2.1 单一源搬家),此处
# 回导维持本模块既有消费点与外部 ``shop.CROSS_LINE_KEEP_NAMES`` 读面;
# 保护集成员判定自同一模块单一取源(design §2.2 买面接线)。
from sr_od.application.currency_war.strategies.impl.mandate_v1.protection import (
    CROSS_LINE_KEEP_NAMES,
    protection_membership,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
    horizon,
    predicates,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.income import (
    net_income,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
    saturation_line,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    refund_full_star_ok,
)


def _deployed_units_of(gs: GameState) -> list[Unit]:
    """上场单位域紧缩序(行域 front_row+back_row,前排在前;本模块单一读点)。"""
    front, back = deployed_rows_of(gs)
    return [d for d in (*front, *back) if d is not None]

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import (
        Comp,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        GameState,
        Unit,
    )
    from sr_od.application.currency_war.kernel.cw_vocab import Action
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

# ===== 商店截断语义(迁移批)=====
# CwActionRefreshShopParam 即终结,CwActionCloseShopParam 恒可用;名-槽一致性复检 = 执行侧
# proposal-vs-expected 守卫断言(cw_shop_action_ops;和解注)。

# ===== M2 停摆续段缓存停用 =====
# 商店域 M2_STALL_NONVARIANT_SHOP_ACTIONS 白名单、cw4_m2_stall_latch
# 续段缓存与其续段 token 消费随商店期腾席卖射一并停用:席满缺员形态
# 现表达 = 关店返回主循环(终结动作),不再有「无候选输入不变续段」的重复
# 帧面。备战域同构缓存(mandate.run_mandate M4)不受影响,续段 token
# (cw4_frame_action_record)由备战域继续消费。


def _shop_sell_refund(bc) -> int | None:
    """卖出预期回金(sell_refund 口径;注册表 cost 缺失 ⇒ None=未标)。

    入参 = bench 占席条目(容器 BenchSlot,身份经解包口取;占位件无
    现值 = None)或行域 Unit(P4 容器形)。"""
    u = mandate._slot_unit(bc) \
        if getattr(bc, 'kind', None) is not None else bc
    if u is None:
        return None
    ch = CHARACTERS.get(u.char_id or '')
    if ch is None or not ch.cost:
        return None
    return sell_refund(u.star, ch.cost)


# (R1 路径总账装配侧 _r1_ledger_terms 已随三段式刷新判据实现停用——
#  shop_session §2.4 判据替换申报:期望比较的连续判据 → 目标状态的
#  结构判据,消费面改由 criteria/refresh.refresh_warranted 查表承载;
#  P40/P47/P54 命题本体保留已登记。)


def _r2_card_reserve(gs: GameState) -> int:
    """R2 预算门卡价预留 ρ(单一源 = criteria/refresh.r2_card_reserve;
    本名保留使生产调用点零漂移,语义 = 停留目标实费档,未锁窗口恒 0
    ——docstring 见单一源本体)。"""
    return crit_refresh.r2_card_reserve(gs)


def _merge_pair_names(bench: list[BenchSlot],
                      deployed: list[Unit]) -> set[str]:
    """合成可触发名集(M2b 循环与判据目标可买合成腿两处共吃的单一源,
    禁第二实现):全局面(bench∪deployed)同名**同星**副本恰 2 张(任一
    星档计数 == 2)的角色名——机制全集口径。

    机制依据 = merge_mechanics.md §1/§2「同名同星凑满 3 即合成」+ §3
    恒成立约束「全场同名同星 ≤2」:任一星档第 3 张出现的瞬间即触发
    合成,故「买一张即合成」的持有形态全集 = 1★ 档计数 == 2(恰 2 张
    1★ / 场上 2★ + 备战 1★×2——买第 3 张 1★ 合成,与已持 2★ 无关,
    产物 2★ 向 3★ 推进)∨ 2★ 档计数 == 2(2★×2 + 直出 2★ 卡——买即
    合成 3★)。旧「恰 2 张全 1★」单跳口径只是其子集,旧 docstring 的
    误杀警示(买三张通道未实现)由本全集口径消除。3★ 档不收(星级目标
    追到底 = 3★,4★ 出机制文档域,收录会误放 3★ 档买入通道)。

    归一化/计数键逐字符同 ``decide_shop_action`` 内 ``_cnt``(同名同
    星副本计数):星级 ``(c.star or 1)``(None 视同 1★)、键
    ``(c.char_id or '')``、计数宇宙 bench∪deployed。资格维不在本
    谓词适用范围(调用方各自过滤):M2b 循环天然约束于 buy_members,
    且对 1★ 买入通道再验「该名 1★ 档计数 == 2」(只有 2★ 档凑满进度
    的名,买 1★ 不触发合成,禁混入 1★ 通道);合成腿消费 = 目标名 ∈
    本谓词名集——目标名构造性 ∈ 义务面,资格维对齐。
    """
    counts: dict[str, dict[int, int]] = {}
    for c in list(bench) + list(deployed):
        u = mandate._slot_unit(c) \
            if getattr(c, 'kind', None) is not None else c
        cid = (getattr(u, 'char_id', '') or '') if u is not None else ''
        star = int(getattr(u, 'star', 1) or 1) if u is not None else 1
        counts.setdefault(cid, {})
        counts[cid][star] = counts[cid].get(star, 0) + 1
    return {n for n, ss in counts.items()
            if ss.get(1, 0) == 2 or ss.get(2, 0) == 2}


def _frame_search_windows(session: StrategySession, gs: GameState,
                          registry, counters: dict) -> tuple[frozenset[int],
                                                            frozenset[int]]:
    """帧级搜索窗口(T1;设计 13_buy_face_design §2.3/§3.2)。

    窗口判据重锚(V̄ 链停用随批):旧 V̄ 门式
    (``vbar.window_vbar`` 帧级现算 + P57 双读法参数化)随 V̄ 比较项
    一并停用,窗口改为塌缩带锚——费档在窗内 ⟺ 该级命中率 ≥ ω×峰值级
    命中率(``statefn/odds.tier/card_search_window``,ω 锚与
    refresh_ev_budget 归零分支同源),全游戏定义量(REFRESH_PROB
    表 + 峰值查表 + 注册表 ω 字段)。空集语义 = 真无窗口帧(该级全部
    费档归零),非门控。P57 读法分歧随单一判据消解(文档面声明)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.odds import (
        card_search_window,
        tier_search_window,
    )
    level = level_of(gs)
    omega = registry.omega_collapse_ratio
    return (tier_search_window(level, omega),
            card_search_window(level, omega))


def _refresh_block_key(gs: GameState, gold: int, bench_used: int) -> tuple:
    """刷新负结果记忆比对键(W11;载体字段 = ``StrategyState.
    refresh_blocked``,读写单一消费位 = ``decide_shop_action`` 刷新提案
    段)。键 = (生效节点序位, 金, 席位快照, 星级目标键)四元组:

    - 节点序位 = ``effective_node_pos`` 现值(节点推进即键变——标记
      节点级生命周期经值比对承载,跨节点残留键失配即失效);
    - 金 = 会话金位读数现值(调用方传帧级 ``session_gold`` 投影);
    - 席位快照 = 备战席占席数(腾位/买入/合成即键变——席位变化使目标
      可买性可能翻转,记忆随之失效);
    - 星级目标键 = ``unfinished_star_targets`` 名-必要星级序元组(星级
      目标完成/集合变动即键变——判据输入面变化,记忆不得跨目标生效)。

    取值时机 = 置位帧与消费帧各现读一次(同帧同参;禁快照跨帧复用)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup as _lvl,
    )
    targets = tuple(sorted(
        (t[0], int(t[1])) for t in _lvl.unfinished_star_targets(gs)))
    return (effective_node_pos(gs), int(gold), int(bench_used), targets)


def shop_unbought_reasons(gs: GameState,
                          comp: Comp | None,
                          k_members: tuple[str, ...],
                          actions: list[Action],
                          hub_names: frozenset[str] = frozenset(),
                          protection: frozenset[str] | None = None,
                          ) -> dict[str, str]:
    """商店波未买牌拒因串(决策帧遥测字段 ``shop_rejects`` 的生产端)。

    为什么:复盘 g_20260904_031925 把在售 transition 件「花火」误读成
    线内核心件「火花」(花火≠火花:花火=2费盛会之星辅助,cw_chars 注册
    表 source=6401;火花=4费星间旅人、绯英欢愉 shared 成员,source=7001
)——当时决策帧只有 fp 值、无任何 per-card 分类,判读者只能猜「哪道
    门拒了」。本函数对店面每张未买牌给一个归属/拒因标签,让「线内未买
    (哪道门拒)」与「线外归属(刻意不买)」在决策帧内可辨:

    - 义务面缺口件(K 想买而未买;``k_members`` 实参 = 义务面,统一
      保护集 design §2.3 D7 迁移——宽集实参下保护集成员全部落线内
      分支的现状消除):``missing_unaffordable``(金不足)/
      ``missing_bench_full``(席满且无可腾燃料件)/ ``missing_no_path``
      (金席俱足仍未发出 = 异常态:发出被截断丢弃等,须查);
    - 义务面已持有:``owned``;锁定后星级目标已满足成员(need_star 口径
      缺口 = 0,W5 追星改革)细分 ``star_goal_met``(显式停买拒因,
      同名副本零推进——优先于下方持有形态细分);
    - 保护集囤货面(非义务面成员;design §2.3 D7 迁移——退役的
      ``transition_component`` 策展键语义由本键取代,占其原键序位,
      交集卡〔囤货面 ∧ 某阵容 transition_chars,如花火〕可辨性承继):
      在售未买 = ``protection_member_rejected``(囤货臂精确门序以
      protection_hoard_* 计数键为准,本键 = 帧首归属标签),已持有 =
      中性 ``owned``;
    - transition_chars(打工后卖、刻意不入线——单一源 = cw_comps 注册表
      + ``predicates.line_members`` 只取 core∪shared;键保留,判定源
      与④/策展无代码耦合):``transition_char``——非保护打工件照旧落
      本键或 ``non_line`` 桶(可辨性申报,design §2.3);
    - 乙分支枢纽资格集(P86;入参 = kernel.no_target_arms().hub_names 直传,
      判据单一源在 kernel,本函数只挂标签):``hub_option``——空窗帧枢纽
      件从 non_line 改显式拒因(正本 §4.4 行 3 键序消费面重排;未发出
      = 金/席/息/素材门逐帧判,精确门序以 hub_option_* 计数键为准);
    - 其余:``non_line``。

    口径 = 帧首静态快照 + 逐动作累积投影:金按已发出 CwActionBuyCardParam 总价扣减、
    CwActionSellBenchParam/CwActionSellDeployedParam/CwActionDeployMoveParam 的席与回金同步投影(修复:旧版只投影
    金不投影席——M2 波内先买的成员占掉末席后,同波后续线内件被席闸跳过,
    会被误标成 missing_no_path 而非 missing_bench_full,复盘归因失真)。
    拒因串是判读线索,非审计账(精确门序以 shop_ev_*/m2_*/protection_
    hoard_* 各计数键为准)。
    阵容为 None(K 空窗回退带)时 transition 分类不可得,统一 ``non_line``。

    ``protection`` = 保护集成员名集(帧级现算注入;None = 函数内自解析
    ``protection_membership(gs, state_of(gs))``,生产调用点传帧级同一
    集合保持与买面口径同源)。

    语境声明:本函数的拒因语义(「金席俱足仍未发出
    =异常态」)以 cw4 M2 义务通道为参照系——M2 对义务面缺件是义务买入,
    唯一合法拦截集=金/席硬闸+发出截断。
    """
    # 容器单位域现读(P4 容器形):bench = 占席条目(BenchSlot),身份经
    # 解包口取;deployed = 行域单位紧缩序(本函数内多处同吃同一推导)。
    bench = bench_entries_of(gs)
    deployed = _deployed_units_of(gs)
    if protection is None:
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            state_of as _state_of,
        )
        protection = protection_membership(gs, _state_of(gs))
    owned = ({mandate._slot_cid(b) for b in bench}
             | {d.char_id or '' for d in deployed})
    gold = gold_of(gs)
    bench_free = BENCH_CAPACITY - len(bench)
    for a in actions:
        if isinstance(a, CwActionBuyCardParam):
            gold -= card_cost(a.card)
            bench_free -= 1
        elif isinstance(a, (CwActionSellBenchParam, CwActionSellDeployedParam)):
            # 卖出投影:席释放 + 回金(CwActionSellBenchParam.income 缺失按 0 保守——
            # 金低估只会把拒因推向 unaffordable 侧,不会造假 no_path)
            bench_free += 1
            income = getattr(a, 'income', None)
            if income:
                gold += income
        elif isinstance(a, CwActionDeployMoveParam):
            bench_free += 1     # bench→board:席释放(CwActionSwapDeployParam 一进一出净 0)
    trans = (set(getattr(comp, 'transition_chars', []) or [])
             if comp is not None else set())
    bought_names = {a.card.name or '' for a in actions
                    if isinstance(a, CwActionBuyCardParam)}
    out: dict[str, str] = {}
    for card in shop_payload_content_cards(gs.shop.value):
        name = card.name or ''
        if not name or name in out or name in bought_names:
            continue
        if name in k_members:
            if name in owned:
                # 线内已持有帧按持有形态细分拒因(与同帧实际动作一致):
                # - W5 达标显式停买(锁定后):星级目标已满足成员的同名
                #   副本零推进(缺口 = 0,买臂显式停买,序 1 缺件域/M2b/
                #   m2_stockpile 三处门同口径)——优先于持有形态细分,拒因
                #   = ``star_goal_met`` 可观测(旧口径落「四臂够不着,拒因
                #   混杂」的 owned 桶,追查件缺陷 4);
                # - 合并完成段(cnt=2 ∧ 无 2★):§3.6 满栏例外后买入直发
                #   (免 bench_free 门),'merge_bench_full' 键停用;金不足
                #   仍记 merge_unaffordable,金席俱足未发 = merge_ready
                #   (判读关注面);
                # - 分支①囤分支段(cnt1=1 ∧ 无 2★,§3.2):中性 'owned' 停用
                #   ——同帧实际动作 = m2_stockpile 义务买入,拒因按其门序
                #   细分(stockpile_bench_full/stockpile_unaffordable/
                #   stockpile_ready),§7.3 owned 命中占比观测面随之真实;
                # - 其余(含 cnt2>0 让渡死库存,§3.7):中性 'owned'。
                copies = []
                for c in bench:
                    u = mandate._slot_unit(c)
                    if u is not None and (u.char_id or '') == name:
                        copies.append(u)
                for d in deployed:
                    if (d.char_id or '') == name:
                        copies.append(d)
                _need = (getattr(comp, 'need_star', None) or {}).get(name) \
                    if comp is not None else None
                if _need is not None \
                        and session_scope.line_members_view(gs).locked \
                        and max(int(c.star or 1) for c in copies) >= _need:
                    out[name] = 'star_goal_met'
                    continue
                cnt1 = sum(1 for c in copies if (c.star or 1) == 1)
                cnt2 = len(copies) - cnt1
                cost = min((card_cost(c))
                           for c in shop_payload_content_cards(gs.shop.value)
                           if (c.name or '') == name)
                if len(copies) == 2 and cnt2 == 0:
                    out[name] = ('merge_unaffordable' if gold < cost
                                 else 'merge_ready')
                elif cnt1 == 1 and cnt2 == 0:
                    if bench_free <= 0:
                        out[name] = 'stockpile_bench_full'
                    elif gold < cost:
                        out[name] = 'stockpile_unaffordable'
                    else:
                        out[name] = 'stockpile_ready'
                else:
                    out[name] = 'owned'
                continue
            cost = min((card_cost(c)) for c in shop_payload_content_cards(gs.shop.value)
                       if (c.name or '') == name)
            if bench_free <= 0:
                out[name] = 'missing_bench_full'
            elif gold < cost:
                out[name] = 'missing_unaffordable'
            else:
                out[name] = 'missing_no_path'
        elif name in hub_names:
            # P86 乙分支拒因键(枢纽资格件在售未买帧与真 non_line 可辨)。
            # 键序 = 先于 保护/trans 分支(P86 正本 §4.4 行 3「键序消费面
            # 重排」;判据单一源 = kernel.hub_option_names,本函数只挂
            # 标签)。
            out[name] = 'hub_option'
        elif name in protection:
            # 保护集囤货面拒因键(design §2.3 D7 迁移:取代退役的
            # transition_component 策展键,占其原键序位——囤货面成员
            # 先于 trans 分支,交集卡可辨性承继)。已持有 = 中性 owned
            # (同名第二张走 M6/序 5 判据,非「被拒」);在售未买帧 = 席/
            # 金/星级硬闸拒的归属标签,帧首快照无门序投影,精确门序以
            # protection_hoard_* 计数键为准。
            out[name] = 'owned' if name in owned \
                else 'protection_member_rejected'
        elif name in trans:
            out[name] = 'transition_char'
        else:
            # C1 拒因拆键(设计《直通核心卡信号层入口》§4 意向状态机行):
            # registry 核心卡在售未买帧与真 non_line 可辨——sim 检查器归
            # 机会错失类,实现批带方向声明(严格向:核心件在售帧被拒判红)。
            # 规则③后语义收窄:未锁定帧在售核心卡正常帧
            # 已由恒买放行分支买入,本键残留 = 席/金硬闸拒的 fallback 标签。
            out[name] = ('core_candidate_rejected'
                         if name in CORE_SINGLE_CARD_REGISTRY else 'non_line')
    return out


def count_material_stale(counters: dict, session: StrategySession,
                         bench: list[BenchSlot],
                         deployed: list[Unit],
                         round_num: int) -> None:
    """滞留素材暴露分键(滞留暴露的待修问题 G-B1 第四级;官方键,
    旧「重复对在场行数」代理口径已停用)。

    分键两把:
    - ``merge_material_stale``:素材对(同名同 1★ ≥2,判定单一源 =
      ``cw_state.merge_material_stale_names``)在场的决策帧计数,
      粒度 = 名×帧(与 cw4_counters 家族逐帧口径一致);
    - ``merge_material_stale_ge2``:跨轮仍滞留(上一见帧轮次 < 本轮)
      的名×帧计数 = 「N 轮未合成」的轮级暴露——合成后键停止增长
      (轮差分归零),滞留时长由判读端按键差分读,本函数不做时长判定。

    适用范围 = 商店决策帧(由 ``decide_shop_action`` 逐帧调用;备战帧不计,
    与家族同域)。跨轮记忆载体 = ``session.cw4_stale_seen_rounds``
    (名 → 上一见帧轮次;名离场即清,防拆对后再组被误计跨轮)。
    纯观测:只写 counters/session 记忆,零行为面。
    """
    _stale_names = merge_material_stale_names(bench, deployed)
    if _stale_names:
        counters['merge_material_stale'] = \
            counters.get('merge_material_stale', 0) + len(_stale_names)
    _seen = getattr(state_of(session), 'cw4_stale_seen_rounds', None)
    if _seen is None:
        _seen = {}
        state_of(session).cw4_stale_seen_rounds = _seen
    for _sn in _stale_names:
        _prev = _seen.get(_sn)
        if _prev is not None and _prev < round_num:
            counters['merge_material_stale_ge2'] = \
                counters.get('merge_material_stale_ge2', 0) + 1
    for _sn in [k for k in _seen if k not in _stale_names]:
        del _seen[_sn]
    for _sn in _stale_names:
        _seen[_sn] = round_num


# ===== 线账闭合孤儿证明载体 =====
# 单一源上移申报:簿键/读口/孤儿
# 证明集单一源 = sell_gate(_OBLIGATION_BOOK_KEY / obligation_book_of /
# line_switch_orphans_of)——L1 换线孤儿 carve-out 需要同源证明(第二
# 键 = 双源漂移面);本侧保留薄委托零断链(调用位/测试引用不变)。


def _obligation_book(session: StrategySession) -> dict:
    """义务类买入镜像簿读口(单一源 = sell_gate.obligation_book_of)。"""
    return sell_gate.obligation_book_of(session)


# (线账闭合孤儿证明集帧首读位随商店域卖射停用删除:该集唯一
#  消费 = CwActionSellBenchParam.reason 孤儿证明标记,读口单一源 =
#  sell_gate.line_switch_orphans_of,备战域卖出位按需直读。)


# ===== P77 缺口面装载(2★ 直出现货比较子 + s_reserve 拒绝对价)=====

def spot2_direct_out_card(cands: list[ShopCard], name: str, level: int,
                          c_eff: int) -> ShopCard | None:
    """j=1 帧的同名 2★ 直出现货比较子(P77 缺口面1)。

    账式(P77 §2.2 原式,零新自由参数):DIY 账 = 再收 2 张 1★
    (2×基价)+ 付费刷新账 c_eff·E(D|j=1,k=3)(E 单一源 =
    ``expected_refreshes_for_card``;溢价表 P77 §2.2:3费@L7=30.9 /
    2费@L6=30.4 / 4费@L8=57.2 / 5费@L9=80.7 金【推】,全档>0);现货账
    = 星级费用实付(card.cost,徽章 ×3 律,merge_mechanics §2.6)。
    现货账 ≤ DIY 账 ⇔ 发卡。
    - fail-closed 边界:p(level,基价)=0 帧 E=0 系函数约定(该级 DIY
      结构性不可达,非「零刷新成本」),比较子判不可评 → None(维持
      星过滤拒;P77 溢价表覆盖可行 DIY 域,域外延未证不入)。
    - 席/金交互不在本函数(比较子只裁「值不值」):买不买仍走分支内既有
      闸序(金闸前置 → M4 腾席,与 1★ 路径同序同闸,装载设计 §1.3;
      买入后 cnt2=1 分支触发自灭,二-1 守卫防重复)。
    - [A/B 切换面] 本函数 = 模块级槽位:基线分支经 monkeypatch 置恒 None
      关闭(fixtures/cw_ab.py;strategy-work §3「A/B 对照手段不进生产
      代码」)。j=2 帧归 M2b(P77 备注5:DIY 再买 1★ 严格占优,禁重开)。
    """
    char = CHARACTERS.get(name)
    if char is None or not char.cost:
        return None
    base = int(char.cost)
    cands2 = [c for c in cands if (c.star or 1) == 2]
    if not cands2:
        return None
    if refresh_prob(level, base) <= 0.0:
        return None
    diy = 2 * base + c_eff * expected_refreshes_for_card(
        level, base, target_star=2, owned=1)
    spot = cands2[0]
    return spot if (spot.cost or 3 * base) <= diy else None


#: s_reserve 拒帧再遇窗的不可达域入账上限(p=0 帧窗无界,以量级上限计入
#: 累计并申报「均值读数被稀释」;概率可行帧的窗 ≤ 10^3 量级,远不可达)。
_REMEET_WINDOW_CAP_FRAMES: int = 999_999


def _s_reserve_remeet_frames(level: int, bench, deployed,
                             card: ShopCard) -> int:
    """s_reserve 拒帧的对价侧(P77 缺口面3):被拒现货的再遇窗
    (自然帧,ceil)——「留保息 vs 收现货」权衡自此有量值载体。

    纯遥测累计,禁决策判据消费;让路裁决(下界是否/如何为现货让路)
    归 P56 设计批(P77 适用范围申报:本命题不裁决)。held 折算 = 全局面
    同名基础副本数(1★×1/2★×3/3★×9);窗式单一源 =
    ``reencounter_window_frames``(P77 §1.4「再遇窗 1/q(自然帧)」)。
    """
    name = card.name or ''
    char = CHARACTERS.get(name)
    base = int(char.cost) if char is not None and char.cost \
        else card_cost(card)
    held = 0
    for c in list(bench) + list(deployed):
        if c is None:
            continue
        u = mandate._slot_unit(c) \
            if getattr(c, 'kind', None) is not None else c
        if u is None or (u.char_id or '') != name:
            continue
        held += star_base_copies(u.star)
    win = reencounter_window_frames(level, base, held)
    if not math.isfinite(win):
        return _REMEET_WINDOW_CAP_FRAMES
    return int(math.ceil(win))


# ===== 结算线地板(discretionary 买分支的买后裸金下界)=====

def check_settlement_line(gold: int, cost: int, g_star: int) -> tuple[bool, str]:
    """结算线地板:买后裸金不出息律饱和线(gold − cost ≥ g*,g* 由
    调用方传 ``saturation_line(cap_resolved)`` 派生,禁字面 50——R70-1
    利息帽参数化链,买断制 g*=0 时被 check_affordable 蕴含即 no-op)。

    为什么需要(五件结构事实的合取,§背景):①资格门单边——
    dominance 分支原只查买前 gold > g* 与 check_affordable,是全部
    discretionary 买分支中唯一无买后线检查的分支;②单动作串行链——一次
    店访每帧买一张、金为期望态现值,串行消费下末笔可穿线;③P78-1 同
    visit 禁卖回(定义性抵消买入);④T3 同轮垫保——买入即入动作发出登记
    簿(press 类 τ=同轮),卖回恢复通道当轮结构性不可达;⑤息结算在
    轮末、按裸金(bench 资产不计息,P47)——穿线笔使当轮利息档恰降
    1 档且当轮不可恢复。

    口径分界(禁三处买分支判据漂移):
    - 与 P56 s_reserve(可变现口径)**不同源不同面禁统一**(账本预裁):
      s_reserve 管 EV 分支完成度价值买入的财富账,本线管纪律面当轮结算
      利息档,本谓词不消费 s_reserve 谓词;
    - 档 1 press_buy_deployable 的金位地板为同形判据,
      自本起消费本谓词(同谓词同值,行为不变);
    - ②(b) 当轮档地板是**另一形状**(当轮利息档保持 cost ≤ gold −
      10×⌊gold/10⌋,带内语义),不合流、勿合并。

    拦截语义 = 资格修正非票据废除(P88 同族):买后金 ≥ g* 的购买全程
    处于富余带——该带内支出息损 L≡0(P70 全网格复算已证),地板保留的
    全部行为都在已证零损域内;穿线笔(出域段)无在证授权,fail-closed。
    被截笔价值面(压缩/垫件)不进判据(P49 判据一:跨档压缩恒 0 为
    结构事实;价值账归显式模型轨,已登记为待办)。

    正本规格指认的家 = mandate.check_s_reserve 旁;因 mandate.py 存在
    并行在飞改动暂居本模块(文件面阶段化),归位迁移随 mandate
    面修正批整体平移(本函数零模块态依赖,平移零行为面)。
    """
    if gold - cost < g_star:
        return False, 'settlement_line'
    return True, ''


# ============================================================ 会话循环重写(迭代)


#: 机会清单的序类值域(shop_session §4.2:解拦后重评归属;六序 + C1/
#: dominance 邻位通道)。
ORDER_CLASSES: frozenset[str] = frozenset({
    'order_1', 'order_2', 'order_3', 'order_4', 'order_5',
    'c1_neighbor', 'dominance_neighbor',
})

#: 会话内累积的机会清单暂存 scratch 键(收工时按收工时牌面过滤后落库;
#: scratch 纪律 = 模块前缀 + 局级生命周期)。
_BLOCKED_SCRATCH_KEY: str = 'shop36_blocked_records'


def _face_names(gs: GameState) -> set[str]:
    """当前牌面名集(收工清单过滤/店内段验证消费)。"""
    return {c.name or '' for c in shop_payload_content_cards(gs.shop.value)}


def _session_close(gs: GameState, st, counters: dict) -> CwActionCloseShopParam:
    """会话收工(shop_session §2.5/§4:清单落库 + 标记判定 + 旗标清理)。

    - 清单 = 会话内暂存记录按**收工时牌面**过滤后落库(§4.2 牌面代次
      边界:会话内刷新后旧牌面记录随过滤消亡);
    - 标记:读数会话(意图标记 ∧ 本会话零处理动作)与受限 visit 不置
      (契约 A/§1 路径③),其余正常收工置 ``shop_handled``;
    - 旗标清理:读数意图/处理旗标(受限 visit 标记随 visit 生命周期,
      下一 visit 入口重取快照)。
    """
    def _count(key: str) -> None:
        counters[key] = counters.get(key, 0) + 1

    _pending = st.scratch.pop(_BLOCKED_SCRATCH_KEY, []) \
        if isinstance(st.scratch, dict) else []
    _face = _face_names(gs)
    st.shop_opportunities = tuple(
        rec for rec in _pending if rec.card_name in _face)
    if st.shop_read_intent and not st.shop_session_processing:
        _count('shop_close_read_noop')
    elif not st.shop_visit_restricted:
        session_scope.mark_shop_handled(gs)
    st.shop_read_intent = False
    st.shop_session_processing = False
    if gold_of(gs) >= 10:
        _count('shop_visit_idle_gold')
    return CwActionCloseShopParam()


def _session_upgrade_check(gs: GameState, session: StrategySession,
                           counters: dict, verdict: tuple) -> Action | None:
    """会话内升级意图出口(shop_session §2.2 前置升级检查;迭代
    2026-10-17-levelup-shop-transition design §2.1 三分支)。

    升级执行位置 = 备战画面(用户裁定 2026-10-17:商店画面不买经验,
    升级在备战画面做);本函数不再执行店内升级,收窄为「判定 + 关店
    转场」。资格门全链判定单一源 =
    :func:`criteria.levelup.upgrade_gate_verdict`(六道门序,与备战
    升级执行两屏同参消费,本函数零内联门、禁子集化;逐道拒因计数键域
    见该函数 docstring)——判定由调用方同帧一次评估后经 ``verdict``
    四元组传入(单帧全链判定只此一次;升级资金面由其门⑥资金线门
    承载)。三分支:

    - **判据命中 ∧ 本帧可发射** → 返回关店动作,**不置 handled 标记**
      (本次关店 = 升级转场,非「商店事情办完」;转场后升级先落地,
      重开会话时概率档已是新档——「升级金优先于买牌金,先定概率档」
      的排序语义保留);
    - **判据命中 ∧ 不可发射(待付窗)** → 返回 None,会话照常进入买牌
      六序与刷新判据。「等节点收入」形态由此成立:会话经 §2.5 正常
      收工置标记 → 出店 → 战斗 → 节点收入 → 备战侧凑金发射——不存在
      「开店即关」环(转场只在可发射帧发生,收店只在 §2.5 正常条件
      发生)。待付窗两形态:凑金可达域(gold_short,备战侧凑金收敛)与
      资金线不可达 defer(整批推迟等节点收入);
    - 未命中 → None,照常。

    资格门保证转场后零空转帧:店侧转场帧的后继(备战同参重评)必然
    命中且可发射,落店即执行。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup,
    )
    _verdict, _arm, _clicks, _cost = verdict
    if _verdict == levelup.GATE_EMIT:
        # 升级转场关店:不置 handled 标记、不写机会清单(转场帧的后继
        # = 备战升级执行,商店未「事情办完」);读数意图标记随任意关店
        # 出口清位(mandate_state.shop_read_intent 契约)。
        counters['levelup_transition_close'] = \
            counters.get('levelup_transition_close', 0) + 1
        state_of(gs).shop_read_intent = False
        return CwActionCloseShopParam()
    if _verdict == levelup.GATE_GOLD_SHORT:
        # 待付窗(凑金可达域):不凑金不发射,会话照常进入买牌六序
        # 与刷新判据;凑金 = 备战侧 levelup_liquidate_prep 场景
        # (资格门同参重评,凑至「现金 − 批 ≥ saturation_line」发射)。
        counters['levelup_stockpile_wait'] = \
            counters.get('levelup_stockpile_wait', 0) + 1
    return None


def decide_shop_action(gs: GameState, session: StrategySession,
                       config: object, *, registry=None) -> Action:
    """商店会话单动作决策(shop_session §1-§5 会话循环;迭代重写)。

    契约不变:**全函数**——f(期望态) → 恰一个动作,永不返回 None;
    「无动作可做」= ``CwActionCloseShopParam`` 终结动作(恒可用)。每帧
    按序评估,输出恰一个动作(单动作契约);刷新 = 访问终结(op 结束
    → 外循环重识别 → 本 op 重新入口观察,同一会话)。

    会话循环结构:

    1. 全 unknown 窗第二线(失读窗花钱动作全禁——主防线 = 商店 op
       入口观察停机闸,纵深第二线);
    2. visit 入口内务:金位账面锚定(读数协议③)/序 2 会话额度快照/
       解拦复核店内段(牌面外记录销项)/受限访问帧标记(契约 A 豁免);
    3. 会话标记门:本节点已处理 → 立即关店(幂等);受限访问帧不受
       标记覆盖;
    4. 前置升级检查(:func:`_session_upgrade_check`;每轮买入评估前
       ——升级意图出口三分支:命中 ∧ 可发射 → 关店转场不置标记,
       命中 ∧ 待付窗 / 未命中 → None 会话继续,design §2.1);
    5. 统一买入策略六序(契约 E;序 1 名单三态 + 席满买入六步流程 +
       金不足筹资,详见各段内注释);
    6. 三段式刷新判据(免费刷新无条件刷〔design §2.2,外层记忆闸照旧〕
       + 付费判据 + 金线闸);
    7. 收工(置标记 + 写清单;读数会话零处理 ∧ 意图标记 → 不置标记)。
    """
    if getattr(state_of(session), 'cw4_counters', None) is None:
        state_of(session).cw4_counters = {}
    _st = state_of(session)
    counters: dict = _st.cw4_counters

    def _count(key: str) -> None:
        counters[key] = counters.get(key, 0) + 1

    # ---- 1 全 unknown 窗第二线 ----
    _payload_u = gs.shop.value
    if _payload_u is not None and any(
            s.kind == 'unknown' for s in _payload_u.cards):
        return CwActionCloseShopParam()

    # ---- 2 visit 入口内务(读数协议③ + 会话域快照 + 店内段验证)----
    shop_sess.sync_gold_ledger(gs)
    if shop_sess.anchor_gold_ledger_if_new_visit(gs):
        _cap_snap = max_units_of(gs)
        _dep_n = len(_deployed_units_of(gs))
        _st.shop_plugin_budget = (_cap_snap - _dep_n) if _cap_snap else 0
        shop_sess.shop_recheck_drop_off_face(gs)
        from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
            launch_restricted_session_active,
        )
        _st.shop_visit_restricted = launch_restricted_session_active(gs)
        if _st.shop_visit_restricted:
            _count('shop_visit_restricted_frame')

    # ---- 3 会话标记门(契约 A 入口统一行为)----
    if not _st.shop_visit_restricted \
            and session_scope.shop_handled_for_current_node(gs):
        _st.shop_read_intent = False
        return CwActionCloseShopParam()

    # ---- 3.5 店内合成结果帧检测(读数协议②合成族;不分源含买入致合成)----
    shop_sess.detect_merge_result_frame(gs)

    # ---- 4 前置升级检查(升级意图出口,design §2.1 三分支;资格门全链
    # 本帧一次判定,会话内两消费面共用——升级出口 + 刷新整级预留
    # (§2.5③ 载体 = 判据现值,2026-10-17 迭代 T-4))----
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup as _crit_levelup,
    )
    _up_verdict, _up_arm, _up_clicks, _up_cost = \
        _crit_levelup.upgrade_gate_verdict(gs, session, registry=registry,
                                           counters=counters)
    _up = _session_upgrade_check(
        gs, session, counters, (_up_verdict, _up_arm, _up_clicks, _up_cost))
    if _up is not None:
        return _up

    # ---- 5 统一买入策略六序(契约 E)----
    _reg = registry
    if _reg is None:
        from sr_od.application.currency_war.kernel.cw_registry import (
            DEFAULT_REGISTRY,
        )
        _reg = DEFAULT_REGISTRY
    gold = shop_sess.session_gold(gs)
    bench = bench_entries_of(gs)
    deployed = _deployed_units_of(gs)
    bench_names = [mandate._slot_cid(b) for b in bench]
    deployed_names = [d.char_id or '' for d in deployed]
    bench_free = BENCH_CAPACITY - len(bench)
    owned = set(bench_names) | set(deployed_names)

    def _cnt(name: str, star: int) -> int:
        """同名同星副本计数(全局面 bench∪deployed;现行单一源)。"""
        n = 0
        for c in bench:
            u = mandate._slot_unit(c)
            if u is not None and (u.char_id or '') == name \
                    and (u.star or 1) == star:
                n += 1
        for d in deployed:
            if (d.char_id or '') == name and (d.star or 1) == star:
                n += 1
        return n

    cap_resolved = mandate._cap_of(session)
    g_star = saturation_line(cap_resolved)
    _cap_hold_now = cw_intention.locked_buy_cap_hold(gs)
    _ist = getattr(_st, 'v3_intention', None)
    _p2_started = session_scope.plane2_started_of(gs)
    _line_view = session_scope.line_members_view(gs)
    _cap_now = max_units_of(gs)
    _lvl_readable = bool(level_of(gs) is not None)

    # —— 序 1 名单解析(三态;契约 E)——
    # k = 现行方向阵容(锁定线优先,未锁 = 过渡配方开局面;§1.6 消费面
    # 分派的组合读形态——键面归一:target_comp = 锁定线槽单写者,
    # 未锁帧配方面走 opening_recipe_comp,读口单一源 = direction_comp_of)。
    k = session_scope.direction_comp_of(session)
    k_members = predicates.line_members(k)
    k_fallback: frozenset[str] | set[str] | None = None
    k_band: str | None = None
    if k is None and _ist is not None and _p2_started:
        # K 空窗回退(语义保留、判定源切换 = 未锁定旗标来自线选择机制
        # 〔锁定线槽空〕;line_and_upgrade §1.6 行):回退单一源 =
        # cw_intention,与备战域同源消费,禁复制。位面适用范围守卫(P86 甲分支
        # 并入:命题适用范围 = 位面 2——宪法第 2 条豁免登记的适用范围字面量,
        # 被停用调用位的 plane 条件在序 1 源①候选集构建处显式保留,
        # 非静默丢失;3.7 正本更新批消字面量化)。
        k_fallback, k_band = cw_intention.k_empty_window_fallback(
            gs, _ist, session=session, registry=_reg)
        if k_fallback:
            k_members = tuple(sorted(k_fallback))
            _count(f'shop_k_fallback_{k_band}')
    _buy_members = cw_intention.locked_buy_membership(_ist) \
        if _ist is not None else None
    # 保护集成员名集(帧级现算,买面接线单一源 = protection_membership;
    # design §2.2)。锁定态本集无买面消费(囤臂守卫 = 未锁定帧),仍按
    # 帧级单一读口现算供 ②(b) 保护档/计数键/拒因键消费。
    _protection = protection_membership(gs, _st)
    if _line_view.locked:
        # 锁定态(锁定线槽非空):P1 锁定局 = 过渡配方 ∪ 锁定线名单并集
        #(配方物化链不覆盖 P1 配方件);P2 起 = 锁定线名单单源(退出条件
        # 载体 = plane2_started 窗口谓词,line_and_upgrade §1.3 分域)。
        # 锁定态买面不动(design §2.2):义务面 = 买面名单,保护集不并入。
        if _p2_started:
            buy_members = tuple(sorted(set(_line_view.members)))
        else:
            _recipe = getattr(_st, 'opening_recipe_comp', None)
            _recipe_names = set(predicates.line_members(_recipe)) \
                if _recipe is not None else set()
            buy_members = tuple(sorted(
                set(_line_view.members) | _recipe_names))
        obligation_members = buy_members
    else:
        # 未锁定 = 候选态(义务面/囤货面拆分,design §2.2——现行成员
        # 待遇零变化,仅新增成员设级):
        # - 义务面 = 现行口径零变化:候选线成员并集 ∪ 贯穿件恒囤(空窗
        #   帧回退集承接为候选 stand-in)——免息 + 筹资 + 置换全待遇;
        # - 宽集买面名单 = 义务面 ∪ 保护集(序 1 未锁定名单并集,消除
        #   「配方对未选中体系成员」的名单缺口);
        # - 囤货面(宽集 − 义务面)= 期权级:首副本走新囤货臂(下),
        #   同名副本走 M6/序 5——义务类买入/筹资/排除面的比对域一律
        #   收窄义务面(见各消费位)。
        _cand_names: set[str] = set(k_members) | set(CROSS_LINE_KEEP_NAMES)
        for _cn in _st.line_candidates:
            _comp_c = get_comp(_cn) if _cn else None
            if _comp_c is None:
                continue
            _cand_names |= set(_comp_c.core_chars)
            _cand_names |= set(getattr(_comp_c, 'shared_chars', None) or ())
        obligation_members = tuple(sorted(_cand_names))
        buy_members = tuple(sorted(
            set(obligation_members) | set(_protection)))
    # —— 缺件集口径分域(W5 追星改革;设计 details/shop-buy-reform.md §1)——
    # 锁定后 = 缺口驱动:未持成员(现行口径,义务面照买)∪ 星级缺口成员
    # (消费 ``unfinished_star_targets`` 判据现值,只消费不改编据本体——
    # 修「义务面名单星级盲」:已持 2★ 追 3★ 成员同名 1★ 副本此前进不了
    # 任何买臂,追查件缺陷 4);减去 M2b 即时合成快路径名(1★ 档恰 2 张——
    # 该形态由 M2b 免席直发承接,进序 1 会被席满六步流程拦掉,快路径语义
    # 保留)。未锁窗口 = 维持现行候选缺件口径不变(未锁期星级目标集恒
    # 空集,字面替换会清空未锁窗口 M2;行为变化申报仅限锁定后)。
    # 达标集(锁定后星级目标已满足成员)= need_star 键 − 缺口集:同名
    # 副本对达标成员零推进,买臂显式停买(拒因键 ``star_goal_met``)。
    _star_gap_names: frozenset[str] = frozenset()
    _star_done_names: frozenset[str] = frozenset()
    _m2b_fast_names: frozenset[str] = frozenset()
    if _line_view.locked:
        _star_gap_names = frozenset(
            t[0] for t in _crit_levelup.unfinished_star_targets(gs))
        _star_need = set(getattr(k, 'need_star', None) or {})
        _star_done_names = frozenset(
            m for m in obligation_members
            if m in _star_need and m not in _star_gap_names)
        _m2b_fast_names = frozenset(
            m for m in obligation_members if _cnt(m, 1) == 2)
        missing = [m for m in obligation_members
                   if (m not in owned or m in _star_gap_names)
                   and m not in _m2b_fast_names]
    else:
        missing = [m for m in obligation_members if m not in owned]

    # P60 容量超限告警门(检查对象 = 义务面,design §2.2 对象面收窄——
    # 囤货面超容由席满六步流程自然管理;分母 = cap_hold 现读)。
    if obligation_members and _cap_hold_now is not None \
            and len(obligation_members) > _cap_hold_now:
        _count('shop_hoard_over_capacity')
        log.warning('[cw!][shop] 义务采购集 |B|=%d > 实用容量上界 '
                    'cap_hold=%d(bench 9 + 上阵 %d):义务面已截断',
                    len(obligation_members), _cap_hold_now,
                    _cap_hold_now - BENCH_CAPACITY)

    # 滞留素材暴露(单一源 = count_material_stale)。
    count_material_stale(counters, session, bench, deployed,
                         int(round_num_of(gs) or 1))
    # 保护集纯计数键(零行为;键值重定义 = 备战席上保护集成员数——
    # 统一保护集 design §2.4 计数键重定义,原「配方锁帧 ④ 件数」口径
    # 随 ④ 策展名单退役)。
    _prot_hold_n = sum(1 for b in bench
                       if mandate._slot_cid(b) in _protection)
    if _prot_hold_n:
        counters['transition_hold_locked_frame'] = \
            counters.get('transition_hold_locked_frame', 0) + _prot_hold_n

    # stop_buy 契约核验面(消费位历史:泄金阶梯档 0 三处消费位已摘,
    # 末位消费 = 旧筹资形态 MandateFrame,随会话内筹资重写停用——
    # [13] 停手线纪律由序 6 纯冗余停买与各序判据本体承载;核验面保留
    # = 契约纪律不断线,前提违例弃权计数照落)。
    if contracts.ensure_contract(
            ('proof', 'stop_buy'), contracts.ContractCtx(), counters):
        proof.stop_buy(k, bench_names, deployed_names)

    # —— 预算投影(序 3/4/5 共用金约束门;11 §1 判据零改动)——
    _mm_dedup: set[str] = set()
    _line_for_gate = sell_line_membership(gs)
    _p56_excl = sell_gate.sell_exclusions(
        session, tuple(sorted(_line_for_gate)), channel='projection',
        cap_hold=_cap_hold_now, current_round=int(round_num_of(gs) or 1))
    _dp_release = sell_gate.dead_pair_exit_release(
        session, tuple(sorted(_line_for_gate)), bench, deployed,
        int(round_num_of(gs) or 1), cap_hold=_cap_hold_now, counters=counters)
    liquid_refund = sum(sell_refund(1, bench_char_cost(b))
                        for b in mandate.fuel_sell_candidates(
                            bench, tuple(sorted(_line_for_gate)), state=gs,
                            exclude_names=_p56_excl, counters=counters,
                            dedup_names=_mm_dedup,
                            merge_guard_release=_dp_release))
    s_reserve = g_star - liquid_refund
    tier_w, card_w = _frame_search_windows(session, gs, _reg, counters)
    _narrow_frame = mandate.swap_transition_narrow_frame(gs, session)
    _front_window = predicates.front_window_frame(gs)
    if (gs.node.value.plane if gs.node.value is not None else None) == 1 \
            and not predicates.front_window_table_ready(gs):
        _count('p90_front_table_missing')
    _zw_armed = False
    if _front_window and predicates.zero_form_frame(deployed):
        _zw_armed = True
        _count('p90_zerostack_frame_armed')
        if not any(predicates.advances_four_system(
                getattr(c, 'name', '') or '')
                for c in shop_payload_content_cards(gs.shop.value)):
            _count('p94_no_activatable')
        elif provisional.is_none('U_X'):
            _count('p94_exemption_refuse')
    with contextlib.suppress(Exception):
        _st.cw4_shop_rejects = shop_unbought_reasons(
            gs, k, obligation_members, [], hub_names=frozenset(),
            protection=_protection)
    _t3_protect = mandate.stall_protect_active(
        session, round_num_of(gs), counters=counters)
    _round_sold = mandate.round_sold_names(session, gs)

    ev_arm = getattr(config, 'ev_arm', 'full')
    if ev_arm not in entry.EV_ARM_VALUES:
        ev_arm = 'full'
    skeleton_only = (ev_arm == 'skeleton_only')
    _zone_hit = in_must_spend_zone(gold, session)

    # —— 会话内动作发出公共位 ——
    def _mark_processing() -> None:
        _st.shop_session_processing = True

    def _record_opportunity(card_name: str, blocked_by: str,
                            price: int, order_class: str) -> None:
        """机会清单暂存(收工时按收工时牌面过滤后落库;§4.2)。"""
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            ShopOpportunity,
        )
        if not card_name or order_class not in ORDER_CLASSES:
            return
        _st.scratch.setdefault(_BLOCKED_SCRATCH_KEY, []).append(
            ShopOpportunity(card_name=card_name, blocked_by=blocked_by,
                            price=int(price), order_class=order_class))

    def _emit_buy(card: ShopCard, reason: str, *,
                  launch_cause: str | None = None) -> CwActionBuyCardParam:
        """买入动作发出点(fresh 排除登记 + 动作发出登记 + 读数协议伴生入金)。

        登记族语义(LAUNCH_CAUSE_BY_ARM 映射/合成销检出/种子获取/持久
        获取账)承继现行,禁第二实现;增补 = 伴生入金钩子
        (shop_session §4.2 记账层①:返利/返利+ 5 费计数——上报链不
        覆盖的单卡「X 动作时 +Y 金」型,双写账面与 gs.gold)。"""
        _buy_name = getattr(card, 'name', '') or ''
        record_fresh_buy(session, gs, _buy_name)
        shop_sess.account_buy_companion_gold(gs, card)
        _mark_processing()
        if _front_window:
            _fw_cost = card_cost(card)
            _count('p90_front_window_buy')
            if _fw_cost >= 3:
                _count('p90_front_buy_cost3p')
            _fw_loss = interest(gold, cap_resolved) - interest(
                max(0, gold - _fw_cost), cap_resolved)
            if _fw_loss >= 1:
                _count('p90_front_buy_cross_tier')
            if _fw_cost <= 2 and _fw_loss > 1:
                _count('p90_front_buy_over_bound')
            if _zw_armed and predicates.advances_four_system(_buy_name):
                _count('p90_zerostack_advancing_buy')
        if (getattr(card, 'star', 1) or 1) == 1 \
                and same_star_count(_buy_name, 1,
                                    bench_entries_of(gs),
                                    _deployed_units_of(gs)) >= 2:
            sell_gate.consume_on_merge(session, _buy_name)
            return CwActionBuyCardParam(card=card, reason=reason)
        _cause = launch_cause
        if _cause is None:
            _cause = sell_gate.launch_cause_of(reason)
        if _cause is None:
            raise ValueError(
                f'买入臂 {reason!r} 未登记 LAUNCH_CAUSE_BY_ARM 因果类'
                '映射(sell_gate;A4 硬闸——新臂'
                ' 先入映射表归入某因果类才可发射)')
        if sell_gate.register_launch(
                session, _buy_name, cause=_cause,
                round_num=int(round_num_of(gs) or 1),
                star=getattr(card, 'star', 1) or 1,
                cost=card_cost(card)) \
                and _cause == 'obligation' and _buy_name:
            _obligation_book(session)[_buy_name] = \
                int(round_num_of(gs) or 1)
        if _buy_name and sell_gate.seed_acquisition_eligible(
                _buy_name, getattr(card, 'star', 1) or 1,
                bench_entries_of(gs),
                _deployed_units_of(gs)):
            sell_gate.register_seed_acquisition(
                session, _buy_name,
                plane=(gs.node.value.plane if gs.node.value is not None else None),
                round_num=int(round_num_of(gs) or 1))
        if _buy_name:
            sell_gate.register_acquisition(
                session, _buy_name,
                plane=(gs.node.value.plane if gs.node.value is not None else None),
                round_num=int(round_num_of(gs) or 1),
                star=getattr(card, 'star', 1) or 1)
        return CwActionBuyCardParam(card=card, reason=reason)

    def _emit_sell_cand(cand, *, reason: str, counter_key: str) \
            -> CwActionSellBenchParam | None:
        """评估器候选 → 店内卖出动作(坐标换算:紧缩占席序 → 容器槽位
        表下标;失配 = 陈旧帧 fail-closed 返回 None)。"""
        vidx = mandate._bench_container_idx_by_compact(gs, cand.idx)
        if vidx is None:
            _count(f'{counter_key}_stale_idx')
            return None
        mandate.record_round_sold(session, gs, cand.char_id)
        _count(counter_key)
        _mark_processing()
        return CwActionSellBenchParam(
            bench_idx=vidx, reason=reason,
            income=sell_refund(int(cand.star or 1),
                               bench_char_cost(cand.unit, gs)),
            expect=cand.char_id)

    def _acquire_swap(card: ShopCard, order_class: str,
                      emit_buy: Callable[[], Action] | None = None
                      ) -> Action | None:
        """席满买入六步流程(统一让位优先级迭代 3.2;店内置换账整段替换,
        规格 = changes/2026-10-29-unified-priority/details/acquisition-
        and-sell.md §2 + 总纲 §2.3):

        ① 局面只读快照 → ② 新牌虚拟置入备战位 → ③ 升星连锁模拟
        (同名同星计数场上+备战混合达 3 合成、向三星推进、连锁到不再
        触发;合成释放备战位计入虚拟局面)→ ④ ``mandate.select_
        deployment`` 部署定型 → ⑤ 部署外全部持牌按 ``priority.sell_
        order`` 排序(排序池 = 备战位——场上件不入卖出池,被部署挤下
        件的离场归后续备战环节;新牌在手旗标 = 将获取,同优先级在手
        优先)→ ⑥ 末位 = 新牌 → 放弃买入(拦因改「优先级不足」进
        机会清单);末位 = 存量牌 → 发出卖旧——单动作契约:卖与买分
        两帧,下帧重入买入自然完成置换。

        ③ 后备战位净释放 → 无需让路直接买(总纲 §2.3 步骤 2;满栏
        合成买语义,游戏对完成合成的买入照常接受)。直买仅经调用方
        注入的臂内发射器 ``emit_buy``(承载该臂剩余门链与登记族语义);
        门链未在本分支走全的臂(如 M6 席满环的 stockpile 判据在位外)
        传 None = 净释放帧零动作,下帧席位已空由臂内正常买入路径接手
        ——零让路语义已达成,不绕门直买。虚拟重算全程快照纯计算
        (MandateFrame 构造,禁容器深拷贝)且零遥测(journal/策略遥测/
        决策帧三通道零写入,acquisition-and-sell 问题约束节)。
        """
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            bench_slot_unit,
        )
        from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.priority import (
            HeldUnit,
            ShopUnit,
            assemble_priority_context,
            priority_rng_of,
            sell_order,
        )
        _name = str(card.name or '')
        _star = int(card.star or 1)
        frame = mandate.snapshot_frame(gs)
        sim = mandate.simulate_acquired_units(
            frame.bench, frame.deployed, _name, _star)
        # 净释放判定 = 置入后单位可用空槽 > 0(占位件占槽不计入单位数,
        # 与 BENCH_CAPACITY 同一口径——合成释放的是单位槽,占位件槽
        # 不可卖不可放单位)。
        _n_items = sum(1 for b in frame.bench
                       if bench_slot_unit(b) is None)
        if BENCH_CAPACITY - _n_items - len(sim.bench) > 0:
            # 合成净释放备战位:无需让路(发射器在位 = 臂内门链已走全,
            # 直买;缺省 None = 门链未全,零动作交下帧臂内正常路径)。
            _count('acquire_swap_merge_free_buy')
            if emit_buy is not None:
                return emit_buy()
            return None
        v_bench = [bs for _i, bs in sim.bench]
        v_frame = mandate.MandateFrame(
            gold=frame.gold, level=frame.level, bench=v_bench,
            deployed=sim.field, deploy_cap=frame.deploy_cap,
            node_type=frame.node_type, stop_flag=False,
            k_members=frame.k_members, round_num=frame.round_num,
            overflow_warning=frame.overflow_warning)
        prep = mandate.assemble_prep_context(session, gs, v_frame)
        target = mandate.select_deployment(v_frame, prep)
        # 虚拟持牌全量快照(档 2/5/6/7 聚合谓词看虚拟局面全量)。
        v_copies: dict[str, list[int]] = {}
        for u in (*(bench_slot_unit(b) for b in v_bench), *sim.field):
            if u is not None and u.char_id:
                v_copies.setdefault(str(u.char_id), []).append(
                    int(u.star or 1))
        ctx = assemble_priority_context(
            session, gs, deployed_names=target, held_copies=v_copies,
            rng=priority_rng_of(session, config))
        # 排序池 = 备战位(acquisition §2 步骤 5):存量牌以 HeldUnit
        # (在手旗标 0)承载,新牌以 ShopUnit(将获取旗标 1)承载——虚拟
        # 备战位里的新牌本体不重复入池(origin 哨兵 = len(frame.bench)),
        # 否则新牌的在手影子会抢在其 ShopUnit 之前、末位判定失真。
        units: list[HeldUnit | ShopUnit] = []
        for orig, bs in sim.bench:
            if orig >= len(frame.bench):
                continue   # 置入的新牌 = 由 ShopUnit 承载,不双计
            u = bench_slot_unit(bs)
            if u is None or not u.char_id:
                continue
            units.append(HeldUnit(
                str(u.char_id), int(u.star or 1), orig, False,
                cost=(effective_cost(gs, str(u.char_id)) or None)))
        units.append(ShopUnit(_name, _star, card_cost(card)))
        tail = sell_order(units, ctx)[-1]
        if isinstance(tail, ShopUnit):
            # 末位 = 新牌自己 → 放弃买入(拒绝语义:拦因键改「优先级
            # 不足」,acquisition §2;本牌进未消费机会清单,解拦复核
            # 对本拦因无解拦动作——非瞬时可解除的拦阻)。
            _count('acquire_swap_declined')
            _record_opportunity(_name, 'priority_insufficient',
                                card_cost(card), order_class)
            return None
        # 末位 = 存量牌 → 卖旧(坐标还原:虚拟尾牌的原紧缩占席序下标
        # → 容器槽位表下标;失配 = 陈旧帧 fail-closed 零动作)。
        vidx = mandate._bench_container_idx_by_compact(gs, tail.slot)
        if vidx is None:
            _count('acquire_swap_stale_idx')
            return None
        mandate.record_round_sold(session, gs, tail.name)
        _count('acquire_swap_sell')
        _mark_processing()
        return CwActionSellBenchParam(
            bench_idx=vidx, reason='shop_swap',
            income=sell_refund(int(tail.star or 1),
                               bench_char_cost(
                                   Unit(char_id=tail.name, star=tail.star),
                                   gs)),
            expect=tail.name)

    def _funding_sell(card: ShopCard, order_class: str) -> Action | None:
        """筹资伴生卖出(shop_session §2.3:前置 = 买入判据已过 ∧ 金
        不足——不跌破利息档为未过判据的牌筹资)。

        统一序列末位备战位件凑缺口(session_funding 场景,3.2 改造:
        排序单一源 = priority.sell_order,仅一星代理过滤退役【拍,总纲
        §2.4】;店内禁卖场上 → 消费位只取备战席支,场上件 = 档 1 本就
        序列永不先卖),凑够即买(下一帧买入分支自然接手)、不多卖;
        主路径尽 → P78-5 四条件兜底豁免(funding 通道对价,单一源 =
        sell_gate.funding_hold_fallback;两条分支必要条件:序 1/序 2 =
        骨架义务血统分支①,其余 = 对象级无损分支②);候选穷尽仍不足
        → 该牌进机会清单(拦因 = 金不足;义务类金不足入清单合法,其
        解拦购买允许跌破利息档——§4.2 解拦复核规则)。缺口判定用账面金
        (读数协议④:多卖循环第二笔起禁逐笔开店重读)。"""
        need = card_cost(card)
        cands, _why = evaluate_sell_candidates(gs, 'session_funding')
        _cand = next((c for c in cands if c.zone == 'bench'), None)
        if _cand is not None:
            act = _emit_sell_cand(_cand, reason='session_funding',
                                  counter_key='session_funding_sell')
            if act is not None:
                return act
        _line = tuple(sorted(sell_line_membership(gs)))
        fallback = sell_gate.funding_hold_fallback(
            session, _line, bench, gold=shop_sess.session_gold(gs),
            need=need,
            a_exclusions=sell_gate.sell_exclusions(
                session, _line, channel='funding',
                current_round=round_num_of(gs),
                cap_hold=_cap_hold_now),
            deployed=deployed,
            cap_hold=_cap_hold_now)
        if fallback:
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                bench_slot_unit,
            )
            u = bench_slot_unit(fallback[0])
            _legs_ok = False
            if order_class in ('order_1', 'order_2'):
                _legs_ok = True   # 分支①:骨架义务血统(触发源 = 序 1/2)
            elif u is not None:
                # 分支②对象级无损判定域 = 「保护集 ∪ registry 核心」
                # (统一保护集 design §2.3 表:常规筹资不卖保护件与核心,
                # 最后手段走 P78-5 通道;兜底池 ⊆ 该域 ⇒ 偏好分支结构性
                # 恒拒,验证照落为防御性分支)。
                _nm = str(u.char_id or '')
                _legs_ok = (
                    _nm not in protection_membership(gs, state_of(gs))
                    and _nm not in CORE_SINGLE_CARD_REGISTRY
                    and _nm not in sell_gate.seed_exclusions(
                        session, round_num_of(gs)))
            if _legs_ok and u is not None:
                idx = mandate._bench_container_idx(gs, fallback[0])
                if idx is not None:
                    mandate.record_round_sold(session, gs,
                                              str(u.char_id or ''))
                    _count('session_funding_fallback_sell')
                    _mark_processing()
                    return CwActionSellBenchParam(
                        bench_idx=idx, reason='session_funding',
                        income=sell_refund(int(u.star or 1),
                                           bench_char_cost(u, gs)))
            _count('session_funding_leg_reject')
        _record_opportunity(str(card.name or ''), 'gold_short',
                            need, order_class)
        _count('session_funding_exhausted')
        return None

    def _buy_view(arm_key: str) -> list[ShopCard]:
        """店内卡全集的 L2 过滤视图(本轮已卖名集剔除;零成型帧推进件
        前移排序——P90 前窗,现行语义保留)。"""
        out: list[ShopCard] = []
        for c in shop_payload_content_cards(gs.shop.value):
            n = c.name or ''
            if n and n in _round_sold:
                _count(f'{arm_key}_round_sold_excluded')
                continue
            out.append(c)
        if _zw_armed:
            out.sort(key=lambda c: 0 if predicates.advances_four_system(
                c.name or '') else 1)
        return out

    def _shop_candidates(m: str, arm_key: str = ''):
        if m and mandate.sold_this_round(session, gs, m):
            if arm_key:
                _count(f'{arm_key}_round_sold_excluded')
            return []
        return sorted(
            (c for c in shop_payload_content_cards(gs.shop.value)
             if (c.name or '') == m),
            key=lambda c: (card_cost(c)))

    def _on_target_buy() -> None:
        """D-A45 商店侧半边:买入目标件 ⇒ 干旱计数器重置(现行语义)。"""
        ls = getattr(_st, 'cw4_line_state', None)
        if ls is not None and getattr(ls, 'drought', 0):
            ls.drought = 0
            _count('shop_drought_reset_on_buy')

    def _fund_or_none(card: ShopCard, order_class: str) -> Action | None:
        """金不足 → 筹资伴生卖出(判据已过前置由调用方保证)。"""
        if shop_sess.session_gold(gs) >= card_cost(card):
            return None
        return _funding_sell(card, order_class)

    # ===== 序 1:目标阵容件 =====
    # 承继变更申报:满席腾位关店链(关店→备战卖→重开)废止——席满走
    # 席满买入六步流程(3.2:置换账替换);金不足走会话内筹资;两类
    # 拦阻进机会清单。
    for m in missing:
        shop_cands = _shop_candidates(m, 'm2')
        if not shop_cands:
            continue
        card = shop_cands[0]
        cost = card_cost(card)
        if bench_free <= 0:
            def _emit_m2(card=card, m=m, cost=cost) -> Action | None:
                # 席满分支的金门在置换评估后补(与现行分支序一致):
                # 净释放帧金不足 = 零动作交筹资分支下帧处置。循环变量
                # 经默认参绑定(ruff B023;本函数当帧即调用,无迟绑定面)。
                if gold < cost:
                    return None
                _on_target_buy()
                return _emit_buy(card, 'm2_line_member' if m in k_members
                                 else 'm2_locked_member')
            _sw = _acquire_swap(card, 'order_1', _emit_m2)
            if _sw is not None:
                return _sw
            continue
        if gold < cost:
            _fd = _fund_or_none(card, 'order_1')
            if _fd is not None:
                return _fd
            continue
        _on_target_buy()
        return _emit_buy(card, 'm2_line_member' if m in k_members
                         else 'm2_locked_member')

    # m2_stockpile(分支① 囤分支,j=1 第二份;现行判据本体不动——含 P77
    # 现货比较子;席满 → 六步流程,金不足 → 筹资。遍历域 = 义务面,design
    # §2.2:囤货面成员同名副本退出义务类买入/筹资,恢复压牌库/凑星通道)。
    for m in obligation_members:
        if _cnt(m, 1) != 1 or _cnt(m, 2) != 0:
            continue
        if _line_view.locked:
            if m in _star_gap_names:
                # W5 缺口分域:缺口 > 0 成员已升格序 1 缺件买臂域(任意
                # 星级照买,先行段已发射或入六步流程),本囤臂不再重评——
                # 防同帧双重置换/筹资评估与机会清单重复入账。
                continue
            if m in _star_done_names:
                # W5 显式停买:星级目标已满足成员的同名副本零推进(追星
                # 口径缺口 = 0),拒因键可观测(旧口径此处会买第二张 1★)。
                _count('star_goal_met')
                continue
        all_cands = _shop_candidates(m, 'm2_stockpile')
        cands1 = [c for c in all_cands if (c.star or 1) == 1]
        _spot2 = spot2_direct_out_card(
            all_cands, m, level_of(gs),
            refresh_cost_effective(gs=gs)) \
            if not cands1 else None
        if _spot2 is not None:
            card = _spot2
            cost = card.cost or 3 * int(CHARACTERS[m].cost)
        elif cands1:
            card = cands1[0]
            cost = card_cost(card)
        else:
            if all_cands:
                _count('m2_stockpile_star_mismatch')
            continue
        if gold < cost:
            _count('stockpile_unaffordable')
            _fd = _fund_or_none(card, 'order_1')
            if _fd is not None:
                return _fd
            continue
        if bench_free <= 0:
            # m2_stockpile 席满分支:金门已过,净释放帧可直买。
            _sw = _acquire_swap(
                card, 'order_1',
                lambda card=card: _emit_buy(card, 'm2_stockpile'))
            if _sw is not None:
                return _sw
            _count('bench_full')
            continue
        _on_target_buy()
        if _spot2 is not None:
            _count('m2_stockpile_spot2_buy')
        return _emit_buy(card, 'm2_stockpile')

    # M2b 升星合并完成买入(机制全集口径消费 :func:`_merge_pair_names`;
    # 满栏例外免席——机制出处 merge_mechanics §2.5,买入即合成净释放
    # 1 席)。W5 机制全集扩面:1★ 档恰 2 张 ∧ 已持同名 2★ 的形态(场上
    # 2★ + 备战 1★×2)旧「恰 2 张全 1★」口径排除,本臂现承接——买第 3 张
    # 1★ 合成第 2 个 2★,向 3★ 推进。1★ 买入合法性门 = 该名 1★ 档计数
    # == 2(只有 2★ 档凑满 3 进度的名,买 1★ 不触发合成,无免席资格,
    # 其缺口照买归序 1 缺件域)。
    _pairs = _merge_pair_names(bench, deployed)
    for m in buy_members:
        if m not in _pairs or _cnt(m, 1) != 2:
            continue
        if _line_view.locked and m in _star_done_names:
            # W5 显式停买:达标成员的合成完成买入同样零推进(如 1★ 目标
            # 已持对仍凑合成),拒因键同序 1 口径。
            _count('star_goal_met')
            continue
        all_cands = _shop_candidates(m, 'm2_merge_completion')
        shop_cands = [c for c in all_cands if (c.star or 1) == 1]
        if not shop_cands:
            if all_cands:
                _count('m2b_star_mismatch')
            continue
        card = shop_cands[0]
        cost = card_cost(card)
        if gold < cost:
            _fd = _fund_or_none(card, 'order_1')
            if _fd is not None:
                return _fd
            continue
        _on_target_buy()
        return _emit_buy(card, 'm2_merge_completion')

    # ===== 新囤货臂(④ 转投分支退役的语义承接;design §2.2)=====
    # 位置 = M2b 后、序 2 前。守卫 = 未锁定帧(终局锁定态;锁定局过渡件
    # 采购由配方对并集承载,囤臂不聚焦)。命中 = 保护集成员 ∧ 未持有首
    # 副本(不限未点亮——已点亮但不在配方对体系的成员同臂承接)。门序 =
    # 1★ 全额退(refund_full_star_ok,[11] 零息损 + P46 豁免类「资产可
    # 逆」)→ 金可负担(期权级,无筹资特权)→ 席(席满走六步流程,
    # 候选 = 非保护垫件;穷尽 = 放弃并计数)。买因 protection_hoard
    #(hold 类,LAUNCH_CAUSE_BY_ARM 单一映射);出口键 protection_hoard_
    # hit / protection_hoard_no_fuel / protection_hoard_unaffordable。
    if not _line_view.locked:
        for card in _buy_view('protection_hoard'):
            name = card.name or ''
            if not name or name not in _protection or name in owned:
                continue
            cost = card_cost(card)
            if not refund_full_star_ok(card.star or 1, cost):
                continue
            if gold < cost:
                _count('protection_hoard_unaffordable')
                _record_opportunity(name, 'gold_short', cost, 'order_1')
                continue
            if bench_free <= 0:
                # 席满 → 六步流程(金门已过,净释放帧可直买)。
                _sw = _acquire_swap(
                    card, 'order_1',
                    lambda card=card: _emit_buy(card, 'protection_hoard'))
                if _sw is not None:
                    return _sw
                _count('protection_hoard_no_fuel')
                continue
            _count('protection_hoard_hit')
            return _emit_buy(card, 'protection_hoard')

    # ===== 序 2:场况插件(板面羁绊差一人进下一档;会话累计额度)=====
    if _st.shop_plugin_budget > 0:
        _front_r, _back_r = deployed_rows_of(gs)
        _board_tags = board_by_row(_front_r, _back_r).total()
        for card in _buy_view('scene_plugin_buy'):
            name = card.name or ''
            if not name:
                continue
            # 羁绊差一人判定([35];11 §1 序 2 判据本体):该卡任一羁绊
            # 标签的板面计数 +1 恰达下一激活档(单单位聚合 = 按排聚合
            # 单一源 board_by_row 的单件形态,与 sell_candidates 同源)。
            _u = Unit(char_id=name, star=int(card.star or 1))
            _tags = set(board_by_row([_u], []).front) \
                | set(board_by_row([], [_u]).back)
            _gap = False
            for _tag in _tags:
                _info = FACTIONS.get(_tag)
                if _info is None or not _info.tiers:
                    continue
                _c = _board_tags.get(_tag, 0)
                _nxt = next((t for t in _info.tiers if t > _c), None)
                if _nxt is not None and _c + 1 >= _nxt:
                    _gap = True
                    break
            if not _gap:
                continue
            cost = card_cost(card)
            # 义务通道语义(序 1/序 2 不走息律门;[41])。
            if gold < cost:
                _fd = _fund_or_none(card, 'order_2')
                if _fd is not None:
                    return _fd
                continue
            if bench_free <= 0:
                # 席满 → 六步流程(金门已过,净释放帧可直买)。
                _sw = _acquire_swap(
                    card, 'order_2',
                    lambda card=card: _emit_buy(card, 'scene_plugin_buy'))
                if _sw is not None:
                    return _sw
                _count('scene_plugin_no_seat')
                continue
            _st.shop_plugin_budget -= 1
            _count('scene_plugin_buy_hit')
            return _emit_buy(card, 'scene_plugin_buy')
    elif _st.shop_plugin_budget <= 0:
        # 额度尽即停(上阵空位非节点内可解除资源,拦因在 {席满,金不足}
        # 闭集外——被拦插件不进机会清单,部署步消耗空位后判据下帧自然
        # 重评;shop_session §2.2 序 2)。
        _count('scene_plugin_budget_exhausted')

    # ===== 序 4:压牌库件(②(b) 死金 → 档 1 可上场 → M6 富余 → 垫件补位支)=====
    # (序 4 前置于 EV 面系承继现行物理位次——②(b)「M3 后 M6/EV 前」
    # 明文位次继承,line_and_upgrade §2.2;EV 面 = 序 3/5 联合载体,
    # 生产 fail-closed 零行为差,位次申报见收工对照表。)

    # —— ②(b) 死金压牌库(现行判据本体不动;消费位随会话循环接线)——
    if gold < g_star and reward_node_suppressed(gs):
        _dead_gold = gold - 10 * (gold // 10)
        # prio0 缺口集推导域 = 缺件集(与 missing 同款两推导同步收窄,W5
        # 缺口口径:锁定后含星级缺口成员;囤货面缺口归囤臂,不入死金缺口账)。
        _dg_gap = set(missing)
        for _dg_prio in range(3):
            for card in _buy_view('dead_gold_press_buy'):
                name = card.name or ''
                cost = card_cost(card)
                if not name or cost > _dead_gold:
                    continue
                if _dg_prio == 0:
                    _hit = name in _dg_gap
                elif _dg_prio == 1:
                    # 保护档(design §2.4 消费迁移):registry 核心 →
                    # prio1 延续(零回退);保护集成员 → prio1(过渡优先)。
                    # 注册表扩员成员(如桑博/椒丘等 drop/漏计档)自
                    # unrelated(prio2)位移保护档 = 本批预期行为(身份
                    # 升格,design §2.2 申报)。
                    _hit = (name in CORE_SINGLE_CARD_REGISTRY
                            or name in _protection)
                else:
                    # prio2(press):档位表分支已退役摘除(design §2.4)——
                    # 到本档的名恒为非核心非保护(其余 → prio2),
                    # 结构分支(1★/零重叠/全额退)保持。
                    _hit = ((card.star or 1) == 1
                            and predicates.zero_overlap(name, k_members)
                            and refund_full_star_ok(1, cost))
                    if _hit and mandate.dead_stock_pair_buy_reject_reason(
                            name, card.star or 1, bench, deployed,
                            k_members):
                        _count('press_dead_stock_pair_blocked')
                        _hit = False
                if not _hit:
                    continue
                if gold < cost:
                    continue
                _dg_cause = ('obligation', 'hold', 'press')[_dg_prio]
                if bench_free <= 0:
                    # 席满 → 六步流程(金门已过;发射器携臂内因果类
                    # launch_cause,净释放帧直买语义随臂)。
                    _sw = _acquire_swap(
                        card, 'order_4',
                        lambda card=card, cause=_dg_cause: _emit_buy(
                            card, 'dead_gold_press_buy',
                            launch_cause=cause))
                    if _sw is not None:
                        return _sw
                    _count('dead_gold_press_bench_full_gate')
                    continue
                ok2, _ = mandate.check_seats(
                    bench_free, 0, needs_bench=True, needs_board=False,
                    name='', deployed_names=deployed_names)
                if not ok2:
                    break
                _count('dead_gold_press_buy_hit')
                return _emit_buy(card, 'dead_gold_press_buy',
                                 launch_cause=_dg_cause)

    # —— 档 1:可上场非定向买(现行判据本体不动;富余段消费位)——
    if getattr(_ist, 'locked_comp', None) and _zone_hit:
        _pd_vac = (_cap_now - len(deployed)) if _cap_now else None
        if _pd_vac is None:
            _count('press_buy_deployable_cap_unreadable')
        elif _pd_vac < 1:
            _count('press_buy_deployable_no_vacancy')
        else:
            _pd_tgt, _pd_fw = deploy_target_sets(k)
            try:
                _pd_lfs = cw_intention.locked_faction_scope(_ist) \
                    if _ist is not None else frozenset()
            except Exception:   # noqa: BLE001 兜底 best-effort(现行)
                _pd_lfs = frozenset()
            try:
                _pd_rf = cw_intention.locked_line_recipe_floor_conflict(_ist)
            except Exception:   # noqa: BLE001 豁免语境 fail-closed(现行)
                _pd_rf = False
            for card in _buy_view('press_buy_deployable'):
                name = card.name or ''
                if not name or name in obligation_members:
                    continue    # 义务面线内件归序 1 义务通道(design §2.2
                    # 排除面收窄:囤货面成员恢复压牌库通道)
                cost = card_cost(card)
                _pf_ok, _ = check_settlement_line(gold, cost, g_star)
                if not _pf_ok:
                    _count('press_buy_deployable_below_floor')
                    continue
                if (card.star or 1) == 1 \
                        and predicates.zero_overlap(name, k_members) \
                        and refund_full_star_ok(1, cost):
                    _count('press_buy_deployable_filler_excluded')
                    continue
                _pd_mch = get_char(name)
                _pd_cand = BenchSlot(
                    kind='unit',
                    unit=Unit(char_id=name, star=(card.star or 1)))
                try:
                    _pd_ok, _pd_why = can_deploy_single(
                        _pd_cand, bench,
                        deployed_cids=set(deployed_names),
                        deployed_fac=deployed_bond_counts(
                            set(deployed_names)),
                        board=deployed_bond_counts(set(deployed_names)),
                        cap=(_cap_now if _cap_now else 10 ** 6),
                        target_factions=_pd_tgt,
                        target_cores=set(),
                        fw_carry=_pd_fw,
                        locked_factions=_pd_lfs or frozenset(),
                        recipe_floor_lock_exempt=_pd_rf)
                except Exception:   # noqa: BLE001 查询不可得 fail 向
                    _pd_ok, _pd_why = False, 'precheck_unavailable'
                if not _pd_ok:
                    _count('press_buy_deployable_fenced')
                    _count(f'press_buy_deployable_fenced_{_pd_why}')
                    continue
                if gold < cost:
                    _count('press_buy_deployable_unaffordable')
                    continue
                if bench_free <= 0:
                    # 席满 → 六步流程(金门已过,净释放帧可直买)。
                    _sw = _acquire_swap(
                        card, 'order_4',
                        lambda card=card: _emit_buy(card,
                                                    'press_buy_deployable'))
                    if _sw is not None:
                        return _sw
                    _count('press_buy_deployable_bench_full_gate')
                    continue
                _count('press_buy_deployable_hit')
                return _emit_buy(card, 'press_buy_deployable')

    # —— M6 富余转压牌库(现行判据本体不动;整买预留约束经 s_reserve
    # 与 R2 侧预留承载)——
    # W4 停留刷窗口让位(设计 details/shop-buy-reform.md §2):窗口内
    # (``refresh_warranted`` 为真)M6 压牌库囤货臂停用——窗口内金用途
    # 优先级 = 刷新 + 目标卡钱,富余金留线上吃息;囤货买入与刷新争席是
    # 支配性互斥(席位是刷新买卡的必要资源,追查件缺陷 3 归因 = M6 灌满
    # 反锁刷新)。求值时点 = 本帧 M6 触发判定点即时求值(与刷新提案段
    # 同帧同参,禁第二推导;判定轴复用总纲接口契约;非帧首快照)。免费
    # 刷不耗金不受影响(窗口内免费刷仍可用);非窗口 M6 照常。
    _m6_exhausted = gold <= g_star   # 无富余 ⇒ 压牌库候选结构性耗尽(空转)
    _m6_arms = gold > g_star
    if _m6_arms:
        _m6_ok_w, _ = crit_refresh.refresh_warranted(
            gs, session, k_members=k_members, counters=counters,
            dedup_names=_mm_dedup)
        if _m6_ok_w:
            _count('m6_stay_window_yield')
            _m6_arms = False
    if _m6_arms:
        ok2, _ = mandate.check_seats(
            bench_free, 0, needs_bench=True, needs_board=False,
            name='', deployed_names=deployed_names)
        if not ok2:
            # 席满 → 六步流程(候选过滤 = M6 视图去义务面线内件
            # 〔design §2.2 排除面收窄〕——压牌库判据的席位维由序列
            # 末位让路承载;stockpile 判据在席位分支之外未走全,发射器
            # 不注入 = 净释放帧零动作,下帧席位空由正常 M6 臂接手)。
            for card in _buy_view('m6'):
                _m6_name = card.name or ''
                if not _m6_name or _m6_name in obligation_members:
                    continue
                if gold < card_cost(card):
                    continue
                _sw = _acquire_swap(card, 'order_4')
                if _sw is not None:
                    return _sw
            _count('m6_bench_full')
        elif not tier_w:
            _count('m6_overflow_strand')
            _m6_exhausted = True
        else:
            _stock_ok = contracts.ensure_contract(
                ('stockpile', 'stockpile_buy'),
                contracts.ContractCtx(k_members=k_members, k_target=k),
                counters)
            _p91_band = frozenset(crit_refresh.qualified_member_costs(
                buy_members, bench, deployed, level_of(gs)))
            if _p91_band:
                _count('p91_active_band_frame')
            _m6_cands = _buy_view('m6')
            if _p91_band:
                _m6_cands = sorted(
                    _m6_cands,
                    key=lambda c: 0 if (card_cost(c)) in _p91_band
                    else 1)
            if _front_window:
                _m6_cands = sorted(
                    _m6_cands,
                    key=lambda c: 0 if (card_cost(c)) <= 2 else 1)
            _m6_hit = False
            for card in _m6_cands:
                name = card.name or ''
                if name in obligation_members:
                    _count('m6_line_member_excluded')
                    continue
                cost = card_cost(card)
                okm, _mkey = crit_stockpile.stockpile_buy(
                    gold, s_reserve, bench_free, cost,
                    card.star or 1, tier_w) if _stock_ok else (False, '')
                if not okm:
                    if _mkey == 's_reserve':
                        _count('m6_s_reserve_reject')
                        if name:
                            counters['m6_s_reserve_remeet_frames_sum'] = (
                                counters.get(
                                    'm6_s_reserve_remeet_frames_sum', 0)
                                + _s_reserve_remeet_frames(
                                    level_of(gs), bench, deployed,
                                    card))
                    continue
                if gold < cost:
                    continue
                if _p91_band:
                    _count('p91_m6_same_axis_hit' if cost in _p91_band
                           else 'p91_m6_off_axis_hit')
                _m6_hit = True
                return _emit_buy(card, 'm6_stockpile')
            if not _m6_hit:
                _m6_exhausted = True

    # —— 垫件补位支(并入 = 17 号稿出口③/20 号稿 L2/T5;触发域改写:
    # 停滞支出授权激活 ∨ 富余帧,∧ 压牌库候选耗尽——「压牌库候选耗尽即买
    # 第二触发域」;未锁定期 Φ_stall 零开火 → 停滞授权支休眠〔休眠
    # 申报 + 随锁定打开〕;T5 的 cost-1 收窄形态随统一垫件过滤器替代)——
    _ff_stall_auth = False
    if getattr(_ist, 'locked_comp', None) and _lvl_readable:
        if level_of(gs) - len(deployed) > 0 or _zone_hit:
            _rp = (gs.shop.value.refresh_probs
                   if gs.shop.value is not None else None)
            _causal: list[str] = []
            _chaseable = False
            if _rp is None:
                _chaseable = True   # 概率条不可得:fail 向(视同可追)
            else:
                for _m in k_members:
                    if _cnt(_m, 2) > 0:
                        continue
                    _mch = get_char(_m)
                    _mcost = _mch.cost if _mch is not None else None
                    if _mcost is None:
                        continue
                    if effective_refresh_prob(
                            gs, level_of(gs), _mcost) <= 0.0:
                        _causal.append(_m)
                    else:
                        _chaseable = True
            if (_causal and not _chaseable) or _zone_hit:
                if _zone_hit:
                    _count('must_spend_l2_trigger')
                if gold > s_reserve:
                    _ff_stall_auth = True
    if (_ff_stall_auth or _zone_hit) and _m6_exhausted:
        _ff_sale = [c for c in _buy_view('fuel_filler_stall')
                    if (c.name or '')
                    and (c.name or '') not in obligation_members
                    and (c.star or 1) == 1
                    and predicates.zero_overlap(c.name or '',
                                                k_members)
                    and refund_full_star_ok(
                        1, card_cost(c))]
        if not _ff_sale:
            _count('fuel_not_on_sale')
        elif bench_free <= 0:
            # 席满 → 六步流程(precheck 门在本分支之外未走全,发射器
            # 不注入 = 净释放帧零动作,下帧席位空由正常垫件补位支接手)。
            for card in _ff_sale:
                if gold - card_cost(card) < s_reserve:
                    continue
                _sw = _acquire_swap(card, 'order_4')
                if _sw is not None:
                    return _sw
            _count('bench_full')
        else:
            for card in _ff_sale:
                name = card.name or ''
                cost = card_cost(card)
                if gold - cost < s_reserve:
                    _count('below_reserve')
                    continue
                _cand_bc = BenchSlot(
                    kind='unit',
                    unit=Unit(char_id=name, star=1))
                _tgt2, _fw2 = deploy_target_sets(k)
                try:
                    _lfs = cw_intention.locked_faction_scope(
                        _ist) if _ist is not None \
                        else frozenset()
                except Exception:   # noqa: BLE001 兜底 best-effort
                    _lfs = frozenset()
                try:
                    _rf_ctx = cw_intention \
                        .locked_line_recipe_floor_conflict(_ist)
                except Exception:   # noqa: BLE001 豁免语境 fail-closed
                    _rf_ctx = False
                try:
                    _ff_ok, _ff_why = can_deploy_single(
                        _cand_bc, bench,
                        deployed_cids=set(deployed_names),
                        deployed_fac=deployed_bond_counts(
                            set(deployed_names)),
                        board=deployed_bond_counts(set(deployed_names)),
                        cap=(_cap_now if _cap_now
                             else 10 ** 6),
                        target_factions=_tgt2,
                        target_cores=set(),
                        fw_carry=_fw2,
                        locked_factions=_lfs or frozenset(),
                        recipe_floor_lock_exempt=_rf_ctx)
                except Exception:   # noqa: BLE001 查询不可得
                    _ff_ok, _ff_why = False, \
                        'precheck_unavailable'
                if not _ff_ok:
                    if _ff_why == 'precheck_unavailable':
                        _count('fuel_filler_stall_'
                               'precheck_unavailable')
                    else:
                        _count('fuel_filler_stall_fenced')
                        _count(f'fuel_filler_stall_fenced_'
                               f'{_ff_why}')
                        if _zone_hit:
                            _count(f'fuel_filler_stall_fenced_'
                                   f'l2_{_ff_why}')
                    continue
                _count('fuel_filler_stall_buy')
                mandate.stall_buys_register(
                    session, name, round_num_of(gs))
                _on_target_buy()
                return _emit_buy(card, 'fuel_filler_stall')

    # ===== 序 3/序 5:通用插件 + 凑星件(EV 面照旧,fail-closed)=====
    if not skeleton_only:
        if contracts.ensure_contract(
                ('buy', 'ev_buy_candidates'),
                contracts.ContractCtx(k_members=k_members, k_target=k),
                counters):
            cands, ckey = crit_buy.ev_buy_candidates(
                gold, s_reserve,
                (gs.shop.value.cards if gs.shop.value is not None else []),
                obligation_members,
                level=level_of(gs), window=card_w,
                counters=counters)
            if ckey:
                _count(f'shop_ev_{ckey}')
            elif cands:
                ok_seat, _ = mandate.check_seats(
                    bench_free, 0, needs_bench=True, needs_board=False,
                    name='', deployed_names=deployed_names)
                if not ok_seat:
                    # 席满 → 六步流程(生产 U_X None fail-closed 恒零
                    # 候选,接线统一为零行为差;veto/金门在席位分支外
                    # 未走全,发射器不注入 = 净释放帧零动作,下帧由
                    # 正常 EV 买入路径接手)。
                    for cand in cands:
                        _slots = (gs.shop.value.cards
                                  if gs.shop.value is not None else [])
                        _slot = (_slots[cand.slot_idx]
                                 if cand.slot_idx < len(_slots) else None)
                        _card = (_slot.card
                                 if _slot is not None
                                 and _slot.kind == 'content' else None)
                        if _card is None:
                            continue
                        _sw = _acquire_swap(_card, 'order_5')
                        if _sw is not None:
                            return _sw
                    _count('shop_ev_bench_wait')
                else:
                    _deferred = []
                    for cand in cands:
                        _slots = (gs.shop.value.cards
                                  if gs.shop.value is not None else [])
                        _slot = (_slots[cand.slot_idx]
                                 if cand.slot_idx < len(_slots) else None)
                        card = (_slot.card
                                if _slot is not None
                                and _slot.kind == 'content' else None)
                        if card is None:
                            continue
                        if mandate.sold_this_round(session, gs,
                                                   card.name or ''):
                            _count('ev_buy_round_sold_excluded')
                            continue
                        veto, _vkey = crit_buy.ev_buy_veto(cand, gold) \
                            if contracts.ensure_contract(
                                ('buy', 'ev_buy_veto'),
                                contracts.ContractCtx(gold=gold),
                                counters) \
                            else (True, '')
                        if veto and not _zone_hit:
                            continue
                        if gold < cand.cost:
                            continue
                        if veto:
                            _deferred.append(card)
                            continue
                        return _emit_buy(card, 'ev_buy')
                    if _deferred:
                        _count('must_spend_ev_deferred')
                        return _emit_buy(_deferred[0], 'ev_buy')
                    _count('shop_ev_all_vetoed')
            else:
                _count('shop_ev_no_candidate')

    # ===== 序 6:纯冗余停买(反向门——不命中任何序即停;邻位通道不受约束)=====

    # ===== C1 名单核心卡支(第 7 位邻位;席满恒买豁免价值比较)=====
    _core_victim_cache: list[tuple[BenchSlot | None, bool]] = []

    def _core_victim() -> tuple[BenchSlot | None, bool]:
        """(victim,可卖)帧内探测(victim = 首燃料候选,可卖 = 过
        check_irreversible;金闸双桶探测消费,现行语义)。"""
        if _core_victim_cache:
            return _core_victim_cache[0]
        _m4_excl = sell_gate.sell_exclusions(session, k_members,
                                             channel='m4_fuel',
                                             cap_hold=_cap_hold_now,
                                             current_round=int(
                                                 round_num_of(gs) or 1))
        _dp_rel = sell_gate.dead_pair_exit_release(
            session, k_members, bench, deployed,
            int(round_num_of(gs) or 1),
            cap_hold=_cap_hold_now, counters=counters)
        cands = mandate.fuel_sell_candidates(bench, k_members,
                                             state=gs,
                                             exclude_names=_m4_excl,
                                             defer_names=_t3_protect,
                                             counters=counters,
                                             dedup_names=_mm_dedup,
                                             merge_guard_release=_dp_rel)
        victim = cands[0] if cands else None
        ok4 = False
        if victim is not None:
            ok4, _ = mandate.check_irreversible(mandate._slot_cid(victim),
                                                k_members)
        if not ok4:
            victim = None
        _core_victim_cache.append((victim, ok4))
        return _core_victim_cache[0]

    _core_locked = _buy_members is not None
    # C1 候选过滤直判注册表(统一保护集 design §2.4:该处语义 = 「单卡
    # 核心身份」非「保护身份」,不迁移保护集口径——否则银狼等非四体系
    # 核心被逐出 C1;行为零变化)。
    _core_cands = [c for c in _buy_view('core_single_card_buy')
                   if (c.name or '') in CORE_SINGLE_CARD_REGISTRY
                   and (not _core_locked
                        or (c.name or '') not in buy_members)]
    if _core_cands:
        _count('core_candidate_seen')
        for card in _core_cands:
            cost = card_cost(card)
            if gold < cost:
                # 金闸双桶(现行观测语义保留;两桶均不卖不买)。
                victim, ok4 = _core_victim()
                _ref = _shop_sell_refund(victim) \
                    if victim is not None else None
                if ok4 and victim is not None and _ref is not None \
                        and gold + _ref >= cost:
                    _count('core_unaffordable_fundable')
                else:
                    _count('core_unaffordable_strict')
                continue
            if bench_free <= 0:
                # 席满恒买豁免价值比较(shop_session §2.2 第 7 条:C1
                # 支配语义 = 跳过置换直买,核心在售即买,腾位按序列末位
                # 让位自然发生——c1_make_room 场景评估器取首位直接卖;
                # 店内禁卖场上 → 只取备战席支)。
                _room, _why = evaluate_sell_candidates(gs, 'c1_make_room')
                _room_cand = next((c for c in _room
                                   if c.zone == 'bench'), None)
                if _room_cand is not None:
                    act = _emit_sell_cand(
                        _room_cand, reason='c1_make_room',
                        counter_key='c1_make_room_sell')
                    if act is not None:
                        _count('core_c1_make_room_sell')
                        return act
                _count('core_no_fuel')
                continue
            if not _core_locked:
                _count('core_unlocked_buy_hit')
                return _emit_buy(card, 'core_single_card_buy:unlocked')
            if contracts.ensure_contract(
                    ('mandate', 'core_single_card_buy_eligible'),
                    contracts.ContractCtx(locked_buy_members=_buy_members),
                    counters) and mandate.core_single_card_buy_eligible(
                        _core_locked):
                for card2 in _core_cands:
                    cost2 = card_cost(card2)
                    star2 = card2.star or 1
                    if not refund_full_star_ok(star2, cost2):
                        continue
                    if not predicates.t5_p1_false(
                            gold, cost2,
                            horizon.r_remaining(
                                session, plane_of(gs), round_num_of(gs)),
                            net_income(round_num_of(gs), 0),
                            cap_resolved):
                        continue
                    if gold < cost2:
                        victim, ok4 = _core_victim()
                        _ref = _shop_sell_refund(victim) \
                            if victim is not None else None
                        if ok4 and victim is not None and _ref is not None \
                                and gold + _ref >= cost2:
                            _count('core_locked_unaffordable_fundable')
                        else:
                            _count('core_locked_unaffordable_strict')
                        continue
                    if bench_free <= 0:
                        _room, _why2 = evaluate_sell_candidates(
                            gs, 'c1_make_room')
                        _room_cand2 = next((c for c in _room
                                            if c.zone == 'bench'), None)
                        if _room_cand2 is not None:
                            act = _emit_sell_cand(
                                _room_cand2, reason='c1_make_room',
                                counter_key='c1_make_room_sell')
                            if act is not None:
                                _count('core_c1_make_room_sell')
                                return act
                        _count('core_locked_no_fuel')
                        continue
                    _count('core_dominance_buy_hit')
                    return _emit_buy(card2, 'core_single_card_buy')
                else:
                    _count('core_numeric_fail_closed')

    # ===== dominance_buy(结算线口径;C1 后——相对顺序翻转申报:现行
    # dominance 先于 C1 → 新序 C1 核心支先、dominance 段后)=====
    _dom_narrow_counted = False
    _dom_ok = contracts.ensure_contract(
        ('mandate', 'dominance_buy'),
        contracts.ContractCtx(k_members=k_members, k_target=k), counters)
    if _dom_ok and mandate.dominance_buy_eligible(gold, bench_free,
                                                  cap_resolved):
        for card in _buy_view('dominance_buy'):
            name = card.name or ''
            cost = card_cost(card)
            star = card.star or 1
            if not name:
                continue
            if not predicates.zero_overlap(name, k_members):
                continue
            if mandate.dead_stock_pair_buy_reject_reason(
                    name, star, bench, deployed, k_members):
                _count('dominance_dead_stock_pair_blocked')
                continue
            if not refund_full_star_ok(star, cost):
                continue
            ok2, _ = mandate.check_seats(
                bench_free, 0, needs_bench=True, needs_board=False,
                name='', deployed_names=deployed_names)
            if not ok2:
                _count('dominance_bench_wait')
                break
            if gold < cost:
                continue
            _sl_ok, _ = check_settlement_line(gold, cost, g_star)
            if not _sl_ok:
                _count('dominance_settlement_floor_reject')
                continue
            if _narrow_frame:
                if not _dom_narrow_counted:
                    _count('press_narrowed_transition_domain')
                    _dom_narrow_counted = True
                continue
            return _emit_buy(card, 'dominance_buy')
    elif _dom_ok and gold > g_star and bench_free <= 1:
        _count('dominance_band_wait')

    # ===== 刷新链三组件:判据 → 金线闸 → 发射(shop_session §2.4;
    # 金线闸算式 = 2026-10-28 用户裁定刷新链定型;目标可买合取拆除 =
    # 统一让位优先级迭代 3.2 免费腿先行 + 3.4 预测门整拆)=====
    # W11 刷新负结果记忆(轻量形态,非期望式;设计 details/shop-buy-
    # reform.md §3):刷新提案被拒(金线不足;「目标不可买」置位分支已
    # 随预测门退役,design §2.2)→ 本帧置会话标记 + 照常收店;外循环
    # 重进商店入口观察时标记存在且状态三元组无变化 → 本帧跳过刷新提案
    # (按六序买面/关店走;免费腿与付费同闸——置位标记帧免费刷同跳),
    # 直至状态变化(节点推进/金变/席位变/星级目标完成)清标记。比对键
    # = (节点, 金, 席位快照, 星级目标键),节点推进与星级目标完成两清除
    # 条件以键内分量比对承载(标记字段本体不进节点边界重置表,值比对 =
    # shop_handled 同款双保险读法)。
    _block_key = _refresh_block_key(gs, gold, len(bench))
    if _st.refresh_blocked is not None \
            and _st.refresh_blocked != _block_key:
        _st.refresh_blocked = None
    if _st.refresh_blocked is not None:
        _count('shop_refresh_blocked_memory_skip')
    else:
        _free_left = gs.free_refresh_left.value
        if _free_left is not None and int(_free_left) > 0:
            # 免费刷新无条件刷(统一让位优先级迭代 3.2;design §2.2 免费
            # 刷新行为声明):分支内零阶段/带/目标/目标可买判据门,免费
            # 次数在册即刷——行为申报 = 唯一变化「目标可买」门删除,目标
            # 不可买(备战位满)帧从「拦下不耗次数」变「照刷耗次数」(免费
            # 不耗金,次数每节点重置/概率补给,低价值接受)。外层负结果
            # 记忆闸(上方记忆键比对跳过)免费与付费同闸照旧——金线不足
            # 置位帧不刷与现行一致;本分支不再置位记忆标记(「目标不可买」
            # 置位随预测门退役,付费腿置位分支同步删除)。计数达阈族失效
            # 钩子照挂(协议②)。
            shop_sess.note_refresh_counters(gs, 0)
            _mark_processing()
            return CwActionRefreshShopParam(cost=0,
                                            reason='free_refresh')
        _ok_w = False
        _wkey = 'contract_abstain'
        if contracts.ensure_contract(
                ('refresh', 'refresh_warranted'),
                contracts.ContractCtx(), counters):
            _ok_w, _wkey = crit_refresh.refresh_warranted(
                gs, session, k_members=k_members, counters=counters,
                dedup_names=_mm_dedup)
        if not _ok_w:
            # 拒因计数照落;「目标不可买」记忆置位分支删除(design §2.2:
            # 该置位随预测门退役——预测门本体 = refresh_warranted 内
            # target_buyable 合取,拆除归 3.4;收敛前该拒因仍可能命中,
            # 仅不再记忆置位:重入帧重复提案计数,动作面不变 = 拒后照常
            # 收店)。判据拒绝族其余键 = 升级优先/带外等资金序与阶段
            # 语义,循环终止由其自身承载,不入记忆(现行口径不变)。
            _count(f'shop_refresh_{_wkey}')
        else:
            # 金线闸:预留 = saturation_line + 停留目标实费档 ρ(2026-10-28
            # 用户裁定实费档实现口径:ρ = stay_target 实费档,变费卡随档;
            # 未锁窗口 stay_target 恒空 → ρ=0,金线 = g* + 刷价——两分支
            # 口径分行声明于判据本体)。整级预留分支删(同日裁定:升级概率
            # 带单判据
            # 后升级触发态与刷新放行态带互斥,预留腿不可达;凑金等待帧的
            # 刷新让位由判据①支「升级优先」直接承载——资金序 = 升级优先
            # 于刷新,升级推迟期刷新维持拒绝、不设解锁支,防「刷新烧凑金
            # → 升级永久 defer」饿死环)。
            _reserve = g_star + _r2_card_reserve(gs)
            if contracts.ensure_contract(
                    ('refresh', 'r2_budget'),
                    contracts.ContractCtx(gold=gold, reserve=_reserve),
                    counters):
                if crit_refresh.r2_budget(
                        gold, _reserve, refresh_cost_effective(gs=gs)):
                    shop_sess.note_refresh_counters(
                        gs, refresh_cost_effective(gs=gs))
                    _mark_processing()
                    return CwActionRefreshShopParam(
                        cost=refresh_cost_effective(gs=gs),
                        reason='star_target')
                # W11:金线不足拒绝同置标记(拒绝态关店,无状态变化不重入
                # 提刷——重入帧直接按六序/关店走,消除重复提刷白转帧)。
                if _zone_hit:
                    _count('must_spend_r1_budget_fail')
                _st.refresh_blocked = _block_key

    # ---- 收工(§2.5)----
    return _session_close(gs, _st, counters)
