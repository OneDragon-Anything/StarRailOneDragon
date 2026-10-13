"""货币战争策略器 session 作用域键基建(节点边界重置 + 方向状态骨架 +
商店会话标记与机会清单存储)。

职责与设计依据(迭代 changes/2026-10-12-prep-shop-workflow-redesign):

- **节点边界处理** = 节点作用域键重置清单的唯一所有者
  (prep_pipeline §3;design 契约 C):备战/商店两决策入口各调同一
  函数 :func:`handle_node_boundary`,检测到节点号(位面, 轮)变化时
  按 :data:`_NODE_SCOPE_RESET_TABLE` 复位——其他模块的节点作用域键
  显式登记进该表,禁各自散写重置逻辑;
- **方向状态骨架**(design 契约 B;line_and_upgrade §3):
  :func:`refresh_line_if_needed`(签名前置段,幂等跳过)+
  :func:`write_line_lock`(锁定写入——连带动作三件的唯一所有者)+
  :func:`line_members_view`(名单读接口)。**本阶段方向解析 = 现行为
  等价**(现行 ``target_comp`` 物化链照读),候选-锁定判据本体在迭代
  批 3.7 替换内核;
- **商店会话标记与机会清单存储**(design 契约 A;shop_session §4):
  ``shop_handled`` 标记与未消费机会清单的写入/清空/查询——解拦复核
  判定函数归迭代批 3.6 建造,本模块只建存储。

过渡期双轨(line_and_upgrade §3「框架事实」节):现行 ``target_comp``
物化链(flow 层帧代次消费)写点不动,本模块方向键为新增键族,不改
任何现有键语义;3.3-3.7 各批按消费面逐步切到本模块视图(读侧分批
切换,无协调缺口)。
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
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    LevelUpPreAuth,
    ShopOpportunity,
    StrategyState,
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import Unit


# ============================================================ 节点边界处理(契约 C)


# 节点边界重置清单表(键清单唯一所有者 = 本模块;prep_pipeline §3;
# design 契约 C)。每行 = (StrategyState 属性名, 复位值)。
# 登记扩展方式:其他模块的节点作用域键在此显式登记(键名 + 初始值),
# 禁各自散写重置逻辑——重置动作集中执行才可被逐键测试对账。
#
# 清单五项(prep_pipeline §3;前四项 = 重置动作,第五项 = 负登记):
# ① shop_handled → 清值(新节点牌面全换,旧标记语义死亡;机制依据 =
#    economy §2.1「节点切换自动刷新全店」);
# ② shop_opportunities → 清空(牌面变了,旧机会作废);
# ③ levelup_preauth → 清零(节点切换 = 金/血/收入日程全变,旧授权
#    作废,防旧授权跨节点兑现;登记来源 = line_and_upgrade §2.2);
# ④ line_eval_signature → 置失效(强制下帧重算——节点变动伴随结算
#    收入与自然经验,资产面可能变化);
# ⑤ 方向状态本身(line_locked_comp / line_candidates /
#    opening_recipe_comp)不重置——锁定为一次性决策跨节点持续保留
#    (契约 C;候选快照随签名重算自然更新、配方物化链每备战期自写,
#    均非节点作用域键)。plane2_started 同不重置(单调历史事实)。
_NODE_SCOPE_RESET_TABLE: tuple[tuple[str, object], ...] = (
    ('shop_handled', None),
    ('shop_opportunities', ()),
    ('levelup_preauth', None),
    ('line_eval_signature', None),
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
    log.info('[cw][node-boundary] 节点切换 %s → %s,节点作用域键按清单复位',
             prev, cur)


#: 「第二位面已启动」窗口谓词的置位序位下界(line_and_upgrade §1.4
#: 时点兜底行):(位面, 轮) 序位元组,均 1 基,轮次 1 基下 (2,1) 即
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
    """方向证据签名(line_and_upgrade §3 步骤 1)。

    构成 = 持有名单(备战席 ∪ 场上,(char_id, star) 多重集,排序成序)
    + 装备持有 + 投资效果集(active_strategies)+ 等级 + 节点号 + 锁定态。
    为什么等级入签名:店内整级购买经验后等级变 → 概率表变 → 候选分数
    与刷新判据期望全变,消费旧等级概率 = 评估陈旧(设计原文)。锁定态
    入签名:锁定写入为一次性事件,写入后签名含锁定标志、此后只读。
    签名只做相等比较(幂等跳过判据),持有名单排序保证顺序无关。
    """
    held = sorted((u.char_id, int(u.star)) for u in _held_units(gs))
    equips = gs.equips.value or ()
    strategies = gs.active_strategies.value or ()
    return (
        tuple(held),
        tuple(sorted(equips)),
        tuple(sorted(strategies)),
        int(level_of(gs)),
        effective_node_pos(gs),
        st.line_locked_comp,
    )


def _recompute_line_state(gs: GameState, st: StrategyState) -> None:
    """方向状态重算(签名变化时执行;**本阶段 = 现行为等价内核**)。

    - 锁定后只读锁定线:锁定线槽非空时候选快照停算(锁定写入连带
      动作③的结构承载,不另设标志位)——签名照常更新(签名含锁定态,
      幂等跳过照常),快照不再维护;
    - 未锁定态(本阶段恒未锁定——锁定判据 3.7 落码,锁定仅经
      :func:`write_line_lock` 骨架写入):
      * ``opening_recipe_comp`` = 现行 ``target_comp`` 物化链产物照读
        (配方开局面独立键;终态写者 = 配方对物化链本体,本阶段物化
        链仍写 ``target_comp``,故此处照读搬运);
      * ``line_candidates`` = 照读产物名的单元素快照(终态 = 线分数
        top3,3.7 替换;无产物 = 空)。
    """
    if st.line_locked_comp is not None:
        return
    comp = getattr(st, 'target_comp', None)
    st.opening_recipe_comp = comp
    st.line_candidates = (comp.name,) if comp is not None else ()


def refresh_line_if_needed(gs: GameState) -> None:
    """方向签名前置段(契约 B;line_and_upgrade §3 步骤 1-3)。

    备战决策入口与商店决策入口各挂本前置函数;执行时序(帧内先后序)
    = 节点边界重置 → 本函数 → 决策:

    1. 拼证据签名(:func:`_direction_signature`);
    2. 签名 == 上次评估签名 → 直接返回现值(幂等跳过,零重算);
    3. 签名变化 → 重算方向状态(:func:`_recompute_line_state`)。节点
       号在签名构成内,节点边界重置置失效签名后本函数必重算(节点号
       变化时签名必变 = 节点边界重算入口,prep_pipeline §3)。
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
    指向此处):

    - 锁定线槽一次性写入,锁后只读:已锁定时本函数 no-op(候选-锁定
      制无换目标,重复触发不改变锁定线);
    - 连带动作三件:
      ① 清升级预授权键(未锁定态授权按候选集算,锁定线变更后需按
         新名单重新过账,防旧授权跨锁定兑现);
      ② 清商店会话标记(``shop_handled``——下一轮备战第 4 步按锁定
         线名单重开会话全量评估,shop_session §4.2「方向锁定不走清单
         解拦」);
      ③ 候选快照停算(锁定后只读锁定线,无候选维护)——结构承载于
         :func:`_recompute_line_state` 的锁定守卫。
    - 触发判据(硬规则查表/时点兜底)归迭代批 3.7;本函数 = 写入
      骨架,3.7 判据命中帧经此写入。
    """
    st = state_of(gs)
    if st.line_locked_comp is not None:
        return
    st.line_locked_comp = comp_name
    st.levelup_preauth = None
    st.shop_handled = None
    log.info('[cw][line-lock] 方向锁定 → %s(连带:清预授权键/清商店标记/快照停算)',
             comp_name)


def line_members_view(gs: GameState) -> LineMembersView:
    """方向状态读接口(契约 B;line_and_upgrade §3)。

    未锁定 → 空名单 + 未锁定旗标(两域据此走件级评估路径——候选囤件
    优先级,line_and_upgrade §1.3);锁定 → 锁定线名单(core_chars ∪
    shared_chars,注册表序去重)。注册表漂移(锁定名解析失败)按未
    锁定口径返回(保守向:消费面拿空名单走件级路径,不猜名单)。
    """
    st = state_of(gs)
    name = st.line_locked_comp
    if name is None:
        return LineMembersView(locked=False, comp_name=None, members=())
    comp = get_comp(name)
    if comp is None:
        log.warning('[cw!][line-view] 锁定线解析失败(%s),按未锁定口径返回', name)
        return LineMembersView(locked=False, comp_name=None, members=())
    members = tuple(dict.fromkeys(
        list(comp.core_chars) + list(getattr(comp, 'shared_chars', None) or ())))
    return LineMembersView(locked=True, comp_name=name, members=members)


# ============================================================ 商店会话标记与机会清单存储(契约 A)


def mark_shop_handled(gs: GameState) -> None:
    """商店会话标记写入(仅正常收工位调用;shop_session §4.1)。

    值 = 当前生效节点号二元组(位面, 轮;取值时机 = 正常收工帧现读
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
    'LevelUpPreAuth',
    'LineMembersView',
    'ShopOpportunity',
    'clear_shop_handled',
    'clear_shop_opportunities',
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
