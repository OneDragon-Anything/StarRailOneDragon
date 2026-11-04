"""货币战争策略器 session 作用域键基建(节点边界重置 + 方向状态骨架 +
商店会话标记与机会清单存储)。

职责与设计依据(迭代 changes/2026-10-12-prep-shop-workflow-redesign):

- **节点边界处理** = 节点作用域键重置清单的唯一所有者
  (prep_pipeline §3;design 契约 C):备战/商店两决策入口各调同一
  函数 :func:`handle_node_boundary`,检测到节点号(位面,轮)变化时
  按 :data:`_NODE_SCOPE_RESET_TABLE` 复位——其他模块的节点作用域键
  显式登记进该表,禁各自散写重置逻辑;
- **方向状态**(design 契约 B;line_and_upgrade §3;键面归一
  后的终态形态):
  :func:`refresh_line_if_needed`(签名前置段,幂等跳过 + 候选-锁定
  判据内核 = :mod:`line_select`)+
  :func:`write_line_lock`(锁定写入——连带动作三件的唯一所有者,兼
  ``target_comp`` 终态单写者)+
  :func:`line_members_view`(名单读接口)+
  :func:`direction_comp_of`(现行方向读口:锁定线优先,未锁 = 过渡
  配方开局面——§1.6 消费面分派的组合读形态);
- **商店会话标记与机会清单存储**(design 契约 A;shop_session §4):
  ``shop_handled`` 标记与未消费机会清单的写入/清空/查询——解拦复核
  判定函数归迭代建造,本模块只建存储。

现行键面:``target_comp`` 双写者冲突
已消——写者收为锁定动作(:func:`write_line_lock` 终态单写者),配方
物化链写端切 ``opening_recipe_comp``(flow 层);``line_locked_comp``
过渡键已删除。kernel 消费面经 ``ist.locked_comp``/``ist.phase``
派生缓存续读(重建写端 = 本模块刷新/锁定动作同步,§1.6「line_
members_view 刷新时重写 locked_comp」的实现形态)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
    effective_node_pos,
    level_of,
)
from sr_od.application.currency_war.kernel.cw_intention import IntentionState
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    line_select,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    ShopOpportunity,
    StrategyState,
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp, Unit


# ============================================================ 节点边界处理(契约 C)


# 节点边界重置清单表(键清单唯一所有者 = 本模块;prep_pipeline §3;
# design 契约 C)。每行 = (StrategyState 属性名,复位值)。
# 登记扩展方式:其他模块的节点作用域键在此显式登记(键名 + 初始值),
# 禁各自散写重置逻辑——重置动作集中执行才可被逐键测试对账。
#
# 清单(prep_pipeline §3;前若干项 = 重置动作,尾项 = 负登记):
# ① shop_handled → 清值(新节点牌面全换,旧标记语义死亡;机制依据 =
#    economy §2.1「节点切换自动刷新全店」);
# ② shop_opportunities → 清空(牌面变了,旧机会作废);
# ③ line_eval_signature → 置失效(强制下帧重算——节点变动伴随结算
#    收入与自然经验,资产面可能变化);
# ④ 金位读数账面 gold_ledger → 置失效(读数失效条件「节点切换」经本
#    清单落地,契约 C;「经验就是财富」类节点结算入金由本项天然吸收
#    ——失效先行;登记来源 = shop_session §4.2 读数协议);
# ⑤ 商店会话会话域旗标(shop_read_intent/shop_visit_restricted/
#    shop_session_processing/shop_plugin_budget)→ 复位(会话不跨节点;
#    边界帧残留旗标防泄入下一节点会话,卫生性复位);
# ⑥ 方向状态本身(target_comp / line_candidates /
#    opening_recipe_comp / transition_candidates)不重置——锁定为一次性
#    决策跨节点持续保留(契约 C;候选快照随签名重算自然更新、配方物化链
#    与过渡候选槽随方向节拍贵段重算自写〔update_p1_recipe,
#    12 号篇 §3 写端单一〕,均非节点作用域键,清空点 =
#    进 P2〔clear_p1_recipe〕)。plane2_started 同不重置(单调历史事实);
#    p2_pick_baseline/p2_strategy_pick_done 同不重置(时点兜底触发
#    分支为单调事实,且锁定后无消费面);
# ⑦ 获取让位跨画面计划槽 yield_plan → 清空 + X 路径失败标记
#    x_path_failed → 复位(roster-plane1-union design §2.2 第 4 项:
#    节点切换 = 新货架新局面,旧计划/失败标记语义死亡;槽另带节点戳
#    双保险,见 mandate_state 字段注)。
# (升级预授权重置行已随 2026-10-17 迭代 T-4 键退役删除——
#  判据同帧重评后无跨帧授权可清。)
_NODE_SCOPE_RESET_TABLE: tuple[tuple[str, object], ...] = (
    ('shop_handled', None),
    ('shop_opportunities', ()),
    ('line_eval_signature', None),
    ('gold_ledger', None),
    ('shop_read_intent', False),
    ('shop_visit_restricted', False),
    ('shop_session_processing', False),
    ('shop_plugin_budget', 0),
    ('yield_plan', None),
    ('x_path_failed', False),
)


def handle_node_boundary(gs: GameState) -> None:
    """节点边界处理函数(备战/商店两决策入口各调同一函数;契约 C)。

    - 触发检测 = 函数内部上次处理节点号比对(判重键
      ``node_boundary_last_pos`` 存储):生效序位 ``effective_node_pos``
      变化才执行,相同节点号不重复执行(重置操作全部幂等,重复执行
      无害——判重为避免冗余执行与日志噪声,prep_pipeline §3);
    - 首次调用(上次记录 None)同样执行:状态对象局首冷建天然初值,
      重置冗余但无害,统一「变化即执行」语义免特判;
    - 节点号未观察(None)不执行:未观察不当真。
    - 窗口谓词标志维护(:func:`_update_plane2_started`)随本函数同点
      位执行——它是节点序位的单调派生,不是节点作用域键,不进重置
      清单。
    """
    st = state_of(gs)
    _update_plane2_started(gs, st)
    cur = effective_node_pos(gs)
    if cur is None or st.node_boundary_last_pos == cur:
        return
    prev = st.node_boundary_last_pos
    st.node_boundary_last_pos = cur
    for attr, reset_value in _NODE_SCOPE_RESET_TABLE:
        setattr(st, attr, reset_value)
    # 商店随机态重开信号节点边界清扫(2026-10-17 迭代 design §2.4:信号
    # 宿主 = GameState 簿记槽 shop_randomized_pending,不在 StrategyState
    # 重置表——节点推进 = 旧节点商店牌面语义死亡,过期代次随之失效,与
    # 重置表 shop_handled 清值同机制依据)。代次判据(迭代
    # 2026-09-23-invest-effects-calc T-434):只清真旧源 = 戳 ≠ 当前生效
    # 序位(cur,与 :func:`effective_node_pos` 判定基准同源);戳 = cur =
    # 节点推进时点置位的新源(经 T-432 advance 尾排空置位,恰在进入新
    # 节点的同一次 advance 内盖新节点戳),保留交本帧重开位消费——无差别
    # 一刀切会把该新源当旧牌面清掉(守恒式 spy_deals == reopens 破,
    # seed 20261012 实测,T-432 验收偏差 A;置位端盖戳 =
    # kernel mark_shop_randomized_pending)。
    sig_gen = gs.shop_randomized_pending
    if sig_gen is not None and sig_gen != cur:
        gs.shop_randomized_pending = None
    log.info('[cw][node-boundary] 节点切换 %s → %s,节点作用域键按清单复位',
             prev, cur)


#: 「第二位面已启动」窗口谓词的置位序位下界(line_and_upgrade §1.4
#: 时点兜底行):(位面,轮) 序位元组,均 1 基,轮次 1 基下 (2,1) 即
#: (2,*) 段最小序位——字典序 ≥ (2,1) ⇔ 首入第二位面段。
_PLANE2_START_MIN_POS: tuple[int, int] = (2, 1)


def _update_plane2_started(gs: GameState, st: StrategyState) -> None:
    """「第二位面已启动」布尔标志维护(单调置位,永不复位)。

    置位判据 = ``gs.node_hist_pos``(本 run 已见最大生效节点序位,单调
    水位)序位首入 (2,*) 段。为什么用 node_hist_pos 而非 effective_node_pos
    现值:标志语义 = 「第二位面已启动」的历史事实,单调水位天然承载
    (现值可被纠偏写序中间态拉回,历史事实不可逆);载体指认 =
    line_and_upgrade §1.4 时点兜底行。消费端 = 3.7 时点兜底,经
    :func:`plane2_started_of` 读布尔标志(宪法第 2 条合规:窗口谓词
    形态,非位面元组字面量直接比较)。
    """
    hist = gs.node_hist_pos
    if hist is not None and hist >= _PLANE2_START_MIN_POS:
        st.plane2_started = True


def plane2_started_of(gs: GameState) -> bool:
    """「第二位面已启动」窗口谓词读口(置位后恒真;3.7 时点兜底消费)。"""
    return state_of(gs).plane2_started


# ============================================================ 方向状态骨架(契约 B)


@dataclass(frozen=True)
class LineMembersView:
    """方向状态读接口的返回视图(契约 B;line_and_upgrade §3)。

    消费方(备战部署/凑息/自救与商店买入序/置换账)消费同一视图,
    禁各自维护第二份名单口径(design 契约 B)。
    """

    locked: bool               # 锁定旗标(锁定线槽非空)
    comp_name: str | None      # 锁定线名;未锁定 = None
    members: tuple[str, ...]   # 锁定线名单(core ∪ shared,注册表序去重);未锁定 = 空


def _held_units(gs: GameState) -> list[Unit]:
    """持有单位枚举(备战席 ∪ 场上;方向证据签名的持有读面)。"""
    units: list[Unit] = list(bench_units_of(gs))
    front, back = deployed_rows_of(gs)
    units.extend(front)
    units.extend(back)
    return units


def _direction_signature(gs: GameState, st: StrategyState) -> tuple:
    """方向证据签名(12 号篇 §3 步骤 1;统一阵容评分迭代扩参)。

    构成 = 持有名单(备战席 ∪ 场上,(char_id, star) 多重集,排序成序)
    + 装备持有 + 投资效果集(active_strategies)+ **投资环境
    (active_env)** + **开局词缀/boss**(enemy_affixes/plane_bosses 排序
    分量)+ 等级 + 节点号 + 锁定态。为什么等级入签名:店内整级购买经验
    后等级变 → 概率表变 → 候选分数与刷新判据期望全变,消费旧等级概率 =
    评估陈旧(设计原文)。env 入签名(review-37 R1)与词缀/boss 入签名
    (2026-11-03-unified-line-scoring design §6,沿 env 先例):两者现进
    线分(投资通道派生/词缀分),变化而签名其余分量不变时幂等跳过会漏
    重算——词缀/boss 简报观察晚于开局首帧(中断恢复位面详情转正帧),
    缺签名分量 = 候选消费静默旧值。锁定态入签名:锁定写入为一次性事件,
    写入后签名含锁定标志、此后只读。签名只做相等比较(幂等跳过判据),
    持有名单/词缀/boss 排序保证顺序无关。
    """
    held = sorted((u.char_id, int(u.star)) for u in _held_units(gs))
    equips = gs.equips.value or ()
    strategies = gs.active_strategies.value or ()
    return (
        tuple(held),
        tuple(sorted(equips)),
        tuple(sorted(strategies)),
        gs.active_env.value or '',
        tuple(sorted(gs.enemy_affixes.value or ())),
        tuple(sorted(b for b in (gs.plane_bosses.value or ()) if b)),
        int(level_of(gs)),
        effective_node_pos(gs),
        st.target_comp,
    )


def _sync_derived_lock_cache(st: StrategyState) -> None:
    """kernel 派生缓存同步(``ist.locked_comp``/``ist.phase`` ← 锁定线槽)。

    §1.6 意向层机器本体停用后,``ist.locked_comp`` 不再有状态机写者,
    改为锁定线槽(``target_comp``)的派生缓存——「重建写端 =
    line_members_view 刷新时重写 locked_comp(派生缓存单一写端)」的
    实现形态:kernel 消费面(cw_economy/cw_deploy_logic/shop/flow 装配
    面等已登记读点)读端零改。锁定 ⟺ ``st.target_comp`` 非 None;
    ``phase`` 仅剩 ``locked``/``unlocked`` 两态(weak/demoted 随状态机
    停用不可达)。ist 缺席时**冷建**(与 flow._ensure_intention 同构)——
    前置序时序上 refresh 先于 flow 方向内务,首帧锁定时 ist 可能尚未
    惰性就位,不冷建则派生缓存存在失同步窗。
    """
    ist = getattr(st, 'v3_intention', None)
    if not isinstance(ist, IntentionState):
        ist = st.v3_intention = IntentionState()
    name = st.target_comp.name if st.target_comp is not None else None
    ist.locked_comp = name or ''
    ist.phase = 'locked' if name else 'unlocked'


def _update_p2_pick_done(gs: GameState, st: StrategyState) -> None:
    """时点兜底触发分支之二:P2 起首次投资策略三选一完成侦测(§1.4)。

    基线 = **P1 滑动基线**(每次 P1 帧刷新持续覆写,进 P2 冻结)——
    P1 期间获得的策略(白银投资类加场卡)入基线不计增长;进 P2 后的
    集合增长(投资策略获得——上报链写 active_strategies,决策帧刷新
    观察到)即置位。为什么滑动而非「P2 首帧快照」(review-37 R2):
    P2 开局三选一先于首个 P2 决策帧完成时,首帧快照会把该笔获得吞进
    基线(兜底退化为第二笔获得帧);滑动基线以 P1 末次刷新快照冻结,
    首笔 P2 获得照常侦测为增长。单调旗标,置位后不再维护(锁定后无
    消费面)。防御位:P2 首帧前无任何 P1 刷新帧(中断恢复的对局)时基线以
    首帧现值兜底捕获——该帧前的获得不可辨(保守侧:不触发,等下一
    笔增长)。增长来源不区分选卡/节点赠得(P2 段下一笔策略获得的
    压倒性形态 = 开局三选一;两者对「策略已定 → 可兜底终局阵容锁定」语义
    等价,裁量申报)。
    """
    current = frozenset(gs.active_strategies.value or ())
    if not st.plane2_started:
        st.p2_pick_baseline = current   # P1 滑动基线(进 P2 冻结)
        return
    if st.p2_strategy_pick_done:
        return
    if st.p2_pick_baseline is None:
        st.p2_pick_baseline = current   # 防御位:P2 首帧前无 P1 帧(中断恢复的对局)
        return
    if current - st.p2_pick_baseline:
        st.p2_strategy_pick_done = True


def _recompute_line_state(gs: GameState, st: StrategyState) -> None:
    """方向状态重算(签名变化时执行;统一阵容评分真内核,12 号篇
    §1.2-§1.3;判据本体单一源 = :mod:`line_select`)。

    - 锁定后只读锁定线:锁定线槽(``target_comp``)非空时本段在缓存
      同步后直接返回(候选快照停算,锁定写入时已清空——
      :func:`write_line_lock` 连带③);
    - 未锁定态:每帧对全部 21 线算分(:func:`line_select.line_score_key`
      单值和:证据 + 投资通道派生 + 词缀 + boss〔批 2 前恒 0〕+ 热度,
      注册序终局;开局简报上下文 = :func:`line_select.opening_ctx_of`
      现读),top3 写候选快照(``line_candidates``,派生快照非持久状态)
      ——**证据门开启版**(12 号篇 §1.2:线分量 env ∨ carry ∨ 骨架 ∨
      插件 > 0,不含热度;零证据线不入,开局零信号 = 空候选合法形态);
      随后求值锁定判定(:func:`line_select.evaluate_lock`——P2 时点兜底
      唯一路径:硬规则/即时锁全退役,``plane2_started ∧ P2 投资策略选卡
      完成`` → 候选首名),命中即经 :func:`write_line_lock` 写入(锁定
      动作发生的域内立即生效,§3)。
    """
    _sync_derived_lock_cache(st)
    if st.target_comp is not None:
        return
    _update_p2_pick_done(gs, st)
    held_chars = line_select.held_chars_of(gs)
    opening_ctx = line_select.opening_ctx_of(gs)
    candidates = line_select.compute_candidates(
        held_chars, opening_ctx, evidence_gate=True)
    st.line_candidates = candidates
    lock_name = line_select.evaluate_lock(
        candidates, held_chars, opening_ctx,
        plane2_started=st.plane2_started,
        p2_strategy_pick_done=st.p2_strategy_pick_done)
    if lock_name is not None:
        write_line_lock(gs, lock_name)


def refresh_line_if_needed(gs: GameState) -> None:
    """方向签名前置段(契约 B;line_and_upgrade §3 步骤 1-3)。

    备战决策入口与商店决策入口各挂本前置函数;执行时序(帧内先后序)
    = 节点边界重置 → 本函数 → 决策:

    1. 拼证据签名(:func:`_direction_signature`);
    2. 签名 == 上次评估签名 → 直接返回现值(幂等跳过,零重算);
    3. 签名变化 → 重算方向状态(:func:`_recompute_line_state`)。节点
       号在签名构成内,节点边界重置置失效签名后本函数必重算(节点号
       变化时签名必变 = 节点边界重算入口,prep_pipeline §3)。

    本阶段重算 = 候选-锁定制真内核(判据本体 = :mod:`line_select`)。
    """
    st = state_of(gs)
    sig = _direction_signature(gs, st)
    if st.line_eval_signature == sig:
        return
    st.line_eval_signature = sig
    _recompute_line_state(gs, st)


def write_line_lock(gs: GameState, comp_name: str) -> None:
    """锁定写入(一次性决策;**连带动作三件的唯一所有者 = 本函数**,
    line_and_upgrade §3 载体落位节——§1.4/契约 B 对连带动作的引用均
    指向此处)。键面归一后本函数兼任 ``target_comp`` 的**终态
    单写者**(锁定线槽 = target_comp;物化链写端已切 opening_recipe_
    阵容,P1 锁定局互不覆写):

    - 锁定线槽一次性写入,锁后只读:已锁定时本函数 no-op(候选-锁定
      制无换目标,重复触发不改变锁定线);注册表解析失败(锁定名不在
      COMP_LIBRARY)按未锁定处置拒绝写入——判定内核只产注册表名,
      此分支为防御位;
    - 连带动作三件:
      ① 清商店会话标记(``shop_handled``——下一轮备战第 5 步按锁定
         线名单重开会话全量评估,shop_session §4.2「方向锁定不走清单
         解拦」);
      ② 候选快照**清空**并停算(锁定后只读锁定线,无候选维护;清空
         消除消费歧义——锁定后读 ``line_candidates`` 恒 = 空集,语义
         自明,无需另查锁定旗标)——停算结构承载于
         :func:`_recompute_line_state` 的锁定守卫;
      ③ kernel 派生缓存同步(见下行)。
      (旧升级预授权连带清键已随 2026-10-17 迭代 T-4 键退役删除——
      判据同帧重评,无跨帧授权可清。)
      **P1 过渡层维持核对(12 号篇 §1.2 P1 锁定局采购通道)**:锁定
      不辖配方链——过渡候选槽/配方物化链/opening_recipe_comp 键不在
      本函数连带面(P1 锁定局配方链照常每 game-round 重算,退场清空
      只在进 P2 = clear_p1_recipe),现行语义零改动。
    - kernel 派生缓存(``ist.locked_comp``/``ist.phase``)同帧同步
      (:func:`_sync_derived_lock_cache`)——kernel 消费面锁定当帧生效。
    """
    st = state_of(gs)
    if st.target_comp is not None:
        return
    comp = get_comp(comp_name)
    if comp is None:
        log.warning('[cw!][line-lock] 锁定线解析失败(%s),拒绝写入(按未锁定)',
                    comp_name)
        return
    st.target_comp = comp
    st.shop_handled = None
    st.line_candidates = ()
    _sync_derived_lock_cache(st)
    log.info('[cw][line-lock] 方向锁定 → %s(连带:清商店标记/快照清空停算)',
             comp_name)


def line_members_view(gs: GameState) -> LineMembersView:
    """方向状态读接口(契约 B;line_and_upgrade §3)。

    未锁定 → 空名单 + 未锁定旗标(两域据此走件级评估路径——候选囤件
    优先级,line_and_upgrade §1.3);锁定 → 锁定线名单(core_chars ∪
    shared_chars,注册表序去重)。
    """
    st = state_of(gs)
    comp = st.target_comp
    if comp is None:
        return LineMembersView(locked=False, comp_name=None, members=())
    members = tuple(dict.fromkeys(
        list(comp.core_chars) + list(getattr(comp, 'shared_chars', None) or ())))
    return LineMembersView(locked=True, comp_name=comp.name, members=members)


def direction_comp_of(gs: GameState) -> Comp | None:
    """现行方向阵容读口(§1.6 消费面分派的组合读形态)。

    = 锁定线(``target_comp``,终局面)优先;**P1 未锁帧**回落过渡
    配方开局面(``opening_recipe_comp``,配方物化链产物——窗口谓词
    覆盖,P2 起配方面明确不在设计范围内、进 P2 时由 ``clear_p1_recipe`` 同点清空)。
    两键都空(P1 空窗 / P2+ 未锁窗口)= None——无方向帧由 K 空窗回退
    (``cw_intention.k_empty_window_fallback``)承接。「现行方向」类
    消费位(flow pick 族/部署围栏 k_members/工具面/商店序 1 名单)
    统一经本读口,禁消费点自拼两键优先级(第二读口径)。

    防御双保险(review-37 P1):``plane2_started`` 帧**禁回落配方键**
    ——即使清空写端因时序未及(如 P2 首帧先于 flow 贵段),读口也
    不消费过期 P1 配方(P2 未锁窗恒走「无方向 → K 空窗回退 p2plus
    带」)。
    """
    st = state_of(gs)
    if st.target_comp is not None:
        return st.target_comp
    if st.plane2_started:
        return None
    return st.opening_recipe_comp


# ============================================================ 商店会话标记与机会清单存储(契约 A)


def mark_shop_handled(gs: GameState) -> None:
    """商店会话标记写入(仅正常收工位调用;shop_session §4.1)。

    值 = 当前生效节点号二元组(位面,轮;取值时机 = 正常收工帧现读
    ``effective_node_pos``)。异常退出/失读停机不写 = 调用方纪律(收工
    位接线归 3.6);节点号未观察(None)时 no-op——「本节点已处理」必
    须有可回比的节点号,未观察不当真。
    """
    st = state_of(gs)
    pos = effective_node_pos(gs)
    if pos is None:
        return
    st.shop_handled = pos


def clear_shop_handled(gs: GameState) -> None:
    """商店会话标记清除(存储口;调用方 = 3.6 解拦复核清标记与
    :func:`write_line_lock` 连带动作②)。"""
    state_of(gs).shop_handled = None


def shop_handled_for_current_node(gs: GameState) -> bool:
    """商店会话标记检查:本节点是否已正常收工处理(shop_session §4.1)。

    判定语义 = 值 ≠ 当前节点号视为未处理;跨节点失效由节点边界重置
    统一清值(契约 C),本值比对作为双保险保留——标记写入后节点号已
    推进、边界函数尚未执行的窗口帧,标记按节点号失配即失效。
    """
    st = state_of(gs)
    pos = effective_node_pos(gs)
    return pos is not None and st.shop_handled == pos


def record_shop_opportunity(gs: GameState, record: ShopOpportunity) -> None:
    """未消费机会清单追加记录(shop_session §4.2;写入端 = 商店会话
    正常收工位,3.6 接线)。追加序保留(同牌多次记录为独立行,消费
    端按牌名自取最近态)。"""
    st = state_of(gs)
    st.shop_opportunities = tuple(st.shop_opportunities) + (record,)


def shop_opportunities_of(gs: GameState) -> tuple[ShopOpportunity, ...]:
    """未消费机会清单查询(只读快照;消费端 = 3.6 解拦复核)。"""
    return tuple(state_of(gs).shop_opportunities)


def clear_shop_opportunities(gs: GameState) -> None:
    """未消费机会清单清空(存储口;节点边界重置走清单表复位不经本
    函数,本函数 = 3.6 解拦消费后的销项口)。"""
    state_of(gs).shop_opportunities = ()


__all__ = [
    'LineMembersView',
    'ShopOpportunity',
    'clear_shop_handled',
    'clear_shop_opportunities',
    'direction_comp_of',
    'handle_node_boundary',
    'line_members_view',
    'mark_shop_handled',
    'plane2_started_of',
    'record_shop_opportunity',
    'refresh_line_if_needed',
    'shop_handled_for_current_node',
    'shop_opportunities_of',
    'write_line_lock',
]
