"""criteria/sell——EV 卖面(§2.2;fuel_sell/protected_sell 在 mandate/谓词层)。

三个发射/通道位:line_switch_sell(换线塌缩出口)、sell_for_interest
(凑息档 EV 面,臂①旁路)、funding_support_sell(支付能力变现子域,
R13-5 支付支撑通道,两臂同开、mandate=false+funding_support=true)。

fail 方向(§2.2.1 唯一权威规格):不可逆卖面缺输入(λ 表损坏/域外/
第四态无载/sell_refund 损坏)⇒ 不评不卖;u/V_ms🔴 ⇒ line_switch_sell
比较臂无载 ⇒ 不卖 + 出口确定性关闭(proof.should_switch 前置门同构)。
凑息卖自 T1 语义重写批(设计 13_buy_face_design §2.2)起 = 回拉发射位
(金位触发+目标量止盈,函数 docstring 单一源),无 fail-closed 输入面。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_state import (
    bench_char_cost,
    count_merge_material_blocked,
    merge_material_reject_reason,
    sell_refund,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import provisional
from sr_od.application.currency_war.strategies.impl.mandate_v1.sell_gate import (
    EMPTY_BOARD_SELL_GUARD_KEY,
    empty_board_sell_blocked,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    refund_full_star_ok,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_board_state import (
        BoardState,
    )
    from sr_od.application.currency_war.kernel.cw_state import BenchChar, GameState


def line_switch_sell(old_line_members: tuple[str, ...],
                     new_line_members: tuple[str, ...],
                     bench: list[BenchChar], deployed: list[BenchChar],
                     bs: BoardState | GameState, *, k_switched: bool,
                     counters: dict | None = None,
                     dedup_names: set[str] | None = None,
                     ) -> tuple[list[int], str]:
    """换线塌缩出口(§2.2 主比较式的发射位;k_switched=K 已按 K′ 更新)。

    载体 = 容器 bs(prep 链容器化段 1:prep 位直传 bs;双形态注解 =
    双形态读支与存量直调/测试面兼容,GameState 支随段 2/波 5 消亡)。

    返回 (拟卖 bench slot 列表, 归因键)。发射前置:
    - K 未切换 ⇒ 无对象(空,'no_event');
    - u/V_ms【拟】None(全🔴延迟态,§2.2.1 第 4 行)⇒ 不卖 +
      'switchline_exit_blocked'(塌缩出口整体延迟至标定后);
    - 候选 = 旧线成员 ∧ 非新线成员 ∧ protected_sell 恒不卖对象排除
      (骨架/贯穿件 = 新旧线交集成员保留)。
    比较式本体(V_opt/V_power 全式)消费 u/V_ms 数值——全式未落位期
    (含 U_X/V_MS 注入态)返回**保守子集而非全集**(IMPL_ADV_R200 症5③
    「全堵→全卖」悬崖修):保守子集 = 燃料类件(1★ ∧ sell_refund 全额
    可退,``refund_full_star_ok``)——依据=p41-hoard-sell-ev 燃料类支配性
    论证(零重叠∧1★全额退 ⇒ 卖出净成本=0,卖错代价≈0);2★+/部分退
    件卖错损失不可逆(手续费+V_opt 再遇账),注入态无全式比较 ⇒ 保守
    保留至 vopt 全式落位。全式接线后本子集语义由比较式取代。

    合成素材拒入守卫(G-S1):保守子集候选若与场上(bench∪deployed)
    另有同名同星副本(2/3 合成进度素材),拒因键 ``merge_material_
    guard``(单一源 = ``cw_state.merge_material_reject_reason``,与
    部署侧同键)拒入塌缩对象集——换线不构成素材豁免(素材对换线后
    板面仍可能是素材)。设计出处:ADR-0558。
    拒因分键接线(D1 整改,ADR-0558 §3「全发射位显影」兑现:本通道
    曾静默 continue 无计数,接线枚举也不含本位):``counters`` 非 None
    时计数 ``merge_material_guard_blocked``;计数 = 事件口径(C1,同帧
    同名只计 1,去重载体 = ``dedup_names``,单一源 =
    ``cw_state.count_merge_material_blocked``,与 M4 燃料/凑息/支付
    变现同键同口径分账)。

    T3 同轮保留结构无关声明:本通道候选集 ⊂ 旧线成员,同轮保留集
    (垫件)零重叠永不在旧线 ⇒ 无交互,本函数不设 defer 参数——
    形式化声明防后人误加;若未来候选域扩到线外件,须先补 defer 接线。
    """
    if not k_switched:
        return [], 'no_event'
    if provisional.is_none('U_X') or provisional.is_none('V_MS'):
        return [], 'switchline_exit_blocked'
    # 空板止损守卫(T-32;单一源 = sell_gate.empty_board_sell_blocked):
    # 板空帧不塌缩清算,孤儿件留 bench 下帧再评(损失 = 清算延迟,非自旋)。
    # deployed 双形态读(prep 链容器化段 1:prep 位传容器 bs;与
    # funding_support_sell 守卫同式,GameState 支随段 2/波 5 消亡)。
    from sr_od.application.currency_war.kernel.cw_board_state import (
        BoardState,
        deployed_slots_of,
    )
    _deployed = deployed_slots_of(bs) if isinstance(bs, BoardState) \
        else bs.deployed
    if empty_board_sell_blocked(_deployed, counters=counters):
        return [], EMPTY_BOARD_SELL_GUARD_KEY
    out: list[int] = []
    for b in bench:
        name = b.char_id or ''
        if name in old_line_members and name not in new_line_members:
            # 注入态保守子集:仅燃料类(1★ 全额可退)放行,其余保留
            if not refund_full_star_ok(b.star, bench_char_cost(b)):
                continue
            if merge_material_reject_reason(name, b.star, bench, deployed):
                if counters is not None:
                    count_merge_material_blocked(counters, name, dedup_names)
                continue
            out.append(b.slot)
    return out, ''


def sell_for_interest(gold: int, bench: list[BenchChar],
                      cap_resolved: int,
                      k_members: tuple[str, ...],
                      state: object | None = None,
                      *,
                      prefer_names: tuple[str, ...] = (),
                      counters: dict | None = None,
                      exclude_names: frozenset[str] | set[str] = frozenset(),
                      defer_names: frozenset[str] | set[str] = frozenset(),
                      dedup_names: set[str] | None = None,
                      ) -> tuple[list[int], str]:
    """凑息卖·回拉发射位(T1 语义重写;设计 13_buy_face_design §2.2)。

    语义重写三项(R2-N4,取代旧「T_SEARCH_A 注入态资格全集无差别全发」):
    ① **金位触发(缺口驱动)**:买/花后投影金 ``gold`` < 息线
       g* = saturation_line(cap_resolved) 才发射,缺口 = g* − gold;
       非缺口帧零发射(返回 'not_needed',与 funding_support 触发形态同构);
    ② **目标量止盈**:remaining 递减贪心(funding_support ``remaining``
       模板同构移植,零待证依赖;任意确定序贪心都能卖够,序只影响效率
       ——p49 ⑤ 每金序/[11] 最小化为效率升级项,非本位前件),
       Σrefund ≥ 缺口即止,不多卖一张;
    ③ **槽位布尔门退役**:T_SEARCH_A 裸布尔检查退出本消费位(窗口数值
       链归 P57 裁决,与本重写分账)。

    资格谓词不变(占位件物理门 ∧ 1★ ∧ 零重叠 ∧ 无后台效果,与
    funding_support_sell 同一;占位件恒拒判据单一源 =
    ``predicates.item_slot_unsellable`` 跨通道共享谓词,与 M4 燃料通道
    同门——占席物品不可卖且无金币现值,空名 1★ 禁穿透资格循环;
    语境经 ``predicates.bench_effect_context`` 共享装配现读——症3 三通道
    统一,``state=None`` 按装配缺省保守端处置)。序:``prefer_names``
    (刚买件名集合,R2-N1 发射约束:首卖刚买件使连带卖出损失=0;帧投影
    架构下刚买件尚未入 bench,按名匹配同资格在册件)优先,其余按
    (star, slot) 升序(funding_support 同款序)。

    分键遥测(R3-R5 四字段,设计 §3.2;counters=None 时不记):
    ``t1_interest_emit_frames``(发射帧数)/``t1_interest_gap_total``(缺口
    累计)与 ``t1_interest_sellback_total``(实际卖回累计,两者之比=覆盖
    缺口率)/``t1_pullback_gold_ge_gstar``(回拉后投影金 ≥ g* 帧数=金位
    轨迹)。

    凑息禁令(血线硬地板解锁包件②,≤15 族在册授权):死亡线帧不凑息
    ——金不卖回,当轮转化优先(14号稿 §5.4 Y7 口径);返回
    ([], 'blood_floor') 零静默分键。state=None = 语境缺失,禁令按保守端
    照禁(fail-closed:禁令是授权约束,缺读不构成豁免)。P2 半边 =
    p2_blood_floor_unlock 合成(设计出处 = p2_blood_band_unified_design/
    DESIGN.md §2.1 凑息禁令直移植,裁定条目 = 241 §15.2 覆①消费让位;
    授权闩 False 期间恒不触发,P2 帧凑息行为零变更),拒因键
    'p2_blood_floor' 与 P1 域 'blood_floor' 分键禁并(键族零交集,
    统一设计稿 §4-8)。

    合成素材拒入守卫(G-S1,ADR-0558):候选与场上(state.deployed ∪ bench,含
    自身)另有同名同星副本 ⇒ 2/3 合成进度素材,拒因键
    ``merge_material_guard``(单一源 = ``cw_state.merge_material_
    reject_reason``,与部署侧同键)拒入资格集;拒因同键计数
    ``merge_material_guard_blocked``(与 M4 燃料/支付变现/换线同键
    分账;事件口径 C1:同帧同名只计 1,去重载体 = ``dedup_names``)。

    ``defer_names``(T3 同轮保留;凑息回拉通道 = **绝对跳过**,非降序):
    集合内名字整体退出卖出资格集(分键 ``t3_protect_deferred``,零静默)
    ——机理 = T5 门槛7 不等式:买后缺口 gap ≤ 决策帧可变现件退金总和
    (被保垫件 1★ 全额可退,卖谁都净零,跳过后改卖其他 liquid 照常闭合
    缺口,回拉功能零损失;边界申报:同轮多笔被保买入帧,前笔被保件在
    买入帧 s_reserve 投影内时缺口闭合可能不足——失败形态 = 金留 g* 之下
    真实持有,非自旋,经 t1_interest_gap/sellback 差值可判读)。与
    G-S1 不冲突:被保件同时是素材时双守卫各拒各的(保护只影响排序/跳过,
    不影响资格闭集)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        p1_blood_floor,
        p2_blood_floor_unlock,
    )
    if state is None or p1_blood_floor(state):
        return [], 'blood_floor'
    if p2_blood_floor_unlock(state):
        return [], 'p2_blood_floor'
    # 空板止损守卫(T-32;单一源 = sell_gate.empty_board_sell_blocked):
    # 板空帧卖储备换金 = 期权损失换零净金(1★ 全额退),弱劣拒帧。
    # deployed 双形态读(W6 波 4:商店线传容器 bs;存量面传帧)
    from sr_od.application.currency_war.kernel.cw_board_state import (
        BoardState,
        deployed_slots_of,
    )
    _deployed = deployed_slots_of(state) if isinstance(state, BoardState) \
        else state.deployed
    if empty_board_sell_blocked(_deployed, counters=counters):
        return [], EMPTY_BOARD_SELL_GUARD_KEY
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
        saturation_line,
    )
    g_star = saturation_line(cap_resolved)
    gap = g_star - int(gold or 0)
    if gap <= 0:
        return [], 'not_needed'

    def _count(key: str, n: int = 1) -> None:
        if counters is not None:
            counters[key] = counters.get(key, 0) + n

    _deployed = list(getattr(state, 'deployed', None) or [])
    qualified: list[BenchChar] = []
    for b in bench:
        # 占位件物理门(先于其余资格门短路):占席物品不可卖、无金币
        # 现值,判据单一源 = predicates.item_slot_unsellable(跨通道共享
        # 谓词,与 M4 燃料/支付变现同门,禁内联复制)。
        if predicates.item_slot_unsellable(b):
            continue
        name = b.char_id or ''
        if b.star != 1:
            continue
        if not predicates.zero_overlap(name, k_members):
            continue
        if name in exclude_names:
            continue   # P60:买面义务集成员禁入卖出资格集(防义务换手)
        if name in defer_names:
            _count('t3_protect_deferred')   # T3 同轮保留:回拉通道绝对跳过
            continue
        if merge_material_reject_reason(name, b.star, bench, _deployed):
            if counters is not None:
                count_merge_material_blocked(counters, name, dedup_names)
            continue
        if predicates.bench_effect_qualified(
                name, predicates.bench_effect_context(state, b, k_members)):
            continue
        qualified.append(b)
    # 序:刚买件优先(R2-N1),其余 (star, slot) 升序(确定性)
    prefer = set(prefer_names)
    qualified.sort(key=lambda b: (0 if (b.char_id or '') in prefer else 1,
                                  b.star, b.slot))
    out: list[int] = []
    remaining = gap
    sellback = 0
    for b in qualified:
        out.append(b.slot)
        # 1★ 卖回净额 = sell_refund(1, 注册表 cost)(与 funding_support
        # 同款:bench_char_cost 未知名保守估 3,禁字面量双源)
        refund = sell_refund(1, bench_char_cost(b))
        remaining -= refund
        sellback += refund
        if remaining <= 0:
            break
    _count('t1_interest_emit_frames')
    _count('t1_interest_gap_total', gap)
    _count('t1_interest_sellback_total', sellback)
    if sellback >= gap:
        _count('t1_pullback_gold_ge_gstar')
    return out, ''


def funding_support_sell(gold: int, need_gold: int, bench: list[BenchChar],
                         k_members: tuple[str, ...],
                         state: BoardState | GameState | None = None,
                         *,
                         exclude_names: frozenset[str] | set[str] = frozenset(),
                         defer_names: frozenset[str] | set[str] = frozenset(),
                         counters: dict | None = None,
                         dedup_names: set[str] | None = None,
                         ) -> tuple[list[int], str]:
    """「支付能力变现」子域(R13-5/R14-4:支付支撑通道,两臂同开)。

    载体注解显式化(prep 链容器化段 1:prep 位直传 bs;商店线波 4 已
    传 bs;``None`` = 旧调用面/手工帧兼容形态)。

    触发 = 骨架义务动作金不足(gold < need_gold,硬约束①不满足侧的
    筹资面);变现对象 = 凑息档序同资格(占位件物理门 ∧ 1★ ∧ 无后台
    效果 ∧ 零重叠,占位件判据单一源 = ``predicates.item_slot_
    unsellable`` 跨通道共享谓词,与 M4 燃料/凑息同门——空名 1★ 禁
    穿透资格循环;语境经 ``predicates.bench_effect_context`` 共享装配
    现读——症3 三通道统一;卖回量最小化 [11]);跨帧语义 = 变现金
    作用于下一备战期义务动作(延迟=1 备战期间隔,进遥测 reason)。
    无对象 ⇒ 空。
    ``exclude_names`` = 买面义务集成员禁入(P60,与凑息卖/M4 燃料同款)。
    ``defer_names``(T3 同轮保留;支付变现 = 转化类,**仅降序放行**,
    非绝对禁卖):集合内名字排候选末位——为骨架义务筹资的卖出优先级
    支配保护(保护若辖此通道 = 安全域内抑制发展动作的回归);非保
    燃料在场时先卖非保件,被保件仅兜底消费。defer 空集时排序键逐位
    等价旧 (star, slot) 序(零漂移)。

    合成素材拒入守卫(G-S1,ADR-0558):候选与场上(state.deployed ∪ bench,含
    自身)另有同名同星副本 ⇒ 2/3 合成进度素材,拒因键
    ``merge_material_guard``(单一源 = ``cw_state.merge_material_
    reject_reason``,与部署侧同键)拒入资格集;``counters`` 非 None
    时同键计数 ``merge_material_guard_blocked``(事件口径 C1:同帧同
    名只计 1,去重载体 = ``dedup_names``,单一源 =
    ``cw_state.count_merge_material_blocked``)。
    """
    if gold >= need_gold:
        return [], 'not_needed'
    # 空板止损守卫(T-32;单一源 = sell_gate.empty_board_sell_blocked):
    # 板空帧筹资卖出同弱劣拒帧(收益侧=义务在 bench 域,守卫不评收益
    # 只钉卖出腿;恢复正路 = 部署与买面,不在卖出通道)。state 缺读 =
    # fail-closed 拒(资格判据禁缺读放行)。
    # deployed 双形态读(W6 波 4:商店线传容器 bs;存量面传帧)——
    # 与 sell_for_interest 守卫同式。
    from sr_od.application.currency_war.kernel.cw_board_state import (
        BoardState,
        deployed_slots_of,
    )
    _deployed = deployed_slots_of(state) if isinstance(state, BoardState) \
        else getattr(state, 'deployed', None)
    if empty_board_sell_blocked(_deployed,
                                counters=counters):
        return [], EMPTY_BOARD_SELL_GUARD_KEY
    out: list[int] = []
    remaining = need_gold - gold
    _deployed = list(_deployed or [])   # 双形态读复用(守卫位已按容器/帧解析)
    # T3 末位牺牲序:被保件稳定移尾(转化类放行,非禁卖)
    for b in sorted(bench, key=lambda x: ((x.char_id or '') in defer_names,
                                          x.star, x.slot)):
        # 占位件物理门(先于其余资格门短路):占席物品不可卖、无金币
        # 现值,判据单一源 = predicates.item_slot_unsellable(跨通道共享
        # 谓词,与 M4 燃料/凑息同门,禁内联复制)。
        if predicates.item_slot_unsellable(b):
            continue
        name = b.char_id or ''
        if b.star != 1:
            continue
        if not predicates.zero_overlap(name, k_members):
            continue
        if name in exclude_names:
            continue   # P60:买面义务集成员禁入卖出资格集
        if merge_material_reject_reason(name, b.star, bench, _deployed):
            if counters is not None:
                count_merge_material_blocked(counters, name, dedup_names)
            continue
        if predicates.bench_effect_qualified(
                name, predicates.bench_effect_context(state, b, k_members)):
            continue
        out.append(b.slot)
        # 1★ 卖回净额 = sell_refund(1, 注册表 cost) 派生(R196 症6:
        # 禁字面量 3 双源——bench_char_cost 未知名保守估 3 与旧值同构)
        remaining -= sell_refund(1, bench_char_cost(b))
        if remaining <= 0:
            break
    return out, ''
