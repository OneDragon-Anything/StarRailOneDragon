"""cw4 备战决策入口(十段全扫工序)。

工序结构(判据正本 = strategy-docs/22_prep_screen.md §1;2026-10-17
迭代 design §2.2 重排——新增第 1 步商店随机态重开,其后顺延):每次回
到备战画面从第 0 步向下扫描,执行第一个满足条件的步骤并返回其动作,
下一帧重新扫描(单动作循环不变;回跳语义——腾位后回头点晶矿、买完牌
回头部署——在全扫下自然表达):

    第 0 步 溢出告警自救 → 第 1 步 商店随机态重开(信号在:清 handled
        标记 + 开店进店 + 清信号)→ 第 2 步 点开消耗品 → 第 3 步 晶矿
     → 第 4 步 升级检查(design §2.2:判据每帧重评,资格门全链同参
        消费 criteria/levelup;命中 → 凑金/发射)
     → 第 5 步 商店会话 → 第 6 步 部署调整 → 第 7 步 装备与工具
     → 第 8 步 节末凑息 → 第 9 步 出战

模块分工:买面/凑息/腾位的备战域动作发出点(dominance/M2/M4/M6
凑息分支)由店内会话(23 号篇)与卖出评估器(criteria/sell_candidates,
卖出场景注册表)承载;卖出场景统一消费 ``evaluate_sell_candidates``;
升级判据本体与发射资格门全链 = ``criteria/levelup``(11 号篇 §2 +
design §2.1 七道成员集单一源),本模块只做工序接线与发出组装。
部署/装备/工具判据单一源 = deploy_plan / cw_equip_wear_plan /
cw_equip_env(第 6/7 步只承载调用时机)。

``mandate.run_mandate`` 为测试面已登记函数(生产调用走本模块 emit)。
``truncate_frame_stable``(帧稳定截断动作发出器,词表正本 =
flow/action_exec.md §1)与 ``_ore_bench_free`` 等公共骨架——
bridge 与测试面在产消费。

晶矿第 3 步 = 垫件纯判断(无试错计数)。占席颜色→内容映射为待实机
证项,若立项需双倍审面(判据面 + 建档面)。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
from sr_od.application.currency_war.kernel.cw_economy import (
    cap_resolved_of_session,
    in_must_spend_zone,
    next_interest_line,
)
from sr_od.application.currency_war.kernel.cw_exec_state import BENCH_CAPACITY
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_entries_of,
    bench_free_slots,
    clear_shop_randomized_pending,
    deployed_rows_of,
    game_state_of,
    gold_of,
    level_of,
    max_units_of,
    node_kind_of,
    round_num_of,
    shop_randomized_pending_of,
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
    is_field_irrelevant_unit,
    is_ore_pad_unit,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.protection import (
    protection_membership,
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
#: 本常量为商店域校验的兼容单一源(备战域 EV pass 不在十段工序内),
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


# ============================================================ 上阵窗口适用范围(22 号篇 第 6 步)

#: 终局库成员并集(core ∪ shared 全线去重;纯终局件谓词的「终局库成员」
#: 分支——未锁定期按全库知识判定的数据面,22 号篇 第 6 步)。
_ENDGAME_LIBRARY_MEMBERS: frozenset[str] = frozenset(
    name
    for _comp in COMP_LIBRARY
    for name in (*_comp.core_chars, *(_comp.shared_chars or ())))


def _entry_window_open(gs: GameState, char_id: str) -> bool:
    """角色上线窗口判定(22 号篇 第 6 步;数据 = COMP_LIBRARY
    ``entry_signals`` 建表,缺行 fail 恒假)。

    查线顺序:锁定 → 仅锁定线的信号行;未锁定 → 全库任一含该角色的线
    (候选囤件窗口未到时照囤不上,窗口适用范围同样适用)。信号类闭集语义见
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
    """纯终局件窗口适用范围判定(22 号篇 第 6 步)。

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
    """部署动作发出点(第 0 步态 1 与第 6 步共用;选人/落位/对位单一源 =
    ``deploy_plan.deploy_plan_moves``——判据本体不改动,prep_pipeline
    22 号篇 §1 第 6 步)。

    ``window_scope`` = 是否施加上阵窗口适用范围:第 6 步 True(终局成员在
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
    """select_swap_plan 的 select_up 注入包装(第 6 步换人替补的上阵窗口
    适用范围——契约 D 部署换人行:替补受窗口适用范围覆盖,窗口未到的终局替补
    不可上 = 窗口适用范围自然结果,换人通道由过渡替补在产)。

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


# ============================================================ emit(十段全扫)


def emit(session: StrategySession,
         config: object, *,
         registry: DecisionV2Registry | None = None) -> list[Emitted]:
    """备战决策入口十段全扫(22 号篇 §1 工序 + 2026-10-17 迭代 §2.2
    重排;返回 Emitted 列表交桥截断)。

    决策输入 = 容器 game state 直读(黑板帧停用契约照旧)。每帧从第 0
    步向下扫描,首中段返回其动作序列(单动作循环取首项执行);全部不中
    ⇒ 第 9 步出战。步间调用:3.1 边界/标记/清单存储(session_scope)、
    3.2 卖出评估器(evaluate_sell_candidates,契约 D 场景参数化)。

    ``config`` = 调用方透传(现行十段无消费面;旧 ev_arm 实验因子随 EV
    pass 停用)。``registry`` = 上下文注册表(装备计划等级帽等消费注入)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )

    st = state_of(session)
    if getattr(st, 'cw4_counters', None) is None:
        st.cw4_counters = {}

    # M1″ seam 门写点·生产面(emit prologue;session 属性,值源 =
    # mandate.M1P_SEAM_VERIFIED 常量,出处与回滚路径见该常量注释;
    # 测试面写点 = run_mandate prologue,两面同值同源)。补点依据 =
    # 换人发射缝(emit_swap_redeploy)的对齐核对开闸常量早已置 True,
    # 写点此前残留测试面 prologue——生产 entry 面恒缺省 False,非空
    # 换人计划恒被 m1p_input_seam_pending 拦(C1 局 g_20261026_203023
    # 遥测实锤 m1p_input_seam_pending=1 ∧ m1p_fired=0;design §2.7
    # 执行形态要求组计划可发射)。
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        M1P_SEAM_VERIFIED,
    )
    st.cw4_m1p_seam_verified = M1P_SEAM_VERIFIED

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
    # k = 现行方向阵容(锁定线优先,未锁 = 过渡配方开局面;键面归一
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

    # —— 第 1 步:商店随机态重开(2026-10-17 迭代 design §2.2 第 1 步/
    # §2.4)——信号在 = 商店有未处理的随机态新牌面(含商业间谍偷入备战席
    # 的 3 张,用户裁定「很高的优先级」;置于溢出自救之后、资源动作之前):
    # 清 handled 标记 → 开店进店(入口观察读真牌面,会话循环正常评估)
    # → 清信号。信号写端 = 商业间谍升级回调(T-3 接线,cw_action_report/
    # level_up.py 升级生效时点);重开触发计数键 = §2.6③ 随机态闭环
    # 批跑取数口(商业间谍升级次数 ↔ 重开触发次数恒等式)。
    if shop_randomized_pending_of(gs):
        session_scope.clear_shop_handled(gs)
        clear_shop_randomized_pending(gs)
        st.cw4_counters['shop_randomized_reopen'] = \
            st.cw4_counters.get('shop_randomized_reopen', 0) + 1
        return [Emitted(CwActionOpenShopParam(),
                        True, 'step1_shop_randomized_reopen')]

    # —— 第 2 步:点开消耗品(书册卡 → 补给箱 → 星徽秘典;分支序 = 现行
    # 实体面段在案顺序)——弹窗由外循环画面分发接住,处理后回备战重新
    # 全扫(弹窗不是工序步骤)。
    _open_act = _consumable_open_action(gs)
    if _open_act is not None:
        return [_open_act]

    # —— 第 3 步:晶矿(22 号篇 §1 晶矿步)——
    _ore_out = _step2_ore(session, gs)
    if _ore_out:
        return _ore_out

    # —— 第 4 步:升级检查(design §2.2:判据每帧重评,无跨画面键;
    # 资格门全链 = criteria/levelup.upgrade_gate_verdict 两屏同参单一源。
    # 命中后凑金与发射:全链通过 → 单帧原子整批(实付上界 = 发射时授权
    # 值,授权不跨帧携带)+ 清 handled 标记;凑金域 → 凑金每帧一卖
    # (levelup_liquidate_prep 场景,排序键①费用带外②低星③金当量);
    # 凑金候选穷尽 → 整批推迟零动作等节点收入,拒因键
    # levelup_fund_line_defer)——
    # (函数名 _step3_level_up 沿用旧序号,重命名随工序 sweep 批统一。)
    levelup_actions: list[Emitted] = _step3_level_up(session, gs, registry)
    if levelup_actions:
        return levelup_actions

    # —— 第 5 步:商店会话(22 号篇 §1 商店会话步;契约 A)——
    # 入口先调解拦复核(判定函数本体 = criteria/shop_session);然后判标记
    # ≠ 当前节点号。满足 → 开店(备战侧决策性开店意图的唯一来源)。
    if _step4_shop_session_pending(session, gs):
        return [Emitted(CwActionOpenShopParam(), True, 'step4_shop_session')]

    # —— 第 6 步:部署调整(部署面判据照旧;调用时机在商店会话
    # 之后——「先逛店再统一部署」)——
    _deploy_out = _step5_deploy(session, gs, frame, levelup_actions)
    if _deploy_out:
        return _deploy_out

    # —— 第 7 步:装备与工具(工具判据 =
    # kernel/cw_equip_env.evaluate_tool_actions;调用位置固定为部署
    # 之后)——
    _equip_out = _step6_equip_tools(session, gs, registry)
    if _equip_out:
        return _equip_out

    # —— 第 8 步:节末凑息(22 号篇 §1 节末凑息步)——所有花费决策
    # 完成后的最终利息线检查(为买而卖在会话内,为息而卖在本步;息按节末
    # 金位结算,提前卖会被后续购买把金位吃回去)。
    _interest_out = _step7_node_end_interest(session, gs, registry)
    if _interest_out:
        return _interest_out

    # 形态⑥观测(纯观测零行为,fail-closed 期只记不判):target 空窗
    # ∧ 濒死带 ∧ 域外 ∧ 持金 ∧ 本帧零金消费——金滞留入败局的形态暴露
    # (键名申报源 = supply_arbitration_design §5.1 terminal_targetless_
    # idle;载体适用范围随工序重排收窄 = 到达第 8 步之后的帧,实体面/开店/
    # 部署/装备帧提前返回不入键;到达本段的帧无 LevelUp/OpenShop 类
    # 动作,旧动作面条件恒真,申报)。
    if (gold_of(gs) > 0
            and session_scope.direction_comp_of(session) is None
            and not in_must_spend_zone(gold_of(gs), session)
            and (predicates.p1_blood_floor(gs)
                 or predicates.p2_blood_floor(gs))):
        st.cw4_counters['terminal_targetless_idle'] = \
            st.cw4_counters.get('terminal_targetless_idle', 0) + 1

    # —— 第 9 步:出战(以上全部步骤无动作;备战环唯一完成态)——
    # 出战前置动作发出点机制保留在 bridge(出战就绪帧短路本 emit,机制出处 =
    # strategy-docs/26 号篇;本迭代零改动);受限商店访问帧不受会话标记
    # 覆盖(契约 A 豁免条款,前置位承载)。
    return [Emitted(CwActionStartBattleParam(), True, 'battle')]


# ============================================================ 第 0 步:溢出告警自救


def _consumable_open_action(gs: GameState) -> Emitted | None:
    """备战席消耗品点开动作(第 1 步主体;第 0 步态 2 复用)。

    触发 = bench 槽位 kind ∈ bookcard/supply_box/tome(现行容器
    BenchSlot.kind 判定);点开顺序 = 书册卡 → 补给箱 → 星徽秘典
    (现行实体面分支序,入口清场旧全局序在案)。星徽秘典占席 = 待实机
    证实项(点开出路对其防御性纳入,22 号篇 第 2 步)。动作参数
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
    态 1 上阵安置(非卖出,不受该守卫覆盖;22 号篇 第 0 步申报)。
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
    """第 3 步晶矿(22 号篇 §1 第 3 步;现行晶矿读口
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


# ============================================================ 升级检查(工序第 4 步)


def _bench_liquid_gold(gs: GameState) -> int:
    """攒批资金的活期分量(11 号篇 §2 攒批口径):备战席
    **非线内非保护 1★ 活期卡**退金合计(1★ 全额退口径)。

    bench-only 口径——与契约 D 升级变现候选池(bench∪场上无关角色)
    是两个分立维度:场上无关角色 1★ 退金**不计入**攒批基数(保守侧,
    两处口径分立维护非同源,11 号篇 §2 攒批资金口径行)。
    线内判定 = 卖出侧线内身份集(``sell_line_membership``:锁定线成员
    ∨ 未锁定期候选 top3 成员——「卖自己人凑升级金不在语义内」)。
    保护集分支(统一保护集 design §2.5-5 攒批资金联动申报):变现候选池
    过滤保护集后保护件在偏好臂下不可变现,攒批基数同步剔除——否则
    「预授权误发 → 键滞留 → 刷新预留被压制至节点末」风险链 reopening。
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
    protection = protection_membership(gs, state_of(gs))
    total = 0
    for u in bench_units_of(gs):
        name = str(u.char_id or '')
        star = int(u.star or 1)
        if name and name not in line and name not in protection \
                and refund_full_star_ok(star, bench_char_cost(u, gs)):
            total += sell_refund(star, bench_char_cost(u, gs))
    return total


def _levelup_fund_line_ok(gs: GameState, session: StrategySession,
                          gold: int, clicks: int, click_cost: int) -> bool:
    """升级资金线门装配口(11 号稿 §2 资金线门;单一装配位)。

    现金口径单门:花后金 = 现金 − 整批成本,下界单一源 =
    ``saturation_line(cap_resolved)``(session resolved 链;活期退金
    **不进放行算术**——发射分支不消费活期资产,旧「现金+活期−批」
    预支算式与按臂分档的利息线差额保留分支随批删除)。豁免两支由
    :func:`criteria.levelup.levelup_fund_gate` 体内自判(终局域末战
    ALL IN / 买断制 cap=0 ⇒ 下界 0 恒过)。

    契约核验(前提恒真行,纪律接线;失败 = 保守拒)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        cap_resolved_of_session,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        contracts,
        levelup,
    )
    if not contracts.ensure_contract(
            ('levelup', 'fund_line_gate'),
            contracts.ContractCtx(), state_of(session).cw4_counters):
        return False
    return levelup.levelup_fund_gate(gs, session, gold, clicks, click_cost,
                                     cap_resolved=cap_resolved_of_session(session))


def _step3_level_up(session: StrategySession, gs: GameState,
                    registry: DecisionV2Registry | None) -> list[Emitted]:
    """升级检查步(工序第 4 步;11 号稿 §2 单判据三分派 + 升级执行:
    判据每帧重评,无跨画面键)。

    资格门全链判定单一源 = :func:`criteria.levelup.upgrade_gate_verdict`
    (与商店会话升级意图出口两屏同参消费,本函数零内联门)。
    命中后凑金与发射:

    - **全链通过** → 发购买经验整批,**单帧原子**(实付上界 = 发射时
      授权值;授权不再跨帧携带——「买一半」形态由发射原子性消解)+
      **清 handled 标记**(升级前若经会话正常收工置位,升级后概率档
      已变,本节点找牌与刷新判据需重评——非商业间谍路径的重开通道);
    - **凑金域**(花后破线 ∧ 凑金可达,``gold_short``)→ 凑金:
      ``levelup_liquidate_prep`` 场景每帧一卖、重扫续卖(候选/锁定阵容
      外任意星级可卖,场景参数 ``one_star_refund_only`` False;排序键
      ①费用带外先卖②低星先③金当量兜底,场景级覆盖见评估器)。凑金
      目标 = 保线缺口闭合:凑至「现金 − 批 ≥ saturation_line」发射;
    - **凑金候选穷尽** → 整批推迟(帧零动作,拒因键
      ``levelup_fund_line_defer``——资金面拒因统一键;新触发臂均为
      非义务账,穷尽 = 真不可达,推迟为正确语义);
    - 其余 defer(门拦/凑金不可达)/未命中 → 零动作。

    血本位局(XP 以血支付):金凑金与变现步不适用(变现卖出对血支付
    零贡献)——经验批支付门过即发射(单帧原子同款;R-1 币种通式:
    血余额 ≥ 整批血成本 = 支付能力检查);不足 = 零购买(攒钱模式
    = 等节点血收入)。

    (函数名 ``_step3_level_up`` 沿用旧工序序号,重命名随工序 sweep 批
    统一;本步现位 = 工序第 4 步。)
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
    # 失效帧无法评估凑金/触发面 → 读数开店锚定,标记不动;账面宿主 =
    # 容器态(state_of(gs),与会话标记/清单同宿主)。
    if state_of(gs).gold_ledger is None:
        return _open_shop_for_gold_read(session, gs)

    # ===== 资格门全链判定(两屏同参单一源)=====
    verdict, arm_key, clicks, click_cost = levelup.upgrade_gate_verdict(
        gs, session, registry=registry, counters=counters)

    if verdict == levelup.GATE_EMIT:
        # 发射 = 单帧原子整批(实付上界 = 发射时授权值;授权不跨帧)
        # + 清 handled 标记(升级后概率档已变,本节点找牌与刷新判据
        # 需重评)。
        counters['levelup_batch_emitted'] = \
            counters.get('levelup_batch_emitted', 0) + 1
        # 升级发出失效/伴生钩子(读数协议②:升 9 级成长基金独立
        # 失效;节节高升任意升级 +1 伴生入金)。
        shop_sess.note_levelup_emission(gs, level_of(gs) + 1)
        session_scope.clear_shop_handled(gs)
        return [Emitted(CwActionLevelUpParam(
            cost=int(click_cost), clicks=max(1, clicks),
            auth_basis=arm_key), True, f'step3_levelup_batch:{arm_key}')]
    if verdict != levelup.GATE_GOLD_SHORT:
        # 未命中 / 资格门拦(拒因计数已由判定函数写入)= 零动作。
        return []

    # ===== 凑金(凑金域;每帧一卖、重扫续卖,天然收敛)=====
    # 主路径 = 评估器升级变现场景(排序键①费用带外②低星③金当量,
    # 场景级覆盖)。凑金穷尽 → 整批推迟(非义务账无兜底豁免——穷尽 =
    # 真不可达,推迟零动作等节点收入)。
    cands, _why = evaluate_sell_candidates(gs, 'levelup_liquidate_prep')
    if cands:
        out = _emit_sell_candidate(
            session, gs, cands[0], reason='levelup_liquidate',
            tag='levelup_liquidate_sell',
            counter='levelup_liquidate_sell')
        if out:
            return out
    counters['levelup_fund_line_defer'] = \
        counters.get('levelup_fund_line_defer', 0) + 1
    return []


def _step3_liquidation_pending(session: StrategySession,
                               gs: GameState,
                               registry: DecisionV2Registry | None
                               ) -> bool:
    """升级判据命中判定(节末凑息步的抑制条件;2026-10-17 迭代 T-4
    载体迁移,design §2.5①:预授权键读删除,条件改升级资格门同帧重评
    ——判据命中(非 MISS 结论,含金量不足攒批待付帧与各资格门拒帧)
    即凑金在途,凑息让位;未命中帧凑息照常。判定单一源 =
    :func:`criteria.levelup.upgrade_gate_verdict`(counters 不传 = 静默
    重评,拒因计数归升级执行步,本判定零计数副作用)。

    抑制面拓宽申报(design §2.5① 预注册):键载体时代的抑制面 = 授权态
    (键在)∧ 缺口未闭;判据载体覆盖全部命中帧——等级帽/奖励帧拦截等
    非金拒帧也进抑制面(命中即升级议题在册,凑金优先于凑息),抑制面
    拓宽、方向保守。凑金候选尚存与否由凑金步内评估器自然收敛,本判定
    零独立候选口径。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup,
    )
    verdict, _arm, _clicks, _ccost = levelup.upgrade_gate_verdict(
        gs, session, registry=registry)
    return verdict != levelup.GATE_MISS


# ============================================================ 第 5 步:商店会话入口


def _open_shop_for_gold_read(session: StrategySession,
                             gs: GameState) -> list[Emitted]:
    """金位读数开商店(22 号篇 §1 第 5 步前置/第 4/8 步读数门;
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
    """商店会话步触发判定(工序第 5 步;22 号篇 §1 第 5 步;契约 A)。

    入口序:解拦复核(读数分支开店不清标记——锚定后标记门
    即关,下帧复核继续)→ 解拦分支清标记 → 标记 ≠ 当前节点号判定
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


# ============================================================ 第 6 步:部署调整


def _step5_deploy(session: StrategySession, gs: GameState,
                  frame: MandateFrame,
                  levelup_actions: list[Emitted]) -> list[Emitted]:
    """部署调整步(工序第 6 步;22 号篇 §1 第 6 步;部署面判据照旧,
    判据本体不改动,仅调用时机移到商店会话之后)。

    动作生成消费部署选人纯函数(统一让位优先级迭代 3.1 结构抽取,
    判据零改动,契约 = changes/2026-10-29-unified-priority/details/
    acquisition-and-sell.md §1):先经 ``mandate.select_deployment``
    求部署定型名集(目标态),目标态 == 现板 = 部署已定型零动作;
    diff 非空帧按下列三臂发射(发射器与臂内判据零改动,回归由现行
    部署测试守)。行为申报:动作序列与定型收敛逐位同旧;定型帧不再
    触达换阵发射器——其计划空分键(m1p_plan_empty 族/abstain 键)与
    「窗口拦全」帧的 deploy_emit_held 分键不再写入(遥测覆盖面收窄
    至有 diff 帧,键语义不变);cw4_m1p_*_pending 在定型帧同步复位
    (与现行发射器无发射分支的帧级复位语义一致)。

    结构(判据本体与 run_mandate 部署段同源;升级后补部署经**下帧
    M1 空槽补位结构性收敛**——十段全扫单动作循环下第 4 步命中即
    emit 返回,升级帧到不了本步;下帧全扫 deploy_vacancy 更新后 M1
    以零卖出成本接管,「卖出不可逆 > 等一帧」的原语义由该结构承载,
    不设独立 M1′ 分支):
    - M5 开局配方(开局帧 round_num ≤ 1 ∧ 板空 ∧ bench 有件);
    - M1 空槽凑人数补位(deploy_vacancy > 0;任意合法单位上阵优于空槽,
      P24 残余补部署——升级开新 vacancy 的补部署也经本分支);
    - M1″ 板满换阵补部署(m1p 换人;替补受上阵窗口适用范围覆盖)。

    上阵窗口适用范围(用户裁定 2026-10-12):终局成员在其上线窗口前不上阵
    ——纯终局件谓词 + 窗口判定见 :func:`_deploy_window_blocked`;过渡∩
    终局重叠件按过渡成员正常上阵;全局累积型例外 = entry_signals 的
    always_on 信号类。
    """
    # 部署定型名集一次求取(生产装配 = 容器/session 读口现取;三臂门
    # 与选人判据核心 = mandate.select_deployment 纯函数单一源,本步
    # 只承载动作发射)。
    prep = mandate.assemble_prep_context(session, gs, frame)
    target = mandate.select_deployment(frame, prep)
    current = {d.char_id for d in frame.deployed
               if d is not None and d.char_id}
    if target == current:
        st = state_of(session)
        st.cw4_m1p_arm_pending = None
        st.cw4_m1p_plan_pending = None
        return []
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
    # M1″ 板满换阵(m1p 换人;up 候选经窗口适用范围包装注入)。defer_actions
    # 输入在十段全扫下单动作循环下结构性恒空(第 4 步命中即 emit 返回,
    # 升级帧到不了本步)——同帧升级推迟换人的语义由结构承载:升级帧
    # 第 4 步先行返回 + 下帧 M1 空槽补位以零卖出成本接管(卖出不可逆
    # > 等一帧)。
    if not any(isinstance(e.action, (CwActionDeployMoveParam,
                                     CwActionSellDeployedParam))
               for e in out):
        out.extend(mandate.emit_swap_redeploy(
            frame, session, gs,
            select_up=_make_windowed_select_up(session, gs),
            defer_actions=levelup_actions))
    return out


# ============================================================ 第 7 步:装备与工具


def _step6_equip_tools(session: StrategySession, gs: GameState,
                       registry: DecisionV2Registry | None) -> list[Emitted]:
    """装备与工具步(工序第 7 步;22 号篇 §1 第 7 步)。

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


# ============================================================ 第 8 步:节末凑息


#: 凑息保护档阻断观测键(统一保护集 design §2.3 凑息语义;分键写入端
#: = 本写点单一源,判读侧禁另立同义键)。
INTEREST_PROTECTED_BLOCK_KEY: str = 'interest_round_protected_block'


def _protected_member_blocks_interest(gs: GameState, gap: int) -> bool:
    """凑息保护档反事实支存在性(design §2.3 观测键第三合取):凑息
    候选池同域(备战席 ∪ 场上无关角色,节末凑息无店面)内存在被保护集
    排除、退金 ≥ 缺口的 1★ 成员——「若无保护本可跨档」的反事实存在性。

    枚举域钉死(design §2.3):池族 = 节末凑息同域(备战席全量 +
    场上无关角色谓词单一源),星级 = 1★(与凑息资格面
    one_star_refund_only 同域,不外推);判定面 = 池族 ∧ 保护身份 ∧
    「退金 ≥ 缺口」三条分支,不重放常规面其余资格门(设计定死粒度:与
    第二合取同用同一「退金 ≥ 缺口」筛选)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        bench_char_cost,
        sell_refund,
    )
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import Unit
    protection = protection_membership(gs, state_of(gs))

    def _viable(u: Unit) -> bool:
        name = str(u.char_id or '')
        return (bool(name) and name in protection
                and int(u.star or 1) == 1
                and sell_refund(1, bench_char_cost(u, gs)) >= gap)

    for slot in bench_entries_of(gs):
        if predicates.item_slot_unsellable(slot):
            continue
        u = bench_slot_unit(slot)
        if u is not None and _viable(u):
            return True
    front, back = deployed_rows_of(gs)
    for row_units, row in ((front, 'front'), (back, 'back')):
        for u in row_units:
            if u is not None and _viable(u) \
                    and is_field_irrelevant_unit(gs, u, row):
                return True
    return False


def _step7_node_end_interest(session: StrategySession,
                             gs: GameState,
                             registry: DecisionV2Registry | None
                             ) -> list[Emitted]:
    """节末凑息步(工序第 8 步;22 号篇 §1 第 8 步;候选池 = 备战席 ∪
    场上无关角色〔来金族,用户裁定 2026-10-13〕)。

    触发 = 存在「单件退金 ≥ 到下一利息档缺口」的资格候选(缺口单一源
    = kernel ``next_interest_line``;跨不了档的卖出零利息收益,一件不
    卖——金 10~19 区间卖光 bench 也不涨息,纯亏资产,[11] 卖回量最小
    化的前件)。动作 = 取退金 ≥ 缺口中退金最小的 1★ 全额退件(评估器
    'node_end_interest' 场景过滤),逐帧单张:跨档后下帧按新金位重评,
    缺口重算自然收敛。空板守卫(deployed = 0 帧哑火)= 评估器 as-built
    并入语义。本步卖出的退金由第 5 步入口统一复核(23 号篇契约 A)。

    升级凑金在途抑制(11 号篇 §2 帧交错规则①):升级判据命中帧本步
    零发出(同池候选竞争,凑金优先)。抑制载体 = 资格门判据同帧重评
    (2026-10-17 迭代 T-4,design §2.5①;预授权键读已随键退役删除,
    抑制面拓宽申报见 :func:`_step3_liquidation_pending`)。

    金位读数门(23 号篇金位读数形态):账面失效帧无法判「缺口与候选
    退金」→ 读数开店锚定(标记不动),下帧重评。

    观测键(统一保护集 design §2.3 凑息语义):无可行件帧按三合取
    「非零缺口 ∧ 常规合格集退金 ≥ 缺口为空 ∧ 被排除保护成员存在退金
    ≥ 缺口者」计数 ``interest_round_protected_block``——凑息在「全场
    保护档」帧的成功率损失量化面(用户裁定:候选/锁定成员不凑息,
    结构性少 1-2 金/轮由此键观测)。
    """
    if _step3_liquidation_pending(session, gs, registry):
        return []
    if state_of(gs).gold_ledger is None:
        return _open_shop_for_gold_read(session, gs)
    _gold = gold_of(gs)
    _line = next_interest_line(_gold, cap_resolved_of_session(session))
    if _line is None:
        return []
    _gap = _line - _gold
    _cands, _why = evaluate_sell_candidates(gs, 'node_end_interest')
    from sr_od.application.currency_war.kernel.cw_economy import (
        bench_char_cost,
        sell_refund,
    )
    _feasible: list[tuple[int, int]] = []
    for _i, _c in enumerate(_cands):
        _r = sell_refund(1, bench_char_cost(_c.unit, gs))
        if _r >= _gap:
            _feasible.append((_r, _i))
    if not _feasible:
        # 常规合格集(退金 ≥ 缺口)为空——含「合格候选全保护档」帧
        # (评估器候选整体为空的形态,_feasible 随空候选平凡为空):
        # 观测键三合取(统一保护集 design §2.3)= 非零缺口 ∧ 无可行件
        # ∧ 被排除保护成员存在退金 ≥ 缺口者(反事实支,枚举域见
        # _protected_member_blocks_interest)。
        if _gap > 0 and _protected_member_blocks_interest(gs, _gap):
            _st = state_of(session)
            _ct = _st.cw4_counters
            if not isinstance(_ct, dict):
                _ct = {}
                _st.cw4_counters = _ct
            _ct[INTEREST_PROTECTED_BLOCK_KEY] = \
                _ct.get(INTEREST_PROTECTED_BLOCK_KEY, 0) + 1
        return []
    _r, _best_i = min(_feasible)   # 退金最小;并列取评估器让位序靠前
    return _emit_sell_candidate(
        session, gs, _cands[_best_i], reason='interest_prep',
        tag='interest_prep', counter='node_end_interest_sell')
