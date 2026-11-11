"""criteria/sell——EV 卖面(§2.2;fuel_sell/protected_sell 在 mandate/谓词层)。

两个动作发出/通道位:sell_for_interest(凑利息档 EV 面,分支①旁路)、
funding_support_sell(支付能力变现子域,R13-5 支付支撑通道,两分支同开、
mandate=false+funding_support=true)。换线清仓出口(line_switch_sell)
已删除(候选-锁定制:锁定为一次性决策,无换目标后的清场需求——
停用面申报,git 历史可溯;V_MS 槽随函数删除撤槽)。

fail 方向(§2.2.1 唯一权威规格):不可逆卖面缺输入(λ 表损坏/域外/
第四态无载/sell_refund 损坏)⇒ 不评不卖。凑息卖(T1 语义重写)
= 回拉动作发出点(金位触发+目标量止盈,
函数 docstring 单一源),无 fail-closed 输入面。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_economy import (
    bench_char_cost,
    next_interest_line,
    sell_refund,
)
from sr_od.application.currency_war.kernel.cw_exec_state import bench_slot_unit
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    count_merge_material_blocked,
    merge_material_reject_reason,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.sell_gate import (
    EMPTY_BOARD_SELL_GUARD_KEY,
    empty_board_sell_blocked,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        GameState,
        Unit,
    )


def _slot_of(b: object, idx: int | None = None) -> int:
    """占席条目 → 卖出候选位键(紧缩序下标;Unit.slot 仅作信息位,
    候选键 = 条目在紧缩占席序(物理槽序)中的 0 基下标,
    发出侧经状态容器槽位表枚举对位还原;``idx`` 显式传位,P4 状态容器形解包
    单一读点,本模块三通道共用)。"""
    return int(idx if idx is not None else 0)


def _star_of(b: object) -> int:
    """占席条目 → 星级(占位件缺省 1,资格门先拒,值不被消费)。"""
    u = bench_slot_unit(b)
    return int(getattr(u, 'star', 1) or 1) if u is not None else 1


def _cid_of(b: object) -> str:
    """占席条目 → 身份名(占位件 = '')。"""
    u = bench_slot_unit(b)
    return (getattr(u, 'char_id', '') or '') if u is not None else ''


def _deployed_units_of(state: GameState) -> list[Unit]:
    """场上单位域现读(行域紧缩;守卫/素材计数全场域共用同一次解析)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        deployed_rows_of,
    )
    front, back = deployed_rows_of(state)
    return [d for d in (*front, *back) if d is not None]


def sell_for_interest(gold: int, bench: list[BenchSlot],
                      cap_resolved: int,
                      k_members: tuple[str, ...],
                      state: GameState,
                      *,
                      prefer_names: tuple[str, ...] = (),
                      counters: dict | None = None,
                      exclude_names: frozenset[str] | set[str] = frozenset(),
                      defer_names: frozenset[str] | set[str] = frozenset(),
                      merge_guard_release: frozenset[str] | set[str] = frozenset(),
                      dedup_names: set[str] | None = None,
                      ) -> tuple[list[int], str]:
    """凑息卖·回拉动作发出点(11 号稿 §4.0 场景表 node_end_interest 行)。

    语义(R2-N4,取代旧「T_SEARCH_A 注入态资格全集无差别全发」):
    ① **金位触发(下一利息档缺口驱动)**:当前金未达下一利息档线
       (单一源 = kernel ``next_interest_line``;已达满档/买断制 =
       None)才评资格,缺口 = 档线 − 当前金;档线之上零发出(返回
       'not_needed',与 funding_support 触发形态同构);
    ② **跨档止盈(卖回量最小化 [11] 的严格语义)**:只有「单件退金
       ≥ 缺口」的候选才可卖——跨不了档的卖出零利息收益、纯亏持有
       资产,一件不卖(拒因 'no_tier_gain');可行件取**退金最小**的
       一张(逐帧单张模型:跨档后下帧按新金位重评,缺口重算自然
       收敛,不一次多卖);
    ③ **槽位布尔门停用**:T_SEARCH_A 裸布尔检查退出本消费位(窗口数值
       链归 P57 裁决,与本重写分账)。

    资格谓词(占位件物理门 ∧ 1★ ∧ 零重叠,与
    funding_support_sell 同一;占位件恒拒判据单一源 =
    ``predicates.item_slot_unsellable`` 跨通道共享谓词,与 M4 燃料通道
    同门——占席物品不可卖且无金币现值,空名 1★ 禁穿透资格循环)。
    「无后台效果」资格维已随旧评估器退役删除(统一让位优先级迭代
    3.4:bench_effect_qualified 消费位拆除,该维度归统一序列档 9)。
    序:``prefer_names``
    (刚买件名集合,R2-N1 发出约束:首卖刚买件使连带卖出损失=0;帧级逻辑态
    架构下刚买件尚未入 bench,按名匹配同资格已登记件)优先,其余按
    (star, slot) 升序(funding_support 同款序)。

    分键遥测(R3-R5 四字段,设计 §3.2;counters=None 时不记):
    ``t1_interest_emit_frames``(动作发出帧数)/``t1_interest_gap_total``(到
    下一利息档缺口累计)与 ``t1_interest_sellback_total``(实际卖回累计,
    两者之比=覆盖缺口率)/``t1_pullback_gold_ge_gstar``(本张卖出即闭合
    缺口〔跨档〕帧数——跨档止盈下发出即闭合,键名保留 g* 字样 =
    历史遥测兼容,语义按本行)。

    凑息禁令(血线硬地板解锁包件②)已删除(11 号稿 §2 拦截层
    血线地板解锁行——唯一消费方 = 已废止的血线解锁;正典依据
    口述条目 39(登记簿已退役)「HP 不作决策依据」,濒死响应 = 修经济/阵容
    本身,凑息卖回不受血线覆盖)。

    合成素材拒入守卫(G-S1):候选与场上(state.deployed ∪ bench,含
    自身)另有同名同星副本 ⇒ 2/3 合成进度素材,拒因键
    ``merge_material_guard``(单一源 = ``cw_state.merge_material_
    reject_reason``,与部署侧同键)拒入资格集;拒因同键计数
    ``merge_material_guard_blocked``(与 M4 燃料/支付变现/换线同键
    分账;事件口径 C1:同帧同名只计 1,去重载体 = ``dedup_names``)。

    ``defer_names``(T3 同轮保留;凑息回拉通道 = **绝对跳过**,非降序):
    集合内名字整体退出卖出资格集(分键 ``t3_protect_deferred``,零静默)
    ——被保垫件 1★ 全额可退卖谁都净零,跳过零损失;其余候选按跨档
    止盈判据独立评估,凑不齐缺口即零发出(失败形态 = 金留档内真实
    持有,非自旋,经 t1_interest_gap/sellback 差值可判读)。与
    G-S1 不冲突:被保件同时是素材时双守卫各拒各的(保护只影响排序/跳过,
    不影响资格闭集)。

    ``merge_guard_release``(缺省空集 = 零漂移端):死库存素材对
    释放集,G-S1 判据处的条件旁路(命中 ⇒ 跳过拒入、不计数;单一源 =
    sell_gate.dead_pair_exit_release,消费位禁自算)。凑息通道消费释放
    成员 = 卖掉意图已死的近零值资产,正是燃料类语义(P78-5′ 对价豁免
    条款照常覆盖,无新增豁免需求)。
    """
    # 空板止损守卫(单一源 = sell_gate.empty_board_sell_blocked):
    # 板空帧卖储备换金 = 期权损失换零净金(1★ 全额退),弱劣拒帧。
    # deployed 读 = 状态容器行域单一源(守卫与资格循环两处共用同一次
    # 解析,禁双形态各读半份)。
    _deployed = _deployed_units_of(state)
    if empty_board_sell_blocked(_deployed, counters=counters):
        return [], EMPTY_BOARD_SELL_GUARD_KEY
    _line = next_interest_line(int(gold or 0), cap_resolved)
    if _line is None:
        return [], 'not_needed'
    gap = _line - int(gold or 0)
    if gap <= 0:
        return [], 'not_needed'

    def _count(key: str, n: int = 1) -> None:
        if counters is not None:
            counters[key] = counters.get(key, 0) + n

    qualified: list[tuple[int, BenchSlot]] = []
    for i, b in enumerate(bench):
        # 占位件物理门(先于其余资格门短路):占席物品不可卖、无金币
        # 现值,判据单一源 = predicates.item_slot_unsellable(跨通道共享
        # 谓词,与 M4 燃料/支付变现同门,禁内联复制)。
        if predicates.item_slot_unsellable(b):
            continue
        name = _cid_of(b)
        star = _star_of(b)
        if star != 1:
            continue
        if not predicates.zero_overlap(name, k_members):
            continue
        if name in exclude_names:
            continue   # P60:买面义务集成员禁入卖出资格集(防义务换手)
        if name in defer_names:
            _count('t3_protect_deferred')   # T3 同轮保留:回拉通道绝对跳过
            continue
        if merge_material_reject_reason(name, star, bench, _deployed) \
                and name not in merge_guard_release:
            if counters is not None:
                count_merge_material_blocked(counters, name, dedup_names)
            continue
        # (挂后台效果资格门已随旧评估器退役删除——统一让位优先级迭代
        # 3.4:bench_effect_qualified 四消费位的凑息档序处拆除,该维度
        # 由统一序列档 9 判定承载,判定表权威版本 =
        # strategy-docs/32_unified_sell_priority.md §3。)
        qualified.append((i, b))
    # 序:刚买件优先(R2-N1),其余 (star,紧缩位) 升序(确定性;紧缩序
    # = 物理槽序,与旧 (star, slot) 逐位等价)
    prefer = set(prefer_names)
    qualified.sort(key=lambda ib: (0 if _cid_of(ib[1]) in prefer else 1,
                                   _star_of(ib[1]), ib[0]))
    # 跨档止盈(数量判据,非资格):单件退金 ≥ 缺口才卖,取退金最小的
    # 一张(并列取紧缩位靠前 = 资格序稳定);无可行件 = 跨不了档的卖出
    # 零利息收益纯亏资产,一件不卖('no_tier_gain',消费位按非空拒因
    # 跳过路径处置)。资格集空 = 无候选诚实空集,拒因保持 ''(原语义,
    # 与「有候选凑不出档」分键)。
    if not qualified:
        return [], ''
    feasible: list[tuple[int, int]] = []
    for i, b in qualified:
        refund = sell_refund(1, bench_char_cost(bench_slot_unit(b)))
        if refund >= gap:
            feasible.append((refund, i))
    if not feasible:
        return [], 'no_tier_gain'
    sellback, best_idx = min(feasible)
    out = [best_idx]
    _count('t1_interest_emit_frames')
    _count('t1_interest_gap_total', gap)
    _count('t1_interest_sellback_total', sellback)
    if sellback >= gap:
        _count('t1_pullback_gold_ge_gstar')
    return out, ''


def funding_support_sell(gold: int, need_gold: int, bench: list[BenchSlot],
                         k_members: tuple[str, ...],
                         state: GameState,
                         *,
                         exclude_names: frozenset[str] | set[str] = frozenset(),
                         defer_names: frozenset[str] | set[str] = frozenset(),
                         merge_guard_release: frozenset[str] | set[str] = frozenset(),
                         counters: dict | None = None,
                         dedup_names: set[str] | None = None,
                         ) -> tuple[list[int], str]:
    """「支付能力变现」子域(R13-5/R14-4:支付支撑通道,两分支同开)。

    载体 = 状态容器 gs 单形态(prep 链结构化段 2;prep 位/商店线消费恒直传
    gs)。

    触发 = 骨架义务动作金不足(gold < need_gold,硬约束①不满足侧的
    筹资面);变现对象 = 凑利息档序同资格(占位件物理门 ∧ 1★ ∧
    零重叠,占位件判据单一源 = ``predicates.item_slot_
    unsellable`` 跨通道共享谓词,与 M4 燃料/凑息同门——空名 1★ 禁
    穿透资格循环;「无后台效果」资格维已随旧评估器退役删除——统一
    让位优先级迭代 3.4:bench_effect_qualified 消费位拆除,该维度归
    统一序列档 9;卖回量最小化 [11]);跨帧语义 = 变现金
    作用于下一备战期义务动作(延迟=1 备战期间隔,进遥测 reason)。
    无对象 ⇒ 空。
    ``exclude_names`` = 买面义务集成员禁入(P60,与凑息卖/M4 燃料同款)。
    ``defer_names``(T3 同轮保留;支付变现 = 转化类,**仅降序放行**,
    非绝对禁卖):集合内名字排候选末位——为骨架义务筹资的卖出优先级
    支配保护(保护若覆盖此通道 = 安全域内抑制发展动作的回归);非保
    燃料在场时先卖非保件,被保件仅兜底消费。defer 空集时排序键逐位
    等价旧 (star, slot) 序(零漂移)。

    合成素材拒入守卫(G-S1):候选与场上(state.deployed ∪ bench,含
    自身)另有同名同星副本 ⇒ 2/3 合成进度素材,拒因键
    ``merge_material_guard``(单一源 = ``cw_state.merge_material_
    reject_reason``,与部署侧同键)拒入资格集;``counters`` 非 None
    时同键计数 ``merge_material_guard_blocked``(事件口径 C1:同帧同
    名只计 1,去重载体 = ``dedup_names``,单一源 =
    ``cw_state.count_merge_material_blocked``)。

    ``merge_guard_release``(缺省空集 = 零漂移端):死库存素材对
    释放集,G-S1 判据处的条件旁路(命中 ⇒ 跳过拒入、不计数;单一源 =
    sell_gate.dead_pair_exit_release,消费位禁自算)。支付变现消费释放
    成员的对价豁免条款(P78-5/5′ 两条分支)照常覆盖,无新增豁免需求。
    """
    if gold >= need_gold:
        return [], 'not_needed'
    # 空板止损守卫(单一源 = sell_gate.empty_board_sell_blocked):
    # 板空帧筹资卖出同弱劣拒帧(收益侧=义务在 bench 域,守卫不评收益
    # 只钉卖出分支;恢复正路 = 部署与买面,不在卖出通道)。
    # deployed 读 = 状态容器行域单一源。
    _deployed = _deployed_units_of(state)
    if empty_board_sell_blocked(_deployed,
                                counters=counters):
        return [], EMPTY_BOARD_SELL_GUARD_KEY
    out: list[int] = []
    remaining = need_gold - gold
    # T3 末位牺牲序:被保件稳定移尾(转化类放行,非禁卖);位键 = 紧缩
    # 序下标(物理槽序,与旧 (star, slot) 序逐位等价)
    for i, b in sorted(enumerate(bench),
                       key=lambda t: (_cid_of(t[1]) in defer_names,
                                      _star_of(t[1]), t[0])):
        # 占位件物理门(先于其余资格门短路):占席物品不可卖、无金币
        # 现值,判据单一源 = predicates.item_slot_unsellable(跨通道共享
        # 谓词,与 M4 燃料/凑息同门,禁内联复制)。
        if predicates.item_slot_unsellable(b):
            continue
        name = _cid_of(b)
        star = _star_of(b)
        if star != 1:
            continue
        if not predicates.zero_overlap(name, k_members):
            continue
        if name in exclude_names:
            continue   # P60:买面义务集成员禁入卖出资格集
        if merge_material_reject_reason(name, star, bench, _deployed) \
                and name not in merge_guard_release:
            if counters is not None:
                count_merge_material_blocked(counters, name, dedup_names)
            continue
        # (挂后台效果资格门已随旧评估器退役删除——统一让位优先级迭代
        # 3.4:bench_effect_qualified 四消费位的危局阀桶处拆除,该维度
        # 由统一序列档 9 判定承载,判定表权威版本 =
        # strategy-docs/32_unified_sell_priority.md §3。)
        out.append(_slot_of(b, i))
        # 1★ 卖回净额 = sell_refund(1,注册表 cost) 派生(R196 症6:
        # 禁字面量 3 双源——bench_char_cost 未知名保守估 3 与旧值同构)
        remaining -= sell_refund(1, bench_char_cost(bench_slot_unit(b)))
        if remaining <= 0:
            break
    return out, ''
