"""货币战争 v2 决策纯映射层(decision 桶;原 w606 阶段2批③ adapter 的映射半部)。

分包期 5 起原 adapter.py 拆两半:本模块只留**纯映射**——Snapshot →
PrepObservation(视觉/占用观察视图)、PrepAction → AtomOp
(动作 → 原子记账键)。装配半部(DecideAdapter/影子比对/observe 端口
snapshot_from_obs/影子开关)落 app 桶 ``decision_assembly.py``:那些代码
import prep_actions/cw_screen_prep 执行面词汇,留 decision 会构成
decision→app 反向边(分包依赖矩阵:decision 只可依 kernel/data)。

映射语义单一源 = ``.debug/temp/currency_war/w606_stage2_batch3/
DIRECTOR_ADAPTER_DESIGN.md``。``decision_state`` CwWorkFrame 骨架输出
已随 prep 链容器化段 2 退役(唯一消费 assembly.assemble 改容器单例
直读,设计件 §2.4-5);预备域数值锚(旧 ``_anchor_state``)同批消亡
——决策面数值域统一读 session 容器单例。``action_to_atomop`` 的
AtomOp 契约无参数字段:op_key 携参数指纹(幂等/屏蔽键粒度 =
动作类型+参数)。

本模块零 SrOperation 依赖、零识别调用;消费面只有 decision 桶内部
(prep_brain)与测试。
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepAction,
    PrepObservation,
)
from sr_od.application.currency_war.kernel.cw_exec_state import BENCH_CAPACITY
from sr_od.application.currency_war.strategies.impl.mandate_v1.contracts import (
    AtomOp,
    Snapshot,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

#: 决策子态名(适配器只服务备战决策环;分类可信度由框架门在环顶拦截,
#: 进本模块的快照恒 confident——``DecideAdapter.decide`` 断言此前提)。
PREP_SUBSTATE_NAME: str = 'prep_shop'


# ------------------------------------------------- Snapshot → 决策输入(§3)

def snapshot_to_obs(snapshot: Snapshot, session: StrategySession) -> PrepObservation:
    """Snapshot → 备战观察视图(视觉/占用域;设计 §3.1 逐字段表的段 2
    形态:state 装配随 ``PrepObservation.state`` 槽退役删除——局内事实由
    决策面直读 session 容器单例,黑板帧 = 纯视觉/占用观察载体)。

    保守方向裁决(设计钉死,fixture 锁):free_bench_slots None →
    ``BENCH_CAPACITY``(宁多收球——点击失败可自愈、defer 门兜住;不误卖,
    SellBench 不可逆);deploy_vacancy None → 0(不假装有空位)。
    """
    if not snapshot.classification.confident:
        raise ValueError(
            'snapshot_to_obs:非 confident 快照不可进 decide(框架门职责,'
            f'name={snapshot.classification.name})')

    return PrepObservation(
        state_gold_trusted=bool(snapshot.gold_trusted),
        bench_chars=[b for b in snapshot.bench if b is not None],
        deployed_chars=[d for d in snapshot.deployed if d is not None],
        spheres=[(s.color, _point(s.x, s.y), s.radius)
                 for s in snapshot.spheres],
        boxes=[(None, _point(b.x, b.y)) for b in snapshot.boxes],
        tomes=[(None, _point(t.x, t.y)) for t in snapshot.tomes],
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
        event_overlay=snapshot.event_overlay,
    )


def _point(x: int, y: int):
    """交互面坐标 → Point(1080p 游戏空间,契约 RewardSphere 同坐标系)。"""
    from one_dragon.base.geometry.point import Point
    return Point(x, y)


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
    """op_key 参数指纹(与 action_key 同粒度思想:同族不同参数=不同幂等键;
    带 ``action_key_exclude`` metadata 的归因字段同样不入——批 4
    SellBench.reason 填充后,归因标签不得分裂同槽动作的幂等键,与
    action_key 消费同一 metadata 单一源)。"""
    if not dataclasses.is_dataclass(action):
        return ''
    parts = []
    for f in dataclasses.fields(action):
        if f.metadata.get('action_key_exclude'):
            continue
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
