"""货币战争 v2 决策纯映射层(decision 桶;原 w606 阶段2批③ adapter 的映射半部)。

分包期 5 起原 adapter.py 拆两半:本模块只留**纯映射**——Snapshot →
PrepObservation/GameState(decision 核内部输入视图)、PrepAction → AtomOp
(动作 → 原子记账键)。装配半部(DecideAdapter/影子比对/observe 端口
snapshot_from_obs/影子开关)落 app 桶 ``decision_assembly.py``:那些代码
import prep_actions/prep_director 执行面词汇,留 decision 会构成
decision→app 反向边(分包依赖矩阵:decision 只可依 kernel/data)。

映射语义单一源 = ``.debug/temp/currency_war/w606_stage2_batch3/
DIRECTOR_ADAPTER_DESIGN.md``;三映射面中 ``snapshot_to_obs``/``decision_state``
含义务清单四字段(dual_track_phase/active_strategies/equips/refresh_probs)
的 session 显式注入——``active_strategies`` 注入即修复现役 ``_pseudo_state``
漏拷裂缝(消费点 = cw_intention._direct_line_qualified /
cw_economy.level_up_gate 语义链),该修复是相对现役的预期
行为差,归对拍已知合法差异白名单。``action_to_atomop`` 的 AtomOp 契约无
参数字段:op_key 携参数指纹(幂等/屏蔽键粒度 = 动作类型+参数)。

本模块零 SrOperation 依赖、零识别调用;消费面只有 decision 桶内部
(prep_brain)与测试。
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.decision.decision_v2.contracts import (
    AtomOp,
    Snapshot,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepAction,
    PrepObservation,
)
from sr_od.application.currency_war.kernel.cw_state import BENCH_CAPACITY, GameState

if TYPE_CHECKING:
    from sr_od.application.currency_war.decision.cw_strategy import StrategySession

#: 决策子态名(适配器只服务备战决策环;分类可信度由框架门在环顶拦截,
#: 进本模块的快照恒 confident——``DecideAdapter.decide`` 断言此前提)。
PREP_SUBSTATE_NAME: str = 'prep_shop'


# ------------------------------------------------- Snapshot → 决策输入(§3)

def snapshot_to_obs(snapshot: Snapshot, session: StrategySession) -> PrepObservation:
    """Snapshot → 现役 decide_prep_action 的观察视图(设计 §3.1 逐字段表)。

    保守方向裁决(设计钉死,fixture 锁):free_bench_slots None →
    ``BENCH_CAPACITY``(宁多收球——点击失败可自愈、defer 门兜住;不误卖,
    SellBench 不可逆);deploy_vacancy None → 0(不假装有空位)。
    """
    if not snapshot.classification.confident:
        raise ValueError(
            'snapshot_to_obs:非 confident 快照不可进 decide(框架门职责,'
            f'name={snapshot.classification.name})')

    st = _anchor_state(snapshot, session)
    spheres = [(s.color, _point(s.x, s.y), s.radius)
               for s in snapshot.spheres]
    boxes = [(None, _point(b.x, b.y)) for b in snapshot.boxes]
    tomes = [(None, _point(t.x, t.y)) for t in snapshot.tomes]
    return PrepObservation(
        state=st,
        state_gold_trusted=bool(snapshot.gold_trusted),
        bench_chars=[b for b in snapshot.bench if b is not None],
        deployed_chars=[d for d in snapshot.deployed if d is not None],
        spheres=list(spheres),
        boxes=list(boxes),
        tomes=list(tomes),
        free_bench_slots=(snapshot.free_bench_slots
                          if snapshot.free_bench_slots is not None
                          else BENCH_CAPACITY),
        deploy_vacancy=(snapshot.deploy_vacancy
                        if snapshot.deploy_vacancy is not None else 0),
        shop_open=snapshot.shop_open,
        box_overlay_open=snapshot.box_overlay_open,
        front_occupied=set(snapshot.front_occupied),
        back_occupied=set(snapshot.back_occupied),
        front_size=snapshot.front_size,
        back_size=snapshot.back_size,
        event_overlay=snapshot.event_overlay,
    )


def _point(x: int, y: int):
    """交互面坐标 → Point(1080p 游戏空间,契约 RewardSphere 同坐标系)。"""
    from one_dragon.base.geometry.point import Point
    return Point(x, y)


def _anchor_state(snapshot: Snapshot, session: StrategySession) -> GameState:
    """快照数值域 → GameState 骨架(plane/round/level 等带 session 锚回退)。"""
    last = getattr(session, 'last_state', None)
    st = GameState()
    st.plane = snapshot.plane or (last.plane if last is not None else 1)
    st.round_num = snapshot.round_num or (last.round_num if last is not None else 1)
    st.node_type = (snapshot.node_type
                    or getattr(session, 'node_type_current', None)
                    or (last.node_type if last is not None else None))
    st.level = snapshot.level or (last.level if last is not None else 1)
    st.xp_progress = snapshot.xp_progress
    st.level_up_cost = snapshot.level_up_cost
    st.selected_difficulty = snapshot.selected_difficulty
    st.streak = snapshot.streak
    # gold:F2 门(gold_trusted=True 才采用,镜像现役 _pseudo_state 保守口径;
    # gold_readable 保真位独立记录「读到了」这一观测事实)。
    if snapshot.gold_trusted and snapshot.gold is not None:
        st.gold = snapshot.gold
    st.gold_readable = snapshot.gold is not None
    st.hp_readable = snapshot.hp_readable
    return st


def decision_state(snapshot: Snapshot, session: StrategySession) -> GameState:
    """Snapshot + session → 策略内部链消费的 GameState(设计 §3.2 逐字段表)。

    与现役 ``_pseudo_state`` 的关键差异 = `w598_contracts_adversarial/` 映射义务清单四字段显式注入;
    其中 ``active_strategies`` 注入修复现役伪态漏拷裂缝(见模块 docstring)。
    """
    from sr_od.application.currency_war.decision.cw_strategy import gated_hp

    st = snapshot_to_obs(snapshot, session).state
    st.board = dict(snapshot.board) if snapshot.board is not None else {}
    st.board_readable = snapshot.board is not None
    st.bench = [b for b in snapshot.bench if b is not None]   # __post_init pad 到定长
    st.deployed = [d for d in snapshot.deployed if d is not None]
    st.deploy_cap = snapshot.deploy_cap
    st.front_max = snapshot.front_size
    st.back_max = snapshot.back_size
    # R1(蓝图 §4.3)+ 迁移迁移批 2(方向层接管)(方向层接管) 接管:committed 唯一合法读端
    # (prep_brain.committed_from,内部 = cw_intention 权威派生);
    # state.dual_track_phase 为老栈决策核的既有消费面,装配时显式回填
    # (值源 = 方向层权威,P1 同 commit 面)。
    from sr_od.application.currency_war.decision.decision_v2.prep_brain import (
        committed_from,
    )
    st.dual_track_phase = not committed_from(session)
    st.active_strategies = list(getattr(session, 'active_strategies', None) or [])
    st.equips = list(getattr(session, 'last_owned_equips', None) or [])
    last = getattr(session, 'last_state', None)
    probs = getattr(last, 'refresh_probs', None) if last is not None else None
    st.refresh_probs = dict(probs) if probs else None
    # hp 过现役同一新鲜度门(session 锚;None 现读=沿用链,禁 0/100 兜底改值)。
    _t = ((st.plane - 1) * 9 + st.round_num) if (st.plane and st.round_num) else None
    _cur = snapshot.hp if snapshot.hp is not None else (
        last.hp if last is not None else None)   # 无真值=诚实未知(不兜底,W823)
    st.hp = gated_hp(_cur, session, _t, current_readable=snapshot.hp_readable)
    st.hp_readable = snapshot.hp_readable
    return st


# ------------------------------------------- PrepAction → AtomOp 映射(§4)

@dataclass(frozen=True)
class _OpSpec:
    """动作族的 AtomOp 映射规格(设计 §4.1 表的代码化)。"""

    family: str    # op_key 族名(带参数时 op_key = family:参数指纹)
    domain: str


#: 全集映射表(16 动作;键 = PrepAction 类型)。PrepAction 新增动作必须
#: 同步登记(F3 白名单同纪律:漏登记 = 影子侧未知动作缺陷计数,开环侧
#: decide 直接抛错防静默)。
_OP_SPECS: dict[str, _OpSpec] = {}
for _cls, _fam, _dom in [
    ('PickBoxCard', 'pick_box_card', 'interact'),
    ('OpenBox', 'open_box', 'interact'),
    ('OpenTome', 'open_tome', 'interact'),
    ('ClickSpheres', 'click_spheres', 'interact'),
    ('SellBench', 'sell_bench', 'bench'),
    ('SellDeployed', 'sell_deployed', 'bench'),
    ('DeployMove', 'deploy', 'bench'),
    ('LevelUp', 'level_up', 'shop'),
    ('EnsureShopOpen', 'ensure_shop_open', 'shop'),
    ('EnsureShopClosed', 'ensure_shop_closed', 'shop'),
    # W970 批 C:EnsureShop 意图退役后的承接形态(§4.3.6 read_only 变体)
    ('OpenShop', 'open_shop', 'shop'),
    ('StartBattle', 'start_battle', 'battle'),
    ('RunBuyPhase', 'run_buy_phase', 'shop'),
    ('RunDeploy', 'run_deploy', 'deploy'),
    ('RunEquip', 'run_equip', 'equip'),
]:
    _OP_SPECS[_cls] = _OpSpec(_fam, _dom)


def _param_fingerprint(action: PrepAction) -> str:
    """op_key 参数指纹(与 action_key 同粒度思想:同族不同参数=不同幂等键)。"""
    if not dataclasses.is_dataclass(action):
        return ''
    parts = []
    for f in dataclasses.fields(action):
        v = getattr(action, f.name)
        parts.append('' if v is None else str(v))
    return ':'.join(parts) if any(parts) else ''


def action_to_atomop(action: PrepAction) -> AtomOp:
    """PrepAction → AtomOp(控制流动作不经此——Defer/Bail 走 Decision.control)。"""
    spec = _OP_SPECS.get(type(action).__name__)
    if spec is None:
        raise ValueError(f'action_to_atomop:未登记动作 {type(action).__name__}'
                         '(新动作必须同步 _OP_SPECS,防静默)')
    fp = _param_fingerprint(action)
    return AtomOp(op_key=f'{spec.family}:{fp}' if fp else spec.family,
                  domain=spec.domain)
