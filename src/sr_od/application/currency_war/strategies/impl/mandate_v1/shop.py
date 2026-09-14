"""cw4 商店线 decide_shop_action——步4b 商店线(单动作形态,ADR-0517)。

SIM_CONSUMPTION_MAP Q1:sim A/B 证明面 = 商店经济决策(买/卖/升/刷/事务)
——本模块是 mandate_v1 商店线的决策本体,黑板唯一输入 =
``session.prep_obs_frame`` + 容器单例 ``board_state_of(session)``
(GameState,写者=商店入口观察段/单动作逻辑态直写)。

商店单动作形态(ADR-0517;前身份 = 波批 decide_shop_wave,迁移批改型):

1. 方向(证明面投影):K = ``state_of(session).target_comp``(方向重估产物,
   写者 = flow 层方向刷新,ADR-0583)、stop_flag = proof.stop_buy、D-A45 干旱计数器;
   **K 空窗回退(2026-09-03 第三病灶修复;FIX_REVIEW_20260903 R3 扩域
   至三带)**:target_comp 为 None 时按带回退(单一源 cw_intention,禁
   复制)——P1 空窗带(支持度 < P1_PAIR_LOCK_MIN_SUPPORT)取
   ``hoard_target_set`` 四体系全集;P1 锁线过渡带(支持度 ≥门槛未锁帧)
   取 ``p1_early_pair_members`` top-2 方向;P2+ 带取 ``hoard_target_set``
   分带兜底(绯英⑤/跨线骨架/降格满配)。非 None 期行为不变;
2. 预算投影:cap_resolved 现读 → 守息线 g* = 10×cap_resolved(R70-1 参数化)
   + S 预留(P56 可变现息线下界 s_reserve := g* − Σ活期退金投影,设计
   13_buy_face_design §2.2)——单动作下输入金/席位 = 期望态当前值
   (动作后真值),「帧首快照 + 逐动作累积逻辑态」口径随波批退役;
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

计数键(state_of(session).cw4_counters;键登记单一源=本清单与写点,原
design_telemetry 键节已删档,取回口径=ADR-0644——步4b 新键):
shop_ev_u_unavailable / shop_ev_shop_domain / shop_ev_no_candidate /
shop_ev_all_vetoed / shop_ev_bench_wait / shop_r1_ev_unavailable /
shop_visit_idle_gold /
shop_hard_node_gate_open / shop_drought_reset_on_buy /
shop_merge_trigger_truncate;K 空窗回退修复批(2026-09-03 第三病灶)
增补 shop_k_fallback_p1_gap(空窗帧回退计数);复审返工批
(FIX_REVIEW_20260903 R3)增补 shop_k_fallback_p1_lock_band(P1 锁线
过渡带回退计数)/shop_k_fallback_p2plus(P2+ 带回退计数)——三带
回退分键登记=各键写点(原 design_telemetry「复审返工批」节已删档,取回
口径=ADR-0644)。P86 无目标期三臂判据
落码批增补(判据=kernel 三臂;分键独立,禁混入历史 token 计数——
shop_k_fallback_p2plus 语义重建为「回退采用」,落码后构成=甲臂方向
采购集):shop_no_target_arm_a_adopted(甲臂方向采用帧)/
shop_no_target_arm_a_dead_defer(甲臂判死出辖帧,P35 病灶帧行为改变
显影)/ shop_no_target_arm_a_corner_defer(缓锁豁免角漏授帧,证明批
§3.1-4 已知缺口,与无信号判死禁混桶)/ shop_no_target_hold_default
(丙臂守息合法空帧,契约 k_fallback_source 证据通道显影)/
hub_option_candidate_seen / hub_option_buy_hit / hub_option_arbitration_
yield / hub_option_reject_{merge_material,seats,interest,unaffordable}
(乙臂发射五前件合取的拒因归真族)。T-115 恒买腾席批(ADR-0580 席满
转化支)增补:三腿席满腾席/诚实停摆/金闸双桶出口键闭集
{core_unlocked,core_locked,transition} × {seat_swap,no_fuel,
unaffordable_strict,unaffordable_fundable}(seen 帧必落 ≥1,sim 判红
检测器 sim/checks/ledger.check_core_ruling_seat_violation 判据)+
core_numeric_fail_closed 尾键收窄(席满停摆帧不再共火,for-else 语义)
+ dead_gold_press_bench_full_gate(②(b) 外门席满支静默显影,B2 移位案)。

键语义申报:``shop_visit_idle_gold`` = CloseShop 收尾且金 ≥10 的
**visit**(单动作迁移批自旧 ``shop_wave_idle_gold`` 改名——「波」结构
已退役;旧计数跨结构不可对拍,visit 含刷新段时旧波计数与其不等值,
判读须按新语义重建基线);``shop_ev_bench_wait`` = EV 候选在场但
bench 无空席、EV 买不提案的帧(席位门,与 dominance_bench_wait 同款)。

T-82 必花臂重试风暴批计数粒度变更:``m2_retry_exhausted`` /
``bench_full_buy_abandon`` 从「每决策帧一次」改**事件粒度**——腾席
无候选的输入不变续段(上帧动作 ∈ M2_STALL_NONVARIANT_SHOP_ACTIONS
白名单 ∧ 同段)内命中续段缓存的帧不再 +1(量级骤降 ≠ 风暴消失,
判读协议随批声明);新增观测对 ``m2_stall_cache_hit``(命中帧)/
``m2_stall_cache_rederive``(重推导得出无候选帧)与重复帧键
``m2_stall_repeat_frame``(风暴帧量级保留可见,零静默)。语义依据
= P60 诚实停摆事件语义(停摆计数应量「不同停摆段」而非「帧」)。
``merge_material_guard_blocked`` 不受本批影响:帧首 P56 投影位
无条件先触达并首计,与本缓存正交、行为零变化。

T5 未锁线止血买分键族(ADR-0556 §5;对齐 17号稿
七键口径):t3_available / t3_buy / t3_no_candidate(店无 cost-1 垫件,
有意收窄帧归因显影)/ t3_fenced(+kernel 五拒因动态后缀)/
t3_precheck_bench_full / t3_precheck_no_vacancy(vacancy ≤ 可部署
bench 件数,买后无空槽可落,与 bench 满拆键)/ t3_precheck_unavailable /
t3_unaffordable / t3_below_reserve / t3_p1_true_blocked(P1 真帧
行为层挂起显影)——held 闭环归并申报:本发射面**不设独立 t3_held_postbuy
键**,T5 垫件买入走出口③同款 N3 登记(session.cw4_fuel_filler_stall_buys
单一载体),部署侧 held 显影并入 fuel_filler_stall_held_postbuy 口径
(cw_op_deploy.record_fuel_filler_held_postbuy 消费;两触发源同垫件
语义,禁第二登记集);t3_calib_blocked(行为层标定闸)归授权批。

计数键粒度(ADR-0517 迁移步 2):各键从「每波一次」改「每决策帧一次」
(shop_drought_reset_on_buy 经 drought 值门维持「每访问至多一笔」);
``shop_merge_trigger_truncate``/``emitter_*`` 族随截断器退役(语义被
逻辑态直写与终结 op 吸收)。R197 症6 的 funding need 注册表派生
(``mandate.cheapest_member_cost`` 单一源)原样保留。

P77 缺口面装载批(ADR-0626)增补:m2_stockpile_spot2_buy(j=1 帧
同名 2★ 直出现货经比较子买入的达成路线显影;义务 reason 键不扩闭集,
P88 豁免集 15 键零扰动)/ m6_s_reserve_remeet_frames_sum(s_reserve
拒帧的被拒现货再遇窗累计,自然帧 ceil;对价载体纯遥测,禁决策判据
消费,让路裁决归 P56 设计批)。

T-263 前窗/定向刷新批(ADR-0635;命题 = math_proofs P90-P94)增补:
p90_front_table_missing(P1 帧节点表缺,前窗 fail-closed 显影)/
p90_zerostack_frame_armed(前窗∧四体系零成型帧)/
p90_zerostack_advancing_buy(零成型帧四体系推进件买入 = 排序层前移
命中)/ p90_front_window_buy(前窗买入总笔)/ p90_front_buy_cross_tier
(前窗跨档买入笔数,P90① 成本界检验)/ p90_front_buy_over_bound
(1-2 费前窗买入息损 >1 断言键,结构性恒 0,违反即 P90 推导失效)/
p90_front_buy_cost3p(前窗 3 费以上买入越域观测,P90 辖 1-2 费)/
p94_no_activatable(零成型帧店无推进件)/ p94_exemption_refuse
(P94 放行层豁免拒绝——u_x 🔴 在册标定债,豁免恒拒;**p94_exemption_
grant 结构性恒 0**,无代码路径可增,P94 证明+标定批落授权,禁把死
通道读成生效件)/ p91_active_band_frame(P91 活跃搜索费带非空帧)/
p91_m6_same_axis_hit / p91_m6_off_axis_hit(M6 压库同轴/异轴选择帧
对键)/ p91_refresh_up_switch(R1 刷-升选择切换帧)/
p92_no_buy_refresh_blocked(P92 全通道可实现买入集空帧拦刷 = 面②
审计①桶计数)/ must_spend_r1_no_buy_blocked(必花域内 P92 拦刷的
域内 liveness 显影,与 must_spend_r1_budget_fail 混桶禁)。
"""
from __future__ import annotations

import contextlib
import math
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS, get_char
from sr_od.application.currency_war.data.cw_shop_odds import (
    expected_refreshes_for_card,
    reencounter_window_frames,
    refresh_prob,
)
from sr_od.application.currency_war.kernel import cw_intention
from sr_od.application.currency_war.kernel.cw_card_identity import (
    TIER_REGISTRY_CORE,
    TIER_TRANSITION,
    TIER_UNRELATED,
    line_identity_tier,
)
from sr_od.application.currency_war.kernel.cw_comps import (
    CORE_SINGLE_CARD_REGISTRY,
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    can_deploy_single,
    deploy_target_sets,
    deployed_bond_counts,
    record_fresh_buy,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    bench_char_cost,
    blood_xp_gate_for,
    card_cost,
    clicks_to_next_level,
    effective_refresh_prob,
    in_must_spend_zone,
    interest,
    refresh_cost_effective,
    sell_refund,
    xp_click_cost,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
    BenchChar,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_slots_of,
    deployed_slots_of,
    gold_of,
    level_of,
    max_units_of,
    node_kind_of,
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
    is_piggy_reward_frame,
    reward_node_suppressed,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    BuyCard,
    CloseShop,
    DeployMove,
    LevelUpShop,
    RefreshShop,
    SellBench,
    SellDeployed,
    ShopCard,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    entry,
    mandate,
    proof,
    sell_gate,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
    provisional,
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
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
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
    from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar
    from sr_od.application.currency_war.kernel.cw_vocab import Action
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

# ===== 截断分类退役声明(ADR-0517 迁移批)=====
# 旧 _SHOP_CONTINUE/_SHOP_CONDITIONAL/_SHOP_TRUNCATION 三分类与
# ``truncate_shop_frame_stable`` 截断器已随波批形态退役——截断点语义被
# 终结 op 吸收(RefreshShop 即终结,CloseShop 恒可用;原 CompTransaction 邻接 fallback 已随批2b R3 删除),
# 名-槽一致性复检降级为执行侧 proposal-vs-expected 守卫断言
# (cw_shop_action_ops;ADR-0517 决策 9 和解注)。

# ===== M2 停摆续段缓存:非变异动作白名单(T-82 必花臂重试风暴)=====
# 跳过条件 = 可判定谓词「帧间动作全在本集 ∧ 同段」,非任何计数阈值
# (零参数结构,同族支配语境:P70 已证、P69 草拟未证,本批语义依据
# = P60 诚实停摆 + ADR-0573 方案 §3 跳过弱支配)。白名单外动作(含
# 未知新动作型)一律视为变异 ⇒ 缓存失效 ⇒ 全量重推导(保守端 = 现
# 行为,最坏退化即无缓存)。⚠️ 守卫:加入新动作型前须验证其执行语义
# 不动 bench/deployed/k/敌缀/意图集(停摆结论的全部输入)——现行两
# 成员依据:sim 引擎 LevelUpShop 只动 gold/spend/xp、RefreshShop 只动
# gold/spend/xp/商店牌面(牌面不在输入集),生产对应 op(真实点击
# 升级/刷新)同语义。
M2_STALL_NONVARIANT_SHOP_ACTIONS: frozenset[str] = frozenset(
    {'LevelUpShop', 'RefreshShop'})


def _shop_sell_refund(bc: BenchChar) -> int | None:
    """卖出预期回金(sell_refund 口径;注册表 cost 缺失 ⇒ None=未标)。"""
    ch = CHARACTERS.get(bc.char_id or '')
    if ch is None or not ch.cost:
        return None
    return sell_refund(bc.star, ch.cost)


def _r1_ledger_terms(buy_members: tuple[str, ...],
                     bench: list, deployed: list,
                     level: int) -> tuple[float, int]:
    """R1 总账装配侧(R1 门·形式二可负担性口径):返回 (E(D|level), Σ卡费)。

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
    - 该级不出此费(refresh_prob≤0)成员剔出本级合格集(E 不计;下级
      账由 T_up 在 L+1 级重估同一成员集)——与 r2_card_reserve 的
      continue 过滤同款语义,inf 仅由「合格集空」承载(见返回契约);
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
            continue    # 该级不出此费:成员出合格集(禁打 inf——任一不可追
                        # 成员污染共享累加器会把非空合格集错判「无可追」,
                        # 整局刷新臂结构性恒关;复现与修法裁决 = ADR-0571)
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
                     bs: GameState,
                     level: int | None = None) -> int:
    """R2 预算门 Σ预留卡价 ρ(单一源已提升至 criteria/refresh.
    r2_card_reserve;P71 闸批别名重导出——本名保留使既有测试面
    (test_cw_interest_floor.py 私有名直引)与生产调用点零漂移,
    语义/签名/等级过滤口径逐位不变,docstring 见单一源本体)。"""
    return crit_refresh.r2_card_reserve(k_members, bench, deployed,
                                        bs, level=level)


def _merge_pair_names(bench: list[BenchChar],
                      deployed: list[BenchChar]) -> set[str]:
    """合成完备购形态对名集(M2b 循环与 P92 ④通道装配两处共吃的单一
    源,禁第二实现):全局面(bench∪deployed)同名副本恰 2 张 ∧ 均
    1★ 的角色名。

    机器口径申报(消费纪律):本谓词 = M2b 机器实现口径,非机制全集
    ——机制上「同名 1★ 凑满 3 即合成」(merge_mechanics.md §2 主例:
    备战 1★×2 + 场上 2★×1 → 买第三张 1★ 触发合成),机器只实现「恰
    2 张全 1★」单跳形态;「1★×2 与 ≥2★ 同名并存」的买三张通道机器
    未实现(两真实合成通道残余,经 T-313 发现、T-315 追认的设计边界;裁定档已删,git da3a7370ce
    可溯)。未来 M2b 若补该形态,
    本谓词须同步收扩——否则 P92 门将从「对齐机器」翻成「误杀真
    通道」。

    归一化/计数键逐字符同 ``decide_shop_action`` 内 ``_cnt``(同名同
    星副本计数):星级 ``(c.star or 1)``(None 视同 1★)、键
    ``(c.char_id or '')``、计数宇宙 bench∪deployed。资格维不在本
    谓词辖域(调用方各自过滤:M2b 循环天然辖于 buy_members,P92 装配
    显式 ∩ buy_members——资格维对齐 M2b 实现,T-295 对抗审问题 6
    转正,reviews/T-295-方案对抗审.md)。
    """
    copies: dict[str, list[int]] = {}
    for c in list(bench) + list(deployed):
        copies.setdefault(c.char_id or '', []).append(c.star or 1)
    return {n for n, ss in copies.items()
            if len(ss) == 2 and all(s == 1 for s in ss)}


def p92_seat_recoverable(session: StrategySession,
                         bench: list[BenchChar],
                         k_members: tuple[str, ...],
                         bs: GameState, *,
                         cap_hold: int | None,
                         current_round: int,
                         defer_names: frozenset[str] | set[str],
                         counters: dict | None = None,
                         dedup_names: set[str] | None = None) -> bool:
    """P92「席可落」腾席可达判定(IC-1 单源;T-20 收窄落码)。

    真值 = ``mandate.fuel_sell_candidates`` 资格面非空,排除集与店帧
    实际腾席臂(M2 缺员腾席位/m2_stockpile 腾席位/恒买腾席支)同一
    装配 A 形态(``sell_gate.sell_exclusions(channel='m4_fuel')``,单一
    入口禁第二排除集),T3 同轮保留走 defer 末位(转化类放行,与腾席
    臂同参)——「存在可变现 1★ 燃料件」即席可落,判定尺与腾席发射位
    同源,禁平行第二实现。

    收窄沿革(旧代理为何退役):旧装配传 P56 投影 ``liquid_refund>0``
    (金额投影代理)。其申报的偏宽面(占位件被当可变现候选)已随该
    投影读的单一源化(fuel_sell_candidates 占位件滤门)闭合;残余失真
    是**口径错配**双向漂:①排除集——投影视图并 T3 活跃集
    (sell_gate.py projection 支),而腾席臂对垫保是 defer 转化类放行
    非排除 ⇒ T3 活跃帧投影读 0、席实际可腾,旧代理误判不可达 ⇒ P92
    误拦(方向 = 过度拦刷,失刷新机会);②布尔化——「Σ退金>0」是
    资金量语义非席可落能力布尔(零费候选角帧同误判)。本判定直引
    腾席臂同参资格面,两向漂移一次消除;行为差方向 = P92 在 T3 活跃
    帧少拦(差帧 ② 通道真实可达,旧拦为误拦),行为差锁 =
    sr-od-test test_cw_seat_recoverable_narrow.py。
    ``counters``/``dedup_names`` 照传帧级共享载体
    (``merge_material_guard_blocked`` 事件口径每帧每素材至多 1,与
    P56 投影读/凑息/支付变现触达位同款纪律)。
    """
    excl = sell_gate.sell_exclusions(session, k_members, channel='m4_fuel',
                                     cap_hold=cap_hold,
                                     current_round=current_round)
    cands = mandate.fuel_sell_candidates(bench, k_members, state=bs,
                                         exclude_names=excl,
                                         defer_names=defer_names,
                                         counters=counters,
                                         dedup_names=dedup_names)
    return bool(cands)


def _frame_search_windows(session: StrategySession, bs: GameState,
                          registry, counters: dict) -> tuple[frozenset[int],
                                                            frozenset[int]]:
    """帧级搜索窗口(T1;设计 13_buy_face_design §2.3/§3.2)。

    窗口判据重锚(V̄ 链退役随批):旧 V̄ 门式
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
    level = level_of(bs)
    omega = registry.omega_collapse_ratio
    return (tier_search_window(level, omega),
            card_search_window(level, omega))


def shop_unbought_reasons(bs: GameState,
                          comp: Comp | None,
                          k_members: tuple[str, ...],
                          actions: list[Action],
                          hub_names: frozenset[str] = frozenset(),
                          ) -> dict[str, str]:
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
    - ④转线放行集(kernel.cw_card_identity 身份分层单一源,T-115 D7 键序
      先于 trans 分支——交集卡可辨):``transition_component``;
    - 乙臂枢纽资格集(P86;入参 = kernel.no_target_arms().hub_names 直传,
      判据单一源在 kernel,本函数只挂标签):``hub_option``——空窗帧枢纽
      件从 non_line 改显式拒因(正本 §4.4 行 3 键序消费面重排;未发射
      = 金/席/息/素材门逐帧判,精确门序以 hub_option_* 计数键为准);
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
    bench = [b for b in bench_slots_of(bs) if b is not None]
    deployed = [d for d in deployed_slots_of(bs) if d is not None]
    owned = ({b.char_id or '' for b in bench}
             | {d.char_id or '' for d in deployed})
    gold = gold_of(bs)
    bench_free = BENCH_CAPACITY - len(bench)
    for a in actions:
        if isinstance(a, BuyCard):
            gold -= card_cost(a.card)
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
    for card in shop_payload_content_cards(bs.shop.value):
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
                cost = min((card_cost(c))
                           for c in shop_payload_content_cards(bs.shop.value)
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
            cost = min((card_cost(c)) for c in shop_payload_content_cards(bs.shop.value)
                       if (c.name or '') == name)
            if bench_free <= 0:
                out[name] = 'missing_bench_full'
            elif gold < cost:
                out[name] = 'missing_unaffordable'
            else:
                out[name] = 'missing_no_path'
        elif name in hub_names:
            # P86 乙臂拒因键(枢纽资格件在售未买帧与真 non_line 可辨)。
            # 键序 = 先于 ④/trans 分支(P86 正本 §4.4 行 3「键序消费面重排」:
            # p2plus 无目标帧上 ④ 放行臂经 committed 门构造性关闭,枢纽臂
            # 才是在售交集卡(如 花火)的活发射通道,拒因按活通道归属;P1
            # 帧本键不产(hub_names 空集直传),④ 旧键序零变化)。判据单一
            # 源 = kernel.hub_option_names,本函数只挂标签。
            out[name] = 'hub_option'
        elif line_identity_tier(name) == TIER_TRANSITION:
            # T-115 规则④ 拒因键(D7 键序,ADR-0580):④放行集判据先于
            # trans 分支——交集卡(④放行件 ∧ 某 comp transition_chars)
            # 在旧序(k_members→trans→else)下恒落 transition_char,新键
            # 不可达。定序理由 = 判读价值:④件被拒才是要盯的信号(席/金/
            # 星级硬闸漏放),打工件刻意不买是常态;行为无影响(买入由
            # 放行臂驱动),纯遥测口径。判据单一源 = line_identity_tier
            #(与规则④买入臂同源)。
            out[name] = 'transition_component'
        elif name in trans:
            out[name] = 'transition_char'
        else:
            # C1 拒因拆键(设计《直通核心卡信号层入口》§4 意向状态机行):
            # registry 核心卡在售未买帧与真 non_line 可辨——sim 检查器归
            # 机会错失类,落码批带方向声明(严格向:核心件在售帧被拒判红)。
            # T-115 规则③后语义收窄(ADR-0580):未锁线帧在售核心卡正常帧
            # 已由恒买放行臂买入,本键残留 = 席/金硬闸拒的 fallback 标签。
            out[name] = ('core_candidate_rejected'
                         if name in CORE_SINGLE_CARD_REGISTRY else 'non_line')
    return out


def count_material_stale(counters: dict, session: StrategySession,
                         bench: list[BenchChar],
                         deployed: list[BenchChar],
                         round_num: int) -> None:
    """滞留素材显影分键(ADR-0558 §4 滞留显影欠账 G-B1 第四级;官方键,
    取代 sim71 守卫验收批的「重复对在场行数」代理口径)。

    分键两把:
    - ``merge_material_stale``:素材对(同名同 1★ ≥2,判定单一源 =
      ``cw_state.merge_material_stale_names``)在场的决策帧计数,
      粒度 = 名×帧(与 cw4_counters 家族逐帧口径一致);
    - ``merge_material_stale_ge2``:跨轮仍滞留(上一见帧轮次 < 本轮)
      的名×帧计数 = 「N 轮未合成」的轮级显影——合成后键停止增长
      (轮差分归零),滞留时长由判读端按键差分读,本函数不做时长判定。

    辖域 = 商店决策帧(由 ``decide_shop_action`` 逐帧调用;备战帧不计,
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


# ===== 线账闭合孤儿证明载体(T-141 乙′;ADR-0591 §4)=====
# T-165 上移申报(原「回迁候 sell_gate 开放批」兑现):簿键/读口/孤儿
# 证明集单一源 = sell_gate(_OBLIGATION_BOOK_KEY / obligation_book_of /
# line_switch_orphans_of)——L1 换线孤儿 carve-out 需要同源证明(第二
# 键 = 双源漂移面);本侧保留薄委托零断链(调用位/测试引用不变)。


def _obligation_book(session: StrategySession) -> dict:
    """义务类买入镜像簿读口(单一源 = sell_gate.obligation_book_of)。"""
    return sell_gate.obligation_book_of(session)


def _line_switch_orphans(session: StrategySession,
                         base: set[str], round_num: int) -> frozenset[str]:
    """本轮线账闭合孤儿证明集(帧首计算;必须先于本帧任何装配 A 读点
    调用——A 身份段会就地销账,销账后登记面不可再辨「曾义务」;
    证据载体/谓词单一源 = sell_gate.line_switch_orphans_of,镜像簿
    轮戳跨销账存活)。"""
    return sell_gate.line_switch_orphans_of(session, base, round_num)


# ===== P77 缺口面装载(2★ 直出现货比较子 + s_reserve 拒绝对价;ADR-0626)=====

def spot2_direct_out_card(cands: list[ShopCard], name: str, level: int,
                          c_eff: int) -> ShopCard | None:
    """j=1 帧的同名 2★ 直出现货比较子(P77 缺口面1,ADR-0626)。

    账式(P77 §2.2 原式,零新自由参数):DIY 账 = 再收 2 张 1★
    (2×基价)+ 付费刷新账 c_eff·E(D|j=1,k=3)(E 单一源 =
    ``expected_refreshes_for_card``;溢价表 P77 §2.2:3费@L7=30.9 /
    2费@L6=30.4 / 4费@L8=57.2 / 5费@L9=80.7 金【推】,全档>0);现货账
    = 星级费用实付(card.cost,徽章 ×3 律,merge_mechanics §2.6)。
    现货账 ≤ DIY 账 ⇔ 发卡。
    - fail-closed 边界:p(level,基价)=0 帧 E=0 系函数约定(该级 DIY
      结构性不可达,非「零刷新成本」),比较子判不可评 → None(维持
      星过滤拒;P77 溢价表覆盖可行 DIY 域,域外延未证不入)。
    - 席/金交互不在本函数(比较子只裁「值不值」):买不买仍走臂内既有
      闸序(金闸前置 → M4 腾席,与 1★ 路径同序同闸,装载设计 §1.3;
      买入后 cnt2=1 臂触发自灭,二-1 守卫防重复)。
    - [A/B 切换面] 本函数 = 模块级槽位:基线臂经 monkeypatch 置恒 None
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
    """s_reserve 拒帧的对价侧(P77 缺口面3,ADR-0626):被拒现货的再遇窗
    (自然帧,ceil)——「留保息 vs 收现货」权衡自此有量值载体。

    纯遥测累计,禁决策判据消费;让路裁决(下界是否/如何为现货让路)
    归 P56 设计批(P77 辖域申报:本命题不裁决)。held 折算 = 全局面
    同名基础副本数(1★×1/2★×3/3★×9);窗式单一源 =
    ``reencounter_window_frames``(P77 §1.4「再遇窗 1/q(自然帧)」)。
    """
    name = card.name or ''
    char = CHARACTERS.get(name)
    base = int(char.cost) if char is not None and char.cost \
        else card_cost(card)
    held = sum(star_base_copies(c.star)
               for c in list(bench) + list(deployed)
               if c is not None and (c.char_id or '') == name)
    win = reencounter_window_frames(level, base, held)
    if not math.isfinite(win):
        return _REMEET_WINDOW_CAP_FRAMES
    return int(math.ceil(win))


# ===== 结算线地板(discretionary 买臂的买后裸金下界;ADR-0624)=====

def check_settlement_line(gold: int, cost: int, g_star: int) -> tuple[bool, str]:
    """结算线地板:买后裸金不出息律饱和线(gold − cost ≥ g*,g* 由
    调用方传 ``saturation_line(cap_resolved)`` 派生,禁字面 50——R70-1
    息帽参数化链,买断制 g*=0 时被 check_affordable 蕴含即 no-op)。

    为什么需要(五件结构事实的合取,ADR-0624 §背景):①资格门单边——
    dominance 臂原只查买前 gold > g* 与 check_affordable,是全部
    discretionary 买臂中唯一无买后线检查的臂;②单动作串行链——一次
    店访每帧买一张、金为期望态现值,串行消费下末笔可穿线;③P78-1 同
    visit 禁卖回(定义性抵消买入);④T3 同轮垫保——买入即入发射登记
    簿(press 类 τ=同轮),卖回恢复通道当轮结构性不可达;⑤息结算在
    轮末、按裸金(bench 资产不计息,P47)——穿线笔使当轮息档恰降
    1 档且当轮不可恢复。

    口径分界(禁三处买臂判据漂移):
    - 与 P56 s_reserve(可变现口径)**不同源不同面禁统一**(账本预裁):
      s_reserve 管 EV 臂完成度价值买入的财富账,本线管纪律面当轮结算
      息档,本谓词不消费 s_reserve 谓词;
    - 档 1 press_buy_deployable 的金位地板(ADR-0604 §2)为同形判据,
      自本批起消费本谓词(同谓词同值,行为不变);
    - ②(b) 当轮档地板是**另一形状**(当轮息档保持 cost ≤ gold −
      10×⌊gold/10⌋,带内语义),不合流、勿合并。

    拦截语义 = 资格修正非票据废除(P88 同族):买后金 ≥ g* 的购买全程
    处于溢余带——该带内支出息损 L≡0(P70 全网格复算已证),地板保留的
    全部行为都在已证零损域内;穿线笔(出域段)无在证授权,fail-closed。
    被截笔价值面(压缩/垫件)不进判据(P49 判据一:跨档压缩恒 0 为
    结构事实;价值账归显式模型轨,ADR-0624 §挂账)。

    正本规格指认的家 = mandate.check_s_reserve 旁;因 mandate.py 存在
    并行在飞改动暂居本模块(T-193 文件面阶段化),归位迁移随 mandate
    面修正批整体平移(本函数零模块态依赖,平移零行为面)。
    """
    if gold - cost < g_star:
        return False, 'settlement_line'
    return True, ''


def decide_shop_action(bs: GameState, session: StrategySession,
                       config: object, *, registry=None) -> Action:
    """商店单动作决策(ADR-0517 决策 1/2;前身份 = ``decide_shop_wave`` 波批)。

    契约:**全函数**——f(期望态) → 恰一个动作,永不返回 None(决策 5);
    「无动作可做」= 返回 ``CloseShop`` 终结动作(决策 4/6,取代旧「空序列
    = 决策完成」通道)。画面内合法性全部内化于本函数(决策 2 和解注:以
    期望态为据只提合法动作);执行侧只余守卫断言(cw_shop_action_ops)。

    选择序 = 既有波批优先级逐帧取首项(ADR-0517 §映射,序不变):
    M4 腾席 → M2 线成员(含 M2b 合并完成)→ dominance → C1 核心卡支配支
    (dominance 邻位,ADR-0569)→ M3 升级(单击)
    → M6 溢余 → EV 买面 → R1 付费刷新(终结)→ 凑息卖 → 支付支撑卖
    → CloseShop(终结)。输入 ``state`` = 期望态当前值(动作后真值,
    ADR-0517 §8.1 裁决:契约核验与决策同源消费此值,禁帧首快照口径)。

    计数键粒度声明(ADR-0517 迁移步 2):``state_of(session).cw4_counters`` 各键
    语义从「每波一次」改「每决策帧一次」;跨结构对比(A/B 或回归判读)
    须声明口径切换,禁把两粒度计数直接对拍。拒因遥测
    (``state_of(session).cw4_shop_rejects``)同样逐帧刷新——期望态即逻辑态直写后真值,
    无累积逻辑态账,``actions`` 传空列表(买走的牌已从 state.shop 摘除)。
    M3 粒度(ADR-0517 决策 3 + §权衡):升一级 = 一个动作 op,clicks
    序列是动作内部步骤;单动作形态下每帧恰发一个单击动作,下一帧以更新
    后的 xp/level 重判(spend_unified 逐次校验整批可负担,可负担面单调
    ⇒ clicks 序列逐次全过,P48 整买纪律不破)。
    """
    if getattr(state_of(session), 'cw4_counters', None) is None:
        state_of(session).cw4_counters = {}
    counters: dict = state_of(session).cw4_counters

    # 全 unknown 窗(用户三态裁定 2026-09-13,shop-slot-model §5.1):店开
    # 而牌面含 unknown(整帧 OCR/SIFT 失读窗)→ 花钱动作(BuyCard/
    # RefreshShop/LevelUp)一律禁发射(烧金在失读牌面上、刷后重观察多半
    # 仍失读,不猜),终结集降级为仅 CloseShop——收工路径的未识别卡停机
    # 钩子(kind=='unknown' 判据)随即留证停机。行为收紧显式申报:旧
    # 「失读窗沿用陈旧牌面续决策」退役,该窗从「带陈旧牌面试买」收紧为
    # 「快速收店+停机留证」;真买空([empty×5])不受影响。
    _payload_u = bs.shop.value
    if _payload_u is not None and any(
            s.kind == 'unknown' for s in _payload_u.cards):
        return CloseShop()

    # T-82 续段 token 读清协议:入口读取后立即清除(防重复消费;生产单
    # 动作循环与 sim/replay 驱动器的共同必经点在本函数,读清单点覆盖全部
    # 调用方)。命中判定见 M4 块——任何调用方首帧(槽空/型外/序号不等)
    # 默认全量重推导。
    _st = state_of(session)
    _frame_token = _st.cw4_frame_action_record
    _st.cw4_frame_action_record = None

    # T-159 B4 内容面观测:重进店内段(本节点 S1 曾被旗标机清键)的
    # discretionary 面(dominance/EV/R1)动作计数。重开的合法来源 = 义务
    # 残差闭环(猎点 14),重跑 discretionary 面 = 内容面如实开放(编者③
    # 边界只在触发面成立),本键为其 [28] 息基腿风险源监控读数(量级非
    # 归因)。标记键式,本节点首个清键后的全部店内段计入;纯遥测,禁
    # 决策判据消费。
    _reopen_armed = (getattr(_st, 'cw4_reopen_armed_phase', None)
                     == ((bs.node.value.plane if bs.node.value is not None else None),
                         int(round_num_of(bs) or 1)))

    # 备战期开店闩置位(唯一写点;键与 mandate.run_mandate 的 phase 同式):
    # 本函数被调 = 开店动作真执行、商店域决策访问已发生——闩语义
    # 「本备战期商店已被访问,期内重开无信息量」的记账位在访问发生,
    # 不在 mandate 发射位(备战环单动作环下发射≠执行,发射列表中
    # OpenShop 前的可续动作先执行即终结本环、OpenShop 未执行;发射即
    # 置闩会让闩烧而店未开、后续环被闩挡死空批出战。实证与修法裁决 =
    # run_mandate docstring「备战期开店闩」节;装备闩同型残留先例)。
    # read_only 开店(纯读数,不进本函数)不消耗闩:读数访问不改店面,
    # 期内买入决策仍待发。位面/轮次推进=新键自动失效,与 mandate 侧同。
    state_of(session).cw4_shopped_phase = ((bs.node.value.plane if bs.node.value is not None else None),
                                 round_num_of(bs))

    def _count(key: str) -> None:
        counters[key] = counters.get(key, 0) + 1

    def _emit_buy(card: ShopCard, reason: str, *,
                  launch_cause: str | None = None) -> BuyCard:
        """买入发射位 fresh 排除登记(ADR-0530 开闸批接线;单一载体 =
        kernel ExecState.cw4_swap_fresh_buys,禁第二实现)。单动作契约(本函数
        docstring)下 return 动作被决策循环无条件采纳执行——生产买面无
        截断丢弃面(刷新硬墙只降级 RefreshShop),故本写入时点 = 买入
        采纳;发射位逐名写入(漏记 = 卖出环切不断),过度排除方向安全
        (载体注释口径,拒因 fresh_buy 可追溯)。

        发射登记(P78 窗口段;T-126 批 3,ADR-0585 §2/§3):窗口段两类
        买因(press/stall_protect)经发射登记簿逐名登记(登记轮 = 当前
        轮;活跃 = 登记轮==当前轮 → 同 visit 卖回全通道被禁,W1)。
        ②(b) 按 prio 三分买因(obligation/hold/press)经 ``launch_cause``
        显式传因;hold 类过类资格断言(2★ 转线直出 = launch_cause_
        mismatch 拒登记不拦发射,W5/V2-06)。dominance/M6/ev_buy 按
        LAUNCH_CAUSE_BY_ARM 映射落 press 写点;T5/出口③ 垫保登记经
        mandate.stall_buys_register(shim 同簿)。**写点扩全映射(T-141;
        ADR-0585 §6 在途件提前落)**:M2 族(obligation)/C1·④(hold)
        自此随发射落账,义务件有账可闭、线账闭合读点真实运转;行为
        零面(两类不入窗口段,身份段独立承载)。

        合成销检出(V2-05,出口②′):本笔 1★ 买入补齐同名 1★ 三张 ⇒
        执行层买入应用即自动合成 2★,登记的 1★ 副本离场(件离场闭合)
        ——发射位先销旧账,且不为本笔开账(1★ 即刻离场,press 账的
        资产对象不存在)。接线位申报:方案 v3 §3.1 理想位 = 执行层合成
        事务应用位(cw_op_buy_cards/sim 引擎,本批文件面禁碰);单动作
        契约下发射位检出与执行层应用等价(动作被无条件采纳执行),
        事务 fill 残余形态载体已随批2b R3 删除(轮界销 ≤1 轮兜底语义随原子序列重表达消亡;V2-05 有界性
        申报)。

        sim 边界(ADR-0585 §6 申报,三审 F2 回填):上述等价性前提 =
        生产单动作循环;sim/replay 序列驱动形态下引擎两个作废通道
        (仲裁预算闸拒/事务 fill 后陈旧 BuyCard 作废重决策)可作废
        已发射动作,而本发射位 consume_on_merge 已销账(同轮卖回保护
        缺口)、register_launch 已开账(≤1 轮滞留,轮界销兜底)——
        缺口有界低概率无决策行为差,sim 为测试载体生产不可达,接线
        位维持发射位不变(移位属行为面变更,候后续行为批)。

        种子获取登记(P78-7,T-126 批 5,ADR-0633):见函数尾段——
        种子账作废形态与上述 sim 边界同型(作废买入的种子账由活性
        闭合在名不在 bench 的下一读点就地销,自愈有界)。
        """
        _buy_name = getattr(card, 'name', '') or ''
        # W6 波3 贯通:record_fresh_buy 已切容器签名,帧经桥装箱。
        record_fresh_buy(session, bs, _buy_name)
        # T-263 前窗买入分键(P90① 检验点;置于合成早退前 = 全路径覆盖)。
        # 息损 = 买入跨档数(cap 消费帧 cap_resolved,与策略息账同源);
        # over_bound 断言键依据 P90①「1-2 费单价下单笔最多穿 1 档」,
        # 违反即推导失效(防御性,结构性恒 0);cost3p = P90 辖域外
        # (1-2 费)观测,买入经各臂自身授权发生,分键供越域审计。
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
        # 合成检出计数单一源 = kernel same_star_count(店内外身份计数
        # 共用,禁消费方手搓内联——落地审 §2-Ⓑ 附条件收敛行)。
        if (getattr(card, 'star', 1) or 1) == 1 \
                and same_star_count(_buy_name, 1,
                                    bench_slots_of(bs), deployed_slots_of(bs)) >= 2:
            sell_gate.consume_on_merge(session, _buy_name)
            return BuyCard(card=card, reason=reason)
        _cause = launch_cause
        if _cause is None:
            # 登记写点扩全映射(T-141;ADR-0585 §6「写点随矩阵批落」
            # 提前落):obligation/hold 类自此随发射落账——义务件有账
            # 可闭,线账闭合读点真实运转。行为零面:两类不入窗口段
            # (active_window 过滤面不变),身份段由基座/静态集独立
            # 承载;hold 过既有 W5 类资格断言,拒登记不拦发射语义不变。
            _cause = sell_gate.launch_cause_of(reason)
        if _cause is None:
            # A4 硬闸(ADR-0611):未映射
            # reason 的旧形态 = 静默跳过登记分支——新买入臂忘配映射即
            # 绕过发射登记与一切以 LAUNCH_CAUSE_BY_ARM 为臂全集的穷举
            # 断言(防复发保证的地基为假)。抛错把静默裸奔变硬闸,此后
            # 14 键穷举断言才成立;新买入臂先入映射表归入某因果类才可
            # 发射(launch_cause_of 契约同源)。
            raise ValueError(
                f'买入臂 {reason!r} 未登记 LAUNCH_CAUSE_BY_ARM 因果类'
                ' 映射(sell_gate;ADR-0611 A4 硬闸——新臂'
                ' 先入映射表归入某因果类才可发射)')
        if sell_gate.register_launch(
                session, _buy_name, cause=_cause,
                round_num=int(round_num_of(bs) or 1),
                star=getattr(card, 'star', 1) or 1,
                cost=card_cost(card)) \
                and _cause == 'obligation' and _buy_name:
            # 义务类镜像簿同步落(孤儿证明载体,见
            # _line_switch_orphans;义务类登记无资格断言恒落账,
            # 簿 ≡ 登记簿义务类视图)。
            _obligation_book(session)[_buy_name] = \
                int(round_num_of(bs) or 1)
        # 种子获取登记(P78-7,T-126 批 5,ADR-0633):1★ 引擎件 ∧
        # 购买时未持有 = 种子账开立,相邻轮(≤2 轮窗)全通道禁卖——
        # 同轮由 fresh_buys 硬面辖,本登记辖 ADR-0611 §4 P4 相邻轮残留
        # 形态(ADR-0289 设计 0 容忍的生产落地)。资格谓词单一源 =
        # sell_gate.seed_acquisition_eligible(禁调用侧手搓)。义务基座
        # 成员重叠无害(身份段本就保护)。A4 硬闸之后落账 = 仅活决策
        # 登记;合成补齐分支已提前 return(1★ 即刻离场,无种子账)。
        if _buy_name and sell_gate.seed_acquisition_eligible(
                _buy_name, getattr(card, 'star', 1) or 1,
                bench_slots_of(bs),
                deployed_slots_of(bs)):
            sell_gate.register_seed_acquisition(
                session, _buy_name,
                plane=(bs.node.value.plane if bs.node.value is not None else None),
                round_num=int(round_num_of(bs) or 1))
        return BuyCard(card=card, reason=reason)

    ev_arm = getattr(config, 'ev_arm', 'full')
    if ev_arm not in entry.EV_ARM_VALUES:
        ev_arm = 'full'
    skeleton_only = (ev_arm == 'skeleton_only')

    # ---- ① 方向(证明面投影;契约核验 = 单动作决策入口,动作后真值口径)----
    _reg = registry
    if _reg is None:
        from sr_od.application.currency_war.kernel.cw_registry import (
            DEFAULT_REGISTRY,
        )
        _reg = DEFAULT_REGISTRY
    k = getattr(state_of(session), 'target_comp', None)
    k_members = predicates.line_members(k)
    k_fallback: frozenset[str] | set[str] | None = None
    k_band: str | None = None
    _kfb_tok: str | None = None
    _kfb_source: str | None = None
    _arms = None   # P86 三臂帧判定件(p2plus 带才派生;乙臂发射位消费)
    _ist = getattr(state_of(session), 'v3_intention', None)
    if k is None and _ist is not None:
        # K 空窗回退(FIX_REVIEW_20260903 R3 扩域;经济冻结批单一源化;
        # P86 落码批:p2plus 带派生本体 = 三臂判据——甲臂判活帧成员集
        # 换源为甲臂方向采购集,甲臂空帧合法空[丙臂守息,k_fallback_source
        # 证据放行])。派生本体 = cw_intention.k_empty_window_fallback
        #(商店域与准备域共用,禁第二源);本处只保留消费面(回退采用+
        # 计数键)。ist 缺失 = 意向供给缺帧,保守侧不回退(现行 () 行为)。
        # W6 波3 贯通:k 空窗回退/三臂判据已切容器签名,帧经桥装箱。
        k_fallback, _kfb_tok = cw_intention.k_empty_window_fallback(
            bs, _ist, session=session, registry=_reg)
        k_band = f'shop_k_fallback_{_kfb_tok}'
        if _kfb_tok == 'p2plus':
            _arms = cw_intention.no_target_arms(bs,
                                                _ist, session=session,
                                                registry=_reg)
            if not k_fallback:
                _kfb_source = cw_intention.K_FALLBACK_SOURCE_THREE_ARM
            # P86 判读分键(证明批 §6 增量 1/4/7 + 正本 §4.4 行1):
            # 甲臂采用/判死出辖/漏授角/丙臂合法空四态独立分键,禁混入
            # 历史 token 计数(shop_k_fallback_p2plus 语义 = 回退采用,
            # 落码后构成 = 甲臂方向采购集,判读按新臂构成重建)。
            # F-7 口径注(落地审):hold_default = 「合法空/契约通道显影」,
            # 判死帧即计、先于乙臂发射位——同帧乙臂发射时两键并发,
            # 「守息帧」直读须按 dead_defer+adopted/hit 联合口径修正。
            if _arms is not None and _arms.direction:
                _count('shop_no_target_arm_a_adopted')
            elif _arms is not None:
                _count('shop_no_target_arm_a_dead_defer')
                if _arms.corner_names:
                    _count('shop_no_target_arm_a_corner_defer')
                _count('shop_no_target_hold_default')
    # 契约核验(可核验派生形态;P86 带维度非对称期待,证明批 §4.6):
    # 回退字面量空元组但保留声明 = 违例 ⇒ 不回退 + 计数;p2plus 带合法空
    # 仅在 source 标明判据臂评估产出时放行。sorted = 确定性发射序(str 哈
    # 希随机化防御)。
    if contracts.ensure_contract(
            ('shop', 'k_projection'),
            contracts.ContractCtx(k_target=k,
                                  k_fallback_available=_ist is not None,
                                  k_fallback_resolved=k_fallback,
                                  k_fallback_band=_kfb_tok,
                                  k_fallback_source=_kfb_source),
            counters) and k_fallback:
        k_members = tuple(sorted(k_fallback))
        _count(k_band)
    # 锁定帧(locked_comp 非空)买面口径拆分(T-307/R1 起两面,ADR-0647;
    # 单一源 = cw_intention.locked_buy_membership):
    # - 义务面 ``obligation_members`` = 容量可行截断集 B'(cap_hold 现读;
    #   序 = core∪shared ≻ 其余同级,级内 cost 升序声明序 tie-break)——
    #   消费面 = 缺员派生(M2 义务循环)与线账闭合孤儿证明集(义务账本
    #   语义:孤儿 = 曾义务离场,义务口径随 B')。截断使 missing(B')
    #   可清空 ⇒ M2 终止条件恢复(T-295-P1 停摆不动点解除);
    # - 囤货/观察面 ``buy_members`` = 锁定采购集宽集(不截断)——消费面 =
    #   m2_stockpile 囤腿/M2b 合并完成买入(囤货面,息律/预算辖;截断会
    #   制造「不可完成又不可卖」死库存)、拒因遥测(观察面,W65 锁内成员
    #   标签语义保持)、EV 排除集/R1 刷新账/P92 囤腿费带(表外既有面,
    #   本批零漂移)。购买侧与锁定侧同源,锁内成员经 M2 义务买入、不再落
    #   non_line 拒因(实机对局 g_20260905_035710 双源断裂修复面不变);
    # - ``k_members`` 保持 comp core∪shared 口径(M4 fuel_sell_candidates/
    #   funding_support_sell 的 zero_overlap 卖免判定、R1/R2 刷新账合格集
    #   P40 A4「目标阵容件」口径)——锁定全集若灌入卖免面,bench 被
    #   hoard 低星成员塞满后腾席候选空集、缺员买不进(滞留换拍复发);
    #   灌入刷新账则判据行为翻转无数学重推背书。两处均按「无证明重推
    #   不翻转」维持原口径。
    # 未锁帧两集相等(membership 返回 None),P1 无锁态零变化。
    _buy_members = cw_intention.locked_buy_membership(_ist)
    buy_members = tuple(sorted(_buy_members)) if _buy_members else k_members
    _obligation_raw = cw_intention.locked_buy_membership(
        _ist, cap_hold=cw_intention.locked_buy_cap_hold(bs))
    obligation_members = (tuple(sorted(_obligation_raw))
                          if _obligation_raw else k_members)
    # P60 容量超限告警门(T-307/R1 修正:检查对象 = 截断前宽集,分母 =
    # cap_hold = BENCH_CAPACITY + max_units(level) 现读;ADR-0647):
    # |宽集| > cap_hold = 义务面已截断、截断前宽集缺员出口结构性不可达
    # 的形态——截断集上检查恒假 = 死观测面,故检查宽集;旧固定分母
    # 9+10=19 高估实用容量(lv8=17),|B|=18 已不可达而不告警。
    _cap_hold_now = cw_intention.locked_buy_cap_hold(bs)
    if _buy_members and _cap_hold_now is not None \
            and len(_buy_members) > _cap_hold_now:
        _count('shop_hoard_over_capacity')
        log.warning('[cw!][shop] 锁定采购集 |B|=%d > 实用容量上界 '
                    'cap_hold=%d(bench 9 + 上阵 %d):义务面已截断,宽集'
                    '缺员出口结构性不可达,换手循环诚实停摆形态可见(证据='
                    '换手对/m2_retry_exhausted 计数;ADR-0647)',
                    len(_buy_members), _cap_hold_now,
                    _cap_hold_now - BENCH_CAPACITY)
    # 线账闭合孤儿证明集(T-141 乙′;ADR-0591 §4;T-307/R1 起基座随 B',
    # ADR-0647):帧首计算,必须先于本帧任何装配 A 读点(P56 投影/M4/
    # 凑息/支付变现)——A 身份段会就地销账,销账后登记面不可再辨
    # 「曾义务」。base 传义务面 B'(义务账本语义:R1 后 M4 按设计卖出
    # 被截成员非账闭合事件,基座保宽会把设计内卖出误标孤儿)。未锁帧
    # 与截断未触发帧两口径同集,判读零漂移。
    _sw_orphans = _line_switch_orphans(
        session, set(obligation_members),
        int(round_num_of(bs) or 1))
    bench = [b for b in bench_slots_of(bs) if b is not None]
    deployed = [d for d in deployed_slots_of(bs) if d is not None]
    bench_names = [b.char_id or '' for b in bench]
    deployed_names = [d.char_id or '' for d in deployed]
    # 滞留素材显影(分键,本体 = ``count_material_stale`` 单一源)。
    count_material_stale(counters, session, bench, deployed,
                         int(round_num_of(bs) or 1))
    owned = set(bench_names) | set(deployed_names)
    # 契约核验:stop_buy 消费位(前提恒真 None 登记,违例路径仅剩未登记键)
    stop_flag = proof.stop_buy(k, bench_names, deployed_names) \
        if contracts.ensure_contract(
            ('proof', 'stop_buy'), contracts.ContractCtx(), counters) \
        else True   # 弃权侧=保守停买——辖域限支配买/溢余面;M2 义务不走
                        # 停手门([41]),不受本弃权影响

    # ---- ② 预算投影(期望态当前值;帧首快照口径随波批退役,ADR-0517
    # §消灭的 bug 类·金位买后逻辑态族——期望态金即动作后真值,无口径可言)----
    cap_resolved = mandate._cap_of(session)
    g_star = saturation_line(cap_resolved)
    # P56 可变现息线下界(设计 13_buy_face_design §2.2):s_reserve :=
    # g* − Σ活期退金投影;活期集合以期望态现值计(M4 卖出的活期件在下一
    # 决策帧自然离开集合——旧「帧内即时扣减」专修无存在载体)。
    # T3 边界申报:本投影不改吃 defer(保护集)——门槛7 买入判据保持
    # 既有口径(触发判据不动,修复只落协调层卖侧读端);同轮多笔被保
    # 买入帧回拉缺口闭合可能不足,失败形态 = 金留 g* 之下真实持有,
    # 非自旋(t1_interest_gap/sellback 差值可判读,见 criteria/sell 申报)。
    # 拦截事件去重集(C1 口径:同一决策帧内同一素材名只计 1)——本帧
    # 内所有守卫触达位(P56 投影读/M4 腾席资格评估/凑息/支付变现/换线)
    # 共享,投影读与真卖评估不再重复计数;单一源 =
    # ``cw_state.count_merge_material_blocked``。
    _mm_dedup: set[str] = set()
    # 排除集 = 统一装配 A 全量形态(单一入口 sell_gate;P78-6 读端同源,
    # 方案 v3 §2.9 新格 B/V2-08):投影位「读」的资格面必须与凑息发射位
    # 同一——本位旧形态只排 buy_members,漏静态持有两集(③④件在 bench
    # 不入凑息资格却被计入可变现投影 → liquid_refund 高估 → s_reserve
    # 低估 → 预留被吃)。批 2 身份段先行、批 3 补齐全资格面:projection
    # 视图 = 身份段 ∪ 窗口段(press 登记活跃帧不可变现,W1 同源)∪
    # T3 活跃集(凑息对垫保是资格级绝对跳过,criteria/sell.py:140-148,
    # 投影漏 T3 则 liquid_refund 仍高估;通道侧 defer 参数语义零改,M7)。
    _p56_excl = sell_gate.sell_exclusions(session, k_members,
                                          channel='projection',
                                          cap_hold=_cap_hold_now,
                                          current_round=int(
                                              round_num_of(bs) or 1))
    liquid_refund = sum(sell_refund(1, bench_char_cost(b))
                        for b in mandate.fuel_sell_candidates(
                            bench, k_members, state=bs,
                            exclude_names=_p56_excl, counters=counters,
                            dedup_names=_mm_dedup))
    # 口径注(P56 投影位):上面这步是为 s_reserve 投影而「读」资格集
    # (非卖出发射),``counters`` 照传时经 _mm_dedup 与本帧真卖评估位
    # 去重——``merge_material_guard_blocked`` = 拦截事件数(每帧每素材
    # 至多 1),非评估次数;投影读可能占首计(素材首次触达发生在本投
    # 影读),判读时按帧级事件语义解读(ADR-0558 §4 F-2 消费面)。
    s_reserve = g_star - liquid_refund
    tier_w, card_w = _frame_search_windows(session, bs, _reg, counters)
    gold = gold_of(bs)
    bench_free = BENCH_CAPACITY - len(bench)
    # 锁线转型域 D 帧旗(T-190 批 B;P88,ADR-0627):S_spec 收窄辖域,
    # 仅 dominance/hub 两发射位消费。域谓词单一源 = mandate.
    # swap_transition_narrow_frame(kernel _swap_transition_domain_of 同
    # 一谓词,禁第二份合取);域外帧旗恒 False = 本批零行为面。
    _narrow_frame = mandate.swap_transition_narrow_frame(bs, session)
    # ---- T-263 前窗/零成型帧旗(P90 面①;谓词单一源 = statefn/predicates,
    # 命题 = math_proofs P90-P94,ADR-0635)----
    # 前窗 = P1 首个战斗节点前窗(节点表查表定义,01 §8-1 位面参数化);
    # 零成型 = 四体系激活档全 0(per-体系谓词,engines_count 合计标量
    # 禁用口径)。表缺 = 前窗行为 fail-closed 不发生(现行为),分键显影。
    _front_window = predicates.front_window_frame(bs, session)
    if (bs.node.value.plane if bs.node.value is not None else None) == 1 \
            and not predicates.front_window_table_ready(session):
        _count('p90_front_table_missing')
    _zw_armed = False
    if _front_window and predicates.zero_form_frame(deployed):
        _zw_armed = True
        _count('p90_zerostack_frame_armed')
        if not any(predicates.advances_four_system(
                getattr(c, 'name', '') or '') for c in shop_payload_content_cards(bs.shop.value)):
            # 面①(b) 四分键之三:触发帧店无可激活件(输入死观测位)
            _count('p94_no_activatable')
        elif provisional.is_none('U_X'):
            # 面①(b) 四分键之三:放行层豁免拒绝——P94 待证明件,u_x 属
            # 在册【拟】🔴 标定债,豁免恒拒(fail-closed 维持现行为;
            # p94_exemption_grant 无代码路径,待 P94 证明+标定批落授权)。
            _count('p94_exemption_refuse')
    # 拒因遥测逐帧刷新(ADR-0517 迁移步 2:拒因计数键逐动作化;期望态
    # 即真值,actions 传空——买走牌已由 project 从 state.shop 摘除)。
    # P86:乙臂枢纽资格集直传(拒因键 hub_option 的单一源直通面)。
    with contextlib.suppress(Exception):
        # 拒因遥测 = 观察面宽集口径(T-307/R1,ADR-0647:W65 锁内成员
        # 标签语义保持,R1 截断不辖观察面)。
        state_of(session).cw4_shop_rejects = shop_unbought_reasons(
            bs, k, buy_members, [],
            hub_names=frozenset(_arms.hub_names)
            if _arms is not None else frozenset())
    missing = [m for m in obligation_members if m not in owned]   # 义务面 B'(T-307/R1,ADR-0647)
    # T3 同轮保留集卖侧读端(单一源 = mandate.stall_protect_active,禁
    # 手搓读 cw4_fuel_filler_stall_buys):本帧活跃保护名集;轮界过期名
    # 在此就地销账(t3_protect_expired_round 分键)。语义 = 末位牺牲序,
    # 非绝对禁卖:凑息回拉绝对跳过,M4 腾席/支付变现仅降序放行(转化类)。
    _t3_protect = mandate.stall_protect_active(
        session, round_num_of(bs), counters=counters)

    # ---- L2 卖后禁买:全买入臂统一过滤位(ADR-0611 §3-3)----
    # 单一事实源 = mandate.round_sold_names(档 2 键式相位载体,写端 =
    # 各卖出发射位 record_round_sold 收口,零新载体零新阈值);判定单一
    # helper = mandate.sold_this_round。形态申报(新建结构如实申报,
    # ADR-0611 §2):
    # 「新建统一过滤位」——各买入臂候选枚举改经本帧级视图单点
    # (_buy_view / _shop_candidates 过滤),臂层零手搓读法,防「第七臂
    # 绕过新鲜度」复发;直读 state.shop 的买入候选路径已全量收口。
    # 分键显影(C6/ADR-0604 §3-5 扩域候观测键判读载体):按触发臂归因
    # 分键 <arm>_round_sold_excluded(M6 沿用既有 m6_round_sold_excluded
    # 键名零断链),逐臂排斥可观测、禁静默。
    _round_sold = mandate.round_sold_names(session, bs)

    def _buy_view(arm_key: str) -> list[ShopCard]:
        """店内卡全集的 L2 过滤视图:剔除「本轮已卖名集」命中卡,
        按触发臂分键显影(arm_key 只进计数键,不进判据)。
        零成型帧(前窗∧四体系零成型,P90 面①(b) 排序层)追加稳定
        排序——四体系推进件前移(P20 方向级背书,非金量纲、不构成
        支出放行:全臂既有门照过,仅改同门通过时的取件序);非零成型
        帧零漂移。"""
        out: list[ShopCard] = []
        for c in shop_payload_content_cards(bs.shop.value):
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
        if m and mandate.sold_this_round(session, bs, m):
            # 按名查店内卡路径的 L2 过滤(arm_key 空 = 观测快照位,
            # 过滤不计数——快照口径与买入面同源一致,T-161 F2 同闭包)。
            if arm_key:
                _count(f'{arm_key}_round_sold_excluded')
            return []
        return sorted(
            (c for c in shop_payload_content_cards(bs.shop.value) if (c.name or '') == m),
            key=lambda c: (card_cost(c)))

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
            state_of(session), 'cw4_recent_sold_names', ())
        if churn:
            _count('shop_churn_pair_buy')   # 换手对:与 drought 状态无关恒计
        ls = getattr(state_of(session), 'cw4_line_state', None)
        if ls is not None and getattr(ls, 'drought', 0):
            ls.drought = 0
            _count('shop_drought_reset_on_churn_buy' if churn
                   else 'shop_drought_reset_on_buy')

    def _note_sell(name: str) -> None:
        """卖出记认(P60 换手对观测面):本 visit 卖出件名入近期卖出集,
        后续买入命中 = 义务换手对。定长截断防长 visit 无界增长。
        另写轮内卖出登记(泄金阶梯档 2 新鲜度排除写端,单一源 =
        mandate.record_round_sold;同轮卖X买回X再卖X禁,模拟批#5 s108
        实证)——本函数 = shop 域全部 SellBench 发射位的共同收口,
        凑息回拉/M4 腾席/支付变现四发射位零遗漏。"""
        if not name:
            return
        recent = getattr(state_of(session), 'cw4_recent_sold_names', None)
        if recent is None:
            recent = []
            state_of(session).cw4_recent_sold_names = recent
        recent.append(name)
        del recent[:-16]
        mandate.record_round_sold(session, bs, name)

    # T-82 事件粒度辖记(初始化先于 M4 块:bench_full_buy_abandon 发射位
    # 与 M4 块两处消费同一布尔,条件谓词相同但独立书写,防未来耦合)。
    _m2_stall_hit = False
    # M4 腾席(买入遇 bench 满:现场卖 1 燃料件,R8-8 单帧闭环)。
    # P60:燃料集排除义务基座(exclude_names)——义务换手通道闭死,
    # |B|>容量时走 m2_retry_exhausted 诚实停摆而非永恒卖 1 买 1。
    # T-307/R1(ADR-0647)起义务基座 = 截断集 B'(sell_gate._resolve_base
    # 单点解析):被截成员(∉B')M2 不再义务重买 ⇒ 保护必要性消失,
    # 可入腾席候选(死锁解除主链);B' 内成员照旧禁卖(义务换手闭死
    # 语义不变)。
    # T-82 续段缓存:上帧动作 ∈ 白名单 ∧ token/闩序号均 == 当前段序号 ∧
    # 闩结论=腾席无候选 ⇒ 扫描输入逐项不变 ⇒ 拒绝确定性复现,跳过扫描
    # (弱支配:发射序列逐位一致;P56 投影位每帧照常触达,不受本缓存
    # 影响)。计数从帧粒度回到事件粒度:命中帧两事件键不增,改计
    # m2_stall_repeat_frame(风暴量级保留可见);段首/失效后重推导帧两
    # 事件键照计 + m2_stall_cache_rederive。
    if missing and bench_free <= 0:
        _seg = _st.cw4_segment_serial
        _latch = _st.cw4_m2_stall_latch
        if (_frame_token is not None
                and _frame_token[0] in M2_STALL_NONVARIANT_SHOP_ACTIONS
                and _frame_token[1] == _seg
                and _latch is not None and _latch[0]
                and _latch[1] == _seg):
            _m2_stall_hit = True
            _count('m2_stall_cache_hit')
            _count('m2_stall_repeat_frame')
        else:
            # 排除集升级 → 统一装配 A 全量形态(单一入口
            # sell_gate;ADR-0585):义务基座与装配单点同源(T-307/R1 起
            # = 截断集 B',sell_gate._resolve_base 解析;ADR-0647),
            # 静态持有两集生效——W4 修法(shop_sell 攻击
            # 报告 W4;P78-4):M4 腾席对 ③④ 持有 1★ 件禁卖 = P41 燃料
            # 类资格本义,③④ 持有换手震荡通道闭死,腾不出席走
            # m2_retry_exhausted 诚实停摆。批 3 窗口段生效(press 登记
            # 活跃帧腾席同禁,P78 INV 通道无关)。
            _m4_excl = sell_gate.sell_exclusions(session, k_members,
                                                 channel='m4_fuel',
                                                 cap_hold=_cap_hold_now,
                                                 current_round=int(
                                                     round_num_of(bs) or 1))
            cands = mandate.fuel_sell_candidates(bench, k_members, state=bs,
                                                 exclude_names=_m4_excl,
                                                 defer_names=_t3_protect,
                                                 counters=counters,
                                                 dedup_names=_mm_dedup)
            if cands:
                victim = cands[0]
                ok4, _ = mandate.check_irreversible(victim.char_id or '', k_members)
                if ok4:
                    idx = bench_slots_of(bs).index(victim)
                    _vname = victim.char_id or ''
                    # T3 末位牺牲序命中 + 卖出销账(生命周期出口②):
                    # 被保件是唯一燃料 ⇒ 放行卖出(为义务买入腾位的转化类;
                    # 销账 = 行为面保留)。纯归因分键计数已随 2026-09-08
                    # 用户归因遥测删除指令拆除。
                    _prot_hit = _vname in _t3_protect
                    if _prot_hit:
                        mandate.stall_buys_consume(session, _vname)
                    _note_sell(_vname)
                    # reason 仅存线账闭合孤儿证明标记(T-141/ADR-0591:
                    # 本轮义务登记且已出基座的 victim,键带账闭合证明供
                    # 同轮买卖检查豁免面分键,通道无关);纯归因通道值/
                    # 特化值填充已删,'' = 未标缺省形态。转化类豁免分键
                    # 走结构化字段 convert_reason(ADR-0611 §3-5:
                    # 值域收窄两类放行键;孤儿键留 reason,零双源)。
                    # 发射 = 中间步动作:卖出真执行腾出 1 席,下一决策
                    # 迭代 bench_free ≥ 1 由 M2 原判据买入;CloseShop 在
                    # 此处等于把「有后续意图」表达成「终结」——商店段
                    # 提前收口,升级/刷新通道整段不可达(T-238 修复)。
                    return SellBench(bench_idx=idx,
                                     income=_shop_sell_refund(victim),
                                     expect=_vname,
                                     reason=('line_switch_collapse'
                                             if _vname in _sw_orphans
                                             else ''),
                                     convert_reason=(
                                         'fuel_victim_protect_demoted'
                                         if _prot_hit else ''))
            else:
                _count('m2_retry_exhausted')
                _count('m2_stall_cache_rederive')
                _st.cw4_m2_stall_latch = (True, _st.cw4_segment_serial)

    # P86 乙臂发射位(枢纽期权;unlocked p2plus 无目标带;物理位次先于 M2
    # = 同帧仲裁三层序的承载,证明批 §4.4/§6 增量 1)。获取 = 备战席持有
    # (免费期权),行权 = 部署/组线归部署域既有管辖,零新增行权授权;
    # 持有期租金残余由 M4 腾席/P41③ V_slot 现行管辖吸收(正本 §6.1)。
    # 五前件合取 = 资格核(kernel.hub_option_names:覆盖数≥2 ∧ 非单卡注册
    # 身份)+ 非合并素材(第五前件,P75 原子⑩同款)+ 四谓词核
    #(1★ 全额退/席位/不破息/可负担,与 C1 锁线腿同源单一实现)。
    # 甲乙并存帧仲裁:支配序(覆盖甲臂方向线的枢纽先于该方向**单线**方向
    # 件,推论 B1.1;多线方向件不授件级支配)→ 机器原生序(甲臂方向已由
    # kernel 机器自身选择序定,本位不动)→ 注册表声明序(资格核枚举序;
    # 枢纽与在售方向件竞争按卡声明序首发判定)。覆盖数降序已否决(集合
    # 包含单调性 ≠ 基数单调性,非嵌套集合无授权比较,§4.4 显式否决)。
    # 乙臂收窄分键帧内去重(T-190 批 B):D 帧停发为帧级事件,候选循环
    # 内首见笔计数一次(与 dominance 位同款帧级口径)。
    _hub_narrow_counted = False
    if _arms is not None and _arms.hub_names:
        _hub_set = set(_arms.hub_names)
        _hub_cands = sorted(
            (c for c in _buy_view('hub_option_buy')
             if refund_full_star_ok(c.star or 1, card_cost(c))
             and (c.name or '') in _hub_set),
            key=lambda c: cw_intention.char_declaration_index(c.name or ''))
        # ↑ 候选序 = 注册表声明序(资格核枚举序同源)——店面槽位序不进
        # 仲裁(乱序注入店面发射序不变,增量 1;hub-hub 并列同序兜底)。
        # ↑ 星级腿(攻击 r1 发现5):1★ 过滤走 refund_full_star_ok 单一源
        #(1★ 全档净 0 恒真/2★+ 恒假,与本面原内联 (star or 1)==1 等价;
        # 防「乙臂只吃半边退金表」的演化期静默分叉)。
        if _hub_cands:
            _count('hub_option_candidate_seen')
            # 发射时点 t5 输入(与 C1 锁线腿同源:r_remaining/net_income;
            # Ī 取 streak_pre=0 保守近似——收入低估 ⇒ L 偏大 ⇒ 发射收窄)。
            _hub_rounds = horizon.r_remaining(
                session, plane_of(bs), round_num_of(bs))
            _hub_ibar = net_income(round_num_of(bs), 0)
            # 在售缺员方向件声明序(第三层让位判定的输入;店面槽位序无关
            # ——乱序注入店面发射序不变,§6 增量 1 测试化)。
            # F-1(落地审,证明批 §4.4 先决澄清+附带条款①):竞争域收窄
            # ——仅本帧**可发射**(金/席快判过)的在售缺员方向件获挤占权,
            # 合取不过的方向件不因序获得挤占权,否则甲帧上更早声明的
            # 不可负担件会逐帧挤掉枢纽发射机会。
            _dir_name = _arms.direction
            _piece_in_shop = []
            _ok_seat_all, _ = mandate.check_seats(
                bench_free, 0, needs_bench=True, needs_board=False,
                name='', deployed_names=deployed_names)
            for _m in missing:
                if not _m:
                    continue
                _mcands = _shop_candidates(_m)
                if not _mcands:
                    continue
                if not _ok_seat_all:
                    continue    # 帧级席满:任何方向件本帧皆不可发射
                _mcost = card_cost(_mcands[0])
                _ok_aff, _ = mandate.check_affordable(gold, _mcost)
                if _ok_aff:
                    _piece_in_shop.append(_m)
            for card in _hub_cands:
                _hname = card.name or ''
                if _dir_name:
                    # 仲裁三层序(逐在售方向件判定,§4.4 候选级序):
                    _covers = _dir_name in cw_intention.hub_covered_lines(
                        bs, _ist, _hname)
                    _yield = False
                    for _m in _piece_in_shop:
                        # 第一层授权面(推论 B1.1 收窄):仅 C_x == {l_d} 的
                        # 单线方向件受支配序辖——枢纽覆盖多线时件级比较无
                        # 定理授权,一律降第三层声明序。
                        if _covers and cw_intention.hub_covered_lines(
                                bs, _ist, _m) == frozenset({_dir_name}):
                            continue    # 第一层支配序:枢纽先于单线方向件
                        if cw_intention.char_declaration_index(_hname) > \
                                cw_intention.char_declaration_index(_m):
                            # 第三层注册表声明序:更早方向件首发,本帧让位
                            # (M2 先发;次帧重评,竞错代价由 1★ 全退可逆封顶)
                            _yield = True
                            break
                    if _yield:
                        _count('hub_option_arbitration_yield')
                        continue
                # 非合并素材第五前件(获取时点不与在场同名同星 1★ 副本构成
                # 即时合并素材,保住 1★ 净 0 出口;核对面 = bench∪deployed
                # 全场域,计数单一源 = cw_state.same_star_count 禁手搓同式;
                # 买面阈值 = 场内已有 ≥1 副本即拒 = 获取后 c_excl≥1 的
                # merge_material_reject_reason 同式视点,副本在部署面同拦)。
                if same_star_count(_hname, 1, bench, deployed) >= 1:
                    _count('hub_option_reject_merge_material')
                    continue
                cost = card_cost(card)
                ok2, _ = mandate.check_seats(
                    bench_free, 0, needs_bench=True, needs_board=False,
                    name='', deployed_names=deployed_names)
                if not ok2:
                    _count('hub_option_reject_seats')
                    break       # 帧级门已拦 bench 满(C1/支配族同款防御)
                if not predicates.t5_p1_false(
                        gold, cost, _hub_rounds, _hub_ibar, cap_resolved):
                    _count('hub_option_reject_interest')
                    continue    # 不破息带:L>0 帧不放行(丙臂同带同纪律)
                ok1, _ = mandate.check_affordable(gold, cost)
                if not ok1:
                    _count('hub_option_reject_unaffordable')
                    continue
                if _narrow_frame:
                    # 锁线转型域收窄(T-190 批 B;P88,ADR-0627):D 帧
                    # hub_option_buy 停发(S_spec 辖域前置)。hub 辖
                    # unlocked 与 locked D 域结构性不相交(设计 v2 修订 10
                    # 空开火面申报)——本谓词 = P86 辖域变更的防御性哨兵,
                    # 预期恒 0 开火,判读禁并桶进 dominance 位键
                    #(press_narrowed_transition_domain_hub 独立分键)。
                    if not _hub_narrow_counted:
                        _count('press_narrowed_transition_domain_hub')
                        _hub_narrow_counted = True
                    continue
                _count('hub_option_buy_hit')
                # F-3 载体(P86 正本 §6.1;P75 §7.4 先例):乙臂获取名集
                # 单一写点(session 载体,零分支去重)。**先登记后 emit**:
                # 本笔的 hold 类登记资格域(攻击 r1 面①)与装配 A 身份段
                #(面②)在本发射内即消费本名集;面③ = 部署域行权显影
                #(cw_op_deploy 读端,deployed_from_hub)。
                _hub_held = getattr(state_of(session),
                                    'cw4_hub_acquired_names', None)
                if _hub_held is None:
                    _hub_held = []
                    state_of(session).cw4_hub_acquired_names = _hub_held
                if _hname and _hname not in _hub_held:
                    _hub_held.append(_hname)
                # 买因 = hold 类(LAUNCH_CAUSE_BY_ARM 映射行,P86 随批登记)
                return _emit_buy(card, 'hub_option_buy')

    # M2 线成员买入(序 1/2 义务;[41]:义务不走息律门)。金不足侧:
    # 支付支撑通道在 R1 拒后的发射位处理(卖一张回此帧重判)。
    # bench_full_buy_abandon 同受 T-82 事件粒度辖(_m2_stall_hit 命中帧
    # 不增——与 m2_retry_exhausted 同一停摆事件的两投影键,粒度必须一致,
    # 否则事件数与帧数两口径混计)。
    if bench_free <= 0 and missing and not _m2_stall_hit:
        _count('bench_full_buy_abandon')
        # T-159 迁移 A:S2 wanted 残差置位(唯一写点 = mandate.shop_
        # wanted_defer)。挂本点 = 两投影键的超集位(同帧不双计;
        # m2_retry_exhausted 分支为其子事件——腾席候选空的强形态)。
        # 席满残差的结构性流失(猎点 10)自此有载体:回备战后由消费臂
        # 评估腾席/重进,买入机会不再丢失至下节点。
        # T-161 F2 前件快照(方案审 F2-1/F2-6,ADR-0599):「在店的
        # 缺员 (名, 费用)」子集必须由本调用位经同一 _shop_candidates
        # 闭包计算(禁 mandate 侧复刻第二份候选读法)——消费臂时点商店
        # 域字段已被 obs 清空(ADR-0462),臂时点现读恒空会把闭环闷死。
        # 口径:M2 语义取同名最便宜卡(不滤星,区别于 stockpile 1★
        # 过滤),cost 假值兜 3 与排序键一致,空名(识别失败占位)不进集。
        _wanted_snap: list[tuple[str, int]] = []
        for _m in missing:
            if not _m:
                continue
            _cands = _shop_candidates(_m)
            if _cands:
                _wanted_snap.append(
                    (_m, card_cost(_cands[0])))
        mandate.shop_wanted_defer(
            session, bs, missing, in_shop_snapshot=tuple(_wanted_snap))
    for m in missing:
        if bench_free <= 0:
            break
        shop_cands = _shop_candidates(m, 'm2')   # L2 统一过滤位(逐臂分键)
        if not shop_cands:
            continue
        card = shop_cands[0]
        cost = card_cost(card)
        ok1, _ = mandate.check_affordable(gold, cost)
        if not ok1:
            continue
        _on_target_buy(card.name or m)
        # 买因分键按线成员资格拆分(局21 g_20260906_021859 复盘候选3:
        # 锁定采购集扩展成员(阵营∪流派,非 comp core∪shared)曾与真线
        # 成员共用 'm2_line_member',同名异源买因不可辨——砂金/花火被记
        # 线成员即此失真)。成员集单一源不变:两侧仍同吃
        # cw_intention.locked_buy_membership(T-307/R1 起本循环吃截断集
        # B'、拒因遥测吃宽集,ADR-0647 两口径声明),本处只拆标签不拆源。
        # 未锁帧两集 == k_members ⇒ 恒走线成员键,零漂移。
        return _emit_buy(card, 'm2_line_member' if m in k_members
                         else 'm2_locked_member')

    # m2_stockpile(臂①囤腿,j=1 第二份;14号稿 §3.2-3.4,发射位次 =
    # M2 主循环之后、M2b 之前,理由键 'm2_stockpile'):
    # 成员集分叉声明(编排者存-2 裁决 = 有意设计):本臂循环 buy_members
    # (锁定采购集宽集,T-307/R1 起显式囤货面口径,ADR-0647)而
    # arm0_need 只量 k_members——囤腿件走合成→上板,部署/升级授权面只量
    # 可部署现量,两口径禁混。R1 截断不辖本臂(囤货面裁决:截断会制造
    # 「不可完成(B' 不含)又不可卖(G-S1 合成素材拒入燃料)」死库存)。
    # 触发 = m ∈ buy_members ∧ cnt1(m)==1 ∧ cnt2(m)==0(二-1:cnt2>0 帧
    # 臂①不判,防制造 cnt1=2∧有2★ 死库存)∧ 店内有该成员 **1★** 在售,
    # 或仅同名 **2★ 直出**在售(P77 缺口面1 比较子,ADR-0626;N7 星过滤:
    # 候选锚按 name 过滤不分星,取卡按星择路——1★ 直取,2★ 过比较子);
    # 单提案至多购 1 张(F2 防御性上限——merge §2.5 自动多买在 j=1 帧的
    # 辖域未核,宁少买不多买,确认后如允许多买走规格修订)。
    # 拒因序 = 金闸前置 → M4 腾席(落地审清单存-1,20260905_cp1_landing_review/问题清单.md:j=1 囤腿优先级低于缺员,
    # 满栏+金不足帧禁「先卖燃料件再报 unaffordable」的不可逆净损);拒因
    # 计数粒度申报 = 每成员命中一笔(帧内多成员可累计,与 visit 粒度键
    # 对拍时须声明,清单低-2)。bench 满 → M4 腾席(Y5:02 §3 M2 硬约束
    # 同构,腾席后仍满记 'bench_full' 普通席闸键,非 merge_bench_full);
    # 金不足记 stockpile_unaffordable;cnt 达标但店内仅同名 2★ 直出卡:
    # 过比较子(ADR-0626)后仍不买(p=0 不可评域/溢价≤0)⇒
    # m2_stockpile_star_mismatch 分键(W4 零静默,与 M2b 分键,清单低-1);
    # 过比较子后闸失败落各自闸键,不再落本键(语义拆分申报随批)。
    def _cnt(name: str, star: int) -> int:
        """同名同星副本计数(全局面 bench∪deployed;14号稿 §3.5 单一源:
        按 (名,星) 分星计数,2★ 成件不折算 1★)。"""
        return sum(1 for c in bench + deployed
                   if (c.char_id or '') == name and (c.star or 1) == star)

    for m in buy_members:
        if _cnt(m, 1) != 1 or _cnt(m, 2) != 0:
            continue
        all_cands = _shop_candidates(m, 'm2_stockpile')   # L2 统一过滤位
        cands1 = [c for c in all_cands if (c.star or 1) == 1]
        # P77 缺口面1(ADR-0626):j=1 帧同名 2★ 直出现货此前被星过滤
        # 单侧拒,现过比较子(DIY 账 vs 现货账)后同闸序放行;比较子
        # None(p=0 不可评域/溢价≤0/无 2★)维持星过滤拒。
        _spot2 = spot2_direct_out_card(
            all_cands, m, level_of(bs),
            refresh_cost_effective(None, 0, bs=bs)) \
            if not cands1 else None
        if _spot2 is not None:
            card = _spot2
            cost = card.cost or 3 * int(CHARACTERS[m].cost)
        elif cands1:
            card = cands1[0]
            cost = card_cost(card)
        else:
            if all_cands:
                _count('m2_stockpile_star_mismatch')   # W4:比较子后仍不买(不可评域/溢价≤0),分键非静默
            continue
        ok1, _ = mandate.check_affordable(gold, cost)
        if not ok1:
            _count('stockpile_unaffordable')
            continue
        if bench_free <= 0:
            # M4 腾席(Y5):j=1 帧不合成,满栏例外不辖;卖 1 燃料件
            # 后下一帧 bench_free ≥ 1 即合法买入。排除集 = 统一装配 A
            # 全量形态(与 M2 缺员腾席位同源,单一入口 sell_gate;W4/P78-4
            # 同格:③④ 持有件退出燃料资格,禁与臂① 囤腿件换手;批 3
            # 窗口段生效)。
            _m4_excl = sell_gate.sell_exclusions(session, k_members,
                                                 channel='m4_fuel',
                                                 cap_hold=_cap_hold_now,
                                                 current_round=int(
                                                     round_num_of(bs) or 1))
            cands = mandate.fuel_sell_candidates(bench, k_members,
                                                 state=bs,
                                                 exclude_names=_m4_excl,
                                                 defer_names=_t3_protect,
                                                 counters=counters,
                                                 dedup_names=_mm_dedup)
            victim = cands[0] if cands else None
            if victim is not None:
                ok4, _ = mandate.check_irreversible(victim.char_id or '',
                                                    k_members)
            else:
                ok4 = False
            if victim is not None and ok4:
                idx = bench_slots_of(bs).index(victim)
                _vname1 = victim.char_id or ''
                # T3 末位牺牲序命中 + 卖出销账(同 M4 腾席位;纯归因
                # 分键计数已随 2026-09-08 用户归因遥测删除指令拆除)
                _prot1 = _vname1 in _t3_protect
                if _prot1:
                    mandate.stall_buys_consume(session, _vname1)
                _note_sell(_vname1)
                # reason 仅存线账闭合孤儿证明标记(T-141/ADR-0591,同
                # M2 位);纯归因填充已删,'' = 未标缺省形态。转化分键 =
                # convert_reason(同 M4 位,ADR-0611 §3-5)。发射 = 中间
                # 步动作(同 M4 缺员腾席位):卖出真执行,下一决策迭代
                # 席空由本臂原判据买入;CloseShop 会提前终结商店段
                #(T-238 修复,机制同 M4 位注释)。
                return SellBench(bench_idx=idx,
                                 income=_shop_sell_refund(victim),
                                 expect=_vname1,
                                 reason=('line_switch_collapse'
                                         if _vname1 in _sw_orphans
                                         else ''),
                                 convert_reason=(
                                     'fuel_victim_protect_demoted'
                                     if _prot1 else ''))
            _count('bench_full')
            continue
        _on_target_buy(card.name or m)
        if _spot2 is not None:
            _count('m2_stockpile_spot2_buy')   # W4(ADR-0626):2★ 现货达成路线显影;义务 reason 键不扩闭集
        return _emit_buy(card, 'm2_stockpile')

    # M2b 升星合并完成买入(实机复盘 g_20260904_054904 p2r1 候选②):
    # 已持 2 张同名同星 1★、无 2★ 成件,第三张在店 affordable ⇒ 买入即
    # 合成 2★。义务通道不走息律门([41] 同 M2)。
    # T-307/R1 显式裁决(ADR-0647):本循环吃宽集 buy_members(囤货面)——
    # ①完成买入净释放 1 席(3×1★→1×2★),与腾席方向一致,不恶化义务面
    # 席位竞争;②归义务面(B')会制造死库存——被截 breadth 的 1★×2 对
    # 既不可完成(B' 不含)又不可卖(G-S1 合成素材拒入燃料),双席永久
    # 占死;③残余抢席由 stockpile 既有息律/预算门辖。
    # Y4:候选 star==1 过滤——同名异星不合成(merge §1 凑满 3 指同名
    # 同星),×3 价买 2★ 直出卡不成链且制造 §3.7 让渡死库存;仅 2★ 直出
    # 卡帧 star_mismatch_skip 分键(W4 零静默)。
    # §3.6 席位门满栏例外对齐(B2):本循环形态已保证「买入即触发合成」
    #(同名同星 2→3),机制上买入后全局面同名同星 3→1 净席 −1,无溢出
    # 散牌 ⇒ 免 bench_free 门(与机制对齐,非行为放宽;理由键不变;
    # 机制出处=merge_mechanics.md §2.5 满栏例外+§2.5 上限「绝不多买」)。
    # 形态维单一源(与 P92 ④通道装配共吃 _merge_pair_names;对
    # buy_members 域内名,本守卫与旧「恰 2 张全 1★」三行过滤逐条等价,
    # 机制锚同上 §3.6 满栏例外注)。
    _pairs = _merge_pair_names(bench, deployed)
    for m in buy_members:
        if m not in _pairs:
            continue
        all_cands = _shop_candidates(m, 'm2_merge_completion')   # L2 统一过滤位
        shop_cands = [c for c in all_cands if (c.star or 1) == 1]
        if not shop_cands:
            if all_cands:
                _count('m2b_star_mismatch')   # W4:仅 2★ 直出卡帧(与臂①分键,低-1)
            continue
        card = shop_cands[0]
        cost = card_cost(card)
        ok1, _ = mandate.check_affordable(gold, cost)
        if not ok1:
            continue
        _on_target_buy(card.name or m)
        return _emit_buy(card, 'm2_merge_completion')

    # dominance_buy(零参数资格门,两臂同开;金口径 = 期望态现值——单动作下
    # 每帧金即买后真值,R197 症9 的逻辑态口径问题无存在载体)。
    # (stop_flag 已摘,见 mandate.dominance_buy_eligible docstring——
    # 泄金阶梯档 0,ADR-0604 §2,三处消费位同步摘;本臂物理位次先于
    # 下方档 1/档 2,支配性优先序先于带参臂,发射序申报同 §2。)
    # 锁线转型域收窄(T-190 批 B;P88,ADR-0627):D 帧停发 dominance_buy
    #(S_spec 辖域前置;豁免闭集 = LAUNCH_CAUSE_BY_ARM ∖ PRESS_NARROWED_
    # ARMS 由「仅本臂与 hub 位挂 _narrow_frame」结构性承载)。分键取
    # 「将发射笔」口径 = 候选全门通过后的首见笔计数一次(帧级),防
    # 「辖域覆盖比 = 开火数/全部 dominance 买入数」(设计 §4.1-⑦①)
    # 判读畸变;T-193 结算线地板分键为候选级事件,先于本检查照常显影。
    _dom_narrow_counted = False
    _dom_ok = contracts.ensure_contract(
        ('mandate', 'dominance_buy'),
        contracts.ContractCtx(k_members=k_members, k_target=k,
                              k_fallback_available=_ist is not None,
                              k_fallback_resolved=k_fallback,
                              k_fallback_band=_kfb_tok,
                              k_fallback_source=_kfb_source), counters)
    if _dom_ok and mandate.dominance_buy_eligible(gold, bench_free,
                                                  cap_resolved):
        # 支配性背书仅全额可退 1★(P76 甲/[41];误注 P24 已正——
        # P24 为残余补部署支配定理,无买入命题,T-165 B4)
        for card in _buy_view('dominance_buy'):   # L2 统一过滤位(逐臂分键)
            name = card.name or ''
            cost = card_cost(card)
            star = card.star or 1
            if not name:
                continue
            if not predicates.zero_overlap(name, k_members):
                continue
            # 死库存买入防线(T-229 方向②;T-243 接线,谓词单一源 =
            # mandate.dead_stock_pair_buy_reject_reason):C=1 帧第二张
            # 拒买,非线内名同名 1★ 对构造性不可达(G-S1 卖侧拒因
            # dead_stock_pair 同键;C=2 第三张合成消对放行,K 成员豁免
            # 皆在谓词内)。bench/deployed = 帧首现读(与 hub 位
            # same_star_count 消费同源),计数归消费位。
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
            ok1, _ = mandate.check_affordable(gold, cost)
            if not ok1:
                continue
            # 结算线地板(ADR-0624):买后金 gold−cost ≥ g* 才发射,拒则
            # 试下一更便宜候选(单动作契约下金现读每帧,逐笔买后检查
            # ≡ 顺序贪心花完溢余带预算 g_visit − g*,零批状态;拒笔为
            # 候选级事件,分键显影防静默)。
            _sl_ok, _ = check_settlement_line(gold, cost, g_star)
            if not _sl_ok:
                _count('dominance_settlement_floor_reject')
                continue
            if _narrow_frame:
                # P88 收窄:锁线转型域帧停发——金维支配性论证(1★ 全额退
                # 净 0)前提 = 席位免费,D 帧席位最贵态(被阻线内义务净
                # EV>0,P41③/P76 丙),放行辖域不含 D 帧(调和引理;
                # mandate.dominance_buy_eligible docstring 辖域注同源)。
                if not _dom_narrow_counted:
                    _count('press_narrowed_transition_domain')
                    _dom_narrow_counted = True
                continue
            if _reopen_armed:
                _count('shop_reopen_discretionary_actions')
            return _emit_buy(card, 'dominance_buy')
    elif _dom_ok and gold > g_star and bench_free <= 1:
        # band 否决分键(T-234 验收观察;T-243):命题 4 席位外部性带
        #(bench_free ≤ 1,mandate.dominance_buy_eligible 后半合取)拒发
        # 帧显影——资格门 False 此前静默,否决观测面只剩发射频次差。
        # 本支只计数不决策:两半合取的复算 = 遥测归因(金带外 False =
        # 非必花域常态不计),判定单一源仍在资格门本体。
        _count('dominance_band_wait')

    # C1 直通核心卡支配性支(并列支配通道;位次 = dominance 邻位:既有
    # 通道之后、M3 之前——支配族发射位先于一切带参数值比较,
    # 01_math_framework §3 与权限骨架行(01:15)+支配性优先序(01:40);
    # 设计《直通核心卡信号层入口》§2 案A,
    # ADR-0569)。候选身份(T-115 规则③重构,ADR-0580)= 身份分层单一源
    # line_identity_tier == registry_core 层(原 CORE_SINGLE_CARD_REGISTRY
    # 直查同义——helper 对表即该注册表;③④共源防第六套并列前件)。
    # 前件分叉:锁线态(_buy_members 非 None ⟺ locked_comp 非空)走既有
    # C1 全判据(排除已入采购集者→M2 义务;ADR-0569 判据式);未锁线态 =
    # 规则③ 恒买放行(裁定:核心卡过渡/终局皆核心,恒买;原「锁线前置
    # 使 1-3 未锁线不触发」即本批病灶之一)。
    # 辖域分界(显式):既有 dominance_buy 辖「停手态 ∧ 溢余带 ∧ 线外
    # 燃料件(全体 zero_overlap 1★)」;本通道辖「不破息带 ∧ registry
    # 名单核心卡(锁线态)/恒买(未锁线态)」。锁线∧成型重叠带(stop_flag
    # 与锁线态可并存)两通道动作同致:既有通道序位在前先买 + 1★ 全额退/
    # 席位判据共享单一源,单动作契约下无双发射(spotcheck δ2 措辞口径)。
    # 开店闩申报(设计 §2 落码批核对项):备战期开店闩(cw4_shopped_phase)
    # 辖 run_mandate 的 OpenShop 发射节流(mandate._emit_open_shop,
    # shop_latch_skip_* 计数);本通道在商店决策访问位下游,闩不辖,
    # 默认不消费、零闩读/写。
    # 息纪律口径:不破息判据 = L 项零损(predicates.t5_p1_false 单一源,
    # P47 现算;Ī 取 streak_pre=0 保守近似——收入低估 ⇒ L 偏大 ⇒ 发射
    # 收窄,与 T5 位同款申报)——S 预留硬约束③对象列(EV 买/M6/
    # dominance_buy)不辖本通道,设计判据式无 s_reserve 前件。未锁线恒买
    # 腿**不继承** t5(裁定「恒买」= 无条件;ADR-0580)。
    # 席满转化支(T-115 恒买腾席批,ADR-0580):三腿(未锁线恒买/锁线
    # 支配支/④转线)席满帧经共享 helper 腾席——卖 1 张燃料件释放 1 席,
    # 卖 1 张即止,下一决策迭代原臂原判据买入;无合法 victim = 诚实
    # 停摆(no_fuel 显影)。锁线腿资格门席位维已下放循环内(mandate.
    # core_single_card_buy_eligible 收窄为锁线态单判)。出口键闭集 =
    # seen 帧必落 ≥1(sim 判红检测器判据,sim/checks/ledger.py)。
    # ---- 恒买腾席支共享件(T-115;ADR-0580 席满转化支,方案 v2 §5)----
    # victim 面唯一入口(预挂义务①):排除集 = 统一装配 A 全量形态
    #(单一入口 sell_gate,channel='m4_fuel',与 M2 缺员/m2_stockpile
    # 两腾席位同源装配;候选 = mandate.fuel_sell_candidates 1★ 零重叠
    # 边际≈0,T3 被保件稳定移尾);首候选过 ④不可逆护栏 = 发射资格。
    # 帧内惰性缓存:单动作契约下同一决策帧 bench/排除面不变,金闸双桶
    # 探测与席满腾席共享一次装配(_mm_dedup 同集防 merge_material 事件
    # 双计,P56 投影位同款纪律)。腾席成本面 = 1★ 全额退精确 0
    #(P76 甲;方案 v2 §3),机会成本 = victim 压库贡献二阶小量。
    _core_victim_cache: list[tuple[BenchChar | None, bool]] = []

    def _core_victim() -> tuple[BenchChar | None, bool]:
        """(victim, 可卖)帧内探测:victim = 首燃料候选,可卖 = 过
        check_irreversible(线内件禁卖)。无候选/不过护栏 = (None, False)。"""
        if _core_victim_cache:
            return _core_victim_cache[0]
        _m4_excl = sell_gate.sell_exclusions(session, k_members,
                                             channel='m4_fuel',
                                             cap_hold=_cap_hold_now,
                                             current_round=int(
                                                 round_num_of(bs) or 1))
        cands = mandate.fuel_sell_candidates(bench, k_members,
                                             state=bs,
                                             exclude_names=_m4_excl,
                                             defer_names=_t3_protect,
                                             counters=counters,
                                             dedup_names=_mm_dedup)
        victim = cands[0] if cands else None
        ok4 = False
        if victim is not None:
            ok4, _ = mandate.check_irreversible(victim.char_id or '',
                                                k_members)
        if not ok4:
            victim = None
        _core_victim_cache.append((victim, ok4))
        return _core_victim_cache[0]

    def _core_gold_bucket(prefix: str, cost: int) -> None:
        """金闸双桶分键(A4;候裁4 默认案 = 恒买「金物理约束」按卖前金
        读,ADR-0580 硬闸只继承席/金字面——金不足不卖筹;扩展案须按
        P78-5′ 通道对价段显式立项,本批禁夹带):金不足帧按「卖后可足/
        卖后仍不足」分桶显影,两桶均不卖不买(判读面保住)。fundable
        判据 = 存在可卖 victim 且 gold + refund(victim) ≥ cost。"""
        victim, ok4 = _core_victim()
        _ref = _shop_sell_refund(victim) if victim is not None else None
        if ok4 and victim is not None and _ref is not None \
                and gold + _ref >= cost:
            _count(f'{prefix}_unaffordable_fundable')
        else:
            _count(f'{prefix}_unaffordable_strict')

    def _core_seat_vacate(prefix: str) -> SellBench | None:
        """腾席购买支(镜像 m2_stockpile 腾席位,三腿共享单函数):席满
        帧卖 1 张燃料件释放 1 席,卖 1 张即止(下一决策迭代席空,原臂
        原判据买入)。无合法 victim = 诚实停摆(权限模型:骨架义务 M2 族
        > 裁定族买,禁卖义务件凑恒买;P78-1 本 visit 窗口件经排除集
        同落此支),计 {prefix}_no_fuel 并返回 None。发射契约与两既有
        腾席位逐字段一致(reason 缺省 '' 仅孤儿证明标记;转化分键 =
        convert_reason,ADR-0611 §3-5)。"""
        victim, ok4 = _core_victim()
        if not ok4:
            _count(f'{prefix}_no_fuel')
            return None
        idx = bench_slots_of(bs).index(victim)
        _vname = victim.char_id or ''
        # T3 末位牺牲序命中 + 卖出销账(同两既有腾席位;纯归因分键计数
        # 已随 2026-09-08 用户归因遥测删除指令拆除)
        _prot = _vname in _t3_protect
        if _prot:
            mandate.stall_buys_consume(session, _vname)
        _note_sell(_vname)
        # 出口键(§5.6 闭集;发射 = 席换手,判红检测器与判读面载体)
        _count(f'{prefix}_seat_swap')
        # 发射 = 中间步动作(docstring 契约):卖出真执行释放 1 席,
        # 下一决策迭代席空原臂原判据买入;CloseShop = 终结语义,会把
        # 商店段提前收口(T-238 修复,机制同 M4 缺员腾席位注释)。
        return SellBench(bench_idx=idx,
                         income=_shop_sell_refund(victim),
                         expect=_vname,
                         reason=('line_switch_collapse'
                                 if _vname in _sw_orphans else ''),
                         convert_reason=(
                             'fuel_victim_protect_demoted'
                             if _prot else ''))

    _core_locked = _buy_members is not None
    _core_cands = [c for c in _buy_view('core_single_card_buy')
                   if line_identity_tier(c.name or '')
                   == TIER_REGISTRY_CORE
                   and (not _core_locked
                        or (c.name or '') not in _buy_members)]
    if _core_cands:
        _count('core_candidate_seen')   # 候补支触发(帧级;§7 三键分账)
        if not _core_locked:
            # T-115 规则③ 未锁线恒买放行:硬闸继承只保留席/金物理约束;
            # 息纪律/锁线单判/星级(refund_full_star_ok,恒买不限星)不
            # 继承——2★ 核心件买入价按店面现价过 check_affordable,可逆
            # 性是 dominance 族语义,恒买语义 = 持有价值非燃料可逆
            #(ADR-0580 申报)。auth_basis 以 unlocked 形态 + 独立计数键
            # 与锁线路径可辨不混桶(A2 二选一申报:两件都落)。
            # 门序 = 金→席腾席(T-115 恒买腾席批):买射出 = 全门合取,
            # 合取可交换 ⇒ 席空帧发射/弃买逐位不变;变化仅席满帧新增
            # 腾席发射与帧内分键混合比(计数面)。金闸前置 = m2_stockpile
            # 同纪律(金不足不卖筹,禁「先卖再报」不可逆净损)。
            for card in _core_cands:
                cost = card_cost(card)
                ok1, _ = mandate.check_affordable(gold, cost)
                if not ok1:
                    _core_gold_bucket('core_unlocked', cost)
                    continue
                ok2, _ = mandate.check_seats(
                    bench_free, 0, needs_bench=True, needs_board=False,
                    name='', deployed_names=deployed_names)
                if not ok2:
                    # check_seats 本调用形(not ok2)⟺ bench 满(name 空/
                    # needs_board=False,无同名/板满维)——腾席支。
                    _swap = _core_seat_vacate('core_unlocked')
                    if _swap is not None:
                        return _swap
                    break   # 诚实停摆(no_fuel 已计):席满停摆帧终止本腿
                _count('core_unlocked_buy_hit')
                return _emit_buy(card, 'core_single_card_buy:unlocked')
        elif contracts.ensure_contract(
                ('mandate', 'core_single_card_buy_eligible'),
                # T-307/R1(ADR-0647)前提位声明:仍喂宽集变量 _buy_members
                # (契约前提 = 形态核验非空 frozenset;两口径拆分后义务面
                # 变量为 obligation_members,禁改名致本位静默换喂)。
                contracts.ContractCtx(locked_buy_members=_buy_members),
                counters) and mandate.core_single_card_buy_eligible(
                    _core_locked):
            _core_rounds = horizon.r_remaining(
                session, plane_of(bs), round_num_of(bs))
            _core_ibar = net_income(round_num_of(bs), 0)
            # 门序 = 星级→息档→金→席腾席(T-115 恒买腾席批;席位维自帧门
            # 下放循环内,合取重排对席空帧零漂移——论证同未锁线腿)。
            for card in _core_cands:
                cost = card_cost(card)
                star = card.star or 1
                if not refund_full_star_ok(star, cost):
                    continue    # 支配性背书仅全额可退 1★(共享单一源,禁内联星级判断)
                if not predicates.t5_p1_false(
                        gold, cost, _core_rounds, _core_ibar,
                        cap_resolved):
                    continue    # 不破息带:L>0 帧不放行(统一式 L 项判定)
                ok1, _ = mandate.check_affordable(gold, cost)
                if not ok1:
                    _core_gold_bucket('core_locked', cost)
                    continue
                ok2, _ = mandate.check_seats(
                    bench_free, 0, needs_bench=True, needs_board=False,
                    name='', deployed_names=deployed_names)
                if not ok2:
                    # 席满入循环走腾席支(A1:席维已自帧门下放,此处为
                    # 帧内真席门,非死防御)。check_seats 本调用形
                    #(not ok2)⟺ bench 满。
                    _swap = _core_seat_vacate('core_locked')
                    if _swap is not None:
                        return _swap
                    break   # 席满停摆:no_fuel 已计;break 跳过 for-else 尾键
                _count('core_dominance_buy_hit')    # 支配性支命中(§7 三键分账)
                # 同帧多候补 = 等价免费期权,任意分配序不劣(设计 §2);
                # 发射序 = 店面确定性序。动作形态默认 = 囤(bench 持有,
                # 不上场;deploy 围栏不因持有而变化,设计 §4)。
                return _emit_buy(card, 'core_single_card_buy')
            else:
                # 尾键收窄(T-115 恒买腾席批 A1):for-else = 循环无 break
                # 自然走完(星级/息档/金闸 continue 路径)才落——席满停摆
                # 帧(no_fuel break)不落数值域键,消除「no_fuel 与本键
                # 共火」;金闸弃帧经双桶键显影后同走完路径照落(机制面
                # 如实申报)。语义 = 数值支域帧 fail-closed 显影(§7)。
                _count('core_numeric_fail_closed')

    # T-115 规则④ 转线前瞻放行臂(ADR-0580;C1 邻位,③优先 = C1 先行
    # return 兑现,命中③即不评④)。数据源单一源 =
    # kernel.cw_card_identity.transition_release_names
    #(knowledge/cw_line_facts.TRANSITION_PACK 档∈{carry,partial};drop 档
    # 不放行;禁消费 kernel/cw_transition 迁移副本——其内明令勿新增消费)。
    # 时间辖域(L2)= 未定型期:定型权威 = cw_intention.committed_from
    #(唯一读端,消费先例 cw_op_buy_cards 装配段),定型后放行收窄 =
    # TRANSITION_PACK「P1 过渡包」语义直接推论;P2 换线场景 = 显式不辖
    #(方案悬而未决节请裁,实施者无裁量)。硬闸继承 = 席/金/1★ 全额退
    # refund_full_star_ok(2★ 转线件买入价值未证,本批不放开,ADR-0580)。
    # 未买帧拒因 = transition_component(D7 键序,shop_unbought_reasons
    # 同源分层)。
    if not cw_intention.committed_from(session, bs):
        # 门序 = 星级→金→席腾席(T-115 恒买腾席批:④腿同批接腾席支,
        # 候裁3 复审同意;合取重排对席空帧零漂移,论证同 C1 两腿)。
        for card in _buy_view('transition_component_buy'):   # L2 统一过滤位
            name = card.name or ''
            if not name or line_identity_tier(name) != TIER_TRANSITION:
                continue
            cost = card_cost(card)
            if not refund_full_star_ok(card.star or 1, cost):
                continue    # 1★ 全额退:转线件可逆性硬闸(与 C1 同源)
            ok1, _ = mandate.check_affordable(gold, cost)
            if not ok1:
                _core_gold_bucket('transition', cost)
                continue
            ok2, _ = mandate.check_seats(
                bench_free, 0, needs_bench=True, needs_board=False,
                name='', deployed_names=deployed_names)
            if not ok2:
                # check_seats 本调用形(not ok2)⟺ bench 满——腾席支
                #(T-192 划界:不触 segments.py ④例外臂检测器锁)。
                _swap = _core_seat_vacate('transition')
                if _swap is not None:
                    return _swap
                break       # 席满停摆(transition_no_fuel 已计)
            _count('transition_component_buy_hit')
            return _emit_buy(card, 'transition_component_buy')

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
    # T-115 规则① 消费位1(ADR-0580):抑制判据置于臂计算之前短路——
    # 抑制 = 结构性无授权,三臂与闸链全部无须求值;判据单一源 =
    # kernel.cw_reward_node.reward_node_suppressed(None fail-open:店开
    # 观察帧节点行被遮,误拦升级 = 奖励帧人口停滞,方向论证见 kernel
    # 单一源 docstring)。同帧双闸分键不混桶:reward_node_defer ≠
    # blood_xp_gate_defer ≠ crisis_level_spend_defer。扑满环境帧守卫
    # 解除抑制,写点同时复活 v3_piggy_reward 遥测真值(ADR-0348 ↺)。
    # (容器视图构造器自 W6 波3 起模块级导入,原函数内惰性 import
    #  删除——惰性局部名会遮蔽全函数作用域,前置消费点 UnboundLocalError。)
    _reward_defer = reward_node_suppressed(bs)
    if _reward_defer:
        _count('reward_node_defer')
    # 节点判读 = kernel 单一源 node_kind_of(容器读口;旧 CwSimFrame.
    # node_type 属性在 GameState 上不存在,getattr 恒 None ⇒ 写点曾失联
    # —— piggy_reward 全语料恒 False 的根因,识别面数据通路修复)。
    _node_kind = node_kind_of(bs)
    if _node_kind == 'reward':
        # 每可辨奖励帧刷新扑满标记(真值随环境选择变化,防跨帧滞留旧值)
        state_of(session).v3_piggy_reward = is_piggy_reward_frame(
            bs)
    elif _node_kind is not None:
        # 可辨非奖励帧复位(纯遥测零决策面;字段语义 = telemetry schema
        # piggy_reward「本帧是扑满奖励帧」,跨轮滞留 True 污染按行判读)。
        # 不可辨帧(None,店开观察帧节点行被遮的结构性常态)不复位,维持
        # 最近真值,与 reward_node_suppressed 的 None 失效方向同族。
        state_of(session).v3_piggy_reward = False
    _cap_now = max_units_of(bs)
    _lvl_readable = bool(level_of(bs) is not None)
    _arm1 = False
    _arm0 = False
    _pop = False
    if not _reward_defer:
        _arm1_ok = contracts.ensure_contract(
            ('predicates', 'arm1_existence'),
            contracts.ContractCtx(deploy_cap=_cap_now), counters)
        _arm1 = bool(_arm1_ok and predicates.arm1_existence(
            len(deployed), bench_names, deployed_names, _cap_now))
        if contracts.ensure_contract(
                ('predicates', 'arm0_level_lag'),
                contracts.ContractCtx(), counters):
            _arm0, _arm0_key = predicates.arm0_level_lag(
                level_of(bs), _lvl_readable, deployed, bench,
                k_members, _cap_now)
            if not _arm0 and _arm0_key == 'level_unreadable':
                _count('arm0_level_unreadable')
            elif _arm0 and _cap_now is None:
                _count('arm0_cap_unreadable')   # 存-3:cap 不可读静默弃权补分键
                _arm0 = False
        if contracts.ensure_contract(
                ('levelup', 'pop_slot'), contracts.ContractCtx(), counters):
            _bench_cand = sum(1 for n in bench_names if n in k_members)
            _buyable_cand = bench_free >= 1 and any(
                (c.name or '') in k_members
                and mandate.check_affordable(
                    gold, card_cost(c))[0]
                for c in shop_payload_content_cards(bs.shop.value))
            _pop, _pop_why = crit_levelup.pop_slot(
                len(deployed), _cap_now, gold, _bench_cand, g_star,
                buyable_candidate=_buyable_cand, bench_free=bench_free)
            state_of(session).cw4_pop_slot_why = _pop_why   # D-lv7:否向理由留决策迹
    _budget_gate_blocked = False   # P71-b 闸拒帧标记(M6 同帧挂起辖域)
    if not _reward_defer and (_arm1 or _arm0 or _pop):
        # auth_basis 三臂分键(可归因):触发臂按 arm1 > arm0 > pop 序取首
        _arm_tag = 'arm1' if _arm1 else ('arm0' if _arm0 else 'pop')
        if contracts.ensure_contract(
                ('levelup', 'level_spend_blocked'),
                contracts.ContractCtx(), counters) \
                and crit_levelup.level_spend_blocked(bs, session, _reg):
            _count('crisis_level_spend_defer')
        elif bs is None or not blood_xp_gate_for(
                bs, session):
            # [40]② 血闸(ADR-0578):支付能力检查(买不买得起下一级),与
            # level_spend_blocked 串联;拒因独立分键。金本位 gate 恒 True 直通。
            # kernel 闸波 2 已切容器签名(hp 经政策层读口),CwSimFrame 帧经
            # 过渡桥装箱(桥视图 hp source 失真语义见该桥 docstring)。
            _count('blood_xp_gate_defer')
        elif contracts.ensure_contract(
                ('levelup', 'lv9_stop'), contracts.ContractCtx(), counters) \
                and contracts.ensure_contract(
                    ('levelup', 'xp_ledger_stop'), contracts.ContractCtx(),
                    counters) \
                and not crit_levelup.lv9_stop(level_of(bs), _reg.level_max) \
                and not crit_levelup.xp_ledger_stop(
                    bs.xp.value, _reg.level_max):
            # xp_ledger_stop(T-228):level 域轮内滞留时 lv9_stop 恒 False
            # 的盲区补位(商店域逻辑态直写不写 level,升档等观察覆盖)——
            # 按 XP 期望账本判「已到/越过 level_max」拒发,防 ALL IN 窗
            # 同窗连买下级。判据本体见 criteria/levelup.xp_ledger_stop。
            clicks = clicks_to_next_level(bs)
            cost = xp_click_cost(bs)
            if contracts.ensure_contract(
                    ('levelup', 'spend_unified'),
                    contracts.ContractCtx(gold=gold), counters) \
                    and crit_levelup.spend_unified(clicks, gold, cost):
                ok1, _ = mandate.check_affordable(gold, 0,
                                                  batch_cost=clicks * cost)
                if ok1 and clicks > 0:
                    # P72 (3) 全段预算闸(ADR-0576;P71-b 溢余段形态的
                    # 全段化替换):整买与可负担之后、发射之前的量闸。
                    # 拒 = 整批推迟(攒到闸开帧一次买齐,禁部分买),
                    # 拒因独立分键;契约核验失败(fail-closed 弃权)
                    # 不发射,违例计数由 ensure_contract 自带,不混拒因键。
                    if contracts.ensure_contract(
                            ('levelup', 'levelup_budget_gate'),
                            contracts.ContractCtx(gold=gold,
                                                  deploy_cap=_cap_now),
                            counters):
                        _gate_ok, _gate_why = (
                            crit_levelup.levelup_budget_gate(
                                bs, session, gold, cap_resolved,
                                k_members, bench, deployed, clicks, cost))
                        if _gate_ok:
                            return LevelUpShop(cost=cost,
                                               auth_basis=f'm3_batch:{_arm_tag}')
                        _count(_gate_why)
                        _budget_gate_blocked = True

    # ---- T-115 规则②(b) 死金压库买入(ADR-0580)----
    # 裁定 409:金不满息档时二选一——卖低价值件凑息(②(a) prep 接线)
    # 或花掉压库,禁死囤。触发 = gold < g* ∧ 奖励帧型(帧型判据与规则①
    # **同一谓词同向** = reward_node_suppressed,禁第二套帧型判定,方案
    # D3;None 帧与规则①同向不发射,该域禁死囤由 ②(a) 承载——其触发
    # 节点无关;战斗类节点不新增义务,既有 M2/dominance/C1 授权面已管
    # 战斗帧买入)。位次 = M3 之后、M6/EV 之前:奖励帧上 M3 已被规则①
    # 抑制短路,本臂独占残余(同帧无竞争,D3);M6(gold>g*)与本臂
    #(gold<g*)金带互斥;裁定 409 优先于 EV 面(EV 帧可下帧再评,死金
    # 囤积即病灶本体,ADR-0580)。
    # 买入地板(B2):cost ≤ 死金 gold − 10×⌊gold/10⌋——买入后金位不跌
    # 破当前息档;地板只辖本臂自身,③④/M2/dominance 各臂自有息纪律
    # 判据不受约束(骨架例外,防「同一买入两处闸」混判,ADR-0580)。
    # 跨帧申报(F3 改写):本臂消费不改变 ⌊gold/10⌋,但全金下降使后续
    # 中间段帧的整批可负担时点(spend_unified 按全金判)至多推迟一个
    # 收入周期——与裁定 409 取舍一致,申报为有意。
    # 候选集 = 既有买入臂对象集并集,取序沿用既有买面优先序(线内缺口 >
    # ③/④ > 燃料件);线内缺口/③/④类在此结构性被更早的 M2/C1/④ 臂
    # 吸收(同帧更宽判据未发射 ⇒ 本臂同判据 + 更严地板必不发射),保留
    # 枚举 = 候选集定义完备性(方案规格),实际新增覆盖面 = 燃料类
    #(dominance 辖 gold>g* 带与本臂不重叠)。全不可达 = 诚实空转允许囤
    #(禁为花而买垃圾)。发射即按 prio 买因登记入统一发射登记簿
    #(窗口段:press 类活跃 = 登记轮==当前轮,同 visit 卖回全通道被禁,
    # W1;F1 锁线清空语义废除,P78-3/W3,载体注释在 mandate_state)。
    # 外门三条件合取(gold/席/reward)显式拆分(T-115 恒买腾席批;候裁1
    # 移位案采纳,B2):席满支 = 本臂结构性不出手的静默显影位,键
    # dead_gold_press_bench_full_gate 只在 bench_free≤0 支计——原拟内门
    # 落点不可达 = 死键(B2 证;死键纪律:落键前核实外门无同维短路)。
    # 行为零变化:原合取首支照旧,新支只计数。
    if gold < g_star and bench_free > 0 \
            and reward_node_suppressed(bs):
        _dead_gold = gold - 10 * (gold // 10)
        _dg_gap = {m for m in buy_members if m not in owned}
        for _dg_prio in range(3):
            for card in _buy_view('dead_gold_press_buy'):   # L2 统一过滤位
                name = card.name or ''
                cost = card_cost(card)
                if not name or cost > _dead_gold:
                    continue
                tier = line_identity_tier(name)
                if _dg_prio == 0:
                    _hit = name in _dg_gap
                elif _dg_prio == 1:
                    _hit = tier in (TIER_REGISTRY_CORE, TIER_TRANSITION)
                else:
                    # 燃料类 = dominance 对象定义同款:非线内 1★ 全额退
                    _hit = (tier == TIER_UNRELATED
                            and (card.star or 1) == 1
                            and predicates.zero_overlap(name, k_members)
                            and refund_full_star_ok(1, cost))
                    # 死库存买入防线(T-229 方向②;T-243 接线,与
                    # dominance 臂同谓词单一源):燃料类拒成对第二张,
                    # 分键 press_dead_stock_pair_blocked;prio0(缺口)/
                    # prio1(持有档)不接 = 义务通道豁免(T-234 §④ 申报)。
                    if _hit and mandate.dead_stock_pair_buy_reject_reason(
                            name, card.star or 1, bench, deployed,
                            k_members):
                        _count('press_dead_stock_pair_blocked')
                        _hit = False
                if not _hit:
                    continue
                ok2, _ = mandate.check_seats(
                    bench_free, 0, needs_bench=True, needs_board=False,
                    name='', deployed_names=deployed_names)
                if not ok2:
                    break
                ok1, _ = mandate.check_affordable(gold, cost)
                if not ok1:
                    continue
                _count('dead_gold_press_buy_hit')
                # ②(b) 按 prio 三分买因登记(prio0=obligation/prio1=
                # hold/prio2=press;ADR-0585 §2 映射定稿):旧 ②(b) 动态
                # 集 cw4_dead_gold_bought_names 退役并入统一发射登记簿,
                # F1 锁线清空废除(P78-3),窗口段轮界过期承载(W3)。
                # prio1(hold)过类资格断言:2★ 转线直出 = launch_cause_
                # mismatch 拒登记不拦发射(W5/V2-06,买面门槛归臂自身批)。
                _dg_cause = ('obligation', 'hold', 'press')[_dg_prio]
                return _emit_buy(card, 'dead_gold_press_buy',
                                 launch_cause=_dg_cause)
    elif gold < g_star and bench_free <= 0 \
            and reward_node_suppressed(bs):
        # 外门 else 席满支(结构性可达:B2 移位案;零行为,只显影)。
        _count('dead_gold_press_bench_full_gate')

    # ---- 泄金阶梯档 1:可上场非定向买(press_buy_deployable;ADR-0604
    # §2,R2 审 F8/F10/F12 落点)----
    # 必花域溢余金消费序的第二档(单动作契约下物理位次即优先序:
    # 档 0 定向/支配臂已在前,本臂先于下方档 2 压库)。触发 = 必花域
    # 帧 ∧ 锁线态(单一源 = ``_ist.locked_comp``,同出口③ D 支定谳,
    # 禁 k_members 非空作门——恒真不可作门,17号稿 §1.1 应修-8 B-1)
    # ∧ deploy_vacancy > 0 ∧ bench_free ≥ 1 ∧ 店内存在可上场件。
    # 判据性质 = [31]②/[32] 口述判据+结构判据(非支配,审 F10 降格
    # 标注):买入的边际账 = 填充价值 vs 搜索预算的 EV 比较臂,立项
    # 命题候选挂 ADR-0604 §4(待证钩子),本臂不引 P24/P70。
    # 「可上场件」= a. 围栏可落(can_deploy_single 预检放行,内含
    # 非纯散件 = [31]③ 边际羁绊贡献;kernel 五键闭集拒因语义同出口③);
    # b. 替换可落(板满变体)首版出辖(待实证 #4 挂账,ADR-0604 §4-⑦)。
    # 候选互斥切分(F12):垫件类(1★ 零重叠全额退)归出口③ 既有臂
    #(N3 登记/位次语义保留),线内件归 M2 义务通道——本臂候选集 =
    # 围栏可落 ∧ 非垫件类 ∧ 非线内,显式排除分键零静默。
    # 金位地板 = ``g − cost ≥ g*``(息基零破坏,ADR-0604 §2;
    # 不走档 2 的 s_reserve 投影口径——本臂非压库语义)。判据自结算线
    # 地板批起消费 ``check_settlement_line`` 同谓词(与 dominance 臂
    # 单一源,防三处买臂判据漂移;同谓词同值,行为不变,ADR-0624)。
    # P72 拒帧挂起(L4):M3 批被 levelup_budget_gate 拒的帧,预留金
    # 不被本臂同帧击穿(复用 m6_budget_gate_suspend 先例,ADR-0560;
    # 挂起只辖 NORMAL 语境,F16 的 FLOOR_ON 让位随 hp 闸批落位,本批
    # 无该分支,申报 = ADR-0604 §4-F16)。
    _zone_hit = in_must_spend_zone(gold, session)
    if (getattr(_ist, 'locked_comp', None)
            and _zone_hit and bench_free > 0):
        _pd_vac = (_cap_now - len(deployed)) if _cap_now else None
        if _pd_vac is None:
            _count('press_buy_deployable_cap_unreadable')
        elif _pd_vac < 1:
            _count('press_buy_deployable_no_vacancy')
        elif _budget_gate_blocked:
            _count('press_buy_deployable_budget_suspend')
        else:
            _pd_tgt, _pd_fw = deploy_target_sets(k)
            try:
                _pd_lfs = cw_intention.locked_faction_scope(_ist) \
                    if _ist is not None else frozenset()
            except Exception:   # noqa: BLE001 兜底 best-effort(同出口③)
                _pd_lfs = frozenset()
            try:
                _pd_rf = cw_intention.locked_line_recipe_floor_conflict(_ist)
            except Exception:   # noqa: BLE001 豁免语境 fail-closed(同出口③)
                _pd_rf = False
            for card in _buy_view('press_buy_deployable'):   # L2 统一过滤位
                name = card.name or ''
                if not name or name in buy_members:
                    continue    # 线内件归 M2 义务通道(定向最高优先不变)
                cost = card_cost(card)
                _pf_ok, _ = check_settlement_line(gold, cost, g_star)
                if not _pf_ok:
                    _count('press_buy_deployable_below_floor')
                    continue
                # 垫件类互斥切分(F12):1★ 零重叠全额退 = 出口③ 候选,
                # 本臂不评(出口③ 物理在后,先到先发射语义不破——本臂
                # 显式跳过即让位,登记语义不分流)。
                if (card.star or 1) == 1 \
                        and predicates.zero_overlap(name, k_members) \
                        and refund_full_star_ok(1, cost):
                    _count('press_buy_deployable_filler_excluded')
                    continue
                _pd_mch = get_char(name)
                _pd_cand = BenchChar(
                    slot=0, char_id=name, star=(card.star or 1),
                    faction=(_pd_mch.factions[0]
                             if _pd_mch is not None and _pd_mch.factions
                             else '?'),
                    position_pref='back')
                try:
                    # kernel 单一源直调(围栏语义,预检查询非判据面谓词
                    # 不挂 contracts,形态同出口③/T5)。
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
                ok1, _ = mandate.check_affordable(gold, cost)
                if not ok1:
                    _count('press_buy_deployable_unaffordable')
                    continue
                _count('press_buy_deployable_hit')
                if _reopen_armed:
                    _count('shop_reopen_discretionary_actions')
                return _emit_buy(card, 'press_buy_deployable')

    # M6 溢余转压库(存在性=金>g*;档匹配 fail-closed ⇒
    # 不买 + 溢余滞留遥测;两臂同开)。P71-b 闸拒同帧挂起(ADR-0560):
    # 闸刚护住的预留金不得被同帧压库击穿(拒后照发 = 金换通道,预留
    # 语义同帧失效)——挂起只辖 shop 侧 M6;prep 位「M6」是 emit
    # OpenShop(转店后本函数 M3 重过闸兜住),不重复挂起(防双闸)。
    # stop_flag 已摘(泄金阶梯档 2,ADR-0604 §2 摘旗扩域,
    # 对抗审 F6 落点三处消费位之一):必花域转化期帧(线未齐)压库
    # 合法,[13] 停手线纪律语义由候选集判据本体承载(P49 档匹配
    # fail-closed + P56 s_reserve 下界 + 线内副本排除 + 轮内新鲜度
    # 排除,全保留/新增见下);窗口语义维持在产 ω 塌缩带
    #(tier_w = tier_search_window(level, ω) 单一源,审 F11 维持裁决,
    # 不采用「合格集费用带」替换案,申报 = ADR-0604 §4-#11)。
    _m6_arms = gold > g_star and bench_free > 0
    if _m6_arms and _budget_gate_blocked:
        _count('m6_budget_gate_suspend')
    elif _m6_arms:
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
                contracts.ContractCtx(k_members=k_members, k_target=k,
                                      k_fallback_available=_ist is not None,
                                      k_fallback_resolved=k_fallback,
                                      k_fallback_band=_kfb_tok,
                                      k_fallback_source=_kfb_source),
                counters)
            # T-263 P91(a) 压库同轴(ADR-0635):活跃搜索费带 = 合格集
            # 成员费带(qualified_member_costs 单一源,与 R2 预留卡价
            # 同源过滤);带非空帧候选稳定排序「带内先于带外」——同费
            # 非目标压库使活跃方向每刷命中率单调不减(P91(a)),异轴对
            # 活跃方向恒零影响(P49)。前窗帧追加 1-2 费优先(P90 成本界
            # 背书的排序语义,非窗口禁令——ADR-0635 偏差申报)。稳定
            # 排序复合:最终序 = (零成型推进件, 同轴带内, 1-2 费)。
            _p91_band = frozenset(crit_refresh.qualified_member_costs(
                buy_members, bench, deployed, level_of(bs)))
            if _p91_band:
                _count('p91_active_band_frame')
            _m6_cands = _buy_view('m6')   # L2 统一过滤位
            if _p91_band:
                _m6_cands = sorted(
                    _m6_cands,
                    key=lambda c: 0 if (card_cost(c)) in _p91_band
                    else 1)
            if _front_window:
                _m6_cands = sorted(
                    _m6_cands,
                    key=lambda c: 0 if (card_cost(c)) <= 2 else 1)
            for card in _m6_cands:
                name = card.name or ''
                # 线内追星段排除(落地审清单存疑收口,N2/§3.7):线内副本
                # 的买入全链归义务通道(M2 j=0→1 / 臂① j=1∧cnt2=0 / M2b
                # j=2 完成段,§3.4 边界表)——M6 压库若买线内 1★ 副本会
                # 绕过臂① cnt2==0 守卫制造「cnt1=2∧有 2★」死库存
                #(§3.7 让渡形态)。压库域收窄为非线内件,分键零静默。
                if name in buy_members:
                    _count('m6_line_member_excluded')
                    continue
                # 轮内新鲜度排除已由统一过滤位承载(泄金阶梯档 2,
                # ADR-0604 §3;模拟批#5 s108 实证:同轮「卖X→买回X→
                # 再卖X」净零自旋)。起位收编 = 全买入臂统一位
                # (ADR-0611 §3-3),分键 m6_round_sold_excluded 键名
                # 零断链;原档 2 手搓读法退役。
                cost = card_cost(card)
                okm, _mkey = crit_stockpile.stockpile_buy(
                    gold, s_reserve, bench_free, cost,
                    card.star or 1, tier_w) if _stock_ok else (False, '')
                if not okm:
                    if _mkey == 's_reserve':
                        _count('m6_s_reserve_reject')
                        # P77 缺口面3 对价载体(ADR-0626):拒帧再遇窗入
                        # 累计(自然帧 ceil;纯遥测禁决策消费,让路裁决
                        # 归 P56 设计批)——「留保息 vs 收现货」有权衡量值。
                        if name:
                            counters['m6_s_reserve_remeet_frames_sum'] = (
                                counters.get(
                                    'm6_s_reserve_remeet_frames_sum', 0)
                                + _s_reserve_remeet_frames(
                                    level_of(bs), bench, deployed,
                                    card))
                    continue
                ok1, _ = mandate.check_affordable(gold, cost)
                if not ok1:
                    continue
                if _p91_band:
                    # P91 同轴/异轴选择帧对键(零静默:两键覆盖全部 M6
                    # 买入,带空帧不计——无方向帧无同轴语义)
                    _count('p91_m6_same_axis_hit' if cost in _p91_band
                           else 'p91_m6_off_axis_hit')
                return _emit_buy(card, 'm6_stockpile')

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
    # 必花域判定(20 号稿 §2.1):g > G_must = 10 × cap_resolved_of_
    # session(saturation_line 同源派生,零新自由参数);买断制语境
    #(cap_resolved = 0)出辖恒 False。辖域 = 有动作决策点帧(本函数
    # 即 shop 决策点)。L2 第二触发源 / L3 / R1 切分线共用本判定。
    # (求值点已上移至档 1 臂前,泄金阶梯批:档 1/出口③ 同帧同值
    # 单点计算,禁第二份。)
    if _zone_hit:
        # 必花域帧义务来源披露(T-88 写点;遥测键 sess_release_reason 透传
        # 源):帧内 last-wins、域外帧不覆写,轮界清零在装配键戳
        # (assembly._disclose_budget)。披露面字段禁决策判据消费
        #(决策输入一律走 TurnState 幂等装配;ADR-0571)。
        state_of(session).v3_release_reason = 'must_spend'
    # D 支锁线布尔单一源 = ``_ist.locked_comp````(17 号稿 §1.1 应修-8 B-1
    # 定谳;flow.py 物化段证明 P1 未锁线帧早对物化伪 comp →
    # ``k is not None`` 恒真,作锁线门会让垫件在未锁线期发射——fail-closed
    # 破门,ADR-0525 决策 2 辖域)。
    if (getattr(_ist, 'locked_comp', None)
            and _lvl_readable):
        # C 支(落后·期望态口径;level 消费 level_readable 可信位)。
        # L2 第二触发源(20 号稿 §3.1-L2,∨ 合并):必花域帧不辖 C/A
        #(触发面差异),垫件在售/席/金位/围栏预检资格照常(资格硬闸
        #(i) 零解封);触发源分键 must_spend_l2_trigger。
        if level_of(bs) - len(deployed) > 0 or _zone_hit:
            # A 支(无可追件·不可追支):合格集 = cnt2==0 ∧ 有效概率>0;
            # 成因支 = ∃ cnt2==0 ∧ 有效概率=0。有效概率单一源 =
            # effective_refresh_prob(轮岗感知:概率条实读优先,不可得/
            # 缺键/≤0 采样回退基线表;概率条 None = 不可得 fail 向不判 A,
            # 禁据疑零值发射)。
            _rp = (bs.shop.value.refresh_probs if bs.shop.value is not None else None)
            _causal: list[str] = []
            _chaseable = False
            if _rp is None:
                _chaseable = True   # 概率条不可得:fail 向(视同可追)。
                # 容器域读法(W6 波 4 契约:payload 在屏时 probs 恒非 None,
                # 「概率条未读」= 空表 {}——falsy 判覆盖 None/{} 两形态,
                # 与决策视图 adapter 的 probs 折 None 同门)
            else:
                for _m in k_members:
                    if _cnt(_m, 2) > 0:
                        continue   # 排除支:全员 2★ 成件 = 线齐,非病灶
                    _mch = get_char(_m)
                    _mcost = _mch.cost if _mch is not None else None
                    if _mcost is None:
                        continue
                    if effective_refresh_prob(
                            bs, level_of(bs), _mcost) <= 0.0:
                        _causal.append(_m)
                    else:
                        _chaseable = True
            if (_causal and not _chaseable) or _zone_hit:
                if _zone_hit:
                    # 触发源分键(20 号稿 §3.5:合并不吞文号,发射时
                    # 触发源可归因)
                    _count('must_spend_l2_trigger')
                # B 支(富金;观测条件,调度仍由 arm2 g* 线管辖)
                if gold > s_reserve:
                    # 垫件在售 = 非 1★ 直出卡全过滤后仍有候选;资格排除集
                    # ≡ locked_buy_membership(§2.3 第 2 点单一源);L2
                    # 统一过滤位随行(本轮已卖垫件不再买回,T-165)。
                    _ff_sale = [c for c in _buy_view('fuel_filler_stall')
                                if (c.name or '')
                                and (c.name or '') not in buy_members
                                and (c.star or 1) == 1
                                and predicates.zero_overlap(c.name or '',
                                                            k_members)
                                and refund_full_star_ok(
                                    1, card_cost(c))]
                    if not _ff_sale:
                        _count('fuel_not_on_sale')   # Φ_stall 成立而垫件缺
                    elif bench_free <= 0:
                        _count('bench_full')   # §7.3 授权条件含 bench_free≥1
                    else:
                        for card in _ff_sale:
                            name = card.name or ''
                            cost = card_cost(card)
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
                            # 豁免武装布尔(ADR-0564;豁免是帧属性,同一帧
                            # 预检与部署必须同值——语义分裂 = 发射×执行单一
                            # 源契约破口;try/fail-closed 同 mandate.
                            # _deployable 形态)
                            try:
                                _rf_ctx = cw_intention \
                                    .locked_line_recipe_floor_conflict(_ist)
                            except Exception:   # noqa: BLE001 豁免语境 fail-closed
                                _rf_ctx = False
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
                                    # fenced 拒因拆键透传(exit3_fence_
                                    # semantics DESIGN §5-1;kernel
                                    # reasons_out 既有五键口径,零新语义
                                    # ——拆的是计数不是谓词)。聚合键
                                    # fuel_filler_stall_fenced 保留
                                    #(合计口径,兼容既有判读/复盘对照)。
                                    # 预注册裁决协议(DESIGN §5-3,先写
                                    # 死后看数,防挪线):
                                    # - 必花域触发源(l2 前缀键)中 cap
                                    #   占比 >80% ⇒ 板满平凡拒成立,层错
                                    #   假设终结,走 DESIGN §4-2(L3 接线)
                                    #   /§4-3(白名单扩行);
                                    # - scatter_fence ∪ rest_capacity 占比
                                    #   >20% ⇒ 存在「板未满仍被围栏语义拒」
                                    #   形态,重开预检辖域审查(仍须先过
                                    #   §3.2 价值账,不直接豁免);
                                    # - name_dup/recipe_floor 非零 ⇒ 各自
                                    #   独立资格细化问题,单独立项。
                                    # kernel 五键是闭集(cap/scatter_fence/
                                    # rest_capacity/name_dup/recipe_floor,
                                    # cw_deploy_logic:255-256);闭集外值
                                    # 仍按动态后缀落键,零静默。
                                    _count('fuel_filler_stall_fenced')
                                    _count(f'fuel_filler_stall_fenced_'
                                           f'{_ff_why}')
                                    if _zone_hit:
                                        # 触发源对照分列(DESIGN §5-2):
                                        # Φ_stall 源板未满 cap 占比应≈0,
                                        # 必花域源板满帧 cap 主导——两源
                                        # 分布差异可检验(Φ_stall 源 =
                                        # 非前缀键,必花域源 = l2_ 前缀键)。
                                        _count(f'fuel_filler_stall_fenced_'
                                               f'l2_{_ff_why}')
                                continue   # 围栏拒帧,试其余垫件
                            _count('fuel_filler_stall_buy')
                            # N3 闭环登记契约(写端单一源,带轮戳 dict;
                            # 卖侧读端 = mandate.stall_protect_active)
                            mandate.stall_buys_register(
                                session, name, round_num_of(bs))
                            _on_target_buy(name)
                            return _emit_buy(card, 'fuel_filler_stall')
                # B 支不成立:g ≤ s_reserve(非病灶帧,静默)

    # ---- T5 未锁线止血买(结构层,无开关;ADR-0556 §2):
    # 垫底级消费位第五触发源——消费位单一源 = 11号稿 §7.3 垫底级,与
    # 上方出口③同位:出口③辖锁线帧、T5 辖未锁线帧,锁线布尔两支互斥
    #(单一源锚 = cw_intention.locked_buy_membership:未锁帧返回 None),
    # 锁线交接时 T5 出辖、出口③/(b)2 接盘。触发核替换(W8 同款申报):
    # 店侧「全店无候选」→「未锁线 ∧ P1(g,1) 假 ∧ vacancy 余存」结构谓词;
    # P1 判据 = predicates.t5_p1_false 现算(零战力量,ADR-0556 §4
    # 支配论证,ADR-0288 仅接受形态先例)。cost-1 收窄 = 有意辖域
    #(ADR-0556 §2:lv1-3 全店 cost-1 的注册表事实;仅 2/3 费垫件帧
    # 不触发,禁自行扩域)。
    # P1 真帧落行为层挂起(V_deploy 候用户逐项授权,00 §3 硬闸门;
    # ADR-0556 §7 挂账)——t3_p1_true_blocked 显影后照旧落既有序,
    # 结构层禁发射。级内序(ADR-0556 §3):
    # 降级1(羁绊填充,在册)→ 本止血变体 → 降级2 囤形态(在册,回退位)
    # ——梯宿主申报:降级1/降级2 囤形态两段不在本文件面(宿主 = 11号稿
    # §7.3 垫底级 owner),本文件只承载止血变体位次;同帧双真单次消费由
    # 物理位次保证(M6 囤臂 gold>g* 先行 = ADR-0556 §3「现行序先行」)。
    # 锁线布尔边缘双开形态申报(ADR-0556 §3):locked_comp 非空而采购集
    # 解析为空(get_comp 注册表缺项脏态 ∧ 无 p1_pair/transition_pair)时
    # locked_buy_membership 返回 None,T5 门与出口③门同帧双开——
    # 出口③物理先行、先到先发射(单动作契约),T5 仅承接其未消费帧,
    # 无双买面。
    # 发射序 = 垫底级在既有序(M6)之后、EV/R1 之前(ADR-0556 §3
    # 同备战期序);部署腿不占发射位——单动作契约下买入落 bench,垫件
    # 上板由部署侧残余补部署(P24:空 cap 槽任意合法单位 ΔEV≥0)既有
    # 语义承接,vacancy > 可部署 bench 件数预检保证买后仍有空槽可落;
    # held 闭环 = 出口③同款 N3 登记(cw4_fuel_filler_stall_buys 单一
    # 载体,T5 held 并入 fuel_filler_stall_held_postbuy 口径,ADR-0556 §5)。
    if _buy_members is None and shop_payload_content_cards(bs.shop.value):
        # L2 统一过滤位随行(本轮已卖垫件不再买回,ADR-0611 §3-3)。
        _t5_sale = [c for c in _buy_view('t3_unlocked_hemostat')
                    if (c.name or '') and (c.star or 1) == 1
                    and (card_cost(c)) == 1
                    and predicates.zero_overlap(c.name or '', k_members)
                    and refund_full_star_ok(1, 1)]
        if not _t5_sale:
            # 店无 cost-1 1★ 零重叠垫件:T5 域不开(ADR-0556 §2 有意收窄,
            # 无病灶证据禁扩域);计数显影归因(全店无候选帧的 T1 原生
            # 触发源宿主 = 11号稿 §7.3,不在本文件面)。
            _count('t3_no_candidate')
        elif bench_free <= 0:
            _count('t3_precheck_bench_full')
        else:
            _t5_dep = sum(1 for b in bench
                          if (b.char_id or '') in k_members
                          and (b.char_id or '') not in deployed_names)
            # 可部署 bench 件数口径 = 线内件按名去重现读(与 arm0_need
            # 部署去重语义对齐;未锁线 k_members=() 时恒 0)。
            _t5_vac = _cap_now - len(deployed) if _cap_now else None
            if _t5_vac is None:
                _count('t3_precheck_unavailable')   # cap 不可读,查询不可得
            elif _t5_vac < 1 or _t5_vac <= _t5_dep:
                # 假想部署预检的结构前置:买后须仍有空槽可落
                #(与 bench_free 拒拆键,两因判读可辨)
                _count('t3_precheck_no_vacancy')
            elif not predicates.t5_p1_false(
                    gold, 1,
                    horizon.r_remaining(session, plane_of(bs),
                                        round_num_of(bs)),
                    net_income(round_num_of(bs), 0),
                    cap_resolved):
                # Ī 口径申报:streak_pre=0 恒定近似(连胜奖励不计入,
                # 与本函数 R1 段 _ibar 同款)——收入低估 ⇒ L 偏大 ⇒
                # P1 偏真 ⇒ 发射收窄,方向保守。
                _count('t3_p1_true_blocked')   # P1 真帧:行为层挂起显影
            else:
                _count('t3_available')
                for card in _t5_sale:
                    name = card.name or ''
                    # 金 ≥ 卡价 → 金−卡价 ≥ s_reserve → 围栏预检
                    #(ADR-0556 §2 判据序;kernel 单一源,禁第二套围栏语义)
                    ok5, _ = mandate.check_affordable(gold, 1)
                    if not ok5:
                        _count('t3_unaffordable')
                        continue
                    if gold - 1 < s_reserve:
                        _count('t3_below_reserve')
                        continue
                    _mch5 = get_char(name)
                    _cand5 = BenchChar(
                        slot=0, char_id=name, star=1,
                        faction=(_mch5.factions[0]
                                 if _mch5 is not None and _mch5.factions
                                 else '?'),
                        position_pref='back')
                    _tgt5, _fw5 = deploy_target_sets(k)
                    try:
                        _lfs5 = cw_intention.locked_faction_scope(_ist) \
                            if _ist is not None else frozenset()
                    except Exception:   # noqa: BLE001 兜底 best-effort(同出口③)
                        _lfs5 = frozenset()
                    # 豁免武装布尔(ADR-0564;帧属性同帧同值,形态同出口③):
                    # 武装帧 T5 结构性出辖(armed ⇒ 采购集解析成功 ⇒ T5
                    # 门关),本接线 = 帧属性语义统一,非行为变更
                    try:
                        _rf_ctx5 = cw_intention \
                            .locked_line_recipe_floor_conflict(_ist)
                    except Exception:   # noqa: BLE001 豁免语境 fail-closed
                        _rf_ctx5 = False
                    try:
                        ok5, why5 = can_deploy_single(
                            _cand5, bench,
                            deployed_cids=set(deployed_names),
                            deployed_fac=deployed_bond_counts(
                                set(deployed_names)),
                            board=deployed_bond_counts(set(deployed_names)),
                            cap=(_cap_now if _cap_now else 10 ** 6),
                            target_factions=_tgt5,
                            target_cores=set(),
                            fw_carry=_fw5,
                            locked_factions=_lfs5 or frozenset(),
                            recipe_floor_lock_exempt=_rf_ctx5)
                    except Exception:   # noqa: BLE001 查询不可得 fail 向(同出口③)
                        ok5, why5 = False, 'precheck_unavailable'
                    if not ok5:
                        if why5 == 'precheck_unavailable':
                            _count('t3_precheck_unavailable')
                        else:
                            # fenced 拒因拆键透传(kernel reasons_out 五键
                            # 闭集口径,拆计数不拆谓词;闭集外动态后缀零静默)
                            _count('t3_fenced')
                            _count(f't3_fenced_{why5}')
                        continue
                    _count('t3_buy')
                    # N3 闭环登记契约(出口③同款单一载体,写端单一源
                    # mandate.stall_buys_register 带轮戳):T5 垫件买入
                    # 入 cw4_fuel_filler_stall_buys,部署侧 held 时经
                    # record_fuel_filler_held_postbuy 显影;卖侧读端 =
                    # stall_protect_active(同轮保留=末位牺牲序,修复
                    # 买后同轮即卖净零自旋;T5 held 并入 fuel_ 键口径,
                    # 不设独立 t3_held_postbuy,见文件头申报)。
                    mandate.stall_buys_register(
                        session, name, round_num_of(bs))
                    return _emit_buy(card, 't3_unlocked_hemostat')

    # ---- ④ EV pass(臂①旁路集;仅 criteria 真 EV 发射面)----
    if not skeleton_only:
        if contracts.ensure_contract(
                ('buy', 'ev_buy_candidates'),
                contracts.ContractCtx(k_members=k_members, k_target=k,
                                      k_fallback_available=_ist is not None,
                                      k_fallback_resolved=k_fallback,
                                      k_fallback_band=_kfb_tok,
                                      k_fallback_source=_kfb_source),
                counters):
            # EV 排除集 = 买入义务集(buy_members):义务面成员「走 M2,
            # 非 EV 域」——与买面同口径;非卖免面,不吃锁定全集收窄裁。
            cands, ckey = crit_buy.ev_buy_candidates(
                gold, s_reserve,
                (bs.shop.value.cards if bs.shop.value is not None else []),
                buy_members,
                level=level_of(bs), window=card_w,
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
                    # 必花域内 (iii) 期望核算类 veto(ev_buy_veto)降为
                    # 排序信号:非 veto 先买,veto 候选排末位仍可消费
                    #(三分类 (iii),ADR-0528);域外 veto 照旧直拒。
                    _deferred = []
                    for cand in cands:
                        _slots = (bs.shop.value.cards
                                  if bs.shop.value is not None else [])
                        _slot = (_slots[cand.slot_idx]
                                 if cand.slot_idx < len(_slots) else None)
                        card = (_slot.card
                                if _slot is not None
                                and _slot.kind == 'content' else None)
                        if card is None:
                            continue
                        # L2 统一过滤位(ev_buy 走 slot_idx 解析,过滤位
                        # 落在解析点;单一判定 helper 同源,T-165)。
                        if mandate.sold_this_round(session, bs,
                                                   card.name or ''):
                            _count('ev_buy_round_sold_excluded')
                            continue
                        veto, _vkey = crit_buy.ev_buy_veto(cand, gold) \
                            if contracts.ensure_contract(
                                ('buy', 'ev_buy_veto'),
                                contracts.ContractCtx(gold=gold), counters) \
                            else (True, '')
                        if veto and not _zone_hit:
                            continue
                        ok1, _ = mandate.check_affordable(gold, cand.cost)
                        if not ok1:
                            continue
                        if veto:
                            _deferred.append(card)   # 域内:降排序末位
                            continue
                        if _reopen_armed:
                            _count('shop_reopen_discretionary_actions')
                        return _emit_buy(card, 'ev_buy')
                    if _deferred:
                        # 触发源分键(§3.5 归因纪律):域内 (iii) 类 veto
                        # 降排序后的末位消费,可归因。
                        _count('must_spend_ev_deferred')
                        if _reopen_armed:
                            _count('shop_reopen_discretionary_actions')
                        return _emit_buy(_deferred[0], 'ev_buy')
                    _count('shop_ev_all_vetoed')   # D-P2idle:「全拒」可辨
            else:
                _count('shop_ev_no_candidate')     # D-P2idle:「无候选」可辨
        # 付费刷新(R1 发射位;终结 op——刷新即本画面访问结束,ADR-0517
        # 决策 7)。R1 门形态 = 形式二可负担性(路径总账判据);输入全为游戏定义
        # 量,零胜率建模。L* = 形式二等级选择输出(留级账 T_stay vs 升一
        # 级账 T_up 取小);P40 R2 息线熔断保留原语义。金基准 = 期望态
        # 现值(旧「买后逻辑态金」专修无存在载体——每帧金即真值)。
        # 触发源记录初值(息线门 R1 域外常规;域内 yielded 支在上方
        # 切分线覆写。值域契约见 kernel/cw_state.RefreshShop.reason 注)。
        _r1_src = 'r1'
        if contracts.ensure_contract(
                ('refresh', 'r1_commitment_account'),
                contracts.ContractCtx(), counters):
            _c_eff = refresh_cost_effective(None, 0, bs=bs)
            _ibar = net_income(round_num_of(bs), 0)
            _g0 = gold
            _rounds = horizon.r_remaining(session, plane_of(bs),
                                          round_num_of(bs))
            _lvl = level_of(bs)
            _e_stay, _fees = _r1_ledger_terms(buy_members, bench, deployed,
                                              _lvl)
            if _e_stay == float('inf'):
                _t_stay = float('inf')
            else:
                _t_stay = _c_eff * _e_stay + _fees + loss_exact(
                    _g0, int(math.ceil(_c_eff * _e_stay)) + _fees,
                    _rounds, _ibar, cap_resolved)
            _t_up = float('inf')
            _clicks = clicks_to_next_level(bs)
            if _clicks > 0:
                _u_gold = _clicks * xp_click_cost(bs)
                _e_up, _fees_up = _r1_ledger_terms(buy_members, bench,
                                                   deployed, _lvl + 1)
                if _e_up != float('inf'):
                    _t_up = _c_eff * _e_up + _fees_up + _u_gold + loss_exact(
                        _g0,
                        int(math.ceil(_c_eff * _e_up)) + _fees_up + _u_gold,
                        _rounds, _ibar, cap_resolved)
            _ledger = min(_t_stay, _t_up)
            _lvl_star = _lvl if _t_stay <= _t_up else _lvl + 1
            if _lvl_star != _lvl:
                # P91(b) 刷-升切换分键(P5/P39 在册通道的形式二消费位,
                # T-263 补零静默观测,ADR-0635)
                _count('p91_refresh_up_switch')
            r2_reserve = g_star + _r2_card_reserve(k_members, bench,
                                                   deployed, bs,
                                                   level=_lvl_star)
            ok_r1, rkey = crit_refresh.r1_commitment_account(
                _ledger, _g0 - g_star)
            if _zone_hit and rkey == 'account_over_budget':
                # R1 域内残形切分线(20 号稿;ADR-0528)——设计出处 =
                # 必花域「要花」授权对 g*/L 核算账的切分;辖域申报:现辖
                # = 末轮豁免支(计划视野关闭),其余域内超账帧恢复账前件
                # 拦(口径分叉修复;病灶 = 2026-09-15 sim 批量找问题报告
                # 「问题 1」零买入连刷段)。合格集空守卫(no_chaseable_
                # member,(ii) 类 fail-closed)不在此列照旧。
                # 末轮豁免支:本帧后无未来节点(谓词单一源 = crit_refresh.
                # r1_horizon_closed;契约弃权 fail-closed 走拦支),金随
                # 局终沉没 => 刷新机会成本 = 0,正概率出牌机会弱支配
                # 停手——放行照旧。
                _hc_ok = contracts.ensure_contract(
                    ('refresh', 'r1_horizon_closed'),
                    contracts.ContractCtx(gold=gold), counters) \
                    and crit_refresh.r1_horizon_closed(_rounds)
                if _hc_ok:
                    ok_r1 = True
                    _r1_src = 'must_spend_r1_yielded'   # 触发源记录(sim obs)
                    _count('must_spend_r1_account_yielded')   # 零静默纪律
                    if _arms is not None:
                        # F-6(落地审;批件 §6-4)键④联合分键。辖域申报:
                        # 本键现辖 = 末轮豁免支放行量;修复前旧批读数 =
                        # 全域 yielded 量级(同上报告,零买入连刷段量级
                        # 代理),两口径禁混桶,跨批对照按口径分节。
                        _count('must_spend_r1_yielded_no_target')
                else:
                    # 期望账前件恢复:「一次买齐这一级即停」的完整性判据
                    #(r1_commitment_account 路径总账,输入全为游戏定义
                    # 量)全域一致辖刷新发射——计划账超预算 = 一次买不
                    # 齐,部分刷的期望尾段 = 零产出烧金段(主批零买入
                    # 刷新 761 次 × 2 金);拦后帧落 L3 必花域升级
                    #(转升级)或 CloseShop(停手),泄金阶梯买/压库臂
                    # 不受影响。血线维度不辖本判据(user_playstyle
                    # [39]:hp 只进读数位)。
                    ok_r1 = False
                    _count('must_spend_r1_account_fail')
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
                    refresh_cost_effective(None, 0, bs=bs)):
                # ---- P92 全通道可实现买入集存在性门(T-263,ADR-0635;
                # math_proofs P92「在册结构的严格化非新门」)----
                # p40 R0-1 在册语义的席满维/可购性维落地:四买入通道
                # (dominance/义务 M2/EV/合成完备购)帧级可达全假 ⇒
                # 任何店产不触发买入 ⇒ 付费刷新净差 = −(c_eff+L) < 0
                # 严格,拦刷(fail-closed,落凑息/CloseShop 既有续流)。
                # 判定尺单一源 = crit_refresh.all_channel_buy_exists;
                # seat_recoverable 传收窄判定 p92_seat_recoverable
                #(腾席臂同参资格面非空,IC-1 单源;旧 P56 投影金额代理
                # 退役,行为差锁 = test_cw_seat_recoverable_narrow)。
                # P36-a 让位:危机不变式先于本门(01 §3.4 既有序;现行
                # 决策链无危机直通支,executor 结构位承载)。
                _p92_ready = contracts.ensure_contract(
                    ('refresh', 'all_channel_buy_exists'),
                    contracts.ContractCtx(gold=gold), counters)
                _p92_ok = False
                if _p92_ready:
                    _p92_missing = sorted(
                        {int(CHARACTERS[m].cost) for m in missing
                         if CHARACTERS.get(m) is not None
                         and CHARACTERS[m].cost})
                    _p92_stockpile = sorted(
                        {int(CHARACTERS[m].cost) for m in buy_members
                         if CHARACTERS.get(m) is not None
                         and CHARACTERS[m].cost
                         and _cnt(m, 1) == 1 and _cnt(m, 2) == 0})
                    # ④候选 = 形态对名集 ∩ buy_members(资格维对齐 M2b
                    # 循环同函数上方同一变量=同一单源;形态维单一源 =
                    # _merge_pair_names)。T-295 对抗审问题 6 转正
                    #(reviews/T-295-方案对抗审.md):旧装配遍历
                    # bench∪deployed 全体不滤买入资格,∉采购集的 1★×2
                    # 对被算「④可达」→ 全通道死帧族假可达放行白刷。
                    # CHARACTERS 防御保留(识别面残名)。
                    _p92_pairs = sorted(
                        {int(CHARACTERS[n].cost)
                         for n in _merge_pair_names(bench, deployed)
                         if n in set(buy_members)
                         and CHARACTERS.get(n) is not None
                         and CHARACTERS[n].cost})
                    _p92_ok = crit_refresh.all_channel_buy_exists(
                        gold=gold, g_star=g_star, cap_resolved=cap_resolved,
                        bench_free=bench_free,
                        seat_recoverable=p92_seat_recoverable(
                            session, bench, k_members, bs,
                            cap_hold=_cap_hold_now,
                            current_round=round_num_of(bs),
                            defer_names=_t3_protect, counters=counters,
                            dedup_names=_mm_dedup),
                        missing_costs=_p92_missing,
                        stockpile_costs=_p92_stockpile,
                        merge_pair_costs=_p92_pairs,
                        level=_lvl,
                        ev_face_open=not provisional.is_none('U_X'),
                        window_nonempty=bool(card_w))
                if _p92_ready and _p92_ok:
                    if _reopen_armed:
                        _count('shop_reopen_discretionary_actions')
                    # reason = 触发源记录字段(非指令;sim obs 分键消费,
                    # 执行层不读——cw_state.RefreshShop.reason 值域契约)。
                    return RefreshShop(
                        cost=refresh_cost_effective(None, 0, bs=bs),
                        reason=_r1_src)
                if _p92_ready:
                    # 面② 审计①桶计数(全通道口径判定尺,禁以 P40 E
                    # 口径单独判定);必花域内加计域内 liveness 键
                    # (与 budget_fail 混桶禁)。
                    _count('p92_no_buy_refresh_blocked')
                    if _zone_hit:
                        _count('must_spend_r1_no_buy_blocked')
            elif _zone_hit:
                # 刷新臂 liveness 显影(52 轮 sim 设计输入②):域内刷新
                # 尝试被可负担性硬闸拦 = 显式分键,禁恒零盲区
                #(directed_refresh_game_cap_lock 绿灯掩盖恒零教训)。
                _count('must_spend_r1_budget_fail')
        # 凑息卖·回拉发射位(T1 语义;设计 13_buy_face_design §2.2):
        # 金位触发(期望态金 < g* 才发射)+ 目标量止盈(remaining 递减
        # 贪心,Σrefund ≥ 缺口即止)。prefer_names = 本访问已买件
        # (carried 融合:执行侧/兼容驱动器在 BuyCard 决策后登记,
        # R2-N1 首卖刚买件连带损失=0)。defer_names = T3 同轮保留集
        #(凑息回拉通道绝对跳过被保件——门槛7 不等式保证跳过无损,
        # 买后同轮即卖自旋的路径 A 在此精确切除)。
        if contracts.ensure_contract(
                ('sell', 'sell_for_interest'),
                contracts.ContractCtx(gold=gold), counters):
            # T-115 Z1 排除集扩展(ADR-0580)→ 批 3 全量形态:装配单一
            # 源 = sell_gate.sell_exclusions(channel='interest', ADR-0585)
            # = 义务基座(锁线宽集解析在装配体内完成,落地审低-1 修复:
            # 调用只传各自 k_members,禁调用侧自选基座)∪ 静态持有两集
            # ∪ 窗口段(press 登记活跃帧禁卖回,W1;F1 锁线清空废除,
            # P78-3/W3)。凑息与 prep ②(a) 接线两处同步(只扩一处时另一
            # 处成卖回漏口——shop 访视帧 bench ④件 1★ 无效果仍会入资格),
            # 判据本体零改(B3 单一源纪律,参数级扩展)。
            _slots, skey = crit_sell.sell_for_interest(
                gold, bench, cap_resolved, k_members, state=bs,
                prefer_names=tuple(getattr(
                    state_of(session), 'cw4_visit_bought_names', ()) or ()),
                exclude_names=sell_gate.sell_exclusions(
                    session, k_members, channel='interest',
                    cap_hold=_cap_hold_now,
                    current_round=round_num_of(bs)),
                defer_names=_t3_protect,
                counters=counters,
                dedup_names=_mm_dedup)
        else:
            _slots, skey = [], 'contract_abstain'
        if not skey:
            for s in _slots:
                bc = next((b for b in bench if b.slot == s), None)
                idx = bench_slots_of(bs).index(bc) if bc is not None else None
                if idx is None:
                    continue
                _iname = (bc.char_id or '') if bc else ''
                _note_sell(_iname)
                # reason 仅存线账闭合孤儿证明标记(T-141/ADR-0591:义务
                # 买入当轮 K 窄化出基座,闭合后凑息清算 = P78-2a/P78 INV
                # 合法形态,键带账闭合证明供同轮买卖检查豁免面分键;被保
                # 件已被 defer 绝对跳过)。凑息通道归因值已随 2026-09-08
                # 用户归因遥测删除指令拆除,'' = 未标缺省形态。
                # 发射 = 中间步动作:卖出真执行回金,金位向 g* 递增,
                # 止盈(Σrefund ≥ 缺口)后凑息位不再触发、后续位续评;
                # CloseShop 会提前终结商店段(T-238 修复,机制同 M4
                # 缺员腾席位注释)。
                return SellBench(bench_idx=idx,
                                 income=_shop_sell_refund(bc) if bc else None,
                                 expect=_iname,
                                 reason=('line_switch_collapse'
                                         if _iname in _sw_orphans
                                         else ''))
    # 支付支撑通道(两臂同开,R13-5):骨架义务动作金不足侧筹资变现。
    # F2 已由 ADR-0585 §4 拆三块修订(原「有意不扩 Z1 排除集」申报废止):
    # ①义务基座并入(本位旧排除 buy_members 与义务基座同源,并入零
    # 漂移);②③④ 持有件变现 = 显式兜底豁免(P78-5 四条件,批 3 本批
    # 接线:主路径(非持有资格面)空 ∧ 仍需筹资 ⇒ 兜底池单笔变现,
    # 分键 funding_hold_liquidated;豁免面(同轮买卖检查)同步见
    # kernel/cw_state.SELL_BENCH_CONVERT_REASONS);③窗口段生效(批 3:
    # press 登记活跃帧筹资卖回被禁,W1)。
    if missing:
        mf = mandate.MandateFrame(
            gold=gold, level=level_of(bs), bench=bench, deployed=deployed,
            deploy_cap=max_units_of(bs),
            node_type=node_kind_of(bs),
            stop_flag=stop_flag, k_members=k_members,
            round_num=round_num_of(bs))
        need = mandate.cheapest_member_cost(mf)
        for m in missing:
            shop_cands = [c for c in shop_payload_content_cards(bs.shop.value)
                          if (c.name or '') == m]
            if shop_cands:
                need = min(need, min(
                    (card_cost(c)) for c in shop_cands))
                break
        # 排除集 = 统一装配 A 全量形态(单一入口 sell_gate;ADR-0585):
        # 义务基座(防义务件被筹资卖 → M2 重买换手)+ 静态持有两集
        #(W4 同格)+ 窗口段(批 3)。
        _f_excl = sell_gate.sell_exclusions(session, k_members,
                                            channel='funding',
                                            cap_hold=_cap_hold_now,
                                            current_round=int(
                                                round_num_of(bs) or 1))
        fslots, _fkey = crit_sell.funding_support_sell(
            gold, need, bench, k_members, state=bs,
            exclude_names=_f_excl,
            defer_names=_t3_protect,   # T3:转化类仅降序放行,非禁卖
            counters=counters, dedup_names=_mm_dedup) \
            if contracts.ensure_contract(
                ('sell', 'funding_support_sell'),
                contracts.ContractCtx(gold=gold), counters) else ([], '')
        # 兜底豁免(P78-5:主路径空 ∧ 仍需筹资;池定义与达成量化单一源
        # = sell_gate.funding_hold_fallback;单笔即止,need 即止)。
        _f_fallback = []
        if not fslots and gold < need:
            _f_fallback = sell_gate.funding_hold_fallback(
                session, k_members, bench, gold=gold, need=need,
                a_exclusions=_f_excl, deployed=deployed_slots_of(bs),
                cap_hold=_cap_hold_now)
        for s in fslots:
            bc = next((b for b in bench if b.slot == s), None)
            idx = bench_slots_of(bs).index(bc) if bc is not None else None
            if idx is None:
                continue
            _fname = (bc.char_id or '') if bc else ''
            # T3 转化类卖出销账(为骨架义务筹资卖出被保垫件;转化类/
            # plain 分键计数已随 2026-09-08 用户归因遥测删除指令拆除,
            # 销账行为面保留)。
            _fprot = _fname in _t3_protect
            if _fprot:
                mandate.stall_buys_consume(session, _fname)
            _note_sell(_fname)
            # reason 仅存线账闭合孤儿证明标记(T-141/ADR-0591,通道
            # 无关);纯归因填充已删,'' = 未标缺省形态。被保垫件筹资卖
            # = 转化类,分键走 convert_reason(ADR-0611 §3-5)。
            # 发射 = 中间步动作:卖出真执行筹资,下一决策迭代金 ≥ need
            # 由 M2 原判据买入义务件;CloseShop 会提前终结商店段
            #(T-238 修复,机制同 M4 缺员腾席位注释)。
            return SellBench(
                bench_idx=idx,
                income=_shop_sell_refund(bc) if bc else None,
                expect=_fname,
                reason=('line_switch_collapse'
                        if _fname in _sw_orphans
                        else ''),
                convert_reason=('funding_support_stall_convert'
                                if _fprot else ''))
        for bc in _f_fallback:
            _fidx = bench_slots_of(bs).index(bc)
            _fname = bc.char_id or ''
            # 卖出销账(出口①;兜底分键计数已随 2026-09-08 用户归因
            # 遥测删除指令拆除,销账行为面保留)。reason 缺省 '' 未标;
            # 兜底变现 = P78-5 最后手段豁免语境,转化分键恒带
            # funding_hold_liquidated(ADR-0611 §3-5)。
            sell_gate.consume_on_sell(session, _fname)
            _note_sell(_fname)
            # 发射 = 中间步动作(同筹资主路径):卖出真执行筹资,
            # 下一决策迭代金 ≥ need 由 M2 原判据买入义务件;CloseShop
            # 会提前终结商店段(T-238 修复,机制同 M4 缺员腾席位注释)。
            return SellBench(
                bench_idx=_fidx,
                income=_shop_sell_refund(bc),
                expect=_fname,
                convert_reason='funding_hold_liquidated')

    # ---- D-D 硬节点补强门消费(观察级接线;逐帧计数,粒度申报见上)----
    _gate_open, _gkey = crit_refresh.hard_node_reinforce_gate(
        node_kind_of(bs), gold_of(bs), g_star) \
        if contracts.ensure_contract(
            ('refresh', 'hard_node_reinforce_gate'),
            contracts.ContractCtx(gold=gold_of(bs)), counters) \
        else (False, '')
    if _gate_open:
        _count('shop_hard_node_gate_open')

    # ---- 终结:CloseShop(恒可用;D-P2idle 带金零动作帧计数)----
    # 键语义 = CloseShop 收尾且金 ≥10 的 visit(visit 含刷新段时与旧
    # shop_wave_idle_gold 波计数不等值,跨结构不可对拍)。
    if gold_of(bs) >= 10:
        _count('shop_visit_idle_gold')
    # L3 必花域升级(20 号稿 §3.1-L3;授权文号 = 用户裁定 §1「无论什么
    # hp,金这么多都是要花的」——消费权优先于期望核算的否决权;域内
    # p1/p2_levelup_stop_hp 让位 = ADR-0528,域外停付线照旧)。
    # 发射位合并纪律(§3.5):触发源 = M3 三臂 ∨ 必花域,同一
    # LevelUpShop 单动作消费,auth_basis 触发源分键(m3_batch:must_spend)
    # 可归因,无第二升级机制。本位点 = 分层序末位(L1 M2/EV/R1 与
    # L2 出口③全未命中)——「L1/L2 无对象或未命中时 L3 消费」的载体位;
    # 负账(P35 lv9→10 恒负/P39 L9→L10 −11.4)属 (iii) 类成本披露,
    # 非否决门(§2.2-3)。资格硬闸((i) 零解封):等级 cap(lv9_stop 族)/
    # 整批可负担(spend_unified + check_affordable);拒因分键
    # level_cap/batch_unaffordable 零静默。
    # T-115 规则① 消费位2(ADR-0580):本变体触发条件含「三臂未触发」,
    # 大金奖励帧三臂被压空后若无此守卫会经必花域绕过抑制(方案审 L3
    # 实证的绕行面)——奖励帧显式拒,分键独立可辨。
    if (_zone_hit and not (_arm1 or _arm0 or _pop)
            and _reward_defer):
        _count('reward_node_must_spend_defer')
    elif _zone_hit and not (_arm1 or _arm0 or _pop):
        _lvl_now = level_of(bs)
        _lv9_ok = contracts.ensure_contract(
            ('levelup', 'lv9_stop'), contracts.ContractCtx(), counters) \
            and contracts.ensure_contract(
                ('levelup', 'xp_ledger_stop'), contracts.ContractCtx(),
                counters) \
            and not crit_levelup.lv9_stop(_lvl_now, _reg.level_max) \
            and not crit_levelup.xp_ledger_stop(
                bs.xp.value, _reg.level_max)   # T-228 账本停,与 M3 批位同判据
        if not _lvl_readable or not _lv9_ok:
            _count('level_cap')
        else:
            _clicks3 = clicks_to_next_level(bs)
            _cost3 = xp_click_cost(bs)
            _unified_ok = contracts.ensure_contract(
                ('levelup', 'spend_unified'),
                contracts.ContractCtx(gold=gold), counters) \
                and crit_levelup.spend_unified(_clicks3, gold, _cost3)
            if not _unified_ok:
                _count('batch_unaffordable')
            else:
                ok3, _ = mandate.check_affordable(
                    gold, 0, batch_cost=_clicks3 * _cost3)
                if not (ok3 and _clicks3 > 0):
                    _count('batch_unaffordable')
                else:
                    # P72 (3) 全段预算闸在必花域内生效(ADR-0576 承继
                    # ADR-0560 方案审 v2 采纳 3;73002 病灶即域内帧——
                    # 域内豁免 = 修复不成立):必花域授权辖「要花」不辖
                    # 「花在哪」,闸拒只量住升级通道,买卡臂(M2/压库/
                    # 下帧命中卡)仍是合法消费出口,义务不被否决。拒因
                    # 独立分键(与域外 levelup_budget_gate_blocked 分开,
                    # 归因可辨);闸拒 ∧ bench 无空席(义务无处安放)⇒
                    # 金滞留死角观测分键(纯观察,攒 sim 数据后再裁是否
                    # 需要域内降档——降档 = 部分买,与 P48 整买冲突,
                    # 当前禁做)。
                    _gate3_ok, _gate3_why = False, ''
                    if contracts.ensure_contract(
                            ('levelup', 'levelup_budget_gate'),
                            contracts.ContractCtx(gold=gold,
                                                  deploy_cap=_cap_now),
                            counters):
                        _gate3_ok, _gate3_why = (
                            crit_levelup.levelup_budget_gate(
                                bs, session, gold, cap_resolved,
                                k_members, bench, deployed,
                                _clicks3, _cost3))
                    if _gate3_ok:
                        return LevelUpShop(cost=_cost3,
                                           auth_basis='m3_batch:must_spend')
                    if _gate3_why == 'guarantee_floor_defer':
                        # 保底金门推迟独立分键(ADR-0603):域内 XP 花穿
                        # 推迟与 (3a) 量闸拒归因分离,禁混键(与 mandate/
                        # entry 位的原键转发同语义,本位加 must_spend 前缀)
                        _count('must_spend_guarantee_floor_defer')
                    else:
                        _count('budget_gate_must_spend_defer')
                    if bench_free <= 0:
                        _count('budget_gate_must_spend_deadend')
    return CloseShop()


