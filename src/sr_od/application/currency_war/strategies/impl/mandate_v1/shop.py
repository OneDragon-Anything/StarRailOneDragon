"""cw4 商店线 decide_shop_action——步4b 商店线(单动作形态,ADR-0517)。

SIM_CONSUMPTION_MAP Q1:sim A/B 证明面 = 商店经济决策(买/卖/升/刷/事务)
——本模块是 mandate_v1 商店线的决策本体,黑板唯一输入 =
``session.shop_state_frame``(GameState,写者=商店入口观察段/单动作投影/
sim 引擎)。

商店单动作形态(ADR-0517;前身份 = 波批 decide_shop_wave,迁移批改型):

1. 方向(证明面投影):K = ``session.target_comp``(战略层 update_target 产物,
   见 bridge 透传声明)、stop_flag = proof.stop_buy、D-A45 干旱计数器;
   **K 空窗回退(2026-09-03 第三病灶修复;FIX_REVIEW_20260903 R3 扩域
   至三带)**:target_comp 为 None 时按带回退(单一源 cw_intention,禁
   复制)——P1 空窗带(支持度 < P1_PAIR_LOCK_MIN_SUPPORT)取
   ``hoard_target_set`` 四体系全集;P1 锁线过渡带(支持度 ≥门槛未锁帧)
   取 ``p1_early_pair_members`` top-2 方向;P2+ 带取 ``hoard_target_set``
   分带兜底(绯英⑤/跨线骨架/降格满配)。非 None 期行为不变;
2. 预算投影:cap_resolved 现读 → 守息线 g* = 10×cap_resolved(R70-1 参数化)
   + S 预留(P56 可变现息线下界 s_reserve := g* − Σ活期退金投影,设计
   13_buy_face_design §2.2)——单动作下输入金/席位 = 期望态当前值
   (动作后真值),「帧首快照 + 逐动作累积投影」口径随波批退役;
3. criteria 七面发射(§4.2.1 臂①旁路集:骨架面[M2/M3/M4/dominance/M6
   存在性]两臂同开,真 EV 发射面[ev_buy/付费刷新/凑息档]臂①旁路;
   支付支撑通道两臂同开,R13-5);
4. 终结集:RefreshShop(付费刷新)/ CloseShop(恒可用)——刷新是唯一
   引入新事实的动作,执行即本画面访问结束交回外循环重观察(ADR-0517
   决策 7;旧截断器的截断点语义被终结 op 吸收)。

R197 防线重定位(ADR-0517 §现行代码映射;防线存在前提 = 波批多动作共享
同一帧快照,单动作下按守卫断言语义重定位,详见 cw_shop_action_ops):
同槽去重(症3)/名-槽复检(症4①)/LevelUp 归一化(症4②)不再在发射侧
截断,proposal-vs-expected 断言在执行侧承接。

rng 中立:本模块零 rng 消费(SIM_CONSUMPTION_MAP ③-5 会话流派生契约);
registry 属性经 bridge 自带(Q3 坑位①)。

D-BUYNOTE(修复池执行层附注):M3 升级内嵌 P48 整买纪律
  (``criteria/levelup.spend_unified``,散买 XP 零收益拦截)。

计数键(session.cw4_counters,登记见 design_telemetry 键节——步4b 新键):
shop_ev_u_unavailable / shop_ev_shop_domain / shop_ev_no_candidate /
shop_ev_all_vetoed / shop_ev_bench_wait / shop_r1_ev_unavailable /
shop_visit_idle_gold /
shop_hard_node_gate_open / shop_drought_reset_on_buy /
shop_merge_trigger_truncate;K 空窗回退修复批(2026-09-03 第三病灶)
增补 shop_k_fallback_p1_gap(空窗帧回退计数);复审返工批
(FIX_REVIEW_20260903 R3)增补 shop_k_fallback_p1_lock_band(P1 锁线
过渡带回退计数)/shop_k_fallback_p2plus(P2+ 带回退计数)——三带
回退分键登记=design_telemetry「复审返工批」节。

键语义申报:``shop_visit_idle_gold`` = CloseShop 收尾且金 ≥10 的
**visit**(单动作迁移批自旧 ``shop_wave_idle_gold`` 改名——「波」结构
已退役;旧计数跨结构不可对拍,visit 含刷新段时旧波计数与其不等值,
判读须按新语义重建基线);``shop_ev_bench_wait`` = EV 候选在场但
bench 无空席、EV 买不提案的帧(席位门,与 dominance_bench_wait 同款)。

计数键粒度(ADR-0517 迁移步 2):各键从「每波一次」改「每决策帧一次」
(shop_drought_reset_on_buy 经 drought 值门维持「每访问至多一笔」);
``shop_merge_trigger_truncate``/``emitter_*`` 族随截断器退役(语义被
投影与终结 op 吸收)。R197 症6 的 funding need 注册表派生
(``mandate.cheapest_member_cost`` 单一源)原样保留。
"""
from __future__ import annotations

import contextlib
import math
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS, get_char
from sr_od.application.currency_war.data.cw_shop_odds import (
    expected_refreshes_for_card,
    refresh_prob,
)
from sr_od.application.currency_war.kernel import cw_intention
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    can_deploy_single,
    deploy_target_sets,
    deployed_bond_counts,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    clicks_to_next_level,
    xp_click_cost,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BENCH_CAPACITY,
    DEPLOYED_CAPACITY,
    REFRESH_COST_BASE,
    BenchChar,
    BuyCard,
    CloseShop,
    DeployMove,
    LevelUpShop,
    RefreshShop,
    SellBench,
    SellDeployed,
    bench_char_cost,
    sell_refund,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    entry,
    mandate,
    proof,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    buy as crit_buy,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import contracts
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    levelup as crit_levelup,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    refresh as crit_refresh,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    sell as crit_sell,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    stockpile as crit_stockpile,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
    horizon,
    predicates,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.income import (
    net_income,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
    loss_exact,
    saturation_line,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    refund_full_star_ok,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import (
        Comp,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        Action,
        BenchChar,
        GameState,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

# ===== 截断分类退役声明(ADR-0517 迁移批)=====
# 旧 _SHOP_CONTINUE/_SHOP_CONDITIONAL/_SHOP_TRUNCATION 三分类与
# ``truncate_shop_frame_stable`` 截断器已随波批形态退役——截断点语义被
# 终结 op 吸收(RefreshShop/CompTransaction 即终结,CloseShop 恒可用),
# 名-槽一致性复检降级为执行侧 proposal-vs-expected 守卫断言
# (cw_shop_action_ops;ADR-0517 决策 9 和解注)。


def _shop_sell_refund(bc: BenchChar) -> int | None:
    """卖出预期回金(sell_refund 口径;注册表 cost 缺失 ⇒ None=未标)。"""
    ch = CHARACTERS.get(bc.char_id or '')
    if ch is None or not ch.cost:
        return None
    return sell_refund(bc.star, ch.cost)


def _r1_ledger_terms(buy_members: tuple[str, ...],
                     bench: list, deployed: list,
                     level: int) -> tuple[float, int]:
    """R1 总账装配侧(ADR-0516 形式二):返回 (E(D|level), Σ卡费)。

    合格集 E = 未达 2★ 的线成员(目标阵容件,P40 A4);E(D|L) =
    Σ成员 expected_refreshes_for_card(L, cost, target_star=2, owned=j)
    (k=3 完成档;3★=9 与下一张=1 档在文档判据面声明,代码消费位与
    P40 ② 单卡代表形态同辖域取 2★ 档)。口径申报(出处→边界):
    - 成员集单源 = **buy_members**(F1 口径对齐:刷新追赶义务面与买入
      义务面同一集合——臂①囤腿落地后「买满三张」费用口径与行为
      (0→1→2→3 全链义务化)一致,§6.2 输入②申报的账面虚增随之消解;
      锁定帧 = locked_buy_membership 采购集,未锁帧 = k_members);
    - j = bench∪deployed 中该成员副本数(star≥2 = 成型即出域;
      j 低估 ⇒ E 高估 ⇒ 账高估 = 门收紧向,保守端申报);
    - c_taken=0(P40 待标定清单「缺则 0」;q 低估 ⇒ E 高估,同上
      保守向);
    - 该级不出此费(refresh_prob≤0)成员在该级不可追,E 记 inf
      (判据侧 isfinite 过滤 = R0-1 合格集空特例);
    - Σ卡费 = Σ合格成员 (k−j)×cost(k=3 完成档张数):完成路径真实卡费
      与 E 的 (k−j) 张折算同档——旧单张 cost 口径与 E 口径不一致已修齐
      (单成员 j=2 帧两口径相消,j<2 帧旧口径低估总账)。
    返回 (e_sum, card_fees);e_sum=inf 表示该级无可追成员(合格集空
    ——成员集空/全部 2★ 成型/该级全不可追 ⇒ inf,P40 R0-1 刷新侧
    特例由判据 isfinite 过滤承载)。
    """
    e_sum = 0.0
    card_fees = 0
    qualified_any = False
    for m in buy_members:
        ch = CHARACTERS.get(m)
        if ch is None or not ch.cost:
            continue
        copies = [c for c in list(bench) + list(deployed)
                  if (getattr(c, 'char_id', '') or '') == m]
        if any((getattr(c, 'star', 1) or 1) >= 2 for c in copies):
            continue                      # 已 2★:成员成型,出合格集(先于
                                          # 可追性判定——成型件不受该级
                                          # 出牌面辖制,禁污染其余成员账)
        if refresh_prob(level, ch.cost) <= 0.0:
            e_sum = float('inf')
            continue                      # 该级不出此费:不可追(P40 R0)
        qualified_any = True
        j = len(copies)
        e_sum += expected_refreshes_for_card(level, ch.cost, target_star=2,
                                             owned=j)
        card_fees += max(0, 3 - j) * int(ch.cost)   # (k−j)×cost,k=3 完成档
    if not qualified_any:
        return float('inf'), 0
    return e_sum, card_fees


def _r2_card_reserve(k_members: tuple[str, ...],
                     bench: list, deployed: list,
                     state: GameState,
                     level: int | None = None) -> int:
    """R2 预算门 Σ预留卡价 ρ = 合格集最低费卡价(修 R2 批)。

    可追过滤等级:缺省=当前级;R2 消费位在 R1 选定 L* 之后,调用方
    (decide_shop_wave R1 段)按 L* 重估传入——R1 已选等级的出牌面辖
    R2 预留卡价,量级=一张卡价(用当前级过滤会在 L*≠当前级帧错档)。

    证明单一源 = p54-r2-interest-floor §②(零新自由参数:ρ 锚
    CHARACTERS 注册表 cost,非字面量)。可追过滤与 ``_r1_ledger_
    terms`` 同一(该级出此费 refresh_prob>0 ∧ 无 2★)——语义
    单一源不复制。单卡下界口径(P54 A2:P40 待标定清单「最低费卡价
    × 期望命中数」在单刷波粒度下的整数下界;多命中超出部分 = 下一波
    R2 重估补足的显式让渡,非破线刷新)。合格集空 ⇒ 0:该帧 R1 必先
    以 no_chaseable_member 关闭,R2 不可达,兜底值不进任何可达比较。
    """
    level_now = int(state.level or 1) if level is None else int(level)
    costs: list[int] = []
    for m in k_members:
        ch = CHARACTERS.get(m)
        if ch is None or not ch.cost:
            continue
        if refresh_prob(level_now, ch.cost) <= 0.0:
            continue
        copies = [c for c in list(bench) + list(deployed)
                  if (getattr(c, 'char_id', '') or '') == m]
        if any((getattr(c, 'star', 1) or 1) >= 2 for c in copies):
            continue
        costs.append(int(ch.cost))
    return min(costs) if costs else 0


def _frame_search_windows(session: StrategySession, state: GameState,
                          registry, counters: dict) -> tuple[frozenset[int],
                                                            frozenset[int]]:
    """帧级搜索窗口(T1;设计 13_buy_face_design §2.3/§3.2)。

    窗口判据重锚(ADR-0516 形式二;V̄ 链退役):旧 V̄ 门式
    (``vbar.window_vbar`` 帧级现算 + P57 双读法参数化)随 V̄ 比较项
    一并退役,窗口改为塌缩带锚——费档在窗内 ⟺ 该级命中率 ≥ ω×峰值级
    命中率(``statefn/odds.tier/card_search_window``,ω 锚与
    ADR-0475 refresh_ev_budget 归零腿同源),全游戏定义量(REFRESH_PROB
    表 + 峰值查表 + 注册表 ω 字段)。空集语义 = 真无窗口帧(该级全部
    费档塌缩),非门控。P57 读法分歧随单一判据消解(文档面声明)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.odds import (
        card_search_window,
        tier_search_window,
    )
    level = int(state.level or 1)
    omega = registry.omega_collapse_ratio
    return (tier_search_window(level, omega),
            card_search_window(level, omega))


def shop_unbought_reasons(state: GameState,
                          comp: Comp | None,
                          k_members: tuple[str, ...],
                          actions: list[Action]) -> dict[str, str]:
    """商店波未买牌拒因串(决策帧遥测字段 ``shop_rejects`` 的生产端)。

    为什么:复盘 g_20260904_031925 把在售 transition 件「花火」误读成
    线内核心件「火花」(花火≠火花:花火=2费盛会之星辅助,cw_chars 注册
    表 source=6401;火花=4费星间旅人、绯英欢愉 shared 成员,source=7001
    )——当时决策帧只有 fp 值、无任何 per-card 分类,判读者只能猜「哪道
    门拒了」。本函数对店面每张未买牌给一个归属/拒因标签,让「线内未买
    (哪道门拒)」与「线外归属(刻意不买)」在决策帧内可辨:

    - 线内缺口件(K 想买而未买):``missing_unaffordable``(金不足)/
      ``missing_bench_full``(席满且无可腾燃料件)/ ``missing_no_path``
      (金席俱足仍未发射 = 异常态:发射被截断丢弃等,须查);
    - 线内已持有:``owned``;
    - transition_chars(打工后卖、刻意不入线——单一源 = cw_comps 注册表
      + ``predicates.line_members`` 只取 core∪shared):``transition_char``;
    - 其余:``non_line``。

    口径 = 帧首静态快照 + 逐动作累积投影:金按已发射 BuyCard 总价扣减、
    SellBench/SellDeployed/DeployMove 的席与回金同步投影(修复:旧版只投影
    金不投影席——M2 波内先买的成员占掉末席后,同波后续线内件被席闸跳过,
    会被误标成 missing_no_path 而非 missing_bench_full,复盘归因失真)。
    拒因串是判读线索,非审计账(精确门序以 shop_ev_*/m2_* 各计数键为准)。
    comp 为 None(K 空窗回退带)时 transition 分类不可得,统一 ``non_line``。

    双栈语境声明(sim 判读必读):本函数的拒因语义(「金席俱足仍未发射
    =异常态」)以 cw4 M2 义务通道为参照系——M2 对线内缺件是义务买入,
    唯一合法拦截集=金/席硬闸+发射截断。sim 引擎(engine_p1)每决策段用
    本函数对 **decision_v2 栈**的原始决策打标:decision_v2 的愿买集由候选
    评分/copies_cap/预算投影(s_reserve 等)决定,线内在售未买多为合法
    评分裁决而非异常——sim 面的 missing_no_path 须先查 decision_v2 侧
    拒因(评分/上限/预算),不能按 cw4 义务语义直接定谳「异常态」。
    """
    bench = [b for b in (state.bench or []) if b is not None]
    deployed = [d for d in (state.deployed or []) if d is not None]
    owned = ({b.char_id or '' for b in bench}
             | {d.char_id or '' for d in deployed})
    gold = int(state.gold or 0)
    bench_free = BENCH_CAPACITY - len(bench)
    for a in actions:
        if isinstance(a, BuyCard):
            gold -= a.card.cost if a.card.cost else 3
            bench_free -= 1
        elif isinstance(a, (SellBench, SellDeployed)):
            # 卖出投影:席释放 + 回金(SellBench.income 缺失按 0 保守——
            # 金低估只会把拒因推向 unaffordable 侧,不会造假 no_path)
            bench_free += 1
            income = getattr(a, 'income', None)
            if income:
                gold += income
        elif isinstance(a, DeployMove):
            bench_free += 1     # bench→board:席释放(SwapDeploy 一进一出净 0)
    trans = (set(getattr(comp, 'transition_chars', []) or [])
             if comp is not None else set())
    bought_names = {a.card.name or '' for a in actions
                    if isinstance(a, BuyCard)}
    out: dict[str, str] = {}
    for card in (state.shop or []):
        name = card.name or ''
        if not name or name in out or name in bought_names:
            continue
        if name in k_members:
            if name in owned:
                # 线内已持有帧按持有形态细分拒因(与同帧实际动作一致):
                # - 合并完成段(cnt=2 ∧ 无 2★):§3.6 满栏例外后买入直发
                #   (免 bench_free 门),'merge_bench_full' 键退役;金不足
                #   仍记 merge_unaffordable,金席俱足未发 = merge_ready
                #   (判读关注面);
                # - 臂①囤腿段(cnt1=1 ∧ 无 2★,§3.2):中性 'owned' 退役
                #   ——同帧实际动作 = m2_stockpile 义务买入,拒因按其门序
                #   细分(stockpile_bench_full/stockpile_unaffordable/
                #   stockpile_ready),§7.3 owned 命中占比观测面随之真实;
                # - 其余(含 cnt2>0 让渡死库存,§3.7):中性 'owned'。
                copies = [c for c in bench + deployed
                          if (c.char_id or '') == name]
                cnt1 = sum(1 for c in copies if (c.star or 1) == 1)
                cnt2 = len(copies) - cnt1
                cost = min((c.cost if c.cost else 3)
                           for c in (state.shop or [])
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
            cost = min((c.cost if c.cost else 3) for c in (state.shop or [])
                       if (c.name or '') == name)
            if bench_free <= 0:
                out[name] = 'missing_bench_full'
            elif gold < cost:
                out[name] = 'missing_unaffordable'
            else:
                out[name] = 'missing_no_path'
        elif name in trans:
            out[name] = 'transition_char'
        else:
            out[name] = 'non_line'
    return out


def decide_shop_action(state: GameState, session: StrategySession,
                       config: object, *, registry=None) -> Action:
    """商店单动作决策(ADR-0517 决策 1/2;前身份 = ``decide_shop_wave`` 波批)。

    契约:**全函数**——f(期望态) → 恰一个动作,永不返回 None(决策 5);
    「无动作可做」= 返回 ``CloseShop`` 终结动作(决策 4/6,取代旧「空序列
    = 决策完成」通道)。画面内合法性全部内化于本函数(决策 2 和解注:以
    期望态为据只提合法动作);执行侧只余守卫断言(cw_shop_action_ops)。

    选择序 = 既有波批优先级逐帧取首项(ADR-0517 §映射,序不变):
    M4 腾席 → M2 线成员(含 M2b 合并完成)→ dominance → M3 升级(单击)
    → M6 溢余 → EV 买面 → R1 付费刷新(终结)→ 凑息卖 → 支付支撑卖
    → CloseShop(终结)。输入 ``state`` = 期望态当前值(动作后真值,
    ADR-0517 §8.1 裁决:契约核验与决策同源消费此值,禁帧首快照口径)。

    计数键粒度声明(ADR-0517 迁移步 2):``session.cw4_counters`` 各键
    语义从「每波一次」改「每决策帧一次」;跨结构对比(A/B 或回归判读)
    须声明口径切换,禁把两粒度计数直接对拍。拒因遥测
    (``session.cw4_shop_rejects``)同样逐帧刷新——期望态即投影后真值,
    无累积投影账,``actions`` 传空列表(买走的牌已从 state.shop 摘除)。
    M3 粒度(ADR-0517 决策 3 + §权衡):升一级 = 一个动作 op,clicks
    序列是动作内部步骤;单动作形态下每帧恰发一个单击动作,下一帧以更新
    后的 xp/level 重判(spend_unified 逐次校验整批可负担,可负担面单调
    ⇒ clicks 序列逐次全过,P48 整买纪律不破)。
    """
    if getattr(session, 'cw4_counters', None) is None:
        session.cw4_counters = {}
    counters: dict = session.cw4_counters

    # 备战期开店闩置位(唯一写点;键与 mandate.run_mandate 的 phase 同式):
    # 本函数被调 = 开店动作真执行、商店域决策访问已发生——闩语义
    # 「本备战期商店已被访问,期内重开无信息量」的记账位在访问发生,
    # 不在 mandate 发射位(备战环单动作环下发射≠执行,发射列表中
    # OpenShop 前的可续动作先执行即终结本环、OpenShop 未执行;发射即
    # 置闩会让闩烧而店未开、后续环被闩挡死空批出战。实证与修法裁决 =
    # run_mandate docstring「备战期开店闩」节 + dd-027 同型残留)。
    # read_only 开店(纯读数,不进本函数)不消耗闩:读数访问不改店面,
    # 期内买入决策仍待发。位面/轮次推进=新键自动失效,与 mandate 侧同。
    session.cw4_shopped_phase = (getattr(state, 'plane', None),
                                 getattr(state, 'round_num', 1))

    def _count(key: str) -> None:
        counters[key] = counters.get(key, 0) + 1

    ev_arm = getattr(config, 'ev_arm', 'full')
    if ev_arm not in entry.EV_ARM_VALUES:
        ev_arm = 'full'
    skeleton_only = (ev_arm == 'skeleton_only')

    # ---- ① 方向(证明面投影;契约核验 = 单动作决策入口,动作后真值口径)----
    k = getattr(session, 'target_comp', None)
    k_members = predicates.line_members(k)
    k_fallback: frozenset[str] | set[str] | None = None
    k_band: str | None = None
    _ist = getattr(session, 'v3_intention', None)
    if k is None and _ist is not None:
        # K 空窗回退(FIX_REVIEW_20260903 R3 扩域;经济冻结批单一源化):
        # 派生本体 = cw_intention.k_empty_window_fallback(商店域与准备域
        # 共用,禁第二源);本处只保留消费面(回退采用+计数键)。ist 缺失
        # = 意向供给缺帧,保守侧不回退(现行 () 行为)。
        k_fallback, _tok = cw_intention.k_empty_window_fallback(state, _ist)
        k_band = f'shop_k_fallback_{_tok}'
    # 契约核验(可核验派生形态):回退字面量空元组但保留声明 = 违例 ⇒
    # 不回退 + 计数。sorted = 确定性发射序(str 哈希随机化防御)。
    if contracts.ensure_contract(
            ('shop', 'k_projection'),
            contracts.ContractCtx(k_target=k,
                                  k_fallback_available=_ist is not None,
                                  k_fallback_resolved=k_fallback),
            counters) and k_fallback:
        k_members = tuple(sorted(k_fallback))
        _count(k_band)
    # 锁定帧(locked_comp 非空)买面口径拆分(买面/卖免面/刷新账三面
    # 分参数,单一源 = cw_intention.locked_buy_membership):
    # - 买入义务集 ``buy_members``(M2 缺员循环、M2b 合并完成买入、拒因
    #   遥测)= 锁定采购集(含锁定 comp 的阵营∪流派成员)——购买侧与
    #   锁定侧同源,锁内成员经 M2 义务买入、不再落 non_line 拒因(实机
    #   对局 g_20260905_035710 锁「列车同行」后锁内阵营成员被拒的
    #   双源断裂修复);
    # - ``k_members`` 保持 comp core∪shared 口径(M4 fuel_sell_candidates/
    #   funding_support_sell 的 zero_overlap 卖免判定、R1/R2 刷新账合格集
    #   P40 A4「目标阵容件」口径)——锁定全集若灌入卖免面,bench 被
    #   hoard 低星成员塞满后腾席候选空集、缺员买不进(滞留换拍复发);
    #   灌入刷新账则判据行为翻转无数学重推背书。两处均按「无证明重推
    #   不翻转」维持原口径。
    # 未锁帧两集相等(locked_buy_membership 返回 None),P1 无锁态零变化。
    _buy_members = cw_intention.locked_buy_membership(_ist)
    buy_members = tuple(sorted(_buy_members)) if _buy_members else k_members
    # P60 容量超限告警门(帧级计数):|buy_members| > bench+板容量上界
    # = 义务集出口(missing=∅)结构性不可达的形态——诚实停摆可判读的
    # 前提是该形态可见。
    if _buy_members and len(_buy_members) > BENCH_CAPACITY + DEPLOYED_CAPACITY:
        _count('shop_hoard_over_capacity')
        log.warning('[cw!][shop] 锁定采购集 |B|=%d > 容量上界 %d:缺员出口'
                    '结构性不可达,换手循环诚实停摆形态(证据=换手对/'
                    'm2_retry_exhausted 计数)', len(_buy_members),
                    BENCH_CAPACITY + DEPLOYED_CAPACITY)
    bench = [b for b in (state.bench or []) if b is not None]
    deployed = [d for d in (state.deployed or []) if d is not None]
    bench_names = [b.char_id or '' for b in bench]
    deployed_names = [d.char_id or '' for d in deployed]
    owned = set(bench_names) | set(deployed_names)
    # 契约核验:stop_buy 消费位(前提恒真 None 登记,违例路径仅剩未登记键)
    stop_flag = proof.stop_buy(k, bench_names, deployed_names) \
        if contracts.ensure_contract(
            ('proof', 'stop_buy'), contracts.ContractCtx(), counters) \
        else True   # 弃权侧=保守停买——辖域限支配买/溢余面;M2 义务不走
                        # 停手门([41]),不受本弃权影响

    # ---- ② 预算投影(期望态当前值;帧首快照口径随波批退役,ADR-0517
    # §消灭的 bug 类·金位买后投影族——期望态金即动作后真值,无口径可言)----
    cap_resolved = mandate._cap_of(session)
    g_star = saturation_line(cap_resolved)
    # P56 可变现息线下界(设计 13_buy_face_design §2.2):s_reserve :=
    # g* − Σ活期退金投影;活期集合以期望态现值计(M4 卖出的活期件在下一
    # 决策帧自然离开集合——旧「帧内即时扣减」专修无存在载体)。
    liquid_refund = sum(sell_refund(1, bench_char_cost(b))
                        for b in mandate.fuel_sell_candidates(
                            bench, k_members, state=state,
                            exclude_names=buy_members))
    s_reserve = g_star - liquid_refund
    _reg = registry
    if _reg is None:
        from sr_od.application.currency_war.kernel.cw_registry import (
            DEFAULT_REGISTRY,
        )
        _reg = DEFAULT_REGISTRY
    tier_w, card_w = _frame_search_windows(session, state, _reg, counters)
    gold = int(state.gold or 0)
    bench_free = BENCH_CAPACITY - len(bench)
    # 拒因遥测逐帧刷新(ADR-0517 迁移步 2:拒因计数键逐动作化;期望态
    # 即真值,actions 传空——买走牌已由 project 从 state.shop 摘除)。
    with contextlib.suppress(Exception):
        session.cw4_shop_rejects = shop_unbought_reasons(
            state, k, buy_members, [])
    missing = [m for m in buy_members if m not in owned]

    def _shop_candidates(m: str):
        return sorted(
            (c for c in (state.shop or []) if (c.name or '') == m),
            key=lambda c: (c.cost if c.cost else 3))

    # ---- ③ 选择序逐帧取首项 ----

    def _on_target_buy(bought_name: str = '') -> None:
        """D-A45 商店侧半边:买入目标件 ⇒ 干旱计数器重置 + 事件计数。

        计数粒度 = 每 visit 至多一笔(旧口径为每波;visit 含刷新段时
        行为等效但计数粒度不等效—— drought 已 0 帧跳过计数,跨结构
        对拍须声明口径差异)。

        ``bought_name`` 传入时查近期卖出记认(``cw4_recent_sold_names``,
        本 visit 内卖出件名集):买回近期卖出成员 = 义务换手买入,drought
        重置按来源分键(P60 伪装进展观测面)——换手买动作不得与真实
        缺员买入共用同一「进展」信号。
        """
        churn = bool(bought_name) and bought_name in getattr(
            session, 'cw4_recent_sold_names', ())
        if churn:
            _count('shop_churn_pair_buy')   # 换手对:与 drought 状态无关恒计
        ls = getattr(session, 'cw4_line_state', None)
        if ls is not None and getattr(ls, 'drought', 0):
            ls.drought = 0
            _count('shop_drought_reset_on_churn_buy' if churn
                   else 'shop_drought_reset_on_buy')

    def _note_sell(name: str) -> None:
        """卖出记认(P60 换手对观测面):本 visit 卖出件名入近期卖出集,
        后续买入命中 = 义务换手对。定长截断防长 visit 无界增长。"""
        if not name:
            return
        recent = getattr(session, 'cw4_recent_sold_names', None)
        if recent is None:
            recent = []
            session.cw4_recent_sold_names = recent
        recent.append(name)
        del recent[:-16]

    # M4 腾席(买入遇 bench 满:现场卖 1 燃料件,R8-8 单帧闭环)。
    # P60:燃料集排除 buy_members(exclude_names)——义务换手通道闭死,
    # |B|>容量时走 m2_retry_exhausted 诚实停摆而非永恒卖 1 买 1。
    if missing and bench_free <= 0:
        cands = mandate.fuel_sell_candidates(bench, k_members, state=state,
                                             exclude_names=buy_members)
        if cands:
            victim = cands[0]
            ok4, _ = mandate.check_irreversible(victim.char_id or '', k_members)
            if ok4:
                idx = (state.bench or []).index(victim)
                _note_sell(victim.char_id or '')
                return SellBench(bench_idx=idx,
                                 income=_shop_sell_refund(victim),
                                 expect=victim.char_id or '')
        else:
            _count('m2_retry_exhausted')

    # M2 线成员买入(序 1/2 义务;[41]:义务不走息律门)。金不足侧:
    # 支付支撑通道在 R1 拒后的发射位处理(卖一张回此帧重判)。
    if bench_free <= 0 and missing:
        _count('bench_full_buy_abandon')
    for m in missing:
        if bench_free <= 0:
            break
        shop_cands = _shop_candidates(m)
        if not shop_cands:
            continue
        card = shop_cands[0]
        cost = card.cost if card.cost else 3
        ok1, _ = mandate.check_affordable(gold, cost)
        if not ok1:
            continue
        _on_target_buy(card.name or m)
        return BuyCard(card=card, reason='m2_line_member')

    # m2_stockpile(臂①囤腿,j=1 第二份;14号稿 §3.2-3.4,发射位次 =
    # M2 主循环之后、M2b 之前,理由键 'm2_stockpile'):
    # 成员集分叉声明(编排者存-2 裁决 = 有意设计):本臂循环 buy_members
    # (锁定采购集超集)而 arm0_need 只量 k_members——囤腿件走合成→上板,
    # 部署/升级授权面只量可部署现量,两口径禁混。
    # 触发 = m ∈ buy_members ∧ cnt1(m)==1 ∧ cnt2(m)==0(二-1:cnt2>0 帧
    # 臂①不判,防制造 cnt1=2∧有2★ 死库存)∧ 店内有该成员 **1★** 在售
    #(N7 星过滤:候选锚按 name 过滤不分星,店含同名 2★ 直出卡会取错);
    # 单提案至多购 1 张(F2 防御性上限——merge §2.5 自动多买在 j=1 帧的
    # 辖域未核,宁少买不多买,确认后如允许多买走规格修订)。
    # 拒因序 = 金闸前置 → M4 腾席(落地审清单存-1,20260905_cp1_landing_review/问题清单.md:j=1 囤腿优先级低于缺员,
    # 满栏+金不足帧禁「先卖燃料件再报 unaffordable」的不可逆净损);拒因
    # 计数粒度申报 = 每成员命中一笔(帧内多成员可累计,与 visit 粒度键
    # 对拍时须声明,清单低-2)。bench 满 → M4 腾席(Y5:02 §3 M2 硬约束
    # 同构,腾席后仍满记 'bench_full' 普通席闸键,非 merge_bench_full);
    # 金不足记 stockpile_unaffordable;cnt 达标但店内仅同名 2★ 直出卡 ⇒
    # m2_stockpile_star_mismatch 分键(W4 零静默,与 M2b 分键,清单低-1)。
    def _cnt(name: str, star: int) -> int:
        """同名同星副本计数(全局面 bench∪deployed;14号稿 §3.5 单一源:
        按 (名,星) 分星计数,2★ 成件不折算 1★)。"""
        return sum(1 for c in bench + deployed
                   if (c.char_id or '') == name and (c.star or 1) == star)

    for m in buy_members:
        if _cnt(m, 1) != 1 or _cnt(m, 2) != 0:
            continue
        all_cands = _shop_candidates(m)
        cands1 = [c for c in all_cands if (c.star or 1) == 1]
        if not cands1:
            if all_cands:
                _count('m2_stockpile_star_mismatch')   # W4:仅 2★ 直出卡帧,分键非静默
            continue
        card = cands1[0]
        cost = card.cost if card.cost else 3
        ok1, _ = mandate.check_affordable(gold, cost)
        if not ok1:
            _count('stockpile_unaffordable')
            continue
        if bench_free <= 0:
            # M4 腾席(Y5):j=1 帧不合成,满栏例外不辖;卖 1 燃料件
            #(P60 排除集照常)后下一帧 bench_free ≥ 1 即合法买入。
            cands = mandate.fuel_sell_candidates(bench, k_members,
                                                 state=state,
                                                 exclude_names=buy_members)
            victim = cands[0] if cands else None
            if victim is not None:
                ok4, _ = mandate.check_irreversible(victim.char_id or '',
                                                    k_members)
            else:
                ok4 = False
            if victim is not None and ok4:
                idx = (state.bench or []).index(victim)
                _note_sell(victim.char_id or '')
                return SellBench(bench_idx=idx,
                                 income=_shop_sell_refund(victim),
                                 expect=victim.char_id or '')
            _count('bench_full')
            continue
        _on_target_buy(card.name or m)
        return BuyCard(card=card, reason='m2_stockpile')

    # M2b 升星合并完成买入(实机复盘 g_20260904_054904 p2r1 候选②):
    # 已持 2 张同名同星 1★、无 2★ 成件,第三张在店 affordable ⇒ 买入即
    # 合成 2★。义务通道不走息律门([41] 同 M2)。
    # Y4:候选 star==1 过滤——同名异星不合成(merge §1 凑满 3 指同名
    # 同星),×3 价买 2★ 直出卡不成链且制造 §3.7 让渡死库存;仅 2★ 直出
    # 卡帧 star_mismatch_skip 分键(W4 零静默)。
    # §3.6 席位门满栏例外对齐(B2):本循环形态已保证「买入即触发合成」
    #(同名同星 2→3),机制上买入后全局面同名同星 3→1 净席 −1,无溢出
    # 散牌 ⇒ 免 bench_free 门(与机制对齐,非行为放宽;理由键不变;
    # 机制出处=merge_mechanics.md §2.5 满栏例外+§2.5 上限「绝不多买」)。
    for m in buy_members:
        copies = [c for c in bench + deployed if (c.char_id or '') == m]
        if len(copies) != 2 or any((c.star or 1) >= 2 for c in copies):
            continue
        all_cands = _shop_candidates(m)
        shop_cands = [c for c in all_cands if (c.star or 1) == 1]
        if not shop_cands:
            if all_cands:
                _count('m2b_star_mismatch')   # W4:仅 2★ 直出卡帧(与臂①分键,低-1)
            continue
        card = shop_cands[0]
        cost = card.cost if card.cost else 3
        ok1, _ = mandate.check_affordable(gold, cost)
        if not ok1:
            continue
        _on_target_buy(card.name or m)
        return BuyCard(card=card, reason='m2_merge_completion')

    # dominance_buy(P24 零参数,两臂同开;金口径 = 期望态现值——单动作下
    # 每帧金即买后真值,R197 症9 的投影口径问题无存在载体)。
    _dom_ok = contracts.ensure_contract(
        ('mandate', 'dominance_buy'),
        contracts.ContractCtx(k_members=k_members), counters)
    if _dom_ok and mandate.dominance_buy_eligible(gold, bench_free,
                                                  stop_flag, cap_resolved):
        for card in (state.shop or []):
            name = card.name or ''
            cost = card.cost if card.cost else 3
            star = card.star or 1
            if not name:
                continue
            if not predicates.zero_overlap(name, k_members):
                continue
            if not refund_full_star_ok(star, cost):
                continue            # 支配性背书仅全额可退 1★(P24)
            ok2, _ = mandate.check_seats(
                bench_free, 0, needs_bench=True, needs_board=False,
                name='', deployed_names=deployed_names)
            if not ok2:
                _count('dominance_bench_wait')
                break
            ok1, _ = mandate.check_affordable(gold, cost)
            if not ok1:
                continue
            return BuyCard(card=card, reason='dominance_buy')

    # M3 升级(触发信号三臂并联;D-BUYNOTE:P48 整买纪律内嵌)。单动作
    # 粒度:每帧恰发一个「购买经验」单击动作(升一级 = 一个动作 op,
    # clicks = 动作内部步骤,外部买面不可插花——ADR-0517 §权衡)。
    # 双栈同义面声明(落地审清单阻-1/应-2,20260905_cp1_landing_review/问题清单.md):本块与备战批栈
    # (mandate.run_mandate M3)消费同一组触发臂——
    # arm1_existence(板满∧bench 有候补)/ arm0_level_lag(等级落后于
    # 上阵人数需求,need = 期望态现量 (名,星) 口径 Y3,level 消费
    # level_readable C4)/ pop_slot(D-lv7 满编+富金+候补升 cap;§4.3
    # 前置放宽「bench 有候选 ∨ 买得起候选」,买得起 = affordable ∧
    # bench_free≥1)——「板满+bench 空+富金」病灶场景的商店帧升级授权
    # 由 arm0/pop_slot 承载(arm1 在该形态恒 False)。
    _cap_now = state.max_units()
    _lvl_readable = bool(getattr(state, 'level_readable', True))
    _arm1_ok = contracts.ensure_contract(
        ('predicates', 'arm1_existence'),
        contracts.ContractCtx(deploy_cap=_cap_now), counters)
    _arm1 = bool(_arm1_ok and predicates.arm1_existence(
        len(deployed), bench_names, deployed_names, _cap_now))
    _arm0 = False
    if contracts.ensure_contract(
            ('predicates', 'arm0_level_lag'),
            contracts.ContractCtx(), counters):
        _arm0, _arm0_key = predicates.arm0_level_lag(
            int(state.level or 1), _lvl_readable, deployed, bench,
            k_members, _cap_now)
        if not _arm0 and _arm0_key == 'level_unreadable':
            _count('arm0_level_unreadable')
        elif _arm0 and _cap_now is None:
            _count('arm0_cap_unreadable')   # 存-3:cap 不可读静默弃权补分键
            _arm0 = False
    _pop = False
    if contracts.ensure_contract(
            ('levelup', 'pop_slot'), contracts.ContractCtx(), counters):
        _bench_cand = sum(1 for n in bench_names if n in k_members)
        _buyable_cand = bench_free >= 1 and any(
            (c.name or '') in k_members
            and mandate.check_affordable(
                gold, c.cost if c.cost else 3)[0]
            for c in (state.shop or []))
        _pop, _pop_why = crit_levelup.pop_slot(
            len(deployed), _cap_now, gold, _bench_cand, g_star,
            buyable_candidate=_buyable_cand, bench_free=bench_free)
        session.cw4_pop_slot_why = _pop_why   # D-lv7:否向理由留决策迹
    if _arm1 or _arm0 or _pop:
        # auth_basis 三臂分键(可归因):触发臂按 arm1 > arm0 > pop 序取首
        _arm_tag = 'arm1' if _arm1 else ('arm0' if _arm0 else 'pop')
        if contracts.ensure_contract(
                ('levelup', 'level_spend_blocked'),
                contracts.ContractCtx(), counters) \
                and crit_levelup.level_spend_blocked(state, session, _reg):
            _count('crisis_level_spend_defer')
        elif contracts.ensure_contract(
                ('levelup', 'lv9_stop'), contracts.ContractCtx(), counters) \
                and not crit_levelup.lv9_stop(state.level):
            clicks = clicks_to_next_level(state)
            cost = xp_click_cost(state)
            if contracts.ensure_contract(
                    ('levelup', 'spend_unified'),
                    contracts.ContractCtx(gold=gold), counters) \
                    and crit_levelup.spend_unified(clicks, gold, cost):
                ok1, _ = mandate.check_affordable(gold, 0,
                                                  batch_cost=clicks * cost)
                if ok1 and clicks > 0:
                    return LevelUpShop(cost=cost,
                                       auth_basis=f'm3_batch:{_arm_tag}')

    # M6 溢余转压库(存在性=金>g* ∧ 无 S 目标;档匹配 fail-closed ⇒
    # 不买 + 溢余滞留遥测;两臂同开)
    if gold > g_star and stop_flag and bench_free > 0:
        ok2, _ = mandate.check_seats(
            bench_free, 0, needs_bench=True, needs_board=False,
            name='', deployed_names=deployed_names)
        if not ok2:
            _count('m6_bench_full')
        elif not tier_w:
            _count('m6_overflow_strand')
        else:
            _stock_ok = contracts.ensure_contract(
                ('stockpile', 'stockpile_buy'),
                contracts.ContractCtx(k_members=k_members), counters)
            for card in (state.shop or []):
                name = card.name or ''
                # 线内追星段排除(落地审清单存疑收口,N2/§3.7):线内副本
                # 的买入全链归义务通道(M2 j=0→1 / 臂① j=1∧cnt2=0 / M2b
                # j=2 完成段,§3.4 边界表)——M6 压库若买线内 1★ 副本会
                # 绕过臂① cnt2==0 守卫制造「cnt1=2∧有 2★」死库存
                #(§3.7 让渡形态)。压库域收窄为非线内件,分键零静默。
                if name in buy_members:
                    _count('m6_line_member_excluded')
                    continue
                cost = card.cost if card.cost else 3
                okm, _mkey = crit_stockpile.stockpile_buy(
                    gold, s_reserve, bench_free, cost,
                    card.star or 1, tier_w) if _stock_ok else (False, '')
                if not okm:
                    if _mkey == 's_reserve':
                        _count('m6_s_reserve_reject')
                    continue
                ok1, _ = mandate.check_affordable(gold, cost)
                if not ok1:
                    continue
                return BuyCard(card=card, reason='m6_stockpile')

    # ---- 出口③(Φ_stall 过渡件垫件出口;17 号稿 §2.3/§7.3-§7.5,消费位
    # = 11 §7.3 垫底级辖域扩展:「未锁线期」→「+ 锁线后 Φ_stall 帧」;
    # 与 14 号稿 §5.2(b)2 同消费位两触发源,Z1 确认批落地后按 ∨ 合并)。
    # 授权条件(§7.3 定稿,全量结构计数/注册表派生界,零自由参数):
    # Φ_stall(四支) ∧ 垫件在售 ∧ bench_free ≥ 1 ∧ g − cost ≥ s_reserve
    # ∧ 围栏预检放行(can_deploy_single 单一源,禁第二套围栏语义)。
    # 授权定性(ADR-0525):净成本 ≤1 金(注册表派生界:Δ息∈{0,1})的
    # 有界成本结构改善授权;严格支配仅 Δ息=0 帧,禁回退「无条件授权」。
    # 发射序 = M4 腾席后(§7.5-②4);垫件买入即登记
    # session.cw4_fuel_filler_stall_buys(N3 闭环登记契约)。
    # 七分键零静默:fuel_filler_stall_buy/fenced/precheck_unavailable/
    # fuel_not_on_sale/bench_full/below_reserve(held_postbuy = 部署
    # 执行侧,record_fuel_filler_held_postbuy)。
    if k is not None and _lvl_readable:
        # C 支(落后·期望态口径;level 消费 level_readable 可信位)
        if int(state.level or 1) - len(deployed) > 0:
            # A 支(无可追件·不可追支):合格集 = cnt2==0 ∧ 表概率>0;
            # 成因支 = ∃ cnt2==0 ∧ 表概率=0。概率真值对账纪律(存疑-9):
            # 表值 0 与概率条实读(state.refresh_probs)对账,不一致/不可得
            # 帧 fail 向不判 A(禁据疑零值发射)。
            _rp = getattr(state, 'refresh_probs', None)
            _causal: list[str] = []
            _chaseable = False
            for _m in k_members:
                if _cnt(_m, 2) > 0:
                    continue   # 排除支:全员 2★ 成件 = 线齐,非病灶
                _mch = get_char(_m)
                _mcost = _mch.cost if _mch is not None else None
                if _mcost is None:
                    continue
                if refresh_prob(int(state.level or 1), _mcost) <= 0.0:
                    _causal.append(_m)
                else:
                    _chaseable = True
            if (_causal and not _chaseable
                    and isinstance(_rp, dict)):
                # A 支概率对账(二十四跳:缺键语义与 cw_economy 消费点统一):
                # parse_prob_bar 契约 = 全 5 键或 None——结构内缺键 = 按
                # 表值回退(因果支表值 0 ⇒ 回退即确证零,禁当「条读非零」);
                # 键在且 >0 = 与表值对账不一致 → fail 向不判 A。
                _confirm_zero = True
                for _m in _causal:
                    _m_reg = CHARACTERS.get(_m)
                    if _m_reg is None:
                        continue
                    _bar = _rp.get(_m_reg.cost)
                    _eff = (refresh_prob(int(state.level or 1), _m_reg.cost)
                            if _bar is None else _bar)
                    if _eff:
                        _confirm_zero = False
                        break
                if _confirm_zero:
                    # B 支(富金;观测条件,调度仍由 arm2 g* 线管辖)
                    if gold > s_reserve:
                        # 垫件在售 = 非 1★ 直出卡全过滤后仍有候选;资格排除集
                        # ≡ locked_buy_membership(§2.3 第 2 点单一源)
                        _ff_sale = [c for c in (state.shop or [])
                                    if (c.name or '')
                                    and (c.name or '') not in buy_members
                                    and (c.star or 1) == 1
                                    and predicates.zero_overlap(c.name or '',
                                                                k_members)
                                    and refund_full_star_ok(
                                        1, c.cost if c.cost else 3)]
                        if not _ff_sale:
                            _count('fuel_not_on_sale')   # Φ_stall 成立而垫件缺
                        elif bench_free <= 0:
                            _count('bench_full')   # §7.3 授权条件含 bench_free≥1
                        else:
                            for card in _ff_sale:
                                name = card.name or ''
                                cost = card.cost if card.cost else 3
                                # 金位 fail 向(§7.3:g − cost ≥ s_reserve)
                                if gold - cost < s_reserve:
                                    _count('below_reserve')
                                    continue
                                # 板面账围栏预检(§2.3 第 4 点;kernel 单一源)
                                _mch2 = get_char(name)
                                _cand_bc = BenchChar(
                                    slot=0, char_id=name, star=1,
                                    faction=(_mch2.factions[0]
                                             if _mch2 is not None
                                             and _mch2.factions else '?'),
                                    position_pref='back')
                                _tgt2, _fw2 = deploy_target_sets(k)
                                try:
                                    _lfs = cw_intention.locked_faction_scope(
                                        _ist) if _ist is not None \
                                        else frozenset()
                                except Exception:   # noqa: BLE001 兜底 best-effort
                                    _lfs = frozenset()
                                try:
                                    # kernel 单一源直调(围栏语义单一源契约 =
                                    # N2;预检查询非判据面谓词,不挂 contracts
                                    # 注册表——ensure_contract 未注册键会误判
                                    # 违例,直调 + try/fail 向即完整闭环)
                                    _ff_ok, _ff_why = can_deploy_single(
                                        _cand_bc, bench,
                                        deployed_cids=set(deployed_names),
                                        deployed_fac=deployed_bond_counts(
                                            set(deployed_names)),
                                        board=deployed_bond_counts(
                                            set(deployed_names)),
                                        cap=(_cap_now if _cap_now
                                             else 10 ** 6),
                                        target_factions=_tgt2,
                                        target_cores=set(),
                                        fw_carry=_fw2,
                                        locked_factions=_lfs or frozenset())
                                except Exception:   # noqa: BLE001 查询不可得
                                    _ff_ok, _ff_why = False, \
                                        'precheck_unavailable'
                                if not _ff_ok:
                                    if _ff_why == 'precheck_unavailable':
                                        _count('fuel_filler_stall_'
                                               'precheck_unavailable')
                                    else:
                                        _count('fuel_filler_stall_fenced')
                                    continue   # 围栏拒帧,试其余垫件
                                _count('fuel_filler_stall_buy')
                                _ff_reg = getattr(session,
                                                  'cw4_fuel_filler_stall_buys',
                                                  None)
                                if _ff_reg is None:
                                    _ff_reg = set()
                                    session.cw4_fuel_filler_stall_buys = _ff_reg
                                _ff_reg.add(name)   # N3 闭环登记契约
                                _on_target_buy(name)
                                return BuyCard(card=card,
                                               reason='fuel_filler_stall')
                # B 支不成立:g ≤ s_reserve(非病灶帧,静默)

    # ---- ④ EV pass(臂①旁路集;仅 criteria 真 EV 发射面)----
    if not skeleton_only:
        if contracts.ensure_contract(
                ('buy', 'ev_buy_candidates'),
                contracts.ContractCtx(k_members=k_members), counters):
            # EV 排除集 = 买入义务集(buy_members):义务面成员「走 M2,
            # 非 EV 域」——与买面同口径;非卖免面,不吃锁定全集收窄裁。
            cands, ckey = crit_buy.ev_buy_candidates(
                gold, s_reserve, state.shop, buy_members,
                level=int(state.level or 1), window=card_w,
                counters=counters)
            if ckey:
                _count(f'shop_ev_{ckey}')  # shop_domain / u_unavailable
            elif cands:
                # 席位门(ADR-0518):满栏帧 EV 买不提案——EV 候选非义务
                # 面,无 M4 腾席前置;满栏非合并买入在 simulate 走「bench_full
                # 整动作 no-op」分支(cw_state.py BuyCard bench_full 返回
                # state.copy())⇒ 同帧重复提案同候选 = 决策循环不收敛。
                # 门形态与 dominance_buy 的 check_seats 同款;拒因分键
                # shop_ev_bench_wait。席位门后,买面全 gated(满栏 §2.5
                # 分支在商店生产路径不可达,保留为防御纵深)。
                ok_seat, _ = mandate.check_seats(
                    bench_free, 0, needs_bench=True, needs_board=False,
                    name='', deployed_names=deployed_names)
                if not ok_seat:
                    _count('shop_ev_bench_wait')
                else:
                    for cand in cands:
                        card = (state.shop or [])[cand.slot_idx] \
                            if cand.slot_idx < len(state.shop or []) else None
                        if card is None:
                            continue
                        veto, _vkey = crit_buy.ev_buy_veto(cand, gold) \
                            if contracts.ensure_contract(
                                ('buy', 'ev_buy_veto'),
                                contracts.ContractCtx(gold=gold), counters) \
                            else (True, '')
                        if veto:
                            continue
                        ok1, _ = mandate.check_affordable(gold, cand.cost)
                        if not ok1:
                            continue
                        return BuyCard(card=card, reason='ev_buy')
                    _count('shop_ev_all_vetoed')   # D-P2idle:「全拒」可辨
            else:
                _count('shop_ev_no_candidate')     # D-P2idle:「无候选」可辨
        # 付费刷新(R1 发射位;终结 op——刷新即本画面访问结束,ADR-0517
        # 决策 7)。R1 门形态 = ADR-0516 形式二可负担性;输入全为游戏定义
        # 量,零胜率建模。L* = 形式二等级选择输出(留级账 T_stay vs 升一
        # 级账 T_up 取小);P40 R2 息线熔断保留原语义。金基准 = 期望态
        # 现值(旧「买后投影金」专修无存在载体——每帧金即真值)。
        if contracts.ensure_contract(
                ('refresh', 'r1_commitment_account'),
                contracts.ContractCtx(), counters):
            _c_eff = int(state.shop_refresh_cost or REFRESH_COST_BASE)
            _ibar = net_income(int(state.round_num or 1), 0)
            _g0 = gold
            _rounds = horizon.r_remaining(session, int(state.plane or 1),
                                          int(state.round_num or 1))
            _lvl = int(state.level or 1)
            _e_stay, _fees = _r1_ledger_terms(buy_members, bench, deployed,
                                              _lvl)
            if _e_stay == float('inf'):
                _t_stay = float('inf')
            else:
                _t_stay = _c_eff * _e_stay + _fees + loss_exact(
                    _g0, int(math.ceil(_c_eff * _e_stay)) + _fees,
                    _rounds, _ibar, cap_resolved)
            _t_up = float('inf')
            _clicks = clicks_to_next_level(state)
            if _clicks > 0:
                _u_gold = _clicks * xp_click_cost(state)
                _e_up, _fees_up = _r1_ledger_terms(buy_members, bench,
                                                   deployed, _lvl + 1)
                if _e_up != float('inf'):
                    _t_up = _c_eff * _e_up + _fees_up + _u_gold + loss_exact(
                        _g0,
                        int(math.ceil(_c_eff * _e_up)) + _fees_up + _u_gold,
                        _rounds, _ibar, cap_resolved)
            _ledger = min(_t_stay, _t_up)
            _lvl_star = _lvl if _t_stay <= _t_up else _lvl + 1
            r2_reserve = g_star + _r2_card_reserve(k_members, bench,
                                                   deployed, state,
                                                   level=_lvl_star)
            ok_r1, rkey = crit_refresh.r1_commitment_account(
                _ledger, _g0 - g_star)
        else:
            ok_r1, rkey = (False, 'contract_abstain')
            r2_reserve = g_star
        if not ok_r1:
            _count(f'shop_r1_{rkey}')  # no_chaseable_member / account_over_budget
            if rkey == 'no_chaseable_member' and gold > g_star:
                # 语境分键:金过剩 ∧ 合格集空 = 深血线死握的孪生观测面
                #(F1 定位批 H2 判别信号);合格集空守卫先于一切刷新语义
                #(§6.2 显式守卫),(b)3 危机直通支永久挂空(§11.8)后
                # 该帧无承重件——只显影观测,禁据以调参(§5.3 挂账期申报)。
                _count('r1_idle_gold_no_chaseable')
        elif contracts.ensure_contract(
                ('refresh', 'r2_budget'),
                contracts.ContractCtx(gold=gold, reserve=r2_reserve),
                counters):
            if crit_refresh.r2_budget(
                    gold, r2_reserve,
                    int(state.shop_refresh_cost or REFRESH_COST_BASE)):
                return RefreshShop(
                    cost=int(state.shop_refresh_cost or REFRESH_COST_BASE))
        # 凑息卖·回拉发射位(T1 语义;设计 13_buy_face_design §2.2):
        # 金位触发(期望态金 < g* 才发射)+ 目标量止盈(remaining 递减
        # 贪心,Σrefund ≥ 缺口即止)。prefer_names = 本访问已买件
        # (carried 融合:执行侧/兼容驱动器在 BuyCard 决策后登记,
        # R2-N1 首卖刚买件连带损失=0)。
        if contracts.ensure_contract(
                ('sell', 'sell_for_interest'),
                contracts.ContractCtx(gold=gold), counters):
            _slots, skey = crit_sell.sell_for_interest(
                gold, bench, cap_resolved, k_members, state=state,
                prefer_names=tuple(getattr(
                    session, 'cw4_visit_bought_names', ()) or ()),
                exclude_names=buy_members,
                counters=counters)
        else:
            _slots, skey = [], 'contract_abstain'
        if not skey:
            for s in _slots:
                bc = next((b for b in bench if b.slot == s), None)
                idx = (state.bench or []).index(bc) if bc is not None else None
                if idx is None:
                    continue
                _note_sell((bc.char_id or '') if bc else '')
                return SellBench(bench_idx=idx,
                                 income=_shop_sell_refund(bc) if bc else None,
                                 expect=(bc.char_id or '') if bc else '')
    # 支付支撑通道(两臂同开,R13-5):骨架义务动作金不足侧筹资变现。
    if missing:
        mf = mandate.MandateFrame(
            gold=gold, level=state.level, bench=bench, deployed=deployed,
            deploy_cap=state.max_units(),
            node_type=state.node_type,
            stop_flag=stop_flag, k_members=k_members,
            round_num=getattr(state, 'round_num', 1))
        need = mandate.cheapest_member_cost(mf)
        for m in missing:
            shop_cands = [c for c in (state.shop or [])
                          if (c.name or '') == m]
            if shop_cands:
                need = min(need, min(
                    (c.cost if c.cost else 3) for c in shop_cands))
                break
        fslots, _fkey = crit_sell.funding_support_sell(
            gold, need, bench, k_members, state=state,
            exclude_names=buy_members) \
            if contracts.ensure_contract(
                ('sell', 'funding_support_sell'),
                contracts.ContractCtx(gold=gold), counters) else ([], '')
        for s in fslots:
            bc = next((b for b in bench if b.slot == s), None)
            idx = (state.bench or []).index(bc) if bc is not None else None
            if idx is None:
                continue
            _note_sell((bc.char_id or '') if bc else '')
            return SellBench(
                bench_idx=idx,
                income=_shop_sell_refund(bc) if bc else None,
                expect=(bc.char_id or '') if bc else '')

    # ---- D-D 硬节点补强门消费(观察级接线;逐帧计数,粒度申报见上)----
    _gate_open, _gkey = crit_refresh.hard_node_reinforce_gate(
        state.node_type, int(state.gold or 0), g_star) \
        if contracts.ensure_contract(
            ('refresh', 'hard_node_reinforce_gate'),
            contracts.ContractCtx(gold=int(state.gold or 0)), counters) \
        else (False, '')
    if _gate_open:
        _count('shop_hard_node_gate_open')

    # ---- 终结:CloseShop(恒可用;D-P2idle 带金零动作帧计数)----
    # 键语义 = CloseShop 收尾且金 ≥10 的 visit(visit 含刷新段时与旧
    # shop_wave_idle_gold 波计数不等值,跨结构不可对拍)。
    if int(state.gold or 0) >= 10:
        _count('shop_visit_idle_gold')
    return CloseShop()


