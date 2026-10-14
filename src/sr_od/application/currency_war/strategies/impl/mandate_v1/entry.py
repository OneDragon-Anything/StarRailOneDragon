"""cw4 备战决策入口(九段全扫工序)。

工序结构(判据正本 = strategy-docs/22_prep_screen.md §1):每次回到备战
画面从第 0 步向下扫描,执行第一个满足条件的步骤并返回其动作,下一帧
重新扫描(单动作循环不变;回跳语义——腾位后回头点晶矿、买完牌回头
部署——在全扫下自然表达):

    第 0 步 溢出告警自救 → 第 1 步 点开消耗品 → 第 2 步 晶矿
    → 第 3 步 升级检查(11 号篇 §2:五臂判据 + 整级预授权
       + 变现步 + 执行帧整批发出)
    → 第 4 步 商店会话 → 第 5 步 部署调整 → 第 6 步 装备与工具
    → 第 7 步 节末凑息 → 第 8 步 出战

模块分工:买面/凑息/腾位的备战域动作发出点(dominance/M2/M4/M6
凑息臂)由店内会话(23 号篇)与卖出评估器(criteria/sell_candidates,
卖出场景注册表)承载;卖出场景统一消费 ``evaluate_sell_candidates``;
升级判据本体 = ``criteria/levelup``(11 号篇 §2),本模块只做
工序接线与发出组装。部署/装备/工具判据单一源 = deploy_plan /
cw_equip_wear_plan / cw_equip_env(第 5/6 步只承载调用时机)。

``mandate.run_mandate`` 为测试面已登记函数(生产调用走本模块 emit)。
``truncate_frame_stable``(帧稳定截断动作发出器,词表正本 =
flow/action_exec.md §1)与 ``_ore_bench_free`` 等公共骨架——
bridge 与测试面在产消费。

晶矿第 2 步 = 垫件纯判断(无试错计数)。占席颜色→内容映射为待实机
证项,若立项需双倍审面(判据面 + 建档面)。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
from sr_od.application.currency_war.kernel.cw_economy import (
    cap_resolved_of_session,
    in_must_spend_zone,
    saturation_line,
)
from sr_od.application.currency_war.kernel.cw_exec_state import BENCH_CAPACITY
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_entries_of,
    bench_free_slots,
    deployed_rows_of,
    game_state_of,
    gold_of,
    level_of,
    max_units_of,
    node_kind_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    ore_click_targets_of,
    select_ore_clicks,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionCollectOreParam,
    CwActionDeployMoveParam,
    CwActionFurnaceUseParam,
    CwActionLevelUpParam,
    CwActionLuckyTokenUseParam,
    CwActionOpenBookcardParam,
    CwActionOpenBoxParam,
    CwActionOpenShopParam,
    CwActionOpenTomeParam,
    CwActionPerfectProjectorUseParam,
    CwActionPrecisionWrenchUseParam,
    CwActionPrivilegeCardUseParam,
    CwActionSellBenchParam,
    CwActionSellDeployedParam,
    CwActionStaffProjectorUseParam,
    CwActionStartBattleParam,
    CwActionWearEquipParam,
    CwActionWrenchUseParam,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    mandate,
    session_scope,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.sell_candidates import (
    SellCandidate,
    evaluate_sell_candidates,
    is_ore_pad_unit,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
        LevelUpPreAuth,
    )
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
        MandateFrame,
    )

log = logging.getLogger(__name__)


#: ev_arm 值域(R1-1 实验因子;**商店域 shop.py 消费中**——备战 emit 的
#: 本常量为商店域校验的兼容单一源(备战域 EV pass 不在九段工序内),
#: 随商店会话正本维护(23 号篇)。
EV_ARM_VALUES: tuple[str, ...] = ('skeleton_only', 'full')


def _deployed_units_of(gs: GameState) -> list:
    """上场单位域紧缩序(deployed 视图两子表的容器 Unit,前排在前;
    本模块单一读点,benchchar-retirement P4 容器形)。"""
    front, back = deployed_rows_of(gs)
    return [d for d in (*front, *back) if d is not None]


def _ore_bench_free(gs: GameState) -> int:
    """席自由槽读数(晶矿第 2 步「席位未满」判据输入;容器派生读口
    ``bench_free_slots`` 单一源)。缺省方向 = adapter.py 在库裁决对齐:
    free None(bench 未观察,不确定)→ BENCH_CAPACITY,宁多收晶矿不误卖,
    非 0 值按物理现读。"""
    _free = bench_free_slots(gs)
    return BENCH_CAPACITY if _free is None else max(0, int(_free))


#: 单批采晶矿上界(框架流程防线常量,非三形态决策值——它上界化单帧发出
#: 的点击预算,不作任何做/不做闸门):席满时晶矿点不动,批式连点越过
#: 自由席位数即空点,批间由晶矿计数自然回补(screen_flow_timing #16
#: 容忍语义)。执行层硬帽 = kernel ``ORE_CLICK_HARD_CAP``(防识别抖动
#: 死循环);kernel ``select_ore_clicks``(大晶矿优先/上界挑选单一源)
#: 显式消费本常量为预算参数(单一源,禁再内联字面 3)。
ORE_CLICK_BATCH_MAX_K: int = 3

# ===== 帧稳定截断分类(契约 v2 §3.2 备战线域逐类;词表 as-built 权威
# ===== = flow/action_exec.md §1,动作发出器增补条目须回契约改版,禁只改代码)=====

#: 截断点(该动作可作序列最后一个动作发出,其后截断)。武装箱选卡 = 画面
#: op 分发,非动作词表成员。穿戴/工具原子 = 截断点:穿戴即合成/网格
#: reflow aftermath 不可静态预测(决策侧逐帧现算,每原子独占动作发出帧)。
_TRUNCATION_POINTS: tuple[type, ...] = (
    CwActionOpenBoxParam, CwActionOpenTomeParam, CwActionOpenShopParam,
    CwActionOpenBookcardParam,
    CwActionWearEquipParam, CwActionFurnaceUseParam, CwActionPrivilegeCardUseParam, CwActionWrenchUseParam, CwActionPrecisionWrenchUseParam,
    CwActionStaffProjectorUseParam, CwActionPerfectProjectorUseParam, CwActionLuckyTokenUseParam,
)
#: 终点(只能作序列最后一个动作;CwActionStartBattleParam = 出战环出口)
_TERMINAL: tuple[type, ...] = (CwActionStartBattleParam,)
#: 可续(画面零迁移/坐标不变)
_CONTINUABLE: tuple[type, ...] = (CwActionLevelUpParam,)
#: 条件续(bench 索引结构恒稳 + 名-槽一致性复检;board 空位/星级合成按
#: 前序动作累积静态推出,推不出即截断——契约 §3.2;CwActionCollectOreParam
#: 行 = 条件:常态可续,末批可能掉箱后截断)
_CONDITIONAL: tuple[type, ...] = (
    CwActionSellBenchParam, CwActionSellDeployedParam, CwActionDeployMoveParam,
    CwActionCollectOreParam,                          # 条件:常态可续;末批可能掉箱后截断
)


def classify_frame_stability(action: CwAction) -> str:
    """单动作帧稳定分类(契约 v2 §3.2 逐类判的机器可读形式)。

    返回:'continue' / 'conditional' / 'truncation' / 'terminal' /
    'unknown'(词表外/无分类 ⇒ §3.3 fail-closed)。
    """
    for t in _TERMINAL:
        if isinstance(action, t):
            return 'terminal'
    for t in _TRUNCATION_POINTS:
        if isinstance(action, t):
            return 'truncation'
    for t in _CONDITIONAL:
        if isinstance(action, t):
            return 'conditional'
    for t in _CONTINUABLE:
        if isinstance(action, t):
            return 'continue'
    return 'unknown'


def truncate_frame_stable(actions: list[CwAction],
                          session: StrategySession | None = None,
                          *, bench_slots: set[int] | None = None,
                          ) -> list[CwAction]:
    """帧稳定截断动作发出器(契约 §2 帧稳定域 + §3 分域枚举 + §3.3)。

    逐动作判「本动作执行后的画面状态能否静态推出」:可续/条件续 →
    继续发出;截断点 → 该动作作为序列最后一个动作发出;终点 → 序列
    终点(其后必须截断);unknown(词表外/无分类)→ fail-closed 截断
    + 计数披露(``emitter_unknown_action_truncated``)。

    conditional 类的复检(键 = 容器槽位表下标,动作发出器生产路径经 bridge
    供给生成期占用集):

    - ``CwActionSellBenchParam``/``CwActionDeployMoveParam``:bench 槽位
      引用对 ``bench_slots`` 复检 + 前序同序列卖出/拖出累积逻辑态(槽位
      卖出后从逻辑态集移除)——引用空槽/未知槽 ⇒ 推不出 ⇒ 该动作处
      截断 + ``emitter_conditional_truncated`` 计数。``bench_slots``
      缺省 None = 复检语境缺失,按条件成立续发。
    - ``CwActionCollectOreParam``:末批判——同序列其后还有
      CwActionCollectOreParam 批次 ⇒ 非末批,常态分支可续;本批为序列内
      最后一批(可能掉箱,掉箱弹 overlay 不可静态预测)⇒ 其后截断(末批
      截断系判型内语义,非失败,不计 ``emitter_conditional_truncated``)。
    - ``CwActionSellDeployedParam``:deployed 槽表下标恒稳(卖出置 None
      不移位),序列内成立 ⇒ 可续。

    尾动作丢弃计数:任一截断路径(词表外/复检失败/截断点/终点/
    CwActionCollectOreParam 末批)丢弃的后续动作逐个计数
    ``emitter_post_truncation_dropped``——截断本身系契约语义(非失败),
    但「丢弃了什么」必须可观测,禁零计数静默。
    """
    counters: dict | None = None
    if session is not None:
        got = getattr(state_of(session), 'cw4_counters', None)
        if isinstance(got, dict):
            counters = got

    def _count(key: str, n: int = 1) -> None:
        if counters is not None:
            counters[key] = counters.get(key, 0) + n

    out: list[CwAction] = []
    slots: set[int] | None = set(bench_slots) if bench_slots is not None else None

    def _cut() -> list[CwAction]:
        # 截断收尾:丢弃尾动作逐个计数(零静默披露)
        _count('emitter_post_truncation_dropped', len(actions) - len(out))
        return out

    for i, a in enumerate(actions):
        kind = classify_frame_stability(a)
        if kind == 'unknown':
            _count('emitter_unknown_action_truncated')
            return _cut()       # 词表外:该动作处截断(不猜测分类)
        if kind == 'conditional':
            if isinstance(a, CwActionCollectOreParam):
                has_later_batch = any(
                    isinstance(a2, CwActionCollectOreParam) for a2 in actions[i + 1:])
                out.append(a)
                if not has_later_batch:
                    return _cut()  # 末批可能掉箱 ⇒ 其后截断(判型内语义)
                continue
            if isinstance(a, (CwActionSellBenchParam, CwActionDeployMoveParam)):
                if slots is not None and a.bench_idx not in slots:
                    _count('emitter_conditional_truncated')
                    return _cut()  # 名-槽一致性复检失败:推不出即截断
                out.append(a)
                if slots is not None:
                    slots.discard(a.bench_idx)
                continue
            # CwActionSellDeployedParam:deployed 槽表下标恒稳,序列内成立
            out.append(a)
            continue
        out.append(a)
        if kind in ('truncation', 'terminal'):
            return _cut()
    return out


# ============================================================ 上阵窗口适用范围(22 号篇 第 5 步)

#: 终局库成员并集(core ∪ shared 全线去重;纯终局件谓词的「终局库成员」
#: 腿——未锁定期按全库知识判定的数据面,22 号篇 第 5 步)。
_ENDGAME_LIBRARY_MEMBERS: frozenset[str] = frozenset(
    name
    for _comp in COMP_LIBRARY
    for name in (*_comp.core_chars, *(_comp.shared_chars or ())))


def _entry_window_open(gs: GameState, char_id: str) -> bool:
    """角色上线窗口判定(22 号篇 第 5 步;数据 = COMP_LIBRARY
    ``entry_signals`` 建表,缺行 fail 恒假)。

    查线顺序:锁定 → 仅锁定线的信号行;未锁定 → 全库任一含该角色的线
    (候选囤件窗口未到时照囤不上,窗口适用范围同辖)。信号类闭集语义见
    ``Comp.entry_signals`` 字段注:``synergy`` = 该线主羁绊
    (bond_signal,缺省 form_tiers 首键)板面计数 ≥ 阈值;``level`` =
    玩家等级 ≥ 阈值;``plane_end`` = 终局位面段已启动(窗口谓词形态 =
    ``session_scope.plane2_started_of``,宪法第 2 条合规);``always_on``
    = 恒真(全局累积型例外)。
    """
    from sr_od.application.currency_war.kernel.cw_board_by_row import board_by_row
    view = session_scope.line_members_view(gs)
    if view.locked:
        from sr_od.application.currency_war.kernel.cw_comps import get_comp
        comps = [c for c in (get_comp(view.comp_name),) if c is not None]
    else:
        comps = list(COMP_LIBRARY)
    _board_counts: dict[str, int] | None = None
    for comp in comps:
        sig = comp.entry_signals.get(char_id)
        if sig is None:
            continue
        kind, threshold = sig
        if kind == 'always_on':
            return True
        if kind == 'level':
            if level_of(gs) >= int(threshold):
                return True
        elif kind == 'plane_end':
            if session_scope.plane2_started_of(gs):
                return True
        elif kind == 'synergy':
            if _board_counts is None:
                front, back = deployed_rows_of(gs)
                _board_counts = board_by_row(front, back).total()
            tag = comp.bond_signal or (
                comp.form_tiers and next(iter(comp.form_tiers)))
            if tag and _board_counts.get(tag, 0) >= int(threshold):
                return True
    return False


def _deploy_window_blocked(session: StrategySession,
                           gs: GameState, char_id: str) -> bool:
    """纯终局件窗口适用范围判定(22 号篇 第 5 步)。

    纯终局件谓词 = 终局库成员 ∧ 非现行过渡配方成员(未锁定期按全库
    知识判定,锁定后按锁定线名单);窗口未到 → True(挡上阵)。过渡∩
    终局重叠件 = 过渡成员正常上阵(它们的上阵是过渡行为,不挡)。未识别
    件(char_id='')fail-open 照旧上(与部署谓词同口径)。
    """
    if not char_id:
        return False
    k = session_scope.direction_comp_of(session)
    if char_id in predicates.line_members(k):
        return False   # 现行过渡/方向配方成员 = 过渡行为正常上阵
    view = session_scope.line_members_view(gs)
    if view.locked:
        if char_id not in view.members:
            return False   # 锁定线外的囤件非当前终局成员(其上阵 = 插件/P24 行为)
    elif char_id not in _ENDGAME_LIBRARY_MEMBERS:
        return False
    return not _entry_window_open(gs, char_id)


def _bench_char_at(gs: GameState, container_idx: int) -> str:
    """bench 容器槽位表下标 → 角色规范名(占位件/空槽 = '';
    窗口适用范围过滤的部署计划行身份读点)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    view = gs.bench.value
    if view is None or not 0 <= container_idx < len(view.slots):
        return ''
    unit = bench_slot_unit(view.slots[container_idx])
    return str(unit.char_id or '') if unit is not None else ''


def _emit_deploy_moves_scoped(out: list, frame: MandateFrame,
                              session: StrategySession, state: GameState,
                              tag: str, *, window_scope: bool) -> None:
    """部署动作发出点(第 0 步态 1 与第 5 步共用;选人/落位/对位单一源 =
    ``deploy_plan.deploy_plan_moves``——判据本体不改动,prep_pipeline
    22 号篇 §1 第 5 步)。

    ``window_scope`` = 是否施加上阵窗口适用范围:第 5 步 True(终局成员在
    其上线窗口前不上阵);第 0 步态 1 False(告警帧豁免——上阵纯为腾槽
    保命,告警解除后下轮全扫窗口适用范围恢复正常,22 号篇 第 0 步
    态 1 豁免行)。板满前置门与现行 ``mandate._emit_deploy_moves`` 同门
    同源。
    """
    if mandate._deploy_cap_full_gate(session, state, frame):
        return
    from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
        deploy_plan_moves,
    )
    for bi, row, slot, faction in deploy_plan_moves(frame, session, state):
        if window_scope and _deploy_window_blocked(
                session, state, _bench_char_at(state, int(bi))):
            continue
        out.append(mandate.Emitted(
            CwActionDeployMoveParam(bench_idx=int(bi),
                                    to_row=row,
                                    to_slot=int(slot),
                                    faction=faction),
            True, tag))


def _make_windowed_select_up(session: StrategySession, gs: GameState):
    """select_swap_plan 的 select_up 注入包装(第 5 步换血替补的上阵窗口
    适用范围——契约 D 部署换血行:替补受窗口适用范围辖,窗口未到的终局替补
    不可上 = 窗口适用范围自然结果,换血通道由过渡替补在产)。

    过滤形态:窗口未到件从 up 集移入 held(不给拒因键——窗口适用范围是帧级
    defer 非资格拒,不进 select_deployments 拒因闭集);被滤后 up 空的
    假想板面由 select_swap_plan 自然判计划不成立。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
        _slot_cid,
        select_deployments_reasoned,
    )

    def _select_up(bench, **kwargs):
        up, held, reasons = select_deployments_reasoned(bench, **kwargs)
        kept = [i for i in up if not _deploy_window_blocked(
            session, gs, _slot_cid(bench[i]))]
        if len(kept) == len(up):
            return up, held, reasons
        dropped = sorted(set(up) - set(kept))
        return kept, list(held) + dropped, reasons

    return _select_up


# ============================================================ emit(九段全扫)


def emit(session: StrategySession,
         config: object, *,
         registry: DecisionV2Registry | None = None) -> list[Emitted]:
    """备战决策入口九段全扫(22 号篇 §1;返回 Emitted 列表交桥截断)。

    决策输入 = 容器 game state 直读(黑板帧停用契约照旧)。每帧从第 0
    步向下扫描,首中段返回其动作序列(单动作循环取首项执行);全部不中
    ⇒ 第 8 步出战。步间调用:3.1 边界/标记/清单存储(session_scope)、
    3.2 卖出评估器(evaluate_sell_candidates,契约 D 场景参数化)。

    ``config`` = 调用方透传(现行九段无消费面;旧 ev_arm 实验因子随 EV
    pass 停用)。``registry`` = 上下文注册表(装备计划等级帽等消费注入)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )

    st = state_of(session)
    if getattr(st, 'cw4_counters', None) is None:
        st.cw4_counters = {}

    # 决策判据载体一次置顶(同帧同视图纪律,禁函数内二次取容器)。
    gs = game_state_of(session)
    _round_num = round_num_of(gs)

    # 读数协议入口序(23 号篇读数协议节):账面同步(吸收
    # 备战域卖出/买经验的上报链 delta)+ 合成族失效检测(全扫级——
    # 任何 3★ 合成结果帧不分源,持有 3★ 集合帧差检测)。
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        shop_session as shop_sess,
    )
    shop_sess.sync_gold_ledger(gs)
    shop_sess.detect_merge_result_frame(gs)

    # 骨架帧装配(部署面共用输入;stop_flag 构造性 False——成型停买线 = 买面
    # 判据,消费位在商店域(shop.py 自装配),备战域 M2 已移店内)。
    # k = 现行方向 阵容(锁定线优先,未锁 = 过渡配方开局面;键面归一
    # 归一后的统一读口 direction_comp_of——12 号篇 §2 消费面分派)。
    _k = session_scope.direction_comp_of(session)
    k_members = predicates.line_members(_k)
    # K 空窗回退(部署围栏目标供给;回退单一源 = cw_intention,与商店域
    # 同源消费,禁复制兜底逻辑;ist 缺失 = 意向供给缺帧,保守侧不回退)。
    if _k is None:
        from sr_od.application.currency_war.kernel import cw_intention
        _ist = getattr(st, 'v3_intention', None)
        if _ist is not None:
            _fb, _band = cw_intention.k_empty_window_fallback(
                gs, _ist, session=session, registry=registry)
            if _fb:
                k_members = tuple(sorted(_fb))
                st.cw4_counters[f'prep_k_fallback_{_band}'] = \
                    st.cw4_counters.get(f'prep_k_fallback_{_band}', 0) + 1
    _bench = bench_entries_of(gs)
    _deployed = _deployed_units_of(gs)
    frame = mandate.MandateFrame(
        gold=gold_of(gs),
        level=level_of(gs),
        bench=list(_bench), deployed=list(_deployed),
        deploy_cap=max_units_of(gs),
        node_type=node_kind_of(gs),
        stop_flag=False, k_members=k_members,
        round_num=_round_num,
        owned_equips=(list(gs.equips.value)
                      if gs.equips.value is not None else None),
        overflow_warning=bool(gs.overflow_warning.value))

    # —— 第 0 步:溢出告警自救(22 号篇 §1 第 0 步)——
    # 告警在场 = 备战席 9 格全满且溢出位有卡,溢出卡阻断进入战斗;解除
    # 方式唯一 = 腾出一个备战席空槽。自救动作序按损失递增排列(免费在
    # 前、有损卖出最后),每帧重评取首个可行,无试错计数;告警在场时
    # 其余步骤全部不执行(告警不消出战无效,例外仅自救动作本身)。
    if bool(gs.overflow_warning.value):
        _rescue = _step0_overflow_self_rescue(session, gs, frame)
        return _rescue   # 含 [] = 防御分支零动作返回主循环(不出战)

    # —— 第 1 步:点开消耗品(书册卡 → 补给箱 → 星徽秘典;臂序 = 现行
    # 实体面段在案顺序)——弹窗由外循环画面分发接住,处理后回备战重新
    # 全扫(弹窗不是工序步骤)。
    _open_act = _consumable_open_action(gs)
    if _open_act is not None:
        return [_open_act]

    # —— 第 2 步:晶矿(22 号篇 §1 第 2 步)——
    _ore_out = _step2_ore(session, gs)
    if _ore_out:
        return _ore_out

    # —— 第 3 步:升级检查(11 号篇 §2 概率主轴 + 整级预授权 +
    # 变现步;判据五臂 = criteria/levelup.upgrade_trigger。预授权键驱动
    # 两帧态:授权帧(判据通过 → 置键 → 变现序列每帧一卖)与执行帧
    # (缺口闭合 → 购买经验整批发出,实付上界 = 授权值不再重闸)——
    # 单动作循环下每帧全扫到本步,键与缺口面共同决定本帧动作)——
    step3_actions: list[Emitted] = _step3_level_up(session, gs, registry)
    if step3_actions:
        return step3_actions

    # —— 第 4 步:商店会话(22 号篇 §1 第 4 步;契约 A)——
    # 入口先调解拦复核(判定函数本体 = criteria/shop_session);然后判标记
    # ≠ 当前节点号。满足 → 开店(备战侧决策性开店意图的唯一来源)。
    if _step4_shop_session_pending(session, gs):
        return [Emitted(CwActionOpenShopParam(), True, 'step4_shop_session')]

    # —— 第 5 步:部署调整(部署面判据照旧;调用时机在商店会话
    # 之后——「先逛店再统一部署」)——
    _deploy_out = _step5_deploy(session, gs, frame, step3_actions)
    if _deploy_out:
        return _deploy_out

    # —— 第 6 步:装备与工具(工具判据 =
    # kernel/cw_equip_env.evaluate_tool_actions;调用位置固定为部署
    # 之后)——
    _equip_out = _step6_equip_tools(session, gs, registry)
    if _equip_out:
        return _equip_out

    # —— 第 7 步:节末凑息(22 号篇 §1 第 7 步)——所有花费决策
    # 完成后的最终利息线检查(为买而卖在会话内,为息而卖在本步;息按节末
    # 金位结算,提前卖会被后续购买把金位吃回去)。
    _interest_out = _step7_node_end_interest(session, gs)
    if _interest_out:
        return _interest_out

    # 形态⑥观测(纯观测零行为,fail-closed 期只记不判):target 空窗
    # ∧ 濒死带 ∧ 域外 ∧ 持金 ∧ 本帧零金消费——金滞留入败局的形态暴露
    # (键名申报源 = supply_arbitration_design §5.1 terminal_targetless_
    # idle;载体适用范围随工序重排收窄 = 到达第 7 步之后的帧,实体面/开店/
    # 部署/装备帧提前返回不入键;到达本段的帧无 LevelUp/OpenShop 类
    # 动作,旧动作面条件恒真,申报)。
    if (gold_of(gs) > 0
            and session_scope.direction_comp_of(session) is None
            and not in_must_spend_zone(gold_of(gs), session)
            and (predicates.p1_blood_floor(gs)
                 or predicates.p2_blood_floor(gs))):
        st.cw4_counters['terminal_targetless_idle'] = \
            st.cw4_counters.get('terminal_targetless_idle', 0) + 1

    # —— 第 8 步:出战(以上全部步骤无动作;备战环唯一完成态)——
    # 出战前置动作发出点机制保留在 bridge(出战就绪 帧短路本 emit,机制出处 =
    # strategy-docs/26 号篇;本迭代零改动);受限商店访问帧不受会话标记
    # 辖(契约 A 豁免条款,前置位承载)。
    return [Emitted(CwActionStartBattleParam(), True, 'battle')]


# ============================================================ 第 0 步:溢出告警自救


def _consumable_open_action(gs: GameState) -> Emitted | None:
    """备战席消耗品点开动作(第 1 步主体;第 0 步态 2 复用)。

    触发 = bench 槽位 kind ∈ bookcard/supply_box/tome(现行容器
    BenchSlot.kind 判定);点开顺序 = 书册卡 → 补给箱 → 星徽秘典
    (现行实体面臂序,入口清场旧全局序在案)。星徽秘典占席 = 待实机
    证实项(点开出路对其防御性纳入,22 号篇 第 1 步)。动作参数
    = 物理槽号(下标 + 1,执行器按槽号现算点击坐标)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    _slots = (gs.bench.value.slots if gs.bench.value is not None else [])
    for kind, atom_cls, tag in (
            ('bookcard', CwActionOpenBookcardParam, 'prep_bookcard'),
            ('supply_box', CwActionOpenBoxParam, 'prep_box'),
            ('tome', CwActionOpenTomeParam, 'prep_tome')):
        idx = next((i for i, s in enumerate(_slots)
                    if s is not None and s.kind == kind), None)
        if idx is not None:
            return Emitted(atom_cls(slot=idx + 1), True, tag)
    return None


def _step0_overflow_self_rescue(session: StrategySession, gs: GameState,
                                frame: MandateFrame) -> list[Emitted]:
    """第 0 步溢出告警自救序(22 号篇 §1 第 0 步;按损失递增,
    每帧重评取首个可行,无试错计数)。

    态序:① 上阵安置(免费腾位,告警帧豁免窗口适用范围——上阵纯为腾槽
    保命)→ ② 点开消耗品(免费腾位;占席道具不可卖但可点开)→
    ③ 卖出(有损腾位;评估器自救扩展面 = 仅备战席 + 真全量持有,P78
    资格仲裁族全通道豁免、线内件按价值序末位让位)→ ④ 防御性分支
    (识别异常真实形态;真全量可卖下候选空结构性不可达,若仍到达 =
    零动作正常返回主循环轮转,持续无推进由外部哨兵保留证据暴露)。

    空板守卫 as-built 如实申报:评估器内 empty_board_sell_blocked 为
    后态判定,deployed = 0 帧卖出哑火——deployed = 0 帧的自救主路径 =
    态 1 上阵安置(非卖出,不受该守卫辖;22 号篇 第 0 步申报)。
    """
    # 态 1:上阵安置(免费;cap 有空位 ∧ 备战席有可上阵单位——豁免窗口
    # 适用范围,部署判据本体与现行 M1 同源)。
    if frame.deploy_vacancy > 0 \
            and mandate._deployable(frame, session, gs):
        _out: list[Emitted] = []
        _emit_deploy_moves_scoped(_out, frame, session, gs,
                                  'm0_self_rescue_deploy', window_scope=False)
        if _out:
            return _out
    # 态 2:点开消耗品(免费;占席道具腾槽)。
    _open_act = _consumable_open_action(gs)
    if _open_act is not None:
        return [_open_act]
    # 态 3:卖出(有损;评估器 'self_rescue' 场景 = 自救扩展面)。
    _cands, _why = evaluate_sell_candidates(gs, 'self_rescue')
    if _cands:
        return _emit_sell_candidate(
            session, gs, _cands[0], reason='self_rescue_sell',
            tag='m0_self_rescue_sell', counter='self_rescue_sell')
    # 态 4:防御性分支(结构不可达;识别异常形态零动作返回主循环)。
    st = state_of(session)
    st.cw4_counters['self_rescue_no_exit'] = \
        st.cw4_counters.get('self_rescue_no_exit', 0) + 1
    log.warning('[cw!][self-rescue] 溢出告警帧自救序全不可行'
                '(态 4 防御分支;拒因键 = %s)', _why)
    return []


def _emit_sell_candidate(session: StrategySession, gs: GameState,
                         cand: SellCandidate, *, reason: str, tag: str,
                         counter: str) -> list[Emitted]:
    """卖出候选动作发出点(第 0/2/7 步共用;评估器候选 → 动作)。

    坐标换算:评估器候选 idx = 紧缩占席序下标(bench 支)→ 容器槽位表
    下标(动作参数坐标系);deployed 支 = 上场紧缩行序 → 容器行序
    (CwActionSellDeployedParam 坐标系)。失配 = 陈旧帧 fail-closed
    零动作返回主循环。卖出登记(record_round_sold) = 轮内新鲜度排除
    账本写端(资格面账本,非试错计数),与现行卖出位同口径。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    st = state_of(session)
    if cand.zone == 'bench':
        vidx = mandate._bench_container_idx_by_compact(gs, cand.idx)
        if vidx is None:
            st.cw4_counters[f'{counter}_stale_idx'] = \
                st.cw4_counters.get(f'{counter}_stale_idx', 0) + 1
            return []
        mandate.record_round_sold(session, gs, cand.char_id)
        st.cw4_counters[counter] = st.cw4_counters.get(counter, 0) + 1
        return [Emitted(CwActionSellBenchParam(bench_idx=vidx,
                                               reason=reason),
                        True, tag)]
    didx = mandate._deployed_container_idx(gs, cand.unit)
    if didx is None:
        st.cw4_counters[f'{counter}_stale_idx'] = \
            st.cw4_counters.get(f'{counter}_stale_idx', 0) + 1
        return []
    mandate.record_round_sold(session, gs, cand.char_id)
    st.cw4_counters[counter] = st.cw4_counters.get(counter, 0) + 1
    return [Emitted(CwActionSellDeployedParam(deployed_idx=didx),
                    True, tag)]


# ============================================================ 第 2 步:晶矿


def _step2_ore(session: StrategySession, gs: GameState) -> list[Emitted]:
    """第 2 步晶矿(22 号篇 §1 第 2 步;现行晶矿读口
    ``ore_click_targets_of``)。

    - 席位未满:点全部晶矿(判据 = 全点;执行面按批式点击上界分批推进,
      飞行等待 2s 口径 = screen_flow_timing #16);
    - 席位满:按候选身份直接判断值不值得腾位(无试错计数)——评估
      候选经**垫件谓词过滤后取价值最小**(价值函数无垫件身份维,1★
      插件可排 2★ 纯垫件之前,禁全池排序首位判断)→ 卖 1 个腾位,下轮
      全扫回来点晶矿;过滤集空(无垫件)→ 本节点放弃晶矿(确定的
      高价值持有不换随机产出)。判断天然自收敛:候选按价值升序让位,
      散件卖完后自动停在「无垫件可卖」——无次数上限。ore_defer 试错
      计数键族已随纯判断替代停用。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        shop_session as shop_sess,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    st = state_of(session)
    targets = ore_click_targets_of(gs)
    if not targets:
        return []
    if _ore_bench_free(gs) > 0:
        # 晶矿族失效触发(读数协议②;挂点 = 第 2 步动作发出点——随机金
        # 不可精确记账,失效交下次实读锚定收敛)。
        shop_sess.note_ore_click(gs)
        return [Emitted(CwActionCollectOreParam(
            points=select_ore_clicks(targets, ORE_CLICK_BATCH_MAX_K)),
            True, 'prep_spheres')]
    # 席满:垫件身份判断(评估器 'ore_make_room' 场景 = 仅备战席 + 常规面;
    # 消费 = 垫件谓词过滤后取价值最小)。
    _cands, _why = evaluate_sell_candidates(gs, 'ore_make_room')
    for _c in _cands:   # 评估器序 = 价值升序;首个垫件 = 价值最小垫件
        if not is_ore_pad_unit(gs, _c.char_id, _c.star):
            continue
        return _emit_sell_candidate(
            session, gs, _c, reason='ore_make_room',
            tag='ore_make_room_sell', counter='ore_pad_sell')
    # 无垫件 → 放弃晶矿(白拿的必拿精神保留:垫件卖尽前的晶矿全拿;
    # 放弃仅发生在需要牺牲高价值持有时——挂待玩家确认,prep_pipeline
    # 「关键取舍」节差分申报)。
    st.cw4_counters['ore_yield_no_pad'] = \
        st.cw4_counters.get('ore_yield_no_pad', 0) + 1
    return []


# ============================================================ 第 3 步:升级检查


def _fallback_legs_ok(session: StrategySession, gs: GameState,
                      pre: LevelUpPreAuth, name: str) -> bool:
    """P78-5′ 兜底豁免的两腿必要条件(design 契约 D 升级变现行;
    设计写入代码比对确认):豁免构成 = **义务账 ∨ 对象无损**。

    - 腿①(触发源义务血统维,验臂):``pre.source_arm`` 为骨架义务
      血统——人口位(02 号稿 §3 M3 义务正文)/ arm0(02 §5 回退)
      → 豁免成立,funding_hold_fallback 全量消费(对象不验);
    - 腿②(卖出对象级无损维,验对象非验触发臂):偏好账臂(停留门
      升级优先臂/概率账 = 优化路径;富余段-L3 = 20 号稿义务形态但
      P78-5′ 账性判别上零息损不构成「不做会输」= 偏好账——同走本
      腿)下被放行对象须持有账 ≈ 0:非核心/非④件(``holds``)∧ 非
      种子(P78-7 相邻轮回卖封口集)。funding_hold_fallback 兜底池
      ⊆ hold 核心集(池条件 = holds ∩ A 排除),偏好臂下结构性
      恒拒——验证照落为防御性腿(兜底池未来扩容非核心资产时腿②
      自动生效)。臂键缺省 ''(异常/无臂身份)按保守侧走腿②对象验。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup,
    )
    if pre.source_arm in (levelup.ARM_POPULATION, levelup.ARM_ARM0):
        return True    # 腿①:骨架义务血统(授权文号含义务正文)
    from sr_od.application.currency_war.kernel.cw_card_identity import (
        sell_hold_exclusion_names,
    )
    if name in sell_hold_exclusion_names():
        return False   # 核心/④件:持有账 > 0,腿②不成立
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        sell_gate,
    )
    # 种子(P78-7):相邻轮回卖封口集
    return name not in sell_gate.seed_exclusions(session, round_num_of(gs))


def _bench_liquid_gold(gs: GameState) -> int:
    """攒批资金的活期分量(11 号篇 §2 攒批口径):备战席
    **非线内 1★ 活期卡**退金合计(1★ 全额退口径)。

    bench-only 口径——与契约 D 升级变现候选池(bench∪场上无关角色)
    是两个分立维度:场上无关角色 1★ 退金**不计入**攒批基数(保守侧,
    两处口径分立维护非同源,11 号篇 §2 攒批资金口径行)。
    线内判定 = 卖出侧线内身份集(``sell_line_membership``:锁定线成员
    ∨ 未锁定期候选 top3 成员——「卖自己人凑升级金不在语义内」)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        bench_char_cost,
        sell_refund,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.sell_candidates import (
        refund_full_star_ok,
        sell_line_membership,
    )
    line = sell_line_membership(gs)
    total = 0
    for u in bench_units_of(gs):
        name = str(u.char_id or '')
        star = int(u.star or 1)
        if name and name not in line and refund_full_star_ok(star,
                                                             bench_char_cost(u, gs)):
            total += sell_refund(star, bench_char_cost(u, gs))
    return total


def _levelup_floor_ok(gs: GameState, session: StrategySession,
                      arm_key: str, after_gold: int) -> bool:
    """发出前花后金下界检查(11 号篇 §2 保底金门 + 守 50 定论(user_playstyle [3])
    确认前 fail 态的单一装配口)。

    - 全域(所有臂):保底金门 = ``guarantee_floor_gate`` 单一源
      (花后金 ≥ 1 利息档 boss_floor;两支不在本门设计范围内 = 终局域末战 ALL IN/
      买断制,门内自判)——``after_gold`` = 预估花后金(裸金 + 活期
      退金 − 批成本,保守下界),clicks/cost 传 0/1 直比形态;
    - 优化臂(概率账/停留门)追加:利息线差额保留(saturation_line,
      保守侧——「花完仍守 50」利息线级预算前提的确认前 fail 态;
      买断制 cap=0 时 saturation_line(0)=0 该门自动恒过,终局域经
      ``terminal_all_in`` 单一源豁免)。

    人口位/arm0/富余段为义务/机制臂,不受攒息约束([12]/[33] 明文
    例外),只辖保底金门。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        cap_resolved_of_session,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
        saturation_line,
    )
    cap = cap_resolved_of_session(session)
    if arm_key in (levelup.ARM_PROB_ACCOUNT, levelup.ARM_STAY_GATE) \
            and cap > 0 \
            and after_gold < saturation_line(cap) \
            and not levelup.terminal_all_in(gs, session):
        return False       # 优化臂利息线差额保留(确认前保守侧)
    # 契约核验(前提恒真行,纪律接线;失败 = 保守拒)。
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        contracts,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
        state_of,
    )
    if not contracts.ensure_contract(
            ('levelup', 'guarantee_floor_gate'),
            contracts.ContractCtx(), state_of(session).cw4_counters):
        return False
    return levelup.guarantee_floor_gate(gs, session, after_gold, 0, 1, cap)


def _step3_level_up(session: StrategySession, gs: GameState,
                    registry: DecisionV2Registry | None) -> list[Emitted]:
    """第 3 步升级检查(11 号篇 §2:五臂判据 + 整级预授权
    + 变现步 + 执行帧整批发出)。

    两帧态(单动作循环下每帧全扫到本步):

    - **键驱动帧**(预授权键在):缺口(裸金 < 授权批成本)未闭合 →
      变现序列每帧一卖(评估器升级变现场景,让位序;主路径尽 → P78-5
      兜底豁免拼装,单一源 ``sell_gate.funding_hold_fallback``)——候选
      穷尽 → 键保留至节点末、零动作(幂等重评,无试错计数);缺口闭合
      → 执行帧发购买经验整批(实付上界 = 授权值,**不再重闸**——防
      「买一半」复发)→ 清键。
    - **授权帧**(键不在):奖励帧抑制 → 等级帽 → 五臂判据 → P21
      (域内让位照 20 号稿)→ 血本位支付检查 → 攒批资金与发出前
      花后金下界 → 置键发出(裸金足 = 同帧执行帧;不足 = 置键进入
      变现序列,首卖本帧发出)。

    血本位局(XP 以血支付):金攒批与变现步不适用(变现卖出对血支付
    零贡献)——发出条件 = 血余额 ≥ 整级血成本(blood_xp_gate 单一
    源,静态阈值授权帧一次检查);不足 = 零购买(攒钱模式 = 等节点
    血收入)。整批发出 + 实付上界在血本位局同款生效。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        shop_session as shop_sess,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    st = state_of(session)
    counters = st.cw4_counters

    # 金位读数门(23 号篇金位读数形态:备战域金位唯一供给 = 账面;
    # 失效帧无法评估攒批/触发面 → 读数开店锚定,标记不动;账面宿主 =
    # 容器态(state_of(gs),与会话标记/清单同宿主)。
    if state_of(gs).gold_ledger is None:
        return _open_shop_for_gold_read(session, gs)

    # ===== 键驱动帧 =====
    pre = st.levelup_preauth
    if pre is not None:
        gold = gold_of(gs)
        if pre.gold_cost <= 0 or gold >= pre.gold_cost:
            # 执行帧:发购买经验整批(实付上界 = 授权值,不重闸)→ 清键。
            # 击数 = 剩余击数现读(门槛表差值折击数),超授权值按上界截
            # (XP 中途变化的数据漂移防御,非判据闸)。
            from sr_od.application.currency_war.kernel.cw_economy import (
                clicks_to_next_level,
                xp_click_cost,
            )
            clicks = clicks_to_next_level(gs)
            cost = xp_click_cost(gs)
            if cost > 0:
                clicks = min(clicks, pre.gold_cost // cost)
            st.levelup_preauth = None
            counters['levelup_batch_emitted'] = \
                counters.get('levelup_batch_emitted', 0) + 1
            # 升级发出失效/伴生钩子(读数协议②:升 9 级成长基金独立
            # 失效;节节高升任意升级 +1 伴生入金)。
            shop_sess.note_levelup_emission(gs, level_of(gs) + 1)
            return [Emitted(CwActionLevelUpParam(
                cost=int(cost), clicks=max(1, clicks),
                auth_basis='preauth'), True, 'step3_levelup_batch')]
        # 缺口未闭合 → 变现序列:每帧一卖(评估器升级变现场景,让位序)。
        cands, _why = evaluate_sell_candidates(gs, 'levelup_liquidate_prep')
        if cands:
            out = _emit_sell_candidate(
                session, gs, cands[0], reason='levelup_liquidate',
                tag='levelup_liquidate_sell',
                counter='levelup_liquidate_sell')
            if out:
                return out
        # 主路径尽 → P78-5 兜底豁免(funding 通道对价;触发前提 = 主路径
        # 空 ∧ 仍缺金——P78-5 四条件单一源 = sell_gate.funding_hold_
        # fallback,本循环只拼装消费,11 号篇 §2 变现步)。
        from sr_od.application.currency_war.kernel.cw_intention import (
            locked_buy_cap_hold,
        )
        from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
            sell_gate,
        )
        from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.sell_candidates import (
            sell_line_membership,
        )
        line = tuple(sorted(sell_line_membership(gs)))
        fallback = sell_gate.funding_hold_fallback(
            session, line, bench_entries_of(gs), gold=gold,
            need=pre.gold_cost,
            a_exclusions=sell_gate.sell_exclusions(
                session, line, channel='funding',
                current_round=round_num_of(gs),
                cap_hold=locked_buy_cap_hold(gs)),
            deployed=_deployed_units_of(gs),
            cap_hold=locked_buy_cap_hold(gs))
        if fallback:
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                bench_slot_unit,
            )
            u = bench_slot_unit(fallback[0])
            if u is not None and _fallback_legs_ok(session, gs, pre,
                                                   str(u.char_id or '')):
                idx = mandate._bench_container_idx(gs, fallback[0])
                if idx is not None:
                    mandate.record_round_sold(session, gs,
                                              str(u.char_id or ''))
                    counters['levelup_funding_fallback_sell'] = \
                        counters.get('levelup_funding_fallback_sell', 0) + 1
                    return [Emitted(CwActionSellBenchParam(
                        bench_idx=idx, reason='levelup_liquidate'),
                        True, 'levelup_liquidate_sell')]
            if u is not None:
                # 腿拒暴露(两腿必要条件不过——偏好账臂变卖有价资产):
                # 键保留零动作,分键区分「无兜底候选」与「候选被腿拒」。
                counters['levelup_fallback_leg_reject'] = \
                    counters.get('levelup_fallback_leg_reject', 0) + 1
        # 候选穷尽(含兜底):键保留至节点末,执行帧不发出——零动作结束本次访问
        # 全扫(幂等重评;失效出口 = 节点边界重置清键)。
        counters['levelup_liquidate_exhausted'] = \
            counters.get('levelup_liquidate_exhausted', 0) + 1
        return []

    # ===== 授权帧(键不在)=====
    # 奖励帧抑制(reward_node_suppressed 辖升级触发不辖刷新;抑制 =
    # 结构性无授权,后续支付检查无须求值)。
    from sr_od.application.currency_war.kernel.cw_reward_node import (
        reward_node_suppressed,
    )
    if reward_node_suppressed(gs):
        counters['levelup_reward_node_defer'] = \
            counters.get('levelup_reward_node_defer', 0) + 1
        return []
    # 判据契约核验(criteria/contracts.py 契约表;消费位
    # 经 ensure_contract,前提违例 = 弃权零动作 + 计数,契约纪律不断线)。
    # 等级帽(注册表 level_max 单一源;备战域等级真值每帧观察新鲜,
    # xp_ledger_stop 轮内盲区补位辖 shop 域逻辑态直写窗,此处不合取)。
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        contracts,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    if not contracts.ensure_contract(('levelup', 'lv9_stop'),
                                     contracts.ContractCtx(), counters):
        return []
    if levelup.lv9_stop(level_of(gs), reg.level_max):
        counters['levelup_reject_level_cap'] = \
            counters.get('levelup_reject_level_cap', 0) + 1
        return []
    # 五臂判据(11 号篇 §2 触发源并集;契约前提 = 人口位板满
    # 口径等级驱动 cap——消费位现读 max_units_of 传入核验)。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        max_units_of,
    )
    if not contracts.ensure_contract(
            ('levelup', 'upgrade_trigger'),
            contracts.ContractCtx(deploy_cap=max_units_of(gs)), counters):
        return []
    trig, arm_key = levelup.upgrade_trigger(gs, session, reg)
    if not trig:
        return []
    counters[f'levelup_trigger_{arm_key}'] = \
        counters.get(f'levelup_trigger_{arm_key}', 0) + 1
    # 富余段域内判定与备战期标志(20 号稿 L3 域内让位载体:本备战期曾入
    # 域即置标志,标志存续帧 P21 让位——「本备战期必花」语义,键式 =
    # (plane, round),节点推进自动失效)。
    from sr_od.application.currency_war.kernel.cw_economy import (
        in_must_spend_zone,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        plane_of,
    )
    phase = (plane_of(gs), round_num_of(gs))
    if in_must_spend_zone(gold_of(gs), session):
        st.cw4_must_spend_phase = phase
    zone_hit = (in_must_spend_zone(gold_of(gs), session)
                or st.cw4_must_spend_phase == phase)
    if not zone_hit:
        if not contracts.ensure_contract(('levelup', 'level_spend_blocked'),
                                         contracts.ContractCtx(), counters):
            return []
        if levelup.level_spend_blocked(gs, session, reg):
            # P21 危机带让位(域外帧;域内帧 = 富余花出义务优先)。
            counters['levelup_crisis_defer'] = \
                counters.get('levelup_crisis_defer', 0) + 1
            return []
    # 整级批成本(批大小 = 门槛表差值折击数,P48 整买引理形态)。
    from sr_od.application.currency_war.kernel.cw_economy import (
        clicks_to_next_level,
        xp_click_cost,
    )
    clicks = clicks_to_next_level(gs)
    if clicks <= 0:
        return []
    cost = xp_click_cost(gs)
    batch_cost = clicks * cost
    # 血本位支付检查([40]②:血余额 ≥ 下一级血成本才发整级授权,否则
    # 零购买;金本位局直通)。
    from sr_od.application.currency_war.kernel.cw_economy import (
        blood_xp_gate_for,
    )
    if not blood_xp_gate_for(gs, session):
        counters['levelup_blood_gate_defer'] = \
            counters.get('levelup_blood_gate_defer', 0) + 1
        return []
    from sr_od.application.currency_war.kernel.cw_investments import (
        blood_xp_mode,
    )
    if blood_xp_mode(session) is not None:
        # 血本位局:无变现步,授权帧即执行帧(血余额为静态阈值,无逐帧
        # 重闸复发面;闸已在上行过 = 发出条件成立)。
        shop_sess.note_levelup_emission(gs, level_of(gs) + 1)
        return [Emitted(CwActionLevelUpParam(
            cost=int(cost), clicks=clicks, auth_basis=arm_key),
            True, f'step3_levelup_batch:{arm_key}')]
    # 金本位:发出前花后金下界(保底金门全域 + 优化臂利息线差额保留;
    # 预估花后金 = 裸金 + 活期退金 − 批成本,保守下界)。
    liquid = _bench_liquid_gold(gs)
    if not _levelup_floor_ok(gs, session, arm_key,
                             gold_of(gs) + liquid - batch_cost):
        key = ('levelup_reserve_line_defer'
               if arm_key in (levelup.ARM_PROB_ACCOUNT, levelup.ARM_STAY_GATE)
               else 'levelup_guarantee_floor_defer')
        counters[key] = counters.get(key, 0) + 1
        return []
    # 攒批资金到位判定(裸金 + bench 非线内 1★ 活期退金 ≥ 批成本;
    # P48 整买纪律消费经契约核验)。
    if gold_of(gs) >= batch_cost:
        if contracts.ensure_contract(
                ('levelup', 'spend_unified'),
                contracts.ContractCtx(gold=gold_of(gs)), counters) \
                and levelup.spend_unified(clicks, gold_of(gs), cost):
            # 裸金足:同帧执行帧(P48 整买纪律放行,一次买齐)。
            shop_sess.note_levelup_emission(gs, level_of(gs) + 1)
            return [Emitted(CwActionLevelUpParam(
                cost=int(cost), clicks=clicks, auth_basis=arm_key),
                True, f'step3_levelup_batch:{arm_key}')]
        return []
    if gold_of(gs) + liquid >= batch_cost:
        # 裸金不足,活期补:置预授权键(含授权批成本上界)→ 变现序列
        # (首卖本帧发出;中间态 = 键在 ∧ 缺口未闭合 ∧ 候选尚存 → 下帧
        # 续卖,无商店域外金动作插入——零金穿插分域见 11 号篇 §2
        # §2.2 相邻性语义)。
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            LevelUpPreAuth,
        )
        st.levelup_preauth = LevelUpPreAuth(gold_cost=batch_cost,
                                            blood_cost=0,
                                            source_arm=arm_key)
        counters['levelup_preauth_issued'] = \
            counters.get('levelup_preauth_issued', 0) + 1
        cands, _why = evaluate_sell_candidates(gs, 'levelup_liquidate_prep')
        if cands:
            out = _emit_sell_candidate(
                session, gs, cands[0], reason='levelup_liquidate',
                tag='levelup_liquidate_sell',
                counter='levelup_liquidate_sell')
            if out:
                return out
        counters['levelup_liquidate_exhausted'] = \
            counters.get('levelup_liquidate_exhausted', 0) + 1
        return []
    # 攒批资金(含活期口径)不足整级 → 一击不买(攒钱模式,等节点收入;
    # 压牌库买入受整买预留约束不会吃掉攒批资金,23 号篇序 4 压牌库)。
    counters['levelup_stockpile_wait'] = \
        counters.get('levelup_stockpile_wait', 0) + 1
    return []


def _step3_liquidation_pending(session: StrategySession,
                               gs: GameState) -> bool:
    """升级变现序列在途判定(第 7 步凑息的抑制条件;11 号篇 §2
    帧交错规则①:变现序列优先于第 7 步凑息——同池 1★ 全额退候选
    竞争,抑制条件 = 键在 ∧ 变现候选尚存;变现穷尽后竞争消失、第 7 步
    凑息恢复——键保留至节点末不连带抑制凑息)。

    候选面与变现步同参(``levelup_liquidate_prep`` 场景评估一次),本
    函数零独立口径。"""
    st = state_of(session)
    if st.levelup_preauth is None:
        return False
    cands, _why = evaluate_sell_candidates(gs, 'levelup_liquidate_prep')
    return bool(cands)


# ============================================================ 第 4 步:商店会话入口


def _open_shop_for_gold_read(session: StrategySession,
                             gs: GameState) -> list[Emitted]:
    """金位读数开商店(22 号篇 §1 第 4 步前置/第 3/7 步读数门;
    23 号篇金位读数形态)。

    账面失效帧的金位供给形态:开店 → 入口观察锚定账面 → 会话决策
    (命中处理需求转正常会话;零处理 → 读数意图收工不置标记)。意图
    标记 = ``shop_read_intent``(收工位消费)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    st = state_of(gs)
    st.shop_read_intent = True
    st.cw4_counters['shop_gold_read_open'] = \
        st.cw4_counters.get('shop_gold_read_open', 0) + 1
    return [Emitted(CwActionOpenShopParam(), True, 'shop_gold_read')]


def _step4_shop_unblock_recheck(session: StrategySession,
                                gs: GameState):
    """解拦复核判定接线位(判定函数本体 = criteria/shop_session.
    shop_unblock_recheck,23 号篇读数协议;宪法第 6 条:备战第 4 步与
    商店入口两画面消费同一函数)。

    - ``unblock`` = 任一记录拦因解除(席位空出/金位达解除线)→ 调用方
      清「本节点已处理」标记,本步开店(记录的目标牌在店内段验证);
    - ``need_gold_read`` = 金不足类记录在场 ∧ 账面失效 → 读数形态开店
      (路径③;**标记不动**——标记门内锚定后即关,锚定后的下帧复核
      自然继续);
    - 方向锁定不走清单解拦(锁定写入直接清标记,12 号篇
      §1.4)。复核唯一触发点 = 本步入口,不在部署/卖出后挂触发钩子。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        shop_session as shop_sess,
    )
    return shop_sess.shop_unblock_recheck(gs)


def _step4_shop_session_pending(session: StrategySession,
                                gs: GameState) -> bool:
    """第 4 步商店会话触发判定(22 号篇 §1 第 4 步;契约 A)。

    入口序:解拦复核(读数腿开店不清标记——锚定后标记门
    即关,下帧复核继续)→ 解拦腿清标记 → 标记 ≠ 当前节点号判定
    (23 号篇;节点边界重置清值 = 双保险)。满足 → True
    (调用方输出 CwActionOpenShopParam)。
    """
    outcome = _step4_shop_unblock_recheck(session, gs)
    if outcome.need_gold_read:
        state_of(gs).shop_read_intent = True
        return True
    if outcome.unblock:
        session_scope.clear_shop_handled(gs)
    return not session_scope.shop_handled_for_current_node(gs)


# ============================================================ 第 5 步:部署调整


def _step5_deploy(session: StrategySession, gs: GameState,
                  frame: MandateFrame,
                  step3_actions: list[Emitted]) -> list[Emitted]:
    """第 5 步部署调整(22 号篇 §1 第 5 步;部署面判据照旧,
    判据本体不改动,仅调用时机移到商店会话之后)。

    结构(判据本体与 run_mandate 部署段同源;升级后补部署经**下帧
    M1 空槽补位结构性收敛**——九段全扫单动作循环下第 3 步命中即
    emit 返回,升级帧到不了本步;下帧全扫 deploy_vacancy 更新后 M1
    以零卖出成本接管,「卖出不可逆 > 等一帧」的原语义由该结构承载,
    不设独立 M1′ 分支):
    - M5 开局配方(开局帧 round_num ≤ 1 ∧ 板空 ∧ bench 有件);
    - M1 空槽凑人数补位(deploy_vacancy > 0;任意合法单位上阵优于空槽,
      P24 残余补部署——升级开新 vacancy 的补部署也经本臂);
    - M1″ 板满换阵补部署(m1p 换血;替补受上阵窗口适用范围辖)。

    上阵窗口适用范围(用户裁定 2026-10-12):终局成员在其上线窗口前不上阵
    ——纯终局件谓词 + 窗口判定见 :func:`_deploy_window_blocked`;过渡∩
    终局重叠件按过渡成员正常上阵;全局累积型例外 = entry_signals 的
    always_on 信号类。
    """
    out: list[Emitted] = []
    deploy_intent_emitted = False
    # M5 开局板(开局配方 = 过渡体系开局)。
    if (frame.round_num <= 1 and not frame.deployed and frame.bench
            and mandate._deployable(frame, session, gs)):
        _emit_deploy_moves_scoped(out, frame, session, gs,
                                  'm5_opening_board', window_scope=True)
        deploy_intent_emitted = bool(out)
    # M1 同帧部署(空槽补位)。
    if (not deploy_intent_emitted and frame.deploy_vacancy > 0
            and mandate._deployable(frame, session, gs)):
        _emit_deploy_moves_scoped(out, frame, session, gs,
                                  'm1_deploy', window_scope=True)
    # M1″ 板满换阵(m1p 换血;up 候选经窗口适用范围包装注入)。defer_actions
    # 输入在九段全扫下单动作循环下结构性恒空(第 3 步命中即 emit 返回,
    # 升级帧到不了本步)——同帧升级推迟换血的语义由结构承载:升级帧
    # 第 3 步先行返回 + 下帧 M1 空槽补位以零卖出成本接管(卖出不可逆
    # > 等一帧)。
    if not any(isinstance(e.action, (CwActionDeployMoveParam,
                                     CwActionSellDeployedParam))
               for e in out):
        out.extend(mandate.emit_swap_redeploy(
            frame, session, gs,
            select_up=_make_windowed_select_up(session, gs),
            defer_actions=step3_actions))
    return out


# ============================================================ 第 6 步:装备与工具


def _step6_equip_tools(session: StrategySession, gs: GameState,
                       registry: DecisionV2Registry | None) -> list[Emitted]:
    """第 6 步装备与工具(22 号篇 §1 第 6 步)。

    - 装备穿戴 = 现行完整实现整体保留(合成规划/分配/转移;计划产出位
      单一源 = kernel/cw_equip_wear_plan._build_equip_wear_plan);
    - 工具使用判据 = 现行 kernel/cw_equip_env.evaluate_tool_actions 不动
      (G1 准入 + 逐件原子发出);
    - 组内序:穿戴先行、工具随后(旧「工具动作先于骨架动作发出」的排序
      随编排停用;穿戴/工具原子均系截断点,实际执行逐帧单件收敛)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    st = state_of(session)
    counters = st.cw4_counters
    out: list[Emitted] = []
    owned = list(gs.equips.value or [])
    if not owned:
        return out
    # —— 装备穿戴(M7)——
    if mandate.m7_wearable_exists(owned):
        from sr_od.application.currency_war.kernel.cw_equip_wear_plan import (
            _build_equip_wear_plan,
        )
        build = _build_equip_wear_plan(session, registry)
        if build.fail_reason:
            # 资源前置缺失(装备观察域未就绪)= 未发出通道,下帧重派。
            counters['equip_plan_resource_missing'] = \
                counters.get('equip_plan_resource_missing', 0) + 1
        else:
            for step in build.steps:
                out.append(Emitted(
                    CwActionWearEquipParam(item_name=step.item_name,
                                           char_name=step.char_name,
                                           row=step.row, slot=step.slot),
                    True, 'm7_equip_transfer'))
            if not build.steps:
                counters['equip_plan_empty_noop'] = \
                    counters.get('equip_plan_empty_noop', 0) + 1
    # —— 工具消费(判据/准入单一源 = kernel/cw_equip_env;评估留痕与
    # 原子构造 = 现行 M7.5 动作发出点原样移入)——
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        admitted_tool_actions as _admit_tools,
    )
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        evaluate_tool_actions as _eval_tools,
    )
    counters['m7_5_evaluated'] = counters.get('m7_5_evaluated', 0) + 1
    _tool_actions = _eval_tools(
        owned, session_scope.direction_comp_of(session))
    _tool_admitted = _admit_tools(_tool_actions)
    if not any(a.usable for a in _tool_admitted):
        if any(a.usable for a in _tool_actions):
            # 判据放行但准入拒(执行通道未就绪形态)——禁混入判据拒桶
            counters['m7_5_reject_g1_not_admitted'] = \
                counters.get('m7_5_reject_g1_not_admitted', 0) + 1
        else:
            _m75_rejs = sorted({a.action for a in _tool_actions
                                if not a.usable})
            for _r in _m75_rejs:
                counters[f'm7_5_reject_{_r}'] = \
                    counters.get(f'm7_5_reject_{_r}', 0) + 1
            if not _m75_rejs:
                counters['m7_5_reject_none'] = \
                    counters.get('m7_5_reject_none', 0) + 1
    for _ta in _tool_admitted:
        log.info('[cw!][tools] tool=%s action=%s usable=%s reason=%s',
                 _ta.tool, _ta.action, _ta.usable, _ta.reason or '-')
    if any(a.usable for a in _tool_admitted):
        # 逐件产工具原子类(判据面同源纯函数按 owned 序首中;未知 usable
        # 动作 = 判据面扩容未同步原子类,禁猜交互)。
        from sr_od.application.currency_war.data.cw_synthesis import (
            recycle_qualified as _rq,
        )
        from sr_od.application.currency_war.kernel.cw_equip_env import (
            _privilege_base_name as _pbn,
        )
        _keys = list(getattr(session_scope.direction_comp_of(session),
                             'key_equips', None) or [])
        _rq_set = _rq(_keys)
        _priv_targets = {_pbn(k) for k in _keys if _pbn(k) is not None}
        for _ta in _tool_admitted:
            if not _ta.usable:
                continue
            _tgt = ''
            if _ta.action == 'furnace_single':
                _tgt = next((n for n in owned
                             if n != _ta.tool and n in _rq_set), '')
            elif _ta.action == 'privilege_upgrade':
                _tgt = next((n for n in owned if n in _priv_targets), '')
            else:
                counters['m7_5_atomic_unmapped'] = \
                    counters.get('m7_5_atomic_unmapped', 0) + 1
                continue
            if not _tgt:
                continue
            if _ta.tool == '冶金炉':
                _atom: CwAction = CwActionFurnaceUseParam(
                    target_kind='equip', item_name=_tgt)
            elif _ta.tool == '特权赋予卡':
                _atom = CwActionPrivilegeCardUseParam(
                    target_kind='equip', item_name=_tgt)
            else:
                counters['m7_5_atomic_unmapped'] = \
                    counters.get('m7_5_atomic_unmapped', 0) + 1
                continue
            out.append(Emitted(_atom, True, 'm7_5_tool_consume'))
    return out


# ============================================================ 第 7 步:节末凑息


def _step7_node_end_interest(session: StrategySession,
                             gs: GameState) -> list[Emitted]:
    """第 7 步节末凑息(22 号篇 §1 第 7 步;候选池 = 备战席 ∪
    场上无关角色〔来金族,用户裁定 2026-10-13〕)。

    触发 = 当前金位 < 利息线(saturation_line(cap_resolved);禁裸 50)。
    动作 = 卖 1★ 全额退件(评估器 'node_end_interest' 场景过滤)补缺口,
    卖到缺口闭合即止、不多卖一张(卖回量最小化):单动作循环下每帧
    首候选一张,卖出上报更新金位后下帧重评,金位 ≥ 利息线即停。空板守卫
    (deployed = 0 帧哑火)= 评估器 as-built 并入语义。本步卖出的退金
    由第 4 步入口统一复核(23 号篇契约 A)。

    升级变现序列在途抑制(11 号篇 §2 帧交错规则①):键在
    ∧ 变现候选尚存时本步零发出(同池候选竞争,变现优先);变现穷尽
    后竞争消失、本步恢复。

    金位读数门(23 号篇金位读数形态):账面失效帧无法判「金位 ≥
    利息线」→ 读数开店锚定(标记不动),下帧重评。
    """
    if _step3_liquidation_pending(session, gs):
        return []
    if state_of(gs).gold_ledger is None:
        return _open_shop_for_gold_read(session, gs)
    if gold_of(gs) >= saturation_line(cap_resolved_of_session(session)):
        return []
    _cands, _why = evaluate_sell_candidates(gs, 'node_end_interest')
    if not _cands:
        return []
    return _emit_sell_candidate(
        session, gs, _cands[0], reason='interest_prep',
        tag='interest_prep', counter='node_end_interest_sell')
