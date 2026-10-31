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
    CwActionMoveUnitParam,
    CwActionObsParam,
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
    sell_line_membership,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
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
_CONTINUABLE: tuple[type, ...] = (
    CwActionLevelUpParam,
    # 重观察动作(in_place = 当前画面环内重观察):零迁移/零坐标,满足
    # 「可续」语义;现役发出面 = 备战决策环无动作可发帧(计划前置步
    # 无进展帧/空序列兜底)——单一动作级发出,序列续发面为零。登记
    # 义务(动作发出器增补条目须回契约改版,flow/action_exec.md §1)
    # 由此声明;分类表契约改版随部署统一批(D5-1)统一回正本。
    CwActionObsParam,
)
#: 条件续(bench 索引结构恒稳 + 名-槽一致性复检;board 空位/星级合成按
#: 前序动作累积静态推出,推不出即截断——契约 §3.2;CwActionCollectOreParam
#: 行 = 条件:常态可续,末批可能掉箱后截断)
_CONDITIONAL: tuple[type, ...] = (
    CwActionSellBenchParam, CwActionSellDeployedParam, CwActionDeployMoveParam,
    CwActionMoveUnitParam,                      # 统一拖动(部署统一批;bench 源/目标槽复检同 SellBench/DeployMove 形)
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
            if isinstance(a, CwActionMoveUnitParam):
                # 统一拖动复检(bench 源槽名-槽一致性;场上域无 bench 复检面):
                # 源 bench 槽发出后保守释放(交换回填/清空两形态后续引用
                # 均按新观察重建,续发不依赖回填位置);目标 bench 槽登记
                # 占用(空槽落位/交换占位均变占用态)。
                if slots is not None and a.src_domain == 'bench' \
                        and a.src_slot not in slots:
                    _count('emitter_conditional_truncated')
                    return _cut()
                out.append(a)
                if slots is not None:
                    if a.src_domain == 'bench':
                        slots.discard(a.src_slot)
                    if a.dst_domain == 'bench':
                        slots.add(a.dst_slot)
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
    """告警帧态 1 上阵安置动作发出点(部署统一批丁收编后的专用执行路径,
    unified-deploy-order §4 entry 备战工序部署面行 D3-4:告警帧常规搜索
    跳过,态 1 上阵腾槽 = 专用路径——bench 真单位直落场上空槽(腾 bench
    席),载体 = 统一拖动;窗口豁免照旧(上阵纯为腾槽保命,告警解除后
    下轮全扫恢复常规部署)。

    选人 = bench 扫描序(占位件/板上同名剔除;cap 有空位即态 1 前提)
    ——告警帧的救援语义只求确定性腾槽,排序质量无诉求(旧七桶序随选人
    族收编退役);落位 = ``deploy_plan.deploy_slot_plans`` 单一源(排
    路由 + 前排保证 + 空槽选择)。``window_scope`` 形参保留(恒不拦:
    态 1 豁免语义的显式载体,防未来调用面误接窗口过滤)。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_entries_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
        _slot_cid,
        deploy_slot_plans,
    )
    bench = bench_entries_of(state)
    on_board = set(frame.deployed_names)
    # 选人:bench 真单位(占位件经解包口自然剔除)∧ 名不在板上(同名
    # 去重;未识别 char_id='' 恒不在 on_board = 旧「照旧上」fail-open)。
    up_idx = [i for i, b in enumerate(bench)
              if bench_slot_unit(b) is not None
              and _slot_cid(b) not in on_board]
    if not up_idx:
        return
    _comp = getattr(state_of(session), 'target_comp', None)
    for bi, row, slot in deploy_slot_plans(bench, up_idx, _comp, state):
        out.append(mandate.Emitted(
            CwActionMoveUnitParam(
                src_domain='bench', src_slot=int(bi),
                dst_domain=row, dst_slot=int(slot),
                reason='m0_self_rescue_deploy'),
            True, tag))


# (select_swap_plan 的 select_up 注入包装 _make_windowed_select_up(第 6 步
#  换人替补的上阵窗口适用范围)已随部署统一批丁收编删除:第 6 步切差分
#  执行器,窗口谓词过滤进搜索段 0 枚举硬约束(unified-deploy-order §4
#  entry 备战工序部署面行;谓词本体 _deploy_window_blocked 保留为唯一源)。)


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
    # k_members 读口 = 统一线内名单(单一准入 §2.1:候选 ∪ 配方 ∪ 锁定线
    # 并集;换源不消亡,保留面消费 = 溢出告警门卖出装配/金需求侧
    # cheapest_member_cost)。复用阶段 1 成员判定函数 sell_line_membership,
    # 禁手搓第二份名单(旧读口 predicates.line_members(direction_
    # comp_of) 已随换源退役——方向读口回答「现行方向是谁」,P1 锁定局
    # 看不见配方成员即其名单语义缺陷)。
    k_members = tuple(sorted(sell_line_membership(gs)))
    # K 空窗回退(部署围栏目标供给;回退单一源 = cw_intention,与商店域
    # 同源消费,禁复制兜底逻辑;ist 缺失 = 意向供给缺帧,保守侧不回退)。
    # 空窗判定 = 名单真空(未锁定 ∧ 候选/配方全空);旧「无方向」判定
    # 随 direction 读口换源退役。
    if not k_members:
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

    # —— 前置步:计划游标逐帧消化(第 0 步溢出自救后新插;roster-
    #    plane1-union design §2.2 第 4 项执行端 + 用户裁定补录「跨画面
    #    计划变量终版」:商店决策一次定型,备战照单执行零重验)——
    # 槽在期间本步优先于第 1-9 全部步(含第 5 步开店与第 9 步出战——
    # 计划未完成不出战);被第 0 步自救抢占的帧本步不运行(告警帧零
    # 计划观察,DF-7:不累加也不清零卡死计数)。
    _plan_out = _step_yield_plan(session, gs)
    if _plan_out is not None:
        return _plan_out

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
    # 命中后发射:全链通过 → 单帧原子整批(实付上界 = 发射时授权
    # 值,授权不跨帧携带)+ 清 handled 标记;金不足(花后破线)→
    # 整批推迟零动作等节点收入,拒因键 levelup_fund_line_defer
    # (用户裁定 2026-10-30:不存在升级卖牌凑金——保持最大压牌库,
    # 钱够了再升)——
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
    _interest_out = _step7_node_end_interest(session, gs)
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
    # 适用范围;选人 = bench 扫描序腾槽语义,发射器内自带空候选短路)。
    if frame.deploy_vacancy > 0:
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


# ============================================================ 前置步:计划游标(阶段 3)


def _yield_plan_fail(st, counters: dict, plan) -> None:
    """计划失败出口③(design §2.2 第 4 项执行端:V 不在场/卖失败/级联
    卡死三态同款)——清槽 + X 路径失败标记置位 + 恢复扫描;下轮商店重评
    走 bench 件路径或机会清单(标记消费 = shop 统一获取让位评估排除
    场上件 victim,PV-8)。

    计数键按计划语境分键(观测键族「执行失败」;语境写入时定格):
    席位 → yield_plan_failed_priority_insufficient / 纯金 →
    yield_plan_failed_priority_insufficient_gold。
    """
    st.yield_plan = None
    st.x_path_failed = True
    _key = ('yield_plan_failed_priority_insufficient'
            if plan.context == 'seat'
            else 'yield_plan_failed_priority_insufficient_gold')
    counters[_key] = counters.get(_key, 0) + 1


def _step_yield_plan(session: StrategySession,
                     gs: GameState) -> list[Emitted] | None:
    """前置步:计划游标逐帧消化(工序第 0 步后新插;总纲 design §2.2
    第 4 项执行端 = 照计划操作零重验,逐帧消化步骤序列)。

    - 槽空/节点戳失效 → 返回 None(扫描正常推进);
    - ① 取下一未完成步骤:**卖步骤**(目标 V 已不在场/席 = 执行失败
    走③;在场/席 → 发 SellDeployed/SellBench〔按 name 现读落位分派〕,
    issued 位置位待下帧对账;issued ∧ 目标仍在原域 = 卖出执行层失败
    走③)/**驱板步骤**(T 名集覆盖判定,缺位者从 bench 上场——本阶段
    用现行 deploy_plan 落位算术(deploy_row_pref + 空槽选择),统一
    拖动/交替重观察属部署统一批;卡死检测简化版 = 连续 2 帧覆盖数
    不增〔含无动作帧,S7-9〕→ 失败出口③);
    - ② 序列空 → 清槽 → 返回 None 扫描继续(**开店 = 非序列步骤**
    〔SF-10〕,由第 5 步常规机制发);
    - ③ 执行失败 → :func:`_yield_plan_fail`(清槽 + 标记 + 按语境
    记键)→ 恢复扫描;
    - 驱板步骤无动作可发帧(缺位者不在 bench 等)→ CwActionObsParam
    (in_place 环内重观察)——扫描不前进,卡死计数照常累加。

    **零重验/零搜索**(用户裁定「跨画面计划变量终版」:备战执行零
    搜索——T 已定型,差分与落位是执行算术):select_deployment/
    assemble_prep_context 等搜索面零调用;卖步骤 = 名在场性现读 +
    坐标换算;驱板步骤 = 名集覆盖比对 + 落位算术。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
        effective_node_pos,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
        YieldPlan,
    )
    st = state_of(gs)
    plan: YieldPlan | None = st.yield_plan
    if plan is None:
        return None
    # 节点戳双保险(同 shop_handled 形态:重置表为主,戳不等 = 跨节点
    # 残留失效清槽)。
    if plan.node_stamp is None or plan.node_stamp != effective_node_pos(gs):
        st.yield_plan = None
        st.cw4_counters['yield_plan_stamp_mismatch'] = \
            st.cw4_counters.get('yield_plan_stamp_mismatch', 0) + 1
        return None
    counters: dict = st.cw4_counters
    front, back = deployed_rows_of(gs)
    _board_names = {str(d.char_id or '') for d in (*front, *back)
                    if d is not None and d.char_id}
    _bench_names = {str(u.char_id or '') for u in bench_units_of(gs)
                    if u is not None and u.char_id}
    while plan.cursor < len(plan.steps):
        step = plan.steps[plan.cursor]
        if step.kind == 'sell':
            _on_board = step.name in _board_names
            _on_bench = (not _on_board) and step.name in _bench_names
            if _on_board or _on_bench:
                if step.issued:
                    # 上帧已发出 ∧ 目标仍在原域 = 卖出执行层失败 → ③。
                    _yield_plan_fail(st, counters, plan)
                    return None
                step.issued = True
                counters['yield_plan_step'] = \
                    counters.get('yield_plan_step', 0) + 1
                mandate.record_round_sold(session, gs, step.name)
                if _on_board:
                    _didx = _deployed_idx_by_name(gs, step.name)
                    if _didx is None:
                        # 名在场但槽位对位失配(陈旧帧)→ fail-closed 走③。
                        _yield_plan_fail(st, counters, plan)
                        return None
                    return [Emitted(
                        CwActionSellDeployedParam(deployed_idx=_didx),
                        True, 'yield_plan_sell')]
                _bidx = mandate._bench_container_idx_by_compact(
                    gs, _bench_compact_idx(gs, step.name))
                if _bidx is None:
                    _yield_plan_fail(st, counters, plan)
                    return None
                return [Emitted(
                    CwActionSellBenchParam(bench_idx=_bidx,
                                           reason='yield_plan_sell'),
                    True, 'yield_plan_sell')]
            # 目标已不在场/席:未发 = 计划失效(V 不在场形态)→ ③;
            # 已发 = 卖出已生效 → 步骤完成推进。
            if step.issued:
                plan.cursor += 1
                continue
            _yield_plan_fail(st, counters, plan)
            return None
        # deploy 步骤(阶段 5/6 差分执行器驱动,§3.5 D8-1 定稿:拖动与
        # 重观察交替 + 完整卡死检测):
        # - 上帧已发拖动(pending_reobserve)→ 本帧发 obs(in_place)
        #   环内重观察(观察帧对账:自上报推演 vs 实读板面);
        # - 每帧先判进展(已就位名字数——名+排+星全对):增 → 清零;
        #   连续 2 次重观察不增(含无动作帧,禁挤/未知件占目标槽形态
        #   也计入)→ 级联卡死 → 失败出口③;
        # - T 已就位(diff 空)→ 步骤完成推进;diff 非空 → 发差分
        #   首动作(统一拖动/换星直卖),pending_reobserve 置位;
        # - 无动作可发帧(缺位者不在 bench/容量矛盾)→ 发 obs
        #   in_place 重观察,扫描不前进,卡死计数照常累加(下帧再计
        #   一次 = 出口)。
        from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
            deploy_diff,
        )
        _t = plan.target_board or {}
        if plan.pending_reobserve:
            plan.pending_reobserve = False
            return [Emitted(CwActionObsParam(scope='in_place'),
                            True, 'yield_plan_reobserve')]
        _settled = deploy_diff.settled_count(gs, _t)
        if _settled > plan.progress_mark:
            plan.progress_mark = _settled
            plan.stall_frames = 0
        else:
            plan.stall_frames += 1
            if plan.stall_frames >= 2:
                # 连续 2 次重观察后 diff 无进展 → 级联卡死 → ③。
                _yield_plan_fail(st, counters, plan)
                return None
        if deploy_diff.diff_settled(gs, _t):
            plan.cursor += 1
            continue   # T 已就位 → 步骤完成(序列尽则下方清槽)
        _actions = deploy_diff.deploy_diff_actions(gs, _t)
        if not _actions:
            # 无动作帧:in_place 重观察,扫描不前进,卡死计数已累加。
            return [Emitted(CwActionObsParam(scope='in_place'),
                            True, 'yield_plan_hold')]
        plan.pending_reobserve = True
        counters['yield_plan_step'] = \
            counters.get('yield_plan_step', 0) + 1
        return [Emitted(_actions[0], True, 'yield_plan_deploy')]
    # ② 序列空 → 清槽 → 扫描继续(开店由第 5 步常规机制发,SF-10)。
    st.yield_plan = None
    counters['yield_plan_completed'] = \
        counters.get('yield_plan_completed', 0) + 1
    return None


def _bench_compact_idx(gs: GameState, name: str) -> int | None:
    """bench 紧缩占席序下标 → 名对位(缺位者/目标名的现读定位;陈旧
    帧名不在席 = None)。身份解包 = ``bench_slot_unit`` 统一读口。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    for _compact, slot in enumerate(bench_entries_of(gs)):
        _u = bench_slot_unit(slot)
        if _u is not None and str(_u.char_id or '') == name:
            return _compact
    return None


def _deployed_idx_by_name(gs: GameState, name: str) -> int | None:
    """场上名 → deployed 槽位表下标(前排 0-3/后排 4+;场上同名唯一性
    不变量下首中即真;不在场 = None)。"""
    _d = mandate._deployed_container_idx(
        gs, next((u for u in _deployed_units_of(gs)
                  if str(u.char_id or '') == name), None))
    return _d


def _plan_slot_for(gs: GameState, session: StrategySession,
                   compact_idx: int, name: str) -> tuple[str | None, int]:
    """驱板步骤的落位算术(现行 deploy_plan 机制单一源复用:
    ``deploy_slot_plans`` 的排路由 + 前排保证 + 空槽选择——本阶段零
    搜索执行算术,统一拖动属部署统一批)。

    返回 (row, slot);排容量不可得(两排满)→ (None, 0) = 无动作帧
    (交卡死计数)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
        deploy_slot_plans,
    )
    _comp = getattr(state_of(gs), 'target_comp', None)
    _plans = deploy_slot_plans(bench_entries_of(gs), [compact_idx],
                               _comp, gs)
    if not _plans:
        return None, 0
    _bi, _row, _slot = _plans[0]
    return _row, int(_slot)


def _emit_sell_candidate(session: StrategySession, gs: GameState,
                         cand: SellCandidate, *, reason: str, tag: str,
                         counter: str) -> list[Emitted]:
    """卖出候选动作发出点(第 0/2/7 步共用;评估器候选 → 动作)。

    坐标换算:评估器候选 idx = 紧缩占席序下标(bench 支)→ 容器槽位表
    下标(动作参数坐标系);deployed 支 = 上场紧缩行序 → 容器行序
    (CwActionSellDeployedParam 坐标系)。失配 = 陈旧帧 fail-closed
    零动作返回主循环。卖出登记(record_round_sold) = 轮内新鲜度排除
    账本写端(资格面账本,非试错计数),与现行卖出位同口径。
    取用观测键随发出落账(<counter>_tier_<n> 档位分布 /
    <counter>_rng_tail_hit 随机尾键命中;键名族登记 =
    telemetry/schema.py 键表节,载荷来源 = 评估器候选行观测字段)。
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
        if cand.tier is not None:
            _tk = f'{counter}_tier_{int(cand.tier)}'
            st.cw4_counters[_tk] = st.cw4_counters.get(_tk, 0) + 1
        if cand.rng_tail_hit:
            _rk = f'{counter}_rng_tail_hit'
            st.cw4_counters[_rk] = st.cw4_counters.get(_rk, 0) + 1
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
    if cand.tier is not None:
        _tk = f'{counter}_tier_{int(cand.tier)}'
        st.cw4_counters[_tk] = st.cw4_counters.get(_tk, 0) + 1
    if cand.rng_tail_hit:
        _rk = f'{counter}_rng_tail_hit'
        st.cw4_counters[_rk] = st.cw4_counters.get(_rk, 0) + 1
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
    # 席满:统一序列末位让位(采晶矿前空位场景;3.2 改造 = 垫件谓词
    # 过滤退役【拍,总纲 §2.7 无场景专属池子/身份过滤退役】——部署重排
    # 后的全局面序列,末位即让位对象;无任何可卖件 → 放弃晶矿保留:
    # 确定的高价值持有不换随机产出的让位只发生在序列真空时,挂待玩家
    # 确认申报沿袭,prep_pipeline「关键取舍」节差分申报)。
    _cands, _why = evaluate_sell_candidates(gs, 'ore_make_room')
    if _cands:
        return _emit_sell_candidate(
            session, gs, _cands[0], reason='ore_make_room',
            tag='ore_make_room_sell', counter='ore_pad_sell')
    # 无垫件 → 放弃晶矿(白拿的必拿精神保留:垫件卖尽前的晶矿全拿;
    # 放弃仅发生在需要牺牲高价值持有时——挂待玩家确认,prep_pipeline
    # 「关键取舍」节差分申报)。
    st.cw4_counters['ore_yield_no_pad'] = \
        st.cw4_counters.get('ore_yield_no_pad', 0) + 1
    return []


# ============================================================ 升级检查(工序第 4 步)


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
    """升级检查步(工序第 4 步;11 号稿 §2 单判据 + 单帧原子发射:
    判据每帧重评,无跨画面键)。

    资格门全链判定单一源 = :func:`criteria.levelup.upgrade_gate_verdict`
    (与商店会话升级意图出口两屏同参消费,本函数零内联门)。
    命中后发射:

    - **全链通过** → 发购买经验整批,**单帧原子**(实付上界 = 发射时
      授权值;授权不再跨帧携带——「买一半」形态由发射原子性消解)+
      **清 handled 标记**(升级前若经会话正常收工置位,升级后概率档
      已变,本节点找牌与刷新判据需重评——非商业间谍路径的重开通道);
    - **金不足**(花后破线)→ 整批推迟,帧零动作,拒因键
      ``levelup_fund_line_defer``——升级发射 = 收入/利息净累积支配,
      等节点收入自然过线(用户裁定 2026-10-30:不存在升级卖牌凑金
      ——保持最大压牌库,钱够了再升;卖牌凑金链已整删,压牌库资产
      不再被升级变现回抽);
    - 其余 defer(门拦)/未命中 → 零动作。

    血本位局(XP 以血支付):变现步不适用(变现卖出对血支付零贡献)
    ——经验批支付门过即发射(单帧原子同款;R-1 币种通式:血余额 ≥
    整批血成本 = 支付能力检查);不足 = 零购买(攒钱模式 = 等节点
    血收入)。

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
    # 失效帧无法评估资金线/触发面 → 读数开店锚定,标记不动;账面宿主 =
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
    # 未命中 / 资格门拦(金不足恒 defer,拒因计数已由判定函数写入
    # levelup_fund_line_defer)= 零动作。
    return []


# (升级凑金在途的节末凑息抑制谓词 _step3_liquidation_pending 已随
# 凑金链整删(用户裁定 2026-10-30 选 A:等钱帧凑息照常——卖垫牌跨档
# 增金正助「钱够了再升」);等级帽/奖励/等钱帧的节末凑息恢复运行,
# 凑息触发不再咨询升级判据。)


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
    """部署调整步(工序第 6 步;阶段 5/6 切差分执行器——unified-
    deploy-order §5 步骤映射:第 6 步 = 搜索定型 + 差分执行器
    (``_step5_deploy`` 旧三臂定型 + ``_make_windowed_select_up`` 换人
    替补均被替换,与前置步级联共用 §3 执行器)。

    形态 = 常规部署差分(非计划执行期):**零读屏多动作循环 + 入口
    heavy 对账**现状维持(§3.5 D9-3:无卡死判定需求,收敛由下一入口
    对账兜底;假收敛最坏 = 带误差板打完当前节点、战后对账纠回——
    常规纯移动可逆故入口对账足够)。溢出告警帧 = 搜索与差分执行器
    全跳过(emit 溢出门早退承载);窗口谓词/上场锁过滤在搜索段 0
    (枚举硬约束,谓词本体单一源 = 本模块 ``_deploy_window_blocked``)。

    动作 = 统一拖动/换星直卖序列(帧稳定 conditional 续发,同序列
    bench 槽位复检);每帧重算幂等,执行进度由容器逻辑态自上报推进。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        deploy_diff,
    )
    prep = mandate.assemble_prep_context(session, gs, frame)
    target = mandate.select_deployment(frame, prep)
    actions = deploy_diff.deploy_diff_target_actions(session, gs, target)
    if not actions:
        # 定型收敛帧:零动作正常返回(扫描推进)。
        return []
    st = state_of(session)
    st.cw4_counters['deploy_diff_actions'] = \
        st.cw4_counters.get('deploy_diff_actions', 0) + len(actions)
    return [mandate.Emitted(a, True, 'step6_deploy_diff') for a in actions]


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


# (凑息保护档阻断观测键 interest_round_protected_block 及其反事实支
# _protected_member_blocks_interest 已随身份保护判据退役删除——统一让位
# 优先级迭代 3.4,拆除清单 §3 遥测键面:保护件阻断类键的消费位(数据源
# protection_membership)退役,键停止生产;退役登记 = telemetry/schema.py
# 键表节「停产键族」。)


def _step7_node_end_interest(session: StrategySession,
                             gs: GameState,
                             ) -> list[Emitted]:
    """节末凑息步(工序第 8 步;22 号篇 §1 第 8 步;3.2 改造 = 统一序列
    消费,场景池/身份面随评估器重写退役——部署重排后全局面序列,部署
    定型内档 1 天然永不先卖,「凑金/凑息可卖场上无关角色」形态废止,
    总纲 §2.7 行为申报)。

    凑息豁免(roster-plane1-union design §2.2 第 5 项):候选池剔除
    线内未达标成员(线内 ∧ 手持 ∧ 星未达目标)——为利息不得动阵容
    在建件,是为利息绝对不可卖,非排序后移;被迫类卖出(溢出/晶矿/
    获取让位)不适用。池空 → 零动作,剔光帧落观测键(评估器写点,
    见下方调用注释)。

    触发 = 存在「单件退金 ≥ 到下一利息档缺口」的资格候选(缺口单一源
    = kernel ``next_interest_line``;跨不了档的卖出零利息收益,一件不
    卖——跨档止盈保留为场景参数,评估器内实现)。动作 = 统一让位序列
    末位一张(priority.sell_order,身份/星级代理过滤退役),逐帧单张:
    跨档后下帧按新金位重评,缺口重算自然收敛。空板守卫(deployed = 0
    帧哑火)= 评估器 as-built 并入语义。本步卖出的退金由第 5 步入口
    统一复核(23 号篇契约 A)。

    (升级凑金在途的凑息抑制已随凑金链整删——用户裁定 2026-10-30
    选 A:等钱帧凑息照常,等级帽/奖励/等钱帧的节末凑息恢复运行;
    凑息触发不再咨询升级判据,同帧重评的二次资格门调用一并退役。)

    金位读数门(23 号篇金位读数形态):账面失效帧无法判「缺口与候选
    退金」→ 读数开店锚定(标记不动),下帧重评。

    观测键退役申报(统一让位优先级迭代 3.4):原
    ``interest_round_protected_block``(「全场保护档」帧凑息损失量化)
    随身份保护判据退役——凑息资格不再有保护身份排除,无可行件帧 =
    序列真空帧,反事实支无对象。
    """
    if state_of(gs).gold_ledger is None:
        return _open_shop_for_gold_read(session, gs)
    _gold = gold_of(gs)
    _line = next_interest_line(_gold, cap_resolved_of_session(session))
    if _line is None:
        return []
    # 统一序列消费(3.2):跨档止盈已为节末凑息场景参数(评估器内实现,
    # 仅「单件退金 ≥ 缺口」者入序列,按实际星级退金判——仅一星过滤退役
    # 【拍,总纲 §2.4】),取用 = 让位序首位;无可行件 = 序列真空,
    # 零动作(观测键已随身份段退役,3.4)。凑息豁免(roster-plane1-
    # union design §2.2 第 5 项):线内未达标成员为利息绝对不可卖,
    # 评估器池过滤承载;剔光帧(唯一可行件全为线内未达标成员 → 零
    # 动作)观测键随 counters 载体落账(写点 = 评估器,键 =
    # sell_candidates.INTEREST_EXEMPT_DEPLETED_KEY)。
    _cands, _why = evaluate_sell_candidates(
        gs, 'node_end_interest',
        counters=state_of(gs).cw4_counters)
    if not _cands:
        return []
    return _emit_sell_candidate(
        session, gs, _cands[0], reason='interest_prep',
        tag='interest_prep', counter='node_end_interest_sell')
