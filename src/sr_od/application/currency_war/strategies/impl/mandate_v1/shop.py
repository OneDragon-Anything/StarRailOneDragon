"""cw4 商店线 decide_shop_screen——步4b 商店波形态(criteria 七面商店接线)。

SIM_CONSUMPTION_MAP Q1:sim A/B 证明面 = 商店波经济决策(买/卖/升/刷/事务)
——本模块是 mandate_v1 商店线的决策本体,黑板唯一输入 =
``session.shop_state_frame``(GameState,写者白名单=商店观察段/sim 引擎)。

商店波形态(IMPL_DESIGN §4.2 发射面规格,entry 三遍编排的商店侧投影):

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
   13_buy_face_design §2.2)+ 逐动作金/席位静态投影(帧稳定域的前序
   累积静态推出,契约 §2);
3. criteria 七面发射(§4.2.1 臂①旁路集:骨架面[M2/M3/M4/dominance/M6
   存在性]两臂同开,真 EV 发射面[ev_buy/付费刷新/凑息档]臂①旁路;
   支付支撑通道两臂同开,R13-5);
4. 截断/排序:契约 v2 §3.1 商店线域(BuyCard/LevelUpShop 可续、拖拽族
   条件续、RefreshShop/CompTransaction 截断点、合成触发=可能触发合成的
   买牌后截断)+ §3.3 fail-closed(PickEvent 系 pick 决策返回载体,词表源
   对账声明辖外 ⇒ 词表外动作处置)。

rng 中立:本模块零 rng 消费(SIM_CONSUMPTION_MAP ③-5 会话流派生契约);
registry 属性经 bridge 自带(Q3 坑位①)。

D-BUYNOTE(修复池执行层附注):M3 升级内嵌 P48 整买纪律
  (``criteria/levelup.spend_unified``,散买 XP 零收益拦截)。

计数键(session.cw4_counters,登记见 design_telemetry 键节——步4b 新键):
shop_ev_u_unavailable / shop_ev_shop_domain / shop_ev_no_candidate /
shop_ev_all_vetoed / shop_r1_ev_unavailable / shop_wave_idle_gold /
shop_hard_node_gate_open / shop_drought_reset_on_buy /
shop_merge_trigger_truncate;K 空窗回退修复批(2026-09-03 第三病灶)
增补 shop_k_fallback_p1_gap(空窗帧回退计数);复审返工批
(FIX_REVIEW_20260903 R3)增补 shop_k_fallback_p1_lock_band(P1 锁线
过渡带回退计数)/shop_k_fallback_p2plus(P2+ 带回退计数)——三带
回退分键登记=design_telemetry「复审返工批」节。

R197 修复批增补(登记=design_telemetry「R197 修复批」节):
- 症3:商店波同槽去重防线(pre-wave sold 槽集合 vs funding_support/
  sell_for_interest 提案冲突丢弃 + 计数,复用 ``ev_conflict_dropped``
  键——与 prep 侧同型同键,发射前丢弃语义一致);
- 症4:①拖拽族名-槽一致性复检实装(契约 §3.1 行既有要求;截断计数
  复用 ``emitter_conditional_truncated``);②商店词表 LevelUp 超集收口
  =**发射侧归一化**:商店波发射一律 LevelUpShop(is-a LevelUp,契约表
  既有行),裸 LevelUp 进截断器前归一化,词表收紧为契约 8 类(契约
  正文零改动);
- 症6:funding 通道 need 缺省改 ``mandate.cheapest_member_cost`` 派生
  (注册表单一源;字面量 3 删除);
- 症9:dominance/M6 存在性门金口径改**支出后投影金**(同波 M4/M2/M3
  支出后;实际支出安全由 check_affordable 兜底,本改只正存在性计数
  键的触发面口径)。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    expected_refreshes_for_card,
    refresh_prob,
)
from sr_od.application.currency_war.kernel import cw_intention
from sr_od.application.currency_war.kernel.cw_economy import (
    clicks_to_next_level,
    xp_click_cost,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BENCH_CAPACITY,
    REFRESH_COST_BASE,
    BuyCard,
    CompTransaction,
    DeployMove,
    LevelUp,
    LevelUpShop,
    RefreshShop,
    SellBench,
    SellDeployed,
    SwapDeploy,
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
    vbar,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.income import (
    net_income,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
    loss_exact,
    saturation_line,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vbar import (
    DEFAULT_VBAR_READING,
    VBAR_READINGS,
    window_vbar,
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

# ===== 截断分类(契约 v2 §3.1 商店线域;R197 症4②:词表收紧为契约
# 8 类——裸 LevelUp 不在词表,进截断器前经发射侧归一化转 LevelUpShop
# [is-a LevelUp,契约表既有行;执行器/sim 按 isinstance(a, LevelUp) 消费,
# 归一化零行为差]) =====

#: 可续(牌位/按钮坐标不变,画面零迁移)
_SHOP_CONTINUE: tuple[type, ...] = (BuyCard, LevelUpShop)
#: 条件续(bench 索引结构恒稳[ADR-0316/0392 槽位模型]+名-槽一致性复检;
#: 本发射器的拖拽成员全部引用生成期槽位下标,board 空位/星级合成按
#: 前序动作累积静态推出——推不出即截断)
_SHOP_CONDITIONAL: tuple[type, ...] = (
    SellBench, SellDeployed, DeployMove, SwapDeploy,
)
#: 截断点(该动作可作序列最后一个动作发出,其后截断)
_SHOP_TRUNCATION: tuple[type, ...] = (RefreshShop, CompTransaction)
# PickEvent 系 pick 决策返回载体(契约 v2 §3.1 词表源对账声明:非商店线
# 发射动作)⇒ 走 §3.3 fail-closed(unknown),不猜测分类。


def _shop_sell_refund(bc: BenchChar) -> int | None:
    """卖出预期回金(sell_refund 口径;注册表 cost 缺失 ⇒ None=未标)。"""
    ch = CHARACTERS.get(bc.char_id or '')
    if ch is None or not ch.cost:
        return None
    return sell_refund(bc.star, ch.cost)


def _r1_member_accounts(k_members: tuple[str, ...],
                        bench: list, deployed: list,
                        state: GameState, session: StrategySession,
                        rounds: int) -> list[float]:
    """R1 承诺账装配侧(P40 ①/②;k=1 单卡代表形态)。

    合格集 E = 未达 2★ 的线成员(目标阵容件,P40 A4);逐成员账 =
    ``c_eff·expected_refreshes_for_card(level, cost, star=2, j)
    + L(gold, ⌈c_eff·E⌉, R_剩余, Ī)``。口径申报(出处→边界):
    - j = bench∪deployed 中该成员 1★ 副本数(star≥2 = 成型即出域;
      与 decision_v2 ``_vd_core_copies`` 的 len 口径同源;2★ 卡=3 基础
      副本的折叠不展开——j 低估 ⇒ k−j 高估 ⇒ E 高估 ⇒ 账高估 = 门收紧
      向,保守端申报);
    - c_taken=0(P40 待标定清单「c_taken 现场读数:缺则 0(保守低估
      q)」——q 低估 ⇒ E 高估 ⇒ 同上保守向);
    - Ī = ``income.net_income(round_num, streak_pre=0)``(streak 下界
      ⇒ L 上界 ⇒ 账高估 = 保守向;R09 收入三表现算,非 i_bar 常量);
    - ``rounds`` = 决策帧 R_剩余(horizon.r_remaining 现算,消费位传入
      ——与门侧 V̄_net(r) 同帧同源,禁两次现算各读各的);
    - 该级不出此费(refresh_prob≤0)或 E=inf 的成员不可追,剔除
      (账 inf 由判据侧 isfinite 过滤 = R0-1 合格集空特例)。
    """
    level = int(state.level or 1)
    c_eff = int(state.shop_refresh_cost or REFRESH_COST_BASE)
    ibar = net_income(int(state.round_num or 1), 0)
    accounts: list[float] = []
    for m in k_members:
        ch = CHARACTERS.get(m)
        if ch is None or not ch.cost:
            continue
        if refresh_prob(level, ch.cost) <= 0.0:
            continue                      # 该级不出此费:不可追(P40 R0)
        copies = [c for c in list(bench) + list(deployed)
                  if (getattr(c, 'char_id', '') or '') == m]
        if any((getattr(c, 'star', 1) or 1) >= 2 for c in copies):
            continue                      # 已 2★:成员成型,出合格集
        j = len(copies)
        e = expected_refreshes_for_card(level, ch.cost, target_star=2,
                                        owned=j)
        spend = int(math.ceil(c_eff * e))
        l_val = loss_exact(int(state.gold or 0), spend, rounds, ibar)
        accounts.append(c_eff * e + l_val)
    return accounts


def _r2_card_reserve(k_members: tuple[str, ...],
                     bench: list, deployed: list,
                     state: GameState) -> int:
    """R2 预算门 Σ预留卡价 ρ = 合格集最低费卡价(修 R2 批)。

    证明单一源 = p54-r2-interest-floor §②(零新自由参数:ρ 锚
    CHARACTERS 注册表 cost,非字面量)。可追过滤与 ``_r1_member_
    accounts`` 同一(该级出此费 refresh_prob>0 ∧ 无 2★)——语义
    单一源不复制。单卡下界口径(P54 A2:P40 待标定清单「最低费卡价
    × 期望命中数」在单刷波粒度下的整数下界;多命中超出部分 = 下一波
    R2 重估补足的显式让渡,非破线刷新)。合格集空 ⇒ 0:该帧 R1 必先
    以 no_chaseable_member 关闭,R2 不可达,兜底值不进任何可达比较。
    """
    level = int(state.level or 1)
    costs: list[int] = []
    for m in k_members:
        ch = CHARACTERS.get(m)
        if ch is None or not ch.cost:
            continue
        if refresh_prob(level, ch.cost) <= 0.0:
            continue
        copies = [c for c in list(bench) + list(deployed)
                  if (getattr(c, 'char_id', '') or '') == m]
        if any((getattr(c, 'star', 1) or 1) >= 2 for c in copies):
            continue
        costs.append(int(ch.cost))
    return min(costs) if costs else 0


def truncate_shop_frame_stable(actions: list[Action],
                               state: GameState,
                               session: StrategySession | None = None,
                               ) -> list[Action]:
    """商店线帧稳定截断发射器(契约 v2 §2 + §3.1 + §3.3)。

    逐动作判「本动作执行后的画面状态能否静态推出」:

    - BuyCard/LevelUpShop = 可续(同 x 重复发射执行侧去重,现役);
      **归一化(R197 症4②)**:裸 ``LevelUp`` 进本发射器前转
      ``LevelUpShop``(同字段保留)——商店波发射一律 LevelUpShop,
      词表收紧为契约 8 类,§3.3 fail-closed 通道不再被词表超集静默放宽;
    - **合成触发**(§3.1 末行):买入使同名同星持有数(含场上,保守域)
      达到 3 ⇒ 自动合成可能触发、bench 形变不可静态精确预测 ⇒ 该买牌后
      截断 + ``shop_merge_trigger_truncate`` 计数(保守边界呈报:场上
      deployed 副本并入计数域,合成载体可在场域);
    - 拖拽族 = 条件续 + **名-槽一致性复检实装(R197 症4①,契约 §3.1 行
      既有要求;与 prep 侧发射器内复检同载体非双源——两域词表不同,
      复检同在各自发射器内)**:SellBench/DeployMove/SwapDeploy 的
      ``bench_idx`` 须落在生成期 bench 槽位表占用位上(前序卖出/拖出
      累积投影,卖出后槽位从投影集移除),``SellBench.expect``/
      ``SellDeployed.expect`` 名不符 ⇒ 推不出即截断 +
      ``emitter_conditional_truncated`` 计数;SellDeployed 的
      ``deployed_idx`` 同款占用复检(deployed 槽位表,卖出置 None
      不移位,ADR-0392);
    - RefreshShop/CompTransaction = 截断点(刷后/事务 fill 后重观察
      重决策,sim break-redecide 先例);
    - 词表外/无分类(PickEvent 等)⇒ §3.3 fail-closed:该动作处截断 +
      ``emitter_unknown_action_truncated`` 计数披露(键已登记,步3+4 批)。

    尾动作丢弃计数(R197 症1② 同款零静默纪律):任一截断路径丢弃的
    后续动作逐个计数 ``emitter_post_truncation_dropped``。
    """
    counters = None
    if session is not None:
        counters = getattr(session, 'cw4_counters', None)
        if not isinstance(counters, dict):
            counters = None

    def _count(key: str, n: int = 1) -> None:
        if counters is not None:
            counters[key] = counters.get(key, 0) + n

    # 同名同星持有计数(合成触发的静态投影基准;bench∪deployed 全场域)
    held: dict[tuple[str, int], int] = {}
    for b in (state.bench or []):
        if b is not None:
            held[(b.char_id or '', b.star or 1)] = \
                held.get((b.char_id or '', b.star or 1), 0) + 1
    for d in (state.deployed or []):
        if d is not None:
            held[(d.char_id or '', d.star or 1)] = \
                held.get((d.char_id or '', d.star or 1), 0) + 1

    # 名-槽复检语境(R197 症4①):生成期槽位表占用投影——前序卖出/拖出
    # 累积移除;deployed 侧同款(卖出置 None 不移位)。
    bench_table = list(state.bench or [])
    deployed_table = list(state.deployed or [])

    def _bench_alive(idx: int) -> bool:
        return 0 <= idx < len(bench_table) and bench_table[idx] is not None

    def _deployed_alive(idx: int) -> bool:
        return (0 <= idx < len(deployed_table)
                and deployed_table[idx] is not None)

    out: list[Action] = []

    def _cut() -> list[Action]:
        _count('emitter_post_truncation_dropped', len(actions) - len(out))
        return out

    for a in actions:
        # 归一化(R197 症4②):裸 LevelUp → LevelUpShop(字段保留;
        # isinstance(LevelUp) 消费面零行为差)
        if isinstance(a, LevelUp) and not isinstance(a, LevelUpShop):
            a = LevelUpShop(cost=a.cost, auth_basis=a.auth_basis)
        if not isinstance(a, (BuyCard, LevelUpShop, SellBench,
                              SellDeployed, DeployMove, SwapDeploy,
                              RefreshShop, CompTransaction)):
            # 含 PickEvent(pick 决策返回载体,词表源对账声明辖外)与
            # 词表外一切类型 ⇒ §3.3 fail-closed
            _count('emitter_unknown_action_truncated')
            return _cut()         # §3.3:词表外动作处截断(不猜测分类)
        # 拖拽族名-槽一致性复检(R197 症4①)
        if isinstance(a, SellBench):
            if not _bench_alive(a.bench_idx):
                _count('emitter_conditional_truncated')
                return _cut()     # 引用空槽/越界:推不出即截断
            bc = bench_table[a.bench_idx]
            if a.expect and (bc.char_id or '') != a.expect:
                _count('emitter_conditional_truncated')
                return _cut()     # 名-槽不一致:跨代际提案,截断
            bench_table[a.bench_idx] = None   # 卖出累积投影
        elif isinstance(a, DeployMove):
            if not _bench_alive(a.bench_idx):
                _count('emitter_conditional_truncated')
                return _cut()
            bench_table[a.bench_idx] = None   # 拖出累积投影
        elif isinstance(a, SwapDeploy):
            if not _bench_alive(a.bench_idx) \
                    or not _deployed_alive(a.deployed_idx):
                _count('emitter_conditional_truncated')
                return _cut()
        elif isinstance(a, SellDeployed):
            if not _deployed_alive(a.deployed_idx):
                _count('emitter_conditional_truncated')
                return _cut()
            dc = deployed_table[a.deployed_idx]
            if a.expect and (dc.char_id or '') != a.expect:
                _count('emitter_conditional_truncated')
                return _cut()
            deployed_table[a.deployed_idx] = None
        out.append(a)
        if isinstance(a, (RefreshShop, CompTransaction)):
            return _cut()            # 截断点
        if isinstance(a, BuyCard):
            key = (a.card.name or '', a.card.star or 1)
            if held.get(key, 0) >= 2:
                # 本买使同名同星达 3 ⇒ 可能触发自动合成 ⇒ 买牌后截断
                _count('shop_merge_trigger_truncate')
                return _cut()
            held[key] = held.get(key, 0) + 1
    return out


def _frame_search_windows(session: StrategySession, state: GameState,
                          registry, reading: str,
                          counters: dict) -> tuple[frozenset[int],
                                                   frozenset[int]]:
    """帧级搜索窗口(T1 短路径;设计 13_buy_face_design §2.3/§3.2)。

    T_SEARCH_A 布尔门退役出窗口消费位:V̄ 改接 ``vbar.v_bar_net`` 帧级
    现算链(修 A 单一源,p53;与 R1 刷新门比较项同链同帧——r =
    ``horizon.r_remaining`` 本帧现算一次,禁两次现算各读各的),零新
    自由参数。读法 = P57 双读法参数化(``vbar.window_vbar``;生产默认
    读法② frame_horizon,sim 双臂经 config.cw4_vbar_reading 切换)。
    P57 窗口集指纹(分键遥测 R3-R5,零额外跑批):两读法窗口集不同的
    帧计数,档级/单卡两族分键。空集语义 = 真无窗口帧(等级无合格档时
    V̄ 链自然给出空集,非门控)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.odds import (
        card_search_window,
        tier_search_window,
    )
    level = int(state.level or 1)
    rounds = horizon.r_remaining(session, int(state.plane or 1),
                                 int(state.round_num or 1))
    v_step = window_vbar(registry, rounds, 'per_step',
                         plane=int(state.plane or 1))
    v_frame = window_vbar(registry, rounds, 'frame_horizon',
                          plane=int(state.plane or 1))
    tier_step = tier_search_window(level, v_step)
    tier_frame = tier_search_window(level, v_frame)
    card_step = card_search_window(level, v_step)
    card_frame = card_search_window(level, v_frame)
    if tier_step != tier_frame:
        counters['p57_tier_window_diff_frames'] = \
            counters.get('p57_tier_window_diff_frames', 0) + 1
    if card_step != card_frame:
        counters['p57_card_window_diff_frames'] = \
            counters.get('p57_card_window_diff_frames', 0) + 1
    v = v_step if reading == 'per_step' else v_frame
    return tier_search_window(level, v), card_search_window(level, v)


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
                # 合并完成件拒因细分(候选②判读面):已持 2 张同名同星
                # 1★ 且无 2★ 成件 ⇒ 第三张买入即合成 2★,拒因不再是中性
                # 「owned」而是「合并买入未发生」的具体门(bench 满/金不足),
                # 复盘可直接归因(g_20260904_054904 p2r1 判读缺口)。
                copies = [c for c in bench + deployed
                          if (c.char_id or '') == name]
                merge_completable = (len(copies) == 2
                                     and all((c.star or 1) < 2
                                             for c in copies))
                cost = min((c.cost if c.cost else 3)
                           for c in (state.shop or [])
                           if (c.name or '') == name)
                if merge_completable and bench_free <= 0:
                    out[name] = 'merge_bench_full'
                elif merge_completable and gold < cost:
                    out[name] = 'merge_unaffordable'
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


def decide_shop_wave(state: GameState, session: StrategySession,
                     config: object, *, registry=None) -> list[Action]:
    """商店波决策(entry 三遍编排的商店侧投影;返回 ``list[Action]``)。

    编排:方向(K/stop_flag/干旱)→ 预算投影(g*/S 预留/金与席位静态
    投影)→ 骨架 pass(M4 腾席→M2 线成员买入→dominance_buy→M3 升级
    整批→M6 溢余)→ EV pass(臂①旁路集=§4.2.1;支付支撑通道两臂同开)
    → 截断/排序(契约 v2 §3.1)。空序列 = 决策完成(关店,契约 §4)。
    """
    if getattr(session, 'cw4_counters', None) is None:
        session.cw4_counters = {}
    counters: dict = session.cw4_counters

    def _count(key: str) -> None:
        counters[key] = counters.get(key, 0) + 1

    ev_arm = getattr(config, 'ev_arm', 'full')
    if ev_arm not in entry.EV_ARM_VALUES:
        ev_arm = 'full'
    skeleton_only = (ev_arm == 'skeleton_only')

    # ---- ① 方向(证明面投影)----
    k = getattr(session, 'target_comp', None)
    k_members = predicates.line_members(k)
    k_fallback: frozenset[str] | set[str] | None = None
    k_band: str | None = None
    _ist = getattr(session, 'v3_intention', None)
    if k is None and _ist is not None:
        # K 空窗回退(FIX_REVIEW_20260903 R3 扩域;经济冻结批单一源化):
        # 派生本体已提为 cw_intention.k_empty_window_fallback(商店域与
        # 准备域共用,禁第二源);本处只保留消费面(回退采用+计数键)。
        # ist 缺失=意向供给缺帧,保守侧不回退(现行 () 行为,fail 方向
        # 与 committed_authority 缺供给同款)。
        k_fallback, _tok = cw_intention.k_empty_window_fallback(state, _ist)
        k_band = f'shop_k_fallback_{_tok}'
    # 契约核验(§4.2.2;FIX_REVIEW 防线硬化=可核验派生形态):前提不采信
    # 消费位硬编码声明,核验实解析——k_target=None 且供给在场而回退解析
    # 空集 = 「回退字面量空元组但保留声明」复发形态,违例 ⇒ 不回退
    # +计数(键族 criteria_contract_violation)。sorted=确定性发射序
    # (str 哈希随机化下 frozenset 迭代序跨进程不稳定)。
    if contracts.ensure_contract(
            ('shop', 'k_projection'),
            contracts.ContractCtx(k_target=k,
                                  k_fallback_available=_ist is not None,
                                  k_fallback_resolved=k_fallback),
            counters) and k_fallback:
        k_members = tuple(sorted(k_fallback))
        _count(k_band)
    bench = [b for b in (state.bench or []) if b is not None]
    deployed = [d for d in (state.deployed or []) if d is not None]
    bench_names = [b.char_id or '' for b in bench]
    deployed_names = [d.char_id or '' for d in deployed]
    owned = set(bench_names) | set(deployed_names)
    # 契约核验(§4.2.2,FIX_REVIEW R1 漏接位补齐):stop_buy 消费位经
    # ensure_contract(前提恒真 None 登记,违例路径仅剩未登记键)
    stop_flag = proof.stop_buy(k, bench_names, deployed_names) \
        if contracts.ensure_contract(
            ('proof', 'stop_buy'), contracts.ContractCtx(), counters) \
        else True   # 弃权侧=保守停买——辖域限支配买/溢余面(dominance/M6
        # 受 stop_flag 门);商店线 M2 线成员买入系义务不走停手门([41]),
        # 不受本弃权影响(REWORK_REVIEW_20260903 F3 辖域收口)

    # ---- ② 预算投影 ----
    cap_resolved = mandate._cap_of(session)
    g_star = saturation_line(cap_resolved)
    # P56 可变现息线下界(设计 13_buy_face_design §2.2;dd-026 姊妹缺口
    # 收口):s_reserve := g* − Σ活期退金投影——discretionary 买面(EV/M6)
    # 金约束 gold − cost ≥ s_reserve ⇔ gold − cost + Σrefund ≥ g*
    # (p48 命题 3 可变现口径的同构引用)。活期卡资格谓词与 funding_
    # support_sell 同一 = ``mandate.fuel_sell_candidates`` 单一源。
    # 旧值 b_target(0,0,0)=0(P48 零参退化)使买面可任意跌破息线
    # (floor 对称面缺失,设计 §1.2 定谳)。无 ρ 项防双计:买面支出 x
    # 即刷新门 ρ 预留所指的那笔买入,重复预留=双计(设计 §2.2 同构性
    # 检讨)。帧级静态投影让渡:活期集合以帧首快照计,M4 卖出的活期件
    # 即时从投影扣减(见 M4 段);帧内其余卖出(回拉/支付支撑)发生在
    # 全部买入之后,不进本帧任何金约束比较。Σ=0(无活期卡)时约束退化
    # 为裸金 ≥ g*(保守端,无声洞)。
    liquid_refund = sum(sell_refund(1, bench_char_cost(b))
                        for b in mandate.fuel_sell_candidates(
                            bench, k_members, state=state))
    s_reserve = g_star - liquid_refund
    # R2 预算门预留(P40 R2 规范口径落码,修 R2 批;证明单一源 =
    # p54-r2-interest-floor + dd-026-r2-interest-floor):
    # reserve = 息线 g* + Σ预留卡价 ρ —— 与 P40 溢余段刷窗式
    # ⌊(g−g*−ρ)/c_eff⌋ ≥ 1 逐位等价(P54 §①,判据本体零改动)。
    # 旧值 b_target(0,0,0)=0(P48 零参退化)使门退化为 gold≥2:
    # 金刷穿 0-4、买入链饿死(修 A 后 b1 对拍病灶,P53 §④ 申报 1)。
    # g* = saturation_line(cap_resolved)(守息线同源派生);
    # ρ = 合格集最低费卡价(单卡下界,P54 A2)。辖域:只入刷新门——
    # EV 买面/M6 的 S 预留消费位语义不同(P48 S 线),本批不动(挂账)。
    r2_reserve = g_star + _r2_card_reserve(k_members, bench, deployed,
                                           state)
    # P57 双读法参数化(设计 §2.3/§3.2):读法经 config.cw4_vbar_reading,
    # 生产默认读法② frame_horizon;脏值回落缺省(不放大为行为分叉)。
    _reading = getattr(config, 'cw4_vbar_reading', DEFAULT_VBAR_READING)
    if _reading not in VBAR_READINGS:
        _reading = DEFAULT_VBAR_READING
    # registry 缺省兜底(与 r1 段同先例;本链锚字段在两视图同值——sim
    # 视图只覆写 level_max)。窗口帧级现算一次,M6/EV 两消费位共用同帧
    # 同源(禁各消费位各算各的)。
    _reg = registry
    if _reg is None:
        from sr_od.application.currency_war.kernel.cw_registry import (
            DEFAULT_REGISTRY,
        )
        _reg = DEFAULT_REGISTRY
    tier_w, card_w = _frame_search_windows(session, state, _reg, _reading,
                                           counters)
    gold = int(state.gold or 0)
    bench_free = BENCH_CAPACITY - len(bench)
    out: list[mandate.Emitted] = []
    used_cards: set[int] = set()      # 已发射店槽(identity;防同槽再提案)
    bought_target = False
    # 本帧已发射买入件名集合(T1 回拉 R2-N1 发射约束的 prefer_names 输入:
    # 首卖刚买件使连带卖出损失=0;帧投影架构下刚买件未入 bench,按名
    # 匹配同资格在册件)
    bought_names: list[str] = []
    # 同槽去重防线(R197 症3,与 prep 侧 sold_slots 同型):pre-wave 共享
    # 同一 bench 快照的卖面(M4/sell_for_interest/funding_support)对同
    # bench_idx 双 SellBench = 执行侧第二笔 progressed=False 触发
    # fail-stop,整序列后半被一帧废动作截断——先到先得丢弃 + 计数
    # (``ev_conflict_dropped`` 键复用:发射前丢弃语义与 prep 侧一致)
    sold_idxs: set[int] = set()

    # ---- ③ 骨架 pass ----
    missing = [m for m in k_members if m not in owned]

    # M4 腾席(买入遇 bench 满:现场卖 1 燃料件,R8-8 单帧闭环)
    if missing and bench_free <= 0:
        cands = mandate.fuel_sell_candidates(bench, k_members, state=state)
        if cands:
            victim = cands[0]
            ok4, _ = mandate.check_irreversible(victim.char_id or '', k_members)
            if ok4:
                idx = (state.bench or []).index(victim)
                income = _shop_sell_refund(victim)
                out.append(mandate.Emitted(
                    SellBench(bench_idx=idx, income=income,
                                    expect=victim.char_id or ''),
                    True, 'm4_fuel_sell_for_m2'))
                sold_idxs.add(idx)
                bench_free += 1
                if income:
                    gold += income
                # P56 投影同步:卖出的活期件从 Σ活期退金投影扣减(帧首
                # 快照的重复计入会让买面金约束偏松——非保守方向,即时修正)
                liquid_refund -= sell_refund(1, bench_char_cost(victim))
                s_reserve = g_star - liquid_refund
        else:
            _count('m2_retry_exhausted')

    # M2 线成员买入(序 1/2 义务;[41]:义务不走息律门)
    for m in missing:
        if bench_free <= 0:
            _count('bench_full_buy_abandon')
            break
        shop_cands = sorted(
            (c for c in (state.shop or []) if (c.name or '') == m
             and id(c) not in used_cards),
            key=lambda c: (c.cost if c.cost else 3))
        if not shop_cands:
            continue
        card = shop_cands[0]
        cost = card.cost if card.cost else 3
        ok1, _ = mandate.check_affordable(gold, cost)
        if not ok1:
            continue            # 金不足侧:支付支撑通道在下方两臂段处理
        out.append(mandate.Emitted(BuyCard(card=card,
                                           reason='m2_line_member'),
                                   True, 'm2_line_member'))
        used_cards.add(id(card))
        gold -= cost
        bench_free -= 1
        bought_target = True

    # M2b 升星合并完成买入(实机复盘 g_20260904_054904 p2r1 候选②:
    # 千冶·刃 合并件 2g 在店被 owned 拒后无人买,同帧 36g 买经验=优先级
    # 倒置)。k_members 中已持 2 张同名同星 1★、无 2★ 成件,且第三张在店
    # affordable ⇒ 买入即合成 2★(游戏规则常数:三张合一,零新自由参数;
    # dd-032 先例 merge_completion_exempt 同款判读——完成价值在星级阶梯
    # [P20 e1→e2/P30 ①合成完备购置],评分维对它构造性零增量)。序位=
    # M2 缺口买入之后(体系激活边际 > 散件升星,P20 辖域)、dominance/M6
    # (1★ 囤积面)之前;义务通道不走息律门([41] 同 M2)。bench_free ≥ 1
    # = 买入硬前提(合成投影:买入触合并净席 -1,保守取买入时点可行)。
    for m in k_members:
        copies = [c for c in bench + deployed if (c.char_id or '') == m]
        if len(copies) != 2 or any((c.star or 1) >= 2 for c in copies):
            continue
        shop_cands = sorted(
            (c for c in (state.shop or []) if (c.name or '') == m
             and id(c) not in used_cards),
            key=lambda c: (c.cost if c.cost else 3))
        if not shop_cands:
            continue
        if bench_free <= 0:
            _count('merge_bench_full')
            continue
        card = shop_cands[0]
        cost = card.cost if card.cost else 3
        ok1, _ = mandate.check_affordable(gold, cost)
        if not ok1:
            continue
        out.append(mandate.Emitted(
            BuyCard(card=card, reason='m2_merge_completion'),
            True, 'm2_merge_completion'))
        used_cards.add(id(card))
        bought_names.append(card.name or '')
        gold -= cost
        bench_free -= 1
        bought_target = True

    # dominance_buy(M2 前置支配买入,mandate 邻位;P24 零参数,两臂同开。
    # 金口径=支出后投影金,R197 症9:同波 M4/M2 支出后 gold——存在性
    # 计数键触发面与后续 check_affordable 同基准;实际支出安全由
    # check_affordable(gold=投影金) 兜底,本改只正口径)
    # 判据契约核验(IMPL_DESIGN §4.2.2):S 预留辖域前提=目标线成型
    # (contracts.py 先例①),不成立 ⇒ 本帧弃权 + 违例计数
    _dom_ok = contracts.ensure_contract(
        ('mandate', 'dominance_buy'),
        contracts.ContractCtx(k_members=k_members), counters)
    if _dom_ok and mandate.dominance_buy_eligible(gold, bench_free,
                                                  stop_flag, cap_resolved):
        for card in (state.shop or []):
            if id(card) in used_cards:
                continue
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
            out.append(mandate.Emitted(BuyCard(card=card,
                                              reason='dominance_buy'),
                                       True, 'dominance_buy'))
            used_cards.add(id(card))
            gold -= cost
            bench_free -= 1

    # M3 升级整批(触发信号=arm1_existence;D-BUYNOTE:P48 整买纪律内嵌)。
    # cap 接线=state.max_units() 单点(等级+宝钻、封顶 10;cw_state 收口),
    # 非固定槽表常数——2026-09-03 零刷新诊断批定谳的域错位修复点。
    # 契约核验(IMPL_DESIGN §4.2.2):arm1 前提=cap 现读口径(contracts.py
    # 先例③,deploy_cap=None 退固定常数即违例;lv9/spend_unified 前提
    # 恒真(None 登记,显式辖域声明)
    _cap_now = state.max_units()
    _arm1_ok = contracts.ensure_contract(
        ('predicates', 'arm1_existence'),
        contracts.ContractCtx(deploy_cap=_cap_now), counters)
    if _arm1_ok and predicates.arm1_existence(len(deployed), bench_names,
                                              deployed_names, _cap_now):
        # 候选③危机带经验授权让位(与 mandate M3 同判据同计数键;
        # 判据单一源 = levelup.level_spend_blocked,见该函数注)。
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
                    for _i in range(clicks):
                        out.append(mandate.Emitted(
                            LevelUpShop(cost=cost, auth_basis='m3_batch'),
                            True, 'm3_levelup_batch'))
                    gold -= clicks * cost

    # M6 溢余转压库(存在性=金>g* ∧ 无 S 目标;金口径=支出后投影金,
    # R197 症9 同 dominance;档匹配 fail-closed ⇒ 不买 + 溢余滞留遥测;
    # 两臂同开——义务存在性不在旁路集,§4.2.1)
    if gold > g_star and stop_flag and bench_free > 0:
        ok2, _ = mandate.check_seats(
            bench_free, 0, needs_bench=True, needs_board=False,
            name='', deployed_names=deployed_names)
        if not ok2:
            _count('m6_bench_full')
        else:
            # 窗口 = 帧级现算(T1 后 T_SEARCH_A 门退役;空集=真无窗口帧,
            # 语义不变:不买 + 溢余滞留遥测)
            if not tier_w:
                _count('m6_overflow_strand')
            else:
                # 契约核验(§4.2.2):S 预留辖域前提=目标线成型(先例①),
                # 不成立 ⇒ 本帧弃权(不买)+违例计数,不溢余滞留误报
                _stock_ok = contracts.ensure_contract(
                    ('stockpile', 'stockpile_buy'),
                    contracts.ContractCtx(k_members=k_members), counters)
                for card in (state.shop or []):
                    if id(card) in used_cards:
                        continue
                    cost = card.cost if card.cost else 3
                    okm, _mkey = crit_stockpile.stockpile_buy(
                        gold, s_reserve, bench_free, cost,
                        card.star or 1, tier_w) if _stock_ok \
                        else (False, '')
                    if not okm:
                        # P56 拒因分键(R3-R5):s_reserve 拒买帧计数
                        if _mkey == 's_reserve':
                            _count('m6_s_reserve_reject')
                        continue
                    ok1, _ = mandate.check_affordable(gold, cost)
                    if not ok1:
                        continue
                    out.append(mandate.Emitted(
                        BuyCard(card=card, reason='m6_stockpile'),
                        True, 'm6_stockpile'))
                    used_cards.add(id(card))
                    bought_names.append(card.name or '')
                    gold -= cost
                    bench_free -= 1

    # ---- ④ EV pass(臂①旁路集=§4.2.1;仅 criteria 真 EV 发射面)----
    if not skeleton_only:
        # EV 买面(发射面一体,R7-1:候选生成+否决门)。契约核验
        # (§4.2.2):S 预留辖域前提=目标线成型(先例①),不成立 ⇒
        # 本帧弃权(不发候选)+违例计数——不落入 no_candidate 分键
        if contracts.ensure_contract(
                ('buy', 'ev_buy_candidates'),
                contracts.ContractCtx(k_members=k_members), counters):
            cands, ckey = crit_buy.ev_buy_candidates(
                gold, s_reserve, state.shop, k_members,
                level=int(state.level or 1), window=card_w,
                counters=counters)
            if ckey:
                _count(f'shop_ev_{ckey}')  # shop_domain / u_unavailable
            elif cands:
                emitted_ev = 0
                for cand in cands:
                    card = (state.shop or [])[cand.slot_idx] \
                        if cand.slot_idx < len(state.shop or []) else None
                    if card is None or id(card) in used_cards:
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
                    out.append(mandate.Emitted(
                        BuyCard(card=card, reason='ev_buy'), False, 'ev_buy'))
                    used_cards.add(id(card))
                    bought_names.append(card.name or '')
                    gold -= cand.cost
                    bench_free -= 1
                    emitted_ev += 1
                if emitted_ev == 0:
                    _count('shop_ev_all_vetoed')   # D-P2idle:「全拒」可辨
            else:
                _count('shop_ev_no_candidate')     # D-P2idle:「无候选」可辨
        # 付费刷新(r1 发射位)。V_GAP 槽位接线(2026-09-03 零刷新修复批,
        # ZERO_REFRESH_DIAG §4.1 实现缺口闭合):此前 EV 输入是字面量
        # None——标定注入后行为不变(开闸路径不可达)。现读
        # audit/provisional V_GAP(NMF §3.3 #2b;V̄ 系 R10-2 封印族恒 None,
        # 不入此门):槽位 None ⇒ 与旧实现逐字同 fail-closed 零刷新
        # (零漂移)。
        # R1 门形态(标定批落码,零刷新修复批登记欠账的闭合):有值 ⇒
        # **P40 R1 启动门总账**判据求值(c_eff·E[refreshes|j] + L ≤ V_gap,
        # k=1 单卡代表形态,判据本体=criteria/refresh.r1_commitment_account)
        # ——取代接线批的「有值即放行进 r2」过渡形态(该形态下刷新唯一
        # 约束是 r2 预算门,注入形态刷新量 ≈ 反事实 C 的 60+,EV 门无
        # 约束力,ZERO_REFRESH_FIX_REPORT §1 呈报项;diag §6.2 回归判据
        # 「0<refreshes≪60+」由本总账结构承载)。发射粒度=每商店波至多
        # 1 次刷新(RefreshShop 截断点),故总账逐波以现 state 重算——
        # 波边界=新的启动决策(j/gold 均已更新),期中续刷不建模
        # (sim 波粒度边界,如实申报)。
        from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
            provisional,
        )
        v_gap = provisional.get('V_GAP')
        # 契约核验(§4.2.2;FIX_REVIEW 防线硬化=可核验派生形态+R2 消费位
        # 补齐):r1 两形态各经本键核验,前提不采信硬编码声明而核验
        # ``ev_slot`` 运行类型(None=None 期 fail-closed / CalibValue=
        # 槽位现读;裸 float 字面量=复发形态违例)——
        # - None 期:r1_start(None) 逐字同旧实现零刷新(零漂移);
        # - 有值期:R1 门形态=P40 启动门总账(标定批落码,零刷新修复批
        #   登记欠账的闭合),判据本体=criteria/refresh.
        #   r1_commitment_account(k=1 单卡代表形态,装配=_r1_member_
        #   accounts)——取代接线批「有值即放行进 r2」过渡形态(该形态
        #   刷新量 ≈ 反事实 C 的 60+,EV 门无约束力,ZERO_REFRESH_FIX_
        #   REPORT §1 呈报项;diag §6.2 回归判据「0<refreshes≪60+」由
        #   本总账结构承载)。发射粒度=每商店波至多 1 次刷新(RefreshShop
        #   截断点),故总账逐波以现 state 重算——波边界=新的启动决策
        #   (j/gold 均已更新),期中续刷不建模(sim 波粒度边界,如实申报)。
        # r2 前提=金−预留语境(先例②,现读金与预留均在场)
        if v_gap is None:
            _r1_ok = contracts.ensure_contract(
                ('refresh', 'r1_start'),
                contracts.ContractCtx(ev_slot=None), counters)
            ok_r1, rkey = (crit_refresh.r1_start(None) if _r1_ok
                           else (False, 'contract_abstain'))
        else:
            _r1_ok = contracts.ensure_contract(
                ('refresh', 'r1_commitment_account'),
                contracts.ContractCtx(ev_slot=v_gap), counters)
            if _r1_ok:
                # 比较项 = V̄_net(r) 帧级现算(修 A 批;P53/
                # REFRESH_CFO_REPORT §6):rung 流 + 胜率流 × 决策帧
                # R_剩余(horizon.r_remaining,schedule_of 单一源)——
                # 取代「rung_value[2]×rounds_left_est=5 常数」静态链
                # (常数 5 低估被拦帧真实视界中位 12,512/512 拒刷的
                # 主因;零新自由参数,链与 calib_vuh_v1 同源)。V_GAP
                # 槽位保持 fail-closed 开闸通道语义(None ⇒ r1 闭),
                # 槽位数值不再是比较项(其带 [16.7,24.7] = 本链 r=5
                # 特例的历史标定带,披露用途)。registry 缺省兜底
                # DEFAULT_REGISTRY(与 entry 同先例;本链锚字段在两
                # 视图同值——sim 视图只覆写 level_max)。
                _reg = registry
                if _reg is None:
                    from sr_od.application.currency_war.kernel.cw_registry import (
                        DEFAULT_REGISTRY,
                    )
                    _reg = DEFAULT_REGISTRY
                _rounds = horizon.r_remaining(session, int(state.plane or 1),
                                              int(state.round_num or 1))
                ok_r1, rkey = crit_refresh.r1_commitment_account(
                    vbar.v_bar_net(_reg, _rounds, int(state.plane or 1)),
                    _r1_member_accounts(k_members, bench, deployed, state,
                                        session, rounds=_rounds))
            else:
                ok_r1, rkey = (False, 'contract_abstain')
        if not ok_r1:
            _count(f'shop_r1_{rkey}')      # ev_unavailable / account_over_vgap / no_chaseable_member
        elif contracts.ensure_contract(
                ('refresh', 'r2_budget'),
                contracts.ContractCtx(gold=gold, reserve=r2_reserve),
                counters):
            ok_r2 = crit_refresh.r2_budget(
                gold, r2_reserve,
                int(state.shop_refresh_cost or REFRESH_COST_BASE))
            if ok_r2:
                out.append(mandate.Emitted(
                    RefreshShop(cost=int(state.shop_refresh_cost
                                         or REFRESH_COST_BASE)),
                    False, 'r1_paid_refresh'))
        # 凑息卖·回拉发射位(T1 语义重写,设计 13_buy_face_design §2.2;
        # dd-026 姊妹缺口收口):金位触发(买/花后投影金 < g* 才发射)+
        # 目标量止盈(remaining 递减贪心,Σrefund ≥ 缺口即止,不多卖一张)
        # + T_SEARCH_A 布尔门退役——语义单一源 = criteria/sell.
        # sell_for_interest(函数 docstring);prefer_names = 刚买件(R2-N1
        # 发射约束,首卖刚买件连带损失=0)。分键遥测四字段在判据内随
        # counters 落键(R3-R5)。契约核验(§4.2.2):前提恒真(None 登记),
        # 违例路径仅剩未登记键
        if contracts.ensure_contract(
                ('sell', 'sell_for_interest'),
                contracts.ContractCtx(gold=gold), counters):
            _slots, skey = crit_sell.sell_for_interest(
                gold, bench, cap_resolved, k_members, state=state,
                prefer_names=tuple(bought_names), counters=counters)
        else:
            _slots, skey = [], 'contract_abstain'
        if not skey:
            for s in _slots:
                bc = next((b for b in bench if b.slot == s), None)
                idx = (state.bench or []).index(bc) if bc is not None else None
                if idx is None:
                    continue
                if idx in sold_idxs:
                    # 同槽冲突(R197 症3):M4 已卖槽先到先得,丢弃非重发
                    _count('ev_conflict_dropped')
                    continue
                income = _shop_sell_refund(bc) if bc else None
                out.append(mandate.Emitted(
                    SellBench(bench_idx=idx, income=income,
                                    expect=(bc.char_id or '') if bc else ''),
                    False, 'sell_for_interest'))
                sold_idxs.add(idx)
                bench_free += 1
                # 卖出回金入投影(症3 小账:与 M4 的 gold += income 对称,
                # 后续买面金投影不再保守偏低)
                if income:
                    gold += income
        # line_switch_sell:商店波无换线事件(k_switched 恒 False,判据
        # 本体 prep 侧消费)——零发射,非旁路缺位。
    # 支付支撑通道(两臂同开,R13-5):骨架义务动作金不足侧筹资变现
    if missing:
        # need 缺省 = 线成员注册表最低 cost(mandate.cheapest_member_cost
        # 单一源,R197 症6:字面量 3 删除——未注册名保守估 3 的先例在
        # 该函数内,注释即契约);店面有候选时按实际店价收敛
        mf = mandate.MandateFrame(
            gold=gold, level=state.level, bench=bench, deployed=deployed,
            # cap 真值源=max_units() 派生链(R4 统一:与 arm1 消费位/
            # entry 侧同链;本帧仅 cheapest_member_cost 消费 k_members,
            # cap 取同链保持单一真值源)
            deploy_cap=state.max_units(),
            node_type=state.node_type,
            stop_flag=stop_flag, k_members=k_members,
            round_num=getattr(state, 'round_num', 1))
        need = mandate.cheapest_member_cost(mf)
        for m in missing:
            shop_cands = [c for c in (state.shop or [])
                          if (c.name or '') == m and id(c) not in used_cards]
            if shop_cands:
                need = min(need, min(
                    (c.cost if c.cost else 3) for c in shop_cands))
                break
        # 契约核验(§4.2.2):前提恒真(None 登记);不成立 ⇒ 弃权+计数
        fslots, _fkey = crit_sell.funding_support_sell(
            gold, need, bench, k_members, state=state) if contracts.ensure_contract(
            ('sell', 'funding_support_sell'),
            contracts.ContractCtx(gold=gold), counters) else ([], '')
        for s in fslots:
            bc = next((b for b in bench if b.slot == s), None)
            idx = (state.bench or []).index(bc) if bc is not None else None
            if idx is None:
                continue
            if idx in sold_idxs:
                # 同槽冲突(R197 症3):M4/sell_for_interest 已卖槽先到先得,
                # 丢弃非重发(第二笔执行必 fail-stop,契约 §2)
                _count('ev_conflict_dropped')
                continue
            out.append(mandate.Emitted(
                SellBench(bench_idx=idx,
                                income=_shop_sell_refund(bc) if bc else None,
                                expect=(bc.char_id or '') if bc else ''),
                False, 'funding_support', funding_support=True))
            sold_idxs.add(idx)

    # ---- D-A45 商店侧半边:买入目标件 ⇒ 干旱计数器重置 ----
    if bought_target:
        ls = getattr(session, 'cw4_line_state', None)
        if ls is not None:
            ls.drought = 0
        _count('shop_drought_reset_on_buy')

    # ---- D-D 硬节点补强门消费(观察级接线;数值加权挂标定批)----
    # 契约核验(§4.2.2):前提恒真(None 登记);不成立 ⇒ 弃权+计数
    _gate_open, _gkey = crit_refresh.hard_node_reinforce_gate(
        state.node_type, int(state.gold or 0), g_star) \
        if contracts.ensure_contract(
            ('refresh', 'hard_node_reinforce_gate'),
            contracts.ContractCtx(gold=int(state.gold or 0)), counters) \
        else (False, '')
    if _gate_open:
        _count('shop_hard_node_gate_open')

    # ---- D-P2idle:带金零动作波计数(「无候选 vs 全拒」由分键承载)----
    if not out and int(state.gold or 0) >= 10:
        _count('shop_wave_idle_gold')

    actions: list[Action] = [e.action for e in out]
    actions = truncate_shop_frame_stable(actions, state, session)
    # 拒因遥测(截断后口径:被截断器丢弃的买 = missing_no_path,可辨):
    # session 汇点(recorder 固定尾巴按 w603 先例自取),sim/实机同源。
    session.cw4_shop_rejects = shop_unbought_reasons(
        state, k, k_members, actions)
    return actions

